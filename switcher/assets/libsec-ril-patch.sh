#!/system/bin/sh
# Inbound SMS in the guest (0.4.61).
#
# Samsung's rild does not hand a new SMS to the RIL socket until its own
# framework sends the FW_READY vendor configuration over Samsung's HIDL radio
# interface. Until then SecRilProxy::OnUnsolicitedResponse keeps the new-SMS
# unsolicited response (Samsung ID 2201003) in its pending list, so the modem
# log shows "Received New GW SMS Message" while the guest's AOSP RILJ never
# gets UNSOL_RESPONSE_NEW_SMS.
#
# An AOSP guest's phone process has no Samsung HIDL client and cannot send
# FW_READY. This script makes the vendor library take the direct (post-FW_READY)
# path for the session: it NOPs the branch that checks the enable flag in
# SecRilProxy::OnUnsolicitedResponse, bind-mounts the copy over
# /vendor/lib64/libsec-ril.so, and restarts rild and multiclientd so the new
# library is loaded. return_to_oneui.sh calls "restore" before its stage-mount
# check, which would otherwise fail on the bind's source path.
#
# The patch is found by its exact instruction sequence, not by a version hash:
# a library without the sequence is left alone (and inbound SMS stays as it was,
# which is broken). The sequence is:
#   a8 06 40 f9   ldr  x8, [x21, #8]
#   08 05 44 39   ldrb w8, [x8, #0x101]
#   a8 01 00 34   cbz  w8, <queue>       <- replaced with 1f 20 03 d5 (nop)
#   08 48 88 52   mov  w8, #0xf4240
#   e8 01 a0 72
#   9f 03 08 6b   cmp  w28, w8
#
# 0.4.65: the S23 family's library (SM8550, S918BXXUAGZIF) loads the object
# from x20 (88 06 40 f9) instead of x21, so the sequence above is not there
# and the guest got no SMS (0.4.62 S23+ 43ca7db8). When it is not found, the
# same check from the ldrb on is looked for instead (the 20 bytes from
# 08 05 44 39 to 9f 03 08 6b, the cbz the fourth word): its first 6 bytes by
# grep (a shell pattern holds no zero byte), then all 20 read back at each hit.
#
# Usage: libsec-ril-patch.sh apply|restore
# Both are idempotent. Run as root; the script moves itself into init's mount
# namespace, where the vendor mount and rild live.

STAGE="${ONEOS_STAGE:-/data/local/tmp/oneos}"
LIB="${ONEOS_RIL_LIB:-/vendor/lib64/libsec-ril.so}"
SESSION="$STAGE/session"
PATCHED="$SESSION/libsec-ril.session.so"
MARKER="$SESSION/ril_patch.active"
# The original sequence and the patched form, as grep -F patterns (no newline).
ORIG_PAT="$(printf '\250\006\100\371\010\005\104\071\250\001')"
# Patched: the ldrb followed by the nop (either form of the load before it).
PATCHED_PAT="$(printf '\010\005\104\071\037\040\003\325')"
ALT_HEAD="$(printf '\010\005\104\071\250\001')"
ALT_HEX=08054439a801003408488852e801a0729f03086b

BB=""
for c in /data/adb/ksu/bin/busybox /data/adb/ap/bin/busybox /data/adb/magisk/busybox; do
    [ -x "$c" ] && { BB=$c; break; }
done
[ -n "$BB" ] || { echo "inbound SMS: no busybox at the root manager's paths"; exit 1; }

# The vendor mount and rild are in init's namespace. oneos_switch.sh and
# return_to_oneui.sh already run there; a manual run from a shell may not.
if [ "$(readlink /proc/self/ns/mnt 2>/dev/null)" != "$(readlink /proc/1/ns/mnt 2>/dev/null)" ]; then
    exec "$BB" nsenter -t 1 -m -- /system/bin/sh "$0" "$@"
fi

is_mounted() {
    "$BB" grep -Fq " $LIB " /proc/1/mountinfo 2>/dev/null
}

# The source path of the bind on LIB (field 4 of mountinfo), or empty.
mount_src() {
    "$BB" awk -v mp="$LIB" '$5 == mp { print $4; exit }' /proc/1/mountinfo 2>/dev/null
}

