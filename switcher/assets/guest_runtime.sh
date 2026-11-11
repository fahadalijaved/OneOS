#!/system/bin/sh
# OneOS full-stack experiment. Host setup and guest lifecycle share this file.
# There are no calls to a host root manager or global injector monitor.
set -eu
S=${STAGE:-/data/local/tmp/oneos}
R=$S/rootfs
STATE=$S/data/oneos_root
verify_private_adb_bind() {
    for suffix in '' /modules; do
        expected=$("$B" stat -L -c %d:%i "$A$suffix") || return 1
        actual=$("$B" stat -L -c %d:%i "$R/data/adb$suffix") || return 1
        [ "$expected" = "$actual" ] || return 1
    done
}

case "${1:-}" in
control)
    A=/data/adb
    id=${3:-}
    valid_id() { case "$1" in ''|*[!A-Za-z0-9._-]*|.*) return 1 ;; esac; }
    safe_dirs() {
        for d in "$A" "$A/oneos" "$A/modules" "$A/modules_update"; do
            [ -d "$d" ] && [ ! -L "$d" ] || exit 1
        done
    }
    safe_dirs
    case "${2:-}" in
    status|list)
        echo '@@RESULT root active'
        selected=$(cat "$A/oneos/framework")
        valid_id "$selected" || exit 1
        provider="$A/modules/$selected"
        kind=none
        [ ! -f "$provider/.oneos-framework" ] || kind=$(cat "$provider/.oneos-framework")
        active=0; zp=$(cat "$A/oneos/run/injection.pid" 2>/dev/null || true)
        case "$zp" in ''|*[!0-9]*) zp=0 ;; esac
        if [ "$zp" -gt 1 ] && kill -0 "$zp" 2>/dev/null &&
           [ "$(stat -Lc %d:%i /proc/$zp/root)" = "$(stat -Lc %d:%i /)" ]; then
            case "$kind" in vector) candidates=$(pidof vectord || true) ;; lsposed) candidates=$(pidof lspd || true) ;; *) candidates= ;; esac
            for pid in $candidates; do
                [ "$(stat -Lc %d:%i /proc/$pid/root 2>/dev/null)" != "$(stat -Lc %d:%i /)" ] || active=1
            done
        fi
        echo "@@RESULT framework-status $selected $kind $active"
        for base in modules modules_update; do
            for m in "$A/$base/"*; do
                [ -d "$m" ] && [ ! -L "$m" ] || continue
                enabled=1; [ ! -f "$m/disable" ] || enabled=0
                kind=module; [ ! -f "$m/.oneos-framework" ] || kind=$(cat "$m/.oneos-framework")
                namehex=$(sed -n 's/^name=//p' "$m/module.prop" | head -n 1 | head -c 256 | tr -d '\r\n' | od -An -v -tx1 | tr -d ' \n')
                deschex=$(sed -n 's/^description=//p' "$m/module.prop" | head -n 1 | head -c 1024 | tr -d '\r\n' | od -An -v -tx1 | tr -d ' \n')
                verhex=$(sed -n 's/^version=//p' "$m/module.prop" | head -n 1 | head -c 128 | tr -d '\r\n' | od -An -v -tx1 | tr -d ' \n')
                authorhex=$(sed -n 's/^author=//p' "$m/module.prop" | head -n 1 | head -c 256 | tr -d '\r\n' | od -An -v -tx1 | tr -d ' \n')
                codehex=$(sed -n 's/^versionCode=//p' "$m/module.prop" | head -n 1 | head -c 32 | tr -d '\r\n' | od -An -v -tx1 | tr -d ' \n')
                updatehex=$(sed -n 's/^updateJson=//p' "$m/module.prop" | head -n 1 | head -c 1024 | tr -d '\r\n' | od -An -v -tx1 | tr -d ' \n')
                caps=-
                [ ! -f "$m/action.sh" ] || caps=action
                [ ! -f "$m/webroot/index.html" ] || caps="$caps,webui"
                removed=0; [ ! -f "$m/remove" ] || removed=1
                echo "@@RESULT module-info ${m##*/} $enabled $base $kind ${verhex:--} ${namehex:--} ${deschex:--} ${authorhex:--} ${codehex:--} ${updatehex:--} $caps $removed"
            done
        done
        ;;
    asset)
        valid_id "$id" || exit 1
        rel=${4:-}
        case "$rel" in ''|/*|*..*|*\\*) exit 1 ;; esac
        root="$A/modules/$id/webroot"
        [ -d "$root" ] && [ ! -L "$root" ] || exit 1
        root=$(realpath "$root") || exit 1
        file=$(realpath "$root/$rel") || exit 1
        case "$file" in "$root"/*) ;; *) exit 1 ;; esac
        [ -f "$file" ] && [ "$(stat -c %s "$file")" -le 16777216 ] || exit 1
        exec cat "$file"
        ;;
    restart)
        # Only the host watcher restarts namespaces; never ask shared init to reboot.
        setprop oneos.guest.powerctl ksud:soft-reboot
        ;;
    remove|restore)
        valid_id "$id" || exit 1
        [ "$id" != "$(cat "$A/oneos/framework")" ] || { echo 'Select another framework before removing this one' >&2; exit 1; }
        found=0
        for m in "$A/modules/$id" "$A/modules_update/$id"; do
            [ -d "$m" ] && [ ! -L "$m" ] || continue
            [ ! -L "$m/remove" ] || exit 1
            if [ "$2" = remove ]; then : > "$m/remove"; else rm -f "$m/remove"; fi
            found=1
        done
        [ "$found" = 1 ] || exit 1
        ;;
    action)
        valid_id "$id" || exit 1
        m="$A/modules/$id"
        [ -d "$m" ] && [ ! -L "$m" ] && [ ! -f "$m/remove" ] && [ -f "$m/action.sh" ] && [ ! -L "$m/action.sh" ] || exit 1
        cd "$m"
        export MODPATH="$m" ASH_STANDALONE=1 PATH=/system/bin:/system/xbin:/data/adb/ksu/bin
        exec /data/oneos_bin/busybox timeout 120 /data/oneos_bin/busybox sh "$m/action.sh"
        ;;
    toggle)
        valid_id "$id" || exit 1
        case "${4:-}" in on|off) ;; *) exit 1 ;; esac
        found=0
        for m in "$A/modules/$id" "$A/modules_update/$id"; do
            [ -d "$m" ] && [ ! -L "$m" ] || continue
            [ ! -L "$m/disable" ] || exit 1
            if [ -f "$m/.oneos-framework" ] && [ "$4" = on ]; then
                [ "$id" = "$(cat "$A/oneos/framework")" ] || { echo 'Select this framework on the pre-boot page first' >&2; exit 1; }
            fi
            if [ "$4" = on ]; then rm -f "$m/disable"; else : > "$m/disable"; fi
            found=1
        done
        [ "$found" = 1 ] || exit 1
        ;;
    import)
        valid_id "$id" || exit 1
        case "$id" in oneos|zygisksu) exit 1 ;; esac
        file=${4:-}
        case "$file" in /data/user/0/com.fahadali.oneos.guest/cache/guest-module-*.bundle) ;; *) exit 1 ;; esac
        [ -f "$file" ] && [ ! -L "$file" ] || exit 1
        target="$A/modules_update/$id"
        [ ! -e "$target" ] && [ ! -L "$target" ] || { echo 'An update for this module is already staged' >&2; exit 1; }
        temp="$A/modules_update/.oneos-import-$$"
        mkdir "$temp"
        trap 'rm -rf "$temp"' EXIT
        "$A/oneos/bin/su" --unpack "$temp" < "$file" || exit 1
        [ "$(sed -n 's/^id=//p' "$temp/module.prop" | tr -d '\r')" = "$id" ] || exit 1
        mv "$temp" "$target"
        trap - EXIT
        ;;
    *) exit 2 ;;
    esac
    ;;
baseline)
    [ -f "$STATE/enabled" ] || exit 0
    B=$S/tmp/guest_runtime_baseline
    mkdir -p "$B"
    rm -f "$B/ready"
    # Keep the host's persisted list intact even if an older kernel prunes its
    # live table after seeing a guest package event. Keep this read-only bind
    # until reboot on an audit failure; remove it only after a matching audit.
    if [ -f /data/adb/ksu/.allowlist ] && [ ! -L /data/adb/ksu/.allowlist ]; then
        cp /data/adb/ksu/.allowlist "$B/allowlist.saved"
        busy=''
        for x in /data/adb/ksu/bin/busybox /data/adb/ap/bin/busybox /data/adb/magisk/busybox; do [ ! -x "$x" ] || { busy=$x; break; }; done
        [ -n "$busy" ] || exit 1
        "$busy" mount --bind "$B/allowlist.saved" /data/adb/ksu/.allowlist
        # BusyBox requires both operands for a file bind remount; the host
        # namespace's /proc/mounts need not list the bind we just created.
        if ! "$busy" mount -o remount,bind,ro "$B/allowlist.saved" /data/adb/ksu/.allowlist; then
            "$busy" umount /data/adb/ksu/.allowlist
            exit 1
        fi
        : > "$B/allowlist.protected"
    fi
    : > "$B/host-frameworks"
    for proc in /proc/[0-9]*; do
        name=$(tr '\000' ' ' < "$proc/cmdline" 2>/dev/null || true)
        case "$name" in vectord|vectord' '*|lspd|lspd' '*|org.lsposed.lspd|org.lsposed.lspd' '*|org.matrix.vector.daemon|org.matrix.vector.daemon' '*)
            pid=${proc##*/}
            start=$(awk '{print $22}' "$proc/stat")
            kill -STOP "$pid" || exit 1
            echo "$pid $start" >> "$B/host-frameworks"
            ;;
        esac
    done
    "$S/guest_root" --host-audit > "$B/root.unsorted" || exit 0
    sort "$B/root.unsorted" > "$B/root"
    sha256sum /sys/fs/selinux/policy > "$B/selinux" || exit 0
    awk '{print $1, $2, $6}' /proc/modules | sort > "$B/kernel-modules"
    if [ -f /data/adb/ksu/.allowlist ]; then sha256sum /data/adb/ksu/.allowlist > "$B/allowlist"; fi
    cat /proc/sys/kernel/random/boot_id > "$B/boot"
    : > "$B/ready"
    ;;
