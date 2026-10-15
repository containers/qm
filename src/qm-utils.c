/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#define _GNU_SOURCE
#include "qm-utils.h"

#include <assert.h>
#include <err.h>
#include <errno.h>
#include <fcntl.h>
#include <fts.h>
#include <linux/magic.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/wait.h>
#include <sys/xattr.h>

void js_cleanup_json(void *p)
{
	void **pp = p;
	if (*pp)
		json_object_put(*pp);
}

void oom(void)
{
	errx(1, "Out of memory");
}

void *xmalloc(size_t size)
{
	void *result = malloc(size);
	if (!result)
		oom();

	return result;
}

void *xrealloc(void *ptr, size_t size)
{
	void *result = realloc(ptr, size);
	if (!result)
		oom();

	return result;
}

char *xstrdup(const char *string)
{
	char *result = strdup(string);
	if (!result)
		oom();

	return result;
}

char *xasprintf(const char *format, ...)
{
	char *result;
	va_list args;
	va_start(args, format);
	int size = vasprintf(&result, format, args);
	va_end(args);
	if (size < 0)
		oom();

	return result;
}

void strv_builder_add(StrvBuilder *builder, const char *string)
{
	if (builder->length + 1 >= builder->capacity) {
		size_t capacity = builder->capacity ? builder->capacity * 2 : 8;
		if (capacity <= builder->capacity ||
		    capacity > SIZE_MAX / sizeof(*builder->strv))
			oom();
		builder->strv =
			xrealloc(builder->strv, capacity * sizeof(*builder->strv));
		builder->capacity = capacity;
	}
	builder->strv[builder->length++] = (char *)string;
	builder->strv[builder->length] = NULL;
}

void strv_builder_clear(StrvBuilder *builder)
{
	free(builder->strv);
	*builder = (StrvBuilder){0};
}

void ptr_array_add(PtrArray *array, void *item)
{
	if (array->length == array->capacity) {
		size_t capacity = array->capacity ? array->capacity * 2 : 8;
		if (capacity <= array->capacity ||
		    capacity > SIZE_MAX / sizeof(*array->items))
			oom();

		array->items = xrealloc(array->items, capacity * sizeof(*array->items));
		array->capacity = capacity;
	}

	array->items[array->length++] = item;
}

void ptr_array_clear(PtrArray *array, void (*free_func)(void *))
{
	if (free_func)
		for (size_t i = 0; i < array->length; i++)
			free_func(array->items[i]);

	free(array->items);
	*array = (PtrArray){0};
}

bool starts_with(const char *string, const char *prefix)
{
	return strncmp(string, prefix, strlen(prefix)) == 0;
}

char *join_path(const char *a, const char *b)
{
	while (*b == '/')
		b++;

	return xasprintf("%s%s%s", a, *a && a[strlen(a) - 1] != '/' ? "/" : "", b);
}

bool char_in_class(unsigned char character, CharClass classes)
{
	return ((classes & CHAR_ALPHA) &&
		((character >= 'a' && character <= 'z') ||
		 (character >= 'A' && character <= 'Z'))) ||
	       ((classes & (CHAR_DIGIT | CHAR_HEX)) &&
		character >= '0' && character <= '9') ||
	       ((classes & CHAR_HEX) &&
		((character >= 'a' && character <= 'f') ||
		 (character >= 'A' && character <= 'F'))) ||
	       ((classes & CHAR_DOT) && character == '.') ||
	       ((classes & CHAR_DASH) && character == '-') ||
	       ((classes & CHAR_UNDERSCORE) && character == '_');
}

bool string_in_class(const char *string, CharClass classes)
{
	for (; *string; string++)
		if (!char_in_class(*string, classes))
			return false;

	return true;
}

char *canonicalize_path(const char *path)
{
	if (*path != '/') {
		errno = EINVAL;
		return NULL;
	}

	char *result = xmalloc(strlen(path) + 1);
	char *out = result;
	*out++ = '/';

	while (*path) {
		while (*path == '/')
			path++;

		const char *component = path;
		while (*path && *path != '/')
			path++;
		size_t length = path - component;
		if (!length || (length == 1 && component[0] == '.'))
			continue;

		if (length == 2 && component[0] == '.' && component[1] == '.') {
			while (out > result + 1 && out[-1] != '/')
				out--;
			if (out > result + 1)
				out--;
			continue;
		}

		if (out > result + 1)
			*out++ = '/';
		memcpy(out, component, length);
		out += length;
	}
	*out = '\0';

	return result;
}

