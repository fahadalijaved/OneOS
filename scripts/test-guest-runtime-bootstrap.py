#!/usr/bin/env python3
"""The guest root's module cleanup can never hold a switch (0.4.92).

Galaxy S22 Ultra, 0.4.91, OxygenOS 16, 2026-11-11: three switches in a row stood behind the
"shutting down" splash for good, right after "Guest runtime: ... explicit guest injection enabled".
guest_runtime.sh's uninstall stage starts a bootstrap su in the background and ends it from its
EXIT trap, which with no module to remove runs microseconds later. The guest's shell (mksh) catches
SIGTERM itself: one that reaches the forked child before it has become su is swallowed, su never
gets it, and the trap's wait never returns. Nothing bounded the step.

Here: the stage as it is in the script, run with SIGTERM ignored from the start (a kill by SIGTERM
then never works, as on the phone when it is lost), must still end at once; and the generated
guest_modules.sh must end a cleanup that does not return, and the bootstrap it left.
"""
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / 'switcher/assets/guest_runtime.sh').read_text()
PREPARE = (ROOT / 'switcher/assets/guest_prepare.sh').read_text()


def stage(name, following):
    """The body of one stage of guest_runtime.sh's case, without its closing ';;'."""
    body = RUNTIME.split('\n%s)\n' % name, 1)[1].split('\n%s)\n' % following, 1)[0]
    assert body.rstrip().endswith(';;'), name
    return body.rstrip()[:-2]


def modules_script():
    return PREPARE.split("<<'GUESTMODULES'\n", 1)[1].split('\nGUESTMODULES\n', 1)[0]


def gone(pid):
    """True once the process has ended (a zombie waiting for its parent counts as ended)."""
    for _ in range(50):
        try:
            state = Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()[0]
        except (FileNotFoundError, ProcessLookupError):
            return True
        if state == 'Z':
            return True
        time.sleep(0.1)
    return False


def ignore_sigterm():
    signal.signal(signal.SIGTERM, signal.SIG_IGN)


