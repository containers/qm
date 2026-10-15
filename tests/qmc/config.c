/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#include "qm-config.h"
#include "qm-oci-config.h"
#include "qm-utils.h"

#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
	const char *oci_base = NULL;
	if (argc >= 3 && !strcmp(argv[1], "--oci")) {
		oci_base = argv[2];
		argc -= 2;
		argv += 2;
	}

	if (argc != 3 && argc != 4)
		return 2;
	autofreeconfig Config *config =
		configuration_load(argv[1], argv[2], argc == 4 ? argv[3] : NULL);
	autofreejson json_object *result = NULL;
	if (oci_base) {
		result = js_load(oci_base);
		configure_oci_policy(result, config);
	} else {
		result = configuration_serialize(config);
	}

	puts(json_object_to_json_string_ext(
		result, JSON_C_TO_STRING_SPACED | JSON_C_TO_STRING_NOSLASHESCAPE));
	return 0;
}
