#!/system/bin/sh
# The OneiOS session: One UI's framework stops and xnuhost (XNU as a process,
# from the OneiOS runtime package) starts with the staged iOS image set.
# docs/oneios.md; the contract with xnuhost is OneiOS's oneos/interface.md
# (session ABI 1). Modelled on oneos_switch.sh: every refusal comes before the
# first change, One UI's zygote is stopped and kept stopped, and the way back
# (oneios_return.sh: in place, else a reboot) is armed before the stop.
#
#   oneios_switch.sh            the session (preflight, stop, start xnuhost)
#   oneios_switch.sh --check    the preflight only; changes nothing
#   oneios_switch.sh --inner    (internal) inside the session's mount namespace
#   oneios_switch.sh --watch    (internal) the watcher that returns to One UI
#   oneios_switch.sh --keys D TOK        (internal) Volume Up + Volume Down, from device D's events
#   oneios_switch.sh --keys-poll TOK D.. (internal) the same chord from the keys' state (works under a grab)
#   oneios_switch.sh --feed     (internal) Samsung's software watchdog feeder
#   oneios_switch.sh --stop-loop X (internal) keeps One UI's zygote (and the takeover's stops) stopped; X: xnuhost, for --prop-wait
#   oneios_switch.sh --bootui   (internal) the boot screen's stage line, from xnuhost's log
#   oneios_switch.sh --usb-watch (internal) keeps adb on the USB gadget through the session
#   oneios_switch.sh --cpu-cap  (internal) the Android takeover's CPU cap (session-mode=takeover only)
#   oneios_switch.sh --takeover-stops (tests only) the Android takeover's stops against a fake phone
#
# The session mode (docs/oneios.md, "Android takeover"; OneiOS's oneos/interface.md 4a): session-mode=hosted, the
# default, is the session below exactly as it was. session-mode=takeover (the app's toggle, or the image's
# xnuhost.conf) is the opt-in Android takeover: xnuhost takes the phone's touchscreen for iOS alone (never a key
# device), the switch stops the services of zygote's restart list that no bridge uses (takeover-stops=, recorded in
# control/base/stopped; the stop loop keeps them stopped, the return starts them again), and a CPU cap of the
# switch's own lowers each CPU policy's scaling_max_freq when the cell gets hot (50 C up; the case is logged, never a
# level); the return writes One UI's values back, as for every session. The way back is the same: the chord and the
# return in place first, a restart into One UI only when the in-place return cannot put One UI back.
#
# What a session never touches: One UI's /data beyond $STAGE (xnuhost's mount
# namespace has the stage bound over /data), vold, keystore2, gatekeeper,
# weaver, the lock-screen files, SELinux's mode, persist.* properties.
# What it changes, all undone by oneios_return.sh or a reboot: One UI's zygote
# (and zygote_secondary) stopped, the kernel wakelock oneios_session, Samsung's
# software watchdog closed and fed, the cgroup oneios_session (xnuhost's own),
# OneOS's boot screen on a surfaceflinger layer until the guest's first frame,
# and, with USB debugging on, the USB watcher's repairs (sys.usb.config, adbd
# and the gadget's UDC, each only back to One UI's own value).
#
# The ways back to One UI, none of which needs anything from the guest
# (docs/oneios.md, "Getting back to One UI"):
#   1  Volume Up + Volume Down held 3 s: one reader per key device (--keys) and
#      a poll of the keys' state (--keys-poll) that a grab cannot starve.
#   2  the watcher (--watch): on a request, when xnuhost ends, when the guest
#      never reports ready. If it does not act on the keys, the key readers
#      start the return themselves.
#   3  oneios_return.sh: in place, a reboot on any doubt, and a reboot by its
#      own guard if it does not finish.
#   4  Power + Volume Down held: the phone's own forced restart, below all of this.

# Tests (OneiosScriptTest) set ONEIOS_TEST_ROOT to a folder that stands for /:
# then only the stage checks run, never as root, and no session is started.
# The watcher and the key readers (--watch, --keys, --keys-poll) can be run
# there by themselves: against that folder's proc, sys and stage, with its
# bin/ first on PATH (stand-ins for getevent, getprop, setprop, ...), and with
# its bin/kill and bin/sleep in place of the shell's, so a test never signals
# a real process.
T="${ONEIOS_TEST_ROOT:-}"
if [ -n "$T" ]; then
    [ "$(id -u)" != 0 ] || { echo "PREFLIGHT REFUSED: ONEIOS_TEST_ROOT is for tests, never as root"; exit 3; }
    PATH="$T/bin:$PATH"; export PATH
    kill() { "$T/bin/kill" "$@"; }
    sleep() { "$T/bin/sleep" "$@"; }
fi
SH=/system/bin/sh
[ -z "$T" ] || SH="${ONEIOS_TEST_SH:-/bin/sh}"
P="$T/proc"
STAGE="$T/data/local/tmp/oneios"
ANDROID_STAGE="$T/data/local/tmp/oneos"
# session/ is what xnuhost and the switch share (its log, its pid, ready,
# return.request, display.sock). control/ is the way back's own: the state,
# the baseline, the pids, the keys. xnuhost's namespace has it read-only, so
# nothing the guest does to its /data can change what the watcher, the key
# readers and the return read.
SESSION="$STAGE/session"
CTL="$STAGE/control"
SELF="$STAGE/oneios_switch.sh"
ABI=1
APP="${ONEIOS_APP:-0}"
[ "$APP" = 1 ] || APP=0
MODE="${1:-session}"
# The app's status (root's status verb): --check by the files' ids, hashing nothing (check_list). Never the switch.
QUICK=0
[ "$MODE" != --check ] || [ "${ONEIOS_CHECK_QUICK:-0}" != 1 ] || QUICK=1
OWNER=0
[ -z "$T" ] || OWNER=$(id -u)

refuse() {
    echo "PREFLIGHT REFUSED: $*"
    echo "Nothing on the phone was changed; One UI keeps running."
    exit 2
}
# Owned by root and writable by root only (stat %A: group w is the 6th
# character, other w the 9th), and not a link.
root_only() {
    [ ! -L "$1" ] || return 1
    case "$(stat -c '%u %A' "$1" 2>/dev/null)" in
        "$OWNER "?????w*|"$OWNER "????????w*) return 1 ;;
        "$OWNER "*) return 0 ;;
    esac
    return 1
}
conf() { # <file> <key>: the value of key=value, first match
    sed -n "s/^$2=//p" "$1" 2>/dev/null | head -n 1
}
boot_id() { cat "$T/proc/sys/kernel/random/boot_id" 2>/dev/null; }
# "dev:inode:size:mtime" of a file: what root recorded when it staged it.
file_id() { stat -c '%d:%i:%s:%Y' "$1" 2>/dev/null; }

# --- THE WAY BACK'S OWN HELPERS ---------------------------------------------
# The watcher and the key readers must run whatever the guest does. They are
# One UI-side processes in init's mount namespace; this puts the calling shell
# in the root cgroup (which cannot be frozen, has no limits and is not killed
# with the app's group; xnuhost gets a cgroup of its own, see --inner), on
# every core, ahead of ordinary processes and out of the OOM killer's reach.
out_of_the_way() {
    # (2>/dev/null first: a path that is not there is not worth a line.)
    echo $$ 2>/dev/null > "$T/sys/fs/cgroup/cgroup.procs"
    echo -1000 2>/dev/null > "$P/$$/oom_score_adj"
    for g in /dev/cpuset /dev/cpuctl; do
        [ -w "$T$g/cgroup.procs" ] && echo $$ 2>/dev/null > "$T$g/cgroup.procs"
    done
    renice -n -10 -p $$ >/dev/null 2>&1
    return 0
}
# The keys ask the watcher, which acts within a second. A session that is
# still not returning 5 s later has no working watcher (killed, or stuck): the
# return then starts from the key reader itself. oneios_return.sh takes one
# caller at a time, so the two can meet.
ask_return() { # <why>
    [ -e "$SESSION/return.request" ] || echo "$1 at $(date '+%F %T')" > "$SESSION/return.request"
    sleep 5
    case "$(cat "$CTL/state" 2>/dev/null)" in
        starting|running)
            echo "$(date '+%F %T') keys: the watcher did not start the return within 5 s of '$1'; starting it from the key reader" >> "$STAGE/return.log"
            # In a session of its own: the return ends the key readers by
            # their process groups, and this is one of them.
            if [ -n "$BB" ]; then exec "$BB" setsid $SH "$STAGE/oneios_return.sh" keys-direct >> "$STAGE/return.log" 2>&1
            else exec $SH "$STAGE/oneios_return.sh" keys-direct >> "$STAGE/return.log" 2>&1; fi ;;
    esac
    return 0
}
# A key reader is started in a session of its own (setsid), so it leads a
# process group that holds only itself, its getevent and its timers: the
# return, and a reader that finds it is no longer this session's, end the
# whole group at once. The reader lists itself for the return.
reader_start() {
    echo $$ >> "$CTL/keys/pids"
    OWN_GROUP=0
    [ "$(ps -o pgid= -p $$ 2>/dev/null | tr -d ' ')" = "$$" ] && OWN_GROUP=1
    out_of_the_way
}
reader_end() {
    [ "$OWN_GROUP" = 1 ] && kill -9 -- "-$$" 2>/dev/null
    exit 0
}
# The display helper (OneiOS's runtime/display, bin/oneios-display): a One
# UI-side process that shows the guest's frames (session/display.sock) on a
# surfaceflinger layer. Ended by its pid, never waited for: surfaceflinger
# drops a dead client's layers, and the return restarts the composer anyway.
end_display() {
    for dp in $(cat "$CTL/display.pid" 2>/dev/null); do
        # (cat, then tr: toybox's tr never ends on a failed read, and a read of
        # the cmdline of a process that just ended fails. oneios_return.sh.)
        case "$(cat "$P/$dp/cmdline" 2>/dev/null | tr '\0' ' ')" in
            *OneiOSDisplay*|*oneios-display*) kill -9 "$dp" 2>/dev/null ;;
        esac
    done
    return 0
}
# --- THE BOOT SCREEN -------------------------------------------------------
# OneOS's own boot screen, the one an Android guest's switch shows
# (boot_status.sh, its renderer OneOSBootStatus.dex, the OneOS icon;
# docs/boot-status.md), from $STAGE/bin, which xnuhost's namespace has
# read-only. From the stop of One UI's framework until the guest's first frame
# it shows "Starting iOS 27", the boot stage read from xnuhost's log, and the
# way back. Optional, like OneOS's: every failure here leaves the switch and
# the way back exactly as they are without it. It reads no key and takes no
# input device; its status files are in control/, where the guest cannot write.
BOOTUI="$CTL/bootui"
BOOTBIN="$STAGE/bin"
bootui() { # <a function of boot_status.sh> [arguments]
    [ -d "$BOOTUI" ] && [ -f "$BOOTBIN/boot_status.sh" ] || return 0
    ( ONEOS_BOOT_DIR=$BOOTUI; ONEOS_BOOT_HOME=$BOOTBIN; . "$BOOTBIN/boot_status.sh" && "$@" ) >/dev/null 2>&1
    return 0
}
# What is drawn comes from a log the guest writes: printable ASCII, one line, cut.
plain() { printf '%s' "$1" | LC_ALL=C tr -c ' -~' ' ' | cut -c1-"${2:-200}"; }
screen() { # <title|status> <text>
    bootui oneos_boot_write "$1" "$(plain "$2")"
}
# Starts the screen (the session only). The renderer gets 3 s for its first
# frame; with or without one the switch goes on.
bootui_begin() {
    [ "${ONEIOS_BOOTUI:-1}" != 0 ] || { echo "Boot screen: off (ONEIOS_BOOTUI=0)"; return 0; }
    for f in boot_status.sh OneOSBootStatus.dex oneos_boot_icon.png; do
        [ -f "$BOOTBIN/$f" ] && root_only "$BOOTBIN/$f" ||
            { echo "Boot screen: $BOOTBIN/$f is not staged or not root's; the screen stays dark until iOS draws"; return 0; }
    done
    command -v app_process >/dev/null 2>&1 || { echo "Boot screen: no app_process; the screen stays dark until iOS draws"; return 0; }
    (
        ONEOS_BOOT_DIR=$BOOTUI; ONEOS_BOOT_HOME=$BOOTBIN; ONEOS_BOOT_MAX=1800
        export ONEOS_BOOT_DIR ONEOS_BOOT_HOME ONEOS_BOOT_MAX
        . "$BOOTBIN/boot_status.sh" || exit 1
        oneos_boot_begin ios
        oneos_boot_write status "Stopping One UI's framework"
        oneos_boot_write progress "1 $BOOT_STEPS 0.000"
        oneos_boot_write next "$(stage_name 2)"
        oneos_boot_wait_ready 3
    ) </dev/null >>"$CTL/bootui.log" 2>&1
    rc=$?
    [ -s "$BOOTUI/generation" ] || { echo "Boot screen: could not be started (log $CTL/bootui.log); the screen stays dark until iOS draws"; return 0; }
    "$BB" setsid $SH "$SELF" --bootui </dev/null >>"$CTL/bootui.log" 2>&1 &
    if [ $rc = 0 ]; then echo "Boot screen: up (renderer $(cut -d' ' -f1 "$BOOTUI/ready" 2>/dev/null), log $BOOTUI/renderer.log)"
    else echo "Boot screen: the renderer posted no frame within 3 s (log $BOOTUI/renderer.log); the switch goes on"; fi
    return 0
}
# xnuhost's log from byte $1 on (1 MiB at most): how far the boot got ($2 is the
# step so far) and what ended it. The steps are the boot screen's twelve
# (stage_name below; docs/oneios.md, "Boot screen"), each begun by the first
# line here that names it; a step is only ever raised, except by a new boot.
# Prints "S <step>", "F" (the kernel makes a new Data store: a first start),
# "B" (a new boot began: xnuhost started the guest again in place),
# "P <panic text>", "W <why xnuhost stops>", "X <exit code>", "E <xnuhost's
# last error line>".
log_scan() { # <first byte, from 1> <step so far>
    [ -f "$SESSION/xnuhost.log" ] && [ ! -L "$SESSION/xnuhost.log" ] || return 0
    $TMO tail -c "+$1" "$SESSION/xnuhost.log" 2>/dev/null | head -c 1048576 | LC_ALL=C tr -d '\000' | LC_ALL=C awk -v st="$2" '
        function s(n) { if (n > st) st = n }
        { line = $0; sub(/^\[ *[0-9]+\.[0-9][0-9][0-9]\] /, "", line) }
        index(line, "oneios inner: ") == 1 { s(2); next }
        line ~ /^guest / {
            t = line; sub(/^guest +/, "", t)
            if (index(t, "Darwin Kernel Version") == 1 || index(t, "BSD root: ") == 1) s(4)
            else if (index(t, "OneiOS Data: first start") == 1) { s(5); first = 1 }
            else if (index(t, "OneiOS Data: unpacking the seed") == 1) { s(6); first = 1 }
            else if (index(t, "load_init_program: attempting to load") == 1) s(7)
            else if (index(t, "com.apple.xpc.launchd|") == 1) s(8)
            else if (panic == "" && t ~ /^panic\(cpu [0-9]+ caller 0x[0-9a-f]+\): /) { panic = t; sub(/^panic\([^)]*\): /, "", panic) }
            if (index(t, "SpringBoard[") || index(t, "crashed: SpringBoard.")) s(9)
            if (index(t, "backboardd[")) s(10)
            next
        }
        line ~ /^xnuhost I / {
            t = substr(line, 11)
            if (index(t, "xnuhost: session ABI ") == 1) { st = 2; boot = 1; first = 0; panic = ""; why = ""; code = ""; err = "" }
            else if (t ~ /^memory: the guest.s RAM is held for the session/) s(3)
            else if (t ~ /^memory: the guest.s RAM is held: / || index(t, "cpu0: entering the kernel at ") == 1) s(4)
            else if (t ~ /^display: the guest.s first frame of its own/) s(11)
            else if (index(t, "guest ready: first frame") == 1) s(12)
            else if (index(t, "stopping: ") == 1) { why = substr(t, 11); sub(/ \(reason [0-9]+, code [0-9]+\)$/, "", why) }
            else if (t ~ /^exit [0-9]+$/) code = substr(t, 6)
            next
        }
        line ~ /^xnuhost E / { err = substr(line, 11) }
        END {
            print "S " st
            if (first) print "F"
            if (boot) print "B"
            if (panic != "") print "P " panic
            if (why != "") print "W " why
            if (code != "") print "X " code
            if (err != "") print "E " err
        }'
}
# The boot screen's steps, in order: what the status line says while each
# runs (the "next" file names the one after it). Steps 5 and 6 run only on a
# first start (no Data store yet); a later boot goes from 4 to 7, and the
# count goes on past them.
BOOT_STEPS=12
stage_name() { # <step>
    case "$1" in
        1) echo "Stopping One UI's framework" ;;
        2) echo "Starting xnuhost" ;;
        3) echo "Locking iOS's RAM" ;;
        4) echo "Starting the kernel" ;;
        5) echo "First start: making iOS's Data store (once)" ;;
        6) echo "First start: unpacking iOS's data (once)" ;;
        7) echo "Starting launchd" ;;
        8) echo "Starting iOS's system services" ;;
        9) echo "Starting SpringBoard" ;;
        10) echo "Starting the display (backboardd)" ;;
        11) echo "Waiting for iOS's first picture" ;;
        12) echo "iOS is up: handing the screen to it" ;;
    esac
}
next_name() { # <step> <first start: 1 or 0>
    nn=$(($1 + 1))
    [ "$2" = 1 ] || case $nn in 5|6) nn=7 ;; esac
    [ $nn -gt $BOOT_STEPS ] || stage_name $nn
}
# How far the bar is, 0.000 to 1.000: the steps before this one, and the time
# in this one up to 90% of its share, of the boot's whole time. Each step's
# share is its typical length in seconds on the S24 Ultra (the phone's boots
# of 2026-11-22: steps 5 and 6 from the first start, the others from later
# boots); a later boot leaves out 5 and 6. Never less than the last value.
progress_of() { # <step> <seconds in it> <first start: 1 or 0> <last value>
    awk -v n="$1" -v e="$2" -v f="$3" -v last="$4" 'BEGIN {
        split("18 1 3 2 22 10 20 12 7 4 35 0", w, " ")
        for (i = 1; i <= 12; i++) { if (!f && (i == 5 || i == 6)) continue; all += w[i]; if (i < n) done += w[i] }
        c = (e > 0) ? e : 0; if (c > w[n] * 0.9) c = w[n] * 0.9
        p = (n >= 12) ? 1 : (done + c) / all
        if (p < last + 0) p = last + 0; if (p > 1) p = 1
        printf "%.3f\n", p }'
}
# One line on why xnuhost ended, from the last 64 KiB of its log.
why_ended() {
    sz=$(stat -c %s "$SESSION/xnuhost.log" 2>/dev/null)
    # (awk, not the shell: Android's sh counts in 32 bits.)
    from=$(awk -v s="${sz:-0}" 'BEGIN { print (s + 0 > 65536) ? s - 65535 : 1 }')
    log_scan "$from" 0 | awk '
        /^P / { p = substr($0, 3) } /^W / { w = substr($0, 3) } /^X / { x = substr($0, 3) } /^E / { e = substr($0, 3) }
        END {
            if (p != "") print "iOS stopped: kernel panic: " p
            else if (w != "") print "iOS stopped: " w (x != "" ? " (xnuhost exit " x ")" : "")
            else if (x != "") print "xnuhost ended with exit " x (e != "" ? ": " e : "")
            else if (e != "") print "xnuhost ended: " e
            else print "xnuhost ended"
        }'
}
# The display helper runs and has the guest's picture: its first frame is
# posted, or xnuhost reported ready and the helper's layer is up. Its layer is
# above the boot screen's, so the picture covers the boot screen first and the
# boot screen is taken away under it.
display_up() {
    for dp in $(cat "$CTL/display.pid" 2>/dev/null); do
        case "$(cat "$P/$dp/cmdline" 2>/dev/null | tr '\0' ' ')" in
            *OneiOSDisplay*|*oneios-display*) ;;
            *) continue ;;
        esac
        grep -q 'oneios-display: first frame posted' "$CTL/display.log" 2>/dev/null && return 0
        [ -e "$SESSION/ready" ] && grep -q 'oneios-display: layer up' "$CTL/display.log" 2>/dev/null && return 0
    done
    return 1
}
TMO=""
command -v timeout >/dev/null 2>&1 && TMO="timeout 5"

