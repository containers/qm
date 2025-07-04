#!/bin/bash -x

# shellcheck disable=SC1091
source ../../e2e/lib/utils

# Build and install the QM sub-package KVM
install_kvm_subPackage() {
    info_message "install_kvm_subPackage(): Download qm, build QM sub-package KVM and install it."
    exec_cmd "cd /root/ && git clone https://github.com/containers/qm.git && cd qm"
    exec_cmd "make TARGETS=kvm subpackages"

    kvm_rpm_package_dir="/root/qm/rpmbuild/RPMS/noarch"
    search_string="qm-kvm.*noarch.rpm"
    # shellcheck disable=SC2010
    kvm_rpm_package_name=$(ls -l "$kvm_rpm_package_dir" | grep ".*$search_string.*" | awk '{print $9}')

    # Install the KVM rpm package
    if [ -n "$kvm_rpm_package_name" ]; then
        exec_cmd "sudo dnf install $kvm_rpm_package_dir/$kvm_rpm_package_name -y >/dev/null"
        info_message "PASS: QM sub-package KVM installation completed."
    else
        info_message "FAIL: No QM sub-package KVM found."
        exit 1
    fi
}


# Verify the kvm configuration exist
verify_configuration() {
    info_message "verify_configuration(): Verify the kvm configuration exist."
    dropin_file="/etc/containers/systemd/qm.container.d/qm_dropin_mount_bind_kvm.conf"
    cntr_file="/etc/qm/containers/systemd/kvm.container"

    if [ -f $dropin_file ];then
        info_message "PASS: qm_dropin_mount_bind_kvm.conf exist."
    else
        info_message "FAIL: qm_dropin_mount_bind_kvm.conf dose not exist."
        exit 1

    fi

    if [ -f $cntr_file ];then
        info_message "PASS: kvm.container exist."
    else
        info_message "FAIL: kvm.container dose not exist."
        exit 1
    fi
}

# Check kvm is active in qm
check_kvm_is_active () {
    exec_cmd "systemctl daemon-reload"
    exec_cmd "systemctl restart qm"
    # Waiting for qm to start
    sleep 3

    exec_cmd "podman exec qm systemctl start kvm"
    # Waiting for kvm to be ready
    sleep 10

    if [ "$(podman exec qm systemctl is-active kvm)" == "active" ]; then
        info_message "PASS: check_kvm_is_active(): kvm is active in qm."
    else
        info_message "FAIL: check_kvm_is_active(): kvm is not active in qm."
        exit 1
    fi
}

# Login to kvm
check_kvm_is_working () {
    network_namespace="$(ip netns | cut -d ' ' -f 1)"
    kvm_os_version=$(ip netns exec "$network_namespace" sshpass -p "fedora" ssh -tt \
    -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null fedora@localhost -p 2226 << EOF
cat /etc/os-release
exit
EOF
)
    # Verify the kvm os version
    if grep -q 'NAME="Fedora Linux"' <<< "$kvm_os_version"; then
        info_message "PASS: check_kvm_is_working(): Login to kvm successfully."
    else
        info_message "FAIL: check_kvm_is_working(): Failed to login to kvm."
        exit 1
    fi
}

# Remove the downloaded qm
remove_testing_files () {
    exec_cmd "cd /root/ && rm -rf qm"
    exit 0
}

install_kvm_subPackage
verify_configuration
check_kvm_is_active
check_kvm_is_working
remove_testing_files
