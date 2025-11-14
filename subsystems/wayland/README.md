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
- **Container files**: `/etc/container/systemd/*.container`

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
