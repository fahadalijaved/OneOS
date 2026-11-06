#!/bin/sh
# The double-tap-to-sleep helpers in Java (SystemUI's: dt2s/src; Pixel Launcher's:
# ../../pixel-launcher/src), compiled to the smali the APK builds add (dt2s/smali,
# ../../pixel-launcher/smali-add). Usage: build.sh
set -e
HERE=$(cd "$(dirname "$0")" && pwd); R=$(cd "$HERE/../../../.." && pwd)
SDK=${ANDROID_HOME:-/opt/android-sdk}; JAR=$(ls -d "$SDK"/platforms/android-* | sort -V | tail -1)/android.jar
BT=$(ls -d "$SDK"/build-tools/* | sort -V | tail -1); APKTOOL=$(ls "$R"/mysticgsi/tools/apktool/*.jar | head -1)
build() {  # $1 sources, $2 smali output (cleared), $3 package path
    W=$(mktemp -d)
    javac --release 17 -cp "$JAR" -d "$W/c" $(find "$1" -name '*.java')
    "$BT/d8" --min-api 34 --output "$W" $(find "$W/c" -name '*.class')
    (cd "$W" && zip -q h.apk classes.dex) && java -jar "$APKTOOL" d -q -r -f -o "$W/dec" "$W/h.apk"
    rm -rf "$2/$3"; mkdir -p "$2/$3"
    cp "$W"/dec/smali/$3/*.smali "$2/$3/"
    rm -rf "$W"
    ls "$2/$3"
}
build "$HERE/src" "$HERE/smali" oneos/sysui
build "$R/switcher/patches/pixel-launcher/src" "$R/switcher/patches/pixel-launcher/smali-add" oneos/launcher
