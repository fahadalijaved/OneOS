#!/system/bin/sh
# Fold8 / Find N6 UI integration plus capability-detected performance handover
# for all profiles and guests. UI runtime still runs only in the selected guest.
set -e
STAGE=${STAGE:-/data/local/tmp/oneos}
BB=${BB:-/data/oneos_bin/busybox}
fail() { echo "Fold8 ColorOS: $*" >&2; exit 3; }
# 0.4.38: the Find N6 global image on the Z Fold8 and the Z Fold8 Ultra (set n6-f8u,
# which carries the global build's Fold8SystemUI.apk and angle relay); the CN build's
# n6-f8 is retired. Only where the patched SystemUI is staged.
selected() {
    case "${ONEOS_PROFILE:-}" in f8|f8u) ;; *) return 1 ;; esac
    grep -Eq '^  "image": "coloros17-findn6(-global)?",$' "$STAGE/.oneos_stage" &&
        grep -Eq '^  "set": "(n6-f8|n6-f8u|n6-global-f8)",$' "$STAGE/.oneos_stage" &&
        [ -f "$STAGE/Fold8SystemUI.apk" ] && [ ! -L "$STAGE/Fold8SystemUI.apk" ]
}
# Reject links anywhere below the new folder, including a guest-planted link
# to host data. Existing stage/namespace checks run before this script.
# Play services and the Play Store come from guest_google.sh (every ColorOS
# set since 0.4.16).
plain_tree() {
    [ ! -L "$1" ] || fail "$1 is a symlink"
    [ ! -d "$1" ] || [ -z "$(find "$1" -type l -print -quit)" ] || fail "symlink below $1"
}
# Samsung's userspace votes survive framework shutdown. Own only requests we
# change, preserve a host snapshot, and yield to external policy writers.
# This backend is shared by every profile/guest. Probe the Samsung request
# interfaces instead of assuming a model, cluster number or GPU frequency.
# The GPU's frequencies in gpu_max_clock's unit. Snapdragon: Qualcomm's kgsl
# table in Hz, gpu_max_clock in MHz (the Fold8's tested path). Without kgsl
# (Exynos: Galaxy Z Flip8, the Exynos S26 and S26+), Samsung's own
# gpu_freq_table, which its driver prints in gpu_max_clock's unit.
gpu_freqs() {
    if [ -r /sys/class/kgsl/kgsl-3d0/gpu_available_frequencies ]; then
        awk '{for(i=1;i<=NF;i++)if($i~/^[0-9]+$/)printf "%d ", int($i/1000000)}' /sys/class/kgsl/kgsl-3d0/gpu_available_frequencies
    elif [ -r /sys/kernel/gpu/gpu_freq_table ]; then
        awk '{for(i=1;i<=NF;i++)if($i~/^[0-9]+$/)printf "%d ", $i}' /sys/kernel/gpu/gpu_freq_table
    fi
}
gpu_max() { gpu_freqs | awk '{for(i=1;i<=NF;i++)if($i>m)m=$i}END{print m+0}'; }
perf_supported() {
    for node in /sys/devices/system/cpu/cpufreq_limit/cpufreq_max_limit /sys/kernel/gpu/gpu_max_clock /sys/kernel/gpu/gpu_tmu; do
        [ -r "$node" ] || return 1
    done
    [ "$(gpu_max)" -gt 0 ] || return 1
    [ -w /sys/devices/system/cpu/cpufreq_limit/cpufreq_max_limit ] && [ -w /sys/kernel/gpu/gpu_max_clock ] || return 1
    count=0
    for policy in /sys/devices/system/cpu/cpufreq/policy*; do
        [ -r "$policy/cpuinfo_max_freq" ] && [ -w "$policy/scaling_max_freq" ] || return 1
        maximum=$(cat "$policy/cpuinfo_max_freq")
        case "$maximum" in ''|*[!0-9]*) return 1;; esac
        [ "$maximum" -gt 0 ] || return 1
        count=$((count + 1))
    done
    [ "$count" -gt 0 ]
}
perf_state() { echo "$STAGE/performance_handover"; }
perf_log() { echo "$(date +%T) $*" >> "$STAGE/performance_handover.log"; }
perf_guest() {
    for q in $(pidof system_server); do
        [ "$(stat -Lc %d:%i /proc/$q/root/data 2>/dev/null)" = "$(stat -Lc %d:%i "$STAGE/data")" ] && { echo "$q"; return; }
    done
    return 1
}
perf_snapshot() {
    perf_supported || return 0
    PSTATE=$(perf_state); plain_tree "$PSTATE"
    [ -f /sys/devices/system/cpu/cpufreq_limit/cpufreq_max_limit ] && [ -f /sys/kernel/gpu/gpu_max_clock ] || return 0
    [ ! -f "$PSTATE/pid" ] || ! kill -0 "$(cat "$PSTATE/pid")" 2>/dev/null || fail 'performance worker already active'
    mkdir -p "$PSTATE"; chmod 700 "$PSTATE"
    for f in stop cpu.last gpu.last cpu.external gpu.external released; do rm -f "$PSTATE/$f"; done
    rmdir "$PSTATE/worker.lock" 2>/dev/null || true
    cat /proc/sys/kernel/random/boot_id > "$PSTATE/boot"
    cat /sys/devices/system/cpu/cpufreq_limit/cpufreq_max_limit > "$PSTATE/cpu.before"
    cat /sys/kernel/gpu/gpu_max_clock > "$PSTATE/gpu.before"
    for p in /sys/devices/system/cpu/cpufreq/policy*; do
        cat "$p/scaling_max_freq" > "$PSTATE/${p##*/}.before"
        rm -f "$PSTATE/${p##*/}.last" "$PSTATE/${p##*/}.external"
    done
    power_save=unknown
    if [ "${1:-host}" = host ]; then
        power_save=$(timeout 3 settings get global low_power 2>/dev/null || true)
        case "$power_save" in 0|1) ;; *) power_save=unknown;; esac
    fi
    echo "$power_save" > "$PSTATE/power_save"
    echo "${1:-host}" > "$PSTATE/mode"
    perf_log "snapshot ($1): cpu=$(cat "$PSTATE/cpu.before") gpu=$(cat "$PSTATE/gpu.before")"
}
perf_valid() {
    PSTATE=$(perf_state)
    plain_tree "$PSTATE"
    perf_supported && [ -f "$PSTATE/boot" ] && [ "$(cat "$PSTATE/boot")" = "$(cat /proc/sys/kernel/random/boot_id)" ]
}
perf_restore_one() {
    node=$1; tag=$2
    [ -f "$PSTATE/$tag.last" ] || return 0
    last=$(cat "$PSTATE/$tag.last"); before=$(cat "$PSTATE/$tag.before")
    case "$before:$last" in *[!0-9:-]*|:*) return 1;; esac
    if [ "$(cat "$node")" = "$last" ]; then
        echo "$before" > "$node"
        perf_log "restored $tag=$before (effective $(cat "$node"))"
    else
        perf_log "preserved external $tag request $(cat "$node")"
    fi
    rm -f "$PSTATE/$tag.last"
}
perf_restore() {
    perf_valid || return 0
    perf_restore_one /sys/devices/system/cpu/cpufreq_limit/cpufreq_max_limit cpu
    perf_restore_one /sys/kernel/gpu/gpu_max_clock gpu
    for p in /sys/devices/system/cpu/cpufreq/policy*; do perf_restore_one "$p/scaling_max_freq" "${p##*/}"; done
    rm -f "$PSTATE/pid"
}
perf_write() {
    node=$1; tag=$2; target=$3
    case "$target" in ''|*[!0-9-]*) return 1;; esac
    [ ! -f "$PSTATE/$tag.external" ] || return 0
    if [ -f "$PSTATE/$tag.last" ] && [ "$(cat "$node")" != "$(cat "$PSTATE/$tag.last")" ]; then
        perf_log "yielding $tag to external controller ($(cat "$node"))"
        touch "$PSTATE/$tag.external"; return 0
    fi
    echo "$target" > "$node"
    cat "$node" > "$PSTATE/$tag.last"
    perf_log "requested $tag=$target; effective $(cat "$node")"
}
perf_worker() {
    perf_supported || return 0
    perf_valid || return 0
    mkdir "$PSTATE/worker.lock" 2>/dev/null || fail 'performance worker already running'
    echo $$ > "$PSTATE/pid"
    echo $$ > /sys/fs/cgroup/cgroup.procs 2>/dev/null || true
    trap 'perf_restore; rmdir "$PSTATE/worker.lock" 2>/dev/null || true' EXIT
    trap 'exit 0' TERM INT
    for n in $(seq 1 150); do
        [ ! -f "$PSTATE/stop" ] && [ ! -f "$STAGE/data/oneos_rec_stop" ] || return 0
        gp=$(perf_guest) && break
        sleep 2
    done
    [ -n "${gp:-}" ] || return 1
    gpu_top=$(gpu_max)
    case "$gpu_top" in ''|0|*[!0-9]*) return 1;; esac
    mode=$(cat "$PSTATE/mode"); released=0; level=-1
    while [ ! -f "$PSTATE/stop" ] && [ ! -f "$STAGE/data/oneos_rec_stop" ]; do
        gp=$(perf_guest) || return 0
        skin=$(timeout 3 "$BB" nsenter -t "$gp" -m -r -- /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys thermalservice 2>/dev/null |
          sed -n '/^Current temperatures from HAL:/,/^Current cooling devices/p' | sed -n 's/.*mValue=\([0-9.]*\), mType=3,.*/\1/p' | awk 'NF {if(!seen || $1>max) max=$1; seen=1} END {if(seen) print max}')
        gpu_t=$(cat /sys/kernel/gpu/gpu_tmu)
        case "$gpu_t" in ''|*[!0-9]*) skin='';; esac
        if [ -z "$skin" ]; then
            # No new headroom without a valid temperature reading. Once active,
            # a telemetry loss selects conservative caps, not full frequency.
            [ "$released" = 1 ] || { sleep 2; continue; }
            new=3
        else
            new=$(awk -v s="$skin" -v g="$gpu_t" -v l="$level" 'BEGIN {t[1]=45;t[2]=47;t[3]=50;u[1]=70000;u[2]=75000;u[3]=80000;if(l<0)l=0;while(l<3&&(s>=t[l+1]||g>=u[l+1]))l++;while(l>0&&s<t[l]-2&&g<u[l]-5000)l--;print l}')
        fi
        if [ "$released" = 0 ]; then
            [ -n "$skin" ] && awk -v s="$skin" -v g="$gpu_t" 'BEGIN{exit !(s<38&&g<65000)}' || { sleep 2; continue; }
            before=$(cat "$PSTATE/cpu.before")
            prime=$(cat /sys/devices/system/cpu/cpufreq/policy*/cpuinfo_max_freq | awk '$1>m{m=$1} END{print m}')
            # A deliberately restricted host is preserved. Live repair is an
            # explicit diagnostic command for the already observed stale vote.
            power_save=$(cat "$PSTATE/power_save")
            if [ "$mode" != live ] && { [ "$power_save" = 1 ] || { [ "$power_save" != 0 ] && [ "$before" != -1 ] && [ "$before" -lt "$prime" ]; }; }; then
                perf_log 'host power saving or unknown restricted policy; preserving limits'; return 0
            fi
            perf_write /sys/devices/system/cpu/cpufreq_limit/cpufreq_max_limit cpu -1
            released=1; touch "$PSTATE/released"
        fi
        if [ "$new" != "$level" ]; then
            case "$new" in 0) pct=100;; 1) pct=80;; 2) pct=65;; *) pct=50;; esac
            for p in /sys/devices/system/cpu/cpufreq/policy*; do
                hw=$(cat "$p/cpuinfo_max_freq"); ceiling=$(cat "$PSTATE/${p##*/}.before")
                if [ "$mode" = live ] || [ "$(cat "$PSTATE/power_save")" = 0 ]; then ceiling=$hw; fi
                target=$((hw / 100 * pct)); [ "$target" -le "$ceiling" ] || target=$ceiling
                perf_write "$p/scaling_max_freq" "${p##*/}" "$target"
            done
            ceiling=$(cat "$PSTATE/gpu.before"); if [ "$mode" = live ] || [ "$(cat "$PSTATE/power_save")" = 0 ]; then ceiling=$gpu_top; fi
            target=$(gpu_freqs | awk -v max="$((gpu_top * pct / 100))" -v ceiling="$ceiling" '{for(i=1;i<=NF;i++){v=$i;if(v<=max&&v<=ceiling&&v>m)m=v}}END{print m}')
            # No table step under this level's cap: the lowest one, never an empty write.
            case "$target" in ''|0) target=$(gpu_freqs | awk '{for(i=1;i<=NF;i++)if(!m||$i<m)m=$i}END{print m}');; esac
            perf_write /sys/kernel/gpu/gpu_max_clock gpu "$target"
            perf_log "thermal level $level->$new skin=${skin:-unknown} gpu=$gpu_t"
            level=$new
        fi
        sleep 2
    done
}

