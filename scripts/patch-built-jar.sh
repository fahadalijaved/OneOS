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
APKTOOL=${APKTOOL:-$(ls "$ROOT"/mysticgsi/tools/apktool/*.jar 2>/dev/null | head -1)}
JAR=$(realpath "$JAR"); PATCHER=$(realpath "$PATCHER"); OUT=$(realpath -m "$OUT")
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
java -jar "$APKTOOL" d -q -f -r -o "$W/src" "$JAR"
DIRS=$(python3 -I "$PATCHER" "$W/src")
[ -n "$DIRS" ] || { echo "$PATCHER changed nothing" >&2; exit 1; }
java -jar "$APKTOOL" b -q -o "$W/rebuilt.jar" "$W/src"
cp "$JAR" "$W/out.jar"
for d in $DIRS; do
    DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
    rm -rf "$W/dex" && mkdir -p "$W/dex"
    unzip -q -o "$W/rebuilt.jar" "$DEX" -d "$W/dex"
    if command -v zip >/dev/null 2>&1; then
        (cd "$W/dex" && zip -q -0 "$W/out.jar" "$DEX")
    else
        # The Windows toolchain has the JDK but no Info-ZIP. jar's
        # --no-compress update keeps the replacement dex stored as ART expects.
        jar --update --file "$W/out.jar" --no-compress -C "$W/dex" "$DEX"
    fi
    python3 - "$W/out.jar" "$DEX" <<'PY'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    info = archive.getinfo(sys.argv[2])
    if info.compress_type != zipfile.ZIP_STORED:
        raise SystemExit(f"{sys.argv[2]} is not stored")
    if archive.testzip() is not None:
        raise SystemExit("rebuilt jar failed its ZIP integrity check")
PY
    echo "replaced $DEX"
done
python3 "$ROOT/scripts/check-dex.py" "$W/out.jar" >&2 || true
mv "$W/out.jar" "$OUT"
echo "built $OUT"
