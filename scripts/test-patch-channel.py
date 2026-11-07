#!/usr/bin/env python3
"""Exercise release preparation without network or publishing."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import shutil

spec = importlib.util.spec_from_file_location('publisher', Path(__file__).with_name('release-patch-channel.py'))
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class ChannelPublisherTests(unittest.TestCase):
    def test_override_is_hashed_and_uses_only_the_fork(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); inputs = root / 'inputs'; inputs.mkdir()
            payload = inputs / 'Fold8SystemUI.apk'; payload.write_bytes(b'fixture')
            manifest = publisher.prepare('n6-global-f8', 'fixture-1', inputs, root / 'release')
            data = json.loads(manifest.read_text())
            entry = next(f for f in data['files'] if f['name'] == payload.name)
            self.assertEqual(hashlib.sha256(b'fixture').hexdigest(), entry['sha256'])
            self.assertEqual('gh:thatjoshguy67/OneOS-files:fold8-experimental', entry['source'])
            self.assertEqual(b'fixture', (manifest.parent / entry['sha256']).read_bytes())

    def test_guarded_payloads_and_their_guards_stay_the_apps(self):
        for name in ('services_patched.jar', 'vold_patched', 'guards.txt', 'samcam.tar', 'Fold8AngleRelay.dex'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); inputs = root / 'inputs'; inputs.mkdir()
                (inputs / name).write_bytes(b'new guarded fixture')
                with self.assertRaises(ValueError):
                    publisher.prepare('n6-global-f8', 'fixture-2', inputs, root / 'release')
                self.assertFalse((root / 'release').exists())

    def test_rejects_new_scripts_and_bad_guard_lists(self):
        for name, content in [('guest_prepare.sh', b'new script'), ('guards.txt', b'bad guards')]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); inputs = root / 'inputs'; inputs.mkdir()
                (inputs / name).write_bytes(content)
                with self.assertRaises((ValueError, KeyError)):
                    publisher.prepare('n6-global-f8', 'fixture-3', inputs, root / 'release')

    def test_second_contributor_and_shared_device_sets_use_the_same_publisher(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packages = root / 'app-android/packages'
            shutil.copytree(publisher.ROOT / 'app-android/packages', packages)
            registry = packages / 'patch-sources.json'
            catalog = json.loads(registry.read_text())
            image_hash = catalog['contributors'][0]['targets'][0]['imageSha256']
            catalog['contributors'].append(dict(id='another-contributor', label='Another contributor',
                repository='another-contributor/patches', tag='testing', targets=[
                    dict(profile=profile, image='coloros17-findn6', set='n6-f8u', imageSha256=image_hash)
                    for profile in ('f7', 'f8u')]))
            registry.write_text(json.dumps(catalog))
            inputs = root / 'inputs'; inputs.mkdir()
            (inputs / 'Fold8SystemUI.apk').write_bytes(b'another device fixture')
            with patch.object(publisher, 'ROOT', root):
                with self.assertRaises(ValueError):
                    publisher.prepare('n6-f8u', 'other-1', inputs, root / 'ambiguous', 'another-contributor')
                manifest = publisher.prepare('n6-f8u', 'other-1', inputs, root / 'release', 'another-contributor', 'f7')
            data = json.loads(manifest.read_text())
            self.assertEqual('f7-n6-f8u.json', manifest.name)
            self.assertEqual('f7', data['profile'])
            entry = next(f for f in data['files'] if f['name'] == 'Fold8SystemUI.apk')
            self.assertEqual('gh:another-contributor/patches:testing', entry['source'])


if __name__ == '__main__':
    unittest.main()
