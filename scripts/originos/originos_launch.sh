#!/system/bin/sh
# OriginOS over adb (not in the OneOS app, never released): one session from the
# stage's session.env, as the owner's /data/local/tmp/originos_launch.sh on the Z
# Fold8 Ultra did since the seventh run. Run as root, after a fresh, direct yes from
# the owner:  adb shell 'su -c "sh /data/local/tmp/originos_launch.sh"'
# The switch runs in init's mount namespace, in its own session, so it outlives the
# adb shell; its output goes to $STAGE/takeover_adb.log. Back to One UI: Volume Up +
# Volume Down for 3 s, or the auto-return.
STAGE=/data/local/tmp/oneos
LOG="$STAGE/takeover_adb.log"
[ "$(id -u)" = 0 ] || { echo "originos_launch: run it as root (su -c)"; exit 1; }
for f in oneos_switch.sh guest_prepare.sh guest_start.sh guest_props.sh session.env guards.txt system.raw; do
    [ -f "$STAGE/$f" ] || { echo "originos_launch: $STAGE/$f is missing"; exit 1; }
done
grep -q ' vivo-services_patched\.jar$' "$STAGE/guards.txt" ||
    { echo "originos_launch: $STAGE is not an OriginOS stage (no vivo-services_patched.jar in guards.txt)"; exit 1; }
# The app's own session.env (ONEOS_APP=1) belongs to an app stage; an adb run uses its own.
grep -qx 'ONEOS_APP=1' "$STAGE/session.env" && { echo "originos_launch: session.env is the OneOS app's (ONEOS_APP=1)"; exit 1; }
grep -q '^ONEOS_PROFILE=[a-z0-9-]*$' "$STAGE/session.env" || { echo "originos_launch: session.env names no ONEOS_PROFILE"; exit 1; }
if grep -q " $STAGE/rootfs " /proc/mounts; then echo "originos_launch: a session is running (rootfs mounted)"; exit 1; fi
BB=/data/adb/ksu/bin/busybox
[ -x "$BB" ] || BB=$(command -v busybox)
[ -n "$BB" ] || { echo "originos_launch: no busybox"; exit 1; }
echo "=== adb launch OriginOS $(date '+%F %T') epoch $(date +%s) ===" >> "$LOG"
"$BB" nsenter -t 1 -m "$BB" setsid /system/bin/sh -c \
    'set -a; . /data/local/tmp/oneos/session.env; set +a; exec /system/bin/sh /data/local/tmp/oneos/oneos_switch.sh' \
    </dev/null >> "$LOG" 2>&1 &
echo "originos_launch: started ($(grep '^ONEOS_PROFILE=' "$STAGE/session.env")); log: $LOG"
