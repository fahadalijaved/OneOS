"""Read the reviewed, saved V2 stage-only evidence without contacting a device."""

import argparse
import json
from pathlib import Path
import re

from check_file_stage_device_preflight import BUILD, FINGERPRINT, MODEL, PATHS, SCHEMA, drop_artifacts, require
from check_file_stage_local_cohort import verify_local_cohort
from guest_tree_shell_v2_transfer import READBACK_PREFIX, parse_publication_witness, verify_carrier_readback
from review_file_stage_sequence import parse_bound_bootstrap
from run_guest_tree_install_transport import load_io, pinned, selected_source_receipt, sha


STAGED_JOB = 'out/file-stage-live-staging/r-d3a9b960'
_PINS = {
    'initial-preflight.json': 'c378481c17d633515d8748dcb62147006d36dbd229c71f615e904607bd6bab60',
    'sequence-review.json': 'ba9da9cfe11ebbe828b6754c0323b0d954f408e65ad06aeb5c4b84e4905c4abf',
    'bound-pre-grant-readback.json': '5a78a5bd52b08fc33607a1dadbc4728ffc52994c9eaa783d204ac64a8473c7f6',
    'drop-transport.json': '3d8d30550747419cc1d412ae7aceea98024e8ff6e3aa2fdf41435c0d2a1dedec',
    'drop-readback.json': 'cb08dd9e99de98151a57d723144e760a922259984761b19ffa0c45af87ca65f6',
    'bootstrap-terminal.json': 'c038a4b31e46f34b6ff6512269c1c1e73f6ad058f40d7d27d6645069caf62574',
    'bootstrap-witness.json': '6485da82c10516bbd5d7cde29eb54b9be837eaeb8c034d9d349382e78ef30c54',
    'stage-readback.json': '49d6e1125b7fe9eaa86e7c57100c284fb5a7636b96f9b2465bf00a2c2235ce3a',
    'feed/source-receipt.json': '1e0ec2749bb3cd7107e68d0a53a497fd249b89d4b8bfee9f70d98850509b12d2',
    'carrier-transport.json': '834670f39b2287cf40c65b7124d6c069d4bf0cf3a588ac11fc688512639cd53a',
    'carrier-publication-readback.json': '6763ba76d816c2541bff6a04d7f7be501d0d985e419ac21625f27e6701d4f46b',
    'carrier-readback.json': '7cb75137979bb239414c20eca6f0833eb163226146fce8358ee21f19cecc9759',
    'result.json': '08b4cd596420065670768006febf69e52b676ba4e5664764519612595951874a',
}
_DIR_STAT = re.compile(r'41c0\|700\|0\|0\|([1-9][0-9]{0,19})\|([1-9][0-9]{0,19})')
_IMAGE_FIELDS = ('mountId', 'deviceMajor', 'deviceMinor', 'inode', 'bytes',
                 'mtimeSec', 'mtimeNs', 'ctimeSec', 'ctimeNs')


def _matches(record, **expected):
    return all(key in record and type(record[key]) is type(value) and record[key] == value
               for key, value in expected.items())


def _directory_fields(stat, mount):
    match = _DIR_STAT.fullmatch(stat) if type(stat) is str else None
    require(match is not None and type(mount) is int, 'Invalid saved directory witness')
    return (*match.groups(), str(mount))


def _node(paths, role, kind, mode, *, uid=0, gid=0, links, size=None):
    row = paths[role]
    require(_matches(row, state='present', type=kind, mode=mode, uid=uid, gid=gid, links=links)
            and type(row.get('bytes')) is int and row['bytes'] >= 0
            and (size is None or row['bytes'] == size), 'Saved stage object metadata differs')


def _absent(paths, *roles):
    require(all(paths[role] == {'state': 'absent'} for role in roles), 'Expected saved stage absence')


