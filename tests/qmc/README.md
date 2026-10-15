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

## Installed service (disposable CentOS 10 machine)

Install the built QM RPM and prepare its default rootfs first. Keep SELinux
**enforcing**. The test needs Python 3, nftables, rootfs `curl`/`getent`, network
connectivity, and a preloaded local nested image with `/bin/sh` and `sleep`.
User namespaces require rootfs and the writable etc/var filesystems to support
ID mapped mounts; transient bootc overlay mounts may not support them. Use
prepared paths on a supporting filesystem for that case. The test reads the
configured etc path, so it can also exercise custom setup locations.
Create subordinate ID mappings with `/usr/share/qm/userns enable` before running:

```sh
python3 tests/qmc/installed-service.py --nested-image localhost/qm-test:latest
```

The test uses the actual `qm.service`, checks userns off and required, and
restores its test-owned configuration. It restarts QM and must run on a
disposable machine. Each command has a deadline. Do not register it with `%check`
or run it on a developer's host. Bootc machines can use `bootc usr-overlay` in a
VM snapshot to test RPM installation without changing the original image.

## Isolated launcher regressions

`smoke.py` and `systemd.py` exercise synthetic roots in delegated private user,
mount, PID and network namespaces. They intentionally remove SELinux labels from
the fixture and are supplementary checks. On a host with unprivileged user
namespaces and user cgroup delegation, run for example:

```sh
systemd-run --user --wait --pipe -p Delegate=yes -p DelegateSubgroup=supervisor -p RuntimeMaxSec=180 \
  env TMPDIR=/var/tmp unshare --user --map-root-user --mount --mount-proc --net --pid --fork \
  python3 tests/qmc/smoke.py build/src/qmc
```

Run `systemd.py` with the same wrapper. It accepts an additional `existing` or
`uninitialized` machine-id fixture argument. These helpers need crun, nftables,
iproute, a C compiler, and a usable private cgroup subtree. They do not establish
installed-unit or SELinux behavior.
