#!/usr/bin/env python3
"""MediaTek ColorOS Bluetooth disables incompatible quality reports without changing A2DP behaviour."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'switcher/assets/guest_props.sh').read_text()
START = '    BTO=persist.sys.oplus.bt.use_origin\n'
CODE = START + SOURCE.split(START, 1)[1].split('    # Power key stall (run 32:', 1)[0]
KEY = 'persist.sys.oplus.bt.use_origin'
BQR = 'persist.bluetooth.bqr.event_mask'
G99 = 'MT6789: disable incompatible Bluetooth quality reports without changing A2DP'


class OplusBtOrigin(unittest.TestCase):
    def run_case(self, soc='MT6789', oplus=1, env=None, new='ro.build.id=X\n', host='ro.soc.model\n', props=None, rp_fails=False):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); store = root / 'props'; store.mkdir()
            for k, v in {'ro.soc.model': soc, **(props or {})}.items(): (store / k).write_text(v)
            (root / 'new').write_text(new); (root / 'host').write_text(host)
            rp = root / 'rp'
            rp.write_text('#!/bin/sh\n[ "$1" = -n ] || exit 2\n' + ('exit 1\n' if rp_fails else 'printf "%s" "$3" > "$PROPS/$2"\n'))
            rp.chmod(0o755)
            prefix = 'getprop() { [ -f "$PROPS/$1" ] && cat "$PROPS/$1"; }\n'
            e = {k: v for k, v in os.environ.items() if k != 'ONEOS_GUEST_BT_ORIGIN'}
            e.update({'PROPS': str(store), 'RP': str(rp), 'OVR': str(root / 'ovr'), 'NEW': str(root / 'new'),
                      'HOST': str(root / 'host'), 'GUEST_OPLUS': str(oplus), **(env or {})})
            out = subprocess.run(['sh', '-c', prefix + CODE], env=e, check=True, capture_output=True, text=True)
            self.assertEqual('', out.stderr)
            ovr = (root / 'ovr').read_text() if (root / 'ovr').exists() else ''
            now = {p.name: p.read_text() for p in store.iterdir() if p.name != 'ro.soc.model'}
            return out.stdout, (root / 'new').read_text(), ovr, now

    def test_the_block_is_there(self):
        self.assertIn('auto:MT6789*|0:MT6789*)', CODE)
        self.assertIn('*mt[0-9]*|*MT[0-9]*|*[Mm]edia[Tt]ek*', CODE)
        self.assertLess(len(CODE), 3000)

    def test_a_helio_g99_phone_keeps_normal_a2dp_and_disables_bqr(self):
        for soc in ('MT6789', 'MT6789V/CD'):
            with self.subTest(soc):
                out, new, ovr, now = self.run_case(soc=soc)
                self.assertEqual(f'ro.build.id=X\n{KEY}=false\n{BQR}=0\n', new)
                reason = G99.replace('MT6789', soc)
                self.assertEqual(f'guest_props: {KEY}=false for the session ({reason})\n'
                                 f'guest_props: {BQR}=0 for the session ({reason})\n', out)
                # Nothing of One UI's is touched: the name goes the way of the image's own props.
                self.assertEqual(('', {}), (ovr, now))

    def test_the_images_own_values_are_replaced_not_doubled(self):
        out, new, ovr, now = self.run_case(
            new=f'a=1\n{KEY}=true\n{BQR}=7\npersist.sys.oplus.bt.use_originX=1\nb=2\n')
        self.assertEqual(f'a=1\npersist.sys.oplus.bt.use_originX=1\nb=2\n{KEY}=false\n{BQR}=0\n', new)

    def test_the_whole_mediaTek_family_gets_the_same_treatment(self):
        # MT6877 (A34) had working-Bluetooth reports, but the change only
        # disables diagnostic quality reports and pins OPPO's normal path;
        # both are restored on return. Detected through ro.soc.model ...
        out, new, ovr, now = self.run_case(soc='MT6877')
        reason = G99.replace('MT6789', 'MT6877')
        self.assertEqual(f'ro.build.id=X\n{KEY}=false\n{BQR}=0\n', new)
        self.assertEqual(f'guest_props: {KEY}=false for the session ({reason})\n'
                         f'guest_props: {BQR}=0 for the session ({reason})\n', out)
        # ... and through ro.board.platform when ro.soc.model is empty.
        out, new, ovr, now = self.run_case(soc='', props={'ro.board.platform': 'mt6768'})
        reason = 'MediaTek SoC: disable incompatible Bluetooth quality reports without changing A2DP'
        self.assertEqual(f'ro.build.id=X\n{KEY}=false\n{BQR}=0\n', new)
        self.assertEqual(f'guest_props: {KEY}=false for the session ({reason})\n'
                         f'guest_props: {BQR}=0 for the session ({reason})\n', out)

    def test_other_phones_and_other_systems_are_left_alone(self):
        # Exynos and Qualcomm: OPPO's parser matches their BQR layout, no crash.
        for kw in ({'soc': 'SM8850'}, {'soc': 's5e8845'}, {'soc': ''}, {'oplus': 0},
                   {'env': {'ONEOS_GUEST_BT_ORIGIN': 'yes'}}):
            with self.subTest(kw):
                self.assertEqual(('', 'ro.build.id=X\n', '', {}), self.run_case(**kw))
        # Explicit values other than 0/auto leave every phone alone, and the
        # override is a no-op without a ColorOS guest.
        self.assertEqual(('', 'ro.build.id=X\n', '', {}),
                         self.run_case(soc='MT6877', env={'ONEOS_GUEST_BT_ORIGIN': 'yes'}))

    def test_the_override_sets_it_on_any_phone_with_a_coloros_guest(self):
        out, new, ovr, now = self.run_case(soc='SM8850', env={'ONEOS_GUEST_BT_ORIGIN': '1'})
        self.assertEqual((f'guest_props: {KEY}=true for the session (ONEOS_GUEST_BT_ORIGIN=1)\n', f'ro.build.id=X\n{KEY}=true\n'),
                         (out, new))
        self.assertEqual(('', 'ro.build.id=X\n', '', {}), self.run_case(soc='SM8850', oplus=0, env={'ONEOS_GUEST_BT_ORIGIN': '1'}))

    def test_one_ui_values_are_overridden_and_restorable(self):
        # Left behind by a session that never returned: then it is One UI's to get back.
        host = f'ro.soc.model\n{KEY}\n{BQR}\n'
        out, new, ovr, now = self.run_case(host=host, props={KEY: 'true', BQR: '7'})
        self.assertEqual((f'guest_props: {KEY}=true overridden to false for the session ({G99})\n'
                          f'guest_props: {BQR}=7 overridden to 0 for the session ({G99})\n', 'ro.build.id=X\n',
                          f'{KEY}=true\n{BQR}=7\n', {KEY: 'false', BQR: '0'}), (out, new, ovr, now))
        # Already safe, or writes that fail: nothing is recorded or announced.
        self.assertEqual(('', 'ro.build.id=X\n', '', {KEY: 'false', BQR: '0'}),
                         self.run_case(host=host, props={KEY: 'false', BQR: '0'}))
        self.assertEqual(('', 'ro.build.id=X\n', '', {KEY: 'true', BQR: '7'}),
                         self.run_case(host=host, props={KEY: 'true', BQR: '7'}, rp_fails=True))


if __name__ == '__main__':
    unittest.main()
