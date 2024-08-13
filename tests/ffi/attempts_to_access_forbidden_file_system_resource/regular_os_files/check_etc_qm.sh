#!/bin/bash -euvx

# shellcheck disable=SC1091
. ../../../e2e/lib/utils

check_etc_qm_not_accessible(){
    # Check /etc/qm is not accessible in the QM partition
    if podman exec qm test -d /etc/qm; then
        info_message "Found /etc/qm in the QM partition: $(podman exec -t qm ls -l /etc/qm)"
        info_message "FAIL: check_etc_qm_not_accessible: Check for /etc/qm in the QM partition failed, it should not be accessible."
        exit 1
    else
        info_message "PASS: check_etc_qm_not_accessible: As expected, /etc/qm is not accessible in the QM partition."
        exit 0
    fi
}

check_etc_qm_not_accessible