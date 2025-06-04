#!/bin/bash

# shellcheck disable=SC1091
. ../e2e/lib/utils

QMCTL_SCRIPT="../../tools/qmctl/qmctl"

python3 $QMCTL_SCRIPT cp ./files/file-to-copy.txt qm:/tmp

expected_output_file="./files/file-to-check-cp.txt"
actual_output_temp_file=$(mktemp)

python3 $QMCTL_SCRIPT exec cat /tmp/file-to-copy.txt > "$actual_output_temp_file"

if diff "$actual_output_temp_file" "$expected_output_file" > /dev/null; then
  info_message "The output matches the content of '$expected_output_file'."
  info_message "PASS: qmctl cp command executed successfully"
  exit 0
else
  echo "FAIL: The output does NOT match the content of '$expected_output_file'."
  exit 1
fi