# sync, waited for 5 s at most: a sync that stands still (a stuck disk or
# FUSE) must not keep the reboot's last resorts from running.
sync_bounded() {
    sync &
    sb=$!; sn=0
    while [ $sn -lt 25 ] && [ -d "$P/$sb" ]; do sleep 0.2; sn=$((sn + 1)); done
}
# The reboot return without oneios_return.sh, for the watcher when that script
# cannot be run or ends with an error: the same three steps as its failsafe.
hard_reboot() { # <reason word> <why>
    echo "$(date '+%F %T') watcher: $2 - rebooting into One UI"
    bootui oneos_boot_stop
    echo "failsafe $(date +%s) $2" > "$STAGE/return.outcome"
    sync_bounded
    setprop sys.powerctl "reboot,$1"
    sleep 20
    # init did not reboot: Android's own reboot, then busybox's (a root manager's busybox may have no reboot
    # applet: then it only prints that), then sysrq.
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
# How xnuhost ended, from the status the inner shell's wait gave: "exit N", or "signal S" for a status of 128 + S
# (xnuhost's own exit codes are below 128: docs/booter.md). how_of says a record in words.
end_record() { # <status>
    if [ "$1" -gt 128 ] 2>/dev/null && [ "$1" -le 192 ]; then echo "signal $(($1 - 128))"; else echo "exit $1"; fi
}
signame() {
    case "$1" in
        1) echo SIGHUP ;; 2) echo SIGINT ;; 3) echo SIGQUIT ;; 4) echo SIGILL ;; 5) echo SIGTRAP ;; 6) echo SIGABRT ;;
        7) echo SIGBUS ;; 8) echo SIGFPE ;; 9) echo SIGKILL ;; 10) echo SIGUSR1 ;; 11) echo SIGSEGV ;; 12) echo SIGUSR2 ;;
        13) echo SIGPIPE ;; 14) echo SIGALRM ;; 15) echo SIGTERM ;; 16) echo SIGSTKFLT ;; 24) echo SIGXCPU ;;
        25) echo SIGXFSZ ;; 26) echo SIGVTALRM ;; 27) echo SIGPROF ;; 29) echo SIGIO ;; 30) echo SIGPWR ;; 31) echo SIGSYS ;;
        *) echo "signal $1" ;;
    esac
}
how_of() { # <exit N | signal S>
    case "$1" in
        "signal "*) echo "killed by signal ${1#signal } ($(signame "${1#signal }"))" ;;
        *) echo "$1" ;;
    esac
}
end_how() { how_of "$(end_record "$1")"; }
# The watcher's view of the record: how xnuhost <pid> ended, from session/xnuhost.exit ("pid P exit N" or "pid P
# signal S"). The inner shell writes it at once when its wait returns; while that shell still runs it is given 2 s.
end_of() { # <xnuhost pid>
    _ip=$(cat "$CTL/inner.pid" 2>/dev/null); _n=0
    while [ ! -s "$SESSION/xnuhost.exit" ] && [ $_n -lt 20 ] && [ -n "$_ip" ] && [ -d "$P/$_ip" ]; do sleep 0.1; _n=$((_n + 1)); done
    _r=$(head -n 1 "$SESSION/xnuhost.exit" 2>/dev/null)
    _w=${_r#"pid $1 "}
    case "$_w" in
        "$_r") echo "how is not recorded" ;;
        "exit "[0-9]*|"signal "[0-9]*) case "${_w#* }" in *[!0-9]*) echo "how is not recorded" ;; *) how_of "$_w" ;; esac ;;
        *) echo "how is not recorded" ;;
    esac
}
# What the host saw of xnuhost's end, read at once by the watcher (the kernel's ring and logcat's are overwritten
# within minutes; on 2026-11-23 neither reached back to the end by the time they were read): the kernel OOM killer's
# and lmkd's lines that name xnuhost or its pid, xnuhost's own lines in logcat (bionic's and the allocator's fatal
# messages go there, not to its log), the host's memory pressure and memory, and the session cgroup's memory events
# where the cgroup has the memory controller. One line each, into return.log.
death_notes() { # <xnuhost pid>
    _say() { echo "$(date '+%F %T') watcher: after xnuhost's end: $*"; }
    _k=$($TMO dmesg 2>/dev/null | grep -i -E "out of memory|oom-kill|oom_reaper|killed process|lowmemorykiller|xnuhost|[^0-9]$1[^0-9]" | tail -n 6 | cut -c1-300)
    if [ -n "$_k" ]; then echo "$_k" | while IFS= read -r _l; do _say "kernel: $_l"; done; else _say "kernel: no OOM kill and no line of xnuhost or pid $1 in dmesg"; fi
    _l=$($TMO logcat -d -b main,system,events -s lowmemorykiller killinfo 2>/dev/null | grep -E "xnuhost|[^0-9]$1[^0-9]" | tail -n 3 | cut -c1-300)
    if [ -n "$_l" ]; then echo "$_l" | while IFS= read -r _x; do _say "lmkd: $_x"; done; else _say "lmkd: no kill of xnuhost or pid $1 in logcat"; fi
    _l=$($TMO logcat -d -b main,system,crash --pid="$1" 2>/dev/null | tail -n 4 | cut -c1-300)
    [ -z "$_l" ] || echo "$_l" | while IFS= read -r _x; do _say "logcat of pid $1: $_x"; done
    _m=$(awk '/^(MemAvailable|SwapTotal|SwapFree):/ { printf "%s%s %d MiB", s, $1, $2 / 1024; s = ", " }' "$P/meminfo" 2>/dev/null)
    _p=$(awk '{ printf "%s%s", s, $0; s = " | " }' "$P/pressure/memory" 2>/dev/null)
    _say "host memory now: ${_m:-meminfo not readable}; pressure: ${_p:-none (no PSI)}"
    _c="$T/sys/fs/cgroup/oneios_session"
    if [ -f "$_c/memory.events" ]; then
        _say "the session cgroup's memory.events: $(awk '{ printf "%s%s %s", s, $1, $2; s = ", " }' "$_c/memory.events" 2>/dev/null)"
    else
        _say "the session cgroup has no memory.events (no memory controller there)"
    fi
}

