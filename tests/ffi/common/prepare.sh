#!/bin/bash
# shellcheck disable=SC1091
. ../../e2e/lib/utils

DROP_IN_DIR="/etc/containers/systemd/qm.container.d/"
export QM_HOST_REGISTRY_DIR="/var/qm/lib/containers/registry"
export QM_REGISTRY_DIR="/var/lib/containers/registry"

prepare_test() {
   # Search variables for update file in qm.container
   # qm_service_file=$(systemctl show -P  SourcePath qm)
   # Create qm container custom config folder for qm drop-in file.
   # Use drop-in files to update qm_service_file
   # please refer 'zcat $(man -w qm.8) | grep -i "^\.sh" | grep drop-in'
   exec_cmd "mkdir -p ${DROP_IN_DIR}"
}

disk_cleanup() {
   exec_cmd "podman exec -it qm /bin/bash -c \"podman  rmi -f --all\""
   # Clean large size files created by tests inside qm part
   remove_file=$(find /var/qm -size  +2G)
   exec_cmd "rm -rf $remove_file"
   # Clean drop-in files used for tests
   if test -d "${DROP_IN_DIR=}"; then
      exec_cmd "rm -rf ${DROP_IN_DIR}"
   fi
   exec_cmd "systemctl daemon-reload"
   exec_cmd "systemctl restart qm"
   # Clean large size files created by tests inside host part
   remove_file=$(find /root -size  +1G)
   exec_cmd "rm -f $remove_file"
}

reload_config() {
   exec_cmd "systemctl daemon-reload"
   exec_cmd "systemctl restart qm"
}

prepare_images() {
   exec_cmd "podman pull quay.io/centos-sig-automotive/ffi-tools:latest"
   # Copy container image registry to /var/qm/lib/containers
   image_id=$(podman images | grep quay.io/centos-sig-automotive/ffi-tools | awk -F " " '{print $3}')
   if [ ! -d "${QM_HOST_REGISTRY_DIR}" ]; then
       exec_cmd "mkdir -p ${QM_HOST_REGISTRY_DIR}"
       exec_cmd "podman push ${image_id} dir:${QM_HOST_REGISTRY_DIR}/tools-ffi:latest"
       # Remove image to save /var space
       exec_cmd "podman rmi -f ${image_id}"
   fi
}

run_container_in_qm() {
   local container_name
   local tmp_image_dir
   local run_ctr_in_qm
   # Clean tmp image directory
   tmp_image_dir=$(podman info | grep  CopyTmp | awk -F":" '{print $2}')
   container_name="${1}"

   exec_cmd "podman exec -it qm /bin/bash -c \
      \"rm -rf ${tmp_image_dir}/*\""
   run_ctr_in_qm="podman exec -it qm /bin/bash -c \
      \"podman run -d --net host  --replace --name ${container_name} \
      dir:${QM_REGISTRY_DIR}/tools-ffi:latest \
      tail -f /dev/null\""
   exec_cmd "${run_ctr_in_qm}"
}
