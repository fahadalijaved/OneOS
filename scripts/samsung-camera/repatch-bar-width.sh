#!/bin/sh
# A built samcam.tar with fix_bar_width.py's current helper (Loneos/camera/OneOSBarWidth;), for a set
# whose guest image is no longer on the server: decode the tar's SamsungCamera.apk, write the helper
# from fix_bar_width.py over the old one, rebuild, put only the helper's dex back into the APK (every
# other entry byte for byte), align and sign with the key build-cached.sh signs with. The other tar
# members are copied as they are, in the same order.
# Usage: repatch-bar-width.sh <samcam.tar> <out samcam.tar>
set -e
TAR="$1"; OUT="$2"
[ -f "$TAR" ] && [ -n "$OUT" ] || { echo "usage: $0 <samcam.tar> <out samcam.tar>" >&2; exit 2; }
R=/srv/projects/OneOS; HERE=$R/scripts/samsung-camera
APKTOOL=$(ls $R/mysticgsi/tools/apktool/*.jar | head -1); BT=$(ls -d /opt/android-sdk/build-tools/* | sort | tail -1)
TAR=$(realpath "$TAR"); OUT=$(realpath -m "$OUT")
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
mkdir "$W/t" && tar -xf "$TAR" -C "$W/t"
java -jar "$APKTOOL" d -q -r -f -o "$W/dec" "$W/t/SamsungCamera.apk"
H=$(ls "$W"/dec/smali*/oneos/camera/OneOSBarWidth.smali 2>/dev/null)
[ "$(echo "$H" | grep -c .)" = 1 ] || { echo "$TAR: no single OneOSBarWidth helper in SamsungCamera.apk" >&2; exit 1; }
python3 -I - "$HERE/fix_bar_width.py" "$H" <<'EOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("fix_bar_width", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
open(sys.argv[2], "w").write(m.HELPER_SMALI)
EOF
D=$(echo "$H" | sed "s|^$W/dec/||; s|/.*||")
DEX="$(echo "$D" | sed 's/^smali_//; s/^smali$/classes/').dex"
java -jar "$APKTOOL" b -q -o "$W/rebuilt.apk" "$W/dec"
cp "$W/t/SamsungCamera.apk" "$W/cam.apk"
mkdir "$W/dex" && unzip -q -o "$W/rebuilt.apk" "$DEX" -d "$W/dex"
(cd "$W/dex" && zip -q -0 "$W/cam.apk" "$DEX")
python3 -I "$R/scripts/check-dex.py" "$W/cam.apk"
zip -q -d "$W/cam.apk" 'META-INF/*.SF' 'META-INF/*.RSA' 'META-INF/*.EC' 'META-INF/*.DSA' 'META-INF/MANIFEST.MF' || true
"$BT/zipalign" -p -f 4 "$W/cam.apk" "$W/aligned.apk"
"$BT/apksigner" sign --ks "$HOME/.android/debug.keystore" --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android --out "$W/t/SamsungCamera.apk" "$W/aligned.apk"
rm -f "$W/t/SamsungCamera.apk.idsig"
(cd "$W/t" && tar -cf "$OUT" --owner=0 --group=0 $(tar -tf "$TAR"))
echo "built $OUT (helper in $DEX)"
