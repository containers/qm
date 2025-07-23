# Wayland-session-devices

The wayland-session-devices OCI hook enables containers to access Wayland display server devices in a multi-seat
environment managed by systemd-logind.

## Key Functionality

1. **Device Discovery**: The hook automatically discovers and configures access to hardware devices associated with a
   specific systemd-logind seat, including:

   - Input devices (keyboard, mouse, touchpad, etc.)
   - Render devices (GPU hardware acceleration)
   - Display-related devices

2. **Container Configuration**: It dynamically modifies the container's OCI configuration to include the necessary
   device permissions and access controls for Wayland compositor functionality.

3. **Comprehensive Logging**: All operations are logged to `/var/log/qm-wayland-session-devices.log` for monitoring and debugging.

## Configuration

The hook supports the following container annotation:

- `org.containers.qm.wayland.seat`: Specifies which systemd-logind seat devices should be made available to the
  container. This annotation would be used in the QM container and the wayland compositor container
  (running as a nested container inside the QM container) to have access to the required devices.
  The value should match a valid seat name configured in the system's multi-seat infrastructure.

## Logging

The hook provides detailed logging of all operations:

- **Log File**: `/var/log/qm-wayland-session-devices.log`
- **Log Format**: `YYYY-MM-DD HH:MM:SS - qm-wayland-session-devices - LEVEL - MESSAGE`
- **Log Levels**: INFO, WARNING, ERROR

### Example Log Output

```text
2024-01-15 10:30:45 - qm-wayland-session-devices - INFO - Processing Wayland seat annotation: seat0
2024-01-15 10:30:45 - qm-wayland-session-devices - INFO - Found seat system devices for seat0
2024-01-15 10:30:45 - qm-wayland-session-devices - INFO - Adding seat device: /dev/input/event0
2024-01-15 10:30:45 - qm-wayland-session-devices - INFO - Adding input device: /dev/input/mouse0
2024-01-15 10:30:45 - qm-wayland-session-devices - INFO - Adding render device: /dev/dri/renderD128
2024-01-15 10:30:45 - qm-wayland-session-devices - INFO - Processing 5 devices for Wayland seat seat0
2024-01-15 10:30:45 - qm-wayland-session-devices - INFO - Added Wayland seat device: /dev/input/event0
2024-01-15 10:30:45 - qm-wayland-session-devices - INFO - Total devices in final spec: 5
2024-01-15 10:30:45 - qm-wayland-session-devices - INFO - QM Wayland Session Devices hook completed successfully
```

## Example Configuration

To use the Wayland-session-devices hook, you can create a dropin configuration file to add the necessary annotation
to your qm.container:

1. Create a dropin directory and file:

   ```bash
   mkdir -p /etc/containers/systemd/qm.container.d/
   ```

2. Create a dropin file (e.g., `wayland.conf`):

   ```ini
   [Container]
   Annotation=org.containers.qm.wayland.seat=seat0
   ```

The same procedure would be done in the wayland compositor container, running inside the qm container as nested
container, by adding a similar dropin file.
