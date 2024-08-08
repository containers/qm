#!/bin/bash

# shellcheck disable=SC1091
. ../common/prepare.sh

# Declare global variables and initialize to 0
QM_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE=0
HOST_DEFAULT_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE=0
HOST_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE=0

# Function to execute the sysctl command on the host and save the output
# Globals:
#   HOST_DEFAULT_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE: The default sysctl value set on the host
collect_from_host() {
        HOST_DEFAULT_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE=$(sysctl net.ipv4.tcp_max_syn_backlog | awk '{print $3}')
        echo "Default Host Value: $HOST_DEFAULT_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE"
}

# Function to generate a random number within a specified range
# Arguments:
#   min: The minimum value of the range
#   max: The maximum value of the range
# Returns:
#   A random number within the specified range
generate_random_number() {
    local min=$1
    local max=$2
    echo $((RANDOM % (max - min + 1) + min))
}

# Function to execute the sysctl command inside the QM container using podman exec and save the output
# Globals:
#   QM_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE: The sysctl value set in the QM container
execute_in_qm() {
	local min=128
	local max=1024
	local new_value

	new_value=$(generate_random_number $min $max)
	QM_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE=$(podman exec -it qm bash -c "sysctl -w net.ipv4.tcp_max_syn_backlog=$new_value" | awk '{print $3}')
	echo "QM Value: $QM_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE"
}

# Function to execute the sysctl command on the host and save the output
# Globals:
#   HOST_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE: The sysctl value set on the host
execute_on_host() {
	HOST_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE=$(sysctl net.ipv4.tcp_max_syn_backlog | awk '{print $3}')
	echo "Host Value: $HOST_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE"
}

# Function to compare the two values
# Globals:
#   QM_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE: The sysctl value set in the QM container
#   HOST_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE: The sysctl value exists on the host
compare_values() {
	if [ "$QM_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE" == 0 ] || [ "$HOST_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE" == 0 ] || [ "$HOST_DEFAULT_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE" == 0 ]; then
		echo -e "\e[1;31mFAIL:\e[0m One or multiple tcp_max_syn_backlog values are 0. Ensure the sysctl command executed correctly."
		exit 1
	elif [ "$HOST_DEFAULT_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE" -eq "$HOST_NET_IPV4_TCP_MAX_SYN_BACKLOG_VALUE" ]; then
		echo "PASS: tcp_max_syn_backlog wasn't changed."
	else
		echo -e "\e[1;31mFAIL:\e[0m tcp_max_syn_backlog value have been changed."
		exit 1
	fi
}

# Execute the functions
collect_from_host
execute_in_qm
execute_on_host
compare_values

exit 0
