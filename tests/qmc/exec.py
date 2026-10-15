# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 Alexander Larsson
# See LICENSE for the full license text.

"""Check exec arguments, terminal handling and runtime isolation."""

import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

LAUNCHER = pathlib.Path(sys.argv[1]).resolve()
PRIVATE_CRUN = os.environ.get("QM_TEST_PRIVATE_CRUN") == "1"
sys.argv = sys.argv[:1]


class ExecTests(unittest.TestCase):
    """Check exec dispatch without modifying an existing runtime."""

    def setUp(self):
        """Create an isolated fixture for each test."""
        self.temp = tempfile.TemporaryDirectory(prefix="qm-exec-")
        self.addCleanup(self.temp.cleanup)
        self.directory = pathlib.Path(self.temp.name)
        self.runtime = self.directory / "runtime"
        state = self.runtime / "crun/qm"
        state.mkdir(parents=True)
        for path in (
            self.runtime / "config.json",
            self.runtime / "netns",
            state / "status",
        ):
            path.write_text("existing runtime state\n")
        self.crun = self.directory / "crun"
        self.crun.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            "print(json.dumps({'argv': sys.argv[1:], "
            "'stdin': None if os.isatty(0) else sys.stdin.read()}))\n"
            "sys.exit(23)\n"
        )
        self.crun.chmod(0o755)
        if PRIVATE_CRUN:
            subprocess.run(
                ["mount", "--bind", str(self.crun), "/usr/bin/crun"],
                check=True,
            )
            self.addCleanup(
                subprocess.run, ["umount", "/usr/bin/crun"], check=True
            )

    def command(self, command, *args):
        """Build a launcher command for the test runtime."""
        return [
            str(LAUNCHER),
            command,
            "--runtime-dir",
            str(self.runtime),
            *args,
        ]

    @unittest.skipUnless(
        PRIVATE_CRUN, "requires the smoke test's private crun mount"
    )
    def test_exec_arguments_stdio_and_status(self):
        """Check exec arguments stdio and status."""
        arguments = [
            "/bin/bash",
            "-c",
            "printf '%s' \"$1\"",
            "--",
            "two words",
            "--runtime-dir",
            "relative",
            "--help",
            "-i",
            "-t",
        ]
        for options in ([], ["-i"], ["--interactive"]):
            with self.subTest(options=options):
                result = subprocess.run(
                    self.command("exec", *options, *arguments),
                    input="piped input\n",
                    text=True,
                    capture_output=True,
                    timeout=5,
                )
                self.assertEqual(result.returncode, 23, result.stderr)
                output = json.loads(result.stdout)
                self.assertEqual(
                    output["argv"],
                    [
                        "--root",
                        str(self.runtime / "crun"),
                        "--cgroup-manager=cgroupfs",
                        "exec",
                        "qm",
                        *arguments,
                    ],
                )
                expected = "piped input\n" if options else ""
                self.assertEqual(output["stdin"], expected)
        for path in self.runtime.rglob("*"):
            if path.is_file():
                self.assertEqual(path.read_text(), "existing runtime state\n")

    @unittest.skipUnless(
        PRIVATE_CRUN, "requires the smoke test's private crun mount"
    )
    def test_exec_terminal(self):
        """Check exec terminal."""
        for options in ([], ["-t"], ["--tty"], ["-it"], ["-ti"]):
            with self.subTest(options=options):
                master, slave = os.openpty()
                try:
                    result = subprocess.run(
                        self.command("exec", *options, "/bin/bash"),
                        stdin=slave,
                        stdout=slave,
                        stderr=subprocess.PIPE,
                        timeout=5,
                    )
                    output = json.loads(os.read(master, 4096))
                finally:
                    os.close(master)
                    os.close(slave)
                self.assertEqual(result.returncode, 23, result.stderr)
                if options:
                    self.assertEqual(
                        output["argv"][-3:], ["--tty", "qm", "/bin/bash"]
                    )
                    self.assertIsNone(output["stdin"])
                else:
                    self.assertNotIn("--tty", output["argv"])
                    self.assertEqual(output["stdin"], "")

    @unittest.skipUnless(
        PRIVATE_CRUN, "requires the smoke test's private crun mount"
    )
    def test_exec_separator(self):
        """Check exec separator."""
        result = subprocess.run(
            self.command("exec", "--", "/bin/true"),
            input="",
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertEqual(
            json.loads(result.stdout)["argv"][-2:], ["qm", "/bin/true"]
        )

    def test_runtime_directory_environment(self):
        """Check runtime directory environment."""
        (self.runtime / "crun/qm/status").unlink()
        (self.runtime / "state.json").write_text(
            json.dumps({"version": 1, "netns": str(self.runtime / "netns")})
        )
        environment = {**os.environ, "RUNTIME_DIRECTORY": str(self.runtime)}
        result = subprocess.run(
            [str(LAUNCHER), "cleanup"],
            text=True,
            capture_output=True,
            env=environment,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.runtime / "netns").exists())
        (self.runtime / "netns").touch()
        (self.runtime / "state.json").write_text(
            json.dumps({"version": 1, "netns": str(self.runtime / "netns")})
        )
        result = subprocess.run(
            self.command("cleanup"),
            text=True,
            capture_output=True,
            env={**environment, "RUNTIME_DIRECTORY": "/wrong-runtime"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.runtime / "netns").exists())

    def test_invalid_command_arguments(self):
        """Check invalid command arguments."""
        cases = [
            (["exec"], "exec requires a command"),
            (["exec", "--"], "exec requires a command"),
            (
                ["cleanup", "exec", "/bin/bash"],
                "cleanup takes no positional arguments",
            ),
            (["cleanup", "--hostname", "qm"], "unrecognized option"),
            (["unknown"], "unknown command"),
        ]
        for arguments, message in cases:
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    self.command(*arguments), text=True, capture_output=True
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)

    def test_help_and_missing_command(self):
        """Check help and missing command."""
        result = subprocess.run(
            [str(LAUNCHER), "--help"], text=True, capture_output=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ("exec", "inspect", "signal"):
            self.assertIn(f"\n  {command} ", result.stdout)
        for internal in ("launch", "cleanup", "update-resolv-conf"):
            self.assertNotIn(internal, result.stdout)
        self.assertIn("qmc COMMAND --help", result.stdout)
        self.assertNotIn("--config", result.stdout)

        result = subprocess.run(
            [str(LAUNCHER)], text=True, capture_output=True
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage: qmc", result.stderr)

    def test_command_help(self):
        """Check command help."""
        common = {"--runtime-dir", "--verbose", "--help"}
        commands = {
            "exec": {"--interactive", "--tty"},
            "inspect": {"--config", "--oci", "--field"},
            "signal": {"--clear"},
            "launch": {"--config", "--prepare-only"},
            "cleanup": set(),
            "update-resolv-conf": {"--config"},
        }
        for command, options in commands.items():
            with self.subTest(command=command):
                result = subprocess.run(
                    [str(LAUNCHER), command, "--help"],
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(
                    result.stdout.startswith(f"Usage: qmc {command} [OPTIONS]")
                )
                self.assertEqual(result.stderr, "")
                listed = {
                    match[1]
                    for line in result.stdout.splitlines()
                    if (match := re.match(r"  (?:-[it], )?(--[a-z-]+)", line))
                }
                self.assertEqual(listed, common | options)
                self.assertEqual(
                    "\nConfiguration:" in result.stdout, "--config" in options
                )
                for other in commands.keys() - {command}:
                    self.assertNotIn(f"qmc {other} ", result.stdout)

    def test_command_specific_options(self):
        """Check command specific options."""
        cases = {
            "exec": ["--config", "--prepare-only", "--oci", "--field"],
            "inspect": ["--prepare-only"],
            "signal": ["--config", "--prepare-only", "--oci", "--field"],
            "launch": ["--oci", "--field"],
            "cleanup": ["--config", "--prepare-only", "--oci", "--field"],
            "update-resolv-conf": ["--prepare-only", "--oci", "--field"],
        }
        for command, options in cases.items():
            if command != "exec":
                options.extend(["--interactive", "--tty"])
            for option in options:
                with self.subTest(command=command, option=option):
                    result = subprocess.run(
                        self.command(command, option),
                        text=True,
                        capture_output=True,
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, "")
                    self.assertIn(
                        f"unrecognized option '{option}'", result.stderr
                    )
                    self.assertIn(
                        f"Usage: qmc {command} [OPTIONS]", result.stderr
                    )

    @unittest.skipUnless(
        PRIVATE_CRUN, "requires the smoke test's private crun mount"
    )
    def test_exec_missing_crun_preserves_state(self):
        """Check exec missing crun preserves state."""
        self.crun.write_text("#!/missing-interpreter\n")
        result = subprocess.run(
            self.command("exec", "/bin/bash"), text=True, capture_output=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("exec /usr/bin/crun", result.stderr)
        self.assertTrue((self.runtime / "netns").exists())
        self.assertTrue((self.runtime / "crun/qm/status").exists())


unittest.main()
