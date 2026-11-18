"""Render confirmation publisher delivery and independent V2 drop readback."""

import re

from check_file_stage_device_preflight import STAT_FORMAT, drop_artifacts, require
from confirmation_tester_cohort import (
    CONFIRMATION_PUBLISHER_BYTES as PUBLISHER_BYTES,
    CONFIRMATION_PUBLISHER_NAME as PUBLISHER_LEAF,
    CONFIRMATION_PUBLISHER_SHA256 as PUBLISHER_SHA256,
)
from guest_tree_carrier_receiver import _bound_installer_preamble


READBACK_FRAME = b'ONEOS_CONFIRMATION_PUBLISHER_READBACK_V1 VERIFIED_CLOSED\n'


def _frame(state, nonce):
    require(type(nonce) is str and re.fullmatch(r'[0-9a-f]{32}', nonce) is not None,
            'Invalid confirmation publisher nonce')
    return f'ONEOS_CONFIRMATION_PUBLISHER_V1 {state} {nonce}\n'.encode('ascii')


def ready_frame(nonce):
    return _frame('READY', nonce)


def published_frame(nonce):
    return _frame('PUBLISHED_CLOSED', nonce)


def _bound_preamble(target, witness):
    require(type(witness) is dict and witness.keys() == {'stageStat', 'guardStat', 'stageMount', 'guardMount'},
            'Expected the exact V2 bootstrap witness')
    return _bound_installer_preamble(
        target, witness['stageStat'], witness['guardStat'], mounts=(witness['stageMount'], witness['guardMount']),
    )


def _old_publisher_checks(device):
    _, old_size, old_sha = drop_artifacts('v2')['deploy_publisher']
    return rf"""old_id=$("$tb" stat -c "$fmt" "$drop_fd/publisher") || exit 2
case "$old_id" in '8140|500|0|0|1|{old_size}|{device}|'*) ;; *) exit 2;; esac
old_publisher_verified() (
    [ "$("$tb" stat -c "$fmt" "$drop/publisher")" = "$old_id" ] &&
    [ "$("$tb" stat -c "$fmt" "$drop_fd/publisher")" = "$old_id" ] || exit 1
    exec 4< "$drop_fd/publisher" || exit 1
    [ "$("$tb" sed -n 's/^mnt_id:[[:space:]]*//p' /proc/self/fdinfo/4 4<&4)" = "$data_mount" ] &&
    [ "$("$tb" stat -Lc "$fmt" /proc/self/fd/4 4<&4)" = "$old_id" ] || exit 1
    digest=$("$tb" sha256sum /proc/self/fd/4 4<&4) || exit 1
    [ "${{digest%% *}}" = '{old_sha}' ] &&
    [ "$("$tb" stat -Lc "$fmt" /proc/self/fd/4 4<&4)" = "$old_id" ] &&
    [ "$("$tb" stat -c "$fmt" "$drop/publisher")" = "$old_id" ] &&
    [ "$("$tb" stat -c "$fmt" "$drop_fd/publisher")" = "$old_id" ] || exit 1
    exec 4<&-
)
"""


_MISSING_CHECK = """missing() {
    row=$("$tb" stat -c %f "$1" 2>&1) && return 1
    case "$row" in *'No such file or directory') return 0;; *) return 1;; esac
}
"""


