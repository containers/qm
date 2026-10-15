/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#define _GNU_SOURCE
#include "qm-utils.h"

#include <err.h>
#include <limits.h>
#include <string.h>

int __real_ftruncate64(int fd, off64_t length);

int __wrap_ftruncate64(int fd, off64_t length)
{
	const char *directory = getenv("QM_TEST_BEFORE_TRUNCATE_DIR");
	if (directory) {
		autofree char *source = xasprintf("/proc/self/fd/%d", fd);
		char target[PATH_MAX];
		ssize_t length = readlink(source, target, sizeof(target) - 1);
		if (length < 0)
			err(1, "readlink %s", source);
		target[length] = '\0';
		const char *name = strrchr(target, '/');
		autofree char *snapshot = join_path(directory, name ? name + 1 : target);
		autofree char *contents = read_text_file(source);
		write_text_file(snapshot, contents);
	}
	return __real_ftruncate64(fd, length);
}
