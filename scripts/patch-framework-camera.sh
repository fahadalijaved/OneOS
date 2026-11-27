#!/bin/sh
# framework_patched.jar for a Pixel (AOSP) guest: the image's framework.jar
# with One UI's camera transaction codes (switcher/patches/pixel_camera_abi.py,
# table switcher/patches/host_camera.txt from scripts/aidl-table.py on One UI's
# framework.jar). Only the dex files the patcher changed are rebuilt; the rest
# of the jar is the image's, byte for byte (as make-overlays.sh does for the
# other jars). Nothing is written when the guest's tables already agree.
#
# Usage: scripts/patch-framework-camera.sh <framework.jar> <out dir>
#   writes <out dir>/framework_patched.jar (or removes it) and appends its
#   sha256 line to <out dir>/guards.txt when that file exists and lacks it.
# make-overlays.sh calls it for a Pixel image; for a set whose image is no
# longer on the server, call it with the jar pulled from the phone's stage.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
[ -f "$1" ] && [ -d "$2" ] || { echo "usage: $0 <framework.jar> <out dir>" >&2; exit 2; }
# Absolute paths: the zip step runs inside a temp dir.
JAR=$(cd "$(dirname "$1")" && pwd)/$(basename "$1"); OUT=$(cd "$2" && pwd)
APKTOOL=${APKTOOL:-$(ls "$ROOT"/mysticgsi/tools/apktool/*.jar /opt/homebrew/Cellar/apktool/*/libexec/*.jar 2>/dev/null | head -1)}
# CAMERA_TABLE: another host table (0.5.37: switcher/patches/host_camera_oneui95.txt for One UI 9.5 phones).
TABLE="${CAMERA_TABLE:-${HOST_CAMERA:-$ROOT/switcher/patches/host_camera.txt}}"
[ -f "$TABLE" ] || { echo "$TABLE missing (scripts/aidl-table.py on One UI's framework.jar)" >&2; exit 1; }
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
java -jar "$APKTOOL" d -q -f -r -o "$WORK/fw" "$JAR"
DIRS=$(python3 -I "$ROOT/switcher/patches/pixel_camera_abi.py" "$WORK/fw" "$TABLE")
# ColorOS (extendGetComponentName) and HyperOS ("<package>&<activity>"): the
# app's package name, not a component, for One UI's cameraserver
# (switcher/patches/coloros_camera_client.py, 0.4.37). AOSP has neither site.
CM=$(find "$WORK/fw" -path '*/android/hardware/camera2/CameraManager.smali' | head -1)
if [ -n "$CM" ] && grep -q -e 'ICameraManagerExt;->extendGetComponentName' -e '^ *const-string v[0-9]*, "&"$' "$CM"; then
    python3 -I "$ROOT/switcher/patches/coloros_camera_client.py" "$WORK/fw"
    d=${CM#"$WORK/fw/"}; d=${d%%/*}
    case " $DIRS " in *" $d "*) ;; *) DIRS="$DIRS $d" ;; esac
fi
# Samsung IMS's framework additions as OneOS stand-ins (switcher/patches/
# guest_secims_members.py, 0.4.38): only what the guest's classes lack.
SD=$(python3 -I "$ROOT/switcher/patches/guest_secims_members.py" "$WORK/fw")
for d in $SD; do
    case " $DIRS " in *" $d "*) ;; *) DIRS="$DIRS $d" ;; esac
done
# Samsung IMS hears that telephony is ready for a call's callbacks once telephony
# attaches to the session (switcher/patches/guest_secims_ready.py, 0.5.01): without
# it the end of a call never reached the guest (Z Fold8 Pixel, 4bb83bcd).
RD=$(python3 -I "$ROOT/switcher/patches/guest_secims_ready.py" "$WORK/fw")
for d in $RD; do
    case " $DIRS " in *" $d "*) ;; *) DIRS="$DIRS $d" ;; esac
done
# vivo OriginOS: its camera JSON cache without the 31 five-second waits for
# vivo's own camera service (switcher/patches/vivo_guards.py framework; the
# third OriginOS run's system_server was killed by its watchdog). Other
# frameworks lack the class and nothing changes.
VD=$(python3 -I "$ROOT/switcher/patches/vivo_guards.py" framework "$WORK/fw")
for d in $VD; do
    case " $DIRS " in *" $d "*) ;; *) DIRS="$DIRS $d" ;; esac
