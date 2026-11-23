#!/bin/sh
# Stand-ins for Android's tools on a fake phone (OneiosScriptTest): one script
# under many names in $ONEIOS_TEST_ROOT/bin and the root manager's folder. The
# phone is a folder:
#   props               key=value, what getprop prints and setprop writes
#   pids/<name>         what pidof answers
#   services/<name>     registered with servicemanager ("/" as "_")
#   proc/<pid>/         a process: ns/mnt, comm, cmdline; ignore_term and
#                       unkillable are what it does with a signal
#   behave/<flag>       what goes wrong in this test
#   log/<tool>          what was asked of each tool, in order
# Nothing here signals, starts or stops a real process.
T=$ONEIOS_TEST_ROOT
[ -n "$T" ] && [ -d "$T/log" ] || { echo "phone-tools: no fake phone"; exit 99; }
me=${0##*/}
REAL_SLEEP=@SLEEP@

prop() { awk -v k="$1" 'index($0, k "=") == 1 { v = substr($0, length(k) + 2); f = 1 } END { if (f) print v }' "$T/props"; }
setp() {
    awk -v k="$1" 'index($0, k "=") != 1' "$T/props" > "$T/props.$$"
    echo "$1=$2" >> "$T/props.$$"
    mv "$T/props.$$" "$T/props"
}
delp() { awk -v k="$1" 'index($0, k "=") != 1' "$T/props" > "$T/props.$$"; mv "$T/props.$$" "$T/props"; }
newpid() { n=$(cat "$T/nextpid"); echo $((n + 1)) > "$T/nextpid"; echo "$n"; }
# A process of One UI's, in init's mount namespace.
spawn() { # <name>
    p=$(newpid)
    mkdir -p "$T/proc/$p/ns"
    ln -s "mnt:[1]" "$T/proc/$p/ns/mnt"
    echo "$1" > "$T/proc/$p/comm"
    printf '%s\0' "$1" > "$T/proc/$p/cmdline"
    echo "$p" > "$T/pids/$1"
    echo "$p"
}
unspawn() {
    for p in $(cat "$T/pids/$1" 2>/dev/null); do rm -rf "$T/proc/$p"; done
    rm -f "$T/pids/$1"
}
COMPOSER=vendor.qti.hardware.display.composer
start() { # <init service>
    [ -e "$T/behave/no_start_$1" ] && { setp "init.svc.$1" restarting; return 0; }
    case "$1" in
        zygote)
            spawn zygote64 > /dev/null
            [ -e "$T/behave/no_system_server" ] || spawn system_server > /dev/null ;;
        surfaceflinger)
            spawn surfaceflinger > /dev/null
            [ -e "$T/behave/sf_not_registered" ] || : > "$T/services/SurfaceFlinger" ;;
        audioserver)
            spawn audioserver > /dev/null
            [ -e "$T/behave/audio_not_registered" ] || { : > "$T/services/media.audio_policy"; : > "$T/services/media.audio_flinger"; } ;;
        "$COMPOSER")
            p=$(spawn composer)
            setp "init.svc_debug_pid.$1" "$p"
            : > "$T/services/android.hardware.graphics.composer3.IComposer_default" ;;
        netd)
            spawn netd > /dev/null
            # AOSP's netd.rc: onrestart restart zygote.
            [ -e "$T/behave/netd_no_onrestart" ] || [ "$2" != restart ] || { setp init.svc.netd running; start zygote; } ;;
        *) spawn "$1" > /dev/null ;;
    esac
    setp "init.svc.$1" running
}
stop() { # <init service>
    case "$1" in
        zygote) unspawn zygote64; unspawn system_server ;;
        surfaceflinger) unspawn surfaceflinger; rm -f "$T/services/SurfaceFlinger" ;;
        audioserver) unspawn audioserver; rm -f "$T/services/media.audio_policy" "$T/services/media.audio_flinger" ;;
        "$COMPOSER") unspawn composer; rm -f "$T/services/android.hardware.graphics.composer3.IComposer_default" ;;
        *) unspawn "$1" ;;
    esac
    setp "init.svc.$1" stopped
}
hang() { # a call that does not come back (until the test lets it)
    n=0
    while [ ! -e "$T/behave/unhang" ] && [ $n -lt 300 ]; do "$REAL_SLEEP" 0.1; n=$((n + 1)); done
}

