"""Collect bounded read-only evidence from the existing paired ADB service."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shlex
import socket
import stat
import struct
import time
import uuid

from run_guest_tree_install_transport import carrier_installer_pin


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'out/file-stage-device-preflight'
ENDPOINT = ('127.0.0.1', 5038)
MODEL = 'SM-S948U1'
BUILD = 'CP2A.260605.016.S948U1UES4BZIG'
FINGERPRINT = 'samsung/m3quew/m3q:17/CP2A.260605.016/S948U1UES4BZIG_OYM4BZIG:user/release-keys'
SCHEMA = 'oneos-file-stage-read-only-preflight/v4'
STAGE = '/data/local/tmp/oneos-viewprep'
GUARD = '/dev/oneos-retained-viewprep'
PROFILE = '/data/system/oneos_retained_root_link_v2'
HOST_PERMIT_DIR = '/data/system/oneos-samsung-pin-host-bootstrap'
HOST_PERMIT = HOST_PERMIT_DIR + '/request-v1'
HOST_PERMIT_MARKER = b'CAPTURE_PIN_HOST_BOOTSTRAP_V1\n'
HOST_PERMIT_SHA = hashlib.sha256(HOST_PERMIT_MARKER).hexdigest()
DROP_PARENT = '/data/local'
DEPLOY_DROP = DROP_PARENT + '/.oneos-file-stage-803691c5'


def drop_artifacts(carrier_protocol='v1'):
    pin = carrier_installer_pin(carrier_protocol)
    publisher = ((580128, '080eaecc5e8024078126158489200a4a758749d07dd4a42fe8a3dbbfe4b399e5')
                 if carrier_protocol == 'v2' else
                 (602736, 'a52243daf6a0c153efaf6410d1341806486a3f98fc9faac71210d92848bae477'))
    return {
        'deploy_installer': (DEPLOY_DROP + '/installer', pin.artifact_bytes, pin.artifact_sha256),
        'deploy_publisher': (DEPLOY_DROP + '/publisher', *publisher),
    }


DROP_ARTIFACTS = drop_artifacts()
MIN_FREE = 13890850816 + 109383680 + 134217728
PATHS = {
    'data': '/data', 'local': '/data/local', 'tmp': '/data/local/tmp', 'system': '/data/system', 'dev': '/dev',
    'stage': STAGE, 'stage_tmp': '/data/local/.oneos-viewprep.new', 'bin': STAGE + '/bin',
    'backing': STAGE + '/backing', 'private_data': STAGE + '/data', 'private_user': STAGE + '/data/user',
    'private_user0': STAGE + '/data/user/0', 'private_alias': STAGE + '/data/data',
    'carrier': STAGE + '/guest.erofs', 'carrier_tmp': STAGE + '/.guest.erofs.new',
    'controller': STAGE + '/bin/oneos_retained_tree_preparation',
    'controller_tmp': STAGE + '/bin/.oneos_retained_tree_preparation.new',
    'guard': GUARD, 'guard_tmp': '/dev/.oneos-retained-viewprep.new', 'lease': GUARD + '/lease',
    'writer_blocked': GUARD + '/writer-blocked', 'legacy_blocked': GUARD + '/legacy-blocked',
    'view_blocked': GUARD + '/view-blocked', 'profile': PROFILE,
    'host_permit_dir': HOST_PERMIT_DIR, 'host_permit': HOST_PERMIT,
    'deploy_drop': DEPLOY_DROP,
    **{role: artifact[0] for role, artifact in DROP_ARTIFACTS.items()},
}
PACKAGES = {
    'tester': ('com.fahadali.oneos.viewprep.filetree', 49356,
               '28bf08bb0fd79782280c468bfdba9f700315695e3847c78657e135bafdf43fe5'),
    'host': ('com.appleexploit.oneos.security.retainedguard', 139689,
             '50413f663e7a87d1b561dc5aaefdc7c46561dc431fffe03d3bc4053be0a9e2c4'),
}
READINESS_PINS = {
    'tester': 'ad51b53f141904ee1dd465fd26a7d214ab98ca635e185eb02d13d67c7d51aea4',
    'host': '4feb18aa31f2ade65d954cf64f5f909e7731106773df41802907c46c80f6a163',
    'profile': '51f95b060b279fd7d92b3ec99b2d3fd7d324ded13d8012d5023f6dcf6b6b9ddf',
}


def readiness_artifacts(carrier_protocol='v1', *, confirmation=False):
    carrier_installer_pin(carrier_protocol)
    require(type(confirmation) is bool and (not confirmation or carrier_protocol == 'v2'),
            'Confirmation observations require V2')
    packages = PACKAGES.copy()
    readiness = READINESS_PINS.copy()
    if confirmation:
        from confirmation_tester_cohort import (
            CONFIRMATION_PROFILE_SHA256, CONFIRMATION_TESTER_BYTES, CONFIRMATION_TESTER_SHA256,
        )

        packages['tester'] = (PACKAGES['tester'][0], CONFIRMATION_TESTER_BYTES, CONFIRMATION_TESTER_SHA256)
        readiness.update(tester=CONFIRMATION_TESTER_SHA256, profile=CONFIRMATION_PROFILE_SHA256)
    elif carrier_protocol == 'v2':
        readiness.update(tester='715a0ee1c7db1c26c72865923f6f1a16e74db78065a774e27289721aa879af72',
                         profile='a26688148b671a8b47246d18a006b93a8cd28281cab4a11eddb49ac3b383b760')
    return packages, readiness


def controller_artifact(carrier_protocol='v1'):
    carrier_installer_pin(carrier_protocol)
    if carrier_protocol == 'v2':
        return 724152, 'e9cbc1012b4d3afe734f0c050de6c4c1c43b17253e83bb6206e99f4c2d65f891'
    return 746760, '803691c55ac876a42d57488a1c10d76328aa33c3a4ff6cf3606d16f8d201d125'


STAT_FORMAT = '%f|%a|%u|%g|%h|%s|%d|%i|%Y|%Z'
LIMIT = 65536
HEX = re.compile(r'[0-9a-f]{64}\Z')


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def timeout(sock, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('Read-only observation deadline expired')
    sock.settimeout(remaining)


def exact(sock, count, deadline):
    result = bytearray()
    while len(result) < count:
        timeout(sock, deadline)
        part = sock.recv(count - len(result))
        if not part:
            raise EOFError('Incomplete ADB reply')
        result.extend(part)
    return bytes(result)


def service(sock, name, deadline):
    message = name.encode('ascii')
    require(0 < len(message) <= 16384, 'ADB service name exceeds bound')
    timeout(sock, deadline)
    sock.sendall(f'{len(message):04x}'.encode('ascii') + message)
    require(exact(sock, 4, deadline) == b'OKAY', 'Existing ADB service refused')


def shell_script(sock, command, deadline):
    """Keep A_OPEN within the legacy limit without consuming later stdin bytes."""
    name = 'shell,raw,v2:'
    source = command.encode('ascii')
    require(0 < len(source) <= 16384 and b'\0' not in source, 'Invalid fixed shell source')
    if len(name) + len(source) + 1 <= 4096:
        service(sock, name + command, deadline)
        return
    digest = hashlib.sha256(source).hexdigest()
    loader = f"""export LC_ALL=C
