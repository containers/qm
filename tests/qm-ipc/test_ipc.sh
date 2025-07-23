#!/bin/bash

# shellcheck disable=SC1091
. ../e2e/lib/utils

./scripts/common/build.sh

info_message "Running QM IPC tests..."

if ! ./scripts/asil-to-qm/asil-to-qm.sh ; then
  echo "FAIL: ASIL to QM IPC tests failed."
  exit 1
fi

if ! ./scripts/qm-to-qm/qm-to-qm.sh; then
  echo "FAIL: QM to QM IPC tests failed."
  exit 1
fi