verify-return)
    [ -f "$STATE/enabled" ] || exit 0
    B=$S/tmp/guest_runtime_baseline
    [ -f "$B/ready" ] || { echo 'Guest runtime: no supported live root audit; reboot fallback required'; exit 1; }
    [ "$(cat "$B/boot")" = "$(cat /proc/sys/kernel/random/boot_id)" ] || exit 1
    "$S/guest_root" --host-audit > "$B/return.unsorted" || exit 1
    sort "$B/return.unsorted" > "$B/return.root"
    cmp -s "$B/root" "$B/return.root" || { echo 'Guest runtime: host root grants or manager changed'; exit 1; }
    sha256sum -c "$B/selinux" || { echo 'Guest runtime: shared SELinux policy changed'; exit 1; }
    [ ! -f "$B/allowlist" ] || sha256sum -c "$B/allowlist" || exit 1
    awk '{print $1, $2, $6}' /proc/modules | sort > "$B/return.kernel-modules"
    cmp -s "$B/kernel-modules" "$B/return.kernel-modules" || { echo 'Guest runtime: loaded kernel modules changed'; exit 1; }
    if [ -f "$B/host-frameworks" ]; then
        while read -r pid start; do
            [ -r "/proc/$pid/stat" ] || continue
            [ "$(awk '{print $22}' "/proc/$pid/stat")" = "$start" ] || { echo 'Host framework process identity changed'; exit 1; }
            kill -CONT "$pid" || exit 1
        done < "$B/host-frameworks"
    fi
    if [ -f "$B/allowlist.protected" ]; then
        umount /data/adb/ksu/.allowlist || exit 1
        rm -f "$B/allowlist.protected"
    fi
    echo 'Guest runtime: live host grants, manager, SELinux policy and kernel modules match baseline'
    ;;
