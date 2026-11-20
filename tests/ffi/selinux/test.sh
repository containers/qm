#!/bin/bash

# shellcheck disable=SC1091
. ../common/prepare.sh

#Preset with expected value the variable.
expected_value="setenforce:  security_setenforce() failed:  Permission denied"

# Capture both streams: non-terminal qmc exec keeps stderr separate.
if setenforce_0=$(LC_ALL=C qmc exec setenforce 0 2>&1); then
        echo "FAIL: setenforce 0: Changing SELinux enforcement succeeded inside QM."
        exit 1
fi

echo "This is what qm returns $setenforce_0"

# Require the expected denial, rather than accepting any command failure.
if      [[ $setenforce_0 != *"$expected_value"* ]];then
        echo "FAIL: setenforce 0: Did not receive the expected SELinux permission denial."
        exit 1
fi

echo "PASS: setenforce 0: Attempt to change Selinux enforcement to 0 denied successfully inside QM container."
exit 0