# --- THE STAGE (no root tools needed; also what the tests run) -------------
# The runtime package and the image set as oneios_root.sh staged them. A
# missing runtime or image is the usual refusal: one line that says which.
stage_checks() {
    [ -d "$STAGE" ] && [ ! -L "$STAGE" ] || refuse "OneiOS is not set up on this phone ($STAGE is missing)"
    root_only "$STAGE" || refuse "$STAGE is not root's or is writable by others"
    for f in oneios_switch.sh oneios_return.sh; do
        [ -f "$STAGE/$f" ] && root_only "$STAGE/$f" || refuse "$STAGE/$f is missing or not root's"
    done

    # The runtime: runtime.conf (written by root from the checked runtime.json),
    # runtime.sha256 (every file root wrote), and xnuhost itself.
    RC="$STAGE/runtime.conf"
    [ -f "$RC" ] && [ -d "$STAGE/runtime" ] && [ ! -L "$STAGE/runtime" ] ||
        refuse "no OneiOS runtime is staged: xnuhost, the program that runs iOS, comes with it (download or import the runtime in the OneOS app)"
    root_only "$RC" && root_only "$STAGE/runtime" || refuse "the staged runtime is not root's"
    R_VERSION=$(conf "$RC" version)
    R_ABI=$(conf "$RC" session_abi)
    R_XNUHOST=$(conf "$RC" xnuhost)
    R_FORMATS=$(conf "$RC" image_formats)
    case "$R_XNUHOST" in
        ''|/*|*..*|*[!A-Za-z0-9._/+-]*) refuse "the runtime ${R_VERSION:-?} names no xnuhost (runtime.conf: '${R_XNUHOST}')" ;;
    esac
    [ "$R_ABI" = "$ABI" ] ||
        refuse "the runtime ${R_VERSION:-?} speaks session ABI ${R_ABI:-none}, this OneOS speaks $ABI: update the OneOS app or the runtime"
    X="$STAGE/runtime/$R_XNUHOST"
    [ -f "$X" ] && [ ! -L "$X" ] ||
        refuse "the runtime ${R_VERSION:-?} has no xnuhost ($R_XNUHOST): it cannot start iOS yet"
    root_only "$X" && [ -x "$X" ] || refuse "xnuhost is not root's, or not executable"
    # OneiOS's packages carry a stand-in that only prints "not built yet" until
    # xnuhost is built (runtime.json "placeholder": true). One UI is not stopped for it.
    [ "$(conf "$RC" placeholder)" != 1 ] ||
        refuse "the runtime ${R_VERSION:-?} carries a placeholder instead of xnuhost (OneiOS has not built xnuhost yet): it cannot start iOS"
    # An arm64 ELF executable: "\177ELF", class 2 (64-bit), e_machine 0xb7.
    [ "$(od -An -tx1 -N5 "$X" 2>/dev/null | tr -d ' \n')" = 7f454c4602 ] &&
        [ "$(od -An -tx1 -j18 -N2 "$X" 2>/dev/null | tr -d ' \n')" = b700 ] ||
        refuse "xnuhost is not an arm64 program"
    check_list runtime full

    # The image set: its format must be one this runtime boots.
    IC="$STAGE/image.conf"
    [ -f "$IC" ] && [ -d "$STAGE/image" ] && [ ! -L "$STAGE/image" ] ||
        refuse "no iOS image set is staged: import the one you built with OneiOS's scripts in the OneOS app"
    root_only "$IC" && root_only "$STAGE/image" || refuse "the staged image set is not root's"
    I_FORMAT=$(conf "$IC" format)
    I_VERSION=$(conf "$IC" version)
    I_BUILD=$(conf "$IC" build)
    case "$I_FORMAT" in ''|*[!0-9]*) refuse "the image set has no format number (image.conf)" ;; esac
    case ",$R_FORMATS," in
        *",$I_FORMAT,"*) ;;
        *) refuse "the image set is format $I_FORMAT, the runtime ${R_VERSION:-?} boots format(s) ${R_FORMATS:-none}: build the image again or take a matching runtime" ;;
    esac
    check_list image ids
}
# <runtime|image> <full|ids>: $STAGE/<kind>.sha256 lists exactly the files of
# $STAGE/<kind>, each root's. full: every SHA-256 again (the runtime is small).
# ids: each file is the one root hashed at staging (dev:inode:size:mtime in
# <kind>.ids); files under 64 MiB are hashed again, and all of them with
# ONEIOS_VERIFY_IMAGE=1 (minutes for an image of several GB).
# quick (the app's status: --check with ONEIOS_CHECK_QUICK=1): both kinds by their
# ids only, nothing hashed, so iOS 27's page has its answer in a moment. The
# switch never takes it: its own preflight hashes as above before the first change.
check_list() {
    kind=$1 how=$2
    [ "$QUICK" != 1 ] || how=quick
    SUMS="$STAGE/$kind.sha256"
    [ -f "$SUMS" ] && root_only "$SUMS" || refuse "$kind.sha256 is missing or not root's: stage the $kind again"
    bad=$(awk 'NF != 2 || length($1) != 64 || $1 ~ /[^0-9a-f]/ || $2 !~ /^[A-Za-z0-9_][A-Za-z0-9._+\/-]*$/ || $2 ~ /\.\./ ||
               seen[$2]++ { print NR ": " $0 }' "$SUMS" | head -n 3)
    [ -z "$bad" ] || refuse "$kind.sha256 has malformed lines: $bad"
    [ -s "$SUMS" ] || refuse "$kind.sha256 is empty"
    if [ "$how" != full ]; then
        IDS="$STAGE/$kind.ids"
        [ -f "$IDS" ] && root_only "$IDS" || refuse "$kind.ids is missing or not root's: stage the $kind again"
    fi
    while read -r sum name || [ -n "$sum" ]; do
        f="$STAGE/$kind/$name"
        [ -f "$f" ] && [ ! -L "$f" ] || refuse "$kind/$name is missing or a link: stage the $kind again"
        root_only "$f" || refuse "$kind/$name is not root's or is writable by others"
        hash=1
        if [ "$how" != full ]; then
            want=$(awk -v n="$name" '$2 == n { print $1 }' "$IDS")
            [ -n "$want" ] && [ "$(file_id "$f")" = "$want" ] ||
                refuse "$kind/$name changed since it was staged: stage the $kind again"
            if [ "$how" = quick ]; then hash=0
            # (awk, not the shell: Android's sh counts in 32 bits, and an image of several GB wraps.)
            else [ "${ONEIOS_VERIFY_IMAGE:-0}" = 1 ] || awk -v b="$(stat -c %s "$f" 2>/dev/null)" 'BEGIN { exit !(b + 0 < 67108864) }' || hash=0
            fi
        fi
        if [ $hash = 1 ]; then
            [ "$(sha256sum "$f" 2>/dev/null | cut -d' ' -f1)" = "$sum" ] ||
                refuse "$kind/$name does not match its SHA-256: stage the $kind again"
        fi
    done < "$SUMS"
    # Nothing the list does not name (a leftover would be visible to xnuhost): one awk that reads the list once,
    # not one awk for each file.
    extra=$(cd "$STAGE/$kind" && find . ! -type d | sed 's|^\./||' |
        awk -v s="$SUMS" 'BEGIN { while ((getline l < s) > 0) { split(l, w, " "); listed[w[2]] = 1 } } !($0 in listed)' |
        head -n 3 | tr '\n' ' ')
    [ -z "$extra" ] || refuse "$kind/ holds files its list does not name ($extra): stage the $kind again"
}

# --- ONE UI'S CLOCK CAPS ----------------------------------------------------
# One UI (Samsung's SSRM in system_server, and the HALs it drives) caps the CPU and
# GPU clocks when the phone is warm, and its power HAL raises the CPUs' floors in
# bursts. The switch stops system_server, so whatever it last wrote stayed for the
# whole session: 1.7-2.0 GHz CPUs and a 500 MHz GPU after a warm One UI (the S24
# Ultra, 2026-11-12; OneiOS docs/hardware.md 7d). These nodes are saved while One
# UI is whole (clocks_save, into control/base/clocks: node, One UI's value, the
# session's) and the hardware's range is written once system_server is gone
# (clocks_tops); the return writes One UI's values back before its zygote starts,
# on every path that stopped One UI, a killed xnuhost's too. The kernel's thermal
# zones, trips and cooling devices are never written: they, LMh and xnuhost's own
# thermal step (OneiOS runtime/bridges/thermal) cap the session. Nothing under
# /sys/power.
clock_top() { # <list of numbers>: the largest
    awk '{ for (i = 1; i <= NF; i++) if ($i ~ /^[0-9]+$/ && $i + 0 > m) m = $i + 0 } END { if (m) print m }'
}
clocks_save() {
    out="$CTL/base/clocks"
    true > "$out"
    # Samsung's cpufreq_limit (drivers/cpufreq/cpufreq_limit.c of the SM8650 kernel): SSRM's one value for every
    # cluster, held as a freq QoS request of its own above scaling_max_freq and scaling_min_freq (so a write there
    # does not lift it: the phone, 2026-11-12, 2035200 kept); -1 releases it. First in the file: released first,
    # put back last.
    for n in cpufreq_max_limit cpufreq_min_limit; do
        v=$(cat "$T/sys/devices/system/cpu/cpufreq_limit/$n" 2>/dev/null)
        case "${v#-}" in ''|*[!0-9]*) ;; *) echo "/sys/devices/system/cpu/cpufreq_limit/$n $v -1" >> "$out" ;; esac
    done
    for pol in "$T"/sys/devices/system/cpu/cpufreq/policy*; do
        [ -d "$pol" ] || continue
        lo=$(cat "$pol/cpuinfo_min_freq" 2>/dev/null); hi=$(cat "$pol/cpuinfo_max_freq" 2>/dev/null)
        mn=$(cat "$pol/scaling_min_freq" 2>/dev/null); mx=$(cat "$pol/scaling_max_freq" 2>/dev/null)
        case "$lo$hi$mn$mx" in ''|*[!0-9]*) continue ;; esac
        echo "${pol#"$T"}/scaling_min_freq $mn $lo" >> "$out"
        echo "${pol#"$T"}/scaling_max_freq $mx $hi" >> "$out"
    done
    g="$T/sys/kernel/gpu"
    v=$(cat "$g/gpu_max_clock" 2>/dev/null); top=$(clock_top < "$g/gpu_freq_table" 2>/dev/null)
    case "$v" in ''|*[!0-9]*) ;; *) [ -z "$top" ] || echo "/sys/kernel/gpu/gpu_max_clock $v $top" >> "$out" ;; esac
    k="$T/sys/class/kgsl/kgsl-3d0"
    v=$(cat "$k/max_gpuclk" 2>/dev/null); top=$(clock_top < "$k/gpu_available_frequencies" 2>/dev/null)
    case "$v" in ''|*[!0-9]*) ;; *) [ -z "$top" ] || echo "/sys/class/kgsl/kgsl-3d0/max_gpuclk $v $top" >> "$out" ;; esac
    pl=""
    [ ! -e "$k/thermal_pwrlevel" ] || pl="; KGSL thermal_pwrlevel $(cat "$k/thermal_pwrlevel" 2>/dev/null)"
    echo "Clocks of One UI: $(awk '{ printf "%s %s, ", $1, $2 }' "$out" | sed 's/, $//')$pl"
}
clocks_tops() {
    # The mark first: from here the return writes One UI's values back.
    echo "$(date +%s)" > "$CTL/clocks.set"
    while read -r node old new; do
        case "$node" in /sys/devices/system/cpu/cpufreq/policy*/scaling_m??_freq|/sys/kernel/gpu/gpu_max_clock|/sys/class/kgsl/kgsl-3d0/max_gpuclk) ;;
            /sys/devices/system/cpu/cpufreq_limit/cpufreq_max_limit|/sys/devices/system/cpu/cpufreq_limit/cpufreq_min_limit) ;; *) continue ;; esac
        case "${old#-}${new#-}" in ''|*[!0-9]*) continue ;; esac
        if echo "$new" > "$T$node" 2>/dev/null; then
            echo "clocks: $node $old -> $new (reads $(cat "$T$node" 2>/dev/null))"
        else
            echo "clocks: $node $old -> $new not written (left at $(cat "$T$node" 2>/dev/null))"
        fi
    done < "$CTL/base/clocks"
    l="$T/sys/devices/system/cpu/cpufreq_limit/limit_stat"
    [ ! -e "$l" ] || echo "clocks: cpufreq_limit limit_stat: $(awk '{ printf "%s ", $0 }' "$l" 2>/dev/null | cut -c1-300)"
    k="$T/sys/class/kgsl/kgsl-3d0"
    [ ! -e "$k/thermal_pwrlevel" ] || echo "clocks: KGSL thermal_pwrlevel $(cat "$k/thermal_pwrlevel" 2>/dev/null), max_gpuclk $(cat "$k/max_gpuclk" 2>/dev/null)"
}

