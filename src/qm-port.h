/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#pragma once

#include <netinet/in.h>
#include <stdbool.h>
#include <stdint.h>

typedef struct {
	struct in_addr host_ip; /* INADDR_ANY publishes on all host IPv4 addresses. */
	uint16_t host_port;
	uint16_t container_port;
	uint16_t range;	  /* Number of consecutive ports, at least one. */
	uint8_t protocol; /* IPPROTO_TCP, IPPROTO_UDP or IPPROTO_SCTP. */
} PortMapping;

/* Parse [IPv4:]host-port:container-port[/protocol], including equal-length
 * ranges. Returns false on invalid input and leaves *mapping unchanged.
 */
bool port_mapping_parse(const char *text, PortMapping *mapping);
bool port_mapping_valid(const PortMapping *mapping);
bool port_mapping_conflicts(const PortMapping *a, const PortMapping *b);
/* Return the protocol name, or NULL for an unsupported protocol. */
const char *port_mapping_protocol_name(const PortMapping *mapping);
/* Return an owned string, with an explicit protocol. Requires a valid mapping. */
char *port_mapping_format(const PortMapping *mapping);
