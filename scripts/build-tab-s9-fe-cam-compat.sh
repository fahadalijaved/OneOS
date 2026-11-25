#!/bin/sh
# OneOSTabS9FeCamCompat.jar (switcher/overlays/tab_s9_fe_cam_compat/c5/m.java, pull request #371): a dex jar with
# the Galaxy Tab S9 FE host SamsungCamera's c5.m (OneUiVersion) enum, so One UI 9.5's 90500 maps to V9_0.
# guest_prepare.sh stages it in the guest's system_ext/framework on that tablet only.
# Usage: scripts/build-tab-s9-fe-cam-compat.sh [<out.jar>]   (default switcher/assets/OneOSTabS9FeCamCompat.jar)
set -e
R=$(cd "$(dirname "$0")/.." && pwd); OUT=$(realpath -m "${1:-$R/switcher/assets/OneOSTabS9FeCamCompat.jar}")
SDK=${ANDROID_HOME:-/opt/android-sdk}
AJ=$(ls "$SDK"/platforms/*/android.jar | sort -V | tail -1)
D8=$(ls "$SDK"/build-tools/*/d8 2>/dev/null | sort -V | tail -1)
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
mkdir -p "$W/classes"
javac -nowarn --release 17 -classpath "$AJ" -d "$W/classes" "$R/switcher/overlays/tab_s9_fe_cam_compat/c5/m.java"
"$D8" --release --min-api 31 --lib "$AJ" --output "$W/out.jar" "$W"/classes/c5/*.class
cp "$W/out.jar" "$OUT"
echo "built $OUT"
