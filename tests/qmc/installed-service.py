# SPDX-License-Identifier: GPL-2.0-only
"""Exercise an installed QM package on a disposable CentOS 10 machine.

Requires storage prepared for the selected userns mode, SELinux enforcing, and
a local nested test image containing /bin/sh and sleep. It restarts QM and
changes test-owned files.
"""

import argparse
import json
import pathlib
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--nested-image", required=True, help="preloaded local image; never pulled"
)
parser.add_argument(
    "--userns-mode",
    choices=("off", "required"),
    default="required",
    help="mode matching the prepared filesystem ownership (default: required)",
)
parser.add_argument(
    "--network-url",
    default="https://example.com",
    help="reachable HTTP(S) URL for the routing check",
)
args = parser.parse_args()


def run(*command, input=None, expected=0):
    """Run a bounded command and check its exit status."""
    result = subprocess.run(
        command, input=input, text=True, capture_output=True, timeout=60
    )
    assert result.returncode == expected, (
        command,
        result.returncode,
        result.stdout,
        result.stderr,
    )
    return result.stdout


def qm(*command, **kwargs):
    """Execute a command inside the installed QM environment."""
    return run("qmc", "exec", *command, **kwargs)


def stopped():
    """Stop QM and check that its network resources were removed."""
    run("systemctl", "stop", "qm.service")
    assert not pathlib.Path("/run/qm/netns").exists()
    assert not pathlib.Path("/sys/class/net/qm-veth").exists()
    rules = json.loads(run("nft", "-j", "list", "tables"))
    assert not any(
        e.get("table", {}).get("name") == "qm_launch"
        for e in rules["nftables"]
    )


assert run("getenforce").strip() == "Enforcing"
settings = json.loads(run("qmc", "inspect"))
etc_source = next(
    m["source"]
    for m in reversed(settings["mounts"])
    if m["destination"] == "/etc"
)
etc = pathlib.Path(etc_source) / "containers/systemd"
quadlet = etc / "qmc-installed-test.container"
assert not quadlet.exists()
config_dir = pathlib.Path("/etc/qmc.conf.d")
config_dir.mkdir(exist_ok=True)
userns_config = config_dir / "zz-qmc-installed-userns.conf"
failure_config = config_dir / "zz-qmc-installed-failure.conf"
assert not userns_config.exists() and not failure_config.exists()
mode = args.userns_mode
if mode == "required":
    assert all(
        "qm_root:" in pathlib.Path("/etc", name).read_text()
        for name in ("subuid", "subgid")
    )
try:
    userns_config.write_text(
        json.dumps({"userns": mode, "devices": [{"source": "/dev/zero"}]})
    )
    run("systemctl", "restart", "qm.service")
    assert run("systemctl", "is-active", "qm.service").strip() == "active"
    assert run("qmc", "inspect", "--field", "userns").strip() == mode
    # Require a local nested image so no registry access is needed.
    qm("podman", "image", "exists", args.nested_image)
    assert qm("cat", "/proc/1/comm").strip() == "systemd"
    assert (
        qm("/bin/sh", "-c", 'printf "%s\\n" "$1"', "sh", "a b") == "a b\n"
    )
    assert qm("cat", input="ignored\n") == ""
    assert qm("-i", "cat", input="qmc stdin\n") == "qmc stdin\n"
    qm("/bin/sh", "-c", "exit 37", expected=37)
    assert "qm_t" in qm("cat", "/proc/self/attr/current")
    qm("test", "-c", "/dev/zero")
    qm("/bin/sh", "-c", "touch /usr/qmc-test", expected=1)
    for path in ("/etc", "/var", "/var/tmp"):
        qm("touch", path + "/qmc-installed-marker")
        qm("rm", path + "/qmc-installed-marker")
    # DNS/hosts watchers must refresh the existing files visible inside QM.
    hosts = pathlib.Path("/etc/hosts")
    saved_hosts = hosts.read_bytes()
    try:
        with hosts.open("ab") as f:
            f.write(b"\n192.0.2.19 qmc-installed-test.invalid\n")
        deadline = time.monotonic() + 15
        while "qmc-installed-test.invalid" not in qm("cat", "/etc/hosts"):
            assert (
                time.monotonic() < deadline
            ), "hosts watcher did not update QM"
            time.sleep(0.2)
    finally:
        hosts.write_bytes(saved_hosts)
    resolv = pathlib.Path(settings["resolv-conf"])
    saved_resolv = resolv.read_bytes()
    try:
        with resolv.open("ab") as f:
            f.write(b"\n# qmc-installed-resolver-update\n")
        deadline = time.monotonic() + 15
        while "qmc-installed-resolver-update" not in qm(
            "cat", "/etc/resolv.conf"
        ):
            assert (
                time.monotonic() < deadline
            ), "resolver watcher did not update QM"
            time.sleep(0.2)
    finally:
        resolv.write_bytes(saved_resolv)
    qm(
        "curl",
        "--fail",
        "--connect-timeout",
        "10",
        "--max-time",
        "30",
        args.network_url,
    )
    qm("getent", "hosts", "example.com")
    qm("mkdir", "-p", "/etc/containers/systemd")
    qm(
        "-i", "tee", "/etc/containers/systemd/qmc-installed-test.container",
        input="[Container]\nImage=" + args.nested_image + (
            "\nPull=never\nExec=sleep infinity\n"
        )
    )
    qm("systemctl", "daemon-reload")
    qm("systemctl", "start", "qmc-installed-test.service")
    nested_status = qm(
        "systemctl", "is-active", "qmc-installed-test.service"
    )
    assert nested_status.strip() == "active"
    qm(
        "podman",
        "exec",
        "systemd-qmc-installed-test",
        "/bin/sh",
        "-c",
        "exit 23",
        expected=23,
    )
    qm("systemctl", "stop", "qmc-installed-test.service")
    quadlet.unlink()
    stopped()
    print(
        (
            'PASS installed service, exec, mounts, devices, hosts/DNS, '
            'networking, nested Quadlet and cleanup; userns='
        ) + mode,
        flush=True,
    )
    failure_config.write_text("{broken")
    run("systemctl", "start", "qm.service", expected=1)
    stopped()
    failure_config.unlink()
    run("systemctl", "reset-failed", "qm.service")
    run("systemctl", "start", "qm.service")
    assert run("systemctl", "is-active", "qm.service").strip() == "active"
    print("PASS failed-start cleanup and restart", flush=True)
finally:
    for path in (quadlet, userns_config, failure_config):
        path.unlink(missing_ok=True)
    run("systemctl", "reset-failed", "qm.service")
    run("systemctl", "restart", "qm.service")
