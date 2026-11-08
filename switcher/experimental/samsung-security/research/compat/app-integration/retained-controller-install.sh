# Authored fixed-target handler. Defines a function only; sourcing does not install.
# The containing root script supplies STAGE, ROOT_UID, ROOT_OWNER, ge, sha,
# idle_or_refuse, say, refuse, die and usage. No controller is ever executed here.
do_install_closed_controller() (
    [ $# -eq 2 ] || usage "install-closed-controller <bytes> <sha256>"
    ci_bytes=$1 ci_sum=$2
    case "$ci_bytes" in ''|0*|*[!0-9]*) usage "invalid closed controller size" ;; esac
    [ ${#ci_bytes} -le 7 ] && ge 2097152 "$ci_bytes" || usage "closed controller size out of range"
    case "$ci_sum" in *[!0-9a-f]*) usage "invalid closed controller SHA256" ;; esac
    [ ${#ci_sum} -eq 64 ] || usage "invalid closed controller SHA256"
    umask 077
    ci_stage_open=0 ci_bin_open=0 ci_work_open=0 ci_payload_open=0 ci_target_open=0
    ci_work_owned=0 ci_payload_owned=0 ci_published=0 ci_verified=0 ci_cleaned=0 ci_cleanup_ok=0
    ci_work_id= ci_payload_id=
    ci_fdroot=/proc/self/fd

    ci_directory_profile() {
        [ -d "$1" ] && [ ! -L "$1" ] || return 1
        [ "$(stat -c %u "$1" 2>/dev/null)" = "$ROOT_UID" ] || return 1
        case "$(stat -c %a "$1" 2>/dev/null)" in [57][0145][0145]) return 0 ;; esac
        return 1
    }
    ci_fd_profile() {
        [ "$(stat -Lc %u "$1" 2>/dev/null)" = "$ROOT_UID" ] || return 1
        case "$(stat -Lc %a "$1" 2>/dev/null)" in [57][0145][0145]) return 0 ;; esac
        return 1
    }
    ci_same_directories() {
        ci_directory_profile "$STAGE" && ci_directory_profile "$STAGE/bin" &&
        [ -d "$ci_fdroot/8" ] && [ -d "$ci_fdroot/9" ] &&
        ci_fd_profile "$ci_fdroot/8" && ci_fd_profile "$ci_fdroot/9" &&
        [ "$(stat -c '%d:%i' "$STAGE" 2>/dev/null)" = "$ci_stage_id" ] &&
        [ "$(stat -Lc '%d:%i' "$ci_fdroot/8" 2>/dev/null)" = "$ci_stage_id" ] &&
        [ "$(stat -c '%d:%i' "$STAGE/bin" 2>/dev/null)" = "$ci_bin_id" ] &&
        [ "$(stat -Lc '%d:%i' "$ci_fdroot/9" 2>/dev/null)" = "$ci_bin_id" ]
    }
    ci_same_target() {
        [ -f "$ci_target" ] && [ ! -L "$ci_target" ] &&
        ci_fd_profile "$ci_target" && [ -f "$ci_fdroot/7" ] && ci_fd_profile "$ci_fdroot/7" &&
        [ "$(stat -Lc '%d:%i' "$ci_fdroot/7" 2>/dev/null)" = "$ci_target_id" ] &&
        [ ! -L "$ci_target" ] &&
        [ "$(stat -c '%d:%i' "$ci_target" 2>/dev/null)" = "$ci_target_id" ]
    }
    ci_cleanup() {
        if [ "$ci_cleaned" = 1 ]; then [ "$ci_cleanup_ok" = 1 ]; return; fi
        ci_cleaned=1 ci_bad=0 # consume cleanup once, including uncertain failures
        if [ "$ci_payload_open" = 1 ]; then ci_payload_open=0; exec 6>&- || ci_bad=1; fi
        if [ "$ci_payload_owned" = 1 ]; then
            ci_payload_owned=0
            if [ ! -e "$ci_work/payload" ] && [ ! -L "$ci_work/payload" ]; then :
            elif [ -n "$ci_payload_id" ] && [ -f "$ci_work/payload" ] && [ ! -L "$ci_work/payload" ] &&
                 [ "$(stat -c '%d:%i' "$ci_work/payload" 2>/dev/null)" = "$ci_payload_id" ]; then
                rm "$ci_work/payload" || ci_bad=1
            else ci_bad=1
            fi
        fi
        if [ "$ci_work_owned" = 1 ]; then
            ci_work_owned=0
            if [ -n "$ci_work_id" ] && [ -d "$ci_work_name" ] && [ ! -L "$ci_work_name" ] &&
               [ "$(stat -c '%d:%i' "$ci_work_name" 2>/dev/null)" = "$ci_work_id" ]; then
                rmdir "$ci_work_name" || ci_bad=1
            else ci_bad=1
            fi
        fi
        if [ "$ci_work_open" = 1 ]; then ci_work_open=0; exec 5<&- || ci_bad=1; fi
        # The content hash was read through FD7. Recheck its actual named leaf
        # AFTER hashing and all temporary-path cleanup while parent/target FDs
        # are still held. Only our descriptor closes and ACK follow this check.
        if [ "$ci_verified" = 1 ]; then
            ci_same_directories && ci_same_target || ci_bad=1
        fi
        if [ "$ci_target_open" = 1 ]; then ci_target_open=0; exec 7<&- || ci_bad=1; fi
        if [ "$ci_bin_open" = 1 ]; then ci_bin_open=0; exec 9<&- || ci_bad=1; fi
        if [ "$ci_stage_open" = 1 ]; then ci_stage_open=0; exec 8<&- || ci_bad=1; fi
        [ "$ci_bad" = 0 ] || return 1
        ci_cleanup_ok=1
    }
    ci_exit() {
        ci_status=$?
        trap - 0 HUP INT TERM
        if ! ci_cleanup; then
            say "@@FAILED closed controller cleanup uncertain"
            ci_status=4
        fi
        case "$ci_status" in 0|2|3|4) ;; *) ci_status=4 ;; esac
        exit "$ci_status"
    }
    trap ci_exit 0
    trap 'die "closed controller install interrupted"' HUP INT TERM
    # Do not overwrite an inherited descriptor belonging to the fixed launcher.
    for ci_slot in 5 6 7 8 9; do
        [ ! -e "$ci_fdroot/$ci_slot" ] && [ ! -L "$ci_fdroot/$ci_slot" ] ||
            refuse "closed controller descriptor slot is occupied"
    done
    ci_directory_profile "$STAGE" && ci_directory_profile "$STAGE/bin" ||
        refuse "closed controller needs existing root-owned stage and bin"
    ci_stage_id=$(stat -c '%d:%i' "$STAGE") || refuse "could not inspect stage"
    ci_bin_id=$(stat -c '%d:%i' "$STAGE/bin") || refuse "could not inspect bin"
    ci_stage_open=1; exec 8<"$STAGE"
    ci_bin_open=1; exec 9<"$ci_fdroot/8/bin"
    ci_bin=$ci_fdroot/9
    ci_target=$ci_bin/oneos_retained_root_session
    ci_work_name=$ci_bin/.oneos-retained-controller-install
    ci_same_directories || refuse "closed controller directory identity changed"
    idle_or_refuse # existing read-only mount/bridge/loop refusal; not orphan proof
    # An existing work directory is another/uncertain owner; never delete it.
    mkdir "$ci_work_name" || refuse "closed controller installer already owned"
    ci_work_owned=1 # before open, metadata changes, payload acquisition or checks
    ci_work_id=$(stat -c '%d:%i' "$ci_work_name") || die "could not retain installer identity"
    ci_work_open=1; exec 5<"$ci_work_name"
    ci_work=$ci_fdroot/5
    [ -d "$ci_work" ] && [ "$(stat -Lc '%d:%i' "$ci_work")" = "$ci_work_id" ] ||
        die "installer directory identity changed"
    # These are newly created installer objects only, never existing OneOS data.
    chown "$ROOT_OWNER" "$ci_work" && chmod 0700 "$ci_work" || die "could not protect installer"
    ci_payload_owned=1 ci_payload_open=1
    set -C
    exec 6>"$ci_work/payload" # noclobber creation in the exclusively owned directory
    set +C
    ci_payload_id=$(stat -Lc '%d:%i' "$ci_fdroot/6") || die "could not retain payload identity"
    [ -f "$ci_fdroot/6" ] && [ ! -L "$ci_work/payload" ] &&
        [ "$(stat -c '%d:%i' "$ci_work/payload")" = "$ci_payload_id" ] || die "payload identity changed"
    ci_limit=$((ci_bytes + 1)) # canonical decimal and <=2MiB, safe with mksh arithmetic
    # Reads at most expected+1, and waits for EOF when exactly expected arrive.
    # Root's DATA producer closes stdin; no invented read-timeout acknowledgement.
    head -c "$ci_limit" >&6 || die "could not receive closed controller"
    [ "$(stat -Lc %s "$ci_fdroot/6")" = "$ci_bytes" ] || refuse "closed controller length mismatch"
    [ "$(sha "$ci_fdroot/6")" = "$ci_sum" ] || refuse "closed controller SHA256 mismatch"
    chown "$ROOT_OWNER" "$ci_fdroot/6" && chmod 0755 "$ci_fdroot/6" || die "could not protect controller payload"
    ci_same_directories || refuse "closed controller directories changed"
    if [ ! -e "$ci_target" ] && [ ! -L "$ci_target" ]; then
        # The final source component is an actual regular name under the held
        # 0700 private directory. The intermediate proc-FD5 follows normally;
        # no -L support for a final proc magic link is needed. Recheck the name
        # against owned FD6 immediately before the atomic link.
        [ -f "$ci_work/payload" ] && [ ! -L "$ci_work/payload" ] &&
            [ "$(stat -c '%d:%i' "$ci_work/payload")" = "$ci_payload_id" ] &&
            [ "$(stat -Lc '%d:%i' "$ci_fdroot/6")" = "$ci_payload_id" ] ||
            die "payload name changed before publication"
        # -T forbids a directory-target fallback. No -f, cp or overwriting mv;
        # unsupported publication fails closed with no alternative path.
        if ln -T "$ci_work/payload" "$ci_target"; then
            ci_published=1
        else
            [ -e "$ci_target" ] || [ -L "$ci_target" ] || die "exclusive controller publication failed"
        fi
    fi
    [ -f "$ci_target" ] && [ ! -L "$ci_target" ] || refuse "existing controller is not a regular nonlink image"
    ci_target_id=$(stat -c '%d:%i' "$ci_target") || refuse "could not inspect installed controller"
    ci_target_open=1; exec 7<"$ci_target"
    [ -f "$ci_fdroot/7" ] && ci_fd_profile "$ci_fdroot/7" &&
        [ "$(stat -Lc '%d:%i' "$ci_fdroot/7")" = "$ci_target_id" ] &&
        [ ! -L "$ci_target" ] && [ "$(stat -c '%d:%i' "$ci_target")" = "$ci_target_id" ] &&
        [ "$(stat -Lc %s "$ci_fdroot/7")" = "$ci_bytes" ] &&
        [ "$(sha "$ci_fdroot/7")" = "$ci_sum" ] ||
        refuse "different or unsafe controller already installed; replacement refused"
    [ "$ci_published" = 0 ] || [ "$ci_target_id" = "$ci_payload_id" ] ||
        die "published controller is not the retained payload inode"
    ci_same_directories && ci_same_target || refuse "closed controller image changed after verification"
    # No chmod/chown/removal/replacement of an existing target, even after a
    # later failure: it might already be executing. Idempotence checks content.
    ci_verified=1
    ci_cleanup || die "closed controller cleanup uncertain"
    say "@@OK closed-controller-installed"
)
