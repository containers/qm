#!/bin/bash

# shellcheck disable=SC1091
. ../e2e/lib/utils

QMCTL_SCRIPT="../../tools/qmctl/qmctl"
CONTAINER_NAME="alpine-podman"
TMP_FILE="/tmp/file-execin.txt"

# Ensure the alpine-podman container exists (create if needed)
if ! python3 $QMCTL_SCRIPT exec podman ps -a | grep -q "$CONTAINER_NAME"; then
    info_message "Creating $CONTAINER_NAME container for execin test..."
    python3 $QMCTL_SCRIPT exec podman run -d --name "$CONTAINER_NAME" alpine tail -f /dev/null
fi

# Ensure the container is running
python3 $QMCTL_SCRIPT exec podman start "$CONTAINER_NAME" > /dev/null 2>&1 || true

# Clean up any existing test file from previous runs
python3 $QMCTL_SCRIPT execin "$CONTAINER_NAME" rm -f "$TMP_FILE" > /dev/null 2>&1 || true

# Verify test file doesn't exist
if python3 $QMCTL_SCRIPT execin "$CONTAINER_NAME" ls -la /tmp/ | grep -q "file-execin.txt"; then
    fail_message "The file $TMP_FILE still exists after cleanup"
    exit 1
fi

# Create the test file
info_message "Testing execin functionality..."
python3 $QMCTL_SCRIPT execin "$CONTAINER_NAME" touch "$TMP_FILE"

# Verify the file was created and can be read
if ! python3 $QMCTL_SCRIPT execin "$CONTAINER_NAME" cat "$TMP_FILE" > /dev/null 2>&1; then
    fail_message "The file $TMP_FILE was not created or cannot be read"
    exit 1
fi

# Cleanup test file
python3 $QMCTL_SCRIPT execin "$CONTAINER_NAME" rm -f "$TMP_FILE" > /dev/null 2>&1 || true

pass_message "qmctl execin command executed successfully"
