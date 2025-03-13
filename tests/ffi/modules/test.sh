#!/bin/bash -uvx

# shellcheck disable=SC1091

. ../common/prepare.sh

trap disk_cleanup EXIT
prepare_test
reload_config

# Run the ffi-tools container in qm vm
running_container_in_qm

# Get result message of './modprobe_module'
msg=$(podman exec -it qm /usr/bin/podman exec -it ffi-qm ./modprobe_module 2>&1)

# Check result message displays right.
if grep -eq "modprobe: FATAL: Module ext4 not found in directory /lib/modules/*" "$msg"; then
   if_error_exit "Module ext4 should not found in /lib/modules/ inside QM"
elif grep -Eq "ls: cannot access '(.+)': No such file or directory" "$msg"; then
   if_error_exit "Modules address under /lib/modules/ cannot access inside QM"
else
   info_message "Access /lib/modules to load any module via modprobe is impossible inside QM container"
   exit 0
fi
