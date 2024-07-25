#!/bin/bash

# shellcheck disable=SC1091
. ../common/prepare.sh

#Preset with expected value the variable.
expected_value="setenforce:  security_setenforce() failed:  Permission denied"

# Get setenforce 0 permission denied from qm.
setenforce_0=$(podman exec -it qm setenforce 0)

echo "This is what qm returns $setenforce_0"

#Check if setenforce 0 succeeds in QM container and fail the test if it does.
if      [[ $setenforce_0 != *"$expected_value"* ]];then
        echo "FAIL: setenforce 0: Attempt to change Selinux enforcement to 0 succeeded inside QM container."
        exit 1
fi

echo "PASS: setenforce 0: Attempt to change Selinux enforcement to 0 denied successfully inside QM container."
exit 0
