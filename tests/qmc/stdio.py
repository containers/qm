# SPDX-License-Identifier: GPL-2.0-only
"""Check non-terminal exec stream forwarding and exit status."""

import fcntl
import os
import select
import signal
import socket
import subprocess
import sys
import tempfile
import time
import tty
import unittest

RELAY = sys.argv.pop(1)


class StdioTests(unittest.TestCase):
    """Check exec byte streams, exit status and signal forwarding."""

    def test_large_binary_streams_and_status(self):
        """Check large binary streams and status."""
        data = bytes(range(256)) * 8192
        program = (
            'import os,sys; data=sys.stdin.buffer.read(); '
            "os.write(2,b'error'*10000); sys.stdout.buffer.write(data); "
            'sys.exit(37)'
        )
        command = [
            RELAY,
            "-i",
            sys.executable,
            "-c",
            (
                program
            ),
        ]
        result = subprocess.run(
            command, input=data, capture_output=True, timeout=10
        )
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertEqual(result.stdout, data)
        self.assertEqual(result.stderr, b"error" * 10000)

    def test_closed_stdin(self):
        """Check closed stdin."""
        result = subprocess.run(
            [RELAY, "-i", "/bin/cat"],
            preexec_fn=lambda: os.close(0),
            capture_output=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b"")

    def test_command_closes_input(self):
        """Check command closes input."""
        result = subprocess.run(
            [RELAY, "-i", "/bin/true"],
            input=b"x" * 1048576,
            capture_output=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)

    def test_default_leaves_input_unread(self):
        """Give the child EOF and preserve the caller's input and output."""
        source, writer = os.pipe()
        self.addCleanup(os.close, source)
        self.addCleanup(os.close, writer)
        os.write(writer, b"caller input")
        program = (
            "import sys; assert sys.stdin.read() == ''; "
            "print('output'); print('error', file=sys.stderr)"
        )
        result = subprocess.run(
            [RELAY, sys.executable, "-c", program],
            stdin=source,
            capture_output=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b"output\n")
        self.assertEqual(result.stderr, b"error\n")
        self.assertEqual(os.read(source, 12), b"caller input")

    def test_regular_file_offset_and_append(self):
        """Preserve shared file offsets and append when relaying output."""
        with tempfile.TemporaryFile() as output:
            output.write(b"prefix\n")
            output.flush()
            flags = fcntl.fcntl(output, fcntl.F_GETFL)
            fcntl.fcntl(output, fcntl.F_SETFL, flags | os.O_APPEND)
            output.seek(0)
            result = subprocess.run(
                [RELAY, "/bin/echo", "suffix"],
                stdout=output,
                stderr=subprocess.PIPE,
                timeout=5,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.tell(), 14)
            output.seek(0)
            self.assertEqual(output.read(), b"prefix\nsuffix\n")

    def test_pty_output(self):
        """Relay to PTY slaves and reject masters, preserving caller flags."""
        for use_master in (False, True):
            for stream in (1, 2):
                for blocking in (False, True):
                    with self.subTest(master=use_master, stream=stream,
                                      blocking=blocking):
                        master, slave = os.openpty()
                        try:
                            tty.setraw(slave)
                            writer, reader = ((master, slave) if use_master
                                              else (slave, master))
                            os.set_blocking(writer, blocking)
                            flags = fcntl.fcntl(writer, fcntl.F_GETFL)
                            data = bytes(range(256)) * 4
                            program = (
                                f"import os; os.write({stream}, {data!r})"
                            )
                            outputs = {"stdout": subprocess.PIPE,
                                       "stderr": subprocess.PIPE}
                            outputs["stdout" if stream == 1 else "stderr"] = (
                                writer
                            )
                            result = subprocess.run(
                                [RELAY, sys.executable, "-c", program],
                                timeout=5,
                                **outputs,
                            )
                            self.assertEqual(
                                fcntl.fcntl(writer, fcntl.F_GETFL), flags
                            )
                            if use_master:
                                self.assertEqual(result.returncode, 1)
                                error = result.stderr
                                if stream == 2:
                                    self.assertTrue(select.select(
                                        [reader], [], [], 5
                                    )[0], "missing PTY master error")
                                    error = os.read(reader, 4096)
                                self.assertIn(
                                    b"PTY masters are not supported", error
                                )
                                continue
                            self.assertEqual(result.returncode, 0,
                                             result.stderr)
                            received = bytearray()
                            deadline = time.monotonic() + 5
                            while len(received) < len(data):
                                self.assertTrue(select.select(
                                    [reader], [], [],
                                    max(0, deadline - time.monotonic()),
                                )[0], "output did not reach the original PTY")
                                received.extend(os.read(reader, len(data)))
                            self.assertEqual(received, data)
                        finally:
                            os.close(master)
                            os.close(slave)

    def test_signal_with_blocked_output(self):
        """Forward termination even when a pipe or journal socket is full."""
        for use_socket in (False, True):
            for stream in (1, 2):
                with self.subTest(socket=use_socket, stream=stream):
                    self.check_blocked_output(use_socket, stream)

    def check_blocked_output(self, use_socket, stream):
        """Fill the caller's output and cancel a child writing to it."""
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
        program = (
            "import os; print('ready', flush=True, "
            f"file=os.fdopen({3 - stream}, 'w', closefd=False)); "
            f"data=b'x'*4096\nwhile True: os.write({stream}, data)"
        )
        outputs = {"stdout": descriptor, "stderr": subprocess.PIPE}
        if stream == 2:
            outputs = {"stdout": subprocess.PIPE, "stderr": descriptor}
        with subprocess.Popen(
            [RELAY, sys.executable, "-c", program], **outputs
        ) as process:
            try:
                ready = process.stderr if stream == 1 else process.stdout
                self.assertTrue(select.select([ready], [], [], 5)[0])
                self.assertEqual(ready.readline(), b"ready\n")
                # Let the relay reach the full output before sending a signal.
                time.sleep(0.1)
                self.assertEqual(fcntl.fcntl(descriptor, fcntl.F_GETFL), flags)
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
                self.assertEqual(process.returncode, 128 + signal.SIGTERM)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)

    def test_signal_reaches_child(self):
        """Check signal reaches child."""
        program = (
            "import time; print('ready'); time.sleep(60)"
        )
        with subprocess.Popen(
            [
                RELAY,
                sys.executable,
                "-u",
                "-c",
                program,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as process:
            self.assertEqual(process.stdout.readline(), b"ready\n")
            process.send_signal(signal.SIGTERM)
            process.communicate(timeout=5)
            self.assertEqual(process.returncode, 128 + signal.SIGTERM)


unittest.main()
