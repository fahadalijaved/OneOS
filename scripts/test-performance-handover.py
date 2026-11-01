#!/usr/bin/env python3
"""Exercise performance vote ownership and thermal behavior without a device."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / 'switcher/assets/fold8_coloros.sh').read_text()
FUNCTIONS = TEXT[TEXT.index('# Samsung\'s userspace votes'):TEXT.index('case "$1" in')]

class PerformanceHandover(unittest.TestCase):
    def run_case(self, body):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            files = {
                'sys/devices/system/cpu/cpufreq_limit/cpufreq_max_limit': '1267200',
                'sys/kernel/gpu/gpu_max_clock': '160',
                'sys/kernel/gpu/gpu_tmu': '35000',
                'sys/class/kgsl/kgsl-3d0/gpu_available_frequencies': '1300000000 1050000000 826000000 646000000 160000000',
                'boot': 'test-boot',
            }
            for p, hw, freq in [('policy0',3628800,1228800),('policy6',4742400,1267200)]:
                files[f'sys/devices/system/cpu/cpufreq/{p}/cpuinfo_max_freq'] = str(hw)
                files[f'sys/devices/system/cpu/cpufreq/{p}/scaling_max_freq'] = str(freq)
            for name,value in files.items():
                p = base/name; p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value+'\n')
            (base/'stage/data').mkdir(parents=True)
            source = FUNCTIONS.replace('/proc/sys/kernel/random/boot_id',str(base/'boot')).replace('/sys/',str(base/'sys')+'/')
            script = f'STAGE={base}/stage\nBB=/bin/false\nset -eu\n' + source + '''
selected() { return 0; }
plain_tree() { [ ! -L "$1" ]; }
fail() { echo "$*" >&2; exit 3; }
''' + body
            result = subprocess.run(['sh','-c',script],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_snapshot_and_compare_restore(self):
        self.run_case('''
perf_snapshot live
C=$(dirname "$PSTATE")/../sys/devices/system/cpu/cpufreq_limit/cpufreq_max_limit
G=$(dirname "$PSTATE")/../sys/kernel/gpu/gpu_max_clock
perf_write "$C" cpu -1
perf_write "$G" gpu 1300
perf_restore
[ "$(cat "$C")" = 1267200 ] && [ "$(cat "$G")" = 160 ]
''')

    def test_external_writer_is_preserved_and_new_session_resets_ownership(self):
        self.run_case('''
perf_snapshot live
G=$(dirname "$PSTATE")/../sys/kernel/gpu/gpu_max_clock
perf_write "$G" gpu 1300
echo 826 > "$G"
perf_write "$G" gpu 1050
[ "$(cat "$G")" = 826 ] && [ -f "$PSTATE/gpu.external" ]
perf_restore
[ "$(cat "$G")" = 826 ]
perf_snapshot host
[ ! -f "$PSTATE/gpu.external" ]
''')

    def test_hot_guest_gets_no_new_headroom(self):
        self.run_case('''
perf_snapshot live
perf_guest() { echo 123; }
timeout() { echo 'Current temperatures from HAL:'; echo 'Temperature{mValue=48.0, mType=3, mName=SKIN, mStatus=0}'; echo 'Current cooling devices'; }
sleep() { touch "$PSTATE/stop"; }
perf_worker
[ ! -f "$PSTATE/released" ]
''')

    def test_cool_guest_releases_votes_and_restores_on_stop(self):
        self.run_case('''
perf_snapshot live
perf_guest() { echo 123; }
timeout() { echo 'Current temperatures from HAL:'; echo 'Temperature{mValue=35.0, mType=3, mName=SKIN, mStatus=0}'; echo 'Current cooling devices'; }
sleep() { touch "$PSTATE/stop"; }
perf_worker
[ -f "$PSTATE/released" ]
grep -q 'requested gpu=1300' "$STAGE/performance_handover.log"
perf_restore
G=$(dirname "$PSTATE")/../sys/kernel/gpu/gpu_max_clock
[ "$(cat "$G")" = 160 ]
''')

    def test_existing_host_restriction_is_preserved(self):
        self.run_case('''
perf_snapshot host
perf_guest() { echo 123; }
timeout() { echo 'Current temperatures from HAL:'; echo 'Temperature{mValue=35.0, mType=3, mName=SKIN, mStatus=0}'; echo 'Current cooling devices'; }
sleep() { touch "$PSTATE/stop"; }
perf_worker
[ ! -f "$PSTATE/released" ]
''')

    def test_missing_telemetry_after_release_selects_conservative_caps(self):
        self.run_case('''
perf_snapshot live
perf_guest() { echo 123; }
timeout() {
 if [ ! -f "$PSTATE/first-read" ]; then
  touch "$PSTATE/first-read"
  echo 'Current temperatures from HAL:'
  echo 'Temperature{mValue=35.0, mType=3, mName=SKIN, mStatus=0}'
  echo 'Current cooling devices'
 fi
}
sleep() {
 if [ -f "$PSTATE/slept" ]; then touch "$PSTATE/stop"; else touch "$PSTATE/slept"; fi
}
perf_worker
grep -q 'requested gpu=646' "$STAGE/performance_handover.log"
''')

    def test_idle_host_vote_is_released_when_power_saving_is_off(self):
        self.run_case('''
timeout() {
 if [ "$2" = settings ]; then echo 0; else
  echo 'Current temperatures from HAL:'
  echo 'Temperature{mValue=35.0, mType=3, mName=SKIN, mStatus=0}'
  echo 'Current cooling devices'
 fi
}
perf_snapshot host
perf_guest() { echo 123; }
sleep() { touch "$PSTATE/stop"; }
perf_worker
[ -f "$PSTATE/released" ]
grep -q 'requested gpu=1300' "$STAGE/performance_handover.log"
''')

    def test_power_saving_selection_prevents_release(self):
        self.run_case('''
timeout() {
 if [ "$2" = settings ]; then echo 1; else
  echo 'Current temperatures from HAL:'
  echo 'Temperature{mValue=35.0, mType=3, mName=SKIN, mStatus=0}'
  echo 'Current cooling devices'
 fi
}
perf_snapshot host
perf_guest() { echo 123; }
sleep() { touch "$PSTATE/stop"; }
perf_worker
[ ! -f "$PSTATE/released" ]
''')

if __name__ == '__main__':
    unittest.main()
