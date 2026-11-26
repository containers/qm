/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#include "qm-port.h"
#include "qm-utils.h"

#include <arpa/inet.h>
#include <err.h>
#include <string.h>

static bool parse_port_number(const char **text, unsigned int *port)
{
	const char *p = *text;
	unsigned int value = 0;
	if (*p < '0' || *p > '9')
		return false;
	while (*p >= '0' && *p <= '9') {
		value = value * 10 + (*p++ - '0');
		if (value > UINT16_MAX)
			return false;
	}
	*text = p;
	*port = value;
	return value > 0;
}

static bool parse_port_range(const char *text, uint16_t *port, uint16_t *count)
{
	unsigned int first, last;
	if (!parse_port_number(&text, &first))
		return false;
	last = first;
	if (*text == '-') {
		text++;
		if (!parse_port_number(&text, &last) || last < first)
			return false;
	}
	if (*text)
		return false;
	*port = first;
	*count = last - first + 1;
	return true;
}

bool port_mapping_parse(const char *string, PortMapping *mapping)
{
	autofree char *text = xstrdup(string);
	PortMapping parsed = {.protocol = IPPROTO_TCP};
	char *protocol = strchr(text, '/');
	if (protocol) {
		*protocol++ = 0;
		if (streq(protocol, "tcp"))
			parsed.protocol = IPPROTO_TCP;
		else if (streq(protocol, "udp"))
			parsed.protocol = IPPROTO_UDP;
		else if (streq(protocol, "sctp"))
			parsed.protocol = IPPROTO_SCTP;
		else
			return false;
	}
	char *host = text;
	char *container = strchr(host, ':');
	if (!container)
		return false;
	*container++ = 0;
	char *next = strchr(container, ':');
	if (next) {
		if (inet_pton(AF_INET, host, &parsed.host_ip) != 1)
			return false;
		host = container;
		container = next + 1;
		*next = 0;
	}
	uint16_t count;
	if (!parse_port_range(host, &parsed.host_port, &parsed.range) ||
	    !parse_port_range(container, &parsed.container_port, &count) ||
	    parsed.range != count)
		return false;

	if (!port_mapping_valid(&parsed))
		return false;
	*mapping = parsed;
	return true;
}

const char *port_mapping_protocol_name(const PortMapping *mapping)
{
	switch (mapping->protocol) {
	case IPPROTO_TCP:
		return "tcp";
	case IPPROTO_UDP:
		return "udp";
	case IPPROTO_SCTP:
		return "sctp";
	default:
		return NULL;
	}
}

bool port_mapping_valid(const PortMapping *mapping)
{
	uint32_t ip = ntohl(mapping->host_ip.s_addr);
	return (!ip || ((ip >> 24) > 0 && (ip >> 24) < 224)) && mapping->host_port &&
	       mapping->container_port && mapping->range &&
	       (unsigned int)mapping->host_port + mapping->range - 1 <= UINT16_MAX &&
	       (unsigned int)mapping->container_port + mapping->range - 1 <= UINT16_MAX &&
	       port_mapping_protocol_name(mapping);
}

bool port_mapping_conflicts(const PortMapping *a, const PortMapping *b)
{
	return a->protocol == b->protocol &&
	       (!a->host_ip.s_addr || !b->host_ip.s_addr ||
		a->host_ip.s_addr == b->host_ip.s_addr) &&
	       a->host_port < (unsigned int)b->host_port + b->range &&
	       b->host_port < (unsigned int)a->host_port + a->range;
}

static char *format_port_range(uint16_t port, uint16_t count)
{
	return count == 1 ? xasprintf("%u", port)
			  : xasprintf("%u-%u", port, port + count - 1);
}

char *port_mapping_format(const PortMapping *mapping)
{
	char address[INET_ADDRSTRLEN] = "";
	if (mapping->host_ip.s_addr &&
	    !inet_ntop(AF_INET, &mapping->host_ip, address, sizeof(address)))
		err(1, "format published port address");
	autofree char *host = format_port_range(mapping->host_port, mapping->range);
	autofree char *container =
		format_port_range(mapping->container_port, mapping->range);
	return xasprintf("%s%s%s:%s/%s", address, *address ? ":" : "", host, container,
			 port_mapping_protocol_name(mapping));
}
