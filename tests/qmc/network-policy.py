# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 Alexander Larsson
# See LICENSE for the full license text.

"""Check real packet filtering and NAT in private network namespaces."""

import json
import pathlib
import select
import shutil
import subprocess
import sys
import tempfile
import unittest

HELPER = pathlib.Path(sys.argv[1]).resolve()
PEER = "172.30.20.2"
SOURCES = (PEER, "172.30.20.3", "198.51.100.2")
PORT = "49001"
RECEIVER = """
import json
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('0.0.0.0', 49001))
s.settimeout(1)
print('READY', flush=True)
try:
    data, peer = s.recvfrom(128)
    print(json.dumps([data.decode(), peer[0]]), flush=True)
except socket.timeout:
    print('null', flush=True)
"""
SENDER = """
import socket
import sys
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind((sys.argv[1], 0))
s.sendto(b'qm-network-policy', (sys.argv[2], 49001))
"""


def run(*args):
    """Run a bounded setup or observation command."""
    result = subprocess.run(
        args, check=False, text=True, capture_output=True, timeout=10
    )
    if result.returncode:
        raise RuntimeError(f"{args}: {result.stdout}{result.stderr}")
    return result.stdout


def make_uplink(namespace, interface, host, remote):
    """Connect another network namespace to the isolated test host."""
    run("ip", "netns", "add", namespace)
    run(
        "ip", "link", "add", interface, "type", "veth", "peer", "name",
        "eth0", "netns", namespace,
    )
    run("ip", "addr", "add", f"{host}/24", "dev", interface)
    run("ip", "link", "set", interface, "up")
    command = ("ip", "netns", "exec", namespace)
    run(*command, "ip", "addr", "add", f"{remote}/24", "dev", "eth0")
    run(*command, "ip", "link", "set", "eth0", "up")
    run(*command, "ip", "link", "set", "lo", "up")
    # Permit one-way observation even when this namespace has no return route
    # to the packet's source. Kernel defaults may enable reverse-path checks.
    for interface_name in ("all", "eth0"):
        run(*command, "sysctl", "-w",
            f"net.ipv4.conf.{interface_name}.rp_filter=0")
    return command


