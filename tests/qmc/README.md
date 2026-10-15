# qmc regression tests

Run `meson setup build --prefix=/usr`, then `meson test -C build --print-errorlogs`.
The tests use Python unittest and C fixtures. They exercise configuration,
OCI preparation, inspection, command errors, signals and utility failures without
a running QM instance or host network changes. Meson and RPM builds enable them
by default; use `-Dtests=false` for a build without test fixtures.

Some preparation and exec cases need private mounts or privileges. unittest
reports these cases as skipped when their prerequisites are unavailable. Passing
this suite does not establish that the installed service runs with SELinux or
that networking works; those checks require a disposable integration machine.

## Isolated launcher regressions

`smoke.py` and `systemd.py` exercise synthetic roots in delegated private user,
mount, PID and network namespaces. They intentionally remove SELinux labels from
the fixture and are supplementary checks. On a host with unprivileged user
namespaces and user cgroup delegation, run for example:

```sh
systemd-run --user --wait --pipe -p Delegate=yes -p DelegateSubgroup=supervisor -p RuntimeMaxSec=180 \
  env TMPDIR=/var/tmp unshare --user --map-auto --map-root-user --mount --mount-proc --net --pid --fork \
  python3 tests/qmc/smoke.py build/src/qmc
```

Run `systemd.py` with the same wrapper. It accepts an additional `existing` or
`uninitialized` machine-id fixture argument. These helpers need crun, nftables,
iproute, a C compiler, and a usable private cgroup subtree. They do not establish
installed-unit or SELinux behavior. `--map-auto` needs subordinate-ID ranges for
the invoking user. Without them, omit that option; the pre-shifted filesystem
case is then reported as skipped.
