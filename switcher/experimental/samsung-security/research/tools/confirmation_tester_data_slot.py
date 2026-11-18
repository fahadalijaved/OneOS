"""Render and parse metadata-only checks of the fixed tester's app data slots."""

import re

from check_file_stage_device_preflight import require
from guest_tree_carrier_receiver import _bound_installer_preamble


TESTER = 'com.fahadali.oneos.viewprep.filetree'
MAX_USERS = 64
REPLY_LIMIT = 4096
_FRAME = 'ONEOS_TESTER_DATA_V1'
_USER = re.compile(r'0|[1-9][0-9]{0,9}')


def data_slot_checks():
    """Render the framed check body for the bound preamble's shell context."""
    return _CHECKS.replace('@TESTER@', TESTER).replace('@MAX_USERS@', str(MAX_USERS))


def data_slot_command(target, witness):
    """Observe direct internal CE, DE and legacy slots in the current installd view."""
    require(type(witness) is dict and witness.keys() == {'stageStat', 'guardStat', 'stageMount', 'guardMount'},
            'Expected the exact V2 bootstrap witness')
    preamble = _bound_installer_preamble(target, witness['stageStat'], witness['guardStat'],
                                         mounts=(witness['stageMount'], witness['guardMount']))
    command = preamble + data_slot_checks()
    require(command.isascii() and 0 < len(command) <= 16384, 'Tester data-slot command exceeds the shell source bound')
    return command


def require_empty_data_slots(code, stdout, stderr, *, eof) -> None:
    """Admit only the complete successful reply from the bound shell after EOF."""
    require(type(code) is int and code == 0 and type(stdout) is bytes and type(stderr) is bytes
            and not stderr and eof is True and 0 < len(stdout) <= REPLY_LIMIT and stdout.endswith(b'\n')
            and re.fullmatch(rb'[ -~\n]+', stdout), 'Tester data-slot observation is unconfirmed')
    lines = stdout[:-1].decode('ascii').split('\n')
    require(len(lines) >= 7 and lines[0] == _FRAME + ' BEGIN', 'Missing tester data-slot frame')
    header = lines[1].split(' ')
    users = header[1:]
    require(header[0] == 'USERS' and 0 < len(users) <= MAX_USERS and users[0] == '0'
            and all(_USER.fullmatch(user) for user in users), 'Invalid tester data-slot user set')
    ids = [int(user) for user in users]
    require(ids == sorted(set(ids)) and ids[-1] <= 2**31 - 1, 'Ambiguous tester data-slot user set')
    expected = [f'{kind} {user} ABSENT' for user in users for kind in ('CE', 'DE')]
    expected.extend(('LEGACY ABSENT', 'ADOPTED NONE', _FRAME + ' END'))
    require(lines[2:] == expected, 'Tester data slots are occupied, incomplete or unobservable')