prepare)
    [ -f "$STATE/enabled" ] || exit 0
    [ "$(getprop ro.product.cpu.abi)" = arm64-v8a ] || { echo 'Guest runtime: no native backend for this ABI'; exit 1; }
    B=''
    for b in /data/adb/ksu/bin/busybox /data/adb/ap/bin/busybox /data/adb/magisk/busybox; do [ ! -x "$b" ] || { B=$b; break; }; done
    [ -n "$B" ] || exit 1
    # Existing prepare validates all staged data ancestors against symlinks.
    for p in "$STATE" "$STATE/adb" "$STATE/adb/oneos" "$STATE/adb/modules" "$STATE/adb/modules_update"; do
        [ ! -L "$p" ] || { echo "Guest runtime: symlink $p"; exit 1; }
        mkdir -p "$p"
    done
    A=$STATE/adb
    mkdir -p "$A/oneos/bin" "$A/oneos/run/zygisk/lib64" "$A/ksu/bin" "$A/service.d" "$A/post-fs-data.d"
    cp "$S/guest_root" "$A/oneos/bin/su"
    cp "$S/guest_zygiskd" "$A/oneos/bin/zygiskd"
    cp "$S/guest_zygisk_ptrace" "$A/oneos/bin/zygisk-ptrace64"
    cp "$S/guest_zygisk.so" "$A/oneos/run/zygisk/lib64/libzygisk.so"
    cp "$B" "$A/ksu/bin/busybox"
    for rp in /data/adb/ksu/bin/resetprop /data/adb/ap/bin/resetprop /debug_ramdisk/resetprop /sbin/resetprop; do
        if [ -x "$rp" ]; then cp "$rp" "$A/ksu/bin/resetprop"; chmod 755 "$A/ksu/bin/resetprop"; break; fi
    done
    chmod 755 "$A/oneos/bin/"* "$A/ksu/bin/busybox"
    chmod 711 "$A" "$A/oneos"
    chmod 755 "$A/oneos/run" "$A/oneos/run/zygisk"
    : > "$A/oneos/run/session.log"
    rm -f "$A/oneos/run/injection.pid" "$A/oneos/run/su.sock" "$A/oneos/run/zygisk/cp64.sock" "$A/oneos/run/module-props"
    if [ ! -d "$A/modules/zygisk_vector" ] && [ ! -d "$A/modules_update/zygisk_vector" ]; then
        mkdir "$A/modules_update/zygisk_vector"
        "$S/guest_root" --unpack "$A/modules_update/zygisk_vector" < "$S/guest_vector.bundle" || exit 1
    fi
    selected=zygisk_vector
    [ ! -f "$STATE/framework" ] || selected=$(cat "$STATE/framework")
    case "$selected" in ''|*[!A-Za-z0-9._-]*|.*) exit 1 ;; esac
    for base in modules modules_update; do
        for provider in "$A/$base/"*; do
            [ -f "$provider/.oneos-framework" ] || continue
            # Preserve the selected provider's explicit switch; alternatives stay disabled.
            [ "${provider##*/}" = "$selected" ] || touch "$provider/disable"
        done
    done
    mkdir -p "$A/oneos/framework-state/$selected/lspd" "$A/lspd"
    printf '%s\n' "$selected" > "$A/oneos/framework"
    cp "$S/guest_runtime.sh" "$S/data/oneos_runtime.sh"
    # Bind the complete private root state, including framework and service.d.
    "$B" mount --make-private "$R/data/adb"
    "$B" mount --bind "$A" "$R/data/adb"
    "$B" mount --make-rprivate "$R/data/adb"
    "$B" mount --bind "$A/oneos/framework-state/$selected/lspd" "$R/data/adb/lspd"
    "$B" mount --make-private "$R/data/adb/lspd"
    # /system/xbin/su is the copied passthrough binary; replace only the guest target.
    [ -f "$R/system/xbin/su" ] || { echo 'Guest runtime: guest su target missing'; exit 1; }
    "$B" mount --bind "$S/guest_root" "$R/system/xbin/su"
    "$B" mount --make-private "$R/system/xbin/su"
    # Modules can expect either spelling. Never expose the host provider's su.
    if [ -f "$R/system/bin/su" ]; then
        "$B" mount --bind "$S/guest_root" "$R/system/bin/su"
        "$B" mount --make-private "$R/system/bin/su"
    fi
    # Literal /data/adb paths used by zygiskd and module scripts must resolve
    # to this guest's private tree, including any nested modules mount.
    verify_private_adb_bind || { echo 'Guest runtime: private adb bind identity mismatch' >&2; exit 1; }
    echo 'Guest runtime: separate permissions, module state and explicit guest injection enabled'
    ;;
