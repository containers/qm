#!/bin/bash

# Exit immediately on any error
set -e

# shellcheck disable=SC1091
. ../e2e/lib/utils

info_message "Starting comprehensive qmctl error handling tests..."

# Test 1: No subcommand (should show usage and fail)
run_test "No subcommand" 22 "error_pattern" "requires a subcommand" \
    qmctl

# Test 2: Invalid subcommand
run_test "Invalid subcommand" 2 "error_pattern" "invalid choice" \
    qmctl invalid_command

# Test 3: Exec without command
run_test "Exec without command" 22 "error_pattern" "No command provided" \
    qmctl exec

# Test 4: Execin without container name
run_test "Execin without container" 1 "error_pattern" "No command provided" \
    qmctl execin

# Test 5: Execin with container but no command
run_test "Execin with container but no command" 1 "error_pattern" "No command provided" \
    qmctl execin some_container

# Test 6: Copy without any paths
run_test "Copy without paths" 2 "error_pattern" "required" \
    qmctl cp

# Test 7: Copy with single path (missing destination)
run_test "Copy with single path" 2 "error_pattern" "required" \
    qmctl cp /some/path

# Test 8: Copy with invalid path format
run_test "Copy with invalid path format" 1 "error_pattern" "Provide.*qm.*only in source or destination" \
    qmctl cp /some/path invalid:/path/format

# Test 9: Copy both paths with qm: prefix (invalid)
run_test "Copy both paths with container prefix" 1 "error_pattern" "Provide.*qm.*only in source or destination" \
    qmctl cp qm:/path1 qm:/path2

# Test 10: Show with invalid subcommand
run_test "Show invalid subcommand" 2 "error_pattern" "invalid choice" \
    qmctl show invalid_show_command

# Test 11: Help command (should succeed)
run_test "Help command" 0 "output_pattern" "usage" \
    qmctl --help

# Test 12: JSON flag with exec but no command
run_test "JSON exec without command" 22 "none" "" \
    qmctl exec --json

# Test 13: Verbose mode with error
run_test "Verbose mode with error" 22 "error_pattern" "No command provided" \
    qmctl -v exec

# Test 14: Empty string as command
run_test "Empty string command" 1 "error_pattern" "Failed to execute" \
    qmctl exec ""

# Test 15: Exec with non-existent command
run_test "Exec non-existent command" 1 "error_pattern" "not found" \
    qmctl exec /definitely/nonexistent/command/12345

# Test 16: Execin with non-existent nested container
run_test "Execin non-existent container" 1 "error_pattern" "failed" \
    qmctl execin nonexistent_nested_container echo hello

# Test 17: Copy non-existent source file
nonexistent_file="/tmp/qmctl_test_nonexistent_$(date +%s%N)"
run_test "Copy non-existent source" 1 "error_pattern" "could not be found" \
    qmctl cp "$nonexistent_file" qm:/tmp/

# Test 18: Very long command
long_command=$(printf 'a%.0s' {1..1000})
run_test "Very long command" 1 "error_pattern" "File name too long" \
    qmctl exec "$long_command"

# Test 19: Special characters in command
# shellcheck disable=SC2016  # Single quotes intentional to prevent expansion
run_test "Special characters command" 1 "error_pattern" "not found" \
    qmctl exec 'command_with_$pecial_ch@rs_!@#$%^&*()'

# All tests passed
pass_message "All qmctl error handling tests completed successfully"
