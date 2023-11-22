#!/bin/bash

set -ux

# shellcheck disable=SC1094
# shellcheck source=tests/e2e/lib/utils
source ../e2e/lib/utils

CONTROL_CONTAINER_NAME="${CONTROL_CONTAINER_NAME:-control}"

test_qm_readonly_unit_file() {

    local qm_cmd

    echo
    info_message "Connected to \033[92m${CONTROL_CONTAINER_NAME}\033[0m, trying to update unit file"
    if [  "${CONTROL_CONTAINER_NAME}" != "host" ]; then
        qm_cmd="podman exec "
        qm_cmd+="${CONTROL_CONTAINER_NAME} "
    fi
    qm_cmd+="podman exec qm bash -c 'echo true >> /usr/lib/systemd/system/bluechi-agent.service' 2>&1"
    sleep 1
    cmd_result=$(eval "${qm_cmd}")

    grep -E  "Read-only file system" <<< "${cmd_result}"
    if_error_exit "Expecting Read-only file system"
}

test_qm_readonly_unit_file