class BootstrapTest(unittest.TestCase):
    def test_every_waited_bootstrap_ends_by_sigkill(self):
        traps = [l for l in RUNTIME.split('\n') if 'wait "$bootstrap"' in l]
        self.assertEqual(len(traps), 2, traps)
        for l in traps:
            self.assertIn('kill -KILL "$bootstrap"', l)
        self.assertNotIn('kill "$bootstrap"', RUNTIME)

    def test_uninstall_stage_ends_although_sigterm_never_arrives(self):
        with tempfile.TemporaryDirectory() as d:
            adb = Path(d) / 'adb'
            (adb / 'oneos/bin').mkdir(parents=True)
            (adb / 'oneos/run').mkdir()
            (adb / 'modules/some_module').mkdir(parents=True)
            su = adb / 'oneos/bin/su'
            # A daemon: it never ends by itself.
            su.write_text('#!/bin/sh\necho $$ > "%s/su.pid"\nexec sleep 300\n' % d)
            su.chmod(0o755)
            body = stage('uninstall', 'install')
            self.assertEqual(body.count('A=/data/adb\n'), 1)
            # The guest's PATH has no meaning on the build server.
            self.assertEqual(body.count(' PATH=/system/bin:/system/xbin:/data/adb/ksu/bin\n'), 1)
            script = 'set -eu\n' + body.replace('A=/data/adb\n', 'A="%s"\n' % adb).replace(
                ' PATH=/system/bin:/system/xbin:/data/adb/ksu/bin\n', '\n')
            started = time.time()
            try:
                run = subprocess.run(['sh', '-c', script], preexec_fn=ignore_sigterm, timeout=30,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            except subprocess.TimeoutExpired:
                pid = Path(d, 'su.pid')
                if pid.exists():
                    os.kill(int(pid.read_text()), signal.SIGKILL)
                self.fail('the uninstall stage waits for a bootstrap that SIGTERM did not end')
            self.assertEqual(run.returncode, 0, run.stdout)
            self.assertLess(time.time() - started, 10)
            self.assertFalse((adb / 'oneos/run/bootstrap.pid').exists())
            pid = Path(d, 'su.pid')
            if pid.exists():
                self.assertTrue(gone(int(pid.read_text())), 'the bootstrap is still running')


class BoundedCleanupTest(unittest.TestCase):
    def fixture(self, d, chroot):
        """A stage with guest root on, one module without files, and a busybox whose chroot is `chroot`."""
        stage_dir = Path(d) / 'stage'
        k = stage_dir / 'data/oneos_root/adb'
        (k / 'modules/some_module').mkdir(parents=True)
        (k / 'oneos/run').mkdir(parents=True)
        (k / 'oneos/bin').mkdir()
        (stage_dir / 'data/oneos_root/enabled').touch()
        (stage_dir / 'tmp').mkdir()
        (stage_dir / 'rootfs/data').mkdir(parents=True)
        shutil.copy('/bin/sleep', k / 'oneos/bin/su')
        bb = Path(d) / 'busybox'
        # timeout: the script's own signal, its 150 s shortened to 2. mount/umount: nothing to do here.
        bb.write_text('''#!/bin/sh
K="%s"
case "$1" in
    timeout) [ "$2" = -s ] && [ "$3" = KILL ] && [ "$4" = 150 ] || exit 99; shift 4; exec timeout -s KILL 2 "$@" ;;
    chroot) shift 2
%s ;;
    mount|umount) exit 0 ;;
    *) exec "$@" ;;
esac
''' % (k, chroot))
        bb.chmod(0o755)
        return stage_dir, k, bb

    def run_modules(self, stage_dir, bb):
        started = time.time()
        run = subprocess.run(['sh', '-c', modules_script()], timeout=60, text=True,
                             env={**os.environ, 'ONEOS_TEST_STAGE': str(stage_dir), 'BB': str(bb)},
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return run, time.time() - started

    def test_cleanup_runs_under_a_sigkill_bound(self):
        line = [l for l in modules_script().split('\n') if '/data/oneos_runtime.sh uninstall' in l]
        self.assertEqual(len(line), 1)
        self.assertIn('"$BB" timeout -s KILL 150 "$BB" chroot "$R" /system/bin/sh /data/oneos_runtime.sh uninstall', line[0])

    def test_a_cleanup_that_ends_goes_on_to_the_modules(self):
        with tempfile.TemporaryDirectory() as d:
            stage_dir, k, bb = self.fixture(d, '        [ "$*" = "/system/bin/sh /data/oneos_runtime.sh uninstall" ] || exit 98; exit 0')
            run, took = self.run_modules(stage_dir, bb)
            self.assertEqual(run.returncode, 0, run.stdout)
            self.assertIn('Modules: some_module: nothing to mount', run.stdout)
            self.assertIn('Modules: 1 enabled for this system', run.stdout)
            self.assertNotIn('did not end', run.stdout)

    def test_a_cleanup_that_never_ends_is_stopped_with_its_bootstrap(self):
        with tempfile.TemporaryDirectory() as d:
            stage_dir, k, bb = self.fixture(d, '''        "$K/oneos/bin/su" 300 &
        echo $! > "$K/oneos/run/bootstrap.pid"
        exec sleep 300''')
            run, took = self.run_modules(stage_dir, bb)
            self.assertEqual(run.returncode, 1, run.stdout)
            self.assertLess(took, 20)
            self.assertIn("Modules: the guest's module cleanup did not end within 150 s and was stopped", run.stdout)
            self.assertIn("Modules: the guest's module cleanup failed (exit 137;", run.stdout)
            self.assertNotIn('enabled for this system', run.stdout)
            self.assertFalse((k / 'oneos/run/bootstrap.pid').exists())
            left = subprocess.run(['pgrep', '-f', str(k / 'oneos/bin/su')], stdout=subprocess.PIPE, text=True).stdout.split()
            for p in left:
                self.assertTrue(gone(int(p)), 'the bootstrap su is still running')

    def test_a_recorded_pid_that_is_not_the_bootstrap_is_left_alone(self):
        with tempfile.TemporaryDirectory() as d:
            other = subprocess.Popen(['sleep', '300'])
            try:
                stage_dir, k, bb = self.fixture(d, '''        echo %d > "$K/oneos/run/bootstrap.pid"
        exec sleep 300''' % other.pid)
                run, took = self.run_modules(stage_dir, bb)
                self.assertEqual(run.returncode, 1, run.stdout)
                self.assertIn('did not end within 150 s', run.stdout)
                self.assertIsNone(other.poll(), 'a process that is not the bootstrap su was killed')
            finally:
                other.kill()
                other.wait()


if __name__ == '__main__':
    unittest.main()
