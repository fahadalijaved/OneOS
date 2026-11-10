#!/bin/sh
# Build the framework overlays that guest_prepare.sh bind-mounts over the
# guest image (services_patched.jar etc.), from the GSI image itself.
#
# Only the dex files that contain a patched class are rebuilt; the rest of each
# jar is copied byte for byte from the image.
#
# Usage: scripts/make-overlays.sh <system.img> [outdir]   (default out/overlays)
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
IMG="$1"
OUT="${2:-$ROOT/out/overlays}"
APKTOOL=${APKTOOL:-$(ls "$ROOT"/mysticgsi/tools/apktool/*.jar 2>/dev/null | head -1)}
# aapt2, zipalign, apksigner and android.jar for the checks and static RROs below.
SDK="${ANDROID_HOME:-/opt/android-sdk}"
BT=$(ls -d "$SDK"/build-tools/* | sort -V | tail -1)
AJ=$(ls "$SDK"/platforms/android-*/android.jar | sort -V | tail -1)
DEBUGFS=$(command -v debugfs || echo /usr/sbin/debugfs)
# A file the image has (ColorOS's own jars are not in a Pixel image).
in_image() { "$DEBUGFS" -R "stat $1" "$IMG" 2>&1 | grep -q '^Inode:'; }
[ -f "$IMG" ] || { echo "usage: $0 <system.img> [outdir]" >&2; exit 2; }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$OUT"
# Absolute: the zip steps below run in their own directories.
OUT=$(cd "$OUT" && pwd)

# vold: the guest's own vold registers "gvld" instead of "vold" (run 44). Up to
# run 43 it took over "vold" and android.system.vold.IVold/default in the shared
# servicemanager; One UI's vold kept running without its names and cannot be
# restarted (init.rc: reboot_on_failure), so only a reboot gave One UI its
# storage back (docs/inplace-return.md). Only the builds pinned below, by
# sha256; done before services.jar, whose patch (patches/guest_own_vold.py)
# goes with it. Offsets are the Pixel 17 (yogi) build's, then ColorOS 17
# CP2A.260605.016's (the Find N6 and Find X9 Ultra images carry the same vold
# and service.incremental.so):
# - vold 0xde12 / 0x104e7 "vold" -> "gvld": the String16
#   VoldNativeService::start() passes to addService (adrp 0x65100 + add
#   0x65104 / adrp 0x79174 + add 0x79178); the other 9 references are
#   async_safe log tags in forked children. 4 bytes: "gvld" has no '/' or '.',
#   so servicemanager wants no VINTF declaration for it.
# - vold 0x64ac8 / 0x78b64 "tbz w19, #0, +0xd4" -> "b +0xd4":
#   VendorVoldNativeService::try_start always takes its "not declared" path
#   (returns OK), so the guest never registers android.system.vold.IVold/
#   default. Not renamed: a VINTF name servicemanager refuses unless the
#   manifest declares it.
# - service.incremental.so 0x64129 / 0x6536c "vold" -> "gvld": both
#   IncrementalService lookups (adr, and adrp + add with String16(s, 4)); the
#   guest system_server loads it (run 43: incfs v2).
# Function addresses from each binary's .gnu_debugdata symbols; segments: file
# offset == vaddr in all four files. The crashrecovery APEX is pinned too: its
# RescueParty is the guest's one call left that reaches One UI's "vold"
# (RecoverySystem.rebootPromptAndWipeUserData), and only while RescueParty is
# on (AOSP's isDisabled() in both builds), which guest_start.sh checks. On
# ColorOS, OPPO's OplusStorageManagerFeature looks up "vold" too
# (oplus-services.jar, guest_own_vold.py --oplus below). Other images are not
# patched and their guest vold keeps "vold" (no return without a reboot).
# "gvld" falls to service_contexts' catch-all default_android_service, which
# only a permissive session may add and find.
rm -f "$OUT/vold_patched" "$OUT/service.incremental_patched.so"
"$DEBUGFS" -R "dump /system/bin/vold $WORK/vold" "$IMG" 2>/dev/null
"$DEBUGFS" -R "dump /system/lib64/service.incremental.so $WORK/service.incremental.so" "$IMG" 2>/dev/null
"$DEBUGFS" -R "dump /system/apex/com.google.android.crashrecovery.apex $WORK/crashrecovery-google.apex" "$IMG" 2>/dev/null
"$DEBUGFS" -R "dump /system/apex/com.android.crashrecovery.apex $WORK/crashrecovery-aosp.apex" "$IMG" 2>/dev/null
"$DEBUGFS" -R "dump /system/apex/com.google.android.crashrecovery_compressed.apex $WORK/crashrecovery-google-compressed.apex" "$IMG" 2>/dev/null
"$DEBUGFS" -R "dump /system/apex/com.android.crashrecovery.capex $WORK/crashrecovery-aosp.capex" "$IMG" 2>/dev/null
python3 -I - "$WORK" "$OUT/vold_patched" "$OUT/service.incremental_patched.so" <<'PYEOF'
import hashlib, os, sys
work, vold_out, inc_out = sys.argv[1:4]
# The NULs either side: the whole string, not a suffix of a longer one.
NAME = (b"\0vold\0", b"\0gvld\0")
TRY_START = (bytes.fromhex("b3060036"), bytes.fromhex("35000014"))
BUILDS = [
    ("Pixel 17 (yogi)", {
        "vold": "5ecfb2f67a941129a382a150a865d01ad62898d534dafc102ac1fab832b335b7",
        "service.incremental.so": "3add0c259ba1e76378359d556d792136f96ce75197c99ff9d3d7fe850d8e4a92",
        "crashrecovery-google.apex": "fc82e88e3234efc0db0fff5da07e66005f6530e930671a42ac64788421793947",
    }, [("vold", 0xde11, NAME), ("vold", 0x64ac8, TRY_START), ("service.incremental.so", 0x64128, NAME)]),
    # The Pixel 11 Pro (kodiak) image of the same build: the same vold and
    # service.incremental.so, a crashrecovery APEX packaged differently whose
    # service-crashrecovery.jar decompiles to the same smali as yogi's.
    ("Pixel 17 (kodiak)", {
        "vold": "5ecfb2f67a941129a382a150a865d01ad62898d534dafc102ac1fab832b335b7",
        "service.incremental.so": "3add0c259ba1e76378359d556d792136f96ce75197c99ff9d3d7fe850d8e4a92",
        "crashrecovery-google.apex": "8ae8917117e528bc876f8658633a65ed370b32ac1f8b77180909a94a5d1f87b9",
    }, [("vold", 0xde11, NAME), ("vold", 0x64ac8, TRY_START), ("service.incremental.so", 0x64128, NAME)]),
    # The Pixel 9 Pro XL (komodo) image, CP3A.261005.005: the same code at other
    # offsets. start() takes the string at 0xdbcb (adrp 0x653f0 + add 0x653f4; the
    # other 9 references are umount/remountStorageDirs log tags), try_start's tbz
    # on isDeclared() is at +0x68 (0x64db8), service.incremental.so has both
    # lookups (adr 0xc0f7c, adrp + add 0xc3870 with String16(s, 4)) on the string
    # at 0x64328. Its crashrecovery APEX (compressed) has the same
    # RescueParty.isDisabled() as yogi's.
    ("Pixel 17 (komodo)", {
        "vold": "498c6d86fb7232e1b7d486ac6202672aab60837dd1e665bfc303ba14ff31c16a",
        "service.incremental.so": "b519753a86b5389434b170434913e8216c263de73606dd368d1098b04d583e9c",
        "crashrecovery-google.apex": "4c47853948d58166facca39a6b58d00bf47302e38b6e8a8989c622a0e15c6521",
    }, [("vold", 0xdbca, NAME), ("vold", 0x64db8, TRY_START), ("service.incremental.so", 0x64327, NAME)]),
    ("ColorOS 17 CP2A.260605.016 (Find N6, Find X9 Ultra)", {
        "vold": "3df4d13bb9636cb9833a6ee2027d189c6acfd25b0404058ca130afb164a55896",
        "service.incremental.so": "43ae83091df41f9cd43fa985e7b629e09ba9f581d93336d0efb38dd05de1bab8",
        "crashrecovery-aosp.apex": "a8396ec6bebe9511a701315964314aa8a755bef32d20cf4458293ed319bfdcf1",
    }, [("vold", 0x104e6, NAME), ("vold", 0x78b64, TRY_START), ("service.incremental.so", 0x6536b, NAME)]),
    # The Find X9 Ultra IN (global) build of the same release: its vold is
    # the CN one laid out 0x2000 later (the same instructions; start() takes
    # the string at 0x7b178, try_start's tbz is at +0x68 as in the CN build),
    # service.incremental.so has the string and both lookups where the CN one
    # has them, and its compressed crashrecovery APEX holds the same
    # service-crashrecovery.jar as Pixel's yogi, byte for byte.
    ("ColorOS 17 CP2A.260605.016 IN (Find X9 Ultra global)", {
        "vold": "7fe53478f0e482e64a680bd12f6ead83f0501d62cab5d6de085bfeec8acecc5f",
        "service.incremental.so": "25979ef93ee4b1a781c16adc783febdba2462563e5a7e69f4ba24d011d4b8427",
        "crashrecovery-google-compressed.apex": "304784481c167b3d196c9ba8ce8d45ea7b59b04b2c061d0b19ed0a4e93574f50",
    }, [("vold", 0x104e6, NAME), ("vold", 0x7ab64, TRY_START), ("service.incremental.so", 0x6536b, NAME)]),
    # Project Infinity-X 4.1 for the Find X9 Ultra (lighthouse, CP2A.260605.016),
    # built from source: its own layout. start() takes the string at 0xe164
    # (adrp 0xe000 + add 0x164), try_start's tbz w19 is at 0x64d8c (+0xd4, as
    # above), service.incremental.so has the string at 0x646c1 with both
    # lookups (adr at 0xc051c, adrp + add at 0xc2a7c). Its compressed
    # crashrecovery APEX (.capex) holds the same service-crashrecovery.jar as
    # Pixel's yogi, byte for byte.
    ("Infinity-X 4.1 CP2A.260605.016 (Find X9 Ultra)", {
        "vold": "7bc11b794ac19af6a2e1e7dc2bcf9baad3f3a673079f574b90132469a303c613",
        "service.incremental.so": "c964e27681a3632a7f83acb1698acffa572b3ece773690bc64444dff7bfaf7a7",
        "crashrecovery-aosp.capex": "1c4fa1a8417b233765db1621f3911b66de230049c39b248f116c3d18a8920ca6",
    }, [("vold", 0xe163, NAME), ("vold", 0x64d8c, TRY_START), ("service.incremental.so", 0x646c0, NAME)]),
    # HyperOS OS4.0 (Xiaomi lhasa, 2026-10): start() takes "vold" at 0xf3fd
    # (adrp 0xf000 + add 0x3fd at 0x6e8f4, the binary's only "\0vold\0"),
    # try_start's tbz w19, #0, +0xd4 is at 0x6e2d4, and service.incremental.so
    # has the string at 0x64746 with its two lookups (adr at 0xc0794, adrp + add
    # at 0xc2e28). Its crashrecovery APEX (com.android.crashrecovery.capex) has
    # AOSP's RescueParty.isDisabled (persist.sys.disable_rescue), and the wipe
    # behind it. The seventh HyperOS run's guest vold took "vold", and the
    # return could only reboot ("vold is not registered").
    ("HyperOS OS4.0 (lhasa)", {
        "vold": "06c00894fa5ce1bb1c6bc7821ef60ae18907ed9d9a213d37987cdfe633c798f7",
        "service.incremental.so": "e7da297ddedc625df330317c2321b5a2fd25f4dd2535f9c65a1490b5b8d6687d",
        "crashrecovery-aosp.capex": "d31bc1ccbb9bd60d2c78f0bd045cbb194838f936aafe2b551ab5d8344c9f2cd8",
    }, [("vold", 0xf3fc, NAME), ("vold", 0x6e2d4, TRY_START), ("service.incremental.so", 0x64745, NAME)]),
    # Nothing OS 5.0 (Metroid, AQ3A.250924.001): start() takes "vold" at 0xe1e8
    # (adrp 0xe000 + add 0x1e8 at 0x64d38, then String16 and a new
    # VoldNativeService; the binary's only "\0vold\0", whose other 9 references
    # are __android_log_print tags around 0xa56c0, as on the Pixel builds).
    # try_start's tbz w19, #0, +0xd4 is at 0x64728, right after the
    # isDeclared("android.system.vold.IVold/default", the string at 0x14316)
    # call through the service manager's vtable +0x48; patched it always takes
    # the not-declared path, which logs and returns 0 without registering the
    # AIDL instance. service.incremental.so has the string at 0x64411 with its
    # two lookups (adr at 0xc005c, adrp + add at 0xc2714). Its compressed
    # crashrecovery APEX holds AOSP's RescueParty.isDisabled -- the same four
    # tests in the same order (persist.sys.enable_rescue,
    # persist.device_config.configuration.disable_rescue_party, eng/userdebug,
    # persist.sys.disable_rescue) -- so guest_start.sh's property check holds.
    ("Nothing OS 5.0 AQ3A.250924.001 (Metroid)", {
        "vold": "536cc0b286923afbb6be2aad9457b8420dbd93e78bfe14fcfdbfef06f6901148",
        "service.incremental.so": "7509ea1a751e70400057bf1afd79876b2630ad0fd1ee2e993ff06a8f1528ca74",
        "crashrecovery-google-compressed.apex": "e2661820811896284537a044664dee933e5fd62a879efe02b5104d1388f43816",
    }, [("vold", 0xe1e7, NAME), ("vold", 0x64728, TRY_START), ("service.incremental.so", 0x64410, NAME)]),
    # vivo OriginOS 17 (X500 Pro Max, MediaTek, CP2A.260605.016): start() takes
    # "vold" at 0x10e24 (adrp 0x10000 + add 0xe24 at 0x83a1c, the binary's only
    # "\0vold\0"); try_start's tbz w19, #0, +0xd4 on the isDeclared() result is at
    # 0x83384 (+0x74 into try_start, 0x83310). service.incremental.so has the
    # string at 0x6578e with its two lookups. Its compressed crashrecovery APEX
    # holds Pixel yogi's service-crashrecovery.jar (AOSP RescueParty.isDisabled).
    # Not optional here: vivo's IVold interleaves vendor methods (26 getDuInfo, 27
    # rmFile...), so any guest IVold call reaching One UI's "vold" would run
    # another method on the phone's storage daemon.
    ("vivo OriginOS 17 CP2A.260605.016 (X500 Pro Max)", {
        "vold": "da6af9f4b1152c9ca3b66df5d75ac7a94d4c386d6ce6c991a0151e50e02db4ed",
        "service.incremental.so": "649cb1e9dd6db10f09a038600fe5818f5542f32f0d0350c43c9404b8ffbbc66d",
        "crashrecovery-google-compressed.apex": "f6750712189d56e68dacdb092c418acb092176ed7e33bef4d37d72a15b4970c2",
    }, [("vold", 0x10e23, NAME), ("vold", 0x83384, TRY_START), ("service.incremental.so", 0x6578d, NAME)]),
    # vivo OriginOS 6 CN (PD2609MA, k6993v1_64, MediaTek, 2026-09-01): start()
    # takes "vold" at 0x10e40 (adrp 0x10000 + add 0xe40 at 0x83a1c, the binary's
    # only "\0vold\0"; its 25 other references are log tags: async_safe_format_log
    # in umountStorageDirs, the exFat/Ntfs check and mount logs). try_start
    # (0x83310) has its tbz w19, #0, +0xd4 on the isDeclared() result at 0x83384,
    # as in the global build. service.incremental.so is the global build's, byte
    # for byte. Its uncompressed com.android.crashrecovery.apex has AOSP's
    # RescueParty.isDisabled (the same four tests in the same order), checked by
    # all four observer entry points before executeFactoryReset.
    ("vivo OriginOS 6 CN (PD2609MA, k6993v1_64)", {
        "vold": "db7106d6ff3f45d7b4b2cbb411d6b35233d268b18c9dc971c9bd4166f0836d0b",
        "service.incremental.so": "649cb1e9dd6db10f09a038600fe5818f5542f32f0d0350c43c9404b8ffbbc66d",
        "crashrecovery-aosp.apex": "5bad89011c1d327d211cbe450d28887515c94c16ed1db574f13b050bd7e79333",
    }, [("vold", 0x10e3f, NAME), ("vold", 0x83384, TRY_START), ("service.incremental.so", 0x6578d, NAME)]),
    # OnePlus OxygenOS 16 (CPH2745 16.0.10.601, Android 16): start() takes "vold" at
    # 0xfd4a (adrp 0xf000 + add 0xd4a at 0x75f78, then String16 and a new
    # VoldNativeService; the binary's only "\0vold\0", its other 9 references are
    # log tags around 0xb9734). try_start's tbz w19, #0, +0xd4 is at 0x758e4, right
    # after isDeclared("android.system.vold.IVold/default", adr 0x17f83) through the
    # service manager's vtable +0x48. service.incremental.so has the string at
    # 0x4f883 with its two lookups (adr at 0x98fb8 in BinderIncrementalService::start,
    # adrp + add at 0x9b6a4 with String16(s, 4)). Its crashrecovery APEX
    # (com.android.crashrecovery.apex, erofs) has AOSP's RescueParty.isDisabled
    # (persist.sys.enable_rescue, the DeviceConfig flag, eng/userdebug,
    # persist.sys.disable_rescue). 0.4.67: without it every OxygenOS return rebooted
    # ("vold is not registered", S22 Ultra 96977dcc, A34 deb8690c).
    ("OnePlus OxygenOS 16 BP2A (CPH2745)", {
        "vold": "cd18c5313787c3bd5f182c7bcfb6982d4b23f5629a1c95be41cef2c156d7ebc1",
        "service.incremental.so": "e24c296c9148f71faa35267e535e65d9ed527206e25d929d371eb400cc8f2279",
        "crashrecovery-aosp.apex": "626a82dda7c6cc0dfc7ee26397466b75a3d5d12bdaf0a1cd8d9c521c6142c548",
    }, [("vold", 0xfd49, NAME), ("vold", 0x758e4, TRY_START), ("service.incremental.so", 0x4f882, NAME)]),
]
def read(name):
    p = os.path.join(work, name)
    return bytearray(open(p, "rb").read()) if os.path.isfile(p) else bytearray()
def sha(d):
    return hashlib.sha256(d).hexdigest()
data = {n: read(n) for n in ("vold", "service.incremental.so", "crashrecovery-google.apex", "crashrecovery-aosp.apex", "crashrecovery-google-compressed.apex", "crashrecovery-aosp.capex")}
build = next((b for b in BUILDS if all(sha(data[n]) == want for n, want in b[1].items())), None)
if build is None:
    have = ", ".join("%s %s" % (n, sha(d)[:12] if d else "missing") for n, d in data.items())
    print("vold: not a build this was written against (%s): not patched, the guest vold keeps the name vold" % have)
    sys.exit(0)
for name, off, (old, new) in build[2]:
    d = data[name]
    if d[off:off + len(old)] != old:
        sys.exit("%s: unexpected bytes at %#x, not patching" % (name, off))
    d[off:off + len(old)] = new
open(vold_out, "wb").write(data["vold"])
open(inc_out, "wb").write(data["service.incremental.so"])
print("built %s for %s (registers gvld, not android.system.vold.IVold/default)" % (vold_out, build[0]))
print("built %s (looks up gvld)" % inc_out)
PYEOF
VOLD_GVLD=0
if [ -f "$OUT/vold_patched" ]; then
    chmod 755 "$OUT/vold_patched"
    chmod 644 "$OUT/service.incremental_patched.so"
    VOLD_GVLD=1
fi

# services.jar: LocalDisplayAdapter falls back to the active mode when
# SurfaceFlinger has no desired mode specs (see patches/display_mode_specs.py).
"$DEBUGFS" -R "dump /system/framework/services.jar $WORK/services.jar" "$IMG" 2>/dev/null
java -jar "$APKTOOL" d -q -f -r -o "$WORK/services" "$WORK/services.jar"
SMALI=$(grep -rl "Desired display mode specs from SurfaceFlinger are null" "$WORK/services" | head -1)
[ -n "$SMALI" ] || { echo "LocalDisplayAdapter not found in services.jar" >&2; exit 1; }
python3 -I "$ROOT/switcher/patches/display_mode_specs.py" "$SMALI"
DISPLAY_DIR="$(basename "$(dirname "$(dirname "$(dirname "$(dirname "$(dirname "$SMALI")")")")")")"
# And never let the guest send user-key calls to the host's vold
# (patches/guest_no_vold_keys.py).
KEY_DIRS=$(python3 -I "$ROOT/switcher/patches/guest_no_vold_keys.py" "$WORK/services")
# Skip the host vendor's APEX system services (patches/skip_host_apex_services.py).
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/skip_host_apex_services.py" "$WORK/services")"
# Never let the guest reboot or shut down the shared phone (patches/guest_power_guards.py).
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/guest_power_guards.py" "$WORK/services")"
# Never let the guest delete or rewrite the phone's data through the shared
# installd, vold or keystore2 (patches/guest_storage_guards.py).
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/guest_storage_guards.py" "$WORK/services")"
# Send installd calls with One UI's transaction codes, block the rest
# (patches/guest_installd_abi.py, table from scripts/host-installd-table.sh).
# The host is the One UI of the image's Android version (0.4.66): One UI 9 (Android 17)
# for SDK 37 images, One UI 8.5 (Android 16, host_installd_a16.txt from the A07/A17/A15
# probes; One UI 8.0's differs only in slot 33, createOatDir, which the proxy blocks
# under 8.5's table, and lacks Samsung's 74-78) for SDK 36 ones.
IMAGE_SDK=$("$DEBUGFS" -R "cat /system/build.prop" "$IMG" 2>/dev/null | sed -n 's/^ro.build.version.sdk=//p' | head -n 1)
case "$IMAGE_SDK" in
    37) HOST_INSTALLD="$ROOT/switcher/patches/host_installd.txt" ;;
    36) HOST_INSTALLD="$ROOT/switcher/patches/host_installd_a16.txt" ;;
    *) echo "image SDK ${IMAGE_SDK:-unknown}: no host installd table for it" >&2; exit 1 ;;
