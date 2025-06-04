#!/bin/bash

# shellcheck disable=SC1091
. ../e2e/lib/utils

QMCTL_SCRIPT="../../tools/qmctl/qmctl"

if python3 $QMCTL_SCRIPT exec podman ps -a | grep -q "alpine-podman"; then
    echo "FAIL: podman named alpine-container already exists"
    exit 1
fi

python3 $QMCTL_SCRIPT exec podman run -d --name alpine-podman alpine tail -f /dev/null

if ! python3 $QMCTL_SCRIPT exec podman ps -a | grep -q "alpine-podman"; then
    echo "FAIL: podman container was not created"
    exit 1
fi

info_message "PASS: qmctl exec command executed successfully"
exit 0
