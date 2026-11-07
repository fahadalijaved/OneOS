#!/bin/sh
# Build a normally signed manager APK before configuring :app's staging pins.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
case "${1:-release}" in
  release) variant=Release; folder=release ;;
  --debug|debug) variant=Debug; folder=debug ;;
  *) echo 'Usage: scripts/build-guest-manager.sh [release|--debug]' >&2; exit 2 ;;
esac
(cd "$ROOT/app-android" && ./gradlew ":guest:assemble$variant")
apk="$ROOT/app-android/guest/build/outputs/apk/$folder/guest-$folder.apk"
[ -s "$apk" ] || { echo "Missing signed APK: $apk" >&2; exit 1; }
cp "$apk" "$ROOT/switcher/assets/guest_manager.apk.tmp"
mv "$ROOT/switcher/assets/guest_manager.apk.tmp" "$ROOT/switcher/assets/guest_manager.apk"
echo "Guest manager staged from $folder; rebuild :app to regenerate its integrity pins."
