/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */
#pragma once
#include <json-c/json.h>

/* ID map qmc's generated runtime bind mounts, leaving persistent trees alone. */
void userns_configure_mounts(json_object *config, const char *runtime_dir);