case "$1" in
addons-prepare|addons-worker|addons-verify)
    selected || exit 0
    # Locally retained optional APKs: absent on stock stages. Never trust a
    # manifest supplied by guest data; this exact accepted bundle is pinned.
    ADDON_DIR="$STAGE/verified_addons"
    OVERLAY_MANIFEST_SHA256=dc070965265f33c3b8c6825b0bd3ffae2877f847a4de41b39d24594ae9d748fc
    if grep -q '"set": "n6-global-f8"' "$STAGE/.oneos_stage"; then
        ADDON_DIR="$STAGE/global_verified_addons"
        expected_archive=$(awk '$2 == "GlobalVerifiedAddons.tar" { print $1 }' "$STAGE/files.sha256")
        [ "${#expected_archive}" = 64 ] || fail 'global addon archive is not staged'
        [ -f "$STAGE/GlobalVerifiedAddons.tar" ] && [ ! -L "$STAGE/GlobalVerifiedAddons.tar" ] || fail 'global addon archive is not staged'
        [ "$(sha256sum "$STAGE/GlobalVerifiedAddons.tar" | cut -d' ' -f1)" = "$expected_archive" ] || fail 'global addon archive differs'
        plain_tree "$ADDON_DIR"
        if [ "$1" = addons-prepare ]; then
            # Root unpacks it in One UI's mount namespace, and a patch channel chooses it: regular
            # files and folders only, plain relative names, into a fresh folder. busybox tar follows
            # hard links ("name -> target" in its listing) and would write through them (pull
            # request #37 review). The worker and the check read this folder, never unpack again.
            # A channel's archive may be gzip (busybox reads it only with z).
            ZF=; [ "$("$BB" od -An -tx1 -N2 "$STAGE/GlobalVerifiedAddons.tar" | tr -d ' ')" = 1f8b ] && ZF=z
            "$BB" tar -${ZF}tvf "$STAGE/GlobalVerifiedAddons.tar" > "$STAGE/addons_members.txt" 2>/dev/null ||
                fail 'global addon archive is unreadable'
            "$BB" awk 'substr($1, 1, 1) != "-" && substr($1, 1, 1) != "d" { bad = 1 } / -> / { bad = 1 } END { exit bad }' \
                "$STAGE/addons_members.txt" || fail 'global addon archive holds a link or a special file'
            "$BB" tar -${ZF}tf "$STAGE/GlobalVerifiedAddons.tar" > "$STAGE/addons_members.txt" 2>/dev/null ||
                fail 'global addon archive is unreadable'
            "$BB" awk '{ n = $0; sub(/^\.\//, "", n) } n == "" { next }
                       n !~ /^[A-Za-z0-9_][A-Za-z0-9._-]*(\/[A-Za-z0-9_][A-Za-z0-9._-]*)*\/?$/ || n ~ /(^|\/)\.\.?(\/|$)/ { bad = 1 } END { exit bad }' \
                "$STAGE/addons_members.txt" || fail 'global addon archive holds a name outside its folder'
            rm -f "$STAGE/addons_members.txt"
            rm -rf "$ADDON_DIR"
            mkdir -p "$ADDON_DIR" && chmod 700 "$ADDON_DIR"
            "$BB" tar -${ZF}xf "$STAGE/GlobalVerifiedAddons.tar" -C "$ADDON_DIR" || fail 'global addon archive did not unpack'
            [ -z "$(find "$ADDON_DIR" ! -type f ! -type d -print -quit)" ] || fail 'global addon archive unpacked a link or a special file'
        fi
        [ -s "$ADDON_DIR/overlays.list" ] || exit 0
        OVERLAY_MANIFEST_SHA256=$(sha256sum "$ADDON_DIR/overlays.list" | cut -d' ' -f1)
    fi
    [ -d "$ADDON_DIR" ] || exit 0
    export OVERLAY_MANIFEST_SHA256
    set -- "${1#addons-}"
