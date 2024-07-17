#!/bin/bash -euvx

# shellcheck source=tests/ffi/common/prepare.sh
. ../common/prepare.sh

expected_result="sched_setattr failed: Operation not permitted"

disk_cleanup
prepare_test
reload_config

prepare_images
run_container_in_qm "ffi-qm"

return_from_sched_setattr=$(podman exec -it qm /bin/bash -c \
         'podman exec -it ffi-qm ./QM/execute_sched_setattr')

# shellcheck disable=SC2076
if [[ "${return_from_sched_setattr}" =~ "${expected_result}" ]]; then
    info_message "QM not allow SCHED_DEADLINE be set via sched_setattr() syscall."
else
    info_message "Failure: SCHED_DEADLINE can not be set via sched_setattr() syscall in QM."
    exit 1
fi
