# QM Wayland Subsystem

This package provides Wayland display server support for the QM (Quality Management) containerized environment.

## Components

### wayland-session Script

The `/usr/bin/wayland-session` script monitors and manages Wayland user sessions with configurable options:

- **Command line options**:
  - `-s, --seat SEAT`: Target seat (default: seat0)
  - `-t, --tty TTY`: Target TTY (default: tty7)
  - `-h, --help`: Show help message

- **Environment variables**:
  - `WAYLAND_SEAT`: Override default seat
  - `WAYLAND_TTY`: Override default TTY

### Systemd Services

- **wayland-session.service**: Manages Wayland session lifecycle
- **qm-dbus.socket**: Provides D-Bus session bus placeholder socket
- **wayland.socket**: Provides Wayland display placeholder socket

### Configuration

- **PAM files**: `/etc/pam.d/systemd-user`, `/etc/pam.d/wayland-autologin`
- **Container files**: `/etc/containers/systemd/*.container`

### Device access

Select the devices exposed to QM in a host qmc drop-in, for example
`/etc/qmc.conf.d/60-wayland.conf`:

```json
{
  "devices": [
    {"seat": "seat0", "optional": true},
    {"source": "/dev/tty[0-7]", "optional": true}
  ]
}
```

Restart `qm.service` after changing the selection. The compositor's Quadlet uses
`AddDevice=` to pass the DRM and input devices available inside QM into its
application container. It cannot access devices that qmc has not exposed to QM.
Adjust the host selection for other seats or additional required devices.

## Usage

After installation, the services are automatically enabled and will start when the graphical target is reached.

To check service status:

```bash
systemctl status wayland-session.service
systemctl status qm-dbus.socket
systemctl status wayland.socket
```

To customize seat or TTY, you can create systemd drop-in files:

```bash
# /etc/systemd/system/wayland-session.service.d/custom.conf
[Service]
Environment=WAYLAND_SEAT=seat1
Environment=WAYLAND_TTY=tty8
```
