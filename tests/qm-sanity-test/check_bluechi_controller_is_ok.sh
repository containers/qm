#!/bin/bash -euvx

# shellcheck disable=SC1091
source ../e2e/lib/utils


# Verify bluechi-controller is up and bluechictl is ok
check_bluechi_controller_is_ok(){
    if [ "$(systemctl is-active bluechi-controller)" == "active" ]; then
        info_message "check_bluechi_controller_is_ok(): bluechi-controller is active."
        info_message "PASS: check_bluechi_controller_is_ok()"
    else
        info_message "FAIL: check_bluechi_controller_is_ok(): bluechi-controller is not active."
        exit 1
    fi

    regex_qm_localrootfs="qm.localrootfs * \| online"
    regex_ASIL_localrootfs="localrootfs * \| online"
    if [[ ! "$(bluechictl status)" =~ ${regex_qm_localrootfs} ]]; then
        info_message "FAIL: check_bluechi_controller_is_ok: Checking QM bluechi-agent online failed.\n $(bluechictl status)"
        exit 1
    elif [[ ! "$(bluechictl status)" =~ ${regex_ASIL_localrootfs} ]]; then
        info_message "FAIL: check_bluechi_controller_is_ok: Checking host bluechi-agent online failed.\n $(bluechictl status)"
        exit 1
    else
        info_message "check_bluechi_controller_is_ok: QM bluechi-agent is online."
        info_message "check_bluechi_controller_is_ok: host bluechi-agent is online."
        info_message "PASS: check_bluechi_controller_is_ok()"
        exit 0
    fi
}

check_bluechi_controller_is_ok