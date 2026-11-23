#!/bin/sh
# OneOSPixelCorners.apk (switcher/overlays/pixel_corners): PixelOS's screen corners at the phone's
# own radius, a static SystemUI overlay guest_prepare.sh puts in the guest's /oem/overlay.
# Its drawables reference @*android:dimen/rounded_corner_radius_top/_bottom by resource ID, so it
# is linked against the PixelOS image's own framework-res.apk; guest_prepare.sh installs it only
# when the guest's framework-res.apk has the sha256 printed here (PIXEL_CORNERS_FWR there).
# Usage: scripts/build-pixel-corners-rro.sh <pixelos framework-res.apk> <out.apk>
set -e
R=$(cd "$(dirname "$0")/.." && pwd); FWR=$(realpath "$1"); OUT=$(realpath -m "$2")
SDK=${ANDROID_HOME:-/opt/android-sdk}; BT=$(ls -d "$SDK"/build-tools/* | sort -V | tail -1)
RRO=$R/switcher/overlays/pixel_corners; W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
"$BT/aapt2" compile --dir "$RRO/res" -o "$W/res.zip"
"$BT/aapt2" link -o "$W/u.apk" -I "$FWR" --manifest "$RRO/AndroidManifest.xml" --min-sdk-version 35 --target-sdk-version 36 --no-resource-deduping "$W/res.zip"
"$BT/zipalign" -p -f 4 "$W/u.apk" "$W/a.apk"
"$BT/apksigner" sign --ks "${KEYSTORE:-$HOME/.android/debug.keystore}" --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android --out "$OUT" "$W/a.apk"
rm -f "$OUT.idsig"
echo "built $OUT for framework-res.apk sha256 $(sha256sum "$FWR" | cut -d' ' -f1)"
