#!/bin/bash
# Device Support Library for OCI Hooks
# This file provides standard device discovery functionality for OCI hooks.

# Source common utilities
# shellcheck source=./common.sh disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# Device discovery function using standard filesystem operations
discover_devices() {
    local pattern="$1"
    local device_type="$2"

    # Extract directory path from pattern to check existence first
    local dir_path=""
    if [[ "$pattern" =~ find[[:space:]]+(/[^[:space:]]+) ]]; then
        dir_path="${BASH_REMATCH[1]}"
    fi

    # Check if specific directory exists (for patterns that search specific dirs)
    if [[ -n "$dir_path" && "$dir_path" != "/dev" ]]; then
        if [[ ! -d "$dir_path" ]]; then
            # Directory doesn't exist - return empty, not an error
            return 0
        fi
    fi

    # Normal device discovery
    eval "$pattern" 2>/dev/null || true
}

# Get device information for a given device path
get_device_info() {
    local device_path="$1"

    if [[ ! -e "$device_path" ]]; then
        return 1
    fi

    if [[ ! -c "$device_path" ]]; then
        return 1
    fi

    local stat_output
    if ! stat_output=$(stat -c "%F:%t:%T:%f:%u:%g" "$device_path" 2>/dev/null); then
        return 1
    fi

    local major minor file_mode uid gid
    IFS=':' read -r _ major minor file_mode uid gid <<<"$stat_output"

    # Convert hex to decimal
    major=$((0x$major))
    minor=$((0x$minor))
    file_mode=$((0x$file_mode))

    # Determine device type
    local device_type="c"

    # Return colon-separated values
    echo "$device_type:$major:$minor:$file_mode:$uid:$gid"
}

# Check if device directory exists
should_process_device_type() {
    local device_type="$1"
    local directory="$2"

    # Process if the directory exists and is accessible
    [[ -d "$directory" ]] 2>/dev/null
}

# GPU device discovery for wayland-client-devices
discover_gpu_devices() {
    # Normal device discovery - check if directory exists first
    if [[ -d "/dev/dri" ]]; then
        find /dev/dri -type c \( -regex ".*/render.*" \) 2>/dev/null || true
    else
        # No GPU devices directory - return empty (not an error)
        return 0
    fi
}
