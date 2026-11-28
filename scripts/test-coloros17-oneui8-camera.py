#!/usr/bin/env python3
"""Regression tests for ColorOS 17 (x9u-in-1105-a16) camera on One UI 8.0 hosts (Galaxy S22)."""
import hashlib
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUEST_PREPARE = ROOT / "switcher/assets/guest_prepare.sh"
ONEOS_SWITCH = ROOT / "switcher/assets/oneos_switch.sh"
PATCH_NATIVE_SH = ROOT / "scripts/patch-camera-native.sh"
A16_CAM_PY = ROOT / "switcher/patches/a16_camera.py"
A16_CRE_PY = ROOT / "switcher/patches/a16_camera_result_extras.py"
PIXEL_NATIVE_PY = ROOT / "switcher/patches/pixel_camera_native.py"


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


SAMPLE_COLOROS_CRE_SMALI = """\
.class public Landroid/hardware/camera2/impl/CaptureResultExtras;
.super Ljava/lang/Object;

.field private multiResConcurrentReadersStartInfo:[Landroid/hardware/camera2/impl/MultiResConcurrentReadersStartInfo;

.method public readFromParcel(Landroid/os/Parcel;)V
    .locals 5

    sget-object v1, Landroid/hardware/camera2/impl/MultiResConcurrentReadersStartInfo;->CREATOR:Landroid/os/Parcelable$Creator;

    invoke-virtual {v4, v1}, Landroid/os/Parcel;->createTypedArray(Landroid/os/Parcelable$Creator;)[Ljava/lang/Object;

    move-result-object v1

    check-cast v1, [Landroid/hardware/camera2/impl/MultiResConcurrentReadersStartInfo;

    iput-object v1, v3, Landroid/hardware/camera2/impl/CaptureResultExtras;->multiResConcurrentReadersStartInfo:[Landroid/hardware/camera2/impl/MultiResConcurrentReadersStartInfo;

    return-void
.end method
"""


