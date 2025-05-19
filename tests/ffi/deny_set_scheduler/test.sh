#!/bin/bash -euvx

# shellcheck source=tests/ffi/common/prepare.sh
. ../common/prepare.sh

policy_arr=(SCHED_OTHER SCHED_BATCH SCHED_IDLE SCHED_FIFO SCHED_RR)
num_of_failed_policy=0

trap disk_cleanup EXIT
prepare_test
reload_config

running_container_in_qm

for policy in "${policy_arr[@]}"; do
    return_from_setscheduler=$(podman exec -it qm /usr/bin/podman exec -it ffi-qm ./QM/test_sched_setscheduler "$policy")

    # Assign the expected result according to the policy
    if [[ "$policy" == "SCHED_OTHER" || "$policy" == "SCHED_BATCH" || "$policy" == "SCHED_IDLE" ]]; then
        expected_result="sched_setscheduler($policy) succeeded."
    elif [[ "$policy" == "SCHED_FIFO" || "$policy" == "SCHED_RR" ]]; then
        expected_result="sched_setscheduler($policy) failed: errno=38 (Function not implemented)"
    fi

    # Check that the result is the same as expected
    if [[ "${return_from_setscheduler}" == "${expected_result}" ]]; then
        info_message "$expected_result"
        info_message "PASS: The result of sched_setscheduler($policy) is as expected in QM."
    else
        info_message "$return_from_setscheduler"
        info_message "FAIL: The result of sched_setscheduler($policy) is not what is expected in QM."
        ((num_of_failed_policy++))
    fi
done

# If there is a failed policy, then this test returns failure
if [[ $num_of_failed_policy -gt 0 ]]; then
    info_message "FAIL: sched_setscheduler() test failed."
    exit 1
else
    info_message "PASS: sched_setscheduler() test passed."
    exit 0
fi