_CHECKS = r"""tb=/system/bin/toybox
tester='@TESTER@'
directory_token() {
    [ -r "$1" ] && [ -x "$1" ] || return 1
    token=$("$tb" stat -c '%f|%d|%i' "$1") || return 1
    printf '%s\n' "$token" | "$tb" grep -Eq '^4[0-9a-f]{3}\|[1-9][0-9]{0,19}\|[1-9][0-9]{0,19}$' || return 1
    printf '%s\n' "$token"
}
leaf_absent() {
    error=$({ "$tb" stat -c '%f' "$1"; rc=$?; printf '.'; exit "$rc"; } 2>&1)
    [ "$?" -eq 1 ] && [ "$error" = "$(printf "stat: '%s': No such file or directory\n." "$1")" ]
}
canonical_ids() (
    set -- $1
    [ "$#" -ge 1 ] && [ "$#" -le @MAX_USERS@ ] || exit 1
    ordered=$(printf '%s\n' "$@" | "$tb" sort -n) || exit 1
    set -- $ordered
    [ "$#" -ge 1 ] && [ "$#" -le @MAX_USERS@ ] && [ "$1" = 0 ] || exit 1
    prior=-1
    for id in "$@"; do
        printf '%s\n' "$id" | "$tb" grep -Eq '^(0|[1-9][0-9]{0,9})$' || exit 1
        [ "$id" -gt "$prior" ] && [ "$id" -le 2147483647 ] || exit 1
        prior=$id
    done
    printf '%s' "$*"
)
parse_registry() (
    IFS= read -r header || exit 1
    [ "$header" = 'Users:' ] || exit 1
    ids=
    while IFS= read -r row; do
        if [ "$row" = '.' ]; then
            ! IFS= read -r extra || exit 1
            canonical_ids "$ids"
            exit $?
        fi
        id=$(printf '%s\n' "$row" | "$tb" sed -nE 's/^[[:blank:]]+UserInfo\{(0|[1-9][0-9]{0,9}):[^:{}[:cntrl:]]*:[0-9a-fA-F]+\}( running)?$/\1/p') || exit 1
        [ -n "$id" ] || exit 1
        ids="$ids $id"
    done
    exit 1
)
registry_ids() (
    rows=$({ /system/bin/cmd user list --all || exit 1; printf '.'; } 2>&1) || exit 1
    [ "${#rows}" -le 8192 ] || exit 1
    parse_registry <<EOF
$rows
EOF
)
parent_ids() (
    rows=$({ "$tb" ls -1A "$1" || exit 1; printf '.'; } 2>&1) || exit 1
    [ "${#rows}" -le 1024 ] || exit 1
    ids=
    while IFS= read -r row; do
        if [ "$row" = '.' ]; then
            ! IFS= read -r extra || exit 1
            canonical_ids "$ids"
            exit $?
        fi
        printf '%s\n' "$row" | "$tb" grep -Eq '^(0|[1-9][0-9]{0,9})$' || exit 1
        ids="$ids $row"
    done <<EOF
$rows
EOF
    exit 1
)
unlocked() {
    state=$({ /system/bin/cmd activity get-started-user-state "$1" || exit 1; printf '.'; } 2>&1) || return 1
    [ "$state" = "$(printf 'RUNNING_UNLOCKED\n.')" ]
}
adopted_clear() {
    volumes=$({ /system/bin/sm list-volumes private || exit 1; printf '.'; } 2>&1) || return 1
    [ "$volumes" = "$(printf 'private mounted null\n.')" ] || return 1
    entries=$({ "$tb" ls -1A /mnt/expand || exit 1; printf '.'; } 2>&1) || return 1
    [ "$entries" = '.' ] || return 1
    "$tb" grep -Eq '^[^ ]+ [^ ]+ [^ ]+ [^ ]+ /mnt/expand/[^ ]+' "/proc/$$/mountinfo"
    [ "$?" -eq 1 ]
}
installd_token() (
    pid=$("$tb" pidof installd) || exit 1
    printf '%s\n' "$pid" | "$tb" grep -Eq '^[1-9][0-9]{0,9}$' || exit 1
    [ "$("$tb" readlink "/proc/$pid/ns/mnt")" = "$namespace" ] || exit 1
    root=$("$tb" stat -Lc '%d|%i' "/proc/$pid/root") || exit 1
    [ "$root" = "$("$tb" stat -c '%d|%i' /)" ] || exit 1
    proc=$("$tb" cat "/proc/$pid/stat") || exit 1
    set -- ${proc##*\) }
    [ "$#" -ge 20 ] || exit 1
    shift 19
    printf '%s\n' "$1" | "$tb" grep -Eq '^[1-9][0-9]{0,19}$' || exit 1
    printf '%s|%s' "$pid" "$1"
)
ce_token() {
    path=/data/user/$1
    if [ "$1" = 0 ] && [ -L "$path" ]; then
        [ "$("$tb" readlink "$path")" = /data/data ] || return 1
        [ -r "$path" ] && [ -x "$path" ] || return 1
        token=$("$tb" stat -Lc '%f|%d|%i' "$path") || return 1
        [ "$token" = "$legacy" ] || return 1
        printf 'alias|%s\n' "$token"
    else
        directory_token "$path"
    fi
}
mount_token() {
    digest=$("$tb" sha256sum "/proc/$$/mountinfo") || return 1
    printf '%s' "${digest%% *}"
}

installer=$(installd_token) || exit 2
mounts=$(mount_token) || exit 2
ce_root=$(directory_token /data/user) || exit 2
de_root=$(directory_token /data/user_de) || exit 2
legacy=$(directory_token /data/data) || exit 2
mnt=$(directory_token /mnt) || exit 2
expand=$(directory_token /mnt/expand) || exit 2
users=$(registry_ids) || exit 2
[ "$(parent_ids /data/user)" = "$users" ] && [ "$(parent_ids /data/user_de)" = "$users" ] || exit 2
adopted_clear && leaf_absent "/data/data/$tester" || exit 2
printf 'ONEOS_TESTER_DATA_V1 BEGIN\nUSERS %s\n' "$users" || exit 2
for id in $users; do
    unlocked "$id" || exit 2
    ce=$(ce_token "$id") && de=$(directory_token "/data/user_de/$id") || exit 2
    leaf_absent "/data/user/$id/$tester" && leaf_absent "/data/user_de/$id/$tester" || exit 2
    [ "$(ce_token "$id")" = "$ce" ] && [ "$(directory_token "/data/user_de/$id")" = "$de" ] && unlocked "$id" || exit 2
    printf 'CE %s ABSENT\nDE %s ABSENT\n' "$id" "$id" || exit 2
done
for id in $users; do unlocked "$id" || exit 2; done
[ "$(registry_ids)" = "$users" ] && [ "$(parent_ids /data/user)" = "$users" ] &&
[ "$(parent_ids /data/user_de)" = "$users" ] && [ "$(directory_token /data/user)" = "$ce_root" ] &&
[ "$(directory_token /data/user_de)" = "$de_root" ] && [ "$(directory_token /data/data)" = "$legacy" ] &&
[ "$(directory_token /mnt)" = "$mnt" ] && [ "$(directory_token /mnt/expand)" = "$expand" ] &&
adopted_clear && leaf_absent "/data/data/$tester" &&
[ "$(mount_token)" = "$mounts" ] && [ "$(installd_token)" = "$installer" ] && bound_current || exit 2
printf 'LEGACY ABSENT\nADOPTED NONE\nONEOS_TESTER_DATA_V1 END\n' || exit 2
"""
