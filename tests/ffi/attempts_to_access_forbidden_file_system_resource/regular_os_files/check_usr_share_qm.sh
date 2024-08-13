#!/bin/bash -euvx

# shellcheck disable=SC1091
. ../../../e2e/lib/utils

check_usr_share_qm_not_accessible(){
    # Check /usr/share/qm is not accessible in the QM partition
    if podman exec qm test -d /usr/share/qm; then
        info_message "Found /usr/share/qm in the QM partition: $(podman exec -t qm ls -l /usr/share/qm)"
        info_message "FAIL: check_usr_share_qm_not_accessible: Check for /usr/share/qm in the QM partition failed, it should not be accessible."
        exit 1
    else
        info_message "PASS: check_usr_share_qm_not_accessible: As expected, /usr/share/qm is not accessible in the QM partition."
        exit 0
    fi
}

check_usr_share_qm_not_accessible