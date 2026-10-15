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
Exec=/bin/sh -c "sleep 2 && /root/tests/FFI/bin/bluechi-tester --url=\"unix:path=/run/bluechi.sock\" --nodename=bluechi-tester-X --numbersignals=11111111 --signal=\"JobDone\""
Network=host
StopTimeout=1
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
        exec_cmd "qmc exec systemctl daemon-reload"
        exec_cmd "qmc exec systemctl restart bluechi-tester-${i}"
    done
}

create_bluechi_socket_volume_mount_drop_in_file(){
    info_message "Creating BlueChi socket volume mount drop-in file..."
  mkdir -p /etc/qmc.conf.d/
  cat > /etc/qmc.conf.d/90-ffi-bluechi-socket.conf << 'EOF'
{"mounts": [{"source": "/run/bluechi/bluechi.sock", "destination": "/run/bluechi.sock"}]}
EOF
  info_message "BlueChi socket volume mount drop-in file created successfully"
}


trap disk_cleanup EXIT
prepare_test
create_bluechi_socket_volume_mount_drop_in_file
reload_config

#Stop QM bluechi-agent once bluechi-agent is up
qm_node=$(bluechictl status | grep qm | cut -d'|' -f1)
if timeout 30 sh -c "until bluechictl status $qm_node bluechi-agent.service >/dev/null; do sleep 5; done"; then
    info_message "PASS: bluechi-agent.service is online on $qm_node.";
    exec_cmd 'qmc exec sh -c "systemctl stop bluechi-agent"'
fi

#Prepare quadlet files for testing containers
setup_test_containers_in_qm
#Run containers through systemd
run_test_containers

#Check both tests services are on
for ((i=1;i<=NUMBER_OF_NODES;i++)); do
    if [ "$(qmc exec systemctl is-active bluechi-tester-"${i}")" != "active" ]; then
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
