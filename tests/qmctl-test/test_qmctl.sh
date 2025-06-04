#!/bin/bash

# shellcheck disable=SC1091
. ../e2e/lib/utils

info_message "Running qmctl command..."

QMCTL_SCRIPT="../../tools/qmctl/qmctl"

if [ ! -f "$QMCTL_SCRIPT" ]; then
  echo "FAIL: qmctl script not found at $QMCTL_SCRIPT"
  exit 1
fi

if ! ./scripts/qmctl_show.sh ; then
  echo "FAIL: qmctl show failed."
  exit 1
fi

if ! ./scripts/qmctl_exec.sh; then
  echo "FAIL: qmctl exec failed."
  exit 1
fi

if ! ./scripts/qmctl_execin.sh; then
  echo "FAIL: qmctl execin failed."
  exit 1
fi

if ! ./scripts/qmctl_cp.sh; then
  echo "FAIL: qmctl cp failed."
  exit 1
fi
