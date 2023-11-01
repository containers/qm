#!/bin/bash -euvx

# shellcheck disable=SC1091

. ../common/prepare.sh

export QM_HOST_REGISTRY_DIR="/var/qm/lib/containers/registry"
export QM_REGISTRY_DIR="/var/lib/containers/registry"

disk_cleanup
prepare_test
reload_config

exec_cmd "podman run -d --rm --replace -d --name ffi-asil \
          quay.io/centos-sig-automotive/ffi-tools:latest \
          ./ASIL/20_percent_memory_eat > /dev/null"
# Copy container image registry to /var/qm/lib/containers
image_id=$(podman images | grep quay.io/centos-sig-automotive/ffi-tools | awk -F " " '{print $3}')
if [ ! -d "${QM_HOST_REGISTRY_DIR}" ]; then
    exec_cmd "mkdir -p ${QM_HOST_REGISTRY_DIR}"
    exec_cmd "podman push ${image_id} dir:${QM_HOST_REGISTRY_DIR}/tools-ffi:latest"
fi

podman exec -it qm /bin/bash -c \
         "podman run  --replace --name ffi-qm  dir:${QM_REGISTRY_DIR}/tools-ffi:latest \
         ./QM/90_percent_memory_eat > /dev/null"

if [ $? -eq 137 ]; then
    echo ffi-qm was killed by SIGKILL
fi
exec_cmd "systemctl status qm --no-pager | grep \"qm.service: A process of this unit has been killed\""
