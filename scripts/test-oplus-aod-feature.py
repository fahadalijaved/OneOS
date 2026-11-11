#!/usr/bin/env python3
"""The Always-On Display feature switch for Oplus images (guest_prepare.sh), against stage fixtures."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SOURCE = (ROOT / 'switcher/assets/guest_prepare.sh').read_text()
START = '    AODF=oplus.software.display.aod_support\n'
END = '    case "$FORM" in\n        fold) ADDED="$ADDED oplus.hardware.type.fold"'
BLOCK = (START + SOURCE.split(START, 1)[1].split(END, 1)[0]).replace(
    '/system/etc/floating_feature.xml', '$HOST/floating_feature.xml').replace('/sys/class/lcd/panel/alpm', '$HOST/alpm')
FEATURE = 'oplus.software.display.aod_support'
FLOATING = ('<SecFloatingFeatureSet>\n    <SEC_FLOATING_FEATURE_FRAMEWORK_CONFIG_AOD_ITEM>%s</SEC_FLOATING_FEATURE_FRAMEWORK_CONFIG_AOD_ITEM>\n'
            '</SecFloatingFeatureSet>\n')


class OplusAod(unittest.TestCase):
    def run_block(self, image='coloros17-findx9u-in', floating='aodversion=7,clocktransition', alpm=False, listed=True,
                  app=None, catalogue=None, added='x.first', env=None, link_list=False):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            stage = r / 'stage'; rootfs = stage / 'rootfs'; host = r / 'host'
            (stage / 'data/system').mkdir(parents=True); (rootfs / 'system_ext').mkdir(parents=True); host.mkdir()
            (stage / '.oneos_stage').write_text('{\n  "image": "%s",\n  "set": "x"\n}\n' % image)
            if floating is not None:
                (host / 'floating_feature.xml').write_text(FLOATING % floating)
            if alpm:
                (host / 'alpm').write_text('0\n')
            names = ['android', 'com.oplus.aodx', 'x.com.oplus.aod'] + (['com.oplus.aod'] if listed else [])
            text = ''.join(f'{n} 10001 0 /data/user/0/{n} platform:privapp none 0 1 1 @null\n' for n in names)
            if link_list:
                (r / 'list').write_text(text); (stage / 'data/system/packages.list').symlink_to(r / 'list')
            else:
                (stage / 'data/system/packages.list').write_text(text)
            if app:
                (rootfs / app).mkdir(parents=True)
            if catalogue:
                d = rootfs / catalogue; d.parent.mkdir(parents=True)
                d.write_text(f'<oplus-config>\n    <oplus-feature name="{FEATURE}"/>\n</oplus-config>\n')
            out = subprocess.run(['/bin/sh', '-c', f'ADDED="{added}"\n' + BLOCK + 'echo "ADDED=$ADDED"\n'], check=True,
                                 capture_output=True, text=True,
                                 env=dict(os.environ, STAGE=str(stage), ROOTFS=str(rootfs), GUEST_SYSTEM_EXT=str(rootfs / 'system_ext'),
                                          HOST=str(host), **(env or {})))
            self.assertEqual('', out.stderr)
            lines = out.stdout.splitlines()
            return lines[:-1], lines[-1][len('ADDED='):].split()

    def test_the_installed_aod_app_on_a_phone_with_aod(self):
        for image in ('coloros17-findx9u-in', 'oxygenos16-cph2745'):
            with self.subTest(image):
                lines, added = self.run_block(image=image)
                self.assertEqual(['x.first', FEATURE], added)
                self.assertEqual(['ColorOS Always-On Display: on (One UI has AOD here; com.oplus.aod installed)'], lines)

    def test_a_first_boot_goes_by_the_image(self):
        for app in ('my_stock/app/Aod', 'my_heytap/priv-app/AodUnit', 'system_ext/priv-app/Aod'):
            with self.subTest(app):
                lines, added = self.run_block(listed=False, app=app)
                self.assertIn(FEATURE, added)
                self.assertEqual([f'ColorOS Always-On Display: on (One UI has AOD here; /{app})'], lines)
        lines, added = self.run_block(listed=False, catalogue='my_product/etc/extension/com.oplus.oplus-feature.xml')
        self.assertIn(FEATURE, added)
        self.assertEqual(['ColorOS Always-On Display: on (One UI has AOD here; declared in '
                          '/my_product/etc/extension/com.oplus.oplus-feature.xml)'], lines)

    def test_the_low_power_node_of_the_panel_counts_too(self):
        lines, added = self.run_block(floating=None, alpm=True)
        self.assertIn(FEATURE, added)
        self.assertEqual(['ColorOS Always-On Display: on (the panel has a low-power mode; com.oplus.aod installed)'], lines)

    def test_a_phone_without_aod_is_left_alone(self):
        # No floating feature file, or the item without a value (an LCD phone).
        for floating in (None, ''):
            with self.subTest(floating):
                lines, added = self.run_block(floating=floating)
                self.assertEqual(['x.first'], added)
                self.assertEqual(['ColorOS Always-On Display: left off (One UI has no AOD on this phone)'], lines)

    def test_an_image_without_the_aod_app_is_left_alone(self):
        lines, added = self.run_block(listed=False)
        self.assertEqual((['ColorOS Always-On Display: left off (no AOD app in this image)'], ['x.first']), (lines, added))
        # A linked package list is not read.
        lines, added = self.run_block(link_list=True)
        self.assertEqual((['ColorOS Always-On Display: left off (no AOD app in this image)'], ['x.first']), (lines, added))

    def test_the_switch(self):
        lines, added = self.run_block(env={'ONEOS_GUEST_AOD': '0'})
        self.assertEqual((['ColorOS Always-On Display: left off (ONEOS_GUEST_AOD=0)'], ['x.first']), (lines, added))

    def test_the_find_n6_build_keeps_its_own_rules(self):
        self.assertEqual(([], ['x.first']), self.run_block(image='coloros17-findn6'))
        # Already declared (the Z Fold8 sets): no second entry, no line.
        self.assertEqual(([], ['x.first', FEATURE]), self.run_block(added='x.first ' + FEATURE))


if __name__ == '__main__':
    unittest.main()
