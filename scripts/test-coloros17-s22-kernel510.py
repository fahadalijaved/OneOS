#!/usr/bin/env python3
"""Regression tests for ColorOS 17 kernel 5.10 fallbacks and ultrasonic refresh rate on Galaxy S22."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUEST_PREPARE = ROOT / "switcher/assets/guest_prepare.sh"
ONEOS_SWITCH = ROOT / "switcher/assets/oneos_switch.sh"


def extract_function(text: str, name: str) -> str:
    m = re.search(rf"^{re.escape(name)}\(\)\s*\{{", text, re.M)
    if not m:
        raise AssertionError(f"function {name}() not found")
    start = m.start()
    end = re.search(r"^\}", text[m.end():], re.M)
    if not end:
        raise AssertionError(f"closing brace for {name}() not found")
    return text[start:m.end() + end.end()]


def has_unshare_mount() -> bool:
    r = subprocess.run(
        ["unshare", "-Ur", "-m", "sh", "-c", "true"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return r.returncode == 0


def run_in_ns(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["unshare", "-Ur", "-m", "sh", "-eu", "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestColorOS17S22Kernel510(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gp_text = GUEST_PREPARE.read_text(encoding="utf-8")
        cls.os_text = ONEOS_SWITCH.read_text(encoding="utf-8")
        cls.farm_helpers = "\n".join([
            extract_function(cls.gp_text, "farm_dir"),
            extract_function(cls.gp_text, "unfarm_dir"),
            extract_function(cls.gp_text, "merge_up"),
            extract_function(cls.gp_text, "bio_features_into"),
            extract_function(cls.gp_text, "secims_mountpoints"),
            extract_function(cls.gp_text, "sec_ims_bind"),
        ])

    def _preamble(self, workdir: str) -> str:
        # Provide a shim BB script that forwards to real Linux mount/umount/mkdir
        # while stubbing Android-only chcon so the exact shell functions from
        # guest_prepare.sh execute unmodified inside unshare -Ur -m.
        return f"""
T="{workdir}"
BB="$T/bb"
cat > "$BB" <<'EOF'
#!/bin/sh
cmd=$1; shift
case "$cmd" in
    chcon) exit 0 ;;
    *) exec "$cmd" "$@" ;;
esac
EOF
chmod +x "$BB"
STAGE="$T/data/stage"
ROOTFS="$T/rootfs"
mkdir -p "$T/data" "$ROOTFS"
mount -t tmpfs tmpfs "$T/data"
mount --make-shared "$T/data"
mount -t tmpfs tmpfs "$ROOTFS"
mount --make-rprivate "$ROOTFS"
mkdir -p "$STAGE"
{self.farm_helpers}
"""

    def test_shell_syntax(self):
        for p in (GUEST_PREPARE, ONEOS_SWITCH):
            r = subprocess.run(["sh", "-n", str(p)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{p} syntax error: {r.stderr}")

    def test_static_guards_present(self):
        # farm_dir isolates tmpfs and target propagation and labels symlinks/stubs with target context
        fn = extract_function(self.gp_text, "farm_dir")
        self.assertIn('mount --make-private "$fd_f"', fn)
        self.assertIn('mount --make-private "$fd_t"', fn)
        self.assertIn('chcon -h -R "$fd_c" "$fd_f"', fn)
        # system_ext_ov and bio_features_ov are isolated
        self.assertIn('$BB mount --make-private "$OV"', self.gp_text)
        self.assertIn('$BB mount --make-private "$BFO"', self.gp_text)
        self.assertIn('$BB mount --rbind "$GUEST_SYSTEM_EXT" "$FORIG" && $BB mount --make-rprivate "$FORIG"', self.gp_text)
        # BIO_FEATURES no longer gated behind ONEOS_MERGE_UP=0
        bio_block = self.gp_text[self.gp_text.index('BFO="$STAGE/bio_features_ov"'):]
        bio_block = bio_block[:bio_block.index("VK_HIDL_OV=0")]
        self.assertNotIn("ONEOS_MERGE_UP", bio_block)
        # MPF and SEC_IMS non-overlayfs fallbacks exist
        self.assertIn('MPX="$OV/up/etc/permissions/oneos-my-product-features.xml"', self.gp_text)
        self.assertIn('SIUP="$STAGE/secims_se_up"', self.gp_text)
        self.assertIn("ODM_AI_FALLBACK=1", self.gp_text)

    @unittest.skipUnless(has_unshare_mount(), "unshare -Ur -m unavailable")
    def test_coloros22test9_propagation_regression(self):
        """Reproduce coloros22test9: farm_dir(system) followed by system_ext without overlayfs must keep system_ext/lib64 intact."""
        with tempfile.TemporaryDirectory() as td:
            script = self._preamble(td) + """
