#!/bin/bash -euvx

# shellcheck disable=SC1091

. ../common/prepare.sh

disk_cleanup
prepare_test

cat << EOF > "${DROP_IN_DIR}"/oom.conf
[Service]
OOMScoreAdjust=
OOMScoreAdjust=1000
EOF

reload_config
prepare_images

exec_cmd "podman run -d --rm --replace -d --name ffi-asil \
          quay.io/centos-sig-automotive/ffi-tools:latest \
          ./ASIL/20_percent_memory_eat > /dev/null"

podman exec -it qm /bin/bash -c \
         "podman run  --replace --name ffi-qm  dir:${QM_REGISTRY_DIR}/tools-ffi:latest \
         ./QM/90_percent_memory_eat > /dev/null"

if [ $? -eq 137 ]; then
    echo ffi-qm was killed by SIGKILL
fi
exec_cmd "systemctl status qm --no-pager | grep \"qm.service: A process of this unit has been killed\""
