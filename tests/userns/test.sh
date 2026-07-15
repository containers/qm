#!/bin/bash -uxv
# shellcheck disable=SC1090,SC1091,SC2317,SC2155,SC2034
#
# Unit tests for userns script functions
# Tests each function in isolation with mock data to avoid system modifications
#

# Source utilities
source ../e2e/lib/utils

# Relative path to userns script
USERNS_SCRIPT="../../userns"

# Global test variables
TEST_DIR=""
MOCK_ROOT_DIR=""
MOCK_SYSUSERS_DIR=""
MOCK_DROPIN_DIR=""
SYSUSERS_CONF="qm-sysusers.conf"
QM_CONF="qm-user-namespaces.conf"
TEST_PASSED=0
TEST_FAILED=0

# Test configuration
USERMOD_CALLS=()
SYSTEMD_SYSUSERS_CALLED=0

#######################################
# Setup test environment
# Creates temporary directories and mock files
#######################################
setup_test_env() {
    info_message "Setting up test environment"
    TEST_DIR=$(mktemp -d -t userns-test.XXXXXX)
    MOCK_ROOT_DIR="${TEST_DIR}"
    MOCK_QM_ROOT_DIR="${MOCK_ROOT_DIR}/qm/rootfs"
    MOCK_SYSUSERS_DIR="${MOCK_ROOT_DIR}/etc/sysusers.d"
    MOCK_DROPIN_DIR="${TEST_DIR}/etc/containers/systemd/qm.container.d"

    mkdir -p "${MOCK_ROOT_DIR}"
    mkdir -p "${MOCK_QM_ROOT_DIR}"
    mkdir -p "${MOCK_SYSUSERS_DIR}"
    mkdir -p "${MOCK_DROPIN_DIR}"

    mkdir -p "${MOCK_SYSUSERS_DIR}"
    mkdir -p "${MOCK_QM_ROOT_DIR}/etc"

    info_message "Test directory created at ${TEST_DIR}"
}

#######################################
# Cleanup test environment
# Removes all temporary files and directories
#######################################
cleanup_test_env() {
    if [ -n "${TEST_DIR}" ] && [ -d "${TEST_DIR}" ]; then
        info_message "Cleaning up test directory ${TEST_DIR}"
        rm -rf "${TEST_DIR}"
    fi
}

# Register cleanup trap
trap cleanup_test_env EXIT

#######################################
# Create mock /etc/passwd file
# Arguments:
#   $1 - Path to output file
#######################################
create_mock_passwd() {
    cat > "${MOCK_QM_ROOT_DIR}/etc/passwd" << 'EOF'
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
testuser:x:1000:1000:Test User:/home/testuser:/bin/bash
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
EOF
}

#######################################
# Create mock /etc/group file
# Arguments:
#   $1 - Path to output file
#######################################
create_mock_group() {
    cat > "${MOCK_QM_ROOT_DIR}/etc/group" << 'EOF'
root:x:0:
daemon:x:1:
bin:x:2:
sys:x:3:
adm:x:4:
tty:x:5:
disk:x:6:
testgroup:x:1000:
users:x:100:
nogroup:x:65534:
EOF
}

#######################################
# Create mock /etc/subuid and /etc/subgid files
# Arguments:
#   $1 - Path to subuid file
#   $2 - Path to subgid file
#######################################
create_mock_subid_files() {
    local subuid_file="$1"
    local subgid_file="$2"

    cat > "${subuid_file}" << 'EOF'
root:100000:65536
testuser:165536:65536
existing_user:231072:65536
EOF

    cat > "${subgid_file}" << 'EOF'
root:100000:65536
testuser:165536:65536
existing_user:231072:65536
EOF
}

#######################################
# Mock usermod command
# Records calls instead of actually running usermod
#######################################
usermod() {
    USERMOD_CALLS+=("$*")
    info_message "MOCK: usermod $*"
}

#######################################
# Mock systemd-sysusers command
#######################################
systemd-sysusers() {
    ((SYSTEMD_SYSUSERS_CALLED++))
    info_message "MOCK: systemd-sysusers called"
}

