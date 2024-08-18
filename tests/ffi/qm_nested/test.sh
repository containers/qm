#!/bin/bash

# shellcheck disable=SC1091
. ../common/prepare.sh

# Declare global variables and initialize to 0
NESTED_NAME=0
NESTED_STATUS=0

# Create nested container fedora inside the QM.
# Function to create and start nested container fedora, while executing podman commands from inside the QM container.
# Extract nested container's valuable information and store it inside the global variables for later use.
# Globals:
#  NESTED_NAME: The nested container name in the QM container.
#  NESTED_STATUS: The nested container status in the QM container.
create_nested() {
        podman exec -it qm bash -c "podman run -d -it --name fedora fedora /bin/bash"
        echo "Container started inside QM."
        NESTED_NAME=$(podman exec -it qm bash -c "podman inspect fedora --format '{{.Name}}'")
        echo "Container name is: $NESTED_NAME"
        NESTED_STATUS=$(podman exec -it qm bash -c "podman inspect --format='{{.State.Status}}' fedora")
        echo "Container $NESTED_NAME status is: $NESTED_STATUS"
}

# Function to check and verify that nested container fedora was created and is running inside the QM container.
# Globals:
#  NESTED_NAME: The nested container name in the QM container.
#  NESTED_STATUS: The nested container status in the QM container.
compare_values() {
        local expected_nested_name="fedora"
        local expected_nested_status="running"

        if [ "$NESTED_NAME" == 0 ] || [ "$NESTED_STATUS" == 0 ]; then
                echo "FAIL: Failed to run the container inside QM."
                exit 1
        elif [[ $NESTED_NAME != *"$expected_nested_name"* ]];then
                echo "FAIL: The $expected_nested_name container had not been created inside QM."
                exit 1
        elif [[ $NESTED_STATUS != *"$expected_nested_status"*  ]];then
                echo "FAIL: The container status is not $expected_nested_status inside QM."
        fi

        echo "PASS: The container $NESTED_NAME is $NESTED_STATUS inside QM."
}

# Execute the functions
create_nested
compare_values

exit 0
