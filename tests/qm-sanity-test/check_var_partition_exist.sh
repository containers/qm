#!/bin/bash -euvx

# shellcheck disable=SC1091
source ../e2e/lib/utils

# Verify /var partition exist
check_var_partition_exist(){
    # /var on ostree image
    if stat /run/ostree-booted > /dev/null 2>&1; then
        expected_var_partition="part /var"
    # /var on c9s image
    else
        expected_var_partition="part /usr/lib/qm/rootfs/var"
    fi

    if [[ "$(lsblk -o 'MAJ:MIN,TYPE,MOUNTPOINTS')" =~ ${expected_var_partition} ]]; then
        info_message "check_var_partition_exist: /var exists in QM"
        info_message "PASS: check_var_partition_exist()"
    else
        info_message "FAIL: check_var_partition_exist: /var does not exists in QM"
        exit 1
    fi
}

# Check that a mount point is not ext4 and is writable inside QM container
check_mountpoint() {
    local mount_point="$1"

    if [[ -z "${mount_point}" ]]; then
        info_message "FAIL: check_mountpoint requires mount_point parameter"
        exit 1
    fi

    # Get filesystem type for the mount point inside QM container
    local fstype
    fstype=$(podman exec qm stat -f -c %T "${mount_point}" 2>/dev/null || echo "unknown")

    info_message "Filesystem type for ${mount_point}: ${fstype}"

    # Check that mount point is not tmpfs
    if [[ "${fstype}" == "ext4" ]]; then
        info_message "FAIL: ${mount_point} mount point is ext4 but should be persistent storage"
        info_message "Debug: QM container volume mounts:"
        podman inspect qm --format '{{range .Mounts}}{{.Source}}:{{.Destination}} {{end}}' 2>/dev/null || true
        exit 1
    else
        info_message "PASS: ${mount_point} is not tmpfs (filesystem type: ${fstype})"
    fi

    # Verify mount point is writable
    local test_file="${mount_point}/test_write_access"
    if podman exec qm touch "${test_file}" 2>/dev/null; then
        podman exec qm rm -f "${test_file}"
        info_message "PASS: ${mount_point} is writable"
    else
        info_message "FAIL: ${mount_point} is not writable"
        exit 1
    fi
}

# Verify that QM mount points are not tmpfs inside container
check_qm_mountpoints_not_tmpfs() {
    # Check if QM container is running
    if ! podman exec qm true > /dev/null 2>&1; then
        info_message "FAIL: QM container is not running"
        exit 1
    fi

    local mount_points=("/var" "/var/tmp")
    for mount_point in "${mount_points[@]}"; do
        check_mountpoint "${mount_point}"
    done
}

check_var_partition_exist
check_qm_mountpoints_not_tmpfs
