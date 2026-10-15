# SPDX-License-Identifier: GPL-2.0-only

project('qm', version: files('VERSION'), license: 'GPL-2.0-only',
  meson_version: '>=1.2.0', default_options: ['python.bytecompile=-1'])

data_dir = get_option('datadir') / 'qm'
python = import('python').find_installation('python3')
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
install_man('qm_selinux.8')
install_man('tools/qmctl/qmctl.1')

install_data('qm.if', install_dir: get_option('datadir') / 'selinux/devel/include/services')
install_data('qm_contexts', install_dir: data_dir, rename: 'contexts')
install_data('containers.conf', install_dir: data_dir)
install_data('qm.container', install_dir: get_option('datadir') / 'containers/systemd')
install_data('setup', 'userns', 'create-seccomp-rules', 'tools/comment-tz-local',
  'tools/qm-rootfs', 'tools/qm-storage-settings', 'tools/qm-is-ostree',
  install_dir: data_dir, install_mode: 'rwxr-xr-x')
install_data('tools/qmctl/qmctl', install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x')
python.install_sources('tools/qmctl/__init__.py', 'tools/qmctl/qmctl.py',
  subdir: 'qmctl', pure: true)
install_emptydir(get_option('sysconfdir') / 'containers/systemd/qm.container.d')
install_emptydir(get_option('sysconfdir') / 'containers/containers.conf.d')
