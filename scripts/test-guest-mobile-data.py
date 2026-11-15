#!/usr/bin/env python3
"""Mobile data follows One UI's switch (guest_prepare.sh), against settings fixtures.

HyperOS keeps the switch per SIM slot (mobile_data0, mobile_data1); the other systems per
subscription (mobile_data<sub id>).
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SOURCE = (ROOT / 'switcher/assets/guest_prepare.sh').read_text()
SEED = 'seed_settings() {\n' + SOURCE.split('seed_settings() {\n', 1)[1].split('\n}\n', 1)[0] + '\n}\n'
START = 'HMD=$(cat "$STAGE/host_mobile_data" 2>/dev/null)\n'
END = '# A binary-XML settings file (Pixel: starts with ABX) cannot be read here:'
BLOCK = START + SOURCE.split(START, 1)[1].split(END, 1)[0]
HEAD = "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>\n<settings version=\"226\">\n"
ROW = '  <setting id="%d" name="%s" value="%s" package="android" defaultValue="%s" defaultSysSet="true" />\n'


def settings(**values):
    rows = dict({'airplane_mode_on': '0', 'wifi_on': '1'}, **values)
    return HEAD + ''.join(ROW % (40 + i, k, v, v) for i, (k, v) in enumerate(rows.items())) + '</settings>\n'


class MobileData(unittest.TestCase):
    def run_block(self, text=None, host='1', miui='file', env=None):
        with tempfile.TemporaryDirectory() as t:
            stage = Path(t) / 'stage'; fw = Path(t) / 'system_ext/framework'
            (stage / 'data/system/users/0').mkdir(parents=True); fw.mkdir(parents=True)
            gset = stage / 'data/system/users/0/settings_global.xml'
            if text is not None:
                if isinstance(text, bytes):
                    gset.write_bytes(text)
                else:
                    gset.write_text(text)
            if host is not None:
                (stage / 'host_mobile_data').write_text(host + '\n')
            if miui == 'file':
                (fw / 'miui-services.jar').write_text('x')
            elif miui == 'link':
                (fw / 'miui-services.jar').symlink_to('/system_ext/framework/not-on-this-side.jar')
            out = subprocess.run(['/bin/sh', '-c', SEED + BLOCK], check=True, capture_output=True, text=True,
                                 env=dict(os.environ, STAGE=str(stage), GSET=str(gset), MIUI_FW=str(fw), **(env or {})))
            self.assertEqual('', out.stderr)
            after = gset.read_bytes() if gset.exists() else None
            left = sorted(p.name for p in gset.parent.iterdir())
            return out.stdout.splitlines(), after, left

    def values(self, after):
        text = after.decode()
        self.assertTrue(text.startswith(HEAD) and text.endswith('</settings>\n'), text[-80:])
        names = re.findall(r'<setting id="(\d+)" name="([^"]+)" value="([^"]*)"', text)
        self.assertEqual(text.count('<setting '), len(names))
        self.assertEqual(len(names), len({n for _, n, _ in names}), 'a name twice')
        self.assertEqual(len(names), len({i for i, _, _ in names}), 'an id twice')
        return {n: v for _, n, v in names}

    def test_hyperos_gets_both_sim_slots(self):
        # S25 Ultra ba784a19: sub 1 sits in slot 0; the earlier seed left mobile_data1=1 and slot 0 off.
        lines, after, left = self.run_block(settings(mobile_data='0', mobile_data1='1', multi_sim_data_call='1'))
        self.assertEqual(['Guest settings_global: mobile_data=1', 'Guest settings_global: mobile_data0=1',
                          'Guest settings_global: mobile_data1=1'], lines)
        got = self.values(after)
        self.assertEqual(('1', '1', '1'), (got['mobile_data'], got['mobile_data0'], got['mobile_data1']))
        self.assertEqual(('0', '1', '1'), (got['airplane_mode_on'], got['wifi_on'], got['multi_sim_data_call']))
        self.assertEqual(['settings_global.xml'], left)

    def test_hyperos_switched_off_in_both_slots(self):
        lines, after, _ = self.run_block(settings(mobile_data='0', mobile_data0='0', mobile_data1='0', multi_sim_data_call='2'))
        got = self.values(after)
        self.assertEqual(('1', '1', '1'), (got['mobile_data'], got['mobile_data0'], got['mobile_data1']))
        self.assertNotIn('mobile_data2', got)
        self.assertEqual(3, len(lines))

    def test_hyperos_needs_no_guest_data_sub(self):
        lines, after, _ = self.run_block(settings(mobile_data='0'))
        got = self.values(after)
        self.assertEqual(('1', '1', '1'), (got['mobile_data'], got['mobile_data0'], got['mobile_data1']))
        # A linked jar (the guarded one bound over it) is HyperOS too.
        lines, after, _ = self.run_block(settings(mobile_data='0'), miui='link')
        self.assertEqual('1', self.values(after)['mobile_data0'])

    def test_a_first_hyperos_start_has_no_settings_file(self):
        lines, after, left = self.run_block(None)
        self.assertEqual((['Guest settings_global: no text settings file, not seeded'], None, []), (lines, after, left))
        # A binary settings file is left alone.
        blob = b'ABX\x00\x10\x00\x08settings'
        lines, after, left = self.run_block(blob)
        self.assertEqual((['Guest settings_global: no text settings file, not seeded'], blob, ['settings_global.xml']),
                         (lines, after, left))

    def test_one_ui_off_or_the_switch_leaves_the_guest_alone(self):
        text = settings(mobile_data='0', mobile_data0='0', multi_sim_data_call='1')
        for miui in ('file', None):
            for host, env, said in (('0', None, '0'), (None, None, 'unknown'), ('1', {'ONEOS_GUEST_MOBILE_DATA': '0'}, '1')):
                with self.subTest((miui, host, env)):
                    lines, after, _ = self.run_block(text, host=host, miui=miui, env=env)
                    self.assertEqual([f'Guest mobile data: left as it is (One UI: {said}, guest data sub: 1)'], lines)
                    self.assertEqual(text.encode(), after)

    def test_the_other_systems_keep_the_key_of_the_data_sub(self):
        lines, after, _ = self.run_block(settings(mobile_data='0', mobile_data2='0', multi_sim_data_call='2'), miui=None)
        self.assertEqual(['Guest settings_global: mobile_data=1', 'Guest settings_global: mobile_data2=1'], lines)
        got = self.values(after)
        self.assertEqual(('1', '1'), (got['mobile_data'], got['mobile_data2']))
        self.assertFalse({'mobile_data0', 'mobile_data1'} & set(got), got)
        text = settings(mobile_data='0')
        lines, after, _ = self.run_block(text, miui=None)
        self.assertEqual((['Guest mobile data: left as it is (One UI: 1, guest data sub: none)'], text.encode()), (lines, after))


if __name__ == '__main__':
    unittest.main()
