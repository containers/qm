#!/bin/bash

set -euo pipefail

# Download basic QM manifest
curl -fL -o qm.aib.yml https://gitlab.com/CentOS/automotive/src/automotive-image-builder/-/raw/main/examples/qm.aib.yml

USE_QM_COPR="${PACKIT_COPR_PROJECT:-@centos-automotive-sig/qm-next}"
# Packit builds QM for EPEL 10; scope that chroot to this repository.
QM_COPR_URL="https://download.copr.fedorainfracloud.org/results/${USE_QM_COPR}/epel-10-$(uname -m)/"

# Run AIB in container
curl -fL -o aib.sh https://gitlab.com/CentOS/automotive/src/automotive-image-builder/-/raw/main/aib.sh
/bin/bash aib.sh build --target qemu \
    --extra-repo "$QM_COPR_URL" qm.aib.yml qm.qcow2
