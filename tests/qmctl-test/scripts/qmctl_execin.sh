#!/bin/bash

# shellcheck disable=SC1091
. ../e2e/lib/utils

CONTAINER_NAME="alpine-podman"
TMP_FILE="/tmp/file-execin.txt"

# Ensure the alpine-podman container exists (create if needed)
if ! qmctl exec podman ps -a | grep -q "$CONTAINER_NAME"; then
    info_message "Creating $CONTAINER_NAME container for execin test..."
    qmctl exec podman run -d --name "$CONTAINER_NAME" alpine tail -f /dev/null
fi

# Ensure the container is running
qmctl exec podman start "$CONTAINER_NAME" > /dev/null 2>&1 || true

# Clean up any existing test file from previous runs
qmctl execin "$CONTAINER_NAME" rm -f "$TMP_FILE" > /dev/null 2>&1 || true

# Verify test file doesn't exist
if qmctl execin "$CONTAINER_NAME" ls -la /tmp/ | grep -q "file-execin.txt"; then
    fail_message "The file $TMP_FILE still exists after cleanup"
    exit 1
fi

# Create the test file
info_message "Testing execin functionality..."
qmctl execin "$CONTAINER_NAME" touch "$TMP_FILE"

# Verify the file was created and can be read
if ! qmctl execin "$CONTAINER_NAME" cat "$TMP_FILE" > /dev/null 2>&1; then
    fail_message "The file $TMP_FILE was not created or cannot be read"
    exit 1
fi

# Cleanup test file
qmctl execin "$CONTAINER_NAME" rm -f "$TMP_FILE" > /dev/null 2>&1 || true

pass_message "qmctl execin command executed successfully"
