#!/system/bin/sh
# The root manager's own busybox (as oneos_switch.sh checked), never a
# search of /data; after the pivot the guest's copy in its /data.
BB=""
for c in /data/adb/ksu/bin/busybox /data/adb/ap/bin/busybox /data/adb/magisk/busybox; do
    [ -x "$c" ] && { BB=$c; break; }
done
[ -n "$BB" ] || [ "${ONEOS_APP:-0}" = 1 ] || BB=$(command -v busybox 2>/dev/null)
[ -n "$BB" ] || { echo "[Pivoted Root] FATAL: no busybox. Not starting the guest."; exit 1; }

echo "[Pivoted Root] Preparing pivot..."
cd /data/local/tmp/oneos/rootfs
$BB mount --make-rprivate /
if ! $BB pivot_root . postinstall; then
    echo "[Pivoted Root] Fallback: bind mounting rootfs onto itself..."
    $BB mount --bind . .
    if ! $BB pivot_root . postinstall; then
        echo "[Pivoted Root] FATAL: pivot_root failed completely! Aborting."
        exit 1
    fi
fi
# OneOS: guest_prepare.sh copied busybox into the guest /data, so nothing below
# (nor the keepers started from here) runs it from host /data/adb, which the
# guest sees read-only. The file keeps the name busybox: a multi-call busybox
# takes its applet from argv[0] and only reads it from argv[1] when it is called
# busybox (run 36a: /data/oneos_busybox answered every call 'applet not found').
/data/oneos_bin/busybox true 2>/dev/null && BB=/data/oneos_bin/busybox
echo "[Pivoted Root] busybox: $BB"
ONEOS_BOOT_DIR=/data/oneos_bootui
[ ! -f "$ONEOS_BOOT_DIR/boot_status.sh" ] || . "$ONEOS_BOOT_DIR/boot_status.sh"
$BB mount -t proc proc /proc
# OneOS: the kernel is the phone's. No sysrq from the guest (its watchdog
# writes 'c' to crash the kernel; the framework patch stops that too).
if $BB mount --bind /dev/null /proc/sysrq-trigger 2>/dev/null; then
    echo "[Pivoted Root] /proc/sysrq-trigger hidden from the guest"
else
    echo "[Pivoted Root] FATAL: could not hide /proc/sysrq-trigger. Not starting the guest."
    exit 1
fi
# OneOS: pivot_root left the host's whole old root at /postinstall, including
# vold's bind of the phone's real /data/media and every unbridged /data tree.
# Nothing in the guest needs it (this namespace is rprivate, so this does not
# touch the host).
$BB umount -l /postinstall 2>/dev/null
if awk '$5 ~ "^/postinstall(/|$)"' /proc/self/mountinfo | grep -q .; then
    echo "[Pivoted Root] FATAL: host mounts still under /postinstall. Not starting the guest."
    exit 1
fi
echo "[Pivoted Root] Host root detached from /postinstall"

export PATH=/system/bin:/system/xbin

# OneOS: /mnt and /storage came in from the host, and its pass_through,
# installer, androidwritable, runtime and user views are binds of the phone's
# real /data/media. Drop them in this (private) namespace before anything in
# the guest runs; the guest builds its own from its staged /data/media below.
for m in $(awk '$5 ~ "^/(mnt/(pass_through|installer|androidwritable|runtime|user)|storage)(/|$)" {print $5}' /proc/self/mountinfo | sort -r); do
    $BB umount -l "$m" 2>/dev/null
done
left=$(awk '$5 ~ "^/(mnt/(pass_through|installer|androidwritable|runtime|user)|storage)(/|$)"' /proc/self/mountinfo | wc -l)
if [ "$left" != 0 ]; then
    echo "[Pivoted Root] FATAL: $left host storage views still mounted. Not starting the guest."
    exit 1
fi
echo "[Pivoted Root] Host storage views removed from the guest namespace"
# Rebuild the installer and androidwritable views the way init does, over the
# guest's own /mnt/user (zygote binds /mnt/installer/0 for apps that can
# install packages). /mnt is private to this namespace, so the new peer group
# is the guest's alone.
mkdir -p /mnt/user/0 /mnt/installer /mnt/androidwritable
$BB mount --make-shared /mnt
for v in installer androidwritable; do
    $BB mount --rbind /mnt/user /mnt/$v && $BB mount --make-rslave /mnt/$v
done

echo "[Pivoted Root] Setting up /data_mirror and /data/data mounts for Zygote isolation..."
$BB mount --bind /data/user/0 /data/data 2>/dev/null || true
$BB mount -t tmpfs tmpfs /data_mirror 2>/dev/null || true
mkdir -p /data_mirror/data_de/null/0 /data_mirror/data_ce/null/0 /data_mirror/cur_profiles /data_mirror/ref_profiles
chmod -R 777 /data_mirror
$BB mount --bind /data/user_de/0 /data_mirror/data_de/null/0 2>/dev/null || true
$BB mount --bind /data/user/0 /data_mirror/data_ce/null/0 2>/dev/null || true
mkdir -p /data/misc/profiles/cur /data/misc/profiles/ref
$BB mount --bind /data/misc/profiles/cur /data_mirror/cur_profiles 2>/dev/null || true
$BB mount --bind /data/misc/profiles/ref /data_mirror/ref_profiles 2>/dev/null || true

echo "[Pivoted Root] Setting up /data/media and emulated storage..."
mkdir -p /data/media/0/Android /data/media/0/Pictures/Screenshots /data/media/0/Download /data/media/0/DCIM /data/media/0/Documents
chown -R 1023:1023 /data/media 2>/dev/null || true
chmod -R 777 /data/media 2>/dev/null || true
$BB mount -t tmpfs tmpfs /storage 2>/dev/null || true
mkdir -p /storage/emulated/0
$BB mount --bind /data/media/0 /storage/emulated/0 2>/dev/null || true
mkdir -p /mnt/user/0
$BB mount -t tmpfs tmpfs /mnt/user/0 2>/dev/null || true
mkdir -p /mnt/user/0/emulated
$BB mount --bind /data/media/0 /mnt/user/0/emulated 2>/dev/null || true

echo "[Pivoted Root] Rootfs successfully activated as /"
# oneos_switch.sh's TMPDIR ($STAGE/tmp) is not a path of the pivoted
# root; mksh would fail a long here-document with it (see there). The
# guest's /data/local/tmp is the stage's own, made by guest_prepare.sh.
mkdir -p /data/local/tmp 2>/dev/null
export TMPDIR=/data/local/tmp

# Class paths. This shell inherits the HOST's BOOTCLASSPATH and
# SYSTEMSERVERCLASSPATH (One UI's, with Samsung jars such as knoxanalyticssdk
# and semwifi-service). init normally runs derive_classpath and load_exports
# them; nothing does that in the container, so the guest zygote got the host's
# list. Lineage survived that, but ColorOS's libhwui aborts zygote looking for
# com/oplus/media/OplusBitmapChecker, which lives in oplus-framework.jar on
# ColorOS's own boot class path. Derive the guest's lists the way init does.
DERIVE=/apex/com.android.sdkext/bin/derive_classpath
CLASSPATH_FILE=/data/system/environ/classpath
mkdir -p /data/system/environ
if [ -x "$DERIVE" ] && "$DERIVE" "$CLASSPATH_FILE" > /data/derive_classpath.log 2>&1; then
    while read -r kw name value; do
        [ "$kw" = "export" ] && [ -n "$name" ] && export "$name=$value"
    done < "$CLASSPATH_FILE"
    echo "[Pivoted Root] Guest class paths loaded from $CLASSPATH_FILE:"
    sed 's/^/[Pivoted Root]   /' "$CLASSPATH_FILE" | cut -c1-400
else
    echo "[Pivoted Root] WARNING: derive_classpath failed, zygote keeps the host's class paths"
    sed 's/^/[Pivoted Root]   /' /data/derive_classpath.log 2>/dev/null | head -5
fi

# OneOS: every guest process, not just zygote, needs the guest class paths:
# app_process tools (oplus_defrag's defrag_wrap, settings/cmd/am run by the
# switch through nsenter) aborted with "Unable to find class
# com/oplus/media/OplusBitmapChecker" on the host's. Derive them first, and
# leave /data/oneos_genv.sh for commands entered from the host side.
cat > /data/oneos_genv.sh <<'GENV'
#!/system/bin/sh
[ -f /data/system/environ/classpath ] && while read -r kw name value; do
    [ "$kw" = "export" ] && [ -n "$name" ] && export "$name=$value"
done < /data/system/environ/classpath
exec "$@"
GENV
chmod 755 /data/oneos_genv.sh
echo "[Pivoted Root] Testing /dev/null resolution:"
exec 8< /dev/null
echo -n "FD 8: "
$BB readlink /proc/$$/fd/8
exec 8<&-

echo "[Pivoted Root] Testing su availability:"
su -c id || echo "su check non-fatal"
# OneOS: what the guest gets of host /data/adb and /data/apex (guest_prepare.sh
# binds both read-only); a failure above or a write error later points here.
for d in /data/adb /data/apex; do
    echo "[Pivoted Root] $d: $(awk -v p="$d" '$5 == p {print $6}' /proc/self/mountinfo | tail -n 1)"
done

