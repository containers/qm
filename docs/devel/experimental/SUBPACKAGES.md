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
sudo systemctl daemon-reload
sudo podman restart qm
```

## Removing QM sub-packages

```bash
sudo rpm -e qm_mount_bind_input
```

## QM Sub-Package Input

The `input` sub-package exposes `/dev/input/*` devices (such as keyboards, mice, touchpads, etc.) from the host system to the QM container.

Follow the steps below to verify that the input sub-package properly mounts and exposes input devices inside the QM container.

### Step 1: Verify input devices are NOT visible inside QM

```bash
host> sudo podman exec -it qm ls /dev/input
ls: cannot access '/dev/input': No such file or directory
```

### Step 2: Build and install the input sub-package

```bash
host> make TARGETS=input subpackages
host> sudo dnf install ./rpmbuild/RPMS/noarch/qm_mount_bind_input-0.7.4-1.fc41.noarch.rpm
```

### Step 3: Confirm input devices exist on the host

```bash
host> ls /dev/input
by-id    event0  event2  event4  js0   mouse0  mouse2
by-path  event1  event3  event5  mice  mouse1
```

### Step 4: Restart QM to apply the mount bind configuration

```bash
host> sudo systemctl daemon-reload
host> sudo podman restart qm
```

### Step 5: Re-check input devices inside QM

```bash
host> sudo podman exec -it qm ls /dev/input
event0  event2  event4  js0   mouse0  mouse2
event1  event3  event5  mice  mouse1
```

## QM sub-package Video

The video sub-package exposes `/dev/video0` (or many video devices required) to the container. This feature is useful for demonstrating how to share a camera from the host system into a container using Podman drop-in. To showcase this functionality, we provide the following demo:

### Building the video sub-package, installing, and restarting QM

```bash
make TARGETS=video subpackages
sudo dnf install ./rpmbuild/RPMS/noarch/qm-mount-bind-video-0.6.7-1.fc40.noarch.rpm
sudo systemctl daemon-reload
sudo podman restart qm
```

This simulates a rear camera when the user shifts into reverse gear.

In this simulation, we created a systemd service that, every time it is started, captures a snapshot from the webcam, simulating the action of a rear camera. (Feel free to start and restart the service multiple times!)

```bash
host> sudo podman exec -it qm bash

bash-5.2# systemctl daemon-reload
bash-5.2# systemctl start rear-camera

# ls -la /var/tmp/screenshot.jpg
-rw-r--r--. 1 root root 516687 Oct 13 04:05 /var/tmp/screenshot.jpg
bash-5.2#
```

### Copy the screenshot to the host and view it

```bash
host> sudo podman cp qm:/var/tmp/screenshot.jpg .
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
sudo systemctl daemon-reload
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

Please refer [Creating your own drop-in QM sub-package](/docs/devel/README.md#creating-your-own-dropin-qm-subpackage)

## QM sub-package ROS2

The QM sub-package ROS2 (a.k.a "The Robot Operating System" or middleware for robots) is widely used by open-source projects, enterprises, companies, edge env and government agencies, including NASA, to advance robotics and autonomous systems. Enabled by Quadlet in QM, ROS2 on top of QM provides a secure environment where robots can operate and communicate safely, benefiting from QM's "Freedom from Interference" frequently tested layer. This ensures robots can function without external interference, enhancing their reliability and security.

The types of robots compatible with this environment are extensive, ranging from medical devices and aerial drones to aqua drones and space rockets. ROS2 within QM supports high availability, meaning these robotic systems can maintain continuous operations, crucial for mission-critical and industrial applications. This versatility makes it ideal for environments that demand robust communication and operational safety, from healthcare and aerospace to underwater exploration and autonomous land vehicles.

How to test this env?

```bash
git clone https://github.com/containers/qm.git && cd qm
make TARGETS=ros2_rolling subpackages
sudo dnf install rpmbuild/RPMS/noarch/qm_ros2_rolling-0.6.7-1.fc40.noarch.rpm  -y
sudo systemctl daemon-reload
sudo podman restart qm  # if you have qm already running

Testing using talked and listener examples
$host> sudo podman exec -it qm bash
QM> ros2 run demo_nodes_cpp talker &
QM> ros2 run demo_nodes_cpp listener
```

## QM sub-package KVM

The QM sub-package KVM includes drop-in configuration that enables the integration of Kernel-based Virtual Machine (KVM) management into the QM (Quality Management) container environment.
This configuration allows users to pull containerized kvm from [qm-images-repo](https://quay.io/repository/qm-images/kvm) and run it inside QM

There is also kvm.container which is installed as a service.

Below example step by step:

Step 1:  clone QM repo, create rpm.

```bash
git clone https://github.com/containers/qm.git && cd qm
make TARGETS=kvm subpackages
```

Step 2: copy rpm to running machine

```bash
scp -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null -P 2222 rpmbuild/RPMS/noarch/qm-kvm-0.7.4-1.fc41.noarch.rpm   root@127.0.0.1:/root/
```

Step 3: ssh machine install and verify

```bash
sudo dnf install ./qm-kvm-0.7.4-1.fc41.noarch.rpm
sudo systemctl restart qm  # if you have qm already running
```

Step 4: verify, configuration exist

```bash
ls -ltr /etc/containers/systemd/qm.container.d/
total 12
-rw-r--r--. 1 root root  34 Jan  1  1970 publish-port.conf
-rw-r--r--. 1 root root 139 Jul 21  2023 qm_dropin_mount_bind_kvm.conf

 ls -ltr /etc/qm/containers/systemd/
total 12
-rw-r--r--. 1 root root  91 Jan  1  1970 nginx.container
-rw-r--r--. 1 root root 188 Jul 21  2023 kvm.container

[root@localhost ~]# podman exec  qm systemctl is-active kvm
active

[root@localhost ~]# podman exec -it qm sh
sh-5.1# ssh fedora@localhost -p 2226
[fedora@ibm-p8-kvm-03-guest-02 ~]$ grep ^NAME /etc/os-release
NAME="Fedora Linux"
```

### AutoSD install

Some notes related to installing qm on ostree AutoSD image

1. Check /var/qm size is larger then 1.5G
2. Installing in ostree images with dnf command, requires running rpm-ostree usroverlay

In case using aib schema to build your image, verify adding the following to build command

```bash
--define 'extra_rpms=["audit","dnf","python3-gobject"] qm_varpart_relative_size=0.5'
```
