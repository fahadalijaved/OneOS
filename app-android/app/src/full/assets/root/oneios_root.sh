#!/system/bin/sh
# OneiOS root script: every change the OneOS app makes as root for the iOS 27
# (OneiOS) system is one of the verbs below, and nothing else (docs/oneios.md).
#
# Like oneos_root.sh, the app never runs this file from its own storage. Its
# launcher (OneiosRoot.kt, a fixed text) runs only $STAGE/bin/oneios_root.sh,
# root's and writable by root only, and only with the SHA-256 pinned in the
# app's BuildConfig; status, begin and remove may first install it there.
# Arguments are fixed words, decimal numbers, lowercase hex and plain relative
# paths only.
#
#   status                      read only: what is staged, the session, whether
#                               a switch would start (oneios_switch.sh --check)
#   begin <runtime|image>       start staging one of them into <kind>.new
#   receive <runtime|image> <path> <bytes> <sha256> <mode>
#                               stdin: exactly <bytes> bytes of <path>
#                               (mode 0644 or 0755)
#   script <name> <bytes> <sha256>
#                               stdin: oneios_switch.sh or oneios_return.sh
#   finish runtime <files> <version> <sessionAbi> <xnuhost> <imageFormats> <placeholder>
#   finish image <files> <format> <version> <build>
#                               <files> received files (the manifest included)
#                               become $STAGE/<kind>; the facts the app read
#                               from the checked manifest go to <kind>.conf
#   switch <versionCode> <ack>  the preflight, then the session, detached, in
#                               init's mount namespace (ack 1 = the
#                               experimental tick)
#   return                      Back to One UI: runs oneios_return.sh, detached,
#                               in init's mount namespace. With no open session
#                               that script does nothing
#   remove                      delete the stage (never during a session)
#   check <id>                  one hardware check (docs/oneios.md, "Hardware
#                               checks"): a phone tool of the staged runtime's
#                               bin/, run beside One UI with a time limit; a
#                               tool that has not finished is ended and what it
#                               changed is put back. Never during a session
#   uncheck <id>                the put-back step of <id> alone, for a check
#                               whose root command the app had to end
#   checkfile <id>              the picture a camera check wrote, in base64
#   logs                        read only: the session logs in the stage (this
#                               session's or the last one's xnuhost.log, the
#                               five earlier ones, the switch's, the return's
#                               and the helpers'), each with its size, the time
#                               of its last line and its last lines
#   logfile <id> <end> <bytes>  read only: up to <bytes> bytes (1 MiB at most)
#                               of one of them, whole lines, ending at byte
#                               <end> (0 = the end of the file)
#   tool <work|read>            OneiOS's Rust tools of the staged runtime
#                               (bin/oneios-tool serve) for one flow of the
#                               app, on the app's pipe: one request a line
#                               in, progress and results out, until the app
#                               closes the pipe. work: the Make iOS image
#                               steps, never during a session; read: also
#                               during one (the tool refuses its heavy
#                               requests then)
#   untool                      the backstop: ends every process of the
#                               staged bin/oneios-tool serve (SIGTERM, 2 s,
#                               SIGKILL)
#
# Writes: only under $STAGE (/data/local/tmp/oneios), which is root's, mode
# 0700, and separate from OneOS's Android stage. Nothing of One UI's data, no
# property, no SELinux change. switch starts oneios_switch.sh; what that does
# is written at its top. The one exception is check's put-back step: the
# panel's backlight level and the light sensor's enable file, written back to
# the values read before the tool ran.
umask 077
T="${ONEIOS_TEST_ROOT:-}"
if [ -n "$T" ]; then
    [ "$(id -u)" != 0 ] || { echo "@@REFUSED ONEIOS_TEST_ROOT is for tests, never as root"; exit 3; }
fi
STAGE="$T/data/local/tmp/oneios"
OWNER=0
[ -z "$T" ] || OWNER=$(id -u)
EXIT_REFUSED=2
EXIT_USAGE=3
EXIT_FAILED=4
# One file of a runtime package or an image set: 16 GiB at most.
RECEIVE_MAX=17179869184
SCRIPT_MAX=1048576

