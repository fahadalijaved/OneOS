#!/usr/bin/env python3
"""The double-tap keeper's touchscreen writes (guest_start.sh, return_to_oneui.sh) against stand-in drivers.

The stand-in is a shell function named echo: a write of "N,M" to the enabled node answers as one of
the Samsung drivers does (the state it leaves is what the node reads next), everything else is the
real echo. "old" is the kernel 6.1 generation, where 1,1 and 2,0 end in "write error: Invalid
argument"; "dead" refuses every write.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
START_SH = (ROOT / 'switcher/assets/guest_start.sh').read_text()
RETURN_SH = (ROOT / 'switcher/assets/return_to_oneui.sh').read_text()


def between(text, start, end):
    return start + text.split(start, 1)[1].split(end, 1)[0]


GATE = between(START_SH, '        for t in tsp tsp1 tsp2; do\n            T=/sys/class/sec/$t\n',
               '        [ -n "$IDS" ] || { log "no touchscreen to keep')
FUNCS = between(START_SH, '        tsp_off() {', '        while :; do\n            D=; read -r D < $AF')
RETURN = between(RETURN_SH, 'for t in tsp tsp1 tsp2; do\n    f=$S/data/oneos_dt2w_armed.$t\n',
                 'rm -f /dev/oneos_dt2w_event*')


def local(block):
    # The device is a plain file here (no device nodes without root).
    return (block.replace('-c /dev/input/$ev', '-e /dev/input/$ev').replace('/sys/class/', '$R/sys/class/')
            .replace('/dev/input/', '$R/dev/input/').replace('/data/oneos_dt2w', '$R/data/oneos_dt2w'))


PRELUDE = r'''
log() { command echo "$*"; }
BB=; LIDF=0
in_call() { return 1; }
setaod() { :; }
ST=$START
echo() {
    case "$1" in
        [12],[01])
            command echo "$1" >> $R/writes
            if [ "$1" = 1,0 ]; then
                h=free; ls -l /proc/$g/fd 2>/dev/null | grep -q "$R/dev/input/" && h=held
                command echo $h >> $R/held
            fi
            case "$DRV:$1" in
                old:1,1|old:2,0|dead:*) printf %s "$ST"; command echo "sh: write error: Invalid argument" >&2; return 1 ;;
            esac
            case "$1" in 1,0) ST=$OFFV ;; 2,1) ST=$ONV ;; esac
            printf %s "$ST" ;;
        *) command echo "$@" ;;
    esac
}
'''

GETEVENT = '''#!/bin/sh
# getevent -l <device>: holds the device open; one double tap when the test asks for it.
[ -z "$SLOW" ] || sleep $SLOW
exec 3< "$2"
while [ ! -e "$R/tap" ]; do sleep 0.05; done
echo "EV_KEY       KEY_WAKEUP           DOWN"
exec sleep 20
'''


class Keeper(unittest.TestCase):
    def run_keeper(self, scenario, drv='new', start='1', on='1', off='0', slow='', gate=True):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            tsp = r / 'sys/class/sec/tsp'
            (tsp / 'input/event3/x').mkdir(parents=True)
            (tsp / 'input/capabilities').mkdir()
            (tsp / 'input/capabilities/key').write_text('8000 0 0\n')
            (tsp / 'input/name').write_text('sec_touchscreen\n')
            (tsp / 'enabled').write_text(start)
            (r / 'sys/class/backlight/panel0-backlight').mkdir(parents=True)
            (r / 'sys/class/backlight/panel0-backlight/brightness').write_text('100\n')
            (r / 'sys/class/drm/card0-DSI-1').mkdir(parents=True)
            (r / 'sys/class/drm/card0-DSI-1/dpms').write_text('On\n')
            (r / 'dev/input').mkdir(parents=True)
            (r / 'dev/input/event3').write_text('')
            (r / 'data').mkdir()
            (r / 'stage/data').mkdir(parents=True)
            (r / 'bin').mkdir()
            (r / 'bin/getevent').write_text(GETEVENT)
            (r / 'bin/cmd').write_text('#!/bin/sh\necho "$*" >> "$R/woke"\n')
            for f in ('getevent', 'cmd'):
                os.chmod(r / 'bin' / f, 0o755)
            code = PRELUDE + (local(GATE) if gate else '') + local(FUNCS) + scenario
            shell = shutil.which('busybox')
            argv = [shell, 'sh', '-c', code] if shell else ['/bin/sh', '-c', code]
            env = dict(os.environ, R=str(r), DRV=drv, START=start, ONV=on, OFFV=off, SLOW=slow,
                       PATH=f'{r}/bin:' + os.environ['PATH'])
            out = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=60)
            read = lambda n: (r / n).read_text().split() if (r / n).exists() else []
            return {'out': out.stdout.splitlines(), 'err': out.stderr.strip(), 'writes': read('writes'),
                    'held': read('held'), 'woke': read('woke'), 'marker': (r / 'data/oneos_dt2w_armed.tsp').exists(),
                    'enabled': (tsp / 'enabled').read_text()}

    SLEEP_AND_WAKE = '''
command echo "IDS=$IDS EON=$EON_tsp"
arm tsp "panel off"
[ -f $R/data/oneos_dt2w_armed.tsp ] && command echo armed
wake_tsp tsp "panel on"
arm tsp "panel off"
wake_tsp tsp "panel on"
command echo "NO=$NO_tsp"
'''

    def assert_two_nights(self, got, asleep, awake):
        dev = [l for l in got['out'] if 'event3' in l]
        self.assertEqual(1, len(dev), got['out'])
        self.assertEqual([f'IDS= tsp EON={awake}', f'tsp: panel off: low-power mode (enabled={asleep})', 'armed',
                          f'tsp: panel on: enabled={awake}', f'tsp: panel off: low-power mode (enabled={asleep})',
                          f'tsp: panel on: enabled={awake}', 'NO='], [l for l in got['out'] if l not in dev])
        self.assertEqual(['1,0', '1,1', '2,0', '2,1'] * 2, got['writes'])
        self.assertEqual('', got['err'])
        self.assertFalse(got['marker'])
        self.assertEqual(awake, got['enabled'])

    def test_newer_driver_sleeps_and_wakes(self):
        self.assert_two_nights(self.run_keeper(self.SLEEP_AND_WAKE), '0', '1')

    def test_an_error_on_the_writes_that_do_nothing_is_not_a_refusal(self):
        # S24 Exynos, S23 FE, A25, A34, A35: the session used to end at "refused 1,0/1,1" here.
        self.assert_two_nights(self.run_keeper(self.SLEEP_AND_WAKE, drv='old'), '0', '1')

    def test_a_driver_that_shows_its_power_state_is_kept(self):
        # S22 Ultra, S23 series: 2 on, 1 low-power mode; no second try at the wake.
        self.assert_two_nights(self.run_keeper(self.SLEEP_AND_WAKE, drv='old', start='2', on='2', off='1'), '1', '2')

    def test_a_refused_first_write_gives_double_tap_up_and_leaves_the_ic_on(self):
        got = self.run_keeper('arm tsp "panel off"\narm tsp "panel off"\ncommand echo "NO=$NO_tsp GP=$GP_tsp"\n', drv='dead')
        self.assertEqual(1, sum('refused 1,0: back on, double tap left to the guest' in l for l in got['out']), got['out'])
        self.assertEqual('NO=1 GP=', got['out'][-1])
        # One try, the way back (2,0 2,1), and nothing at the second sleep.
        self.assertEqual(['1,0', '2,0', '2,1'], got['writes'])
        self.assertEqual(('1', False), (got['enabled'], got['marker']))

    def test_other_readings_are_left_to_the_guest(self):
        for start in ('3', '', 'on'):
            with self.subTest(start):
                got = self.run_keeper('command echo "IDS=$IDS"\n', start=start)
                self.assertEqual('IDS=', got['out'][-1])
                self.assertIn('not a known protocol: double tap left to the guest', got['out'][0])

    def test_an_ic_that_was_off_at_the_start_learns_what_on_reads(self):
        got = self.run_keeper('command echo "EON=$EON_tsp"\narm tsp "panel off"\nwake_tsp tsp "panel on"\ncommand echo "EON=$EON_tsp"\n',
                              start='0', on='2', off='1')
        self.assertEqual(['EON=1', 'tsp: panel off: low-power mode (enabled=1)', 'tsp: panel on: enabled=2', 'EON=2'], got['out'][1:])
        self.assertEqual(['1,0', '1,1', '2,0', '2,1'], got['writes'])

    def test_the_first_write_waits_until_the_touchscreen_is_held_open(self):
        got = self.run_keeper('arm tsp "panel off"\nwake_tsp tsp "panel on"\n', slow='0.4')
        self.assertEqual(['held'], got['held'])
        self.assertFalse(any('has not opened' in l for l in got['out']), got['out'])

    def test_a_double_tap_wakes_the_guest(self):
        got = self.run_keeper('arm tsp "panel off"\n: > $R/tap\ni=0; while [ ! -e $R/woke ] && [ $i -lt 100 ]; do sleep 0.05; i=$((i + 1)); done\n'
                              'wake_tsp tsp "panel on"\n')
        self.assertIn('tsp: double tap: waking the guest', got['out'])
        self.assertEqual(['input', 'keyevent', 'KEYCODE_WAKEUP'], got['woke'])

    def test_the_return_switches_a_sleeping_ic_on_without_an_error(self):
        code = ': > $S/data/oneos_dt2w_armed.tsp\n' + RETURN.replace('/sys/class/', '$R/sys/class/')
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            (r / 'sys/class/sec/tsp').mkdir(parents=True)
            (r / 'sys/class/sec/tsp/enabled').write_text('0')
            (r / 'stage/data').mkdir(parents=True)
            env = dict(os.environ, R=str(r), S=str(r / 'stage'), DRV='old', START='0', ONV='1', OFFV='0')
            out = subprocess.run(['/bin/sh', '-c', PRELUDE + code], env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual("Touchscreen tsp: back from the guest's double-tap low-power mode (enabled=1)", out.stdout.strip())
            self.assertEqual('', out.stderr.strip())
            self.assertEqual(['2,0', '2,1'], (r / 'writes').read_text().split())
            self.assertFalse((r / 'stage/data/oneos_dt2w_armed.tsp').exists())


if __name__ == '__main__':
    unittest.main()