case "$me" in
    getprop)
        if [ $# -eq 0 ]; then sed 's/^\([^=]*\)=\(.*\)$/[\1]: [\2]/' "$T/props"; else prop "$1"; fi ;;
    setprop)
        echo "$1 $2" >> "$T/log/setprop"
        [ -e "$T/behave/hang_$1_$2" ] && hang
        case "$1" in
            ctl.start) [ "$(prop "init.svc.$2")" = running ] || start "$2" ;;
            ctl.stop) stop "$2" ;;
            ctl.restart)
                [ -e "$T/behave/no_restart_$2" ] && exit 0
                stop "$2"; start "$2" restart
                # The composer's clients go with it: surfaceflinger is started again.
                if [ "$2" = "$COMPOSER" ] && [ ! -e "$T/behave/sf_survives_composer" ]; then stop surfaceflinger; start surfaceflinger; fi ;;
            sys.powerctl) setp "$1" "$2" ;;
            *) setp "$1" "$2" ;;
        esac ;;
    resetprop)
        echo "$*" >> "$T/log/resetprop"
        case "$1" in -n) setp "$2" "$3" ;; --delete) delp "$2" ;; esac ;;
    pidof)
        [ -s "$T/pids/$1" ] || exit 1
        tr '\n' ' ' < "$T/pids/$1" | sed 's/ $//'; echo ;;
    service)
        [ "$1" = check ] || exit 1
        if [ -e "$T/services/$(echo "$2" | tr / _)" ]; then echo "Service $2: found"; else echo "Service $2: not found"; fi ;;
    getenforce) cat "$T/selinux" ;;
    am)
        echo "$*" >> "$T/log/am"
        if [ -e "$T/behave/locked" ]; then echo RUNNING_LOCKED; else echo RUNNING_UNLOCKED; fi ;;
    vdc|sync|renice|lshal) echo "$me $*" >> "$T/log/calls" ;;
    busybox)
        echo "$*" >> "$T/log/busybox"
        case "$1" in setsid) shift; exec "$@" ;; esac ;;
    # The fake phone's clock runs sleep_scale times faster: a sleep is that
    # much shorter, and "now" counts that many seconds in each real one.
    sleep)
        k=$(cat "$T/sleep_scale" 2>/dev/null)
        exec "$REAL_SLEEP" "$(awk -v s="$1" -v k="${k:-100}" 'BEGIN { printf "%.3f", s / k }')" ;;
    now)
        k=$(cat "$T/sleep_scale" 2>/dev/null)
        # BSD's date (macOS) has no %N: it prints the seconds and a literal N, the sum below failed, and "now"
        # printed nothing (Gate A's 30 s wait ended at once). perl's clock there; the first call marks it.
        if [ -e "$T/now.perl" ]; then ns=
        else ns=$(date +%s%N); case "$ns" in ''|*[!0-9]*) ns=; true > "$T/now.perl" ;; esac
        fi
        [ -n "$ns" ] || ns=$(perl -MTime::HiRes=time -e 'printf "%.0f", time * 1e9')
        echo $((ns / (1000000000 / ${k:-100}))) ;;
    kill)
        echo "$*" >> "$T/log/kill"
        sig=TERM
        rc=0
        for a in "$@"; do
            case "$a" in
                --) continue ;;
                -[A-Z]*) sig=${a#-}; continue ;;
                -9) sig=KILL; continue ;;
                -0) sig=0; continue ;;
            esac
            p=${a#-}
            [ -d "$T/proc/$p" ] || { rc=1; continue; }
            case "$sig" in
                0) continue ;;
                TERM) [ -e "$T/proc/$p/ignore_term" ] && continue ;;
                KILL) [ -e "$T/proc/$p/unkillable" ] && continue
                    # kills_left N: a process that ends only at the Nth SIGKILL (one that leaves
                    # an uninterruptible system call late, as on the phone on 2026-11-12)
                    if [ -f "$T/proc/$p/kills_left" ]; then
                        n=$(($(cat "$T/proc/$p/kills_left") - 1))
                        [ $n -le 0 ] || { echo $n > "$T/proc/$p/kills_left"; continue; }
                    fi ;;
            esac
            # Its tasks die with it (PR_SET_PDEATHSIG), unless they cannot.
            for c in $(cat "$T/proc/$p/children" 2>/dev/null) "$p"; do
                [ -e "$T/proc/$c/unkillable" ] && continue
                rm -rf "$T/proc/$c"
                cg="$T/sys/fs/cgroup/oneios_session/cgroup.procs"
                [ -f "$cg" ] && { grep -v -x "$c" "$cg" > "$cg.$$"; mv "$cg.$$" "$cg"; }
            done
        done
        exit $rc ;;
    getevent)
        dev=${2##*/}
        case "$1" in
            -pl) cat "$T/keystate/$dev" 2>/dev/null ;;
            -lq)
                # The device's events as the test wrote them: "@ N" waits N
                # (real) seconds, any other line is an event. Then it blocks,
                # as getevent does on a quiet device.
                while read -r a b rest; do
                    if [ "$a" = "@" ]; then "$REAL_SLEEP" "$b"; else echo "$a $b $rest"; fi
                done < "$T/events/$dev"
                n=0
                while [ ! -e "$T/events/stop" ] && [ $n -lt 300 ]; do "$REAL_SLEEP" 0.1; n=$((n + 1)); done ;;
        esac ;;
    *) echo "phone-tools: no stand-in for $me"; exit 99 ;;
esac
