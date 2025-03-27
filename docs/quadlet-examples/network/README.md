# Here is an example of running a network-test container using quadlets for both --network=host and --network=private

You should place this file either in /usr/share/containers/systemd/ or /etc/containers/systemd/

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
