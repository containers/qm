#!/bin/bash

# Exit immediately on any error
set -e

# shellcheck disable=SC1091
. ../e2e/lib/utils

# Install development tools if needed
exec_cmd "dnf install --setopt=reposdir=/etc/yum.repos.d  --installroot=/usr/lib/qm/rootfs -y hostname iproute || true"

QMCTL_SCRIPT="../../tools/qmctl/qmctl"

info_message "Starting qmctl JSON output tests..."

# Test 1: Show commands with JSON output
run_test "JSON Show container" 0 "json_valid" "[Container]" \
    python3 "$QMCTL_SCRIPT" show container --json

# Handle unix-domain-sockets separately (may have missing ss command)
info_message "Testing: JSON Show unix-domain-sockets"
unix_json_file=$(mktemp)
python3 "$QMCTL_SCRIPT" show unix-domain-sockets --json > "$unix_json_file" 2>&1
unix_json_exit=$?

if [ "$unix_json_exit" -eq 0 ]; then
    if python3 -m json.tool < "$unix_json_file" > /dev/null 2>&1; then
        pass_message "JSON Show unix-domain-sockets - Valid JSON output"
    else
        fail_message "JSON Show unix-domain-sockets - Invalid JSON output"
        rm -f "$unix_json_file"
        exit 1
    fi
elif [ "$unix_json_exit" -eq 1 ] && grep -q "ss.*not found\|executable file.*ss.*not found" "$unix_json_file"; then
    if python3 -m json.tool < "$unix_json_file" > /dev/null 2>&1; then
        info_message "SKIP: JSON Show unix-domain-sockets - Missing 'ss' command (valid JSON error)"
    else
        fail_message "JSON Show unix-domain-sockets - Invalid JSON error response"
        rm -f "$unix_json_file"
        exit 1
    fi
else
    fail_message "JSON Show unix-domain-sockets - Unexpected error (exit $unix_json_exit)"
    rm -f "$unix_json_file"
    exit 1
fi
rm -f "$unix_json_file"

run_test "JSON Show shared-memory" 0 "json_valid" "Shared Memory Segments" \
    python3 "$QMCTL_SCRIPT" show shared-memory --json

run_test "JSON Show available-devices" 0 "json_valid" "/dev/kvm" \
    python3 "$QMCTL_SCRIPT" show available-devices --json

run_test "JSON Show namespaces" 0 "json_valid" "Namespaces" \
    python3 "$QMCTL_SCRIPT" show namespaces --json

# Test 2: Exec commands with JSON output
info_message "QM container is available - testing exec JSON commands"

run_test "JSON Exec echo" 0 "json_valid" "" \
    python3 "$QMCTL_SCRIPT" exec --json echo "hello world"

# Handle hostname separately (may not work in container)
info_message "Testing: JSON Exec hostname"
hostname_json_file=$(mktemp)
python3 "$QMCTL_SCRIPT" exec --json hostname > "$hostname_json_file" 2>&1
hostname_json_exit=$?

if [ "$hostname_json_exit" -eq 0 ]; then
    if python3 -m json.tool < "$hostname_json_file" > /dev/null 2>&1; then
        pass_message "JSON Exec hostname - Valid JSON output"
    else
        fail_message "JSON Exec hostname - Invalid JSON output"
        rm -f "$hostname_json_file"
        exit 1
    fi
else
    # hostname might fail in container, check if it's a reasonable error
    if grep -q "Error.*hostname\|not found\|No output returned" "$hostname_json_file"; then
        info_message "SKIP: JSON Exec hostname - Command failed in container environment"
    else
        fail_message "JSON Exec hostname - Unexpected error (exit $hostname_json_exit)"
        head -3 "$hostname_json_file"
        rm -f "$hostname_json_file"
        exit 1
    fi
fi
rm -f "$hostname_json_file"

run_test "JSON Exec ls" 0 "json_valid" "" \
    python3 "$QMCTL_SCRIPT" exec --json ls /tmp

# Test 3: Copy commands with JSON output
info_message "Testing copy JSON commands"

# Create test files for copy operations
copy_test_file_1=$(mktemp)
copy_test_file_2="/tmp/json_copy_test_result.txt"
echo "JSON copy test content" > "$copy_test_file_1"

run_test "JSON Copy host to container" 0 "none" "" \
    python3 "$QMCTL_SCRIPT" cp --json "$copy_test_file_1" "qm:/tmp/json_copy_test.txt"

info_message "NOTE: JSON Copy host to container - Silent success (no JSON output expected)"

run_test "JSON Copy container to host" 0 "none" "" \
    python3 "$QMCTL_SCRIPT" cp --json "qm:/tmp/json_copy_test.txt" "$copy_test_file_2"

info_message "NOTE: JSON Copy container to host - Silent success (no JSON output expected)"

# Cleanup copy test files
rm -f "$copy_test_file_1" "$copy_test_file_2" 2>/dev/null || true
python3 "$QMCTL_SCRIPT" exec bash -c "rm -f /tmp/json_copy_test.txt && echo 'cleaned up copy test file'" >/dev/null 2>&1 || true

# Test 4: Error cases that should produce JSON error responses
run_test "JSON error: exec without command" 22 "none" "" \
    python3 "$QMCTL_SCRIPT" exec --json

run_test "JSON error: invalid show subcommand" 2 "error_pattern" "invalid choice" \
    python3 "$QMCTL_SCRIPT" show --json nonexistent_subcommand

# Test 5: JSON format specifics
info_message "Testing JSON format specifics..."

# Test JSON formatting with a simple command
json_format_file=$(mktemp)
python3 "$QMCTL_SCRIPT" show container --json > "$json_format_file"

# Test with jq if available
if command -v jq > /dev/null 2>&1; then
    if jq . < "$json_format_file" > /dev/null 2>&1; then
        pass_message "JSON formatting validation - Valid JSON (jq validation)"
    else
        fail_message "JSON formatting validation - Invalid JSON (jq validation)"
        rm -f "$json_format_file"
        exit 1
    fi
else
    info_message "NOTE: jq not available, skipping jq validation"
fi

# Test if JSON is pretty-printed (contains newlines and indentation)
if grep -q $'\n' "$json_format_file" && grep -q '    ' "$json_format_file"; then
    pass_message "JSON formatting validation - JSON is pretty-printed"
else
    fail_message "JSON formatting validation - JSON is not properly formatted"
    rm -f "$json_format_file"
    exit 1
fi

rm -f "$json_format_file"

# Clean up development tools
exec_cmd "dnf remove --setopt=reposdir=/etc/yum.repos.d  --installroot=/usr/lib/qm/rootfs -y hostname iproute || true"

# All tests passed
pass_message "All qmctl JSON output tests completed successfully"
