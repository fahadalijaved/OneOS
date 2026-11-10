#!/system/bin/sh
# Loads the guest ROM's build properties into the shared property area.
#
# The container has no init of its own, so nothing reads the guest's build.prop
# files: the guest system_server only ever sees the host's (Samsung's) props.
# ColorOS gates a lot of its framework on ro.oplus.* / persist.oplus.* values
# that only exist in its own prop files. Only props the host does not define
# are added, so One UI keeps its own values, and every added name is recorded
# so `guest_props.sh remove` can delete them again on the way back.
#
# Usage: guest_props.sh add <rootfs> | remove | snapshot-persist | store-on |
#        restore-persist | recover
STAGE="${STAGE:-/data/local/tmp/oneos}"
ADDED="$STAGE/guest_props.added"
# Host values that `add` overrides for the session (key=host value);
# `remove` puts them back before One UI's system_server reads them.
OVR="$STAGE/guest_props.overridden"
# Names `remove` blanked instead of deleting (see remove), for this boot
# (guest_props.blanked.boot): while still empty they are the guest's, and the
# next session's `add` writes into their slots again.
BLANKED="$STAGE/guest_props.blanked"
# The root manager's own resetprop (KernelSU, APatch), never a search of /data.
# Missing is fatal: exiting 0 here (OneLineage) skipped the persist snapshot and
# its restore without a word, and One UI then booted with the guest's settings.
RP=""
for c in /data/adb/ksu/bin/resetprop /data/adb/ap/bin/resetprop /debug_ramdisk/resetprop /sbin/resetprop; do
    [ -x "$c" ] && { RP=$c; break; }
done
[ -n "$RP" ] || [ "${ONEOS_APP:-0}" = 1 ] || RP=$(command -v resetprop 2>/dev/null)
if [ -z "$RP" ] || [ ! -x "$RP" ]; then
    echo "guest_props: ERROR: resetprop not found"
    exit 1
