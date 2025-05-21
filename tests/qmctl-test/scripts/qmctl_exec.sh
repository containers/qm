#!/bin/bash

QMCTL_SCRIPT="../../tools/qmctl/qmctl"

if python3 $QMCTL_SCRIPT exec podman ps -a | grep -q "alpine-podman"; then
    echo "podman named alpine-container already exists"
    exit 1
fi

python3 $QMCTL_SCRIPT exec podman run -d --name alpine-podman alpine tail -f /dev/null

if ! python3 $QMCTL_SCRIPT exec podman ps -a | grep -q "alpine-podman"; then
    echo "podman container was not created"
    exit 1
fi

exit 0