# Foldable layouts. The host's display_layout_configuration.xml is Samsung's.
# ColorOS's DeviceStateToLayoutMapExtImpl.updateRealDisplayAddressId
# (oplus-services.jar) reads each <display>'s <address> without a null check
# and, for every state but 0, looks it up in a map that only state 0's displays
# fill (it takes the display disabled in state 0 for the big panel and the
# enabled one for the small panel). Samsung's file breaks one of these rules,
# and the NPE took DisplayManagerService and system_server down during
# bootstrap. Hide it in this namespace only; once the guest SurfaceFlinger
# reports both panels, ONEOS_GUEST_FOLD=layout (the default) writes our own file
# into the copy (below, after the HW overlay switch).
# The file has to be absent, not empty: an empty <layouts/> enables no display
# at all and DisplayManagerService times out waiting for a default display. A
# copy of the directory without it keeps the per-panel display_id_*.xml.
DISPLAYCONFIG=/vendor/etc/displayconfig
LAYOUT_HIDDEN=0
rm -f /data/oneos_fold_mode /data/oneos_inner_display
if [ -f "$DISPLAYCONFIG/display_layout_configuration.xml" ] && [ "${ONEOS_KEEP_FOLD_LAYOUT:-0}" != "1" ]; then
    rm -rf /data/oneos_displayconfig && mkdir -p /data/oneos_displayconfig
    for f in "$DISPLAYCONFIG"/*; do
        [ "$(basename "$f")" = display_layout_configuration.xml ] || cp -p "$f" /data/oneos_displayconfig/
    done
    chmod 755 /data/oneos_displayconfig && chmod 644 /data/oneos_displayconfig/*
    $BB mount --bind /data/oneos_displayconfig "$DISPLAYCONFIG" && LAYOUT_HIDDEN=1 && \
        echo "[Pivoted Root] Fold layout config hidden from the guest ($(ls /data/oneos_displayconfig | wc -l) display configs kept)"
fi

# Gap splash (oneos_switch.sh): [4b/6] froze One UI's surfaceflinger
# (SIGSTOP) on the switcher's OneOS screen instead of killing it, so its
# composer client stayed and the panel kept that frame through the host-side
# setup (run 32: 31.6 s of black, 23 s of it guest_prepare.sh). Kill it now,
# before the composer restart: alive, it would come back through the composer's
# "onrestart restart surfaceflinger". From here to ColorOS's first frame was
# 4.3 s in run 32 (composer restart 13:09:51.94, first frame 13:09:56.18).
if [ -s /data/oneos_host_sf_frozen ]; then
    FZ=$(cat /data/oneos_host_sf_frozen)
    rm -f /data/oneos_host_sf_frozen
    setprop ctl.stop surfaceflinger
    [ "$(cat /proc/$FZ/comm 2>/dev/null)" = surfaceflinger ] && kill -9 "$FZ" 2>/dev/null
    n=0
    while [ $n -lt 20 ] && [ -d "/proc/$FZ" ]; do n=$((n + 1)); sleep 0.1; done
    echo "[Pivoted Root] Gap splash: One UI's frozen surfaceflinger $FZ released at $(date +%T) ($([ -d "/proc/$FZ" ] && echo 'still there' || echo gone))"
fi

# A guest restart retained its splash in the composer while installers ran.
# Thaw that exact compositor before restarting it for the new guest client.
command -v oneos_boot_release_display >/dev/null 2>&1 && oneos_boot_release_display

# The vendor composer still treats the killed host SurfaceFlinger as its client:
# every frame from the guest's came back NO_RESOURCES on both displays and the
# panel kept showing One UI's last frame. Restart it so the guest gets a fresh
# client.
# Snapdragon's composer service is vendor.qti.hardware.display.composer,
# Samsung's Exynos one vendor.hwcomposer-3 (Galaxy S26+ Exynos and Z Flip7
# probes, 2026-10-25). Not every phone uses one of those two names -- the
# Galaxy A56 probe (2026-10-30) runs the AIDL composer as
# android.hardware.graphics.composer3-service.exynos -- so when neither is
# there, take the running init service whose own name says it is the display
# composer rather than skip the restart (here) or fail the return
# (return_to_oneui.sh).
COMPOSER_SVC=""
for c in vendor.qti.hardware.display.composer vendor.hwcomposer-3; do
    [ -n "$(getprop init.svc.$c)" ] && { COMPOSER_SVC=$c; break; }
done
[ -n "$COMPOSER_SVC" ] || COMPOSER_SVC=$(getprop | "$BB" sed -n 's/^\[init\.svc\.\([^]]*\)\]: \[running\]$/\1/p' | "$BB" grep -m1 -E 'hwcomposer|display\.composer|graphics\.composer')
echo "[Pivoted Root] Restarting the vendor display composer (${COMPOSER_SVC:-none found})..."
# Stopped and started, not ctl.restart: init runs a service's onrestart
# commands only when it restarts it, and the composer's "onrestart restart
# surfaceflinger" brought One UI's surfaceflinger back. When that one
# registered with the new composer before it was killed below, it took the
# hotplug of every built-in panel but the primary: SDM creates and announces
# a built-in display once, and the guest's SurfaceFlinger, registering later,
# was only given the primary again (Z Fold7 report 1b88226a: "Builtin display
# created ... client id 3" to the dead One UI surfaceflinger, BR_DEAD_REPLY;
# no cover in the guest, so no fold layout, inner panel only, touch lost).
# ONEOS_COMPOSER_RESTART=restart keeps ctl.restart.
if [ -n "$COMPOSER_SVC" ]; then
    if [ "${ONEOS_COMPOSER_RESTART:-stopstart}" = restart ]; then
        setprop ctl.restart "$COMPOSER_SVC"
    else
        setprop ctl.stop "$COMPOSER_SVC"
        n=0
        while [ $n -lt 30 ] && [ "$(getprop init.svc.$COMPOSER_SVC)" != stopped ]; do n=$((n + 1)); sleep 0.1; done
        echo "[Pivoted Root] Composer stopped after $((n * 100)) ms ($(getprop init.svc.$COMPOSER_SVC)); started again without its onrestart"
        setprop ctl.start "$COMPOSER_SVC"
    fi
fi
# With the gap splash, the black that is left is from here to the first boot
# animation frame, and most of it was fixed sleeps. Run 33 (all.log): the
# splash's surfaceflinger died 14:41:22.70, the new composer had registered
# AidlComposer at 14:41:23.157, the host surfaceflinger its onrestart revived
# (14:41:22.998) was gone before it got a composer client, but this sleep 2 and
# the one after the guest's surfaceflinger below kept the panel black until the
# animation's first frame at 14:41:27.31 (4.6 s). So wait for the new composer
# instead: 0.5 s first (the old one must be gone, or service check finds its
# entry), then until it is registered, at most the old 2 s.
# ONEOS_GAP_FAST=0 (guest_prepare.sh: /data/oneos_gap_slow) keeps both sleeps.
if [ -f /data/oneos_gap_slow ]; then
    sleep 2
else
    sleep 0.5
    n=0
    while [ $n -lt 15 ] && ! service check android.hardware.graphics.composer3.IComposer/default 2>/dev/null | grep -q ': found'; do
        n=$((n + 1)); sleep 0.1
    done
    echo "[Pivoted Root] Composer registered after $((5 + n))00 ms"
fi
# The composer's rc has "onrestart restart surfaceflinger", which brings the
# HOST surfaceflinger back. Any surfaceflinger alive now is the host's (the
# guest's is started below), so stop it before it owns the display and the
# "SurfaceFlinger" service name. oneos_switch.sh keeps it stopped.
setprop ctl.stop surfaceflinger
n=0
while [ $n -lt 20 ] && pidof surfaceflinger >/dev/null; do
    kill -9 $(pidof surfaceflinger) 2>/dev/null
    n=$((n + 1)); sleep 0.1
done
echo "[Pivoted Root] Host surfaceflinger after composer restart: $(pidof surfaceflinger || echo none)"

# What the composer has to offer, recorded BEFORE the guest's SurfaceFlinger
# asks for it. The diag rounds in oneos_switch.sh all start from
# `pidof surfaceflinger`, so a guest SF that dies leaves no display diag at all:
# the Galaxy S24 Ultra report of 2026-10-30 aborted with "No matching frame rate
# modes for primary range" and its bundle had nothing to say why, while its
# One UI offers 21 modes (its probe the same day). This runs first and keeps the
# mode list whatever SF then does with it.
# Reads files, and one lshal bounded by timeout, on a composer that has just
# registered: no plain dumpsys and no service walk here, the host's
# system_server is frozen at this point (0.4.11 hung every switch that way).
# $STAGE is the host side's name for the stage; this script runs inside the
# pivoted root, where the stage's own /data IS /data. Write it where the log
# collector already looks: collect.list takes "$S"/data/*.log for every guest
# log (takeover.log and the rest), so one .log there needs no collector change.
CD=/data/oneos_composer_before_sf.log
{
    echo "== composer service ${COMPOSER_SVC:-none found}"
    [ -z "$COMPOSER_SVC" ] || echo "init.svc.$COMPOSER_SVC: $(getprop "init.svc.$COMPOSER_SVC")"
    service check android.hardware.graphics.composer3.IComposer/default 2>&1
    echo
    echo "== panel modes the kernel reports (/sys/class/drm)"
    for c in /sys/class/drm/card*-*; do
        [ -r "$c/modes" ] || continue
        echo "-- $(basename "$c") status=$(cat "$c/status" 2>/dev/null) enabled=$(cat "$c/enabled" 2>/dev/null)"
        cat "$c/modes" 2>/dev/null
    done
    echo
    echo "== vendor display configs (the file name is the display id it is for)"
    ls -l /vendor/etc/displayconfig /odm/etc/displayconfig 2>&1
    echo
    echo "== the composer's own dump"
    # An AIDL composer (every phone OneOS knows) answers dumpsys, not lshal
    # debug (HIDL only); one named service, bounded.
    timeout 5 dumpsys android.hardware.graphics.composer3.IComposer/default 2>&1 | head -n 400 ||
        echo "dumpsys of the composer: no answer in 5 s"
    if command -v lshal >/dev/null 2>&1; then
        timeout 5 lshal debug android.hardware.graphics.composer3.IComposer/default 2>&1 ||
            echo "lshal debug: no answer in 5 s"
    else
        echo "no lshal in this image"
    fi
} > "$CD" 2>&1

# Shader caches. init.rc makes /data/misc/surfaceflinger (0700 system system)
# and sets service.sf.cache_dir_available; the container has no init, so the
# guest's RenderEngine could not save one (run 32 all.log:276689, 39 times:
# "error creating cache file /data/misc/surfaceflinger/skia_shaders" and
# egl_shaders, "No such file or directory") and compiled every shader again in
# each session: a stutter the first time each blur, animation or window shape
# is drawn. This is the guest's own /data (the stage).
mkdir -p /data/misc/surfaceflinger && chown 1000:1000 /data/misc/surfaceflinger && chmod 0700 /data/misc/surfaceflinger
echo "[Pivoted Root] Starting guest SurfaceFlinger..."
# sf.log used to grow without bound: the guest's RenderEngine dumps LLVM IR for
# every shader it compiles ("Global Value @fullLiteral...") and got to 300+ MB in
# ~3 minutes, filling /data. SurfaceFlinger's real diagnostics go through logcat,
# so stderr can be dropped.
/system/bin/surfaceflinger > /dev/null 2>&1 &
SF_PID=$!
echo "[Pivoted Root] SurfaceFlinger PID: $SF_PID"
# The loop below already waits for the "SurfaceFlinger" service (5 s at most),
# and nothing else can hold that name now: the frozen host one died above and
# the revived one was killed before its init finished (run 33: it never got a
# composer client). Run 33's guest surfaceflinger was up 0.2 s after it started
# (14:41:25.337 -> power mode set 14:41:25.55), the fixed 2 s only delayed the
# boot animation (see the composer restart above).
if [ -f /data/oneos_gap_slow ]; then sleep 2; else sleep 0.5; fi

# Samsung's composer rejected ColorOS's surfaceflinger's command batches
# (executeCommands BAD_VALUE, presentOrValidate NO_RESOURCES on every frame:
# black panel). Disable hardware overlays (developer options "Disable HW
# overlays", SurfaceFlinger transaction 1008) so everything is GPU-composed
# and the composer only gets the client target buffer.
n=0
while [ $n -lt 25 ] && ! service check SurfaceFlinger 2>/dev/null | grep -q ": found"; do
    n=$((n + 1)); sleep 0.2
done
# /data/oneos_hwc (guest_prepare.sh) leaves the overlays on: the default since
# run 44 for guests without oplus-services.jar and since 0.4.76 for ColorOS
# (see there), ONEOS_GUEST_HWC=0 for GPU composition.
# The docs record that 1008 did not stop the rejected frames (run 23 still had
# 3890); the surfaceflinger patch that skips IQtiComposer3Client did, and the
# Pixel surfaceflinger has no such client. Forcing GPU composition is costly:
# every frame of the 2504x2256 panel goes through RenderEngine (run 32 diag_90
# surfaceflinger.txt: clientType=DEVOPTFORCECLIENT) and SurfaceFlinger counted
# 4800 GPU missed frames by 110 s (run 31: 5291 without window blur), about 45
# a second; run 43's Pixel about 2 a second (221 by diag_90).
if [ -f /data/oneos_hwc ]; then
    echo "[Pivoted Root] SurfaceFlinger HW overlays left on (the default; ONEOS_GUEST_HWC=0 for GPU composition)"
    # Run 44: should the composer reject the frames anyway (a black panel),
    # force GPU composition by itself instead of waiting for the return keys.
    # Its rejections (run 23's executeCommands / presentOrValidate lines)
    # since now are counted 5, 15 and 30 s on; past 30, transaction 1008 once.
    HWC_T0=$(date +%s)
    (
        n=0
        for w in 5 10 15; do
            sleep $w
            n=$(logcat -d -b main -s SurfaceFlinger:E -T "$HWC_T0.000" 2>/dev/null | grep -c -E 'executeCommands failed|presentOrValidate failed')
            if [ "$n" -gt 30 ]; then
                service call SurfaceFlinger 1008 i32 1 > /data/sf_1008.log 2>&1
                : > /data/oneos_hwc_forced
                echo "[Pivoted Root] composer rejected $n frames with HW overlays: GPU composition forced: $(cat /data/sf_1008.log)"
                exit 0
            fi
        done
        echo "[Pivoted Root] SurfaceFlinger HW overlays kept: $n composer rejections in the first 30 s"
    ) </dev/null 2>/dev/null &
else
    service call SurfaceFlinger 1008 i32 1 > /data/sf_1008.log 2>&1
    echo "[Pivoted Root] SurfaceFlinger HW overlays disabled: $(cat /data/sf_1008.log)"
fi

# Fold layout (see "Foldable layouts" above), like the Find N6: lid closed
# (Samsung's device state 0) puts ColorOS on the cover, lid open (3) on the
# inner panel; the other panel is switched off. State 0 comes first and lists
# both panels with the cover enabled: ColorOS maps addresses by that rule, so
# with the real ids its mapping is the identity. The ids come from the guest
# SurfaceFlinger: port 147 is the inner panel, 148 the cover (run 30; the Find
# N6's own overlay uses the same two ports). SurfaceFlinger keeps the port in
# the id's low byte, which is where DeviceStateToLayoutMap takes the port from
# when the file has no <port>. ONEOS_GUEST_FOLD=off: inner panel only (run 30).
# OneOS: the ports come from the host's touch-to-display associations
# (sec_touchscreen = inner, sec_touchscreen2 = cover), 147/148 when the file
# does not say, so another foldable does not get the Fold's.
if [ "$LAYOUT_HIDDEN" = 1 ] && [ "${ONEOS_GUEST_FOLD:-layout}" != off ]; then
    IN_PORT=''; CV_PORT=''
    for f in /vendor/etc/input-port-associations.xml /vendor/odm/etc/input-port-associations.xml; do
        [ -f "$f" ] || continue
        IN_PORT=$(sed -n 's/.*<port display="\([0-9][0-9]*\)" input="sec_touchscreen".*/\1/p' "$f" | head -1)
        CV_PORT=$(sed -n 's/.*<port display="\([0-9][0-9]*\)" input="sec_touchscreen2".*/\1/p' "$f" | head -1)
        break
    done
    [ -n "$IN_PORT" ] && [ -n "$CV_PORT" ] && [ "$IN_PORT" != "$CV_PORT" ] || { IN_PORT=147; CV_PORT=148; }
    echo "[Pivoted Root] Fold ports: inner $IN_PORT, cover $CV_PORT"
    INNER=''; COVER=''; n=0
    while [ $n -lt 25 ]; do
        DIDS=$(dumpsys SurfaceFlinger --display-id 2>/dev/null)
        INNER=$(echo "$DIDS" | sed -n "s/^Display \([0-9][0-9]*\) (HWC display [0-9]*): port=$IN_PORT .*/\1/p" | head -1)
        COVER=$(echo "$DIDS" | sed -n "s/^Display \([0-9][0-9]*\) (HWC display [0-9]*): port=$CV_PORT .*/\1/p" | head -1)
        [ -n "$INNER" ] && [ -n "$COVER" ] && break
        n=$((n + 1)); sleep 0.2
    done
    if [ -n "$INNER" ] && [ -n "$COVER" ] && [ "$INNER" != "$COVER" ]; then
        # Each entry: state, the panel it shows, the panel it switches off.
        # Run 44: a guest without oplus-services.jar (Pixel) gets AOSP's fold
        # states as yogi's own file maps them: 0 closed and 3 rear display on
        # the cover, 1 half open and 2 open on the inner panel (4 and 5, both
        # panels on, left out). Run 43 had only 0 and 3, so its rear display
        # state went to the inner panel. ColorOS keeps Samsung's 0 and 3.
        if [ -e /system/framework/oplus-services.jar ]; then
            # Samsung's states from the phone's own device_state_configuration.xml:
            # 0 (lid closed) on the cover, every other one on the inner panel.
            # The Z Fold8 Ultra and Z Fold7 list 0 CLOSE and 3 OPEN; the Z Fold8
            # (h8q) adds 1 TENT, which had no layout.
            STATES="0:$COVER:$INNER"
            DSC=/vendor/etc/devicestate/device_state_configuration.xml
            # Match the same root-prepared state file the guest framework reads.
            if [ -f /data/system/devicestate/device_state_configuration.xml ] && [ ! -L /data/system/devicestate/device_state_configuration.xml ]; then
                DSC=/data/system/devicestate/device_state_configuration.xml
            fi
            for id in $(sed -n 's/.*<identifier>\([0-9][0-9]*\)<\/identifier>.*/\1/p' "$DSC" 2>/dev/null | sort -un); do
                [ "$id" = 0 ] || STATES="$STATES $id:$INNER:$COVER"
            done
            [ "$STATES" != "0:$COVER:$INNER" ] || STATES="$STATES 3:$INNER:$COVER"
            LNOTE="Samsung's device states: 0 (lid closed) on the cover, the others ($(echo "$STATES" | tr ' ' '\n' | sed -n 's/:.*//p' | grep -v '^0$' | tr '\n' ' ')) on the inner panel."
        elif [ -e /system/system_ext/framework/miui-services.jar ] || [ -e /system_ext/framework/miui-services.jar ]; then
            # HyperOS's own states (guest_prepare.sh binds a lid-switch copy of
            # its product device_state_configuration.xml): 0 CLOSED and 1 TENT
            # outer primary, 2 HALF_OPENED and 3 OPENED inner, 4 OPENED_REVERSE
            # outer (the Pixel order below put 3 on the cover).
            STATES="0:$COVER:$INNER 1:$COVER:$INNER 2:$INNER:$COVER 3:$INNER:$COVER 4:$COVER:$INNER"
            LNOTE="HyperOS fold states 0 closed and 1 tent on the cover, 2 half open and 3 open on the inner panel, 4 reverse on the cover."
        else
            # AOSP's numbering is only right for an image that brings its own
            # device states, because it is its own file that makes 1 and 2
            # happen (yogi: 0 closed, 1 half open, 2 open, 3 rear display).
            # A bar-phone image brings none, so the guest falls back to the
            # phone's /vendor/etc/devicestate, and this Fold declares just
            # 0 CLOSE and 3 OPEN on the lid switch: under AOSP's numbering
            # state 3 is the rear display, so folded AND unfolded both landed
            # on the cover and the inner panel was never enabled at all
            # (Nothing OS run 5, 2026-10-31 -- "inner display doesn't work").
            # So ask the guest's own filesystem first. /vendor is the host's
            # here and must not count as the image's.
            GDSC=""
            for f in /product/etc/devicestate /system/product/etc/devicestate \
                     /system_ext/etc/devicestate /system/system_ext/etc/devicestate \
                     /system/etc/devicestate /odm/etc/devicestate; do
                [ -f "$f/device_state_configuration.xml" ] && { GDSC="$f/device_state_configuration.xml"; break; }
            done
            if [ -n "$GDSC" ]; then
                STATES="0:$COVER:$INNER 1:$INNER:$COVER 2:$INNER:$COVER 3:$COVER:$INNER"
                LNOTE="AOSP fold states 0 closed, 1 half open, 2 open, 3 rear display (the image's own $GDSC)."
            else
                # The states the guest will really be handed, in its own search
                # order: 0 (lid closed) on the cover, every other one on the
                # inner panel, as the ColorOS branch above does.
                HDSC=/vendor/etc/devicestate/device_state_configuration.xml
                if [ -f /data/system/devicestate/device_state_configuration.xml ] &&
                        [ ! -L /data/system/devicestate/device_state_configuration.xml ]; then
                    HDSC=/data/system/devicestate/device_state_configuration.xml
                fi
                STATES="0:$COVER:$INNER"
                for id in $(sed -n 's/.*<identifier>\([0-9][0-9]*\)<\/identifier>.*/\1/p' "$HDSC" 2>/dev/null | sort -un); do
                    [ "$id" = 0 ] || STATES="$STATES $id:$INNER:$COVER"
                done
                [ "$STATES" != "0:$COVER:$INNER" ] || STATES="$STATES 3:$INNER:$COVER"
                LNOTE="the image brings no device states, so the phone's ($HDSC): 0 closed on the cover, every other one on the inner panel."
            fi
        fi
        {
            echo '<?xml version="1.0" encoding="utf-8"?>'
            echo "<!-- OneOS (guest_start.sh): $LNOTE -->"
            echo '<layouts>'
            for s in $STATES; do
                st=${s%%:*}; on=${s#*:}; off=${on#*:}; on=${on%%:*}
                cat <<LAYOUT
    <layout>
        <state>$st</state>
        <display enabled="true" defaultDisplay="true">
            <address>$on</address>
        </display>
        <display enabled="false">
            <address>$off</address>
        </display>
    </layout>
LAYOUT
            done
            echo '</layouts>'
        } > /data/oneos_displayconfig/display_layout_configuration.xml
        chmod 644 /data/oneos_displayconfig/display_layout_configuration.xml
        echo layout > /data/oneos_fold_mode
        # The inner panel's id for the UI activator's density and fold line
        # (oneos_switch.sh, run 44).
        echo "$INNER" > /data/oneos_inner_display; chmod 644 /data/oneos_inner_display
        # vivo in fold mode 1 (ro.vivo.device.type=foldable): the inner panel as vivo's
        # main panel (patches/vivo_guards.py, OneOSVivoPrimaryDisplay). SurfaceFlinger
        # named the cover primary at boot and the inner panel's brightness never
        # followed the slider (F8U run 14). Before system_server, which reads it.
        if [ -e /system/framework/vivo-services.jar ] && [ "$(getprop ro.vivo.device.type)" = foldable ]; then
            setprop oneos.vivo.inner_display "$INNER" &&
                echo "[Pivoted Root] vivo main panel: inner $INNER (oneos.vivo.inner_display)"
        fi
        echo "[Pivoted Root] Fold layout: lid closed -> cover $COVER, lid open -> inner $INNER (states$(for s in $STATES; do printf ' %s' "${s%%:*}"; done))"
    else
        echo "[Pivoted Root] WARNING: no fold layout (SurfaceFlinger gave inner '$INNER', cover '$COVER'); inner display only"
    fi
fi

# Render rate, Pixel guest (run 42). Pixel's DisplayModeDirector gives
# SurfaceFlinger an app-request render range of [0, 120] next to the primary
# [120, 120] the UI activator's min/peak refresh rate set (the cover: [0, inf]
# for both), and on these VRR panels (one mode each, 240 Hz vsync, 120 fps peak,
# rates down to 1 Hz) SurfaceFlinger dropped to 1 Hz within 10 ms of every
# window transition: 9 freezes of 1-2.4 s in 5 minutes (Davey 1038 ms, "Faking
# VSYNC due to driver stall"). ColorOS kept [120, 120] and did not (below thermal status CRITICAL; at
# CRITICAL its range is capped to 0-60 Hz too and a fold stalled the same way:
# guest_props.sh, set_display_power_timer_ms, build 106). Each
# panel's primary and app-request render ranges are pinned with SurfaceFlinger's
# backdoor transaction 1035 (i32 mode id, i64 physical display id, f min, f max;
# this image's surfaceflinger: readInt32, readUint64, readFloat twice ->
# setActiveModeFromBackdoor), on the panel's active mode. While pinned,
# SurfaceFlinger ignores DisplayManager's policies
# (setDesiredDisplayModeSpecsInternal returns early on the backdoor flag), so
# the guest's thermal cap and refresh settings no longer reach it. Up to 0.4.22
# the range was [60, 120]: SurfaceFlinger's idle timer (250 ms) and content
# detection then rendered "normal" frame-rate-category content at 60 Hz (S25
# Ultra af6c2b17: 47 s of the first 2 minutes at 60 Hz, 74 s at 120; testers
# said it felt like 60 Hz). Since 0.4.23 it is [N, 120] with N the active
# mode's vsync rate, at most 120: 120 on the S25 Ultra and on the Fold's VRR
# panels (240 Hz vsync), and never more than a panel can show. The parcel result
# and the policy SurfaceFlinger then reports are logged. Pixel only (no
# oplus-services.jar); ONEOS_GUEST_SF_PIN=0 leaves the ranges to DisplayManager.
# 0.4.55: the pin goes through /data/oneos_sf_kick.sh, which oneos_switch.sh's
# panel keeper runs again later. Reports since 0.4.38 (S25 Ultra e6a54d95, S25+
# 5e94e07b, Z Flip5 51bad347; 10-15 fps "since the last update"): the guest's
# SurfaceFlinger at 120 Hz and pinned there, the panel at 24 Hz the whole session
# (/sys/class/lcd/panel/vrr "24", its low-frequency range 10-24 Hz where a good
# session has 10-120), every frame paced at 24 Hz. One UI's SurfaceFlinger,
# frozen on the switch screen, had left the panel in its idle 24 Hz mode, and
# the restarted composer took the guest's request for its default mode as
# already done. So each display is switched to another mode of its resolution
# and back to the top one (<= 120 Hz), which makes the composer program the
# panel, and pinned at that top rate (a 60 Hz cover at 60: "60-120" was
# refused there, Z Flip5). Displays not listed yet are left to the keeper.
# A VRR panel lists modes whose vsync is above its peak (Z Fold8 Ultra: 240 Hz
# vsync, 120 fps at most): such a mode counts as 120 and is pinned at
# [120, 120], as up to 0.4.54. 0.4.55-0.4.58 skipped it ("no modes in the dump,
# left alone"), so Pixel on the Fold dropped to 1 Hz whenever the screen was
# still (session 9455098f: 27 times in 6 minutes, up to 4 s; freezes, flicker
# on touch).
cat > /data/oneos_sf_kick.sh <<'SFKICK'
# OneOS (guest_start.sh): every physical display through another mode back to its top mode, pinned there.
D=$(dumpsys SurfaceFlinger 2>/dev/null)
n=0
for id in $(dumpsys SurfaceFlinger --display-id 2>/dev/null | sed -n 's/^Display \([0-9][0-9]*\) (HWC display .*/\1/p'); do
    sel=$(echo "$D" | awk -v d="$id" '$0 == "Display " d { f = 1; next } f && /^Display / { f = 0 }
        f && /^ *activeMode=\{id=[0-9]+,/ { r = $0; sub(/.*resolution=/, "", r); sub(/,.*/, "", r); res = r }
        f && /^ *\{id=[0-9]+, hwcId=/ { m = $0; sub(/^ *\{id=/, "", m); sub(/,.*/, "", m)
            rr = $0; sub(/.*resolution=/, "", rr); sub(/,.*/, "", rr)
            v = $0; if (!sub(/.*vsyncRate=/, "", v)) v = 0; k++; id_[k] = m; res_[k] = rr; hz[k] = int(v + 0.5) }
        END { b = -1; bv = 0; bh = 0; o = -1; ov = 0
            for (i = 1; i <= k; i++) if (res_[i] == res) { c = hz[i] > 120 ? 120 : hz[i]
                if (c > bv || (c == bv && hz[i] < bh)) { bv = c; bh = hz[i]; b = id_[i] } }
            for (i = 1; i <= k; i++) if (res_[i] == res && id_[i] != b && hz[i] != bv && hz[i] >= 48 && hz[i] > ov) { ov = hz[i]; o = id_[i] }
            if (b >= 0) print b, bv, o, ov }')
    set -- $sel
    [ $# = 4 ] || { echo "display $id: no modes in the dump, left alone"; continue; }
    # Each call waits on SurfaceFlinger's main thread: never longer than 5 s.
    [ "$3" = -1 ] || { timeout 5 service call SurfaceFlinger 1035 i32 "$3" i64 "$id" f "$4" f "$4" >/dev/null 2>&1; sleep 0.4; }
    r=$(timeout 5 service call SurfaceFlinger 1035 i32 "$1" i64 "$id" f "$2" f "$2" 2>&1 | tr -s ' \n' ' ' | cut -c1-120)
    echo "display $id: through mode $3 ($4 Hz) to mode $1, pinned at $2 Hz: $r"
    n=$((n + 1))
done
[ "$n" -gt 0 ] || echo "no physical displays listed yet"
SFKICK
chmod 644 /data/oneos_sf_kick.sh
if [ -e /system/framework/oplus-services.jar ]; then
    :
elif [ "${ONEOS_GUEST_SF_PIN:-1}" = 0 ]; then
    echo "[Pivoted Root] SF render rate left to DisplayManager (ONEOS_GUEST_SF_PIN=0)"
else
    /system/bin/sh /data/oneos_sf_kick.sh 2>&1 | sed 's/^/[Pivoted Root] SF render rate: /'
    dumpsys SurfaceFlinger 2>/dev/null | awk '/^Display [0-9]+$/ { d = $2 } /debugDisplayModeSetByBackdoor/ { print "[Pivoted Root] SF " $0 }
        d != "" && /^ *displayManagerPolicy=/ { sub(/^ */, ""); print "[Pivoted Root] SF " d " " substr($0, 1, 440); d = "" }'
fi

# OneOS: screen recording from the boot animation on, when /data/oneos_record
# exists (the stage's data/oneos_record). ColorOS's screenrecord through its own
# SurfaceFlinger and the host's Codec2 encoder; 90 s segments at half size and
# 4 Mbps (each under Telegram's 50 MB), 6 segments. A segment that fails at
# once (SurfaceFlinger not ready yet) is retried. return_to_oneui.sh stops it
# with SIGINT so the last segment is finalised.
if [ -f /data/oneos_record ]; then
    rm -f /data/oneos_rec_*.mp4 /data/oneos_rec_stop
    (
        i=1; tries=0
        # return_to_oneui.sh creates /data/oneos_rec_stop before it stops the
        # recording, so no new segment starts during the teardown.
        while [ $i -le 6 ] && [ $tries -lt 30 ] && [ ! -f /data/oneos_rec_stop ]; do
            start=$(date +%s)
            /system/bin/screenrecord --time-limit 90 --size 1128x1252 --bit-rate 4000000 "/data/oneos_rec_$i.mp4" >> /data/screenrecord.log 2>&1
            if [ $(( $(date +%s) - start )) -ge 10 ]; then i=$((i + 1)); else tries=$((tries + 1)); sleep 2; fi
        done
    ) </dev/null >/dev/null 2>&1 &
    echo "[Pivoted Root] Recording the screen to /data/oneos_rec_N.mp4"
fi

echo "[Pivoted Root] Starting guest BootAnimation..."
setprop service.bootanim.exit 0
/system/bin/bootanimation > /data/anim.log 2>&1 &
ANIM_PID=$!
echo "[Pivoted Root] BootAnimation PID: $ANIM_PID"
sleep 1

# Backlight. With the host framework stopped nothing drives the panel
# brightness until the guest's system_server does, so the boot animation can
# play on a dark panel. Log both Fold panels and keep the inner one
# (panel0-backlight) lit for the first 3 minutes if it sits at 0.
# Snapdragon: panel0-backlight and panel1-backlight; Exynos: panel and panel1.
# MediaTek phones without a backlight class device (Galaxy A07, 0.4.65): the
# panel's LED, /sys/class/leds/lcd-backlight (0..max_brightness, 255 there).
BL=/sys/class/backlight/panel0-backlight; BL2=/sys/class/backlight/panel1-backlight
[ -d "$BL" ] || { BL=/sys/class/backlight/panel; BL2=/sys/class/backlight/panel1; }
LEDBL=0
[ -d "$BL" ] || [ ! -w /sys/class/leds/lcd-backlight/brightness ] || { BL=/sys/class/leds/lcd-backlight; BL2=/nonexistent; LEDBL=1; }
# 928: about 135 nits on a Fold's inner panel (max/4 was ~660 nits); 40% of a smaller range.
BLMAX=$(cat $BL/max_brightness 2>/dev/null); BLON=928
case "$BLMAX" in ''|*[!0-9]*) [ $LEDBL = 1 ] && { BLMAX=255; BLON=102; } ;; *) [ "$BLMAX" -lt 928 ] && BLON=$((BLMAX * 2 / 5)) ;; esac
echo "[Pivoted Root] Backlight: inner=$(cat $BL/brightness 2>/dev/null) cover=$(cat $BL2/brightness 2>/dev/null)$([ $LEDBL = 1 ] && echo " (LED $BL, max ${BLMAX:-?})")"
# A Fold switched while folded has the inner panel at 0 and the cover lit:
# the cover is the one kept lit then (guest_props.sh puts the boot animation
# there too), not the inner panel nobody can see.
# Never on a flip or bar phone (ONEOS_GUEST_FORM=phone): a Z Flip5 on HyperOS
# booted with its main panel dark and the cover lit (0.4.59 report 1e8846f4).
KBL=$BL; KNAME=inner
if [ "${ONEOS_GUEST_FORM:-fold}" = fold ] && [ "$(cat $BL/brightness 2>/dev/null)" = 0 ] && [ -w "$BL2/brightness" ] && [ "$(cat $BL2/brightness 2>/dev/null || echo 0)" != 0 ]; then
    KBL=$BL2; KNAME=cover
fi
if [ -w "$KBL/brightness" ]; then
    $BB sh -c "
        i=0
        while [ \$i -lt 60 ]; do
            # ColorOS drives the panel itself once the UI activator ran.
            [ \"\$(getprop service.bootanim.exit)\" = 1 ] && break
            if [ \"\$(cat $KBL/brightness)\" = 0 ]; then
                echo $BLON > $KBL/brightness
                echo \"\$(date +%T) $KNAME backlight was 0, set to \$(cat $KBL/brightness)\"
            fi
            sleep 3; i=\$((i + 1))
        done
    " </dev/null >> /data/backlight.log 2>&1 &
fi
# The brightness bridge. Two cases, one loop (/data/oneos_bl_bridge.sh):
# 1. The LED bridge (0.4.65). On the Galaxy A07 the composer refuses every
#    brightness the guest sets ("HWCDisplay setBrightness() failed to set
#    brightness: 8"), One UI drives the LED through its lights HAL instead, and
#    ColorOS's screen stayed black after boot (0.4.62 1d1308c4: screen on,
#    backlight 0). Where the panel is that LED: always.
# 2. The panel node (0.4.81). The same refusal on every Galaxy A with a backlight
#    class device (A15, A16, A17, A24, A26, A34, A35: "useSurfaceControl=false" in
#    the guest's display dump). ColorOS and OxygenOS send the brightness to the
#    composer anyway ("force_anyway? true"), so nothing ever reached the panel:
#    the node read the same at 20, 40 and 90 s in all 12 such reports of 0.4.72 to
#    0.4.74 (A34 7e5896b0 81 of 510, A15 336e9373, A17 5G 98780abb, A24 80412f38
#    ...), the slider did nothing. Only for that pair. A system that goes through
#    Samsung's lights HAL (HyperOS, Pixel, Infinity-X: "force_anyway? false") is
#    left alone: two writers on one node would fight.
# The guest's brightness (cmd display get-brightness) and wakefulness (dumpsys
# power) are copied once a second. ColorOS and OxygenOS give a level, not 0..1
# (222..8191, sunlight boost to 10239: the 0.4.65 loop took that for no value and
# wrote 40% for good, A07 9e6398f5); the range is read from the display dump.
# On Samsung's panel node 255 is One UI's full slider and the rest of the range
# its sunlight boost, so the guest's normal range ends at 255 and only its own
# boost goes above. Asleep: 0 on the LED (it has no other off switch), nothing on
# a panel node; dozing: 1/20. Ends with the guest.
# ONEOS_GUEST_LED_BRIDGE=0 / ONEOS_GUEST_BL_BRIDGE=0: off.
BRIDGE=0
if [ $LEDBL = 1 ]; then [ "${ONEOS_GUEST_LED_BRIDGE:-1}" = 1 ] && BRIDGE=1
elif [ "${ONEOS_GUEST_BL_BRIDGE:-1}" = 1 ] && [ "$BL" = /sys/class/backlight/panel ] && [ -w "$BL/brightness" ]; then
    case "$BLMAX" in ''|*[!0-9]*) ;; *) BRIDGE=1 ;; esac
fi
if [ $BRIDGE = 1 ]; then
    cat > /data/oneos_bl_bridge.sh <<'BLEOF'
BL=$1; MAX=$2; ON=$3; LED=$4
i=0
while [ "$(getprop service.bootanim.exit)" != 1 ] && [ $i -lt 600 ]; do sleep 1; i=$((i + 1)); done
D=""; n=0
while [ $n -lt 10 ]; do
    D=$(timeout 15 dumpsys display 2>/dev/null | sed -n \
        -e 's/.*\(useSurfaceControl=[a-z]* (force_anyway? [a-z]*)\).*/\1/p' \
        -e 's/^ *\(mScreenBrightnessRangeMinimum=[0-9.]*\).*/\1/p' \
        -e 's/^ *\(mScreenBrightnessRangeMaximum=[0-9.]*\).*/\1/p' \
        -e 's/^ *\(mScreenBrightnessNormalMaximum=[0-9.]*\).*/\1/p')
    case "$D" in *useSurfaceControl=*) break ;; esac
    n=$((n + 1)); sleep 3
done
usc=$(echo "$D" | sed -n 's/^useSurfaceControl=\([a-z]*\) .*/\1/p' | head -n 1)
force=$(echo "$D" | sed -n 's/^useSurfaceControl=[a-z]* (force_anyway? \([a-z]*\))$/\1/p' | head -n 1)
lo=$(echo "$D" | sed -n 's/^mScreenBrightnessRangeMinimum=//p' | head -n 1)
hi=$(echo "$D" | sed -n 's/^mScreenBrightnessRangeMaximum=//p' | head -n 1)
nm=$(echo "$D" | sed -n 's/^mScreenBrightnessNormalMaximum=//p' | head -n 1)
if [ "$LED" != 1 ] && { [ "$usc" != false ] || [ "$force" != true ]; }; then
    echo "$(date +%T) brightness bridge: not needed for $BL (useSurfaceControl=${usc:-not read}, force_anyway=${force:-not read})"
    exit 0
fi
# A level scale when the range ends above 1 (ColorOS, OxygenOS); else 0..1.
SCALE=$(echo "${lo:-x} ${hi:-x} ${nm:-x}" | awk '{ t = $3; if (t !~ /^[0-9.]+$/) t = $2
    if ($1 ~ /^[0-9.]+$/ && $2 ~ /^[0-9.]+$/ && $2 + 0 > 1 && t + 0 > $1 + 0 && $2 + 0 >= t + 0) print "level"; else print "unit" }')
case "$nm" in ''|*[!0-9.]*) nm=$hi ;; esac
NORM=$MAX
[ "$LED" = 1 ] || [ "$MAX" -le 255 ] || NORM=255
echo "$(date +%T) brightness bridge: $BL (max $MAX, the guest's full slider = $NORM; scale $SCALE ${lo:-?}..${nm:-?}..${hi:-?}; useSurfaceControl=${usc:-not read}, force_anyway=${force:-not read})"
last=""; pw=""
while :; do
    w=$(timeout 3 dumpsys power 2>/dev/null | sed -n 's/^ *mWakefulness=//p' | head -n 1)
    [ "$w" = "$pw" ] || last=""
    pw=$w
    case "$w" in
        Asleep) if [ "$LED" = 1 ]; then v=0; else v=""; fi ;;
        Dozing) v=$((NORM / 20 + 1)) ;;
        Awake)
            f=$(timeout 3 cmd display get-brightness 0 2>/dev/null | head -n 1)
            v=$(echo "$f" | awk -v m="$MAX" -v n="$NORM" -v lo="$lo" -v nm="$nm" -v hi="$hi" -v s="$SCALE" '
                {
                    # The first field that is a number (AOSP prints the bare value).
                    x = -1
                    for (i = 1; i <= NF; i++) if ($i ~ /^[0-9]*[.]?[0-9]+(E-?[0-9]+)?$/) { x = $i + 0; break }
                    if (x <= 0) exit
                    if (s == "level") {
                        if (x <= nm) { p = (x - lo) / (nm - lo); if (p < 0) p = 0; y = 1 + p * (n - 1) }
                        else { p = (hi > nm) ? (x - nm) / (hi - nm) : 1; if (p > 1) p = 1; y = n + p * (m - n) }
                    } else {
                        if (x > 1) exit
                        y = x * n
                    }
                    y = int(y + 0.5); if (y < 1) y = 1; if (y > m) y = m; print y; exit
                }')
            if [ -z "$v" ] && [ "$LED" = 1 ]; then v=$ON; fi ;;
        *) v="" ;;
    esac
    if [ -n "$v" ] && [ "$v" != "$last" ]; then
        echo $v > $BL/brightness && echo "$(date +%T) $w: $v"
        last=$v
    fi
    sleep 1
