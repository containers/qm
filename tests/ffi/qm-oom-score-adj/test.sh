#!/bin/bash -euvx

# shellcheck disable=SC1091

. ../common/prepare.sh

export QM_HOST_REGISTRY_DIR="/var/qm/lib/containers/registry"
export QM_REGISTRY_DIR="/var/lib/containers/registry"

disk_cleanup
prepare_test
reload_config

# Copy container image registry to /var/qm/lib/containers
image_id=$(podman images | grep quay.io/centos-sig-automotive/ffi-tools | awk -F " " '{print $3}')
if [ ! -d "${QM_HOST_REGISTRY_DIR}" ]; then
    exec_cmd "mkdir -p ${QM_HOST_REGISTRY_DIR}"
    exec_cmd "podman push ${image_id} dir:${QM_HOST_REGISTRY_DIR}/tools-ffi:latest"
fi

podman exec -it qm /bin/bash -c \
         "podman run -d --replace --name ffi-qm  dir:${QM_REGISTRY_DIR}/tools-ffi:latest \
          /usr/bin/sleep infinity > /dev/null"


QM_PID=$(podman inspect qm --format '{{.State.Pid}}' | tr -d '\r')
QM_FFI_PID=$(podman exec -it qm /bin/bash -c "podman inspect ffi-qm --format '{{.State.Pid}}'" | tr -d '\r')

QM_OOM_SCORE_ADJ=$(cat "/proc/$QM_PID/oom_score_adj")
QM_FFI_OOM_SCORE_ADJ=$(podman exec -it qm /bin/bash -c "cat /proc/$QM_FFI_PID/oom_score_adj" | tr -d '\r')


# "500" is the oom_score_adj defined for the qm/qm.container.
if [ "$QM_OOM_SCORE_ADJ" -eq "500" ]; then
    info_message "PASS: qm.container oom_score_adj value == 500"
else
    info_message "FAIL: qm.container oom_score_adj value != 500"
    exit 1
fi


# "750" is the oom_score_adj defined in the qm/containers.conf as default value
# for the containers that would run inside of the qm container.
if [ "$QM_FFI_OOM_SCORE_ADJ" -eq "750" ]; then
    info_message "PASS: qm containers oom_score_adj == 750"
else
    info_message "FAIL: qm containers oom_score_adj != 750"
    exit 1
fi


podman exec -it qm /bin/bash -c "podman stop ffi-qm > /dev/null"

