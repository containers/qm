# Developers documentation

## Building QM rpm manually with changes

Building QM locally with changes for tests is a recommended practice,
especially for testing new features before submitting a pull request.

**1.** Prerequisites

On CentOS Stream 10, enable CRB and the BlueChi SELinux package repository.
Install `dnf-plugins-core` for the builddep command, then clone the repository.

**2.** Clone the repo

```bash
git clone https://github.com/containers/qm.git && cd qm
dnf builddep rpm/qm.spec
```

**3.** Build the RPM

Select a QM version that is a higher number from the current one.
For example, if today's QM version is 0.6.2, set it to 1.0 so that
the RPM created is identifiable as yours.

```bash
env TMPDIR=/var/tmp make rpm VERSION=1.0
```

The rpm is created at the `${RPM_TOPDIR}/RPMS` folder, by default
`${PWD}/rpmbuild/RPMS`.
You can export **RPM_TOPDIR** to change the path where the rpm will be placed.
For example:

```bash
env TMPDIR=/var/tmp make rpm VERSION=1.0 RPM_TOPDIR=/var/tmp/qm-rpmbuild
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
ls /root/rpmbuild/RPMS/x86_64/qm-1.0-1.x86_64.rpm
/root/rpmbuild/RPMS/x86_64/qm-1.0-1.x86_64.rpm
```

**2.** Download additional packages required by the image

```bash
sudo dnf download --destdir /root/rpmbuild/RPMS/x86_64/ selinux-policy selinux-policy-any
```

**3.** Create a local repository with the new package

```bash
dnf install createrepo_c -y
cd /root/rpmbuild/RPMS/x86_64/
createrepo .
```

**4.** Clone the CentOS Automotive distro for the build

Ensure you meet the requirements for the CentOS Automotive Stream by
referring to [this link](https://sigs.centos.org/automotive/building/).

The following commands will execute:

- Install the podman package
- Clone the sample-images repository and required submodules (automotive-image-builder)
- Cleanups before a fresh build
- Finally creates a new qcow2 image (BASED ON distro name, mode (ostree or regular) and uses the qemu-qm-container sample image)
  NOTE:
  - The path for the new QM rpm file (/root/rpmbuild/RPMS/x86_64)
  - extra_rpms - useful for debug.
  - ssh enabled

The command below utilises automotive-image-builder to produce a `qm-minimal` qcow2 image for cs10,
other example images such as `simple-qm-container` and the `simple-qm`
image can be found in the images directory of the sample-images repository.

```bash
curl -Lo qm.aib.yml "https://gitlab.com/CentOS/automotive/src/automotive-image-builder/-/raw/main/examples/qm.aib.yml?ref_type=heads"

curl -Lo auto-image-builder.sh "https://gitlab.com/CentOS/automotive/src/automotive-image-builder/-/raw/main/auto-image-builder.sh?ref_type=heads"

sudo ./auto-image-builder.sh build \
    --distro cs10 \
    --mode package \
    --define "ssh_permit_root_login=true" \
    --define "ssh_permit_password_auth=true" \
    --define "extra_repos=[{id: local,baseurl: file:///root/rpmbuild/RPMS/x86_64}]" \
    --define "extra_rpms=[qm-1.0, vim-enhanced, openssh-server, openssh-clients, python3, polkit, rsync, strace, dnf, gdb]" \
    --target qemu \
    qm.aib.yml \
    cs10-qemu-qm-container.x86_64.qcow2
```

If you would like more information on building automotive images with automotive-image-builder, please see the
[Automotive SIG pages for AutoSD](https://sigs.centos.org/automotive/getting-started/about-automotive-image-builder/)

Run the virtual machine, default user: root, pass: password.
To change default values, use the [defaults.ipp.yml](https://gitlab.com/CentOS/automotive/src/automotive-image-builder/-/blob/main/include/defaults.ipp.yml) file.

```bash
./automotive-image-builder/automotive-image-runner --nographics ./cs10-qemu-qm-container.x86_64.qcow2
```

## Native build and tests

Use CentOS Stream 10 with CRB enabled and the BlueChi SELinux build dependency
available. The main build uses Meson; the top-level Makefile wraps common tasks.
Subsystem Makefiles retain their separate package builds. The version comes
from `VERSION` (or the `VERSION` override for a local RPM).

```sh
meson setup build --prefix=/usr
meson compile -C build
env TMPDIR=/var/tmp meson test -C build --print-errorlogs
DESTDIR=/var/tmp/qm-stage meson install -C build
```

C dependencies are json-c, libmnl, libnftables and libsystemd >=254.
Python is required when tests are enabled; `-Dtests=false` omits the fixtures.
SELinux compilation uses the system policy development Makefile in the build
directory. Building and staging installation do not load policy on the host.
RPM `%check` runs the unprivileged Meson tests, including configuration, OCI
preparation, exec streams, setup, user namespaces and migration checks.

See [qmc integration tests](../../tests/qmc/README.md) for the disposable installed
service test and supplementary isolated launcher/network/systemd regressions.
Skipped privileged fixtures are reported by unittest. The installed-service test
requires SELinux enforcing and exercises local nested workloads with user
namespaces both disabled and required. Existing TMT/FFI tests remain separate.

The outer launcher and its cleanup state use `/run/qm`; application Podman state
inside QM remains managed by Podman. Changes to runtime behavior should include
focused regressions in `tests/qmc/` and an installed-service VM run when relevant.