done
# Samsung providers may announce camera statuses in a non-numeric order. A few
# AOSP-derived frameworks carry Qualcomm's shouldExposeAuxCamera path; where it
# exists, filter IDs 0/1 rather than truncate the status map, or SystemUI can
# select a vendor ID (A15 Infinity-X chose 23) for the torch. Frameworks without
# that vendor path need no such patch.
ACM=$(find "$WORK/fw" -path '*/android/hardware/camera2/CameraManager$CameraManagerGlobal.smali' | head -1)
# ONEOS_CAMERA_NO_AUX_FILTER=1 leaves it out (0.5.37: a set built before it, LineageOS r10, rebuilt as it was).
if [ "${ONEOS_CAMERA_NO_AUX_FILTER:-0}" != 1 ] && [ -n "$ACM" ] && grep -Eq 'shouldExposeAuxCamera\(\)Z|CameraExtStub;->isAuxCameraClient' "$ACM"; then
    AD=$(python3 -I "$ROOT/switcher/patches/camera_aux_id_filter.py" "$WORK/fw")
    for d in $AD; do
        case " $DIRS " in *" $d "*) ;; *) DIRS="$DIRS $d" ;; esac
    done
fi
# Samsung Camera's slow motion: up to 4 outputs in a constrained high-speed session, as One UI's
# framework allows (switcher/patches/samsung_highspeed_surfaces.py, 0.5.15; A36 LineageOS froze on
# "size must be 1 or 2"). One UI's cameraserver takes the session.
HD=$(python3 -I "$ROOT/switcher/patches/samsung_highspeed_surfaces.py" "$WORK/fw")
for d in $HD; do
    case " $DIRS " in *" $d "*) ;; *) DIRS="$DIRS $d" ;; esac
done
if [ -z "$DIRS" ]; then
    rm -f "$OUT/framework_patched.jar"
    sed -i '/ framework_patched\.jar$/d' "$OUT/guards.txt" 2>/dev/null || true
    echo "framework_patched.jar: not needed (the guest's camera tables are One UI's)"
    exit 0
fi
# A patched framework.jar runs without the image's boot image, whose initialized classes had
# filled Android 17's device-policy registry (switcher/patches/policy_metadata_init.py; One UI 9.5,
# A36 run 6: DevicePolicyManagerService died at boot). Only when the jar is patched anyway.
PM=$(python3 -I "$ROOT/switcher/patches/policy_metadata_init.py" "$WORK/fw")
# One UI 9.5's Privacy Display flags are true at build time (the S26 Ultra's panel feature): off
# (switcher/patches/oneui_no_privacy_display.py; nothing on images without them).
PD=$(python3 -I "$ROOT/switcher/patches/oneui_no_privacy_display.py" "$WORK/fw") || exit 1
# One UI 9.5's engmode client off where the phone's VINTF lacks ISehEngmode/default (the S23 family):
# its callers waited forever, SetupWizard and system_server ANRs (switcher/patches/oneui_engmode_undeclared.py,
# set oneui95 r4; nothing on images without EngineeringModeManager).
ED=$(python3 -I "$ROOT/switcher/patches/oneui_engmode_undeclared.py" "$WORK/fw") || exit 1
for d in $PM $PD $ED; do
    case " $DIRS " in *" $d "*) ;; *) DIRS="$DIRS $d" ;; esac
done
java -jar "$APKTOOL" b -q -o "$WORK/fw-rebuilt.jar" "$WORK/fw"
cp "$JAR" "$OUT/framework_patched.jar"
for d in $DIRS; do
    DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
    rm -rf "$WORK/dex" && mkdir -p "$WORK/dex"
    unzip -q -o "$WORK/fw-rebuilt.jar" "$DEX" -d "$WORK/dex"
    (cd "$WORK/dex" && zip -q -0 "$OUT/framework_patched.jar" "$DEX")
    echo "built $OUT/framework_patched.jar (replaced $DEX)"
done
# A dex-container framework.jar (One UI 9.5) needs all rebuilt dex files; no class may go missing.
python3 -I "$ROOT/scripts/dex-container-fix.py" "$JAR" "$WORK/fw-rebuilt.jar" "$OUT/framework_patched.jar" || exit 1
chmod 644 "$OUT/framework_patched.jar"
python3 -I "$ROOT/scripts/check-dex.py" "$OUT/framework_patched.jar"
if [ -f "$OUT/guards.txt" ]; then
    sed -i '/ framework_patched\.jar$/d' "$OUT/guards.txt"
    (cd "$OUT" && sha256sum framework_patched.jar) >> "$OUT/guards.txt"
    echo "guards.txt: framework_patched.jar listed"
fi
