#!/bin/bash

# Exit immediately on any error
set -e

# shellcheck disable=SC1091
. ../e2e/lib/utils

QMCTL_SCRIPT="../../tools/qmctl/qmctl"

# Install development tools if needed
exec_cmd "dnf install --setopt=reposdir=/etc/yum.repos.d  --installroot=/usr/lib/qm/rootfs -y iproute hostname || true"

info_message "Starting comprehensive qmctl show tests..."

# Test 0: Basic show command (default behavior - shows container config)
info_message "Testing: Basic show command (default)"
expected_output_file="/usr/share/containers/systemd/qm.container"
actual_output_temp_file=$(mktemp)

python3 "$QMCTL_SCRIPT" show > "$actual_output_temp_file"

if diff "$actual_output_temp_file" "$expected_output_file" > /dev/null; then
    pass_message "Basic show - Output matches expected container config"
else
    fail_message "Basic show - Output does NOT match expected container config"
    echo "  Expected: $expected_output_file"
    echo "  Actual output saved to: $actual_output_temp_file"
    rm -f actual_output_temp_file
    exit 1
fi
rm -f "$actual_output_temp_file"

# Clean up the basic test file
python3 "$QMCTL_SCRIPT" exec bash -c "rm -f /tmp/file-to-copy.txt && echo 'cleaned up basic test file'" >/dev/null 2>&1 || true

# Test 1: Show unix-domain-sockets (handle missing 'ss' command gracefully)
info_message "Testing: Show unix-domain-sockets"
unix_sockets_file=$(mktemp)
stderr_file=$(mktemp)

python3 "$QMCTL_SCRIPT" show unix-domain-sockets > "$unix_sockets_file" 2> "$stderr_file"

unix_sockets_exit=$?

if [ "$unix_sockets_exit" -eq 0 ]; then
    pass_message "Show unix-domain-sockets - Exit code correct (0)"
    if grep -q "UNIX domain sockets" "$unix_sockets_file"; then
        pass_message "Show unix-domain-sockets - Output contains expected pattern"
    else
        info_message "NOTE: Show unix-domain-sockets - Output format may vary"
    fi
    if [ -s "$unix_sockets_file" ]; then
        pass_message "Show unix-domain-sockets - Output contains data"
    else
        fail_message "Show unix-domain-sockets - Expected output data but got empty output"
        rm -f "$unix_sockets_file" "$stderr_file"
        exit 1
    fi
elif grep -q "ss.*not found\|executable file.*ss.*not found" "$stderr_file"; then
    info_message "SKIP: Show unix-domain-sockets - 'ss' command not available in container"
    info_message "NOTE: This is a container configuration issue, not a qmctl bug"
else
    fail_message "Show unix-domain-sockets - Unexpected error (exit code $unix_sockets_exit)"
    echo "stderr:"
    head -5 "$stderr_file"
    rm -f "$unix_sockets_file" "$stderr_file"
    exit 1
fi
rm -f "$unix_sockets_file" "$stderr_file"

# Test 2: Show shared-memory
run_test "Show shared-memory" 0 "output_pattern" "Shared Memory Segments" \
    python3 "$QMCTL_SCRIPT" show shared-memory

# Test 3: Show available-devices - Contains device info
run_test "Show available-devices - device pattern" 0 "output_pattern" "present in QM" \
    python3 "$QMCTL_SCRIPT" show available-devices

# Test 4: Show namespaces
run_test "Show namespaces" 0 "output_pattern" "Namespaces" \
    python3 "$QMCTL_SCRIPT" show namespaces

# Test 5: Show all (comprehensive test - handle missing tools gracefully)
info_message "Testing: Show all"
show_all_file=$(mktemp)
timeout 3s python3 "$QMCTL_SCRIPT" show all > "$show_all_file" 2>&1 || true

# Check that the file contains expected content
if [ -s "$show_all_file" ]; then
    if grep -q "\[Container\]" "$show_all_file" && grep -q "UNIX domain sockets:" "$show_all_file"; then
        pass_message "Show all - Output contains expected container and socket data"
    else
        fail_message "Show all - Output missing expected content"
        echo "First 10 lines of output:"
        head -10 "$show_all_file"
        rm -f "$show_all_file"
        exit 1
    fi
else
    fail_message "Show all - No output captured"
    rm -f "$show_all_file"
    exit 1
fi
rm -f "$show_all_file"

# Test 6: Show resources (special handling - may be interactive)
info_message "Testing: Show resources (with timeout)"
show_resources_file=$(mktemp)
timeout 10s python3 "$QMCTL_SCRIPT" show resources > "$show_resources_file" 2>&1 || true

# Check that the file contains expected content
if [ -s "$show_resources_file" ]; then
    if grep -q "qm.service" "$show_resources_file"; then
        pass_message "Show resources - Output contains expected resource monitoring data"
    else
        fail_message "Show resources - Output missing expected content"
        echo "First 10 lines of output:"
        head -10 "$show_resources_file"
        rm -f "$show_resources_file"
        exit 1
    fi
else
    fail_message "Show resources - No output captured"
    rm -f "$show_resources_file"
    exit 1
fi

# Clean up development tools
exec_cmd "dnf remove --setopt=reposdir=/etc/yum.repos.d  --installroot=/usr/lib/qm/rootfs -y iproute hostname || true"

# All tests passed
pass_message "All comprehensive qmctl show tests completed successfully"