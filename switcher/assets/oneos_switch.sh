#!/system/bin/sh
# The OneOS session: the userspace takeover (started from WeWaffles' OneLineage
# switch_to_lineage.sh).
STAGE="/data/local/tmp/oneos"
# ONEOS_APP=1 (session.env): started by the OneOS app's root script. Then every
# preflight check below has to pass. Without it (the owner's adb loop,
# scripts/deploy-phone.sh) the app-only checks are skipped and a few warn.
APP="${ONEOS_APP:-0}"
[ "$APP" = 1 ] || APP=0

# --- PREFLIGHT ------------------------------------------------------------
# Every refusal comes before the first change to the phone (SELinux, props,
# watchdogs, One UI's framework), so a refused switch leaves One UI exactly as
# it was. Up to run 35 system.raw was only checked at [4/6], after setenforce
# 0, the persist snapshot, the watchdogs, disable_rescue and the BPF update,
# and that exit undid none of them.
refuse() {
    echo "PREFLIGHT REFUSED: $*"
    echo "Nothing on the phone was changed; One UI keeps running."
    exit 2
}
app_refuse() {
    [ "$APP" = 1 ] && refuse "$*"
    echo "WARNING (no ONEOS_APP): $*"
}
# Owned by root and writable by root only (stat %A: group w is the 6th
# character, other w the 9th).
root_only() {
    case "$(stat -c '%u %A' "$1" 2>/dev/null)" in
        "0 "?????w*|"0 "????????w*) return 1 ;;
        "0 "*) return 0 ;;
    esac
    return 1
}
[ "$(id -u 2>/dev/null)" = 0 ] || refuse "not running as root"

# Root tools: the root manager's own busybox and resetprop (KernelSU, APatch,
# Magisk), never whatever a search of /data finds (OneLineage fell back to
# `find /data -name busybox`). A missing resetprop is fatal: without it
# guest_props.sh can neither snapshot nor restore One UI's persist.* props.
BB=""
for c in /data/adb/ksu/bin/busybox /data/adb/ap/bin/busybox /data/adb/magisk/busybox; do
    [ -x "$c" ] && { BB=$c; break; }
done
RP=""
for c in /data/adb/ksu/bin/resetprop /data/adb/ap/bin/resetprop /debug_ramdisk/resetprop /sbin/resetprop; do
    [ -x "$c" ] && { RP=$c; break; }
done
if [ "$APP" != 1 ]; then
    [ -n "$BB" ] || BB=$(command -v busybox 2>/dev/null)
    [ -n "$RP" ] || RP=$(command -v resetprop 2>/dev/null)
fi
[ -n "$BB" ] && [ -x "$BB" ] || refuse "no busybox at the root manager's paths (/data/adb/ksu/bin, /data/adb/ap/bin, /data/adb/magisk)"
APPLETS=" $("$BB" --list 2>/dev/null | tr '\n' ' ') "
missing=""
for a in sh mount umount losetup unshare nsenter pivot_root setsid awk grep sed; do
    case "$APPLETS" in *" $a "*) ;; *) missing="$missing $a" ;; esac
done
[ -z "$missing" ] || refuse "$BB lacks the applets:$missing"
# guest_prepare.sh attaches system.raw read-only (losetup -r).
"$BB" losetup --help 2>&1 | grep -q -e '-[A-Za-z]*r' || app_refuse "$BB losetup shows no -r (read-only loop device)"
[ -n "$RP" ] && [ -x "$RP" ] || refuse "no resetprop at the root manager's paths: One UI's persist.* props could not be saved and restored"
FP=$(getprop ro.build.fingerprint 2>/dev/null)
[ -n "$FP" ] && [ "$("$RP" ro.build.fingerprint 2>/dev/null)" = "$FP" ] || refuse "$RP does not read properties"
command -v sha256sum >/dev/null 2>&1 || refuse "no sha256sum"
command -v getevent >/dev/null 2>&1 || app_refuse "no getevent: Volume Up + Volume Down could not return to One UI"

# init's mount namespace. One UI's installd and artd run there: binds made in
# any other namespace (a root shell can get its own, e.g. KernelSU's per-app
# mount namespace option) would never reach them, and they would write into
# One UI's real /data for the guest (run 25). The app's launch enters init's
# namespace with nsenter; the adb loop is run again there, once.
SELF_NS=$(readlink /proc/$$/ns/mnt 2>/dev/null)
INIT_NS=$(readlink /proc/1/ns/mnt 2>/dev/null)
if [ -z "$SELF_NS" ] || [ "$SELF_NS" != "$INIT_NS" ]; then
    if [ "$APP" != 1 ] && [ -z "$ONEOS_NS_REENTERED" ]; then
        echo "Not in init's mount namespace (${SELF_NS:-unreadable}, init ${INIT_NS:-unreadable}): running again in init's"
        export ONEOS_NS_REENTERED=1
        exec "$BB" nsenter -t 1 -m -- /system/bin/sh "$STAGE/oneos_switch.sh" "$@"
    fi
    refuse "not in init's mount namespace (this shell: ${SELF_NS:-unreadable}, init: ${INIT_NS:-unreadable})"
fi

# The stage's name up to app 0.3.6 (OneLineage's). The app's root script and
# scripts/deploy-phone.sh rename it to $STAGE, only while it is idle; a session
# never starts while it is still there, so nothing runs from two stages.
LEGACY_STAGE=/data/local/tmp/lineage_stage
if [ -d "$LEGACY_STAGE" ] && [ ! -L "$LEGACY_STAGE" ]; then
    [ -e "$STAGE" ] || [ -L "$STAGE" ] ||
        refuse "the stage is still at its old path $LEGACY_STAGE, not $STAGE: prepare again in the OneOS app (or run scripts/deploy-phone.sh), which renames it"
    refuse "both $STAGE and the old $LEGACY_STAGE are on this phone: OneOS uses one stage; move the one you do not need aside (e.g. to $STAGE.old-<epoch>, which the OneOS app lists under Old copies)"
fi
[ -d "$STAGE" ] && [ ! -L "$STAGE" ] || refuse "$STAGE is missing or not a directory"
root_only "$STAGE" || app_refuse "$STAGE is not root's or is writable by others ($(stat -c '%U:%G %A' "$STAGE" 2>/dev/null))"
[ -f "$STAGE/system.raw" ] || refuse "the guest image ($STAGE/system.raw) is not staged"
for f in oneos_switch.sh guest_prepare.sh guest_start.sh guest_props.sh return_to_oneui.sh libsec-ril-patch.sh \
         check_host_apex.sh bridges.sh fold8_coloros.sh guest_google.sh zygote_exec guards.txt services_patched.jar; do
    [ -f "$STAGE/$f" ] || refuse "$STAGE/$f is missing"
done
# The guarded jars: services_patched.jar, and oplus-services_patched.jar for a
# ColorOS image, miui-services_patched.jar and apprecovery.proinstaller_patched.jar
# for a HyperOS one (guards.txt lists what make-overlays.sh built;
# guest_prepare.sh refuses an image with oplus-services.jar or miui-services.jar
# that lacks them). A set's
# vold_patched and service.incremental_patched.so (Pixel 17, and ColorOS 17
# since 0.4.8) go with its guarded jars (the guest vold as "gvld", run 44), so
# they are checked the same way.
GUARD_JARS="services_patched.jar $(awk '$2 == "oplus-services_patched.jar" || $2 == "vold_patched" || $2 == "service.incremental_patched.so" ||
                                       $2 == "miui-services_patched.jar" || $2 == "apprecovery.proinstaller_patched.jar" ||
                                       $2 == "framework_patched.jar" || $2 == "miui-wifi-service_patched.jar" || $2 == "miui-telephony-common_patched.jar" ||
                                       $2 == "telephony-common_patched.jar" { print $2 }' "$STAGE/guards.txt")"

if [ "$APP" = 1 ]; then
    # Every staged file (files.sha256, written by the app's root script; all
    # but system.raw) is checked, not only the two guarded jars: the scripts,
    # zygote_exec, bridges.sh, surfaceflinger_patched, the other jars, the
    # payloads and the RROs are all bound or run as root.
    SUMS="$STAGE/files.sha256"
    [ -f "$SUMS" ] && [ ! -L "$SUMS" ] && root_only "$SUMS" || refuse "files.sha256 is missing, or not root's"
    bad=$(awk 'NF != 2 || length($1) != 64 || $1 ~ /[^0-9a-f]/ || $2 !~ /^[A-Za-z0-9_][A-Za-z0-9._-]*$/ ||
               $2 == "system.raw" || seen[$2]++ { print NR ": " $0 }' "$SUMS" | head -3)
    [ -z "$bad" ] || refuse "files.sha256 has malformed lines: $bad"
    for need in oneos_switch.sh guest_prepare.sh guest_start.sh guest_props.sh return_to_oneui.sh libsec-ril-patch.sh \
                check_host_apex.sh bridges.sh zygote_exec guards.txt $GUARD_JARS; do
        awk -v n="$need" '$2 == n { f = 1 } END { exit !f }' "$SUMS" || refuse "files.sha256 does not list $need"
    done
    while read -r sum name || [ -n "$sum" ]; do
        f="$STAGE/$name"
        [ -f "$f" ] && [ ! -L "$f" ] || refuse "$name (files.sha256) is missing or a link"
        root_only "$f" || refuse "$name is not root's or is writable by others"
        [ "$(sha256sum "$f" 2>/dev/null | cut -d' ' -f1)" = "$sum" ] || refuse "$name does not match files.sha256"
    done < "$SUMS"
    # A leftover the package does not carry would still be bound by
    # guest_prepare.sh (framework_patched.jar, libaudio*_patched.so,
    # PermissionController_patched.apk, an extra payload, an apex info list).
    for f in "$STAGE"/*; do
        [ -f "$f" ] || [ -L "$f" ] || continue
        n=${f##*/}
        case "$n" in
            *_patched*|*_payload.img|*.apk|clean_apex_info_list.xml)
                awk -v n="$n" '$2 == n { f = 1 } END { exit !f }' "$SUMS" ||
                    refuse "$n is in $STAGE but not in files.sha256 (left from an older stage)" ;;
        esac
    done
    # system.raw is verified once, at staging (10 GB); since then its identity
    # must be unchanged: "<size> <sha256>" and stat dev:inode:size:mtime.
    ID="$STAGE/system.raw.id"
    [ ! -L "$STAGE/system.raw" ] && root_only "$STAGE/system.raw" || refuse "system.raw is a link, or not root's"
    [ -f "$ID" ] && root_only "$ID" || refuse "system.raw.id is missing, or not root's"
    ID_STAT=$(tr '\n' ' ' < "$ID" | awk 'NF == 3 && $1 ~ /^[0-9]+$/ && length($2) == 64 && $2 !~ /[^0-9a-f]/ &&
        $3 ~ /^[0-9]+:[0-9]+:[0-9]+:[0-9]+$/ && split($3, s, ":") == 4 && s[3] == $1 { print $3 }')
    [ -n "$ID_STAT" ] || refuse "system.raw.id is not \"<size> <sha256> <dev:inode:size:mtime>\""
    [ "$(stat -c '%d:%i:%s:%Y' "$STAGE/system.raw" 2>/dev/null)" = "$ID_STAT" ] ||
        refuse "system.raw changed since it was verified (system.raw.id $ID_STAT, now $(stat -c '%d:%i:%s:%Y' "$STAGE/system.raw" 2>/dev/null))"
    # The ways back to One UI and the session log cannot be switched off from
    # the app: the root script never writes these keys, checked again here.
    ENVF="$STAGE/session.env"
    [ -f "$ENVF" ] && root_only "$ENVF" && grep -qx 'ONEOS_APP=1' "$ENVF" || refuse "session.env is missing, not root's, or lacks ONEOS_APP=1"
    RMAX=${ONEOS_RETURN_MAX:-600}; RBLACK=${ONEOS_RETURN_BLACK:-150}
    case "$RMAX:$RBLACK" in *[!0-9:]*|:*|*:) refuse "ONEOS_RETURN_MAX/ONEOS_RETURN_BLACK not numbers" ;; esac
    [ "$RMAX" -ge 300 ] && [ "$RMAX" -le 900 ] || refuse "ONEOS_RETURN_MAX=$RMAX (300..900)"
    [ "$RBLACK" -ge 60 ] && [ "$RBLACK" -le "$RMAX" ] || refuse "ONEOS_RETURN_BLACK=$RBLACK (60..ONEOS_RETURN_MAX)"
    [ "${ONEOS_RETURN_KEYS:-1}" = 1 ] || refuse "ONEOS_RETURN_KEYS=$ONEOS_RETURN_KEYS"
    # 0.4.7: the app's session.env asks for the in-place return (run 48); any
    # check that fails there still reboots (return_to_oneui.sh failsafe).
    case "${ONEOS_RETURN_MODE:-reboot}" in reboot|inplace) ;; *) refuse "ONEOS_RETURN_MODE=$ONEOS_RETURN_MODE" ;; esac
    [ "${ONEOS_LOGCAT:-1}" = 1 ] || refuse "ONEOS_LOGCAT=$ONEOS_LOGCAT"
    [ "${ONEOS_STOCK_SF:-0}" = 0 ] || refuse "ONEOS_STOCK_SF=$ONEOS_STOCK_SF"
    [ "${ONEOS_KEEP_FOLD_LAYOUT:-0}" = 0 ] || refuse "ONEOS_KEEP_FOLD_LAYOUT=$ONEOS_KEEP_FOLD_LAYOUT"
    # ColorOS's own use of the return chord would turn TalkBack on (run 34).
    [ "${ONEOS_GUEST_A11Y_SHORTCUT:-0}" = 0 ] || refuse "ONEOS_GUEST_A11Y_SHORTCUT=$ONEOS_GUEST_A11Y_SHORTCUT"
    case "${ONEOS_PREPARE_ONLY:-0}" in 0|1) ;; *) refuse "ONEOS_PREPARE_ONLY=$ONEOS_PREPARE_ONLY" ;; esac
    env | grep -q '^ONEOS_TUNNEL_' && refuse "ONEOS_TUNNEL_* set"
fi
# Google services in a Pixel guest (guest_prepare.sh, docs/pixel-guest.md):
# ONEOS_GUEST_GMS is 0 or 1, unset meaning 1, from the app and the adb loop
# alike; and not on together with ONEOS_GUEST_HIDE_GMS=1 when the payload is
# staged. guest_prepare.sh checks both again, with the guards and the stage's
# app ids, but only after One UI's framework is stopped.
case "${ONEOS_GUEST_GMS:-1}" in 0|1) ;; *) refuse "ONEOS_GUEST_GMS=$ONEOS_GUEST_GMS (0 or 1)" ;; esac
# Cool down when hot (the heat cap below): 0 or 1, unset meaning 1.
case "${ONEOS_HEAT_CAP:-1}" in 0|1) ;; *) refuse "ONEOS_HEAT_CAP=$ONEOS_HEAT_CAP (0 or 1)" ;; esac
[ "${ONEOS_GUEST_GMS:-1}" = 1 ] && [ "${ONEOS_GUEST_HIDE_GMS:-0}" = 1 ] && [ -f "$STAGE/gmssystem_payload.img" ] &&
    refuse "ONEOS_GUEST_GMS is on (the default) with gmssystem_payload.img staged, and ONEOS_GUEST_HIDE_GMS=1 hides Google services: set one of them to 0"
# The same guard and app-id checks as guest_prepare.sh, here so a refusal comes
# before One UI's framework stops (after it, guest_prepare's exit 3 reboots).
if [ "${ONEOS_GUEST_GMS:-1}" = 1 ] && [ -f "$STAGE/gmssystem_payload.img" ]; then
    for t in gatekeeper pdb apexd appid15000; do
        grep '^#' "$STAGE/guards.txt" 2>/dev/null | grep -qw "$t" ||
            refuse "Google services: guards.txt lacks the $t guard (ONEOS_GUEST_GMS=0 starts without Google services)"
    done
    awk -v ksu="me.weishu.kernelsu com.rifsxd.ksunext com.sukisu.ultra app.kitsusu.manager" 'BEGIN { split(ksu, a, " "); for (i in a) m[a[i]] = 1 } $2 ~ /^[0-9]+$/ && $2 >= 10000 && $2 <= 14999 && !($1 in m) { f = 1 } END { exit !f }' "$STAGE/data/system/packages.list" 2>/dev/null &&
        refuse "Google services: the stage has guest app ids 10000-14999 from before the app-id guard (a fresh guest data dir, or ONEOS_GUEST_GMS=0)"
fi

# The guarded framework jars (scripts/make-overlays.sh: storage, installd,
# power, sysrq and weaver guards). guest_prepare.sh checks them again.
for need in $GUARD_JARS; do
    sum=$(awk -v n="$need" '$2 == n {print $1}' "$STAGE/guards.txt")
    [ -n "$sum" ] && [ "$(sha256sum "$STAGE/$need" 2>/dev/null | cut -d' ' -f1)" = "$sum" ] ||
        refuse "$need is missing or not the guarded build in guards.txt"
done
# The guest vold as "gvld" takes both binaries (guest_prepare.sh refuses one
# alone too, but only once One UI's framework is stopped).
[ "$(awk '$2 == "vold_patched" { v = 1 } $2 == "service.incremental_patched.so" { i = 1 } END { print v + i }' "$STAGE/guards.txt")" = 1 ] &&
    refuse "guards.txt lists only one of vold_patched and service.incremental_patched.so (a half-built set)"
# The /data bridges (bridges.sh) and their floor, as guest_prepare.sh needs
# them; nothing may be left mounted under the stage or bridged from a session
# that never returned (the return reboots, which removes them).
BRIDGES=""
. "$STAGE/bridges.sh" || refuse "bridges.sh unreadable"
for need in app:app user:user user_de:user_de data:user/0 media:media; do
    case " $BRIDGES " in *" $need "*) ;; *) refuse "bridges.sh lacks $need" ;; esac
done
left=$(awk -v s="$STAGE/" 'index($5, s) == 1 {print $5}' /proc/self/mountinfo | head -3 | tr '\n' ' ')
[ -z "$left" ] || refuse "mounted under the stage ($left): a session is running or never returned; return to One UI (reboot) first"
for pair in $BRIDGES; do
    awk -v p="/data/${pair%%:*}" '$5 == p' /proc/self/mountinfo | grep -q . &&
        refuse "/data/${pair%%:*} is still bridged from an earlier session; return to One UI (reboot) first"
done
# The gap splash (below): the OneOS app's GapSplashActivity, started by root
# (it is not exported). ONEOS_SPLASH_COMPONENT names another package/.Activity,
# e.g. com.wewaffles.onelineage/.SplashActivity for the old switcher.
SPLASH_COMPONENT="${ONEOS_SPLASH_COMPONENT:-com.fahadali.oneos/.ui.GapSplashActivity}"
case "$SPLASH_COMPONENT" in
    */*/*|/*|*/|*[!A-Za-z0-9._/]*) refuse "ONEOS_SPLASH_COMPONENT=$SPLASH_COMPONENT is not package/.Activity" ;;
    */*) ;;
    *) refuse "ONEOS_SPLASH_COMPONENT=$SPLASH_COMPONENT is not package/.Activity" ;;
esac
# One UI's property space. Each property context is one fixed-size file in
# /dev/__properties__ (prop_area: a 128-byte header, bytes_used first) that
# only grows: a property resetprop deletes leaves its slot behind until the
# next reboot. With the in-place return the phone does not reboot between
# sessions, and every session adds the guest's build properties (the persist.sys.*
# ones to the same area as persist.sys.disable_rescue). The S25 Ultra's second
# session of a night (485d5ffa, 0.4.17): init "__system_property_add failed"
# for persist.sys.disable_rescue, guest_props added 339 of 439, and guest_start.sh
# rightly refused to start the guest without it, after One UI was already
# stopped. Checked here instead, before anything changes.
pa_free() { # bytes left in the property area file $1
    s=$(stat -c %s "$1" 2>/dev/null)
    u=$("$BB" od -An -tu4 -N4 "$1" 2>/dev/null | tr -d ' ')
    case "$s:$u" in *[!0-9:]*|:*|*:) return 1 ;; esac
    echo $((s - 128 - u))
}
# Two areas: the one holding persist.sys.disable_rescue, and the one property
# names One UI's policy does not know land in (default_prop: every
# persist.vivo.*, ro.vivo.*... of a vivo guest). Properties are never removed,
# only blanked, so each session's new names stay until the phone restarts; the
# sixth OriginOS run found default_prop full (196476 of 196608 bytes) and its
# system_server died setting a persist.vivo property.
# vivo OriginOS adds about 380 persist names of its own at runtime (audio policy:
# persist.vivo.audio.*, persist.sys.audio.vapc.*), about 45 to 95 KB of
# default_prop a session by the seventh run's count: it starts only with room for it.
PA_CTX=$(getprop -Z persist.sys.disable_rescue 2>/dev/null)
PA_DEF=$(getprop -Z oneos.unknown.name.probe 2>/dev/null)
PA_NEED_CTX=16384; PA_NEED_DEF=16384
if grep -q ' vivo-services_patched\.jar$' "$STAGE/guards.txt" 2>/dev/null; then
    PA_NEED_CTX=32768; PA_NEED_DEF=98304
    # A vivo session earlier in this boot left those names blanked in memory
    # (guest_props.sh store-on): the next one writes into the same slots.
    if [ "$(cat "$STAGE/guest_props.blanked.boot" 2>/dev/null)" = "$(cat /proc/sys/kernel/random/boot_id 2>/dev/null)" ] &&
       [ "$(grep -c '^persist\.vivo\.' "$STAGE/guest_props.blanked" 2>/dev/null)" -ge 100 ]; then
        PA_NEED_CTX=16384; PA_NEED_DEF=32768
    fi
fi
for PA_FILE in "/dev/__properties__/${PA_CTX:-u:object_r:system_prop:s0}" "/dev/__properties__/${PA_DEF:-u:object_r:default_prop:s0}"; do
    PA_NEED=$PA_NEED_CTX; [ "$PA_FILE" = "/dev/__properties__/${PA_DEF:-u:object_r:default_prop:s0}" ] && PA_NEED=$PA_NEED_DEF
    if PA_LEFT=$(pa_free "$PA_FILE"); then
        [ "$PA_LEFT" -ge "$PA_NEED" ] ||
            refuse "One UI's property space is nearly full ($((PA_LEFT / 1024)) KB left in ${PA_FILE##*/}): the sessions since the phone last restarted used it up. Restart the phone, then switch again"
        [ "$PA_LEFT" -ge 49152 ] || echo "WARNING: One UI's property space is getting full ($((PA_LEFT / 1024)) KB left in ${PA_FILE##*/}); some of the other system's settings may not load. Restart the phone before the next session"
    else
        echo "WARNING: could not read the free property space in $PA_FILE"
    fi
done
# One UI's thermal HAL taken down by a root module. Galaxy S23 Ultra ColorOS
# report 6a474324 (0.4.73, GUEST_DEAD after 110 s): ZyC_ThermalKiller and
# kreapic-disable-thermal-universal were on; One UI's thermal service had no
# temperatures before the stop ("thermal service none"; the earlier sessions of
# that phone read 40 C), and init could not start the HIDL thermal HAL again
# (hwservicemanager: "Unable to set property ctl.interface_start to
# android.hardware.thermal@1.0::IThermal/default", 1140 times). Every
# system_server started after that waits for that HAL on its main thread
# (HardwarePropertiesManagerService.nativeInit: "Thermal AIDL service is not
# declared, trying HIDL", then "Waited one second for
# android.hardware.thermal@1.0::IThermal/default") until its watchdog kills it:
# ColorOS's after 72 s, then One UI's own after the in-place return after 69 s,
# and the return's failsafe restarted the phone. Asked while One UI's thermal
# service still answers, only when such a module is on.
TH_MODS=""
for m in /data/adb/modules/*; do
    [ -d "$m" ] && [ ! -f "$m/disable" ] && [ ! -f "$m/remove" ] || continue
    if printf '%s\n' "${m##*/}" | grep -q -i therm ||
       sed -n 's/^name=//p' "$m/module.prop" 2>/dev/null | head -n 1 | grep -q -i therm; then
        TH_MODS="$TH_MODS ${m##*/}"
    fi
done
if [ -n "$TH_MODS" ]; then
    if timeout 10 dumpsys thermalservice 2>/dev/null | grep -q '^HAL Ready: false'; then
        refuse "One UI's thermal HAL is not running (thermal service: HAL Ready: false) and a root module that turns thermal control off is on:$TH_MODS. The other system's framework would wait for that HAL and stop after a minute, and One UI's own after the return too. Turn the module off in your root manager, restart the phone, then switch again"
    fi
    echo "Thermal modules on:$TH_MODS (One UI's thermal service did not report HAL Ready: false)"
fi
echo "Preflight passed (ONEOS_APP=$APP, profile ${ONEOS_PROFILE:-none}, busybox $BB, resetprop $RP, mount namespace $SELF_NS)"

# Every ColorOS set (pull request #1 began it for the Z Fold8): copy One UI's
# Play services and Play Store APK files, never their data, while One UI's
# package manager still runs, after checking the stage's guards
# (switcher/assets/guest_google.sh). It never refuses: without a copy the guest
# starts without them.
STAGE="$STAGE" BB="$BB" /system/bin/sh "$STAGE/guest_google.sh" snapshot ||
    echo "!!! guest_google.sh snapshot failed; the guest starts without One UI's Play services"

# mksh keeps a short here-document in memory and writes a long one to a temp
# file in $TMPDIR, a directory it accepts once, when the shell starts, and
# does not look at again. Started from the app, every long heredoc of
# guest_prepare.sh after its [5d] bridges failed with "can't create
# temporary file : No such file or directory" (run 36a; S25U session
# f075d93a): the shells had a TMPDIR that existed at their start and was gone
# by then (an app's own cache folder under /data/user/0 is what the bridges
# hide; adb shell's TMPDIR=/data/local/tmp never showed it), so
# fix_app_dirs.sh, ensure_app_storage.sh, net_fix.sh and app_storage_loop.sh
# were never written. The stage's own folder, root's alone, kept for the
# whole session; a link in its place (a guest with root) is refused like the
# other staged paths. guest_start.sh sets its own after the pivot.
[ ! -L "$STAGE/tmp" ] || refuse "$STAGE/tmp is a symlink"
mkdir -p "$STAGE/tmp" && chown 0:0 "$STAGE/tmp" && chmod 0700 "$STAGE/tmp" || refuse "could not make $STAGE/tmp"
export TMPDIR="$STAGE/tmp"

# Out of the launching app's cgroup and away from the OOM killer:
# ActivityManager kills an app's whole cgroup when the app dies, and a switch
# killed half way leaves One UI stopped with nothing to bring it back.
# Everything started below inherits both.
echo $$ > /sys/fs/cgroup/cgroup.procs 2>/dev/null
echo -1000 > /proc/$$/oom_score_adj 2>/dev/null

export BB
export RP
export STAGE

set_prop() {
    if [ -n "$RP" ] && [ -x "$RP" ]; then
        "$RP" "$1" "$2" 2>/dev/null || true
    else
        setprop "$1" "$2" 2>/dev/null || true
    fi
}

echo "=== OneOS guest takeover starting ==="
# Samsung's record of the phone's last reset as it stands at the switch (read
# only). Samsung keeps one record, the newest: Galaxy S25 FE reports 7bcdf946
# (ColorOS) and a7bbbb41 (Pixel), both HARD_RESET, sent a kernel panic
# (rt_mutex_adjust_prio_chain, RCNT 10 and 6) at uptime 204 s and 456 s of a
# later boot, 4 and 19 minutes after the session's own reset, with no session
# running: the session's own reset record was gone. RCNT (resets so far) and
# the uptime here tell the next report how many resets came after the switch.
echo "Last reset before this session: $(cat /proc/reset_reason 2>/dev/null | tr -d '\000\n' | head -c 40); $(head -c 600 /proc/extra 2>/dev/null | tr -d '\000' | tr '\n' ' ' | head -c 300); boot reasons $(getprop persist.sys.boot.reason.history | head -n 3 | tr '\n' ' '); uptime $(cut -d' ' -f1 /proc/uptime 2>/dev/null) s"
# One header per session in auto_return.log, which every session appends to:
# the app's last-session screen reads the outcome of the newest session only.
echo "=== OneOS session $(date '+%F %T') epoch $(date +%s) boot $(cat /proc/sys/kernel/random/boot_id 2>/dev/null) app $APP profile ${ONEOS_PROFILE:-none} return max ${ONEOS_RETURN_MAX:-600}s black ${ONEOS_RETURN_BLACK:-150}s keys ${ONEOS_RETURN_KEYS:-1} ===" >> "$STAGE/auto_return.log"

# Prove resetprop can WRITE and DELETE a persist prop, not only read one (the
# preflight only read). Without this the snapshot below is useless and the
# return could not restore One UI's props: on some KernelSU/APatch builds
# resetprop cannot rewrite /data/property or rejects -p --delete, and that only
# showed up at return time. Its own throwaway prop, deleted again; a failure
# here is before the snapshot, so One UI is untouched.
if ! "$RP" -p persist.oneos.probe 1 2>/dev/null || [ "$("$RP" persist.oneos.probe 2>/dev/null)" != 1 ] ||
   ! "$RP" -p --delete persist.oneos.probe 2>/dev/null; then
    "$RP" -p --delete persist.oneos.probe 2>/dev/null
    echo "ERROR: resetprop cannot write persist props on this phone; not switching (One UI's props could not be restored on return)."
    exit 1
fi
# Snapshot the host's persist.* props before anything below or the guest can
# change them; return_to_oneui.sh puts them back (see guest_props.sh). This is
# the first change to the phone: if it fails, nothing else is done.
if ! /system/bin/sh "$STAGE/guest_props.sh" snapshot-persist; then
    echo "ERROR: One UI's persist.* props could not be saved; not switching."
    exit 1
fi
setprop oneos.guest.powerctl "" 2>/dev/null
# "Back to One UI" in the guest's OneOS app (app-android/guest) is a file in
# that app's own data folder: /data/user/0/com.fahadali.oneos.guest/files/
# oneos_return in the guest, whose /data is $STAGE/data. The watcher below acts
# on it like on the keys; one left from an earlier session must not end this
# one as soon as it starts.
GUEST_RETURN_REQ="$STAGE/data/user/0/com.fahadali.oneos.guest/files/oneos_return"
GUEST_RESTART_REQ="$STAGE/data/user/0/com.fahadali.oneos.guest/files/oneos_restart"
rm -f "$GUEST_RETURN_REQ" "$GUEST_RESTART_REQ"
# One UI's protected state, recorded now and compared by return_to_oneui.sh:
# the FRP partition, gatekeeper's files and the APEX state. The guest is kept
# off all three (patches/guest_no_gatekeeper.py, guest_pdb_readonly.py,
# guest_no_apex_installs.py); a difference means a path the guards missed.
# Read only; it only logs.
host_state() {
    f=$(readlink -f "$(getprop ro.frp.pst)" 2>/dev/null)
    [ -b "$f" ] && echo "frp $(sha256sum "$f" 2>/dev/null | cut -d' ' -f1)"
    for p in /data/misc/gatekeeper /data/apex/active /data/apex/sessions; do
        [ -d "$p" ] && find "$p" -type f -exec stat -c '%n %s %Y' {} + 2>/dev/null | sort
    done
}
host_state > "$STAGE/host_state.before"
# A Wi-Fi capture from an earlier session must not be pulled as this one's.
# Nor a fold test or a display capture: run 43's diag_fold was run 41's (lid
# events at 04:17, nothing cleared it), and its HALF_OPENED after a flat
# unfold nearly decided the run-44 posture fix. Nor the rounds (mkdir -p and
# overwrite: a file a round skips this time, such as a stack of an app that is
# not running, would be the last session's) and the return's capture.
rm -rf "$STAGE/diag_wifi" "$STAGE/diag_fold" "$STAGE/diag_display" "$STAGE/diag_pages" \
       "$STAGE/diag_20" "$STAGE/diag_40" "$STAGE/diag_90" "$STAGE/diag_final" "$STAGE/diag_return"
echo "Host state recorded: $(wc -l < "$STAGE/host_state.before") entries"
# This phone's camera hole, while One UI's display service still runs, for
# guest_props.sh (bar phones): the image's ro.oplus.display.screenhole.positon
# is its own phone's. The S25 (1080 px) got the Find X9 Ultra's 679..762
# (1440 px): left of it past the middle (540) is HOLE_RIGHT_TYPE in
# OplusStatusBarUtils.isHoleType, so the status icons ended next to the camera
# with the right half of the bar empty. The top bounding rect of the one
# default-capable internal display (S25: 511,0:569,103), or nothing.
# The rect is in the size One UI runs the panel at, which the guest does not:
# the S25 Ultra at One UI's FHD+ (1080 of its 1440 px) gave 521,0:560,72, and
# ColorOS, on the whole 1440 px panel, took that for a hole left of the
# middle (HOLE_LEFT_TYPE, session e98f44ff): the clock started right of it,
# next to the real camera. Scaled to the panel's physical width
# (cutoutPathParserInfo physicalDisplayWidth / displayWidth); see host_holes below.
rm -f "$STAGE/host_screenhole" "$STAGE/host_cover_screenhole" "$STAGE/host_holes"
# The display modes as One UI's SurfaceFlinger has them, while it is alive (a
# .log in the stage goes into the session's logs): HyperOS's SurfaceFlinger
# aborts at the first display connect on the S24 Ultra, S23 and Z Flip5 ("No
# matching frame rate modes" with an unrestricted policy) before it logs any.
timeout 10 dumpsys SurfaceFlinger --display-id > "$STAGE/display_modes_host.log" 2>&1
# Each mode as SurfaceFlinger made it: hwc id, vsync, dpi, group and the VRR
# config (minFrameIntervalNs) the composer reports, and the peak rate taken
# from it. The S24 Ultra's 0.4.33 sessions showed One UI's 21 modes and the
# composer answering, yet HyperOS's SurfaceFlinger found no mode in an
# unrestricted policy; what it takes the peak rate from is the open question.
timeout 15 dumpsys SurfaceFlinger 2>/dev/null | grep -E 'activeMode=|[{]id=[0-9]+, hwcId=|peakRefreshRate=' | head -n 120 | cut -c1-400 >> "$STAGE/display_modes_host.log"
timeout 10 dumpsys display 2>/dev/null | grep -E 'mSupportedModes|mActiveModeId|mDefaultModeId|DisplayModeRecord|mUserPreferredModeId|mDisplayModeSpecs|DisplayDeviceInfo\{' |
    cut -c1-3000 >> "$STAGE/display_modes_host.log"
for p in /sys/class/lcd/panel /sys/class/lcd/panel1; do
    [ -d "$p" ] || continue
    for n in vrr vrr_lfd; do echo "$p/$n (One UI): $(cat "$p/$n" 2>&1 | tr '\n' ' ' | cut -c1-600)"; done
