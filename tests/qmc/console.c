/* SPDX-License-Identifier: GPL-2.0-only */
#include "qm-console.h"
#include "qm-utils.h"

#include <stdio.h>

int main(int argc, char **argv)
{
	if (argc != 2)
		return 2;
	pid_t relay = console_start(argv[1]);
	if (relay < 0)
		return 1;
	fputs("ready\n", stderr);
	fflush(stderr);
	return wait_child(relay);
}
