# QM Device Manager OCI Hook

The QM Device Manager OCI Hook provides dynamic device access management for QM containers. This lightweight shell script hook replaces static drop-in configurations with a flexible, annotation-based approach to device mounting.

## Overview

The device manager hook allows containers to request specific device access through annotations. The hook dynamically discovers and mounts the requested devices at container creation time.

## Supported Devices

| Device Type | Annotation | Devices Mounted | Description |
|-------------|------------|-----------------|-------------|
| audio | `org.containers.qm.device.audio=true` | `/dev/snd/*` | ALSA sound devices |
| video | `org.containers.qm.device.video=true` | `/dev/video*`, `/dev/media*` | V4L2 video devices |
| input | `org.containers.qm.device.input=true` | `/dev/input/*` | Input devices (keyboard, mouse, etc.) |
| ttys | `org.containers.qm.device.ttys=true` | `/dev/tty0-7` | Virtual TTY devices for window managers |
| ttyUSB | `org.containers.qm.device.ttyUSB=true` | `/dev/ttyUSB*` | USB TTY devices for serial communication |
| dvb | `org.containers.qm.device.dvb=true` | `/dev/dvb/*` | DVB digital TV devices |
| radio | `org.containers.qm.device.radio=true` | `/dev/radio*` | Radio devices |

## Usage Examples

### Systemd Drop-In Files

1. Create a drop-in directory and file:

   ```bash
   mkdir -p /etc/containers/systemd/qm.container.d/
   ```

2. Create a dropin file (e.g., `devices.conf`):

   ```ini
   [Container]
   Annotation=org.containers.qm.device.audio=true
   Annotation=org.containers.qm.device.ttys=true
   ```

### Podman Command Line

```bash
# Run container with audio device access
podman run --annotation org.containers.qm.device.audio=true qm

# Run container with all TTY devices (for window managers)
podman run --annotation org.containers.qm.device.ttys=true qm

# Run container with all USB TTY devices (for serial communication)
podman run --annotation org.containers.qm.device.ttyUSB=true qm

# Run container with multiple device types
podman run \
  --annotation org.containers.qm.device.audio=true \
  --annotation org.containers.qm.device.video=true \
  qm
```

## Logging

The hook logs activity to `/var/log/qm-device-manager.log` for debugging and monitoring:

```bash
# View hook activity
tail -f /var/log/qm-device-manager.log

# Check device discovery for a specific container
grep "audio" /var/log/qm-device-manager.log
```

## Security Considerations

- Only devices that exist on the host are mounted
- Device permissions are preserved from the host
- Hook validates device accessibility before mounting
- Annotation-based activation prevents accidental device exposure

## Troubleshooting

### Device Not Available

If a requested device is not mounted:

1. Check if the device exists on the host: `ls -la /dev/snd/`
2. Verify the annotation syntax: `org.containers.qm.device.audio=true`
3. Check hook logs: `grep ERROR /var/log/qm-device-manager.log`
4. Ensure the device is accessible: `test -c /dev/snd/controlC0`

### Hook Not Triggering

If the hook is not being called:

1. Verify hook installation: `ls -la /usr/libexec/oci/hooks.d/`
2. Check hook configuration: `cat /usr/share/containers/oci/hooks.d/oci-qm-device-manager.json`
3. Validate annotation pattern matching
4. Check podman/crun OCI hook support
