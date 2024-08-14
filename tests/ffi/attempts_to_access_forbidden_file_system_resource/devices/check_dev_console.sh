#!/bin/bash -euvx

# shellcheck disable=SC1091
. ../../../e2e/lib/utils

check_dev_console_not_available(){
    # Check /dev/console is not available in the QM partition
    if podman exec qm test -c /dev/console; then
        info_message "Found /dev/console in the QM partition: $(podman exec -t qm ls -l /dev/console)"
        info_message "FAIL: check_dev_console_not_available: Check for /dev/console in the QM partition failed, it should not be available."
        exit 1
    else
        info_message "PASS: check_dev_console_not_available: As expected, /dev/console is not available in the QM partition."
        exit 0
    fi
}

check_dev_console_not_available