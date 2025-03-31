# QM

## QM is a containerized environment for running Functional Safety QM (Quality Management) software

The qm package sets up an isolated runtime environment for non-critical processes, managed through container tools and systemd. It is designed to ensure that these processes do not interfere with the host system, making it ideal for scenarios such as ASIL (Automotive Safety Integrity Level) separation.

QM runs as an exploded container—a persistent, containerized root filesystem mounted under /var/lib/qm/rootfs. It operates with its own instance of systemd, effectively creating a nested user space within its dedicated disk partition. This setup allows the system to isolate and control resource usage via cgroups, namespaces, and security constraints.

System-level tooling like Podman and systemd inside QM are fully independent from the host, so even container commands themselves are sandboxed. The environment is provisioned using Podman and configured with quadlet units, which streamline setup and lifecycle management.

Software installed inside the QM root is automatically isolated from the host. Developers can further segment workloads by using container tools inside QM to manage additional levels of containment for processes requiring extra isolation.
