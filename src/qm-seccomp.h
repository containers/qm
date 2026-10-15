/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#pragma once

#include <json-c/json.h>

/* Convert a containers-style profile in place to OCI format, resolving
 * architecture and capability conditions against the host and process's
 * bounding capabilities. OCI profiles are also accepted. Invalid profiles
 * are fatal.
 */
void resolve_seccomp(json_object *profile, json_object *process);