done
BLEOF
    $BB sh /data/oneos_bl_bridge.sh "$BL" "$BLMAX" "$BLON" "$LEDBL" </dev/null >> /data/backlight.log 2>&1 &
    if [ $LEDBL = 1 ]; then echo "[Pivoted Root] Backlight: LED bridge started for $BL"
    else echo "[Pivoted Root] Backlight: brightness bridge started for $BL (it runs only if the composer refuses brightness and the system does not use the lights HAL; see backlight.log)"; fi
fi

# aconfig flag storage. init/aconfigd normally build /metadata/aconfig from
# every partition's and APEX's etc/{package.map,flag.map,flag.val,flag.info};
# the container had none, so flag lookups failed ("failed to open
# /metadata/aconfig/maps/system.package.map") and AdvancedProtectionService
# took system_server down on "Invalid feature flag". Lay out the guest's own
# files the same way on a tmpfs in this namespace.
AC=/metadata/aconfig
if $BB mount -t tmpfs -o mode=755 tmpfs /metadata 2>/dev/null; then
    mkdir -p $AC/maps $AC/boot $AC/flags
    n=0
    add_flags() {
        [ -f "$2/package.map" ] && [ -f "$2/flag.map" ] && [ -f "$2/flag.val" ] || return 0
        cp "$2/package.map" "$AC/maps/$1.package.map"
        cp "$2/flag.map" "$AC/maps/$1.flag.map"
        cp "$2/flag.val" "$AC/boot/$1.val"
        [ -f "$2/flag.info" ] && cp "$2/flag.info" "$AC/boot/$1.info"
        n=$((n + 1))
    }
    add_flags system /system/etc/aconfig
    add_flags system_ext /system_ext/etc/aconfig
    add_flags product /product/etc/aconfig
    add_flags vendor /vendor/etc/aconfig
    for a in /apex/*; do
        case "$a" in *@*) continue ;; esac
        add_flags "$(basename "$a")" "$a/etc"
    done
    chown -R 1000:1000 /metadata/aconfig
    chmod 775 $AC $AC/maps $AC/boot; chmod 770 $AC/flags; chmod 644 $AC/maps/* $AC/boot/* 2>/dev/null
    echo "[Pivoted Root] aconfig storage for $n containers on /metadata"
else
    echo "[Pivoted Root] WARNING: could not mount /metadata for aconfig storage"
fi
# (Built only after surfaceflinger and the boot animation started: with the
# guest's flag values surfaceflinger used composer features Samsung's composer
# rejects, executeCommands BAD_VALUE / presentOrValidate NO_RESOURCES on every
# frame, a black panel. Without flag storage it runs on defaults, which worked.)

# OneOS: the guest framework must get THIS vold, never One UI's (which holds the
# phone's real storage). Up to run 43 both registered "vold" in the shared
# servicemanager, the guest's last. Run 44: with vold_patched bound
# (guest_prepare.sh then writes gvld to /data/oneos_vold_name) the guest vold
# registers "gvld" and neither "vold" nor android.system.vold.IVold/default,
# and the guest framework looks up "gvld" (services.jar, service.incremental.so;
# docs/inplace-return.md). One UI's vold cannot be restarted (init.rc:
# reboot_on_failure), so returning to One UI without a reboot needs both names
# to stay its own all session. "gvld" has no service_contexts entry:
# servicemanager labels it default_android_service, which only this permissive
# session (oneos_switch.sh: setenforce 0) lets the guest add and find. Images
# without vold_patched (ColorOS) keep the guest vold on "vold", as up to run 43.

# The pid servicemanager has for a name, or nothing: only an all-digit line
# counts ("Can't find service: ..." is not a pid).
svc_pid() {
    o=$(timeout 5 dumpsys --pid "$1" 2>/dev/null | head -n 1)
    case "$o" in ''|*[!0-9]*) ;; *) echo "$o" ;; esac
}
# Why One UI's vold no longer has its names, or nothing: "vold" is the pid init
# started it as, and android.system.vold.IVold/default, when registered, too.
host_vold_lost() {
    hv=$(svc_pid vold)
    if [ -z "$HOST_VOLD" ] || [ "$hv" != "$HOST_VOLD" ]; then
        echo "servicemanager's vold is pid '$hv', not One UI's vold '$HOST_VOLD' (init.svc_debug_pid.vold)"
    elif [ "$(getprop init.svc_debug_pid.vold)" != "$HOST_VOLD" ]; then
        echo "One UI's vold is pid '$(getprop init.svc_debug_pid.vold)' now, was $HOST_VOLD"
    elif service check android.system.vold.IVold/default 2>/dev/null | grep -q ': found'; then
        hv=$(svc_pid android.system.vold.IVold/default)
        [ "$hv" = "$HOST_VOLD" ] || echo "android.system.vold.IVold/default is pid '$hv', not One UI's vold $HOST_VOLD"
    fi
}
# For the log: android.system.vold.IVold/default's pid, if registered.
vdef() { hv=$(svc_pid android.system.vold.IVold/default); echo "${hv:-not registered}"; }
VOLD_NAME=vold
if [ "$(cat /data/oneos_vold_name 2>/dev/null)" = gvld ]; then
    VOLD_NAME=gvld
    HOST_VOLD=$(getprop init.svc_debug_pid.vold)
    why=$(host_vold_lost)
    # Bound by guest_prepare.sh, which checked them against guards.txt. And the
    # services.jar: one that still looked up "vold" would hand the guest
    # StorageManagerService One UI's vold (connectVold, then IVold.reset()).
    # Its patched dex is stored, not deflated (make-overlays.sh: zip -0). On
    # ColorOS also oplus-services.jar (OplusStorageManagerFeature.connectVold),
    # HyperOS miui-services.jar (ExtendMImpl, AppCacheOptimizer).
    for f in /system/bin/vold /system/lib64/service.incremental.so /system/framework/services.jar \
             $([ -f /system/framework/oplus-services.jar ] && echo /system/framework/oplus-services.jar) \
             $([ -f /system/system_ext/framework/miui-services.jar ] && echo /system/system_ext/framework/miui-services.jar); do
        $BB grep -q gvld "$f" || why="$f is not the gvld build"
    done
    [ "$(cat /sys/fs/selinux/enforce 2>/dev/null)" = 1 ] && why="SELinux is enforcing: servicemanager refuses gvld (default_android_service)"
    # RecoverySystem.rebootPromptAndWipeUserData (framework.jar) asks
    # checkService("vold"), One UI's vold now, for needsCheckpoint/abortChanges.
    # services.jar no longer calls it (patches/guest_storage_guards.py,
    # guest_own_vold.py); RescueParty's factory reset (crashrecovery APEX) does,
    # only when RescueParty is on: isDisabled() is false with
    # persist.sys.enable_rescue, true with persist.sys.disable_rescue
    # (oneos_switch.sh [1/6]).
    case "$(getprop persist.sys.disable_rescue)" in true|1|y|yes|on) ;; *) why="persist.sys.disable_rescue is not true (RescueParty would reach One UI's vold)" ;; esac
    case "$(getprop persist.sys.enable_rescue)" in true|1|y|yes|on) why="persist.sys.enable_rescue is set (RescueParty would reach One UI's vold)" ;; esac
    if [ -n "$why" ]; then
        echo "[Pivoted Root] FATAL: $why. Not starting the guest."
        exit 1
    fi
    echo "[Pivoted Root] One UI's vold: pid $HOST_VOLD, android.system.vold.IVold/default: $(vdef); SELinux $(getenforce 2>/dev/null); the guest's will register gvld"
fi
echo "[Pivoted Root] Starting guest Vold..."
# The four SELinux contexts every vold since 3.0 takes, and any further
# --*_context= flag this image's own vold.rc passes: a build that needs one and
# does not get it dies in main() before it registers anything. Nothing OS 5.0
# adds --fuseblk_fs_context=u:r:nt_ntfs_3g:s0 for its NTFS-3G helper, and
# aborted on "Check failed: sFuseblkFsContext != nullptr" (main.cpp:195)
# without it; the Pixel's Android 17 vold has no such flag. Taking them from
# the image's vold.rc keeps the next vendor's addition working too. The
# context only has to parse here: it is used when a fuseblk volume is mounted,
# which a session never does, and One UI's policy has no nt_ntfs_3g.
VOLD_RC=""
for f in /system/etc/init/vold.rc /etc/init/vold.rc; do
    [ -f "$f" ] && { VOLD_RC=$f; break; }
done
VOLD_EXTRA=""
if [ -n "$VOLD_RC" ]; then
    VOLD_EXTRA=$(awk '
        /^service vold / { inv = 1 }
        inv {
            for (i = 1; i <= NF; i++)
                if ($i ~ /^--[a-z_]+_context=/ && $i !~ /^--(blkid|blkid_untrusted|fsck|fsck_untrusted)_context=/)
                    printf "%s ", $i
            if ($0 !~ /\\$/) inv = 0
        }' "$VOLD_RC")
fi
[ -z "$VOLD_EXTRA" ] || echo "[Pivoted Root] Guest vold flags from ${VOLD_RC}: $VOLD_EXTRA"
# shellcheck disable=SC2086
/system/bin/vold --blkid_context=u:r:blkid:s0 --blkid_untrusted_context=u:r:blkid_untrusted:s0 --fsck_context=u:r:fsck:s0 --fsck_untrusted_context=u:r:fsck_untrusted:s0 $VOLD_EXTRA > /data/vold.log 2>&1 &
VOLD_PID=$!
echo "[Pivoted Root] Vold PID: $VOLD_PID"
n=0
while [ $n -lt 50 ]; do
    [ "$(svc_pid $VOLD_NAME)" = "$VOLD_PID" ] && break
    n=$((n + 1)); sleep 0.2
done
if [ "$(svc_pid $VOLD_NAME)" != "$VOLD_PID" ]; then
    echo "[Pivoted Root] FATAL: servicemanager's $VOLD_NAME is pid '$(dumpsys --pid $VOLD_NAME 2>&1 | head -n 1)', not the guest's $VOLD_PID. Not starting the guest."
    exit 1
fi
echo "[Pivoted Root] servicemanager's $VOLD_NAME is the guest's ($VOLD_PID)"
# And One UI's vold kept both its names. Again right before zygote: the guest
# vold's vendor name would come a moment after gvld.
if [ "$VOLD_NAME" = gvld ]; then
    why=$(host_vold_lost)
    if [ -n "$why" ]; then
        echo "[Pivoted Root] FATAL: $why. Not starting the guest."
        exit 1
    fi
    echo "[Pivoted Root] One UI's vold ($HOST_VOLD) still has vold and android.system.vold.IVold/default ($(vdef))"
fi

# Wifi. oneos_switch.sh stops the host wificond; the guest's own registers
# IWificond before WifiService initialises, and drives Samsung's wifi HAL (which
# is still registered by host init) with matching AIDL.
# Pixel 17 has none and needs none: its wifi module drives nl80211 itself
# (useWificond: false); oneos_switch.sh restarts One UI's idle.
if [ -x /system/bin/wificond ]; then
    echo "[Pivoted Root] Starting guest wificond..."
    /system/bin/wificond > /data/wificond.log 2>&1 &
    WIFICOND_PID=$!
    echo "[Pivoted Root] wificond PID: $WIFICOND_PID"
    sleep 1
else
    echo "[Pivoted Root] No wificond in the image: the guest's wifi module drives nl80211 itself"
fi

# ColorOS list/feedback daemons ("class main" in system_ext/etc/init/
# mmlistservice.rc and atlasservice.rc; host init never starts them). ColorOS's
# AudioTrack, ToneGenerator and NuPlayer and its audioserver look them up with a
# blocking getService(): 5 s per lookup, several per track (run 29: Telecom built
# its call-connected tone for 25 s under its lock; the hang-up waited 16 s).
# Other systems (Pixel) have neither: no wait then.
MMLIST=0
for d in "/system_ext/bin/mmlistservice" "/system_ext/bin/atlasservice"; do
    [ -x "$d" ] || continue
    "$d" > /dev/null 2>&1 &
    echo "[Pivoted Root] $(basename "$d") PID: $!"
    MMLIST=1
done
if [ "$MMLIST" = 1 ]; then
    n=0
    while [ $n -lt 25 ] && ! service check MMListService 2>/dev/null | grep -q ": found"; do n=$((n + 1)); sleep 0.2; done
    echo "[Pivoted Root] MMListService:$(service check MMListService 2>/dev/null | cut -d: -f2), AtlasService:$(service check AtlasService 2>/dev/null | cut -d: -f2) after $((n / 5))s"
fi

# Guest media stack (see oneos_switch.sh: the host's copies are stopped).
# ColorOS ships mediaserverwrapper on Qualcomm; its plain mediaserver is 32-bit
# only and cannot run on this arm64-only phone.
if [ -f /data/guest_media.flag ]; then
    echo "[Pivoted Root] Starting guest media services..."
    # The wrapper picks mediaserver64 only when ro.mediaserver.64b.enable is
    # set, which OPPO's vendor does and Samsung's does not; it then ran the
    # 32-bit one, and media.player / media.resource_manager never registered.
    # Pixel has only a 64-bit /system/bin/mediaserver.
    MS=/system/bin/mediaserver64
    [ -x "$MS" ] || MS=/system/bin/mediaserverwrapper
    [ -x "$MS" ] || MS=/system/bin/mediaserver
    $MS > /dev/null 2>&1 &
    echo "[Pivoted Root] $(basename $MS) PID: $!"
    /system/bin/mediaextractor > /dev/null 2>&1 &
    echo "[Pivoted Root] mediaextractor PID: $!"
    /system/bin/mediametrics > /dev/null 2>&1 &
    echo "[Pivoted Root] mediametrics PID: $!"
fi

# Guest audioserver (oneos_switch.sh stopped Samsung's): ColorOS's audio
# interfaces are not numbered like Samsung's (run 29: no routing strategies,
# volume groups or ports; Samsung's AudioFlinger refused every app stream). The
# guest's drives Samsung's audio HAL through the stable audio.core AIDL, as a
# GSI does. It registers media.audio_flinger/media.audio_policy only after the
# guest framework's "activity" service exists (run 30: it waited for it, while
# this script waited for it to register before starting zygote), so it is
# started here and watched alongside the boot: if it has not registered after
# 60 s, or keeps dying, Samsung's audioserver takes over (AudioService waits
# for the policy service without a timeout).
if [ -f /data/guest_audio.flag ]; then
    echo "[Pivoted Root] Starting guest audioserver..."
    mkdir -p /data/misc/audioserver && chown 1041:1005 /data/misc/audioserver && chmod 0700 /data/misc/audioserver
    n=0
    while [ $n -lt 50 ] && ! service check android.hardware.audio.core.IModule/default 2>/dev/null | grep -q ": found"; do n=$((n + 1)); sleep 0.2; done
    echo "[Pivoted Root] audio HAL IModule/default:$(service check android.hardware.audio.core.IModule/default 2>/dev/null | cut -d: -f2) after $((n / 5))s"
    # A2DP offload (run 44): Samsung's QTI HAL turns its Bluetooth offload path
    # on only from the vendor parameter l_a2dp_format (bit 21 of the number,
    # Platform+8), which One UI's audioserver sends and a GSI's never does: every
    # connect logged "bt_offload state is disabled" and the earbuds played on the
    # speaker. Sent with the call keeper's IModule parcel (sizes 124, 76, 24 for
    # 2097152) and again whenever the HAL restarts. Never l_support_sec_audio_feature,
    # which would switch the HAL to One UI's module config. The value lives in the
    # HAL process only, and the return restarts the HAL before One UI's
    # audioserver. ColorOS and Infinity-X too since 0.4.37: on the S25 Ultra and
    # S25+ their earbuds connected and played nothing, the HAL logging
    # "bt_offload state is disabled" at each connect as the Pixel did before
    # this (reports 1b63fc7a, 65339344); they were left out only by caution.
    # ONEOS_GUEST_A2DP_FORMAT=0 skips it.
    # Each send is checked against the HAL's own log, as the call keeper does
    # (run 43: a binder reply of 00000000 for a key the HAL never got), and
    # oneos_a2dp.log gets the HAL's line ("configured l_a2dp_format", or "not
    # configured ..." for a key it does not take). The log, like the keepers'
    # logs, grows across sessions: each session starts with a dated line.
    A2F=${ONEOS_GUEST_A2DP_FORMAT:-2097152}
    case "$A2F" in ""|*[!0-9]*) A2F=0 ;; esac
    if [ "$A2F" != 0 ]; then
        echo "=== $(date '+%F %T') session: l_a2dp_format=$A2F to the audio HAL" >> /data/oneos_a2dp.log
        $BB sh -c 'v=$1; bb=$2
            s16() { echo $((4 + (${#1} * 2 + 5) / 4 * 4)); }
            vs=$((4 + $(s16 "$v"))); hs=$(($(s16 qti.audio.core.VString) + vs)); ps=$((4 + $(s16 l_a2dp_format) + 12 + hs))
            # The HAL (pid h) line for the key, the last one; empty if none.
            seen() { logcat -d --pid="$h" -s AHAL_SecModulePrimary 2>/dev/null | $bb grep -F "configured l_a2dp_format" | tail -n 1; }
            hp=""; n=0
            while :; do
                h=$(dumpsys --pid android.hardware.audio.core.IModule/default 2>/dev/null | head -n 1 | tr -dc 0-9)
                if [ -n "$h" ] && [ "$h" != "$hp" ]; then
                    b=$(seen)
                    r=$(service call android.hardware.audio.core.IModule/default 34 i32 1 i32 1 i32 $ps s16 l_a2dp_format i32 1 i32 1 i32 $hs s16 qti.audio.core.VString i32 $vs s16 "$v" i32 0 2>&1 | tr -s " \n" " " | head -c 100 | $bb sed "s/ *\$//")
                    sleep 1; a=$(seen)
                    [ -n "$a" ] && [ "$a" != "$b" ] || { sleep 2; a=$(seen); }
                    if [ -n "$a" ] && [ "$a" != "$b" ]; then ok="HAL: ${a#*: }"
                    else ok="HAL NEVER logged it (no AHAL_SecModulePrimary line for l_a2dp_format from pid $h)"; fi
                    echo "$(date +%T) l_a2dp_format=$v (sizes $ps $hs $vs) to the audio HAL pid $h: $r; $ok"
                    # Not logged by the HAL: sent again on the next round, 3 tries per HAL pid.
                    if [ -n "$a" ] && [ "$a" != "$b" ]; then hp=$h; n=0
                    else n=$((n + 1)); [ $n -lt 3 ] || { hp=$h; n=0; echo "$(date +%T) l_a2dp_format: gave up on HAL pid $h after 3 tries"; }; fi
                fi
                sleep 10
            done' oneos_a2dp "$A2F" "$BB" >> /data/oneos_a2dp.log 2>&1 &
        echo "[Pivoted Root] A2DP offload: l_a2dp_format=$A2F to the audio HAL, again on every HAL restart, each send checked in the HAL log (/data/oneos_a2dp.log)"
    else
        echo "[Pivoted Root] A2DP offload: l_a2dp_format not sent (ONEOS_GUEST_A2DP_FORMAT=0)"
    fi
    # ColorOS's AOSP audio policy parser wants /vendor/etc/audio_policy_configuration.xml.
    # Samsung's vendor only ships QTI's _base and sku files at other paths, so the
    # parser fell back to setDefault: volume groups with max index 0, and SystemUI's
    # volume slider crashes on NaN. The QTI _base file is the same format ColorOS
    # loads; put it at the top-level path through a guest-only overlay (the f2fs
    # upper is refused for casefold, so a small tmpfs holds the upper).
    if [ -e /system/framework/oplus-services.jar ] && grep -rqs 'android.hardware.audio.core' /vendor/etc/vintf/ &&
       [ -f /vendor/etc/audio_policy_configuration_base.xml ] && [ ! -e /vendor/etc/audio_policy_configuration.xml ]; then
        AOV=/data/oneos_audio_policy
        mkdir -p "$AOV"
        mount | grep -q " $AOV " || $BB mount -t tmpfs -o size=8m,mode=755 tmpfs "$AOV"
        mkdir -p "$AOV/upper" "$AOV/work"
        cp /vendor/etc/audio_policy_configuration_base.xml "$AOV/upper/audio_policy_configuration.xml" &&
            chmod 644 "$AOV/upper/audio_policy_configuration.xml" &&
            $BB chcon u:object_r:vendor_configs_file:s0 "$AOV/upper/audio_policy_configuration.xml" 2>/dev/null || true
        if $BB mount -t overlay overlay -o "lowerdir=/vendor/etc,upperdir=$AOV/upper,workdir=$AOV/work" /vendor/etc; then
            echo "[Pivoted Root] ColorOS audio policy: _base.xml as /vendor/etc/audio_policy_configuration.xml (volume tables)"
        else
            echo "!!! WARNING: ColorOS audio policy: the overlay on /vendor/etc was refused; volume groups may be default"
        fi
    fi
    # Samsung's audio HAL keeps the streams of a dead audioserver: a fresh one
    # then gets -38 on every openOutputStream ("port config ... already has a
    # stream opened"), AudioPolicyManager init fails and audio is silent until
    # the HAL restarts. Restart it before the first audioserver and before each
    # restart in the keeper below.
    restart_audio_hal() {
        service check android.hardware.audio.core.IModule/default 2>/dev/null | grep -q ": found" || return 0
        h=$(pidof audiohalservice.qti 2>/dev/null)
        [ -n "$h" ] && kill -9 $h 2>/dev/null
        i=0
        while [ $i -lt 50 ]; do
            service check android.hardware.audio.core.IModule/default 2>/dev/null | grep -q ": found" && return 0
            i=$((i + 1)); sleep 0.2
        done
        return 1
    }
    restart_audio_hal && echo "[Pivoted Root] audio HAL restarted before guest audioserver"
    /system/bin/audioserver > /dev/null 2>&1 &
    AS_PID=$!
    echo "[Pivoted Root] guest audioserver PID: $AS_PID (registers once the guest framework is up)"
    echo "=== $(date '+%F %T') session: guest audioserver $AS_PID" >> /data/audio_keeper.log
    $BB sh -c 'as=$1
        owner() { dumpsys --pid media.audio_policy 2>/dev/null | tr -dc 0-9; }
        handover() {
            kill -9 $as 2>/dev/null; rm -f /data/guest_audio.flag
            setprop ctl.start audioserver
            echo "$(date +%T) $1; handed over to the host audioserver"
        }
        # The guest audioserver registers 1 to 3 s after the guest system_server
        # publishes its services (SetSystemProcess: the "activity" service). A flat
        # 60 s was too short on the slow MediaTek Galaxy A (0.4.74 reports, ColorOS
        # 17: A16 4G 96e8e88c registered at 48, 54 and 56 s, then four sessions and
        # the A15 336e9373 missed it by 1 to 3 s). The hand-over then killed a
        # healthy audioserver and started the One UI one, which waited for its
        # vendor extension for good; AudioService blocked in its constructor and
        # the watchdog killed system_server ("The other system stopped").
        # So: 60 s as before, and never less than 20 s after the guest framework
        # is there (a = seconds since "activity" was first found); 600 s at most
        # while there is no framework at all (nothing needs sound until then).
        t=0; a=-1
        while [ "$(owner)" != "$as" ] && kill -0 $as 2>/dev/null; do
            if [ $a -lt 0 ]; then
                case "$(service check activity 2>/dev/null)" in *": found"*) a=0 ;; esac
            fi
            if [ $a -lt 0 ]; then [ $t -lt 600 ] || break
            else [ $t -lt 60 ] || [ $a -lt 20 ] || break; fi
            sleep 2; t=$((t + 2)); [ $a -lt 0 ] || a=$((a + 2))
        done
        if [ "$(owner)" != "$as" ]; then
            if [ $a -lt 0 ]; then handover "guest audioserver did not register in ${t}s (no guest framework in that time)"
            else handover "guest audioserver did not register in ${t}s (${a}s after the guest framework came up)"; fi
            exit 0
        fi
        echo "$(date +%T) guest audioserver $as registered after ${t}s"
        # Keep it the one servicemanager hands out (host init can bring
        # Samsung audioserver back through the HAL onrestart). Log why it
        # restarts. No apostrophes anywhere in this script: it is one
        # single-quoted sh -c argument, and the two this comment had (runs
        # 31-33) cut it here, so as was the word through, kill -0 failed,
        # every session handed over at 0s and dropped guest_audio.flag
        # while the guest audioserver went on serving (run 33: 15587 owned
        # media.audio_policy from 14:41:42 next to Samsung 15619).
        # The 5 restarts before the hand-over count within 2 minutes: deaths far
        # apart start again from 0 (0.4.38 S23 report 161be9f1: two deaths each at
        # 7, 23 and 27 minutes, the fifth handed over to Samsung audioserver, whose
        # product strategies carry Samsung usage 1005; a Pixel AudioService throws
        # Invalid usage 1005 and system_server died).
        miss=0; r=0; last=0
        while [ -f /data/guest_audio.flag ]; do
            sleep 3
            if ! kill -0 $as 2>/dev/null; then why="died"
            elif [ "$(owner)" != "$as" ]; then why="media.audio_policy taken"
            else miss=0; continue; fi
            miss=$((miss + 1)); [ $miss -lt 2 ] && continue
            kill -9 $as 2>/dev/null
            now=$(date +%s); [ $((now - last)) -gt 120 ] && r=0; last=$now
            # 0.4.60: no hand-over after registration. Every guest framework is not
            # Samsung, and Samsung audioserver killed it (Invalid usage 1005; 0.4.59
            # Pixel reports 2c9c6419, 630e5625, 7fe453b5: a sound model Samsung sound
            # trigger HAL refused made the guest reboot that HAL five times, the
            # hand-over followed and system_server died, back to One UI after 60 s).
            # From the fifth death within 2 minutes, a pause before each restart.
            if [ $r -ge 4 ]; then
                d=$(( (r - 3) * 10 )); [ $d -gt 60 ] && d=60
                echo "$(date +%T) guest audioserver $why $((r + 1)) times within 2 minutes; restart in ${d}s (no hand-over)"
                sleep $d
                now=$(date +%s); last=$now
            fi
            if service check android.hardware.audio.core.IModule/default 2>/dev/null | grep -q ": found"; then
                h=$(pidof audiohalservice.qti 2>/dev/null); [ -n "$h" ] && kill -9 $h 2>/dev/null
                i=0; while [ $i -lt 50 ]; do service check android.hardware.audio.core.IModule/default 2>/dev/null | grep -q ": found" && break; i=$((i + 1)); sleep 0.2; done
                echo "$(date +%T) audio HAL restarted before audioserver"
            fi
            /system/bin/audioserver > /dev/null 2>&1 & as=$!; miss=0; r=$((r + 1))
            echo "$(date +%T) guest audioserver $why, restarted as $as"
        done' sh "$AS_PID" </dev/null >> /data/audio_keeper.log 2>&1 &
fi

# Voice calls (run 32): a call on SIM 2 connected with no audio either way
# while media played. all.log 13:16:53: GsmCdmaCallTracker [1] OFFHOOK, and
# AHAL_Telephony_QTI "switchAudioMode: new call state is ACTIVE for vsid
# VSID_1", voice graph "..._VSID_VSID_DEFAULT". Samsung's HAL starts the voice
# session on the VSID that g_call_sim_slot last chose (Telephony::
# updateSecVSID: 0x01 -> VSID_1 0x11C05000, 0x02 -> VSID_2 0x11DC5000; VSID_1
# until told), and One UI's audioserver sends it right before every
# setMode(IN_CALL) (run 29: "CallStateManager: getCallSetParamByGuard:
# g_call_sim_slot=0x01"). ColorOS's audioserver never does, so the ADSP ran
# SIM 1's voice session while the modem had the call on SIM 2. Tell the HAL
# through the guest AudioFlinger's setParameters (IAudioFlingerService
# transaction 18 in this image's audioflinger-aidl-cpp.so). While idle: the
# ringing SIM, else the SIM of the last call (kept in /data/oneos_call_slot).
# An outgoing call reaches the HAL (Telecom's setMode) before the phone
# reports OFFHOOK, and the HAL skips a plain 0x01/0x02 while a call runs in
# IN_CALL mode, so a call already on the wrong VSID gets 0x10, the HAL's own
# swap (stop and restart the voice session on the other VSID). The HAL's own
# log (its current pid only) says which VSID it is on; call_audio.log keeps
# the decisions. ONEOS_GUEST_CALL_SIM=0 leaves the HAL alone.
# Run 33: call_audio.log stayed empty and all five calls ran on VSID_1 (SIM 1
# fine; SIM 2 silent, not even ringback; all.log 14:53:32, 14:53:59, 14:55:47)
# because the keeper above had dropped guest_audio.flag at 14:41:31 (see
# there), so this loop skipped every turn. From hal.so: updateSecVSID only
# stores 0x01/0x02 in mCurVSID while idle, and switchAudioMode copies that
# into the call at setMode(IN_CALL); during a call in IN_CALL mode it logs
# "skip to change vsid to VSID_n during call" and does nothing; 0x10
# (SIM_FORCE_UPDATE) needs a running call and restarts it on the OTHER VSID.
# Telecom setMode reached the HAL 16-20 ms either side of OFFHOOK, so an
# outgoing call on the other SIM always starts wrong: it gets 0x10 at once,
# and only once (a second one would swap back).
# OneOS: only with a vendor audio HAL that has both g_call_sim_slot and
# updateSecVSID (read from the F8U HAL only), looked up first in the vendor
# audio libraries the way oneos_switch.sh greps the sysinput HAL; without
# them the loop logs that and stops. ONEOS_GUEST_CALL_SIM=2 skips the look.
# Run 43 (Pixel): every SIM 2 call in runs 41-43 ran on VSID_1 and was silent
# both ways. AudioFlinger returned OK, but the HAL never logged "configured
# g_call_sim_slot": Pixel's libaudiohal@aidl hands unknown keys to
# IModule.setVendorParameters only through an IHalAdapterVendorExtension, and
# with ro.audio.ihaladaptervendorextension_enabled=false (guest_props.sh, run
# 38) it has none and drops them without a log line. One UI's and ColorOS's
# QTI audioservers load that extension (libaudiohalvendorextn.so) in-process,
# which is why ColorOS's keys arrived (run 34). So unless the property is true
# the keeper sends the key straight to the shared HAL (IModule/default
# transaction 34) with the parcel that extension builds, and checks every send
# against the HAL's own log. The path is checked as soon as the HAL is known
# (af: once the guest audioserver has registered; nothing goes out on a path
# that is not ready), before any call; when it is not delivered the keeper
# switches path once, and only on an idle 0x01/0x02 (never a 0x10), after a
# second look for a late HAL line. ONEOS_GUEST_CALL_SIM_VIA=af|hal
# forces the first path (af: through the guest AudioFlinger).
# call_audio.log grows across sessions and its lines carry the time only (run
# 44's capture still had a session of 09:07 before run 44's): a dated line
# first.
if [ -f /data/guest_audio.flag ] && [ "${ONEOS_GUEST_CALL_SIM:-1}" != 0 ]; then
    echo "=== $(date '+%F %T') session" >> /data/call_audio.log
    $BB sh -c 'bb=$1
        if [ "$2" != 2 ]; then
            lib=""
            for f in $(grep -l -s -F g_call_sim_slot /vendor/lib64/*audio*.so /vendor/lib64/hw/*audio*.so /vendor/bin/hw/*audio* 2>/dev/null); do
                grep -q -s -F updateSecVSID "$f" && { lib=$f; break; }
            done
            if [ -z "$lib" ]; then
                echo "$(date +%T) no vendor audio library has g_call_sim_slot and updateSecVSID: SIM slot loop off"
                exit 0
            fi
            echo "$(date +%T) audio HAL keys found in $lib"
        fi
        # How g_call_sim_slot reaches the HAL (run 43): af through the guest
        # AudioFlinger, whose libaudiohal forwards vendor keys only through
        # the QTI vendor extension (property true: ColorOS, run 34), or hal
        # straight to IModule/default. $3 is ONEOS_GUEST_CALL_SIM_VIA.
        ve=$(getprop ro.audio.ihaladaptervendorextension_enabled)
        case $3 in
            af|hal) via=$3; why="ONEOS_GUEST_CALL_SIM_VIA" ;;
            *) if [ "$ve" = true ]; then via=af; else via=hal; fi; why="ro.audio.ihaladaptervendorextension_enabled=${ve:-unset}" ;;
        esac
        first=$via; tried=""; probed=""
        # Which library gives the HAL qti.audio.core.VString (the ext type
        # below), and whether the HAL could check the caller uid (the keeper
        # is root, an audioserver 1041). Audio libraries only: boot is busy.
        vt=$(grep -l -s -F qti.audio.core.VString /vendor/lib64/*audio*.so /vendor/lib64/hw/*audio*.so 2>/dev/null | head -n 2 | tr "\n" " "); vt=${vt% }
        uc=$([ -n "$lib" ] && grep -c -s -F AIBinder_getCallingUid "$lib")
        echo "$(date +%T) g_call_sim_slot path $via first ($why; extension service:$(service check android.media.audio.IHalAdapterVendorExtension/default 2>&1 | cut -d: -f2))"
        # Run 44: true (the image value) kept SCO closed; guest_props.sh now
        # leaves it out for Pixel guests, so unset is what a call needs.
        sm=$(getprop bluetooth.sco.managed_by_audio)
        echo "$(date +%T) VString in: ${vt:-none}; AIBinder_getCallingUid in the HAL: ${uc:-?}; bluetooth.sco.managed_by_audio=${sm:-unset}"
        # IModule.setVendorParameters is transaction 34 (BpModule in the
        # image android.hardware.audio.core-V4-ndk.so). The parcel is the one
        # the QTI extension builds, the layout ColorOS sent in run 34:
        # count 1, non-null 1, VendorParameter {size, String16 id, non-null 1,
        # holder stability 1 (VINTF, the only one the HAL reads), holder size,
        # String16 qti.audio.core.VString, VString {size, String16 value}},
        # then async false. Each size counts its own 4 bytes; s16 is the size
        # of a String16 (length, UTF-16 with a NUL, padded to 4). For 0x10 the
        # data after the interface token is 136 bytes, sizes 124, 72 and 20.
        s16() { echo $((4 + (${#1} * 2 + 5) / 4 * 4)); }
        send() {
            if [ "$1" = hal ]; then
                vs=$((4 + $(s16 "$2"))); hs=$(($(s16 qti.audio.core.VString) + vs)); ps=$((4 + $(s16 g_call_sim_slot) + 12 + hs))
                service call android.hardware.audio.core.IModule/default 34 i32 1 i32 1 i32 $ps s16 g_call_sim_slot i32 1 i32 1 i32 $hs s16 qti.audio.core.VString i32 $vs s16 "$2" i32 0 2>&1
            else
                service call media.audio_flinger 18 i32 0 s16 "g_call_sim_slot=$2" 2>&1
            fi | tr -s " \n" " " | head -c 100 | $bb sed "s/ *\$//"
        }
        # Delivered when the last "configured g_call_sim_slot" line of the
        # HAL (its current pid) changed: its timestamp makes it unique, while
        # a count can stay the same as the log buffer rotates (all.log runs at
        # about 700 lines a second). A line can reach logd late, so a send is
        # called lost only after a second look 1 s later: a late line taken
        # for the other path would switch to a path that drops the key.
        seen() { logcat -d --pid="$hp" -s AHAL_SecModulePrimary 2>/dev/null | $bb grep -F "configured g_call_sim_slot" | tail -n 1; }
        got() { a=$(seen); [ -n "$a" ] && [ "$a" != "$b" ]; }
        dlv() { sleep 0.5; got || { sleep 1; got; }; }
        # af needs the guest audioserver, which registers late (run 30).
        ready() { [ "$1" = hal ] || service check media.audio_policy 2>/dev/null | $bb grep -q ": found"; }
        other() { if [ "$1" = hal ]; then echo af; else echo hal; fi; }
        # Returns 1 when nothing was sent (no flag, no HAL pid, path not
        # ready yet), so the caller tries again on a later turn.
        setp() {
            [ -f /data/guest_audio.flag ] && [ -n "$hp" ] && ready $via || return 1
            b=$(seen); r=$(send $via "$1")
            if dlv; then ok="HAL got it"; else ok="HAL NEVER got it"; fi
            w=$(hal); echo "$(date +%T) g_call_sim_slot=$1 via $via ($2): $r; $ok; HAL state ${w:-none}"
            # Switch path once, and only on an idle 0x01 or 0x02, which set
            # the same VSID however often they come. Never resend a 0x10
            # swap: a late first copy plus a second one would swap back.
            [ "$ok" = "HAL got it" ] || [ "$1" = 0x10 ] || [ -n "$tried" ] || ! ready "$(other $via)" || {
                tried=1; via=$(other $via)
                b=$a; r=$(send $via "$1")
                if dlv; then w=$(hal); echo "$(date +%T) g_call_sim_slot=$1 again via $via: $r; HAL got it, path $via from now on; HAL state ${w:-none}"; return 0; fi
                echo "$(date +%T) g_call_sim_slot=$1 again via $via: $r; HAL NEVER got it on either path, staying on $first"
                via=$first
                logcat -d --pid="$hp" -t 400 2>/dev/null | $bb grep -i -E "vendor|parcel|g_call" | tail -n 4
            }
            return 0
        }
        # What the HAL log (its current pid) said last: A1/A2 a call runs on
        # VSID_1/2 (a 0x10 swap counts at once, its updateCalls lines can
        # come later), I1/I2 idle and the next call starts on VSID_1/2,
        # empty if nothing yet. mCurVSID is logged only when it changes.
        hal() {
            [ -n "$hp" ] || return
            logcat -d --pid="$hp" -s AHAL_Telephony_QTI 2>/dev/null | $bb grep -o -E "INACTIVE -> ACTIVE vsid:VSID_[12]|ACTIVE -> INACTIVE vsid:VSID_[12]|change vsid to VSID_[12] by|mCurVSID to VSID_[12]" | tail -n 1 | $bb sed -e "s/^INACTIVE.*_\([12]\)\$/A\1/" -e "s/^change.*_\([12]\) by\$/A\1/" -e "s/^[Am].*_\([12]\)\$/I\1/"
        }
        cur=""; last=$(cat /data/oneos_call_slot 2>/dev/null); call=""; n=0; hp=""; on=""
        echo "$(date +%T) started, last call on SIM slot ${last:-none}"
        while true; do
            sleep 2
            if [ -f /data/guest_audio.flag ]; then f=1; else f=0; fi
            [ "$f" = "$on" ] || { on=$f; echo "$(date +%T) guest_audio.flag $([ $f = 1 ] && echo present, watching calls || echo gone, idle)"; }
            [ $f = 1 ] || continue
            # A restarted HAL starts over on VSID_1.
            h=$(dumpsys --pid android.hardware.audio.core.IModule/default 2>/dev/null | tr -dc 0-9)
            [ "$h" = "$hp" ] || { echo "$(date +%T) audio HAL pid ${h:-none}"; hp=$h; cur=""; }
            # The path check (run 43), once, as soon as the HAL is known and
            # before any call: the SIM of the last call (the idle send below
            # would come first anyway), else 0x01, which a restarted HAL is on.
            [ -n "$probed" ] || [ -z "$hp" ] || ! ready $via || {
                probed=1
                if [ -n "$last" ]; then setp 0x0$((last + 1)) "path check, last call was on SIM slot $last" && cur=$last
                else setp 0x01 "path check, VSID_1 as the HAL starts"; fi
            }
            st=$(dumpsys telephony.registry 2>/dev/null | $bb awk -F= "/^ *Phone Id=/ { p = \$2 } /^ *mCallState=/ { print p \":\" \$2 }")
            [ -n "$st" ] || continue
            ring=""; off=""
            for e in $st; do
                case ${e#*:} in 1) ring=${e%:*} ;; 2) off=${e%:*} ;; esac
            done
            if [ -z "$off" ]; then
                call=""; n=0; t=${ring:-$last}
                if [ -n "$t" ] && [ "$t" != "$cur" ]; then
                    if [ -n "$ring" ]; then setp 0x0$((t + 1)) "SIM slot $t ringing"; else setp 0x0$((t + 1)) "last call was on SIM slot $t"; fi && cur=$t
                fi
                continue
            fi
            [ "$call" = "$off" ] || { call=$off; n=0; }
            [ $n -ge 3 ] && continue
            n=$((n + 1)); want=$((off + 1)); s=$(hal)
            case $s in
                ?$want) ;;
                A?) setp 0x10 "call on SIM slot $off runs on VSID_${s#A}" && n=3; sleep 0.5; s=$(hal) ;;
                *) setp 0x0$want "call on SIM slot $off, HAL ${s:-silent}"; sleep 0.5; s=$(hal) ;;
            esac
            echo "$(date +%T) call on SIM slot $off: HAL ${s:-?}"
            [ "${s#?}" = "$want" ] && n=3
            [ $n -ge 3 ] || continue
            last=$off; echo "$off" > /data/oneos_call_slot
            if [ "${s#?}" = "$want" ]; then cur=$off; else cur=""; fi
        done' sh "$BB" "${ONEOS_GUEST_CALL_SIM:-1}" "${ONEOS_GUEST_CALL_SIM_VIA:-}" </dev/null >> /data/call_audio.log 2>&1 &
fi

# ColorOS system daemons that its init would start on demand ("interface aidl"
# in cotad.rc / defrag.rc). The host's init refuses ctl.interface_start for
# services it does not know, and oplus-services waits for them.
for d in "/system_ext/bin/cotad" "/system_ext/bin/oplus_defrag"; do
    [ -x "$d" ] || continue
    "$d" > /dev/null 2>&1 &
    echo "[Pivoted Root] $(basename "$d") PID: $!"
done

# Overlay idmaps. idmap2 refuses the GSI's product overlays because framework-res
# does not declare the targeted resources as overlayable, so OMS ends up with no
# idmap at all and silently ignores every overlay: gesture navigation never
# applies (navbar stays 3-button) and the SystemUI accent overlays do nothing.
# Build the nav-bar idmap ourselves, before zygote can cache the empty overlay.
NAV_IDMAP="/data/resource-cache/system@product@overlay@NavigationBarModeGestural@NavigationBarModeGesturalOverlay.apk@idmap"
NAV_OV="/system/product/overlay/NavigationBarModeGestural/NavigationBarModeGesturalOverlay.apk"
mkdir -p /data/resource-cache
if [ ! -s "$NAV_IDMAP" ] && [ -f "$NAV_OV" ]; then
    echo "[Pivoted Root] Generating gesture-nav overlay idmap..."
    /system/bin/idmap2 create --target-apk-path /system/framework/framework-res.apk \
        --overlay-apk-path "$NAV_OV" --idmap-path "$NAV_IDMAP" --ignore-overlayable \
        > /data/idmap.log 2>&1 \
        && chmod 644 "$NAV_IDMAP" && chown system:system "$NAV_IDMAP" \
        && echo "[Pivoted Root] idmap OK ($(wc -c < "$NAV_IDMAP") bytes)" \
        || echo "[Pivoted Root] idmap FAILED: $(head -n1 /data/idmap.log 2>/dev/null)"
fi

# Newly installed apps have no data directories (the guest has no installd), and
# zygote kills their first launch with "Failed to mount /data_mirror/...". This
# sweep creates them while the guest runs, so Play Store/Aurora installs become
# launchable within ~15 s.
if [ -x /system/bin/setsid ]; then
    setsid /system/bin/sh /data/local/tmp/app_storage_loop.sh < /dev/null > /dev/null 2>&1 &
else
    /system/bin/sh /data/local/tmp/app_storage_loop.sh < /dev/null > /dev/null 2>&1 &
fi
echo "[Pivoted Root] App storage sweeper started..."


# Fresh netd for the guest. The DNS resolver lives in the host's netd and
# hands IDnsResolver.getUnstableInterface() to AID_SYSTEM only once; One UI's
# system_server took it at boot, so the guest's ConnectivityService died with
# "Already called by AID_SYSTEM". netd's rc has "onrestart restart zygote":
# oneos_switch.sh's loop stops the host zygote again, and the stale
# zygote sockets are removed just below, before the guest's launcher binds
# its own. Wifi is already down while the guest boots.
echo "[Pivoted Root] Restarting the host netd for a fresh DNS resolver..."
setprop ctl.restart netd
n=0
while [ $n -lt 50 ]; do
    [ "$(getprop init.svc.netd)" = running ] && service check dnsresolver 2>/dev/null | grep -q ": found" && break
    n=$((n + 1)); sleep 0.2
done
echo "[Pivoted Root] netd: $(getprop init.svc.netd), dnsresolver: $(service check dnsresolver 2>/dev/null | cut -d: -f2) after $((n / 5))s"
sleep 1


# Fresh GNSS HAL for the guest. The One UI app com.qualcomm.location holds the
# HAL A-GPS callback (vendor.qti.gnss ILocAidlAGnss.setCallbackExt), and libgnss
# keeps the callback with the higher priority (GnssAdapter::initAgpsCommand,
# cbPriority), so the IAGnss callback the guest sets at boot was ignored. That
# app died with One UI (run 34 16:28:34.332 IAGnssCallback died) and the guest
# image has none (IZatManager: IzatService not installed), so every SUPL data
# request went nowhere: 16:34:19.116 requestATL, Peer has gone, 15 s later
# LocSvc_Agps timeout. GPS ran without assistance and Weather gave up after
# 57 s four times. A restarted HAL has no callbacks until the guest sets its
# own. gnss_service has no onrestart actions and the return reboots anyway.
# ONEOS_GUEST_GNSS_RESTART=0 leaves the HAL alone.
if [ "${ONEOS_GUEST_GNSS_RESTART:-1}" != 0 ] && [ -n "$(getprop init.svc.gnss_service)" ]; then
    echo "[Pivoted Root] Restarting the vendor GNSS HAL (A-GPS callback for the guest)..."
    setprop ctl.restart gnss_service
    n=0
    while [ $n -lt 25 ]; do
        sleep 0.2; n=$((n + 1))
        [ "$(getprop init.svc.gnss_service)" = running ] && service check android.hardware.gnss.IGnss/default 2>/dev/null | grep -q ": found" && break
    done
    echo "[Pivoted Root] gnss_service: $(getprop init.svc.gnss_service), pid $(getprop init.svc_debug_pid.gnss_service) after $((n / 5))s"
else
    # Exynos phones (S.LSI: gpsd and an AIDL HAL, Galaxy Z Flip7 report 16e735f2)
    # have no gnss_service, so nothing above ran and the takeover log said
    # nothing: name the GNSS services that do run (property reads only).
    gnss_svcs=$(getprop | grep -iE '^\[init\.svc\.[^]]*(gnss|gps)' | sed 's/^\[init\.svc\.\([^]]*\)\]: \[\([^]]*\)\]$/\1=\2/' | tr '\n' ' ')
    echo "[Pivoted Root] GNSS HAL not restarted (no gnss_service, or ONEOS_GUEST_GNSS_RESTART=0); GNSS services: ${gnss_svcs:-none}"
fi

# OneOS: the guest's own idmap2d for the whole session (its overlay manager no
# longer asks host init to start One UI's, which cannot see the guest's
# partitions; switcher/patches/guest_own_idmap.py).
/system/bin/idmap2d > /data/idmap2d.log 2>&1 &
IDMAP_PID=$!
n=0
while [ $n -lt 25 ] && [ "$(dumpsys --pid idmap 2>/dev/null | tr -dc 0-9)" != "$IDMAP_PID" ]; do
    n=$((n + 1)); sleep 0.2
done
echo "[Pivoted Root] idmap2d PID: $IDMAP_PID, servicemanager's idmap: $(dumpsys --pid idmap 2>/dev/null | tr -dc 0-9)"
# The guest's own artd (guest_prepare.sh: whenever the guest's ART payload is mounted).
# artd is lazy: it exits when nothing holds it, so it runs again 0.2 s later,
# before servicemanager would ask init for One UI's. The loop ends with the guest
# (return_to_oneui.sh kills this namespace) or at /data/oneos_artd_stop.
if [ -f /data/oneos_guest_artd ] && [ -x /apex/com.android.art/bin/artd ]; then
    rm -f /data/oneos_artd_stop
    $BB sh -c '
        while [ ! -f /data/oneos_artd_stop ]; do
            /apex/com.android.art/bin/artd
            sleep 0.2
        done' </dev/null >> /data/artd.log 2>&1 &
    n=0
    while [ $n -lt 25 ] && [ -z "$(dumpsys --pid artd 2>/dev/null | tr -dc 0-9)" ]; do
        n=$((n + 1)); sleep 0.2
    done
    ARTD_PID=$(dumpsys --pid artd 2>/dev/null | tr -dc 0-9)
    echo "[Pivoted Root] artd: the guest's (servicemanager's artd: ${ARTD_PID:-none yet}, $(readlink /proc/${ARTD_PID:-0}/exe 2>/dev/null || echo 'exe unknown'))"
else
    echo "[Pivoted Root] artd: One UI's (guest_prepare.sh chose it: no guest ART payload, or ONEOS_GUEST_ARTD=0)"
fi
if [ -f /data/guest_media.flag ]; then
    echo "[Pivoted Root] media.player: $(service check media.player 2>/dev/null | cut -d: -f2), media.resource_manager: $(service check media.resource_manager 2>/dev/null | cut -d: -f2)"
fi

# The guest vold names, last before the guest framework starts (see above).
if [ "$VOLD_NAME" = gvld ]; then
    why=$(host_vold_lost)
    [ "$(svc_pid gvld)" = "$VOLD_PID" ] || why="servicemanager's gvld is pid '$(svc_pid gvld)', not the guest vold's $VOLD_PID"
    if [ -n "$why" ]; then
        echo "[Pivoted Root] FATAL: $why. Not starting the guest."
        exit 1
    fi
    echo "[Pivoted Root] Before zygote: gvld is the guest vold's ($VOLD_PID); vold One UI's ($HOST_VOLD), android.system.vold.IVold/default $(vdef)"
fi

# Forced JIT zygote (run 44). OneLineage's zygote_exec always passed
# -Xforcejitzygote, and so did ours: ART then ignores the image's own AOT boot
# image (/system/framework/arm64/boot*.art/.oat/.vdex, built with the image
# for its ART module and framework jars), compiles the boot class path in
# memory at every zygote start (run 44: dex2oat64 --compiler-filter=verify
# --oat-location=/nonx/arm64/boot.oat, 1.4 s, 3.4 s CPU) and runs framework
# code JIT-compiled only, in every guest process. zygote_exec (zygote_launcher.c)
# passes the flag only with ONEOS_GUEST_JIT_ZYGOTE=1. Up to 0.4.75 that was
# the default for ColorOS guests (oplus-services.jar). 0.4.76: 0 for every
# guest. The owner's Fold in ColorOS 17 (11-10, "too hot on any OS"): no
# process had one .oat/.odex/.art mapped, the switch took the skin from 40 to
# 57.7 C in a minute (system_server 200% CPU, SystemUI 97%), and a trial
# odrefresh in the running guest built its boot image in 10 s; a guest tool
# then started on 0.05 s of CPU instead of 0.26 s. The odrefresh step below
# builds that boot image; without one ART compiles the boot class path in
# memory, as with the flag.
case "${ONEOS_GUEST_JIT_ZYGOTE:-}" in
    0|1) JIT_WHY="ONEOS_GUEST_JIT_ZYGOTE=$ONEOS_GUEST_JIT_ZYGOTE" ;;
    *)
        [ -n "${ONEOS_GUEST_JIT_ZYGOTE:-}" ] && echo "[Pivoted Root] ONEOS_GUEST_JIT_ZYGOTE=$ONEOS_GUEST_JIT_ZYGOTE is not 0 or 1: the default"
        ONEOS_GUEST_JIT_ZYGOTE=0; JIT_WHY="default" ;;
esac
export ONEOS_GUEST_JIT_ZYGOTE
if [ "$ONEOS_GUEST_JIT_ZYGOTE" = 1 ]; then
    echo "[Pivoted Root] zygote: -Xforcejitzygote ($JIT_WHY): boot class path compiled in memory, framework JIT only"
else
    # Whether ART can take that image: besides the jars' checksums (the image's
    # own jars, art_payload.img and i18n_payload.img from the image's APEXes)
    # it checks the boot oat's apex-versions (the image's build: "/" for each
    # factory module) against the versions /apex/apex-info-list.xml gives the
    # boot class path's modules. guest_prepare.sh copies One UI's list there
    # when the set has no clean_apex_info_list.xml, and an updated One UI ART
    # module makes ART reject the image (run 44's guest app_process tools:
    # "ValidateApexVersions found APEX versions mismatch ... Oat file:
    # '//////', Runtime: '/1792624397/..."). The zygote then compiles the boot
    # class path in memory, as with the flag. Read only.
    UPD=$(awk 'BEGIN { RS = "<" } /^apex-info[[:space:]]/ && /moduleName="com\.android\.(art|i18n)"/ && /isActive="true"/ && /isFactory="false"/ {
        m = $0; sub(/.*moduleName="/, "", m); sub(/".*/, "", m); printf "%s ", m }' /apex/apex-info-list.xml 2>/dev/null)
    BOOT_OATS=$(ls /system/framework/arm64/boot*.oat 2>/dev/null | wc -l)
    if [ -n "$UPD" ]; then
        echo "[Pivoted Root] zygote: the image's boot image ($JIT_WHY, $BOOT_OATS oat files), but /apex/apex-info-list.xml has ${UPD}as updated: ART will reject it (APEX versions) and compile the boot class path in memory"
    else
        echo "[Pivoted Root] zygote: the image's boot image ($JIT_WHY): $BOOT_OATS oat files in /system/framework/arm64, no updated ART or i18n module in /apex/apex-info-list.xml"
    fi
