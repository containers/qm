/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#include "qm-state.h"
#include "qm-utils.h"

#include <err.h>

json_object *state_serialize(const State *state)
{
	json_object *object = js_new_object();
	js_object_add(object, "version", js_new_int(QM_STATE_VERSION));
	if (state->bundle)
		js_set_string(object, "bundle", state->bundle);
	if (state->crun_executable) {
		json_object *crun = js_new_object();
		js_set_string(crun, "executable", state->crun_executable);
		js_set_string(crun, "root", state->crun_root);
		js_set_string(crun, "id", state->container_id);
		js_object_add(object, "crun", crun);
	}
	if (state->netns)
		js_set_string(object, "netns", state->netns);
	if (state->network)
		js_object_add(object, "network", network_state_serialize(state->network));
	return object;
}

State *state_deserialize(json_object *object)
{
	if (json_object_get_int64(js_need(object, "version", json_type_int)) !=
	    QM_STATE_VERSION)
		errx(1, "unsupported cleanup state version");
	autostate State *state = xnew(State);
	*state = (State){0};
	if (js_get(object, "bundle"))
		state->bundle = xstrdup(js_string(object, "bundle"));
	if (js_get(object, "crun")) {
		json_object *crun = js_need(object, "crun", json_type_object);
		state->crun_executable = xstrdup(js_string(crun, "executable"));
		state->crun_root = xstrdup(js_string(crun, "root"));
		state->container_id = xstrdup(js_string(crun, "id"));
	}
	if (js_get(object, "netns"))
		state->netns = xstrdup(js_string(object, "netns"));
	if (js_get(object, "network"))
		state->network = network_state_deserialize(
			js_need(object, "network", json_type_object));
	return steal_ptr(&state);
}

void state_free(State *state)
{
	if (!state)
		return;
	free(state->bundle);
	free(state->crun_executable);
	free(state->crun_root);
	free(state->container_id);
	free(state->netns);
	network_state_free(state->network);
	free(state);
}

void state_cleanup(State **state)
{
	state_free(*state);
}