say() { echo "$*"; }
refuse() { echo "@@REFUSED $*"; exit $EXIT_REFUSED; }
usage() { echo "@@REFUSED usage: $*"; exit $EXIT_USAGE; }
die() { echo "@@FAILED $*"; exit $EXIT_FAILED; }
is_dec() { case "$1" in ''|*[!0-9]*) return 1 ;; esac; [ ${#1} -le 18 ]; }
is_hex64() { case "$1" in *[!0-9a-f]*) return 1 ;; esac; [ ${#1} -eq 64 ]; }
# A relative path of plain segments: no leading slash or dot, no "..", no "//".
is_path() {
    case "$1" in
        ''|/*|*/|.*|*/.*|*..*|*//*|*[!A-Za-z0-9._+/-]*) return 1 ;;
    esac
    [ ${#1} -le 200 ]
}
is_word() { case "$1" in ''|.*|*[!A-Za-z0-9._-]*) return 1 ;; esac; [ ${#1} -le 40 ]; }
sha() { sha256sum "$1" 2>/dev/null | cut -d' ' -f1; }
mine() {
    [ ! -L "$1" ] && [ -e "$1" ] || return 1
    case "$(stat -c '%u %A' "$1" 2>/dev/null)" in
        "$OWNER "?????w*|"$OWNER "????????w*) return 1 ;;
        "$OWNER "*) return 0 ;;
    esac
    return 1
}
own() { # <path> <mode>
    { [ -n "$T" ] || chown 0:0 "$1"; } && chmod "$2" "$1"
}
boot_id() { cat "$T/proc/sys/kernel/random/boot_id" 2>/dev/null; }
conf() { sed -n "s/^$2=//p" "$1" 2>/dev/null | head -n 1; }
find_bb() {
    BB=""
    for c in /data/adb/ksu/bin/busybox /data/adb/ap/bin/busybox /data/adb/magisk/busybox; do
        [ -x "$T$c" ] && { BB=$T$c; break; }
    done
}
# A session of this boot that has not returned, or an xnuhost still alive in
# the namespace the switch recorded.
session_open() {
    s="$STAGE/control"
    if [ "$(cat "$s/boot" 2>/dev/null)" = "$(boot_id)" ]; then
        case "$(cat "$s/state" 2>/dev/null)" in starting|running|returning) return 0 ;; esac
    fi
    p=$(cat "$s/xnuhost.pid" 2>/dev/null)
    n=$(cat "$s/mntns" 2>/dev/null)
    [ -n "$p" ] && [ -n "$n" ] && [ "$(readlink "$T/proc/$p/ns/mnt" 2>/dev/null)" = "$n" ]
}
stage_ok() {
    [ -d "$STAGE" ] && mine "$STAGE" || refuse "$STAGE is missing or not root's"
}
kind_ok() { case "$1" in runtime|image) ;; *) usage "kind '$1' is not runtime or image" ;; esac; }
manifest_name() { case "$1" in runtime) echo runtime.json ;; image) echo manifest.json ;; esac; }

do_status() {
    [ $# -eq 0 ] || usage "status"
    if [ ! -d "$STAGE" ]; then
        say "@@RESULT stage none"
        say "@@OK status"
        return
    fi
    say "@@RESULT stage present"
    rc="$STAGE/runtime.conf"
    if [ -f "$rc" ] && mine "$rc" && [ -d "$STAGE/runtime" ]; then
        say "@@RESULT runtime $(conf "$rc" version) $(conf "$rc" session_abi) $(conf "$rc" xnuhost) $(conf "$rc" image_formats) $(conf "$rc" placeholder)"
    else
        say "@@RESULT runtime none"
    fi
    ic="$STAGE/image.conf"
    if [ -f "$ic" ] && mine "$ic" && [ -d "$STAGE/image" ]; then
        b=$(conf "$ic" build)
        say "@@RESULT image $(conf "$ic" format) $(conf "$ic" version) ${b:-unknown} $(conf "$ic" bytes)"
    else
        say "@@RESULT image none"
    fi
    st=$(cat "$STAGE/control/state" 2>/dev/null)
    if session_open; then say "@@RESULT session open ${st:-running}"; else say "@@RESULT session none ${st:-never}"; fi
    o=$(head -n 1 "$STAGE/return.outcome" 2>/dev/null | cut -c1-200)
    case "$o" in inplace\ *|failsafe\ *|reboot\ *) say "@@RESULT outcome $o" ;; *) say "@@RESULT outcome none" ;; esac
    # Would a switch start now? The session script's own preflight, read only.
    if [ -f "$STAGE/oneios_switch.sh" ] && mine "$STAGE/oneios_switch.sh"; then
        if [ -n "$T" ]; then
            out=$(ONEIOS_TEST_ROOT="$T" sh "$STAGE/oneios_switch.sh" --check 2>&1)
        else
            find_bb
            if [ -n "$BB" ]; then
                out=$(ONEIOS_APP=1 ONEIOS_ACK_EXPERIMENTAL=1 "$BB" nsenter -t 1 -m -- /system/bin/sh "$STAGE/oneios_switch.sh" --check 2>&1 </dev/null)
            else
                out="PREFLIGHT REFUSED: no busybox at the root manager's paths"
            fi
        fi
        why=$(printf '%s\n' "$out" | sed -n 's/^PREFLIGHT REFUSED: //p' | head -n 1 | cut -c1-400)
        if [ -n "$why" ]; then say "@@RESULT ready 0 $why"
        elif printf '%s\n' "$out" | grep -q -e '^PREFLIGHT OK$' -e '^TEST ROOT: stage checks passed'; then say "@@RESULT ready 1"
        else say "@@RESULT ready 0 the preflight gave no answer: $(printf '%s\n' "$out" | tail -n 1 | cut -c1-200)"
        fi
    else
        say "@@RESULT ready 0 OneiOS is not set up on this phone yet"
    fi
    say "@@OK status"
}

