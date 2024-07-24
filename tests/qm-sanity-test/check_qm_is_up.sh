#!/bin/bash -euvx

# shellcheck disable=SC1091
source ../e2e/lib/utils

# Verify qm is up and running
check_qm_is_up(){
    if [ "$(systemctl is-active qm)" == "active" ]; then
        info_message "check_qm_is_up(): qm is active"
        info_message "PASS: check_qm_is_up()"
        exit 0
    else
        info_message "FAIL: check_qm_is_up(): qm is not active"
        exit 1
    fi
}

check_qm_is_up