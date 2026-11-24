#!/bin/sh
# OneOSRcdCorners.apk (switcher/overlays/s24fe_rcd_corners, pull request #355): ColorOS's hardware rounded-corner
# artwork (oplus_rc_*) for the Galaxy S24 FE's DISPLAY_DECORATION layer, a static overlay of the "oplus" package
# with no code (hasCode=false). guest_prepare.sh installs it only on that phone.
# Usage: scripts/build-rcd-corners-rro.sh [<out.apk>]   (default switcher/assets/OneOSRcdCorners.apk)
set -e
R=$(cd "$(dirname "$0")/.." && pwd); OUT=$(realpath -m "${1:-$R/switcher/assets/OneOSRcdCorners.apk}")
SDK=${ANDROID_HOME:-/opt/android-sdk}; BT=$(ls -d "$SDK"/build-tools/* | sort -V | tail -1)
AJ=$(ls "$SDK"/platforms/*/android.jar | sort -V | tail -1)
RRO=$R/switcher/overlays/s24fe_rcd_corners; W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
"$BT/aapt2" compile --dir "$RRO/res" -o "$W/res.zip"
"$BT/aapt2" link -o "$W/u.apk" -I "$AJ" --manifest "$RRO/AndroidManifest.xml" --min-sdk-version 31 --target-sdk-version 36 "$W/res.zip"
"$BT/zipalign" -p -f 4 "$W/u.apk" "$W/a.apk"
"$BT/apksigner" sign --ks "${KEYSTORE:-$HOME/.android/debug.keystore}" --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android --out "$OUT" "$W/a.apk"
rm -f "$OUT.idsig"
echo "built $OUT"
