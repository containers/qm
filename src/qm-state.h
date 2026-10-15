/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#pragma once

#include "qm-network.h"

#define QM_STATE_FILE "state.json"
#define QM_STATE_VERSION 1

typedef struct {
	char *bundle;
	char *crun_executable;
	char *crun_root;
	char *container_id;
	char *netns;
	NetworkState *network;
} State;

json_object *state_serialize(const State *state);
State *state_deserialize(json_object *object);
void state_free(State *state);
void state_cleanup(State **state);

#define autostate __attribute__((cleanup(state_cleanup)))
