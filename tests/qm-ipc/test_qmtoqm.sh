#!/bin/bash

# shellcheck disable=SC1091
. ../e2e/lib/utils

info_message "Running QM IPC tests..."

if ! ./scripts/qm-to-qm; then
  echo "FAIL: QM to QM IPC tests failed."
  exit 1
fi
