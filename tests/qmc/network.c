/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#include "qm-network.h"
#include "qm-state.h"
#include "qm-utils.h"

#include <err.h>
#include <string.h>

static void save_state(const State *state, const char *filename, bool replace)
{
	autofreejson json_object *object = state_serialize(state);
	js_save_atomic(object, filename, replace);
}

int main(int argc, char **argv)
{
	if (argc != 2 && (argc != 3 || strcmp(argv[2], "--prepare-only")))
		errx(2, "usage: test-network RUNTIME_DIR [--prepare-only]");
	const NetworkOptions options = {
		.runtime_dir = argv[1],
		.veth = "test-veth",
		.interface = "test0",
		.ip = "172.30.20.2",
		.gateway = "172.30.20.1",
		.subnet = "172.30.20.0",
		.prefix_len = 28,
		.veth_mac = {0x02, 0x00, 0xac, 0x1e, 0x14, 0x01},
		.fallback_mtu = 1234,
		.rp_filter = 1,
		.disable_ipv6 = false,
		.nft_table = "test_network",
	};
	autofree char *state_file = join_path(options.runtime_dir, QM_STATE_FILE);
	autostate State *state = xnew(State);
	*state = (State){.bundle = xstrdup(options.runtime_dir),
			 .netns = join_path(options.runtime_dir, "netns")};
	save_state(state, state_file, false);
	bool created;
	if (network_create_namespace(state->netns, &created))
		return 1;
	state->network = network_prepare(&options);
	if (!state->network)
		return 1;
	save_state(state, state_file, true);
	return argc == 3 ? 0 : network_setup(&options, state->network);
}
