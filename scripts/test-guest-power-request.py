#!/usr/bin/env python3
"""What the watcher writes down when the guest's framework asks for a shutdown or a reboot (oneos_switch.sh).

The branch is taken out of the watcher's quoted block, unquoted the way the outer shell does it, and
run with stand-ins for logcat, pidof and the guest's dumpsys (through $BB nsenter).
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parent.parent
SOURCE = (ROOT / 'switcher/assets/oneos_switch.sh').read_text()
START = '            if [ -n \\"\\$req\\" ]; then\n                echo \\"\\$(date) guest requested'
END = '                exec /system/bin/sh $STAGE/return_to_oneui.sh\n'
RAW = START + SOURCE.split(START, 1)[1].split(END, 1)[0]

SYSTEM_LOG = '''11-11 02:17:40.100  1000  2222  2301 I ActivityManager: Start proc 9999:org.example.app/u0a123 for service
11-11 02:17:52.900  1000  2222  2400 W OneOS   : guest ShutdownThread.shutdown blocked
11-11 02:17:52.901  1000  2222  2400 I SomeVendorTag: high temperature, shutdown now
'''
THERMAL = '''IsStatusOverride: false
Thermal Status: 3
Cached temperatures:
\tTemperature{mValue=63.1, mType=0, mName=AP, mStatus=0}
\tTemperature{mValue=45.4, mType=3, mName=SKIN, mStatus=3}
HAL Ready: true
Current temperatures from HAL:
\tTemperature{mValue=65.7, mType=0, mName=AP, mStatus=0}
\tTemperature{mValue=46.2, mType=3, mName=SKIN, mStatus=3}
Temperature static thresholds from HAL:
\tTemperatureThreshold{mType=3, mName=SKIN, mHotThrottlingThresholds=[38.0, 40.0, 42.0, 45.0, 47.0, 60.0, 90.0]}
'''
BATTERY = '''Current Battery Service state:
  AC powered: false
  USB powered: true
  Max charging current: 0
  Charge counter: 1984000
  status: 3
  health: 2
  present: true
  level: 41
  scale: 100
  voltage: 3792
  temperature: 403
  technology: Li-ion
'''
LOGCAT = '''#!/bin/sh
echo "$*" >> "$R/logcat_args"
case " $* " in *" -b system "*) cat "$R/system_log" ;; *) i=0; while [ $i -lt 50 ]; do echo "11-11 02:17:53.000 CameraSpam: frame $i"; i=$((i + 1)); done ;; esac
'''
BB = '''#!/bin/sh
echo "$*" >> "$R/bb_args"
[ -z "$SLOW" ] || exec sleep 30
case "$*" in
    "nsenter -t 4321 -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys thermalservice") cat "$R/thermal" ;;
    "nsenter -t 4321 -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys battery") cat "$R/battery" ;;
    *) echo "unexpected: $*" ;;
esac
'''


def unquote(block, stage, bb):
    """The outer shell's double quotes: its own $STAGE and $BB, then \\$ \\" \\\\ and \\`."""
    block = re.sub(r'(?<!\\)\$STAGE\b', stage, block)
    block = re.sub(r'(?<!\\)\$BB\b', bb, block)
    left = re.findall(r'(?<!\\)\$[A-Za-z_{(]', block)
    assert not left, left
    return re.sub(r'\\([$"\\`])', r'\1', block)


