"""Load the reviewed V2 tester APK and render its isolated install command."""

import json
import shlex

from check_file_stage_device_preflight import PROFILE, STAT_FORMAT, readiness_artifacts, require
from check_file_stage_local_cohort import pair_receipt_pin, verify_local_cohort
from confirmation_tester_cohort import (
    CONFIRMATION_PROFILE_SHA256, CONFIRMATION_TESTER_BYTES, load_confirmation_cohort,
)
from confirmation_tester_data_slot import data_slot_checks
from guest_tree_carrier_receiver import _bound_installer_preamble, validate_target
from run_guest_tree_install_transport import load_io, pinned


def load_tester_apk(*, confirmation=False) -> bytes:
    """Read the exact reviewed signed tester into one immutable byte buffer."""
    require(type(confirmation) is bool, 'Expected an explicit tester cohort selection')
    if confirmation:
        return load_confirmation_cohort().tester_apk.data

    cohort = verify_local_cohort(carrier_protocol='v2')
    pair_path, pair_sha = pair_receipt_pin('v2')
    require(cohort['status'] == 'MATCHED_LOCAL_COHORT_VERIFIED' and cohort['mayExecute'] is False
            and cohort['installerProtocol'] == 'v2' and cohort['pairReceiptSha256'] == pair_sha,
            'Unexpected local tester cohort')
    packages, readiness = readiness_artifacts('v2')
    name, size, _ = packages['tester']
    io = load_io()
    pair = json.loads(pinned(io, pair_path, pair_sha, 64 * 1024), object_pairs_hook=io['unique_object'])
    tester = pair['packages']['app']
    apk = tester['apk']
    require(tester['package'] == name and type(tester['versionCode']) is int and tester['versionCode'] == 1
            and type(apk['bytes']) is int and apk['bytes'] == size and apk['sha256'] == readiness['tester']
            and cohort['packages']['tester'] == {'package': name, 'apkSha256': apk['sha256'],
                                                'certificateSha256': tester['publicCertificate']['sha256']},
            'Signed tester APK differs from the reviewed cohort')
    data = pinned(io, apk['path'], apk['sha256'], size)
    require(len(data) == size, 'Incomplete signed tester APK')
    return data


def tester_install_command(target, bootstrap_witness, *, confirmation=False) -> str:
    """Render the fixed no-replacement command without opening a transport."""
    require(type(confirmation) is bool, 'Expected an explicit tester cohort selection')
    validate_target(target)
    require(target.carrier_protocol == 'v2' and type(bootstrap_witness) is dict
            and bootstrap_witness.keys() == {'stageStat', 'guardStat', 'stageMount', 'guardMount'},
            'Expected the bound V2 tester install inputs')
    preamble = _bound_installer_preamble(
        target, bootstrap_witness['stageStat'], bootstrap_witness['guardStat'],
        mounts=(bootstrap_witness['stageMount'], bootstrap_witness['guardMount']),
    )
    packages, readiness = readiness_artifacts('v2')
    tester, size, _ = packages['tester']
    profile_sha256 = readiness['profile']
    data_guard = ''
    if confirmation:
        size = CONFIRMATION_TESTER_BYTES
        profile_sha256 = CONFIRMATION_PROFILE_SHA256
        # Send the frame to /dev/null and count diagnostic bytes separately.
        data_guard = f"""data_slot_diagnostics=$(
    set -o pipefail 2>/dev/null || exit 2
    (
{data_slot_checks()}    ) </dev/null 2>&1 >/dev/null | /system/bin/toybox wc -c 2>/dev/null
) || exit 2
[ "$data_slot_diagnostics" = 0 ] || exit 2
"""
    host = packages['host'][0]
    device = target.parent.local_stat.split('|')[-2]
    command = preamble + f"""profile={shlex.quote(PROFILE)}
fmt={shlex.quote(STAT_FORMAT)}
profile_id=$(/system/bin/toybox stat -c "$fmt" "$profile") || exit 2
case "$profile_id" in '8120|440|0|1000|1|288|{device}|'*) ;; *) exit 2;; esac
exec 4< "$profile" || exit 2
profile_current() {{
    [ "$(mount_id 4)" = "$data_mount" ] &&
    [ "$(/system/bin/toybox stat -c "$fmt" "$profile")" = "$profile_id" ] &&
    [ "$(/system/bin/toybox stat -Lc "$fmt" "/proc/$$/fd/4")" = "$profile_id" ]
}}
profile_current || exit 2
digest=$(/system/bin/toybox sha256sum "/proc/$$/fd/4") || exit 2
[ "${{digest%% *}}" = '{profile_sha256}' ] || exit 2
{data_guard}package_absent() {{
    listed=$({{ /system/bin/cmd package list packages -a -u --user all "$1" || exit 2; printf '.'; }} 2>&1) || return 1
    [ "$listed" = '.' ]
}}
package_absent {shlex.quote(tester)} && package_absent {shlex.quote(host)} || exit 2
bound_current && profile_current || exit 2
exec 3<&- 4<&- 5<&- 6<&- 7<&- 8<&- 9<&- || exit 2
printf 'ONEOS_APK_READY\\n' || exit 2
exec /system/bin/cmd package install -R --user 0 -S {size} -
"""
    require(command.isascii() and 0 < len(command) <= 16384, 'V2 tester command exceeds the shell source bound')
    return command