fi

echo "[Pivoted Root] Cleaning stale sockets..."
rm -f /dev/socket/zygote /dev/socket/usap_pool_primary 2>/dev/null || true

# HyperOS starts its "rust" packages (the launcher with Recents, Weather; their
# code is a Flutter library, the APK has no dex) through hyos_spawner, a
# zygote-like server its own init starts with "socket hyos_spawner stream 0660
# root system" once zygote runs and rust.runtime_active=1. One UI's init has
# no such service: with the rust path off (0.4.16) zygote started the launcher
# with no code, and it died 1008 times in 4 minutes (sixth HyperOS run). Start
# it here with its socket (socket_exec, the HyperOS set's), as root with the
# socket for group system like the image's rc. guest_props.sh set the two
# properties HyperOS's init would (rust.runtime_version, rust.runtime_active=1),
# and the return sweeps the spawner with the other guest processes.
if [ -x /system_ext/bin/hyos_spawner ] && [ -x /data/socket_exec ]; then
    rm -f /dev/socket/hyos_spawner
    /data/socket_exec hyos_spawner /system_ext/bin/hyos_spawner /system_ext/bin --spawner --start-spawner-server \
        </dev/null >/data/hyos_spawner.log 2>&1 &
    echo "[Pivoted Root] hyos_spawner PID: $! (socket /dev/socket/hyos_spawner)"
