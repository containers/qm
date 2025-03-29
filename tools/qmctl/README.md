# QMCTL

QMCTL is a command-line tool for managing QM containers using Podman. It provides a simple interface to inspect container internals, run commands, and monitor system-level resources.

## Usage
Show container information

```bash
./qmctl show                        # Show raw container config
./qmctl show all                    # Show all supported info (except live cgtop)
./qmctl show unix-domain-sockets    # Inspect UNIX domain sockets
./qmctl show shared-memory          # View shared memory segments
./qmctl show namespaces             # View container namespaces
./qmctl show available-devices      # Check configured devices
./qmctl show resources              # Live stream systemd-cgtop
```

Run a command inside the container

```bash
./qmctl exec uname -a
./qmctl exec ls /dev --json
```

With verbose output
```
./qmctl --verbose show
```

Requirements

- Python 3.6+
- Podman installed and configured
- Optional: argcomplete for tab completion

To enable autocompletion:

```bash
pip install argcomplete
activate-global-python-argcomplete --user
```
