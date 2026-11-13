#!/usr/bin/env python3
"""Guest status-bar content stays inside the physical panel: device-verified
inset values live in a per-profile table, and the Galaxy A15's values are
applied to AOSP guest SystemUIs."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "switcher/assets/oneos_switch.sh").read_text()
TABLE_ANCHOR = "Device-verified status-bar insets"
TABLE = SOURCE.split(TABLE_ANCHOR, 1)[1].split('if [ -n \\"$PADV\\" ]', 1)[0]


class A15StatusBarInsets(unittest.TestCase):
    def test_device_verified_values_live_in_a_per_profile_table(self):
        self.assertEqual(1, SOURCE.count(TABLE_ANCHOR))
        self.assertIn("a15) PADV=56; TOPV=16", TABLE)
        self.assertIn("*) PADV=; TOPV= ;;", TABLE)

    def test_the_table_only_applies_to_aosp_guest_systemuis(self):
        self.assertIn('if [ -n \\"$PADV\\" ] && [ $GUEST_AOSP_SYSUI = 1 ]', SOURCE)
        self.assertIn("PAD=$PADV", SOURCE)
        self.assertIn("status_bar_padding_top=$TOPV", SOURCE)

    def test_device_verified_insets_are_registered(self):
        self.assertIn("OneOSStatusBarTop", SOURCE)

    def test_stale_top_overlay_is_disabled_for_other_sessions(self):
        self.assertIn(
            "OneOSCutout|OneOSCutoutRect|OneOSStatusBarHeight|"
            "OneOSStatusBarTop|OneOSCornerPadding)",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
