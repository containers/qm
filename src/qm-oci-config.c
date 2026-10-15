/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#define _GNU_SOURCE
#include "qm-oci-config.h"
#include "qm-utils.h"

#include <err.h>
#include <errno.h>
#include <fts.h>
#include <glob.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <systemd/sd-device.h>

static json_object *ensure_object(json_object *parent, const char *name)
{
	if (!js_get(parent, name))
		js_object_add(parent, name, js_new_object());

	return js_need(parent, name, json_type_object);
}

static json_object *ensure_array(json_object *parent, const char *name)
{
	if (!js_get(parent, name))
		js_object_add(parent, name, js_new_array());

	return js_need(parent, name, json_type_array);
}

static void remove_path(json_object *array, const char *key, const char *path)
{
	if (!array)
		return;

	for (size_t i = json_object_array_length(array); i > 0; i--) {
		json_object *item = json_object_array_get_idx(array, i - 1);
		if (!strcmp(js_string(item, key), path))
			json_object_array_del_idx(array, i - 1, 1);
	}
}

/* Only remove an exact allow rule when no remaining OCI device needs it.
 * Broad rules and deny rules belong to the base policy and are retained.
 */
static void remove_device_rules(json_object *linux_config, json_object *removed)
{
	json_object *devices = js_get(linux_config, "devices");
	int64_t device_major = json_object_get_int64(js_get(removed, "major"));
	int64_t device_minor = json_object_get_int64(js_get(removed, "minor"));
	const char *type = js_string(removed, "type");

	for (size_t i = 0; devices && i < json_object_array_length(devices); i++) {
		json_object *other = json_object_array_get_idx(devices, i);
		if (!strcmp(js_string(other, "type"), type) &&
		    json_object_get_int64(js_get(other, "major")) == device_major &&
		    json_object_get_int64(js_get(other, "minor")) == device_minor)
			return;
	}

	json_object *rules = js_get(js_get(linux_config, "resources"), "devices");
	for (size_t i = rules ? json_object_array_length(rules) : 0; i > 0; i--) {
		json_object *rule = json_object_array_get_idx(rules, i - 1);
		json_object *rule_type = js_get(rule, "type");

		if (json_object_get_boolean(js_get(rule, "allow")) && rule_type &&
		    !strcmp(json_object_get_string(rule_type), type) &&
		    js_get(rule, "major") && js_get(rule, "minor") &&
		    json_object_get_int64(js_get(rule, "major")) == device_major &&
		    json_object_get_int64(js_get(rule, "minor")) == device_minor)
			json_object_array_del_idx(rules, i - 1, 1);
	}
}

static void remove_device(json_object *linux_config, const char *destination)
{
	json_object *devices = js_get(linux_config, "devices");
	for (size_t i = devices ? json_object_array_length(devices) : 0; i > 0; i--) {
		json_object *device = json_object_array_get_idx(devices, i - 1);
		if (strcmp(js_string(device, "path"), destination))
			continue;

		autofreejson json_object *removed = json_object_get(device);
		json_object_array_del_idx(devices, i - 1, 1);
		remove_device_rules(linux_config, removed);
	}
}

static void add_device_rule(json_object *linux_config, const struct stat *st)
{
	json_object *rules =
		ensure_array(ensure_object(linux_config, "resources"), "devices");

	autofreejson json_object *rule = js_new_object();
	js_object_add(rule, "allow", js_new_bool(true));
	js_set_string(rule, "type", S_ISCHR(st->st_mode) ? "c" : "b");
	js_object_add(rule, "major", js_new_int(major(st->st_rdev)));
	js_object_add(rule, "minor", js_new_int(minor(st->st_rdev)));
	js_set_string(rule, "access", "rwm");

	js_array_add(rules, steal_ptr(&rule));
}

