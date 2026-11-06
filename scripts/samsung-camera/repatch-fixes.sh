#!/bin/sh
# A built samcam.tar whose SamsungCamera.apk gets one or more camera fixes (fix_*.py, each taking the
# decoded APK's smali root and printing the smali_* directories it changed), in the order given, for
# sets whose guest image is no longer on the server: decode the APK once, run the fixes, rebuild, put
# back only the dex files the fixes name (every other entry byte for byte), align and sign with the
# key build-cached.sh signs with. The other tar members are copied as they are, in the same order.
# (repatch-track-start.sh and repatch-gallery.sh are this with one fix.)
# Usage: repatch-fixes.sh <samcam.tar> <out samcam.tar> <fix.py> [<fix.py> ...]
set -e
TAR="$1"; OUT="$2"; shift 2 || true
[ -f "$TAR" ] && [ -n "$OUT" ] && [ $# -gt 0 ] || { echo "usage: $0 <samcam.tar> <out samcam.tar> <fix.py> [<fix.py> ...]" >&2; exit 2; }
R=/srv/projects/OneOS; HERE=$R/scripts/samsung-camera
APKTOOL=$(ls $R/mysticgsi/tools/apktool/*.jar | head -1); BT=$(ls -d /opt/android-sdk/build-tools/* | sort | tail -1)
TAR=$(realpath "$TAR"); OUT=$(realpath -m "$OUT")
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
mkdir "$W/t" && tar -xf "$TAR" -C "$W/t"
java -jar "$APKTOOL" d -q -r -f -o "$W/dec" "$W/t/SamsungCamera.apk"
DIRS=""
for FIX in "$@"; do
    case "$FIX" in /*) ;; *) FIX="$HERE/$FIX" ;; esac
    D=$(python3 -I "$FIX" "$W/dec") || { echo "$TAR: $(basename "$FIX") failed" >&2; exit 1; }
    [ -n "$D" ] || { echo "$TAR: $(basename "$FIX") changed nothing" >&2; exit 1; }
    DIRS="$DIRS $D"
done
DIRS=$(printf '%s\n' $DIRS | sort -u)
java -jar "$APKTOOL" b -q -o "$W/rebuilt.apk" "$W/dec"
cp "$W/t/SamsungCamera.apk" "$W/cam.apk"
mkdir "$W/dex"
for D in $DIRS; do
    DEX="$(echo "$D" | sed 's/^smali_//; s/^smali$/classes/').dex"
    unzip -q -o "$W/rebuilt.apk" "$DEX" -d "$W/dex"
    (cd "$W/dex" && zip -q -0 "$W/cam.apk" "$DEX")
done
python3 -I "$R/scripts/check-dex.py" "$W/cam.apk"
zip -q -d "$W/cam.apk" 'META-INF/*.SF' 'META-INF/*.RSA' 'META-INF/*.EC' 'META-INF/*.DSA' 'META-INF/MANIFEST.MF' || true
"$BT/zipalign" -p -f 4 "$W/cam.apk" "$W/aligned.apk"
"$BT/apksigner" sign --ks "$HOME/.android/debug.keystore" --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android --out "$W/t/SamsungCamera.apk" "$W/aligned.apk"
rm -f "$W/t/SamsungCamera.apk.idsig"
(cd "$W/t" && tar -cf "$OUT" --owner=0 --group=0 $(tar -tf "$TAR"))
echo "built $OUT (dex: $(echo $DIRS | tr '\n' ' '))"
