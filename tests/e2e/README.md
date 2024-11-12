# e2e testing

- [Introduction](#introduction)
- [Requirements](#requirements)
- [Tests executed](#tests-executed)
- [Running using containers](#running-using-containers)
- [Running using virt](#running-using-virt)
- [Env variables](#env-variables)
- [Demo](#demo)
- [Automated tests](#automated-e2e-tests)

## Introduction

`run-test-e2e` executes tests for qm software using [podman quadlet](https://www.redhat.com/sysadmin/quadlet-podman) as platform.
For running the tool is required to run as **root** as the nested containers will need privileges to change limits settings.

Demo:
[![asciicast](https://asciinema.org/a/cwnb6RjckO7vXLUvHpbMA9fAU.svg)](https://asciinema.org/a/cwnb6RjckO7vXLUvHpbMA9fAU)

## Requirements

A recent version of Fedora or CentOS9 with the following packages: bash, selinux and podman.
Make sure to enable `cgroupv2`.
Enable the following on host machine before installing podman
[bluechi_repo](https://github.com/containers/qm/blob/main/tests/e2e/ContainerFile.control#L44-L45)

## Tests executed

The idea behind the test is: create isolated environments using technologies like containers, podman (quadlet), selinux and cgroupv2. On top of that, make sure all systemd services in the nodes are controlled remotely taking advanced of [bluechi](https://github.com/containers/bluechi/).

## Running using containers

By default the tool will create three containers, `control`, `node1` (both running on the host) and the third container will be running on top of `node1` which is called `qm`. In other words, this will be a **nested container environment**.

In a short description, the container control is the **bluechi controller**, `node1` and `qm` are the **bluechi agents**. After the three nodes are installed and properly configured will be executed several tests scenarios focused in managing systemd remotely using bluechi.

## Running using virt

Not developed yet.

## Env variables

There a few env variables that can be set to change the tool behavior.
Just call `export VARNAME=foobar` before executing the script.

| Name                     | Description                                                       |
| ------------------------ | ----------------------------------------------------------------- |
| NUMBER_OF_NODES          | Increase the number of agent nodes. Useful for scale tests.       |
| NET_INTERFACE_IP_CONTROL | By default is eth0. Used to collect ip address of controller node |
| TAG_CONTROL_MACHINE      | The control machine tag. Default is control:latest                |

## Demo

If your browser doesn't support asciinema, here the demo in text:

``` bash
[root@dell730 e2e]# #host
[root@dell730 e2e]# cat /etc/fedora-release
Fedora release 38 (Thirty Eight)
[root@dell730 e2e]# getenforce
Enforcing
[root@dell730 e2e]# ./run-test-e2e
[ INFO  ] Starting setup
[ INFO  ] ==============================
[ INFO  ] Cleaning any previous e2e files

[ INFO  ] Preparing ASIL environment
[ INFO  ] ==============================
[ INFO  ] Creating container control [ASIL mode]
[ INFO  ] Creating stub systemd service: container-safety in container control
[ INFO  ] Creating stub systemd service: container-cruise_control in container control
[ INFO  ] Creating stub systemd service: container-tires in container control
[ INFO  ] Creating stub systemd service: container-breaks in container control

[ INFO  ] Preparing QM environment
[ INFO  ] ==============================
[ INFO  ] Creating container node1 [QM mode]
[ INFO  ] Creating stub systemd service: container-radio in node1 and moving it to container qm inside node1
[ INFO  ] Creating stub systemd service: container-store in node1 and moving it to container qm inside node1
[ INFO  ] Creating stub systemd service: container-stream_audio in node1 and moving it to container qm inside node1
[ INFO  ] Creating stub systemd service: container-maps in node1 and moving it to container qm inside node1

[ INFO  ] Starting tests
[ INFO  ] ==============================
[ INFO  ] Waiting bluechi containers be ready...

[ INFO  ] #1- Test scenario: bluechi list all units from control to node (vise-versa)
[ INFO  ] Connected to control, listing few systemd units from control
[ INFO  ] Executing: podman exec control bluechictl list-units control | head -5
ID                                                                              |   ACTIVE|      SUB
====================================================================================================
console-getty.service                                                           | inactive|     dead
dev-ttyS7.device                                                                |   active|  plugged
sys-devices-pci0000:00-0000:00:1f.2-ata10-host9-target9:0:0-9:0:0:0-block-sda-sd|   active|  plugged

[ INFO  ] Connected to control, listing few systemd units from node1
[ INFO  ] Executing: podman exec control bluechictl list-units node1 | head -5
ID                                                                              |   ACTIVE|      SUB
====================================================================================================
dracut-shutdown.service                                                         |   active|   exited
systemd-journald.service                                                        |   active|  running
dev-hugepages.mount                                                             |   active|  mounted

[ INFO  ] Connected to control, listing few systemd units from qm.544fac352098
[ INFO  ] Executing: podman exec control bluechictl list-units qm.544fac352098 | head -5
ID                                                                              |   ACTIVE|      SUB
====================================================================================================
systemd-udevd.service                                                           | inactive|     dead
container-stream_audio.service                                                  |   active|  running
var-lib-containers-storage-overlay\x2dcontainers-37579a9bbc96dd7e8c60eae095876a9|   active|  mounted

[ INFO  ] All set!
[root@dell730 e2e]# podman exec node1 podman ps
CONTAINER ID  IMAGE       COMMAND     CREATED         STATUS         PORTS       NAMES
eeed67710d86              /sbin/init  45 seconds ago  Up 44 seconds              qm
[root@dell730 e2e]# podman exec control podman ps
CONTAINER ID  IMAGE                                               COMMAND         CREATED             STATUS             PORTS       NAMES
3b53534dede0  registry.access.redhat.com/ubi8/ubi-minimal:latest  sleep infinity  About a minute ago  Up About a minute              safety
9402e530feb8  registry.access.redhat.com/ubi8/ubi-minimal:latest  sleep infinity  About a minute ago  Up About a minute              cruise_control
07b55cee56fd  registry.access.redhat.com/ubi8/ubi-minimal:latest  sleep infinity  About a minute ago  Up About a minute              tires
27441c8a0fe5  registry.access.redhat.com/ubi8/ubi-minimal:latest  sleep infinity  About a minute ago  Up About a minute              breaks
[root@dell730 e2e]# podman exec node1 podman exec qm podman ps
CONTAINER ID  IMAGE                                               COMMAND         CREATED         STATUS         PORTS       NAMES
faf4da74567d  registry.access.redhat.com/ubi8/ubi-minimal:latest  sleep infinity  43 seconds ago  Up 44 seconds              radio
37579a9bbc96  registry.access.redhat.com/ubi8/ubi-minimal:latest  sleep infinity  41 seconds ago  Up 42 seconds              store
7492e2972bf8  registry.access.redhat.com/ubi8/ubi-minimal:latest  sleep infinity  40 seconds ago  Up 40 seconds              stream_audio
bf87fe122d8c  registry.access.redhat.com/ubi8/ubi-minimal:latest  sleep infinity  38 seconds ago  Up 38 seconds              maps
```

## Automated e2e tests

The containers/qm project build RPM packages out of pull requests, commits or releases,
In addition testing code changes and bring upstream coomunity releases to Fedora Linux.
The above achieved through community project [packit](https://packit.dev), an open source project aiming
to ease the integration of source projects with Fedora Linux, CentOS Stream and other distributions.

Packit tests are running in [TestingFarm](https://packit.dev/docs/testing-farm/) with
community tool [TMT](https://tmt.readthedocs.io/en/stable/) testing framework
Refer [FMF](https://fmf.readthedocs.io/en/stable) for tmt test metadata specification

### Run TMT tests framework locally

#### Setup device under test

- Install required packages

``` bash
dnf install -y libguestfs-tools-c qemu-kvm python3-pip git tmt tmt-report-junit
```

- Download CentOSStream9 cloud image for [CentOSStream9](https://cloud.centos.org/centos/9-stream/x86_64/images/CentOS-Stream-GenericCloud-9-latest.x86_64.qcow2)

``` bash
curl --output-dir "/tmp" -O https://cloud.centos.org/centos/9-stream/x86_64/images/CentOS-Stream-GenericCloud-9-latest.x86_64.qcow2
```

- Increase disk size in +20G

``` bash
qemu-img resize /tmp/CentOS-Stream-GenericCloud-9-latest.x86_64.qcow2 +20G
```

- Set root password.

``` bash
virt-customize -a /tmp/CentOS-Stream-GenericCloud-9-latest.x86_64.qcow2 --root-password password:${PASSWORD}
```

- Update disk size

Use the following command within the vm, once qemu-image resize used

```bash
sudo growpart /dev/vda 1
```

In case of running FFI tests, test scripts, add additional partition, reserve some space as following

```bash
growpart --free-percent=50 /dev/vda 1
```

Extend the mounted filesystem

```bash
xfs_growfs /
```

- Run VM locally

``` bash
/usr/bin/qemu-system-x86_64 -nographic -smp 12 -enable-kvm -m 2G -machine q35 -cpu host -device virtio-net-pci,netdev=n0,mac=FE:30:26:a6:91:2d -netdev user,id=n0,net=10.0.2.0/24,hostfwd=tcp::${PORT}-:22 -drive file=/tmp/CentOS-Stream-GenericCloud-9-latest.x86_64.qcow2,index=0,media=disk,format=qcow2,if=virtio,snapshot=off
```

**To exit from qemu**: `CTRL-a c` and then `quit` into the qemu terminal

#### Install TMT locally (python)

Refer [tmt install](https://tmt.readthedocs.io/en/stable/overview.html#install)

- Install tmt from pip optional

``` bash
 pip install tmt
 pip install tmt[junit-report]
```

- Verify tmt plan/ tests are visible

``` bash
git clone https://github.com/containers/qm && cd qm
cd tests && tmt plan ls
tmt tests ls

```

#### Run TMT against VM

- Run tests

``` bash
tmt run plans -n /plans/e2e/tier-0

or connecting to VM:

tmt -c distro=centos-stream-9 run -a \
        provision --how connect -u root -p ${PASSWORD} -P ${PORT} -g localhost \
        plans -n /plans/e2e/tier-0
```

Note:
Fedora distro supported

##### Other tmt configurations

In case of running against prepared image, such as AutoSD, use the following tmt command
Where there is already running vm set with:
Set test with comtext `-c distro=automotive-stream-distribution-9`

- qm container with bluechi agent running under systemd.

- host is running bluechi and bluechi agent.

Override the context distro and CONTROL_CONTAINER_NAME and NODES_FOR_TESTING_ARR

``` bash
tmt  -c distro=automotive-stream-distribution-9 run -e CONTROL_CONTAINER_NAME="host" \
     -e NODES_FOR_TESTING_ARR="\"host qm.host\""  -a \
     provision --how connect -u root -p ${PASSWORD} -P {PORT} -g localhost plans -n /plans/e2e/tier-0
```

##### FFI tmt configurations

Freedom From Interference, FFI, tests prove cgroups and other security constraints work in the QM environment.
QM environment running inside qm container as systemd service and isolated from interfereing other host
processes.

Running FFI tests connecting c9s host, sets different tests environment from the demo environment.

``` bash
tmt -c scenario=ffi run -a prepare  provision --how connect \
    -u root -p ${PASSWORD} -P {PORT} -g localhost plan -n /plans/e2e/ffi
```

##### Running manual tests with PACKIT copr packages

Assume debug of PR rpm needed to run locally,
Use context `-c run=manual` with environment variable `-e PACKIT_COPR_PROJECT=<packit-qm-copr>`

``` bash
tmt -c distro=fedora-41 -c run=manual  run  -e PACKIT_COPR_PROJECT=packit/containers-qm-647 -a prepare -vvv -d  provision --how connect -u root -p <password> -P <port> -g localhost  plans -n /plans/e2e/tier-0 exec -d -vvv report --how junit
```