stopped=
trap 'for stopped_pid in $stopped; do kill -CONT "$stopped_pid" 2>/dev/null || true; done' EXIT
: "${STAGE:?}" "${BB:?}"
DIR="$ADDON_DIR"
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
    "$BB" sh "$0" addons-worker </dev/null >> "$STAGE/verified_overlays.log" 2>&1 &
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
# Keep package operations in system_server's stable namespace while patched
# apps restart; a launcher PID becomes stale after applying its own overlay.
server=$(pidof system_server | cut -d' ' -f1)
[ -n "$server" ] && [ "$(stat -Lc '%d:%i' /proc/$server/root/data)" = "$(stat -Lc '%d:%i' "$STAGE/data")" ] || exit 3
launcher=$server
cache="$STAGE/data/local/tmp/oneos_verified_overlays"
safe_data_path "$cache" || exit 3
mkdir -p "$cache"
chmod 700 "$cache"
while read -r package original patched file; do
    if grep -q '"set": "n6-global-f8"' "$STAGE/.oneos_stage"; then
        case "$package" in com.android.launcher|com.android.systemui|com.oplus.wallpapers) ;;
            *) echo "verified overlays: global firmware keeps bundled $package"; continue ;;
        esac
    fi
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
    ;;
performance-supported) perf_supported ;;
performance-snapshot) perf_snapshot host ;;
performance-live)
    perf_supported || exit 0
    perf_guest >/dev/null || fail 'live repair requires this ColorOS guest'
    perf_snapshot live
    perf_worker
    ;;
