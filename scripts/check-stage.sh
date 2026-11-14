#!/bin/sh
# The session stage on the phone against the overlay set it should hold.
#
# A stage jar only changes when deploy-phone.sh pushes one. Rebuilding the app
# does not touch it, and neither does editing a patcher: on 2026-11-14 the
# ColorOS stage still held a services_patched.jar from before the guest lock
# could mint a hardware auth token, so face enrollment failed inside Settings
# while the source, the rebuilt APK and the guards looked right. This compares
# the stage's copies with a set's guards.txt and build-info.txt.
#
# Usage: scripts/check-stage.sh [<overlays dir>]   (default out/overlays)
#   Exit 0 when every guarded file on the phone is the set's, and the set was
#   built from HEAD. Exit 1 when something is stale, 2 on a usage error.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OVERLAYS=$(cd "${1:-$ROOT/out/overlays}" && pwd) || { echo "overlays dir not found: ${1:-$ROOT/out/overlays}" >&2; exit 2; }
[ -f "$OVERLAYS/guards.txt" ] || { echo "$OVERLAYS: no guards.txt" >&2; exit 2; }
STAGE=/data/local/tmp/oneos
SERIAL="${ANDROID_SERIAL:-}"
adb_() {
    if [ -n "$SERIAL" ]; then ${ADB:-adb} -s "$SERIAL" "$@"; else ${ADB:-adb} "$@"; fi
}

adb_ shell "su -c 'test -f $STAGE/files.sha256'" 2>/dev/null || {
    echo "no $STAGE/files.sha256 on the phone: is a stage deployed?" >&2
    exit 2
}
SUM=$(mktemp); trap 'rm -f "$SUM"' EXIT
adb_ shell "su -c 'cat $STAGE/files.sha256'" | tr -d '\r' > "$SUM"

stale=0
while read -r sum name; do
    case "$sum" in ''|\#*) continue ;; esac
    [ -n "$name" ] || continue
    have=$(awk -v n="$name" '$2 == n { print $1 }' "$SUM")
    if [ -z "$have" ]; then
        echo "absent   $name (in $OVERLAYS/guards.txt, not in the stage)"
        stale=1
    elif [ "$have" != "$sum" ]; then
        echo "stale    $name (stage $(echo "$have" | cut -c1-12), set $(echo "$sum" | cut -c1-12))"
        stale=1
    fi
done < "$OVERLAYS/guards.txt"

if [ ! -f "$OVERLAYS/build-info.txt" ]; then
    echo "no build-info.txt in $OVERLAYS: the set predates provenance, rebuild it"
    stale=1
else
    set_commit=$(awk '$1 == "commit" { print $2 }' "$OVERLAYS/build-info.txt")
    head_commit=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)
    if [ -n "$head_commit" ] && [ "$set_commit" != "$head_commit" ]; then
        changed=$(git -C "$ROOT" log --oneline "$set_commit..HEAD" -- \
            switcher/patches scripts/make-overlays.sh scripts/patch-framework-camera.sh \
            scripts/patch-built-jar.sh facehal 2>/dev/null || true)
        if [ -n "$changed" ]; then
            echo "old set  $OVERLAYS was built from $(echo "$set_commit" | cut -c1-12), HEAD is $(echo "$head_commit" | cut -c1-12), and the overlays changed since:"
            echo "$changed" | sed 's/^/         /'
            stale=1
        fi
    fi
    if awk '$1 == "dirty" && $2 == "1" { found = 1 } END { exit !found }' "$OVERLAYS/build-info.txt"; then
        echo "warning  $OVERLAYS was built from a modified tree (build-info.txt: dirty 1)"
    fi
fi

if [ "$stale" = 1 ]; then
    echo "rebuild and redeploy: scripts/make-overlays.sh <image> $OVERLAYS, then scripts/deploy-phone.sh --overlays $OVERLAYS <image>"
    exit 1
fi
echo "stage matches $OVERLAYS ($(wc -l < "$OVERLAYS/guards.txt") guarded files)"
