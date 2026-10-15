/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#define _GNU_SOURCE
#include "config.h"
#include "qm-config.h"
#include "qm-console.h"
#include "qm-exec.h"
#include "qm-network.h"
#include "qm-oci-config.h"
#include "qm-seccomp.h"
#include "qm-state.h"
#include "qm-userns.h"
#include "qm-utils.h"

#include <dirent.h>
#include <err.h>
#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <json-c/json.h>
#include <json-c/json_pointer.h>
#include <limits.h>
#include <signal.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <unistd.h>

#define QM_CONTAINER_ID "qm"
#define QM_SUBID_USER "qm_root"
#define SUPERVISOR_CGROUP "supervisor"
#define PAYLOAD_CGROUP "payload"

#define DEFAULT_RUNTIME_DIR "/run/qm"
#define CRUN "/usr/bin/crun"

typedef enum {
	COMMAND_LAUNCH,
	COMMAND_EXEC,
	COMMAND_INSPECT,
	COMMAND_SIGNAL,
	COMMAND_CLEANUP,
	COMMAND_UPDATE_RESOLV_CONF,
} Command;

static const char *opt_runtime_dir = DEFAULT_RUNTIME_DIR;
static const char *opt_config_file;
static bool opt_verbose;
static bool opt_prepare_only;
static bool opt_inspect_oci;
static const char *opt_inspect_field;
static const char *opt_signal_name;
static bool opt_clear_signal;
static char **opt_exec_argv; /* Borrowed from main's argv, NULL-terminated. */

static void debug(const char *format, ...) __attribute__((format(printf, 1, 2)));

static void debug(const char *format, ...)
{
	if (!opt_verbose)
		return;
	int saved_errno = errno;
	va_list args;
	va_start(args, format);
	fputs("qmc: ", stderr);
	vfprintf(stderr, format, args);
	fputc('\n', stderr);
	va_end(args);
	errno = saved_errno;
}

/* Global crun options must precede the subcommand. */
static void crun_prefix(StrvBuilder *argv, const char *executable, const char *root)
{
	strv_builder_add(argv, executable);
	if (opt_verbose)
		strv_builder_add(argv, "--debug");
	strv_builder_add(argv, "--root");
	strv_builder_add(argv, root);
}

static NetworkOptions get_network_options(const Config *configuration)
{
	return (NetworkOptions){
		.runtime_dir = opt_runtime_dir,
		.veth = "qm-veth",
		.interface = "eth0",
		.ip = configuration->ip,
		.gateway = configuration->gateway,
		.subnet = configuration->subnet,
		.prefix_len = configuration->prefix_length,
		.veth_mac = {0x02, 0x00, 0x0a, 0x5a, 0x00, 0x01},
		.fallback_mtu = 1500,
		.rp_filter = 2,
		.disable_ipv6 = true,
		.nft_table = "qm_launch",
	};
}

static void save_state(const State *state, const char *runtime_dir, bool replace)
{
	autofreejson json_object *object = state_serialize(state);
	autofree char *filename = join_path(runtime_dir, QM_STATE_FILE);
	js_save_atomic(object, filename, replace);
}

static void write_bundle(const Config *configuration, json_object *config);

static int crun_delete(const State *state)
{
	if (!state->crun_executable)
		return 0;
	const char *executable = state->crun_executable;
	const char *root = state->crun_root;
	const char *id = state->container_id;
	autofree char *container = join_path(root, id);
	autofree char *container_status = join_path(container, "status");
	if (access(container_status, F_OK) < 0) {
		if (errno == ENOENT)
			return 0;
		warn("access %s", container_status);
		return 1;
	}

	debug("Deleting container %s with %s (state root %s)", id, executable, root);
	autofreestrvbuilder StrvBuilder argv = {0};
	crun_prefix(&argv, executable, root);
	strv_builder_add(&argv, "delete");
	strv_builder_add(&argv, "--force");
	strv_builder_add(&argv, id);

	return run_command(argv.strv);
}

static int teardown_namespace(const char *netns)
{
	if (!netns)
		return 0;
	int result = 0;

	if (ns_is_mounted(netns)) {
		if (umount(netns) < 0) {
			warn("umount %s", netns);
			return 1;
		}

		if (unlink(netns) < 0) {
			warn("unlink %s", netns);
			result = 1;
		}
	} else if (unlink(netns) < 0 && errno != ENOENT) {
		warn("unlink %s", netns);
		result = 1;
	}

	return result != 0;
}

static int cleanup(const char *runtime_dir)
{
	autofree char *state_file = join_path(runtime_dir, QM_STATE_FILE);
	autoclose int state_fd = open(state_file, O_RDONLY | O_CLOEXEC);
	if (state_fd < 0) {
		if (errno == ENOENT) {
			debug("No saved cleanup state at %s", state_file);
			return 0;
		}
		warn("open %s", state_file);
		return 1;
	}
	/* Setup workers inherit a shared lock. Wait for all of them, including
	 * children of an interrupted worker, before tearing down resources.
	 */
	if (TEMP_FAILURE_RETRY(flock(state_fd, LOCK_EX)) < 0) {
		warn("lock cleanup state %s", state_file);
		return 1;
	}
	debug("Loading cleanup state from %s", state_file);
	autofreejson json_object *object = js_load(state_file);
	autostate State *state = state_deserialize(object);
	int result = crun_delete(state);
	debug("Tearing down recorded network resources");
	result |= network_teardown(state->network);
	debug("Removing recorded network namespace %s",
	      state->netns ? state->netns : "(none)");
	result |= teardown_namespace(state->netns);
	if (!result && state->bundle) {
		debug("Removing runtime bundle contents in %s", state->bundle);
		/* systemd may own this directory and its label/mode. Keep it intact. */
		result |= remove_tree_contents_except(state->bundle, "signals");
	}
	if (!result && unlink(state_file) < 0 && errno != ENOENT) {
		warn("remove %s", state_file);
		result = 1;
	}

	debug("Cleanup %s", result ? "incomplete" : "complete");
	return result != 0;
}

