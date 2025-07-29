To build ipc server image and upload to quay.io

podman login quay.io
podman build -t server:latest .
podman tag server:latest quay.io/qm-images/ipc/server:latest
podman push quay.io/qm-images/ipc/server:latest