fi

# Samsung Camera's working folder /data/sec/camera for the camera's uid
# (guest_prepare.sh makes it when the app's data folder is already there). On a
# stage where the camera never ran, the guest's package manager makes that
# folder during boot: the folder is made then, before anyone opens the camera.
# Without it the camera's post-processing fails ("can't create secureDirectory")
# and the picture is lost (0.4.58 report f794c15d). Five minutes at most.
if [ -f /data/oneos_samcam ] && [ ! -L /data/sec ]; then
    ONEOS_BB="$BB" $BB sh -c '
        i=0
        while [ $i -lt 300 ]; do
            for d in /data/user/0/com.sec.android.app.camera /data/user_de/0/com.sec.android.app.camera; do
                [ -d "$d" ] && [ ! -L "$d" ] || continue
                u=$(stat -c %u "$d" 2>/dev/null)
                [ -n "$u" ] && [ "$u" -ge 10000 ] || continue
                if [ "$(stat -c %u /data/sec/camera 2>/dev/null)" = "$u" ]; then echo "$(date +%T) /data/sec/camera is already the camera uid $u"; exit 0; fi
                [ -L /data/sec/camera ] && { echo "/data/sec/camera is a link: left alone"; exit 1; }
                mkdir -p /data/sec/camera && chown 0:0 /data/sec && chmod 771 /data/sec &&
                    chown "$u:$u" /data/sec/camera && chmod 2770 /data/sec/camera &&
                    "$ONEOS_BB" chcon -R u:object_r:app_data_file:s0 /data/sec 2>/dev/null
                echo "$(date +%T) /data/sec/camera made for the camera (uid $u, from $d)"
                exit 0
            done
            i=$((i + 1)); sleep 1
        done
        echo "$(date +%T) no Samsung Camera data folder after 300 s: /data/sec/camera not made"
    ' </dev/null >> /data/sec_camera.log 2>&1 &
