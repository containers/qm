/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#pragma once

#include <json-c/json.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/types.h>
#include <unistd.h>

#define N_ELEMENTS(arr) (sizeof(arr) / sizeof((arr)[0]))
#define autofree __attribute__((cleanup(cleanup_free)))
#define autoclose __attribute__((cleanup(cleanup_close)))
#define autofreejson __attribute__((cleanup(js_cleanup_json)))

static inline void cleanup_free(void *p)
{
	free(*(void **)p);
}

static inline void cleanup_close(const int *fd)
{
	/* Linux releases the descriptor even when close() returns EINTR. */
	if (*fd >= 0)
		close(*fd);
}

static inline void *steal_ptr(void *p)
{
	void **pp = p;
	void *result = *pp;

	*pp = NULL;

	return result;
}

void oom(void) __attribute__((noreturn));
void *xmalloc(size_t size) __attribute__((malloc, alloc_size(1)));
void *xrealloc(void *ptr, size_t size) __attribute__((alloc_size(2)));
char *xstrdup(const char *string) __attribute__((malloc));
char *xasprintf(const char *format, ...) __attribute__((format(printf, 1, 2)));

#define xnew(type) ((type *)xmalloc(sizeof(type)))

/* Builds an allocated NULL-terminated vector, borrowing strings.
 * Initialize to {0}. Each add requires a non-NULL string and grows the array
 * as needed. Clear frees the array, leaving the borrowed strings untouched.
 */
typedef struct {
	char **strv;
	size_t length;
	size_t capacity;
} StrvBuilder;

void strv_builder_add(StrvBuilder *builder, const char *string);
void strv_builder_clear(StrvBuilder *builder);

#define autofreestrvbuilder __attribute__((cleanup(strv_builder_clear)))

/* A growing array of pointers. Initialize to {0}. Clear optionally frees each
 * element with free_func, then frees the array and resets it to {0}.
 */
typedef struct {
	void **items;
	size_t length;
	size_t capacity;
} PtrArray;

void ptr_array_add(PtrArray *array, void *item);
void ptr_array_clear(PtrArray *array, void (*free_func)(void *));

bool starts_with(const char *string, const char *prefix);
char *join_path(const char *a, const char *b);

typedef enum {
	CHAR_ALPHA = 1 << 0,
	CHAR_DIGIT = 1 << 1,
	CHAR_HEX = 1 << 2,
	CHAR_DOT = 1 << 3,
	CHAR_DASH = 1 << 4,
	CHAR_UNDERSCORE = 1 << 5,
	CHAR_ALNUM = CHAR_ALPHA | CHAR_DIGIT,
} CharClass;

/* Match any selected ASCII character class, independently of locale.
 * NUL and non-ASCII bytes never match. The string helper accepts empty strings.
 */
bool char_in_class(unsigned char character, CharClass classes);
bool string_in_class(const char *string, CharClass classes);

/* Return an allocated absolute path with repeated slashes, . and .. resolved
 * lexically, without filesystem I/O or following symlinks. Relative paths
 * return NULL with errno set to EINVAL; .. at the root stays at the root.
 */
char *canonicalize_path(const char *path);

/* Parse positive bytes with an optional binary K/M/G/T/P/E suffix (optionally
 * followed by B or iB), or "infinity" as -1. Return false for invalid input or
 * values exceeding INT64_MAX, leaving size unchanged.
 */
bool parse_size(const char *string, int64_t *size);

char *read_text_file(const char *filename);
/* Return NULL with errno set on open/read failure. */
char *try_read_text_file(const char *filename);
void write_all(int fd, const char *data, size_t length);
void ensure_private_directory(const char *name);
void write_text_file(const char *name, const char *contents);
/* Remove a directory's contents without removing the directory itself,
 * following symlinks or crossing filesystems.
 * Missing paths succeed; return 1 and report other errors on stderr.
 */
int remove_tree_contents(const char *path);
/* Preserve one named entry directly inside path, including its contents. */
int remove_tree_contents_except(const char *path, const char *preserve);
/* Write a slash-separated key under /proc/sys; optional ignores missing keys.
 * Return 0 on success, -1 on failure and report errors on stderr.
 */
int sysctl_write(const char *key, const char *value, bool optional);
void set_selinux_label(const char *name, const char *context);
/* Return an allocated label, or NULL when SELinux is disabled. */
char *get_selinux_label(const char *name);

typedef struct {
	bool found;
	uint32_t start;
	uint32_t count;
} IdRange;

/* Return .found=false when the file or username has no subordinate-ID range. */
IdRange read_subid(const char *directory, const char *filename, const char *username);

/* Return an allocated path for the calling process's cgroup v2 membership. */
char *get_current_cgroup(void);

bool ns_is_mounted(const char *path);

/* Return exit status (128 + signal if killed), or -1 with errno on failure.
 * These helpers do not exit, so cleanup can continue after an error. */
int wait_child(pid_t child);

/* Also report fork, exec and wait errors on stderr. */
int run_command(char *const argv[]);

void js_cleanup_json(void *p);

/* Constructors and js_load return owned references. Getters return borrowed
 * references; string pointers remain valid while their JSON value is alive.
 * js_object_add, js_array_add and js_array_insert consume the supplied reference. */
json_object *js_new_int(int64_t value);
json_object *js_new_bool(bool value);
json_object *js_new_strings(const char *const values[], size_t count);
json_object *js_new_string(const char *value);
json_object *js_new_array(void);
json_object *js_new_object(void);

void js_object_add(json_object *object, const char *key, json_object *value);
void js_array_add(json_object *array, json_object *value);
/* Insert before index, which must be at most the current array length. */
void js_array_insert(json_object *array, size_t index, json_object *value);

json_object *js_get(json_object *object, const char *key);
json_object *js_need(json_object *object, const char *key, enum json_type type);
const char *js_array_string(json_object *array, size_t index);
const char *js_string(json_object *object, const char *key);
void js_set_string(json_object *object, const char *key, const char *value);

json_object *js_load(const char *filename);
void js_save(json_object *object, const char *filename);
/* Publish a complete JSON file atomically; refuse an existing file unless
 * replace is true. New files are private to the current user.
 */
void js_save_atomic(json_object *object, const char *filename, bool replace);
bool js_contains(json_object *array, const char *value);
