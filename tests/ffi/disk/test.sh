#!/bin/bash -evx

# shellcheck disable=SC1091

. ../common/prepare.sh

check_var_partition(){
   name_of_qm_var_partition="part /var/qm"

   # In the ostree image
   if stat /run/ostree-booted > /dev/null 2>&1; then
      name_of_qm_var_partition="part /var"
   else
      # In the centos cloud image
      local release_id
      release_id=$(grep -oP '(?<=^ID=)\w+' <<< "$(tr -d '"' < /etc/os-release)")
      if [[ "$release_id" == "centos" ]]; then
         name_of_qm_var_partition="part /usr/lib/qm/rootfs/var"
      fi
   fi

   # Prints all available block devices to make it easier to debug
   exec_cmd "lsblk"
   exec_cmd "df -kh"
   # If there is no separate /var partition this test will terminate early
   if [[ "$(lsblk -o 'MAJ:MIN,TYPE,MOUNTPOINTS')" =~ ${name_of_qm_var_partition} ]]; then
      info_message "A separate /var partition was detected on the image."
   else
      info_message "FAIL: No separate /var partition was detected on the image."
      info_message "Test terminated, it requires a separate /var disk partition for QM to run this test."
      exit 1
   fi
}

set_PodmanArgs(){
   podmanArgs_of_qm=$(grep "PodmanArgs" /usr/share/containers/systemd/qm.container)
   if [ -n "$podmanArgs_of_qm" ]; then
      podmanArgs_of_qm=$podmanArgs_of_qm" --memory 5G"
   else
      podmanArgs_of_qm="--memory 5G"
   fi
}

check_var_partition
trap disk_cleanup EXIT
prepare_test

set_PodmanArgs
cat << EOF > "${DROP_IN_DIR}"/oom.conf
[Container]
PodmanArgs=
PodmanArgs=${podmanArgs_of_qm}

EOF

reload_config

running_container_in_qm
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
