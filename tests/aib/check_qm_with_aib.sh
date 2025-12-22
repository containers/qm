#!/bin/bash

# shellcheck disable=SC1091
source ../e2e/lib/utils

# Download basic QM manifest
exec_cmd "curl -o qm.aib.yml https://gitlab.com/CentOS/automotive/src/automotive-image-builder/-/raw/main/examples/qm.aib.yml?ref_type=heads"

USE_QM_COPR="${PACKIT_COPR_PROJECT:-@centos-automotive-sig/qm-next}"
COPR_URL="https://download.copr.fedorainfracloud.org/results/${USE_QM_COPR}/epel-9-$(uname -m)/"
#shellcheck disable=SC2089
EXTRA_REPOS="extra_repos=[{id: qm_build, baseurl: $COPR_URL}]"


# Run AIB in container
exec_cmd "curl -o auto-image-builder.sh https://gitlab.com/CentOS/automotive/src/automotive-image-builder/-/raw/main/auto-image-builder.sh?ref_type=heads"
#shellcheck disable=SC2027,SC2090,SC2086
exec_cmd "/bin/bash auto-image-builder.sh build --target qemu --define \\\"$EXTRA_REPOS\\\" qm.aib.yml qm.qcow2"
