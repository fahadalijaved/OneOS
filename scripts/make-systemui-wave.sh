#!/bin/sh
# Build the fingerprint-wave SystemUI APK from a stock ColorOS SystemUI.apk.
# Usage: [APKTOOL="java -jar apktool.jar"] scripts/make-systemui-wave.sh [stock.apk] [out.apk]
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
patch_file="$root/switcher/patches/systemui-fingerprint-wave/systemui-fingerprint-wave.patch"
tested=0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77
stock=${1:-}
out=${2:-SystemUI_wave.apk}
apktool=${APKTOOL:-apktool}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

if [ -z "$stock" ]; then
    stock="$work/SystemUI.apk"
    echo "Pulling SystemUI.apk from the guest; it must be unpatched." >&2
    adb exec-out su -c 'cat /system/system_ext/priv-app/SystemUI/SystemUI.apk' > "$stock"
fi
[ -f "$stock" ] || { echo "no such APK: $stock" >&2; exit 1; }

got=$(sha256sum "$stock" | cut -d' ' -f1)
if [ "$got" != "$tested" ] && [ "${ONEOS_WAVE_ALLOW_OTHER:-0}" != 1 ]; then
    echo "SystemUI.apk sha256 is $got" >&2
    echo "tested build is $tested; set ONEOS_WAVE_ALLOW_OTHER=1 to try anyway" >&2
    exit 1
fi

$apktool d -f --no-res -o "$work/dec" "$stock" >/dev/null
patch -p1 -d "$work/dec" < "$patch_file"
$apktool b "$work/dec" -o "$work/rebuilt.apk" >/dev/null
unzip -o -q "$work/rebuilt.apk" classes3.dex -d "$work"
python3 "$root/scripts/apk-replace-dex.py" "$stock" classes3.dex "$work/classes3.dex" "$out"
sha256sum "$out"