restore-props)
    A=/data/adb
    snapshot="$A/oneos/run/module-props"
    if [ -f "$snapshot" ]; then
        [ -x "$A/ksu/bin/resetprop" ] || exit 1
        while IFS='|' read -r key present value; do
            case "$key" in ''|*[!A-Za-z0-9._-]*) exit 1 ;; esac
            if [ "$present" = 1 ]; then "$A/ksu/bin/resetprop" -n "$key" "$value"
            else "$A/ksu/bin/resetprop" --delete "$key"; fi
        done < "$snapshot"
        rm -f "$snapshot"
    fi
    ;;
uninstall)
    A=/data/adb
    # Installation/cleanup may invoke su before the normal guest daemon starts.
    "$A/oneos/bin/su" --daemon >> "$A/oneos/run/session.log" 2>&1 &
    bootstrap=$!
    trap 'kill "$bootstrap" 2>/dev/null || true; wait "$bootstrap" 2>/dev/null || true' EXIT
    export ASH_STANDALONE=1 PATH=/system/bin:/system/xbin:/data/adb/ksu/bin
    for m in "$A/modules/"*; do
        [ -d "$m" ] && [ ! -L "$m" ] && [ -f "$m/remove" ] || continue
        id=${m##*/}
        # A framework's uninstall.sh (Vector's and LSPosed's: "rm -rf /data/adb/lspd") is not
        # run: /data/adb/lspd is the selected framework's state bound there by prepare, so it
        # emptied that one and then failed on the mount point, and with "|| exit 1" every
        # switch ended at prepare while the remove mark stayed (A36 0.4.73 d2de5297, HyperOS:
        # code 3 right after "explicit guest injection enabled" at 15:53, 16:11 and 16:57,
        # booted only with guest root off; "I can't remove any module (lsposed/hma oss/vector)").
        # Its own state is framework-state/<id>, never bound while another one is selected.
        if [ -f "$m/.oneos-framework" ]; then
            if [ "$id" != "$(cat "$A/oneos/framework" 2>/dev/null)" ] && [ ! -L "$A/oneos/framework-state/$id" ]; then
                rm -rf "$A/oneos/framework-state/$id"
                echo "Guest runtime: $id's framework state removed with it (its uninstall.sh not run)"
            fi
            continue
        fi
        # As KernelSU and Magisk: a failing uninstall.sh is logged and the module still goes.
        if [ -f "$m/uninstall.sh" ] && [ ! -L "$m/uninstall.sh" ]; then
            ( cd "$m"; export MODPATH="$m"; timeout 30 /data/oneos_bin/busybox sh "$m/uninstall.sh" ) >> "$A/oneos/run/session.log" 2>&1 ||
                echo "Guest runtime: $id's uninstall.sh failed (exit $?); removed anyway"
        fi
    done
    ;;
install)
    A=/data/adb
    /data/adb/oneos/bin/su --daemon >> "$A/oneos/run/session.log" 2>&1 &
    bootstrap=$!
    trap 'kill "$bootstrap" 2>/dev/null || true; wait "$bootstrap" 2>/dev/null || true' EXIT
    A=/data/adb
    export PATH=/system/bin:/system/xbin:/data/adb/ksu/bin
    export ASH_STANDALONE=1
    B=/data/oneos_bin/busybox
    for m in "$A/modules"/*; do
        [ -d "$m" ] && [ ! -f "$m/disable" ] && [ ! -f "$m/remove" ] || continue
        # Installation occurs inside the guest, never as a host-side installer.
        # ZYGISK_ENABLED=1 as Magisk sets it for installers: this runtime's Zygisk always runs
        # with it (HMA-OSS and other Zygisk modules refuse to install without a Zygisk framework).
        if [ -f "$m/.oneos-pending" ]; then
            MODPATH=$m ZIPFILE=$m/.oneos-install.zip BOOTMODE=true KSU=true KSU_VER_CODE=99999 MAGISK_VER_CODE=0 ZYGISK_ENABLED=1 ARCH=arm64 IS64BIT=true API=$(getprop ro.build.version.sdk) \
                "$B" sh /data/oneos_runtime.sh customize "$m" >> "$A/oneos/run/session.log" 2>&1 || {
                    # As a module that asks for shared SELinux changes (pre, below): disabled with
                    # the reason for the modules screen, and the system starts without it. It used
                    # to end the whole switch (S26 Ultra 00655d58, 0.4.74: one module's installer
                    # failed, "Guest module installation failed (exit 1); returning to One UI").
                    # .oneos-pending stays, so turning the module on again runs its installer again.
                    rc=$?
                    touch "$m/disable"
                    echo "Its installer failed (exit $rc); turn it on again to retry, or remove it" > "$m/.oneos-disabled-reason"
                    echo "Guest runtime: installation failed for ${m##*/} (exit $rc); disabled, the system starts without it"
                    continue
                }
            rm -f "$m/.oneos-pending"
            # The host helper reapplies generated mount payloads before zygote.
        fi
    done
    ;;