static void add_device(json_object *linux_config, const char *destination,
		       const struct stat *st)
{
	autofreejson json_object *device = js_new_object();
	js_set_string(device, "path", destination);
	js_set_string(device, "type", S_ISCHR(st->st_mode) ? "c" : "b");
	js_object_add(device, "major", js_new_int(major(st->st_rdev)));
	js_object_add(device, "minor", js_new_int(minor(st->st_rdev)));
	js_object_add(device, "fileMode", js_new_int(st->st_mode & 07777));
	js_object_add(device, "uid", js_new_int(st->st_uid));
	js_object_add(device, "gid", js_new_int(st->st_gid));

	js_array_add(ensure_array(linux_config, "devices"), steal_ptr(&device));
	add_device_rule(linux_config, st);
}

typedef struct {
	const PathOperation *operation;
	char *source;
	char *destination;
	bool remove;
} ResolvedPath;

static void resolved_path_free(void *data)
{
	ResolvedPath *path = data;
	free(path->source);
	free(path->destination);
	free(path);
}

static void resolve_path(PtrArray *paths, const PathOperation *operation,
			 const char *source, const char *destination, bool remove)
{
	autofree char *normalized = canonicalize_path(destination);
	if (reserved_mount_destination(normalized))
		errx(1, "reserved mount destination: %s", normalized);

	ResolvedPath *path = xnew(ResolvedPath);
	*path = (ResolvedPath){
		.operation = operation,
		.source = source ? canonicalize_path(source) : NULL,
		.destination = steal_ptr(&normalized),
		.remove = remove,
	};

	for (size_t i = 0; i < paths->length; i++) {
		ResolvedPath *previous = paths->items[i];
		if (!strcmp(previous->destination, path->destination)) {
			resolved_path_free(previous);
			paths->items[i] = path;
			return;
		}
	}

	ptr_array_add(paths, path);
}

static int compare_device_paths(const FTSENT **a, const FTSENT **b)
{
	return strcmp((*a)->fts_name, (*b)->fts_name);
}

static bool expand_device_directory(PtrArray *paths, const PathOperation *operation,
				    const char *source, const char *destination)
{
	autofree char *root = xstrdup(source);
	char *roots[] = {root, NULL};
	FTS *tree = fts_open(roots, FTS_PHYSICAL | FTS_COMFOLLOW | FTS_NOCHDIR,
			     compare_device_paths);
	if (!tree)
		err(1, "fts_open %s", source);

	bool found = false;
	for (;;) {
		errno = 0;
		FTSENT *entry = fts_read(tree);
		if (!entry) {
			if (errno)
				err(1, "fts_read %s", source);
			break;
		}

		if (entry->fts_info == FTS_ERR || entry->fts_info == FTS_DNR ||
		    entry->fts_info == FTS_NS)
			errx(1, "%s: %s", entry->fts_path, strerror(entry->fts_errno));

		/* Do not follow symlinks inside a directory or include ordinary files. */
		if (entry->fts_info == FTS_SL || entry->fts_info == FTS_SLNONE ||
		    (!S_ISCHR(entry->fts_statp->st_mode) &&
		     !S_ISBLK(entry->fts_statp->st_mode)))
			continue;

		autofree char *target =
			join_path(destination, entry->fts_path + strlen(source));
		resolve_path(paths, operation, entry->fts_path, target, false);
		found = true;
	}

	if (fts_close(tree) < 0)
		err(1, "fts_close %s", source);

	return found;
}

static char *device_destination(const PathOperation *operation, const char *source,
				bool pattern)
{
	if (!strcmp(operation->source, operation->destination))
		return xstrdup(source);
	if (!pattern)
		return xstrdup(operation->destination);

	/* Remap the tree below the source's first wildcard component. */
	const char *wildcard = strpbrk(operation->source, "*?[");
	const char *prefix_end =
		memrchr(operation->source, '/', wildcard - operation->source + 1);
	return join_path(operation->destination,
			 source + (prefix_end - operation->source) + 1);
}

