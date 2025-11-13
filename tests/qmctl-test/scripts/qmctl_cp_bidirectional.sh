#!/bin/bash

# Exit immediately on any error
set -e

# shellcheck disable=SC1091
. ../e2e/lib/utils

info_message "Starting comprehensive qmctl copy tests..."

# Check if container is available
if ! qmctl exec echo "container_check" > /dev/null 2>&1; then
    fail_message "QM container is not available - copy tests cannot run"
    echo "Please ensure QM container is running with: sudo systemctl start qm"
    exit 1
fi

info_message "QM container is available - running comprehensive copy tests"

# Test 0: Basic copy test (from original qmctl_cp.sh)
info_message "Testing: Basic copy test (host to container)"
qmctl cp ./files/file-to-copy.txt qm:/tmp

expected_output_file="./files/file-to-check-cp.txt"
actual_output_temp_file=$(mktemp)

qmctl exec cat /tmp/file-to-copy.txt > "$actual_output_temp_file"

if diff "$actual_output_temp_file" "$expected_output_file" > /dev/null; then
    pass_message "Basic copy - File content matches expected"
else
    fail_message "Basic copy - File content does NOT match expected"
    echo "  Expected: $expected_output_file"
    echo "  Actual output saved to: $actual_output_temp_file"
    exit 1
fi
rm -f "$actual_output_temp_file"

# Clean up the basic test file
qmctl exec bash -c "rm -f /tmp/file-to-copy.txt && echo 'cleaned up basic test file'" >/dev/null 2>&1 || true

# Function to create a unique test file with specific content
create_test_file() {
    local filepath="$1"
    local content="$2"

    echo "$content" > "$filepath"
    if [ ! -f "$filepath" ]; then
        echo "ERROR: Failed to create test file $filepath"
        return 1
    fi
}

# Helper function to verify file content at destination
verify_copy_content() {
    local test_name="$1"
    local dst_path="$2"
    local expected_content="$3"
    local src_path="$4"

    local actual_content=""
    local actual_dst_path="$dst_path"

    # Handle directory destinations - construct full path
    if [[ "$dst_path" == */ ]]; then
        local src_filename
        src_filename=$(basename "$src_path")
        actual_dst_path="${dst_path}${src_filename}"
    fi

    if [[ "$actual_dst_path" == qm:* ]]; then
        # Destination is in container - use exec to read content
        local container_path="${actual_dst_path#qm:}"
        if actual_content=$(qmctl exec cat "$container_path" 2>/dev/null); then
            # Success - continue with verification
            :
        else
            fail_message "$test_name - Could not read destination file in container"
            echo "  Tried to read: $container_path"
            exit 1
        fi

        actual_content="${actual_content#output: }"
    else
        # Destination is on host
        if [ ! -f "$actual_dst_path" ]; then
            fail_message "$test_name - Destination file not found on host"
            echo "  Expected file: $actual_dst_path"
            exit 1
        fi
        actual_content=$(cat "$actual_dst_path")
    fi

    # Compare content
    if [ "$actual_content" = "$expected_content" ]; then
        pass_message "$test_name - File content matches expected"
        return 0
    else
        fail_message "$test_name - File content mismatch"
        echo "  Expected: '$expected_content'"
        echo "  Actual: '$actual_content'"
        exit 1
    fi
}

# Function to perform copy test with content verification
test_copy_with_verification() {
    local test_name="$1"
    local src_path="$2"
    local dst_path="$3"
    local expected_content="$4"
    local cleanup_paths="$5"  # paths to clean up after test

    # Run the copy command using the general run_test function
    if run_test "$test_name" 0 "none" "" \
        qmctl cp "$src_path" "$dst_path"; then

        # If copy succeeded, verify content
        if verify_copy_content "$test_name" "$dst_path" "$expected_content" "$src_path"; then
            pass_message "$test_name - Copy operation completed successfully"
        fi
    fi

    # Cleanup
    if [ -n "$cleanup_paths" ]; then
        for cleanup_path in $cleanup_paths; do
        local container_cleanup_path="${cleanup_path#qm:}"
        qmctl exec bash -c "rm -f '$container_cleanup_path' && echo 'cleaned up $container_cleanup_path'" >/dev/null 2>&1 || true
        done
    fi
}

# Test 1: Host to Container copy (basic bidirectional test)
test_content_1="Bidirectional copy test 1: host to container"
test_file_1=$(mktemp)
create_test_file "$test_file_1" "$test_content_1"

test_copy_with_verification \
    "Host to container copy" \
    "$test_file_1" \
    "qm:/tmp/bidi_test1.txt" \
    "$test_content_1" \
    "$test_file_1 qm:/tmp/bidi_test1.txt"

# Test 2: Container to Host copy (the missing functionality!)
test_content_2="Bidirectional copy test 2: container to host"

# First, create file in container
qmctl exec bash -c "echo '$test_content_2' > /tmp/bidi_test2.txt && echo 'File created in container'"

# Then copy from container to host
test_file_2="/tmp/bidi_test2_result.txt"
test_copy_with_verification \
    "Container to host copy" \
    "qm:/tmp/bidi_test2.txt" \
    "$test_file_2" \
    "$test_content_2" \
    "$test_file_2 qm:/tmp/bidi_test2.txt"

# Test 5: Copy to different directories
test_content_5="Directory copy test"
test_file_5=$(mktemp)
create_test_file "$test_file_5" "$test_content_5"

# Ensure target directory exists in container
qmctl exec bash -c "mkdir -p /tmp/copy_test_dir && echo 'Directory created'"

# When copying to a directory, the file keeps its original name
test_file_5_basename=$(basename "$test_file_5")
test_copy_with_verification \
    "Host to container directory" \
    "$test_file_5" \
    "qm:/tmp/copy_test_dir/" \
    "$test_content_5" \
    "$test_file_5"

# The actual destination file will be at /tmp/copy_test_dir/$test_file_5_basename
# Clean up the file we just copied
qmctl exec bash -c "rm -f '/tmp/copy_test_dir/$test_file_5_basename' && echo 'cleaned up test file'" >/dev/null 2>&1 || true

# Test 6: Container directory to host
test_content_6="Container directory to host test"

# Create file in container directory
qmctl exec bash -c "mkdir -p /tmp/container_source_dir && echo 'Source directory created'"
qmctl exec bash -c "echo '$test_content_6' > /tmp/container_source_dir/test_file.txt && echo 'File created in container directory'"

# Create target directory on host
mkdir -p /tmp/host_target_dir

test_copy_with_verification \
    "Container to host directory" \
    "qm:/tmp/container_source_dir/test_file.txt" \
    "/tmp/host_target_dir/test_file.txt" \
    "$test_content_6" \
    "/tmp/host_target_dir/test_file.txt"

# Cleanup test directories
qmctl exec bash -c "rm -rf /tmp/copy_test_dir /tmp/container_source_dir && echo 'cleaned up test directories'" >/dev/null 2>&1 || true
rm -rf /tmp/host_target_dir 2>/dev/null || true

# All tests passed
pass_message "All comprehensive qmctl copy tests completed successfully"