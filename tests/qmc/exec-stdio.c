/* SPDX-License-Identifier: GPL-2.0-only */
#include "qm-exec.h"
int main(int argc, char **argv)
{
    return argc > 1 ? exec_with_stdio(argv + 1) : 2;
}
