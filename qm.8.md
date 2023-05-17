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
**selinux-policy-targeted**, **podman**, **systemd**, and **hirte** packages.
Setup then enables and starts a Podman quadlet service qm.service (qm.container).

This Podman quadlet can be examined with the following command:

```
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
     CGroup: /QM.slice/qm.service
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

## CGROUPS QM.slice

Notice that the QM environment is running systemd and other services within the
QM.Slice. This slice can be used to modify the cgroups controls of all of the
processes within the QM environment.

## Install Additional packages in QM

If other packages need to be added into the QM environment, use the `dnf` command
on the host. For example, the following example installs the dnf command into the QM environment:

```
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

To enter the QM environment, use this Podman command to 
launch containers within it.

```
sh-5.2# podman exec -ti qm sh
sh-5.2#
```
The SELinux label can be checked by executing the following:

```
sh-5.2# id -Z
system_u:system_r:qm_t:s0:c35,c404
```

Notice that the process is running as `qm_t`, indicating that the process is a
confined QM process within the QM environment.

Containers can now be run within the QM environment using Podman.

```
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

## Configuring hirte agent in the QM

The configuration of the hosts /etc/hirte/agent.conf file is copied into the QM every time the
qm.service is started, with the nodename of the hosts agent.conf modified by prepending `qm.`
on the front of the nodename. If the hosts /etc/hirte/agent.conf does not exists, then the
QM hirte agent will default to `qm.`$(hostname).

If you want permanently modify the hirte agent within the QM you can add config to
/usr/lib/qm/rootfs/etc/hirte/agent.conf.d/ directory or modify the /etc/containers/systemd/qm.container
quadlet file to not execute the hirte-agent setup script.

## SEE ALSO
**[podman(1)](https://github.com/containers/podman/blob/main/docs/source/markdown/podman.1.md)**,**[quadlet(5)](https://github.com/containers/podman/blob/main/docs/source/markdown/podman-systemd.unit.5.md)**, systemctl(1), systemd(1), dnf(8), [hirte-agent(1)](https://github.com/containers/hirte/blob/main/doc/man/hirte-agent.1.md),[hirte-agent.conf.5](https://github.com/containers/hirte/blob/main/doc/man/hirte-agent.conf.5.md)
