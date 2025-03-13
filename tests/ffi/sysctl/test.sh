#!/bin/bash -euvx

# shellcheck disable=SC1091

. ../common/prepare.sh

trap disk_cleanup EXIT
prepare_test
reload_config

# Run the ffi-tools container in qm vm
running_container_in_qm

# Get numbers of sysctl permission denied
sysctl_num=$(podman exec qm /usr/bin/podman exec ffi-qm ./setsysctl 2>&1 | grep -c "sysctl: permission denied on key")

# We execute 'X' sysctl call(s) inside a nested container running in a QM environment
# to determine if changes are allowed, which should be denied for:
#  - Network subsystem
#  - Virtual memory subsystem
SYSCTL_DENIED_COUNT=5
if [ "$sysctl_num" -eq "${SYSCTL_DENIED_COUNT}" ];then
   info_message "PASS: Attempt to change OS level are denied successfully inside QM container."
   exit 0
fi
