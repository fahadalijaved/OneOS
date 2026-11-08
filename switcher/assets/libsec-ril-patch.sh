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
PATCHED_PAT="$(printf '\250\006\100\371\010\005\104\071\037\040\003\325')"

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

read4() { # <file> <offset> -> 8 lowercase hex digits
    "$BB" dd if="$1" bs=1 skip="$2" count=4 2>/dev/null | "$BB" od -An -tx1 | "$BB" tr -d ' \n'
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
    n=$(LC_ALL=C /system/bin/grep -aobF "$ORIG_PAT" "$LIB" 2>/dev/null | "$BB" wc -l)
    [ "$n" = 1 ] || {
        echo "inbound SMS: found $n matches for the rild SMS queue sequence in $LIB; left alone"
        return 1
    }
    off=$(LC_ALL=C /system/bin/grep -aobF "$ORIG_PAT" "$LIB" 2>/dev/null | "$BB" head -n 1 | "$BB" cut -d: -f1)
    case "$off" in
        ''|*[!0-9]*) echo "inbound SMS: could not read the match offset in $LIB; left alone"; return 1 ;;
    esac
    "$BB" mkdir -p "$SESSION" || { echo "inbound SMS: no $SESSION"; return 1; }
    rm -f "$PATCHED"
    "$BB" cp -f "$LIB" "$PATCHED" || { echo "inbound SMS: could not copy $LIB"; return 1; }
    printf '\037\040\003\325' | "$BB" dd of="$PATCHED" bs=1 seek=$((off + 8)) conv=notrunc 2>/dev/null ||
        { echo "inbound SMS: could not write the nop at $off"; rm -f "$PATCHED"; return 1; }
    got=$(read4 "$PATCHED" $((off + 8)))
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
    if ! is_mounted || [ "$(read4 "$LIB" $((off + 8)))" != "1f2003d5" ]; then
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
