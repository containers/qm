#!/bin/bash
# Mock Device Support Library for OCI Hooks Testing
# This file provides device mocking functionality for testing OCI hooks
# without requiring actual system devices.

# Source common utilities
# shellcheck source=./common.sh disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# Device discovery function with test override support
discover_devices() {
    local pattern="$1"
    local device_type="$2"

    # Check for test override environment variable
    local override_var="TEST_MOCK_${device_type^^}_DEVICES"
    local override_value="${!override_var:-}"

    if [[ -n "$override_value" ]]; then
        # Use test-provided mock devices
        log "DEBUG" "Using mock $device_type devices: $override_value"
        # Convert comma-separated devices to null-terminated individual paths
        IFS=',' read -ra device_array <<<"$override_value"
        for device in "${device_array[@]}"; do
            printf '%s\0' "$device"
        done
        return
    fi

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

    # Normal device discovery fallback
    eval "$pattern" 2>/dev/null || true
}

# Get device information - works with real temporary device files created by mknod
get_device_info() {
    local device_path="$1"

    # First try to get real device info (works if mknod succeeded)
    if [[ -e "$device_path" && -c "$device_path" ]]; then
        local stat_output
        if stat_output=$(stat -c "%F:%t:%T:%f:%u:%g" "$device_path" 2>/dev/null); then
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
            return 0
        fi
    fi

    # If real device doesn't exist and we're in test mode, generate mock device info
    if [[ "${FORCE_MOCK_DEVICES:-false}" == "true" || -n "${TEST_LOGFILE:-}" ]]; then
        # Check if this path matches any of our test mock device patterns
        local is_mock=false
        for env_var in TEST_MOCK_AUDIO_DEVICES TEST_MOCK_VIDEO_DEVICES TEST_MOCK_INPUT_DEVICES \
            TEST_MOCK_GPU_DEVICES TEST_MOCK_TTYUSB_DEVICES TEST_MOCK_DVB_DEVICES \
            TEST_MOCK_RADIO_DEVICES TEST_MOCK_TTYS_DEVICES; do
            if [[ -n "${!env_var:-}" ]]; then
                IFS=',' read -ra mock_devices <<<"${!env_var}"
                for mock_device in "${mock_devices[@]}"; do
                    if [[ "$mock_device" == "$device_path" ]]; then
                        is_mock=true
                        break 2
                    fi
                done
            fi
        done
        if [[ "$is_mock" == "true" ]]; then
            # Generate mock device info based on device path patterns
            local major minor file_mode=8624 uid=0 gid=0 # Default values
            local device_type="c"

            case "$device_path" in
            */snd/*)
                major=116
                minor=$((RANDOM % 20 + 1))
                ;; # ALSA devices
            */video*)
                major=81
                minor=$((RANDOM % 10))
                ;; # Video devices
            */input/*)
                major=13
                minor=$((RANDOM % 32))
                ;; # Input devices
            */dri/*)
                major=226
                minor=$((RANDOM % 10 + 128))
                ;; # DRI/GPU devices
            */ttyUSB*)
                major=188
                minor=$((RANDOM % 10))
                ;; # USB serial
            */dvb/*)
                major=212
                minor=$((RANDOM % 10))
                ;; # DVB devices
            */radio*)
                major=81
                minor=$((RANDOM % 10 + 64))
                ;; # Radio devices
            */tty[0-9]*)
                major=4
                minor=$((RANDOM % 10))
                ;; # TTY devices
            *)
                major=1
                minor=$((RANDOM % 10))
                ;; # Fallback
            esac

            # Adjust gid for audio devices (usually audio group = 63)
            if [[ "$device_path" == */snd/* ]]; then
                gid=63
            fi

            echo "$device_type:$major:$minor:$file_mode:$uid:$gid"
            return 0
        fi
    fi

    # Neither real device nor mock - fail
    return 1
}

# Check if device directory exists or we have mock devices for the type
should_process_device_type() {
    local device_type="$1"
    local directory="$2"

    local override_var="TEST_MOCK_${device_type^^}_DEVICES"
    local override_value="${!override_var:-}"

    # Process if we have mock devices OR the directory exists and is accessible
    [[ -n "$override_value" ]] || [[ -d "$directory" ]] 2>/dev/null
}

# GPU device discovery with mocking support for wayland-client-devices
discover_gpu_devices() {
    if [[ -n "${TEST_MOCK_GPU_DEVICES:-}" ]]; then
        # Use test-provided mock devices
        log "DEBUG" "Using mock GPU devices: $TEST_MOCK_GPU_DEVICES"
        echo "$TEST_MOCK_GPU_DEVICES" | tr ',' ' '
    else
        # Normal device discovery - check if directory exists first
        if [[ -d "/dev/dri" ]]; then
            find /dev/dri -type c \( -regex ".*/render.*" \) 2>/dev/null || true
        else
            # No GPU devices directory - return empty (not an error)
            log "DEBUG" "No /dev/dri directory found - no GPU devices available"
            return 0
        fi
    fi
}