fi
SNAP_FILE="$STAGE/persist_props.snapshot"
MARK="$STAGE/persist_session.active"
BOOT_ID=$(cat /proc/sys/kernel/random/boot_id 2>/dev/null)
sha() { sha256sum "$1" 2>/dev/null | cut -d' ' -f1; }
mark_field() { sed -n "s/^$1=//p" "$MARK" 2>/dev/null | head -n 1; }
# The persist snapshot is only ever used when this stage's own session took it:
# persist_session.active (format 2, written by snapshot-persist) holds its
# sha256 and the sha256 of the app's stage marker .oneos_stage ("none" without
# one). A snapshot from an older stage (OneLineage's, or one set up before the
# app adopted the stage) could lack props One UI has now, and restore-persist
# deletes every persist prop missing from the snapshot.
snapshot_trusted() {
    [ -f "$MARK" ] && [ -f "$SNAP_FILE" ] || return 1
    [ "$(mark_field format)" = 2 ] || return 1
    [ -n "$(mark_field snapshot)" ] && [ "$(mark_field snapshot)" = "$(sha "$SNAP_FILE")" ] || return 1
    sm=none; [ -f "$STAGE/.oneos_stage" ] && sm=$(sha "$STAGE/.oneos_stage")
    [ "$(mark_field stage_marker)" = "$sm" ]
}
# Moved aside, never deleted: $STAGE/attic/<epoch>/.
set_aside() {
    a="$STAGE/attic/$(date +%s)"
    mkdir -p "$a" || return 1
    for f in "$@"; do [ -e "$f" ] && mv -f "$f" "$a/"; done
    echo "guest_props: moved to $a:$(for f in "$@"; do printf ' %s' "${f##*/}"; done)"
}
# Props set with resetprop -n live in memory only: after a reboot the lists of
# a session that never returned name nothing, and replaying an old
# guest_props.overridden would set whatever an older stage wrote there (the
# remove of a hard reset). `add` records the boot in guest_props.boot.
# The session's own copy of One UI's property store (store-on, 0.4.60). A guest
# saves its persist.* settings through the shared property service, and init
# writes them to /data/property, One UI's store; the return then had to delete
# them, from the store and from memory. A deleted property keeps its slot in
# /dev/__properties__ until the phone restarts, and the next session adds the
# same names in new slots: vivo OriginOS adds about 380 at runtime (its audio
# policy), about 95 KB of default_prop a session, so the eighth run left too
# little for a second session without a restart. With a tmpfs copy over
# /data/property from the moment One UI's framework is down, the guest's
# settings never reach One UI's store: the return unmounts the copy (One UI's
# store is as it was), blanks the guest's names in memory instead of deleting
# them, and the next session writes into the same slots. A restart during the
# session drops the copy with it. ONEOS_PROPS_SESSION_STORE=0 keeps the old way.
STORE_MARK="$STAGE/property_session.active"
PD=/data/property
pd_mounted() { awk -v d="$PD" '$5 == d' /proc/self/mountinfo | grep -q .; }
store_off() {
    pd_mounted || return 0
    # toybox umount -D: never detach a loop device (deploy-phone.sh; a tmpfs has none).
    umount -D "$PD" 2>/dev/null || umount -D -l "$PD" 2>/dev/null
    ! pd_mounted
}

drop_stale_memory_lists() {
    if [ -f "$STORE_MARK" ] && [ "$(cat "$STORE_MARK" 2>/dev/null)" != "$BOOT_ID" ]; then
        rm -f "$STORE_MARK"
        echo "guest_props: the session property store is from before this boot, dropped (the copy died with the reboot)"
    fi
    if [ -f "$BLANKED" ] && [ "$(cat "$BLANKED.boot" 2>/dev/null)" != "$BOOT_ID" ]; then
        rm -f "$BLANKED" "$BLANKED.boot"
        echo "guest_props: guest_props.blanked is from before this boot, dropped (its props died with the reboot)"
    fi
    if [ -f "$STAGE/guest_props.boot" ]; then
        [ "$(cat "$STAGE/guest_props.boot" 2>/dev/null)" = "$BOOT_ID" ] && return 0
    else
        bt=$(awk '/^btime/ {print $2}' /proc/stat 2>/dev/null)
        [ -n "$bt" ] || return 0
        for f in "$ADDED" "$OVR"; do
            [ -f "$f" ] && [ "$(stat -c %Y "$f" 2>/dev/null)" -ge "$bt" ] 2>/dev/null && return 0
        done
    fi
    for f in "$ADDED" "$OVR"; do
        [ -f "$f" ] && rm -f "$f" && echo "guest_props: ${f##*/} is from before this boot, dropped (its props died with the reboot)"
    done
    rm -f "$STAGE/guest_props.boot"
    return 0
}

case "$1" in
add)
    ROOTFS="$2"
    HOST="$STAGE/host_props.txt"
    NEW="$STAGE/guest_props.new"
    # A session that never returned left its overrides in place: put One UI's
    # values back first, so they are what gets saved again. Only lists from
    # this boot (see drop_stale_memory_lists).
    drop_stale_memory_lists
    if [ -f "$OVR" ]; then
        while IFS= read -r line; do "$RP" -n "${line%%=*}" "${line#*=}" 2>/dev/null; done < "$OVR"
        rm -f "$OVR"
    fi
    echo "$BOOT_ID" > "$STAGE/guest_props.boot"
    # One getprop for the whole host set instead of one per key. An empty
    # value counts as unset (as for Android's readers), so the props an
    # earlier session of this boot blanked (remove) are the guest's again;
    # persist.* ones only by the list, since One UI stores its own empty ones.
    getprop | awk -v bf="$BLANKED" '
        BEGIN { while ((getline k < bf) > 0) b[k] = 1 }
        {
            i = index($0, "]: ["); if (substr($0, 1, 1) != "[" || i < 3) next
            k = substr($0, 2, i - 2)
            if (substr($0, i + 4) == "]" && (k !~ /^persist\./ || (k in b))) next
            print k
        }' > "$HOST"
    # The image's system_ext and product: inside system in MysticGSI's merged
    # images; at the image root in HyperOS's, where system/system_ext and
    # system/product are absolute links (-> /system_ext, /product) that root
    # follows to One UI's own files here on the host. Until the eighth HyperOS
    # run the guest got none of its product, system_ext or mi_ext props (no
    # ro.miui.ui.font.* or ro.miui.ui.version.code: themes, fonts and
    # wallpapers did not apply and the launcher's own pages drew no text).
    # From root partitions only ro.* keys, and no vendor, surface_flinger,
    # nnapi or odm ones: their persist.*, debug.*, dalvik.* and bluetooth.*
    # keys are Xiaomi's tuning for its own 10-core chip and daemons (core sets
    # 8-9, persist.sys.stability.reboot_days, vendor.zram.disable, traced's
    # relay port), and One UI's daemons share this property area.
    GSE="$ROOTFS/system/system_ext"; GPR="$ROOTFS/system/product"; ROOTPARTS=""
    [ -L "$GSE" ] && GSE="$ROOTFS/system_ext" && ROOTPARTS="$ROOTPARTS $GSE/etc/build.prop"
    [ -L "$GPR" ] && GPR="$ROOTFS/product" && ROOTPARTS="$ROOTPARTS $GPR/etc/build.prop"
    [ -n "$ROOTPARTS" ] && ROOTPARTS="$ROOTPARTS $ROOTFS/mi_ext/etc/build.prop"
    # Lowest priority first; a later file wins for a key defined twice.
    {
        ls "$ROOTFS"/system/build.prop \
           "$ROOTFS"/system/system_ext/etc/build.prop \
           "$ROOTFS"/system/product/etc/build.prop \
           "$ROOTFS"/my_*/build.prop \
           "$ROOTFS"/my_*/etc/build.prop 2>/dev/null | while read -r f; do
            case "$f" in "$ROOTFS"/system/build.prop|"$ROOTFS"/my_*) cat "$f" ;; *) [ -L "${f%/etc/build.prop}" ] || cat "$f" ;; esac
        done
        for f in $ROOTPARTS; do
            [ -f "$f" ] && [ ! -L "$f" ] || continue
            grep -E '^[ \t]*ro\.' "$f" | grep -v -E '^[ \t]*ro\.(vendor|surface_flinger|nnapi|odm)\.'
        done
    } |
    awk -v hostfile="$HOST" '
        BEGIN { while ((getline k < hostfile) > 0) host[k] = 1 }
        /^[ \t]*(#|import|$)/ { next }
        {
            i = index($0, "="); if (i < 2) next
            key = substr($0, 1, i - 1); val = substr($0, i + 1)
            sub(/\?$/, "", key)
            if (key ~ /[^A-Za-z0-9._-]/ || (key in host)) next
            # Never configure the HOST daemons through the shared property
            # area. ColorOS sets apexd.config.compressed_apex=false; the
            # host apexd, started on demand by the guest, then cleaned up
            # /data/apex/decompressed under the APEXes One UI had mounted
            # (dm-verity I/O errors, SIGBUS in the One UI package parser,
            # boot loop). No apostrophes in here: this is a quoted awk script.
            # rild: the phone radio daemon reads vendor.rild.libpath when it
            # (re)starts; vivo OriginOS (MediaTek) sets mtk-ril.so.
            if (key ~ /^(persist\.)?(apexd|ro\.apex|ro\.boot|ro\.bootimage|ro\.crypto|ro\.hardware|ro\.vndk|ro\.zygote|init|vold|ro\.vold|sys\.usb|persist\.sys\.usb|ro\.adb|ro\.debuggable|ro\.secure|selinux|ro\.build\.selinux|ro\.kernel|ro\.dalvik\.vm\.native\.bridge|vendor\.rild|rild|ro\.vendor\.rild)\./) next
            if (key ~ /^(apexd|ro\.apex|init|vold|selinux)$/) next
            # Key attestation reports these as the device identity (KeyMint
            # checks them against the phone): always the phone values, never
            # the guest image ones (Pixel ships a yogi set).
            if (key ~ /_for_attestation$/) next
            if (!(key in seen)) order[n++] = key
            seen[key] = 1; value[key] = val
        }
        END { for (j = 0; j < n; j++) print order[j] "=" value[order[j]] }
    ' > "$NEW"
    # Window-level blur (run 31: glass UI flat in places). The Find N6 turns
    # it on in its vendor build.prop, which the GSI does not carry. The guest
    # SurfaceFlinger logged "Disabling blur effects, they are not supported."
    # (run 30 all.log), its RenderEngine chose blur algorithm None and
    # WindowManager had mBlurEnabled=false (run 31 diag_40). ColorOS's capture
    # blur (BlurService) still drew the shade and Control Center, but whatever
    # asks SurfaceFlinger for a background blur or checks
    # isCrossWindowBlurEnabled fell back to a flat dim: dialogs, the black
    # power menu, QS detail panels, the app drawer and Recents backdrop. The
    # guest framework reads it with getBoolean(..., true) and WindowManager
    # still said false, so One UI most likely defines it as 0: override it for
    # the session. ONEOS_GUEST_BLUR=0 leaves it alone.
    if [ "${ONEOS_GUEST_BLUR:-1}" = 1 ]; then
        BLUR=ro.surface_flinger.supports_background_blur
        if grep -qxF "$BLUR" "$HOST"; then
            hv=$(getprop "$BLUR")
            if [ "$hv" != 1 ] && "$RP" -n "$BLUR" 1 2>/dev/null; then
                echo "$BLUR=$hv" >> "$OVR"
                echo "guest_props: $BLUR=$hv overridden to 1 for the session (window blur)"
            fi
        elif ! grep -q "^$BLUR=" "$NEW"; then
            echo "$BLUR=1" >> "$NEW"
        fi
    fi
    # ColorOS's animation level. OPPO's launcher turns its material blur on
    # only when persist.sys.oplus.anim_level is a valid level
    # (PlatformLevelUtils ii.l.h(): 1-4): the app drawer needs level 1
    # (BlurUtils.isSupportDrawerBlur, ii.l.g(1)), folder and card blur 1 or 2
    # (isMaterialBlurJumpSupported, via OplusBlurProperties.isSupportNewBlur).
    # Nothing in the guest sets it (no build.prop the add above loads, One UI
    # neither): the launcher logged "animationLevelOS14 = -1" (0.4.40
    # b9110fc3, 0.4.55 4933a41d), CardBackgroundBlurManager supportBlur=false
    # even after the material blur switch was turned on, and BlurService only
    # ever blurred the shade. 1 = the top level (A+). ColorOS only: Infinity-X
    # also ships oplus-services.jar but has no oplus-telephony-common.jar.
    # Memory only and in the added list, so remove blanks it again.
    # ONEOS_GUEST_ANIM_LEVEL=0 leaves it unset; 2, 3 or 4 sets that level.
    AL=persist.sys.oplus.anim_level; ALV=${ONEOS_GUEST_ANIM_LEVEL:-1}
    case "$ALV" in 1|2|3|4) ;; *) ALV="" ;; esac
    if [ -n "$ALV" ] && { grep -q '"image": "coloros17-findn6"' "$STAGE/.oneos_stage" ||
            { [ -f "$GSE/framework/oplus-telephony-common.jar" ] && [ -e "$ROOTFS/system/framework/oplus-services.jar" ]; }; }; then
        # A previous return can leave an empty property name behind. Treat an
        # empty host/guest value as missing, while recording any host override.
        if grep -qxF "$AL" "$HOST"; then
            hv=$(getprop "$AL")
            if [ -z "$hv" ] && "$RP" -n "$AL" "$ALV"; then
                echo "$AL=$hv" >> "$OVR"
                echo "guest_props: empty $AL overridden to $ALV for this ColorOS session"
            fi
        elif ! grep -q '^persist\.sys\.oplus\.anim_level=.' "$NEW"; then
            sed -i '/^persist\.sys\.oplus\.anim_level=/d' "$NEW"
            echo "$AL=$ALV" >> "$NEW"
            echo "guest_props: $AL=$ALV for the session (ColorOS launcher material blur level)"
        fi
    fi
    if grep -q '"image": "coloros17-findn6"' "$STAGE/.oneos_stage"; then
        # Framework animation/Gaussian tiers use 3 for high-end; COUI's
        # separate anim_level above uses 1. Apply both before guest processes.
        for kv in ro.launcher.blur.appLaunch=1 ro.oplus.animationlevel=3 ro.oplus.gaussianlevel=3; do
            key=${kv%%=*}; value=${kv#*=}
            if grep -qxF "$key" "$HOST"; then
                hv=$(getprop "$key")
                if [ "$hv" != "$value" ] && "$RP" -n "$key" "$value"; then echo "$key=$hv" >> "$OVR"; fi
            else
                sed -i "/^$key=/d" "$NEW"
                echo "$key=$value" >> "$NEW"
            fi
            echo "guest_props: $key=$value for this ColorOS session"
        done
    fi
    # Fold and unfold in ColorOS took 2-3 s to show the other panel (owner,
    # 11-10, Z Fold8 Ultra; One UI is instant). That session's log: the guest's
    # thermal status was CRITICAL (its skin estimate 47 C), the framework then
    # caps rendering at 0-60 Hz and the 120 Hz floor we set drops out; 1-3 ms
    # after the newly lit panel was powered this SurfaceFlinger chose 1 Hz for
    # it, SystemUI could not draw its first frame and the display switch sat out
    # its 2 s sync timeout. Below CRITICAL the range is [120, 120] and the swap
    # is instant. This image's SurfaceFlinger ranks "Power On Imminent" before
    # idle and content (read in its binary): while a panel is not on yet, and
    # for this many ms after its power mode changed, it takes the top of the
    # allowed range (60 Hz under the cap, 120 otherwise). The timer is made per
    # display and only when the property is above 0; One UI does not define it.
    # The thermal cap itself is not touched. Only for the image it was read in.
    # ONEOS_GUEST_SF_POWER_TIMER=0 leaves it out, another number is that many ms.
    PT=ro.surface_flinger.set_display_power_timer_ms; PTV=${ONEOS_GUEST_SF_POWER_TIMER:-1000}
    case "$PTV" in [1-9]|[1-9][0-9]|[1-9][0-9][0-9]|[1-9][0-9][0-9][0-9]) ;; *) PTV="" ;; esac
    if [ -n "$PTV" ] && grep -q '"image": "coloros17-findn6"' "$STAGE/.oneos_stage"; then
        if grep -qxF "$PT" "$HOST"; then
            hv=$(getprop "$PT")
            case "$hv" in
                [1-9]*) echo "guest_props: $PT is One UI's $hv, kept" ;;
                *) if "$RP" -n "$PT" "$PTV"; then
                       echo "$PT=$hv" >> "$OVR"
                       echo "guest_props: $PT overridden to $PTV for this ColorOS session"
                   fi ;;
            esac
        else
            sed -i '/^ro\.surface_flinger\.set_display_power_timer_ms=/d' "$NEW"
            echo "$PT=$PTV" >> "$NEW"
            echo "guest_props: $PT=$PTV for this ColorOS session (a newly lit panel starts at the top of the allowed refresh range)"
        fi
    fi
    # One UI's color mode (oneos_switch.sh, host_color_mode), read by the
    # guest's SurfaceFlinger at start: it no longer moves the panels between
    # SRGB and DISPLAY_P3 with what is on screen (Pixel, session 9455098f: a
    # flash on each switch). Memory only and in the added list, like the
    # others. ONEOS_GUEST_COLOR_MODE=0 leaves the guest's own choice; a number
    # forces that mode.
    CM=persist.sys.sf.color_mode; CMV=${ONEOS_GUEST_COLOR_MODE:-$(cat "$STAGE/host_color_mode" 2>/dev/null)}
    case "$CMV" in [1-9]|[1-9][0-9]) ;; *) CMV="" ;; esac
    if [ -n "$CMV" ] && ! grep -qxF "$CM" "$HOST" && ! grep -q '^persist\.sys\.sf\.color_mode=' "$NEW"; then
        echo "$CM=$CMV" >> "$NEW"
        echo "guest_props: $CM=$CMV for the session (One UI's color mode)"
    fi
    # OxygenOS 16 on a MediaTek Galaxy (A34): the guest's SurfaceFlinger hung in RenderEngine's
    # GL driver load ("Threaded RenderEngine with SkiaGL Backend", then nothing; system_server's
    # watchdog then killed the session: 0.4.67 deb8690c, 6d4eaf85, 91b699cf, 1dd827e1). ColorOS
    # on the MediaTek A16 4G runs SkiaVk and gets past it: Vulkan RenderEngine for this pair.
    # debug.* goes back to One UI's value at the return (return_to_oneui.sh). Test in 0.4.69;
    # ONEOS_GUEST_RE_BACKEND overrides (empty: the image's own choice).
    # Why SkiaGL stopped there: OPPO's SkiaGLRenderEngine::create (the image's surfaceflinger, BuildId
    # 8b4eaee1, create at 0x70d160) first reads persist.sys.renderengine.retry and, when set (the
    # image's build.prop: =1), waits 200 ms at a time until /sys/class/kgsl/kgsl-3d0/gpu_model opens:
    # Adreno's node, which no Mali, Xclipse or MediaTek GPU has (A33 0.4.69 d741af95
    # diag_40_native_surfaceflinger: the RenderEngine thread in usleep at create+924, the main
    # thread in waitUntilInitialized). Without that node: 0 for the session, so the GL path starts.
    # ONEOS_GUEST_RE_RETRY=1 leaves the image's value.
    RR=persist.sys.renderengine.retry
    if [ ! -e /sys/class/kgsl/kgsl-3d0/gpu_model ] && [ "${ONEOS_GUEST_RE_RETRY:-0}" != 1 ]; then
        if grep -qxF "$RR" "$HOST"; then
            hv=$(getprop "$RR")
            case "$hv" in 1|true) "$RP" -n "$RR" 0 && echo "$RR=$hv" >> "$OVR" &&
                echo "guest_props: $RR=$hv overridden to 0 for the session (no Adreno: SkiaGL would wait for kgsl forever)" ;; esac
        elif grep -q "^persist\.sys\.renderengine\.retry=\(1\|true\)$" "$NEW"; then
            sed -i "/^persist\.sys\.renderengine\.retry=/d" "$NEW"
            echo "$RR=0" >> "$NEW"
            echo "guest_props: $RR=0 for the session (no Adreno: SkiaGL would wait for kgsl forever)"
        fi
    fi
    RE=debug.renderengine.backend
    REV=""
    if grep -q '"image": "oxygenos' "$STAGE/.oneos_stage" 2>/dev/null; then
        # 0.4.70: the Exynos phones too (Mali on the A54 d0f664a8 and A26 de5d8a87, Xclipse on the S23 FE
        # be228999: the same stop after "Threaded RenderEngine with SkiaGL"); the Snapdragon S22 Ultra's
        # Adreno got past it (15cf8a3f), so Qualcomm keeps the image's own choice.
        case "$(getprop ro.board.platform)$(getprop ro.hardware)$(getprop ro.soc.manufacturer)" in
            *mt[0-9]*|*[Mm]edia[Tt]ek*|*s5e[0-9]*|*erd[0-9]*|*exynos*|*[Ss]amsung*) REV=skiavkthreaded ;;
        esac
        # But Vulkan never starts on Samsung's Mali driver (Exynos 1280, Mali-G68 r32p1): SkiaVk aborts
        # "GrDirectContext creation failed" on its first, unprotected context (createContexts+152), 3 s
        # after the start, every time (A33 0.4.72 560d4195 boot.log.01:84362, A53 0.4.71 5cf23f6b,
        # A25 0.4.72 08a96294). One UI's own surfaceflinger runs SkiaGL on that driver, and with the
        # retry wait off (above) so can the guest's: the image's choice there. The Xclipse Exynos
        # (S22, S23 FE) and the MediaTek Mali (A34) start with Vulkan and keep it.
        if grep -qxF "$RR" "$HOST"; then rrv=$(getprop "$RR"); else rrv=$(sed -n 's/^persist\.sys\.renderengine\.retry=//p' "$NEW" | tail -n 1); fi
        # 0.4.81: this test read ro.board.platform alone ("s5e*"), and the A25 and A33 say
        # "universal8825" there (s5e8825 is their ro.hardware), so 0.4.74 never came here on
        # the phones it was written for: every A25/A33 OxygenOS report of 0.4.72 to 0.4.74
        # ran Vulkan and aborted the same way (A25 1578c3e9, 5979f592, b0f57229, e213e9be,
        # ee0546c3; A33 0dbc9e00, 2368e662, ce33e392, ead48ebc). Now the three properties
        # of the test above, MediaTek first (the A34 and A24 start with Vulkan). And the
        # retry wait is switched off by name here, whatever set or did not set it: an
        # unset, blank or leftover value must not decide whether SkiaGL waits for kgsl.
        # Untested on a real A25/A33 until the first 0.4.81 report: look for this line.
        REP="$(getprop ro.board.platform)/$(getprop ro.hardware)/$(getprop ro.soc.manufacturer)"
        case "$REP" in
            *mt[0-9]*|*[Mm]edia[Tt]ek*) ;;
            *s5e[0-9]*|*erd[0-9]*|*exynos*|*universal[0-9]*|*[Ss]amsung*)
                if [ -e /vendor/lib64/egl/libGLES_mali.so ] && [ ! -e /sys/class/kgsl/kgsl-3d0/gpu_model ]; then
                    case "$rrv" in
                        1|true) echo "guest_props: Mali Exynos ($REP) with $RR=$rrv: Vulkan RenderEngine kept (SkiaGL would wait for kgsl)" ;;
                        *) REV=""
                            case "$rrv" in
                                0|false) ;;
                                *)  if grep -qxF "$RR" "$HOST"; then
                                        "$RP" -n "$RR" 0 && echo "$RR=$rrv" >> "$OVR"
                                    else
                                        sed -i "/^persist\.sys\.renderengine\.retry=/d" "$NEW"
                                        echo "$RR=0" >> "$NEW"
                                    fi ;;
                            esac
                            echo "guest_props: Mali Exynos ($REP): the image's RenderEngine (SkiaGL; SkiaVk fails on this driver), $RR=0 (was '$rrv')" ;;
                    esac
                fi ;;
        esac
    fi
    REV=${ONEOS_GUEST_RE_BACKEND-$REV}
    if [ -n "$REV" ]; then
        case "$REV" in *[!a-z]*) REV="" ;; esac
    fi
    if [ -n "$REV" ]; then
        if grep -qxF "$RE" "$HOST"; then
            hv=$(getprop "$RE")
            if "$RP" -n "$RE" "$REV"; then
                echo "$RE=$hv" >> "$OVR"
                echo "guest_props: $RE $hv -> $REV for this session (Vulkan RenderEngine)"
            fi
        else
            sed -i "/^debug\.renderengine\.backend=/d" "$NEW"
            echo "$RE=$REV" >> "$NEW"
            echo "guest_props: $RE=$REV for this session (Vulkan RenderEngine)"
        fi
    fi
    # The boot animation on the panel that is on. AOSP's bootanimation draws on
    # the first display persist.service.bootanim.displays lists, at that
    # display's size, else on SurfaceFlinger's primary: a Fold's inner panel.
    # Switched while folded, Pixel played it on the dark inner panel and the
    # cover stayed black until Home (Z Fold8 Ultra, 2026-11-06). Folded (the
    # inner backlight at 0, the cover's lit): the cover's id from
    # host_cover_display. Memory only and in the added list, like the others.
    # ONEOS_GUEST_BOOTANIM_COVER=0 leaves it on the primary.
    BAD=persist.service.bootanim.displays
    CVID=$(sed -n 's/^local:\([0-9][0-9]*\) .*/\1/p' "$STAGE/host_cover_display" 2>/dev/null)
    BL0=/sys/class/backlight/panel0-backlight; BL1=/sys/class/backlight/panel1-backlight
    [ -d "$BL0" ] || { BL0=/sys/class/backlight/panel; BL1=/sys/class/backlight/panel1; }
    if [ "${ONEOS_GUEST_BOOTANIM_COVER:-1}" = 1 ] && [ -n "$CVID" ] &&
            [ "$(cat "$BL0/brightness" 2>/dev/null)" = 0 ] && [ "$(cat "$BL1/brightness" 2>/dev/null || echo 0)" != 0 ] &&
            ! grep -qxF "$BAD" "$HOST" && ! grep -q '^persist\.service\.bootanim\.displays=' "$NEW"; then
        echo "$BAD=$CVID" >> "$NEW"
        echo "guest_props: $BAD=$CVID for the session (folded: the boot animation on the cover)"
    fi
    # USB functions AOSP does not define. Samsung's persist.sys.usb.config is
    # "sec_charging,adb"; UsbManager.usbFunctionsFromString knows no
    # sec_charging and throws IllegalArgumentException, which killed the guest
    # system_server on the android.fg thread in UsbDeviceManager.finishBoot
    # (first Nothing run, 2026-10-31; its UsbHandlerLegacy reads the persist
    # prop). The live sys.usb.config is already a plain AOSP value on this
    # phone (mtp,adb), so the guest gets that for the session, and "adb" alone
    # if it is not. Memory only: init watches sys.usb.config, not this one, so
    # nothing is reconfigured by the override itself, and One UI's own value
    # goes back with remove and restore-persist.
    # ONEOS_GUEST_USB_CONFIG=0 leaves it alone.
    if [ "${ONEOS_GUEST_USB_CONFIG:-1}" = 1 ]; then
        UCK=persist.sys.usb.config
        huv=$(getprop "$UCK")
        case ",$huv," in
            *,sec_*)
                nuv=$(getprop sys.usb.config)
                case ",$nuv," in ""|*,sec_*|,,) nuv=adb ;; esac
                if grep -qxF "$UCK" "$HOST" && "$RP" -n "$UCK" "$nuv" 2>/dev/null; then
                    echo "$UCK=$huv" >> "$OVR"
                    echo "guest_props: $UCK=$huv overridden to $nuv for the session (AOSP's UsbManager rejects sec_charging)"
                fi
                ;;
        esac
    fi
    # Bluetooth audio offload (run 44: the earbuds connected, audio stayed on the
    # speaker). A2DP keeps One UI's offload: Samsung's QTI HAL turns its offload
    # path on from the vendor parameter l_a2dp_format, which guest_start.sh now
    # sends (the HAL analysis: no property decides it; with offload forced off
    # the guest policy still connected A2DP on the primary module and the
    # bluetooth module's stream failed). LE Audio stays in software: the same
    # HAL bit drives the LE paths, and LE ports sit on the primary module too.
    # Memory only, One UI's value goes back with remove and restore-persist.
    # ColorOS guests keep the host values. ONEOS_GUEST_BT_OFFLOAD=1 leaves LE alone.
    # One guest-only prop out of the list (key, dots taken literally); 1 if the
    # list did not have it.
    drop_new() {
        dk=$(printf '%s' "$1" | sed 's/[.]/\\./g')
        grep -q "^$dk=" "$NEW" || return 1
        sed -i "/^$dk=/d" "$NEW"
    }
    GUEST_OPLUS=0
    [ -f "$ROOTFS/system/framework/oplus-services.jar" ] && GUEST_OPLUS=1
    # ColorOS's records of its last boot's kind, when One UI's own property store holds one
    # (owner's Fold, 11-10: persist.sys.oplus.my_carrier.data_utc_backup with a date of August,
    # written there by a session from before the store was kept apart (0.4.81); every One UI
    # boot loads it and every return restores it as One UI's). The image has no such date, so
    # OplusRemovableAppManager.isBootFromCotaUpdate took every start for the first one after a
    # carrier-package update: "Upgrading from ...", every preinstalled app scanned and copied
    # to data/app again, 30 "Failed to scan ... we try again" per boot. Blank for the session,
    # memory only: ColorOS reads no record ("first boot consider as false", the path of 41 of
    # the 45 ColorOS boots in the reports of 0.4.72 to 0.4.74) and writes its own, which the
    # return drops. One UI's values go back with remove and restore-persist; its store is not
    # touched. sys.oplus.bootupgrade is ColorOS's note of such a boot, left set by the session
    # before (no One UI name). ONEOS_GUEST_OPLUS_BOOT_KIND=1 keeps them all.
    if [ "$GUEST_OPLUS" = 1 ] && [ "${ONEOS_GUEST_OPLUS_BOOT_KIND:-0}" = 0 ]; then
        out=""
        for k in persist.sys.oplus.my_carrier.data_utc_backup persist.sys.oplus.company.data_backup \
                 persist.sys.recopy.preload.opinstalled; do
            hv=$(getprop "$k")
            [ -n "$hv" ] || continue
            if "$RP" -n "$k" "" 2>/dev/null && [ -z "$(getprop "$k")" ]; then
                echo "$k=$hv" >> "$OVR"; out="$out $k"
            fi
        done
        if [ -n "$(getprop sys.oplus.bootupgrade)" ] && "$RP" -n sys.oplus.bootupgrade "" 2>/dev/null; then
            out="$out sys.oplus.bootupgrade"
        fi
        [ -z "$out" ] || echo "guest_props: ColorOS's last-boot records from an earlier session blanked for the session:$out"
    fi
    if [ "${ONEOS_GUEST_BT_OFFLOAD:-0}" = 0 ] && [ "$GUEST_OPLUS" = 0 ]; then
        for k in persist.bluetooth.leaudio_offload.disabled; do
            if grep -qxF "$k" "$HOST"; then
                hv=$(getprop "$k")
                if [ "$hv" != true ] && "$RP" -n "$k" true 2>/dev/null; then
                    echo "$k=$hv" >> "$OVR"
                    echo "guest_props: $k=$hv overridden to true for the session (LE Audio encoded by the guest)"
                fi
            else
                sed -i "/^$k=/d" "$NEW"
                echo "$k=true" >> "$NEW"
                echo "guest_props: $k=true for the session (LE Audio encoded by the guest)"
            fi
        done
        # The image's other LE Audio offload props, which One UI does not define
        # (run 44 review). ro.bluetooth.leaudio_offload.supported=true, with One
        # UI's leaudio_offload.disabled=false, put the Pixel stack's LE Audio
        # codec on the DSP: codec_manager.cc "configure_data_path for encode"
        # and LE_AUDIO_HARDWARE_OFFLOAD capabilities read at 17:29:36 and
        # 17:32:25 (run 44 all.log), the HAL offload path that refused A2DP.
        # Left out, LE Audio stays in software even if the override above did
        # not take. persist.bluetooth.leaudio_sw_offload and
        # persist.vendor.audio.leaudio_sw_offload are for Pixel's own audio HAL:
        # neither the image's Bluetooth module, framework, services nor
        # audioserver libraries read them, nor Samsung's libaudiocorehal.qti.so,
        # so they could only reach Samsung's audio HAL process, which is
        # restarted after this. ONEOS_GUEST_BT_OFFLOAD=1 keeps all three.
        out=""
        for k in ro.bluetooth.leaudio_offload.supported persist.bluetooth.leaudio_sw_offload persist.vendor.audio.leaudio_sw_offload; do
            drop_new "$k" && out="$out $k"
        done
        [ -z "$out" ] || echo "guest_props: left out for the session (undefined like One UI's: LE Audio encoded by the guest):$out"
    fi
    # HFP (run 44: calls routed to the earbuds stayed silent). The image's
    # product build.prop sets bluetooth.sco.managed_by_audio=true and One UI
    # does not define it, so it was added. With it, Pixel's Telecom,
    # AudioService and Bluetooth stack leave opening SCO to the audio HAL:
    # Telecom set the earbuds active and the HAL patched [Telephony Rx -> BT
    # SCO Headset], but nobody called connectAudio, the guest audioserver only
    # ever sent BT_SCO=off, the stack stayed in BTA_AG_SCO_LISTEN_ST and PAL
    # logged "BT device 7 not connected or not ready" (all.log 17:34:00 to
    # 17:34:07). Samsung's QTI HAL never opens SCO itself; One UI's stack does.
    # Undefined (false), AudioService opens SCO through the stack and sends
    # BT_SCO=on, which reaches the HAL as setScoConfig through the standard
    # IBluetooth (no vendor extension needed). ColorOS guests keep the image's
    # props. ONEOS_GUEST_SCO_MANAGED=1 keeps it.
    SCO=bluetooth.sco.managed_by_audio
    if [ "$GUEST_OPLUS" = 0 ]; then
        if [ "${ONEOS_GUEST_SCO_MANAGED:-0}" = 1 ]; then
            grep -q "^bluetooth\.sco\.managed_by_audio=" "$NEW" &&
                echo "guest_props: $(grep "^bluetooth\.sco\.managed_by_audio=" "$NEW" | tail -n 1) kept for the session (ONEOS_GUEST_SCO_MANAGED=1: SCO left to the audio HAL)"
        elif drop_new "$SCO"; then
            echo "guest_props: $SCO left out for the session (undefined like One UI's: the guest's AudioService opens SCO through the Bluetooth stack)"
        fi
    fi
    # LE Audio without Android's Bluetooth audio HAL (S25 Ultra, X9U CN, app
    # 0.4.7, session e98f44ff: Bluetooth on -> com.android.bluetooth aborted
    # 2.5 s later, 19 times in a row, "[broadcaster.cc:1532] Initialize: HAL
    # requirements not met. Init aborted.", after "HalVersionManager: No
    # supported HAL version"). One UI turns every LE Audio profile on
    # (bluetooth.profile.bap.*, csip, hap, vcp, ccp, mcp), but only the SM8850
    # phones register android.hardware.bluetooth.audio.
    # IBluetoothAudioProviderFactory/default; the SM8750 and older ones
    # (probe reports: S25+, Z Fold7, S24 Ultra, S23s) register only Samsung's
    # vendor.samsung.hardware.bluetooth.audio.ISehBluetoothAudioProviderFactory,
    # which the guest's stack does not know, and its HIDL fallback is off
    # (no hwservicemanager for it). The guest's LE Audio broadcaster then
    # aborts the whole Bluetooth process. On such a phone the LE Audio
    # profiles are off for the session (memory only, One UI's values go back
    # with remove), so classic Bluetooth starts. ONEOS_GUEST_LE_AUDIO=1 keeps
    # them. Classic (A2DP) audio then goes through oneos_btaudio, which
    # oneos_switch.sh starts after this check (0.4.33); LE Audio stays off.
    # Only `service check` (a servicemanager lookup): `service list` asks every
    # service for its interface, and One UI's surfaceflinger is frozen behind
    # the gap splash here, so it never answered and the switch hung before the
    # guest started (0.4.11, S24 Ultra session 0210fa8a: OneOS logo, black,
    # reboot). Only an explicit "not found" turns LE Audio off.
    BTA=android.hardware.bluetooth.audio.IBluetoothAudioProviderFactory/default
    if [ "${ONEOS_GUEST_LE_AUDIO:-0}" != 1 ] &&
        timeout 5 service check "$BTA" 2>/dev/null | grep -q ": not found"; then
        out=""
        for k in bluetooth.profile.bap.broadcast.source.enabled bluetooth.profile.bap.broadcast.assist.enabled \
                 bluetooth.profile.bap.unicast.client.enabled bluetooth.profile.csip.set_coordinator.enabled \
                 bluetooth.profile.hap.client.enabled bluetooth.profile.vcp.controller.enabled \
                 bluetooth.profile.ccp.server.enabled bluetooth.profile.mcp.server.enabled; do
            drop_new "$k" && out="$out $k(guest)"
            grep -qxF "$k" "$HOST" || continue
            hv=$(getprop "$k")
            if [ "$hv" != false ] && "$RP" -n "$k" false 2>/dev/null; then
                echo "$k=$hv" >> "$OVR"
                out="$out $k"
            fi
        done
        echo "guest_props: no $BTA on this phone: LE Audio off for the session:${out:- nothing was on}"
    fi
    # Power key stall (run 32: the power menu ~15 s late or missing after a
    # long press, Power + Volume Down screenshots late, folds handled late).
    # ColorOS's lib_inputflingerEx.so runs saupwkProcessKey on system_server's
    # InputReader thread for every power key press and looks up OPPO's
    # IOplusProject HAL with AServiceManager_getService, which polls for 5 s
    # when the service does not exist (it never does on this phone). Every key,
    # touch and lid event waits behind it: run 32 all.log:564703 "[theia_saupwk]
    # prepare send key event by hidl", "Waiting for service
    # 'vendor.oplus.hardware.stability.oplus_project.IOplusProject/default'",
    # 5 s later "didn't start" (25 times); 4492 EventHub "Slow read detected",
    # up to 13.2 s (all.log:579475); the lid opened at 13:11:49 was committed
    # at 13:12:03 (all.log:579291). The function first checks
    # property_get_bool(persist.sys.saupwk_test) and, when it is set, returns
    # before the HAL lookup ("test return, don't write
    # POWERKEY_InputReaderProcessKey"). Only OPPO's Theia power key statistics
    # are skipped. Memory only (resetprop -n), deleted again by remove.
    # ONEOS_GUEST_SAUPWK=0 leaves it out.
    # The panel's brightness scale for OPPO's framework (ColorOS, Infinity-X:
    # patches/OneOSPanelBacklight.smali, 0.4.36): the Z Fold8 Ultra's composer
    # floats times 5.2980394 / this panel's brightnessMaximum (One UI's dumpsys
    # display, captured by the switch; the same scale guest_prepare.sh gives
    # the display configs of the other systems). 1000 = the Fold's own.
    bm=$(grep 'DisplayDeviceInfo{' "$STAGE/display_modes_host.log" 2>/dev/null | sed -n 's/.*brightnessMaximum \([0-9.]*\).*/\1/p' | head -n 1)
    sc=$(awk -v m="$bm" 'BEGIN { if (m + 0 >= 1.5 && m + 0 <= 8) printf "%d", 5298.0394 / m + 0.5; else print 1000 }')
    sed -i '/^ro\.oneos\.panel_scale_milli=/d' "$NEW"
    echo "ro.oneos.panel_scale_milli=$sc" >> "$NEW"
    echo "guest_props: panel brightness scale $sc/1000 (One UI's brightnessMaximum ${bm:-unknown})"
    if [ "${ONEOS_GUEST_SAUPWK:-1}" = 1 ]; then
        sed -i '/^persist\.sys\.saupwk_test=/d' "$NEW"
        echo "persist.sys.saupwk_test=1" >> "$NEW"
        echo "guest_props: persist.sys.saupwk_test=1 for the session (no 5 s HAL wait per power key press)"
    fi
    # Inner screen status bar (Fold layout): the image brings the Find N6's
    # hole 2102,28:2176,102. OplusStatusBarUtils.isHoleType calls a hole
    # entirely right of the middle (2256/2 = 1128) HOLE_RIGHT, and
    # StatusBarPaddingProvider.updatePaddingLeftRight then ends the system icons
    # at the hole's left edge plus 36 px: x 2066 (run 36a all.log 07:14:27,
    # paddingResult (58, 190)), so they ran under this phone's camera at
    # 1665..1747. With the real hole they would end left of the camera and the
    # free band right of it would stay empty. A hole with left >= right is
    # NO_HOLE_TYPE: corner padding only on both sides, so the icons sit at the
    # right edge, in that band. The cover keeps the image's secondary hole.
    # ONEOS_GUEST_INNER_HOLE=image keeps the image's value.
    if [ "${ONEOS_GUEST_FORM:-fold}" = fold ] && [ "${ONEOS_GUEST_INNER_HOLE:-none}" = none ] &&
        grep -q '^ro\.oplus\.display\.screenhole\.positon=' "$NEW"; then
        sed -i 's/^ro\.oplus\.display\.screenhole\.positon=.*/ro.oplus.display.screenhole.positon=0,0:0,0/' "$NEW" &&
            echo "guest_props: ro.oplus.display.screenhole.positon=0,0:0,0 for the session (no inner hole: status icons at the right edge, right of the camera)"
    fi
    # Bar phones: the image's hole is its own phone's, compared raw with this
    # panel's width (isHoleType: left < width/2 < right is HOLE_CENTER_TYPE).
    # The S25 got the Find X9 Ultra's 679,40:762,123 on 1080 px: HOLE_RIGHT,
    # icons ended next to the camera. This phone's lens as the switch worked it
    # out from One UI's cutout (oneos_switch.sh, host_holes/host_screenhole);
    # unread = no hole, icons at the right edge. ColorOS takes it for the lens
    # itself: StatusBarPaddingProvider.updatePaddingTopBottom centres the icons
    # between its top and bottom, and the capsule (SystemUIPlugin) is its
    # height + 4 dp, centred on it. One UI's own rect from the top edge (S25
    # Ultra 685,0:755,128) made a 139 px capsule on a 128 px bar (report
    # 4933a41d), and below QHD+ an Ultra's rect was 3/4 size (695,0:747,96).
    # ONEOS_GUEST_INNER_HOLE=image keeps the image's value here too.
    if [ "${ONEOS_GUEST_FORM:-fold}" != fold ] && [ "${ONEOS_GUEST_INNER_HOLE:-none}" = none ] &&
        grep -q '^ro\.oplus\.display\.screenhole\.positon=' "$NEW"; then
        h=$(cat "$STAGE/host_screenhole" 2>/dev/null) what="this phone's camera hole"
        echo "$h" | grep -qx '[0-9]\{1,5\},[0-9]\{1,5\}:[0-9]\{1,5\},[0-9]\{1,5\}' ||
            { h="0,0:0,0"; what="no hole, this phone's was not read"; }
        was=$(sed -n 's/^ro\.oplus\.display\.screenhole\.positon=//p' "$NEW" | tail -n 1)
        sed -i "s/^ro\.oplus\.display\.screenhole\.positon=.*/ro.oplus.display.screenhole.positon=$h/" "$NEW" &&
            echo "guest_props: ro.oplus.display.screenhole.positon=$h for the session ($what; the image's: $was)"
    fi
    # AppSearch isolated storage: Pixel sets ro.appsearch.feature.enable_isolated_storage=true,
    # and system_server's AppSearch then starts a protected VM through the
    # virtualization APEX, which is One UI's here (run 41: UnsatisfiedLinkError in
    # libvirtualmachine_jni, appsearch crashed twice; had it loaded, the guest would
    # have run a VM on One UI's virtualizationservice, like composd). Off for the
    # session; the property is only read when system_server starts.
    if grep -q '^ro\.appsearch\.feature\.enable_isolated_storage=true$' "$NEW"; then
        sed -i 's/^ro\.appsearch\.feature\.enable_isolated_storage=.*/ro.appsearch.feature.enable_isolated_storage=false/' "$NEW" &&
            echo "guest_props: ro.appsearch.feature.enable_isolated_storage=false for the session (no AppSearch VM on One UI's virtualization service)"
    fi
    # Night Light (run 42): turning it on faded the screen to black. Pixel's
    # framework-res takes config_nightDisplayAvailable from
    # config_setColorTransformAccelerated, which Pixel's own vendor overlay sets
    # and Samsung's vendor (the guest's) does not: the colour matrix stayed all
    # zeros ("The color transform's last row must be (0, 0, 0, 1)", "Could not
    # invert colorTransform!"). The image's static
    # product/overlay/treble-overlay-NightMode.apk sets it to true when
    # persist.sys.overlay.nightmode=true, which nothing sets. Added with the
    # others: memory only (resetprop -n), never in persistent storage; remove
    # deletes it, and restore-persist deletes every persist prop the switch's
    # snapshot (taken before this) lacks. Only with that overlay in the image
    # (Pixel), and not over a value One UI has. ONEOS_GUEST_NIGHT_LIGHT=0 leaves
    # it out.
    NM=persist.sys.overlay.nightmode
    if [ "${ONEOS_GUEST_NIGHT_LIGHT:-1}" = 1 ] && { [ -f "$ROOTFS/system/product/overlay/treble-overlay-NightMode.apk" ] && [ ! -L "$ROOTFS/system/product" ]; }; then
        if grep -qxF "$NM" "$HOST"; then
            echo "guest_props: $NM is One UI's ($(getprop "$NM")), left alone"
        else
            sed -i '/^persist\.sys\.overlay\.nightmode=/d' "$NEW"
            echo "$NM=true" >> "$NEW"
            echo "guest_props: $NM=true for the session (Night Light: the image's treble NightMode overlay)"
        fi
    fi
    # HyperOS on a fold: Xiaomi's fold flag lives in the phone's vendor props,
    # which the GSI does not carry. MiWallpaper (a fold build: the image is
    # Xiaomi's fold lhasa) loads the cover screen's two wallpaper records only
    # when persist.sys.muiltdisplay_type is 2, then reads them anyway, and
    # crashed at every start without them (sixth HyperOS run: NPE in
    # WallpaperTypeUtils.f for which=4/8, no wallpaper). MiuiMultiDisplayTypeInfo
    # reads the same value for the rest of HyperOS (isFoldDevice: without it
    # the seventh run laid HyperOS's phone UI out on the inner panel, "zoomed
    # in", and the theme pickers failed). Memory only, blanked by remove,
    # never over a value One UI has. The image's own fold_disp marks a fold
    # build; not $NEW, which skips it: One UI defines ro.config.fold_disp too
    # (Samsung's "2256,2504,1080,2520"), so the run 6 check never matched.
    MDT=persist.sys.muiltdisplay_type
    if [ "${ONEOS_GUEST_FORM:-fold}" = fold ] && grep -q '^ro\.config\.fold_disp=' "$ROOTFS"/system/build.prop "$ROOTFS"/mi_ext/etc/build.prop 2>/dev/null &&
        { [ -e "$ROOTFS/system/system_ext/framework/miui-services.jar" ] || [ -e "$ROOTFS/system_ext/framework/miui-services.jar" ]; }; then
        if grep -qxF "$MDT" "$HOST"; then
            echo "guest_props: $MDT is One UI's ($(getprop "$MDT")), left alone"
        else
            sed -i '/^persist\.sys\.muiltdisplay_type=/d' "$NEW"
            echo "$MDT=2" >> "$NEW"
            echo "guest_props: $MDT=2 for the session (HyperOS fold: cover screen wallpapers)"
        fi
    fi
    # HyperOS's rust runtime (its launcher among the packages): the image's
    # init.hyos_spawner.rc sets rust.runtime_version when zygote runs and
    # starts hyos_spawner on rust.runtime_active=1, and system_server sends
    # rust packages to the spawner only while that is 1. One UI's init has
    # neither; guest_start.sh starts the spawner, and the two values are added
    # here so that remove deletes them again (system_server sets the second
    # one itself as well).
    if [ -f "$ROOTFS/system/system_ext/bin/hyos_spawner" ] || [ -f "$ROOTFS/system_ext/bin/hyos_spawner" ]; then
        for kv in rust.runtime_version=3.1.0 rust.runtime_active=1; do
            k=${kv%%=*}
            grep -qxF "$k" "$HOST" && { echo "guest_props: $k is One UI's ($(getprop "$k")), left alone"; continue; }
            sed -i "/^$(echo "$k" | sed 's/\./\\./g')=/d" "$NEW"
            echo "$kv" >> "$NEW"
        done
        echo "guest_props: rust.runtime_version=3.1.0 rust.runtime_active=1 for the session (HyperOS rust packages through hyos_spawner)"
    fi
    # HyperOS's telephony (xiaomi-opt-telephony.jar, XmTelephonyUtils.ModemProvider)
    # takes the modem's maker from ro.vendor.radio.modem.provider, else from
    # ro.mi.os.soc.vendor, which the image's own build.prop sets to xring. On
    # "xring" VendorRIL.setupDataCall goes to Xiaomi's radio extension
    # (RadioInterfaceManager, setupDataCallEx), which Samsung's vendor never
    # registers: run 10 "onSetupDataCallComplete. resultCode = 4", cause
    # RADIO_NOT_AVAILABLE, no mobile data. With "qcom" (the Snapdragon modem
    # it is) every data call takes RIL's own IRadioData path. One UI's vendor
    # does not define the name.
    if { [ -f "$ROOTFS/system/system_ext/framework/xiaomi-opt-telephony.jar" ] || [ -f "$ROOTFS/system_ext/framework/xiaomi-opt-telephony.jar" ]; } &&
        ! grep -qxF ro.vendor.radio.modem.provider "$HOST"; then
        if [ "$(getprop ro.soc.manufacturer)" = QTI ]; then
            sed -i '/^ro\.vendor\.radio\.modem\.provider=/d' "$NEW"
            echo "ro.vendor.radio.modem.provider=qcom" >> "$NEW"
            echo "guest_props: ro.vendor.radio.modem.provider=qcom for the session (HyperOS data calls through IRadioData, not Xiaomi's XRING extension)"
        else
            echo "guest_props: ro.vendor.radio.modem.provider left unset: $(getprop ro.soc.manufacturer) is not a Qualcomm SoC"
        fi
    fi
    # HyperOS's XRING helpers fail on every frame and log each time: libxqos
    # ("XQos: Failed to open /dev/xr_fbt" and "Failed to initialize", 300,000
    # lines in run 10's 12 minutes, 258,000 in run 6's four), SurfaceFlinger's
    # PerfFlinger client (17,000) and the Dolby renderer's metadata reads
    # (51,000): a third of the session's log and of OneOS's capture. liblog
    # checks log.tag.<tag> before it formats a line; S drops these three tags
    # in every process. Xiaomi's and Dolby's own tags only, never AOSP ones
    # (BufferQueueProducer and SurfaceFlinger carry real errors too). Run 11
    # added: RadioProxyEx (Xiaomi's radio extension proxy, never ready on
    # Samsung's vendor: 9,500 lines a file), com.xiaomi.type (Xiaomi's
    # keyboard dumping its key table, 8,000) and, down to W only, AdrenoVK-0
    # (Qualcomm's Vulkan driver: "Unknown struct ... provided to
    # vkCmdBeginRenderPass" on every frame HyperOS draws, 16,600 a file).
    if [ -f "$ROOTFS/system/lib64/libxqos.so" ]; then
        for tl in XQos:S perfflinger_client:S DolbyRenderer:S RadioProxyEx:S com.xiaomi.type:S AdrenoVK-0:W; do
            k=log.tag.${tl%:*}
            grep -qxF "$k" "$HOST" && { echo "guest_props: $k is One UI's ($(getprop "$k")), left alone"; continue; }
            sed -i "/^$(echo "$k" | sed 's/\./\\./g')=/d" "$NEW"
            echo "$k=${tl##*:}" >> "$NEW"
        done
        echo "guest_props: log.tag.XQos, perfflinger_client, DolbyRenderer, RadioProxyEx, com.xiaomi.type = S and AdrenoVK-0 = W for the session (failures and dumps on every frame or call)"
        # HyperOS's SurfaceFlinger pre-warms its shaders at start with fake
        # layers, and died there on two phones (0.4.38): S24 Ultra 548e7b73
        # SIGSEGV in DolbyRenderer::requiresDolbyEffect, A57 609d7c2f abort
        # "input buffer not gpu readable", both under Cache::primeShaderCache;
        # the guest stayed black and OneOS returned. Off for the session: the
        # shaders compile on first use instead (the Z Fold8 Ultra primed fine).
        k=service.sf.prime_shader_cache
        if grep -qxF "$k" "$HOST"; then
            echo "guest_props: $k is One UI's ($(getprop "$k")), left alone"
        else
            sed -i "/^service\.sf\.prime_shader_cache=/d" "$NEW"
            echo "$k=0" >> "$NEW"
            echo "guest_props: $k=0 for the session (HyperOS's SurfaceFlinger died pre-warming shaders on the S24 Ultra and A57)"
        fi
    fi
    # Chrome draws nothing in the Nothing OS guest: its renderers never start
    # (cr_ChildProcessConn "Failed to establish the service connection" 20
    # times a page, run 11), while WebView in other apps works. One UI's
    # log.tag is E, which the guest shares, so ActivityManager and the zygote
    # said nothing about why. These tags at I for the session only (log.tag.*
    # is not persistent), Nothing OS guests only, until the cause is known.
    if [ -f "$GSE/framework/nt-telephony-common.jar" ]; then
        # One UI's camera port (run 19: lens switches slow, which camera opens
        # where): the camera service's opens, closes and evictions, and the
        # app's device manager, at I. The policy's power presses (WindowManager at D:
        # "powerPress: ... count=", run 26: a double press opened nothing, no line).
        for tl in ActivityManager:I Zygote:I AppZygoteInit:I ActiveServices:I cr_ChildProcessConn:V cr_ChildProcLH:V cr_ChildProcessService:V cr_LibraryLoader:V \
                  CameraService:I Camera3-Device:I CameraDeviceClient:I CameraProviderManager:I CameraDeviceManager:I CameraContext:I \
                  ServiceManagerCppClient:I ServiceManagerCppClientCallback:I CameraServiceWorkerWrapper:I \
                  WindowManager:D SingleKeyGesture:D; do
            k=log.tag.${tl%:*}
            grep -qxF "$k" "$HOST" && { echo "guest_props: $k is One UI's ($(getprop "$k")), left alone"; continue; }
            sed -i "/^$(echo "$k" | sed 's/\./\\./g')=/d" "$NEW"
            echo "$k=${tl##*:}" >> "$NEW"
        done
        echo "guest_props: ActivityManager, Zygote, AppZygoteInit, ActiveServices and the camera service's tags at I, Chrome's child process tags at V for the session"
    fi
    # HyperOS's libhwui encodes JPEG and HEIF through Xiaomi's XRING VPU
    # (JpegXEncoder) and waits for vendor.xring.hardware.graphics.vpu.jpeg.
    # IJpegXCodecStore/default, which Samsung's vendor never registers: every
    # Bitmap.compress hung (run 9: wallpaper apply, the lock screen editor's
    # apply and screenshots, system_server's own wallpaper thread). With bit 0
    # of debug.video.jpegopt.enable / heifopt.enable clear (default 1) Skia
    # uses libjpeg and its HEIF encoder. Only when the image's libhwui reads
    # them; not the vendor.video.* ones, which One UI's vendor might read.
    if grep -qF debug.video.jpegopt.enable "$ROOTFS/system/lib64/libhwui.so" 2>/dev/null; then
        for kv in debug.video.jpegopt.enable=0 debug.video.heifopt.enable=0; do
            k=${kv%%=*}
            grep -qxF "$k" "$HOST" && { echo "guest_props: $k is One UI's ($(getprop "$k")), left alone"; continue; }
            sed -i "/^$(echo "$k" | sed 's/\./\\./g')=/d" "$NEW"
            echo "$kv" >> "$NEW"
        done
        echo "guest_props: debug.video.jpegopt.enable=0 debug.video.heifopt.enable=0 for the session (no XRING JPEG/HEIF codec)"
    fi
    # ColorOS's first-boot clock. OplusNewNetworkTimeUpdateServiceFeature.
    # checkSystemTime (oplus-services.jar) takes every boot with
    # persist.sys.device_first_boot unset (default true) for the phone's first
    # and sets the clock to 1 January of the build year: the shared kernel
    # clock read 2026-01-01 until network time came back (Galaxy S26+ 80387c66,
    # S25 Ultra 485d5ffa), and the Galaxy S23 (699602d7) returned to One UI on
    # it. 0 for the session. Since 0.4.39 also over a value One UI has (its
    # persist props are saved above and restored on the return): it was left
    # alone then, and on an S25 Ultra (cdd75ef8) the reset came back, every
    # HTTPS check failed on the clock and Google said offline.
    # One UI's own value goes on the override list (put back on the return,
    # as persist.sys.usb.config above); a key One UI lacks is added and removed.
    key=persist.sys.device_first_boot
    if [ -f "$ROOTFS/system/framework/oplus-services.jar" ] || [ -f "$ROOTFS/system/system_ext/framework/oplus-services.jar" ]; then
        if grep -qxF "$key" "$HOST"; then
            hv=$(getprop "$key")
            if [ "$hv" = 0 ]; then
                echo "guest_props: $key=0 already (One UI's), no first-boot clock reset"
            elif "$RP" -n "$key" 0 2>/dev/null; then
                echo "$key=$hv" >> "$OVR"
                echo "guest_props: $key=$hv overridden to 0 for the session (no first-boot clock reset to 1 January)"
            fi
        else
            sed -i "/^$key=/d" "$NEW"
            echo "$key=0" >> "$NEW"
            echo "guest_props: $key=0 for the session (no first-boot clock reset to 1 January)"
        fi
    fi
    # Fold cover screens: the image's cover hole is its own phone's (Find N6:
    # 534..606), and ColorOS reads it while oplus_system_folding_mode is not 1
    # (OplusStatusBarUtils.getScreenHoleParam). On the Z Fold5's 904 px cover
    # that is right of the middle: HOLE_RIGHT_TYPE, the icons ended at the real
    # camera, 423..482 (report 4efbf1e8: "isHoleType stableDisplayWidth: 904,
    # holeLeftPosition 534,holeRightPosition 606 ,holeType HOLE_RIGHT_TYPE",
    # paddingResult (51, 402)). Only the Z Fold8 had its own (pull request #1).
    # This cover's lens, from One UI's cover cutout (oneos_switch.sh,
    # host_cover_screenhole). The Z Fold8 keeps pull request #1's rule, which
    # was accepted on that phone: One UI's cover rect (host_holes) centred in
    # ColorOS's 48 dp = 126 px cover bar, its size and x kept; 589,11:659,115
    # when it was not read. Session-only, removed on return.
    # ONEOS_GUEST_COVER_HOLE=image keeps the image's value.
    key=ro.oplus.display.secondary.screenhole.position
    if [ "${ONEOS_GUEST_FORM:-fold}" = fold ] && [ "${ONEOS_GUEST_COVER_HOLE:-host}" != image ] &&
       grep -q '^ro\.oplus\.display\.' "$NEW"; then
        h=$(cat "$STAGE/host_cover_screenhole" 2>/dev/null) what="this cover's lens"
        if [ "${ONEOS_PROFILE:-}" = f8 ] && grep -q '^  "image": "coloros17-findn6",$' "$STAGE/.oneos_stage"; then
            r=$(sed -n 's/^cover [^ ]* [0-9]* \([0-9]*,[0-9]*:[0-9]*,[0-9]*\) .*/\1/p' "$STAGE/host_holes" 2>/dev/null | head -n 1)
            h=$(echo "$r" | awk -F '[:,]' 'NF==4 && $1~/^[0-9]+$/ && $2~/^[0-9]+$/ && $3~/^[0-9]+$/ && $4~/^[0-9]+$/ && $3>$1 && $4>$2 && $4-$2<=126 {top=int((126-($4-$2))/2);printf "%d,%d:%d,%d",$1,top,$3,top+$4-$2}')
            what="the Z Fold8's rule from pull request #1, One UI's cover rect ${r:-not read}"
            [ -n "$h" ] || h=589,11:659,115
        elif ! echo "$h" | grep -qx '[0-9]\{1,5\},[0-9]\{1,5\}:[0-9]\{1,5\},[0-9]\{1,5\}'; then
            h='' what=''
        fi
        if [ -n "$h" ]; then
            was=$(sed -n "s/^$key=//p" "$NEW" | tail -n 1)
            sed -i "/^$key=/d" "$NEW"
            echo "$key=$h" >> "$NEW"
            echo "guest_props: $key=$h for the session ($what; the image's: ${was:-none})"
        else
            echo "guest_props: $key kept (the image's; this cover's lens was not read)"
        fi
    fi
    # Nothing OS: haptics through the phone's own vibrator. Nothing's feature
    # bit 139 (bits from ro.build.nothing.feature.base, flipped by the diff
    # props; NtFeaturesUtilsImpl) sends every vibration to AAC's RichTap
    # (VintfHalVibrator's on() -> NtVibratorManagerImpl.ntVibrateOn), which it
    # finds as IVibrator/default's extension. On a Galaxy that extension is
    # Samsung's, so every RichTap call failed ("aac richtap doVibratorStop
    # fail") and nothing vibrated (run 14: 1 HAL vibration in the session).
    # The base with that bit cleared (hex digit 35 from the right, value 8; the
    # number is too long for awk's arithmetic). No diff of this image sets it.
    # ONEOS_GUEST_NT_RICHTAP=1 keeps the image's value.
    key=ro.build.nothing.feature.base
    v=$(sed -n "s/^$key=//p" "$NEW" | tail -n 1)
    if [ -n "$v" ] && [ "${ONEOS_GUEST_NT_RICHTAP:-0}" != 1 ]; then
        nv=$(echo "$v" | awk '{
            s = $0; pre = ""; suf = ""
            if (substr(s, 1, 2) == "0x" || substr(s, 1, 2) == "0X") { pre = substr(s, 1, 2); s = substr(s, 3) }
            if (substr(s, length(s)) == "L") { suf = "L"; s = substr(s, 1, length(s) - 1) }
            if (length(s) < 35) { print $0; exit }
            p = length(s) - 34; d = tolower(substr(s, p, 1)); h = "0123456789abcdef"
            x = index(h, d) - 1
            if (x < 0) { print $0; exit }
            if (x >= 8) x -= 8
            print pre substr(s, 1, p - 1) substr(h, x + 1, 1) substr(s, p + 1) suf }')
        if [ -n "$nv" ] && [ "$nv" != "$v" ]; then
            sed -i "/^$key=/d" "$NEW"
            echo "$key=$nv" >> "$NEW"
            echo "guest_props: $key without feature 139 (RichTap haptics) for the session"
        fi
    fi
    # ONEOS_GUEST_LOG_INFO=1 (a debug session, off by default): every tag at I
    # for the session, so app-level logs (the camera's RecordingSession, the
    # activity starts) reach the capture; One UI's own level is E. Restored on
    # return like every session prop.
    if [ -n "$v" ] && [ "${ONEOS_GUEST_LOG_INFO:-0}" = 1 ]; then
        if grep -qxF log.tag "$HOST"; then
            echo "guest_props: log.tag is One UI's ($(getprop log.tag)), left alone"
        else
            sed -i '/^log\.tag=/d' "$NEW"
            echo "log.tag=I" >> "$NEW"
            echo "guest_props: log.tag=I for this debug session"
        fi
    fi
    # vivo OriginOS: each vivo feature lookup in zygote (android.util.FtFeature
    # through VivoConfigStorePropertyHelper) first waits up to 11 x 50 ms for
    # vendor.vivoconfigstore.ready, which vivo's vendor config store sets
    # ("vivoconfigstore is not ready , wait 50ms again"). Samsung's vendor has
    # none, so every lookup cost 550 ms. Set for the session when One UI has no
    # such key: the features then read as unsupported at once, as they would
    # after the wait (their ro.vendor.<feature>:vivo-support props are vivo's
    # vendor's). ONEOS_GUEST_VIVO_CFG=0 leaves it out.
    if [ -f "$ROOTFS/system/framework/vivo-services.jar" ] && [ "${ONEOS_GUEST_VIVO_CFG:-1}" = 1 ] &&
       [ -z "$(getprop vendor.vivoconfigstore.ready)" ]; then
        sed -i '/^vendor\.vivoconfigstore\.ready=/d' "$NEW"
        echo "vendor.vivoconfigstore.ready=1" >> "$NEW"
        echo "guest_props: vendor.vivoconfigstore.ready=1 (no 550 ms wait per vivo feature lookup)"
    fi
    # The garbage collector the image's ART code was compiled for (0.4.60). An
    # image's boot image (system/framework/boot.art) and its apps' odex files
    # are built for one collector: CC, with read barriers, or CMC (userfaultfd),
    # without. vivo's OriginOS says ro.dalvik.vm.enable_uffd_gc=false (product
    # build.prop) and One UI says true, so the guest's zygote ran CMC and
    # refused the boot image ("ValidateOatFile found read barrier state
    # mismatch", tenth OriginOS run): the whole framework went through the JIT
    # in every process, slow and hot. The image's own value for the session
    # when it has one and it differs; One UI's goes back with remove.
    # ONEOS_GUEST_IMAGE_GC=0 keeps One UI's.
    UK=ro.dalvik.vm.enable_uffd_gc
    UFILES="$ROOTFS/system/build.prop"
    for d in system_ext product; do
        if [ -L "$ROOTFS/system/$d" ]; then UFILES="$UFILES $ROOTFS/$d/etc/build.prop"; else UFILES="$UFILES $ROOTFS/system/$d/etc/build.prop"; fi
    done
    UIV=$(for f in $UFILES; do [ -f "$f" ] && [ ! -L "$f" ] && cat "$f"; done 2>/dev/null |
          sed -n 's/^[ \t]*ro\.dalvik\.vm\.enable_uffd_gc=//p' | tail -n 1)
    # Proven on vivo OriginOS only (0.4.73; its odrefresh step builds the boot image for
    # this collector): other systems keep One UI's value unless ONEOS_GUEST_IMAGE_GC=1.
    IGC_DEF=0; [ -f "$ROOTFS/system/framework/vivo-services.jar" ] && IGC_DEF=1
    if [ "${ONEOS_GUEST_IMAGE_GC:-$IGC_DEF}" = 1 ] && [ -n "$UIV" ] && grep -qxF "$UK" "$HOST"; then
        UHV=$(getprop "$UK")
        if [ "$UHV" != "$UIV" ] && "$RP" -n "$UK" "$UIV" 2>/dev/null; then
            echo "$UK=$UHV" >> "$OVR"
            echo "guest_props: $UK=$UHV overridden to $UIV for the session (the collector the image's boot image is built for)"
        fi
    fi
    # vivo OriginOS on a Fold: vivo's fold mode is a build property, not a
    # feature. The X500 Pro Max image says ro.vivo.device.type=phone, so the
    # seventh run laid the phone UI out on the inner panel and the launcher
    # restarted at each fold. foldable for the session (the key is already the
    # image's, blanked on return; no new name). Goes with the vivo device states
    # (guest_prepare.sh, 0 CLOSE and 1 OPEN) and the LogicalDisplayMapper guards
    # (patches/vivo_guards.py). Mode 1 (ONEOS_GUEST_VIVO_FOLD=1), the default on a
    # Fold since 0.4.73 (F8U runs 14-24: the inner panel's own layout, Themes fine
    # once the manufacturer check was fixed, brightness with vivo_guards' phone
    # brightness path); 2 keeps the apps a bar phone's (below), 0 "phone" everywhere.
    if [ -f "$ROOTFS/system/framework/vivo-services.jar" ] && [ "${ONEOS_GUEST_FORM:-fold}" = fold ] &&
       [ "${ONEOS_GUEST_VIVO_FOLD:-1}" = 1 ] && grep -qx 'ro.vivo.device.type=phone' "$NEW"; then
        sed -i 's/^ro\.vivo\.device\.type=.*/ro.vivo.device.type=foldable/' "$NEW" &&
            echo "guest_props: ro.vivo.device.type=foldable for the session (vivo fold mode; the image's: phone)"
    fi
    # vivo's display and input side (SurfaceFlinger, libinputflinger, libinputservice,
    # libandroid_servers; make-overlays.sh) read ro.oneos.vivo.dtype for vivo's device
    # type: "foldable" in fold modes 1 and 2, so both panels work. Mode 2
    # (ONEOS_GUEST_VIVO_FOLD=2) leaves ro.vivo.device.type the image's "phone" for
    # everything else: vivo's apps took foldable paths their phone build lacks in
    # mode 1 in the tenth CN run (Themes crashed: the manufacturer check, fixed since).
    # Mode 2 lays the inner panel out as a stretched phone; mode 1 is the default
    # (above); a bar phone (ONEOS_GUEST_FORM=phone) is "phone".
    if [ -f "$ROOTFS/system/framework/vivo-services.jar" ]; then
        VDT=phone
        [ "${ONEOS_GUEST_FORM:-fold}" = fold ] && case "${ONEOS_GUEST_VIVO_FOLD:-1}" in 1|2) VDT=foldable ;; esac
        sed -i '/^ro\.oneos\.vivo\.dtype=/d' "$NEW"
        echo "ro.oneos.vivo.dtype=$VDT" >> "$NEW"
        echo "guest_props: ro.oneos.vivo.dtype=$VDT (vivo's display and input side; apps: $(grep '^ro\.vivo\.device\.type=' "$NEW" | tail -n 1 | cut -d= -f2))"
    fi
    # Nothing OS's ringtones: NothingGenerateRingtoneService composes each with a
    # Glyph pattern from libgenerative_glyph, which sizes it by Nothing's vendor
    # props (ro.vendor.glyph.*, the Phone (3)'s 25 x 25 matrix). Samsung's
    # /vendor has none, so every pattern came out all zero frames; the service
    # deleted it, took a new seed and tried again, 31 246 times in four minutes
    # at full speed on its main thread (run 16: the phone hot, no ringtone, ANR
    # after 200 s and a restart scheduled). The Metroid vendor image's values,
    # for the session. No light is driven: nothing here has a Glyph device.
    # ONEOS_GUEST_NT_GLYPH=0 leaves them out.
    if [ -n "$v" ] && [ "${ONEOS_GUEST_NT_GLYPH:-1}" = 1 ]; then
        for kv in ro.vendor.glyph.row=25 ro.vendor.glyph.column=25 ro.vendor.glyph.matrix_channels=625 \
                  ro.vendor.glyph.channels=489 ro.vendor.glyph.generative.simulation.multiple=4; do
            sed -i "/^${kv%%=*}=/d" "$NEW"
            echo "$kv" >> "$NEW"
        done
        echo "guest_props: Nothing Glyph matrix 25 x 25 for the ringtone generator"
    fi
    # Nothing OS's About phone reads this phone's hardware once its "own phone"
    # mode is on (switcher/overlays/nothing_about): RAM from ro.boot.ddr_size
    # (MB; /proc/meminfo's total without it, 11 GB on the 12 GB Fold8 Ultra),
    # the processor's name from ro.product.cpu_info, and the screen line as
    # <screen_physical_size>" <ro.vendor.display.panel.type>. All from the
    # phone: RAM rounded up to the next usual size, the SoC by its model, the
    # panels' diagonals from the switch's display capture (pixels / dpi). The
    # activator takes the inner size and the battery's design capacity from
    # $STAGE/nt_about.txt for the two strings. ONEOS_GUEST_NT_ABOUT=0 leaves them.
    if [ -n "$v" ] && [ "${ONEOS_GUEST_NT_ABOUT:-1}" = 1 ]; then
        gb=$(awk '/^MemTotal:/ { g = $2 / 1048576; n = split("4 6 8 12 16 24 32 48 64", s, " "); for (i = 1; i <= n; i++) if (s[i] + 0 >= g) { print s[i]; exit } }' /proc/meminfo)
        case "$(getprop ro.soc.model)" in
            SM8850) cpu="8 Elite Gen 5" ;;
            SM8750) cpu="8 Elite" ;;
            SM8650) cpu="8 Gen 3" ;;
            SM8550) cpu="8 Gen 2" ;;
            s5e9965) cpu="Exynos 2600" ;;
            s5e9955) cpu="Exynos 2500" ;;
            *) cpu="" ;;
        esac
        # The Folds' overlay says "Qualcomm Snapdragon %s"; every other phone's
        # (0.4.35, guest_prepare.sh) only "%s", so the name is whole here.
        case "${ONEOS_PROFILE:-f8u}" in
            f8u|f8|f7|f6) ;;
            *) case "$cpu" in ''|Exynos*) ;; *) cpu="Snapdragon $cpu" ;; esac ;;
        esac
        # One "<diagonal>" per built-in panel, the largest first.
        sizes=$(awk '/DisplayDeviceInfo\{"Built-in Screen"/ {
                if (match($0, /, [0-9]+ x [0-9]+,/)) { split(substr($0, RSTART + 2, RLENGTH - 3), r, " x ") } else next
                if (match($0, /, [0-9.]+ x [0-9.]+ dpi/)) { split(substr($0, RSTART + 2, RLENGTH - 6), d, " x ") } else next
                if (d[1] + 0 <= 0 || d[2] + 0 <= 0) next
                printf "%d\n", sqrt((r[1] / d[1]) ^ 2 + (r[2] / d[2]) ^ 2) * 10 }' "$STAGE/display_modes_host.log" 2>/dev/null |
            sort -rn | awk '{ printf "%d.%d\n", $1 / 10, $1 % 10 }')
        inner=$(echo "$sizes" | sed -n 1p); cover=$(echo "$sizes" | sed -n 2p)
        mah=$(awk '{ printf "%d", $1 / 1000 }' /sys/class/power_supply/battery/charge_full_design 2>/dev/null)
        for kv in "ro.boot.ddr_size=${gb:+$((gb * 1024))}" "ro.product.cpu_info=$cpu" \
                  "ro.vendor.display.panel.type=${cover:+inner, $cover\" cover}"; do
            [ -n "${kv#*=}" ] || continue
            sed -i "/^${kv%%=*}=/d" "$NEW"
            echo "$kv" >> "$NEW"
        done
        { echo "screen=$inner"; echo "battery=$mah"; } > "$STAGE/nt_about.txt"
        echo "guest_props: Nothing About phone: ${gb:-?} GB, ${cpu:-?}, panels ${inner:-?}\" ${cover:+and $cover\" }, ${mah:-?} mAh"
    fi
    if "$RP" -n -f "$NEW" 2>/dev/null; then
        cut -d= -f1 "$NEW" > "$ADDED"
    else
        # Older resetprop without -f: fall back to one call per prop.
        : > "$ADDED"
        while IFS= read -r line; do
            "$RP" -n "${line%%=*}" "${line#*=}" 2>/dev/null && echo "${line%%=*}" >> "$ADDED"
        done < "$NEW"
    fi
    echo "guest_props: added $(wc -l < "$ADDED") props from the guest's build.prop files"
    rm -f "$HOST" "$NEW"
    # ColorOS's default sounds. One UI defines ro.config.ringtone,
    # notification_sound and alarm_alert, so the guest read Samsung's names (run
    # 30, Settings_RingtoneUtils: "getInternalRingtoneUri ACH_Galaxy_Bells.ogg
    # null") and RingtoneManager.ensureDefaultRingtones never set a default
    # ringtone or notification sound. For these keys only, the guest's file name
    # wins for the session (guest_prepare.sh stages the files).
    # ONEOS_GUEST_RINGTONES=0 keeps One UI's names.
    if [ "${ONEOS_GUEST_RINGTONES:-1}" = 1 ]; then
        for key in ro.config.ringtone ro.config.notification_sound ro.config.alarm_alert; do
            # The same files and order as above (Pixel sets these in product).
            g=$(cat "$ROOTFS"/system/build.prop "$GSE"/etc/build.prop \
                "$GPR"/etc/build.prop "$ROOTFS"/my_*/build.prop "$ROOTFS"/mi_ext/etc/build.prop 2>/dev/null | sed -n "s/^$key=//p" | tail -n 1)
            h=$(getprop "$key")
            [ -n "$g" ] && [ -n "$h" ] && [ "$g" != "$h" ] || continue
            echo "$key=$h" >> "$OVR" && "$RP" -n "$key" "$g" 2>/dev/null &&
                echo "guest_props: $key=$g for the session (One UI: $h)"
        done
    fi
    # The audio HAL adapter's vendor extension. One UI sets
    # ro.audio.ihaladaptervendorextension_enabled=true; the Pixel GSI sets false
    # (no such service on another vendor). With One UI's value the guest
    # audioserver waited forever in DeviceHalAidl initCheck for
    # IHalAdapterVendorExtension/default (run 38: 123 failed starts, no
    # media.audio_flinger). The guest's value wins for the session, the same way
    # as the sound names; ColorOS's images set true, like One UI.
    # With false the guest audioserver forwards no vendor keys to the HAL at
    # all: libaudiohal drops them without a log line and AudioFlinger still
    # returns OK (run 43: SIM 2 calls silent, g_call_sim_slot never arrived).
    # g_call_sim_slot then reaches the HAL only through guest_start.sh's call
    # keeper, which sends it to IModule/default directly while this is not true.
    for key in ro.audio.ihaladaptervendorextension_enabled; do
        g=$(cat "$ROOTFS"/system/build.prop "$GSE"/etc/build.prop \
            "$GPR"/etc/build.prop "$ROOTFS"/my_*/build.prop "$ROOTFS"/mi_ext/etc/build.prop 2>/dev/null | sed -n "s/^$key=//p" | tail -n 1)
        h=$(getprop "$key")
        [ -n "$g" ] && [ -n "$h" ] && [ "$g" != "$h" ] || continue
        echo "$key=$h" >> "$OVR" && "$RP" -n "$key" "$g" 2>/dev/null &&
            echo "guest_props: $key=$g for the session (One UI: $h)"
    done
    # vivo OriginOS: vivo's apps tell a vivo phone from another maker's by
    # ro.product.system.manufacturer (Android R and later: isNoVivoPhone is true
    # unless it is vivo, JOVI or iqoo) and then run as an overseas build. One UI
    # says samsung, so on the CN image Themes took its overseas paths, whose
    # layouts the CN build lacks (twelfth CN run: Themes, wallpapers and home
    # style crashed: VTitleBarView inflated Resource ID #0x0, the overseas
    # Settings entrance layout had no such view; Themes logged
    # "judgePhoneManufacturer: manufacturer = samsung" and used vivo's global
    # servers). The image's system manufacturer and brand for the session,
    # restored on return. ro.product.manufacturer and ro.product.brand
    # (Build.MANUFACTURER and Build.BRAND, the identity GMS sees) stay the
    # phone's. ONEOS_GUEST_VIVO_MAKER=0 keeps One UI's.
    if [ -f "$ROOTFS/system/framework/vivo-services.jar" ] && [ "${ONEOS_GUEST_VIVO_MAKER:-1}" = 1 ]; then
        for key in ro.product.system.manufacturer ro.product.system.brand; do
            g=$(sed -n "s/^$key=//p" "$ROOTFS/system/build.prop" 2>/dev/null | tail -n 1)
            h=$(getprop "$key")
            [ -n "$g" ] && [ -n "$h" ] && [ "$g" != "$h" ] || continue
            echo "$key=$h" >> "$OVR" && "$RP" -n "$key" "$g" 2>/dev/null &&
                echo "guest_props: $key=$g for the session (One UI: $h; vivo's apps run as a vivo phone's)"
        done
    fi
    # A 64-bit guest on a phone with 32-bit ABIs (Galaxy S23: zygote64_32,
    # armeabi-v7a and armeabi). The guest has no app_process32 and the switch
    # stops One UI's zygote_secondary, yet with One UI's ABI lists its
    # system_server asked for a 32-bit zygote: ZygoteProcess.bootCompleted
    # threw "Failed to inform zygote of boot_completed" and took it down
    # (1f4f0c7f, 0.4.18). The image's own lists for the session. 0.4.40: also when
    # the image has app_process32 (HyperOS, with Xiaomi's lazily started 32-bit
    # zygote): no guest gets a 32-bit zygote from OneOS, whatever its image ships.
    if [ -n "$(getprop ro.product.cpu.abilist32)" ]; then
        # A key the image's build.prop does not name (HyperOS: 0.4.40 S23 2d486da1 and
        # S23 Ultra c70e1b54 reached the lock screen, then the same boot_completed
        # crash; the loop skipped every key) gets the 64-bit-only value.
        g64=$(sed -n "s/^ro.system.product.cpu.abilist64=//p" "$ROOTFS/system/build.prop" 2>/dev/null | tail -n 1)
        for key in ro.product.cpu.abilist ro.product.cpu.abilist32 ro.system.product.cpu.abilist ro.system.product.cpu.abilist32; do
            if grep -q "^$key=" "$ROOTFS/system/build.prop" 2>/dev/null; then
                g=$(sed -n "s/^$key=//p" "$ROOTFS/system/build.prop" | tail -n 1)
            else
                case "$key" in *32) g="" ;; *) g=${g64:-arm64-v8a} ;; esac
            fi
            h=$(getprop "$key")
            [ "$g" != "$h" ] || continue
            echo "$key=$h" >> "$OVR" && "$RP" -n "$key" "$g" 2>/dev/null &&
                echo "guest_props: $key='$g' for the session (One UI: $h; the guest has no 32-bit zygote)"
        done
    fi
    # A Qualcomm-built guest on an Exynos phone (Galaxy S26+, 4cad07e6, 0.4.19).
    # ColorOS's zygote preloads libqti_performance.so only when
    # Build.IS_QCOM_PLATFORM is true, which framework.jar computes from
    # ro.boot.hardware starting with "qcom" (ZygoteInit.preloadSharedLibraries).
    # On the S26+ (ro.boot.hardware is Samsung's) nothing loaded it, every
    # com.qualcomm.qti.Performance native was "No implementation found" (over
    # 1,000 lines a session) and a game-launch broadcast dispatched on an OThread
    # took system_server down with UnsatisfiedLinkError: black screen after a
    # few seconds, then the return. QPerformance.jar is in the guest's boot image,
    # so it cannot be patched; the image's own value for the session instead,
    # whenever the guest ships that library and the phone is not Qualcomm's.
    if [ -f "$ROOTFS/system/system_ext/lib64/libqti_performance.so" ]; then
        h=$(getprop ro.boot.hardware)
        case "$h" in
            qcom*) ;;
            *) echo "ro.boot.hardware=$h" >> "$OVR" && "$RP" -n ro.boot.hardware qcom 2>/dev/null &&
                   echo "guest_props: ro.boot.hardware=qcom for the session (One UI: $h; the guest's zygote then preloads its Qualcomm perf library)" ;;
        esac
    fi
    # The platform's minor SDK version (Build.VERSION.SDK_INT_FULL, read from
    # ro.build.version.sdk_full). One UI 8.5 says 36.1 (A07/A15/A17 probes,
    # S23 FE BP4A), OxygenOS 16 is built for 36.0, and the guest framework took
    # One UI's value: apps then call the 36.1 APIs its framework does not have.
    # S23 FE 6d13b740 (0.4.72): Play services died 24 times on
    # SupervisionManager.isSupervisionEnabled (KidsSettingsModuleInit; the
    # user's Google account did not work), Chrome 4 times on
    # DisplayManager.getDisplayTopology;
    # M55s 0e73a8d6: Gboard on AccessibilityAction ACTION_SET_EXTENDED_SELECTION
    # (no keyboard). The S22 Ultra on One UI 8.0 (BP2A, 36.0) had none of them.
    # The image's own value for the session when its major version is the
    # phone's (a value it does not set, or another Android, is left alone).
    key=ro.build.version.sdk_full
    g=$(sed -n "s/^$key=//p" "$ROOTFS/system/build.prop" 2>/dev/null | tail -n 1)
    h=$(getprop "$key")
    case "$g" in
        ""|*[!0-9.]*|.*|*.|*.*.*) ;;
        *)
            if [ -n "$h" ] && [ "$g" != "$h" ] && [ "${g%%.*}" = "$(getprop ro.build.version.sdk)" ]; then
                echo "$key=$h" >> "$OVR" && "$RP" -n "$key" "$g" 2>/dev/null &&
                    echo "guest_props: $key=$g for the session (One UI: $h; the guest framework has no $h APIs)"
            fi ;;
    esac
    # No isolated compilation from the guest. SystemServer starts
    # IsolatedCompilationService when ro.config.isolated_compilation_enabled is
    # true (One UI: true); it schedules compiles in the HOST's composd (One UI's
    # VM, One UI's /data/misc/apexdata) for staged APEXes the shared apexd
    # reports. Off for every guest, restored on return.
    key=ro.config.isolated_compilation_enabled
    h=$(getprop "$key")
    if [ "$h" = true ]; then
        echo "$key=$h" >> "$OVR" && "$RP" -n "$key" false 2>/dev/null &&
            echo "guest_props: $key=false for the session (the guest never drives One UI's composd)"
    fi
    ;;
