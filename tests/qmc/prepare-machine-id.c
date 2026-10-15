/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#include "qm-utils.h"

#include <string.h>

char *__real_read_text_file(const char *filename);

char *__wrap_read_text_file(const char *filename)
{
	/* RPM build containers may have no initialized host machine ID. */
	if (!strcmp(filename, "/etc/machine-id")) {
		const char *id = getenv("QM_TEST_MACHINE_ID");
		return xstrdup(id ? id : "d2c79cc3388a48e494c8cd22cce8f499\n");
	}
	return __real_read_text_file(filename);
}
