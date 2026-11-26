#!/usr/bin/env python3
"""Host display installOrientation capture (oneos_switch.sh), SurfaceFlinger prop
propagation (guest_props.sh), and Galaxy Tab One UI 9.5 detection (guest_prepare.sh)."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SWITCH_SRC = (ROOT / 'switcher/assets/oneos_switch.sh').read_text(encoding='utf-8')
PROPS_SRC = (ROOT / 'switcher/assets/guest_props.sh').read_text(encoding='utf-8')
PREPARE_SRC = (ROOT / 'switcher/assets/guest_prepare.sh').read_text(encoding='utf-8')

SH = shutil.which('sh') or '/bin/sh'


def part(src, start, end):
    return start + src.split(start, 1)[1].split(end, 1)[0] + end


ORIENT_CAPTURE_CODE = (
    part(SWITCH_SRC, 'cut_after() {', '\n')
    + part(SWITCH_SRC, "HLINE=$(grep 'DisplayDeviceInfo{'", '\n')
    + part(SWITCH_SRC, 'MLINE=$(printf', "cut -d' ' -f2-)\n")
    + part(SWITCH_SRC, 'rm -f "$STAGE/host_install_orientation"', 'esac\n')
)

PROPS_ORIENT_CODE = (
    'PDO=ro.surface_flinger.primary_display_orientation'
    + PROPS_SRC.split('PDO=ro.surface_flinger.primary_display_orientation', 1)[1].split('    # OxygenOS 16 on a MediaTek Galaxy', 1)[0]
)

TAB_DETECT_CODE = part(
    PREPARE_SRC,
    'TAB_S9_FE_HOST=0',
    '[ "$ONEUI95_IMAGE" = 1 ] && [ "$TAB_HOST" = 1 ] && ONEUI95_TAB=1\n',
)


def run_sh(code, env):
    return subprocess.run(
        [SH, '-c', code],
        env=dict(os.environ, **env),
        check=True,
        capture_output=True,
        text=True,
    )


def device_line(w, h, install_orientation=None):
    io = f', installOrientation {install_orientation}' if install_orientation is not None else ''
    return (
        f'  DisplayDeviceInfo{{"Built-in Screen": uniqueId="local:4627039422300187648", {w} x {h}, '
        f'modeId 1, renderFrameRate 120.0, density 280, type INTERNAL, state ON, '
        f'FLAG_ALLOWED_TO_BE_DEFAULT_DISPLAY, FLAG_ROTATES_WITH_CONTENT, FLAG_TRUSTED{io}, '
        f'displayShape DisplayShape{{type=2, displayWidth={w}, displayHeight={h}}}}}\n'
    )


class HostDisplayOrientationTest(unittest.TestCase):
    def test_captures_tab_s12_ultra_install_orientation_3(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'display_host.txt').write_text(device_line(1848, 2960, 3), encoding='utf-8')
            out = run_sh(ORIENT_CAPTURE_CODE, {'STAGE': d}).stdout
            self.assertEqual('3', (Path(d) / 'host_install_orientation').read_text(encoding='utf-8').strip())
            self.assertIn('Host install orientation: 3 (panel installed rotated 270 deg)', out)

    def test_ignores_install_orientation_0_or_missing(self):
        for io in (0, None):
            with tempfile.TemporaryDirectory() as d:
                (Path(d) / 'display_host.txt').write_text(device_line(1440, 3120, io), encoding='utf-8')
                run_sh(ORIENT_CAPTURE_CODE, {'STAGE': d})
                self.assertFalse((Path(d) / 'host_install_orientation').exists())

    def test_guest_props_sets_primary_display_orientation_and_replaces_guest_zero(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'host_install_orientation').write_text('3\n', encoding='utf-8')
            (p / 'host').write_text('ro.product.model\n', encoding='utf-8')
            (p / 'new').write_text('ro.surface_flinger.primary_display_orientation=ORIENTATION_0\nfoo=bar\n', encoding='utf-8')
            out = run_sh(PROPS_ORIENT_CODE, {'STAGE': d, 'HOST': str(p / 'host'), 'NEW': str(p / 'new')}).stdout
            lines = (p / 'new').read_text(encoding='utf-8').splitlines()
            self.assertIn('ro.surface_flinger.primary_display_orientation=ORIENTATION_270', lines)
            self.assertNotIn('ro.surface_flinger.primary_display_orientation=ORIENTATION_0', lines)
            self.assertIn('ORIENTATION_270', out)

    def test_guest_props_overrides_host_orientation_0_and_journals_ovr(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'host_install_orientation').write_text('3\n', encoding='utf-8')
            (p / 'host').write_text('ro.surface_flinger.primary_display_orientation\n', encoding='utf-8')
            (p / 'new').write_text('', encoding='utf-8')
            (p / 'ovr').write_text('', encoding='utf-8')
            rp = p / 'fake_rp.sh'
            rp.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$RP_LOG"\n', encoding='utf-8')
            rp.chmod(0o755)
            script = 'getprop() { echo ORIENTATION_0; }\n' + PROPS_ORIENT_CODE
            out = run_sh(
                script,
                {
                    'STAGE': d,
                    'HOST': str(p / 'host'),
                    'NEW': str(p / 'new'),
                    'OVR': str(p / 'ovr'),
                    'RP': str(rp),
                    'RP_LOG': str(p / 'rp.log'),
                },
            ).stdout
            self.assertEqual(
                'ro.surface_flinger.primary_display_orientation=ORIENTATION_0',
                (p / 'ovr').read_text(encoding='utf-8').strip(),
            )
            self.assertIn('-n ro.surface_flinger.primary_display_orientation ORIENTATION_270', (p / 'rp.log').read_text(encoding='utf-8'))
            self.assertIn('overridden to ORIENTATION_270', out)

        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'host_install_orientation').write_text('3\n', encoding='utf-8')
            (p / 'host').write_text('', encoding='utf-8')
            (p / 'new').write_text('', encoding='utf-8')
            run_sh(
                PROPS_ORIENT_CODE,
                {'STAGE': d, 'HOST': str(p / 'host'), 'NEW': str(p / 'new'), 'ONEOS_GUEST_DISPLAY_ORIENTATION': '0'},
            )
            self.assertEqual('', (p / 'new').read_text(encoding='utf-8'))

    def test_oneui95_tab_detection_scopes_hardware_vs_generic_tablet(self):
        script = 'getprop() { echo "$FAKE_MODEL"; }\n' + TAB_DETECT_CODE + 'echo "$TAB_S9_FE_HOST $ONEUI95_TAB_S9_FE $TAB_HOST $ONEUI95_TAB"\n'
        # Tab S12 Ultra: generic One UI 9.5 tablet fixes on, Tab S9 FE hardware fixes off
        r1 = run_sh(script, {'ONEOS_PROFILE': 'tab-s12-ultra', 'FAKE_MODEL': 'SM-X940', 'ONEUI95_IMAGE': '1'}).stdout.strip()
        self.assertEqual('0 0 1 1', r1)
        # Tab S9 FE: both on
        r2 = run_sh(script, {'ONEOS_PROFILE': 'tab-s9-fe', 'FAKE_MODEL': 'SM-X510', 'ONEUI95_IMAGE': '1'}).stdout.strip()
        self.assertEqual('1 1 1 1', r2)
        # S26 Ultra phone: neither on
        r3 = run_sh(script, {'ONEOS_PROFILE': 's-ultra-8850', 'FAKE_MODEL': 'SM-S948B', 'ONEUI95_IMAGE': '1'}).stdout.strip()
        self.assertEqual('0 0 0 0', r3)


if __name__ == '__main__':
    unittest.main()