class PowerRequest(unittest.TestCase):
    def run_branch(self, req='shutdown', pids='4321 99', thermal=THERMAL, battery=BATTERY, slow=''):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            (r / 'bin').mkdir()
            (r / 'bin/logcat').write_text(LOGCAT)
            (r / 'bin/pidof').write_text('#!/bin/sh\n[ "$1" = surfaceflinger ] && [ -n "$PIDS" ] && echo "$PIDS"\n')
            (r / 'bb').write_text(BB)
            for f in ('bin/logcat', 'bin/pidof', 'bb'):
                os.chmod(r / f, 0o755)
            (r / 'system_log').write_text(SYSTEM_LOG)
            (r / 'thermal').write_text(thermal)
            (r / 'battery').write_text(battery)
            code = f"req='{req}'; t=590\n" + unquote(RAW, str(r / 'stage'), str(r / 'bb')) + '                echo RETURN\n            fi\n'
            env = dict(os.environ, R=str(r), PIDS=pids, SLOW=slow, PATH=f'{r}/bin:' + os.environ['PATH'])
            began = time.time()
            out = subprocess.run(['/bin/sh', '-c', code], env=env, capture_output=True, text=True, timeout=60)
            read = lambda n: (r / n).read_text().splitlines() if (r / n).exists() else []
            return {'out': out.stdout.splitlines(), 'err': out.stderr, 'logcat': read('logcat_args'), 'bb': read('bb_args'),
                    'took': time.time() - began}

    def test_a_shutdown_asked_by_the_guest(self):
        got = self.run_branch()
        self.assertEqual('', got['err'])
        self.assertTrue(got['out'][0].endswith("guest requested 'shutdown' after 590s, returning to One UI"), got['out'][0])
        self.assertEqual('RETURN', got['out'][-1])
        body = got['out'][1:-1]
        # The system buffer is read on its own: a busy camera cannot push the request out of the lines read.
        self.assertTrue(any(' -b system ' in f' {a} ' for a in got['logcat']), got['logcat'])
        self.assertIn('11-11 02:17:52.900  1000  2222  2400 W OneOS   : guest ShutdownThread.shutdown blocked', body)
        self.assertIn('11-11 02:17:52.901  1000  2222  2400 I SomeVendorTag: high temperature, shutdown now', body)
        self.assertFalse(any('org.example.app' in l or 'CameraSpam' in l for l in body), body)
        self.assertIn('guest thermal service: Thermal Status: 3 Temperature{mValue=45.4, mType=3, mName=SKIN, mStatus=3} '
                      'Temperature{mValue=46.2, mType=3, mName=SKIN, mStatus=3}', [l.rstrip() for l in body])
        self.assertIn('guest battery service: USB powered: true status: 3 health: 2 level: 41 voltage: 3792 temperature: 403',
                      [l.rstrip() for l in body])
        self.assertEqual(2, len(got['bb']))

    def test_a_reboot_asked_by_the_guest_is_written_down_the_same_way(self):
        got = self.run_branch(req='reboot,userrequested')
        self.assertEqual(1, sum(l.startswith('guest thermal service: Thermal Status: 3') for l in got['out']), got['out'])
        self.assertEqual('RETURN', got['out'][-1])

    def test_the_users_own_return_asks_the_guest_nothing(self):
        for req in ('app:tile', 'app:app', 'keys:volume-up+down', 'ksud:soft-reboot'):
            with self.subTest(req):
                got = self.run_branch(req=req)
                self.assertEqual([], got['bb'])
                self.assertFalse(any(l.startswith('guest ') for l in got['out'][1:]), got['out'])
                self.assertEqual('RETURN', got['out'][-1])

    def test_no_guest_composer_no_questions(self):
        got = self.run_branch(pids='')
        self.assertEqual(([], 'RETURN', ''), (got['bb'], got['out'][-1], got['err']))

    def test_services_that_do_not_answer(self):
        got = self.run_branch(thermal="Can't find service: thermalservice\n", battery='')
        lines = [l.rstrip() for l in got['out']]
        self.assertIn('guest thermal service: no answer', lines)
        self.assertIn('guest battery service: no answer', lines)
        self.assertEqual('RETURN', lines[-1])

    def test_a_hanging_guest_does_not_hold_the_return(self):
        got = self.run_branch(slow='1')
        self.assertEqual('RETURN', got['out'][-1])
        self.assertLess(got['took'], 20)
        self.assertIn('guest thermal service: no answer', [l.rstrip() for l in got['out']])


if __name__ == '__main__':
    unittest.main()
