#!/bin/bash -euvx

# shellcheck disable=SC1091
. ../../e2e/lib/utils

check_dev_mem_not_present(){
    # Check /dev/mem is not present in QM partition
    if podman exec qm test -e /dev/mem; then
        info_message "Found /dev/mem in QM partition: $(podman exec -t qm ls -l /dev/mem)"
        info_message "FAIL: check_dev_mem_not_present: Check for /dev/mem in QM partition failed, it should not be present."
        exit 1
    else
        info_message "PASS: check_dev_mem_not_present: As expected, /dev/mem is not present in QM partition."
        exit 0
    fi
}

check_dev_mem_not_present
