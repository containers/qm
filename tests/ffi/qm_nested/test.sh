#!/bin/bash -euvx

# shellcheck disable=SC1091
. ../common/prepare.sh

# init_ffi() uses functions from common.sh to init the env before tests.
init_ffi() {
	disk_cleanup
	prepare_test
	reload_config
}

# Declare global variables and initialize to 0
NESTED_NAME=""
NESTED_STATUS=""

# Create nested container ffi-qm inside the QM.
# Function to create and start nested container ffi-qm, while executing podman commands from inside the QM container.
# Extract nested container's valuable information and store it inside the global variables for later use.
# Globals:
#  NESTED_NAME: The nested container name in the QM container.
#  NESTED_STATUS: The nested container status in the QM container.
create_nested() {
	prepare_images
	local nested_container_name="ffi-qm"
	run_container_in_qm "${nested_container_name}"
	NESTED_NAME=$(podman exec -it qm bash -c "podman inspect ${nested_container_name} --format '{{.Name}}'")
	if_error_exit "An error occured: failed to extract Name parameter of container from inside of QM."
	echo "Container name is: ${NESTED_NAME}"
	NESTED_STATUS=$(podman exec -it qm bash -c "podman inspect --format='{{.State.Status}}' ${nested_container_name}")
	if_error_exit "An error occured: failed to extract State parameter of container from inside of QM."
	echo "Container $NESTED_NAME status is: ${NESTED_STATUS}"
}

# Function to check and verify that nested container fedora was created and is running inside the QM container.
# Globals:
#  NESTED_NAME: The nested container name in the QM container.
#  NESTED_STATUS: The nested container status in the QM container.
compare_values() {
	local expected_nested_name="ffi-qm"
        local expected_nested_status="running"

	if [ "${NESTED_NAME}" == "" ] || [ "${NESTED_STATUS}" == "" ]; then
                echo "FAIL: Failed to run the container inside QM."
                exit 1
        elif [[ "${NESTED_NAME}" != *"${expected_nested_name}"* ]]; then
                echo "FAIL: The ${expected_nested_name} container had not been created inside QM."
                exit 1
        elif [[ "${NESTED_STATUS}" != *"${expected_nested_status}"*  ]]; then
                echo "FAIL: The container status is not ${expected_nested_status} inside QM."
		exit 1
        fi

        echo "PASS: The container ${NESTED_NAME} is ${NESTED_STATUS} inside QM."
}

# Execute the functions
init_ffi
create_nested
compare_values

exit 0
