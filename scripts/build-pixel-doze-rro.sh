#!/bin/sh
# OneOSPixelDoze.apk (switcher/overlays/pixel_doze): AOD for the Pixel guests, a static
# framework overlay guest_prepare.sh puts in the guest's /oem/overlay.
# Usage: scripts/build-pixel-doze-rro.sh <out.apk>
set -e
R=$(cd "$(dirname "$0")/.." && pwd); OUT=$(realpath -m "$1")
SDK=${ANDROID_HOME:-/opt/android-sdk}; BT=$(ls -d "$SDK"/build-tools/* | sort -V | tail -1)
AJ=$(ls -d "$SDK"/platforms/android-* | sort -V | tail -1)/android.jar
RRO=$R/switcher/overlays/pixel_doze; W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
"$BT/aapt2" compile --dir "$RRO/res" -o "$W/res.zip"
"$BT/aapt2" link -o "$W/u.apk" -I "$AJ" --manifest "$RRO/AndroidManifest.xml" --min-sdk-version 35 --target-sdk-version 36 --no-resource-deduping "$W/res.zip"
"$BT/zipalign" -p -f 4 "$W/u.apk" "$W/a.apk"
"$BT/apksigner" sign --ks "${KEYSTORE:-$HOME/.android/debug.keystore}" --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android --out "$OUT" "$W/a.apk"
rm -f "$OUT.idsig"
echo "built $OUT"
