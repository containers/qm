# Here is an example of running a network-test container using quadlets for both --network=host and --network=private

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
