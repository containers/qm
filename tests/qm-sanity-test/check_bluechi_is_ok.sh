#!/bin/bash -euvx

# shellcheck disable=SC1091
source ../e2e/lib/utils

print_journal_for_bluechi() {
    info_message "Journal for bluechi-controller:\n"
    journalctl -r -u bluechi-controller -n 100

    info_message "Journal for bluechi-agent:\n"
    journalctl -r -u bluechi-agent -n 100
}

# Verify bluechi nodes are connected
check_bluechi_is_ok(){
    LOCAL=localrootfs
    LOCAL_QM=qm.localrootfs

    if ! bluechi-is-online node "${LOCAL}"; then
        info_message "FAIL: check_bluechi_is_ok: host bluechi-agent ${LOCAL} is not connected to controller."
        print_journal_for_bluechi
        exit 1
    fi

    if ! bluechi-is-online node "${LOCAL_QM}"; then
        info_message "FAIL: check_bluechi_is_ok: host bluechi-agent ${LOCAL_QM} is not connected to controller."
        print_journal_for_bluechi
        exit 1
    fi

    info_message "check_bluechi_is_ok: host bluechi-agent is connected to controller."
    info_message "check_bluechi_is_ok: QM bluechi-agent is connected to controller."
    info_message "PASS: check_bluechi_is_ok()"
    exit 0
}

check_bluechi_is_ok