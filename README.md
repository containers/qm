# QM is a containerized environment for running Functional Safety qm (Quality Management) software

1. [QM is a containerized environment for running Functional Safety qm (Quality Management) software](#qm-is-a-containerized-environment-for-running-functional-safety-qm-quality-management-software)
2. [QM Sub Packages](#qm-sub-packages)
    - [Key Features of QM Sub-Packages](#key-features-of-qm-sub-packages)
    - [Building QM sub-packages](#building-qm-sub-packages)
    - [Installing QM sub-packages](Installing-qm-sub-packages)
    - [Removing QM sub-packages](Removing-qm-sub-packages)
    - [Creating your own drop-in QM sub-package](Creating-your-own-drop-in-QM-sub-package)
    - [QM sub-package kvm](QM-sub-package-kvm)
    - [QM sub-package Sound](QM-sub-package-Sound)
3. [SELinux Policy](#selinux-policy)
4. [BlueChi](#bluechi)
5. [RPM building dependencies](#rpm-building-dependencies)
6. [How the OOM Score Adjustment (`om_score_adj`) is used in QM](#how-the-oom-score-adjustment-om_score_adj-is-used-in-qm)
    - [Why use `om_score_adj` in QM?](#why-use-om_score_adj-in-qm)
    - [OOM Score Adjustment in QM](#oom-score-adjustment-in-qm)
    - [Nested Containers](#nested-containers)
    - [QM Process](#qm-process)
    - [ASIL Applications](#asil-applications)
    - [Highlights](#highlights)
    - [ASCII Diagram](#ascii-diagram)
7. [Examples](#examples)
8. [Development](#development)
9. [RPM Mirrors](#rpm-mirrors)

The main purpose of this package is allow users to setup an environment which
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

## QM Sub-packages

The qm project is designed to provide a flexible and modular environment for managing
Quality Management (QM) software in containerized environments. One of the key features
of the qm package is its support for sub-package(s), such as the qm-dropin sub-packages.
These sub-packages are not enabled by default and are optional. However,  allow users
to easily extend or customize their QM environment by adding specific configurations,
tools, or scripts to the containerized QM ecosystem by simple installing or uninstalling
a RPM package into the system.

## Key Features of QM Sub-Packages

### Modularity

- No configuration change, no typo or distribution rebuild/update.
- Just dnf install/remove from the tradicional rpm schema.

### Customizability

- Users can easily add specific configurations to enhance or modify the behavior of their QM containers.

### Maintainability

- Sub-packages ensure that the base qm package remains untouched, allowing easy updates without breaking custom configurations.

### Simplicity

- Like qm-dropin provide a clear directory structure and templates to guide users in customizing their QM environment.

## Building QM sub-packages

Choose one of the following sub-packages and build using make.

```bash
$ git clone git@github.com:containers/qm.git && cd qm
$ make | grep qm_dropin
qm_dropin_img_tempdir            - Creates a QM RPM sub-package qm_dropin_img_tempdir
qm_dropin_mount_bind_tty7        - Creates a QM RPM sub-package to mount bind /dev/tty7 in the nested containers
qm_dropin_mount_bind_input       - Creates a QM RPM sub-package to mount bind input in the nested containers

$ make qm_dropin_mount_bind_input
$ ls rpmbuild/RPMS/noarch/
qm-0.6.7-1.fc40.noarch.rpm  qm_mount_bind_input-0.6.7-1.fc40.noarch.rpm
```

## Installing QM sub-packages

```bash
$ sudo dnf install ./rpmbuild/RPMS/noarch/qm_mount_bind_input-0.6.7-1.fc40.noarch.rpm
<SNIP>
Complete!
```

If QM is already running, restart or reload your QM container environment to apply the new configurations.

```bash
sudo podman restart qm
```

## Removing QM sub-packages

```bash
sudo rpm -e qm_mount_bind_input
```

## QM sub-package Sound

### Step 1: Install the QM Mount Bind Sound Package

To set up sound cards in a QM environment using Podman, follow the steps below:
Run the following commands to install the `qm_mount_bind_sound` package and restart QM (if previously in use):

```bash
# Build and install the RPM for QM sound
git clone https://github.com/containers/qm.git && cd qm
make qm_dropin_mount_bind_sound
sudo dnf install -y rpmbuild/RPMS/noarch/qm_mount_bind_sound-0.6.7-1.fc40.noarch.rpm

# To check if your system is using PulseAudio: pactl info
$ pactl info
Server String: /run/user/1000/pulse/native
Library Protocol Version: 35
Server Protocol Version: 35
Is Local: yes
Client Index: 118
Tile Size: 65472
User Name: douglas
Host Name: fedora
Server Name: PulseAudio (on PipeWire 1.0.8)
Server Version: 15.0.0
Default Sample Specification: float32le 2ch 48000Hz
Default Channel Map: front-left,front-right
Default Sink: alsa_output.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__hw_sofhdadsp__sink
Default Source: alsa_input.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__hw_sofhdadsp_6__source
Cookie: 9108:667a

# Install PuseAudio (pactl) and alsa-utils (aplay) in the QM partition
sudo dnf --installroot /usr/lib/qm/rootfs install pulseaudio-utils alsa-utils -y

# Restart QM container (if already running)
sudo podman restart qm

# Showing /dev/snd data inside QM
sudo podman exec -it qm bash
controlC0  hwC0D0  hwC1D2    pcmC0D7p  pcmC0D9p  pcmC1D0p   pcmC1D3p  pcmC1D5p pcmC1D7c  timer
controlC1  hwC1D0  pcmC0D3p  pcmC0D8p  pcmC1D0c  pcmC1D31p  pcmC1D4p  pcmC1D6c seq
```

### Step 2: Identify Sound Cards

After installing the drop-in and restarting QM, you need to identify which sound card in the Linux system will be used in QM. If you're familiar with your sound card setup feel free to skip this step.

To list the sound cards available on your system (in our case, we will pick the number 1):

```bash
cat /proc/asound/cards
```

**Example Output**:

```bash
 0 [NVidia         ]: HDA-Intel - HDA NVidia
                      HDA NVidia at 0x9e000000 irq 17
 1 [sofhdadsp      ]: sof-hda-dsp - sof-hda-dsp
                      LENOVO-20Y5000QUS-ThinkPadX1ExtremeGen4i
 2 [USB            ]: USB-Audio - USB Audio Device
                      Generic USB Audio at usb-0000:00:14.0-5, full speed
```

### Detecting Channels and Sample Rates

To list the supported number of channels and samples use `pactl` command:

```bash
pactl list sinks | grep -i 48000 | uniq
    Sample Specification: s24-32le 2ch 48000Hz
```

### Verify Sample Rate Support

To show the supported sample rates for a specific sound card codec, you can also inspect the codec details:

```bash
cat /proc/asound/card1/codec#0 | grep -i rates
```

This will output the supported sample rates for the codec associated with `card1`.

### Differentiating Between Cards

Accessing Card 1 (sof-hda-dsp)

```bash
cat /proc/asound/cards | grep -A 1 '^ 1 '
```

Accessing Card 2 (USB Audio Device)

```bash
cat /proc/asound/cards | grep -A 1 '^ 2 '
```

### Step 3: Testing audio inside QM

Inside QM, run the following command:

```bash
podman exec -it qm bash
bash-# speaker-test -D hw:1,0 -c 2 -r 48000
```

This command runs a test with:

```bash
hw:1,0: sound card 1, device 0
-c 2: two channels (stereo)
-r 48000: sample rate of 48 kHz
```

If you want to test different sample rates, change the `-r` parameter to other values (e.g., 44100 for 44.1 kHz or 96000 for 96 kHz) to see which ones are supported by the hardware.

## Creating your own drop-in QM sub-package

We recommend using the existing drop-in files as a guide and adapting them to your specific needs. However, here are the step-by-step instructions:

1) Create a drop-in file in the directory: `etc/qm/containers/containers.conf.d`
2) Add it as a sub-package to `rpm/qm.spec`
3) Test it by running: `make clean && VERSION=YOURVERSIONHERE make rpm`
4) Additionally, test it with and without enabling the sub-package using (by default it should be disabled but there are cases where it will be enabled by default if QM community decide):

Example changing the spec and triggering the build via make (feel free to automate via sed, awk etc):

```bash
# Define the feature flag: 1 to enable, 0 to disable
# By default it's disabled: 0
%define enable_qm_dropin_img_tempdir 1

$ make clean && VERSION=YOURVERSIONHERE make rpm
```

## QM sub-package KVM

The QM sub-package KVM includes drop-in configuration that enables the integration of Kernel-based Virtual Machine (KVM) management into the QM (Quality Management) container environment. This configuration allows users to easily configure and manage KVM virtual machines within the QM system, streamlining virtualization tasks in containerized setups.

Below example step by step:

Step 1:  clone QM repo, install libvirt packages, prepare some files inside QM and start the libvirt daemon.

```bash
$host> git clone https://github.com/containers/qm.git && cd qm
$host> make qm_dropin_mount_bind_kvm
$host> sudo dnf install rpmbuild/RPMS/noarch/qm_mount_bind_kvm-0.6.7-1.fc40.noarch.rpm
$host> sudo podman restart qm  # if you have qm already running
$host> sudo dnf --installroot /usr/lib/qm/rootfs/ install virt-install libvirt-daemon libvirt-daemon-qemu libvirt-daemon-kvm -y

# Copy default network settings to /root dir inside QM (/usr/lib/qm/rootfs/root)
$host> sudo cp /usr/share/libvirt/networks/default.xml /usr/lib/qm/rootfs/root

Step 2: Preparing cloudinit files inside QM (/usr/lib/qm/rootfs/root)

# Cloud-init files
------------------------------
$host> cd /usr/lib/qm/rootfs/root/
$host> cat meta-data
instance-id: fedora-cloud
local-hostname: fedora-vm

# We are setting to user fedora the default password as fedora
$host> cd /usr/lib/qm/rootfs/root/
$host> cat user-data
#cloud-config
password: fedora
chpasswd: { expire: False }
ssh_pwauth: True

# Download the Fedora Cloud image for tests and save it /usr/lib/qm/rootfs/var/lib/libvirt/images/
$ wget -O /usr/lib/qm/rootfs/root/Fedora-Cloud-Base-Generic.qcow2 https://download.fedoraproject.org/pub/fedora/linux/releases/40/Cloud/x86_64/images/Fedora-Cloud-Base-Generic.x86_64-40-1.14.qcow2

# Generate the cloud-init.iso and move it to /usr/lib/qm/rootfs/var/lib/libvirt/images/
$host> cloud-localds cloud-init.iso user-data meta-data
$host> mv cloud-init.iso /usr/lib/qm/rootfs/var/lib/libvirt/images/

# Change permission to qemu:qemu
$host> chown qemu:qemu /usr/lib/qm/rootfs/var/lib/libvirt/*

Step 3: Starting libvirtd and checking if it's active inside QM

##################################################################
# Keep in mind for the next steps:
# Depending on the distro you are running SELinux might complain
# about libvirtd running on QM / udev errors
##################################################################

# Going inside QM
$ sudo podman exec -it qm bash

# Starting libvirtd
bash-5.2# systemctl start libvirt

# Check if it's running:
bash-5.2# systemctl is-active libvirtd
active
```

Step 4: Creating a script inside QM and running the VM

```bash
$host> cd /usr/lib/qm/rootfs/root/
$host> vi run
##### START SCRIPT ############
# Set .cache to /tmp
export XDG_CACHE_HOME=/tmp/.cache

# Remove previous instance
virsh destroy fedora-cloud-vm 2> /dev/null
virsh undefine fedora-cloud-vm 2> /dev/null

# Network
virsh net-define ./default.xml 2> /dev/null
virsh net-start default 2> /dev/null
virsh net-autostart default 2> /dev/null

# Install
virt-install \
--name fedora-cloud-vm \
--memory 20048 \
--vcpus 4 \
--disk path=/var/lib/libvirt/images/Fedora-Cloud-Base-Generic.qcow2,format=qcow2 \
--disk path=/var/lib/libvirt/images/cloud-init.iso,device=cdrom \
--os-variant fedora-unknown \
--network network=default \
--import \
--graphics none \
--console pty,target_type=serial \
--noautoconsole

##### END SCRIPT ############
```

Step 5: Running the script

```bash
qm$ sudo podman exec -it qm bash
bash-5.2# cd /root
bash-5.2# ./run
Domain 'fedora-cloud-vm' destroyed

Domain 'fedora-cloud-vm' has been undefined

Network default marked as autostarted

Starting install...
Creating domain...                                                                                        |    0 B  00:00:00
Domain creation completed.
bash-5.2# virsh list
 Id   Name              State
---------------------------------
 4    fedora-cloud-vm   running

bash-5.2# virsh console fedora-cloud-vm

fedora-vm login: fedora
Password:

Last login: Tue Oct  8 06:01:18 on ttyS0
[fedora@fedora-vm ~]$
```

## RPM building dependencies

In order to build qm package on CentOS Stream 9 you'll need Code Ready Builder
repository enabled in order to provide `golang-github-cpuguy83-md2man` package.

## How the OOM Score Adjustment (`om_score_adj`) is used in QM

The om_score_adj refers to the "Out of Memory score adjustment" in Linux operating systems. This parameter is used by the Out of Memory (OOM) killer to decide which processes to terminate when the system is critically low on memory.

### Why use `om_score_adj` in QM?

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

## RPM Mirrors

Looking for a specific version of QM?
Search in the mirrors list below.

[CentOS Automotive SIG - qm package - noarch](https://mirror.stream.centos.org/SIGs/9-stream/automotive/aarch64/packages-main/Packages/q/)
