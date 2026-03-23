#!/bin/bash -euvx

# shellcheck disable=SC1091

. ../common/prepare.sh

# Remove ffi-asil to free host RAM, then do disk_cleanup
trap 'cleanup_host_then_qm ffi-asil' EXIT

prepare_test

exec_cmd "podman run -d --rm --replace -d --name ffi-asil \
          quay.io/centos-sig-automotive/ffi-tools:latest \
          ./ASIL/20_percent_memory_eat > /dev/null"

reload_config
running_container_in_qm

podman exec qm podman exec ffi-qm ./QM/90_percent_memory_eat > /dev/null

if [ $? -eq 137 ]; then
    info_message "ffi-qm was killed by SIGKILL"
fi
exec_cmd "systemctl status qm --no-pager | grep \"qm.service: A process of this unit has been killed\""
