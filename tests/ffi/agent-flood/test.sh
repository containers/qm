#!/bin/bash -euvx

# shellcheck disable=SC1091

# Check if SKIP_TEST is set to true
if [ "$SKIP_TEST" == "true" ]; then
    echo "Skipping the bluechi stress test."
    exit 0
fi

. ../common/prepare.sh

export NUMBER_OF_NODES="${NUMBER_OF_NODES:-2}"
WAIT_BLUECHI_AGENT_CONNECT="${WAIT_BLUECHI_AGENT_CONNECT:-5}"

setup_test_containers_in_qm() {

    #Prepare quadlet files for testing containers
    for ((i=1;i<=NUMBER_OF_NODES;i++)); do
        info_message "setup_test_containers_in_qm(): prepare quadlet files for bluechi-tester-${i}.container"
        cat > "/etc/qm/containers/systemd/bluechi-tester-${i}.container" <<EOF
[Unit]
Description=bluechi-tester-X
After=local-fs.target

[Container]
Image=quay.io/centos-sig-automotive/ffi-tools:latest
Exec=/root/tests/FFI/bin/bluechi-tester --url="tcp:host=${controller_host_ip},port=842" \
     --nodename=bluechi-tester-X \
     --numbersignals=11111111 \
     --signal="JobDone"
Network=host
EOF
        sed -i -e "s/tester-X/tester-${i}/g" "/etc/qm/containers/systemd/bluechi-tester-${i}.container"

        info_message "setup_test_containers_in_qm(): updating AllowedNodeNames in /etc/bluechi/controller.conf"
        #Update controller configuration
        sed -i -e '/^AllowedNodeNames=/ s/$/,bluechi-tester-'"${i}"'/' /etc/bluechi/controller.conf

        info_message "setup_test_containers_in_qm(): bluechi-controller reload & restart"
        #Reload bluechi-controller
        exec_cmd "systemctl daemon-reload"
        exec_cmd "systemctl restart bluechi-controller"

    done

    #Restart bluechi-agent for clean connection logs
    exec_cmd "systemctl restart bluechi-agent"
    sleep "${WAIT_BLUECHI_AGENT_CONNECT}"
    if [ "$(systemctl is-active bluechi-agent)" != "active" ]; then
        info_message "setup_test_containers_in_qm(): bluechi-agent is not active"
        exit 1
    fi
}

run_test_containers(){
    for ((i=1;i<=NUMBER_OF_NODES;i++)); do
        #Reload bluechi-testers in qm
        info_message "run_test_containers(): bluechi-tester-${i} reload & restart"
        exec_cmd "podman exec qm systemctl daemon-reload"
        exec_cmd "podman exec qm systemctl restart bluechi-tester-${i}"
    done
}

# Extract the Network mode from qm.service
get_qm_network_mode(){
    qm_config_file="/run/systemd/generator/qm.service"

    # Check if the configuration file exists
    if [ ! -f "$qm_config_file" ]; then
        echo "Configuration file not found: $qm_config_file"
        exit 1
    fi

    # Extract the Network using awk
    qm_network_mode=$(awk -F'=' '/Network=/ { print $2 }' "$qm_config_file")
    echo "${qm_network_mode}"
}

trap disk_cleanup EXIT
prepare_test
reload_config

# Assign value to ${controller_host_ip} according to qm network mode
if [ "$(get_qm_network_mode)" == "private" ]; then
    controller_host_ip=$(hostname -I | awk '{print $1}')
else
    info_message "qm network mode should be private, not: $(get_qm_network_mode)"
    exit 1
fi

#Stop QM bluechi-agent
exec_cmd "podman exec -it qm /bin/bash -c \
         \"systemctl stop bluechi-agent\""

#Prepare quadlet files for testing containers
setup_test_containers_in_qm
#Run containers through systemd
run_test_containers

#Check both tests services are on
for ((i=1;i<=NUMBER_OF_NODES;i++)); do
    if [ "$(podman exec qm systemctl is-active bluechi-tester-"${i}")" != "active" ]; then
        info_message "test() bluechi-tester-${i} is not active"
        exit 1
    fi
done

#check ASIL bluechi-agent is connected
connection_cnt="$(grep -e Connected -e "'localrootfs'" \
    -oc <<< "$(systemctl status -l --no-pager bluechi-agent)")"
if [ "${connection_cnt}" -ne 1 ]; then
    info_message "test() expects ASIL bluechi-agent connection not disturbed"
    agent_log="$(grep "bluechi-agent\[.*\]:" <<< "$(systemctl status -l --no-pager bluechi-agent)")"
    info_message "test() agent logs..."
    info_message "test() ${agent_log}"
    info_message "test() number of connections found ${connection_cnt}"
    exit "${connection_cnt}"
fi
