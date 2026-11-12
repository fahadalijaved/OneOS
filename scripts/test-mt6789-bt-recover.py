#!/usr/bin/env python3
"""The MT6789 A2DP recovery is narrowly armed and has a bounded retry."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
START = (ROOT / "switcher/assets/guest_start.sh").read_text()


class Mt6789BluetoothRecoveryTest(unittest.TestCase):
    def test_only_mt6789_arms_the_recovery_and_it_has_an_escape_hatch(self):
        gate = re.search(
            r'if \[ "\$\(getprop ro\.soc\.model\)" = MT6789 \] && '
            r'\[ "\$\{ONEOS_GUEST_BT_RECOVER:-1\}" = 1 \]; then',
            START,
        )
        self.assertIsNotNone(gate)
        self.assertIn('ONEOS_GUEST_BT_RECOVER=0 disables it', START)

    def test_trigger_requires_both_the_specific_hal_failure_and_active_a2dp(self):
        body = START.split("<<'BTRECOVEREOF'\n", 1)[1].split("\nBTRECOVEREOF", 1)[0]
        self.assertIn("grep -F 'session_type=A2DP_SOFTWARE_ENCODING_DATAPATH'", body)
        self.assertIn("grep -F 'state=DISABLED failure'", body)
        self.assertIn("dumpsys bluetooth_manager 2>/dev/null | grep -q '<- ACTIVE'", body)
        self.assertNotIn('factoryReset', body)

    def test_it_retries_at_most_once_and_records_the_result(self):
        body = START.split("<<'BTRECOVEREOF'\n", 1)[1].split("\nBTRECOVEREOF", 1)[0]
        actions = re.findall(r'cmd bluetooth_manager ([^ >]+)', body)
        self.assertEqual(
            ['disable', 'wait-for-state:STATE_OFF', 'enable', 'wait-for-state:STATE_ON'],
            actions,
        )
        self.assertEqual(2, body.count('exit 0'))
        self.assertIn('while [ $attempt -le 2 ]', body)
        self.assertIn('while [ $waited -lt 12 ]', body)
        self.assertIn('replacement A2DP session STARTED on attempt $attempt', body)
        self.assertIn('A2DP recovery exhausted after 2 attempts', body)
        self.assertIn('while [ $i -lt 300 ]', body)


if __name__ == '__main__':
    unittest.main()
