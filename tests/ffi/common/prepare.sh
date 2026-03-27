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
   remove_file=$(find /var/qm -size +2G)
   if [ -n "${remove_file}" ]; then
      exec_cmd "rm -rf ${remove_file}"
   fi
   # Remove all containers in qm (don't care about stop in clean-up)
   if [ "$(podman inspect qm --format '{{.State.Running}}' 2>/dev/null)" = "true" ]; then
      exec_cmd "podman exec qm /usr/bin/podman rm -af"
   else
      info_message "SKIP: qm is not running, nested 'podman rm -af' not executed."
   fi
   if test -d "${DROP_IN_DIR}"; then
      exec_cmd "rm -rf ${DROP_IN_DIR}"
   fi
   exec_cmd "systemctl daemon-reload"
   exec_cmd "systemctl restart qm"
   # Clean large size files created by tests inside host part
   remove_file=$(find /root -size +1G)
   if [ -n "${remove_file}" ]; then
      exec_cmd "rm -f ${remove_file}"
   fi
}

# Remove all containers in host, then disk_cleanup.
# e.g. trap 'cleanup_host_then_qm ffi-asil' EXIT
cleanup_host_then_qm() {
   local container_name
   for container_name in "$@"; do
      [ -n "${container_name}" ] || continue
      podman rm -f "${container_name}" >/dev/null 2>&1 || true
   done
   disk_cleanup
}

reload_config() {
   exec_cmd "systemctl daemon-reload"
   exec_cmd "systemctl restart qm"
   # Add verification loop for qm status
   if timeout 30 bash -c "until systemctl is-active qm; do sleep 1; done"; then
      info_message "PASS: Service QM is Active."
   else
      info_message "FAIL: Service QM is not Active"
      exit 1
   fi
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

# systemd can report ffi-qm Active before nested podman reliably accepts exec.
ffi_qm_nested_ready() {
   local wait_sec="${1:-60}"
   if timeout "${wait_sec}" bash -c "until podman exec qm /usr/bin/podman exec ffi-qm true 2>/dev/null; do sleep 1; done"; then
      info_message "ffi-qm nested podman exec is ready"
   else
      info_message "FAIL: ffi-qm nested exec not ready within ${wait_sec}s"
      exit 1
  fi
}