esac
echo "installd: the image is SDK $IMAGE_SDK, host table $(basename "$HOST_INSTALLD")"
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/guest_installd_abi.py" "$WORK/services" "$HOST_INSTALLD")"
# No kernel crash from the guest's watchdog (patches/guest_no_sysrq_crash.py).
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/guest_no_sysrq_crash.py" "$WORK/services")"
# The guest never touches the phone's weaver slots, where One UI's lock
# protectors live (patches/guest_no_weaver.py).
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/guest_no_weaver.py" "$WORK/services")"
# Nor removes templates from the phone's fingerprint and face sensors, where
# One UI's enrolments live (patches/guest_no_biometric_cleanup.py).
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/guest_no_biometric_cleanup.py" "$WORK/services")"
# Samsung's host fingerprint HAL is AIDL v3 only. ColorOS's config picks the
# absent HIDL 2.1 adapter and the guest never opens a sensor
# (patches/guest_force_aidl_fingerprint.py).
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/guest_force_aidl_fingerprint.py" "$WORK/services")"
# The phone's gatekeeper (screen lock), FRP partition and apexd stay One UI's;
# guest apps get app ids from 15000 (no keystore namespace shared with One UI's
# apps) and the guest makes no users or profiles (their per-user keys share
# aliases with One UI's). patches/guest_no_gatekeeper.py, guest_pdb_readonly.py,
# guest_no_apex_installs.py, guest_app_id_offset.py, guest_no_new_users.py; the KernelSU
# manager keeps One UI's app id (guest_ksu_manager_appid.py, 0.4.39).
# 0.4.63: the PDB start task survives a failed FRP deactivation (guest_pdb_init_survives.py).
for g in guest_no_gatekeeper guest_pdb_readonly guest_pdb_init_survives guest_no_apex_installs guest_app_id_offset guest_ksu_manager_appid guest_no_new_users; do
    NEW=$(python3 -I "$ROOT/switcher/patches/$g.py" "$WORK/services")
    KEY_DIRS="$KEY_DIRS $NEW"
done
# The guest's own idmap2d instead of One UI's (patches/guest_own_idmap.py).
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/guest_own_idmap.py" "$WORK/services")"
# A WebView zygote that cannot start is logged, not fatal (S24 Ultra, Find X9
# Ultra IN, session 77e7789e: system_server died 60 s into boot;
# patches/guest_webview_zygote_safe.py).
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/guest_webview_zygote_safe.py" "$WORK/services")"
# A native-only service fails to start instead of waiting on One UI's
# zygote_next (S25 Ultra, Pixel 9 Pro XL, app 0.4.25: Chrome's renderer held
# every process start of the session; patches/guest_no_native_services.py).
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/guest_no_native_services.py" "$WORK/services")"
# Samsung's VoLTE app (com.sec.imsservice) keeps android.uid.system in the guest,
# but only from the staged read-only path /system_ext/priv-app/OneOSSecIms
# (guest_prepare.sh, ONEOS_GUEST_SEC_IMS=1): verifySignatures admits that one
# package there despite its Samsung platform signature, and nothing else
# (patches/guest_sec_ims_signature.py, docs/samsung-ims-in-guest.md). Always
# applied; dormant unless such a package is staged at that path.
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/guest_sec_ims_signature.py" "$WORK/services")"
# The wipe paths never delete the phone's secrets: Secretkeeper, the secure
# element, vold's storage and metadata keys (Infinity-X's duress wipe calls
# them directly; patches/guest_no_wipe_secrets.py). Before guest_own_vold.py.
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/guest_no_wipe_secrets.py" "$WORK/services")"
# The guest's StorageManagerService keeps no handle on the phone's own A/B
# updater (patches/guest_no_update_engine.py). oneos_switch.sh stops
# update_engine for the session, and a build whose StorageManagerService
# constructs an UpdateEngine then dies at boot (Nothing OS 5.0, first run);
# a build that has none is left alone (Pixel).
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/guest_no_update_engine.py" "$WORK/services")"
# vivo OriginOS: the face HAL's extension only when it is vivo's, and AOSP's
# AlarmManagerService instead of MediaTek's RTC power-off alarms
# (patches/vivo_guards.py; vivo-services.jar below).
if in_image /system/framework/vivo-services.jar; then
    KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/vivo_guards.py" services "$WORK/services")"
fi
# The guest's own vold as "gvld", with vold_patched above; no guest call left
# that reaches One UI's "vold" (patches/guest_own_vold.py).
if [ "$VOLD_GVLD" = 1 ]; then
    KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/guest_own_vold.py" "$WORK/services")"
fi
# StorageManagerService waits for OPPO's DefragService, which never registers.
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/oplus_wait_for_service.py" "$WORK/services" --only DefragService)"
# ColorOS's sound trigger retried a HAL the phone does not have forever on system_server's
# main thread (A16 5G, A17 5G: Watchdog kill after 60 s); it gives up as AOSP does
# (patches/oplus_soundtrigger_no_hal.py; nothing to change on other images).
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/oplus_soundtrigger_no_hal.py" "$WORK/services")"
# A sound-trigger HAL that refuses a model (Pixel's Now Playing on Samsung's HAL) is not
# rebooted: the reboot took One UI's audio HAL process and the guest's audio down, again
# and again (patches/guest_soundtrigger_no_reboot.py, 0.4.64).
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/guest_soundtrigger_no_reboot.py" "$WORK/services")"
# Pixel's Comfort View as a color matrix, like Night Light (run 43: the switch
# did nothing; patches/comfort_view_bridge.py). Left out, with a warning, on an
# image without ColorDisplayService.setUp, and not run for ColorOS: its
# services.jar has the anchor too, but nothing there writes cv_enabled, so its
# system_server stays as it was.
if in_image /system/framework/oplus-services.jar; then
    echo "Comfort View bridge: ColorOS image, left out"
else
    KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/comfort_view_bridge.py" "$WORK/services" "$ROOT/switcher/patches/OneOSComfortView.smali")"
    # Window blur stays on when the phone is warm (owner, run 45): only the
    # thermal term leaves updateBlurEnabled(); Developer options and battery
    # saver still turn it off (patches/guest_blur_no_thermal.py).
    KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/guest_blur_no_thermal.py" "$WORK/services")"
    echo "Window blur: not turned off by heat (BlurController.updateBlurEnabled)"
fi
# Qualcomm's display additions make a second built-in panel private, and the
# Z Fold's cover becomes display 0 when it folds: no app could use it
# (patches/qti_builtin_display_public.py; nothing in images without them).
KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/qti_builtin_display_public.py" "$WORK/services")"
# A dex the added OneOS classes push past 65536 method references (the Pixel 9
# Pro XL's classes2: 65568) gets them moved to a dex of their own after the
# last one: one jar, one class loader, so they keep their package access.
# Builds that fit are unchanged.
if ! java -jar "$APKTOOL" b -q -o "$WORK/rebuilt.jar" "$WORK/services" 2> "$WORK/apktool.err"; then
    FULL=$(sed -n 's/.*Could not smali folder: \(smali[_a-z0-9]*\).*/\1/p' "$WORK/apktool.err" | head -1)
    if [ -z "$FULL" ] || ! grep -q 'Unsigned short value out of range' "$WORK/apktool.err" ||
       [ -z "$(cd "$WORK/services/$FULL" && find . -name 'OneOS*.smali')" ]; then
        cat "$WORK/apktool.err" >&2
        exit 1
    fi
    LAST=$(ls -d "$WORK"/services/smali_classes* 2>/dev/null | sed 's/.*smali_classes//' | sort -n | tail -1)
    OWN="smali_classes$((${LAST:-1} + 1))"
    (cd "$WORK/services/$FULL" && find . -name 'OneOS*.smali') | while read -r f; do
        mkdir -p "$WORK/services/$OWN/$(dirname "$f")"
        mv "$WORK/services/$FULL/$f" "$WORK/services/$OWN/$f"
        echo "services.jar: $FULL is past 65536 method references, $f moved to $OWN"
    done
    java -jar "$APKTOOL" b -q -o "$WORK/rebuilt.jar" "$WORK/services"
    KEY_DIRS="$KEY_DIRS $OWN"
fi
cp "$WORK/services.jar" "$OUT/services_patched.jar"
for d in $(printf '%s\n' "$DISPLAY_DIR" $KEY_DIRS | sort -u); do
    DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
    rm -rf "$WORK/dex" && mkdir -p "$WORK/dex"
    unzip -q -o "$WORK/rebuilt.jar" "$DEX" -d "$WORK/dex"
    (cd "$WORK/dex" && zip -q -0 "$OUT/services_patched.jar" "$DEX")
    echo "built $OUT/services_patched.jar (replaced $DEX)"
done

# oplus-services.jar: waitForService -> checkService for OPPO-only services
# (patches/oplus_wait_for_service.py). Every dex it touched is replaced.
# Only in ColorOS images; without it guest_prepare.sh needs no second guard jar.
if in_image /system/framework/oplus-services.jar; then
    "$DEBUGFS" -R "dump /system/framework/oplus-services.jar $WORK/oplus-services.jar" "$IMG" 2>/dev/null
    java -jar "$APKTOOL" d -q -f -r -o "$WORK/oplus" "$WORK/oplus-services.jar"
    DIRS=$(python3 -I "$ROOT/switcher/patches/oplus_wait_for_service.py" "$WORK/oplus")
    # QSPM wait in GameGpuControlPanel, ctl.start dumpenvironment and gettpinfo (patches/oplus_boot_hangs.py).
    # (Each patcher in a plain assignment, so set -e stops the build when it fails.)
    NEW=$(python3 -I "$ROOT/switcher/patches/oplus_boot_hangs.py" "$WORK/oplus")
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    # Same storage guards as services.jar (patches/guest_storage_guards.py).
    NEW=$(python3 -I "$ROOT/switcher/patches/guest_storage_guards.py" "$WORK/oplus")
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    # ColorOS waits 3 s for a keystore property the guest never sets
    # (patches/guest_skip_negotiation.py).
    NEW=$(python3 -I "$ROOT/switcher/patches/guest_skip_negotiation.py" "$WORK/oplus")
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    NEW=$(python3 -I "$ROOT/switcher/patches/guest_no_sysrq_crash.py" "$WORK/oplus")
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    NEW=$(python3 -I "$ROOT/switcher/patches/guest_no_wipe_secrets.py" "$WORK/oplus")
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    # With the guest vold as "gvld": OPPO's own "vold" lookup too
    # (OplusStorageManagerFeature, patches/guest_own_vold.py --oplus).
    if [ "$VOLD_GVLD" = 1 ]; then
        NEW=$(python3 -I "$ROOT/switcher/patches/guest_own_vold.py" --oplus "$WORK/oplus")
        DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    fi
    # OPPO's own IInstalld.Stub.asInterface() calls go through services.jar's
    # OneOSInstalldProxy too (patches/guest_installd_abi.py --callers).
    NEW=$(python3 -I "$ROOT/switcher/patches/guest_installd_abi.py" --callers "$WORK/oplus")
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    # Brightness on Samsung's panel (patches/samsung_backlight_curve.py).
    NEW=$(python3 -I "$ROOT/switcher/patches/samsung_backlight_curve.py" "$WORK/oplus" "$ROOT/switcher/patches/OneOSPanelBacklight.smali")
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)

    # OPPO's default runtime grants without CUST_LEVEL_LIST (patches/oplus_default_grants.py).
    NEW=$(python3 -I "$ROOT/switcher/patches/oplus_default_grants.py" "$WORK/oplus")
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    # No charge error warnings from the missing OPPO charger HAL's -1 (patches/oplus_battery_notify.py).
    NEW=$(python3 -I "$ROOT/switcher/patches/oplus_battery_notify.py" "$WORK/oplus")
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    # No FHD+/QHD+ resolution switch without ColorOS's density tables: it made every density 640
    # (patches/oplus_resolution_tables.py).
    NEW=$(python3 -I "$ROOT/switcher/patches/oplus_resolution_tables.py" "$WORK/oplus")
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    # No system_server crash when Do Not Disturb turns on without a notification
    # light (Samsung has none; patches/oplus_zen_light.py).
    NEW=$(python3 -I "$ROOT/switcher/patches/oplus_zen_light.py" "$WORK/oplus")
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    java -jar "$APKTOOL" b -q -o "$WORK/oplus-rebuilt.jar" "$WORK/oplus"
    cp "$WORK/oplus-services.jar" "$OUT/oplus-services_patched.jar"
    for d in $DIRS; do
        DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
        rm -rf "$WORK/odex" && mkdir -p "$WORK/odex"
        unzip -q -o "$WORK/oplus-rebuilt.jar" "$DEX" -d "$WORK/odex"
        (cd "$WORK/odex" && zip -q -0 "$OUT/oplus-services_patched.jar" "$DEX")
        echo "built $OUT/oplus-services_patched.jar (replaced $DEX)"
    done
else
    rm -f "$OUT/oplus-services_patched.jar"
    echo "oplus-services.jar: not in the image, nothing to patch"
fi

# HyperOS: Xiaomi's miui-services.jar runs in the same system_server, with its
# own recovery, factory reset, preinstall and vold paths (patches/miui_guards.py,
# docs/hyperos.md), the storage guards and installd callers like
# oplus-services.jar's, and with "gvld" its two "vold" lookups
# (guest_own_vold.py --miui). apprecovery.proinstaller.jar (also on the system
# server class path) installs apps by itself: its InstallService does nothing
# (miui_guards.py --proinstaller). Only in HyperOS images; guest_prepare.sh
# refuses one without them.
# vivo-services.jar (vivo OriginOS), on system_server's classpath: vivo's
# IOemNetd never reaches One UI's netd, HAL extensions only when vivo's
# (patches/vivo_guards.py), and the storage guards, which drop its two
# AndroidKeyStoreMaintenance.onUserLskfRemoved calls on the shared keystore2.
# Its IVold calls use StorageManagerService's own (the guest's gvld). An image
# with vivo-services.jar starts only with this one bound (guest_prepare.sh).
rm -f "$OUT/vivo-services_patched.jar"
if in_image /system/framework/vivo-services.jar; then
    "$DEBUGFS" -R "dump /system/framework/vivo-services.jar $WORK/vivo-services.jar" "$IMG" 2>/dev/null
    java -jar "$APKTOOL" d -q -f -r -o "$WORK/vivo" "$WORK/vivo-services.jar"
    DIRS=$(python3 -I "$ROOT/switcher/patches/vivo_guards.py" vivo-services "$WORK/vivo")
    NEW=$(python3 -I "$ROOT/switcher/patches/guest_storage_guards.py" "$WORK/vivo")
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    NEW=$(python3 -I "$ROOT/switcher/patches/guest_installd_abi.py" --callers "$WORK/vivo")
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    # vivo's app freezer asks for transport 11, which One UI's connectivity module
    # refuses (second CN run: system_server died); see vivo-service-wifi.jar below.
    NEW=$(python3 -I "$ROOT/switcher/patches/vivo_wifi_connectivity.py" "$WORK/vivo" services)
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    # vivo's vendor HALs without a wait that never ends (vcode: tenth CN run, 542
    # one-second waits in system_server, a lock held meanwhile).
    NEW=$(python3 -I "$ROOT/switcher/patches/vivo_no_wait.py" "$WORK/vivo")
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    java -jar "$APKTOOL" b -q -o "$WORK/vivo-rebuilt.jar" "$WORK/vivo"
    cp "$WORK/vivo-services.jar" "$OUT/vivo-services_patched.jar"
    for d in $DIRS; do
        DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
        rm -rf "$WORK/vdex" && mkdir -p "$WORK/vdex"
        unzip -q -o "$WORK/vivo-rebuilt.jar" "$DEX" -d "$WORK/vdex"
        (cd "$WORK/vdex" && zip -q -0 "$OUT/vivo-services_patched.jar" "$DEX")
        echo "built $OUT/vivo-services_patched.jar (replaced $DEX)"
    done
    rm -rf "$WORK/vivo" "$WORK/vivo-rebuilt.jar" "$WORK/vdex" "$WORK/vivo-services.jar"
