# SPDX-License-Identifier: GPL-2.0-only
"""Legacy configuration must be reported without changing administrator files."""
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2]


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='qm-migration-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def check(self):
        return subprocess.run([str(SOURCE / 'tools/check-config-migration'), str(self.root)],
                              capture_output=True, text=True)

    def test_empty_legacy_directory(self):
        (self.root / 'etc/containers/systemd/qm.container.d').mkdir(parents=True)
        self.assertEqual(self.check().returncode, 0)

    def test_old_admin_and_vendor_overrides_are_preserved(self):
        for base in ('etc', 'run', 'usr/lib', 'usr/share'):
            with self.subTest(base=base):
                path = self.root / base / 'containers/systemd/qm.container.d/devices.conf'
                path.parent.mkdir(parents=True)
                path.write_text('[Container]\nAddDevice=/dev/kvm\n')
                result = self.check()
                self.assertEqual(result.returncode, 1)
                self.assertIn(str(path), result.stderr)
                self.assertIn('/etc/qmc.conf.d', result.stderr)
                self.assertEqual(path.read_text(), '[Container]\nAddDevice=/dev/kvm\n')
                path.unlink()

    def test_full_quadlet(self):
        path = self.root / 'etc/containers/systemd/qm.container'
        path.parent.mkdir(parents=True)
        path.touch()
        self.assertEqual(self.check().returncode, 1)

    def test_application_quadlets_and_backup_files(self):
        path = self.root / 'etc/qm/containers/systemd/app.container'
        path.parent.mkdir(parents=True)
        path.touch()
        backup = self.root / 'etc/containers/systemd/qm.container.d/saved.conf.old'
        backup.parent.mkdir(parents=True)
        backup.touch()
        self.assertEqual(self.check().returncode, 0)


unittest.main()