set -o pipefail || exit 2
tb=/system/bin/toybox
script=$("$tb" dd bs=4096 iflag=count_bytes count={len(source)} status=none && printf '.') || exit 2
[ "${{#script}}" -eq {len(source) + 1} ] || exit 2
script=${{script%.}}
digest=$(printf '%s' "$script" | "$tb" sha256sum) || exit 2
[ "${{digest%% *}}" = '{digest}' ] || exit 2
exec /system/bin/sh -c "$script"
"""
    require(len(name) + len(loader) + 1 <= 4096, 'Fixed shell loader exceeds A_OPEN limit')
    service(sock, name + loader, deadline)
    timeout(sock, deadline)
    sock.sendall(struct.pack('<BI', 0, len(source)) + source)


def online_devices(raw):
    found = []
    for line in raw.splitlines():
        serial, separator, state = line.partition(b'\t')
        require(separator and re.fullmatch(rb'[A-Za-z0-9_.:%\[\]-]{1,160}', serial) and state,
                'Unexpected ADB device row')
        if state == b'device':
            found.append(serial.decode('ascii'))
    require(len(found) == len(set(found)), 'Duplicate ADB device entry')
    return found


def devices():
    deadline = time.monotonic() + 5
    with socket.create_connection(ENDPOINT, timeout=5) as sock:
        service(sock, 'host:devices', deadline)
        length = exact(sock, 4, deadline)
        require(re.fullmatch(rb'[0-9a-fA-F]{4}', length), 'Invalid ADB device-list length')
        count = int(length, 16)
        require(count <= 16384, 'ADB device list exceeds bound')
        return online_devices(exact(sock, count, deadline))


def shell_reply(sock, deadline):
    stdout, stderr = bytearray(), bytearray()
    total = 0
    while total < LIMIT:
        kind, length = struct.unpack('<BI', exact(sock, 5, deadline))
        require(length <= LIMIT - total - 5, 'Read-only shell output exceeds bound')
        total += 5 + length
        data = exact(sock, length, deadline)
        if kind == 3:
            require(length == 1, 'Invalid shell-v2 exit packet')
            timeout(sock, deadline)
            require(sock.recv(1) == b'', 'Unexpected bytes after remote shell exit')
            return data[0], bytes(stdout), bytes(stderr)
        require(kind in (1, 2), 'Unexpected read-only shell packet type')
        (stdout if kind == 1 else stderr).extend(data)
    raise ValueError('Missing remote shell exit')


def shell(serial, command):
    deadline = time.monotonic() + 20
    with socket.create_connection(ENDPOINT, timeout=5) as sock:
        service(sock, 'host:transport:' + serial, deadline)
        shell_script(sock, command, deadline)
        status, stdout, stderr = shell_reply(sock, deadline)
    require(status == 0 and not stderr and stdout.isascii() and b'\0' not in stdout,
            'Read-only shell observation refused or incomplete')
    return stdout.decode('ascii').splitlines()


IDENTITY = ('set -e; /system/bin/getprop ro.product.model; /system/bin/getprop ro.build.display.id; '
            '/system/bin/getprop ro.build.fingerprint; /system/bin/getprop ro.build.version.sdk; '
            '/system/bin/toybox uname -r; /system/bin/toybox id -u; /system/bin/toybox id -ru; '
            '/system/bin/toybox id -g; /system/bin/toybox id -rg; /system/bin/getenforce; '
            '/system/bin/toybox cat /proc/sys/kernel/random/boot_id; '
            '/system/bin/toybox readlink /proc/$$/ns/mnt')


def inventory_command(identity, *, carrier_protocol='v1', confirmation=False):
    # Identity is a quoted comparison value. All sampled paths and sizes are
    # fixed, and path and digest observations are reduced before receipt output.
    expected = shlex.quote('\n'.join(identity))
    commands = [f"""