fi
# vivo-telephony-common-platform-ex.jar (vivo OriginOS, MediaTek build), loaded
# by telephony-common for the phone process's RIL: MtkRIL waits for MediaTek's
# mtkradioex services before it connects to One UI's radio, and a Samsung vendor
# has none (patches/vivo_telephony.py; seventh run: no SIM, no signal).
rm -f "$OUT/vivo-telephony-common-platform-ex_patched.jar"
VTX_JAR=/system/framework/vivo-telephony-common-platform-ex.jar
if in_image $VTX_JAR; then
    "$DEBUGFS" -R "dump $VTX_JAR $WORK/vtx.jar" "$IMG" 2>/dev/null
    java -jar "$APKTOOL" d -q -f -r -o "$WORK/vtx" "$WORK/vtx.jar"
    DIRS=$(python3 -I "$ROOT/switcher/patches/vivo_telephony.py" "$WORK/vtx")
    java -jar "$APKTOOL" b -q -o "$WORK/vtx-rebuilt.jar" "$WORK/vtx"
    cp "$WORK/vtx.jar" "$OUT/vivo-telephony-common-platform-ex_patched.jar"
    for d in $DIRS; do
        DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
        rm -rf "$WORK/vdex" && mkdir -p "$WORK/vdex"
        unzip -q -o "$WORK/vtx-rebuilt.jar" "$DEX" -d "$WORK/vdex"
        (cd "$WORK/vdex" && zip -q -0 "$OUT/vivo-telephony-common-platform-ex_patched.jar" "$DEX")
        echo "built $OUT/vivo-telephony-common-platform-ex_patched.jar (replaced $DEX)"
    done
    rm -rf "$WORK/vtx" "$WORK/vtx-rebuilt.jar" "$WORK/vdex" "$WORK/vtx.jar"
fi
# framework-adapter.jar (vivo OriginOS, boot class path): About phone's processor
# from the generic CPU nodes, not vivo's /sys/cpu_info (patches/vivo_guards.py
# framework-adapter; seventh run: "Processor null GHz"). Its boot image part is
# already given up with framework_patched.jar.
rm -f "$OUT/framework-adapter_patched.jar"
FA_JAR=/system/framework/framework-adapter.jar
if in_image /system/framework/vivo-services.jar && in_image $FA_JAR; then
    "$DEBUGFS" -R "dump $FA_JAR $WORK/fa.jar" "$IMG" 2>/dev/null
    java -jar "$APKTOOL" d -q -f -r -o "$WORK/fa" "$WORK/fa.jar"
    DIRS=$(python3 -I "$ROOT/switcher/patches/vivo_guards.py" framework-adapter "$WORK/fa")
    java -jar "$APKTOOL" b -q -o "$WORK/fa-rebuilt.jar" "$WORK/fa"
    cp "$WORK/fa.jar" "$OUT/framework-adapter_patched.jar"
    for d in $DIRS; do
        DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
        rm -rf "$WORK/vdex" && mkdir -p "$WORK/vdex"
        unzip -q -o "$WORK/fa-rebuilt.jar" "$DEX" -d "$WORK/vdex"
        (cd "$WORK/vdex" && zip -q -0 "$OUT/framework-adapter_patched.jar" "$DEX")
        echo "built $OUT/framework-adapter_patched.jar (replaced $DEX)"
    done
    rm -rf "$WORK/fa" "$WORK/fa-rebuilt.jar" "$WORK/vdex" "$WORK/fa.jar"
fi

MIUI_JAR=/system/system_ext/framework/miui-services.jar
PRO_JAR=/system/system_ext/framework/apprecovery.proinstaller.jar
if in_image $MIUI_JAR; then
    "$DEBUGFS" -R "dump $MIUI_JAR $WORK/miui-services.jar" "$IMG" 2>/dev/null
    java -jar "$APKTOOL" d -q -f -r -o "$WORK/miui" "$WORK/miui-services.jar"
    DIRS=$(python3 -I "$ROOT/switcher/patches/miui_guards.py" "$WORK/miui")
    NEW=$(python3 -I "$ROOT/switcher/patches/guest_storage_guards.py" "$WORK/miui")
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    NEW=$(python3 -I "$ROOT/switcher/patches/guest_installd_abi.py" --callers "$WORK/miui")
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    if [ "$VOLD_GVLD" = 1 ]; then
        NEW=$(python3 -I "$ROOT/switcher/patches/guest_own_vold.py" --miui "$WORK/miui")
        DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    fi
    # HAL extension casts (patches/hyperos_hal_ext.py): the vibrator's.
    NEW=$(python3 -I "$ROOT/switcher/patches/hyperos_hal_ext.py" --expect 1 "$WORK/miui" HalExtServices)
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    java -jar "$APKTOOL" b -q -o "$WORK/miui-rebuilt.jar" "$WORK/miui"
    cp "$WORK/miui-services.jar" "$OUT/miui-services_patched.jar"
    for d in $DIRS; do
        DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
        rm -rf "$WORK/mdex" && mkdir -p "$WORK/mdex"
        unzip -q -o "$WORK/miui-rebuilt.jar" "$DEX" -d "$WORK/mdex"
        (cd "$WORK/mdex" && zip -q -0 "$OUT/miui-services_patched.jar" "$DEX")
        echo "built $OUT/miui-services_patched.jar (replaced $DEX)"
    done
    in_image $PRO_JAR || { echo "ERROR: $MIUI_JAR without $PRO_JAR: another HyperOS layout, not guarded" >&2; exit 1; }
    "$DEBUGFS" -R "dump $PRO_JAR $WORK/proinstaller.jar" "$IMG" 2>/dev/null
    java -jar "$APKTOOL" d -q -f -r -o "$WORK/pro" "$WORK/proinstaller.jar"
    DIRS=$(python3 -I "$ROOT/switcher/patches/miui_guards.py" --proinstaller "$WORK/pro")
    java -jar "$APKTOOL" b -q -o "$WORK/pro-rebuilt.jar" "$WORK/pro"
    cp "$WORK/proinstaller.jar" "$OUT/apprecovery.proinstaller_patched.jar"
    for d in $DIRS; do
        DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
        rm -rf "$WORK/mdex" && mkdir -p "$WORK/mdex"
        unzip -q -o "$WORK/pro-rebuilt.jar" "$DEX" -d "$WORK/mdex"
        (cd "$WORK/mdex" && zip -q -0 "$OUT/apprecovery.proinstaller_patched.jar" "$DEX")
        echo "built $OUT/apprecovery.proinstaller_patched.jar (replaced $DEX)"
    done
    # miui-wifi-service.jar (MiuiWifiService in system_server): its casts of
    # the Wi-Fi HALs' extensions (supplicant, hardware, hostapd) to Xiaomi
    # interfaces, which One UI's HALs answer with Samsung's
    # (patches/hyperos_hal_ext.py; the third HyperOS run died in
    # ISupplicantXm.registerCallback).
    WIFI_JAR=/system/system_ext/framework/miui-wifi-service.jar
    in_image $WIFI_JAR || { echo "ERROR: $MIUI_JAR without $WIFI_JAR" >&2; exit 1; }
    "$DEBUGFS" -R "dump $WIFI_JAR $WORK/miui-wifi-service.jar" "$IMG" 2>/dev/null
    java -jar "$APKTOOL" d -q -f -r -o "$WORK/mwifi" "$WORK/miui-wifi-service.jar"
    DIRS=$(python3 -I "$ROOT/switcher/patches/hyperos_hal_ext.py" --expect 5 "$WORK/mwifi" HalExtWifi)
    java -jar "$APKTOOL" b -q -o "$WORK/mwifi-rebuilt.jar" "$WORK/mwifi"
    cp "$WORK/miui-wifi-service.jar" "$OUT/miui-wifi-service_patched.jar"
    for d in $DIRS; do
        DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
        rm -rf "$WORK/mdex" && mkdir -p "$WORK/mdex"
        unzip -q -o "$WORK/mwifi-rebuilt.jar" "$DEX" -d "$WORK/mdex"
        (cd "$WORK/mdex" && zip -q -0 "$OUT/miui-wifi-service_patched.jar" "$DEX")
        echo "built $OUT/miui-wifi-service_patched.jar (replaced $DEX)"
    done
    rm -rf "$WORK/mwifi" "$WORK/mwifi-rebuilt.jar"
    # miui-telephony-common.jar (com.android.phone): Xiaomi's IMS controller
    # without an IMS phone (patches/hyperos_telephony.py; the fourth HyperOS
    # run's phone process died on every service state poll).
    TEL_JAR=/system/system_ext/framework/miui-telephony-common.jar
    in_image $TEL_JAR || { echo "ERROR: $MIUI_JAR without $TEL_JAR" >&2; exit 1; }
    "$DEBUGFS" -R "dump $TEL_JAR $WORK/miui-telephony-common.jar" "$IMG" 2>/dev/null
    java -jar "$APKTOOL" d -q -f -r -o "$WORK/mtel" "$WORK/miui-telephony-common.jar"
    DIRS=$(python3 -I "$ROOT/switcher/patches/hyperos_telephony.py" "$WORK/mtel")
    java -jar "$APKTOOL" b -q -o "$WORK/mtel-rebuilt.jar" "$WORK/mtel"
    cp "$WORK/miui-telephony-common.jar" "$OUT/miui-telephony-common_patched.jar"
    for d in $DIRS; do
        DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
        rm -rf "$WORK/mdex" && mkdir -p "$WORK/mdex"
        unzip -q -o "$WORK/mtel-rebuilt.jar" "$DEX" -d "$WORK/mdex"
        (cd "$WORK/mdex" && zip -q -0 "$OUT/miui-telephony-common_patched.jar" "$DEX")
        echo "built $OUT/miui-telephony-common_patched.jar (replaced $DEX)"
    done
    rm -rf "$WORK/mtel" "$WORK/mtel-rebuilt.jar"
    # xiaomi-opt-telephony.jar (com.android.phone): VendorRIL takes a HIDL radio instead of waiting
    # for Xiaomi's AIDL rild (patches/hyperos_hidl_radio.py; the MediaTek A phones had no SIM, 0.4.67).
    XOT_JAR=/system/system_ext/framework/xiaomi-opt-telephony.jar
    if in_image $XOT_JAR; then
        "$DEBUGFS" -R "dump $XOT_JAR $WORK/xiaomi-opt-telephony.jar" "$IMG" 2>/dev/null
        java -jar "$APKTOOL" d -q -f -r -o "$WORK/xot" "$WORK/xiaomi-opt-telephony.jar"
        DIRS=$(python3 -I "$ROOT/switcher/patches/hyperos_hidl_radio.py" "$WORK/xot")
        java -jar "$APKTOOL" b -q -o "$WORK/xot-rebuilt.jar" "$WORK/xot"
        cp "$WORK/xiaomi-opt-telephony.jar" "$OUT/xiaomi-opt-telephony_patched.jar"
        for d in $DIRS; do
            DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
            rm -rf "$WORK/mdex" && mkdir -p "$WORK/mdex"
            unzip -q -o "$WORK/xot-rebuilt.jar" "$DEX" -d "$WORK/mdex"
            (cd "$WORK/mdex" && zip -q -0 "$OUT/xiaomi-opt-telephony_patched.jar" "$DEX")
            echo "built $OUT/xiaomi-opt-telephony_patched.jar (replaced $DEX)"
        done
        rm -rf "$WORK/xot" "$WORK/xot-rebuilt.jar"
    else
        echo "xiaomi-opt-telephony.jar: not in this image, not built"
    fi
    # libaudiohal@aidl.so: HyperOS's audioserver waited for an audio HAL
    # adapter vendor extension that only One UI's own audioserver serves, and
    # a session stops it (patches/hyperos_audio_ext.py, sixth run: no sound).
    AH_LIB=/system/lib64/libaudiohal@aidl.so
    in_image $AH_LIB || { echo "ERROR: $MIUI_JAR without $AH_LIB" >&2; exit 1; }
    "$DEBUGFS" -R "dump $AH_LIB $WORK/libaudiohal_aidl.so" "$IMG" 2>/dev/null
    python3 -I "$ROOT/switcher/patches/hyperos_audio_ext.py" "$WORK/libaudiohal_aidl.so" "$OUT/libaudiohal_aidl_patched.so"
    rm -f "$WORK/libaudiohal_aidl.so"
    # socket_exec (switcher/native): guest_start.sh starts hyos_spawner with
    # it, the service that runs HyperOS's rust packages (the launcher).
    cp -f "$ROOT/switcher/native/bin/socket_exec" "$OUT/socket_exec"
    # framework.jar: Xiaomi's CameraStatus parcel back to AOSP's fields, as One
    # UI's cameraserver writes them (patches/hyperos_framework.py; the first
    # HyperOS run died in BiometricService on a null CameraStatus).
    FW_JAR=/system/framework/framework.jar
    in_image $FW_JAR || { echo "ERROR: $MIUI_JAR without $FW_JAR" >&2; exit 1; }
    # The camera transaction codes step further down builds on this jar (HYPEROS_FW).
    HYPEROS_FW=1
    "$DEBUGFS" -R "dump $FW_JAR $WORK/framework.jar" "$IMG" 2>/dev/null
    java -jar "$APKTOOL" d -q -f -r -o "$WORK/fw" "$WORK/framework.jar"
    DIRS=$(python3 -I "$ROOT/switcher/patches/hyperos_framework.py" "$WORK/fw")
    java -jar "$APKTOOL" b -q -o "$WORK/fw-rebuilt.jar" "$WORK/fw"
    cp "$WORK/framework.jar" "$OUT/framework_patched.jar"
    for d in $DIRS; do
        DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
        rm -rf "$WORK/mdex" && mkdir -p "$WORK/mdex"
        unzip -q -o "$WORK/fw-rebuilt.jar" "$DEX" -d "$WORK/mdex"
        (cd "$WORK/mdex" && zip -q -0 "$OUT/framework_patched.jar" "$DEX")
        echo "built $OUT/framework_patched.jar (replaced $DEX)"
    done
    rm -rf "$WORK/fw" "$WORK/fw-rebuilt.jar" "$WORK/framework.jar"
else
    rm -f "$OUT/miui-services_patched.jar" "$OUT/apprecovery.proinstaller_patched.jar" "$OUT/framework_patched.jar" "$OUT/miui-wifi-service_patched.jar" \
          "$OUT/miui-telephony-common_patched.jar" "$OUT/xiaomi-opt-telephony_patched.jar" "$OUT/socket_exec" \
          "$OUT/libaudiohal_aidl_patched.so"
    echo "miui-services.jar: not in the image, nothing to patch"
fi


# product/framework/ims-ext-common.jar: QtiImsExtConnector retries a failed
# bind every 60 s instead of every 500 ms (patches/qti_ims_ext_backoff.py).
# Not a guard jar: guest_prepare.sh binds it only when it is there.
if in_image /system/product/framework/ims-ext-common.jar; then
    "$DEBUGFS" -R "dump /system/product/framework/ims-ext-common.jar $WORK/ims-ext-common.jar" "$IMG" 2>/dev/null
    java -jar "$APKTOOL" d -q -f -r -o "$WORK/imsext" "$WORK/ims-ext-common.jar"
    DIRS=$(python3 -I "$ROOT/switcher/patches/qti_ims_ext_backoff.py" "$WORK/imsext")
    java -jar "$APKTOOL" b -q -o "$WORK/imsext-rebuilt.jar" "$WORK/imsext"
    cp "$WORK/ims-ext-common.jar" "$OUT/ims-ext-common_patched.jar"
    for d in $DIRS; do
        DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
        rm -rf "$WORK/idex" && mkdir -p "$WORK/idex"
        unzip -q -o "$WORK/imsext-rebuilt.jar" "$DEX" -d "$WORK/idex"
        (cd "$WORK/idex" && zip -q -0 "$OUT/ims-ext-common_patched.jar" "$DEX")
        echo "built $OUT/ims-ext-common_patched.jar (replaced $DEX)"
    done
else
    rm -f "$OUT/ims-ext-common_patched.jar"
    echo "ims-ext-common.jar: not in the image, nothing to patch"
fi

# Nothing OS loads its telephony extension in a class loader of its own holding
# exactly one jar (telephony-common.jar's NtTelephonyFactory:
# new PathClassLoader("/system_ext/framework/nt-telephony-common.jar", parent)),
# and NrModeUpdaterQc$1 in that jar extends com.qti.extphone.ExtPhoneCallbackBase,
# which lives in extphonelib.jar and is not in that loader. So com.android.phone
# died with NoClassDefFoundError in PhoneFactory.makeDefaultPhone at every start
# ("crashed too many times, killing"): no RILJ, no ServiceState, and the lock
# screen read "Emergency calls only", though rild itself was up and had
# registered IRadioSim and IRadioNetwork for both slots (first Nothing run,
# 2026-10-31).
#
# extphonelib's dex is put into the jar that loader does read, as classes2.dex:
# a PathClassLoader takes classes.dex, classes2.dex, ... from each path it is
# given, so the superclass resolves inside the same loader. The alternative was
# to add a second path to that string in telephony-common.jar, which is on the
# boot class path; this leaves it alone. The dex is copied, not rebuilt, so
# nothing in either jar changes meaning. Only for an image that has both.
in_image_either() {
    for p in "/system_ext/framework/$1" "/system/system_ext/framework/$1"; do
        in_image "$p" && { echo "$p"; return 0; }
    done
    return 1
}
NT_TC=$(in_image_either nt-telephony-common.jar || true)
# The jars it needs that the loader's parent does not already cover, from a
# scan of all 54 references its 7169 classes make outside the boot class path:
#   extphonelib            ExtPhoneCallbackBase, NrModeUpdaterQc$1's superclass
#   qcrilhook             OemHookCallback
#   qti-telephony-common  QtiRilInterface, which RrcIndicationEnablerQc wants
#   qti-telephony-utils, qti-telephony-hidl-wrapper   qcrilhook's own declared
#                          dependencies
# Everything else resolves from the boot class path (framework.jar,
# telephony-common.jar, nt-framework.jar, nt-telephony-interface.jar):
# com/android/{ims,telephony,server/net}, com/nothing/{experience,kafka,
# onlineconfig,thermal,telephony,internal/telephony/ext} and com/sysaac/haptic.
# Each missing one only showed itself when the one before it was in, a run at a
# time, so the list is taken from the scan now rather than from the next crash.
NT_ADD=""
for j in extphonelib.jar qcrilhook.jar qti-telephony-common.jar \
         qti-telephony-utils.jar qti-telephony-hidl-wrapper.jar; do
    p=$(in_image_either "$j" || true)
    [ -n "$p" ] && NT_ADD="$NT_ADD $p"
done
rm -f "$OUT/nt-telephony-common_patched.jar"
if [ -n "$NT_TC" ] && [ -n "$NT_ADD" ]; then
    "$DEBUGFS" -R "dump $NT_TC $WORK/nt_base.jar" "$IMG" 2>/dev/null
    NT_FILES=""
    mkdir -p "$WORK/ntadd"
    for p in $NT_ADD; do
        b=$(basename "$p")
        "$DEBUGFS" -R "dump $p $WORK/ntadd/$b" "$IMG" 2>/dev/null
        NT_FILES="$NT_FILES $WORK/ntadd/$b"
    done
    # shellcheck disable=SC2086
    python3 -I - "$OUT/nt-telephony-common_patched.jar" "$WORK/nt_base.jar" $NT_FILES <<'PYEOF'