done >> "$STAGE/display_modes_host.log"
HLINE=$(dumpsys display 2>/dev/null | grep 'DisplayDeviceInfo{' | grep 'type INTERNAL' | grep 'FLAG_ALLOWED_TO_BE_DEFAULT_DISPLAY')
HDW=$(printf '%s\n' "$HLINE" | sed -n 's/.*CutoutPathParserInfo{displayWidth=\([0-9]*\) displayHeight=[0-9]* physicalDisplayWidth=\([0-9]*\) .*/\1/p')
HPW=$(printf '%s\n' "$HLINE" | sed -n 's/.*CutoutPathParserInfo{displayWidth=\([0-9]*\) displayHeight=[0-9]* physicalDisplayWidth=\([0-9]*\) .*/\2/p')
# Each panel's camera on the whole panel (the guest runs every panel at its
# full size), one line per internal panel with a top cutout, in host_holes:
#   <main|cover> <uniqueId> <panel px> <rect> <lens>|<rect spec px>|<lens spec px>|<One UI's rect> at <px>
# main is the largest panel (a bar phone's only one, a fold's or flip's inner
# one); host_screenhole gets its lens, host_cover_screenhole the cover's.
# - Size. One UI's rect is in the size One UI runs the panel at, and an Ultra's
#   One UI scales a @dp spec twice below full size: the S25 Ultra gave
#   521,0:560,72 at FHD+ (1080 of 1440 px; 695,0:747,96 scaled once, report
#   1b63fc7a) and 685,0:755,128 at QHD+ (4933a41d), the S24 Ultra the same
#   521,0:560,72 and 686,0:754,128. Scaled once it is 3/4 of the camera: 52 px,
#   2.7 mm at 498 ppi, where the S25 shows the same front camera as 58 px =
#   3.5 mm at 416 ppi (QHD+: 70 px = 3.6 mm). Distances from a centred @dp
#   spec's top centre scale by (physical / display width)^2, others by the ratio.
# - The lens. One UI's rect runs from the top edge to about the status bar's
#   bottom (S25 103/103 px, S23 98/98, S24 Ultra 128/129), the lens inside it.
#   ColorOS reads ro.oplus.display.screenhole.positon as the lens's own box (the
#   Find X9 Ultra's 679,40:762,123: 83 x 83, centred in its 0..160 framework
#   rect): StatusBarPaddingProvider.updatePaddingTopBottom centres the icons on
#   it, and SystemUIPlugin's capsule (seedling.base.k.b()) is the box's height
#   + 4 dp: One UI's 0..128 rect gave the S25 Ultra a 139 px capsule on a 128 px
#   bar (4933a41d: "calculatePosition: 128 Rect(685, 0 - 755, 128) Rect(685,
#   3 - 755, 142)", "config is error! 128 128 139"). A rect from the top edge
#   more than 15% taller than wide holds a round lens of its width, centred in
#   it; ONEOS_GUEST_HOLE_Y=bottom puts the lens at the rect's bottom, =rect keeps
#   One UI's rect. A spec that is the lens already (A56: a circle, 24..92) stays:
#   a circle spec (an arc, " a ") is the lens, the circle of the rect's width at
#   its bottom. Some builds start its bounds at the spec's M 0,0 above the circle
#   (A53 findings: 512,0:568,88 for "M 0,0 M 0,11.43 a 9.9,9.9 ...", the lens at
#   32..88; one A36 build 505,0:575,92 for the A56's circle at 24..92).
HOLES=$(printf '%s\n' "$HLINE" | awk -v ym="${ONEOS_GUEST_HOLE_Y:-center}" '
    match($0, /uniqueId="local:[0-9]+", [0-9]+ x [0-9]+/) {
        t = substr($0, RSTART + 10, RLENGTH - 10); id = t; sub(/".*/, "", id)
        sub(/^[^"]*", /, "", t); split(t, wh, / x /)
        if (id in area) next
        area[id] = wh[1] * wh[2]; if (area[id] > maxa) maxa = area[id]
        if (!match($0, /boundingRect=\{Bounds=\[Rect\(-?[0-9]+, -?[0-9]+ - -?[0-9]+, -?[0-9]+\), Rect\([0-9]+, [0-9]+ - [0-9]+, [0-9]+\)/)) next
        r = substr($0, RSTART, RLENGTH); sub(/.*Rect\(/, "", r); gsub(/[^0-9]+/, " ", r); split(r, b, " ")
        if (b[3] <= b[1] || b[4] <= b[2]) next
        dw = wh[1]; pw = wh[1]
        if (match($0, /CutoutPathParserInfo\{displayWidth=[0-9]+ displayHeight=[0-9]+ physicalDisplayWidth=[0-9]+/)) {
            c = substr($0, RSTART, RLENGTH); gsub(/[^0-9]+/, " ", c); split(c, cc, " "); dw = cc[1]; pw = cc[3]
        }
        if (dw <= 0 || pw <= 0) next
        sp = ""; if (match($0, /cutoutSpec=\{[^}]*\}/)) sp = substr($0, RSTART, RLENGTH)
        k = pw / dw; if (sp ~ /@dp/ && sp !~ /@left|@right|@bottom|@center_vertical/) k = k * k
        cx = pw / 2 + ((b[1] + b[3]) / 2 - dw / 2) * k; hw = (b[3] - b[1]) / 2 * k
        L = int(cx - hw + 0.5); R = int(cx + hw + 0.5); T = int(b[2] * k + 0.5); B = int(b[4] * k + 0.5)
        hl = L; hr = R; ht = T; hb = B
        if (sp ~ / a /) {
            if (B - T > R - L) { ht = B - (R - L); hb = B }
        } else if (ym != "rect" && T == 0 && B * 20 > (R - L) * 23) {
            ht = (ym == "bottom") ? B - (R - L) : int((B - (R - L)) / 2 + 0.5); hb = ht + R - L
        }
        d = hr - hl; if (hb - ht < d) d = hb - ht
        line[id] = sprintf("%s %d %d,%d:%d,%d %d,%d:%d,%d|M %g,%d L %g,%d L %g,%d L %g,%d Z|M %g,%g a %g,%g 0 1,0 0,%g a %g,%g 0 1,0 0,-%g Z|%d,%d:%d,%d at %d",
            id, pw, L, T, R, B, hl, ht, hr, hb, L - pw / 2, T, L - pw / 2, B, R - pw / 2, B, R - pw / 2, T,
            (hl + hr) / 2 - pw / 2, ht + (hb - ht - d) / 2, d / 2, d / 2, d, d / 2, d / 2, d, b[1], b[2], b[3], b[4], dw)
    }
    END { for (id in line) print ((area[id] == maxa) ? "main " : "cover ") line[id] }')
if [ -n "$HOLES" ]; then
    printf '%s\n' "$HOLES" > "$STAGE/host_holes"
    printf '%s\n' "$HOLES" | while IFS='|' read -r f rs ls raw; do
        set -- $f
        echo "Host camera hole: $1 panel $2 ($3 px): One UI's $raw px; rect $4, lens $5 (spec '$ls')"
    done
    HM=$(printf '%s\n' "$HOLES" | sed -n 's/^main [^ ]* [0-9]* [0-9,:]* \([0-9]*,[0-9]*:[0-9]*,[0-9]*\)|.*/\1/p' | head -n 1)
    HC=$(printf '%s\n' "$HOLES" | sed -n 's/^cover [^ ]* [0-9]* [0-9,:]* \([0-9]*,[0-9]*:[0-9]*,[0-9]*\)|.*/\1/p' | head -n 1)
    [ -n "$HM" ] && echo "$HM" > "$STAGE/host_screenhole"
    [ -n "$HC" ] && echo "$HC" > "$STAGE/host_cover_screenhole"
else
    echo "Host camera hole: not read (no internal panel with a top cutout)"
fi
# This phone's cutout and status bar height, for the UI activator's overlays in a
# Pixel guest (a Galaxy S26 Ultra user, 0.4.17: Pixel's bar far taller than the
# camera hole). The image's own device overlays (product, above OneOS's /oem
# ones) give it the Pixel's cutout and status bar height. One UI's cutout spec
# (cutoutSpec, "@dp", so the same at any resolution) and its status bar's height
# (the statusBars inset at One UI's resolution, scaled to the panel's like the
# hole), from a phone with one default-capable internal display only (a fold's
# two panels are left alone).
rm -f "$STAGE/host_statusbar"
if [ "$(printf '%s\n' "$HLINE" | grep -c .)" = 1 ]; then
    HCS=$(printf '%s\n' "$HLINE" | sed -n 's/.*cutoutSpec={\([^}]*\)}.*/\1/p' | head -n 1)
    HSB=$(timeout 10 dumpsys window 2>/dev/null | sed -n "s/.*type=statusBars frame=\[0,0\]\[$HDW,\([0-9]*\)\].*/\1/p" | head -n 1)
    # The panel's corner radius (RoundedCorner{position=TopLeft, radius=<px>, ...}
    # at One UI's resolution): an image's own corners are its phone's (Infinity-X
    # on the S25 Ultra: radius 0, so SystemUI kept no clear of the curved corners).
    HRC=$(printf '%s\n' "$HLINE" | sed -n 's/.*RoundedCorner{position=TopLeft, radius=\([0-9]*\),.*/\1/p' | head -n 1)
    case "$HDW:$HPW:$HSB" in
        *[!0-9:]*|:*|*::*|*:) HSB='' ;;
        *) [ "$HDW" -gt 0 ] && HSB=$(( (HSB * HPW + HDW / 2) / HDW )) || HSB='' ;;
    esac
    case "$HDW:$HPW:$HRC" in
        *[!0-9:]*|:*|*::*|*:) HRC='' ;;
        *) [ "$HDW" -gt 0 ] && [ "$HRC" -gt 0 ] && HRC=$(( (HRC * HPW + HDW / 2) / HDW )) || HRC='' ;;
    esac
    case "$HCS" in *[!-0-9A-Za-z._,@\ ]*) HCS='' ;; esac
    # The main panel's lens and One UI's rect as pixel specs of the whole panel
    # (host_holes above), for the UI activator: One UI's @dp spec, worked out in
    # a guest at the shared ro.sf.lcd_density (an Ultra's FHD+ 450) on the full
    # 1440 px panel, is 3/4 of the camera there (S24 Ultra, Nothing OS 3066a57c:
    # the guest's 695,0:746,96 for One UI's 686,0:754,128).
    HMP=$(printf '%s\n' "$HOLES" | sed -n 's/^main //p' | head -n 1)
    if [ -n "$HCS$HSB$HRC" ]; then
        { echo "spec=$HCS"; echo "height=$HSB"; echo "radius=$HRC"
          [ -n "$HMP" ] && printf '%s\n' "$HMP" | awk -F'|' '{ split($1, f, " "); print "hole=" f[4]; print "rect_px=" $2; print "hole_px=" $3 }'
        } > "$STAGE/host_statusbar"
        echo "Host status bar: cutout '${HCS:-none}', height ${HSB:-not read} px, corner radius ${HRC:-not read} px on the $HPW px panel; $(grep -E '^(hole|rect_px|hole_px)=' "$STAGE/host_statusbar" | tr '\n' ' ')"
    fi
fi
# The panels' corner radius, for the guests the block above leaves out (0.4.76):
# ColorOS on any phone and every guest on a Fold. An image has its own phone's
# corners: the Find N6's 77 px in ColorOS 17 on the owner's Fold, whose panels
# are 15 px in One UI (11-10: "each time i open any app it shows rounded cutout
# before showing full page", Circle to Search's frame the same). The radius of
# every default-capable internal panel, each at its panel's resolution like the
# one above; the smallest, since one value serves both panels of a Fold and a
# corner cut too small only hides under the panel's own.
rm -f "$STAGE/host_corner_radius"
HCR=$(printf '%s\n' "$HLINE" | awk '
    function num(re,   t) { if (!match($0, re)) return ""; t = substr($0, RSTART, RLENGTH); sub(/.*=/, "", t); return t }
    { r = num("RoundedCorner[{]position=TopLeft, radius=[0-9]+"); if (r == "") { bad = 1; next }
      dw = num("CutoutPathParserInfo[{]displayWidth=[0-9]+"); pw = num("physicalDisplayWidth=[0-9]+")
      r += 0; if (dw + 0 > 0 && pw + 0 > 0) r = int((r * pw + dw / 2) / dw)
      n++; if (n == 1 || r < min) min = r }
    END { if (n > 0 && !bad && min > 0 && min <= 400) print min }')
case "$HCR" in
    ''|*[!0-9]*) echo "Host corner radius: not read ($(printf '%s\n' "$HLINE" | grep -c .) internal panels)" ;;
    *) echo "$HCR" > "$STAGE/host_corner_radius"
       echo "Host corner radius: $HCR px (the smallest of $(printf '%s\n' "$HLINE" | grep -c .) internal panels)" ;;
esac
# One UI's scale, for the guest's density (UI activator; standing rule: right on
# every phone and image): the density One UI runs its main panel at (Screen zoom
# included) and the width it runs it at. An Ultra's One UI runs its 1440 px panel
# at FHD+ (1080) with the shared ro.sf.lcd_density 450 (384 dp wide); the guest
# always runs the whole panel, so at that density it was 512 dp wide, a third too
# small (S24/S25 Ultra reports), and One UI's cutout spec (@dp) missed the camera.
# The main panel is the largest internal one: a bar phone's only panel, a flip's
# inner one. Recorded only while it is One UI's display 0 (wm size, wm density),
# so a flip switched shut leaves the guest at the base density.
rm -f "$STAGE/host_display"
MLINE=$(printf '%s\n' "$HLINE" | while IFS= read -r l; do
            s=$(echo "$l" | sed -n 's/.*uniqueId="local:[0-9]*", \([0-9]*\) x \([0-9]*\), .*/\1 \2/p')
            [ -n "$s" ] && echo "$(echo "$s" | awk '{ print $1 * $2 }') $l"
        done | sort -n | tail -n 1 | cut -d' ' -f2-)
MW=$(printf '%s\n' "$MLINE" | sed -n 's/.*uniqueId="local:[0-9]*", \([0-9]*\) x [0-9]*, .*/\1/p')
MDW=$(printf '%s\n' "$MLINE" | sed -n 's/.*CutoutPathParserInfo{displayWidth=\([0-9]*\) displayHeight=[0-9]* physicalDisplayWidth=\([0-9]*\) .*/\1/p')
MPW=$(printf '%s\n' "$MLINE" | sed -n 's/.*CutoutPathParserInfo{displayWidth=\([0-9]*\) displayHeight=[0-9]* physicalDisplayWidth=\([0-9]*\) .*/\2/p')
# A panel without a cutout: One UI runs it at the size it reports.
[ -n "$MDW" ] || MDW=$MW
[ -n "$MPW" ] || MPW=$MW
# The main panel's full size in pixels, for guest_prepare.sh (the stable display
# size of an image made for another panel, 0.4.81).
MPH=$(printf '%s\n' "$MLINE" | sed -n 's/.*physicalDisplayWidth=[0-9]* physicalDisplayHeight=\([0-9]*\) .*/\1/p')
[ -n "$MPH" ] || MPH=$(printf '%s\n' "$MLINE" | sed -n 's/.*uniqueId="local:[0-9]*", [0-9]* x \([0-9]*\), .*/\1/p')
rm -f "$STAGE/host_panel_size"
case "$MPW:$MPH" in *[!0-9:]*|:*|*:) ;; *) [ "$MPW" -ge 320 ] && [ "$MPH" -ge 320 ] && echo "$MPW $MPH" > "$STAGE/host_panel_size" ;; esac
H0W=$(timeout 10 wm size 2>/dev/null | sed -n 's/^Physical size: \([0-9]*\)x[0-9]*$/\1/p' | head -n 1)
HWD=$(timeout 10 wm density 2>/dev/null)
HUD=$(printf '%s\n' "$HWD" | sed -n 's/^Override density: \([0-9]*\)$/\1/p' | head -n 1)
[ -n "$HUD" ] || HUD=$(printf '%s\n' "$HWD" | sed -n 's/^Physical density: \([0-9]*\)$/\1/p' | head -n 1)
case "$HUD:$MDW:$MPW:$H0W" in
    *[!0-9:]*|:*|*::*|*:) echo "Host display scale: not read (density '${HUD}', width '${MDW}' of '${MPW}' px, display 0 '${H0W}' px)" ;;
    *) if [ "$H0W" != "$MPW" ] && [ "$H0W" != "$MDW" ] && [ "$H0W" != "$MW" ]; then
           echo "Host display scale: One UI's display 0 ($H0W px) is not the main panel ($MPW px), not recorded"
       elif [ "$HUD" -gt 0 ] && [ "$MDW" -gt 0 ]; then
           echo "density=$HUD width=$MDW physical=$MPW" > "$STAGE/host_display"
           echo "Host display scale: density $HUD at $MDW of the $MPW px main panel ($((MDW * 160 / HUD)) dp wide)"
       fi ;;
esac
# The cover panel of a fold, for guest_prepare.sh (ColorOS cover density): the
# smaller of the two default-capable internal displays, as
# "<uniqueId> <port> <width> <height> <xdpi>". The guest's SurfaceFlinger
# gives the panels the same ids (local:<id>) and ports as One UI's.
rm -f "$STAGE/host_cover_display"
if [ "${ONEOS_GUEST_FORM:-fold}" = fold ]; then
    # One record per panel (a dump may list a panel more than once).
    CVDS=$(printf '%s\n' "$HLINE" | while IFS= read -r l; do
        u=$(echo "$l" | sed -n 's/.*uniqueId="\(local:[0-9]*\)", \([0-9]*\) x \([0-9]*\), .*/\1 \2 \3/p')
        p=$(echo "$l" | sed -n 's/.*address [A-Za-z]*{[^}]*port=\([0-9]*\)[,}].*/\1/p')
        x=$(echo "$l" | sed -n 's/.*, density [0-9]*, \([0-9]*\)[.0-9]* x [.0-9]* dpi.*/\1/p')
        set -- $u
        [ -n "$3" ] && [ -n "$p" ] && [ -n "$x" ] && echo "$(($2 * $3)) $1 $p $2 $3 $x"
    done | sort -u)
    CVD=""
    [ "$(printf '%s\n' "$CVDS" | awk 'NF { print $2 }' | sort -u | wc -l)" = 2 ] &&
        CVD=$(printf '%s\n' "$CVDS" | sort -n | head -n 1 | cut -d' ' -f2-)
    if [ "$(echo "$CVD" | wc -w)" = 5 ]; then
        echo "$CVD" > "$STAGE/host_cover_display" && echo "Host cover display: $CVD"
    else
        echo "Host cover display: not read"
    fi
fi
# One UI's screen mode (Vivid) is a vendor render intent its composer applies
# (F8U: DisplayRenderIntent 258, renderIntent=0x102 on both panels); a guest's
# own SurfaceFlinger asks for COLORIMETRIC and every panel looked dull (0.4.38,
# ColorOS cover screen). The UI activator asks the guest's for the same one.
# Read here, while One UI's surfaceflinger still runs (never after [4b/6]).
rm -f "$STAGE/host_render_intent"
HRI=$(timeout 5 dumpsys SurfaceFlinger 2>/dev/null | sed -n 's/^DisplayRenderIntent: \([0-9][0-9]*\)$/\1/p' | head -n 1)
if [ -n "$HRI" ] && [ "$HRI" -ge 256 ] 2>/dev/null && [ "$HRI" -le 65535 ]; then
    echo "$HRI" > "$STAGE/host_render_intent" && echo "Host render intent: $HRI (One UI's screen mode, a vendor intent)"
else
    echo "Host render intent: ${HRI:-not read} (not a vendor intent; the guest keeps its own)"
fi
# One UI's color mode (F8U: SRGB, 7, on both panels, whatever is on screen). A
# Pixel guest's SurfaceFlinger moved the panels between SRGB and DISPLAY_P3
# every second or so while the camera or a photo was on screen (session
# 9455098f: 22 switches in 20 s; a visible flash each time). guest_props.sh
# and the UI activator keep the guest on One UI's mode (persist.sys.sf.color_mode,
# the composition color mode of transaction 1023).
rm -f "$STAGE/host_color_mode"
HCM=$(timeout 5 dumpsys SurfaceFlinger 2>/dev/null | sed -n 's/^ *Current color mode: ColorMode::[A-Z0-9_]* (\([0-9][0-9]*\))$/\1/p' | head -n 1)
case "$HCM" in
    [1-9]|[1-9][0-9]) echo "$HCM" > "$STAGE/host_color_mode" && echo "Host color mode: $HCM (the guest keeps it)" ;;
    *) echo "Host color mode: ${HCM:-not read} (the guest picks its own)" ;;
esac
# One UI's staged installs (Google Play system updates): 0.4.39 test2 returned in
# place with a train pending, and One UI's own system_server rebooted 5 s after
# it started ("Rollback staged install"). Logged for the next such return.
STG=$(timeout 10 pm list staged-sessions 2>/dev/null | grep -c 'sessionId')
[ "${STG:-0}" -gt 0 ] && echo "One UI has $STG staged install session(s): $(timeout 10 pm list staged-sessions 2>/dev/null | sed -n 's/.*appPackageName = \([^;]*\); isStaged = true; isReady = \([a-z]*\); isApplied = \([a-z]*\).*/\1(ready \2, applied \3)/p' | tr '\n' ' ')"
# KernelSU's manager inside the guest (0.4.39): the kernel knows the manager by
# the app id One UI gave it, so the guest's package manager gives the same
# package that id (patches/guest_ksu_manager_appid.py reads these two props) and
# the UI activator installs One UI's own copy of the app. Only a KernelSU manager
# (its kernel checks the uid) with an id below 15000 (no guest app has one).
# Off by default since 0.4.39 (owner): root grants for guest apps and Zygisk are
# not done yet; ONEOS_GUEST_KSU_MANAGER=1 turns it on. Off, nothing is staged and
# the UI activator removes a manager an earlier session installed in the guest.
setprop oneos.ksu.mgr_pkg "" 2>/dev/null
setprop oneos.ksu.mgr_appid "" 2>/dev/null
KSU_DIR="$STAGE/data/oneos_ksu"
rm -f "$KSU_DIR/manager" "$KSU_DIR/manager.apk" 2>/dev/null
if [ -x /data/adb/ksud ] && [ "${ONEOS_GUEST_KSU_MANAGER:-0}" = 1 ]; then
    KSU_PKG="" KSU_ID=""
    for p in me.weishu.kernelsu com.rifsxd.ksunext com.sukisu.ultra app.kitsusu.manager; do
        u=$(awk -v p="$p" '$1 == p { print $2 }' /data/system/packages.list 2>/dev/null)
        [ -n "$u" ] && { KSU_PKG=$p KSU_ID=$u; break; }
    done
    KSU_APK=$(timeout 10 pm path "$KSU_PKG" 2>/dev/null | sed -n 's/^package://p' | grep '/base\.apk$' | head -n 1)
    case "$KSU_ID" in
        1[0-4][0-9][0-9][0-9]) ;;
        *) KSU_ID="" ;;
    esac
    if [ -n "$KSU_PKG" ] && [ -n "$KSU_ID" ] && [ -f "$KSU_APK" ] && mkdir -p "$KSU_DIR" &&
       cp -f "$KSU_APK" "$KSU_DIR/manager.apk.new" && mv -f "$KSU_DIR/manager.apk.new" "$KSU_DIR/manager.apk"; then
        chmod 755 "$KSU_DIR"; chmod 644 "$KSU_DIR/manager.apk"
        echo "$KSU_PKG $KSU_ID" > "$KSU_DIR/manager"
        setprop oneos.ksu.mgr_pkg "$KSU_PKG"
        setprop oneos.ksu.mgr_appid "$KSU_ID"
        echo "KernelSU manager for the guest: $KSU_PKG, One UI's app id $KSU_ID ($(stat -c %s "$KSU_DIR/manager.apk") bytes staged)"
    else
        rm -f "$KSU_DIR/manager" "$KSU_DIR/manager.apk"
        echo "KernelSU manager for the guest: none (package '${KSU_PKG:-none}', app id '${KSU_ID:-none}', apk '${KSU_APK:-none}')"
    fi
fi

# What a return without a reboot compares against (return_to_oneui.sh): One
# UI's APEX devices, props, SELinux mode and the servicemanager names it keeps,
# recorded while One UI is still whole. Read only; without it the return reboots.
/system/bin/sh "$STAGE/return_to_oneui.sh" baseline
STAGE="$STAGE" /system/bin/sh "$STAGE/guest_runtime.sh" baseline || {
    echo 'Guest root baseline failed before stopping One UI; switch cancelled'
    exit 3
}

# Full logcat of the session (host and guest share logd) for pull-run-logs.sh.
# Started here so no session runs without it: run 31 was launched without the
# separate capture, and the reboot back to One UI emptied the buffers. A
# capture that is already running (started by hand) is kept; otherwise the
# previous session's files move to oneos_logs.prev. ONEOS_LOGCAT=0 skips it.
# Size (run 44): 24 rotated files of 32 MiB and the current one, 800 MiB at
# most (the app's free-space gate counts 1 GiB for logs). Run 44 wrote 56 MiB
# in 8 minutes after a 45 MiB dump of One UI's history: about 1.7 h at its
# average rate, 1 h at its peak; with 11 x 20 MiB the rotation would have
# started dropping the oldest files (One UI's history, then the switch and the
# guest's boot) after about 26 minutes. The watcher's 90 s round also keeps
# the files of the boot in $LOGS/head (hard links, below).
LOGS=/data/local/tmp/oneos_logs
# LOGCAT_HEAD=1 only for a capture this session starts: a capture already
# running (by hand, or the last session's within the 120 s before
# return_to_oneui.sh stops it) keeps its head/, which may hold the boot of an
# earlier session that its rotation has dropped since.
LOGCAT_HEAD=0
if [ "${ONEOS_LOGCAT:-1}" = 1 ]; then
    # pgrep -f matches the same "^logcat ... boot.log" command line in one
    # process. The loop it replaces forked tr and grep for each of ~1100 pids:
    # 1.6 s with One UI idle (measured 22 Oct, pgrep 49 ms), and it runs before
    # the gap splash below, which in run 33 reached ActivityTaskManager 6 s
    # after the switch started (adbd 14:40:51.03, START 14:40:57.03).
    lp=$(pgrep -f "^logcat .*$LOGS/boot.log" 2>/dev/null | head -1)
    if [ -n "$lp" ]; then
        # The last return stops its capture two minutes after One UI is up
        # (return_to_oneui.sh) unless its token is gone: this session keeps it.
        rm -f "$LOGS/logcat.stop"
        echo "Logcat capture already running (pid $lp): kept, its head/ left as it is"
    else
        rm -rf "$LOGS.prev"; [ -d "$LOGS" ] && mv "$LOGS" "$LOGS.prev"
        mkdir -p "$LOGS"
        $BB setsid logcat -b all -v threadtime -f "$LOGS/boot.log" -r 32768 -n 24 </dev/null >/dev/null 2>&1 &
        LOGCAT_HEAD=1
        echo "Logcat capture: $LOGS/boot.log"
    fi
fi
# Sound and vibration watch (0.4.58): rings, vibrations, audio effects and
# crashes of the session in a small log of its own ($STAGE/sound_watch.log,
# collected with the other stage logs). The capture above keeps the start and
# the end of a session; the rings in the middle of report 4933a41d ("the
# vibration style for call is not strong": rings at 12:51 and 13:07 of a
# 12:29-13:24 session) and the notification tone crash of report
# findingssms918b20261104 were in no report. Tags only, 2 MiB at most; it ends
# itself after two hours (no process walk at the return), and the next
# session ends an earlier one by its pid. ONEOS_LOGCAT=0 skips it.
# 0.4.74: also the audio HAL's, AudioFlinger's, the policy manager's and the
# Bluetooth A2DP stack's warnings and errors. Media "bad", Bluetooth connected
# without sound and a game's endless static (A56 da7379d6, M55s 0e73a8d6) all
# fell in the gap between the capture's head and its end (A56: 13:48-15:35);
# this log had the whole A56 session but none of those tags.
if [ "${ONEOS_LOGCAT:-1}" = 1 ]; then
    swp=$(cat "$STAGE/sound_watch.pid" 2>/dev/null)
    case "$swp" in
        ""|*[!0-9]*) ;;
        *) tr '\0' ' ' < "/proc/$swp/cmdline" 2>/dev/null | grep -q "sound_watch.log" && kill "$swp" 2>/dev/null ;;
    esac
    [ -f "$STAGE/sound_watch.log" ] && mv -f "$STAGE/sound_watch.log" "$STAGE/sound_watch.prev"
    $BB setsid $BB timeout 7200 logcat -b main,system,crash -v threadtime -f "$STAGE/sound_watch.log" -r 2048 -n 1 -s \
        AndroidRuntime:E DEBUG:F Telecom:I Telecom_INCOMING_RINGING:V Ringtone:V RingtoneManager:V \
        VibratorManagerService:V VibratorManagerServiceExtImpl:V VibrationThread:V VibrationScaler:V \
        SecVibrator-HAL-AIDL-CORE:V AHAL_StreamOut_QTI:D EffectOffloadImpl:V AHAL_EffectFactoryQti:V \
        AHAL_DlbSpatializerEffectImpl:V DlbDap2Process:V \
        AudioFlinger:W APM_AudioPolicyManager:W AHAL:W AHAL_ModulePrimary:W AHAL_StreamPrimary_exynos:W \
        audio_hw_primary:W audio_hw_proxy2:E bluetooth-a2dp:W A2dpStateMachine:I A2dpService:I \
        BTAudioProviderStub_2_1:I BTAudioProviderA2dpSoftware:W </dev/null >/dev/null 2>&1 &
    echo $! > "$STAGE/sound_watch.pid"
    echo "Sound watch: $STAGE/sound_watch.log"
fi
# Play Store and Google sign-in watch: no longer live. Test builds 3 to 6 ran
# a logcat -e watch here (store_watch.log); its regex runs on every line of the
# main, system and crash buffers, and it took 65% of a core all session and two
# hours after it (measured in One UI after a Pixel session, 11-06; owner: "the
# device gets super hot" on Pixel, which logs the most). The return now takes
# the same lines from the session's capture once, at the lowest priority
# (return_to_oneui.sh). A watch an earlier session left running ends here,
# and so does that extraction while it still waits (0.4.74: its grep took a
# core for the whole next session, S26 2f97ffa9, S22 Ultra acd15d4c).
stp=$(cat "$STAGE/store_watch.pid" 2>/dev/null)
case "$stp" in
    ""|*[!0-9]*) ;;
    *) tr '\0' ' ' < "/proc/$stp/cmdline" 2>/dev/null | grep -q "store_watch.log" && kill "$stp" 2>/dev/null ;;
esac
rm -f "$STAGE/store_watch.pid"
# Charging (charge_watch.log, collected with the other stage logs): one line a
# minute with the charger's own view, whichever system runs. Samsung's direct
# charger (super fast charging, PPS) is chosen by the kernel and the charger IC,
# not by the framework; direct_charging_status=1 and the current show it is on
# (the owner asked whether Pixel charges at 45 W). Read-only sysfs reads; two
# hours at most like the other watches, and the next session ends an earlier one.
CHB=/sys/class/power_supply/battery
if [ -r "$CHB/current_now" ]; then
    chp=$(cat "$STAGE/charge_watch.pid" 2>/dev/null)
    case "$chp" in
        ""|*[!0-9]*) ;;
        *) tr '\0' ' ' < "/proc/$chp/cmdline" 2>/dev/null | grep -q "charge_watch" && kill "$chp" 2>/dev/null ;;
    esac
    CHB="$CHB" $BB setsid $BB timeout 7200 $BB sh -c '
        echo "=== $(date "+%F %T") session (charge_watch): status charging_type direct current(mA) voltage(mV) temp"
        while :; do
            st=$(cat "$CHB/status" 2>/dev/null); ty=$(cat "$CHB/charging_type" 2>/dev/null)
            dc=$(cat "$CHB/direct_charging_status" 2>/dev/null); cu=$(cat "$CHB/current_now" 2>/dev/null)
            vo=$(cat "$CHB/voltage_now" 2>/dev/null); te=$(cat "$CHB/temp" 2>/dev/null)
            echo "$(date +%T) $st ${ty:-?} direct=${dc:-?} $(( ${cu:-0} / 1000 )) $(( ${vo:-0} / 1000 )) ${te:-?}"
            sleep 60
        done' charge_watch </dev/null >> "$STAGE/charge_watch.log" 2>&1 &
    echo $! > "$STAGE/charge_watch.pid"
    echo "Charge watch: $STAGE/charge_watch.log"
fi

# --- GAP SPLASH ---
# A still OneOS screen for the black gap at the start of the switch. Run 32
# (all.log): One UI's surfaceflinger was killed in [4b/6] at 13:09:24.55 (the
# composer destroyed its client and blanked the panel: NullCommit) and the
# guest's ColorOS boot animation drew its first frame at 13:09:56.18, so 31.6 s
# of black, 23 s of it guest_prepare.sh. Samsung's bootanimation only plays
# QMG files, and nothing of the guest can draw before its own SurfaceFlinger
# runs. So a splash activity (the OneOS app's GapSplashActivity, before that
# the switcher's SplashActivity; $SPLASH_COMPONENT, see the preflight) puts the
# OneOS wordmark on screen while One UI still runs, and [4b/6] freezes One
# UI's surfaceflinger (SIGSTOP) on that frame instead of killing it: its
# composer client stays, so nothing presents or blanks the panel.
# guest_start.sh kills it right before it restarts the composer (run 32: ~4 s
# before ColorOS's animation, which is unchanged). Started here in the
# background so the switch does not wait for it; [4b/6] waits 3 s at most and
# kills surfaceflinger as before when the splash is not up (no 'Status: ok'
# from am start, e.g. the component is not installed).
# ONEOS_GAP_SPLASH=0: the black gap of run 32.
. "$STAGE/boot_status.sh"
GAP_SPLASH_LOG="$STAGE/gap_splash.log"
rm -f "$GAP_SPLASH_LOG" "$STAGE/data/oneos_host_sf_frozen"
if [ "${ONEOS_GAP_SPLASH:-1}" = 1 ]; then
    # settled = 0.6 s after the first frame, once the system bars slid out.
    # The times (inner shell's date) date the splash against the switch: run
    # 33's log had none, and its splash came 6 s after the switch started.
    /system/bin/sh -c "echo start \$(date +%T.%N); am start -W --activity-no-animation -n $SPLASH_COMPONENT; sleep 0.6; echo settled \$(date +%T.%N)" </dev/null >"$GAP_SPLASH_LOG" 2>&1 &
fi

# Put SELinux in permissive mode for the duration of the takeover. The guest
# userspace is a foreign, unlabelled-for-this-policy userspace: its
# system_server runs as u:r:system_server:s0 against Samsung's policy, and MAC
# denials there surface as confusing EACCES/ENOENT deep inside system_server
# (e.g. settings.db "doesn't exist", users/0.xml EACCES). guest_prepare.sh
# relabels the staged /data properly, but permissive is the safety net that
# keeps the rest of the guest boot from tripping over labels we cannot predict.
# return_to_oneui.sh restores enforcing.
setenforce 0 2>/dev/null || true
echo "SELinux mode: $(getenforce 2>/dev/null || echo unknown)"
oneos_boot_begin enter

# --- IMS / SMS REGISTRATION GATE -----------------------------------------
# The guest has no ImsService of its own, so the modem's IMS registration is
# owned by One UI's imsd and survives the takeover. That registration is what
# makes SMS behave: with it, T-Mobile delivers inbound SMS promptly (Samsung's
# RIL hands SMSoIP messages to the framework as normal SMS) and the modem
# accepts mobile-originated SMS. Without it, voice sits OUT_OF_SERVICE, sends
# fail with RESULT_ERROR_NO_SERVICE and inbound codes fall back to the SMSC
# retry schedule, arriving 20-40 minutes late - and every radio nudge then
# appears to "magically" deliver them.
# So: make sure imsd is up, and give the modem a moment to (re)register before
# the pivot. Never stop imsd afterwards; killing it was what degraded SMS.
if ! pidof imsd >/dev/null 2>&1; then
    setprop ctl.start imsd 2>/dev/null || true
fi
ims_i=0
ims_st=1
while [ "$ims_i" -lt 45 ]; do
    if dumpsys telephony.registry 2>/dev/null | grep -q 'mVoiceRegState=0'; then
        ims_st=0
        break
    fi
    ims_i=$((ims_i + 1))
    sleep 2
done
echo "IMS gate: voiceRegState=$ims_st after $((ims_i * 2))s, imsd=${ims_pid:-$(pidof imsd)}"

# --- ADB WATCHDOG ---------------------------------------------------------
# adb is the only way into the phone while the guest is up (until wifi is
# configured), and the host adbd occasionally dies or loses the adb function
# when the container's system_server touches the USB configuration. init does
# not reliably restart it, which is the "adb randomly stopped working" symptom.
# Keep it supervised from the host namespace for the whole session; the watchdog
# is stopped again by return_to_oneui.sh.
# OneOS: only when One UI has USB debugging on (read while its framework still
# runs). A phone without it gets no adb watchdog, and guest_prepare.sh then
# neither copies the host's adb_keys into the guest nor turns the guest's
# adb_enabled on ($STAGE/host_adb_on).
case "$(settings get global adb_enabled 2>/dev/null)" in
    1) HOST_ADB=1 ;;
    *) case "$(getprop persist.sys.usb.config)" in *adb*) HOST_ADB=1 ;; *) HOST_ADB=0 ;; esac ;;
esac
echo "$HOST_ADB" > "$STAGE/host_adb_on"
echo "Host USB debugging: $([ "$HOST_ADB" = 1 ] && echo on || echo off)"
if [ "$HOST_ADB" = 1 ] && ! ps -ef 2>/dev/null | grep -v grep | grep -q "adb_watchdog.sh"; then
    cat > /data/local/tmp/adb_watchdog.sh <<'ADBW'
