#!/bin/sh -ex

sudo systemctl stop qm
sudo podman volume rm qmEtc qmVar --force

install() {
    rootfs=$1
    sudo semodule -i qm.pp.bz2
    sudo mkdir -p ${rootfs}
    sudo restorecon -v ${rootfs}
    sudo dnf -y install --installroot ${rootfs} selinux-policy-targeted podman systemd dnf iputils
    sudo cp containers.conf ${rootfs}/etc/containers/
    sudo restorecon -R ${rootfs}
}

setup_selinux() {
    rootfs=$1
    parent=$(dirname ${rootfs})

    sudo cp qm_contexts ${rootfs}/usr/share/containers/selinux/contexts
    sudo rm -rf ${rootfs}/etc/selinux/targeted/contexts/files/file_contexts/*
    sed \
	 -e "s|${rootfs}||" \
	 -e "s/gen_context(//g" \
	 -e "s/,s0)/:s0/g" \
	 -e "s|${parent}||g" qm.fc > file_context
    sudo mv -Z file_context ${rootfs}/etc/selinux/targeted/contexts/files/file_contexts
}

setup_systemd() {
    rootfs=$1
    for unit in dbus-org.freedesktop.oom1.service systemd-userdbd.socket dbus-org.freedesktop.resolve1.service ctrl-alt-del.target; do
	sudo rm -f ${rootfs}/etc/systemd/system/${unit}
    done
}
make

ROOTFS="$1"
[ ! -z "${ROOTFS}" ] || ROOTFS=/usr/lib/qm/rootfs

install ${ROOTFS}

setup_selinux  ${ROOTFS}

setup_systemd ${ROOTFS}

sudo cp qm.container /etc/containers/systemd/
sudo systemctl daemon-reload
sudo systemctl start qm.service