pre)
    A=/data/adb
    rm -f "$A/oneos/run/injection.pid" "$A/oneos/run/zygisk/cp64.sock"
    "$A/oneos/bin/su" --daemon >> "$A/oneos/run/session.log" 2>&1 &
    n=0
    while [ ! -S "$A/oneos/run/su.sock" ]; do n=$((n+1)); [ "$n" -lt 50 ] || exit 1; sleep 0.1; done
    export PATH=/system/bin:/system/xbin:/data/adb/ksu/bin
    export ASH_STANDALONE=1
    B=/data/oneos_bin/busybox
    for m in "$A/modules"/*; do
        [ -d "$m" ] && [ ! -f "$m/disable" ] && [ ! -f "$m/remove" ] || continue
        # Shared kernel policy/boot changes cannot be advertised as guest-local: such a module is
        # disabled (with the reason, for the modules screen) and the guest boots without it, rather
        # than the whole session going back to One UI (owner's test: Oh My Keymint's sepolicy.rule).
        if [ -s "$m/sepolicy.rule" ] && [ ! -f "$m/.oneos-framework" ]; then
            echo "Guest runtime: ${m##*/} requests shared SELinux changes; disabled, not loaded"
            : > "$m/disable"
            echo "Needs SELinux policy changes, which would also change One UI's policy (one kernel)" > "$m/.oneos-disabled-reason"
            continue
        fi
        if [ -f "$m/system.prop" ]; then
            # OneOS snapshots/restores persistent properties on either return path.
            while IFS= read -r line; do
                case "$line" in ''|'#'*) continue ;; *=*)
                    key=${line%%=*}
                    case "$key" in ''|*[!A-Za-z0-9._-]*) exit 1 ;; esac
                    [ -x "$A/ksu/bin/resetprop" ] || { echo 'Module properties require reversible resetprop support'; exit 1; }
                    snapshot="$A/oneos/run/module-props"
                    if ! cut -d '|' -f 1 "$snapshot" 2>/dev/null | grep -Fxq "$key"; then
                        present=0; getprop | grep -Fq "[$key]:" && present=1
                        printf '%s|%s|%s\n' "$key" "$present" "$(getprop "$key")" >> "$snapshot"
                    fi
                    "$A/ksu/bin/resetprop" -n "$key" "${line#*=}"
                    ;; *) exit 1 ;; esac
            done < "$m/system.prop"
        fi
        [ ! -f "$m/.oneos-framework" ] || continue
        for hook in post-fs-data.sh post-mount.sh; do
            [ ! -f "$m/$hook" ] || timeout 30 "$B" sh "$m/$hook" >> "$A/oneos/run/session.log" 2>&1
        done
    done
    selected=$(cat "$A/oneos/framework")
    framework="$A/modules/$selected"
    [ -f "$framework/.oneos-framework" ] || { echo 'Guest runtime: selected framework is missing'; exit 1; }
    if [ ! -f "$framework/disable" ]; then
        [ -f "$framework/zygisk/arm64-v8a.so" ] || { echo 'Guest runtime: selected framework layout is not supported'; exit 1; }
        ( cd "$framework"; exec "$A/oneos/bin/su" --guard-exec /system/bin/sh "$framework/daemon" ) >> "$A/oneos/run/session.log" 2>&1 &
    fi
    "$A/oneos/bin/zygiskd" --workdir "$A/oneos/run/zygisk" >> "$A/oneos/run/session.log" 2>&1 &
    n=0
    while [ ! -S "$A/oneos/run/zygisk/cp64.sock" ]; do
        n=$((n+1)); [ "$n" -lt 100 ] || { echo 'Guest runtime: injector daemon did not start'; exit 1; }; sleep 0.1
    done
    ;;