static pid_t start_network(const NetworkOptions *network, const NetworkState *state)
{
	pid_t parent = getpid();
	autoclose int parent_fd = syscall(SYS_pidfd_open, parent, 0);
	if (parent_fd < 0) {
		warn("open network parent pidfd");
		return -1;
	}
	pid_t monitor = fork();
	if (monitor < 0) {
		warn("fork network monitor");
		return -1;
	}
	if (monitor)
		return monitor;

	int status = 1;
	if (prctl(PR_SET_PDEATHSIG, SIGKILL) < 0) {
		warn("set network monitor parent-death signal");
		goto failed;
	}
	if (getppid() != parent)
		_exit(0);
	/* Supervise a separate job so crashes and fatal errors in setup are
	 * reported too. Crun ignores exit statuses from unrelated children.
	 */
	pid_t job_parent = getpid();
	pid_t job = fork();
	if (job < 0) {
		warn("fork network setup");
		goto failed;
	}
	if (!job) {
		if (prctl(PR_SET_PDEATHSIG, SIGKILL) < 0) {
			warn("set network setup parent-death signal");
			_exit(1);
		}
		if (getppid() != job_parent)
			_exit(0);
		int result = network_setup(network, state);
		if (!result)
			debug("Network setup complete");
		_exit(result != 0);
	}
	status = wait_child(job);
	if (!status)
		_exit(0);
	if (status < 0)
		warn("wait for network setup");
failed:
	warnx("QM network setup failed (status %d); stopping container startup", status);
	/* The parent may already be crun, which forwards catchable signals to
	 * PID 1. SIGKILL ensures a failed job aborts startup even before crun
	 * has created the container. The service's ExecStopPost cleans up.
	 */
	if (syscall(SYS_pidfd_send_signal, parent_fd, SIGKILL, NULL, 0) < 0 &&
	    errno != ESRCH)
		warn("stop container after network setup failure");
	_exit(1);
}

static int setup(const Config *configuration, json_object *config, bool *state_created,
		 pid_t *network_pid)
{
	debug("Preparing runtime directory %s", opt_runtime_dir);
	ensure_private_directory(opt_runtime_dir);
	autofree char *netns = join_path(opt_runtime_dir, "netns");
	/* Do not claim a pre-existing pin, even when it is only an empty file. */
	struct stat st;
	if (lstat(netns, &st) == 0) {
		errno = EEXIST;
		warn("create %s", netns);
		return 1;
	}
	if (errno != ENOENT) {
		warn("stat %s", netns);
		return 1;
	}
	autostate State *state = xnew(State);
	*state = (State){
		.bundle = xstrdup(opt_runtime_dir),
		.crun_executable = xstrdup(CRUN),
		.crun_root = join_path(opt_runtime_dir, "crun"),
		.container_id = xstrdup(QM_CONTAINER_ID),
		.netns = xstrdup(netns),
	};
	/* Check for conflicts before replacing an earlier cleanup journal. */
	const NetworkOptions network = get_network_options(configuration);
	debug("Checking network resource ownership");
	state->network = network_prepare(&network);
	if (!state->network) {
		warnx("QM network preparation failed");
		return 1;
	}
	debug("Saving cleanup state in %s/%s", opt_runtime_dir, QM_STATE_FILE);
	save_state(state, opt_runtime_dir, true);
	*state_created = true;
	write_bundle(configuration, config);
	debug("Creating network namespace %s", netns);
	bool netns_file_created;
	if (network_create_namespace(netns, &netns_file_created)) {
		if (!netns_file_created) {
			free(state->netns);
			state->netns = NULL;
			save_state(state, opt_runtime_dir, true);
		}
		return 1;
	}

	debug("Setting up network in background: veth=%s address=%s/%u "
	      "gateway=%s nftables=%s",
	      network.veth, network.ip, network.prefix_len, network.gateway,
	      network.nft_table);
	autofree char *state_file = join_path(opt_runtime_dir, QM_STATE_FILE);
	autoclose int state_fd = open(state_file, O_RDONLY | O_CLOEXEC);
	if (state_fd < 0 || TEMP_FAILURE_RETRY(flock(state_fd, LOCK_SH)) < 0) {
		warn("lock network setup state %s", state_file);
		return 1;
	}
	/* Workers inherit the lock; setup closes the parent's copy before
	 * execing crun. No worker PID needs to be persisted.
	 */
	*network_pid = start_network(&network, state->network);
	return *network_pid < 0;
}

