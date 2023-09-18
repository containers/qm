#!/bin/bash
# shellcheck disable=SC1091


prepare_test() {

   qm_service_file=$(systemctl show -P  SourcePath qm)

   #create backup file for qm unit file
   qm_service_backup=$(mktemp -d -p /tmp)/qm.service
   cp "${qm_service_file}" "${qm_service_backup}"
   # Remove 'DropCapability=sys_resource' enable nested container in QM
   sed -i 's/DropCapability=sys_resource/#DropCapability=sys_resource/' \
       /etc/containers/systemd/qm.container
   # Keep definition for the test not to survive reboot
   #systemctl set-property --runtime qm ManagedOOMMemoryPressure=kill
}

reload_config() {

   systemctl daemon-reload
   systemctl restart qm

}