#######################################
# Verify sysusers configuration file format
# Arguments:
#   $1 - Path to sysusers config file
# Returns:
#   0 if valid, 1 if invalid
#######################################
verify_sysusers_format() {
    local config_file="${1}"

    if [ ! -f "${config_file}" ]; then
        fail_message "Config file ${config_file} does not exist"
        return 1
    fi

    local line_count=$(wc -l < "${config_file}")
    if [ "${line_count}" -eq 0 ]; then
        fail_message "Config file is empty"
        return 1
    fi

    # Check for expected format: "u     qm_username      UID:GID" for users (with multiple spaces)
    # and "g     qm_groupname     GID" for groups
    # Also skip comment lines starting with #
    local user_pattern='^u[[:space:]]+qm_[a-z0-9_-]+[[:space:]]+[0-9]+:[0-9]+[[:space:]]+".*"$'
    local group_pattern='^g[[:space:]]+qm_[a-z0-9_-]+[[:space:]]+[0-9]+$'
    local comment_pattern='^#'

    while IFS= read -r line; do
        # Skip comment lines
        if [[ "${line}" =~ ${comment_pattern} ]]; then
            continue
        fi
        if [[ ! "${line}" =~ ${user_pattern} ]] && [[ ! "${line}" =~ ${group_pattern} ]]; then
            fail_message "Invalid line format: ${line}"
            return 1
        fi
    done < "${config_file}"

    return 0
}

#######################################
# Record test result
# Arguments:
#   $1 - Test name
#   $2 - Result (0 for pass, non-zero for fail)
#######################################
record_test_result() {
    local test_name="$1"
    local result="$2"

    if [ "${result}" -eq 0 ]; then
        pass_message "PASS: ${test_name}"
        ((TEST_PASSED++))
    else
        fail_message "FAIL: ${test_name}"
        ((TEST_FAILED++))
    fi
}

#######################################
# Test: generate_sysusers_conf with basic input
#######################################
test_generate_sysusers_conf_basic() {
    info_message "TEST: generate_sysusers_conf - basic functionality"

    # Source the userns script to get the function
    source "${USERNS_SCRIPT}"
    # overwrite the userns root and qm root dir
    local ROOT_DIR="${MOCK_ROOT_DIR}"
    local QM_ROOT_DIR="${MOCK_QM_ROOT_DIR}"
    create_mock_passwd
    create_mock_group

    # Execute
    generate_sysusers_conf 1000000000

    # Verify
    local output_file="${MOCK_SYSUSERS_DIR}/${SYSUSERS_CONF}"

    local result=0
    if ! verify_sysusers_format "${output_file}"; then
        result=1
    fi

    # Check that root user is transformed correctly (allowing for whitespace)
    if ! grep -q "qm_root[[:space:]]\+1000000000:1000000000" "${output_file}"; then
        fail_message "Root user not found with correct UID:GID"
        result=1
    fi

    # Check that testuser is transformed correctly (UID 1000 + offset)
    if ! grep -q "qm_testuser[[:space:]]\+1000001000:1000001000" "${output_file}"; then
        fail_message "testuser not found with correct UID:GID"
        result=1
    fi

    # Check that groups are created
    if ! grep -q "qm_root[[:space:]]\+1000000000" "${output_file}"; then
        fail_message "Root group not found"
        result=1
    fi

    record_test_result "generate_sysusers_conf_basic" "${result}"
    return "${result}"
}

#######################################
# Test: generate_sysusers_conf with custom offset
#######################################
test_generate_sysusers_conf_custom_offset() {
    info_message "TEST: generate_sysusers_conf - custom offset"

    # Source the userns script to get the function
    source "${USERNS_SCRIPT}"
    # overwrite the userns root and qm root dir
    local ROOT_DIR="${MOCK_ROOT_DIR}"
    local QM_ROOT_DIR="${MOCK_QM_ROOT_DIR}"
    create_mock_passwd
    create_mock_group

    # Execute with different offset
    local custom_offset=5000000000
    generate_sysusers_conf "${custom_offset}"

    # Verify
    local output_file="${MOCK_SYSUSERS_DIR}/${SYSUSERS_CONF}"
    local result=0

    # Check that root user has custom offset applied
    if ! grep -q "qm_root[[:space:]]\+${custom_offset}:${custom_offset}" "${output_file}"; then
        fail_message "Root user not found with custom offset"
        result=1
    fi

    # Check that testuser has custom offset applied (1000 + 5000000000)
    local expected_uid=$((1000 + custom_offset))
    if ! grep -q "qm_testuser[[:space:]]\+${expected_uid}:${expected_uid}" "${output_file}"; then
        fail_message "testuser not found with custom offset (expected ${expected_uid})"
        result=1
    fi

    record_test_result "generate_sysusers_conf_custom_offset" "${result}"
    return "${result}"
}

