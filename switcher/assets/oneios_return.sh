#!/system/bin/sh
# Back to One UI from a OneiOS session (oneios_switch.sh). docs/oneios.md.
#
#   oneios_return.sh [who]      in place when every check holds, else a reboot
#   oneios_return.sh reboot     straight to the reboot
#   oneios_return.sh --guard T  (internal) this return's own dead-man timer
#
# In place (the structure of return_to_oneui.sh, docs/inplace-return.md,
# shorter: an iOS session mounts nothing in init's namespace, changes no
# property and never talks to One UI's services):
#   1  stop the session: SIGTERM to xnuhost, 20 s, then SIGKILL to everything
#      in its cgroup and its mount namespace; the key readers and the watcher end.
#   A  nothing of the session is left: no process in its namespace or cgroup,
#      the stage mounted in no process's mount table, the same boot, vold,
#      keystore2 and servicemanager with the pids of the switch, SELinux as it
#      was.
#   B  the stop loop is gone; One UI's boot counters are back; the display is
#      One UI's again (the composer and surfaceflinger restarted, the boot
#      animation); audioserver and the rest of zygote's restart list; the
#      services One UI's framework waits for are registered; the USB gadget and
#      adbd are One UI's again (control/base/usb); in the Android takeover each
#      service it stopped (control/base/stopped) runs again; zygote starts.
#   C  system_server keeps its pid until user 0 is unlocked and 20 s more.
# Never ":" with a redirection in this script or in oneios_switch.sh: ":" is a
# special builtin, and Android's sh (mksh) ends the whole script, without a
# word, when its redirection fails. "true" is not one.
# Any failed check ends in failsafe(): a reboot, which is always a correct way
# back (nothing of the session survives one, and nothing of One UI's was
# written). A return that does not finish is rebooted by its guard.

# Tests (OneiosScriptTest) set ONEIOS_TEST_ROOT to a folder that stands for /:
# its proc, sys, stage and root tools, its bin/ first on PATH, its bin/kill
# and bin/sleep in place of the shell's, so a test never signals a real
# process, and its bin/now as the clock (a test's seconds are shorter). Never
# as root; on a phone the variable is dropped instead, because this script
# must not refuse to return.
T="${ONEIOS_TEST_ROOT:-}"
if [ -n "$T" ] && [ "$(id -u 2>/dev/null)" = 0 ]; then
    if [ -e /system/build.prop ]; then T=""; else echo "oneios_return.sh: ONEIOS_TEST_ROOT is for tests, never as root"; exit 3; fi
fi
if [ -n "$T" ]; then
    PATH="$T/bin:$PATH"; export PATH
    kill() { "$T/bin/kill" "$@"; }
    sleep() { "$T/bin/sleep" "$@"; }
    now() { "$T/bin/now"; }
else
    now() { date +%s; }
fi
SH=/system/bin/sh
[ -z "$T" ] || SH="${ONEIOS_TEST_SH:-/bin/sh}"
P="$T/proc"
BB=""
for c in /data/adb/ksu/bin/busybox /data/adb/ap/bin/busybox /data/adb/magisk/busybox; do
    [ -x "$T$c" ] && { BB=$T$c; break; }
done
RP=""
for c in /data/adb/ksu/bin/resetprop /data/adb/ap/bin/resetprop /debug_ramdisk/resetprop /sbin/resetprop; do
    [ -x "$T$c" ] && { RP=$T$c; break; }
done
S="$T/data/local/tmp/oneios"
# The stage as mount tables show it: its path, and its path on /data's own
# filesystem (the source of a bind from it, mountinfo's fourth field).
SM=/data/local/tmp/oneios
SRC=/local/tmp/oneios
# The way back's own folder (oneios_switch.sh): the state, the baseline, the
# pids. Read-only in xnuhost's namespace.
CTL=$S/control
BASE=$CTL/base
LOG=$S/return.log
# xnuhost's cgroup (oneios_switch.sh --inner). Only ever this one path.
CG="$T/sys/fs/cgroup/oneios_session"
WHO="${1:-manual}"
# Every wait below has its own limit and its own failsafe; all of them
# together, each used up to its last second, come to about 7 minutes (20 s for
# xnuhost, the display and audio waits, 60 s for system_server, 180 s for the
# unlock, 20 s after it). The guard is for what has no limit: a command that
# never comes back. Past this it reboots.
GUARD_MAX=600
[ -z "$T" ] || GUARD_MAX="${ONEIOS_TEST_GUARD_MAX:-$GUARD_MAX}"
# Each step also has a limit of its own (step, below): 90 s to stop the
# session, 45 s for Gate A, 75 s for Gate B, 45 s to start One UI's zygote,
# 290 s for Gate C. (A test's clock runs faster than its commands: its limits
# are that much longer.)
STEP_K=1
[ -z "$T" ] || STEP_K="${ONEIOS_TEST_STEP_K:-40}"

[ -n "$T" ] || [ "$(id -u 2>/dev/null)" = 0 ] || { echo "oneios_return.sh: not root"; exit 2; }
# The return must finish even if whatever started it goes away.
trap '' HUP PIPE
# (2>/dev/null first: a path that is not there is not worth a line.)
echo $$ 2>/dev/null > "$T/sys/fs/cgroup/cgroup.procs"
echo -1000 2>/dev/null > "$P/$$/oom_score_adj"

