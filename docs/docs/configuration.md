# QM configuration reference

## Name

qmc.conf - JSON configuration for the QM container

## Files and precedence

QM reads these files in order:

1. `/usr/share/qm/qmc.conf`
2. `/usr/share/qm/qmc.conf.d/*.conf`, sorted by filename
3. `/etc/qmc.conf`
4. `/etc/qmc.conf.d/*.conf`, sorted by filename

Files and directories may be absent. Each file is a JSON object, without comments.
Unknown keys and incorrect types are errors. Keep packaged vendor files unchanged;
put local settings in `/etc/qmc.conf.d/`. Administrator files are read after all
vendor files. Matching filenames are both read, rather than masking a vendor file.

Later scalar values replace earlier ones. Lists accumulate in load order;
`[]` adds no operations and does not clear an earlier list. Use explicit removal
operations where needed. Lexical ordering applies to the whole filename: a file
called `qm-user-namespaces.conf` sorts after files beginning with digits.

For example, `/etc/qmc.conf.d/50-local.conf`:

```json
{"hostname": "my-qm", "verbose": false}
```

Check and apply changes:

```sh
qmc inspect
systemctl restart qm.service
```

`qmc inspect --config /absolute/file.conf` reads only that standalone file,
including built-in scalar defaults. It does not inherit the vendor mounts,
capabilities or seccomp path. Use drop-ins for ordinary customization.

## Settings

| Key | Value and default |
| --- | --- |
| `hostname` | String; `qm` |
| `rootfs` | Absolute rootfs path; vendor default `/usr/lib/qm/rootfs` |
| `ip` | QM IPv4 address; `10.90.0.2` |
| `gateway` | Host-side IPv4 address; `10.90.0.1` |
| `prefix-length` | Integer 1–31; `24` |
| `resolv-conf` | Absolute host resolver file; automatically selected by default |
| `userns` | `"auto"`, `"off"` or `"required"`; `"auto"` |
| `verbose` | Boolean; vendor default `true` |
| `memory-max` | Positive integer bytes, size string such as `"5G"`, or `"infinity"` |
| `mounts` | Ordered bind mount operations |
| `devices` | Ordered device operations |
| `capabilities` | Ordered capability additions and removals |
| `unmask` | Array of exact container paths, or `["ALL"]` |
| `seccomp` | Absolute seccomp JSON path; vendor default `/usr/share/qm/seccomp-no-rt.json` |
| `base-config` | Absolute OCI base JSON path; `/usr/share/qm/qm.json` |

The shipped rootfs is read-only. Writable host defaults are `/etc/qm` for `/etc`,
`/var/qm` for `/var`, and `/var/qm/tmp` for `/var/tmp`. Use setup's `--rootfs`,
`--rwetcfs` and `--rwvarfs` options when preparing different locations; setup
writes matching container settings and service mount dependencies. Moving an
existing installation also requires moving its data while QM is stopped.

The resolver source defaults to the host's upstream systemd-resolved file when
available, otherwise `/etc/resolv.conf`. Supplied service watchers refresh DNS
and `/etc/hosts` inside QM. Custom resolver paths outside the watched locations
need a corresponding systemd path-unit override.

QM supports an isolated IPv4 network with outbound masquerading. IP and gateway
must be distinct usable addresses in the same subnet. Host firewall policy must
permit forwarding for it. Outer host networking and port publishing are not
supported. Application Podman networking inside QM remains available.

## Mounts

```json
{
  "mounts": [
    {"source": "/srv/shared", "destination": "/opt/shared", "options": ["ro", "nosuid", "nodev"]},
    {"destination": "/opt/old-share", "remove": true}
  ]
}
```

Create and label shared source directories appropriately before starting QM.
Mount entries require absolute `source` and `destination` paths. `optional: true`
skips a missing source; other lookup failures remain errors. `options` supplies
mount flags, while qmc always adds recursive bind and private propagation.
Omitted or empty options do not imply read-only access; specify `ro` when needed.