# --- THE SESSION MODE: hosted (the default) or the Android takeover ------------
# session-mode= comes from the app (root's switch verb passes ONEIOS_SESSION_MODE when its toggle is on), else from
# the staged image's xnuhost.conf files (the last session-mode= line, as xnuhost reads them: image/xnuhost.conf,
# then image/overlay/userland/xnuhost.conf), else hosted. takeover is refused, before anything changes, where the
# phone's row of OneiOS's host table does not allow it (xnuhost --host-info: takeover=yes), where the runtime's
# xnuhost is too old to say, and where there is no CPU policy for its cap. hosted adds no line and no step.
SMODE=hosted SMODE_FROM=default
session_mode_pick() {
    if [ -n "${ONEIOS_SESSION_MODE:-}" ]; then
        SMODE=$ONEIOS_SESSION_MODE SMODE_FROM="the app"
    else
        v=$(cat "$STAGE/image/xnuhost.conf" "$STAGE/image/overlay/userland/xnuhost.conf" 2>/dev/null |
            sed -n 's/^[[:space:]]*session-mode=//p' | tail -n 1 | tr -d ' \t\r')
        [ -z "$v" ] || SMODE=$v SMODE_FROM="the image's xnuhost.conf"
    fi
    case "$SMODE" in
        hosted|takeover) ;;
        *) refuse "session-mode '$SMODE' (from $SMODE_FROM) is not hosted or takeover" ;;
    esac
}
# The cap's policies: every cpufreq policy the baseline saved (clocks_save), with a top to scale from.
cap_policies() {
    awk '$1 ~ /^\/sys\/devices\/system\/cpu\/cpufreq\/policy[0-9]+\/scaling_max_freq$/ && $3 ~ /^[0-9]+$/ && $3 > 0 { print $1 }' "$1" 2>/dev/null
}
# The Android takeover's stops (OneiOS docs/plan-ios-first-session.md 4, stage 2b): services of One UI's zygote's
# restart list that no bridge of a session uses. Every return restarts this list already (oneios_return.sh, Gate B
# and its step 4), so a stop adds no new step to the way back. The first six are the default; netd and media only when
# the image's xnuhost.conf names them (a Wi-Fi join and an encode without them are not yet checked on the phone).
# takeover-stops= (the last such line of image/xnuhost.conf, then image/overlay/userland/xnuhost.conf): default, none,
# or names of this list separated by commas. OneiOS's xnuhost checks the same word (config.rs TAKEOVER_STOPPABLE).
TAKEOVER_STOPPABLE="cameraserver mediaextractor mediametrics media.tuner perfmond wificond netd media"
TAKEOVER_DEFAULT="cameraserver mediaextractor mediametrics media.tuner perfmond wificond"
# TSTOPS: the names, in order (empty for none); TSTOPS_FROM: where they come from. Refuses a word it does not know.
takeover_stops_pick() {
    TSTOPS=$TAKEOVER_DEFAULT TSTOPS_FROM="the default list"
    v=$(cat "$STAGE/image/xnuhost.conf" "$STAGE/image/overlay/userland/xnuhost.conf" 2>/dev/null |
        sed -n 's/^[[:space:]]*takeover-stops=//p' | tail -n 1 | tr -d ' \t\r')
    [ -n "$v" ] || return 0
    TSTOPS_FROM="the image's xnuhost.conf (takeover-stops=$v)"
    case "$v" in
        default) return 0 ;;
        none) TSTOPS=""; return 0 ;;
    esac
    TSTOPS=""
    for s in $(echo "$v" | tr ',' ' '); do
        case " $TAKEOVER_STOPPABLE " in *" $s "*) ;; *) refuse "takeover-stops: '$s' (in the image's xnuhost.conf) is not one of: $TAKEOVER_STOPPABLE" ;; esac
        case " $TSTOPS " in *" $s "*) refuse "takeover-stops: '$s' is named twice (in the image's xnuhost.conf)" ;; esac
        TSTOPS="${TSTOPS:+$TSTOPS }$s"
    done
    case ",$v," in *,,*) refuse "takeover-stops: '$v' (in the image's xnuhost.conf) has an empty name" ;; esac
}
# How init defines service $1, from the .rc files it reads (named folders, one awk for all): "critical" (the service
# has the critical option: never stopped), "found", or nothing (no .rc names it: not stopped either).
rc_kind() {
    rk_s=$1
    # Only files that are there: a folder with no .rc leaves its pattern as it is, and some awks end at a missing file.
    set --
    for rk_f in "$T"/system/etc/init/*.rc "$T"/system_ext/etc/init/*.rc "$T"/product/etc/init/*.rc \
        "$T"/vendor/etc/init/*.rc "$T"/odm/etc/init/*.rc "$T"/apex/*/etc/*.rc; do
        [ -f "$rk_f" ] && set -- "$@" "$rk_f"
    done
    [ $# -gt 0 ] || return 0
    awk -v s="$rk_s" 'FNR == 1 { in_ = 0 }
        $1 == "service" { in_ = ($2 == s); if (in_) f = 1; next }
        $1 == "on" || $1 == "import" { in_ = 0 }
        in_ && $1 == "critical" { c = 1 }
        END { if (c) print "critical"; else if (f) print "found" }' "$@" 2>/dev/null
}
mem_avail() { awk '$1 == "MemAvailable:" { print int($2 / 1024); exit }' "$P/meminfo" 2>/dev/null; }
# The stops (--takeover-stops), after zygote's stop and system_server's end, before the stop loop and xnuhost start:
# each name that runs and is not critical is written to control/base/stopped first, then ctl.stop; then up to 5 s for
# init to say each is no longer running, so that xnuhost's ram=auto sees the RAM they held. Nothing persistent: a
# reboot brings every one back; the return starts each one and fails safe (the restart) if one does not come back.
# TSTOPS and TSTOPS_FROM are the preflight's (takeover_stops_pick): nothing here refuses, One UI is already stopped.
takeover_stops() {
    rm -f "$CTL/base/stopped"
    [ -n "$TSTOPS" ] || { echo "Android takeover: no service of Android stopped (takeover-stops=none)"; return 0; }
    before=$(mem_avail)
    done_="" kept=""
    for s in $TSTOPS; do
        st=$(getprop "init.svc.$s")
        [ "$st" = running ] || { kept="$kept $s(${st:-no such service})"; continue; }
        k=$(rc_kind "$s")
        case "$k" in
            critical) kept="$kept $s(critical in its .rc)"; continue ;;
            found) ;;
            *) kept="$kept $s(no .rc names it)"; continue ;;
        esac
        echo "$s" >> "$CTL/base/stopped" || { kept="$kept $s(control/base/stopped not written)"; continue; }
        setprop ctl.stop "$s"
        done_="$done_ $s"
    done
    n=0
    while [ $n -lt 25 ]; do
        up=""
        for s in $done_; do [ "$(getprop "init.svc.$s")" != running ] || up="$up $s"; done
        [ -n "$up" ] || break
        sleep 0.2; n=$((n + 1))
    done
    after=$(mem_avail)
    echo "Android takeover: stopped${done_:- nothing} (from $TSTOPS_FROM; control/base/stopped)${kept:+; not stopped:$kept}${up:+; still running after 5 s:$up}; host MemAvailable ${before:-?} -> ${after:-?} MiB"
}
takeover_checks() { # <xnuhost to ask>
    # The stop list first: a word xnuhost does not know would make it refuse the conf below, with a less clear line.
    takeover_stops_pick
    info=$("$1" --host-info $(for f in "$STAGE/image/xnuhost.conf" "$STAGE/image/overlay/userland/xnuhost.conf"; do [ -f "$f" ] && echo "--config $f"; done) 2>&1 </dev/null)
    rc=$?
    info=$(printf '%s\n' "$info" | grep -m1 '^host-info: ')
    [ $rc = 0 ] && [ -n "$info" ] ||
        refuse "session-mode=takeover (from $SMODE_FROM): the runtime ${R_VERSION:-?}'s xnuhost does not answer --host-info (a runtime from before the Android takeover): get a newer runtime, or switch without the takeover"
    case "$info" in
        *" takeover=yes "*) ;;
        *) refuse "session-mode=takeover (from $SMODE_FROM) is not supported on this phone (${info#host-info: }): switch without the Android takeover" ;;
    esac
    n=0
    for pol in "$T"/sys/devices/system/cpu/cpufreq/policy*; do
        [ -f "$pol/cpuinfo_max_freq" ] && [ -f "$pol/scaling_max_freq" ] && n=$((n + 1))
    done
    [ $n -gt 0 ] || refuse "session-mode=takeover (from $SMODE_FROM): no CPU policy for its CPU cap (/sys/devices/system/cpu/cpufreq/policy*)"
    [ -r "$T/sys/class/power_supply/battery/temp" ] ||
        refuse "session-mode=takeover (from $SMODE_FROM): the cell's temperature, its CPU cap's input, is not readable"
    echo "Session mode: Android takeover (session-mode=takeover, from $SMODE_FROM; ${info#host-info: }): iOS gets the touchscreen alone; Android's services stopped for the session: ${TSTOPS:-none} (from $TSTOPS_FROM); a CPU cap from the cell's temperature (50 C up); the way back as in every session"
}

# The Android takeover's CPU cap (--cpu-cap): levels from the cell (power_supply/battery/temp, in tenths of a degree
# C) only; the case (Samsung's lrp; the board thermistor where there is none) is read and logged, never a level.
# Re-judged 2026-11-23 from the hosted sessions of that day (OneiOS out/session-logs/2026-11-23-mac-*): a hosted
# session has no cap of ours either (One UI's SSRM goes with system_server in both modes) and runs on the kernel's own
# trips (the SoC at 92-95 C), with the case at 44-50.1 C and the cell up to 43.6 C. The first cap (case 46/48/50 C,
# cell 46/47/48 C) would have cut the clocks at once in such a session and ended it at the case's 50 C. The case is
# the skin, not the hardware, and the kernel's junction trips already protect the SoC; what nothing in a session
# guards is the cell while the SoC heats it (the kernel's battery driver stops charging and, far higher, shuts the
# phone down, but caps no CPU). So the cap acts only on the cell, above anything a hosted session reached:
#   level 1: the cell at 50 C: each policy's scaling_max_freq at 80 % of its top
#   level 2: the cell at 52 C: 60 %
#   level 3: the cell at 55 C: still 60 %, and a return to One UI is asked (in place, as every return:
#            session/return.request)
# A level is left one step at a time when the cell is 2 C under it for 3 readings in a row. 50-55 C sits under the
# usual 60 C discharge limit of a Li-ion cell [a guess: Samsung's own battery limits were not read on the phone].
# Only scaling_max_freq of the policies clocks_save saved is written, never above the top clocks_tops wrote, never
# under cpuinfo_min_freq; never scaling_min_freq, a thermal node, a GPU node or /sys/power.
CAP_EVERY=2
CAP_CELL_LIMIT=550
cap_level() { # <case> <cell> <margin>, tenths of a degree: LV, the level those readings ask for (the case is not one)
    cl_b=$(($2 + $3))
    if [ $cl_b -ge $CAP_CELL_LIMIT ]; then LV=3
    elif [ $cl_b -ge 520 ]; then LV=2
    elif [ $cl_b -ge 500 ]; then LV=1
    else LV=0; fi
}
cap_pct() { case "$1" in 0) PCT=100 ;; 1) PCT=80 ;; *) PCT=60 ;; esac; }
deg() { echo "$(($1 / 10)).$(($1 % 10)) C"; }
tdeg() { case "${1#-}" in ''|*[!0-9]*) echo "?" ;; *) deg "$1" ;; esac; } # a reading that may be missing
pol_name() { pn=${1#/sys/devices/system/cpu/cpufreq/}; echo "${pn%/scaling_max_freq}"; }

# --- USB AND ADB DURING A SESSION ---------------------------------------------
# (docs/oneios.md, "USB and adb during a session"; OneiOS's oneos/interface.md.)
# One UI's framework is what sets the USB gadget's functions: UsbDeviceManager in
# system_server, through the USB gadget HAL or init's sys.usb.config triggers, on
# every plug-in and unplug. The switch stops system_server, so for the whole
# session nobody re-arms the gadget: whatever unbinds it, or drops adb from it,
# stays (the S24 Ultra, 2026-11-13: a cable plugged in during the session, and
# the Mac saw no USB device at all). usb_save records it while One UI is whole
# (control/base/usb); the session's USB watcher (--usb-watch) keeps adb on it,
# with One UI's own values only; the return puts back what differs.
# Only named files and properties: sys.usb.controller names the UDC, and
# /sys/class/udc is never listed. Nothing is written but sys.usb.config (One
# UI's value), ctl.start adbd and the gadget's UDC file (One UI's controller).
UDC_FILE="$T/config/usb_gadget/g1/UDC"
usb_read() { head -c 64 "$1" 2>/dev/null | tr -d '\n'; }      # one named file, one line
usb_name() { # a controller name that is one path component, else nothing
    case "$1" in ''|.|..|*/*|*[!A-Za-z0-9._:-]*) echo "" ;; *) echo "$1" ;; esac
}
usb_has_adb() { case ",$1," in *,adb,*) return 0 ;; esac; return 1; }
usb_now() { # the gadget as it is now, on one line
    _uc=$(usb_name "$(getprop sys.usb.controller)")
    _us=""; [ -z "$_uc" ] || _us=$(usb_read "$T/sys/class/udc/$_uc/state")
    echo "state $(getprop sys.usb.state), config $(getprop sys.usb.config), UDC ${_uc:-?} ${_us:-?}; bound '$(usb_read "$UDC_FILE")', adbd $(getprop init.svc.adbd), ffs.ready $(getprop sys.usb.ffs.ready), cable $(usb_read "$T/sys/class/power_supply/usb/online")"
}
usb_save() {
    _cfg=$(getprop sys.usb.config)
    _adb=0
    usb_has_adb "$_cfg" && _adb=1
    usb_has_adb "$(getprop persist.sys.usb.config)" && _adb=1
    [ "$(settings get global adb_enabled 2>/dev/null)" = 1 ] && _adb=1
    {
        echo "adb=$_adb"
        echo "config=$_cfg"
        echo "state=$(getprop sys.usb.state)"
        echo "persist=$(getprop persist.sys.usb.config)"
        echo "controller=$(usb_name "$(getprop sys.usb.controller)")"
        echo "udc=$(usb_read "$UDC_FILE")"
        echo "adbd=$(getprop init.svc.adbd)"
        echo "configfs=$(getprop sys.usb.configfs)"
        # The repairs of the USB watcher and the return: only with $STAGE/usb-repair (or ONEIOS_USB_REPAIR=1)
        _rep=0; { [ -e "$STAGE/usb-repair" ] || [ "${ONEIOS_USB_REPAIR:-0}" = 1 ]; } && _rep=1
        echo "repair=$_rep"
    } > "$CTL/base/usb"
    echo "USB of One UI: $(usb_now); USB debugging $([ $_adb = 1 ] && echo on || echo off)"
}

