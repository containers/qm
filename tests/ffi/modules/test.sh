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

# Get result message of './modprobe_module'
msg=$(podman exec -it qm /bin/bash -c \
               "podman exec ffi-qm ./modprobe_module 2>&1")

# Check result message displays right.
if grep -eq "modprobe: FATAL: Module ext4 not found in directory /lib/modules/*" "$msg"; then
   if_error_exit "Module ext4 should not found in /lib/modules/ inside QM"
elif grep -Eq "ls: cannot access '(.+)': No such file or directory" "$msg"; then
   if_error_exit "Modules address under /lib/modules/ cannot access inside QM"
else
   info_message "Access /lib/modules to load any module via modprobe is impossible inside QM container"
   exit 0
fi
