#!/bin/sh
# Keep a patched services.jar in the guest's own data so a fixes update cannot
# defeat the guest-local PIN or the AIDL fingerprint transport. The update
# replaces $STAGE/services_patched.jar with upstream's build, which has neither
# the PIN verifier nor the AIDL sensor forcing: /data/system/oneos_pin stays in
# place but cannot be entered, and ColorOS asks for the absent HIDL 2.1
# fingerprint HAL ("Fingerprint HAL not available").
#
# The patched copy is stamped with the sha256 of the stage jar it was built
# from. guest_prepare.sh binds it only while that stamp matches the current
# stage jar, so a new fixes build falls back to the stock jar instead of
# running an old guard set.
#
# Usage: [APKTOOL="java -jar apktool.jar"] scripts/install-pin-jar.sh [--jar <services_patched.jar>] [--no-push]
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
STAGE=/data/local/tmp/oneos
PIN_DIR="$STAGE/data/local/tmp/oneos_pin"
SERIAL=${ANDROID_SERIAL:-}
ADB=${ADB:-adb}
jar=
push=1

while [ $# -gt 0 ]; do
    case "$1" in
        --jar) [ $# -ge 2 ] || { echo "usage: $0 [--jar <services_patched.jar>] [--no-push]" >&2; exit 2; }; jar=$2; shift 2 ;;
        --no-push) push=0; shift ;;
        -h|--help) sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "usage: $0 [--jar <services_patched.jar>] [--no-push]" >&2; exit 2 ;;
    esac
done

adb_() { if [ -n "$SERIAL" ]; then "$ADB" -s "$SERIAL" "$@"; else "$ADB" "$@"; fi; }
su_() { adb_ shell "su -c '$*'"; }

mkdir -p "$root/out"
if [ -z "$jar" ]; then
    jar="$root/out/services_patched_stage.jar"
    echo "pulling $STAGE/services_patched.jar" >&2
    adb_ exec-out su -c "cat $STAGE/services_patched.jar" > "$jar"
fi
[ -s "$jar" ] || { echo "no jar: $jar" >&2; exit 1; }

base=$(sha256sum "$jar" | awk '{print $1}')
out="$root/out/services_pin.jar"
step="$root/out/services_pin.step.jar"
echo "patching $jar ($base): AIDL fingerprint, then the PIN verifier" >&2
APKTOOL=${APKTOOL:-apktool}
APKTOOL="$APKTOOL" sh "$root/scripts/patch-built-jar.sh" "$jar" \
    "$root/switcher/patches/guest_force_aidl_fingerprint.py" "$step"
APKTOOL="$APKTOOL" sh "$root/scripts/patch-built-jar.sh" "$step" \
    "$root/switcher/patches/guest_local_pin.py" "$out"
rm -f "$step"

unzip -p "$out" classes2.dex | grep -aq OneOsPin ||
    { echo "the rebuilt jar has no OneOsPin; refusing to stage it" >&2; exit 1; }
printf '%s\n' "$base" > "$root/out/services_pin.base.sha256"

[ "$push" = 1 ] || exit 0

[ "$(su_ id -u | tr -d '\r')" = 0 ] || { echo "no root on the phone (su -c id failed)" >&2; exit 1; }
adb_ push "$out" /data/local/tmp/services_pin.jar >/dev/null
adb_ push "$root/out/services_pin.base.sha256" /data/local/tmp/services_pin.base.sha256 >/dev/null
su_ "mkdir -p $PIN_DIR &&
     mv -f /data/local/tmp/services_pin.jar $PIN_DIR/services_patched.jar &&
     mv -f /data/local/tmp/services_pin.base.sha256 $PIN_DIR/base.sha256 &&
     chown root:root $PIN_DIR/services_patched.jar $PIN_DIR/base.sha256 &&
     chmod 644 $PIN_DIR/services_patched.jar $PIN_DIR/base.sha256 &&
     chcon -h u:object_r:system_file:s0 $PIN_DIR/services_patched.jar &&
     chcon -h u:object_r:system_data_file:s0 $PIN_DIR/base.sha256" >/dev/null
echo "kept $PIN_DIR/services_patched.jar (for $base); guest_prepare.sh binds it on the next switch" >&2
