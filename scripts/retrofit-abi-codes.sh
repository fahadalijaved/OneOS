#!/bin/sh
# A set built before 0.5.28 as a new set revision whose services_patched.jar reads installd and
# IOemNetd codes on the phone at runtime (patches/guest_installd_abi.py --retrofit,
# patches/guest_oemnetd_abi.py, OneOSInstalldCodes / OneOSOemNetdCodes), as make-overlays.sh builds
# them now: such a set works on a One UI 9.5 phone too (an S26 updated to One UI 9.5 renumbered
# IInstalld and IOemNetd). Every other file of the old set is hard-linked, so the new revision takes
# no space but the new jar. Only dex files with a changed class are replaced in the jar.
#
# Usage: scripts/retrofit-abi-codes.sh <old set dir> <new set dir>   (APKTOOL=<apktool jar> to override)
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OLD=$(cd "$1" && pwd)
NEW=$2
APKTOOL=${APKTOOL:-$(ls "$ROOT"/mysticgsi/tools/apktool/*.jar /srv/projects/OneOS/mysticgsi/tools/apktool/*.jar 2>/dev/null | head -1)}
MARK="# installd and IOemNetd codes read on the phone at runtime (OneOSInstalldCodes, OneOSOemNetdCodes): One UI 9.0 and 9.5 phones"
[ -f "$OLD/services_patched.jar" ] && [ -f "$OLD/guards.txt" ] || { echo "$OLD: no services_patched.jar or guards.txt" >&2; exit 1; }
grep -qxF "$MARK" "$OLD/guards.txt" && { echo "$OLD reads its codes at runtime already" >&2; exit 1; }
[ -e "$NEW" ] && { echo "$NEW exists" >&2; exit 1; }
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
java -jar "$APKTOOL" d -q -f -r -o "$WORK/services" "$OLD/services_patched.jar"
DIRS=$(python3 -I "$ROOT/switcher/patches/guest_installd_abi.py" --retrofit "$WORK/services")
DIRS="$DIRS $(python3 -I "$ROOT/switcher/patches/guest_oemnetd_abi.py" "$WORK/services" \
    "90000=$ROOT/switcher/patches/host_oemnetd.txt" "90500=$ROOT/switcher/patches/host_oemnetd_95.txt")"
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
SUM=$(sha256sum "$NEW/services_patched.jar" | cut -d' ' -f1)
OLDSUM=$(sha256sum "$OLD/services_patched.jar" | cut -d' ' -f1)
# guards.txt: the marker after the first line, the jar's new hash.
awk -v mark="$MARK" -v old="$OLDSUM" -v new="$SUM" 'NR == 1 { print; print mark; next }
    $1 == old && $2 == "services_patched.jar" { print new "  services_patched.jar"; next } { print }' \
    "$OLD/guards.txt" > "$NEW/guards.txt"
grep -q "^$SUM  services_patched.jar$" "$NEW/guards.txt" || { echo "guards.txt: services_patched.jar line not updated" >&2; exit 1; }
echo "$NEW: services_patched.jar $SUM (was $OLDSUM)"
