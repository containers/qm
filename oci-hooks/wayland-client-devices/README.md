# Wayland-client-devices

The wayland-client-devices OCI hook enables containers to access GPU hardware acceleration devices for Wayland client
applications that would run as qm's nested containers.

## Key Functionality

1. **GPU Device Discovery**: The hook automatically discovers and configures access to GPU render devices when
   GPU support is enabled, including:

   - GPU hardware acceleration devices

2. **Container Configuration**: It dynamically modifies the container's OCI configuration to include the necessary
   GPU device permissions and access controls for Wayland client applications that require hardware acceleration.

3. **Comprehensive Logging**: All operations are logged to `/var/log/qm-wayland-client-devices.log` for monitoring and debugging.

## Configuration

The hook supports the following container annotation:

- `org.containers.qm.wayland-client.gpu`: Enables GPU device access for Wayland clients. When this annotation is
  present, the hook will automatically detect and configure access to available render devices in `/dev/dri/`.

## Logging

The hook provides detailed logging of all operations:

- **Log File**: `/var/log/qm-wayland-client-devices.log`
- **Log Format**: `YYYY-MM-DD HH:MM:SS - qm-wayland-client-devices - LEVEL - MESSAGE`
- **Log Levels**: INFO, WARNING, ERROR

### Example Log Output

```text
2024-01-15 10:32:15 - qm-wayland-client-devices - INFO - Processing Wayland client GPU annotation: true
2024-01-15 10:32:15 - qm-wayland-client-devices - INFO - Scanning for GPU render devices
2024-01-15 10:32:15 - qm-wayland-client-devices - INFO - Adding GPU render device: /dev/dri/renderD128
2024-01-15 10:32:15 - qm-wayland-client-devices - INFO - Found 1 GPU render devices
2024-01-15 10:32:15 - qm-wayland-client-devices - INFO - Processing 1 GPU devices for Wayland client
2024-01-15 10:32:15 - qm-wayland-client-devices - INFO - Added GPU device: /dev/dri/renderD128
2024-01-15 10:32:15 - qm-wayland-client-devices - INFO - Successfully processed all GPU devices for Wayland client
2024-01-15 10:32:15 - qm-wayland-client-devices - INFO - Total devices in final spec: 1
2024-01-15 10:32:15 - qm-wayland-client-devices - INFO - QM Wayland Client Devices hook completed successfully
```

## Example Configuration

To use the Wayland-client-devices hook, you can create a dropin configuration file to add the necessary annotation
to your container:

1. Create a dropin directory and file:

   ```bash
   mkdir -p /etc/containers/systemd/myapp.container.d/
   ```

2. Create a dropin file (e.g., `wayland-client.conf`):

   ```ini
   [Container]
   Annotation=org.containers.qm.wayland-client.gpu=true
   ```
