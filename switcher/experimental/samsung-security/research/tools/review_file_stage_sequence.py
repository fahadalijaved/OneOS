"""Review the fixed fresh Prepare/Stop cohort from an existing preflight receipt."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re

from check_file_stage_device_preflight import (
    BUILD, DROP_ARTIFACTS, FINGERPRINT, HOST_PERMIT_MARKER, MIN_FREE, MODEL, OUT, PATHS, SCHEMA,
    controller_artifact, drop_artifacts, require,
)
from check_file_stage_local_cohort import verify_local_cohort
from run_guest_tree_install_transport import carrier_installer_pin, load_io
from stream_guest_tree_install_feed import IMAGE_BYTES


@dataclass(frozen=True)
class NativeStep:
    artifact: str
    verb: str
    prefix: bytes


BOOTSTRAP = NativeStep('installer', '--bootstrap-empty-stage', b'ONEOS_STAGE_V1')
CONTROLLER = NativeStep('installer', '--install-preparation-controller', b'ONEOS_CONTROLLER_V1')
CARRIER = NativeStep('installer', '--install-verified-carrier', b'ONEOS_CARRIER_V1')
PROFILE = NativeStep('publisher', '--publish-verified-host-profile', b'ONEOS_PROFILE_V1')
NATIVE_STEPS = (BOOTSTRAP, CONTROLLER, CARRIER, PROFILE)
ROOTS = {'data', 'local', 'tmp', 'system', 'dev'}
HOST_SLOTS = {'profile', 'host_permit_dir', 'host_permit'}
CONTENT_ROLES = DROP_ARTIFACTS.keys() | {'profile', 'host_permit', 'controller', 'host', 'tester'}
PREFLIGHT_MAX_AGE = timedelta(minutes=2)
_BOOTSTRAP_WITNESS = re.compile(rb'ONEOS_STAGE_V2 PUBLISHED_CLOSED '
                                + rb' '.join([rb'([1-9][0-9]{0,19})'] * 6) + rb'\n')


def native_terminal(step, status, stdout, stderr, eof):
    """Classify the complete captured transport result, without granting progress."""
    if not any(step is candidate for candidate in NATIVE_STEPS):
        raise ValueError('Unknown fixed stage step')
    if (type(status) is not int or eof is not True or type(stdout) is not bytes
            or type(stderr) is not bytes or stderr != b''):
        return 'UNCONFIRMED'
    prefix = step.prefix + b' '
    if status == 0:
        if stdout == prefix + b'PUBLISHED_CLOSED\n':
            return 'PUBLISHED_REQUIRES_READBACK'
        if step is PROFILE and stdout == prefix + b'MATCHED_LOCAL_CLOSED\n':
            return 'UNEXPECTED_EXISTING_PROFILE_REQUIRES_REVIEW'
    if status == 2 and stdout == prefix + b'REFUSED_LOCAL_CLOSED\n':
        return 'REFUSED_REQUIRES_READBACK'
    if status == 3 and stdout == prefix + b'HOLD\n':
        return 'HOLD'
    return 'UNCONFIRMED'


def parse_bound_bootstrap(code, stdout, stderr, *, eof):
    """Parse a successful V2 bootstrap witness for the same-target readback."""
    if (type(code) is not int or code != 0 or type(stdout) is not bytes or len(stdout) >= 160
            or type(stderr) is not bytes or stderr or eof is not True):
        raise ValueError('Unconfirmed bound bootstrap terminal')
    match = _BOOTSTRAP_WITNESS.fullmatch(stdout)
    if match is None:
        raise ValueError('Invalid bound bootstrap identity frame')
    stage_dev, stage_ino, stage_mount, guard_dev, guard_ino, guard_mount = map(int, match.groups())
    if (any(value >= 2**64 for value in (stage_dev, stage_ino, stage_mount, guard_dev, guard_ino, guard_mount))
            or stage_mount == guard_mount or (stage_dev, stage_ino) == (guard_dev, guard_ino)):
        raise ValueError('Bound bootstrap identities differ from the directory profile')
    return {'stageStat': f'41c0|700|0|0|{stage_dev}|{stage_ino}', 'stageMount': stage_mount,
            'guardStat': f'41c0|700|0|0|{guard_dev}|{guard_ino}', 'guardMount': guard_mount}


def _node(row, kind, mode, uid, gid):
    return type(row.get('uid')) is int and type(row.get('gid')) is int and (
        row.get('state'), row.get('type'), row.get('mode'), row.get('uid'), row.get('gid')) == (
        'present', kind, mode, uid, gid,
    )


def require_stage_only_inventory(observed, *, profile_present=False, tester_present=False) -> None:
    """Validate the identity-bound V2 inventory for the specified publication state."""
    require(type(profile_present) is bool and type(tester_present) is bool
            and (not tester_present or profile_present), 'Invalid stage-only publication state')
    flags = ('protectedDropParentObserved', 'stageParentsOnData',
             'dataWritableF2fs', 'dataExecutableF2fs', 'sameDataDeviceAdvertisesVerity')
    mounts = ('nestedIsolatedMounts', 'nestedDropMounts')
    require(type(observed) is dict and observed.keys() == {
        'paths', 'contents', 'availableDataBytes', 'imageAndHeadroomAvailable', *flags, *mounts,
    }, 'Unexpected stage-only inventory envelope')
    paths, contents, free = (observed[key] for key in ('paths', 'contents', 'availableDataBytes'))
    require(type(paths) is dict and paths.keys() == PATHS.keys() and all(type(row) is dict for row in paths.values())
            and type(contents) is dict and contents.keys() == CONTENT_ROLES, 'Incomplete stage-only inventory')
    require(type(free) is int and free >= 0 and type(observed['imageAndHeadroomAvailable']) is bool
            and all(observed[key] is True for key in flags)
            and all(type(observed[key]) is int and observed[key] == 0 for key in mounts),
            'Stage-only storage or mount evidence refused')

    directories = {
        'data': ('0771', 1000, 1000, None), 'local': ('0751', 0, 0, None), 'tmp': ('0771', 2000, 2000, None),
        'system': ('0775', 1000, 1000, None), 'dev': ('0755', 0, 0, None),
        'stage': ('0700', 0, 0, 5), 'bin': ('0700', 0, 0, 2), 'backing': ('0700', 0, 0, 2),
        'private_data': ('0771', 1000, 1000, 4), 'private_user': ('0700', 0, 0, 3),
        'private_user0': ('0700', 0, 0, 2), 'private_alias': ('0700', 0, 0, 2), 'guard': ('0700', 0, 0, 2),
        'host_permit_dir': ('0750', 0, 1000, None), 'deploy_drop': ('0700', 0, 0, 2),
    }
    files = {'lease': ('0600', 0, 0), 'carrier': ('0600', 0, IMAGE_BYTES),
             'controller': ('0500', 0, controller_artifact('v2')[0]),
             'host_permit': ('0440', 1000, len(HOST_PERMIT_MARKER))}
    if profile_present:
        files['profile'] = ('0440', 1000, 288)
    files.update({role: ('0500', 0, size) for role, (_, size, _) in drop_artifacts('v2').items()})
    for role in directories.keys() | files.keys():
        row = paths[role]
        require(row.keys() == {'state', 'type', 'mode', 'uid', 'gid', 'links', 'bytes'}
                and type(row['links']) is int and type(row['bytes']) is int,
                f'Malformed stage-only metadata: {role}')
    for role, (mode, uid, gid, links) in directories.items():
        row = paths[role]
        require(_node(row, 'directory', mode, uid, gid) and row['bytes'] >= 0 and row['links'] >= 2
                and (links is None or row['links'] == links), f'Unexpected stage-only directory: {role}')
    for role, (mode, gid, size) in files.items():
        row = paths[role]
        require(_node(row, 'regular', mode, 0, gid) and row['links'] == 1 and row['bytes'] == size,
                f'Unexpected stage-only file: {role}')
    require(all(paths[role] == {'state': 'absent'} for role in PATHS.keys() - directories.keys() - files.keys()),
            'Unexpected stage-only profile, temporary path or blocker')
    expected_contents = {
        'tester': 'exact_readiness_bytes' if tester_present else 'not_listed_any_user',
        'host': 'not_listed_any_user',
        'profile': 'exact_readiness_bytes' if profile_present else 'unobserved',
        'host_permit': 'exact_bytes', 'controller': 'exact_bytes',
        'deploy_installer': 'exact_bytes', 'deploy_publisher': 'exact_bytes',
    }
    require(contents == expected_contents, 'Stage-only artifact, permit or package evidence refused')


def _fresh_utc(value):
    if type(value) is not str or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00', value):
        return False
    try:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(value)
    except ValueError:
        return False
    return timedelta(0) <= age <= PREFLIGHT_MAX_AGE


def review(preflight, *, carrier_protocol='v1'):
    carrier_installer_pin(carrier_protocol)
    result = {'status': 'HELD', 'mayExecute': False, 'orderedSteps': []}
    if preflight.get('schema') != SCHEMA or preflight.get('deviceEligible') is not False:
        return result | {'reason': 'FRESH_PREFLIGHT_SCHEMA_REQUIRED'}
    if preflight.get('carrierProtocol', 'v1') != carrier_protocol:
        return result | {'reason': 'CARRIER_PREFLIGHT_PROTOCOL_MISMATCH'}
    if preflight.get('status') == 'READ_ONLY_WAIT_FOR_UNIQUE_PAIRED_TRANSPORT':
        return result | {'reason': 'WAIT_FOR_UNIQUE_PAIRED_TRANSPORT'}
    if (preflight.get('status'), preflight.get('model'), preflight.get('build'),
            preflight.get('fingerprint'), preflight.get('api')) != (
            'READ_ONLY_PREFLIGHT_REVIEW_REQUIRED', MODEL, BUILD, FINGERPRINT, 37):
        return result | {'reason': 'EXACT_TARGET_PROFILE_REQUIRED'}
    if type(preflight['api']) is not int or preflight.get('actualLiveFrameworkHostActivation') != 'unverified':
        return result | {'reason': 'UNEXPECTED_OBSERVATION_ENVELOPE'}
    if preflight.get('inventoryIdentityBound') is not True:
        return result | {'reason': 'INVENTORY_SHELL_IDENTITY_UNPROVEN'}
    if not _fresh_utc(preflight.get('observedUtc')):
        return result | {'reason': 'CURRENT_PREFLIGHT_TIMESTAMP_REQUIRED'}
    flags = ('rootShellObserved', 'enforcingObserved', 'imageAndHeadroomAvailable',
             'protectedDropParentObserved', 'dataWritableF2fs', 'dataExecutableF2fs',
             'stageParentsOnData', 'sameDataDeviceAdvertisesVerity')
    free = preflight.get('availableDataBytes')
    if (any(preflight.get(name) is not True for name in flags) or type(free) is not int or free < MIN_FREE
            or any(type(preflight.get(k)) is not int or preflight[k] != 0
                   for k in ('nestedIsolatedMounts', 'nestedDropMounts'))):
        return result | {'reason': 'ROOT_STORAGE_OR_MOUNT_PRECONDITION_UNPROVEN'}
    paths, contents = preflight.get('paths'), preflight.get('contents')
    if (type(paths) is not dict or paths.keys() != PATHS.keys()
            or any(type(row) is not dict for row in paths.values()) or type(contents) is not dict
            or contents.keys() != CONTENT_ROLES):
        return result | {'reason': 'INCOMPLETE_STAGE_OBSERVATION'}
    if (not _node(paths['data'], 'directory', '0771', 1000, 1000)
            or not _node(paths['local'], 'directory', '0751', 0, 0)
            or not _node(paths['tmp'], 'directory', '0771', 2000, 2000)
            or not _node(paths['system'], 'directory', '0775', 1000, 1000)
            or not _node(paths['dev'], 'directory', '0755', 0, 0)):
        return result | {'reason': 'UNEXPECTED_STAGE_PARENT_PROFILE'}
    if (any(paths[name] != {'state': 'absent'} for name in paths.keys() - ROOTS - HOST_SLOTS)
            or any(contents.get(name) != 'unobserved' for name in ('deploy_installer', 'deploy_publisher', 'controller'))):
        return result | {'reason': 'FRESH_STAGE_AND_DROP_NOT_PROVEN'}

    permit_dir, permit = paths['host_permit_dir'], paths['host_permit']
    permit_dir_matches = _node(permit_dir, 'directory', '0750', 0, 1000)
    if (permit == {'state': 'absent'} and contents['host_permit'] == 'unobserved'
            and (permit_dir == {'state': 'absent'} or permit_dir_matches)):
        return result | {'reason': 'HOST_BOOTSTRAP_PERMIT_ABSENT'}
    if (not permit_dir_matches or not _node(permit, 'regular', '0440', 0, 1000)
            or type(permit.get('links')) is not int or permit['links'] != 1
            or type(permit.get('bytes')) is not int or permit['bytes'] != len(HOST_PERMIT_MARKER)
            or contents['host_permit'] != 'exact_bytes'):
        return result | {'reason': 'HOST_BOOTSTRAP_PERMIT_COLLISION_OR_UNKNOWN'}

    profile = paths['profile']
    if profile == {'state': 'absent'} and contents.get('profile') == 'unobserved':
        profile_action = 'publish_profile_after_absence_recheck'
    elif (_node(profile, 'regular', '0440', 0, 1000) and type(profile.get('links')) is int
            and type(profile.get('bytes')) is int and profile['links'] == 1 and profile['bytes'] == 288
            and contents.get('profile') == 'exact_readiness_bytes'):
        profile_action = 'read_back_existing_profile'
    else:
        return result | {'reason': 'PROTECTED_PROFILE_COLLISION_OR_UNKNOWN'}

    packages = []
    for role in ('tester', 'host'):
        match = contents.get(role)
        if match == 'not_listed_any_user':
            packages.append('review_fresh_' + role + '_install')
        elif match == 'exact_readiness_bytes':
            packages.append('read_back_existing_' + role)
        else:
            return result | {'reason': 'PACKAGE_COLLISION_OR_UNKNOWN', 'role': role}
    try:
        cohort = verify_local_cohort(carrier_protocol='v2') if carrier_protocol == 'v2' else verify_local_cohort()
    except (KeyError, OSError, TypeError, ValueError):
        return result | {'reason': 'MATCHED_LOCAL_COHORT_UNVERIFIED'}
    install_steps = ['controller', 'carrier']
    if carrier_protocol == 'v2':
        install_steps = ['bound_controller', 'bound_carrier', 'verify_published_carrier_by_readback']
    return result | {
        'status': 'FRESH_SEQUENCE_FOR_OPERATOR_REVIEW',
        'orderedSteps': ['protected_drop', 'bootstrap', *install_steps, profile_action,
                         *packages, 'read_back_host_bootstrap_permit', 'review_actual_host_activation',
                         'prepare_and_stop'],
        'requiresSameGenerationReadbackAfterEachPublication': True,
        'localCohort': cohort,
    }


def read_preflight(path):
    if (path.absolute() != path.resolve() or path.name != 'receipt.json' or path.parent.parent != OUT
            or not re.fullmatch(r'r-[0-9a-f]{8}', path.parent.name)):
        raise ValueError('Expected an exact saved preflight receipt path')

    io = load_io()
    with io['checked_input'](path, max_size=65536) as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError('Preflight receipt exceeds the limit')
    result = json.loads(raw, object_pairs_hook=io['unique_object'])
    if type(result) is not dict:
        raise ValueError('Expected a preflight receipt object')
    return result


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('receipt', type=Path)
    cli.add_argument('--carrier-protocol', choices=('v1', 'v2'), default='v1')
    args = cli.parse_args()
    print(json.dumps(review(read_preflight(args.receipt.absolute()), carrier_protocol=args.carrier_protocol), indent=2))