import os, sys, zipfile
out, src = sys.argv[1:3]
adds = sys.argv[3:]
zi = zipfile.ZipFile(src)
have = [e for e in zi.namelist() if e.endswith(".dex")]
if have != ["classes.dex"]:
    sys.exit("nt-telephony-common.jar has %s, not one classes.dex; not merged" % have)
need = {b"com/qti/extphone/ExtPhoneCallbackBase", b"com/qualcomm/qcrilhook/OemHookCallback",
        b"com/qualcomm/qti/internal/telephony/QtiRilInterface"}
seen, dexes = set(), []
for a in adds:
    za = zipfile.ZipFile(a)
    ad = [e for e in za.namelist() if e.endswith(".dex")]
    if ad != ["classes.dex"]:
        sys.exit("%s has %s, not one classes.dex; not merged" % (os.path.basename(a), ad))
    d = za.read("classes.dex")
    dexes.append((os.path.basename(a), d))
    seen |= {c for c in need if c in d}
missing = need - seen
if missing:
    sys.exit("none of the added jars has %s; not merged" % b", ".join(sorted(missing)).decode())
with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as zo:
    for e in zi.infolist():
        zo.writestr(e, zi.read(e.filename))
    for i, (name, d) in enumerate(dexes, start=2):
        zo.writestr("classes%d.dex" % i, d)
print("built %s (its classes.dex, plus %s)" % (
    out, ", ".join("%s as classes%d.dex" % (n, i) for i, (n, _) in enumerate(dexes, start=2))))
PYEOF
elif [ -n "$NT_TC" ]; then
    echo "nt-telephony-common.jar: none of the jars it needs are in the image, left as it is"
else
    echo "nt-telephony-common.jar: not in the image, nothing to merge"
fi


# oplus-telephony-common.jar (system_ext, not on the boot class path, so the
# boot image stays valid): poll the signal strength every 20 s. Samsung's RIL
# sent the guest no currentSignalStrength indication in all of run 34 and AOSP
# polls only for opportunistic subscriptions, so both SIMs showed no bars
# (patches/guest_signal_poll.py). ONEOS_GUEST_SIGNAL_POLL=0 on the phone keeps
# ColorOS's jar (guest_prepare.sh).
if in_image /system/system_ext/framework/oplus-telephony-common.jar; then
    "$DEBUGFS" -R "dump /system/system_ext/framework/oplus-telephony-common.jar $WORK/oplus-telephony-common.jar" "$IMG" 2>/dev/null
    java -jar "$APKTOOL" d -q -f -r -o "$WORK/otc" "$WORK/oplus-telephony-common.jar"
    NEW=$(python3 -I "$ROOT/switcher/patches/guest_signal_poll.py" "$WORK/otc" "$ROOT/switcher/patches/OneOSSignalPoll.smali")
    java -jar "$APKTOOL" b -q -o "$WORK/otc-rebuilt.jar" "$WORK/otc"
    cp "$WORK/oplus-telephony-common.jar" "$OUT/oplus-telephony-common_patched.jar"
    for d in $NEW; do
        DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
        rm -rf "$WORK/tdex" && mkdir -p "$WORK/tdex"
        unzip -q -o "$WORK/otc-rebuilt.jar" "$DEX" -d "$WORK/tdex"
        (cd "$WORK/tdex" && zip -q -0 "$OUT/oplus-telephony-common_patched.jar" "$DEX")
        echo "built $OUT/oplus-telephony-common_patched.jar (replaced $DEX)"
    done
else
    rm -f "$OUT/oplus-telephony-common_patched.jar"
    echo "oplus-telephony-common.jar: not in the image, nothing to patch"
fi

# Signal bars in any other AOSP-based guest (run 43, Pixel 17): the same missing
# indication as ColorOS's run 34 (both SIMs at level 0 all session; Pixel's
# stacked dual-SIM icon at level 0 even looked like a row of "!"), but no
# OplusSignalSmooth to hook. TeleService's own TelephonyComponentFactory
# injection loads oneos-telephony.jar for the one component
# SignalStrengthController: OneOSTelephonyComponentFactory returns the image's
# controller and starts OneOSSignalPoll on it (patches/OneOSSignalPollAosp.smali,
# GET_SIGNAL_STRENGTH every 20 s with the screen on). The static RRO
# OneOSPhoneInjection.apk (switcher/overlays/phone_injection) names it in
# TeleService's xml/telephony_injection. No Google dex changes: telephony-common.jar
# is on the boot class path and in the boot image. guest_prepare.sh puts the jar
# in a read-only overlay layer on the guest's system_ext and the RRO in its
# /oem/overlay, only on the files oneos-telephony.sha256 names
# (ONEOS_GUEST_SIGNAL_POLL=0 leaves it out). Built only when (a) the image has
# telephony-common.jar and TeleService.apk, (b) is not ColorOS
# (oplus-telephony-common_patched.jar polls there), (c) TeleService's injection
# config is empty, (d) TeleService declares no overlayable resources (an /oem
# overlay may then override any), (e) no RRO in the image overrides that config
# (9 target com.android.phone in the Pixel image, TrebleDroid's among them), and
# (f) patches/aosp_signal_poll_check.py finds every class, member and message
# the jar relies on as expected: there is no ART verifier here, and
# check-dex.py below is not one.
INJ_TC=/system/framework/telephony-common.jar
INJ_TS=/system/priv-app/TeleService/TeleService.apk
INJ_RRO="$ROOT/switcher/overlays/phone_injection"
rm -f "$OUT/oneos-telephony.jar" "$OUT/oneos-telephony.sha256" "$OUT/OneOSPhoneInjection.apk"
INJ_WHY=""
if in_image /system/system_ext/framework/oplus-telephony-common.jar; then
    INJ_WHY="ColorOS image: oplus-telephony-common_patched.jar polls instead"
elif ! in_image "$INJ_TC" || ! in_image "$INJ_TS"; then
    INJ_WHY="no $INJ_TC or $INJ_TS in the image"
else
    "$DEBUGFS" -R "dump $INJ_TS $WORK/TeleService.apk" "$IMG" 2>/dev/null
    "$DEBUGFS" -R "dump $INJ_TC $WORK/telephony-common.jar" "$IMG" 2>/dev/null
    INJ_XML=$("$BT/aapt2" dump resources "$WORK/TeleService.apk" 2>/dev/null |
        grep -A1 ' xml/telephony_injection$' | sed -n 's/.*(file) \([^ ]*\) type=XML.*/\1/p' | head -1)
    if [ -z "$INJ_XML" ]; then
        INJ_WHY="TeleService.apk has no xml/telephony_injection"
    elif ! "$BT/aapt2" dump xmltree --file "$INJ_XML" "$WORK/TeleService.apk" > "$WORK/inj_xml.txt" 2>/dev/null ||
         ! grep -Eq '^ *A: jar=""( \(Raw: ""\))?$' "$WORK/inj_xml.txt" ||
         ! grep -Eq '^ *A: package=""( \(Raw: ""\))?$' "$WORK/inj_xml.txt"; then
        INJ_WHY="TeleService.apk's $INJ_XML is not empty:$(grep -E '^ *A: (jar|package)=' "$WORK/inj_xml.txt" | tr -s ' \n' ' ')"
    elif [ -n "$("$BT/aapt2" dump overlayable "$WORK/TeleService.apk" 2>/dev/null | head -n 3)" ]; then
        INJ_WHY="TeleService.apk declares overlayable resources"
    else
        INJ_PHONE_RROS=0
        INJ_OVERRIDES=""
        for d in /system/product/overlay /system/overlay /system/system_ext/overlay; do
            in_image "$d" || continue
            rm -rf "$WORK/ovl" && mkdir -p "$WORK/ovl"
            "$DEBUGFS" -R "rdump $d $WORK/ovl" "$IMG" 2>/dev/null || true
            find "$WORK/ovl" -type f -name '*.apk' > "$WORK/ovl.txt"
            while read -r a; do
                "$BT/aapt2" dump badging "$a" 2>/dev/null | grep -q "targetPackage='com.android.phone'" || continue
                INJ_PHONE_RROS=$((INJ_PHONE_RROS + 1))
                if "$BT/aapt2" dump resources "$a" 2>/dev/null | grep -q ' xml/telephony_injection$'; then
                    INJ_OVERRIDES="$INJ_OVERRIDES${INJ_OVERRIDES:+, }$d/${a#"$WORK"/ovl/*/}"
                fi
            done < "$WORK/ovl.txt"
        done
        rm -rf "$WORK/ovl" "$WORK/ovl.txt"
        echo "signal poll injection: $INJ_PHONE_RROS RRO(s) in the image target com.android.phone"
        # An image RRO that sets xml/telephony_injection itself (Nothing OS 5.0:
        # product/overlay/TelephonyResCommon_Sys.apk, Qualcomm's factory) used to
        # rule the poll out. Run 10 showed the guest's static overlay order:
        # system_ext < product < vendor < oem, so ours in /oem (guest_prepare.sh)
        # comes last and wins; from system_ext it lost, and Qualcomm's factory,
        # loading now that the read-only layer made its jars "protected",
        # crash-looped com.android.phone (org.codeaurora.ims is not on its class
        # path). That order only holds without an overlay ordering file, so an
        # image with one is still left out.
        if [ -n "$INJ_OVERRIDES" ]; then
            for c in /system/overlay/config/config.xml /system/product/overlay/config/config.xml \
                     /product/overlay/config/config.xml /system/system_ext/overlay/config/config.xml \
                     /system_ext/overlay/config/config.xml /system/etc/overlay/config.xml; do
                in_image "$c" && INJ_WHY="$INJ_WHY${INJ_WHY:+, }$INJ_OVERRIDES overrides xml/telephony_injection and $c sets the overlay order"
            done
            [ -n "$INJ_WHY" ] || echo "signal poll injection: $INJ_OVERRIDES overrides xml/telephony_injection; ours goes in /oem, which comes after it"
        fi
        if [ -z "$INJ_WHY" ]; then
            # Another image's jar that apktool cannot read only leaves this out,
            # like every other reason here: not a failed build.
            if ! java -jar "$APKTOOL" d -q -f -r -o "$WORK/tc" "$WORK/telephony-common.jar"; then
                INJ_WHY="apktool could not decode telephony-common.jar"
            elif INJ_CHECK=$(python3 -I "$ROOT/switcher/patches/aosp_signal_poll_check.py" "$WORK/tc" 2>&1); then
                echo "$INJ_CHECK"
            else
                INJ_WHY="patches/aosp_signal_poll_check.py: $INJ_CHECK"
            fi
            rm -rf "$WORK/tc"
        fi
    fi
fi
if [ -n "$INJ_WHY" ]; then
    echo "signal poll injection: not built ($INJ_WHY)"
else
    mkdir -p "$WORK/inj/smali/oneos/telephony"
    cp "$ROOT/switcher/patches/OneOSTelephonyComponentFactory.smali" "$WORK/inj/smali/oneos/telephony/"
    cp "$ROOT/switcher/patches/OneOSSignalPollAosp.smali" "$WORK/inj/smali/oneos/telephony/OneOSSignalPoll.smali"
    printf '%s\n' "version: 3.0.3" "apkFileName: oneos-telephony.jar" "sdkInfo:" "  minSdkVersion: 29" \
        "doNotCompress:" "- dex" > "$WORK/inj/apktool.yml"
    java -jar "$APKTOOL" b -q -o "$OUT/oneos-telephony.jar" "$WORK/inj"
    # The files the jar was checked against, as paths in the guest's root:
    # guest_prepare.sh enables the injection only when the image has these.
    for f in "$INJ_TC" "$INJ_TS"; do
        echo "$(sha256sum < "$WORK/$(basename "$f")" | cut -d' ' -f1) ${f#/}"
    done > "$OUT/oneos-telephony.sha256"
    "$BT/aapt2" compile --dir "$INJ_RRO/res" -o "$WORK/inj_rro.zip"
    "$BT/aapt2" link -o "$WORK/inj_rro.apk" -I "$AJ" --manifest "$INJ_RRO/AndroidManifest.xml" \
        --min-sdk-version 35 --target-sdk-version 37 "$WORK/inj_rro.zip"
    # TeleService reads the component name verbatim: one text node, no whitespace.
    "$BT/aapt2" dump xmltree --file res/xml/telephony_injection.xml "$WORK/inj_rro.apk" > "$WORK/inj_rro_xml.txt"
    if ! grep -q "^ *T: 'com.android.internal.telephony.SignalStrengthController'\$" "$WORK/inj_rro_xml.txt" ||
       ! grep -Eq '^ *A: jar="/system_ext/framework/oneos-telephony\.jar"( \(Raw: .*\))?$' "$WORK/inj_rro_xml.txt" ||
       ! grep -Eq '^ *A: package="oneos\.telephony\.OneOSTelephonyComponentFactory"( \(Raw: .*\))?$' "$WORK/inj_rro_xml.txt"; then
        echo "phone_injection overlay: unexpected telephony_injection.xml:" >&2
        cat "$WORK/inj_rro_xml.txt" >&2
        exit 1
    fi
    "$BT/zipalign" -p -f 4 "$WORK/inj_rro.apk" "$WORK/inj_rro-aligned.apk"
    "$BT/apksigner" sign --ks "${KEYSTORE:-$HOME/.android/debug.keystore}" \
        --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android \
        --out "$OUT/OneOSPhoneInjection.apk" "$WORK/inj_rro-aligned.apk"
    rm -f "$OUT/OneOSPhoneInjection.apk.idsig"
    echo "built $OUT/oneos-telephony.jar, oneos-telephony.sha256 and OneOSPhoneInjection.apk (signal poll through TeleService's TelephonyComponentFactory injection)"
fi
rm -rf "$WORK/inj" "$WORK/TeleService.apk" "$WORK/telephony-common.jar"

# A Pixel (AOSP) or ColorOS guest's camera calls with One UI's transaction codes
# (patches/pixel_camera_abi.py and pixel_camera_native.py, docs/pixel-guest.md
# "What differs"): the image's framework.jar as framework_patched.jar and its
# native client libraries as libcamera_client_patched.so and
# libcameracompatbilityinfo_patched.so (the legacy camera API and the NDK ride
# on those). guest_prepare.sh binds them and guards.txt pins them. ColorOS's
# ICameraService has Oplus methods and its own numbering (21-28), the same
# treatment as the Pixels'. scripts/patch-framework-camera.sh and
# patch-camera-native.sh do the same for a set whose image is no longer on the
# server, from files pulled from the phone.
# HyperOS (0.4.31): on top of its own framework_patched.jar (hyperos_framework.py's
# CameraStatus, made above in this run), so the set carries both.
if [ "${HYPEROS_FW:-0}" = 1 ] && [ -f "$OUT/framework_patched.jar" ]; then
    cp "$OUT/framework_patched.jar" "$WORK/framework-cam.jar"
fi
rm -f "$OUT/framework_patched.jar" "$OUT/libcamera_client_patched.so" "$OUT/libcameracompatbilityinfo_patched.so"
# ONEOS_NO_CAMERA_ABI=1: no camera bridge in this set (0.4.66, the Android 16 OxygenOS set for One UI 8
# phones: the host tables here are One UI 9's; One UI 8's camera numbering is not on the server yet).
# The guest's camera then does not work; everything else is built as usual.
if [ "${ONEOS_NO_CAMERA_ABI:-0}" = 1 ]; then
    echo "camera bridge: left out (ONEOS_NO_CAMERA_ABI=1)"
    rm -f "$WORK/framework-cam.jar"
elif in_image /system/framework/framework.jar; then
    [ -f "$WORK/framework-cam.jar" ] || "$DEBUGFS" -R "dump /system/framework/framework.jar $WORK/framework-cam.jar" "$IMG" 2>/dev/null
    "$ROOT/scripts/patch-framework-camera.sh" "$WORK/framework-cam.jar" "$OUT"
    rm -f "$WORK/framework-cam.jar"
fi
if [ "${ONEOS_NO_CAMERA_ABI:-0}" != 1 ] && in_image /system/lib64/libcamera_client.so && in_image /system/lib64/libcameracompatbilityinfo.so; then
    "$DEBUGFS" -R "dump /system/lib64/libcamera_client.so $WORK/libcamera_client.so" "$IMG" 2>/dev/null
    "$DEBUGFS" -R "dump /system/lib64/libcameracompatbilityinfo.so $WORK/libcameracompatbilityinfo.so" "$IMG" 2>/dev/null
    "$ROOT/scripts/patch-camera-native.sh" "$WORK/libcamera_client.so" "$WORK/libcameracompatbilityinfo.so" "$OUT"
    rm -f "$WORK/libcamera_client.so" "$WORK/libcameracompatbilityinfo.so"
fi

# telephony-common.jar: the SMS service centre as an international number
# (patches/guest_smsc_international.py, 0.4.39). Samsung's radio answers
# getSmscAddress as "972...",145; AOSP kept the digits and dropped the type, so
# the guest's SMS named an unknown-type service centre (over IMS: SIP 404).
# And (patches/guest_sms_invalid_response.py, 0.4.58): Samsung's radio HAL
# answers every SEND_SMS without a result payload, so a text the modem sent
# came back as error 66 (INVALID_RESPONSE) and showed as not sent; 66 now
# counts as sent (a failed send keeps its own error).
# telephony-common.jar is on the boot class path: built only next to a
# framework_patched.jar (that set's boot image is not used already).
rm -f "$OUT/telephony-common_patched.jar"
if [ -f "$OUT/framework_patched.jar" ] && in_image /system/framework/telephony-common.jar; then
    "$DEBUGFS" -R "dump /system/framework/telephony-common.jar $WORK/telephony-common.jar" "$IMG" 2>/dev/null
    "$ROOT/scripts/patch-built-jar.sh" "$WORK/telephony-common.jar" "$ROOT/switcher/patches/guest_smsc_international.py" "$WORK/telephony-common_smsc.jar"
    "$ROOT/scripts/patch-built-jar.sh" "$WORK/telephony-common_smsc.jar" "$ROOT/switcher/patches/guest_sms_invalid_response.py" "$OUT/telephony-common_patched.jar"
    rm -f "$WORK/telephony-common.jar" "$WORK/telephony-common_smsc.jar"
fi

# ART rejects a whole class for an empty try range, which a patcher leaves when
# it drops the only call inside a try block (run 26: Installer, system_server
# died at boot). Fail the build instead.
JARS=""
for j in services_patched.jar oplus-services_patched.jar ims-ext-common_patched.jar oplus-telephony-common_patched.jar \
         oneos-telephony.jar miui-services_patched.jar apprecovery.proinstaller_patched.jar framework_patched.jar \
         miui-wifi-service_patched.jar miui-telephony-common_patched.jar telephony-common_patched.jar vivo-services_patched.jar \
         vivo-telephony-common-platform-ex_patched.jar framework-adapter_patched.jar; do
    [ -f "$OUT/$j" ] && JARS="$JARS $OUT/$j"
done
python3 -I "$ROOT/scripts/check-dex.py" $JARS

