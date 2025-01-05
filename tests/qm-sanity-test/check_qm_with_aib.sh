#!/bin/bash

# Create AIB manifest with the correct QM copr
USE_QM_COPR="${PACKIT_COPR_PROJECT:-rhcontainerbot/qm}"
sed -e "s,\${QM_COPR},${USE_QM_COPR},g" check_qm_with_aib.aib.yml > qm.aib.yml

AIB="automotive-image-builder build --export qcow2 qm.aib.yml qm.qcow2"
BUILDDIR=_build
# OSBUILD_BUILDDIR with podman machine is on local non-overlayfs filesystem /root, with native podman it needs to be on host's filesystem (shared volume /host)
EXEC="cd /host; mkdir -p $BUILDDIR; cp -f /usr/bin/osbuild $BUILDDIR/osbuild; chcon system_u:object_r:install_exec_t:s0 $BUILDDIR/osbuild; export PATH=$BUILDDIR:\$PATH; export OSBUILD_BUILDDIR=$BUILDDIR; $AIB"

podman run -v /dev:/dev -v "$PWD":/host --rm --privileged --pull=newer --security-opt label=type:unconfined_t --read-only=false quay.io/centos-sig-automotive/automotive-osbuild /bin/bash -c "$EXEC"
