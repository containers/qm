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

enable_repo
install_libkrun
check_libkrun