# The phone refuses jars that were not built with the guards above
# (guest_prepare.sh checks these hashes, and needs oplus-services_patched.jar
# whenever the image has oplus-services.jar, miui-services_patched.jar and
# apprecovery.proinstaller_patched.jar whenever it has miui-services.jar). vold_patched and
# service.incremental_patched.so are listed with the services_patched.jar that
# looks up "gvld": guest_prepare.sh binds all three or none of them.
{
    echo "# framework overlays built by scripts/make-overlays.sh with the storage, installd, power, sysrq, weaver, biometric, gatekeeper, pdb, apexd, appid15000, nousers, nativeservices, wipesecrets and ksuappid guards, and the secims carve-out (com.sec.imsservice kept in android.uid.system from /system_ext/priv-app/OneOSSecIms only)"
    [ "$VOLD_GVLD" = 1 ] && echo "# guest vold name: gvld (vold_patched, service.incremental_patched.so and services_patched.jar)"
    # HyperOS images (miui-services_patched.jar) and Pixel images list their
    # files in the order and with the notes each set was built with.
    if [ -f "$OUT/miui-services_patched.jar" ]; then
        echo "# HyperOS: miui-services_patched.jar and apprecovery.proinstaller_patched.jar (patches/miui_guards.py)"
        [ -f "$OUT/framework_patched.jar" ] && echo "# HyperOS: framework_patched.jar (patches/hyperos_framework.py, CameraStatus as One UI's cameraserver writes it; 0.4.31: and One UI's camera transaction codes, patches/pixel_camera_abi.py)"
        [ -f "$OUT/miui-wifi-service_patched.jar" ] && echo "# HyperOS: miui-wifi-service_patched.jar (patches/hyperos_hal_ext.py, Xiaomi's HAL extension casts only on Xiaomi's)"
        [ -f "$OUT/miui-telephony-common_patched.jar" ] && echo "# HyperOS: miui-telephony-common_patched.jar (patches/hyperos_telephony.py, the IMS controller without an IMS phone)"
        [ -f "$OUT/telephony-common_patched.jar" ] && echo "# telephony-common_patched.jar: the SMS service centre as an international number (patches/guest_smsc_international.py); SEND_SMS error 66 (sent, no result payload) counted as sent (patches/guest_sms_invalid_response.py)"
        [ -f "$OUT/libcamera_client_patched.so" ] && echo "# libcamera_client_patched.so, libcameracompatbilityinfo_patched.so: the native camera client with One UI's codes (patches/pixel_camera_native.py)"
        (cd "$OUT" && sha256sum services_patched.jar $([ -f oplus-services_patched.jar ] && echo oplus-services_patched.jar) \
            miui-services_patched.jar apprecovery.proinstaller_patched.jar framework_patched.jar miui-wifi-service_patched.jar \
            miui-telephony-common_patched.jar \
            $([ "$VOLD_GVLD" = 1 ] && echo vold_patched service.incremental_patched.so) \
            $([ -f telephony-common_patched.jar ] && echo telephony-common_patched.jar) \
            $([ -f libcamera_client_patched.so ] && echo libcamera_client_patched.so) \
            $([ -f libcameracompatbilityinfo_patched.so ] && echo libcameracompatbilityinfo_patched.so))
    else
        [ -f "$OUT/framework_patched.jar" ] && echo "# framework_patched.jar: the image's framework.jar with One UI's camera transaction codes (patches/pixel_camera_abi.py)"
        [ -f "$OUT/telephony-common_patched.jar" ] && echo "# telephony-common_patched.jar: the SMS service centre as an international number (patches/guest_smsc_international.py); SEND_SMS error 66 (sent, no result payload) counted as sent (patches/guest_sms_invalid_response.py)"
        [ -f "$OUT/libcamera_client_patched.so" ] && echo "# libcamera_client_patched.so, libcameracompatbilityinfo_patched.so: the native camera client with One UI's codes (patches/pixel_camera_native.py)"
        [ -f "$OUT/vivo-services_patched.jar" ] && echo "# vivo: vivo-services_patched.jar (patches/vivo_guards.py: no IOemNetd to One UI's netd, vivo-only HAL extensions; and the storage guards)"
        [ -f "$OUT/vivo-telephony-common-platform-ex_patched.jar" ] && echo "# vivo: vivo-telephony-common-platform-ex_patched.jar (patches/vivo_telephony.py: MtkRIL ready without MediaTek's mtkradioex services)"
        (cd "$OUT" && sha256sum services_patched.jar $([ -f oplus-services_patched.jar ] && echo oplus-services_patched.jar) \
            $([ -f vivo-services_patched.jar ] && echo vivo-services_patched.jar) \
            $([ -f vivo-telephony-common-platform-ex_patched.jar ] && echo vivo-telephony-common-platform-ex_patched.jar) \
            $([ -f framework-adapter_patched.jar ] && echo framework-adapter_patched.jar) \
            $([ "$VOLD_GVLD" = 1 ] && echo vold_patched service.incremental_patched.so) \
            $([ -f framework_patched.jar ] && echo framework_patched.jar) \
            $([ -f telephony-common_patched.jar ] && echo telephony-common_patched.jar) \
            $([ -f libcamera_client_patched.so ] && echo libcamera_client_patched.so) \
            $([ -f libcameracompatbilityinfo_patched.so ] && echo libcameracompatbilityinfo_patched.so))
    fi
} > "$OUT/guards.txt"

# surfaceflinger: skip the Qualcomm composer extension client, so every frame
# goes through the plain IComposerClient.executeCommands path. Samsung's
# composer answered ColorOS's qtiExecuteCommands batches with BAD_VALUE on
# every frame (black panel). At 0x470bc8 "cbz x8, 0x470c14" (no extension ->
# skip IQtiComposer3Client::fromBinder) becomes "b 0x470c14"; SurfaceFlinger
# then takes its own "Failed to get QtiComposer3Client service" fallback.
# Code segment: file offset == vaddr (LOAD 0x1d0000). Only for the exact builds
# below: the Find N6 and Find X9 Ultra CN images share one binary; the Find X9
# Ultra IN image (CPH2841IN) has the same code 0x5b0 later (0x471178, after
# AIBinder_getExtension, before IQtiComposer3Client::fromBinder), same bytes.
"$DEBUGFS" -R "dump /system/bin/surfaceflinger $WORK/surfaceflinger" "$IMG" 2>/dev/null
python3 -I - "$WORK/surfaceflinger" "$OUT/surfaceflinger_patched" <<'PYEOF'
import hashlib, os, sys
src, dst = sys.argv[1], sys.argv[2]
data = bytearray(open(src, "rb").read())
SITES = {"9896c0cba131": 0x470bc8, "a09087821954": 0x471178,
         # Nothing OS 5.0 (Metroid, SDK 37): same three instructions, at 0x452a50
         # (bl AIBinder_getExtension, ldr x8, cbz x8 -> +0x4c, bl IQtiComposer3Client::fromBinder).
         "e5a8726a6687": 0x452a50,
         # OnePlus OxygenOS 16 (CPH2745, Android 16): a status check (tbnz) comes between the
         # load and the cbz; cbz x8 -> +0x4c at 0x5d9bb8, the same bytes (code segment 0x2a0000,
         # file offset == vaddr).
         "b8dc0a4def28": 0x5d9bb8}
# vivo OriginOS 17 (MediaTek, X500 Pro Max CP2A.260605.016): after init, main()
# registers MediaTek's MtkSF_ext as vendor.mediatek.framework.mtksf_ext.IMtkSF_ext/
# default, a VINTF-stable binder only the guest's own manifest declares. One UI's
# servicemanager refuses it and the failed addService is a LOG(FATAL) (line 163):
# surfaceflinger aborts, black panel. At 0x657250 "cbz x8, 0x6573c8" (no IMtkSF_ext
# descriptor -> log "can't start MtkSF_ext", go on to the main loop at 0x65737c,
# where the registered path also ends) becomes "b 0x6573c8": the extension is never
# created; only MediaTek's vendor clients use it. This build has no QTI client.
# vivo OriginOS 6 CN (PD2609MA, k6993v1_64): the same code 0x6060 later, cbz x8 at
# 0x65d2b0 -> "can't start MtkSF_ext" at 0x65d428, which rejoins the main loop at
# 0x65d3dc where the registered path ends.
MTK_SITES = {"f693da9ab9b2": (0x657250, "c80b00b4", "5e000014"),
             "2b227833b558": (0x65d2b0, "c80b00b4", "5e000014")}
mtk = MTK_SITES.get(hashlib.sha1(data).hexdigest()[:12])
if mtk:
    moff, mold, mnew = mtk
    if data[moff:moff + 4] != bytes.fromhex(mold) or b"IQtiComposer3Client" in data:
        sys.exit("surfaceflinger: unexpected bytes at %#x, not patching" % moff)
    data[moff:moff + 4] = bytes.fromhex(mnew)
    # vivo: SurfaceFlinger reads ro.vivo.device.type itself and drives the second
    # panel only as "foldable"; it reads ro.oneos.vivo.dtype instead (same length),
    # which guest_props.sh sets per ONEOS_GUEST_VIVO_FOLD, so the apps can keep the
    # phone build's "phone" (fold mode 2; tenth CN run: vivo's apps took foldable
    # paths their phone build lacks) while both panels work.
    VT, VN = b"ro.vivo.device.type\0", b"ro.oneos.vivo.dtype\0"
    if data.count(VT) == 1 and VN not in data:
        data = data.replace(VT, VN)
        print("surfaceflinger: reads ro.oneos.vivo.dtype for vivo's device type")
    elif VT in data:
        sys.exit("surfaceflinger: ro.vivo.device.type %d times, not patching" % data.count(VT))
    open(dst, "wb").write(data)
    print("built %s (MediaTek MtkSF_ext not registered)" % dst)
    sys.exit(0)
if b"IMtkSF_ext" in data:
    sys.exit("surfaceflinger: a MediaTek build with MtkSF_ext this was not written against, not patching")
off = SITES.get(hashlib.sha1(data).hexdigest()[:12])
if off is None and b"IQtiComposer3Client" not in data:
    # Google's own build (Pixel image): no QTI composer client to skip.
    if os.path.exists(dst):
        os.remove(dst)
    print("surfaceflinger: no QTI composer client in this build, not patched (the image's runs)")
    sys.exit(0)
if off is None:
    sys.exit("surfaceflinger: unexpected build, not patching")
old, new = bytes.fromhex("680200b4"), bytes.fromhex("13000014")
if data[off:off + 4] != old:
    sys.exit("surfaceflinger: unexpected bytes at %#x, not patching" % off)
data[off:off + 4] = new
open(dst, "wb").write(data)
print("built %s (QTI composer client skipped)" % dst)
PYEOF
[ ! -f "$OUT/surfaceflinger_patched" ] || chmod 755 "$OUT/surfaceflinger_patched"

# libsensorservice.so (vivo OriginOS 17, X500 Pro Max): convertToSensorEvent reads
# two sensor types with vivo's own payload, where AOSP and One UI's sensor HAL
# send a scalar: HINGE_ANGLE (36) as 16 floats of "data" (vivo's foldables), and
# LIGHT (5) the same whenever ro.product.brand is not "Android" (in a session it
# is One UI's). The first hinge or light event from One UI's HAL then failed the
# union's tag check ("bad access: a wrong tag", _Tag = data) and SensorService
# aborted system_server (fourth OriginOS run). The switch's jump table (43
# halfwords at 0x18290, target = 0x45dd0 + 4 * entry) sends both types to the
# scalar branch every other scalar type takes (entry 0x1ef, 0x4658c), as AOSP
# does. Only the exact build below; the image's library otherwise.
rm -f "$OUT/libsensorservice_patched.so"
"$DEBUGFS" -R "dump /system/lib64/libsensorservice.so $WORK/libsensorservice.so" "$IMG" 2>/dev/null
python3 -I - "$WORK/libsensorservice.so" "$OUT/libsensorservice_patched.so" <<'PYEOF'
import hashlib, os, struct, sys
src, dst = sys.argv[1], sys.argv[2]
data = bytearray(open(src, "rb").read()) if os.path.isfile(src) else bytearray()
PINS = {"f43b606820527ceca41e989f8863a6fbc60f2b4b7b205f9415c514e0a7ccf826":
        [(0x18290 + 2 * 5, 0x1dd, 0x1ef), (0x18290 + 2 * 36, 0x0fa, 0x1ef)],
        # vivo OriginOS 6 CN (PD2609MA): the same switch with the same 43 entries,
        # table at 0x18250, target = 0x45de0 + 4 * entry: 0x1ef (0x4659c) is the
        # scalar branch (tag 4, one float), 0x1dd LIGHT's brand check + data read,
        # 0x0fa HINGE_ANGLE's data read.
        "a06232e1f7e32b630ecd812c87566ec2629540c245aea7d263b55a4b134ef609":
        [(0x18250 + 2 * 5, 0x1dd, 0x1ef), (0x18250 + 2 * 36, 0x0fa, 0x1ef)]}
patches = PINS.get(hashlib.sha256(data).hexdigest())
if patches is None:
    print("libsensorservice: not a build this was written against, the image's runs")
    sys.exit(0)
for off, old, new in patches:
    if struct.unpack_from("<H", data, off)[0] != old:
        sys.exit("libsensorservice: unexpected jump table entry at %#x, not patching" % off)
    struct.pack_into("<H", data, off, new)
open(dst, "wb").write(data)
print("built %s (LIGHT and HINGE_ANGLE events read as scalars, as One UI's sensor HAL sends them)" % dst)
PYEOF
rm -f "$WORK/libsensorservice.so"
[ ! -f "$OUT/libsensorservice_patched.so" ] || chmod 644 "$OUT/libsensorservice_patched.so"

# libcomposer_ext.so (vivo OriginOS 17, MediaTek): ComposerExt::ClientImpl::Init asks for
# vendor.mediatek.hardware.composer_ext@1.0::IComposerExt 21 times 100 ms apart. Samsung's
# vendor has none, and SurfaceFlinger runs it on its main thread at every display power-mode
# change (and system_server's sensorservice once): 2.1 s of a frozen screen per change, two
# per fold, the bulk of the 20-25 s cover/inner switch of the seventh OriginOS run. After the
# first failed lookup and its log line, "mov w0, #0x86a0" (the 100 ms usleep's argument) at
# 0x1ca28 becomes "b 0x1cec0", the loop's own "retries used up" exit (mov w0, #-0x70): the
# same -112 result and state as after 21 tries, at once. guest_prepare.sh binds it.
rm -f "$OUT/libcomposer_ext_patched.so"
"$DEBUGFS" -R "dump /system/system_ext/lib64/libcomposer_ext.so $WORK/libcomposer_ext.so" "$IMG" 2>/dev/null
python3 -I - "$WORK/libcomposer_ext.so" "$OUT/libcomposer_ext_patched.so" <<'PYEOF'
import hashlib, os, sys
src, dst = sys.argv[1], sys.argv[2]
data = bytearray(open(src, "rb").read()) if os.path.isfile(src) else bytearray()
PINS = {"ad21236f78393660e11c2b5b28ec6de249d14409b4eda4ed242ff150a37b6bf6":
        ((0x1ca28, "00d49052", "26010014"), [(0x1cec0, "e00d8012"), (0x1ca30, "86990094")])}
pin = PINS.get(hashlib.sha256(data).hexdigest())
if pin is None:
    print("libcomposer_ext: not a build this was written against, the image's runs" if data else "libcomposer_ext: not in the image")
    sys.exit(0)
(off, old, new), checks = pin
for o, want in checks + [(off, old)]:
    if data[o:o + 4].hex() != want:
        sys.exit("libcomposer_ext: unexpected bytes at %#x, not patching" % o)
data[off:off + 4] = bytes.fromhex(new)
open(dst, "wb").write(data)
print("built %s (one IComposerExt lookup, not 21 x 100 ms)" % dst)
PYEOF
rm -f "$WORK/libcomposer_ext.so"
[ ! -f "$OUT/libcomposer_ext_patched.so" ] || chmod 644 "$OUT/libcomposer_ext_patched.so"

# bootanimation on every panel (patch-bootanim-multidisplay.py; guest_prepare.sh
# binds it under the image's own name): without Android's multidisplay flag it
# drew on the Fold's inner panel only, the cover black when started folded.
for l in libbootanimation_preapex libbootanimation; do
    rm -f "$OUT/${l}_patched.so" "$WORK/$l.so"
    "$DEBUGFS" -R "dump /system/lib64/$l.so $WORK/$l.so" "$IMG" 2>/dev/null
    [ -s "$WORK/$l.so" ] || continue
    python3 -I "$ROOT/scripts/patch-bootanim-multidisplay.py" "$WORK/$l.so" "$OUT/${l}_patched.so" || rm -f "$OUT/${l}_patched.so"
done

# com.oplus.wallpapers "Home screen, Lock screen & style": with type.fold the app
# uses its Find N6 inner-screen page, a 4x4 grid where every card is 2x2 = half
# the panel (run 30: 1072 px cards, "too zoomed in"). This static RRO
# (switcher/overlays/wallpapers_fold_grid) keeps 4x4 in embedded panes and
# chooses 8x2 only for windows at least 800dp wide; guest_prepare.sh binds it in the guest's /oem/overlay. Built only if
# the image's layout is still the 4x4 one it was written against.
RRO="$ROOT/switcher/overlays/wallpapers_fold_grid"
"$DEBUGFS" -R "dump /my_stock/priv-app/Wallpapers/Wallpapers.apk $WORK/Wallpapers.apk" "$IMG" 2>/dev/null
LAYOUT=$("$BT/aapt2" dump resources "$WORK/Wallpapers.apk" 2>/dev/null | grep -A1 ' layout/personal_card_fold_large_layout$' | sed -n 's/.*(file) \([^ ]*\) type=XML.*/\1/p')
if [ -n "$LAYOUT" ] && "$BT/aapt2" dump xmltree --file "$LAYOUT" "$WORK/Wallpapers.apk" | grep -q 'columnCount(0x[0-9a-f]*)=4'; then
    "$BT/aapt2" compile --dir "$RRO/res" -o "$WORK/rro.zip"
    "$BT/aapt2" link -o "$WORK/rro.apk" -I "$AJ" --manifest "$RRO/AndroidManifest.xml" \
        --min-sdk-version 35 --target-sdk-version 36 "$WORK/rro.zip"
    "$BT/zipalign" -p -f 4 "$WORK/rro.apk" "$WORK/rro-aligned.apk"
    "$BT/apksigner" sign --ks "${KEYSTORE:-$HOME/.android/debug.keystore}" \
        --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android \
        --out "$OUT/OneOSWallpapersFoldGrid.apk" "$WORK/rro-aligned.apk"
    rm -f "$OUT/OneOSWallpapersFoldGrid.apk.idsig"
    echo "built $OUT/OneOSWallpapersFoldGrid.apk (Wallpapers responsive fold grid)"
else
    rm -f "$OUT/OneOSWallpapersFoldGrid.apk"
    echo "Wallpapers.apk: fold card layout not as expected, grid overlay not built"
fi

