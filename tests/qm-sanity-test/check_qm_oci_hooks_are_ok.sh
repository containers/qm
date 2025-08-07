#!/bin/bash -euvx

# shellcheck disable=SC1091
source ../e2e/lib/utils

# Setup OCI hooks directly from source tree (TMT_TREE approach)
setup_qm_oci_hooks_from_source() {
    info_message "setup_qm_oci_hooks_from_source(): Setting up OCI hooks directly from TMT_TREE"

    local hooks_config_dir="/usr/share/containers/oci/hooks.d"
    local hooks_exec_dir="/usr/libexec/oci/hooks.d"

    # Create directories if they don't exist
    exec_cmd "mkdir -p $hooks_config_dir"
    exec_cmd "mkdir -p $hooks_exec_dir"

    # Copy QM Device Manager hook
    exec_cmd "cp ${TMT_TREE}/oci-hooks/qm-device-manager/oci-qm-device-manager.json $hooks_config_dir/"
    exec_cmd "cp ${TMT_TREE}/oci-hooks/qm-device-manager/oci-qm-device-manager $hooks_exec_dir/"
    exec_cmd "chmod +x $hooks_exec_dir/oci-qm-device-manager"

    # Copy Wayland Client Devices hook
    exec_cmd "cp ${TMT_TREE}/oci-hooks/wayland-client-devices/oci-qm-wayland-client-devices.json $hooks_config_dir/"
    exec_cmd "cp ${TMT_TREE}/oci-hooks/wayland-client-devices/oci-qm-wayland-client-devices $hooks_exec_dir/"
    exec_cmd "chmod +x $hooks_exec_dir/oci-qm-wayland-client-devices"

    # Copy essential library files (excluding mock support)
    exec_cmd "mkdir -p $hooks_exec_dir/../lib"
    exec_cmd "cp ${TMT_TREE}/oci-hooks/lib/common.sh $hooks_exec_dir/../lib/"
    exec_cmd "cp ${TMT_TREE}/oci-hooks/lib/device-support.sh $hooks_exec_dir/../lib/"

    info_message "setup_qm_oci_hooks_from_source(): All OCI hooks copied successfully from TMT_TREE"
}

# Cleanup function to remove test hooks on exit
cleanup_oci_hooks() {
    info_message "cleanup_oci_hooks(): Cleaning up test OCI hooks"

    local hooks_config_dir="/usr/share/containers/oci/hooks.d"
    local hooks_exec_dir="/usr/libexec/oci/hooks.d"

    # Remove test hooks
    rm -f "$hooks_config_dir/oci-qm-device-manager.json" || true
    rm -f "$hooks_config_dir/oci-qm-wayland-client-devices.json" || true

    rm -f "$hooks_exec_dir/oci-qm-device-manager" || true
    rm -f "$hooks_exec_dir/oci-qm-wayland-client-devices" || true

    # Clean up library files
    rm -rf "$hooks_exec_dir/../lib" || true

    # Clean up test containers
    local test_containers=("qm-oci-hooks-device-test")
    for test_container in "${test_containers[@]}"; do
        systemctl stop "$test_container" 2>/dev/null || true
        rm -f "/etc/containers/systemd/${test_container}.container" || true
    done
    systemctl daemon-reload 2>/dev/null || true
}

# shellcheck disable=SC2317
trap cleanup_oci_hooks EXIT

# Verify QM OCI hooks are working properly
check_qm_oci_hooks_are_ok(){
    info_message "check_qm_oci_hooks_are_ok(): Starting OCI hooks sanity test"

    # Setup hooks directly from source tree
    setup_qm_oci_hooks_from_source

    # Validate hook JSON configurations
    info_message "check_qm_oci_hooks_are_ok(): Validating hook JSON configurations"

    local hooks_config_dir="/usr/share/containers/oci/hooks.d"

    if command -v jq > /dev/null 2>&1; then
        for hook_json in "$hooks_config_dir"/*.json; do
            if [[ -f "$hook_json" ]]; then
                if jq . "$hook_json" > /dev/null 2>&1; then
                    info_message "check_qm_oci_hooks_are_ok(): Valid JSON: $(basename "$hook_json")"
                else
                    info_message "FAIL: check_qm_oci_hooks_are_ok(): Invalid JSON: $(basename "$hook_json")"
                    exit 1
                fi
            fi
        done
    else
        info_message "check_qm_oci_hooks_are_ok(): jq not available, skipping JSON validation"
    fi

    # Test QM Device Manager hook with TTY devices
    local test_container="qm-oci-hooks-device-test"

    cat > "/tmp/${test_container}.container" << EOF
[Unit]
Description=OCI Hooks Sanity Test Container
After=local-fs.target

[Container]
Image=registry.access.redhat.com/ubi9-minimal:latest
Exec=sleep 10
Annotation=org.containers.qm.device.ttys=true

[Install]
WantedBy=multi-user.target default.target
EOF

    info_message "check_qm_oci_hooks_are_ok(): Testing quadlet container with OCI hook annotation"

    # Deploy and test the container
    exec_cmd "cp /tmp/${test_container}.container /etc/containers/systemd/"
    exec_cmd "systemctl daemon-reload"

    # Start the container and verify it works
    if exec_cmd "systemctl start $test_container" && sleep 5; then
        if systemctl is-active "$test_container" > /dev/null; then
            info_message "check_qm_oci_hooks_are_ok(): Quadlet container with OCI hook annotation started successfully"

            # Check if device manager hook logged activity
            if [[ -f "/var/log/qm-device-manager.log" ]]; then
                if tail -20 "/var/log/qm-device-manager.log" | grep -i "ttys\|device" > /dev/null 2>&1; then
                    info_message "check_qm_oci_hooks_are_ok(): OCI hook processing detected in logs"
                fi
            fi

            # Clean up test container
            systemctl stop "$test_container" 2>/dev/null || true
            rm -f "/etc/containers/systemd/${test_container}.container" || true

        else
            info_message "FAIL: check_qm_oci_hooks_are_ok(): Quadlet container with OCI hook annotation is not active"
            exit 1
        fi
    else
        info_message "FAIL: check_qm_oci_hooks_are_ok(): Quadlet container with OCI hook annotation failed to start"
        exit 1
    fi

    exec_cmd "systemctl daemon-reload"
    info_message "PASS: check_qm_oci_hooks_are_ok(): QM Device Manager hook tested successfully"
}

check_qm_oci_hooks_are_ok
