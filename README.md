# Topics

- [Topics](#topics)
  - [QM is a containerized environment for running functional safety Quality Management software](#qm-is-a-containerized-environment-for-running-functional-safety-quality-management-software)
  - [QM SELinux policy](#qm-selinux-policy)
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
processes and applications. AutoSD is not a certified safety product. In the context of
AutoSD, QM is not for use in production environments but for research and learning purposes only.

The QM environment uses containerization tools, such as cgroups, namespaces, and
security isolation, to prevent accidental interference by processes in the QM.

The QM runs its own version of systemd and Podman to isolate not only the
applications and containers launched by systemd and Podman, but also systemd and
Podman commands themselves.

The native `qm.service` uses `qmc` and crun to start the environment. Podman and
application Quadlets continue to run inside QM. Use `systemctl` to manage QM and
`qmc` to interact with it:

```sh
sudo qmc exec /bin/bash
qmc inspect
qmc inspect --field rootfs
```

See the [command reference](docs/docs/qmc.md) and
[configuration reference](docs/docs/configuration.md) for configuration files,
command options and examples.

Software installed in the QM environment under `/usr/lib/qm/rootfs` is
automatically isolated from the host. To further isolate these processes
from other processes in the QM, developers can use container tools, such as Podman.

## QM SELinux policy

The QM SELinux policy isolates QM parts of the operating system
from the other domain-specific functional safety levels, such as ASIL.

The main purpose of this policy is to prevent applications and container
tools from interfering with other processes on the system. The QM must
isolate containers from `qm_t` processes as well as from other containers.

For now, all of the control processes in the QM other than containers run
with the same `qm_t` type. For more information, refer to `man qm_selinux`.

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

Systems with QM installed have two systemd processes running on them. Setup
creates the QM BlueChi agent configuration from the host configuration, with a
`qm.` prefix on the node name. Customize the agent through
`/etc/qm/bluechi/agent.conf.d/` on the host, or the configured writable etc tree.

```console
# dnf install -y python3-dnf-plugins-core
# dnf config-manager --set-enabled crb
```

## RPM building dependencies

To build QM packages on CentOS Stream 10, enable the Code Ready Builder
repository for access to the `golang-github-cpuguy83-md2man` package.

## How OOM score adjustment is used in QM

The Linux host kernel controls ASIL and QM processes. The Out-of-Memory (OOM) Killer is part of the Linux
kernel's memory management subsystem. OOM Killer terminates processes to release RAM in memory-constrained conditions.
The `oom_score_adj` parameter refers to the Out-of-Memory score adjustment in Linux operating systems.
The OOM Killer uses the `oom_score_adj` parameter to decide which processes to terminate when the system is
critically low on memory.

By fine-tuning which processes are more likely to be terminated during low-memory situations,
critical processes can be protected, which enhances the overall stability of the system.

- For example, ASIL applications are essential to maintaining functional safety in automotive systems.
You can set their OOM score adjustment value from *-1* to *-1000*. To prioritize their operation
even in low-memory situations, setting the value to *-1000* makes the process immune to the OOM killer
and ensures that ASIL applications are the last to be terminated.

- The QM process has a default OOM score adjustment value set to *500*, configured via the `qm.service` file.

```console
systemctl show qm.service -p OOMScoreAdjust
OOMScoreAdjust=500
```

- All nested containers created inside the QM have a default OOM score adjustment of *750*.

```console
$ cat /usr/share/qm/containers.conf | grep oom_score_adj
oom_score_adj = 750
```

### Adjusting OOM Score for Nested Containers

You can customize the OOM score adjustment for nested containers running inside QM. This requires both nested container configurations and QM capability adjustments.

**Important Note:** To customize OOM scores for QM nested containers, you need to add the `SYS_RESOURCE` capability. The default QM configuration drops `SYS_RESOURCE` capability for security reasons. While adding this capability is not recommended, if it's absolutely necessary, the steps below demonstrate how to modify the default QM container definition.

#### Step 1: Create Nested Container Configurations

Create nested container configurations in `/etc/qm/containers/systemd/`:

**Create:** `/etc/qm/containers/systemd/nested.container`

```ini
[Container]
ContainerName=nested
Image=alpine:latest
Exec=sleep 1d
Network=none

[Service]
OOMScoreAdjust=1000
```

**Create:** `/etc/qm/containers/systemd/nested2.container`

```ini
[Container]
ContainerName=nested2
Image=alpine:latest
Exec=sleep 1d
Network=none

[Service]
OOMScoreAdjust=100
```

#### Step 2: Modify QM Capabilities (Required but Not Recommended)

Create a QM drop-in file to override the default capability restrictions. This adds back the `SYS_RESOURCE` capability that QM drops by default:

**Create:** `/etc/qmc.conf.d/100-capabilities.conf`

```json
{"capabilities": [{"name": "CAP_SYS_RESOURCE"}]}
```

#### Step 3: Verify and Apply the Configuration

1. **Check the merged container configuration:**

   ```bash
   qmc inspect --field capabilities
   ```

2. **Apply the changes:**

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart qm
   ```

3. **Test the nested containers inside QM:**

   ```bash
   # Enter the QM container
   sudo qmc exec /bin/bash

   # Start first nested container and check its OOM score
   systemctl start nested
   PID=$(podman inspect -f '{{.State.Pid}}' nested)
   cat /proc/$PID/oom_score_adj
   # Should output: 1000

   # Start second nested container and check its OOM score
   systemctl start nested2
   PID=$(podman inspect -f '{{.State.Pid}}' nested2)
   cat /proc/$PID/oom_score_adj
   # Should output: 100
   ```

This allows fine-grained control over OOM killer priority for different nested containers based on their importance.

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

For information about how to contribute to the QM project, see the [Developers documentation README](docs/devel/README.developer.md).

## Realtime

To enable real-time removal of sched_* blockage via seccomp, use the following schema:

```bash
mkdir -p /etc/qmc.conf.d
cat > /etc/qmc.conf.d/50-realtime.conf <<'EOF'
{"seccomp": "/usr/share/containers/seccomp.json"}
EOF
systemctl restart qm.service
```

This uses the standard containers seccomp profile in place of QM's additional
realtime scheduling restrictions.

## Talks and videos

Let's spread the knowledge regarding QM. If you have interesting content pertaining to
QM-related technology, please share it with us.

## RPM mirrors

Looking for a specific version of QM? Search the [CentOS Automotive SIG Stream Mirror](https://mirror.stream.centos.org/SIGs/10-stream/automotive/aarch64/packages-main/Packages/q/). The packages in CentOS Automotive SIG Stream Mirror are for experimentation only.

## Configuring QM

QM runs through the native `qm.service`, including on immutable OSTree-based
systems. Container settings belong in JSON files under `/etc/qmc.conf.d/`.
Systemd resource limits and service ordering belong in
`/etc/systemd/system/qm.service.d/`. Keep vendor files unchanged.

See [configuration](docs/docs/configuration.md) for precedence and examples,
and [migration](docs/docs/migration.md) when upgrading from the outer Quadlet.

### Modifying the `MemoryHigh` variable

To override the default settings, create a new drop-in `.conf` file in the
`/etc/systemd/system/qm.service.d/` directory. This method ensures that QM memory
usage is controlled without modifying the base system configuration.

1. Check the current memory limit:

```bash

systemctl show -P MemoryHigh qm

infinity

```

The command output `infinity` indicates that `MemoryHigh` is unlimited. You can
see this setting in `/usr/lib/systemd/system/qm.service`.

1. Create a directory for the new drop-in file:

```bash

mkdir -p /etc/systemd/system/qm.service.d/

```

1. Create a new drop-in file:

```bash
vim /etc/systemd/system/qm.service.d/100-MemoryHigh.conf
```

In this example, the new drop-in file is named `100-MemoryHigh.conf`. You can choose a different name,
but be aware that the configuration is built in alphabetical order of the drop-in files.

1. Edit the file to add the following content:

```bash

[Service]

MemoryHigh=2G

```

`MemoryHigh` is specified in gigabytes. 2G means 2 gigabytes.

1. Preview the updated systemd configuration:

```bash

systemctl cat qm.service

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
