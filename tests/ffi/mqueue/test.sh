#!/bin/bash -euvx

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# shellcheck disable=SC1091

. ../common/prepare.sh

# Number of host message queues to test (configurable via environment)
HOST_QUEUE_COUNT=${HOST_QUEUE_COUNT:-3}

# Validate HOST_QUEUE_COUNT is reasonable
if ! [[ "$HOST_QUEUE_COUNT" =~ ^[1-9][0-9]*$ ]] || [ "$HOST_QUEUE_COUNT" -gt 100 ]; then
    echo "ERROR: HOST_QUEUE_COUNT must be a positive integer between 1 and 100, got: $HOST_QUEUE_COUNT"
    exit 1
fi

# Comprehensive cleanup function to ensure no state is left behind
# shellcheck disable=SC2317  # Function is called indirectly via trap
comprehensive_cleanup() {
    info_message "Running comprehensive cleanup"

    # Clean up host message queues
    if [ -d "/dev/mqueue" ]; then
        for mq_file in /dev/mqueue/host_test_queue_*; do
            if [ -e "$mq_file" ]; then
                info_message "Cleaning up leftover host message queue: $mq_file"
                rm -f "$mq_file" 2>/dev/null || true
            fi
        done
    fi

    # Clean up container message queues (if container is running)
    if podman ps --format "{{.Names}}" | grep -q "^qm$" 2>/dev/null; then
        info_message "Cleaning up container message queues"
        podman exec qm bash -c 'for mq in /dev/mqueue/test_queue_*; do [ -e "$mq" ] && rm -f "$mq" 2>/dev/null || true; done' 2>/dev/null || true
    fi

    # Clean up compiled binaries
    if [ -f "./test_host_mqueue" ]; then
        info_message "Cleaning up host compiled test program"
        make clean 2>/dev/null || true
    fi

    # Run the original disk cleanup
    disk_cleanup 2>/dev/null || true
}

trap comprehensive_cleanup EXIT
prepare_test
reload_config

# Run the ffi-tools container in qm vm
running_container_in_qm

# Function to test message queues on the host system
test_host_mqueue() {
    local action="$1"
    local mqueue_names=()
    local created_count=0

    info_message "Testing host message queue availability ($action container test)"

    # Get current host mqueue limit
    HOST_MQUEUE_LIMIT=$(sysctl -n fs.mqueue.queues_max)
    info_message "Host fs.mqueue.queues_max value: $HOST_MQUEUE_LIMIT"

    # Build the host test program if it doesn't exist
    if [ ! -f "./test_host_mqueue" ]; then
        # Install development tools if needed
        exec_cmd "dnf install -y gcc make || true"

        # Build the test program
        info_message "Building host message queue test program"
        make test_host_mqueue
    fi

    # Try to create message queues on the host to verify they work
    for i in $(seq 1 "$HOST_QUEUE_COUNT"); do
        local queue_name="/host_test_queue_${action}_$i"
        mqueue_names+=("$queue_name")

        # Clean up any existing queue first
        if [ -e "/dev/mqueue$queue_name" ]; then
            rm -f "/dev/mqueue$queue_name" 2>/dev/null || true
        fi

        # Use the pre-built test program
        if ./test_host_mqueue "$queue_name"; then
            created_count=$((created_count + 1))
            info_message "Host queue $queue_name created successfully"
        else
            info_message "FAIL: Could not create host queue $queue_name"
            return 1
        fi
    done

    info_message "PASS: Successfully created $created_count host message queues $action container test"
    if [ "$action" = "after" ]; then
        local total_queues=$((HOST_QUEUE_COUNT * 2))
        info_message "Host now has $total_queues total queues ($HOST_QUEUE_COUNT before + $HOST_QUEUE_COUNT after), demonstrating isolation from container's 4-queue limit"
        # Don't clean up here - comprehensive_cleanup at exit will handle all host queues
    fi

    return 0
}

# Function to test the message queue limit
test_mqueue_limit() {
    info_message "Testing message queue limit enforcement in QM container"

    # Check if the sysctl setting is applied correctly
    MQUEUE_LIMIT=$(podman exec qm sysctl -n fs.mqueue.queues_max)
    info_message "Current fs.mqueue.queues_max value in QM: $MQUEUE_LIMIT"

    if [ "$MQUEUE_LIMIT" != "4" ]; then
        info_message "FAIL: Expected fs.mqueue.queues_max=4, but got $MQUEUE_LIMIT"
        exit 1
    fi

    # Install development tools if needed
    exec_cmd "dnf install --setopt=reposdir=/etc/yum.repos.d  --installroot=/usr/lib/qm/rootfs -y gcc make || true"

    # Create test directory and copy the test files to the QM container
    exec_cmd "podman exec qm mkdir -p /tmp/mqueue_test"
    exec_cmd "podman cp test_mqueue_limit.c qm:/tmp/mqueue_test/"
    exec_cmd "podman cp Makefile qm:/tmp/mqueue_test/"

    # Compile the test program inside QM
    exec_cmd "podman exec qm bash -c 'cd /tmp/mqueue_test && make test_mqueue_limit'"

    # Run the test program inside QM
    if exec_cmd "podman exec qm bash -c 'cd /tmp/mqueue_test && ./test_mqueue_limit'"; then
        info_message "PASS: Message queue limit test passed successfully"
    else
        info_message "FAIL: Message queue limit test failed"
        exit 1
    fi
}

# Execute the tests
info_message "=== Starting message queue isolation test ==="

# Test 1: Verify host message queues work before container test
test_host_mqueue "before"

# Test 2: Run the container message queue limit test
test_mqueue_limit

# Test 3: Verify host message queues still work after container test
test_host_mqueue "after"

info_message "=== All message queue tests passed successfully ==="

# Clean up compiled binaries
info_message "Cleaning up compiled test programs"

exit 0
