/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#pragma once

#include "qm-utils.h"

#include <netinet/in.h>
#include <stdbool.h>
#include <stdint.h>

typedef enum { USERNS_AUTO, USERNS_OFF, USERNS_REQUIRED } UserNamespaceMode;

typedef struct {
	char *source;
	char *destination;
	char *seat; /* Alternative device selector; source and destination are NULL. */

	bool device;
	bool remove;
	bool optional;

	bool options_set; /* Preserves an explicit empty list during serialization. */
	PtrArray options; /* Owned strings. */
} PathOperation;

typedef struct {
	char *name; /* Normalized capability name, or "all". */
	bool remove;
} CapabilityOperation;

/* NULL-terminated list of known Linux capability names. */
extern const char *const capability_names[];

typedef struct {
	char *base_config;
	char *hostname;
	char *rootfs;
	char *seccomp_file;
	char *resolv_conf;
	char *ip;
	char *gateway;
	unsigned int prefix_length;
	char subnet[INET_ADDRSTRLEN]; /* Derived from ip and prefix_length. */
	UserNamespaceMode userns;
	bool verbose;

	bool memory_max_set;
	int64_t memory_max;

	/* Owned PathOperation pointers, in load order within each list. */
	PtrArray mounts;
	PtrArray devices;

	PtrArray capabilities; /* Owned CapabilityOperation pointers, in load order. */
	PtrArray unmask;       /* Owned strings. */
} Config;

void config_free(Config *config);

bool reserved_mount_destination(const char *destination);

static inline void cleanup_config(Config **config)
{
	config_free(*config);
}

#define autofreeconfig __attribute__((cleanup(cleanup_config)))

/* Load qmc.conf, then sorted .conf files from qmc.conf.d, in each directory in turn.
 * Missing files/directories are optional. Later scalar keys replace earlier values;
 * mount, device, capability and unmask operations accumulate in load order.
 * An explicit filename instead loads only that file, which must exist.
 * Returns an allocated Config with defaults and owned strings; free with config_free.
 * Failures report the offending file and exit.
 */
Config *configuration_load(const char *vendor_dir, const char *admin_dir,
			   const char *filename);

/* Return an owned JSON object in qmc.conf format, including defaults. */
json_object *configuration_serialize(const Config *config);