# --- INTERNAL MODES --------------------------------------------------------
case "$MODE" in
    --clocks-save|--clocks-tops)
        # The tests' way in (OneiosScriptTest, against a fake sysfs): the same two steps the session takes.
        [ -n "$T" ] || { echo "$MODE: for the tests only"; exit 2; }
        mkdir -p "$CTL/base"
        if [ "$MODE" = --clocks-save ]; then clocks_save; else clocks_tops; fi
        exit 0 ;;
    --usb-save)
        # The tests' way in (against a fake phone): the step the session takes at its baseline.
        [ -n "$T" ] || { echo "$MODE: for the tests only"; exit 2; }
        mkdir -p "$CTL/base"
        usb_save
        exit 0 ;;
    --mode-check)
        # The tests' way in (against a fake phone): the session mode's choice and its preflight, with a stand-in
        # for xnuhost's --host-info (ONEIOS_TEST_XNUHOST). Prints what the preflight prints; refuses as it refuses.
        [ -n "$T" ] || { echo "$MODE: for the tests only"; exit 2; }
        session_mode_pick
        [ "$SMODE" = hosted ] || takeover_checks "${ONEIOS_TEST_XNUHOST:-$T/none}"
        echo "MODE OK $SMODE"
        exit 0 ;;
    --cpu-cap)
        # The Android takeover's CPU cap ("THE SESSION MODE" above), started by the switch once system_server is
        # gone and the hardware's range is written (clocks_tops), in init's mount namespace, outside xnuhost's
        # cgroup; not the way back, so not out_of_the_way: no OOM score of its own, no renice. Every CAP_EVERY
        # seconds it reads two named files with the shell's own read (no process per reading), and writes only
        # when its level changes. It ends with the session (a state that is not starting or running), on
        # control/cpu-cap.off, and when the return kills it; the return writes One UI's values back after it is
        # gone. Its lines go to control/cpu-cap.log; its level, for the return, to control/cpu-cap.level.
        [ "$(cat "$CTL/base/mode" 2>/dev/null)" = takeover ] || { echo "$(date '+%F %T') cpu-cap: not an Android takeover session: nothing to do"; exit 0; }
        echo $$ > "$CTL/cpu-cap.pid"
        rm -f "$CTL/cpu-cap.ended"
        trap 'echo "$(date +%s)" 2>/dev/null > "$CTL/cpu-cap.ended"' EXIT
        csay() { echo "$(date '+%F %T') cpu-cap: $*"; }
        CASE_F="$T/sys/class/power_supply/battery/lrp" CASE_N=lrp
        [ -r "$CASE_F" ] || CASE_F="$T/sys/class/sec/sec-ap-thermistor/temperature" CASE_N=sec-ap-thermistor
        CELL_F="$T/sys/class/power_supply/battery/temp"
        NODES=$(cap_policies "$CTL/base/clocks")
        [ -n "$NODES" ] || { csay "no CPU policy in $CTL/base/clocks: nothing to cap"; exit 0; }
        TOPS="" LOS=""
        for node in $NODES; do
            top=$(awk -v n="$node" '$1 == n { print $3; exit }' "$CTL/base/clocks")
            lo=$(cat "$T${node%/scaling_max_freq}/cpuinfo_min_freq" 2>/dev/null)
            case "$lo" in ''|*[!0-9]*) lo=0 ;; esac
            TOPS="$TOPS $top" LOS="$LOS $lo"
        done
        # Writes each policy's cap for level $1, unless the session is over. Its line says what each reads after.
        cap_write() {
            cap_pct "$1"
            out="" i=0
            for node in $NODES; do
                i=$((i + 1))
                set -- $TOPS; eval "top=\${$i}"
                set -- $LOS; eval "lo=\${$i}"
                want=$((top / 100 * PCT))
                [ "$PCT" != 100 ] || want=$top
                [ "$want" -ge "$lo" ] || want=$lo
                read -r st < "$CTL/state" 2>/dev/null || st=""
                case "$st" in starting|running) ;; *) return 1 ;; esac
                [ ! -e "$CTL/cpu-cap.off" ] || return 1
                if echo "$want" 2>/dev/null > "$T$node"; then
                    read -r got < "$T$node" 2>/dev/null || got="?"
                    out="$out $(pol_name "$node")=$got"
                else
                    out="$out $(pol_name "$node"):not-written"
                fi
            done
            echo "$LEVEL" 2>/dev/null > "$CTL/cpu-cap.level"
            csay "level $LEVEL ($PCT % of each policy's top): case $(tdeg "$CASE") ($CASE_N), cell $(deg "$CELL"):$out"
            return 0
        }
        LEVEL=0 CASE=0 CELL=0 low=0 bad="" asked=0 t=0
        echo 0 > "$CTL/cpu-cap.level"
        csay "watching every $CAP_EVERY s: case $CASE_F, cell $CELL_F; policies:$(for node in $NODES; do printf " %s" "$(pol_name "$node")"; done), tops$TOPS; level 0: the hardware's top (clocks_tops)"
        while :; do
            read -r st < "$CTL/state" 2>/dev/null || st=""
            case "$st" in starting|running) ;; *) csay "the session is over (state '$st'): the cap ends at level $LEVEL"; exit 0 ;; esac
            [ ! -e "$CTL/cpu-cap.off" ] || { csay "control/cpu-cap.off: the cap ends at level $LEVEL"; exit 0; }
            c="" b=""
            read -r c < "$CASE_F" 2>/dev/null
            read -r b < "$CELL_F" 2>/dev/null
            # The cell decides; the case is only logged (a case that cannot be read is "?").
            case "${c#-}" in ''|*[!0-9]*) c="" ;; esac
            case "${b#-}" in
                ''|*[!0-9]*)
                    [ -n "$bad" ] || csay "the cell's reading is not a number (cell '$b', case '$c'): the level stays $LEVEL"
                    bad=1 ;;
                *)
                    bad="" CASE=$c CELL=$b
                    cap_level "$CASE" "$CELL" 0
                    if [ "$LV" -gt "$LEVEL" ]; then
                        # Up at once (level 3 caps as level 2 and asks for the return).
                        LEVEL=$LV low=0
                        cap_write "$LEVEL" || exit 0
                    elif [ "$LV" -lt "$LEVEL" ] && [ "$LEVEL" -lt 3 ]; then
                        # Down one step only when the cell is 2 C under this level for 3 readings in a row.
                        cap_level "$CASE" "$CELL" 20
                        if [ "$LV" -lt "$LEVEL" ]; then low=$((low + 1)); else low=0; fi
                        if [ $low -ge 3 ]; then LEVEL=$((LEVEL - 1)) low=0; cap_write "$LEVEL" || exit 0; fi
                    else
                        low=0
                    fi
                    if [ "$LEVEL" = 3 ] && [ $asked = 0 ]; then
                        asked=1
                        [ -e "$SESSION/return.request" ] ||
                            echo "thermal: the Android takeover's limit: cell $(deg "$CELL") (limit $(deg "$CAP_CELL_LIMIT")), case $(tdeg "$CASE") ($CASE_N, not a limit) at $(date '+%F %T')" > "$SESSION/return.request"
                        csay "level 3: a return to One UI is asked (session/return.request); the cap stays at 60 % until it ends"
                    fi ;;
            esac
            # One line a minute while capped, so the log shows the readings the level rests on.
            t=$((t + CAP_EVERY))
            [ "$LEVEL" = 0 ] || [ $((t % 60)) -ne 0 ] || csay "level $LEVEL: case $(tdeg "$CASE"), cell $(deg "$CELL")"
            sleep $CAP_EVERY
        done ;;
    --usb-watch)
        # The session's USB watcher, started once One UI's framework is stopped
        # (above, "USB AND ADB DURING A SESSION"); its lines go to control/usb.log.
        # Every 3 s it reads the gadget and logs it when it changed; at most one
        # repair every 21 s, in this order: adbd not running (ctl.start adbd); adb
        # gone from sys.usb.config (One UI's value again); the UDC file empty while
        # One UI had it bound (One UI's controller written); a cable in for 15 s
        # with the UDC still "not attached", "attached" or "powered" (sys.usb.config
        # none, then One UI's: init or the HAL binds it again; twice per plug-in at
        # most, so a charger that never enumerates is left alone). Not with USB
        # debugging off at the switch. Ends on control/usb-watch.off, or when the
        # session is over. Not the way back: nothing of the return waits for it.
        echo $$ > "$CTL/usb-watch.pid"
        U="$CTL/base/usb"
        usay() { echo "$(date '+%F %T') usb: $*"; }
        [ "$(conf "$U" adb)" = 1 ] || { usay "One UI had USB debugging off at the switch (or no $U): nothing to keep"; exit 0; }
        CFG=$(conf "$U" config)
        usb_has_adb "$CFG" || CFG=$(conf "$U" persist)
        usb_has_adb "$CFG" || CFG=adb
        CTRL=$(usb_name "$(conf "$U" controller)")
        BOUND=$(conf "$U" udc)
        [ "$BOUND" != none ] || BOUND=""
        EVERY=3
        # Repairs only where the stage asks for them (usb-repair, recorded at the switch as repair=1): not run on the
        # phone yet, so off by default; off, every repair is logged and nothing is written.
        REPAIR=$(conf "$U" repair)
        OFF=""; [ "$REPAIR" = 1 ] || OFF=" (repairs are off: logged only; $STAGE/usb-repair turns them on)"
        act() { [ "$REPAIR" = 1 ] || return 0; "$@"; }
        udc_put() { [ "$REPAIR" = 1 ] || return 0; echo "$1" 2>/dev/null > "$UDC_FILE"; }
        usay "watching every ${EVERY} s: keeps config $CFG, adbd and UDC ${CTRL:-?} (bound '${BOUND}' at the switch), repairs $([ "$REPAIR" = 1 ] && echo on || echo off)"
        last=""; n=0; fix=-100; plug=0; tries=0; cable0=""
        while [ ! -e "$CTL/usb-watch.off" ]; do
            case "$(cat "$CTL/state" 2>/dev/null)" in returning|returned|failed) usay "the session is over: the watcher ends"; exit 0 ;; esac
            now=$(usb_now)
            [ "$now" = "$last" ] || { usay "$now"; last=$now; }
            cable=$(usb_read "$T/sys/class/power_supply/usb/online")
            if [ "$cable" = 1 ] && [ "$cable0" != 1 ]; then plug=$n; tries=0; fi
            cable0=$cable
            if [ $((n - fix)) -ge 7 ]; then
                cfg=$(getprop sys.usb.config)
                b=$(usb_read "$UDC_FILE"); [ "$b" != none ] || b=""
                if [ "$(getprop init.svc.adbd)" != running ]; then
                    usay "adbd is '$(getprop init.svc.adbd)': ctl.start adbd$OFF"
                    act setprop ctl.start adbd; fix=$n
                elif ! usb_has_adb "$cfg"; then
                    usay "adb is gone from the gadget (config '$cfg'): sys.usb.config $CFG again$OFF"
                    act setprop sys.usb.config "$CFG"; fix=$n
                elif [ -n "$CTRL" ] && [ -n "$BOUND" ] && [ -z "$b" ]; then
                    if udc_put "$CTRL"; then usay "the gadget was unbound: UDC $CTRL written$OFF"
                    else usay "the gadget was unbound: UDC $CTRL could not be written (adbd's endpoints not ready yet?)"; fi
                    fix=$n
                elif [ "$cable" = 1 ] && [ -n "$CTRL" ] && [ $tries -lt 2 ] && [ $((n - plug)) -ge 5 ]; then
                    st=$(usb_read "$T/sys/class/udc/$CTRL/state")
                    case "$st" in
                        "not attached"|attached|powered)
                            tries=$((tries + 1)); fix=$n
                            usay "a cable is in for $(((n - plug) * EVERY)) s and UDC $CTRL is '$st': re-armed (sys.usb.config none, then $CFG; $tries of 2 for this plug-in)$OFF"
                            act setprop sys.usb.config none
                            sleep 1
                            act setprop sys.usb.config "$CFG"
                            sleep 2
                            b=$(usb_read "$UDC_FILE"); [ "$b" != none ] || b=""
                            if [ -n "$BOUND" ] && [ -z "$b" ]; then
                                if udc_put "$CTRL"; then usay "UDC $CTRL written after the re-arm$OFF"
                                else usay "UDC $CTRL could not be written after the re-arm"; fi
                            fi ;;
                    esac
                fi
            fi
            sleep $EVERY; n=$((n + 1))
        done
        usay "ended (control/usb-watch.off)"
        exit 0 ;;
    --inner)
        # Inside the new mount namespace (unshare -m), still root. The stage
        # becomes /data: nothing else of One UI's /data exists in here.
        [ -z "$T" ] || exit 3
        # Every step says so in xnuhost's log before it is taken, and however
        # this shell ends before xnuhost starts, its last line says with what
        # status and in which step. (The S24 Ultra, 2026-11-11, 0.4.77 to
        # 0.4.80: it ended here without a word, in the check that control/ is
        # read-only. That check wrote with ":", a special builtin, and
        # Android's sh ends the script when a special builtin's redirection
        # fails; with 2>/dev/null before it, silently. The check succeeded,
        # and that was the end. Never ":" with a redirection: "true".)
        AT="start"
        at() { AT=$*; echo "oneios inner: $(date +%T) $*"; }
        trap 'echo "oneios inner: $(date +%T) ended with status $? in step: $AT"' EXIT
        die_inner() { echo "oneios inner: $*"; exit 70; }
        echo $$ 2>/dev/null > "$CTL/inner.pid"
        at "pid $$, mount namespace $(readlink /proc/$$/ns/mnt 2>/dev/null)"
        R_XNUHOST=$(conf "$STAGE/runtime.conf" xnuhost)
        [ -n "$BB" ] && [ -x "$BB" ] || die_inner "no busybox"
        [ "$(readlink /proc/$$/ns/mnt)" != "$(readlink /proc/1/ns/mnt)" ] || die_inner "still in init's mount namespace"
        # The root manager's busybox is in One UI's /data (/data/adb), which the bind below hides: the rest of
        # this namespace's setup runs a copy in the way back's control folder (root's, read-only in here), as
        # OneOS's guest_prepare.sh copies busybox into the guest's /data. It keeps the name busybox (a
        # multi-call busybox goes by its name).
        at "copying busybox to $CTL/busybox"
        cp "$BB" "$CTL/busybox" && chmod 0700 "$CTL/busybox" || die_inner "could not copy $BB to $CTL/busybox"
        at "making the mounts private"
        "$BB" mount --make-rprivate / || die_inner "could not make the mounts private"
        at "binding the stage over /data"
        "$BB" mount --bind "$STAGE" /data || die_inner "could not bind the stage over /data"
        BB=/data/control/busybox
        at "running busybox from the stage"
        "$BB" true 2>/dev/null || die_inner "busybox does not run from the stage ($BB)"
        # Read-only in here: the runtime and the image (as staged), and what
        # the way back runs and reads (its scripts, its control folder).
        for d in runtime image control bin oneios_switch.sh oneios_return.sh; do
            [ -e "/data/$d" ] || continue
            at "making /data/$d read-only"
            "$BB" mount --bind "/data/$d" "/data/$d" && "$BB" mount -o remount,bind,ro "/data/$d" ||
                die_inner "could not make /data/$d read-only"
        done
        at "checking that /data/control is read-only"
        if true 2>/dev/null > /data/control/.w; then
            rm -f /data/control/.w
            die_inner "the way back's control folder is writable in the session's namespace"
        fi
        # The guard this session rests on: One UI's data is not reachable here.
        at "checking that One UI's /data is not visible"
        [ ! -e /data/system ] && [ ! -e /data/misc ] && [ ! -e /data/user ] && [ -f /data/runtime.conf ] ||
            die_inner "One UI's /data is still visible in the session's namespace"
        cd /data || die_inner "cd /data"
        at "session folders"
        mkdir -p /data/data /data/session/tmp && chmod 0700 /data/data /data/session/tmp || die_inner "could not make /data/data"
        # (xnuhost's pid file is written by the shell that becomes xnuhost, at the end: the switch waits for it.)
        # A cgroup of its own for xnuhost and everything it starts (cgroup v2,
        # no controller needed): the watcher, the key readers and the return
        # are in the root group, never in the guest's, and the return ends the
        # whole group at once (cgroup.kill) wherever a task of it went. Without
        # cgroup v2 (its root has cgroup.controllers) the return has the mount
        # namespace alone, as before.
        at "the session's cgroup"
        CG=/sys/fs/cgroup/oneios_session
        if [ -f /sys/fs/cgroup/cgroup.controllers ] && mkdir -p "$CG" 2>/dev/null && echo $$ > "$CG/cgroup.procs" 2>/dev/null; then
            echo "oneios inner: cgroup $CG"
        else
            echo "oneios inner: no cgroup of its own ($CG); the return ends the session by its mount namespace"
        fi
        # Every core for the guest's vCPUs. Android's v1 cpusets (/dev/cpuset) still
        # apply under the v2 group above: this shell kept the cpuset of the root
        # shell the app started (top-app while the app was in front, background
        # once it was not), and background and system-background allow the
        # A520s only, where xnuhost's cpu-pin cannot put a vCPU on the X4 or an
        # A720 (sched_setaffinity is limited to the cpuset). The cpuset's root has
        # every core, as for the watcher and the key readers (out_of_the_way).
        # xnuhost logs the cpuset it runs in ("cpu: xnuhost's cpuset ...").
        if [ -w /dev/cpuset/cgroup.procs ] && echo $$ > /dev/cpuset/cgroup.procs 2>/dev/null; then
            echo "oneios inner: cpuset / (cpus $(cat /dev/cpuset/cpus 2>/dev/null))"
        else
            echo "oneios inner: cpuset kept: $(cat /proc/$$/cpuset 2>/dev/null) (cpus $(grep Cpus_allowed_list /proc/$$/status 2>/dev/null | awk '{print $2}'))"
        fi
        # The switch is exempt from the OOM killer (-1000) and xnuhost would
        # inherit that: with memory gone the kernel would then end One UI's
        # daemons, or panic. The guest is what goes first; its end is a return.
        echo 500 > /proc/$$/oom_score_adj 2>/dev/null
        export ONEIOS_SESSION_ABI=$ABI ONEIOS_MODE=takeover ONEIOS_RUNTIME=/data/runtime ONEIOS_IMAGE=/data/image \
               ONEIOS_DATA=/data/data ONEIOS_SESSION=/data/session TMPDIR=/data/session/tmp
        # The app's versionCode (root's switch verb sets it) for xnuhost's versions: line; a number or nothing.
        case "${ONEIOS_APP_VERSION_CODE:-}" in ''|*[!0-9]*) unset ONEIOS_APP_VERSION_CODE ;; *) export ONEIOS_APP_VERSION_CODE ;; esac
        unset BB ONEIOS_APP ONEIOS_TEST_ROOT
        # A switch that gave up on this shell meanwhile is returning to One
        # UI: nothing starts under it. "running" is not giving up: the outer
        # switch writes it as soon as it reads xnuhost's pid (up to the app 0.5.80 this
        # shell wrote it earlier, and the phone hit that race on 2026-11-11).
        ST=$(cat /data/control/state 2>/dev/null)
        case "$ST" in
            starting|running) ;;
            *) die_inner "the switch is no longer starting (state '$ST'): xnuhost is not started" ;;
        esac
        set -- "/data/runtime/$R_XNUHOST" --session-abi $ABI --mode takeover \
            --runtime /data/runtime --image /data/image --data /data/data --session /data/session
        # The Android takeover (session-mode=takeover, recorded by the switch in control/base/mode): the same command
        # line and one setting more. The default session's command line is unchanged.
        [ "$(cat /data/control/base/mode 2>/dev/null)" = takeover ] && set -- "$@" --set session-mode=takeover
        # xnuhost runs as this shell's child, and this shell waits for it: however xnuhost ends, its exit code or
        # the signal that killed it goes to its log and to session/xnuhost.exit, which the watcher copies into
        # return.log. (Up to the app 0.5.80 this shell exec'd xnuhost and nothing waited for it: on the phone, 2026-11-23
        # 19:06, xnuhost ended without a line and nothing said how.) The shell that writes the pid file execs
        # xnuhost, so the file holds xnuhost's own pid, as the switch, the watcher and the return expect. It runs in
        # the foreground: a shell without job control starts a background (&) command with SIGINT and SIGQUIT
        # ignored, and xnuhost takes SIGINT as a return and SIGQUIT as its dump.
        AT="running /data/runtime/$R_XNUHOST"
        echo "oneios inner: $(date '+%F %T') starting /data/runtime/$R_XNUHOST"
        /system/bin/sh -c 'echo $$ > /data/session/xnuhost.pid || exit 70; exec "$@"' xnuhost "$@"
        rc=$?
        XP=$(cat /data/session/xnuhost.pid 2>/dev/null)
        how=$(end_how "$rc")
        echo "oneios inner: $(date '+%F %T') xnuhost ${XP:-?} ended: $how"
        echo "pid ${XP:-?} $(end_record "$rc")" 2>/dev/null > /data/session/xnuhost.exit
        AT="xnuhost ended"
        exit "$rc"
        ;;
    --stop-loop)
        # One UI's zygote must stay stopped: other services restart it
        # (onrestart), and a zygote that starts would bring system_server back
        # next to the guest. oneios_return.sh ends this loop before it starts
        # One UI ($CTL/stop-loop.off, then the waiter's pid, then the loop's).
        # It keeps zygote, zygote_secondary, the boot animation and, in the
        # Android takeover, every service of control/base/stopped stopped.
        # $2: the staged xnuhost, whose --prop-wait (OneiOS docs/booter.md
        # 2.9d) sleeps on init's property area until one of their init.svc
        # properties says running, 60 s at most: no process at all while
        # nothing starts. Until 2026-11-23 this was three getprop every 0.2 s,
        # 15 processes a second for the whole session (OneiOS's
        # docs/plan-ios-first-session.md, stage 2a). A runtime without
        # --prop-wait (it answers 2): one look a second. Each stop it makes is
        # a line of control/stop-loop.log.
        W="${2:-}"
        L="$CTL/stop-loop.log"
        lsay() { echo "$(date '+%F %T') stop loop: $*" >> "$L"; }
        names="zygote zygote_secondary bootanim"
        for s in $(cat "$CTL/base/stopped" 2>/dev/null); do
            case " $TAKEOVER_STOPPABLE " in *" $s "*) names="$names $s" ;; esac
        done
        wants=""
        for s in $names; do wants="$wants init.svc.$s=running"; done
        stops=0
        stop_running() {
            for s in $names; do
                [ "$(getprop "init.svc.$s")" = running ] || continue
                setprop ctl.stop "$s"
                stops=$((stops + 1))
                lsay "$s was running: ctl.stop $s"
            done
        }
        if [ -n "$W" ] && [ -f "$W" ] && [ -x "$W" ]; then
            "$W" --prop-wait 0 $wants >/dev/null 2>&1 </dev/null
            rc=$?
            [ $rc -le 1 ] || { lsay "$W --prop-wait answered $rc (a runtime from before it)"; W=""; }
        else
            W=""
        fi
        if [ -n "$W" ]; then lsay "keeps $names stopped: waits on their init.svc properties ($W --prop-wait, 60 s a wait)"
        else lsay "keeps $names stopped: one look a second (getprop)"; fi
        while [ ! -e "$CTL/stop-loop.off" ]; do
            stop_running
            if [ -n "$W" ]; then
                "$W" --prop-wait 60 $wants >/dev/null 2>&1 </dev/null &
                echo $! > "$CTL/stop-loop.wait.pid"
                wait $!
                rc=$?
                [ ! -e "$CTL/stop-loop.off" ] || break
                case $rc in
                    # One started: init takes a moment to act on a stop, so one look after 0.2 s, not a busy loop.
                    0) sleep 0.2 ;;
                    1) ;;
                    *) lsay "the wait ended with $rc: one look a second from here"; W="" ;;
                esac
            else
                sleep 1
            fi
        done
        lsay "ends: $stops stops in the session"
        exit 0
        ;;
    --takeover-stops)
        # The tests' way in (against a fake phone): the Android takeover's stops as the switch makes them, after its
        # preflight's choice of the list (which refuses as the preflight refuses).
        [ -n "$T" ] || { echo "$MODE: for the tests only"; exit 2; }
        mkdir -p "$CTL/base"
        takeover_stops_pick
        takeover_stops
        exit 0 ;;
    --feed)
        # One UI's system_server opened Samsung's software watchdog (100 s) and
        # kicked it; stopped, it leaves the timer running and the phone panics
        # ("Software Watchdog Timer expired 100s", oneos_switch.sh [4b/6]). "V"
        # is the magic close where the driver allows it, and a kick otherwise.
        [ -z "$T" ] || exit 3
        L="$CTL/watchdog_feeder.log"
        was=""
        while [ ! -e "$CTL/feeder.off" ]; do
            now=""
            for wd in /dev/watchdog /dev/softdog $(cat "$CTL/softdog_nodes" 2>/dev/null); do
                [ -c "$wd" ] || continue
                if e=$(printf V 2>&1 > "$wd"); then now="$now $wd:written"; else now="$now $wd:refused($e)"; fi
            done
            for w in /sys/class/watchdog/watchdog*; do
                [ "$(cat "$w/state" 2>/dev/null)" = active ] || continue
                case "$(cat "$w/identity" 2>/dev/null)" in *[Ss]oft*) ;; *) continue ;; esac
                d=/dev/${w##*/}
                [ -c "$d" ] || continue
                if e=$(printf V 2>&1 > "$d"); then now="$now $d:kicked"; else now="$now $d:refused($e)"; fi
            done
            [ "$now" = "$was" ] || { echo "$(date +%T)$now" >> "$L"; was=$now; }
            sleep 2
        done
        exit 0
        ;;
    --bootui)
        # The boot screen's status line (bootui_begin starts this beside the
        # renderer): once a second, the furthest boot stage in what xnuhost's
        # log gained, a kernel panic, or why xnuhost ended. It hands the screen
        # to the display helper when the guest's picture is up (display_up)
        # and leaves when a return begins: the return ends the screen. It
        # reads the log and control/, and writes only $BOOTUI.
        gen=$(cat "$BOOTUI/generation" 2>/dev/null)
        [ -n "$gen" ] || exit 0
        echo $$ > "$BOOTUI/feeder.pid"
        live() { [ "$(cat "$BOOTUI/generation" 2>/dev/null)" = "$gen" ] && [ ! -e "$BOOTUI/stop" ]; }
        show() {
            [ "$1" = "$shown" ] && return 0
            shown=$1
            screen status "$1"
            echo "$(date '+%F %T') boot screen: $(plain "$1")"
        }
        # The bar ("progress": the step, of how many, how far 0.000..1.000)
        # and the next step's name ("next"), each written when it changes.
        screen_bar() { # <step> <first start: 1 or 0>
            [ "$1" = "$step" ] || {
                [ "$1" -ge "${step:-0}" ] || frac=0
                step=$1 since=$t
            }
            frac=$(progress_of "$step" $((t - since)) "$2" "$frac")
            screen_put progress "$step $BOOT_STEPS $frac" "$was_progress" && was_progress="$step $BOOT_STEPS $frac"
            nx=$(next_name "$step" "$2")
            screen_put next "$nx" "$was_next" && was_next=$nx
        }
        screen_put() { # <file> <text> <what it says now>: a file of the screen, whole or not at all
            [ "$2" != "$3" ] || return 1
            # (Not once a return began: it takes the bar away.)
            case "$(cat "$CTL/state" 2>/dev/null)" in starting|running) ;; *) return 1 ;; esac
            printf '%s\n' "$2" > "$BOOTUI/.$1.tmp" 2>/dev/null && mv -f "$BOOTUI/.$1.tmp" "$BOOTUI/$1" 2>/dev/null
            return 0
        }
        # A first start is expected while there is no Data store yet (xnuhost
        # makes data.img on the first start); the log's own lines decide.
        first=0
        [ -s "$STAGE/data/data.img" ] || first=1
        off=0 st=0 shown="" panic="" t=0 drawn=0 native=0 step="" since=0 frac=0 was_progress="" was_next=""
        screen_bar 1 $first
        while live; do
            state=$(cat "$CTL/state" 2>/dev/null)
            case "$state" in starting|running) ;; *) break ;; esac
            if display_up; then
                echo "$(date '+%F %T') boot screen: the guest's picture is on the display helper's layer; the boot screen ends"
                bootui oneos_boot_stop
                break
            fi
            # The display helper, once it connects in a takeover, sets the
            # display's projection to the panel's own mode and leaves it so
            # (One UI's resolution setting may be smaller). The boot screen
            # then draws for that size: the renderer reads this file.
            if [ $native = 0 ] && grep -q 'oneios-display: display projection set to the active mode' "$CTL/display.log" 2>/dev/null; then
                native=1
                bootui oneos_boot_write native 1
                echo "$(date '+%F %T') boot screen: the display helper set the projection to the panel's mode; drawing at that size"
            fi
            # A renderer that never posted a frame is not retried for the whole session.
            [ -s "$BOOTUI/ready" ] && drawn=1
            if [ $drawn = 0 ] && [ $t -ge 30 ]; then
                echo "$(date '+%F %T') boot screen: the renderer posted no frame in 30 s (log $BOOTUI/renderer.log); the boot screen ends"
                bootui oneos_boot_stop
                break
            fi
            # What the log gained since the last look, with 511 bytes before it
            # (a marker cut in two by the last read; a stage is only ever raised).
            size=$(stat -c %s "$SESSION/xnuhost.log" 2>/dev/null)
            set -- $(awk -v s="${size:-0}" -v o="$off" 'BEGIN {
                s += 0; o += 0; if (s < o) o = 0
                if (s == o) { print "-", o; exit }
                f = (o > 511) ? o - 510 : 1
                e = (s - f + 1 > 1048576) ? f + 1048575 : s
                print f, e }')
            if [ "$1" != - ]; then
                out=$(log_scan "$1" "$st")
                off=$2
                n=$(printf '%s\n' "$out" | sed -n 's/^S //p' | head -n 1)
                case "$n" in ''|*[!0-9]*) ;; *) st=$n ;; esac
                printf '%s\n' "$out" | grep -q -x B && panic=""
                if printf '%s\n' "$out" | grep -q -x F; then first=1
                # (Past the Data steps without one: a later boot.)
                elif [ "$st" -ge 7 ] && [ "${step:-0}" -lt 5 ]; then first=0; fi
                found=$(printf '%s\n' "$out" | sed -n 's/^P //p' | head -n 1)
                [ -z "$found" ] || panic=$found
            else
                off=$2
            fi
            gone=0
            if [ "$state" = running ]; then
                xp=$(cat "$CTL/xnuhost.pid" 2>/dev/null)
                [ -n "$xp" ] && [ "$(readlink "$P/$xp/ns/mnt" 2>/dev/null)" = "$(cat "$CTL/mntns" 2>/dev/null)" ] || gone=1
            fi
            # The bar stays where the boot stopped; the watcher takes the way
            # back when xnuhost ends.
            if [ $gone = 1 ]; then show "$(why_ended)"; screen_put next "Going back to One UI" "$was_next" && was_next="Going back to One UI"
            elif [ -n "$panic" ]; then show "Kernel panic: $panic"; screen_put next "" "$was_next" && was_next=""
            elif [ "$st" -gt 0 ]; then show "$(stage_name "$st")"; screen_bar "$st" $first
            else screen_bar 1 $first
            fi
            sleep 1; t=$((t + 1))
        done
        exit 0
        ;;
    --keys)
        # Volume Up + Volume Down held 3 s, from one key device's events.
        # getevent only reads: it never grabs (EVIOCGRAB), so the guest still
        # gets the keys, and it is a One UI-side process the guest cannot
        # block. It only asks for the return (ask_return). A later session
        # (another token) ends this reader, with its getevent, on its next event.
        [ -n "$2" ] && [ -n "$3" ] || exit 3
        kd=$2 tok=$3
        KS="$CTL/keys"
        reader_start
        getevent -lq "$kd" 2>/dev/null | while read -r typ code val rest; do
            [ "$(cat "$KS/session" 2>/dev/null)" = "$tok" ] || reader_end
            case "$code" in KEY_VOLUMEUP) k=up ;; KEY_VOLUMEDOWN) k=down ;; *) continue ;; esac
            # DOWN and UP only (getevent -l's names, or the bare values). The
            # auto-repeat of a held key (REPEAT, on a device with EV_REP) is
            # not a release: taken as one, a hold would never reach 3 s.
            case "$val" in DOWN|00000001) v=DOWN ;; UP|00000000) v=UP ;; *) continue ;; esac
            echo "$v" > "$KS/$k"
            # Both down: a timer looks at the two keys every 0.25 s for 3 s.
            # The S24 Ultra's volume keys are one rocker, and pressing both of
            # its ends chatters: one end lifts for a moment and comes back
            # (session of 2026-11-12: 6 key events in 3 s, no 3 s without a
            # release). A release of 0.5 s or more ends the hold; a shorter one
            # does not. The timer reads only the two keys' files: there is no
            # shared token for the other reader to clear (two readers that both
            # see the chord start a timer each, and ask_return asks once).
            if [ "$v" = DOWN ] && [ "$(cat "$KS/up" 2>/dev/null)" = DOWN ] && [ "$(cat "$KS/down" 2>/dev/null)" = DOWN ]; then
                ( n=0 miss=0
                  while [ $n -lt 12 ] && [ $miss -lt 2 ]; do
                      sleep 0.25; n=$((n + 1))
                      if [ "$(cat "$KS/up" 2>/dev/null)" = DOWN ] && [ "$(cat "$KS/down" 2>/dev/null)" = DOWN ]; then miss=0; else miss=$((miss + 1)); fi
                  done
                  [ $miss -lt 2 ] && [ "$(cat "$KS/session" 2>/dev/null)" = "$tok" ] &&
                      ask_return "keys: Volume Up + Volume Down held 3 s" ) &
            fi
        done
        exit 0
        ;;
    --keys-poll)
        # The same chord without the event stream. "getevent -pl DEVICE" asks
        # the device for its keys' state (EVIOCGKEY) and marks a key that is
        # down with "*". A program that grabs a device (EVIOCGRAB) takes its
        # events from every other reader, the one above included, but not this
        # state: so the chord works even if xnuhost grabs the keys, which its
        # contract forbids (OneiOS docs/agents.md). Twice a second; seven
        # samples with both keys down are 3 s. One sample without them in
        # between does not end the hold (the rocker's chatter, see --keys); two
        # in a row do.
        [ -n "$2" ] && [ -n "$3" ] || exit 3
        tok=$2
        shift 2
        KS="$CTL/keys"
        reader_start
        TMO=""
        command -v timeout >/dev/null 2>&1 && TMO="timeout 2"
        n=0 miss=0
        while [ "$(cat "$KS/session" 2>/dev/null)" = "$tok" ]; do
            st=$(for kd in "$@"; do $TMO getevent -pl "$kd" 2>/dev/null; done)
            held=0
            case "$st" in *"KEY_VOLUMEUP*"*) case "$st" in *"KEY_VOLUMEDOWN*"*) held=1 ;; esac ;; esac
            if [ $held = 1 ]; then n=$((n + 1)); miss=0
            elif [ $n -gt 0 ]; then miss=$((miss + 1)); [ $miss -lt 2 ] || { n=0; miss=0; }
            fi
            if [ $n -ge 7 ]; then
                n=0 miss=0
                ask_return "keys: Volume Up + Volume Down down for 3 s (polled)"
            fi
            sleep 0.5
        done
        exit 0
        ;;
    --watch)
        # The way back, armed before One UI's zygote stops. A One UI-side
        # process: init's mount namespace, its own session (setsid), the root
        # cgroup, never the OOM killer's, so nothing the guest does can stop
        # or freeze it. It returns to One UI when: the switch did not get as
        # far as starting xnuhost (60 s), xnuhost ended, a return was asked
        # ($SESSION/return.request: the volume keys, the guest, adb), or the
        # guest never said it is up ($SESSION/ready) within ONEIOS_RETURN_MAX
        # seconds of its start (600; 0 = no limit).
        echo $$ > "$CTL/watcher.pid"
        out_of_the_way
        MAX="${ONEIOS_RETURN_MAX:-600}"
        case "$MAX" in ''|*[!0-9]*) MAX=600 ;; esac
        awake() { echo oneios_session 2>/dev/null > "$T/sys/power/wake_lock"; }
        SCREEN=""
        go() {
            echo "$(date '+%F %T') watcher: $*; returning to One UI"
            # The boot screen, while it is still up, says so (and why, in
            # $SCREEN) until the return ends it.
            screen title 'Returning to One UI'
            [ -z "$SCREEN" ] || screen status "$SCREEN"
            # (No bar on the way back: what it counted was the boot.)
            rm -f "$BOOTUI/progress" "$BOOTUI/next"
            # The guest's picture goes first: nothing of the return waits for it.
            end_display
            # Not exec: a return script that cannot be run (gone, damaged) or
            # that ends with an error must still end in One UI, by the reboot.
            # A return that hangs is its own guard's to end (oneios_return.sh).
            $SH "$STAGE/oneios_return.sh" watcher
            rc=$?
            [ $rc = 0 ] && exit 0
            hard_reboot oneios-watcher-failsafe "oneios_return.sh ended with $rc in state '$(cat "$CTL/state" 2>/dev/null)'"
        }
        t=0
        while [ "$(cat "$CTL/state" 2>/dev/null)" = starting ]; do
            [ -e "$SESSION/return.request" ] && SCREEN="A return to One UI was asked for" && go "return asked before xnuhost started ($(head -c 200 "$SESSION/return.request" 2>/dev/null))"
            [ $t -lt 60 ] || { SCREEN="iOS did not start within 60 s"; go "the switch did not start xnuhost within 60 s"; }
            sleep 1; t=$((t + 1))
        done
        case "$(cat "$CTL/state" 2>/dev/null)" in
            running) ;;
            # A return someone else started (the app, adb, the key readers): theirs.
            returning|returned) echo "$(date '+%F %T') watcher: a return is under way or done; nothing to do"; exit 0 ;;
            # (The switch wrote why on the boot screen.)
            *) go "the switch ended in state '$(cat "$CTL/state" 2>/dev/null)'" ;;
        esac
        pid=$(cat "$CTL/xnuhost.pid" 2>/dev/null)
        ns=$(cat "$CTL/mntns" 2>/dev/null)
        t=0
        while :; do
            # A return someone else started (the app, adb, the key readers) is
            # theirs, with its own guard. Any other state, an unreadable one
            # included, is still this session.
            case "$(cat "$CTL/state" 2>/dev/null)" in
                returning|returned) echo "$(date '+%F %T') watcher: a return is under way or done; nothing to do"; exit 0 ;;
            esac
            [ -e "$SESSION/return.request" ] && SCREEN="A return to One UI was asked for" && go "return asked ($(head -c 200 "$SESSION/return.request" 2>/dev/null))"
            if ! { [ -n "$pid" ] && [ "$(readlink "$P/$pid/ns/mnt" 2>/dev/null)" = "$ns" ]; }; then
                # How it ended (the inner shell's record) and what the host saw of it, before anything else.
                how=$(end_of "$pid")
                death_notes "$pid"
                SCREEN=$(why_ended)
                [ "$SCREEN" != "xnuhost ended" ] || [ "$how" = "how is not recorded" ] || SCREEN="xnuhost ended: $how"
                go "xnuhost $pid ended: $how (last log lines: $(tail -n 3 "$SESSION/xnuhost.log" 2>/dev/null | tr '\n' '|' | cut -c1-300))"
            fi
            if [ "$MAX" -gt 0 ] && [ ! -e "$SESSION/ready" ] && [ $t -ge "$MAX" ]; then
                SCREEN="iOS did not come up within ${MAX} s"
                go "the guest did not report ready within ${MAX}s"
            fi
            # Nothing else keeps the phone awake with One UI's framework gone:
            # the session's wakelock again every 10 s, whoever released it.
            [ $((t % 10)) = 0 ] && awake
            sleep 1; t=$((t + 1))
        done
        ;;
    session|--check) ;;
    *) echo "usage: oneios_switch.sh [--check]"; exit 3 ;;