#!/system/bin/sh
# Watchdog for the host adbd, which is the only way into the phone while the guest
# is up. Two failure modes are handled:
#   1. adbd simply died -> ask init to start it again.
#   2. adbd is alive but the USB gadget lost the adb function. The guest's own
#      UsbService rewrites sys.usb.config during boot, and a plain setprop is a
#      no-op in that state, so the gadget has to be re-applied by toggling it.
LOG=/data/local/tmp/adb_watchdog.log
last_toggle=0
while true; do
    sleep 10
    st=$(getprop init.svc.adbd)
    usb=$(getprop sys.usb.state)
    cfg=$(getprop sys.usb.config)
    if [ "$st" != "running" ]; then
        setprop ctl.start adbd 2>/dev/null
        echo "$(date) restarted adbd (was: $st, usb.state=$usb, usb.config=$cfg)" >> "$LOG"
    fi
    case "$cfg" in
        *adb*) ;;
        *)
            setprop sys.usb.config "$cfg,adb" 2>/dev/null
            echo "$(date) added adb to usb.config (was: $cfg)" >> "$LOG"
            ;;
    esac
    case "$usb" in
        *adb*) ;;
        "")
            ;;
        *)
            now=$(date +%s 2>/dev/null || echo 0)
            if [ $((now - last_toggle)) -gt 300 ]; then
                last_toggle=$now
                echo "$(date) gadget lost adb, toggling (state: $usb, config: $cfg)" >> "$LOG"
                setprop sys.usb.config none 2>/dev/null
                sleep 1
                setprop sys.usb.config rndis,adb 2>/dev/null
                sleep 2
                setprop ctl.start adbd 2>/dev/null
            fi
            ;;
    esac
done
ADBW
    chmod 755 /data/local/tmp/adb_watchdog.sh
    if command -v setsid >/dev/null 2>&1; then
        setsid /system/bin/sh /data/local/tmp/adb_watchdog.sh </dev/null >/dev/null 2>&1 &
    else
        nohup /system/bin/sh /data/local/tmp/adb_watchdog.sh </dev/null >/dev/null 2>&1 &
    fi
    echo "adbd watchdog started (log: /data/local/tmp/adb_watchdog.log)"
fi

# --- IMS KEEPALIVE --------------------------------------------------------
# imsd is the daemon holding the modem's IMS registration (see the IMS gate
# above). init does not always bring it back if it dies, and a dead imsd means
# SMS quietly degrades to "arrives whenever the SMSC next retries", so keep it
# supervised for the whole guest session.
if ! ps -ef 2>/dev/null | grep -v grep | grep -q "ims_watchdog.sh"; then
    cat > /data/local/tmp/ims_watchdog.sh <<'IMSW'
#!/system/bin/sh
LOG=/data/local/tmp/ims_watchdog.log
while true; do
    sleep 60
    if ! pidof imsd >/dev/null 2>&1; then
        setprop ctl.start imsd 2>/dev/null
        echo "$(date) restarted imsd (was missing)" >> "$LOG"
    fi
done
IMSW
    chmod 755 /data/local/tmp/ims_watchdog.sh
    if command -v setsid >/dev/null 2>&1; then
        setsid /system/bin/sh /data/local/tmp/ims_watchdog.sh </dev/null >/dev/null 2>&1 &
    else
        nohup /system/bin/sh /data/local/tmp/ims_watchdog.sh </dev/null >/dev/null 2>&1 &
    fi
    echo "imsd keepalive started (log: /data/local/tmp/ims_watchdog.log)"
fi

# Set permissive privapp permissions to avoid Signature|privileged fatal exceptions
set_prop ro.control_privapp_permissions log

# --- ONEUI PROTECTION & RESCUEPARTY DISABLE ---
echo "=== [1/6] $(date +%T) Protecting OneUI Home Screen and Disabling RescueParty ==="
set_prop persist.sys.disable_rescue true
set_prop sys.rescue_boot_count 0
# Android 16+ counts boots for its boot-loop check in crashrecovery.* (0.4.47): the guest's
# system_server starts from 0 too. The property area is One UI's, so the return puts these back.
set_prop crashrecovery.rescue_boot_count 0
[ "$(getprop persist.sys.disable_rescue)" = true ] ||
    echo "!!! persist.sys.disable_rescue did not take (property space: $(pa_free "$PA_FILE") bytes left); guest_start.sh will not start the guest"
# OneOS: no snapshot of One UI Home's databases any more. OneLineage copied
# them to /data/local/tmp/lineage_backups here and back over the live ones on
# the way back: the only intended write into One UI's app data, never emptied.

# --- AUDIO LOW LATENCY TUNING ---
# Deep buffer must stay OFF. Tested live: with audio.deep_buffer.media=true the
# deep-buffer output opens but never consumes, and an AudioTrack write blocks
# forever (app_process hung in futex_wait). The 20 ms normal path is the one
# that actually works; a streamed tone on it is clean (0 underruns, 0 late
# writes). Offload stays off: no working vendor DSP session in the container.
echo "=== [2/6] $(date +%T) Configuring Low-Latency Audio ==="
set_prop audio.offload.disable 1
set_prop audio.deep_buffer.media false
set_prop audio.offload.video false
set_prop vendor.audio.offload.track.enable false

# --- NETWORK BPF FIREWALL & DNS BYPASS ---
echo "=== [3/6] $(date +%T) Configuring Network BPF Filters ==="
bpftool map update pinned /sys/fs/bpf/netd_shared/map_netd_configuration_map key hex 00 00 00 00 value hex 00 00 00 00 2>/dev/null || true
chmod 666 /dev/socket/dnsproxyd 2>/dev/null || true

# --- VERIFY STAGING ENVIRONMENT ---
echo "=== [4/6] $(date +%T) Verifying Staging Environment ==="
# system.raw and the staged files were checked in the preflight, before the
# first change to the phone.
mkdir -p "$STAGE/data"
# OneOS: the staged scripts are the ones scripts/deploy-phone.sh pushed. They are
# no longer replaced by the switcher app's bundled copies, which can be older
# (an older APK would bring back scripts without the storage protections).
chmod 755 "$STAGE"/*.sh "$STAGE/zygote_exec" 2>/dev/null || true
# A namespace id left by a session that never returned (phone rebooted) must
# not make a failed switch's return kill whatever owns that id now.
rm -f "$STAGE/guest_mntns" "$STAGE/guest_rootdev"
# The return-key readers are armed last (below). Clear any set left by an
# earlier boot now, before any early return (a dry run, a guest_prepare
# failure): return_to_oneui.sh kills the PIDs listed there, which after a
# reboot are recycled and belong to other processes (run: a stale pids file
# signalled vold/apexd or the return script itself).
# A reader a return did not stop (its shell acts on SIGTERM only after getevent
# ends) ends by itself on its next key event, once the session file below is
# not its own. Never walked or killed from here: 0.4.38's pgrep cleanup at this
# spot hung the switch behind the splash (and in the return, behind the frozen
# composer).
rm -rf "$STAGE/return_keys"

# OneOS: ColorOS components (the launcher among them) only log their info and
# debug lines with this set. guest_props.sh restore-persist removes it again on
# return (it is added after the persist snapshot).
setprop persist.sys.assert.panic true 2>/dev/null
# An app that crashes three times is moved to OPPO's zygote_ocomp, which nothing
# starts in the container: system_server then polled its socket for 62 s and no
# app could start (run 28, black home). oplus_boot_hangs.py blocks it as well.
setprop persist.sys.oplus.aotcrash_controller_enabled false 2>/dev/null
# The guest's own language, saved on the last return (guest_props.sh). The
# property is shared: One UI's value comes back with restore-persist. Only a
# language tag (en-US, zh-Hans-CN): the file may come from an older stage.
# Without one (a fresh stage): One UI's current language, its system_locales.
# persist.sys.locale is only One UI's boot default and can differ: run 41 got
# another language (the guest booted in it) while One UI showed en-GB,en-US. One UI's
# framework still runs here, so settings answers.
GL=$(head -n 1 "$STAGE/guest_locale" 2>/dev/null) GLW="saved guest locale"
case "$GL" in
    ''|-*|*[!A-Za-z0-9-]*) [ -n "$GL" ] && echo "Guest locale '$GL' in $STAGE/guest_locale is not a language tag; not used"; GL="" ;;
esac
if [ -z "$GL" ]; then
    GL=$(settings get system system_locales 2>/dev/null | head -n 1 | cut -d, -f1) GLW="One UI's language"
    case "$GL" in ''|null|-*|*[!A-Za-z0-9-]*) GL="" ;; esac
fi
if [ -n "$GL" ] && [ ${#GL} -le 35 ] && setprop persist.sys.locale "$GL" 2>/dev/null; then
    echo "Guest locale: $GL ($GLW)"
else
    echo "Guest locale: left at $(getprop persist.sys.locale) (no saved guest locale, One UI's language not readable)"
fi

# --- STOP THE HOST FRAMEWORK ---
# OneOS: before guest_prepare.sh, not after it. guest_prepare bind-mounts the
# guest's trees over the host's /data/app, /data/user, /data/user_de, ...; with
# One UI still running, its apps suddenly could not load their own APKs
# (1.2 million "ResourcesManager: failed to preload asset path" lines in a
# minute) and One UI's PackageManager saw its packages vanish.
# OneOS: silence the guest-session log storms (~30k lines/s in run 23: the
# host audioserver's "protected data in Parcel", the guest's CaptureStateTracker
# "Audio policy service died" retry spin, ResourcesManager). They pushed the
# SurfaceFlinger failures out of every tail-based check and can make logd drop
# lines. log.tag.* is not persistent; return_to_oneui.sh clears them.
# Run 32 (about 36k of 787k lines in the last 10 min, all from OPPO HALs and
# kernel nodes this phone does not have): PerformanceManager and ProjectManager
# log a full NullPointerException stack per call (1083 and 250 calls, on
# WindowManager and power key paths), SchedAssist "mSharedBinderUxFd=-1 is
# invalid" per binder call, GestureLog_OplusPenGestureManager per touch event,
# HoraeHelper "Cannot connect to HoraeService", OsenseResManagerService and
# OLC's postman "heap ... too small".
# Run 34 (678k lines in the 880 s after boot; the tags above logged 0): the
# guest system_server's UserAwareMgr logs every OPPO resource request and
# release (8684 lines, about 10/s; its urcc HAL is not declared here), and
# OplusUIFirst_TS "Failed to connect bpf bin" (396).
for t in CaptureStateTracker libbinder.Parcel Parcel ResourcesManager MediaCodecList AString BOOTPROF GED \
         PerformanceManager ProjectManager SchedAssist GestureLog_OplusPenGestureManager HoraeHelper OsenseResManagerService postman \
         UserAwareMgr OplusUIFirst_TS; do
    setprop "log.tag.$t" SILENT 2>/dev/null
done

# Wifi handover, recorded while One UI still runs. The guest's WifiService gets
# the supplicant (ISupplicant/default) from the shared servicemanager, which
# asks this init to start it; One UI's supplicant quits as soon as One UI's
# framework stops ("Client died. Terminating..."). The UI activator turns the
# guest's Wi-Fi on if One UI had it on. (Never print supplicant configs.)
case "$(settings get global wifi_on 2>/dev/null)" in 1|2) echo 1 ;; *) echo 0 ;; esac > "$STAGE/host_wifi_on"

# One UI's mobile data switch, for guest_prepare.sh (guest mobile data): it
# can only be read while One UI's framework runs.
HMD=$(settings get global mobile_data 2>/dev/null)
case "$HMD" in 0|1) echo "$HMD" ;; *) echo "" ;; esac > "$STAGE/host_mobile_data"
# One UI's preferred (attach) APN per SIM slot, for guest_prepare.sh (guest
# attach APN, a Pixel guest only: guards.txt without oplus-services_patched.jar).
# Runs 41 and 42: SIM 2 attached with the carrier's web1 in the guest and fell to 3G;
# One UI uses web2. Read only, from One UI's telephony provider (root's content
# queries): one "slot mcc mnc apn" line per SIM that has one, nothing when the
# provider gives no answer (the guest then keeps its own). ONEOS_GUEST_APN=0
# skips it.
rm -f "$STAGE/host_pref_apn"
if [ "${ONEOS_GUEST_APN:-1}" = 1 ] && ! grep -q ' oplus-services_patched.jar$' "$STAGE/guards.txt" 2>/dev/null; then
    # <row> <column>: the value of one column in a "Row: N a=1, b=2" line.
    row_val() { printf '%s\n' "$1" | tr ',' '\n' | sed -n "s/^ *\(Row: [0-9]* \)\{0,1\}$2=//p" | head -n 1; }
    timeout 10 content query --uri content://telephony/siminfo --projection _id:sim_id --where "sim_id>=0" 2>/dev/null |
        grep '^Row: ' | while IFS= read -r row; do
            sub=$(row_val "$row" _id); slot=$(row_val "$row" sim_id)
            case "$sub:$slot" in *[!0-9:]*|:*|*:) continue ;; esac
            prow=$(timeout 10 content query --uri "content://telephony/carriers/preferapn/subId/$sub" --projection apn:mcc:mnc 2>/dev/null | grep -m 1 '^Row: ')
            [ -n "$prow" ] || continue
            echo "$slot $(row_val "$prow" mcc) $(row_val "$prow" mnc) $(row_val "$prow" apn)"
        done | awk 'NF == 4 && $1 ~ /^[0-7]$/ && $2 ~ /^[0-9][0-9][0-9]$/ && $3 ~ /^[0-9][0-9][0-9]?$/ &&
                    $4 ~ /^[A-Za-z0-9._-]+$/ && !seen[$1]++' > "$STAGE/host_pref_apn"
    PA=$(tr '\n' ';' < "$STAGE/host_pref_apn" | sed 's/;$//; s/;/; /g')
    echo "One UI's preferred APNs (slot mcc mnc apn): ${PA:-none read}"
fi
SUPP_SVC=$(getprop | sed -n 's/^\[init\.svc\.\([^]]*supplicant[^]]*\)\]: .*/\1/p' | grep -v mainline | head -1)
echo "$SUPP_SVC" > "$STAGE/host_supplicant_svc"
echo "Host wifi_on: $(cat "$STAGE/host_wifi_on"), supplicant service: ${SUPP_SVC:-none} ($(getprop "init.svc.$SUPP_SVC"))"

# CPU caps and heat around the stop (run 44): One UI's thermal control (SIOP,
# in its system_server) had capped both CPU clusters at 2.112 GHz a second
# before the stop, and nothing lifted that cap for the whole session. Each
# cpufreq policy's scaling_max_freq/cpuinfo_max_freq, and the skin
# temperature from the thermal service (One UI's before the stop, none after)
# and from the vendor thermal daemon's log (Samsung: "thermal_core: pivot(AP)
# : 539, skin : 436", tenths of a degree). Read only.
cpu_caps() {
    caps=""
    for p in /sys/devices/system/cpu/cpufreq/policy*; do
        [ -r "$p/scaling_max_freq" ] || continue
        caps="$caps ${p##*/} $(cat "$p/scaling_max_freq" 2>/dev/null)/$(cat "$p/cpuinfo_max_freq" 2>/dev/null)"
    done
    echo "${caps# }"
}
skin_temp() {
    ts=$(timeout 5 dumpsys thermalservice 2>/dev/null | sed -n '/^Current temperatures from HAL/,/^[^[:space:]]/p' |
        sed -n 's/.*mValue=\([-0-9.]*\), mType=[0-9]*, mName=SKIN,.*/\1/p' | head -n 1)
    tc=$(timeout 5 logcat -d -t 4000 -s thermal_core 2>/dev/null | sed -n 's/.* skin : \([0-9][0-9]*\).*/\1/p' | tail -n 1)
    if [ -n "$ts" ]; then ts="$ts C"; else ts="none"; fi
    if [ -n "$tc" ]; then tc="$((tc / 10)).$((tc % 10)) C"; else tc="none logged"; fi
    echo "thermal service $ts, thermal_core $tc"
}
STAGE="$STAGE" BB="$BB" /system/bin/sh "$STAGE/fold8_coloros.sh" performance-snapshot || refuse "Performance limit snapshot failed"
# Samsung's own CPU ceiling (cpufreq_limit/cpufreq_max_limit, SSRM's vote)
# outlives One UI's framework: a 2.2 of 3.5 GHz vote from before the switch
# held the whole HyperOS session on the S25 Ultra, and One UI after the return
# until power saving was turned on and off (0.4.34 report bdbb0509); the heat
# cap's full clock on scaling_max_freq does not lift it. The heat cap releases
# it (-1) when power saving was off here, and the return releases it again for
# One UI's new SSRM to vote afresh. Read now: settings needs the framework.
HOST_LOW_POWER=$(timeout 3 settings get global low_power 2>/dev/null)
echo "Before the stop: power saving ${HOST_LOW_POWER:-unknown}, cpufreq_max_limit $(cat /sys/devices/system/cpu/cpufreq_limit/cpufreq_max_limit 2>/dev/null || echo none)"
echo "=== [4b/6] $(date +%T) Stopping the One UI framework ==="
echo "Before the stop: CPU max/hw kHz: $(cpu_caps); skin: $(skin_temp)"
pkill -f "while true; do [ \"\$(getprop init.svc.zygote)\"" 2>/dev/null || true
pkill -f "while true; do for p in \\\$(pidof audioserver cameraserver)" 2>/dev/null || true
# Gap splash (see the top): once SplashActivity is on screen, freeze One UI's
# surfaceflinger on it before anything below removes a window (the deaths of
# system_server and the app would make it compose a frame without them). The
# pid goes to the guest's /data for guest_start.sh, and the loop below leaves
# surfaceflinger alone while that file exists.
SF_FROZEN=""
if [ "${ONEOS_GAP_SPLASH:-1}" = 1 ]; then
    n=0
    while [ $n -lt 15 ] && ! grep -q '^settled' "$GAP_SPLASH_LOG" 2>/dev/null; do n=$((n + 1)); sleep 0.2; done
    if [ "${ONEOS_VERBOSE_BOOT:-0}" = 1 ]; then
        if oneos_boot_wait_ready 5; then
            echo "Verbose boot: live renderer posted its first frame at $(date +%T)"
        else
            echo "Verbose boot: live renderer not ready after 5 s; retaining static fallback"
        fi
    fi
    SFP=$(pidof surfaceflinger)
    if grep -q '^Status: ok' "$GAP_SPLASH_LOG" 2>/dev/null && grep -q '^settled' "$GAP_SPLASH_LOG" &&
       [ -n "$SFP" ] && [ "$SFP" = "${SFP%% *}" ] && echo "$SFP" > "$STAGE/data/oneos_host_sf_frozen"; then
        if [ "${ONEOS_VERBOSE_BOOT:-0}" = 1 ] && oneos_boot_ready; then
            # Keep the compositor live for the root status layer, with the same
            # guest_start/safety-net cleanup as the ordinary frozen frame.
            SF_FROZEN=$SFP
            echo "Verbose boot: surfaceflinger $SFP kept live for status updates"
        elif kill -STOP "$SFP" 2>/dev/null; then SF_FROZEN=$SFP; else rm -f "$STAGE/data/oneos_host_sf_frozen"; fi
    fi
    if [ "${ONEOS_VERBOSE_BOOT:-0}" = 1 ] && oneos_boot_ready; then
        echo "Gap splash: live process status on surfaceflinger ${SF_FROZEN:-unavailable}"
    else
        echo "Gap splash: $(grep -E '^(Status|LaunchState|TotalTime|Error)' "$GAP_SPLASH_LOG" 2>/dev/null | tr '\n' ' ')waited $((n / 5)).$((n % 5 * 2))s; One UI's surfaceflinger ${SF_FROZEN:-not frozen, black gap}${SF_FROZEN:+ frozen on it at $(date +%T)}"
    fi
fi
setprop ctl.stop zygote
# zygote64_32 phones (Galaxy S23): One UI's 32-bit zygote is a service of its
# own, and stopping zygote leaves it running. The guest's system_server then
# asked it to preload (SecondaryZygotePreload, as the phone lists 32-bit ABIs):
# One UI's idmap2 rewrote the framework overlay idmaps in /data/resource-cache,
# the stage's through the bridge, under the guest's mapped copies, and the
# guest's system_server died in IdmapResMap::Lookup 0.4 s later, every session
# (699602d7). Stopped with zygote, kept stopped below, started on the return.
[ -n "$(getprop init.svc.zygote_secondary)" ] && setprop ctl.stop zygote_secondary
# Android 17's zygote_next (native-only processes, app zygotes) stays One UI's
# for now: the image's own, started by guest_start.sh in 0.4.25-hyperos, forked
# children that exited at once ("Failed to poll client socket: EBADF"), an app
# zygote never came up, system_server's process starts waited on it and it
# died after two minutes (HyperOS run 12, docs/hyperos.md).
[ -n "$SF_FROZEN" ] || setprop ctl.stop surfaceflinger
# audioserver/cameraserver are deliberately left running. The guest shares this
# binder namespace, and its AudioService.<init> -> AudioDeviceBroker.init ->
# AudioSystem::addAudioPortCallback waits on media.audiopolicy with no timeout:
# with no audio policy service registered, system_server's main thread hangs
# (~2 min watchdog stall, boot stuck on the animation). Freezing them with
# kill -STOP is the worst of both worlds - the binder registration survives
# while the process can never answer.
# The watchdog device One UI's system_server keeps open: Samsung's software
# watchdog, fed by its WatchdogSoftdog. Its node differs per phone (/dev/watchdog,
# /dev/softdog -> watchdog1 on the MediaTek A16 4G and A17, /dev/watchdog1 on the
# S24 Exynos, where /dev/watchdog is the kernel's and busy: 0.4.54 3bb18528
# panicked "Software Watchdog Timer expired 100s" with persist.vendor.softdog=off
# set). Recorded from its open files before it stops; closed with "V" below and
# kicked by the feeder (guest_prepare.sh) for the session.
rm -f "$STAGE/host_softdog_nodes"
for p in $(pidof system_server); do
    for fd in /proc/$p/fd/*; do
        t=$(readlink "$fd" 2>/dev/null)
        case "$t" in /dev/watchdog*|/dev/softdog*) echo "$t" ;; esac
    done
done 2>/dev/null | sort -u > "$STAGE/host_softdog_nodes"
# Not every phone's system_server holds it open at this moment: the Galaxy A17 5G
# (Exynos 1330, 0.4.64 78f6e716) recorded nothing and panicked "Software Watchdog
# Timer expired 100s" about 100 s into the session, with persist.vendor.softdog=off
# set; its nodes were /dev/watchdog 0:0 (busy, init's watchdogd), /dev/watchdog0
# 0:0 and /dev/watchdog1 0:1000. Samsung's ueventd gives its software watchdog to
# the system group for system_server; the kernel's hardware watchdog stays root's.
# So a watchdog node of group system (1000) is taken as the softdog too (0.4.66).
# Only a node beside /dev/watchdog and /dev/softdog: those two get their own "V"
# below and the feeder's every 2 s. The S23 and S25 series (Snapdragon) have
# /dev/watchdog 0:1000 itself; listing it made the 0.4.66/0.4.67 feeder exit
# after its first kick (its node loop left the counter n=/dev/watchdog), and
# ColorOS panicked "Software Watchdog Timer expired 100s" minutes later (0.4.67
# S9360 e92bad4f, S931B 96af0d7b, S938B a0b8383f). There nothing is recorded
# here again, as in 0.4.65.
for n in /dev/watchdog* /dev/softdog*; do
    case "$n" in /dev/watchdog|/dev/softdog) continue ;; esac
    [ -c "$n" ] || continue
    [ "$(stat -c %g "$n" 2>/dev/null)" = 1000 ] && echo "$n"
done 2>/dev/null >> "$STAGE/host_softdog_nodes"
sort -u -o "$STAGE/host_softdog_nodes" "$STAGE/host_softdog_nodes" 2>/dev/null
[ -s "$STAGE/host_softdog_nodes" ] || rm -f "$STAGE/host_softdog_nodes"
[ -n "$SF_FROZEN" ] || kill -9 $(pidof surfaceflinger) 2>/dev/null || true
kill -9 $(pidof bootanimation) 2>/dev/null || true
kill -9 $(pidof app_process64) 2>/dev/null || true
kill -9 $(pidof zygote_exec) 2>/dev/null || true
kill -9 $(pidof zygote64) 2>/dev/null || true
kill -9 $(pidof zygote_secondary) 2>/dev/null || true
kill -9 $(pidof system_server) 2>/dev/null || true
# Suppress the host zygote, so Samsung init does not resurrect it. OneOS: and
# the host surfaceflinger: guest_start.sh restarts the vendor composer, whose
# rc has "onrestart restart surfaceflinger", and the revived Samsung
# surfaceflinger then answered the guest's private SurfaceFlinger calls
# (ColorOS's OPlusRefreshRateConfigs got a SecurityException and took
# system_server down). init.svc.* only covers init's services, never the
# guest's own surfaceflinger. return_to_oneui.sh kills this loop by matching
# "ctl.stop zygote".
# A guest_audio.flag from an earlier session must not make the loop below stop
# Samsung's audioserver in a session that keeps it (ONEOS_GUEST_AUDIO=0).
# One UI's dumpstate and bugreport services too (0.4.71): a guest's ctl.start reaches One UI's init,
# whose dumpstate dumps every service, One UI's vold among them. vold's DUMP permission check waited
# 47 s for the guest's permission service, and init rebooted the phone right after ("reboot,vold-failed",
# 0.4.69 A15 c2da41ee: dumpstate pid 10916, "Check passed after 47063ms", shutdown 0.3 s later).
rm -f "$STAGE/data/guest_audio.flag"
nohup $BB sh -c "while true; do [ \"\$(getprop init.svc.zygote)\" = \"running\" ] && setprop ctl.stop zygote; [ \"\$(getprop init.svc.zygote_secondary)\" = \"running\" ] && setprop ctl.stop zygote_secondary; [ ! -f $STAGE/data/oneos_host_sf_frozen ] && [ \"\$(getprop init.svc.surfaceflinger)\" = \"running\" ] && setprop ctl.stop surfaceflinger; [ \"\$(getprop init.svc.bootanim)\" = \"running\" ] && setprop ctl.stop bootanim; [ -f $STAGE/data/guest_audio.flag ] && [ \"\$(getprop init.svc.audioserver)\" = \"running\" ] && setprop ctl.stop audioserver; for s in dumpstate dumpstatez bugreport bugreportd; do [ \"\$(getprop init.svc.\$s)\" = \"running\" ] && setprop ctl.stop \$s; done; sleep 0.2; done" </dev/null >/dev/null 2>&1 &
sleep 1
# The session's own copy of One UI's property store, now that One UI's
# framework is down (guest_props.sh store-on): the guest's persist settings
# never reach One UI's /data/property, and the return reuses their slots.
/system/bin/sh "$STAGE/guest_props.sh" store-on
# One UI's system_server kept Samsung's softdog (/dev/watchdog, 100 s) and is
# gone: its magic close now, before guest_prepare.sh's feeder takes over (see
# there; the Exynos phones panicked when nothing fed it).
SOFTDOG_V=0
if e=$(printf V 2>&1 > /dev/watchdog); then echo "Softdog: /dev/watchdog closed with V (One UI's system_server stopped)"; SOFTDOG_V=1
else echo "Softdog: /dev/watchdog not written ($e)"; fi
# The Galaxy A16 4G (MediaTek, 0.4.55 64e7f7da) panicked about 100 s into every
# session (softdog_fire, KP): there Samsung's softdog is /dev/softdog, a link to
# /dev/watchdog1, and /dev/watchdog is another device, which took the "V" above,
# so the off switch below was skipped. A /dev/softdog gets the magic close too,
# and the off switch.
SOFTDOG_DEV=0
# The node(s) One UI's system_server held (recorded above): the magic close, and
# the off switch below too.
if [ -f "$STAGE/host_softdog_nodes" ]; then
    while read -r n; do
        case "$n" in /dev/watchdog|/dev/softdog) continue ;; esac
        [ -c "$n" ] || continue
        SOFTDOG_DEV=1
        if e=$(printf V 2>&1 > "$n"); then echo "Softdog: $n (One UI's system_server had it open, or of group system) closed with V"
        else echo "Softdog: $n (One UI's system_server had it open, or of group system) not written ($e)"; fi
    done < "$STAGE/host_softdog_nodes"
fi
if [ -c /dev/softdog ]; then
    SOFTDOG_DEV=1
    if e=$(printf V 2>&1 > /dev/softdog); then echo "Softdog: /dev/softdog ($(readlink /dev/softdog 2>/dev/null || echo node)) closed with V"
    else echo "Softdog: /dev/softdog not written ($e)"; fi
fi
# The Exynos phones (S26+ 756047eb, Z Flip7 aaeea148, both 0.4.20) still
# panicked, "Software Watchdog Timer expired 100s" about 100 s after One UI's
# system_server stopped: /dev/watchdog is busy there (init's watchdogd) and
# neither has /dev/softdog, which 0.4.20 fed. Samsung's init owns the softdog
# (init.sysfw.rc: softdog init / settimeout 100 / disable): it disables it when
# zygote stops, which fired on both (resetreason restarted) and still did not
# hold, most likely because One UI's system_server kicked it again before it
# died. Its own off switch, persist.vendor.softdog=off ("softdog disable";
# Samsung sets it on unlocked and GSI phones, and One UI's system_server then
# leaves the softdog alone), now that system_server is gone. Only where the "V"
# above could not reach it; the snapshot taken before the switch puts the
# property back on the return (restore-persist), and after a hard reset too
# (recover). With a /dev/softdog too (the A16 4G above).
if { [ "$SOFTDOG_V" = 0 ] || [ "$SOFTDOG_DEV" = 1 ]; } && grep -q '^on property:persist\.vendor\.softdog=off' /system/etc/init/init.sysfw.rc 2>/dev/null; then
    sd=$(getprop persist.vendor.softdog)
    if [ "$sd" = off ]; then echo "Softdog: persist.vendor.softdog already off"
    else
        setprop persist.vendor.softdog off
        echo "Softdog: persist.vendor.softdog off for the session (was ${sd:-unset}): Samsung's init disables its software watchdog"
    fi
fi
echo "After the stop: CPU max/hw kHz: $(cpu_caps); skin: $(skin_temp)"

# --- MOUNT PREPARATION ---
# OneOS safeguards: One UI's /apex mounts must look the same after the
# container setup, and its APEXes on /data must still read back cleanly.
# (Field 5 of mountinfo is the mount point; matching anywhere in the line
# also caught binds whose *source* was under /apex.)
awk '$5 ~ /^\/apex(\/|$)/ {print $5, $10}' /proc/1/mountinfo | sort > "$STAGE/host_apex.before"
/system/bin/sh "$STAGE/check_host_apex.sh" before-setup
# The device states, display layouts and touch-port associations the guest's
# framework finds on the host, copied for the logs (pull-run-logs.sh takes
# $S/diag_*). toybox grep has no \| in basic regexps, which left the summary
# line empty in run 30 (takeover_app.log:15): use -E.
mkdir -p "$STAGE/diag_host"
for f in /odm/etc/devicestate/device_state_configuration_private.xml /odm/etc/devicestate/device_state_configuration.xml /vendor/etc/devicestate/device_state_configuration.xml; do
    [ -f "$f" ] || continue
    echo "Device states for the guest from $f: $(tr -d ' \t\r\n' < "$f" | grep -o -E '<identifier>[0-9]+</identifier>|<name>[^<]*</name>|PROPERTY_[A-Z_]+' | sed 's/<[^>]*>//g' | tr '\n' ' ')"
    break
done
for f in /vendor/etc/devicestate/device_state_configuration.xml /vendor/etc/displayconfig/display_layout_configuration.xml /vendor/etc/input-port-associations.xml /vendor/odm/etc/input-port-associations.xml; do
    [ -f "$f" ] && cp "$f" "$STAGE/diag_host/$(echo "${f#/}" | tr / _)"
done
ls -l /vendor/etc/displayconfig /vendor/odm/etc/displayconfig /vendor/odm/etc/devicestate > "$STAGE/diag_host/displayconfig_ls.txt" 2>&1
# Samsung switches each panel's touch IC from One UI's framework through its
# sysinput HAL ("enabled@<display state>,<event>", "set_fold_state"; run 30
# all.log 10:13:06). In the guest only the activator's fold monitor does it, for
# the cover IC: record where the nodes are.
{ for d in /sys/class/sec/tsp*; do
      echo "== $d"; ls "$d" "$d/input" 2>&1
      echo "input/enabled: $(cat "$d/input/enabled" 2>&1)"
  done
  for b in /vendor/bin/hw/*sysinput*; do
      echo "== $b"; strings -a "$b" 2>/dev/null | grep -E '^/sys/|enabled|fold_state' | head -40
  done
} > "$STAGE/diag_host/touch_nodes.txt" 2>&1
echo "=== [5/6] $(date +%T) Executing Mount Hierarchy Preparation ==="
/system/bin/sh "$STAGE/guest_prepare.sh"
PREP_RET=$?
if [ $PREP_RET -ne 0 ]; then
    echo "ERROR: guest_prepare.sh failed (code $PREP_RET)! Returning to One UI."
    # The One UI framework is already stopped; never leave the phone like that.
    /system/bin/sh "$STAGE/return_to_oneui.sh"
    exit 1
fi
awk '$5 ~ /^\/apex(\/|$)/ {print $5, $10}' /proc/1/mountinfo | sort > "$STAGE/host_apex.after"
if ! cmp -s "$STAGE/host_apex.before" "$STAGE/host_apex.after"; then
    echo "ERROR: the container setup changed One UI's /apex mounts:"
    diff "$STAGE/host_apex.before" "$STAGE/host_apex.after" | head -20
    echo "Aborting and returning to One UI."
    /system/bin/sh "$STAGE/return_to_oneui.sh"
    exit 1
fi
echo "One UI's /apex mounts unchanged by the container setup"
echo "Host mounts under $STAGE (outside the rootfs): $(awk -v s="$STAGE/" -v r="$STAGE/rootfs" 'index($2, s) == 1 && index($2, r) != 1 {print $2}' /proc/mounts | tr '\n' ' ')"
if ! /system/bin/sh "$STAGE/check_host_apex.sh" after-setup; then
    echo "ERROR: One UI's APEXes no longer read back after the container setup."
    echo "Aborting and returning to One UI."
    /system/bin/sh "$STAGE/return_to_oneui.sh"
    exit 1
fi
if [ "${ONEOS_PREPARE_ONLY:-0}" = "1" ]; then
    echo "ONEOS_PREPARE_ONLY=1: container prepared and checked, returning to One UI without starting the guest."
    /system/bin/sh "$STAGE/return_to_oneui.sh"
    /system/bin/sh "$STAGE/check_host_apex.sh" after-return
    exit 0
fi

# OneOS: keep the network usable while the guest boots. With One UI's
# ConnectivityService gone nothing maintains the routes, so the phone dropped
# off the network (and the adb tunnel with it) until the guest finished
# booting, which for a broken guest is never. Run guest_prepare's net_fix.sh
# from the host side for the whole session, and log what the network looked
# like, so a drop that routing cannot fix (wifi itself going away) shows up.
NETFIX="$STAGE/data/local/tmp/net_fix.sh"
$BB sh -c "
    while [ -f $STAGE/rootfs/system/build.prop ]; do
        /system/bin/sh $NETFIX 2>&1 | sed \"s/^/\$(date +%T) /\"
        {
            echo \"--- \$(date +%T)\"
            ip -4 -o addr show wlan0 2>&1 | awk '{print \$4}'
            ip rule show 2>&1 | awk 'NR <= 6 || /^14999:/ || / iif [^l][^ ]* lookup /'
            ip route show table 4242 2>&1
            [ -d /sys/class/net/swlan0 ] && echo \"swlan0: \$(ip -4 -o addr show swlan0 2>/dev/null | awk '{print \$4}'), ip_forward \$(cat /proc/sys/net/ipv4/ip_forward 2>/dev/null)\"
            ping -c 1 -W 2 \$(ip route show table 4242 2>/dev/null | awk '/default/{print \$3; exit}') >/dev/null 2>&1 && echo gateway: ok || echo gateway: unreachable
        } 2>&1
        # Watch One UI's APEX backing files: after earlier sessions One UI's
        # decompressed APEXes read back with dm-verity I/O errors.
        {
            echo \"--- \$(date +%T) apex\"
            ls -l /data/apex/decompressed/ 2>&1 | awk '{print \$5, \$6, \$7, \$NF}'
            for l in /sys/block/loop*/loop/backing_file; do
                case \"\$(cat \$l 2>/dev/null)\" in /data/apex/*) echo \"\$(basename \$(dirname \$(dirname \$l))): \$(cat \$l)\";; esac
            done
        } >> $STAGE/apex_watch.log 2>&1
        sleep 10
    done
