#!/bin/bash
#
# Copyright 2023 The qm Authors
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; If not, see <http://www.gnu.org/licenses/>.
# Capture the start time

START_TIME=$(date +%s)
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Add menu

# shellcheck source=/dev/null
source "${SCRIPT_DIR}"/lib/systemd

# shellcheck source=/dev/null
source "${SCRIPT_DIR}"/lib/utils

# Cleanup
cleanup_node_services

# Create host services
echo
info_message "Preparing HOST services"
info_message "=============================="

srvs_host=("safety" "cruise_control" "tires" "breaks")
create_stub_systemd_srv "" "" "${srvs_host[@]}"

# Run verification for HOST
for service in "${srvs_host[@]}"; do
    bluechictl list-units localrootfs --filter \
    "*${service}*" | grep active
    if_error_exit "HOST ${service} service is not in running state"
done

info_message "${GRN}HOST services are running ${CLR}"

# Create QM services
echo
info_message "Preparing QM services"
info_message "=============================="

srvs_qm=("radio" "store" "stream_audio" "maps")
echo
create_stub_systemd_srv "" "qm" "${srvs_qm[@]}"

# Run verification for QM
for service in "${srvs_qm[@]}"; do
    bluechictl list-units qm.localrootfs --filter \
    "*${service}*" | grep active
    if_error_exit "QM ${service} service is not in running state"
done

info_message "${GRN}QM services are running ${CLR}"

# Capture the end time
END_TIME=$(date +%s)

# Calculate the duration in seconds
DURATION=$((END_TIME - START_TIME))

# Calculate minutes and seconds
DAYS=$((DURATION / 86400))
HOURS=$(( (DURATION % 86400) / 3600 ))
MINUTES=$(( (DURATION % 3600) / 60 ))
SECONDS=$((DURATION % 60))

echo
info_message "${GRN}Running time for this script${CLR}"
info_message "\t- ${DAYS} days, ${HOURS} hours, ${MINUTES} minutes and ${SECONDS} seconds"