# Patch one dex of a system APK and splice it back with the signing block as
# it was (scripts/apk-replace-dex.py): PackageManager does not check the digests
# of an APK on a system partition and still reads the platform certificate.
# patch_apk_dex <apk> <out apk> <patcher in switcher/patches> <class the image
# must have> <what it does>. The patcher refuses a body it was not written for;
# then nothing is built.
patch_apk_dex() {
    rm -f "$2"
    if ! unzip -p "$1" 'classes*.dex' 2>/dev/null | grep -aq "$4"; then
        echo "$(basename "$1"): no $4, $5: not built"
        return 0
    fi
    rm -rf "$WORK/pad"
    java -jar "$APKTOOL" d -q -f -r -o "$WORK/pad" "$1"
    if PAD_DIRS=$(python3 -I "$ROOT/switcher/patches/$3" "$WORK/pad") && [ -n "$PAD_DIRS" ]; then
        # Rebuild the dex files the patcher changed only (one per line it printed);
        # the others are left out of the build, and each goes back in turn.
        for d in "$WORK"/pad/smali*; do
            echo "$PAD_DIRS" | grep -qx "$(basename "$d")" || rm -rf "$d"
        done
        java -jar "$APKTOOL" b -q -o "$WORK/pad-rebuilt.apk" "$WORK/pad"
        rm -rf "$WORK/pad-dex" "$WORK/pad-dex.jar" && mkdir -p "$WORK/pad-dex"
        PAD_IN="$1"; PAD_N=0; PAD_ALL=""
        for PAD_DIR in $PAD_DIRS; do
            PAD_DEX="$(echo "$PAD_DIR" | sed 's/^smali_//; s/^smali$/classes/').dex"
            unzip -q -o "$WORK/pad-rebuilt.apk" "$PAD_DEX" -d "$WORK/pad-dex"
            (cd "$WORK/pad-dex" && zip -q -0 "$WORK/pad-dex.jar" "$PAD_DEX")
            PAD_N=$((PAD_N + 1))
            python3 -I "$ROOT/scripts/apk-replace-dex.py" "$PAD_IN" "$PAD_DEX" "$WORK/pad-dex/$PAD_DEX" "$WORK/pad-step$PAD_N.apk"
            PAD_IN="$WORK/pad-step$PAD_N.apk"; PAD_ALL="$PAD_ALL $PAD_DEX"
        done
        python3 -I "$ROOT/scripts/check-dex.py" "$WORK/pad-dex.jar"
        mv -f "$PAD_IN" "$2"
        rm -f "$WORK"/pad-step*.apk
        echo "built $2 ($5,$PAD_ALL)"
    else
        echo "$(basename "$1"): $5: not built (see above)"
    fi
    rm -rf "$WORK/pad" "$WORK/pad-rebuilt.apk" "$WORK/pad-dex" "$WORK/pad-dex.jar"
}

# vivo's launcher stays a bar phone's (switcher/patches/vivo_launcher.py, with
# vivo_guards.py framework's FtDeviceInfo): with ro.vivo.device.type=foldable
# (vivo fold mode on a Galaxy Z Fold) the X500 Pro Max's BBKLauncher2 exited at
# start (eighth run), and let through, crashed in its foldable paths, whose
# classes its build lacks (ninth run). guest_prepare.sh binds
# BBKLauncher2_patched.apk over the image's, only when the image's APK is the one
# it was made from (BBKLauncher2_patched.apk.src_sha256) and a build it pins.
rm -f "$OUT/BBKLauncher2_patched.apk" "$OUT/BBKLauncher2_patched.apk.src_sha256"
if in_image /system/framework/vivo-services.jar && in_image /system/app/BBKLauncher2/BBKLauncher2.apk; then
    "$DEBUGFS" -R "dump /system/app/BBKLauncher2/BBKLauncher2.apk $WORK/BBKLauncher2.apk" "$IMG" 2>/dev/null
    patch_apk_dex "$WORK/BBKLauncher2.apk" "$OUT/BBKLauncher2_patched.apk" vivo_launcher.py \
        "ro.vivo.device.type" "its own device type kept"
    [ ! -f "$OUT/BBKLauncher2_patched.apk" ] ||
        sha256sum "$WORK/BBKLauncher2.apk" | cut -d' ' -f1 > "$OUT/BBKLauncher2_patched.apk.src_sha256"
    rm -f "$WORK/BBKLauncher2.apk"
fi

# HyperOS's wallpaper app on a one-panel phone (switcher/patches/
# hyperos_miwallpaper_null.py): it died in Application.onCreate on every start
# when the lock wallpaper had no effect type yet (0.4.32, Galaxy S25), so there
# was no wallpaper. guest_prepare.sh binds MiWallpaper_patched.apk over the
# image's. HyperOS images keep /product at the image root.
rm -f "$OUT/MiWallpaper_patched.apk"
MIWP=""
for p in /product/app/MiWallpaper/MiWallpaper.apk /system/product/app/MiWallpaper/MiWallpaper.apk; do
    in_image "$p" && { MIWP=$p; break; }
done
if [ -n "$MIWP" ]; then
    "$DEBUGFS" -R "dump $MIWP $WORK/MiWallpaper.apk" "$IMG" 2>/dev/null
    patch_apk_dex "$WORK/MiWallpaper.apk" "$OUT/MiWallpaper_patched.apk" hyperos_miwallpaper_null.py \
        'Lcom/miui/miwallpaper/utils/WallpaperTypeUtils;' "wallpaper app starts with an unknown effect type"
    rm -f "$WORK/MiWallpaper.apk"
else
    echo "MiWallpaper.apk: not in the image, nothing to patch"
fi

# Pixel's status bar (run 42): SystemUIGoogle's StatusBarContentInsetsProvider
# leaves ongoing_appops_dot_min_padding (20dp, for the privacy dot) on the end
# side and only rounded_corner_content_padding on the start side, which points to
# the framework's 0dp here (Pixel's vendor overlay sets it; the guest runs on
# Samsung's vendor partition): the battery sat 47-60 px further from the right
# edge than the clock from the left, on both panels. This static RRO
# (switcher/overlays/pixel_statusbar, signed like the grid overlay) makes both
# paddings 8dp and keeps a 4dp end padding on the inner panel (sw600dp, 0dp in
# the image); guest_prepare.sh puts it in the guest's /oem/overlay when the
# guest has SystemUIGoogle. Built only when the image's SystemUIGoogle has the
# three dimens and declares no overlayable resources (an /oem overlay may then
# override any of them), and not when the image gives one of them a value for a
# configuration the overlay lacks and a phone panel can match: that target
# value would win over the overlay's (sw1000dp and up is ignored here).
SYSUI=/system/system_ext/priv-app/SystemUIGoogle/SystemUIGoogle.apk
# Infinity-X (0.4.33): AOSP's SystemUI has the same insets provider and the same
# gap (rounded_corner_content_padding points to the framework's 0dp on Samsung's
# vendor; A56 report a321c25b: "the clock padding on status bar is too close to
# the right corner"). Not ColorOS's SystemUI (same package, OPPO's own layout):
# an image with oplus-telephony-common.jar keeps its own.
if ! in_image "$SYSUI" && ! in_image /system/system_ext/framework/oplus-telephony-common.jar &&
   in_image /system/system_ext/priv-app/SystemUI/SystemUI.apk; then
    SYSUI=/system/system_ext/priv-app/SystemUI/SystemUI.apk
fi
SB_RRO="$ROOT/switcher/overlays/pixel_statusbar"
SB_DIMENS="rounded_corner_content_padding ongoing_appops_dot_min_padding status_bar_padding_end"
# "<name> <(config)>" for each of those dimens in an APK's resource dump.
sb_cfgs() {
    awk -v names=" $SB_DIMENS " '
        /^ *resource 0x/ { n = $3; cur = ""; if (sub(/^dimen\//, "", n) && index(names, " " n " ")) cur = n; next }
        cur != "" && /^ *\(/ { print cur, $1 }' "$1"
}
rm -f "$OUT/OneOSPixelStatusBar.apk"
if in_image "$SYSUI"; then
    "$DEBUGFS" -R "dump $SYSUI $WORK/SystemUIGoogle.apk" "$IMG" 2>/dev/null
    "$BT/aapt2" dump resources "$WORK/SystemUIGoogle.apk" > "$WORK/sysui_res.txt" 2>/dev/null || true
    SB_MISSING=""
    for d in $SB_DIMENS; do
        grep -q " dimen/$d\$" "$WORK/sysui_res.txt" || SB_MISSING="$SB_MISSING $d"
    done
    SB_OVERLAYABLE=$("$BT/aapt2" dump overlayable "$WORK/SystemUIGoogle.apk" 2>/dev/null | head -n 3) || true
    if [ -n "$SB_MISSING" ]; then
        echo "$(basename "$SYSUI"): no dimen$SB_MISSING, status bar overlay not built"
    elif [ -n "$SB_OVERLAYABLE" ]; then
        echo "$(basename "$SYSUI") declares overlayable resources, status bar overlay not built"
    else
        # No deduping: aapt2 drops the sw600dp value equal to the default one,
        # and the image's sw600dp 0dp would then win on the inner panel.
        "$BT/aapt2" compile --dir "$SB_RRO/res" -o "$WORK/sb.zip"
        "$BT/aapt2" link -o "$WORK/sb.apk" -I "$AJ" --manifest "$SB_RRO/AndroidManifest.xml" \
            --min-sdk-version 35 --target-sdk-version 36 --no-resource-deduping "$WORK/sb.zip"
        "$BT/aapt2" dump resources "$WORK/sb.apk" > "$WORK/sb_res.txt"
        sb_cfgs "$WORK/sb_res.txt" > "$WORK/sb_cfgs.txt"
        SB_UNCOVERED=$(sb_cfgs "$WORK/sysui_res.txt" | while read -r n c; do
            grep -qxF "$n $c" "$WORK/sb_cfgs.txt" && continue
            sw=$(echo "$c" | sed -n 's/^(sw\([0-9][0-9]*\)dp.*/\1/p')
            [ -n "$sw" ] && [ "$sw" -ge 1000 ] && continue
            printf ' %s%s' "$n" "$c"
        done) || true
        if [ "$(wc -l < "$WORK/sb_cfgs.txt")" != 4 ]; then
            echo "pixel_statusbar overlay: unexpected resources ($(tr '\n' ' ' < "$WORK/sb_cfgs.txt")), not built" >&2
            exit 1
        elif [ -n "$SB_UNCOVERED" ]; then
            echo "$(basename "$SYSUI") has$SB_UNCOVERED, which the overlay does not cover: status bar overlay not built"
        else
            "$BT/zipalign" -p -f 4 "$WORK/sb.apk" "$WORK/sb-aligned.apk"
            "$BT/apksigner" sign --ks "${KEYSTORE:-$HOME/.android/debug.keystore}" \
                --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android \
                --out "$OUT/OneOSPixelStatusBar.apk" "$WORK/sb-aligned.apk"
            rm -f "$OUT/OneOSPixelStatusBar.apk.idsig"
            echo "built $OUT/OneOSPixelStatusBar.apk (Pixel status bar insets: $(tr '\n' ' ' < "$WORK/sb_cfgs.txt"))"
        fi
    fi
else
    echo "SystemUIGoogle.apk (or an AOSP SystemUI.apk): not in the image, no status bar overlay"
fi

# Patch one dex of a system APK and splice it back with the signing block as
# it was (scripts/apk-replace-dex.py): PackageManager does not check the digests
# of an APK on a system partition and still reads the platform certificate.
# patch_apk_dex <apk> <out apk> <patcher in switcher/patches> <class the image
# must have> <what it does>. The patcher refuses a body it was not written for;
# then nothing is built.
# Quick settings on a tablet-width panel. Nothing OS's SystemUI has
# config_use_split_notification_shade for (land) and (sw600dp-land) but no
# sw600dp-port value, so on the Z Fold's inner panel in portrait (sw902dp) it
# fell back to the () phone shade and the tiles were stretched over 2256 px,
# while config_use_large_screen_shade_header, which does have an (sw600dp)
# value, had already gone large-screen: the two disagreed (the owner, first
# Nothing runs). The overlay gives both a value under sw600dp, which covers
# portrait as well; the cover panel is below 600dp and keeps the phone shade.
# Built only when the image's SystemUI has both bools and declares no
# overlayable resources (an /oem overlay may then override any of them).
QS_SYSUI=""
for p in /system_ext/priv-app/SystemUI/SystemUI.apk /system/system_ext/priv-app/SystemUI/SystemUI.apk; do
    in_image "$p" && { QS_SYSUI=$p; break; }
done
QS_RRO="$ROOT/switcher/overlays/nothing_tablet_qs"
QS_BOOLS="config_use_split_notification_shade config_use_large_screen_shade_header"
rm -f "$OUT/OneOSTabletQs.apk" "$OUT/SystemUI_patched.apk"
if [ -n "$QS_SYSUI" ]; then
    "$DEBUGFS" -R "dump $QS_SYSUI $WORK/SystemUI.apk" "$IMG" 2>/dev/null
    "$BT/aapt2" dump resources "$WORK/SystemUI.apk" > "$WORK/qs_res.txt" 2>/dev/null || true
    QS_MISSING=""
    for b in $QS_BOOLS; do
        grep -q " bool/$b\$" "$WORK/qs_res.txt" || QS_MISSING="$QS_MISSING $b"
    done
    QS_OVERLAYABLE=$("$BT/aapt2" dump overlayable "$WORK/SystemUI.apk" 2>/dev/null | head -n 3) || true
    if [ -n "$QS_MISSING" ]; then
        echo "SystemUI.apk: no bool$QS_MISSING, tablet quick settings overlay not built"
    elif [ -n "$QS_OVERLAYABLE" ]; then
        echo "SystemUI.apk declares overlayable resources, tablet quick settings overlay not built"
    else
        # The tile sizes are not resources: run 10 had sw600dp dimens here,
        # scaled from the image's own, and the overlay enabled above Nothing's
        # own, with no effect. The panel draws at a density of its own
        # (SystemUI_patched.apk below).
        "$BT/aapt2" compile --dir "$QS_RRO/res" -o "$WORK/qs.zip"
        "$BT/aapt2" link -o "$WORK/qs.apk" -I "$AJ" --manifest "$QS_RRO/AndroidManifest.xml" \
            --min-sdk-version 35 --target-sdk-version 36 --no-resource-deduping "$WORK/qs.zip"
        "$BT/zipalign" -p -f 4 "$WORK/qs.apk" "$WORK/qs-aligned.apk"
        "$BT/apksigner" sign --ks "${KEYSTORE:-$HOME/.android/debug.keystore}" \
            --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android \
            --out "$OUT/OneOSTabletQs.apk" "$WORK/qs-aligned.apk"
        rm -f "$OUT/OneOSTabletQs.apk.idsig"
        echo "built $OUT/OneOSTabletQs.apk (split shade and large-screen header from sw600dp)"
    fi
    # Nothing's quick settings panel at the screen's own density on a panel of
    # sw600dp and up (switcher/patches/nothing_qs_density.py): it lays itself
    # out as if every screen were 420 dp wide, which on the Fold's inner panel
    # is 859 dpi, tiles twice the size and half the panel off the screen. One
    # method in one dex; scripts/apk-replace-dex.py puts that dex back without
    # touching the signing block, so PackageManager, which does not check the
    # digests of an APK on a system partition, still reads the platform
    # certificate. Only for the build the patch was written for: the patcher
    # refuses any other body.
    patch_apk_dex "$WORK/SystemUI.apk" "$OUT/SystemUI_patched.apk" nothing_qs_density.py \
        'Lcom/nothing/systemui/qs/workspace/workspace/CellLayoutKt;' \
        "quick settings at the screen's density from sw600dp"
else
    echo "SystemUI.apk: not in the image, no tablet quick settings overlay"
fi

# Nothing's app drawer with more category boxes per row on a wide panel
# (switcher/patches/nothing_launcher_drawer.py): it has two per row on any
# screen, sized from the width, and on the Fold's inner panel each box came out
# about 1000 x 1100 px around four normal icons (the owner, Nothing run 11).
LAUNCHER=""
for p in /system_ext/priv-app/NothingLauncher3/NothingLauncher3.apk /system/system_ext/priv-app/NothingLauncher3/NothingLauncher3.apk; do
    in_image "$p" && { LAUNCHER=$p; break; }
done
rm -f "$OUT/NothingLauncher3_patched.apk"
if [ -n "$LAUNCHER" ]; then
    "$DEBUGFS" -R "dump $LAUNCHER $WORK/NothingLauncher3.apk" "$IMG" 2>/dev/null
    patch_apk_dex "$WORK/NothingLauncher3.apk" "$OUT/NothingLauncher3_patched.apk" nothing_launcher_drawer.py \
        'Lcom/nothing/launcher/allapps/smart/z;' "drawer category boxes per row from the width"
    rm -f "$WORK/NothingLauncher3.apk"
else
    echo "NothingLauncher3.apk: not in the image, drawer left as it is"
fi

# Nothing OS's About phone with the phone's own hardware (switcher/overlays/
# nothing_about): its own-phone mode, the Fold's cameras and picture. Only for
# an image with Nothing's Settings; guest_prepare.sh installs it on the F8U.
NA_RRO="$ROOT/switcher/overlays/nothing_about"
rm -f "$OUT/OneOSNtAbout.apk" "$OUT"/OneOSNtAbout?*.apk
for p in /system_ext/priv-app/NothingSettings/NothingSettings.apk /system/system_ext/priv-app/NothingSettings/NothingSettings.apk; do
    in_image "$p" || continue
    "$BT/aapt2" compile --dir "$NA_RRO/res" -o "$WORK/na.zip"
    # No --min-sdk-version: it would drop the -v4 of values-xxhdpi-v4, and the
    # pictures must match Nothing's drawable-xxhdpi-v4 exactly to win.
    "$BT/aapt2" link -o "$WORK/na.apk" -I "$AJ" --manifest "$NA_RRO/AndroidManifest.xml" \
        --target-sdk-version 36 --no-resource-deduping "$WORK/na.zip"
    "$BT/zipalign" -p -f 4 "$WORK/na.apk" "$WORK/na-aligned.apk"
    "$BT/apksigner" sign --ks "${KEYSTORE:-$HOME/.android/debug.keystore}" \
        --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android \
        --out "$OUT/OneOSNtAbout.apk" "$WORK/na-aligned.apk"
    rm -f "$OUT/OneOSNtAbout.apk.idsig"
    echo "built $OUT/OneOSNtAbout.apk (Nothing About phone: own-phone mode, cameras, picture)"
    # The other Nothing phones (0.4.35): the Z Fold8 with the Fold's resources
    # and its own picture and lenses over them; the S26 family and the Z Flip8
    # with nothing_about_phone (the processor's whole name, the S26's picture),
    # the S26 Ultra's and the flip's pictures and lenses over that.
    NP_RRO="$ROOT/switcher/overlays/nothing_about_phone"
    "$BT/aapt2" compile --dir "$NP_RRO/res" -o "$WORK/np.zip"
    for v in Fold8 Phone S26U Flip; do
        case $v in
            Fold8) base="$WORK/na.zip"; man="$NA_RRO/AndroidManifest.xml"; layer=nothing_about_fold8 ;;
            Phone) base="$WORK/np.zip"; man="$NP_RRO/AndroidManifest.xml"; layer="" ;;
            S26U) base="$WORK/np.zip"; man="$NP_RRO/AndroidManifest.xml"; layer=nothing_about_s26u ;;
            Flip) base="$WORK/np.zip"; man="$NP_RRO/AndroidManifest.xml"; layer=nothing_about_flip ;;
        esac
        extra=""
        if [ -n "$layer" ]; then
            "$BT/aapt2" compile --dir "$ROOT/switcher/overlays/$layer/res" -o "$WORK/nl.zip"
            extra="-R $WORK/nl.zip"
        fi
        # shellcheck disable=SC2086
        "$BT/aapt2" link -o "$WORK/np.apk" -I "$AJ" --manifest "$man" \
            --target-sdk-version 36 --no-resource-deduping "$base" $extra
        "$BT/zipalign" -p -f 4 "$WORK/np.apk" "$WORK/np-aligned.apk"
        "$BT/apksigner" sign --ks "${KEYSTORE:-$HOME/.android/debug.keystore}" \
            --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android \
            --out "$OUT/OneOSNtAbout$v.apk" "$WORK/np-aligned.apk"
        rm -f "$OUT/OneOSNtAbout$v.apk.idsig" "$WORK/np.apk" "$WORK/np-aligned.apk" "$WORK/nl.zip"
        echo "built $OUT/OneOSNtAbout$v.apk (Nothing About phone, $v)"
    done
    break