remove)
    # Host values add overrode for the session (blur, sound names, audio HAL
    # extension, isolated compilation).
    if [ -f "$OVR" ]; then
        while IFS= read -r line; do
            "$RP" -n "${line%%=*}" "${line#*=}" 2>/dev/null && echo "guest_props: restored host ${line%%=*}=${line#*=}"
        done < "$OVR"
        rm -f "$OVR"
    fi
    rm -f "$STAGE/guest_props.boot"
    [ -f "$ADDED" ] || exit 0
    # Blanked, not deleted. resetprop's delete leaves a property's slot in its
    # context's area (/dev/__properties__) until the next reboot, and the next
    # add takes a new one. With the in-place return nothing reboots in between:
    # the S25 Ultra's system_prop area was full by its second session of a
    # night (485d5ffa: persist.sys.disable_rescue could not be added, the guest
    # was not started). An empty value is what Android's readers take for an
    # unset property (base::GetProperty, property_get and SystemProperties.get
    # return their default), and the next session's add writes into the same
    # slot (an empty value counts as unset there). Still deleted: persist.*
    # props the guest's property service stored in /data/property (deleted
    # there too, or One UI would load them at its next boot; -P lists the
    # store, and without it every persist.* one is deleted the old way), and
    # values of 92 bytes or more (long ro.* values, not blanked in place).
    NOWF="$STAGE/guest_props.now"
    getprop > "$NOWF"
    stored_ok=0
    "$RP" -P > "$STAGE/guest_props.stored" 2>/dev/null && stored_ok=1
    awk -v ok=$stored_ok -v sf="$STAGE/guest_props.stored" -v nf="$NOWF" '
        function key(l,  i) { i = index(l, "]: ["); return (substr(l, 1, 1) == "[" && i > 2) ? substr(l, 2, i - 2) : "" }
        BEGIN {
            while ((getline l < nf) > 0) { k = key(l); if (k == "") continue; v = substr(l, index(l, "]: [") + 4); sub(/\]$/, "", v); has[k] = 1; len[k] = length(v) }
            while ((getline l < sf) > 0) { k = key(l); if (k != "") st[k] = 1 }
        }
        !($0 in has) { next }
        /^persist\./ && (!ok || ($0 in st)) { print "P " $0; next }
        len[$0] >= 92 { print "D " $0; next }
        { print "B " $0 }' "$ADDED" > "$STAGE/guest_props.plan"
    removed=0; blanked=0
    # All blanks in one call, then each checked: whatever still has a value
    # is blanked on its own, and deleted if that does not take either.
    sed -n 's/^B \(.*\)$/\1=/p' "$STAGE/guest_props.plan" > "$STAGE/guest_props.blank"
    [ -s "$STAGE/guest_props.blank" ] && "$RP" -n -f "$STAGE/guest_props.blank" 2>/dev/null
    while read -r op key; do
        case "$op" in
            P) "$RP" -p --delete "$key" 2>/dev/null && removed=$((removed + 1)) ;;
            D) "$RP" --delete "$key" 2>/dev/null && removed=$((removed + 1)) ;;
        esac
    done < "$STAGE/guest_props.plan"
    getprop > "$NOWF"
    : > "$BLANKED.new"
    awk -v nf="$NOWF" '
        BEGIN { while ((getline l < nf) > 0) { i = index(l, "]: ["); if (substr(l, 1, 1) != "[" || i < 3) continue; v = substr(l, i + 4); sub(/\]$/, "", v); val[substr(l, 2, i - 2)] = v } }
        /^B / { k = substr($0, 3); print ((k in val) && val[k] == "" ? "E " : "S ") k }' "$STAGE/guest_props.plan" |
    while read -r st key; do
        if [ "$st" = E ] || { "$RP" -n "$key" "" 2>/dev/null && [ -z "$(getprop "$key")" ]; }; then
            echo "$key" >> "$BLANKED.new"
        else
            "$RP" --delete "$key" 2>/dev/null && echo "$key" >> "$STAGE/guest_props.deleted"
        fi
    done
    blanked=$(wc -l < "$BLANKED.new")
    [ -f "$STAGE/guest_props.deleted" ] && removed=$((removed + $(wc -l < "$STAGE/guest_props.deleted")))
    rm -f "$STAGE/guest_props.deleted"
    { [ -f "$BLANKED" ] && cat "$BLANKED"; cat "$BLANKED.new"; } | sort -u > "$BLANKED.tmp" &&
        mv -f "$BLANKED.tmp" "$BLANKED" && echo "$BOOT_ID" > "$BLANKED.boot"
    rm -f "$ADDED" "$NOWF" "$BLANKED.new" "$STAGE/guest_props.stored" "$STAGE/guest_props.plan" "$STAGE/guest_props.blank"
    echo "guest_props: blanked $blanked guest props (their slots are reused next session), deleted $removed"
    ;;
