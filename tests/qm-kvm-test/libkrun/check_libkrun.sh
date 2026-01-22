#!/bin/bash -x

# shellcheck disable=SC1091
source ../../e2e/lib/utils

enable_repo() {
    info_message "enable_repo(): enable repo"
    exec_cmd "cd /etc/yum.repos.d/"
    exec_cmd "dnf copr enable -y copr.fedorainfracloud.org/@centos-automotive-sig/libkrun centos-stream-9-$(arch)"
}

install_libkrun() {
    info_message "install_libkrun(): install libkrun and crun-krun"
    exec_cmd "dnf install --setopt=reposdir=/etc/yum.repos.d  --installroot=/usr/lib/qm/rootfs -y libkrun crun-krun"
}

check_libkrun() {
    info_message "check_libkrun(): run virtualization-isolated containers."
    exec_cmd "podman exec -it qm podman run --runtime=krun --rm -it alpine echo 'Hello libkrun.'"
    info_message "PASS: libkrun runs successfully."
}

verify_kvm_exposed_to_qm() {
    info_message "verify_kvm_exposed_to_qm(): check if /dev/kvm is exposed to qm."

    # Check /dev/kvm in qm
    if podman exec qm test -c /dev/kvm; then
        info_message "PASS: /dev/kvm is exposed to qm."
    else
        info_message "FAIL: /dev/kvm is not exposed to qm."
    fi
}

test -f /usr/share/qm/seccomp-no-rt.json && grep -i "memfd" /usr/share/qm/seccomp-no-rt.json || echo "File not found or memfd not in profile"
verify_kvm_exposed_to_qm
enable_repo
install_libkrun
check_libkrun

