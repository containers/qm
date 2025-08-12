#!/bin/bash

# shellcheck disable=SC1091
. ../e2e/lib/utils

QMCTL_SCRIPT="../../tools/qmctl/qmctl"
CONTAINER_NAME="alpine-podman"

# Cleanup any existing container from previous runs
info_message "Cleaning up any existing test container..."
python3 $QMCTL_SCRIPT exec podman rm -f "$CONTAINER_NAME" > /dev/null 2>&1 || true

# Verify container doesn't exist
if python3 $QMCTL_SCRIPT exec podman ps -a | grep -q "$CONTAINER_NAME"; then
    fail_message "Container $CONTAINER_NAME still exists after cleanup"
    exit 1
fi

# Create new container
info_message "Creating test container..."
python3 $QMCTL_SCRIPT exec podman run -d --name "$CONTAINER_NAME" alpine tail -f /dev/null

# Verify container was created
if ! python3 $QMCTL_SCRIPT exec podman ps -a | grep -q "$CONTAINER_NAME"; then
    fail_message "Container $CONTAINER_NAME was not created"
    exit 1
fi

# NOTE: We don't clean up the container here as subsequent tests (execin) may need it

pass_message "qmctl exec command executed successfully"
exit 0