class NetworkPolicyTests(unittest.TestCase):
    """Exercise the production rules installed by the network fixture."""

    @classmethod
    def setUpClass(cls):
        """Create QM, an upstream, and an unrelated network interface."""
        run("mount", "--make-rprivate", "/")
        run("mount", "-t", "tmpfs", "tmpfs", "/run")
        pathlib.Path("/proc/sys/net/ipv4/ip_forward").write_text("1\n")
        for interface in ("all", "default"):
            pathlib.Path(
                f"/proc/sys/net/ipv4/conf/{interface}/rp_filter"
            ).write_text("0\n")
        run("ip", "link", "set", "lo", "up")
        cls.upstream = make_uplink(
            "policy-upstream", "policy-uplink", "192.0.2.1", "192.0.2.2"
        )
        # The upstream deliberately has no return route to the QM subnet.
        run("ip", "route", "add", "default", "via", "192.0.2.2")
        cls.other = make_uplink(
            "policy-other", "policy-other", "198.18.0.1", "198.18.0.2"
        )
        run(*cls.other, "ip", "route", "add", "default", "via", "198.18.0.1")
        run(*cls.other, "ip", "addr", "add", f"{PEER}/32", "dev", "eth0")
        pathlib.Path(
            "/proc/sys/net/ipv4/conf/policy-other/rp_filter"
        ).write_text("2\n")

        temporary = tempfile.TemporaryDirectory(prefix="qm-network-policy-")
        cls.addClassCleanup(temporary.cleanup)
        runtime = pathlib.Path(temporary.name)
        # The fixture bind-mounts its namespace here, even on setup failure.
        cls.addClassCleanup(
            subprocess.run, ["umount", str(runtime / "netns")],
            capture_output=True, check=False,
        )
        run(str(HELPER), str(runtime))
        cls.qm = ("nsenter", f"--net={runtime / 'netns'}")
        # Match qmc's loose reverse-path filtering. Neither it nor subnet-based
        # source checks should mask the behavior of the exact peer-IP check.
        pathlib.Path(
            "/proc/sys/net/ipv4/conf/test-veth/rp_filter"
        ).write_text("2\n")
        for source in SOURCES[1:]:
            run(*cls.qm, "ip", "addr", "add", f"{source}/32", "dev", "test0")

        # Count packets before the production source check. Negative tests must
        # prove that a packet reached the host, not just that no reply arrived.
        run("nft", "add", "table", "ip", "network_observer")
        run("nft", "add", "counter", "ip", "network_observer", "seen")
        run(
            "nft", "add", "chain", "ip", "network_observer", "prerouting",
            "{ type filter hook prerouting priority raw; policy accept; }",
        )
        run(
            "nft", "add", "rule", "ip", "network_observer", "prerouting",
            f'iifname "test-veth" udp dport {PORT} counter name seen',
        )

    def seen(self):
        """Read the count of QM packets arriving before source validation."""
        objects = json.loads(run(
            "nft", "-j", "list", "counter", "ip", "network_observer", "seen"
        ))["nftables"]
        return next(o["counter"]["packets"] for o in objects if "counter" in o)

    def receive_packet(self, sender, source, destination, receiver=()):
        """Observe the source at the destination, without needing replies."""
        listener = subprocess.Popen(
            [*receiver, sys.executable, "-u", "-c", RECEIVER],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            self.assertTrue(select.select([listener.stdout], [], [], 5)[0])
            self.assertEqual(listener.stdout.readline(), "READY\n")
            run(*sender, sys.executable, "-c", SENDER, source, destination)
            stdout, stderr = listener.communicate(timeout=5)
            self.assertEqual(listener.returncode, 0, stderr)
            packet = json.loads(stdout)
            if packet is not None:
                self.assertEqual(packet[0], "qm-network-policy")
                return packet[1]
            return None
        finally:
            if listener.poll() is None:
                listener.kill()
            listener.communicate(timeout=5)

    def check_qm_sources(self, destination, receiver, expected_source):
        """Reject spoofs inside and outside the peer's subnet."""
        for source in SOURCES:
            with self.subTest(source=source):
                before = self.seen()
                observed = self.receive_packet(
                    self.qm, source, destination, receiver
                )
                self.assertEqual(self.seen(), before + 1)
                self.assertEqual(
                    observed, expected_source if source == PEER else None
                )

    def test_qm_sources_to_host(self):
        """Host-bound traffic must pass the same source check as forwarding."""
        self.check_qm_sources("172.30.20.1", (), PEER)

    def test_qm_sources_forwarded(self):
        """Only the peer may reach the upstream and be masqueraded."""
        self.check_qm_sources("192.0.2.2", self.upstream, "192.0.2.1")

    def test_unrelated_ingress_is_not_masqueraded(self):
        """A matching source IP on another interface must remain unchanged."""
        self.assertEqual(self.receive_packet(
            self.other, PEER, "192.0.2.2", self.upstream
        ), PEER)

    def test_host_traffic_is_not_masqueraded(self):
        """Host traffic with the peer's source IP stays unchanged."""
        run("ip", "addr", "add", f"{PEER}/32", "dev", "lo")
        try:
            self.assertEqual(self.receive_packet(
                (), PEER, "192.0.2.2", self.upstream
            ), PEER)
        finally:
            run("ip", "addr", "del", f"{PEER}/32", "dev", "lo")


if __name__ == "__main__":
    if "--isolated" not in sys.argv:
        for tool in (
            "unshare", "mount", "umount", "nsenter", "ip", "nft", "sysctl"
        ):
            if not shutil.which(tool):
                print(f"SKIP network-policy: {tool} is unavailable")
                sys.exit(77)
        isolation = (
            "unshare", "--user", "--map-root-user", "--mount", "--net"
        )
        probe = subprocess.run(
            [*isolation, "true"], capture_output=True, text=True, timeout=10
        )
        if probe.returncode:
            print(f"SKIP network-policy: {probe.stderr.strip()}")
            sys.exit(77)
        sys.exit(subprocess.run([
            *isolation, sys.executable, __file__, str(HELPER), "--isolated"
        ], check=False).returncode)
    unittest.main(argv=[sys.argv[0]], verbosity=2)
