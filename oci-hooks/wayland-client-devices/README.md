# Wayland-client-devices

The wayland-client-devices OCI hook enables containers to access GPU hardware acceleration devices for Wayland client
applications that would run as qm's nested containers.

## Key Functionality

1. **GPU Device Discovery**: The hook automatically discovers and configures access to GPU render devices when
   GPU support is enabled, including:

   - GPU hardware acceleration devices

2. **Container Configuration**: It dynamically modifies the container's OCI configuration to include the necessary
   GPU device permissions and access controls for Wayland client applications that require hardware acceleration.

## Configuration

The hook supports the following container annotation:

- `org.containers.qm.wayland-client.gpu`: Enables GPU device access for Wayland clients. When this annotation is
  present, the hook will automatically detect and configure access to available render devices in `/dev/dri/`.

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
