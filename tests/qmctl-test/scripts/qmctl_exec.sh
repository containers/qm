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

# Test that touch command returns exit code 0 with empty output
info_message "Testing touch command with empty output..."
touch_output=$(python3 $QMCTL_SCRIPT exec touch /tmp/test_file 2>&1)
touch_exit=$?

if [ $touch_exit -ne 0 ]; then
    fail_message "Touch command failed with exit code $touch_exit"
    exit 1
fi

if [ -n "$touch_output" ]; then
    fail_message "Touch command should have empty output but got: '$touch_output'"
    exit 1
fi

# Clean up the test file - only check return code
info_message "Removing test file..."
if ! python3 $QMCTL_SCRIPT exec rm -f /tmp/test_file; then
    fail_message "Failed to remove test file"
    exit 1
fi
# NOTE: We don't clean up the container here as subsequent tests (execin) may need it

pass_message "qmctl exec command executed successfully"