readn() { # <file> <offset> <count> -> lowercase hex digits
    "$BB" dd if="$1" bs=1 skip="$2" count="$3" 2>/dev/null | "$BB" od -An -tx1 | "$BB" tr -d ' \n'
}
read4() { readn "$1" "$2" 4; }

# 0.4.85: a library with neither sequence (the Galaxy A57's: all five of its reports from
# 0.4.61 on, and the guest gets no SMS there). For the next signature the log names the
# library and shows the code at each "flag byte, branch, compare with 1000000" place: the
# 16 bytes before a load of 1000000 (mov wN, #0x4240; movk wN, #0xf, lsl #16) when a byte
# load and a branch on zero are among them, and the 16 from it. Code bytes of the vendor's
# library, nothing of the user's. At most 200 places looked at, 8 shown.
MILLION_PAT="$(printf '\110\210\122')"
describe_lib() {
    echo "inbound SMS: $LIB is $("$BB" wc -c < "$LIB" 2>/dev/null) bytes, sha256 $("$BB" sha256sum "$LIB" 2>/dev/null | "$BB" cut -c1-64)"
    seen=0; shown=0
    for c in $(LC_ALL=C /system/bin/grep -aobF "$MILLION_PAT" "$LIB" 2>/dev/null | "$BB" cut -d: -f1 | "$BB" head -n 200); do
        case "$c" in ''|*[!0-9]*) continue ;; esac
        c=$((c - 1))
        [ "$c" -ge 16 ] && [ $((c % 4)) = 0 ] || continue
        case "$(readn "$LIB" "$c" 8)" in ??488852??01a072) ;; *) continue ;; esac
        seen=$((seen + 1))
        before=$(readn "$LIB" $((c - 16)) 16)
        rest=$before; cb=0; lb=0
        while [ -n "$rest" ]; do
            w=${rest%"${rest#????????}"}; [ -n "$w" ] || break
            rest=${rest#????????}
            case "$w" in ??????3[4-7]) cb=1 ;; ????[4-7]?39) lb=1 ;; esac
        done
        [ $cb = 1 ] && [ $lb = 1 ] && [ $shown -lt 8 ] || continue
        echo "inbound SMS: flag check before a compare with 1000000 at $c: $before | $(readn "$LIB" "$c" 16)"
        shown=$((shown + 1))
    done
    echo "inbound SMS: $seen loads of 1000000 looked at, $shown with a flag check before them"
}

restart_ril() {
    /system/bin/setprop ctl.restart ril-daemon 2>/dev/null
    /system/bin/setprop ctl.restart multiclient-daemon 2>/dev/null
}

