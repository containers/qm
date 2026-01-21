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
    # Adding rawhide as 1.17 fixes Internal(Vm(SetMemoryAttributes(Error(22))))
    # See-Also: https://github.com/containers/qm/pull/959
    if grep -qi "^ID=fedora" /etc/os-release; then
        # Need the remove as soon the land in stable channel
        exec_cmd "dnf install --installroot=/usr/lib/qm/rootfs -y fedora-repos-rawhide"
    fi
    exec_cmd "cat /usr/lib/qm/rootfs/etc/yum.repos.d/*"
    exec_cmd "dnf repolist --all --setopt=reposdir=/etc/yum.repos.d"
    exec_cmd "dnf install --use-host-config --releasever=rawhide --enablerepo=rawhide --setopt=reposdir=/etc/yum.repos.d  --installroot=/usr/lib/qm/rootfs -y libkrun crun-krun libkrunfw"
}

check_libkrun() {
    info_message "check_libkrun(): run virtualization-isolated containers."
    exec_cmd "podman exec -it qm podman run --runtime=krun --rm -it alpine echo 'Hello libkrun.'"
    info_message "PASS: libkrun runs successfully."
}

#if grep -qi "^ID=centos" /etc/os-release; then
#    enable_repo
#fi

enable_repo
install_libkrun
check_libkrun

