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
#                               a switch would start (oneios_switch.sh --check, quick: by the
#                               files' ids, nothing hashed; the switch hashes)
#   begin <runtime|image>       start staging one of them into <kind>.new
#   receive <runtime|image> <path> <bytes> <sha256> <mode>
#                               stdin: exactly <bytes> bytes of <path>
#                               (mode 0644 or 0755)
#   script <name> <bytes> <sha256>
#                               stdin: oneios_switch.sh or oneios_return.sh
#   finish runtime <files> <version> <sessionAbi> <xnuhost> <imageFormats> <placeholder>
#                <kernelBuildId|none> <kernelSha256|none> <kernelXnu|none>
#   finish image <files> <format> <version> <build>
#                               <files> received files (the manifest included)
#                               become $STAGE/<kind>; the facts the app read
#                               from the checked manifest go to <kind>.conf
#                               (runtime.conf also records the runtime's own
#                               kernel, when its runtime.json has one)
#   kbinput <name> <bytes> <sha256> [kb-<BUILD>]
#                               stdin: exactly <bytes> of one kernel-build input
#                               ($STAGE/kb/<name>, or $STAGE/kb-<BUILD>/<name>
#                               for the inputs of another Apple build than
#                               24A446: kb-24B156 for iOS 27.2.1). <name> is
#                               one of the fixed allowlist (the app's
#                               kb/kb.json): profile.toml,
#                               reviewed/pairs/stubs/lead/user.json, the
#                               matcher's files
#                               (match/fixtures/fileset-<id>-symbols.json), or
#                               kernelcache.macho (Apple's
#                               decoded kernelcache: the optional import of a
#                               file a PC wrote; the kernel update fetches it
#                               itself, kbcache). Writable only by this verb
#                               and kbcache.
#   kbcache <bytes> <sha256> [kb-<BUILD>]
#                               Apple's kernelcache that the phone's
#                               oneios-tool fetched from Apple and decoded
#                               ($STAGE/make-kernel/kernelcache.macho, the
#                               tool's fetch and im4p) becomes the cached
#                               kb/kernelcache.macho (or kb-<BUILD>/'s), when
#                               it has <bytes> and
#                               <sha256> (the pin of the app's kb/kb.json;
#                               another one is deleted and refused). The
#                               downloaded IM4P ($STAGE/make-kernel/inputs) is
#                               removed. Never committed, released or shipped:
#                               each phone fetches its own from Apple.
#   kbclean                     the kernel update's work folder goes
#                               ($STAGE/make-kernel: the download's parts, the
#                               decode, a build not activated); kb/, kb-*/ and
#                               their cached kernelcaches stay
#   finish kernel <kc-sha256> <build-id> [kb-<BUILD> <xnu path>]
#                               activate the kernel the phone's oneios-tool built
#                               ($STAGE/make-kernel/out: kernel.kc with its
#                               hashes and records, the audit passed): checks
#                               first (the collection is from this runtime's xnu
#                               and the staged kernelcache: kernel/xnu.macho and
#                               kb/, or for an image set of another build
#                               <xnu path> of the runtime, e.g.
#                               kernel/24B156/xnu.macho, and kb-<BUILD>/, which
#                               must be the staged set's build), then the old set
#                               aside to $STAGE/kernel.prev, the new files in,
#                               image.sha256, image.ids, manifest.json and
#                               image.conf rewritten, a receipt in logs/. The
#                               old set stays as the fallback (restore kernel).
#                               An iOS 16.5 (20F66) set then gets the runtime's
#                               A56 GPU addon (a56_gpu_place: bin/oneios-tool
#                               image a56-gpu-place, kernel.kc.gpuaddon and
#                               owner-trust.json in, the lists rewritten; its
#                               line @@RESULT a56-gpu placed|none|skipped ...).
#                               Refuses during a session.
#   restore kernel              the fallback back: $STAGE/kernel.prev becomes
#                               the image's set again (owner-trust.json and the
#                               GPU addon as it kept them), with its own receipt.
#                               Refuses with no fallback or during a session.
#   switch <versionCode> <ack> [hosted|takeover]
#                               the preflight, then the session, detached, in
#                               init's mount namespace (ack 1 = the
#                               experimental tick; takeover = the Android
#                               takeover's toggle, passed to the switch as
#                               ONEIOS_SESSION_MODE=takeover; hosted or none:
#                               nothing passed, the image's xnuhost.conf decides)
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
# A kernel build id (`oneios-tool kernel build-record`): xnu-<xnu>-<profile>-<12 hex>, plain and short.
is_bid() { case "$1" in xnu-*[!A-Za-z0-9._-]*) return 1 ;; esac; [ ${#1} -ge 5 ] && [ ${#1} -le 90 ]; }
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
    # The kernels: the runtime's own (its runtime.json, recorded at finish),
    # and the image set's kernel.kc (recorded at its activation, with the
    # fallback when one is kept). "none": staged before kernel tracking, or
    # the runtime carries no kernel.
    krb=$(conf "$rc" kernel_build_id 2>/dev/null)
    case "$krb" in ''|none|-*) krb="none"; kxn="none" ;; *) kxn=$(conf "$rc" kernel_xnu) ;; esac
    say "@@RESULT kernel runtime $krb $kxn"
    kbb=$(conf "$ic" kernel_build_id 2>/dev/null)
    case "$kbb" in ''|-*) kbb="unknown" ;; esac
    if [ -f "$STAGE/image/kernel.kc" ] && mine "$STAGE/image/kernel.kc"; then
        kcs=$(awk '$2 == "kernel.kc" { print $1 }' "$STAGE/image.sha256" 2>/dev/null | head -n 1)
        case "$kcs" in ????????????????????????????????????????????????????????????????) ;; *) kcs="unknown" ;; esac
        prev=0
        [ -f "$STAGE/kernel.prev/kernel.kc" ] && prev=1
        say "@@RESULT kernel image $kbb $kcs $prev"
    else
        say "@@RESULT kernel image none"
    fi
    # The kernel-build inputs ($STAGE/kb): Apple's kernelcache by its recorded
    # SHA-256 (written by kbcache or kbinput, the file itself is 78 MB), and how many
    # of the 13 inputs are staged. Presence is integrity here: every file is
    # root's, and only this script's kbinput and kbcache (size and SHA-256 checked) write.
    if [ -d "$STAGE/kb" ] && mine "$STAGE/kb" && [ -f "$STAGE/kb/kernelcache.macho" ] && [ ! -L "$STAGE/kb/kernelcache.macho" ]; then
        kcs=$(cat "$STAGE/kb/kernelcache.sha256" 2>/dev/null)
        case "$kcs" in ????????????????????????????????????????????????????????????????) ;; *) kcs="none" ;; esac
    else
        kcs="none"
    fi
    kbn=0
    if [ -d "$STAGE/kb" ] && mine "$STAGE/kb" ]; then
        for kf in kernelcache.macho profile.toml reviewed.json pairs.json stubs.json lead.json user.json; do
            [ -f "$STAGE/kb/$kf" ] && [ ! -L "$STAGE/kb/$kf" ] && kbn=$((kbn + 1))
        done
        for kf in match/fixtures/fileset-23F84-symbols.json match/fixtures/fileset-24A446-symbols.json match/fixtures/fileset-26C5035r-symbols.json; do
            [ -f "$STAGE/kb/$kf" ] && [ ! -L "$STAGE/kb/$kf" ] && kbn=$((kbn + 1))
        done
    fi
    say "@@RESULT kb $kcs $kbn"
    # The inputs of another Apple build ($STAGE/kb-<BUILD>, e.g. kb-24B156 for
    # iOS 27.2.1), one line each: the build, the kernelcache's SHA-256 (or
    # none) and how many input files are there (the kernelcache counted).
    for d in "$STAGE"/kb-*; do
        [ -d "$d" ] && mine "$d" || continue
        kbd_ok "${d##*/}" >/dev/null || continue
        if [ -f "$d/kernelcache.macho" ] && [ ! -L "$d/kernelcache.macho" ]; then
            kcs=$(cat "$d/kernelcache.sha256" 2>/dev/null)
            case "$kcs" in ????????????????????????????????????????????????????????????????) ;; *) kcs="none" ;; esac
        else
            kcs="none"
        fi
        kbn=$(find "$d" -type f ! -name kernelcache.sha256 2>/dev/null | wc -l | tr -d ' ')
        is_dec "$kbn" || kbn=0
        say "@@RESULT kbset ${d##*/kb-} $kcs $kbn"
    done
    st=$(cat "$STAGE/control/state" 2>/dev/null)
    if session_open; then say "@@RESULT session open ${st:-running}"; else say "@@RESULT session none ${st:-never}"; fi
    o=$(head -n 1 "$STAGE/return.outcome" 2>/dev/null | cut -c1-200)
    case "$o" in inplace\ *|failsafe\ *|reboot\ *) say "@@RESULT outcome $o" ;; *) say "@@RESULT outcome none" ;; esac
    # Would a switch start now? The session script's own preflight, read only, by the files' ids (ONEIOS_CHECK_QUICK:
    # nothing hashed, an answer in a moment); the switch verb's preflight hashes every file as before.
    if [ -f "$STAGE/oneios_switch.sh" ] && mine "$STAGE/oneios_switch.sh"; then
        if [ -n "$T" ]; then
            out=$(ONEIOS_CHECK_QUICK=1 ONEIOS_TEST_ROOT="$T" sh "$STAGE/oneios_switch.sh" --check 2>&1)
        else
            find_bb
            if [ -n "$BB" ]; then
                out=$(ONEIOS_CHECK_QUICK=1 ONEIOS_APP=1 ONEIOS_ACK_EXPERIMENTAL=1 "$BB" nsenter -t 1 -m -- /system/bin/sh "$STAGE/oneios_switch.sh" --check 2>&1 </dev/null)
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
    [ $# -ge 1 ] || usage "finish <runtime|image|kernel> ..."
    kind=$1
    if [ "$kind" = kernel ]; then
        shift
        do_finish_kernel "$@"
        return
    fi
    kind_ok "$kind"
    if [ "$kind" = runtime ]; then
        [ $# -eq 10 ] || usage "finish runtime <files> <version> <sessionAbi> <xnuhost> <imageFormats> <placeholder> <kernelBuildId|-> <kernelSha256|-> <kernelXnu|->"
        files=$2 version=$3 abi=$4 xnuhost=$5 formats=$6 placeholder=$7 krb=$8 ksha=$9 kxnu=${10}
        case "$placeholder" in 0|1) ;; *) usage "finish: placeholder '$placeholder'" ;; esac
        is_dec "$abi" || usage "finish: session ABI '$abi'"
        is_path "$xnuhost" || usage "finish: xnuhost '$xnuhost'"
        case "$formats" in ''|*[!0-9,]*|,*|*,|*,,*) usage "finish: image formats '$formats'" ;; esac
        case "$krb" in none) ;; xnu-*) is_bid "$krb" || usage "finish: kernel build id" ;; *) usage "finish: kernel build id" ;; esac
        case "$ksha" in none) ;; *) is_hex64 "$ksha" || usage "finish: kernel SHA-256" ;; esac
        case "$kxnu" in none) ;; *) is_word "$kxnu" || usage "finish: kernel xnu" ;; esac
        { [ "$krb" = none ] && [ "$ksha" = none ] && [ "$kxnu" = none ]; } ||
            { [ "$krb" != none ] && [ "$ksha" != none ] && [ "$kxnu" != none ]; } ||
            usage "finish: the kernel facts come together or not at all"
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
            echo "kernel_build_id=$krb"
            echo "kernel_sha256=$ksha"
            echo "kernel_xnu=$kxnu"
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

