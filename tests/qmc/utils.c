/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#define _GNU_SOURCE
#include "qm-utils.h"

#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdarg.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>

static unsigned open_calls, read_calls, write_calls, wait_calls;
static bool fail_fork;

pid_t __real_fork(void);
int __real_open64(const char *path, int flags, ...);
ssize_t __real_read(int fd, void *buffer, size_t size);
ssize_t __real_write(int fd, const void *buffer, size_t size);
pid_t __real_waitpid(pid_t pid, int *status, int options);

int __wrap_open64(const char *path, int flags, ...)
{
	if (++open_calls <= 2) {
		errno = EINTR;
		return -1;
	}

	mode_t mode = 0;
	if (flags & O_CREAT) {
		va_list args;
		va_start(args, flags);
		mode = va_arg(args, mode_t);
		va_end(args);
	}

	return __real_open64(path, flags, mode);
}

ssize_t __wrap_read(int fd, void *buffer, size_t size)
{
	if (++read_calls == 1 || read_calls == 3) {
		errno = EINTR;
		return -1;
	}

	return __real_read(fd, buffer, size > 3 ? 3 : size);
}

/* Fortified builds use this entry point instead of read. */
ssize_t __wrap___read_chk(int fd, void *buffer, size_t size, size_t buffer_size)
{
	assert(size <= buffer_size);
	return __wrap_read(fd, buffer, size);
}

ssize_t __wrap_write(int fd, const void *buffer, size_t size)
{
	if (++write_calls == 1 || write_calls == 3) {
		errno = EINTR;
		return -1;
	}

	return __real_write(fd, buffer, size > 3 ? 3 : size);
}

pid_t __wrap_waitpid(pid_t pid, int *status, int options)
{
	if (++wait_calls <= 2) {
		errno = EINTR;
		return -1;
	}

	return __real_waitpid(pid, status, options);
}

pid_t __wrap_fork(void)
{
	if (fail_fork) {
		errno = EAGAIN;
		return -1;
	}

	return __real_fork();
}