done

# One UI's brightness range (switcher/overlays/samsung_brightness_range), for a
# Nothing image for now (guest_prepare.sh installs it there).
BR_RRO="$ROOT/switcher/overlays/samsung_brightness_range"
rm -f "$OUT/OneOSBrightnessRange.apk"
if in_image /system_ext/framework/nt-telephony-common.jar || in_image /system/system_ext/framework/nt-telephony-common.jar; then
    "$BT/aapt2" compile --dir "$BR_RRO/res" -o "$WORK/br.zip"
    "$BT/aapt2" link -o "$WORK/br.apk" -I "$AJ" --manifest "$BR_RRO/AndroidManifest.xml" \
        --min-sdk-version 35 --target-sdk-version 36 --no-resource-deduping "$WORK/br.zip"
    "$BT/zipalign" -p -f 4 "$WORK/br.apk" "$WORK/br-aligned.apk"
    "$BT/apksigner" sign --ks "${KEYSTORE:-$HOME/.android/debug.keystore}" \
        --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android \
        --out "$OUT/OneOSBrightnessRange.apk" "$WORK/br-aligned.apk"
    rm -f "$OUT/OneOSBrightnessRange.apk.idsig"
    echo "built $OUT/OneOSBrightnessRange.apk (One UI's brightness range)"
fi

# Essential Space from a double press of power (switcher/overlays/
# nothing_essential_key), for an image with Nothing's Essential Space.
NE_RRO="$ROOT/switcher/overlays/nothing_essential_key"
rm -f "$OUT/OneOSNtEssentialKey.apk"
if in_image /product/overlayfs_origin/system/noth/priv-app/EssentialSpace/EssentialSpace.apk; then
    "$BT/aapt2" compile --dir "$NE_RRO/res" -o "$WORK/ne.zip"
    "$BT/aapt2" link -o "$WORK/ne.apk" -I "$AJ" --manifest "$NE_RRO/AndroidManifest.xml" \
        --min-sdk-version 35 --target-sdk-version 36 --no-resource-deduping "$WORK/ne.zip"
    "$BT/zipalign" -p -f 4 "$WORK/ne.apk" "$WORK/ne-aligned.apk"
    "$BT/apksigner" sign --ks "${KEYSTORE:-$HOME/.android/debug.keystore}" \
        --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android \
        --out "$OUT/OneOSNtEssentialKey.apk" "$WORK/ne-aligned.apk"
    rm -f "$OUT/OneOSNtEssentialKey.apk.idsig"
    echo "built $OUT/OneOSNtEssentialKey.apk (Essential Space on a double press of power)"
fi

# Per-panel display cutout for the Z Fold (switcher/overlays/fold_display_cutout).
# An image whose framework-res leaves config_displayUniqueIdArray empty takes
# the cutout from Samsung's vendor framework overlay, which /vendor shares with
# the guest, and applies the cover's punch hole to whichever panel is on: the
# inner panel, which has no cutout on this phone, got a phantom 108 px notch
# (Nothing OS run 7). The overlay names the cover panel only (arrays.xml says
# why not the inner); in run 10 the inner then had no cutout and a 24 dp status
# bar inset. guest_prepare.sh installs it on the Z Fold (F8U) only, since the
# ids and the hole are that phone's.
CO_RRO="$ROOT/switcher/overlays/fold_display_cutout"
CO_ARRAYS="config_displayUniqueIdArray config_displayCutoutPathArray"
CO_DIMENS="status_bar_height status_bar_height_default status_bar_height_portrait"
rm -f "$OUT/OneOSFoldCutout.apk"
if in_image /system/framework/framework-res.apk; then
    "$DEBUGFS" -R "dump /system/framework/framework-res.apk $WORK/framework-res.apk" "$IMG" 2>/dev/null
    "$BT/aapt2" dump resources "$WORK/framework-res.apk" > "$WORK/co_res.txt" 2>/dev/null || true
    CO_MISSING=""
    for a in $CO_ARRAYS; do
        grep -q " array/$a\$" "$WORK/co_res.txt" || CO_MISSING="$CO_MISSING $a"
    done
    for d in $CO_DIMENS; do
        grep -q " dimen/$d\$" "$WORK/co_res.txt" || CO_MISSING="$CO_MISSING $d"
    done
    CO_OVERLAYABLE=$("$BT/aapt2" dump overlayable "$WORK/framework-res.apk" 2>/dev/null | head -n 3) || true
    if [ -n "$CO_MISSING" ]; then
        echo "framework-res.apk: no$CO_MISSING, fold cutout overlay not built"
    elif [ -n "$CO_OVERLAYABLE" ]; then
        echo "framework-res.apk declares overlayable resources, fold cutout overlay not built"
    else
        # vivo centres its dynamic island on the cutout's bounding box, taking
        # bottom - width/2 as the lens centre (DynamicCapsuleContainer.updateCutoutValue).
        # One UI's 0..108 box put it at 73 px, under the lens (19..89, centre 54; F8U run
        # 21). A vivo image gets the lens itself, the same circle One UI's spec draws
        # (host_holes: M 0,19 a 35,35 ...); the status bar height stays 54dp. Cutout specs
        # are relative to the panel's top centre (CutoutSpecification): the shared
        # 505..575 box lies right of the cover, so no cutout reached the guest at all
        # (run 23: empty bounds); the lens is written centre-relative, as One UI's spec.
        CO_RES="$CO_RRO/res"
        CO_NOTE="cover 505,0-575,108"
        if in_image /system/framework/vivo-services.jar; then
            # In fold mode vivo's SurfaceFlinger names the cover "local:secondary" (run 22:
            # the numeric id never matched, no cover cutout at all), so both names.
            rm -rf "$WORK/co_res" && cp -r "$CO_RRO/res" "$WORK/co_res" &&
                sed -i -e 's#<item>M 505,0 L 575,0 L 575,108 L 505,108 Z</item>#<item>M 0,19 a 35,35 0 1,0 0,70 a 35,35 0 1,0 0,-70 Z</item>\n        <item>M 0,19 a 35,35 0 1,0 0,70 a 35,35 0 1,0 0,-70 Z</item>#' \
                       -e 's#<item>local:4630946379103915412</item>#<item>local:4630946379103915412</item>\n        <item>local:secondary</item>#' "$WORK/co_res/values/arrays.xml"
            [ "$(grep -c '<item>M 0,19 a 35,35 0 1,0 0,70 a 35,35 0 1,0 0,-70 Z</item>' "$WORK/co_res/values/arrays.xml")" = 2 ] &&
                grep -q '<item>local:secondary</item>' "$WORK/co_res/values/arrays.xml" ||
                { echo "fold cutout overlay: the cover path is not the expected one, vivo lens not applied" >&2; exit 1; }
            CO_RES="$WORK/co_res"; CO_NOTE="cover lens 505,19-575,89 (vivo island)"
        fi
        "$BT/aapt2" compile --dir "$CO_RES" -o "$WORK/co.zip"
        "$BT/aapt2" link -o "$WORK/co.apk" -I "$AJ" --manifest "$CO_RRO/AndroidManifest.xml" \
            --min-sdk-version 35 --target-sdk-version 36 --no-resource-deduping "$WORK/co.zip"
        "$BT/zipalign" -p -f 4 "$WORK/co.apk" "$WORK/co-aligned.apk"
        "$BT/apksigner" sign --ks "${KEYSTORE:-$HOME/.android/debug.keystore}" \
            --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android \
            --out "$OUT/OneOSFoldCutout.apk" "$WORK/co-aligned.apk"
        rm -f "$OUT/OneOSFoldCutout.apk.idsig"
        echo "built $OUT/OneOSFoldCutout.apk (inner panel no cutout and 24dp status bar, $CO_NOTE and 54dp)"; rm -rf "$WORK/co_res"
    fi
else
    echo "framework-res.apk: not in the image, no fold cutout overlay"
fi

# The guest's own APEX payloads, which guest_prepare.sh loop-mounts into the
# container ($STAGE/<name>_payload.img). Extracting them on the phone picked up
# the HOST's modules (Google-signed tethering next to ColorOS's OPPO-signed
# NetworkStack: PackageManagerService "Signature mismatch ... shared user
# android.uid.networkstack"), so take them from the image here.
# OPPO's CN images carry com.android.<name>.apex/.capex; a global image (the
# Find X9 Ultra IN, CPH2841IN) carries Google's mainline builds of the same
# modules instead, com.google.android.<name>[_tplus]_compressed.apex (the
# compressed layout: original_apex inside) or com.google.android.<name>.apex.
# The module name inside is com.android.<name> either way, which is what
# guest_prepare.sh mounts the payload as.
# Pixel 17 (yogi) has no /system/framework/framework-telecom.jar: android.telecom
# is in its telephonycore module (framework-telecom.jar, service-telecom.jar).
# One UI's telephonycore has neither (One UI, like ColorOS, keeps the platform
# jar), so run 38's guest zygote died preloading SystemServiceRegistry
# (NoClassDefFoundError for android.telecom.TelecomFrameworkInitializer). Such an
# image gets its own telephonycore, and its conscrypt and profiling: One UI's
# newer builds of those call into ART and framework APIs Pixel's lack
# (javax.crypto KEM/KDF, ActivityManagerLocal.crashApplication,
# Process.setProcessThreadGroup). guest_prepare.sh mounts these only when
# staged; ColorOS's images have the platform jar, so their sets are unchanged.
EXTRA=""
if ! in_image /system/framework/framework-telecom.jar; then
    EXTRA="telephonycore conscrypt profiling"
    echo "no platform framework-telecom.jar: also the image's $EXTRA"
fi
for name in art i18n runtime sdkext nfcservices tethering crashrecovery cellbroadcast \
            extservices permission wifi appsearch mediaprovider adservices rkpd \
            healthfitness ondevicepersonalization configinfrastructure bt $EXTRA; do
    rm -f "$WORK/m.apex" "$WORK/m.capex"
    for f in com.android.$name.apex com.android.$name.capex com.google.android.$name.apex \
             com.google.android.${name}_compressed.apex com.google.android.${name}_tplus_compressed.apex; do
        "$DEBUGFS" -R "dump /system/apex/$f $WORK/m.capex" "$IMG" 2>/dev/null
        [ -s "$WORK/m.capex" ] || continue
        # Compressed (original_apex inside) or a plain APEX.
        if unzip -l "$WORK/m.capex" original_apex >/dev/null 2>&1; then
            unzip -p "$WORK/m.capex" original_apex > "$WORK/m.apex"
        else
            mv "$WORK/m.capex" "$WORK/m.apex"
        fi
        echo "payload $name: from /system/apex/$f"
        break
    done
    if [ -s "$WORK/m.apex" ]; then
        unzip -p "$WORK/m.apex" apex_payload.img > "$OUT/${name}_payload.img"
        echo "payload $name: $(file -b "$OUT/${name}_payload.img" | cut -d, -f1)"
    else
        rm -f "$OUT/${name}_payload.img"
        echo "payload $name: not in the image (the host's module stays)"
    fi
done

# OneOS inside the guest (app-android/guest): "Back to One UI" from its screen
# or its Quick Settings tile. guest_prepare.sh puts it in every guest's /oem as
# app/OneOSGuest/OneOSGuest.apk, from $STAGE/OneOSGuest.apk. The release build,
# signed with the OneOS key: cd app-android && ./gradlew :guest:assembleRelease
GUEST_APK=$(ls "$ROOT"/app-android/guest/build/outputs/apk/release/*.apk 2>/dev/null | head -1)
ONEOS_CERT=37560f7ba9e82a7977c239b77a47c7fa6df0f381cdad44810ffdcab12295f83a
if [ -z "$GUEST_APK" ]; then
    rm -f "$OUT/OneOSGuest.apk"
    echo "OneOS guest app not built (app-android: ./gradlew :guest:assembleRelease): no OneOSGuest.apk copied"
elif ! "$BT/apksigner" verify --print-certs "$GUEST_APK" 2>/dev/null | grep -q "certificate SHA-256 digest: $ONEOS_CERT"; then
    rm -f "$OUT/OneOSGuest.apk"
    echo "$GUEST_APK is not signed with the OneOS release key: not copied" >&2
    exit 1
else
    cp -f "$GUEST_APK" "$OUT/OneOSGuest.apk"
    echo "copied $GUEST_APK to $OUT/OneOSGuest.apk (OneOS app in the guest)"
fi

# Google Play services for a Pixel guest (docs/pixel-guest.md, "Google
# services"). Pixel 17 ships GmsCore only inside the product APEX
# /system/product/apex/com.google.android.gmssystem*.apex, which the phone's
# apexd never activates, so the guest's package manager never scanned it
# ("Missing required system package: com.google.android.gms", runs 40-42). Its
# payload (EROFS, ~155 MB: the GmsCore APK and two XMLs) is staged here;
# guest_prepare.sh loop-mounts it at the guest's /apex/com.google.android.gmssystem
# and presents the APK as a plain product priv-app (ONEOS_GUEST_GMS, default on).
# Staged only when exactly one priv-app/PrebuiltGmsCore*/PrebuiltGmsCore*.apk is
# inside and it is com.google.android.gms; deploy-phone.sh pushes it like the
# other payloads.
EXTRACT_EROFS=${EXTRACT_EROFS:-$ROOT/mysticgsi/tools/bin/Linux/x86_64/extract.erofs}
GMSAPEX=$("$DEBUGFS" -R "ls -p /system/product/apex" "$IMG" 2>/dev/null |
    awk -F/ '$6 ~ /^com\.google\.android\.gmssystem.*\.apex$/ { print $6; exit }')
# Pixel's layout: its product PrebuiltGmsCore folder (app_chimera) waiting for
# the APK; vivo OriginOS 17's: product priv-app/GmsCore with only GmsCore's m
# folder (guest_prepare.sh presents the APK in whichever the image has). The
# ColorOS images carry the same APEX but their own GmsCore in my_product/priv-app,
# and neither folder.
if [ -n "$GMSAPEX" ] && { in_image /my_product/priv-app/GmsCore ||
        ! { in_image /system/product/priv-app/PrebuiltGmsCore/app_chimera || in_image /system/product/priv-app/GmsCore/m; }; }; then
    echo "payload gmssystem: $GMSAPEX is there but in neither Pixel's nor vivo's layout (no product PrebuiltGmsCore/app_chimera or GmsCore/m, or its own GmsCore in my_product): none staged"
    GMSAPEX=""
fi
GP="$OUT/gmssystem_payload.img"
rm -f "$GP"
if [ -z "$GMSAPEX" ]; then
    echo "payload gmssystem: no /system/product/apex/com.google.android.gmssystem*.apex in the image, none staged (no Google services from an APEX)"
else
    [ -x "$EXTRACT_EROFS" ] || { echo "payload gmssystem: $EXTRACT_EROFS missing, cannot check the payload" >&2; exit 1; }
    rm -f "$WORK/g.apex" "$WORK/g.capex"
    "$DEBUGFS" -R "dump /system/product/apex/$GMSAPEX $WORK/g.capex" "$IMG" 2>/dev/null
    [ -s "$WORK/g.capex" ] || { echo "payload gmssystem: could not dump /system/product/apex/$GMSAPEX" >&2; exit 1; }
    # Compressed (original_apex inside) or a plain APEX, as above.
    if unzip -l "$WORK/g.capex" original_apex >/dev/null 2>&1; then
        unzip -p "$WORK/g.capex" original_apex > "$WORK/g.apex"
        rm -f "$WORK/g.capex"
    else
        mv "$WORK/g.capex" "$WORK/g.apex"
    fi
    unzip -p "$WORK/g.apex" apex_payload.img > "$GP"
    rm -f "$WORK/g.apex"
    # The APK guest_prepare.sh binds. EROFS (Pixel's) or ext4, which
    # guest_prepare.sh's mount_payload tells apart by the same magic.
    GMS_FS=ext4
    if [ "$(od -An -tx4 -j1024 -N4 "$GP" | tr -d ' ')" = e0f5e1e2 ]; then
        GMS_FS=erofs
        GMS_IN=$("$EXTRACT_EROFS" -i "$GP" -p 2>/dev/null |
            sed -n 's#.*type=FILE .*fsConfig=\[/\(priv-app/PrebuiltGmsCore[^/ ]*/PrebuiltGmsCore[^/ ]*\.apk\) .*#\1#p')
    else
        GMS_IN=""
        for d in $("$DEBUGFS" -R "ls -p /priv-app" "$GP" 2>/dev/null | awk -F/ '$6 ~ /^PrebuiltGmsCore/ { print $6 }'); do
            GMS_IN="$GMS_IN $("$DEBUGFS" -R "ls -p /priv-app/$d" "$GP" 2>/dev/null |
                awk -F/ -v d="$d" '$6 ~ /^PrebuiltGmsCore.*\.apk$/ { print "priv-app/" d "/" $6 }')"
        done
    fi
    GMS_N=$(echo $GMS_IN | wc -w)
    if [ "$GMS_N" != 1 ]; then
        rm -f "$GP"
        echo "payload gmssystem: $GMSAPEX has $GMS_N PrebuiltGmsCore APKs in its payload (one expected): none staged, no Google services in the guest"
    else
        # Its package name and version, from the APK itself.
        rm -rf "$WORK/gx" && mkdir -p "$WORK/gx"
        if [ "$GMS_FS" = erofs ]; then
            (cd "$WORK/gx" && "$EXTRACT_EROFS" -i "$GP" -X "/$GMS_IN" -o "$WORK/gx" -s >/dev/null 2>&1) || true
        else
            "$DEBUGFS" -R "dump /$GMS_IN $WORK/gx/g.apk" "$GP" 2>/dev/null || true
        fi
        GX=$(find "$WORK/gx" -type f -name '*.apk' | head -1)
        GMS_APK_SIZE=""; GMS_BADGING=""
        if [ -n "$GX" ]; then
            GMS_APK_SIZE=$(stat -c %s "$GX")
            GMS_BADGING=$("$BT/aapt2" dump badging "$GX" 2>/dev/null | sed -n '1s/^package: //p')
        fi
        rm -rf "$WORK/gx"
        case "$GMS_BADGING" in
            "name='com.google.android.gms' "*) ;;
            *) rm -f "$GP"
               echo "payload gmssystem: $GMS_IN in $GMSAPEX is not GmsCore (${GMS_BADGING:-unreadable}): none staged" >&2
               exit 1 ;;
        esac
        echo "payload gmssystem: from /system/product/apex/$GMSAPEX ($GMS_FS, $(stat -c %s "$GP") bytes)"
        echo "payload gmssystem: $GMS_IN, $GMS_APK_SIZE bytes, $(echo "$GMS_BADGING" | cut -d' ' -f1-2)"
    fi
