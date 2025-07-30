#!/bin/bash
# Common Utility Library for OCI Hooks
# This file provides shared utility functions for all OCI hooks.

# Common logging function for OCI hooks
log() {
    local level="$1"
    shift
    local message
    message="$(date '+%Y-%m-%d %H:%M:%S') - ${HOOK_NAME:-oci-hook} - $level - $*"

    # Write to log file if LOGFILE is set
    if [[ -n "${LOGFILE:-}" ]]; then
        echo "$message" >>"$LOGFILE"
    fi

    # Also write errors to stderr
    if [[ "$level" == "ERROR" ]]; then
        echo "$message" >&2
    fi
}
