#!/bin/bash

daemon_reload_in_qm() {
    echo "qm: systemctl daemon-reload inside qm..."
    podman exec -it qm bash -c "systemctl daemon-reload"
}

restart_ipc_client_in_qm() {
    echo "qm: restart ipc_client inside qm..."
    podman exec -it qm bash -c "podman restart systemd-ipc_client"
    sleep 15
}

show_qm_podman_ps() {
    echo "qm: podman ps inside qm..."
    podman exec -it qm bash -c "podman ps"
}

check_nested_ipc_containers_exist() {
  local nested_containers=("systemd-ipc_client" "systemd-ipc_server")
  local missing=0

  echo "Checking nested containers inside 'qm'..."

  # Capture the list of nested container names inside 'qm'
  local container_list
  container_list=$(podman exec -it qm podman ps --all --format '{{.Names}}' | tr -d '\r')

  for name in "${nested_containers[@]}"; do
    if ! grep -q "^${name}$" <<< "$container_list"; then
      echo "Error: Nested container '$name' does not exist inside 'qm'."
      missing=1
    fi
  done

  if [[ $missing -eq 1 ]]; then
    exit 1
  else
    echo "Both nested containers exist inside 'qm'."
  fi
}


check_ipc_client_logs() {
    echo "qm: podman logs systemd-ipc_client"
    if podman exec -it qm bash -c "podman logs systemd-ipc_client" | grep -Eiq "permission denied|no such file or directory"; then
        echo "systemd-ipc_client has failed"
        exit 1
    fi
}

print_debug_info() {
    echo
    echo "===================================="
    echo "Printing $CLIENT"
    echo "===================================="
    cat $CLIENT

    echo
    echo "===================================="
    echo "Printing $SERVER"
    echo "===================================="
    cat $SERVER

    if [[ -n $EXTRA_VOLUME ]]; then
        echo "===================================="
        echo "Printing $EXTRA_VOLUME"
        echo "===================================="
        cat "$EXTRA_VOLUME"

        echo "ls -laZ ${VOLUME_PATH%%:*} in the HOST"
        ls -laZ "${VOLUME_PATH%%:*}"
    fi

    echo
    echo "===================================="
    echo "ls -laZ ${VOLUME_PATH%%:*} in the HOST"
    echo "===================================="
    find "${VOLUME_PATH%%:*}" -name '*ipc*' -exec ls -laZ {} +

    echo
    echo "===================================="
    echo "ls -laZ ${VOLUME_PATH%%:*} in the QM"
    echo "===================================="
    podman exec -it qm bash -c "ls -laZ ${VOLUME_PATH%%:*} | grep ipc"
}

MODE="$1"

echo "Creating IPC files for mode: $MODE"

# Define file paths for both modes
QMQM_SERVER="/etc/qm/containers/systemd/ipc_server.container"
QMQM_CLIENT="/etc/qm/containers/systemd/ipc_client.container"

echo "Cleaning up asil-to-qm files..."
rm -f "$ASIL_SOCKET" "$ASIL_SERVER" "$ASIL_CLIENT" "$ASIL_EXTRA_VOLUME"

VOLUME_PATH=/run/:/run/
ENVIRONMENT="Environment=SOCKET_PATH=/run/ipc.sock"

SERVER=$QMQM_SERVER
CLIENT=$QMQM_CLIENT

# Create ipc_server.socket
echo "Creating $SERVER"
# Create ipc_server.container
cat <<EOF > "$SERVER"
[Unit]
Description=Demo server service container ($MODE)
[Container]
Image=localhost/ipc-server:latest
Network=none
$ENVIRONMENT
Volume=$VOLUME_PATH
SecurityLabelLevel=s0:c1,c2
#SecurityLabelType=ipc_t
[Service]
Restart=always
Type=notify
[Install]
WantedBy=multi-user.target
EOF

echo "Creating $CLIENT"
# Create ipc_client.container
cat <<EOF > "$CLIENT"
[Unit]
Description=Demo client service container ($MODE)
Requires=ipc_server.service
After=ipc_server.service

[Container]
Image=localhost/ipc-client:latest
Network=none
$ENVIRONMENT
Volume=$VOLUME_PATH
SecurityLabelLevel=s0:c1,c2
[Service]
Restart=always
[Install]
WantedBy=multi-user.target
EOF

echo "Reloading systemd and restarting containers (qm-to-qm)..."
systemctl daemon-reload
systemctl restart qm
sleep 15

daemon_reload_in_qm

print_debug_info
restart_ipc_client_in_qm
check_nested_ipc_containers_exist
check_ipc_client_logs
show_qm_podman_ps
