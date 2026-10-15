/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#pragma once

#include "qm-config.h"

#include <json-c/json.h>

/* Apply configured policy before resolving the seccomp profile. */
void configure_oci_policy(json_object *oci, const Config *config);
