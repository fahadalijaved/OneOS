#!/usr/bin/env python3
"""The RenderEngine choice for a session (guest_props.sh add), run with a grep that, like the phone's, has no "\\|"."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'switcher/assets'
SOURCE = (ASSETS / 'guest_props.sh').read_text()
START = '    RR=persist.sys.renderengine.retry\n'
END = '    REV=${ONEOS_GUEST_RE_BACKEND-$REV}\n'
CODE = (START + SOURCE.split(START, 1)[1].split(END, 1)[0]) \
    .replace('/sys/class/kgsl/kgsl-3d0/gpu_model', '$KGSL').replace('/vendor/lib64/egl/libGLES_mali.so', '$MALI') + 'echo "REV=$REV"\n'
RR = 'persist.sys.renderengine.retry'
REAL_GREP = next(p for p in ('/usr/bin/grep', '/bin/grep') if os.path.exists(p))
# toybox grep on bionic: "\|" in a basic expression is a plain "|", not "or".
PHONE_GREP = f'''#!/bin/sh
ext=0
for a in "$@"; do case "$a" in -*E*) ext=1 ;; esac; done
if [ $ext = 0 ]; then
    n=$#; i=0
    while [ $i -lt $n ]; do
        a=$1; shift
        case "$a" in -*) ;; *) a=$(printf '%s' "$a" | sed 's/\\\\|/[|]/g') ;; esac
        set -- "$@" "$a"; i=$((i + 1))
    done
fi
exec {REAL_GREP} "$@"
'''
A25 = {'ro.board.platform': 'universal8825', 'ro.hardware': 's5e8825', 'ro.soc.manufacturer': 'Samsung'}
A34 = {'ro.board.platform': 'mt6877', 'ro.hardware': 'mt6877', 'ro.soc.manufacturer': 'Mediatek'}
S23FE = {'ro.board.platform': 'universal9925', 'ro.hardware': 's5e9925', 'ro.soc.manufacturer': 'Samsung'}
S22U = {'ro.board.platform': 'taro', 'ro.hardware': 'qcom', 'ro.soc.manufacturer': 'QTI'}


class RenderEngineProps(unittest.TestCase):
    def run_case(self, phone, image_retry='1', host=None, mali=True, kgsl=False, image='oxygenos16-cph2745', env=None, rp_fails=False):
        """host: None when One UI does not hold the retry property, else its value there."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); store = root / 'props'; store.mkdir(); stage = root / 'stage'; stage.mkdir(); bin_ = root / 'bin'; bin_.mkdir()
            for k, v in phone.items(): (store / k).write_text(v)
            names = list(phone)
            if host is not None:
                (store / RR).write_text(host); names.append(RR)
            (root / 'host').write_text(''.join(n + '\n' for n in names))
            (root / 'new').write_text('ro.guest.other=1\n' + (f'{RR}={image_retry}\n' if image_retry is not None else ''))
            (stage / '.oneos_stage').write_text('{"image": "%s", "set": "x"}\n' % image)
            if mali: (root / 'mali.so').write_text('')
            if kgsl: (root / 'gpu_model').write_text('Adreno')
            (bin_ / 'grep').write_text(PHONE_GREP); (bin_ / 'grep').chmod(0o755)
            rp = root / 'rp'
            rp.write_text('#!/bin/sh\n[ "$1" = -n ] || exit 2\n' + ('exit 1\n' if rp_fails else 'printf "%s" "$3" > "$PROPS/$2"\n'))
            rp.chmod(0o755)
            prefix = 'getprop() { [ -f "$PROPS/$1" ] && cat "$PROPS/$1"; }\n'
            e = {**os.environ, 'PATH': f'{bin_}:{os.environ["PATH"]}', 'PROPS': str(store), 'RP': str(rp), 'OVR': str(root / 'ovr'),
                 'HOST': str(root / 'host'), 'NEW': str(root / 'new'), 'STAGE': str(stage), 'MALI': str(root / 'mali.so'),
                 'KGSL': str(root / 'gpu_model'), **(env or {})}
            out = subprocess.run(['sh', '-c', prefix + CODE], env=e, check=True, capture_output=True, text=True).stdout.splitlines()
            new = [l for l in (root / 'new').read_text().splitlines() if l.startswith(RR)]
            ovr = (root / 'ovr').read_text() if (root / 'ovr').exists() else ''
            held = (store / RR).read_text() if (store / RR).exists() else None
            return out[:-1], out[-1], new, ovr, held

    def test_the_phone_grep_stand_in_has_no_or_in_basic_expressions(self):
        with tempfile.TemporaryDirectory() as d:
            g = Path(d) / 'grep'; g.write_text(PHONE_GREP); g.chmod(0o755)
            run = lambda *a: subprocess.run([str(g), *a], input='retry=1\n', text=True, capture_output=True).returncode
            self.assertEqual(1, run('-q', r'^retry=\(1\|true\)$'))
            self.assertEqual(0, run('-qE', r'^retry=(1|true)$'))
            self.assertEqual(0, run('-qxF', 'retry=1'))

    def test_a25_with_the_images_retry_value_runs_the_images_skiagl(self):
        # 0.4.83/0.4.84 (288aabca, 6435d433): One UI does not hold the property, the image's build.prop says 1.
        lines, rev, new, ovr, held = self.run_case(A25)
        self.assertEqual('REV=', rev)
        self.assertEqual([f'{RR}=0'], new)
        self.assertEqual(('', None), (ovr, held))
        self.assertEqual([
            f'guest_props: {RR}=0 for the session (no Adreno: SkiaGL would wait for kgsl forever)',
            f"guest_props: Mali Exynos (universal8825/s5e8825/Samsung): the image's RenderEngine (SkiaGL; SkiaVk fails on this driver), {RR}=0 (was '0')",
        ], lines)

    def test_a25_whose_one_ui_holds_the_property(self):
        for value, first in (('1', [f'guest_props: {RR}=1 overridden to 0 for the session (no Adreno: SkiaGL would wait for kgsl forever)']), ('', [])):
            with self.subTest(value):
                lines, rev, new, ovr, held = self.run_case(A25, host=value)
                self.assertEqual(('REV=', '0', f'{RR}={value}\n'), (rev, held, ovr))
                self.assertEqual([f'{RR}=1'], new)   # One UI's store wins over the image's line; it is left as it was
                was = '0' if value == '1' else ''
                self.assertEqual(first + [f"guest_props: Mali Exynos (universal8825/s5e8825/Samsung): the image's RenderEngine "
                                          f"(SkiaGL; SkiaVk fails on this driver), {RR}=0 (was '{was}')"], lines)

    def test_a25_with_no_retry_value_anywhere_gets_zero_by_name(self):
        lines, rev, new, ovr, held = self.run_case(A25, image_retry=None)
        self.assertEqual(('REV=', [f'{RR}=0'], ''), (rev, new, ovr))
        self.assertIn("(was '')", lines[-1])

    def test_a_write_that_fails_is_said_and_not_recorded(self):
        lines, rev, new, ovr, held = self.run_case(A25, host='1', rp_fails=True)
        self.assertEqual(('REV=', '1', ''), (rev, held, ovr))
        self.assertEqual([f"guest_props: Mali Exynos (universal8825/s5e8825/Samsung): the image's RenderEngine (SkiaGL; SkiaVk fails on this driver), "
                          f"!!! {RR} could not be set to 0 (One UI holds '1'): SkiaGL may wait for kgsl"], lines)

    def test_the_switch_keeps_the_images_value_and_vulkan(self):
        lines, rev, new, ovr, held = self.run_case(A25, env={'ONEOS_GUEST_RE_RETRY': '1'})
        self.assertEqual(('REV=skiavkthreaded', [f'{RR}=1'], ''), (rev, new, ovr))
        self.assertEqual([f'guest_props: Mali Exynos (universal8825/s5e8825/Samsung) with {RR}=1: Vulkan RenderEngine kept '
                          '(ONEOS_GUEST_RE_RETRY=1; SkiaGL would wait for kgsl)'], lines)

    def test_mediatek_and_xclipse_keep_vulkan(self):
        for name, phone, mali in (('A34', A34, True), ('S23 FE', S23FE, False)):
            with self.subTest(name):
                lines, rev, new, ovr, held = self.run_case(phone, mali=mali)
                self.assertEqual(('REV=skiavkthreaded', [f'{RR}=0'], ''), (rev, new, ovr))
                self.assertEqual([f'guest_props: {RR}=0 for the session (no Adreno: SkiaGL would wait for kgsl forever)'], lines)

    def test_adreno_is_left_alone(self):
        lines, rev, new, ovr, held = self.run_case(S22U, mali=False, kgsl=True)
        self.assertEqual(([], 'REV=', [f'{RR}=1'], ''), (lines, rev, new, ovr))

    def test_other_systems_on_the_a25_only_lose_the_wait(self):
        lines, rev, new, ovr, held = self.run_case(A25, image='coloros17-x9u-in')
        self.assertEqual(('REV=', [f'{RR}=0']), (rev, new))
        self.assertEqual([f'guest_props: {RR}=0 for the session (no Adreno: SkiaGL would wait for kgsl forever)'], lines)


class PhoneGrep(unittest.TestCase):
    """No "\\|" in a grep without -E in any script that runs on the phone."""
    # The composer-rejection count of the session watcher: it has never counted, and turning it on arms the
    # watcher's GPU-composition switch and its black-screen return for the whole session. The owner's decision.
    KNOWN = {("oneos_switch.sh", r"grep -c 'presentOrValidate failed\|executeCommands failed'")}

    def test_every_alternation_uses_extended_expressions(self):
        bad = []
        for f in sorted(ASSETS.glob('*.sh')):
            for n, line in enumerate(f.read_text().splitlines(), 1):
                if line.lstrip().startswith('#') or '\\|' not in line: continue
                for m in re.finditer(r'\bgrep\b((?:\s+-[A-Za-z0-9]+(?:\s+\d+)?)*)\s+([^|]*(?:\\\|[^|]*)+)', line):
                    if 'E' in re.sub(r'\s\d+', '', m.group(1)): continue
                    if any(f.name == name and text in line for name, text in self.KNOWN): continue
                    bad.append(f'{f.name}:{n}: {m.group(0)[:80]}')
        self.assertEqual([], bad)


if __name__ == '__main__':
    unittest.main()
