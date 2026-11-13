#!/usr/bin/env python3
"""Galaxy A15 guests keep status-bar content inside the physical panel."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "switcher/assets/oneos_switch.sh").read_text()
BLOCK = SOURCE.split("# The Galaxy A15's physical top corners", 1)[1].split(
    "if [ $GUEST_AOSP_SYSUI = 1 ]", 1
)[0]


class A15StatusBarInsets(unittest.TestCase):
    def test_override_is_scoped_to_a15_aosp_systemui(self):
        self.assertIn('[ \\"${ONEOS_PROFILE:-}\\" = a15 ]', BLOCK)
        self.assertIn('[ $GUEST_AOSP_SYSUI = 1 ]', BLOCK)

    def test_device_verified_insets_are_registered(self):
        self.assertIn("PAD=56", BLOCK)
        self.assertIn("OneOSStatusBarTop", BLOCK)
        self.assertIn("status_bar_padding_top=16", BLOCK)

    def test_stale_top_overlay_is_disabled_for_other_sessions(self):
        self.assertIn(
            "OneOSCutout|OneOSCutoutRect|OneOSStatusBarHeight|"
            "OneOSStatusBarTop|OneOSCornerPadding)",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
