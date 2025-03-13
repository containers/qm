#!/bin/bash -vx

# shellcheck disable=SC1091

. ../common/prepare.sh

check_var_partition(){
   if stat /run/ostree-booted > /dev/null 2>&1; then
      qm_var_partition="part /var/qm"
   else
      qm_var_partition="part /usr/lib/qm/rootfs/var/qm"
   fi

   if [[ "$(lsblk -o 'MAJ:MIN,TYPE,MOUNTPOINTS')" =~ ${qm_var_partition} ]]; then
      info_message "A separate /var/qm partition was detected on the image."
   else
      lsblk
      df -kh
      info_message "FAIL: No separate /var/qm partition was detected on the image."
      info_message "Test terminated, it requires a separate /var disk partition for QM to run this test."
      exit 1
   fi
}

check_var_partition
trap disk_cleanup EXIT
prepare_test

cat << EOF > "${DROP_IN_DIR}"/oom.conf
[Service]
OOMScoreAdjust=
OOMScoreAdjust=1000

[Container]
PodmanArgs=
PodmanArgs=--pids-limit=-1 --security-opt seccomp=/usr/share/qm/seccomp-no-rt.json --security-opt label=nested --security-opt unmask=all --memory 5G

EOF

reload_config

run_container_in_qm "ffi-qm"

exec_cmd "podman exec -it qm /bin/bash -c \
         'podman exec -it ffi-qm ./QM/file-allocate'"

if ! eval "fallocate -l 2G /root/file.lock" ; then
   info_message "FAIL: No space left on device."
   podman exec -it qm /bin/bash -c 'podman  rmi -i -f --all; echo $?'
   exit 1
fi

ls -lh /root/file.lock
info_message "PASS: The disk in qm is full, host is not affected."

# Calling cleanup QM directory to workaround exit code once
# /var/qm disk is full.
podman exec -it qm /bin/bash -c 'podman  rmi -i -f --all; echo $?'
