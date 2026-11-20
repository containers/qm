#!/bin/bash -x

# shellcheck disable=SC1091
source ../../e2e/lib/utils

install_libkrun() {
    info_message "install_libkrun(): install libkrun and crun-krun"
    exec_cmd "dnf install --setopt=reposdir=/usr/lib/qm/rootfs/etc/yum.repos.d --installroot=/usr/lib/qm/rootfs -y libkrun crun-krun"
}

check_libkrun() {
    info_message "check_libkrun(): run virtualization-isolated containers."
    exec_cmd "qmc exec podman run --runtime=krun --rm -it alpine echo 'Hello libkrun.'"
    info_message "PASS: libkrun runs successfully."
}

install_libkrun
check_libkrun

