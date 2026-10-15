## Installing QM

The first step to getting started with QM is installation.

Fedora or CentOS Stream 10:
On Fedora and CentOS-Stream systems (with EPEL repository enabled), QM can be directly installed via:

```bash
dnf install qm
```

### RPM Mirrors

Looking for a specific version of QM?
Search in the mirrors list below.

[CentOS Automotive SIG - qm package](https://mirror.stream.centos.org/SIGs/10-stream/automotive/aarch64/packages-main/Packages/q/)

## Preparing and starting QM

Automotive images normally prepare the QM rootfs during the image build.
For a regular writable installation, use:

```sh
sudo /usr/share/qm/setup
sudo systemctl status qm.service
sudo qmc exec /bin/bash
```

Use `setup --help` for custom rootfs, writable etc and writable var paths.
On immutable systems, add software to the rootfs during image construction.
The launcher keeps the rootfs read-only and provides writable etc and var trees.

## User namespaces

The default `auto` mode enables user namespaces when both host subordinate-ID
files contain ranges for `qm_root`; otherwise QM runs without them.
The helper creates the accounts, ranges and a `userns: required` drop-in:

```sh
sudo /usr/share/qm/userns enable
sudo systemctl restart qm.service
```

Use `--qm-root-dir` when the prepared rootfs has a custom location. To disable:

```sh
sudo /usr/share/qm/userns disable
sudo systemctl restart qm.service
```

Disabling writes `userns: off` explicitly. Enabling requires filesystem support
for ID mapped mounts; see [configuration](configuration.md#user-namespaces).
With user namespaces enabled, host process listings show users such as
`qm_root` and `qm_dbus`.
