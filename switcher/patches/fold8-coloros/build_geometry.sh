#!/bin/sh
# Rebuild the source-owned helper shipped with the pinned session scripts.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
SDK=${ANDROID_HOME:-/opt/android-sdk}
D8="$SDK/build-tools/${ONEOS_BUILD_TOOLS:-36.1.0}/d8"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT INT TERM
mkdir "$WORK/classes"
javac --release 8 -d "$WORK/classes" "$HERE/OneOSFold8Geometry.java"
"$D8" --release --min-api 31 --output "$WORK" "$WORK"/classes/*.class
cp "$WORK/classes.dex" "$ROOT/switcher/assets/OneOSFold8Geometry.dex"
echo 'Built switcher/assets/OneOSFold8Geometry.dex'
