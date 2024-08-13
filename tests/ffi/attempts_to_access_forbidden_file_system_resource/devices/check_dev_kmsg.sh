#!/bin/bash -euvx

# shellcheck disable=SC1091
. ../../../e2e/lib/utils

check_dev_kmsg_not_available(){
    # Check /dev/kmsg is not available in the QM partition
    if podman exec qm test -c /dev/kmsg; then
        info_message "Found /dev/kmsg in the QM partition: $(podman exec -t qm ls -l /dev/kmsg)"
        info_message "FAIL: check_dev_kmsg_not_available: Check for /dev/kmsg in the QM partition failed, it should not be available."
        exit 1
    else
        info_message "PASS: check_dev_kmsg_not_available: As expected, /dev/kmsg is not available in the QM partition."
        exit 0
    fi
}

check_dev_kmsg_not_available