#!/usr/bin/env python3
"""Tests for Samsung AIDL fingerprint selection and guest preparation."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PATCHER = ROOT / "switcher/patches/guest_force_aidl_fingerprint.py"
PREPARE = (ROOT / "switcher/assets/guest_prepare.sh").read_text()
REL = Path("smali/com/android/server/biometrics/sensors/fingerprint/FingerprintService.smali")


class GuestFingerprintTest(unittest.TestCase):
    def test_patcher_accepts_both_known_register_shapes(self):
        for register in ("v3", "p1"):
            with self.subTest(register=register), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / REL
                path.parent.mkdir(parents=True)
                path.write_text(
                    ".class public Lcom/android/server/biometrics/sensors/fingerprint/FingerprintService;\n"
                    ".method private initSensors()V\n"
                    "    .line 1089\n"
                    "    invoke-virtual {p1}, Landroid/hardware/fingerprint/FingerprintSensorConfigurations;->getResetLockoutRequiresHardwareAuthToken()Z\n\n"
                    f"    move-result {register}\n"
                    ".end method\n"
                )
                result = subprocess.run(
                    [sys.executable, "-I", str(PATCHER), tmp],
                    check=True, capture_output=True, text=True,
                )
                patched = path.read_text()
                self.assertEqual("smali\n", result.stdout)
                self.assertIn(f"const/4 {register}, 0x1", patched)
                self.assertNotIn("getResetLockoutRequiresHardwareAuthToken", patched)

    def test_guest_preparation_carries_only_biometric_metadata(self):
        self.assertIn("$STAGE/data/vendor_de/0/fpdata", PREPARE)
        self.assertIn("settings_fingerprint_0.xml settings_face.xml", PREPARE)
        self.assertIn("out=settings_fingerprint.xml", PREPARE)
        self.assertIn('su -g 1000 -G 1000 -c "cat \'$src\' > \'$tmp\'"', PREPARE)
        self.assertNotIn("gatekeeper.password.key\" \"$BIO_DST", PREPARE)

    def test_guest_declares_biometric_features(self):
        self.assertIn('feature name="android.hardware.fingerprint"', PREPARE)
        self.assertIn('feature name="android.hardware.biometrics.face"', PREPARE)


if __name__ == "__main__":
    unittest.main()