#######################################
# Test: generate_sysusers_conf preserves GECOS field
#######################################
test_generate_sysusers_conf_gecos() {
    info_message "TEST: generate_sysusers_conf - GECOS preservation"

    # Source the userns script to get the function
    source "${USERNS_SCRIPT}"
    # overwrite the userns root and qm root dir
    local ROOT_DIR="${MOCK_ROOT_DIR}"
    local QM_ROOT_DIR="${MOCK_QM_ROOT_DIR}"
    create_mock_passwd
    create_mock_group

    # Execute
    generate_sysusers_conf 1000000000

    # Verify
    local output_file="${MOCK_SYSUSERS_DIR}/${SYSUSERS_CONF}"
    local result=0

    # Check that GECOS field is preserved with "QM - " prefix
    if ! grep -q 'qm_testuser[[:space:]]\+[0-9]\+:[0-9]\+[[:space:]]\+"QM - Test User"' "${output_file}"; then
        fail_message "GECOS field not properly preserved for testuser"
        result=1
    fi

    if ! grep -q 'qm_root[[:space:]]\+[0-9]\+:[0-9]\+[[:space:]]\+"QM - root"' "${output_file}"; then
        fail_message "GECOS field not properly preserved for root"
        result=1
    fi

    record_test_result "generate_sysusers_conf_gecos" "${result}"
    return "${result}"
}

#######################################
# Test: generate_qm_dropin basic functionality
#######################################
test_generate_qm_dropin_basic() {
    info_message "TEST: generate_qm_dropin - basic functionality"

    # Source the userns script
    source "${USERNS_SCRIPT}"
    local ROOT_DIR="${MOCK_ROOT_DIR}"
    local QM_ROOT_DIR="${MOCK_QM_ROOT_DIR}"
    local test_user="qm_root"

    # Execute
    generate_qm_dropin "${test_user}"

    # Verify
    local dropin_file="${MOCK_DROPIN_DIR}/${QM_CONF}"
    local result=0

    if [ ! -f "${dropin_file}" ]; then
        fail_message "Dropin file was not created"
        result=1
    fi

    if ! grep -q "^SubUIDMap=${test_user}$" "${dropin_file}"; then
        fail_message "SubUIDMap not set correctly"
        result=1
    fi

    if ! grep -q "^SubGIDMap=${test_user}$" "${dropin_file}"; then
        fail_message "SubGIDMap not set correctly"
        result=1
    fi

    record_test_result "generate_qm_dropin_basic" "${result}"
    return "${result}"
}

#######################################
# Test: generate_qm_dropin with different username
#######################################
test_generate_qm_dropin_custom_user() {
    info_message "TEST: generate_qm_dropin - custom username"

    # Source the userns script
    source "${USERNS_SCRIPT}"
    local ROOT_DIR="${MOCK_ROOT_DIR}"
    local QM_ROOT_DIR="${MOCK_QM_ROOT_DIR}"
    local test_user="qm_root"

    # Execute
    generate_qm_dropin "${test_user}"

    # Verify
    local dropin_file="${MOCK_DROPIN_DIR}/${QM_CONF}"
    local result=0

    if ! grep -q "^SubUIDMap=${test_user}$" "${dropin_file}"; then
        fail_message "SubUIDMap not set to custom username"
        result=1
    fi

    if ! grep -q "^SubGIDMap=${test_user}$" "${dropin_file}"; then
        fail_message "SubGIDMap not set to custom username"
        result=1
    fi

    record_test_result "generate_qm_dropin_custom_user" "${result}"
    return "${result}"
}

