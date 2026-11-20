#!/bin/sh
# A set built before 0.5.31 as a new set revision whose services_patched.jar gives the guest's BatteryService
# a Samsung charger's power (patches/battery_charge_power.py, OneOSChargePower), as make-overlays.sh builds
# them now: the Galaxy's health HAL reports no maximum charging current or voltage, so no guest showed fast
# charging. Every other file of the old set is hard-linked, so the new revision takes no space but the new
# jar. Only dex files with a changed class are replaced in the jar.
#
# Usage: scripts/retrofit-charge-power.sh <old set dir> <new set dir>   (APKTOOL=<apktool jar> to override)
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OLD=$(cd "$1" && pwd)
NEW=$2
APKTOOL=${APKTOOL:-$(ls "$ROOT"/mysticgsi/tools/apktool/*.jar /srv/projects/OneOS/mysticgsi/tools/apktool/*.jar 2>/dev/null | head -1)}
MARK="# charger power from Samsung's charging_type in BatteryService (OneOSChargePower)"
AFTER="# installd and IOemNetd codes read on the phone at runtime (OneOSInstalldCodes, OneOSOemNetdCodes): One UI 9.0 and 9.5 phones"
[ -f "$OLD/services_patched.jar" ] && [ -f "$OLD/guards.txt" ] || { echo "$OLD: no services_patched.jar or guards.txt" >&2; exit 1; }
grep -qxF "$MARK" "$OLD/guards.txt" && { echo "$OLD has the charger power already" >&2; exit 1; }
[ -e "$NEW" ] && { echo "$NEW exists" >&2; exit 1; }
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
java -jar "$APKTOOL" d -q -f -r -o "$WORK/services" "$OLD/services_patched.jar"
DIRS=$(python3 -I "$ROOT/switcher/patches/battery_charge_power.py" "$WORK/services" "$ROOT/switcher/patches/OneOSChargePower.smali")
[ -n "$DIRS" ] || { echo "$OLD: BatteryService not patched (see above)" >&2; exit 1; }
java -jar "$APKTOOL" b -q -o "$WORK/rebuilt.jar" "$WORK/services"
# Hard links: the sets' files belong to several accounts and fs.protected_hardlinks lets only
# their owner link them, so root makes the links (no file is copied or changed) and this
# account gets the new folder.
if ! cp -al "$OLD" "$NEW" 2>/dev/null; then
    rm -rf "$NEW"
    sudo cp -al "$OLD" "$NEW"
    sudo chown "$(id -u)" "$NEW"
fi
[ "$(ls "$OLD" | wc -l)" = "$(ls "$NEW" | wc -l)" ] || { echo "$NEW: not every file linked" >&2; exit 1; }
rm -f "$NEW/services_patched.jar" "$NEW/guards.txt"
cp "$OLD/services_patched.jar" "$NEW/services_patched.jar"
for d in $(printf '%s\n' $DIRS | sort -u); do
    DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
    rm -rf "$WORK/dex" && mkdir -p "$WORK/dex"
    unzip -q -o "$WORK/rebuilt.jar" "$DEX" -d "$WORK/dex"
    (cd "$WORK/dex" && zip -q -0 "$NEW/services_patched.jar" "$DEX")
    echo "replaced $DEX"
done
python3 -I "$ROOT/scripts/dex-container-fix.py" "$OLD/services_patched.jar" "$WORK/rebuilt.jar" "$NEW/services_patched.jar"
# HyperOS: miui-services_patched.jar gets Xiaomi's quick charge type the same way (patches/miui_quick_charge.py).
MSUM=""; MOLDSUM=""
if [ -f "$OLD/miui-services_patched.jar" ]; then
    java -jar "$APKTOOL" d -q -f -r -o "$WORK/miui" "$OLD/miui-services_patched.jar"
    MDIRS=$(python3 -I "$ROOT/switcher/patches/miui_quick_charge.py" "$WORK/miui" "$ROOT/switcher/patches/OneOSMiCharge.smali")
    [ -n "$MDIRS" ] || { echo "$OLD: miui-services.jar not patched (see above)" >&2; exit 1; }
    java -jar "$APKTOOL" b -q -o "$WORK/miui-rebuilt.jar" "$WORK/miui"
    rm -f "$NEW/miui-services_patched.jar"
    cp "$OLD/miui-services_patched.jar" "$NEW/miui-services_patched.jar"
    for d in $(printf '%s\n' $MDIRS | sort -u); do
        DEX="$(echo "$d" | sed 's/^smali_//; s/^smali$/classes/').dex"
        rm -rf "$WORK/mdex" && mkdir -p "$WORK/mdex"
        unzip -q -o "$WORK/miui-rebuilt.jar" "$DEX" -d "$WORK/mdex"
        (cd "$WORK/mdex" && zip -q -0 "$NEW/miui-services_patched.jar" "$DEX")
        echo "miui-services: replaced $DEX"
    done
    python3 -I "$ROOT/scripts/dex-container-fix.py" "$OLD/miui-services_patched.jar" "$WORK/miui-rebuilt.jar" "$NEW/miui-services_patched.jar"
    MSUM=$(sha256sum "$NEW/miui-services_patched.jar" | cut -d' ' -f1)
    MOLDSUM=$(sha256sum "$OLD/miui-services_patched.jar" | cut -d' ' -f1)
fi
SUM=$(sha256sum "$NEW/services_patched.jar" | cut -d' ' -f1)
OLDSUM=$(sha256sum "$OLD/services_patched.jar" | cut -d' ' -f1)
# guards.txt: the marker after the runtime-codes marker (else after the first line), the jar's new hash.
L=$(grep -n -x -F "$AFTER" "$OLD/guards.txt" | head -n 1 | cut -d: -f1); L=${L:-1}
awk -v mark="$MARK" -v at="$L" -v old="$OLDSUM" -v new="$SUM" -v mold="$MOLDSUM" -v mnew="$MSUM" 'NR == at { print; print mark; next }
    $1 == old && $2 == "services_patched.jar" { print new "  services_patched.jar"; next }
    mold != "" && $1 == mold && $2 == "miui-services_patched.jar" { print mnew "  miui-services_patched.jar"; next } { print }' \
    "$OLD/guards.txt" > "$NEW/guards.txt"
grep -q "^$SUM  services_patched.jar$" "$NEW/guards.txt" || { echo "guards.txt: services_patched.jar line not updated" >&2; exit 1; }
[ -z "$MSUM" ] || grep -q "^$MSUM  miui-services_patched.jar$" "$NEW/guards.txt" || { echo "guards.txt: miui-services_patched.jar line not updated" >&2; exit 1; }
echo "$NEW: services_patched.jar $SUM (was $OLDSUM)${MSUM:+, miui-services_patched.jar $MSUM (was $MOLDSUM)}"