mkdir -p "$ROOTFS/system/system_ext/lib64" "$ROOTFS/system/lib64" "$ROOTFS/system/etc"
echo "COMPOSER_SO" > "$ROOTFS/system/system_ext/lib64/vendor.qti.hardware.display.composer@3.0.so"
echo "IMMLIST_SO" > "$ROOTFS/system/system_ext/lib64/libimmlistservice.so"
echo "DCS_SO" > "$ROOTFS/system/system_ext/lib64/libcommon_dcs_service.so"
echo "LIBC_SO" > "$ROOTFS/system/lib64/libc.so"
ln -s libc.so "$ROOTFS/system/lib64/libc_link.so"

# Step 1: merge_up on $ROOTFS/system (as samcam_merge does)
mkdir -p "$STAGE/up/cameradata" "$STAGE/up/saiv" "$STAGE/up/lib64"
: > "$STAGE/up/lib64/libMyFilterPlugin.camera.samsung.so"
N=$(merge_up "$STAGE/up" "$ROOTFS/system" "$STAGE/samcam_merge")
[ "$N" = 2 ] || { echo "expected 2 farmed dirs, got $N"; exit 1; }

# Step 2: system_ext without overlayfs (exact propagation-safe sequence)
GUEST_SYSTEM_EXT="$ROOTFS/system/system_ext"
OV="$STAGE/system_ext_ov"
mkdir -p "$OV"
mount -t tmpfs -o size=1m,mode=755 tmpfs "$OV"
$BB mount --make-private "$OV"
FARM="$OV/farm"; FORIG="$OV/orig"
mkdir -p "$FARM/apex" "$FORIG"
for e in "$GUEST_SYSTEM_EXT"/*; do
    [ -e "$e" ] || [ -L "$e" ] || continue
    n=${e##*/}
    if [ -L "$e" ]; then cp -P "$e" "$FARM/$n"
    elif [ -d "$e" ]; then mkdir -p "$FARM/$n"
    else : > "$FARM/$n"; fi
done
$BB mount --rbind "$GUEST_SYSTEM_EXT" "$FORIG"
$BB mount --make-rprivate "$FORIG"
$BB mount --bind "$FARM" "$GUEST_SYSTEM_EXT"
$BB mount --make-private "$GUEST_SYSTEM_EXT"
for e in "$FORIG"/*; do
    [ -e "$e" ] && [ ! -L "$e" ] || continue
    $BB mount --rbind "$e" "$GUEST_SYSTEM_EXT/${e##*/}"
done