fi
# What folding does, set as soon as the guest's settings provider answers. The
# UI activator sets it too, but only once the UI is up: a Fold switched while
# folded started Pixel in state 2 (open; the hinge sensor had not reported
# yet), the first hinge event 4 s later folded it to state 0 with "sleep on
# fold", and the screen went off at 02:19:55, eleven seconds before the
# activator's setting (Z Fold8 Ultra, session 9455098f). Same values and rule
# as the activator (a stage set to sleep is kept). Only the guest's own
# provider is asked (its mount namespace is this one), each call bounded by
# timeout: One UI's services are not to be called during the switch.
if [ "$(cat /data/oneos_fold_mode 2>/dev/null)" = layout ] && [ "${ONEOS_GUEST_FOLD_CONTINUE:-1}" = 1 ]; then
    if [ -e /system/framework/oplus-services.jar ]; then FOLDN=continue_using_apps_when_folded; FOLDV=1; else FOLDN=fold_lock_behavior_setting; FOLDV=stay_awake_on_fold_key; fi
    $BB sh -c "
        SELF=\$(readlink /proc/self/ns/mnt); i=0
        while [ \$i -lt 2000 ]; do
            p=\$(timeout 2 dumpsys --pid settings 2>/dev/null | tr -dc 0-9)
            if [ -n \"\$p\" ] && [ \"\$(readlink /proc/\$p/ns/mnt 2>/dev/null)\" = \"\$SELF\" ]; then
                cur=\$(timeout 5 settings get system $FOLDN 2>/dev/null)
                case \"$FOLDN:\$cur\" in
                    continue_using_apps_when_folded:1|continue_using_apps_when_folded:2|fold_lock_behavior_setting:stay_awake_on_fold_key|fold_lock_behavior_setting:sleep_on_fold_key) ;;
                    *) timeout 5 settings put system $FOLDN $FOLDV 2>/dev/null ;;
                esac
                echo \"\$(date +%T) $FOLDN: \$cur -> \$(timeout 5 settings get system $FOLDN 2>/dev/null) (the guest's settings provider, pid \$p)\"
                exit 0
            fi
            i=\$((i + 1)); sleep 0.3
        done
        echo \"\$(date +%T) $FOLDN: the guest's settings provider did not answer in 10 minutes; the UI activator sets it\"
    " </dev/null >> /data/fold_setting.log 2>&1 &
    echo "[Pivoted Root] Fold behaviour: $FOLDN=$FOLDV as soon as the guest's settings provider answers (/data/fold_setting.log)"
fi
# vivo OriginOS's glass (real-time blur): SystemUI's material SDK
# (com.spacesystem.materialsdk.Material.resolveGlassSetting) and its plugins
# draw glass only when system setting realtime_blur_state is 1, reading 0 when
# it is unset; vivo's first boot sets it, the guest's never did (tenth run:
# "isGlassEffectEnabled realtimeBlurState=0", no blur anywhere). Set once, only
# while unset (a 0 the user chose in Settings stays); the SDK watches the
# setting. ONEOS_GUEST_VIVO_BLUR=0 leaves it alone.
if [ -e /system/framework/vivo-services.jar ] && [ "${ONEOS_GUEST_VIVO_BLUR:-1}" = 1 ]; then
    # Asked straight: during the session the only settings service is the guest's
    # (One UI's system_server is stopped); a call before it is up fails and is
    # retried. (Matching its pid through dumpsys --pid never succeeded on vivo's
    # build, runs 12 and 13: the setting stayed unset.)
    $BB sh -c "
        i=0
        while [ \$i -lt 600 ]; do
            cur=\$(timeout 5 settings get system realtime_blur_state 2>/dev/null)
            case \"\$cur\" in
                null) timeout 5 settings put system realtime_blur_state 1 2>/dev/null
                      echo \"\$(date +%T) realtime_blur_state: unset -> \$(timeout 5 settings get system realtime_blur_state 2>/dev/null)\"; exit 0 ;;
                0|1) echo \"\$(date +%T) realtime_blur_state: \$cur (set already, left)\"; exit 0 ;;
            esac
            i=\$((i + 1)); sleep 1
        done
        echo \"\$(date +%T) realtime_blur_state: the guest's settings service did not answer in 10 minutes\"
    " </dev/null >> /data/vivo_blur.log 2>&1 &
    echo "[Pivoted Root] vivo glass: realtime_blur_state=1 if unset, once the guest's settings provider answers (/data/vivo_blur.log)"
fi
# vivo's transition animation server (vivonrtservice, "vivo_nrt_service"): vivo's
# launcher runs its app open and close animations in it (com.bbk.launcher2's
# AnimationServer). vivo's init starts it (class core, user system) once
# persist.vivo.nrtservice is true; the guest has no init of its own, so it never ran:
# "AnimationServer: Service.INSTANCE is null", and every launch from or return to
# home waited about 2 s for an animation that never played (tenth CN run). Started
# here as system, again if it exits, until the namespace ends (the return) or
# /data/oneos_nrt_stop. It talks to SurfaceFlinger only (libgui), and its one vivo
# node (/sys/rsc/rsc_svp) is missing on a Samsung kernel. ONEOS_GUEST_VIVO_NRT=0
# leaves it off.
if [ -x /system/bin/vivonrtservice ] && [ "${ONEOS_GUEST_VIVO_NRT:-1}" = 1 ]; then
    rm -f /data/oneos_nrt_stop
    ONEOS_BB="$BB" $BB sh -c '
        n=0
        while [ ! -f /data/oneos_nrt_stop ] && [ $n -lt 30 ]; do
            $ONEOS_BB setuidgid system /system/bin/vivonrtservice
            echo "$(date +%T) vivonrtservice exited ($?)"
            n=$((n + 1)); sleep 1
        done' </dev/null >> /data/vivo_nrt.log 2>&1 &
    echo "[Pivoted Root] vivo transition animations: vivonrtservice started as system (/data/vivo_nrt.log)"
fi
# vivo's setup skipped (guest_prepare.sh hides vivo's setup wizard, ONEOS_GUEST_VIVO_SETUP
# unset): guest_prepare.sh seeds the provisioned keys only into settings files that
# exist, and a fresh /data has none before its first boot. Without them the guest
# stays "not provisioned" (no notifications or quick settings) with no wizard to
# finish it. Set once the guest's settings service answers, only where not 1.
if [ -e /system/framework/vivo-services.jar ] && [ "${ONEOS_GUEST_VIVO_SETUP:-0}" != 1 ]; then
    $BB sh -c "
        i=0
        while [ \$i -lt 600 ]; do
            cur=\$(timeout 5 settings get global device_provisioned 2>/dev/null)
            case \"\$cur\" in
                1|0|null)
                    for kv in 'global device_provisioned' 'secure user_setup_complete' 'secure setup_wizard_has_run'; do
                        set -- \$kv
                        [ \"\$(timeout 5 settings get \$1 \$2 2>/dev/null)\" = 1 ] && continue
                        timeout 5 settings put \$1 \$2 1 2>/dev/null
                        echo \"\$(date +%T) \$1 \$2 -> \$(timeout 5 settings get \$1 \$2 2>/dev/null)\"
                    done
                    exit 0 ;;
            esac
            i=\$((i + 1)); sleep 1
        done
        echo \"\$(date +%T) the guest's settings service did not answer in 10 minutes\"
    " </dev/null >> /data/vivo_setup.log 2>&1 &
    echo "[Pivoted Root] vivo setup: device_provisioned, user_setup_complete, setup_wizard_has_run = 1 where not, once the guest's settings provider answers (/data/vivo_setup.log)"
fi
# Test build 8 had an event-driven keeper (inotifyd on the guest's opens and
# closes, the touchscreens held all session): the guest never showed a close
# there, so it armed late or not at all and double tap stopped working (owner,
# 11-06 18:40). This is build 6's keeper, which worked, polling every 0.1 s
# (was 0.25 s) to arm sooner after the screen goes dark.
# Double tap to wake (Pixel on the Z Fold8 Ultra, 0.4.59 test: none). On a
# Galaxy the touch IC sees the double tap itself, in its low-power mode, and
# reports it as KEY_WAKEUP on the touchscreen's own input device. One UI puts it
# there (its logcat and kernel log in One UI, 11-06): its input manager keeps
# the touchscreen open and, through Samsung's sysinput HAL, writes the panel's
# display state to /sys/class/sec/tspN/enabled, "1,0" then "1,1" as the panel
# goes off (the IC enters low-power mode on the first) and "2,0" then "2,1" as
# it comes on (it leaves it on the second), and set_fold_state,0|1 to
# tspN/cmd on every fold. A guest does neither: its InputReader closes the
# touchscreen while the panel is off, so the tap goes to nobody. This keeper
# does One UI's part for the panel in use: when it goes off, it holds that
# touchscreen open, writes "1,0" and "1,1", and on KEY_WAKEUP wakes the guest
# (cmd input keyevent WAKEUP; not during a call, when the screen is off for the
# proximity sensor); when the panel comes on, it writes "2,0" and "2,1" and
# lets go. It writes "on" only to a touchscreen it put in low-power mode
# (/data/oneos_dt2w_armed.<tsp>; the return does the same for one left so).
# A panel is off when its DSI connector says dpms Off and its backlight is 0
# (an AOD panel counts as on: no double tap on AOD yet); the fold state
# follows the lit panel. From the end of the boot animation; ends with the
# guest. ONEOS_GUEST_DT2W=0 turns it off, =1 on for every guest.
# ColorOS was left alone up to build 105 ("double tap works there"). It does
# not (owner, 11-10, Z Fold8 Ultra): its gesture needs OPPO's touch HAL; on a
# Galaxy nobody writes the IC's enabled node when ColorOS sleeps (kernel log of
# that session: not one enabled_store while it slept, the cover IC went on
# reporting plain touches), so the IC never reports KEY_WAKEUP. Build 106 kept
# only the IC of a panel that is off by its dpms. ColorOS shows its clock for
# about 7 s after every sleep with the panel still on (display state
# DOZE_SUSPEND, dpms On), so the double tap came 8 s late (dt2w.log against
# power_screen_state of that session: asleep 11:44:11, armed 11:44:19) and
# never with the clock set to always. Now every Oplus guest is kept, on every
# phone (owner: the ColorOS builds on the S25 and S26 series behave the same),
# and every guest sleep arms the IC in use, panel lit or not, as on a vivo
# image. On a fold a panel is off by its dpms alone, and the lid switch tells
# which panel is in use after a fold made with the screen off.
DT2W=${ONEOS_GUEST_DT2W:-1}
if [ "$DT2W" = 1 ] && command -v getevent >/dev/null 2>&1 && { [ -w /sys/class/sec/tsp/enabled ] || [ -w /sys/class/sec/tsp1/enabled ]; }; then
    rm -f /data/oneos_dt2w_armed.* /data/oneos_dt2w_*.fifo /data/oneos_dt2w_aod* /data/oneos_dt2w_lid*
    ONEOS_BB="$BB" $BB sh -c '
        BB=$ONEOS_BB
        log() { echo "$(date +%T) $*"; }
        i=0
        while [ "$(getprop service.bootanim.exit)" != 1 ] && [ $i -lt 600 ]; do sleep 1; i=$((i + 1)); done
        IDS=""
        for t in tsp tsp1 tsp2; do
            T=/sys/class/sec/$t
            [ -w $T/enabled ] || continue
            ev=""; I=$T/input
            for e in $I/event*; do [ -e "$e" ] && ev=${e##*/}; done
            # Some drivers have no input link under sec/tsp (S24 FE, 0.4.59 report 8e514969):
            # the touchscreen of the main panel by its name instead, as oneos_switch.sh finds it.
            if [ -z "$ev" ] && [ $t = tsp ]; then
                for e in /sys/class/input/event*; do
                    [ "$(cat $e/device/name 2>/dev/null)" = sec_touchscreen ] && { ev=${e##*/}; I=$e/device; break; }
                done
            fi
            [ -n "$ev" ] && [ -c /dev/input/$ev ] || { log "$t: no input device under $T/input"; continue; }
            # What enabled reads while the IC is on: 1 on the newer drivers (on or off: Z
            # Fold8 Ultra, S24, S25, the A series), 2 on the older ones, which show the power
            # state (2 on, 1 low-power mode, 0 off: S22 Ultra, S23 series). The older ones
            # were left out from 0.4.60 to build 115 for "no touch for the whole session"
            # (0.4.59 reports 9dbcda58, 7b972a82, 2c9c6419); that was this keeper, see
            # tsp_off below: it took the answer to 1,1 for a refusal after 1,0 had put the
            # IC in low-power mode, and at that time did not switch it back on.
            e0=$(cat $T/enabled 2>/dev/null)
            case "$e0" in 0|1) eon=1 ;; 2) eon=2 ;; *) log "$t ($ev): enabled reads ${e0:-nothing}, not a known protocol: double tap left to the guest"; continue ;; esac
            # KEY_WAKEUP (143) among its keys: bit 15 of the third word from the end.
            set -- $(cat $I/capabilities/key 2>/dev/null)
            w=""; [ $# -ge 3 ] && eval w=\${$(($# - 2))}
            w=0000$w; w=${w#${w%????}}
            if [ $(( 0x$w & 0x8000 )) = 0 ]; then log "$t ($ev): no KEY_WAKEUP among its keys"; continue; fi
            case $t in
                tsp2) C=/sys/class/drm/card0-DSI-2/dpms; B=/sys/class/backlight/panel1-backlight; [ -e $B/brightness ] || B=/sys/class/backlight/panel1 ;;
                *) C=/sys/class/drm/card0-DSI-1/dpms; B=/sys/class/backlight/panel0-backlight; [ -e $B/brightness ] || B=/sys/class/backlight/panel ;;
            esac
            [ -r $B/brightness ] || { log "$t ($ev): no backlight to follow ($B)"; continue; }
            eval "EV_$t=$ev C_$t=$C B_$t=$B/brightness ON_$t=1 L_$t=1 GP_$t= EON_$t=$eon"
            IDS="$IDS $t"
            log "$t: $ev ($(cat $I/name 2>/dev/null)), panel $C=$(cat $C 2>/dev/null), $B=$(cat $B/brightness 2>/dev/null), enabled=$(cat $T/enabled 2>/dev/null)"
        done
        [ -n "$IDS" ] || { log "no touchscreen to keep: double tap left to the guest"; exit 0; }
        FOLD=0; case "$IDS" in *tsp1*tsp2*) FOLD=1 ;; esac
        # The dpms-only reading is proven on vivo OriginOS (0.4.73); other systems keep both signals.
        VIVO_IMG=0; [ -e /system/framework/vivo-services.jar ] && VIVO_IMG=1
        # ColorOS on the same phone: the panel not in use reads backlight 0 (fold_test.log,
        # 11-10) and its clock (AOD) is dpms On, so dpms alone says "off" there too.
        OPLUS_IMG=0; [ -e /system/framework/oplus-services.jar ] && OPLUS_IMG=1
        # Two panels: the dpms of each panel only. The panel that is off keeps backlight 1,
        # not 0 (F8U run 13, OriginOS: inner panel0-backlight 1 with DSI-1 Off once
        # folded, cover panel1-backlight 1 with DSI-2 On in AOD), so "backlight not 0"
        # kept the inner panel lit: the fold was never seen, the cover never got
        # low-power mode, and a double tap on the cover AOD reached the guest as
        # plain touches while it slept. One panel keeps both signals.
        lit() {
            eval c=\$C_$1 b=\$B_$1
            d=Off; [ -r "$c" ] && read -r d < "$c"
            if [ $FOLD = 1 ] && { [ $VIVO_IMG = 1 ] || [ $OPLUS_IMG = 1 ]; } && [ -r "$c" ]; then [ "$d" != Off ]; return; fi
            l=0; read -r l < "$b"
            [ "$d" != Off ] || [ "$l" != 0 ]
        }
        F=""
        for t in $IDS; do if lit $t; then eval ON_$t=1 L_$t=1; else eval ON_$t=0 L_$t=0; fi; done
        [ $FOLD = 1 ] && { if [ $L_tsp1 = 1 ]; then F=0; elif [ $L_tsp2 = 1 ]; then F=1; fi; }
        log "keeping:$IDS (fold $FOLD, folded ${F:-unknown}); panels lit:$(for t in $IDS; do eval echo -n \" $t=\$ON_$t\"; done)"
        in_call() {
            timeout 3 dumpsys telephony.registry 2>/dev/null | grep -q "mCallState=[12]"
        }
        # AOD (test build 9, 11-06 22:51-22:55: no double tap on AOD). Pixel
        # SystemUI here has doze_display_state_supported=false (Pixel sets it in
        # its vendor overlay), so DozeService asks for STATE_ON ("UpdateDoze
        # mDozeScreenState=2"): the AOD panel stays dpms On at its lowest
        # backlight, like a dim home screen, and only the guest knows it sleeps.
        # Its Notifier logs power_screen_state [0,...] going to sleep and [1,...]
        # waking; one blocked logcat keeps /data/oneos_dt2w_aod at 1 while the
        # guest sleeps with AOD on (doze_always_on=1, read once per sleep), so a
        # lit panel then gets low-power mode like a dark one. With AOD off a lit
        # panel while asleep is a notification pulse and keeps its touch, as on a
        # Pixel. Anything but 1 is no AOD: before the first event, after the
        # reader ends, after a system_server start and after a double tap, so
        # touch is never taken from an awake guest. ONEOS_GUEST_DT2W_AOD=0: off.
        # vivo keeps the panel lit in its own AOD (keyguard_aod, not doze_always_on;
        # tenth CN run: the panel never read as off, nothing was armed): on a vivo
        # image every guest sleep counts as AOD here, panel lit or not.
        VAOD=0
        [ -e /system/framework/vivo-services.jar ] && VAOD=${ONEOS_GUEST_VIVO_AOD:-3}
        case "$VAOD" in ""|*[!0-9]*) VAOD=0 ;; esac
        [ "$VAOD" -le 20 ] || VAOD=20
        AF=/data/oneos_dt2w_aod
        setaod() { echo $1 > $AF.n && $BB mv -f $AF.n $AF; }
        setaod 0
        # An Oplus guest keeps its clock on a lit panel (DOZE_SUSPEND, dpms On: about
        # 7 s after every sleep, or always) and does not read the taps there (owner,
        # 11-10, build 106): on an Oplus image every guest sleep counts as AOD too.
        AODR=${ONEOS_GUEST_DT2W_AOD:-1}
        # Lid switch (Oplus guest on a fold). The fold state above follows the lit
        # panel, which says nothing once the phone is folded or opened while it
        # sleeps: the IC of the panel now in use was never armed. One blocked
        # getevent on the "flip" switch keeps /data/oneos_dt2w_lid at 1 (folded),
        # 0 (open) or u (not known: before the first event, after the reader
        # ends); a lit panel still wins. No flip switch: lit panels only, as before.
        LIDF=0; LF=/data/oneos_dt2w_lid; LV=u; OLV=u
        if [ $FOLD = 1 ] && [ $OPLUS_IMG = 1 ]; then
            FL=""
            for e in /sys/class/input/event*; do
                [ "$(cat $e/device/name 2>/dev/null)" = flip ] && { FL=/dev/input/${e##*/}; break; }
            done
            setlid() { echo $1 > $LF.n && $BB mv -f $LF.n $LF; }
            if [ -n "$FL" ] && [ -c "$FL" ] && setlid u; then
                ( getevent -l $FL 2>/dev/null | while read -r a k v; do
                      [ "$k" = SW_LID ] || continue
                      case "$v" in 00000001) setlid 1 ;; 00000000) setlid 0 ;; esac
                  done
                  setlid u
                  log "lid: the reader of $FL ended: fold state from the lit panel only" ) &
                LIDF=1
                log "lid: $FL read for folds made while the screen is off"
            else
                log "lid: no flip switch to read: fold state from the lit panel only"
            fi
        fi
        if [ "$AODR" = 1 ]; then
            ( n=0
              while [ $n -lt 20 ]; do
                  logcat -b events -v raw -s power_screen_state boot_progress_system_run -T "$(date +%s).000" 2>/dev/null |
                      while read -r l; do
                          case "$l" in
                              "[0,"*) { [ -e /system/framework/vivo-services.jar ] || [ $OPLUS_IMG = 1 ] || [ "$(timeout 3 settings get secure doze_always_on 2>/dev/null)" = 1 ]; } && setaod 1 ;;
                              "[1,"*|[0-9]*) setaod 0 ;;
                          esac
                      done
                  setaod 0
                  n=$((n + 1))
                  log "AOD: the reader of the guest sleep and wake events ended ($n): no AOD assumed"
                  sleep 5
              done
              log "AOD: reader given up: no double tap on AOD this session" ) &
        fi
        # Only two of the four writes do anything in the driver: 1,0 (the IC goes to
        # low-power mode when a wake gesture is on in One UI, else off) and 2,1 (on).
        # 1,1 and 2,0 are the other half of what One UI writes. The drivers up to the
        # kernel 6.1 generation (S24 Exynos, S23 FE, A25, A34, A35; public sec_cmd
        # sources: enabled_store ends in "if (ret) return ret" with ret still the 2 of
        # its sscanf) answer those two with a short write; the shell writes the rest
        # and that fails with "Invalid argument". Up to build 115 that error, after a
        # 1,0 that had worked, was read as a refusal: the IC was switched back on and
        # double tap given up for the session, in every session on those phones
        # (reports of 0.4.83 to 0.4.85). Only the write that acts decides now; the
        # other is still sent, as One UI does, and its answer is not read.
        tsp_off() { echo 1,0 > $1/enabled || return 1; echo 1,1 > $1/enabled 2>/dev/null; return 0; }
        tsp_on() { echo 2,0 > $1/enabled 2>/dev/null; echo 2,1 > $1/enabled; }
        # enabled, and 2 once seen is what this IC reads while on (an older driver that
        # was off or asleep at the first read).
        tsp_read() {
            e=$(cat /sys/class/sec/$1/enabled 2>/dev/null)
            [ "$e" = 2 ] && eval EON_$1=2
            eval eon=\$EON_$1
        }
        arm() {
            eval g=\$GP_$1 no=\$NO_$1
            [ -z "$g" ] && [ -z "$no" ] || return 0
            T=/sys/class/sec/$1; eval ev=\$EV_$1
            P=/data/oneos_dt2w_$1.fifo
            rm -f $P; $BB mkfifo $P || { log "$1: no fifo"; return; }
            getevent -l /dev/input/$ev > $P 2>/dev/null &
            g=$!
            eval GP_$1=$g
            ( while read -r a k v; do
                  [ "$k" = KEY_WAKEUP ] && [ "$v" = DOWN ] || continue
                  if [ $LIDF = 1 ]; then
                      # The panel not in use: inner while folded, cover while open.
                      lv=u; { read -r lv < $LF; } 2>/dev/null
                      case "$1$lv" in tsp11|tsp20) log "$1: double tap on the panel not in use (lid $lv): ignored"; continue ;; esac
                  fi
                  if in_call; then log "$1: double tap during a call: ignored"; continue; fi
                  log "$1: double tap: waking the guest"
                  timeout 5 cmd input keyevent KEYCODE_WAKEUP >/dev/null 2>&1 || log "$1: cmd input keyevent failed"
                  setaod 0
              done < $P ) &
            # 1,0 only counts once getevent holds the touchscreen: the driver closes only
            # a device somebody has open, and the guest lets go of it when its panel goes
            # off. Written before that open it does nothing, and the open then powers the
            # IC fully on: plain touches all night, no double tap. getevent opens it after
            # the reader above has opened the fifo, so a fixed wait can be too short.
            i=0
            while [ $i -lt 20 ]; do
                sleep 0.05
                ls -l /proc/$g/fd 2>/dev/null | grep -q "/dev/input/$ev\$" && break
                i=$((i + 1))
            done
            [ $i -lt 20 ] || log "$1: getevent has not opened $ev after 1 s"
            # The marker first: only a marked IC is ever put back on (here, by wake_tsp
            # and by the return).
            : > /data/oneos_dt2w_armed.$1
            if tsp_off $T; then
                tsp_read $1
                log "$1: $2: low-power mode (enabled=$e)"
            else
                log "$1: panel off, but $T/enabled refused 1,0: back on, double tap left to the guest"
                tsp_on $T
                tsp_read $1
                [ "$e" = "$eon" ] && rm -f /data/oneos_dt2w_armed.$1
                disarm $1
                eval NO_$1=1
            fi
        }
        disarm() {
            eval g=\$GP_$1
            [ -n "$g" ] && kill $g 2>/dev/null
            eval GP_$1=
            rm -f /data/oneos_dt2w_$1.fifo
        }
        wake_tsp() {
            T=/sys/class/sec/$1
            [ -f /data/oneos_dt2w_armed.$1 ] || { disarm $1; return; }
            tsp_on $T
            tsp_read $1
            [ "$e" = "$eon" ] || { sleep 0.2; tsp_on $T; tsp_read $1; }
            rm -f /data/oneos_dt2w_armed.$1
            disarm $1
            log "$1: $2: enabled=$e"
        }
        # Lid path only. A fold made in the dark changes which IC is in use while
        # both panels stay off. The driver chooses between low-power mode and
        # power off at the moment it is disabled, by the fold state it has then,
        # and ignores 1,0 on an IC that is already disabled (the fold monitor
        # disables the cover IC at every unfold; an IC armed before the fold was
        # disabled under the other fold state). So bring it up under the new fold
        # state first (2,0 2,1), then low-power mode as usual.
        arm_fresh() {
            T=/sys/class/sec/$1
            eval g=\$GP_$1 no=\$NO_$1
            [ -z "$no" ] || return 0
            if [ -n "$g" ]; then
                tsp_on $T
                if tsp_off $T; then
                    tsp_read $1
                    log "$1: $2: low-power mode again under folded=$F (enabled=$e)"
                else
                    log "$1: $2: $T/enabled refused 1,0 under folded=$F: back on, double tap left to the guest"
                    tsp_on $T
                    tsp_read $1
                    [ "$e" = "$eon" ] && rm -f /data/oneos_dt2w_armed.$1
                    disarm $1
                    eval NO_$1=1
                fi
                return 0
            fi
            if [ "$(cat $T/enabled 2>/dev/null)" = 0 ]; then
                tsp_on $T
                tsp_read $1
                log "$1: off before arming (folded=$F): switched on first (enabled=$e)"
            fi
            arm $1 "$2"
        }
        while :; do
            D=; read -r D < $AF 2>/dev/null; [ "$D" = 1 ] || D=0
            if [ $LIDF = 1 ]; then LV=u; { read -r LV < $LF; } 2>/dev/null; fi
            CH=""; LC=""
            for t in $IDS; do
                if lit $t; then l=1; else l=0; fi
                s=$l; [ $D = 1 ] && s=0
                eval o=\$ON_$t ol=\$L_$t
                [ $l = $ol ] || { eval L_$t=$l; LC=1; }
                [ $s = $o ] && continue
                eval ON_$t=$s
                CH="$CH $t"
            done
            if [ $FOLD = 1 ] && { [ -n "$LC" ] || [ "$LV" != "$OLV" ]; }; then
                OLV=$LV
                n=$F; by="lit panel"
                if [ $L_tsp1 = 1 ]; then n=0; elif [ $L_tsp2 = 1 ]; then n=1; else case "$LV" in 0|1) n=$LV; by="lid switch, both panels off" ;; esac; fi
                if [ "$n" != "$F" ]; then
                    F=$n
                    for t in tsp1 tsp2; do echo set_fold_state,$F > /sys/class/sec/$t/cmd 2>/dev/null; done
                    log "folded=$F: set_fold_state,$F ($by)"
                    # AOD moved to the other panel while asleep: arm the one now in use.
                    for t in tsp1 tsp2; do eval s=\$ON_$t; [ $s = 0 ] && case " $CH " in *" $t "*) ;; *) CH="$CH $t" ;; esac; done
                fi
            fi
            for t in $CH; do
                eval s=\$ON_$t l=\$L_$t
                if [ $s = 1 ]; then
                    eval PA_$t=0
                    wake_tsp $t "panel on"
                else
                    if [ $l = 1 ]; then w="AOD (guest asleep, panel lit)"; else w="panel off"; fi
                    a=1
                    [ $FOLD = 1 ] && { [ $t = tsp1 ] && [ "$F" != 0 ] && a=0; [ $t = tsp2 ] && [ "$F" != 1 ] && a=0; }
                    if [ $LIDF = 1 ]; then
                        # Armed eight passes (about 1 s) on, below: while a fold moves the picture to the
                        # other panel both are off for a moment, and the lid already
                        # names the one about to light. Three passes when the guest
                        # itself says it sleeps: no fold in progress to wait out.
                        if [ $a = 1 ]; then eval PA_$t=8; [ $D = 1 ] && eval PA_$t=3; else eval PA_$t=0; fi
                    elif [ $a = 1 ]; then
                        arm $t "$w"
                    fi
                fi
            done
            if [ $LIDF = 1 ]; then
                for t in tsp1 tsp2; do
                    eval p=\$PA_$t s=\$ON_$t
                    [ "${p:-0}" -gt 0 ] || continue
                    if [ $s = 1 ]; then eval PA_$t=0; continue; fi
                    [ $D = 1 ] && [ $p -gt 3 ] && p=3
                    p=$((p - 1)); eval PA_$t=$p
                    [ $p = 0 ] || continue
                    a=1; [ $t = tsp1 ] && [ "$F" != 0 ] && a=0; [ $t = tsp2 ] && [ "$F" != 1 ] && a=0
                    eval l=\$L_$t
                    if [ $l = 1 ]; then w="AOD (guest asleep, panel lit)"; else w="panel off"; fi
                    [ $a = 1 ] && arm_fresh $t "$w"
                done
            fi
            # vivo AOD brightness (F8U run 13, OriginOS: AOD "very weak, unseeable"). The
            # vivo AOD asks for doze brightness 0.0 (DreamManager override) and maps it
            # through vivo panel tables that a Galaxy panel does not have, so the lit AOD
            # panel sat at backlight 1 of 13510. While the guest sleeps with AOD, a lit
            # panel at 0 or 1 gets ONEOS_GUEST_VIVO_AOD percent of its range (default 3;
            # 0 leaves it). The guest sets its own level again when it wakes.
            if [ $VAOD -gt 0 ] && [ $D = 1 ]; then
                for t in $IDS; do
                    eval c=\$C_$t b=\$B_$t
                    d=Off; [ -r "$c" ] && read -r d < "$c"
                    [ "$d" != Off ] || continue
                    l=0; read -r l < "$b"
                    case "$l" in 0|1) ;; *) continue ;; esac
                    m=0; read -r m < "${b%/brightness}/max_brightness"
                    case "$m" in ""|*[!0-9]*) continue ;; esac
                    v=$((m * VAOD / 100)); [ $v -gt 1 ] || continue
                    echo $v > "$b" && log "$t: vivo AOD at backlight $l: set to $v ($VAOD% of $m)"
                done
            fi
            sleep 0.1
        done
    ' </dev/null >> /data/dt2w.log 2>&1 &
    echo "[Pivoted Root] Double tap to wake: kept from the end of the boot animation (/data/dt2w.log)"
