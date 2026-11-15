#!/bin/sh
# The camera helpers written in Java (src/), compiled to the smali the patchers copy (smali/):
# fix_recorder_progress.py (OneOSRecordProgress), fix_secmedia_insert.py (OneOSMedia),
# fix_gallery_fallback.py (OneOSGallery) and fix_a_series_resolution_lookup.py (OneOSResolution).
set -e
HERE=$(cd "$(dirname "$0")" && pwd); R=$(cd "$HERE/../../.." && pwd)
SDK=${ANDROID_HOME:-/opt/android-sdk}; JAR=$(ls -d "$SDK"/platforms/android-* | sort -V | tail -1)/android.jar
BT=$(ls -d "$SDK"/build-tools/* | sort -V | tail -1); APKTOOL=$(ls "$R"/mysticgsi/tools/apktool/*.jar | head -1)
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
javac --release 17 -cp "$JAR" -d "$W/c" $(find "$HERE/src" -name '*.java')
"$BT/d8" --min-api 30 --output "$W" $(find "$W/c" -name '*.class')
(cd "$W" && zip -q h.apk classes.dex) && java -jar "$APKTOOL" d -q -r -f -o "$W/dec" "$W/h.apk"
cp "$W"/dec/smali/oneos/camera/*.smali "$HERE/smali/"
ls "$HERE/smali"
