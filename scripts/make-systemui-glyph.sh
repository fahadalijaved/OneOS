#!/bin/sh
# Build SystemUI_glyph.apk for the Infinity-X set: the image's SystemUI (sha256 6a99684e..., the build vdcoolok's
# pull request #152 glyph was made on) with classes2.dex replaced: switcher/patches/systemui-guest-glyph/
# shade-hook.patch (his NotificationShadeWindowView hook) plus OneOSGlyphView.java (ours: the ring placed from
# ro.oneos.fp_glyph instead of the S25 Ultra's fixed numbers). Only classes2.dex is decoded and rebuilt.
# Usage: APKTOOL=apktool.jar scripts/make-systemui-glyph.sh <stock SystemUI.apk> <out.apk>
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
p="$root/switcher/patches/systemui-guest-glyph"
stock=$1; out=$2
sdk=${ANDROID_HOME:-/opt/android-sdk}; bt="$sdk/build-tools/${ONEOS_BUILD_TOOLS:-37.0.0}"; jar="$sdk/platforms/android-36/android.jar"
[ "$(sha256sum "$stock" | cut -c1-64)" = 6a99684e831f9635738189d39667debe0f8b798012fa4eb622a7cb87ad9b1ddf ] ||
    { echo "not the tested Infinity-X SystemUI" >&2; exit 1; }
w=$(mktemp -d); trap 'rm -rf "$w"' EXIT
mkdir -p "$w/cls" "$w/gdex" "$w/j2" "$w/jg"
javac --release 17 -cp "$jar" -d "$w/cls" "$p/OneOSGlyphView.java"
"$bt/d8" --min-api 34 --lib "$jar" --output "$w/gdex" $(find "$w/cls" -name '*.class')
unzip -p "$stock" classes2.dex > "$w/j2/classes.dex"; (cd "$w/j2" && zip -q ../c2.jar classes.dex)
cp "$w/gdex/classes.dex" "$w/jg/"; (cd "$w/jg" && zip -q ../g.jar classes.dex)
java -Xmx1800m -jar "$APKTOOL" d -f --no-res -o "$w/d2" "$w/c2.jar" >/dev/null
java -Xmx512m -jar "$APKTOOL" d -f --no-res -o "$w/dg" "$w/g.jar" >/dev/null
sed 's#smali_classes2/#smali/#g' "$p/shade-hook.patch" | patch -p1 --no-backup-if-mismatch -F0 -d "$w/d2"
mkdir -p "$w/d2/smali/com/oneos"; cp -r "$w/dg/smali/com/oneos/glyph" "$w/d2/smali/com/oneos/"
java -Xmx1800m -jar "$APKTOOL" b -o "$w/b2.jar" "$w/d2" >/dev/null
unzip -oq "$w/b2.jar" classes.dex -d "$w/n2"
python3 "$root/scripts/apk-replace-dex.py" "$stock" classes2.dex "$w/n2/classes.dex" "$out"
sha256sum "$out"
