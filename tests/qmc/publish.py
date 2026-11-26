# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 Alexander Larsson
# See LICENSE for the full license text.

"""Exercise published ports in private user, mount and network namespaces."""

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HELPER = str(pathlib.Path(sys.argv.pop(1)).resolve())
LAUNCHER = str(pathlib.Path(sys.argv.pop(1)).resolve())

SERVER = r"""
import select, socket, sys
sockets = []
for protocol, port in [('tcp', 18080), ('tcp', 18081), ('tcp', 18082),
                       ('udp', 18080), ('udp', 18053)]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM if protocol == 'tcp'
                      else socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', port))
    if protocol == 'tcp':
        s.listen()
    sockets.append(s)
print('READY', flush=True)
while True:
    for s in select.select(sockets, [], [])[0]:
        if s.type == socket.SOCK_STREAM:
            c, peer = s.accept()
            with c:
                c.sendall(f'{s.getsockname()[1]} {peer[0]}'.encode())
        else:
            data, peer = s.recvfrom(1024)
            s.sendto(f'{s.getsockname()[1]} {peer[0]}'.encode(), peer)
"""

CLIENT = r"""
import socket, sys
protocol, address, port = sys.argv[1:]
with socket.socket(socket.AF_INET, socket.SOCK_STREAM if protocol == 'tcp'
                   else socket.SOCK_DGRAM) as s:
    s.settimeout(1)
    s.connect((address, int(port)))
    if protocol == 'udp':
        s.send(b'hello')
    print(s.recv(1024).decode())
"""


def run(*args):
    """Run a command with a deadline and report failures."""
    return subprocess.run(
        args, check=True, text=True, capture_output=True, timeout=10
    ).stdout