# Every line to the caller and to the log; once only where the caller's
# output is the log itself (the watcher, the app's root script, the key readers).
TEE=1
[ "/proc/$$/fd/1" -ef "$LOG" ] && TEE=0
# The core:root tests on a machine without /proc (a Mac) say it themselves, as
# ONEIOS_CHECK_LIMIT is a test's: only with a test root, never on the phone.
[ -n "$T" ] && [ "${ONEIOS_TEST_OUT_IS_LOG:-0}" = 1 ] && TEE=0
say() {
    m="$(date +%T) $*"
    echo "$m"
    [ $TEE = 0 ] || echo "$m" >> "$LOG"
}
# A step and its own time limit in seconds (return.watch, for the guard): a
# step that stands still is rebooted out of at its limit, not at the guard's.
step() { # <title> <seconds>
    echo "$1" 2>/dev/null > "$CTL/return.step"
    echo "$(($2 * STEP_K)) $1" 2>/dev/null > "$CTL/return.watch"
    say "=== $1 ==="
}
# sync, waited for 5 s at most: a sync that stands still (a stuck disk or
# FUSE) must not keep the reboot's last resorts from running.
sync_bounded() {
    sync &
    sb=$!; sn=0
    while [ $sn -lt 25 ] && [ -d "$P/$sb" ]; do sleep 0.2; sn=$((sn + 1)); done
}
do_reboot() { # <reason word>
    # Nothing of the session's on the screen while the phone restarts.
    bootui_end
    sync_bounded
    setprop sys.powerctl "reboot,$1"
    sleep 20
    # init did not reboot: Android's own reboot, then busybox's (KernelSU's busybox has no reboot applet: then it
    # only prints that), then sysrq as the last resort.
    sync_bounded
    # (In the background: Android's reboot waits for init for ever once it set the property.)
    [ -x "$T/system/bin/reboot" ] && "$T/system/bin/reboot" "$1" </dev/null >/dev/null 2>&1 &
    sleep 5
    [ -n "$BB" ] && "$BB" reboot -f
    sleep 5
    echo 1 > "$P/sys/kernel/sysrq" 2>/dev/null
    echo s > "$P/sysrq-trigger" 2>/dev/null
    sleep 2
    echo b > "$P/sysrq-trigger" 2>/dev/null
    exit 1
}
failsafe() {
    say "FAILSAFE: $* - rebooting into One UI instead"
    echo "failsafe $(date +%s) $*" > "$S/return.outcome"
    do_reboot oneios-inplace-failsafe
}
# The shmem THP mode back to the bare mode the switch saved ($BASE/shmem_enabled;
# the switch writes advise for xnuhost's 2 MiB host pages, under its stop lock).
# The node lists every mode with the active one in brackets: compare and write
# bare modes, never the whole line (2026-11-16: the line written back was EINVAL,
# Gate A failed and the phone rebooted). Read back after the write. <on failure:
# failsafe (One UI was stopped) or say (it never was)>. Nothing without a saved mode.
# (Ported from YMGPwcca/OneOS 403d8b4: the early return restores it too.)
SHMEM_EN="$T/sys/kernel/mm/transparent_hugepage/shmem_enabled"
shmem_mode() {
    awk 'NF == 1 && $1 ~ /^[a-z_]+$/ { print $1; exit }
        { for (i = 1; i <= NF; i++) if ($i ~ /^\[[a-z_]+\]$/) { print substr($i, 2, length($i) - 2); exit } }' "$SHMEM_EN" 2>/dev/null
}
shmem_restore() {
    [ -f "$BASE/shmem_enabled" ] || return 0
    shmem_old=$(cat "$BASE/shmem_enabled" 2>/dev/null)
    case "$shmem_old" in
        always|within_size|advise|never|deny|force) ;;
        *) "$1" "shmem_enabled: the switch's saved mode '$shmem_old' is not a mode: not written"; rm -f "$BASE/shmem_enabled"; return 0 ;;
    esac
    [ -f "$SHMEM_EN" ] || { rm -f "$BASE/shmem_enabled"; return 0; }
    shmem_now=$(shmem_mode)
    if [ "$shmem_now" != "$shmem_old" ]; then
        if ! printf '%s\n' "$shmem_old" 2>/dev/null > "$SHMEM_EN" || [ "$(shmem_mode)" != "$shmem_old" ]; then
            "$1" "shmem_enabled is $(shmem_mode), was $shmem_old at the switch, and the write back failed"
            return 0
        fi
        say "shmem_enabled back: $shmem_old"
    fi
    rm -f "$BASE/shmem_enabled"
}
# vm.swappiness back to One UI's: the Android takeover's takeover-swappiness= (oneios_switch.sh takeover_memory saved
# One UI's value in $BASE/swappiness before its write). Read back after the write. Logged, never a reason for the
# failsafe: it is no part of the way back, and a restart sets One UI's own. Nothing without a saved value.
swappiness_restore() {
    [ -f "$BASE/swappiness" ] || return 0
    sw_old=$(cat "$BASE/swappiness" 2>/dev/null)
    case "$sw_old" in
        ''|*[!0-9]*) say "vm.swappiness: the switch's saved value '$sw_old' is not a number: not written" ;;
        *)
            if echo "$sw_old" 2>/dev/null > "$P/sys/vm/swappiness" && [ "$(cat "$P/sys/vm/swappiness" 2>/dev/null)" = "$sw_old" ]; then
                say "vm.swappiness back: $sw_old"
            else
                say "vm.swappiness is $(cat "$P/sys/vm/swappiness" 2>/dev/null || echo -), was $sw_old at the switch, and the write back failed (logged only)"
            fi ;;
    esac
    rm -f "$BASE/swappiness"
}
base_prop() { sed -n "s/^\[$1\]: \[\(.*\)\]\$/\1/p" "$BASE/props" 2>/dev/null | head -n 1; }
base_has() { grep -q "^\[$1\]: " "$BASE/props" 2>/dev/null; }
# A non-persist prop back to its value at the switch, in memory only
# (resetprop -n: no property triggers), or deleted if One UI had none.
put_back() {
    if base_has "$1"; then "$RP" -n "$1" "$(base_prop "$1")" 2>/dev/null
    else "$RP" --delete "$1" 2>/dev/null; fi
}
# Is this pid still one of our own shells? A pid file outlives its process and
# ids are reused: nothing is signalled by a pid alone.
is_ours() { # <pid> <script and mode words>
    # cat, then tr: a process that ends between the open and the read makes the
    # read fail (ESRCH), and toybox's tr reads again for ever on a failed read
    # (the S24 Ultra, 2026-11-11: the stop loop ended just then, and Gate B
    # stood still on this line with a black screen). cat ends on the error.
    case "$(cat "$P/$1/cmdline" 2>/dev/null | tr '\0' ' ')" in *"$2"*) return 0 ;; esac
    return 1
}
# Ends one of oneios_switch.sh's helpers by its pid file.
end_helper() { # <pid file> <mode word>
    for p in $(cat "$1" 2>/dev/null); do
        is_ours "$p" "oneios_switch.sh $2" && kill -9 "$p" 2>/dev/null
    done
}
# The stop loop's wait (xnuhost --prop-wait, its child, which sleeps on init's properties for up to 60 s): ended at
# once, so the loop sees control/stop-loop.off now. Only a process whose command line is that wait.
end_waiter() {
    for p in $(cat "$CTL/stop-loop.wait.pid" 2>/dev/null); do
        is_ours "$p" " --prop-wait 60 init.svc.zygote=running " && kill -9 "$p" 2>/dev/null
    done
}
# The services the Android takeover stopped (oneios_switch.sh takeover_stops: control/base/stopped), each a name of
# One UI's zygote's restart list, which this return starts again with the rest of that list.
TAKEOVER_STOPPABLE="cameraserver mediaextractor mediametrics media.tuner perfmond wificond netd media"
takeover_stopped() {
    for s in $(cat "$BASE/stopped" 2>/dev/null); do
        case " $TAKEOVER_STOPPABLE " in *" $s "*) echo "$s" ;; esac
    done
}
# The USB gadget and adbd back to One UI's (oneios_switch.sh, "USB AND ADB
# DURING A SESSION": control/base/usb, recorded at the switch), before One UI's
# zygote starts, so that its UsbDeviceManager finds them as it left them. Only
# what differs, only One UI's values: sys.usb.config (with its triggers: init
# or the HAL applies it), adbd, the gadget's UDC file. Named files and
# properties only. Logged; never a reason for the failsafe.
UDC_FILE="$T/config/usb_gadget/g1/UDC"
usb_read() { head -c 64 "$1" 2>/dev/null | tr -d '\n'; }
usb_name() { case "$1" in ''|.|..|*/*|*[!A-Za-z0-9._:-]*) echo "" ;; *) echo "$1" ;; esac; }
usb_now() {
    _uc=$(usb_name "$(getprop sys.usb.controller)")
    _us=""; [ -z "$_uc" ] || _us=$(usb_read "$T/sys/class/udc/$_uc/state")
    echo "state $(getprop sys.usb.state), config $(getprop sys.usb.config), UDC ${_uc:-?} ${_us:-?}; bound '$(usb_read "$UDC_FILE")', adbd $(getprop init.svc.adbd), ffs.ready $(getprop sys.usb.ffs.ready), cable $(usb_read "$T/sys/class/power_supply/usb/online")"
}
usb_restore() {
    U="$BASE/usb"
    [ -f "$U" ] || { say "usb: no record of the switch ($U): left as it is ($(usb_now))"; return 0; }
    ucfg=$(sed -n 's/^config=//p' "$U" | head -n 1)
    uctl=$(usb_name "$(sed -n 's/^controller=//p' "$U" | head -n 1)")
    ubound=$(sed -n 's/^udc=//p' "$U" | head -n 1)
    uadbd=$(sed -n 's/^adbd=//p' "$U" | head -n 1)
    say "usb: before the restore: $(usb_now)"
    # Only with the repairs on (the switch recorded repair=1: $S/usb-repair); off, by default, logged only.
    if [ "$(sed -n 's/^repair=//p' "$U" | head -n 1)" != 1 ]; then
        say "usb: repairs are off (no $S/usb-repair at the switch): nothing put back; One UI's were config '$ucfg', adbd '$uadbd', UDC '$ubound'"
        return 0
    fi
    cur=$(getprop sys.usb.config)
    if [ -n "$ucfg" ] && [ "$cur" != "$ucfg" ]; then
        setprop sys.usb.config "$ucfg"
        say "usb: sys.usb.config $cur -> $ucfg (One UI's)"
        un=0
        while [ $un -lt 15 ] && [ "$(getprop sys.usb.state)" != "$ucfg" ]; do sleep 0.2; un=$((un + 1)); done
    fi
    ua=$(getprop init.svc.adbd)
    if [ "$uadbd" = running ] && [ "$ua" != running ]; then
        setprop ctl.start adbd
        say "usb: adbd was '$ua': ctl.start adbd"
    fi
    if [ -n "$uctl" ] && [ "$ubound" = "$uctl" ]; then
        b=$(usb_read "$UDC_FILE")
        if [ -z "$b" ] || [ "$b" = none ]; then
            if echo "$uctl" 2>/dev/null > "$UDC_FILE"; then say "usb: UDC $uctl written back"
            else say "usb: UDC $uctl could not be written back (logged only)"; fi
        fi
    fi
    say "usb: after the restore: $(usb_now)"
    return 0
}
# The key readers lead process groups of their own (setsid): the reader, its
# getevent and its timers end together. A reader that is not a group leader
# has no such group, and is ended alone.
end_readers() {
    for p in $(cat "$CTL/keys/pids" 2>/dev/null); do
        is_ours "$p" "oneios_switch.sh --keys" || continue
        kill -9 -- "-$p" 2>/dev/null
        kill -9 "$p" 2>/dev/null
    done
}
# The boot screen of the switch (oneios_switch.sh: OneOS's boot_status.sh and
# its renderer, with the switch's feeder), where it is still up: iOS never
# drew, or ended before it did. Its status files are in control/bootui.
BOOTUI=$CTL/bootui
bootui() { # <a function of boot_status.sh> [arguments]; never fails
    [ -d "$BOOTUI" ] && [ -f "$S/bin/boot_status.sh" ] || return 0
    ( ONEOS_BOOT_DIR=$BOOTUI; ONEOS_BOOT_HOME=$S/bin; . "$S/bin/boot_status.sh" && "$@" ) >/dev/null 2>&1
    return 0
}
# Ends it, on every return: the stop flag and a new generation retire the
# supervisor, the renderer (which takes its layer away) and the feeder; they
# get a second, then SIGKILL, each by its pid and only while that pid is
# still what it was. One UI-side processes in init's namespace and the root
# cgroup: none of them is the session's for Gate A, and a renderer that could
# not be ended is logged only, because the composer restart of Gate B drops
# every layer it had. Nothing of the return waits for it longer than 2 s.
bootui_end() {
    [ -d "$BOOTUI" ] && [ ! -e "$BOOTUI/ended" ] || return 0
    true 2>/dev/null > "$BOOTUI/stop"
    echo "ended.$$" 2>/dev/null > "$BOOTUI/generation"
    bn=0
    while [ $bn -lt 10 ]; do
        bleft=""
        for bp in $(cat "$BOOTUI/feeder.pid" 2>/dev/null); do
            is_ours "$bp" "oneios_switch.sh --bootui" || continue
            kill -9 "$bp" 2>/dev/null
            [ ! -d "$P/$bp" ] || bleft="$bleft$bp "
        done
        for bp in $(cat "$BOOTUI/supervisor" 2>/dev/null); do
            is_ours "$bp" "boot_status.sh supervise" || continue
            [ $bn -lt 5 ] || kill -9 "$bp" 2>/dev/null
            [ ! -d "$P/$bp" ] || bleft="$bleft$bp "
        done
        for bp in $({ cat "$BOOTUI/worker"; cut -d' ' -f1 "$BOOTUI/ready"; } 2>/dev/null | sort -u); do
            is_ours "$bp" OneOSBootStatus || continue
            [ $bn -lt 5 ] || kill -9 "$bp" 2>/dev/null
            [ ! -d "$P/$bp" ] || bleft="$bleft$bp "
        done
        [ -n "$bleft" ] || break
        sleep 0.2; bn=$((bn + 1))
    done
    true 2>/dev/null > "$BOOTUI/ended"
    if [ -n "$bleft" ]; then say "boot screen: still running after SIGKILL ($bleft): logged only, its layer goes with the composer restart"
    else say "boot screen: ended"; fi
    return 0
}
# By the clock: a "service check" that does not answer takes its 3 s each time.
wait_found() { # <servicemanager name> <seconds>
    w0=$(now)
    while :; do
        timeout 3 service check "$1" 2>/dev/null | grep -q ': found' && return 0
        [ $(($(now) - w0)) -lt "$2" ] || return 1
        sleep 0.5
    done
}

# --- THE GUARD -------------------------------------------------------------
# Armed by every return before its first step, in a session of its own, in
# the root cgroup and out of the OOM killer's reach: it does not depend on the
# return's shell. The return takes its mark away when it is done. A mark that
# is still this return's GUARD_MAX seconds later means a step never came back
# (a command that hangs on a dead service, a script that was killed): the
# phone reboots into One UI.
if [ "$WHO" = --guard ]; then
    tok=$2
    [ -n "$tok" ] || exit 3
    t=0 last="" in=0
    while [ $t -lt $GUARD_MAX ]; do
        [ "$(cat "$CTL/return.guard" 2>/dev/null)" = "$tok" ] || exit 0
        # The step the return is in, and how long it has been in it.
        cur=$(cat "$CTL/return.watch" 2>/dev/null)
        if [ "$cur" = "$last" ]; then in=$((in + 2)); else last=$cur; in=0; fi
        lim=${cur%% *}
        case "$lim" in ''|*[!0-9]*) lim=0 ;; esac
        if [ "$lim" -gt 0 ] && [ $in -ge "$lim" ]; then
            [ "$(cat "$CTL/return.guard" 2>/dev/null)" = "$tok" ] || exit 0
            say "GUARD: '${cur#* }' did not finish within ${lim}s - rebooting into One UI"
            echo "failsafe $(date +%s) '${cur#* }' did not finish within ${lim}s" > "$S/return.outcome"
            do_reboot oneios-return-guard
        fi
        sleep 2; t=$((t + 2))
    done
    [ "$(cat "$CTL/return.guard" 2>/dev/null)" = "$tok" ] || exit 0
    say "GUARD: the return did not finish within ${GUARD_MAX}s (last step: $(cat "$CTL/return.step" 2>/dev/null)) - rebooting into One UI"
    echo "failsafe $(date +%s) the return did not finish within ${GUARD_MAX}s (last step: $(cat "$CTL/return.step" 2>/dev/null))" > "$S/return.outcome"
    do_reboot oneios-return-guard
fi
# The tests' way in (against a fake phone): the USB step of the return alone.
if [ "$WHO" = --usb-restore ]; then
    [ -n "$T" ] || { echo "oneios_return.sh --usb-restore: for the tests only"; exit 2; }
    usb_restore
    exit 0
fi

true >> "$LOG"
say "=== Return to One UI ($WHO), session state '$(cat "$CTL/state" 2>/dev/null)', boot $(cat "$P/sys/kernel/random/boot_id" 2>/dev/null) ==="
# The reboot return needs no session state and no lock.
if [ "$WHO" = reboot ]; then
    say "Reboot return asked"
    echo "reboot $(date +%s) asked" > "$S/return.outcome"
    do_reboot oneios-return
fi

# A session that already returned, or none: nothing to do, and never a reboot.
# One exception. The watcher and the key readers exist only in a session, so
# a state they cannot read is a session whose control folder is gone; if One
# UI's framework is down as well, nothing here can be checked: the reboot.
framework_down() { [ "$(getprop init.svc.zygote)" != running ] && ! pidof system_server >/dev/null 2>&1; }
case "$(cat "$CTL/state" 2>/dev/null)" in
    returned)
        # Returned, but the switch stopped One UI's framework after that return
        # (a switch from before the stop lock, oneios_switch.sh): an open session.
        if [ -e "$CTL/stopped" ] && framework_down; then
            say "state 'returned', but One UI's framework is down since the switch's stop: returning again"
        else
            say "no open session (state 'returned'): nothing to return from"; exit 0
        fi ;;
    '')
        case "$WHO" in
            watcher|keys-direct)
                [ "$(getprop init.svc.zygote)" = running ] || pidof system_server >/dev/null 2>&1 ||
                    failsafe "the session's state cannot be read ($CTL/state) and One UI's framework is not running" ;;
        esac
        say "no open session (state ''): nothing to return from"; exit 0 ;;
esac
# One return at a time: the watcher, the key readers and a manual return can
# meet. The lock names its holder; a holder that is gone (a return that was
# killed) does not keep the next one out.
if ! mkdir "$CTL/returning.lock" 2>/dev/null; then
    [ -d "$CTL" ] || { say "no session folder: nothing to return from"; exit 0; }
    holder=$(cat "$CTL/returning.lock/pid" 2>/dev/null)
    if [ -n "$holder" ] && is_ours "$holder" "oneios_return.sh"; then
        say "another return is already running (pid $holder); leaving it to it"
        exit 0
    fi
    # The holder writes its pid right after it makes the lock: an empty lock is
    # a return that is just starting, unless it is still empty a moment later.
    [ -n "$holder" ] || { sleep 2; holder=$(cat "$CTL/returning.lock/pid" 2>/dev/null); }
    if [ -n "$holder" ] && is_ours "$holder" "oneios_return.sh"; then
        say "another return is already running (pid $holder); leaving it to it"
        exit 0
    fi
    say "the return that held the lock is gone (pid '${holder}'): taking over"
fi
echo $$ > "$CTL/returning.lock/pid"
echo returning > "$CTL/state"
# The switch's stop lock (oneios_switch.sh, step 3): taken and kept. A switch in
# the middle of its stop finishes it first (15 s at most, then the lock counts as
# that switch's leftover), so the "stopped" mark below is final, and a switch
# that has not stopped anything yet never will.
n=0
until mkdir "$CTL/stop.lock" 2>/dev/null; do
    [ -e "$CTL/stop.lock/return" ] && break           # an earlier return's: the switch can stop nothing any more
    [ $n -lt 75 ] || { say "the switch's stop lock is still held after 15 s: taken over"; break; }
    sleep 0.2; n=$((n + 1))
done
echo $$ > "$CTL/stop.lock/return"
echo oneios_return 2>/dev/null > "$T/sys/power/wake_lock"
GTOK="$$.$(date +%s)"
echo "$GTOK" > "$CTL/return.guard"
if [ -n "$BB" ]; then "$BB" setsid $SH "$S/oneios_return.sh" --guard "$GTOK" </dev/null >/dev/null 2>&1 &
else $SH "$S/oneios_return.sh" --guard "$GTOK" </dev/null >/dev/null 2>&1 & fi
finished() { # the guard's mark and the lock go; the wakelocks are released
    rm -f "$CTL/return.guard" "$CTL/return.step" "$CTL/return.watch"
    rm -rf "$CTL/returning.lock"
    echo oneios_session 2>/dev/null > "$T/sys/power/wake_unlock"
    echo oneios_return 2>/dev/null > "$T/sys/power/wake_unlock"
}

step "[1/5] Stopping the session" 90
# The boot screen, while it is still up, says what happens now. The watcher
# wrote its reason there already.
bootui oneos_boot_write title 'Returning to One UI'
[ "$WHO" = watcher ] || bootui oneos_boot_write status 'Stopping iOS'
# (No bar on the way back: what it counted was the boot.)
rm -f "$BOOTUI/progress" "$BOOTUI/next"
# The key readers and the watcher (unless this return is the watcher's own
# child, or the watcher itself).
true 2>/dev/null > "$CTL/keys/session"
end_readers
# The session's USB watcher (it also ends by itself on this state); the USB
# gadget goes back to One UI's in step 4.
true 2>/dev/null > "$CTL/usb-watch.off"
end_helper "$CTL/usb-watch.pid" --usb-watch
# The Android takeover's CPU cap (oneios_switch.sh --cpu-cap; session-mode=takeover only: control/base/mode). It also
# ends by itself on this state; before One UI's clocks are written back below, it must be gone.
true 2>/dev/null > "$CTL/cpu-cap.off"
end_helper "$CTL/cpu-cap.pid" --cpu-cap
wp=$(cat "$CTL/watcher.pid" 2>/dev/null)
[ "$wp" = "$$" ] || [ "$wp" = "$PPID" ] || end_helper "$CTL/watcher.pid" --watch
XP=$(cat "$CTL/xnuhost.pid" 2>/dev/null)
XNS=$(cat "$CTL/mntns" 2>/dev/null)
INIT_NS=$(readlink "$P/1/ns/mnt" 2>/dev/null)
[ -n "$INIT_NS" ] || failsafe "init's mount namespace is not readable"
# Never kill by a namespace that is init's own (a session that did not get as
# far as a namespace has none recorded).
[ "$XNS" != "$INIT_NS" ] || XNS=""
[ -d "$CG" ] || CG=""
# The pids in the session's mount namespace: one ls for every process (a
# readlink each took over a second a round on a phone's few hundred).
in_session() {
    [ -n "$XNS" ] || return 0
    ls -l "$P"/[0-9]*/ns/mnt 2>/dev/null |
        awk -v ns="$XNS" -v pre="$P/" '$NF == ns && $(NF - 1) == "->" { p = substr($(NF - 2), length(pre) + 1); sub(/\/.*/, "", p); print p }'
}
# The pids in xnuhost's cgroup: a task that made a mount namespace of its own
# is still here. (Only pids that exist: the kernel lists no others.)
in_cgroup() {
    [ -n "$CG" ] || return 0
    for p in $(cat "$CG/cgroup.procs" 2>/dev/null); do [ -d "$P/$p" ] && echo "$p"; done
}
# The pids outside init's namespace whose mount table shows the stage (bound
# from it, or mounted under it). The session's binds are private to a
# namespace made for it, so only something that came from the session has
# them: a task in a namespace copied from xnuhost's.
stage_holders() {
    grep -l -F "$SRC" "$P"/[0-9]*/mountinfo 2>/dev/null | while read -r f; do
        awk -v s="$SM" -v r="$SRC" '$5 == s || index($5, s "/") == 1 || $4 == r || index($4, r "/") == 1 { f = 1; exit } END { exit !f }' "$f" 2>/dev/null || continue
        p=${f%/mountinfo}
        [ "$(readlink "$p/ns/mnt" 2>/dev/null)" = "$INIT_NS" ] || echo "${p##*/}"
    done
}
session_left() { { in_cgroup; in_session; stage_holders; } | sort -u | grep -v -x -e 1 -e "$$" | tr '\n' ' '; }
if [ -n "$XNS" ] && [ -n "$XP" ] && [ "$(readlink "$P/$XP/ns/mnt" 2>/dev/null)" = "$XNS" ]; then
    # What xnuhost holds of the display and the GPU, for the log: the kernel
    # takes all of it back when the process ends, however it ends.
    held=$(ls -l "$P/$XP/fd" 2>/dev/null | awk '$NF ~ /^\/dev\/(dri\/|kgsl|dma_heap\/|udmabuf|input\/)/ { n[$NF]++ } END { for (d in n) printf "%s x%d ", d, n[d] }')
    say "xnuhost $XP holds: ${held:-no display, GPU or input node}"
    say "SIGTERM to xnuhost $XP (20 s to end its tasks and flush the guest's data)"
    kill -TERM "$XP" 2>/dev/null
    t0=$(now)
    while [ $(($(now) - t0)) -lt 20 ] && [ "$(readlink "$P/$XP/ns/mnt" 2>/dev/null)" = "$XNS" ]; do sleep 0.2; done