def confirmation_publisher_delivery_command(target, witness, nonce):
    """Render only. Caller owns the saved stage join, approval and shell-v2 stream.

    Supply payload after READY and close shell-v2 stdin after the exact bytes.
    Any interruption requires readback before further writes. The root-owned
    drop must have a single writer during the transfer and publication.
    """
    ready = ready_frame(nonce).decode('ascii').removesuffix('\n')
    published = published_frame(nonce).decode('ascii').removesuffix('\n')
    preamble = _bound_preamble(target, witness)
    device = target.parent.local_stat.split('|')[-2]
    command = preamble + rf"""set -o pipefail || exit 2
umask 077
tb=/system/bin/toybox
proc=/proc/$$
drop_fd=$proc/fd/5
held=$proc/fd/4
fmt='{STAT_FORMAT}'
dest='{PUBLISHER_LEAF}'
prefix='.{PUBLISHER_LEAF}-'

{_MISSING_CHECK}
{_old_publisher_checks(device)}
missing "$held" && missing "$drop_fd/$dest" && old_publisher_verified || exit 2
# An earlier failed transfer can leave a temporary sibling. Keep it for review.
set +f
for pending in "$drop_fd/$prefix"*; do
    missing "$pending" || exit 2
done
set -f
bound_current && missing "$drop_fd/$dest" || exit 2

# mktemp creates a new inode exclusively. Open its name for reading first,
# then write only through the validated descriptor, never through a leaf name.
pending=$("$tb" mktemp "$drop_fd/$prefix{nonce}.XXXXXX") || exit 3
case "$pending" in "$drop_fd/$prefix{nonce}."[a-zA-Z0-9][a-zA-Z0-9][a-zA-Z0-9][a-zA-Z0-9][a-zA-Z0-9][a-zA-Z0-9]) ;; *) exit 3;; esac
pending_leaf=${{pending##*/}}
empty=$("$tb" stat -c "$fmt" "$pending") || exit 3
case "$empty" in '8180|600|0|0|1|0|{device}|'*) ;; *) exit 3;; esac
exec 4< "$pending" || exit 3
ino=$("$tb" stat -Lc %i "$held" 4<&4) || exit 3
case "$ino" in ''|0*|*[!0-9]*) exit 3;; esac

candidate_at() {{
    row=$("$tb" stat -Lc "$fmt" "$held" 4<&4) || return 1
    case "$row" in "$2|0|0|$3|$4|{device}|$ino|"*) ;; *) return 1;; esac
    [ "$(mount_id 4)" = "$data_mount" ] &&
    [ "$("$tb" stat -c "$fmt" "$drop_fd/$1")" = "$row" ] &&
    [ "$("$tb" stat -c "$fmt" "$drop/$1")" = "$row" ] && printf '%s\n' "$row"
}}

candidate_hash() {{
    digest=$("$tb" sha256sum "$held" 4<&4) || return 1
    [ "${{digest%% *}}" = '{PUBLISHER_SHA256}' ]
}}

bound_current && [ "$(candidate_at "$pending_leaf" '8180|600' 1 0)" = "$empty" ] || exit 3
printf '%s\n' '{ready}' || exit 3
"$tb" dd bs=65536 iflag=count_bytes count={PUBLISHER_BYTES} status=none conv=notrunc,fsync of="$held" 4<&4 || exit 3
extra=$("$tb" dd bs=1 iflag=count_bytes count=1 status=none | "$tb" wc -c) || exit 3
[ "$extra" -eq 0 ] || exit 3
exec 0<&- || exit 3

received=$(candidate_at "$pending_leaf" '8180|600' 1 {PUBLISHER_BYTES}) || exit 3
candidate_hash && [ "$(candidate_at "$pending_leaf" '8180|600' 1 {PUBLISHER_BYTES})" = "$received" ] || exit 3
"$tb" chmod 0500 "$held" 4<&4 || exit 3
sealed=$(candidate_at "$pending_leaf" '8140|500' 1 {PUBLISHER_BYTES}) || exit 3
"$tb" fsync "$held" 4<&4 || exit 3
bound_current && old_publisher_verified && missing "$drop_fd/$dest" && candidate_hash &&
[ "$(candidate_at "$pending_leaf" '8140|500' 1 {PUBLISHER_BYTES})" = "$sealed" ] || exit 3

"$tb" ln -T "$pending" "$drop_fd/$dest" || exit 3
linked=$(candidate_at "$dest" '8140|500' 2 {PUBLISHER_BYTES}) || exit 3
bound_current && candidate_hash && [ "$(candidate_at "$dest" '8140|500' 2 {PUBLISHER_BYTES})" = "$linked" ] &&
[ "$(candidate_at "$pending_leaf" '8140|500' 2 {PUBLISHER_BYTES})" = "$linked" ] || exit 3
"$tb" rm "$pending" || exit 3
final=$(candidate_at "$dest" '8140|500' 1 {PUBLISHER_BYTES}) || exit 3
"$tb" fsync "$held" "$drop_fd" 4<&4 5<&5 || exit 3
bound_current && old_publisher_verified && missing "$pending" && candidate_hash &&
[ "$(candidate_at "$dest" '8140|500' 1 {PUBLISHER_BYTES})" = "$final" ] || exit 3
exec 3<&- 4<&- 5<&- 6<&- 7<&- 8<&- 9<&- || exit 3
for slot in 3 4 5 6 7 8 9; do
    missing "$proc/fd/$slot" || exit 3
done
printf '%s\n' '{published}' || exit 3
"""
    require(command.isascii() and 0 < len(command) <= 16384,
            'Confirmation publisher command exceeds the shell source bound')
    return command


