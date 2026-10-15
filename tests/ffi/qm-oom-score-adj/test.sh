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

trap disk_cleanup EXIT
prepare_test
reload_config

# Start the FFI container inside qm
running_container_in_qm

# Check if ffi-qm container started successfully
QM_FFI_STATUS=$(qmc exec podman inspect ffi-qm --format '{{.State.Status}}')
if [[ "$QM_FFI_STATUS" != "running" ]]; then
    info_message "Error: ffi-qm container failed to start. Status: $QM_FFI_STATUS" >&2
    exit 1
fi

# Retrieve the PID of the outer container (qm) with retries
QM_PID=1 # PID 1 in QM's PID namespace

# Retrieve the PID of the inner container (ffi-qm) directly within the qm container
QM_FFI_PID=$(qmc exec podman inspect ffi-qm --format '{{.State.Pid}}')

# Debugging: Output the retrieved PIDs
info_message "Retrieved QM_PID: $QM_PID"
info_message "Retrieved QM_FFI_PID: $QM_FFI_PID"

# Ensure that PIDs are valid before proceeding
if [[ -z "$QM_PID" || ! "$QM_PID" =~ ^[0-9]+$ ]]; then
    info_message "Error: Invalid QM_PID: $QM_PID" >&2
    exit 1
fi

if [[ -z "$QM_FFI_PID" || ! "$QM_FFI_PID" =~ ^[0-9]+$ ]]; then
    info_message "Error: Invalid QM_FFI_PID: $QM_FFI_PID" >&2
    info_message "Check if the ffi-qm container was successfully started."
    exit 1
fi

# Get the oom_score_adj values
QM_OOM_SCORE_ADJ=$(qmc exec cat /proc/1/oom_score_adj)
QM_FFI_OOM_SCORE_ADJ=$(qmc exec /bin/bash -c "cat /proc/$QM_FFI_PID/oom_score_adj" | tr -d '\r\n')

# Debugging: Output the retrieved oom_score_adj values
info_message "Retrieved QM_OOM_SCORE_ADJ: '$QM_OOM_SCORE_ADJ'"
info_message "Retrieved QM_FFI_OOM_SCORE_ADJ: '$QM_FFI_OOM_SCORE_ADJ'"

# Define the expected oom_score_adj values
OOM_SCORE_ADJ_EXPECTED=500
FFI_OOM_SCORE_ADJ_EXPECTED=750

# Check the oom_score_adj for the outer container
if [[ "$QM_OOM_SCORE_ADJ" -eq "$OOM_SCORE_ADJ_EXPECTED" ]]; then
    info_message "PASS: qm.service payload oom_score_adj value == $OOM_SCORE_ADJ_EXPECTED"
else
    info_message "FAIL: qm.service payload oom_score_adj value != $OOM_SCORE_ADJ_EXPECTED. Current value is ${QM_OOM_SCORE_ADJ}"
    exit 1
fi

# Check the oom_score_adj for the inner container
if [[ "$QM_FFI_OOM_SCORE_ADJ" -eq "$FFI_OOM_SCORE_ADJ_EXPECTED" ]]; then
    info_message "PASS: ffi-qm container oom_score_adj == $FFI_OOM_SCORE_ADJ_EXPECTED"
else
    info_message "FAIL: ffi-qm container oom_score_adj != $FFI_OOM_SCORE_ADJ_EXPECTED. Current value is '${QM_FFI_OOM_SCORE_ADJ}'"
    exit 1
fi

# Stop the inner FFI container
qmc exec /bin/bash -c "podman stop ffi-qm > /dev/null"
