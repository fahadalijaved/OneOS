#!/bin/sh
# OneOSTabS9FeBrightness.apk (switcher/overlays/tab_s9_fe_brightness, pull request #371): the Galaxy Tab S9 FE's
# LCD brightness floor for One UI 9.5, a static overlay of the "android" package with no code (hasCode=false).
# guest_prepare.sh mounts it into the guest's product/overlay on that tablet only.
# Usage: scripts/build-tab-s9-fe-brightness-rro.sh [<out.apk>]   (default switcher/assets/OneOSTabS9FeBrightness.apk)
set -e
R=$(cd "$(dirname "$0")/.." && pwd); OUT=$(realpath -m "${1:-$R/switcher/assets/OneOSTabS9FeBrightness.apk}")
SDK=${ANDROID_HOME:-/opt/android-sdk}; BT=$(ls -d "$SDK"/build-tools/* | sort -V | tail -1)
AJ=$(ls "$SDK"/platforms/*/android.jar | sort -V | tail -1)
RRO=$R/switcher/overlays/tab_s9_fe_brightness; W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
"$BT/aapt2" compile --dir "$RRO/res" -o "$W/res.zip"
"$BT/aapt2" link -o "$W/u.apk" -I "$AJ" --manifest "$RRO/AndroidManifest.xml" --min-sdk-version 35 --target-sdk-version 36 "$W/res.zip"
"$BT/zipalign" -p -f 4 "$W/u.apk" "$W/a.apk"
"$BT/apksigner" sign --ks "${KEYSTORE:-$HOME/.android/debug.keystore}" --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android --out "$OUT" "$W/a.apk"
rm -f "$OUT.idsig"
echo "built $OUT"
