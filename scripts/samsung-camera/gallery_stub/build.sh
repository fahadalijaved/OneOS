#!/bin/sh
# Build OneOSGalleryStub.apk (see AndroidManifest.xml) into <out dir>
# (default: switcher/assets).
# Usage: scripts/samsung-camera/gallery_stub/build.sh [<out dir>]
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
OUT="${1:-$ROOT/switcher/assets}"
SDK=${ANDROID_HOME:-/opt/android-sdk}
BT=$(ls -d "$SDK"/build-tools/* | sort -V | tail -1)
AJ=$(ls "$SDK"/platforms/*/android.jar | sort -V | tail -1)
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
mkdir -p "$W/classes" "$W/dex"
javac --release 17 -nowarn -cp "$AJ" -d "$W/classes" \
    "$HERE/src/oneos/samgallery/GalleryStubProvider.java" \
    "$HERE/src/com/samsung/android/gallery/app/activity/GalleryActivity.java"
"$BT/d8" --release --min-api 31 --lib "$AJ" --output "$W/dex" $(find "$W/classes" -name '*.class')
"$BT/aapt2" link -o "$W/stub.apk" -I "$AJ" --manifest "$HERE/AndroidManifest.xml" \
    --min-sdk-version 31 --target-sdk-version 36
(cd "$W/dex" && zip -0 -q -j "$W/stub.apk" classes.dex)
"$BT/zipalign" -p -f 4 "$W/stub.apk" "$W/aligned.apk"
"$BT/apksigner" sign --ks "$HOME/.android/debug.keystore" --ks-pass pass:android --ks-key-alias androiddebugkey \
    --key-pass pass:android --out "$OUT/OneOSGalleryStub.apk" "$W/aligned.apk"
rm -f "$OUT/OneOSGalleryStub.apk.idsig"
echo "built $OUT/OneOSGalleryStub.apk"