static int crun_run(json_object *config)
{
	autofree char *crun_state = join_path(opt_runtime_dir, "crun");
	autofree char *notify_alias = NULL;
	const char *notify_socket = getenv("NOTIFY_SOCKET");
	if (notify_socket && *notify_socket) {
		/* Crun mounts its proxy at NOTIFY_SOCKET inside the container and
		 * appends /notify. Systemd needs /run/systemd/notify for its own
		 * services, so give crun an alias outside that directory. On the
		 * host the alias still resolves to our service manager's socket.
		 */
		if (notify_socket[0] != '/') {
			warnx("NOTIFY_SOCKET must be an absolute filesystem path");
			return 1;
		}
		notify_alias = join_path(opt_runtime_dir, "notify.sock");
		debug("Aliasing host notify socket %s at %s", notify_socket,
		      notify_alias);
		/* Startup may be continuing after incomplete cleanup. */
		if (unlink(notify_alias) < 0 && errno != ENOENT) {
			warn("remove old notify alias %s", notify_alias);
			return 1;
		}
		if (symlink(notify_socket, notify_alias) < 0) {
			warn("create notify alias %s", notify_alias);
			return 1;
		}
		if (setenv("NOTIFY_SOCKET", notify_alias, 1) < 0) {
			warn("set NOTIFY_SOCKET");
			return 1;
		}
	}
	autofree char *console_socket = NULL;
	pid_t console_pid = -1;
	if (json_object_get_boolean(js_get(js_get(config, "process"), "terminal"))) {
		console_socket = join_path(opt_runtime_dir, "console.sock");
		debug("Forwarding container console to stdout");
		console_pid = console_start(console_socket);
		if (console_pid < 0)
			return 1;
	}
	autofreestrvbuilder StrvBuilder argv = {0};
	crun_prefix(&argv, CRUN, crun_state);
	strv_builder_add(&argv, "--cgroup-manager=cgroupfs");
	strv_builder_add(&argv, "run");
	strv_builder_add(&argv, "--bundle");
	strv_builder_add(&argv, opt_runtime_dir);
	if (console_socket) {
		strv_builder_add(&argv, "--console-socket");
		strv_builder_add(&argv, console_socket);
	}
	strv_builder_add(&argv, QM_CONTAINER_ID);
	notify_socket = getenv("NOTIFY_SOCKET");
	debug("Starting container %s with %s (bundle %s, state root %s, "
	      "NOTIFY_SOCKET=%s)",
	      QM_CONTAINER_ID, CRUN, opt_runtime_dir, crun_state,
	      notify_socket ? notify_socket : "(unset)");

	execv(CRUN, argv.strv);
	warn("exec %s", CRUN);
	if (console_pid > 0) {
		kill(console_pid, SIGTERM);
		wait_child(console_pid);
	}

	return 1;
}

static int exec_in_container(void)
{
	autofree char *crun_state = join_path(opt_runtime_dir, "crun");
	autofreestrvbuilder StrvBuilder argv = {0};
	crun_prefix(&argv, CRUN, crun_state);
	strv_builder_add(&argv, "--cgroup-manager=cgroupfs");
	strv_builder_add(&argv, "exec");
	if (isatty(STDIN_FILENO) && isatty(STDOUT_FILENO))
		strv_builder_add(&argv, "--tty");
	strv_builder_add(&argv, QM_CONTAINER_ID);
	for (size_t i = 0; opt_exec_argv[i]; i++)
		strv_builder_add(&argv, opt_exec_argv[i]);

	debug("Executing %s in container %s with %s", opt_exec_argv[0], QM_CONTAINER_ID,
	      CRUN);
	if (!isatty(STDIN_FILENO) || !isatty(STDOUT_FILENO))
		return exec_with_stdio(argv.strv);

	execv(CRUN, argv.strv);
	warn("exec %s", CRUN);

	return 1;
}

static char *cgroup_parent(bool prepare_only)
{
	autofree char *cgroup = get_current_cgroup();

	char *subgroup = strrchr(cgroup, '/');
	if (subgroup && !strcmp(subgroup + 1, SUPERVISOR_CGROUP))
		*subgroup = '\0';
	else if (!prepare_only)
		errx(1,
		     "service requires Delegate=yes and "
		     "DelegateSubgroup=%s",
		     SUPERVISOR_CGROUP);

	if (!prepare_only && (!*cgroup || !strcmp(cgroup, "/")))
		errx(1, "run inside a delegated systemd service");

	return steal_ptr(&cgroup);
}

static void configure_identity(json_object *config, json_object *process,
			       const char *hostname)
{
	const char *timezone = getenv("TZ");
	json_object *old = js_need(process, "env", json_type_array);
	autofreejson json_object *env = js_new_array();
	for (size_t i = 0; i < json_object_array_length(old); i++) {
		json_object *entry = json_object_array_get_idx(old, i);
		const char *value = js_array_string(old, i);
		if (!starts_with(value, "HOSTNAME=") &&
		    !starts_with(value, "container_uuid=") &&
		    (!timezone || !starts_with(value, "TZ=")))
			js_array_add(env, json_object_get(entry));
	}

	autofree char *entry = xasprintf("HOSTNAME=%s", hostname);
	js_array_add(env, js_new_string(entry));

	if (timezone) {
		autofree char *tz = xasprintf("TZ=%s", timezone);
		js_array_add(env, js_new_string(tz));
	}

	js_object_add(process, "env", steal_ptr(&env));
	js_set_string(config, "hostname", hostname);
}

static void configure_machine_id(json_object *process)
{
	json_object *args = js_need(process, "args", json_type_array);
	const char *init = js_array_string(args, 0);
	if (strcmp(init, "/sbin/init") && strcmp(init, "/usr/sbin/init") &&
	    strcmp(init, "/lib/systemd/systemd") &&
	    strcmp(init, "/usr/lib/systemd/systemd"))
		return;

	autofree char *id = read_text_file("/etc/machine-id");
	id[strcspn(id, "\r\n")] = '\0';
	if (strlen(id) != 32 || !string_in_class(id, CHAR_HEX) ||
	    strspn(id, "0") == 32) {
		warnx("invalid host machine ID in /etc/machine-id; "
		      "leaving container machine ID selection to systemd");
		return;
	}

	/* Let systemd write or commit its own machine-id file. A host bind mount
	 * would trigger machine-id-commit without being its expected tmpfs mount.
	 * The last option overrides any machine ID supplied by the base config.
	 */
	autofree char *argument = xasprintf("--machine-id=%s", id);
	js_array_add(args, js_new_string(argument));
}