performance-worker) perf_worker ;;
performance-restore)
    if perf_valid; then
        touch "$PSTATE/stop"
        pid=$(cat "$PSTATE/pid" 2>/dev/null || true)
        # Do not signal a stale or reused PID; process ownership is checked.
        case "$pid" in *[!0-9]*) fail 'invalid performance worker PID';; esac
        if [ -n "$pid" ] && tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null | grep -q 'performance-'; then
            kill -TERM "$pid" 2>/dev/null || true
            for n in 1 2 3 4; do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
        fi
        perf_restore
    fi
    ;;
prepare)
    selected || exit 0
    ROOTFS="$STAGE/rootfs"
    # Official global Photos must replace the donor directory before package
    # scanning, otherwise duplicate permissions keep the donor active.
    if ! grep -q '"set": "n6-global-f8"' "$STAGE/.oneos_stage" && [ -f "$STAGE/verified_addons/PhotosGlobal.apk" ]; then
        plain_tree "$STAGE/verified_addons"
SOURCE="$STAGE/verified_addons/PhotosGlobal.apk"
TARGET="$ROOTFS/my_stock/priv-app/OppoGallery2"
[ -f "$SOURCE" ] && [ ! -L "$SOURCE" ] || exit 3
[ "$(sha256sum "$SOURCE" | cut -d' ' -f1)" = af2801326bd3f5db80f2583644cf7e7a8ddfa2740022b72ae9ed099b038329ac ] || exit 3
# The CN build's gallery only; the global build has its own Photos (left as it is).
if [ "$(sha256sum "$TARGET/OppoGallery2.apk" 2>/dev/null | cut -d' ' -f1)" = 9610c7efab2b3b45a547d8caa7c75df74ebb614c2dea0322b33343cf2fff2198 ]; then
# Clean directory avoids mixing old gallery libraries with the global APK.
REPLACEMENT="$STAGE/verified_addons/gallery_global_system"
[ ! -L "$REPLACEMENT" ] || exit 3
plain_tree "$REPLACEMENT"
mkdir -p "$REPLACEMENT"
[ ! -L "$REPLACEMENT/Photos.apk" ] || exit 3
cp "$SOURCE" "$REPLACEMENT/Photos.apk"
chmod 755 "$REPLACEMENT"
chmod 644 "$REPLACEMENT/Photos.apk"
"$BB" mount --bind "$REPLACEMENT" "$TARGET"
echo 'Official global Photos replaces donor gallery for guest package scan'
fi
    fi
    target="$ROOTFS/system/system_ext/priv-app/SystemUI/SystemUI.apk"
    "$BB" umount -l "$target" 2>/dev/null || true
    [ -f "$target" ] && [ ! -L "$target" ] || fail 'unexpected SystemUI path'
    # The CN build's SystemUI or (0.4.38) the global build's, each with its own Fold8SystemUI.apk.
    case "$(sha256sum "$target" | cut -d' ' -f1)" in
        e6bf0e49649dc82117e7b9584c13dbcf737183d17c461cd6edcedcc127165f7e|735e43e076bfcef6e73508ea366f3675a69a5a8bb0750cd92d0e3612b2cd7c54) ;;
        *) fail 'SystemUI donor differs' ;;
    esac
    "$BB" mount --bind "$STAGE/Fold8SystemUI.apk" "$target"
    "$BB" mount --make-private "$target"
    "$BB" mount -o remount,bind,ro "$STAGE/Fold8SystemUI.apk" "$target"
    dest="$STAGE/data/oneos_fold8"
    plain_tree "$dest"
    mkdir -p "$dest"
    # The CN build's donor apps only where staged (the global build has its own).
    for f in Fold8Aod.apk Fold8UMS.apk Fold8Instant.apk Fold8AngleRelay.dex; do
        [ -f "$STAGE/$f" ] || { rm -f "$dest/$f"; continue; }
        cp -f "$STAGE/$f" "$dest/$f"
        chmod 644 "$dest/$f"
    done
    cp -f "$STAGE/OneOSFold8Geometry.dex" "$dest/OneOSFold8Geometry.dex"
    chmod 644 "$dest/OneOSFold8Geometry.dex"
    cp -f "$STAGE/fold8_coloros.sh" "$dest/runtime.sh"
    # The runtime runs in the guest without the session's environment.
    echo "${ONEOS_PROFILE:-}" > "$dest/profile"
    chmod 755 "$dest"; chmod 644 "$dest/runtime.sh"
    chown -R 0:0 "$dest"
    chcon -R u:object_r:system_data_file:s0 "$dest"
    ;;
