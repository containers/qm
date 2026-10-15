/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#define _GNU_SOURCE
#include "qm-utils.h"

#include <err.h>
#include <errno.h>
#include <fcntl.h>
#include <libmnl/libmnl.h>
#include <linux/rtnetlink.h>
#include <net/if.h>
#include <nftables/libnftables.h>
#include <string.h>

int __real_nft_run_cmd_from_buffer(struct nft_ctx *ctx, const char *command);
ssize_t __real_mnl_socket_sendto(const struct mnl_socket *nl, const void *buffer,
				 size_t length);
int __real_sysctl_write(const char *key, const char *value, bool optional);

int __wrap_sysctl_write(const char *key, const char *value, bool optional)
{
	const char *fail = getenv("QM_TEST_SYSCTL_FAIL");
	if (fail && !strcmp(key, fail)) {
		errno = EROFS;
		warn("set sysctl %s", key);
		return -1;
	}
	return __real_sysctl_write(key, value, optional);
}

static void wait_gate(const char *gate)
{
	autofree char *pid_file = xasprintf("%s.pid", gate);
	autofree char *pid = xasprintf("%ld\n", (long)getpid());
	write_text_file(pid_file, pid);
	autoclose int fd = open(gate, O_RDONLY | O_CLOEXEC);
	char byte;
	if (fd < 0 || TEMP_FAILURE_RETRY(read(fd, &byte, 1)) != 1)
		errx(1, "release network test gate");
}

ssize_t __wrap_mnl_socket_sendto(const struct mnl_socket *nl, const void *buffer,
				 size_t length)
{
	const struct nlmsghdr *header = buffer;
	if (getenv("QM_TEST_LOOPBACK_FAIL") && header->nlmsg_type == RTM_NEWLINK &&
	    !(header->nlmsg_flags & NLM_F_CREATE)) {
		const struct ifinfomsg *info = mnl_nlmsg_get_payload(header);
		if (info->ifi_flags & IFF_UP) {
			errno = EIO;
			return -1;
		}
	}
	const char *gate = getenv("QM_TEST_LINK_GATE");
	if (gate && header->nlmsg_type == RTM_NEWLINK &&
	    (header->nlmsg_flags & NLM_F_CREATE)) {
		/* Pause before creating the veth pair. Loopback is already up. */
		unsetenv("QM_TEST_LINK_GATE");
		wait_gate(gate);
	}
	return __real_mnl_socket_sendto(nl, buffer, length);
}

int __wrap_nft_run_cmd_from_buffer(struct nft_ctx *ctx, const char *command)
{
	/* Gate table creation, leaving ownership checks and cleanup untouched. */
	const char *gate = getenv("QM_TEST_NFT_GATE");
	if (gate && strstr(command, "\"create\""))
		wait_gate(gate);
	/* Fail after creating the owned table to exercise partial rollback. */
	if (getenv("QM_TEST_NFT_FAIL") && starts_with(command, "add chain"))
		return __real_nft_run_cmd_from_buffer(ctx, "invalid-nft-command\n");
	return __real_nft_run_cmd_from_buffer(ctx, command);
}
