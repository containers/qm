#

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
Setup then enables and starts a Podman quadlet service qm.service (qm.container).

This Podman quadlet can be examined with the following command:

```console
systemctl status qm.service
● qm.service
     Loaded: loaded (/etc/containers/systemd/qm.container; generated)
    Drop-In: /usr/lib/systemd/system/service.d
             └─10-timeout-abort.conf
     Active: active (running) since Tue 2023-04-11 15:43:45 EDT; 28min ago
   Main PID: 993674 (conmon)
      Tasks: 11 (limit: 76801)
     Memory: 275.1M (swap max: 0B)
        CPU: 4.527s
     CGroup: /qm.service
             ├─libpod-payload-00de006493bc970788d6c830beb494a58a9a2847a5eda200812d3a8b4e214814
             │ ├─init.scope
             │ │ └─993676 /sbin/init
             │ └─system.slice
             │   ├─dbus-broker.service
             │   │ ├─993763 /usr/bin/dbus-broker-launch --scope system --audit
             │   │ └─993764 dbus-broker --log 4 --controller 9 --machine-id 4ce4c21b211d41e78b7b64418c1c0cb5 -->
             │   ├─systemd-journald.service
             │   │ └─993718 /usr/lib/systemd/systemd-journald
...
```

## CGroups and container configuration

The options in the qm.container file overridden by using drop-in files, in the
directories `/etc/containers/systemd/qm.container.d` or`
`/usr/lib/containers/systemd/qm.container.d. This allows overriding for example
CGroup options like Service.CPUWeight, or podman options like Container.Volume.
Such options will affect all the processes running in the qm container.

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

However, please note that this method may not work correctly for all packages, especially those that install files in `/var` or `/etc`.

Recommended Method

To ensure that packages are installed correctly, we recommend using the following script:

```console
#!/bin/bash

DIR=$(mktemp -d)

run_exit_cmds() {
  umount $DIR/var
  umount $DIR/etc
  umount $DIR
  rmdir $DIR
}
trap run_exit_cmds EXIT

mount --bind /usr/lib/qm/rootfs $DIR
mount --bind /var/qm $DIR/var
mount --bind /etc/qm $DIR/etc

dnf install --installroot=$DIR "$@"
```

This script creates a temporary environment that mirrors the QM environment, and installs the package using dnf. The package is installed to the temporary directory, which is then unmounted and deleted when the script exits.

Usage

To use this script, save it to a file (e.g. install_package.sh), make the file executable with `chmod +x install_package.sh`, and then run it with the package name as an argument:

```console
./install_package.sh <package_name>
```

This will install the package to the QM environment.

Note: You can modify the script to install multiple packages by separating the package names with spaces.

```console
./install_package.sh package1 package2 package3
```

This will install all three packages to the QM environment.
For example, to install the vim and git packages, you would run:

```console
./install_package.sh vim git
```

This will install both vim and git to the QM environment.

## Entering the QM

To enter the QM environment, use this Podman command to
launch containers within it.

```console
sh-5.2# podman exec -ti qm sh
sh-5.2#
```

The SELinux label can be checked by executing the following:

```console
sh-5.2# id -Z
system_u:system_r:qm_t:s0:c35,c404
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

The configuration of the hosts /etc/bluechi/agent.conf file is copied into the QM every time the
qm.service is started, with the nodename of the hosts agent.conf modified by prepending `qm.`
on the front of the nodename. If the hosts /etc/bluechi/agent.conf does not exists, then the
QM bluechi agent will default to `qm.`$(hostname).

If you want permanently modify the bluechi agent within the QM you can add config to
/usr/lib/qm/rootfs/etc/bluechi/agent.conf.d/ directory or modify the /etc/containers/systemd/qm.container
quadlet file to not execute the bluechi-agent setup script.

## Using systemd drop-in with QM

The systemd drop-in feature allows users to extend or modify the configuration of systemd units without directly editing the unit files provided by the system package.

In this example, we will add the AllowedCPU to set as 1 to qm.service that quadlet generated:

### Create allowedcpus.conf

```console
cat  /etc/systemd/system/qm.service.d/allowedcpus.conf

# Contents of qm.continer.d/allowedcpus.conf
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

**[podman(1)](https://github.com/containers/podman/blob/main/docs/source/markdown/podman.1.md)**,**[quadlet(5)](https://github.com/containers/podman/blob/main/docs/source/markdown/podman-systemd.unit.5.md)**, systemctl(1), systemd(1), dnf(8), [bluechi-agent(1)](https://github.com/containers/bluechi/blob/main/doc/man/bluechi-agent.1.md),[bluechi-agent.conf.5](https://github.com/containers/bluechi/blob/main/doc/man/bluechi-agent.conf.5.md)
