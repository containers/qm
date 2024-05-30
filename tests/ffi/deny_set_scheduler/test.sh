#!/bin/bash -euvx

. ../common/prepare.sh

expected_result="Failed to set scheduler: Operation not permitted"

disk_cleanup
prepare_test
reload_config

podman exec -it qm /bin/bash -c \
         'podman run -d  --replace --name ffi-qm \
          quay.io/centos-sig-automotive/ffi-tools:latest \
          tail -f /dev/null'

return_from_setscheduler=$(podman exec -it qm /bin/bash -c \
         'podman exec -it ffi-qm ./QM/test_sched_setscheduler')

if [[ "${return_from_setscheduler}" =~ ${expected_result} ]]; then
    info_message "set_scheduler() syscall denied in QM."
else
    info_message "set_scheduler() syscall can be executed in QM."
    exit 1
fi