#!/bin/bash -euvx

# shellcheck source=tests/ffi/common/prepare.sh
. ../common/prepare.sh

expected_result="Failed to set scheduler: Operation not permitted"

disk_cleanup
prepare_test
reload_config

prepare_images
run_container_in_qm "ffi-qm"

return_from_setscheduler=$(podman exec -it qm /bin/bash -c \
         'podman exec -it ffi-qm ./QM/test_sched_setscheduler')

if [[ "${return_from_setscheduler}" =~ ${expected_result} ]]; then
    info_message "set_scheduler() syscall denied in QM."
else
    info_message "set_scheduler() syscall can be executed in QM."
    exit 1
fi