# --- Kernel updates ---------------------------------------------------------
# A new kernel without rebuilding the image set: the phone's oneios-tool pairs
# the staged runtime's xnu.macho with Apple's kernelcache (fetched from Apple by
# the phone itself, kbcache) and the reviewed records the app carries, and its
# `prelink build` writes kernel.kc with its hashes and records only after the
# audit and the stub check passed. These verbs stage those inputs and activate
# that output, atomically: checks first, the old set aside, the new files in,
# the lists, the manifest and the configs rewritten, a receipt where the
# session logs live. The old set stays in $STAGE/kernel.prev as the fallback
# (restore kernel). Any intermediate state fails the switch's preflight
# (check_list: every file hashed or matched against the lists), so a
# half-updated set never boots: it refuses instead.
KB_MAX=536870912
# The inputs' folder: kb/ (24A446, and the Galaxy A56's 20F66, whose kernel.kc
# has the 24A446 kexts) unless [kb-<BUILD>] names another Apple build's
# (kb-24B156 for iOS 27.2.1). Fails when the word is not one.
kbd_ok() { # [kb-<BUILD>]
    case "$1" in
        '') echo "$STAGE/kb" ;;
        kb-*)
            b=${1#kb-}
            case "$b" in ''|*[!0-9A-Z]*) return 1 ;; esac
            [ ${#b} -ge 3 ] && [ ${#b} -le 20 ] || return 1
            echo "$STAGE/$1" ;;
        *) return 1 ;;
    esac
}
kb_name() { # <name> [kb-<BUILD>]: the input's path, or nothing when it is not a kernel-build input
    d=$(kbd_ok "$2") || return 0
    case "$1" in
        kernelcache.macho|profile.toml|reviewed.json|pairs.json|stubs.json|lead.json|user.json)
            echo "$d/$1" ;;
        match/fixtures/fileset-*-symbols.json)
            id=${1#match/fixtures/fileset-}
            id=${id%-symbols.json}
            case "$id" in ''|*[!0-9A-Za-z]*) return 0 ;; esac
            [ ${#id} -le 20 ] && echo "$d/$1" ;;
    esac
    return 0
}

do_kbinput() {
    [ $# -eq 3 ] || [ $# -eq 4 ] || usage "kbinput <name> <bytes> <sha256> [kb-<BUILD>]"
    [ $# -eq 3 ] || [ -n "$4" ] || usage "kbinput: the folder is kb-<BUILD>"
    kbd=$(kbd_ok "${4:-}") || usage "kbinput: '$4' is not kb-<BUILD>"
    to=$(kb_name "$1" "${4:-}")
    [ -n "$to" ] || usage "kbinput: '$1' is not a kernel-build input"
    is_dec "$2" && [ "$2" -ge 1 ] || usage "kbinput: size '$2'"
    awk -v b="$2" -v m="$KB_MAX" 'BEGIN { exit !(b + 0 <= m + 0) }' || refuse "$1 is too large"
    is_hex64 "$3" || usage "kbinput: SHA-256"
    stage_ok
    session_open && refuse "an iOS session is running: return to One UI first"
    [ ! -L "$kbd" ] || refuse "$kbd is a link"
    d="${to%/*}"
    [ ! -L "$d" ] || refuse "$d is a link"
    { [ -d "$d" ] || mkdir -p "$d"; } && own "$d" 0700 || die "could not make $d"
    [ ! -L "$to" ] || refuse "$to is a link"
    take "$to" "$2" "$3" 0600
    if [ "$1" = kernelcache.macho ]; then
        echo "$3" > "$kbd/kernelcache.sha256" && own "$kbd/kernelcache.sha256" 0600 || die "could not record the kernelcache"
    fi
    say "@@OK kbinput $1"
}

# Apple's kernelcache as the kernel update fetched it (the tool's fetch of the
# profile's kernelcache member from Apple, then its im4p): into kb/ (or the
# kb-<BUILD>/ named) only when it is the pinned one; root hashes the file
# itself, whatever the tool said.
do_kbcache() {
    [ $# -eq 2 ] || [ $# -eq 3 ] || usage "kbcache <bytes> <sha256> [kb-<BUILD>]"
    [ $# -eq 2 ] || [ -n "$3" ] || usage "kbcache: the folder is kb-<BUILD>"
    d=$(kbd_ok "${3:-}") || usage "kbcache: '$3' is not kb-<BUILD>"
    is_dec "$1" && [ "$1" -ge 1 ] || usage "kbcache: size '$1'"
    awk -v b="$1" -v m="$KB_MAX" 'BEGIN { exit !(b + 0 <= m + 0) }' || refuse "kernelcache.macho is too large"
    is_hex64 "$2" || usage "kbcache: SHA-256"
    stage_ok
    session_open && refuse "an iOS session is running: return to One UI first"
    w="$STAGE/make-kernel"
    from="$w/kernelcache.macho"
    [ -d "$w" ] && mine "$w" && [ -f "$from" ] && mine "$from" ||
        refuse "no kernelcache was fetched in $w: run the kernel update"
    got=$(stat -c %s "$from" 2>/dev/null)
    if [ "$got" != "$1" ]; then
        rm -f "$from"
        refuse "the fetched kernelcache has ${got:-no} bytes, not $1: it is not the one the profile pins, nothing was kept"
    fi
    if [ "$(sha "$from")" != "$2" ]; then
        rm -f "$from"
        refuse "the fetched kernelcache is not the one the profile pins (its SHA-256 differs): nothing was kept"
    fi
    [ ! -L "$d" ] || refuse "$d is a link"
    { [ -d "$d" ] || mkdir -p "$d"; } && own "$d" 0700 || die "could not make $d"
    [ ! -L "$d/kernelcache.macho" ] || refuse "$d/kernelcache.macho is a link"
    own "$from" 0600 && mv -f "$from" "$d/kernelcache.macho" || die "could not keep the kernelcache"
    echo "$2" > "$d/kernelcache.sha256" && own "$d/kernelcache.sha256" 0600 || die "could not record the kernelcache"
    # The IM4P and the fetch's record: the decoded file is all a later build needs.
    rm -rf "$w/inputs" || die "could not remove $w/inputs"
    say "@@OK kbcache $1"
}

# The kernel update's work folder, after a cancel or a download that cannot be
# resumed. The cached kernelcaches in kb/ and kb-*/ are not part of it.
do_kbclean() {
    [ $# -eq 0 ] || usage "kbclean"
    stage_ok
    session_open && refuse "an iOS session is running: return to One UI first"
    w="$STAGE/make-kernel"
    [ -e "$w" ] || [ -L "$w" ] || { say "@@OK kbclean nothing"; return; }
    # (a link is removed itself, never followed)
    rm -rf "$w" || die "could not remove $w"
    say "@@OK kbclean"
}

# kernel.kc's manifest entry (its size and SHA-256) rewritten from stdin to
# stdout; only those two lines change. Exit 1 when the entry is not as
# expected, so nothing is activated from a manifest of another shape.
manifest_rekernel() { # <size> <sha256>
    awk -v s="$1" -v h="$2" '
        /"path": *"kernel\.kc",/ { kc = 1 }
        kc == 1 && /"size": *[0-9]+,/ { sub(/"size": *[0-9]+,/, "\"size\": " s ","); kc = 2 }
        kc == 2 && /"sha256": *"[0-9a-f]+",/ { sub(/"sha256": *"[0-9a-f]+",/, "\"sha256\": \"" h "\","); kc = 3 }
        { print }
        END { exit(kc == 3 ? 0 : 1) }
    '
}

# One "<sha>  <path>" line of a sha256sum list rewritten from stdin to stdout,
# keeping the two spaces serve's sums parses (no field splitting: the path is
# compared whole, so dots and slashes are literal). Exit 1 when the path is
# not in there exactly once.
list_resha() { # <path> <sha256>
    awk -v p="$1" -v h="$2" '
        {
            head = substr($0, 1, 64); mid = substr($0, 65, 2); tail = substr($0, 67)
            if (head ~ /^[0-9a-f]{64}$/ && mid == "  " && tail == p) { print h "  " p; n++ }
            else print
        }
        END { exit(n == 1 ? 0 : 1) }
    '
}

file_id() { stat -c '%d:%i:%s:%Y' "$1" 2>/dev/null; }

# What the activation switches, backed up first: the two kernel files, the
# manifest, the two lists and the image's config.

kc_check_prebuilt() { # <dir>: the collection there is complete and named by <kc-sha256>
    out=$1
    [ -d "$out" ] && mine "$out" || return 1
    for f in kernel.kc kernel.kc.hashes kernel.kc.build.json kernel.kc.prelink.json kernel.kc.binds.json; do
        [ -f "$out/$f" ] && [ ! -L "$out/$f" ] && mine "$out/$f" || return 1
    done
    return 0
}

# The inputs a kernel is checked against: the runtime's kernel/xnu.macho and
# kb/ (24A446), unless finish kernel names another build's kb-<BUILD>/ and
# the runtime's xnu path for it. restore kernel's receipt uses the defaults.
KB_XNU=kernel/xnu.macho
KB_DIR=
kc_check_inputs() { # <dir>: the collection is from this runtime's xnu and the staged kernelcache
    out=$1
    xnu=$(awk -v p="$KB_XNU" '$2 == p { print $1 }' "$STAGE/runtime.sha256" 2>/dev/null | head -n 1)
    [ -n "$xnu" ] || { echo "the staged runtime has no $KB_XNU: stage a runtime with a kernel first"; return 1; }
    grep -Fq "\"sha256\": \"$xnu\"" "$out/kernel.kc.build.json" ||
        { echo "the built kernel.kc is not from this runtime's ${KB_XNU#kernel/}: run the kernel build again"; return 1; }
    kd=$(kbd_ok "$KB_DIR") || { echo "'$KB_DIR' is not kb-<BUILD>"; return 1; }
    [ -f "$kd/kernelcache.macho" ] && [ ! -L "$kd/kernelcache.macho" ] ||
        { echo "the Apple kernelcache is not staged: run the kernel update first"; return 1; }
    grep -Fq "\"sha256\": \"$(sha "$kd/kernelcache.macho")\"" "$out/kernel.kc.build.json" ||
        { echo "the built kernel.kc is not from the staged kernelcache: run the kernel build again"; return 1; }
    return 0
}

kc_backup() { # <dest>: the live set aside (the manifest, lists and config with the kernel files)
    dest=$1
    rm -rf "$dest" || return 1
    mkdir "$dest" && own "$dest" 0700 || return 1
    for f in kernel.kc kernel.kc.hashes manifest.json; do
        cp -p "$STAGE/image/$f" "$dest/$f" && own "$dest/$f" 0600 || return 1
    done
    for f in image.sha256 image.ids image.conf; do
        cp -p "$STAGE/$f" "$dest/$f" && own "$dest/$f" 0600 || return 1
    done
    # The A56's GPU addon and owner-trust.json (a56_gpu_place may replace both): kept, or recorded as absent, so
    # a restore leaves the set its lists name (gpu.kept: "kept <path>" or "none <path>").
    printf '' > "$dest/gpu.kept" && own "$dest/gpu.kept" 0600 || return 1
    for g_p in "$GPU_TRUST" "$GPU_ADDON"; do
        if [ -f "$STAGE/image/$g_p" ] && [ ! -L "$STAGE/image/$g_p" ]; then
            cp -p "$STAGE/image/$g_p" "$dest/${g_p##*/}" && own "$dest/${g_p##*/}" 0600 || return 1
            echo "kept $g_p" >> "$dest/gpu.kept" || return 1
        else
            echo "none $g_p" >> "$dest/gpu.kept" || return 1
        fi
    done
    return 0
}

kc_receipt() { # <kind: update|restore> <from-sha> <from-bid> <to-sha> <to-bid>: where the session logs live
    epoch=$(date +%s)
    name="update-$epoch"
    n=1
    while [ -e "$STAGE/logs/$name.log" ]; do
        n=$((n + 1))
        name="update-$epoch-$n"
    done
    {
        echo "oneios kernel $1 $epoch"
        echo "date: $(date '+%F %T')"
        echo "from: kernel.kc $2 (build $3)"
        echo "to: kernel.kc $4 (build $5)"
        echo "xnu: $(awk -v p="$KB_XNU" '$2 == p { print $1 }' "$STAGE/runtime.sha256" 2>/dev/null | head -n 1) (the staged runtime's $KB_XNU)"
        echo "kernelcache: $(sha "$(kbd_ok "$KB_DIR")/kernelcache.macho" 2>/dev/null) (the staged Apple kernelcache${KB_DIR:+, $KB_DIR})"
        echo "audit: passed (kernel.kc.binds.json present, $(sha "$STAGE/kernel-build/$5/kernel.kc.binds.json" 2>/dev/null))"
        echo "records: $STAGE/kernel-build/$5/ (kernel.kc.build.json, kernel.kc.prelink.json, kernel.kc.binds.json)"
    } > "$STAGE/logs/$name.log" && own "$STAGE/logs/$name.log" 0600 || return 1
    echo "$name"
    return 0
}

kc_activate() { # <dir> <kc-sha256> <build-id>: <dir>'s kernel.kc + hashes become the image's (the backup is already aside)
    src=$1 kc=$2 bid=$3
    [ -d "$STAGE/image" ] && mine "$STAGE/image" || { echo "no iOS image set is staged"; return 1; }
    newbytes=$(stat -c %s "$src/kernel.kc" 2>/dev/null)
    is_dec "$newbytes" || { echo "could not read the built kernel.kc"; return 1; }
    # All rewrites land in a scratch folder first, checked before anything
    # moves: nothing half-written ever sits in the image or beside its lists
    # (a stray file there fails the switch's preflight). Every intermediate
    # state after the moves then fails that preflight instead of booting
    # half-updated.
    tmp="$src/tmp"
    rm -rf "$tmp" && mkdir "$tmp" && own "$tmp" 0700 || { echo "could not make $tmp"; return 1; }
    manifest_rekernel "$newbytes" "$kc" < "$STAGE/image/manifest.json" > "$tmp/manifest.json" ||
        { echo "manifest.json has no kernel.kc entry as expected: stage the image set again"; return 1; }
    grep -Fq "\"sha256\": \"$kc\"" "$tmp/manifest.json" ||
        { echo "the rewritten manifest.json does not name $kc"; return 1; }
    mfsha=$(sha "$tmp/manifest.json")
    list_resha kernel.kc "$kc" < "$STAGE/image.sha256" > "$tmp/image.sha256" ||
        { echo "image.sha256 names kernel.kc no or twice: stage the image set again"; return 1; }
    hsha=$(sha "$src/kernel.kc.hashes")
    list_resha kernel.kc.hashes "$hsha" < "$tmp/image.sha256" > "$tmp/image.sha256.2" &&
        mv -f "$tmp/image.sha256.2" "$tmp/image.sha256" ||
        { echo "image.sha256 names kernel.kc.hashes no or twice: stage the image set again"; return 1; }
    list_resha manifest.json "$mfsha" < "$tmp/image.sha256" > "$tmp/image.sha256.2" &&
        mv -f "$tmp/image.sha256.2" "$tmp/image.sha256" ||
        { echo "image.sha256 names manifest.json no or twice: stage the image set again"; return 1; }
    mv -f "$src/kernel.kc" "$STAGE/image/kernel.kc" && mv -f "$src/kernel.kc.hashes" "$STAGE/image/kernel.kc.hashes" ||
        { echo "could not put the new kernel.kc in place"; return 1; }
    own "$STAGE/image/kernel.kc" 0644 && own "$STAGE/image/kernel.kc.hashes" 0644 || return 1
    mv -f "$tmp/manifest.json" "$STAGE/image/manifest.json" &&
        mv -f "$tmp/image.sha256" "$STAGE/image.sha256" || { echo "could not put the new lists in place"; return 1; }
    kid=$(file_id "$STAGE/image/kernel.kc")
    hid=$(file_id "$STAGE/image/kernel.kc.hashes")
    mid=$(file_id "$STAGE/image/manifest.json")
    case "$kid$hid$mid" in ''|*'
'*) { echo "could not read the new files back"; return 1; } ;; esac
    awk -v kid="$kid" -v hid="$hid" -v mid="$mid" '
        $2 == "kernel.kc" { print kid " kernel.kc"; n++; next }
        $2 == "kernel.kc.hashes" { print hid " kernel.kc.hashes"; n++; next }
        $2 == "manifest.json" { print mid " manifest.json"; n++; next }
        { print }
        END { exit(n == 3 ? 0 : 1) }
    ' "$STAGE/image.ids" > "$tmp/image.ids" || { echo "could not rewrite image.ids"; return 1; }
    mv -f "$tmp/image.ids" "$STAGE/image.ids" || return 1
    [ -n "$T" ] || sync
    return 0
}

# --- The Galaxy A56's GPU addon (docs/oneios.md, "Kernel updates") ---------
# An iOS 16.5 (20F66) set gets the staged runtime's A56 gpuaddon (the Metal and
# OpenGL ES plug-ins) as image/kernel.kc.gpuaddon, with its CDHashes in
# overlay/userland/owner-trust.json, in the same finish kernel, after the
# kernel is activated: the runtime's oneios-tool (`image a56-gpu-place`, the
# file root hashed when the runtime was staged) writes the three files into a
# scratch folder, root checks them and moves them in, and rewrites
# image.sha256 and image.ids. Any other build (iOS 27, 24A446) never runs the
# tool. A runtime without the command, or with nothing for this set, leaves the
# set as it is ("none"); a tool that fails or writes something else leaves it
# too ("skipped"): the kernel stays activated and the session is the 2D one.
A56_GPU_BUILD=20F66
GPU_TRUST=overlay/userland/owner-trust.json
GPU_ADDON=kernel.kc.gpuaddon
# xnuhost's limit for the sidecar (docs/booter.md).
GPU_ADDON_MAX=67108864

# A sha256sum list (<list>) with the changes of <changes> made, to stdout: a
# "<sha256> <path>" line replaces <path>'s line (or is added at the end when
# the list has none), "- <path>" removes it. The two spaces are kept, and the
# path is compared whole (as list_resha).
sums_set() { # <list> <changes>
    awk -v c="$2" '
        BEGIN { while ((getline l < c) > 0) { split(l, w, " "); want[w[2]] = w[1]; order[++n] = w[2] } }
        {
            head = substr($0, 1, 64); mid = substr($0, 65, 2); tail = substr($0, 67)
            if (head ~ /^[0-9a-f]+$/ && length(head) == 64 && mid == "  " && (tail in want)) {
                if (!(tail in done) && want[tail] != "-") print want[tail] "  " tail
                done[tail] = 1
                next
            }
            print
        }
        END { for (i = 1; i <= n; i++) if (!(order[i] in done) && want[order[i]] != "-") print want[order[i]] "  " order[i] }
    ' "$1"
}

# The same for an ids list ("<dev:inode:size:mtime> <path>").
ids_set() { # <list> <changes>
    awk -v c="$2" '
        BEGIN { while ((getline l < c) > 0) { split(l, w, " "); want[w[2]] = w[1]; order[++n] = w[2] } }
        NF == 2 && ($2 in want) {
            if (!($2 in done) && want[$2] != "-") print want[$2] " " $2
            done[$2] = 1
            next
        }
        { print }
        END { for (i = 1; i <= n; i++) if (!(order[i] in done) && want[order[i]] != "-") print want[order[i]] " " order[i] }
    ' "$1"
}

# How often <path> is in a list (its second field).
list_count() { awk -v p="$2" '$2 == p { n++ } END { print n + 0 }' "$1" 2>/dev/null; }

gpu_say() { # <placed|none|skipped> <words>: the finish's line (the app shows it), and the receipt's
    GPU_LINE="$1: $2"
    say "@@RESULT a56-gpu $1 $2"
}

# After kc_activate and image.conf: never refuses the finish. Dies only when a
# move into the image fails (the kernel is activated then; Restore puts the set
# back). Its variables are g_*: the finish's own (out, kc, bid, name) stay.
a56_gpu_place() {
    GPU_LINE=""
    [ "$(conf "$STAGE/image.conf" build)" = "$A56_GPU_BUILD" ] || return 0
    if [ ! -f "$TOOL_BIN" ] || [ -L "$TOOL_BIN" ] || [ ! -x "$TOOL_BIN" ]; then
        gpu_say none "this runtime has no bin/oneios-tool: the session stays 2D"
        return 0
    fi
    g_want=$(awk '$2 == "bin/oneios-tool" { print $1 }' "$STAGE/runtime.sha256" 2>/dev/null | head -n 1)
    [ -n "$g_want" ] && [ "$(sha "$TOOL_BIN")" = "$g_want" ] ||
        { gpu_say skipped "bin/oneios-tool is not the file that was staged: stage the runtime again"; return 0; }
    [ -f "$STAGE/image/$GPU_TRUST" ] && [ ! -L "$STAGE/image/$GPU_TRUST" ] &&
        [ "$(list_count "$STAGE/image.sha256" "$GPU_TRUST")" = 1 ] && [ "$(list_count "$STAGE/image.ids" "$GPU_TRUST")" = 1 ] ||
        { gpu_say skipped "the image set has no listed $GPU_TRUST: the addon's code would not be trusted"; return 0; }
    # The tool's --out (empty, root's, 0700), its TMPDIR, and root's own work (its output, the lists).
    g_w="$out/a56gpu"
    g_x="$out/a56gpu.root"
    rm -rf "$g_w" "$g_w.tmp" "$g_x" && mkdir "$g_w" "$g_w.tmp" "$g_x" &&
        own "$g_w" 0700 && own "$g_w.tmp" 0700 && own "$g_x" 0700 ||
        { gpu_say skipped "could not make $g_w"; return 0; }
    TMPDIR="$g_w.tmp" nice -n 10 "$TOOL_BIN" image a56-gpu-place --stage "$STAGE" --out "$g_w" \
        </dev/null >"$g_x/out" 2>"$g_x/err"
    g_rc=$?
    g_last=$(tail -n 1 "$g_x/out" 2>/dev/null)
    g_err=$(grep -v '^ *$' "$g_x/err" 2>/dev/null | tail -n 1 | cut -c1-200)
    case "$g_last" in
        "@@A56GPU none: "*)
            if [ $g_rc = 0 ]; then
                gpu_say none "${g_last#@@A56GPU none: }"
            else
                gpu_say skipped "oneios-tool image a56-gpu-place said none with status $g_rc"
            fi
            return 0 ;;
        "@@A56GPU error: "*)
            gpu_say skipped "${g_last#@@A56GPU error: }"
            return 0 ;;
        "@@A56GPU placed: "*) ;;
        *)
            # An older runtime's tool: `image` with a command it does not know prints its usage (which does not
            # name a56-gpu-place) and exits 1, with nothing on stdout.
            if [ $g_rc = 1 ] && ! grep -q '^@@A56GPU' "$g_x/out" && ! grep -q 'a56-gpu-place' "$g_x/err"; then
                gpu_say none "this runtime's oneios-tool has no image a56-gpu-place (an older runtime): the session stays 2D"
            else
                gpu_say skipped "oneios-tool image a56-gpu-place ended with status $g_rc${g_err:+: $g_err}"
            fi
            return 0 ;;
    esac
    [ $g_rc = 0 ] || { gpu_say skipped "oneios-tool image a56-gpu-place said placed but ended with status $g_rc"; return 0; }
    # kernel.kc.gpuaddon SHA BYTES; owner-trust.json SHA; manifest.json SHA
    read -r g_n1 g_asha g_abytes g_n2 g_tsha g_n3 g_msha g_more <<EOF
${g_last#@@A56GPU placed: }
EOF
    g_abytes=${g_abytes%;}
    g_tsha=${g_tsha%;}
    [ "$g_n1" = kernel.kc.gpuaddon ] && [ "$g_n2" = owner-trust.json ] && [ "$g_n3" = manifest.json ] && [ -z "$g_more" ] &&
        is_hex64 "$g_asha" && is_dec "$g_abytes" && is_hex64 "$g_tsha" && is_hex64 "$g_msha" ||
        { gpu_say skipped "oneios-tool's placed line is not as expected: $(echo "$g_last" | cut -c1-200)"; return 0; }
    # Exactly the three files, as the line says; the manifest is this finish's (it names the new kernel.kc).
    [ "$(cd "$g_w" && find . | LC_ALL=C sort | tr '\n' ' ')" = ". ./kernel.kc.gpuaddon ./manifest.json ./owner-trust.json " ] ||
        { gpu_say skipped "oneios-tool left other files than kernel.kc.gpuaddon, owner-trust.json and manifest.json"; return 0; }
    for g_f in kernel.kc.gpuaddon owner-trust.json manifest.json; do
        [ -f "$g_w/$g_f" ] && [ ! -L "$g_w/$g_f" ] || { gpu_say skipped "$g_f is not a plain file"; return 0; }
    done
    [ "$(stat -c %s "$g_w/kernel.kc.gpuaddon" 2>/dev/null)" = "$g_abytes" ] && [ "$g_abytes" -le $GPU_ADDON_MAX ] &&
        [ "$(head -c 8 "$g_w/kernel.kc.gpuaddon")" = NGPUADD2 ] &&
        [ "$(sha "$g_w/kernel.kc.gpuaddon")" = "$g_asha" ] ||
        { gpu_say skipped "the gpuaddon the tool wrote is not the one it named (NGPUADD2, $g_abytes bytes, 64 MiB at most)"; return 0; }
    [ "$(sha "$g_w/owner-trust.json")" = "$g_tsha" ] && [ "$(sha "$g_w/manifest.json")" = "$g_msha" ] ||
        { gpu_say skipped "owner-trust.json or manifest.json is not the one the tool named"; return 0; }
    grep -Fq "\"sha256\": \"$kc\"" "$g_w/manifest.json" && grep -Fq "\"sha256\": \"$g_tsha\"" "$g_w/manifest.json" ||
        { gpu_say skipped "the tool's manifest.json does not name the new kernel.kc and owner-trust.json"; return 0; }
    # The new image.sha256 first, checked, before anything moves.
    {
        echo "$g_asha $GPU_ADDON"
        echo "$g_tsha $GPU_TRUST"
        echo "$g_msha manifest.json"
    } > "$g_x/sums.changes" && sums_set "$STAGE/image.sha256" "$g_x/sums.changes" > "$g_x/image.sha256" ||
        { gpu_say skipped "could not rewrite image.sha256"; return 0; }
    for g_l in "$g_asha  $GPU_ADDON" "$g_tsha  $GPU_TRUST" "$g_msha  manifest.json"; do
        [ "$(grep -Fxc -- "$g_l" "$g_x/image.sha256")" = 1 ] || { gpu_say skipped "the rewritten image.sha256 lacks '$g_l'"; return 0; }
    done
    # The moves: every state between them fails the switch's preflight (a file its list does not name, or
    # whose id or sum differs) rather than booting half-placed.
    g_fail="the kernel is activated, but the GPU addon is half in place: Restore the kept kernel set, or Update the kernel again"
    mv -f "$g_w/kernel.kc.gpuaddon" "$STAGE/image/$GPU_ADDON" && own "$STAGE/image/$GPU_ADDON" 0644 &&
        mv -f "$g_w/owner-trust.json" "$STAGE/image/$GPU_TRUST" && own "$STAGE/image/$GPU_TRUST" 0644 &&
        mv -f "$g_w/manifest.json" "$STAGE/image/manifest.json" && own "$STAGE/image/manifest.json" 0644 &&
        mv -f "$g_x/image.sha256" "$STAGE/image.sha256" || die "could not move the GPU addon in: $g_fail"
    g_aid=$(file_id "$STAGE/image/$GPU_ADDON")
    g_tid=$(file_id "$STAGE/image/$GPU_TRUST")
    g_mid=$(file_id "$STAGE/image/manifest.json")
    [ -n "$g_aid" ] && [ -n "$g_tid" ] && [ -n "$g_mid" ] || die "could not read the GPU addon's files back: $g_fail"
    {
        echo "$g_aid $GPU_ADDON"
        echo "$g_tid $GPU_TRUST"
        echo "$g_mid manifest.json"
    } > "$g_x/ids.changes" && ids_set "$STAGE/image.ids" "$g_x/ids.changes" > "$g_x/image.ids" &&
        mv -f "$g_x/image.ids" "$STAGE/image.ids" || die "could not rewrite image.ids: $g_fail"
    [ -n "$T" ] || sync
    rm -rf "$g_w" "$g_w.tmp" "$g_x"
    gpu_say placed "kernel.kc.gpuaddon $g_asha ($g_abytes bytes), owner-trust.json $g_tsha"
}

do_finish_kernel() {
    [ $# -eq 2 ] || [ $# -eq 4 ] || usage "finish kernel <kc-sha256> <build-id> [kb-<BUILD> <xnu path>]"
    kc=$1 bid=$2
    is_hex64 "$kc" || usage "finish: kernel SHA-256"
    is_bid "$bid" || usage "finish: kernel build id"
    if [ $# -eq 4 ]; then
        # Another Apple build's kernel (iOS 27.2.1, 24B156): its inputs folder
        # and the runtime's xnu for it; only for an image set of that build.
        case "$3" in kb-*) ;; *) usage "finish: '$3' is not kb-<BUILD>" ;; esac
        kbd_ok "$3" >/dev/null || usage "finish: '$3' is not kb-<BUILD>"
        case "$4" in kernel/*/xnu.macho) ;; *) usage "finish: '$4' is not a kernel/<dir>/xnu.macho path" ;; esac
        is_path "$4" || usage "finish: xnu path '$4'"
        KB_DIR=$3 KB_XNU=$4
    fi
    stage_ok
    session_open && refuse "an iOS session is running: return to One UI first"
    [ -f "$STAGE/runtime.conf" ] && mine "$STAGE/runtime.conf" || refuse "no OneiOS runtime is staged"
    if [ -n "$KB_DIR" ]; then
        ib=$(conf "$STAGE/image.conf" build 2>/dev/null)
        [ "$ib" = "${KB_DIR#kb-}" ] || refuse "the staged image set is ${ib:-unknown}, not ${KB_DIR#kb-}: a kernel built from $KB_DIR must never boot it"
    fi
    out="$STAGE/make-kernel/out"
    kc_check_prebuilt "$out" || refuse "no phone-built kernel is staged in $out: run the kernel build first"
    rm -rf "$out/tmp"
    [ "$(sha "$out/kernel.kc")" = "$kc" ] || refuse "the built kernel.kc is not $kc: run the kernel build again"
    why=$(kc_check_inputs "$out") || refuse "$why"
    kb="$STAGE/kernel-build/$bid"
    [ ! -L "$kb" ] || refuse "$kb is a link"
    rm -rf "$kb" && mkdir -p "$kb" && own "$kb" 0700 || die "could not make $kb"
    for f in kernel.kc.build.json kernel.kc.prelink.json kernel.kc.binds.json; do
        cp -p "$out/$f" "$kb/$f" && own "$kb/$f" 0600 || die "could not keep $f"
    done
    oldsha=$(awk '$2 == "kernel.kc" { print $1 }' "$STAGE/image.sha256" 2>/dev/null | head -n 1)
    oldbid=$(conf "$STAGE/image.conf" kernel_build_id 2>/dev/null)
    case "$oldbid" in ''|-*) oldbid="unknown" ;; esac
    kc_backup "$STAGE/kernel.prev" || die "could not set the old set aside"
    why=$(kc_activate "$out" "$kc" "$bid") || die "$why"
    ic="$STAGE/image.conf"
    {
        grep -v '^kernel_build_id=\|^kernel_kc_sha256=' "$ic"
        echo "kernel_build_id=$bid"
        echo "kernel_kc_sha256=$kc"
    } > "$ic.new" && own "$ic.new" 0600 && mv -f "$ic.new" "$ic" || die "could not write image.conf"
    # The A56's GPU addon, for an iOS 16.5 set only (its @@RESULT a56-gpu line; nothing for iOS 27).
    a56_gpu_place
    { [ -d "$STAGE/logs" ] || mkdir "$STAGE/logs"; } && own "$STAGE/logs" 0700 || die "could not make $STAGE/logs"
    name=$(kc_receipt update "${oldsha:-unknown}" "$oldbid" "$kc" "$bid") || die "could not write the receipt"
    [ -z "$GPU_LINE" ] || echo "a56 gpu: $GPU_LINE" >> "$STAGE/logs/$name.log" || die "could not write the receipt"
    [ -n "$T" ] || sync
    rm -rf "$out"
    say "@@OK finish kernel $bid (receipt logs/$name.log)"
}

do_restore_kernel() {
    [ $# -eq 1 ] && [ "$1" = kernel ] || usage "restore kernel"
    stage_ok
    session_open && refuse "an iOS session is running: return to One UI first"
    prev="$STAGE/kernel.prev"
    [ -d "$prev" ] && mine "$prev" || refuse "no previous kernel set is kept: nothing to restore"
    for f in kernel.kc kernel.kc.hashes manifest.json image.sha256 image.ids image.conf; do
        [ -f "$prev/$f" ] && [ ! -L "$prev/$f" ] && mine "$prev/$f" || refuse "the kept set lacks $f: stage the image set again"
    done
    kc=$(awk '$2 == "kernel.kc" { print $1 }' "$prev/image.sha256" 2>/dev/null | head -n 1)
    is_hex64 "$kc" || refuse "the kept set names no kernel.kc: stage the image set again"
    bid=$(awk -F= '$1 == "kernel_build_id" { print $2 }' "$prev/image.conf" 2>/dev/null | head -n 1)
    case "$bid" in ''|-*|*[!A-Za-z0-9._-]*) bid="unknown" ;; esac
    [ "$(sha "$prev/kernel.kc")" = "$kc" ] || refuse "the kept kernel.kc does not match its list: stage the image set again"
    for f in kernel.kc.hashes manifest.json; do
        [ "$(sha "$prev/$f")" = "$(awk -v p="$f" '$2 == p { print $1 }' "$prev/image.sha256" | head -n 1)" ] ||
            refuse "the kept set's $f does not match its list: stage the image set again"
    done
    # The GPU addon and owner-trust.json as the kept set had them (gpu.kept; a set kept by an app before it
    # has none, and then both stay as they are, as before).
    gpu=0
    if [ -f "$prev/gpu.kept" ]; then
        mine "$prev/gpu.kept" || refuse "the kept set's gpu.kept is not root's: stage the image set again"
        gpu=1
        while read -r g_how g_p || [ -n "$g_how" ]; do
            case "$g_how $g_p" in
                "kept $GPU_TRUST"|"kept $GPU_ADDON")
                    g_b="$prev/${g_p##*/}"
                    [ -f "$g_b" ] && [ ! -L "$g_b" ] && mine "$g_b" || refuse "the kept set lacks ${g_p##*/}: stage the image set again"
                    [ "$(sha "$g_b")" = "$(awk -v p="$g_p" '$2 == p { print $1 }' "$prev/image.sha256" | head -n 1)" ] ||
                        refuse "the kept set's ${g_p##*/} does not match its list: stage the image set again" ;;
                "none $GPU_TRUST"|"none $GPU_ADDON")
                    [ "$(list_count "$prev/image.sha256" "$g_p")" = 0 ] || refuse "the kept set lists $g_p but did not keep it: stage the image set again" ;;
                *) refuse "the kept set's gpu.kept is not as expected: stage the image set again" ;;
            esac
        done < "$prev/gpu.kept"
    fi
    oldsha=$(awk '$2 == "kernel.kc" { print $1 }' "$STAGE/image.sha256" 2>/dev/null | head -n 1)
    oldbid=$(conf "$STAGE/image.conf" kernel_build_id 2>/dev/null)
    case "$oldbid" in ''|-*) oldbid="unknown" ;; esac
    cur="$STAGE/kernel.cur-$$"
    rm -rf "$cur" && mkdir "$cur" && own "$cur" 0700 || die "could not make $cur"
    # The live set aside, the kept one in, the lists rewritten for the kept
    # files; the set aside becomes the new fallback, so a restore is
    # itself restorable.
    for f in kernel.kc kernel.kc.hashes manifest.json; do
        mv -f "$STAGE/image/$f" "$cur/$f" || die "could not move the live $f aside"
    done
    for f in image.sha256 image.ids image.conf; do
        mv -f "$STAGE/$f" "$cur/$f" || die "could not move the live $f aside"
    done
    for f in kernel.kc kernel.kc.hashes manifest.json; do
        mv -f "$prev/$f" "$STAGE/image/$f" || die "could not put the kept $f back"
    done
    for f in image.sha256 image.ids image.conf; do
        mv -f "$prev/$f" "$STAGE/$f" || die "could not put the kept $f back"
    done
    for f in kernel.kc kernel.kc.hashes manifest.json image.sha256 image.ids image.conf; do
        mv -f "$cur/$f" "$prev/$f" || die "could not keep the fallback"
    done
    if [ $gpu = 1 ]; then
        # The live GPU files aside (recorded, so the new fallback has them too), the kept ones in.
        printf '' > "$cur/gpu.kept" || die "could not keep the fallback"
        for g_p in "$GPU_TRUST" "$GPU_ADDON"; do
            if [ -f "$STAGE/image/$g_p" ] && [ ! -L "$STAGE/image/$g_p" ]; then
                mv -f "$STAGE/image/$g_p" "$cur/${g_p##*/}" || die "could not move the live ${g_p##*/} aside"
                echo "kept $g_p" >> "$cur/gpu.kept"
            else
                echo "none $g_p" >> "$cur/gpu.kept"
            fi
        done
        while read -r g_how g_p || [ -n "$g_how" ]; do
            [ "$g_how" = kept ] || continue
            g_d="$STAGE/image/$g_p"
            { [ -d "${g_d%/*}" ] || mkdir -p "${g_d%/*}"; } && mv -f "$prev/${g_p##*/}" "$g_d" && own "$g_d" 0644 ||
                die "could not put the kept ${g_p##*/} back"
            echo "$(file_id "$g_d") $g_p" >> "$cur/ids.changes"
        done < "$prev/gpu.kept"
        for g_p in "$GPU_TRUST" "$GPU_ADDON"; do
            [ ! -f "$cur/${g_p##*/}" ] || mv -f "$cur/${g_p##*/}" "$prev/${g_p##*/}" || die "could not keep the fallback"
        done
        own "$cur/gpu.kept" 0600 && mv -f "$cur/gpu.kept" "$prev/gpu.kept" || die "could not keep the fallback"
    fi
    # The kept list's ids are those of the files before kc_backup copied them: the files now in the image are
    # the copies (other inodes), so their ids are set again (their sums were checked above).
    for f in kernel.kc kernel.kc.hashes manifest.json; do
        echo "$(file_id "$STAGE/image/$f") $f" >> "$cur/ids.changes"
    done
    ids_set "$STAGE/image.ids" "$cur/ids.changes" > "$cur/image.ids" && mv -f "$cur/image.ids" "$STAGE/image.ids" ||
        die "could not rewrite image.ids"
    rm -f "$cur/ids.changes"
    rmdir "$cur" 2>/dev/null
    name=$(kc_receipt restore "${oldsha:-unknown}" "$oldbid" "$kc" "$bid") || die "could not write the receipt"
    [ -n "$T" ] || sync
    say "@@OK restore kernel $bid (receipt logs/$name.log)"
}

