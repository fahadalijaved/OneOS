#!/usr/bin/env python3
"""The MediaTek A2DP recovery (Galaxy A15/A16 4G MT6789 device-confirmed) is
armed for the whole MediaTek family, triggered only by the exact HAL failure,
and has a bounded retry."""

from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
START = (ROOT / "switcher/assets/guest_start.sh").read_text()
GATE_ANCHOR = 'bt_soc="$(getprop'
IF_ANCHOR = 'if [ "$bt_mtk" = 1 ] && [ "${ONEOS_GUEST_BT_RECOVER:-1}" = 1 ]; then'


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


class Mt6789BluetoothRecoveryTest(unittest.TestCase):
    def test_gate_arms_the_whole_mediaTek_family_and_keeps_the_escape_hatch(self):
        self.assertEqual(1, START.count(GATE_ANCHOR))
        self.assertEqual(1, START.count(IF_ANCHOR))
        gate = START.split(GATE_ANCHOR, 1)[1].split(IF_ANCHOR, 1)[0]
        # All four SoC properties are matched: builds leave ro.soc.model empty
        # or suffix it, Samsung reports it uppercase, and A25/A33-style boards
        # put universalNNNN/s5eNNNN on ro.board.platform/ro.hardware.
        for prop in (
            "ro.board.platform",
            "ro.hardware",
            "ro.soc.manufacturer",
            "ro.soc.model",
        ):
            self.assertIn(prop, gate)
        self.assertIn("*mt[0-9]*|*MT[0-9]*|*[Mm]edia[Tt]ek*", gate)
        self.assertIn("ONEOS_GUEST_BT_RECOVER=0 disables it", START)

    def test_mediaTek_devices_arm_and_other_socs_do_not(self):
        sh = find_sh()
        if not sh:
            self.skipTest("a POSIX shell is not installed")
        cases = [
            # name, platform, hardware, manufacturer, model, extra env, armed
            ("a15", "mt6789", "mt6789", "MediaTek", "MT6789", {}, True),
            ("a16-4g-suffixed-model", "mt6789", "mt6789", "MediaTek", "MT6789V/CD", {}, True),
            ("mediaTek-empty-soc-model", "mt6789", "mt6789", "MediaTek", "", {}, True),
            ("mediaTek-only-soc-model", "", "", "", "MT6789", {}, True),
            ("mediaTek-lowercase-name", "mt6768", "mt6768", "mediatek", "", {}, True),
            ("qualcomm", "pineapple", "qcom", "QTI", "SM8850", {}, False),
            ("exynos-a25-a33", "universal8825", "s5e8825", "Samsung", "", {}, False),
            ("opt-out", "mt6789", "mt6789", "MediaTek", "MT6789", {"ONEOS_GUEST_BT_RECOVER": "0"}, False),
        ]
        gate = GATE_ANCHOR + START.split(GATE_ANCHOR, 1)[1].split(IF_ANCHOR, 1)[0]
        script = gate + "\n" + IF_ANCHOR + " echo armed; else echo disarmed; fi"
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / "getprop"
            stub.write_text(
                "#!/bin/sh\n"
                'case "$1" in\n'
                '    ro.board.platform) echo "$FAKE_PLATFORM" ;;\n'
                '    ro.hardware) echo "$FAKE_HARDWARE" ;;\n'
                '    ro.soc.manufacturer) echo "$FAKE_MANUFACTURER" ;;\n'
                '    ro.soc.model) echo "$FAKE_MODEL" ;;\n'
                "esac\n",
                encoding="utf-8",
                newline="\n",
            )
            stub.chmod(0o755)
            for name, platform, hardware, manufacturer, model, extra, armed in cases:
                with self.subTest(name=name):
                    env = dict(os.environ)
                    env["PATH"] = f"{tmp}{os.pathsep}{env.get('PATH', '')}"
                    env["FAKE_PLATFORM"] = platform
                    env["FAKE_HARDWARE"] = hardware
                    env["FAKE_MANUFACTURER"] = manufacturer
                    env["FAKE_MODEL"] = model
                    env.update(extra)
                    out = subprocess.run(
                        [sh, "-c", script],
                        env=env,
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    self.assertEqual("armed" if armed else "disarmed", out.stdout.strip())

    def test_trigger_requires_both_the_specific_hal_failure_and_active_a2dp(self):
        body = START.split("<<'BTRECOVEREOF'\n", 1)[1].split("\nBTRECOVEREOF", 1)[0]
        self.assertIn("grep -F 'session_type=A2DP_SOFTWARE_ENCODING_DATAPATH'", body)
        self.assertIn("grep -F 'state=DISABLED failure'", body)
        self.assertIn("dumpsys bluetooth_manager 2>/dev/null | grep -q '<- ACTIVE'", body)
        self.assertNotIn('factoryReset', body)

    def test_it_retries_at_most_once_and_records_the_result(self):
        body = START.split("<<'BTRECOVEREOF'\n", 1)[1].split("\nBTRECOVEREOF", 1)[0]
        actions = re.findall(r'cmd bluetooth_manager ([^ >]+)', body)
        self.assertEqual(['disable', 'enable'], actions)
        # The stack boots slowly on some ROMs (HyperOS: its own wait-for-state
        # timed out and the earbuds bound to the half-initialized stack), so the
        # OFF and ON states are polled with long timeouts and the recovery
        # settles 8 s after ON before looking for the replacement session.
        self.assertNotIn('cmd bluetooth_manager wait-for-state', body)
        self.assertIn("grep -q '^  State:  *OFF$'", body)
        self.assertIn("grep -q '^  State:  *ON$'", body)
        self.assertIn('while [ $n -lt 30 ]', body)
        self.assertIn('while [ $n -lt 45 ]', body)
        self.assertIn('sleep 8', body)
        self.assertIn('while [ $waited -lt 25 ]', body)
        self.assertEqual(2, body.count('exit 0'))
        self.assertIn('while [ $attempt -le 2 ]', body)
        self.assertIn('replacement A2DP session STARTED on attempt $attempt', body)
        self.assertIn('A2DP recovery exhausted after 2 attempts', body)
        self.assertIn('while [ $i -lt 300 ]', body)


if __name__ == '__main__':
    unittest.main()
