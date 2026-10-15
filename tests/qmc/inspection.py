# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 Alexander Larsson
# See LICENSE for the full license text.

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

LAUNCHER = pathlib.Path(sys.argv.pop(1)).resolve()


class InspectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qmc-inspect-")
        self.addCleanup(self.temp.cleanup)
        self.directory = pathlib.Path(self.temp.name)
        self.runtime = self.directory / "runtime"
        self.base = self.directory / "base.json"
        self.base.write_text(json.dumps({
            "root": {"path": "/base/rootfs"},
            "mounts": [],
        }))
        self.settings = {"base-config": str(self.base)}
        self.filename = self.directory / "qmc.conf"

    def inspect(self, *options, oci=False, env=None):
        self.filename.write_text(json.dumps(self.settings))
        return subprocess.run(
            [str(LAUNCHER), "inspect", "--runtime-dir", str(self.runtime),
             *(["--oci"] if oci else ["--config", str(self.filename)]), *options],
            text=True, capture_output=True, env=env,
        )

    def save_oci(self, config):
        self.runtime.mkdir()
        (self.runtime / "config.json").write_text(json.dumps(config))
        (self.runtime / "state.json").write_text("invalid cleanup journal\n")

    def test_merged_settings_without_runtime_or_source_access(self):
        self.settings.update({
            "hostname": "inspection", "verbose": True, "userns": "required",
            "memory-max": "5G", "seccomp": "/missing/seccomp.json",
            "resolv-conf": "/missing/resolv.conf",
            "mounts": [{"source": "/missing/tree", "destination": "/shared",
                        "options": []}],
            "devices": [{"source": "/missing/devices/*", "destination": "/dev/test"},
                        {"seat": "seat-qmc-inspect-absent"},
                        {"destination": "/dev/test/null", "remove": True}],
            "capabilities": [{"name": "ALL"}, {"name": "chown", "remove": True},
                             {"name": "chown"}],
            "unmask": ["/proc/keys"],
        })
        result = self.inspect()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        config = json.loads(result.stdout)
        self.assertEqual(config["hostname"], "inspection")
        self.assertEqual(config["rootfs"], "/base/rootfs")
        self.assertNotIn("etc-dir", config)
        self.assertNotIn("var-dir", config)
        self.assertNotIn("path-operations", config)
        self.assertNotIn("capability-operations", config)
        self.assertNotIn("add-capabilities", config)
        self.assertNotIn("drop-capabilities", config)
        self.assertNotIn("subnet", config)
        self.assertEqual(config["userns"], "required")
        self.assertEqual(config["memory-max"], 5 * 1024 ** 3)
        self.assertEqual(config["mounts"], self.settings["mounts"])
        self.assertEqual(config["devices"], self.settings["devices"])
        self.assertEqual(config["capabilities"], [
            {"name": "all"}, {"name": "CAP_CHOWN", "remove": True}, {"name": "CAP_CHOWN"}])
        self.assertEqual(config["unmask"], ["/proc/keys"])
        self.assertFalse(self.runtime.exists())

        self.settings = config
        reloaded = self.inspect()
        self.assertEqual(reloaded.returncode, 0, reloaded.stderr)
        self.assertEqual(json.loads(reloaded.stdout), config)

    def test_rootfs_override(self):
        self.settings["rootfs"] = "/custom/rootfs/."
        self.base.unlink()
        result = self.inspect()
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads(result.stdout)
        self.assertEqual(config["rootfs"], "/custom/rootfs")

    def test_field_values_and_json_pointers(self):
        self.settings["memory-max"] = "infinity"
        self.settings["mounts"] = [{"source": "/source", "destination": "/target",
                                     "options": []}]
        self.settings["capabilities"] = [{"name": "chown", "remove": True}]
        for field, expected in (("rootfs", "/base/rootfs\n"),
                                ("verbose", "false\n"), ("prefix-length", "24\n"),
                                ("memory-max", "infinity\n"),
                                ("/mounts/0/source", "/source\n"),
                                ("/mounts/0/options", "[]\n"),
                                ("/capabilities/0/name", "CAP_CHOWN\n"),
                                ("/capabilities/0/remove", "true\n")):
            with self.subTest(field=field):
                result = self.inspect("--field", field)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, expected)

    def test_saved_oci_is_read_without_current_configuration_or_cleanup(self):
        config = {"hostname": "running", "root": {"path": "/running/rootfs"},
                  "annotations": {"a/b~c": "escaped", "unset": None}}
        self.save_oci(config)
        self.base.write_text("invalid current base configuration\n")
        before = {path.name: path.read_bytes() for path in self.runtime.iterdir()}

        result = self.inspect(oci=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), config)
        for field, expected in (("/root/path", "/running/rootfs\n"),
                                ("/annotations/a~1b~0c", "escaped\n"),
                                ("/annotations/unset", "null\n")):
            with self.subTest(field=field):
                result = self.inspect("--field", field, oci=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, expected)

        after = {path.name: path.read_bytes() for path in self.runtime.iterdir()}
        self.assertEqual(after, before)

    def test_runtime_directory_environment(self):
        self.save_oci({"hostname": "saved"})
        result = subprocess.run(
            [str(LAUNCHER), "inspect", "--oci", "--field", "hostname"],
            text=True, capture_output=True,
            env={**os.environ, "RUNTIME_DIRECTORY": str(self.runtime)},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "saved\n")

    def test_unknown_fields_and_missing_saved_bundle(self):
        for field in ("absent", "/absent/key", "/mounts/99", ""):
            with self.subTest(field=field):
                result = self.inspect("--field", field)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn("unknown inspection field", result.stderr)

        result = self.inspect(oci=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(self.runtime / "config.json"), result.stderr)
        self.assertFalse(self.runtime.exists())

    def test_invalid_options(self):
        for arguments, message in (
            (["inspect", "--oci", "--config", str(self.base)],
             "--oci cannot be combined with --config"),
            (["inspect", "extra"], "inspect takes no positional arguments"),
        ):
            with self.subTest(arguments=arguments):
                result = subprocess.run([str(LAUNCHER), *arguments],
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn(message, result.stderr)
                self.assertEqual(result.stdout, "")


unittest.main()