do_begin() {
    [ $# -eq 1 ] || usage "begin <runtime|image>"
    kind_ok "$1"
    stage_ok
    session_open && refuse "an iOS session is running: return to One UI first"
    n="$STAGE/$1.new"
    [ ! -L "$n" ] || refuse "$n is a link"
    rm -rf "$n" "$STAGE/$1.new.sha256" "$STAGE/$1.new.ids" || die "could not clear $n"
    mkdir "$n" && own "$n" 0700 || die "could not make $n"
    true > "$STAGE/$1.new.sha256" && true > "$STAGE/$1.new.ids" && own "$STAGE/$1.new.sha256" 0600 && own "$STAGE/$1.new.ids" 0600 ||
        die "could not start the list"
    say "@@OK begin $1"
}

# Reads exactly <bytes> bytes of stdin into <file>.part, checks size and
# SHA-256, and only then gives it its name.
#
# The copy is dd in 1 MiB blocks where dd can count in bytes: toybox's head -c
# copies 4 KiB at a time, two system calls for every 4 KiB of a 10 GiB file.
# toybox's dd counts the bytes it read (iflag=count_bytes); GNU's and
# busybox's also need fullblock, or a short read from the pipe counts as a
# whole block, and toybox's refuses that word. Which one this dd is is found
# by copying two bytes of three; a dd that does neither leaves head -c, as
# before. The size is checked after the copy in any case. The SHA-256 is of
# the file as it is on the disk, read again after the last byte.
copy_bytes() { # <bytes>: stdin to stdout, exactly that many
    if [ "$(printf abc | dd bs=1M iflag=count_bytes,fullblock count=2 2>/dev/null)" = ab ]; then
        dd bs=1M iflag=count_bytes,fullblock count="$1" 2>/dev/null
    elif [ "$(printf abc | dd bs=1M iflag=count_bytes count=2 2>/dev/null)" = ab ]; then
        dd bs=1M iflag=count_bytes count="$1" 2>/dev/null
    else
        head -c "$1"
    fi
}
take() { # <file> <bytes> <sha256> <mode>
    f=$1
    rm -f "$f.part"
    copy_bytes "$2" > "$f.part" || { rm -f "$f.part"; die "could not write ${f##*/}"; }
    got=$(stat -c %s "$f.part" 2>/dev/null)
    [ "$got" = "$2" ] || { rm -f "$f.part"; refuse "${f##*/}: $got of $2 bytes arrived"; }
    [ "$(sha "$f.part")" = "$3" ] || { rm -f "$f.part"; refuse "${f##*/} did not arrive intact (SHA-256 differs)"; }
    own "$f.part" "$4" && mv -f "$f.part" "$f" || { rm -f "$f.part"; die "could not place ${f##*/}"; }
}

do_receive() {
    [ $# -eq 5 ] || usage "receive <runtime|image> <path> <bytes> <sha256> <mode>"
    kind=$1 path=$2 bytes=$3 sum=$4 mode=$5
    kind_ok "$kind"
    is_path "$path" || usage "receive: path '$path'"
    is_dec "$bytes" || usage "receive: size '$bytes'"
    is_hex64 "$sum" || usage "receive: SHA-256"
    case "$mode" in 0644|0755) ;; *) usage "receive: mode '$mode'" ;; esac
    # Not the shell's own comparison: Android's sh (mksh) counts in 32 bits,
    # and a limit of 16 GiB read as 0 there, so every file was "too large".
    awk -v b="$bytes" -v m="$RECEIVE_MAX" 'BEGIN { exit !(b + 0 <= m + 0) }' || refuse "$path is too large"
    stage_ok
    session_open && refuse "an iOS session is running: return to One UI first"
    n="$STAGE/$kind.new"
    [ -d "$n" ] && mine "$n" || refuse "no $kind is being staged: begin first"
    awk -v p="$path" '$2 == p { f = 1 } END { exit !f }' "$STAGE/$kind.new.sha256" && refuse "$path was already received"
    # Room for the file and a little more.
    if [ -z "$T" ]; then
        set -- $(stat -f -c '%a %S' "$STAGE" 2>/dev/null)
        [ $# -eq 2 ] && [ "$(awk -v a="$1" -v s="$2" -v b="$bytes" 'BEGIN { print (a * s >= b + 268435456) ? 1 : 0 }')" = 1 ] ||
            refuse "not enough free space on /data for $path"
    fi
    # Its folders, each root's own, never through a link.
    d=$n
    rest=$path
    while [ "$rest" != "${rest#*/}" ]; do
        d="$d/${rest%%/*}"
        rest=${rest#*/}
        [ ! -L "$d" ] || refuse "$d is a link"
        [ -d "$d" ] || { mkdir "$d" && own "$d" 0700; } || die "could not make $d"
    done
    take "$n/$path" "$bytes" "$sum" "$mode"
    echo "$sum  $path" >> "$STAGE/$kind.new.sha256" &&
        echo "$(stat -c '%d:%i:%s:%Y' "$n/$path") $path" >> "$STAGE/$kind.new.ids" || die "could not record $path"
    say "@@OK receive $kind $path"
}

do_script() {
    [ $# -eq 3 ] || usage "script <name> <bytes> <sha256>"
    case "$1" in
        oneios_switch.sh|oneios_return.sh) to="$STAGE/$1"; mode=0700 ;;
        # OneOS's boot screen, which the switch shows until iOS draws (docs/oneios.md, "Boot screen"): in bin/,
        # which the session's namespace has read-only, like the two scripts.
        # (0644, the modes the Android guests' stage gives them: app_process loads the dex as it does there.)
        boot_status.sh|OneOSBootStatus.dex|oneos_boot_icon.png) to="$STAGE/bin/$1"; mode=0644 ;;
        *) usage "script: '$1'" ;;
    esac
    is_dec "$2" && [ "$2" -ge 1 ] && [ "$2" -le $SCRIPT_MAX ] || usage "script: size '$2'"
    is_hex64 "$3" || usage "script: SHA-256"
    stage_ok
    session_open && refuse "an iOS session is running: return to One UI first"
    [ -d "${to%/*}" ] && mine "${to%/*}" || refuse "${to%/*} is missing or not root's"
    [ ! -L "$to" ] || refuse "$to is a link"
    take "$to" "$2" "$3" "$mode"
    say "@@OK script $1"
}

