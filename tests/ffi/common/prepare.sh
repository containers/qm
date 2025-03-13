#!/bin/bash
# shellcheck disable=SC1091
. ../../e2e/lib/utils

export DROP_IN_DIR="/etc/containers/systemd/qm.container.d/"
OSTREE_PATH="/run/ostree"

# Checks if the system is running under OSTree.
# This function determines if the system is using OSTree by checking for the
# existence of the directory specified by the OSTREE_PATH environment variable.
# Returns:
# 0 (success) if the OSTREE_PATH directory exists, indicating the system is
# running under OSTree.
# 1 (failure) if the OSTREE_PATH directory does not exist, indicating the
# system is not running under OSTree.
is_ostree() {
    if [ -d "${OSTREE_PATH}" ]; then
        echo "The system is running under OSTree."
        return 0
    else
        echo "The system is not running under OSTree."
        return 1
    fi
}

prepare_test() {
   # Search variables for update file in qm.container
   # qm_service_file=$(systemctl show -P  SourcePath qm)
   # Create qm container custom config folder for qm drop-in file.
   # Use drop-in files to update qm_service_file
   # please refer 'zcat $(man -w qm.8) | grep -i "^\.sh" | grep drop-in'
   exec_cmd "mkdir -p ${DROP_IN_DIR}"
}

disk_cleanup() {
   # Clean large size files created by tests inside qm part
   remove_file=$(find /var/qm -size  +2G)
   exec_cmd "rm -rf $remove_file"
   # Remove all containers in qm (don't care about stop in clean-up)
   exec_cmd "podman exec -it qm /usr/bin/podman rm -af"
   if test -d "${DROP_IN_DIR}"; then
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

running_container_in_qm() {
     while true; do
         if podman exec qm /usr/bin/systemctl is-active ffi-qm -q; then
             info_message "ffi-qm container inside qm is fully started"
             break
         fi
         sleep 1
     done
     info_message "qm was started: $(systemctl status qm | grep Active | cut -d ';' -f 2)"
}
