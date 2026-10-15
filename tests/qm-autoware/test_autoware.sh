#!/bin/bash

# shellcheck disable=SC1091
. ../e2e/lib/utils

info_message "Running QM Autoware tests..."

qmc exec podman pull quay.io/qm-images/autoware:latest

if qmc exec podman run --privileged -v /var/lib/containers/storage:/var/lib/containers/storage -it quay.io/qm-images/autoware:latest; then
    pass_message "podman run autoware executed successfully."
else
    fail_message "podman run autoware failed."
fi
