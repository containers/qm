# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 Alexander Larsson
# See LICENSE for the full license text.

import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest

LAUNCHER = pathlib.Path(sys.argv.pop(1)).resolve()


class SignalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qmc-signals-")
        self.addCleanup(self.temp.cleanup)
        self.runtime = pathlib.Path(self.temp.name) / "runtime"

    def signal(self, *args, env=None, umask=-1):
        return subprocess.run(
            [str(LAUNCHER), "signal", "--runtime-dir", str(self.runtime), *args],
            text=True, capture_output=True, env=env, umask=umask)

    def test_signal_before_startup_is_readable_and_idempotent(self):
        result = self.signal("network-ready", umask=0o077)
        self.assertEqual(result.returncode, 0, result.stderr)
        marker = self.runtime / "signals/network-ready"
        original = marker.stat()
        self.assertEqual(marker.read_bytes(), b"")
        self.assertEqual(stat.S_IMODE(original.st_mode), 0o644)
        self.assertEqual(stat.S_IMODE(marker.parent.stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE(self.runtime.stat().st_mode), 0o700)
        result = self.signal("network-ready")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(marker.stat(), original)
        self.assertEqual(list(marker.parent.iterdir()), [marker])

    def test_clear_is_idempotent_and_does_not_create_runtime(self):
        result = self.signal("--clear", "network-ready")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.runtime.exists())
        result = self.signal("network-ready")
        self.assertEqual(result.returncode, 0, result.stderr)
        for _ in range(2):
            result = self.signal("--clear", "network-ready")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list((self.runtime / "signals").iterdir()), [])

    def test_signals_do_not_read_launch_configuration_or_state(self):
        self.runtime.mkdir(mode=0o700)
        for name in ("config.json", "state.json"):
            (self.runtime / name).write_text("invalid configuration\n")
        result = self.signal("network-ready")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("config.json", "state.json"):
            self.assertEqual((self.runtime / name).read_text(), "invalid configuration\n")

    def test_name_validation(self):
        for name in ("", ".", "..", ".hidden", "../escape", "path/name", "two words",
                     "bad\nname", "-option", "_private", "a" * 256):
            with self.subTest(name=name):
                result = self.signal("--", name)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("invalid signal name", result.stderr)
                self.assertFalse(self.runtime.exists())
        for args in ((), ("one", "two")):
            result = self.signal(*args)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("signal requires exactly one name", result.stderr)

    def test_symlinks_are_not_followed(self):
        self.runtime.mkdir(mode=0o700)
        signals = self.runtime / "signals"
        signals.symlink_to(self.temp.name)
        result = self.signal("network-ready")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((pathlib.Path(self.temp.name) / "network-ready").exists())
        signals.unlink()
        signals.mkdir(mode=0o755)
        target = pathlib.Path(self.temp.name) / "outside"
        target.write_text("keep\n")
        (signals / "network-ready").symlink_to(target)
        result = self.signal("network-ready")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_text(), "keep\n")
        result = self.signal("--clear", "network-ready")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(target.read_text(), "keep\n")

    def test_runtime_directory_environment_and_override(self):
        environment = {**os.environ, "RUNTIME_DIRECTORY": str(self.runtime)}
        result = subprocess.run([str(LAUNCHER), "signal", "network-ready"],
                                text=True, capture_output=True, env=environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.signal("second-signal", env={**environment, "RUNTIME_DIRECTORY": "/wrong"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(path.name for path in (self.runtime / "signals").iterdir()),
                         ["network-ready", "second-signal"])


if __name__ == "__main__":
    unittest.main()