static json_object *find_mount(json_object *config, const char *destination)
{
	json_object *mounts = js_need(config, "mounts", json_type_array);
	for (size_t i = 0; i < json_object_array_length(mounts); i++) {
		json_object *mount = json_object_array_get_idx(mounts, i);
		if (!strcmp(js_string(mount, "destination"), destination))
			return mount;
	}

	return NULL;
}

static void override_mount_source(json_object *config, const char *destination,
				  const char *source)
{
	if (!source)
		return;

	json_object *mount = find_mount(config, destination);
	if (mount)
		js_set_string(mount, "source", source);
}

static void configure_mounts(json_object *config, const char *files)
{
	const struct {
		const char *destination;
		const char *filename;
	} sources[] = {
		{"/run/.containerenv", "containerenv"},
		{"/run/secrets", "secrets"},
		{"/etc/hostname", "hostname"},
		{"/etc/resolv.conf", "resolv.conf"},
		{"/etc/hosts", "hosts"},
	};

	for (size_t i = 0; i < N_ELEMENTS(sources); i++) {
		autofree char *source = join_path(files, sources[i].filename);
		override_mount_source(config, sources[i].destination, source);
	}

	autofree char *signals = join_path(opt_runtime_dir, "signals");
	override_mount_source(config, "/run/host/qmc-signals", signals);
}

static void configure_seccomp(json_object *linux_config, json_object *process,
			      const char *filename)
{
	if (filename) {
		autofreejson json_object *profile = js_load(filename);
		resolve_seccomp(profile, process);
		js_object_add(linux_config, "seccomp", steal_ptr(&profile));
	}

	if (!js_get(linux_config, "seccomp"))
		errx(1, "base config has no seccomp filter; set seccomp in qmc.conf");
}

static json_object *id_mapping(IdRange range)
{
	autofreejson json_object *mapping = js_new_object();
	js_object_add(mapping, "containerID", js_new_int(0));
	js_object_add(mapping, "hostID", js_new_int(range.start));
	js_object_add(mapping, "size", js_new_int(range.count));

	return steal_ptr(&mapping);
}

static void configure_userns(json_object *linux_config, const Config *configuration)
{
	if (configuration->userns == USERNS_OFF) {
		debug("User namespace detection disabled");
		return;
	}

	IdRange uid = read_subid("/etc", "subuid", QM_SUBID_USER);
	IdRange gid = read_subid("/etc", "subgid", QM_SUBID_USER);
	if (!uid.found && !gid.found) {
		if (configuration->userns == USERNS_REQUIRED)
			errx(1, "%s subordinate ID ranges are required", QM_SUBID_USER);
		debug("No %s subordinate ID ranges; using base namespaces",
		      QM_SUBID_USER);
		return;
	}
	if (!uid.found || !gid.found)
		errx(1, "%s requires both subuid and subgid ranges", QM_SUBID_USER);
	debug("User namespace: uid start=%u count=%u, gid start=%u count=%u", uid.start,
	      uid.count, gid.start, gid.count);

	if (js_get(linux_config, "uidMappings") || js_get(linux_config, "gidMappings"))
		errx(1, "base config already has user namespace mappings");

	json_object *namespaces = js_need(linux_config, "namespaces", json_type_array);
	for (size_t i = 0; i < json_object_array_length(namespaces); i++)
		if (!strcmp(js_string(json_object_array_get_idx(namespaces, i), "type"),
			    "user"))
			errx(1, "base config already has a user namespace");

	autofreejson json_object *user = js_new_object();
	js_set_string(user, "type", "user");
	js_array_add(namespaces, steal_ptr(&user));

	autofreejson json_object *uids = js_new_array();
	js_array_add(uids, id_mapping(uid));
	js_object_add(linux_config, "uidMappings", steal_ptr(&uids));

	autofreejson json_object *gids = js_new_array();
	js_array_add(gids, id_mapping(gid));
	js_object_add(linux_config, "gidMappings", steal_ptr(&gids));
}

static void configure_isolation(json_object *linux_config)
{
	autofree char *parent = cgroup_parent(opt_prepare_only);
	autofree char *payload = join_path(parent, PAYLOAD_CGROUP);
	debug("Container cgroup %s", payload);
	js_set_string(linux_config, "cgroupsPath", payload);

	json_object *namespaces = js_need(linux_config, "namespaces", json_type_array);
	for (size_t i = 0; i < json_object_array_length(namespaces); i++) {
		json_object *entry = json_object_array_get_idx(namespaces, i);
		if (!strcmp(js_string(entry, "type"), "network")) {
			autofree char *netns = join_path(opt_runtime_dir, "netns");
			js_set_string(entry, "path", netns);
			return;
		}
	}

	errx(1, "base config requires a network namespace entry");
}

static void configure_annotations(json_object *config)
{
	json_object *annotations = js_get(config, "annotations");
	autofreejson json_object *clean = js_new_object();
	if (annotations) {
		if (!json_object_is_type(annotations, json_type_object))
			errx(1, "invalid annotations: expected a JSON object");

		json_object_object_foreach (annotations, key, value) {
			if (!starts_with(key, "io.podman.") &&
			    !starts_with(key, "org.systemd.property.") &&
			    strcmp(key, "org.opencontainers.image.stopSignal"))
				js_object_add(clean, key, json_object_get(value));
		}
	}

	js_set_string(clean, "io.container.manager", "qmc");
	js_object_add(config, "annotations", steal_ptr(&clean));
}

