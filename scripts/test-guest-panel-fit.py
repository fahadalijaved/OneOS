#!/usr/bin/env python3
"""The camera hole property for the size a guest runs the panel at (oneos_switch.sh: guest_panel_fit.sh, fit_guest_panel)
and the UI activator's script as the switch hands it to the shell (it must parse for every kind of guest)."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'switcher/assets/oneos_switch.sh').read_text()
KEY = 'ro.oplus.display.screenhole.positon'
FIT = SOURCE.split("<<'FIT'\n", 1)[1].split('\nFIT\n', 1)[0] + '\n'
WATCH = 'fit_guest_panel() {' + SOURCE.split('fit_guest_panel() {', 1)[1].split('\n}\n', 1)[0] + '\n}\n'

GETPROP = '#!/bin/sh\nsed -n "s/^$1=//p" "$PROPS" | head -n 1\n'
RESETPROP = ('#!/bin/sh\n[ "$1" = -n ] && shift\n[ ! -f "$PROPS.readonly" ] || exit 0\n'
             'grep -v "^$1=" "$PROPS" > "$PROPS.new"\necho "$1=$2" >> "$PROPS.new"\nmv "$PROPS.new" "$PROPS"\n')
# busybox: "nsenter ... wm size -d 0" answers with the next line of wm_sizes (the last one again after that) and
# ends the session when there is none; any other applet is the server's own.
BUSYBOX = ('#!/bin/sh\nif [ "$1" != nsenter ]; then exec "$@"; fi\n'
           'n=$(cat "$STAGE/calls" 2>/dev/null); n=$((${n:-0} + 1)); echo $n > "$STAGE/calls"\n'
           'line=$(sed -n "${n}p" "$STAGE/wm_sizes")\n'
           '[ -n "$line" ] || line=$(tail -n 1 "$STAGE/wm_sizes")\n'
           'case "$line" in end) touch "$STAGE/data/oneos_rec_stop" ;; none) ;; *) echo "Physical size: $line"; echo "Override size: 1x1" ;; esac\n')


class Stage:
    def __init__(self, d, panel='1440 3120', hole='686,34:756,104', prop=None):
        self.d = Path(d)
        (self.d / 'bin').mkdir()
        (self.d / 'stage/data').mkdir(parents=True)
        for name, text in (('getprop', GETPROP), ('resetprop', RESETPROP), ('busybox', BUSYBOX), ('timeout', '#!/bin/sh\nshift\nexec "$@"\n')):
            (self.d / 'bin' / name).write_text(text)
            (self.d / 'bin' / name).chmod(0o755)
        if panel is not None:
            (self.d / 'stage/host_panel_size').write_text(panel + '\n')
        if hole is not None:
            (self.d / 'stage/host_screenhole').write_text(hole + '\n')
        value = hole if prop is None else prop
        (self.d / 'props').write_text(f'ro.other=1\n{KEY}={value}\n' if value else 'ro.other=1\n')
        (self.d / 'stage/guest_panel_fit.sh').write_text(FIT)
        self.env = dict(os.environ, STAGE=str(self.d / 'stage'), BB=str(self.d / 'bin/busybox'), RP=str(self.d / 'bin/resetprop'),
                        PROPS=str(self.d / 'props'), PATH=str(self.d / 'bin') + os.pathsep + os.environ['PATH'])

    def fit(self, *args):
        r = subprocess.run(['/bin/sh', str(self.d / 'stage/guest_panel_fit.sh'), *args], env=self.env, capture_output=True, text=True, timeout=60)
        assert r.returncode == 0 and r.stderr == '', (r.returncode, r.stderr)
        return r.stdout

    def prop(self):
        got = re.findall(rf'^{re.escape(KEY)}=(.*)$', (self.d / 'props').read_text(), re.M)
        return got[-1] if got else None

    def width(self):
        f = self.d / 'stage/guest_hole_width'
        return f.read_text().strip() if f.exists() else None


class GuestPanelFit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def stage(self, **kw):
        return Stage(self.tmp.name, **kw)

    def test_s24_plus_at_fhd(self):
        s = self.stage()
        out = s.fit('1080', '2340')
        self.assertEqual(('515,26:567,78', '1080'), (s.prop(), s.width()))
        self.assertEqual(f'guest_panel_fit: the guest runs the 1440x3120 panel at 1080x2340: {KEY}=515,26:567,78, '
                         'the camera hole at that size (was 686,34:756,104)\n', out)
        # 515 < 540 < 567: the centre type on a display 1080 px wide.
        self.assertEqual('', s.fit('1080', '2340'))
        self.assertEqual(('515,26:567,78', '1080'), (s.prop(), s.width()))

    def test_whole_panel_is_left_alone(self):
        s = self.stage()
        self.assertEqual('', s.fit('1440', '3120'))
        self.assertEqual(('686,34:756,104', None), (s.prop(), s.width()))

    def test_size_changes_follow(self):
        s = self.stage()
        s.fit('1080', '2340')
        out = s.fit('720', '1560')
        self.assertEqual(('343,17:378,52', '720'), (s.prop(), s.width()))
        self.assertIn('at 720x1560', out)
        self.assertIn('(was 515,26:567,78)', out)
        out = s.fit('1440', '3120')
        self.assertEqual(('686,34:756,104', '1440'), (s.prop(), s.width()))
        self.assertIn('(was 343,17:378,52)', out)
        self.assertEqual('', s.fit('1440', '3120'))

    def test_late_says_so(self):
        s = self.stage()
        out = s.fit('1080', '2340', 'late')
        self.assertTrue(out.endswith('(was 686,34:756,104); SystemUI was up already and may keep the earlier value until its status bar starts again\n'), out)

    def test_props_added_again_with_an_old_width_record(self):
        # A new start of the guest's props: the panel's value is back, the record is of the session before.
        s = self.stage()
        s.fit('1080', '2340')
        (s.d / 'props').write_text(f'{KEY}=686,34:756,104\n')
        self.assertIn('at 1080x2340', s.fit('1080', '2340'))
        self.assertEqual(('515,26:567,78', '1080'), (s.prop(), s.width()))
        (s.d / 'props').write_text(f'{KEY}=686,34:756,104\n')
        self.assertEqual('', s.fit('1440', '3120'))
        self.assertEqual(('686,34:756,104', None), (s.prop(), s.width()))

    def test_another_shape_is_not_this_panel(self):
        s = self.stage(panel='1080 2640', hole='500,30:580,110')
        for size in (('720', '748'), ('1080', '2340'), ('2640', '1080')):
            self.assertEqual('', s.fit(*size))
        self.assertEqual(('500,30:580,110', None), (s.prop(), s.width()))
        # The S22 Ultra's modes are the panel's shape to a pixel or two.
        s2 = Stage(tempfile.mkdtemp(dir=self.tmp.name), panel='1440 3088', hole='684,40:756,112')
        s2.fit('1080', '2316')
        self.assertEqual('513,30:567,84', s2.prop())

    def test_a_value_oneos_did_not_place_stays(self):
        for value in ('679,40:762,123', '0,0:0,0'):
            s = Stage(tempfile.mkdtemp(dir=self.tmp.name), prop=value)
            out = s.fit('1080', '2340')
            self.assertEqual((value, None), (s.prop(), s.width()))
            self.assertEqual(f"guest_panel_fit: {KEY} is {value}, not a value OneOS placed: left alone (the guest's display is 1080x2340)\n", out)

    def test_nothing_to_go_by(self):
        cases = (dict(panel=None), dict(panel='1440'), dict(panel='0 3120'), dict(panel='1440 x'), dict(hole=None, prop='686,34:756,104'),
                 dict(hole='686,34', prop='686,34'), dict(prop=''))
        for kw in cases:
            s = Stage(tempfile.mkdtemp(dir=self.tmp.name), **kw)
            before = s.prop()
            self.assertEqual('', s.fit('1080', '2340'), kw)
            self.assertEqual((before, None), (s.prop(), s.width()), kw)
        s = self.stage()
        for args in ((), ('1080',), ('1080', ''), ('x', '2340'), ('0', '0'), ('1080', '-2340'), ('1080000', '2340000')):
            self.assertEqual('', s.fit(*args), args)
        self.assertEqual(('686,34:756,104', None), (s.prop(), s.width()))

    def test_no_hole_stays_no_hole_quietly(self):
        s = self.stage(hole='0,0:0,0')
        self.assertEqual('', s.fit('1080', '2340'))
        self.assertEqual(('0,0:0,0', None), (s.prop(), s.width()))

    def test_a_property_that_does_not_take_is_said(self):
        s = self.stage()
        (s.d / 'props.readonly').write_text('')
        out = s.fit('1080', '2340')
        self.assertEqual(f"!!! guest_panel_fit: {KEY} not set to 515,26:567,78 for the guest's 1080x2340 (it is 686,34:756,104)\n", out)
        self.assertIsNone(s.width())

    def watch(self, s, sizes, form='phone', pid=None):
        (s.d / 'stage/wm_sizes').write_text('\n'.join(sizes) + '\n')
        (s.d / 'stage/guest_mntns').write_text('mnt:[4026533000]\n')
        gate = SOURCE.split(WATCH, 1)[1].split('\nfi\n', 1)[0] + '\nfi\n'
        self.assertTrue(gate.startswith('if [ "${ONEOS_GUEST_FORM:-fold}" != fold ]') and 'fit_guest_panel </dev/null &' in gate, gate)
        # One second on the clock for every look at it.
        clock = 'date() { c=$(cat "$STAGE/clock" 2>/dev/null); c=$((${c:-0} + 1)); echo $c > "$STAGE/clock"; echo $c; }\n'
        code = 'sleep() { :; }\n' + clock + (WATCH + gate).replace('/system/bin/sh', '/bin/sh') + 'wait\n'
        env = dict(s.env, ONEOS_GUEST_FORM=form, TAKEOVER_PID=str(pid or os.getpid()))
        r = subprocess.run(['/bin/sh', '-c', code], env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual((0, ''), (r.returncode, r.stderr))
        calls = s.d / 'stage/calls'
        return r.stdout, int(calls.read_text()) if calls.exists() else 0

    def test_watcher_fits_when_the_window_manager_answers_and_follows_a_change(self):
        s = self.stage()
        out, calls = self.watch(s, ['none', 'none', '1080x2340', '1080x2340', '720x1560', 'end'])
        self.assertEqual(6, calls)
        self.assertEqual(['at 1080x2340', 'at 720x1560'], re.findall(r'at \d+x\d+', out))
        self.assertEqual(('343,17:378,52', '720'), (s.prop(), s.width()))
        self.assertNotIn('SystemUI was up', out)

    def test_watcher_ends_two_minutes_after_the_first_answer(self):
        s = self.stage()
        out, calls = self.watch(s, ['1440x3120'])
        self.assertEqual(('', 120), (out, calls))
        self.assertIn('[ $((now - t0)) -lt 600 ] || return 0', WATCH)
        self.assertEqual(('686,34:756,104', None), (s.prop(), s.width()))

    def test_watcher_only_for_a_bar_phone_with_the_property_and_a_live_guest(self):
        s = self.stage()
        self.assertEqual(('', 0), self.watch(s, ['1080x2340'], form='fold'))
        self.assertEqual(('', 0), self.watch(s, ['1080x2340'], pid=4194304 + 7))
        (s.d / 'props').write_text('ro.other=1\n')
        self.assertEqual(('', 0), self.watch(s, ['1080x2340']))
        self.assertIsNone(s.prop())

    def test_watcher_looks_for_no_process(self):
        for word in ('pidof', 'pgrep', 'ps ', 'kill', '/proc/[0-9]', 'service list', 'dumpsys'):
            self.assertNotIn(word, WATCH, word)
        self.assertIn('timeout 10 $BB nsenter -t "$TAKEOVER_PID" -m', WATCH)


class ActivatorScript(unittest.TestCase):
    """The activator is one double-quoted string of the switch; a quote too many in it only shows on a phone."""

    def test_it_parses_for_every_kind_of_guest(self):
        start = SOURCE.index('\n$BB sh -c "\n', SOURCE.index('\nGUEST_FOLD_FORM=')) + 1
        end = SOURCE.index('\n" </dev/null >/data/local/tmp/ui_activator.log 2>&1 &\n', start)
        body = SOURCE[start + len('$BB sh -c "\n'):end]
        names = sorted(set(re.findall(r'(?<!\\)\$\{?([A-Za-z_][A-Za-z0-9_]*)', body)))
        self.assertIn('GUEST_OXYGEN', names)
        kinds = ({'GUEST_OPLUS': '1', 'GUEST_AOSP_SYSUI': '0', 'GUEST_MIUI': '0', 'GUEST_FOLD_FORM': '0', 'GUEST_OXYGEN': '1'},
                 {'GUEST_OPLUS': '1', 'GUEST_AOSP_SYSUI': '0', 'GUEST_MIUI': '0', 'GUEST_FOLD_FORM': '1', 'GUEST_OXYGEN': '0'},
                 {'GUEST_OPLUS': '0', 'GUEST_AOSP_SYSUI': '1', 'GUEST_MIUI': '0', 'GUEST_FOLD_FORM': '1', 'GUEST_OXYGEN': '0'},
                 {'GUEST_OPLUS': '0', 'GUEST_AOSP_SYSUI': '0', 'GUEST_MIUI': '1', 'GUEST_FOLD_FORM': '0', 'GUEST_OXYGEN': '0'})
        with tempfile.TemporaryDirectory() as d:
            for kind in kinds:
                # No command of the server runs while the string is put together: nothing is on the PATH.
                env = {n: '1' if n.startswith('GUEST_') or n.endswith('_PID') else '/x/' + n.lower() for n in names}
                env.update(kind, PATH='/nonexistent')
                Path(d, 'gen.sh').write_text("printf '%s\\n' \"" + body + '"\n')
                made = subprocess.run(['/bin/sh', str(Path(d, 'gen.sh'))], env=env, capture_output=True, text=True, cwd=d, timeout=60)
                self.assertEqual((0, ''), (made.returncode, made.stderr), kind)
                self.assertIn("[UI Activator] guest display 0: ", made.stdout)
                self.assertIn('[UI Activator] stable display size: ', made.stdout)
                Path(d, 'activator.sh').write_text(made.stdout)
                r = subprocess.run(['/bin/sh', '-n', str(Path(d, 'activator.sh'))], capture_output=True, text=True, timeout=60)
                self.assertEqual((0, ''), (r.returncode, r.stderr), kind)


if __name__ == '__main__':
    unittest.main()
