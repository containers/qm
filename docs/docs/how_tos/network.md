# Using network modes with QM

## Basics: Network Modes in Podman

When running a container with Podman, you can specify the network mode using the `--network` flag. Two common options are `host` and `private`.

### Network=host

If you set `--network=host`, the container will use the host's network stack. This means the container will share the same network namespace as the host, and will be able to access the host's network interfaces, IP addresses, and ports.

In this mode, the container is not isolated from the host's network, and can potentially access sensitive network resources. This can be useful for certain use cases, such as running a container that needs to access a specific network interface or port on the host.

### Network=private (default)

By default, Podman uses the `private` network mode. This means that the container will have its own isolated network namespace, and will not be able to access the host's network interfaces, IP addresses, or ports.

In this mode, the container is isolated from the host's network, and can only communicate with other containers on the same network. This provides a higher level of security, as the container is not able to access sensitive network resources on the host.

### Security Implications

The reason `private` is the default network mode is due to security concerns. By isolating the container's network namespace, Podman prevents the container from accessing sensitive network resources on the host, such as:

* Host's network interfaces and IP addresses
* Host's ports and services
* Other containers on the host

This helps to prevent potential security vulnerabilities, such as:

* Container escape: a container accessing sensitive resources on the host
* Lateral movement: a container accessing other containers on the host

### Example

To illustrate the difference, consider the following example:

```bash
# Run a container with network=host
podman run -it --network=host fedora /bin/bash

# Run a container with network=private (default)
podman run -it --network=private fedora /bin/bash
```

In the first example, the container will share the host's network namespace, while in the second example, the container will have its own isolated network namespace.

For more information, see the [Podman Networking Tutorial](https://github.com/containers/podman/blob/main/docs/tutorials/basic_networking.md).

For network modes configuration example using quadlets, see [Quadlet Network Example](https://github.com/containers/qm/blob/main/docs/quadlet-examples/network/README.md).

## Quadlet example running host and private networks

Here is an example of running a network-test container using quadlets for both --network=host and --network=private. You should place this file either in /usr/share/containers/systemd/ or /etc/containers/systemd/

```console
/usr/share/containers/systemd/
/etc/containers/systemd/
```

For rootless users:

```console
$HOME/.config/containers/systemd/

```

Host Network

```console
# network-test.container
[Container]
ContainerName=network-test
Image=localhost/local-audio-image
Network=host
```

Private Network

```console
# network-test.container
[Container]
ContainerName=network-test
Image=localhost/local-audio-image
Network=private
```
