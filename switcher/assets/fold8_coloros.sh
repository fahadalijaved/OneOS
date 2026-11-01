#!/system/bin/sh
# Fold8 / Find N6 only. Called by the checked session scripts; never in One UI
# for runtime. Binaries come through the normal pinned n6-f8 package set.
set -e
STAGE=${STAGE:-/data/local/tmp/oneos}
BB=${BB:-/data/oneos_bin/busybox}
fail() { echo "Fold8 ColorOS: $*" >&2; exit 3; }
selected() {
    [ "${ONEOS_PROFILE:-}" = f8 ] &&
        grep -q '^  "image": "coloros17-findn6",$' "$STAGE/.oneos_stage" &&
        grep -q '^  "set": "n6-f8",$' "$STAGE/.oneos_stage"
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
perf_state() { echo "$STAGE/performance_handover"; }
perf_log() { echo "$(date +%T) $*" >> "$STAGE/performance_handover.log"; }
perf_guest() {
    for q in $(pidof system_server); do
        [ "$(stat -Lc %d:%i /proc/$q/root/data 2>/dev/null)" = "$(stat -Lc %d:%i "$STAGE/data")" ] && { echo "$q"; return; }
    done
    return 1
}
perf_snapshot() {
    selected || return 0
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
    perf_log "snapshot ($1): cpu=$(cat "$PSTATE/cpu.before") gpu=$(cat "$PSTATE/gpu.before")MHz"
}
perf_valid() {
    PSTATE=$(perf_state)
    plain_tree "$PSTATE"
    [ -f "$PSTATE/boot" ] && [ "$(cat "$PSTATE/boot")" = "$(cat /proc/sys/kernel/random/boot_id)" ]
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
    selected || return 0
    perf_valid || fail 'no performance snapshot for this boot'
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
    gpu_top=$(awk '{for(i=1;i<=NF;i++)if($i>m)m=$i}END{print int(m/1000000)}' /sys/class/kgsl/kgsl-3d0/gpu_available_frequencies)
    case "$gpu_top" in ''|*[!0-9]*) return 1;; esac
    mode=$(cat "$PSTATE/mode"); released=0; level=-1
    while [ ! -f "$PSTATE/stop" ] && [ ! -f "$STAGE/data/oneos_rec_stop" ]; do
        gp=$(perf_guest) || return 0
        skin=$(timeout 3 "$BB" nsenter -t "$gp" -m -r -- /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys thermalservice 2>/dev/null |
          sed -n '/^Current temperatures from HAL:/,/^Current cooling devices/p' | sed -n 's/.*mValue=\([0-9.]*\), mType=3, mName=SKIN,.*/\1/p' | head -1)
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
            prime=$(cat /sys/devices/system/cpu/cpufreq/policy6/cpuinfo_max_freq)
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
            target=$(awk -v max="$((gpu_top * pct / 100))" -v ceiling="$ceiling" '{for(i=1;i<=NF;i++){v=int($i/1000000);if(v<=max&&v<=ceiling&&v>m)m=v}}END{print m}' /sys/class/kgsl/kgsl-3d0/gpu_available_frequencies)
            perf_write /sys/kernel/gpu/gpu_max_clock gpu "$target"
            perf_log "thermal level $level->$new skin=${skin:-unknown} gpu=$gpu_t"
            level=$new
        fi
        sleep 2
    done
}

case "$1" in
performance-snapshot) perf_snapshot host ;;
performance-live)
    selected || exit 0
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
    target="$ROOTFS/system/system_ext/priv-app/SystemUI/SystemUI.apk"
    "$BB" umount -l "$target" 2>/dev/null || true
    [ -f "$target" ] && [ ! -L "$target" ] || fail 'unexpected SystemUI path'
    [ "$(sha256sum "$target" | cut -d' ' -f1)" = e6bf0e49649dc82117e7b9584c13dbcf737183d17c461cd6edcedcc127165f7e ] || fail 'SystemUI donor differs'
    "$BB" mount --bind "$STAGE/Fold8SystemUI.apk" "$target"
    "$BB" mount --make-private "$target"
    "$BB" mount -o remount,bind,ro "$STAGE/Fold8SystemUI.apk" "$target"
    dest="$STAGE/data/oneos_fold8"
    plain_tree "$dest"
    mkdir -p "$dest"
    for f in Fold8Aod.apk Fold8UMS.apk Fold8Instant.apk Fold8AngleRelay.dex; do
        cp -f "$STAGE/$f" "$dest/$f"
        chmod 644 "$dest/$f"
    done
    cp -f "$STAGE/OneOSFold8Geometry.dex" "$dest/OneOSFold8Geometry.dex"
    chmod 644 "$dest/OneOSFold8Geometry.dex"
    cp -f "$STAGE/fold8_coloros.sh" "$dest/runtime.sh"
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
    uid=$(cmd package list packages -U com.android.systemui | sed -n 's/.*uid://p' | head -1)
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
    if ! content query --uri "$uri" --where 'featurename="com.android.launcher.TASKBAR_ENABLE"' 2>/dev/null | grep -q 'featurename=com.android.launcher.TASKBAR_ENABLE'; then
        content insert --uri "$uri" --bind featurename:s:com.android.launcher.TASKBAR_ENABLE --bind parameters:s:
        reload=1
    fi
    # Prefer the export search path only when both global components exist.
    if pm path com.oppo.quicksearchbox >/dev/null 2>&1 && pm path com.oplus.aiassistant >/dev/null 2>&1; then
        content delete --uri "$uri" --where 'featurename="com.android.launcher.CN_VERSION"'
        settings put system system_tokyo_search_ai_enable 1
        reload=1
    elif ! content query --uri "$uri" --where 'featurename="com.android.launcher.CN_VERSION"' 2>/dev/null | grep -q 'featurename=com.android.launcher.CN_VERSION'; then
        content insert --uri "$uri" --bind featurename:s:com.android.launcher.CN_VERSION --bind parameters:s:
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
