# SPDX-License-Identifier: GPL-2.0-only
"""Exercise real userns functions with isolated files and mocked account tools."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "userns"


class UserNamespaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qm-userns-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "etc").mkdir()
        (self.root / "qm/etc").mkdir(parents=True)
        (self.root / "qm/etc/passwd").write_text("root:x:0:0:Root:/root:/bin/bash\napp:x:1000:1000:App:/home/app:/bin/sh\n")
        (self.root / "qm/etc/group").write_text("root:x:0:\napp:x:1000:\n")
        for name in ("subuid", "subgid"):
            (self.root / "etc" / name).write_text("other:100000:65536\n")

    def run_functions(self, commands):
        script = r'''source "$1"
ROOT_DIR=$TEST_ROOT
QM_ROOT_DIR=$TEST_ROOT/qm
systemd-sysusers() { printf 'sysusers %s\n' "$*" >> "$TEST_ROOT/calls"; }
usermod() {
    printf 'usermod %s\n' "$*" >> "$TEST_ROOT/calls"
    local file=subuid
    [ "$2" != --add-subgids ] || file=subgid
    printf 'qm_root:1000000000:1500000000\n' >> "$TEST_ROOT/etc/$file"
}
''' + commands
        return subprocess.run(["bash", "-euc", script, "test", str(SCRIPT)],
                              env={**os.environ, "TEST_ROOT": str(self.root)},
                              capture_output=True, text=True)

    def test_enable_repeat_and_disable(self):
        result = self.run_functions("enable; enable")
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.root / "etc/qmc.conf.d/qm-user-namespaces.conf"
        self.assertEqual(json.loads(config.read_text()), {"userns": "required"})
        self.assertIn("qm_app      1000001000:1000001000", (self.root / "etc/sysusers.d/qm-sysusers.conf").read_text())
        calls = (self.root / "calls").read_text()
        self.assertEqual(calls.count("usermod"), 2)
        self.assertIn("1000000000-2499999999", calls)
        result = self.run_functions("disable; disable")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(config.read_text()), {"userns": "off"})
        self.assertFalse((self.root / "etc/sysusers.d/qm-sysusers.conf").exists())
        for name in ("subuid", "subgid"):
            self.assertEqual((self.root / "etc" / name).read_text(), "other:100000:65536\n")

    def test_disable_without_subid_files(self):
        for name in ("subuid", "subgid"):
            (self.root / "etc" / name).unlink()
        result = self.run_functions("disable")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / "etc/qmc.conf.d/qm-user-namespaces.conf").read_text()), {"userns": "off"})

    def test_account_tool_failure_propagates(self):
        result = self.run_functions("usermod() { return 23; }; enable")
        self.assertEqual(result.returncode, 23)
        self.assertFalse((self.root / "etc/qmc.conf.d/qm-user-namespaces.conf").exists())


if __name__ == "__main__":
    unittest.main()
