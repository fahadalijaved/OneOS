#!/bin/sh
# Apply one more smali patcher to an already-built guard jar (a set's
# services_patched.jar), without the guest image: decode the jar, run the
# patcher, rebuild, and put only the dex files the patcher names into a copy of
# the jar (the same step as make-overlays.sh; every other entry stays byte for
# byte). For sets whose image is no longer on the server.
#
# Usage: scripts/patch-built-jar.sh <built jar> <patcher.py> <out jar>
set -e
JAR="$1"; PATCHER="$2"; OUT="$3"
[ -f "$JAR" ] && [ -f "$PATCHER" ] && [ -n "$OUT" ] || { echo "usage: $0 <built jar> <patcher.py> <out jar>" >&2; exit 2; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
APKTOOL=${APKTOOL:-$(ls "$ROOT"/mysticgsi/tools/apktool/*.jar | head -1)}
JAR=$(realpath "$JAR"); PATCHER=$(realpath "$PATCHER"); OUT=$(realpath -m "$OUT")
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
$APKTOOL d -q -f -r -o "$W/src" "$JAR"
DIRS=$(python3 -I "$PATCHER" "$W/src")
[ -n "$DIRS" ] || { echo "$PATCHER changed nothing" >&2; exit 1; }
$APKTOOL b -q -o "$W/rebuilt.jar" "$W/src"
cp "$JAR" "$W/out.jar"
for d in $DIRS; do
    DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
    rm -rf "$W/dex" && mkdir -p "$W/dex"
    unzip -q -o "$W/rebuilt.jar" "$DEX" -d "$W/dex"
    python3 - "$W/out.jar" "$W/dex/$DEX" "$DEX" <<'PY'
import os, sys, zipfile
jar, dex, name = sys.argv[1:4]
tmp = jar + ".tmp"
with zipfile.ZipFile(jar) as src, zipfile.ZipFile(tmp, "w") as dst:
    for entry in src.infolist():
        if entry.filename != name:
            dst.writestr(entry, src.read(entry.filename))
    dst.write(dex, name, compress_type=zipfile.ZIP_STORED)
os.replace(tmp, jar)
PY
    echo "replaced $DEX"
done
python3 "$ROOT/scripts/check-dex.py" "$W/out.jar" >&2 || true
mv "$W/out.jar" "$OUT"
echo "built $OUT"
