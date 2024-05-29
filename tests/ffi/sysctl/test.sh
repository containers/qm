#!/bin/bash -euvx

# shellcheck disable=SC1091

. ../common/prepare.sh

export QM_HOST_REGISTRY_DIR="/var/qm/lib/containers/registry"
export QM_REGISTRY_DIR="/var/lib/containers/registry"

disk_cleanup
prepare_test
reload_config

# Download ffi-tools container and push ffi-tools image into QM registry
prepare_images

# Run the ffi-tools container in qm vm
run_container_in_qm ffi-qm

# Get numbers of sysctl permission denied
sysctl_num=$(podman exec qm /bin/bash -c \
               "podman exec ffi-qm ./setsysctl 2>&1" | grep -c "sysctl: permission denied on key")

# We execute 'X' sysctl call(s) inside a nested container running in a QM environment
# to determine if changes are allowed, which should be denied for:
#  - Network subsystem
#  - Virtual memory subsystem
SYSCTL_DENIED_COUNT=5
if [ $sysctl_num -eq "${SYSCTL_DENIED_COUNT}" ];then
   info_message "Attempt to change OS level are denied successfully inside QM container."
   exit 0
fi
