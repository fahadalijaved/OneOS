#!/bin/sh
# Build the fingerprint-wave SystemUI APK and put it in the guest's
# /data/local/tmp. guest_start.sh binds it over the image's SystemUI on every
# guest boot, so the patch survives a guest restart without a host rebuild.
#
# The stock APK is needed once per ColorOS SystemUI build. Pass it with
# --stock, or leave it as out/SystemUI_stock.apk; without either the script
# pulls it from a running, unpatched guest and caches it there.
#
# Usage: [APKTOOL="java -jar apktool.jar"] scripts/install-systemui-wave.sh [--stock <apk>] [--no-push]
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
STAGE=/data/local/tmp/oneos
GUEST_TMP="$STAGE/data/local/tmp"
SERIAL=${ANDROID_SERIAL:-}
ADB=${ADB:-adb}
stock=
push=1

while [ $# -gt 0 ]; do
    case "$1" in
        --stock) [ $# -ge 2 ] || { echo "usage: $0 [--stock <apk>] [--no-push]" >&2; exit 2; }; stock=$2; shift 2 ;;
        --no-push) push=0; shift ;;
        -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "usage: $0 [--stock <apk>] [--no-push]" >&2; exit 2 ;;
    esac
done

adb_() { if [ -n "$SERIAL" ]; then "$ADB" -s "$SERIAL" "$@"; else "$ADB" "$@"; fi; }
su_() { adb_ shell "su -c '$*'"; }

if [ -z "$stock" ] && [ -f "$root/out/SystemUI_stock.apk" ]; then
    stock=$root/out/SystemUI_stock.apk
fi
if [ -z "$stock" ]; then
    echo "No stock APK; pulling the guest's SystemUI (it must be unpatched)." >&2
    mkdir -p "$root/out"
    stock="$root/out/SystemUI_stock.apk"
    adb_ exec-out su -c 'cat /system/system_ext/priv-app/SystemUI/SystemUI.apk' > "$stock"
fi
[ -f "$stock" ] || { echo "no such APK: $stock" >&2; exit 1; }

out="$root/out/SystemUI_wave.apk"
mkdir -p "$root/out"
APKTOOL=${APKTOOL:-apktool}
echo "building $out from $stock" >&2
APKTOOL="$APKTOOL" sh "$root/scripts/make-systemui-wave.sh" "$stock" "$out"
stock_size=$(stat -c %s "$stock")
stock_sha=$(sha256sum "$stock" | awk '{print $1}')
printf '%s\n' "$stock_size" > "$root/out/SystemUI_wave.stock.size"
printf '%s\n' "$stock_sha" > "$root/out/SystemUI_wave.stock.sha256"

[ "$push" = 1 ] || exit 0

[ "$(su_ id -u | tr -d '\r')" = 0 ] || { echo "no root on the phone (su -c id failed)" >&2; exit 1; }
adb_ push "$out" /data/local/tmp/SystemUI_wave.apk >/dev/null
adb_ push "$root/out/SystemUI_wave.stock.size" /data/local/tmp/SystemUI_wave.stock.size >/dev/null
adb_ push "$root/out/SystemUI_wave.stock.sha256" /data/local/tmp/SystemUI_wave.stock.sha256 >/dev/null
su_ "mkdir -p $GUEST_TMP &&
     mv -f /data/local/tmp/SystemUI_wave.apk $GUEST_TMP/SystemUI_wave.apk &&
     mv -f /data/local/tmp/SystemUI_wave.stock.size $GUEST_TMP/SystemUI_wave.stock.size &&
     mv -f /data/local/tmp/SystemUI_wave.stock.sha256 $GUEST_TMP/SystemUI_wave.stock.sha256 &&
     chown root:root $GUEST_TMP/SystemUI_wave.apk $GUEST_TMP/SystemUI_wave.stock.size $GUEST_TMP/SystemUI_wave.stock.sha256 &&
     chmod 644 $GUEST_TMP/SystemUI_wave.apk $GUEST_TMP/SystemUI_wave.stock.size $GUEST_TMP/SystemUI_wave.stock.sha256 &&
     chcon u:object_r:system_file:s0 $GUEST_TMP/SystemUI_wave.apk" >/dev/null
echo "staged $GUEST_TMP/SystemUI_wave.apk (applied by guest_start.sh on the next guest boot)" >&2

# Apply now only when the guest is running. Binding inside zygote's namespace
# is what makes it visible to the SystemUI that zygote will spawn.
if su_ "mount | grep -q $STAGE/rootfs"; then
    zygote=$(adb_ shell "su -c 'pidof zygote64'" | tr -d '\r')
    if [ -n "$zygote" ]; then
        su_ "nsenter -t $zygote -m -- mount -o bind /data/local/tmp/empty_oat /system/system_ext/priv-app/SystemUI/oat/arm64 2>/dev/null || true"
        if su_ "nsenter -t $zygote -m -- mount -o bind /data/local/tmp/SystemUI_wave.apk /system/system_ext/priv-app/SystemUI/SystemUI.apk"; then
            ui=$(adb_ shell "su -c 'pidof com.android.systemui'" | tr -d '\r')
            [ -z "$ui" ] || su_ "kill -9 $ui"
            echo "bound in the running guest; SystemUI restarted" >&2
        else
            echo "guest is running but the bind failed; it applies on the next boot" >&2
        fi
    fi
fi

@1033@
