#!/usr/bin/env python3
"""The launch's answer waits for the started switch's own verdict (oneos_root.sh, do_launch).

The root script starts oneos_switch.sh detached and used to answer "@@OK launch"
at once. The switch then checks once more before it changes anything and can
still refuse, with its reason only in takeover_app.log: on a Galaxy S23 whose
property space was nearly full (a report on 0.4.95) the app's screen stayed on
"Shutting down One UI" for good, twice. Now the launch reads that verdict from
the log and passes a refusal on. These tests run the real function and the real
end of do_launch from the script against made-up logs.

Nothing of a switch is started here: the tests take only the lines after the
detached start, and the made-up log is the only thing they read.
"""
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / 'app-android/app/src/full/assets/root/oneos_root.sh').read_text()
SWITCH = (ROOT / 'switcher/assets/oneos_switch.sh').read_text()

FN_FIRST = 'switch_verdict() {\n'
FN_LAST = '\n}\n\ndo_launch() {\n'
END_FIRST = '    step "switch started"\n'
END_LAST = '    say "@@OK launch $sid"\n}\n'

SID = '7ce4d4f94b51cda5'
OLD = '3f1327ba1f690014'
REASON = ("One UI's property space is nearly full (4 KB left in u:object_r:system_prop:s0): the sessions since the "
          "phone last restarted used it up. Restart the phone, then switch again")


def header(sid):
    return ('=== OneOS app launch %s session 2026-11-12 07:46:30 epoch 1794449790 profile s-8550 image '
            'coloros17-findx9u-in set x9u-in-sultra hide-gms 0 sec-ims 1 edm-stub 1 ===\n' % sid)


def refusal(reason=REASON):
    return 'PREFLIGHT REFUSED: %s\nNothing on the phone was changed; One UI keeps running.\n' % reason


PASSED = 'Preflight passed (ONEOS_APP=1, profile s-8550, busybox /data/adb/ksu/bin/busybox, resetprop /data/adb/ksu/bin/resetprop, mount namespace mnt:[4026532515])\n'


def function_text():
    assert SCRIPT.count(FN_FIRST) == 1 and SCRIPT.count(FN_LAST) == 1, 'switch_verdict is not where the test expects it'
    return FN_FIRST + SCRIPT.split(FN_FIRST, 1)[1].split(FN_LAST, 1)[0] + '\n}\n'


def launch_end(seconds):
    """The lines of do_launch after the detached start, with the wait shortened to `seconds`."""
    assert SCRIPT.count(END_FIRST) == 1 and SCRIPT.count(END_LAST) == 1, 'the end of do_launch is not where the test expects it'
    body = END_FIRST + SCRIPT.split(END_FIRST, 1)[1].split(END_LAST, 1)[0] + 'say "@@OK launch $sid"\n'
    wait = 'switch_verdict "$sid" "$STAGE/takeover_app.log" 90'
    assert body.count(wait) == 1, body
    assert 'nsenter' not in body and 'oneos_switch.sh' not in body, 'the test must not hold the line that starts the switch'
    return body.replace(wait, 'switch_verdict "$sid" "$STAGE/takeover_app.log" %d' % seconds)


HELPERS = r'''
say() { printf '%s\n' "$*"; }
refuse() { say "@@REFUSED $*"; exit 2; }
step() { say "@@STEP $*"; }
'''