esac

# --- PREFLIGHT ------------------------------------------------------------
# Every refusal comes before the first change to the phone, so a refused
# switch leaves One UI exactly as it was.
if [ -n "$T" ]; then
    stage_checks
    echo "TEST ROOT: stage checks passed (runtime $R_VERSION, xnuhost $R_XNUHOST, image $I_VERSION $I_BUILD format $I_FORMAT); nothing was started"
    exit 0
fi
[ "$(id -u 2>/dev/null)" = 0 ] || refuse "not running as root"
command -v sha256sum >/dev/null 2>&1 || refuse "no sha256sum"

# Mainly tested on: the Galaxy S24 Ultra (docs/oneios.md, "Scope"): e3q on an
# SM8650, the SM-S928 models. The owner (2026-11-16): another phone may try it,
# told what to expect; nothing here refuses one any more. The Galaxy A56
# (SM-A566 models, a56x on an s5e8855; docs/oneios.md, "Galaxy A56") has a path
# of its own: iOS 16.5 (20F66), OneiOS's galaxy-a56 host row. Untested on an A56.
P_MODEL=$(getprop ro.product.model)
P_DEVICE=$(getprop ro.product.device)
P_SOC=$(getprop ro.soc.model)
S24U=0
case "$P_MODEL" in SM-S928*) ;; *) S24U=1 ;; esac
[ "$P_DEVICE" = e3q ] && [ "$P_SOC" = SM8650 ] || S24U=1
A56=0
case "$P_MODEL" in SM-A566*) A56=1 ;; esac
[ "$P_DEVICE" = a56x ] && [ "$P_SOC" = s5e8855 ] || A56=0
if [ "$A56" = 1 ]; then
    echo "Galaxy A56 path: this phone is ${P_MODEL} (a56x, s5e8855): iOS 16.5 (20F66), OneiOS's galaxy-a56 host row."
    echo "WARNING: this path has not run on a Galaxy A56 yet (untested). iOS 16.5 reached the lock screen there"
    echo "WARNING: only in another fork, and touch did not work there. A return that fails restarts the phone"
    echo "WARNING: into One UI. Going on because you asked it to."
