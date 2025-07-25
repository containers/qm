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

check_ipc_client_logs() {
    echo "qm: podman logs systemd-ipc_client"
    if podman exec -it qm bash -c "podman logs systemd-ipc_client" | grep -Eiq "permission denied|no such file or directory"; then
        echo "systemd-ipc_client has failed"
        exit 1
    fi
}

check_nested_container_exists() {
  local container_name="$1"

  echo "Checking for '$container_name' inside 'qm'..."

  # Capture output of nested podman ps inside qm
  local output
  output=$(podman exec qm podman ps --format "{{.Names}}" 2>/dev/null)

  if echo "$output" | grep -wq "$container_name"; then
    echo "Container '$container_name' exists inside 'qm'."
  else
    echo "Container '$container_name' does NOT exist inside 'qm'."
    echo "Output from qm's podman:"
    echo "$output"
    exit 1
  fi
}

print_debug_info() {
    echo
    echo "===================================="
    echo "Printing $SOCKET"
    echo "===================================="
    cat $SOCKET

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
        cat $EXTRA_VOLUME

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

check_container_exists() {
    local container_name="systemd-ipc_server"
    echo "Checking if container '$container_name' exists and is running..."

    if podman ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
        echo "Container '$container_name' is running."
    else
        echo "Container '$container_name' is NOT running."
        exit 1
    fi
}

echo "Creating IPC files for mode: ASIL to QM"

# Define file paths for both modes
QMQM_SOCKET=""
QMQM_EXTRA_VOLUME=""
QMQM_SERVER="/etc/qm/containers/systemd/ipc_server.container"
QMQM_CLIENT="/etc/qm/containers/systemd/ipc_client.container"

ASIL_SOCKET="/etc/systemd/system/ipc_server.socket"
ASIL_SERVER="/etc/containers/systemd/ipc_server.container"
ASIL_CLIENT="/etc/qm/containers/systemd/ipc_client.container"
ASIL_EXTRA_VOLUME="/etc/containers/systemd/qm.container.d/10-extra-volume.conf"

# asil to qm
echo "Cleaning up qm-to-qm files..."
rm -f "$QMQM_SOCKET $QMQM_SERVER $QMQM_CLIENT $QMQM_EXTRA_VOLUME"

SOCKET=$ASIL_SOCKET
SERVER=$ASIL_SERVER
CLIENT=$ASIL_CLIENT
EXTRA_VOLUME="$ASIL_EXTRA_VOLUME"

ENVIRONMENT="Environment=SOCKET_PATH=/run/ipc/ipc.socket"
LISTEN_PATH="%t/ipc/ipc.socket"
VOLUME_PATH="/run/ipc/:/run/ipc/"

# Create ipc_server.socket
echo "Creating $SOCKET"
cat <<EOF > "$SOCKET"
[Unit]
Description=IPC Server Socket for $MODE
[Socket]
ListenStream=$LISTEN_PATH
SELinuxContextFromNet=yes

[Install]
WantedBy=sockets.target
EOF

ASIL_VOLUME_DIR="${ASIL_EXTRA_VOLUME%/*}"
mkdir -p "$ASIL_VOLUME_DIR"
echo "Creating $EXTRA_VOLUME"
cat <<EOF > "$EXTRA_VOLUME"
[Unit]
Requires=ipc_server

[Container]
Volume=$VOLUME_PATH
EOF

echo "Creating $SERVER"
# Create ipc_server.container
cat <<EOF > "$SERVER"
[Unit]
Description=Demo server service container ($MODE)
Requires=ipc_server.socket
After=ipc_server.socket
[Container]
Image=localhost/ipc-server:latest
Network=none
$ENVIRONMENT
Volume=$VOLUME_PATH
SecurityLabelType=ipc_t
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
[Container]
Image=localhost/ipc-client:latest
Network=none
$ENVIRONMENT
Volume=$VOLUME_PATH
SecurityLabelType=qm_container_ipc_t
[Service]
Restart=always
[Install]
WantedBy=multi-user.target
EOF

echo "systemctl daemon reload..."
systemctl daemon-reload

echo "restart ipc_server.socket"
systemctl restart ipc_server.socket

echo "restart ipc_server"
systemctl restart ipc_server

echo "restarting qm..."
systemctl restart qm
sleep 5

daemon_reload_in_qm
check_container_exists

echo "qm: systemctl status ipc_client"
podman exec -it qm bash -c "systemctl status ipc_client"

#check_nested_container_exists "systemd-ipc_client"
restart_ipc_client_in_qm

echo "qm: systemctl status ipc_client"
podman exec -it qm bash -c "systemctl status ipc_client"

show_qm_podman_ps
check_ipc_client_logs
print_debug_info
