/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */
#define _GNU_SOURCE
#include "qm-userns.h"
#include "qm-utils.h"
#include <err.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/mount.h>
#include <sched.h>
#include <signal.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <sys/wait.h>

static void write_mapping(pid_t pid, json_object *mappings, const char *name)
{
	autofree char *path = xasprintf("/proc/%d/%s", pid, name);
	autofree char *text = xstrdup("");
	for (size_t i = 0; i < json_object_array_length(mappings); i++) {
		json_object *mapping = json_object_array_get_idx(mappings, i);
		char *next = xasprintf(
			"%s%lld %lld %lld\n", text,
			(long long)json_object_get_int64(js_get(mapping, "containerID")),
			(long long)json_object_get_int64(js_get(mapping, "hostID")),
			(long long)json_object_get_int64(js_get(mapping, "size")));
		free(text);
		text = next;
	}
	write_text_file(path, text);
}

void userns_configure_mounts(json_object *config, const char *runtime_dir)
{
	if (!js_get(js_get(config, "linux"), "uidMappings"))
		return;
	json_object *mounts = js_need(config, "mounts", json_type_array);
	for (size_t i = 0; i < json_object_array_length(mounts); i++) {
		json_object *entry = json_object_array_get_idx(mounts, i);
		const char *destination = js_string(entry, "destination");
		const char *source = json_object_get_string(js_get(entry, "source"));
		if (strcmp(js_string(entry, "type"), "bind") || !source)
			continue;
		/* QM's persistent state and generated private files remain unshifted
		 * on disk, so switching userns off again does not change ownership. */
		if (strcmp(destination, "/etc") && strcmp(destination, "/var") &&
		    strcmp(destination, "/var/tmp") &&
		    !(starts_with(source, runtime_dir) &&
		      source[strlen(runtime_dir)] == '/'))
			continue;
		json_object *options = js_need(entry, "options", json_type_array);
		bool mapped = false;
		for (size_t j = 0; j < json_object_array_length(options); j++) {
			const char *option = json_object_get_string(
				json_object_array_get_idx(options, j));
			mapped |= starts_with(option, "idmap") ||
				  starts_with(option, "ridmap");
		}
		if (!mapped)
			js_array_add(options, js_new_string("idmap"));
	}
}

char *userns_mount_rootfs(json_object *config)
{
	json_object *linux_config = js_get(config, "linux");
	if (!js_get(linux_config, "uidMappings"))
		return NULL;
	pid_t parent = getpid();
	pid_t child = fork();
	if (child < 0)
		err(1, "fork mount user namespace");
	if (!child) {
		if (unshare(CLONE_NEWUSER) < 0 || prctl(PR_SET_PDEATHSIG, SIGKILL) < 0 ||
		    getppid() != parent)
			_exit(1);
		raise(SIGSTOP);
		_exit(0);
	}
	int status;
	if (TEMP_FAILURE_RETRY(waitpid(child, &status, WUNTRACED)) < 0 ||
	    !WIFSTOPPED(status))
		errx(1, "create mount user namespace");
	write_mapping(child, js_need(linux_config, "uidMappings", json_type_array),
		      "uid_map");
	write_mapping(child, js_need(linux_config, "gidMappings", json_type_array),
		      "gid_map");
	autofree char *ns_path = xasprintf("/proc/%d/ns/user", child);
	autoclose int userns = open(ns_path, O_RDONLY | O_CLOEXEC);
	kill(child, SIGKILL);
	wait_child(child);
	if (userns < 0)
		err(1, "open mount user namespace");
	if (unshare(CLONE_NEWNS) < 0 ||
	    mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) < 0)
		err(1, "make rootfs mount namespace private");
	json_object *root = js_get(config, "root");
	autoclose int tree = syscall(SYS_open_tree, AT_FDCWD, js_string(root, "path"),
				     OPEN_TREE_CLONE | OPEN_TREE_CLOEXEC);
	if (tree < 0)
		err(1, "clone rootfs mount");
	struct mount_attr attr = {.attr_set = MOUNT_ATTR_IDMAP, .userns_fd = userns};
	if (syscall(SYS_mount_setattr, tree, "", AT_EMPTY_PATH, &attr, sizeof(attr)) < 0)
		err(1, "map rootfs ownership (filesystem must support ID mapped mounts)");
	/* Keep the original searchable ancestors: crun resolves the root path
	 * after entering the payload userns. The private /run/qm directory is
	 * deliberately inaccessible there. This mount affects only our namespace. */
	autofree char *path = xstrdup(js_string(root, "path"));
	if (syscall(SYS_move_mount, tree, "", AT_FDCWD, path, MOVE_MOUNT_F_EMPTY_PATH) <
	    0)
		err(1, "attach ID mapped rootfs");
	return steal_ptr(&path);
}
