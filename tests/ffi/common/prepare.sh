#!/bin/bash
# shellcheck disable=SC1091
. ../../e2e/lib/utils

prepare_test() {
   qm_service_file=$(systemctl show -P  SourcePath qm)
   #create backup file for qm unit file
   qm_service_backup=$(mktemp -d -p /tmp)/qm.service
   if_error_exit "cannot create temp dir under /tmp/"
   exec_cmd "cp ${qm_service_file} ${qm_service_backup}"
   # Remove 'DropCapability=sys_resource' enable nested container in QM
   exec_cmd "sed -i 's|DropCapability=sys_resource|#DropCapability=sys_resource|' \
            ${qm_service_file}"
   # FIXME: QM is failing to start podman command
   # Add back once this ReadOnlyTmpfs added to quadlet
   # Ref: https://github.com/containers/podman/issues/20439
   if ! grep "Volatile" "${qm_service_file}" ; then
     exec_cmd "sed -i 's|ReadOnly=true|&\nVolatileTmp=true|' ${qm_service_file}"
   fi
   # FIXME: QM is failing to start run podman #297 on asil space
   exec_cmd "restorecon -RFv /var/lib/containers &> /tmp/asil-restorecon"
}

disk_cleanup() {
   exec_cmd "systemctl stop qm"
   remove_file=$(find /var/qm -size  +2G)
   exec_cmd "rm -f $remove_file"
   exec_cmd "systemctl start qm"
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
       exec_cmd "podman image rm ${image_id}"
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