elif [ "$S24U" = 1 ]; then
    echo "WARNING: OneiOS is mainly tested and working on the Galaxy S24 Ultra 5G (an e3q on an SM8650;"
    echo "WARNING: the SM-S928 models). This phone is ${P_MODEL:-unknown} (${P_DEVICE:-?}, ${P_SOC:-?}): on it the"
    echo "WARNING: code may be unstable, miss pieces, or not come back to One UI. Samsung devices are the"
    echo "WARNING: ones it is written for. Going on because you asked it to."
    # What is known of a phone another fork measured (OneiOS docs/s26.md).
    case "$P_MODEL:$P_DEVICE:$P_SOC" in
        SM-S948*:*|*:m3q:*)
            echo "WARNING: Galaxy S26 Ultra (SM8850): iOS ran there only in another fork's root-only test, never"
            echo "WARNING: through this switch. Its watchdog hand-off and the return to One UI in place are not"
            echo "WARNING: verified on it (a magic close of /dev/watchdog was refused, EBUSY). A return that fails"
            echo "WARNING: restarts the phone into One UI." ;;
    esac
fi

# The stage first: without a runtime that has xnuhost, that one line is the answer.
stage_checks
# The Galaxy A56: OneiOS has a GPU path there only for iOS 16.5 (20F66, its galaxy-a56
# host row: gpu=2d). Another image (iOS 27, 24A446) is warned, never refused (the
# owner's 2026-11-16 rule). Untested on an A56.
if [ "$A56" = 1 ] && [ "$I_BUILD" != 20F66 ]; then
    echo "WARNING: the staged image is iOS ${I_VERSION:-?} (${I_BUILD:-?}), not iOS 16.5 (20F66): iOS 27 has no GPU"
    echo "WARNING: path on the Galaxy A56, so it may not draw. Make iOS image on this phone makes iOS 16.5."
fi

# Root tools: the root manager's own busybox and resetprop, as oneos_switch.sh.
BB=""
for c in /data/adb/ksu/bin/busybox /data/adb/ap/bin/busybox /data/adb/magisk/busybox; do
    [ -x "$c" ] && { BB=$c; break; }
done
RP=""
for c in /data/adb/ksu/bin/resetprop /data/adb/ap/bin/resetprop /debug_ramdisk/resetprop /sbin/resetprop; do
    [ -x "$c" ] && { RP=$c; break; }
done
[ -n "$BB" ] || refuse "no busybox at the root manager's paths (/data/adb/ksu/bin, /data/adb/ap/bin, /data/adb/magisk)"
APPLETS=" $("$BB" --list 2>/dev/null | tr '\n' ' ') "
missing=""
# No reboot applet: KernelSU's busybox has none, and oneos_switch.sh asks for none. The way back's reboot is
# init's (sys.powerctl), then Android's own reboot, then busybox's where it has one, then sysrq (hard_reboot).
for a in sh mount umount unshare nsenter setsid awk grep sed; do
    case "$APPLETS" in *" $a "*) ;; *) missing="$missing $a" ;; esac
done
[ -z "$missing" ] || refuse "$BB lacks the applets:$missing"
[ -n "$RP" ] || refuse "no resetprop at the root manager's paths: One UI's boot counters could not be put back on the return"

# init's mount namespace: the session's own namespace is made from it, and the
# return checks init's mount table.
SELF_NS=$(readlink /proc/$$/ns/mnt 2>/dev/null)
INIT_NS=$(readlink /proc/1/ns/mnt 2>/dev/null)
if [ -z "$SELF_NS" ] || [ "$SELF_NS" != "$INIT_NS" ]; then
    if [ "$APP" != 1 ] && [ -z "$ONEIOS_NS_REENTERED" ]; then
        echo "Not in init's mount namespace: running again in init's"
        export ONEIOS_NS_REENTERED=1
        exec "$BB" nsenter -t 1 -m -- /system/bin/sh "$SELF" "$@"
    fi
    refuse "not in init's mount namespace (this shell: ${SELF_NS:-unreadable}, init: ${INIT_NS:-unreadable})"
fi

# One UI must be whole and no session of either kind may be up.
[ "$(getprop sys.boot_completed)" = 1 ] || refuse "One UI has not finished starting"
[ "$(getprop init.svc.zygote)" = running ] && pidof system_server >/dev/null 2>&1 ||
    refuse "One UI's framework is not running (another session, or a return in progress): restart the phone first"
pidof surfaceflinger >/dev/null 2>&1 || refuse "One UI's surfaceflinger is not running"
left=$(awk -v s="$STAGE" -v o="$ANDROID_STAGE" '$5 == s || index($5, s "/") == 1 || index($5, o "/") == 1 { print $5 }' /proc/self/mountinfo | head -n 3 | tr '\n' ' ')
[ -z "$left" ] || refuse "mounted under a stage ($left): a session is running or never returned; restart the phone first"
if [ "$(cat "$CTL/boot" 2>/dev/null)" = "$(boot_id)" ]; then
    case "$(cat "$CTL/state" 2>/dev/null)" in
        starting|running|returning) refuse "an iOS session of this boot is still open ($(cat "$CTL/state")): restart the phone first" ;;
    esac
fi
op=$(cat "$CTL/xnuhost.pid" 2>/dev/null)
on=$(cat "$CTL/mntns" 2>/dev/null)
[ -z "$op" ] || [ -z "$on" ] || [ "$(readlink "/proc/$op/ns/mnt" 2>/dev/null)" != "$on" ] ||
    refuse "xnuhost of an earlier session is still running (pid $op): restart the phone first"
old=""
for p in $(head -n 3 /sys/fs/cgroup/oneios_session/cgroup.procs 2>/dev/null); do [ -d "/proc/$p" ] && old="$old$p "; done
[ -z "$old" ] || refuse "processes of an earlier iOS session are still running (cgroup oneios_session: $old): restart the phone first"