class Base(unittest.TestCase):
    # TEST_SH='busybox sh' runs the same tests in busybox's shell, with busybox's own awk and sleep.
    shell = os.environ.get('TEST_SH', 'sh').split()

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='verdict-test-')
        self.log = os.path.join(self.dir, 'takeover_app.log')
        self.path = os.environ.get('PATH', '/usr/bin:/bin')
        if os.path.basename(self.shell[0]) == 'busybox':
            applets = os.path.join(self.dir, 'applets')
            os.mkdir(applets)
            for a in ('awk', 'sleep'):
                os.symlink(shutil.which('busybox'), os.path.join(applets, a))
            self.path = applets + ':' + self.path

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, text):
        Path(self.log).write_text(text)

    def run_sh(self, text, timeout=30):
        env = {'PATH': self.path, 'STAGE': self.dir}
        t = time.time()
        r = subprocess.run(self.shell + ['-c', text], capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode, r.stdout, r.stderr, time.time() - t

    def verdict(self, sid=SID, seconds=1, log=None):
        return self.run_sh(function_text() + 'switch_verdict "%s" "%s" %d\n' % (sid, log or self.log, seconds))

    def end(self, seconds=1, sid=SID):
        return self.run_sh(HELPERS + function_text() + 'sid=%s\n' % sid + launch_end(seconds))


class VerdictTest(Base):
    def test_a_refusal_is_read_with_its_reason(self):
        self.write(header(SID) + refusal())
        rc, out, err, took = self.verdict()
        self.assertEqual((rc, out, err), (0, 'refused ' + REASON + '\n', ''))
        self.assertLess(took, 0.45, 'a verdict that is already there must not wait')

    def test_a_passed_check_is_read(self):
        self.write(header(SID) + "WARNING: One UI's property space is getting full (41 KB left in u:object_r:system_prop:s0); "
                   'some of the other system\'s settings may not load. Restart the phone before the next session\n' + PASSED)
        rc, out, err, took = self.verdict()
        self.assertEqual((rc, out, err), (0, 'passed\n', ''))
        self.assertLess(took, 0.45)

    def test_an_earlier_launchs_refusal_is_not_this_launchs(self):
        # The report's own log: the launch before was refused too. Only what follows this launch's line counts.
        self.write(header(OLD) + refusal() + header(SID))
        rc, out, err, took = self.verdict(seconds=1)
        self.assertEqual((rc, out, err), (1, '', ''))
        self.assertGreater(took, 0.9, 'no verdict yet: it has to wait its time')
        self.write(header(OLD) + refusal() + header(SID) + PASSED)
        self.assertEqual(self.verdict()[:2], (0, 'passed\n'))
        self.write(header(OLD) + PASSED + 'preflight: switch start 15:35:31\n' + header(SID) + refusal('battery too warm'))
        self.assertEqual(self.verdict()[:2], (0, 'refused battery too warm\n'))

    def test_another_session_id_that_begins_the_same_is_not_this_launch(self):
        self.write(header(SID + 'ff') + refusal())
        self.assertEqual(self.verdict(seconds=1)[:2], (1, ''))
        self.write(header(SID[:8]) + refusal())
        self.assertEqual(self.verdict(seconds=1)[:2], (1, ''))

    def test_the_first_verdict_counts(self):
        # Two late refusals of the switch come after its "Preflight passed"; the launch was answered by then.
        self.write(header(SID) + PASSED + refusal('could not make /data/local/tmp/oneos/tmp'))
        self.assertEqual(self.verdict()[:2], (0, 'passed\n'))
        self.write(header(SID) + refusal('no sha256sum') + PASSED)
        self.assertEqual(self.verdict()[:2], (0, 'refused no sha256sum\n'))

    def test_a_launch_line_starts_the_reading_again(self):
        # Session ids are not used twice; if one ever is, what the earlier launch got is not the later one's.
        self.write(header(SID) + refusal('battery too warm') + header(SID) + PASSED)
        self.assertEqual(self.verdict()[:2], (0, 'passed\n'))
        self.write(header(SID) + PASSED + header(SID))
        self.assertEqual(self.verdict(seconds=1)[:2], (1, ''))

    def test_only_a_line_that_begins_with_the_words_counts(self):
        self.write(header(SID) + 'note: PREFLIGHT REFUSED: not a verdict\n  Preflight passed, says a note\nx === OneOS app launch %s \n' % SID)
        self.assertEqual(self.verdict(seconds=1)[:2], (1, ''))
        self.write('x' + header(SID) + refusal())
        self.assertEqual(self.verdict(seconds=1)[:2], (1, ''), 'a launch line that does not begin the line')

    def test_a_verdict_that_comes_later_is_waited_for(self):
        self.write(header(SID))
        late = "( sleep 1.2; printf '%%s\\n' 'PREFLIGHT REFUSED: late one' >> '%s' ) &\n" % self.log
        rc, out, err, took = self.run_sh(function_text() + late + 'switch_verdict "%s" "%s" 10; rc=$?; wait; exit $rc\n' % (SID, self.log))
        self.assertEqual((rc, out, err), (0, 'refused late one\n', ''))
        self.assertTrue(1.0 < took < 3.5, took)

    def test_no_log_or_no_launch_line_gives_nothing(self):
        rc, out, err, took = self.verdict(seconds=1, log=os.path.join(self.dir, 'missing.log'))
        self.assertEqual((rc, out, err), (1, '', ''))
        self.write(refusal() + PASSED)
        self.assertEqual(self.verdict(seconds=1)[:3], (1, '', ''))

    def test_the_wait_ends_after_its_seconds(self):
        self.write(header(SID))
        rc, out, err, took = self.verdict(seconds=2)
        self.assertEqual((rc, out), (1, ''))
        self.assertTrue(1.9 < took < 4.0, took)


class LaunchEndTest(Base):
    def test_a_refused_switch_is_answered_as_refused(self):
        self.write(header(OLD) + refusal('no getevent') + header(SID) + refusal())
        rc, out, err, _ = self.end()
        self.assertEqual((rc, err), (2, ''))
        self.assertEqual(out.splitlines(), ['@@STEP switch started', '@@REFUSED ' + REASON])

    def test_a_passed_check_is_answered_ok(self):
        self.write(header(SID) + PASSED)
        rc, out, err, took = self.end()
        self.assertEqual((rc, err), (0, ''))
        self.assertEqual(out.splitlines(), ['@@STEP switch started', '@@OK launch ' + SID])
        self.assertLess(took, 0.45)

    def test_no_verdict_in_time_is_answered_as_before(self):
        self.write(header(SID) + 'some line of the switch\n')
        rc, out, err, took = self.end(seconds=1)
        self.assertEqual((rc, err), (0, ''))
        self.assertEqual(out.splitlines(), ['@@STEP switch started', '@@OK launch ' + SID])
        self.assertGreater(took, 0.9)

    def test_the_step_comes_before_the_wait(self):
        # The app keeps the launch for Last session when it saw this step; it must be out before a refusal.
        self.write(header(SID) + refusal())
        out = self.end()[1]
        self.assertTrue(out.startswith('@@STEP switch started\n@@REFUSED '), out)


class WordsTest(unittest.TestCase):
    """The words the function looks for are the ones the two scripts write."""

    def test_the_switch_script_writes_these_lines(self):
        self.assertIn('    echo "PREFLIGHT REFUSED: $*"\n', SWITCH)
        self.assertEqual(SWITCH.count('\necho "Preflight passed ('), 1)
        self.assertEqual(len('PREFLIGHT REFUSED: ') + 1, 20, 'substr($0, 20) starts at the reason')
        self.assertIn('substr($0, 20)', function_text())

    def test_the_launch_line_is_written_with_the_session_id_first(self):
        self.assertEqual(SCRIPT.count('    echo "=== OneOS app launch $sid $mode $(date'), 1)
        self.assertIn('index($0, "=== OneOS app launch " sid " ") == 1', function_text())

    def test_the_function_keeps_to_the_root_scripts_audit(self):
        # StageAudit (core/root): plain awk, no busybox applet, and the script's one sleep.
        fn = function_text()
        self.assertNotIn('$BB', fn)
        self.assertEqual(fn.count('sleep'), 1)
        self.assertIn('\n        sleep 1\n', fn)
        self.assertNotIn('while :', fn)

    def test_the_app_knows_the_step(self):
        job = (ROOT / 'app-android/app/src/full/kotlin/com/fahadali/oneos/session/LaunchJob.kt').read_text()
        self.assertIn('private const val SWITCH_STARTED = "switch started"', job)
        self.assertIn('if (SWITCH_STARTED !in reply.reply.steps) SessionPrefs.forgetLaunch(app)', job)


if __name__ == '__main__':
    unittest.main()
