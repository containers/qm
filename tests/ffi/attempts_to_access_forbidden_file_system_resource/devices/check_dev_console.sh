#!/bin/bash -euvx

# shellcheck disable=SC1091
. ../../../e2e/lib/utils

check_dev_console_is_private(){
    local qm_devpts host_devpts

    # qmc provides a console PTY for systemd. It must use private devpts,
    # rather than exposing the host console or a host PTY.
    # Evaluate the shell substitutions inside QM.
    # shellcheck disable=SC2016
    if ! qm_devpts=$(qmc exec /bin/sh -ec '
        if [ ! -e /dev/console ]; then
            test ! -L /dev/console
            echo absent
            exit 0
        fi
        test -c /dev/console
        test "$(stat -fLc %T /dev/pts)" = devpts
        devpts=$(stat -Lc %d /dev/pts)
        test "$(stat -Lc %d /dev/console)" = "$devpts"
        echo "$devpts"
    '); then
        info_message "FAIL: Could not verify that QM has an isolated console."
        exit 1
    fi

    if [[ "$qm_devpts" != absent ]]; then
        host_devpts=$(stat -Lc %d /dev/pts)
        if ! [[ "$qm_devpts" =~ ^[0-9]+$ ]] || [[ "$qm_devpts" == "$host_devpts" ]]; then
            info_message "FAIL: QM's console is not on a private devpts filesystem."
            exit 1
        fi
    fi
    info_message "PASS: check_dev_console_is_private: QM does not expose the host console."
}

check_dev_console_is_private