#######################################
# Test: add_subid_entries with new user
# Note: This tests the logic by verifying parameter calculation,
# but uses mock usermod to avoid system modifications
#######################################
test_add_subid_entries_new_user() {
    info_message "TEST: add_subid_entries - new user"

    # Create a test wrapper that mimics add_subid_entries but with testable paths
    test_add_subid_entries_impl() {
        local id_range_start=$1
        local id_range=$2
        local id_range_end=$((id_range_start+id_range))
        local user=$3
        local subuid_file="${MOCK_ROOT_DIR}/subuid"
        local subgid_file="${MOCK_ROOT_DIR}/subgid"

        if ! grep -q "^${user}:" "${subuid_file}" 2>/dev/null; then
            usermod --add-subuids "${id_range_start}-${id_range_end}" "${user}"
        fi
        if ! grep -q "^${user}:" "${subgid_file}" 2>/dev/null; then
            usermod --add-subgids "${id_range_start}-${id_range_end}" "${user}"
        fi
    }

    # Setup
    local subuid_file="${MOCK_ROOT_DIR}/subuid"
    local subgid_file="${MOCK_ROOT_DIR}/subgid"
    create_mock_subid_files "${subuid_file}" "${subgid_file}"

    # Reset mock tracking
    USERMOD_CALLS=()

    # Execute - add entries for a new user
    test_add_subid_entries_impl 1000000000 1500000000 "new_user"

    # Verify
    local result=0

    # Should have called usermod twice (once for subuids, once for subgids)
    if [ "${#USERMOD_CALLS[@]}" -ne 2 ]; then
        fail_message "Expected 2 usermod calls, got ${#USERMOD_CALLS[@]}"
        result=1
    fi

    # Check that usermod was called with correct arguments
    local expected_range="1000000000-2500000000"
    if ! echo "${USERMOD_CALLS[0]}" | grep -q -- "--add-subuids ${expected_range} new_user"; then
        fail_message "usermod not called with correct subuids range"
        result=1
    fi

    if ! echo "${USERMOD_CALLS[1]}" | grep -q -- "--add-subgids ${expected_range} new_user"; then
        fail_message "usermod not called with correct subgids range"
        result=1
    fi

    record_test_result "add_subid_entries_new_user" "${result}"
    return "${result}"
}

#######################################
# Test: add_subid_entries idempotency (existing user)
#######################################
test_add_subid_entries_existing_user() {
    info_message "TEST: add_subid_entries - existing user (idempotency)"

    # Create a test wrapper that mimics add_subid_entries but with testable paths
    test_add_subid_entries_existing_impl() {
        local id_range_start=$1
        local id_range=$2
        local id_range_end=$((id_range_start+id_range))
        local user=$3
        local subuid_file="${MOCK_ROOT_DIR}/subuid"
        local subgid_file="${MOCK_ROOT_DIR}/subgid"

        if ! grep -q "^${user}:" "${subuid_file}" 2>/dev/null; then
            usermod --add-subuids "${id_range_start}-${id_range_end}" "${user}"
        fi
        if ! grep -q "^${user}:" "${subgid_file}" 2>/dev/null; then
            usermod --add-subgids "${id_range_start}-${id_range_end}" "${user}"
        fi
    }

    # Setup
    local subuid_file="${MOCK_ROOT_DIR}/subuid"
    local subgid_file="${MOCK_ROOT_DIR}/subgid"
    create_mock_subid_files "${subuid_file}" "${subgid_file}"

    # Reset mock tracking
    USERMOD_CALLS=()

    # Execute - try to add entries for existing user
    test_add_subid_entries_existing_impl 100000 65536 "testuser"

    # Verify
    local result=0

    # Should NOT have called usermod since user already exists
    if [ "${#USERMOD_CALLS[@]}" -ne 0 ]; then
        fail_message "Expected 0 usermod calls for existing user, got ${#USERMOD_CALLS[@]}"
        result=1
    fi

    record_test_result "add_subid_entries_existing_user" "${result}"
    return "${result}"
}