snapshot-persist)
    # persist.* values the host has right now, before the guest can change
    # them. A running guest saves its own persist.* settings through the
    # property service, which writes them to /data/property, so One UI would
    # boot with them. restore-persist undoes that.
    # A session whose cleanup never ran (the phone rebooted mid-session) left its
    # marker: delete what that guest added before trusting the current values
    # as the host's. Changed values are left alone; most are One UI's own
    # counters (radio resets, log indexes) that moved on since.
    # OneOS: only with a snapshot this stage's own session took (format 2,
    # snapshot_trusted); any other marker and snapshot are moved aside unused.
    drop_stale_memory_lists
    if [ -f "$MARK" ]; then
        if snapshot_trusted; then
            echo "guest_props: previous session was not cleaned up, removing its added persist props"
            sh "$0" restore-persist --added-only || { echo "guest_props: cleanup of the previous session failed, not taking a snapshot"; exit 1; }
        else
            echo "guest_props: persist snapshot left by another stage or an older session, not used"
            set_aside "$MARK" "$SNAP_FILE" || { echo "guest_props: could not move it aside, not taking a snapshot"; exit 1; }
        fi
    fi
    # Not the guest's blanked ones (remove): still empty, they are not One UI's.
    getprop | sed -n 's/^\[\(persist\.[^]]*\)\]: \[\(.*\)\]$/\1=\2/p' |
        awk -v bf="$BLANKED" 'BEGIN { while ((getline k < bf) > 0) b[k "="] = 1 } !($0 in b)' > "$SNAP_FILE"
    [ -s "$SNAP_FILE" ] || { echo "guest_props: ERROR: no persist props read"; rm -f "$SNAP_FILE"; exit 1; }
    sm=none; [ -f "$STAGE/.oneos_stage" ] && sm=$(sha "$STAGE/.oneos_stage")
    { echo "format=2"
      echo "boot_id=$BOOT_ID"
      echo "epoch=$(date +%s)"
      echo "app=${ONEOS_APP:-0}"
      echo "profile=${ONEOS_PROFILE:-none}"
      echo "stage_marker=$sm"
      echo "snapshot=$(sha "$SNAP_FILE")"; } > "$MARK.tmp" && mv -f "$MARK.tmp" "$MARK" ||
        { echo "guest_props: ERROR: could not write $MARK"; exit 1; }
    echo "guest_props: saved $(wc -l < "$SNAP_FILE") host persist props"
    ;;