fi
# The switch's inner shell: where it is still setting up xnuhost's namespace (it has not bound the stage
# yet, so the mount tables below do not show it), or where it waits for xnuhost (since 2026-11-23, after the app 0.5.80). Ended
# after xnuhost's stop, so it has written how xnuhost ended (session/xnuhost.exit, said here): it writes that at
# once when xnuhost is gone, and is given 1 s for it.
if [ -n "$XP" ]; then
    ip=$(cat "$CTL/inner.pid" 2>/dev/null); n=0
    while [ ! -s "$S/session/xnuhost.exit" ] && [ $n -lt 5 ] && [ -n "$ip" ] && is_ours "$ip" "oneios_switch.sh --inner"; do sleep 0.2; n=$((n + 1)); done
fi
[ ! -s "$S/session/xnuhost.exit" ] || say "xnuhost's end, as its inner shell recorded it: $(head -n 1 "$S/session/xnuhost.exit" | head -c 80 | tr -cd "a-z0-9 ?")"
end_helper "$CTL/inner.pid" --inner
# Everything that is left, clean end or not: the cgroup at once (the kernel
# ends every member, forks included), then by pid, five rounds.
left=$(session_left)
if [ -n "$left" ]; then
    say "SIGKILL to what is left of the session: $left"
    pass=1
    while [ $pass -le 5 ] && [ -n "$left" ]; do
        [ -n "$CG" ] && [ -e "$CG/cgroup.kill" ] && echo 1 > "$CG/cgroup.kill" 2>/dev/null
        for p in $left; do kill -9 "$p" 2>/dev/null; done
        sleep 1
        left=$(session_left)
        pass=$((pass + 1))
    done