do_finish() {
    [ $# -ge 1 ] || usage "finish <runtime|image> ..."
    kind=$1
    kind_ok "$kind"
    if [ "$kind" = runtime ]; then
        [ $# -eq 7 ] || usage "finish runtime <files> <version> <sessionAbi> <xnuhost> <imageFormats> <placeholder>"
        files=$2 version=$3 abi=$4 xnuhost=$5 formats=$6 placeholder=$7
        case "$placeholder" in 0|1) ;; *) usage "finish: placeholder '$placeholder'" ;; esac
        is_dec "$abi" || usage "finish: session ABI '$abi'"
        is_path "$xnuhost" || usage "finish: xnuhost '$xnuhost'"
        case "$formats" in ''|*[!0-9,]*|,*|*,|*,,*) usage "finish: image formats '$formats'" ;; esac
    else
        [ $# -eq 5 ] || usage "finish image <files> <format> <version> <build>"
        files=$2 format=$3 version=$4 build=$5
        is_dec "$format" || usage "finish: format '$format'"
        is_word "$build" || usage "finish: build '$build'"
    fi
    is_dec "$files" && [ "$files" -ge 2 ] || usage "finish: file count '$files'"
    is_word "$version" || usage "finish: version '$version'"
    stage_ok
    session_open && refuse "an iOS session is running: return to One UI first"
    n="$STAGE/$kind.new"
    sums="$STAGE/$kind.new.sha256"
    [ -d "$n" ] && mine "$n" && [ -f "$sums" ] && mine "$sums" || refuse "no $kind is being staged: begin first"
    got=$(awk 'END { print NR }' "$sums")
    [ "$got" = "$files" ] || refuse "$got of $files files were received"
    man=$(manifest_name "$kind")
    awk -v p="$man" '$2 == p { f = 1 } END { exit !f }' "$sums" || refuse "$man was not received"
    onDisk=$(cd "$n" && find . ! -type d | awk 'END { print NR }')
    [ "$onDisk" = "$files" ] || refuse "$kind.new holds $onDisk files, $files were received"
    if [ "$kind" = runtime ]; then
        awk -v p="$xnuhost" '$2 == p { f = 1 } END { exit !f }' "$sums" || refuse "the runtime has no $xnuhost"
        [ -x "$n/$xnuhost" ] || refuse "$xnuhost is not executable (mode 0755 in runtime.json)"
    fi
    c="$STAGE/$kind.conf.new"
    {
        echo "version=$version"
        if [ "$kind" = runtime ]; then
            echo "format=1"
            echo "session_abi=$abi"
            echo "xnuhost=$xnuhost"
            echo "image_formats=$formats"
            echo "placeholder=$placeholder"
        else
            echo "format=$format"
            echo "build=$build"
            echo "bytes=$(cd "$n" && find . -type f -exec stat -c %s {} + | awk '{ s += $1 } END { printf "%.0f", s }')"
        fi
        echo "staged=$(date +%s)"
    } > "$c" && own "$c" 0600 || die "could not write $kind.conf"
    # What was received is on the disk before it counts as staged: a switch may
    # end in a restart. Once, here, not after every file.
    [ -n "$T" ] || sync
    # The old one aside, the new one in, then the old one gone. The guest's
    # data ($STAGE/data) is not touched: a new runtime or image keeps it.
    old="$STAGE/$kind.old-$$"
    rm -f "$STAGE/$kind.conf"
    if [ -e "$STAGE/$kind" ] || [ -L "$STAGE/$kind" ]; then
        mv "$STAGE/$kind" "$old" || die "could not move the old $kind aside"
    fi
    mv "$n" "$STAGE/$kind" && mv -f "$sums" "$STAGE/$kind.sha256" && mv -f "$STAGE/$kind.new.ids" "$STAGE/$kind.ids" &&
        mv -f "$c" "$STAGE/$kind.conf" || die "could not put the new $kind in place"
    rm -rf "$old"
    say "@@OK finish $kind $version"
}

do_switch() {
    [ $# -eq 2 ] || usage "switch <versionCode> <ack>"
    is_dec "$1" || usage "switch versionCode '$1'"
    case "$2" in 1) ;; *) refuse "the experimental tick was not given" ;; esac
    stage_ok
    for f in oneios_switch.sh oneios_return.sh; do
        [ -f "$STAGE/$f" ] && mine "$STAGE/$f" || refuse "$f is not staged: set up again"
    done
    session_open && refuse "an iOS session is already running"
    if [ -n "$T" ]; then
        out=$(ONEIOS_TEST_ROOT="$T" sh "$STAGE/oneios_switch.sh" --check 2>&1)
        why=$(printf '%s\n' "$out" | sed -n 's/^PREFLIGHT REFUSED: //p' | head -n 1)
        [ -z "$why" ] || refuse "$why"
        refuse "test root: every stage check passed, nothing was started"
    fi
    find_bb
    [ -n "$BB" ] || refuse "no busybox at the root manager's paths"
    for a in sh nsenter setsid; do
        "$BB" --list 2>/dev/null | grep -q -x "$a" || refuse "$BB lacks $a"
    done
    # The preflight first, here, so its refusal is the app's answer: one line,
    # and nothing was changed.
    out=$(ONEIOS_APP=1 ONEIOS_ACK_EXPERIMENTAL=1 "$BB" nsenter -t 1 -m -- /system/bin/sh "$STAGE/oneios_switch.sh" --check 2>&1 </dev/null)
    why=$(printf '%s\n' "$out" | sed -n 's/^PREFLIGHT REFUSED: //p' | head -n 1 | cut -c1-400)
    [ -z "$why" ] || refuse "$why"
    printf '%s\n' "$out" | grep -q '^PREFLIGHT OK$' || refuse "the preflight gave no answer: $(printf '%s\n' "$out" | tail -n 1 | cut -c1-200)"
    echo "=== OneOS app switch $(date '+%F %T') epoch $(date +%s) versionCode $1 ===" >> "$STAGE/switch.log"
    # Out of the app's cgroup: the app dies when One UI's framework stops.
    echo $$ > /sys/fs/cgroup/cgroup.procs 2>/dev/null
    for v in $(env | sed -n 's/^\(ONEIOS_[A-Za-z0-9_]*\)=.*/\1/p'); do unset "$v"; done
    ONEIOS_APP=1 ONEIOS_ACK_EXPERIMENTAL=1 "$BB" nsenter -t 1 -m -- "$BB" setsid /system/bin/sh "$STAGE/oneios_switch.sh" \
        </dev/null >>"$STAGE/switch.log" 2>&1 &
    say "@@OK switch"
}

