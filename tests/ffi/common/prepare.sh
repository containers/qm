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