bool parse_size(const char *string, int64_t *size)
{
	if (!strcmp(string, "infinity")) {
		*size = -1;
		return true;
	}

	/* strtoull accepts signs and leading whitespace; sizes do not. */
	if (!char_in_class(*string, CHAR_DIGIT))
		return false;

	errno = 0;
	char *p;
	uint64_t bytes = strtoull(string, &p, 10);
	if (errno || !bytes || bytes > INT64_MAX)
		return false;

	if (*p) {
		const char *units = "KMGTPE";
		const char *unit = strchr(units, *p++);
		if (!unit || (*p && strcmp(p, "B") && strcmp(p, "iB")))
			return false;

		uint64_t multiplier = UINT64_C(1) << (10 * (unit - units + 1));
		if (bytes > INT64_MAX / multiplier)
			return false;
		bytes *= multiplier;
	}

	*size = bytes;
	return true;
}

char *try_read_text_file(const char *filename)
{
	autoclose int fd = TEMP_FAILURE_RETRY(open(filename, O_RDONLY | O_CLOEXEC));
	if (fd < 0)
		return NULL;

	size_t size = 4096, length = 0;
	autofree char *buffer = xmalloc(size);
	for (;;) {
		if (length == size - 1) {
			size *= 2;
			buffer = xrealloc(buffer, size);
		}

		ssize_t count =
			TEMP_FAILURE_RETRY(read(fd, buffer + length, size - length - 1));
		if (count < 0) {
			int saved_errno = errno;
			close(fd);
			fd = -1;
			errno = saved_errno;
			return NULL;
		}
		if (!count)
			break;

		length += count;
	}

	buffer[length] = 0;

	return steal_ptr(&buffer);
}

char *read_text_file(const char *filename)
{
	char *contents = try_read_text_file(filename);
	if (!contents)
		err(1, "read %s", filename);
	return contents;
}

int sysctl_write(const char *key, const char *value, bool optional)
{
	autofree char *path = join_path("/proc/sys", key);
	autoclose int fd = TEMP_FAILURE_RETRY(open(path, O_WRONLY | O_CLOEXEC));
	if (fd < 0 && optional && errno == ENOENT)
		return 0;
	if (fd < 0 || TEMP_FAILURE_RETRY(write(fd, value, strlen(value))) !=
			      (ssize_t)strlen(value)) {
		warn("set sysctl %s", key);
		return -1;
	}
	return 0;
}

static json_object *js_checked(json_object *value)
{
	if (!value)
		oom();

	return value;
}

json_object *js_new_string(const char *value)
{
	return js_checked(json_object_new_string(value));
}

json_object *js_new_int(int64_t value)
{
	return js_checked(json_object_new_int64(value));
}

json_object *js_new_bool(bool value)
{
	return js_checked(json_object_new_boolean(value));
}

json_object *js_new_strings(const char *const values[], size_t count)
{
	autofreejson json_object *array = js_new_array();
	for (size_t i = 0; i < count; i++)
		js_array_add(array, js_new_string(values[i]));

	return steal_ptr(&array);
}

json_object *js_new_array(void)
{
	return js_checked(json_object_new_array());
}

json_object *js_new_object(void)
{
	return js_checked(json_object_new_object());
}

void js_object_add(json_object *object, const char *key, json_object *value)
{
	if (json_object_object_add(object, key, value) < 0)
		oom();
}

void js_array_add(json_object *array, json_object *value)
{
	if (json_object_array_add(array, value) < 0)
		oom();
}

void js_array_insert(json_object *array, size_t index, json_object *value)
{
	size_t length = json_object_array_length(array);
	assert(index <= length);

	js_array_add(array, NULL);
	for (size_t i = length; i > index; i--) {
		json_object *item = json_object_array_get_idx(array, i - 1);
		if (json_object_array_put_idx(array, i, json_object_get(item)) < 0)
			oom();
	}
	if (json_object_array_put_idx(array, index, value) < 0)
		oom();
}

json_object *js_get(json_object *object, const char *key)
{
	json_object *value = NULL;
	if (object)
		json_object_object_get_ex(object, key, &value);

	return value;
}

json_object *js_need(json_object *object, const char *key, enum json_type type)
{
	json_object *value = js_get(object, key);
	if (!json_object_is_type(value, type))
		errx(1, "missing or invalid JSON field: %s", key);

	return value;
}

