#!/system/bin/sh
# Pinned Pixel 11 Fold guest payloads on the Z Fold8 (pixel-f8) and Z Fold8 Ultra
# (pixel-f8u), which have the same Samsung folding-angle sensor. No host APK writes.
set -eu
STAGE=${STAGE:-/data/local/tmp/oneos}
BB=${BB:-/data/oneos_bin/busybox}
fail() { echo "Fold8 Pixel: $*" >&2; exit 3; }
selected() {
    grep -q '^  "image": "pixel11fold-yogi",$' "$STAGE/.oneos_stage" || return 1
    case "${ONEOS_PROFILE:-}" in
        f8) grep -q '^  "set": "pixel-f8",$' "$STAGE/.oneos_stage" ;;
        f8u) grep -q '^  "set": "pixel-f8u",$' "$STAGE/.oneos_stage" ;;
        *) return 1 ;;
    esac
}
# Bar Pixel images (0.4.59): double tap to sleep from the image's own SystemUIGoogle and
# Pixel Launcher (switcher/patches/pixel-bar/build-systemui-bar.py, pixel-launcher/
# build-launcher.py), each bound only over the exact donor it was built from (its platform
# certificate must be the image's). Anything else leaves the image's files (no double tap
# to sleep, nothing else changes). ONEOS_GUEST_DT2S=0 leaves them out.
bar_bind() { # <staged apk> <image path> <donor sha256> <what>
    [ -f "$STAGE/$1" ] || return 0
    "$BB" umount -l "$2" 2>/dev/null || true
    if [ -f "$2" ] && [ ! -L "$2" ] && [ "$(sha256sum "$2" | cut -d' ' -f1)" = "$3" ]; then
        "$BB" mount --bind "$STAGE/$1" "$2"
        "$BB" mount --make-private "$2"
        "$BB" mount -o remount,bind,ro "$STAGE/$1" "$2"
        echo "Pixel: $4 with double tap to sleep bound"
    else
        echo "Pixel: the image's $4 is not the donor: left as it is (no double tap to sleep there)"
    fi
}
bar_prepare() {
    [ "${ONEOS_GUEST_DT2S:-1}" = 1 ] || { echo 'Pixel: double tap to sleep off (ONEOS_GUEST_DT2S=0)'; return 0; }
    SUI="$STAGE/rootfs/system/system_ext/priv-app/SystemUIGoogle/SystemUIGoogle.apk"
    LCH="$STAGE/rootfs/system/system_ext/priv-app/NexusLauncherRelease/NexusLauncherRelease.apk"
    if grep -q '^  "image": "pixel11pro-kodiak",$' "$STAGE/.oneos_stage" && grep -q '^  "set": "pixel-sultra",$' "$STAGE/.oneos_stage"; then
        bar_bind OneOSPixelSystemUI.apk "$SUI" db35d92ce22e7afcafde19877c4d5f60ec94cf7389bcb140b22902a4ca3e53ec SystemUI
        bar_bind OneOSPixelLauncher.apk "$LCH" 3c0ea0aca798fa54395e619b26527da08037fe4bda145d2f4ab62db55547a62f 'Pixel Launcher'
    elif grep -q '^  "image": "pixel9proxl-komodo",$' "$STAGE/.oneos_stage" && grep -q '^  "set": "pixel9-sultra",$' "$STAGE/.oneos_stage"; then
        bar_bind OneOSPixelSystemUI.apk "$SUI" e2072d91e7fe553256de6b6bfdbce00691e67a0b99fb90db3afb3dff9285c91b SystemUI
        bar_bind OneOSPixelLauncher.apk "$LCH" 28866dd3953784fe154ffcc5c44d76461b12a304e20b9806a1a91338310b4bb0 'Pixel Launcher'
    fi
}
case "$1" in
prepare)
    bar_prepare
    selected || exit 0
    target="$STAGE/rootfs/system/system_ext/priv-app/SystemUIGoogle/SystemUIGoogle.apk"
    "$BB" umount -l "$target" 2>/dev/null || true
    [ -f "$target" ] && [ ! -L "$target" ] || fail 'unexpected SystemUI path'
    [ "$(sha256sum "$target" | cut -d' ' -f1)" = 9934d2dac326f56290f459b9e649185cd5531e1b6ae1f5a72b11e88f865f8b03 ] || fail 'SystemUI donor differs'
    "$BB" mount --bind "$STAGE/Fold8PixelSystemUI.apk" "$target"
    "$BB" mount --make-private "$target"
    "$BB" mount -o remount,bind,ro "$STAGE/Fold8PixelSystemUI.apk" "$target"
    # Pixel Launcher with double tap to sleep on the home screen (0.4.59,
    # switcher/patches/pixel-launcher): bound over the image's own when that is
    # the exact donor; otherwise the image's stays (no double tap to sleep on
    # the home screen, nothing else changes).
    lt="$STAGE/rootfs/system/system_ext/priv-app/NexusLauncherRelease/NexusLauncherRelease.apk"
    if [ -f "$STAGE/OneOSPixelLauncher.apk" ]; then
        "$BB" umount -l "$lt" 2>/dev/null || true
        if [ -f "$lt" ] && [ ! -L "$lt" ] &&
           [ "$(sha256sum "$lt" | cut -d' ' -f1)" = 0c8c50434e0cf6f445be6bf6173702dcdbdd7a49baca274f15fcd86afa58500e ]; then
            "$BB" mount --bind "$STAGE/OneOSPixelLauncher.apk" "$lt"
            "$BB" mount --make-private "$lt"
            "$BB" mount -o remount,bind,ro "$STAGE/OneOSPixelLauncher.apk" "$lt"
            echo 'Fold8 Pixel: Pixel Launcher with double tap to sleep bound'
        else
            echo 'Fold8 Pixel: the image launcher is not the donor: left as it is (no double tap to sleep on the home screen)'
        fi
    fi
    dest="$STAGE/data/oneos_pixel_hinge"
    [ ! -L "$STAGE/data" ] && [ ! -L "$dest" ] || fail 'symlink in guest payload path'
    [ ! -d "$dest" ] || [ -z "$(find "$dest" -type l -print -quit)" ] || fail 'symlink below guest payload path'
    mkdir -p "$dest"
    cp -f "$STAGE/Fold8AngleRelay.dex" "$dest/Fold8AngleRelay.dex"
    cp -f "$STAGE/fold8_pixel.sh" "$dest/runtime.sh"
    chown -R 0:0 "$dest"
    chmod 755 "$dest"; chmod 644 "$dest/Fold8AngleRelay.dex" "$dest/runtime.sh"
    chcon -R u:object_r:system_data_file:s0 "$dest"
    ;;