" </dev/null >>"$STAGE/net_watch.log" 2>&1 &

# The guest's own build props (ro.oplus.* etc.), now that its rootfs is mounted.
/system/bin/sh "$STAGE/guest_props.sh" add "$STAGE/rootfs"
if [ -f "$STAGE/data/oneos_root/enabled" ]; then
    # Bounded, each part timed. Galaxy S24 Ultra ColorOS report 0756b014
    # (0.4.72, HARD_RESET, "stuck on Starting Zygote"): the last line of the
    # switch was guest_props.sh's, then nothing from either part below and
    # no [6/6] for seven minutes, until the phone was force-restarted with
    # the keys (reset reason MPON, "User press reset keys for 7 sec"); the
    # auto-return is armed only at [6/6]. A part that does not finish now
    # ends the session like a failed one. Their own output:
    # data/oneos_root/adb/oneos/run/session.log (in the session logs).
    echo "Guest runtime: $(date +%T) module installers (oneos_runtime.sh install)"
    timeout 240 "$BB" chroot "$STAGE/rootfs" /system/bin/sh /data/oneos_runtime.sh install
    GR_RC=$?
    if [ "$GR_RC" = 0 ]; then
        echo "Guest runtime: $(date +%T) modules onto the tree (guest_modules.sh)"
        BB="$BB" timeout 120 /system/bin/sh "$STAGE/tmp/guest_modules.sh"
        GR_RC=$?
    fi
    if [ "$GR_RC" != 0 ]; then
        [ "$GR_RC" = 124 ] && echo "Guest runtime: $(date +%T) that part did not finish in time and was stopped"
        echo "Guest module installation failed (exit $GR_RC); returning to One UI"
        /system/bin/sh "$STAGE/return_to_oneui.sh"
        exit 1
    fi
    echo "Guest runtime: $(date +%T) modules ready"
fi

# --- STOP HOST DAEMONS & LAUNCH CONTAINER ---
echo "=== [6/6] $(date +%T) Launching the guest takeover daemon ==="

# Stop the HOST media codec stack. The guest's libmedia binds `media.codec` from
# the shared servicemanager, i.e. Samsung's mediaserver - whose IMediaCodecList
# AIDL hash differs from the GSI's. The reply parcel is then parsed as garbage
# ("enforceInterface() expected 'android.gui.IGraphicBufferProducer' but read
# 'android.media.IMediaCodecList'", "AString: ctor got NULL"), which yields a
# codec list with a bogus length, so findCodecForFormat -> codecHandlesFormat
# spins ~2M times inside both system_server and SystemUI, round-tripping to
# mediaserver each iteration. That is the 125% CPU / constant overheating / GB
# of logcat. With no media.codec registered the lookup fails fast and the list
# is empty. Audio is unaffected (audioserver is its own process and is kept).
# mediaserver must stay UP even though the codec list is unusable: apps play
# short sounds with MediaPlayer, and MediaPlayer.setDataSource blocks in
# IMediaDeathNotifier::getMediaPlayerService when "media.player" is missing.
# That is a 5 s main-thread stall -> ANR -> force-close: Messaging died on every
# send because of its "sent" sound (playSentSound), and any app doing the same
# would die too. Keep only the codec processes down, which is what causes the
# spin described above.
#
# OneOS: on Android 17 there is no media.codec service any more (codecs go
# through the Codec2 HAL stores directly), yet guests still overheat talking to
# Samsung's modified mediaserver/mediaextractor/mediametrics. So by default the
# host's copies are stopped and guest_start.sh starts the GUEST's own, which
# share the guest framework's AIDL. The Codec2 HALs (vendor-qti-media-c2-hal,
# media.swcodec) stay on the host: they are stable versioned AIDL either way.
# Set ONEOS_GUEST_MEDIA=0 to get the old behaviour back.
if [ "${ONEOS_GUEST_MEDIA:-1}" = "1" ]; then
    for svc in media mediaextractor mediametrics media.codec media.metrics; do
        setprop ctl.stop $svc 2>/dev/null || true
    done
    kill -9 $(pidof mediaserver) $(pidof mediaextractor) $(pidof media.metrics) $(pidof media.codec) 2>/dev/null || true
    touch "$STAGE/data/guest_media.flag"
else
    rm -f "$STAGE/data/guest_media.flag"
    setprop ctl.start media 2>/dev/null || true
    for svc in media.codec media.metrics; do
        setprop ctl.stop $svc 2>/dev/null || true
    done
    kill -9 $(pidof media.codec) $(pidof media.metrics) 2>/dev/null || true
fi

# Audio handover (run 29): ColorOS's IAudioPolicyService numbering is not
# Samsung's (listAudioProductStrategies -61, setStreamVolumeIndex -22,
# getDevicesForAttributes arrived as an AudioFlinger-only call) and Samsung's
# AudioFlinger refused every app stream. Stop the host audioserver;
# guest_start.sh starts the GUEST's, which drives Samsung's audio HAL through
# the stable android.hardware.audio.core AIDL like a GSI, and falls back to
# Samsung's if it does not register. The HAL is stopped and started so the
# guest's gets it fresh. ONEOS_GUEST_AUDIO=0 keeps Samsung's audioserver.
if [ "${ONEOS_GUEST_AUDIO:-1}" = "1" ]; then
    touch "$STAGE/data/guest_audio.flag"
    AHAL=$(getprop | sed -n 's/^\[init\.svc\.\(vendor\.audio-hal[^]]*\)\]: \[running\]$/\1/p' | tr '\n' ' ')
    echo "$AHAL" > "$STAGE/host_audio_hal_svcs"
    setprop ctl.stop audioserver
    n=0
    while [ $n -lt 25 ] && pidof audioserver >/dev/null; do n=$((n + 1)); sleep 0.2; done
    kill -9 $(pidof audioserver) 2>/dev/null || true
    for s in $AHAL; do setprop ctl.stop $s; done
    sleep 1
    for s in $AHAL; do setprop ctl.start $s; done
    echo "Host audioserver: $(getprop init.svc.audioserver); audio HAL services restarted: ${AHAL:-none found}"
    # The audio HAL adapter's vendor extension. The S25 series' One UI sets
    # ro.audio.ihaladaptervendorextension_enabled=true, and with One UI's
    # audioserver stopped nothing serves
    # android.media.audio.IHalAdapterVendorExtension/default: a guest whose image
    # has no value of its own (Infinity-X) took One UI's, and its audioserver
    # waited for the extension for good, so no sound and no microphone at all
    # (0.4.32 and 0.4.33 reports 3e9af08a, 72062bdf, f0fffbb5: "Waited one second"
    # 60 times, media.audio_flinger never registered). guest_props.sh already
    # gives an image's own value; when the key is still true and the
    # extension is not there a few seconds after the HAL restart, false for
    # the session (put back on the return with the other overrides).
    AVX=ro.audio.ihaladaptervendorextension_enabled
    if [ "$(getprop $AVX)" = true ] && [ -n "$RP" ]; then
        n=0
        while [ $n -lt 10 ] && ! timeout 5 service check android.media.audio.IHalAdapterVendorExtension/default 2>/dev/null | grep -q ": found"; do n=$((n + 1)); sleep 0.5; done
        if ! timeout 5 service check android.media.audio.IHalAdapterVendorExtension/default 2>/dev/null | grep -q ": found"; then
            grep -q "^$AVX=" "$STAGE/guest_props.overridden" 2>/dev/null || echo "$AVX=true" >> "$STAGE/guest_props.overridden"
            "$RP" -n "$AVX" false 2>/dev/null &&
                echo "Audio: $AVX=false for the session (no IHalAdapterVendorExtension with One UI's audioserver stopped)"
        fi
    fi
else
    rm -f "$STAGE/data/guest_audio.flag" "$STAGE/host_audio_hal_svcs"
    setprop ctl.start audioserver
    n=0; while [ $n -lt 25 ] && ! service check media.audio_policy 2>/dev/null | grep -q ": found"; do n=$((n + 1)); sleep 0.2; done
    echo "Host audioserver kept: $(getprop init.svc.audioserver)"
fi

# Bluetooth audio on a phone with only Samsung's Bluetooth audio HAL (0.4.33).
# The SM8750 and older Galaxies register vendor.samsung.hardware.bluetooth.audio.
# ISehBluetoothAudioProviderFactory and not Android's IBluetoothAudioProviderFactory,
# so a guest's Bluetooth found no audio HAL: devices connected and the sound
# stayed on the phone (S24 Ultra, S25 Ultra, A57 reports). Samsung's interface is
# Android's version 2 under other names; oneos_btaudio (switcher/native) serves
# Android's factory and forwards to Samsung's. The guest's stack asks
# servicemanager whether the name is declared before it looks, so the instance
# is declared for the session: a copy of the vendor manifest fragment that
# declares Samsung's HAL, with Android's factory added, is bound over it, and
# /apex/apex-info-list.xml is touched, which makes servicemanager read the
# manifests again (libvintf keys its cache on that file's mtime). Both go back
# on the return (return_to_oneui.sh): One UI's own stack would otherwise wait
# for a factory nobody serves. Samsung's audio HAL carries Qualcomm's provider
# for Android's factory as well and tries to register it when a guest opens
# its Bluetooth module ("BtAudioAIDLService: Could not register ...
# IBluetoothAudioProviderFactory/default, status=-3", S24 Ultra ColorOS
# sessions): with the declaration that now succeeds and replaces the bridge's
# registration, which is as good (the Fold8 Ultra has exactly that); the return
# restarts the audio HAL after taking the declaration back. Only when Samsung's
# factory is registered and Android's is not; ONEOS_GUEST_BT_AUDIO_BRIDGE=0
# leaves it all alone.
rm -f "$STAGE/bt_bridge_vintf"
BTA_AOSP=android.hardware.bluetooth.audio.IBluetoothAudioProviderFactory/default
BTA_SEH=vendor.samsung.hardware.bluetooth.audio.ISehBluetoothAudioProviderFactory/default
# The audio HAL that serves Samsung's factory was restarted just above and
# registers it again only after a few seconds: 0.4.33's first S25 Ultra
# sessions checked at once, found nothing and skipped the bridge without a word
# (f0fffbb5, 04857daa). So the vendor manifest decides whether this is such a
# phone, servicemanager whether Android's factory is declared (the
# SM8850 phones declare it themselves), and the start waits for Samsung's.
BT_WHY=""
BT_FRAG=$(grep -l -s "vendor.samsung.hardware.bluetooth.audio" /vendor/etc/vintf/manifest/*.xml | head -n 1)
[ -n "$BT_FRAG" ] || BT_FRAG=$(grep -l -s "vendor.samsung.hardware.bluetooth.audio" /vendor/etc/vintf/manifest.xml)
if [ "${ONEOS_GUEST_BT_AUDIO_BRIDGE:-1}" != 1 ]; then
    BT_WHY="off (ONEOS_GUEST_BT_AUDIO_BRIDGE=$ONEOS_GUEST_BT_AUDIO_BRIDGE)"
elif [ ! -f "$STAGE/oneos_btaudio" ] || [ -L "$STAGE/oneos_btaudio" ]; then
    BT_WHY="no oneos_btaudio in the stage"
elif [ -z "$BT_FRAG" ]; then
    BT_WHY="not needed (no vendor manifest declares Samsung's Bluetooth audio HAL)"
elif chmod 755 "$STAGE/oneos_btaudio" && [ "$(timeout 5 "$STAGE/oneos_btaudio" --declared "$BTA_AOSP" 2>/dev/null)" = 1 ]; then
    BT_WHY="not needed (the vendor declares Android's factory itself)"
elif [ "$(grep -c '</manifest>' "$BT_FRAG")" != 1 ]; then
    BT_WHY="$BT_FRAG is not one manifest; not started"
else
    n=0
    while [ $n -lt 30 ] && ! timeout 5 service check "$BTA_SEH" 2>/dev/null | grep -q ": found"; do n=$((n + 1)); sleep 0.5; done
    if ! timeout 5 service check "$BTA_SEH" 2>/dev/null | grep -q ": found"; then
        BT_WHY="Samsung's factory was not registered 15 s after the audio HAL restart; not started"
    fi
fi
BT_COPY="$STAGE/oneos_bt_vintf.xml"
if [ -n "$BT_WHY" ]; then
    echo "Bluetooth audio bridge: $BT_WHY"
else
    echo "Bluetooth audio bridge: Samsung's factory registered after $((n / 2)) s"
    $BB awk '/<\/manifest>/ {
        print "    <hal format=\"aidl\">"
        print "        <name>android.hardware.bluetooth.audio</name>"
        print "        <version>2</version>"
        print "        <fqname>IBluetoothAudioProviderFactory/default</fqname>"
        print "    </hal>"
    } { print }' "$BT_FRAG" > "$BT_COPY"
    chmod 644 "$BT_COPY"
    chcon u:object_r:vendor_configs_file:s0 "$BT_COPY" 2>/dev/null
    if grep -q "IBluetoothAudioProviderFactory/default" "$BT_COPY" && $BB mount -o bind,ro "$BT_COPY" "$BT_FRAG"; then
        echo "$BT_FRAG" > "$STAGE/bt_bridge_vintf"
        touch /apex/apex-info-list.xml
        (umask 027; $BB nohup "$STAGE/oneos_btaudio" > "$STAGE/oneos_btaudio.log" 2>&1 </dev/null &)
        n=0
        while [ $n -lt 25 ] && ! timeout 5 service check "$BTA_AOSP" 2>/dev/null | grep -q ": found"; do n=$((n + 1)); sleep 0.2; done
        echo "Bluetooth audio bridge: $(timeout 5 "$STAGE/oneos_btaudio" --check 2>&1) (manifest: $BT_FRAG; $(head -n 1 "$STAGE/oneos_btaudio.log" 2>/dev/null))"
    else
        echo "Bluetooth audio bridge: could not declare the factory over $BT_FRAG; not started"
    fi
fi

# Same handover for wifi. The guest's WifiService binds IWificond (service
# "wifinl80211") and drives the vendor HAL through it. Samsung's wificond is
# still holding the client interface that One UI's (now dead) WifiService
# created, so every startScan() comes back "status: -1" and the framework sees
# "No scan results" - wifi looks broken but only the scanner is wedged. The
# GSI's own wificond starts in guest_start.sh and scans fine against the same
# vendor HAL.
setprop ctl.stop wificond 2>/dev/null || true
kill -9 $(pidof wificond) 2>/dev/null || true
sleep 1
# Pixel 17 has no wificond (only AOSP's /system/bin/wificond link to a
# system_ext binary its system_ext lacks) and needs none: its wifi module
# (config_wificondMigrationEnabled=true) drives nl80211 itself ("Nl80211Native:
# useWificond: false") and never binds "wifinl80211". One UI's is restarted idle,
# with no client interface, for One UI only; its "No handler for scan result
# notification" warnings are expected (ColorOS run 36a has them too). The link is
# absolute, so resolve it inside the guest's rootfs, not the host's.
GW=$(readlink "$STAGE/rootfs/system/bin/wificond" 2>/dev/null)
case "$GW" in /*) GW="$STAGE/rootfs$GW" ;; "") GW="$STAGE/rootfs/system/bin/wificond" ;; *) GW="$STAGE/rootfs/system/bin/$GW" ;; esac
if [ ! -f "$GW" ]; then
    setprop ctl.start wificond 2>/dev/null || true
    echo "No wificond in the guest image (its wifi module drives nl80211 itself): One UI's restarted idle ($(getprop init.svc.wificond))"
fi
# The phone's own A/B updater stays stopped while the guest runs. It is a
# shared binder service: the guest's Google Play services system update, or
# the setup wizard's update check, could hand it a payload for the phone.
# init does not restart a service stopped this way; the return's reboot starts
# it again (an interrupted One UI update resumes then).
if [ -n "$(getprop init.svc.update_engine)" ] && [ "$(getprop init.svc.update_engine)" != stopped ]; then
    setprop ctl.stop update_engine 2>/dev/null
    n=0; while [ $n -lt 10 ] && [ "$(getprop init.svc.update_engine)" = running ]; do n=$((n + 1)); sleep 0.2; done
    echo "Phone updater (update_engine) stopped for the session: $(getprop init.svc.update_engine)"
fi

# ColorOS's bootanimation opens /data/local/bootanimation.zip before its own
# Find N animation (run 30 logcat). The owner wants ColorOS's animation kept,
# so make sure nothing in the staged /data shadows it.
rm -f "$STAGE/data/local/bootanimation.zip"
# Chrome in the guest (0.4.33): on Android 17 Chrome starts its renderers as
# native-only services (NativeOnlySandboxedProcessService, through zygote_next),
# which the guest cannot start: zygote_next is One UI's, so
# guest_no_native_services.py refuses them, and Chrome has no fallback for that
# service, so no page ever rendered ("Failed to establish the service
# connection", every guest since 0.4.25). Chrome only takes that
# path while its JavalessRenderers feature is on, and the --javaless-renderers
# switch decides first (ChildProcessCreationParamsImpl, JavalessRenderersFeatureList);
# Chrome reads /data/local/chrome-command-line with no further condition
# (CommandLineInitUtil). With the switch at disabled Chrome uses its Java
# renderers, which start through the guest's own app zygote like WebView's.
# The guest's /data/local, written before the guest runs; data the guest can
# write, so never through a link. A file the user made keeps its flags.
# ONEOS_GUEST_CHROME_JAVA_RENDERERS=0 leaves it alone.
CCL="$STAGE/data/local/chrome-command-line"
if [ "${ONEOS_GUEST_CHROME_JAVA_RENDERERS:-1}" = 1 ] && [ -d "$STAGE/data/local" ] && [ ! -L "$STAGE/data/local" ]; then
    if [ -L "$CCL" ] || { [ -e "$CCL" ] && [ ! -f "$CCL" ]; }; then
        echo "Chrome: $CCL is not a plain file; left alone"
    elif [ ! -e "$CCL" ]; then
        (set -C; echo "_ --javaless-renderers=disabled" > "$CCL") 2>/dev/null && chmod 644 "$CCL" &&
            echo "Chrome: Java renderers (data/local/chrome-command-line made)"
    elif ! grep -q -- "--javaless-renderers" "$CCL"; then
        CCL_LINE="$(head -n 1 "$CCL") --javaless-renderers=disabled"
        rm -f "$CCL" && (set -C; echo "$CCL_LINE" > "$CCL") 2>/dev/null && chmod 644 "$CCL" &&
            echo "Chrome: Java renderers (added to the user's chrome-command-line)"
    else
        echo "Chrome: chrome-command-line already sets $(grep -o -- '--javaless-renderers=[a-z]*' "$CCL" | head -n 1)"
    fi
fi
# return_to_oneui.sh creates data/oneos_rec_stop as its first step (for the
# screen recording) and nothing removes it unless a recording starts; the
# session sampler below stops on it, so clear the last session's.
rm -f "$STAGE/data/oneos_rec_stop"

# Copy inner script and zygote_exec into container data partition. rm the
# destinations first: a guest could have left them as symlinks into host /data,
# and cp -f through such a link would overwrite a host file as root.
# (master_inner.sh: the copy's name up to app 0.3.6, removed with it.)
rm -f "$STAGE/data/guest_start.sh" "$STAGE/data/zygote_exec" "$STAGE/data/master_inner.sh"
cp -f "$STAGE/guest_start.sh" "$STAGE/data/guest_start.sh"
chmod 755 "$STAGE/data/guest_start.sh"
cp -f "$STAGE/zygote_exec" "$STAGE/data/zygote_exec"
chmod 755 "$STAGE/data/zygote_exec"
# The camera worker stand-in the UI activator runs in the guest (0.4.34), in
# the Knox stand-in's dex.
rm -f "$STAGE/data/oneos_edm_stub.dex"
if [ -f "$STAGE/OneOSEdmStub.dex" ] && [ ! -L "$STAGE/OneOSEdmStub.dex" ]; then
    cp -f "$STAGE/OneOSEdmStub.dex" "$STAGE/data/oneos_edm_stub.dex" && chmod 644 "$STAGE/data/oneos_edm_stub.dex"
fi
# The dimension overlay helper the UI activator runs in the guest (0.4.33).
rm -f "$STAGE/data/oneos_overlay_dimen.dex"
if [ -f "$STAGE/OneOSOverlayDimen.dex" ] && [ ! -L "$STAGE/OneOSOverlayDimen.dex" ]; then
    cp -f "$STAGE/OneOSOverlayDimen.dex" "$STAGE/data/oneos_overlay_dimen.dex" && chmod 644 "$STAGE/data/oneos_overlay_dimen.dex"
fi
# HyperOS: the launcher for hyos_spawner (guest_start.sh), from its set only.
rm -f "$STAGE/data/socket_exec"
if [ -f "$STAGE/socket_exec" ] && [ ! -L "$STAGE/socket_exec" ]; then
    cp -f "$STAGE/socket_exec" "$STAGE/data/socket_exec" && chmod 755 "$STAGE/data/socket_exec"
fi

# Inbound SMS (0.4.61): Samsung's rild queues new-SMS unsolicited responses
# until its own framework sends FW_READY=1 over HIDL. An AOSP guest's RILJ
# cannot send that vendor configuration, so SecRilProxy keeps the SMS in its
# pending list and the guest never sees UNSOL_RESPONSE_NEW_SMS. NOP the queue
# branch in the vendor library and bind-mount the copy for the session;
# return_to_oneui.sh removes it. A library without the exact sequence is left
# alone, and inbound SMS stays as it was.
if ! /system/bin/sh "$STAGE/libsec-ril-patch.sh" apply; then
    echo "!!! inbound SMS: libsec-ril.so was not patched; the guest will not receive SMS"
fi

# Launch takeover inside isolated mount namespace
$BB unshare -m $BB sh "$STAGE/data/guest_start.sh" </dev/null >"$STAGE/data/takeover.log" 2>&1 &
TAKEOVER_PID=$!
# Remember the container's mount namespace: return_to_oneui.sh kills exactly
# the processes in it. Guest daemons share names and even command lines with
# the host's (the guest vold is launched with the same flags as One UI's), so
# killing by name took down the host vold and init rebooted ("vold-failed").
sleep 0.5
readlink "/proc/$TAKEOVER_PID/ns/mnt" > "$STAGE/guest_mntns" 2>/dev/null
# And the device of the guest's root filesystem: zygote gives every app its own
# mount namespace, but all of them share this root (return_to_oneui.sh).
stat -c %d "$STAGE/rootfs" > "$STAGE/guest_rootdev" 2>/dev/null
echo "Guest mount namespace: $(cat "$STAGE/guest_mntns" 2>/dev/null) (host: $(readlink /proc/1/ns/mnt))"
echo "Takeover daemon PID: $TAKEOVER_PID"
# The guest zygote's sockets. On an S24 Ultra with LSPosed's Vector daemon
# (0.4.15), 20 s into the session the daemon restarted One UI's zygote: init
# made /dev/socket/zygote and usap_pool_primary over the guest's, the loop
# above stopped that zygote, and init's cleanup unlinked both files. The
# guest's system_server then found no zygote socket ("Error connecting to
# zygote ... No such file or directory") and no app ever started. /dev is the
# same tmpfs in the guest, so once zygote_exec has made them and turned into
# app_process64 (the takeover pid), each is bound onto itself here, in init's
# mount namespace. init can then neither unlink nor replace them (EBUSY): a
# restarted One UI zygote starts without its sockets and the loop stops it,
# and the guest keeps its own. return_to_oneui.sh takes the binds off before
# One UI's zygote starts again; a reboot drops them.
# With guest root on, guest_start.sh ends in "su --launch" (guest_root.c): the
# takeover pid stays that launcher and the zygote is its child. Up to 0.4.80
# only the takeover pid itself was looked at, so in every such session of the
# 0.4.72-0.4.74 reports (54 launches, none bound; 337 of 337 bound without
# guest root) this waited its 300 s and protected nothing.
protect_zygote_sockets() {
    n=0
    while :; do
        case "$(readlink "/proc/$TAKEOVER_PID/exe" 2>/dev/null)" in
            */app_process64) break ;;
            '') echo "Zygote sockets: the takeover process is gone, nothing to protect"; return 0 ;;
        esac
        zc=""
        for c in $($BB pgrep -P "$TAKEOVER_PID" 2>/dev/null); do
            case "$(readlink "/proc/$c/exe" 2>/dev/null)" in */app_process64) zc=$c; break ;; esac
        done
        [ -z "$zc" ] || { echo "Zygote sockets: the guest zygote is $zc, started by the guest root launcher $TAKEOVER_PID"; break; }
        n=$((n + 1))
        [ $n -lt 3000 ] || { echo "Zygote sockets: the guest zygote did not start within 300 s, not protected"; return 0; }
        sleep 0.1
    done
    for s in zygote usap_pool_primary; do
        f=/dev/socket/$s
        if [ -S "$f" ] && ! $BB awk -v m="$f" '$5 == m { f = 1 } END { exit !f }' /proc/self/mountinfo &&
           $BB mount --bind "$f" "$f"; then
            echo "Zygote sockets: $f bound onto itself at $(date +%T) (One UI's zygote is $(getprop init.svc.zygote))"
        else
            echo "!!! Zygote sockets: $f not protected (socket: $([ -S "$f" ] && echo yes || echo no))"
        fi
    done
}
protect_zygote_sockets </dev/null &
# Gap splash safety net: guest_start.sh releases the frozen surfaceflinger
# about 1 s after the pivot. If it never gets there (a FATAL exit), kill it
# here, so the panel and the auto-return below behave as without the splash.
if [ -n "$SF_FROZEN" ]; then
    $BB sh -c "sleep 20; f=$STAGE/data/oneos_host_sf_frozen; [ -s \$f ] || exit 0; p=\$(cat \$f); rm -f \$f; setprop ctl.stop surfaceflinger; [ \"\$(cat /proc/\$p/comm 2>/dev/null)\" = surfaceflinger ] && kill -9 \$p; echo \"\$(date +%T) guest_start.sh never released surfaceflinger \$p: killed\"" </dev/null >>"$GAP_SPLASH_LOG" 2>&1 &
fi

# ColorOS-only settings below (brightness scale, fold key) are left alone on
# other systems (Pixel): the rootfs is mounted since guest_prepare.sh.
GUEST_OPLUS=0
[ -f "$STAGE/rootfs/system/framework/oplus-services.jar" ] && GUEST_OPLUS=1
GUEST_VIVO=0
[ -f "$STAGE/rootfs/system/framework/vivo-services.jar" ] && GUEST_VIVO=1
# HyperOS keeps system_ext at the image root (system/system_ext links to One UI's).
GUEST_MIUI=0
[ -f "$STAGE/rootfs/system_ext/framework/miui-services.jar" ] && GUEST_MIUI=1
# A guest whose status bar is AOSP's SystemUI, laid out from the framework's
# cutout: every non-ColorOS guest, and Infinity-X, which carries OPPO's framework
# jars (GUEST_OPLUS) on a LineageOS base. ColorOS's own SystemUI places its icons
# from ro.oplus.display.screenhole.positon (guest_props.sh) instead, and HyperOS's
# MIUI SystemUI places its own.
GUEST_AOSP_SYSUI=1
[ $GUEST_OPLUS = 1 ] && [ ! -f "$STAGE/rootfs/system/framework/org.lineageos.platform.jar" ] && GUEST_AOSP_SYSUI=0
[ $GUEST_MIUI = 1 ] && GUEST_AOSP_SYSUI=0
# Window-level blur default for a new stage (UI activator below); only 0 or 1
# reaches the root shell.
GUEST_BLUR=1; [ "${ONEOS_GUEST_BLUR:-1}" = 1 ] || GUEST_BLUR=0
# Settings for the UI activator (run 44), checked here so that only 0/1, off,
# auto or a plain number goes into its root shell.
# ONEOS_WIFI_VERBOSE=1: verbose Wi-Fi logging in the guest (debug text under
# every network); otherwise it is switched off on every boot.
WIFI_VERBOSE=0; [ "${ONEOS_WIFI_VERBOSE:-0}" = 1 ] && WIFI_VERBOSE=1
# ONEOS_GUEST_DENSITY=off|auto|<dpi 120-640>: the inner panel's density.
GUEST_DENSITY=auto
case "${ONEOS_GUEST_DENSITY:-auto}" in
    off|auto) GUEST_DENSITY=${ONEOS_GUEST_DENSITY:-auto} ;;
    [1-9][0-9][0-9]) [ "$ONEOS_GUEST_DENSITY" -ge 120 ] && [ "$ONEOS_GUEST_DENSITY" -le 640 ] && GUEST_DENSITY=$ONEOS_GUEST_DENSITY ;;
esac
[ "$GUEST_DENSITY" = "${ONEOS_GUEST_DENSITY:-auto}" ] || echo "ONEOS_GUEST_DENSITY=$ONEOS_GUEST_DENSITY is not off, auto or 120-640: auto"
# ONEOS_GUEST_POSTURE=live: the fold line's posture follows the guest's hinge
# state instead of always flat.
# Live by default with the hinge sets of pull request #1 (Fold8) and the Fold8 Ultra's.
POSTURE_DEFAULT=flat
case "${ONEOS_PROFILE:-}:$GUEST_OPLUS" in
    # 0.4.38: n6-f8u on the Z Fold8 too (the Find N6 global image); pull request #37: the
    # Z Fold8's own n6-global-f8 (n6-f8u on stages made before it).
    f8:1) HINGE_SET="n6-global-f8 n6-f8u" ;;
    f8:0) HINGE_SET=pixel-f8 ;;
    f8u:1) HINGE_SET=n6-f8u ;;
    f8u:0) HINGE_SET=pixel-f8u ;;
    *) HINGE_SET="" ;;
esac
for h in $HINGE_SET; do
    grep -q "^  \"set\": \"$h\",\$" "$STAGE/.oneos_stage" && POSTURE_DEFAULT=live