fi

# The display helper (OneiOS's runtime/display; oneios_switch.sh starts it on
# One UI's side and puts it in the session's cgroup, so it is usually gone by
# here: it leaves when xnuhost's socket closes). Whatever is left of it is
# asked once, given a second, then killed. A dead client's layers are
# surfaceflinger's to drop, and the composer restart below takes the panel
# back whatever it left: nothing of the return waits for it longer.
end_display() {
    for dp in $(cat "$CTL/display.pid" 2>/dev/null); do
        is_ours "$dp" OneiOSDisplay || is_ours "$dp" oneios-display || continue
        kill -TERM "$dp" 2>/dev/null
        dn=0
        while [ $dn -lt 5 ] && [ -d "$P/$dp" ]; do sleep 0.2; dn=$((dn + 1)); done
        [ -d "$P/$dp" ] && kill -9 "$dp" 2>/dev/null
    done
    [ ! -s "$CTL/display.log" ] || say "display helper: $(tail -n 2 "$CTL/display.log" 2>/dev/null | tr '\n' '|' | cut -c1-300)"
    return 0
}
end_display
# The boot screen ends here, before the first gate and on every path below.
bootui_end

# One UI's panel brightness from the switch's baseline: xnuhost is gone by here,
# so nothing writes the node any more. Only a backlight node, only a number;
# a missing or unwritable node is logged and never stops the return.
while read -r bl lv; do
    case "$bl" in /sys/class/backlight/*/brightness) ;; *) continue ;; esac
    case "$lv" in ''|*[!0-9]*) continue ;; esac
    if echo "$lv" > "$T$bl" 2>/dev/null; then say "backlight: $bl back to $lv"; else say "backlight: $bl could not be written back (logged only)"; fi
done < "$CTL/base/backlight" 2>/dev/null

# The Android takeover (session-mode=takeover: the switch's control/base/mode; a hosted session has none, and none
# of the lines below with TAKEOVER=1 runs for it). Its CPU cap must be gone before One UI's clocks go back: a cap
# that writes after them would leave One UI capped. It was asked to end and killed above; one that is still there
# 2 s later cannot be stopped in place: the restart.
TAKEOVER=0
[ "$(cat "$BASE/mode" 2>/dev/null)" = takeover ] && TAKEOVER=1
CAP_LEVEL=$(cat "$CTL/cpu-cap.level" 2>/dev/null)
case "$CAP_LEVEL" in ''|*[!0-9]*) CAP_LEVEL=0 ;; esac
if [ "$TAKEOVER" = 1 ]; then
    cn=0 calive=0
    while [ $cn -lt 10 ]; do
        calive=0
        for p in $(cat "$CTL/cpu-cap.pid" 2>/dev/null); do is_ours "$p" "oneios_switch.sh --cpu-cap" && calive=1; done
        [ $calive = 1 ] || break
        [ $cn -lt 5 ] || end_helper "$CTL/cpu-cap.pid" --cpu-cap
        sleep 0.2; cn=$((cn + 1))
    done
    [ $calive = 0 ] || failsafe "the Android takeover's CPU cap ($(cat "$CTL/cpu-cap.pid" 2>/dev/null)) could not be ended: it could cap One UI's clocks after the return"
    say "Android takeover: its CPU cap ended at level $CAP_LEVEL ($(tail -n 1 "$CTL/cpu-cap.log" 2>/dev/null | cut -c1-200))"
fi
# One UI's clock caps and floors from the switch's baseline (oneios_switch.sh,
# clocks_save), once the switch wrote the session's (it marks that): in the
# reverse order of the writes, before One UI's zygote starts, on every path
# that stopped One UI, a killed xnuhost's too. Only those nodes, only numbers; a
# node that cannot be written is logged and never stops the return, except in an
# Android takeover whose CPU cap was in force (level 1 or more): a policy's
# scaling_max_freq left at the cap would slow One UI until a restart, so that is
# the restart (below).
rm -f "$CTL/clocks.unwritten"
if [ -e "$CTL/clocks.set" ]; then
    awk '{ l[NR] = $0 } END { for (i = NR; i > 0; i--) print l[i] }' "$CTL/base/clocks" 2>/dev/null | while read -r node old new; do
        case "$node" in /sys/devices/system/cpu/cpufreq/policy*/scaling_m??_freq|/sys/kernel/gpu/gpu_max_clock|/sys/class/kgsl/kgsl-3d0/max_gpuclk) ;;
            /sys/devices/system/cpu/cpufreq_limit/cpufreq_max_limit|/sys/devices/system/cpu/cpufreq_limit/cpufreq_min_limit) ;; *) continue ;; esac
        case "$node" in *..*) continue ;; esac
        case "${old#-}" in ''|*[!0-9]*) continue ;; esac
        was=$(cat "$T$node" 2>/dev/null)
        if echo "$old" > "$T$node" 2>/dev/null; then say "clocks: $node $was -> $old (One UI's)"
        elif [ "$TAKEOVER" = 1 ] && [ "$CAP_LEVEL" != 0 ]; then
            say "clocks: $node could not be written back to $old (it reads $was; the Android takeover's CPU cap was at level $CAP_LEVEL)"
            echo "$node" >> "$CTL/clocks.unwritten"
        else say "clocks: $node could not be written back to $old (logged only)"; fi
    done
    rm -f "$CTL/clocks.set"