# Assertions: every system_ext/lib64 library and system/lib64 symlink is intact, zero farm leaks
[ "$(cat "$GUEST_SYSTEM_EXT/lib64/vendor.qti.hardware.display.composer@3.0.so")" = "COMPOSER_SO" ]
[ "$(cat "$GUEST_SYSTEM_EXT/lib64/libimmlistservice.so")" = "IMMLIST_SO" ]
[ "$(cat "$GUEST_SYSTEM_EXT/lib64/libcommon_dcs_service.so")" = "DCS_SO" ]
[ -d "$GUEST_SYSTEM_EXT/apex" ]
[ -d "$ROOTFS/system/cameradata" ]
[ -L "$ROOTFS/system/lib64/libc_link.so" ]
[ "$(cat "$ROOTFS/system/lib64/libc_link.so")" = "LIBC_SO" ]
LEAKS=$(grep -c '/farm/' /proc/self/mountinfo || true)
[ "$LEAKS" = 0 ] || { echo "leaked mounts into farm: $LEAKS"; exit 1; }
echo "OK_PROPAGATION"
"""
            r = run_in_ns(script)
            self.assertEqual(r.returncode, 0, f"stderr={r.stderr}\nstdout={r.stdout}")
            self.assertIn("OK_PROPAGATION", r.stdout)

    @unittest.skipUnless(has_unshare_mount(), "unshare -Ur -m unavailable")
    def test_odm_ai_fallback_with_existing_and_missing_lib64(self):
        """oplus_odm_ai.tar fallback binds libaiboost.so + nested aiframe/*.so both when /odm/lib64 exists and when absent."""
        with tempfile.TemporaryDirectory() as td:
            script = self._preamble(td) + """
ODM_AI="$STAGE/odm_ai"
mkdir -p "$ODM_AI/lib64/aiframe"
echo "AIBOOST" > "$ODM_AI/lib64/libaiboost.so"
echo "LITERT" > "$ODM_AI/lib64/aiframe/libaiboost_litert.so"
echo "QNN" > "$ODM_AI/lib64/aiframe/libaiboost_qnn_external_delegate.so"
echo "stamp" > "$ODM_AI/.from_tar"

# Case A: /odm/lib64 exists
mkdir -p "$ROOTFS/odm/lib64"
echo "HOST_ODM" > "$ROOTFS/odm/lib64/libhost_odm.so"
ODMN=$(merge_up "$ODM_AI/lib64" "$ROOTFS/odm/lib64" "$STAGE/odm_ai_merge")
[ "$ODMN" = 1 ]
[ "$(cat "$ROOTFS/odm/lib64/libhost_odm.so")" = "HOST_ODM" ]
[ "$(cat "$ROOTFS/odm/lib64/libaiboost.so")" = "AIBOOST" ]
[ "$(cat "$ROOTFS/odm/lib64/aiframe/libaiboost_litert.so")" = "LITERT" ]
[ "$(cat "$ROOTFS/odm/lib64/aiframe/libaiboost_qnn_external_delegate.so")" = "QNN" ]
[ ! -e "$ROOTFS/odm/.from_tar" ]

# Case B: /odm has no lib64 directory
mkdir -p "$ROOTFS/odm2/etc"
echo "ODM_CFG" > "$ROOTFS/odm2/etc/cfg.xml"
farm_dir "$ROOTFS/odm2" "$STAGE/odm2_merge/f0" lib64/
$BB mount --bind "$ODM_AI/lib64" "$ROOTFS/odm2/lib64"
[ "$(cat "$ROOTFS/odm2/etc/cfg.xml")" = "ODM_CFG" ]
[ "$(cat "$ROOTFS/odm2/lib64/libaiboost.so")" = "AIBOOST" ]
[ "$(cat "$ROOTFS/odm2/lib64/aiframe/libaiboost_litert.so")" = "LITERT" ]
echo "OK_ODM_AI"
"""
            r = run_in_ns(script)
            self.assertEqual(r.returncode, 0, f"stderr={r.stderr}\nstdout={r.stdout}")
            self.assertIn("OK_ODM_AI", r.stdout)

    @unittest.skipUnless(has_unshare_mount(), "unshare -Ur -m unavailable")
    def test_bio_features_fallback_isolated_to_permissions_dir(self):
        """BIO_FEATURES fallback farms only /system/etc/permissions and leaves /system root and /system/lib64 untouched."""
        with tempfile.TemporaryDirectory() as td:
            script = self._preamble(td) + """
mkdir -p "$ROOTFS/system/etc/permissions" "$ROOTFS/system/lib64"
echo "ORIG_PERM" > "$ROOTFS/system/etc/permissions/platform.xml"
echo "ORIG_LIB" > "$ROOTFS/system/lib64/libc.so"
BIO_FEATURES=1
BFO="$STAGE/bio_features_ov"
mkdir -p "$BFO"
mount -t tmpfs -o size=1m,mode=755 tmpfs "$BFO"
$BB mount --make-private "$BFO"
mkdir -p "$BFO/up"
bio_features_into "$BFO/up"
BFN=$(merge_up "$BFO/up/etc/permissions" "$ROOTFS/system/etc/permissions" "$STAGE/bio_features_merge")
[ "$BFN" = 1 ]
grep -q 'android.hardware.fingerprint' "$ROOTFS/system/etc/permissions/android.hardware.fingerprint.xml"
grep -q 'android.hardware.biometrics.face' "$ROOTFS/system/etc/permissions/android.hardware.biometrics.face.xml"
[ "$(cat "$ROOTFS/system/etc/permissions/platform.xml")" = "ORIG_PERM" ]
# /system and /system/lib64 were never farmed
! grep -q " $ROOTFS/system tmpfs " /proc/mounts
! grep -q " $ROOTFS/system/lib64 tmpfs " /proc/mounts
echo "OK_BIO"
"""
            r = run_in_ns(script)
            self.assertEqual(r.returncode, 0, f"stderr={r.stderr}\nstdout={r.stdout}")
            self.assertIn("OK_BIO", r.stdout)

    @unittest.skipUnless(has_unshare_mount(), "unshare -Ur -m unavailable")
    def test_mpf_and_secims_stacked_without_overlayfs(self):
        """MPF (Circle to Search / PowerShare) and SEC_IMS stack cleanly in system_ext without overlayfs."""
        with tempfile.TemporaryDirectory() as td:
            script = self._preamble(td) + """
GUEST_SYSTEM_EXT="$ROOTFS/system/system_ext"
mkdir -p "$GUEST_SYSTEM_EXT/etc/permissions" "$GUEST_SYSTEM_EXT/framework" "$GUEST_SYSTEM_EXT/lib64" "$GUEST_SYSTEM_EXT/priv-app/ExistingApp"
echo "EXISTING_PERM" > "$GUEST_SYSTEM_EXT/etc/permissions/existing.xml"
echo "IMMLIST_SO" > "$GUEST_SYSTEM_EXT/lib64/libimmlistservice.so"
echo "EXISTING_JAR" > "$GUEST_SYSTEM_EXT/framework/oplus-framework.jar"

# Stage MPF file
OV="$STAGE/system_ext_ov"
mkdir -p "$OV"
mount -t tmpfs -o size=1m,mode=755 tmpfs "$OV"
$BB mount --make-private "$OV"
mkdir -p "$OV/up/etc/permissions"
cat > "$OV/up/etc/permissions/oneos-my-product-features.xml" <<'XML'
<?xml version="1.0" encoding="utf-8"?>
<permissions>
    <feature name="com.google.android.feature.CONTEXTUAL_SEARCH" />
    <feature name="oplus.power.onwirelesscharger.support" />
</permissions>
XML

# Stage SEC_IMS set
SECIMS="$STAGE/secims"
mkdir -p "$SECIMS/priv-app/OneOSSecIms" "$SECIMS/framework" "$SECIMS/lib64" "$SECIMS/etc/permissions"
echo "IMS_APK" > "$SECIMS/priv-app/OneOSSecIms/imsservice.apk"
echo "IMS_JAR" > "$SECIMS/framework/imsmanager.jar"
echo "IMS_SO" > "$SECIMS/lib64/libsec-ims.so"
echo "ENG_TXT" > "$SECIMS/etc/public.libraries-engmodejni.samsung.txt"
echo "IMS_XML" > "$SECIMS/etc/permissions/imsmanager_library.xml"

# 1) Bind MPF into etc/permissions via farm_dir
MPX="$OV/up/etc/permissions/oneos-my-product-features.xml"
farm_dir "$GUEST_SYSTEM_EXT/etc/permissions" "$STAGE/sysext_mpf_farm" oneos-my-product-features.xml
$BB mount --bind "$MPX" "$GUEST_SYSTEM_EXT/etc/permissions/oneos-my-product-features.xml"
$BB mount -o remount,bind,ro "$GUEST_SYSTEM_EXT/etc/permissions/oneos-my-product-features.xml"

# 2) Stack SEC_IMS on top via secims_mountpoints + merge_up + sec_ims_bind
SIUP="$STAGE/secims_se_up"
mkdir -p "$SIUP"
mount -t tmpfs -o size=1m,mode=755 tmpfs "$SIUP"
$BB mount --make-private "$SIUP"
secims_mountpoints "$SIUP"
SIM=$(merge_up "$SIUP" "$GUEST_SYSTEM_EXT" "$STAGE/secims_se_merge")
[ "$SIM" -ge 4 ]
sec_ims_bind

# Verify existing ColorOS files, MPF, and SEC_IMS are all intact simultaneously
[ "$(cat "$GUEST_SYSTEM_EXT/etc/permissions/existing.xml")" = "EXISTING_PERM" ]
grep -q 'CONTEXTUAL_SEARCH' "$GUEST_SYSTEM_EXT/etc/permissions/oneos-my-product-features.xml"
grep -q 'oplus.power.onwirelesscharger.support' "$GUEST_SYSTEM_EXT/etc/permissions/oneos-my-product-features.xml"
[ "$(cat "$GUEST_SYSTEM_EXT/etc/permissions/imsmanager_library.xml")" = "IMS_XML" ]
[ "$(cat "$GUEST_SYSTEM_EXT/priv-app/OneOSSecIms/imsservice.apk")" = "IMS_APK" ]
[ "$(cat "$GUEST_SYSTEM_EXT/framework/imsmanager.jar")" = "IMS_JAR" ]
[ "$(cat "$GUEST_SYSTEM_EXT/framework/oplus-framework.jar")" = "EXISTING_JAR" ]
[ "$(cat "$GUEST_SYSTEM_EXT/lib64/libsec-ims.so")" = "IMS_SO" ]
[ "$(cat "$GUEST_SYSTEM_EXT/lib64/libimmlistservice.so")" = "IMMLIST_SO" ]
[ "$(cat "$GUEST_SYSTEM_EXT/etc/public.libraries-engmodejni.samsung.txt")" = "ENG_TXT" ]
echo "OK_MPF_SECIMS"
"""
            r = run_in_ns(script)
            self.assertEqual(r.returncode, 0, f"stderr={r.stderr}\nstdout={r.stdout}")
            self.assertIn("OK_MPF_SECIMS", r.stdout)

    @unittest.skipUnless(has_unshare_mount(), "unshare -Ur -m unavailable")
    def test_mpf_when_permissions_subdir_absent(self):
        """MPF fallback creates etc/permissions/oneos-my-product-features.xml when etc/permissions does not exist."""
        with tempfile.TemporaryDirectory() as td:
            script = self._preamble(td) + """
GUEST_SYSTEM_EXT="$ROOTFS/system/system_ext"
mkdir -p "$GUEST_SYSTEM_EXT/etc"
echo "ETC_FILE" > "$GUEST_SYSTEM_EXT/etc/existing.conf"
MPX="$STAGE/oneos-my-product-features.xml"
echo "<permissions><feature name='CONTEXTUAL_SEARCH'/></permissions>" > "$MPX"
farm_dir "$GUEST_SYSTEM_EXT/etc" "$STAGE/sysext_mpf_etc_farm" permissions/oneos-my-product-features.xml
$BB mount --bind "$MPX" "$GUEST_SYSTEM_EXT/etc/permissions/oneos-my-product-features.xml"
[ "$(cat "$GUEST_SYSTEM_EXT/etc/existing.conf")" = "ETC_FILE" ]
grep -q 'CONTEXTUAL_SEARCH' "$GUEST_SYSTEM_EXT/etc/permissions/oneos-my-product-features.xml"
echo "OK_MPF_NEW_SUBDIR"
"""
            r = run_in_ns(script)
            self.assertEqual(r.returncode, 0, f"stderr={r.stderr}\nstdout={r.stdout}")
            self.assertIn("OK_MPF_NEW_SUBDIR", r.stdout)

    @unittest.skipUnless(has_unshare_mount(), "unshare -Ur -m unavailable")
    def test_merge_up_rollback_on_failure(self):
        """If merge_up fails mid-way, mu_rollback cleanly unmounts earlier farmed folders."""
        with tempfile.TemporaryDirectory() as td:
            script = self._preamble(td) + """
mkdir -p "$ROOTFS/tgt/a" "$ROOTFS/tgt/b"
echo "ORIG_A" > "$ROOTFS/tgt/a/keep.txt"
# Make tgt/b a symlink so the second farm_dir fails
rmdir "$ROOTFS/tgt/b"
ln -s /nonexistent "$ROOTFS/tgt/b"
mkdir -p "$STAGE/layer/a" "$STAGE/layer/b"
echo "NEW_A" > "$STAGE/layer/a/new.txt"
echo "NEW_B" > "$STAGE/layer/b/new.txt"
# Override: make tgt/b appear as a dir check fail via symlink to real dir so [ -d ] is true but [ ! -L ] fails in farm_dir
mkdir -p "$STAGE/real_b"
ln -snf "$STAGE/real_b" "$ROOTFS/tgt/b"

if merge_up "$STAGE/layer" "$ROOTFS/tgt" "$STAGE/roll_w" >/dev/null; then
    echo "expected merge_up to fail on symlinked subdir"
    exit 1
fi
[ ! -e "$ROOTFS/tgt/a/new.txt" ]
[ "$(cat "$ROOTFS/tgt/a/keep.txt")" = "ORIG_A" ]
! grep -q " $ROOTFS/tgt/a tmpfs " /proc/mounts
echo "OK_ROLLBACK"
"""
            r = run_in_ns(script)
            self.assertEqual(r.returncode, 0, f"stderr={r.stderr}\nstdout={r.stdout}")
            self.assertIn("OK_ROLLBACK", r.stdout)

    def test_guest_orr_dyn_ultrasonic_vs_optical(self):
        """GUEST_ORR_DYN stays 1 on ultrasonic Galaxy S22 and S24 FE, and 0 on optical or unknown UDFPS."""
        m = re.search(
            r"(GUEST_ORR_DYN=1\n.*?if \[ -s \"\$STAGE/data/system/oneos_udfps\" \].*?\nfi)",
            self.os_text,
            re.S,
        )
        self.assertIsNotNone(m, "GUEST_ORR_DYN block not found in oneos_switch.sh")
        snippet = m.group(1)

        cases = [
            ("SM-S901E", True, "<SEC_FLOATING_FEATURE_BIOAUTH_CONFIG_FINGERPRINT_FEATURES>ultrasonic_display_phone</SEC_FLOATING_FEATURE_BIOAUTH_CONFIG_FINGERPRINT_FEATURES>", "1"),
            ("SM-S908E", True, "<SEC_FLOATING_FEATURE_BIOAUTH_CONFIG_FINGERPRINT_FEATURES>ultrasonic_display_phone</SEC_FLOATING_FEATURE_BIOAUTH_CONFIG_FINGERPRINT_FEATURES>", "1"),
            ("SM-A366B", True, "<SEC_FLOATING_FEATURE_BIOAUTH_CONFIG_FINGERPRINT_FEATURES>optical_display_phone</SEC_FLOATING_FEATURE_BIOAUTH_CONFIG_FINGERPRINT_FEATURES>", "0"),
            ("SM-S721B", True, "<SEC_FLOATING_FEATURE_BIOAUTH_CONFIG_FINGERPRINT_FEATURES>optical_display_phone</SEC_FLOATING_FEATURE_BIOAUTH_CONFIG_FINGERPRINT_FEATURES>", "1"),
            ("SM-A556B", True, None, "0"),
            ("SM-F956B", False, None, "1"),
        ]
        for model, has_udfps, ff_line, expected in cases:
            with tempfile.TemporaryDirectory() as td:
                stage = Path(td) / "stage"
                (stage / "data/system").mkdir(parents=True)
                if has_udfps:
                    (stage / "data/system/oneos_udfps").write_text("540 1980 90\n")
                ff_path = Path(td) / "floating_feature.xml"
                if ff_line is not None:
                    ff_path.write_text(f"<SecFloatingFeatureSet>\n{ff_line}\n</SecFloatingFeatureSet>\n")
                test_snippet = snippet.replace("/system/etc/floating_feature.xml", str(ff_path))
                cmd = f'STAGE="{stage}"; getprop() {{ echo "{model}"; }}; {test_snippet}; echo "$GUEST_ORR_DYN"'
                r = subprocess.run(["sh", "-c", cmd], capture_output=True, text=True, check=True)
                self.assertEqual(
                    r.stdout.strip(),
                    expected,
                    f"model={model}, has_udfps={has_udfps}, ff={ff_line}: got {r.stdout.strip()!r}, want {expected!r}",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
