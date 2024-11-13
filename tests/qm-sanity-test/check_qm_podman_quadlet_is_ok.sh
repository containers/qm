#!/bin/bash -x

# shellcheck disable=SC1091
source ../e2e/lib/utils

# Verify podman run and exec container inside qm with service file
check_qm_podman_quadlet_is_ok(){
    info_message "check_qm_podman_quadlet_is_ok(): \
    prepare quadlet files for qm-sanity-test.container"
    cat > "/etc/qm/containers/systemd/qm-sanity-test.container" <<EOF
[Unit]
Description=the qm-sanity-test sleep container
After=local-fs.target

[Container]
Image=quay.io/fedora/fedora
Exec=sleep 1000

[Install]
# Start by default on boot
WantedBy=multi-user.target default.target
EOF
    info_message "check_qm_podman_quadlet_is_ok(): qm-sanity-test container reload & restart"
    exec_cmd_with_pass_info "podman exec qm systemctl daemon-reload"
    exec_cmd_with_pass_info "podman exec qm systemctl start qm-sanity-test"
    exec_cmd_with_pass_info "podman exec qm systemctl status qm-sanity-test | grep -i started"
    exec_cmd_with_pass_info "podman exec qm podman run fedora echo Hello QM"
    info_message "PASS: check_qm_podman_quadlet_is_ok()"
    exit 0
}

exec_cmd_with_pass_info(){
    local command="$1"
    exec_cmd "${command}"
    info_message "PASS: Command ${command} successful"
}

check_qm_podman_quadlet_is_ok
