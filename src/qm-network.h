/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#pragma once

#include <json-c/json.h>
#include <stdbool.h>
#include <stdint.h>

typedef struct {
	const char *runtime_dir;
	const char *veth;
	const char *interface;
	const char *ip;
	const char *gateway;
	const char *subnet; /* IPv4 network address without a prefix length. */
	unsigned int prefix_len;
	uint8_t veth_mac[6];
	uint32_t fallback_mtu; /* Used when no default IPv4 route exists. */
	unsigned int rp_filter;
	bool disable_ipv6;
	const char *nft_table;
} NetworkOptions;

typedef struct NetworkState NetworkState;

/* Create and pin a namespace with loopback already up. Return 0 on success,
 * 1 on failure. Set *file_created when the pin file was created, even if a
 * later step failed; the caller must clean it up.
 */
int network_create_namespace(const char *path, bool *file_created);

/* Check for conflicts and return allocated cleanup state without changing the
 * network, or NULL on failure. The caller must save it before network_setup().
 */
NetworkState *network_prepare(const NetworkOptions *options);
/* Execute setup using the same options passed to network_prepare(). The
 * namespace must already be pinned at options->runtime_dir/netns. Saved state
 * also identifies resources left by a failed or interrupted setup.
 */
int network_setup(const NetworkOptions *options, const NetworkState *state);
/* Remove only resources identified by the saved network state. Safe to repeat.
 * NULL means that setup did not claim any network resources.
 */
int network_teardown(const NetworkState *state);

json_object *network_state_serialize(const NetworkState *state);
NetworkState *network_state_deserialize(json_object *object);
void network_state_free(NetworkState *state);
