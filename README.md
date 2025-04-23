# Topics

- [Topics](#topics)
  - [QM is a containerized environment for running functional safety Quality Management software](#qm-is-a-containerized-environment-for-running-functional-safety-quality-management-software)
  - [SELinux policy](#selinux-policy)
  - [BlueChi](#bluechi)
  - [RPM building dependencies](#rpm-building-dependencies)
  - [How OOM score adjustment is used in QM](#how-oom-score-adjustment-is-used-in-qm)
    - [Priority process of OOM killer in the QM context](#priority-process-of-oom-killer-in-the-qm-context)
  - [Contributing to the QM project](#contributing-to-the-qm-project)
  - [Realtime](#realtime)
  - [Talks and videos](#talks-and-videos)
  - [RPM mirrors](#rpm-mirrors)
  - [Configuring QM](#configuring-qm)
    - [Modifying the `MemoryHigh` variable](#modifying-the-memoryhigh-variable)

## QM is a containerized environment for running functional safety Quality Management software

The main purpose of the Quality Management (QM) environment is to allow users to configure
an environment that prevents applications and container tools from interfering with
other processes on the system, such as in Automotive Safety Integrity Level (ASIL)
processes and applications.

The QM environment uses containerization tools, such as cgroups, namespaces, and
security isolation, to prevent accidental interference by processes in the QM.

The QM runs its own version of systemd and Podman to isolate not only the
applications and containers launched by systemd and Podman, but also systemd and
Podman commands themselves.

This package requires the Podman package to establish the containerized
environment and uses Quadlet to set it up. Refer to the [docs directory](docs/quadlet-examples/)
for example Quadlet files.

Software installed in the QM environment under `/usr/lib/qm/rootfs` is
automatically isolated from the host. To further isolate these processes
from other processes in the QM, developers can use container tools, such as Podman.

## SELinux policy

The SELinux policy isolates QM parts of the operating system
from the other domain-specific functional safety levels, such as ASIL.

The main purpose of this policy is to prevent applications and container
tools from interfering with other processes on the system. The QM must
isolate containers from `qm_t` processes as well as from other containers.

For now, all of the control processes in the QM other than containers run
with the same `qm_t` type.

For support with a specific SELinux issue, open a [QM issue](https://github.com/containers/qm/issues)
and include the SELinux error output from a recent QM-related operation.

The following commands yield output that can help determine the root cause of the issue:

```console
ausearch -m avc -ts recent | audit2why
journalctl -t setroubleshoot
sealert -a /var/log/audit/audit.log
```

## BlueChi

- [BlueChi](https://github.com/containers/qm/pull/57)

The package configures the bluechi-agent within the QM.

BlueChi is a systemd service controller intended for use in highly regulated
ecosystems that feature multi-node environments with a predefined number of nodes.
Potential use cases can be found in industries that require functional safety,
such as the transportation industry in which services must be controlled across different
edge devices and where traditional orchestration tools do not comply with
regulatory requirements.

Systems with QM installed have two systemd processes running on them. The QM
bluechi-agent is based on the hosts `/etc/bluechi/agent.conf` file. By default, any
changes to the system's `agent.conf` file are reflected in the QM `/etc/bluechi/agent.conf` file.
You can further customize the QM bluechi-agent by adding content to the
`/usr/lib/qm/rootfs/etc/bluechi/agent.conf.d/` directory.

```console
# dnf install -y python3-dnf-plugins-core
# dnf config-manager --set-enabled crb
```

## RPM building dependencies

To build QM packages on CentOS Stream 9, enable the Code Ready Builder
repository for access to the `golang-github-cpuguy83-md2man` package.

## How OOM score adjustment is used in QM

The `oom_score_adj` parameter refers to the Out-of-Memory score adjustment in Linux operating systems.
The Out-of-Memory (OOM) killer uses the `oom_score_adj` parameter to decide which processes to terminate
when the system is critically low on memory.

By fine-tuning which processes are more likely to be terminated during low-memory situations,
critical processes can be protected, which enhances the overall stability of the system.

- For example, ASIL applications are essential to maintaining functional safety in automotive systems.
You can set their OOM score adjustment value from *-1* to *-1000*. To prioritize their operation
even in low-memory situations, setting the value to *-1000* makes the process immune to the OOM killer
and ensures that ASIL applications are the last to be terminated.

- The QM process has a default OOM score adjustment value set to *500*, configured via the `qm.container` file.

```console
cat /usr/share/containers/systemd/qm.container | grep OOMScoreAdjust
# OOMScoreAdjust=500
```

- All nested containers created inside the QM have a default OOM score adjustment of *750*.

```console
$ cat /usr/share/qm/containers.conf | grep oom_score_adj
oom_score_adj = 750
```

### Priority process of OOM killer in the QM context

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
         | terminated first, ensuring the system and ASIL apps are     |
         | kept as safe as possible.                                   |
         |                                                             |
         +-------------------------------------------------------------+

------------------------------------ User space -------------------------------------------------

------------------------------------ Kernel space -----------------------------------------------
```

## Contributing to the QM project

For information about how to contribute to the QM project, see the [Developers documentation README](docs/devel/README.md).

## Realtime

To enable real-time removal of sched_* blockage via seccomp, use the following schema:

```bash
cat << EOF >> /etc/containers/systemd/qm.container.d/rt.conf
> [Container]
SeccompProfile=""
> EOF
```

## Talks and videos

Let's spread the knowledge regarding QM. If you have interesting content pertaining to
QM-related technology, please share it with us.

## RPM mirrors

Looking for a specific version of QM? Search the [CentOS Automotive SIG Stream Mirror](https://mirror.stream.centos.org/SIGs/9-stream/automotive/aarch64/packages-main/Packages/q/).

## Configuring QM

To run QM on an immutable OSTree-based OS, we use systemd units with Podman Quadlet.
For more information on how `podman-systemd.unit` works, refer to the manual:

`man podman-systemd.unit`

The default QM configuration drop-in file is located in `/usr/share/containers/systemd/qm.container`.
Modifying the original service file is not an option. Instead, create drop-in files to
modify the default configuration.

**NOTE:** The configuration is built in alphabetical order of the drop-in files.

### Modifying the `MemoryHigh` variable

To override the default settings, create a new drop-in `.conf` file in the
`/etc/containers/systemd/qm.container.d/` directory. This method ensures that QM memory
usage is controlled without modifying the base system configuration.

*Procedure*

1. Check the current memory limit:

```bash

systemctl show -P MemoryHigh qm

infinity

```

The command output `infinity` indicates that `MemoryHigh` is unlimited. You can
see this setting in `/usr/share/containers/systemd/qm.container`.

1. Create a directory for the new drop-in file:

```bash

mkdir -p /etc/containers/systemd/qm.container.d/

```

1.  Create a new drop-in file:

```bash

vim /etc/containers/systemd/qm.container.d/100-MemoryMax.conf

```

In this example, the new drop-in file is named `100-MemoryMax.conf`. You can choose a different name,
but be aware that the configuration is built in alphabetical order of the drop-in files.

1. Edit the file to add the following content:

```bash

[Service]

MemoryHigh=2G

```

`MemoryHigh` is specified in gigabytes. 2G means 2 gigabytes.

1. Preview the updated systemd configuration:

```bash

/usr/lib/systemd/system-generators/podman-system-generator {--user} --dryrun

```

1. Reload systemd and restart `qm.service` to apply the configuration changes:

```bash

systemctl daemon-reload

systemctl restart qm.service

```

1. Verify the value of `MemoryHigh`:

```bash

systemctl show -P MemoryHigh qm

2147483648
```

Memory values are displayed in bytes; 2147483648 bytes = 2G, which confirms that `MemoryHigh` is set to 2G.
