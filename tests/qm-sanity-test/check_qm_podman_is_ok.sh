#!/bin/bash -euvx

# shellcheck disable=SC1091
source ../e2e/lib/utils

# Verify podman in qm is ok
check_qm_podman_is_ok(){
    if podman exec qm bash -c "podman info" > /dev/null; then
        info_message "check_qm_podman_is_ok(): check 'podman info' in qm successfully."
        info_message "PASS: check_qm_podman_is_ok()"
        exit 0
    else
        info_message "FAIL: check_qm_podman_is_ok(): check 'podman info' in qm failed.\n $(podman exec qm bash -c "podman info")"
        exit 1
    fi
}

check_qm_podman_is_ok