do_return() {
    [ $# -eq 0 ] || usage "return"
    stage_ok
    [ -f "$STAGE/oneios_return.sh" ] && mine "$STAGE/oneios_return.sh" || refuse "oneios_return.sh is not staged"
    session_open || { say "@@OK return nothing"; return; }
    [ -z "$T" ] || refuse "test root: a session is open, nothing was started"
    find_bb
    [ -n "$BB" ] || refuse "no busybox at the root manager's paths"
    echo $$ > /sys/fs/cgroup/cgroup.procs 2>/dev/null
    "$BB" nsenter -t 1 -m -- "$BB" setsid /system/bin/sh "$STAGE/oneios_return.sh" app </dev/null >>"$STAGE/return.log" 2>&1 &
    say "@@OK return started"
}

do_remove() {
    [ $# -eq 0 ] || usage "remove"
    [ -e "$STAGE" ] || [ -L "$STAGE" ] || { say "@@OK remove nothing"; return; }
    stage_ok
    session_open && refuse "an iOS session is running: return to One UI first"
    for m in "$T/proc/1/mountinfo" "$T/proc/self/mountinfo"; do
        [ -r "$m" ] || refuse "could not read $m"
        awk -v s="${STAGE#$T}" '$5 == s || index($5, s "/") == 1 { f = 1 } END { exit !f }' "$m" &&
            refuse "something is mounted in the stage: restart the phone first"
    done
    trash="$STAGE.trash-$(date +%s)"
    mv "$STAGE" "$trash" || die "could not move the stage aside"
    rm -rf "$trash" || die "could not delete $trash"
    say "@@OK remove"
}

# --- Hardware checks ----------------------------------------------------------
# OneiOS's phone tools (its runtime's bin/), each alone, as root, beside a
# running One UI. Nothing here stops or starts a service, a session or a
# process of One UI's; the tools' own READMEs in OneiOS say what each touches.
# The table is the same as OneiosChecks.ALL in the app (a test compares them).
CHECKS="$STAGE/checks"
check_cmd() { # <id>: TOOL (a file of the runtime's bin/), ARGS, LIMIT in seconds
    R="$STAGE/runtime/bin"
    case "$1" in
        cpu) TOOL=bridgectl ARGS="cpu" LIMIT=15 ;;
        gpu) TOOL=gpuctl ARGS="" LIMIT=120 ;;
        display) TOOL=displayctl ARGS="test" LIMIT=30 ;;
        haptic) TOOL=bridgectl ARGS="haptic 200 1000" LIMIT=10 ;;
        haptic-pattern) TOOL=bridgectl ARGS="haptic-pattern" LIMIT=15 ;;
        audio) TOOL=bridgectl ARGS="audio $R/oneios-audio" LIMIT=20 ;;
        bt) TOOL=bridgectl ARGS="bt" LIMIT=45 ;;
        brightness) TOOL=brightctl ARGS="info" LIMIT=10 ;;
        levels) TOOL=brightctl ARGS="levels" LIMIT=30 ;;
        als) TOOL=brightctl ARGS="als 10" LIMIT=25 ;;
        camera-list) TOOL=camctl ARGS="--backend ndk list" LIMIT=30 ;;
        camera) TOOL=camctl ARGS="--backend ndk --camera wide --frames 90 --out $CHECKS/camera.png capture" LIMIT=45 ;;
        camera-hal-list) TOOL=camctl ARGS="--backend hal list" LIMIT=30 ;;
        camera-hal) TOOL=camctl ARGS="-v --backend hal --camera wide --frames 90 --out $CHECKS/camera-hal.png capture" LIMIT=45 ;;
        *) usage "check: '$1' is not a hardware check" ;;
    esac
}
# Is <pid> still the tool this check started (not another process that got its number)?
check_is_tool() { cat "/proc/$1/cmdline" 2>/dev/null | grep -q -F "$STAGE/runtime/bin/$TOOL"; }
# What a check may change, read before its tool runs.
check_save() { # <id>
    true > "$CHECKS/saved.backlight"
    true > "$CHECKS/saved.als"
    case "$1" in
        levels)
            for d in "$T"/sys/class/backlight/*; do
                [ -r "$d/brightness" ] && echo "${d##*/} $(cat "$d/brightness")"
            done > "$CHECKS/saved.backlight" ;;
    esac
    case "$1" in
        brightness|levels|als)
            for d in "$T"/sys/class/input/event*; do
                [ "$(cat "$d/device/name" 2>/dev/null)" = als_rear ] && [ -r "$d/device/enable" ] && echo "${d##*/} $(cat "$d/device/enable")"
            done > "$CHECKS/saved.als" ;;
    esac
}
# The put-back step, for a tool that was ended before it could do its own: the
# tool and its helpers are gone, the backlight has the level and the light
# sensor the enable value read before the tool ran, the display test's layer
# and folder are removed.
check_restore() { # <id>
    if [ -z "$T" ]; then
        pkill -9 -f "$STAGE/runtime/bin/$TOOL" 2>/dev/null
        case "$1" in
            display) pkill -f OneiOSDisplay 2>/dev/null; pkill -9 -f "$STAGE/runtime/bin/oneios-display" 2>/dev/null ;;
            audio) pkill -9 -f "$STAGE/runtime/bin/oneios-audio" 2>/dev/null ;;
            camera*) pkill -9 -f "$STAGE/runtime/bin/oneios-camera" 2>/dev/null ;;
        esac
    fi
    # displayctl's own folder (its socket), left by a killed display test.
    for d in "$CHECKS"/displayctl.??????; do
        [ -d "$d" ] && [ ! -L "$d" ] && unlink "$d/display.sock" 2>/dev/null
        [ -d "$d" ] && [ ! -L "$d" ] && rmdir "$d" 2>/dev/null
    done
    if [ -f "$CHECKS/saved.backlight" ] && [ ! -L "$CHECKS/saved.backlight" ]; then
        while read -r name value; do
            case "$name" in ''|*[!A-Za-z0-9._-]*) continue ;; esac
            is_dec "$value" || continue
            n="$T/sys/class/backlight/$name/brightness"
            [ -w "$n" ] && echo "$value" > "$n" && say "@@INFO put back: backlight $name $value"
        done < "$CHECKS/saved.backlight"
    fi
    if [ -f "$CHECKS/saved.als" ] && [ ! -L "$CHECKS/saved.als" ]; then
        while read -r name value; do
            case "$name" in event[0-9]*) ;; *) continue ;; esac
            case "$name" in *[!a-z0-9]*) continue ;; esac
            case "$value" in 0|1) ;; *) continue ;; esac
            n="$T/sys/class/input/$name/device/enable"
            [ -w "$n" ] && echo "$value" > "$n" && say "@@INFO put back: light sensor $name enable $value"
        done < "$CHECKS/saved.als"
    fi
    true > "$CHECKS/saved.backlight"
    true > "$CHECKS/saved.als"
    [ ! -e "$CHECKS/timeout" ] || unlink "$CHECKS/timeout"
}
checks_dir() {
    [ ! -L "$CHECKS" ] || refuse "$CHECKS is a link"
    [ -d "$CHECKS" ] || mkdir "$CHECKS" || die "could not make $CHECKS"
    own "$CHECKS" 0700 || die "could not make $CHECKS root's"
}

