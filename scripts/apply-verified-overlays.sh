#!/system/bin/sh
# Post-scan overlays: never present modified OEM APKs to PackageManager at boot.
set -eu
stopped=
trap 'for stopped_pid in $stopped; do kill -CONT "$stopped_pid" 2>/dev/null || true; done' EXIT
: "${STAGE:?}" "${BB:?}"
DIR="$STAGE/verified_addons"
[ ! -L "$DIR" ] && [ -d "$DIR" ] || exit 3
[ -z "$(find "$DIR" -type l -print -quit)" ] || exit 3
: "${OVERLAY_MANIFEST_SHA256:?Expected manifest digest is required}"
MANIFEST="$DIR/overlays.list"
verify() {
    [ "$(sha256sum "$MANIFEST" | cut -d' ' -f1)" = "$OVERLAY_MANIFEST_SHA256" ] || return 3
    while read -r package original patched file; do
        case "$package" in ''|*[!a-zA-Z0-9._]*|*..*) return 3;; esac
        case "$file" in ''|*[!a-zA-Z0-9._-]*|*..*) return 3;; esac
        [ "${#original}" = 64 ] && [ "${#patched}" = 64 ] || return 3
        case "$original$patched" in *[!0-9a-f]*) return 3;; esac
        [ -f "$DIR/$file" ] || return 3
        [ "$(sha256sum "$DIR/$file" | cut -d' ' -f1)" = "$patched" ] || return 3
    done < "$MANIFEST"
}
# Paths below shared guest /data must not resolve through a guest-planted
# symlink into the host. Check the existing parent before creating a leaf.
safe_data_path() {
    [ ! -L "$1" ] || return 3
    parent=$("$BB" readlink -f "${1%/*}") || return 3
    case "$parent/" in "$STAGE/data/"*) return 0;; *) return 3;; esac
}
guest() { pid=$1; shift; "$BB" nsenter -t "$pid" -m -r -- /system/bin/sh /data/oneos_genv.sh "$@"; }
verify
[ "${1:-prepare}" != verify ] || exit 0
if [ "${1:-prepare}" = prepare ]; then
    chmod 700 "$DIR"
    rm -f "$DIR/launcher-grid-values.xml"
    GRID="$STAGE/data/user_de/0/com.android.launcher/shared_prefs/com.android.launcher_unique_shared_prefs.xml"
    if [ -f "$GRID" ]; then
        safe_data_path "$GRID" || exit 3
        cp -p "$GRID" "$DIR/launcher-grid-before.xml"
        grep -E 'name="(layout_cellcount_[xy]|LastStandardModeCell[XY]|LastDrawModeCell[XY])"' "$GRID" > "$DIR/launcher-grid-values.xml" || true
    fi
    # Chrome's Java startup reads this cache before native feature initialization.
    F="$STAGE/data/user/0/com.android.chrome/shared_prefs/com.android.chrome_preferences.xml"
    if [ -f "$F" ]; then
        safe_data_path "$F" || exit 3
        uid=$(stat -c %u "$F"); gid=$(stat -c %g "$F")
        cp -p "$F" "$DIR/chrome-before.xml"
        sed 's/name="Chrome.Flags.CachedFlag.JavalessRendererExperimentOn" value="true"/name="Chrome.Flags.CachedFlag.JavalessRendererExperimentOn" value="false"/' "$F" > "$DIR/chrome-fixed.xml"
        cat "$DIR/chrome-fixed.xml" > "$F"
        chown "$uid:$gid" "$F"
    fi
    "$BB" sh "$0" worker </dev/null >> "$STAGE/verified_overlays.log" 2>&1 &
    exit 0
fi
[ "$1" = worker ] || exit 2
# Never mistake One UI or another guest for this stage. Bound the wait.
ready=
for attempt in $(seq 1 150); do
    launcher=$(pidof com.android.launcher | cut -d' ' -f1)
    if [ -n "$launcher" ] && [ "$(stat -Lc '%d:%i' /proc/$launcher/root/data 2>/dev/null)" = "$(stat -Lc '%d:%i' "$STAGE/data")" ]; then
        ready=1; break
    fi
    sleep 2
done
[ "$ready" = 1 ] || { echo 'verified overlays: no guest launcher within 300s; originals retained'; exit 1; }
verify
cache="$STAGE/data/local/tmp/oneos_verified_overlays"
safe_data_path "$cache" || exit 3
mkdir -p "$cache"
chmod 700 "$cache"
while read -r package original patched file; do
    target=$(guest "$launcher" /system/bin/pm path "$package" | sed -n 's/^package://p' | head -1)
    case "$target" in /data/app/*/base.apk|/system/*/*.apk|/my_stock/*/*.apk) ;; *) echo "verified overlays: $package has no supported APK path; skipped"; continue ;; esac
    current=$(sha256sum "/proc/$launcher/root$target" | cut -d' ' -f1)
    [ "$current" = "$original" ] || { echo "verified overlays: $package changed; skipped"; continue; }
    copy="/data/local/tmp/oneos_verified_overlays/$file"
    safe_data_path "$cache/$file" || exit 3
    cp "$DIR/$file" "$cache/$file"
    chmod 644 "/proc/$launcher/root$copy"
    if [ "$package" = com.android.launcher ] && [ -s "$DIR/launcher-grid-values.xml" ]; then
        for p in $(pidof "$package"); do
            [ "$(stat -Lc %d:%i /proc/$p/root/data 2>/dev/null)" = "$(stat -Lc %d:%i "$STAGE/data")" ] || continue
            stopped="$stopped $p"; kill -STOP "$p"; done
        GRID="$STAGE/data/user_de/0/com.android.launcher/shared_prefs/com.android.launcher_unique_shared_prefs.xml"
        safe_data_path "$GRID" || exit 3
        cp -p "$GRID" "$DIR/launcher-before-restore.xml"
        awk 'FNR==NR { lines=lines $0 ORS; next } /name="(layout_cellcount_[xy]|LastStandardModeCell[XY]|LastDrawModeCell[XY])"/ {next} /<\/map>/ {printf "%s",lines} {print}' "$DIR/launcher-grid-values.xml" "$GRID" > "$DIR/grid-restored.xml"
        cat "$DIR/grid-restored.xml" > "$GRID"
    fi
    # Guest zygote is the parent's parent for apps, but resolve by namespace data.
    for p in $(pidof zygote64 system_server com.android.launcher "$package"); do
        [ "$(stat -Lc '%d:%i' /proc/$p/root/data 2>/dev/null)" = "$(stat -Lc '%d:%i' "$STAGE/data")" ] || continue
        "$BB" nsenter -t "$p" -m -r -- /system/bin/mount --bind "$copy" "$target"
    done
    echo "verified overlays: applied $package ($patched)"
    # Refresh only the patched app, after the zygote namespace sees its overlay.
    for p in $(pidof "$package"); do
        [ "$(stat -Lc %d:%i /proc/$p/root/data 2>/dev/null)" = "$(stat -Lc %d:%i "$STAGE/data")" ] || continue
        kill -9 "$p"
    done
done < "$MANIFEST"
echo 'verified overlays: complete'