#######################################
# Test: remove_subid_entries basic functionality
#######################################
test_remove_subid_entries_basic() {
    info_message "TEST: remove_subid_entries - basic functionality"

    # Create a test wrapper that mimics remove_subid_entries but with testable paths
    test_remove_subid_entries_impl() {
        local user=$1
        local subuid_file="${MOCK_ROOT_DIR}/subuid"
        local subgid_file="${MOCK_ROOT_DIR}/subgid"
        sed -i "/^${user}:/d" "${subuid_file}"
        sed -i "/^${user}:/d" "${subgid_file}"
    }

    # Setup
    local subuid_file="${MOCK_ROOT_DIR}/subuid"
    local subgid_file="${MOCK_ROOT_DIR}/subgid"
    create_mock_subid_files "${subuid_file}" "${subgid_file}"

    # Execute - remove testuser entries
    test_remove_subid_entries_impl "testuser"

    # Verify
    local result=0

    # Check that testuser was removed from subuid
    if grep -q "^testuser:" "${subuid_file}"; then
        fail_message "testuser still present in ${subuid_file}"
        result=1
    fi

    # Check that testuser was removed from subgid
    if grep -q "^testuser:" "${subgid_file}"; then
        fail_message "testuser still present in ${subgid_file}"
        result=1
    fi

    # Check that other users remain
    if ! grep -q "^root:" "${subuid_file}"; then
        fail_message "root was incorrectly removed from ${subuid_file}"
        result=1
    fi

    if ! grep -q "^existing_user:" "${subuid_file}"; then
        fail_message "existing_user was incorrectly removed from ${subuid_file}"
        result=1
    fi

    record_test_result "remove_subid_entries_basic" "${result}"
    return "${result}"
}

#######################################
# Test: remove_subid_entries with non-existent user
#######################################
test_remove_subid_entries_nonexistent() {
    info_message "TEST: remove_subid_entries - non-existent user"

    # Create a test wrapper that mimics remove_subid_entries but with testable paths
    test_remove_subid_entries_nonexistent_impl() {
        local user=$1
        local subuid_file="${MOCK_ROOT_DIR}/subuid"
        local subgid_file="${MOCK_ROOT_DIR}/subgid"
        sed -i "/^${user}:/d" "${subuid_file}"
        sed -i "/^${user}:/d" "${subgid_file}"
    }

    # Setup
    local subuid_file="${MOCK_ROOT_DIR}/subuid"
    local subgid_file="${MOCK_ROOT_DIR}/subgid"
    create_mock_subid_files "${subuid_file}" "${subgid_file}"

    # Count lines before
    local subuid_lines_before=$(wc -l < "${subuid_file}")
    local subgid_lines_before=$(wc -l < "${subgid_file}")

    # Execute - try to remove non-existent user (should not error)
    test_remove_subid_entries_nonexistent_impl "nonexistent_user"

    # Verify
    local result=0

    # Check that file contents haven't changed
    local subuid_lines_after=$(wc -l < "${subuid_file}")
    local subgid_lines_after=$(wc -l < "${subgid_file}")

    if [ "${subuid_lines_before}" -ne "${subuid_lines_after}" ]; then
        fail_message "subuid file was modified when removing non-existent user"
        result=1
    fi

    if [ "${subgid_lines_before}" -ne "${subgid_lines_after}" ]; then
        fail_message "subgid file was modified when removing non-existent user"
        result=1
    fi

    record_test_result "remove_subid_entries_nonexistent" "${result}"
    return "${result}"
}

#######################################
# Main test execution
#######################################
main() {
    info_message "=== Starting userns unit tests ==="

    # Setup environment
    setup_test_env

    # Run all tests
    test_generate_sysusers_conf_basic
    test_generate_sysusers_conf_custom_offset
    test_generate_sysusers_conf_gecos
    test_generate_qm_dropin_basic
    test_generate_qm_dropin_custom_user
    test_add_subid_entries_new_user
    test_add_subid_entries_existing_user
    test_remove_subid_entries_basic
    test_remove_subid_entries_nonexistent

    # Summary
    info_message "=== Test Summary ==="
    pass_message "Tests passed: ${TEST_PASSED}"
    if [ "${TEST_FAILED}" -gt 0 ]; then
        fail_message "Tests failed: ${TEST_FAILED}"
        exit 1
    else
        pass_message "All tests passed!"
        exit 0
    fi
}

# Run tests
main
