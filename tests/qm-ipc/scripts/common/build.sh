#!/bin/bash
set -euo pipefail

# Build the client image; pass the build argument for FEDORA_VERSION
pushd client
podman build \
  --file Containerfile \
  --build-arg FEDORA_VERSION=41 \
  --tag ipc-client:latest .
popd
podman run --rm ipc-client:latest

# Build the server image; pass the build argument for FEDORA_VERSION
pushd server
podman build \
  --file Containerfile \
  --build-arg FEDORA_VERSION=41 \
  --tag ipc-server:latest .
popd

podman run --rm ipc-server:latest
