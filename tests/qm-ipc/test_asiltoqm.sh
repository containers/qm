#!/bin/bash

# shellcheck disable=SC1091
. ../e2e/lib/utils

info_message "Running QM IPC tests..."

if ! ./scripts/asil-to-qm ; then
  echo "FAIL: ASIL to QM IPC tests failed."
  exit 1
fi