export LC_ALL=C
set -f
expected_identity={expected}
check_identity() {{
    observed_identity=$({IDENTITY})
    [ "$?" -eq 0 ] && [ "$observed_identity" = "$expected_identity" ] || exit 2
    printf 'inventory_identity|%s\\n' "$1"
}}
check_identity begin
metadata() {{ /system/bin/toybox stat -c '{STAT_FORMAT}' "$1"; }}
observe() {{
    row=$(metadata "$2" 2>&1)
    if [ "$?" -eq 0 ]; then printf 'path|%s|present|%s\\n' "$1" "$row"
    else case "$row" in *'No such file or directory') printf 'path|%s|absent\\n' "$1";;
        *) printf 'path|%s|unobserved\\n' "$1";; esac
    fi
}}
file_digest() {{
    before=$(metadata "$1" 2>/dev/null) || {{ printf unobserved; return; }}
    info=$(/system/bin/toybox stat -c '%F|%h|%s' "$1" 2>/dev/null) || {{ printf unobserved; return; }}
    if [ "$info" != "regular file|1|$2" ]; then printf unexpected_object; return; fi
    digest=$(/system/bin/toybox sha256sum "$1" 2>/dev/null) || digest=unobserved
    after=$(metadata "$1" 2>/dev/null) || after=invalid
    if [ "$before" != "$after" ]; then digest=unobserved; fi
    printf '%s' "${{digest%% *}}"
}}
measure() {{
    value=$(file_digest "$2" "$3") || value=unobserved
    printf 'hash|%s|%s\\n' "$1" "$value"
}}
package() {{
    role=$1; name=$2; bytes=$3
    listed=$(/system/bin/cmd package list packages --user 0 "$name" 2>&1) || {{
        printf 'hash|%s|unobserved\\n' "$role"; return; }}
    if [ -z "$listed" ]; then
        known=$(/system/bin/cmd package list packages -a -u --user all "$name" 2>&1) || {{
            printf 'hash|%s|unobserved\\n' "$role"; return; }}
        case "$known" in
            '') printf 'hash|%s|not_listed_any_user\\n' "$role";;
            "package:$name") printf 'hash|%s|known_outside_user0_or_retained\\n' "$role";;
            *) printf 'hash|%s|unobserved\\n' "$role";;
        esac
        return
    fi
    [ "$listed" = "package:$name" ] || {{ printf 'hash|%s|unobserved\\n' "$role"; return; }}
    enabled=$(/system/bin/cmd package list packages -e --user 0 "$name" 2>&1) || {{
        printf 'hash|%s|unobserved\\n' "$role"; return; }}
    case "$enabled" in
        '') printf 'hash|%s|disabled_user0\\n' "$role"; return;;
        "package:$name") :;;
        *) printf 'hash|%s|unobserved\\n' "$role"; return;;
    esac
    source=$(/system/bin/cmd package path --user 0 "$name" 2>&1) || {{
        printf 'hash|%s|unobserved\\n' "$role"; return; }}
    case "$source" in
        *[!a-zA-Z0-9_:./=~-]*|*'/./'*|*'/../'*|*'//'*)
            printf 'hash|%s|unexpected_object\\n' "$role"; return;;
        package:/data/app/*/base.apk) :;;
        *) printf 'hash|%s|unexpected_object\\n' "$role"; return;;
    esac
    value=$(file_digest "${{source#package:}}" "$bytes") || value=unobserved
    current=$(/system/bin/cmd package path --user 0 "$name" 2>&1) || current=invalid
    enabled=$(/system/bin/cmd package list packages -e --user 0 "$name" 2>&1) || enabled=invalid
    if [ "$current" != "$source" ] || [ "$enabled" != "package:$name" ]; then value=unobserved; fi
    printf 'hash|%s|%s\\n' "$role" "$value"
}}
/system/bin/toybox stat -f -c 'space|%a|%s|%t' /data 2>/dev/null || printf 'space|unobserved\\n'
source=unobserved
nested=0
drop_mounts=0
parent_mounts=0
while IFS= read -r row; do
    set -- $row
    [ "$#" -ge 10 ] || exit 2
    case "$5" in
        /data)
            options=$6
            shift 6
            while [ "$#" -gt 0 ] && [ "$1" != '-' ]; do shift; done
            [ "$#" -eq 4 ] || exit 2
            source=$3
            printf 'data_mount|%s|%s|%s|%s\\n' "$options" "$2" "$source" "$4";;
        {STAGE}|{STAGE}/*|{GUARD}|{GUARD}/*) nested=$((nested+1));;
        {DROP_PARENT}|{DEPLOY_DROP}|{DEPLOY_DROP}/*) drop_mounts=$((drop_mounts+1));;
        /data/local/tmp|/data/system|{PROFILE}|{HOST_PERMIT_DIR}|{HOST_PERMIT}) parent_mounts=$((parent_mounts+1));;
    esac
done < /proc/$$/mountinfo || exit 2
printf 'nested_mounts|%s\\n' "$nested"
printf 'drop_mounts|%s\\n' "$drop_mounts"
printf 'parent_mounts|%s\\n' "$parent_mounts"
case "$source" in /dev/block/dm-[0-9]*)
    row=$(/system/bin/toybox cat "/sys/fs/f2fs/${{source##*/}}/features" 2>/dev/null) || row=unobserved
    printf 'features|%s|%s\\n' "$source" "$row";;
    *) printf 'features|unobserved\\n';;
