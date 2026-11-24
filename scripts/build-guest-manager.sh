#!/bin/sh
# Build a normally signed manager APK before configuring :app's staging pins.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# oneui95 <out apk>: the release build for the One UI 9.5 sets (OneOSGuest.apk there), without the Knox
# provider authority Samsung's android package owns in that image; written to <out apk>, not staged.
prop=""; out95=""
case "${1:-release}" in
  release) variant=Release; folder=release ;;
  --debug|debug) variant=Debug; folder=debug ;;
  oneui95) variant=Release; folder=release; prop="-Poneos.guestNoKnox=true"; out95=${2:?out apk} ;;
  *) echo 'Usage: scripts/build-guest-manager.sh [release|--debug|oneui95 <out apk>]' >&2; exit 2 ;;
esac
(cd "$ROOT/app-android" && ./gradlew $prop ":guest:assemble$variant")
if [ -n "$out95" ]; then
    cp "$ROOT/app-android/guest/build/outputs/apk/$folder/guest-$folder.apk" "$out95"
    echo "One UI 9.5 guest manager written to $out95 (not staged)"
    exit 0
fi
apk="$ROOT/app-android/guest/build/outputs/apk/$folder/guest-$folder.apk"
[ -s "$apk" ] || { echo "Missing signed APK: $apk" >&2; exit 1; }
cp "$apk" "$ROOT/switcher/assets/guest_manager.apk.tmp"
mv "$ROOT/switcher/assets/guest_manager.apk.tmp" "$ROOT/switcher/assets/guest_manager.apk"
echo "Guest manager staged from $folder; rebuild :app to regenerate its integrity pins."
