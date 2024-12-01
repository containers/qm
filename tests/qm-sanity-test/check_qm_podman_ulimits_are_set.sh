#!/bin/bash -x

# shellcheck disable=SC1091
source ../e2e/lib/utils

U_NOFILE_PRCTG=${NOFILE_RATIO:-0.5}
U_NPROC_PRCTG=${NPROC_RATIO:-0.75}
QM_CTR_CFG=/etc/qm/containers/containers.conf

# Verify podman run and exec container inside qm with service file
check_qm_podman_ulimits_are_set(){
    local ulimit_nofile
    local ulimit_nproc=
    info_message "check_qm_podman_ulimits_are_set(): \
    prepare qm containers.conf file
    refer issue #666"
    info_message "check_qm_podman_ulimits_are_set(): qm-sanity-test update qm ulimits"
    exec_cmd "test -e ${QM_CTR_CFG}"
    ulimit_nofile=$(printf %.0f "$(echo "$(ulimit -n) * $U_NOFILE_PRCTG" | bc)")
    ulimit_nproc=$(printf %.0f "$(echo "$(ulimit -u) * $U_NPROC_PRCTG" | bc)")
    exec_cmd "sed -i -E 's/(default_ulimits = \[)/\1\"nproc=$ulimit_nproc:$ulimit_nproc\",\"nofile=$ulimit_nofile:$ulimit_nofile\"/' $QM_CTR_CFG"
    info_message "check_qm_podman_ulimits_are_set(): qm-sanity-test verify limits are set"
    exec_cmd "grep -oP \(nproc.*\",\|nofile.*\"\)  ${QM_CTR_CFG} | tr -d '\t\",' "
    exit 0
}

check_qm_podman_ulimits_are_set
