#!/usr/bin/env python3
"""A guest restart that keeps the previous generation's audio HAL restarts the
HAL, because the new audioserver cannot open the primary output on the old one
(Galaxy A15 Infinity-X 16:10:33: createTrack error -19 for the whole session).
A fresh HAL, or a first run, is left alone."""

from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
START = (ROOT / "switcher/assets/guest_start.sh").read_text()
BLOCK_ANCHOR = (
    "hpid=$(dumpsys --pid android.hardware.audio.core.IModule/default"
    ' 2>/dev/null | head -n 1 | tr -dc 0-9)\n    hprev=$(cat /data/oneos_audio_hal.pid 2>/dev/null)'
)
END_ANCHOR = 'if [ -n "$hpid" ]; then echo "$hpid" > /data/oneos_audio_hal.pid; fi'


def find_sh():
    sh = shutil.which("sh")
    if not sh and os.name == "nt":
        candidate = (
            Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            / "Git/usr/bin/sh.exe"
        )
        if candidate.is_file():
            sh = str(candidate)
    return sh


class AudioHalStaleRestartTest(unittest.TestCase):
    def setUp(self):
        self.assertEqual(1, START.count(BLOCK_ANCHOR))
        self.assertEqual(1, START.count(END_ANCHOR))
        block = BLOCK_ANCHOR + START.split(BLOCK_ANCHOR, 1)[1].split(END_ANCHOR, 1)[0] + END_ANCHOR
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.fix = d / "fix"
        self.fix.mkdir()
        self.pidfile = d / "oneos_audio_hal.pid"
        self.block = block.replace(
            "/data/oneos_audio_hal.pid", str(self.pidfile).replace("\\", "/")
        )
        for name, text in (
            ("getprop", '#!/bin/sh\ncase "$1" in\n  ""|all) echo "[init.svc.vendor.audio-hal-2-0]: [running]" ;;\nesac\n'),
            ("dumpsys", '#!/bin/sh\nif [ -e "$FIX/restarted" ]; then echo "$FAKE_NEW_PID"; else echo "$FAKE_OLD_PID"; fi\n'),
            ("setprop", '#!/bin/sh\nprintf "%s\\n" "$@" >> "$FIX/setprop.log"\n[ "$1" = ctl.restart ] && : > "$FIX/restarted"\n'),
            ("sleep", "#!/bin/sh\n"),
        ):
            p = self.fix / name
            p.write_text(text, encoding="utf-8", newline="\n")
            p.chmod(0o755)
        self.sh = find_sh()

    def tearDown(self):
        self.tmp.cleanup()

    def run_block(self, old="2920", new="4311", pre_pid=None):
        env = dict(os.environ)
        env["PATH"] = f"{self.fix}{os.pathsep}{env.get('PATH', '')}"
        env["FIX"] = str(self.fix)
        env["FAKE_OLD_PID"] = old
        env["FAKE_NEW_PID"] = new
        if pre_pid is not None:
            self.pidfile.write_text(pre_pid)
        script = self.block + '\nprintf "%s" "$(cat ' + str(self.pidfile).replace("\\", "/") + ' 2>/dev/null)"'
        out = subprocess.run(
            [self.sh, "-c", script], env=env, capture_output=True, text=True, check=True
        )
        self.assertEqual("", out.stderr)
        sp = self.fix / "setprop.log"
        restarts = sp.read_text().splitlines() if sp.exists() else []
        return out.stdout, restarts, (self.fix / "restarted").exists()

    def test_stale_hal_is_restarted_through_its_init_services(self):
        out, restarts, restarted = self.run_block(pre_pid="2920")
        self.assertTrue(restarted)
        self.assertEqual(["ctl.restart", "vendor.audio-hal-2-0"], restarts[0:2])
        self.assertIn("audio HAL survived the guest restart as pid 2920", out)
        self.assertIn("audio HAL pid after the restart: 4311", out)
        self.assertEqual("4311", out.strip().splitlines()[-1])

    def test_a_fresh_hal_is_left_alone_but_recorded(self):
        out, restarts, restarted = self.run_block(pre_pid="4999")
        self.assertFalse(restarted)
        self.assertNotIn("survived the guest restart", out)
        self.assertEqual("2920", out.strip())

    def test_the_first_run_records_the_pid_without_restarting(self):
        out, restarts, restarted = self.run_block()
        self.assertFalse(restarted)
        self.assertEqual("2920", out.strip())

    def test_an_hal_that_survives_the_restart_call_is_killed(self):
        # ctl.restart ran, but the stub keeps reporting the old pid: the block
        # falls back to killing the pid so init starts the service again. The
        # fake pid is not a real process here, so the kill is a no-op and the
        # recorded pid stays the old one.
        env = dict(os.environ)
        env["PATH"] = f"{self.fix}{os.pathsep}{env.get('PATH', '')}"
        env["FIX"] = str(self.fix)
        env["FAKE_OLD_PID"] = "2920"
        env["FAKE_NEW_PID"] = "2920"
        self.pidfile.write_text("2920")
        script = self.block + '\nprintf "%s" "$(cat ' + str(self.pidfile).replace("\\", "/") + ' 2>/dev/null)"'
        out = subprocess.run(
            [self.sh, "-c", script], env=env, capture_output=True, text=True, check=True
        )
        self.assertIn("still pid 2920 after the ctl.restart; killing it", out.stdout)
        self.assertIn("audio HAL pid after the restart: 2920 (waited 20s)", out.stdout)
        self.assertEqual("2920", out.stdout.strip().splitlines()[-1])


if __name__ == "__main__":
    unittest.main()
