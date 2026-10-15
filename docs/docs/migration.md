# Migrating from the outer Quadlet

The native `qm.service` replaces the outer `qm.container`; `qmc` replaces host
interaction through Podman and qmctl. Podman and application Quadlets inside QM
continue to work. The default rootfs, writable etc and writable var paths remain
`/usr/lib/qm/rootfs`, `/etc/qm` and `/var/qm`.

## Before upgrading

Inventory the old outer `qm.container` and `qm.container.d/*.conf` files under
`/etc/containers/systemd`, `/run/containers/systemd`, `/usr/lib/containers/systemd`
and `/usr/share/containers/systemd`. Back them up outside those directories.
Upgrade subsystem packages along with the main package so their vendor drop-ins
are converted too. Convert local changes, then move the old files aside.

Existing `qm.service.d` systemd overrides keep their meaning. Move `[Unit]` and
`[Service]` settings from old Quadlet drop-ins there. A full local
`/etc/systemd/system/qm.service` must be reviewed and moved aside before upgrading,
so it cannot shadow the new native unit.

| Old setting or command | Native equivalent |
| --- | --- |
| `podman exec qm COMMAND` / `qmctl exec` | `qmc exec COMMAND` |
| `podman inspect qm` | `qmc inspect` for settings; `qmc inspect --oci` for the saved launch configuration |
| Start, stop, restart or status QM | `systemctl ... qm.service` |
| `Rootfs=` | JSON `rootfs` or setup `--rootfs` |
| `Volume=SOURCE:DEST:ro` | JSON `mounts` entry with `source`, `destination`, `options: ["ro"]` |
| `AddDevice=-/dev/kvm` | JSON `devices` entry with `source: "/dev/kvm", optional: true` |
| `AddCapability=` / `DropCapability=` | JSON `capabilities` operations |
| `SeccompProfile=` / `Unmask=` | JSON `seccomp` / `unmask` |
| `SubUIDMap=` / `SubGIDMap=` | `userns enable` and JSON `userns`; the ranges must belong to `qm_root` |
| `[Service] MemoryMax=` / `MemoryHigh=` | Same keys in `qm.service.d`; JSON `memory-max` is the separate payload limit |
| `Environment=ROOTFS=...` / `RWETCFS` / `RWVARFS` | Setup's path options and generated qmc/service drop-ins |

For example, replace an outer `Volume=/srv/shared:/opt/shared:ro` drop-in with
`/etc/qmc.conf.d/50-shared.conf`:

```json
{"mounts": [{"source": "/srv/shared", "destination": "/opt/shared", "options": ["ro"]}]}
```

Retain appropriate source ownership and SELinux labels. Relocating writable var
also requires an explicit `/var/tmp` mount change. See
[configuration](configuration.md) for ordered list behavior and examples.

## Applying the migration

The package stops the old running unit before replacing its files, remembers
activation, reloads systemd, and starts the new unit when the old one was active.
Enablement from the generated old unit is transferred to the native service.
A stopped leftover Podman container is removed only when its label identifies
`qm.service` as the owner. No unrelated host containers are removed.

Leftover outer Quadlet files cause startup to fail with their paths in the
journal, instead of silently discarding their settings. Convert them and move
the originals aside, then run:

```sh
qmc inspect
systemctl daemon-reload
systemctl reset-failed qm.service
systemctl start qm.service
qmc exec systemctl list-units
```

Check the service journal and application behavior after migration. Host firewall
rules must allow the QM subnet. The prepared rootfs and application data are
preserved when uninstalling the new package; explicit removal remains available
through `setup --remove-qm-rootfs` before uninstalling.

## Features without a direct replacement

There is no general Quadlet converter. Outer `Network=host`, port publishing,
arbitrary Podman arguments, and arbitrary outer OCI hook annotations are not
supported. Use the private IPv4 network and supported JSON device/mount/seat
settings. Nested application Quadlets can still use their own Podman features.

qmctl's command structure, copy operations and specialized inspection output are
retired, without a compatibility alias. Use qmc exec streams for regular file
copies, or the configured writable host trees. qmc inspect output has its own
JSON schema. Do not assume scripts consuming Podman/qmctl inspection formats
will continue to work.
