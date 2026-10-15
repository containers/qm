# SPDX-License-Identifier: GPL-2.0-only
service_config = configuration_data()
service_config.set('BINDIR', get_option('prefix') / get_option('bindir'))
service_config.set('DATADIR', get_option('prefix') / data_dir)
configure_file(input: 'qmc.conf.in', output: 'qmc.conf',
  configuration: service_config, install_dir: data_dir)
install_data('qm.json', install_dir: data_dir)
install_emptydir(data_dir / 'qmc.conf.d')
install_emptydir(get_option('sysconfdir') / 'qmc.conf.d')