fi

# vivo's Wi-Fi code on One UI's connectivity module (patches/vivo_wifi_connectivity.py):
# a wifi APEX of vivo's own (OriginOS 6 CN) loads vivo-service-wifi.jar into
# system_server, and vivo-service-wifi-ex.jar loads vivo-service-wifi-ex-impl.jar.
# Both use transport 11 (vivo's second Wi-Fi), which only vivo's CN tethering
# module knows; the guest keeps One UI's, which refuses it: system_server died
# making WifiService (first CN run). vivo-service-wifi.jar also calls five methods
# only vivo's CN connectivity module has (the only such calls in the boot and
# system_server class paths). guest_prepare.sh binds both over the image's.
# A jar the patcher does not recognise fails the build: the guest would not boot.
rm -f "$OUT/vivo-service-wifi_patched.jar" "$OUT/vivo-service-wifi-ex-impl_patched.jar"
[ ! -f "$OUT/wifi_payload.img" ] || "$DEBUGFS" -R "dump /javalib/vivo-service-wifi.jar $WORK/vivo-service-wifi.jar" "$OUT/wifi_payload.img" 2>/dev/null
VWI=/system/framework/vivo-service-wifi-ex-impl.jar
if in_image $VWI; then
    "$DEBUGFS" -R "dump $VWI $WORK/vivo-service-wifi-ex-impl.jar" "$IMG" 2>/dev/null
fi
for VW in vivo-service-wifi:wifi vivo-service-wifi-ex-impl:impl; do
    VWN=${VW%%:*}; VWM=${VW#*:}
    [ -s "$WORK/$VWN.jar" ] || continue
    unzip -p "$WORK/$VWN.jar" 'classes*.dex' | grep -aq "addTransportType" || { echo "$VWN.jar: no transport requests, not patched"; continue; }
    rm -rf "$WORK/vw" "$WORK/vw-rebuilt.jar"
    java -jar "$APKTOOL" d -q -f -r -o "$WORK/vw" "$WORK/$VWN.jar"
    DIRS=$(python3 -I "$ROOT/switcher/patches/vivo_wifi_connectivity.py" "$WORK/vw" "$VWM")
    java -jar "$APKTOOL" b -q -o "$WORK/vw-rebuilt.jar" "$WORK/vw"
    cp "$WORK/$VWN.jar" "$WORK/${VWN}_patched.jar"
    for d in $DIRS; do
        DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
        rm -rf "$WORK/vdex" && mkdir -p "$WORK/vdex"
        unzip -q -o "$WORK/vw-rebuilt.jar" "$DEX" -d "$WORK/vdex"
        (cd "$WORK/vdex" && zip -q -0 "$WORK/${VWN}_patched.jar" "$DEX")
        echo "built $OUT/${VWN}_patched.jar (replaced $DEX)"
    done
    python3 -I "$ROOT/scripts/check-dex.py" "$WORK/${VWN}_patched.jar"
    mv -f "$WORK/${VWN}_patched.jar" "$OUT/${VWN}_patched.jar"
    chmod 644 "$OUT/${VWN}_patched.jar"
    rm -rf "$WORK/vw" "$WORK/vw-rebuilt.jar" "$WORK/vdex" "$WORK/$VWN.jar"
done

# vivo's Wi-Fi traffic counters (framework-wifi.jar of vivo's wifi APEX, on the boot
# class path): VivoTrafficStats' natives read the network stats BPF maps with the
# layout of vivo's CN connectivity module; the maps are One UI's, and the library
# aborted system_server (fourth CN run). patches/vivo_traffic_stats.py takes vivo's
# overseas path (no native reads). guest_prepare.sh binds it with the jars above.
rm -f "$OUT/framework-wifi_patched.jar"
rm -f "$WORK/framework-wifi.jar"
[ ! -f "$OUT/wifi_payload.img" ] || "$DEBUGFS" -R "dump /javalib/framework-wifi.jar $WORK/framework-wifi.jar" "$OUT/wifi_payload.img" 2>/dev/null
if [ -s "$WORK/framework-wifi.jar" ] && unzip -p "$WORK/framework-wifi.jar" 'classes*.dex' | grep -aq "Landroid/net/wifi/VivoTrafficStats;"; then
    rm -rf "$WORK/fw" "$WORK/fw-rebuilt.jar"
    java -jar "$APKTOOL" d -q -f -r -o "$WORK/fw" "$WORK/framework-wifi.jar"
    DIRS=$(python3 -I "$ROOT/switcher/patches/vivo_traffic_stats.py" "$WORK/fw")
    java -jar "$APKTOOL" b -q -o "$WORK/fw-rebuilt.jar" "$WORK/fw"
    cp "$WORK/framework-wifi.jar" "$WORK/framework-wifi_patched.jar"
    for d in $DIRS; do
        DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
        rm -rf "$WORK/vdex" && mkdir -p "$WORK/vdex"
        unzip -q -o "$WORK/fw-rebuilt.jar" "$DEX" -d "$WORK/vdex"
        (cd "$WORK/vdex" && zip -q -0 "$WORK/framework-wifi_patched.jar" "$DEX")
        echo "built $OUT/framework-wifi_patched.jar (replaced $DEX)"
    done
    python3 -I "$ROOT/scripts/check-dex.py" "$WORK/framework-wifi_patched.jar"
    mv -f "$WORK/framework-wifi_patched.jar" "$OUT/framework-wifi_patched.jar"
    chmod 644 "$OUT/framework-wifi_patched.jar"
    rm -rf "$WORK/fw" "$WORK/fw-rebuilt.jar" "$WORK/vdex"
fi
rm -f "$WORK/framework-wifi.jar"

# vivo's device type for the display and input side only (fold mode 2): system_server's
# input (libinputflinger, libinputservice) and libandroid_servers read
# ro.vivo.device.type natively, as SurfaceFlinger does (above); they read
# ro.oneos.vivo.dtype instead (same length; guest_props.sh), so apps keep "phone".
for VL in libinputflinger libinputservice libandroid_servers; do
    rm -f "$OUT/${VL}_patched.so" "$WORK/$VL.so"
    in_image /system/framework/vivo-services.jar || continue
    "$DEBUGFS" -R "dump /system/lib64/$VL.so $WORK/$VL.so" "$IMG" 2>/dev/null
    [ -s "$WORK/$VL.so" ] || continue
    python3 -I - "$WORK/$VL.so" "$OUT/${VL}_patched.so" <<'PYEOF'
import os, sys
src, dst = sys.argv[1], sys.argv[2]
d = open(src, "rb").read()
VT, VN = b"ro.vivo.device.type\0", b"ro.oneos.vivo.dtype\0"
n = d.count(VT)
if n == 0:
    print("%s: does not read ro.vivo.device.type, the image's runs" % os.path.basename(src))
    sys.exit(0)
if n != 1 or VN in d:
    sys.exit("%s: ro.vivo.device.type %d times, not patching" % (os.path.basename(src), n))
open(dst, "wb").write(d.replace(VT, VN))
print("built %s (reads ro.oneos.vivo.dtype for vivo's device type)" % dst)
PYEOF
    [ ! -f "$OUT/${VL}_patched.so" ] || chmod 644 "$OUT/${VL}_patched.so"
    rm -f "$WORK/$VL.so"
done

# vivo's Bluetooth stack (MediaTek's, in vivo's bt APEX) on Samsung's Qualcomm
# controller: libbluetooth_jni.so reads ro.vivo.product.platform (MTK6993) for four
# MediaTek-controller features, among them vivo's BLR vendor command in gatt_init
# (0xfc51) and MediaTek's quality report: the controller answered "unknown command",
# and the stack crashed in HciLayer at every Bluetooth start (tenth CN run: five times
# in 13 s). It reads ro.oneos.btchip.platform instead (same length, never set), the
# not-MediaTek path. guest_prepare.sh binds it on the guest's bt APEX.
rm -f "$OUT/libbluetooth_jni_patched.so" "$WORK/libbluetooth_jni.so"
if in_image /system/framework/vivo-services.jar && [ -f "$OUT/bt_payload.img" ]; then
    "$DEBUGFS" -R "dump /lib64/libbluetooth_jni.so $WORK/libbluetooth_jni.so" "$OUT/bt_payload.img" 2>/dev/null
    if [ -s "$WORK/libbluetooth_jni.so" ]; then
        python3 -I - "$WORK/libbluetooth_jni.so" "$OUT/libbluetooth_jni_patched.so" <<'PYEOF'
import sys
src, dst = sys.argv[1], sys.argv[2]
d = open(src, "rb").read()
VT, VN = b"ro.vivo.product.platform\0", b"ro.oneos.btchip.platform\0"
n = d.count(VT)
if n == 0:
    print("libbluetooth_jni: no ro.vivo.product.platform, the image's runs")
    sys.exit(0)
if n != 1 or VN in d:
    sys.exit("libbluetooth_jni: ro.vivo.product.platform %d times, not patching" % n)
open(dst, "wb").write(d.replace(VT, VN))
print("built %s (Bluetooth without MediaTek's controller features)" % dst)
PYEOF
        [ ! -f "$OUT/libbluetooth_jni_patched.so" ] || chmod 644 "$OUT/libbluetooth_jni_patched.so"
    fi
    rm -f "$WORK/libbluetooth_jni.so"
fi

# vivo's brightness on a bar phone's tables (patches/vivo_brightness.py): vivo-
# framework.jar (boot class path) takes "unfolded" brightness tables whenever the
# device state is above 0, which a phone build does not have (ninth CN run:
# system_server died in BaseNitCurve.calcNitBrightnessUnFold with automatic
# brightness on). Phone builds only (ro.vivo.device.type=phone in the image).
rm -f "$OUT/vivo-framework_patched.jar"
if in_image /system/framework/vivo-framework.jar &&
   "$DEBUGFS" -R "cat /system/build.prop" "$IMG" 2>/dev/null | grep -qx 'ro.vivo.device.type=phone'; then
    "$DEBUGFS" -R "dump /system/framework/vivo-framework.jar $WORK/vivo-framework.jar" "$IMG" 2>/dev/null
    rm -rf "$WORK/vf" "$WORK/vf-rebuilt.jar"
    java -jar "$APKTOOL" d -q -f -r -o "$WORK/vf" "$WORK/vivo-framework.jar"
    DIRS=$(python3 -I "$ROOT/switcher/patches/vivo_brightness.py" "$WORK/vf")
    # vivo's secure TEE (sectee) and other vivo vendor HALs: no endless wait (vivo_no_wait.py).
    NEW=$(python3 -I "$ROOT/switcher/patches/vivo_no_wait.py" "$WORK/vf")
    DIRS=$(printf '%s\n' $DIRS $NEW | sort -u)
    java -jar "$APKTOOL" b -q -o "$WORK/vf-rebuilt.jar" "$WORK/vf"
    cp "$WORK/vivo-framework.jar" "$WORK/vivo-framework_patched.jar"
    for d in $DIRS; do
        DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
        rm -rf "$WORK/vdex" && mkdir -p "$WORK/vdex"
        unzip -q -o "$WORK/vf-rebuilt.jar" "$DEX" -d "$WORK/vdex"
        (cd "$WORK/vdex" && zip -q -0 "$WORK/vivo-framework_patched.jar" "$DEX")
        echo "built $OUT/vivo-framework_patched.jar (replaced $DEX)"
    done
    python3 -I "$ROOT/scripts/check-dex.py" "$WORK/vivo-framework_patched.jar"
    mv -f "$WORK/vivo-framework_patched.jar" "$OUT/vivo-framework_patched.jar"
    chmod 644 "$OUT/vivo-framework_patched.jar"
    rm -rf "$WORK/vf" "$WORK/vf-rebuilt.jar" "$WORK/vdex" "$WORK/vivo-framework.jar"
fi

# vivo's feature list (patches/vivo_guards.py framework: VivoConfigStoreHelper reads
# /data/system/oneos_vivo_features, guest_prepare.sh copies this file there): vivo's
# config store HAL is vivo's vendor's, so without it every vivo feature read as off
# (tenth CN run: 54 617 failed lookups in 12 minutes; launcher, Themes, wallpaper
# features missing). From the vendor's vivo_config.ini (VIVO_CONFIG_INI, default
# the CN OTA's out/originos-cn/vendor_cfg/vendor/etc/vivo_config.ini). Features that
# drive vivo hardware or vendor code a Samsung phone lacks stay off (listed in the
# file's first line).
rm -f "$OUT/oneos-vivo-features.txt"
VCI=${VIVO_CONFIG_INI:-$ROOT/out/originos-cn/vendor_cfg/vendor/etc/vivo_config.ini}
if in_image /system/framework/vivo-services.jar && [ -r "$VCI" ]; then
    # vivo's native code (SurfaceFlinger and others) asks vivo's config store HAL
    # itself, which is missing: those features read as off there. Kept off in this
    # list too, or Java and native disagree (eleventh CN run: brightness stuck,
    # vivo.software.brightness.unified_mapping on for system_server's LCM controller,
    # which then waited for SurfaceFlinger to load the panel's tables; SurfaceFlinger
    # read it off and never did). Names from the system binaries that use the store.
    : > "$WORK/vivo-native-features.txt"
    for d in /system/bin /system/bin/hw /system/lib64 /system/system_ext/bin /system/system_ext/lib64; do
        for f in $("$DEBUGFS" -R "ls -p $d" "$IMG" 2>/dev/null | awk -F/ '$3 ~ /^1/ {print $6}'); do
            "$DEBUGFS" -R "dump $d/$f $WORK/vnf" "$IMG" 2>/dev/null
            # A binary may use the store without naming a feature (no match is no
            # error: set -e ended the 11th CN set's build here).
            if grep -aq "vendor.vivo.hardware.configstore" "$WORK/vnf" 2>/dev/null; then
                strings -n 8 "$WORK/vnf" | { grep -E '^vivo\.[a-z0-9_.]+$' || :; } >> "$WORK/vivo-native-features.txt"
            fi
        done
    done
    rm -f "$WORK/vnf"
    python3 -I - "$VCI" "$OUT/oneos-vivo-features.txt" "$WORK/vivo-native-features.txt" <<'PYEOF'
import re, sys
src, dst, nat = sys.argv[1], sys.argv[2], sys.argv[3]
NATIVE = set(l.strip() for l in open(nat) if l.strip())
OFF = re.compile(r"^vivo\.hardware\.|vblurnpu|\bnpu\b|\bapu\b|sdr2hdr|\bhdr|lcm|dimming|polarizer|\.ir\.|motor|audio|wifi|charg|camera|"
                 r"fingerprint|face|modem|radio|sensor|hall|\.tp|tpincoming|nfc|gnss|gps|vibrat|thermal|gpu|hwc|composer|dsp|bluetooth|\.bt\b")
pairs, off, sec = [], [], None
for line in open(src, encoding="utf-8", errors="replace"):
    line = line.strip()
    if not line or line.startswith(("#", ";")):
        continue
    m = re.fullmatch(r"\[([^\]]+)\]", line)
    if m:
        sec = m.group(1).strip()
        if OFF.search(sec) or sec in NATIVE:
            off.append(sec + ("(native)" if sec in NATIVE and not OFF.search(sec) else "")); sec = None
        else:
            pairs.append(sec + "$vivo-support")
        continue
    if sec is None or "=" not in line:
        continue
    k, v = line.split("=", 1)
    pairs.append(sec + ":" + k.strip() + "$" + v.strip())
bad = [p for p in pairs if p.count("$") != 1 or "&" in p]
if bad:
    sys.exit("oneos-vivo-features: '$' or '&' in %s" % bad[:3])
with open(dst, "w") as f:
    f.write("&".join(pairs) + "\n")
print("built %s (%d features on, %d off: %s)" % (dst, sum(p.endswith("$vivo-support") for p in pairs), len(off), " ".join(off)))
PYEOF
    chmod 644 "$OUT/oneos-vivo-features.txt"
elif in_image /system/framework/vivo-services.jar; then
    echo "oneos-vivo-features: no readable vivo_config.ini ($VCI): vivo's features stay off"
fi

# The guest's own APEX payloads run on One UI's /linkerconfig (guest_prepare.sh
# binds it), whose namespaces are linked from One UI's APEX manifests. Where the
# image's module needs more (OriginOS CN: vivo's wifi APEX needs libnativehelper.so
# for libvivowifi-service.so; third CN run: UnsatisfiedLinkError, system_server
# died), guest_prepare.sh adds those links in a guest-only copy of ld.config.txt.
# This table is each staged payload's requireNativeLibs: "<apex> <namespace> <lib>...".
rm -f "$OUT/oneos-apex-requires.txt"
for p in "$OUT"/*_payload.img; do
    [ -f "$p" ] || continue
    rm -f "$WORK/m.pb"
    "$DEBUGFS" -R "dump /apex_manifest.pb $WORK/m.pb" "$p" 2>/dev/null || true
    [ -s "$WORK/m.pb" ] || continue
    python3 -I - "$WORK/m.pb" >> "$OUT/oneos-apex-requires.txt" <<'PYEOF'
import sys
b = open(sys.argv[1], "rb").read()
def varint(i):
    r = s = 0
    while True:
        x = b[i]; i += 1; r |= (x & 0x7f) << s; s += 7
        if x < 0x80:
            return r, i
i, f = 0, {}
while i < len(b):
    k, i = varint(i)
    n, w = k >> 3, k & 7
    if w == 0:
        v, i = varint(i)
    elif w == 2:
        l, i = varint(i); v = b[i:i + l]; i += l
    elif w == 1:
        v = b[i:i + 8]; i += 8
    elif w == 5:
        v = b[i:i + 4]; i += 4
    else:
        sys.exit("apex_manifest.pb: wire type %d" % w)
    f.setdefault(n, []).append(v)
# ApexManifest: 1 name, 8 requireNativeLibs
name = f[1][0].decode()
req = [x.decode() for x in f.get(8, [])]
if req:
    print(name, name.replace(".", "_"), " ".join(req))
PYEOF
done
[ -s "$OUT/oneos-apex-requires.txt" ] && echo "built $OUT/oneos-apex-requires.txt ($(wc -l < "$OUT/oneos-apex-requires.txt") payloads with native requirements)" || rm -f "$OUT/oneos-apex-requires.txt"

# Calls into OneOS's helper classes must reach methods the jar defines: a patcher
# that overwrote another's helper (eleventh CN run: OneOSVivoFeatures.listed gone,
# the zygote died at boot) fails the build here instead of on the phone.
RJ=""
for j in "$OUT"/*_patched.jar "$OUT"/oneos-telephony.jar; do [ -f "$j" ] && RJ="$RJ $j"; done
[ -z "$RJ" ] || python3 -I "$ROOT/scripts/check-oneos-refs.py" "$BT/dexdump" $RJ
