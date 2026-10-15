/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#include "qm-utils.h"

/* Build containers can expose only the root of a cgroup namespace. */
char *__wrap_get_current_cgroup(void)
{
	return xstrdup("/");
}
