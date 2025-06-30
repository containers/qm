# Setting up IPC

In systems where **Automotive Safety Integrity Level (ASIL)** and **Quality Management (QM)**
components coexist, strict separation is enforced to maintain safety and security boundaries via
**SELinux (Security-Enhanced Linux)**, which labels processes and files with security contexts
to control their interactions.

**IPC (Inter-Process Communication)** between ASIL and QM components must be tightly controlled.
To comply with SELinux policies and avoid permission denials, any socket-based communication
between ASIL and QM domains should be established in the dedicated directory such as /run/ipc
with ipc_var_run_t file context. It serves as a secure bridge for cross-domain communication
while maintaining SELinux isolation.

On the other hand, **IPC between QM services** (e.g., two services or containers within the same QM domain)
can occur as well. Since these components share the same SELinux type and context, they are allowed to
communicate using standard Unix domain sockets located in /run. This approach simplifies internal QM
communication without compromising the system's overall security posture. Such communication can be
orchestrated also using container orchestration patterns like **.pod (Podman pod definitions)** or
**.kube (Kubernetes pod manifests)**, which group related services in shared namespaces to support efficient
IPC within the same trust boundary.

## Example QM to QM app

## /etc/qm/containers/systemd/ipc_client.container

```console
[Unit]
Description=Demo client service container
Requires=ipc_server.socket
After=ipc_server.socket
[Container]
Image=quay.io/username/ipc-demo/ipc_client:latest
Network=none
Volume=/run/:/run/
SecurityLabelLevel=s0:c1,c2
[Service]
Restart=always
[Install]
WantedBy=multi-user.target
```

## /etc/qm/containers/systemd/ipc_server.container

```console
[Unit]
Description=Demo server service container
Requires=ipc_server.socket
After=ipc_server.socket
[Container]
Image=quay.io/username/ipc-demo/ipc_server:latest
Network=none
Volume=/run/:/run/
SecurityLabelLevel=s0:c1,c2
[Service]
Restart=always
Type=notify
[Install]
WantedBy=multi-user.target
```

## /etc/qm/systemd/system/ipc_server.socket

```console
[Unit]
Description=IPC Server Socket
[Socket]
ListenStream=%t/ipc_server.socket
SELinuxContextFromNet=yes

[Install]
WantedBy=sockets.target
```
