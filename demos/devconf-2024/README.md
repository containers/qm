# DevConf2024

- [Introduction](## Introduction)
- [Requirements](## Requirements)
- [Install](## Running the demo)

## Introduction

This demo runs uninterfered service containers, process, under the following:

- HOST partition
- QM partition

It demonstartes:

- How to use quadlet service files under HOST and QM partitions
- How to control services with bluechictl

Running the demo recommend environment for tests is inside CentOS-Stream-9

## Requirements

It is recommend to use vm environment for tests in CentOS-Stream-9 virtual machine

Follow the following procedure to prepare virtual machine
[Download and run vm](../../tests/e2e/README.md#run-tmt-tests-framework-locally)

ssh to vm

``` bash
ssh -oStrictHostKeyChecking=no  -oUserKnownHostsFile=/dev/null  "root@localhost" -p <port>
```

## Install and set QM partition

Once inside VM, install rpms

``` bash
dnf install git python3-pip podman
```

Under root directory run the following git commands

``` bash
git clone --depth=1 https://github.com/containers/qm.git
cd qm
git checkout -b devconf-update
git pull origin devconf-update
git sparse-checkout set --no-cone demos/devconf-2024
git sparse-checkout add tests/e2e
```

Run setup script, it installs & prepares QM partition filesystem

``` bash
cd demos/devconf-2024
bash -x setup
```

Check QM partition is running and active

``` bash
systemctl is-active qm
active
```

## Prepare demo services

The demo create containers under HOST partition and QM partition

``` bash
bash -x prepare-demo.sh
```

## Running the demo

Please refer the following demo (ADD LINK)
