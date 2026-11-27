#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 Alexander Larsson

set -euxo pipefail

# Run as root on a disposable VM. All host-file and network changes made by
# smoke.py stay inside its private namespaces.
test "$EUID" -eq 0
source_dir=$(realpath "$(dirname "${BASH_SOURCE[0]}")/../..")
build_dir=$(mktemp -d "${TMT_TEST_DATA:-/var/tmp}/qmc-smoke-build.XXXXXX")

meson setup "$build_dir" "$source_dir" --prefix=/usr
meson compile -C "$build_dir" qmc test-network test-launch-network

# Run directly so that an unavailable prerequisite (exit 77) fails CI instead
# of being accepted as a Meson skip.
python3 "$source_dir/tests/qmc/network-policy.py" "$build_dir/tests/qmc/test-network"

# Explicit mappings also cover the pre-shifted UID 1000 / GID 2000 fixture.
# A system service provides delegation without requiring a user session bus.
systemd-run --wait --pipe --collect \
    -p Delegate=yes -p DelegateSubgroup=supervisor -p RuntimeMaxSec=300 \
    env TMPDIR=/var/tmp PYTHONUNBUFFERED=1 \
    unshare --user --map-users=0:0:65536 --map-groups=0:0:65536 \
    --mount --mount-proc --net --pid --fork \
    python3 "$source_dir/tests/qmc/smoke.py" "$build_dir/src/qmc"