static void expand_devices(PtrArray *paths, const PathOperation *operation)
{
	/* Also remove an old mount/node at the directory or pattern destination. */
	resolve_path(paths, operation, NULL, operation->destination, true);

	glob_t matches = {0};
	int result = glob(operation->source, GLOB_ERR | GLOB_NOESCAPE | GLOB_NOCHECK,
			  NULL, &matches);
	if (result == GLOB_NOSPACE)
		oom();
	if (result != 0 && result != GLOB_NOMATCH)
		err(1, "glob %s", operation->source);

	bool pattern = matches.gl_flags & GLOB_MAGCHAR;
	bool found = false;
	for (size_t i = 0; i < matches.gl_pathc; i++) {
		const char *source = matches.gl_pathv[i];
		autofree char *destination =
			device_destination(operation, source, pattern);
		struct stat st;
		int stat_result = stat(source, &st);

		/* Defer individual-device validation until after resolving expanded
		 * destinations, since a later selection may replace this request.
		 */
		if (!pattern && (stat_result < 0 || !S_ISDIR(st.st_mode))) {
			resolve_path(paths, operation, source, destination, false);
			found = true;
			continue;
		}

		if (stat_result < 0) {
			if (operation->optional && errno == ENOENT)
				continue;
			err(1, "stat %s", source);
		}

		if (S_ISDIR(st.st_mode)) {
			found |= expand_device_directory(paths, operation, source,
							 destination);
		} else if (S_ISCHR(st.st_mode) || S_ISBLK(st.st_mode)) {
			resolve_path(paths, operation, source, destination, false);
			found = true;
		}
	}
	globfree(&matches);

	if (!found && !operation->optional)
		errx(1, "no devices found in %s", operation->source);
}

static bool device_on_seat(sd_device *device, const char *seat)
{
	/* Input and sound nodes can inherit membership from a tagged parent.
	 * The nearest tagged device determines membership, including reassigned
	 * subtrees below another seat's parent.
	 */
	for (;;) {
		int r = sd_device_has_current_tag(device, "seat");
		if (r < 0)
			errx(1, "reading device tags for %s: %s", seat, strerror(-r));
		if (r > 0) {
			const char *name = NULL;
			r = sd_device_get_property_value(device, "ID_SEAT", &name);
			if (r < 0 && r != -ENOENT)
				errx(1, "reading device seat for %s: %s", seat,
				     strerror(-r));

			return !strcmp(name && *name ? name : "seat0", seat);
		}

		r = sd_device_get_parent(device, &device);
		if (r == -ENOENT)
			return false;
		if (r < 0)
			errx(1, "reading device parent for %s: %s", seat, strerror(-r));
	}
}

static sd_device_enumerator *device_enumerator_new(const char *seat)
{
	sd_device_enumerator *enumerator;
	int r = sd_device_enumerator_new(&enumerator);
	if (r < 0)
		errx(1, "creating device enumerator for %s: %s", seat, strerror(-r));

	r = sd_device_enumerator_allow_uninitialized(enumerator);
	if (r < 0)
		errx(1, "configuring device enumerator for %s: %s", seat, strerror(-r));

	return enumerator;
}

static void expand_seat(PtrArray *paths, const PathOperation *operation)
{
	const char *seat = operation->seat;
	sd_device_enumerator *seats = device_enumerator_new(seat);
	int r = sd_device_enumerator_add_match_tag(seats, "seat");
	if (r < 0)
		errx(1, "selecting seat devices for %s: %s", seat, strerror(-r));

	bool found = false;
	for (sd_device *parent = sd_device_enumerator_get_device_first(seats); parent;
	     parent = sd_device_enumerator_get_device_next(seats)) {
		if (!device_on_seat(parent, seat))
			continue;

		sd_device_enumerator *children = device_enumerator_new(seat);
		r = sd_device_enumerator_add_match_parent(children, parent);
		if (r < 0)
			errx(1, "selecting device children for %s: %s", seat,
			     strerror(-r));

		for (sd_device *device = sd_device_enumerator_get_device_first(children);
		     device; device = sd_device_enumerator_get_device_next(children)) {
			const char *name;
			r = sd_device_get_devname(device, &name);
			if (r == -ENOENT)
				continue;
			if (r < 0)
				errx(1, "reading device node for %s: %s", seat,
				     strerror(-r));
			if (!device_on_seat(device, seat))
				continue;

			resolve_path(paths, operation, name, name, false);
			found = true;
		}
		sd_device_enumerator_unref(children);
	}
	sd_device_enumerator_unref(seats);

	if (!found && !operation->optional)
		errx(1, "no devices found for seat %s", seat);
}

