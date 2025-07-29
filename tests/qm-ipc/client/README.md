To build ipc client image and upload to quay.io

podman login quay.io
podman build -t client:latest .
podman tag client:latest quay.io/qm-images/ipc/client:latest
podman push quay.io/qm-images/ipc/client:latest