fi
if [ "$TAKEOVER" = 1 ] && grep -q '/scaling_max_freq$' "$CTL/clocks.unwritten" 2>/dev/null; then
    failsafe "the Android takeover's CPU cap is still in force: $(grep '/scaling_max_freq$' "$CTL/clocks.unwritten" | tr '\n' ' ')could not be written back to One UI's value"
fi

# The switch ended before it stopped One UI's zygote (it marks the stop):
# One UI never went away, so there is nothing to check or start. Its helpers
# end, and that is the whole return.
if [ ! -e "$CTL/stopped" ] && ! framework_down; then
    true > "$CTL/stop-loop.off"
    true > "$CTL/feeder.off"
    end_helper "$CTL/stop-loop.pid" --stop-loop
    end_helper "$CTL/feeder.pid" --feed
    [ -z "$CG" ] || rmdir "$CG" 2>/dev/null
    # A switch that wrote advise and ended before its stop mark (it writes both
    # under the stop lock, the mode first): One UI runs, so a mode that cannot
    # be written back is logged, never a reason to restart it.
    shmem_restore say
    swappiness_restore
    echo "inplace $(date +%s) One UI was never stopped" > "$S/return.outcome"
    finished
    say "The switch ended before One UI's framework was stopped: nothing to restore."
    echo returned > "$CTL/state"
    exit 0
