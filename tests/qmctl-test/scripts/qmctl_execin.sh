#!/bin/bash

QMCTL_SCRIPT="../../tools/qmctl/qmctl"

tmp_file="/tmp/file-execin.txt"
if python3 $QMCTL_SCRIPT execin alpine-podman ls -la /tmp/ | grep -q $tmp_file; then
    echo "The file /tmp/file-execin.txt already exists"
    exit 1
fi

python3 $QMCTL_SCRIPT execin alpine-podman touch /tmp/file-execin.txt

if ! python3 $QMCTL_SCRIPT execin alpine-podman cat /tmp/file-execin.txt; then
    echo "The file /tmp/file-execin.txt was not created"
    exit 1
fi
exit 0