class PublishTests(unittest.TestCase):
    """Check packet forwarding and teardown using actual kernel networking."""

    @classmethod
    def setUpClass(cls):
        """Set up QM and a remote client inside private namespaces."""
        cls.temp = tempfile.TemporaryDirectory(prefix="qmc-publish-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.directory = pathlib.Path(cls.temp.name)
        run("mount", "--make-rprivate", "/")
        run("ip", "link", "set", "lo", "up")
        pathlib.Path("/proc/sys/net/ipv4/ip_forward").write_text("1\n")
        cls.remote = subprocess.Popen(["unshare", "--net", "sleep", "60"])
        cls.addClassCleanup(cls.remote.wait, timeout=5)
        cls.addClassCleanup(cls.remote.terminate)
        # Wait for unshare before moving the remote veth into its namespace.
        host_ns = pathlib.Path("/proc/self/ns/net").readlink()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            remote_ns = pathlib.Path(f"/proc/{cls.remote.pid}/ns/net")
            if remote_ns.readlink() != host_ns:
                break
            time.sleep(0.005)
        else:
            raise RuntimeError("remote namespace did not appear")
        cls.remote_ns = f"/proc/{cls.remote.pid}/ns/net"
        run(
            "ip",
            "link",
            "add",
            "remote0",
            "type",
            "veth",
            "peer",
            "name",
            "remote1",
            "netns",
            str(cls.remote.pid),
        )
        run("ip", "addr", "add", "192.0.2.1/24", "dev", "remote0")
        run("ip", "link", "set", "remote0", "up")
        cls.in_ns(
            cls.remote_ns,
            "ip",
            "addr",
            "add",
            "192.0.2.2/24",
            "dev",
            "remote1",
        )
        cls.in_ns(cls.remote_ns, "ip", "link", "set", "remote1", "up")
        cls.in_ns(
            cls.remote_ns, "ip", "route", "add", "default", "via", "192.0.2.1"
        )
        config = cls.directory / "ports.conf"
        config.write_text(
            json.dumps(
                {
                    "publish-ports": [
                        "8080:18080",
                        "8080:18080/udp",
                        "127.0.0.1:8081:18081",
                        "192.0.2.1:8082:18082",
                        "9090-9092:18080-18082",
                        "127.0.0.1:5353:18053/udp",
                        "9999:9999/sctp",
                    ]
                }
            )
        )
        cls.runtime = cls.directory / "runtime"
        cls.runtime.mkdir(mode=0o700)
        cls.addClassCleanup(
            run, LAUNCHER, "cleanup", "--runtime-dir", str(cls.runtime)
        )
        run(HELPER, str(cls.runtime), "--config", str(config))
        cls.qm_ns = str(cls.runtime / "netns")
        cls.server = subprocess.Popen(
            [
                "nsenter",
                f"--net={cls.qm_ns}",
                sys.executable,
                "-u",
                "-c",
                SERVER,
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        cls.addClassCleanup(cls.server.communicate, timeout=5)
        cls.addClassCleanup(cls.server.terminate)
        if cls.server.stdout.readline() != "READY\n":
            raise RuntimeError(cls.server.stderr.read())

    @classmethod
    def in_ns(cls, namespace, *args):
        """Run a command in one of the fixture network namespaces."""
        return run("nsenter", f"--net={namespace}", *args)

    def connect(self, address, port, protocol="tcp", namespace=None):
        """Return the responding service port and observed client address."""
        command = [sys.executable, "-c", CLIENT, protocol, address, str(port)]
        return (
            self.in_ns(namespace, *command) if namespace else run(*command)
        ).strip()

    def test_host_access_and_ranges(self):
        """Localhost and host interface addresses preserve range offsets."""
        for address in ("127.0.0.1", "192.0.2.1", "172.30.20.1"):
            for port in range(9090, 9093):
                with self.subTest(address=address, port=port):
                    self.assertTrue(
                        self.connect(address, port).startswith(
                            f"{18080 + port - 9090} "
                        )
                    )
        self.assertEqual(self.connect("127.0.0.1", 8081), "18081 172.30.20.1")
        self.assertEqual(
            self.connect("127.0.0.1", 5353, "udp"), "18053 172.30.20.1"
        )

    def test_remote_access_and_source_address(self):
        """Remote TCP and UDP traffic retains the original client address."""
        for protocol in ("tcp", "udp"):
            self.assertEqual(
                self.connect("192.0.2.1", 8080, protocol, self.remote_ns),
                "18080 192.0.2.2",
            )
        self.assertEqual(
            self.connect("192.0.2.1", 8082, namespace=self.remote_ns),
            "18082 192.0.2.2",
        )
        for offset in range(3):
            self.assertEqual(
                self.connect(
                    "192.0.2.1", 9090 + offset, namespace=self.remote_ns
                ),
                f"{18080 + offset} 192.0.2.2",
            )

    def test_restricted_bindings(self):
        """Bindings match only their configured address, including loopback."""
        for address, port, protocol, namespace in (
            ("192.0.2.1", 8081, "tcp", self.remote_ns),
            ("172.30.20.1", 8081, "tcp", None),
            ("127.0.0.2", 8081, "tcp", None),
            ("127.0.0.1", 8082, "tcp", None),
            ("192.0.2.1", 5353, "udp", self.remote_ns),
            ("127.0.0.1", 8080, "tcp", self.remote_ns),
        ):
            with self.subTest(address=address, port=port, namespace=namespace):
                with self.assertRaises(subprocess.CalledProcessError):
                    self.connect(address, port, protocol, namespace)

    def test_hairpin(self):
        """QM reaches itself using a published host port."""
        for protocol in ("tcp", "udp"):
            self.assertEqual(
                self.connect("192.0.2.1", 8080, protocol, self.qm_ns),
                "18080 172.30.20.1",
            )

    def test_unrelated_destinations(self):
        """Wildcard publishing does not rewrite traffic to other machines."""
        with self.assertRaises(subprocess.CalledProcessError):
            self.connect("192.0.2.2", 8080)
        with self.assertRaises(subprocess.CalledProcessError):
            self.connect("192.0.2.2", 8080, namespace=self.qm_ns)

    def test_z_cleanup(self):
        """Deleting saved network resources also removes published ports."""
        self.server.terminate()
        self.server.communicate(timeout=5)
        run("nft", "add", "table", "ip", "unrelated")
        run(LAUNCHER, "cleanup", "--runtime-dir", str(self.runtime))
        run(LAUNCHER, "cleanup", "--runtime-dir", str(self.runtime))
        self.assertNotIn("test_network", run("nft", "list", "tables"))
        self.assertIn("unrelated", run("nft", "list", "tables"))
        self.assertFalse((self.runtime / "state.json").exists())
        self.assertFalse((self.runtime / "netns").exists())
        with self.assertRaises(subprocess.CalledProcessError):
            self.connect("127.0.0.1", 8080)


if __name__ == "__main__":
    if "--isolated" in sys.argv:
        sys.argv.remove("--isolated")
        unittest.main()
    else:
        required = ("unshare", "nsenter", "ip", "nft", "mount")
        if any(shutil.which(command) is None for command in required):
            print("SKIP: network test tools unavailable")
            sys.exit(77)
        wrapper = ["unshare", "--user", "--map-root-user", "--mount", "--net"]
        probe = subprocess.run(
            [*wrapper, "ip", "link", "set", "lo", "up"],
            capture_output=True, timeout=10,
        )
        if probe.returncode:
            print("SKIP: private user/mount/network namespaces unavailable")
            sys.exit(77)
        sys.exit(
            subprocess.run(
                [
                    *wrapper,
                    sys.executable,
                    __file__,
                    HELPER,
                    LAUNCHER,
                    "--isolated",
                ],
                timeout=50,
            ).returncode
        )
