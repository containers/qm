#!/bin/bash -euvx

# shellcheck disable=SC1091
. ../../../e2e/lib/utils

check_usr_lib_qm_not_accessible(){
    # Check /usr/lib/qm is not accessible in the QM partition
    if podman exec qm test -d /usr/lib/qm; then
        info_message "Found /usr/lib/qm in the QM partition: $(podman exec -t qm ls -l /usr/lib/qm)"
        info_message "FAIL: check_usr_lib_qm_not_accessible: Check for /usr/lib/qm in the QM partition failed, it should not be accessible."
        exit 1
    else
        info_message "PASS: check_usr_lib_qm_not_accessible: As expected, /usr/lib/qm is not accessible in the QM partition."
        exit 0
    fi
}

check_usr_lib_qm_not_accessible