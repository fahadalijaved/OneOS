#!/usr/bin/env python3
"""The pre-boot cleanup of code folders nothing uses (guest_prepare.sh), against stage fixtures."""
from pathlib import Path
import os
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parent.parent
SOURCE = (ROOT / 'switcher/assets/guest_prepare.sh').read_text()
START = 'PL="$STAGE/data/system/packages.list"\nPX='
END = '    [ "$stg" = 0 ] || echo "Install staging folders older than three days removed: $stg"\nfi\n'
BLOCK = START + SOURCE.split(START, 1)[1].split(END, 1)[0] + END

IN_USE = '~~aaa==/com.keep.app-Q1w2_e3=='
SUFFIX_DASH = '~~bbb==/com.gone.app-ab-cd_ef=='
PREFIX_NAME = '~~ccc==/com.keep-zz=='
OLD_VERSION = '~~ddd==/com.keep.app-old-one=='
OLD_OF_SYSTEM = '~~eee==/com.sys.app-xx=='
MISSING_NEW = '~~fff==/com.moved.app-old=='
NO_APK = '~~ggg==/com.gone.noapk-yy=='
EMPTY_PARENT = '~~hhh=='
PRELOAD_UNUSED = 'Weather'
PRELOAD_USED = 'Notes'
DASH_NO_DOT = 'Some-App'
STAGING_OLD = 'vmdl111.tmp'
STAGING_NEW = 'vmdl222.tmp'
ALL = [IN_USE, SUFFIX_DASH, PREFIX_NAME, OLD_VERSION, OLD_OF_SYSTEM, MISSING_NEW, NO_APK, EMPTY_PARENT,
       PRELOAD_UNUSED, PRELOAD_USED, DASH_NO_DOT, STAGING_OLD, STAGING_NEW]

RECORDS = [
    ('android', '/system/framework'),
    ('com.keep.app', '/data/app/' + IN_USE),
    ('com.sys.app', '/my_stock/del-app/Sys'),
    ('com.moved.app', '/data/app/~~zzz==/com.moved.app-new=='),
    ('com.notes', '/data/app/' + PRELOAD_USED),
]


def packages_xml(records=RECORDS, tail='</packages>\n'):
    body = ''.join(f'    <package name="{n}" codePath="{c}" nativeLibraryPath="{c}/lib" realName="x.{n}" userId="10001">\n'
                   f'        <sigs count="1" schemeVersion="3" />\n    </package>\n' for n, c in records)
    return ('<?xml version=\'1.0\' encoding=\'UTF-8\' standalone=\'yes\' ?>\n<packages>\n'
            '    <updated-package name="com.sys.app" codePath="/my_stock/del-app/Sys" />\n' + body + tail)


def make_stage(root, xml=None, listed=None):
    stage = root / 'stage'
    app = stage / 'data/app'; system = stage / 'data/system'
    app.mkdir(parents=True); system.mkdir(parents=True)
    for rel in ALL:
        d = app / rel; d.mkdir(parents=True)
        if rel not in (NO_APK, EMPTY_PARENT, STAGING_OLD, STAGING_NEW):
            (d / 'base.apk').write_bytes(b'PK')
    (app / NO_APK / 'lib').mkdir()
    (app / STAGING_OLD / 'base.apk').write_bytes(b'PK')
    old = time.time() - 6 * 86400
    os.utime(app / STAGING_OLD, (old, old))
    # A link is never followed or removed (it points inside the fixture).
    outside = root / 'outside'; outside.mkdir(); (outside / 'base.apk').write_bytes(b'PK')
    (app / 'Linked').symlink_to(outside)
    names = listed if listed is not None else [n for n, _ in RECORDS]
    (system / 'packages.list').write_text(''.join(f'{n} 10001 0 /data/user/0/{n} default:targetSdkVersion=36 none 0 1 1 @null\n' for n in names))
    if xml is not None:
        (system / 'packages.xml').write_bytes(xml if isinstance(xml, bytes) else xml.encode())
    return stage


