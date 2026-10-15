% QM 8

## NAME

QM - Set up a Containerized environment for running Functional Safety QM (Quality Management) software.

## SYNOPSIS

This package allows users to set up an environment that prevents applications
and container tools from interfering with other processes on the
system.

The QM runs its own version of systemd and Podman to isolate not only the
applications and containers launched by systemd and Podman but also systemd and
Podman themselves. In other words, the systemd and Podman launched within the QM environment cannot affect the systemd or Podman processes running outside of that environment.

Software installed into the QM environment under the /usr/lib/qm/rootfs
directory is automatically isolated from the host. If developers need to
further isolate their applications from other processes in the QM, they should
use container tools like Podman.

## INSTALL

After the QM software package is installed, execute the
/usr/share/qm/setup script to setup and install the /usr/lib/qm/rootfs
with packages to run an isolated environment. The setup script installs the
**selinux-policy-targeted**, **podman**, **systemd**, and **bluechi** packages.
Setup enables and starts the native `qm.service`, using qmc and crun. On image
builds, `--skip-systemctl` prepares files and enablement without contacting a
running service manager. Existing image build pipelines can supply the rootfs.

```sh
/usr/share/qm/setup
systemctl status qm.service
journalctl -b -u qm.service
```

## CGroups and container configuration

Use JSON `/etc/qmc.conf.d/*.conf` files for container settings and systemd
`/etc/systemd/system/qm.service.d/*.conf` files for service limits and ordering.
See qmc.conf(5). Inspect configuration with `qmc inspect`, then restart QM.
Systemd drop-ins also require `systemctl daemon-reload`.

The default rootfs is `/usr/lib/qm/rootfs`, with writable `/etc/qm` and `/var/qm`.
Setup accepts `--rootfs`, `--rwetcfs` and `--rwvarfs` to prepare custom locations.
Package removal preserves these filesystems. To explicitly remove them before
uninstalling, run `/usr/share/qm/setup --remove-qm-rootfs`.

## Install Additional packages in QM

If other packages need to be added into the QM environment, use the `dnf` command
on the host. For example, the following example installs the dnf command into the QM environment:

```console
# dnf install --installroot=/usr/lib/qm/rootfs dnf
Unable to read consumer identity

Last metadata expiration check: 0:33:12 ago on Tue 11 Apr 2023 03:42:09 PM EDT.
Dependencies resolved.
================================================================================================================
 Package                                Architecture       Version                     Repository          Size
================================================================================================================
Installing:
 dnf                                    noarch             4.14.0-2.fc38               fedora             478 k
...
```

## Entering the QM

Use qmc(1) to run a command or enter a shell inside QM.

```console
sh-5.2# qmc exec sh
sh-5.2#
```

The SELinux label can be checked by executing the following:

```console
sh-5.2# id -Z
system_u:system_r:qm_t:s0
```

Notice that the process is running as `qm_t`, indicating that the process is a
confined QM process within the QM environment.

Containers can now be run within the QM environment using Podman.

```console
sh-5.2# podman run --rm ubi9-minimal echo hi
Resolved "ubi9-minimal" as an alias (/etc/containers/registries.conf.d/000-shortnames.conf)
Trying to pull registry.access.redhat.com/ubi9-minimal:latest...
Getting image source signatures
Checking if image destination supports signatures
Copying blob 7bffb309b4e8 done
Copying config 96179718b4 done
Writing manifest to image destination
Storing signatures
hi
```

It is recommended that Podman quadlets are used to run additional containerized
applications within the QM. All applications within the QM environment are
prevented from interfering with applications running outside of the QM
environment.

## Configuring bluechi agent in the QM

Setup derives QM's BlueChi agent configuration from the host configuration,
with the node name prefixed by `qm.`. Customize the agent inside QM through
`/etc/qm/bluechi/agent.conf.d/` on the host (or the configured writable etc tree).

## Using systemd drop-in with QM

The systemd drop-in feature allows users to extend or modify the configuration of systemd units without directly editing the unit files provided by the system package.

In this example, we will add the AllowedCPU to set as 1 for the native qm.service:

### Create allowedcpus.conf

```console
cat  /etc/systemd/system/qm.service.d/allowedcpus.conf

# Contents of qm.service.d/allowedcpus.conf
[Service]
AllowedCPUs=1
```

## Tools

### qm-rootfs

Prints the qm rootfs location previously configured during setup.

### qm-storage-settings

Setup the initial QM configuration for storage using the follow config files and changes:

- `${ROOTFS}/etc/containers/storage.conf`
  - uncomment `additionalimagestores`
  - add `/var/lib/shared` into `additionalimagestores`
  - uncomment and set to `true` the option `transient_store`
- `${ROOTFS}/etc/containers/container.conf`
  - add `[engine]` and `TMPDIR`

## SEE ALSO

qmc(1), qmc.conf(5),

**[podman(1)](https://github.com/containers/podman/blob/main/docs/source/markdown/podman.1.md)**,**[quadlet(5)](https://github.com/containers/podman/blob/main/docs/source/markdown/podman-systemd.unit.5.md)**, systemctl(1), systemd(1), dnf(8), [bluechi-agent(1)](https://github.com/containers/bluechi/blob/main/doc/man/bluechi-agent.1.md),[bluechi-agent.conf.5](https://github.com/containers/bluechi/blob/main/doc/man/bluechi-agent.conf.5.md)
