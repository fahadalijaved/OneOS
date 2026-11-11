#!/bin/sh
# Builds OneOSWaveRepack.dex, the on-phone half of the fingerprint wave.
#
# The wave patch changes only classes3.dex of ColorOS's SystemUI. Shipping the
# whole 127 MB APK to every phone is wasteful, so the set carries the patched
# dex and this small repacker; guest_prepare.sh appends the dex to the image's
# stock SystemUI with the same layout scripts/apk-replace-dex.py writes on the
# build machine.
#
# Usage: scripts/make-wave-repack.sh [out-dir]
# Needs javac (17+) and d8; d8 comes from $D8 or $ANDROID_HOME/build-tools.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:-$ROOT/out}
SRC=$ROOT/scripts/wave-repack
WORK=${WORK:-/var/tmp/oneos-wave-repack}

JAVAC=${JAVAC:-javac}
D8=${D8:-${ANDROID_HOME:-/home/vd/Android/Sdk}/build-tools/36.0.0/d8}

[ -f "$SRC/OneOSWaveRepack.java" ] || {
    echo "missing $SRC/OneOSWaveRepack.java" >&2
    exit 1
}
[ -x "$D8" ] || {
    echo "d8 not found at $D8 (set D8 or ANDROID_HOME)" >&2
    exit 1
}

rm -rf "$WORK"
mkdir -p "$WORK/classes" "$WORK/dex" "$OUT"
"$JAVAC" --release 17 -d "$WORK/classes" "$SRC/OneOSWaveRepack.java"
"$D8" --min-api 31 --output "$WORK/dex" "$WORK"/classes/com/oneos/wave/*.class

cp -f "$WORK/dex/classes.dex" "$OUT/OneOSWaveRepack.dex"
size=$(stat -c %s "$OUT/OneOSWaveRepack.dex")
sha=$(sha256sum "$OUT/OneOSWaveRepack.dex" | awk '{print $1}')
echo "$sha  OneOSWaveRepack.dex  ($size bytes)"
echo "next: upload $OUT/OneOSWaveRepack.dex to the release, then pin $sha"
