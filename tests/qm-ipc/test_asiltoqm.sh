#!/bin/bash

# shellcheck disable=SC1091
. ../e2e/lib/utils

info_message "Running QM IPC tests..."

if ./scripts/asil-to-qm; then
    info_message "PASS: ASIL to QM IPC tests passed."
else
    info_message "FAIL: ASIL to QM IPC tests failed."
    exit 1
fi
