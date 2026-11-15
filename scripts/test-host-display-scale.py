#!/usr/bin/env python3
"""One UI's display scale as oneos_switch.sh reads it from one "dumpsys display" (density, main panel width, display 0)."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'switcher/assets/oneos_switch.sh').read_text()


def part(start, end):
    return start + SOURCE.split(start, 1)[1].split(end, 1)[0] + end


CODE = (part('cut_after() {', '\n') + part("HLINE=$(grep 'DisplayDeviceInfo{'", '\n') +
        part('MLINE=$(printf', 'esac\necho "preflight: display scale done').rsplit('\n', 1)[0] + '\n')


def device(name, uid, w, h, cutout=None, flags='FLAG_ALLOWED_TO_BE_DEFAULT_DISPLAY, FLAG_ROTATES_WITH_CONTENT'):
    cut = ''
    if cutout:
        dw, pw, ph = cutout
        cut = (f', cutout DisplayCutout{{insets=Rect(0, 80 - 0, 0) cutoutPathParserInfo=CutoutPathParserInfo{{displayWidth={dw} displayHeight={h} '
               f'physicalDisplayWidth={pw} physicalDisplayHeight={ph} density={{2.8}} cutoutSpec={{M 0,0 H -24 V 73.5 H 24 V 0 H 0 Z @dp}} rotation={{0}}}}}}')
    return (f'    DisplayDeviceInfo{{"{name}": uniqueId="local:{uid}", {w} x {h}, modeId 1, renderFrameRate 120.0, density 450, 386.0 x 386.0 dpi, '
            f'type INTERNAL, address {{port=0, model=0x1}}, state ON, {flags}{cut}, roundedCorners RoundedCorners{{[RoundedCorner{{position=TopLeft, radius=95, center=Point(95, 95)}}]}}}}\n')


def info(kind, mode, modes, density, android17=True):
    # One UI 9 puts three fields before a mode's width; One UI 8 has the width right after the id.
    more = 'parentModeId=-1, sfModeId=0, flags=, ' if android17 else ''
    listed = ', '.join(f'{{id={i}, {more}width={w}, height={h}, fps=120.0, vsync=120.0, alternativeRefreshRates=[60.0], supportedHdrTypes=[2, 3, 4]}}' for i, w, h in modes)
    w, h = next((w, h) for i, w, h in modes if i == mode)
    return (f'    m{kind}DisplayInfo=DisplayInfo{{"Built-in Screen", displayId 0, displayGroupId 0, FLAG_SECURE, real {w} x {h}, largest app {h} x {h}, '
            f'appVsyncOff 1000000, presDeadline 10000000, mode {mode}, renderFrameRate 120.0, defaultMode 1, userPreferredModeId -1, supportedModes [{listed}], '
            f'hdrCapabilities HdrCapabilities{{mSupportedHdrTypes=[2, 3]}}, rotation 0, density {density} (386.0 x 386.0) dpi, layerStack 0, type INTERNAL}}\n')


def scale(dump):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / 'display_host.txt').write_text(dump)
        out = subprocess.run(['/bin/sh', '-c', CODE], env=dict(os.environ, STAGE=d), check=True, capture_output=True, text=True).stdout
        read = lambda n: (Path(d) / n).read_text().strip() if (Path(d) / n).exists() else None
        return read('host_display'), read('host_panel_size'), out


SLAB_MODES = [(11, 720, 1560), (1, 1440, 3120), (2, 1080, 2340)]
SLAB = device('Built-in Screen', 1111, 1080, 2340, cutout=(1080, 1440, 3120))
FOLD = device('Inner', 2222, 1968, 2184, cutout=(1968, 1968, 2184)) + device('Cover', 3333, 1080, 2520, cutout=(1080, 1080, 2520))


class HostDisplayScale(unittest.TestCase):
    def test_a_panel_run_below_its_own_resolution_with_a_display_size_setting(self):
        dump = SLAB + info('Base', 2, SLAB_MODES, 450) + info('Override', 2, SLAB_MODES, 420)
        self.assertEqual(('density=420 width=1080 physical=1440', '1440 3120'), scale(dump)[:2])

    def test_the_older_mode_text_reads_the_same(self):
        dump = SLAB + info('Base', 2, SLAB_MODES, 450, android17=False) + info('Override', 2, SLAB_MODES, 420, android17=False)
        self.assertEqual('density=420 width=1080 physical=1440', scale(dump)[0])

    def test_no_display_size_setting_gives_the_base_density(self):
        dump = SLAB + info('Base', 1, SLAB_MODES, 450) + '    mOverrideDisplayInfo=null\n'
        self.assertEqual('density=450 width=1080 physical=1440', scale(dump)[0])

    def test_a_panel_without_a_cutout_is_read_at_the_size_it_reports(self):
        dump = device('Built-in Screen', 4444, 1600, 2560) + info('Base', 1, [(1, 1600, 2560)], 340)
        self.assertEqual(('density=340 width=1600 physical=1600', '1600 2560'), scale(dump)[:2])

    def test_a_fold_is_recorded_open_and_not_shut(self):
        modes = [(1, 1968, 2184)]
        self.assertEqual('density=420 width=1968 physical=1968', scale(FOLD + info('Base', 1, modes, 420))[0])
        shut, panel, out = scale(FOLD + info('Base', 1, [(1, 1080, 2520)], 420))
        self.assertEqual((None, '1968 2184'), (shut, panel))
        self.assertIn("One UI's display 0 (1080 px) is not the main panel (1968 px), not recorded", out)

    def test_nothing_read_records_nothing(self):
        for dump in ('', SLAB, info('Base', 2, SLAB_MODES, 450)):
            display, _, out = scale(dump)
            self.assertIsNone(display)
            self.assertIn('Host display scale: not read', out)


if __name__ == '__main__':
    unittest.main()
