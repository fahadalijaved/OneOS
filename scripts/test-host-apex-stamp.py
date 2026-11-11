#!/usr/bin/env python3
"""check_host_apex.sh: only the look before a session's setup may keep the page cache, and only right after a clean final look."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'switcher/assets/check_host_apex.sh').read_text()
LIST = ('<apex-info-list>\n'
        '<apex-info moduleName="com.x" modulePath="/data/apex/active/com.x@2.apex" isActive="true" />\n'
        '<apex-info moduleName="com.sys" modulePath="/system/apex/com.sys.apex" isActive="true" />\n'
        '<apex-info moduleName="com.old" modulePath="/data/apex/active/com.old@1.apex" isActive="false" />\n'
        '</apex-info-list>\n')


class Phone:
    def __init__(self, root):
        self.root = Path(root)
        for m in ('com.x', 'com.sys', 'com.old'):
            (self.root / 'apex' / m / 'lib').mkdir(parents=True)
            (self.root / 'apex' / m / 'lib/a.so').write_text('a')
        (self.root / 'apex/com.x/manifest').write_text('m')
        (self.root / 'apex/apex-info-list.xml').write_text(LIST)
        self.stamp = self.root / 'stamp'
        self.calls = self.root / 'calls'
        self.script = ('sync() { echo sync >> "$CALLS"; }\n' + SOURCE
                       .replace('/apex/apex-info-list.xml', str(self.root / 'apex/apex-info-list.xml'))
                       .replace('"/apex/$m"', f'"{self.root}/apex/$m"')
                       .replace('/proc/sys/vm/drop_caches', str(self.root / 'dropped')))

    def look(self, label):
        """(line, exit code, whether the files were read from disk, whether a stamp is left)"""
        self.calls.unlink(missing_ok=True)
        out = subprocess.run(['/bin/sh', '-c', self.script, 'check', label], capture_output=True, text=True,
                             env=dict(os.environ, ONEOS_APEX_STAMP=str(self.stamp), CALLS=str(self.calls)))
        return out.stdout.strip(), out.returncode, self.calls.exists(), self.stamp.exists()


class HostApexStamp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.phone = Phone(self.tmp.name)

    def test_the_line_counts_the_active_modules_on_data(self):
        line, code, disk, stamp = self.phone.look('before-setup')
        self.assertEqual('[before-setup] host APEXes on /data: 1 modules, 2 files, 0 unreadable (read from disk)', line)
        self.assertEqual((0, True, False), (code, disk, stamp))

    def test_only_the_final_look_of_a_return_leaves_a_stamp(self):
        for label, left in (('before-setup', False), ('after-setup', False), ('after-return', False), ('after-inplace', True)):
            with self.subTest(label):
                self.phone.stamp.unlink(missing_ok=True)
                _, code, disk, stamp = self.phone.look(label)
                self.assertEqual((0, True, left), (code, disk, stamp))

    def test_the_next_sessions_first_look_keeps_the_cache_once(self):
        self.phone.look('after-inplace')
        line, code, disk, stamp = self.phone.look('before-setup')
        self.assertIn('page cache kept', line)
        self.assertEqual((0, False, False), (code, disk, stamp))
        # The stamp is spent: the same session's later looks and the next first look read from disk.
        for label in ('after-setup', 'before-setup'):
            self.assertEqual((True, False), self.phone.look(label)[2:], label)

    def test_a_look_after_the_setup_never_trusts_the_stamp(self):
        for label in ('after-setup', 'after-return', 'after-inplace'):
            with self.subTest(label):
                self.phone.look('after-inplace')
                line, _, disk, _ = self.phone.look(label)
                self.assertTrue(disk)
                self.assertIn('(read from disk)', line)

    def test_a_stamp_of_another_boot_or_another_module_list_is_not_trusted(self):
        self.phone.look('after-inplace')
        boot, sig = self.phone.stamp.read_text().split()
        self.phone.stamp.write_text(f'00000000-0000-0000-0000-000000000000 {sig}\n')
        self.assertTrue(self.phone.look('before-setup')[2])
        self.phone.look('after-inplace')
        (self.phone.root / 'apex/apex-info-list.xml').write_text(LIST + '\n')
        self.assertTrue(self.phone.look('before-setup')[2])

    @unittest.skipIf(os.geteuid() == 0, 'root reads every file')
    def test_an_unreadable_file_fails_the_look_and_leaves_no_stamp(self):
        bad = self.phone.root / 'apex/com.x/lib/a.so'
        bad.chmod(0)
        line, code, disk, stamp = self.phone.look('after-inplace')
        bad.chmod(0o644)
        self.assertIn(f'1 unreadable: {bad}', line)
        self.assertEqual((1, True, False), (code, disk, stamp))


if __name__ == '__main__':
    unittest.main()
