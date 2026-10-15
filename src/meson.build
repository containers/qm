# SPDX-License-Identifier: GPL-2.0-only
qmc_sources = files('qmc.c', 'qm-utils.c', 'qm-network.c', 'qm-state.c',
  'qm-console.c', 'qm-config.c', 'qm-oci-config.c', 'qm-seccomp.c')
qmc_deps = [dependency('json-c'), dependency('libmnl'), dependency('libnftables'),
  dependency('libsystemd', version: '>=254')]
qmc_includes = include_directories('.', '..')
qmc = executable('qmc', qmc_sources, include_directories: qmc_includes,
  dependencies: qmc_deps, install: true)
