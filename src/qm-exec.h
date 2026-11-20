/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */
#pragma once

#include <stdbool.h>

/* Relay non-terminal stdio through runtime-owned pipes, preserving byte streams
 * and exit status across the payload's SELinux domain transition. Without
 * interactive input, give the child /dev/null and leave the caller's input alone.
 */
int exec_with_stdio(char *const argv[], bool interactive);