else
    echo "[Pivoted Root] Double tap to wake: left to the guest (ONEOS_GUEST_DT2W=$DT2W, getevent $(command -v getevent >/dev/null 2>&1 && echo yes || echo no))"
fi
# Android 17's WallpaperDataParser calls next() once for <description>. Its
# indented serializer writes whitespace there, so next() returns TEXT and the
# saved component is skipped. WallpaperManagerService then has no static
# imagery and clears the record, so a live or video wallpaper comes back as
# ImageWallpaper after a boot. Remove only whitespace between XML elements,
# preserving every component, crop, colour, content value and wallpaper file.
# Pixel 17 guests (pull request #1 found it on the Fold8) and ColorOS 17 guests
# both ship this code; ColorOS logs ComponentInfo{/} then
# "Unable to regenerate crop; resetting" and clearWallpaperLocked.
if [ -f /data/system/users/0/wallpaper_info.xml ]; then
    WREL=system/users/0/wallpaper_info.xml
    WFILE="/data/$WREL"
    if [ ! -L /data/system ] && [ ! -L /data/system/users ] && [ ! -L /data/system/users/0 ] &&
            [ ! -L "$WFILE.oneos-normalized" ] && [ ! -L "$WFILE.oneos-spacing-backup" ] && [ -f "$WFILE" ] && [ ! -L "$WFILE" ] && [ "$(head -c 5 "$WFILE")" = '<?xml' ]; then
        if cp -p "$WFILE" "$WFILE.oneos-normalized" &&
                "$BB" sed ':a
N
$!ba
s/>[[:space:]]*</></g' "$WFILE" > "$WFILE.oneos-normalized" &&
                [ -s "$WFILE.oneos-normalized" ]; then
            if ! cmp -s "$WFILE" "$WFILE.oneos-normalized"; then
                if cp -p "$WFILE" "$WFILE.oneos-spacing-backup"; then
                    mv -f "$WFILE.oneos-normalized" "$WFILE"
                    echo "Wallpaper: normalized description spacing; saved selection retained"
                else
                    rm -f "$WFILE.oneos-normalized"
                    echo "WARNING: wallpaper backup failed; original retained"
                fi
            else
                rm -f "$WFILE.oneos-normalized"
            fi
        else
            rm -f "$WFILE.oneos-normalized"
            echo "WARNING: wallpaper normalization failed; original retained"
        fi
    fi
fi

# Properties are shared: One UI left boot_completed=1. Clear it before any
# guest framework or module boot-service waiter starts, on cold and soft boots.
# Otherwise a package-manager service can appear before AMS accepts broadcasts,
# and an early module APK verification crashes system_server.
if [ -f /data/oneos_root/enabled ]; then
    setprop sys.boot_completed 0
    setprop dev.bootcomplete 0
fi
# The guest's own compiled framework for the jars OneOS binds over its own
# (0.4.60). The image's boot image (/system/framework/arm64/boot*.oat) and
# system_server odex files are built for the image's framework.jar,
# services.jar...; framework_patched.jar, services_patched.jar and the others
# have other dex checksums, so ART refused them and the zygote ran "JIT
# Zygote", the framework JIT-compiled in every process (eleventh OriginOS run:
# "boot-framework.oat ... dex file checksum", seconds to open or close an app).
# The image's own odrefresh (its ART module) does what Android does after an
# update: it checks those artifacts and compiles what no longer matches into
# /data/misc/apexdata/com.android.art, the stage's own /data, kept between
# sessions, so later sessions find them current in seconds. ART takes them as
# odsign verified (One UI's odsign.verification.success, shared). A collector
# change (ro.dalvik.vm.enable_uffd_gc, guest_props.sh) drops them first: they
# are built for one. Not with -Xforcejitzygote. Bounded: the boot animation runs
# meanwhile, and the zygote starts after 300 s whatever odrefresh did.
# ONEOS_GUEST_ODREFRESH=1 on, 0 off. On for vivo OriginOS since 0.4.73 and for
# every guest since 0.4.76: OneOS's framework and services jars replace the
# image's in every guest, so none could use its image's boot image (ColorOS 17
# on the owner's Fold, 11-10: "boot-framework.oat ... dex file checksum ...
# does not match", "Attempting to fall back to imageless running").
ODR=/apex/com.android.art/bin/odrefresh
case "${ONEOS_GUEST_ODREFRESH:-}" in
    0|1) ;;
    *) ONEOS_GUEST_ODREFRESH=1 ;;
esac
if [ "$ONEOS_GUEST_ODREFRESH" = 1 ] && [ "$ONEOS_GUEST_JIT_ZYGOTE" != 1 ] && [ -x "$ODR" ]; then
    ADC=/data/misc/apexdata/com.android.art
    GCNOW="enable_uffd_gc=$(getprop ro.dalvik.vm.enable_uffd_gc)"
    # The collector the zygote will run (ART's SysPropSaysUffdGc on a uffd kernel):
    # CMC, without read barriers, only with ro.dalvik.vm.enable_uffd_gc true and the
    # force_disable flag off; CC otherwise. A boot image is usable only when its oat
    # header's "concurrent-copying" says the same. The twelfth CN run's zygote ran CC
    # and refused the guest's boot image ("read barrier state mismatch (oat file:
    # false, runtime: true)"): artifacts made under One UI's CMC had stayed, because
    # odrefresh --compile checks the jars, not the collector, and oneos_gc was
    # written whatever odrefresh did. The header is read now, before and after.
    if [ "$(getprop ro.dalvik.vm.enable_uffd_gc)" = true ] &&
       [ "$(getprop persist.device_config.runtime_native_boot.force_disable_uffd_gc)" != true ]; then
        CCWANT=false
    else
        CCWANT=true
    fi
    boot_cc() { # the boot image's concurrent-copying value, or nothing
        [ -f "$ADC/dalvik-cache/arm64/boot.oat" ] &&
            head -c 4194304 "$ADC/dalvik-cache/arm64/boot.oat" 2>/dev/null | tr '\0' '\n' | grep -A 1 -x concurrent-copying | sed -n 2p
    }
    mkdir -p "$ADC" /data/misc/odrefresh
    CCHAVE=$(boot_cc)
    if [ -d "$ADC/dalvik-cache" ] && { [ "$(cat "$ADC/oneos_gc" 2>/dev/null)" != "$GCNOW" ] || { [ -n "$CCHAVE" ] && [ "$CCHAVE" != "$CCWANT" ]; }; }; then
        rm -rf "$ADC/dalvik-cache" "$ADC/cache-info.xml" "$ADC/oneos_gc"
        echo "[Pivoted Root] odrefresh: artifacts made for another collector removed ($GCNOW now; their concurrent-copying ${CCHAVE:-unknown}, the zygote's $CCWANT)"
    fi
    # The jars the artifacts are made from (the boot class path's and the system
    # server's: size, time and path). Only for the case below where odrefresh
    # itself cannot say whether its artifacts are current.
    JARS=$(for j in $(printf '%s:%s:%s' "${BOOTCLASSPATH:-}" "${SYSTEMSERVERCLASSPATH:-}" "${STANDALONE_SYSTEMSERVER_JARS:-}" | tr ':' ' '); do
               ls -lnL "$j" 2>/dev/null | awk '{ print $5, $6, $7, $NF }'
           done | cksum 2>/dev/null | awk '{ print $1 "-" $2 }')
    t0=$(date +%s)
    timeout 300 "$ODR" --compile > /data/odrefresh.log 2>&1; rc=$?
    # odrefresh takes the image's own primary boot image as usable and compiles only
    # the mainline extension on top of it, which dex2oat cannot load (OneOS's
    # framework.jar), and aborts in no time (thirteenth run: 0 files). Without a boot
    # image of the guest's own yet: all of it, once.
    if [ ! -f "$ADC/dalvik-cache/arm64/boot.art" ]; then
        echo "--- no boot image of the guest's own after --compile (exit $rc): --force-compile" >> /data/odrefresh.log
        timeout 300 "$ODR" --force-compile >> /data/odrefresh.log 2>&1; rc=$?
    else
        # odrefresh died instead of answering (ColorOS 17 trial, 11-10: exit 134,
        # "assertion hasLastUpdateMillis() failed" on a module list entry;
        # guest_prepare.sh gives every entry one now): its artifacts were not
        # checked. Kept while the jars are the ones they were made from (ART
        # checks the checksums itself and would only fall back to compiling in
        # memory); other jars, after an update of the stage: all of it, once.
        case "$rc" in
            0|79|80|81|82|124) ;;
            *) if [ -n "$JARS" ] && [ "$(cat "$ADC/oneos_jars" 2>/dev/null)" != "$JARS" ]; then
                   echo "--- --compile ended with exit $rc and the jars are not the ones the artifacts were made from: --force-compile" >> /data/odrefresh.log
                   timeout 300 "$ODR" --force-compile >> /data/odrefresh.log 2>&1; rc=$?
               else
                   echo "--- --compile ended with exit $rc; the jars are the ones the artifacts were made from: kept" >> /data/odrefresh.log
               fi ;;
        esac
    fi
    case "$rc" in
        0|80) [ -n "$JARS" ] && [ -f "$ADC/dalvik-cache/arm64/boot.art" ] && echo "$JARS" > "$ADC/oneos_jars" ;;
    esac
    CCHAVE=$(boot_cc)
    # Once more only while the whole step stays near the 300 s the zygote waits for.
    if [ -n "$CCHAVE" ] && [ "$CCHAVE" != "$CCWANT" ] && [ $(( $(date +%s) - t0 )) -lt 120 ]; then
        echo "--- boot image concurrent-copying $CCHAVE, the zygote's $CCWANT: removed, --force-compile once more" >> /data/odrefresh.log
        rm -rf "$ADC/dalvik-cache" "$ADC/cache-info.xml"
        timeout 240 "$ODR" --force-compile >> /data/odrefresh.log 2>&1; rc=$?
        CCHAVE=$(boot_cc)
    fi
    if [ -n "$CCHAVE" ] && [ "$CCHAVE" != "$CCWANT" ]; then
        # Never leave the zygote a boot image it refuses (it then builds one in memory
        # in every start): without one it takes the image's, as before odrefresh.
        rm -rf "$ADC/dalvik-cache" "$ADC/cache-info.xml" "$ADC/oneos_gc"
        echo "[Pivoted Root] odrefresh: !!! its boot image is for the other collector (concurrent-copying $CCHAVE, the zygote's $CCWANT) after a second compile; removed"
    elif [ -n "$CCHAVE" ]; then
        echo "$GCNOW" > "$ADC/oneos_gc"
    fi
    # ART's odrefresh exit codes (exit_code.h): 0 okay, 79 compilation required,
    # 80 compiled, 81 compilation failed, 82 cleanup failed.
    case "$rc" in 0) w="current" ;; 79) w="compilation needed" ;; 80) w="compiled" ;; 81) w="compilation failed" ;; 82) w="cleanup failed" ;; 124) w="timed out" ;; *) w="exit $rc" ;; esac
    echo "[Pivoted Root] odrefresh: $w in $(( $(date +%s) - t0 )) s ($(ls "$ADC/dalvik-cache/arm64" 2>/dev/null | wc -l) files in $ADC/dalvik-cache/arm64, concurrent-copying ${CCHAVE:-none}, the zygote's $CCWANT; /data/odrefresh.log)"
else
    echo "[Pivoted Root] odrefresh: not run (ONEOS_GUEST_ODREFRESH=$ONEOS_GUEST_ODREFRESH, JIT zygote $ONEOS_GUEST_JIT_ZYGOTE)"
fi
# Bring apps (0.4.75): the owner chose user apps on One UI and `bring-collect`
# copied each one's APKs and its One UI data into /data/oneos_bring. Only the
# restore script is written here; the UI Activator (oneos_switch.sh) runs it
# inside the guest's mount namespace once the guest's own package service
# answers. (Builds 101 and 102 started it from here: 101 trusted
# sys.boot_completed, which One UI had already set, and 102 waited for a
# system_server in this script's mount namespace, which never comes because
# zygote unshares its own. Neither ever installed anything.)
if [ -d /data/oneos_bring ] && [ ! -L /data/oneos_bring ]; then
    cat > /data/oneos_bring_restore.sh <<'BRINGEOF'
#!/system/bin/sh
# OneOS Bring apps, the guest's half (0.4.75 build 103). guest_start.sh writes
# this file at every boot and the UI Activator (oneos_switch.sh) runs it inside
# the guest's mount namespace once the guest's UI is up, so the package service
# that answers is the guest's own. For every app folder `bring-collect` left in
# /data/oneos_bring it installs the APKs and lays the copied One UI data over
# the fresh install with the guest's uid and label, so the app starts signed in.
#
# One way: nothing is written back to One UI. Safe to interrupt (the return to
# One UI kills it): the data is copied beside its place and swapped in, an app
# is marked applied only when all of it is there, and an unmarked app is done
# again at the next start. Everything it does and every answer of the package
# manager is in /data/oneos_bring.log, which the OneOS app shows on One UI.
BRING=/data/oneos_bring
LOG=/data/oneos_bring.log
GUEST_MARK=/data/oneos_genv.sh
HOST_MARK=/data/local/tmp/oneos/.oneos_stage
STOP=/data/oneos_rec_stop
GBB=/data/oneos_bin/busybox
NOTICE=1
CE=/data/user/0
DE=/data/user_de/0
PATH=/system/bin:$PATH
export PATH
umask 077

