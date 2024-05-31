#!/bin/bash -euvx

. ../common/prepare.sh

export QM_HOST_REGISTRY_DIR="/var/qm/lib/containers/registry"
export QM_REGISTRY_DIR="/var/lib/containers/registry"
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