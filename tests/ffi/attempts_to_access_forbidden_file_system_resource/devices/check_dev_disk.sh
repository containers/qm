#!/bin/bash -euvx

# shellcheck disable=SC1091
. ../../../e2e/lib/utils

check_dev_disk_not_available(){
    # Check /dev/disk is not available in the QM partition
    if qmc exec test -d /dev/disk; then
        info_message "Found /dev/disk in the QM partition: $(qmc exec ls -l /dev/disk)"
        info_message "FAIL: check_dev_disk_not_available: Check for /dev/disk in the QM partition failed, it should not be available."
        exit 1
    else
        info_message "PASS: check_dev_disk_not_available: As expected, /dev/disk is not available in the QM partition."
        exit 0
    fi
}

check_dev_disk_not_available