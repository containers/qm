#!/bin/bash -euvx

# shellcheck disable=SC1091
source ../e2e/lib/utils

# Verify /var partition exist
check_var_partition_exist(){
    info_message "Journal for qm bluechi-agent:\n"
    journalctl -r -u qm -n 100

    # /var on ostree image
    if stat /run/ostree-booted > /dev/null 2>&1; then
        expected_var_partition="part /var"
    # /var on c9s image
    else
        expected_var_partition="part /usr/lib/qm/rootfs/var"
    fi

    if [[ "$(lsblk -o 'MAJ:MIN,TYPE,MOUNTPOINTS')" =~ ${expected_var_partition} ]]; then
        info_message "check_var_partition_exist: /var exists in QM"
        info_message "PASS: check_var_partition_exist()"
        exit 0
    else
        info_message "FAIL: check_var_partition_exist: /var does not exists in QM"
        exit 1
    fi
}

check_var_partition_exist