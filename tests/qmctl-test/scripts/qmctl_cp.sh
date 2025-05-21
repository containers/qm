#!/bin/bash

QMCTL_SCRIPT="../../tools/qmctl/qmctl"

python3 $QMCTL_SCRIPT cp ./files/file-to-copy.txt qm:/tmp

expected_output_file="./files/file-to-check-cp.txt"
actual_output_temp_file=$(mktemp)

python3 $QMCTL_SCRIPT exec cat /tmp/file-to-copy.txt > "$actual_output_temp_file"

if diff "$actual_output_temp_file" "$expected_output_file" > /dev/null; then
  echo "The output matches the content of '$expected_output_file'."
  exit 0
else
  echo "The output does NOT match the content of '$expected_output_file'."
  diff "$actual_output_temp_file" "$expected_output_file"
  exit 1
fi