def run(stage):
    out = subprocess.run(['/bin/sh', '-c', BLOCK], env=dict(os.environ, STAGE=str(stage)), check=True,
                         capture_output=True, text=True)
    left = {rel for rel in ALL if (stage / 'data/app' / rel).is_dir()}
    return out.stdout.splitlines(), left


class UninstalledAppCleanup(unittest.TestCase):
    def test_with_text_records_every_unused_code_folder_goes(self):
        with tempfile.TemporaryDirectory() as t:
            stage = make_stage(Path(t), packages_xml())
            lines, left = run(stage)
            self.assertEqual({IN_USE, MISSING_NEW, NO_APK, PRELOAD_USED, STAGING_NEW}, left)
            self.assertEqual([
                "Uninstalled apps' code folders removed: com.gone.app com.keep",
                'Code folders of older versions of installed apps removed: 2',
                'Copies of preinstalled apps that no package uses removed: 2',
                'Install staging folders older than three days removed: 1',
            ], lines)
            app = stage / 'data/app'
            # The emptied parents went with their folders; the link and what it points to stayed.
            for rel in (SUFFIX_DASH, PREFIX_NAME, OLD_VERSION, OLD_OF_SYSTEM):
                self.assertFalse((app / rel).parent.exists(), rel)
            self.assertTrue((app / 'Linked').is_symlink())
            self.assertTrue((Path(t) / 'outside/base.apk').exists())
            self.assertFalse((stage / 'guest_code_paths.txt').exists())
            # Nothing left to do the second time.
            lines, again = run(stage)
            self.assertEqual(([], left), (lines, again))

    def test_without_trusted_records_only_uninstalled_and_staging_folders_go(self):
        cases = {
            'binary': b'ABX\x00' + packages_xml().encode(),
            'cut off': packages_xml(tail=''),
            'no file': None,
            'a record without its code path': packages_xml() .replace('</packages>', '    <package name="com.odd" userId="10002">\n</packages>'),
            'fewer records than listed packages': packages_xml(RECORDS[:3]),
        }
        for name, xml in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as t:
                stage = make_stage(Path(t), xml)
                lines, left = run(stage)
                self.assertEqual(set(ALL) - {SUFFIX_DASH, PREFIX_NAME, STAGING_OLD, EMPTY_PARENT}, left)
                self.assertEqual(["Uninstalled apps' code folders removed: com.gone.app com.keep",
                                  'Install staging folders older than three days removed: 1'], lines)

    def test_an_unfinished_write_of_the_records_is_not_trusted(self):
        with tempfile.TemporaryDirectory() as t:
            stage = make_stage(Path(t), packages_xml())
            (stage / 'data/system/packages-backup.xml').write_text(packages_xml())
            _, left = run(stage)
            self.assertIn(OLD_VERSION, left)
            self.assertIn(PRELOAD_UNUSED, left)
            self.assertNotIn(SUFFIX_DASH, left)

    def test_no_package_list_nothing_is_touched(self):
        for how in ('missing', 'empty', 'link'):
            with self.subTest(how), tempfile.TemporaryDirectory() as t:
                stage = make_stage(Path(t), packages_xml())
                pl = stage / 'data/system/packages.list'
                keep = pl.read_text(); pl.unlink()
                if how == 'empty': pl.write_text('')
                if how == 'link':
                    (Path(t) / 'list').write_text(keep); pl.symlink_to(Path(t) / 'list')
                lines, left = run(stage)
                self.assertEqual(([], set(ALL)), (lines, left))

    def test_a_linked_app_folder_is_left_alone(self):
        with tempfile.TemporaryDirectory() as t:
            stage = make_stage(Path(t), packages_xml())
            real = Path(t) / 'elsewhere'
            (stage / 'data/app').rename(real)
            (stage / 'data/app').symlink_to(real)
            lines, _ = run(stage)
            self.assertEqual([], lines)
            self.assertTrue((real / SUFFIX_DASH).is_dir())


if __name__ == '__main__':
    unittest.main()
