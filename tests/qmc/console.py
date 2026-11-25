# SPDX-License-Identifier: GPL-2.0-only
"""Check console forwarding and shutdown under host output backpressure."""

import fcntl
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import tempfile
import time
import tty
import unittest

RELAY = sys.argv.pop(1)
INIT = """
import array
import os
import socket
import sys

path, master, slave, mode = sys.argv[1:]
master, slave = int(master), int(slave)
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
    connection.connect(path)
    connection.sendmsg([b'x'], [
        (socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', [master]))
    ])
os.close(master)
if mode == 'flood':
    os.write(slave, b'x')
print('ready', file=sys.stderr, flush=True)
data = bytes(range(256)) * 4096
if mode == 'flood':
    while True:
        os.write(slave, data)
else:
    while data:
        data = data[os.write(slave, data):]
"""


class ConsoleTests(unittest.TestCase):
    """Exercise the real relay with a PTY from a synthetic container init."""

    def stop_process(self, process):
        """Clean up a failed fixture without leaving its relay running."""
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()

    def start_console(self, output, mode):
        """Start the relay and pass it a PTY from a separate init process."""
        directory = tempfile.TemporaryDirectory(prefix="qm-console-")
        self.addCleanup(directory.cleanup)
        path = str(Path(directory.name) / "console.sock")
        relay = subprocess.Popen(
            [RELAY, path], stdout=output, stderr=subprocess.PIPE
        )
        self.addCleanup(self.stop_process, relay)
        self.assertTrue(select.select([relay.stderr], [], [], 5)[0])
        self.assertEqual(relay.stderr.readline(), b"ready\n")
        master, slave = os.openpty()
        try:
            tty.setraw(slave)
            init = subprocess.Popen(
                [
                    sys.executable, "-c", INIT, path,
                    str(master), str(slave), mode,
                ],
                pass_fds=(master, slave),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        finally:
            os.close(master)
            os.close(slave)
        self.addCleanup(self.stop_process, init)
        self.assertTrue(select.select([init.stderr], [], [], 5)[0])
        self.assertEqual(init.stderr.readline(), b"ready\n")
        return relay, init

    def test_drains_console(self):
        """Preserve all final output when the caller continues reading."""
        relay, init = self.start_console(subprocess.PIPE, "drain")
        output, errors = relay.communicate(timeout=5)
        self.assertEqual(relay.returncode, 0, errors)
        self.assertEqual(init.wait(timeout=5), 0)
        self.assertEqual(output, bytes(range(256)) * 4096)

    def test_pty_slave_output(self):
        """Drain to the original PTY slave without changing caller flags."""
        for blocking in (False, True):
            with self.subTest(blocking=blocking):
                master, slave = os.openpty()
                self.addCleanup(os.close, master)
                self.addCleanup(os.close, slave)
                tty.setraw(slave)
                os.set_blocking(slave, blocking)
                flags = fcntl.fcntl(slave, fcntl.F_GETFL)
                relay, init = self.start_console(slave, "drain")
                expected = bytes(range(256)) * 4096
                output = bytearray()
                deadline = time.monotonic() + 5
                while len(output) < len(expected):
                    self.assertTrue(select.select(
                        [master], [], [],
                        max(0, deadline - time.monotonic()),
                    )[0], "output did not reach the original PTY")
                    chunk = os.read(master, 65536)
                    self.assertTrue(chunk)
                    output.extend(chunk)
                relay.wait(timeout=5)
                self.assertEqual(relay.returncode, 0, relay.stderr.read())
                self.assertEqual(init.wait(timeout=5), 0)
                self.assertEqual(output, expected)
                self.assertEqual(fcntl.fcntl(slave, fcntl.F_GETFL), flags)

    def test_pty_master_output(self):
        """Reject PTY masters without changing shared caller flags."""
        for blocking in (False, True):
            with self.subTest(blocking=blocking):
                master, slave = os.openpty()
                self.addCleanup(os.close, master)
                self.addCleanup(os.close, slave)
                os.set_blocking(master, blocking)
                flags = fcntl.fcntl(master, fcntl.F_GETFL)
                relay, _ = self.start_console(master, "drain")
                _, errors = relay.communicate(timeout=5)
                self.assertEqual(relay.returncode, 1)
                self.assertIn(b"PTY masters are not supported", errors)
                self.assertEqual(fcntl.fcntl(master, fcntl.F_GETFL), flags)

    def test_init_exit_with_blocked_output(self):
        """Exit after init dies even when a pipe or journal socket is full."""
        for use_socket in (False, True):
            with self.subTest(socket=use_socket):
                self.check_blocked_output(use_socket)

    def check_blocked_output(self, use_socket):
        """Queue PTY data before killing init with a full sink."""
        if use_socket:
            reader, writer = socket.socketpair()
            self.addCleanup(reader.close)
            self.addCleanup(writer.close)
            descriptor = writer.fileno()
        else:
            reader, descriptor = os.pipe()
            self.addCleanup(os.close, reader)
            self.addCleanup(os.close, descriptor)
        os.set_blocking(descriptor, False)
        try:
            while True:
                os.write(descriptor, b"x" * 4096)
        except BlockingIOError:
            pass
        os.set_blocking(descriptor, True)
        flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
        # Init acknowledges readiness only after queuing PTY output.
        relay, init = self.start_console(descriptor, "flood")
        self.assertIsNone(relay.poll())
        self.assertEqual(fcntl.fcntl(descriptor, fcntl.F_GETFL), flags)
        init.terminate()
        init.wait(timeout=5)
        relay.wait(timeout=3)
        self.assertEqual(relay.returncode, 0, relay.stderr.read())
        self.assertEqual(fcntl.fcntl(descriptor, fcntl.F_GETFL), flags)


unittest.main()