static bool same_path_request(const PathOperation *a, const PathOperation *b)
{
	if (a->seat || b->seat)
		return a->seat && b->seat && !strcmp(a->seat, b->seat);

	return !strcmp(a->destination, b->destination);
}

static void resolve_path_operations(PtrArray *resolved, const PtrArray *operations)
{
	/* Reserve the first position of each destination, preserving mount order. */
	for (size_t i = 0; i < operations->length; i++) {
		const PathOperation *operation = operations->items[i];
		if (!operation->seat)
			resolve_path(resolved, operation, NULL, operation->destination,
				     true);
	}

	/* Skip replaced requests before probing their sources, then expand the
	 * surviving requests in load order so later entries override discovered nodes.
	 */
	for (size_t i = 0; i < operations->length; i++) {
		const PathOperation *operation = operations->items[i];
		size_t j;
		for (j = i + 1; j < operations->length; j++) {
			const PathOperation *later = operations->items[j];
			if (same_path_request(later, operation))
				break;
		}
		if (j < operations->length)
			continue;

		if (operation->seat) {
			if (!operation->remove)
				expand_seat(resolved, operation);
			continue;
		}

		if (operation->device && !operation->remove)
			expand_devices(resolved, operation);
		else
			resolve_path(resolved, operation, operation->source,
				     operation->destination, operation->remove);
	}
}

static void configure_paths(json_object *oci, const Config *config)
{
	if (!config->mounts.length && !config->devices.length)
		return;

	/* Merge each config list before applying policy. Device entries take
	 * precedence over mounts, regardless of which drop-in supplied them.
	 */
	PtrArray resolved = {0};
	resolve_path_operations(&resolved, &config->mounts);
	resolve_path_operations(&resolved, &config->devices);

	json_object *mounts = js_need(oci, "mounts", json_type_array);
	json_object *linux_config = js_need(oci, "linux", json_type_object);

	/* Remove base device nodes/rules before adding any new access rules. */
	for (size_t i = 0; i < resolved.length; i++) {
		const ResolvedPath *path = resolved.items[i];
		remove_device(linux_config, path->destination);
	}

	for (size_t i = 0; i < resolved.length; i++) {
		const ResolvedPath *path = resolved.items[i];
		const PathOperation *operation = path->operation;
		const char *destination = path->destination;
		const char *source = path->source;
		bool remove = path->remove;
		bool device = operation->device;
		struct stat st;

		if (!remove && (device || operation->optional)) {
			if (stat(source, &st) < 0) {
				if (operation->optional && errno == ENOENT)
					remove = true;
				else
					err(1, "stat %s", source);
			}

			if (!remove && device && !S_ISCHR(st.st_mode) &&
			    !S_ISBLK(st.st_mode))
				errx(1, "%s is not a character or block device", source);
		}

		if (remove) {
			remove_path(mounts, "destination", destination);
			continue;
		}

		if (device) {
			remove_path(mounts, "destination", destination);
			add_device(linux_config, destination, &st);
			continue;
		}

		autofreejson json_object *mount = js_new_object();
		js_set_string(mount, "destination", destination);
		js_set_string(mount, "source", source);
		js_set_string(mount, "type", "bind");

		autofreejson json_object *options = js_new_array();
		for (size_t j = 0; j < operation->options.length; j++)
			js_array_add(options, js_new_string(operation->options.items[j]));

		js_array_add(options, js_new_string("rbind"));
		js_array_add(options, js_new_string("rprivate"));
		js_object_add(mount, "options", steal_ptr(&options));

		/* Replace in place so parent mounts stay before their children. */
		bool replaced = false;
		for (size_t j = 0; j < json_object_array_length(mounts);) {
			json_object *old = json_object_array_get_idx(mounts, j);
			if (strcmp(js_string(old, "destination"), destination)) {
				j++;
			} else if (!replaced) {
				json_object_array_put_idx(mounts, j++,
							  json_object_get(mount));
				replaced = true;
			} else {
				json_object_array_del_idx(mounts, j, 1);
			}
		}

		if (!replaced) {
			/* New parent mounts must precede existing children too, such as
			 * /etc before the generated hostname, hosts and resolver binds.
			 */
			size_t index, length = strlen(destination);
			for (index = 0; index < json_object_array_length(mounts); index++) {
				const char *child = js_string(
					json_object_array_get_idx(mounts, index), "destination");
				if (starts_with(child, destination) && child[length] == '/')
					break;
			}
			js_array_insert(mounts, index, json_object_get(mount));
		}
	}

	ptr_array_clear(&resolved, resolved_path_free);
}

