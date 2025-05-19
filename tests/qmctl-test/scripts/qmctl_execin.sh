#!/bin/bash

# shellcheck disable=SC1091
. ../e2e/lib/utils

QMCTL_SCRIPT="../../tools/qmctl/qmctl"

tmp_file="/tmp/file-execin.txt"
if python3 $QMCTL_SCRIPT execin alpine-podman ls -la /tmp/ | grep -q $tmp_file; then
    echo "FAIL: The file /tmp/file-execin.txt already exists"
    exit 1
fi

python3 $QMCTL_SCRIPT execin alpine-podman touch /tmp/file-execin.txt

if ! python3 $QMCTL_SCRIPT execin alpine-podman cat /tmp/file-execin.txt; then
    echo "FAIL: The file /tmp/file-execin.txt was not created"
    exit 1
fi

info_message "PASS: qmctl execin command executed successfully"
exit 0
