# Topics

1. [QM Sub-Packages](#qm-sub-packages)
    - [Key Features of QM Sub-Packages](#key-features-of-qm-sub-packages)
    - [Building QM Sub-Packages](#building-qm-sub-packages)
    - [Installing QM Sub-Packages](#installing-qm-sub-packages)
    - [Removing QM Sub-Packages](#removing-qm-sub-packages)
    - [Creating Your Own Drop-In QM Sub-Package](#creating-your-own-drop-in-qm-sub-package)
    - [QM Sub-Package ROS2](#qm-sub-package-ros2)
    - [QM Sub-Package KVM](#qm-sub-package-kvm)
    - [QM Sub-Package Sound](#qm-sub-package-sound)
    - [QM Sub-Package Video](#qm-sub-package-video)

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
- Just dnf install/remove from the traditional rpm schema.

### Customizability

- Users can easily add specific configurations to enhance or modify the behavior of their QM containers.

### Maintainability

- Sub-packages ensure that the base qm package remains untouched, allowing easy updates without breaking custom configurations.

### Simplicity

- Like qm-dropin provide a clear directory structure and templates to guide users in customizing their QM environment.

## Building QM sub-packages

Choose one of the following sub-packages and build using make.

```bash
git clone git@github.com:containers/qm.git && cd qm

Example of subpackages: input, kvm, sound, tty7, ttyUSB0, video, windowmanager

make TARGETS=input subpackages
ls rpmbuild/RPMS/noarch/
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

## QM sub-package Video

The video sub-package exposes `/dev/video0` (or many video devices required) to the container. This feature is useful for demonstrating how to share a camera from the host system into a container using Podman drop-in. To showcase this functionality, we provide the following demo:

### Building the video sub-package, installing, and restarting QM

```bash
make TARGETS=video subpackages

sudo podman restart qm
sudo dnf install ./rpmbuild/RPMS/noarch/qm_mount_bind_video-0.6.7-1.fc40.noarch.rpm
```

This simulates a rear camera when the user shifts into reverse gear.

In this simulation, we created a systemd service that, every time it is started, captures a snapshot from the webcam, simulating the action of a rear camera. (Feel free to start and restart the service multiple times!)

```bash
host> sudo podman exec -it qm bash

bash-5.2# systemctl daemon-reload
bash-5.2# systemctl start rear-camera

# ls -la /tmp/screenshot.jpg
-rw-r--r--. 1 root root 516687 Oct 13 04:05 /tmp/screenshot.jpg
bash-5.2#
```

### Copy the screenshot to the host and view it

```bash
host> sudo podman cp qm:/tmp/screenshot.jpg .
```

Great job! Now imagine all the possibilities this opens up!

## QM sub-package Sound

### Step 1: Install the QM Mount Bind Sound Package

To set up sound cards in a QM environment using Podman, follow the steps below:
Run the following commands to install the `qm_mount_bind_sound` package and restart QM (if previously in use):

```bash
# Build and install the RPM for QM sound
git clone https://github.com/containers/qm.git && cd qm
make TARGETS=sound subpackages
sudo dnf install -y rpmbuild/RPMS/noarch/qm_mount_bind_sound-0.6.7-1.fc40.noarch.rpm

# Restart QM container (if already running)
sudo podman restart qm
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
bash-# podman ps
CONTAINER ID  IMAGE                           COMMAND         CREATED      STATUS      PORTS       NAMES
76dacaa9a89e  quay.io/qm-images/audio:latest  sleep infinity  7 hours ago  Up 7 hours              systemd-audio


bash-# podman exec -it systemd-audio bash

Execute the audio test within the nested container, and the sound will be output through the physical speakers of your computer—or, in this case, the car's multimedia soundbox.
bash-# speaker-test -D hw:1,0 -c 2 -r 48000
```

Params:

```bash
hw:1,0: sound card 1, device 0
-c 2: two channels (stereo)
-r 48000: sample rate of 48 kHz
```

## Creating your own drop-in QM sub-package

We recommend using the existing drop-in files as a guide and adapting them to your specific needs. However, here are the step-by-step instructions:

Please refer [Creating your own drop-in QM sub-package](docs/devel/README.md#creating-your-own-dropin-qm-subpackage)

## QM sub-package ROS2

The QM sub-package ROS2 (a.k.a "The Robot Operating System" or middleware for robots) is widely used by open-source projects, enterprises, companies, edge env and government agencies, including NASA, to advance robotics and autonomous systems. Enabled by Quadlet in QM, ROS2 on top of QM provides a secure environment where robots can operate and communicate safely, benefiting from QM's "Freedom from Interference" frequently tested layer. This ensures robots can function without external interference, enhancing their reliability and security.

The types of robots compatible with this environment are extensive, ranging from medical devices and aerial drones to aqua drones and space rockets. ROS2 within QM supports high availability, meaning these robotic systems can maintain continuous operations, crucial for mission-critical and industrial applications. This versatility makes it ideal for environments that demand robust communication and operational safety, from healthcare and aerospace to underwater exploration and autonomous land vehicles.

How to test this env?

```bash
git clone https://github.com/containers/qm.git && cd qm
make TARGETS=ros2_rolling subpackages
sudo dnf install rpmbuild/RPMS/noarch/qm_ros2_rolling-0.6.7-1.fc40.noarch.rpm  -y
sudo podman restart qm  # if you have qm already running

Testing using talked and listener examples
$host> sudo podman exec -it qm bash
QM> ros2 run demo_nodes_cpp talker &
QM> ros2 run demo_nodes_cpp listener
```

## QM sub-package KVM

The QM sub-package KVM includes drop-in configuration that enables the integration of Kernel-based Virtual Machine (KVM) management into the QM (Quality Management) container environment. This configuration allows users to easily configure and manage KVM virtual machines within the QM system, streamlining virtualization tasks in containerized setups.

Below example step by step:

Step 1:  clone QM repo, install libvirt packages, prepare some files inside QM and start the libvirt daemon.

```bash
git clone https://github.com/containers/qm.git && cd qm
make TARGETS=kvm subpackages
sudo dnf install rpmbuild/RPMS/noarch/qm_mount_bind_kvm-0.6.7-1.fc40.noarch.rpm
sudo podman restart qm  # if you have qm already running
sudo dnf --installroot /usr/lib/qm/rootfs/ install virt-install libvirt-daemon libvirt-daemon-qemu libvirt-daemon-kvm -y
sudo restorecon -R -v /usr/lib/qm

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
