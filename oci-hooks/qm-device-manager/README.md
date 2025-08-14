# QM Device Manager OCI Hook

The QM Device Manager OCI Hook provides dynamic device access management for QM containers. This lightweight shell script hook replaces static drop-in configurations with a flexible, annotation-based approach to device mounting.

## Overview

The device manager hook allows containers to request specific device access through annotations. The hook dynamically discovers and mounts the requested devices at container creation time. It supports both device categories and Wayland seat-based device access.

## How Device Injection Works

The QM Device Manager hook operates during the OCI container **precreate** phase, intercepting container creation to dynamically inject device access. When QM starts a container with device annotations, the hook:

1. Discovers available devices on the host system based on annotation patterns
2. Validates device accessibility and permissions
3. Injects device access into the container's OCI specification via `linux.resources.devices[]`
4. Adds device mounts to make devices available inside the container

### OCI Device Injection Format

The hook modifies the container's OCI runtime specification to include device access rules:

```json
{
  "linux": {
    "resources": {
      "devices": [
        {
          "allow": true,
          "type": "c",
          "major": 116,
          "minor": 0,
          "access": "rwm"
        },
        {
          "allow": true,
          "type": "c",
          "major": 116,
          "minor": 1,
          "access": "rwm"
        }
      ]
    }
  },
  "mounts": [
    {
      "source": "/dev/snd/controlC0",
      "destination": "/dev/snd/controlC0",
      "type": "bind",
      "options": ["bind", "rprivate"]
    }
  ]
}
```

This ensures the container has both cgroup device access permissions and the actual device nodes mounted.

### Testing and Verification

The device injection process is comprehensively tested in the test suite:

- Device Discovery Tests (`test_qm_devices.py`): Verifies correct device discovery for all supported types
- Annotation Processing (`test_qm_validation.py`): Tests annotation parsing and validation
- Mock Device Support (`test_utils.py`): Provides mock device infrastructure for CI testing
- Integration Tests (`test_qm_performance.py`): End-to-end hook execution testing

Run tests to verify device injection:

```bash
cd oci-hooks && tox -e unit -- -k "device"
```

### Library Architecture

The QM Device Manager hook uses a modular library architecture for maintainability and testing:

#### Core Libraries

- `common.sh`: Shared logging and utility functions used across all OCI hooks
- `device-support.sh`: Production device discovery and management functions
- `mock-device-support.sh`: Testing-specific device simulation functions

#### Mock Device Support for Testing

The `mock-device-support.sh` library enables comprehensive testing without requiring actual hardware devices. It works by:

Environment Variable Control - Tests set environment variables like:

```bash
TEST_MOCK_AUDIO_DEVICES="/tmp/test_devices/snd/controlC0,/tmp/test_devices/snd/pcmC0D0p"
TEST_MOCK_VIDEO_DEVICES="/tmp/test_devices/video0,/tmp/test_devices/video1"
TEST_LOGFILE="/tmp/test.log"  # Enables test mode
```

Mock Device Creation - Python test framework creates temporary device files:

```python
# In test_utils.py DeviceDetector class
device_path = Path("/tmp/test_devices/snd/controlC0")
device_path.parent.mkdir(parents=True, exist_ok=True)
device_path.touch()  # Creates regular file as mock device
```

Hook Library Selection - The hook script automatically detects test mode and sources the appropriate library:

```bash
# In oci-qm-device-manager script
if [[ -n "${TEST_LOGFILE:-}" ]]; then
    source /usr/libexec/oci/lib/mock-device-support.sh
else
    source /usr/libexec/oci/lib/device-support.sh
fi
```

**NOTE**: mock device library is not supported in a productive environment.

Mock Functions - `mock-device-support.sh` overrides discovery functions to return test devices:

```bash
discover_audio_devices() {
    if [[ -n "${TEST_MOCK_AUDIO_DEVICES:-}" ]]; then
        echo "${TEST_MOCK_AUDIO_DEVICES}" | tr ',' '\n'
    fi
}

get_device_info() {
    local device_path="$1"
    # Returns mock device info for regular files in test mode
    echo "c 116:0"  # Mock major:minor for audio devices
}
```

This architecture allows the same hook script to work with both real hardware devices in production and simulated devices in CI testing environments.

## Supported Device Types

### Traditional Device Categories

