# Virtualization: Android container with Quadlet

This is an example of an Android container running on top of kvm using quadlet and Wayland:

```console
$ cat ~/.config/containers/systemd/android.container

[Service]
Environment=WAYLAND_DISPLAY=wayland-0

[Container]
AddDevice=/dev/dri/renderD128
AddDevice=/dev/kvm
ContainerName=android
NoNewPrivileges=true
DropCapability=all
Environment=PULSE_SERVER=%t/pulse/native
Environment=WAYLAND_DISPLAY=${WAYLAND_DISPLAY}
Environment=XDG_RUNTIME_DIR=%t
Image=quay.io/slopezpa/qemu-aaos
PodmanArgs=--shm-size=5g
SecurityLabelDisable=true
Volume=%t:%t
```
