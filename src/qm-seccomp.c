/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#include "qm-seccomp.h"
#include "qm-utils.h"

#include <err.h>
#include <string.h>
#include <sys/utsname.h>

typedef struct {
	const char *kernel_name;
	const char *containers_name;
	const char *seccomp_name;
} Architecture;

static const Architecture *native_arch(void)
{
	static const Architecture architectures[] = {
		{"x86_64", "amd64", "SCMP_ARCH_X86_64"},
		{"aarch64", "arm64", "SCMP_ARCH_AARCH64"},
		{"i686", "x86", "SCMP_ARCH_X86"},
		{"armv7l", "arm", "SCMP_ARCH_ARM"},
		{"ppc64le", "ppc64le", "SCMP_ARCH_PPC64LE"},
		{"s390x", "s390x", "SCMP_ARCH_S390X"},
		{"riscv64", "riscv64", "SCMP_ARCH_RISCV64"},
	};

	struct utsname host;
	if (uname(&host) < 0)
		err(1, "uname");

	for (size_t i = 0; i < N_ELEMENTS(architectures); i++)
		if (!strcmp(host.machine, architectures[i].kernel_name))
			return &architectures[i];

	errx(1, "unsupported seccomp architecture: %s", host.machine);
}

static bool seccomp_condition_matches(json_object *condition, json_object *caps,
				      const char *arch, bool include)
{
	if (!condition)
		return true;
	if (!json_object_is_type(condition, json_type_object))
		errx(1, "invalid seccomp condition");

	json_object_object_foreach (condition, key, value) {
		if (strcmp(key, "arches") && strcmp(key, "caps"))
			errx(1, "unsupported seccomp condition: %s", key);
		if (!json_object_is_type(value, json_type_array))
			errx(1, "invalid seccomp condition: %s", key);
	}

	json_object *arches = js_get(condition, "arches");
	if (arches && json_object_array_length(arches) &&
	    js_contains(arches, arch) != include)
		return false;

	json_object *required = js_get(condition, "caps");
	if (required)
		for (size_t i = 0; i < json_object_array_length(required); i++)
			if (js_contains(caps, js_array_string(required, i)) != include)
				return false;

	return true;
}

void resolve_seccomp(json_object *profile, json_object *process)
{
	const Architecture *arch = native_arch();
	json_object *caps = js_get(js_get(process, "capabilities"), "bounding");

	json_object *map = js_get(profile, "archMap");
	if (map) {
		if (!json_object_is_type(map, json_type_array))
			errx(1, "invalid seccomp archMap");

		autofreejson json_object *architectures = js_new_array();
		js_array_add(architectures, js_new_string(arch->seccomp_name));
		for (size_t i = 0; i < json_object_array_length(map); i++) {
			json_object *entry = json_object_array_get_idx(map, i);
			if (strcmp(js_string(entry, "architecture"), arch->seccomp_name))
				continue;

			json_object *sub =
				js_need(entry, "subArchitectures", json_type_array);
			for (size_t j = 0; j < json_object_array_length(sub); j++)
				js_array_add(architectures,
					     json_object_get(
						     json_object_array_get_idx(sub, j)));
		}

		js_object_add(profile, "architectures", steal_ptr(&architectures));
		json_object_object_del(profile, "archMap");
	}

	if (js_get(profile, "defaultErrno") && !js_get(profile, "defaultErrnoRet"))
		errx(1, "seccomp defaultErrno requires numeric defaultErrnoRet");
	json_object_object_del(profile, "defaultErrno");

	json_object *rules = js_need(profile, "syscalls", json_type_array);
	autofreejson json_object *filtered = js_new_array();
	for (size_t i = 0; i < json_object_array_length(rules); i++) {
		json_object *rule = json_object_array_get_idx(rules, i);
		if (!seccomp_condition_matches(js_get(rule, "includes"), caps,
					       arch->containers_name, true) ||
		    !seccomp_condition_matches(js_get(rule, "excludes"), caps,
					       arch->containers_name, false))
			continue;

		if (js_get(rule, "errno") && !js_get(rule, "errnoRet"))
			errx(1, "seccomp errno requires numeric errnoRet");

		json_object_object_del(rule, "includes");
		json_object_object_del(rule, "excludes");
		json_object_object_del(rule, "comment");
		json_object_object_del(rule, "errno");
		js_array_add(filtered, json_object_get(rule));
	}

	js_object_add(profile, "syscalls", steal_ptr(&filtered));
}
