#!/bin/sh -x

install() {
    rootfs=$1
    sudo dnf -y install --rootfs ${rootfs} selinux-policy-targeted podman systemd 
}

setup_selinux() {
    rootfs=$1
    parent=$(dirname ${rootfs})
    sudo cp qm_contexts ${rootfs}/usr/share/containers/selinux/contexts
    sudo rm -rf ${rootfs}/etc/selinux/targeted/contexts/files/file_contexts/*
    sudo sed \
	 -e "s|${rootfs}||" \
	 -e "s/gen_context(//g" \
	 -e "s/,s0)/:s0/g" qm.fc  \
	 -e "s|${parent}||g" > \
	${rootfs}/etc/selinux/targeted/contexts/files/file_contexts
}

make
rootfs=/usr/lib/qm/rootfs

sudo semodule -i qm.pp.bz2

install ${rootfs} 

setup_selinux  ${rootfs} 

