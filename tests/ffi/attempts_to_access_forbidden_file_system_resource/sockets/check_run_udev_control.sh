#!/bin/bash -euvx

# shellcheck disable=SC1091
. ../../../e2e/lib/utils

check_run_udev_control_not_exist(){
    # Check /run/udev/control is not exist in the QM partition
    if podman exec qm test -e /run/udev/control; then
        info_message "Found /run/udev/control in the QM partition: $(podman exec -t qm ls -l /run/udev/control)"
        info_message "FAIL: check_run_udev_control_not_exist: Check for /run/udev/control in the QM partition failed, it should not exist."
        exit 1
    else
        info_message "PASS: check_run_udev_control_not_exist: As expected, /run/udev/control dose not exist in the QM partition."
        exit 0
    fi
}

check_run_udev_control_not_exist