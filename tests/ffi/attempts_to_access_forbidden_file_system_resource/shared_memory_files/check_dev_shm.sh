#!/bin/bash -euvx

# shellcheck disable=SC1091
. ../../../e2e/lib/utils

check_dev_shm_file_not_visible_in_qm(){
    # Create a file /dev/shm/on-host outside the QM partition
    touch /dev/shm/on-host
    if test -e /dev/shm/on-host; then
        info_message "Successfully created the file /dev/shm/on-host outside the QM partition."
    else
        info_message "FAIL: check_dev_shm_file_not_visible_in_qm: Failed to create /dev/shm/on-host outside the QM partition."
        exit 1
    fi

    # Check for file /dev/shm/on-host is not visible inside the QM partition.
    if podman exec qm test -e /dev/shm/on-host; then
        info_message "Found /dev/shm/on-host in the QM partition: $(podman exec -t qm ls -l /dev/shm/on-host)"
        info_message "FAIL: check_dev_shm_file_not_visible_in_qm: Check for /dev/shm/on-host failed, it should not be visible in the QM partition."
        exit 1
    else
        info_message "PASS: check_dev_shm_file_not_visible_in_qm: As expected, /dev/shm/on-host is not visible in the QM partition."
        exit 0
    fi
}

check_dev_shm_file_not_visible_in_qm