#!/bin/bash

QMCTL_SCRIPT="../../tools/qmctl/qmctl"

expected_output_file="./files/qmctl_show_expected.txt"
actual_output_temp_file=$(mktemp)

python3 $QMCTL_SCRIPT show > "$actual_output_temp_file"

if diff "$actual_output_temp_file" "$expected_output_file" > /dev/null; then
  echo "The output matches the content of '$expected_output_file'."
  exit 0
else
  echo "The output does NOT match the content of '$expected_output_file'."
  diff "$actual_output_temp_file" "$expected_output_file"
  exit 1
fi