| Device Type | Annotation | Devices Mounted | Description |
|-------------|------------|-----------------|-------------|
| audio | `org.containers.qm.device.audio=true` | `/dev/snd/*` | ALSA sound devices |
| video | `org.containers.qm.device.video=true` | `/dev/video*`, `/dev/media*` | V4L2 video devices |
| input | `org.containers.qm.device.input=true` | `/dev/input/*` | Input devices (keyboard, mouse, etc.) |
| ttys | `org.containers.qm.device.ttys=true` | `/dev/tty0-7` | Virtual TTY devices for window managers |
| ttyUSB | `org.containers.qm.device.ttyUSB=true` | `/dev/ttyUSB*` | USB TTY devices for serial communication |
| dvb | `org.containers.qm.device.dvb=true` | `/dev/dvb/*` | DVB digital TV devices |
| radio | `org.containers.qm.device.radio=true` | `/dev/radio*` | Radio devices |

### Wayland Seat Support

| Annotation | Purpose | Description |
|------------|---------|-------------|
| `org.containers.qm.wayland.seat=<seat_name>` | Multi-seat support | Mounts devices associated with a specific Wayland seat (e.g., `seat0`) |

The Wayland seat functionality dynamically discovers and mounts devices associated with the specified seat using `loginctl seat-status`. This enables proper multi-seat support for Wayland environments where different users may be logged into different seats.

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
   # Wayland seat support
   Annotation=org.containers.qm.wayland.seat=seat0
   ```

### Generated Systemd Service

When using Quadlet (`.container` files), the systemd generator creates the actual `ExecStart` commands that execute `podman run`. You can preview these with:

```bash
# View generated systemd service commands
/usr/lib/systemd/system-generators/podman-system-generator --dryrun

# Check generated service files
ls -la /var/lib/systemd/generated/
cat /var/lib/systemd/generated/container-name.service
```

#### Example Generated Commands within QM

For a Quadlet container with device annotations:

Quadlet File (`/etc/containers/systemd/audio-app.container`):

```ini
[Unit]
Description=Audio Application Container
After=local-fs.target

[Container]
Image=my-audio-app:latest
Annotation=org.containers.qm.device.audio=true
Annotation=org.containers.qm.device.video=true
Exec=sleep infinity

[Install]
WantedBy=default.target
```

Generated ExecStart Command:

```bash
ExecStart=/usr/bin/podman run \
  --cidfile=%t/%N.cid \
  --cgroups=split \
  --replace \
  --rm -d \
  --sdnotify=container \
  --name=audio-app \
  --annotation=org.containers.qm.device.audio=true \
  --annotation=org.containers.qm.device.video=true \
  localhost/qm/my-audio-app:latest sleep infinity
```

When this service starts, the `qm-device-manager` hook intercepts the container creation and dynamically adds device mounts like:

- `--device=/dev/snd/controlC0:/dev/snd/controlC0`
- `--device=/dev/snd/pcmC0D0p:/dev/snd/pcmC0D0p`
- `--device=/dev/video0:/dev/video0`

## Logging

The hook logs activity to `/var/log/qm-device-manager.log` for debugging and monitoring:

```bash
# View hook activity
tail -f /var/log/qm-device-manager.log

# Check device discovery for a specific container
grep "audio" /var/log/qm-device-manager.log

# Check Wayland seat processing
grep "Wayland seat" /var/log/qm-device-manager.log
```

## Security Considerations

- Only devices that exist on the host are mounted
- Device permissions are preserved from the host
- Hook validates device accessibility before mounting
- Annotation-based activation prevents accidental device exposure
- Wayland seat integration respects systemd-logind seat assignments

## Troubleshooting

### Device Not Available

If a requested device is not mounted:

1. Check if the device exists on the host: `ls -la /dev/snd/`
2. Verify the annotation syntax: `org.containers.qm.device.audio=true`
3. Check hook logs: `grep ERROR /var/log/qm-device-manager.log`
4. Ensure the device is accessible: `test -c /dev/snd/controlC0`

### Wayland Seat Issues

If Wayland seat devices are not mounted:

1. Check seat status: `loginctl seat-status seat0`
2. Verify seat annotation: `org.containers.qm.wayland.seat=seat0`
3. Check systemd-logind service: `systemctl status systemd-logind`
4. Review seat logs: `grep "seat0" /var/log/qm-device-manager.log`

### Hook Not Triggering

If the hook is not being called:

1. Verify hook installation: `ls -la /usr/libexec/oci/hooks.d/`
2. Check hook configuration: `cat /usr/share/containers/oci/hooks.d/oci-qm-device-manager.json`
3. Validate annotation pattern matching
4. Check podman/crun OCI hook support