def confirmation_publisher_readback_command(target, witness):
    """Render a separate read-only observation for an independently bound V2 shell."""
    preamble = _bound_preamble(target, witness)
    device = target.parent.local_stat.split('|')[-2]
    terminal = READBACK_FRAME.decode('ascii').removesuffix('\n')
    command = preamble + rf"""set -o pipefail || exit 2
tb=/system/bin/toybox
proc=/proc/$$
drop_fd=$proc/fd/5
held=$proc/fd/4
fmt='{STAT_FORMAT}'
dest='{PUBLISHER_LEAF}'

{_MISSING_CHECK}
{_old_publisher_checks(device)}
directory_exact() (
    set +f
    count=0
    for entry in "$drop_fd"/* "$drop_fd"/.[!.]* "$drop_fd"/..?*; do
        case "$entry" in
            "$drop_fd/installer"|"$drop_fd/publisher"|"$drop_fd/$dest") count=$((count+1));;
            "$drop_fd/*"|"$drop_fd/.[!.]*"|"$drop_fd/..?*") missing "$entry" || exit 1;;
            *) exit 1;;
        esac
    done
    [ "$count" -eq 3 ]
)

bound_current && missing "$held" && directory_exact && old_publisher_verified || exit 2
new_id=$("$tb" stat -c "$fmt" "$drop_fd/$dest") || exit 2
case "$new_id" in '8140|500|0|0|1|{PUBLISHER_BYTES}|{device}|'*) ;; *) exit 2;; esac
exec 4< "$drop_fd/$dest" || exit 2
new_publisher_current() {{
    [ "$(mount_id 4)" = "$data_mount" ] &&
    [ "$("$tb" stat -Lc "$fmt" "$held" 4<&4)" = "$new_id" ] &&
    [ "$("$tb" stat -c "$fmt" "$drop_fd/$dest")" = "$new_id" ] &&
    [ "$("$tb" stat -c "$fmt" "$drop/$dest")" = "$new_id" ]
}}
new_publisher_current || exit 2
digest=$("$tb" sha256sum "$held" 4<&4) || exit 2
[ "${{digest%% *}}" = '{PUBLISHER_SHA256}' ] || exit 2
bound_current && old_publisher_verified && new_publisher_current && directory_exact || exit 2
exec 3<&- 4<&- 5<&- 6<&- 7<&- 8<&- 9<&- || exit 2
for slot in 3 4 5 6 7 8 9; do
    missing "$proc/fd/$slot" || exit 2
done
printf '%s\n' '{terminal}' || exit 2
"""
    require(command.isascii() and 0 < len(command) <= 16384,
            'Confirmation publisher readback exceeds the shell source bound')
    return command