static void update_capability_set(json_object *set, const CapabilityOperation *operation)
{
	const char *name = operation->name;
	bool all = !strcmp(name, "all");

	if (operation->remove) {
		for (size_t i = json_object_array_length(set); i > 0; i--)
			if (all || !strcmp(js_array_string(set, i - 1), name))
				json_object_array_del_idx(set, i - 1, 1);
		return;
	}

	if (all) {
		for (size_t i = 0; capability_names[i]; i++)
			if (!js_contains(set, capability_names[i]))
				js_array_add(set, js_new_string(capability_names[i]));
	} else if (!js_contains(set, name)) {
		js_array_add(set, js_new_string(name));
	}
}

static void configure_capabilities(json_object *oci, const Config *config)
{
	if (!config->capabilities.length)
		return;

	json_object *caps =
		ensure_object(js_need(oci, "process", json_type_object), "capabilities");
	const char *const sets[] = {"bounding", "effective", "permitted", "inheritable",
				    "ambient"};

	for (size_t i = 0; i < config->capabilities.length; i++) {
		const CapabilityOperation *operation = config->capabilities.items[i];

		for (size_t j = 0; j < N_ELEMENTS(sets); j++) {
			/* Add to the three normal sets; remove from all five. */
			if (!operation->remove && j >= 3)
				continue;

			json_object *set = js_get(caps, sets[j]);
			if (!operation->remove)
				set = ensure_array(caps, sets[j]);
			if (!set)
				continue;

			update_capability_set(set, operation);
		}
	}
}

void configure_oci_policy(json_object *oci, const Config *config)
{
	json_object *linux_config = js_need(oci, "linux", json_type_object);
	if (config->memory_max_set) {
		json_object *memory =
			ensure_object(ensure_object(linux_config, "resources"), "memory");
		js_object_add(memory, "limit", js_new_int(config->memory_max));
	}

	configure_capabilities(oci, config);

	const char *const path_lists[] = {"maskedPaths", "readonlyPaths"};
	for (size_t i = 0; i < config->unmask.length; i++) {
		const char *path = config->unmask.items[i];
		for (size_t j = 0; j < N_ELEMENTS(path_lists); j++) {
			json_object *paths = js_get(linux_config, path_lists[j]);
			if (!paths)
				continue;

			for (size_t k = json_object_array_length(paths); k > 0; k--)
				if (!strcmp(path, "ALL") ||
				    !strcmp(path, js_array_string(paths, k - 1)))
					json_object_array_del_idx(paths, k - 1, 1);
		}
	}

	configure_paths(oci, config);
}
