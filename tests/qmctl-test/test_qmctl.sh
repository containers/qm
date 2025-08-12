#!/bin/bash

# shellcheck disable=SC1091
. ../e2e/lib/utils

info_message "Running qmctl command..."

QMCTL_SCRIPT="../../tools/qmctl/qmctl"

if [ ! -f "$QMCTL_SCRIPT" ]; then
  fail_message "qmctl script not found at $QMCTL_SCRIPT"
  exit 1
fi

if ! ./scripts/qmctl_show_variants.sh ; then
  fail_message "qmctl comprehensive show tests failed."
  exit 1
fi

if ! ./scripts/qmctl_exec.sh; then
  fail_message "qmctl exec failed."
  exit 1
fi

if ! ./scripts/qmctl_execin.sh; then
  fail_message "qmctl execin failed."
  exit 1
fi

if ! ./scripts/qmctl_cp_bidirectional.sh; then
  fail_message "qmctl comprehensive copy tests failed."
  exit 1
fi

if ! ./scripts/qmctl_json_output.sh; then
  fail_message "qmctl json output failed."
  exit 1
fi

if ! ./scripts/qmctl_error_handling.sh; then
  fail_message "qmctl error handling failed."
  exit 1
fi

pass_message "All qmctl tests completed successfully"