static json_object *create_config(const Config *configuration)
{
	debug("Loading OCI configuration from %s", configuration->base_config);
	autofreejson json_object *config = js_load(configuration->base_config);
	if (configuration->rootfs)
		js_set_string(js_need(config, "root", json_type_object), "path",
			      configuration->rootfs);

	json_object *linux_config = js_need(config, "linux", json_type_object);
	json_object *process = js_need(config, "process", json_type_object);
	if (js_string(js_need(config, "root", json_type_object), "path")[0] != '/')
		errx(1, "root.path must be absolute");
	configure_oci_policy(config, configuration);

	debug("Configuring seccomp from %s",
	      configuration->seccomp_file ? configuration->seccomp_file : "base config");
	configure_seccomp(linux_config, process, configuration->seccomp_file);
	configure_identity(config, process, configuration->hostname);
	configure_machine_id(process);
	configure_isolation(linux_config);
	configure_userns(linux_config, configuration);
	configure_annotations(config);

	autofree char *files = join_path(opt_runtime_dir, "files");
	configure_mounts(config, files);
	userns_configure_mounts(config, opt_runtime_dir);

	debug("OCI configuration ready: hostname=%s rootfs=%s", configuration->hostname,
	      js_string(js_get(config, "root"), "path"));
	return steal_ptr(&config);
}

static void container_file(const char *base, const char *name, const char *contents,
			   const char *context)
{
	autofree char *filename = join_path(base, name);
	write_text_file(filename, contents);
	set_selinux_label(filename, context);
}

static char *hosts_contents(const char *hosts, const Config *configuration)
{
	const char *hostname = configuration->hostname;
	bool add_container_alias = strcmp(hostname, QM_CONTAINER_ID) != 0;
	return xasprintf("%s\n%s\thost.containers.internal "
			 "host.docker.internal\n%s\t%s%s%s\n",
			 hosts, configuration->gateway, configuration->ip, hostname,
			 add_container_alias ? " " : "",
			 add_container_alias ? QM_CONTAINER_ID : "");
}

static void update_container_file(const char *name, const char *contents)
{
	autofree char *files = join_path(opt_runtime_dir, "files");
	autofree char *filename = join_path(files, name);
	/* Do not create a new file after the container's runtime was removed.
	 */
	autoclose int fd =
		TEMP_FAILURE_RETRY(open(filename, O_WRONLY | O_NOFOLLOW | O_CLOEXEC));
	if (fd < 0) {
		if (errno == ENOENT)
			return;
		err(1, "open %s", filename);
	}

	/* Keep the inode and its SELinux label for the container's bind mount.
	 */
	struct stat st;
	if (fstat(fd, &st) < 0)
		err(1, "stat %s", filename);
	autofree char *padded = NULL;
	size_t length = strlen(contents), write_length = length;
	if (st.st_size > 0 && (uintmax_t)st.st_size > length) {
		if ((uintmax_t)st.st_size > SIZE_MAX)
			errx(1, "%s is too large", filename);
		write_length = st.st_size;
		padded = xmalloc(write_length);
		memcpy(padded, contents, length);
		/* Overwrite the old tail with whitespace in the same write. */
		memset(padded + length, ' ', write_length - length);
	}
	write_all(fd, padded ? padded : contents, write_length);
	if (ftruncate(fd, length) < 0)
		err(1, "truncate %s", filename);
}

static int update_resolv_conf(const Config *configuration)
{
	debug("Updating DNS and hosts files in %s", opt_runtime_dir);
	autofree char *dns = try_read_text_file(configuration->resolv_conf);
	if (!dns && errno != ENOENT)
		err(1, "read %s", configuration->resolv_conf);
	if (dns)
		update_container_file("resolv.conf", dns);

	autofree char *hosts = try_read_text_file("/etc/hosts");
	if (!hosts) {
		if (errno == ENOENT)
			return 0;
		err(1, "read /etc/hosts");
	}

	/* Keep the running container's hostname and addresses even if the
	 * administrator has edited the next launch's configuration.
	 */
	autofree char *hosts_config = join_path(opt_runtime_dir, "files/hosts.conf");
	if (access(hosts_config, F_OK) < 0) {
		if (errno == ENOENT)
			return 0;
		err(1, "access %s", hosts_config);
	}
	autofreeconfig Config *startup =
		configuration_load(QM_DATA_DIR, QM_CONFIG_DIR, hosts_config);
	autofree char *contents = hosts_contents(hosts, startup);
	update_container_file("hosts", contents);
	return 0;
}

