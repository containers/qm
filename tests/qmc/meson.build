# SPDX-License-Identifier: GPL-2.0-only
config_test = executable('test-config',
  ['config.c', '../../src/qm-config.c', '../../src/qm-oci-config.c', '../../src/qm-utils.c'],
  include_directories: qmc_includes,
  dependencies: [dependency('json-c'), dependency('libsystemd', version: '>=254')])
test('config', python, args: [files('config.py'), config_test, get_option('prefix') / data_dir])
executable('test-launch-network', qmc_sources + ['network-nft.c'],
  include_directories: qmc_includes,
  dependencies: qmc_deps,
  link_args: ['-Wl,--wrap=nft_run_cmd_from_buffer', '-Wl,--wrap=mnl_socket_sendto',
    '-Wl,--wrap=sysctl_write'])
executable('test-network', ['network.c', '../../src/qm-network.c', '../../src/qm-utils.c', '../../src/qm-state.c'],
  include_directories: qmc_includes,
  dependencies: qmc_deps)
prepare_launcher = executable('test-prepare',
  qmc_sources + ['prepare-cgroup.c', 'prepare-machine-id.c', 'file-truncate.c'],
  include_directories: qmc_includes,
  dependencies: qmc_deps,
  # Keep LTO from inlining the call that the fixture wraps.
  c_args: ['-fno-lto'],
  link_args: ['-fno-lto', '-Wl,--wrap=get_current_cgroup', '-Wl,--wrap=read_text_file', '-Wl,--wrap=ftruncate64'])
test('prepare', python, args: [files('prepare.py'), prepare_launcher,
  meson.project_source_root(), '/payload'])
test('exec', python, args: [files('exec.py'), qmc])
test('inspect', python, args: [files('inspection.py'), qmc])
test('signals', python, args: [files('signals.py'), qmc])
utils_test = executable('test-utils', ['utils.c', '../../src/qm-utils.c'],
include_directories: qmc_includes,
dependencies: dependency('json-c'),
link_args: ['-Wl,--wrap=open64', '-Wl,--wrap=read', '-Wl,--wrap=__read_chk',
  '-Wl,--wrap=write', '-Wl,--wrap=waitpid', '-Wl,--wrap=fork'])
test('utils', utils_test)

test('setup', python, args: [files('setup.py'), qmc])
test('userns', python, args: [files('../userns/test.py')])

stdio_test = executable('test-exec-stdio', ['exec-stdio.c', '../../src/qm-exec.c', '../../src/qm-utils.c'],
  include_directories: qmc_includes, dependencies: dependency('json-c'))
test('stdio', python, args: [files('stdio.py'), stdio_test])

test('migration', python, args: [files('migration.py')])