recover)
    # The app, after a hard reset (the phone was force-restarted during a
    # session, so return_to_oneui.sh never ran): One UI booted with the persist
    # props the guest saved, its locale among them (persist.sys.locale is shared
    # and oneos_switch.sh sets the guest's). Put One UI's values back now,
    # as the return would have, instead of waiting for the next switch (which
    # only deletes the added ones). Only a snapshot an app-launched session of
    # this very stage took (app=1, the same .oneos_stage), and only once that
    # session's boot is over. Exit 0 restored or nothing to do, 3 session may
    # still run (nothing touched), 4 snapshot not trusted (moved aside).
    drop_stale_memory_lists
    [ -f "$MARK" ] || { echo "guest_props: no unfinished session, nothing to recover"; exit 0; }
    if ! snapshot_trusted || [ "$(mark_field app)" != 1 ] || [ "$(mark_field stage_marker)" = none ]; then
        echo "guest_props: the unfinished session's snapshot was not taken by this stage's app session, not used"
        set_aside "$MARK" "$SNAP_FILE"
        exit 4
    fi
    if [ -z "$BOOT_ID" ] || [ "$(mark_field boot_id)" = "$BOOT_ID" ] ||
       awk -v s="$STAGE/" 'index($5, s) == 1' /proc/self/mountinfo | grep -q .; then
        echo "guest_props: the session of $(mark_field epoch) may still be running (same boot or the stage is mounted), not touched"
        exit 3
    fi
    echo "guest_props: session of $(mark_field epoch) (profile $(mark_field profile)) never returned, restoring One UI's persist props"
    sh "$0" restore-persist --recover || exit 1
    ;;
