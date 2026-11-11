#!/system/bin/sh
STAGE="/data/local/tmp/oneos"
ROOTFS="$STAGE/rootfs"
# OneOS: init's mount namespace only (oneos_switch.sh's preflight makes
# sure of it). The bridges below are for One UI's installd and artd, which run
# there; made in any other namespace they would not reach them (run 25).
if [ -z "$(readlink /proc/$$/ns/mnt 2>/dev/null)" ] || [ "$(readlink /proc/$$/ns/mnt 2>/dev/null)" != "$(readlink /proc/1/ns/mnt 2>/dev/null)" ]; then
    echo "ERROR: not in init's mount namespace ($(readlink /proc/$$/ns/mnt 2>/dev/null), init $(readlink /proc/1/ns/mnt 2>/dev/null)); not starting the guest"
    exit 4
fi
# The root manager's own busybox, never a search of /data.
BB=""
for c in /data/adb/ksu/bin/busybox /data/adb/ap/bin/busybox /data/adb/magisk/busybox; do
    [ -x "$c" ] && { BB=$c; break; }
done
[ -n "$BB" ] || [ "${ONEOS_APP:-0}" = 1 ] || BB=$(command -v busybox 2>/dev/null)
[ -n "$BB" ] && [ -x "$BB" ] || { echo "ERROR: no busybox at the root manager's paths; not starting the guest"; exit 4; }
# OneOS: nothing may be mounted at or under the staged /data while it is
# rebuilt. The rm -rf, chown -R and chcon -R below would go through such a
# mount into the phone's real data.
if awk -v p="$STAGE/data" '$5 == p || index($5, p "/") == 1' /proc/self/mountinfo | grep -q .; then
    echo "ERROR: something is mounted under $STAGE/data (an earlier session?); return to One UI first"
    awk -v p="$STAGE/data" '$5 == p || index($5, p "/") == 1 {print "  " $5}' /proc/self/mountinfo
    exit 4
fi
# One UI's own partitions as mounted now (mount points), compared after the
# setup below: nothing of the guest may land on them. In an image with
# system/product as an absolute link to /product, binds made through the
# rootfs's system/product in this (host) namespace went onto One UI's own
# /product (Z Fold8 Ultra, 2026-10-25): its product_seapp_contexts and
# split-permissions-google.xml were the guest's for the session, and the
# in-place return found them and rebooted.
host_part_mounts() {
    awk '$5 ~ /^\/(system|system_ext|product|vendor|vendor_dlkm|odm|odm_dlkm|oem|prism|optics|my_[a-z_]+)(\/|$)/ {print $5}' /proc/self/mountinfo | sort
}
host_part_mounts > "$STAGE/host_part_mounts.before"
# Nor may a host /data tree still be bridged from a session that never
# returned: refuse, and let the return (reboot) clean up.
[ -r "$STAGE/bridges.sh" ] || { echo "ERROR: $STAGE/bridges.sh missing"; exit 4; }
. "$STAGE/bridges.sh" || { echo "ERROR: $STAGE/bridges.sh unreadable"; exit 4; }
for need in app:app user:user user_de:user_de data:user/0 media:media; do
    case " $BRIDGES " in *" $need "*) ;; *) echo "ERROR: bridges.sh lacks $need; not starting the guest"; exit 4 ;; esac
done
for pair in $BRIDGES; do
    h=${pair%%:*}
    if awk -v p="/data/$h" '$5 == p' /proc/self/mountinfo | grep -q .; then
        echo "ERROR: /data/$h is still bridged from an earlier session; return to One UI (reboot) first"
        exit 4
    fi
done
# OneOS: no symlink may sit on any staged /data path the host root below writes
# through, binds or relabels. A guest with root (a ColorOS root daemon, or an
# app that got root) could, between sessions, point e.g. $STAGE/data/misc at
# /data/misc, or $STAGE/data/oneos_bin/busybox at a host file; the rm/cp, the
# chown/chcon and the bridge binds would then land in One UI's real /data. A
# symlinked PARENT escapes too, so every component is checked. Refuse (exit 3)
# before the first change.
[ -L "$STAGE/data" ] && { echo "ERROR: $STAGE/data is a symlink; not starting the guest"; exit 3; }
no_symlink() { # <relative path under $STAGE/data>: refuse if any component is a link
    _p="$STAGE/data"; _oifs=$IFS; IFS=/
    for _c in $1; do
        _p="$_p/$_c"
        if [ -L "$_p" ]; then
            IFS=$_oifs
            echo "ERROR: $_p is a symlink (a guest may have planted it to reach host /data); not starting the guest"
            exit 3
        fi
    done
    IFS=$_oifs
}
for pair in $BRIDGES; do no_symlink "${pair#*:}"; done
for s in data misc misc/adb misc/profiles misc/user misc/bluedroid misc/bluetooth \
         misc_ce/0 misc_de/0 system system/devicestate system/package_cache \
         system/watchdog_timestamps system_de system_ce user/0 user_de/0 \
         oneos_bin oneos_bin/busybox zygote_exec oplus oplus/multimedia \
         preapps-lib media/0 anr app local/tmp resource-cache oneos_fold8 oneos_pixel_hinge oneos_hinge; do
    no_symlink "$s"
done
# The framework jars must be the ones built with the storage, installd and
# power guards (scripts/make-overlays.sh records their hashes in guards.txt).
if [ ! -f "$STAGE/guards.txt" ]; then
    echo "ERROR: $STAGE/guards.txt missing: overlays not built with the guards; not starting the guest"
    exit 3
fi
# oplus-services_patched.jar too when guards.txt lists it; an image with
# oplus-services.jar is refused below unless that one is bound. So are
# vold_patched and service.incremental_patched.so (the guest vold as "gvld"),
# HyperOS's miui-services_patched.jar and apprecovery.proinstaller_patched.jar,
# and the Pixel camera client libraries.
for need in services_patched.jar $(awk '$2 == "oplus-services_patched.jar" || $2 == "vold_patched" || $2 == "service.incremental_patched.so" ||
                                        $2 == "miui-services_patched.jar" || $2 == "apprecovery.proinstaller_patched.jar" ||
                                        $2 == "framework_patched.jar" || $2 == "miui-wifi-service_patched.jar" || $2 == "miui-telephony-common_patched.jar" ||
                                        $2 == "libcamera_client_patched.so" || $2 == "libcameracompatbilityinfo_patched.so" ||
                                        $2 == "libsurfaceflinger_patched.so" || $2 == "telephony-common_patched.jar" ||
                                        $2 == "vivo-services_patched.jar" || $2 == "vivo-telephony-common-platform-ex_patched.jar" { print $2 }' "$STAGE/guards.txt"); do
    sum=$(awk -v n="$need" '$2 == n {print $1}' "$STAGE/guards.txt")
    if [ -z "$sum" ] || [ "$(sha256sum "$STAGE/$need" 2>/dev/null | cut -d' ' -f1)" != "$sum" ]; then
        echo "ERROR: $STAGE/$need missing or not the guarded build in guards.txt; not starting the guest"
        exit 3
    fi
done
echo "Guarded overlays verified: $(grep -v '^#' "$STAGE/guards.txt" | awk '{print $2}' | tr '\n' ' ')"
# Google Play services in a Pixel guest (docs/pixel-guest.md, "Google services"):
# GmsCore from the image's own gmssystem APEX payload (make-overlays.sh stages
# gmssystem_payload.img), presented in section 8 and after the hidden folders
# below. Infinity-X (0.4.27) keeps Play services the same way, next to OPPO's
# jars; ColorOS sets never stage the payload (guest_google.sh is theirs). ONEOS_GUEST_GMS=1 (default) presents it when the payload is staged,
# 0 never. Refused here, before the first change:
# - with ONEOS_GUEST_HIDE_GMS=1, which hides Google Services Framework, the Play
#   Store and the PrebuiltGmsCore folder GmsCore is presented in;
# - without the guards guards.txt records for a Google services guest: the
#   phone's gatekeeper (screen lock), FRP partition (pdb) and apexd stay One
#   UI's, and guest apps get app ids from 15000 (no keystore namespace shared
#   with One UI's apps);
# - on a stage whose packages.list has app uids 10000-14999: made before the app
#   id guard, its apps keep the uids One UI's apps have. Such a stage needs a
#   fresh guest data dir (deploy-phone.sh --fresh).
GMS_WANT=0
case "${ONEOS_GUEST_GMS:-1}" in
    0) ;;
    1) [ -f "$STAGE/gmssystem_payload.img" ] && GMS_WANT=1 ;;
    *) echo "ERROR: ONEOS_GUEST_GMS=$ONEOS_GUEST_GMS (0 or 1); not starting the guest"; exit 3 ;;
esac
if [ "$GMS_WANT" = 1 ]; then
    if [ "${ONEOS_GUEST_HIDE_GMS:-0}" = 1 ]; then
        echo "ERROR: ONEOS_GUEST_GMS is on (the default) with gmssystem_payload.img staged, and ONEOS_GUEST_HIDE_GMS=1 hides Google services; set ONEOS_GUEST_GMS=0 or drop ONEOS_GUEST_HIDE_GMS. Not starting the guest"
        exit 3
    fi
    for t in gatekeeper pdb apexd appid15000; do
        grep '^#' "$STAGE/guards.txt" | grep -qw "$t" && continue
        echo "ERROR: guards.txt does not list the $t guard: services_patched.jar was built without the guards Google services need (scripts/make-overlays.sh). ONEOS_GUEST_GMS=0 starts without them. Not starting the guest"
        exit 3
    done
    GMS_LOW=$(awk -v ksu="me.weishu.kernelsu com.rifsxd.ksunext com.sukisu.ultra app.kitsusu.manager" 'BEGIN { split(ksu, a, " "); for (i in a) m[a[i]] = 1 } $2 ~ /^[0-9]+$/ && $2 >= 10000 && $2 <= 14999 && !($1 in m) { n++; if (n <= 3) l = l " " $1 "=" $2 } END { if (n) print n " (" substr(l, 2) ")" }' "$STAGE/data/system/packages.list" 2>/dev/null)
    if [ -n "$GMS_LOW" ]; then
        echo "ERROR: the staged guest has $GMS_LOW app uids in 10000-14999 (a stage from before the app id guard: its apps share keystore namespaces with One UI's). Google services need a fresh guest data dir (deploy-phone.sh --fresh); ONEOS_GUEST_GMS=0 starts this stage without them. Not starting the guest"
        exit 3
    fi
    echo "Google services: GmsCore from gmssystem_payload.img will be presented (ONEOS_GUEST_GMS=0 starts without it)"
elif [ "${ONEOS_GUEST_GMS:-1}" = 0 ]; then
    echo "Google services: not presented (ONEOS_GUEST_GMS=0)"
else
    echo "Google services: not presented (no gmssystem_payload.img staged)"
fi
# Set again only once GmsCore is bound (below); oneos_switch.sh's UI
# activator reads it (Pixel's setup wizard).
rm -f "$STAGE/data/oneos_gms_present"
# Stale state in the staged /data. The package manager's parse cache survives
# sessions and its freshness check is defeated by the image's 2009 mtimes, so
# /system paths bind-swapped here (NetworkStack, CaptivePortalLogin) kept their
# old parse ("Could not resolve the networking module" in run 25). ColorOS's
# watchdog counts kills across sessions in watchdog_timestamps.
rm -rf "$STAGE/data/system/package_cache" "$STAGE/data/system/watchdog_timestamps" 2>/dev/null
# How's it going? (0.4.30): the guest OneOS app's checklist is one session's;
# a new session starts without the last one's answers.
rm -f "$STAGE/data/user/0/com.fahadali.oneos.guest/files/oneos_checklist.json" 2>/dev/null

echo "=== 1. $(date +%T) Ensuring Watchdog Feeder is Active ==="
# One UI's system_server opens /dev/watchdog (Samsung's softdog) unless
# persist.vendor.softdog is off, sets 100 s and kicks it (services.jar
# WatchdogSoftdog); stopped at [4b/6], it leaves the softdog running. The
# Galaxy Z Flip7 (d5e743e6) and S26+ (80387c66), both Exynos, panicked
# ("Software Watchdog Timer expired 100s") about 100 s after the guest's
# system_server started. Each write is "V": a ping, and the magic close, so the
# softdog stops on every close where the driver allows it, and stays stopped
# if this loop ever ends. Every change between written and refused goes to
# watchdog_feeder.log with the device's holders. A feeder of an older build
# (echo -n 1) is replaced.
# The S26+ (4cad07e6, 0.4.19) panicked the same way with that feeder running:
# on this phone /dev/watchdog is the hardware watchdog, held and fed by init's
# watchdogd the whole time (the feeder's writes were refused, EBUSY), and
# Samsung's "Software Watchdog Timer" is a second node, /dev/softdog, which
# One UI's system_server feeds and the community "Watchdog Feeder" module for
# OneLineage writes "1" to every 5 s (it waits for vendor.hotboot.rom=1, which
# OneOS never sets). The panic came 100 s after the guest's system_server
# died. 0.4.20 wrote "1" to /dev/softdog, but neither the S26+ nor the Z Flip7
# has that node (756047eb, aaeea148: both panicked again); oneos_switch.sh now
# turns the softdog off through Samsung's init (persist.vendor.softdog=off).
# The feeder kicks only watchdogs the kernel lists as active software ones
# (/sys/class/watchdog: identity "Software Watchdog"; never a hardware one it
# might start), and logs every watchdog node, its state and time left (every
# change, at most every 10 s), so the next Exynos session shows which one runs.
# The Galaxy A16 4G (MediaTek, 0.4.55 64e7f7da) panicked about 100 s into every
# session with this feeder writing /dev/watchdog: there Samsung's softdog is
# /dev/softdog (a link to /dev/watchdog1), and its sysfs has no identity or
# state to find it by. A /dev/softdog that exists is kicked too.
pkill -f 'echo -n 1 > /dev/watchdog' 2>/dev/null
if ! ps -ef | grep -v grep | grep -q "oneos_wdog_feeder.sh"; then
    echo "Starting watchdog feeder..."
    cat > "$STAGE/oneos_wdog_feeder.sh" <<'WDOG'
L=/data/local/tmp/oneos/watchdog_feeder.log
holders() {
    for p in /proc/[0-9]*; do
        ls -l "$p/fd" 2>/dev/null | grep -qE '/dev/(watchdog|softdog)' && printf ' %s:%s' "${p#/proc/}" "$(cat "$p/comm" 2>/dev/null)"
    done
}
# Every watchdog the kernel lists: name, identity, state, timeout, time left.
wdogs() {
    for w in /sys/class/watchdog/watchdog*; do
        [ -d "$w" ] || continue
        printf ' [%s "%s" %s timeout %s left %s]' "${w##*/}" "$(cat "$w/identity" 2>/dev/null)" "$(cat "$w/state" 2>/dev/null)" \
            "$(cat "$w/timeout" 2>/dev/null)" "$(cat "$w/timeleft" 2>/dev/null)"
    done
}
{ echo "$(date +%T) nodes: $(ls -ln /dev/watchdog* /dev/softdog* 2>/dev/null | awk '{printf "%s %s:%s %s; ", $NF, $3, $4, $1}')"
  echo "$(date +%T) persist.vendor.softdog=$(getprop persist.vendor.softdog) init.svc.watchdogd=$(getprop init.svc.watchdogd); kernel:$(wdogs)"; } >> "$L"
was=''; n=0; seen=''
while true; do
    if e=$(printf V 2>&1 > /dev/watchdog); then now=written; else now="refused ($e)"; fi
    if [ -c /dev/softdog ]; then
        if e=$(printf V 2>&1 > /dev/softdog); then now="$now; /dev/softdog kicked"; else now="$now; /dev/softdog refused ($e)"; fi
    fi
    # The node(s) One UI's system_server had open at the switch (host_softdog_nodes,
    # oneos_switch.sh): the S24 Exynos's /dev/watchdog1, beside a busy /dev/watchdog;
    # since 0.4.66 also every watchdog node of group system (the A17 5G's watchdog1).
    # Its own variable: with n (the loop counter below) the shell left n=<node>
    # and the feeder exited on n=$((n + 1)) after its first kick (0.4.67 S25+
    # e92bad4f: three log lines, then softdog_fire).
    for wd in $(cat /data/local/tmp/oneos/host_softdog_nodes 2>/dev/null); do
        case "$wd" in /dev/watchdog|/dev/softdog) continue ;; esac
        [ -c "$wd" ] || continue
        if e=$(printf V 2>&1 > "$wd"); then now="$now; $wd kicked"; else now="$now; $wd refused ($e)"; fi
    done
    # An active software watchdog other than /dev/watchdog: kicked ("V", the
    # magic close where the driver allows it), never started.
    for w in /sys/class/watchdog/watchdog*; do
        [ "$(cat "$w/state" 2>/dev/null)" = active ] || continue
        case "$(cat "$w/identity" 2>/dev/null)" in *[Ss]oft*) ;; *) continue ;; esac
        d=/dev/${w##*/}
        [ -c "$d" ] || continue
        if e=$(printf V 2>&1 > "$d"); then now="$now; $d kicked"; else now="$now; $d refused ($e)"; fi
    done
    if [ "$now" != "$was" ]; then
        echo "$(date +%T) /dev/watchdog $now; held by:$(holders)" >> "$L"
        was=$now
    fi
    n=$((n + 1))
    if [ $((n % 5)) = 0 ]; then
        k=$(wdogs)
        [ "$(echo "$k" | sed 's/ left [0-9]*\]/]/g')" != "$seen" ] || [ $((n % 30)) = 0 ] &&
            echo "$(date +%T) persist.vendor.softdog=$(getprop persist.vendor.softdog); kernel:$k" >> "$L"
        seen=$(echo "$k" | sed 's/ left [0-9]*\]/]/g')
    fi
    sleep 2
done
WDOG
    chmod 700 "$STAGE/oneos_wdog_feeder.sh"
    nohup $BB sh "$STAGE/oneos_wdog_feeder.sh" </dev/null >/dev/null 2>&1 &
fi

echo "=== 2. $(date +%T) Creating Loop Device Nodes ==="
# Only make the nodes that are missing or not the loop block device: stat the
# tree once, let awk list the exceptions, mknod those. Recreating all 202 nodes
# cost 7 s on the S25 Ultra.
LOOP_NEED=$(stat -c '%n %t %T' /dev/block/loop* /dev/loop* 2>/dev/null | awk '
    $1 ~ /^\/dev\/block\/loop[0-9]+$/ { b[$1] = $2 " " $3 }
    $1 ~ /^\/dev\/loop[0-9]+$/       { d[$1] = $2 " " $3 }
    END {
        for (i = 50; i <= 150; i++) {
            m = sprintf("%x", i * 8)
            if (b["/dev/block/loop" i] != "7 " m || d["/dev/loop" i] != "7 " m) print i
        }
    }')
for i in $LOOP_NEED; do
    minor=$((i * 8))
    rm -f /dev/block/loop$i /dev/loop$i 2>/dev/null || true
    mknod /dev/block/loop$i b 7 $minor
    mknod /dev/loop$i b 7 $minor
done

echo "=== 3. $(date +%T) Mounting system.raw if needed ==="
# Read-only flag of a loop device, by its device number (the node names made
# above need not match the kernel's loopN).
loop_ro() {
    d=$(stat -L -c '%t %T' "$1" 2>/dev/null) || return 1
    set -- $d
    [ "$(cat "/sys/dev/block/$(printf '%d:%d' "0x$1" "0x$2")/ro" 2>/dev/null)" = 1 ]
}
if mount | grep -q "$ROOTFS "; then
    if [ ! -f "$ROOTFS/system/bin/sh" ] || [ ! -f "$ROOTFS/init.environ.rc" ]; then
        echo "Rootfs mount is invalid or stale. Unmounting..."
        while mount | grep -q "$ROOTFS"; do
            $BB umount -l "$ROOTFS" 2>/dev/null || true
            sleep 0.1
        done
    else
        echo "Rootfs already mounted and healthy."
    fi
fi

mkdir -p "$ROOTFS"
if ! mount | grep -q "$ROOTFS "; then
    for l in $($BB losetup -a | grep "system.raw" | cut -d: -f1); do
        $BB losetup -d "$l" 2>/dev/null || true
    done
    LOOP=$($BB losetup -f)
    # OneOS: a read-only loop device. A plain one let the ro ext4 mount replay
    # a journal into system.raw, which changes the file the app verified (its
    # stat identity in system.raw.id, checked before every switch).
    if ! $BB losetup -r "$LOOP" "$STAGE/system.raw"; then
        echo "ERROR: could not attach system.raw read-only ($LOOP); not starting the guest"
        exit 3
    fi
    if ! loop_ro "$LOOP"; then
        if [ "${ONEOS_APP:-0}" = 1 ]; then
            echo "ERROR: $LOOP is not read-only after losetup -r; not starting the guest"
            $BB losetup -d "$LOOP" 2>/dev/null
            exit 3
        fi
        echo "WARNING: could not confirm that $LOOP is read-only (sysfs)"
    fi
    echo "Using LOOP: $LOOP (read-only)"
    $BB mount -t ext4 -o ro "$LOOP" "$ROOTFS"
fi

# /system_ext as its own mount (vivo OriginOS, 0.4.59). Its boot classpath has
# MediaTek jars in /system_ext/framework, and its zygote allowlists the files
# open at a fork by those paths (/system_ext/framework/*.jar, /system_ext/app/
# mediatek-res/mediatek-res.apk). In MysticGSI's merged image /system_ext is a
# link to /system/system_ext, so an open jar reads as /system/system_ext/...:
# "Not allowlisted (29): /system/system_ext/framework/mediatek-common.jar" and
# zygote aborted forking system_server (first run). For an image whose boot
# classpath names /system_ext/ and whose /system_ext is that link, the root gets
# a read-only overlay whose top layer (a small tmpfs) holds only a system_ext
# folder, hiding the link; the real folder is bound there at the end of the
# setup (below), after every mount made under it. Everything until then uses
# /system/system_ext (GUEST_SYSTEM_EXT). Other images are not touched.
SEXT_MOUNT=0
if [ -L "$ROOTFS/system_ext" ] && [ "$(readlink "$ROOTFS/system_ext")" = /system/system_ext ] &&
   [ -d "$ROOTFS/system/system_ext" ] && [ ! -L "$ROOTFS/system/system_ext" ] &&
   grep -aq '/system_ext/framework/' "$ROOTFS/system/etc/classpaths/bootclasspath.pb" 2>/dev/null; then
    ROV="$STAGE/root_ov"
    [ ! -L "$ROV" ] || { echo "ERROR: $ROV is a symlink; not starting the guest"; exit 3; }
    mkdir -p "$ROV"
    mount | grep -q " $ROV " || $BB mount -t tmpfs -o size=64k,mode=755 tmpfs "$ROV"
    $BB mount --make-private "$ROV" 2>/dev/null || true
    rm -rf "$ROV/up" && mkdir -p "$ROV/up/system_ext" && chmod 755 "$ROV/up" "$ROV/up/system_ext"
    $BB chcon u:object_r:system_file:s0 "$ROV/up/system_ext" 2>/dev/null || true
    if $BB mount -t overlay overlay -o "ro,lowerdir=$ROV/up:$ROOTFS" "$ROOTFS" &&
       [ -d "$ROOTFS/system_ext" ] && [ ! -L "$ROOTFS/system_ext" ] && [ -f "$ROOTFS/system/etc/classpaths/bootclasspath.pb" ]; then
        SEXT_MOUNT=1
        echo "/system_ext: the boot classpath has /system_ext jars and the image links /system_ext; root overlay made, the folder is bound at the end"
    else
        echo "ERROR: could not give /system_ext its own mount (overlay on $ROOTFS); not starting the guest"
        exit 3
    fi
fi

mkdir -p "$ROOTFS/postinstall" "$ROOTFS/dev" "$ROOTFS/proc" "$ROOTFS/sys" \
    "$ROOTFS/linkerconfig" "$ROOTFS/vendor" "$ROOTFS/odm" "$ROOTFS/vendor_dlkm" \
    "$ROOTFS/mnt" "$ROOTFS/storage" "$ROOTFS/apex" "$ROOTFS/data"

echo "=== 4. $(date +%T) Setting up Core System Bind Mounts ==="
mount | grep -q "$ROOTFS/proc " || $BB mount -t proc proc "$ROOTFS/proc"
# The host's /sys with everything mounted under it (not a fresh sysfs): the
# guest needs the cgroup2 hierarchy at /sys/fs/cgroup, or zygote cannot put
# system_server in a process group ("createProcessGroup(1000, 0) failed: No
# such file or directory") and it dies on fork; selinuxfs and the bpf fs live
# there too.
if ! mount | grep -q "$ROOTFS/sys "; then
    $BB mount --rbind /sys "$ROOTFS/sys"
    $BB mount --make-rslave "$ROOTFS/sys"
fi

if [ ! -e /dev/binderfs/binder ]; then
    mount -t binder binder /dev/binderfs 2>/dev/null || true
    chmod 666 /dev/binderfs/binder /dev/binderfs/hwbinder /dev/binderfs/vndbinder 2>/dev/null || true
fi

$BB mount --make-rprivate "$ROOTFS" 2>/dev/null || true

if ! mount | grep -q "$ROOTFS/dev "; then
    $BB mount --rbind /dev "$ROOTFS/dev"
    $BB mount --make-rprivate "$ROOTFS/dev"
fi

# OneOS: each bind is made rslave right after it is created, like /dev and /sys
# above. These are peers of the host's shared /mnt, /linkerconfig, /vendor, ...
# mounts; the final --make-rprivate "$ROOTFS" is reached only on the success
# path, so without this an early exit (a missing payload, the /data/adb remount)
# left them shared, and return_to_oneui.sh's umount -l then propagated to the
# host's own /mnt/vendor/efs, /vendor etc. (One UI lost its wifi APEX contents,
# system_server boot loop).
if mount | grep -q "$ROOTFS/linkerconfig " || $BB mount --rbind /linkerconfig "$ROOTFS/linkerconfig"; then
    $BB mount --make-rslave "$ROOTFS/linkerconfig" 2>/dev/null || true
fi
for vb in vendor odm vendor_dlkm; do
    if mount | grep -q "$ROOTFS/$vb " || $BB mount --bind "/$vb" "$ROOTFS/$vb"; then
        $BB mount --make-rslave "$ROOTFS/$vb" 2>/dev/null || true
    fi
done
# OPPO's AI engine for ColorOS (0.4.63): the image is OPPO's system partitions
# only, and the guest's /odm is One UI's. ColorOS's AI service loads
# /odm/lib64/libaiboost.so; without it every request failed ("AIUnitInferEngine:
# has not been initialized", AIBoostEnv: "/odm/lib64/libaiboost.so not found"),
# the lock screen's depth cut-out among them (A57 41b55d01: deepSceneryState is
# STATE_INVALID). oplus_odm_ai.tar (the ColorOS sets; libaiboost.so and its
# LiteRT/QNN delegates from the Find X9 Ultra's odm partition, CPH2841
# 17.0) is unpacked to the stage and laid over the guest's view of /odm,
# read-only; One UI's processes keep their own /odm. Plain files only, or the
# guest keeps the plain bind. ONEOS_GUEST_ODM_AI=0 leaves it out.
ODM_AI_TAR="$STAGE/oplus_odm_ai.tar"
if [ "${ONEOS_GUEST_ODM_AI:-1}" = 1 ] && [ -f "$ODM_AI_TAR" ] && [ ! -L "$ODM_AI_TAR" ]; then
    ODM_AI="$STAGE/odm_ai"
    st="$(stat -c %s:%Y "$ODM_AI_TAR" 2>/dev/null)"
    if [ -f "$ODM_AI/.from_tar" ] && [ "$(cat "$ODM_AI/.from_tar" 2>/dev/null)" = "$st" ] &&
            [ -f "$ODM_AI/lib64/libaiboost.so" ]; then
        ok=1
    else
        ok=1
        "$BB" tar -tvf "$ODM_AI_TAR" 2>/dev/null | "$BB" awk 'substr($1, 1, 1) != "-" && substr($1, 1, 1) != "d" { bad = 1 } / -> / { bad = 1 } END { exit bad }' || ok=0
        "$BB" tar -tf "$ODM_AI_TAR" 2>/dev/null | "$BB" awk '{ n = $0; sub(/^\.\//, "", n) } n == "" { next }
            n !~ /^lib64(\/[A-Za-z0-9_][A-Za-z0-9._-]*)*\/?$/ || n ~ /(^|\/)\.\.?(\/|$)/ { bad = 1 } END { exit bad }' || ok=0
        if [ $ok = 1 ]; then
            rm -rf "$ODM_AI" && mkdir -p "$ODM_AI" && "$BB" tar -xf "$ODM_AI_TAR" -C "$ODM_AI" &&
                [ -z "$(find "$ODM_AI" ! -type f ! -type d -print -quit)" ] && [ -f "$ODM_AI/lib64/libaiboost.so" ] || ok=0
            [ $ok = 1 ] && printf '%s\n' "$st" > "$ODM_AI/.from_tar"
        fi
    fi
    if [ $ok = 1 ]; then
        find "$ODM_AI" -type d -exec chmod 755 {} + ; find "$ODM_AI" -type f -exec chmod 644 {} +
        $BB chcon -R u:object_r:vendor_file:s0 "$ODM_AI" 2>/dev/null || true
        $BB umount -l "$ROOTFS/odm" 2>/dev/null || true
        if $BB mount -t overlay overlay -o "ro,lowerdir=$ODM_AI:/odm" "$ROOTFS/odm"; then
            $BB mount --make-rslave "$ROOTFS/odm" 2>/dev/null || true
            echo "OPPO AI engine: odm/lib64/libaiboost.so and its delegates over the guest's /odm (read-only overlay)"
        else
            $BB mount --bind /odm "$ROOTFS/odm" && $BB mount --make-rslave "$ROOTFS/odm" 2>/dev/null
            echo "!!! OPPO AI engine: overlay on the guest's /odm refused; One UI's /odm as before"
        fi
    else
        echo "!!! OPPO AI engine: oplus_odm_ai.tar is not plain lib64 files; left out"
    fi
fi
# apexd is a HOST daemon: it reports the Samsung apex set (/system/apex,
# /system_ext/apex, /vendor/apex) to the container system_server, which then
# tries to parse those exact paths inside this namespace. Keep the apex
# directories identical to what host apexd sees (an empty tmpfs or the GSI's
# own .capex layout makes PMS abort with "Unable to parse" at boot).
# OneOS: resolve system_ext inside the rootfs. In a GSI it is an absolute
# symlink (/system/system_ext), which in this (host) namespace points at the
# HOST's /system_ext, so the bind used to land on the host's own apex dir and
# the guest kept its own: PackageManagerService then died parsing
# /system_ext/apex/com.android.compos.apex, which host apexd reports but the
# guest's tree does not have.
GUEST_SYSTEM_EXT="$ROOTFS/system_ext"
{ [ -L "$GUEST_SYSTEM_EXT" ] || [ "$SEXT_MOUNT" = 1 ]; } && GUEST_SYSTEM_EXT="$ROOTFS/system/system_ext"
# product the same way, the other way round: ColorOS and Pixel images have
# system/product and an absolute link /product -> /system/product; others
# have /product and system/product -> /product, which in this namespace is One
# UI's /product (see host_part_mounts at the top).
GUEST_PRODUCT="$ROOTFS/system/product"
[ -L "$GUEST_PRODUCT" ] && GUEST_PRODUCT="$ROOTFS/product"
for d in "$GUEST_SYSTEM_EXT" "$GUEST_PRODUCT"; do
    if [ -L "$d" ] || [ ! -d "$d" ]; then
        echo "ERROR: ${d#$ROOTFS/} in the guest image is a link or missing (system_ext and product: one real folder each); not starting the guest"
        exit 3
    fi
done
# Signal bars in a guest without ColorOS's OplusSignalSmooth (run 43, Pixel):
# Samsung's RIL sends the guest no signal strength indication and AOSP polls
# only for opportunistic subscriptions, so both SIMs kept the all-invalid value
# read right after RADIO_POWER on (level 0 all session). TeleService's own
# TelephonyComponentFactory injection loads oneos-telephony.jar
# (scripts/make-overlays.sh), whose OneOSSignalPoll sends GET_SIGNAL_STRENGTH
# every 20 s with the screen on: the jar goes in a read-only overlay layer on
# the guest's system_ext below (the injection takes a jar only on a read-only
# mount under /system, /product or /system_ext), OneOSPhoneInjection.apk in its
# /oem/overlay names it. Only on the telephony-common.jar and TeleService.apk
# the jar was built and checked against (oneos-telephony.sha256): a stale RRO
# would replace another image's own injection config. The oplus jar is tested
# here directly (GUEST_OTC is set further down). ONEOS_GUEST_SIGNAL_POLL=0
# leaves it out.
INJ=0
if [ -d "$GUEST_SYSTEM_EXT" ] && [ ! -f "$GUEST_SYSTEM_EXT/framework/oplus-telephony-common.jar" ]; then
    if [ "${ONEOS_GUEST_SIGNAL_POLL:-1}" != 1 ]; then
        echo "Signal poll: off (ONEOS_GUEST_SIGNAL_POLL=0)"
    elif [ -f "$STAGE/oneos-telephony.jar" ] && [ -f "$STAGE/OneOSPhoneInjection.apk" ] && [ -f "$STAGE/oneos-telephony.sha256" ]; then
        INJ=1
        inj_n=0
        while read -r inj_sum inj_rel; do
            inj_n=$((inj_n + 1))
            [ -n "$inj_rel" ] && [ "$($BB sha256sum "$ROOTFS/$inj_rel" 2>/dev/null | cut -d' ' -f1)" = "$inj_sum" ] ||
                { INJ=0; echo "Signal poll: off ($inj_rel is not the file oneos-telephony.jar was built for)"; }
        done < "$STAGE/oneos-telephony.sha256"
        [ "$inj_n" = 2 ] || { INJ=0; echo "Signal poll: off (oneos-telephony.sha256 has $inj_n lines, 2 expected)"; }
    else
        echo "Signal poll: oneos-telephony.jar, .sha256 or OneOSPhoneInjection.apk not staged (make-overlays.sh builds them only for an image they fit)"
    fi
fi
# HIDL. libhidlbase uses hwservicemanager only when one of its binaries is
# there (system/system_ext/bin, system_ext/bin or system/bin; access() only,
# nothing runs it). Infinity-X is built for a phone without HIDL: its
# system/bin/hwservicemanager links to a system_ext file it does not ship, so
# every guest process took HIDL for absent. On the S23's HIDL-only display
# composer its surfaceflinger aborted ("failed to get hwcomposer service") and
# audioserver found no audio HAL (S23 Ultra session 99ef8224). One UI's
# hwservicemanager serves /dev/hwbinder to the guest as to the images that
# ship one (ColorOS), so an empty file at system_ext/bin/hwservicemanager in
# the overlay below lets the guest's HIDL clients ask it. Only when the image
# has none, One UI runs hwservicemanager, and this phone's vendor manifest
# declares no AIDL display composer or no AIDL audio HAL (as return_to_oneui.sh
# reads it): elsewhere the guests without one (Pixel) keep running as they do.
# The radio too (0.4.74): the MediaTek A07/A16 4G/A17 have AIDL display and audio
# but only HIDL android.hardware.radio@1.6 (IRadio/slot1), so Infinity-X asked for
# it "without hwservicemanager" and showed no SIM, greyed SIM settings and no calls
# or SMS (A07 9de07236, 4e47fe7c), while ColorOS and HyperOS, which ship
# hwservicemanager, found it. Counted only when the vendor declares the HIDL radio
# and no AIDL radio (android.hardware.radio.sim).
HWSM=0
HWSM_WHY=""
"$BB" grep -rqs 'android.hardware.graphics.composer3' /vendor/etc/vintf/ || HWSM_WHY="display composer"
"$BB" grep -rqs 'android.hardware.audio.core' /vendor/etc/vintf/ || HWSM_WHY="${HWSM_WHY:+$HWSM_WHY and }audio HAL"
VM_AIDL=no
VM_HIDL=no
"$BB" grep -rqs 'android.hardware.radio.sim' /vendor/etc/vintf/ && VM_AIDL=yes
"$BB" grep -rqsE '<name>android\.hardware\.radio</name>' /vendor/etc/vintf/ && VM_HIDL=yes
[ $VM_AIDL = no ] && [ $VM_HIDL = yes ] && HWSM_WHY="${HWSM_WHY:+$HWSM_WHY and }radio HAL"
# The image has no hwservicemanager of its own and One UI runs one.
hwsm_fits() {
    [ -d "$GUEST_SYSTEM_EXT/bin" ] &&
        [ ! -e "$GUEST_SYSTEM_EXT/bin/hwservicemanager" ] && [ ! -L "$GUEST_SYSTEM_EXT/bin/hwservicemanager" ] &&
        { [ -L "$ROOTFS/system/bin/hwservicemanager" ] || [ ! -e "$ROOTFS/system/bin/hwservicemanager" ]; } &&
        pidof hwservicemanager >/dev/null
}
# 0.4.87: the manifest text did not say it on the phones it was written for.
# Infinity-X on the A07 (721f435a) and the A15 (be9415c0), both on 0.4.83, got no
# marker and no line about it, and asked for IRadio/slot1 "without
# hwservicemanager" as before: no SIM all session. No report has the manifest
# files, so which half of the test fails there is not known (a second manifest
# for another model in the same folder would do it). When the manifest gives no
# reason, the running services are asked instead: One UI's rild stays up through
# the switch, so the radio is HIDL-only when no AIDL IRadioSim/slot1 is
# registered and hwservicemanager lists an IRadio. If lshal lists nothing at
# all, a running rild without an AIDL service counts the same. The line says
# what all four saw, marker or not.
if [ -z "$HWSM_WHY" ] && hwsm_fits; then
    RA=$("$BB" timeout 10 /system/bin/service check android.hardware.radio.sim.IRadioSim/slot1 2>/dev/null)
    case "$RA" in
        *"not found"*) RA=no ;;
        *found*) RA=yes ;;
        *) RA=unknown ;;
    esac
    RH=unknown
    if [ $RA = no ]; then
        HL=$("$BB" timeout 10 /system/bin/lshal list -i --types=b 2>/dev/null)
        if echo "$HL" | "$BB" grep -qE 'android\.hardware\.radio@[0-9.]+::IRadio/'; then
            RH=yes
        elif echo "$HL" | "$BB" grep -q '::I'; then
            RH=no
        fi
    fi
    if [ $RA = no ] && [ $RH = yes ]; then
        HWSM_WHY="radio HAL"
    elif [ $RA = no ] && [ $RH = unknown ] && [ "$(getprop init.svc.ril-daemon 2>/dev/null)" = running ]; then
        HWSM_WHY="radio HAL"
    fi
    echo "HIDL: this image has no hwservicemanager and One UI runs one. Radio by its services: AIDL $RA, HIDL $RH; by the vendor manifest: AIDL $VM_AIDL, HIDL $VM_HIDL${HWSM_WHY:+ (HIDL-only: the marker is set)}"
fi
if [ -n "$HWSM_WHY" ] && hwsm_fits; then
    HWSM=1
fi
# --- Samsung's IMS stack in the guest (ONEOS_GUEST_SEC_IMS=1) ----------------
# VoLTE on a Samsung phone is the system app com.sec.imsservice (the SIP stack
# is its libsec-ims.so). It reaches the modem through the vendor HAL channel
# vendor.samsung.hardware.radio.channel.ISehRadioChannel/imsd and the host
# daemon imsd over /dev/socket/imsd; both survive the switch (the guest sees
# the host's /dev), the app does not: it dies with One UI's framework, so every
# guest ran calls on 3G and a VoLTE-only carrier (T-Mobile US) got none. The
# app is a plain android.telephony.ims.ImsService (BIND_IMS_SERVICE), so the
# guest's telephony can bind it like its own. Nothing of it is shipped: every
# One UI build has its own, so it is taken from THIS phone's One UI at every
# prepare, read from /system and copied into $STAGE/secims, a lower layer of
# the guest's system_ext (below): the APK as a system_ext priv-app with its
# privapp-permissions list, its library jars with their XMLs, the three native
# libraries (the system linker namespace searches /system_ext/lib64). The 33
# Samsung-only framework classes it needs (307 with what they pull in: Sem*
# managers, CSC features, the HAL stubs) come from One UI's own framework.jar,
# handed to it as the optional library "secimshttpclient" that the app's
# manifest already declares and One UI does not define; the guest's boot
# classes win on every duplicate name, so only the Samsung classes load from
# it. The guest's package manager takes this Samsung-signed package into
# android.uid.system only from this staged path (a services.jar carve-out,
# scripts/make-overlays.sh patches/guest_sec_ims_signature.py; recorded as the
# secims word in guards.txt). Off unless ONEOS_GUEST_SEC_IMS=1.
SEC_IMS=0
SECIMS="$STAGE/secims"
rm -f "$STAGE/data/oneos_sec_ims"
sec_ims_off() { echo "Samsung IMS in the guest: off ($1)"; rm -rf "$SECIMS" 2>/dev/null; }
sec_ims_stage() {
    st=$(for f in /system/priv-app/imsservice/imsservice.apk /system/framework/imsmanager.jar \
        /system/framework/rcsopenapi.jar /system/framework/framework.jar \
        /system/lib64/libsec-ims.so /system/lib64/libresampler_ims.so /system/lib64/libaresdns.so \
        /system/etc/permissions/privapp-permissions-com.sec.imsservice.phone.xml \
        /system/lib64/lib.engmodejni.samsung.so /system/etc/public.libraries-engmodejni.samsung.txt \
        /system/framework/vsimmanager.jar /system/framework/EpdgManager.jar; do
        if [ -e "$f" ]; then stat -c '%n %s %Y' "$f"; else echo "$f absent"; fi
    done | sha256sum | cut -d' ' -f1)
    if [ -f "$SECIMS/.stamp" ] && [ "$(cat "$SECIMS/.stamp" 2>/dev/null)" = "$st" ]; then
        echo "Samsung IMS in the guest: staged set unchanged ($(du -sk "$SECIMS" 2>/dev/null | cut -f1) KB cached)"
        return 0
    fi
    rm -rf "$SECIMS"
    mkdir -p "$SECIMS/priv-app/OneOSSecIms" "$SECIMS/framework" "$SECIMS/lib64" "$SECIMS/etc/permissions" || return 1
    cp /system/priv-app/imsservice/imsservice.apk "$SECIMS/priv-app/OneOSSecIms/" || return 1
    cp /system/framework/imsmanager.jar /system/framework/rcsopenapi.jar "$SECIMS/framework/" || return 1
    cp /system/framework/framework.jar "$SECIMS/framework/oneos-secims-compat.jar" || return 1
    cp /system/lib64/libsec-ims.so /system/lib64/libresampler_ims.so /system/lib64/libaresdns.so "$SECIMS/lib64/" || return 1
    cp /system/etc/permissions/privapp-permissions-com.sec.imsservice.phone.xml "$SECIMS/etc/permissions/" || return 1
    # Samsung's EngineeringModeManager (in the framework classes above) loads
    # lib.engmodejni.samsung.so; without it the app died at start (F8U test5:
    # UnsatisfiedLinkError, after the class loader fix). Public through One UI's
    # own list for it, which the guest reads from system_ext/etc like /system/etc.
    if [ -f /system/lib64/lib.engmodejni.samsung.so ] && [ -f /system/etc/public.libraries-engmodejni.samsung.txt ]; then
        mkdir -p "$SECIMS/etc" &&
            cp /system/lib64/lib.engmodejni.samsung.so "$SECIMS/lib64/" &&
            cp /system/etc/public.libraries-engmodejni.samsung.txt "$SECIMS/etc/" || return 1
    fi
    # Libraries the manifest lists as not required: along when One UI has them.
    for lib in vsimmanager EpdgManager; do
        [ -f "/system/framework/$lib.jar" ] && { cp "/system/framework/$lib.jar" "$SECIMS/framework/" || return 1; }
    done
    # The library XMLs name the guest's copies. Each Samsung library gets its own
    # class loader, which sees only the libraries it depends on: imsmanager's
    # com.sec.ims.util.DeviceCategory needs android.os.SemSystemProperties, so
    # without the dependency on secimshttpclient (One UI's framework classes) the
    # app died at start with NoClassDefFoundError and Android stopped restarting
    # it (F8U, Find N6 global, 0.4.38 test4: no IMS, no SMS).
    for pair in imsmanager:imsmanager.jar rcsopenapi:rcsopenapi.jar secimshttpclient:oneos-secims-compat.jar \
                vsimmanager:vsimmanager.jar EpdgManager:EpdgManager.jar; do
        [ -f "$SECIMS/framework/${pair#*:}" ] || continue
        dep=' dependency="secimshttpclient"'
        [ "${pair%%:*}" != secimshttpclient ] || dep=''
        printf '<?xml version="1.0" encoding="utf-8"?>\n<permissions>\n    <library name="%s" file="/system_ext/framework/%s"%s/>\n</permissions>\n' \
            "${pair%%:*}" "${pair#*:}" "$dep" > "$SECIMS/etc/permissions/${pair%%:*}_library.xml" || return 1
    done
    # Make the guest advertise IMS support. An AOSP-based guest (Infinity-X, the
    # Pixels) only starts ImsResolver when the device has FEATURE_TELEPHONY_IMS;
    # without it PhoneFactory logs "IMS is not supported on this device, skipping
    # ImsResolver" and the staged app is installed but never bound (report
    # 707642218d0049a0: S24 Ultra on Infinity-X, calls stayed on 3G/failed).
    # system_ext/etc/permissions is scanned for <feature>. One UI/ColorOS images
    # already declare it, so this is a no-op there.
    printf '<?xml version="1.0" encoding="utf-8"?>\n<permissions>\n    <feature name="android.hardware.telephony.ims"/>\n</permissions>\n' \
        > "$SECIMS/etc/permissions/oneos-telephony-ims.xml" || return 1
    find "$SECIMS" -type d -exec chmod 755 {} + && find "$SECIMS" -type f -exec chmod 644 {} + || return 1
    $BB chcon -h -R u:object_r:system_file:s0 "$SECIMS" 2>/dev/null || true
    $BB chcon -h u:object_r:system_lib_file:s0 "$SECIMS"/lib64/*.so 2>/dev/null || true
    printf '%s\n' "$st" > "$SECIMS/.stamp" || return 1
    return 0
}
# Bind the staged Samsung IMS tree onto the guest's system_ext (made writable by
# the overlay below) a file at a time, rather than adding $SECIMS as a second
# overlay lower layer: some kernels (Galaxy S24 Ultra, report 8fe87c0c9064a2a2)
# reject an overlay with more than one lower dir (mount ... : Invalid argument).
# Only empty mount points are created in the overlay's tmpfs upper; the content
# stays on the staged copy. The return path unmounts every mount under the stage.
sec_ims_bind() {
    local gse="$GUEST_SYSTEM_EXT" n=0 f t d
    mkdir -p "$gse/priv-app/OneOSSecIms" || return 1
    $BB mount --bind "$SECIMS/priv-app/OneOSSecIms" "$gse/priv-app/OneOSSecIms" || return 1
    $BB mount --make-rslave "$gse/priv-app/OneOSSecIms" 2>/dev/null || true
    for d in framework lib64 etc etc/permissions; do
        [ -d "$SECIMS/$d" ] || continue
        mkdir -p "$gse/$d" || return 1
        for f in "$SECIMS/$d"/*; do
            [ -f "$f" ] || continue
            t="$gse/$d/$(basename "$f")"
            [ -e "$t" ] || : > "$t" || return 1
            $BB mount --bind "$f" "$t" || return 1
            $BB mount --make-rslave "$t" 2>/dev/null || true
            n=$((n + 1))
        done
    done
    echo "Samsung IMS in the guest: staged set bind-mounted onto $gse (OneOSSecIms priv-app + $n files; this kernel rejects a second overlay lower layer)"
    return 0
}
# Samsung IMS's mount points in an overlay's own layer (0.4.43): the read-only (signal
# poll) overlay of HyperOS, Infinity-X and Nothing OS takes no mkdir or new file later,
# so sec_ims_bind had nowhere to bind and IMS was off on all three (calls and SMS on
# VoLTE-only networks: reports 4e9c9333, 71a26ead, c70e1b54 on 0.4.40). Empty files,
# so the overlay's 1 MB tmpfs is enough; only names the image does not have itself.
secims_mountpoints() {
    local up="$1" d f
    mkdir -p "$up/priv-app/OneOSSecIms" || return 1
    for d in framework lib64 etc etc/permissions; do
        [ -d "$SECIMS/$d" ] || continue
        for f in "$SECIMS/$d"/*; do
            [ -f "$f" ] || continue
            [ -e "$GUEST_SYSTEM_EXT/$d/$(basename "$f")" ] && continue
            mkdir -p "$up/$d" && : > "$up/$d/$(basename "$f")" || return 1
        done
    done
    find "$up" -type d -exec chmod 755 {} + 2>/dev/null
    $BB chcon -R u:object_r:system_file:s0 "$up/priv-app" 2>/dev/null || true
    for d in framework etc; do [ -d "$up/$d" ] && $BB chcon -R u:object_r:system_file:s0 "$up/$d" 2>/dev/null; done
    [ -d "$up/lib64" ] && $BB chcon -R u:object_r:system_lib_file:s0 "$up/lib64" 2>/dev/null
    return 0
}
if [ "${ONEOS_GUEST_SEC_IMS:-0}" = 1 ]; then
    secims_missing=""
    for f in /system/priv-app/imsservice/imsservice.apk /system/framework/framework.jar /system/framework/imsmanager.jar \
             /system/framework/rcsopenapi.jar /system/lib64/libsec-ims.so /system/lib64/libresampler_ims.so \
             /system/lib64/libaresdns.so /system/etc/permissions/privapp-permissions-com.sec.imsservice.phone.xml; do
        [ -f "$f" ] || secims_missing="$secims_missing $f"
    done
    if [ ! -d "$GUEST_SYSTEM_EXT" ]; then sec_ims_off "the guest has no system_ext"
    elif [ -L "$SECIMS" ]; then echo "ERROR: $SECIMS is a symlink; not starting the guest"; exit 3
    # Only the sets whose services.jar carries the carve-out can keep the
    # Samsung-signed package in android.uid.system; on the others the guest's
    # scan drops it and calls stay on 3G with nothing in the log to say why.
    # Say it here instead of staging 40 MB the guest will throw away.
    elif ! grep '^#' "$STAGE/guards.txt" | grep -qw secims; then
        sec_ims_off "this system's overlays were built without the secims carve-out (guards.txt): the guest would drop com.sec.imsservice"
    elif [ -n "$secims_missing" ]; then sec_ims_off "this One UI lacks$secims_missing"
    elif [ -f /system/etc/permissions/secimshttpclient_library.xml ] || [ -f /system_ext/etc/permissions/secimshttpclient_library.xml ]; then
        sec_ims_off "this One UI defines the secimshttpclient library itself; the compat jar needs that name"
    elif sec_ims_stage; then
        SEC_IMS=1
        touch "$STAGE/data/oneos_sec_ims"
        echo "Samsung IMS in the guest: staged from this One UI ($(du -sk "$SECIMS" 2>/dev/null | cut -f1) KB: $(ls "$SECIMS/framework" | tr '\n' ' ')$(ls "$SECIMS/lib64" | tr '\n' ' '))"
    else
        sec_ims_off "copy from /system failed"
    fi
else
    rm -rf "$SECIMS" 2>/dev/null
fi
# --- Samsung Camera in the guest (staged $STAGE/samcam_build) ------------------
# Nothing OS's own camera needs Nothing's camera HAL; this phone's HAL and
# camera service are Samsung's, which the guest already uses. So One UI's
# camera app runs in the guest instead: its APK rewritten on the server so that
# the Samsung (sem*) members of platform classes that a non-Samsung framework
# lacks go to static shims, its two library jars likewise, and the One UI
# classes it reaches (Sem* managers, floating/CSC features, MotionPhoto) in
# oneos-camera-compat.jar, handed to it as its optional library
# worker_wrapper_compat (switcher/samsung-camera.md). The app, the jars and
# their permission files go onto the guest's system_ext (empty mount points in
# that overlay's tmpfs layer, which may be the read-only one the signal poll
# needs). What its native code opens by One UI's own paths goes onto the
# guest's /system, through a read-only overlay of its own: the 101 native
# libraries (bound from One UI's /system/lib64; two from Samsung's imagecodec
# APEX are staged copies), /system/cameradata, /system/saiv and
# floating_feature.xml (also at /system_ext/etc, where the compat copy of
# SemFloatingFeature reads it). Only with the staged files;
# ONEOS_GUEST_SAMSUNG_CAMERA=0 leaves it out.
SAMCAM=0
SAMCAM_SRC="$STAGE/samcam_build"
SAMCAM_BOUND=0
SAMCAM_LIST="$STAGE/samcam_files.txt"
SAMCAM_SH=${ONEOS_TEST_SH:-/system/bin/sh}
# The set's samcam.tar (0.4.35 Nothing OS, 0.4.37 ColorOS), unpacked into
# samcam_build when it is not the one unpacked last (size and time). Each set's
# camera is rewritten against its own image's framework, so only a stage whose
# set brought a samcam.tar takes it (setup moves every other set's files to the
# attic); a samcam_build left from another system stays out.
# 0.4.55: a set that folds and bar phones share (Nothing OS) also carries a bar
# phone's camera, samcam_bar.tar (the Galaxy S26 Ultra's own); a phone (every
# form but fold) takes it. The Z Fold8 Ultra's camera, made for a foldable's two
# screens, had its layout wrong on every bar phone.
SAMCAM_TAR="$STAGE/samcam.tar"
if [ "${ONEOS_GUEST_FORM:-fold}" != fold ] && [ -f "$STAGE/samcam_bar.tar" ] && [ ! -L "$STAGE/samcam_bar.tar" ]; then
    SAMCAM_TAR="$STAGE/samcam_bar.tar"
fi
SAMCAM_IMAGE=0
[ -f "$SAMCAM_TAR" ] && [ ! -L "$SAMCAM_TAR" ] && SAMCAM_IMAGE=1
if [ $SAMCAM_IMAGE = 1 ] && [ ! -L "$SAMCAM_SRC" ] && [ "${ONEOS_GUEST_SAMSUNG_CAMERA:-1}" = 1 ]; then
    st="${SAMCAM_TAR##*/}:$(stat -c %s:%Y "$SAMCAM_TAR")"
    if [ "$(cat "$SAMCAM_SRC/.from_tar" 2>/dev/null)" != "$st" ]; then
        rm -rf "$SAMCAM_SRC" && mkdir -p "$SAMCAM_SRC" &&
            $BB tar -xf "$SAMCAM_TAR" -C "$SAMCAM_SRC" && echo "$st" > "$SAMCAM_SRC/.from_tar" &&
            echo "Samsung Camera: the set's ${SAMCAM_TAR##*/} unpacked into $SAMCAM_SRC" ||
            echo "Samsung Camera: ${SAMCAM_TAR##*/} did not unpack"
    fi
fi
# scamera_sdk_util.jar must be OneOS's (scripts/samsung-camera/scamera_util:
# CustomInterfaceHelper's CameraDevice.setParameters sent by SamsungParams).
# One UI's own calls a method no guest framework has ("Fail to set samsung
# parameter"): the HAL never gets samsungcamera=true and runs the camera as a
# third-party app ("Unihal is bypass mode", isSamsungCamera(0); 0.4.55 to
# 0.4.57 bar sets). A log line only.
if [ $SAMCAM_IMAGE = 1 ] && [ ! -L "$SAMCAM_SRC" ] && [ "${ONEOS_GUEST_SAMSUNG_CAMERA:-1}" = 1 ] &&
    [ -f "$SAMCAM_SRC/scamera_sdk_util.jar" ] &&
    ! grep -q 'Lcom/oneos/camera/SamsungParams;' "$SAMCAM_SRC/scamera_sdk_util.jar"; then
    echo "!!! Samsung Camera: scamera_sdk_util.jar is One UI's unpatched one: the camera HAL will treat the camera as a third-party app"
fi
# The camera's JNI libraries, which it loads by name from Java (uses-native-library
# and System.loadLibrary). libs.txt is the closure build-cached.sh derives from
# its native dependencies, which misses them; the Nothing set's (scripts/
# samsung-camera/build.sh) has all 36. Without libMyFilterPlugin the package
# manager gave the camera none of its libraries (NoClassDefFoundError
# oneos/semcompat/Sem; S25+ IN, F8U test1); without libcore2nativeutil its
# preview surface could not be measured and the capture session failed at once
# ("surfaceNativeUtil is null", "Unknown error -2147483648": a black preview, F8U
# test5). Bound from One UI's /system/lib64 only where the guest image has no
# library of that name, so none of the image's own is replaced.
# libAIQSolution_MPI: the night shot's MPI node (NodeFeatureLoader registers
# super_night.mpi.v2 from this phone's cameradata); the S26 Ultra has no such
# library, so libs.txt cannot name it: S25 Ultra 3715fe57, "dlopen failed:
# library libAIQSolution_MPI.camera.samsung.so not found", camera closed.
# libsuperresolutionraw_wrapper_v2 (0.4.81): the same on an S23 Ultra when a
# picture is taken (6c95a630, 0.4.74: preview fine, then "dlopen failed: library
# libsuperresolutionraw_wrapper_v2.camera.samsung.so not found", PostProcessThread
# "load nativeNode(id: 4000200) fail"). With it the other super resolution wrapper
# and the two ArcSoft engines Samsung ships beside them, which the wrappers link;
# their names are not confirmed from an S23 Ultra (the Fold8 has none of the
# four), and a name One UI lacks is left out as always. If the picture still
# fails there, the dlopen line names the next library.
SAMCAM_JNI="libAEBHDR_wrapper.camera.samsung.so libAIQSolution_MPI.camera.samsung.so libAIQSolution_MPISingleRGB40.camera.samsung.so \
    libDeflickerHDR.camera.samsung.so libDocMagnetEngine.camera.samsung.so \
    libDocRectifyWrapper.camera.samsung.so libDualCamBokehCapture.camera.samsung.so \
    libEventDetector.camera.samsung.so libFaceRestoration.camera.samsung.so libFoodDetector.camera.samsung.so \
    libLttEngine.camera.samsung.so libMyFilter.camera.samsung.so libMyFilterPlugin.camera.samsung.so \
    libPortraitSolution.camera.samsung.so libQREngine.camera.samsung.so libRectify.camera.samsung.so \
    libSDKMoireDetector.spenocr.samsung.so libSDKRecognitionOCR.spenocr.samsung.so \
    libSmartScan.camera.samsung.so libStereoSolution.camera.samsung.so libStride.camera.samsung.so \
    libUltraWideDistortionCorrection.camera.samsung.so libWideDistortionCorrection.camera.samsung.so \
    libagifencoder.quram.so libcommon-jni.vexfwk.samsung.so libcore2nativeutil.camera.samsung.so \
    libexifa.camera.samsung.so libhybridHDR_wrapper.camera.samsung.so libimage_enhancement.arcsoft.so \
    libjpega.camera.samsung.so libsdk-v2-jni.vexfwk.samsung.so libsecimaging.camera.samsung.so \
    libsecimaging_pdk.camera.samsung.so libsimba.cfa.media.samsung.so libsum_jni.media.samsung.so \
    libsume_jni.media.samsung.so libsume_mediabuffer_jni.media.samsung.so \
    libsuperresolutionraw_wrapper_v2.camera.samsung.so libsuperresolution_wrapper_v2.camera.samsung.so \
    libsuperresolution_raw.arcsoft.so libsuperresolution.arcsoft.so"
# libs.txt's names and the JNI libraries bound here, one per line.
samcam_jni_here() { # <lib>: One UI has it, libs.txt does not name it, the image has none of its own
    # A library of the image is never empty; the empty file there is this
    # function's own mount point (samcam_mountpoints), made before the binds
    # ask again (0.4.38 test6: -e saw it, nothing was bound, "file offset ...
    # >= file size: 0 >= 0").
    ! grep -q "^$1 " "$SAMCAM_SRC/libs.txt" && [ -e "/system/lib64/$1" ] &&
        [ ! -s "$ROOTFS/system/lib64/$1" ] && [ ! -L "$ROOTFS/system/lib64/$1" ]
}
samcam_libs() {
    awk '{ print $1 }' "$SAMCAM_SRC/libs.txt"
    for lib in $SAMCAM_JNI; do samcam_jni_here "$lib" && echo "$lib"; done
}
samcam_files() {
    # "<sys|sysext> <path under the guest's /system or system_ext> <source>".
    # Native code opens One UI's own paths (/system/cameradata, /system/saiv,
    # /system/etc/floating_feature.xml, libraries by /system/lib64 path; run 12:
    # "Feature file is not valid", the camera's feature list in
    # /system/cameradata), so those go onto the guest's /system as they are.
    echo "sysext priv-app/SamsungCamera/SamsungCamera.apk $SAMCAM_SRC/SamsungCamera.apk"
    # An empty Filter Provider (scripts/samsung-camera/filter_stub): the camera
    # observes One UI's at start and stopped without it (run 16: "Failed to
    # find provider com.samsung.android.provider.filterprovider").
    if [ -f "$SAMCAM_SRC/OneOSSamFilterStub.apk" ]; then echo "sysext app/OneOSSamFilterStub/OneOSSamFilterStub.apk $SAMCAM_SRC/OneOSSamFilterStub.apk"; fi
    for j in semextendedformat.jar secimaging.jar oneos-camera-compat.jar; do
        echo "sysext framework/$j $SAMCAM_SRC/$j"
    done
    echo "sysext etc/floating_feature.xml /system/etc/floating_feature.xml"
    echo "sysext etc/permissions/privapp-permissions-com.sec.android.app.camera.xml /system/etc/permissions/privapp-permissions-com.sec.android.app.camera.xml"
    for x in semextendedformat secimaging worker_wrapper_compat; do
        echo "sysext etc/permissions/oneos-samcam-$x.xml $SAMCAM_SRC/oneos-samcam-$x.xml"
    done
    # Its native helpers read hidden framework fields over JNI
    # (libcore2nativeutil: ImageReader$SurfaceImage.mNativeBuffer); One UI's
    # camera may, ours is not platform-signed: "can't find
    # android/graphics/ImageReader.mNativeBuffer", abort (run 17). A system
    # app listed here may use them.
    echo "sysext etc/sysconfig/oneos-samcam-hiddenapi.xml $SAMCAM_SRC/oneos-samcam-hiddenapi.xml"
    # One UI's libraries this phone has: the camera was built from the Z Fold8
    # Ultra's, which loads some only for features this phone's own camera list
    # (cameradata) does not turn on; an S24 Ultra or Z Fold6 has no
    # libAIDeflicker.camera.samsung.so, and the whole camera was off (0.4.36
    # reports 81f8194c, 8d915c9b). samcam_prepare names the ones left out.
    while read -r lib from; do
        case "$from" in
            apex) echo "sys lib64/$lib $SAMCAM_SRC/$lib" ;;
            *) [ -e "/system/lib64/$lib" ] && echo "sys lib64/$lib /system/lib64/$lib" ;;
        esac
    done < "$SAMCAM_SRC/libs.txt"
    for lib in $SAMCAM_JNI; do
        samcam_jni_here "$lib" && echo "sys lib64/$lib /system/lib64/$lib"
    done
    echo "sys etc/floating_feature.xml /system/etc/floating_feature.xml"
    for f in "$SAMCAM_SRC"/public.libraries-*.txt; do
        [ -f "$f" ] && echo "sys etc/${f##*/} $f"
    done
    # The camera loads /system/framework/scamera_sdk_util.jar itself for
    # setSamsungParameter (PdkUtil); One UI's calls CameraDevice.setParameters,
    # which a non-Samsung framework lacks, so the set's copy sends the same
    # binder call (scripts/samsung-camera/scamera_util). Without it the HAL got
    # no Samsung parameters and configuring the streams failed (run 15).
    if [ -f "$SAMCAM_SRC/scamera_sdk_util.jar" ]; then echo "sys framework/scamera_sdk_util.jar $SAMCAM_SRC/scamera_sdk_util.jar"; fi
    for d in cameradata saiv; do
        [ -d "/system/$d" ] && echo "sys $d /system/$d"
    done
}
samcam_prepare() {
    echo "Samsung Camera: prepare $(date +%T)"
    [ -f "$SAMCAM_SRC/SamsungCamera.apk" ] && [ -f "$SAMCAM_SRC/libs.txt" ] || return 1
    [ -d /system/cameradata ] || { echo "Samsung Camera: this One UI has no /system/cameradata"; return 1; }
    # The library declarations name the guest's copies. semextendedformat (the
    # one the manifest requires) depends on the other two, so its loader sees
    # the compat classes too.
    printf '<?xml version="1.0" encoding="utf-8"?>\n<permissions>\n    <library name="semextendedformat" file="/system_ext/framework/semextendedformat.jar" dependency="secimaging:worker_wrapper_compat"/>\n</permissions>\n' \
        > "$SAMCAM_SRC/oneos-samcam-semextendedformat.xml" || return 1
    printf '<?xml version="1.0" encoding="utf-8"?>\n<permissions>\n    <library name="secimaging" file="/system_ext/framework/secimaging.jar" dependency="worker_wrapper_compat"/>\n    <feature name="com.sec.android.secimaging"/>\n</permissions>\n' \
        > "$SAMCAM_SRC/oneos-samcam-secimaging.xml" || return 1
    printf '<?xml version="1.0" encoding="utf-8"?>\n<permissions>\n    <library name="worker_wrapper_compat" file="/system_ext/framework/oneos-camera-compat.jar"/>\n</permissions>\n' \
        > "$SAMCAM_SRC/oneos-samcam-worker_wrapper_compat.xml" || return 1
    printf '<?xml version="1.0" encoding="utf-8"?>\n<config>\n    <hidden-api-whitelisted-app package="com.sec.android.app.camera"/>\n</config>\n' \
        > "$SAMCAM_SRC/oneos-samcam-hiddenapi.xml" || return 1
    # The native libraries the camera's manifest requires (uses-native-library:
    # libMyFilterPlugin, libexifa, libjpega, libsecimaging(_pdk) .camera.samsung,
    # libagifencoder.quram) are public only through One UI's
    # /system/etc/public.libraries-<company>.txt. Without them the guest's
    # package manager gave the camera no libraries at all, the compat jar
    # included ("requires unavailable native shared library
    # libMyFilterPlugin.camera.samsung.so", then NoClassDefFoundError
    # oneos/semcompat/Sem). One UI's lists, cut to the libraries bound here.
    samcam_libs > "$STAGE/samcam_libs.txt"
    rm -f "$SAMCAM_SRC"/public.libraries-*.txt
    for f in /system/etc/public.libraries-*.txt; do
        [ -f "$f" ] || continue
        awk 'NR == FNR { if (NF) have[$1] = 1; next } { l = $1; sub(/#.*/, "", l) } l != "" && (l in have) { print l }' \
            "$STAGE/samcam_libs.txt" "$f" > "$SAMCAM_SRC/${f##*/}" || return 1
        [ -s "$SAMCAM_SRC/${f##*/}" ] || rm -f "$SAMCAM_SRC/${f##*/}"
    done
    rm -f "$STAGE/samcam_libs.txt"
    chmod 755 "$SAMCAM_SRC"; chmod 644 "$SAMCAM_SRC"/*
    if [ ! -f "$SAMCAM_SRC/.selinux" ] ||
       [ "$(cat "$SAMCAM_SRC/.selinux" 2>/dev/null)" != "$(cat "$SAMCAM_SRC/.from_tar" 2>/dev/null)" ]; then
        if $BB chcon -R u:object_r:system_file:s0 "$SAMCAM_SRC" 2>/dev/null; then
            $BB chcon u:object_r:system_lib_file:s0 "$SAMCAM_SRC"/*.so 2>/dev/null || true
            if [ -s "$SAMCAM_SRC/.from_tar" ]; then
                cat "$SAMCAM_SRC/.from_tar" > "$SAMCAM_SRC/.selinux"
            else
                rm -f "$SAMCAM_SRC/.selinux"
            fi
        else
            rm -f "$SAMCAM_SRC/.selinux"
            echo "Samsung Camera: SELinux labels not applied; retrying next start"
        fi
    fi
    samcam_files > "$SAMCAM_LIST"
    [ -s "$SAMCAM_LIST" ] || return 1
    while read -r k t s; do
        [ -e "$s" ] || { echo "Samsung Camera: $s missing"; return 1; }
    done < "$SAMCAM_LIST" || return 1
    SKIP=$( { awk '$2 == "system" { print $1 }' "$SAMCAM_SRC/libs.txt"; for lib in $SAMCAM_JNI; do echo "$lib"; done; } | sort -u | while read -r lib; do [ -e "/system/lib64/$lib" ] || printf ' %s' "$lib"; done)
    [ -z "$SKIP" ] || echo "Samsung Camera: One UI here has no$SKIP (left out; this phone's camera does not use them)"
    echo "Samsung Camera: prepared $(date +%T)"
    return 0
}
# Empty mount points of kind $2 in the overlay layer $1, before it is mounted.
samcam_mountpoints() {
    echo "Samsung Camera: mount points $(date +%T)"
    [ -s "$SAMCAM_LIST" ] || samcam_files > "$SAMCAM_LIST"
    [ -s "$SAMCAM_LIST" ] || return 1
    mp_base=$1 mp_kind=$2
    # Collect every parent directory and make them in one mkdir: 124 separate
    # mkdir processes cost 5 s on the S25 Ultra. Files are created below, after
    # their parents exist.
    set --
    while read -r k t s; do
        [ "$k" = "$mp_kind" ] || continue
        if [ -d "$s" ]; then
            set -- "$@" "$mp_base/$t"
        else
            case $t in
                */*) set -- "$@" "$mp_base/${t%/*}" ;;
                *)   set -- "$@" "$mp_base" ;;
            esac
        fi
    done < "$SAMCAM_LIST" || return 1
    [ $# -eq 0 ] || $BB mkdir -p "$@" || return 1
    while read -r k t s; do
        [ "$k" = "$mp_kind" ] || continue
        [ -d "$s" ] || : > "$mp_base/$t" || return 1
    done < "$SAMCAM_LIST" || return 1
    find "$mp_base" -type d -exec chmod 755 {} + 2>/dev/null
    $BB chcon -R u:object_r:system_file:s0 "$mp_base" 2>/dev/null || true
    [ -d "$mp_base/lib64" ] && $BB chcon -R u:object_r:system_lib_file:s0 "$mp_base/lib64" 2>/dev/null
    echo "Samsung Camera: mount points done $(date +%T)"
    return 0
}
# Bind every source of kind $1 onto its mount point under $2.
samcam_bind() {
    local n p k t s
    [ -s "$SAMCAM_LIST" ] || samcam_files > "$SAMCAM_LIST"
    [ -s "$SAMCAM_LIST" ] || return 1
    n=$(awk -v k="$1" '$1 == k' "$SAMCAM_LIST" | wc -l | tr -d ' ')
    if [ "$n" -gt 0 ]; then
        p=$($BB nproc 2>/dev/null || nproc 2>/dev/null || echo 2)
        case "$p" in ''|*[!0-9]*) p=2 ;; esac
        [ "$p" -gt 8 ] && p=8
        [ "$p" -lt 2 ] && p=2
        # No target in the list lies inside another one (files, and the two
        # folders cameradata and saiv), so the order does not matter. Not every
        # root manager's busybox has xargs -P: asked first, and without it the
        # files are bound one after the other as before.
        if echo x x | "$BB" xargs -P 2 -n 2 "$SAMCAM_SH" -c 'exit 0' sh 2>/dev/null; then
            echo "Samsung Camera: binding $n onto $2 with $p workers $(date +%T)"
            awk -v k="$1" '$1 == k { print $2, $3 }' "$SAMCAM_LIST" |
                MP="$2" BB="$BB" "$BB" xargs -P "$p" -n 2 "$SAMCAM_SH" -c '
                    t="$1"; s="$2"
                    [ -e "$MP/$t" ] || { echo "Samsung Camera: no mount point $MP/$t" >&2; exit 1; }
                    "$BB" mount --bind "$s" "$MP/$t" || exit 1
                    "$BB" mount --make-rslave "$MP/$t" 2>/dev/null || true
                ' sh || return 1
        else
            echo "Samsung Camera: binding $n onto $2 one by one (this busybox has no parallel xargs) $(date +%T)"
            while read -r k t s; do
                [ "$k" = "$1" ] || continue
                [ -e "$2/$t" ] || { echo "Samsung Camera: no mount point $2/$t"; return 1; }
                $BB mount --bind "$s" "$2/$t" || return 1
                $BB mount --make-rslave "$2/$t" 2>/dev/null || true
            done < "$SAMCAM_LIST"
        fi
    fi
    echo "Samsung Camera in the guest: $n files and folders bound onto $2 $(date +%T)"
    return 0
}
# Add the missing guest su mount point to an overlay before its read-only
# system view is mounted. Modern guest images need not ship /system/xbin.
guest_root_mountpoint() {
    [ ! -f "$STAGE/data/oneos_root/enabled" ] || [ -d "$ROOTFS/system/xbin" ] || mkdir -p "$1/xbin"
}
if [ -d "$SAMCAM_SRC" ] && [ $SAMCAM_IMAGE = 0 ]; then
    echo "Samsung Camera in the guest: off (this system's set has no samcam.tar; samcam_build is another system's)"
elif [ -d "$SAMCAM_SRC" ] && [ "${ONEOS_GUEST_SAMSUNG_CAMERA:-1}" = 1 ]; then
    if [ ! -d "$GUEST_SYSTEM_EXT" ]; then echo "Samsung Camera in the guest: off (the guest has no system_ext)"
    elif [ -L "$SAMCAM_SRC" ]; then echo "ERROR: $SAMCAM_SRC is a symlink; not starting the guest"; exit 3
    elif mount | grep -q " $ROOTFS/system type overlay"; then
        echo "Samsung Camera in the guest: off (an overlay on $ROOTFS/system is already there)"
    elif samcam_prepare; then
        # The guest's /system: a read-only overlay whose top layer (a small
        # tmpfs) holds only the mount points. Nothing is mounted under
        # $ROOTFS/system yet, so the jar and library binds further down land on
        # top of it as usual.
        SOV="$STAGE/system_ov"
        mkdir -p "$SOV"
        mount | grep -q " $SOV " || $BB mount -t tmpfs -o size=1m,mode=755 tmpfs "$SOV"
        rm -rf "$SOV/up" && mkdir -p "$SOV/up"
        mkdir -p "$SOV/up/etc/permissions" &&
            printf '%s\n' '<?xml version="1.0" encoding="utf-8"?>' '<permissions>' '    <feature name="android.hardware.fingerprint" />' '</permissions>' > "$SOV/up/etc/permissions/android.hardware.fingerprint.xml" &&
            printf '%s\n' '<?xml version="1.0" encoding="utf-8"?>' '<permissions>' '    <feature name="android.hardware.biometrics.face" />' '</permissions>' > "$SOV/up/etc/permissions/android.hardware.biometrics.face.xml" &&
            chmod 755 "$SOV/up/etc" "$SOV/up/etc/permissions" &&
            chmod 644 "$SOV/up/etc/permissions/android.hardware.fingerprint.xml" "$SOV/up/etc/permissions/android.hardware.biometrics.face.xml" &&
            $BB chcon -R u:object_r:system_file:s0 "$SOV/up/etc" 2>/dev/null || true
        echo "Samsung Camera: overlay $(date +%T)"
        if samcam_mountpoints "$SOV/up" sys && guest_root_mountpoint "$SOV/up" &&
           $BB mount -t overlay overlay -o "ro,lowerdir=$SOV/up:$ROOTFS/system" "$ROOTFS/system"; then
            echo "Samsung Camera: overlay up $(date +%T)"
            if samcam_bind sys "$ROOTFS/system"; then SAMCAM=1; else
                echo "Samsung Camera in the guest: off (bind-mount onto $ROOTFS/system failed)"
                awk -v r="$ROOTFS/system/" 'index($2, r) == 1 {print $2}' /proc/mounts | sort -r | while read -r m; do $BB umount -l "$m"; done
                $BB umount -l "$ROOTFS/system" 2>/dev/null || true
            fi
        else
            echo "Samsung Camera in the guest: off (overlay on $ROOTFS/system refused)"
        fi
    else echo "Samsung Camera in the guest: off (staged files or One UI's camera files missing)"
    fi
elif [ -d "$SAMCAM_SRC" ]; then
    echo "Samsung Camera in the guest: left out (ONEOS_GUEST_SAMSUNG_CAMERA=0)"
fi
# Without the camera's system overlay, add only the missing directory in a
# private read-only layer before later system submounts are installed.
if [ -f "$STAGE/data/oneos_root/enabled" ] && [ ! -d "$ROOTFS/system/xbin" ]; then
    GRO="$STAGE/guest_root_ov"
    [ ! -L "$GRO" ] || { echo 'ERROR: guest root overlay is a symlink'; exit 3; }
    mkdir -p "$GRO"
    $BB mount -t tmpfs -o size=1m,mode=755 tmpfs "$GRO" || exit 3
    $BB mount --make-private "$GRO" || exit 3
    mkdir -p "$GRO/up"
    guest_root_mountpoint "$GRO/up" || exit 3
    $BB chcon -R u:object_r:system_file:s0 "$GRO/up" 2>/dev/null || true
    if $BB mount -t overlay overlay -o "ro,lowerdir=$GRO/up:$ROOTFS/system" "$ROOTFS/system"; then
        echo 'Guest root: missing system/xbin supplied by a private read-only overlay'
    else
        # The android12-5.10 kernels (S22 series, S23 FE, A25, A33, A53) refuse overlayfs here
        # as on system_ext ("Operation not supported on transport endpoint"): with guest root on,
        # every switch of the A33 0.4.72 f8cc2067 ended at prepare. As for system_ext (0.4.70):
        # the top level of the image /system copied on this tmpfs (folders, empty files, links)
        # plus xbin, and each entry bound from the image. Nothing is mounted under it yet.
        GF="$GRO/farm"; GOR="$GRO/orig"; fok=1; fn=0
        rm -rf "$GF" && mkdir -p "$GF/xbin" "$GOR" || fok=0
        for e in "$ROOTFS/system"/* "$ROOTFS/system"/.[!.]*; do
            [ $fok = 1 ] || break
            [ -e "$e" ] || [ -L "$e" ] || continue
            n=${e##*/}
            if [ -L "$e" ]; then cp -P "$e" "$GF/$n" || fok=0
            elif [ -d "$e" ]; then mkdir -p "$GF/$n" || fok=0
            else : > "$GF/$n" || fok=0; fi
        done
        if [ $fok = 1 ]; then
            chmod 755 "$GF" "$GF/xbin"
            $BB chcon -R u:object_r:system_file:s0 "$GF" 2>/dev/null || true
            if $BB mount --bind "$ROOTFS/system" "$GOR" && $BB mount --bind "$GF" "$ROOTFS/system"; then
                for e in "$GOR"/* "$GOR"/.[!.]*; do
                    [ -e "$e" ] && [ ! -L "$e" ] || continue
                    if $BB mount --bind "$e" "$ROOTFS/system/${e##*/}"; then fn=$((fn + 1)); else fok=0; break; fi
                done
            else
                fok=0
            fi
        fi
        if [ $fok = 1 ] && [ -d "$ROOTFS/system/xbin" ]; then
            echo "Guest root: no overlayfs on this kernel; missing system/xbin supplied by a copy of the system top level ($fn entries of the image bound into it)"
        else
            awk -v r="$ROOTFS/system/" 'index($2, r) == 1 {print $2}' /proc/mounts | sort -r | while read -r m; do $BB umount -l "$m"; done
            grep -q " $ROOTFS/system tmpfs " /proc/mounts && $BB umount -l "$ROOTFS/system"
            $BB umount -l "$GOR" 2>/dev/null
            echo 'ERROR: guest root needs system/xbin, and neither an overlay nor a bound copy of the system top level worked'
            exit 3
        fi
    fi
    [ -d "$ROOTFS/system/xbin" ] || { echo 'ERROR: guest su mount point missing after overlay'; exit 3; }
fi
# The camera's working folder /data/sec/camera, which One UI's init makes
# (vendor_secdir, the camera's own uid): the camera cannot make it, "AccessDenied
# /data/sec", and its post-processing lost every picture (run 19). In the
# guest's own /data (the stage), for the guest camera's uid once it has one.
# A stage where the camera never ran has no app data folder yet, so no uid here:
# guest_start.sh makes the folder once the guest's package manager has made the
# app's (data/oneos_samcam; 0.4.58 report f794c15d, Galaxy S25+: "can't create
# secureDirectory", no photo in the gallery).
rm -f "$STAGE/data/oneos_samcam"
[ $SAMCAM = 1 ] && touch "$STAGE/data/oneos_samcam"
if [ $SAMCAM = 1 ]; then
    CUID=""
    for CAMDATA in "$STAGE/data/user/0/com.sec.android.app.camera" "$STAGE/data/user_de/0/com.sec.android.app.camera" "$STAGE/data/data/com.sec.android.app.camera"; do
        [ -d "$CAMDATA" ] && [ ! -L "$CAMDATA" ] && { CUID=$(stat -c %u "$CAMDATA" 2>/dev/null); break; }
    done
    if [ -n "$CUID" ] && [ "$CUID" -ge 10000 ] && [ ! -L "$STAGE/data/sec" ] && [ ! -L "$STAGE/data/sec/camera" ]; then
        mkdir -p "$STAGE/data/sec/camera" && chown 0:0 "$STAGE/data/sec" && chmod 771 "$STAGE/data/sec" &&
            chown "$CUID:$CUID" "$STAGE/data/sec/camera" && chmod 2770 "$STAGE/data/sec/camera" &&
            $BB chcon -R u:object_r:app_data_file:s0 "$STAGE/data/sec" 2>/dev/null
        echo "Samsung Camera in the guest: data/sec/camera for uid $CUID"
    fi
fi
# Nothing OS: the apps under system/noth (Essential Space, Essential Recorder,
# the ringtone generator, Rakuten Aura) are in product/overlayfs_origin/
# system/noth, which a Nothing phone's init lays over /system/noth at boot; in
# the image system/noth/priv-app/<app> holds only an empty "<app>Mkdir"
# folder, so without init the apps were missing (run 15: no ringtones at all).
# The same read-only overlay here, after the camera's overlay on /system (a
# mount under it would be hidden by that one). ONEOS_GUEST_NOTH_APPS=0 leaves it.
NOTH_UP="$GUEST_PRODUCT/overlayfs_origin/system/noth"
if [ -d "$NOTH_UP" ] && [ -d "$ROOTFS/system/noth" ] && [ "${ONEOS_GUEST_NOTH_APPS:-1}" = 1 ]; then
    if mount | grep -q " $ROOTFS/system/noth type overlay"; then
        echo "Nothing apps: overlay on system/noth already there"
    elif $BB mount -t overlay overlay -o "ro,lowerdir=$NOTH_UP:$ROOTFS/system/noth" "$ROOTFS/system/noth"; then
        echo "Nothing apps: product/overlayfs_origin/system/noth over system/noth ($(ls "$NOTH_UP/priv-app" 2>/dev/null | tr '\n' ' '))"
    else
        echo "!!! WARNING: Nothing apps: the overlay on system/noth was refused"
    fi
    # The ringtone generator without its haptic library's Nothing Phone (3)
    # check (switcher/patches/nothing_ringtone_device.py).
    NTRG="$ROOTFS/system/noth/priv-app/NothingGenerateRingtoneService/NothingGenerateRingtoneService.apk"
    if [ -f "$STAGE/NothingGenerateRingtoneService_patched.apk" ] && [ -f "$NTRG" ] && [ ! -L "$NTRG" ] &&
       [ "${ONEOS_GUEST_NT_RINGTONES:-1}" = 1 ]; then
        chmod 644 "$STAGE/NothingGenerateRingtoneService_patched.apk"
        $BB chcon u:object_r:system_file:s0 "$STAGE/NothingGenerateRingtoneService_patched.apk" 2>/dev/null || true
        $BB mount --bind "$STAGE/NothingGenerateRingtoneService_patched.apk" "$NTRG" &&
            $BB mount -o remount,bind,ro "$STAGE/NothingGenerateRingtoneService_patched.apk" "$NTRG" 2>/dev/null
        if [ "$(stat -c %d:%i "$NTRG" 2>/dev/null)" = "$(stat -c %d:%i "$STAGE/NothingGenerateRingtoneService_patched.apk")" ]; then
            echo "Nothing apps: NothingGenerateRingtoneService_patched.apk bound (haptics without a Nothing device name)"
        else
            echo "!!! WARNING: Nothing apps: the patched ringtone generator did not bind; the image's stays"
        fi
    fi
fi
# Nothing OS's ringtones: the generator (above) composes them from the kits in
# Nothing's /vendor/etc/customringtone (.aif parts, from Nothing's own vendor
# image; nothing_customringtone.tar in the set). The guest's /vendor is One
# UI's, so a read-only overlay on the guest's vendor/etc adds that folder; One
# UI's own /vendor is not touched (the guest's vendor is a slave bind).
# ONEOS_GUEST_NT_RINGTONES=0 leaves it out.
if [ -f "$STAGE/nothing_customringtone.tar" ] && [ "${ONEOS_GUEST_NT_RINGTONES:-1}" = 1 ] && [ -d "$ROOTFS/vendor/etc" ]; then
    NRV="$STAGE/nt_vendor_etc"
    if mount | grep -q " $ROOTFS/vendor/etc type overlay"; then
        echo "Nothing ringtones: overlay on vendor/etc already there"
    else
        mkdir -p "$NRV" && { mount | grep -q " $NRV " || $BB mount -t tmpfs -o size=8m,mode=755 tmpfs "$NRV"; } &&
            $BB mount --make-private "$NRV" 2>/dev/null
        rm -rf "$NRV/up" && mkdir -p "$NRV/up" &&
            $BB tar -xf "$STAGE/nothing_customringtone.tar" -C "$NRV/up" &&
            chown -R 0:0 "$NRV/up" && find "$NRV/up" -type d -exec chmod 755 {} + && find "$NRV/up" -type f -exec chmod 644 {} +
        $BB chcon -R u:object_r:vendor_configs_file:s0 "$NRV/up" 2>/dev/null || true
        if [ -d "$NRV/up/customringtone" ] &&
           $BB mount -t overlay overlay -o "ro,lowerdir=$NRV/up:$ROOTFS/vendor/etc" "$ROOTFS/vendor/etc"; then
            echo "Nothing ringtones: vendor/etc/customringtone ($(ls "$NRV/up/customringtone" | tr '\n' ' '))"
        else
            echo "!!! WARNING: Nothing ringtones: the overlay on vendor/etc was refused"
        fi
    fi
fi
# Nothing OS's own sounds: the ringtones of "Nothing Signals" (01_crossing ..
# 10_clwb), notifications, alarms and the UI sounds (camera click, ...) ship in
# Nothing's vendor image under product/media/audio, which its init lays over
# /product/media; the image's own product/media/audio holds four empty
# sounds.xml lists, so every sound list in the guest was empty (run 18: "Nothing
# Signals, 10 sounds", none shown; the defaults 01_crossing.ogg, 01_oi!.ogg and
# 01_trad.ogg missing). nothing_product_media.tar (from Nothing's vendor image;
# its haptic patterns, vendor/etc/richtapresources, are in the ringtone kit tar)
# goes over the guest's product/media read-only, where the media scanner reads
# built-in sounds. ONEOS_GUEST_NT_RINGTONES=0 leaves it out.
if [ -f "$STAGE/nothing_product_media.tar" ] && [ "${ONEOS_GUEST_NT_RINGTONES:-1}" = 1 ] && [ -d "$GUEST_PRODUCT/media" ] && [ ! -L "$GUEST_PRODUCT/media" ]; then
    NPM="$STAGE/nt_product_media"
    if mount | grep -q " $(readlink -f "$GUEST_PRODUCT/media") type overlay"; then
        echo "Nothing sounds: overlay on product/media already there"
    else
        mkdir -p "$NPM" && { mount | grep -q " $NPM " || $BB mount -t tmpfs -o size=16m,mode=755 tmpfs "$NPM"; } &&
            $BB mount --make-private "$NPM" 2>/dev/null
        rm -rf "$NPM/up" && mkdir -p "$NPM/up" &&
            $BB tar -xf "$STAGE/nothing_product_media.tar" -C "$NPM/up" &&
            chown -R 0:0 "$NPM/up" && find "$NPM/up" -type d -exec chmod 755 {} + && find "$NPM/up" -type f -exec chmod 644 {} +
        $BB chcon -R u:object_r:system_file:s0 "$NPM/up" 2>/dev/null || true
        if [ -d "$NPM/up/media/audio" ] &&
           $BB mount -t overlay overlay -o "ro,lowerdir=$NPM/up/media:$GUEST_PRODUCT/media" "$GUEST_PRODUCT/media"; then
            echo "Nothing sounds: product/media/audio ($(for d in "$NPM/up/media/audio"/*; do printf '%s %s, ' "$(ls "$d" | grep -c '\.ogg$')" "${d##*/}"; done))"
        else
            echo "!!! WARNING: Nothing sounds: the overlay on product/media was refused"
        fi
    fi
fi
# ColorOS's system_ext has no apex dir and the image is mounted read-only, so
# put a thin overlayfs on it to create the mount point. Its upper layer is a
# small tmpfs: overlayfs refuses an upper dir on the encrypted f2fs /data
# (EINVAL). return_to_oneui.sh unmounts $STAGE/system_ext_ov.
# With the signal poll (INJ=1) the same tmpfs is instead the top one of two
# lower layers (apex mount point and framework/oneos-telephony.jar), with no
# upper dir: a read-only overlay, which InjectedComponents requires (statvfs
# ST_RDONLY; on the rw form the jar is dropped from "validated paths").
# An overlay left by an earlier prepare is never unmounted here (umount
# propagation); the signal poll then goes ahead only if it is that read-only one
# with the same jar (checked below).
# With the Samsung IMS set (SEC_IMS=1) the staged tree is bind-mounted onto the
# guest's system_ext after the overlay is up (sec_ims_bind), not added as a second
# overlay lower layer, which some kernels reject (EINVAL). An overlay left by an
# earlier prepare cannot take it.
# The vendor NDK version One UI's vendor asks for (0.4.43). A guest framework manifest
# that does not list it fails VintfObject.verifyBuildAtBoot ("Vndk version 33 is not
# supported. Supported versions in framework manifest are: [ 34]"), and the guest shows
# "There's an internal problem with your device" at every boot (HyperOS on the S23s,
# reports 4cd02405, c70e1b54, 2d486da1; a Pixel GSI too). Empty when nothing is missing.
VNDK_NEED=$(sed -n '/<vendor-ndk>/,/<\/vendor-ndk>/s:.*<version>\([^<]*\)</version>.*:\1:p' /vendor/etc/vintf/compatibility_matrix.xml 2>/dev/null | head -n 1)
case "$VNDK_NEED" in *[!0-9]*) VNDK_NEED="" ;; esac
if [ -n "$VNDK_NEED" ] && cat "$ROOTFS/system/etc/vintf/manifest.xml" "$ROOTFS"/system/etc/vintf/manifest/*.xml \
        "$GUEST_SYSTEM_EXT"/etc/vintf/manifest.xml "$GUEST_SYSTEM_EXT"/etc/vintf/manifest/*.xml \
        "$GUEST_PRODUCT"/etc/vintf/manifest.xml "$GUEST_PRODUCT"/etc/vintf/manifest/*.xml 2>/dev/null |
        tr -d ' \t\n\r' | grep -q "<vendor-ndk><version>$VNDK_NEED</version>"; then
    VNDK_NEED=""
fi
# The fragment in an overlay layer ($1), merged with the framework manifest by libvintf.
vndk_fragment() {
    [ -n "$VNDK_NEED" ] || return 0
    mkdir -p "$1/etc/vintf/manifest" &&
        printf '<manifest version="1.0" type="framework">\n    <vendor-ndk>\n        <version>%s</version>\n    </vendor-ndk>\n</manifest>\n' "$VNDK_NEED" \
            > "$1/etc/vintf/manifest/oneos-vendor-ndk.xml" || return 1
    chmod 755 "$1/etc" "$1/etc/vintf" "$1/etc/vintf/manifest"; chmod 644 "$1/etc/vintf/manifest/oneos-vendor-ndk.xml"
    $BB chcon -R u:object_r:system_file:s0 "$1/etc/vintf" 2>/dev/null || true
    echo "VINTF: vendor-ndk $VNDK_NEED added to the guest's framework manifest (One UI's vendor matrix asks for it)"
    VNDK_NEED=""
}
SECIMS_BOUND=0
VIVO_SE=""
if { [ -d /system_ext/apex ] && [ -d "$GUEST_SYSTEM_EXT" ]; } || [ $INJ = 1 ] || [ $HWSM = 1 ] || [ $SEC_IMS = 1 ] || [ $SAMCAM = 1 ]; then
    if mount | grep -q " $GUEST_SYSTEM_EXT type overlay"; then
        echo "Overlay on $GUEST_SYSTEM_EXT already there (an earlier prepare), left as it is"
        [ $SEC_IMS = 1 ] && { SEC_IMS=0; rm -f "$STAGE/data/oneos_sec_ims"; echo "Samsung IMS in the guest: off (that overlay has no secims layer)"; }
        [ $SAMCAM = 1 ] && { SAMCAM=0; echo "Samsung Camera in the guest: off (that overlay has no mount points for it)"; }
    elif [ ! -d "$GUEST_SYSTEM_EXT/apex" ] || [ $INJ = 1 ] || [ $HWSM = 1 ] || [ $SEC_IMS = 1 ] || [ $SAMCAM = 1 ]; then
        OV="$STAGE/system_ext_ov"
        mkdir -p "$OV"
        mount | grep -q " $OV " || $BB mount -t tmpfs -o size=1m,mode=755 tmpfs "$OV"
        mkdir -p "$OV/up/apex"
        # vivo's package manager never scans /oem (F8U run 13, OriginOS CN: no package
        # cache entry for anything there, so the fold cutout overlay and the OneOS app
        # were missing and the status bar ignored the cover's camera hole). Their
        # folders go in system_ext instead: empty mount points here, bound in the /oem
        # step. With no partition-order config, system_ext overlays rank above vendor's
        # and product's (run 13: vendor 5, product 11), as /oem's did elsewhere.
        # ONEOS_GUEST_VIVO_SYSEXT=0 leaves them in /oem only.
        if [ -f "$ROOTFS/system/framework/vivo-services.jar" ] && [ "${ONEOS_GUEST_VIVO_SYSEXT:-1}" = 1 ]; then
            for n in app/OneOSGuest:OneOSGuest.apk overlay/OneOSFoldCutout:OneOSFoldCutout.apk; do
                d=${n%%:*}; f=${n#*:}
                [ -f "$STAGE/$f" ] && [ ! -e "$GUEST_SYSTEM_EXT/$d" ] || continue
                mkdir -p "$OV/up/$d" && VIVO_SE="$VIVO_SE $d"
            done
            for d in app overlay; do
                [ -d "$OV/up/$d" ] || continue
                find "$OV/up/$d" -type d -exec chmod 755 {} + 2>/dev/null
                $BB chcon -R u:object_r:system_file:s0 "$OV/up/$d" 2>/dev/null || true
            done
        fi
        # Features my_product declares (0.4.38): the container does not load
        # /my_product/etc/permissions, so the Find N6 global build had no Circle to
        # Search (ContextualManagerServiceExtImpl: mIsSupportCircleToSearch false; no
        # option under Gestures) and no large-screen mode (three-app split screen).
        # Only these software features, and only those the image itself declares;
        # its hardware ones (sensors, the curved display, eSIM) stay out.
        MPF=""
        for x in com.google.android.feature.CONTEXTUAL_SEARCH com.google.android.feature.CONTEXTUAL_SEARCH_LIVE_TRANSLATE \
                 com.google.android.feature.GEMINI_POWER_MENU com.google.lens.feature.CAMERA_INTEGRATION \
                 com.google.lens.feature.IMAGE_INTEGRATION oplus.feature.largescreen oplus.feature.largescreen.land; do
            case "$x" in oplus.feature.largescreen*) [ "${ONEOS_GUEST_FORM:-fold}" = fold ] || continue ;; esac
            grep -l -s "<feature name=\"$x\"" "$ROOTFS"/my_product/etc/permissions/*.xml >/dev/null || continue
            MPF="$MPF $x"
        done
        if [ -n "$MPF" ]; then
            mkdir -p "$OV/up/etc/permissions" &&
                { echo '<?xml version="1.0" encoding="utf-8"?>'; echo '<permissions>'
                  for x in $MPF; do echo "    <feature name=\"$x\" />"; done
                  echo '</permissions>'; } > "$OV/up/etc/permissions/oneos-my-product-features.xml" &&
                chmod 755 "$OV/up/etc" "$OV/up/etc/permissions" && chmod 644 "$OV/up/etc/permissions/oneos-my-product-features.xml" &&
                $BB chcon -R u:object_r:system_file:s0 "$OV/up/etc" 2>/dev/null
            echo "Features from my_product:$MPF"
        fi
        vndk_fragment "$OV/up" || echo "VINTF: could not write the vendor-ndk fragment on the overlay"
        if [ $SAMCAM = 1 ] && ! samcam_mountpoints "$OV/up" sysext; then
            SAMCAM=0; echo "Samsung Camera in the guest: off (no room for its mount points on the overlay's tmpfs)"
        fi
        if [ $HWSM = 1 ]; then
            mkdir -p "$OV/up/bin" && : > "$OV/up/bin/hwservicemanager" &&
                chmod 755 "$OV/up/bin" "$OV/up/bin/hwservicemanager" || HWSM=0
            $BB chcon u:object_r:system_file:s0 "$OV/up/bin" 2>/dev/null || true
            $BB chcon u:object_r:hwservicemanager_exec:s0 "$OV/up/bin/hwservicemanager" 2>/dev/null || true
        fi
        if [ $INJ = 1 ]; then
            mkdir -p "$OV/up/framework" && cp "$STAGE/oneos-telephony.jar" "$OV/up/framework/" &&
                chmod 755 "$OV/up" "$OV/up/framework" && chmod 644 "$OV/up/framework/oneos-telephony.jar"
            # A stage copy, labelled like the image's own framework files.
            $BB chcon u:object_r:system_file:s0 "$OV/up/framework" "$OV/up/framework/oneos-telephony.jar" 2>/dev/null || true
            if [ $SEC_IMS = 1 ] && ! secims_mountpoints "$OV/up"; then
                SEC_IMS=0; rm -f "$STAGE/data/oneos_sec_ims"
                echo "Samsung IMS in the guest: off (no room for its mount points on the overlay's tmpfs)"
            fi
            if $BB mount -t overlay overlay -o "ro,lowerdir=$OV/up:$GUEST_SYSTEM_EXT" "$GUEST_SYSTEM_EXT"; then
                echo "Read-only overlay on $GUEST_SYSTEM_EXT (apex mount point, framework/oneos-telephony.jar)"
                if [ $SEC_IMS = 1 ]; then
                    if sec_ims_bind; then SECIMS_BOUND=1; else
                        SEC_IMS=0; rm -f "$STAGE/data/oneos_sec_ims"
                        echo "Samsung IMS in the guest: off (bind-mount onto the read-only $GUEST_SYSTEM_EXT failed)"
                    fi
                fi
            else
                # The apex mount point matters more: today's rw form then.
                INJ=0
                rm -rf "$OV/up/framework"
                echo "Signal poll: off (read-only overlay on $GUEST_SYSTEM_EXT refused)"
            fi
        fi
        if [ $INJ = 0 ] && { [ ! -d "$GUEST_SYSTEM_EXT/apex" ] || [ $HWSM = 1 ] || [ $SEC_IMS = 1 ] || [ $SAMCAM = 1 ]; }; then
            mkdir -p "$OV/work"
            if $BB mount -t overlay overlay \
                -o "lowerdir=$GUEST_SYSTEM_EXT,upperdir=$OV/up,workdir=$OV/work" \
                "$GUEST_SYSTEM_EXT"; then
                echo "Overlay on $GUEST_SYSTEM_EXT for the apex mount point$([ $HWSM = 1 ] && echo ' and bin/hwservicemanager')"
                if [ $SEC_IMS = 1 ]; then
                    if sec_ims_bind; then SECIMS_BOUND=1; else
                        SEC_IMS=0; rm -f "$STAGE/data/oneos_sec_ims"
                        echo "Samsung IMS in the guest: off (bind-mount onto $GUEST_SYSTEM_EXT failed)"
                    fi
                fi
            # The S23 FE's kernel refused the read-write form (0.4.67 3513fb67, OxygenOS 16: "Operation not
            # supported on transport endpoint", then no apex mount point for PackageManagerService). The
            # read-only form above (the stage's tmpfs as the top lower layer, no upper) gives the same mount
            # points, as it does wherever the telephony jar is injected.
            elif { echo "Read-write overlay on $GUEST_SYSTEM_EXT refused; kernel: $(dmesg 2>/dev/null | grep -i overlayfs | tail -n 2 | tr '\n' ' ')"
                   $BB mount -t overlay overlay -o "ro,lowerdir=$OV/up:$GUEST_SYSTEM_EXT" "$GUEST_SYSTEM_EXT"; }; then
                echo "Read-only overlay on $GUEST_SYSTEM_EXT for the apex mount point (the read-write form was refused)"
                if [ $SEC_IMS = 1 ]; then
                    if sec_ims_bind; then SECIMS_BOUND=1; else
                        SEC_IMS=0; rm -f "$STAGE/data/oneos_sec_ims"
                        echo "Samsung IMS in the guest: off (bind-mount onto the read-only $GUEST_SYSTEM_EXT failed)"
                    fi
                fi
            elif [ $SEC_IMS = 1 ]; then
                SEC_IMS=0; rm -f "$STAGE/data/oneos_sec_ims"
                echo "Samsung IMS in the guest: off (overlay on $GUEST_SYSTEM_EXT refused)"
            fi
        fi
        # The android12-5.10 kernels (the S22 series, S23 FE, A25, A33, A53 on One UI 8) refuse
        # both overlay forms here (0.4.68 S908B 0e1c3360, S711B be228999 9d30c86d, S908E 15cf8a3f:
        # "Operation not supported on transport endpoint" twice), and PackageManagerService then
        # died on One UI's system_ext APEXes ("Unable to parse: /system_ext/apex/com.android.vndk.
        # v31.apex"). Without overlayfs: system_ext's top level copied on the stage's tmpfs
        # (folders, empty files, links), each entry bound from the image, plus the apex mount
        # point. The overlay's other additions (bin/hwservicemanager, etc/permissions features,
        # Samsung IMS and camera mount points) are not in it; those are off as on a refusal.
        if [ ! -d "$GUEST_SYSTEM_EXT/apex" ] && [ -d /system_ext/apex ] && ! mount | grep -q " $GUEST_SYSTEM_EXT type overlay"; then
            FARM="$OV/farm"; FORIG="$OV/orig"; fok=1; fn=0
            rm -rf "$FARM" && mkdir -p "$FARM/apex" "$FORIG" || fok=0
            for e in "$GUEST_SYSTEM_EXT"/* "$GUEST_SYSTEM_EXT"/.[!.]*; do
                [ $fok = 1 ] || break
                [ -e "$e" ] || [ -L "$e" ] || continue
                n=${e##*/}
                if [ -L "$e" ]; then cp -P "$e" "$FARM/$n" || fok=0
                elif [ -d "$e" ]; then mkdir -p "$FARM/$n" || fok=0
                else : > "$FARM/$n" || fok=0; fi
            done
            if [ $fok = 1 ]; then
                chmod 755 "$FARM" "$FARM/apex"
                $BB chcon -R u:object_r:system_file:s0 "$FARM" 2>/dev/null || true
                if $BB mount --bind "$GUEST_SYSTEM_EXT" "$FORIG" && $BB mount --bind "$FARM" "$GUEST_SYSTEM_EXT"; then
                    for e in "$FORIG"/* "$FORIG"/.[!.]*; do
                        [ -e "$e" ] && [ ! -L "$e" ] || continue
                        if $BB mount --bind "$e" "$GUEST_SYSTEM_EXT/${e##*/}"; then fn=$((fn + 1)); else fok=0; break; fi
                    done
                else
                    fok=0
                fi
            fi
            if [ $fok = 1 ] && [ -d "$GUEST_SYSTEM_EXT/apex" ]; then
                echo "system_ext without overlayfs: $fn entries of the image bound into a copy of its top level, with the apex mount point"
            else
                awk -v r="$GUEST_SYSTEM_EXT/" 'index($2, r) == 1 {print $2}' /proc/mounts | sort -r | while read -r m; do $BB umount -l "$m"; done
                grep -q " $GUEST_SYSTEM_EXT tmpfs " /proc/mounts && $BB umount -l "$GUEST_SYSTEM_EXT"
                $BB umount -l "$FORIG" 2>/dev/null
                echo "!!! system_ext without overlayfs: the bound copy failed, left as the image has it"
            fi
        fi
        # The Samsung IMS set binds onto either overlay (the read-only one through the
        # mount points made in its layer); an earlier prepare's overlay has none.
        [ $SEC_IMS = 1 ] && [ $SECIMS_BOUND = 0 ] && { SEC_IMS=0; rm -f "$STAGE/data/oneos_sec_ims"; echo "Samsung IMS in the guest: off (no writable overlay to bind onto)"; }
        # Samsung Camera's mount points are in the overlay's own layer, so the
        # read-only form takes it as well.
        if [ $SAMCAM = 1 ]; then
            if mount | grep -q " $GUEST_SYSTEM_EXT type overlay" && samcam_bind sysext "$GUEST_SYSTEM_EXT"; then SAMCAM_BOUND=1; else
                SAMCAM=0; echo "Samsung Camera in the guest: off (bind-mount onto $GUEST_SYSTEM_EXT failed)"
            fi
        fi
        if [ $HWSM = 1 ]; then
            if [ -f "$GUEST_SYSTEM_EXT/bin/hwservicemanager" ]; then
                echo "HIDL: the guest sees system_ext/bin/hwservicemanager (an empty file; One UI's hwservicemanager $(pidof hwservicemanager) answers) for this phone's HIDL-only $HWSM_WHY"
            else
                echo "!!! HIDL: no system_ext/bin/hwservicemanager in the guest; it will not find this phone's HIDL-only $HWSM_WHY"
            fi
        fi
    fi
    # No overlay of ours on system_ext (or an earlier prepare's): the vendor-ndk version goes into
    # a bound copy of the system framework manifest instead.
    VM="$ROOTFS/system/etc/vintf/manifest.xml"
    if [ -n "$VNDK_NEED" ] && [ -f "$VM" ] && [ ! -L "$VM" ] && grep -q '</manifest>' "$VM"; then
        awk -v v="$VNDK_NEED" '/<\/manifest>/ && !d { print "    <vendor-ndk>"; print "        <version>" v "</version>"; print "    </vendor-ndk>"; d = 1 } { print }' \
            "$VM" > "$STAGE/oneos_vintf_manifest.xml" &&
            chmod 644 "$STAGE/oneos_vintf_manifest.xml" && $BB chcon u:object_r:system_file:s0 "$STAGE/oneos_vintf_manifest.xml" 2>/dev/null
        $BB mount --bind "$STAGE/oneos_vintf_manifest.xml" "$VM" &&
            echo "VINTF: vendor-ndk $VNDK_NEED added to a bound copy of the guest's system manifest (One UI's vendor matrix asks for it)"
        VNDK_NEED=""
    fi
    if [ -d /system_ext/apex ]; then
        if [ -d "$GUEST_SYSTEM_EXT/apex" ]; then
            mount | grep -q " $GUEST_SYSTEM_EXT/apex " || $BB mount --bind /system_ext/apex "$GUEST_SYSTEM_EXT/apex"
            $BB mount --make-rslave "$GUEST_SYSTEM_EXT/apex" 2>/dev/null || true
            echo "Bound host /system_ext/apex -> $GUEST_SYSTEM_EXT/apex"
        else
            echo "!!! WARNING: no $GUEST_SYSTEM_EXT/apex mount point; PackageManagerService will fail on host system_ext apexes"
        fi
    fi
fi
if [ $INJ = 1 ]; then
    if ! grep -q " $GUEST_SYSTEM_EXT overlay ro[, ]" /proc/mounts; then
        INJ=0
        echo "Signal poll: off (no read-only overlay on $GUEST_SYSTEM_EXT, which the injection needs)"
    elif ! cmp -s "$GUEST_SYSTEM_EXT/framework/oneos-telephony.jar" "$STAGE/oneos-telephony.jar"; then
        INJ=0
        echo "Signal poll: off ($GUEST_SYSTEM_EXT/framework/oneos-telephony.jar missing or not the staged one)"
    fi
fi
# Display configs for the phone's two panels in a Pixel guest (run 49), in a
# read-only overlay on the guest's product/etc, made before anything is bound
# into product/etc (the seapp files below). Without a display_*.xml for these
# panels (One UI's vendor has Qualcomm reference files for other display ids)
# the Pixel framework maps its brightness linearly onto Samsung's composer
# float, which Samsung's composer maps linearly onto panel0-backlight
# 0..13510 (about 2650 nits at the top): adaptive brightness aimed at the wrong
# levels. And it had no proximity sensor: the phone's only
# android.sensor.proximity ("Palm Proximity Sensor", handle "_ear") lives in
# One UI's framework. Each file gives One UI's own nits -> float pairs (the
# table of patches/OneOSPanelBacklight.smali, from One UI's SurfaceFlinger
# logs; from 0.0026, the lowest level One UI uses, up to 520 nits, no high
# brightness mode yet) and names Samsung's IR proximity sensor
# (com.samsung.sensor.physical_proximity, wake-up; system_server passes its
# SSENSOR permission). DisplayDeviceConfig reads product/etc/displayconfig
# before vendor; display_port_147.xml is the inner panel, 148 the cover.
# The Z Fold8 Ultra gets both ports and the proximity sensor; every other
# phone (0.4.34) gets the curve for its own panel ports, an approximation of
# its panel that still beats the image's own phone's curve (below).
# ColorOS and Infinity-X (OPPO's framework) have their own brightness path
# (samsung_backlight_curve.py).
# ONEOS_GUEST_DISPLAY_CONFIG=0 leaves it out.
# ddc_xml wide: the same curve from the lowest float to 1.0, for a framework
# whose brightness range is wider than One UI's (HyperOS: 3.66255E-4 to 1.0;
# with the plain curve DisplayDeviceConfig threw "Min or max values are
# invalid" and system_server died at once, fifth HyperOS run). Samsung's
# composer maps the float linearly onto the panel's backlight, and the curve's
# own slope (0.196 = 520 nits, a quarter of the backlight about 660) puts 1.0
# at about 2600 nits, the panel's peak. DisplayDeviceConfig wants the curve's
# first float at or below the framework's config_screenBrightnessSettingMinimumFloat:
# vivo OriginOS's is 7.0E-5 ("raw min=3.66255E-4 ... backlight min=7.0E-5", second
# OriginOS run), so the wide curve starts at 1.0E-5 (0.05 nits), below every
# framework seen, with HyperOS's 3.66255E-4 point kept as it was.
# Every panel by its own scale (0.4.35): Samsung's composer float is One UI's
# brightness over its brightnessMaximum (dumpsys display: the panel's peak
# over about 500 nits; the backlight's max over it is 255 or 2550 on every
# probe), so the Z Fold8 Ultra's floats (brightnessMaximum 5.2980394) times
# 5.2980394 / this panel's give the same nits. Up to 0.4.34 every phone took
# the Fold's floats: a Z Fold5 or Flip5 (3.0) or an S23 (2.4) got half to two
# thirds of the nits each step asked for. $2 is the panel's brightnessMaximum
# (display_modes_host.log); outside 1.5..8 the Fold's own floats.
ddc_xml() {
    cat <<'DDCEOF'
<?xml version="1.0" encoding="utf-8"?>
<!-- OneOS (guest_prepare.sh): One UI's nits for Samsung's composer float on this panel, and Samsung's IR proximity sensor. -->
<displayConfiguration>
    <screenBrightnessMap>
DDCEOF
    awk -v wide="$1" -v m="${2:-}" 'BEGIN {
        ref = 5.2980394; k = 1
        if (m + 0 >= 1.5 && m + 0 <= 8) k = ref / m
        n = split("0.0026:2.21 0.00333:3.0 0.005015:5.0 0.00694:7.5 0.008891:10.4 0.012079:15.0 0.015279:20.0 0.021151:30.0 0.026566:40.0 0.03701:60.0 0.045723:80.0 0.054391:100.0 0.068653:135.0 0.082069:170.0 0.093062:200.0 0.110574:250.0 0.127287:300.0 0.158918:400.0 0.188764:500.0 0.196299:520.0", pt, " ")
        if (wide == "wide") printf "        <point><value>0.00001</value><nits>0.05</nits></point>\n        <point><value>0.000366255</value><nits>0.3</nits></point>\n"
        for (i = 1; i <= n; i++) {
            split(pt[i], v, ":"); f = v[1] * k
            if (f >= 1.0) break
            printf "        <point><value>%.6g</value><nits>%s</nits></point>\n", f, v[2]
        }
        # The top: the panel peak, 2600 nits on the Fold (490.75 per unit of brightnessMaximum).
        if (wide == "wide") printf "        <point><value>1.0</value><nits>%.1f</nits></point>\n", 2600.0 / k
    }'
    cat <<'DDCEOF'
    </screenBrightnessMap>
    <proxSensor>
        <type>com.samsung.sensor.physical_proximity</type>
    </proxSensor>
</displayConfiguration>
DDCEOF
}
PETC="$GUEST_PRODUCT/etc"
if [ -e "$ROOTFS/system/framework/oplus-services.jar" ] || [ -L "$ROOTFS/system/framework/oplus-services.jar" ]; then
    :
elif [ "${ONEOS_GUEST_DISPLAY_CONFIG:-1}" != 1 ]; then
    echo "Display config: the image's own (ONEOS_GUEST_DISPLAY_CONFIG=0)"
elif [ ! -d "$PETC" ] || [ -L "$PETC" ]; then
    echo "Display config: no product/etc folder in the image, left out"
elif mount | grep -q " $PETC type overlay"; then
    echo "Display config: overlay on product/etc already there (an earlier prepare), left as it is"
elif [ -e "$PETC/displayconfig/display_port_147.xml" ] || [ -e "$PETC/displayconfig/display_port_148.xml" ]; then
    echo "Display config: the image has its own display_port_147/148, left as it is"
else
    # An image with configs for its own panels only (HyperOS: display_id_<Xiaomi
    # panel>.xml) gets ours next to them in the merged folder; without a nits
    # mapping for the Fold's panels Xiaomi's brightness code ignored the slider
    # ("requesting nits when no mapping exists", 3 % brightness; 2026-10-25).
    # Always the wide curve. Up to 0.4.32 it was used only for an image that
    # ships its own product/etc/displayconfig, which says nothing about the
    # range its framework asks for: HyperOS happened to have both, Nothing OS
    # 5.0 has the wide range (0.035433073 = 4.5/127 to 1.0) and no folder, so
    # it got the plain curve and DisplayDeviceConfig threw the same
    # "Min or max values are invalid; raw min=0.0026; raw max=0.196299" as the
    # fifth HyperOS run -- system_server died on the android.display thread
    # before the first frame (first Nothing run, 2026-10-30).
    # Between 0.0026 and 0.196299 the curve is unchanged, so a framework whose
    # range sits inside One UI's reads exactly what it read before; the two
    # extra points only carry the same slope out to the ends of the float
    # range, which every Android brightness range is inside. There is no range
    # the plain curve covers and this one does not.
    DDC_RANGE=wide
    [ -e "$PETC/displayconfig" ] &&
        echo "Display config: the image's own product/etc/displayconfig ($(ls "$PETC/displayconfig" | tr '\n' ' ')) is kept; the Fold's two port files are added"
    DOV="$STAGE/product_etc_ov"
    mkdir -p "$DOV"
    if ! mount | grep -q " $DOV "; then
        $BB mount -t tmpfs -o size=256k,mode=755 tmpfs "$DOV" && $BB mount --make-private "$DOV" 2>/dev/null
    fi
    mkdir -p "$DOV/up/displayconfig"
    # Every other phone: the same One UI curve for the ports of its own built-in
    # panels, which the switch read from One UI's SurfaceFlinger
    # (display_modes_host.log), and no proximity entry (the sensor's name is the
    # Fold8 Ultra's). Samsung's composer maps the float onto the panel's
    # backlight linearly on every Galaxy, so an image's own curve (its phone's
    # panel) aims the slider and auto brightness at the wrong levels: Infinity-X
    # on the S25 Ultra took 0.28 for 98 nits and 0.0 for 1 nit (0.4.32/0.4.33
    # reports f0fffbb5, 9d0bf2e2, 3e9af08a), and HyperOS, with no mapping for the
    # panel at all, sent -1.0 from the slider and sat at 5 of 12750 (cfa53628).
    DDC_PORTS="147 148"
    DDC_PROX=1
    if [ "${ONEOS_GUEST_FORM:-fold}" != fold ] || [ "${ONEOS_PROFILE:-f8u}" != f8u ]; then
        DDC_PORTS=$(sed -n 's/^Display [0-9]* (HWC display [0-9]*): port=\([0-9]*\) .*/\1/p' "$STAGE/display_modes_host.log" 2>/dev/null | sort -u | tr '\n' ' ')
        DDC_PROX=0
    fi
    [ -n "$DDC_PORTS" ] || echo "Display config: no panel ports from One UI's SurfaceFlinger (display_modes_host.log), none written"
    DDC_MAX=""
    for port in $DDC_PORTS; do
        # One UI's brightnessMaximum for this panel (dumpsys display, captured
        # by the switch while One UI was up).
        m=$(grep 'DisplayDeviceInfo{' "$STAGE/display_modes_host.log" 2>/dev/null | grep -E "port=$port[},]" |
            sed -n 's/.*brightnessMaximum \([0-9.]*\).*/\1/p' | head -n 1)
        DDC_MAX="$DDC_MAX $port:${m:-?}"
        if [ $DDC_PROX = 1 ]; then ddc_xml $DDC_RANGE "$m"
        else ddc_xml $DDC_RANGE "$m" | sed '/<proxSensor>/,/<\/proxSensor>/d'
        fi > "$DOV/up/displayconfig/display_port_$port.xml"
    done
    chmod 755 "$DOV/up" "$DOV/up/displayconfig" && chmod 644 "$DOV/up/displayconfig/"*.xml
    $BB chcon -R u:object_r:system_file:s0 "$DOV/up" 2>/dev/null || true
    if $BB mount -t overlay overlay -o "ro,lowerdir=$DOV/up:$PETC" "$PETC"; then
        echo "Display config: product/etc/displayconfig/display_port_ for ports ${DDC_PORTS:-none} (One UI's nits curve, brightnessMaximum${DDC_MAX:- none}$([ $DDC_PROX = 1 ] && echo ", Samsung's IR proximity"))"
    else
        echo "Display config: read-only overlay on product/etc refused, left out"
    fi
fi
# The guest's /mnt is a tmpfs of its own (0.4.63), with One UI's folders bound in
# one by one, except the storage views guest_start.sh drops and rebuilds anyway
# (user, pass_through, installer, androidwritable, runtime). Until 0.4.62 it was
# a recursive bind of One UI's /mnt, so the guest's vold and zygote made and
# chmod'ed /mnt/user/0 in One UI's own /mnt (the guest's vold tears down the
# mounts under /mnt/ at its start, our tmpfs on /mnt/user/0 included). On the
# Galaxy A54 that file system was read-only for both systems: every session died
# at the first fork (fs_prepare_dir failed on /mnt/user/0: Read-only file system;
# 0.4.60/0.4.61 fe657556, 89641598, 7f813b0e, 84669c97, ColorOS and Infinity-X)
# and One UI's vold could not remake /mnt/user/0/self after the return.
# ONEOS_GUEST_OWN_MNT=0 keeps the recursive bind.
if mount | grep -q "$ROOTFS/mnt "; then
    :
elif [ "${ONEOS_GUEST_OWN_MNT:-1}" = 1 ] &&
     $BB mount -t tmpfs -o mode=0755,uid=0,gid=1000 tmpfs "$ROOTFS/mnt" && $BB mount --make-private "$ROOTFS/mnt"; then
    $BB chcon u:object_r:tmpfs:s0 "$ROOTFS/mnt" 2>/dev/null || true
    MNT_BOUND=""
    for d in /mnt/* /mnt/.[!.]*; do
        [ -e "$d" ] || [ -L "$d" ] || continue
        name=${d#/mnt/}
        case "$name" in
            user|pass_through|installer|androidwritable|runtime) mkdir -p "$ROOTFS/mnt/$name"; continue ;;
        esac
        if [ -L "$d" ]; then
            ln -s "$(readlink "$d")" "$ROOTFS/mnt/$name" 2>/dev/null
        elif [ -d "$d" ]; then
            # rslave at once: an umount on the way back must never reach One UI's mounts.
            mkdir -p "$ROOTFS/mnt/$name" && $BB mount --rbind "$d" "$ROOTFS/mnt/$name" &&
                $BB mount --make-rslave "$ROOTFS/mnt/$name" 2>/dev/null && MNT_BOUND="$MNT_BOUND $name"
        fi
    done
    # init.rc's folders for those views, made the way init makes them (0.4.65): the
    # guest's vold makes its mount points inside them (/mnt/runtime/default/emulated
    # and the rest) and does not make the parents. With the bind, One UI's init-made
    # folders stayed after guest_start.sh dropped the mounts; in the new tmpfs
    # /mnt/runtime was empty, vold failed "emulated;0 failed to create mount points"
    # and the guest had no internal storage (0.4.63 S25+ HyperOS a4000feeb958acf5,
    # "full storage", /storage/emulated/0 missing). Mode, owner and SELinux label are
    # One UI's for the same folder (Fold8 Ultra: runtime 700 root storage_file, user,
    # installer, androidwritable 750 root:media_rw mnt_user_file, pass_through 700
    # root mnt_pass_through_file); init.rc's mode and root when One UI has none.
    MNT_MADE=0
    for spec in runtime:700 runtime/default:755 runtime/default/self:755 runtime/read:755 runtime/read/self:755 \
                runtime/write:755 runtime/write/self:755 runtime/full:755 runtime/full/self:755 \
                pass_through:700 user:750 installer:750 androidwritable:750; do
        p=${spec%:*}
        mode=${spec#*:} own=0:0
        if [ -d "/mnt/$p" ]; then
            m=$(stat -c %a "/mnt/$p" 2>/dev/null) && [ -n "$m" ] && mode=$m
            o=$(stat -c %u:%g "/mnt/$p" 2>/dev/null) && [ -n "$o" ] && own=$o
        fi
        mkdir -p "$ROOTFS/mnt/$p" && chmod "$mode" "$ROOTFS/mnt/$p" && chown "$own" "$ROOTFS/mnt/$p" || continue
        ctx=$(ls -dZ "/mnt/$p" 2>/dev/null | awk '{print $1}')
        case "$ctx" in u:object_r:*) $BB chcon "$ctx" "$ROOTFS/mnt/$p" 2>/dev/null ;; esac
        MNT_MADE=$((MNT_MADE + 1))
    done
    echo "Guest /mnt: its own tmpfs; One UI's$MNT_BOUND bound in (storage views rebuilt by the guest; $MNT_MADE of init's 13 storage folders made)"
elif $BB mount --rbind /mnt "$ROOTFS/mnt"; then
    # rslave at once: /mnt is a recursive bind of the host's shared storage
    # (/mnt/vendor/efs, /mnt/user/0/emulated); an early-exit umount on the way
    # back must never propagate to those host mounts.
    $BB mount --make-rslave "$ROOTFS/mnt" 2>/dev/null || true
    echo "Guest /mnt: One UI's, a recursive bind (ONEOS_GUEST_OWN_MNT=${ONEOS_GUEST_OWN_MNT:-1})"
fi
# Guest-local PIN: an update of the fixes replaces services_patched.jar with a
# build that has no PIN verifier, which strands a PIN already stored in the
# guest's /data. A patched copy is kept in the guest's own data, stamped with
# the jar it was built from, and used only for that same build.
SERVICES_SRC="$STAGE/services_patched.jar"
PIN_JAR="$STAGE/data/local/tmp/oneos_pin/services_patched.jar"
PIN_BASE="$STAGE/data/local/tmp/oneos_pin/base.sha256"
if [ -f "$PIN_JAR" ] && [ -f "$PIN_BASE" ] && [ -f "$SERVICES_SRC" ]; then
    pin_want=$(head -n 1 "$PIN_BASE" 2>/dev/null | awk '{print $1}')
    pin_have=$(sha256sum "$SERVICES_SRC" 2>/dev/null | awk '{print $1}')
    if [ -n "$pin_want" ] && [ "$pin_want" = "$pin_have" ]; then
        $BB chcon -h u:object_r:system_file:s0 "$PIN_JAR" 2>/dev/null || true
        SERVICES_SRC="$PIN_JAR"
        echo "Guest-local PIN: using the kept patched services.jar"
    else
        echo "Guest-local PIN: the kept jar is for another build; not used (scripts/install-pin-jar.sh)"
        [ -f "$STAGE/data/system/oneos_pin" ] &&
            echo "WARNING: the guest has a PIN but the services.jar in use has no verifier; it cannot be entered until scripts/install-pin-jar.sh runs for this build"
    fi
else
    [ -f "$STAGE/data/system/oneos_pin" ] &&
        echo "WARNING: the guest has a PIN but no kept verifier jar; run scripts/install-pin-jar.sh before switching"
fi
if [ -f "$SERVICES_SRC" ]; then
    $BB umount -l "$ROOTFS/system/framework/services.jar" 2>/dev/null || true
    $BB mount --bind "$SERVICES_SRC" "$ROOTFS/system/framework/services.jar"
    echo "Bound services_patched.jar -> $ROOTFS/system/framework/services.jar"
fi
# The guarded jar is what keeps the guest away from One UI's data.
if [ "$(stat -c %d:%i "$ROOTFS/system/framework/services.jar")" != "$(stat -c %d:%i "$SERVICES_SRC")" ]; then
    echo "ERROR: the guarded services.jar is not in place; not starting the guest"
    exit 3
fi
# Patched guest surfaceflinger (no Qualcomm composer extension client; see
# scripts/make-overlays.sh). Inside the container only.
if [ -f "$STAGE/surfaceflinger_patched" ] && [ "${ONEOS_STOCK_SF:-0}" != "1" ]; then
    chmod 755 "$STAGE/surfaceflinger_patched"
    $BB umount -l "$ROOTFS/system/bin/surfaceflinger" 2>/dev/null || true
    $BB mount --bind "$STAGE/surfaceflinger_patched" "$ROOTFS/system/bin/surfaceflinger"
    echo "Bound surfaceflinger_patched -> $ROOTFS/system/bin/surfaceflinger"
fi
# Pixel Fold's device state policy without tent mode (scripts/patch-yogi-tent.py):
# it keeps the cover on until the hinge passes 90 degrees whenever it guesses a
# tent (screen kept on, rotated, or the second accelerometer a Galaxy has not).
# Off by default since test build 8: Samsung's hinge_angle sensor, the one the
# policy reads, reports every 4-6 s in coarse steps (180, 90/115, 0/5), and
# without tent mode Pixel followed those late readings: the inner panel came on
# about 5 s after opening, and a switch made folded started on the inner panel
# (owner, 11-06). ONEOS_GUEST_TENT=0 binds it again.
if [ "${ONEOS_GUEST_TENT:-1}" = 0 ] && [ -f "$STAGE/yogi-services_patched.jar" ]; then
    for YS in "$ROOTFS/system/system_ext/framework/yogi-services.jar" "$ROOTFS/system_ext/framework/yogi-services.jar"; do
        [ -f "$YS" ] && [ ! -L "$YS" ] || continue
        $BB umount -l "$YS" 2>/dev/null || true
        $BB mount --bind "$STAGE/yogi-services_patched.jar" "$YS" &&
            echo "Bound yogi-services_patched.jar -> $YS (no tent mode: the inner panel as soon as the hinge opens)"
        break
    done
fi
# The guest's boot animation on every panel (scripts/patch-bootanim-multidisplay.py):
# built without Android's multidisplay flag it drew on the first display only,
# the Fold's inner panel, and the cover stayed black when the switch started
# folded, though the guest's surfaceflinger lights every panel. The library
# keeps the image's name. Looks only: a missing or odd file leaves the image's
# own. ONEOS_GUEST_BOOTANIM_ALL=0 keeps it.
if [ "${ONEOS_GUEST_BOOTANIM_ALL:-1}" = 1 ]; then
    for l in libbootanimation_preapex libbootanimation; do
        BAL="$ROOTFS/system/lib64/$l.so"
        if [ -f "$STAGE/${l}_patched.so" ] && [ -f "$BAL" ] && [ ! -L "$BAL" ] && [ ! -L "$ROOTFS/system/lib64" ]; then
            $BB umount -l "$BAL" 2>/dev/null || true
            $BB mount --bind "$STAGE/${l}_patched.so" "$BAL" &&
                echo "Bound ${l}_patched.so -> $BAL (boot animation on every display)"
        fi
    done
fi
# The guest's own vold as "gvld" (run 44; scripts/make-overlays.sh,
# docs/inplace-return.md): vold_patched registers "gvld" and not
# android.system.vold.IVold/default, so One UI's vold keeps both its names all
# session (it cannot be restarted; the return without a reboot needs them).
# service.incremental_patched.so and the guarded services.jar look up "gvld".
# All three or none, as guards.txt lists them (hashes checked above): a
# services.jar that looks up "vold" next to this vold would get One UI's.
# guest_start.sh reads oneos_vold_name and checks both names before going on.
rm -f "$STAGE/data/oneos_vold_name"
VG=$(awk '$2 == "vold_patched" { v = 1 } $2 == "service.incremental_patched.so" { i = 1 } END { print v + i }' "$STAGE/guards.txt")
if [ "$VG" = 2 ]; then
    chmod 755 "$STAGE/vold_patched"
    chmod 644 "$STAGE/service.incremental_patched.so"
    for b in vold_patched:/system/bin/vold service.incremental_patched.so:/system/lib64/service.incremental.so; do
        src="$STAGE/${b%%:*}"; dst="$ROOTFS${b#*:}"
        $BB umount -l "$dst" 2>/dev/null || true
        $BB mount --bind "$src" "$dst"
        if [ "$(stat -c %d:%i "$dst" 2>/dev/null)" != "$(stat -c %d:%i "$src")" ]; then
            echo "ERROR: ${b%%:*} is not in place at $dst (guards.txt lists it); not starting the guest"
            exit 3
        fi
        echo "Bound ${b%%:*} -> $dst"
    done
    echo gvld > "$STAGE/data/oneos_vold_name"
    echo "Guest vold: registers gvld; One UI's vold keeps vold and android.system.vold.IVold/default"
elif [ "$VG" != 0 ]; then
    echo "ERROR: guards.txt lists only one of vold_patched and service.incremental_patched.so (a half-built set); not starting the guest"
    exit 3
elif [ -f "$STAGE/vold_patched" ]; then
    echo "Guest vold: vold_patched is staged but guards.txt does not list it (another overlay set): not bound, the guest vold takes vold"
else
    echo "Guest vold: no vold_patched for this image, the guest vold takes vold (no return without a reboot)"
fi
# vivo OriginOS: vivo-services.jar runs in system_server; its guarded build
# (patches/vivo_guards.py: vivo's IOemNetd never reaches One UI's netd, HAL
# extensions only when vivo's; the storage guards) must be in place, or the
# guest does not start.
VSJ="$ROOTFS/system/framework/vivo-services.jar"
if [ -e "$VSJ" ] || [ -L "$VSJ" ]; then
    if [ -f "$STAGE/vivo-services_patched.jar" ] && [ -f "$VSJ" ] && [ ! -L "$VSJ" ] && [ ! -L "$ROOTFS/system/framework" ]; then
        $BB umount -l "$VSJ" 2>/dev/null || true
        $BB mount --bind "$STAGE/vivo-services_patched.jar" "$VSJ"
    fi
    VJ=$(stat -c %d:%i "$VSJ" 2>/dev/null)
    if [ -z "$VJ" ] || [ "$VJ" != "$(stat -c %d:%i "$STAGE/vivo-services_patched.jar" 2>/dev/null)" ] ||
        ! awk '$2 == "vivo-services_patched.jar" { f = 1 } END { exit !f }' "$STAGE/guards.txt"; then
        echo "ERROR: the guarded vivo-services.jar is not in place; not starting the guest"
        exit 3
    fi
    echo "Bound vivo-services_patched.jar -> $VSJ"
fi
# vivo-telephony-common-platform-ex.jar (vivo OriginOS, MediaTek build): the phone
# process's MtkRIL waited for MediaTek's mtkradioex services, which a Samsung
# vendor lacks, and never connected to One UI's radio (seventh run: no SIM, no
# signal). The guarded build (patches/vivo_telephony.py) needs only the AOSP
# IRadio services; listed in guards.txt and checked above.
VTX="$ROOTFS/system/framework/vivo-telephony-common-platform-ex.jar"
if [ -f "$STAGE/vivo-telephony-common-platform-ex_patched.jar" ] && [ -f "$VTX" ] && [ ! -L "$VTX" ] && [ ! -L "$ROOTFS/system/framework" ]; then
    $BB umount -l "$VTX" 2>/dev/null || true
    $BB mount --bind "$STAGE/vivo-telephony-common-platform-ex_patched.jar" "$VTX" &&
        echo "Bound vivo-telephony-common-platform-ex_patched.jar -> $VTX (MtkRIL without mtkradioex)"
fi
# vivo-framework_patched.jar (boot class path, phone builds): vivo's brightness and
# sensor code keeps its normal tables (patches/vivo_brightness.py); with a device
# state above 0 (fold mode's OPEN, or the vendor's 3 in slab mode) it took
# "unfolded" tables a phone build lacks (ninth CN run: system_server died).
VFJ="$ROOTFS/system/framework/vivo-framework.jar"
if [ -f "$STAGE/vivo-framework_patched.jar" ] && [ -f "$VFJ" ] && [ ! -L "$VFJ" ] && [ ! -L "$ROOTFS/system/framework" ]; then
    $BB umount -l "$VFJ" 2>/dev/null || true
    $BB mount --bind "$STAGE/vivo-framework_patched.jar" "$VFJ" &&
        echo "Bound vivo-framework_patched.jar -> $VFJ (brightness on the phone build's tables)"
fi
# vivo's display and input side read their device type from ro.oneos.vivo.dtype
# (guest_props.sh; make-overlays.sh renamed the property in them): "foldable" for
# both panels while the apps keep the phone build's "phone" (fold mode 2).
for VL in libinputflinger libinputservice libandroid_servers; do
    VLF="$ROOTFS/system/lib64/$VL.so"
    [ -f "$STAGE/${VL}_patched.so" ] && [ -f "$VLF" ] && [ ! -L "$VLF" ] && [ ! -L "$ROOTFS/system/lib64" ] || continue
    chmod 644 "$STAGE/${VL}_patched.so"
    $BB umount -l "$VLF" 2>/dev/null || true
    $BB mount --bind "$STAGE/${VL}_patched.so" "$VLF" && echo "Bound ${VL}_patched.so -> $VLF (vivo's device type from ro.oneos.vivo.dtype)"
done
# framework-adapter_patched.jar (vivo OriginOS, boot class path): About phone's
# processor from the generic CPU nodes (patches/vivo_guards.py framework-adapter;
# "Processor null GHz" with One UI's vendor version). Cosmetic: a missing one
# leaves the image's.
FAJ="$ROOTFS/system/framework/framework-adapter.jar"
if [ -f "$STAGE/framework-adapter_patched.jar" ] && [ -f "$FAJ" ] && [ ! -L "$FAJ" ] && [ ! -L "$ROOTFS/system/framework" ]; then
    $BB umount -l "$FAJ" 2>/dev/null || true
    $BB mount --bind "$STAGE/framework-adapter_patched.jar" "$FAJ" &&
        echo "Bound framework-adapter_patched.jar -> $FAJ (CPU info from the generic nodes)"
fi
# BBKLauncher2_patched.apk (vivo OriginOS on a Fold): the bar phone's launcher
# stays one with ro.vivo.device.type=foldable (guest_props.sh): it reads a
# property no build sets instead (patches/vivo_launcher.py), and framework.jar's
# FtDeviceInfo answers "phone" in its process (vivo_guards.py). As a foldable it
# exited at start (eighth run), then crashed in foldable paths its build lacks
# (ninth run). Only over a build it was written for (the X500 Pro Max global,
# the CN PD2609MA), and only over the very APK it was made from
# (BBKLauncher2_patched.apk.src_sha256, written by make-overlays.sh): a global
# set's launcher must never go over the CN image's, or the other way round.
VLA="$ROOTFS/system/app/BBKLauncher2/BBKLauncher2.apk"
if [ -f "$STAGE/BBKLauncher2_patched.apk" ] && [ -f "$VLA" ] && [ ! -L "$VLA" ] && [ ! -L "$ROOTFS/system/app" ]; then
    $BB umount -l "$VLA" 2>/dev/null || true
    VLA_SUM=$(sha256sum "$VLA" 2>/dev/null | cut -d' ' -f1)
    VLA_SRC=$(cat "$STAGE/BBKLauncher2_patched.apk.src_sha256" 2>/dev/null)
    case "$VLA_SUM" in
        4927b1690e9b60884a495f71d9ba71086cf047f2c37f5f59e210c8fd6cb38a0a|cc6bb458eae1c0fc3f452df439089cf4fa95419516e3bac2c4d7c329ce38e03a) ;;
        *) VLA_SUM="" ;;
    esac
    if [ -z "$VLA_SUM" ]; then
        echo "vivo launcher: this image's BBKLauncher2.apk is another build; its own stays"
    elif [ "$VLA_SRC" != "$VLA_SUM" ]; then
        echo "vivo launcher: the staged BBKLauncher2_patched.apk was made from another BBKLauncher2.apk (${VLA_SRC:-no .src_sha256}); the image's own stays"
    else
        chmod 644 "$STAGE/BBKLauncher2_patched.apk"
        $BB chcon u:object_r:system_file:s0 "$STAGE/BBKLauncher2_patched.apk" 2>/dev/null || true
        $BB mount --bind "$STAGE/BBKLauncher2_patched.apk" "$VLA" &&
            $BB mount -o remount,bind,ro "$STAGE/BBKLauncher2_patched.apk" "$VLA" 2>/dev/null
        if [ "$(stat -c %d:%i "$VLA" 2>/dev/null)" = "$(stat -c %d:%i "$STAGE/BBKLauncher2_patched.apk")" ]; then
            echo "Bound BBKLauncher2_patched.apk -> $VLA (the bar phone's launcher keeps its device type)"
        else
            echo "!!! WARNING: BBKLauncher2_patched.apk is not in place; vivo's launcher may take foldable paths it lacks"
        fi
    fi
fi
if [ -f "$STAGE/oplus-services_patched.jar" ] && [ -f "$ROOTFS/system/framework/oplus-services.jar" ]; then
    $BB umount -l "$ROOTFS/system/framework/oplus-services.jar" 2>/dev/null || true
    $BB mount --bind "$STAGE/oplus-services_patched.jar" "$ROOTFS/system/framework/oplus-services.jar"
    echo "Bound oplus-services_patched.jar -> $ROOTFS/system/framework/oplus-services.jar"
fi
# OneOS: checked like services.jar. This jar carries guards too (storage,
# installd callers, sysrq; scripts/make-overlays.sh), and a failed bind used
# to start the guest with ColorOS's own. An image without it (Pixel) has no
# OPPO framework to guard.
if [ -e "$ROOTFS/system/framework/oplus-services.jar" ] || [ -L "$ROOTFS/system/framework/oplus-services.jar" ]; then
    OSJ=$(stat -c %d:%i "$ROOTFS/system/framework/oplus-services.jar" 2>/dev/null)
    if [ -z "$OSJ" ] || [ "$OSJ" != "$(stat -c %d:%i "$STAGE/oplus-services_patched.jar" 2>/dev/null)" ] ||
        ! awk '$2 == "oplus-services_patched.jar" { f = 1 } END { exit !f }' "$STAGE/guards.txt"; then
        echo "ERROR: the guarded oplus-services.jar is not in place; not starting the guest"
        exit 3
    fi
else
    echo "No oplus-services.jar in the guest image: only services.jar carries guards"
fi
# Bluetooth A2DP and USB outputs for a guest that reads Samsung's plain audio
# policy file. On the Exynos phones with a HIDL audio HAL (A16 5G, A34, A35,
# S24, S24+) /vendor/etc/audio_policy_configuration.xml is the short file
# Samsung ships for the vendor tests: speaker, earpiece, wired headset and
# Bluetooth calls, no A2DP device, no Bluetooth module and no USB one (the
# _sec file One UI's own audioserver loads has them in its primary module). A
# guest that reads the plain file connects earbuds, the Bluetooth audio bridge
# starts the session, and audio policy has nowhere to send the sound ("could
# not find HW module for device type 'AUDIO_DEVICE_OUT_BLUETOOTH_A2DP'", A35
# sessions 631945a2 and b06d044f; the same for AUDIO_DEVICE_OUT_USB_HEADSET
# in b06d044f, where only the modules primary and r_submix were loaded).
#
# apm_copy <vendor file> <out file> <1: outputs may be added> writes the file
# with its relative xi:include hrefs made absolute, since the copy no longer
# sits next to the files they name, and then adds what the file lacks.
#
# Bluetooth A2DP (apm_a2dp): where the file and the files it includes name no
# A2DP output, a vendor manifest names an AIDL Bluetooth audio factory
# (Samsung's, for the bridge, or Android's: with the older HIDL one of the
# A25, A33 and S23 FE the guest's Bluetooth has no audio session to give the
# HAL, and sound would leave the speaker for nothing) and ONEOS_GUEST_APM_A2DP
# is not 0. One of two ways:
#   - The vendor's own Bluetooth module: Android's
#     bluetooth_audio_policy_configuration.xml (the _7_0 one for a 7.x policy
#     file that has it) included at the end of <modules>, where the vendor has
#     that file and the library the module loads (audio.bluetooth.*.so) and
#     the phone is not a Qualcomm one. This is a user's fix: on his Galaxy A35
#     with OxygenOS 16 he included this file and the USB one in a copy bound
#     over the guest's file, with a script of his own, and Bluetooth and USB
#     headphones played. 0.4.90 does the same before the guest starts.
#     ONEOS_GUEST_APM_BT_MODULE=0 takes the other way, =1 takes this one on a
#     Qualcomm phone too.
#   - Otherwise, where One UI's _sec or _base file has an A2DP output, three
#     A2DP devices in the primary module as that file has them (16-bit PCM,
#     48 kHz stereo), fed by the speaker's own mix ports except the mmap ones
#     (0.4.85; it played on a Qualcomm vendor, Nothing OS session 32b35f59,
#     and no report says it did on an Exynos one).
#
# USB (apm_usb): where the file and the files it includes name no USB output
# and the vendor has Android's usb_audio_policy_configuration.xml and the
# library its module loads (audio.usb.*.so), that file is included the same
# way. ONEOS_GUEST_APM_USB=0 leaves it out.
#
# Speaker, earpiece, headset and microphones stay as the file has them.
# APM_NOTE says what was done for Bluetooth and APM_USB what was done for USB
# (empty: nothing); APM_ADDED is 1 when the copy has more in it than the
# vendor's file. A file whose layout these do not follow is left as it is.

# apm_hw_lib <module>: the vendor has the audio HAL library a policy module of
# that name loads (audio.<module>.<variant>.so).
apm_hw_lib() {
    for apm_d in /vendor/lib64/hw /vendor/lib/hw /odm/lib64/hw /odm/lib/hw; do
        for apm_f in "$apm_d/audio.$1."*.so; do
            [ -f "$apm_f" ] && return 0
        done
    done
    return 1
}

# apm_format <copy>: the version the policy file says it is written in ("7.0":
# lists with spaces; "1.0": with commas).
apm_format() {
    $BB tr '\n\t' '  ' < "$1" | $BB sed -n 's/.*<audioPolicyConfiguration[^>]* version="\([0-9.]*\)".*/\1/p'
}

# apm_include <copy> <module file> <why>: the module file included at the end
# of the copy's <modules>, under a comment that says why. Only in a file that
# declares xi: and has one </modules> outside its comments.
apm_include() {
    rm -f "$1.inc"
    if awk -v inc="$2" -v why="$3" '
        function blank(n,  s) { s = ""; while (n-- > 0) s = s " "; return s }
        { doc = doc $0 "\n" }
        END {
            w = doc
            while ((i = index(w, "<!--")) > 0) {
                j = index(substr(w, i), "-->"); if (!j) exit 1
                w = substr(w, 1, i - 1) blank(j + 2) substr(w, i + j + 2)
            }
            if (!index(w, "xmlns:xi=")) exit 1
            p = index(w, "</modules>"); if (!p || index(substr(w, p + 1), "</modules>")) exit 1
            # The indentation of </modules>, where it stands alone on its line.
            b = p; while (b > 1 && substr(doc, b - 1, 1) != "\n") b--
            ind = substr(doc, b, p - b); lead = ""
            if (ind !~ /^[ \t]*$/) { ind = "    "; lead = "\n" ind }
            printf "%s", substr(doc, 1, p - 1) lead "    <!-- OneOS: " why " -->\n" ind "    <xi:include href=\"" inc "\"/>\n" ind substr(doc, p)
        }' "$1" > "$1.inc" && [ "$($BB grep -c "<xi:include href=\"$2\"/>" "$1.inc")" = 1 ]; then
        cat "$1.inc" > "$1"
        rm -f "$1.inc"
        return 0
    fi
    rm -f "$1.inc"
    return 1
}

# apm_a2dp <vendor file> <copy>: the Bluetooth A2DP outputs, see above.
apm_a2dp() {
    if [ "${ONEOS_GUEST_APM_A2DP:-1}" != 1 ]; then
        APM_NOTE="no A2DP outputs added (ONEOS_GUEST_APM_A2DP=$ONEOS_GUEST_APM_A2DP)"; return 0
    fi
    apm_inc=$($BB grep -o 'href="/[^" ]*"' "$2" | $BB sed -e 's/^href="//' -e 's/"$//')
    if $BB grep -qs 'AUDIO_DEVICE_OUT_BLUETOOTH_A2DP' "$2" $apm_inc; then
        APM_NOTE="it has A2DP outputs of its own"; return 0
    fi
    case "${ONEOS_GUEST_APM_BT_MODULE:-auto}" in
        0) apm_mod=0 ;;
        1) apm_mod=1 ;;
        *) apm_mod=1; if [ "$(getprop ro.soc.manufacturer)" = QTI ]; then apm_mod=0; fi ;;
    esac
    if [ "$apm_mod" = 1 ]; then
        apm_bt=/vendor/etc/bluetooth_audio_policy_configuration.xml
        case "$(apm_format "$2")" in
            7.*) if $BB grep -qs 'AUDIO_DEVICE_OUT_BLUETOOTH_A2DP"' "${apm_bt%.xml}_7_0.xml"; then apm_bt="${apm_bt%.xml}_7_0.xml"; fi ;;
        esac
        if $BB grep -qs 'AUDIO_DEVICE_OUT_BLUETOOTH_A2DP"' "$apm_bt" && apm_hw_lib bluetooth \
           && $BB grep -rqs -E 'ISehBluetoothAudioProviderFactory|IBluetoothAudioProviderFactory' /vendor/etc/vintf/ \
           && apm_include "$2" "$apm_bt" "Bluetooth A2DP through the vendor's own Bluetooth audio module"; then
            APM_NOTE="Bluetooth A2DP outputs added with the vendor's Bluetooth module (${apm_bt##*/})"
            APM_ADDED=1
            return 0
        fi
    fi
    if ! $BB grep -qs 'AUDIO_DEVICE_OUT_BLUETOOTH_A2DP"' /vendor/etc/audio_policy_configuration_sec.xml /vendor/etc/audio_policy_configuration_base.xml; then
        APM_NOTE="no A2DP outputs added (One UI's own policy file has none)"; return 0
    fi
    if ! $BB grep -rqs -E 'ISehBluetoothAudioProviderFactory|IBluetoothAudioProviderFactory' /vendor/etc/vintf/; then
        APM_NOTE="no A2DP outputs added (no AIDL Bluetooth audio HAL on this phone)"; return 0
    fi
    if awk '
        function blank(n,  s) { s = ""; while (n-- > 0) s = s " "; return s }
        function attr(tag, name,  v, q) {
            if (!match(tag, "[ \t\n]" name "[ \t\n]*=[ \t\n]*\"[^\"]*\"")) return ""
            v = substr(tag, RSTART, RLENGTH); q = index(v, "\"")
            return substr(v, q + 1, length(v) - q - 1)
        }
        # The first <el ...> tag whose attribute key is val: its attribute want.
        function tagwith(m, el, key, val, want,  p, i, j, tag) {
            p = m
            while ((i = index(p, "<" el)) > 0) {
                p = substr(p, i); j = index(p, ">"); if (!j) return ""
                tag = substr(p, 1, j)
                if (attr(tag, key) == val) return attr(tag, want)
                p = substr(p, j + 1)
            }
            return ""
        }
        { doc = doc $0 "\n" }
        END {
            # Comments blanked in a working copy, so that positions stay those of the file.
            w = doc
            while ((i = index(w, "<!--")) > 0) {
                j = index(substr(w, i), "-->"); if (!j) exit 1
                w = substr(w, 1, i - 1) blank(j + 2) substr(w, i + j + 2)
            }
            if (index(w, "OneOS BT A2DP")) exit 1
            if (!match(w, "<module[^>]*[ \t\n]name[ \t\n]*=[ \t\n]*\"primary\"[^>]*>")) exit 1
            ms = RSTART; me = index(substr(w, ms), "</module>"); if (!me) exit 1
            m = substr(w, ms, me - 1)
            spk = tagwith(m, "devicePort", "type", "AUDIO_DEVICE_OUT_SPEAKER", "tagName"); if (spk == "") exit 1
            src = tagwith(m, "route", "sink", spk, "sources"); if (src == "") exit 1
            n = split(src, a, ","); out = ""
            for (k = 1; k <= n; k++) {
                s = a[k]; gsub(/^[ \t\n]+/, "", s); gsub(/[ \t\n]+$/, "", s)
                if (s == "" || tolower(s) ~ /mmap/) continue
                if (tagwith(m, "mixPort", "name", s, "role") != "source") exit 1
                out = out (out == "" ? "" : ",") s
            }
            if (out == "") exit 1
            dp = index(m, "</devicePorts>"); rt = index(m, "</routes>"); if (!dp || rt < dp) exit 1
            dp = ms + dp - 1; rt = ms + rt - 1
            ind = "            "
            split("Out Headphones Speaker", nm, " "); split("x _HEADPHONES _SPEAKER", ty, " "); ty[1] = ""
            ports = "<!-- OneOS: Bluetooth A2DP through the primary module, as in the policy file One UI itself loads -->\n" ind
            routes = ""
            for (k = 1; k <= 3; k++) {
                ports = ports "<devicePort tagName=\"OneOS BT A2DP " nm[k] "\" type=\"AUDIO_DEVICE_OUT_BLUETOOTH_A2DP" ty[k] "\" role=\"sink\">\n" \
                    ind "    <profile name=\"\" format=\"AUDIO_FORMAT_PCM_16_BIT\" samplingRates=\"48000\" channelMasks=\"AUDIO_CHANNEL_OUT_STEREO\"/>\n" \
                    ind "</devicePort>\n" ind
                routes = routes "<route type=\"mix\" sink=\"OneOS BT A2DP " nm[k] "\" sources=\"" out "\"/>\n" ind
            }
            printf "%s", substr(doc, 1, dp - 1) ports substr(doc, dp, rt - dp) routes substr(doc, rt)
        }' "$2" > "$2.a2dp" && [ "$($BB grep -c 'tagName="OneOS BT A2DP ' "$2.a2dp")" = 3 ]; then
        APM_NOTE="Bluetooth A2DP outputs added on $($BB sed -n 's/.*sink="OneOS BT A2DP Out" sources="\([^"]*\)".*/\1/p' "$2.a2dp")"
        cat "$2.a2dp" > "$2"
        APM_ADDED=1
    else
        APM_NOTE="no A2DP outputs added (the layout of $1 is not one this knows)"
    fi
    rm -f "$2.a2dp"
}

# apm_usb <copy>: the USB outputs, see above.
apm_usb() {
    [ "${ONEOS_GUEST_APM_USB:-1}" = 1 ] || return 0
    apm_inc=$($BB grep -o 'href="/[^" ]*"' "$1" | $BB sed -e 's/^href="//' -e 's/"$//')
    if $BB grep -qs 'AUDIO_DEVICE_OUT_USB_' "$1" $apm_inc; then return 0; fi
    apm_uf=/vendor/etc/usb_audio_policy_configuration.xml
    if $BB grep -qs 'AUDIO_DEVICE_OUT_USB_' "$apm_uf" && apm_hw_lib usb \
       && apm_include "$1" "$apm_uf" "USB headphones through the vendor's own usb audio module"; then
        APM_USB="USB outputs added with the vendor's usb module (${apm_uf##*/})"
        APM_ADDED=1
    fi
    return 0
}

apm_copy() {
    APM_NOTE=""
    APM_USB=""
    APM_ADDED=0
    rm -f "$2" "$2.a2dp" "$2.inc"
    [ -f "$1" ] || return 1
    $BB sed -e "s#href=\"\([^/\"][^\"]*\)\"#href=\"${1%/*}/\1\"#g" "$1" > "$2" || return 1
    [ -s "$2" ] || return 1
    [ "$3" = 1 ] || return 0
    apm_a2dp "$1" "$2"
    apm_usb "$2"
    [ -s "$2" ]
}

# HyperOS: Xiaomi's miui-services.jar (recovery, factory resets, preinstall
# copiers, vold, netd) and apprecovery.proinstaller.jar (installs apps by
# itself), both on the system server class path, guarded like
# oplus-services.jar (patches/miui_guards.py, docs/hyperos.md), and
# miui-wifi-service.jar, whose casts of One UI's Wi-Fi HAL extensions only
# take Xiaomi's (patches/hyperos_hal_ext.py), and miui-telephony-common.jar,
# whose IMS controller works without an IMS phone (patches/hyperos_telephony.py). Bound on the guest's system_ext
# after its overlay above; an image with miui-services.jar starts only with
# both guarded jars in place.
MIUI_FW="$GUEST_SYSTEM_EXT/framework"
if [ -e "$MIUI_FW/miui-services.jar" ] || [ -L "$MIUI_FW/miui-services.jar" ]; then
    for j in miui-services apprecovery.proinstaller miui-wifi-service miui-telephony-common; do
        if [ -f "$STAGE/${j}_patched.jar" ] && [ -f "$MIUI_FW/$j.jar" ] && [ ! -L "$MIUI_FW/$j.jar" ]; then
            $BB umount -l "$MIUI_FW/$j.jar" 2>/dev/null || true
            $BB mount --bind "$STAGE/${j}_patched.jar" "$MIUI_FW/$j.jar"
        fi
        MJ=$(stat -c %d:%i "$MIUI_FW/$j.jar" 2>/dev/null)
        if [ -z "$MJ" ] || [ "$MJ" != "$(stat -c %d:%i "$STAGE/${j}_patched.jar" 2>/dev/null)" ] ||
            ! awk -v n="${j}_patched.jar" '$2 == n { f = 1 } END { exit !f }' "$STAGE/guards.txt"; then
            echo "ERROR: the guarded $j.jar is not in place; not starting the guest"
            exit 3
        fi
        echo "Bound ${j}_patched.jar -> $MIUI_FW/$j.jar"
    done
    # framework.jar with AOSP's CameraStatus parcel (patches/hyperos_framework.py):
    # Xiaomi's two extra fields made every status from One UI's cameraserver
    # after the first null, and system_server died in BiometricService.
    HFW="$ROOTFS/system/framework/framework.jar"
    if [ -f "$STAGE/framework_patched.jar" ] && [ -f "$HFW" ] && [ ! -L "$HFW" ] && [ ! -L "$ROOTFS/system/framework" ]; then
        $BB umount -l "$HFW" 2>/dev/null || true
        $BB mount --bind "$STAGE/framework_patched.jar" "$HFW"
    fi
    MJ=$(stat -c %d:%i "$HFW" 2>/dev/null)
    if [ -z "$MJ" ] || [ "$MJ" != "$(stat -c %d:%i "$STAGE/framework_patched.jar" 2>/dev/null)" ] ||
        ! awk '$2 == "framework_patched.jar" { f = 1 } END { exit !f }' "$STAGE/guards.txt"; then
        echo "ERROR: HyperOS's framework.jar with One UI's camera status format is not in place; not starting the guest"
        exit 3
    fi
    echo "Bound framework_patched.jar -> $HFW"
    # The SIM on a HIDL radio (0.4.70; patches/hyperos_hidl_radio.py): Xiaomi's VendorRIL waited for
    # its AIDL radio forever on the MediaTek A07, A16 4G and A17 ("getRadioServiceProxy wait for rild
    # ready", no SIM: 0.4.67 5357ba6a, d946ff36, c3630d06). Sets from r25 carry the jar; older ones
    # keep the image's.
    XOT="$MIUI_FW/xiaomi-opt-telephony.jar"
    if [ -f "$STAGE/xiaomi-opt-telephony_patched.jar" ] && [ -f "$XOT" ] && [ ! -L "$XOT" ]; then
        $BB umount -l "$XOT" 2>/dev/null || true
        if $BB mount --bind "$STAGE/xiaomi-opt-telephony_patched.jar" "$XOT"; then
            echo "Bound xiaomi-opt-telephony_patched.jar -> $XOT (VendorRIL takes a HIDL radio)"
        else
            echo "!!! xiaomi-opt-telephony_patched.jar not bound; a HIDL radio keeps waiting for Xiaomi's AIDL rild"
        fi
    fi
    # Calls and SMS over Samsung IMS (0.4.62). HyperOS's ImsFactory loads
    # Xiaomi's XmImsFactory from xiaomi-opt-ims.jar, and its XmImsManager wants
    # Xiaomi's own IMS service, which a Galaxy does not have: at the first
    # connectionReady it threw "XmImsService is unavailable(106)" (createImsService
    # binder is null), and ImsSmsDispatcher and ImsPhoneCallTracker dropped
    # Samsung's IMS service for the whole session (S23 HyperOS 36e46e14, Jio:
    # IMS REGISTERED with mmtel and smsip, every text went to the radio as
    # IMS_SEND_SMS and came back error 44, calls failed). Without the jar
    # ImsFactory falls back to AOSP's ImsManager by itself ("failed to load ims
    # factory"), which talks to the bound ImsService as on the other systems.
    # Nothing else loads the jar (no app declares the library). An empty file
    # over it for the session; ONEOS_GUEST_XIAOMI_IMS=1 keeps it.
    XIMS="$MIUI_FW/xiaomi-opt-ims.jar"
    if [ "${ONEOS_GUEST_XIAOMI_IMS:-0}" != 1 ] && [ -f "$XIMS" ] && [ ! -L "$XIMS" ]; then
        rm -f "$STAGE/xiaomi-opt-ims.empty"
        : > "$STAGE/xiaomi-opt-ims.empty" && chmod 644 "$STAGE/xiaomi-opt-ims.empty"
        $BB chcon u:object_r:system_file:s0 "$STAGE/xiaomi-opt-ims.empty" 2>/dev/null || true
        $BB umount -l "$XIMS" 2>/dev/null || true
        if $BB mount --bind "$STAGE/xiaomi-opt-ims.empty" "$XIMS" && [ ! -s "$XIMS" ]; then
            echo "Hid xiaomi-opt-ims.jar: HyperOS uses AOSP's ImsManager with Samsung IMS (calls and SMS)"
        else
            echo "!!! could not hide xiaomi-opt-ims.jar; HyperOS's calls and SMS over IMS may fail"
        fi
    fi
    # Xiaomi's SurfaceFlinger with the display mode group read whole
    # (patches/hyperos_sf_group.py): it compared a mode's group with the default
    # mode's low byte, and One UI numbers the groups by panel width on the S23,
    # S24 Ultra and Z Flip5 (1440 against 160): no mode matched and SurfaceFlinger
    # aborted at the first display, a black screen every session there.
    # 0.4.40: and its DolbyRenderer no longer queries Xiaomi's Xring buffer
    # metadata through a mapper the older Samsung vendors never load
    # (patches/hyperos_dolby_mapper.py; S24 Ultra, S23, A57: SIGSEGV at the
    # first GPU-composed frame, with or without the shader pre-warm).
    HSF="$GUEST_SYSTEM_EXT/lib64/libsurfaceflinger.so"
    if [ -f "$STAGE/libsurfaceflinger_patched.so" ] && [ -f "$HSF" ] && [ ! -L "$HSF" ]; then
        chmod 644 "$STAGE/libsurfaceflinger_patched.so"
        $BB chcon u:object_r:system_lib_file:s0 "$STAGE/libsurfaceflinger_patched.so" 2>/dev/null || true
        $BB umount -l "$HSF" 2>/dev/null || true
        $BB mount --bind "$STAGE/libsurfaceflinger_patched.so" "$HSF"
        if [ "$(stat -c %d:%i "$HSF" 2>/dev/null)" = "$(stat -c %d:%i "$STAGE/libsurfaceflinger_patched.so")" ]; then
            echo "Bound libsurfaceflinger_patched.so -> $HSF (mode groups read whole)"
        else
            echo "ERROR: HyperOS's SurfaceFlinger with whole mode groups is not in place; not starting the guest"
            exit 3
        fi
    fi
    # HyperOS's audioserver without an audio HAL adapter vendor extension
    # (patches/hyperos_audio_ext.py): only One UI's own audioserver serves one,
    # it is stopped for the session, and HyperOS's waited for it with no time
    # limit. Sound only, so a missing or odd file leaves the image's library.
    HAH="$ROOTFS/system/lib64/libaudiohal@aidl.so"
    if [ -f "$STAGE/libaudiohal_aidl_patched.so" ] && [ -f "$HAH" ] && [ ! -L "$HAH" ] && [ ! -L "$ROOTFS/system/lib64" ]; then
        $BB umount -l "$HAH" 2>/dev/null || true
        $BB mount --bind "$STAGE/libaudiohal_aidl_patched.so" "$HAH" &&
            echo "Bound libaudiohal_aidl_patched.so -> $HAH (no audio HAL adapter vendor extension)"
    fi
    # HyperOS's audio policy file. Xiaomi's AudioPolicyConfig
    # (system/lib64/libaudiopolicycomponents.so, the same code in both policy
    # engines) never asks for AOSP's audio_policy_configuration.xml: with
    # ro.miui.ui.version.code set it looks for a Bluetooth-offload variant
    # (audio_policy_configuration_le_offload_disabled.xml and the like) and then
    # audio_policy_configuration_mi.xml, in /odm/etc, /odm/etc/audio/sku_<sku>,
    # /vendor/etc/audio/sku_<sku>, /vendor/etc/audio, /vendor/etc and
    # /system/etc. Where the audio HAL is AIDL (S25, S26, Z Fold7/8, A36/A56/A57)
    # the policy comes from the HAL and no file is read. On the HIDL ones (S23,
    # S24, Z Fold5/Flip5, Z Fold6/Flip6, A26) no Samsung file has those names, so
    # HyperOS's audioserver fell back to AudioPolicyConfig::setDefault: speaker
    # and bottom mic only, no earpiece, no Bluetooth module, no volume curves.
    # Earbuds connected and the Bluetooth audio bridge started the A2DP session,
    # but AudioService could not make them a sound device ("could not find HW
    # module for device type 'AUDIO_DEVICE_OUT_BLUETOOTH_A2DP'", S24 Ultra
    # session 4e9c9333; the same default on S23 and S23 Ultra up to 0.4.55).
    # One UI's own policy file (the _sec or _base one its audioserver loads, with
    # Samsung's bluetooth module) goes into the guest's vendor/etc/audio
    # (vendor/etc where there is none) under Xiaomi's name, through a read-only
    # overlay on a small tmpfs as for Nothing's ringtones: One UI's /vendor is
    # not touched. Relative xi:include hrefs are made absolute, since the copy
    # no longer sits next to the files they name. ONEOS_GUEST_APM_XML=<vendor
    # file> picks the file, ONEOS_GUEST_APM_XML=0 leaves HyperOS's default.
    APM_X="${ONEOS_GUEST_APM_XML:-}"
    APM_A2DP=0
    if [ "$APM_X" != 0 ] && ! "$BB" grep -rqs 'android.hardware.audio.core' /vendor/etc/vintf/; then
        if [ -z "$APM_X" ]; then
            SKU=$(getprop ro.boot.product.vendor.sku)
            # 0.4.63: Qualcomm's SKU file first. HyperOS's parser rejected Samsung's
            # _sec and _base files ("APM::Serializer: deserialize: bad type 00000000",
            # "Could not load audio policy ... -22") and fell back to setDefault, whose
            # streams have a maximum index of 0: every app's volume maths was 0/0 and
            # SystemUI's volume slider crashed on NaN (S23 a8d01e17 and 36e46e14, Flip5
            # fbd248fc). The QCOM file is the format Xiaomi's own derives from, and
            # ColorOS's AOSP parser loads it on the same phones (S23 Ultra 7d694dd5).
            # 0.4.87: without a SKU file (the Exynos phones) Samsung's plain file
            # before its _sec and _base ones. The parser stops at the _sec file's
            # Samsung-only device type AUDIO_DEVICE_IN_2MIC ("bad type", -22) there
            # too: volume stuck at the maximum, no headset, no Bluetooth audio (A35
            # 8aeb6707, A16 5G c9cd977d). The plain file is plain AOSP, the one
            # ColorOS loads on the same phones; apm_copy adds the A2DP outputs it
            # lacks.
            for f in ${SKU:+/vendor/etc/audio/sku_${SKU}_qssi/audio_policy_configuration.xml /vendor/etc/audio/sku_$SKU/audio_policy_configuration.xml} \
                /vendor/etc/audio_policy_configuration.xml \
                /vendor/etc/audio_policy_configuration_sec.xml /vendor/etc/audio_policy_configuration_base.xml; do
                [ -f "$f" ] && { APM_X=$f; break; }
            done
            [ "$APM_X" = /vendor/etc/audio_policy_configuration.xml ] && APM_A2DP=1
        fi
        APM_D=/vendor/etc/audio
        [ -d "$ROOTFS$APM_D" ] || APM_D=/vendor/etc
        APM_OV="$STAGE/hyperos_apm"
        if [ -z "$APM_X" ] || [ ! -f "$APM_X" ]; then
            echo "!!! WARNING: HyperOS audio policy: no vendor policy file; HyperOS keeps its default (speaker only, no Bluetooth audio)"
        elif mount | grep -q " $ROOTFS$APM_D type overlay"; then
            echo "HyperOS audio policy: overlay on $APM_D already there"
        else
            mkdir -p "$APM_OV" && { mount | grep -q " $APM_OV " || $BB mount -t tmpfs -o size=2m,mode=755 tmpfs "$APM_OV"; } &&
                $BB mount --make-private "$APM_OV" 2>/dev/null
            rm -rf "$APM_OV/up" && mkdir -p "$APM_OV/up" &&
                apm_copy "$APM_X" "$APM_OV/up/audio_policy_configuration_mi.xml" $APM_A2DP &&
                chown -R 0:0 "$APM_OV/up" && chmod 755 "$APM_OV/up" && chmod 644 "$APM_OV/up/audio_policy_configuration_mi.xml"
            $BB chcon -R u:object_r:vendor_configs_file:s0 "$APM_OV/up" 2>/dev/null || true
            if [ -s "$APM_OV/up/audio_policy_configuration_mi.xml" ] &&
               $BB mount -t overlay overlay -o "ro,lowerdir=$APM_OV/up:$ROOTFS$APM_D" "$ROOTFS$APM_D"; then
                echo "HyperOS audio policy: $APM_X as $APM_D/audio_policy_configuration_mi.xml (no AIDL audio HAL)${APM_NOTE:+; $APM_NOTE}${APM_USB:+; $APM_USB}"
            else
                echo "!!! WARNING: HyperOS audio policy: the overlay on $APM_D was refused; HyperOS keeps its default (speaker only, no Bluetooth audio)"
            fi
        fi
    fi
fi

# The other systems read AOSP's file name: /odm/etc, /vendor/etc/audio/sku_<sku>
# and then /vendor/etc/audio_policy_configuration.xml. Where that last one is
# the file the guest gets and apm_copy has Bluetooth A2DP or USB outputs to
# add to it (see there: Exynos, HIDL audio HAL), the copy is bound over it in
# the guest's vendor, from a small tmpfs as above; One UI's /vendor is not
# touched and a file apm_copy adds nothing to is left alone.
# ONEOS_GUEST_APM_A2DP=0 and ONEOS_GUEST_APM_USB=0 together leave the vendor's
# file; each alone leaves out its own outputs.
GAPM=/vendor/etc/audio_policy_configuration.xml
if [ ! -e "$MIUI_FW/miui-services.jar" ] && [ ! -L "$MIUI_FW/miui-services.jar" ] \
   && { [ "${ONEOS_GUEST_APM_A2DP:-1}" = 1 ] || [ "${ONEOS_GUEST_APM_USB:-1}" = 1 ]; } \
   && [ -f "$GAPM" ] && [ -f "$ROOTFS$GAPM" ] && [ ! -L "$ROOTFS$GAPM" ] \
   && ! "$BB" grep -rqs 'android.hardware.audio.core' /vendor/etc/vintf/; then
    SKU=$(getprop ro.boot.product.vendor.sku)
    GAPM_OV="$STAGE/guest_apm"
    GAPM_FIRST=""
    for f in /odm/etc/audio_policy_configuration.xml ${SKU:+/vendor/etc/audio/sku_$SKU/audio_policy_configuration.xml}; do
        [ -e "$ROOTFS$f" ] && { GAPM_FIRST=$f; break; }
    done
    if [ -n "$GAPM_FIRST" ]; then
        echo "Guest audio policy: the guest reads $GAPM_FIRST; left alone"
    elif mount | grep -q " $ROOTFS$GAPM "; then
        echo "Guest audio policy: copy on $GAPM already there"
    else
        mkdir -p "$GAPM_OV" && { mount | grep -q " $GAPM_OV " || $BB mount -t tmpfs -o size=2m,mode=755 tmpfs "$GAPM_OV"; } &&
            $BB mount --make-private "$GAPM_OV" 2>/dev/null
        if mount | grep -q " $GAPM_OV " && apm_copy "$GAPM" "$GAPM_OV/audio_policy_configuration.xml" 1; then
            if [ "$APM_ADDED" = 1 ]; then
                # What the copy has more, Bluetooth first, and what a refused bind costs.
                case "$APM_NOTE" in
                    "Bluetooth A2DP outputs added"*)
                        GAPM_SAID="$APM_NOTE${APM_USB:+; $APM_USB}"
                        GAPM_LOST="no Bluetooth audio${APM_USB:+, no USB audio}" ;;
                    *)
                        GAPM_SAID="$APM_USB${APM_NOTE:+; $APM_NOTE}"
                        GAPM_LOST="no USB audio" ;;
                esac
                chown 0:0 "$GAPM_OV/audio_policy_configuration.xml" && chmod 644 "$GAPM_OV/audio_policy_configuration.xml"
                $BB chcon u:object_r:vendor_configs_file:s0 "$GAPM_OV/audio_policy_configuration.xml" 2>/dev/null || true
                if $BB mount --bind "$GAPM_OV/audio_policy_configuration.xml" "$ROOTFS$GAPM"; then
                    $BB mount -o remount,ro,bind "$ROOTFS$GAPM" 2>/dev/null || true
                    echo "Guest audio policy: $GAPM with $GAPM_SAID (no AIDL audio HAL)"
                else
                    echo "!!! WARNING: guest audio policy: the bind on $GAPM was refused; the guest keeps the vendor's file ($GAPM_LOST)"
                fi
            else
                echo "Guest audio policy: $GAPM left as it is${APM_NOTE:+: $APM_NOTE}"
            fi
        else
            echo "!!! WARNING: guest audio policy: no copy of $GAPM could be made; the guest keeps the vendor's file"
        fi
    fi
fi

# ims-ext-common.jar with a 60 s QtiImsExtConnector bind retry instead of 500 ms
# (patches/qti_ims_ext_backoff.py). The guest skips Qualcomm's ims.apk (it needs
# persist.oplus.qspa.modem=enabled), so in run 34 com.android.phone's main thread
# retried bindService 6 times a second for the whole session.
# ONEOS_GUEST_IMS_EXT_BACKOFF=0 keeps ColorOS's jar.
if [ "${ONEOS_GUEST_IMS_EXT_BACKOFF:-1}" = 1 ] && [ -f "$STAGE/ims-ext-common_patched.jar" ] \
   && [ -f "$GUEST_PRODUCT/framework/ims-ext-common.jar" ]; then
    $BB umount -l "$GUEST_PRODUCT/framework/ims-ext-common.jar" 2>/dev/null || true
    $BB mount --bind "$STAGE/ims-ext-common_patched.jar" "$GUEST_PRODUCT/framework/ims-ext-common.jar"
    echo "Bound ims-ext-common_patched.jar -> $GUEST_PRODUCT/framework/ims-ext-common.jar"
fi

# nt-telephony-common.jar with extphonelib's dex alongside it as classes2.dex
# (scripts/make-overlays.sh). Nothing loads this one jar in a class loader of
# its own, and a class in it extends com.qti.extphone.ExtPhoneCallbackBase,
# which that loader could not otherwise see: com.android.phone died at every
# start and the guest had no telephony at all ("Emergency calls only", first
# Nothing run). ONEOS_GUEST_NT_TELEPHONY=0 keeps the image's own jar.
if [ "${ONEOS_GUEST_NT_TELEPHONY:-1}" = 1 ] && [ -f "$STAGE/nt-telephony-common_patched.jar" ] \
   && [ -f "$GUEST_SYSTEM_EXT/framework/nt-telephony-common.jar" ]; then
    chmod 644 "$STAGE/nt-telephony-common_patched.jar"
    $BB umount -l "$GUEST_SYSTEM_EXT/framework/nt-telephony-common.jar" 2>/dev/null || true
    $BB mount --bind "$STAGE/nt-telephony-common_patched.jar" "$GUEST_SYSTEM_EXT/framework/nt-telephony-common.jar"
    if [ "$(stat -c %d:%i "$GUEST_SYSTEM_EXT/framework/nt-telephony-common.jar" 2>/dev/null)" = \
         "$(stat -c %d:%i "$STAGE/nt-telephony-common_patched.jar")" ]; then
        echo "Bound nt-telephony-common_patched.jar -> $GUEST_SYSTEM_EXT/framework/nt-telephony-common.jar"
    else
        echo "!!! WARNING: nt-telephony-common_patched.jar is not in place; the guest will have no telephony"
    fi
fi

# Nothing OS's SystemUI with its quick settings panel drawn at the screen's own
# density on a panel of sw600dp and up (scripts/make-overlays.sh,
# patches/nothing_qs_density.py). Nothing lays the panel out as if every screen
# were 420 dp wide: on the Fold's inner panel that is 859 dpi, tiles twice the
# size and the lower half of the panel off the screen (Nothing runs 8 to 10).
# The cover and phones keep Nothing's value. One dex changed, the signing block
# as it was. ONEOS_GUEST_QS_DENSITY=0 keeps the image's own SystemUI.
QS_APK="$GUEST_SYSTEM_EXT/priv-app/SystemUI/SystemUI.apk"
if [ -f "$STAGE/SystemUI_patched.apk" ] && [ -f "$QS_APK" ]; then
    if [ "${ONEOS_GUEST_QS_DENSITY:-1}" = 1 ]; then
        chmod 644 "$STAGE/SystemUI_patched.apk"
        $BB chcon u:object_r:system_file:s0 "$STAGE/SystemUI_patched.apk" 2>/dev/null || true
        $BB umount -l "$QS_APK" 2>/dev/null || true
        $BB mount --bind "$STAGE/SystemUI_patched.apk" "$QS_APK" &&
            $BB mount -o remount,bind,ro "$STAGE/SystemUI_patched.apk" "$QS_APK" 2>/dev/null
        if [ "$(stat -c %d:%i "$QS_APK" 2>/dev/null)" = "$(stat -c %d:%i "$STAGE/SystemUI_patched.apk")" ]; then
            echo "Bound SystemUI_patched.apk -> $QS_APK (quick settings at the screen's density from sw600dp)"
        else
            echo "!!! WARNING: SystemUI_patched.apk is not in place; quick settings keep Nothing's own density"
        fi
    else
        echo "Quick settings density patch left out (ONEOS_GUEST_QS_DENSITY=0)"
    fi
fi

# ColorOS has no fingerprint ripples of its own: the wake glyph and the wave
# after a successful unlock are this patched SystemUI
# (switcher/patches/systemui-fingerprint-wave). Shipping the whole 127 MB APK
# is wasteful, so the set carries only the patched classes3.dex and the small
# repacker that appends it to the image's stock SystemUI — the same operation
# scripts/apk-replace-dex.py does on the build machine. The built APK lives in
# the guest's data, so it survives reboots and switches; it is rebuilt only
# when the stock APK or the patched dex changes. guest_start binds it and sets
# the 120 Hz floor.
WAVE_STAMP_DEX="$STAGE/data/local/tmp/SystemUI_wave.dex.sha256"
if [ -f "$STAGE/SystemUI_wave.dex" ] && [ -f "$STAGE/OneOSWaveRepack.dex" ] &&
   [ -f "$QS_APK" ] && [ ! -f "$STAGE/SystemUI_patched.apk" ] &&
   [ -f "$ROOTFS/system/framework/oplus-services.jar" ]; then
    wave_dst="$STAGE/data/local/tmp"
    mkdir -p "$wave_dst" || true
    wave_stock_size=$(stat -c %s "$QS_APK" 2>/dev/null)
    wave_stock_sha=$(sha256sum "$QS_APK" 2>/dev/null | awk '{print $1}')
    wave_dex_sha=$(sha256sum "$STAGE/SystemUI_wave.dex" 2>/dev/null | awk '{print $1}')
    if [ -f "$wave_dst/SystemUI_wave.apk" ] &&
       [ "$(cat "$wave_dst/SystemUI_wave.stock.sha256" 2>/dev/null)" = "$wave_stock_sha" ] &&
       [ "$(cat "$WAVE_STAMP_DEX" 2>/dev/null)" = "$wave_dex_sha" ]; then
        echo "Guest SystemUI: the fingerprint wave APK is up to date"
    else
        $BB umount -l "$QS_APK" 2>/dev/null || true
        # oneos_switch captured the host zygote's boot class paths before it
        # stopped the framework at [4b/6]; prefer them, and only look for a
        # live zygote when this script runs on its own.
        wave_env=
        if [ -n "${ONEOS_HOST_BOOTCLASSPATH:-}" ] && [ -n "${ONEOS_HOST_DEX2OATBOOTCLASSPATH:-}" ]; then
            wave_env="BOOTCLASSPATH=$ONEOS_HOST_BOOTCLASSPATH DEX2OATBOOTCLASSPATH=$ONEOS_HOST_DEX2OATBOOTCLASSPATH"
        else
            wave_zpid=$(pidof zygote64 2>/dev/null | awk '{print $1}')
            [ -n "$wave_zpid" ] || wave_zpid=$(pidof zygote 2>/dev/null | awk '{print $1}')
            [ -n "$wave_zpid" ] &&
                wave_env=$(tr '\0' '\n' < "/proc/$wave_zpid/environ" 2>/dev/null |
                    grep -e '^BOOTCLASSPATH=' -e '^DEX2OATBOOTCLASSPATH=')
        fi
        rm -f "$wave_dst/SystemUI_wave.apk"
        if [ -n "$wave_env" ] &&
           env $wave_env ANDROID_ROOT=/system ANDROID_DATA=/data \
               CLASSPATH="$STAGE/OneOSWaveRepack.dex" \
               /system/bin/app_process /system/bin com.oneos.wave.OneOSWaveRepack \
               "$QS_APK" classes3.dex "$STAGE/SystemUI_wave.dex" "$wave_dst/SystemUI_wave.apk"; then
            printf '%s\n' "$wave_dex_sha" > "$WAVE_STAMP_DEX"
            echo "Guest SystemUI: built the fingerprint wave APK from the stock SystemUI"
        else
            rm -f "$wave_dst/SystemUI_wave.apk"
            echo "!!! WARNING: could not build the fingerprint wave APK; the stock SystemUI has no wave"
        fi
    fi
    if [ -f "$wave_dst/SystemUI_wave.apk" ]; then
        printf '%s\n' "$wave_stock_size" > "$wave_dst/SystemUI_wave.stock.size"
        printf '%s\n' "$wave_stock_sha" > "$wave_dst/SystemUI_wave.stock.sha256"
        chmod 644 "$wave_dst/SystemUI_wave.apk" "$wave_dst"/SystemUI_wave.stock.* 2>/dev/null || true
        $BB chcon -h u:object_r:system_file:s0 "$wave_dst/SystemUI_wave.apk" 2>/dev/null || true
    fi
fi

# Nothing OS's launcher with more category boxes per row in the app drawer on
# a wide panel (scripts/make-overlays.sh, patches/nothing_launcher_drawer.py):
# two per row on any screen, sized from the width, gave boxes of about
# 1000 x 1100 px on the Fold's inner panel (Nothing run 11). The cover and
# phones keep two. ONEOS_GUEST_LAUNCHER_DRAWER=0 keeps the image's own launcher.
NL_APK="$GUEST_SYSTEM_EXT/priv-app/NothingLauncher3/NothingLauncher3.apk"
if [ -f "$STAGE/NothingLauncher3_patched.apk" ] && [ -f "$NL_APK" ]; then
    if [ "${ONEOS_GUEST_LAUNCHER_DRAWER:-1}" = 1 ]; then
        chmod 644 "$STAGE/NothingLauncher3_patched.apk"
        $BB chcon u:object_r:system_file:s0 "$STAGE/NothingLauncher3_patched.apk" 2>/dev/null || true
        $BB umount -l "$NL_APK" 2>/dev/null || true
        $BB mount --bind "$STAGE/NothingLauncher3_patched.apk" "$NL_APK" &&
            $BB mount -o remount,bind,ro "$STAGE/NothingLauncher3_patched.apk" "$NL_APK" 2>/dev/null
        if [ "$(stat -c %d:%i "$NL_APK" 2>/dev/null)" = "$(stat -c %d:%i "$STAGE/NothingLauncher3_patched.apk")" ]; then
            echo "Bound NothingLauncher3_patched.apk -> $NL_APK (drawer category boxes per row from the width)"
        else
            echo "!!! WARNING: NothingLauncher3_patched.apk is not in place; the drawer keeps two boxes per row"
        fi
    else
        echo "Launcher drawer patch left out (ONEOS_GUEST_LAUNCHER_DRAWER=0)"
    fi
fi

# HyperOS's wallpaper app with an unknown effect type allowed (scripts/
# make-overlays.sh, patches/hyperos_miwallpaper_null.py): on a one-panel phone
# it died on every start (0.4.32, Galaxy S25: no wallpaper at all).
# ONEOS_GUEST_MIWALLPAPER_FIX=0 keeps the image's own.
MIWP_APK="$GUEST_PRODUCT/app/MiWallpaper/MiWallpaper.apk"
if [ -f "$STAGE/MiWallpaper_patched.apk" ] && [ -f "$MIWP_APK" ] && [ "${ONEOS_GUEST_MIWALLPAPER_FIX:-1}" = 1 ]; then
    chmod 644 "$STAGE/MiWallpaper_patched.apk"
    $BB umount -l "$MIWP_APK" 2>/dev/null || true
    $BB mount --bind "$STAGE/MiWallpaper_patched.apk" "$MIWP_APK" &&
        $BB mount -o remount,bind,ro "$STAGE/MiWallpaper_patched.apk" "$MIWP_APK" 2>/dev/null
    if [ "$(stat -c %d:%i "$MIWP_APK" 2>/dev/null)" = "$(stat -c %d:%i "$STAGE/MiWallpaper_patched.apk")" ]; then
        echo "Bound MiWallpaper_patched.apk -> $MIWP_APK"
    else
        echo "!!! WARNING: MiWallpaper_patched.apk is not in place; the wallpaper app may not start on this phone"
    fi
fi

# HyperOS's preinstalled data apps (product/data-app: Weather, Downloads, Game
# Center, WPS, ...) load their native libraries from /data/app-lib/<app>/arm64,
# which Xiaomi's preinstaller fills on a Xiaomi phone's first boot. Its
# installers are stopped in the guest (they took system_server down, 0.4.32),
# so those folders stayed empty: "dlopen failed: library libxldownload.so /
# libmmkv.so not found", Weather's shell with no libweather_app.so (S25 Ultra,
# 0.4.33 report 04857daa). Each app's arm64 libraries are unpacked into the
# guest's own /data (the stage's) when its folder is missing or empty;
# ONEOS_GUEST_DATA_APP_LIBS=0 leaves them out.
if [ -d "$GUEST_PRODUCT/data-app" ] && [ "${ONEOS_GUEST_DATA_APP_LIBS:-1}" = 1 ] && [ -d "$STAGE/data" ] && [ ! -L "$STAGE/data" ]; then
    DAL="$STAGE/data/app-lib"
    if [ -L "$DAL" ]; then
        echo "HyperOS data apps: data/app-lib is a link, not made by OneOS; left alone"
    else
        mkdir -p "$DAL" && chown 1000:1000 "$DAL" && chmod 771 "$DAL"
        DAL_DONE=""; DAL_SAID=""
        for d in "$GUEST_PRODUCT"/data-app/*; do
            n=${d##*/}; a="$d/$n.apk"
            [ -f "$a" ] || continue
            t="$DAL/$n/arm64"
            [ -L "$DAL/$n" ] || [ -L "$t" ] && continue
            [ -n "$(ls -A "$t" 2>/dev/null)" ] && continue
            unzip -l "$a" 2>/dev/null | grep -q " lib/arm64-v8a/[^/]*\.so\$" || continue
            # 0.4.87: said before the first one. The step had no line until its end
            # (S23 HyperOS dd8e9734: the log of a first start stops right before it).
            [ -n "$DAL_SAID" ] || { DAL_SAID=1; echo "HyperOS data apps: unpacking native libraries (first start with these apps)"; }
            mkdir -p "$t" && $BB unzip -o -j -q "$a" 'lib/arm64-v8a/*.so' -d "$t" 2>/dev/null &&
                chown -R 1000:1000 "$DAL/$n" && chmod 755 "$DAL/$n" "$t" && chmod 644 "$t"/*.so &&
                DAL_DONE="$DAL_DONE $n"
        done
        $BB chcon -R u:object_r:apk_data_file:s0 "$DAL" 2>/dev/null || true
        echo "HyperOS data apps: native libraries unpacked for${DAL_DONE:- none (already there)}"
    fi
fi

# Signal bars: OplusSignalSmooth polls GET_SIGNAL_STRENGTH every 20 s with the
# screen on (scripts/make-overlays.sh, patches/guest_signal_poll.py). Run 34:
# Samsung's RIL sent the guest no signal strength indication after boot, so both
# SIMs kept the all-invalid value read right after RADIO_POWER on (no bars).
# ONEOS_GUEST_SIGNAL_POLL=0 keeps ColorOS's jar. Other images: INJ above.
GUEST_OTC="$GUEST_SYSTEM_EXT/framework/oplus-telephony-common.jar"
if [ "${ONEOS_GUEST_SIGNAL_POLL:-1}" = 1 ] && [ -f "$STAGE/oplus-telephony-common_patched.jar" ] && [ -f "$GUEST_OTC" ]; then
    $BB umount -l "$GUEST_OTC" 2>/dev/null || true
    $BB mount --bind "$STAGE/oplus-telephony-common_patched.jar" "$GUEST_OTC"
    echo "Bound oplus-telephony-common_patched.jar -> $GUEST_OTC"
fi
# Play services and the Play Store from One UI's copy (oneos_switch.sh took it
# before One UI stopped), bound over the image's my_product slots, for every
# ColorOS set (switcher/assets/guest_google.sh). Never stops the start: without
# a checked copy the guest starts without it.
STAGE="$STAGE" BB="$BB" /system/bin/sh "$STAGE/guest_google.sh" prepare ||
    echo "!!! guest_google.sh prepare failed; the guest starts without One UI's Play services"
# Galaxy Z Fold8 with the Find N6 set (n6-f8): its SystemUI and guest fixes
# (switcher/assets/fold8_coloros.sh). Does nothing for any other profile or set.
# After the system_ext overlay above: a bind made under system_ext before it is
# hidden by it (0.4.14 on the Z Fold8: SystemUI kept the image's, no fold layout).
STAGE="$STAGE" BB="$BB" /system/bin/sh "$STAGE/fold8_coloros.sh" prepare || exit 3
# Pull request #1's SystemUI reads oneos.unfold_transition for Android's unfold
# reveal (0.4.38). The Z Fold8 Ultra waited 2.0-2.2 s for its inner screen on every
# unfold with it, 0.1-1.0 s without (test3 against test4): off there, on elsewhere
# (the Z Fold8, as pull request #1 tested it). setprop oneos.unfold_transition 1 and
# a SystemUI restart turn it on for a session.
if [ "${ONEOS_PROFILE:-}" = f8u ]; then setprop oneos.unfold_transition 0; else setprop oneos.unfold_transition 1; fi
echo "Unfold reveal: oneos.unfold_transition=$(getprop oneos.unfold_transition)"
STAGE="$STAGE" BB="$BB" /system/bin/sh "$STAGE/fold8_pixel.sh" prepare || exit 3
# ColorOS feature switches the guest needs, added to com.oplus.features_config.xml
# in its system_ext, a feature file it already loads (the my_* feature files are
# only read with CUST_LEVEL_LIST, which OPPO's init sets):
# - multibits_dimming_support: the Settings brightness slider steps through the
#   222..8191 levels one by one instead of 0..255 steps (run 28: jumpy slider).
# - the form factor, ONEOS_GUEST_FORM=fold (default) | tablet | phone. The Find
#   N6 is a ColorOS foldable: with type.fold the launcher follows Android's fold
#   state (Samsung's open state 3 is not in OPPO's folded list 0,1,100,102) and
#   uses its unfolded layout. tablet = run 29 (OPPO's pad grid turned into 6x10
#   cells, 1265 px off screen); phone = run 28 (Recents crashed with scaleX=NaN
#   on swipe home). Never tablet and fold together.
# - feature_unfold_width_small_high, with fold (ONEOS_GUEST_UNFOLD_PORTRAIT=0
#   leaves it out): the Find N6's open panel is landscape at rotation 0, ours is
#   portrait (2256x2504). Without the switch SystemUI's side gesture swaps width
#   and height on a large fold screen (SideGestureConfiguration; run 30 log:
#   SideGesture mScreenWidth = 2504, mScreenHeight = 2256), so the right back
#   zone sat at x 2442..2504, off the 2256 px panel (run 31 diag_90 input.txt,
#   InvalidRegion) and back from the right edge never fired. Only SystemUI's
#   side gesture reads it (not the launcher, framework or services).
# - windowmode.compact, with fold (ONEOS_GUEST_COMPACT_WINDOW=0 leaves it out):
#   the Find N6 has it (my_product/etc/permissions/oplus.feature.android.xml,
#   not read here; run 32 Settings: hasFeature = false). It is all that tells
#   com.oplus.wallpapers it runs on a foldable (f0.w: this framework-res has
#   no config_lidControlsDisplayFold). Without it every page of the app
#   (BaseDefaultDensityActivity.getResources -> o.a) is laid out at a phone
#   density, shortest side = 360dp = 6.27 px/dp, while text stays at 3.0:
#   the 386dp My theme header was 2419 px tall and filled the first screen,
#   the cards had 100 px padding instead of 48 (run 32 all.log: iconCardView
#   632,100-1089,557, the cards only reached at scrollY 2232). In WMS it also
#   turns on OPPO's full compact window mode (compat mode, starting windows,
#   animations); the .lite variant was already on.
# - radio.support_5g (ONEOS_GUEST_5G=0 leaves it out): without it ColorOS
#   telephony picks 4G mode 22 and masks NR out (run 29: LTE only on SIM 2's carrier
#   while One UI showed 5G).
# - radio.support_dual_nr, only with support_5g (ONEOS_GUEST_DUAL_5G=0 leaves
#   it out): the Find N6 is a dual-5G phone (its my_product feature file
#   declares it, its build.prop sets ro.oplus.radio.dual_nr_enabled=true).
#   Without it ColorOS offers and allows 5G only on the mobile-data SIM and
#   puts the other SIM on 4G mode 22. Run 32: SIM 2 switched off and on moved
#   data to SIM 1, so SIM 2's Preferred network type list had only 4G and 3G
#   (OplusExportPreferredNetworkSettings: primarySlotId 0, isSupportDual5g
#   false). With it telephony turns its dual_nr_enabled persist feature on at
#   boot and both SIMs list 5G and default to mode 33, like One UI here
#   (dumpsys isub: user=840583, NR included, on both SIMs).
# - connectivity.region_CN (ONEOS_GUEST_WIFI_CN=0 leaves it out): the Find N6's
#   own /my_region feature file sets it, but my_* files are never read here.
#   The image's WirelessSettings is the domestic build: after Connect it keeps
#   its modal Connecting dialog up until the wifi service sends the sticky
#   android.net.wifi.DISABLE_ALERT_NETWORKS (state COMPLETED), and Back or
#   Cancel on that dialog removes the network it just added. Only
#   OplusWifiConnectionAlert sends it, and OplusWifiInjector creates it only
#   with region_CN. Run 32: connected and validated at 13:14:02, no such
#   broadcast and no OplusWifiConnectionAlert line all session, Back at
#   13:14:12 -> remove by config -> removeNetwork -> disconnected, nothing
#   saved; the dialog left open is the Settings page that could not be left.
#   It also turns on OplusWifi's other CN paths (self-cure, smart assistant).
#   CN images only: my_region/build.prop says ro.oplus.pipeline.region=CN in
#   the Find N6 and Find X9 Ultra CN builds; a global build (the X9U IN) has
#   the export WirelessSettings and keeps its own region.
FEAT="$GUEST_SYSTEM_EXT/etc/permissions/com.oplus.features_config.xml"
$BB umount -l "$FEAT" 2>/dev/null
FORM="${ONEOS_GUEST_FORM:-fold}"
case "$FORM" in fold|tablet|phone) ;; *) echo "WARNING: ONEOS_GUEST_FORM=$FORM unknown, using fold"; FORM=fold ;; esac
if [ -f "$FEAT" ]; then
    ADDED="oplus.software.display.multibits_dimming_support"
    # Galaxy Z Fold8, Find N6 (pull request #1): Live Alerts, AOD, fold animations,
    # separate wallpapers per panel and haptic sounds, as the Find N6 declares them.
    # 0.4.38: the Z Fold8 Ultra too wherever pull request #1's SystemUI is staged (the
    # global build ships its own AOD app, so no donor is needed for the AOD switch).
    if { [ "${ONEOS_PROFILE:-}" = f8 ] || { [ "${ONEOS_PROFILE:-}" = f8u ] && [ -f "$STAGE/Fold8SystemUI.apk" ]; }; } &&
       grep -q '^  "image": "coloros17-findn6",$' "$STAGE/.oneos_stage"; then
        ADDED="$ADDED oplus.software.support_fluid_entry oplus.software.fluid_replace_ntf"
        ADDED="$ADDED oplus.software.display.aod_support oplus.software.adaptive_smooth_animation"
        ADDED="$ADDED oplus.software.flexible_exchange_animation"
        # Stock Find N6: my_stock/etc/extension/com.oplus.oplus-feature.xml.
        # The container does not load that component's feature catalogue.
        ADDED="$ADDED oplus.software.flexible_freeform.support oplus.software.pocketstudio.support"
        ADDED="$ADDED oplus.software.wallpaper.separate_wallpaper_for_multi_display"
        ADDED="$ADDED oplus.software.audio.haptic_channel_support"
    elif [ "$FORM" = fold ] && grep -q '^  "image": "coloros17-findn6",$' "$STAGE/.oneos_stage"; then
        # The same on every other fold with the Find N6 build (0.4.36: the Z Fold8
        # Ultra, Fold7, Fold6, Fold5), except AOD and haptics, which go with the
        # Fold8 set's donor AOD app and its own tuning.
        ADDED="$ADDED oplus.software.support_fluid_entry oplus.software.fluid_replace_ntf"
        ADDED="$ADDED oplus.software.adaptive_smooth_animation oplus.software.flexible_exchange_animation"
        ADDED="$ADDED oplus.software.flexible_freeform.support oplus.software.pocketstudio.support"
        ADDED="$ADDED oplus.software.wallpaper.separate_wallpaper_for_multi_display"
    fi
    # Every ColorOS image (0.4.36): the UI features its own stock catalogue
    # (my_stock/etc/extension/com.oplus.oplus-feature.xml) declares, which the
    # container does not load: Live Alerts, the smooth and exchange animations,
    # flexible freeform windows, Pocket Studio, separate wallpapers. The Find X9
    # Ultra builds list the first five. Its other entries (memory, swap, binder,
    # preload and boot tuning) expect OPPO's kernel and stay out.
    # ONEOS_GUEST_STOCK_FEATURES=0 leaves them out.
    STOCKF="$ROOTFS/my_stock/etc/extension/com.oplus.oplus-feature.xml"
    if [ "${ONEOS_GUEST_STOCK_FEATURES:-1}" = 1 ] && [ -f "$STOCKF" ] && [ ! -L "$STOCKF" ]; then
        SF=""
        for x in oplus.software.support_fluid_entry oplus.software.fluid_replace_ntf oplus.software.adaptive_smooth_animation \
                 oplus.software.flexible_exchange_animation oplus.software.flexible_freeform.support oplus.software.pocketstudio.support \
                 oplus.software.wallpaper.separate_wallpaper_for_multi_display; do
            grep -q "name=\"$x\"" "$STOCKF" || continue
            case " $ADDED " in *" $x "*) ;; *) ADDED="$ADDED $x"; SF="$SF ${x#oplus.software.}" ;; esac
        done
        echo "ColorOS features from the image's stock catalogue:${SF:- none new}"
    fi
    # Circle to Search (0.4.38): the global builds switch OPPO's long press on the
    # gesture handle to Google's contextual search with my_product's
    # feature_contextualsearch_navbarhidden*.xml, which the container does not load
    # either (no Circle to Search, F8U test10). Only those files' features.
    CS=""
    for f in "$ROOTFS"/my_product/etc/extension/feature_contextualsearch_*.xml; do
        [ -f "$f" ] && [ ! -L "$f" ] || continue
        for x in $(sed -n 's/.*<oplus-feature name="\(oplus\.software\.[a-z0-9_.]*\)".*/\1/p' "$f"); do
            case " $ADDED " in *" $x "*) ;; *) ADDED="$ADDED $x"; CS="$CS ${x#oplus.software.}" ;; esac
        done
    done
    [ -z "$CS" ] || echo "ColorOS contextual search features from my_product:$CS"
    # Always-On Display (build 116; owner and reports, 11-11: no AOD in ColorOS on the
    # S24+ and the S25 Ultra). OPPO's framework names its doze service only with
    # oplus.software.display.aod_support (AmbientDisplayConfiguration
    # .ambientDisplayComponent), which a Find or OnePlus phone declares in a my_*
    # catalogue the container does not load. Without it the dream manager has no doze
    # component (dumpsys dreams "getDozeComponent()=null" in every Find X9 Ultra IN and
    # OxygenOS 16 report, on every phone; the Find N6 build on the Z Fold8 Ultra, which
    # gets the switch above, has SystemUI's DozeService there): the guest never dozes
    # and its Settings offer no AOD. Declared where this phone's panel does AOD in One
    # UI (its floating feature, or the panel's low-power node; an LCD phone has
    # neither) and the image has OPPO's AOD app. The Find N6 build keeps its rules
    # above. ONEOS_GUEST_AOD=0 leaves it out.
    AODF=oplus.software.display.aod_support
    if ! grep -q '^  "image": "coloros17-findn6",$' "$STAGE/.oneos_stage" 2>/dev/null; then
        case " $ADDED " in *" $AODF "*) ;; *)
            HAOD=""
            if grep -q '<SEC_FLOATING_FEATURE_FRAMEWORK_CONFIG_AOD_ITEM>[^<]' /system/etc/floating_feature.xml 2>/dev/null; then
                HAOD="One UI has AOD here"
            elif [ -e /sys/class/lcd/panel/alpm ]; then
                HAOD="the panel has a low-power mode"
            fi
            AODAPP=""
            APL="$STAGE/data/system/packages.list"
            if [ -f "$APL" ] && [ ! -L "$APL" ] && grep -q '^com\.oplus\.aod ' "$APL"; then
                AODAPP="com.oplus.aod installed"
            else
                for d in "$ROOTFS"/my_*/app/Aod* "$ROOTFS"/my_*/priv-app/Aod* "$GUEST_SYSTEM_EXT"/app/Aod* "$GUEST_SYSTEM_EXT"/priv-app/Aod*; do
                    [ -d "$d" ] && [ ! -L "$d" ] || continue
                    AODAPP="${d#"$ROOTFS"}"; break
                done
                if [ -z "$AODAPP" ]; then
                    for f in "$ROOTFS"/my_*/etc/extension/*.xml; do
                        [ -f "$f" ] && [ ! -L "$f" ] && grep -q "name=\"$AODF\"" "$f" || continue
                        AODAPP="declared in ${f#"$ROOTFS"}"; break
                    done
                fi
            fi
            if [ "${ONEOS_GUEST_AOD:-1}" != 1 ]; then
                echo "ColorOS Always-On Display: left off (ONEOS_GUEST_AOD=${ONEOS_GUEST_AOD:-})"
            elif [ -z "$HAOD" ]; then
                echo "ColorOS Always-On Display: left off (One UI has no AOD on this phone)"
            elif [ -z "$AODAPP" ]; then
                echo "ColorOS Always-On Display: left off (no AOD app in this image)"
            else
                ADDED="$ADDED $AODF"
                echo "ColorOS Always-On Display: on ($HAOD; $AODAPP)"
            fi ;;
        esac
    fi
    case "$FORM" in
        fold) ADDED="$ADDED oplus.hardware.type.fold"
            if [ "${ONEOS_GUEST_UNFOLD_PORTRAIT:-1}" = 1 ]; then
                ADDED="$ADDED oplus.software.feature_unfold_width_small_high"
            fi
            if [ "${ONEOS_GUEST_COMPACT_WINDOW:-1}" = 1 ]; then
                ADDED="$ADDED oplus.software.windowmode.compact"
            fi ;;
        tablet) ADDED="$ADDED oplus.hardware.type.tablet" ;;
    esac
    if [ "${ONEOS_GUEST_5G:-1}" = 1 ]; then
        ADDED="$ADDED oplus.software.radio.support_5g"
        if [ "${ONEOS_GUEST_DUAL_5G:-1}" = 1 ]; then
            ADDED="$ADDED oplus.software.radio.support_dual_nr"
        fi
    fi
    GUEST_REGION=$(sed -n 's/^ro\.oplus\.pipeline\.region=//p' "$ROOTFS/my_region/build.prop" 2>/dev/null | head -n 1)
    if [ "${ONEOS_GUEST_WIFI_CN:-1}" = 1 ] && [ "$GUEST_REGION" = CN ]; then
        ADDED="$ADDED oplus.software.connectivity.region_CN"
    else
        echo "Wi-Fi region_CN switch left out (image region ${GUEST_REGION:-unknown})"
    fi
    { grep -v '</oplus-config>' "$FEAT"
      for f in $ADDED; do echo "    <oplus-feature name=\"$f\"/>"; done
      echo '</oplus-config>'; } > "$STAGE/oplus_features_config.xml"
    $BB mount --bind "$STAGE/oplus_features_config.xml" "$FEAT" &&
        echo "Bound ColorOS feature switches (form $FORM): $ADDED"
    # The Theme Store (0.4.42, owner: "no theme store in ColorOS for fold8u build"). The
    # Find N6 global build ships it (com.oplus.themestore, my_stock/priv-app/KeKeThemeSpace),
    # but its product config my_product/etc/config/app_v2.xml disables it
    # (<disable pkg="com.oplus.themestore" priority="7"/>, no layer enables it), so
    # OplusAppConfigManager ignored the package at every boot and it was never installed.
    # A copy without that one line is bound over the file; the rest of OPPO's app
    # config (Pictorial, the browser, Game Center...) stays as the image has it.
    # ONEOS_GUEST_THEME_STORE=0 leaves the file alone.
    if [ "${ONEOS_GUEST_THEME_STORE:-1}" = 1 ]; then
        for f in "$ROOTFS"/my_*/etc/config/app_v2.xml; do
            [ -f "$f" ] && [ ! -L "$f" ] && grep -q '<disable pkg="com.oplus.themestore"' "$f" || continue
            part=${f#"$ROOTFS"/}; part=${part%%/*}
            out="$STAGE/oneos_${part}_app_v2.xml"
            grep -v '<disable pkg="com.oplus.themestore"' "$f" > "$out" && chmod 644 "$out" &&
                $BB mount --bind "$out" "$f" &&
                echo "ColorOS Theme Store: the disable line in /$part/etc/config/app_v2.xml left out"
        done
        # 0.4.47: the store's DeviceChecker reads ro.product.brand, which is the Galaxy's here,
        # and closed with "is a customised app, not compatible with this device" on every
        # phone (owner's Z Fold8 Ultra on the Find N6 build, testers on the Find X9 Ultra
        # builds). The set's KeKeThemeSpace_patched.apk is the image's APK with that check
        # answering yes, and (0.4.48) reporting brand OPPO and model CPH2765 to OPPO's theme server,
        # which sent no themes for samsung (only a search icon; scripts/apk-replace-dex.py on
        # classes4.dex and classes5.dex, OPPO's signing block kept). The
        # Find N6 global and Find X9 Ultra IN builds ship the same APK (SHA-256 below); on any
        # other build the image's own stays.
        TS_APK="$ROOTFS/my_stock/priv-app/KeKeThemeSpace/KeKeThemeSpace.apk"
        TS_ORIG=496ca751d42793811dfd4bf18bf6f6884e5dfe8909ecf451dff94cecca2cff6a
        [ -f "$STAGE/KeKeThemeSpace_patched.apk" ] && $BB umount -l "$TS_APK" 2>/dev/null
        if [ -f "$STAGE/KeKeThemeSpace_patched.apk" ] && [ -f "$TS_APK" ] && [ ! -L "$TS_APK" ] &&
           [ "$(sha256sum "$TS_APK" 2>/dev/null | cut -d' ' -f1)" != $TS_ORIG ]; then
            echo "ColorOS Theme Store: this image's KeKeThemeSpace.apk is another build; its own stays (brand check on)"
        elif [ -f "$STAGE/KeKeThemeSpace_patched.apk" ] && [ -f "$TS_APK" ] && [ ! -L "$TS_APK" ]; then
            chmod 644 "$STAGE/KeKeThemeSpace_patched.apk"
            $BB chcon u:object_r:system_file:s0 "$STAGE/KeKeThemeSpace_patched.apk" 2>/dev/null || true
            $BB mount --bind "$STAGE/KeKeThemeSpace_patched.apk" "$TS_APK" &&
                $BB mount -o remount,bind,ro "$STAGE/KeKeThemeSpace_patched.apk" "$TS_APK" 2>/dev/null
            if [ "$(stat -c %d:%i "$TS_APK" 2>/dev/null)" = "$(stat -c %d:%i "$STAGE/KeKeThemeSpace_patched.apk")" ]; then
                echo "ColorOS Theme Store: KeKeThemeSpace_patched.apk bound (no brand check, OPPO to its server)"
            else
                echo "!!! WARNING: KeKeThemeSpace_patched.apk is not in place; the Theme Store refuses this phone's brand"
            fi
        fi
    fi
    # UniRender off on non-Qualcomm phones (0.4.43): ColorOS draws the launcher through
    # SurfaceFlinger's UniRenderSurface with a buffer usage Samsung's Exynos gralloc refuses
    # ("[S.LSI_GRALLOC] request input size is invalid", "dequeue buffer failed -22", about
    # 120 a second), so the home screen showed no icons (S24 Exynos 2a1eab9c, A56 3efc1847).
    # A copy of the image's switch list with func_switch 0 is bound over it; a cloud copy in
    # the guest's data (a higher version would win) is removed. Qualcomm phones keep it.
    # ONEOS_GUEST_UNIRENDER=1 keeps it everywhere.
    if [ "${ONEOS_GUEST_UNIRENDER:-0}" != 1 ] && [ "$(getprop ro.soc.manufacturer)" != QTI ]; then
        UR=""
        for f in "$ROOTFS"/my_*/etc/sys_global_uni_render_list.xml "$ROOTFS"/my_*/etc/*/sys_global_uni_render_list.xml; do
            [ -f "$f" ] && [ ! -L "$f" ] && grep -q '<func_switch value="1"' "$f" || continue
            part=${f#"$ROOTFS"/}; part=${part%%/*}
            out="$STAGE/oneos_${part}_uni_render_list.xml"
            sed 's/<func_switch value="1"/<func_switch value="0"/' "$f" > "$out" && chmod 644 "$out" &&
                $BB mount --bind "$out" "$f" && UR="$UR /${f#"$ROOTFS"/}"
        done
        rm -f "$STAGE/data/oplus/os/config/sys_global_uni_render_list.xml" 2>/dev/null
        echo "ColorOS UniRender: off on this $(getprop ro.soc.manufacturer) phone (${UR:+bound over$UR}${UR:-no switch list in the image})"
    fi
fi
# The guest's /oem, built in $STAGE/oem and bound over the image's. /oem is
# empty in the images (ColorOS and Pixel) and scanned by the guest's
# PackageManagerService as a system partition (PackagePartitions: oem has an
# app and an overlay folder, no priv-app), so what is in it counts as
# preinstalled:
# - overlay/OneOSWallpapersFoldGrid.apk, fold form only. "Home screen, Lock
#   screen & style" (com.oplus.wallpapers): with type.fold the app takes its
#   Find N6 inner-screen page, a 4x4 grid where every card is 2x2 = half the
#   panel (run 30, "too zoomed in"; not density or compat scaling: the app
#   draws 2256x2504 at 408 dpi). This static RRO (make-overlays.sh) makes the
#   grid 8x2. ONEOS_GUEST_WALLPAPER_GRID=0 keeps ColorOS's own layout.
# - overlay/OneOSPixelStatusBar.apk, a guest with Pixel's SystemUIGoogle or
#   Infinity-X's AOSP SystemUI (never ColorOS's SystemUI). Run 42: the battery sat 47-60 px further from
#   the right edge than the clock from the left, on both panels; the corner
#   padding Pixel's own vendor overlay gives is 0dp on Samsung's vendor, the
#   privacy dot padding 20dp. This static RRO (make-overlays.sh,
#   switcher/overlays/pixel_statusbar) makes both 8dp.
#   ONEOS_GUEST_STATUSBAR_PADDING=0 leaves it out.
# - overlay/OneOSPhoneInjection.apk, with the signal poll only (INJ=1 above:
#   oneos-telephony.jar in place on a read-only system_ext). Run 43: no bars on
#   either SIM. This static RRO (make-overlays.sh,
#   switcher/overlays/phone_injection) gives TeleService the injection config
#   that names the jar. ONEOS_GUEST_SIGNAL_POLL=0 leaves it out.
# - app/OneOSGuest/OneOSGuest.apk, every guest: OneOS inside the guest
#   (app-android/guest), "Back to One UI" from its screen or its Quick Settings
#   tile. A plain system app, not privileged, no permission: it writes a
#   request file in its own data folder, which oneos_switch.sh's watcher
#   takes. ONEOS_GUEST_APP=0 leaves it out.
$BB umount -l "$ROOTFS/oem" 2>/dev/null
rm -rf "$STAGE/oem"
OEM_FILES=""
if [ "$FORM" = fold ] && [ "${ONEOS_GUEST_WALLPAPER_GRID:-1}" = 1 ] && [ -f "$STAGE/OneOSWallpapersFoldGrid.apk" ]; then
    mkdir -p "$STAGE/oem/overlay" &&
        cp "$STAGE/OneOSWallpapersFoldGrid.apk" "$STAGE/oem/overlay/" &&
        chmod 755 "$STAGE/oem" "$STAGE/oem/overlay" && chmod 644 "$STAGE/oem/overlay/OneOSWallpapersFoldGrid.apk" &&
        OEM_FILES="$OEM_FILES overlay/OneOSWallpapersFoldGrid.apk"
fi
# Infinity-X's AOSP SystemUI takes it too (0.4.33); never ColorOS's (it has
# oplus-telephony-common.jar, and make-overlays.sh builds the RRO for its sets
# only from SystemUIGoogle or an AOSP SystemUI).
if [ -f "$STAGE/OneOSPixelStatusBar.apk" ] && { [ -f "$GUEST_SYSTEM_EXT/priv-app/SystemUIGoogle/SystemUIGoogle.apk" ] ||
     { [ -f "$GUEST_SYSTEM_EXT/priv-app/SystemUI/SystemUI.apk" ] && [ ! -f "$GUEST_SYSTEM_EXT/framework/oplus-telephony-common.jar" ]; }; }; then
    if [ "${ONEOS_GUEST_STATUSBAR_PADDING:-1}" = 1 ]; then
        mkdir -p "$STAGE/oem/overlay" &&
            cp "$STAGE/OneOSPixelStatusBar.apk" "$STAGE/oem/overlay/" &&
            chmod 755 "$STAGE/oem" "$STAGE/oem/overlay" && chmod 644 "$STAGE/oem/overlay/OneOSPixelStatusBar.apk" &&
            OEM_FILES="$OEM_FILES overlay/OneOSPixelStatusBar.apk"
    else
        echo "Pixel status bar overlay left out (ONEOS_GUEST_STATUSBAR_PADDING=0)"
    fi
fi
# AOD for a Pixel guest (switcher/overlays/pixel_doze): Pixel's doze service and
# "AOD available", which a Pixel has in its vendor overlay and a guest on One
# UI's vendor had not (getDozeComponent()=null). Static, so the dream manager
# has them at boot. ONEOS_GUEST_DOZE=0 leaves it out.
if [ -f "$STAGE/OneOSPixelDoze.apk" ] && [ -f "$GUEST_SYSTEM_EXT/priv-app/SystemUIGoogle/SystemUIGoogle.apk" ]; then
    if [ "${ONEOS_GUEST_DOZE:-1}" = 1 ]; then
        mkdir -p "$STAGE/oem/overlay" &&
            cp "$STAGE/OneOSPixelDoze.apk" "$STAGE/oem/overlay/" &&
            chmod 755 "$STAGE/oem" "$STAGE/oem/overlay" && chmod 644 "$STAGE/oem/overlay/OneOSPixelDoze.apk" &&
            OEM_FILES="$OEM_FILES overlay/OneOSPixelDoze.apk"
    else
        echo "Pixel AOD overlay left out (ONEOS_GUEST_DOZE=0)"
    fi
fi
# Quick settings on a tablet-width panel: the split (two column) shade in
# portrait too, which Nothing OS's SystemUI only has a landscape value for
# (scripts/make-overlays.sh). Under sw600dp, so the cover keeps the phone
# shade. ONEOS_GUEST_TABLET_QS=0 leaves the image's own values.
if [ -f "$STAGE/OneOSTabletQs.apk" ]; then
    if [ "${ONEOS_GUEST_TABLET_QS:-1}" = 1 ]; then
        mkdir -p "$STAGE/oem/overlay" &&
            cp "$STAGE/OneOSTabletQs.apk" "$STAGE/oem/overlay/" &&
            chmod 755 "$STAGE/oem" "$STAGE/oem/overlay" && chmod 644 "$STAGE/oem/overlay/OneOSTabletQs.apk" &&
            OEM_FILES="$OEM_FILES overlay/OneOSTabletQs.apk"
    else
        echo "Tablet quick settings overlay left out (ONEOS_GUEST_TABLET_QS=0)"
    fi
fi
# Nothing OS's About phone with this phone's picture, cameras and the cards
# Nothing shows only on its own phones (switcher/overlays/nothing_about*): the
# Z Fold8 Ultra's, and (0.4.35) the Z Fold8's, the S26 Ultra's, the Z Flip8's
# and the S26's (also the S26+'s) from the owner's product shots, each with
# its lenses; all but the Folds' with the processor's whole name. 0.4.36,
# until their own pictures: the Z Fold7 and Fold6 the Fold8 Ultra's page (three
# rear lenses, cover and inner), the S25 and S24 Ultra the S26 Ultra's, the S25
# and S25+ the S26's.
# ONEOS_GUEST_NT_ABOUT=0 leaves Nothing's page as it is.
case "${ONEOS_PROFILE:-f8u}" in
    f8u|f7|f6) NT_ABOUT=OneOSNtAbout.apk ;;
    f8) NT_ABOUT=OneOSNtAboutFold8.apk ;;
    s-ultra-8850|s-ultra-8750|s-ultra-8650) NT_ABOUT=OneOSNtAboutS26U.apk ;;
    flip*) NT_ABOUT=OneOSNtAboutFlip.apk ;;
    *) NT_ABOUT=OneOSNtAboutPhone.apk ;;
esac
if [ -f "$STAGE/$NT_ABOUT" ] && [ -f "$GUEST_SYSTEM_EXT/framework/nt-telephony-common.jar" ] && [ "${ONEOS_GUEST_NT_ABOUT:-1}" = 1 ]; then
    mkdir -p "$STAGE/oem/overlay" &&
        cp "$STAGE/$NT_ABOUT" "$STAGE/oem/overlay/" &&
        chmod 755 "$STAGE/oem" "$STAGE/oem/overlay" && chmod 644 "$STAGE/oem/overlay/$NT_ABOUT" &&
        OEM_FILES="$OEM_FILES overlay/$NT_ABOUT"
fi
# One UI's brightness range for the slider (switcher/overlays/
# samsung_brightness_range): Samsung's composer takes the float as the panel's
# backlight, and Nothing OS's own range (0.0354 to 1.0) put its lowest step near
# 70 nits and its highest at the panel's 2600-nit peak (Nothing run 23).
# Nothing images for now. ONEOS_GUEST_BRIGHTNESS_RANGE=0 keeps the image's.
if [ -f "$STAGE/OneOSBrightnessRange.apk" ] && [ -f "$GUEST_SYSTEM_EXT/framework/nt-telephony-common.jar" ] &&
   [ "${ONEOS_GUEST_BRIGHTNESS_RANGE:-1}" = 1 ]; then
    mkdir -p "$STAGE/oem/overlay" &&
        cp "$STAGE/OneOSBrightnessRange.apk" "$STAGE/oem/overlay/" &&
        chmod 755 "$STAGE/oem" "$STAGE/oem/overlay" && chmod 644 "$STAGE/oem/overlay/OneOSBrightnessRange.apk" &&
        OEM_FILES="$OEM_FILES overlay/OneOSBrightnessRange.apk"
fi
# Essential Space from a double press of the power key, for a Nothing image
# (switcher/overlays/nothing_essential_key): Nothing opens it with its own
# Essential key, which no Galaxy has. Any phone; the double-tap camera gesture
# goes with it. ONEOS_GUEST_NT_ESSENTIAL_KEY=0 leaves the power key alone.
if [ -f "$STAGE/OneOSNtEssentialKey.apk" ] && [ -d "$GUEST_PRODUCT/overlayfs_origin/system/noth/priv-app/EssentialSpace" ] &&
   [ "${ONEOS_GUEST_NT_ESSENTIAL_KEY:-1}" = 1 ]; then
    mkdir -p "$STAGE/oem/overlay" &&
        cp "$STAGE/OneOSNtEssentialKey.apk" "$STAGE/oem/overlay/" &&
        chmod 755 "$STAGE/oem" "$STAGE/oem/overlay" && chmod 644 "$STAGE/oem/overlay/OneOSNtEssentialKey.apk" &&
        OEM_FILES="$OEM_FILES overlay/OneOSNtEssentialKey.apk"
fi
# Per-panel display cutout, the Z Fold (F8U) only: the ids and the hole in it
# are this phone's, and on another phone the named displays would match nothing
# and every panel would fall back to the default path. The inner panel has no
# cutout here, so without this the guest put the cover's punch hole on it
# (scripts/make-overlays.sh). ONEOS_GUEST_FOLD_CUTOUT=0 leaves it out.
if [ -f "$STAGE/OneOSFoldCutout.apk" ] && [ "$FORM" = fold ] && [ "${ONEOS_PROFILE:-f8u}" = f8u ]; then
    if [ "${ONEOS_GUEST_FOLD_CUTOUT:-1}" = 1 ]; then
        mkdir -p "$STAGE/oem/overlay" &&
            cp "$STAGE/OneOSFoldCutout.apk" "$STAGE/oem/overlay/" &&
            chmod 755 "$STAGE/oem" "$STAGE/oem/overlay" && chmod 644 "$STAGE/oem/overlay/OneOSFoldCutout.apk" &&
            OEM_FILES="$OEM_FILES overlay/OneOSFoldCutout.apk"
    else
        echo "Fold cutout overlay left out (ONEOS_GUEST_FOLD_CUTOUT=0)"
    fi
elif [ -f "$STAGE/OneOSFoldCutout.apk" ]; then
    echo "Fold cutout overlay left out (profile ${ONEOS_PROFILE:-f8u}, form $FORM: its panel ids are the Z Fold Ultra's)"
fi
# Pixel wallpaper metadata is normalized in guest_start.sh on every start.
# Pixel on the Fold8 / Fold8 Ultra: the unfold transition's boot flags, read by
# SystemUI and the launcher at start (pixel-f8: Fold8PixelUnfold.apk, which also
# has the Fold8's 48dp bar and AOD; pixel-f8u: OneOSPixelUnfold.apk, the gates only).
UNFOLD_RRO=""
if [ "${ONEOS_PROFILE:-}" = f8 ] && grep -q '^  "set": "pixel-f8",$' "$STAGE/.oneos_stage"; then
    UNFOLD_RRO=Fold8PixelUnfold.apk
elif [ "${ONEOS_PROFILE:-}" = f8u ] && grep -q '^  "set": "pixel-f8u",$' "$STAGE/.oneos_stage"; then
    UNFOLD_RRO=OneOSPixelUnfold.apk
fi
if [ -n "$UNFOLD_RRO" ] && [ -f "$STAGE/$UNFOLD_RRO" ]; then
    mkdir -p "$STAGE/oem/overlay" &&
        cp "$STAGE/$UNFOLD_RRO" "$STAGE/oem/overlay/" &&
        chmod 755 "$STAGE/oem" "$STAGE/oem/overlay" && chmod 644 "$STAGE/oem/overlay/$UNFOLD_RRO" &&
        OEM_FILES="$OEM_FILES overlay/$UNFOLD_RRO"
fi
if [ $INJ = 1 ]; then
    # In /oem, not in the read-only system_ext layer: run 10 (Nothing OS 5.0)
    # ordered the static overlays system_ext < product < vendor < oem, so from
    # system_ext ours lost to Nothing's TelephonyResCommon_Sys.apk (product),
    # whose Qualcomm factory then crash-looped com.android.phone (no
    # org.codeaurora.ims on its class path): no SIM at all. /oem came last.
    mkdir -p "$STAGE/oem/overlay" &&
        cp "$STAGE/OneOSPhoneInjection.apk" "$STAGE/oem/overlay/" &&
        chmod 755 "$STAGE/oem" "$STAGE/oem/overlay" && chmod 644 "$STAGE/oem/overlay/OneOSPhoneInjection.apk" &&
        OEM_FILES="$OEM_FILES overlay/OneOSPhoneInjection.apk" &&
        echo "Signal poll: TelephonyComponentFactory injection (oneos-telephony.jar), GET_SIGNAL_STRENGTH every 20 s with the screen on"
fi
if [ "${ONEOS_GUEST_APP:-1}" = 1 ]; then
    mkdir -p "$STAGE/data/oneos_bootui"
    cp "$STAGE/boot_status.sh" "$STAGE/data/oneos_bootui/boot_status.sh"
    chmod 644 "$STAGE/data/oneos_bootui/boot_status.sh"
    GUEST_APP_APK="$STAGE/OneOSGuest.apk"
    [ ! -f "$STAGE/guest_manager.apk" ] || GUEST_APP_APK="$STAGE/guest_manager.apk"
    # One integrated OneOS app in every guest, including when guest root is off.
    rm -f "$STAGE/oem/app/OneOSGuestRoot/GuestRoot.apk"
    if [ -f "$GUEST_APP_APK" ]; then
        mkdir -p "$STAGE/oem/app/OneOSGuest" &&
            cp "$GUEST_APP_APK" "$STAGE/oem/app/OneOSGuest/OneOSGuest.apk" &&
            chmod 755 "$STAGE/oem" "$STAGE/oem/app" "$STAGE/oem/app/OneOSGuest" &&
            chmod 644 "$STAGE/oem/app/OneOSGuest/OneOSGuest.apk" &&
            OEM_FILES="$OEM_FILES app/OneOSGuest/OneOSGuest.apk"
    else
        echo "No guest OneOS APK: Volume Up + Volume Down still return"
    fi
fi
if [ -n "$OEM_FILES" ]; then
    # A stage copy, not a bind of host data: safe to label like a system file.
    $BB chcon -h -R u:object_r:system_file:s0 "$STAGE/oem" 2>/dev/null || true
    $BB mount --bind "$STAGE/oem" "$ROOTFS/oem" &&
        echo "Bound guest /oem -> $ROOTFS/oem:$OEM_FILES"
fi
# vivo: the same files bound onto the system_ext mount points made with its
# overlay (VIVO_SE, above); one folder per package, as the scan wants.
for d in $VIVO_SE; do
    n=${d##*/}
    src="$STAGE/oem/$d"
    case "$d" in overlay/*)
        src="$STAGE/oem/vivo/$n"
        if [ -f "$STAGE/oem/overlay/$n.apk" ]; then
            mkdir -p "$src" && cp "$STAGE/oem/overlay/$n.apk" "$src/" &&
                chmod 755 "$STAGE/oem/vivo" "$src" && chmod 644 "$src/$n.apk" &&
                $BB chcon -R u:object_r:system_file:s0 "$STAGE/oem/vivo" 2>/dev/null
        fi ;;
    esac
    if [ -f "$src/$n.apk" ] && [ -d "$GUEST_SYSTEM_EXT/$d" ] && $BB mount --bind "$src" "$GUEST_SYSTEM_EXT/$d"; then
        $BB mount --make-rslave "$GUEST_SYSTEM_EXT/$d" 2>/dev/null || true
        echo "vivo: $n.apk in /system_ext/$d (vivo does not scan /oem)"
    else
        echo "vivo: $n.apk not placed in /system_ext/$d (not in this session's /oem, or no mount point)"
    fi
done
# ColorOS apps whose SELinux domain the host policy does not have (run 31: 35
# zygote aborts in 6 minutes, crash/system/dropbox). The guest's system_ext and
# product seapp_contexts give OPPO apps their own domains
# (oplus_assistantscreen_app, oplus_phonemanager_app, oplus_backuprestore_app,
# oplus_game_service, oplus_instant_local_service, ...), but the loaded policy is
# Samsung's: selinux_android_setcontext fails with EINVAL, permissive or not
# (the kernel rejects a context with an unknown type), and the forked zygote
# child aborts. The launcher's card channel (pcs_server) pulls a provider of
# com.coloros.assistantscreen, so it was restarted every ~10 s (the AMS start
# timeout) for the whole session, each time with a tombstone and a dropbox
# entry; com.coloros.sceneservice was killed with it each time ("depends on
# provider ... in dying proc", run 30). Comment out every rule whose domain= or
# type= the host policy lacks: such a rule can never apply here. Those apps
# then get AOSP's generic rules (untrusted_app, priv_app, platform_app,
# system_app), the same ones the host's installd uses for their data (One UI's
# seapp_contexts has no OPPO rules either). Whole lines only, so the files stay
# parseable; plat_seapp_contexts (system_server's rule, same AOSP build as the
# host) is left alone. The host's types come from its CIL files, so this
# follows whatever policy the phone has. ONEOS_GUEST_SEAPP=0 keeps ColorOS's files.
SEAPP_FILES="$GUEST_SYSTEM_EXT/etc/selinux/system_ext_seapp_contexts $GUEST_PRODUCT/etc/selinux/product_seapp_contexts"
for f in $SEAPP_FILES; do $BB umount -l "$f" 2>/dev/null; done
if [ "${ONEOS_GUEST_SEAPP:-1}" = 1 ]; then
    HOST_TYPES="$STAGE/host_sepolicy_types.txt"
    for c in /system/etc/selinux/*.cil /system_ext/etc/selinux/*.cil /product/etc/selinux/*.cil \
        /vendor/etc/selinux/*.cil /odm/etc/selinux/*.cil; do
        case "$c" in *debug*) continue ;; esac
        [ -f "$c" ] && cat "$c"
    done | awk '$1 == "(type" || $1 == "(typealias" { t = $2; sub(/\).*$/, "", t); print t }' | sort -u > "$HOST_TYPES"
    SEAPP_OK=1
    for t in untrusted_app priv_app platform_app system_app app_data_file privapp_data_file system_app_data_file; do
        grep -qx "$t" "$HOST_TYPES" || SEAPP_OK=0
    done
    if [ "$SEAPP_OK" != 1 ]; then
        echo "WARNING: host SELinux types unreadable ($(wc -l < "$HOST_TYPES") found); guest seapp_contexts unchanged"
    else
        for f in $SEAPP_FILES; do
            [ -f "$f" ] || continue
            out="$STAGE/oneos_$(basename "$f")"
            awk -v types="$HOST_TYPES" '
                BEGIN { while ((getline t < types) > 0) known[t] = 1 }
                /^[ \t]*#/ || NF == 0 { print; next }
                {
                    bad = ""
                    for (i = 1; i <= NF; i++)
                        if ($i ~ /^(domain|type)=/) {
                            v = $i; sub(/^[a-z]*=/, "", v)
                            if (!(v in known)) bad = bad " " v
                        }
                    if (bad != "") print "# OneOS: host policy lacks" bad ": " $0
                    else print
                }' "$f" > "$out" || { echo "WARNING: could not rewrite $f; left as is"; continue; }
            chmod 644 "$out"
            $BB chcon u:object_r:seapp_contexts_file:s0 "$out" 2>/dev/null ||
                $BB chcon u:object_r:system_file:s0 "$out" 2>/dev/null || true
            $BB mount --bind "$out" "$f" &&
                echo "Bound $(basename "$f"): $(grep -c '^# OneOS: host policy lacks' "$out") rule(s) with types the host policy lacks commented out"
            echo "    types missing: $(grep '^# OneOS: host policy lacks' "$out" | cut -d: -f2 | sed 's/^ host policy lacks //' | tr ' ' '\n' | sort -u | tr '\n' ' ')"
        done
    fi
fi
# framework_patched.jar: a Pixel guest's framework.jar with One UI's camera
# transaction codes (patches/pixel_camera_abi.py). Listed in guards.txt and
# checked above, so a stage that has the jar binds the one the set was built
# with or does not start.
if [ -f "$STAGE/framework_patched.jar" ]; then
    $BB umount -l "$ROOTFS/system/framework/framework.jar" 2>/dev/null || true
    $BB mount --bind "$STAGE/framework_patched.jar" "$ROOTFS/system/framework/framework.jar"
    echo "Bound framework_patched.jar -> $ROOTFS/system/framework/framework.jar"
fi
# telephony-common_patched.jar: the SMS service centre as an international
# number (patches/guest_smsc_international.py; Samsung's radio answers it in
# the modem's AT form). Only built for sets that already bind a patched
# framework.jar, so the boot image is not given up for it alone. Listed in
# guards.txt and checked above.
if [ -f "$STAGE/telephony-common_patched.jar" ] && [ -f "$ROOTFS/system/framework/telephony-common.jar" ]; then
    $BB umount -l "$ROOTFS/system/framework/telephony-common.jar" 2>/dev/null || true
    $BB mount --bind "$STAGE/telephony-common_patched.jar" "$ROOTFS/system/framework/telephony-common.jar"
    echo "Bound telephony-common_patched.jar -> $ROOTFS/system/framework/telephony-common.jar"
fi
# libcamera_client_patched.so, libcameracompatbilityinfo_patched.so: the guest's
# native camera client (legacy camera API, NDK camera2) with One UI's codes
# (patches/pixel_camera_native.py); guards.txt lists them, checked above.
# libsensorservice_patched.so (vivo OriginOS): One UI's light and hinge events as
# scalars (make-overlays.sh; system_server aborted on the first one).
for pair in libcamera_client_patched.so:libcamera_client.so libcameracompatbilityinfo_patched.so:libcameracompatbilityinfo.so \
            libsensorservice_patched.so:libsensorservice.so; do
    if [ -f "$STAGE/${pair%%:*}" ]; then
        $BB umount -l "$ROOTFS/system/lib64/${pair#*:}" 2>/dev/null || true
        $BB mount --bind "$STAGE/${pair%%:*}" "$ROOTFS/system/lib64/${pair#*:}"
        echo "Bound ${pair%%:*} -> $ROOTFS/system/lib64/${pair#*:}"
    fi
done
# libcomposer_ext_patched.so (vivo OriginOS, MediaTek): its ComposerExt client
# asked 21 times, 100 ms apart, for MediaTek's IComposerExt (no such service on
# a Samsung vendor) on every display power-mode change, stalling SurfaceFlinger
# 2.2 s each time (seventh run: about 25 s from cover to inner). The patched one
# gives up after the first try (make-overlays.sh, pinned to the image's build).
HCE="$GUEST_SYSTEM_EXT/lib64/libcomposer_ext.so"
if [ -f "$STAGE/libcomposer_ext_patched.so" ] && [ -f "$HCE" ] && [ ! -L "$HCE" ]; then
    chmod 644 "$STAGE/libcomposer_ext_patched.so"
    $BB chcon u:object_r:system_lib_file:s0 "$STAGE/libcomposer_ext_patched.so" 2>/dev/null || true
    $BB umount -l "$HCE" 2>/dev/null || true
    $BB mount --bind "$STAGE/libcomposer_ext_patched.so" "$HCE" &&
        echo "Bound libcomposer_ext_patched.so -> $HCE (one IComposerExt try)"
fi
# MediaTek's frame hooks in every app's libgui (libged_kpi.so: the GPU's /proc/ged;
# libdisp_dejitter.so: the display's frame timestamps) fail on a Qualcomm phone,
# every frame, with three to six log lines (tenth CN run: 157 000 lines in 12 minutes,
# logd dropping 1 219 times). libgui loads both with dlopen and runs without them;
# nothing links them. Hidden from the guest (vivo images; ONEOS_GUEST_MTK_FRAME_HOOKS=1
# keeps them).
if [ -e "$ROOTFS/system/framework/vivo-services.jar" ] && [ "${ONEOS_GUEST_MTK_FRAME_HOOKS:-0}" != 1 ]; then
    : > "$STAGE/oneos_empty_lib" && chmod 644 "$STAGE/oneos_empty_lib"
    for l in libged_kpi.so libdisp_dejitter.so; do
        for d in "$GUEST_SYSTEM_EXT/lib64" "$GUEST_SYSTEM_EXT/lib"; do
            [ -f "$d/$l" ] && [ ! -L "$d/$l" ] || continue
            $BB umount -l "$d/$l" 2>/dev/null || true
            $BB mount --bind "$STAGE/oneos_empty_lib" "$d/$l" && echo "Hid guest ${d#"$ROOTFS"/}/$l (MediaTek frame hook without its driver)"
        done
    done
fi
if [ -f "$STAGE/libaudio_aidl_conversion_common_cpp_patched.so" ]; then
    $BB umount -l "$ROOTFS/system/lib64/libaudio_aidl_conversion_common_cpp.so" 2>/dev/null || true
    $BB mount --bind "$STAGE/libaudio_aidl_conversion_common_cpp_patched.so" "$ROOTFS/system/lib64/libaudio_aidl_conversion_common_cpp.so"
    echo "Bound libaudio_aidl_conversion_common_cpp_patched.so"
fi
if [ -f "$STAGE/libaudioclient_aidl_conversion_patched.so" ]; then
    $BB umount -l "$ROOTFS/system/lib64/libaudioclient_aidl_conversion.so" 2>/dev/null || true
    $BB mount --bind "$STAGE/libaudioclient_aidl_conversion_patched.so" "$ROOTFS/system/lib64/libaudioclient_aidl_conversion.so"
    echo "Bound libaudioclient_aidl_conversion_patched.so"
fi
if [ -f "$STAGE/framework-res_patched.apk" ]; then
    $BB umount -l "$ROOTFS/system/framework/framework-res.apk" 2>/dev/null || true
    $BB mount --bind "$STAGE/framework-res_patched.apk" "$ROOTFS/system/framework/framework-res.apk"
    echo "Bound framework-res_patched.apk -> $ROOTFS/system/framework/framework-res.apk"
fi

if [ -f "$STAGE/PermissionController_patched.apk" ]; then
    chmod 644 "$STAGE/PermissionController_patched.apk"
    PERM_APK=$(find "$ROOTFS/apex/com.android.permission" -name "PermissionController.apk" 2>/dev/null | head -n 1)
    if [ -n "$PERM_APK" ]; then
        $BB umount -l "$PERM_APK" 2>/dev/null || true
        $BB mount --bind "$STAGE/PermissionController_patched.apk" "$PERM_APK"
        echo "Bound PermissionController_patched.apk -> $PERM_APK"
    fi
fi



echo "=== 5. $(date +%T) Setting up Isolated Data & Bridges ==="
mkdir -p "$STAGE/data/adb" "$STAGE/data/apex" "$STAGE/data/dalvik-cache/arm64"

# Give the guest the host's authorised ADB keys. The container has no
# AdbDebuggingManager (the guest system_server registers no "adb" service), so a
# guest adbd or wireless-debugging session cannot answer an authorisation prompt;
# pre-seeding the keys is the only way it can accept this machine silently.
# Pre-seed adb_enabled=1 into the guest's settings before its system_server runs.
# The in-boot fix (in fix_app_dirs.sh) only lands once the framework is up, but
# UsbDeviceManager drops the adb USB function within seconds of system_server
# starting -- which is why adb dies right after the guest boots and macOS stops
# seeing the phone entirely. Writing the XML now keeps the gadget stable through
# the whole boot.
GSET="$STAGE/data/system/users/0/settings_global.xml"
# OneOS: only ever change the value of an existing entry, and only in a text
# XML file. Inserting <setting id="adb_enabled" ...> gave the entry a non-numeric
# id; ColorOS's SettingsProvider then failed to parse settings_global.xml, moved
# it aside and aborted system_server ("No fallback file found"). Any line a
# previous run inserted is removed again. If there is no entry yet, the UI
# activator's "settings put global adb_enabled 1" sets it once the guest is up.
# Each key is checked after the edit and that one edit is undone if the file
# did not come out as expected.
seed_settings() {
    f=$1; label=$2; shift 2
    [ -f "$f" ] && [ "$(head -c 5 "$f")" = "<?xml" ] || { echo "Guest $label: no text settings file, not seeded"; return; }
    for kv in "$@"; do
        k=${kv%=*}; v=${kv#*=}
        cp -f "$f" "$f.oneos-prev"
        if grep -q "name=\"$k\" " "$f"; then
            if grep "name=\"$k\" " "$f" | grep -q ' value="'; then
                sed -i "/name=\"$k\" /s/ value=\"[^\"]*\"/ value=\"$v\"/" "$f"
            else
                sed -i "s/ name=\"$k\" / name=\"$k\" value=\"$v\" /" "$f"
            fi
        else
            NEXT_ID=$(( $(grep -o ' id="[0-9]*"' "$f" | tr -dc '0-9\n' | sort -n | tail -1) + 1 ))
            sed -i "s#</settings>#<setting id=\"$NEXT_ID\" name=\"$k\" value=\"$v\" package=\"android\" />\n</settings>#" "$f"
        fi
        if [ "$(grep -c "name=\"$k\" value=\"$v\"" "$f")" != 1 ] || ! tail -c 32 "$f" | grep -q '</settings>'; then
            cp -f "$f.oneos-prev" "$f"
            echo "WARNING: Guest $label: could not set $k=$v, left as it was"
        else
            echo "Guest $label: $k=$v"
        fi
    done
    rm -f "$f.oneos-prev"
}
# A first ColorOS boot that died part-way leaves some of user 0's settings
# files and not the others. SettingsProvider then takes the upgrade path and
# crashes on the missing one in every later session (Galaxy S25, 2026-10-23:
# "No settings state /data/system/users/0/settings_global.xml", "Upgrading
# settings for user: 0 ... from version: 201", then a NullPointerException in
# SettingsRegistry$UpgradeController.onUpgradeLocked and system_server gone).
# Such a partial set is moved aside (never deleted) so ColorOS writes all three
# fresh. A stage that ran fine has all three; one never booted has none.
U0="$STAGE/data/system/users/0"
s_have=0; s_miss=0
for n in settings_global.xml settings_secure.xml settings_system.xml; do
    if [ -f "$U0/$n" ]; then s_have=$((s_have + 1)); else s_miss=$((s_miss + 1)); fi
done
if [ "$s_have" -gt 0 ] && [ "$s_miss" -gt 0 ]; then
    s_aside="$U0/oneos-partial-settings-$(date +%s)"
    if mkdir -p "$s_aside"; then
        for n in settings_global.xml settings_secure.xml settings_system.xml; do
            for f in "$U0/$n" "$U0/$n.fallback" "$U0/$n.bak"; do
                [ -f "$f" ] && mv -f "$f" "$s_aside/"
            done
        done
        echo "Guest settings: a partial set from an earlier first boot ($s_have of 3 files) moved to ${s_aside#$STAGE/}; ColorOS writes all three fresh"
    else
        echo "WARNING: guest settings are a partial set ($s_have of 3 files) and could not be moved aside"
    fi
fi
sed -i '/<setting id="adb_enabled" /d' "$GSET" 2>/dev/null
# adb_enabled=1: without it the guest's UsbDeviceManager drops adb from the
# USB gadget seconds after its system_server starts.
# OneOS: only when One UI has USB debugging on (oneos_switch.sh saved it
# in host_adb_on); a phone without it does not get adb from the guest either.
# data/oneos_host_adb tells fix_app_dirs.sh the same.
HOST_ADB=$(cat "$STAGE/host_adb_on" 2>/dev/null)
ADB_SEED=""
if [ "$HOST_ADB" = 1 ]; then
    ADB_SEED=adb_enabled=1; touch "$STAGE/data/oneos_host_adb"
else
    rm -f "$STAGE/data/oneos_host_adb"
fi
echo "Guest adb: $([ "$HOST_ADB" = 1 ] && echo 'on (One UI has USB debugging on)' || echo 'left alone (One UI has USB debugging off)')"
# auto_time=0 / auto_time_zone=0: the clock is the host's, and ColorOS's time
# detection set it to 1 Jan 2026 during a session.
# device_provisioned=1 / user_setup_complete=1: the image has no setup wizard,
# but with them at 0 ColorOS keeps the device in "setup" mode: the phone app
# opens its APN list over the home screen, Quick Settings, notifications and
# the home gesture stay off, and mobile data is forced off. Set before boot so
# no setup-complete observer fires (one writes persist.sys.* props).
# launcher_support_card_no_padding=1 (what the launcher itself writes): with it
# missing, Launcher.onCreate queries its own provider on the main thread, a
# suspect for the onCreate hang in runs 23-25.
# With Google services presented (GMS_WANT, top) the two provisioned keys are
# left to Pixel's setup wizard, which sets both when it finishes: a stage it
# has set up already has them, one it has not keeps its wizard.
# vivo OriginOS: the only wizard is vivo's (com.vivo.setupwizard), and it stops at
# its vivo account step (fifth CN run: nothing there, no way on). Setup is marked
# done before boot, Google services or not; a Google account can be added in
# Settings. vivo's wizard also reads setup_wizard_has_run (Secure, then System).
# ONEOS_GUEST_VIVO_SETUP=1 keeps the wizard.
PROV_GLOBAL=device_provisioned=1
PROV_SECURE=user_setup_complete=1
if [ "$GMS_WANT" = 1 ]; then
    if [ -f "$ROOTFS/system/framework/vivo-services.jar" ] && [ "${ONEOS_GUEST_VIVO_SETUP:-0}" != 1 ]; then
        PROV_SECURE="user_setup_complete=1 setup_wizard_has_run=1"
        echo "Guest setup: marked done (vivo's setup wizard stops at its vivo account; ONEOS_GUEST_VIVO_SETUP=1 keeps it)"
    else
        PROV_GLOBAL=""; PROV_SECURE=""
        echo "Guest setup: device_provisioned / user_setup_complete left to Pixel's setup wizard (Google services presented)"
    fi
fi
seed_settings "$GSET" settings_global $ADB_SEED auto_time=0 auto_time_zone=0 $PROV_GLOBAL launcher_support_card_no_padding=1
[ -z "$PROV_SECURE" ] || seed_settings "$STAGE/data/system/users/0/settings_secure.xml" settings_secure $PROV_SECURE

echo "=== 5.1 $(date +%T) settings seeded ==="
# The switcher's return combo (hold Volume Up + Volume Down 3 s, read on the
# host) is also Android's accessibility shortcut, and ColorOS aims that at
# TalkBack: settings_secure id 26, accessibility_shortcut_target_service from
# SettingsProvider's config_preinstalled_screen_reader_service, written at the
# guest's first boot. Run 34 (all.log): the first hold showed the shortcut's
# warning dialog at 16:43:59.409 and saved accessibility_shortcut_dialog_shown=1;
# the host watcher acted only at 16:44:06, so the user held the keys again, and
# with the dialog seen the shortcut needs only 1 s: TalkBack came on at
# 16:44:02.839 (enabled_accessibility_services, accessibility_enabled,
# touch_exploration_enabled: ids 1145-1148 in the staged file, all four new in
# run 34). An empty target turns the shortcut off (a missing one
# would fall back to config_defaultAccessibilityService): KeyGestureController
# then has no rule for the chord and the keys stay volume keys. Done only while
# the target is still the factory TalkBack one, so a shortcut picked later in
# Settings is kept; TalkBack goes off with it only when it is the sole enabled
# service, as the shortcut left it. ONEOS_GUEST_A11Y_SHORTCUT=1 keeps
# ColorOS's shortcut.
SSET="$STAGE/data/system/users/0/settings_secure.xml"
if [ "${ONEOS_GUEST_A11Y_SHORTCUT:-0}" != 1 ] &&
   grep -q 'name="accessibility_shortcut_target_service" value="com\.google\.android\.marvin\.talkback/' "$SSET" 2>/dev/null; then
    A11Y="accessibility_shortcut_target_service="
    grep -q 'name="accessibility_shortcut_dialog_shown" value="1"' "$SSET" && A11Y="$A11Y accessibility_shortcut_dialog_shown=0"
    grep -q -E 'name="enabled_accessibility_services" value="com\.google\.android\.marvin\.talkback/[^":]*TalkBackService"' "$SSET" &&
        A11Y="$A11Y enabled_accessibility_services= accessibility_enabled=0 touch_exploration_enabled=0"
    seed_settings "$SSET" settings_secure $A11Y
fi
A11T=$(sed -n 's/.* name="accessibility_shortcut_target_service" value="\([^"]*\)".*/\1/p' "$SSET" 2>/dev/null | head -n 1)
A11S=$(sed -n 's/.* name="enabled_accessibility_services" value="\([^"]*\)".*/\1/p' "$SSET" 2>/dev/null | head -n 1)
echo "Guest accessibility shortcut target: ${A11T:-none}; enabled services: ${A11S:-none}"

# Mobile data follows One UI's switch (oneos_switch.sh [4/6] saved it).
# Run 33: the guest's mobile_data and mobile_data2 were 0 (sub 2 = SIM 2 is
# the guest's data SIM, multi_sim_data_call=2) while One UI had mobile_data=1,
# so ColorOS never set up a data call (DSMGR-1 mIsDataEnabled=false all
# session), SIM 2's NR leg came without a data context id (all.log
# 14:42:04-14:42:12, mContextIds=[]) and the 5G icon could not show. On Wi-Fi
# nothing changes: mobile_data_always_on is 0, so no cellular data call while
# Wi-Fi is the default network. ONEOS_GUEST_MOBILE_DATA=0 leaves the guest's
# own values (the switch in ColorOS's Quick Settings is kept across sessions).
HMD=$(cat "$STAGE/host_mobile_data" 2>/dev/null)
GDDS=$(sed -n 's/.*name="multi_sim_data_call" value="\([0-9][0-9]*\)".*/\1/p' "$GSET" 2>/dev/null | head -1)
# 0.4.87: HyperOS keeps the switch per SIM slot, not per subscription: on a
# MIUI ROM DataSettingsManager.isUserDataEnabled reads mobile_data<phone id>
# (telephony-common.jar). S25 Ultra ba784a19: the SIM was sub 1 in slot 0, so
# mobile_data1=1 switched the empty slot 1 on and left the SIM's slot off
# ("Data disallowed reasons: DATA_DISABLED" all session, no data call asked).
# Both slots, as HyperOS's own switch sets them; with two SIMs its framework
# turns the one that is not the data SIM off again. No guest data sub needed.
# A first start has no settings file yet: HyperOS starts with the switch off.
if [ "${ONEOS_GUEST_MOBILE_DATA:-1}" = 1 ] && [ "$HMD" = 1 ] &&
    { [ -e "$MIUI_FW/miui-services.jar" ] || [ -L "$MIUI_FW/miui-services.jar" ]; }; then
    seed_settings "$GSET" settings_global mobile_data=1 mobile_data0=1 mobile_data1=1
elif [ "${ONEOS_GUEST_MOBILE_DATA:-1}" = 1 ] && [ "$HMD" = 1 ] && [ -n "$GDDS" ]; then
    seed_settings "$GSET" settings_global mobile_data=1 "mobile_data$GDDS=1"
else
    echo "Guest mobile data: left as it is (One UI: ${HMD:-unknown}, guest data sub: ${GDDS:-none})"
fi
# A binary-XML settings file (Pixel: starts with ABX) cannot be read here:
# run 43 printed "not forced" for it every time. The UI activator sets and
# logs the guest's density then (oneos_switch.sh, run 44).
if [ "$(head -c 3 "$SSET" 2>/dev/null)" = ABX ]; then
    echo "Guest display size: binary settings, set by the UI activator"
else
    echo "Guest display size: $(grep -o 'name="display_density_forced" value="[^"]*"' "$SSET" 2>/dev/null || echo 'not forced')"
fi
echo "=== 5.2 $(date +%T) accessibility, mobile data, density ==="
# ColorOS's cover screen on a fold (owner, 0.4.10 on the Z Fold8 Ultra: "outer
# display looks 720p", "set to high, still looks blurry"). The guest drew it at
# the panel's full 1080 x 2520 (SurfaceFlinger: 1:1 projection, full-size
# window buffers), but at Samsung's shared ro.sf.lcd_density 480, a 360 dp wide
# phone layout, about 14% larger than One UI's 420 on the same 422 dpi panel.
# The cover gets its own forced density in the guest's display_settings.xml,
# keyed like WindowManager keys it (the uniqueId, or port:<n> when the file
# says identifier 1), so the inner panel and Settings.Secure
# display_density_forced (display 0 at boot, whichever panel it is) stay as
# they are: auto = the panel's real dpi down to a multiple of 20 (420 here,
# also one of ColorOS's own display sizes), only under the base density, and
# never over a size chosen in the guest (an entry with forcedDensity).
# ONEOS_GUEST_COVER_DENSITY=off|auto|<dpi 120-640>.
# HyperOS too (run 10, owner: "feels like a zoomed in fold display like the
# dynamic island stuff is going out of bounds"): its cover ran at 480, 360 dp,
# and the Dynamic Island's window went past the right edge. Not the Pixel
# image, whose own cover is a 480 phone layout.
DSET="$STAGE/data/system/display_settings.xml"
CVD=$(cat "$STAGE/host_cover_display" 2>/dev/null)
CDEN="${ONEOS_GUEST_COVER_DENSITY:-auto}"
CV_GUEST=""
[ -e "$ROOTFS/system/framework/oplus-services.jar" ] && CV_GUEST=ColorOS
{ [ -e "$ROOTFS/system_ext/framework/miui-services.jar" ] || [ -e "$ROOTFS/system/system_ext/framework/miui-services.jar" ]; } && CV_GUEST=HyperOS
if [ "$FORM" != fold ] || [ -z "$CV_GUEST" ] || [ "$CDEN" = off ]; then
    :
elif [ "$(echo "$CVD" | wc -w)" != 5 ]; then
    echo "Cover density: not set (the cover panel was not read)"
else
    set -- $CVD
    CV_UID=$1 CV_PORT=$2 CV_XDPI=$5
    BASE=$(getprop ro.sf.lcd_density)
    case "$CDEN" in
        auto) CDEN=$((CV_XDPI / 20 * 20)) ;;
        [1-9][0-9][0-9]) [ "$CDEN" -ge 120 ] && [ "$CDEN" -le 640 ] || CDEN=0 ;;
        *) CDEN=0 ;;
    esac
    if [ "$CDEN" -lt 120 ] 2>/dev/null || [ -z "$BASE" ] || [ "$CDEN" -ge "$BASE" ]; then
        echo "Cover density: left at ${BASE:-the base} (${ONEOS_GUEST_COVER_DENSITY:-auto} gives $CDEN for $CV_XDPI dpi)"
    else
        mkdir -p "$STAGE/data/system"
        DTXT="$STAGE/display_settings.txt"
        rm -f "$DTXT"
        if [ ! -s "$DSET" ]; then
            printf '%s\n' "<?xml version='1.0' encoding='utf-8' standalone='yes' ?>" '<display-settings>' '</display-settings>' > "$DTXT"
        elif [ "$(head -c 3 "$DSET")" = ABX ]; then
            abx2xml "$DSET" "$DTXT" 2>/dev/null || rm -f "$DTXT"
        else
            cp "$DSET" "$DTXT"
        fi
        IDT=$(sed -n 's/.*<config identifier="\([0-9]*\)".*/\1/p' "$DTXT" /vendor/etc/display_settings.xml 2>/dev/null | head -n 1)
        CV_NAME=$CV_UID; [ "$IDT" = 1 ] && CV_NAME="port:$CV_PORT"
        if [ ! -s "$DTXT" ] || ! grep -q '</display-settings>' "$DTXT"; then
            echo "Cover density: not set (display_settings.xml not readable)"
        elif grep "<display name=\"$CV_NAME\"" "$DTXT" | grep -q 'forcedDensity='; then
            echo "Cover density: $(grep "<display name=\"$CV_NAME\"" "$DTXT" | sed -n 's/.*forcedDensity="\([0-9]*\)".*/\1/p') kept (chosen in $CV_GUEST)"
        else
            if grep -q "<display name=\"$CV_NAME\"" "$DTXT"; then
                sed -i "s|<display name=\"$CV_NAME\"|<display name=\"$CV_NAME\" forcedDensity=\"$CDEN\"|" "$DTXT"
            else
                awk -v e="<display name=\"$CV_NAME\" forcedDensity=\"$CDEN\" />" '/<\/display-settings>/ { print e } { print }' "$DTXT" > "$DTXT.new" && mv -f "$DTXT.new" "$DTXT"
            fi
            CTX=$(ls -Z "$DSET" 2>/dev/null | awk '{ print $1 }')
            case "$CTX" in u:object_r:*) ;; *) CTX=u:object_r:system_data_file:s0 ;; esac
            if grep -q "forcedDensity=\"$CDEN\"" "$DTXT" && mv -f "$DTXT" "$DSET"; then
                chown 1000:1000 "$DSET"; chmod 600 "$DSET"; $BB chcon "$CTX" "$DSET" 2>/dev/null
                echo "Cover density: $CDEN for $CV_NAME ($CV_XDPI dpi panel, base $BASE)"
            else
                echo "Cover density: not set (display_settings.xml not written)"
            fi
        fi
        rm -f "$DTXT" "$DTXT.new"
    fi
fi

echo "=== 5.3 $(date +%T) cover density ==="
# OxygenOS's status bar on another phone's panel (0.4.81). The image carries its
# own phone's stable display size (1272 x 2772, config_stableDeviceDisplayWidth
# and Height), DisplayManager keeps it ("mStableDisplaySize=Point(1272, 2772)" in
# all OxygenOS reports of 0.4.72 to 0.4.74, on 1080 and 1440 px panels alike) and
# OPPO's SystemUI sorts the camera hole by halves of that width: a centred hole
# came out HOLE_LEFT_TYPE on the M55s (5514dd7b, 4cb0e1ad: 509..571 of 1080) and
# the A24 (80412f38), HOLE_RIGHT_TYPE on the S22 Ultra (1cb56737: 683..758 of
# 1440), and the status bar laid its clock and icons out for a corner hole.
# ColorOS has no such resource, takes the panel's size (A34 7e5896b0: 1080,
# HOLE_CENTER_TYPE) and is right. The size DisplayManager has saved in
# display-manager-state.xml wins over the resource, so the panel's own size
# (oneos_switch.sh: host_panel_size) is written there before every boot. Not on
# a fold (two panels, one stable size). ONEOS_GUEST_STABLE_SIZE=0: left alone.
# The reports after it (0.4.81 to 0.4.89, seven sessions): mStableDisplaySize
# was the panel's and the status bar the same as before. OPPO's SystemUI reads
# the resource itself ("ScreenSizeHelper--> StableDisplayWidthSize =
# config_stableDeviceDisplayWidth: 1272", Galaxy A35 b06d044f), so since 0.4.90
# the UI activator overlays the resource too (oneos_switch.sh, "stable display
# size"). This write stays: DisplayManager's own value, right from the boot on.
DMS="$STAGE/data/system/display-manager-state.xml"
HPS=$(cat "$STAGE/host_panel_size" 2>/dev/null)
if [ "${ONEOS_GUEST_STABLE_SIZE:-1}" != 1 ] || [ "$FORM" = fold ] ||
        ! grep -q '^  "image": "oxygenos' "$STAGE/.oneos_stage" 2>/dev/null; then
    :
elif [ "$(echo "$HPS" | wc -w)" != 2 ]; then
    echo "Stable display size: not set (the panel's size was not read)"
else
    SW=${HPS% *}; SH=${HPS#* }
    # A first start: the folder as init makes it (it sets owner, mode and label again).
    if [ ! -d "$STAGE/data/system" ]; then
        mkdir -p "$STAGE/data/system" && chown 1000:1000 "$STAGE/data/system" && chmod 775 "$STAGE/data/system"
        $BB chcon u:object_r:system_data_file:s0 "$STAGE/data/system" 2>/dev/null
    fi
    DMT="$STAGE/display_manager_state.txt"
    rm -f "$DMT"
    if [ ! -s "$DMS" ]; then
        printf '%s\n' "<?xml version='1.0' encoding='utf-8' standalone='yes' ?>" '<display-manager-state>' '</display-manager-state>' > "$DMT"
    elif [ "$(head -c 3 "$DMS")" = ABX ]; then
        abx2xml "$DMS" "$DMT" 2>/dev/null || rm -f "$DMT"
    else
        cp "$DMS" "$DMT"
    fi
    WAS=$(sed -n 's|.*<stable-display-width>\([0-9]*\)</stable-display-width>.*|\1|p' "$DMT" 2>/dev/null | head -n 1)x$(sed -n 's|.*<stable-display-height>\([0-9]*\)</stable-display-height>.*|\1|p' "$DMT" 2>/dev/null | head -n 1)
    if [ ! -s "$DMT" ] || ! grep -q '</display-manager-state>' "$DMT"; then
        echo "Stable display size: not set (display-manager-state.xml not readable)"
    elif [ "$WAS" = "${SW}x${SH}" ]; then
        echo "Stable display size: $WAS already (the panel's)"
    else
        if grep -q '<stable-display-width>[0-9]*</stable-display-width>' "$DMT" && grep -q '<stable-display-height>[0-9]*</stable-display-height>' "$DMT"; then
            sed -i -e "s|<stable-display-width>[0-9]*</stable-display-width>|<stable-display-width>$SW</stable-display-width>|" \
                -e "s|<stable-display-height>[0-9]*</stable-display-height>|<stable-display-height>$SH</stable-display-height>|" "$DMT"
        else
            # No saved size yet (a first boot), or a half-written one: one whole element.
            sed -i -e 's|<stable-device-values>.*</stable-device-values>||' -e 's|<stable-device-values */>||' \
                -e "s|</display-manager-state>|<stable-device-values><stable-display-height>$SH</stable-display-height><stable-display-width>$SW</stable-display-width></stable-device-values></display-manager-state>|" "$DMT"
        fi
        CTX=$(ls -Z "$DMS" 2>/dev/null | awk '{ print $1 }')
        case "$CTX" in u:object_r:*) ;; *) CTX=u:object_r:system_data_file:s0 ;; esac
        if grep -q "<stable-display-width>$SW</stable-display-width>" "$DMT" && grep -q "<stable-display-height>$SH</stable-display-height>" "$DMT" &&
                mv -f "$DMT" "$DMS"; then
            chown 1000:1000 "$DMS"; chmod 600 "$DMS"; $BB chcon "$CTX" "$DMS" 2>/dev/null
            echo "Stable display size: $SW x $SH, this panel's (was ${WAS}; OxygenOS's status bar sorts the camera hole by it)"
        else
            echo "Stable display size: not set (display-manager-state.xml not written)"
        fi
    fi
    rm -f "$DMT"
fi

# ColorOS's touch-idle refresh rate (OTI, oplus_vrr_config.json "touch_idle")
# takes this panel's mode (240 Hz vsync, 120 fps at most) as 240 Hz: it
# rendered at 240 on touch and 60 Hz 2.5 s later, over the 120 Hz policy (run
# 29: 337 s at 240, 104 s at 60, 33 s at 120), which also heats the phone.
# OPlusRusHelper prefers data/system/oplus_vrr_config.json (relative to
# system_server's working directory, the guest's /) when its "version" is
# higher than my_product's. ONEOS_GUEST_OTI=1 keeps ColorOS's own setting.
VRRCFG="$ROOTFS/my_product/etc/oplus_vrr_config.json"
VRRDATA="$STAGE/data/system/oplus_vrr_config.json"
# data/system is only created further down; on a fresh stage (S25U dry run,
# session f075d93a) the write failed and the first session kept OTI on.
mkdir -p "$STAGE/data/system" 2>/dev/null || true
rm -f "$VRRDATA"
if [ "${ONEOS_GUEST_OTI:-0}" = 0 ] && [ -f "$VRRCFG" ]; then
    sed -e 's/"touch_idle": *true/"touch_idle": false/' -e 's/"version": *[0-9]*/"version": 20991231/' "$VRRCFG" > "$VRRDATA"
    if grep -q '"touch_idle": false' "$VRRDATA" && grep -q '"version": 20991231' "$VRRDATA"; then
        echo "Guest VRR config: touch idle (OTI) off"
    else
        rm -f "$VRRDATA"; echo "WARNING: guest VRR config not staged (unexpected oplus_vrr_config.json)"
    fi
fi

echo "=== 5.4 $(date +%T) VRR config ==="
# ColorOS's ringtones, notification and UI sounds (run 31: "system ringtones
# are not there"; run 30: Settings_RingtoneUtils "getInternalRingtoneUri
# ringtone_001.ogg null", ModernMediaScanner "Failed to visit
# /data/oplus/multimedia/ringtones: AccessDeniedException"). The Find N6 has no
# plain ringtone folder: its sounds exist only as haptic-channel sets, one per
# motor frequency, in my_product/res/audio/haptic_ringtone/output<Hz>HZ. On the
# phone OplusAtlasService (RingCopyHelper) copies the set for its motor into
# /data/oplus/multimedia, which MediaProvider scans as internal media. It only
# does that with oplus.software.audio.haptic_channel_support, a my_product
# feature the guest does not load (run 30: "ringtone haptic is support:
# false"), and it reads the motor from OPPO's misc HAL, which a Samsung phone
# does not have, so it would take lra_level_middle. Stage that set here, into
# the guest's own /data only, system 0775 like ColorOS's init.rc. AudioFlinger
# drops the haptic channel on an output without one.
# ONEOS_GUEST_RINGTONES=0 leaves /data/oplus/multimedia alone.
if [ "${ONEOS_GUEST_RINGTONES:-1}" = 1 ]; then
    MM="$STAGE/data/oplus/multimedia"
    HR="$ROOTFS/my_product/res/audio/haptic_ringtone"
    LRA=$(sed -n 's/^ro\.oplus\.haptic\.lra_level_middle=//p' "$ROOTFS/my_product/build.prop" 2>/dev/null | head -n 1)
    RSRC="$HR/output${LRA:-166}HZ"
    [ -d "$RSRC/ringtones" ] || RSRC=$(ls -d "$HR"/output*HZ 2>/dev/null | head -n 1)
    if [ -n "$RSRC" ] && [ -d "$RSRC/ringtones" ]; then
        if [ "$(cat "$STAGE/guest_ringtones.src" 2>/dev/null)" != "$RSRC" ] || [ ! -d "$MM/ringtones" ]; then
            rm -f "$STAGE/guest_ringtones.src"
            mkdir -p "$MM"
            ok=1
            for k in ringtones notifications ui; do
                rm -rf "$MM/$k"
                if [ -d "$RSRC/$k" ]; then cp -r "$RSRC/$k" "$MM/$k" || ok=0; else mkdir -p "$MM/$k"; fi
            done
            [ "$ok" = 1 ] && echo "$RSRC" > "$STAGE/guest_ringtones.src"
        fi
        for d in "$STAGE/data/oplus" "$MM" "$MM/ringtones" "$MM/notifications" "$MM/ui"; do
            mkdir -p "$d"
            $BB chown 1000:1000 "$d" 2>/dev/null || true
            $BB chmod 0775 "$d" 2>/dev/null || true
        done
        for k in ringtones notifications ui; do
            $BB chown -h -R 1000:1000 "$MM/$k" 2>/dev/null || true
            for f in "$MM/$k"/*; do [ -f "$f" ] && $BB chmod 0644 "$f"; done
        done
        $BB chcon u:object_r:system_data_file:s0 "$STAGE/data/oplus" 2>/dev/null || true
        $BB chcon -h -R u:object_r:system_data_file:s0 "$MM" 2>/dev/null || true
        echo "Guest ringtones: $(ls "$MM/ringtones" | wc -l) ringtones, $(ls "$MM/notifications" | wc -l) notifications from ${RSRC#$ROOTFS}"
    else
        echo "WARNING: no ColorOS haptic ringtone set in my_product; guest ringtones not staged"
    fi
fi

echo "=== 5.5 $(date +%T) ringtones ==="
# vivo's theme and font folders. vivo's init.vivo.rc (image root, "on
# post-fs-data") makes /data/bbkcore (0777 root, the theme tree under it) and
# /data/vfonts (0777 system); One UI's init never reads it, so the seventh run
# had neither: i Theme's local cache, the default theme and the wallpaper
# thumbnails all failed ("/data/bbkcore/theme error!!", empty Themes and
# Wallpapers). Made in the guest's staged /data only, as the rc says, never
# through a link; quoted paths ("i Theme") kept whole. ONEOS_GUEST_THEME_DIRS=0
# leaves them alone.
if [ "${ONEOS_GUEST_THEME_DIRS:-1}" = 1 ] && [ -e "$ROOTFS/system/framework/vivo-services.jar" ] &&
   [ -f "$ROOTFS/init.vivo.rc" ] && [ ! -L "$ROOTFS/init.vivo.rc" ]; then
    made=0; listed=0
    awk '{ sub(/^[ \t]+/, "") }
     /^mkdir[ \t]+\/data\/(bbkcore|vfonts)([\/ \t"]|$)/ {
       s = $0; sub(/^mkdir[ \t]+/, "", s); p = ""; q = 0
       while (s != "") { c = substr(s, 1, 1); s = substr(s, 2)
         if (c == "\"") { q = !q; continue }
         if (!q && (c == " " || c == "\t")) break
         p = p c }
       sub(/^[ \t]+/, "", s); split(s, f, /[ \t]+/)
       m = (f[1] ~ /^[0-7]+$/) ? f[1] : "0755"; u = (f[2] == "system") ? 1000 : 0; g = (f[3] == "system") ? 1000 : 0
       sub(/\/+$/, "", p)
       if (p ~ /(^|\/)\.\.?(\/|$)/ || p ~ /\/\// || p ~ /[$|]/ || seen[p]++) next
       print m "|" u "|" g "|" p }' "$ROOTFS/init.vivo.rc" > "$STAGE/vivo_data_dirs.txt"
    while IFS='|' read -r mode u g p; do
        listed=$((listed + 1)); q="$STAGE/data"; ok=1; o=$IFS; IFS=/; set -f
        for part in ${p#/data/}; do q="$q/$part"; [ -L "$q" ] && { ok=0; break; }; done
        IFS=$o; set +f
        [ $ok = 1 ] || { echo "vivo /data folder $p: a link on the way, skipped"; continue; }
        d="$STAGE$p"; [ -d "$d" ] || { mkdir -p "$d" && made=$((made + 1)); }
        $BB chown "$u:$g" "$d" 2>/dev/null; $BB chmod "$mode" "$d" 2>/dev/null
        $BB chcon u:object_r:system_data_file:s0 "$d" 2>/dev/null || true
    done < "$STAGE/vivo_data_dirs.txt"
    echo "vivo theme and font /data folders from init.vivo.rc: $made made ($listed listed)"
    rm -f "$STAGE/vivo_data_dirs.txt"
    # The font list itself: vivo's /system/etc/fonts.xml is a link to
    # /data/vfonts/fonts.xml, which a vivo font service writes on a vivo phone and
    # nothing wrote in the guest. Android's own font code reads font_fallback.xml, but
    # Chromium (WebView) reads fonts.xml, found nothing and drew no text: the Google
    # sign-in fields white on white (F8U runs 18-19). The image's default list when
    # there is none (a theme font vivo writes later replaces it).
    if [ -L "$ROOTFS/system/etc/fonts.xml" ] && [ "$(readlink "$ROOTFS/system/etc/fonts.xml")" = /data/vfonts/fonts.xml ] &&
       [ -d "$STAGE/data/vfonts" ] && [ ! -L "$STAGE/data/vfonts" ] && [ ! -s "$STAGE/data/vfonts/fonts.xml" ]; then
        for src in fonts_default.xml fonts_org.xml; do
            [ -f "$ROOTFS/system/etc/$src" ] && [ ! -L "$ROOTFS/system/etc/$src" ] || continue
            rm -f "$STAGE/data/vfonts/fonts.xml"
            cp "$ROOTFS/system/etc/$src" "$STAGE/data/vfonts/fonts.xml" &&
                $BB chown 1000:1000 "$STAGE/data/vfonts/fonts.xml" && chmod 644 "$STAGE/data/vfonts/fonts.xml" &&
                { $BB chcon u:object_r:system_data_file:s0 "$STAGE/data/vfonts/fonts.xml" 2>/dev/null || true; } &&
                echo "vivo font list: /data/vfonts/fonts.xml from the image's $src (fonts.xml links there)" && break
        done
    fi
fi
# ColorOS's theme and icon folders. Its init.oplus.rootdir.rc (system_ext)
# makes /data/theme, /data/oplus/uxicons, /data/oplus/uxres and
# /data/oplus/language 0777 system system "on post-fs-data"; One UI's init
# never reads it, and the apps that write there are not system and cannot make
# them under /data/oplus themselves. Applying the Custom icon style with icon
# colours that follow the wallpaper crashed Wallpapers & style (0.4.40
# b9110fc3, com.oplus.uxdesign: createNewFile ENOENT in common.u.i, which
# writes /data/oplus/uxres/uxcolor), chosen icons were not saved (UxFileUtils:
# /data/oplus/uxicons/choose/... ENOENT) and the launcher's morph icon list
# neither (0.4.55 4933a41d, RusUtils: /data/oplus/uxicons/
# morph_icons_whitelist.xml ENOENT). Made in the guest's own /data only, with
# the rc's mode and owners, never through a link the guest made.
# 0.4.85: and its font folder. ColorOS and OxygenOS keep the system font's
# file as a link in /data/format_unclear/font, which system_server makes at
# each boot; without the folder every guest boot logged "FontUtils: Could not
# update selinux policy check and correct flipfont: /data/format_unclear/font/
# OplusOSUI-Regular.ttf: symlink failed: ENOENT" (30 of 44 OxygenOS 16 and 41
# of 50 ColorOS 17 X9U reports among the latest 150 with logs). Not shown to
# be why web pages lose their text on OxygenOS 16 (S22 Ultra ab076b9a, A25
# 32a0830e: chromium remote_font_face_source.cc NOTREACHED in 4 of the 44,
# Google sign-in without text, blank pages in some apps): ColorOS 17 logs the
# same FontUtils line and shows web text. That cause is still open; diag
# webview.txt has a "fonts:" part for it (oneos_switch.sh).
# Both folders with the rc's mode and owners when an rc names them, else 0771
# system system. Not confirmed on a phone until the first 0.4.85 report: the
# FontUtils line gone.
# ONEOS_GUEST_THEME_DIRS=0 leaves them alone.
if [ "${ONEOS_GUEST_THEME_DIRS:-1}" = 1 ] && [ -e "$ROOTFS/system/framework/oplus-services.jar" ]; then
    made=0
    for f in "$ROOTFS"/system/etc/init/*.rc "$GUEST_SYSTEM_EXT"/etc/init/*.rc; do
        [ -f "$f" ] && [ ! -L "$f" ] && cat "$f"
    done | awk '$1 == "mkdir" && $2 ~ /^\/data\/(theme|format_unclear(\/font)?|oplus\/(uxicons|uxres|language))\/?$/ { sub(/\/$/, "", $2); print $2, ($3 ~ /^[0-7]+$/ ? $3 : "0771"), ($4 == "root" ? 0 : 1000), ($5 == "root" ? 0 : 1000) }' |
        sort -u -k1,1 > "$STAGE/coloros_data_dirs.txt"
    for p in /data/format_unclear /data/format_unclear/font; do
        grep -q "^$p " "$STAGE/coloros_data_dirs.txt" || echo "$p 0771 1000 1000" >> "$STAGE/coloros_data_dirs.txt"
    done
    while read -r p mode u g; do
        q="$STAGE/data"; ok=1
        for part in $(echo "${p#/data/}" | tr '/' ' '); do
            q="$q/$part"; [ -L "$q" ] && { ok=0; break; }
        done
        [ $ok = 1 ] || { echo "ColorOS /data folder $p: a link on the way, skipped"; continue; }
        d="$STAGE$p"
        if [ ! -d "$d" ]; then
            [ -d "$STAGE/data/oplus" ] || { mkdir -p "$STAGE/data/oplus" && $BB chown 1000:1000 "$STAGE/data/oplus" && $BB chmod 0775 "$STAGE/data/oplus" &&
                $BB chcon u:object_r:system_data_file:s0 "$STAGE/data/oplus" 2>/dev/null; }
            mkdir -p "$d" && made=$((made + 1))
        fi
        $BB chown "$u:$g" "$d" 2>/dev/null; $BB chmod "$mode" "$d" 2>/dev/null
        $BB chcon u:object_r:system_data_file:s0 "$d" 2>/dev/null || true
    done < "$STAGE/coloros_data_dirs.txt"
    echo "ColorOS theme/icon /data folders from its init rc files: $made made ($(wc -l < "$STAGE/coloros_data_dirs.txt") listed)"
    rm -f "$STAGE/coloros_data_dirs.txt"
fi

echo "=== 5.6 $(date +%T) theme folders ==="
# Screen recording of the session (guest_start.sh) only when asked for.
if [ "${ONEOS_RECORD:-0}" = 1 ]; then touch "$STAGE/data/oneos_record"; else rm -f "$STAGE/data/oneos_record"; fi
echo "Screen recording: $([ -f "$STAGE/data/oneos_record" ] && echo on || echo off)"
# Hardware overlays for the guest's SurfaceFlinger (see guest_start.sh). On by
# default since run 44 for guests without oplus-services.jar: run 43's Pixel
# surfaceflinger has no Qualcomm composer client, and forcing GPU composition
# there cost about 2 missed frames a second. ColorOS, whose composer extension
# client got its frames rejected, stayed on GPU composition up to 0.4.75 though
# surfaceflinger_patched had ended the rejections. 0.4.76: on for ColorOS too.
# The owner's Fold in ColorOS 17 (11-10): every layer DEVOPTFORCECLIENT and
# 21006 GPU missed frames 40 minutes in; with the overlays switched on in that
# running session (transaction 1008 i32 0) every layer was composed by the
# panel's composer for the 5.5 minutes until the return, in use, without one
# rejected frame. guest_start.sh forces GPU composition again if the composer
# rejects frames in the first 30 s, and the switch's watcher later in the
# session. ONEOS_GUEST_HWC=0|1 overrides the default.
HWC_DEF=1
if [ "${ONEOS_GUEST_HWC:-$HWC_DEF}" = 1 ]; then touch "$STAGE/data/oneos_hwc"; else rm -f "$STAGE/data/oneos_hwc"; fi
rm -f "$STAGE/data/oneos_hwc_forced"
echo "Guest HW overlays: $([ -f "$STAGE/data/oneos_hwc" ] && echo 'on (GPU composition forced only if the composer rejects frames)' || echo 'off (GPU composition)')"

# ONEOS_GAP_FAST=0: guest_start.sh keeps its fixed 2 s sleeps after the
# composer restart and the SurfaceFlinger start (run 32 timing; see there).
if [ "${ONEOS_GAP_FAST:-1}" = 0 ]; then touch "$STAGE/data/oneos_gap_slow"; else rm -f "$STAGE/data/oneos_gap_slow"; fi


echo "=== 5.7 $(date +%T) flags ==="
# OPPO's own default runtime permission grants (patches/oplus_default_grants.py
# in oplus-services_patched.jar reads the my_product and my_stock grant lists
# while this flag exists). Its OplusRuntimePermGrantPolicyManager finds them
# only through CUST_LEVEL_LIST, which OPPO's init exports and the container
# never has. Run 34: "default xmls not found", so the network location
# provider com.oplus.location had no location or phone permission, WifiService
# refused all 27 of its scans ("UID 10163 has no location permission") and
# Weather never got a location; 108 grants of 35 OPPO apps were missing. OPPO
# grants on every boot, only to system apps, only what an app requests and
# never over a choice the user made. ONEOS_GUEST_OPLUS_GRANTS=0 leaves the
# lists out (grants already given stay in the guest's permission state).
if [ "${ONEOS_GUEST_OPLUS_GRANTS:-1}" = 1 ]; then touch "$STAGE/data/oneos_oplus_grants"; else rm -f "$STAGE/data/oneos_oplus_grants"; fi
echo "OPPO default grants: $([ -f "$STAGE/data/oneos_oplus_grants" ] && echo on || echo off)"

# The guest's /data/misc/adb always exists, keys or not. ColorOS's (Android
# 17) AdbDebuggingManager takes a missing directory as null key files and
# AdbService's constructor throws on them ("ADB data directory does not
# exist", "Failure starting AdbService"); the Lifecycle then calls
# systemReady() on the never-created service at boot phase 550 and
# system_server dies of the NullPointerException. Session f075d93a (S25U,
# fresh stage): One UI had USB debugging on but no adb_keys (no computer was
# ever allowed over USB), so the only mkdir, the copy below, never ran; the
# F8U's stage had the directory from its adb_keys. A real /data/misc/adb is
# system:shell 02750 (init.rc); 5b labels it with the rest of data/misc.
# What goes into it is unchanged: the host's adb_keys only with One UI's USB
# debugging on, and never One UI's adb_temp_keys.xml.
mkdir -p "$STAGE/data/misc/adb" || { echo "ERROR: could not create $STAGE/data/misc/adb; not starting the guest"; exit 3; }
chown 1000:2000 "$STAGE/data/misc/adb" 2>/dev/null || true
chmod 02750 "$STAGE/data/misc/adb" 2>/dev/null || true
if [ "$HOST_ADB" = 1 ] && [ -f /data/misc/adb/adb_keys ]; then
    rm -f "$STAGE/data/misc/adb/adb_keys"
    cp -f /data/misc/adb/adb_keys "$STAGE/data/misc/adb/adb_keys" 2>/dev/null && \
        chmod 640 "$STAGE/data/misc/adb/adb_keys" 2>/dev/null && \
        echo "Copied host adb_keys into the guest /data"
elif [ "$HOST_ADB" != 1 ]; then
    # The guest's own copy from an earlier session (stage only, not One UI's).
    rm -f "$STAGE/data/misc/adb/adb_keys"
fi
# WebView's shared RELRO directory, which init.rc makes (mkdir
# /data/misc/shared_relro 0771 shared_relro shared_relro) and the container,
# having no init, did not: WebView's RelroFileCreator failed on every session
# ("Failed to create temporary file /data/misc/shared_relro/...: No such file
# or directory", Nothing OS run 8). Stage only.
mkdir -p "$STAGE/data/misc/shared_relro" &&
    chown 1037:1037 "$STAGE/data/misc/shared_relro" 2>/dev/null &&
    chmod 0771 "$STAGE/data/misc/shared_relro" 2>/dev/null &&
    $BB chcon u:object_r:shared_relro_file:s0 "$STAGE/data/misc/shared_relro" 2>/dev/null || true
if [ -f "$STAGE/zygote_exec" ]; then
    rm -f "$STAGE/data/zygote_exec"
    cp -f "$STAGE/zygote_exec" "$STAGE/data/zygote_exec"
    chmod 755 "$STAGE/data/zygote_exec"
fi
# OneOS: the guest's own busybox, copied like zygote_exec. guest_start.sh uses
# it after the pivot, so nothing in the guest needs host /data/adb (bound
# read-only below).
# Named busybox in its own dir: a multi-call busybox reads its applet from
# argv[0] unless it is called busybox. Checked here with the applets
# guest_start.sh needs first.
rm -f "$STAGE/data/oneos_busybox"
mkdir -p "$STAGE/data/oneos_bin"
rm -f "$STAGE/data/oneos_bin/busybox"
if cp -f "$BB" "$STAGE/data/oneos_bin/busybox" && chmod 755 "$STAGE/data/oneos_bin/busybox" &&
    "$STAGE/data/oneos_bin/busybox" true && "$STAGE/data/oneos_bin/busybox" mount --help >/dev/null 2>&1; then
    echo "Guest busybox: $STAGE/data/oneos_bin/busybox (from $BB)"
else
    rm -f "$STAGE/data/oneos_bin/busybox"
    echo "WARNING: could not copy $BB into the guest /data; guest_start.sh keeps the host's path"
fi
mkdir -p "$STAGE/data/user/0" "$STAGE/data/user_de/0"
mkdir -p "$STAGE/data/system/users/0" "$STAGE/data/system_de/0/spblob" "$STAGE/data/system_ce/0"
# A guest lock state from before the weaver guard (patches/guest_no_weaver.py)
# holds protectors in the phone's weaver slots, which the guarded framework
# can no longer read, so the guest could not unlock its own user 0. Only the
# stage's copy: One UI's lock state is never touched. The guest sets up a
# fresh software protector on its next boot, as on a fresh stage; a lock set
# inside ColorOS is gone with it.
if ls "$STAGE/data/system_de/0/spblob"/*.weaver >/dev/null 2>&1; then
    rm -f "$STAGE/data/system_de/0/spblob"/* "$STAGE/data/system/locksettings.db" \
          "$STAGE/data/system/locksettings.db-journal" "$STAGE/data/system/locksettings.db-wal" \
          "$STAGE/data/system/locksettings.db-shm" "$STAGE/data/system"/gatekeeper.*.key 2>/dev/null
    echo "Guest lock state from before the weaver guard removed (stage only); ColorOS makes a new one"
fi
mkdir -p "$STAGE/data/misc/user/0" "$STAGE/data/misc_de/0" "$STAGE/data/misc_ce/0"
echo "=== 5.8 $(date +%T) adb, relro, busybox, locks ==="
# The guest has no vold_prepare_subdirs, so nothing creates the per-user APEX
# data dirs. WifiConfigStore only mkdir()s the last level (run 32: Could not
# create store directory /data/misc_ce/0/apexdata/com.android.wifi, Failed to
# create user store files): the user store (network suggestions, per-user
# networks) never loaded. Stage only; the chmod/chown pass below covers them.
mkdir -p "$STAGE/data/misc_ce/0/apexdata/com.android.wifi" "$STAGE/data/misc_de/0/apexdata/com.android.wifi"
# Nor apexd's /data/misc/apexdata/<module> (one per active APEX): a guest /data that
# never had them (the first CN run on a fresh /data) lost system_server at
# NetworkStatsService ("Cannot write into stats data directory:
# /data/misc/apexdata/com.android.tethering/netstats"); guest_start.sh's odrefresh
# step had made /data/misc/apexdata root's 755. Every module name, One UI's (the
# guest takes some of One UI's modules) and the image's own, in all three places,
# before the chmod/chown pass below.
for n in $(ls /apex 2>/dev/null | grep -v '@'; ls "$ROOTFS/system/apex" 2>/dev/null |
           sed -e 's/\.c\{0,1\}apex$//' -e 's/_tplus_compressed$//' -e 's/_compressed$//' -e 's/^com\.google\.android\./com.android./'); do
    case "$n" in *[!A-Za-z0-9._]*|.*|"") continue ;; esac
    mkdir -p "$STAGE/data/misc/apexdata/$n" "$STAGE/data/misc_ce/0/apexdata/$n" "$STAGE/data/misc_de/0/apexdata/$n"
done
# vivo's feature list for system_server (patches/vivo_guards.py framework reads
# /data/system/oneos_vivo_features; make-overlays.sh builds it from the vendor's
# vivo_config.ini without the hardware features): without vivo's config store HAL
# every vivo feature read as off. ONEOS_GUEST_VIVO_FEATURES=0 leaves them off.
if [ -f "$STAGE/oneos-vivo-features.txt" ] && [ "${ONEOS_GUEST_VIVO_FEATURES:-1}" = 1 ]; then
    mkdir -p "$STAGE/data/system" && cp -f "$STAGE/oneos-vivo-features.txt" "$STAGE/data/system/oneos_vivo_features" &&
        chmod 644 "$STAGE/data/system/oneos_vivo_features" &&
        echo "Guest vivo features: $(tr '&' '\n' < "$STAGE/data/system/oneos_vivo_features" | grep -c 'vivo-support$') from the vendor's vivo_config.ini"
    # vivo's SuperX (atomic) notifications: VivoSuperXNotificationManager turns its scene
    # support on only with vivo.opt.notification.superx, which the CN vendor's
    # vivo_config.ini does not list (only ...superx_state_changed_support_broadcast).
    # Without it getSceneStatus() said no to every app, so the recorder, clock and music
    # sent no island data and the dynamic island never showed (F8U runs 17-19, with
    # superx_notification_selector on). ONEOS_GUEST_VIVO_SUPERX=0 leaves it out.
    if [ -f "$STAGE/data/system/oneos_vivo_features" ] && [ "${ONEOS_GUEST_VIVO_SUPERX:-1}" = 1 ] &&
       ! tr '&' '\n' < "$STAGE/data/system/oneos_vivo_features" | grep -qxF 'vivo.opt.notification.superx$vivo-support'; then
        printf '&vivo.opt.notification.superx$vivo-support' >> "$STAGE/data/system/oneos_vivo_features" &&
            echo "Guest vivo features: vivo.opt.notification.superx added (SuperX notifications, dynamic island)"
    fi
    # vivo's camera hole (vivo.hardware.holescreen: the lens box's top left and radius,
    # vivo's own phone 590,45 r40 on its 1260 px panel): left out with the hardware
    # features, so SystemUI had isHoleScreen=false and its dynamic island never showed
    # (F8U run 17: music, timer, clock). This phone's lens from One UI (host_holes,
    # oneos_switch.sh): the cover's on a Fold, else the main panel's.
    # ONEOS_GUEST_VIVO_HOLE=0 leaves it out.
    if [ -f "$STAGE/data/system/oneos_vivo_features" ] && [ -s "$STAGE/host_holes" ] && [ "${ONEOS_GUEST_VIVO_HOLE:-1}" = 1 ] &&
       ! grep -q 'vivo\.hardware\.holescreen\$' "$STAGE/data/system/oneos_vivo_features"; then
        HL=$(grep '^cover ' "$STAGE/host_holes" | head -n 1); [ -n "$HL" ] || HL=$(grep '^main ' "$STAGE/host_holes" | head -n 1)
        LENS=$(printf '%s\n' "$HL" | awk '{ print $5 }' | cut -d'|' -f1)
        case "$LENS" in
            [0-9]*,[0-9]*:[0-9]*,[0-9]*)
                hx=${LENS%%,*}; r=${LENS#*,}; hy=${r%%:*}; r=${LENS#*:}; x2=${r%%,*}
                hr=$(( (x2 - hx) / 2 ))
                if [ "$hr" -gt 0 ] && [ "$hr" -lt 200 ]; then
                    printf '&vivo.hardware.holescreen$vivo-support&vivo.hardware.holescreen:hole_x$%s&vivo.hardware.holescreen:hole_y$%s&vivo.hardware.holescreen:hole_radius$%s&vivo.hardware.holescreen:hole_screen_stage$1' \
                        "$hx" "$hy" "$hr" >> "$STAGE/data/system/oneos_vivo_features" &&
                        echo "Guest vivo camera hole: x $hx, y $hy, radius $hr (${HL%% *} panel, from One UI)"
                fi ;;
            *) echo "Guest vivo camera hole: not set (One UI's lens '${LENS:-none}')" ;;
        esac
    fi
else
    rm -f "$STAGE/data/system/oneos_vivo_features"
fi
# init.rc's too (a fresh /data had none of them): Wi-Fi, SMS usage, text classifier.
mkdir -p "$STAGE/data/misc/wifi" "$STAGE/data/misc/sms" "$STAGE/data/misc/textclassifier"
mkdir -p "$STAGE/data/anr" "$STAGE/data/app" "$STAGE/data/rollback" "$STAGE/data/incremental"
# The guest's own shared storage. Never the phone's /data/media: in run 25 the
# guest's cleanup of a user it could not prepare deleted the photos in it.
mkdir -p "$STAGE/data/media/0" "$STAGE/data/media/obb" "$STAGE/data/vendor_de/0" "$STAGE/data/vendor_ce/0"
# The fingerprint framework makes this before setting the active user; without
# it FingerprintUpdateActiveUserClient fails and no sensor is ever opened.
mkdir -p "$STAGE/data/vendor_de/0/fpdata"
chown 1000:1000 "$STAGE/data/vendor_de/0/fpdata" 2>/dev/null || true
chmod 700 "$STAGE/data/vendor_de/0/fpdata" 2>/dev/null || true
$BB chcon u:object_r:fingerprint_vendor_data_file:s0 "$STAGE/data/vendor_de/0/fpdata" 2>/dev/null || true

# ColorOS can only use the biometrics the phone's TEE already holds. Enrolling
# inside the guest needs a HardwareAuthToken, and the guest has no gatekeeper
# to mint one (its PIN is verified locally), so ColorOS's "Add" does nothing.
# Carry One UI's enrollment metadata across instead: the templates never leave
# the TEE, and no credential, gatekeeper handle or SP blob is read. ColorOS
# reads the legacy settings_fingerprint.xml; One UI writes _0.
BIO_DST=$STAGE/data/system/users/0
mkdir -p "$BIO_DST" || true
rm -f "$BIO_DST/settings_fingerprint_0.xml"
bio=0
for f in settings_fingerprint_0.xml settings_face.xml face_enrolled_position_0.xml; do
    out=$f
    [ "$f" = settings_fingerprint_0.xml ] && out=settings_fingerprint.xml
    if [ -f "/data/system/users/0/$f" ]; then
        cp -f "/data/system/users/0/$f" "$BIO_DST/$out" &&
            chown 1000:1000 "$BIO_DST/$out" 2>/dev/null &&
            chmod 644 "$BIO_DST/$out" 2>/dev/null &&
            $BB chcon -h u:object_r:system_data_file:s0 "$BIO_DST/$out" 2>/dev/null
        bio=$((bio + 1))
    else
        # A print or face removed in One UI must not stay listed here.
        rm -f "$BIO_DST/$out"
    fi
done
[ "$bio" -gt 0 ] && echo "Guest biometrics: carried One UI's $bio enrollment file(s) into the guest"

# OneOS: without OneLineage's LineageOS packages (Launcher3, LatinIME,
# LineageSettings; ColorOS has none of them) and with the OneOS app in place
# of the OneLineage switcher.
for pkg in com.android.providers.settings \
           com.android.providers.telephony \
           com.android.phone \
           com.android.systemui \
           com.android.settings \
           com.android.providers.media \
           com.android.providers.downloads \
           com.android.providers.contacts \
           com.android.providers.calendar \
           com.fahadali.oneos; do
    mkdir -p "$STAGE/data/user_de/0/$pkg/databases" \
             "$STAGE/data/user_de/0/$pkg/shared_prefs" \
             "$STAGE/data/user_de/0/$pkg/files/datastore/education" \
             "$STAGE/data/user/0/$pkg/databases" \
             "$STAGE/data/user/0/$pkg/shared_prefs" \
             "$STAGE/data/user/0/$pkg/files"
done

mkdir -p "$STAGE/data/resource-cache"
chmod 771 "$STAGE/data/resource-cache"
chown 1000:1000 "$STAGE/data/resource-cache"
# One UI's side of the resource-cache bridge (bridges.sh): One UI's idmap2
# writes One UI's idmaps here during the session, never over the guest's
# data/resource-cache, whose idmaps the guest's zygote has mapped. Made new
# each session: nothing a guest left in it (a link) is there for One UI's
# idmap2, which runs as root, to write through.
rm -rf "$STAGE/data/oneos_host_resource_cache" 2>/dev/null
mkdir -p "$STAGE/data/oneos_host_resource_cache"
chmod 771 "$STAGE/data/oneos_host_resource_cache"
chown 1000:1000 "$STAGE/data/oneos_host_resource_cache"
$BB chcon u:object_r:resourcecache_data_file:s0 "$STAGE/data/oneos_host_resource_cache" 2>/dev/null || true

rm -rf "$STAGE/data/data" 2>/dev/null || true
mkdir -p "$STAGE/data/data"

chmod -R 777 "$STAGE/data/misc" "$STAGE/data/misc_de" "$STAGE/data/misc_ce" "$STAGE/data/system" "$STAGE/data/system_de" "$STAGE/data/system_ce" "$STAGE/data/anr" "$STAGE/data/data" 2>/dev/null || true
chown -h -R 1000:1000 "$STAGE/data/system" "$STAGE/data/system_de" "$STAGE/data/system_ce" "$STAGE/data/misc" "$STAGE/data/misc_de" "$STAGE/data/misc_ce" 2>/dev/null || true
echo "=== 5.9 $(date +%T) perms ==="
# The package dirs pre-created above are root-owned until something sets an
# owner: give them system's, as before; the realign below corrects the ones the
# guest gave another uid.
for pkg in com.android.providers.settings com.android.providers.telephony com.android.phone \
           com.android.systemui com.android.settings \
           com.android.providers.media com.android.providers.downloads com.android.providers.contacts \
           com.android.providers.calendar com.fahadali.oneos; do
    chown -h -R 1000:1000 "$STAGE/data/user_de/0/$pkg" "$STAGE/data/user/0/$pkg" 2>/dev/null
    chmod -R 777 "$STAGE/data/user_de/0/$pkg" "$STAGE/data/user/0/$pkg" 2>/dev/null
    # Code an app saved there (vivo SystemUI's plugin APKs) read-only again: since Android 14
    # ART refuses to load a writable dex file, and the sweep above made the one vivo's
    # SystemUI kept from the session before writable (eighth OriginOS run: SystemUI died
    # 17 times, "Writable dex file ... MagazinePlugin.apk is not allowed").
    find "$STAGE/data/user_de/0/$pkg" "$STAGE/data/user/0/$pkg" -type f \( -name '*.apk' -o -name '*.dex' -o -name '*.jar' \) \
        -exec chmod a-w {} + 2>/dev/null
done
# OneOS: not the app data trees. Resetting every app dir to 1000:1000 on each
# switch made the host installd refuse to prepare 353 packages ("Expected path
# ... with owner NNNNN but found 1000:1000"). Only the top levels, then every
# package dir back to the uid the guest gave it.
chown system:system "$STAGE/data/user" "$STAGE/data/user_de" "$STAGE/data/user/0" "$STAGE/data/user_de/0" 2>/dev/null
chmod 0711 "$STAGE/data/user" "$STAGE/data/user_de" 2>/dev/null
chmod 0771 "$STAGE/data/user/0" "$STAGE/data/user_de/0" 2>/dev/null
realigned=0
if [ -f "$STAGE/data/system/packages.list" ]; then
    find "$STAGE/data/user/0" "$STAGE/data/user_de/0" -mindepth 1 -maxdepth 1 -type d \
        -exec stat -c '%u %n' {} + 2>/dev/null > "$STAGE/realign.now"
    awk 'NR == FNR { auid[$1] = $2; next }
         { n = $2; sub(/.*\//, "", n); if ((n in auid) && $1 != auid[n]) print auid[n], $2 }' \
        "$STAGE/data/system/packages.list" "$STAGE/realign.now" > "$STAGE/realign.fix"
    while read -r auid d; do
        chown -h -R "$auid:$auid" "$d" && chmod 0700 "$d" && realigned=$((realigned + 1))
    done < "$STAGE/realign.fix"
    rm -f "$STAGE/realign.now" "$STAGE/realign.fix"
fi
echo "App data dirs realigned to their package uids: $realigned"
# Profiles: installd recreates them with the owners it expects.
rm -rf "$STAGE/data/misc/profiles/cur/0/"* "$STAGE/data/misc/profiles/ref/"* 2>/dev/null
echo "=== 5.10 $(date +%T) realign ==="

# Create the bluetooth stack's storage before the guest ever starts. The GSI's
# GD stack asserts out of storage_module.cc if it cannot persist bt_config.conf,
# and the staged tree never had this directory, so com.android.bluetooth
# crash-looped every 4 s from early boot. uid 1002 = bluetooth.
mkdir -p "$STAGE/data/misc/bluedroid" "$STAGE/data/misc/bluetooth" 2>/dev/null
chown 1002:1002 "$STAGE/data/misc/bluedroid" "$STAGE/data/misc/bluetooth" 2>/dev/null || true
chmod 0770 "$STAGE/data/misc/bluedroid" "$STAGE/data/misc/bluetooth" 2>/dev/null || true

# Apps uninstalled in the guest (0.4.50; owner and testers: "apps I uninstalled come back in the
# next session", ColorOS Mod on the owner's Fold). The storage guard drops installd's rmPackageDir
# (patches/guest_storage_guards.py: One UI's installd would act on One UI's own /data/app), so an
# uninstall removed the package's record but left its code folder in the guest's data/app, and the
# next boot's scan installed it again: ColorOS installs whatever code folder it finds there
# (PackageManagerServiceExtImpl.allowUnknownWhenScanRequireKnownInAssertPackageIsValid is always
# true, logged as "assertPackageIsValid ignoring<package>"; stock Android only leaves the folder).
# Here, with the guest down, the code folders nothing uses go. Only the stage's own data/app; no
# list, nothing done.
# 0.4.83 (owner, 11-10: "whatever you uninstall in there like 3rd party app or debloat some system
# app, after updating or booting that OS next time those apps come back"; reports of 0.4.72 to
# 0.4.74: 25 apps installed again on 9 later boots). The 0.4.50 pass took the package from the
# folder's name up to its last "-", and the random part after the name has a "-" of its own in
# about one folder of three: those were skipped. It also never looked at
# - a preinstalled app's copy (data/app/<Name>, no package in the name: ColorOS copies its
#   /my_stock/del-app apps there), which brought a debloated app back the same way;
# - the folder an update or a reinstall left behind (the package is installed from another one);
# - install staging folders (vmdl*.tmp; the system drops an install session after three days).
# The first two of these only with the guest's package records at hand as whole text (ColorOS
# writes packages.xml so; Android's binary form, or a write that was cut off: uninstalled apps'
# folders and staging folders only), and never a folder a record names.
PL="$STAGE/data/system/packages.list"
PX="$STAGE/data/system/packages.xml"
if [ -s "$PL" ] && [ ! -L "$PL" ] && [ -d "$STAGE/data/app" ] && [ ! -L "$STAGE/data/app" ]; then
    # Each package record's code path. Not while a packages-backup.xml says the last write did
    # not finish, and only when every listed package has its record (the two files of one moment).
    CPS="$STAGE/guest_code_paths.txt"; rm -f "$CPS"; recs=0
    if [ -s "$PX" ] && [ ! -L "$PX" ] && [ ! -e "$STAGE/data/system/packages-backup.xml" ] &&
       [ "$(head -c 5 "$PX" 2>/dev/null)" = "<?xml" ] && tail -c 64 "$PX" 2>/dev/null | grep -q "</packages>"; then
        awk '/^[ \t]*<package / { n = ""; c = ""
                 if (match($0, / name="[^"]*"/)) n = substr($0, RSTART + 7, RLENGTH - 8)
                 if (match($0, / codePath="[^"]*"/)) c = substr($0, RSTART + 11, RLENGTH - 12)
                 if (n == "" || c == "") bad++; else print n " " c }
             END { exit bad > 0 }' "$PX" > "$CPS" 2>/dev/null && recs=$(wc -l < "$CPS")
        [ "$recs" -ge "$(wc -l < "$PL")" ] || recs=0
    fi
    in_use() { [ "$recs" -gt 0 ] && awk -v c="$1" '$2 == c { f = 1 } END { exit !f }' "$CPS"; }
    gone=""; old=0; pre=0; stg=0
    for d in "$STAGE"/data/app/~~*/* "$STAGE"/data/app/*; do
        [ -d "$d" ] && [ ! -L "$d" ] || continue
        n=${d##*/}; p=${d%/*}; g=${d#"$STAGE"}
        case "$n" in
            ~~*)
                # A parent folder: its code folder is looked at on its own; an empty one goes.
                [ "$p" = "$STAGE/data/app" ] && { rmdir "${d:?}" 2>/dev/null; continue; } ;;
            vmdl*.tmp)
                [ "$p" = "$STAGE/data/app" ] && [ -n "$(find "$d" -maxdepth 0 -mtime +3 2>/dev/null)" ] &&
                    rm -rf "${d:?}" && stg=$((stg + 1))
                continue ;;
        esac
        ls "$d"/*.apk >/dev/null 2>&1 || continue
        in_use "$g" && continue
        # <package>-<random>: a package name has a dot and no "-".
        pkg=""
        case "$n" in *-*) pkg=${n%%-*} ;; esac
        case "$pkg" in *[!A-Za-z0-9_.]*) pkg="" ;; *.*) ;; *) pkg="" ;; esac
        if [ -n "$pkg" ] && ! awk -v k="$pkg" '$1 == k { f = 1 } END { exit !f }' "$PL"; then
            rm -rf "${d:?}" && gone="$gone $pkg"
        elif [ "$recs" -gt 0 ] && [ -n "$pkg" ]; then
            # Installed, from another folder (or from the image): an older version's folder.
            cur=$(awk -v k="$pkg" '$1 == k { print $2; exit }' "$CPS")
            case "$cur" in
                "") continue ;;
                /data/app/*) [ -d "$STAGE$cur" ] && [ ! -L "$STAGE$cur" ] || continue ;;
            esac
            rm -rf "${d:?}" && old=$((old + 1))
        elif [ "$recs" -gt 0 ]; then
            rm -rf "${d:?}" && pre=$((pre + 1))
        else
            continue
        fi
        [ "$p" != "$STAGE/data/app" ] && rmdir "${p:?}" 2>/dev/null
    done
    rm -f "$CPS"
    [ -z "$gone" ] || echo "Uninstalled apps' code folders removed:$gone"
    [ "$old" = 0 ] || echo "Code folders of older versions of installed apps removed: $old"
    [ "$pre" = 0 ] || echo "Copies of preinstalled apps that no package uses removed: $pre"
    [ "$stg" = 0 ] || echo "Install staging folders older than three days removed: $stg"
fi

echo "=== 5.11 $(date +%T) bluetooth, apps, preapps ==="
# ColorOS's removable preinstalled apps (/my_stock/del-app) load their native
# libraries from /data/preapps-lib/<app>/lib/arm64, which the guest's
# PackageManager fills. The guest's init.rc makes the top directory 0771 system
# system; the container has no init, so PackageManager created it 0700 and no
# app could look inside. Run 32: Weather crashed on open (all.log:872820,
# UnsatisfiedLinkError: "libprivate-constants-v3.so" not found) although the
# file is in the stage's preapps-lib/OppoWeather2/lib/arm64, and the theme
# store could not load KeKeThemeSpace's libmmkv.so (all.log:1222929). Only
# the mode of the guest's own directory changes; made here if missing so
# PackageManager never creates it with 0700 again.
mkdir -p "$STAGE/data/preapps-lib" 2>/dev/null
chown 1000:1000 "$STAGE/data/preapps-lib" 2>/dev/null || true
chmod 0771 "$STAGE/data/preapps-lib" 2>/dev/null || true

echo "=== 5.12 $(date +%T) HyperOS folders ==="
# HyperOS's own /data folders. Its init rc files (system, system_ext, product)
# make /data/system/theme, theme_magic and fonts (owner system_theme, 6101 in
# the image's passwd), mcd, whetstone, miuilog and more at boot; One UI's init
# never reads them, and nothing else creates them in the guest's /data. Theme
# Store could not create them itself (seventh HyperOS run: "mkdirs failed",
# chmod ENOENT), and icons, fonts, lock styles and wallpapers could not be
# applied. Missing ones under /data/system and /data/miuilog are made in the
# guest's own /data with the rc's mode and owners; names the guest's
# passwd/group files lack fall back to system.
# GUEST_SYSTEM_EXT and GUEST_PRODUCT, never system/system_ext or system/product:
# HyperOS has both at its root and system/ links to them with absolute links,
# which here on the host are One UI's folders (r7 checked those, found no
# miui-services.jar and made nothing: eighth HyperOS run, "mkdirs failed" again).
if [ -e "$GUEST_SYSTEM_EXT/framework/miui-services.jar" ]; then
    aid() { # <name> <passwd or group file>: the id
        case "$1" in
            root) echo 0 ;; system) echo 1000 ;; radio) echo 1001 ;; bluetooth) echo 1002 ;;
            graphics) echo 1003 ;; input) echo 1004 ;; audio) echo 1005 ;; camera) echo 1006 ;;
            log) echo 1007 ;; wifi) echo 1010 ;; media) echo 1013 ;; media_rw) echo 1023 ;;
            audioserver) echo 1041 ;; cameraserver) echo 1047 ;; shell) echo 2000 ;; cache) echo 2001 ;;
            *) i=$(awk -F: -v n="$1" '$1 == n {print $3; exit}' "$2" 2>/dev/null)
               case "$i" in ''|*[!0-9]*) echo 1000 ;; *) echo "$i" ;; esac ;;
        esac
    }
    made=0
    for f in "$ROOTFS"/system/etc/init/*.rc "$GUEST_SYSTEM_EXT"/etc/init/*.rc "$GUEST_PRODUCT"/etc/init/*.rc; do
        [ -f "$f" ] && [ ! -L "$f" ] && cat "$f"
    done | awk '$1 == "mkdir" && $2 ~ /^\/data\/(system|miuilog)(\/|$)/ && $2 !~ /[$.][.]|[$]/ { sub(/\/$/, "", $2); print $2, ($3 ~ /^[0-7]+$/ ? $3 : "0771"), ($4 == "" ? "root" : $4), ($5 == "" ? ($4 == "" ? "root" : $4) : $5) }' |
        sort -u -k1,1 > "$STAGE/miui_data_dirs.txt"
    while read -r p mode u g; do
        d="$STAGE$p"
        [ -e "$d" ] || [ -L "$d" ] && continue
        # Root runs this on the host: never through a link the guest made.
        q="$STAGE/data"; ok=1
        for part in $(echo "${p#/data/}" | tr '/' ' '); do
            q="$q/$part"; [ -L "$q" ] && { ok=0; break; }
        done
        [ $ok = 1 ] || { echo "HyperOS /data folder $p: a link on the way, skipped"; continue; }
        mkdir -p "$d" && chmod "$mode" "$d" && chown "$(aid "$u" "$ROOTFS/system/etc/passwd"):$(aid "$g" "$ROOTFS/system/etc/group")" "$d" &&
            made=$((made + 1))
    done < "$STAGE/miui_data_dirs.txt"
    echo "HyperOS /data folders from its init rc files: $made made ($(wc -l < "$STAGE/miui_data_dirs.txt") listed)"
    rm -f "$STAGE/miui_data_dirs.txt"
fi

# Device states for the guest. Its DeviceStateProviderImpl reads /odm (the
# container has none), then /data/system/devicestate, then the host's
# /vendor/etc/devicestate (run 30: 0 CLOSE and 3 OPEN on the lid switch).
# ONEOS_GUEST_DEVICE_STATES=oneos keeps those ids and lid conditions and adds
# the properties the guest framework uses with device_state_property_migration
# (on, read-only, in the guest's aconfig_flags.pb): WindowManager counts
# OUTER_PRIMARY as folded and INNER_PRIMARY as open, TRIGGER_WAKE on 3 wakes the
# screen on unfold. State 0 has no TRIGGER_SLEEP, so folding moves ColorOS to
# the cover instead of sleeping (ColorOS itself only sleeps on fold with
# continue_using_apps_when_folded=2). vendor (default for now) = run 30.
DSDIR="$STAGE/data/system/devicestate"
DS_DEFAULT=vendor
FOLD8_COLOR_HINGE=0
# 0.4.38: the Z Fold8 runs the Find N6 global image with n6-f8u too (n6-f8's UI
# patches were the CN build's); its hinge stays.
# The Z Fold8 Ultra (n6-f8u) has the same lid states (0 CLOSE, 3 OPEN) and the
# same sensor ("Folding Angle  Non-wakeup", 65686, read on SM-F976B 2026-10-26).
if grep -q '^  "image": "coloros17-findn6",$' "$STAGE/.oneos_stage" &&
        { { [ "${ONEOS_PROFILE:-}" = f8 ] && grep -q -e '^  "set": "n6-f8",$' -e '^  "set": "n6-f8u",$' -e '^  "set": "n6-global-f8",$' "$STAGE/.oneos_stage"; } ||
          { [ "${ONEOS_PROFILE:-}" = f8u ] && grep -q '^  "set": "n6-f8u",$' "$STAGE/.oneos_stage"; }; }; then
    DS_DEFAULT=fold8-hinge
    FOLD8_COLOR_HINGE=1
fi
# vivo OriginOS on a Fold (ro.vivo.device.type=foldable, guest_props.sh): vivo's
# framework, SystemUI and launcher count 1 as OPEN and 0 as CLOSE (Samsung's 3
# reads as folded in vivo's launcher), so its own file has those ids on the lid
# switch. No TRIGGER_SLEEP: folding moves to the cover (patches/vivo_guards.py
# drops vivo's sleep on leaving OPEN). ONEOS_GUEST_DEVICE_STATES=vendor keeps 0/3.
if [ -f "$ROOTFS/system/framework/vivo-services.jar" ] && [ "$FORM" = fold ] && [ "${ONEOS_GUEST_VIVO_FOLD:-1}" = 1 ]; then
    DS_DEFAULT=vivo
fi
if [ "$FOLD8_COLOR_HINGE" = 1 ] && [ "${ONEOS_GUEST_DEVICE_STATES:-$DS_DEFAULT}" = fold8-hinge ]; then
    mkdir -p "$DSDIR"
    cat > "$DSDIR/device_state_configuration.xml" <<'F8DSX'
<?xml version="1.0" encoding="utf-8"?>
<!-- OneOS Fold8 / Fold8 Ultra ColorOS hinge. Lid switch owns closed/open panels. -->
<device-state-config>
    <device-state>
        <identifier>0</identifier><name>CLOSE</name>
        <properties>
            <property>com.android.server.policy.PROPERTY_FOLDABLE_HARDWARE_CONFIGURATION_FOLD_IN_CLOSED</property>
            <property>com.android.server.policy.PROPERTY_FOLDABLE_DISPLAY_CONFIGURATION_OUTER_PRIMARY</property>
        </properties>
        <conditions><lid-switch><open>false</open></lid-switch></conditions>
    </device-state>
    <device-state>
        <identifier>1</identifier><name>TENT</name>
        <properties>
            <property>com.android.server.policy.PROPERTY_FOLDABLE_HARDWARE_CONFIGURATION_FOLD_IN_CLOSED</property>
            <property>com.android.server.policy.PROPERTY_FOLDABLE_DISPLAY_CONFIGURATION_OUTER_PRIMARY</property>
        </properties>
        <conditions><lid-switch><open>false</open></lid-switch></conditions>
    </device-state>
    <device-state>
        <identifier>2</identifier><name>HALF_OPENED</name>
        <properties>
            <property>com.android.server.policy.PROPERTY_FOLDABLE_HARDWARE_CONFIGURATION_FOLD_IN_HALF_OPEN</property>
            <property>com.android.server.policy.PROPERTY_FOLDABLE_DISPLAY_CONFIGURATION_INNER_PRIMARY</property>
        </properties>
        <conditions>
            <lid-switch><open>true</open></lid-switch>
            <sensor>
                <type>com.samsung.sensor.folding_angle</type>
                <name>Folding Angle  Non-wakeup</name>
                <value><min-inclusive>15</min-inclusive><max-inclusive>165</max-inclusive></value>
            </sensor>
        </conditions>
    </device-state>
    <device-state>
        <identifier>3</identifier><name>OPEN</name>
        <properties>
            <property>com.android.server.policy.PROPERTY_FOLDABLE_HARDWARE_CONFIGURATION_FOLD_IN_OPEN</property>
            <property>com.android.server.policy.PROPERTY_FOLDABLE_DISPLAY_CONFIGURATION_INNER_PRIMARY</property>
        </properties>
        <conditions><lid-switch><open>true</open></lid-switch></conditions>
    </device-state>
</device-state-config>
F8DSX
    chown 1000:1000 "$DSDIR" "$DSDIR/device_state_configuration.xml"
    chmod 644 "$DSDIR/device_state_configuration.xml"
    echo "Guest device states: fold hinge (0 closed, 2 half-open 15..165 degrees, 3 open)"
elif [ "${ONEOS_GUEST_DEVICE_STATES:-$DS_DEFAULT}" = oneos ]; then
    mkdir -p "$DSDIR"
    cat > "$DSDIR/device_state_configuration.xml" <<'DSX'
<?xml version="1.0" encoding="utf-8"?>
<!-- OneOS (guest_prepare.sh): Samsung's lid-switch states with OPPO/AOSP fold properties. -->
<device-state-config>
    <device-state>
        <identifier>0</identifier>
        <name>CLOSE</name>
        <properties>
            <property>com.android.server.policy.PROPERTY_FOLDABLE_HARDWARE_CONFIGURATION_FOLD_IN_CLOSED</property>
            <property>com.android.server.policy.PROPERTY_FOLDABLE_DISPLAY_CONFIGURATION_OUTER_PRIMARY</property>
        </properties>
        <conditions>
            <lid-switch>
                <open>false</open>
            </lid-switch>
        </conditions>
    </device-state>
    <device-state>
        <identifier>3</identifier>
        <name>OPEN</name>
        <properties>
            <property>com.android.server.policy.PROPERTY_FOLDABLE_HARDWARE_CONFIGURATION_FOLD_IN_OPEN</property>
            <property>com.android.server.policy.PROPERTY_FOLDABLE_DISPLAY_CONFIGURATION_INNER_PRIMARY</property>
            <property>com.android.server.policy.PROPERTY_POWER_CONFIGURATION_TRIGGER_WAKE</property>
        </properties>
        <conditions>
            <lid-switch>
                <open>true</open>
            </lid-switch>
        </conditions>
    </device-state>
</device-state-config>
DSX
    chown 1000:1000 "$DSDIR" "$DSDIR/device_state_configuration.xml"
    chmod 644 "$DSDIR/device_state_configuration.xml"
    echo "Guest device states: OneOS file (0 CLOSE = lid closed, 3 OPEN = lid open)"
elif [ "${ONEOS_GUEST_DEVICE_STATES:-$DS_DEFAULT}" = vivo ]; then
    mkdir -p "$DSDIR"
    cat > "$DSDIR/device_state_configuration.xml" <<'VDSX'
<?xml version="1.0" encoding="utf-8"?>
<!-- OneOS (guest_prepare.sh): Samsung's lid switch with vivo's ids (0 CLOSE, 1 OPEN). -->
<device-state-config>
    <device-state>
        <identifier>0</identifier>
        <name>CLOSE</name>
        <properties>
            <property>com.android.server.policy.PROPERTY_FOLDABLE_HARDWARE_CONFIGURATION_FOLD_IN_CLOSED</property>
            <property>com.android.server.policy.PROPERTY_FOLDABLE_DISPLAY_CONFIGURATION_OUTER_PRIMARY</property>
        </properties>
        <conditions>
            <lid-switch>
                <open>false</open>
            </lid-switch>
        </conditions>
    </device-state>
    <device-state>
        <identifier>1</identifier>
        <name>OPEN</name>
        <properties>
            <property>com.android.server.policy.PROPERTY_FOLDABLE_HARDWARE_CONFIGURATION_FOLD_IN_OPEN</property>
            <property>com.android.server.policy.PROPERTY_FOLDABLE_DISPLAY_CONFIGURATION_INNER_PRIMARY</property>
        </properties>
        <conditions>
            <lid-switch>
                <open>true</open>
            </lid-switch>
        </conditions>
    </device-state>
</device-state-config>
VDSX
    chown 1000:1000 "$DSDIR" "$DSDIR/device_state_configuration.xml"
    chmod 644 "$DSDIR/device_state_configuration.xml"
    echo "Guest device states: vivo (0 CLOSE = lid closed, 1 OPEN = lid open)"
else
    # The staged /data persists between sessions: never leave an old file behind.
    rm -f "$DSDIR/device_state_configuration.xml"
fi

echo "=== 5.13 $(date +%T) device states ==="
# HyperOS's device states. Its DeviceStateProviderImpl (Xiaomi's change) reads
# product/etc/devicestate/device_state_configuration.xml, whose states all wait
# on Xiaomi's hinge sensor (xiaomi.sensor.fold_status). This phone has none:
# "No declared device states match any of the required conditions", no state
# was ever committed, DisplayManager stayed on the inner panel's default layout
# and the cover screen never came on (seventh HyperOS run). A copy with
# Xiaomi's ids, names and properties is bound over it in the guest's view:
# 0 (CLOSED) on the lid switch closed and 3 (OPENED) on it open, like
# Samsung's own 0 and 3; the other states that waited on the sensor (TENT,
# HALF_OPENED) can only be requested (PROPERTY_EMULATED_ONLY). guest_start.sh
# writes the matching display layout.
# The guest's own product (r7 looked under system/product, One UI's /product
# from here, and bound nothing: no device state was ever committed in the
# eighth run either, "Failed to find Sensor with type: xiaomi.sensor.fold_status").
HDSC="$GUEST_PRODUCT/etc/devicestate/device_state_configuration.xml"
if [ -e "$GUEST_SYSTEM_EXT/framework/miui-services.jar" ] && [ -f "$HDSC" ] && [ ! -L "$HDSC" ] &&
   grep -q 'xiaomi.sensor.fold_status' "$HDSC" && [ "${ONEOS_GUEST_FORM:-fold}" = fold ]; then
    awk '
        function flush(   i, out) {
            if (n == 0) return
            for (i = 1; i <= n; i++) {
                if (skip[i]) continue
                out = buf[i]
                if (emul && buf[i] ~ /<\/properties>/)
                    print "            <property>com.android.server.policy.PROPERTY_EMULATED_ONLY</property>"
                print out
                if (lid != "" && buf[i] ~ /<\/properties>/) {
                    print "        <conditions>"
                    print "            <lid-switch>"
                    print "                <open>" lid "</open>"
                    print "            </lid-switch>"
                    print "        </conditions>"
                }
            }
            n = 0
        }
        /<device-state>/ { flush(); inst = 1; id = ""; cond = 0; n = 0; emul = 0; lid = "" }
        !inst { print; next }
        {
            buf[++n] = $0; skip[n] = 0
            if ($0 ~ /<identifier>/) { id = $0; gsub(/[^0-9]/, "", id) }
            if ($0 ~ /<conditions>/) cond = 1
            if (cond) skip[n] = 1
            if ($0 ~ /<\/conditions>/) {
                cond = 0
                if (id == "0") lid = "false"; else if (id == "3") lid = "true"; else emul = 1
            }
            if ($0 ~ /<\/device-state>/) { flush(); inst = 0 }
        }
        END { flush() }' "$HDSC" > "$STAGE/hyperos_device_state.xml"
    if grep -q '<lid-switch>' "$STAGE/hyperos_device_state.xml" && ! grep -q 'xiaomi.sensor' "$STAGE/hyperos_device_state.xml"; then
        chmod 644 "$STAGE/hyperos_device_state.xml"
        $BB mount --bind "$STAGE/hyperos_device_state.xml" "$HDSC" &&
            echo "Guest device states: HyperOS's file on the lid switch (0 CLOSED closed, 3 OPENED open; $(grep -c 'PROPERTY_EMULATED_ONLY' "$STAGE/hyperos_device_state.xml") request-only)"
    else
        echo "!!! HyperOS device states: the copy did not come out as expected, the image's file is left (no cover screen)"
    fi
fi

# SELinux labels matter just as much as modes here. Every directory below lives
# under /data/local/tmp, so it is created as u:object_r:shell_data_file:s0. The
# guest's system_server runs in u:r:system_server:s0 (Samsung policy) and is
# denied both read and write on shell_data_file: chmod 777 does not help, because
# the denial is MAC, not DAC. That broke UserManagerService (users/0.xml EACCES),
# EntropyMixer/BatteryStats/PackageWatchdog ("Failed to create directory for
# *.new") and finally the settings provider:
#   SQLiteCantOpenDatabaseException: /data/user_de/0/com.android.providers.settings/databases/settings.db
# Relabel the staged tree the way a real /data is labeled. The host bind mounts
# that live inside this tree (/data/apex, /data/adb) are deliberately excluded
# so host data never gets relabeled.
# OneOS: every recursive relabel below is -h (no-dereference). busybox chcon
# follows a symlink to its target unless -h is given, so an absolute symlink a
# guest app left in its own data dir (e.g. ~/storage -> /storage/emulated/0, or
# a Termux alternatives link into /data/data/com.termux) would otherwise get its
# HOST target relabelled, and One UI's copy would lose access on return. The
# chown of /data/media is -h for the same reason.
echo "=== 5b. $(date +%T) Relabeling staged /data for guest SELinux ==="
$BB chcon u:object_r:system_data_file:s0 "$STAGE/data" 2>/dev/null || true
for d in data/system data/system_de data/system_ce \
         data/misc data/misc_de data/misc_ce data/anr data/dalvik-cache \
         data/local data/resource-cache data/app data/rollback data/incremental; do
    [ -e "$STAGE/$d" ] && $BB chcon -h -R u:object_r:system_data_file:s0 "$STAGE/$d" 2>/dev/null || true
done
# data/user and data/user_de are handled by app_data_labels below: resetting them
# recursively here would wipe the guest labels that pass is about to keep. Only
# the user dirs other than 0 need the blanket system_data_file label.
for d in data/user data/user_de; do
    [ -e "$STAGE/$d" ] || continue
    $BB chcon u:object_r:system_data_file:s0 "$STAGE/$d" 2>/dev/null || true
    for u in "$STAGE/$d"/*; do
        [ -e "$u" ] || continue
        case "${u##*/}" in
            0) ;;
            *) $BB chcon -h -R u:object_r:system_data_file:s0 "$u" 2>/dev/null || true ;;
        esac
    done
done
# OneOS (0.4.44): an app folder keeps the label the guest gave it. Until 0.4.43 every app
# folder went back to a bare "app_data_file:s0" here on each switch, and the guest's installd
# gave the categories back at boot only to the apps it prepared: the Theme Store on the Find N6
# global ColorOS kept the bare label, was refused its own databases (SQLITE_CANTOPEN, EACCES)
# and closed on Agree. A folder with a label the guest set (an *_data_file type, other than
# shell_data_file, system_data_file or a bare app/privapp_data_file) keeps it, files included,
# so files written here (the launcher grid, folders made above) get the app's label too. A
# bare or staged folder of an installed app gets the level seapp_contexts gives it: its own
# categories and the user's for an app targeting SDK 28+, the user's (c512,c768) for a
# privileged, platform or older app. Anything else is labelled as before.
# 0.4.86: the rule first took effect here. Until then data/user and data/user_de were
# reset to system_data_file as a whole just above, so no folder ever had a label to keep
# (0 kept in every one of 224 log lines of 39 reports). An installed app's folder with
# app_data_file and another uid's categories (its uid changed since) gets its own again.
app_data_labels() {
    ls -dZ "$1"/* 2>/dev/null | awk -v pl="$STAGE/data/system/packages.list" '
        BEGIN {
            while ((getline line < pl) > 0) {
                n = split(line, f, " ")
                if (n < 5 || f[2] !~ /^[0-9]+$/ || f[2] + 0 < 10000 || f[2] + 0 >= 20000) continue
                if (f[5] !~ /^(default|platform)(:privapp)?:targetSdkVersion=[0-9]+/) continue
                sdk = f[5]; sub(/.*targetSdkVersion=/, "", sdk); sub(/[^0-9].*/, "", sdk)
                a = f[2] - 10000
                if (f[5] ~ /^default:targetSdkVersion=/ && sdk + 0 >= 28)
                    lvl[f[1]] = "s0:c" (a % 256) ",c" (256 + int(a / 256) % 256) ",c512,c768"
                else
                    lvl[f[1]] = "s0:c512,c768"
            }
        }
        NF >= 2 {
            l = $1; p = $0; sub(/^[^ ]+ +/, "", p); pkg = p; sub(/.*\//, "", pkg)
            t = l; sub(/^u:object_r:/, "", t); sub(/:.*/, "", t)
            if (l ~ /^u:object_r:[a-z0-9_]+_data_file:s0(:c[0-9]+(,c[0-9]+)*)?$/ && t != "shell_data_file" &&
                t != "system_data_file" && l !~ /^u:object_r:(priv)?app_data_file:s0$/ &&
                !(t == "app_data_file" && (pkg in lvl) && l != "u:object_r:app_data_file:" lvl[pkg])) { w = l; kept++ }
            else if (pkg in lvl) { w = "u:object_r:app_data_file:" lvl[pkg]; given++ }
            else w = "u:object_r:app_data_file:s0"
            if (p ~ /^[A-Za-z0-9_.\/-]+$/) group[w] = group[w] " " p
            else print "1 " w " " p
        }
        END {
            for (w in group) print "n " w group[w]
            print "# " kept + 0 " " given + 0
        }'
}
p=$($BB nproc 2>/dev/null || nproc 2>/dev/null || echo 2)
case "$p" in ''|*[!0-9]*) p=2 ;; esac
[ "$p" -gt 8 ] && p=8
[ "$p" -lt 2 ] && p=2
for d in "$STAGE/data/user/0" "$STAGE/data/user_de/0"; do
    if [ -d "$d" ]; then
        $BB chcon u:object_r:system_data_file:s0 "$d" 2>/dev/null || true
        if ls -dZ "$d" >/dev/null 2>&1; then
            app_data_labels "$d" | {
                jobs=0
                kept=
                given=
                while read -r kind w rest; do
                    case "$kind" in
                        1) $BB chcon -h -R "$w" "$rest" 2>/dev/null &
                           jobs=$((jobs + 1)) ;;
                        n) $BB chcon -h -R "$w" $rest 2>/dev/null &
                           jobs=$((jobs + 1)) ;;
                        '#') kept=$w; given=$rest ;;
                    esac
                    if [ "$jobs" -ge "$p" ]; then
                        wait
                        jobs=0
                    fi
                done
                wait
                [ -z "$kept" ] || echo "App data labels in ${d#$STAGE/data/}: $kept kept as the guest set them, $given given their categories"
            }
        else
            $BB chcon -h -R u:object_r:app_data_file:s0 "$d"/* 2>/dev/null || true
        fi
    fi
done
$BB chown -h -R 1023:1023 "$STAGE/data/media" 2>/dev/null || true
$BB chmod 0770 "$STAGE/data/media" "$STAGE/data/media/0" 2>/dev/null || true
$BB chcon -h -R u:object_r:media_rw_data_file:s0 "$STAGE/data/media" 2>/dev/null || true
# data/apex (host /data/apex) and data/adb (host /data/adb) are left alone: they
# are the host's own directories bind-mounted in, already labeled correctly, and
# chcon-ing a bind mount would relabel the host's copy.

echo "=== 5c. $(date +%T) Fixing staged /data ownership and modes ==="
# The stage tree is created by root under /data/local/tmp, so its top-level
# directories come out root:root 0755. A real /data is system:system 0771, and
# system_server (uid 1000) has to be able to create /data/app/vmdl*.tmp:
#   Failed to prepare session dir: /data/app/vmdl10992519.tmp
# With 0755 root:root that mkdir gets EACCES and *every* install fails, which is
# what "non-system apps / downloads crash" looked like from the outside.
$BB chown system:system "$STAGE/data" 2>/dev/null || true
$BB chmod 0771 "$STAGE/data" 2>/dev/null || true
for d in app app-staging anr dalvik-cache incremental property resource-cache rollback ss system; do
    [ -e "$STAGE/data/$d" ] || mkdir -p "$STAGE/data/$d" 2>/dev/null || continue
    $BB chown system:system "$STAGE/data/$d" 2>/dev/null || true
    $BB chmod 0771 "$STAGE/data/$d" 2>/dev/null || true
done
mkdir -p "$STAGE/data/misc/profiles/cur/0" "$STAGE/data/misc/profiles/ref/0" 2>/dev/null || true
$BB chown system:system "$STAGE/data/misc" "$STAGE/data/misc/profiles" 2>/dev/null || true
for d in "$STAGE/data/misc/profiles/cur" "$STAGE/data/misc/profiles/ref" \
         "$STAGE/data/misc/profiles/cur/0" "$STAGE/data/misc/profiles/ref/0"; do
    [ -d "$d" ] && $BB chown system:system "$d" 2>/dev/null || true
done

# Pixel guest only (an image with oplus-services.jar is ColorOS, unchanged).
# After 5b and 5c, which relabel and re-own the staged trees every session.
GUEST_OPLUS=0
{ [ -e "$ROOTFS/system/framework/oplus-services.jar" ] || [ -L "$ROOTFS/system/framework/oplus-services.jar" ]; } && GUEST_OPLUS=1
[ "$GUEST_OPLUS" = 1 ] || echo "=== 5c2. One UI's preferred APNs and Bluetooth pairings for the guest ==="
# Preferred (attach) APN per SIM, from One UI: oneos_switch.sh recorded
# host_pref_apn ("slot mcc mnc apn") while One UI's telephony provider ran.
# Runs 41 and 42: with no preferred APN for SIM 2 (a fresh stage) Pixel's
# DataProfileManager took the carrier's first APN, web1, as the LTE attach APN;
# SIM 2 left LTE a second later and stayed on 3G for the session. One UI and
# ColorOS attach with web2. Picking it in Settings once the session runs is too
# late (the modem has given up on LTE by then), and that pick stays in the stage.
# So before every boot the guest's TelephonyProvider (com.android.providers.
# telephony, user_de/0, uid radio) gets One UI's APN in its preferred-full-apn
# prefs: apn<sub>, mcc<sub> and mnc<sub> as strings, every other <field><sub>
# removed; and apn_id<sub> / explicit_set_called<sub> are dropped from
# preferred-apn. With no saved id, getPreferredApnId looks the APN up by the
# fields present (getString(field + sub)) and keeps it when exactly one APN
# matches (web2: one, row 8 in run 42); no match leaves the guest's own
# choice, as before. Guest sub = slot + 1 (runs 41 and 42; the UI activator logs
# the guest's mapping). Android's SharedPreferences text XML; a .bak left by an
# interrupted write is what Android would load, so it is taken first. Never
# through a link. ONEOS_GUEST_APN=0 keeps the guest's own APNs.
TP_DIR="$STAGE/data/user_de/0/com.android.providers.telephony"
TP_PREFS="$TP_DIR/shared_prefs"
# <prefs file> <sub> ids|fields [<apn> <mcc> <mnc>]: one SharedPreferences file
# rewritten without apn_id<sub> / explicit_set_called<sub> (ids) or without any
# <field><sub> and with the three strings (fields). 0 done, 1 left as it was.
apn_prefs() {
    p_f=$1; p_s=$2; p_mode=$3; p_a=$4; p_c=$5; p_n=$6
    p_new="$p_f.oneos-new"
    rm -f "$p_new"
    if [ -f "$p_f.bak" ] && [ ! -L "$p_f.bak" ]; then mv -f "$p_f.bak" "$p_f"; else rm -f "$p_f.bak"; fi
    [ -L "$p_f" ] && rm -f "$p_f"
    p_src=/dev/null
    if [ -f "$p_f" ]; then
        [ "$(head -c 5 "$p_f")" = "<?xml" ] || return 1
        p_src=$p_f
    elif [ "$p_mode" = ids ]; then
        return 0
    fi
    # Field names end in a letter or _, so the trailing digits are the sub id
    # (apn12 is sub 12's, never sub 2's).
    awk -v s="$p_s" -v mode="$p_mode" -v a="$p_a" -v c="$p_c" -v n="$p_n" \
        -v hdr="<?xml version='1.0' encoding='utf-8' standalone='yes' ?>" '
        function drop(nm,   p) {
            if (mode == "ids") return nm == "apn_id" s || nm == "explicit_set_called" s
            if (length(nm) <= length(s) || substr(nm, length(nm) - length(s) + 1) != s) return 0
            p = substr(nm, 1, length(nm) - length(s))
            return p ~ /^[a-z_]([a-z0-9_]*[a-z_])?$/
        }
        function add() {
            if (mode != "fields") return
            print "    <string name=\"apn" s "\">" a "</string>"
            print "    <string name=\"mcc" s "\">" c "</string>"
            print "    <string name=\"mnc" s "\">" n "</string>"
        }
        skip { if (index($0, "</string>")) skip = 0; next }
        match($0, / name="[^"]*"/) && drop(substr($0, RSTART + 7, RLENGTH - 8)) {
            if ($0 ~ /<string / && !index($0, "</string>") && $0 !~ /\/>[ \t]*$/) skip = 1
            next
        }
        /<map[ \t]*\/>/ { print "<map>"; add(); print "</map>"; next }
        /<\/map>/ { add(); print; next }
        { print }
        END { if (NR == 0) { print hdr; print "<map>"; add(); print "</map>" } }' "$p_src" > "$p_new" &&
        grep -q '</map>' "$p_new" || { rm -f "$p_new"; return 1; }
    if [ "$p_mode" = fields ]; then
        for p_kv in "apn$p_s>$p_a" "mcc$p_s>$p_c" "mnc$p_s>$p_n"; do
            [ "$(grep -c -F " name=\"${p_kv%%>*}\"" "$p_new")" = 1 ] &&
                [ "$(grep -c -F "<string name=\"${p_kv%%>*}\">${p_kv#*>}</string>" "$p_new")" = 1 ] || { rm -f "$p_new"; return 1; }
        done
    elif grep -q -F -e " name=\"apn_id$p_s\"" -e " name=\"explicit_set_called$p_s\"" "$p_new"; then
        rm -f "$p_new"; return 1
    fi
    chown 1001:1001 "$p_new" && chmod 0660 "$p_new" && mv -f "$p_new" "$p_f" || { rm -f "$p_new"; return 1; }
    $BB chcon u:object_r:radio_data_file:s0 "$p_f" 2>/dev/null || $BB chcon u:object_r:app_data_file:s0 "$p_f" 2>/dev/null || true
    return 0
}
if [ "$GUEST_OPLUS" = 1 ]; then
    :
elif [ "${ONEOS_GUEST_APN:-1}" != 1 ]; then
    echo "Guest attach APN: the guest's own (ONEOS_GUEST_APN=0)"
elif [ ! -s "$STAGE/host_pref_apn" ] || [ -L "$STAGE/host_pref_apn" ]; then
    echo "Guest attach APN: the guest's own (no preferred APN read from One UI)"
elif [ -L "$TP_DIR" ] || [ -L "$TP_PREFS" ]; then
    echo "WARNING: ${TP_PREFS#$STAGE/} or its folder is a symlink; guest attach APN not seeded"
else
    if [ ! -d "$TP_PREFS" ]; then
        mkdir -p "$TP_PREFS" && chown 1001:1001 "$TP_DIR" "$TP_PREFS" && chmod 0771 "$TP_PREFS"
        $BB chcon u:object_r:radio_data_file:s0 "$TP_DIR" "$TP_PREFS" 2>/dev/null || true
    fi
    while read -r slot mcc mnc apn rest; do
        case "$slot:$mcc:$mnc" in
            [0-7]:[0-9][0-9][0-9]:[0-9][0-9]|[0-7]:[0-9][0-9][0-9]:[0-9][0-9][0-9]) ;;
            *) echo "Guest attach APN: host_pref_apn line '$slot $mcc $mnc' not used"; continue ;;
        esac
        case "$apn" in
            ''|*[!A-Za-z0-9._-]*) echo "Guest attach APN: slot $slot APN name not used (unexpected characters)"; continue ;;
        esac
        [ -z "$rest" ] && [ ${#apn} -le 100 ] || { echo "Guest attach APN: host_pref_apn line for slot $slot not used"; continue; }
        sub=$((slot + 1))
        if apn_prefs "$TP_PREFS/preferred-full-apn.xml" "$sub" fields "$apn" "$mcc" "$mnc" &&
           apn_prefs "$TP_PREFS/preferred-apn.xml" "$sub" ids; then
            echo "Guest attach APN: slot $slot (sub $sub) -> $apn ($mcc $mnc, from One UI)"
        else
            echo "WARNING: Guest attach APN: slot $slot (sub $sub) not seeded (unexpected prefs file in ${TP_PREFS#$STAGE/}); the guest's own stays"
        fi
    done < "$STAGE/host_pref_apn"
fi
# Bluetooth pairings (run 42): the guest's stack starts from its own
# bt_config.conf, so none of One UI's paired devices were there, and pairing
# one of them again in the guest replaces that device's key for this phone (both
# systems have the phone's one Bluetooth address): One UI's pairing would stop
# working. So One UI's /data/misc/bluedroid/bt_config.conf (paired devices and
# their keys) is copied one way into the guest's stage copy at every switch:
# only a regular file, never through a link; only the stage's file is replaced,
# nothing is ever copied back, and a guest-only pairing lasts until the next
# switch. bluetooth 1002:1002 0660, bluetooth_data_file; a bt_config.bak from
# the guest's last session (the stack falls back to it) is deleted.
# ONEOS_GUEST_BT_IMPORT=0 keeps the guest's file (through the LE check below).
# Run 43, the first run with the import: One UI's LE keys are not in the layout
# the Pixel stack reads (LE_KEY_PID = 16-byte IRK, address type 00 or 01, the
# identity address). Every device's PID decoded to type 149, 181 or 13 and a
# made-up identity address (earbuds xx:xx -> yy:yy), and the stack used it anyway:
# Java and native sent A2DP, HFP and the pairing record itself to that address,
# so A2DP had no active peer (no Bluetooth audio session, PAL -19 on every
# write), HFP never got its service-level connection and SCO was refused. So
# the stage file is now One UI's through BT_SAN_AWK: if any device's LE_KEY_PID
# is not that layout with its own address, the file's LE layout is not the
# guest's (a car kit's LE_KEY_PENC was refused too), so every device loses its
# LE records (LE_*, Le*, AddrType, ServiceLe, GATT caching, LE Audio, CSIP,
# hearing aid, VCP), LE-only devices (DevType 2) are dropped and dual-mode ones
# become BR/EDR (DevType 3 -> 1); BR/EDR link keys stay. An AOSP-layout file
# passes unchanged. If the filter or the check after it fails, the guest starts
# with no pairings (the stage's bt_config.conf and .bak deleted): never an
# unchecked copy, and never run 43's stage file (One UI's bad PID data plus the
# guest's own key for the earbuds). ONEOS_GUEST_BT_LE_SANITIZE=0 skips the LE part (since
# run 44 the link key check below still runs). diag_bt/ gets the shape of One
# UI's file and of the guest's previous one (BT_SHAPE_AWK: key names, value
# lengths, hex or not, small type values, where the device's own address sits
# in LE_KEY_PID), never a key value or a full address. Run 43 also had the
# imported link key rejected (HCI_ERR_AUTH_FAILURE at the earbuds' first
# connection); the earbuds then asked to pair again and the guest's stack
# auto-accepted it, which replaced their key for this phone and broke One UI's
# pairing. Never pair One UI's devices in the guest (docs/pixel-guest.md).
# Run 44: One UI's link keys are not AOSP's. diag_bt/shape_oneui.txt has
# LinkKey len=64 hex (32 bytes) for both BR/EDR devices, and One UI's LE keys
# are 64 hex too; the Pixel stack's own (shape_guest_prev.txt) is 32 hex (16
# bytes). The stack found no usable key: HCI_ERR_AUTH_FAILURE, "Bond loss
# detected ... KEY_MISSING", autonomous re-pairing, three pairing dialogs, and
# a CsipSetCoordinatorService.bondStateChanged NPE that took the Bluetooth
# process down (17:32:08 to 17:35:21); the earbuds now hold a guest key and
# need pairing again in One UI. So the import is off by default
# (ONEOS_GUEST_BT_IMPORT=1 turns it on), and BT_SAN_AWK drops every device
# whose LinkKey is not exactly 32 hex chars, whichever file it reads: the
# stage's own file kept One UI's imported records with their 64-hex keys
# across the guest's own saves (run 43's, shape_guest_prev.txt device 1), and
# such a record goes through the same KEY_MISSING and re-pairing as soon as
# that device connects. A key the Pixel stack wrote is always 32 hex, so the
# guest's own pairings stay as they are.
BTC=/data/misc/bluedroid/bt_config.conf
BTD="$STAGE/data/misc/bluedroid"
BTDIAG="$STAGE/diag_bt"
# Every guest: the stage's folder and file are never One UI's own (a hard link
# of the file, or the folder reached another way than the checks at the top
# refuse). Nothing below, and no guest stack, may write to them.
if [ "$BTD" -ef /data/misc/bluedroid ] || { [ -e "$BTC" ] && [ "$BTD/bt_config.conf" -ef "$BTC" ]; }; then
    echo "ERROR: ${BTD#$STAGE/} or its bt_config.conf is One UI's own Bluetooth config; not starting the guest"
    exit 3
fi
rm -rf "$BTDIAG"
# Shared by both filters. A device section is [xx:xx:xx:xx:xx:xx] (written out:
# mawk and older busybox awk have no {n}).
BT_AWK_FN='function hex(s) { s = tolower(s); gsub(/[^0-9a-f]/, "", s); return s }
function isdev(s) { return s ~ /^\[[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]\]$/ }
function key(s) { sub(/[ \t]*=.*$/, "", s); return s }
function val(s) { sub(/^[^=]*=[ \t]*/, "", s); sub(/[ \t\r]+$/, "", s); return s }
'
# Names, lengths and layout facts only: a section or key name that is not a
# plain word is not shown, value= only for small numbers, and a device is its
# number plus the last two bytes of its address (as logcat masks it). For
# LE_KEY_PID: byte 16 (the AOSP address type) and the byte offset of the
# device's own address, as written and reversed (17 and - in AOSP's layout).
BT_SHAPE_AWK='function rev(a,   r, i) { r = ""; for (i = length(a) - 1; i >= 1; i -= 2) r = r substr(a, i, 2); return r }
function pos(h, a,   i) { for (i = 1; i + 11 <= length(h); i += 2) if (substr(h, i, 12) == a) return (i - 1) / 2; return "-" }
function name(k) { return (k ~ /^[A-Za-z_][A-Za-z0-9_]*$/ && length(k) <= 48 && !(length(k) >= 8 && k ~ /^[0-9A-Fa-f]+$/)) ? k : "(name not shown, " length(k) " chars)" }
/^\[/ { dev = isdev($0); a = hex($0)
    if (dev) print "[device " ++nd " xx:xx:xx:xx:" substr($0, 14); else print "[" name(substr($0, 2, length($0) - 2)) "]"
    next }
/=/ { k = key($0); v = val($0); x = (v ~ /^[0-9A-Fa-f]+$/) ? "hex" : "txt"; e = ""
    if (dev && x == "hex" && k == "LE_KEY_PID") { h = tolower(v); e = " byte16=" substr(h, 33, 2) " self_at=" pos(h, a) " self_rev_at=" pos(h, rev(a)) }
    if ((k == "DevType" || k == "AddrType" || k == "LinkKeyType" || k ~ /PairingAlgorithm$/) && v ~ /^[0-9]+$/ && length(v) <= 3) e = " value=" v
    printf "  %s len=%d %s%s\n", name(k), length(v), x, e
    next }
/[^ \t\r]/ { print "  (line without =, " length($0) " chars)" }'
# One UI's file is read once and kept in memory. A device whose LinkKey is not
# 32 hex chars (16 bytes, AOSP's form; One UI writes 64) is dropped whole (run
# 44), always. bad = devices whose LE_KEY_PID is not 23 bytes (IRK, type
# 00/01, the device's own address); with any, every device loses its LE
# records, LE-only devices are dropped and dual-mode ones become BR/EDR. A
# device dropped for its link key does not count: in the stage's own file
# those are One UI's leftovers (run 43's device 1 had a bad PID too), and they
# must not strip the LE keys of the pairings the guest made itself. LE=0
# (ONEOS_GUEST_BT_LE_SANITIZE=0) skips the LE part. The summary line goes to SUM.
BT_SAN_AWK='{ L[NR] = $0 }
/^\[/ { sec = $0; dev = isdev(sec); if (dev) ndev++; next }
dev && LE == 1 && /^LE_KEY_PID[ \t]*=/ { p = tolower(val($0)); t = substr(p, 33, 2)
    if (length(p) != 46 || p ~ /[^0-9a-f]/ || (t != "00" && t != "01") || substr(p, 35, 12) != hex(sec)) badpid[sec] = 1 }
dev && /^DevType[ \t]*=/ && val($0) == "2" { leonly[sec] = 1 }
dev && /^LinkKey[ \t]*=/ { lk = val($0); if (length(lk) != 32 || lk ~ /[^0-9A-Fa-f]/) badkey[sec] = 1 }
END { bad = 0; for (s in badpid) if (!(s in badkey)) bad++
    sec = ""; dev = 0; drop = 0
    for (i = 1; i <= NR; i++) { l = L[i]
        if (l ~ /^\[/) { sec = l; dev = isdev(sec); drop = 0
            if (dev && (sec in badkey)) { drop = 1; keygone++ }
            else if (bad && dev && (sec in leonly)) { drop = 1; gone++ } }
        if (drop) continue
        if (bad && dev && l !~ /^\[/) {
            k = key(l)
            if (k ~ /^(LE_|Le[A-Z]|AddrType$|Services?Le$|Gatt|Csis|HearingAid|Sink|Source|VolumeControl|Bass)/) { cut[sec] = 1; continue }
            if (k == "DevType" && val(l) == "3") { print "DevType = 1"; continue }
        }
        print l }
    n = 0; for (s in cut) n++
    printf "%d devices, %d with a LinkKey not in AOSP form (32 hex) dropped, ", ndev, keygone > SUM
    if (LE == 1) printf "%d LE_KEY_PID not in the guest layout: LE records removed from %d, %d LE-only dropped\n", bad, n, gone > SUM
    else printf "LE check off (ONEOS_GUEST_BT_LE_SANITIZE=0)\n" > SUM }'
# The stage's bt_config.conf from $1 (One UI's file, or the stage's own) through
# BT_SAN_AWK, via a temp file: the link key check always, the LE check unless
# ONEOS_GUEST_BT_LE_SANITIZE=0. A failure, or no [Adapter] in the result,
# deletes the stage's file and .bak: no pairings, never an unchecked file. Only
# the stage's folder is written; $1 is only read.
bt_stage_conf() {
    rm -f "$BTD/bt_config.conf.oneos-new" "$BTD/bt_config.bak"
    bt_le=1; [ "${ONEOS_GUEST_BT_LE_SANITIZE:-1}" = 0 ] && bt_le=0
    if $BB awk -v SUM="$BTDIAG/sanitize.txt" -v LE="$bt_le" "$BT_AWK_FN$BT_SAN_AWK" "$1" > "$BTD/bt_config.conf.oneos-new" &&
       grep -q '^\[Adapter\]' "$BTD/bt_config.conf.oneos-new" &&
       chown 1002:1002 "$BTD/bt_config.conf.oneos-new" && chmod 0660 "$BTD/bt_config.conf.oneos-new" &&
       mv -f "$BTD/bt_config.conf.oneos-new" "$BTD/bt_config.conf"; then
        $BB chcon u:object_r:bluetooth_data_file:s0 "$BTD/bt_config.conf" 2>/dev/null || true
        return 0
    fi
    rm -f "$BTD/bt_config.conf.oneos-new" "$BTD/bt_config.conf" "$BTD/bt_config.bak"
    return 1
}
# Run 44: no import unless ONEOS_GUEST_BT_IMPORT=1 (see above).
bt_own=0
if [ "$GUEST_OPLUS" = 1 ]; then
    :
elif [ "${ONEOS_GUEST_BT_IMPORT:-0}" != 1 ]; then
    echo "Guest Bluetooth pairings: the guest's own; One UI's are not imported (its link keys are not in AOSP form; ONEOS_GUEST_BT_IMPORT=1 imports them)"
    bt_own=1
elif [ -L /data/misc/bluedroid ] || [ -L "$BTC" ] || [ ! -f "$BTC" ]; then
    echo "Guest Bluetooth pairings: One UI's bt_config.conf is missing or not a regular file; the guest's own stays"
    bt_own=1
elif [ -L "$BTD" ] || [ ! -d "$BTD" ]; then
    echo "WARNING: ${BTD#$STAGE/} is missing or a symlink; One UI's Bluetooth pairings not copied"
else
    mkdir -p "$BTDIAG"
    if [ -f "$BTD/bt_config.conf" ] && [ ! -L "$BTD/bt_config.conf" ]; then
        $BB awk "$BT_AWK_FN$BT_SHAPE_AWK" "$BTD/bt_config.conf" > "$BTDIAG/shape_guest_prev.txt" 2>&1
    fi
    $BB awk "$BT_AWK_FN$BT_SHAPE_AWK" "$BTC" > "$BTDIAG/shape_oneui.txt" 2>&1
    if bt_stage_conf "$BTC"; then
        echo "Guest Bluetooth pairings: One UI's imported (ONEOS_GUEST_BT_IMPORT=1), never copied back; $(cat "$BTDIAG/sanitize.txt" 2>/dev/null)"
    else
        echo "WARNING: One UI's Bluetooth pairings not imported (the checks failed, or no [Adapter]); the guest starts with no pairings"
    fi
fi
# The guest's own file gets the same checks (run 44 review): the stage's file
# from runs 43 and 44 still holds One UI's records, LE ones with the bad PIDs
# and BR/EDR ones with 64-hex link keys (the guest's stack saved what it had
# loaded), so with no import, or no file in One UI, they would come back. A
# file the Pixel stack wrote from its own pairings passes unchanged.
if [ $bt_own = 1 ] && [ ! -L "$BTD" ] && [ -d "$BTD" ] &&
   [ -f "$BTD/bt_config.conf" ] && [ ! -L "$BTD/bt_config.conf" ]; then
    mkdir -p "$BTDIAG"
    $BB awk "$BT_AWK_FN$BT_SHAPE_AWK" "$BTD/bt_config.conf" > "$BTDIAG/shape_guest_prev.txt" 2>&1
    if bt_stage_conf "$BTD/bt_config.conf"; then
        echo "Guest Bluetooth pairings: the guest's own after the checks; $(cat "$BTDIAG/sanitize.txt" 2>/dev/null)"
    else
        echo "WARNING: the guest's own Bluetooth pairings failed the checks (or have no [Adapter]); the guest starts with no pairings"
    fi
fi
# Which of the guest's own devices One UI has paired too (run 45). A device
# keeps one key for the phone's one Bluetooth address, so once One UI has
# paired it again (as asked after run 44), the guest's key for it is out of
# date: at its first connection in the guest it fails authentication and the
# stack asks to pair again (run 44's bond loss and pairing dialogs), and
# accepting unpairs it in One UI. Counted, with the last two address bytes as
# logcat shows them, and One UI's file's shape in diag_bt/shape_oneui.txt (no
# key value, no full address). One UI's file is only read, as for the import.
if [ $bt_own = 1 ] && [ ! -L /data/misc/bluedroid ] && [ ! -L "$BTC" ] && [ -f "$BTC" ] &&
   [ ! -L "$BTD" ] && [ -f "$BTD/bt_config.conf" ] && [ ! -L "$BTD/bt_config.conf" ]; then
    mkdir -p "$BTDIAG"
    $BB awk "$BT_AWK_FN$BT_SHAPE_AWK" "$BTC" > "$BTDIAG/shape_oneui.txt" 2>&1
    both=$($BB awk "$BT_AWK_FN"'FILENAME == ARGV[1] { if (isdev($0)) one[tolower($0)] = 1; next }
        isdev($0) { n++; if (tolower($0) in one) { b++; s = s ", xx:xx:xx:xx:" substr($0, 14, 5) } }
        END { printf "%d of the %d devices paired in the guest%s", b, n, (b ? " (" substr(s, 3) ")" : "") }' "$BTC" "$BTD/bt_config.conf" 2>/dev/null)
    echo "Guest Bluetooth pairings: ${both:-not compared}: also paired in One UI (if One UI paired one again after the guest did, the guest's key is out of date: a pairing request at its first connection in the guest, and accepting it unpairs it in One UI)"
fi

echo "=== 5d. $(date +%T) Bridging host /data app and storage trees into the staged /data ==="
# installd and artd are HOST daemons (started by Samsung init, they cannot be
# moved into the container namespace). Left alone they create every app data
# dir, dalvik-cache entry and dexopt profile in the real /data, which the guest
# can never see - so every app process the guest zygote forks dies with:
#   Failed to mount /data_mirror/data_de/null/0/<pkg> to /data/user_de/0/<pkg>:
#   No such file or directory
# ("Failed to attach" / "start timeout" in ActivityManager.) Bind the staged
# equivalents over those host paths for the duration of the session, so those
# daemons write into the guest's data. One UI is not running meanwhile and
# return_to_oneui.sh removes the binds again.
# OneOS: /data/data and /data/media as well. For user 0, installd's CE app data
# path is /data/data, not /data/user/0, and in run 25 the guest's
# destroyUserData(0) went through the host installd into One UI's real
# /data/data and /data/media. Host path:stage path.
# $BRIDGES comes from bridges.sh (sourced at the top).
for pair in $BRIDGES; do
    h=${pair%%:*}; s=${pair#*:}
    mkdir -p "$STAGE/data/$s" 2>/dev/null || true
    if [ -d "/data/$h" ] && ! mount | grep -q " /data/$h "; then
        $BB mount --bind "$STAGE/data/$s" "/data/$h" 2>/dev/null && echo "Bridged /data/$h -> $STAGE/data/$s"
    fi
done
# Every one of them must now be the staged copy, or the guest is not started.
unbridged=""
for pair in $BRIDGES; do
    h=${pair%%:*}; s=${pair#*:}
    [ -e "/data/$h" ] || continue
    [ "$(stat -c %d:%i "/data/$h" 2>/dev/null)" = "$(stat -c %d:%i "$STAGE/data/$s" 2>/dev/null)" ] || unbridged="$unbridged /data/$h"
done
if [ -n "$unbridged" ]; then
    echo "ERROR: not bridged to the staged copy:$unbridged; not starting the guest"
    exit 3
fi
echo "All host data trees bridged to the staged copies ($BRIDGES)"

mount | grep -q "$ROOTFS/data " || $BB mount --bind "$STAGE/data" "$ROOTFS/data"
# OneOS: private before anything is mounted beneath it. $STAGE/data lives on
# the host's shared /data, so this bind joins /data's peer group and the binds
# below propagated back into the host as /data/local/tmp/oneos/data/apex
# etc.: One UI's live /data/apex (its decompressed APEXes) showed up inside the
# stage tree, and One UI's APEXes read back with I/O errors afterwards.
$BB mount --make-private "$ROOTFS/data"
mount | grep -q "$ROOTFS/data/adb " || $BB mount --bind /data/adb "$ROOTFS/data/adb"
mount | grep -q "$ROOTFS/data/apex " || $BB mount --bind /data/apex "$ROOTFS/data/apex"
# OneOS: both read-only for the guest. /data/adb is the root manager's own
# (ksud, modules, allowlist); nothing the container runs has to write it now
# that guest_start.sh uses data/oneos_bin/busybox (takeover.log has both binds'
# options and the guest's su -c id). Only host apexd writes /data/apex, from
# One UI's namespace, which this bind does not change. remount,bind changes
# this one bind, never the /data filesystem; checked below: host /data must
# still be read-write. ONEOS_GUEST_DATA_ADB_RW=1 / ONEOS_GUEST_DATA_APEX_RW=1
# keep a bind writable (not with ONEOS_APP).
for d in adb apex; do
    case "$d" in
        adb) knob=ONEOS_GUEST_DATA_ADB_RW; keep=${ONEOS_GUEST_DATA_ADB_RW:-0} ;;
        *) knob=ONEOS_GUEST_DATA_APEX_RW; keep=${ONEOS_GUEST_DATA_APEX_RW:-0} ;;
    esac
    [ "$keep" = 1 ] && [ "${ONEOS_APP:-0}" != 1 ] && { echo "Host /data/$d stays writable in the guest ($knob=1)"; continue; }
    # With the source given: busybox looks a lone target up in /proc/mounts and
    # gives up ('can't find ... in /proc/mounts', run 36a). nosuid,nodev,noatime
    # again, or the remount drops them. Never toybox mount here: it answered
    # EBUSY, a superblock remount of /data, not of this bind.
    r=$($BB mount -o remount,bind,ro,nosuid,nodev,noatime "/data/$d" "$ROOTFS/data/$d" 2>&1) ||
        echo "remount of the /data/$d bind failed: $r"
    opts=$(awk -v p="$ROOTFS/data/$d" '$5 == p {print $6}' /proc/self/mountinfo | tail -n 1)
    case ",$opts," in
        *,ro,*) echo "Host /data/$d read-only in the guest" ;;
        *) echo "WARNING: host /data/$d stays writable in the guest (bind options: ${opts:-none})"
           # The root manager's data must not be writable from the guest.
           [ "$d" = adb ] && [ "${ONEOS_APP:-0}" = 1 ] && { echo "ERROR: not starting the guest with host /data/adb writable"; exit 3; } ;;
    esac
done
# The remounts must not have touched host /data itself (its own bind options
# and the filesystem's), or One UI's /data would be read-only.
DATA_MNT=$(awk '$5 == "/data" {print $6}' /proc/self/mountinfo | tail -n 1)
DATA_SB=$(awk '$5 == "/data" {print $NF}' /proc/self/mountinfo | tail -n 1)
DATA_BAD=""
case ",$DATA_MNT," in *,rw,*) ;; *) DATA_BAD=1 ;; esac
case ",$DATA_SB," in *,rw,*) ;; *) DATA_BAD=1 ;; esac
if [ -n "$DATA_BAD" ]; then
    echo "ERROR: host /data is not read-write any more ($DATA_MNT / $DATA_SB); not starting the guest (the return reboots)"
    exit 3
fi
# $ROOTFS/data/media is the staged $STAGE/data/media (section 5), not the
# phone's: the guest never gets the real shared storage.

# KernelSU inside the guest (0.4.39). The guest's KernelSU manager (oneos_switch.sh
# installs One UI's) runs ksud as root; from here its init-level commands reach
# the phone's own init, One UI's: soft-reboot stops every service (One UI's HALs
# with the guest's), resets sys.boot_completed and runs the module stages, and
# post-fs-data, services, boot-completed, late-load, unload, uninstall and the
# boot-image commands are One UI's boot. And One UI's modules are One UI's: a
# guest system keeps its own (owner: separate per system).
# So in this namespace /data/adb is a tmpfs: One UI's entries bound read-only,
# except modules and modules_update, which are this system's own folders in its
# data (data/oneos_ksu; guest_modules.sh applies them to this system's tree), and
# ksud, which is a wrapper: a soft reboot becomes a request to oneos_switch.sh's
# watcher (oneos.guest.powerctl; guest_softreboot.sh restarts this system only),
# those commands are refused, the rest is the real ksud (bound read-only at
# /data/oneos_ksu/ksud.real; the manager's own bundled copy is replaced with the
# same wrapper by the UI activator). su is not affected: KernelSU's su runs
# /system/bin/sh, and the guest's /system/xbin/su is its own copy (section 6).
# Every mount here is under the guest's private tree and made private itself;
# init's mount table is checked afterwards, and all of it undone if anything
# reached One UI's /data/adb.
if [ -f /data/adb/ksud ] && [ "${ONEOS_GUEST_KSUD_WRAP:-1}" = 1 ]; then
    KW="$STAGE/data/oneos_ksu"
    GA="$ROOTFS/data/adb"
    mkdir -p "$KW/modules" "$KW/modules_update" && chmod 755 "$KW" && chmod 755 "$KW/modules" "$KW/modules_update"
    cat > "$KW/ksud" <<'KSUDWRAP'
#!/system/bin/sh
# OneOS: KernelSU's ksud inside a guest system. Commands that drive init would
# act on the phone's own init (One UI's), so they never run from here.
case "$1" in
    soft-reboot)
        setprop oneos.guest.powerctl "ksud:soft-reboot"
        echo "OneOS: soft reboot of this system requested"
        exit 0 ;;
    post-fs-data|services|boot-completed|late-load|unload|uninstall|install|insmod|boot-patch|boot-patch-v2|boot-restore)
        echo "OneOS: 'ksud $1' acts on One UI's boot; not run inside this system" >&2
        exit 1 ;;
    debug)
        # The manager's root shell asks for the global mount namespace, which is
        # One UI's (init's): module lists and installs there would be One UI's.
        # This system's own namespace instead (its /data/adb view, its modules).
        if [ "$2" = su ]; then
            shift 2
            n=$#
            for a in "$@"; do case "$a" in -g|--global-mnt) ;; *) set -- "$@" "$a" ;; esac; done
            shift $n
            set -- debug su "$@"
        fi ;;
esac
exec /data/oneos_ksu/ksud.real "$@"
KSUDWRAP
    chmod 755 "$KW/ksud"
    : > "$KW/ksud.real" 2>/dev/null
    # ksud's module commands (list, install, uninstall, enable, disable, action)
    # first enter the mount namespace of pid 1, as format!("/proc/{}/ns/mnt", 1):
    # from a guest that is One UI's init, whatever namespace they were run in. In
    # 0.4.39 test4 two modules installed in ColorOS landed in One UI's
    # /data/adb/modules_update. This kernel has no pid namespaces, and a mount
    # namespace file cannot be bound into a newer namespace, so the guest's ksud is
    # a copy whose format string reads /data/ instead of /proc/: pid 1's becomes
    # /data/1/ns/mnt, which in this system's data links to /proc/self/ns/mnt, its
    # own namespace. The template is checked byte by byte before and after; any
    # other ksud build leaves KernelSU out of this session.
    KG="$KW/ksud.guest"
    rm -f "$KG" "$KG.tmp"
    KT=''
    if cp /data/adb/ksud "$KG.tmp"; then
        KO=$(toybox grep -obaF /ns/mnt "$KG.tmp" 2>/dev/null | cut -d: -f1)
        if [ "$(echo "$KO" | grep -c .)" = 1 ] &&
           [ "$($BB dd if="$KG.tmp" bs=1 skip=$((KO - 9)) count=9 2>/dev/null | $BB od -An -tx1 | tr -d ' \n')" = 062f70726f632fc007 ]; then
            printf /data/ | $BB dd of="$KG.tmp" bs=1 seek=$((KO - 8)) conv=notrunc 2>/dev/null
            [ "$($BB dd if="$KG.tmp" bs=1 skip=$((KO - 9)) count=9 2>/dev/null | $BB od -An -tx1 | tr -d ' \n')" = 062f646174612fc007 ] &&
                chmod 755 "$KG.tmp" && mv "$KG.tmp" "$KG" && KT=1
        fi
    fi
    rm -f "$KG.tmp"
    mkdir -p "$STAGE/data/1/ns" && ln -sfn /proc/self/ns/mnt "$STAGE/data/1/ns/mnt"
    [ "$(readlink "$STAGE/data/1/ns/mnt")" = /proc/self/ns/mnt ] || KT=''
    ADB_HOST_MNT=$(grep -c ' /data/adb' /proc/1/mounts)
    awk '$2 ~ "^/data/adb" { print $2 }' /proc/1/mounts > "$STAGE/tmp/adb_mounts.before"
    ok=1
    [ "$KT" = 1 ] || { ok=0; echo "KernelSU in the guest: this ksud's module namespace switch was not found as expected; not patched"; }
    if [ $ok = 1 ] && $BB mount --make-private "$GA" && $BB mount -t tmpfs -o mode=0700,nosuid,nodev tmpfs "$GA" &&
       $BB mount --make-private "$GA"; then
        for e in $(ls -A /data/adb 2>/dev/null); do
            case "$e" in modules|modules_update) continue ;; esac
            if [ "$e" = ksud ]; then
                : > "$GA/ksud" && $BB mount --bind "$KW/ksud" "$GA/ksud" && $BB mount --make-private "$GA/ksud" || ok=0
            elif [ -L "/data/adb/$e" ]; then
                $BB cp -P "/data/adb/$e" "$GA/$e" 2>/dev/null
            elif [ -d "/data/adb/$e" ]; then
                mkdir "$GA/$e" && $BB mount --bind "/data/adb/$e" "$GA/$e" && $BB mount --make-private "$GA/$e" &&
                    $BB mount -o remount,bind,ro "/data/adb/$e" "$GA/$e" || ok=0
            elif [ -f "/data/adb/$e" ]; then
                : > "$GA/$e" && $BB mount --bind "/data/adb/$e" "$GA/$e" && $BB mount --make-private "$GA/$e" &&
                    $BB mount -o remount,bind,ro "/data/adb/$e" "$GA/$e" || ok=0
            fi
        done
        for d in modules modules_update; do
            mkdir "$GA/$d" && $BB mount --bind "$KW/$d" "$GA/$d" && $BB mount --make-private "$GA/$d" || ok=0
        done
        $BB mount --bind "$KG" "$ROOTFS/data/oneos_ksu/ksud.real" &&
            $BB mount -o remount,bind,ro "$KG" "$ROOTFS/data/oneos_ksu/ksud.real" || ok=0
    else
        ok=0
    fi
    [ "$(grep -c ' /data/adb' /proc/1/mounts)" = "$ADB_HOST_MNT" ] || ok=0
    if [ $ok = 1 ]; then
        echo "KernelSU in the guest: /data/adb is this system's view (One UI's entries read-only, its own modules in data/oneos_ksu, ksud the OneOS wrapper)"
    else
        # Undo all of it, One UI's side first if anything got there.
        for m in $(awk '$2 ~ "^/data/adb" { print $2 }' /proc/1/mounts | sort -r); do
            grep -qx "$m" "$STAGE/tmp/adb_mounts.before" || { $BB umount -l "$m" && echo "!!! KernelSU in the guest: $m had reached One UI's namespace; unmounted"; }
        done
        $BB umount -l "$ROOTFS/data/oneos_ksu/ksud.real" 2>/dev/null
        $BB umount -l "$GA" 2>/dev/null
        echo "KernelSU in the guest: view not set up; the guest's /data/adb stays One UI's, read-only (its KernelSU app is not installed this session)"
        rm -f "$KW/manager"
    fi
fi

echo "=== 5e. $(date +%T) Writing per-package data-dir helper ==="
# Apps installed before the /data bridge existed have no CE/DE data dirs in the
# guest tree, and the guest zygote refuses to fork them:
#   Failed to mount /data_mirror/data_de/null/0/<pkg> to /data/user_de/0/<pkg>
# This helper recreates the dirs for every package the guest knows about, with
# the uid PMS reports. oneos_switch.sh runs it once the container is up.
mkdir -p "$STAGE/data/local/tmp" 2>/dev/null || true
cat > "$STAGE/data/local/tmp/fix_app_dirs.sh" <<'FIXAPPDIRS'
#!/system/bin/sh
# Create missing CE/DE data dirs (and dexopt profile dirs) for every installed
# package, using the uid PMS reports. Idempotent.
created=0
profile_dirs=0
pkg=""
for tok in $(pm list packages -U 2>/dev/null); do
    case "$tok" in
        package:*) pkg="${tok#package:}"; uid="" ;;
        uid:*)     uid="${tok#uid:}" ;;
        *)         continue ;;
    esac
    [ -n "$pkg" ] && [ -n "$uid" ] || continue
    for d in "/data/user/0/$pkg" "/data/user_de/0/$pkg"; do
        [ -d "$d" ] && continue
        if mkdir -p "$d" 2>/dev/null; then
            chown "$uid:$uid" "$d" 2>/dev/null
            chmod 0700 "$d" 2>/dev/null
            created=$((created + 1))
        fi
    done
    for d in "/data/misc/profiles/cur/0/$pkg" "/data/misc/profiles/ref/0/$pkg"; do
        [ -d "$d" ] && continue
        if mkdir -p "$d" 2>/dev/null; then
            chown "$uid:$uid" "$d" 2>/dev/null
            chmod 0771 "$d" 2>/dev/null
            profile_dirs=$((profile_dirs + 1))
        fi
    done
    pkg=""; uid=""
done
echo "[fix_app_dirs] created $created data dirs, $profile_dirs profile dirs"

# Realign ownership of pre-existing data dirs with the uid PMS assigned.
# The staged /data tree was restored from a backup, so some app dirs are still
# owned by system:system with 0777 perms. ART then refuses to load any dex from
# them ("Writable dex file ... is not allowed"), and GMS/SQLite cannot chmod its
# own files ("FileUtils.setPermissions" warnings) and the app dies. Only dirs
# whose top-level owner is wrong are touched, so later boots stay cheap.
realigned=0
if [ -f /data/system/packages.list ]; then
    while read -r pkg auid rest; do
        case "$auid" in ''|*[!0-9]*) continue ;; esac
        for base in /data/user/0 /data/user_de/0; do
            d="$base/$pkg"
            [ -d "$d" ] || continue
            cur=$(stat -c %u "$d" 2>/dev/null)
            [ "$cur" = "$auid" ] && continue
            chown -h -R "$auid:$auid" "$d" 2>/dev/null
            chmod -R go-w "$d" 2>/dev/null
            realigned=$((realigned + 1))
        done
    done < /data/system/packages.list
fi
echo "[fix_app_dirs] realigned $realigned data dirs to their app uid"

# Navigation mode: ColorOS's SystemUI owns it (secure hide_navigationbar_enable,
# see the UI activator). Forcing the gestural overlay here kept ColorOS in
# 3-button mode with no buttons drawn (run 28). Only record the state.
echo "[fix_app_dirs] navigation: hide_navigationbar_enable=$(settings get secure hide_navigationbar_enable) navigation_mode=$(settings get secure navigation_mode)"

# OneOS: no SMS role write. OneLineage made LineageOS's com.android.messaging
# the default SMS app here on every boot; ColorOS has no such package (its own
# is com.android.mms) and keeps the user's choice.

# Bluetooth's GD stack asserts out of `storage_module.cc SaveImmediately` when
# it cannot persist its own config, and com.android.bluetooth then restarts
# every ~4 seconds for the rest of the session (1880 tombstones in one boot).
# The staged tree had no /data/misc/bluedroid at all; create it with the
# bluetooth uid (1002) so the stack can save bt_config.conf.
if [ ! -d /data/misc/bluedroid ]; then
    mkdir -p /data/misc/bluedroid /data/misc/bluetooth 2>/dev/null
    chown 1002:1002 /data/misc/bluedroid /data/misc/bluetooth 2>/dev/null
    chmod 0770 /data/misc/bluedroid /data/misc/bluetooth 2>/dev/null
    echo "[fix_app_dirs] created /data/misc/bluedroid for the bluetooth stack"
fi

# Code files must not be writable by the app that loads them. ART rejects any
# dex/apk/jar the calling uid could modify ("Writable dex file ... is not
# allowed"), which crash-looped GMS: its Dynamite modules in
# /data/user_de/0/.../app_chimera were installed 0755. The ownership pass above
# only touches dirs whose *top-level* owner is wrong, so GMS was skipped even
# though its files were wrong. Do this on both storages, cheaply.
code_files=0
for root in /data/user/0 /data/user_de/0; do
    [ -d "$root" ] || continue
    for f in $(find "$root" -type f \( -name '*.apk' -o -name '*.jar' -o -name '*.dex' \) -perm -0200 2>/dev/null); do
        chmod a-w "$f" 2>/dev/null && code_files=$((code_files + 1))
    done
done
echo "[fix_app_dirs] made $code_files code files read-only"

# The guest's Settings.Global.ADB_ENABLED defaults to null (treated as 0), and
# the guest's UsbDeviceManager drops the adb function from the USB gadget as
# soon as it starts. That is what kills the host adbd we rely on: adb dies
# seconds after the guest boots and macOS stops seeing the phone at all. Turn it
# on so the gadget keeps adb, and read back what actually happened.
# OneOS: only when One UI has USB debugging on (guest_prepare.sh leaves
# /data/oneos_host_adb then).
if [ -f /data/oneos_host_adb ]; then
    adb_before=$(getprop sys.usb.state)
    settings put global adb_enabled 1 2>/dev/null
    sleep 2
    echo "[fix_app_dirs] adb_enabled=1 (usb.state was '$adb_before', now '$(getprop sys.usb.state)')"
fi

# Record system services that failed to start (e.g. AdbService: "Failure
# starting ..."), so a problem behind a later crash can be traced without
# guessing from a fresh boot.
# SystemServer reports a service that threw during startup as
# "BOOT FAILURE starting X" (reportWtf) or "Failure starting X": catch both,
# plus anything mentioning AdbService, since that is the one we care about.
{
    logcat -d -b system 2>/dev/null | grep -a -E "BOOT FAILURE|Failure starting" | head -40
    echo "--- AdbService mentions ---"
    logcat -d -b system 2>/dev/null | grep -a -i "AdbService" | tail -10
} > /data/boot_failures.log 2>/dev/null || true
FIXAPPDIRS
chmod 755 "$STAGE/data/local/tmp/fix_app_dirs.sh" 2>/dev/null || true

# The guest has no installd, so nothing creates an app's data directories when
# it is installed. PMS records the package, then zygote aborts the first launch
# with "Failed to mount /data_mirror/data_de/null/0/<pkg> to
# /data/user_de/0/<pkg>: No such file or directory". Every app installed from
# inside the guest -- Play Store, Aurora, adb -- used to crash on launch this way.
# Create the scaffolding installd would; /data_mirror is a bind of these trees.
cat > "$STAGE/data/local/tmp/ensure_app_storage.sh" <<'ENSUREAPP'
#!/system/bin/sh
created=0
[ -f /data/system/packages.list ] || exit 0
realigned=0
while read -r pkg auid rest; do
    case "$auid" in ''|*[!0-9]*) continue ;; esac
    for d in "/data/user/0/$pkg:0771" "/data/user_de/0/$pkg:0700"; do
        p=${d%:*}; mode=${d##*:}
        if [ -d "$p" ]; then
            # Reinstalling a package can assign a NEW uid while the old data
            # dirs survive (uninstall has no installd to delete them), and the
            # app then fails with "SQLiteCantOpenDatabaseException: unable to
            # open database file" because it cannot write its own directory.
            cur=$(stat -c %u "$p" 2>/dev/null)
            if [ -n "$cur" ] && [ "$cur" != "$auid" ]; then
                chown -h -R "$auid:$auid" "$p" 2>/dev/null && realigned=$((realigned + 1))
            fi
            continue
        fi
        mkdir -p "$p" 2>/dev/null || continue
        chown "$auid:$auid" "$p" 2>/dev/null
        chmod "$mode" "$p" 2>/dev/null
        created=$((created + 1))
    done
    # External storage: owner is the app, group is ext_data_rw (1078).
    for kind in data media obb; do
        p="/data/media/0/Android/$kind/$pkg"
        if [ -d "$p" ]; then
            cur=$(stat -c %u "$p" 2>/dev/null)
            if [ -n "$cur" ] && [ "$cur" != "$auid" ]; then
                chown -h -R "$auid:1078" "$p" 2>/dev/null && realigned=$((realigned + 1))
            fi
            continue
        fi
        mkdir -p "$p" 2>/dev/null || continue
        chown "$auid:1078" "$p" 2>/dev/null
        chmod 0770 "$p" 2>/dev/null
        created=$((created + 1))
    done
done < /data/system/packages.list

# Shared storage skeleton. Without it MediaProvider cannot create
# /storage/emulated/0/Pictures/Screenshots and taking a screenshot crashes
# SystemUI ("Failed to create directory: .../.pending-NNN"), and every save
# dialog has nowhere to put its file.
for d in Pictures Pictures/Screenshots DCIM DCIM/Camera Movies Music Documents \
         Alarms Notifications Podcasts Ringtones Download; do
    p="/data/media/0/$d"
    [ -d "$p" ] && continue
    mkdir -p "$p" 2>/dev/null || continue
    chown 1023:1023 "$p" 2>/dev/null
    chmod 0775 "$p" 2>/dev/null
    created=$((created + 1))
done

if [ "$created" -gt 0 ] || [ "$realigned" -gt 0 ]; then
    echo "[ensure_app_storage] created $created dirs, realigned $realigned to new uids"
fi
exit 0
ENSUREAPP
chmod 755 "$STAGE/data/local/tmp/ensure_app_storage.sh" 2>/dev/null || true

# A new install only becomes launchable once the dirs above exist, so sweep
# while the guest is running instead of at boot only. Started by guest_start.
cat > "$STAGE/data/local/tmp/net_fix.sh" <<'NETFIX'
#!/system/bin/sh
# The guest's ConnectivityService cannot install its routes into the host's
# netd: every addRoute fails with "No such file or directory", so the final
# catch-all ip rule keeps pointing at a table from a previous network and all
# traffic ends in the "unreachable" rule. Symptom: the modem reports
# MOBILE[LTE] CONNECTED / VALIDATED, yet every app (Aurora, Play Store) says
# "check your internet connection" and even ping to the gateway fails.
# Keep a private table (4242) in sync with the live interface - wifi first,
# else mobile/CLAT - and point a catch-all rule at it. Idempotent.
# (Since guest_start.sh restarts netd, the guest's routes do reach netd's own
# tables; 0.4.58 limits the rule to what the phone itself sends, iif lo, so the
# hotspot's forwarded traffic keeps netd's tethering rules.)
# Usable = an IPv4 address AND a carrier. After One UI stops, wlan0 keeps One
# UI's DHCP address with the link down (run 28: 192.168.x.y on a "linkdown"
# wlan0 all session); picking it sent all traffic to a dead link.
usable() {
    [ "$(cat "/sys/class/net/$1/carrier" 2>/dev/null)" = 1 ] &&
        ip -4 addr show "$1" 2>/dev/null | grep -q "inet "
}
# Without Wi-Fi: the mobile interface netd made the default network (its rule
# "fwmark 0x0/0xffff iif lo lookup <if>"), then the first usable rmnet_data.
# The first one alone could be the IMS PDN (0.4.60 reports 5278f632, 4cc84045:
# 4242 on the IMS rmnet_data for a while, the phone's internet into the IMS APN).
iface=""
if usable wlan0; then
    iface=wlan0
else
    d=$(ip rule show 2>/dev/null | awk '/fwmark 0x0\/0xffff iif lo lookup rmnet_data/ {print $NF; exit}')
    case "$d" in rmnet_data*) usable "$d" && iface=$d ;; esac
    [ -n "$iface" ] || for d in $(ip -o link show 2>/dev/null | awk -F': ' '{print $2}' | sed 's/@.*//' | grep '^rmnet_data'); do
        if usable "$d"; then iface=$d; break; fi
    done
fi
[ -z "$iface" ] && exit 0
subnet=$(ip route show table all 2>/dev/null | awk -v d="$iface" \
    '$2=="dev" && $3==d && $0 ~ /scope link/ && $1 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\// {print $1; exit}')
[ -z "$subnet" ] && exit 0
gw=$(ip route show table all 2>/dev/null | awk -v d="$iface" \
    '$1=="default" && $2=="via" && $4=="dev" && $5==d && $3 ~ /^[0-9]+\./ {print $3; exit}')
case "$iface" in
    # Raw-IP link, no ARP: a device route is enough. Carriers hand out small
    # subnets (run 27: a /30), where a guessed ".1" gateway is not even inside.
    rmnet_data*) via="dev $iface" ;;
    # no IPv4 default anywhere (netd never installed one): assume the first host
    *) [ -z "$gw" ] && gw="${subnet%.*}.1"; via="via $gw dev $iface" ;;
esac
cur_if=$(ip route show table 4242 2>/dev/null | awk '$1=="default"{for(i=1;i<NF;i++) if($i=="dev"){print $(i+1); exit}}')
if [ "$cur_if" != "$iface" ]; then
    ip route flush table 4242 2>/dev/null
    echo "net route: table 4242 now uses $iface ($via), was ${cur_if:-none}"
fi
ip route replace "$subnet" dev "$iface" table 4242 2>/dev/null
ip route replace default $via table 4242 2>/dev/null
# The phone's other IPv4 subnets (the hotspot's swlan0, USB and Bluetooth
# tethering, Wi-Fi Direct) are not reached through the upstream: throw them out
# of 4242, so the lookup falls through to netd's own tables as on One UI.
# Without this, every reply the phone itself sends to a hotspot client (DNS
# from dnsmasq, ICMP) took 4242's default back out of the upstream (S25 Ultra
# ColorOS sessions 30124d7e and 516ef4ce: clients connected, no internet).
# Prefixes shorter than /8 are left alone (a VPN's 0.0.0.0/1 split routes).
want=$(ip route show table all 2>/dev/null | awk -v d="$iface" \
    '$2=="dev" && $3!=d && $0 ~ / scope link/ && $1 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\/([89]|[12][0-9]|3[0-2])$/ {print $1}' | sort -u)
have=$(ip route show table 4242 2>/dev/null | awk '$1=="throw"{print $2}')
for p in $have; do
    case " $(echo $want) " in *" $p "*) ;; *) ip route del throw "$p" table 4242 2>/dev/null ;; esac
done
for p in $want; do
    case " $(echo $have) " in
        *" $p "*) ;;
        *) ip route replace throw "$p" table 4242 2>/dev/null && echo "net route: $p stays on netd's routes (not $iface)" ;;
    esac
done
# Priority must beat the per-uid rules netd already installed for previous
# networks (15040/29040/29998): app sockets carry an fwmark, so a catch-all
# placed after those still sends them into a dead table even though root's
# unmarked pings work.
# Only what the phone itself sends (iif lo). Forwarded packets keep netd's
# rules: the tethering module's "iif swlan0 lookup <upstream>" and the route
# back to the client's subnet. "from all lookup 4242" sent every reply from
# the internet to a hotspot client back out of the upstream, where the FORWARD
# chain dropped it.
cur=$(ip rule show 2>/dev/null | awk '/^14999:/{print; exit}')
case "$cur" in
    *"iif lo lookup 4242"*) ;;
    *)
        for n in 1 2 3; do ip rule del priority 14999 2>/dev/null || break; done
        ip rule add iif lo lookup 4242 priority 14999 2>/dev/null
        ip rule del priority 31999 2>/dev/null
        echo "net route repaired: $iface $subnet gw $gw"
        ;;
esac
# Sockets bound to a mobile network on purpose (Samsung IMS's SIP to the
# P-CSCF, MMS) carry that network's netId in their fwmark; netd routes them
# with its explicit-network rules (priority 16000, "fwmark 0x1<netId>/0x1ffff
# iif lo lookup rmnet_dataN"), which come after 14999. 0.4.60 S918B Viettel
# (65e30c5c): every REGISTER to 10.204.64.81 left through table 4242's
# rmnet_data0 and ended in TimerF; the one REGISTER sent while 4242 happened to
# use the IMS interface got its 401 at once. The same rules again at 14998, so
# they win over 4242; a table without a matching route falls through to 14999
# as before. Only mobile interfaces; kept in step with netd's.
want=$(ip rule show 2>/dev/null | awk '$1 == "16000:" && / iif lo / && / fwmark / && $NF ~ /^rmnet_data/ { $1 = ""; sub(/^ +/, ""); print }')
have=$(ip rule show 2>/dev/null | awk '$1 == "14998:" { $1 = ""; sub(/^ +/, ""); print }')
echo "$have" | while read -r r; do
    [ -n "$r" ] || continue
    printf '%s\n' "$want" | grep -qxF "$r" || { ip rule del $r priority 14998 2>/dev/null && echo "net route: dropped 14998: $r"; }
done
echo "$want" | while read -r r; do
    [ -n "$r" ] || continue
    printf '%s\n' "$have" | grep -qxF "$r" || { ip rule add $r priority 14998 2>/dev/null && echo "net route: 14998: $r (bound sockets keep their network)"; }
done
exit 0
NETFIX
chmod 755 "$STAGE/data/local/tmp/net_fix.sh" 2>/dev/null || true

cat > "$STAGE/data/local/tmp/app_storage_loop.sh" <<'APPLOOP'
#!/system/bin/sh
# Watches for installs/removals, gives the new package its data dirs, and makes
# the launcher re-query so the app actually shows up.
last=""
while true; do
    sleep 10
    case "$(getprop sys.boot_completed)" in 1) ;; *) continue ;; esac
    netout=$(/system/bin/sh /data/local/tmp/net_fix.sh 2>/dev/null)
    [ -n "$netout" ] && echo "$(date) $netout" >> /data/app_storage.log
    cur=$(md5sum /data/system/packages.list 2>/dev/null | cut -d' ' -f1)
    out=$(/system/bin/sh /data/local/tmp/ensure_app_storage.sh 2>/dev/null)
    if [ -n "$last" ] && { [ "$cur" != "$last" ] || [ -n "$out" ]; }; then
        # A package appeared or went away. LauncherApps caches the app list, so
        # something installed from Aurora or Play Store is missing from both the
        # drawer and app search until the launcher re-queries. Restarting the
        # launcher forces that and does not touch whatever app is in front.
        am force-stop com.android.launcher3 2>/dev/null
        echo "$(date) package list changed -> launcher refreshed ${out:+($out)}" >> /data/app_storage.log
    elif [ -n "$out" ]; then
        echo "$(date) $out" >> /data/app_storage.log
    fi
    last=$cur
done
APPLOOP
chmod 755 "$STAGE/data/local/tmp/app_storage_loop.sh" 2>/dev/null || true

echo "=== 6. $(date +%T) Setting up /system/xbin/su (KernelSU Bridge) ==="
if ! mount | grep -q "$ROOTFS/system/xbin "; then
    if [ -f "$STAGE/data/oneos_root/enabled" ]; then
        $BB mount -t tmpfs tmpfs "$ROOTFS/system/xbin" || exit 3
    else
        $BB mount -t tmpfs tmpfs "$ROOTFS/system/xbin"
    fi
    # The guest's ksud copy (section 5d) when there is one: as su, its -M
    # (mount master) enters pid 1's namespace too, One UI's with the plain copy.
    if [ -f "$STAGE/data/oneos_root/enabled" ]; then
        # The isolated broker is the guest's su. A host provider can expose su
        # virtually through its kernel, leaving no regular host file to copy.
        SU_SRC="$STAGE/guest_root"
    else
        SU_SRC="$STAGE/data/oneos_ksu/ksud.guest"
        [ -f "$SU_SRC" ] || SU_SRC="/data/adb/ksud"
        [ -f "$SU_SRC" ] || SU_SRC=$(which su 2>/dev/null)
        [ -f "$SU_SRC" ] || SU_SRC=$(find /data/adb /system/bin -name su 2>/dev/null | head -n 1)
    fi
    if [ -f "$STAGE/data/oneos_root/enabled" ]; then
        cp "$SU_SRC" "$ROOTFS/system/xbin/su" && chmod 755 "$ROOTFS/system/xbin/su" || exit 3
        [ -x "$ROOTFS/system/xbin/su" ] || exit 3
    else
        [ -f "$SU_SRC" ] && cp "$SU_SRC" "$ROOTFS/system/xbin/su" && chmod 755 "$ROOTFS/system/xbin/su"
    fi
fi

echo "=== 7. $(date +%T) Setting up Fresh APEX tmpfs ==="
# Clean any stale submounts and ensure a clean, writable tmpfs
for m in $(cat /proc/mounts 2>/dev/null | grep "$ROOTFS/apex" | awk '{print $2}' | sort -r); do
    $BB umount -l "$m" 2>/dev/null || true
done
$BB umount -l "$ROOTFS/apex" 2>/dev/null || true
$BB mount -t tmpfs tmpfs "$ROOTFS/apex"

# NOTE: the list is only a hint; apexd (host daemon) owns the preinstalled set
# and PMS parses the paths it reports. That is why the host's apex directories
# are bound into this rootfs (see the /system_ext/apex and /system/apex binds):
# every path in this list must resolve after the pivot.
if [ -f "$STAGE/clean_apex_info_list.xml" ]; then
    cp "$STAGE/clean_apex_info_list.xml" "$ROOTFS/apex/apex-info-list.xml"
else
    cp -a /apex/apex-info-list.xml "$ROOTFS/apex/" 2>/dev/null || true
fi
chmod 644 "$ROOTFS/apex/apex-info-list.xml" 2>/dev/null || true

echo "=== 8. $(date +%T) Direct Mounting Extracted APEX Payloads ==="
rm -f "$STAGE/payload_loops"
mount_payload() {
    NAME="$1"
    TARGET="$2"
    IMG="$STAGE/${NAME}_payload.img"
    DEST="$ROOTFS/apex/$TARGET"
    # OneOS: from the app, only the payloads it staged and files.sha256 lists.
    # Extracting one here would leave an unlisted *_payload.img that the next
    # preflight refuses (and nothing checks what it extracted).
    # The module under OPPO's (AOSP) file names or Google's mainline ones
    # (global and Pixel images; same com.android.<name> inside), as in
    # scripts/make-overlays.sh. The compressed layouts carry original_apex.
    SRC=""
    for f in com.android.${NAME}.apex com.android.${NAME}.capex com.google.android.${NAME}.apex \
             com.google.android.${NAME}_compressed.apex com.google.android.${NAME}_tplus_compressed.apex; do
        [ -f "$ROOTFS/system/apex/$f" ] && { SRC="$ROOTFS/system/apex/$f"; break; }
    done
    # The cell broadcast service shares android.uid.networkstack with
    # tethering (always One UI's Google-signed module, see the list below) and
    # NetworkStack (One UI's NetworkStackGoogle, after section 9). A module built from source
    # (com.android.cellbroadcast.*: Infinity-X) is signed with the build's own
    # networkstack key, so system_server died in its first package scan (S25
    # Ultra session 26ea59af: "Signature mismatch on system package
    # com.android.cellbroadcastservice for shared user android.uid.networkstack").
    # The guest keeps One UI's module then, staged or not; Google's own (Pixel,
    # the X9U IN) is mounted as before.
    if [ "$NAME" = cellbroadcast ]; then
        case "$SRC" in
            */com.android.cellbroadcast.apex|*/com.android.cellbroadcast.capex)
                echo "cellbroadcast: the image's ${SRC##*/} is built from source, not Google's; One UI's module stays (android.uid.networkstack has one signer)"
                return 0 ;;
        esac
    fi
    if [ ! -f "$IMG" ] && [ "${ONEOS_APP:-0}" = 1 ]; then
        if [ -n "$SRC" ]; then
            echo "ERROR: the image has ${SRC##*/} but no ${NAME}_payload.img was staged; not starting the guest"
            exit 3
        fi
        return 0
    fi
    if [ ! -f "$IMG" ] && [ -n "$SRC" ]; then
        if $BB unzip -l "$SRC" 2>/dev/null | grep -q ' original_apex$'; then
            $BB unzip -p "$SRC" original_apex > "$STAGE/temp_${NAME}.apex" 2>/dev/null
            $BB unzip -p "$STAGE/temp_${NAME}.apex" apex_payload.img > "$IMG" 2>/dev/null
            rm -f "$STAGE/temp_${NAME}.apex"
        else
            $BB unzip -p "$SRC" apex_payload.img > "$IMG" 2>/dev/null
        fi
    fi
    [ -f "$IMG" ] || return 0
    if mount | grep "$DEST " | grep -q "/dev/block/dm-"; then
        $BB umount -l "$DEST" 2>/dev/null || true
        for vdir in "$ROOTFS/apex/${TARGET}"@*; do
       [ -d "$vdir" ] && $BB umount -l "$vdir" 2>/dev/null || true
        done
    fi
    if mount | grep "$DEST " | grep -q "/dev/block/loop"; then
        echo "$NAME already mounted on loop at $DEST"
        return 0
    fi
    mkdir -p "$DEST"
    $BB umount -l "$DEST" 2>/dev/null || true
    LOOP=$($BB losetup -f)
    # Read-only like system.raw: an ext4 payload mounted ro could still have
    # its journal replayed into the staged file (files.sha256).
    $BB losetup -r "$LOOP" "$IMG"
    # ColorOS ships erofs payloads; OneLineage assumed ext4.
    FSTYPE=ext4
    [ "$(od -An -tx4 -j1024 -N4 "$IMG" 2>/dev/null | tr -d ' ')" = "e0f5e1e2" ] && FSTYPE=erofs
    if ! $BB mount -t "$FSTYPE" -o ro "$LOOP" "$DEST"; then
        echo "!!! could not mount $NAME ($FSTYPE) from $IMG"
        $BB losetup -d "$LOOP" 2>/dev/null
        return 0
    fi
    echo "Direct mounted $NAME ($FSTYPE) on $LOOP -> $DEST"
    echo "$TARGET $LOOP $FSTYPE" >> "$STAGE/payload_loops"
    for vdir in "$ROOTFS/apex/${TARGET}"@*; do
        if [ -d "$vdir" ]; then
       $BB umount -l "$vdir" 2>/dev/null || true
       $BB mount -t "$FSTYPE" -o ro "$LOOP" "$vdir"
       echo "Direct mounted $NAME on $LOOP -> $vdir"
        fi
    done
}

mount_payload "art" "com.android.art"
mount_payload "i18n" "com.android.i18n"
mount_payload "runtime" "com.android.runtime"
mount_payload "sdkext" "com.android.sdkext"
mount_payload "nfcservices" "com.android.nfcservices"
# OneOS: tethering stays the HOST's module. Its BPF programs and maps were
# loaded at boot by the host's bpfloader for that module version; ColorOS's own
# connectivity module expects maps the host never pinned
# (map_netd_uid_permission_map and 7 more) and NetworkStatsService died on
# "Cannot open uid permission map". The rest of the networkstack shared-user
# group follows below.
mount_payload "crashrecovery" "com.android.crashrecovery"
mount_payload "cellbroadcast" "com.android.cellbroadcast"
mount_payload "extservices" "com.android.extservices"
mount_payload "permission" "com.android.permission"
mount_payload "wifi" "com.android.wifi"
mount_payload "appsearch" "com.android.appsearch"
mount_payload "mediaprovider" "com.android.mediaprovider"
mount_payload "adservices" "com.android.adservices"
mount_payload "rkpd" "com.android.rkpd"
mount_payload "healthfitness" "com.android.healthfitness"
mount_payload "ondevicepersonalization" "com.android.ondevicepersonalization"
mount_payload "configinfrastructure" "com.android.configinfrastructure"
mount_payload "bt" "com.android.bt"
# The image's own copies of modules One UI's build cannot serve it, only when
# make-overlays.sh staged them (Pixel: android.telecom lives in telephonycore;
# conscrypt and profiling match its ART and framework). Never extracted here.
for m in telephonycore conscrypt profiling; do
    [ -f "$STAGE/${m}_payload.img" ] && mount_payload "$m" "com.android.$m"
done
# The guest's apps compiled by the guest's own artd (guest_start.sh runs it for
# the session, again each time the lazy service exits). Without it the guest's
# ArtService (the image's ART module) got One UI's artd, which init starts when
# no artd is registered: another ART version, and every package failed dexopt
# with a NullPointerException from IArtd.maybeCreateSdc (Pixel, 268 times in
# session 9455098f; every ColorOS, HyperOS and Infinity-X session of 0.4.58 too),
# so every app ran uncompiled (more CPU, lag, heat). Only with the guest's own ART
# payload mounted and another version than One UI's module (apex_manifest.pb
# differs; the same module keeps One UI's artd, as before). One UI's artd itself
# is not touched: a bind over it changed One UI's /apex, which the mount check
# below refuses (0.4.59 test build: aborted, then the in-place return's
# failsafe rebooted the phone). ONEOS_GUEST_ARTD=0 starts no guest artd.
# 0.4.81: also when the ART module is the same version as One UI's. One UI's artd
# lives in init's mount namespace and sees One UI's /system, /product and /apex,
# not the guest's: 242 to 248 "Unable to open ... No such file" lines per boot in
# all 13 reports of 0.4.72 to 0.4.74 that kept it (ColorOS 17 on Android 16
# phones: A15 336e9373, A34 7e5896b0, A36 78cc52a6, S24 Ultra 425a0ee1, ...),
# none with the guest's own (1afdbfac, 65ca637a). The guest's system apps stayed
# uncompiled (lag and heat on the slow phones), and the first boot's dexopt sat
# for minutes behind One UI's dex2oat (A36 78cc52a6: a root module's dex2oat
# wrapper, "child process timed out after 570000ms", then the boot timeout).
# The guest's artd is the same binary there, run inside the guest.
rm -f "$STAGE/data/oneos_guest_artd"
if [ "${ONEOS_GUEST_ARTD:-1}" = 1 ] && [ -x "$ROOTFS/apex/com.android.art/bin/artd" ] &&
        grep -q '^com.android.art /dev/block/loop' "$STAGE/payload_loops" 2>/dev/null; then
    touch "$STAGE/data/oneos_guest_artd"
    if cmp -s /apex/com.android.art/apex_manifest.pb "$ROOTFS/apex/com.android.art/apex_manifest.pb"; then
        echo "artd: the guest's own for the session (the same ART module version as One UI's; One UI's artd cannot see the guest's files)"
    else
        echo "artd: the guest's own for the session (its ART module is another version than One UI's)"
    fi
else
    echo "artd: One UI's (ONEOS_GUEST_ARTD=${ONEOS_GUEST_ARTD:-1}; the guest's ART payload $(grep -q '^com.android.art ' "$STAGE/payload_loops" 2>/dev/null && echo mounted || echo 'not mounted'), $([ -x "$ROOTFS/apex/com.android.art/bin/artd" ] && echo 'its artd is there' || echo 'no artd in it'))"
fi
# The image's boot image accepted. guest_start.sh's zygote uses the image's AOT
# boot image (or the one its odrefresh step builds), which ART checks against the versions
# /apex/apex-info-list.xml gives the ART and i18n modules: "/" for a factory
# module. The list above is One UI's, where Play system updates made ART an
# updated module (isFactory="false", lastUpdateMillis), so ART rejected the
# image's boot image ("ValidateApexVersions found APEX versions mismatch") and
# every guest process, the zygote and each app started from it, compiled the
# boot class path in memory and ran the framework JIT-only (Pixel: lag and heat,
# session 9455098f). Those two modules are the image's own factory payloads
# here (payload_loops), so the guest's copy says so. The guest's copy only;
# a set's clean_apex_info_list.xml is left as it is.
if [ ! -f "$STAGE/clean_apex_info_list.xml" ] && [ -f "$ROOTFS/apex/apex-info-list.xml" ]; then
    FACT=""
    for m in com.android.art com.android.i18n; do
        grep -q "^$m /dev/block/loop" "$STAGE/payload_loops" 2>/dev/null && FACT="$FACT $m"
    done
    # lastUpdateMillis kept for the guest's odrefresh step: vivo since 0.4.73, every
    # system since 0.4.76 (the step runs for all now; ColorOS 17 trial on the owner's
    # Fold, 11-10: without it "odrefresh --compile" died on the same assertion).
    # ONEOS_GUEST_APEX_MILLIS=0 removes it from the image's two modules, as before.
    AKEEP=1; [ "${ONEOS_GUEST_APEX_MILLIS:-1}" = 0 ] && AKEEP=0
    if [ -n "$FACT" ] && awk -v mods="$FACT" -v akeep="$AKEEP" 'BEGIN { RS = "<"; ORS = ""; n = split(mods, a, " "); for (i = 1; i <= n; i++) want[a[i]] = 1 }
            NR > 1 { printf "<" }
            /^apex-info[[:space:]]/ && /isActive="true"/ { m = $0; sub(/.*moduleName="/, "", m); sub(/".*/, "", m)
                if (m in want) { sub(/isFactory="false"/, "isFactory=\"true\""); if (!akeep) gsub(/[[:space:]]lastUpdateMillis="[0-9]*"/, "") }
                # lastUpdateMillis stays (ART ignores it for a factory module) and every active
                # entry has one: the guest odrefresh (guest_start.sh) aborts on an entry
                # without it (twelfth OriginOS run: "assertion hasLastUpdateMillis() failed").
                if (akeep && $0 !~ /lastUpdateMillis="/) sub(/isActive="true"/, "isActive=\"true\" lastUpdateMillis=\"0\"") }
            { print }' "$ROOTFS/apex/apex-info-list.xml" > "$ROOTFS/apex/apex-info-list.xml.oneos" &&
            [ -s "$ROOTFS/apex/apex-info-list.xml.oneos" ]; then
        mv -f "$ROOTFS/apex/apex-info-list.xml.oneos" "$ROOTFS/apex/apex-info-list.xml"
        chmod 644 "$ROOTFS/apex/apex-info-list.xml"
        echo "Guest apex-info-list: the image's own$FACT as factory modules (the image's boot image matches them)"
    else
        rm -f "$ROOTFS/apex/apex-info-list.xml.oneos"
        echo "Guest apex-info-list: One UI's as it is (no image ART/i18n payload mounted)"
    fi
fi
# Google Play services (GMS_WANT, top): the image's own gmssystem payload, a
# Google module name, so not com.android.<name>. mount_payload looks for the
# APEX itself only in system/apex (Pixel's is in product/apex), so the staged
# payload is what it mounts. The payload_loops pass after section 9 puts it on
# the @<version> dirs too: the guest never reads One UI's own gmssystem module.
if [ "$GMS_WANT" = 1 ]; then
    mount_payload "gmssystem" "com.google.android.gmssystem"
fi

# Payload extractions above used the GSI's own /system/apex files. Now that the
# images are cached, present the HOST's /system/apex to the container so the
# preinstalled paths reported by host apexd all resolve (see the note above
# about /system_ext/apex).
if [ -d /system/apex ]; then
    mkdir -p "$ROOTFS/system/apex"
    # Bound already only if the folder at that path IS One UI's. A mount there is not enough:
    # guest root's copy of the system top level (kernels without overlayfs: the S22 series,
    # S23 FE, A25, A33, A53) has the image's own apex folder mounted at this path, so the bind
    # was left out and the guest's system_server died in its APEX scan on One UI's modules the
    # image does not have ("Unable to parse: /system/apex/com.android.bt.apex": every switch
    # with guest root on, A33 36686a70 and 7b1d653e, S22 Ultra 5172a6c3, 0.4.85 to 0.4.92).
    if [ "$(stat -c %d:%i "$ROOTFS/system/apex" 2>/dev/null)" != "$(stat -c %d:%i /system/apex 2>/dev/null)" ]; then
        if mount | grep -q "$ROOTFS/system/apex "; then
            echo "Host APEX files: One UI's /system/apex bound over the image's own folder (guest root's copy of the system top level)"
        fi
        $BB mount --bind /system/apex "$ROOTFS/system/apex" ||
            echo "!!! WARNING: One UI's /system/apex not bound on $ROOTFS/system/apex; PackageManagerService will fail on host apexes"
    fi
fi

echo "=== 9. $(date +%T) Bind-mounting Remaining Non-Payload APEXes ==="
# One /proc/mounts read, not one mount process per APEX: 104 iterations of
# mount | grep cost 9 s on the S25 Ultra.
APEX_MOUNTED=" $(awk -v root="$ROOTFS/apex/" 'index($2, root) == 1 { print substr($2, length(root) + 1) }' /proc/mounts | tr '\n' ' ') "
APEX_TODO=""
APEX_DIRS=""
for a in /apex/*; do
    [ -d "$a" ] || continue
    base=${a##*/}
    case "$base" in
        *samsung*)
       continue
       ;;
    esac
    case "$APEX_MOUNTED" in
        *" $base "*) continue ;;
    esac
    APEX_TODO="$APEX_TODO $base"
    APEX_DIRS="$APEX_DIRS $ROOTFS/apex/$base"
done
[ -z "$APEX_DIRS" ] || $BB mkdir -p $APEX_DIRS || true
for base in $APEX_TODO; do
    $BB mount --bind "/apex/$base" "$ROOTFS/apex/$base" 2>/dev/null || true
    echo "Bound $base -> $ROOTFS/apex/$base"
done

# OneOS: the versioned dirs (com.android.tethering@<version>, the paths host
# apexd reports to the guest's PackageManagerService) only exist now, so
# mount_payload's own @-loop never matched and they got the HOST's module from
# the binds above. The guest then saw its own NetworkStack next to Samsung's
# tethering APK: "Signature mismatch on system package
# com.google.android.networkstack.tethering for shared user
# android.uid.networkstack". Put the guest payload on them too.
if [ -f "$STAGE/payload_loops" ]; then
    while read -r TARGET LOOP FSTYPE; do
        for vdir in "$ROOTFS/apex/${TARGET}"@*; do
            [ -d "$vdir" ] || continue
            $BB umount -l "$vdir" 2>/dev/null || true
            $BB mount -t "${FSTYPE:-ext4}" -o ro "$LOOP" "$vdir" && echo "Guest payload $TARGET on $LOOP -> $vdir"
        done
    done < "$STAGE/payload_loops"
fi

# vivo's Wi-Fi code on One UI's connectivity module (OriginOS 6 CN): vivo's wifi
# APEX loads vivo-service-wifi.jar and vivo-service-wifi-ex.jar loads
# vivo-service-wifi-ex-impl.jar into system_server; both used transport 11 (vivo's
# second Wi-Fi), which One UI's tethering module refuses: system_server died making
# WifiService (first CN run), and vivo-service-wifi.jar calls five methods only
# vivo's CN connectivity module has. The patched ones (patches/vivo_wifi_connectivity.py)
# take vivo's overseas value and One UI's methods. After the payload mounts above,
# on every path of the guest's wifi module.
# libbluetooth_jni_patched.so (vivo's bt APEX, MediaTek's stack): the MediaTek-
# controller features off on Samsung's Qualcomm controller (make-overlays.sh; tenth
# CN run: Bluetooth crashed in HciLayer at every start).
if [ -f "$STAGE/libbluetooth_jni_patched.so" ]; then
    chmod 644 "$STAGE/libbluetooth_jni_patched.so"
    for vdir in "$ROOTFS/apex/com.android.bt" "$ROOTFS/apex/com.android.bt"@*; do
        BJ="$vdir/lib64/libbluetooth_jni.so"
        [ -f "$BJ" ] && [ ! -L "$BJ" ] || continue
        $BB umount -l "$BJ" 2>/dev/null || true
        $BB mount --bind "$STAGE/libbluetooth_jni_patched.so" "$BJ" &&
            echo "Bound libbluetooth_jni_patched.so -> $BJ (no MediaTek controller features)"
    done
fi
# framework-wifi_patched.jar (boot class path): VivoTrafficStats on vivo's overseas
# path (patches/vivo_traffic_stats.py): its natives read One UI's BPF stats maps with
# vivo's CN layout and aborted system_server (fourth CN run).
for VWN in vivo-service-wifi framework-wifi; do
    [ -f "$STAGE/${VWN}_patched.jar" ] || continue
    for vdir in "$ROOTFS/apex/com.android.wifi" "$ROOTFS/apex/com.android.wifi"@*; do
        VWJ="$vdir/javalib/$VWN.jar"
        [ -f "$VWJ" ] && [ ! -L "$VWJ" ] || continue
        $BB umount -l "$VWJ" 2>/dev/null || true
        $BB mount --bind "$STAGE/${VWN}_patched.jar" "$VWJ" &&
            echo "Bound ${VWN}_patched.jar -> $VWJ (vivo's Wi-Fi on One UI's connectivity module)"
    done
done
VWI="$ROOTFS/system/framework/vivo-service-wifi-ex-impl.jar"
if [ -f "$STAGE/vivo-service-wifi-ex-impl_patched.jar" ] && [ -f "$VWI" ] && [ ! -L "$VWI" ] && [ ! -L "$ROOTFS/system/framework" ]; then
    $BB umount -l "$VWI" 2>/dev/null || true
    $BB mount --bind "$STAGE/vivo-service-wifi-ex-impl_patched.jar" "$VWI" &&
        echo "Bound vivo-service-wifi-ex-impl_patched.jar -> $VWI (no transport 11)"
fi
for vdir in "$ROOTFS/apex/com.android.wifi" "$ROOTFS/apex/com.android.wifi"@*; do
    VWJ="$vdir/javalib/vivo-service-wifi.jar"
    if [ -f "$VWJ" ] && { [ ! -f "$STAGE/vivo-service-wifi_patched.jar" ] || [ ! -f "$STAGE/framework-wifi_patched.jar" ]; }; then
        echo "!!! WARNING: $VWJ is vivo's own and vivo-service-wifi_patched.jar or framework-wifi_patched.jar is not staged: system_server will die (transport 11, BPF map layout)"
        break
    fi
done

# The guest's own APEX payloads on One UI's /linkerconfig: its namespaces are linked
# from One UI's APEX manifests, and an image's module can need more (OriginOS CN:
# vivo's wifi APEX needs libnativehelper.so; third CN run: system_server died on an
# UnsatisfiedLinkError). A guest-only copy of ld.config.txt adds each missing
# requireNativeLibs entry (make-overlays.sh: oneos-apex-requires.txt) of the payloads
# mounted above, through the namespace the other namespaces of that section already
# take it from, as linkerconfig would. Bound on the guest's view only:
# $ROOTFS/linkerconfig is a slave of One UI's /linkerconfig, which the return checks.
GLD="$ROOTFS/linkerconfig/ld.config.txt"
if [ -f "$STAGE/oneos-apex-requires.txt" ] && [ -f "$STAGE/payload_loops" ] && [ -f "$GLD" ]; then
    $BB umount -l "$GLD" 2>/dev/null || true
    $BB awk 'NR == FNR { m[$1] = 1; next } ($1 in m) { $1 = ""; sub(/^ /, ""); print }' \
        "$STAGE/payload_loops" "$STAGE/oneos-apex-requires.txt" > "$STAGE/ld.config.guest.req"
    if $BB awk '
FNR == 1 { f++ }
f == 1 { for (i = 2; i <= NF; i++) req[$1] = req[$1] " " $i; next }
f == 2 && FNR == 1 { pass = 1 }
f == 3 && FNR == 1 {
    pass = 2
    for (k in exists) {
        split(k, a, SUBSEP); s = a[1]; ns = a[2]
        if (!(ns in req)) continue
        n = split(req[ns], libs, " ")
        for (i = 1; i <= n; i++) {
            lib = libs[i]
            if ((s SUBSEP ns SUBSEP lib) in have) continue
            hit = 0
            for (q in allowall) { split(q, b, SUBSEP); if (b[1] == s && b[2] == ns) hit = 1 }
            if (hit) continue
            best = ""; bc = 0
            m = split(provs[s SUBSEP lib], ps, " ")
            for (j = 1; j <= m; j++) if (ps[j] != ns && cnt[s SUBSEP lib SUBSEP ps[j]] > bc) { best = ps[j]; bc = cnt[s SUBSEP lib SUBSEP ps[j]] }
            if (best == "") { print "linker: [" s "] " ns ": no namespace provides " lib ", left out" > "/dev/stderr"; continue }
            addk = s SUBSEP ns SUBSEP best
            if (addk in add) v = add[addk] ":" lib; else v = lib
            add[addk] = v
            addp[s SUBSEP ns] = addp[s SUBSEP ns] " " best
            print "linker: [" s "] " ns " + " lib " from " best > "/dev/stderr"
        }
    }
}
/^\[[^]]*\]$/ { sec = substr($0, 2, length($0) - 2) }
pass == 1 {
    if (match($0, /^namespace\.[^.]+\./)) {
        ns = substr($0, 11, RLENGTH - 11); exists[sec SUBSEP ns] = 1
        rest = substr($0, RLENGTH + 1)
        if (rest ~ /^links *= */) { v = rest; sub(/^links *= */, "", v); links[sec SUBSEP ns] = "," v "," }
        else if (rest ~ /^link\.[^.]+\.shared_libs *= */) {
            p = rest; sub(/^link\./, "", p); sub(/\..*/, "", p)
            v = rest; sub(/^link\.[^.]+\.shared_libs *= */, "", v)
            n = split(v, ls, ":")
            for (i = 1; i <= n; i++) {
                have[sec SUBSEP ns SUBSEP ls[i]] = 1
                if (!((sec SUBSEP ls[i] SUBSEP p) in cnt)) provs[sec SUBSEP ls[i]] = provs[sec SUBSEP ls[i]] " " p
                cnt[sec SUBSEP ls[i] SUBSEP p]++
            }
        } else if (rest ~ /^link\.[^.]+\.allow_all_shared_libs *= *true/) {
            p = rest; sub(/^link\./, "", p); sub(/\..*/, "", p); allowall[sec SUBSEP ns SUBSEP p] = 1
        }
    }
    next
}
pass == 2 {
    line = $0
    if (match($0, /^namespace\.[^.]+\./)) {
        ns = substr($0, 11, RLENGTH - 11); rest = substr($0, RLENGTH + 1)
        if (rest ~ /^links *= */ && ((sec SUBSEP ns) in addp)) {
            n = split(addp[sec SUBSEP ns], ps, " "); newp = ""
            for (i = 1; i <= n; i++) {
                if (index(links[sec SUBSEP ns], "," ps[i] ",") || index(newp, " " ps[i] " ")) continue
                line = line "," ps[i]; newp = newp " " ps[i] " "
            }
            print line
            for (i = 1; i <= n; i++) if (index(newp, " " ps[i] " ") && !((sec SUBSEP ns SUBSEP ps[i]) in done)) {
                print "namespace." ns ".link." ps[i] ".shared_libs = " add[sec SUBSEP ns SUBSEP ps[i]]
                done[sec SUBSEP ns SUBSEP ps[i]] = 1
            }
            next
        }
        if (rest ~ /^link\.[^.]+\.shared_libs *= */) {
            p = rest; sub(/^link\./, "", p); sub(/\..*/, "", p)
            k = sec SUBSEP ns SUBSEP p
            if ((k in add) && !(k in done)) { line = line ":" add[k]; done[k] = 1 }
        }
    }
    print line
}
' "$STAGE/ld.config.guest.req" "$GLD" "$GLD" > "$STAGE/ld.config.guest.txt" 2> "$STAGE/ld.config.guest.log" &&
       [ "$($BB wc -l < "$STAGE/ld.config.guest.txt")" -ge "$($BB wc -l < "$GLD")" ]; then
        if $BB cmp -s "$STAGE/ld.config.guest.txt" "$GLD"; then
            echo "Guest linker config: One UI's covers the guest's APEX payloads"
        else
            chmod 644 "$STAGE/ld.config.guest.txt"
            $BB chcon "$(ls -Z "$GLD" | $BB awk '{print $1}')" "$STAGE/ld.config.guest.txt" 2>/dev/null || true
            $BB mount --bind "$STAGE/ld.config.guest.txt" "$GLD" &&
                echo "Guest linker config: $($BB grep -c ' + ' "$STAGE/ld.config.guest.log") links added for the guest's APEX payloads ($STAGE/ld.config.guest.log)"
        fi
    else
        echo "!!! WARNING: guest linker config not made ($(head -c 300 "$STAGE/ld.config.guest.log" 2>/dev/null)); One UI's stays"
    fi
fi

# Wi-Fi (run 41): Pixel's wifi module uses the mainline supplicant when its RRO
# sets config_wifiMainlineSupplicantEnabled, the SDK is 37+ and
# /apex/com.android.wifi/bin/wpa_supplicant_mainline is a file. The HOST's init
# then starts that daemon from One UI's wifi APEX, in One UI's namespace and
# /data, without Samsung's overlay conf: P2P lands on wlan0 and addStaInterface
# fails (code 1, "ISupplicantStaIface.addIface failed"). Without the file the
# guest takes Samsung's ISupplicant/default, as ColorOS does. Only the guest's
# own payload mounts are covered (bin/ holds nothing else).
# ONEOS_GUEST_MAINLINE_SUPPLICANT=1 keeps it.
if [ "${ONEOS_GUEST_MAINLINE_SUPPLICANT:-0}" != 1 ]; then
    for d in "$ROOTFS/apex/com.android.wifi" "$ROOTFS/apex/com.android.wifi"@*; do
        [ -f "$d/bin/wpa_supplicant_mainline" ] || continue
        $BB mount --make-private "$d" 2>/dev/null || { echo "!!! could not make $d private, leaving it alone"; continue; }
        $BB mount -t tmpfs -o ro,size=4k,mode=755 tmpfs "$d/bin" &&
            echo "Hid wpa_supplicant_mainline in $(basename "$d"): the guest uses the vendor supplicant"
    done
fi

# OneOS: modules the guest ships as plain system apps instead of APEXes
# (ColorOS: CellBroadcastService, NfcNci, Bluetooth). The host's APEX copies of
# those apps are Google-signed and collide with the guest's OPPO-signed ones
# ("Signature mismatch on system package com.google.android.cellbroadcastservice
# for shared user android.uid.networkstack"). Hide only their app dirs; the
# javalib/lib dirs stay, the boot class path references them. Each bind is made
# private first: it is still a shared peer of the host's /apex mount here, and
# a mount inside it would otherwise propagate into One UI's own APEX.
for m in com.android.nfcservices com.android.bt; do
    [ -f "$STAGE/${m#com.android.}_payload.img" ] && continue
    for d in "$ROOTFS/apex/$m" "$ROOTFS/apex/$m"@*; do
        [ -d "$d" ] || continue
        $BB mount --make-private "$d" 2>/dev/null || { echo "!!! could not make $d private, leaving it alone"; continue; }
        for sub in app priv-app; do
            [ -d "$d/$sub" ] || continue
            $BB mount -t tmpfs -o ro,size=4k,mode=755 tmpfs "$d/$sub" && echo "Hid host $m/$sub in $(basename "$d")"
        done
    done
done

# Play services from One UI's copy in my_product (guest_google.sh prepare wrote
# google_apps/active): hide One UI's own GmsCore in the gmssystem APEX bind, so
# the guest's package manager finds Play services once, where the image's
# privapp-permissions-google-product.xml grants it. Private first, as above.
if [ -f "$STAGE/google_apps/active" ]; then
    for d in "$ROOTFS/apex/com.google.android.gmssystem" "$ROOTFS/apex/com.google.android.gmssystem"@*; do
        [ -d "$d/priv-app" ] || continue
        $BB mount --make-private "$d" 2>/dev/null || { echo "!!! could not make $d private, leaving it alone"; continue; }
        $BB mount -t tmpfs -o ro,size=4k,mode=755 tmpfs "$d/priv-app" &&
            echo "Hid host com.google.android.gmssystem/priv-app in $(basename "$d") (Play services from One UI's copy in my_product)"
    done
fi

# The android.uid.networkstack group has to come from one signer. With the
# host's tethering (Google-signed) and cellbroadcast APEXes kept, use the
# host's NetworkStackGoogle and CaptivePortalLoginGoogle in place of ColorOS's
# OPPO-signed NetworkStack and CaptivePortalLogin, and hide ColorOS's own
# CellBroadcastService.
bind_host_app() {
    [ -d "$1" ] && [ -d "$2" ] || { echo "!!! cannot replace $2 with $1"; return 0; }
    # 0.4.61: the APK must be a readable zip. A36 Infinity-X 607556f1 (0.4.60):
    # "Failed to open APK '/system/priv-app/NetworkStack/NetworkStackGoogle.apk':
    # Invalid file", no MAINLINE_NETWORK_STACK permission, Network Stack and
    # Tethering failed to start, SystemUI's tethering call timed out at startup
    # and SystemUI crash-looped (no status bar, quick settings or navigation).
    # Then One UI's updated copy (/data/app, the same package and signer), bound
    # over the system one in a private folder.
    a=$(ls "$1"/*.apk 2>/dev/null | head -n 1)
    if [ -n "$a" ] && [ "$($BB head -c 2 "$a" 2>/dev/null)" = PK ] && [ "$($BB stat -c %s "$a" 2>/dev/null || echo 0)" -gt 65536 ] &&
       $BB unzip -l "$a" AndroidManifest.xml >/dev/null 2>&1; then
        $BB mount --bind "$1" "$2" && echo "Host $(basename "$1") -> $2"
        return 0
    fi
    echo "!!! host $(basename "$1"): ${a:-no APK} is not a readable APK ($($BB stat -c %s "$a" 2>/dev/null || echo none) bytes)"
    u=""
    [ -n "$3" ] && u=$(ls -d /data/app/*/"$3"-*/base.apk /data/app/"$3"-*/base.apk 2>/dev/null | head -n 1)
    if [ -n "$u" ] && [ "$($BB head -c 2 "$u" 2>/dev/null)" = PK ] && $BB unzip -l "$u" AndroidManifest.xml >/dev/null 2>&1 &&
       $BB mount -t tmpfs -o size=64k,mode=755 tmpfs "$2"; then
        : > "$2/$(basename "$1").apk" && chmod 644 "$2/$(basename "$1").apk" &&
            $BB mount --bind "$u" "$2/$(basename "$1").apk" && $BB mount -o remount,ro "$2" 2>/dev/null &&
            { echo "Host $3 from One UI's update ($u) -> $2"; return 0; }
        $BB umount -l "$2" 2>/dev/null
    fi
    echo "!!! no readable $3 from One UI either; binding $1 as it is"
    $BB mount --bind "$1" "$2" && echo "Host $(basename "$1") -> $2"
}
bind_host_app /system/priv-app/NetworkStackGoogle "$ROOTFS/system/priv-app/NetworkStack" com.google.android.networkstack
bind_host_app /system/app/CaptivePortalLoginGoogle "$ROOTFS/system/app/CaptivePortalLogin" com.google.android.captiveportallogin
if [ -d "$GUEST_SYSTEM_EXT/priv-app/CellBroadcastService" ]; then
    $BB mount -t tmpfs -o ro,size=4k,mode=755 tmpfs "$GUEST_SYSTEM_EXT/priv-app/CellBroadcastService" && \
        echo "Hid guest system_ext/priv-app/CellBroadcastService"
fi
# Pixel's PersistentBackgroundCameraServices registers three binder services
# that only Pixel's own VINTF manifest declares; the shared servicemanager checks
# One UI's and throws "VINTF declaration error", and the app is persistent: run
# 41, 9006 crashes in 6 minutes (a zygote fork every 40 ms, and a listener on One
# UI's cameraserver each time). Pixel's camera HAL is not here anyway.
if [ -d "$GUEST_SYSTEM_EXT/app/PersistentBackgroundCameraServices" ]; then
    $BB mount -t tmpfs -o ro,size=4k,mode=755 tmpfs "$GUEST_SYSTEM_EXT/app/PersistentBackgroundCameraServices" && \
        echo "Hid guest system_ext/app/PersistentBackgroundCameraServices (services only Pixel's VINTF declares)"
fi
# Pixel's ConnectivityThermalPowerManager throttles the Pixel modem and Wi-Fi
# through GRIL when the phone warms up. Here the modem is Samsung's and GRIL is
# not in the image: from the first LIGHT thermal status on, each throttling
# request came back "modem does not support data throttling" and crashed the
# app, which is persistent: S25 Ultra Pixel 9 Pro XL session af6c2b17, 1394
# crashes in 15 minutes (a zygote fork every 0.6 s at full CPU clock, skin
# 54 C).
if [ -d "$GUEST_SYSTEM_EXT/priv-app/ConnectivityThermalPowerManager" ] && \
   [ ! -L "$GUEST_SYSTEM_EXT/priv-app/ConnectivityThermalPowerManager" ]; then
    $BB mount -t tmpfs -o ro,size=4k,mode=755 tmpfs "$GUEST_SYSTEM_EXT/priv-app/ConnectivityThermalPowerManager" && \
        echo "Hid guest system_ext/priv-app/ConnectivityThermalPowerManager (Pixel modem throttling; crash loop on a Samsung modem)"
fi
# OxygenOS 16's NFC app (system/priv-app/NfcNci) asks for OPPO's NFC HAL
# (vendor.oplus.hardware.nfc@1.0::IOplusNfc) in a static initializer
# (NfcChipManager.<clinit> from VendorNfcService), and HwBinder.getService throws
# NoSuchElementException on a Samsung vendor: the persistent app dies in
# NfcApplication.onCreate and is started again, about five times a second for
# the whole session (M55s 0e73a8d6: 628 crashes in 3 minutes; S23 FE 6d13b740,
# S22 Ultra acd15d4c: the same, users report a slow, warm phone). ColorOS 17's
# NfcChipManager logs "Failed to get IOplusNfc service (binder null)" and goes on
# (S26 2f97ffa9), so only OxygenOS, and only when the vendor does not declare
# OPPO's HAL. NFC never started in those sessions either way.
# ONEOS_GUEST_OEM_NFC=1 keeps it.
if [ "${ONEOS_GUEST_OEM_NFC:-0}" != 1 ] && grep -q '^  "image": "oxygenos' "$STAGE/.oneos_stage" 2>/dev/null &&
   ! "$BB" grep -rqs 'vendor.oplus.hardware.nfc' /vendor/etc/vintf/ /odm/etc/vintf/; then
    d="$ROOTFS/system/priv-app/NfcNci"
    if [ -d "$d" ] && [ ! -L "$d" ]; then
        $BB mount -t tmpfs -o ro,size=4k,mode=755 tmpfs "$d" && \
            echo "Hid guest system/priv-app/NfcNci (OxygenOS's NFC app dies without OPPO's NFC HAL; ONEOS_GUEST_OEM_NFC=1 keeps it)"
    fi
fi
# The phone's eSIM chip is shared hardware, and an eSIM manager (LPA) in the
# guest drives it directly: Pixel's EuiccGoogle opens the chip's ISD-R channel
# itself (run 43). A guest factory reset with "Erase eSIMs", Reset mobile
# network settings with "Erase downloaded SIMs", Erase SIM in the guest's SIM
# settings, or Find My Device's remote erase once a Google account is signed
# in, would delete One UI's eSIM profiles for good (the BCB and FRP guards
# stop the rest of such a wipe, not this part). Without an LPA the guest still
# uses the eSIM One UI left enabled (the modem runs it like a SIM card: calls,
# SMS, data); it cannot download, switch or erase profiles, and Settings hides
# those options. Every Euicc* app folder but RROs and permission-only
# packages: Pixel's product EuiccGoogle and system_ext EuiccSupportPixel-P23,
# the Find X9 Ultra's my_product EuiccOplus (the Find N6 has none).
# ONEOS_GUEST_ESIM_MANAGER=1 keeps them.
if [ "${ONEOS_GUEST_ESIM_MANAGER:-0}" != 1 ]; then
    for d in "$ROOTFS"/system/priv-app/Euicc* "$ROOTFS"/system/app/Euicc* \
             "$GUEST_PRODUCT"/priv-app/Euicc* "$GUEST_PRODUCT"/app/Euicc* \
             "$GUEST_SYSTEM_EXT"/priv-app/Euicc* "$GUEST_SYSTEM_EXT"/app/Euicc* \
             "$ROOTFS"/my_*/priv-app/Euicc* "$ROOTFS"/my_*/app/Euicc*; do
        [ -d "$d" ] && [ ! -L "$d" ] || continue
        case ${d##*/} in *Overlay|*Permissions) continue ;; esac
        $BB mount -t tmpfs -o ro,size=4k,mode=755 tmpfs "$d" && \
            echo "Hid guest ${d#"$ROOTFS"/} (eSIM manager: the eSIM chip is One UI's; ONEOS_GUEST_ESIM_MANAGER=1 keeps it)"
    done
fi
# vivo OriginOS (MediaTek build): MediaTek's telephony helpers talk only to
# MediaTek's vendor (mtkradioex, atcid, the IMS data channel and capability
# control), which a Samsung phone does not have; each retries once a second for
# the whole session. MediaTek's IMS too: it starts only with
# persist.vendor.ims_support=1 (vivo's vendor) and, when bound, waits 3 x 5 s per
# SIM for its service. With Samsung's IMS in the guest (ONEOS_GUEST_SEC_IMS=1, the
# thirteenth CN run's plan for SMS) it stays hidden as well: com.mediatek.ims is a
# persistent app in the phone process that declares the MMTEL, emergency MMTEL and
# RCS features, so the guest's ImsResolver would bind it as the device's IMS
# service at every start before the UI activator moves both slots to Samsung's;
# every session that worked so far ran without it. ONEOS_GUEST_MTK_TELEPHONY=1 keeps them.
if [ "${ONEOS_GUEST_MTK_TELEPHONY:-0}" != 1 ] && [ -e "$ROOTFS/system/framework/vivo-telephony-common-platform-ex.jar" ]; then
    for n in MtkTelephonyAssist MtkCapCtrl DataChannelService AtciService ImsService; do
        d="$GUEST_SYSTEM_EXT/priv-app/$n"
        [ -d "$d" ] && [ ! -L "$d" ] || continue
        $BB mount -t tmpfs -o ro,size=4k,mode=755 tmpfs "$d" && \
            echo "Hid guest ${d#"$ROOTFS"/} (MediaTek's vendor only; ONEOS_GUEST_MTK_TELEPHONY=1 keeps it)"
    done
fi
# vivo OriginOS: Vivo3rdAlgoService waits for vivo's IVASAlgoProvider HAL and never
# finishes starting (seventh run: ANR, killed and started again, five times), and
# vdfs keeps asking init for vivo's vdfs daemon, which One UI's init refuses.
# ONEOS_GUEST_VIVO_EXTRAS=1 keeps them.
if [ "${ONEOS_GUEST_VIVO_EXTRAS:-0}" != 1 ] && [ -e "$ROOTFS/system/framework/vivo-services.jar" ]; then
    for d in "$ROOTFS/system/app/Vivo3rdAlgoService" "$ROOTFS/system/app/vdfs"; do
        [ -d "$d" ] && [ ! -L "$d" ] || continue
        $BB mount -t tmpfs -o ro,size=4k,mode=755 tmpfs "$d" && \
            echo "Hid guest ${d#"$ROOTFS"/} (needs vivo's own HAL or daemon; ONEOS_GUEST_VIVO_EXTRAS=1 keeps it)"
    done
fi
# vivo's setup wizard (com.vivo.setupwizard) is a HOME activity until it finishes
# itself, so marking setup done (above) did not stop it: the sixth CN run opened it
# again, at its terms page. Hidden while setup is marked done; vivo's launcher is
# then the home. ONEOS_GUEST_VIVO_SETUP=1 keeps it (and the setup).
if [ "${ONEOS_GUEST_VIVO_SETUP:-0}" != 1 ] && [ -e "$ROOTFS/system/framework/vivo-services.jar" ]; then
    d="$ROOTFS/system/priv-app/SetupWizard"
    if [ -d "$d" ] && [ ! -L "$d" ] && [ -f "$d/SetupWizard.apk" ] &&
       $BB unzip -p "$d/SetupWizard.apk" AndroidManifest.xml 2>/dev/null | tr -d '\0' | grep -aq "com.vivo.setupwizard"; then
        $BB mount -t tmpfs -o ro,size=4k,mode=755 tmpfs "$d" &&
            echo "Hid guest ${d#"$ROOTFS"/} (vivo's setup wizard; setup is marked done; ONEOS_GUEST_VIVO_SETUP=1 keeps it)"
    fi
fi
# OPPO's camera in an image that also has LineageOS's Aperture (Infinity-X 4.1
# for the Find X9 Ultra): OplusCamera takes its camera list from the Find X9
# Ultra's own odm/etc/camera/config/oplus_camera_config, which a Samsung phone
# does not have ("configMap: {}"), and dies opening at CameraManager.c1 with a
# NullPointerException, every time, on every phone (0.4.32 reports: S24 Ultra,
# S25 Ultra, A56, A57, Z Flip5). The camera itself works: Open Camera and Lens
# opened it in the same sessions. Aperture uses the plain camera2 API, so with
# OplusCamera hidden it is the camera app. ColorOS keeps OplusCamera (no
# Aperture there). ONEOS_GUEST_OEM_CAMERA=1 keeps it.
# ColorOS too once Samsung Camera is in the guest (SAMCAM, above): OPPO's camera
# (my_product/app/OplusCamera) never showed a preview in any ColorOS report, Find
# N6 or X9 Ultra, on any Galaxy; it dies at start on its camera SDK
# (NoClassDefFoundError: com.oplus.ocs.camera.appinterface.adapter.
# CameraAdapterUtils), often dozens of times a session, and its launcher icon is
# the one users tap ("Camera crashed": 0.4.58 reports 45bc960f, d89cc8a5,
# 74bcf2b6). Samsung Camera is then the camera.
if [ "${ONEOS_GUEST_OEM_CAMERA:-0}" != 1 ] && { [ -d "$GUEST_PRODUCT/app/Aperture" ] || [ -d "$GUEST_SYSTEM_EXT/app/Aperture" ] || [ "$SAMCAM" = 1 ]; }; then
    if [ "$SAMCAM" = 1 ]; then OCWHY="Samsung Camera is the camera"; else OCWHY="Aperture is the camera"; fi
    for d in "$GUEST_SYSTEM_EXT"/priv-app/OplusCamera "$ROOTFS"/system/priv-app/OplusCamera "$GUEST_PRODUCT"/priv-app/OplusCamera \
             "$ROOTFS"/my_*/app/OplusCamera "$ROOTFS"/my_*/priv-app/OplusCamera; do
        [ -d "$d" ] && [ ! -L "$d" ] || continue
        $BB mount -t tmpfs -o ro,size=4k,mode=755 tmpfs "$d" && \
            echo "Hid guest ${d#"$ROOTFS"/} (OPPO's camera needs the Find X9 Ultra's camera config and SDK; $OCWHY; ONEOS_GUEST_OEM_CAMERA=1 keeps it)"
    done
fi
# Google Play services (GMS_WANT, top; docs/pixel-guest.md). GmsCore is
# presented as a plain product priv-app, as Pixels had it before Android 17,
# and the image is not changed: a small tmpfs package folder ($STAGE/gmscore,
# labelled system_file, read-only once filled) holds the APK, bound from the
# guest's own gmssystem payload (section 8, checked to be the guest's loop
# device, never One UI's module), and the image's own app_chimera and m
# (GmsCore's Dynamite modules, which it looks for next to its APK), and is
# bound over system/product/priv-app/PrebuiltGmsCore. The image already
# allowlists GmsCore's privileged permissions (product
# privapp-permissions-google-p.xml) and its user types
# (preinstalled-packages-product-pixel-2017-and-newer.xml). The payload's own
# priv-app folder is then hidden in every mount of it, so the package manager
# can find GmsCore only once. Everything here mounts the guest's own files; the
# tmpfs on $STAGE/gmscore sits in One UI's shared /data and is made private
# right after it is mounted, so the binds made into it stay in the stage;
# return_to_oneui.sh unmounts it with the rest of the stage, deepest first,
# and its reboot frees the loop device. Anything unexpected stops the session
# (exit 3) before or instead of a half-made folder: ONEOS_GUEST_GMS=0 starts
# without Google services. data/oneos_gms_present tells the UI activator.
mount_source() { # <mount point>: the source of the topmost mount there
    awk -v p="$1" '$5 == p { s = ""; for (i = 7; i < NF; i++) if ($i == "-") { s = $(i + 2); break } } END { print s }' /proc/self/mountinfo
}
loop_devnum() { # <loop device node>: its major:minor (the nodes made in section 2 need not match the kernel's names)
    _lb=$(stat -L -c '%t %T' "$1" 2>/dev/null) || return 1
    set -- $_lb
    printf '%d:%d' "0x$1" "0x$2"
}
on_gms_loop() { # <mount point>: the topmost mount there is the guest's gmssystem loop device (by name or number)
    awk -v p="$1" -v l="$GMS_LOOP" -v d="$GMS_LOOP_DEV" '$5 == p { s = ""; for (i = 7; i < NF; i++) if ($i == "-") { s = $(i + 2); break }
        ok = (s == l || (d != "" && $3 == d)) } END { exit !ok }' /proc/self/mountinfo
}
if [ "$GMS_WANT" = 1 ]; then
    gms_refuse() {
        echo "ERROR: Google services: $*; not starting the guest (ONEOS_GUEST_GMS=0 starts without them)"
        exit 3
    }
    GMS_APEX="$ROOTFS/apex/com.google.android.gmssystem"
    # Pixel's PrebuiltGmsCore (app_chimera and m), or vivo OriginOS's GmsCore (m only).
    GMS_DIR="$GUEST_PRODUCT/priv-app/PrebuiltGmsCore"
    [ -e "$GMS_DIR" ] || [ -L "$GMS_DIR" ] || [ ! -d "$GUEST_PRODUCT/priv-app/GmsCore" ] || GMS_DIR="$GUEST_PRODUCT/priv-app/GmsCore"
    GMS_PKG="$STAGE/gmscore"
    # 1. The payload is the guest's: its loop device (payload_loops, written by
    #    mount_payload), backed by the staged payload, on top at the APEX path.
    GMS_LOOP=$(awk '$1 == "com.google.android.gmssystem" { l = $2 } END { print l }' "$STAGE/payload_loops" 2>/dev/null)
    [ -n "$GMS_LOOP" ] || gms_refuse "gmssystem_payload.img was not mounted (section 8)"
    GMS_LOOP_DEV=$(loop_devnum "$GMS_LOOP")
    on_gms_loop "$GMS_APEX" ||
        gms_refuse "${GMS_APEX#$ROOTFS} is mounted from $(mount_source "$GMS_APEX"), not the guest's $GMS_LOOP ($GMS_LOOP_DEV)"
    g_bf=$(cat "/sys/dev/block/$GMS_LOOP_DEV/loop/backing_file" 2>/dev/null)
    [ -n "$GMS_LOOP_DEV" ] && [ "$g_bf" = "$STAGE/gmssystem_payload.img" ] ||
        gms_refuse "$GMS_LOOP (${GMS_LOOP_DEV:-no device}) is backed by ${g_bf:-nothing}, not $STAGE/gmssystem_payload.img"
    # Its @<version> dirs too (the payload_loops pass): one still on One UI's
    # module would show One UI's GmsCore to the guest, and a mount inside it
    # would reach One UI's own /apex.
    for g_d in "$GMS_APEX"@*; do
        [ -d "$g_d" ] || continue
        on_gms_loop "$g_d" || gms_refuse "${g_d#$ROOTFS} is mounted from $(mount_source "$g_d"), not the guest's $GMS_LOOP"
    done
    echo "Google services: payload ${GMS_APEX#$ROOTFS} (and its @ dirs) on $GMS_LOOP ($g_bf)"
    # 2. Exactly one GmsCore APK in it.
    GMS_APK_SRC=""; g_n=0
    for g_a in "$GMS_APEX"/priv-app/PrebuiltGmsCore*/PrebuiltGmsCore*.apk; do
        [ -f "$g_a" ] && [ ! -L "$g_a" ] || continue
        GMS_APK_SRC=$g_a; g_n=$((g_n + 1))
    done
    [ "$g_n" = 1 ] || gms_refuse "$g_n PrebuiltGmsCore APKs in the gmssystem payload (one expected)"
    GMS_APK_NAME=${GMS_APK_SRC##*/}
    echo "Google services: GmsCore ${GMS_APK_SRC#$GMS_APEX/} ($(stat -c %s "$GMS_APK_SRC") bytes)"
    # 3. The image's GmsCore folder: a real folder of the image (no link
    #    anywhere on the path: it would lead to One UI's own /product), with
    #    GmsCore's module folders (Pixel: app_chimera and m; vivo: m), and no
    #    APK of its own.
    [ -d "$GMS_DIR" ] && [ "$(readlink -f "$GMS_DIR")" = "$GMS_DIR" ] ||
        gms_refuse "${GMS_DIR#$ROOTFS} is missing or reached through a link"
    GMS_SUB=""
    for g_s in app_chimera m; do
        [ -e "$GMS_DIR/$g_s" ] || [ -L "$GMS_DIR/$g_s" ] || continue
        [ -d "$GMS_DIR/$g_s" ] && [ ! -L "$GMS_DIR/$g_s" ] ||
            gms_refuse "${GMS_DIR#$ROOTFS}/$g_s is not a folder of the image"
        GMS_SUB="$GMS_SUB $g_s"
    done
    case "${GMS_DIR##*/}:$GMS_SUB" in
        "PrebuiltGmsCore: app_chimera m"|"GmsCore: m") ;;
        *) gms_refuse "${GMS_DIR#$ROOTFS} has [${GMS_SUB# }] (Pixel's PrebuiltGmsCore has app_chimera and m, vivo's GmsCore m)" ;;
    esac
    for g_a in "$GMS_DIR"/*.apk; do
        [ -e "$g_a" ] || [ -L "$g_a" ] || continue
        gms_refuse "the image already has ${g_a#$ROOTFS} (GmsCore would be there twice)"
    done
    [ -n "$(mount_source "$GMS_DIR")" ] && gms_refuse "${GMS_DIR#$ROOTFS} is already a mount point"
    # 4. The package folder: a tmpfs under the stage (never under the staged
    #    /data, whose tree is rewritten every session), labelled like the image.
    [ -L "$GMS_PKG" ] && rm -f "$GMS_PKG"
    mkdir -p "$GMS_PKG" && [ -d "$GMS_PKG" ] && [ ! -L "$GMS_PKG" ] || gms_refuse "could not create $GMS_PKG"
    [ -n "$(mount_source "$GMS_PKG")" ] && gms_refuse "$GMS_PKG is already a mount point"
    g_label=mount
    if ! $BB mount -t tmpfs -o size=64k,mode=755,context=u:object_r:system_file:s0 tmpfs "$GMS_PKG" 2>/dev/null; then
        $BB mount -t tmpfs -o size=64k,mode=755 tmpfs "$GMS_PKG" || gms_refuse "could not mount a tmpfs on $GMS_PKG"
        g_label=chcon
    fi
    # Private at once: the stage sits on One UI's shared /data mount.
    $BB mount --make-private "$GMS_PKG" 2>/dev/null || gms_refuse "could not make $GMS_PKG private"
    echo "Google services: tmpfs package folder $GMS_PKG (label by $g_label)"
    (cd "$GMS_PKG" && mkdir $GMS_SUB && chmod 755 $GMS_SUB) && : > "$GMS_PKG/$GMS_APK_NAME" &&
        chmod 644 "$GMS_PKG/$GMS_APK_NAME" ||
        gms_refuse "could not fill $GMS_PKG"
    if [ "$g_label" = chcon ]; then
        $BB chcon -R u:object_r:system_file:s0 "$GMS_PKG" 2>/dev/null || gms_refuse "could not label $GMS_PKG system_file"
    fi
    $BB mount --bind "$GMS_APK_SRC" "$GMS_PKG/$GMS_APK_NAME" || gms_refuse "could not bind the GmsCore APK"
    echo "Google services: bound ${GMS_APK_SRC#$ROOTFS} -> $GMS_PKG/$GMS_APK_NAME"
    for g_s in $GMS_SUB; do
        $BB mount --bind "$GMS_DIR/$g_s" "$GMS_PKG/$g_s" || gms_refuse "could not bind ${GMS_DIR#$ROOTFS}/$g_s"
        echo "Google services: bound ${GMS_DIR#$ROOTFS}/$g_s -> $GMS_PKG/$g_s"
    done
    $BB mount -o remount,ro "$GMS_PKG" 2>/dev/null && echo "Google services: $GMS_PKG read-only" ||
        echo "!!! Google services: could not make $GMS_PKG read-only (its contents are: an erofs APK and the read-only image's folders)"
    # 5. Over the image's folder, recursively (the three binds come along).
    $BB mount --rbind "$GMS_PKG" "$GMS_DIR" || gms_refuse "could not bind $GMS_PKG over ${GMS_DIR#$ROOTFS}"
    $BB mount --make-rprivate "$GMS_DIR" 2>/dev/null || gms_refuse "could not make ${GMS_DIR#$ROOTFS} private"
    g_last=${GMS_SUB##* }
    [ "$(stat -c %s "$GMS_DIR/$GMS_APK_NAME" 2>/dev/null)" = "$(stat -c %s "$GMS_APK_SRC")" ] &&
        { [ "$g_last" != m ] || [ -d "$GMS_DIR/m" ]; } && { [ "${GMS_SUB# }" = m ] || [ -d "$GMS_DIR/app_chimera/m" ]; } ||
        gms_refuse "${GMS_DIR#$ROOTFS} does not show the APK and its module folders after the bind"
    echo "Google services: bound $GMS_PKG -> ${GMS_DIR#$ROOTFS} ($GMS_APK_NAME,$GMS_SUB)"
    # 6. The payload's own priv-app folder, hidden in each mount of the payload
    #    (each checked again to be the guest's loop device, as in 1).
    g_hid=0
    for g_d in "$GMS_APEX" "$GMS_APEX"@*; do
        [ -d "$g_d/priv-app" ] || continue
        on_gms_loop "$g_d" || gms_refuse "${g_d#$ROOTFS} is mounted from $(mount_source "$g_d"), not the guest's $GMS_LOOP"
        $BB mount --make-private "$g_d" 2>/dev/null || gms_refuse "could not make ${g_d#$ROOTFS} private"
        $BB mount -t tmpfs -o ro,size=4k,mode=755 tmpfs "$g_d/priv-app" || gms_refuse "could not hide ${g_d#$ROOTFS}/priv-app"
        echo "Google services: hid ${g_d#$ROOTFS}/priv-app (GmsCore is found once, in product)"
        g_hid=$((g_hid + 1))
    done
    [ "$g_hid" -ge 1 ] || gms_refuse "no priv-app folder in ${GMS_APEX#$ROOTFS} to hide"
    rm -f "$STAGE/data/oneos_gms_present"
    echo "$GMS_APK_NAME $(stat -c %s "$GMS_DIR/$GMS_APK_NAME")" > "$STAGE/data/oneos_gms_present"
    echo "Google services presented: ${GMS_DIR#$GUEST_PRODUCT/}/$GMS_APK_NAME in /system/product (the image's setup wizard runs until it is finished)"
fi
# Google services in a global image (the Find X9 Ultra IN has Play services, the
# Play Store and their setup/restore helpers in my_product/priv-app).
# ONEOS_GUEST_HIDE_GMS=1 hides them for the session the same way: an empty
# read-only tmpfs over each folder, the image unchanged, so ColorOS's package
# manager never sees them and nothing Google signs in, restores or keeps keys
# there. For the first runs of such an image; off by default (owner: once a run
# with them on works, they stay on). Pixel's folders carry other names, some
# with a version (PrebuiltGmsCore, PartnerSetupPrebuilt,
# GoogleRestorePrebuilt-v<n>, product/app/PlayAutoInstallConfig_<key>, and
# Google Services Framework in system_ext), hence the patterns.
if [ "${ONEOS_GUEST_HIDE_GMS:-0}" = 1 ]; then
    hid=0
    for a in GmsCore PrebuiltGmsCore Phonesky GooglePartnerSetup PartnerSetupPrebuilt 'GoogleRestore*' \
             ConfigUpdater 'PlayAutoInstallConfig*' GoogleServicesFramework; do
        for d in "$ROOTFS/my_product/priv-app/"$a "$ROOTFS/system/priv-app/"$a "$GUEST_PRODUCT/priv-app/"$a \
                 "$GUEST_PRODUCT/app/"$a "$GUEST_SYSTEM_EXT/priv-app/"$a; do
            [ -d "$d" ] && [ ! -L "$d" ] || continue
            $BB mount -t tmpfs -o ro,size=4k,mode=755 tmpfs "$d" && { echo "Hid guest ${d#$ROOTFS/} (ONEOS_GUEST_HIDE_GMS=1)"; hid=$((hid + 1)); }
        done
    done
    echo "Google services hidden in the guest: $hid folder(s)"
fi
# Google's split permissions without Google Play services. Pixel's
# product/etc/permissions/split-permissions-google.xml (the X9U IN has one in
# my_product) splits com.google.android.gms.permission.ACTIVITY_RECOGNITION,
# which only GmsCore declares. Android 17's permission service throws on a
# split whose source nobody declares, and system_server died in
# PackageManagerService.<init> (run 38... run 39: "Unknown source permission
# com.google.android.gms.permission.ACTIVITY_RECOGNITION in split permissions").
# Pixel's GmsCore APK is in a product APEX the phone's apexd never activates,
# and ONEOS_GUEST_HIDE_GMS hides the others. So when the guest has no GmsCore
# APK, each such file is bound from a stage copy without the gms splits; the
# image is unchanged. Stale binds of a former session come off first: only this
# filter's own (oneos_split_*.xml). Up to 0.4.14 every bind on a permissions
# XML came off here, the ColorOS feature list bound above (FEAT) with them, so
# none of its additions reached a session (pull request #1, Z Fold8).
SPLIT_DIRS="$ROOTFS/system/etc/permissions $GUEST_PRODUCT/etc/permissions $GUEST_SYSTEM_EXT/etc/permissions $ROOTFS/my_product/etc/permissions"
for d in $SPLIT_DIRS; do
    for f in "$d"/*.xml; do
        [ -f "$f" ] || continue
        # Remove only this filter's bind, not ColorOS feature or other XML
        # overrides mounted earlier in prepare. On /data's filesystem the
        # mount root omits the /data prefix; retain support for both forms.
        split_source=$(awk -v target="$f" '$5 == target { source = $4 } END { print source }' /proc/self/mountinfo)
        case "$split_source" in
            "$STAGE"/oneos_split_*.xml|"${STAGE#/data}"/oneos_split_*.xml)
                split_id=${split_source##*/oneos_split_}; split_id=${split_id%.xml}
                case "$split_id" in ''|*[!0-9]*) continue ;; esac
                $BB umount -l "$f" 2>/dev/null
                ;;
        esac
    done
done
rm -f "$STAGE"/oneos_split_*.xml
GMS_APK=0
for a in "$ROOTFS"/my_product/priv-app/*GmsCore*/*.apk "$ROOTFS"/system/priv-app/*GmsCore*/*.apk \
         "$GUEST_PRODUCT"/priv-app/*GmsCore*/*.apk "$GUEST_SYSTEM_EXT"/priv-app/*GmsCore*/*.apk; do
    [ -f "$a" ] && GMS_APK=1
done
if [ "$GMS_APK" = 0 ]; then
    n=0
    for d in $SPLIT_DIRS; do
        for f in "$d"/*.xml; do
            [ -f "$f" ] && [ ! -L "$f" ] && grep -q '<split-permission[^>]*name="com.google.android.gms\.' "$f" || continue
            n=$((n + 1))
            c="$STAGE/oneos_split_$n.xml"
            # Whole <split-permission ...> ... </split-permission> blocks (or a
            # self-closed one) whose source is a gms permission.
            awk 'skip == 0 && /<split-permission[^>]*name="com\.google\.android\.gms\./ {
                     if ($0 !~ /\/>[[:space:]]*$/ && $0 !~ /<\/split-permission>/) skip = 1
                     next }
                 skip == 1 { if ($0 ~ /<\/split-permission>/) skip = 0; next }
                 { print }' "$f" > "$c" &&
                grep -q '</permissions>' "$c" && ! grep -q 'name="com.google.android.gms\.' "$c" || {
                echo "!!! could not filter ${f#$ROOTFS/}, left as it is"; rm -f "$c"; continue; }
            chmod 644 "$c"
            # A stage copy, not host data: labelled like the system file it replaces.
            $BB chcon u:object_r:system_file:s0 "$c" 2>/dev/null || true
            $BB mount --bind "$c" "$f" &&
                echo "Bound ${f#$ROOTFS/} without its gms split permissions (no GmsCore in the guest)"
        done
    done
    [ "$n" = 0 ] && echo "No GmsCore in the guest; no gms split permissions to drop"
fi
# OPPO region overlays in a global image (the Find X9 Ultra IN keeps them in
# my_product/cust/<region>/overlay, one folder per region). OPPO's own first
# stage maps the phone's region onto an allowed path; the container does not
# run it, so ColorOS's package manager finds them at the raw path, the zygote
# opens one while preloading, and its file-descriptor allowlist (fd_utils in
# libandroid_runtime: /my_product/overlay yes, /my_product/cust no) aborts the
# fork of system_server. Run 37 (IN on the Fold): "JNI FatalError called:
# (system_server) Not allowlisted (72): /my_product/cust/IN/overlay/
# GmsConfigOverlaySearchSelector/...", then zygote gone and the auto-return.
# Hidden for the session like the folders above (the region's dialer, contacts
# and Google config tweaks do not apply). The N6 and X9U CN images have
# my_product/cust/<region> folders but no overlay folder in any of them (checked
# with debugfs), so this finds nothing there; the IN image has 24.
# ONEOS_GUEST_REGION_OVERLAYS=1 keeps them (adb loop only: the abort above).
if [ "${ONEOS_GUEST_REGION_OVERLAYS:-0}" != 1 ] || [ "${ONEOS_APP:-0}" = 1 ]; then
    hid=0
    for d in "$ROOTFS"/my_product/cust/*/overlay; do
        [ -d "$d" ] && [ ! -L "$d" ] || continue
        $BB mount -t tmpfs -o ro,size=4k,mode=755 tmpfs "$d" && hid=$((hid + 1))
    done
    [ "$hid" = 0 ] || echo "OPPO region overlays hidden in the guest: $hid my_product/cust/*/overlay folder(s) (outside the zygote's allowlist)"
fi

# PermissionController patch, second pass. The same block near step 4 runs
# before the apex set is mounted, so find(1) finds nothing and Samsung's
# PermissionController stays behind. Samsung's build requires
# android.permission.RANGING, which the GSI platform does not define, so every
# runtime-permission dialog dies with
#   IllegalStateException: android.permission.RANGING not defined by platform
#   -> "Permission controller keeps stopping"
# and Gallery/Phone/Calendar can never be granted anything. Bind it now that
# /apex/com.android.permission actually exists.
if [ -f "$STAGE/PermissionController_patched.apk" ]; then
    chmod 644 "$STAGE/PermissionController_patched.apk" 2>/dev/null || true
    for PERM_APK in $(find "$ROOTFS/apex/com.android.permission" -name "PermissionController.apk" 2>/dev/null); do
        $BB umount -l "$PERM_APK" 2>/dev/null || true
        $BB mount --bind "$STAGE/PermissionController_patched.apk" "$PERM_APK" 2>/dev/null && echo "Bound PermissionController_patched.apk (late) -> $PERM_APK"
    done
else
    echo "!!! WARNING: PermissionController_patched.apk missing from $STAGE"
    echo "!!! Samsung's PermissionController will crash every runtime-permission dialog"
    echo "!!! (android.permission.RANGING not defined by platform)"
fi

# OneOS: make every mount under the rootfs private. The binds of /apex/*,
# /linkerconfig, /mnt etc. inherit the host's shared propagation, so the
# unmounts on the way back to One UI propagated to the HOST's own mounts: One
# UI came back without its wifi APEX contents (WifiService NPE on its
# resources, system_server boot loop, reboot). A private bind does not change
# the source mount.
$BB mount --make-rprivate "$ROOTFS" 2>/dev/null || true

# KernelSU in the guest (0.4.39): the host-side helpers for its own modules
# and for a soft reboot of this system only (oneos_switch.sh's watcher runs
# guest_softreboot.sh). In $STAGE/tmp: root's, never the guest's /data. The
# modules go on once here, after the tree is private and before the check of
# One UI's partitions below; guest_modules.sh checks One UI's mounts itself too.
cat > "$STAGE/tmp/guest_modules.sh" <<'GUESTMODULES'
#!/system/bin/sh
# OneOS: this guest system's own KernelSU modules (data/oneos_ksu/modules, what
# its KernelSU app installs; One UI's never load here) onto its tree, the way
# KernelSU's magic mount does: a module's system/ files over the image's (vendor/,
# product/, system_ext/ and odm/ at those partitions), new files and folders
# through a tmpfs copy of the folder they go into, a folder with a .replace file
# as a whole. Every target is resolved inside the guest's tree; a path that
# leads out of it (an absolute link) is skipped. disable, remove, skip_mount and
# modules_update are honoured. Modules' scripts (post-fs-data.sh, service.sh),
# system.prop and sepolicy.rule are not run in a guest system. Run by
# guest_prepare.sh at the switch and by guest_softreboot.sh before the guest
# starts again; the previous application is undone first.
S=${ONEOS_TEST_STAGE:-/data/local/tmp/oneos}
R=$S/rootfs
K=$S/data/oneos_ksu
[ ! -f "$S/data/oneos_root/enabled" ] || K=$S/data/oneos_root/adb
M=$K/modules
U=$K/modules_update
L=$S/tmp/module_mounts
# The folder copies under the guest's private tree (no propagation to One UI's
# namespaces, unlike the stage's own folders on /data).
W=$R/data/oneos_ksu/.mirrors
[ -n "$BB" ] || for c in /data/adb/ksu/bin/busybox /data/adb/ap/bin/busybox /data/adb/magisk/busybox; do [ -x "$c" ] && { BB=$c; break; }; done
[ -x "$BB" ] && [ -d "$M" ] || { echo "Modules: none for this system"; exit 0; }
under() { case "$1" in "$R"|"$R"/*) return 0 ;; esac; return 1; }
# One UI's own mounts (everything outside the stage) before: compared at the end.
# and the module store itself (a mount there would be in /data's peer group).
outside() { awk -v s="$S/" -v k="$K/" 'index($2, s) != 1 || index($2, k) == 1 { print $2 }' /proc/1/mounts | sort; }
outside > "$S/tmp/module_outside.before"
record() { echo "$1" >> "$L"; }

# The last application (a soft reboot): its mounts off, deepest first.
if [ -f "$L" ]; then
    sort -r "$L" | while read -r t; do $BB umount -l "$t" 2>/dev/null; done
    rm -f "$L"
fi
# Never rm -r here: a copy still mounted would delete through its binds. The
# copies come off, then only their empty mount points go.
if [ -d "$W" ]; then
    for t in $(awk -v w="$W/" 'index($2, w) == 1 { print $2 }' /proc/self/mounts | sort -r); do $BB umount -l "$t" 2>/dev/null; done
    for t in "$W"/*; do [ -d "$t" ] && rmdir "$t" 2>/dev/null; done
    rm -f "$W/.mirrored"
fi
mkdir -p "$W" || { echo "Modules: no $W"; exit 0; }

# Cleanup scripts run in the guest root before deleting anything, never in host /data/adb.
# Bounded, and by SIGKILL (a shell waiting for a child acts on SIGTERM only after it): nothing
# here may hold the switch behind the splash (S22 Ultra 0.4.91, 2026-11-11: this step never
# returned, guest_runtime.sh's uninstall stage has the cause). Each uninstall.sh has its own
# 30 s. A bootstrap su the stopped cleanup left is ended by the pid it recorded.
if [ -f "$S/data/oneos_root/enabled" ]; then
    rm -f "$K/oneos/run/bootstrap.pid"
    "$BB" timeout -s KILL 150 "$BB" chroot "$R" /system/bin/sh /data/oneos_runtime.sh uninstall || {
        rc=$?
        if [ "$rc" = 137 ]; then
            echo "Modules: the guest's module cleanup did not end within 150 s and was stopped"
            bp=$(cat "$K/oneos/run/bootstrap.pid" 2>/dev/null)
            case "$bp" in ''|*[!0-9]*) ;; *)
                case "$("$BB" readlink "/proc/$bp/exe" 2>/dev/null)" in */oneos/bin/su) kill -KILL "$bp" 2>/dev/null ;; esac ;;
            esac
            rm -f "$K/oneos/run/bootstrap.pid"
        fi
        echo "Modules: the guest's module cleanup failed (exit $rc; its log: data/oneos_root/adb/oneos/run/session.log)"; exit 1; }
fi
# Remove wins over a pending update. Never delete an active module at button press.
for d in "$M"/* "$U"/*; do
    [ -d "$d" ] && [ ! -L "$d" ] && [ -f "$d/remove" ] || continue
    id=${d##*/}
    case "$id" in ''|.*|*[!A-Za-z0-9._-]*) echo "Modules: invalid module id"; exit 1 ;; esac
    [ ! -L "$M/$id" ] && [ ! -L "$U/$id" ] || exit 1
    rm -rf "$M/$id" "$U/$id" || exit 1
    echo "Modules: $id removed"
done
for d in "$U"/*; do
    [ -d "$d" ] && [ ! -L "$d" ] || continue
    id=${d##*/}
    case "$id" in ''|.*|*[!A-Za-z0-9._-]*) echo "Modules: invalid module id"; exit 1 ;; esac
    [ ! -L "$M/$id" ] || exit 1
    rm -rf "$M/$id" && mv "$d" "$M/$id" && rm -f "$M/$id/update" && echo "Modules: $id updated" || exit 1
done

# The image's folder for a path under a module's system/ (inside the tree only).
target() {
    case "$1" in
        vendor/*|product/*|system_ext/*|odm/*) set -- "$R/$1" "$R/system/$1" ;;
        *) set -- "$R/system/$1" ;;
    esac
    for c; do
        p=$($BB realpath "$($BB dirname "$c")" 2>/dev/null) || continue
        under "$p" && { echo "$p/${c##*/}"; return 0; }
    done
    return 1
}
# A tmpfs copy of folder $1 bound over it, so new entries can go in: every
# entry of the original bound into the copy (links copied).
mirror() {
    a=$1
    $BB awk -v m="$a" '$2 == m { f = 1 } END { exit !f }' "$W/.mirrored" 2>/dev/null && return 0
    under "$a" && [ -d "$a" ] && [ ! -L "$a" ] || return 1
    t=$W/$($BB echo "$a" | $BB md5sum | cut -c1-12)
    mkdir -p "$t" && $BB mount -t tmpfs -o mode=0755 tmpfs "$t" || return 1
    $BB chmod "$($BB stat -c %a "$a")" "$t"; $BB chown "$($BB stat -c %u:%g "$a")" "$t"
    for e in $(ls -A "$a"); do
        if [ -L "$a/$e" ]; then $BB cp -P "$a/$e" "$t/$e"
        elif [ -d "$a/$e" ]; then mkdir "$t/$e" && $BB mount --rbind "$a/$e" "$t/$e"
        else : > "$t/$e" && $BB mount --bind "$a/$e" "$t/$e"
        fi
    done
    # Private before anything goes on top: a bind of a /data file (a module's) is
    # in /data's peer group, and a mount on it would show up in One UI's /data.
    $BB mount --make-rprivate "$t" 2>/dev/null
    $BB mount --rbind "$t" "$a" || { $BB umount -l "$t"; return 1; }
    $BB mount --make-rprivate "$a" 2>/dev/null
    record "$a"
    echo "$a" >> "$W/.mirrored"
}
# Make folder $2 (an absolute path inside the tree) exist, mirroring the
# deepest existing ancestor so the new folders can be created.
ensure_dir() {
    [ -d "$1" ] && return 0
    p=$1
    while [ ! -d "$p" ]; do p=$($BB dirname "$p"); done
    under "$p" || return 1
    mirror "$p" || return 1
    mkdir -p "$1"
}

n_mod=0
for d in "$M"/*; do
    [ -d "$d" ] && [ ! -L "$d" ] || continue
    id=${d##*/}
    [ -e "$d/disable" ] && { echo "Modules: $id disabled"; continue; }
    n_mod=$((n_mod + 1))
    note=""
    for f in post-fs-data.sh service.sh post-mount.sh boot-completed.sh system.prop sepolicy.rule; do
        [ -f "$d/$f" ] && note="$note $f"
    done
    [ -n "$note" ] && echo "Modules: $id has$note, not run in a guest system"
    [ -e "$d/skip_mount" ] && { echo "Modules: $id: skip_mount"; continue; }
    [ -d "$d/system" ] || { echo "Modules: $id: nothing to mount"; continue; }
    files=0 new=0 skipped=0
    # Folders with .replace first, as a whole.
    for r in $(cd "$d/system" && find . -name .replace -type f 2>/dev/null | sed 's|^\./||; s|/\.replace$||'); do
        tg=$(target "$r") || { skipped=$((skipped + 1)); continue; }
        ensure_dir "$tg" && $BB mount --bind "$d/system/$r" "$tg" && $BB mount --make-rprivate "$tg" && record "$tg" && files=$((files + 1)) || skipped=$((skipped + 1))
    done
    for rel in $(cd "$d/system" && find . \( -type f -o -type l \) ! -name .replace 2>/dev/null | sed 's|^\./||'); do
        skip=0
        for r in $(cd "$d/system" && find . -name .replace -type f 2>/dev/null | sed 's|^\./||; s|/\.replace$||'); do
            case "$rel" in "$r"/*) skip=1 ;; esac
        done
        [ $skip = 1 ] && continue
        tg=$(target "$rel") || { skipped=$((skipped + 1)); continue; }
        if [ -f "$tg" ] && [ ! -L "$tg" ] && [ ! -L "$d/system/$rel" ]; then
            $BB mount --bind "$d/system/$rel" "$tg" && $BB mount --make-private "$tg" && record "$tg" && files=$((files + 1)) || skipped=$((skipped + 1))
        else
            dir=$($BB dirname "$tg")
            if ensure_dir "$dir" && mirror "$dir"; then
                if [ -L "$d/system/$rel" ]; then
                    rm -f "$tg"; $BB cp -P "$d/system/$rel" "$tg" && new=$((new + 1))
                else
                    [ -L "$tg" ] && rm -f "$tg"
                    : > "$tg" && $BB mount --bind "$d/system/$rel" "$tg" && $BB mount --make-private "$tg" && record "$tg" && new=$((new + 1)) || skipped=$((skipped + 1))
                fi
            else
                skipped=$((skipped + 1))
            fi
        fi
    done
    echo "Modules: $id: $files replaced, $new added, $skipped skipped"
done
# Nothing may have landed outside the guest's tree; if it did, all of it goes.
outside > "$S/tmp/module_outside.after"
LEAK=$(awk 'NR == FNR { b[$0] = 1; next } !($0 in b)' "$S/tmp/module_outside.before" "$S/tmp/module_outside.after")
if [ -n "$LEAK" ]; then
    for t in $(echo "$LEAK" | sort -r); do $BB umount -l "$t" 2>/dev/null; done
    [ -f "$L" ] && sort -r "$L" | while read -r t; do $BB umount -l "$t" 2>/dev/null; done
    rm -f "$L"
    echo "Modules: ERROR mounts outside the guest's tree ($(echo $LEAK)); all module mounts undone"
    exit 1
fi
echo "Modules: $n_mod enabled for this system ($M)"
GUESTMODULES
cat > "$STAGE/tmp/guest_softreboot.sh" <<'GUESTSOFTREBOOT'
#!/system/bin/sh
# OneOS: a soft reboot of the guest system only (KernelSU's soft reboot inside
# it, through the ksud wrapper; oneos_switch.sh's watcher runs this). Its
# processes stop the way return_to_oneui.sh stops them (every process in its
# mount namespace or on its root), the zygote sockets' pins come off, its own
# modules are applied again (guest_modules.sh), and guest_start.sh starts it
# again in a fresh namespace exactly as the switch did. One UI stays as the
# switch left it (framework stopped, its zygote kept down), and so do the
# session's host helpers (heat cap, keepers, watchdogs, the watcher). No /proc
# file but the namespace link and root of each process is read. Exit 0 once
# guest_start.sh runs again; anything else and the watcher returns to One UI.
S=/data/local/tmp/oneos
[ -n "$BB" ] || for c in /data/adb/ksu/bin/busybox /data/adb/ap/bin/busybox /data/adb/magisk/busybox; do [ -x "$c" ] && { BB=$c; break; }; done
[ -x "$BB" ] || { echo "soft reboot: no busybox"; exit 1; }
GUEST_NS=$(cat $S/guest_mntns 2>/dev/null)
HOST_NS=$(readlink /proc/1/ns/mnt)
GUEST_DEV=$(cat $S/guest_rootdev 2>/dev/null)
HOST_DEV=$(stat -L -c %d /proc/1/root/ 2>/dev/null)
[ "$GUEST_DEV" = "$HOST_DEV" ] && GUEST_DEV=""
[ -n "$GUEST_NS" ] && [ "$GUEST_NS" != "$HOST_NS" ] || { echo "soft reboot: no guest namespace recorded"; exit 1; }
[ -f $S/data/guest_start.sh ] && [ -f $S/data/zygote_exec ] || { echo "soft reboot: guest_start.sh or zygote_exec missing"; exit 1; }
if [ -f "$S/boot_status.sh" ]; then
    . "$S/boot_status.sh"
    oneos_boot_begin restart
    restart_generation=$(cat "$ONEOS_BOOT_DIR/generation")
    restart_wake="oneos_restart_$$"
    echo "$restart_wake" > /sys/power/wake_lock 2>/dev/null || true
    ( end=$(( $(date +%s) + 120 ))
      while [ "$(date +%s)" -lt "$end" ] && [ ! -f "$ONEOS_BOOT_DIR/stop" ] &&
            [ "$(cat "$ONEOS_BOOT_DIR/generation" 2>/dev/null)" = "$restart_generation" ]; do sleep 1; done
      echo "$restart_wake" > /sys/power/wake_unlock 2>/dev/null || true
    ) </dev/null >/dev/null 2>&1 &
    oneos_boot_event 'Stopping guest apps'
    oneos_boot_wait_ready 5 || echo 'Restart splash: retaining the guest app fallback until the renderer reconnects'
    oneos_boot_hold_display 'Restarting guest'
fi
echo "$(date +%T) soft reboot ($1): stopping the guest's processes"
pass=1
while [ $pass -le 5 ]; do
    killed=""
    for p in /proc/[0-9]*; do
        if [ "$(readlink "$p/ns/mnt" 2>/dev/null)" != "$GUEST_NS" ]; then
            [ -n "$GUEST_DEV" ] && [ "$(stat -L -c %d "$p/root/" 2>/dev/null)" = "$GUEST_DEV" ] || continue
        fi
        pid=${p#/proc/}
        killed="$killed $pid:$(cat "$p/comm" 2>/dev/null)"
        kill -9 "$pid" 2>/dev/null
    done
    [ $pass = 1 ] && echo "$(date +%T) soft reboot: killed$(echo "$killed" | wc -w | sed 's/^/ /') guest processes"
    [ -n "$killed" ] || break
    pass=$((pass + 1)); sleep 0.3
done
[ $pass -le 5 ] || { echo "soft reboot: guest processes still running after 5 passes"; exit 1; }
# The zygote sockets were bound onto themselves in init's namespace (the
# switch's protect_zygote_sockets): off, so guest_start.sh can make new ones.
for s in zygote usap_pool_primary; do
    f=/dev/socket/$s
    n=0
    while [ $n -lt 5 ] && $BB awk -v m="$f" '$5 == m { f = 1 } END { exit !f }' /proc/self/mountinfo; do
        $BB umount -l "$f" 2>/dev/null; n=$((n + 1))
    done
    rm -f "$f"
done
rm -f /dev/socket/hyos_spawner
# The guest vold's name (gvld) leaves servicemanager with its process.
n=0
while [ $n -lt 30 ] && service check gvld 2>/dev/null | grep -q ': found'; do n=$((n + 1)); sleep 0.1; done
command -v oneos_boot_event >/dev/null 2>&1 && oneos_boot_event 'Preparing guest modules'
# Restore recorded system.prop values before loading the next set of modules.
if [ -f "$S/data/oneos_root/enabled" ]; then
    "$BB" chroot "$S/rootfs" /system/bin/sh /data/oneos_runtime.sh restore-props || exit 1
fi
# This system's modules, applied again (installs, updates and removals since).
[ -f $S/tmp/guest_modules.sh ] || exit 1
BB=$BB /system/bin/sh $S/tmp/guest_modules.sh || exit 1
if [ -f "$S/data/oneos_root/enabled" ]; then
    # New ZIPs need customize.sh before their generated files are mounted.
    "$BB" chroot "$S/rootfs" /system/bin/sh /data/oneos_runtime.sh install || exit 1
    BB=$BB /system/bin/sh $S/tmp/guest_modules.sh || exit 1
fi
rm -f $S/data/oneos_rec_stop
setprop sys.boot_completed 0
setprop dev.bootcomplete 0
setprop service.bootanim.exit 0
command -v oneos_boot_event >/dev/null 2>&1 && oneos_boot_event 'Starting guest services'
echo "$(date +%T) soft reboot: starting the guest again"
echo "=== OneOS soft reboot $(date '+%F %T') ($1) ===" >> $S/data/takeover.log
$BB unshare -m $BB sh $S/data/guest_start.sh </dev/null >>$S/data/takeover.log 2>&1 &
TP=$!
sleep 0.5
NEW_NS=$(readlink /proc/$TP/ns/mnt 2>/dev/null)
[ -n "$NEW_NS" ] && [ "$NEW_NS" != "$HOST_NS" ] || { echo "soft reboot: the new guest did not start"; exit 1; }
echo "$NEW_NS" > $S/guest_mntns
stat -c %d $S/rootfs > $S/guest_rootdev 2>/dev/null
# The new zygote's sockets pinned again once zygote_exec is app_process64.
( n=0
  while :; do
      ZP=$TP
      if [ -f "$S/data/oneos_root/enabled" ]; then
          ZP=$(cat "$S/data/oneos_root/adb/oneos/run/injection.pid" 2>/dev/null)
          case "$ZP" in ''|*[!0-9]*) ZP=$TP ;; esac
      fi
      case "$(readlink /proc/$ZP/exe 2>/dev/null)" in
          */app_process64) break ;;
          '') exit 0 ;;
      esac
      n=$((n + 1)); [ $n -lt 3000 ] || exit 0
      sleep 0.1
  done
  for s in zygote usap_pool_primary; do
      f=/dev/socket/$s
      [ -S "$f" ] && ! $BB awk -v m="$f" '$5 == m { f = 1 } END { exit !f }' /proc/self/mountinfo &&
          $BB mount --bind "$f" "$f" && echo "$(date +%T) soft reboot: $f pinned again"
  done ) </dev/null >>$S/auto_return.log 2>&1 &
g=$(cat $S/tmp/softreboot.gen 2>/dev/null); case "$g" in ''|*[!0-9]*) g=0 ;; esac
echo $((g + 1)) > $S/tmp/softreboot.gen
echo "$(date +%T) soft reboot: guest_start.sh running again (pid $TP, $NEW_NS), generation $((g + 1))"
exit 0
GUESTSOFTREBOOT
chmod 700 "$STAGE/tmp/guest_modules.sh" "$STAGE/tmp/guest_softreboot.sh"
rm -f "$STAGE/tmp/softreboot.gen" "$STAGE/tmp/module_mounts"
if [ -f "$STAGE/data/oneos_root/enabled" ]; then
    STAGE="$STAGE" /system/bin/sh "$STAGE/guest_runtime.sh" prepare || exit 3
    BB=$BB /system/bin/sh "$STAGE/tmp/guest_modules.sh" || exit 3
fi
if [ -d "$STAGE/data/oneos_ksu/modules" ]; then
    BB=$BB /system/bin/sh "$STAGE/tmp/guest_modules.sh" || echo "Modules: not applied (see above)"
fi

# Nothing of the guest on One UI's own partitions (host_part_mounts, top).
host_part_mounts > "$STAGE/host_part_mounts.after"
LEAKED=$(awk 'NR == FNR { b[$0] = 1; next } !($0 in b)' "$STAGE/host_part_mounts.before" "$STAGE/host_part_mounts.after")
if [ -n "$LEAKED" ]; then
    echo "ERROR: the setup mounted over One UI's own partitions:" $LEAKED
    for m in $(echo "$LEAKED" | sort -r); do $BB umount -l "$m" 2>/dev/null && echo "  unmounted $m"; done
    echo "Not starting the guest"
    exit 3
fi
echo "One UI's partitions: no mount added by the setup"

# Capture existing preferences before the first signed-launcher startup;
# the bounded worker overlays only the pinned APKs after package scanning.
STAGE="$STAGE" BB="$BB" /system/bin/sh "$STAGE/fold8_coloros.sh" addons-prepare || exit 3
# /system_ext's own mount (SEXT_MOUNT, top): the real folder with everything
# mounted under it so far, so /system_ext/... is what the guest's zygote sees.
if [ "$SEXT_MOUNT" = 1 ]; then
    if $BB mount --rbind "$ROOTFS/system/system_ext" "$ROOTFS/system_ext" &&
       $BB mount --make-rprivate "$ROOTFS/system_ext" 2>/dev/null &&
       [ "$(stat -c %d:%i "$ROOTFS/system_ext/framework" 2>/dev/null)" = "$(stat -c %d:%i "$ROOTFS/system/system_ext/framework" 2>/dev/null)" ]; then
        echo "/system_ext: bound to /system/system_ext (its own mount point for the guest)"
    else
        echo "ERROR: could not bind /system/system_ext onto /system_ext; not starting the guest"
        exit 3
    fi
fi
echo "=== ALL MOUNTS PREPARED SUCCESSFULLY $(date +%T) ==="
