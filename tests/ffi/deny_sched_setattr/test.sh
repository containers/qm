#!/bin/bash -euvx

# shellcheck source=tests/ffi/common/prepare.sh
. ../common/prepare.sh

expected_result="sched_setattr failed: Operation not permitted"

trap disk_cleanup EXIT
prepare_test
reload_config

running_container_in_qm

return_from_sched_setattr=$(podman exec -it qm /usr/bin/podman exec -it ffi-qm ./QM/execute_sched_setattr)

# shellcheck disable=SC2076
if [[ "${return_from_sched_setattr}" =~ "${expected_result}" ]]; then
    info_message "PASS: QM not allow SCHED_DEADLINE be set via sched_setattr() syscall."
else
    info_message "FAIL: SCHED_DEADLINE can not be set via sched_setattr() syscall in QM."
    exit 1
fi
