#!/bin/bash -x

# shellcheck disable=SC1091
source ../../e2e/lib/utils

enable_repo() {
    info_message "enable_repo(): enable repo"
    exec_cmd "cd /etc/yum.repos.d/"
    exec_cmd "curl -O https://copr.fedorainfracloud.org/coprs/slp/autosd-krun/repo/centos-stream-9/slp-autosd-krun-centos-stream-9.repo"
    exec_cmd "dnf copr enable -y copr.fedorainfracloud.org/@centos-automotive-sig/libkrun centos-stream-9-$(arch)"
}

install_libkrun() {
    info_message "install_libkrun(): install libkrun and crun-krun"
    exec_cmd "dnf install --setopt=reposdir=/etc/yum.repos.d  --installroot=/usr/lib/qm/rootfs -y libkrun crun-krun"
}

update_qm_selinux_policy() {
    info_message "update_qm_selinux_policy(): update the qm selinux policy"
    touch /root/krun.te
    cat > "/root/krun.te" << EOF
module krun 1.0;

require {
	type qm_t;
	class process setcurrent;
}

#============= qm_t ==============
allow qm_t self:process setcurrent;
EOF

    exec_cmd "cd /root/"
    exec_cmd "checkmodule -M -m -o krun.mod krun.te"
    exec_cmd "semodule_package -o krun.pp -m krun.mod"
    exec_cmd "semodule -i krun.pp"
}

check_libkrun() {
    info_message "check_libkrun(): run virtualization-isolated containers."
    exec_cmd "podman exec -it qm podman run --runtime=krun --rm -it alpine echo 'Hello libkrun.'"
    info_message "PASS: libkrun runs successfully."
}

remove_generated_files () {
    exec_cmd "cd /root/ && rm -f  *.te *.mod *.pp"
    exit 0
}

enable_repo
install_libkrun
update_qm_selinux_policy
check_libkrun
remove_generated_files

