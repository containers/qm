#!/bin/bash

# shellcheck disable=SC1091
. ../e2e/lib/utils

info_message "Running QM IPC tests..."

if ./scripts/qm-to-qm; then
    info_message "PASS: QM to QM IPC tests passed."
else
    info_message "FAIL: QM to QM IPC tests failed."
    exit 1
fi