# Only ever in the guest: this replaces app data under /data/user/0, which on
# One UI would be One UI's own. The guest has its environment file and never
# sees the stage at its One UI path.
[ -f "$GUEST_MARK" ] || exit 0
[ ! -e "$HOST_MARK" ] || exit 0
[ -d "$BRING" ] && [ ! -L "$BRING" ] || exit 0

log() { echo "[$(date '+%m-%d %H:%M:%S')] $*" >> "$LOG"; }
is_dec() {
    case "$1" in ''|*[!0-9]*) return 1 ;; esac
    [ ${#1} -le 18 ]
}
is_package() {
    case "$1" in ''|.*|*.|*[!A-Za-z0-9._]*|*..*) return 1 ;; esac
    case "$1" in *.*) return 0 ;; *) return 1 ;; esac
}
first_line() {
    [ -f "$1" ] && [ ! -L "$1" ] || return 0
    head -n 1 "$1" 2>/dev/null
}
# The copy's stamp (when bring-collect finished it). 0 for a copy made before
# stamps (build 102); nothing while a copy is unfinished.
stamp_of() {
    s=$(first_line "$1/stamp")
    if is_dec "$s"; then echo "$s"; return; fi
    [ -e "$1/since" ] || [ -e "$1/stamp" ] || echo 0
}
stopping() { [ -e "$STOP" ]; }
short() { echo "$1" | tr '\n' ' ' | sed 's/[^A-Za-z0-9 ._:,()=\/-]/ /g' | cut -c1-240; }
notice() {
    [ "$NOTICE" = 1 ] || return 0
    timeout 10 cmd notification post -S bigtext -t "Apps from One UI" oneos_bring "$1" >/dev/null 2>&1
}
# The package manager, as root or (sys) as the system uid, which it never
# takes for an install over adb.
gpm() {
    gw=$1; gt=$2; shift 2
    if [ "$gw" = sys ]; then timeout "$gt" "$GBB" setuidgid 1000:1000 pm "$@"
    else timeout "$gt" pm "$@"; fi
}
pm_up() { gpm root 10 path android >/dev/null 2>&1; }
wait_pm() {
    i=0
    while ! pm_up; do
        stopping && return 1
        i=$((i + 1)); [ $i -lt 60 ] || return 1
        sleep 3
    done
}
empty() {
    for x in "$1"/* "$1"/.[!.]* "$1"/..?*; do
        [ -e "$x" ] || [ -L "$x" ] || continue
        rm -rf "$x"
    done
}

# "Verify apps over USB" would send every app to a scan first (and can ask on
# screen): off while this runs, and back to what it was afterwards (also when
# the last run was cut short: its saved value is still in the file).
VSAVE="$BRING/.verifier"
verifier_off() {
    if [ ! -f "$VSAVE" ]; then
        v=$(timeout 10 settings get global verifier_verify_adb_installs 2>/dev/null) || return 0
        echo "$v" > "$VSAVE"
    fi
    timeout 10 settings put global verifier_verify_adb_installs 0 >/dev/null 2>&1
}
verifier_back() {
    [ -f "$VSAVE" ] || return 0
    v=$(first_line "$VSAVE")
    case "$v" in
        0|1) timeout 10 settings put global verifier_verify_adb_installs "$v" >/dev/null 2>&1 || return 0 ;;
        *) timeout 10 settings delete global verifier_verify_adb_installs >/dev/null 2>&1 || return 0 ;;
    esac
    rm -f "$VSAVE"
}

# One install attempt of $d/apk as <root|sys> with the given options. 0 when
# the package manager said Success; else 1 and $why holds its own words.
install_try() {
    who=$1; shift
    out=$(gpm "$who" 60 install-create "$@" 2>&1)
    sid=$(echo "$out" | sed -n 's/.*\[\([0-9][0-9]*\)\].*/\1/p' | head -n 1)
    if [ -z "$sid" ]; then why="no install session: $(short "$out")"; return 1; fi
    for a in "$d/apk"/*.apk; do
        [ -f "$a" ] && [ ! -L "$a" ] || continue
        name=${a##*/}
        size=$(stat -c %s "$a" 2>/dev/null)
        w=""
        # By path as root (the package service opens the file itself), else streamed to it.
        if [ "$who" = root ]; then w=$(gpm root 900 install-write -S "$size" "$sid" "$name" "$a" 2>&1); fi
        case "$w" in *Success*) how=path; continue ;; esac
        w=$(gpm "$who" 900 install-write -S "$size" "$sid" "$name" - < "$a" 2>&1)
        case "$w" in *Success*) how=stdin; continue ;; esac
        w=$(cat "$a" | gpm "$who" 900 install-write -S "$size" "$sid" "$name" - 2>&1)
        case "$w" in *Success*) how=pipe; continue ;; esac
        gpm "$who" 20 install-abandon "$sid" >/dev/null 2>&1
        why="the installer did not take $name: $(short "$w")"
        return 1
    done
    out=$(gpm "$who" 300 install-commit "$sid" 2>&1)
    case "$out" in *Success*) return 0 ;; esac
    gpm "$who" 20 install-abandon "$sid" >/dev/null 2>&1
    why=$(short "$out")
    [ -n "$why" ] || why="the installer gave no answer in 5 minutes"
    return 1
}

# What no second try changes (the guest has another build of the app, or an
# APK this system cannot run): said once, tried again only with a new copy.
final_reason() {
    case "$1" in
        *UPDATE_INCOMPATIBLE*|*INVALID_APK*|*NO_MATCHING_ABIS*|*OLDER_SDK*|*PARSE_FAILED*|*NO_CERTIFICATES*|*MISSING_SPLIT*) return 0 ;;
    esac
    return 1
}

# Installs $pkg from $d/apk. 0: installed, or the guest keeps its own newer
# version ($kept=1); 1: not installed and $why says why.
install_app() {
    kept=0
    n=0
    for a in "$d/apk"/*.apk; do [ -f "$a" ] && [ ! -L "$a" ] && n=$((n + 1)); done
    [ $n -gt 0 ] || { why="the copy has no APK"; return 1; }
    vend=""
    gpm root 20 path com.android.vending >/dev/null 2>&1 && vend="-i com.android.vending"
    round=0
    while :; do
        for attempt in "root -r -g $vend --user 0" "root -r --user 0" "sys -r -g $vend --user 0" "sys -r --user 0"; do
            stopping && { why="the system was closing"; return 1; }
            case "$attempt" in sys*) [ -x "$GBB" ] || continue ;; esac
            if install_try $attempt; then
                log "$pkg: installed ($n APK, as ${attempt%% *}, by $how)"
                return 0
            fi
            log "$pkg: install as ${attempt%% *} did not work: $why"
            case "$why" in
                *VERSION_DOWNGRADE*)
                    if gpm root 20 path "$pkg" >/dev/null 2>&1; then kept=1; return 0; fi ;;
            esac
            final_reason "$why" && return 1
            case "$why" in *INSUFFICIENT_STORAGE*) return 1 ;; esac
        done
        round=$((round + 1)); [ $round -lt 2 ] || return 1
        sleep 10
        wait_pm || { why="the package manager stopped answering"; return 1; }
    done
}

# Lays the copy <src> over the app's data folder <dst>: copied beside its
# place inside <dst> (same quota project, so the swap is a rename), given the
# app's uid and the folder's own label, then swapped in. 0 done; 1 and $why.
restore_dir() {
    src=$1; dst=$2
    [ -d "$src" ] && [ ! -L "$src" ] || return 0
    if [ -L "$dst" ]; then why="$dst is a link"; return 1; fi
    if [ ! -d "$dst" ]; then
        mkdir -p "$dst" && chown "$uid:$uid" "$dst" && chmod 700 "$dst" || { why="could not make $dst"; return 1; }
        other=$(stat -c %C "$CE/$pkg" 2>/dev/null)
        case "$other" in u:object_r:*) chcon "$other" "$dst" 2>/dev/null ;; *) restorecon -D "$dst" 2>/dev/null ;; esac
    fi
    ctx=$(stat -c %C "$dst" 2>/dev/null)
    tmp="$dst/.oneos_bring_tmp"
    rm -rf "$tmp"
    need=$(du -sk "$src" 2>/dev/null | cut -f1)
    free=$(df -k "$dst" 2>/dev/null | awk 'NR == 2 { print $4 }')
    if is_dec "$need" && is_dec "$free" && [ "$free" -lt $((need + 262144)) ]; then
        why="not enough free space for its data ($((need / 1024)) MB)"; return 1
    fi
    mkdir "$tmp" || { why="could not write in $dst"; return 1; }
    cp -a "$src/." "$tmp/" 2>>"$LOG" || log "$pkg: some of its ${src##*/} data did not copy"
    chown -hR "$uid:$uid" "$tmp" 2>/dev/null
    case "$ctx" in
        u:object_r:*) chcon -hR "$ctx" "$tmp" 2>>"$LOG" || log "$pkg: could not label its ${src##*/} data ($ctx)" ;;
        *) log "$pkg: no label read from $dst, restorecon used"; restorecon -RD "$tmp" 2>>"$LOG" ;;
    esac
    chmod 700 "$tmp"
    stopping && { rm -rf "$tmp"; why="the system was closing"; return 1; }
    timeout 20 am force-stop "$pkg" >/dev/null 2>&1
    # What the fresh install (or the last bring) left goes; the cache folders
    # stay, emptied. Then the copy moves into place.
    for e in "$dst"/* "$dst"/.[!.]* "$dst"/..?*; do
        [ -e "$e" ] || [ -L "$e" ] || continue
        case "${e##*/}" in
            .oneos_bring_tmp) continue ;;
            cache|code_cache) if [ -d "$e" ] && [ ! -L "$e" ]; then empty "$e"; continue; fi ;;
        esac
        rm -rf "$e"
    done
    for e in "$tmp"/* "$tmp"/.[!.]* "$tmp"/..?*; do
        [ -e "$e" ] || [ -L "$e" ] || continue
        to="$dst/${e##*/}"
        if [ -e "$to" ] || [ -L "$to" ]; then rm -rf "$to"; fi
        mv "$e" "$to" || { why="could not move ${e##*/} into place"; return 1; }
    done
    rmdir "$tmp" 2>/dev/null || rm -rf "$tmp"
    return 0
}

restore_one() {
    pkg=$1; stamp=$2
    d="$BRING/$pkg"
    why=""
    log "$pkg: starting (copy $stamp)"
    if ! install_app; then
        echo "$stamp $why" > "$d/failed"
        log "$pkg: NOT brought: $why"
        return 1
    fi
    uid=$(gpm root 20 list packages -U "$pkg" 2>/dev/null | sed -n "s/^package:$pkg uid:\([0-9][0-9]*\).*/\1/p" | head -n 1)
    is_dec "$uid" || uid=$(stat -c %u "$CE/$pkg" 2>/dev/null)
    if ! is_dec "$uid" || [ "$uid" -lt 10000 ]; then
        why="installed, but the system gave no app uid for it"
        echo "$stamp $why" > "$d/failed"
        log "$pkg: NOT brought: $why"
        return 1
    fi
    if ! { restore_dir "$d/ce" "$CE/$pkg" && restore_dir "$d/de" "$DE/$pkg"; }; then
        echo "$stamp $why" > "$d/failed"
        log "$pkg: NOT brought: $why"
        return 1
    fi
    echo "$stamp" > "$d/applied.new" && mv -f "$d/applied.new" "$d/applied" || { log "$pkg: could not mark it applied"; return 1; }
    rm -f "$d/failed"
    rm -rf "$d/apk" "$d/ce" "$d/de"
    if [ $kept = 1 ]; then log "$pkg: ready (data restored; the newer version already here was kept; uid $uid, label $ctx)"
    else log "$pkg: ready (installed and data restored; uid $uid, label $ctx)"; fi
    return 0
}

# One run at a time (a soft reboot of the guest starts the Activator's pass again).
# "early" (build 106): the Activator also starts this as soon as the guest's
# system_server is there, so the apps are in the launcher when it comes up and
# not 10-15 s later (owner, 11-10). The early run waits below; the Activator's
# later start finds it alive and only leaves it the go file.
MODE=${1:-}
GO="$BRING/.go"
if [ -f "$BRING/.pid" ]; then
    old=$(first_line "$BRING/.pid")
    if is_dec "$old" && [ "$old" != "$$" ] && grep -q oneos_bring_restore "/proc/$old/cmdline" 2>/dev/null; then
        [ "$MODE" = early ] || : > "$GO"
        exit 0
    fi
fi
echo $$ > "$BRING/.pid"
[ "$MODE" = early ] && rm -f "$GO"

# What waits: a finished copy that is not applied yet.
pending=""; count=0
for d in "$BRING"/*; do
    [ -d "$d" ] && [ ! -L "$d" ] || continue
    pkg=${d##*/}
    is_package "$pkg" || continue
    stamp=$(stamp_of "$d")
    [ -n "$stamp" ] || continue
    if [ "$(first_line "$d/applied")" = "$stamp" ]; then
        # Applied; what a cut-short clean-up left of the copy goes now.
        rm -rf "$d/apk" "$d/ce" "$d/de"
        continue
    fi
    [ -d "$d/apk" ] || continue
    f=$(first_line "$d/failed")
    case "$f" in "$stamp "*) final_reason "$f" && continue ;; esac
    pending="$pending $pkg"; count=$((count + 1))
done
if [ $count = 0 ]; then
    [ -f "$VSAVE" ] && pm_up && verifier_back
    rm -f "$BRING/.pid"
    exit 0
fi

if [ -f "$LOG" ] && [ "$(stat -c %s "$LOG" 2>/dev/null || echo 0)" -gt 262144 ]; then
    tail -n 200 "$LOG" > "$LOG.new" && mv -f "$LOG.new" "$LOG"
fi
log "start: $count app(s) to bring:$pending${MODE:+ ($MODE)}"
if [ "$MODE" = early ]; then
    # Until the guest's user 0 is unlocked (its app data is there) and its
    # package service answers, or the Activator's later start says go (what
    # build 105 waited for). Neither in 10 minutes: left to the later start.
    i=0; went=""
    while [ $i -lt 600 ]; do
        if stopping; then rm -f "$BRING/.pid"; exit 0; fi
        if [ -e "$GO" ]; then went="the Activator's start"; break; fi
        case "$(timeout 10 am get-started-user-state 0 2>/dev/null)" in
            *RUNNING_UNLOCKED*) if pm_up; then went="user 0 unlocked"; break; fi ;;
        esac
        i=$((i + 1)); sleep 1
    done
    rm -f "$GO"
    if [ -z "$went" ]; then
        log "early: the guest's user was not unlocked in 10 minutes; they come with the Activator's start"
        rm -f "$BRING/.pid"
        exit 0
    fi
    log "early: $went after $i s"
fi
if ! wait_pm; then
    log "the package manager did not answer; they come at the next start"
    rm -f "$BRING/.pid"
    exit 0
fi
notice "Bringing $count app(s) over from One UI. Keep this system open until they are ready."
verifier_off
ok=0; bad=0
for pkg in $pending; do
    if stopping; then log "the system is closing; the rest comes at the next start"; break; fi
    wait_pm || { log "the package manager stopped answering; the rest comes at the next start"; break; }
    stamp=$(stamp_of "$BRING/$pkg")
    [ -n "$stamp" ] || continue
    if restore_one "$pkg" "$stamp"; then ok=$((ok + 1)); else bad=$((bad + 1)); fi
done
verifier_back
log "done: $ok ready, $bad not brought"
if [ $bad = 0 ] && [ $ok -gt 0 ]; then notice "$ok app(s) from One UI are ready, with their data."
elif [ $ok -gt 0 ]; then notice "$ok app(s) from One UI are ready; $bad could not be brought (OneOS on One UI says why)."
elif [ $bad -gt 0 ]; then notice "$bad app(s) could not be brought from One UI (OneOS on One UI says why)."
fi
rm -f "$BRING/.pid"
exit 0
BRINGEOF
    chmod 700 /data/oneos_bring_restore.sh
    echo "[Pivoted Root] Bring apps: restore script written; the UI Activator runs it once the guest is up (/data/oneos_bring.log)"
else
    rm -f /data/oneos_bring_restore.sh
fi
# Samsung's One UI leaves lockscreen.disabled=1 behind even with a PIN; the
# guest's copy would make ColorOS skip its keyguard. Clear it on the guest's
# copy only, after the guest's own boot_completed (the shared flag is cleared
# above). The marker is staged with the lock state.
if [ -f /data/system/oneos_lockstate/enabled ]; then
    (
        n=0
        while [ "$(getprop sys.boot_completed)" != 1 ]; do
            n=$((n+1)); [ "$n" -lt 120 ] || exit 0; sleep 1
        done
        n=0
        while [ "$(/system/bin/locksettings get-disabled --user 0 2>/dev/null)" != false ]; do
            /system/bin/locksettings set-disabled false --user 0 >/dev/null 2>&1
            n=$((n+1)); [ "$n" -lt 10 ] || break; sleep 1
        done
        if [ "$(/system/bin/locksettings get-disabled --user 0 2>/dev/null)" = false ]; then
            echo "keyguard enabled"
        else
            echo "keyguard still disabled"
        fi
    ) > /data/system/oneos_lockstate/late.log 2>&1 &
fi

# OneOS: the fingerprint-wave SystemUI. scripts/install-systemui-wave.sh
# builds the patched APK once per SystemUI build and leaves it in the guest's
# /data/local/tmp; this bind must run before zygote starts, because zygote and
# SystemUI unshare their own mount namespaces and would not see a later bind.
# The image's oat/arm64 is for the stock dex checksum, so hide it as well.
# Without the APK the stock SystemUI runs and nothing here changes the
# keyguard.
WAVE_APK=/data/local/tmp/SystemUI_wave.apk
WAVE_SIZE=/data/local/tmp/SystemUI_wave.stock.size
WAVE_SHA=/data/local/tmp/SystemUI_wave.stock.sha256
WAVE_OAT=/data/local/tmp/empty_oat
# Only ColorOS's SystemUI is the build this APK patches. A HyperOS, Pixel or
# Infinity-X guest has its own SystemUI, and binding ColorOS's over it would
# crash SystemUI at boot. The stock hash is the second fence: a ColorOS OTA
# that changed SystemUI also skips the APK until install-systemui-wave.sh is
# run again.
if [ ! -e /system/framework/oplus-services.jar ]; then
    echo "[Pivoted Root] SystemUI: guest is not ColorOS; stock SystemUI"
    WAVE_APK=
elif [ -f "$WAVE_APK" ] && [ -f "$WAVE_SIZE" ] && [ -f "$WAVE_SHA" ]; then
    wave_want=$(cat "$WAVE_SIZE" 2>/dev/null)
    wave_sha=$(cat "$WAVE_SHA" 2>/dev/null)
    wave_got=$($BB stat -c %s /system/system_ext/priv-app/SystemUI/SystemUI.apk 2>/dev/null)
    wave_hash=$($BB sha256sum /system/system_ext/priv-app/SystemUI/SystemUI.apk 2>/dev/null | awk '{print $1}')
    if [ "$wave_want" != "$wave_got" ] || [ "$wave_sha" != "$wave_hash" ]; then
        echo "[Pivoted Root] SystemUI: wave APK is for another SystemUI build; stock SystemUI"
        WAVE_APK=
    fi
else
    if [ -f "$WAVE_APK" ]; then
        echo "[Pivoted Root] SystemUI: wave APK has no stock hash; stock SystemUI"
    fi
    WAVE_APK=
fi
if [ -f "$WAVE_APK" ]; then
    mkdir -p "$WAVE_OAT"
    chmod 644 "$WAVE_APK" 2>/dev/null || true
    $BB chcon u:object_r:system_file:s0 "$WAVE_APK" 2>/dev/null || true
    if [ -d /system/system_ext/priv-app/SystemUI/oat/arm64 ]; then
        $BB mount -o bind "$WAVE_OAT" /system/system_ext/priv-app/SystemUI/oat/arm64 2>/dev/null || true
    fi
    if $BB mount -o bind "$WAVE_APK" /system/system_ext/priv-app/SystemUI/SystemUI.apk 2>/dev/null; then
        echo "[Pivoted Root] SystemUI: fingerprint wave APK bound"
        # SurfaceFlinger thrashes 10 Hz <-> 120 Hz during the wave without a
        # floor; the setting lives in the guest's data and resets on boot.
        (
            n=0
            while [ "$(getprop sys.boot_completed)" != 1 ] && [ "$n" -lt 120 ]; do
                n=$((n + 1)); sleep 1
            done
            settings put system min_refresh_rate 120 >/dev/null 2>&1 || true
            n=0
            while [ "$(settings get system min_refresh_rate 2>/dev/null)" != 120 ] && [ "$n" -lt 30 ]; do
                n=$((n + 1)); sleep 1
                settings put system min_refresh_rate 120 >/dev/null 2>&1 || true
            done
        ) >/dev/null 2>&1 &
    else
        echo "[Pivoted Root] SystemUI: fingerprint wave bind failed; stock SystemUI"
    fi
fi

echo "[Pivoted Root] Launching guest Zygote & SystemServer via zygote_exec..."
if [ -f /data/oneos_root/enabled ]; then
    /system/bin/sh /data/oneos_runtime.sh pre || exit 3
    /system/bin/sh /data/oneos_runtime.sh late > /data/adb/oneos/run/late.log 2>&1 &
    exec /data/adb/oneos/bin/su --launch
fi
exec /data/zygote_exec