static int open_signals_directory(const char *path, bool create)
{
	if (create && mkdir(path, 0755) < 0 && errno != EEXIST)
		err(1, "mkdir %s", path);

	int fd = TEMP_FAILURE_RETRY(
		open(path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
	if (fd < 0) {
		if (!create && errno == ENOENT)
			return -1;
		err(1, "open directory %s", path);
	}
	if (TEMP_FAILURE_RETRY(flock(fd, LOCK_EX)) < 0)
		err(1, "lock directory %s", path);

	struct stat st;
	if (fstat(fd, &st) < 0)
		err(1, "stat %s", path);
	if (st.st_uid != geteuid() || (st.st_mode & 0022))
		errx(1,
		     "%s must be a directory owned and writable only by the current user",
		     path);

	/* A mapped container root must be able to search the read-only bind. */
	if (create && fchmod(fd, 0755) < 0)
		err(1, "chmod %s", path);
	return fd;
}

static int signal_container(void)
{
	if (!opt_clear_signal)
		ensure_private_directory(opt_runtime_dir);
	autofree char *directory = join_path(opt_runtime_dir, "signals");
	autoclose int directory_fd = open_signals_directory(directory, !opt_clear_signal);
	if (directory_fd < 0)
		return 0;

	autofree char *filename = join_path(directory, opt_signal_name);
	if (opt_clear_signal) {
		if (unlink(filename) < 0 && errno != ENOENT)
			err(1, "clear signal %s", opt_signal_name);
		return 0;
	}

	struct stat st;
	if (lstat(filename, &st) == 0) {
		if (!S_ISREG(st.st_mode))
			errx(1, "%s is not a regular signal file", filename);
		return 0;
	}
	if (errno != ENOENT)
		err(1, "stat %s", filename);

	/* Publish a fully labelled marker without replacing an existing one. */
	autofree char *temporary = join_path(directory, ".signal-XXXXXX");
	autoclose int fd = mkostemp(temporary, O_CLOEXEC);
	if (fd < 0)
		err(1, "create signal %s", opt_signal_name);
	if (fchmod(fd, 0644) < 0)
		err(1, "chmod %s", temporary);
	autofree char *context = get_selinux_label(directory);
	set_selinux_label(temporary, context);

	if (link(temporary, filename) < 0 && errno != EEXIST) {
		int saved_errno = errno;
		unlink(temporary);
		errno = saved_errno;
		err(1, "set signal %s", opt_signal_name);
	}
	if (unlink(temporary) < 0)
		err(1, "remove temporary signal %s", temporary);
	return 0;
}

static void label_signals(const char *path, const char *context)
{
	set_selinux_label(path, context);
	if (!context || !*context)
		return;

	DIR *directory = opendir(path);
	if (!directory)
		err(1, "open directory %s", path);
	struct dirent *entry;
	errno = 0;
	while ((entry = readdir(directory))) {
		if (entry->d_name[0] != '.') {
			autofree char *filename = join_path(path, entry->d_name);
			set_selinux_label(filename, context);
		}
		errno = 0;
	}
	if (errno)
		err(1, "read directory %s", path);
	if (closedir(directory) < 0)
		err(1, "close directory %s", path);
}

static void write_container_files(const Config *configuration, json_object *config)
{
	const char *context =
		opt_prepare_only ? NULL
				 : json_object_get_string(
					   js_get(js_get(config, "linux"), "mountLabel"));

	autofree char *signals = join_path(opt_runtime_dir, "signals");
	autoclose int signals_fd = open_signals_directory(signals, true);
	label_signals(signals, context);

	autofree char *files = join_path(opt_runtime_dir, "files");
	ensure_private_directory(files);
	set_selinux_label(files, context);

	autofree char *secrets = join_path(files, "secrets");
	ensure_private_directory(secrets);
	set_selinux_label(secrets, context);

	container_file(files, "containerenv", "", context);

	autofree char *hostname = xasprintf("%s\n", configuration->hostname);
	container_file(files, "hostname", hostname, context);
	autofreejson json_object *hosts_config = js_new_object();
	js_set_string(hosts_config, "hostname", configuration->hostname);
	js_set_string(hosts_config, "ip", configuration->ip);
	js_set_string(hosts_config, "gateway", configuration->gateway);
	js_object_add(hosts_config, "prefix-length",
		      js_new_int(configuration->prefix_length));
	container_file(files, "hosts.conf",
		       json_object_to_json_string_ext(
			       hosts_config,
			       JSON_C_TO_STRING_SPACED | JSON_C_TO_STRING_NOSLASHESCAPE),
		       context);

	autofree char *dns = try_read_text_file(configuration->resolv_conf);
	if (!dns && errno != ENOENT)
		err(1, "read %s", configuration->resolv_conf);
	container_file(files, "resolv.conf", dns ? dns : "", context);
	debug("Resolver source %s: %s", configuration->resolv_conf,
	      dns ? "read" : "missing; wrote empty file");

	autofree char *hosts = read_text_file("/etc/hosts");
	autofree char *contents = hosts_contents(hosts, configuration);
	container_file(files, "hosts", contents, context);
}

static void write_bundle(const Config *configuration, json_object *config)
{
	debug("Writing container files in %s", opt_runtime_dir);
	ensure_private_directory(opt_runtime_dir);
	write_container_files(configuration, config);
	autofree char *crun_state = join_path(opt_runtime_dir, "crun");
	ensure_private_directory(crun_state);

	autofree char *oci_config = join_path(opt_runtime_dir, "config.json");
	debug("Writing OCI bundle configuration %s", oci_config);
	js_save(config, oci_config);
}

static json_object *inspect_settings(const Config *configuration)
{
	autofreejson json_object *result = configuration_serialize(configuration);
	if (!configuration->rootfs) {
		autofreejson json_object *base = js_load(configuration->base_config);
		js_set_string(result, "rootfs",
			      js_string(js_need(base, "root", json_type_object), "path"));
	}
	return steal_ptr(&result);
}

static int inspect(const Config *configuration)
{
	autofreejson json_object *object = NULL;
	if (opt_inspect_oci) {
		autofree char *filename = join_path(opt_runtime_dir, "config.json");
		object = js_load(filename);
	} else {
		object = inspect_settings(configuration);
	}

	json_object *value = object;
	if (opt_inspect_field) {
		bool found;
		if (opt_inspect_field[0] == '/')
			found = json_pointer_get(object, opt_inspect_field, &value) == 0;
		else
			found = json_object_object_get_ex(object, opt_inspect_field,
							  &value);
		if (!found)
			errx(1, "unknown inspection field: %s", opt_inspect_field);
	}

	const char *contents;
	size_t length;
	if (opt_inspect_field && json_object_is_type(value, json_type_string)) {
		contents = json_object_get_string(value);
		length = json_object_get_string_len(value);
	} else {
		contents = json_object_to_json_string_ext(
			value, JSON_C_TO_STRING_PRETTY | JSON_C_TO_STRING_NOSLASHESCAPE);
		if (!contents)
			oom();
		length = strlen(contents);
	}

	write_all(STDOUT_FILENO, contents, length);
	write_all(STDOUT_FILENO, "\n", 1);
	return 0;
}

enum {
	OPTION_RUNTIME_DIR = 1 << 0,
	OPTION_CONFIG = 1 << 1,
	OPTION_VERBOSE = 1 << 2,
	OPTION_PREPARE_ONLY = 1 << 3,
	OPTION_OCI = 1 << 4,
	OPTION_FIELD = 1 << 5,
	OPTION_HELP = 1 << 6,
	OPTION_CLEAR = 1 << 7,

	COMMON_OPTIONS = OPTION_RUNTIME_DIR | OPTION_VERBOSE | OPTION_HELP,
};

typedef struct {
	struct option option;
	const char *argument;
	const char *description;
} OptionInfo;

/* Option values also serve as bits in each command's option set. */
static const OptionInfo options[] = {
	{{"runtime-dir", required_argument, NULL, OPTION_RUNTIME_DIR},
	 "DIR",
	 "Runtime files (default " DEFAULT_RUNTIME_DIR ")\n"
	 "                        RUNTIME_DIRECTORY overrides the default"},
	{{"config", required_argument, NULL, OPTION_CONFIG},
	 "FILE",
	 "Use only this JSON configuration file"},
	{{"verbose", no_argument, NULL, OPTION_VERBOSE},
	 NULL,
	 "Enable launcher and crun debug logging"},
	{{"prepare-only", no_argument, NULL, OPTION_PREPARE_ONLY},
	 NULL,
	 "Write bundle without setup"},
	{{"oci", no_argument, NULL, OPTION_OCI}, NULL, "Inspect the saved OCI bundle"},
	{{"field", required_argument, NULL, OPTION_FIELD},
	 "KEY",
	 "Print one field, as a key or JSON pointer\n"
	 "                        Strings are printed without quotes"},
	{{"help", no_argument, NULL, OPTION_HELP}, NULL, "Show this help"},
	{{"clear", no_argument, NULL, OPTION_CLEAR},
	 NULL,
	 "Clear a previously set signal"},
};

typedef struct {
	Command command;
	const char *name;
	const char *arguments;
	const char *description;
	unsigned options;
	bool internal;
} CommandInfo;

static const CommandInfo commands[] = {
	{
		.command = COMMAND_EXEC,
		.name = "exec",
		.arguments = " [--] COMMAND [ARG...]",
		.description = "Run a command in the running container",
		.options = COMMON_OPTIONS,
	},
	{
		.command = COMMAND_INSPECT,
		.name = "inspect",
		.arguments = "",
		.description = "Show merged settings or saved OCI configuration",
		.options = COMMON_OPTIONS | OPTION_CONFIG | OPTION_OCI | OPTION_FIELD,
	},
	{
		.command = COMMAND_SIGNAL,
		.name = "signal",
		.arguments = " NAME",
		.description = "Set or clear a persistent host signal for QM",
		.options = COMMON_OPTIONS | OPTION_CLEAR,
	},
	{
		.command = COMMAND_LAUNCH,
		.name = "launch",
		.arguments = "",
		.description = "Prepare and start the QM container",
		.options = COMMON_OPTIONS | OPTION_CONFIG | OPTION_PREPARE_ONLY,
		.internal = true,
	},
	{
		.command = COMMAND_CLEANUP,
		.name = "cleanup",
		.arguments = "",
		.description = "Delete container and tear down networking",
		.options = COMMON_OPTIONS,
		.internal = true,
	},
	{
		.command = COMMAND_UPDATE_RESOLV_CONF,
		.name = "update-resolv-conf",
		.arguments = "",
		.description = "Update DNS and hosts files in place",
		.options = COMMON_OPTIONS | OPTION_CONFIG,
		.internal = true,
	},
};

static void usage(FILE *output)
{
	fputs("Usage: qmc COMMAND [OPTIONS]...\n"
	      "       qmc --help\n\n"
	      "Commands:\n",
	      output);
	for (size_t i = 0; i < N_ELEMENTS(commands); i++) {
		if (!commands[i].internal)
			fprintf(output, "  %-22s%s\n", commands[i].name,
				commands[i].description);
	}

	fputs("\nRun 'qmc COMMAND --help' for command-specific options.\n", output);
}

static void command_usage(FILE *output, const CommandInfo *command)
{
	fprintf(output, "Usage: qmc %s [OPTIONS]%s\n\n%s\n\nOptions:\n", command->name,
		command->arguments, command->description);
	for (size_t i = 0; i < N_ELEMENTS(options); i++) {
		const OptionInfo *option = &options[i];
		if (!(command->options & option->option.val))
			continue;

		autofree char *name = xasprintf("--%s%s%s", option->option.name,
						option->argument ? " " : "",
						option->argument ? option->argument : "");
		fprintf(output, "  %-22s%s\n", name, option->description);
	}

	if (command->options & OPTION_CONFIG)
		fprintf(output,
			"\nConfiguration: %s/qmc.conf, %s/qmc.conf.d/*.conf,\n"
			"               %s/qmc.conf, %s/qmc.conf.d/*.conf (in order).\n",
			QM_DATA_DIR, QM_DATA_DIR, QM_CONFIG_DIR, QM_CONFIG_DIR);
}

static void require_absolute_path(const char *option, const char *path)
{
	if (path && path[0] != '/')
		errx(1, "%s must be an absolute path: %s", option, path);
}

static void parse_command_options(const CommandInfo *command, int argc, char **argv)
{
	const char *runtime_dir = getenv("RUNTIME_DIRECTORY");
	if (runtime_dir && *runtime_dir)
		opt_runtime_dir = runtime_dir;

	struct option long_options[N_ELEMENTS(options) + 1] = {0};
	size_t n_options = 0;
	for (size_t i = 0; i < N_ELEMENTS(options); i++) {
		if (command->options & options[i].option.val)
			long_options[n_options++] = options[i].option;
	}

	/* Options follow the subcommand. Stop at the first positional argument,
	 * so options belonging to an exec command are forwarded unchanged.
	 */
	optind = 1;
	int option;
	while ((option = getopt_long(argc, argv, "+", long_options, NULL)) != -1) {
		switch (option) {
		case OPTION_CONFIG:
			opt_config_file = optarg;
			break;
		case OPTION_RUNTIME_DIR:
			opt_runtime_dir = optarg;
			break;
		case OPTION_VERBOSE:
			opt_verbose = true;
			break;
		case OPTION_PREPARE_ONLY:
			opt_prepare_only = true;
			break;
		case OPTION_OCI:
			opt_inspect_oci = true;
			break;
		case OPTION_FIELD:
			opt_inspect_field = optarg;
			break;
		case OPTION_CLEAR:
			opt_clear_signal = true;
			break;
		case OPTION_HELP:
			command_usage(stdout, command);
			exit(0);
		default:
			command_usage(stderr, command);
			exit(2);
		}
	}

	require_absolute_path("--runtime-dir", opt_runtime_dir);
	if (opt_inspect_oci && opt_config_file)
		errx(2, "--oci cannot be combined with --config");

	if (command->command == COMMAND_EXEC) {
		opt_exec_argv = argv + optind;
		if (!opt_exec_argv[0] || !*opt_exec_argv[0])
			errx(2, "exec requires a command");
	} else if (command->command == COMMAND_SIGNAL) {
		if (argc - optind != 1)
			errx(2, "signal requires exactly one name");
		opt_signal_name = argv[optind];

		if (!char_in_class(*opt_signal_name, CHAR_ALNUM) ||
		    strlen(opt_signal_name) > NAME_MAX ||
		    !string_in_class(opt_signal_name,
				     CHAR_ALNUM | CHAR_UNDERSCORE | CHAR_DOT | CHAR_DASH))
			errx(2, "invalid signal name: %s", opt_signal_name);
	} else if (optind != argc) {
		errx(2, "%s takes no positional arguments", command->name);
	}
}

static Command parse_options(int argc, char **argv)
{
	if (argc < 2) {
		usage(stderr);
		exit(2);
	}
	if (!strcmp(argv[1], "--help")) {
		usage(stdout);
		exit(0);
	}

	for (size_t i = 0; i < N_ELEMENTS(commands); i++) {
		if (!strcmp(argv[1], commands[i].name)) {
			parse_command_options(&commands[i], argc - 1, argv + 1);
			return commands[i].command;
		}
	}

	errx(2, "unknown command: %s (see qmc --help)", argv[1]);
}

int main(int argc, char **argv)
{
	const Command command = parse_options(argc, argv);

	/* Operations on existing runtime state must work even if the launch
	 * configuration is broken.
	 */
	if (command == COMMAND_EXEC)
		return exec_in_container();
	if (command == COMMAND_CLEANUP)
		return cleanup(opt_runtime_dir);
	if (command == COMMAND_SIGNAL)
		return signal_container();
	if (command == COMMAND_INSPECT && opt_inspect_oci)
		return inspect(NULL);

	autofreeconfig Config *configuration =
		configuration_load(QM_DATA_DIR, QM_CONFIG_DIR, opt_config_file);
	if (command == COMMAND_INSPECT)
		return inspect(configuration);
	opt_verbose |= configuration->verbose;
	if (command == COMMAND_UPDATE_RESOLV_CONF)
		return update_resolv_conf(configuration);

	if (!opt_prepare_only) {
		if (geteuid() != 0)
			errx(1, "launch requires root");
		debug("Checking for pending cleanup in %s", opt_runtime_dir);
		if (cleanup(opt_runtime_dir))
			warnx("cleanup incomplete; continuing startup");
	}

	autofree char *netns = join_path(opt_runtime_dir, "netns");
	if (ns_is_mounted(netns))
		errx(1, "runtime namespace already exists; stop the service or "
			"run qmc cleanup");
	if (opt_prepare_only) {
		autofree char *state_file = join_path(opt_runtime_dir, QM_STATE_FILE);
		struct stat st;
		if (lstat(state_file, &st) == 0)
			errx(1, "cleanup state already exists; run qmc cleanup");
		if (errno != ENOENT)
			err(1, "stat %s", state_file);
	}

	autofreejson json_object *config = create_config(configuration);
	if (opt_prepare_only) {
		write_bundle(configuration, config);
		debug("Bundle preparation complete");
		return 0;
	}

	bool state_created = false;
	pid_t network_pid = -1;
	int status = setup(configuration, config, &state_created, &network_pid);
	autofree char *mapped_rootfs = NULL;
	if (!status) {
		mapped_rootfs = userns_mount_rootfs(config);
		status = crun_run(config);
	}
	if (mapped_rootfs && umount(mapped_rootfs) < 0)
		err(1, "unmount private rootfs before cleanup");

	/* A successful launch execs crun. On a local failure, cancel the job
	 * before cleanup waits for the shared lock held by its descendants.
	 */
	if (network_pid > 0) {
		kill(network_pid, SIGKILL);
		wait_child(network_pid);
	}
	if (state_created)
		cleanup(opt_runtime_dir);

	return status;
}
