# QM

## QM is a containerized environment for running Functional Safety QM (Quality Management) software

The main purpose of this package is to allow users to set up an environment which
prevents applications and container tools from interfering with other processes
on the system. For example ASIL (Automotive Safety Integrity Level) environments.

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
