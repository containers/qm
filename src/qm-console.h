/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#pragma once

#include <sys/types.h>

/* Listen for crun's console master and relay its output to stdout in a child.
 * The child drains the console on shutdown and exits if its parent dies.
 * Return its PID, or -1 on failure with an error reported on stderr.
 */
pid_t console_start(const char *path);
