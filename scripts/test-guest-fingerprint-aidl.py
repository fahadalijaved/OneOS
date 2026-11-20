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
    @staticmethod
    def fixture(locals_count=4, include_transport=True):
        body = f"    .locals {locals_count}\n"
        if include_transport:
            body += (
                "    invoke-virtual {p1}, Landroid/hardware/fingerprint/FingerprintSensorConfigurations;->getResetLockoutRequiresHardwareAuthToken()Z\n\n"
                "    move-result v3\n"
            )
        return (
            ".class public Lcom/android/server/biometrics/sensors/fingerprint/FingerprintService;\n"
            ".method private getProviders(Landroid/hardware/fingerprint/FingerprintSensorConfigurations;)Ljava/util/List;\n"
            + body + ".end method\n"
        )

    @staticmethod
    def run_patcher(root):
        return subprocess.run(
            [sys.executable, "-I", str(PATCHER), str(root)],
            capture_output=True, text=True,
        )

    def test_patcher_selects_aidl_when_registered_and_preserves_image_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / REL
            path.parent.mkdir(parents=True)
            path.write_text(self.fixture())
            result = self.run_patcher(tmp)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("smali\n", result.stdout)
            patched = path.read_text()
            self.assertIn(".locals 5", patched)
            self.assertIn('const-string v4, "android.hardware.biometrics.fingerprint.IFingerprint/default"', patched)
            self.assertIn("invoke-static {v4}, Landroid/os/ServiceManager;->getService", patched)
            self.assertIn("if-eqz v4, :oneos_fingerprint_hidl", patched)
            self.assertIn("invoke-virtual {p1}, Landroid/hardware/fingerprint/FingerprintSensorConfigurations;->getResetLockoutRequiresHardwareAuthToken()Z", patched)
            self.assertEqual(1, patched.count("getResetLockoutRequiresHardwareAuthToken"))

    def test_patcher_fails_closed_when_the_framework_has_no_fingerprint_service(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_patcher(tmp)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("expected exactly one", result.stderr)

    def test_patcher_fails_closed_when_the_transport_choice_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / REL
            path.parent.mkdir(parents=True)
            original = self.fixture(include_transport=False)
            path.write_text(original)
            result = self.run_patcher(tmp)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("read is not there once (found 0)", result.stderr)
            self.assertEqual(original, path.read_text())

    def test_patcher_fails_closed_on_an_unknown_method_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / REL
            path.parent.mkdir(parents=True)
            original = self.fixture(locals_count=5)
            path.write_text(original)
            result = self.run_patcher(tmp)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("getProviders is not there once with .locals 4", result.stderr)
            self.assertEqual(original, path.read_text())

    def test_patcher_fails_closed_on_ambiguous_transport_choices(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / REL
            path.parent.mkdir(parents=True)
            call = (
                "    invoke-virtual {p1}, Landroid/hardware/fingerprint/FingerprintSensorConfigurations;->getResetLockoutRequiresHardwareAuthToken()Z\n\n"
                "    move-result v3\n"
            )
            original = self.fixture().replace(call, call + call)
            path.write_text(original)
            result = self.run_patcher(tmp)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("found 2", result.stderr)
            self.assertEqual(original, path.read_text())

    def test_guest_preparation_creates_the_fingerprint_data_directory(self):
        self.assertIn("$STAGE/data/vendor_de/0/fpdata", PREPARE)

    def test_guest_declares_biometric_features(self):
        self.assertIn('feature name="android.hardware.fingerprint"', PREPARE)
        self.assertIn('feature name="android.hardware.biometrics.face"', PREPARE)


if __name__ == "__main__":
    unittest.main()