store-on)
    # oneos_switch.sh, once One UI's system_server is gone (see STORE_MARK above).
    # Any failure leaves One UI's own store in place (the old way), never a half copy.
    # Every system (0.4.81). 0.4.73 and 0.4.74 used it for vivo OriginOS only, and
    # six OriginOS reports from four phones show it whole ("One UI's own
    # /data/property is back", "deleted 0 and blanked 456-494"). Without it a
    # ColorOS 17 session deleted its 149 runtime persist names at the return and
    # their slots stayed taken: 45, 27, then 9 KB left in system_prop, and the
    # fourth switch since a restart was refused ("One UI's property space is
    # nearly full": Galaxy A56 e0f70626, S24 Ultra 425a0ee1).
    # ONEOS_PROPS_SESSION_STORE=0 keeps One UI's store in use (the old way).
    [ "${ONEOS_PROPS_SESSION_STORE:-1}" = 1 ] || { echo "guest_props: session property store off (ONEOS_PROPS_SESSION_STORE=$ONEOS_PROPS_SESSION_STORE)"; exit 0; }
    snapshot_trusted || { echo "guest_props: no persist snapshot of this session, session property store not used"; exit 0; }
    [ -d "$PD" ] && [ ! -L "$PD" ] || { echo "guest_props: $PD is not a plain folder, session property store not used"; exit 0; }
    pd_mounted && { echo "guest_props: $PD is already a mount point, session property store not used"; exit 0; }
    rm -f "$STORE_MARK"
    T="$STAGE/property_session.copy"
    rm -rf "$T" && mkdir -m 700 "$T" || { echo "guest_props: could not make $T, session property store not used"; exit 0; }
    for f in "$PD"/* "$PD"/.[!.]*; do
        [ -e "$f" ] || continue
        cp -pR "$f" "$T"/ || { rm -rf "$T"; echo "guest_props: could not copy $PD, session property store not used"; exit 0; }
    done
    if ! mount -t tmpfs -o mode=0700,uid=0,gid=0,size=8m,context=u:object_r:property_data_file:s0 oneos_props "$PD" 2>/dev/null &&
       ! { mount -t tmpfs -o mode=0700,uid=0,gid=0,size=8m oneos_props "$PD" 2>/dev/null && chcon u:object_r:property_data_file:s0 "$PD"; }; then
        store_off; rm -rf "$T"; echo "guest_props: could not mount a copy over $PD, session property store not used"; exit 0
    fi
    ok=1
    for f in "$T"/* "$T"/.[!.]*; do
        [ -e "$f" ] || continue
        cp -pR "$f" "$PD"/ && cmp -s "$f" "$PD/${f##*/}" || ok=0
    done
    [ "$(stat -c %d "$PD")" != "$(stat -c %d /data)" ] || ok=0
    case "$(ls -Zd "$PD" 2>/dev/null)" in *property_data_file*) ;; *) chcon -R u:object_r:property_data_file:s0 "$PD" 2>/dev/null || ok=0 ;; esac
    if [ "$ok" = 1 ] && echo "$BOOT_ID" > "$STORE_MARK"; then
        echo "guest_props: $PD is the session's own copy ($(ls "$PD" | wc -l) files); One UI's store stays as it is"
    else
        rm -f "$STORE_MARK"
        store_off || echo "guest_props: ERROR: could not unmount the half-made copy over $PD"
        echo "guest_props: the copy over $PD did not check out, session property store not used"
    fi
    rm -rf "$T"
    ;;
