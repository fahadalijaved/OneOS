#!/usr/bin/env python3
"""Run the overlay verifier against valid and tampered inputs, without root."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/apply-verified-overlays.sh'

class OverlayVerification(unittest.TestCase):
    def check(self, changed_apk=False, changed_manifest=False):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'verified_addons'
            directory.mkdir()
            payload = b'verified fixture'
            digest = hashlib.sha256(payload).hexdigest()
            manifest = f'com.example.fixture {digest} {digest} fixture.apk\n'
            (directory / 'fixture.apk').write_bytes(b'changed' if changed_apk else payload)
            (directory / 'overlays.list').write_text(manifest + ('changed' if changed_manifest else ''))
            env = dict(os.environ, STAGE=tmp, BB='/bin/sh', OVERLAY_MANIFEST_SHA256=hashlib.sha256(manifest.encode()).hexdigest())
            return subprocess.run(['sh', str(SCRIPT), 'verify'], env=env, capture_output=True).returncode

    def test_accepts_verified_payload(self):
        self.assertEqual(0, self.check())

    def test_refuses_changed_apk(self):
        self.assertNotEqual(0, self.check(changed_apk=True))

    def test_refuses_changed_manifest(self):
        self.assertNotEqual(0, self.check(changed_manifest=True))

class GuestPathBoundary(unittest.TestCase):
    def test_parent_symlinks_cannot_escape_guest_data(self):
        text = SCRIPT.read_text()
        helper = "safe_data_path() {" + text.split("safe_data_path() {", 1)[1].split("\n}", 1)[0] + "\n}\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            stage = root/'stage'
            (stage/'data/local/tmp').mkdir(parents=True)
            outside = root/'outside'
            outside.mkdir()
            (stage/'data/escape').symlink_to(outside, target_is_directory=True)
            bb = root/'bb'
            bb.write_text('#!/bin/sh\nexec "$@"\n')
            bb.chmod(0o755)
            env = dict(os.environ, STAGE=str(stage), BB=str(bb))
            for path, expected in [(stage/'data/local/tmp/new-file', 0), (stage/'data/escape/new-file', 3)]:
                result = subprocess.run(['sh', '-c', helper+'safe_data_path "$TARGET"'],
                                        env=dict(env, TARGET=str(path)), capture_output=True)
                self.assertEqual(expected, result.returncode, result.stderr)

if __name__ == '__main__':
    unittest.main()
