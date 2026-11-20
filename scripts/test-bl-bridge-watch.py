#!/usr/bin/env python3
"""The brightness bridge takes the panel node over only from a dead lights HAL.

Extracts the bridge script from guest_start.sh's heredoc and runs it with
stubs (Windows-portable under Git Bash's sh). Three cases:

1. Deaf HAL: the node sits at 0 while the screen is awake and asks for light
   -> the bridge takes the node over and writes proportional values.
2. Healthy HAL: the node moves on its own -> the bridge leaves it alone.
3. The guest asks for dark: a node at 0 with the brightness at minimum is a
   wish, not a dead HAL -> no takeover.

The write loop never ends on its own, so the takeover case runs under a
subprocess timeout and the assertions read the log and the node file.
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'switcher/assets/guest_start.sh').read_text()
BODY = re.search(r"cat > /data/oneos_bl_bridge\.sh <<'BLEOF'\n(.*?)\nBLEOF\n",
                 SOURCE, re.S).group(1)


def posix(p: Path) -> str:
    s = str(p).replace('\\', '/')
    return re.sub(r'^([A-Za-z]):', lambda m: '/' + m.group(1).lower(), s)


class BlBridgeWatch(unittest.TestCase):
    def run_bridge(self, node, brightness, wakefulness='Awake', timeout=90, env=None):
        # The production watch cap is 600 s; the same decision runs here with a
        # small cap so a "left alone" case finishes in seconds. The write loop
        # (in production: until the session ends) is bounded too — the test
        # asserts on what it wrote, not on it running forever.
        body = (BODY.replace('-lt 600', '-lt 18')
                    .replace('while :; do', 'w_n=0; while [ $w_n -lt 25 ]; do w_n=$((w_n + 1));'))
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'bin').mkdir()
            stubs = {
                'sleep': '#!/bin/sh\nexit 0\n',
                'dumpsys': ('#!/bin/sh\n'
                            'case "$1" in\n'
                            '  display) [ -f "$WD/display" ] && cat "$WD/display" ;;\n'
                            '  power) cat "$WD/power" ;;\n'
                            'esac\n'),
                'cmd': ('#!/bin/sh\n'
                        '[ "$1" = display ] && [ "$2" = get-brightness ] && cat "$WD/brightness_out"\n'),
                'getprop': '#!/bin/sh\necho 1\n',
            }
            for name, c in stubs.items():
                p = root / 'bin' / name
                p.write_text(c)
                p.chmod(0o755)
            (root / 'display').write_text(
                '  mScreenBrightnessRangeMinimum=0.0\n'
                '  mScreenBrightnessRangeMaximum=1.0\n'
                '  mScreenBrightnessNormalMaximum=1.0\n'
                '  useSurfaceControl=false (force_anyway? false)\n')
            (root / 'power').write_text(f'  mWakefulness={wakefulness}\n')
            (root / 'brightness_out').write_text(f'{brightness}\n')
            (root / 'node').write_text(f'{node}\n')
            log = root / 'backlight.log'
            e = {k: v for k, v in os.environ.items() if k in ('SYSTEMROOT', 'WINDIR', 'TMP', 'TEMP')}
            wd = posix(root)
            e['PATH'] = f'{wd}/bin:/usr/bin:/bin'
            e['WD'] = wd
            for k, v in (env or {}).items():
                e[k] = v
            # The bridge logs to its stdout; a "left alone" run exits 0 on its
            # own, a takeover run is stopped by the subprocess timeout.
            code = (body.replace("$BL/brightness", f'"{wd}/node"'))
            try:
                out = subprocess.run(
                    ['sh', '-c', f'cd "{wd}" && exec sh -c {repr_shell(code)} sh "'
                                 f'{posix(root / "node")}" 483 193 0'],
                    env=e, capture_output=True, text=True, timeout=timeout)
                text, finished = out.stdout or '', out.returncode == 0
            except subprocess.TimeoutExpired as t:
                text, finished = (t.stdout or '').decode() if isinstance(t.stdout, bytes) else (t.stdout or ''), False
            return text, ((root / 'node').read_text() or '').strip(), finished

    def test_the_script_is_extracted(self):
        self.assertIn('mWakefulness', BODY)
        self.assertIn('taking the node over', BODY)
        self.assertIn('leaving it to the lights HAL', BODY)

    def test_a_dead_hal_is_taken_over(self):
        log, node, finished = self.run_bridge(node=0, brightness=0.35)
        self.assertTrue(finished, 'the bounded write loop should run to its cap')
        self.assertIn('taking the node over', log)
        self.assertNotIn('leaving it to the lights HAL', log)
        # The write loop then drives the node proportionally (0.35 of the
        # guest's normal 255 = 89).
        self.assertEqual('89', node)

    def test_a_live_node_is_left_alone(self):
        log, node, finished = self.run_bridge(node=25, brightness=0.35)
        self.assertTrue(finished, 'the 600 s watch cap should end the run')
        self.assertIn('leaving it to the lights HAL', log)
        self.assertNotIn('taking the node over', log)
        self.assertEqual('25', node)

    def test_a_minimum_setting_is_a_wish_not_a_dead_hal(self):
        log, node, finished = self.run_bridge(node=0, brightness=0.01)
        self.assertTrue(finished, 'the 600 s watch cap should end the run')
        self.assertIn('leaving it to the lights HAL', log)
        self.assertNotIn('taking the node over', log)

    def test_an_asleep_screen_does_not_count(self):
        log, node, finished = self.run_bridge(node=0, brightness=0.35,
                                              wakefulness='Asleep')
        self.assertTrue(finished)
        self.assertIn('leaving it to the lights HAL', log)
        self.assertNotIn('taking the node over', log)

    def test_force_takes_a_thrashing_node_over(self):
        # A stage whose HAL thrashes the node (values jump while the slider sits
        # still) never satisfies the dead-node watch; ONEOS_GUEST_BL_BRIDGE=force
        # takes the node over unconditionally and drives it proportionally.
        log, node, finished = self.run_bridge(node=25, brightness=0.35,
                                              env={'ONEOS_GUEST_BL_BRIDGE': 'force'})
        self.assertTrue(finished, 'the bounded write loop should run to its cap')
        self.assertIn('forced by ONEOS_GUEST_BL_BRIDGE=force', log)
        self.assertNotIn('leaving it to the lights HAL', log)
        self.assertEqual('89', node)

    def test_force_off_leaves_a_live_node_alone(self):
        log, node, finished = self.run_bridge(node=25, brightness=0.35)
        self.assertIn('leaving it to the lights HAL', log)
        self.assertEqual('25', node)


def repr_shell(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


if __name__ == '__main__':
    unittest.main()
