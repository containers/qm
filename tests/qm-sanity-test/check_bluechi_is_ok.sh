#!/bin/bash -euvx

# shellcheck disable=SC1091
source ../e2e/lib/utils

print_journal_for_bluechi() {
    info_message "Journal for bluechi-controller:\n"
    journalctl -r -u bluechi-controller -n 100

    info_message "Journal for local bluechi-agent:\n"
    journalctl -r -u bluechi-agent -n 100

    info_message "Journal for qm bluechi-agent:\n"
    journalctl -r -u qm -n 100
}

# Verify bluechi nodes are connected
check_bluechi_is_ok(){
    LOCAL=localrootfs
    LOCAL_QM=qm.localrootfs

    if ! bluechi-is-online node "${LOCAL}" --wait=5000; then
        info_message "FAIL: check_bluechi_is_ok: host bluechi-agent ${LOCAL} is not connected to controller."
        print_journal_for_bluechi
    fi

    if ! bluechi-is-online node "${LOCAL_QM}" --wait=5000; then
        info_message "FAIL: check_bluechi_is_ok: qm bluechi-agent ${LOCAL_QM} is not connected to controller."
        print_journal_for_bluechi
    fi

    
    info_message "check_bluechi_is_ok: host bluechi-agent is connected to controller."
    info_message "check_bluechi_is_ok: QM bluechi-agent is connected to controller."
    info_message "PASS: check_bluechi_is_ok()"

    print_journal_for_bluechi
    info_message "Checking avcs:"
    ausearch -m avc
    info_message "systemctl cat qm.service:"
    systemctl cat qm.service

    exit 0
}

check_bluechi_is_ok