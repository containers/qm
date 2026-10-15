# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 Alexander Larsson
# See LICENSE for the full license text.

"""Run inside the same delegated user, mount and network namespaces as smoke.py."""

import json
import os
import pathlib
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time

SOURCE = pathlib.Path(__file__).resolve().parents[2]
LAUNCHER = pathlib.Path(sys.argv[1]).resolve()
VENDOR = json.loads((SOURCE / "data/qmc.conf.in").read_text())
MACHINE_ID_STATE = sys.argv[2] if len(sys.argv) > 2 else "existing"
HOST_MACHINE_ID = pathlib.Path("/etc/machine-id").read_text().strip()

subprocess.run(["mount", "--make-rprivate", "/"], check=True)
subprocess.run(["mount", "-t", "tmpfs", "tmpfs", "/run"], check=True)
pathlib.Path("/run/systemd").mkdir()

with tempfile.TemporaryDirectory(prefix="qm-systemd-") as temporary:
    directory = pathlib.Path(temporary)
    root = directory / "root"
    root.mkdir()
    for name in ("lib", "lib64", "bin", "sbin"):
        (root / name).symlink_to("usr/" + name)
    etc = root / "etc"
    etc.mkdir()
    initial_id = "d2c79cc3388a48e494c8cd22cce8f499"
    if initial_id == HOST_MACHINE_ID:
        initial_id = "1" * 32
    if MACHINE_ID_STATE == "uninitialized":
        initial_id = "uninitialized"
    (etc / "machine-id").write_text(initial_id + "\n")
    (etc / "os-release").write_text('ID=qm-test\nPRETTY_NAME="QM test"\n')
    units = etc / "systemd/system"
    units.mkdir(parents=True)
    (units / "qm-test.target").write_text(
        "[Unit]\nDefaultDependencies=no\nRequires=qm-test-ready.service qm-test-signal.path\n"
        "After=qm-test-ready.service\n")
    # Readiness here uses PID 1's /run/systemd/notify, distinct from crun's proxy.
    (units / "qm-test-ready.service").write_text(
        "[Unit]\nDefaultDependencies=no\n[Service]\nType=notify\n"
        "NotifyAccess=all\nRemainAfterExit=yes\n"
        "ExecStart=/usr/bin/systemd-notify --ready\n"
        "StandardOutput=null\nStandardError=null\n")
    (units / "qm-test-signal.path").write_text(
        "[Unit]\nDefaultDependencies=no\n[Path]\n"
        "PathExists=/run/host/qmc-signals/network-ready\n")
    (units / "qm-test-signal.service").write_text(
        "[Unit]\nDefaultDependencies=no\n[Service]\nType=oneshot\nRemainAfterExit=yes\n"
        "ExecStart=/usr/bin/touch /run/signal-received\n")

    config = json.loads((SOURCE / "data/qm.json").read_text())
    config["root"]["path"] = str(root)
    config["process"]["args"] = ["/usr/lib/systemd/systemd", "--unit=qm-test.target"]
    config["process"]["env"] += ["SYSTEMD_GENERATOR_PATH=/run/no-generators",
                                  "SYSTEMD_ENVIRONMENT_GENERATOR_PATH=/run/no-generators"]
    config["process"].pop("selinuxLabel")
    config["process"].pop("rlimits")
    config["linux"].pop("mountLabel")
    config["linux"].pop("sysctl")
    config["linux"]["resources"] = {"devices": []}
    config["mounts"] = [m for m in config["mounts"]
                        if m["destination"] != "/sys/fs/selinux"]
    config["mounts"] += [
        {"destination": "/usr", "source": "/usr", "type": "bind", "options": ["rbind", "ro"]},
    ]
    for mount in config["mounts"]:
        if mount.get("type") == "devpts":
            mount["options"] = ["gid=0" if o == "gid=5" else o for o in mount["options"]]
    base = directory / "base.json"
    base.write_text(json.dumps(config))
    filename = directory / "qmc.conf"
    filename.write_text(json.dumps({"base-config": str(base), "userns": "off",
                                  "capabilities": VENDOR["capabilities"],
                                  "mounts": [{"source": str(etc), "destination": "/etc"}],
                                  "seccomp": str(SOURCE / "tests/qmc/seccomp-no-rt.json")}))
    runtime = directory / "runtime"
    signal_command = [str(LAUNCHER), "signal", "--runtime-dir", str(runtime)]
    subprocess.run([*signal_command, "persistent"], check=True)
    persistent_inode = (runtime / "signals/persistent").stat().st_ino
    signal_before_startup = MACHINE_ID_STATE == "existing"
    if signal_before_startup:
        subprocess.run([*signal_command, "network-ready"], check=True)

    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as notify, \
            (directory / "console.log").open("w+") as log:
        notify.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        notify.bind("/run/systemd/notify")
        process = subprocess.Popen(
            [str(LAUNCHER), "launch", "--verbose", "--runtime-dir", str(runtime),
             "--config", str(filename)],
            stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            env={**os.environ, "NOTIFY_SOCKET": "/run/systemd/notify"})
        try:
            notify.settimeout(10)
            message, ancillary, flags, address = notify.recvmsg(
                256, socket.CMSG_SPACE(struct.calcsize("3i")))
            assert message == b"READY=1", message
            credentials = next(data for level, kind, data in ancillary
                               if level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS)
            assert struct.unpack("3i", credentials)[0] == process.pid
            notify.close()  # Release crun's notification barrier.
            result = subprocess.run(
                [str(LAUNCHER), "exec", "--runtime-dir", str(runtime),
                 "/usr/bin/systemctl", "is-active", "qm-test-ready.service"],
                text=True, capture_output=True, timeout=5)
            assert result.returncode == 0 and result.stdout == "active\n", result

            def exec_in_qm(*command):
                return subprocess.run(
                    [str(LAUNCHER), "exec", "--runtime-dir", str(runtime), *command],
                    text=True, capture_output=True, timeout=5)

            if not signal_before_startup:
                result = exec_in_qm("/usr/bin/test", "-e", "/run/signal-received")
                assert result.returncode == 1, result
                subprocess.run([*signal_command, "network-ready"], check=True)
            deadline = time.monotonic() + 5
            while True:
                result = exec_in_qm("/usr/bin/test", "-e", "/run/signal-received")
                if result.returncode == 0:
                    break
                assert time.monotonic() < deadline, result
                time.sleep(0.01)
            result = exec_in_qm("/usr/bin/touch", "/run/host/qmc-signals/guest")
            assert result.returncode != 0 and "Read-only file system" in result.stderr, result
            subprocess.run([*signal_command, "--clear", "network-ready"], check=True)
            result = exec_in_qm("/usr/bin/test", "!", "-e", "/run/host/qmc-signals/network-ready")
            assert result.returncode == 0, result
            result = subprocess.run(
                [str(LAUNCHER), "exec", "--runtime-dir", str(runtime),
                 "/usr/bin/cat", "/etc/machine-id"],
                text=True, capture_output=True, timeout=5)
            assert result.returncode == 0, result
            assert result.stdout.strip() == HOST_MACHINE_ID, result
            result = subprocess.run(
                [str(LAUNCHER), "exec", "--runtime-dir", str(runtime),
                 "/usr/bin/systemctl", "start", "systemd-machine-id-commit.service"],
                text=True, capture_output=True, timeout=10)
            assert result.returncode == 0, result
            result = subprocess.run(
                [str(LAUNCHER), "exec", "--runtime-dir", str(runtime),
                 "/usr/bin/systemctl", "show", "--property=Result", "--property=ConditionResult",
                 "systemd-machine-id-commit.service"],
                text=True, capture_output=True, timeout=5)
            assert result.returncode == 0 and "Result=success\n" in result.stdout, result
            condition = "yes" if MACHINE_ID_STATE == "uninitialized" else "no"
            assert "ConditionResult=" + condition + "\n" in result.stdout, result
            assert (etc / "machine-id").read_text().strip() == HOST_MACHINE_ID
            result = subprocess.run(
                [str(LAUNCHER), "exec", "--runtime-dir", str(runtime),
                 "/usr/bin/cat", "/proc/self/mountinfo"],
                text=True, capture_output=True, timeout=5)
            assert result.returncode == 0, result
            assert not any(line.split()[4] == "/etc/machine-id"
                           for line in result.stdout.splitlines()), result
            os.kill(process.pid, signal.SIGRTMIN + 3)
            assert process.wait(timeout=10) == 0
            log.seek(0)
            assert "running in system mode" in log.read(), "missing early systemd console output"
            print("Systemd PID 1 inherits the host machine ID, handles machine-id commit "
                  f"({MACHINE_ID_STATE}), accepts service notifications and forwards readiness", flush=True)
            print("Read-only host signals activate a .path service "
                  f"({'before' if signal_before_startup else 'after'} container startup)", flush=True)
        except BaseException:
            log.seek(0)
            print(log.read()[-8000:], file=sys.stderr)
            raise
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            subprocess.run([str(LAUNCHER), "cleanup", "--runtime-dir", str(runtime)], check=True)
        assert runtime.is_dir() and list(runtime.iterdir()) == [runtime / "signals"]
        assert (runtime / "signals/persistent").stat().st_ino == persistent_inode
