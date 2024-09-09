#!/bin/bash

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

disk_cleanup
prepare_images
reload_config

# Function to retrieve the PID with retries for a container
get_pid_with_retries() {
    local container_name=$1
    local retries=10
    local pid=""

    while [[ $retries -gt 0 ]]; do
        pid=$(podman inspect "$container_name" --format '{{.State.Pid}}' | tr -d '\r')
        if [[ -n "$pid" && "$pid" =~ ^[0-9]+$ ]]; then
            echo "$pid"
            return
        fi
        retries=$((retries - 1))
        sleep 1
    done

    echo "Error: Failed to retrieve a valid PID for the container '$container_name' after multiple attempts." >&2
    exit 1
}

# Function to safely retrieve oom_score_adj
get_oom_score_adj() {
    local pid=$1

    if [[ -f "/proc/$pid/oom_score_adj" ]]; then
        tr -d '\r\n' < "/proc/$pid/oom_score_adj"
    else
        echo "Error: /proc/$pid/oom_score_adj does not exist" >&2
        exit 1
    fi
}

# Start the FFI container inside qm
podman exec -it qm /bin/bash -c \
    "podman run -d --replace --name ffi-qm dir:${QM_REGISTRY_DIR}/tools-ffi:latest /usr/bin/sleep infinity > /dev/null"

# Check if ffi-qm container started successfully
QM_FFI_STATUS=$(podman exec -it qm /bin/bash -c "podman inspect ffi-qm --format '{{.State.Status}}'" | tr -d '\r')
if [[ "$QM_FFI_STATUS" != "running" ]]; then
    echo "Error: ffi-qm container failed to start. Status: $QM_FFI_STATUS" >&2
    exit 1
fi

# Retrieve the PID of the outer container (qm) with retries
QM_PID=$(get_pid_with_retries "qm")

# Retrieve the PID of the inner container (ffi-qm) directly within the qm container
QM_FFI_PID=$(podman exec -it qm /bin/bash -c "podman inspect ffi-qm --format '{{.State.Pid}}'" | tr -d '\r')

# Debugging: Output the retrieved PIDs
echo "Retrieved QM_PID: $QM_PID"
echo "Retrieved QM_FFI_PID: $QM_FFI_PID"

# Ensure that PIDs are valid before proceeding
if [[ -z "$QM_PID" || ! "$QM_PID" =~ ^[0-9]+$ ]]; then
    echo "Error: Invalid QM_PID: $QM_PID" >&2
    exit 1
fi

if [[ -z "$QM_FFI_PID" || ! "$QM_FFI_PID" =~ ^[0-9]+$ ]]; then
    echo "Error: Invalid QM_FFI_PID: $QM_FFI_PID" >&2
    echo "Check if the ffi-qm container was successfully started."
    exit 1
fi

# Get the oom_score_adj values
QM_OOM_SCORE_ADJ=$(get_oom_score_adj "$QM_PID")
QM_FFI_OOM_SCORE_ADJ=$(podman exec -it qm /bin/bash -c "cat /proc/$QM_FFI_PID/oom_score_adj" | tr -d '\r\n')

# Debugging: Output the retrieved oom_score_adj values
echo "Retrieved QM_OOM_SCORE_ADJ: '$QM_OOM_SCORE_ADJ'"
echo "Retrieved QM_FFI_OOM_SCORE_ADJ: '$QM_FFI_OOM_SCORE_ADJ'"

# Define the expected oom_score_adj values
OOM_SCORE_ADJ_EXPECTED=500
FFI_OOM_SCORE_ADJ_EXPECTED=750

# Check the oom_score_adj for the outer container
if [[ "$QM_OOM_SCORE_ADJ" -eq "$OOM_SCORE_ADJ_EXPECTED" ]]; then
    echo "PASS: qm.container oom_score_adj value == $OOM_SCORE_ADJ_EXPECTED"
else
    echo "FAIL: qm.container oom_score_adj value != $OOM_SCORE_ADJ_EXPECTED. Current value is ${QM_OOM_SCORE_ADJ}"
    exit 1
fi

# Check the oom_score_adj for the inner container
if [[ "$QM_FFI_OOM_SCORE_ADJ" -eq "$FFI_OOM_SCORE_ADJ_EXPECTED" ]]; then
    echo "PASS: ffi-qm container oom_score_adj == $FFI_OOM_SCORE_ADJ_EXPECTED"
else
    echo "FAIL: ffi-qm container oom_score_adj != $FFI_OOM_SCORE_ADJ_EXPECTED. Current value is '${QM_FFI_OOM_SCORE_ADJ}'"
    exit 1
fi

# Stop the inner FFI container
podman exec -it qm /bin/bash -c "podman stop ffi-qm > /dev/null"
