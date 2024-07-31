#!/bin/bash -euvx

# shellcheck disable=SC1091

. ../common/prepare.sh

disk_cleanup
prepare_images
reload_config

podman exec -it qm /bin/bash -c \
         "podman run -d --replace --name ffi-qm  dir:${QM_REGISTRY_DIR}/tools-ffi:latest \
          /usr/bin/sleep infinity > /dev/null"


QM_PID=$(podman inspect qm --format '{{.State.Pid}}' | tr -d '\r')
QM_FFI_PID=$(podman exec -it qm /bin/bash -c "podman inspect ffi-qm --format '{{.State.Pid}}'" | tr -d '\r')

QM_OOM_SCORE_ADJ=$(cat "/proc/$QM_PID/oom_score_adj")
QM_FFI_OOM_SCORE_ADJ=$(podman exec -it qm /bin/bash -c "cat /proc/$QM_FFI_PID/oom_score_adj" | tr -d '\r')


# Define a constant for the oom_score_adj value
# "500" is the oom_score_adj defined for the qm/qm.container.
OOM_SCORE_ADJ_EXPECTED=500

if [ "$QM_OOM_SCORE_ADJ" -eq "$OOM_SCORE_ADJ_EXPECTED" ]; then
    info_message "PASS: qm.container oom_score_adj value == $OOM_SCORE_ADJ_EXPECTED"
else
    info_message "FAIL: qm.container oom_score_adj value != $OOM_SCORE_ADJ_EXPECTED. Current value is ${QM_OOM_SCORE_ADJ}"
    exit 1
fi

# "750" is the oom_score_adj defined in the qm/containers.conf as default value
# for the containers that would run inside of the qm container.
# Check the oom_score_adj value for QM FFI
FFI_OOM_SCORE_ADJ_EXPECTED=750

if [ "$QM_FFI_OOM_SCORE_ADJ" -eq "$FFI_OOM_SCORE_ADJ_EXPECTED" ]; then
    info_message "PASS: qm containers oom_score_adj == $FFI_OOM_SCORE_ADJ_EXPECTED"
else
    info_message "FAIL: qm containers oom_score_adj != $FFI_OOM_SCORE_ADJ_EXPECTED. Current value is ${QM_FFI_OOM_SCORE_ADJ}"
    exit 1
fi

podman exec -it qm /bin/bash -c "podman stop ffi-qm > /dev/null"