done
GUEST_POSTURE_LIVE=0; [ "${ONEOS_GUEST_POSTURE:-$POSTURE_DEFAULT}" = live ] && GUEST_POSTURE_LIVE=1
GUEST_FOLD_FORM=0; [ "${ONEOS_GUEST_FORM:-fold}" = fold ] && GUEST_FOLD_FORM=1
# Start UI Activator daemon. One pass per boot of the guest: after a soft
# reboot of it (guest_softreboot.sh bumps tmp/softreboot.gen, 0.4.39) the
# same steps run again for the new boot; it ends with the session.
$BB sh -c "
BB=\"$BB\"
[ -n \"\$BB\" ] || BB=\$(which busybox 2>/dev/null || echo /data/adb/ksu/bin/busybox)
GEN=\$(cat $STAGE/tmp/softreboot.gen 2>/dev/null); PASS=1; BRPID=''
while true; do
while true; do
    sleep 2
    PID=\$(pidof system_server | awk '{print \$1}')
    if [ -n \"\$PID\" ]; then
        # Bring apps, early (owner, 11-10: the apps came 10-15 s after the
        # launcher; the restore below only starts at the end of this pass, about
        # 35 s after Home). Once per guest system_server and only when a copy
        # waits: the script itself waits for the guest's user 0 to be unlocked
        # and its package service to answer, then installs while the launcher
        # comes up. The boot animation is not held for it; the later start
        # below stays (it only tells a running early one to go).
        if [ \"\$PID\" != \"\$BRPID\" ] && [ -f $STAGE/data/oneos_bring_restore.sh ] && ls -d $STAGE/data/oneos_bring/*/apk >/dev/null 2>&1; then
            BRPID=\$PID
            ( $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/sh /data/oneos_bring_restore.sh early ) </dev/null >/dev/null 2>&1 &
            echo '[UI Activator] Bring apps: early restore started (waits for the guest user to be unlocked; oneos_bring.log in the guest data)'
        fi
        if $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys window 2>/dev/null | grep -q 'mStatusBar'; then
            echo '[UI Activator] WindowManager is ready! Dismissing bootanim and unlocking...'
            setprop service.bootanim.exit 1
            kill -9 \$(pidof bootanimation) 2>/dev/null
            sleep 1
            # The screen's own timeout and the user's stay-awake choice: up to
            # 0.4.34 every boot forced stay awake on any charger (svc power stayon,
            # stay_on_while_plugged_in 7) and a timeout of 2^31-1 ms, left from
            # early bring-up, so the screen never slept while charging and any
            # timeout chosen in the guest was undone at the next session (owner,
            # Nothing OS run 23). Once per stage the two forced values go back
            # to off and one minute; anything else the user set stays.
            if [ -L $STAGE/data/oneos_screen_timeout ]; then
                echo '[UI Activator] screen timeout: data/oneos_screen_timeout is a link, not made by OneOS; left alone'
            elif [ ! -e $STAGE/data/oneos_screen_timeout ]; then
                SOP=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get global stay_on_while_plugged_in 2>/dev/null)
                SOT=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get system screen_off_timeout 2>/dev/null)
                [ \"\$SOP\" = 7 ] && $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings put global stay_on_while_plugged_in 0
                [ \"\$SOT\" = 2147483647 ] && $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings put system screen_off_timeout 60000
                mkdir $STAGE/data/oneos_screen_timeout 2>/dev/null
                echo \"[UI Activator] screen timeout: was stay_on_while_plugged_in=\${SOP:-?} screen_off_timeout=\${SOT:-?}; the forced values reset once (0, 60000)\"
            fi
            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings put system haptic_feedback_enabled 1
            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings put system peak_refresh_rate 120.0
            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings put system min_refresh_rate 120.0
            # ColorOS's touch idle (OTI) pushes SurfaceFlinger to 240/60 Hz over the
            # 120 Hz policy on this panel (run 29); also staged off by guest_prepare.sh.
            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys oplus_vrr_service oti false >/dev/null 2>&1 && echo '[UI Activator] refresh rate: ColorOS touch idle off'
            # Samsung Camera's working folder (guest_prepare.sh makes it when the
            # camera already has a uid): on a phone's first session with the
            # camera the package is only installed by this boot, the folder was
            # never made and no photo was saved (0.4.37, Z Fold6 report 034a7e05).
            # Made here once the camera's data folder exists.
            CAMD=$STAGE/data/user/0/com.sec.android.app.camera
            if [ -d $STAGE/samcam_build ] && [ ! -d $STAGE/data/sec/camera ] && [ -d \$CAMD ] && [ ! -L \$CAMD ] && [ ! -L $STAGE/data/sec ]; then
                CU=\$(stat -c %u \$CAMD 2>/dev/null)
                if [ -n \"\$CU\" ] && [ \"\$CU\" -ge 10000 ]; then
                    mkdir -p $STAGE/data/sec/camera && chown 0:0 $STAGE/data/sec && chmod 771 $STAGE/data/sec &&
                        chown \$CU:\$CU $STAGE/data/sec/camera && chmod 2770 $STAGE/data/sec/camera &&
                        $BB chcon -R u:object_r:app_data_file:s0 $STAGE/data/sec 2>/dev/null
                    echo \"[UI Activator] Samsung Camera: data/sec/camera made for uid \$CU (first session with the camera)\"
                fi
            fi
            # Live Alerts (0.4.36, every ColorOS image with the stock features of
            # guest_prepare.sh): OPPO's fluid cloud stays off while this global
            # says unsupported, as the Fold8 runtime of pull request #2 found.
            if [ \"${ONEOS_GUEST_STOCK_FEATURES:-1}\" = 1 ] &&
               timeout 10 $BB nsenter -t \$PID -m /system/bin/sh -c '[ -f /my_stock/etc/extension/com.oplus.oplus-feature.xml ]' 2>/dev/null; then
                $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings put global fluid_cloud_not_support 0 && echo '[UI Activator] Live Alerts: fluid_cloud_not_support 0'
            fi
            # Circle to Search (0.4.38): the global builds wire it to Google
            # (contextual_search_package) but leave OPPO's press and hold on the
            # gesture handle or home button off until their setup turns it on, which
            # the guest skips (F8U test12: isCircleToSearchGestureEnable false,
            # oplus_gesture_handle_cui_enable 0). Once per stage, where the image has
            # the feature, so a later choice in Settings stays.
            if [ ! -e $STAGE/data/oneos_cts_default ] && [ ! -L $STAGE/data/oneos_cts_default ] &&
               timeout 10 $BB nsenter -t \$PID -m /system/bin/sh -c 'ls /my_product/etc/extension/feature_contextualsearch_*.xml' >/dev/null 2>&1; then
                for k in oplus_gesture_handle_cui_enable oplus_home_button_cui_enable; do
                    timeout 10 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings put secure \$k 1
                done
                mkdir $STAGE/data/oneos_cts_default 2>/dev/null
                echo \"[UI Activator] Circle to Search: press and hold on, \$(timeout 10 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get secure oplus_gesture_handle_cui_enable) (once per stage)\"
            fi
            # One UI's screen mode on every panel (0.4.38): the vendor render
            # intent recorded before the switch, as SurfaceFlinger's display color
            # setting (transaction 1023; 256 and up are vendor intents). The panels'
            # intents before and after are logged, so a session shows whether the
            # guest's own color service set them back.
            HRI=\$(cat $STAGE/host_render_intent 2>/dev/null)
            case \"\$HRI\" in
                [0-9]*)
                    B4=\$(timeout 10 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys SurfaceFlinger 2>/dev/null | grep -o 'renderIntent=[A-Z0-9x_]*' | tr '\n' ' ')
                    # The second int (when One UI's color mode was read) is the
                    # composition color mode SurfaceFlinger then keeps.
                    HCM=\$(cat $STAGE/host_color_mode 2>/dev/null)
                    case \"\$HCM\" in [1-9]|[1-9][0-9]) ;; *) HCM=\"\" ;; esac
                    timeout 10 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/service call SurfaceFlinger 1023 i32 \$HRI \${HCM:+i32 \$HCM} >/dev/null 2>&1
                    sleep 1
                    AF=\$(timeout 10 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys SurfaceFlinger 2>/dev/null | grep -o 'renderIntent=[A-Z0-9x_]*' | tr '\n' ' ')
                    echo \"[UI Activator] Screen mode: One UI's render intent \$HRI asked (color mode \${HCM:-the guest's}); panels before: \$B4, after: \$AF\" ;;
            esac
            # KernelSU's manager in the guest (0.4.39): One UI's own copy, staged by
            # the preflight, installed once; the guest's package manager gives it One
            # UI's app id (oneos.ksu.mgr_*), so the kernel takes it for the manager.
            # An older install with another id (before the patch) is replaced; an
            # install -r every session keeps it One UI's version (and its id).
            if [ ! -f $STAGE/data/oneos_ksu/manager ]; then
                # None staged (off by default since 0.4.39): a manager an earlier
                # session installed here keeps One UI's app id (below 15000) and the
                # kernel's trust; removed, with its data. One the user installed in
                # the guest too (0.4.41, A36 0ee8cdb1 on 0.4.40): its late load
                # (Magica) ran One UI's KernelSU boot as root in the guest, mounted
                # One UI's modules over it (every guest app died in the same idmap
                # lookup within a second) and rewrote One UI's KernelSU features
                # (adb root on, module umount off) in the shared kernel and config.
                for KP in me.weishu.kernelsu com.rifsxd.ksunext com.sukisu.ultra app.kitsusu.manager; do
                    KC=\$(timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm list packages -U \$KP 2>/dev/null | sed -n \"s/^package:\$KP uid://p\" | head -n 1)
                    case \"\$KC\" in
                        [0-9]*)
                            timeout 30 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm uninstall --user 0 \$KP >/dev/null 2>&1
                            echo \"[UI Activator] KernelSU manager: \$KP (app id \$KC) removed from the guest; its late load would run One UI's KernelSU boot and modules here (off for this session)\" ;;
                    esac
                done
            fi
            if [ -f $STAGE/data/oneos_ksu/manager ] && [ -f $STAGE/data/oneos_ksu/manager.apk ]; then
                read KP KU < $STAGE/data/oneos_ksu/manager
                kuid() { timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm list packages -U \$KP 2>/dev/null | sed -n \"s/^package:\$KP uid://p\" | head -n 1; }
                KC=\$(kuid)
                if [ -n \"\$KC\" ] && [ \"\$KC\" != \"\$KU\" ]; then
                    timeout 30 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm uninstall --user 0 \$KP >/dev/null 2>&1
                    echo \"[UI Activator] KernelSU manager: \$KP had app id \$KC, not One UI's \$KU; reinstalling\"
                    KC=''
                fi
                # Data dirs left by an install with another id (owner 15003 in 0.4.39
                # test1): installd refused them, the app could not write its cache and
                # its root service never listed the apps. Gone before the install, which
                # makes them again under the right id.
                for d in /data/user/0/\$KP /data/user_de/0/\$KP; do
                    o=\$(timeout 10 $BB nsenter -t \$PID -m $BB stat -c %u \$d 2>/dev/null)
                    [ -n \"\$o\" ] && [ \"\$o\" != \"\$KU\" ] && timeout 20 $BB nsenter -t \$PID -m $BB rm -rf \$d &&
                        echo \"[UI Activator] KernelSU manager: removed \$d (owner \$o, not \$KU)\"
                done
                # Its root service's main.jar, which the app writes on every start and
                # leaves read-only (0444): the next start could not open it for writing
                # (0.4.39 test3: EACCES, no app list). Removed before each start here.
                for d in /data/user/0/\$KP/cache /data/user_de/0/\$KP/cache; do
                    timeout 10 $BB nsenter -t \$PID -m $BB rm -f \$d/main.jar 2>/dev/null
                done
                KR=\$(timeout 60 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm install -r --user 0 /data/oneos_ksu/manager.apk 2>&1 | tail -n 1)
                # The app runs its own bundled ksud (lib/arm64/libksud.so), not
                # /data/adb/ksud: in 0.4.39 test1 its soft reboot stopped and started
                # services through One UI's init. That copy becomes the same wrapper.
                KL=\$(timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm path \$KP 2>/dev/null | sed -n 's/^package://p' | grep '/base\\.apk$' | head -n 1)
                KL=\${KL%/base.apk}/lib/arm64/libksud.so
                KW=''
                if [ -f $STAGE/data/oneos_ksu/ksud ] && timeout 10 $BB nsenter -t \$PID -m $BB test -f \$KL &&
                   timeout 20 $BB nsenter -t \$PID -m $BB cp -f /data/oneos_ksu/ksud \$KL &&
                   timeout 10 $BB nsenter -t \$PID -m $BB chmod 755 \$KL; then
                    KW=', its libksud.so is the OneOS wrapper'
                else
                    KW=\", its libksud.so NOT wrapped (\$KL)\"
                fi
                KN=\$(kuid)
                echo \"[UI Activator] KernelSU manager: \$KP app id \$KN (One UI's \$KU)\${KR:+, install: \$KR}\$KW\"
                # A system whose framework lacks guest_ksu_manager_appid.py gives it a
                # guest id: the kernel would not take it for the manager. Not left there.
                if [ -n \"\$KN\" ] && [ \"\$KN\" != \"\$KU\" ]; then
                    timeout 30 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm uninstall --user 0 \$KP >/dev/null 2>&1
                    echo \"[UI Activator] KernelSU manager: this system's framework does not keep One UI's app id (no guest_ksu_manager_appid.py); removed again\"
                fi
            fi
            # Navigation mode belongs to ColorOS: its SystemUI sets the navbar
            # overlay and navigation_mode from secure hide_navigationbar_enable
            # (0 buttons, 2/3 gestures). Forcing AOSP's gestural overlay left that
            # key at 0 (run 28): only a gesture handle was drawn while the
            # launcher stayed in 3-button mode, so neither worked. Keep the
            # user's choice; a stage that never had the key gets gestures.
            NAVK=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get secure hide_navigationbar_enable 2>/dev/null)
            [ \"\$NAVK\" = null ] && $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings put secure hide_navigationbar_enable 3 2>/dev/null
            NAVM=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get secure navigation_mode 2>/dev/null)
            echo \"[UI Activator] navigation: hide_navigationbar_enable=\$NAVK navigation_mode=\$NAVM\"
            case \"\$NAVK:\$NAVM\" in 0:2|2:0|3:0) echo \"[UI Activator] WARNING: ColorOS nav key and AOSP navigation_mode disagree\" ;; esac
            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm disable android.ext.services/android.ext.services.notification.Assistant 2>/dev/null || true
            # Fallback for a staged /data that had no settings files to seed, before
            # HOME: a fresh stage has none. Pixel's two setup wizards (ColorOS has
            # none) would take that first boot and wait for Google services.
            # With Google services presented (guest_prepare.sh wrote
            # data/oneos_gms_present) neither the keys nor the wizards are touched:
            # Pixel's setup wizard runs (HOME is the wizard while the stage is not
            # provisioned), sets both keys and turns itself off when it finishes
            # (it can be skipped without an account), and the stage keeps that.
            if [ -f $STAGE/data/oneos_gms_present ]; then
                echo \"[UI Activator] Google services presented: setup left to the setup wizard (device_provisioned=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get global device_provisioned 2>/dev/null) user_setup_complete=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get secure user_setup_complete 2>/dev/null))\"
            else
            for kv in 'global device_provisioned' 'secure user_setup_complete'; do
                [ \"\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get \$kv 2>/dev/null)\" = 1 ] || $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings put \$kv 1
            done
            for p in com.google.android.setupwizard com.google.android.pixel.setupwizard; do
                $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm disable-user --user 0 \$p >/dev/null 2>&1 && echo \"[UI Activator] \$p disabled (setup is done in the container)\"
            done
            fi
            # Run 43: the verbose Wi-Fi logging run 42 switched on for its diag_wifi
            # capture (below) was saved in the stage's WifiConfigStore.xml and put
            # debug text (frequency, BSSID, RSSI, score) under every network in the
            # setup wizard and Settings. Set on every boot, for every guest, Wi-Fi
            # on or off, before HOME so the setup wizard's Wi-Fi page never shows
            # it: disabled (which also clears what runs 42 and 43 saved) unless
            # ONEOS_WIFI_VERBOSE=1.
            # Samsung's IMS app in the guest (guest_prepare.sh, ONEOS_GUEST_SEC_IMS=1):
            # the guest's telephony is told to bind it through the carrier config
            # override, both slots, kept in the guest's carrier config store; then
            # what the package manager and the ImsResolver made of it. The marker
            # is in data the guest can write: -e and never a link (see the blur
            # marker below).
            if [ -e $STAGE/data/oneos_sec_ims ] && [ ! -L $STAGE/data/oneos_sec_ims ]; then
                # 0.4.38: ColorOS's device MMTEL ImsService is Qualcomm's org.codeaurora.ims,
                # so its ImsResolver skipped Samsung's (F8U test10: IMS registered, never used,
                # no SMS either way). test12: set-ims-service -d without -f answered true and
                # left Qualcomm's bound; the carrier config route is refused for root. Now:
                # (1) the device override with explicit features (0 emergency, 1 MMTEL);
                # (2) if neither slot binds Samsung's, a fabricated overlay of the device
                # setting config_ims_mmtel_package and a restart of the phone process, whose
                # ImsResolver reads it at start. Each step and what is bound, logged.
                G=\"timeout 10 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh\"
                ims_bound() { \$G /system/bin/cmd phone ims get-ims-service -s \$1 -d -f 1 2>&1 | tr -d '\\r' | tail -1; }
                SB=0
                # 0.4.60: the phone service first (HyperOS S25 b474c339, A56 9c6b6ac3:
                # slot 0 answered \"Can't find service: phone\" and never got IMS).
                i=0; while [ \$i -lt 30 ] && ! \$G /system/bin/service check phone 2>/dev/null | grep -q ': found'; do sleep 2; i=\$((i + 1)); done
                for s in 0 1; do
                    for try in 1 2 3; do
                        o=\$(\$G /system/bin/cmd phone ims set-ims-service -s \$s -d -f 0,1 com.sec.imsservice 2>&1 | tr '\\n' ' ' | cut -c1-120)
                        case \"\$o\" in *\"find service\"*) sleep 5 ;; *) break ;; esac
                    done
                    echo \"[UI Activator] Samsung IMS: slot \$s override: \$o\"
                    b=\$(ims_bound \$s); echo \"[UI Activator] Samsung IMS: slot \$s bound: \$b\"
                    [ \"\$b\" = com.sec.imsservice ] && SB=1
                done
                if [ \$SB = 0 ]; then
                    \$G /system/bin/cmd overlay fabricate --target android --name OneOSImsMmtel android:string/config_ims_mmtel_package string com.sec.imsservice >/dev/null 2>&1
                    echo \"[UI Activator] Samsung IMS: device setting overlay: \$(\$G /system/bin/cmd overlay enable --user 0 com.android.shell:OneOSImsMmtel 2>&1 | tr '\\n' ' ' | cut -c1-120)\"
                    PP=\$(\$G /system/bin/pidof com.android.phone 2>/dev/null)
                    [ -n \"\$PP\" ] && \$G /system/bin/kill -9 \$PP 2>/dev/null
                    sleep 15
                    for s in 0 1; do
                        \$G /system/bin/cmd phone ims set-ims-service -s \$s -d -f 0,1 com.sec.imsservice >/dev/null 2>&1
                        echo \"[UI Activator] Samsung IMS: slot \$s bound after the phone restart: \$(ims_bound \$s)\"
                    done
                fi
                echo \"[UI Activator] Samsung IMS: package \$(timeout 10 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm path com.sec.imsservice 2>/dev/null | head -1 | cut -c9-)\"
                echo \"[UI Activator] Samsung IMS: mmtel override \$(timeout 10 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd phone cc get-value -s 0 config_ims_mmtel_package_override_string 2>/dev/null | tail -1)\"
                timeout 10 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys phone 2>/dev/null | grep -i -m 6 'ImsResolver\|imsservice\|MmTel' | sed 's/^/[UI Activator] Samsung IMS: /'
                # 0.4.39 (S25U AT&T report): One UI's telephony broadcasts
                # android.intent.action.ISIM_LOADED once the SIM's ISIM files are read;
                # the guest's AOSP telephony never does. Samsung IMS checks the ISIM once
                # at SIM LOADED (0.46 s before the guest had read the IMPU), then waits
                # for that broadcast forever: no registration, no calls or SMS on carriers
                # with an ISIM. Sent here per slot with a loaded SIM, three times; IMS
                # ignores it for a SIM without an ISIM app or once its ISIM is loaded.
                ( for w in 10 30 90; do
                    sleep \$w
                    ss=\$(\$G /system/bin/getprop gsm.sim.state 2>/dev/null | tr -d '\\r')
                    for s in 0 1; do
                        st=\$(echo \"\$ss\" | cut -d, -f\$((s + 1)))
                        [ \"\$st\" = LOADED ] || continue
                        \$G /system/bin/am broadcast -a android.intent.action.ISIM_LOADED --ei phone \$s >/dev/null 2>&1
                        echo \"[UI Activator] Samsung IMS: slot \$s ISIM_LOADED sent (after a \$w s wait)\"
                    done
                done ) &
            else
                # Samsung IMS off: the device setting overlay of an earlier session goes.
                timeout 10 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd overlay disable --user 0 com.android.shell:OneOSImsMmtel >/dev/null 2>&1
            fi
            if [ $WIFI_VERBOSE = 1 ]; then WV=enabled; else WV=disabled; fi
            timeout 10 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd wifi set-verbose-logging \$WV >/dev/null 2>&1
            echo \"[UI Activator] wifi: verbose logging \$WV -> \$(timeout 10 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd wifi is-verbose-logging 2>&1 | head -1)\"
            # Window-level blur (run 44, owner): guest_props.sh tells SurfaceFlinger
            # blur is supported, but the Pixel kept \"Allow window-level blurs\" off
            # (Developer options) until the owner turned it on. Allowed once, on a
            # stage's first boot (a marker in the guest's data); a later choice in
            # Developer options stays. ColorOS guests and ONEOS_GUEST_BLUR=0: untouched.
            # The marker is in data the guest can write, and this shell is host
            # root: it is made with mkdir and checked with -e and -L, never with
            # touch or -f, which follow a link the guest may have left there to
            # a path in One UI's /data (an older marker, a file, still counts).
            if [ $GUEST_OPLUS = 0 ] && [ -L $STAGE/data/oneos_blur_default ]; then
                echo \"[UI Activator] window blur: data/oneos_blur_default is a link, not made by OneOS; left alone\"
            elif [ $GUEST_OPLUS = 0 ] && [ $GUEST_BLUR = 1 ] && [ ! -e $STAGE/data/oneos_blur_default ]; then
                $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings put global disable_window_blurs 0 >/dev/null 2>&1 &&
                    mkdir $STAGE/data/oneos_blur_default 2>/dev/null &&
                    echo \"[UI Activator] window blur: allowed (disable_window_blurs 0, first boot of this stage)\"
            fi
            # Cache quotas (S25 Ultra session af6c2b17): installd.setAppQuota is
            # blocked in the container (guest_installd_abi.py; quotas are set on
            # One UI's /data), but StorageStatsService still worked them out
            # after app installs and storage changes and logged a stack trace
            # per app: 33464 in 10 minutes of Play Store updates. Its own
            # setting turns the calculation off. Every boot, every guest.
            CQ=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get global enable_cache_quota_calculation 2>/dev/null)
            if [ \"\$CQ\" != 0 ]; then
                $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings put global enable_cache_quota_calculation 0 >/dev/null 2>&1 &&
                    echo \"[UI Activator] cache quotas: calculation off (was \${CQ:-unset}; installd.setAppQuota is blocked in the container)\"
            fi
            # Knox's edmnativehelper, which One UI's cameraserver (shared with the
            # guest, left running) asks on every camera open. Only One UI's
            # system_server registers that name and the switch stops it, so the
            # lookup blocks libbinder's full 5 s while CameraX gives up at 3 s and
            # the first open fails (Z Flip5 and S25 reports, both images; the HAL
            # opens afterwards, so a retry sometimes worked). One UI's wrapper
            # treats an absent name as camera allowed, so this is latency, not
            # policy: a binder under the name makes the lookup immediate.
            # patches/OneOSEdmStub.java answers every code with the single plain
            # int32 1 that One UI's own service replies with, so no transaction
            # number is assumed. uid system through app_process, like the angle
            # relay; it exits with the guest. ONEOS_GUEST_EDM_STUB=1, which the app
            # sends by default since 0.4.33 (Advanced can turn it off): every
            # camera open in the 0.4.32 reports waited the 5 s (Infinity-X, Pixel
            # and ColorOS on the S23, S24/S25 Ultra, A56, A57, Z Flip5) and
            # CameraX apps gave up with ERROR_CAMERA_OPEN_TIMEOUT.
            if [ \"${ONEOS_GUEST_EDM_STUB:-0}\" = 1 ] && [ -f $STAGE/OneOSEdmStub.dex ] && [ ! -L $STAGE/OneOSEdmStub.dex ]; then
                # Inside the guest like the worker below: started on One UI's side
                # (uid system) it was gone 45 s after HOME on the Fold8 Ultra and
                # every open waited the 5 s again (run 22), while the worker in the
                # guest stayed. It also registers itself again if the name goes.
                ($BB nohup $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/env CLASSPATH=/data/oneos_edm_stub.dex /system/bin/app_process /system/bin OneOSEdmStub \$PID > $STAGE/edm_stub.log 2>&1 </dev/null &)
                sleep 2
                echo \"[UI Activator] Knox edm stub: \$(head -n 1 $STAGE/edm_stub.log 2>/dev/null | tr -d '\n' || true); \$(timeout 10 service check edmnativehelper 2>&1 | tr -d '\n')\"
                # The Samsung camera service worker (patches/OneOSCameraWorker.java, in
                # the same dex), which the One UI cameraserver also asks on every open:
                # on the S25 Ultra firmware each connect waited 5 s for it and then
                # refused the guest app (has been restricted, report 04857daa).
                # Inside the guest, which knows the packages of its own apps; only
                # while nothing serves the name. The fold posture it sends the HAL
                # only on a fold (ONEOS_CAMERA_POSTURE=1): a bar phone's one device
                # state is 0, which would read as folded.
                if ! timeout 10 service check media.camera.worker 2>/dev/null | grep -q ': found'; then
                    ($BB nohup $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/env CLASSPATH=/data/oneos_edm_stub.dex ONEOS_CAMERA_POSTURE=$GUEST_FOLD_FORM /system/bin/app_process /system/bin OneOSCameraWorker \$PID > $STAGE/camera_worker.log 2>&1 </dev/null &)
                    sleep 2
                fi
                echo \"[UI Activator] camera worker: \$(head -n 1 $STAGE/camera_worker.log 2>/dev/null | tr -d '\n' || true); \$(timeout 10 service check media.camera.worker 2>&1 | tr -d '\n')\"
            fi
            # Samsung's speaker tuning (experiment, 0.4.58). One UI's audioserver
            # runs Dolby (DAX3 with Samsung's speaker endpoint tuning), SoundBooster
            # Plus and SoundAlive on what it plays; the guest's audioserver runs
            # none of them, and ColorOS's own engine (AudioEffectCenter, effect
            # 41f6c0f4) is not in Samsung's effect HAL (reports 4933a41d, 3715fe57,
            # 30124d7e: the speaker sounds bad). patches/OneOSSoundFx.java, in the
            # same dex, puts the vendor effect HAL's Dolby on the guest's output mix
            # and holds it until the guest's system_server is gone, created again 2 s
            # after music starts so it is on the output music plays on (0.4.65).
            # On by default since 0.4.65 (F8U InfinityX run: Dolby on the music
            # output, sound much better); ONEOS_GUEST_DOLBY=0: off. Phones
            # whose effect HAL has no Dolby: it gives up after a minute, logged.
            if [ \"${ONEOS_GUEST_DOLBY:-1}\" = 1 ] && [ -f $STAGE/OneOSEdmStub.dex ] && [ ! -L $STAGE/OneOSEdmStub.dex ]; then
                ($BB nohup $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/env CLASSPATH=/data/oneos_edm_stub.dex /system/bin/app_process /system/bin OneOSSoundFx \$PID > $STAGE/sound_fx.log 2>&1 </dev/null &)
                sleep 3
                echo \"[UI Activator] sound fx: \$(head -n 3 $STAGE/sound_fx.log 2>/dev/null | tr '\n' ' ' || true)\"
            fi
            # Density and fold line of the inner panel (run 43), before HOME so the
            # setup wizard starts with them. With no init of its own the guest
            # takes ro.sf.lcd_density from the property area it shares with One
            # UI: Samsung's 480, so the 2256 px inner panel was 752 dp wide
            # (sw752), under the 840 dp Pixel's setup wizard needs for its
            # two-pane layouts (w840dp-h900dp sucTwoPaneLayoutStyle), and text was
            # about 14% over size on this 421 ppi panel. That prop (and
            # ro.config.density_override) is One UI's, so the guest gets a forced
            # density instead, kept per panel in the stage (display_settings.xml,
            # settings_secure): auto = the largest multiple of 20 that keeps the
            # short side at 840 dp (2256 px: 420, 859x954 dp), only if that is at
            # least 90% of the panel's real dpi and under the base density. Set
            # only while display 0 is the inner panel (after a folded start it is
            # the cover: the next session sets it), and never over a size chosen
            # in the guest (display_density_forced set). The cover keeps 480,
            # except after a folded start of a later session: WindowManagerService
            # gives display 0 (then the cover) display_density_forced at boot,
            # until the first lid event applies each panel's own (the fold test
            # logs the density at each event).
            # ONEOS_GUEST_DENSITY=off|auto|<dpi>. Google Calculator stays as it
            # is in portrait (sw600dp layout, as on a real Pixel Fold); its wide
            # pad is landscape-only.
            # Fold line: Pixel's product overlay gives WM Extensions yogi's own
            # hinge, fold-[1038,0,1038,2152], which fails its full-height check
            # here (WindowLayoutComponentImpl, 7 times), so apps saw no
            # FoldingFeature. Settings.Global display_features comes first
            # (RawFoldingFeatureProducer): the inner panel's middle line in its
            # rotation-0 coordinates, fold-[1128,0,1128,2504], with -flat because
            # the guest's hinge state cannot be trusted yet (run 41's fold test:
            # HALF_OPENED 3 s after a flat unfold would give apps a tabletop
            # layout). ONEOS_GUEST_POSTURE=live leaves the posture to the hinge.
            # The cover's 1080x2520 windows fail the full-height check: no feature.
            # Not for ColorOS: its fold pages (Wallpapers grid overlay, compact
            # window mode) were tuned at the density it has, and none of this was
            # seen there.
            if [ \"\$(cat $STAGE/data/oneos_fold_mode 2>/dev/null)\" = layout ] && [ $GUEST_FOLD_FORM = 1 ] && [ $GUEST_OPLUS = 1 ]; then
                echo '[UI Activator] density and fold line: left to ColorOS'
            elif [ \"\$(cat $STAGE/data/oneos_fold_mode 2>/dev/null)\" = layout ] && [ $GUEST_FOLD_FORM = 1 ]; then
                IN=\$(cat $STAGE/data/oneos_inner_display 2>/dev/null)
                case \"\$IN\" in ''|*[!0-9]*) IN=none ;; esac
                # DisplayDeviceInfo{\"Built-in Screen\": uniqueId=\"local:<id>\", 2256 x 2504, ..., density 480, 421.34116 x 421.20264 dpi, ...}
                L=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys display 2>/dev/null | grep -m1 \"DisplayDeviceInfo.*uniqueId=.local:\$IN.,\")
                W=\$(echo \"\$L\" | sed -n 's/.*uniqueId=.local:[0-9]*., \([0-9]*\) x \([0-9]*\), .*/\1/p')
                H=\$(echo \"\$L\" | sed -n 's/.*uniqueId=.local:[0-9]*., \([0-9]*\) x \([0-9]*\), .*/\2/p')
                BD=\$(echo \"\$L\" | sed -n 's/.*, density \([0-9]*\), \([0-9]*\)[.0-9]* x [.0-9]* dpi.*/\1/p')
                XDPI=\$(echo \"\$L\" | sed -n 's/.*, density \([0-9]*\), \([0-9]*\)[.0-9]* x [.0-9]* dpi.*/\2/p')
                if [ -n \"\$W\" ] && [ -n \"\$H\" ] && [ -n \"\$BD\" ] && [ -n \"\$XDPI\" ]; then
                    if [ \$W -lt \$H ]; then S=\$W; else S=\$H; fi
                    D=$GUEST_DENSITY
                    [ \$D = auto ] && D=\$((S * 160 / 840 / 20 * 20))
                    CUR=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get secure display_density_forced 2>/dev/null)
                    AUTO=\$(cat $STAGE/data/oneos_auto_density 2>/dev/null)
                    if [ \$D = off ]; then
                        echo \"[UI Activator] density: left at base \$BD (ONEOS_GUEST_DENSITY=off)\"
                    elif [ -n \"\$CUR\" ] && [ \"\$CUR\" != null ] && [ -n \"\$AUTO\" ] && [ \"\$CUR\" != \"\$AUTO\" ]; then
                        echo \"[UI Activator] density: \$CUR kept (chosen in the guest; this panel wants \$D, base \$BD)\"
                    elif [ -L $STAGE/data/oneos_auto_density ]; then
                        echo \"[UI Activator] density: data/oneos_auto_density is a link, not made by OneOS; left at base \$BD\"
                    elif [ $GUEST_DENSITY = auto ] && { [ \$((D * 10)) -lt \$((XDPI * 9)) ] || [ \$D -ge \$BD ]; }; then
                        echo \"[UI Activator] density: left at base \$BD (inner \${W}x\${H} at \$XDPI dpi too small for 840 dp: \$D)\"
                    elif ! $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm size -d 0 2>/dev/null | grep -q -x \"Physical size: \${W}x\${H}\" && [ $GUEST_VIVO = 0 ]; then
                        echo \"[UI Activator] density: not set, display 0 is not the inner panel (started folded); the next session sets it\"
                    elif ! $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm size -d 0 2>/dev/null | grep -q -x \"Physical size: \${W}x\${H}\"; then
                        # vivo OriginOS started folded (the owner uses it on the cover): at
                        # boot WindowManagerService gave the cover display_density_forced,
                        # the inner panel's (twelfth CN run: cover 420 after every fold),
                        # and a first session left the inner panel at its base 480. The
                        # cover's density OneOS set goes back to its base, and the inner
                        # panel gets its own at the first unfold (each panel keeps its own
                        # in display_settings.xml). A density chosen in the guest stays.
                        CD=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm density -d 0 2>/dev/null | sed -n 's/^Override density: \\([0-9]*\\)$/\\1/p' | head -n 1)
                        if [ -n \"\$CD\" ] && [ \"\$CD\" = \"\$AUTO\" ]; then
                            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm density reset -d 0 >/dev/null 2>&1
                            echo \"[UI Activator] density: started folded, the cover's \$CD (the inner panel's) reset -> \$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm density -d 0 2>&1 | tr '\\n' ' ')\"
                        fi
                        ( i=0
                          while [ \$i -lt 600 ]; do
                              sleep 2; i=\$((i + 1))
                              $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm size -d 0 2>/dev/null | grep -q -x \"Physical size: \${W}x\${H}\" || continue
                              $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm density \$D -d 0 >/dev/null 2>&1
                              echo \$D > $STAGE/data/oneos_auto_density
                              echo \"[UI Activator] density: \$D on the inner panel at the first unfold -> \$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm density -d 0 2>&1 | tr '\\n' ' ')\"
                              exit 0
                          done
                          echo '[UI Activator] density: not unfolded in 20 minutes; the next session sets it' ) &
                    else
                        # The density first: with a leading -d, wm only prints it.
                        $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm density \$D -d 0 >/dev/null 2>&1
                        echo \$D > $STAGE/data/oneos_auto_density
                        echo \"[UI Activator] density: \$D (inner \${W}x\${H}, xdpi \$XDPI, base \$BD, was \${CUR:-unforced}) -> \$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm density -d 0 2>&1 | tr '\n' ' ')\"
                    fi
                    F=\"fold-[\$((W / 2)),0,\$((W / 2)),\$H]\"
                    [ $GUEST_POSTURE_LIVE = 1 ] || F=\"\$F-flat\"
                    CF=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get global display_features 2>/dev/null)
                    [ \"\$CF\" = \"\$F\" ] || $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings put global display_features \"\$F\" 2>/dev/null
                    echo \"[UI Activator] fold line: display_features \$CF -> \$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get global display_features 2>/dev/null)\"
                else
                    echo \"[UI Activator] density and fold line: inner panel \$IN not found in dumpsys display, left alone\"
                fi
            else
                # A bar phone or flip (ONEOS_GUEST_FORM=phone): One UI's dp scale
                # (host_display, from the switch). The guest runs the panel at its
                # full width; One UI's density x physical / One UI's width keeps One
                # UI's dp width there (S25 Ultra at FHD+: 450 x 1440 / 1080 = 600,
                # 384 dp, where the shared 450 gave 512 dp). On a phone One UI runs
                # at full width it is One UI's own density (Screen zoom included).
                # A density chosen in the guest stays: data/oneos_auto_density holds
                # the one OneOS set, a forced density that differs is the user's.
                HUD=\$(sed -n 's/^density=\([0-9]*\) .*/\1/p' $STAGE/host_display 2>/dev/null)
                HW=\$(sed -n 's/.* width=\([0-9]*\) .*/\1/p' $STAGE/host_display 2>/dev/null)
                HP=\$(sed -n 's/.* physical=\([0-9]*\)$/\1/p' $STAGE/host_display 2>/dev/null)
                GW=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm size -d 0 2>/dev/null | sed -n 's/^Physical size: \([0-9]*\)x[0-9]*$/\1/p' | head -n 1)
                case \"\$HUD:\$HW:\$HP:\$GW\" in
                    *[!0-9:]*|:*|*::*|*:)
                        echo \"[UI Activator] density: One UI's scale not recorded (\${HUD:-?} at \${HW:-?} of \${HP:-?} px, guest \${GW:-?} px), left at base\" ;;
                    *)
                        D=\$(( (HUD * GW + HW / 2) / HW ))
                        CUR=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get secure display_density_forced 2>/dev/null)
                        AUTO=\$(cat $STAGE/data/oneos_auto_density 2>/dev/null)
                        if [ \$GW != \$HP ]; then
                            echo \"[UI Activator] density: guest display 0 is \$GW px wide, One UI's panel \$HP px; left at base\"
                        elif [ $GUEST_OPLUS = 1 ]; then
                            # ColorOS's Settings puts its Display size back at every boot
                            # (SettingsReceiver -> restoreScreenZoomSettings): the entry at
                            # Settings.System display_density_index_manual in settingslib's list
                            # around the base density (Small at 0.85x, Default, up to three steps
                            # to 1.5x or 320 dp, each rounded down to an even dpi), unless the
                            # density already is that entry. One UI's exact scale is off that list,
                            # so it was undone at the next boot and set again by this (0.4.55
                            # reports: the size changed at every boot, whatever was chosen). OneOS
                            # takes the entry nearest One UI's scale and saves its index (and in
                            # data/oneos_auto_density_index); an index saved since is the user's
                            # (the Display size slider) and stays. Before 0.4.57 there was no
                            # index file: an unset index or Default's counts as not chosen.
                            GH=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm size -d 0 2>/dev/null | sed -n 's/^Physical size: [0-9]*x\([0-9]*\)$/\1/p' | head -n 1)
                            BD=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm density -d 0 2>/dev/null | sed -n 's/^Physical density: \([0-9]*\)$/\1/p' | head -n 1)
                            MAN=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get system display_density_index_manual 2>/dev/null)
                            case \"\$MAN\" in ''|*[!0-9]*) MAN= ;; esac
                            MARK=\$(cat $STAGE/data/oneos_auto_density_index 2>/dev/null)
                            # \"<Default's index> <nearest index> <its dpi> <list>\"
                            ZL=\$(awk -v b=\"\$BD\" -v w=\"\$GW\" -v h=\"\$GH\" -v d=\"\$D\" 'BEGIN {
                                if (b !~ /^[0-9]+\$/ || w !~ /^[0-9]+\$/ || h !~ /^[0-9]+\$/ || b + 0 == 0) exit
                                m = (w + 0 < h + 0) ? w : h
                                mx = int(160 * m / 320) / b; if (mx > 1.5) mx = 1.5; if (mx < 1) mx = 1
                                nl = int((mx - 1) / 0.09); if (nl > 3) nl = 3
                                n = 0; v[n++] = int(b * 0.85 + 0.001); v[0] -= v[0] % 2
                                v[n++] = b + 0
                                for (i = 1; i <= nl; i++) { x = int(b * (1 + i * (mx - 1) / nl) + 0.001); v[n++] = x - x % 2 }
                                k = 0; for (i = 1; i < n; i++) if ((v[i] - d) ^ 2 < (v[k] - d) ^ 2) k = i
                                s = v[0]; for (i = 1; i < n; i++) s = s \",\" v[i]
                                print 1, k, v[k], s
                            }')
                            DI=\$(echo \"\$ZL\" | cut -d' ' -f1); K=\$(echo \"\$ZL\" | cut -d' ' -f2); VK=\$(echo \"\$ZL\" | cut -d' ' -f3); ZS=\$(echo \"\$ZL\" | cut -d' ' -f4)
                            EFF=\$CUR; case \"\$EFF\" in ''|null|*[!0-9]*) EFF=\$BD ;; esac
                            if [ -z \"\$ZL\" ]; then
                                echo \"[UI Activator] density: ColorOS Display size list not worked out (base \${BD:-?}, \${GW}x\${GH:-?}), left as it is\"
                            elif [ -n \"\$MAN\" ] && { { [ -n \"\$MARK\" ] && [ \"\$MAN\" != \"\$MARK\" ]; } || { [ -z \"\$MARK\" ] && [ \"\$MAN\" != \"\$DI\" ]; }; }; then
                                echo \"[UI Activator] density: \$EFF kept (Display size \$MAN of \$ZS chosen in ColorOS; One UI's scale gives \$D)\"
                            elif [ \$D -lt 120 ] || [ \$D -gt 640 ]; then
                                echo \"[UI Activator] density: \$D from One UI's scale is outside 120-640, left as it is\"
                            elif [ -L $STAGE/data/oneos_auto_density ] || [ -L $STAGE/data/oneos_auto_density_index ]; then
                                echo \"[UI Activator] density: data/oneos_auto_density(_index) is a link, not made by OneOS; left as it is\"
                            else
                                $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings put system display_density_index_manual \$K 2>/dev/null
                                echo \$K > $STAGE/data/oneos_auto_density_index
                                echo \$VK > $STAGE/data/oneos_auto_density
                                [ \"\$EFF\" = \"\$VK\" ] || $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm density \$VK -d 0 >/dev/null 2>&1
                                echo \"[UI Activator] density: \$VK, Display size \$K of \$ZS (One UI \$HUD at \$HW of \$HP px gives \$D; was \$EFF, index \${MAN:-unset}) -> \$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm density -d 0 2>&1 | tr '\n' ' ')\"
                            fi
                        elif [ -n \"\$CUR\" ] && [ \"\$CUR\" != null ] && [ \"\$CUR\" != \"\$AUTO\" ]; then
                            echo \"[UI Activator] density: \$CUR kept (chosen in the guest; One UI's scale gives \$D)\"
                        elif [ \$D -lt 120 ] || [ \$D -gt 640 ]; then
                            echo \"[UI Activator] density: \$D from One UI's scale is outside 120-640, left at base\"
                        elif [ -L $STAGE/data/oneos_auto_density ]; then
                            echo \"[UI Activator] density: data/oneos_auto_density is a link, not made by OneOS; left at base\"
                        else
                            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm density \$D -d 0 >/dev/null 2>&1
                            echo \$D > $STAGE/data/oneos_auto_density
                            echo \"[UI Activator] density: \$D (One UI \$HUD at \$HW of \$HP px, \$((HW * 160 / HUD)) dp; was \${CUR:-unforced}) -> \$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm density -d 0 2>&1 | tr '\n' ' ')\"
                        fi ;;
                esac
            fi
            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/input keyevent 224
            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/input keyevent 82
            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/am unlock-user 0
            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/am start -a android.intent.action.MAIN -c android.intent.category.HOME
            # Setup is marked done before boot (guest_prepare.sh), so ColorOS shows
            # its swipe keyguard; there is no credential in the guest.
            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm dismiss-keyguard 2>/dev/null || true
            # The guest's updaters could hand an OTA to the phone's own
            # update_engine: ColorOS's, Pixel's factory OTA and Infinity-X's
            # Updater.
            for p in com.oplus.ota com.google.android.factoryota com.infinity.updater; do
                $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm disable-user --user 0 \$p >/dev/null 2>&1 || true
            done
            # Cover panel. With the fold layout (guest_start.sh wrote
            # data/oneos_fold_mode) ColorOS's DisplayManager switches the panels
            # on the lid switch and keeps the cover off while unfolded: only log
            # what it chose. Without it the cover only mirrors the inner panel
            # and its touches go nowhere: switch it off. The inner panel is display 0.
            if [ \"\$(cat $STAGE/data/oneos_fold_mode 2>/dev/null)\" = layout ]; then
                echo \"[UI Activator] fold layout: \$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd device_state print-state 2>&1 | head -1); \$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys display 2>/dev/null | grep -m1 -o 'mCurrentLayout=.*' | cut -c1-300)\"
                # What folding does (Settings > Foldable features > Screen switching,
                # system continue_using_apps_when_folded): 0 = swipe up to continue,
                # ColorOS's default, 1 = continue using, 2 = turn screen off. With 0
                # the cover asks for a swipe and locks after 3 s, and cover touch is
                # dead (run 31: cover_touch_N.txt empty), so a fold ends on a locked
                # cover; the user switched to continue using by hand at 12:03. A
                # stage set to 2 keeps it. ONEOS_GUEST_FOLD_CONTINUE=0 leaves it alone.
                # AOSP (Pixel): system fold_lock_behavior_setting, stay_awake_on_fold_key
                # = continue using, selective_stay_awake_key = swipe up (set like
                # ColorOS's 0), sleep_on_fold_key kept like ColorOS's 2.
                if [ $GUEST_OPLUS = 1 ]; then FOLDN=continue_using_apps_when_folded; else FOLDN=fold_lock_behavior_setting; fi
                FOLDK=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get system \$FOLDN 2>/dev/null)
                case \"${ONEOS_GUEST_FOLD_CONTINUE:-1}:\$FOLDN:\$FOLDK\" in
                    0:*|1:continue_using_apps_when_folded:1|1:continue_using_apps_when_folded:2|1:fold_lock_behavior_setting:stay_awake_on_fold_key|1:fold_lock_behavior_setting:sleep_on_fold_key) ;;
                    1:continue_using_apps_when_folded:*) $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings put system continue_using_apps_when_folded 1 2>/dev/null ;;
                    *) $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings put system fold_lock_behavior_setting stay_awake_on_fold_key 2>/dev/null ;;
                esac
                echo \"[UI Activator] fold behaviour: \$FOLDN \$FOLDK -> \$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get system \$FOLDN 2>/dev/null)\"
            else
                for id in \$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys display 2>/dev/null | grep -o 'type=INTERNAL, valid=true, isActive=true, displayId=[0-9]*' | grep -o '[0-9]*\$' | sort -u); do
                    [ \"\$id\" = 0 ] && continue
                    $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd display disable-display \$id 2>/dev/null && echo \"[UI Activator] cover display \$id switched off\"
                done
            fi
            # HyperOS's home wallpaper (run 10: only the lock screen took a new
            # one). Until the first fold state commits, about 4 s after
            # MiWallpaper binds, the display mapper shows the cover as a second
            # display (#7); when it closes, MiWallpaper's EngineServiceManager
            # drops the home engines (1 and the cover's 4) with it, and every
            # later apply finds none (requireEngineService returns null).
            # Once display 0 is the only active built-in one, its process is
            # restarted once: WallpaperManagerService rebinds a wallpaper that
            # died (it reverts to the built-in one only after a second death
            # within 10 s, or a low-memory kill) and the engines register again.
            if [ $GUEST_MIUI = 1 ]; then
                n=0
                while [ \$n -lt 30 ]; do
                    $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys display 2>/dev/null |
                        grep -o 'type=INTERNAL, valid=true, isActive=true, displayId=[0-9]*' | grep -q -v 'displayId=0\$' || break
                    n=\$((n + 1)); sleep 1
                done
                WP=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pidof com.miui.miwallpaper 2>/dev/null)
                case \"\$WP\" in
                    ''|*[!0-9]*) echo \"[UI Activator] MiWallpaper: not running (\${WP:-no pid}), left alone\" ;;
                    *)
                        kill \$WP 2>/dev/null
                        n=0; NWP=
                        while [ \$n -lt 15 ]; do
                            sleep 1; n=\$((n + 1))
                            NWP=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pidof com.miui.miwallpaper 2>/dev/null)
                            [ -n \"\$NWP\" ] && [ \"\$NWP\" != \"\$WP\" ] && break
                        done
                        echo \"[UI Activator] MiWallpaper restarted once for its home engines: pid \$WP -> \${NWP:-none after 15 s}\"
                        ;;
                esac
            fi
            # Brightness below ColorOS's minimum level (a fresh stage has 102):
            # its default, about 135 nits with the Samsung panel curve.
            # ColorOS's scale only (AOSP's screen_brightness is 0..255).
            if [ $GUEST_OPLUS = 1 ]; then
            b=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get system screen_brightness 2>/dev/null)
            [ \"\${b%%.*}\" -ge 222 ] 2>/dev/null || $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings put system screen_brightness 4570
            # Once with the fixed panel curve: the saved value was chosen while the
            # curve was wrong (run 28: 1702 looked like ~420 nits, is ~15).
            [ -f $STAGE/data/.oneos_curve2 ] || { $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings put system screen_brightness 4570; touch $STAGE/data/.oneos_curve2; }
            fi
            echo \"[UI Activator] refresh: min \$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get system min_refresh_rate) peak \$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get system peak_refresh_rate); brightness \$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get system screen_brightness)\"
            echo '[UI Activator] Home activated!'
            # ColorOS lock screen depth effect (0.4.60, owner; 0.4.59 A36 768c5a1d, S23
            # 77b9dfc0): SystemUI saves the cut-out subject as /data/oplus/os/deep_scenery_image*,
            # but that folder is system's and SystemUI runs as an app uid here (EACCES, \"can
            # not show deep scenery\"). The Fold8 port's fix (fold8_coloros.sh) for every
            # ColorOS: the folder searchable, the two files SystemUI's own. Links left alone.
            # The exact package (0.4.63): list packages matches by substring, and the first
            # line was another com.android.systemui.* package (A56 fda1b80b: files given to
            # uid 15004, SystemUI ran as 15142, its save still EACCES).
            if [ $GUEST_OPLUS = 1 ]; then
                su_uid=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd package list packages -U com.android.systemui 2>/dev/null | sed -n 's/^package:com[.]android[.]systemui uid://p' | head -1 | tr -dc 0-9)
                depth=$STAGE/data/oplus/os
                if [ -n \"\$su_uid\" ] && [ -d \$depth ] && [ ! -L \$depth ] && [ ! -L $STAGE/data/oplus ]; then
                    chmod 701 \$depth
                    for n in deep_scenery_image0 deep_scenery_image_secondaryDisplay0; do
                        [ ! -L \$depth/\$n ] || continue
                        [ -f \$depth/\$n ] || : > \$depth/\$n
                        $BB chown -h \$su_uid:\$su_uid \$depth/\$n && chmod 600 \$depth/\$n
                    done
                    echo \"[UI Activator] depth effect: \$depth/deep_scenery_image* for SystemUI (uid \$su_uid)\"
                else
                    echo \"[UI Activator] depth effect: left alone (SystemUI uid '\$su_uid', \$depth)\"
                fi
            fi
            # Google Dialer and Nearby devices (run 44): 50 SecurityExceptions
            # (DialerAudioModeProvider, getRemoteAlias: Need
            # android.permission.BLUETOOTH_CONNECT) in the first call, until the
            # owner allowed it in a dialog in the middle of that call. Granted
            # once per stage (a marker in the guest's data, like the blur
            # default), so a later choice in the guest stays. Not BLUETOOTH_SCAN:
            # nothing in run 44 asked for it. Pixel guests only; the guest's own
            # package manager, nothing of One UI's. After HOME: it does not hold
            # up the first screen, and no call comes that early. The marker is
            # made and checked like the blur one (mkdir, -e and -L).
            if [ $GUEST_OPLUS = 0 ]; then
                DST=''
                if [ -L $STAGE/data/oneos_dialer_bt ]; then
                    DST='data/oneos_dialer_bt is a link, not made by OneOS; nothing granted'
                elif [ -e $STAGE/data/oneos_dialer_bt ]; then
                    DST='granted on an earlier boot of this stage, left to the guest'
                elif ! timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm path com.google.android.dialer >/dev/null 2>&1; then
                    DST='com.google.android.dialer not installed (or pm path did not answer in 20 s), nothing granted'
                elif DR=\$(timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm grant --user 0 com.google.android.dialer android.permission.BLUETOOTH_CONNECT 2>&1); then
                    mkdir $STAGE/data/oneos_dialer_bt 2>/dev/null
                    DST='BLUETOOTH_CONNECT granted (once per stage)'
                else
                    DST=\"pm grant BLUETOOTH_CONNECT failed: \$(echo \"\$DR\" | tr '\n' ' ' | cut -c1-200)\"
                fi
                echo \"[UI Activator] dialer: \$DST; now \$(timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys package com.google.android.dialer 2>/dev/null | grep -m 1 -o 'android.permission.BLUETOOTH_CONNECT: granted=[a-z]*' || echo 'BLUETOOTH_CONNECT state not read')\"
            fi
            # Nothing's Gallery (com.nothing.gallery) opens only with read-media
            # and media management (MANAGE_MEDIA app-op) granted, which a Nothing
            # phone grants its own gallery up front; here it said \"either not a
            # pre-installed application or not running on Nothing device\" and
            # stopped (run 15). Granted once per stage, like the dialer's.
            if [ -L $STAGE/data/oneos_ntgallery ]; then
                echo '[UI Activator] Nothing Gallery: data/oneos_ntgallery is a link, not made by OneOS; nothing granted'
            elif [ ! -e $STAGE/data/oneos_ntgallery ] &&
                 timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm path com.nothing.gallery >/dev/null 2>&1; then
                GR=''
                for perm in READ_MEDIA_IMAGES READ_MEDIA_VIDEO ACCESS_MEDIA_LOCATION; do
                    timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm grant --user 0 com.nothing.gallery android.permission.\$perm >/dev/null 2>&1 && GR=\"\$GR \$perm\"
                done
                timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/appops set --user 0 com.nothing.gallery MANAGE_MEDIA allow >/dev/null 2>&1 && GR=\"\$GR MANAGE_MEDIA\"
                mkdir $STAGE/data/oneos_ntgallery 2>/dev/null
                echo \"[UI Activator] Nothing Gallery: granted\${GR:- nothing} (once per stage)\"
            fi
            # Samsung Camera (samcam.tar): One UI grants its own camera these up
            # front. In a fresh ColorOS guest it asked for nothing and kept a black
            # preview (\"isEngineStartAvailable : Can't start Engine - failed to
            # grant permissions\"; F8U, Find N6 global, 0.4.38). Camera,
            # microphone, media and notifications, once per stage; not location
            # (geotags stay the user's choice).
            if [ -L $STAGE/data/oneos_samcam_perms ]; then
                echo '[UI Activator] Samsung Camera: data/oneos_samcam_perms is a link, not made by OneOS; nothing granted'
            elif [ ! -e $STAGE/data/oneos_samcam_perms ] &&
                 timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm path com.sec.android.app.camera >/dev/null 2>&1; then
                GR=''
                for perm in CAMERA RECORD_AUDIO READ_MEDIA_IMAGES READ_MEDIA_VIDEO READ_MEDIA_AUDIO POST_NOTIFICATIONS; do
                    timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm grant --user 0 com.sec.android.app.camera android.permission.\$perm >/dev/null 2>&1 && GR=\"\$GR \$perm\"
                done
                mkdir $STAGE/data/oneos_samcam_perms 2>/dev/null
                echo \"[UI Activator] Samsung Camera: granted\${GR:- nothing} (once per stage)\"
            fi
            # Nothing's Settings shows the phone's own RAM and storage in About
            # phone only on Nothing's phones (Build.DEVICE Spacewar or Pong, or
            # its bool screen_size_for_mp); anywhere else its strings def_ram and
            # def_rom, 8GB and 128GB (run 15 on the 12 GB / 512 GB Fold8 Ultra).
            # Fabricated over them: this phone's sizes as the box gives them, RAM
            # from MemTotal up to the next usual size, storage from /data up to a
            # power of two. Re-made every session. ONEOS_GUEST_NT_ABOUT=0 leaves
            # Nothing's strings.
            if [ \"${ONEOS_GUEST_NT_ABOUT:-1}\" = 1 ] &&
               timeout 10 $BB nsenter -t \$PID -m /system/bin/sh -c '[ -f /system_ext/priv-app/NothingSettings/NothingSettings.apk ]' 2>/dev/null; then
                NRAM=\$(awk '/^MemTotal:/ { g = \$2 / 1048576; n = split(\"4 6 8 12 16 24 32 48 64\", s, \" \"); for (i = 1; i <= n; i++) if (s[i] + 0 >= g) { print s[i] \"GB\"; exit } }' /proc/meminfo)
                NROM=\$($BB df -k /data 2>/dev/null | awk 'NR == 2 { g = \$2 / 1000000; p = 16; while (p < g) p *= 2; if (p >= 1024) print p / 1024 \"TB\"; else print p \"GB\" }')
                # With the About overlay's own-phone mode (guest_props.sh wrote
                # nt_about.txt): the inner panel's diagonal for the screen line
                # (else display 0's, the cover when folded) and the battery's
                # design capacity (else the image's power profile).
                NSCR=\$(sed -n 's/^screen=\([0-9.]*\)\$/\1/p' $STAGE/nt_about.txt 2>/dev/null | head -n 1)
                NMAH=\$(sed -n 's/^battery=\([0-9]*\)\$/\1/p' $STAGE/nt_about.txt 2>/dev/null | head -n 1)
                NON=''
                for spec in \"OneOSNtRam:def_ram:\$NRAM\" \"OneOSNtRom:def_rom:\$NROM\" \"OneOSNtScreen:screen_physical_size:\$NSCR\" \"OneOSNtBattery:about_phone_hardware_battery_capacity_unit:\${NMAH:+\$NMAH mAh}\"; do
                    v=\${spec##*:}; [ -n \"\$v\" ] || continue
                    n=\${spec%%:*}; r=\${spec#*:}; r=\${r%%:*}
                    timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd overlay fabricate --target com.android.settings --name \$n com.android.settings:string/\$r string \"\$v\" >/dev/null 2>&1 &&
                    timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd overlay enable --user 0 com.android.shell:\$n >/dev/null 2>&1 && NON=\"\$NON \$r=\$v\"
                done
                # Nothing's ringtones were left half made by the sessions before
                # the generator's fixes (runs 16-18: 3 of 10, no haptic tracks),
                # and it takes a finished first boot as done. With no haptic
                # track yet, Nothing's own regenerate request, 30 s after HOME.
                NTG=$STAGE/data/media/0/NTGenerateRingtone
                if [ -d \$NTG ] && [ -z \"\$(ls \$NTG/GenerateVibr 2>/dev/null)\" ]; then
                    ( sleep 30; timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/am broadcast -a com.nothing.settings.nt_generative_ringtone_reset -n com.nothing.generateringtoneservice/.BootReceiver >/dev/null 2>&1 && echo \"[UI Activator] Nothing ringtones: regenerate requested (no haptic tracks yet)\" ) </dev/null &
                fi
                # Nothing's launcher on the inner panel (run 16): one phone-wide
                # column of icons, no room at the sides, and the drawer's search
                # bar under the navigation handle. Its own dump (DeviceProfile:
                # two panels, grid, insets, taskbar) 40 s after HOME, folded or
                # not, to diag_launcher.txt.
                ( sleep 40; timeout 15 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys activity com.nothing.launcher > $STAGE/diag_launcher.txt 2>&1 ) </dev/null >/dev/null 2>&1 &
                # The power key's double press (Essential Space, run 24: nothing
                # opened): the policy's multi-press behavior and target, the
                # overlays on android, 20 s after HOME (sessions can be a minute), to diag_power.txt.
                ( sleep 20; {
                      timeout 15 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys window policy 2>&1 | grep -i -E 'press|power|gesture|target' | head -n 40
                      echo '== overlays (android)'
                      timeout 15 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd overlay list android 2>&1 | head -n 40
                      echo '== camera gesture settings'
                      for k in camera_double_tap_power_gesture_disabled double_tap_power_button_gesture_enabled double_tap_power_button_gesture; do
                          echo \"\$k=\$(timeout 10 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get secure \$k 2>&1)\"
                      done
                  } > $STAGE/diag_power.txt 2>&1 ) </dev/null >/dev/null 2>&1 &
                # One UI's cameraserver waits 5 s in every connect (runs 19-21,
                # every app), right after its lookups of these services; the
                # worker and the Knox stand-in both answer. Each name checked from
                # One UI's side (the cameraserver's) and the guest's, timed, 45 s
                # after HOME, to diag_camsvc.txt.
                ( sleep 45; for n in activity appops permission processinfo sensor_privacy media.camera.proxy media.camera.worker edmnativehelper media.camera; do
                      t0=\$(date +%s%N); h=\$(timeout 8 /system/bin/service check \$n 2>&1 | tr -d '\n'); t1=\$(date +%s%N)
                      g=\$(timeout 8 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/service check \$n 2>&1 | tr -d '\n'); t2=\$(date +%s%N)
                      echo \"\$n | host \$(( (t1 - t0) / 1000000 )) ms: \$h | guest \$(( (t2 - t1) / 1000000 )) ms: \$g\"
                  done > $STAGE/diag_camsvc.txt 2>&1 ) </dev/null >/dev/null 2>&1 &
                # Samsung Camera's libraries as the guest's package manager has them
                # (ColorOS on the S25+: ClassNotFoundException oneos.semcompat.Sem,
                # the compat library declared and read; report 6ddd6a87), 50 s
                # after HOME, to diag_samcam.txt. Read-only.
                if [ -d $STAGE/samcam_build ]; then
                    ( sleep 50; {
                        timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys package com.sec.android.app.camera 2>&1 | grep -A14 -E 'usesLibraries|usesOptionalLibraries|usesLibraryFiles|usesLibraryInfos|sharedLibrar'
                        echo '== library declarations'
                        timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys package libraries 2>&1 | grep -E 'worker_wrapper_compat|semextendedformat|secimaging'
                        echo '== files'
                        timeout 10 $BB nsenter -t \$PID -m /system/bin/sh -c 'ls -laZ /system_ext/framework/oneos-camera-compat.jar /system_ext/framework/semextendedformat.jar /system_ext/framework/secimaging.jar' 2>&1
                      } > $STAGE/diag_samcam.txt 2>&1 ) </dev/null >/dev/null 2>&1 &
                fi
                # With a staged OneOSDisplayProbe.dex (patches/OneOSDisplayProbe.java,
                # diagnostics only): the default display's possible sizes as the
                # launcher gets them, from 15 s after HOME, five times 30 s apart (folded and not).
                if [ -f $STAGE/OneOSDisplayProbe.dex ] && [ ! -L $STAGE/data/oneos_display_probe.dex ]; then
                    cp -f $STAGE/OneOSDisplayProbe.dex $STAGE/data/oneos_display_probe.dex && chmod 644 $STAGE/data/oneos_display_probe.dex
                    ( sleep 15; for i in 1 2 3 4 5; do echo \"== \$(date +%T) device state \$(timeout 10 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd device_state print-state 2>&1 | tr '\n' ' ')\"; timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/env CLASSPATH=/data/oneos_display_probe.dex /system/bin/app_process /system/bin OneOSDisplayProbe 2>&1 | cut -c1-900; sleep 30; done > $STAGE/diag_displays.txt ) </dev/null >/dev/null 2>&1 &
                fi
                echo \"[UI Activator] Nothing About phone: RAM \${NRAM:-?}, storage \${NROM:-?}, screen \${NSCR:-?}, battery \${NMAH:-?} mAh; overlays on:\${NON:- none}\"
            fi
            # This phone's cutout, status bar height and corner radius (the switch
            # saved them in host_statusbar, phones with one panel). Infinity-X got
            # none of them before (GUEST_OPLUS): on the S25 Ultra its cutout and
            # corners were empty, the icons off.
            # Every system takes the cutout since 0.4.58. ColorOS and HyperOS kept
            # their image's phone's: the Find X9 Ultra's 0..160 px rect (a 160 px
            # bar where One UI's is 128 on the S25 Ultra and 101 on the A56) and the
            # Xiaomi's top-left 164 x 140 px one (A56, HyperOS f73b6e6f: \"M 0,0 H 164
            # V 140 H 0 V 0 Z @left\", the clock right of x 164). ColorOS's own
            # SystemUI still places its icons and capsule from
            # ro.oplus.display.screenhole.positon (guest_props.sh).
            # Fabricated overlays are mutable: enabled, they come above every
            # static overlay, the image's device ones in product included. The
            # guest's DisplayManager takes the cutout and corners again on the
            # overlay change and SystemUI the height; later sessions start with
            # them. Re-made every session (a resolution change moves the height).
            # ONEOS_GUEST_HOST_CUTOUT=0 leaves them out, and disables those an
            # earlier session made.
            gxo() { timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd overlay \"\$@\" >/dev/null 2>&1; }
            gdim() { timeout 30 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/env CLASSPATH=/data/oneos_overlay_dimen.dex /system/bin/app_process /system/bin OneOSOverlayDimen \"\$@\" 2>&1 | grep -E '^(registered|failed)' | tail -n 1; }
            # The corner radius for the guests the block below leaves out (0.4.76,
            # host_corner_radius; see where the switch saves it): ColorOS on any
            # phone, every guest on a Fold. Made after the block.
            CRAD=''
            if [ \"${ONEOS_GUEST_HOST_CUTOUT:-1}\" = 1 ] && [ -f $STAGE/host_corner_radius ] && [ ! -L $STAGE/host_corner_radius ] &&
               [ -f $STAGE/data/oneos_overlay_dimen.dex ] && { [ \"$GUEST_AOSP_SYSUI$GUEST_MIUI\" = 00 ] || [ $GUEST_FOLD_FORM = 1 ]; }; then
                CRAD=\$(head -n 1 $STAGE/host_corner_radius)
                case \"\$CRAD\" in ''|*[!0-9]*) CRAD='' ;; esac
            fi
            if [ \"${ONEOS_GUEST_HOST_CUTOUT:-1}\" = 1 ] && [ -f $STAGE/host_statusbar ] && [ ! -L $STAGE/host_statusbar ]; then
                HCS=\$(sed -n 's/^spec=//p' $STAGE/host_statusbar | head -n 1)
                # The cutout in pixels of the whole panel when the switch made it
                # (rect_px: One UI's rect, hole_px: the lens in it; host_holes): One
                # UI's @dp spec is worked out in a guest at the shared
                # ro.sf.lcd_density, on an Ultra the FHD+ 450 on the 1440 px panel,
                # 3/4 of the camera (S24 Ultra, Nothing OS 3066a57c: 695,0:746,96
                # for One UI's 686,0:754,128). ONEOS_GUEST_CUTOUT_PX=0 keeps the
                # @dp spec as below.
                HRP=\$(sed -n 's/^rect_px=//p' $STAGE/host_statusbar | head -n 1)
                HHP=\$(sed -n 's/^hole_px=//p' $STAGE/host_statusbar | head -n 1)
                # One UI gives the punch hole as a rectangle from the top edge
                # to the camera's bottom (M 0,0 H -a V b H a V 0 H 0 Z @dp): its own
                # SystemUI only spaces by it. Nothing OS's draws the cutout, and a
                # rectangle from the top down to the camera showed on the S24, S25
                # and S26 Ultras (0.4.36 reports 81f8194c, 8d299b5f, c90a0f14). The
                # cutout is the circle of the rectangle's width at its bottom (the
                # hole); the rect approximation stays One UI's.
                # ONEOS_GUEST_CUTOUT_ROUND=0 keeps One UI's rectangle for both.
                HCSC=\$HCS
                if [ \"${ONEOS_GUEST_CUTOUT_ROUND:-1}\" = 1 ]; then
                    HCSC=\$(printf '%s\\n' \"\$HCS\" | awk '{ n = split(\$0, t, \" \") } n == 14 && t[1] == \"M\" && t[2] == \"0,0\" && t[3] == \"H\" && t[5] == \"V\" && t[7] == \"H\" && t[14] == \"@dp\" { a = t[8] + 0; b = t[6] + 0; if (a > 0 && b >= 2 * a) { printf \"M 0,%.4f a %.4f,%.4f 0 1,0 0,%.4f a %.4f,%.4f 0 1,0 0,-%.4f Z @dp\", b - 2 * a, a, a, 2 * a, a, a, 2 * a; next } } { print }')
                    [ -n \"\$HCSC\" ] || HCSC=\$HCS
                fi
                CUT=\$HCSC CUTR=\$HCS CUTU=dp
                if [ \"${ONEOS_GUEST_CUTOUT_PX:-1}\" = 1 ] && [ -n \"\$HRP\" ] && [ -n \"\$HHP\" ]; then
                    CUT=\$HHP CUTR=\$HRP CUTU=px
                    [ \"${ONEOS_GUEST_CUTOUT_ROUND:-1}\" = 1 ] || CUT=\$HRP
                fi
                case \"\$CUT\$CUTR\" in *[!-0-9A-Za-z._,@\\ ]*) CUT='' CUTR='' ;; esac
                HSB=\$(sed -n 's/^height=//p' $STAGE/host_statusbar | head -n 1)
                HRC=\$(sed -n 's/^radius=//p' $STAGE/host_statusbar | head -n 1)
                OVS=''
                if [ -n \"\$CUT\" ] && [ -n \"\$CUTR\" ] &&
                   gxo fabricate --target android --name OneOSCutout android:string/config_mainBuiltInDisplayCutout string \"\$CUT\" &&
                   gxo fabricate --target android --name OneOSCutoutRect android:string/config_mainBuiltInDisplayCutoutRectApproximation string \"\$CUTR\"; then
                    OVS='OneOSCutout OneOSCutoutRect'
                fi
                # Height, corner radius and the corner padding are dimensions,
                # which cmd overlay fabricate cannot make (integer types 16-31
                # only: \"dataType is out of range\"), so up to 0.4.32 they failed
                # on every phone and only the cutout applied (A56 Pixel session
                # 5d1d3007: a 92 px bar for One UI's 101, the clock 30 px from a
                # 118 px corner). OneOSOverlayDimen (patches/, in the guest's
                # /data) registers them; enabled like the rest. Bar phones only:
                # on a Fold the switch measured whichever panel was on, and one
                # value would be wrong on the other. AOSP SystemUI and HyperOS's
                # (its bar 140 px and corners 142 px on the A56, f73b6e6f); ColorOS
                # sizes its bar from the hole property.
                DIMS=''
                if [ \"$GUEST_AOSP_SYSUI$GUEST_MIUI\" != 00 ] && [ $GUEST_FOLD_FORM = 0 ] && [ -f $STAGE/data/oneos_overlay_dimen.dex ]; then
                    case \"\$HSB\" in
                        ''|*[!0-9]*) ;;
                        *) r=\$(gdim OneOSStatusBarHeight android android:dimen/status_bar_height_default=\$HSB android:dimen/status_bar_height_portrait=\$HSB)
                           case \"\$r\" in registered*) OVS=\"\$OVS OneOSStatusBarHeight\" ;; *) DIMS=\"\$DIMS height: \$r;\" ;; esac ;;
                    esac
                    case \"\$HRC\" in
                        ''|*[!0-9]*) ;;
                        *) r=\$(gdim OneOSCornerRadius android android:dimen/rounded_corner_radius=\$HRC android:dimen/rounded_corner_radius_top=\$HRC android:dimen/rounded_corner_radius_bottom=\$HRC)
                           case \"\$r\" in registered*) OVS=\"\$OVS OneOSCornerRadius\" ;; *) DIMS=\"\$DIMS radius: \$r;\" ;; esac
                           # Where the corner's curve leaves the status bar's icons
                           # room: at a third of the bar's height (the top of the
                           # clock's digits). Only over the 8dp the static RRO
                           # gives (24 px), both sides alike. AOSP SystemUI only.
                           PAD=\$(awk -v r=\"\$HRC\" -v h=\"\${HSB:-0}\" 'BEGIN { y = h / 3; p = 0; if (y < r) p = r - sqrt(r * r - (r - y) * (r - y)); printf \"%d\", p + 0.5 }')
                           if [ $GUEST_AOSP_SYSUI = 1 ] && [ \"\${PAD:-0}\" -gt 24 ]; then
                               r=\$(gdim OneOSCornerPadding com.android.systemui com.android.systemui:dimen/rounded_corner_content_padding=\$PAD com.android.systemui:dimen/ongoing_appops_dot_min_padding=\$PAD)
                               case \"\$r\" in registered*) OVS=\"\$OVS OneOSCornerPadding\" ;; *) DIMS=\"\$DIMS padding \$PAD px: \$r;\" ;; esac
                           fi ;;
                    esac
                fi
                ON=''
                for o in \$OVS; do gxo enable --user 0 com.android.shell:\$o && ON=\"\$ON \$o\"; done
                echo \"[UI Activator] status bar: One UI's cutout '\${HCS:-none}', as \$CUTU: '\${CUT:-none}', rect '\${CUTR:-none}'; height \${HSB:-?} px, corner radius \${HRC:-?} px; overlays on:\${ON:- none}\${DIMS:+ (not made:\$DIMS)}\"
            else
                # No host cutout this session (ONEOS_GUEST_HOST_CUTOUT=0, or a
                # phone with two panels): an earlier session's overlays go off.
                OFF=''
                for o in \$(timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd overlay list --user 0 2>/dev/null | sed -n 's/^.*\\[x\\] com\\.android\\.shell:\\(OneOS[A-Za-z]*\\)\$/\\1/p' | sort -u); do
                    case \$o in
                        OneOSCornerRadius) [ -n \"\$CRAD\" ] && continue
                            gxo disable --user 0 com.android.shell:\$o && OFF=\"\$OFF \$o\" ;;
                        OneOSCutout|OneOSCutoutRect|OneOSStatusBarHeight|OneOSCornerPadding)
                            gxo disable --user 0 com.android.shell:\$o && OFF=\"\$OFF \$o\" ;;
                    esac
                done
                [ -z \"\$OFF\" ] || echo \"[UI Activator] status bar: no host cutout this session; overlays off:\$OFF\"
            fi
            if [ -n \"\$CRAD\" ]; then
                r=\$(gdim OneOSCornerRadius android android:dimen/rounded_corner_radius=\$CRAD android:dimen/rounded_corner_radius_top=\$CRAD android:dimen/rounded_corner_radius_bottom=\$CRAD)
                case \"\$r\" in
                    registered*) if gxo enable --user 0 com.android.shell:OneOSCornerRadius; then
                                     echo \"[UI Activator] corner radius: this phone's \$CRAD px for the guest's windows (overlay OneOSCornerRadius on)\"
                                 else
                                     echo \"[UI Activator] corner radius: !!! OneOSCornerRadius (\$CRAD px) registered but not enabled\"
                                 fi ;;
                    *) echo \"[UI Activator] corner radius: !!! not made (\$CRAD px): \${r:-no answer}\" ;;
                esac
            fi
            # AOD (Pixel on the Z Fold8 Ultra, 0.4.59 test): a Pixel names its doze
            # service and \"AOD available\" in its vendor overlay, and a guest runs on
            # One UI's vendor, so the guest's dream manager had getDozeComponent()=null
            # and never dozed (no AOD; the power key went straight to sleep) though
            # doze_always_on was 1. An AOSP SystemUI guest whose framework names no doze
            # component gets SystemUI's own DozeService and AOD available through
            # fabricated overlays, like the cutout's. ONEOS_GUEST_DOZE=0 leaves it.
            if [ \"${ONEOS_GUEST_DOZE:-1}\" = 1 ] && [ $GUEST_AOSP_SYSUI = 1 ]; then
                DZC=\$(timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd overlay lookup android android:string/config_dozeComponent 2>/dev/null | tr -d '\r' | head -n 1)
                case \"\$DZC\" in
                    */*) echo \"[UI Activator] AOD: the guest names its doze service (\$DZC)\" ;;
                    *)
                        DZON=''
                        gxo fabricate --target android --name OneOSDozeComponent android:string/config_dozeComponent string com.android.systemui/com.android.systemui.doze.DozeService &&
                            gxo enable --user 0 com.android.shell:OneOSDozeComponent && DZON=\"\$DZON OneOSDozeComponent\"
                        gxo fabricate --target android --name OneOSDozeAod android:bool/config_dozeAlwaysOnDisplayAvailable 0x12 0xffffffff &&
                            gxo enable --user 0 com.android.shell:OneOSDozeAod && DZON=\"\$DZON OneOSDozeAod\"
                        echo \"[UI Activator] AOD: no doze service named (lookup '\$DZC'); overlays on:\${DZON:- none}; now \$(timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd overlay lookup android android:string/config_dozeComponent 2>/dev/null | head -n 1)\" ;;
                esac
            fi
            # Fold test (fold layout only). On every lid switch event record what
            # the guest did: device state, layout, both touch mappers and
            # backlights, a screenshot of display 0, and after folding 10 s of
            # raw touches from the cover touchscreen (pull-run-logs.sh takes
            # $STAGE/diag_*).
            # Cover touch IC. Run 31: folding lit the cover and the guest mapped
            # sec_touchscreen2 DIRECT, but the cover never reacted and getevent on
            # it stayed empty (diag_fold/cover_touch_*.txt). Samsung's touch ICs
            # only scan while One UI's sysinput HAL says their panel is on, and One
            # UI switched the cover IC off at its last unfold before the session
            # (run 30 all.log 10:13:06: set_fold_state,0 to both ICs, then TSP_SUB
            # enabled@1,0 and @1,1; the HAL writes /sys/class/sec/tspN/enabled,
            # display state 2 ON / 1 OFF, event 0 early / 1 late around the panel
            # power change). tsp2 is sec_touchscreen2, port 148, the cover. Nothing
            # in the guest talks to that HAL, so the monitor plays One UI's part
            # for the cover IC only: fold = set_fold_state,1, 2,0, wait for the
            # cover backlight, 2,1; unfold = set_fold_state,0, 1,0, 1,1. The inner
            # IC (tsp1) is never written, so it stays on for the whole session and
            # unfolding always gives touch back. ONEOS_COVER_TSP=0 leaves both ICs
            # alone (run 31 behaviour).
            # OneOS: and only on a foldable, never by chance: fold form, a flip
            # lid switch and a sec_touchscreen2 must all be there. On a bar phone
            # (S Ultra) the one touch IC is a single /sys/class/sec/tsp, which
            # the TSP1 match below would find.
            if [ \"\$(cat $STAGE/data/oneos_fold_mode 2>/dev/null)\" = layout ]; then
                FD=$STAGE/diag_fold; mkdir -p \$FD
                FLIP=''; TS2=''; TSP1=''; TSP2=''; TSPLOG=''
                for e in /sys/class/input/event*; do
                    case \"\$(cat \$e/device/name 2>/dev/null)\" in
                        flip) FLIP=/dev/input/\${e##*/} ;;
                        sec_touchscreen2) TS2=/dev/input/\${e##*/} ;;
                    esac
                done
                if [ \"${ONEOS_COVER_TSP:-1}\" = 1 ] && [ \"${ONEOS_GUEST_FORM:-fold}\" = fold ] && [ -n \"\$FLIP\" ] && [ -n \"\$TS2\" ]; then
                    for d in /sys/class/sec/tsp*; do
                        [ \"\$(cat \$d/input/name 2>/dev/null)\" = sec_touchscreen2 ] && [ -w \$d/enabled ] && TSP2=\$d
                        [ \"\$(cat \$d/input/name 2>/dev/null)\" = sec_touchscreen ] && [ -w \$d/enabled ] && TSP1=\$d
                    done
                fi
                # The inner IC is only ever switched ON, and only when One UI left
                # it off: a session started folded (One UI powers the inner IC
                # down while folded; seen on the phone before run 32: tsp1
                # enabled 0, tsp2 1) would otherwise keep inner touch dead after
                # unfolding. Same sequence One UI uses when the inner panel comes on.
                # The double tap keeper (guest_start.sh) puts the IC of a panel that
                # is off into low-power mode and marks it (oneos_dt2w_armed.<tsp>
                # in the guest data). Folding or unfolding with the screen off
                # leaves the panel dark, and the 2,1 below, up to 3 s later, took
                # the IC out of that mode again: no double tap after a fold in the
                # pocket (ColorOS, 11-10). A marked IC of a panel whose connector
                # says Off is left to the keeper, which switches it on when the
                # panel lights; so is a marked IC while the keeper's record says
                # the guest sleeps with its clock on (oneos_dt2w_aod = 1, build
                # 107: the IC is armed under a lit panel then). No keeper, no
                # marker: as before.
                dt2w_holds() {
                    [ -e $STAGE/data/oneos_dt2w_armed.\$1 ] || return 1
                    [ \"\$(cat /sys/class/drm/card0-\$2/dpms 2>/dev/null)\" = Off ] || [ \"\$(cat $STAGE/data/oneos_dt2w_aod 2>/dev/null)\" = 1 ]
                }
                inner_tsp_on() {
                    [ -n \"\$TSP1\" ] && [ \"\$(cat \$TSP1/enabled 2>/dev/null)\" = 0 ] || return 0
                    grep -q -w set_fold_state \$TSP1/cmd_list 2>/dev/null && echo set_fold_state,0 > \$TSP1/cmd
                    echo 2,0 > \$TSP1/enabled
                    i=0; while [ \$i -lt 15 ] && [ \"\$(cat /sys/class/backlight/panel0-backlight/brightness 2>/dev/null)\" = 0 ]; do sleep 0.2; i=\$((i + 1)); done
                    if dt2w_holds \${TSP1##*/} DSI-1; then
                        echo \"inner touch IC \$TSP1: the guest sleeps and the double tap keeper holds it in low-power mode, left there\"
                        return 0
                    fi
                    echo 2,1 > \$TSP1/enabled
                    echo \"inner touch IC \$TSP1 switched on: enabled \$(cat \$TSP1/enabled 2>&1)\"
                }
                # 1 = folded, 0 = unfolded. Writes the cover IC's own enabled and
                # cmd nodes (and the inner IC's only to switch it on, above); the
                # backlights are only read.
                cover_tsp() {
                    [ -n \"\$TSP2\" ] || return 0
                    if [ \"\$1\" = 1 ]; then
                        grep -q -w set_fold_state \$TSP2/cmd_list 2>/dev/null && echo set_fold_state,1 > \$TSP2/cmd
                        echo 2,0 > \$TSP2/enabled
                        i=0; while [ \$i -lt 15 ] && [ \"\$(cat /sys/class/backlight/panel1-backlight/brightness 2>/dev/null)\" = 0 ]; do sleep 0.2; i=\$((i + 1)); done
                        if dt2w_holds \${TSP2##*/} DSI-2; then
                            echo \"cover touch IC \$TSP2: folded while the guest sleeps, the double tap keeper holds it in low-power mode, left there\"
                            return 0
                        fi
                        echo 2,1 > \$TSP2/enabled
                    else
                        grep -q -w set_fold_state \$TSP2/cmd_list 2>/dev/null && echo set_fold_state,0 > \$TSP2/cmd
                        echo 1,0 > \$TSP2/enabled; echo 1,1 > \$TSP2/enabled
                        inner_tsp_on
                    fi
                    echo \"cover touch IC \$TSP2 set for folded=\$1: enabled \$(cat \$TSP2/enabled 2>&1), cmd \$(cat \$TSP2/cmd_result 2>&1)\"
                }
                echo \"[UI Activator] fold test: lid switch \${FLIP:-not found}, cover touch \${TS2:-not found}, cover touch IC \${TSP2:-not used}\"
                # Started folded (device state 0 = CLOSE): no lid event will come.
                if [ \"\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd device_state print-state 2>/dev/null | head -1)\" = 0 ]; then
                    echo \"[UI Activator] \$(cover_tsp 1 2>&1)\"
                else
                    echo \"[UI Activator] \$(inner_tsp_on 2>&1)\"
                fi
                # The sampling below (eight dumpsys calls, a screenshot, 10 s of raw
                # cover touches) ran 3 s after every lid event of a session, on a
                # phone that is used all day (owner, 11-10: daily driving, heat):
                # now for the first six lid events of a session only; after that one
                # line per event, and the touch IC handling as before.
                # ONEOS_FOLD_DIAG=all samples every event, =0 none, a number that many.
                FDN='${ONEOS_FOLD_DIAG:-6}'; case \"\$FDN\" in all) FDN=1000000 ;; ''|*[!0-9]*) FDN=6 ;; esac
                [ -n \"\$FLIP\" ] && [ \$PASS = 1 ] && ( n=0; getevent -lq \$FLIP 2>/dev/null | while read typ code val rest; do
                    [ \"\$code\" = SW_LID ] || continue
                    n=\$((n + 1)); ts=\$(date +%T)
                    case \"\$val\" in
                        00000001) TSPLOG=\$(cover_tsp 1 2>&1) ;;
                        00000000) TSPLOG=\$(cover_tsp 0 2>&1) ;;
                    esac
                    if [ \$n -gt \$FDN ]; then
                        echo \"== \$ts event \$n: SW_LID \$val (00000001 = folded), not sampled; \$TSPLOG\" >> \$FD/fold_test.log
                        continue
                    fi
                    # Sampled in the background. Inline (run 31) the 3 s wait and the
                    # 10 s cover touch capture held the next lid event in the pipe: a
                    # fold undone within a second (event 7, the cover shows for about
                    # 1 s in the recording) was logged as folded in state 3 and its
                    # unfold never made the log. Each block is written in one go so
                    # overlapping samples do not interleave.
                    ( sleep 3
                      { echo \"== \$ts event \$n: SW_LID \$val (00000001 = folded), sampled \$(date +%T)\"
                        $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd device_state print-state 2>&1
                        $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys device_state 2>/dev/null | grep -E 'mCommittedState|mPendingState|mBaseState|mOverrideState' | head -4
                        # Run 44: the hinge reading behind HALF_OPENED (the fold
                        # line stays -flat until an unfold settles in OPENED) and the
                        # density each panel got (inner 420, cover 480 expected).
                        $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys device_state 2>/dev/null | grep -A2 mLastHingeAngleSensorEvent
                        echo \"density: \$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/wm density -d 0 2>&1 | tr '\n' ' ')\"
                        $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys power 2>/dev/null | grep -m1 -E 'mWakefulness='
                        $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys display 2>/dev/null | grep -m1 -o 'mCurrentLayout=.*' | cut -c1-400
                        $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys input 2>/dev/null | grep -E '^  Device [0-9]+: sec_touchscreen|Touch Input Mapper \\(mode'
                        for b in panel0 panel1; do echo \"\$b-backlight \$(cat /sys/class/backlight/\$b-backlight/brightness 2>/dev/null)\"; done
                        [ -n \"\$TSP2\" ] && echo \"\$TSPLOG; after 3 s enabled \$(cat \$TSP2/enabled 2>&1), inhibited \$(cat \$TSP2/input/inhibited 2>&1)\"
                        # What the touch driver made of it (refused while it thinks
                        # the phone is open, already on, failed to power up).
                        [ -n \"\$TSP2\" ] && dmesg 2>/dev/null | grep -i -E 'sec_input|enabled|fold' | tail -n 20
                      } > \$FD/.event_\$n 2>&1
                      cat \$FD/.event_\$n >> \$FD/fold_test.log; rm -f \$FD/.event_\$n
                      $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/screencap -p /data/local/tmp/fold_\$n.png 2>/dev/null
                      cp $STAGE/data/local/tmp/fold_\$n.png \$FD/ 2>/dev/null
                      [ \"\$val\" = 00000001 ] && [ -n \"\$TS2\" ] && timeout 10 getevent -lt \$TS2 > \$FD/cover_touch_\$n.txt 2>&1
                      # Folded: the cover's size, cutout and the status bar inset apps
                      # get, about 15 s on (an app opened by then). Nothing run 11: apps
                      # on the cover started about 60 px down, under the drawn bar, and
                      # the 20/40/90 s rounds had only the inner panel to show.
                      if [ \"\$val\" = 00000001 ]; then
                          sleep 2
                          { echo \"== \$ts event \$n: folded, window state \$(date +%T)\"
                            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys window displays 2>/dev/null |
                                grep -E 'init=|mDisplayCutout=|type=statusBars frame|type=displayCutout|overrideConfig=' | head -n 12 | cut -c1-400
                          } > \$FD/.event_\${n}c 2>&1
                          cat \$FD/.event_\${n}c >> \$FD/fold_test.log; rm -f \$FD/.event_\${n}c
                      fi
                      # Unfolded: the state again about 10 s on, to see whether a
                      # HALF_OPENED settles in OPENED (2) (run 44).
                      if [ \"\$val\" = 00000000 ]; then
                          sleep 7
                          { echo \"== \$ts event \$n: unfolded, sampled again \$(date +%T)\"
                            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd device_state print-state 2>&1
                            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys device_state 2>/dev/null | grep -E 'mCommittedState|mBaseState' | head -2
                            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys device_state 2>/dev/null | grep -A2 mLastHingeAngleSensorEvent
                          } > \$FD/.event_\${n}b 2>&1
                          cat \$FD/.event_\${n}b >> \$FD/fold_test.log; rm -f \$FD/.event_\${n}b
                      fi
                    ) &
                done ) </dev/null >/dev/null 2>&1 &
            fi
            # Wallpapers page probe. Run 31: on Home screen, Lock screen & style
            # the My theme header (dark card, All Flux themes) filled the first
            # screen, about 2400 px tall where its layout and the fragment ask for
            # 386dp = 984 px; the RRO card row below it was fine. Once that page is
            # the top app (oom_score_adj 0), save its view tree with frames
            # and a screenshot to diag_pages. Read-only, two captures at most,
            # polling a /proc file only; ONEOS_WALLPAPER_PROBE=0 skips it. Run 32:
            # dumpsys activity top 4 s later caught Settings Font instead (the user
            # had moved on), so dump every com.oplus.wallpapers activity, stopped
            # ones included, 2 s after it comes to the front.
            if [ '${ONEOS_WALLPAPER_PROBE:-1}' = 1 ]; then
                ( WD=$STAGE/diag_pages; mkdir -p \$WD; n=0; i=0; last=''
                  while [ \$n -lt 2 ] && [ \$i -lt 400 ]; do
                      i=\$((i + 1)); sleep 3
                      wp=\$(pidof com.oplus.wallpapers | awk '{print \$1}')
                      [ -n \"\$wp\" ] && [ \"\$wp\" != \"\$last\" ] || continue
                      [ \"\$(cat /proc/\$wp/oom_score_adj 2>/dev/null)\" = 0 ] || continue
                      sleep 2
                      n=\$((n + 1)); last=\$wp
                      timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys activity activity com.oplus.wallpapers > \$WD/wallpapers_top_\$n.txt 2>&1
                      timeout 15 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/screencap -p /data/local/tmp/wallpapers_\$n.png 2>/dev/null
                      cp $STAGE/data/local/tmp/wallpapers_\$n.png \$WD/ 2>/dev/null
                  done ) </dev/null >/dev/null 2>&1 &
            fi
            # SIM attach APN (run 42). Each SIM's slot, the guest's sub id and the
            # preferred APN its telephony provider resolves (guest_prepare.sh
            # seeded One UI's for sub = slot + 1). Pixel guest, in the background.
            if [ $GUEST_OPLUS = 0 ]; then
                ( sleep 15
                  $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/content query --uri content://telephony/siminfo --projection _id:sim_id --where 'sim_id>=0' 2>/dev/null | grep '^Row: ' | while IFS= read -r row; do
                      sub=\$(echo \"\$row\" | sed -n 's/^Row: [0-9]* _id=\([0-9]*\),.*/\1/p')
                      slot=\$(echo \"\$row\" | sed -n 's/.* sim_id=\([0-9]*\).*/\1/p')
                      [ -n \"\$sub\" ] || continue
                      p=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/content query --uri content://telephony/carriers/preferapn/subId/\$sub --projection _id:name:apn 2>/dev/null | grep -m 1 '^Row: ' | sed 's/^Row: [0-9]* //')
                      echo \"[UI Activator] SIM slot \${slot:-?}: sub \$sub, preferred APN \${p:-none}\"
                  done ) </dev/null &
                # Comfort View (run 43: its switch did nothing; services.jar now
                # turns it into a color matrix, OneOSComfortView level 175): its
                # settings, SurfaceFlinger's color matrix, the overlay that decides
                # config_cv_available and the bridge's log, 60 s after Home, in
                # diag_display. Read only.
                ( sleep 60; WD=$STAGE/diag_display; mkdir -p \$WD
                  for k in cv_enabled cv_preferred_intensity cv_dynamic_enabled; do echo \"\$k=\$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get system \$k 2>&1)\"; done > \$WD/cv.txt
                  timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys SurfaceFlinger 2>&1 | grep -i -E -A6 'color ?matrix|colortransform' > \$WD/sf_color.txt
                  timeout 15 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd overlay lookup android android:bool/config_cv_available > \$WD/cv_overlay.txt 2>&1
                  timeout 10 logcat -d -s OneOSComfortView DisplayTransformManager 2>/dev/null | tail -n 20 > \$WD/cv_log.txt ) </dev/null >/dev/null 2>&1 &
            fi
            echo '[UI Activator] Creating missing app data dirs...'
            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/sh /data/local/tmp/fix_app_dirs.sh 2>/dev/null || true

            # Bring apps: install what bring-collect left for this guest and lay its One UI data over it.
            # The script is the one guest_start.sh wrote; it runs beside this pass, is safe to cut short,
            # and logs to oneos_bring.log in the guest data (also after a guest soft reboot: one run at a time).
            if [ -f $STAGE/data/oneos_bring_restore.sh ] && [ -d $STAGE/data/oneos_bring ]; then
                ( $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/sh /data/oneos_bring_restore.sh ) </dev/null >/dev/null 2>&1 &
                echo '[UI Activator] Bring apps: restore started (oneos_bring.log in the guest data)'
            fi

            # Galaxy Z Fold8, Find N6 set: AOD, widgets, taskbar and the hinge relay in the guest.
            if { [ \"${ONEOS_PROFILE:-}\" = f8 ] || [ \"${ONEOS_PROFILE:-}\" = f8u ]; } && grep -q coloros17-findn6 \"$STAGE/.oneos_stage\" && [ -f \"$STAGE/data/oneos_fold8/runtime.sh\" ]; then
                $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/sh /data/oneos_fold8/runtime.sh runtime >\"$STAGE/fold8_runtime.log\" 2>&1 || echo '[UI Activator] Fold8 runtime setup failed; see fold8_runtime.log'
            fi

            # Pixel Fold8 / Fold8 Ultra: start the system-UID sensor reader in the guest namespace
            # (fold8_pixel.sh prepare made runtime.sh only for those two sets).
            if { [ \"${ONEOS_PROFILE:-}\" = f8 ] || [ \"${ONEOS_PROFILE:-}\" = f8u ]; } && grep -q '\"set\": \"pixel-f8u\\{0,1\\}\",' \"$STAGE/.oneos_stage\" && [ -f \"$STAGE/data/oneos_pixel_hinge/runtime.sh\" ]; then
                $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/sh /data/oneos_pixel_hinge/runtime.sh runtime >\"$STAGE/pixel_hinge_runtime.log\" 2>&1 || echo '[UI Activator] Pixel hinge relay unavailable; native sensor fallback active'
            fi

            # Populate network permissions for all installed packages
            for uid in \$($BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/pm list packages -U 2>/dev/null | grep -o 'uid:[0-9]*' | cut -d: -f2 | sort -u); do
                [ -n \"\$uid\" ] || continue
                b0=\$(printf \"%02x\" \$((uid & 0xff)))
                b1=\$(printf \"%02x\" \$(((uid >> 8) & 0xff)))
                b2=\$(printf \"%02x\" \$(((uid >> 16) & 0xff)))
                b3=\$(printf \"%02x\" \$(((uid >> 24) & 0xff)))
                bpftool map update pinned /sys/fs/bpf/netd_shared/map_netd_uid_permission_map key hex \$b0 \$b1 \$b2 \$b3 value hex 0c 2>/dev/null || true
            done

            # Ensure default routing
            DEF_IF=\$(ip route | grep -o 'dev [^ ]*' | head -n 1 | awk '{print \$2}')
            [ -n \"\$DEF_IF\" ] && ip route add default dev \"\$DEF_IF\" 2>/dev/null || true

            # Mount emulated primary storage
            $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/sm mount \"emulated;0\" 2>/dev/null || true
            # Wifi: ColorOS boots scan-only (wifi_on=0) and One UI's supplicant
            # has exited. Turning Wi-Fi on makes the guest ask servicemanager for
            # the supplicant, so the host init starts Samsung's. wifi_on then
            # persists in the staged /data.
            if [ \"\$(cat $STAGE/host_wifi_on 2>/dev/null)\" = 1 ]; then
                (
                    $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd wifi set-wifi-enabled enabled 2>&1 | head -2
                    n=0
                    while [ \$n -lt 15 ]; do
                        service check android.hardware.wifi.supplicant.ISupplicant/default 2>/dev/null | grep -q ': found' && break
                        n=\$((n + 1)); sleep 1
                    done
                    SVC=\$(cat $STAGE/host_supplicant_svc 2>/dev/null)
                    if [ \$n -ge 15 ] && [ -n \"\$SVC\" ]; then
                        echo \"[UI Activator] wifi: supplicant not started on request, ctl.start \$SVC\"
                        setprop ctl.start \$SVC
                    fi
                    echo \"[UI Activator] wifi: supplicant \$(service check android.hardware.wifi.supplicant.ISupplicant/default 2>/dev/null | cut -d: -f2) after \${n}s\"
                    # Run 42 (Pixel): scans ran, no network was joined and the
                    # Internet page looked empty. 45 s after Wi-Fi came on, the
                    # guest's own status, scan results, saved networks and scanner
                    # state in diag_wifi (network names only there, never in this
                    # log). In the background. None of it needs verbose logging (set
                    # above; run 43: switching it on here gave the debug text).
                    if [ $GUEST_OPLUS = 0 ]; then
                        rm -rf $STAGE/diag_wifi
                        ( sleep 45; mkdir -p $STAGE/diag_wifi
                          for c in status list-scan-results list-networks is-verbose-logging; do echo \"== cmd wifi \$c\"; timeout 15 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd wifi \$c 2>&1; done > $STAGE/diag_wifi/wifi.txt
                          { echo '== dumpsys wifi (verbose)'; timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys wifi 2>&1 | grep -m2 -i verbose; } >> $STAGE/diag_wifi/wifi.txt
                          timeout 20 $BB nsenter -t \$PID -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys wifiscanner > $STAGE/diag_wifi/wifiscanner.txt 2>&1 ) </dev/null >/dev/null 2>&1 &
                        echo '[UI Activator] wifi: status, scan results and saved networks to diag_wifi in 45 s'
                    fi
                )
            fi
            break
        fi
    fi
done
# This boot's pass is done: wait for a soft reboot of the guest, or end with
# the session (the return's first step, or its namespace record gone).
while [ \"\$(cat $STAGE/tmp/softreboot.gen 2>/dev/null)\" = \"\$GEN\" ]; do
    sleep 2
    [ -f $STAGE/data/oneos_rec_stop ] && exit 0
    [ -f $STAGE/guest_mntns ] || exit 0
done
GEN=\$(cat $STAGE/tmp/softreboot.gen 2>/dev/null); PASS=\$((PASS + 1))
echo \"[UI Activator] soft reboot of the guest (generation \$GEN): pass \$PASS, waiting for its new boot\"
done
" </dev/null >/data/local/tmp/ui_activator.log 2>&1 &

# Samsung CPU/GPU votes survive the host framework; capability-detected on every profile.
# 0.4.38: only with the heat cap off (Cool down when hot, Advanced). With it on, the heat cap
# below caps from 45 C and lifts One UI's stale vote itself; the worker only releases under
# 38 C and caps after a release, so a hot guest had no cap at all (F8U, Find N6 global:
# 55.6 C skin at full clock).
if [ "${ONEOS_HEAT_CAP:-1}" != 1 ]; then
    STAGE="$STAGE" BB="$BB" "$BB" nohup /system/bin/sh "$STAGE/fold8_coloros.sh" performance-worker </dev/null >>"$STAGE/performance_handover.log" 2>&1 &
else
    echo "$(date +%T) heat cap on: the worker is not started (the heat cap owns the limits)" >> "$STAGE/performance_handover.log"
fi

# Session sampler (run 44: nothing was recorded after the 90 s round; window
# blur went off and on with the guest's thermal status, not the setting, while
# One UI's last CPU cap stayed). Every 30 s until the return, one line in
# $STAGE/diag_series.txt: time, the guest's thermal status and skin
# temperature (its thermal service on the shared HAL), each cpufreq policy's
# scaling_max_freq/cpuinfo_max_freq, WindowManager's mBlurEnabled,
# disable_window_blurs, battery level and status. Read only, each guest call
# with a timeout; until the guest's system_server runs only the kernel's
# values. It stops once return_to_oneui.sh has started (data/oneos_rec_stop,
# its first step; its pkill of system_server matches this command line too)
# or the guest's namespace record is gone. Out of the app cgroup, like the
# watcher, so it outlives the app that started the switch. Also, in
# $STAGE/cpu_top.log (collected with the stage's logs), the six busiest
# processes over one second and the CPU totals (HyperOS run 11: 42-44 C skin
# all session and nothing said which process kept the CPU busy).
$BB sh -c "
    echo \$\$ > /sys/fs/cgroup/cgroup.procs 2>/dev/null
    F=$STAGE/diag_series.txt
    T=$STAGE/cpu_top.log
    echo \"# \$(date) OneOS session sampler: every 30 s, CPU totals and the six busiest processes over 1 s (%CPU of one core)\" > \$T
    echo \"# \$(date) OneOS session sampler, one line every 30 s: time, thermal status, skin C, policyN=scaling_max_freq/cpuinfo_max_freq kHz, mBlurEnabled, disable_window_blurs, battery %,status\" > \$F
    while true; do
        [ -f $STAGE/data/oneos_rec_stop ] && { echo \"# \$(date +%T) the return started: sampler stopped\" >> \$F; exit 0; }
        [ -s $STAGE/guest_mntns ] || { echo \"# \$(date +%T) no guest namespace record: sampler stopped\" >> \$F; exit 0; }
        t0=\$(date +%s)
        P=\$(pidof system_server | awk '{print \$1}')
        st=''; sk=''; bl=''; dw=''
        if [ -n \"\$P\" ]; then
            TH=\$(timeout 10 $BB nsenter -t \$P -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys thermalservice 2>/dev/null)
            st=\$(echo \"\$TH\" | sed -n 's/^Thermal Status: *\([0-9][0-9]*\).*/\1/p' | head -n 1)
            sk=\$(echo \"\$TH\" | sed -n '/^Current temperatures from HAL/,/^[^[:space:]]/p' | sed -n 's/.*mValue=\([-0-9.]*\), mType=[0-9]*, mName=SKIN,.*/\1/p' | head -n 1)
            bl=\$(timeout 10 $BB nsenter -t \$P -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys window windows 2>/dev/null | grep -m 1 -o 'mBlurEnabled=[a-z]*' | sed 's/.*=//')
            dw=\$(timeout 10 $BB nsenter -t \$P -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get global disable_window_blurs 2>/dev/null)
        fi
        c=''
        for p in /sys/devices/system/cpu/cpufreq/policy*; do
            [ -r \$p/scaling_max_freq ] && c=\"\$c \${p##*/}=\$(cat \$p/scaling_max_freq 2>/dev/null)/\$(cat \$p/cpuinfo_max_freq 2>/dev/null)\"
        done
        bc=\$(cat /sys/class/power_supply/battery/capacity 2>/dev/null)
        bs=\$(cat /sys/class/power_supply/battery/status 2>/dev/null | tr ' ' _)
        echo \"\$(date +%T) thermal=\${st:--} skin=\${sk:--}\$c blur=\${bl:--} disable_window_blurs=\${dw:--} battery=\${bc:-?}%,\${bs:-?}\" >> \$F
        TOP=\$(timeout 10 top -b -n 1 -d 1 -m 6 -s 1 -o %CPU,PID,NAME 2>/dev/null)
        echo \"\$(date +%T) \$(echo \"\$TOP\" | grep -m 1 'cpu ' | tr -s ' ') |\$(echo \"\$TOP\" | awk '\$1 ~ /^[0-9.]+\$/ && \$2 ~ /^[0-9]+\$/ { printf \" %s %s\", \$1, \$3 }')\" >> \$T
        s=\$((t0 + 30 - \$(date +%s))); [ \$s -gt 0 ] || s=1
        sleep \$s
    done
" </dev/null >/dev/null 2>&1 &
echo "Session sampler: every 30 s to $STAGE/diag_series.txt"

# Heat cap (S25 Ultra af6c2b17; owner 2026-10-27: cap only when hot). One UI's
# heat control (SSRM) stops with One UI's system_server, and nothing in the
# guest caps the CPU: that session ran both clusters at full clock up to 54 C
# skin. Every 10 s the guest's SKIN temperature (its thermal service on the
# shared HAL, read as the sampler reads it) sets a level: from 45 C (Samsung's
# SEVERE) every cpufreq policy's scaling_max_freq is 80% of its
# cpuinfo_max_freq, from 47 C 65%, from 50 C 50%; a level ends 2 C under where
# it began. The first reading under 45 C lifts a cap One UI left (run 45: half
# clock for a whole session); after that the policies are written only when the
# level changes, each change logged in $STAGE/heat_cap.log. Only scaling_max_freq
# (the sysfs request) is written: the kernel's own thermal limits stay. It stops
# with the return (data/oneos_rec_stop) or when the guest's namespace record is
# gone, giving the policies their full clock back if it had capped them;
# return_to_oneui.sh stops it as well and does the same (heat_cap.active), for
# One UI's SSRM to set its own. ONEOS_HEAT_CAP=0 (Advanced: Cool down when hot
# off): no cap. Out of the app cgroup, like the sampler.
# Guest thermal status (Pixel; owner's go, 2026-11-06). Samsung's thermal HAL
# told Pixel CRITICAL at 49.6 C skin, and Pixel's JobScheduler holds every
# ordinary job from SEVERE on (ThermalStatusRestriction, fixed in its code):
# Play installs, the live wallpaper download, theme packs and icon styles never
# started while the phone was warm (test build 6, 14:46-14:50). The same loop
# gives the guest a status from the skin temperature instead: NONE under 47 C,
# LIGHT from 47, MODERATE from 50, SEVERE from 53 (1 C hysteresis), and from
# 56 C the HAL's own again, CRITICAL and SHUTDOWN included (cmd thermalservice
# override-status / reset; again after a guest system_server restart). The
# kernel's thermal limits and the cap above stay. It runs without the cap too
# (only the status then); ONEOS_GUEST_THERMAL_MAP=0 leaves the HAL's.
rm -f "$STAGE/heat_cap.active"
HEAT_CAP=0; [ "${ONEOS_HEAT_CAP:-1}" = 1 ] && HEAT_CAP=1
GUEST_THERMAL_MAP=0
[ "${ONEOS_GUEST_THERMAL_MAP:-1}" = 1 ] && grep -q '^  "image": "pixel' "$STAGE/.oneos_stage" 2>/dev/null && GUEST_THERMAL_MAP=1
if [ $HEAT_CAP = 1 ] || [ $GUEST_THERMAL_MAP = 1 ]; then
    [ $HEAT_CAP = 1 ] && : > "$STAGE/heat_cap.active"
    rm -f "$STAGE/cpufreq_max_limit.released"
    $BB sh -c "
    : oneos_heat_cap
    echo \$\$ > /sys/fs/cgroup/cgroup.procs 2>/dev/null
    F=$STAGE/heat_cap.log
    CFL=/sys/devices/system/cpu/cpufreq_limit/cpufreq_max_limit
    if [ $HEAT_CAP = 1 ]; then
        echo \"# \$(date) OneOS heat cap: from 45, 47, 50 C skin every CPU policy at 80, 65, 50% of its top clock (2 C hysteresis)\" > \$F
    else
        echo \"# \$(date) OneOS heat cap off (Cool down when hot): the guest thermal status only\" > \$F
    fi
    [ $GUEST_THERMAL_MAP = 1 ] && echo \"# guest thermal status from skin: NONE, LIGHT 47, MODERATE 50, SEVERE 53, the HAL status from 56 C (1 C hysteresis)\" >> \$F
    full() {
        c=''
        if [ \"$HOST_LOW_POWER\" = 0 ] && [ -w \$CFL ] && [ \"\$(cat \$CFL 2>/dev/null)\" != -1 ]; then
            v=\$(cat \$CFL 2>/dev/null)
            echo -1 > \$CFL 2>/dev/null && echo \"\$v\" > $STAGE/cpufreq_max_limit.released
            c=\" cpufreq_max_limit=\$v->\$(cat \$CFL 2>/dev/null)\"
        fi
        for p in /sys/devices/system/cpu/cpufreq/policy*; do
            hw=\$(cat \$p/cpuinfo_max_freq 2>/dev/null)
            case \"\$hw\" in ''|*[!0-9]*) continue ;; esac
            echo \$hw > \$p/scaling_max_freq 2>/dev/null
            c=\"\$c \${p##*/}=\$(cat \$p/scaling_max_freq 2>/dev/null)/\$hw\"
        done
        echo \"\$(date +%T) \$1: full clock:\$c\" >> \$F
    }
    lvl=0; first=1; tl=-1; lp=''
    while true; do
        if [ -f $STAGE/data/oneos_rec_stop ] || [ ! -s $STAGE/guest_mntns ]; then
            [ \$lvl = 0 ] || full stopped
            echo \"# \$(date +%T) stopped (the return started, or no guest namespace record)\" >> \$F
            exit 0
        fi
        P=\$(pidof system_server | awk '{print \$1}')
        sk=''
        [ -n \"\$P\" ] && sk=\$(timeout 10 $BB nsenter -t \$P -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys thermalservice 2>/dev/null | sed -n '/^Current temperatures from HAL/,/^[^[:space:]]/p' | sed -n 's/.*mValue=\([-0-9.]*\), mType=[0-9]*, mName=SKIN,.*/\1/p' | head -n 1)
        if [ -n \"\$sk\" ] && [ $GUEST_THERMAL_MAP = 1 ]; then
            [ \"\$P\" = \"\$lp\" ] || tl=-1
            lp=\$P
            nt=\$(awk -v s=\"\$sk\" -v l=\$tl 'BEGIN { t[1] = 47; t[2] = 50; t[3] = 53; t[4] = 56; if (l < 0) l = 0; while (l < 4 && s >= t[l + 1]) l++; while (l > 0 && s < t[l] - 1) l--; print l }')
            if [ \"\$nt\" != \"\$tl\" ]; then
                if [ \"\$nt\" = 4 ]; then a=reset; w=\"the HAL status again\"; else a=\"override-status \$nt\"; w=\$nt; fi
                r=\$(timeout 10 $BB nsenter -t \$P -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd thermalservice \$a 2>&1 | head -n 2 | tr '\\n' ' ')
                echo \"\$(date +%T) skin \$sk C: guest thermal status \$w (cmd thermalservice \$a: \${r:-ok})\" >> \$F
                tl=\$nt
            fi
        fi
        if [ -n \"\$sk\" ] && [ $HEAT_CAP = 1 ]; then
            new=\$(awk -v s=\"\$sk\" -v l=\$lvl 'BEGIN { t[1] = 45; t[2] = 47; t[3] = 50; while (l < 3 && s >= t[l + 1]) l++; while (l > 0 && s < t[l] - 2) l--; print l }')
            if [ \"\$new\" = 0 ] && [ \$first = 1 ]; then
                capped=''
                for p in /sys/devices/system/cpu/cpufreq/policy*; do
                    [ \"\$(cat \$p/scaling_max_freq 2>/dev/null)\" = \"\$(cat \$p/cpuinfo_max_freq 2>/dev/null)\" ] || capped=1
                done
                if [ -n \"\$capped\" ]; then full \"skin \$sk C, a cap from before the switch lifted\"
                else echo \"\$(date +%T) skin \$sk C: no cap\" >> \$F; fi
            elif [ \"\$new\" = 0 ] && [ \$lvl != 0 ]; then
                full \"skin \$sk C, level \$lvl to 0\"
            elif [ \"\$new\" != 0 ] && [ \"\$new\" != \$lvl ]; then
                case \$new in 1) pct=80 ;; 2) pct=65 ;; *) pct=50 ;; esac
                c=''
                for p in /sys/devices/system/cpu/cpufreq/policy*; do
                    hw=\$(cat \$p/cpuinfo_max_freq 2>/dev/null)
                    case \"\$hw\" in ''|*[!0-9]*) continue ;; esac
                    echo \$((hw / 100 * pct)) > \$p/scaling_max_freq 2>/dev/null
                    c=\"\$c \${p##*/}=\$(cat \$p/scaling_max_freq 2>/dev/null)/\$hw\"
                done
                echo \"\$(date +%T) skin \$sk C, level \$lvl to \$new: \$pct%:\$c\" >> \$F
            fi
            lvl=\$new; first=0
        fi
        sleep 10
    done
" </dev/null >/dev/null 2>&1 &
    [ $HEAT_CAP = 1 ] && echo "Heat cap: on (from 45 C skin; every 10 s to $STAGE/heat_cap.log)"
    [ $HEAT_CAP = 1 ] || echo "Heat cap: off (ONEOS_HEAT_CAP=0, Cool down when hot off in Advanced)"
    [ $GUEST_THERMAL_MAP = 1 ] && echo "Guest thermal status: from the skin temperature, the HAL status from 56 C ($STAGE/heat_cap.log)"
else
    echo "Heat cap: off (ONEOS_HEAT_CAP=0, Cool down when hot off in Advanced); guest thermal status: the HAL's"
fi

# Panel keeper (0.4.55). The guests OneOS pins at their top refresh rate (no
# oplus-services.jar: Pixel, HyperOS, Nothing OS) could run a whole session with
# the panel at 24 Hz under a SurfaceFlinger at 120 Hz: 10-15 fps (reports since
# 0.4.38; guest_start.sh, oneos_sf_kick.sh). ColorOS and Infinity-X switch modes
# themselves and came back to 120 Hz on their own. Every 15 s the panel's rate
# (/sys/class/lcd/panel/vrr, its first field) is read; under 48 Hz twice running
# with a backlight on, the guest's /data/oneos_sf_kick.sh takes every display
# through another mode back to its top one, which makes the composer program the
# panel (at most 40 times a session). A 60 Hz setting is left alone. Sysfs reads
# only between kicks; it ends itself with the return (data/oneos_rec_stop) or
# when the guest's namespace record is gone, like the heat cap. Logged in
# $STAGE/panel_keeper.log. ONEOS_GUEST_SF_PIN=0: not started.
rm -f "$STAGE/panel_keeper.log"
if [ "$GUEST_OPLUS" != 1 ] && [ "${ONEOS_GUEST_SF_PIN:-1}" != 0 ] && [ -r /sys/class/lcd/panel/vrr ]; then
    $BB sh -c "
    : oneos_panel_keeper
    echo \$\$ > /sys/fs/cgroup/cgroup.procs 2>/dev/null
    F=$STAGE/panel_keeper.log
    echo \"# \$(date) OneOS panel keeper: every 15 s; under 48 Hz twice with the screen on, oneos_sf_kick.sh\" > \$F
    low=0; kicks=0
    while true; do
        if [ -f $STAGE/data/oneos_rec_stop ] || [ ! -s $STAGE/guest_mntns ]; then
            echo \"# \$(date +%T) stopped (the return started, or no guest namespace record) after \$kicks kicks\" >> \$F
            exit 0
        fi
        hz=\$(cut -d' ' -f1 /sys/class/lcd/panel/vrr 2>/dev/null)
        case \"\$hz\" in ''|*[!0-9]*) hz=0 ;; esac
        on=0
        for b in /sys/class/backlight/*/brightness; do
            v=\$(cat \$b 2>/dev/null); case \"\$v\" in ''|*[!0-9]*) ;; 0) ;; *) on=1 ;; esac
        done
        if [ \$on = 1 ] && [ \$hz -gt 0 ] && [ \$hz -lt 48 ]; then low=\$((low + 1)); else low=0; fi
        if [ \$low -ge 2 ] && [ \$kicks -lt 40 ] && [ -f $STAGE/data/oneos_sf_kick.sh ]; then
            P=\$(pidof system_server | awk '{print \$1}')
            out=''
            [ -n \"\$P\" ] && out=\$(timeout 30 $BB nsenter -t \$P -m /system/bin/sh /data/oneos_genv.sh /system/bin/sh /data/oneos_sf_kick.sh 2>&1 | tr '\\n' ';' | cut -c1-400)
            kicks=\$((kicks + 1)); low=0
            sleep 1
            echo \"\$(date +%T) panel at \$hz Hz with the screen on: \${out:-no guest system_server}; now \$(cut -d' ' -f1 /sys/class/lcd/panel/vrr 2>/dev/null) Hz\" >> \$F
        fi
        sleep 15
    done
" </dev/null >/dev/null 2>&1 &
    echo "Panel keeper: on (every 15 s to $STAGE/panel_keeper.log)"
else
    echo "Panel keeper: off ($([ "$GUEST_OPLUS" = 1 ] && echo "this system sets its own refresh rate" || echo "no /sys/class/lcd/panel/vrr, or ONEOS_GUEST_SF_PIN=0"))"
fi

# OneOS dead-man switch. If the guest is not booting, put One UI back by itself:
# a stuck guest otherwise leaves a black screen and no network (so no remote
# adb either) until a forced reboot, which also drops temp root.
#   - black screen (guest surfaceflinger or bootanimation gone): after
#     ONEOS_RETURN_BLACK seconds (150)
#   - boot animation still running: it is loading, wait up to
#     ONEOS_RETURN_MAX seconds (600)
#   - guest home screen reached (UI activator): never
# The host's surfaceflinger/bootanimation were killed above, so these names
# are the guest's. Props are shared with the host, whose sys.boot_completed is
# already 1, which is why the UI activator is the boot signal.
# ONEOS_RETURN_MAX=0 disables it.
RETURN_BLACK="${ONEOS_RETURN_BLACK:-150}"
RETURN_MAX="${ONEOS_RETURN_MAX:-600}"
# ONEOS_SESSION_MAX (seconds, multiple of 10): end every session after this
# long, even one that reached the home screen, after a last round of
# diagnostics (diag_final). For unattended test runs: the guest has no
# network of its own yet, so the remote side cannot see a running session.
SESSION_MAX="${ONEOS_SESSION_MAX:-0}"
if [ "$RETURN_MAX" -gt 0 ]; then
    # OneOS: the watcher is the way back to One UI, so it must outlive the
    # app that started the switch: out of the app cgroup (killed with the
    # app) and never chosen by the OOM killer. Inherited by return_to_oneui.sh.
    $BB sh -c "
        echo \$\$ > /sys/fs/cgroup/cgroup.procs 2>/dev/null
        echo -1000 > /proc/\$\$/oom_score_adj 2>/dev/null
        t=0; total=0; dead=0; sfgone=0; prev_failed=0; homebase=0; wmbase=0; wmseen=0
        while [ \$t -lt $RETURN_MAX ]; do
            # The 10 s wait ends early on a request. Run 34: Volume Up + Volume
            # Down were held 3 s from 16:43:56, but the request was handled only
            # at 16:44:06 (the rest of this wait, then the diagnostics and the
            # logcat count below). Seeing nothing happen, the user held the
            # keys again, and that second hold turned TalkBack on in ColorOS.
            # Back to One UI in the guest's OneOS app (its screen or its Quick
            # Settings tile) is the request file in that app's data folder,
            # checked every second here: taken once (deleted) and turned into
            # the same request as the keys, app:app or app:tile. Only a plain
            # file is read, 16 bytes at most; nothing in it but the reason is used.
            i=0
            while [ \$i -lt 10 ] && [ -z \"\$(getprop oneos.guest.powerctl)\" ]; do
                if [ -f $GUEST_RETURN_REQ ] && [ ! -L $GUEST_RETURN_REQ ]; then
                    case \"\$(timeout 2 head -c 16 $GUEST_RETURN_REQ 2>/dev/null)\" in tile*) r=tile ;; *) r=app ;; esac
                    rm -f $GUEST_RETURN_REQ
                    echo \"\$(date) Back to One UI asked in the guest's OneOS app (\$r)\"
                    setprop oneos.guest.powerctl \"app:\$r\"
                    continue
                fi
                if [ -f $GUEST_RESTART_REQ ] && [ ! -L $GUEST_RESTART_REQ ]; then
                    rm -f $GUEST_RESTART_REQ
                    setprop oneos.guest.powerctl ksud:soft-reboot
                    break
                fi
                sleep 1; i=\$((i + 1))
            done
            t=\$((t + 10)); total=\$((total + 10))
            # A guest reboot/shutdown request (recorded by the guarded ShutdownThread
            # / PowerManagerService), the return keys or the guest's OneOS app end
            # the session from the host side, before the slow checks below.
            req=\$(getprop oneos.guest.powerctl)
            # KernelSU's soft reboot inside the guest (its ksud wrapper, 0.4.39):
            # this system alone starts again (guest_softreboot.sh); the timers
            # start over, with grace for the new boot's zygote and surfaceflinger,
            # and the home screen counts once this boot's activator pass says so.
            if [ \"\$req\" = ksud:soft-reboot ] && [ -f $STAGE/tmp/guest_softreboot.sh ]; then
                setprop oneos.guest.powerctl ''
                echo \"\$(date) guest requested a soft reboot (\$req) after \${t}s\"
                if BB=$BB timeout 120 /system/bin/sh $STAGE/tmp/guest_softreboot.sh \"\$req\"; then
                    t=0; dead=-60; sfgone=-30; prev_failed=0; wmseen=0; hwcarm=0; rm -f $STAGE/data/oneos_hwc_forced
                    homebase=\$(grep -c 'Home activated' /data/local/tmp/ui_activator.log 2>/dev/null)
                    wmbase=\$(grep -c 'Dismissing bootanim' /data/local/tmp/ui_activator.log 2>/dev/null)
                    continue
                fi
                echo \"\$(date) soft reboot failed, returning to One UI\"
                exec /system/bin/sh $STAGE/return_to_oneui.sh
            fi
            if [ -n \"\$req\" ]; then
                echo \"\$(date) guest requested '\$req' after \${t}s, returning to One UI\"
                # Who asked: the guarded ShutdownThread logs under the tag OneOS (run
                # 31 was Restart in ColorOS's power menu, seen only in the recording).
                timeout 5 logcat -d -b main,system -t 4000 2>/dev/null | grep -E ' OneOS|ShutdownThread|GlobalActions|RescueParty|PowerManagerService.*[Rr]eboot' | tail -15
                exec /system/bin/sh $STAGE/return_to_oneui.sh
            fi
            # Reaching the home screen only lifts the black-screen and time
            # limits; a dead guest still has to come back to One UI (the watcher
            # used to exit here and nothing returned after a later crash).
            home=0; [ \"\$(grep -c 'Home activated' /data/local/tmp/ui_activator.log 2>/dev/null)\" -gt \"\${homebase:-0}\" ] && home=1
            # 0.4.60: the activator removes the boot animation itself once
            # WindowManager is up, and says Home activated only after its slow
            # steps (on MediaTek A phones 30 s and more on a first boot: A07
            # 7262fad2 and A17 fb723e47 were sent back with their keyguard and
            # setup wizard on screen). From its dismissal, 120 s for the home.
            wm=0; [ \"\$(grep -c 'Dismissing bootanim' /data/local/tmp/ui_activator.log 2>/dev/null)\" -gt \"\${wmbase:-0}\" ] && wm=1
            [ \$wm = 1 ] && [ \$home = 0 ] && wmseen=\$((wmseen + 10))
            # Display diagnostics from inside the guest (its own screencap and
            # dumpsys talk to its own surfaceflinger), kept in the stage dir.
            dname=''
            case \$total in 20|40|90) dname=\$total ;; esac
            [ $SESSION_MAX -gt 0 ] && [ \$total -eq $((SESSION_MAX - 20)) ] && dname=final
            # Keep the boot (run 44): once the capture is full its rotation
            # drops the oldest files first, One UI's history, the switch and the
            # guest's boot. In the 90 s round the newest six files (all of the
            # boot at run 44's rates, 192 MiB at most) get a second name in
            # $LOGS/head: hard links, no copy, and no space used until the
            # rotation deletes their first name. This session's capture only.
            if [ \"\$dname\" = 90 ] && [ $LOGCAT_HEAD = 1 ]; then
                rm -rf $LOGS/head && mkdir -p $LOGS/head
                for f in $LOGS/boot.log $LOGS/boot.log.0[1-5]; do
                    [ -f \$f ] && $BB ln -f \$f $LOGS/head/ 2>/dev/null
                done
                echo \"\$(date) logcat capture: \$(ls $LOGS/head 2>/dev/null | wc -l) files of the boot kept in $LOGS/head (hard links)\"
            fi
            if [ -n \"\$dname\" ]; then
                SFP=\$(pidof surfaceflinger | awk '{print \$1}')
                if [ -n \"\$SFP\" ]; then
                    D=$STAGE/diag_\$dname; mkdir -p \$D
                    # Who has the vold names now: One UI's vold keeps vold and
                    # android.system.vold.IVold/default, the guest's is gvld (run 44).
                    { for n in vold android.system.vold.IVold/default gvld; do echo \"\$n: \$(timeout 5 dumpsys --pid \$n 2>&1 | head -n 1)\"; done
                      echo \"init.svc_debug_pid.vold: \$(getprop init.svc_debug_pid.vold)\"; } > \$D/vold_names.txt
                    timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys SurfaceFlinger > \$D/surfaceflinger.txt 2>&1
                    timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys display > \$D/display.txt 2>&1
                    for id in \$(grep -o 'Display [0-9]\\{6,\\}' \$D/surfaceflinger.txt | awk '{print \$2}' | sort -u); do
                        timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/screencap -d \$id -p /data/local/tmp/shot_\$id.png 2>>\$D/screencap.err
                        cp $STAGE/data/local/tmp/shot_\$id.png \$D/ 2>/dev/null
                    done
                    for b in /sys/class/backlight/panel0-backlight /sys/class/backlight/panel1-backlight /sys/class/backlight/panel /sys/class/backlight/panel1; do [ -d \$b ] || continue; echo \"\$b: \$(cat \$b/brightness) actual=\$(cat \$b/actual_brightness) max=\$(cat \$b/max_brightness)\"; done > \$D/backlight.txt 2>&1
                    tail -5 $STAGE/data/backlight.log >> \$D/backlight.txt 2>/dev/null
                    # Samsung's panel refresh (S23 Pixel session f848ebc6: 30 fps
                    # while the guest ran 120 Hz, every frame late at the composer):
                    # the rate the panel runs and who holds a low-frequency floor.
                    for p in /sys/class/lcd/panel /sys/class/lcd/panel1; do [ -d \$p ] || continue; for n in vrr vrr_lfd; do echo \"\$p/\$n: \$(cat \$p/\$n 2>&1 | tr '\n' ' ' | cut -c1-600)\"; done; done > \$D/panel_refresh.txt 2>&1
                    timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys power > \$D/power.txt 2>&1
                    timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys device_state > \$D/device_state.txt 2>&1
                    # Which of our /oem overlays the guest actually enabled, and
                    # for which target. Run 9 staged two of them: the framework
                    # one visibly worked and the SystemUI one changed nothing,
                    # and nothing in the session told us whether it was enabled
                    # at all -- the only record is here. Also the window state,
                    # which carries each panel's DisplayCutout and the status
                    # bar inset (dumpsys display does not).
                    timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys overlay > \$D/overlay.txt 2>&1
                    timeout 20 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys window displays > \$D/window_displays.txt 2>&1
                    timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys oplus_vrr_service > \$D/vrr.txt 2>&1
                    for s in media.audio_flinger media.audio_policy; do timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys \$s > \$D/dumpsys_\$s.txt 2>&1; done
                    # Bluetooth (run 43: A2DP and HFP went to a made-up identity
                    # address): active devices, bond states and identity addresses.
                    timeout 20 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys bluetooth_manager > \$D/bluetooth_manager.txt 2>&1
                    cp $STAGE/data/audio_keeper.log $STAGE/data/call_audio.log $STAGE/data/oneos_a2dp.log $STAGE/data/hyos_spawner.log \$D/ 2>/dev/null
                    timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys SurfaceFlinger --list > \$D/layers.txt 2>&1
                    # Does each SurfaceFlinger -> composer transaction arrive at all?
                    for f in failed_transaction_log transaction_log stats; do timeout 5 cat /dev/binderfs/binder_logs/\$f > \$D/binder_\$f.txt 2>&1; done
                    # Heat (run 43: thermal status CRITICAL with 46-51 C skin during
                    # the first boot's dexopt): the guest's thermal service on the
                    # shared HAL, and the clocks the host kernel allows, read only.
                    timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys thermalservice > \$D/thermal.txt 2>&1
                    # AOD and the double tap (Pixel on the Z Fold8 Ultra, 0.4.59: the dream
                    # manager tried to doze at every power key and the group slept 0.5 s
                    # later, no doze dream ever ran): the guest's dream manager, its doze
                    # and gesture settings, and the sensors SystemUI's doze can find.
                    { timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys dreams
                      for k in doze_enabled doze_always_on doze_pulse_on_pick_up doze_tap_gesture doze_double_tap_gesture doze_wake_screen_gesture doze_wake_display_gesture screensaver_enabled screensaver_activate_on_sleep; do
                          echo \"secure \$k=\$(timeout 5 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/settings get secure \$k 2>/dev/null)\"
                      done
                      timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys sensorservice 2>/dev/null | grep -iE 'tap|doze|pickup|pick_up|wake|gesture|hinge|lid|hall' | head -60
                    } > \$D/doze.txt 2>&1
                    { for p in /sys/devices/system/cpu/cpufreq/policy*; do echo \"\$p cur/max/hw \$(cat \$p/scaling_cur_freq \$p/scaling_max_freq \$p/cpuinfo_max_freq 2>/dev/null | tr '\n' ' ')\"; done
                      echo \"gpu cur \$(cat /sys/class/kgsl/kgsl-3d0/devfreq/cur_freq 2>&1) max \$(cat /sys/class/kgsl/kgsl-3d0/max_gpuclk 2>&1)\"
                      timeout 10 logcat -d -s thermal_core 2>/dev/null | tail -n 3; } > \$D/throttle.txt 2>&1
                    # Did user 0 unlock, did the launcher get a window, and if not,
                    # where are the launcher and SystemUI main threads stuck?
                    if [ \$dname != 20 ]; then
                        timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/am get-started-user-state 0 > \$D/user0.txt 2>&1
                        timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys window windows > \$D/windows.txt 2>&1
                        for app in com.android.launcher com.android.systemui; do
                            ap=\$(pidof \$app | awk '{print \$1}')
                            [ -n \"\$ap\" ] || continue
                            timeout 20 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/debuggerd -j \$ap > \$D/stack_\$app.txt 2>&1
                            timeout 5 cat /dev/binderfs/binder_logs/proc/\$ap > \$D/binder_\$app.txt 2>&1
                            # From the kernel, in case ART's stack dump hangs too:
                            # every thread's name, state and wait channel.
                            for tk in /proc/\$ap/task/*; do
                                echo \"\$(cat \$tk/comm) \$(sed 's/.*) //' \$tk/stat | cut -d' ' -f1) \$(cat \$tk/wchan)\"
                            done > \$D/threads_\$app.txt 2>&1
                            cat /proc/\$ap/task/\$ap/stack >> \$D/threads_\$app.txt 2>&1
                            timeout 20 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/debuggerd \$ap > \$D/native_\$app.txt 2>&1
                        done
                        cp -r $STAGE/data/anr \$D/anr 2>/dev/null
                        # A guest SurfaceFlinger that never registered (A34 OxygenOS 16, 0.4.67
                        # deb8690c: stuck once its RenderEngine started, the framework then waited in
                        # SurfaceSession until its watchdog): its threads and native stacks.
                        if grep -q 'find service: SurfaceFlinger' \$D/surfaceflinger.txt 2>/dev/null; then
                            for tk in /proc/\$SFP/task/*; do
                                echo \"\$(cat \$tk/comm) \$(sed 's/.*) //' \$tk/stat | cut -d' ' -f1) \$(cat \$tk/wchan)\"
                            done > \$D/threads_surfaceflinger.txt 2>&1
                            timeout 20 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/debuggerd \$SFP > \$D/native_surfaceflinger.txt 2>&1
                        fi
                        # Touch: where events go (guest input dispatcher state, focus),
                        # who has the touchscreen open, and raw events for 15 s.
                        timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys input > \$D/input.txt 2>&1
                        timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys window > \$D/window_all.txt 2>&1
                        # Mobile network as the guest sees it (run 30: no 5G): per SIM the
                        # service state, physical channel configs (an NR SecondaryServing
                        # entry means EN-DC is up), display info and allowed network types.
                        timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys telephony.registry > \$D/telephony_registry.txt 2>&1
                        # Signal poll in an AOSP guest (guest_prepare.sh, run 43: no bars): is
                        # OneOSPhoneInjection.apk enabled, is oneos-telephony.jar on a read-only
                        # system_ext, did TeleService load it, the polls so far (signal_polls.txt),
                        # and com.android.phone's pid (the same in diag_40 and diag_90: no crash
                        # loop). The host's RIL props too, without identifiers.
                        { timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd overlay list com.android.phone
                          timeout 5 $BB nsenter -t \$SFP -m /system/bin/sh -c 'ls -lZ /system_ext/framework/oneos-telephony.jar; grep system_ext /proc/self/mounts'
                          echo \"com.android.phone pid: \$(pidof com.android.phone)\"
                          timeout 10 logcat -d -b main,radio -s TelephonyComponentFactory OneOSSignalPoll
                          timeout 10 logcat -d -b radio -s RILJ | grep -E '[<>] SIGNAL_STRENGTH' > \$D/signal_polls.txt
                          echo \"SIGNAL_STRENGTH requests in the radio log: \$(grep -c '> SIGNAL_STRENGTH' \$D/signal_polls.txt)\"
                        } > \$D/overlays_phone.txt 2>&1
                        getprop | grep -iE 'ril|radio' | grep -viE 'serial|imei|imsi|iccid|meid|msisdn|number' > \$D/host_ril_props.txt 2>&1

                        # Location as the guest sees it (run 34: Weather found none): providers
                        # and the package each is bound to, GNSS satellites, fixes and TTFF.
                        timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys location > \$D/location.txt 2>&1
                        # Sensors and cameras as the guest sees them (Galaxy S25, X9U, session
                        # 55af6cc8: compass and camera did not work, and nothing in the logs told why).
                        timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys sensorservice > \$D/sensors.txt 2>&1
                        timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys media.camera > \$D/camera.txt 2>&1
                        # WebView and the zygote sockets (S24 Ultra, IN build, session 77e7789e: the
                        # WebView zygote start found no zygote socket file).
                        { timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/dumpsys webviewupdate
                          echo; ls -la /dev/socket 2>&1 | grep -i zygote
                          echo; $BB nsenter -t \$SFP -m ls -la /dev/socket 2>&1 | grep -i zygote
                          echo; grep ' /dev/socket/' /proc/1/mountinfo
                          echo; getprop | grep -E 'abilist|ro.zygote'
                        } > \$D/webview.txt 2>&1
                        # Is the Wallpapers fold-grid overlay (guest_prepare.sh) enabled?
                        timeout 15 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh /system/bin/cmd overlay list com.oplus.wallpapers > \$D/overlays_wallpapers.txt 2>&1
                        for e in /sys/class/input/event*; do
                            [ \"\$(cat \$e/device/name 2>/dev/null)\" = sec_touchscreen ] || continue
                            dev=/dev/input/\${e##*/}
                            echo \"\$dev enabled=\$(cat \$e/device/enabled 2>/dev/null)\" > \$D/touch_holders.txt
                            ls -l /proc/[0-9]*/fd/* 2>/dev/null | grep \" \$dev\$\" >> \$D/touch_holders.txt
                            timeout 15 getevent -lt \$dev > \$D/touch_events.txt 2>&1
                        done
                        # system_server's own black-screen backtraces (OplusWmBlackDetector).
                        cp -r $STAGE/data/debugging/wm/black \$D/wm_black 2>/dev/null
                        # Run 44, in the background so a slow dump does not hold up the
                        # return keys (each call has its own timeout). Read only:
                        # - largescreen.txt: the density and fold line the UI activator
                        #   set, device state, configuration, WM Extensions warnings;
                        # - composition.txt: device or GPU composition, missed frames,
                        #   composer rejections (HW overlays are on by default now);
                        # - dexopt.txt: run 43's first boot failed to compile all 232
                        #   packages (NullPointerException in IArtd.maybeCreateSdc);
                        # - frames.txt: launcher and Settings frame pacing;
                        # - comfort.txt: Comfort View settings, color matrix, bridge log;
                        # - signal_poll.txt, host_ril_props.txt (identifiers left out),
                        #   call_audio_route.txt: phone process, its overlays and
                        #   telephony jar, RIL props, the SCO / communication device
                        #   route. Bluetooth has its own capture (bluetooth_manager.txt).
                        ( gx() { timeout 20 $BB nsenter -t \$SFP -m /system/bin/sh /data/oneos_genv.sh \"\$@\"; }
                          { gx /system/bin/wm size -d 0; gx /system/bin/wm density -d 0
                            echo \"display_density_forced=\$(gx /system/bin/settings get secure display_density_forced 2>&1)\"
                            echo \"display_features=\$(gx /system/bin/settings get global display_features 2>&1)\"
                            echo \"device state \$(gx /system/bin/cmd device_state print-state 2>&1 | head -1)\"
                            gx /system/bin/dumpsys window displays | grep -m3 -E 'init=|mGlobalConfiguration'
                            timeout 10 logcat -d -s WindowLayoutComponentImpl 2>/dev/null | tail -n 3; } > \$D/largescreen.txt 2>&1
                          { grep -E 'missed frame count|usesDeviceComposition|composition=' \$D/surfaceflinger.txt | sed -e 's/^ *//' -e 's/layer=0x[0-9a-f]* //' | sort | uniq -c
                            echo \"composer rejections in the log: \$(timeout 10 logcat -d -b main -s SurfaceFlinger:E 2>/dev/null | grep -c -E 'executeCommands failed|presentOrValidate failed')\"
                            grep -h -E 'HW overlays|GPU composition' $STAGE/data/takeover.log 2>/dev/null; } > \$D/composition.txt 2>&1
                          { for p in com.android.systemui com.google.android.apps.nexuslauncher com.android.settings; do echo \"== pm art dump \$p\"; gx /system/bin/pm art dump \$p 2>&1 | head -n 30; done
                            echo '== ArtService'; timeout 10 logcat -d -s ArtService 2>/dev/null | grep -m2 -A4 'Unexpected package-level'; } > \$D/dexopt.txt 2>&1
                          for p in com.google.android.apps.nexuslauncher com.android.settings; do echo \"== \$p\"; gx /system/bin/dumpsys gfxinfo \$p 2>&1 | grep -E 'Total frames|Janky|percentile'; done > \$D/frames.txt 2>&1
                          { for k in cv_enabled cv_preferred_intensity cv_dynamic_enabled; do echo \"\$k=\$(gx /system/bin/settings get system \$k 2>&1)\"; done
                            grep -i -E -A6 'color ?matrix|colortransform' \$D/surfaceflinger.txt | head -n 40
                            timeout 10 logcat -d -s OneOSComfortView DisplayTransformManager 2>/dev/null | tail -n 10; } > \$D/comfort.txt 2>&1
                          { echo \"com.android.phone pid: \$(pidof com.android.phone)\"
                            gx /system/bin/cmd overlay list com.android.phone
                            gx /system/bin/ls -lZ /system_ext/framework/oneos-telephony.jar
                            gx /system/bin/grep ' /system_ext' /proc/self/mountinfo; } > \$D/signal_poll.txt 2>&1
                          getprop | grep -i -E 'ril|radio' | grep -v -i -E 'imei|imsi|iccid|msisdn|meid|esn|mdn|euimid|serial|number|subinfo' > \$D/host_ril_props.txt 2>&1
                          gx /system/bin/dumpsys audio 2>&1 | grep -i -E 'sco|communication device' | head -n 20 > \$D/call_audio_route.txt
                        ) </dev/null >/dev/null 2>&1 &
                    fi
                    echo \"\$(date) display diagnostics saved in \$D\"
                fi
            fi
            # A running surfaceflinger can still show nothing: when the composer
            # rejects its frames the panel keeps the last host frame.
            # The guest framework is gone for good once its zygote died: the
            # launcher exec'd app_process64, so nothing restarts it.
            # Before that the takeover process is still guest_start.sh (or
            # zygote_exec), in the guest's mount namespace: the guest is still
            # starting, not dead. Z Fold7 OriginOS 7 report de5f30bd (0.4.73):
            # guest_start.sh's odrefresh (the guest's boot image, vivo) began
            # 36 s after the takeover and compiled for 14 s; this check counted
            # 30 s without a zygote and returned at 09:24:50, four seconds
            # before odrefresh ended and the zygote would have started (the
            # next try, 32809875, compiled in 7 s and booted). A start that
            # hangs is still bounded by ONEOS_RETURN_MAX.
            if pidof system_server >/dev/null || pidof zygote64 >/dev/null; then
                dead=0
            elif [ -n \"\$(cat $STAGE/guest_mntns 2>/dev/null)\" ] &&
                 [ \"\$(readlink /proc/$TAKEOVER_PID/ns/mnt 2>/dev/null)\" = \"\$(cat $STAGE/guest_mntns 2>/dev/null)\" ] &&
                 case \"\$(readlink /proc/$TAKEOVER_PID/exe 2>/dev/null)\" in */app_process64|*/app_process32|'') false ;; *) true ;; esac; then
                dead=0
            else
                dead=\$((dead + 10))
                if [ \$dead -ge 30 ]; then
                    echo \"\$(date) guest zygote/system_server gone for \${dead}s after \${t}s, returning to One UI\"
                    exec /system/bin/sh $STAGE/return_to_oneui.sh
                fi
            fi
            # Nothing restarts the guest's surfaceflinger either: once
            # guest_start.sh has started it (its takeover.log line), 30 s
            # without one is a black screen for good, so it need not wait for
            # ONEOS_RETURN_BLACK. S23 Ultra session 99ef8224: it aborted 27 s
            # into the switch and the phone was force-restarted 47 s later
            # (temp root lost), long before the 150 s.
            if pidof surfaceflinger >/dev/null || ! grep -q 'SurfaceFlinger PID:' $STAGE/data/takeover.log 2>/dev/null; then
                sfgone=0
            else
                sfgone=\$((sfgone + 10))
                if [ \$sfgone -ge 30 ]; then
                    echo \"\$(date) black screen after \${t}s (the guest's surfaceflinger gone for \${sfgone}s, nothing restarts it), returning to One UI\"
                    exec /system/bin/sh $STAGE/return_to_oneui.sh
                fi
            fi
            failed=\$(timeout 10 logcat -d -b main -s SurfaceFlinger 2>/dev/null | grep -c 'presentOrValidate failed\|executeCommands failed')
            # Only failures since the last check: a burst early in the boot must
            # not end a session that recovered.
            new_failed=\$((failed - prev_failed)); [ \$new_failed -lt 0 ] && new_failed=\$failed; prev_failed=\$failed
            # HW overlays are on for every guest since 0.4.76 (guest_prepare.sh).
            # guest_start.sh forces GPU composition when the composer rejects
            # frames in the first 30 s; the same here for the rest of the session
            # (the other panel of a Fold, a layer the composer first meets
            # later), once, before the black-screen return below gets to count
            # those frames: the session goes on as it ran up to 0.4.75.
            # Not on the first count (the log can still hold an earlier session's).
            if [ \"\${hwcarm:-0}\" = 1 ] && [ \$new_failed -gt 30 ] && [ -f $STAGE/data/oneos_hwc ] && [ ! -e $STAGE/data/oneos_hwc_forced ]; then
                GP=\$(pidof system_server | awk '{print \$1}'); [ -n \"\$GP\" ] || GP=\$(pidof surfaceflinger | awk '{print \$1}')
                if [ -n \"\$GP\" ]; then
                    : > $STAGE/data/oneos_hwc_forced
                    echo \"\$(date) composer rejected \$new_failed frames with HW overlays on: GPU composition forced: \$(timeout 10 $BB nsenter -t \$GP -m /system/bin/sh /data/oneos_genv.sh /system/bin/service call SurfaceFlinger 1008 i32 1 2>&1 | tr '\n' ' ')\"
                    new_failed=0
                fi
            fi
            hwcarm=1
            # 0.4.63: the boot animation first, then the activator's log again. The
            # dismissal could land between the read of wm above and this check (the
            # failed-frames count takes up to 10 s): A17 4G ColorOS 95faf6cb was sent
            # back 1 s after its first boot's bootanim was dismissed, home on its way.
            # The activator logs the dismissal before it kills bootanim.
            ba=\$(pidof bootanimation)
            [ \$wm = 0 ] && [ \"\$(grep -c 'Dismissing bootanim' /data/local/tmp/ui_activator.log 2>/dev/null)\" -gt \"\${wmbase:-0}\" ] && wm=1
            if [ \$t -ge $RETURN_BLACK ] && { ! pidof surfaceflinger >/dev/null || [ \$new_failed -gt 100 ] || { [ \$home = 0 ] && [ -z \"\$ba\" ] && { [ \$wm = 0 ] || [ \$wmseen -ge 120 ]; }; }; }; then
                echo \"\$(date) black screen after \${t}s (surfaceflinger: \$(pidof surfaceflinger), bootanimation: \$(pidof bootanimation), new failed frames: \$new_failed), returning to One UI\"
                exec /system/bin/sh $STAGE/return_to_oneui.sh
            fi
            if [ $SESSION_MAX -gt 0 ] && [ \$total -ge $SESSION_MAX ]; then
                echo \"\$(date) session limit ${SESSION_MAX}s reached (home: \$home), returning to One UI\"
                exec /system/bin/sh $STAGE/return_to_oneui.sh
            fi
            [ \$home = 1 ] && [ \$t -ge $((RETURN_MAX - 10)) ] && t=$((RETURN_MAX - 20))
        done
        echo \"\$(date) guest still not booted after ${RETURN_MAX}s, returning to One UI\"
        exec /system/bin/sh $STAGE/return_to_oneui.sh
    " </dev/null >>"$STAGE/auto_return.log" 2>&1 &
    echo "Auto-return to One UI armed: ${RETURN_BLACK}s on a black screen, ${RETURN_MAX}s at most"
    echo "Back to One UI in the guest's OneOS app: watching $GUEST_RETURN_REQ"
    # A way back to One UI from the hardware keys (run 32: only Restart in
    # ColorOS's power menu ended a session): hold Volume Up and Volume Down
    # together for 3 s. Host side, so it works whatever ColorOS is doing; it
    # only sets the request the watcher above acts on (within a second).
    # Only the key devices are read (getevent never grabs them, ColorOS still
    # gets the keys), so touches cost nothing. ONEOS_RETURN_KEYS=0 turns it off.
    # ColorOS also takes this chord as its accessibility shortcut, aimed at
    # TalkBack, which it turned on in run 34; guest_prepare.sh empties the
    # shortcut in the staged settings (ONEOS_GUEST_A11Y_SHORTCUT=1 keeps it).
    if [ "${ONEOS_RETURN_KEYS:-1}" = 1 ]; then
        KS="$STAGE/return_keys"; rm -rf "$KS"; mkdir -p "$KS"
        KTOK="$$.$(date +%s)"; echo "$KTOK" > "$KS/session"
        # Stamp this boot: return_to_oneui.sh only kills a listed PID when the
        # boot matches (and the PID is still a oneos_switch.sh shell).
        cat /proc/sys/kernel/random/boot_id 2>/dev/null > "$KS/boot"
        KDEVS=$(getevent -pl 2>/dev/null | awk '/^add device/ { dev = $NF } /KEY_VOLUME(UP|DOWN)/ { print dev }' | sort -u)
        for kd in $KDEVS; do
            # Like the watcher: not in the app cgroup, never OOM-killed (the
            # getevent and the loop below inherit it from this subshell; the
            # builtin echo writes as the subshell, and 0 means the writer).
            ( echo 0 > /sys/fs/cgroup/cgroup.procs 2>/dev/null
              echo -1000 > /proc/self/oom_score_adj 2>/dev/null
              getevent -lq "$kd" 2>/dev/null | while read -r typ code val rest; do
                # A later switch (or none: the stage's file gone) ends this
                # reader; getevent then ends on its next write.
                [ "$(cat "$KS/session" 2>/dev/null)" = "$KTOK" ] || exit 0
                case "$code" in KEY_VOLUMEUP) k=up ;; KEY_VOLUMEDOWN) k=down ;; *) continue ;; esac
                echo "$val" > "$KS/$k"
                if [ "$(cat "$KS/up" 2>/dev/null)" = DOWN ] && [ "$(cat "$KS/down" 2>/dev/null)" = DOWN ]; then
                    tok="$(date +%s).$RANDOM"; echo "$tok" > "$KS/both"
                    ( sleep 3
                      [ "$(cat "$KS/both" 2>/dev/null)" = "$tok" ] && [ "$(cat "$KS/up")" = DOWN ] && [ "$(cat "$KS/down")" = DOWN ] &&
                          echo "$(date) Volume Up + Volume Down held 3 s" >> "$STAGE/auto_return.log" &&
                          setprop oneos.guest.powerctl "keys:volume-up+down" ) &
                else
                    : > "$KS/both"
                fi
            done ) </dev/null >/dev/null 2>&1 &
            echo $! >> "$KS/pids"
        done
        echo "Return to One UI: hold Volume Up + Volume Down for 3 s (key devices: $(echo $KDEVS))"
    fi
fi

echo "=== TAKEOVER LAUNCHED SUCCESSFULLY ==="
