# qmc command reference

## Name

qmc - run commands and inspect the QM environment

## Synopsis

```text
qmc exec [OPTIONS] [--] COMMAND [ARG...]
qmc inspect [OPTIONS]
qmc signal [OPTIONS] NAME
```

Use `systemctl start`, `stop`, `restart` and `status qm.service` to manage QM.
Use `journalctl -b -u qm.service` to read its startup and console output.
Run commands inside QM as root on the host, for example with `sudo`.

## Exec

```sh
sudo qmc exec /bin/bash
sudo qmc exec systemctl list-units
sudo qmc exec podman ps
sudo qmc exec /bin/sh -c 'printf "%s\n" "$1"' sh 'two words'
printf 'hello\n' | sudo qmc exec cat
```

QM must be running. Arguments after `COMMAND` belong to that command, including
options. A shell is used only when explicitly requested. An interactive terminal
is allocated when both standard input and output are terminals. Pipes and
redirection preserve input, output and error streams. The command's exit status
is returned; termination by a signal returns 128 plus its signal number.

To copy a regular file through a stream:

```sh
sudo qmc exec cat /var/tmp/result.log > result.log
sudo qmc exec tee /var/tmp/input.txt < input.txt > /dev/null
```

## Inspect

```sh
qmc inspect
qmc inspect --field rootfs
qmc inspect --field devices
qmc inspect --field /mounts/0/source
sudo qmc inspect --oci --field /linux/resources
```

By default, inspect reads the current merged configuration without starting QM.
Output is JSON; a selected string is printed without quotes. `--field KEY`
selects a top-level key, or a JSON pointer beginning with `/`. Device selections,
seccomp rules and subordinate-ID mappings are resolved at launch, not by this
configuration inspection.

`--oci` reads the OCI configuration saved by the latest launch. It describes
that launch rather than subsequent configuration edits, and fails if no saved
bundle exists. `--config FILE` instead reads one standalone JSON configuration
file, without the normal vendor and administrator layers. It cannot be combined
with `--oci`. See qmc.conf(5) for configuration details.

## Signal

```sh
sudo qmc signal network-ready
sudo qmc signal --clear network-ready
```

Set or clear a named host-state marker visible inside QM at
`/run/host/qmc-signals/NAME`. Both operations are idempotent and work before QM
starts. Markers survive QM restarts until cleared; reboot clears them.
Names begin with an ASCII letter or digit and may contain letters, digits,
periods, underscores and hyphens. Applications can watch markers with systemd
path units. For example:

```ini
[Path]
PathExists=/run/host/qmc-signals/network-ready
Unit=network-dependent.service

[Install]
WantedBy=multi-user.target
```

The host publisher and the application service must be configured separately.
A oneshot service triggered while a marker exists should use
`RemainAfterExit=yes` to avoid repeated activation.

## Options and exit status

All commands accept `--help`, `--verbose` and `--runtime-dir DIR`.
The runtime directory defaults to `/run/qm`; `RUNTIME_DIRECTORY` can override
that default. Normal users should use the directory managed by `qm.service`.
`--verbose` enables command debugging.

Inspect additionally accepts `--config FILE`, `--oci` and `--field KEY`.
Signal additionally accepts `--clear`. Exec requires a command.
Invalid command usage returns 2; other launcher errors return nonzero.
Exec propagates the executed command's status.

## See also

qm(8), qmc.conf(5), systemctl(1), systemd.path(5), podman(1).
