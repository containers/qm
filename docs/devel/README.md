# Developers documentation

## Table of contents

- [Building QM rpm manually with changes](#building-qm-rpm-manually-with-changes)
- [Building CentOS AutoSD and QM manually](#building-centos-autosd-and-qm-manually)
- [Useful Commands](#useful-commands)
  - [Installing software inside QM partition](#installing-software-inside-qm-partition)
  - [Removing software inside QM partition](#removing-software-inside-qm-partition)
  - [Copying files to QM partition](#copying-files-to-qm-partition)
  - [Listing QM service](#listing-qm-service)
  - [List QM container via podman](#list-qm-container-via-podman)
  - [Extend QM quadlet managed by podman](#extend-qm-quadlet-managed-by-podman)
  - [Connecting to QM container via podman](#connecting-to-qm-container-via-podman)
  - [SSH guest CentOS Automotive Stream Distro](#ssh-guest-centos-automotive-stream-distro)
  - [Check if HOST and Container are using different network namespace](#check-if-host-and-container-are-using-different-network-namespace)
  - [Debugging with podman in QM using --root](#debugging-with-podman-in-qm)
  - [Creating your own drop-in QM sub-package](#creating-your-own-dropin-qm-subpackage)
  - [Let automation create/publish PR sub-packages](#let-automation-create-publish-pr-subpackages)
  - [Install PR copr sub-packages on local machine](#install-pr-copr-sub-packages-on-local-machine)
  - [Debugging with quadlet](#debugging-with-quadlet)

## Building QM rpm manually with changes

Building QM locally with changes for tests is a recommended practice,
especially for testing new features before submitting a pull request.

**1.** Prerequisite

```bash
dnf install -y rpm-build golang-github-cpuguy83-md2man selinux-policy-devel
```

**2.** Clone the repo

```bash
git clone https://github.com/containers/qm.git
```

**3.** Build the RPM

Select a QM version that is a higher number from the current one.
For example, if today's QM version is 0.6.2, set it to 1.0 so that
the RPM created is identifiable as yours.

```bash
make clean && VERSION=1.0 make rpm
```

The rpm is created at the `${RPM_TOPDIR}/RPMS` folder, by default
`${PWD}/rpmbuild/RPMS`.
You can export **RPM_TOPDIR** to change the path where the rpm will be placed.
For example:

```bash
VERSION=1.0 RPM_TOPDIR=/USER/rpmbuild make rpm
```

## Building CentOS AutoSD and QM manually

During development, it is common to conduct integration tests to ensure your
changes work well with other components within the overall solution.
In our case, it's best to test against the CentOS Automotive Stream
Distribution (AutoSD) image.

Once you have the new [RPM](#building-qm-rpm-manually-with-changes), follow these steps:

**1.** Make sure the new rpm is located in **/USER/rpmbuild/RPMS/**

Example

```bash
ls /root/rpmbuild/RPMS/noarch/qm-1.0-1.noarch.rpm
/root/rpmbuild/RPMS/noarch/qm-1.0-1.noarch.rpm
```

**2.** Create a local repository with the new package

```bash
dnf install createrepo_c -y
cd /root/rpmbuild/RPMS/
createrepo .
```

**4.** Clone the CentOS Automotive distro for the build

Ensure you meet the requirements for the CentOS Automotive Stream by
referring to [this link](https://sigs.centos.org/automotive/building/).

The following commands will execute:

- Cleanups before a fresh build
- Remove old qcow2 images used (regular and ostree)
- Finally creates a new image (BASED ON target name, ostree or regular)
  NOTE:
  - The path for the new QM rpm file (/root/rpmbuild/RPMS/noarch)
  - extra_rpms - useful for debug (do not use spaces between packages or will break)
  - ssh enabled

```bash
dnf install podman -y && dnf clean all
git clone https://gitlab.com/CentOS/automotive/sample-images.git
git submodule update --init
cd sample-images/
rm -rf _build
rm -f cs9-qemu-qmcontainer-regular.x86_64.qcow2
rm -f cs9-qemu-qmcontainer-ostree.x86_64.qcow2
./build --distro cs9 --target qemu --define 'extra_repos=[{\"id\":\"local\",\"baseurl\":\"file:///root/rpmbuild/RPMS/noarch\"}]' --define 'extra_rpms=[\"qm-1.0\",\"vim-enhanced\",\"strace\",\"dnf\",\"gdb\",\"polkit\",\"rsync\",\"python3\",\"openssh-server\",\"openssh-clients\"]' --define 'ssh_permit_root_login=true' --define 'ssh_permit_password_auth=true' cs9-qemu-qmcontainer-regular.x86_64.qcow2
```

Run the virtual machine, default user: root, pass: password.
To change default values, use the [defaults.ipp.yml](https://gitlab.com/CentOS/automotive/src/automotive-image-builder/-/blob/main/include/defaults.ipp.yml) file.

```bash
./runvm --nographics ./cs9-qemu-qm-minimal-regular.x86_64.qcow2
```

## Useful Commands

### Installing software inside QM partition

```bash
dnf --installroot /usr/lib/qm/rootfs/ install vim -y
```

### Removing software inside QM partition

```bash
dnf --installroot /usr/lib/qm/rootfs/ remove vim -y
```

### Copying files to QM partition

Please note: This process is only applicable for regular images.
OSTree images are read-only, and any files must be included during the build process.

Once this is understood, proceed by executing the following command on the host after
the QM package has been installed.

```bash
#host> cp file_to_be_copied /usr/lib/qm/rootfs/root
#host> podman exec -it qm bash
bash-5.1> ls /root
file_to_be_copied
```

### Listing QM service

```bash
[root@localhost ~]# systemctl status qm -l
● qm.service
     Loaded: loaded (/usr/share/containers/systemd/qm.container; generated)
     Active: active (running) since Sun 2024-04-28 22:12:28 UTC; 12s
ago
   Main PID: 354 (conmon)
      Tasks: 7 (limit: 7772)
     Memory: 82.1M (swap max: 0B)
        CPU: 945ms
     CGroup: /QM.slice/qm.service
             ├─libpod-payload-a83253ae278d7394cb38e975535590d71de90a41157b547040
4abd6311fd8cca
             │ ├─init.scope
             │ │ └─356 /sbin/init
             │ └─system.slice
             │   ├─bluechi-agent.service
             │   │ └─396 /usr/libexec/bluechi-agent
             │   ├─dbus-broker.service
             │   │ ├─399 /usr/bin/dbus-broker-launch --scope system
--audit
             │   │ └─401 dbus-broker --log 4 --controller 9 --machin
e-id a83253ae278d7394cb38e975535590d7 --max-bytes 536870912 --max-fds 4096 --max
-matches 16384 --audit
```

### List QM container via podman

```console
# podman ps
CONTAINER ID  IMAGE       COMMAND     CREATED         STATUS         PORTS       NAMES
a83253ae278d              /sbin/init  38 seconds ago  Up 38 seconds              qm
```

### Extend QM quadlet managed by podman

QM quadlet file is shipped through rpm, refer the following file.
qm.container which is installed to /usr/share/containers/systemd/qm.container
Please refer `man quadlet` for the supported value and how to.

In case a change needed in quadlet file, do not update systemd/qm.container file
As per `man quadlet` do the following:

```console
if ! test -e /etc/containers/systemd/qm.container.d ; then
  mkdir -p  /etc/containers/systemd/qm.container.d
fi
cat > "/etc/containers/systemd/qm.container.d/expose-dev.conf" <<EOF
[Container]
# Expose host device /dev/net/tun
AddDevice=-/dev/net/tun
# In case parameter override needed, add empty value before the required key
Unmask=
Unmask=ALL
EOF
```

To verify the result use the following command:

```console
/usr/lib/systemd/system-generators/podman-system-generator  --dryrun
```

Once the result is satisfied, apply the following

```console
systemctl daemon-reload
systemctl restart qm
systemctl is-active qm
active
```

### Connecting to QM container via podman

```console
# podman exec -it qm bash
bash-5.1#
```

### SSH guest CentOS Automotive Stream Distro

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

### Check if HOST and Container are using different network namespace

#### HOST

```console
[root@localhost ~]# ls -l /proc/self/ns/net
lrwxrwxrwx. 1 root root 0 May  1 04:33 /proc/self/ns/net -> 'net:[4026531840]'
```

#### QM

```console
bash-5.1# ls -l /proc/self/ns/net
lrwxrwxrwx. 1 root root 0 May  1 04:33 /proc/self/ns/net -> 'net:[4026532287]'
```

### Debugging with podman in QM

```console
bash-5.1# podman --root /usr/share/containers/storage pull alpine
Error: creating runtime static files directory "/usr/share/containers/storage/libpod":
mkdir /usr/share/containers/storage: read-only file system
```

### Creating your own dropin QM subpackage

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

### Let automation create publish PR subpackages

subpuckges could be created by Packit and uploaded
by Copr to packit/containers-qm-<PR_ID> repo.
Default macros for each subpackage deactivated by default.

To enable PR repo apply the follwoing

1. Enable subpackage spec macro definition in .packit.sh
Add the following line at the end of file,

```bash
# Update build additional rpms in spec
sed -i 's/\(<spec_file_macro_name> \).*/\11/' ${SPEC_FILE}
```

Check rpms created in PT Actions under PR Checks > Packit-as-a-Service
In case new tests need the sub-package, it will be innstalled immediatly
on Packit-as-a-Service test phase.

### Install PR copr sub-packages on local machine

1. Enbale repo in your machine
This part is done automatically by TestingFarm guest provisioning.
In case of manual installation,

```bash
dnf copr enable packit/containers-qm-<PR_ID> <distro><arch>
```

1. Install rpm in qm
This part is done automatically by TestingFarm guest provisioning.
In case of manual installation,

```bash
podman cp /etc/yum.repos.d/_copr:copr.fedorainfracloud.org:packit:containers-qm-<PR_ID>.repo qm:/etc/yum.repos.d/

dnf  install --releasever=<VERSION_ID> --installroot /usr/lib/qm/rootfs/ <package>
```

### Debugging with quadlet

Imagine a situation where you have a Quadlet container inside QM that isn't starting, and you're unsure why. The best approach is to log into the QM, run the ```quadlet --dryrun``` command, and analyze what's happening. Here's how you can troubleshoot the issue step by step.

```bash
$ sudo podman exec -it qm bash
bash-5.1# cd /etc/containers/systemd/
bash-5.1# ls
ros2-rolling.container

bash-5.1# /usr/libexec/podman/quadlet --dryrun
quadlet-generator[1068]: Loading source unit file /etc/containers/systemd/ros2-rolling.container
quadlet-generator[1068]: converting "ros2-rolling.container": unsupported key 'Command' in group 'Container' in /etc/containers/systemd/ros2-rolling.container
bash-5.1#
```

As you can see above, the error occurs because the Quadlet is attempting to use an unsupported key from the Service section in the Container group. Removing the unsupported key ```Command``` from ```ros2-rolling.container``` and then reloading or restarting the service should resolve the issue.
