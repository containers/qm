# SPDX-License-Identifier: GPL-2.0-only

project('qm', 'c', version: files('VERSION'), license: 'GPL-2.0-only',
  meson_version: '>=1.2.0', default_options: ['c_std=gnu17', 'warning_level=3', 'werror=true', 'python.bytecompile=-1'])

data_dir = get_option('datadir') / 'qm'
make = find_program('make')
md2man = find_program('go-md2man')

policy = custom_target('qm-policy',
  input: ['qm.te', 'qm.fc', 'qm.if'],
  output: 'qm.pp.bz2',
  command: [find_program('build-aux/build-policy'), make,
    '@OUTPUT@', '@INPUT@'],
  build_by_default: true,
  install: true, install_dir: get_option('datadir') / 'selinux/packages')

contexts = custom_target('qm-file-contexts', input: 'qm.fc',
  output: 'file_contexts',
  command: ['sed', '-e', 's|/usr/lib/qm/rootfs||', '-e', 's/gen_context(//g',
    '-e', 's/,s0)/:s0/g', '-e', 's|/usr/lib/qm||g', '@INPUT@'],
  capture: true, build_by_default: true,
  install: true, install_dir: data_dir, install_tag: 'runtime')
qm_man = custom_target('qm-man', input: 'qm.8.md', output: 'qm.8',
  command: [md2man, '--in', '@INPUT@', '--out', '@OUTPUT@'],
  build_by_default: true, install: true,
  install_dir: get_option('mandir') / 'man8')
foreach page : [['qmc', '1', 'qmc'], ['qmc.conf', '5', 'configuration']]
  custom_target(page[0] + '-man', input: 'docs/docs/' + page[2] + '.md',
    output: page[0] + '.' + page[1],
    command: [find_program('build-aux/build-man'), md2man, page[0].to_upper(),
      page[1], '@INPUT@', '@OUTPUT@'],
    build_by_default: true, install: true,
    install_dir: get_option('mandir') / ('man' + page[1]))
endforeach
install_man('qm_selinux.8')

install_data('qm.if', install_dir: get_option('datadir') / 'selinux/devel/include/services')
install_data('qm_contexts', install_dir: data_dir, rename: 'contexts')
install_data('containers.conf', install_dir: data_dir)
install_data('setup', 'userns', 'create-seccomp-rules', 'tools/check-config-migration',
  'tools/qm-rootfs', 'tools/qm-storage-settings', 'tools/qm-is-ostree',
  install_dir: data_dir, install_mode: 'rwxr-xr-x')
install_emptydir(get_option('sysconfdir') / 'containers/containers.conf.d')

build_config = configuration_data()
build_config.set_quoted('QM_DATA_DIR', get_option('prefix') / data_dir)
build_config.set_quoted('QM_CONFIG_DIR', get_option('prefix') / get_option('sysconfdir'))
configure_file(output: 'config.h', configuration: build_config)
subdir('src')
subdir('data')
subdir('systemd')

if get_option('tests')
  python = import('python').find_installation('python3')
  subdir('tests/qmc')
endif