Within the mount list, a later destination replaces an earlier one. Removal
requires only `destination` and `remove: true`. A later addition can restore it.
Place parent mounts before children. The separate `/var/tmp` source does not move
automatically when replacing `/var`; relocate all desired sources explicitly.

## Devices and seats

```json
{
  "devices": [
    {"source": "/dev/kvm", "optional": true},
    {"source": "/dev/video*", "optional": true},
    {"destination": "/dev/fuse", "remove": true}
  ]
}
```

A device source can be a character/block device, a directory searched recursively,
or a glob. Directories ignore ordinary files and symlinks. An optional
`destination` remaps the device or selected subtree; by default source paths are
retained. Glob results are sorted. `optional: true` permits missing devices or
no matches, but does not suppress other errors.

Device nodes inherit source major/minor numbers, modes and IDs with matching
cgroup permissions. Use a mount entry for a device bind mount instead.
Later device operations replace or remove the same container destination.
Mount operations run before device operations, so devices take precedence when
destinations overlap. Empty device lists do not remove vendor devices.

A seat selection uses `{"seat": "seat0", "optional": true}`. It selects udev
seat-tagged devices and device descendants of tagged parents. It does not
perform hotplug or session management. Later entries for the same seat replace
it; `{"seat": "seat0", "remove": true}` cancels it. Seat entries have no source,
destination or options. Selection is evaluated at startup.

The old seat hook additionally exposed common input and render devices regardless
of seat. List those explicitly when required; see the subsystem guide. Optional
KVM and fuse devices are already supplied by the main vendor configuration.

## Capabilities, seccomp and masked paths

Capability entries have a `name` and optional `remove: true`, applied in order.
Names accept the `CAP_` prefix or its omission; `all` selects the known set.
Vendor policy adds all known capabilities, then removes `CAP_SYS_BOOT` and
`CAP_SYS_RESOURCE`. For example, to add the latter back:

```json
{"capabilities": [{"name": "CAP_SYS_RESOURCE"}]}
```

Changes affect capability-dependent seccomp filtering. QM's generated seccomp
profile restricts realtime scheduling. To use the standard containers profile,
set `seccomp` to `/usr/share/containers/seccomp.json`. Omitting the path falls
back to the base configuration's inline filter; the shipped base requires the
vendor-provided profile.

`unmask` removes exact paths from the base's masked and readonly path lists;
`["ALL"]` removes all such entries. It does not alter explicit read-only mounts
or grant additional SELinux permissions.

## User namespaces

`auto` uses the `qm_root` ranges in both `/etc/subuid` and `/etc/subgid` when
present, and uses no user namespace when both are absent. Incomplete or malformed
mappings are errors. `required` fails if mappings are unavailable. `off` disables
automatic detection explicitly.

The `/usr/share/qm/userns enable` helper creates accounts, mappings and a required
mode drop-in; `disable` removes its mappings and writes an off drop-in. Restart
QM after using either command. Use `--qm-root-dir` for a custom prepared rootfs.

Rootfs, writable etc/var and generated runtime mounts must support ID mapped
mounts. On filesystems without that support, startup fails rather than silently
running without the requested isolation. In particular, transient bootc overlays
on the CentOS 10 test kernel do not support these mounts; prepare supported
filesystem locations or use `off` for such a deployment. Ownership is translated
through mounts without recursively changing files on disk. Additional shared
host mounts retain host ownership unless given suitable explicit mapping options.

## Service limits and ordering

Use `/etc/systemd/system/qm.service.d/*.conf` for systemd settings:

```ini
[Service]
MemoryHigh=2G
MemoryMax=3G
CPUWeight=50
```

Then run `systemctl daemon-reload` and restart `qm.service`. Service limits cover
the launcher and all QM processes. The JSON `memory-max` setting instead limits
the payload cgroup beneath the service, including nested workloads. The stricter
applicable limit wins. Configure startup dependencies with systemd `[Unit]`
`Requires=`, `After=` and `RequiresMountsFor=` settings.

## See also

qmc(1), qm(8), systemd.resource-control(5), systemd.unit(5).
