#!/bin/bash -euvx

# shellcheck disable=SC1091
source ../e2e/lib/utils


# Verify bluechi nodes are connected
check_bluechi_is_ok(){
    bluechi_controller_status=$(systemctl status bluechi-controller  | tail -2)
    regex_ASIL_bluechi_agent="Registered managed node from fd [0-9]{1,2} as 'localrootfs'"
    regex_QM_bluechi_agent="Registered managed node from fd [0-9]{1,2} as 'qm.localrootfs'"

    if [[ ! "${bluechi_controller_status}" =~ ${regex_ASIL_bluechi_agent} ]]; then
        info_message "FAIL: check_bluechi_is_ok: host bluechi-agent is not connected to controller.\n ${bluechi_controller_status}"
        exit 1
    elif [[ ! "${bluechi_controller_status}" =~ ${regex_QM_bluechi_agent} ]]; then
        info_message "FAIL: check_bluechi_is_ok: QM bluechi-agent is not connected to controller.\n ${bluechi_controller_status}"
        exit 1
    else
        info_message "check_bluechi_is_ok: host bluechi-agent is connected to controller."
        info_message "check_bluechi_is_ok: QM bluechi-agent is connected to controller."
        info_message "PASS: check_bluechi_is_ok()"
        exit 0
    fi
}

check_bluechi_is_ok