#!/usr/bin/env python3
"""ColorOS's /data folders that One UI's init never makes (guest_prepare.sh): theme, icons, and the font folder."""
from pathlib import Path
import os
import stat
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'switcher/assets/guest_prepare.sh').read_text()
START = 'if [ "${ONEOS_GUEST_THEME_DIRS:-1}" = 1 ] && [ -e "$ROOTFS/system/framework/oplus-services.jar" ]; then\n'
END = '    rm -f "$STAGE/coloros_data_dirs.txt"\nfi\n'
BLOCK = START + SOURCE.split(START, 1)[1].split(END, 1)[0] + END
RC = '''on post-fs-data
    mkdir /data/theme 0777 system system
    mkdir /data/oplus/uxicons 0777 system system
    mkdir /data/oplus/uxres 0777 system system
    mkdir /data/oplus/language 0777 system system
    mkdir /data/oplus/other 0770 system system
    mkdir /data/elsewhere 0700 root root
'''
FONT = ['data/format_unclear', 'data/format_unclear/font']
THEME = ['data/theme', 'data/oplus/uxicons', 'data/oplus/uxres', 'data/oplus/language']


class ColorOsDataDirs(unittest.TestCase):
    def run_case(self, rc=RC, oplus=True, env=None, before=None):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); stage = root / 'stage'; rootfs = root / 'rootfs'; ext = root / 'system_ext'
            (stage / 'data').mkdir(parents=True); (rootfs / 'system/etc/init').mkdir(parents=True)
            (rootfs / 'system/framework').mkdir(); (ext / 'etc/init').mkdir(parents=True)
            if oplus: (rootfs / 'system/framework/oplus-services.jar').write_text('')
            (ext / 'etc/init/init.oplus.rootdir.rc').write_text(rc)
            if before: before(root, stage)
            # busybox stand-in: owners and labels are only recorded (not root here), modes are set.
            bb = root / 'bb'
            bb.write_text('#!/bin/sh\necho "$@" >> "$BBLOG"\ncase "$1" in chmod) exec "$@" ;; esac\nexit 0\n'); bb.chmod(0o755)
            e = {**os.environ, 'STAGE': str(stage), 'ROOTFS': str(rootfs), 'GUEST_SYSTEM_EXT': str(ext), 'BB': str(bb),
                 'BBLOG': str(root / 'bblog'), **(env or {})}
            out = subprocess.run(['sh', '-c', BLOCK], env=e, check=True, capture_output=True, text=True).stdout.splitlines()
            made = {str(p.relative_to(stage)): stat.S_IMODE(p.stat().st_mode) for p in sorted(stage.rglob('*')) if p.is_dir() and not p.is_symlink()}
            log = (root / 'bblog').read_text().replace(str(stage) + '/', '') if (root / 'bblog').exists() else ''
            outside = sorted(p.name for p in (root / 'outside').iterdir()) if (root / 'outside').exists() else None
            return out, made, log, outside

    def test_the_font_folders_come_with_the_theme_folders(self):
        out, made, log, _ = self.run_case()
        self.assertEqual(['ColorOS theme/icon /data folders from its init rc files: 6 made (6 listed)'], out)
        for p in THEME: self.assertEqual(0o777, made[p], p)
        for p in FONT: self.assertEqual(0o771, made[p], p)
        self.assertNotIn('data/oplus/other', made); self.assertNotIn('data/elsewhere', made)
        for p in FONT:
            self.assertIn(f'chown 1000:1000 {p}\n', log)
            self.assertIn(f'chcon u:object_r:system_data_file:s0 {p}\n', log)

    def test_an_rc_that_names_the_font_folders_gives_their_mode_and_owner(self):
        rc = RC + '    mkdir /data/format_unclear 0775 root system\n    mkdir /data/format_unclear/font/ 0777 system system\n'
        out, made, log, _ = self.run_case(rc)
        self.assertEqual(['ColorOS theme/icon /data folders from its init rc files: 6 made (6 listed)'], out)
        self.assertEqual((0o775, 0o777), (made['data/format_unclear'], made['data/format_unclear/font']))
        self.assertIn('chown 0:1000 data/format_unclear\n', log)

    def test_a_second_run_makes_nothing(self):
        def before(root, stage):
            for p in THEME + FONT: (stage / p).mkdir(parents=True)
        out, made, _, _ = self.run_case(before=before)
        self.assertEqual(['ColorOS theme/icon /data folders from its init rc files: 0 made (6 listed)'], out)
        self.assertEqual(0o771, made['data/format_unclear/font'])

    def test_a_link_on_the_way_is_not_followed(self):
        def before(root, stage):
            (root / 'outside').mkdir(); (stage / 'data/format_unclear').symlink_to(root / 'outside')
        out, made, _, outside = self.run_case(before=before)
        self.assertEqual(['ColorOS /data folder /data/format_unclear: a link on the way, skipped',
                          'ColorOS /data folder /data/format_unclear/font: a link on the way, skipped',
                          'ColorOS theme/icon /data folders from its init rc files: 4 made (6 listed)'], out)
        self.assertEqual([], outside)

    def test_other_systems_and_the_switch(self):
        for kw in ({'oplus': False}, {'env': {'ONEOS_GUEST_THEME_DIRS': '0'}}):
            with self.subTest(kw):
                out, made, log, _ = self.run_case(**kw)
                self.assertEqual(([], ['data'], ''), (out, sorted(made), log))


if __name__ == '__main__':
    unittest.main()
