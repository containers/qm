# Topics

1. [QM is a containerized environment for running Functional Safety QM (Quality Management) software](#qm-is-a-containerized-environment-for-running-functional-safety-qm-quality-management-software)
2. [SELinux Policy](#selinux-policy)
3. [BlueChi](#bluechi)
4. [RPM Building Dependencies](#rpm-building-dependencies)
5. [How the OOM Score Adjustment is Used in QM](#how-the-oom-score-adjustment-is-used-in-qm)
    - [Why Use oom score adj in QM?](#why-use-oomscoreadj-in-qm)
    - [OOM Score Adjustment in QM](#oom-score-adjustment-in-qm)
    - [Nested Containers](#nested-containers)
    - [QM Process](#qm-process)
    - [ASIL Applications](#asil-applications)
    - [Highlights](#highlights)
    - [ASCII Diagram](#ascii-diagram)
6. [Examples](#examples)
7. [Development](#development)
8. [Network Settings](https://github.com/containers/qm/blob/main/docs/tutorials/NETWORK.md)
9. [Realtime](#realtime)
10. [Talks and Videos](#talks-and-videos)
    - [Paving the Way for Uninterrupted Car Operations - DevConf Boston 2024](https://www.youtube.com/watch?v=jTrLqpw7E6Q)
    - [Security - Sample Risk Analysis according to ISO26262](https://www.youtube.com/watch?v=jTrLqpw7E6Q&t=1268s)
    - [ASIL and QM - Simulation and Service Monitoring using bluechi and podman](https://www.youtube.com/watch?v=jTrLqpw7E6Q&t=1680s)
    - [Containers in a Car - DevConf.CZ 2023](https://www.youtube.com/watch?v=FPxka5uDA_4)
11. [RPM Mirrors](#rpm-mirrors)
12. [Changing QM Configuration](#changing-qm-configuration)

## QM is a containerized environment for running Functional Safety QM (Quality Management) software

The main purpose of this package is to allow users to set up an environment which
prevents applications and container tools from interfering with other processes
on the system. For example ASIL (Automotive Safety Integrity Level) environments.

The QM environment uses containerization tools like cgroups, namespaces, and
security isolation to prevent accidental interference by processes in the qm.

The QM will run its own version of systemd and Podman to isolate not only the
applications and containers launched by systemd and Podman but systemd and
Podman commands themselves.

This package requires the Podman package to establish the containerized
environment and uses quadlet to set it up.

Software install into the qm environment under /usr/lib/qm/rootfs will
be automatically isolated from the host. But if developers want to further
isolate these processes from other processes in the QM they can use container
tools like Podman to further isolate.

## SELinux Policy

This policy is used to isolate Quality Management parts of the operating system
from the other Domain-Specific Functional Safety Levels (ASIL).

The main purpose of this policy is to prevent applications and container tools
with interfering with other processes on the system. The QM needs to support
further isolate containers run within the qm from the qm_t process and from
each other.

For now all of the control processes in the qm other then containers will run
with the same qm_t type.

Still would like to discuss about a specific selinux prevision?
Please open an [QM issue](https://github.com/containers/qm/issues) with the output of selinux error from a recent operation related to QM. The output of the following commands are appreciated for understanding the root cause.

```console
ausearch -m avc -ts recent | audit2why
journalctl -t setroubleshoot
sealert -a /var/log/audit/audit.log
```

## Bluechi

- [BlueChi](https://github.com/containers/qm/pull/57)

The package configures the bluechi agent within the QM.

BlueChi is a systemd service controller intended for multi-node environments with
a predefined number of nodes and with a focus on highly regulated ecosystems such
as those requiring functional safety. Potential use cases can be found in domains
such as transportation, where services need to be controlled across different
edge devices and where traditional orchestration tools are not compliant with
regulatory requirements.

Systems with QM installed will have two systemd's running on them. The QM bluechi-agent
is based on the hosts /etc/bluechi/agent.conf file. By default any changes to the
systems agent.conf file are reflected into the QM /etc/bluechi/agent.conf. You can
further customize the QM bluechi agent by adding content to the
/usr/lib/qm/rootfs/etc/bluechi/agent.conf.d/ directory.

```console
# dnf install -y python3-dnf-plugins-core
# dnf config-manager --set-enabled crb
```

## RPM building dependencies

In order to build qm package on CentOS Stream 9 you'll need Code Ready Builder
repository enabled in order to provide `golang-github-cpuguy83-md2man` package.

## How the OOM Score Adjustment is used in QM

The om_score_adj refers to the "Out of Memory score adjustment" in Linux operating systems. This parameter is used by the Out of Memory (OOM) killer to decide which processes to terminate when the system is critically low on memory.

### Why use oomscoreadj in QM?

By fine-tuning which processes are more likely to be terminated during low memory situations, critical processes can be protected, thereby enhancing the overall stability of the system. For instance only, ASIL (Automotive Safety Integrity Level) applications, which are critical for ensuring functional safety in automotive systems, will be preserved in case of low resources.

### OOM Score Adjustment in QM

#### Nested Containers

- All nested containers created inside QM will have their OOM score adjustment set to *750*.

```console
$ cat /usr/share/qm/containers.conf | grep oom_score_adj
oom_score_adj = 750
```

#### QM Process

- The QM process has a default OOM score adjustment value set to *500*, configured via the *qm.container* file.

```console
cat /usr/share/containers/systemd/qm.container | grep OOMScoreAdjust
# OOMScoreAdjust=500
```

### ASIL Applications

If we consider the example of ASIL (Automotive Safety Integrity Level) applications, which are essential for maintaining functional safety in automotive systems, their OOM score adjustment values can range from -1 to -1000. Setting the value to -1000 makes the process immune to the OOM killer. This ensures that ASIL applications are the last to be terminated by the OOM killer, thus prioritizing their operation even in low memory situations.

#### Highlights

- Nested Containers inside QM: OOM score adjustment set to 750. (/usr/share/qm/containers.conf)
- QM Process: OOM score adjustment value set to 500, configured via the qm.container file.
- ASIL Applications: Can explore a range from -1 to -1000, with -1000 making the process immune to the OOM killer.

#### ASCII Diagram

```txt
+-------------------------------------------------------------+
| The Priority Process of OOM Killer in the QM Context        |
+-------------------------------------------------------------+

------------------------------------ Kernel space -----------------------------------------------

                           +--------------------------------+
                           | Out of Memory Killer Mechanism |
                           |          (OOM Killer)          |
                           +--------------------------------+
                                          |
                                          v
                           +--------------------------------+
                           |       Kernel Scheduler         |
                           +--------------------------------+

------------------------------------ User space -------------------------------------------------

                    +----------------------------------------+
                    |       Out of Memory Score Adjustment   |
                    |            (oom_score_adj)             |
                    +----------------------------------------+
                                    |
                                    |
                                    v (Processes Priority side by side)
      +-----------------------------+--------------------------+-----------------------+
      |                             |                          |                       |
      v                             v                          v                       v
+------------------+  +----------------------------+   +-----------------+     +-----------------+
|                  |  |                            |   |                 |     |                 |
|    QM Container  |  |  Nested Containers by QM   |   |  ASIL Apps      |     | Other Processes |
|                  |  |                            |   |                 |     |                 |
|     OOM Score    |  |         OOM Score          |   |   OOM Score     |     |    OOM Score    |
|        500       |  |            750             |   |   -1 to -1000   |     |    (default: 0) |
+------------------+  +----------------------------+   +-----------------+     +-----------------+
          |                         |                           |                      |
          v                         v                           v                      v
   +----------------+      +----------------+         +--------------------+    +-----------------+
   | Lower priority |      | Higher priority|         | Very low priority  |    | Default priority|
   | for termination|      | for termination|         | for termination    |    | for termination |
   +----------------+      +----------------+         +--------------------+    +-----------------+
                                    |
                                    |
                                    |
                                    v
         +-------------------------------------------------------------+
         |                                                             |
         | In conclusion, all nested containers created inside QM have |
         | their OOM score adjustment set to 750, making them more     |
         | likely to be terminated first compared to the QM process.   |
         |                                                             |
         | When compared to ASIL applications, nested containers       |
         | will have an even higher likelihood of being terminated.    |
         |                                                             |
         | Compared to other processes with the default adjustment     |
         | value of 0, nested containers are still more likely to be   |
         | terminated first, ensuring the system and ASIL Apps are     |
         | kept as safe as possible.                                   |
         |                                                             |
         +-------------------------------------------------------------+

------------------------------------ User space -------------------------------------------------

------------------------------------ Kernel space -----------------------------------------------
```

## Examples

Looking for quadlet examples files? See our [docs dir](docs/quadlet-examples/).

## Development

If your looking for contribute to the project use our [development README guide](docs/devel/README.md) as start point.

## Realtime

To enable real-time removal of sched_* blockage via seccomp, use the following schema.

```bash
cat << EOF >> /etc/containers/systemd/qm.container.d/rt.conf
> [Container]
SeccompProfile=""
> EOF
```

## Talks and Videos

Let's spread the knowledge regarding QM, if you have any interesting video regarding any
technology related to QM please with us.

## RPM Mirrors

Looking for a specific version of QM?
Search in the mirrors list below.

[CentOS Automotive SIG - qm package - noarch](https://mirror.stream.centos.org/SIGs/9-stream/automotive/aarch64/packages-main/Packages/q/)

## Changing QM Configuration

### Overview

To run QM on an immutable OSTree-based OS, we utilize systemd units with Podman Quadlet. Since modifying the original service file is not an option, we must use drop-in files to adjust the default configuration.

For more information on how podman-systemd.unit works, refer to the manual by running:

`man podman-systemd.unit`

### Default Configuration File

The default QM configuration drop-in file is located at:

 /usr/share/containers/systemd/qm.container

To override settings, create new drop-in files (ending in .conf) under the following directory `/etc/containers/systemd/qm.container.d/`. If the directory does not exist, create it first:

 `mkdir -p /etc/containers/systemd/qm.container.d/`

### Modifying the MemoryHigh Variable Example

#### Checking the Current Memory Limit

Please run:

`systemctl show -P MemoryHigh qm`

Expected output:

`infinity`

This indicates that MemoryHigh is currently unlimited and can be viewed in `/usr/share/containers/systemd/qm.container`.

#### Setting a Memory Limit of 2G

To impose a memory usage limit of 2G for QM:

Create a Drop-in Configuration File and the directory

```bash

mkdir -p /etc/containers/systemd/qm.container.d/

vim /etc/containers/systemd/qm.container.d/100-MemoryMax.conf

```

The name that was choosen for the new drop-in file is  `100-MemoryMax.conf` this name can be changed but please keep in mind that the configuration will be build by alphabetic order of the drop-in files.

Edit the File and Add the Following Content:

```bash

[Service]

MemoryHigh=2G

```

(MemoryHigh is specified in gigabytes; e.g., 2G means 2 gigabytes.)

#### Verifying the New Configuration

To preview the updated systemd configuration, run:

`/usr/lib/systemd/system-generators/podman-system-generator {--user} --dryrun`

#### Applying service configuration changes

Reload systemd and restart QM with the following commands:

```bash

systemctl daemon-reload

systemctl restart qm.service

```

This confirms that MemoryHigh is now set to 2G.

#### Final Confirmation

To ensure the 2G limit is enforced, check the value of `MemoryHigh` with the same command that mentioned above:

`systemctl show -P MemoryHigh qm`

Expected output:

`2147483648`

(Memory values are displayed in bytes; 2147483648 bytes = 2G.)

This method ensures that QM's memory usage is controlled without modifying the base system configuration.
