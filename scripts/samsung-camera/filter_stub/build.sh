#!/bin/sh
# Build OneOSSamFilterStub.apk (see AndroidManifest.xml) into <out dir>, the
# Samsung camera's staged set (scripts/samsung-camera/build.sh's output).
# Usage: scripts/samsung-camera/filter_stub/build.sh <out dir>
set -e
OUT="$1"; [ -n "$OUT" ] || { echo "usage: $0 <out dir>" >&2; exit 2; }
HERE=$(cd "$(dirname "$0")" && pwd)
BT=$(ls -d /opt/android-sdk/build-tools/* | sort | tail -1)
AJ=$(ls /opt/android-sdk/platforms/*/android.jar | sort | tail -1)
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
mkdir -p "$W/classes" "$W/dex"
javac -source 11 -target 11 -nowarn -bootclasspath "$AJ" -d "$W/classes" "$HERE"/src/oneos/samfilter/*.java 2>/dev/null ||
    javac --release 11 -cp "$AJ" -d "$W/classes" "$HERE"/src/oneos/samfilter/*.java
"$BT/d8" --min-api 35 --lib "$AJ" --output "$W/dex" $(find "$W/classes" -name '*.class')
"$BT/aapt2" link -o "$W/stub.apk" -I "$AJ" --manifest "$HERE/AndroidManifest.xml" \
    --min-sdk-version 35 --target-sdk-version 36
(cd "$W/dex" && zip -q -j "$W/stub.apk" classes.dex)
"$BT/zipalign" -p -f 4 "$W/stub.apk" "$W/aligned.apk"
"$BT/apksigner" sign --ks "$HOME/.android/debug.keystore" --ks-pass pass:android --ks-key-alias androiddebugkey \
    --key-pass pass:android --out "$OUT/OneOSSamFilterStub.apk" "$W/aligned.apk"
rm -f "$OUT/OneOSSamFilterStub.apk.idsig"
echo "built $OUT/OneOSSamFilterStub.apk"
