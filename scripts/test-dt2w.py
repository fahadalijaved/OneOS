#!/usr/bin/env python3
"""Run the shipped touch transitions against an inert sysfs fixture."""
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

SOURCE = (Path(__file__).resolve().parents[1] / 'switcher/assets/guest_start.sh').read_text()


def function(name):
    start = SOURCE.index(f'        {name}() {{', SOURCE.index('# Double tap to wake'))
    return SOURCE[start:SOURCE.index('\n        }', start) + len('\n        }')]


class TouchPower(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.touch = self.root / 'sec/tsp'
        (self.touch / 'input').mkdir(parents=True)
        (self.touch / 'enabled').write_text('2')
        (self.touch / 'input/enabled').write_text('1')
        self.marker = self.root / 'armed.tsp'
        self.marker.write_text('2')

    def run_shell(self, commands, protocol=2, fail=False):
        start = SOURCE.index('        tsp_off() {', SOURCE.index('# Double tap to wake'))
        funcs = SOURCE[start:SOURCE.index('        arm() {', start)] + function('wake_tsp')
        scan_start = SOURCE.index('            for t in $IDS; do', SOURCE.index('        while :; do\n            D=;'))
        scan_end = SOURCE.index('            if [ $FOLD = 1 ]', scan_start)
        funcs += '\nscan_panels() {\nCH=""; LC=""\n' + SOURCE[scan_start:scan_end] + '\n}\n'
        funcs = funcs.replace('/sys/class/sec/', str(self.root / 'sec') + '/')
        funcs = funcs.replace('/data/oneos_dt2w_armed.', str(self.root / 'armed.'))
        # Redirected echo emulates the selected driver's state readback.
        mock = '''
echo() {
    printf '%s\n' "$*" >> "$WRITE_LOG"
    if [ "$FAIL" = 1 ]; then printf 1; return 1; fi
    if [ "$FAIL" = 3 ] && [ "$1" = 2,1 ]; then
        attempts=0; [ ! -f "$ATTEMPTS" ] || read -r attempts < "$ATTEMPTS"
        attempts=$((attempts + 1)); printf '%s\n' "$attempts" > "$ATTEMPTS"
        if [ "$attempts" -le 2 ]; then printf 1; return 1; fi
    fi
    if [ "$POWER_tsp" = 2 ]; then
        case "$1" in 1,0) printf 1; printf 0 > "$INPUT";;
                      2,1) printf 2; printf 1 > "$INPUT"; [ "$FAIL" != 2 ] || printf 0 > "$INPUT";; *) return 1;; esac
    else
        case "$1" in 1,*) printf 0;; 2,*) printf 1;; esac
    fi
}
log() { :; }
disarm() { printf '%s\n' "$1" >> "$DISARM_LOG"; }
'''
        return subprocess.run(['sh', '-c', mock + funcs + '\n' + commands],
                              env=dict(os.environ, POWER_tsp=str(protocol), EON_tsp=str(protocol),
                                       FAIL=str(int(fail)), INPUT=str(self.touch / 'input/enabled'),
                                       WRITE_LOG=str(self.root / 'writes'),
                                       DISARM_LOG=str(self.root / 'disarms'),
                                       ATTEMPTS=str(self.root / 'attempts')),
                              capture_output=True, text=True)

    def writes(self):
        return (self.root / 'writes').read_text().splitlines()

    def detect_protocol(self, enabled, input_enabled, model='SM-S918B',
                        driver='/sys/bus/spi/drivers/stm_ts_spi'):
        (self.touch / 'enabled').write_text(str(enabled))
        (self.touch / 'input/enabled').write_text(str(input_enabled))
        start = SOURCE.index('            e0=$(cat $T/enabled', SOURCE.index('# Double tap to wake'))
        block = SOURCE[start:SOURCE.index('            # KEY_WAKEUP', start)]
        code = '''getprop() { printf '%s' "$MODEL"; }
readlink() { printf '%s' "$DRIVER"; }
log() { :; }
for t in tsp; do
''' + block + '\nprintf "%s" "$power"\ndone\n'
        return subprocess.run(['sh', '-c', code],
                              env=dict(os.environ, T=str(self.touch), I=str(self.touch / 'input'),
                                       MODEL=model, DRIVER=driver),
                              capture_output=True, text=True)

    def test_stm_protocol_detected_while_asleep_or_awake(self):
        for enabled, input_enabled in ((1, 0), (2, 1)):
            with self.subTest(enabled=enabled):
                result = self.detect_protocol(enabled, input_enabled)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual('2', result.stdout)

    def test_stm_lpm_start_restores_touch_with_enum_protocol(self):
        result = self.detect_protocol(1, 0)
        self.assertEqual('2', result.stdout)
        restored = self.run_shell('power_tsp tsp 2', protocol=int(result.stdout))
        self.assertEqual(0, restored.returncode, restored.stderr)
        self.assertEqual(['2,1'], self.writes())
        self.assertEqual('2', (self.touch / 'enabled').read_text())
        self.assertEqual('1', (self.touch / 'input/enabled').read_text())

    def test_unmeasured_stm_states_are_not_armed(self):
        for enabled, input_enabled, model in ((0, 0, 'SM-S918B'), (1, 1, 'SM-S918B'),
                                              (2, 0, 'SM-S918B')):
            with self.subTest(enabled=enabled, input_enabled=input_enabled, model=model):
                self.assertEqual('', self.detect_protocol(enabled, input_enabled, model=model).stdout)

    def test_boolean_driver_still_uses_boolean_protocol(self):
        for driver in ('/other/driver', '/sys/bus/spi/drivers/stm_ts_spi'):
            for enabled in (0, 1):
                with self.subTest(driver=driver, enabled=enabled):
                    result = self.detect_protocol(enabled, enabled, model='fold', driver=driver)
                    self.assertEqual('1', result.stdout)
        self.assertEqual('1', self.detect_protocol(2, 1, model='other', driver='/other/driver').stdout)

    def test_stm_enum_sleep_and_wake(self):
        result = self.run_shell('power_tsp tsp 1 && power_tsp tsp 2')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(['1,0', '2,1'], self.writes())
        self.assertEqual('2', (self.touch / 'enabled').read_text())
        self.assertEqual('1', (self.touch / 'input/enabled').read_text())

    def test_fold_protocol_retains_both_notifications(self):
        result = self.run_shell('power_tsp tsp 1 && power_tsp tsp 2', protocol=1)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(['1,0', '1,1', '2,0', '2,1'], self.writes())

    def test_failed_transition_is_reported(self):
        self.assertNotEqual(0, self.run_shell('power_tsp tsp 1', fail=True).returncode)

    def test_wake_removes_marker_after_confirmed_restore(self):
        result = self.run_shell('wake_tsp tsp test')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse(self.marker.exists())
        self.assertEqual(['2,1'], self.writes())

    def test_failed_restore_retains_marker_for_return(self):
        self.run_shell('wake_tsp tsp test', fail=True)
        self.assertTrue(self.marker.exists())
        self.assertEqual(['2,1', '2,1'], self.writes())

    def test_unarmed_touch_is_not_changed(self):
        self.marker.unlink()
        self.run_shell('wake_tsp tsp test')
        self.assertFalse((self.root / 'writes').exists())

    def test_disabled_input_retains_marker_even_with_power_on(self):
        self.run_shell('wake_tsp tsp test', fail=2)
        self.assertEqual('2', (self.touch / 'enabled').read_text())
        self.assertEqual('0', (self.touch / 'input/enabled').read_text())
        self.assertTrue(self.marker.exists())

    def test_wake_listener_clears_aod_while_input_command_is_still_blocked(self):
        start = SOURCE.index('            ( while read -r a k v; do', SOURCE.index('        arm() {'))
        end = SOURCE.index('              done < $P ) &', start)
        listener = SOURCE[start:end].replace('            ( while', '            while', 1)
        listener += '              done < "$EVENTS"\n'
        events = self.root / 'wake-events'
        events.write_text('event KEY_WAKEUP DOWN\n')
        aod, started, release = [self.root / name for name in ('aod', 'command-started', 'release')]
        aod.write_text('1\n')
        mock = '''
LIDF=0
log() { :; }
in_call() { return 1; }
setaod() { printf '%s\\n' "$1" > "$AOD"; }
timeout() { shift; "$@"; }
cmd() {
    printf On > "$PANEL"
    : > "$STARTED"
    while [ ! -e "$RELEASE" ]; do sleep 0.01; done
}
'''
        panel = self.root / 'panel'
        panel.write_text('Off')
        env = dict(os.environ, EVENTS=str(events), AOD=str(aod), STARTED=str(started),
                   RELEASE=str(release), PANEL=str(panel))
        process = subprocess.Popen(['sh', '-c', mock + listener], env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 3
            while not started.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(started.exists(), 'Wake input command never started')
            self.assertIsNone(process.poll(), 'Wake input command should still be blocked')
            self.assertEqual('On', panel.read_text())
            self.assertEqual('0', aod.read_text().strip(),
                             'A lit keypad must not retain the AOD touch-sleep override')
        finally:
            release.touch()
            stdout, stderr = process.communicate(timeout=5)
        self.assertEqual(0, process.returncode, stdout + stderr)

    def test_return_holds_reader_and_checks_full_restore(self):
        path = Path(__file__).resolve().parents[1] / 'switcher/assets/return_to_oneui.sh'
        source = path.read_text()
        start = source.index('for t in tsp tsp1 tsp2; do', source.index('# A touchscreen the guest'))
        block = source[start:source.index('rm -f /dev/oneos_dt2w_event', start)]
        block = block.replace('/sys/class/sec/', str(self.root / 'sec') + '/')
        block = block.replace('/dev/input/', str(self.root / 'dev') + '/')
        device = self.root / 'dev/event10'
        device.parent.mkdir()
        device.symlink_to('/dev/null')
        (self.touch / 'input/event10').symlink_to('/dev/null')
        data = self.root / 'stage/data'
        data.mkdir(parents=True)
        marker = data / 'oneos_dt2w_armed.tsp'
        for marker_protocol, success in ((2, True), (2, False), (1, True), (1, False)):
            with self.subTest(marker_protocol=marker_protocol, success=success):
                marker.write_text(str(marker_protocol))
                (self.touch / 'input/enabled').write_text('1' if success else '0')
                writes = self.root / 'return-writes'
                writes.unlink(missing_ok=True)
                env = dict(os.environ, S=str(self.root / 'stage'), WRITE_LOG=str(writes))
                # Leave the fixture state unchanged by the write, as an acknowledged/no-op device.
                mock = '''getprop() { printf SM-S918B; }
readlink() { printf /sys/bus/spi/drivers/stm_ts_spi; }
echo() {
    case "$1" in
        2,1) printf '%s\\n' "$1" >> "$WRITE_LOG"; printf 2;;
        2,0) printf '%s\\n' "$1" >> "$WRITE_LOG";;
    esac
}
'''
                result = subprocess.run(['sh', '-c', mock + block +
                                         '\n[ -e /proc/$$/fd/9 ] || exit 20\nexec 9<&-\nprintf "%s" "$ONEOS_RETURN_MODE"'],
                                        env=env, capture_output=True, text=True)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(['2,1'], writes.read_text().splitlines())
                self.assertEqual(not success, marker.exists())
                if not success:
                    self.assertIn('reboot', result.stdout)

    def test_return_preserves_stm_marker_when_power_node_disappears(self):
        source = (Path(__file__).resolve().parents[1] / 'switcher/assets/return_to_oneui.sh').read_text()
        start = source.index('for t in tsp tsp1 tsp2; do', source.index('# A touchscreen the guest'))
        block = source[start:source.index('rm -f /dev/oneos_dt2w_event', start)]
        block = block.replace('/sys/class/sec/', str(self.root / 'sec') + '/')
        (self.touch / 'enabled').unlink()
        data = self.root / 'stage/data'
        data.mkdir(parents=True)
        marker = data / 'oneos_dt2w_armed.tsp'
        mock = '''getprop() { printf SM-S918B; }
readlink() { printf /sys/bus/spi/drivers/stm_ts_spi; }
'''
        for protocol in (1, 2):
            with self.subTest(protocol=protocol):
                marker.write_text(str(protocol))
                result = subprocess.run(['sh', '-c', mock + block + '\nprintf "%s" "$ONEOS_RETURN_MODE"'],
                                        env=dict(os.environ, S=str(self.root / 'stage')),
                                        capture_output=True, text=True)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertIn('reboot', result.stdout)
                self.assertTrue(marker.exists())
                self.assertFalse((self.touch / 'enabled').exists())

    def test_s23_transient_restore_failure_keeps_reader_until_paced_retry_succeeds(self):
        (self.touch / 'enabled').write_text('1')
        (self.touch / 'input/enabled').write_text('0')
        result = self.run_shell("""
lit() { return 0; }
IDS=tsp; D=0; ON_tsp=0; L_tsp=1
scan_panels
[ "$CH:$WR_tsp" = " tsp:50" ] || exit 10
wake_tsp tsp test
[ -f "$DISARM_LOG" ] && exit 11
[ -f "$MARKER" ] || exit 12
for n in 1 2 3 4 5 6 7 8 9; do
    scan_panels
    [ -z "$CH" ] || exit 13
done
scan_panels
[ "$CH:$WR_tsp" = " tsp:40" ] || exit 14
wake_tsp tsp retry
[ "$WR_tsp" = 0 ] || exit 15
""".replace('$MARKER', str(self.marker)), fail=3)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(['2,1'] * 3, self.writes())
        self.assertEqual(['tsp'], (self.root / 'disarms').read_text().splitlines())
        self.assertFalse(self.marker.exists())
        self.assertEqual('1', (self.touch / 'input/enabled').read_text())

    def test_s23_persistent_restore_failure_has_finite_paced_retries_and_keeps_reader(self):
        result = self.run_shell("""
lit() { return 0; }
IDS=tsp; D=0; ON_tsp=0; L_tsp=1
scan_panels
wake_tsp tsp test
n=0
while [ "$n" -lt 60 ]; do
    scan_panels
    [ -z "$CH" ] || wake_tsp tsp retry
    n=$((n + 1))
done
[ "$WR_tsp" = 0 ] || exit 16
""", fail=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(['2,1'] * 12, self.writes())
        self.assertFalse((self.root / 'disarms').exists())
        self.assertTrue(self.marker.exists())

    def test_display_paths_are_resolved_by_device_name(self):
        dpms = self.root / 'dpms'
        brightness = self.root / 'brightness'
        dpms.write_text('Off\n')
        brightness.write_text('0\n')
        code = function('lit') + '\nlit tsp'
        env = dict(os.environ, C_tsp=str(dpms), B_tsp=str(brightness),
                   FOLD='0', VIVO_IMG='0')
        self.assertEqual(1, subprocess.run(['sh', '-c', code], env=env).returncode)
        dpms.write_text('On\n')
        self.assertEqual(0, subprocess.run(['sh', '-c', code], env=env).returncode)

    def test_reader_open_failure_does_not_terminate_return_shell(self):
        source = (Path(__file__).resolve().parents[1] / 'switcher/assets/return_to_oneui.sh').read_text()
        line = next(line.strip() for line in source.splitlines() if 'exec 9<&0' in line)
        # Simulate the device disappearing after the character-device check.
        line = line.replace('[ ! -c "$ev" ] || ', '')
        code = line + '\nprintf fallback\nfi\nprintf survived\n'
        result = subprocess.run(['sh', '-c', code], env=dict(os.environ, ev=str(self.root / 'gone')),
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode)
        self.assertEqual('fallbacksurvived', result.stdout)


if __name__ == '__main__':
    unittest.main()
