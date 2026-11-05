#!/bin/sh
# A built samcam.tar (or samcam_bar.tar) whose scamera_sdk_util.jar is One UI's own, unpatched: 0.4.55 to
# 0.4.57 build-cached.sh copied the S26 Ultra pull's jar over the patched one, so the camera's Samsung
# parameters never reached the HAL ("Fail to set samsung parameter", "Unihal is bypass mode",
# isSamsungCamera(0)). The tar's own jar gets CustomInterfaceHelper pointed at SamsungParams
# (scamera_util/build.sh, which refuses a jar whose call is not there exactly once); every other member
# is copied as it is, in the same order.
# Usage: repatch-scamera-util.sh <samcam.tar> <out samcam.tar>
set -e
TAR="$1"; OUT="$2"
[ -f "$TAR" ] && [ -n "$OUT" ] || { echo "usage: $0 <samcam.tar> <out samcam.tar>" >&2; exit 2; }
HERE=$(cd "$(dirname "$0")" && pwd)
TAR=$(realpath "$TAR"); OUT=$(realpath -m "$OUT")
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
mkdir "$W/t" && tar -xf "$TAR" -C "$W/t"
[ -f "$W/t/scamera_sdk_util.jar" ] || { echo "$TAR: no scamera_sdk_util.jar" >&2; exit 1; }
if grep -q 'Lcom/oneos/camera/SamsungParams;' "$W/t/scamera_sdk_util.jar"; then
    echo "$TAR: scamera_sdk_util.jar is patched already" >&2; exit 1
fi
cp "$W/t/scamera_sdk_util.jar" "$W/orig.jar"
sh "$HERE/scamera_util/build.sh" "$W/build" "$W/new" "$W/orig.jar"
grep -q 'Lcom/oneos/camera/SamsungParams;' "$W/new/scamera_sdk_util.jar"
cp "$W/new/scamera_sdk_util.jar" "$W/t/scamera_sdk_util.jar"
(cd "$W/t" && tar -cf "$OUT" --owner=0 --group=0 $(tar -tf "$TAR"))
echo "built $OUT (scamera_sdk_util.jar with SamsungParams)"
