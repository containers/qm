/* SPDX-License-Identifier: GPL-2.0-only */
#include "qm-exec.h"
#include <string.h>
int main(int argc, char **argv)
{
	bool interactive = argc > 1 && strcmp(argv[1], "-i") == 0;
	int first = interactive ? 2 : 1;
	return argc > first ? exec_with_stdio(argv + first, interactive) : 2;
}
