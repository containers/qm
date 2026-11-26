# SPDX-License-Identifier: GPL-2.0-only
foreach unit : ['qm.service', 'qm-resolv-conf.path', 'qm-resolv-conf.service',
                'qm-signal@.service', 'qm-network-integration.service']
  configure_file(input: unit + '.in', output: unit,
    configuration: service_config, install_dir: unit_dir)
endforeach
install_data('00-qm-forwarding.conf', '90-qm-launch.conf', install_dir: sysctl_dir)
