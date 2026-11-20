/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */
#include "qm-userns.h"
#include "qm-utils.h"
#include <string.h>

void userns_configure_mounts(json_object *config, const char *runtime_dir)
{
	if (!js_get(js_get(config, "linux"), "uidMappings"))
		return;
	json_object *mounts = js_need(config, "mounts", json_type_array);
	for (size_t i = 0; i < json_object_array_length(mounts); i++) {
		json_object *entry = json_object_array_get_idx(mounts, i);
		const char *source = json_object_get_string(js_get(entry, "source"));
		if (strcmp(js_string(entry, "type"), "bind") || !source)
			continue;
		/* Persistent trees are already shifted on disk. Only qmc's generated
		 * files and host-owned signal state need a translated runtime mount.
		 */
		if (!(starts_with(source, runtime_dir) &&
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
