# qmc regression tests

Run `meson setup build --prefix=/usr`, then `meson test -C build --print-errorlogs`.
The tests use Python unittest and C fixtures. They exercise configuration,
OCI preparation, inspection, command errors, signals and utility failures without
a running QM instance or host network changes. Meson and RPM builds enable them
by default; use `-Dtests=false` for a build without test fixtures.

The `network-policy` test uses the network fixture in private user, mount and
network namespaces to check source validation for host-bound and forwarded
packets, and to ensure QM masquerading leaves unrelated traffic unchanged. It
needs iproute and nftables, and reports a skip if its tools or unprivileged
namespaces are unavailable. It does not need cgroup delegation or a QM rootfs.

Some preparation and exec cases need private mounts or privileges. unittest
reports these cases as skipped when their prerequisites are unavailable. Passing
this suite does not establish installed-service networking or SELinux behavior;
those checks require a disposable integration machine.

## Installed service (disposable CentOS 10 machine)

Install the built QM RPM and prepare its default rootfs first. Keep SELinux
**enforcing**. The test needs Python 3, nftables, rootfs `curl`/`getent`, network
connectivity, and a preloaded local nested image with `/bin/sh` and `sleep`.
For user namespaces, prepare rootfs and writable etc/var ownership on disk to
match the subordinate-ID ranges configured by `/usr/share/qm/userns enable`,
as automotive-image-builder does. The runtime filesystem must support ID mapped
mounts. The test reads the configured etc path, so it can also exercise custom
setup locations.

```sh
python3 tests/qmc/installed-service.py --nested-image localhost/qm-test:latest
```

The test uses the actual `qm.service` and defaults to userns required. To check
userns off, use `--userns-mode off` with a separately prepared unshifted fixture.
It never switches the same storage between modes. It restores its test-owned
configuration, restarts QM and must run on a disposable machine. Each command
has a deadline. Do not register it with `%check`
or run it on a developer's host. Bootc machines can use `bootc usr-overlay` in a
VM snapshot to test RPM installation without changing the original image.

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

The systemd fixture also installs the guest network integration service and
checks that `network-online.target` and the guest readiness notification wait
for the host signal. It uses the generic signal path and target templates for
both `host-network-online` and `network-ready`. The two machine-ID variants
exercise a signal published before startup and one published while guest
startup is blocked.

Packit runs `/plans/qmc-smoke` for pull requests on a disposable CentOS Stream 10
VM. Its `smoke.sh` wrapper builds QMC from source and runs the integration tests
in private namespaces. Missing prerequisites fail the job.

To reproduce that job on a disposable VM, install the dependencies listed in
`smoke.fmf` (with CRB enabled), then run `sudo bash tests/qmc/smoke.sh`.
