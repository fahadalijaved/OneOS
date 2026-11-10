#!/usr/bin/env python3
"""ColorOS's last-boot records left in One UI's property store are blanked for the session (guest_props.sh add)."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'switcher/assets/guest_props.sh').read_text()
START = '    if [ "$GUEST_OPLUS" = 1 ] && [ "${ONEOS_GUEST_OPLUS_BOOT_KIND:-0}" = 0 ]; then\n'
CODE = START + SOURCE.split(START, 1)[1].split('    if [ "${ONEOS_GUEST_BT_OFFLOAD:-0}" = 0 ]', 1)[0]
CARRIER = 'persist.sys.oplus.my_carrier.data_utc_backup'
COMPANY = 'persist.sys.oplus.company.data_backup'
RECOPY = 'persist.sys.recopy.preload.opinstalled'
NOTE = 'sys.oplus.bootupgrade'


class OplusBootKindProps(unittest.TestCase):
    def run_case(self, props, oplus=1, env=None, rp_fails=False):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); store = root / 'props'; store.mkdir()
            for k, v in props.items(): (store / k).write_text(v)
            rp = root / 'rp'
            rp.write_text('#!/bin/sh\n[ "$1" = -n ] || exit 2\n' + ('exit 1\n' if rp_fails else 'printf "%s" "$3" > "$PROPS/$2"\n'))
            rp.chmod(0o755)
            prefix = 'getprop() { [ -f "$PROPS/$1" ] && cat "$PROPS/$1"; }\n'
            e = {**os.environ, 'PROPS': str(store), 'RP': str(rp), 'OVR': str(root / 'ovr'), 'GUEST_OPLUS': str(oplus), **(env or {})}
            out = subprocess.run(['sh', '-c', prefix + CODE], env=e, check=True, capture_output=True, text=True).stdout
            now = {p.name: p.read_text() for p in store.iterdir()}
            ovr = (root / 'ovr').read_text() if (root / 'ovr').exists() else ''
            return out, now, ovr

    def test_records_with_a_value_are_blanked_and_restorable(self):
        out, now, ovr = self.run_case({CARRIER: '1786738605', RECOPY: 'true', NOTE: '1', 'persist.sys.locale': 'en-GB'})
        self.assertEqual({CARRIER: '', RECOPY: '', NOTE: '', 'persist.sys.locale': 'en-GB'}, now)
        self.assertEqual(f'{CARRIER}=1786738605\n{RECOPY}=true\n', ovr)
        self.assertEqual("guest_props: ColorOS's last-boot records from an earlier session blanked for the session:"
                         f' {CARRIER} {RECOPY} {NOTE}\n', out)

    def test_nothing_to_blank_says_nothing(self):
        out, now, ovr = self.run_case({COMPANY: '', 'persist.sys.locale': 'en-GB'})
        self.assertEqual(('', {COMPANY: '', 'persist.sys.locale': 'en-GB'}, ''), (out, now, ovr))

    def test_other_systems_and_the_switch_keep_them(self):
        props = {CARRIER: '1786738605', NOTE: '1'}
        for kw in ({'oplus': 0}, {'env': {'ONEOS_GUEST_OPLUS_BOOT_KIND': '1'}}):
            with self.subTest(kw):
                self.assertEqual(('', props, ''), self.run_case(props, **kw))

    def test_a_write_that_fails_is_not_recorded(self):
        out, now, ovr = self.run_case({CARRIER: '1786738605'}, rp_fails=True)
        self.assertEqual(('', {CARRIER: '1786738605'}, ''), (out, now, ovr))


if __name__ == '__main__':
    unittest.main()