customize)
    m=$2
    TMPDIR="$m/.oneos-tmp"; export TMPDIR; mkdir -p "$TMPDIR"; cp "$m/module.prop" "$TMPDIR/module.prop"
    grep_prop() { sed -n "s/^$1=//p" "${2:-/system/build.prop}" | head -n 1; }
    ui_print() { echo "$*"; }
    abort() { echo "$*" >&2; exit 1; }
    # Standard Magisk/KernelSU order: target, uid, gid, mode(s), optional context.
    set_perm() {
        chown "$2:$3" "$1" || return 1
        chmod "$4" "$1" || return 1
        chcon "${5:-u:object_r:system_file:s0}" "$1" || return 1
    }
    set_perm_recursive() {
        chown -hR "$2:$3" "$1" || return 1
        find "$1" -type d -exec chmod "$4" '{}' \; || return 1
        find "$1" -type f -exec chmod "$5" '{}' \; || return 1
        chcon -hR "${6:-u:object_r:system_file:s0}" "$1" || return 1
    }
    # The guest package service is absent before zygote. Fail promptly so a
    # module can use its own boot-time retry instead of waiting for minutes.
    pm() {
        /system/bin/service check package 2>/dev/null | grep -q ': found' || { echo 'Guest package manager is not ready; defer this operation to service.sh' >&2; return 1; }
        /data/oneos_bin/busybox timeout 10 /system/bin/pm "$@"
    }
    extract() { unzip -o "$1" "$2" -d "$3"; }
    # Root-manager customization scripts do not inherit this lifecycle shell's
    # errexit/nounset flags. Explicit abort and a failing final command still fail.
    set +eu
    [ ! -f "$m/customize.sh" ] || . "$m/customize.sh"
    ;;