do_check() {
    [ $# -eq 1 ] || usage "check <id>"
    id=$1
    check_cmd "$id"
    stage_ok
    session_open && refuse "an iOS session is running: the hardware checks only run beside One UI"
    [ -f "$STAGE/runtime.conf" ] && mine "$STAGE/runtime.conf" && [ -d "$STAGE/runtime" ] || refuse "no OneiOS runtime is staged: the checks are its tools"
    [ -n "$T" ] || [ "$(getprop sys.boot_completed 2>/dev/null)" = 1 ] || refuse "One UI is not fully up"
    bin="$STAGE/runtime/bin/$TOOL"
    if [ ! -f "$bin" ] || [ -L "$bin" ] || [ ! -x "$bin" ]; then
        say "@@RESULT check $id missing $TOOL"
        say "@@OK check $id"
        return
    fi
    # Only the file root hashed when the runtime was staged.
    want=$(awk -v p="bin/$TOOL" '$2 == p { print $1 }' "$STAGE/runtime.sha256" 2>/dev/null | head -n 1)
    [ -n "$want" ] && [ "$(sha "$bin")" = "$want" ] || refuse "bin/$TOOL is not the file that was staged: stage the runtime again"
    checks_dir
    limit=$LIMIT
    if [ -n "$T" ] && is_dec "${ONEIOS_CHECK_LIMIT:-x}"; then limit=$ONEIOS_CHECK_LIMIT; fi
    log="$CHECKS/$id.log"
    true > "$log"
    [ ! -e "$CHECKS/timeout" ] || unlink "$CHECKS/timeout"
    [ ! -e "$CHECKS/$id.png" ] || unlink "$CHECKS/$id.png"
    check_save "$id"
    # The tool, with nothing on its stdin and its temporary files in the stage.
    TMPDIR="$CHECKS" "$bin" $ARGS > "$log" 2>&1 < /dev/null &
    pid=$!
    # The time limit: SIGTERM (the tools put back what they changed on it), 2 s, SIGKILL.
    (
        sleep "$limit"
        check_is_tool "$pid" || exit 0
        true > "$CHECKS/timeout"
        kill -TERM "$pid" 2>/dev/null
        sleep 2
        check_is_tool "$pid" && kill -KILL "$pid" 2>/dev/null
    ) < /dev/null > /dev/null 2>&1 &
    dog=$!
    wait "$pid"
    rc=$?
    kill "$dog" 2>/dev/null
    timed=0
    [ ! -e "$CHECKS/timeout" ] || timed=1
    head -c 262144 "$log" | sed 's/^/| /'
    if [ $timed = 1 ]; then
        check_restore "$id"
        say "@@RESULT check $id timeout $limit"
    else
        say "@@RESULT check $id exit $rc"
    fi
    say "@@OK check $id"
}

do_uncheck() {
    [ $# -eq 1 ] || usage "uncheck <id>"
    check_cmd "$1"
    stage_ok
    session_open && refuse "an iOS session is running"
    [ -d "$CHECKS" ] && [ ! -L "$CHECKS" ] && mine "$CHECKS" || { say "@@OK uncheck nothing"; return; }
    check_restore "$1"
    say "@@OK uncheck $1"
}

do_checkfile() {
    [ $# -eq 1 ] || usage "checkfile <id>"
    case "$1" in camera|camera-hal) ;; *) usage "checkfile: '$1' has no picture" ;; esac
    stage_ok
    f="$CHECKS/$1.png"
    [ -d "$CHECKS" ] && [ ! -L "$CHECKS" ] && mine "$CHECKS" && [ -f "$f" ] && [ ! -L "$f" ] || refuse "the check left no picture"
    size=$(stat -c %s "$f" 2>/dev/null)
    is_dec "$size" && [ "$size" -ge 1 ] && [ "$size" -le 8388608 ] || refuse "the picture is empty or larger than 8 MiB"
    say "@@RESULT file $1 $size $(sha "$f")"
    base64 "$f" | sed 's/^/| /'
    say "@@OK checkfile $1"
}

# --- oneios-tool --------------------------------------------------------------
# OneiOS's Rust tools (its tools/oneios-tool, README "serve") from the staged
# runtime, for one flow of the app (docs/oneios.md, "oneios-tool in the app").
# Only the file root hashed when the runtime was staged runs; at nice 10, never
# realtime; its temporary files in $STAGE/tool. It takes the app's pipe as its
# stdin and stdout (exec: no shell stays between them), reads one request a
# line, and ends when the app closes the pipe or after its idle time; it leaves
# no process behind. `tool work` is refused during a session; `tool read` is
# not (the logs, the CPU), and the tool itself then refuses its heavy requests
# (`session`). Requests write only under the stage (the tool's --stage). `untool`
# ends what is left when the app could not end it (the app's own backstop, as
# `uncheck` is for the checks). What each request may write is in its README.
TOOL_BIN="$STAGE/runtime/bin/oneios-tool"
tool_pids() { # the processes of the staged bin/oneios-tool serve (by their command line) and theirs
    set --
    for p in /proc/[0-9]*; do
        { tr '\0' ' ' < "$p/cmdline"; } 2>/dev/null | grep -q -F "$TOOL_BIN serve" && set -- "$@" "${p#/proc/}"
    done
    [ $# -gt 0 ] || return 0
    # Their children, four levels down (the parent is field 4 of /proc/PID/stat; a name with spaces sits in (...)).
    all=" $* "
    for _ in 1 2 3 4; do
        for s in /proc/[0-9]*/stat; do
            { read -r l < "$s"; } 2>/dev/null || continue
            pid=${l%% *}
            set -- ${l##*) }
            case "$all" in *" $pid "*) ;; *" $2 "*) all="$all$pid " ;; esac
        done
    done
    echo $all
}

do_tool() {
    [ $# -eq 1 ] || usage "tool <work|read>"
    case "$1" in work|read) ;; *) usage "tool: '$1' is not work or read" ;; esac
    stage_ok
    if [ "$1" = work ]; then
        session_open && refuse "an iOS session is running: return to One UI first"
    fi
    [ -f "$STAGE/runtime.conf" ] && mine "$STAGE/runtime.conf" && [ -d "$STAGE/runtime" ] ||
        refuse "no OneiOS runtime is staged: oneios-tool comes with it"
    if [ ! -f "$TOOL_BIN" ] || [ -L "$TOOL_BIN" ] || [ ! -x "$TOOL_BIN" ]; then
        refuse "this runtime has no bin/oneios-tool: get a newer runtime"
    fi
    want=$(awk '$2 == "bin/oneios-tool" { print $1 }' "$STAGE/runtime.sha256" 2>/dev/null | head -n 1)
    [ -n "$want" ] && [ "$(sha "$TOOL_BIN")" = "$want" ] || refuse "bin/oneios-tool is not the file that was staged: stage the runtime again"
    tmp="$STAGE/tool"
    [ ! -L "$tmp" ] || refuse "$tmp is a link"
    [ -d "$tmp" ] || mkdir "$tmp" || die "could not make $tmp"
    own "$tmp" 0700 || die "could not make $tmp root's"
    say "@@OK tool $1"
    TMPDIR="$tmp" exec nice -n 10 "$TOOL_BIN" serve --stage "$STAGE"
}

