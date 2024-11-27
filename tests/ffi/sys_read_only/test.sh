#!/bin/bash -euvx

# shellcheck disable=SC1091
. ../../e2e/lib/utils

check_sys_read_only(){
    # Check /sys is read-only in QM partition
    if podman exec qm /bin/sh -c 'test -r /sys && test ! -w /sys'; then
        info_message "PASS: check_sys_read_only: As expected, /sys is read-only in QM partition."
        exit 0
    else
        info_message "Found a non-read-only /sys folder in QM partition: $(podman exec -t qm ls -ld /sys)"
        info_message "FAIL: check_sys_read_only: Check for /sys in QM partition failed, it should be read-only."
        exit 1
    fi
}

check_sys_read_only