restore-persist)
    SNAP="$SNAP_FILE"
    # One UI's own store back first (store-on): the guest's persist settings were
    # never written to it. Fail closed: the callers fail safe (reboot), which
    # drops the copy too.
    STORE_SESSION=0
    if [ -f "$STORE_MARK" ] && [ "$(cat "$STORE_MARK" 2>/dev/null)" = "$BOOT_ID" ]; then
        store_off || { echo "guest_props: ERROR: could not unmount the session copy over $PD"; exit 1; }
        # Only this run blanks instead of deleting; a retry after a failure deletes the old way.
        rm -f "$STORE_MARK"
        STORE_SESSION=1
        echo "guest_props: One UI's own $PD is back (the session's copy dropped)"
    fi
    [ -f "$SNAP" ] || { echo "guest_props: no persist snapshot, skipping"; exit 0; }
    snapshot_trusted || { echo "guest_props: persist snapshot not taken by this stage's session (no format 2 marker or hash mismatch), not used"; exit 0; }
    # Keep the guest's language for its next session (oneos_switch.sh
    # sets it again); One UI's own value is restored below.
    gl=$(getprop persist.sys.locale)
    if [ -n "$gl" ] && ! grep -qxF "persist.sys.locale=$gl" "$SNAP"; then
        echo "$gl" > "$STAGE/guest_locale"
        echo "guest_props: kept the guest's locale $gl for its next session"
    fi
    NOW="$STAGE/persist_props.now"
    getprop | sed -n 's/^\[\(persist\.[^]]*\)\]: \[\(.*\)\]$/\1=\2/p' > "$NOW"
    deleted=0; restored=0; failed=0
    # After a hard reset (recover) One UI's init has since recorded that boot
    # in persist.sys.boot.reason*: its own record, kept as it is.
    keep="^$"; [ "$2" = "--recover" ] && keep="^persist\.sys\.boot\.reason"
    # --recover may run long after the hard reset: One UI could have added or
    # changed its own persist props since (a new SIM's persist.radio.*, a
    # timezone or locale change the user made). The snapshot cannot tell those
    # from the guest's, so on --recover touch only props that are clearly the
    # guest's; the normal return (no flag, same boot) still restores everything.
    guest_prop() { # 0 when $1 is clearly a guest-owned persist prop
        case "$1" in
            persist.sys.locale) return 0 ;;
            persist.oplus.*|persist.sys.oplus.*) return 0 ;;
            # vivo OriginOS: its audio policy alone sets about 370 of these (seventh run).
            persist.vivo.*|persist.sys.vivo.*|persist.vendor.vivo.*|persist.sys.audio.vapc.*) return 0 ;;
            # oneos_switch.sh's softdog off switch on the Exynos phones (0.4.22).
            persist.vendor.softdog) return 0 ;;
        esac
        return 1
    }
    # Added by the guest: delete from memory and from persistent storage.
    # Not the ones remove blanked (still empty and not in the store).
    # With the session's own store (store-on) they were never in One UI's: blanked
    # in memory instead, so the next session writes into the same slots (listed
    # in guest_props.blanked, which the next snapshot leaves out).
    : > "$BLANKED.persist"
    for key in $(cut -d= -f1 "$NOW"); do
        grep -q "^$key=" "$SNAP" && continue
        grep -qxF "$key=" "$NOW" && [ -f "$BLANKED" ] && grep -qxF "$key" "$BLANKED" && continue
        echo "$key" | grep -q "$keep" && continue
        [ "$2" = "--recover" ] && ! guest_prop "$key" && continue
        if [ "$STORE_SESSION" = 1 ]; then
            if "$RP" -n "$key" "" 2>/dev/null; then echo "$key" >> "$BLANKED.persist"; blanked_p=$((${blanked_p:-0} + 1)); else failed=$((failed + 1)); fi
        elif "$RP" -p --delete "$key" 2>/dev/null; then deleted=$((deleted + 1)); else failed=$((failed + 1)); fi
    done
    if [ -s "$BLANKED.persist" ]; then
        { [ -f "$BLANKED" ] && cat "$BLANKED"; cat "$BLANKED.persist"; } | sort -u > "$BLANKED.tmp" &&
            mv -f "$BLANKED.tmp" "$BLANKED" && echo "$BOOT_ID" > "$BLANKED.boot"
    fi
    rm -f "$BLANKED.persist"
    # Changed by the guest: put the host's value back, in storage too.
    [ "$2" = "--added-only" ] && : > "$NOW.skip"
    while [ ! -f "$NOW.skip" ] && IFS= read -r line; do
        key=${line%%=*}
        grep -qxF "$line" "$NOW" && continue
        echo "$key" | grep -q "$keep" && continue
        [ "$2" = "--recover" ] && ! guest_prop "$key" && continue
        if "$RP" -p "$key" "${line#*=}" 2>/dev/null; then restored=$((restored + 1)); else failed=$((failed + 1)); fi
    done < "$SNAP"
    rm -f "$NOW" "$NOW.skip"
    # Fail closed: if any resetprop write failed, keep persist_session.active so
    # the app can show the failure and recover can retry, and exit non-zero.
    # Deleting the marker on a silent failure (the old behaviour) left One UI on
    # the guest's persist props with nothing able to see it any more.
    if [ "$failed" -gt 0 ]; then
        echo "guest_props: ERROR: $failed persist prop writes failed (deleted $deleted, restored $restored); keeping persist_session.active to retry"
        exit 1
    fi
    rm -f "$STAGE/persist_session.active"
    echo "guest_props: persist props: deleted $deleted and blanked ${blanked_p:-0} added by the guest, restored $restored changed ones"
    ;;
*)
    echo "usage: $0 add <rootfs> | remove | snapshot-persist | store-on | restore-persist | recover" >&2
    exit 2
    ;;
esac