do_untool() {
    [ $# -eq 0 ] || usage "untool"
    stage_ok
    pids=$(tool_pids)
    [ -n "$pids" ] || { say "@@OK untool nothing"; return; }
    # shellcheck disable=SC2086
    kill -TERM $pids 2>/dev/null
    n=0
    while [ $n -lt 20 ] && [ -n "$(tool_pids)" ]; do sleep 0.1; n=$((n + 1)); done
    left=$(tool_pids)
    # shellcheck disable=SC2086
    [ -z "$left" ] || kill -KILL $left 2>/dev/null
    say "@@OK untool $(echo $pids | wc -w | tr -d ' ')"
}

# --- Session logs -------------------------------------------------------------
# What the last iOS sessions left behind, for the app's Session logs screen
# (docs/oneios.md). Both verbs only read: no file is made, changed or moved,
# and they answer during a session too. session/ is the guest's to write, so a
# log is read only when it is a plain file with one name in a folder that is
# no link: a link left there would otherwise hand the app a file of One UI's.
# Sizes and offsets are compared and added with awk (mksh counts in 32 bits).
LOG_CHUNK_MAX=1048576
LOG_READ_LIMIT=20
LOG_TAIL_LINES=40
log_path() { # <id>: F, that log's file
    case "$1" in
        session) F="$STAGE/session/xnuhost.log" ;;
        switch) F="$STAGE/switch.log" ;;
        return) F="$STAGE/return.log" ;;
        display) F="$STAGE/control/display.log" ;;
        feeder) F="$STAGE/control/watchdog_feeder.log" ;;
        xnuhost-[0-9]*)
            is_dec "${1#xnuhost-}" || usage "'$1' is not a session log"
            F="$STAGE/logs/$1.log" ;;
        *) usage "'$1' is not a session log" ;;
    esac
}
log_plain() { # <file>
    [ -d "${1%/*}" ] && [ ! -L "${1%/*}" ] && [ -f "$1" ] && [ ! -L "$1" ] && [ "$(stat -c %h "$1" 2>/dev/null)" = 1 ]
}
num_le() { awk -v a="$1" -v b="$2" 'BEGIN { exit !(a + 0 <= b + 0) }'; }
log_row() { # <id>: its size, the time of its last write, its last lines
    log_path "$1"
    log_plain "$F" || return 0
    size=$(stat -c %s "$F" 2>/dev/null)
    mtime=$(stat -c %Y "$F" 2>/dev/null)
    is_dec "$size" && is_dec "$mtime" || return 0
    say "@@RESULT log $1 $size $mtime"
    # The end of the file; a first line cut by the 16 KiB is left out.
    if num_le "$size" 16384; then
        timeout "$LOG_READ_LIMIT" tail -c 16384 "$F" 2>/dev/null
    else
        timeout "$LOG_READ_LIMIT" tail -c 16384 "$F" 2>/dev/null | sed 1d
    fi | tail -n "$LOG_TAIL_LINES" | cut -c1-400 | awk -v id="$1" '{ print "| " id " " $0 }'
}