apply() {
    [ -f "$LIB" ] || { echo "inbound SMS: $LIB is missing; not patching"; return 1; }
    if is_mounted; then
        case "$(mount_src)" in
            *libsec-ril.session.so)
                if /system/bin/grep -qaF "$PATCHED_PAT" "$LIB" 2>/dev/null; then
                    echo "inbound SMS: $LIB is already patched for this session"
                    [ -f "$MARKER" ] || { printf 'session\n' > "$MARKER" 2>/dev/null; chmod 600 "$MARKER" 2>/dev/null; }
                    return 0
                fi
                echo "inbound SMS: our bind on $LIB is not patched; removing it"
                "$BB" umount "$LIB" 2>/dev/null || "$BB" umount -l "$LIB" 2>/dev/null
                if is_mounted; then
                    echo "inbound SMS: could not remove the stale bind on $LIB; left alone"
                    return 1
                fi
                ;;
            *)
                echo "inbound SMS: $LIB is mounted from $(mount_src); not this patch, left alone"
                return 1
                ;;
        esac
    fi
    rm -f "$MARKER"
    # Toybox grep knows -b; busybox grep does not. Require exactly one match:
    # a future library with the sequence in more than one place is not ours to
    # guess at.
    # nop: the offset of the cbz to replace.
    n=$(LC_ALL=C /system/bin/grep -aobF "$ORIG_PAT" "$LIB" 2>/dev/null | "$BB" wc -l)
    if [ "$n" = 1 ]; then
        off=$(LC_ALL=C /system/bin/grep -aobF "$ORIG_PAT" "$LIB" 2>/dev/null | "$BB" head -n 1 | "$BB" cut -d: -f1)
        case "$off" in
            ''|*[!0-9]*) echo "inbound SMS: could not read the match offset in $LIB; left alone"; return 1 ;;
        esac
        nop=$((off + 8))
    elif [ "$n" = 0 ]; then
        hits=""; m=0
        for c in $(LC_ALL=C /system/bin/grep -aobF "$ALT_HEAD" "$LIB" 2>/dev/null | "$BB" cut -d: -f1); do
            case "$c" in ''|*[!0-9]*) continue ;; esac
            [ "$(readn "$LIB" "$c" 20)" = "$ALT_HEX" ] && { hits=$c; m=$((m + 1)); }
        done
        [ "$m" = 1 ] || {
            echo "inbound SMS: found 0 matches for the rild SMS queue sequence and $m for its check from the ldrb on in $LIB; left alone"
            describe_lib
            return 1
        }
        off=$hits
        nop=$((off + 4))
        echo "inbound SMS: the SMS queue check found from the ldrb on at $off (another register before it)"
    else
        echo "inbound SMS: found $n matches for the rild SMS queue sequence in $LIB; left alone"
        return 1
    fi
    "$BB" mkdir -p "$SESSION" || { echo "inbound SMS: no $SESSION"; return 1; }
    rm -f "$PATCHED"
    "$BB" cp -f "$LIB" "$PATCHED" || { echo "inbound SMS: could not copy $LIB"; return 1; }
    printf '\037\040\003\325' | "$BB" dd of="$PATCHED" bs=1 seek=$nop conv=notrunc 2>/dev/null ||
        { echo "inbound SMS: could not write the nop at $nop"; rm -f "$PATCHED"; return 1; }
    got=$(read4 "$PATCHED" $nop)
    [ "$got" = "1f2003d5" ] || {
        echo "inbound SMS: the patched copy reads $got at $off, not 1f2003d5; left alone"
        rm -f "$PATCHED"
        return 1
    }
    chmod 644 "$PATCHED"
    "$BB" mount --bind "$PATCHED" "$LIB" || {
        echo "inbound SMS: could not bind $PATCHED over $LIB"
        rm -f "$PATCHED"
        return 1
    }
    if ! is_mounted || [ "$(read4 "$LIB" $nop)" != "1f2003d5" ]; then
        echo "inbound SMS: the bind mount on $LIB did not take; removing it"
        "$BB" umount "$LIB" 2>/dev/null
        rm -f "$PATCHED"
        return 1
    fi
    printf 'session %s\n' "$off" > "$MARKER" || {
        echo "inbound SMS: could not write $MARKER; removing the bind"
        "$BB" umount "$LIB" 2>/dev/null
        rm -f "$PATCHED"
        return 1
    }
    chmod 600 "$MARKER"
    restart_ril
    echo "inbound SMS: patched $LIB at $off for this session (rild restarted)"
    return 0
}

restore() {
    # A bind from this script is ours even if the marker was lost (a stage
    # update, a crash); the mount's source name is unique to this script.
    src=$(mount_src)
    if [ -n "$src" ]; then
        case "$src" in
            *libsec-ril.session.so) ;;
            *)
                echo "inbound SMS: $LIB is mounted from $src, not this patch; left alone"
                return 1
                ;;
        esac
    elif [ ! -f "$MARKER" ]; then
        return 0
    fi
    if is_mounted; then
        "$BB" umount "$LIB" 2>/dev/null || "$BB" umount -l "$LIB" 2>/dev/null
        if is_mounted; then
            echo "inbound SMS: $LIB is still bind-mounted; leaving it for the next return"
            return 1
        fi
        restart_ril
        echo "inbound SMS: removed the vendor RIL patch from $LIB (rild restarted)"
    fi
    rm -f "$MARKER" "$PATCHED"
    return 0
}

case "$1" in
    apply) apply ;;
    restore) restore ;;
    *) echo "usage: $0 apply|restore"; exit 2 ;;
esac
