#!/usr/bin/env python3
"""Checks for session property overrides, responsive resources and pinned patchers."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class ColorOSFollowup(unittest.TestCase):
    def test_power_key_override_also_replaces_a_host_false_value(self):
        text = (ROOT/'switcher/assets/guest_props.sh').read_text()
        block = text.split('    if [ "${ONEOS_GUEST_SAUPWK:-1}" = 1 ]; then', 1)[1].split('\n    fi', 1)[0]
        with tempfile.TemporaryDirectory() as tmp:
            new = Path(tmp)/'props'
            new.write_text('persist.sys.saupwk_test=false\nother=value\n')
            if sys.platform == "darwin":
                block = block.replace("sed -i ", "sed -i '' ")
            subprocess.run(['sh', '-ec', block], env=dict(os.environ, NEW=str(new)), check=True, capture_output=True)
            self.assertEqual('other=value\npersist.sys.saupwk_test=1\n', new.read_text())

    def test_cover_camera_alignment_preserves_size_and_horizontal_position(self):
        text = (ROOT/'switcher/assets/guest_props.sh').read_text()
        block = text.split('        aligned=', 1)[1].split('\n', 1)[0]
        for hole, result in [('589,0:659,104', '589,11:659,115'), ('580,4:650,104', '580,13:650,113'), ('invalid', '')]:
            run = subprocess.run(['sh', '-ec', 'aligned='+block+'\nprintf "%s" "$aligned"'],
                                 env=dict(os.environ, h=hole), capture_output=True, text=True, check=True)
            self.assertEqual(result, run.stdout)

    def test_personalisation_uses_window_width_and_keeps_cover_defaults(self):
        res = ROOT/'switcher/overlays/wallpapers_fold_grid/res'
        narrow = ET.parse(res/'layout/personal_card_fold_large_layout.xml').getroot()
        wide = ET.parse(res/'layout-w800dp/personal_card_fold_large_layout.xml').getroot()
        attr = '{http://schemas.android.com/apk/res-auto}columnCount'
        self.assertEqual('4', narrow.get(attr))
        self.assertEqual('8', wide.get(attr))
        dims = lambda folder: {x.get('name'): x.text for x in ET.parse(res/folder/'dimens.xml').getroot()}
        self.assertEqual('40dp', dims('values')['wallpaper_my_theme_header_height'])
        self.assertEqual('386dp', dims('values-w550dp')['wallpaper_my_theme_header_height'])
        self.assertEqual('330dp', dims('values-w550dp')['wallpaper_my_theme_item_width'])

    def test_geometry_is_declared_in_all_packaging_lists(self):
        for name in ['app-android/app/build.gradle.kts', 'app-android/app/src/full/assets/root/oneos_root.sh',
                     'app-android/core/root/src/main/kotlin/com/fahadali/oneos/core/root/RootScript.kt']:
            self.assertIn('OneOSFold8Geometry.dex', (ROOT/name).read_text())

    def test_patchers_refuse_drift_without_writing(self):
        for name in ['flux_editor', 'flux_viewport', 'flux_depth', 'flux_touch', 'statusbar']:
            path = ROOT/f'switcher/patches/fold8_coloros_{name}.py'
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp)/module.RELATIVE
                target.parent.mkdir(parents=True)
                target.write_bytes(b'unsupported donor')
                with self.assertRaises(ValueError):
                    module.patch(tmp)
                self.assertEqual(b'unsupported donor', target.read_bytes())


if __name__ == '__main__':
    unittest.main()