do_logs() {
    [ $# -eq 0 ] || usage "logs"
    stage_ok
    if session_open; then say "@@RESULT session open"; else say "@@RESULT session none"; fi
    log_row session
    n=0
    if [ -d "$STAGE/logs" ] && [ ! -L "$STAGE/logs" ]; then
        for id in $(ls -1 "$STAGE/logs" 2>/dev/null | sed -n 's/^\(xnuhost-[0-9][0-9]*\)\.log$/\1/p' | sort -r); do
            [ $n -lt 5 ] || break
            log_row "$id"
            n=$((n + 1))
        done
    fi
    for id in switch return display feeder; do log_row "$id"; done
    say "@@OK logs"
}

do_logfile() {
    [ $# -eq 3 ] || usage "logfile takes a log, an end and a size"
    id=$1 end=$2 max=$3
    log_path "$id"
    is_dec "$end" || usage "logfile: end '$end'"
    is_dec "$max" && num_le 1 "$max" && num_le "$max" "$LOG_CHUNK_MAX" || usage "logfile: 1 to $LOG_CHUNK_MAX bytes a call"
    stage_ok
    log_plain "$F" || refuse "there is no such log on this phone"
    size=$(stat -c %s "$F" 2>/dev/null)
    is_dec "$size" || die "could not read the size of $id"
    # The bytes [start, end): end 0, or past the file, is the file's end.
    set -- $(awk -v s="$size" -v e="$end" -v m="$max" 'BEGIN {
        if (e + 0 == 0 || s + 0 < e + 0) e = s
        b = e - m; if (b < 0) b = 0
        printf "%.0f %.0f %.0f\n", b, e, e - b }')
    start=$1 end=$2 len=$3
    # Whole lines only: a chunk that does not start the file starts after its
    # first line break, and says so in its start (the next call ends there).
    skip=0
    if [ "$start" != 0 ] && [ "$len" != 0 ]; then
        from=$(awk -v a="$start" 'BEGIN { printf "%.0f", a + 1 }')
        skip=$(timeout "$LOG_READ_LIMIT" tail -c "+$from" "$F" 2>/dev/null | head -c "$len" | head -n 1 | wc -c | tr -d ' ')
        is_dec "$skip" && [ "$skip" -lt "$len" ] || skip=0
    fi
    set -- $(awk -v a="$start" -v k="$skip" -v l="$len" 'BEGIN { printf "%.0f %.0f %.0f\n", a + k, a + k + 1, l - k }')
    start=$1 from=$2 len=$3
    say "@@RESULT chunk $id $size $start $end"
    [ "$len" = 0 ] || timeout "$LOG_READ_LIMIT" tail -c "+$from" "$F" 2>/dev/null | head -c "$len" | awk '{ print "| " $0 }'
    say "@@OK logfile $id"
}

[ -n "$T" ] || [ "$(id -u)" = 0 ] || refuse "not root"
verb=${1:-}
[ $# -gt 0 ] && shift
case "$verb" in
    status) do_status "$@" ;;
    begin) do_begin "$@" ;;
    receive) do_receive "$@" ;;
    script) do_script "$@" ;;
    finish) do_finish "$@" ;;
    switch) do_switch "$@" ;;
    return) do_return "$@" ;;
    remove) do_remove "$@" ;;
    check) do_check "$@" ;;
    uncheck) do_uncheck "$@" ;;
    checkfile) do_checkfile "$@" ;;
    logs) do_logs "$@" ;;
    logfile) do_logfile "$@" ;;
    tool) do_tool "$@" ;;
    untool) do_untool "$@" ;;
    *) usage "oneios_root.sh status|begin|receive|script|finish|switch|return|remove|check|uncheck|checkfile|logs|logfile|tool|untool" ;;
esac
