/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */
#pragma once
#include <json-c/json.h>

/* Mount the unshifted rootfs privately with the configured UID/GID mappings.
 * The returned path must be unmounted before local failure cleanup. */
char *userns_mount_rootfs(json_object *config);
void userns_configure_mounts(json_object *config, const char *runtime_dir);
