"""Compare a saved native carrier capture with the pinned V2 stage evidence."""

import argparse
import hashlib
import json
from pathlib import PurePosixPath
import re

from check_isolated_stage_readback import device_parts
from file_stage_stop_carrier_capture import decode_stop_carrier_capture
from file_stage_stop_role_screen import decode_stop_role_screen
from file_stage_stop_session_capture import decode_stop_session_capture
from read_staged_file_carrier_receipt import STAGED_JOB, read_completed_stage
from run_guest_tree_install_transport import ROOT, load_io, pinned, selected_source_receipt


def _directory_identity(witness, role):
    # The pinned stage reader has already validated the exact stat format.
    device, inode = map(int, witness[role + 'Stat'].split('|')[-2:])
    return witness[role + 'Mount'], *device_parts(device), inode


def _match_screen_roles(raw, session):
    screen = decode_stop_role_screen(raw)
    native_births = session['processes']['preStop']
    for role in ('controller', 'child'):
        birth = native_births[role]['birth']
        if (screen[role + 'Pid'], screen[role + 'StartTicks']) != (birth['pid'], birth['startTicks']):
            raise ValueError(f'Tester {role} birth differs from the native observation')
    reader = session['identity']['before']['reader']['pid']
    if reader in (screen['appPid'], screen['systemServerPid']):
        raise ValueError('Tester app or SystemServer PID aliases the native reader')


def review(raw, *, relative_path, session=False, screen_raw=None):
    """Check local records only. A match supplies no Stop or execution credit."""
    if screen_raw is not None and not session:
        raise ValueError('Tester role rows require a native V2 session capture')
    if session:
        session_capture = decode_stop_session_capture(raw, saved_relative_path=relative_path)
        if screen_raw is not None:
            _match_screen_roles(screen_raw, session_capture)
        capture = session_capture['carrier']
    else:
        capture = decode_stop_carrier_capture(raw, saved_relative_path=relative_path)
    witness, publication = read_completed_stage(ROOT / STAGED_JOB)
    carrier = capture['after']['carrier']['heldAfter']
    nodes = ('mountId', 'deviceMajor', 'deviceMinor', 'inode')
    actual = {key: carrier['node'][key] for key in nodes}
    actual.update(bytes=carrier['sizeBytes'], mtimeSec=carrier['mtimeSec'], mtimeNs=carrier['mtimeNsec'],
                  ctimeSec=carrier['ctimeSec'], ctimeNs=carrier['ctimeNsec'])
    if actual != publication:
        raise ValueError('Native capture carrier differs from the saved V2 publication')
    digest = json.loads(selected_source_receipt())['fsVerityDigest']
    if any(capture[phase]['measurement']['digestHex'] != digest for phase in ('before', 'after')):
        raise ValueError('Native capture measurement differs from the pinned fs-verity digest')
    backing = capture['physicalRelease']['sample']
    for role in ('stage', 'guard'):
        if tuple(backing[role][key] for key in nodes) != _directory_identity(witness, role):
            raise ValueError(f'Native capture {role} differs from the saved bootstrap directory')
    result = {
        'status': ('SAVED_NATIVE_SESSION_MATCHES_V2_STAGE_ONLY' if session
                   else 'SAVED_NATIVE_CAPTURE_MATCHES_V2_STAGE_ONLY'),
        'captureSha256': capture['closed']['rawRef']['sha256'],
        'mayExecute': False,
        'physicalReleaseAccepted': False,
    }
    if screen_raw is not None:
        result.update(status='SAVED_NATIVE_SESSION_AND_SCREEN_MATCH_STAGE_AND_BIRTHS',
                      screenSha256=hashlib.sha256(screen_raw).hexdigest(),
                      clockJoinVerified=False)
    return result


def _capture_input(cli, path, digest):
    name = PurePosixPath(path)
    base = PurePosixPath('out/file-stage-integrated-stop-evidence')
    if (not name.is_relative_to(base) or name == base or name.as_posix() != path
            or '..' in name.parts or re.fullmatch(r'[A-Za-z0-9_./-]{1,512}', path) is None
            or re.fullmatch(r'[0-9a-f]{64}', digest) is None):
        cli.error('Expected a bounded capture path and digest')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('capture', help='Repository-relative capture path under out/file-stage-integrated-stop-evidence')
    cli.add_argument('sha256', help='Expected lowercase SHA-256 of the complete capture')
    cli.add_argument('--session-v2', action='store_true', help='Review the combined process and carrier format')
    cli.add_argument('--screen', nargs=2, metavar=('CAPTURE', 'SHA256'),
                     help='Compare the saved Partial and terminal rows with the native V2 birth records')
    args = cli.parse_args()
    _capture_input(cli, args.capture, args.sha256)
    if args.screen:
        if not args.session_v2:
            cli.error('Tester role rows require --session-v2')
        _capture_input(cli, *args.screen)
    try:
        io = load_io()
        raw = pinned(io, args.capture, args.sha256, 64 * 1024)
        screen = pinned(io, *args.screen, 1024) if args.screen else None
        result = review(raw, relative_path=args.capture, session=args.session_v2, screen_raw=screen)
    except (OSError, ValueError, KeyError) as exc:
        cli.error(str(exc))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