def read_completed_stage(job: Path) -> tuple[dict, dict]:
    """Return the stage and image witnesses as historical review evidence only."""
    io = load_io()
    expected_job = io['ROOT'] / STAGED_JOB
    require(isinstance(job, Path) and job.absolute() == expected_job, 'Expected the exact saved V2 stage job')
    io['checked_path'](expected_job, directory=True)

    def raw(name):
        return pinned(io, f'{STAGED_JOB}/{name}', _PINS[name], 8192)

    records = {name: json.loads(raw(name), object_pairs_hook=io['unique_object'])
               for name in _PINS if name != 'feed/source-receipt.json'}
    require(all(type(row) is dict for row in records.values()), 'Invalid saved stage record')
    result = records['result.json']
    require(_matches(result, status='STAGED_CARRIER_VERIFIED_ONLY', frameworkActivated=False),
            'Saved run did not complete stage-only work')
    cohort = verify_local_cohort(carrier_protocol='v2')
    review = records['sequence-review.json']
    require(_matches(review, status='FRESH_SEQUENCE_FOR_OPERATOR_REVIEW', mayExecute=False,
                     requiresSameGenerationReadbackAfterEachPublication=True, localCohort=cohort)
            and _matches(cohort, status='MATCHED_LOCAL_COHORT_VERIFIED', mayExecute=False, installerProtocol='v2'),
            'Saved review does not match the current corrected cohort')

    initial = records['initial-preflight.json']
    pregrant = records['bound-pre-grant-readback.json']
    drop = records['drop-readback.json']
    stage = records['stage-readback.json']
    final = records['carrier-readback.json']
    require(_matches(initial, schema=SCHEMA, status='READ_ONLY_PREFLIGHT_REVIEW_REQUIRED', carrierProtocol='v2',
                     model=MODEL, build=BUILD, fingerprint=FINGERPRINT, api=37, rootShellObserved=True,
                     enforcingObserved=True, inventoryIdentityBound=True, deviceEligible=False,
                     actualLiveFrameworkHostActivation='unverified'), 'Saved preflight differs from the fixed profile')
    for observation in (initial, pregrant, drop, stage, final):
        require(observation['paths'].keys() == PATHS.keys()
                and _matches(observation, nestedIsolatedMounts=0, nestedDropMounts=0, stageParentsOnData=True)
                and _matches(observation['contents'], host='not_listed_any_user', tester='not_listed_any_user',
                             profile='unobserved', host_permit='exact_bytes'),
                'Saved stage observations include unexpected mounts, packages or profile')
        _absent(observation['paths'], 'profile', 'stage_tmp', 'guard_tmp', 'carrier_tmp', 'controller_tmp',
                'writer_blocked', 'legacy_blocked', 'view_blocked')
    require(initial['paths'] == pregrant['paths'], 'Saved pre-grant paths differ')
    for observation in (initial, pregrant):
        _absent(observation['paths'], 'stage', 'guard', 'carrier', 'controller',
                'deploy_drop', 'deploy_installer', 'deploy_publisher')

    drops = drop_artifacts('v2')
    drop_total = sum(row[1] for row in drops.values())
    require(_matches(records['drop-transport.json'], status='COMPLETE_PROTECTED_DROP_TRANSPORT_ONLY', failure=None,
                     installerSha256=cohort['installerSha256'], publisherSha256=cohort['publisherSha256'],
                     expectedPayloadBytes=drop_total, stdinPayloadBytesSent=drop_total, pendingWireKind=None,
                     pendingWireBytesSent=0, closeStdinSent=True, remoteExit=0, remoteEof=True,
                     remoteStderrBytes=0, publisherOrCleanupCredit=False), 'Saved protected-drop terminal is incomplete')
    for observation in (drop, stage, final):
        require(_matches(observation['contents'], deploy_installer='exact_bytes', deploy_publisher='exact_bytes')
                and all(observation['paths'][role] == drop['paths'][role] for role in (*drops, 'deploy_drop')),
                'Saved protected-drop readbacks differ')
        _node(observation['paths'], 'deploy_drop', 'directory', '0700', links=2)
        for role, (_, size, _) in drops.items():
            _node(observation['paths'], role, 'regular', '0500', links=1, size=size)
    _absent(drop['paths'], 'stage', 'guard', 'carrier', 'controller')
    _absent(stage['paths'], 'carrier', 'controller')
    for role, links in (('stage', 5), ('bin', 2), ('backing', 2), ('private_user', 3),
                        ('private_user0', 2), ('private_alias', 2), ('guard', 2)):
        _node(stage['paths'], role, 'directory', '0700', links=links)
    _node(stage['paths'], 'private_data', 'directory', '0771', uid=1000, gid=1000, links=4)
    _node(stage['paths'], 'lease', 'regular', '0600', links=1, size=0)
    require(all(stage['paths'][role] == final['paths'][role] for role in PATHS if role not in ('carrier', 'controller')),
            'Saved stage layout differs after carrier publication')
    _node(final['paths'], 'controller', 'regular', '0500', links=1, size=724152)
    require(_matches(final['contents'], controller='exact_bytes'), 'Saved controller readback is incomplete')

    bootstrap = records['bootstrap-witness.json']
    stage_fields = _directory_fields(bootstrap.get('stageStat'), bootstrap.get('stageMount'))
    guard_fields = _directory_fields(bootstrap.get('guardStat'), bootstrap.get('guardMount'))
    frame = ('ONEOS_STAGE_V2 PUBLISHED_CLOSED ' + ' '.join((*stage_fields, *guard_fields)) + '\n').encode('ascii')
    terminal = records['bootstrap-terminal.json']
    require(_matches(terminal, exitCode=0, stdoutSha256=sha(frame), stderrBytes=0, remoteEof=True)
            and parse_bound_bootstrap(terminal['exitCode'], frame, b'', eof=terminal['remoteEof']) == bootstrap,
            'Saved bootstrap terminal or typed witness differs')

    size = cohort['carrier']['imageBytes']
    _node(final['paths'], 'carrier', 'regular', '0600', links=1, size=size)
    source = raw('feed/source-receipt.json')
    require(source == selected_source_receipt(), 'Saved producer source receipt differs')
    transfer = records['carrier-transport.json']
    require(_matches(transfer, status='COMPLETE_SHELL_V2_TRANSFER_ONLY', failure=None, producerExit=0,
                     producerStdoutEof=True, producerBytesObserved=size, producerStderrBytes=0,
                     sourceReceiptSha256=sha(source), expectedBytes=size, stdinPayloadBytesSent=size,
                     pendingWireKind=None, pendingWireBytesSent=0, tailSent=True, closeStdinSent=True,
                     remoteExit=0, remoteEof=True, unparsedRemoteBytes=0, publisherOrCleanupCredit=False),
            'Saved producer or carrier terminal is incomplete')
    encoded = transfer.get('remoteStdoutHex')
    require(type(encoded) is str and re.fullmatch(r'[0-9a-f]{2,446}', encoded) is not None
            and len(encoded) % 2 == 0, 'Invalid saved publication frame encoding')
    publication = parse_publication_witness(bytes.fromhex(encoded), size)
    require(_matches(transfer, publicationWitness=publication)
            and all(type(v) is int for v in transfer['publicationWitness'].values()), 'Saved publication witness differs')
    image = records['carrier-publication-readback.json']
    require(image.keys() == set(_IMAGE_FIELDS) and all(type(v) is int for v in image.values()),
            'Invalid saved independent carrier readback')
    # The coordinator saved the parsed result of its separate verified readback shell.
    readback_frame = READBACK_PREFIX + (' '.join(str(image[key]) for key in _IMAGE_FIELDS) + '\n').encode('ascii')
    require(verify_carrier_readback(readback_frame, publication, size) == image, 'Saved carrier readback differs')
    dev, inode = map(int, stage_fields[:2])
    major = ((dev >> 8) & 0xfff) | ((dev >> 32) & ~0xfff)
    minor = (dev & 0xff) | ((dev >> 12) & ~0xff)
    require(image['mountId'] == bootstrap['stageMount'] and image['inode'] != inode
            and (image['deviceMajor'], image['deviceMinor']) == (major, minor),
            'Saved carrier identity is outside the bootstrapped stage device and mount')
    return bootstrap, image


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('job', type=Path)
    read_completed_stage(cli.parse_args().job)
    print(json.dumps({'status': 'SAVED_STAGE_ONLY_EVIDENCE_VERIFIED', 'mayExecute': False}))
