#!/system/bin/sh
# Optional display only: every failure leaves the original boot/return path intact.
ONEOS_BOOT_DIR=${ONEOS_BOOT_DIR:-/data/local/tmp/oneos/data/oneos_bootui}
oneos_boot_write() {
    [ -d "$ONEOS_BOOT_DIR" ] || return 0
    oneos_boot_tmp=$(mktemp "$ONEOS_BOOT_DIR/$1.XXXXXX") || return 0
    if ! { printf '%s\n' "$2" > "$oneos_boot_tmp" && mv -f "$oneos_boot_tmp" "$ONEOS_BOOT_DIR/$1"; }; then
        rm -f "$oneos_boot_tmp"
    fi
}
oneos_boot_event() {
    [ "$(cat "$ONEOS_BOOT_DIR/verbose" 2>/dev/null)" = 1 ] || return 0
    oneos_boot_write status "$*"
    printf '%s %s\n' "$(date +%T)" "$*" >> "$ONEOS_BOOT_DIR/events.log"
}
oneos_boot_stop() { touch "$ONEOS_BOOT_DIR/stop" 2>/dev/null; }
oneos_boot_ready() {
    [ -f "$ONEOS_BOOT_DIR/ready" ] || return 1
    read -r oneos_boot_pid oneos_boot_token < "$ONEOS_BOOT_DIR/ready" || return 1
    case "$oneos_boot_pid" in ''|*[!0-9]*) return 1;; esac
    [ "$oneos_boot_token" = "$(cat "$ONEOS_BOOT_DIR/generation" 2>/dev/null)" ] || return 1
    tr '\0' ' ' 2>/dev/null < "/proc/$oneos_boot_pid/cmdline" | grep -q 'OneOSBootStatus' && kill -0 "$oneos_boot_pid" 2>/dev/null
}
# A cold renderer must post its first buffer before we choose a live handoff.
# Never freeze its compositor while it is still initializing fonts/buffers.
oneos_boot_wait_ready() {
    oneos_boot_deadline=$(( $(date +%s) + ${1:-5} ))
    while :; do
        oneos_boot_ready && return 0
        [ ! -f "$ONEOS_BOOT_DIR/stop" ] || return 1
        [ "$(date +%s)" -lt "$oneos_boot_deadline" ] || return 1
        sleep 0.1
    done
}
oneos_boot_begin() {
    [ ! -L "$ONEOS_BOOT_DIR" ] || return 0
    mkdir -p "$ONEOS_BOOT_DIR" || return 0
    touch "$ONEOS_BOOT_DIR/stop"
    # A generation also retires any old worker after the stop flag is cleared.
    oneos_boot_write generation "$(date +%s)-$$"
    sleep 0.2
    rm -f "$ONEOS_BOOT_DIR/stop" "$ONEOS_BOOT_DIR/ready"
    if [ "$1" = enter ]; then
        : > "$ONEOS_BOOT_DIR/events.log"
        : > "$ONEOS_BOOT_DIR/renderer.log"
        oneos_boot_write verbose "${ONEOS_VERBOSE_BOOT:-0}"
        oneos_boot_image=$(sed -n 's/.*"image"[[:space:]]*:[[:space:]]*"\([a-z0-9-]*\)".*/\1/p' /data/local/tmp/oneos/.oneos_stage)
        case "$oneos_boot_image" in pixel*) oneos_boot_name='Pixel';; hyper*) oneos_boot_name='HyperOS';; nothing*) oneos_boot_name='Nothing OS 5.0';; infinity*) oneos_boot_name='Infinity-X 4.1';; *) oneos_boot_name='ColorOS 17';; esac
        oneos_boot_write system_name "$oneos_boot_name"
        oneos_boot_write title "Launching into $oneos_boot_name"
    else
        oneos_boot_write title 'Returning to One UI'
    fi
    oneos_boot_write status 'Preparing display'
    cp /data/local/tmp/oneos/oneos_boot_icon.png "$ONEOS_BOOT_DIR/icon.png" 2>/dev/null
    chmod 755 "$ONEOS_BOOT_DIR"; chmod 644 "$ONEOS_BOOT_DIR"/verbose "$ONEOS_BOOT_DIR"/title "$ONEOS_BOOT_DIR"/system_name "$ONEOS_BOOT_DIR"/icon.png 2>/dev/null
    /system/bin/sh /data/local/tmp/oneos/boot_status.sh supervise "$(cat "$ONEOS_BOOT_DIR/generation")" </dev/null >> "$ONEOS_BOOT_DIR/renderer.log" 2>&1 &
}
# Record init requests at the call site, not invented progress percentages.
setprop() {
    case "$1" in ctl.start) oneos_boot_event "Starting $2";; ctl.stop) oneos_boot_event "Stopping $2";; ctl.restart) oneos_boot_event "Restarting $2";; esac
    /system/bin/setprop "$@"
}
if [ "${1:-}" = supervise ]; then
    # The launching app's cgroup is stopped with its framework. Detach this
    # optional display worker; the separate return watcher remains protected.
    echo $$ > /sys/fs/cgroup/cgroup.procs 2>/dev/null || true
    echo -500 > /proc/$$/oom_score_adj 2>/dev/null || true
    generation=$2
    current() { [ "$(cat "$ONEOS_BOOT_DIR/generation" 2>/dev/null)" = "$generation" ] && [ ! -f "$ONEOS_BOOT_DIR/stop" ]; }
    fifo="$ONEOS_BOOT_DIR/events.$generation.pipe"
    mkfifo "$fifo" || exit 0
    # Keep both PIDs so a quiet log buffer cannot strand a producer on return.
    logcat -b events -v brief -T 1 > "$fifo" &
    logger=$!
    (
        new_framework=0
        while IFS= read -r event && current; do
            case "$event" in
                *boot_progress_system_run*) new_framework=1; oneos_boot_event 'Starting system_server';;
                *boot_progress_pms_start*) new_framework=1; oneos_boot_event 'Loading package manager';;
                *boot_progress_pms_ready*) oneos_boot_event 'Package manager ready';;
                *boot_progress_ams_ready*) oneos_boot_event 'Activity manager ready';;
                *boot_progress_enable_screen*) [ "$new_framework" = 1 ] && { oneos_boot_event 'Display ready'; sleep 0.4; current && oneos_boot_stop; break; };;
                *am_proc_start*) process=$(printf '%s\n' "$event" | sed 's/.*\[//' | cut -d, -f4 | cut -c1-100); [ -n "$process" ] && oneos_boot_event "Starting $process";;
                *am_proc_died*) process=$(printf '%s\n' "$event" | sed 's/.*\[//' | cut -d, -f3 | cut -c1-100); [ -n "$process" ] && oneos_boot_event "Stopped $process";;
            esac
        done < "$fifo"
    ) &
    monitor=$!
    stop_worker() {
        [ -n "${worker:-}" ] || return 0
        case "$(tr '\0' ' ' 2>/dev/null < "/proc/$worker/cmdline")" in
            *"OneOSBootStatus $ONEOS_BOOT_DIR $generation"*) kill "$worker" 2>/dev/null ;;
        esac
    }
    cleanup() {
        stop_worker
        kill "$monitor" "$logger" 2>/dev/null
        rm -f "$fifo"
        [ "$(cat "$ONEOS_BOOT_DIR/generation" 2>/dev/null)" != "$generation" ] || oneos_boot_stop
    }
    trap cleanup EXIT
    trap 'exit 0' HUP INT TERM
    end=$(( $(date +%s) + 600 ))
    saw_animation=0
    while current && [ "$(date +%s)" -lt "$end" ]; do
        sf=$(pidof surfaceflinger 2>/dev/null)
        CLASSPATH=/data/local/tmp/oneos/OneOSBootStatus.dex app_process /system/bin OneOSBootStatus "$ONEOS_BOOT_DIR" "$generation" &
        worker=$!
        while current && kill -0 "$worker" 2>/dev/null && [ "$(date +%s)" -lt "$end" ]; do
            case "$(getprop service.bootanim.exit 2>/dev/null)" in
                0) saw_animation=1 ;;
                1) [ "$saw_animation" = 0 ] || { oneos_boot_event 'Display ready'; oneos_boot_stop; break; } ;;
            esac
            [ "$(pidof surfaceflinger 2>/dev/null)" = "$sf" ] || break
            sleep 0.3
        done
        # Reconnect a fresh SurfaceComposer client after the compositor is replaced.
        stop_worker
        wait "$worker" 2>/dev/null
        if [ "$(cut -d ' ' -f1 "$ONEOS_BOOT_DIR/ready" 2>/dev/null)" = "$worker" ]; then
            rm -f "$ONEOS_BOOT_DIR/ready"
        fi
        current || break
        sleep 0.5
    done
fi
