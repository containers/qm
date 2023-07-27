# QM is a containerized environment for running Functional Safety qm (Quality Management) software

The main purpose of this package is allow users to setup an environment which
prevents applications and container tools from interfering with other all
other processes on the system. For example ASIL (Automotive Safety Integrity Level)
environments.

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

* SELinux Policy

This policy is used to isolate Quality Management parts of the operating system
from the other Domain-Specific Functional Safety Levels (ASIL).

The main purpose of this policy is to prevent applications and container tools
with interfering with other processes on the system. The QM needs to support
further isolate containers run within the qm from the qm_t process and from
each other.

For now all of the control processes in the qm other then containers will run
with the same qm_t type.

* [Hirte](https://github.com/containers/qm/pull/57)

The package configures the hirte agent within the QM.

Hirte is a systemd service controller intended for multi-node environments with
a predefined number of nodes and with a focus on highly regulated ecosystems such
as those requiring functional safety. Potential use cases can be found in domains
such as transportation, where services need to be controlled across different
edge devices and where traditional orchestration tools are not compliant with
regulatory requirements.

Systems with QM installed will have two systemd's running on them. The QM hirte-agent
is based on the hosts /etc/hirte/agent.conf file. By default any changes to the
systems agent.conf file are reflected into the QM /etc/hirte/agent.conf. You can
further customize the QM hirte agent by adding content to the
/usr/lib/qm/rootfs/etc/hirte/agent.conf.d/ directory.

## RPM building dependencies

In order to build qm package on CentOS Stream 9 you'll need Code Ready Builder
repository enabled in order to provide `golang-github-cpuguy83-md2man` package.

```console
# dnf install -y python3-dnf-plugins-core
# dnf config-manager --set-enabled crb
```