const char *js_array_string(json_object *array, size_t index)
{
	json_object *value = json_object_array_get_idx(array, index);
	if (!json_object_is_type(value, json_type_string))
		errx(1, "expected a JSON string in array");

	return json_object_get_string(value);
}

const char *js_string(json_object *object, const char *key)
{
	return json_object_get_string(js_need(object, key, json_type_string));
}

void js_set_string(json_object *object, const char *key, const char *value)
{
	js_object_add(object, key, js_new_string(value));
}

json_object *js_load(const char *filename)
{
	autofree char *contents = read_text_file(filename);
	enum json_tokener_error error;
	autofreejson json_object *result = json_tokener_parse_verbose(contents, &error);
	if (error != json_tokener_success)
		errx(1, "%s: %s", filename, json_tokener_error_desc(error));
	if (!json_object_is_type(result, json_type_object))
		errx(1, "%s: expected a JSON object", filename);

	return steal_ptr(&result);
}

void js_save(json_object *object, const char *filename)
{
	if (!object)
		errx(1, "%s: cannot write a null JSON object", filename);

	const char *contents = json_object_to_json_string_ext(
		object, JSON_C_TO_STRING_PRETTY | JSON_C_TO_STRING_NOSLASHESCAPE);
	if (!contents)
		oom();

	write_text_file(filename, contents);
}

void js_save_atomic(json_object *object, const char *filename, bool replace)
{
	const char *contents = json_object_to_json_string_ext(
		object, JSON_C_TO_STRING_PRETTY | JSON_C_TO_STRING_NOSLASHESCAPE);
	if (!contents)
		oom();
	autofree char *temporary = xasprintf("%s.XXXXXX", filename);
	autoclose int fd = mkostemp(temporary, O_CLOEXEC);
	if (fd < 0)
		err(1, "create temporary file for %s", filename);
	write_all(fd, contents, strlen(contents));
	if (close(fd) < 0)
		err(1, "close %s", temporary);
	fd = -1;
	/* link() publishes the initial state without replacing another launch's
	 * state. Subsequent snapshots replace the old file with rename().
	 */
	int result = replace ? rename(temporary, filename) : link(temporary, filename);
	if (result < 0) {
		int saved_errno = errno;
		unlink(temporary);
		errno = saved_errno;
		err(1, "publish %s", filename);
	}
	if (!replace && unlink(temporary) < 0)
		err(1, "unlink %s", temporary);
}

bool js_contains(json_object *array, const char *value)
{
	if (!array)
		return false;
	if (!json_object_is_type(array, json_type_array))
		errx(1, "expected a JSON array");

	for (size_t i = 0; i < json_object_array_length(array); i++)
		if (!strcmp(js_array_string(array, i), value))
			return true;

	return false;
}

void ensure_private_directory(const char *name)
{
	if (mkdir(name, 0700) < 0 && errno != EEXIST)
		err(1, "mkdir %s", name);

	struct stat st;
	if (lstat(name, &st) < 0)
		err(1, "stat %s", name);
	if (!S_ISDIR(st.st_mode) || st.st_uid != geteuid() || (st.st_mode & 0077))
		errx(1, "%s must be a private directory owned by the current user", name);
}

void write_all(int fd, const char *data, size_t length)
{
	while (length) {
		ssize_t written = TEMP_FAILURE_RETRY(write(fd, data, length));
		if (written <= 0)
			err(1, "write");

		data += written;
		length -= written;
	}
}

void write_text_file(const char *name, const char *contents)
{
	autoclose int fd = TEMP_FAILURE_RETRY(
		open(name, O_WRONLY | O_CREAT | O_TRUNC | O_NOFOLLOW | O_CLOEXEC, 0644));
	if (fd < 0)
		err(1, "open %s", name);

	write_all(fd, contents, strlen(contents));
}