late)
    A=/data/adb
    # The same PATH as the pre stage, so service.sh / boot-completed.sh find resetprop
    # and the other root-manager tools (owner's F8U: Play Integrity Fix's service.sh
    # "resetprop: not found" on every call).
    export PATH=/system/bin:/system/xbin:/data/adb/ksu/bin
    # Wait for this guest's package/activity services before starting app_process
    # based framework daemons; they must not bind to stale host services.
    n=0
    while [ "$(getprop sys.boot_completed)" != 1 ]; do n=$((n+1)); [ "$n" -lt 300 ] || exit 1; sleep 1; done
    /data/adb/oneos/bin/su --oneos-info || { echo 'Guest runtime: root broker identity check failed'; exit 1; }
    # guest_start.sh clears the shared boot flag before launching zygote;
    # only the new framework's completed boot releases this gate. Also require
    # this guest's integrated manager to have been discovered by package scan.
    n=0
    until pm path com.fahadali.oneos.guest 2>/dev/null | grep '^package:'; do
        n=$((n+1)); [ "$n" -lt 300 ] || {
            echo 'Guest runtime: Guest root manager was not discovered by the guest package manager'; exit 1;
        }
        sleep 1
    done
    # Each script's start in the shared log as well (session.log stays in the guest's /data and is
    # not in a report): S24 FE 0.4.73 b94e54fe, Pixel, after a module install and a soft reboot,
    # SystemUI got signal 15 2 s after boot_completed (boot.log 17:50:24.829), a display transition
    # snapshot then covered the screen and every touch was dropped as untrusted (17:50:29); only
    # pixel_5g_toggle_fix's service.sh ran then, and nothing named it.
    started() { /system/bin/log -t OneOSGuestRoot "$1 started" 2>/dev/null || true; }
    for m in "$A/modules"/*; do
        [ -d "$m" ] && [ ! -f "$m/disable" ] && [ ! -f "$m/remove" ] || continue
        if [ -f "$m/.oneos-framework" ]; then
            # Prevent its dex2oat helper's /proc/1/ns/mnt setns from reaching One UI.
            : # framework started before guest zygote
        elif [ -f "$m/service.sh" ]; then
            started "${m##*/}/service.sh"
            /data/oneos_bin/busybox sh "$m/service.sh" >> "$A/oneos/run/session.log" 2>&1 &
        fi
        [ ! -f "$m/boot-completed.sh" ] || { started "${m##*/}/boot-completed.sh"; /data/oneos_bin/busybox sh "$m/boot-completed.sh" >> "$A/oneos/run/session.log" 2>&1 & }
    done
    for script in "$A/service.d/"*.sh; do
        [ ! -f "$script" ] || { started "service.d/${script##*/}"; /data/oneos_bin/busybox sh "$script" >> "$A/oneos/run/session.log" 2>&1 & }
    done
    ;;
*) echo 'guest_runtime.sh: prepare | pre | customize | late' >&2; exit 2 ;;
esac