esac
"""]
    commands.extend(f'observe {key} {shlex.quote(path)}' for key, path in PATHS.items())
    packages, _ = readiness_artifacts(carrier_protocol, confirmation=confirmation)
    controller_bytes, _ = controller_artifact(carrier_protocol)
    commands.extend(f'package {role} {name} {size}' for role, (name, size, _) in packages.items())
    commands.append(f'measure profile {shlex.quote(PROFILE)} 288')
    commands.append(f'measure host_permit {shlex.quote(HOST_PERMIT)} {len(HOST_PERMIT_MARKER)}')
    commands.append(f'measure controller {shlex.quote(PATHS["controller"])} {controller_bytes}')
    commands.extend(f'measure {role} {shlex.quote(path)} {size}'
                    for role, (path, size, _) in drop_artifacts(carrier_protocol).items())
    commands.append('check_identity end')
    return '\n'.join(commands)


def inventory(lines, *, carrier_protocol='v1', confirmation=False):
    paths, path_devices, hashes, facts = {}, {}, {}, {}
    for line in lines:
        kind, key, *cells = line.split('|')
        if kind == 'path':
            require(key in PATHS and key not in paths and cells, 'Unexpected path observation')
            state, *values = cells
            require(state in ('present', 'absent', 'unobserved'), 'Unknown path disposition')
            row = {'state': state}
            if state == 'present':
                require(len(values) == 10 and re.fullmatch(r'[0-9a-f]{1,8}', values[0])
                        and re.fullmatch(r'[0-7]{1,4}', values[1])
                        and all(re.fullmatch(r'[0-9]{1,20}', v) for v in values[2:]),
                        'Unexpected numeric path metadata')
                mode, perms, uid, gid, links, size, device, _, _, _ = values
                names = {stat.S_IFREG: 'regular', stat.S_IFDIR: 'directory', stat.S_IFLNK: 'symlink'}
                row.update(type=names.get(stat.S_IFMT(int(mode, 16)), 'other'), mode=f'{int(perms, 8):04o}',
                           uid=int(uid), gid=int(gid), links=int(links), bytes=int(size))
                path_devices[key] = device
            else:
                require(not values, 'Unexpected path metadata after refusal')
            paths[key] = row
        elif kind == 'hash':
            require(key not in hashes and len(cells) == 1, 'Duplicate or malformed digest observation')
            hashes[key] = cells[0]
        else:
            require(kind in ('space', 'data_mount', 'nested_mounts', 'drop_mounts', 'parent_mounts', 'features')
                    and kind not in facts,
                    'Unexpected or ambiguous filesystem observation')
            facts[kind] = [key, *cells]
    packages, readiness = readiness_artifacts(carrier_protocol, confirmation=confirmation)
    _, controller_sha = controller_artifact(carrier_protocol)
    expected = {role: pin for role, (_, _, pin) in packages.items()}
    expected.update({role: pin for role, (_, _, pin) in drop_artifacts(carrier_protocol).items()})
    expected.update(profile=readiness['profile'] if confirmation else
                    '74e8623be20ffba5106c4e3e756f1f4958c39cd3658c6b0346da74766df97b36',
                    controller=controller_sha,
                    host_permit=HOST_PERMIT_SHA)
    require(paths.keys() == PATHS.keys() and hashes.keys() == expected.keys()
            and facts.keys() == {'space', 'data_mount', 'nested_mounts', 'drop_mounts', 'parent_mounts', 'features'},
            'Incomplete preflight evidence')
    contents = {}
    for key, value in hashes.items():
        if HEX.fullmatch(value):
            if value == readiness.get(key):
                contents[key] = 'exact_readiness_bytes'
            else:
                contents[key] = 'exact_bytes' if value == expected[key] else 'different_bytes'
        else:
            dispositions = ('absent', 'unobserved', 'unexpected_object')
            if key in packages:
                dispositions += ('not_listed_any_user', 'known_outside_user0_or_retained', 'disabled_user0')
            require(value in dispositions, 'Invalid digest observation')
            contents[key] = value
    space = facts['space']
    require(len(space) == 3 and space[2].lower() == 'f2f52010'
            and all(re.fullmatch(r'[0-9]{1,20}', v) for v in space[:2]), 'Missing F2FS size')
    available = int(space[0]) * int(space[1])
    mount = facts['data_mount']
    require(len(mount) == 4 and mount[1] == 'f2fs' and re.fullmatch(r'/dev/block/dm-[0-9]+', mount[2]),
            'Unexpected current /data mount')
    nested, drop_mounts, parent_mounts = (facts[key] for key in ('nested_mounts', 'drop_mounts', 'parent_mounts'))
    require(all(len(value) == 1 and re.fullmatch(r'[0-9]{1,8}', value[0])
                for value in (nested, drop_mounts, parent_mounts)), 'Invalid nested mount count')
    feature = facts['features']
    require(feature == ['unobserved'] or len(feature) == 2 and feature[0] == mount[2],
            'Filesystem feature observation does not match the current mount')
    options = tuple(set(field.split(',')) for field in (mount[0], mount[3]))
    writable = all(flags & {'rw', 'ro'} == {'rw'} for flags in options)
    data, local = paths['data'], paths['local']
    protected = (writable and data.get('type') == 'directory' and data.get('mode') == '0771'
                 and data.get('uid') == data.get('gid') == 1000
                 and local.get('type') == 'directory' and local.get('mode') == '0751'
                 and local.get('uid') == local.get('gid') == 0 and 'data' in path_devices
                 and path_devices.get('local') == path_devices['data'] and int(drop_mounts[0]) == 0)
    return {'paths': paths, 'contents': contents, 'availableDataBytes': available,
            'imageAndHeadroomAvailable': available >= MIN_FREE, 'nestedIsolatedMounts': int(nested[0]),
            'protectedDropParentObserved': protected, 'nestedDropMounts': int(drop_mounts[0]),
            'stageParentsOnData': 'data' in path_devices
            and all(path_devices.get(key) == path_devices['data'] for key in ('tmp', 'system'))
            and all(key not in path_devices or path_devices[key] == path_devices['data']
                    for key in ('profile', 'host_permit_dir', 'host_permit'))
            and int(parent_mounts[0]) == 0,
            'dataWritableF2fs': writable, 'dataExecutableF2fs': all('noexec' not in flags for flags in options),
            'sameDataDeviceAdvertisesVerity': len(feature) == 2
            and 'verity' in [v.strip() for v in feature[1].split(',')]}


def observe(*, carrier_protocol='v1'):
    carrier_installer_pin(carrier_protocol)
    result = {'carrierProtocol': 'v2'} if carrier_protocol == 'v2' else {}
    available = devices()
    if len(available) != 1:
        return result | {'status': 'READ_ONLY_WAIT_FOR_UNIQUE_PAIRED_TRANSPORT', 'onlineCount': len(available)}
    serial = available[0]
    identity = shell(serial, IDENTITY)
    require(len(identity) == 12, 'Unexpected target identity fields')
    model, build, fingerprint, sdk, kernel, uid, real_uid, gid, real_gid, enforcing, boot, namespace = identity
    if (model, build, fingerprint, sdk) != (MODEL, BUILD, FINGERPRINT, '37') \
            or not kernel.startswith('6.12.69-android16-6-'):
        return result | {'status': 'READ_ONLY_TARGET_PROFILE_MISMATCH'}
    require(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', boot)
            and re.fullmatch(r'mnt:\[[1-9][0-9]{0,19}\]', namespace), 'Invalid read-only boot or mount identity')
    result.update(model=model, build=build, fingerprint=fingerprint, api=37,
                  rootShellObserved=uid == real_uid == gid == real_gid == '0',
                  enforcingObserved=enforcing == 'Enforcing')
    if not result['rootShellObserved']:
        return result | {'status': 'READ_ONLY_CURRENT_ROOT_UNAVAILABLE'}
    lines = shell(serial, inventory_command(identity, carrier_protocol=carrier_protocol))
    require(len(lines) >= 2 and lines[0] == 'inventory_identity|begin'
            and lines[-1] == 'inventory_identity|end', 'Inventory shell identity boundaries missing')
    data = inventory(lines[1:-1], carrier_protocol=carrier_protocol)
    return result | data | {'status': 'READ_ONLY_PREFLIGHT_REVIEW_REQUIRED',
                            'inventoryIdentityBound': True,
                            'actualLiveFrameworkHostActivation': 'unverified'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--carrier-protocol', choices=('v1', 'v2'), default='v1')
    args = parser.parse_args(argv)
    try:
        result = observe(carrier_protocol=args.carrier_protocol)
    except (OSError, EOFError, ValueError) as exc:
        # Socket and device paths may contain local identifiers. Only fixed
        # authored refusal messages enter the receipt.
        result = {'status': 'READ_ONLY_PREFLIGHT_HELD',
                  'reason': str(exc) if type(exc) is ValueError else type(exc).__name__}
        if args.carrier_protocol == 'v2':
            result['carrierProtocol'] = 'v2'
    result.update(schema=SCHEMA, deviceEligible=False,
                  observedUtc=datetime.now(timezone.utc).isoformat(timespec='seconds'))
    require(OUT.resolve() == OUT, 'Noncanonical preflight output directory')
    OUT.mkdir(exist_ok=True)
    job = OUT / f'r-{uuid.uuid4().hex[:8]}'
    job.mkdir()
    receipt = job / 'receipt.json'
    with receipt.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(result['status'], receipt)
    return 0 if result['status'] == 'READ_ONLY_PREFLIGHT_REVIEW_REQUIRED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
