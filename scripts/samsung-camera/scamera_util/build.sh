#!/bin/sh
# Build scamera_sdk_util.jar for One UI's camera in a guest: One UI's own jar
# (pulled from the phone, never published) with CustomInterfaceHelper's
# CameraDevice.setParameters call pointed at SamsungParams.set (this dir),
# which makes the same binder call. The jar goes onto the guest's
# /system/framework (guest_prepare.sh, from the staged camera set).
#
# Usage: scripts/samsung-camera/scamera_util/build.sh <work dir> <out dir> [<scamera_sdk_util.jar>]
# The third argument: One UI's jar from a firmware pull (build-cached.sh's cache, a
# built samcam.tar) instead of the one on the phone over adb. It must not be in <work dir>.
set -e
W="$1"; OUT="$2"; ORIG="$3"
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT" ;; esac
[ -n "$W" ] && [ -n "$OUT" ] || { echo "usage: $0 <work dir> <out dir> [<scamera_sdk_util.jar>]" >&2; exit 2; }
if [ -n "$ORIG" ]; then
    ORIG=$(realpath "$ORIG")
    case "$ORIG" in "$(realpath -m "$W")"/*) echo "$ORIG is inside the work dir $W" >&2; exit 2 ;; esac
fi
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
APKTOOL=$(ls "$ROOT"/mysticgsi/tools/apktool/*.jar | head -1)
SDK=${ANDROID_HOME:-/opt/android-sdk}
AJ=$(ls -d "$SDK"/platforms/* | sort -V | tail -1)/android.jar
D8=$(ls "$SDK"/build-tools/*/d8 | sort -V | tail -1)
rm -rf "$W" && mkdir -p "$W/cls" "$OUT"
if [ -n "$ORIG" ]; then cp "$ORIG" "$W/orig.jar"
else adb pull /system/framework/scamera_sdk_util.jar "$W/orig.jar" >/dev/null
fi
java -jar "$APKTOOL" d -r -f -q -o "$W/d" "$W/orig.jar"
H="$W/d/smali/com/samsung/android/sdk/camera/impl/internal/CustomInterfaceHelper.smali"
OLD='invoke-virtual {p0, p1}, Landroid/hardware/camera2/CameraDevice;->setParameters(Ljava/lang/String;)V'
NEW='invoke-static {p0, p1}, Lcom/oneos/camera/SamsungParams;->set(Landroid/hardware/camera2/CameraDevice;Ljava/lang/String;)V'
[ "$(grep -cF "$OLD" "$H")" = 1 ] || { echo "CustomInterfaceHelper is not as expected" >&2; exit 1; }
sed -i "s|$(printf '%s' "$OLD" | sed 's/[][\.*^$|/]/\\&/g')|$NEW|" "$H"
java -jar "$APKTOOL" b -q -o "$W/helper.jar" "$W/d"
javac -nowarn --release 17 -classpath "$AJ" -d "$W/cls" "$HERE/SamsungParams.java"
mkdir -p "$W/d8" && "$D8" --release --min-api 31 --lib "$AJ" --output "$W/d8" "$W"/cls/com/oneos/camera/*.class
mkdir -p "$W/jar" && unzip -q -o "$W/helper.jar" classes.dex -d "$W/jar" && cp "$W/d8/classes.dex" "$W/jar/classes2.dex"
(cd "$W/jar" && rm -f "$OUT/scamera_sdk_util.jar" && zip -q -0 "$OUT/scamera_sdk_util.jar" classes.dex classes2.dex)
python3 -I "$ROOT/scripts/check-dex.py" "$OUT/scamera_sdk_util.jar"
echo "built $OUT/scamera_sdk_util.jar"
