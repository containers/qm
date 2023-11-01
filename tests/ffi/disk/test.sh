#!/bin/bash -euvx

# shellcheck disable=SC1091

. ../common/prepare.sh

disk_cleanup
prepare_test
reload_config

podman exec -it qm /bin/bash -c \
       "podman run -d  --replace --name ffi-qm  quay.io/centos-sig-automotive/ffi-tools:latest \
       tail -f /dev/null"

podman exec -it qm /bin/bash -c \
       "podman exec -it ffi-qm ./QM/file-allocate > /dev/null"

if ! eval "fallocate -l 2G /root/file.lock" ; then
   echo "No space left on device"
   exit 1
fi

ls -lh /root/file.lock


