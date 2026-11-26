/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */
#include "qm-userns.h"
#include "qm-utils.h"

void userns_configure_mounts(json_object *config, const char *runtime_dir)
{
	if (!js_get(js_get(config, "linux"), "uidMappings"))
		return;
	json_object *mounts = js_get_array(config, "mounts");
	for (size_t i = 0; i < js_array_len(mounts); i++) {
		json_object *entry = js_array_get_object(mounts, i);
		const char *source = js_get_string_maybe(entry, "source");
		if (!streq(js_get_string(entry, "type"), "bind") || !source)
			continue;
		/* Persistent trees are already shifted on disk. Only qmc's generated
		 * files and host-owned signal state need a translated runtime mount.
		 */
		if (!path_starts_with(source, runtime_dir) || streq(source, runtime_dir))
			continue;
		json_object *options = js_get_array(entry, "options");
		bool mapped = false;
		for (size_t j = 0; j < js_array_len(options); j++) {
			const char *option = js_array_get_string(options, j);
			mapped |= starts_with(option, "idmap") ||
				  starts_with(option, "ridmap");
		}
		if (!mapped)
			js_array_add_string(options, "idmap");
	}
}
