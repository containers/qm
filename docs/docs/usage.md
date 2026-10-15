# Using QM

This section describes how to interact with QM.

## Installing software inside QM partition

```bash
dnf --installroot /usr/lib/qm/rootfs/ install vim -y
```

## Removing software inside QM partition

```bash
dnf --installroot /usr/lib/qm/rootfs/ remove vim -y
```

## Copying files to QM partition

Please note: This process is only applicable for regular images.
OSTree images are read-only, and any files must be included during the build process.

Once this is understood, proceed by executing the following command on the host after
the QM package has been installed.

```bash
#host> cp file_to_be_copied /usr/lib/qm/rootfs/root
#host> qmc exec bash
bash-5.1> ls /root
file_to_be_copied
```

## Managing the QM service

```sh
systemctl status qm.service
systemctl restart qm.service
journalctl -b -u qm.service
qmc exec /bin/bash
qmc inspect
qmc inspect --field rootfs
```

The host starts QM with the native `qm.service`. Manage application services and
Podman containers inside it with `qmc exec`, for example:

```sh
qmc exec systemctl list-units
qmc exec podman ps
```

## Extending QM configuration

Create `/etc/qmc.conf.d/50-devices.conf` to expose an optional host device:

```json
{"devices": [{"source": "/dev/net/tun", "optional": true}]}
```

Check the configuration and restart QM to apply it:

```sh
qmc inspect
systemctl restart qm.service
```

Use `/etc/systemd/system/qm.service.d/*.conf` for service limits and ordering,
then run `systemctl daemon-reload` before restarting QM. See the
[command reference](qmc.md), [configuration reference](configuration.md), and
[migration guide](migration.md).

## Managing CPU usage

Using the steps below, it's possible to manage CPU usage of the `qm.service` by modifying service attributes and utilizing drop-in files.

### Setting the CPUWeight attribute

Modifying the `CPUWeight` attribute affects the priority of the `qm.service`. A higher value prioritizes the service, while a lower value deprioritizes it.

Inspect the current CPUWeight value:

```bash
systemctl show -p CPUWeight qm.service
```

Set the CPUWeight value:

```bash
systemctl set-property qm.service CPUWeight=500
```

### Limiting CPUQuota

It's also possible to limit the percentage of the CPU allocated to the `qm.service` by defining `CPUQuota`. The percentage specifies how much CPU time the unit shall get at maximum, relative to the total CPU time available on one CPU.

Inspect the current `CPUQuota` value via the `CPUQuotaPerSecUSec` property:

```bash
systemctl show -p CPUQuotaPerSecUSec qm.service
```

Set the `CPUQuota` value of `qm.service` on the host using:

```bash
systemctl set-property qm.service CPUQuota=50%
```

Verify the `CPUQuota` drop in file has been created using the command below.

```bash
systemctl show qm.service | grep "DropInPath"
```

Expected output:

```bash
DropInPaths=/usr/lib/systemd/system/service.d/10-timeout-abort.conf /etc/systemd/system.control/qm.service.d/50-CPUQuota.conf
```

To test maxing out CPU usage and then inspect using the `top` command, follow these steps:

- Set the `CPUQuota` value of `qm.service` on the host using:

```bash
systemctl set-property qm.service CPUQuota=50%
```

- Execute this command to stress the CPU for 30 seconds:

```bash
qmc exec timeout 30 dd if=/dev/zero of=/dev/null
```

- Observe the limited CPU consumption from the `qm.service`, as shown in the output of the command below:

```bash
top | head
```

Expected output:

```bash
    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
1213867 root      20   0    2600   1528   1528 R  50.0   0.0   4:15.21 dd
   3471 user      20   0  455124   7568   6492 S   8.3   0.0   1:43.64 ibus-en+
      1 root      20   0   65576  37904  11116 S   0.0   0.1   0:40.00 systemd
```

## Connecting to QM

```console
# qmc exec bash
bash-5.1#
```

## SSH guest CentOS Automotive Stream Distro

Make sure the CentOS Automotive Stream Distro Virtual Machine/Container is running with SSHD enabled
and permits ssh connection from root user.

Add **PermitRootLogin yes** into **sshd_config**

```bash
host> vi /etc/ssh/sshd_config
```

Restart systemctl restart sshd

```bash
host> systemctl restart sshd
```

Find the port the ssh is listening in the VM

```bash
host> netstat -na |more # Locate the port (2222 or 2223, etc)
```

Example connecting from the terminal to the Virtual Machine:

```bash
connect-to-VM-via-SSH> ssh root@127.0.0.1 \
    -p 2222 \
    -oStrictHostKeyChecking=no \
    -oUserKnownHostsFile=/dev/null
```

## Check if HOST and Container are using different network namespace

### HOST

```console
[root@localhost ~]# ls -l /proc/self/ns/net
lrwxrwxrwx. 1 root root 0 May  1 04:33 /proc/self/ns/net -> 'net:[4026531840]'
```

### QM

```console
bash-5.1# ls -l /proc/self/ns/net
lrwxrwxrwx. 1 root root 0 May  1 04:33 /proc/self/ns/net -> 'net:[4026532287]'
```

## Debugging with podman in QM

```console
bash-5.1# podman --root /usr/lib/containers/storage pull alpine
Error: creating runtime static files directory "/usr/lib/containers/storage/libpod":
mkdir /usr/lib/containers/storage: read-only file system
```

## Debugging with quadlet

Imagine a situation where you have a Quadlet container inside QM that isn't starting, and you're unsure why. The best approach is to log into the QM, run the ```quadlet --dryrun``` command, and analyze what's happening. Here's how you can troubleshoot the issue step by step.

```bash
$ sudo qmc exec bash
bash-5.1# cd /etc/containers/systemd/
bash-5.1# ls
ros2.container

bash-5.1# /usr/libexec/podman/quadlet --dryrun
quadlet-generator[1068]: Loading source unit file /etc/containers/systemd/ros2.container
quadlet-generator[1068]: converting "ros2.container": unsupported key 'Command' in group 'Container' in /etc/containers/systemd/ros2.container
bash-5.1#
```

As you can see above, the error occurs because the Quadlet is attempting to use an unsupported key from the Service section in the Container group. Removing the unsupported key ```Command``` from ```ros2.container``` and then reloading or restarting the service should resolve the issue.
