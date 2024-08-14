#!/bin/bash

# shellcheck disable=SC1091
. ../common/prepare.sh

# Declare global variables and initialize to 0
NESTED_NAME=0
IS_NESTED_RUNNING=0
NESTED_STATUS=0

# Create nested container fedora inside the QM.
# Function to create and start nested container fedora, while executing podman commands from inside the QM container.
# Extract nested container's valuable information and store it inside the global variables for later use.
# Globals:
#  NESTED_NAME: The nested container name in the QM container.
#  NESTED_STATUS: The nested container status in the QM container.
#  IS_NESTED_RUNNING: The nested container is running true or false value.
create_nested() {
        podman exec -it qm bash -c "podman run -d -it --name fedora fedora /bin/bash"
        echo "Nested container got started."
        NESTED_NAME=$(podman exec -it qm bash -c "podman inspect fedora --format "{{.Name}}"")
        echo "Netsted container name is: $NESTED_NAME"
        IS_NESTED_RUNNING=$(podman exec -it qm bash -c "podman inspect --format='{{.State.Running}}' fedora")
        echo "Is nested container $NESTED_NAME is running? $IS_NESTED_RUNNING"
        NESTED_STATUS=$(podman exec -it qm bash -c "podman inspect --format='{{.State.Status}}' fedora")
        echo "Nested container $NESTED_NAME status is: $NESTED_STATUS"
}

# Function to check and verify that nested container fedora was created and is running inside the QM container.
# Globals:
#  NESTED_NAME: The nested container name in the QM container.
#  NESTED_STATUS: The nested container status in the QM container.
#  IS_NESTED_RUNNING: The nested container is running true or false value.
compare_values() {
        local expected_nested_name="fedora"
        local expected_nested_status="running"

        if [ "$NESTED_NAME" == 0 ] || [ "$IS_NESTED_RUNNING" == 0 ] || [ "$NESTED_STATUS" == 0 ]; then
                echo -e "\e[1;31mFAIL:\e[0m One or multiple nested container's values are 0. Ensure the nested container is running on the QM container and the environment configured correctly."
                exit 1
        elif [[ $NESTED_NAME != *"$expected_nested_name"* ]];then
                echo "$NESTED_NAME and $expected_nested_name are equal?"
                echo "FAIL: The $expected_nested_name container had not been created inside the QM container."
                exit 1
        elif [[ $IS_NESTED_RUNNING == false ]];then
                echo "$IS_NESTED_RUNNING and false are the same?"
                echo "FAIL: The nested container is not running inside the QM container."
                exit 1
        elif [[ $NESTED_STATUS != *"$expected_nested_status"*  ]];then
                echo "$NESTED_STATUS and $expected_nested_status are the same?"
                echo "FAIL: The nested container status is not $expected_nested_status inside the QM container."
        fi
        echo "PASS: The nested container $NESTED_NAME is $NESTED_STATUS inside the QM container."
}

# Execute the functions
create_nested
compare_values

exit 0
