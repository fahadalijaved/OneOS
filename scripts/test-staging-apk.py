#!/usr/bin/env python3
"""Regression checks using a real built APK's compiled BuildConfig (any series).

Usage: scripts/test-staging-apk.py [unittest flags] <OneOS.apk>
"""
import importlib.util
import pathlib
import re
import sys
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('staging', pathlib.Path(__file__).with_name('check-staging-apk.py'))
staging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(staging)
APK = next((a for a in sys.argv[1:] if a.endswith('.apk')), None) or sys.exit(__doc__)
sys.argv.remove(APK)
PAYLOAD = re.compile(r'assets/oneos/files/[0-9a-f]{64}')


class IntegrityTest(unittest.TestCase):
    def rewrite(self, change):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'test.apk'
            with zipfile.ZipFile(APK) as source, zipfile.ZipFile(path, 'w') as target:
                for entry in source.infolist():
                    data = source.read(entry)
                    target.writestr(entry.filename, change(entry.filename, data))
            return staging.verify(path)

    def test_valid_apk(self):
        staging.verify(APK)

    def test_stale_scripts_pin(self):
        with self.assertRaisesRegex(ValueError, 'manifest differs from compiled'):
            self.rewrite(lambda name, data: data + b'# changed\n' if name == 'assets/oneos/sets/scripts.sha256' else data)

    def test_stale_package_pin(self):
        with self.assertRaisesRegex(ValueError, 'manifest differs from compiled'):
            self.rewrite(lambda name, data: data + b'# changed\n' if name.startswith('assets/oneos/sets/') and not name.endswith('/scripts.sha256') else data)

    def test_changed_root(self):
        with self.assertRaisesRegex(ValueError, 'root script differs'):
            self.rewrite(lambda name, data: data + b'\n' if name == 'assets/root/oneos_root.sh' else data)

    def test_corrupted_payload(self):
        # Only the packed files themselves (index.txt and remote.txt stay as built).
        with self.assertRaisesRegex(ValueError, 'payload hash mismatch'):
            self.rewrite(lambda name, data: bytes([data[0] ^ 1]) + data[1:] if PAYLOAD.fullmatch(name) and data else data)

    def test_download_missing_from_the_list(self):
        def drop_first(name, data):
            if name != 'assets/oneos/files/remote.txt':
                return data
            lines = [l for l in data.decode().splitlines(True) if l.strip() and not l.startswith('#')]
            if not lines:
                self.skipTest('a packed APK (no downloads)')
            return data.decode().replace(lines[0], '', 1).encode()
        with self.assertRaisesRegex(ValueError, 'neither packed nor on the download list'):
            self.rewrite(drop_first)


unittest.main()
