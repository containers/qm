#!/bin/bash

echo "Running qmctl command..."

QMCTL_SCRIPT="../../tools/qmctl/qmctl"

if [ ! -f "$QMCTL_SCRIPT" ]; then
  echo "Error: qmctl script not found at $QMCTL_SCRIPT"
  exit 1
fi

if ! ./scripts/qmctl_show.sh ; then
  echo "qmctl show failed."
  exit 1
fi

if ! ./scripts/qmctl_exec.sh; then
  echo "qmctl exec failed."
  exit 1
fi

if ! ./scripts/qmctl_execin.sh; then
  echo "qmctl execin failed."
  exit 1
fi

if ! ./scripts/qmctl_cp.sh; then
  echo "qmctl cp failed."
  exit 1
fi