int remove_tree_contents_except(const char *path, const char *preserve)
{
	char *paths[] = {(char *)path, NULL};
	FTS *tree = fts_open(paths, FTS_NOCHDIR | FTS_PHYSICAL | FTS_XDEV, NULL);
	if (!tree) {
		warn("remove %s", path);
		return 1;
	}

	int result = 0;
	FTSENT *entry;
	errno = 0;
	while ((entry = fts_read(tree))) {
		if (entry->fts_info == FTS_ERR || entry->fts_info == FTS_DNR ||
		    entry->fts_info == FTS_NS) {
			if (entry->fts_errno != ENOENT) {
				errno = entry->fts_errno;
				warn("remove %s", entry->fts_path);
				result = 1;
			}
		} else if (entry->fts_level == 1 && preserve &&
			   !strcmp(entry->fts_name, preserve)) {
			fts_set(tree, entry, FTS_SKIP);
		} else if (entry->fts_level > 0 && entry->fts_info != FTS_D &&
			   remove(entry->fts_accpath) < 0 && errno != ENOENT) {
			warn("remove %s", entry->fts_path);
			result = 1;
		}
		errno = 0;
	}
	if (errno) {
		warn("read directory %s", path);
		result = 1;
	}
	if (fts_close(tree) < 0) {
		warn("close directory %s", path);
		result = 1;
	}
	return result;
}

int remove_tree_contents(const char *path)
{
	return remove_tree_contents_except(path, NULL);
}

char *get_selinux_label(const char *name)
{
	if (access("/sys/fs/selinux/enforce", F_OK) < 0)
		return NULL;

	ssize_t size = getxattr(name, "security.selinux", NULL, 0);
	if (size < 0)
		err(1, "read label %s", name);

	autofree char *context = xmalloc(size + 1);
	ssize_t length = getxattr(name, "security.selinux", context, size);
	if (length < 0)
		err(1, "read label %s", name);
	context[length] = '\0';
	return steal_ptr(&context);
}

void set_selinux_label(const char *name, const char *context)
{
	if (context && *context && access("/sys/fs/selinux/enforce", F_OK) == 0 &&
	    setxattr(name, "security.selinux", context, strlen(context) + 1, 0) < 0)
		err(1, "label %s", name);
}

IdRange read_subid(const char *directory, const char *filename, const char *username)
{
	autofree char *path = join_path(directory, filename);
	FILE *file = fopen(path, "r");
	if (!file) {
		if (errno == ENOENT)
			return (IdRange){0};
		err(1, "open %s", path);
	}

	autofree char *line = NULL;
	size_t capacity = 0;
	IdRange result = {0};
	while (getline(&line, &capacity, file) >= 0) {
		char *first = strchr(line, ':');
		if (!first)
			continue;
		*first++ = '\0';
		if (strcmp(line, username))
			continue;
		if (result.found)
			errx(1, "%s has multiple %s ranges", path, username);

		char *second = strchr(first, ':');
		if (!second)
			errx(1, "invalid %s range in %s", username, path);
		*second++ = '\0';
		second[strcspn(second, "\n")] = '\0';

		char *end;
		errno = 0;
		unsigned long long start = strtoull(first, &end, 10);
		if (errno || !*first || *end)
			errx(1, "invalid %s start in %s", username, path);

		errno = 0;
		unsigned long long count = strtoull(second, &end, 10);
		if (errno || !*second || *end || !count || start > UINT32_MAX ||
		    count > UINT32_MAX || start + count > (uint64_t)UINT32_MAX + 1)
			errx(1, "invalid %s size in %s", username, path);

		result = (IdRange){.found = true, .start = start, .count = count};
	}

	if (ferror(file))
		err(1, "read %s", path);

	if (fclose(file) < 0)
		err(1, "close %s", path);

	return result;
}

char *get_current_cgroup(void)
{
	autofree char *contents = read_text_file("/proc/self/cgroup");
	char *path = strstr(contents, "0::");
	if (!path)
		errx(1, "cgroup v2 is required");

	path += 3;
	path[strcspn(path, "\n")] = '\0';

	return xstrdup(path);
}

bool ns_is_mounted(const char *path)
{
	struct statfs st;

	return statfs(path, &st) == 0 && st.f_type == NSFS_MAGIC;
}

int wait_child(pid_t child)
{
	int status;
	if (TEMP_FAILURE_RETRY(waitpid(child, &status, 0)) < 0)
		return -1;

	return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}

int run_command(char *const argv[])
{
	pid_t child = fork();
	if (child < 0) {
		int error = errno;
		warn("fork %s", argv[0]);
		errno = error;
		return -1;
	}

	if (!child) {
		execv(argv[0], argv);
		warn("exec %s", argv[0]);
		_exit(127);
	}

	int status = wait_child(child);
	if (status < 0) {
		int error = errno;
		warn("wait for %s", argv[0]);
		errno = error;
	}

	return status;
}
