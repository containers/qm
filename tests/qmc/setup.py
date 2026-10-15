# SPDX-License-Identifier: GPL-2.0-only
"""Check setup configuration and removal without touching host storage."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

QMC = str(Path(sys.argv.pop(1)).resolve())
SOURCE = Path(__file__).resolve().parents[2]


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qm-setup-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = [self.root / name for name in ("rootfs", "etc", "var")]
        self.settings = {"rootfs": str(self.paths[0]), "mounts": [
            {"source": str(path), "destination": destination}
            for path, destination in zip(self.paths[1:], ("/etc", "/var"))]}
        self.config = self.root / "input.conf"

    def run_functions(self, commands):
        self.config.write_text(json.dumps(self.settings))
        script = r'''hostname() { echo qm-test; }
source "$1"
qmc() { "$TEST_QMC" "$@" --config "$TEST_CONFIG"; }
SETUP_CONFIG_DIR=$TEST_ROOT/config
SETUP_SERVICE_DIR=$TEST_ROOT/service
SYSTEMCTL_SKIP=Y
systemctl() { echo 'Unexpected systemctl invocation' >&2; return 91; }
findmnt() { :; }
''' + commands
        return subprocess.run(["bash", "-euc", script, "test", str(SOURCE / "setup")],
                              env={**os.environ, "TEST_ROOT": str(self.root), "TEST_QMC": QMC,
                                   "TEST_CONFIG": str(self.config)}, capture_output=True, text=True)

    def test_custom_paths_and_mount_dependencies(self):
        result = self.run_functions("read_qmc_paths; write_qmc_configuration; write_qmc_configuration")
        self.assertEqual(result.returncode, 0, result.stderr)
        settings = json.loads((self.root / "config/50-qm-setup.conf").read_text())
        self.assertEqual(settings["rootfs"], str(self.paths[0]))
        self.assertEqual(settings["mounts"][-1], {"source": str(self.paths[2] / "tmp"), "destination": "/var/tmp"})
        unit = (self.root / "service/50-qm-setup.conf").read_text()
        for path in self.paths:
            self.assertIn('RequiresMountsFor="' + str(path) + '"', unit)

    def test_removal_uses_configured_paths_without_removing_parent(self):
        for path in self.paths:
            path.mkdir()
            (path / "marker").touch()
        result = self.run_functions("remove_qm_rootfs")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.root.is_dir())
        self.assertTrue(self.config.is_file())
        self.assertTrue(all(not path.exists() for path in self.paths))

    def test_configuration_error_prevents_removal(self):
        marker = self.paths[0]
        marker.mkdir()
        result = self.run_functions('printf broken > "$TEST_CONFIG"; remove_qm_rootfs')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(marker.is_dir())

    def test_removed_mount_prevents_removal(self):
        self.settings["mounts"].append({"destination": "/etc", "remove": True})
        result = self.run_functions("remove_qm_rootfs")
        self.assertNotEqual(result.returncode, 0)

    def test_system_directory_is_rejected(self):
        self.settings["rootfs"] = "/usr/lib"
        result = self.run_functions("remove_qm_rootfs")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Refusing", result.stderr)

    def test_skip_systemctl_needs_no_quadlet_generator(self):
        result = self.run_functions('root_check() { :; }; install() { write_qmc_configuration; }; main --skip-systemctl')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / "config/50-qm-setup.conf").exists())


if __name__ == "__main__":
    unittest.main()