do_switch() {
    [ $# -eq 2 ] || [ $# -eq 3 ] || usage "switch <versionCode> <ack> [hosted|takeover]"
    # The Android takeover's toggle (docs/oneios.md, "Android takeover"): only takeover is passed on; hosted, or no
    # third word, passes nothing, so a session-mode= in the image's xnuhost.conf still decides.
    SMODE=""
    case "${3:-hosted}" in hosted) ;; takeover) SMODE=takeover ;; *) usage "switch: the session mode is hosted or takeover" ;; esac
    # (Exported only for the takeover: a hosted switch runs with exactly the environment it always had.)
    [ -z "$SMODE" ] || { ONEIOS_SESSION_MODE=$SMODE; export ONEIOS_SESSION_MODE; }
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
    [ -z "$SMODE" ] || { ONEIOS_SESSION_MODE=$SMODE; export ONEIOS_SESSION_MODE; }
    # The app's versionCode (is_dec above), for xnuhost's versions: line (OneiOS docs/booter.md 2.9b).
    ONEIOS_APP_VERSION_CODE=$1; export ONEIOS_APP_VERSION_CODE
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
    # The tool's lines as they come, so the app shows them while it runs (a GPU check takes up to two minutes):
    # once a second, whole lines only, each "| "-prefixed and cut at 2000 characters, at most 20000 of them. The
    # loop ends with the tool (a zombie's cmdline is empty, so check_is_tool fails); the rest after the wait.
    sent=0
    check_flush() { # [all]: the log's lines after the first $sent; with all, the last one without its newline too
        n=$(wc -l < "$log" 2>/dev/null)
        [ "$1" = all ] && n=$((n + 1))
        [ "$n" -gt "$sent" ] 2>/dev/null || return 0
        [ "$sent" -ge 20000 ] || sed -n "$((sent + 1)),${n}p" "$log" | head -n $((20000 - sent)) | cut -c1-2000 | sed 's/^/| /'
        sent=$n
    }
    while check_is_tool "$pid"; do
        sleep 1
        check_flush
    done
    wait "$pid"
    rc=$?
    kill "$dog" 2>/dev/null
    timed=0
    [ ! -e "$CHECKS/timeout" ] || timed=1
    check_flush all
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
    # One grep over every command line (a fork per process would take seconds on the phone). The arguments are
    # NUL-separated there, so the match is the path; a process is the tool's when its command line also says serve.
    found=
    for f in $(grep -l -F -- "$TOOL_BIN" /proc/[0-9]*/cmdline 2>/dev/null); do
        p=${f#/proc/}
        p=${p%/cmdline}
        [ "$p" = "$$" ] && continue
        { tr '\0' ' ' < "$f"; } 2>/dev/null | grep -q -F "$TOOL_BIN serve" && found="$found $p"
    done
    [ -n "$found" ] || return 0
    # Their children, four levels down (the parent is field 4 of /proc/PID/stat; a name with spaces sits in (...)).
    all="$found "
    for level in 1 2 3 4; do
        for s in /proc/[0-9]*/stat; do
            { read -r l < "$s"; } 2>/dev/null || continue
            pid=${l%% *}
            rest=${l##*) }
            ppid=${rest#* }
            ppid=${ppid%% *}
            case "$all" in *" $pid "*) ;; *" $ppid "*) all="$all$pid " ;; esac
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
    # Up to 2 s for them to go (only the processes found: no second scan of /proc), then SIGKILL.
    n=0
    while [ $n -lt 20 ]; do
        left=
        for p in $pids; do [ -d "/proc/$p" ] && left="$left $p"; done
        [ -n "$left" ] || break
        sleep 0.1
        n=$((n + 1))
    done
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
        update-[0-9]*)
            rest=${1#update-}
            case "$rest" in
                *-*) is_dec "${rest%-*}" && is_dec "${rest#*-}" || usage "'$1' is not an update receipt" ;;
                *) is_dec "$rest" || usage "'$1' is not an update receipt" ;;
            esac
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
        for id in $(ls -1 "$STAGE/logs" 2>/dev/null | sed -n 's/^\(update-[0-9][0-9]*\(-[0-9][0-9]*\)\{0,1\}\)\.log$/\1/p' | sort -r | head -n 5); do
            log_row "$id"
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
    kbinput) do_kbinput "$@" ;;
    kbcache) do_kbcache "$@" ;;
    kbclean) do_kbclean "$@" ;;
    finish) do_finish "$@" ;;
    restore) do_restore_kernel "$@" ;;
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
    *) usage "oneios_root.sh status|begin|receive|script|kbinput|kbcache|kbclean|finish|restore|switch|return|remove|check|uncheck|checkfile|logs|logfile|tool|untool" ;;
esac
