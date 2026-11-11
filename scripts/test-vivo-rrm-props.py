#!/usr/bin/env python3
"""vivo's refresh-rate manager for an OriginOS session (guest_props.sh add): off where One UI's mode groups are 256 or more."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'switcher/assets/guest_props.sh').read_text()
START = '    if [ -f "$ROOTFS/system/framework/vivo-services.jar" ]; then\n        VRM=persist.sys.vivo.refresh_rate_manager\n'
END = "    # Nothing OS's ringtones"
CODE = START + SOURCE.split(START, 1)[1].split(END, 1)[0]
VRM = 'persist.sys.vivo.refresh_rate_manager'


def mode(i, res, hz, group, active=False):
    head = '    activeMode=' if active else '        '
    return f'{head}{{id={i}, hwcId={i}, resolution={res}, vsyncRate={hz}.00 Hz, dpi=375.78x377.09, group={group}, vrrConfig=N/A, hdrOutputType=INVALID}}\n'


# One UI's SurfaceFlinger as oneos_switch.sh records it (display_modes_host.log).
S23_ULTRA = ('Display 1 (HWC display 0): port=0 pnpId=SDC displayName=""\n' + mode(9, '1080x2316', 60, 1080, True) +
             mode(0, '1440x3088', 120, 1440) + mode(7, '1080x2316', 120, 1080) + mode(9, '1080x2316', 60, 1080) + mode(14, '720x1544', 120, 720) +
             'mSupportedModes=[DisplayModeRecord{mMode={id=1, width=1440, height=3088, fps=120.0}}]\n')
S25 = mode(2, '1080x2340', 60, 0, True) + mode(0, '1080x2340', 120, 0) + mode(2, '1080x2340', 60, 0)
FOLD = mode(1, '1968x2184', 120, 0, True) + mode(0, '1968x2184', 60, 0) + mode(3, '1080x2520', 120, 1, True) + mode(2, '1080x2520', 60, 1)


class VivoRefreshRateManager(unittest.TestCase):
    def run_case(self, host_log, vivo=True, held=None, new='ro.guest.other=1\n', env=None, rp_fails=False):
        """held: None when One UI does not hold the property, else its value there."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); store = root / 'props'; store.mkdir(); stage = root / 'stage'; stage.mkdir()
            fw = root / 'rootfs/system/framework'; fw.mkdir(parents=True)
            if vivo: (fw / 'vivo-services.jar').write_text('')
            if host_log is not None: (stage / 'display_modes_host.log').write_text(host_log)
            names = ['ro.build.id']
            if held is not None:
                (store / VRM).write_text(held); names.append(VRM)
            (root / 'host').write_text(''.join(n + '\n' for n in names))
            (root / 'new').write_text(new)
            rp = root / 'rp'
            rp.write_text('#!/bin/sh\n[ "$1" = -n ] || exit 2\n' + ('exit 1\n' if rp_fails else 'printf "%s" "$3" > "$PROPS/$2"\n'))
            rp.chmod(0o755)
            prefix = 'getprop() { [ -f "$PROPS/$1" ] && cat "$PROPS/$1"; }\n'
            e = {**os.environ, 'PROPS': str(store), 'RP': str(rp), 'OVR': str(root / 'ovr'), 'HOST': str(root / 'host'),
                 'NEW': str(root / 'new'), 'STAGE': str(stage), 'ROOTFS': str(root / 'rootfs'), **(env or {})}
            out = subprocess.run(['sh', '-c', prefix + CODE], env=e, check=True, capture_output=True, text=True).stdout.splitlines()
            added = [l for l in (root / 'new').read_text().splitlines() if l.startswith(VRM)]
            ovr = (root / 'ovr').read_text() if (root / 'ovr').exists() else ''
            now = (store / VRM).read_text() if (store / VRM).exists() else None
            return out, added, ovr, now

    def test_s23_ultra_switches_the_manager_off(self):
        out, added, ovr, now = self.run_case(S23_ULTRA)
        self.assertEqual([VRM + '=false'], added)
        self.assertEqual(('', None), (ovr, now))
        self.assertEqual([f"guest_props: {VRM}=false for the session (One UI's active display mode group: 1080; "
                          "vivo's refresh-rate manager refuses every mode of a group above 255)"], out)

    def test_the_images_own_value_is_replaced_not_doubled(self):
        _, added, _, _ = self.run_case(S23_ULTRA, new=f'ro.guest.other=1\n{VRM}=true\nro.guest.last=1\n')
        self.assertEqual([VRM + '=false'], added)

    def test_s25_and_fold_keep_the_manager(self):
        for name, log, group in (('S25', S25, '0'), ('Fold', FOLD, '1')):
            with self.subTest(name):
                out, added, ovr, _ = self.run_case(log)
                self.assertEqual(([], ''), (added, ovr))
                self.assertEqual([f"guest_props: vivo's refresh-rate manager kept (One UI's active display mode group: {group})"], out)

    def test_without_one_uis_modes_nothing_changes(self):
        for name, log in (('no file', None), ('no active mode line', mode(0, '1440x3088', 120, 1440)), ('odd value', '    activeMode={id=1, hwcId=1, group=, x}\n')):
            with self.subTest(name):
                out, added, _, _ = self.run_case(log)
                self.assertEqual([], added)
                self.assertEqual(["guest_props: vivo's refresh-rate manager kept (One UI's active display mode group: not read)"], out)

    def test_another_system_is_left_alone(self):
        self.assertEqual(([], [], '', None), self.run_case(S23_ULTRA, vivo=False))

    def test_a_value_one_ui_holds_is_overridden_and_noted_for_the_return(self):
        out, added, ovr, now = self.run_case(S23_ULTRA, held='true')
        self.assertEqual(([], VRM + '=true\n', 'false'), (added, ovr, now))
        self.assertIn(f'{VRM}=false for the session', out[0])

    def test_a_failed_write_is_said(self):
        out, added, ovr, now = self.run_case(S23_ULTRA, held='true', rp_fails=True)
        self.assertEqual(([], '', 'true'), (added, ovr, now))
        self.assertTrue(out[0].startswith(f"guest_props: !!! {VRM} could not be set to false (One UI holds 'true')"), out)

    def test_the_switch_can_be_forced_either_way(self):
        out, added, _, _ = self.run_case(S23_ULTRA, env={'ONEOS_GUEST_VIVO_RRM': '1'})
        self.assertEqual([], added)
        self.assertIn('kept', out[0])
        out, added, _, _ = self.run_case(S25, env={'ONEOS_GUEST_VIVO_RRM': '0'})
        self.assertEqual([VRM + '=false'], added)


if __name__ == '__main__':
    unittest.main()
