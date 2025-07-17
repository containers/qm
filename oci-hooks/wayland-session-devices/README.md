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

## Configuration

The hook supports the following container annotation:

- `org.containers.qm.wayland.seat`: Specifies which systemd-logind seat devices should be made available to the
  container. This annotation would be used in the QM container and the wayland compositor container
  (running as a nested container inside the QM container) to have access to the required devices.
  The value should match a valid seat name configured in the system's multi-seat infrastructure.

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
