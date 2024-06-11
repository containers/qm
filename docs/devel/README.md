- [Building QM rpm manually with changes](#building-qm-rpm-manually-with-changes)
- [Building CentOS AutoSD and QM manually](#building-centos-autosd-and-qm-manually)
- [Useful Commands](#useful-commands)
  - [Installing software inside QM partition](#installing-software-inside-qm-partition)
  - [Removing software inside QM partition](#removing-software-inside-qm-partition)
  - [Copying files to QM partition](#copying-files-to-qm-partition)
  - [Listing QM service](#Listing-QM-service)
  - [List QM container via podman](#List-QM-container-via-podman)
  - [Connecting to QM container via podman](#Connecting-to-QM-container-via-podman)
  - [SSH guest CentOS Automotive Stream Distro](#SSH-guest-CentOS-Automotive-Stream-Distro)
  - [Check if HOST and Container are using different network namespace](#Check-if-HOST-and-Container-are-using-different-network-namespace)
  - [Debugging with podman in QM using --root](#Debugging-with-podman-in-QM)

# Building QM rpm manually with changes

Building QM locally with changes for tests is a recommended practice,  
especially for testing new features before submitting a pull request.

**1.** Clone the repo

```bash
git clone https://github.com/containers/qm.git
```

**2.** Change the Version macro in the spec file

Set the QM version to a higher number from the current one.  
For example, if today's QM version is 0.6.2, set it to 1.0 so that  
the RPM created is identifiable as yours.

Use the following sed command to change the default Version (0, used for  
automation) to the new version (1.0):

```bash
sed -i 's/Version: 0/Version: 1.0/g' qm.spec
```

**3.** Execute the changes

Make necessary changes using your preferred editor (e.g., vi/emacs).

**4.** Build the RPM

```bash
VERSION=1.0 make rpm
```

The rpm is created at the `${RPM_TOPDIR}/RPMS` folder, by default
`${PWD}/rpmbuild/RPMS`.
You can export **RPM_TOPDIR** to change the path where the rpm will be placed.
For example:

```bash
VERSION=1.0 RPM_TOPDIR=/USER/rpmbuild make rpm
```

# Building CentOS AutoSD and QM manually

During development, it is common to conduct integration tests to ensure your
changes work well with other components within the overall solution.  
In our case, it's best to test against the CentOS Automotive Stream  
Distribution (AutoSD) image.

Once you have the new [RPM](#building-qm-rpm), follow these steps:

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

**3.** Clone the CentOS Automotive distro for the build

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
dnf install podman -y
git clone https://gitlab.com/CentOS/automotive/sample-images.git
cd sample-images/osbuild-manifests/
dnf clean all
rm -rf _build
rm -f cs9-qemu-qmcontainer-regular.x86_64.qcow2
rm -f cs9-qemu-qmcontainer-ostree.x86_64.qcow2
make cs9-qemu-qmcontainer-regular.x86_64.qcow2 'DEFINES=extra_repos=[{"id":"local","baseurl":"file:///root/rpmbuild/RPMS/noarch"}] extra_rpms=["qm-1.0","vim-enhanced","strace","dnf","gdb","polkit","rsync","python3","openssh-server","openssh-clients"] ssh_permit_root_login=true osname="autosd" ssh_permit_password_auth=true'
```

Run the virtual machine, default user: root, pass: password.  
To change default values, use the [defaults.ipp.yml](https://gitlab.com/CentOS/automotive/sample-images/-/blob/main/osbuild-manifests/include/defaults.ipp.ym) file.

```bash
./runvm --nographics ./cs9-qemu-qm-minimal-regular.x86_64.qcow2
```

# Useful Commands

## Installing software inside QM partition

```bash
dnf --installroot /usr/lib/qm/rootfs/ remove vim -y
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
#host> podman exec -it qm bash
bash-5.1> ls /root
file_to_be_copied
```

## Listing QM service

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

## List QM container via podman

```bash
# podman ps
CONTAINER ID  IMAGE       COMMAND     CREATED         STATUS         PORTS       NAMES
a83253ae278d              /sbin/init  38 seconds ago  Up 38 seconds              qm
```

## Connecting to QM container via podman

```bash
# podman exec -it qm bash
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

**HOST**

```bash
[root@localhost ~]# ls -l /proc/self/ns/net
lrwxrwxrwx. 1 root root 0 May  1 04:33 /proc/self/ns/net -> 'net:[4026531840]'
```

**QM**

```bash
bash-5.1# ls -l /proc/self/ns/net
lrwxrwxrwx. 1 root root 0 May  1 04:33 /proc/self/ns/net -> 'net:[4026532287]'
```

## Debugging with podman in QM

```bash
bash-5.1# podman --root /usr/share/containers/storage pull alpine
Error: creating runtime static files directory "/usr/share/containers/storage/libpod":  
mkdir /usr/share/containers/storage: read-only file system
```
