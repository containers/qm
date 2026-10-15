# SPDX-License-Identifier: GPL-2.0-only
import os
import signal
import subprocess
import sys
import unittest

RELAY = sys.argv.pop(1)


class StdioTests(unittest.TestCase):
    def test_large_binary_streams_and_status(self):
        data = bytes(range(256)) * 8192
        command = [RELAY, sys.executable, "-c", "import os,sys; data=sys.stdin.buffer.read(); os.write(2,b'error'*10000); sys.stdout.buffer.write(data); sys.exit(37)"]
        result = subprocess.run(command, input=data, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertEqual(result.stdout, data)
        self.assertEqual(result.stderr, b"error" * 10000)

    def test_closed_stdin(self):
        result = subprocess.run([RELAY, "/bin/cat"], preexec_fn=lambda: os.close(0),
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b"")

    def test_command_closes_input(self):
        result = subprocess.run([RELAY, "/bin/true"], input=b"x" * 1048576,
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0)

    def test_signal_reaches_child(self):
        with subprocess.Popen([RELAY, sys.executable, "-u", "-c", "import time; print('ready'); time.sleep(60)"],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            self.assertEqual(process.stdout.readline(), b"ready\n")
            process.send_signal(signal.SIGTERM)
            process.communicate(timeout=5)
            self.assertEqual(process.returncode, 128 + signal.SIGTERM)


unittest.main()
