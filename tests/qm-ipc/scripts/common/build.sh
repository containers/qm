#!/bin/bash
set -euo pipefail

# Build the server image; pass the build argument for FEDORA_VERSION
echo "==========="
pwd
echo "==========="

echo "====ls====="
ls 
echo "==========="

echo "====ls ../====="
ls ../
echo "====ls====="

pushd scripts/common/server
podman build \
  --file Containerfile \
  --build-arg FEDORA_VERSION=41 \
  --tag ipc-server:latest .
popd

podman run --rm -d ipc-server:latest

# Build the client image; pass the build argument for FEDORA_VERSION
echo "==========="
pwd
echo "==========="
pushd scripts/common/client
podman build \
  --file Containerfile \
  --build-arg FEDORA_VERSION=41 \
  --tag ipc-client:latest .
popd
podman run --rm -d ipc-client:latest