runtime)
    # This file is copied only into an n6-f8 guest data tree and invoked via
    # the UI activator's guest namespace + environment. No host pm/settings.
    D=/data/oneos_fold8
    [ -f "$D/Fold8AngleRelay.dex" ] || exit 0
    reload=0
    CLASSPATH="$D/OneOSFold8Geometry.dex" app_process /system/bin OneOSFold8Geometry
    # Keep construction-time unfold consumers enabled as well as the patched
    # ResourceUnfoldTransitionConfig accessors. These guest-only overlays also
    # cover consumers which read the framework resources directly.
    for spec in config_unfoldTransitionEnabled:OneOSColorHingeEnabled config_unfoldTransitionHingeAngle:OneOSColorHingeAngle; do
        cmd overlay fabricate --target android --name "${spec#*:}" "android:bool/${spec%:*}" 0x12 1
        cmd overlay enable --user 0 "com.android.shell:${spec#*:}"
    done
    for spec in com.oplus.aod:Fold8Aod.apk com.oplus.pantanal.ums:Fold8UMS.apk com.nearme.instant.platform:Fold8Instant.apk; do
        pkg=${spec%:*}; apk="$D/${spec#*:}"
        [ -f "$apk" ] || continue
        if [ -z "$(pm path "$pkg" 2>/dev/null)" ]; then
            pm install -r --abi arm64-v8a --user 0 "$apk"
        fi
    done
    # This stock AOD declares extractNativeLibs=false. Repair its on-disk
    # arm64 path only while it is still our exact donor, never a user update.
    aod=$(pm path com.oplus.aod | sed -n 's/^package://p' | head -1)
    case "$aod" in /data/app/*/base.apk)
        if [ "$(sha256sum "$aod" | cut -d' ' -f1)" = 87bfba25e06a5081f5feef73aef15a90dbc9b9f39b1fe756c68fd9975ac38638 ]; then
            libdir=${aod%/base.apk}/lib/arm64
            mkdir -p "$libdir"
            for entry in $("$BB" unzip -l "$aod" | "$BB" awk 'split($4, p, "/") == 3 && p[1] == "lib" && p[2] == "arm64-v8a" && p[3] ~ /^lib.*[.]so$/ {print $4}'); do
                "$BB" unzip -p "$aod" "$entry" > "$libdir/${entry##*/}"
                chmod 644 "$libdir/${entry##*/}"
            done
            chmod 755 "${libdir%/arm64}" "$libdir"
            restorecon -RF "${libdir%/arm64}"
        fi
    ;; esac
    home=$(cmd role get-role-holders --user 0 android.app.role.HOME)
    resolved=$(cmd package resolve-activity --brief --user 0 -a android.intent.action.MAIN -c android.intent.category.HOME | tail -1)
    if [ "$home" = com.android.settings ] && [ "$resolved" = com.android.launcher/.Launcher ]; then
        cmd package set-home-activity --user 0 com.android.launcher/.Launcher
    fi
    # SystemUI saves depth masks here but has a distinct app UID on this image.
    uid=$(cmd package list packages -U com.android.systemui | sed -n 's/^package:com[.]android[.]systemui uid://p' | head -1)
    case "$uid" in ''|*[!0-9]*) echo 'Depth storage: SystemUI UID unavailable';;
    *)
        depth=/data/oplus/os
        if [ -d "$depth" ] && [ ! -L "$depth" ]; then
            chmod 701 "$depth"
            for n in deep_scenery_image0 deep_scenery_image_secondaryDisplay0; do
                [ ! -L "$depth/$n" ] || continue
                [ -f "$depth/$n" ] || touch "$depth/$n"
                chown "$uid:$uid" "$depth/$n"
                chmod 600 "$depth/$n"
            done
        fi
        ;;
    esac
    settings put global fluid_cloud_not_support 0
    uri=content://com.oplus.customize.coreapp.configmanager.configprovider.AppFeatureProvider/app_feature
    profile=$(cat "$D/profile" 2>/dev/null)
    # Z Fold8 Ultra: 0.4.38 test8 turned the taskbar off (its window held the cover
    # screen 0.9 s on a fold); the owner wants it, and large-screen mode now loads
    # (guest_prepare.sh, my_product features). Back on once where test8 took it off.
    if [ "$profile" = f8u ] && [ -f "$D/no-taskbar-v1" ] && [ ! -f "$D/taskbar-back-v1" ]; then
        settings put system enable_launcher_taskbar 1
        touch "$D/taskbar-back-v1"
        reload=1
    fi
    if ! content query --uri "$uri" --where 'featurename="com.android.launcher.TASKBAR_ENABLE"' 2>/dev/null | grep -q 'featurename=com.android.launcher.TASKBAR_ENABLE'; then
        content insert --uri "$uri" --bind featurename:s:com.android.launcher.TASKBAR_ENABLE --bind parameters:s:
        reload=1
    fi
    # The Find N6 global build's launcher is an export launcher. Pull request #1
    # marked it CN_VERSION for the CN build; on the global one that made
    # FeatureOption.isExp false, and with it Circle to Search on the taskbar
    # handle (0.4.38: the launcher restarted by this script took the Breeno
    # branch). The global build has com.oppo.quicksearchbox too, so no app
    # decides it: n6-f8u is global only, CN_VERSION goes wherever it is.
    if content query --uri "$uri" --where 'featurename="com.android.launcher.CN_VERSION"' 2>/dev/null | grep -q 'featurename=com.android.launcher.CN_VERSION'; then
        content delete --uri "$uri" --where 'featurename="com.android.launcher.CN_VERSION"'
        reload=1
    fi
    if [ ! -f "$D/defaults-v1" ]; then
        settings put system enable_launcher_taskbar 1
        settings put secure oplus_keyguard_workshop_aod_support 1
        settings put secure Setting_AodState 1
        settings put secure Setting_AodState_Local 1
        touch "$D/defaults-v1"
    fi
    ui=$(pidof com.android.systemui | cut -d' ' -f1)
    if [ -n "$ui" ]; then
        uid=$(stat -c %u /proc/$ui)
        mkdir -p /data/oneos_hinge
        chown 1000:"$uid" /data/oneos_hinge; chmod 2750 /data/oneos_hinge
        chcon u:object_r:system_data_file:s0 /data/oneos_hinge
        if ! ps -A -o ARGS | grep -q '[a]pp_process /system/bin OneOSAngleRelay '; then
            # The data tree survives guest sessions. An old nonempty frame
            # must not make the wait below restart SystemUI before this guest's
            # producer has published its first readable sample.
            rm -f /data/oneos_hinge/angle.bin
            z=$(pidof zygote64 | cut -d' ' -f1)
            (umask 027; CLASSPATH="$D/Fold8AngleRelay.dex" "$BB" nohup "$BB" setuidgid system /system/bin/app_process /system/bin OneOSAngleRelay /data/oneos_hinge/angle.bin "$z" >/data/local/tmp/oneos-angle.log 2>&1 </dev/null &)
            # Let the fresh relay frame exist before SystemUI reselects its provider.
            for n in 1 2 3 4 5; do [ ! -s /data/oneos_hinge/angle.bin ] || break; sleep 1; done
            [ ! -s /data/oneos_hinge/angle.bin ] || reload=1
        fi
    fi
    if [ "$reload" = 1 ]; then
        for pkg in com.android.launcher com.android.systemui; do
            p=$(pidof "$pkg"); [ -z "$p" ] || kill -TERM $p
        done
    fi
    ;;
*) fail 'expected prepare or runtime' ;;
esac