static void test_character_classes(void)
{
	const struct {
		CharClass classes;
		const char *characters;
	} classes[] = {
		{CHAR_ALPHA, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"},
		{CHAR_DIGIT, "0123456789"},
		{CHAR_HEX, "0123456789abcdefABCDEF"},
		{CHAR_DOT, "."},
		{CHAR_DASH, "-"},
		{CHAR_UNDERSCORE, "_"},
		{CHAR_ALNUM, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"},
	};

	for (size_t i = 0; i < N_ELEMENTS(classes); i++) {
		for (unsigned c = 0; c <= UCHAR_MAX; c++) {
			bool expected = c && strchr(classes[i].characters, c);
			assert(char_in_class(c, classes[i].classes) == expected);

			char string[] = {(char)c, '\0'};
			assert(string_in_class(string, classes[i].classes) ==
			       (!c || expected));
		}
	}

	const struct {
		const char *string;
		CharClass classes;
		bool expected;
	} strings[] = {
		{"", 0, true},
		{"", CHAR_ALNUM, true},
		{"a", 0, false},
		{"QM09", CHAR_ALNUM, true},
		{"QM09", CHAR_ALPHA, false},
		{"qmc-test_0.conf", CHAR_ALNUM | CHAR_DASH | CHAR_UNDERSCORE | CHAR_DOT, true},
		{"qmc-test_0.conf", CHAR_ALNUM | CHAR_DASH | CHAR_UNDERSCORE, false},
		{"09aF-fA90", CHAR_HEX | CHAR_DASH, true},
		{"09aF-gA90", CHAR_HEX | CHAR_DASH, false},
		{"9.0", CHAR_DIGIT | CHAR_DOT, true},
		{"a/b", CHAR_ALNUM | CHAR_DOT | CHAR_DASH | CHAR_UNDERSCORE, false},
		{"a b", CHAR_ALNUM, false},
		{"a\nb", CHAR_ALNUM, false},
		{"caf\xc3\xa9", CHAR_ALNUM, false},
	};

	for (size_t i = 0; i < N_ELEMENTS(strings); i++)
		assert(string_in_class(strings[i].string, strings[i].classes) ==
		       strings[i].expected);
}

static void test_canonicalize_path(void)
{
	const struct {
		const char *path;
		const char *expected;
	} cases[] = {
		{"/", "/"},
		{"////", "/"},
		{"/a", "/a"},
		{"/a/b", "/a/b"},
		{"//a///b//", "/a/b"},
		{"/./a/./b/.", "/a/b"},
		{"/a/../b", "/b"},
		{"/a/b/..", "/a"},
		{"/a/b/../../..", "/"},
		{"/../../a/../b", "/b"},
		{"/a/.../.hidden/..b", "/a/.../.hidden/..b"},
		{"/missing-qm-path/child/../file", "/missing-qm-path/file"},
		/* /proc/self is a symlink; normalization must remain lexical. */
		{"/proc/self/../file", "/proc/file"},
	};

	for (size_t i = 0; i < N_ELEMENTS(cases); i++) {
		autofree char *path = canonicalize_path(cases[i].path);
		assert(path && !strcmp(path, cases[i].expected));
	}

	errno = 0;
	assert(canonicalize_path("") == NULL && errno == EINVAL);
	errno = 0;
	assert(canonicalize_path("relative/path") == NULL && errno == EINVAL);
}

static unsigned freed_items;

static void free_item(void *item)
{
	assert(*(int *)item == (int)freed_items++);
	free(item);
}

static void test_ptr_array(void)
{
	PtrArray array = {0};
	ptr_array_clear(&array, free_item);
	assert(freed_items == 0);

	for (int i = 0; i < 128; i++) {
		int *item = xnew(int);
		*item = i;
		ptr_array_add(&array, item);
	}
	assert(array.length == 128);
	for (size_t i = 0; i < array.length; i++)
		assert(*(int *)array.items[i] == (int)i);

	ptr_array_clear(&array, free_item);
	assert(freed_items == 128);
	assert(array.items == NULL && array.length == 0 && array.capacity == 0);

	/* Reuse with borrowed pointers, including NULL. */
	int borrowed = 42;
	ptr_array_add(&array, &borrowed);
	ptr_array_add(&array, NULL);
	assert(array.length == 2 && array.items[0] == &borrowed &&
	       array.items[1] == NULL);
	ptr_array_clear(&array, NULL);
	assert(borrowed == 42);
	assert(array.items == NULL && array.length == 0 && array.capacity == 0);
}

static void test_remove_tree_contents_except(void)
{
	char path[] = "/tmp/qm-utils-tree-XXXXXX";
	assert(mkdtemp(path));
	autofree char *preserved = join_path(path, "keep");
	autofree char *marker = join_path(preserved, "marker");
	autofree char *discarded = join_path(path, "discard");
	autofree char *nested = join_path(discarded, "keep");
	assert(mkdir(preserved, 0700) == 0);
	write_text_file(marker, "keep\n");
	assert(mkdir(discarded, 0700) == 0);
	write_text_file(nested, "remove\n");
	autofree char *link = join_path(discarded, "link");
	assert(symlink(preserved, link) == 0);
	struct stat before, after;
	assert(stat(preserved, &before) == 0);
	assert(remove_tree_contents_except(path, "keep") == 0);
	assert(stat(preserved, &after) == 0 && before.st_ino == after.st_ino);
	autofree char *contents = read_text_file(marker);
	assert(!strcmp(contents, "keep\n"));
	assert(access(discarded, F_OK) < 0 && errno == ENOENT);
	assert(remove_tree_contents(path) == 0);
	assert(access(preserved, F_OK) < 0 && errno == ENOENT);
	assert(rmdir(path) == 0);
	assert(remove_tree_contents_except(path, "keep") == 0);
}

int main(void)
{
	test_character_classes();
	test_canonicalize_path();
	test_ptr_array();
	test_remove_tree_contents_except();

	int64_t size;
	assert(parse_size("5GiB", &size) && size == INT64_C(5) * 1024 * 1024 * 1024);
	assert(parse_size("infinity", &size) && size == -1);
	assert(parse_size("9223372036854775807", &size) && size == INT64_MAX);
	assert(!parse_size("8E", &size) && size == INT64_MAX);
	assert(!parse_size("invalid", &size) && size == INT64_MAX);

	autofreestrvbuilder StrvBuilder builder = {0};
	const char *first = "first string";
	strv_builder_add(&builder, first);
	assert(builder.length == 1 && builder.strv[0] == first &&
	       builder.strv[1] == NULL);
	strv_builder_add(&builder, "");
	for (size_t i = 0; i < 128; i++) {
		strv_builder_add(&builder, first);
		assert(builder.strv[builder.length] == NULL);
	}
	assert(builder.length == 130 && !strcmp(builder.strv[1], ""));
	for (size_t i = 2; i < builder.length; i++)
		assert(builder.strv[i] == first);
	strv_builder_clear(&builder);
	assert(builder.strv == NULL && builder.length == 0 && builder.capacity == 0);
	strv_builder_add(&builder, first);
	assert(builder.length == 1 && builder.strv[0] == first &&
	       builder.strv[1] == NULL);

	char filename[] = "/tmp/qm-utils-XXXXXX";
	autoclose int fd = mkstemp(filename);
	assert(fd >= 0);

	const char *text = "interrupted and partial I/O";
	write_text_file(filename, text);
	assert(open_calls >= 3 && write_calls >= 4);

	open_calls = read_calls = 0;
	autofree char *contents = read_text_file(filename);
	assert(!strcmp(contents, text));
	assert(open_calls >= 3 && read_calls >= 4);

	autofreejson json_object *object = js_new_object();
	js_set_string(object, "message", text);
	open_calls = write_calls = 0;
	js_save(object, filename);
	assert(open_calls >= 3 && write_calls >= 4);

	open_calls = read_calls = 0;
	autofreejson json_object *loaded = js_load(filename);
	assert(json_object_equal(object, loaded));
	assert(open_calls >= 3 && read_calls >= 4);
	assert(unlink(filename) == 0);
	assert(try_read_text_file(filename) == NULL && errno == ENOENT);
	assert(try_read_text_file("/tmp") == NULL && errno == EISDIR);

	pid_t child = fork();
	assert(child >= 0);
	if (!child)
		_exit(17);

	int status = wait_child(child);
	assert(status == 17);
	assert(wait_calls == 3);

	errno = 0;
	status = wait_child(child);
	assert(status == -1 && errno == ECHILD);

	char *argv[] = {"/bin/true", NULL};
	fail_fork = true;
	status = run_command(argv);
	assert(status == -1 && errno == EAGAIN);

	fail_fork = false;
	status = run_command(argv);
	assert(status == 0);

	/* Interrupted/partial writes must publish a complete state, and the
	 * initial publication must not replace another launch's saved state.
	 */
	write_calls = 0;
	js_save_atomic(object, filename, false);
	struct stat before, after;
	assert(stat(filename, &before) == 0);
	assert((before.st_mode & 0777) == 0600);
	autofreejson json_object *replacement = js_new_object();
	js_set_string(replacement, "message", "replacement state");
	child = fork();
	assert(child >= 0);
	if (!child) {
		js_save_atomic(replacement, filename, false);
		_exit(0);
	}
	assert(wait_child(child) == 1);
	autofreejson json_object *original = js_load(filename);
	assert(json_object_equal(original, object));
	write_calls = 0;
	js_save_atomic(replacement, filename, true);
	assert(stat(filename, &after) == 0);
	assert(before.st_ino != after.st_ino);
	autofreejson json_object *replaced = js_load(filename);
	assert(json_object_equal(replaced, replacement));
	assert(unlink(filename) == 0);

	return 0;
}
