#!/bin/sh
# A built samcam.tar whose SamsungCamera.apk gets fix_recorder_track_started.py (0.4.59: every video
# was cancelled on Stop, AOSP's recorder sends no track-started 905), for sets whose guest image is
# no longer on the server: decode the APK, run the fix, rebuild, put back only the dex files the fix
# names (every other entry byte for byte), align and sign with the key build-cached.sh signs with.
# The other tar members are copied as they are, in the same order.
# Usage: repatch-track-start.sh <samcam.tar> <out samcam.tar>
set -e
TAR="$1"; OUT="$2"
[ -f "$TAR" ] && [ -n "$OUT" ] || { echo "usage: $0 <samcam.tar> <out samcam.tar>" >&2; exit 2; }
R=/srv/projects/OneOS; HERE=$R/scripts/samsung-camera
APKTOOL=$(ls $R/mysticgsi/tools/apktool/*.jar | head -1); BT=$(ls -d /opt/android-sdk/build-tools/* | sort | tail -1)
TAR=$(realpath "$TAR"); OUT=$(realpath -m "$OUT")
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
mkdir "$W/t" && tar -xf "$TAR" -C "$W/t"
java -jar "$APKTOOL" d -q -r -f -o "$W/dec" "$W/t/SamsungCamera.apk"
DIRS=$(python3 -I "$HERE/fix_recorder_track_started.py" "$W/dec")
[ -n "$DIRS" ] || { echo "$TAR: the fix changed nothing" >&2; exit 1; }
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
