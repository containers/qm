# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 Alexander Larsson
# See LICENSE for the full license text.

"""Check locking across state replacement and concurrent commands."""

import fcntl
import json
import os
import pathlib
import select
import subprocess
import sys
import tempfile
import time
import unittest

LAUNCHER = pathlib.Path(sys.argv[1]).resolve()
SOURCE = pathlib.Path(sys.argv[2]).resolve()
sys.argv = sys.argv[:1]


class LifecycleTests(unittest.TestCase):
    """Exercise concurrent commands without changing mounts or networking."""

    def setUp(self):
        """Create a private runtime and a minimal preparation configuration."""
        self.temp = tempfile.TemporaryDirectory(prefix="qm-lifecycle-")
        self.addCleanup(self.temp.cleanup)
        self.directory = pathlib.Path(self.temp.name)
        self.runtime = self.directory / "runtime"
        self.runtime.mkdir(mode=0o700)
        self.lock = self.runtime / ".lock"
        self.state = self.runtime / "state.json"
        self.config = self.directory / "qmc.conf"
        self.config.write_text(
            json.dumps(
                {
                    "base-config": str(SOURCE / "data/qm.json"),
                    "rootfs": "/unused",
                    "seccomp": str(SOURCE / "tests/qmc/seccomp-no-rt.json"),
                    "userns": "off",
                }
            )
        )

    def start(self, command="cleanup", *args):
        """Start a command and arrange to stop it after failed assertions."""
        process = subprocess.Popen(
            [
                str(LAUNCHER),
                command,
                "--runtime-dir",
                str(self.runtime),
                "--verbose",
                *args,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.addCleanup(self.stop, process)
        return process

    def stop(self, process):
        """Reap the child and close its pipes on every test exit path."""
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)
        process.stdout.close()
        process.stderr.close()

    def wait_for_lock(self, process):
        """Wait until the child has opened the stable lock."""
        output = b""
        deadline = time.monotonic() + 5
        while b"Locking runtime lifecycle" not in output:
            remaining = deadline - time.monotonic()
            self.assertGreater(remaining, 0, output)
            ready, _, _ = select.select([process.stderr], [], [], remaining)
            self.assertTrue(ready, output)
            chunk = os.read(process.stderr.fileno(), 4096)
            self.assertTrue(chunk, output)
            output += chunk
        self.assert_blocked(process)

    def assert_blocked(self, process):
        """Check the command waits while another caller holds a lock."""
        with self.assertRaises(subprocess.TimeoutExpired):
            process.communicate(timeout=0.1)

    def assert_success(self, process):
        """Check the command completes once its lock is available."""
        stdout, stderr = process.communicate(timeout=5)
        self.assertEqual(process.returncode, 0, (stdout, stderr))

    def prepare(self):
        """Create a bundle using the normal preparation command."""
        process = self.start(
            "launch", "--prepare-only", "--config", str(self.config)
        )
        self.assert_success(process)

    def test_cleanup_after_atomic_state_replacement(self):
        """Check cleanup uses current state after waiting for the lock."""
        old_bundle = self.directory / "old-bundle"
        new_bundle = self.directory / "new-bundle"
        for bundle in (old_bundle, new_bundle):
            bundle.mkdir()
            (bundle / "marker").touch()
        self.state.write_text(
            json.dumps(
                {
                    "version": 1,
                    "bundle": str(old_bundle),
                }
            )
        )
        replacement = self.runtime / "replacement.json"
        replacement.write_text(
            json.dumps(
                {
                    "version": 1,
                    "bundle": str(new_bundle),
                }
            )
        )
        with self.lock.open("a") as lifecycle, self.state.open() as old:
            fcntl.flock(lifecycle, fcntl.LOCK_EX)
            fcntl.flock(old, fcntl.LOCK_EX)
            process = self.start()
            self.wait_for_lock(process)
            with replacement.open() as new:
                fcntl.flock(new, fcntl.LOCK_SH)
                replacement.replace(self.state)
                fcntl.flock(old, fcntl.LOCK_UN)
                self.assert_blocked(process)
                self.assertTrue(self.state.exists())
                self.assertTrue((new_bundle / "marker").exists())
            fcntl.flock(lifecycle, fcntl.LOCK_UN)
            self.assert_success(process)
        self.assertTrue((old_bundle / "marker").exists())
        self.assertFalse((new_bundle / "marker").exists())
        self.assertFalse(self.state.exists())

    def test_overlapping_cleanups(self):
        """Check overlapping cleanups both succeed after state removal."""
        self.state.write_text(
            json.dumps(
                {
                    "version": 1,
                    "bundle": str(self.runtime),
                }
            )
        )
        with self.lock.open("a") as lifecycle, self.state.open() as state_file:
            original = self.lock.stat()
            fcntl.flock(lifecycle, fcntl.LOCK_EX)
            fcntl.flock(state_file, fcntl.LOCK_EX)
            processes = [self.start(), self.start()]
            for process in processes:
                self.wait_for_lock(process)
            fcntl.flock(state_file, fcntl.LOCK_UN)
            fcntl.flock(lifecycle, fcntl.LOCK_UN)
            for process in processes:
                self.assert_success(process)
        self.assertEqual(list(self.runtime.iterdir()), [self.lock])
        self.assertEqual(self.lock.stat().st_ino, original.st_ino)
        self.assert_success(self.start())
        self.assertEqual(self.lock.stat().st_ino, original.st_ino)

    def test_prepare_waits_before_writing_bundle(self):
        """Preparation waits before rewriting protected bundle files."""
        self.prepare()
        original = self.lock.stat()
        bundle = self.runtime / "config.json"
        before = bundle.read_bytes()
        config = json.loads(self.config.read_text())
        config["hostname"] = "replacement"
        self.config.write_text(json.dumps(config))
        with self.lock.open("a") as lifecycle:
            fcntl.flock(lifecycle, fcntl.LOCK_SH)
            process = self.start(
                "launch", "--prepare-only", "--config", str(self.config)
            )
            self.wait_for_lock(process)
            self.assertEqual(bundle.read_bytes(), before)
            fcntl.flock(lifecycle, fcntl.LOCK_UN)
            self.assert_success(process)
        self.assertEqual(
            json.loads(bundle.read_text())["hostname"], "replacement"
        )
        self.assertEqual(self.lock.stat().st_ino, original.st_ino)

    def test_prepare_checks_state_after_locking(self):
        """The state conflict check uses state observed under the lock."""
        self.prepare()
        for create in (False, True):
            with self.subTest(create=create), self.lock.open("a") as lifecycle:
                if not create:
                    self.state.write_text('{"version":1}')
                fcntl.flock(lifecycle, fcntl.LOCK_EX)
                process = self.start(
                    "launch", "--prepare-only", "--config", str(self.config)
                )
                self.wait_for_lock(process)
                if create:
                    self.state.write_text('{"version":1}')
                else:
                    self.state.unlink()
                fcntl.flock(lifecycle, fcntl.LOCK_UN)
                if create:
                    _, stderr = process.communicate(timeout=5)
                    self.assertNotEqual(process.returncode, 0)
                    self.assertIn(b"cleanup state already exists", stderr)
                else:
                    self.assert_success(process)

    def test_cleanup_without_runtime(self):
        """Cleanup does not create a missing runtime just to lock it."""
        self.runtime.rmdir()
        self.assert_success(self.start())
        self.assertFalse(self.runtime.exists())


unittest.main()
