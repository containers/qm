#!/bin/bash -x

# shellcheck disable=SC1091
source ../../e2e/lib/utils

# Prerequisite for the test is that /dev/kvm is exposed to qm.
verify_kvm_exposed_to_qm() {
    info_message "verify_kvm_exposed_to_qm(): Confirm that /dev/kvm is exposed to qm. If not, the test will terminate."

    # Check /dev/kvm in qm
    if podman exec qm test -c /dev/kvm; then
        info_message "PASS: /dev/kvm is exposed to qm."
    else
        info_message "FAIL: /dev/kvm is not exposed to qm, test terminated."
        exit 1
    fi
}

# Set up KVM environment for testing
copy_kvm_configuration() {
    info_message "copy_kvm_configuration(): Copy kvm container quadlet and qm drop-in to host."

    quadlet_dir="/etc/qm/containers/systemd/"
    dropin_dir="/etc/containers/systemd/qm.container.d/"

    if [ ! -d "${dropin_dir}" ]; then
        exec_cmd "mkdir -p ${dropin_dir}"
    fi

    cp "${TMT_TREE}/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_kvm.conf" "$dropin_dir"
    cp "${TMT_TREE}/subsystems/kvm/etc/containers/systemd/kvm.container" "$quadlet_dir"
    info_message "PASS: Copy configuration finished."
}

# Poll the service and wait for it to become active
wait_for_service_active() {
    local container="$1"
    local service="$2"
    local timeout="${3:-30}"  # Default timeout is 30 seconds

    # Command and message
    if [ -n "${container}" ];then # when service in the container
        cmd="podman exec $container systemctl is-active --quiet $service"
        msg="'$service' in container '$container'"
    else # when service in the host
        cmd="systemctl is-active --quiet $service"
        msg="'$service'"
    fi

    # Poll the service
    info_message "Waiting for service $msg to become active..."

    if timeout "$timeout" bash -c "until $cmd; do sleep 1; done"; then
        info_message "Service $msg is active."
    else
        info_message "ERROR: Timeout waiting for service $msg"
        exit 1
    fi
}

# Verify the kvm configuration exist
verify_configuration() {
    info_message "verify_configuration(): Verify the kvm container quadlet and qm drop-in exist."

    qm_dropin_file="$dropin_dir""qm_dropin_mount_bind_kvm.conf"
    kvm_quadlet_file="$quadlet_dir""kvm.container"

    # Check qm_dropin_mount_bind_kvm.conf
    if [ -f $qm_dropin_file ];then
        info_message "PASS: qm_dropin_mount_bind_kvm.conf exist."
    else
        info_message "FAIL: qm_dropin_mount_bind_kvm.conf dose not exist."
        exit 1

    fi

    # Check kvm.container
    if [ -f $kvm_quadlet_file ];then
        info_message "PASS: kvm.container exist."
    else
        info_message "FAIL: kvm.container dose not exist."
        exit 1
    fi

    # Start the kvm service in qm
    exec_cmd "podman exec qm systemctl daemon-reload"
    exec_cmd "podman exec qm systemctl start kvm"
}

# Check kvm is active in qm
check_kvm_service_running () {
    info_message "check_kvm_service_running(): Verify the kvm service is active in qm."

    exec_cmd "systemctl daemon-reload"
    exec_cmd "systemctl restart qm"
    # Waiting for qm to start
    wait_for_service_active "" qm
    # Waiting for kvm in qm to start
    wait_for_service_active qm kvm

    # Check kvm service status
    if [ "$(podman exec qm systemctl is-active kvm)" == "active" ]; then
        info_message "PASS: The kvm service is active in qm."
    else
        info_message "FAIL: The kvm service is not active in qm."
        exit 1
    fi
}

# Login to kvm
check_container_vm_accessible () {
    info_message "check_container_vm_accessible(): Verify the container VM is accessible."

    network_namespace="$(ip netns | cut -d ' ' -f 1)"
    login_vm_cmd="ip netns exec $network_namespace sshpass -p fedora ssh -tt \
    -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null fedora@localhost -p 2226"

    # Waiting for the VM to be ready
    timeout 1m bash -c "until $login_vm_cmd exit; do
        sleep 2
    done"

    # Login to the VM
    vm_os_version=$($login_vm_cmd << EOF
cat /etc/os-release
exit
EOF
)

    # Check the VM OS version
    if grep -q 'NAME="Fedora Linux"' <<< "$vm_os_version"; then
        info_message "PASS: Login to the container VM successfully."
        exit 0
    else
        info_message "FAIL: Failed to login to the container VM."
        exit 1
    fi
}

verify_kvm_exposed_to_qm
copy_kvm_configuration
verify_configuration
check_kvm_service_running
check_container_vm_accessible