# The ways back: the volume keys, and enough battery to get there.
command -v getevent >/dev/null 2>&1 || refuse "no getevent: Volume Up + Volume Down could not return to One UI"
command -v ps >/dev/null 2>&1 || refuse "no ps: the key readers could not be told apart"
KEYS=$(getevent -pl 2>/dev/null)
case "$KEYS" in *KEY_VOLUMEUP*) ;; *) refuse "no Volume Up key found (getevent)" ;; esac
case "$KEYS" in *KEY_VOLUMEDOWN*) ;; *) refuse "no Volume Down key found (getevent)" ;; esac
KDEVS=$(printf '%s\n' "$KEYS" | awk '/^add device/ { dev = $NF } /KEY_VOLUME(UP|DOWN)/ { print dev }' | sort -u)
BAT=/sys/class/power_supply/battery
CAP=$(cat $BAT/capacity 2>/dev/null)
BST=$(cat $BAT/status 2>/dev/null)
BTEMP=$(cat $BAT/temp 2>/dev/null)
case "$CAP" in ''|*[!0-9]*) refuse "battery not readable" ;; esac
case "${BTEMP#-}" in ''|*[!0-9]*) refuse "battery temperature not readable" ;; esac
[ "$CAP" -ge 30 ] || [ "$BST" = Charging ] || [ "$BST" = Full ] || refuse "battery at $CAP% and not charging"
[ "$BTEMP" -lt 420 ] || refuse "battery too warm ($((BTEMP / 10)) C)"
# Room for the guest's data store to grow (2 GiB).
set -- $(stat -f -c '%a %S' /data 2>/dev/null)
[ $# -eq 2 ] && [ "$(awk -v a="$1" -v s="$2" 'BEGIN { print (a * s >= 2147483648) ? 1 : 0 }')" = 1 ] ||
    refuse "less than 2 GiB free on /data"
[ -w /sys/power/wake_lock ] || refuse "no /sys/power/wake_lock: the phone would sleep with One UI's framework stopped"
# The app's experimental tick (root's switch verb passes it on).
[ "$APP" != 1 ] || [ "${ONEIOS_ACK_EXPERIMENTAL:-0}" = 1 ] || refuse "the experimental tick was not given"
# The session mode ("THE SESSION MODE" above): hosted adds nothing here; takeover asks the staged xnuhost.
session_mode_pick
[ "$SMODE" = hosted ] || takeover_checks "$X"

echo "Preflight passed (runtime $R_VERSION, xnuhost $R_XNUHOST, image iOS $I_VERSION $I_BUILD format $I_FORMAT, busybox $BB, SELinux $(getenforce 2>/dev/null))"
if [ "$MODE" = --check ]; then
    echo "PREFLIGHT OK"
    exit 0
fi

# --- THE SESSION -----------------------------------------------------------
# From here on something changes. Out of the launching app's cgroup and away
# from the OOM killer first: ActivityManager kills an app's whole cgroup when
# the app dies, and a switch killed half way leaves One UI stopped.
echo $$ > /sys/fs/cgroup/cgroup.procs 2>/dev/null
echo -1000 > /proc/$$/oom_score_adj 2>/dev/null
trap '' HUP PIPE
export BB

echo "=== [1/5] $(date +%T) Session folder and baseline ==="
# The last session's log is kept (five of them); its folder is this session's.
mkdir -p "$STAGE/logs" && chmod 0700 "$STAGE/logs"
[ -s "$SESSION/xnuhost.log" ] && mv -f "$SESSION/xnuhost.log" "$STAGE/logs/xnuhost-$(date +%s).log"
ls -1t "$STAGE/logs"/xnuhost-*.log 2>/dev/null | tail -n +6 | while read -r old; do rm -f "$old"; done
[ ! -L "$SESSION" ] || refuse "$SESSION is a symlink"
[ ! -L "$CTL" ] || refuse "$CTL is a symlink"
rm -rf "$SESSION" "$CTL"
mkdir -p "$CTL/base" "$CTL/keys" "$SESSION/tmp" "$STAGE/data" && chown -R 0:0 "$SESSION" "$CTL" && chmod -R go-rwx "$SESSION" "$CTL" &&
    chmod 0700 "$STAGE/data" || refuse "could not make $SESSION"
true > "$SESSION/xnuhost.log"
boot_id > "$CTL/boot"
echo starting > "$CTL/state"
# What the in-place return compares against (oneios_return.sh), read while
# One UI is whole. Nothing here is changed by the session; the return only
# proves that.
B="$CTL/base"
boot_id > "$B/boot_id"
getenforce > "$B/selinux" 2>&1
getprop > "$B/props"
for n in vold keystore2 surfaceflinger servicemanager; do echo "$n $(pidof $n 2>/dev/null | tr ' ' ',')"; done > "$B/pids"
case "$(settings get global wifi_on 2>/dev/null)" in 1|2) echo 1 ;; *) echo 0 ;; esac > "$B/wifi_on"
awk '{ print $5 }' /proc/1/mountinfo | sort > "$B/mounts"
# The panel's brightness as One UI has it: xnuhost's brightness bridge writes
# the backlight node, and a session it cannot end itself (SIGKILL) would leave
# iOS's last level, possibly the dimmest. The return writes these back.
for bl in "$T"/sys/class/backlight/*/brightness; do
    [ -f "$bl" ] && echo "${bl#"$T"} $(cat "$bl" 2>/dev/null)"
done > "$B/backlight" 2>/dev/null
clocks_save
# The USB gadget and adbd as One UI has them (control/base/usb), for the
# session's USB watcher and the return.
usb_save
# The Android takeover: its mark for --inner (xnuhost's session-mode=takeover), the CPU cap and the return. Only in
# that mode: a hosted session has no such file.
if [ "$SMODE" = takeover ]; then
    echo takeover > "$B/mode" || refuse "could not make $B/mode (the session mode)"
fi
echo "Baseline: boot $(cat "$B/boot_id"), SELinux $(cat "$B/selinux"), $(tr '\n' ' ' < "$B/pids")wifi $(cat "$B/wifi_on")"

echo "=== [2/5] $(date +%T) Arming the way back ==="
# Before the stop: the watcher returns to One UI by itself if this script
# does not get as far as a running xnuhost. The watcher, the key readers and
# the poll are started here, in init's mount namespace, before xnuhost's
# namespace and cgroup exist: they are never part of either.
# Each of them writes its own pid (watcher.pid, keys/pids) once it runs.
"$BB" setsid $SH "$SELF" --watch </dev/null >>"$STAGE/return.log" 2>&1 &
KTOK="$$.$(date +%s)"
echo "$KTOK" > "$CTL/keys/session"
readers=1
for kd in $KDEVS; do
    "$BB" setsid $SH "$SELF" --keys "$kd" "$KTOK" </dev/null >/dev/null 2>&1 &
    readers=$((readers + 1))
done
"$BB" setsid $SH "$SELF" --keys-poll "$KTOK" $KDEVS </dev/null >/dev/null 2>&1 &
# With One UI's power manager gone nothing would keep the phone awake.
echo oneios_session > /sys/power/wake_lock 2>/dev/null
# One UI is stopped only with the way back in place: the watcher, a reader
# for every key device and the poll running, the wakelock held. Otherwise this
# is where the switch ends, with One UI untouched (the return only ends the
# helpers: there is no stop mark yet).
n=0
while [ $n -lt 25 ]; do
    [ -s "$CTL/watcher.pid" ] && [ "$(grep -c . "$CTL/keys/pids" 2>/dev/null)" = "$readers" ] && break
    sleep 0.2; n=$((n + 1))
done
armed=""
kill -0 "$(cat "$CTL/watcher.pid" 2>/dev/null)" 2>/dev/null || armed="the watcher is not running"
[ "$(grep -c . "$CTL/keys/pids" 2>/dev/null)" = "$readers" ] || armed="${armed:+$armed, }$(grep -c . "$CTL/keys/pids" 2>/dev/null) of $readers key readers started"
for p in $(cat "$CTL/keys/pids" 2>/dev/null); do
    kill -0 "$p" 2>/dev/null || armed="${armed:+$armed, }key reader $p is not running"
done
case " $(cat /sys/power/wake_lock 2>/dev/null) " in
    *" oneios_session "*) ;;
    *) armed="${armed:+$armed, }the wakelock oneios_session is not held" ;;
esac
if [ -n "$armed" ]; then
    echo "!!! The way back to One UI could not be armed ($armed): One UI was not stopped, nothing was changed"
    echo failed > "$CTL/state"
    $SH "$STAGE/oneios_return.sh" switch-not-armed
    exit 4
fi
echo "Return to One UI: hold Volume Up + Volume Down for 3 s (key devices: $(echo $KDEVS)); watcher $(cat "$CTL/watcher.pid"), key readers $(tr '\n' ' ' < "$CTL/keys/pids")"
echo "If that does nothing: hold Power + Volume Down until the phone restarts (about 7 s). It restarts into One UI."
[ "$SMODE" = hosted ] || echo "Android takeover: the same ways back, in place first; a restart into One UI only where the in-place return cannot put One UI back (a failed check, a stopped service that does not come back, or the takeover's CPU cap that cannot be written back)"

# A return asked while the switch runs (the watcher, the key readers, the app,
# adb) wins. The switch and the return meet at one lock, $CTL/stop.lock: the
# switch holds it from its last look at the state to the end of the stop, the
# return takes it and never gives it back. So a return either sees the stop
# done (the "stopped" mark) and restores One UI in place, or the switch never
# stops anything (2026-11-12 11:04: a return during step 3 found no mark yet,
# tidied up and ended; the switch then stopped the framework, xnuhost did not
# start, and nothing returned).
return_asked() { # true when a return was asked or has begun
    [ -e "$SESSION/return.request" ] && return 0
    [ "$(cat "$CTL/state" 2>/dev/null)" = starting ] || return 0
    return 1
}
end_for_return() { # <step>: the switch ends; the return (already under way, or the watcher's) restores
    echo "A return to One UI was asked before $1 ($(head -c 200 "$SESSION/return.request" 2>/dev/null)): the switch ends here; the return restores One UI"
    exit 4
}
return_asked && end_for_return "One UI's framework was stopped"

echo "=== [3/5] $(date +%T) Stopping the One UI framework ==="
# The boot screen first, so that it is up when One UI's windows go.
bootui_begin
# The watchdog device(s) One UI's system_server keeps open, before it stops
# (oneos_switch.sh [4b/6]: recorded for the feeder). One `ls -l` of the fd
# folder, not one readlink process per fd: system_server holds about 1500 fds,
# and the readlink loop took 48 s on the S24 Ultra (2026-11-23 18:19), so the
# switch did not start xnuhost within the watcher's 60 s.
for p in $(pidof system_server); do
    ls -l "/proc/$p/fd/"
done 2>/dev/null | grep -oE '/dev/(watchdog|softdog)[^ ]*' | sort -u > "$CTL/softdog_nodes"
# The stop lock (above): 15 s at most; a return holds it for good.
n=0
until mkdir "$CTL/stop.lock" 2>/dev/null; do
    [ $n -lt 75 ] || end_for_return "One UI's framework was stopped (a return holds the stop lock)"
    sleep 0.2; n=$((n + 1))
done
return_asked && end_for_return "One UI's framework was stopped"
# The shmem THP mode: xnuhost's 2 MiB host pages map the guest's RAM with
# MADV_HUGEPAGE, which shmem honours only in the advise mode (OneiOS 8a9caf3,
# docs/booter.md 2.6c). One UI never advises, so advise changes nothing for it.
# Written here, under the stop lock and just before the stop mark, so that a
# switch that ends earlier (not armed, a return asked) never changed it; the
# bare mode is saved first (the node prints "always within_size advise [never]
# deny force"; the whole line written back is EINVAL: Gate A, 2026-11-16), and
# both returns, the early one too, write it back (YMGPwcca/OneOS 403d8b4).
SHMEM_EN="$T/sys/kernel/mm/transparent_hugepage/shmem_enabled"
if [ -f "$SHMEM_EN" ]; then
    shmem_mode=$(awk 'NF == 1 && $1 ~ /^[a-z_]+$/ { print $1; exit }
        { for (i = 1; i <= NF; i++) if ($i ~ /^\[[a-z_]+\]$/) { print substr($i, 2, length($i) - 2); exit } }' "$SHMEM_EN" 2>/dev/null)
    case "$shmem_mode" in
        always|within_size|advise|never|deny|force)
            if printf '%s\n' "$shmem_mode" 2>/dev/null > "$B/shmem_enabled.tmp" && mv -f "$B/shmem_enabled.tmp" "$B/shmem_enabled"; then
                [ "$shmem_mode" = advise ] || { echo advise 2>/dev/null > "$SHMEM_EN" && echo "shmem_enabled: $shmem_mode -> advise"; }
            else
                echo "shmem_enabled: $shmem_mode could not be saved: left as it is"
            fi ;;
        *) echo "shmem_enabled: no mode read: left as it is" ;;
    esac
fi
# From here One UI's framework is down: the return starts it again. Without
# this mark the return only tidies up (a switch that ended before the stop).
echo "$(date +%s)" > "$CTL/stopped"
setprop ctl.stop zygote
[ -n "$(getprop init.svc.zygote_secondary)" ] && setprop ctl.stop zygote_secondary
n=0
while [ $n -lt 50 ] && pidof system_server >/dev/null 2>&1; do sleep 0.2; n=$((n + 1)); done
kill -9 $(pidof system_server) 2>/dev/null
kill -9 $(pidof zygote64) $(pidof zygote) 2>/dev/null
rmdir "$CTL/stop.lock" 2>/dev/null
# system_server is gone, so nothing of One UI writes the clock caps any more.
clocks_tops
# The Android takeover's CPU cap: from the hardware's top just written, lower only when the cell is hot (50 C up).
# Not a condition of the session: without it the session runs as a hosted one does (the kernel's trips, xnuhost's
# thermal step); the return writes One UI's clocks back either way.
if [ "$SMODE" = takeover ]; then
    rm -f "$CTL/cpu-cap.pid"
    "$BB" setsid /system/bin/sh "$SELF" --cpu-cap </dev/null >>"$CTL/cpu-cap.log" 2>&1 &
    n=0
    while [ $n -lt 10 ] && [ ! -s "$CTL/cpu-cap.pid" ]; do sleep 0.2; n=$((n + 1)); done
    if [ -s "$CTL/cpu-cap.pid" ]; then echo "CPU cap (Android takeover): pid $(cat "$CTL/cpu-cap.pid"), log $CTL/cpu-cap.log"
    else echo "CPU cap (Android takeover): did not start within 2 s (log $CTL/cpu-cap.log): the session goes on without it"; fi
    # Its stops (takeover_stops): recorded in control/base/stopped before each, so the stop loop below keeps them
    # stopped and every return starts them again; before xnuhost, so that ram=auto gives the guest what they held.
    takeover_stops
fi
"$BB" setsid /system/bin/sh "$SELF" --stop-loop "$X" </dev/null >/dev/null 2>&1 &
echo $! > "$CTL/stop-loop.pid"
# UsbDeviceManager went with system_server: from here the USB watcher keeps
# adb on the gadget, across unplug and replug (control/usb.log).
if [ "$(conf "$CTL/base/usb" adb)" = 1 ]; then
    "$BB" setsid /system/bin/sh "$SELF" --usb-watch </dev/null >>"$CTL/usb.log" 2>&1 &
    echo "USB watcher: started (log $CTL/usb.log)"
else
    echo "USB watcher: not started (USB debugging was off in One UI)"
fi
# Samsung's software watchdog: its magic close now, then the feeder.
for wd in /dev/watchdog /dev/softdog $(cat "$CTL/softdog_nodes"); do
    [ -c "$wd" ] || continue
    if e=$(printf V 2>&1 > "$wd"); then echo "Softdog: $wd closed with V"; else echo "Softdog: $wd not written ($e)"; fi
done
"$BB" setsid /system/bin/sh "$SELF" --feed </dev/null >/dev/null 2>&1 &
echo $! > "$CTL/feeder.pid"
echo "One UI's zygote: $(getprop init.svc.zygote); system_server: $(pidof system_server 2>/dev/null || echo gone); surfaceflinger $(pidof surfaceflinger) kept"

# From here a return finds the mark and restores One UI in place.
return_asked && end_for_return "xnuhost was started"

echo "=== [4/5] $(date +%T) Starting xnuhost ==="
screen status "Starting xnuhost"
# A new mount namespace made from init's; --inner binds the stage over /data
# there and execs xnuhost, so the pid it writes is xnuhost's own.
"$BB" setsid "$BB" unshare -m /system/bin/sh "$SELF" --inner </dev/null >>"$SESSION/xnuhost.log" 2>&1 &
# Waited for by its progress, not for a fixed time: until it wrote the pid, for
# as long as that shell runs (control/inner.pid), 30 s at most. A shell that
# ended is not waited for; its trace in the log says where it stopped.
n=0
while [ $n -lt 150 ] && [ ! -s "$SESSION/xnuhost.pid" ]; do
    if [ $n -ge 10 ]; then
        ip=$(cat "$CTL/inner.pid" 2>/dev/null)
        [ -n "$ip" ] && kill -0 "$ip" 2>/dev/null || break
    fi
    sleep 0.2; n=$((n + 1))
done
XP=$(cat "$SESSION/xnuhost.pid" 2>/dev/null)
XNS=$(readlink "/proc/$XP/ns/mnt" 2>/dev/null)
if [ -z "$XP" ] || [ -z "$XNS" ] || [ "$XNS" = "$INIT_NS" ]; then
    echo "!!! xnuhost did not start after $((n / 5)) s (pid '${XP}', namespace '${XNS}'); the last lines of $SESSION/xnuhost.log: $(tail -n 6 "$SESSION/xnuhost.log" | tr '\n' '|')"
    screen status "xnuhost did not start: $(grep . "$SESSION/xnuhost.log" 2>/dev/null | tail -n 1)"
    echo failed > "$CTL/state"
    # One UI's framework is down: never left so. The return, from here (the
    # watcher returns too on this state, or may have ended already; the return
    # takes one caller at a time).
    $SH "$STAGE/oneios_return.sh" switch-failed
    exit 4
fi
# The switch's own record of the two, where the guest cannot write: what the
# watcher and the return go by.
echo "$XP" > "$CTL/xnuhost.pid"
echo "$XNS" > "$CTL/mntns"
echo running > "$CTL/state"
echo "xnuhost: pid $XP in mount namespace $XNS, log $SESSION/xnuhost.log"

# The guest's screen: the runtime's display helper, when it carries one. It
# runs here, on One UI's side (it needs surfaceflinger's binder and the
# framework's classes, which xnuhost's namespace is not for), as root, from
# the runtime the preflight hashed. It waits for xnuhost's display.sock, shows
# the frames on a top layer and leaves when the socket closes. It is in the
# session's cgroup, so the return ends it with the rest, and by its pid
# (control/, where the guest cannot write; its log is there too). Nothing
# waits for it: without it the session runs with a dark screen.
DH="$STAGE/runtime/bin/oneios-display"
if [ -f "$DH" ] && [ ! -L "$DH" ] && [ -x "$DH" ] && root_only "$DH"; then
    # This session's log only: the boot screen's hand-off (display_up) reads its markers, and a
    # "first frame posted" of an earlier session must not end this session's boot screen early.
    [ -f "$CTL/display.log" ] && mv -f "$CTL/display.log" "$CTL/display.log.1" 2>/dev/null
    "$BB" setsid "$DH" --session "$SESSION" --takeover --wait 60 </dev/null >>"$CTL/display.log" 2>&1 &
    DP=$!
    echo "$DP" > "$CTL/display.pid"
    echo 0 2>/dev/null > "/proc/$DP/oom_score_adj"
    echo "$DP" 2>/dev/null > /sys/fs/cgroup/oneios_session/cgroup.procs
    echo "Display helper: pid $DP, log $CTL/display.log"
else
    echo "Display helper: the runtime has none (bin/oneios-display); the guest's screen is not shown"
fi

echo "=== [5/5] $(date +%T) Session running ==="
echo "Auto-return to One UI: when xnuhost ends, on $SESSION/return.request, or without $SESSION/ready after ${ONEIOS_RETURN_MAX:-600}s"
echo "=== ONEIOS SESSION LAUNCHED ==="