class TestColorOS17OneUI8Camera(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gp_text = GUEST_PREPARE.read_text(encoding="utf-8")
        cls.os_text = ONEOS_SWITCH.read_text(encoding="utf-8")

    def test_shell_and_python_syntax(self):
        for sh_file in (GUEST_PREPARE, ONEOS_SWITCH, PATCH_NATIVE_SH):
            r = subprocess.run(["sh", "-n", str(sh_file)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{sh_file}: {r.stderr}")
        for py_file in (A16_CAM_PY, A16_CRE_PY, PIXEL_NATIVE_PY):
            r = subprocess.run(["python3", "-m", "py_compile", str(py_file)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{py_file}: {r.stderr}")

    def test_a16_camera_result_extras_coloros_smali(self):
        with tempfile.TemporaryDirectory() as td:
            cls = Path(td) / "smali_classes2/android/hardware/camera2/impl/CaptureResultExtras.smali"
            cls.parent.mkdir(parents=True)
            cls.write_text(SAMPLE_COLOROS_CRE_SMALI, encoding="utf-8")

            r1 = subprocess.run(["python3", str(A16_CRE_PY), td], capture_output=True, text=True)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            self.assertEqual(r1.stdout.strip(), "smali_classes2")
            patched = cls.read_text(encoding="utf-8")
            self.assertNotIn("createTypedArray", patched)
            self.assertIn("const/4 v1, 0x0", patched)
            self.assertIn(
                "new-array v1, v1, [Landroid/hardware/camera2/impl/MultiResConcurrentReadersStartInfo;",
                patched,
            )

            # Idempotent on second run
            r2 = subprocess.run(["python3", str(A16_CRE_PY), td], capture_output=True, text=True)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertEqual(r2.stdout.strip(), "")
            self.assertIn("already patched", r2.stderr)

    def test_a16_camera_wires_result_extras_and_guards(self):
        self.assertIn("a16_camera_result_extras.py", A16_CAM_PY.read_text(encoding="utf-8"))
        self.assertIn("libcamera_client_patched_oneui8.so", self.os_text)
        self.assertIn("libcamera_client_patched_oneui85.so", self.os_text)
        self.assertIn("framework_patched_oneui85.jar", self.os_text)
        self.assertIn("libcamera_client_patched_oneui8.so", self.gp_text)
        self.assertIn("CAMERA_SUFFIX", PATCH_NATIVE_SH.read_text(encoding="utf-8"))
        # samcam merge_up re-enabled by default after farm_dir propagation fix
        self.assertIn('${ONEOS_MERGE_UP:-1}', self.gp_text)
        self.assertNotIn('${ONEOS_MERGE_UP:-0}" = 1 ] && SMN=$(merge_up', self.gp_text)
        self.assertNotIn('if [ $SAMCAM = 1 ] && [ "${ONEOS_MERGE_UP:-0}" = 1 ]; then', self.gp_text)

    def test_samcam_vendor_lib_info_super_night_mpi_precision(self):
        """super_night.mpi is dropped when libAIQSolution_MPI is absent, while super_night.arcsoft.v2 is kept."""
        m = re.search(
            r"(awk -v drop=\"\$ff_drop\" -v ren=\"\$ff_ren\" '.*?'\s+\"\$SAMCAM_FF\")",
            self.gp_text,
            re.S,
        )
        self.assertIsNotNone(m, "VENDOR_LIB_INFO awk block not found")
        awk_expr = m.group(1)
        self.assertIn("super_night.mpi:libAIQSolution_MPI.camera.samsung.so", self.gp_text)

        sample_xml = (
            "<SecFloatingFeatureSet>\n"
            "<SEC_FLOATING_FEATURE_CAMERA_CONFIG_VENDOR_LIB_INFO>"
            "ai_clear_zoom.arcsoft.v2,super_night.mpi,super_night.arcsoft.v2,image_codec.samsung.v1,hdr.samsung.v1"
            "</SEC_FLOATING_FEATURE_CAMERA_CONFIG_VENDOR_LIB_INFO>\n"
            "</SecFloatingFeatureSet>\n"
        )
        with tempfile.TemporaryDirectory() as td:
            ff = Path(td) / "ff.xml"
            ff.write_text(sample_xml, encoding="utf-8")
            cmd = (
                f'SAMCAM_FF="{ff}"; '
                'ff_drop=" ai_clear_zoom super_night.mpi"; '
                'ff_ren="image_codec.samsung.v1=image_codec.samsung.v2"; '
                f"{awk_expr}"
            )
            r = subprocess.run(["sh", "-c", cmd], capture_output=True, text=True, check=True)
            self.assertNotIn("ai_clear_zoom.arcsoft.v2", r.stdout)
            self.assertNotIn("super_night.mpi", r.stdout)
            self.assertIn("super_night.arcsoft.v2", r.stdout)
            self.assertIn("image_codec.samsung.v2", r.stdout)
            self.assertIn("hdr.samsung.v1", r.stdout)
            self.assertIn("super_night.mpi", r.stderr)
            self.assertIn("image_codec.samsung.v1->image_codec.samsung.v2", r.stderr)

    def test_session_patchers_fail_closed_on_unknown_sha(self):
        fw_fn = extract_function(self.gp_text, "oneui8_patch_framework_jar")
        cl_fn = extract_function(self.gp_text, "oneui8_patch_camera_client")
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "unknown.bin"
            dst = Path(td) / "out.bin"
            src.write_bytes(b"not-a-matching-binary")
            for fn_name, fn_code in (("oneui8_patch_framework_jar", fw_fn), ("oneui8_patch_camera_client", cl_fn)):
                script = f'BB=""; {fn_code}\n{fn_name} "{src}" "{dst}"\n'
                r = subprocess.run(["sh", "-c", script], capture_output=True, text=True)
                self.assertEqual(r.returncode, 2, f"{fn_name} should return 2 on unknown sha, got {r.returncode}")
                self.assertFalse(dst.exists())

    @unittest.skipUnless(has_unshare_mount(), "unshare -Ur -m unavailable")
    def test_full_samcam_kernel510_stack_with_framework_and_camera_client_binds(self):
        """End-to-end Linux mount-namespace test of ColorOS 17 samcam_merge + system_ext without overlayfs + samcam_se_merge + camera binds."""
        helpers = "\n".join([
            extract_function(self.gp_text, "farm_dir"),
            extract_function(self.gp_text, "unfarm_dir"),
            extract_function(self.gp_text, "merge_up"),
            extract_function(self.gp_text, "bio_features_into"),
        ])
        with tempfile.TemporaryDirectory() as td:
            script = f"""
set -eu
T="{td}"
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
mkdir -p "$STAGE/session"
{helpers}

# Build ColorOS 17 rootfs layout
mkdir -p "$ROOTFS/system/lib64" "$ROOTFS/system/etc/permissions" "$ROOTFS/system/framework"
mkdir -p "$ROOTFS/system/system_ext/lib64" "$ROOTFS/system/system_ext/priv-app/OplusApp" "$ROOTFS/system/system_ext/framework" "$ROOTFS/system/system_ext/etc/permissions"
echo "COLOROS_LIBC" > "$ROOTFS/system/lib64/libc.so"
echo "COLOROS_CAM_CLIENT" > "$ROOTFS/system/lib64/libcamera_client.so"
echo "COLOROS_FW" > "$ROOTFS/system/framework/framework.jar"
echo "COLOROS_PERM" > "$ROOTFS/system/etc/permissions/platform.xml"
echo "COMPOSER_SO" > "$ROOTFS/system/system_ext/lib64/vendor.qti.hardware.display.composer@3.0.so"
echo "IMMLIST_SO" > "$ROOTFS/system/system_ext/lib64/libimmlistservice.so"
echo "DCS_SO" > "$ROOTFS/system/system_ext/lib64/libcommon_dcs_service.so"
echo "OPLUS_FW" > "$ROOTFS/system/system_ext/framework/oplus-framework.jar"

# 1) samcam_merge on $ROOTFS/system
SOV="$STAGE/system_ov"
mkdir -p "$SOV"
mount -t tmpfs -o size=4m,mode=755 tmpfs "$SOV"
$BB mount --make-private "$SOV"
mkdir -p "$SOV/up/cameradata" "$SOV/up/saiv" "$SOV/up/lib64" "$SOV/up/etc" "$SOV/up/framework"
BIO_FEATURES=1
bio_features_into "$SOV/up"
: > "$SOV/up/lib64/libMyFilterPlugin.camera.samsung.so"
: > "$SOV/up/etc/floating_feature.xml"
: > "$SOV/up/framework/scamera_sdk_util.jar"
SMN=$(merge_up "$SOV/up" "$ROOTFS/system" "$STAGE/samcam_merge")
[ "$SMN" -ge 4 ]
echo "SAM_PLUGIN" > "$STAGE/libMyFilterPlugin.camera.samsung.so"
echo "SAM_FF" > "$STAGE/floating_feature.xml"
echo "SAM_SDK" > "$STAGE/scamera_sdk_util.jar"
$BB mount --bind "$STAGE/libMyFilterPlugin.camera.samsung.so" "$ROOTFS/system/lib64/libMyFilterPlugin.camera.samsung.so"
$BB mount --bind "$STAGE/floating_feature.xml" "$ROOTFS/system/etc/floating_feature.xml"
$BB mount --bind "$STAGE/scamera_sdk_util.jar" "$ROOTFS/system/framework/scamera_sdk_util.jar"

# 2) system_ext without overlayfs
GUEST_SYSTEM_EXT="$ROOTFS/system/system_ext"
OV="$STAGE/system_ext_ov"
mkdir -p "$OV"
mount -t tmpfs -o size=1m,mode=755 tmpfs "$OV"
$BB mount --make-private "$OV"
FARM="$OV/farm"; FORIG="$OV/orig"
mkdir -p "$FARM/apex" "$FORIG"
for e in "$GUEST_SYSTEM_EXT"/*; do
    [ -e "$e" ] || [ -L "$e" ] || continue
    n=${{e##*/}}
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
    $BB mount --rbind "$e" "$GUEST_SYSTEM_EXT/${{e##*/}}"
done

# 3) samcam_se_merge on $GUEST_SYSTEM_EXT
SEUP="$STAGE/samcam_se_up"
mkdir -p "$SEUP"
mount -t tmpfs -o size=1m,mode=755 tmpfs "$SEUP"
$BB mount --make-private "$SEUP"
mkdir -p "$SEUP/priv-app/SamsungCamera" "$SEUP/framework" "$SEUP/etc/permissions"
: > "$SEUP/priv-app/SamsungCamera/SamsungCamera.apk"
: > "$SEUP/framework/semextendedformat.jar"
: > "$SEUP/etc/permissions/oneos-samcam-semextendedformat.xml"
SEM=$(merge_up "$SEUP" "$GUEST_SYSTEM_EXT" "$STAGE/samcam_se_merge")
[ "$SEM" -ge 3 ]
echo "SAMCAM_APK" > "$STAGE/SamsungCamera.apk"
echo "SEMEXT_JAR" > "$STAGE/semextendedformat.jar"
echo "SEMEXT_XML" > "$STAGE/oneos-samcam-semextendedformat.xml"
$BB mount --bind "$STAGE/SamsungCamera.apk" "$GUEST_SYSTEM_EXT/priv-app/SamsungCamera/SamsungCamera.apk"
$BB mount --bind "$STAGE/semextendedformat.jar" "$GUEST_SYSTEM_EXT/framework/semextendedformat.jar"
$BB mount --bind "$STAGE/oneos-samcam-semextendedformat.xml" "$GUEST_SYSTEM_EXT/etc/permissions/oneos-samcam-semextendedformat.xml"

# 4) Rebind One UI 8.0 patched framework.jar and libcamera_client.so over farmed system dirs
echo "PATCHED_FW_ONEUI8" > "$STAGE/session/framework.oneui8.session.jar"
echo "PATCHED_CL_ONEUI8" > "$STAGE/session/libcamera_client.oneui8.session.so"
$BB umount -l "$ROOTFS/system/framework/framework.jar" 2>/dev/null || true
$BB mount --bind "$STAGE/session/framework.oneui8.session.jar" "$ROOTFS/system/framework/framework.jar"
$BB umount -l "$ROOTFS/system/lib64/libcamera_client.so" 2>/dev/null || true
$BB mount --bind "$STAGE/session/libcamera_client.oneui8.session.so" "$ROOTFS/system/lib64/libcamera_client.so"

# Assertions: ColorOS system_ext/lib64 intact, Samsung Camera intact, patched framework & camera client active, 0 leaks
[ "$(cat "$GUEST_SYSTEM_EXT/lib64/vendor.qti.hardware.display.composer@3.0.so")" = "COMPOSER_SO" ]
[ "$(cat "$GUEST_SYSTEM_EXT/lib64/libimmlistservice.so")" = "IMMLIST_SO" ]
[ "$(cat "$GUEST_SYSTEM_EXT/lib64/libcommon_dcs_service.so")" = "DCS_SO" ]
[ "$(cat "$GUEST_SYSTEM_EXT/priv-app/SamsungCamera/SamsungCamera.apk")" = "SAMCAM_APK" ]
[ "$(cat "$GUEST_SYSTEM_EXT/framework/semextendedformat.jar")" = "SEMEXT_JAR" ]
[ "$(cat "$GUEST_SYSTEM_EXT/framework/oplus-framework.jar")" = "OPLUS_FW" ]
[ "$(cat "$ROOTFS/system/lib64/libMyFilterPlugin.camera.samsung.so")" = "SAM_PLUGIN" ]
[ "$(cat "$ROOTFS/system/lib64/libc.so")" = "COLOROS_LIBC" ]
[ "$(cat "$ROOTFS/system/lib64/libcamera_client.so")" = "PATCHED_CL_ONEUI8" ]
[ "$(cat "$ROOTFS/system/framework/framework.jar")" = "PATCHED_FW_ONEUI8" ]
grep -q 'android.hardware.fingerprint' "$ROOTFS/system/etc/permissions/android.hardware.fingerprint.xml"
LEAKS=$(grep -c '/farm/' /proc/self/mountinfo || true)
[ "$LEAKS" = 0 ] || {{ echo "leaked mounts into farm: $LEAKS"; exit 1; }}
echo "OK_FULL_SAMCAM_STACK"
"""
            r = subprocess.run(["unshare", "-Ur", "-m", "sh", "-c", script], capture_output=True, text=True, timeout=30)
            self.assertEqual(r.returncode, 0, f"stderr={r.stderr}\nstdout={r.stdout}")
            self.assertIn("OK_FULL_SAMCAM_STACK", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
