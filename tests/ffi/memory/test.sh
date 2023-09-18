#!/bin/bash -eux

# shellcheck disable=SC1091

. ../memory/prepare.sh

prepare_test
reload_config

podman run --rm --replace -d --name ffi-asil \
     quay.io/centos-sig-automotive/ffi-tools:latest \
     ./ASIL/20_percent_memory_eat > /dev/null
# Copy container image registry to /var/qm/lib/containers
image_id=$(podman images | grep quay.io/centos-sig-automotive/ffi-tools | awk -F " " '{print $3}')
mkdir -p /var/qm/lib/containers/registry
podman push  "${image_id}" dir:/var/qm/lib/containers/registry/tools-ffi:latest
podman exec -it qm /bin/bash -c \
       "podman run  --replace --name ffi-qm  dir:/var/lib/containers/registry/tools-ffi:latest \
       ./QM/90_percent_memory_eat > /dev/null"

if [ $? -eq 137 ]; then
    echo ffi-qm was killed by SIGKILL
fi
systemctl status qm --no-pager | grep "qm.service: A process of this unit has been killed"
