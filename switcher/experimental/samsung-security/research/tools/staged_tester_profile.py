"""Render the fixed V2 publisher command for an already-bound stage."""

from pathlib import PurePosixPath
import shlex

import check_file_stage_device_preflight as preflight
from confirmation_tester_cohort import (
    CONFIRMATION_PUBLISHER_BYTES, CONFIRMATION_PUBLISHER_NAME, CONFIRMATION_PUBLISHER_SHA256,
)
from guest_tree_carrier_receiver import _bound_installer_preamble


def profile_publication_command(target, witness, *, confirmation=False):
    """Bind the pinned publisher and require a fresh profile and both package slots."""
    preflight.require(type(confirmation) is bool, 'Expected an explicit tester cohort selection')
    preflight.require(type(witness) is dict and witness.keys() == {'stageStat', 'guardStat', 'stageMount', 'guardMount'},
                      'Expected the exact V2 bootstrap witness')
    preamble = _bound_installer_preamble(target, witness['stageStat'], witness['guardStat'],
                                         mounts=(witness['stageMount'], witness['guardMount']))
    path, size, sha256 = preflight.drop_artifacts('v2')['deploy_publisher']
    publisher = PurePosixPath(path).name
    if confirmation:
        publisher = CONFIRMATION_PUBLISHER_NAME
        size = CONFIRMATION_PUBLISHER_BYTES
        sha256 = CONFIRMATION_PUBLISHER_SHA256
    packages, _ = preflight.readiness_artifacts('v2')
    device = target.parent.local_stat.split('|')[-2]
    command = preamble + f"""pub=/proc/self/fd/5/{publisher}
profile={shlex.quote(preflight.PROFILE)}
fmt={shlex.quote(preflight.STAT_FORMAT)}
profile_absent() {{
    row=$(/system/bin/toybox stat -c "$fmt" "$profile" 2>&1) && return 1
    case "$row" in *'No such file or directory') return 0;; *) return 1;; esac
}}
profile_absent || exit 2
pub_id=$(/system/bin/toybox stat -c "$fmt" "$pub" 5<&5) || exit 2
case "$pub_id" in '8140|500|0|0|1|{size}|{device}|'*) ;; *) exit 2;; esac
exec 4< "$pub" || exit 2
publisher_current() {{
    [ "$(mount_id 4)" = "$data_mount" ] &&
    [ "$(/system/bin/toybox stat -c "$fmt" "$pub" 5<&5)" = "$pub_id" ] &&
    [ "$(/system/bin/toybox stat -Lc "$fmt" /proc/self/fd/4 4<&4)" = "$pub_id" ]
}}
publisher_current || exit 2
digest=$(/system/bin/toybox sha256sum /proc/self/fd/4 4<&4) || exit 2
[ "${{digest%% *}}" = '{sha256}' ] && publisher_current && bound_current || exit 2
package_absent() {{
    listed=$({{ /system/bin/cmd package list packages -a -u --user all "$1" || exit 2; printf '.'; }} 2>&1) || return 1
    [ "$listed" = '.' ]
}}
package_absent {shlex.quote(packages['tester'][0])} && package_absent {shlex.quote(packages['host'][0])} || exit 2
bound_current && publisher_current && profile_absent || exit 2
exec 3<&- 5<&- 6<&- 7<&- 8<&- 9<&- || exit 2
exec /proc/self/fd/4 --publish-verified-host-profile 4<&4 </dev/null
"""
    preflight.require(command.isascii() and 0 < len(command) <= 16384, 'V2 publisher command exceeds the shell source bound')
    return command