runtime)
    # Invoked only inside this guest, with its classpath and binder namespace.
    [ "$(pm path com.android.systemui)" = package:/system/system_ext/priv-app/SystemUIGoogle/SystemUIGoogle.apk ] || fail 'not the Pixel guest'
    D=/data/oneos_pixel_hinge
    [ -f "$D/Fold8AngleRelay.dex" ] || fail 'relay absent'
    ui=$(pidof com.android.systemui | cut -d' ' -f1)
    z=$(pidof zygote64 | cut -d' ' -f1)
    [ -n "$ui" ] && [ -n "$z" ] || fail 'guest UI not ready'
    uid=$(stat -c %u /proc/$ui)
    [ ! -L /data/oneos_hinge ] || fail 'hinge folder is a symlink'
    mkdir -p /data/oneos_hinge
    chown 1000:"$uid" /data/oneos_hinge; chmod 2750 /data/oneos_hinge
    chcon u:object_r:system_data_file:s0 /data/oneos_hinge
    if ! ps -A -o ARGS | grep -q "[a]pp_process /system/bin OneOSAngleRelay /data/oneos_hinge/angle.bin $z"; then
        (umask 027; CLASSPATH="$D/Fold8AngleRelay.dex" "$BB" nohup "$BB" setuidgid system /system/bin/app_process /system/bin OneOSAngleRelay /data/oneos_hinge/angle.bin "$z" >"$D/relay.log" 2>&1 </dev/null &)
    fi
    echo 'Pixel continuous-angle relay started; native public sensor remains fallback'
    ;;
*) fail 'expected prepare or runtime' ;;
esac