fi

step "[2/5] Gate A: nothing of the session is left" 45
# A process killed in the stop above ends only when it leaves the kernel: one
# that is inside a system call that cannot be interrupted (state D: the exit of
# a large GPU or memory mapping on a host short of memory) can take seconds.
# Phone, 2026-11-12 23:15: pid 20113 was still there 1 s after the last of the
# five SIGKILL rounds, Gate A looked once, and the failsafe restarted the phone.
# Wait up to 30 s of the step's 45 for those pids, with the cgroup killed and
# each pid killed again every second; say once what each one is (only its own
# /proc/PID files: comm, the state field, wchan), so the next log names it.
left=$(session_left)
if [ -n "$left" ]; then
    for p in $left; do
        st=$(awk '{ print $3 }' "$P/$p/stat" 2>/dev/null)
        say "Gate A: $p still there after SIGKILL: $(cat "$P/$p/comm" 2>/dev/null) state ${st:-?} wchan $(cat "$P/$p/wchan" 2>/dev/null): waiting up to 30 s for it to end"
    done
    t0=$(now)
    while [ -n "$left" ] && [ $(($(now) - t0)) -lt 30 ]; do
        [ -n "$CG" ] && [ -e "$CG/cgroup.kill" ] && echo 1 > "$CG/cgroup.kill" 2>/dev/null
        for p in $left; do kill -9 "$p" 2>/dev/null; done
        sleep 1
        left=$(session_left)
    done
    [ -n "$left" ] || say "Gate A: the killed processes ended after $(($(now) - t0)) s"
fi
[ -z "$left" ] || failsafe "processes still in the session's namespace or cgroup: $left"
[ -z "$CG" ] || rmdir "$CG" 2>/dev/null || say "the session's cgroup $CG is empty but could not be removed (logged only)"
[ -f "$BASE/boot_id" ] || failsafe "no baseline of the switch ($BASE)"
[ "$(cat "$BASE/boot_id")" = "$(cat "$P/sys/kernel/random/boot_id" 2>/dev/null)" ] || failsafe "the baseline is another boot's"
# The stage, in every process's mount table and not only init's (OneOS run 45:
# another namespace kept its own copy of a stage mount). By mount point or by
# source. Nothing is unmounted here: a namespace that still has the stage as
# its /data would see One UI's /data in its place.
m=$(grep -H -F "$SRC" "$P"/[0-9]*/mountinfo 2>/dev/null |
    awk -v s="$SM" -v r="$SRC" '$5 == s || index($5, s "/") == 1 || $4 == r || index($4, r "/") == 1 { print $1 " " $5 }' | head -n 3 | tr '\n' ' ')
[ -z "$m" ] || failsafe "the stage is still mounted (mount table, mount point): $m"
added=$(awk '{ print $5 }' "$P/1/mountinfo" | sort | comm -13 "$BASE/mounts" - 2>/dev/null | grep -E '^/(data|system|vendor|product|system_ext|odm|apex)(/|$)' | head -n 3 | tr '\n' ' ')
[ -z "$added" ] || failsafe "mounts added on One UI's partitions during the session: $added"
# The daemons One UI cannot get back without a boot. surfaceflinger is not one
# of them: it is restarted below with the composer, so its pid is only logged.
SF_BASE=""
while read -r name pids; do
    now=$(pidof "$name" 2>/dev/null | tr ' ' ',')
    if [ "$name" = surfaceflinger ]; then
        SF_BASE=$pids
        [ "$now" = "$pids" ] || say "surfaceflinger is ${now:-not running} now, was $pids at the switch (it is restarted below)"
        continue
    fi
    [ "$now" = "$pids" ] || failsafe "One UI's $name is ${now:-not running} now, was $pids at the switch"
