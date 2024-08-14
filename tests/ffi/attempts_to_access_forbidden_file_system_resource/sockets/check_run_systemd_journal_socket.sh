#!/bin/bash -euvx

# shellcheck disable=SC1091
. ../../../e2e/lib/utils

check_run_systemd_journal_socket_inode_number(){
    # Get inode number of /run/systemd/journal/socket inside and outside of the QM partition.
    inode_number_in_host=$(stat --printf='%i' /run/systemd/journal/socket)
    inode_number_in_qm=$(podman exec qm stat --printf='%i' /run/systemd/journal/socket)

    # Check if the inode numbers inside and outside of the QM partition are different.
    if [ "$inode_number_in_host" -eq "$inode_number_in_qm" ]; then
        info_message "In the host, inode number of /run/systemd/journal/socket is: ${inode_number_in_host}"
        info_message "In the QM partition, inode number of /run/systemd/journal/socket is: ${inode_number_in_qm}"
        info_message "FAIL: check_run_systemd_journal_socket_inode_number: Checking inode number of /run/systemd/journal/socket failed, \
it should have different inode number inside and outside of the QM partition."
        exit 1
    else
        info_message "PASS: check_run_systemd_journal_socket_inode_number: As expected, /run/systemd/journal/socket have different \
inode number inside and outside of the QM partition."
        exit 0
    fi
}

check_run_systemd_journal_socket_inode_number