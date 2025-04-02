#!/bin/bash -euvx

# shellcheck source=tests/ffi/common/prepare.sh
. ../common/prepare.sh

expected_result="Failed to set scheduler: Operation not permitted"

trap disk_cleanup EXIT
prepare_test
reload_config

running_container_in_qm

return_from_setscheduler=$(podman exec -it qm /usr/bin/podman exec -it ffi-qm ./QM/test_sched_setscheduler)

if [[ "${return_from_setscheduler}" =~ ${expected_result} ]]; then
    info_message "PASS: set_scheduler() syscall denied in QM."
else
    info_message "FAIL: set_scheduler() syscall can be executed in QM."
    exit 1
fi