done < "$BASE/pids"
for svc in vold keystore2 servicemanager hwservicemanager logd lmkd installd; do
    [ "$(base_prop init.svc.$svc)" = running ] || continue
    [ "$(getprop init.svc.$svc)" = running ] || failsafe "$svc is $(getprop init.svc.$svc), was running at the switch"
done
# The shmem THP mode back to what the switch found (shmem_restore above).
shmem_restore failsafe
# vm.swappiness back to what the switch found (the takeover's takeover-swappiness=; swappiness_restore above).
swappiness_restore
[ "$(getenforce 2>/dev/null)" = "$(cat "$BASE/selinux")" ] || failsafe "SELinux is $(getenforce 2>/dev/null), was $(cat "$BASE/selinux")"
# The session scripts set no persist property. What differs from the switch
# is One UI's own daemons' doing, or xnuhost's against its contract: by name
# only (values can be personal), and nothing is written back.
changed=$(getprop | awk -F'\\]: \\[' 'NR == FNR { b[$1] = $2; next } $1 ~ /^\[persist\./ && (!($1 in b) || b[$1] != $2) { sub(/^\[/, "", $1); print $1 }' "$BASE/props" - 2>/dev/null | head -n 20 | tr '\n' ' ')
say "Gate A: no session process, the stage mounted nowhere, vold, keystore2 and servicemanager as at the switch, SELinux $(getenforce 2>/dev/null), shmem_enabled $(cat "$SHMEM_EN" 2>/dev/null || echo -); persist properties that differ from the switch: ${changed:-none}"

step "[3/5] Gate B: One UI's display and services" 75
# The stop loop must be gone before anything starts (its last ctl.stop can
# land after a start; it also stops the boot animation).
true > "$CTL/stop-loop.off"
end_waiter
n=0
while [ $n -lt 15 ]; do
    alive=0
    for p in $(cat "$CTL/stop-loop.pid" 2>/dev/null); do
        is_ours "$p" "oneios_switch.sh --stop-loop" && alive=1
    done
    [ $alive = 1 ] || break
    [ $n -lt 10 ] || end_helper "$CTL/stop-loop.pid" --stop-loop
    sleep 0.2; n=$((n + 1))
done
[ $alive = 0 ] || failsafe "the session's stop loop is still running"
# What it did in the session (oneios_switch.sh --stop-loop writes a line for each stop and for how it waited).
if [ -s "$CTL/stop-loop.log" ]; then
    say "stop loop: $(grep -c ' was running: ctl.stop ' "$CTL/stop-loop.log" 2>/dev/null) stops of a service that ran again; $(grep -m1 ' keeps ' "$CTL/stop-loop.log" | sed 's/^.* stop loop: //' | cut -c1-200)"
fi
[ "$(getprop init.svc.zygote)" != running ] && ! pidof system_server >/dev/null 2>&1 ||
    failsafe "One UI's zygote or system_server started before the return was ready"
# One UI's boot-loop check counts every system_server start in a 10 minute
# window (return_to_oneui.sh, 0.4.47: a switch and return read as a boot loop
# and rolled back a Play system update). The counters go back to the
# switch's, in memory only; nothing persist.* is written.
if [ -n "$RP" ]; then
    for k in crashrecovery.rescue_boot_start crashrecovery.boot_mitigation_count crashrecovery.boot_mitigation_start \
             crashrecovery.attempting_reboot crashrecovery.attempting_factory_reset; do
        put_back "$k"
    done
    "$RP" -n sys.rescue_boot_count 0 2>/dev/null
    "$RP" -n crashrecovery.rescue_boot_count 0 2>/dev/null
else
    say "!!! no resetprop: One UI's boot counters stay as they are"
fi

# Display (return_to_oneui.sh's step, for a session in which One UI's own
# surfaceflinger kept running). xnuhost drew the guest with the Adreno and,
# with --display drm, on the panel itself; the kernel closed its KGSL contexts
# and DRM handles when it ended, a SIGKILL included. What may be left is on
# One UI's side: a composer that last saw another DRM master or a mode it did
# not set, a surfaceflinger whose GPU context a guest fault reset or that sits
# in a call that will not return, layers of a display helper. So nothing of
# the old display state is trusted: the composer is restarted, surfaceflinger
# with it, and the boot animation covers One UI's start. Each must come back,
# or the phone reboots.
COMPOSER_SVC=""
for c in vendor.qti.hardware.display.composer vendor.hwcomposer-3; do
    [ -n "$(getprop init.svc.$c)" ] && { COMPOSER_SVC=$c; break; }
done
[ -n "$COMPOSER_SVC" ] || COMPOSER_SVC=$(getprop | sed -n 's/^\[init\.svc\.\([^]]*\)\]: \[running\]$/\1/p' | grep -m1 -E 'hwcomposer|display\.composer|graphics\.composer')
[ -n "$COMPOSER_SVC" ] || failsafe "no display composer service found"
C_OLD=$(getprop "init.svc_debug_pid.$COMPOSER_SVC")
SF_OLD=$(pidof surfaceflinger 2>/dev/null)
setprop ctl.restart "$COMPOSER_SVC"
# The new composer, not the old one on its way out: init's pid for the
# service has changed (a second's wait where init publishes none).
[ -n "$C_OLD" ] || sleep 1
n=0
while [ $n -lt 20 ]; do
    if [ "$(getprop "init.svc.$COMPOSER_SVC")" = running ]; then
        [ -z "$C_OLD" ] || [ "$(getprop "init.svc_debug_pid.$COMPOSER_SVC")" != "$C_OLD" ] && break
    fi
    sleep 0.5; n=$((n + 1))
done
[ $n -lt 20 ] || failsafe "the display composer $COMPOSER_SVC did not restart (pid still '$C_OLD', $(getprop "init.svc.$COMPOSER_SVC"))"
# The vendor manifest says which composer interface this phone serves.
if grep -rqs 'android.hardware.graphics.composer3' "$T/vendor/etc/vintf/"; then
    wait_found android.hardware.graphics.composer3.IComposer/default 10 || failsafe "the display composer did not come back"
else
    n=0
    while [ $n -lt 20 ] && ! timeout 3 lshal list -i 2>/dev/null | grep -q 'android\.hardware\.graphics\.composer@[0-9.]*::IComposer/default'; do
        sleep 0.5; n=$((n + 1))
    done
    [ $n -lt 20 ] || failsafe "the display composer (HIDL) did not come back"
fi
# surfaceflinger was the old composer's client: it ends with it and init
# starts it again. One that is still the old process after 5 s is restarted by
# name; one that is not running is started.
n=0; sf=""
while [ $n -lt 10 ]; do
    sf=$(pidof surfaceflinger 2>/dev/null)
    [ -n "$sf" ] && [ "$sf" != "$SF_OLD" ] && break
    sleep 0.5; n=$((n + 1))
done
if [ -z "$sf" ]; then setprop ctl.start surfaceflinger
elif [ "$sf" = "$SF_OLD" ]; then setprop ctl.restart surfaceflinger; fi
n=0
while [ $n -lt 30 ]; do
    sf=$(pidof surfaceflinger 2>/dev/null)
    [ -n "$sf" ] && [ "$sf" != "$SF_OLD" ] && break
    sleep 0.5; n=$((n + 1))
done
[ -n "$sf" ] && [ "$sf" != "$SF_OLD" ] || failsafe "One UI's surfaceflinger did not restart (pid '${sf}', was '${SF_OLD}')"
wait_found SurfaceFlinger 10 || failsafe "One UI's surfaceflinger did not register"
setprop service.bootanim.exit 0
setprop ctl.start bootanim
say "display: composer $COMPOSER_SVC restarted (was $C_OLD), surfaceflinger $sf (was ${SF_OLD:-not running}; ${SF_BASE:-?} at the switch), boot animation started"

# Audio and the rest of zygote's onrestart list, which a start after a stop
# skips. They served One UI's old framework all session (and the guest's
# bridges, where one of them plays through audioserver): Android restarts them
# with every framework restart. AudioService waits for the policy service
# with no timeout.
setprop ctl.stop audioserver
setprop ctl.start audioserver
wait_found media.audio_policy 20 || failsafe "One UI's audioserver did not register"
setprop ctl.restart cameraserver
for svc in media mediaextractor mediametrics; do setprop ctl.start $svc; done
setprop ctl.restart wificond
# One UI's init.zygote64.rc also restarts these two (return_to_oneui.sh, run 44).
for svc in perfmond media.tuner; do
    [ "$(base_prop init.svc.$svc)" = running ] && setprop ctl.restart $svc
done
say "audioserver, cameraserver, media and wificond restarted"

# Everything One UI's framework waits for, with nothing of the session left.
left=$(session_left)
[ -z "$left" ] || failsafe "processes of the session appeared again: $left"
for name in vold SurfaceFlinger media.audio_policy media.audio_flinger installd; do
    wait_found "$name" 5 || failsafe "$name is not registered"
done
say "Gate B: display, audio and One UI's services up, SELinux $(getenforce 2>/dev/null)"

step "[4/5] Starting One UI in place" 45
# The USB gadget and adbd as One UI left them, before its UsbDeviceManager starts.
usb_restore
# zygote's onrestart by hand: abort the FUSE connections the old framework left.
timeout 10 vdc volume abort_fuse >/dev/null 2>&1
# One UI's zygote_next ran through the session with the old framework's
# children: a fresh one, as a boot gives (return_to_oneui.sh).
if [ -n "$(pidof zygote_next 2>/dev/null)" ] && [ "$(base_prop init.svc.zygote_next)" = running ]; then
    setprop ctl.restart zygote_next
fi
# The Android takeover's stops: zygote's restart list above started each one
# again; each must run again before One UI's framework starts, else the restart
# (OneiOS docs/plan-ios-first-session.md 4, rule 5). One more ctl.start for one
# that does not run (yet), 10 s at most for each. netd below, at its own step.
running_again() { # <service>
    [ "$(getprop "init.svc.$1")" = running ] || setprop ctl.start "$1"
    n=0
    while [ $n -lt 50 ] && [ "$(getprop "init.svc.$1")" != running ]; do sleep 0.2; n=$((n + 1)); done
    st=$(getprop "init.svc.$1")
    [ "$st" = running ] || failsafe "the Android takeover stopped $1 for the session, and it does not run again (init.svc.$1 '${st}')"
    back="$back $1"
}
back=""
for svc in $(takeover_stopped); do [ "$svc" = netd ] || running_again "$svc"; done
# netd's restart is on zygote's list too (the new system_server needs a fresh
# DnsResolver); where its own onrestart starts zygote, that is the start.
# A netd that the Android takeover stopped is started (init runs onrestart only
# for a service that was running), so zygote is not waited for: it is started.
zw=0
if takeover_stopped | grep -qx netd; then setprop ctl.start netd; running_again netd; zw=20
else setprop ctl.restart netd; fi
[ -z "$back" ] || say "Android takeover: its stops run again:$back (control/base/stopped)"
n=$zw
while [ $n -lt 20 ] && [ "$(getprop init.svc.zygote)" != running ]; do sleep 0.5; n=$((n + 1)); done
[ "$(getprop init.svc.zygote)" = running ] || setprop ctl.start zygote
if [ "$(base_prop init.svc.zygote_secondary)" = running ] && [ "$(getprop init.svc.zygote_secondary)" != running ]; then
    setprop ctl.start zygote_secondary
    say "One UI's zygote_secondary started"
fi
n=0
while [ $n -lt 20 ] && [ "$(getprop init.svc.zygote)" != running ]; do sleep 0.5; n=$((n + 1)); done
[ "$(getprop init.svc.zygote)" = running ] || failsafe "One UI's zygote did not start ($(getprop init.svc.zygote))"
say "One UI's zygote started"

step "[5/5] Gate C: One UI's system_server" 290
# By the clock, not by counting rounds: one round's "am" alone takes a second.
t0=$(now); t=0; ss=""
while [ $t -lt 60 ]; do
    # Two pids: a child system_server forked and has not exec'd yet; ask again.
    ss=$(pidof system_server); case "$ss" in *" "*) ss="" ;; esac
    [ -n "$ss" ] && break
    sleep 1; t=$(($(now) - t0))
done
[ -n "$ss" ] || failsafe "One UI's system_server did not start in 60 s"
say "One UI's system_server $ss"
# system_server feeds Samsung's software watchdog again from here.
true > "$CTL/feeder.off"
t0=$(now); up=0
while :; do
    sleep 2; t=$(($(now) - t0))
    [ "$(cat "$P/$ss/comm" 2>/dev/null)" = system_server ] ||
        failsafe "One UI's system_server $ss died after ${t}s (now $(pidof system_server 2>/dev/null || echo none))"
    [ "$(getprop init.svc.zygote)" = running ] || failsafe "zygote is $(getprop init.svc.zygote)"
    if [ $up = 0 ]; then
        st=$(timeout 5 am get-started-user-state 0 2>&1)
        case "$st" in
            *RUNNING_UNLOCKED*) up=$t; say "user 0 unlocked after ${t}s" ;;
            *nknown*|*rror*) pidof com.sec.android.app.launcher >/dev/null 2>&1 && { up=$t; say "One UI Home running after ${t}s"; } ;;
        esac
    fi
    [ $up -gt 0 ] && [ $t -ge $((up + 20)) ] && break
    [ $up = 0 ] && [ $t -ge 180 ] && failsafe "user 0 not unlocked within 180 s"
done
end_helper "$CTL/feeder.pid" --feed
echo "inplace $(date +%s) $(cat "$P/sys/kernel/random/boot_id" 2>/dev/null)" > "$S/return.outcome"
finished
say "One UI restored in place ($(getenforce 2>/dev/null))."
# Last: whoever waits for this state finds everything above done.
echo returned > "$CTL/state"
