"""Check an ordered, normalized UI transcript against the saved signed cohort."""

import argparse
import json
from pathlib import Path
import re

from check_file_stage_device_preflight import PACKAGES, require
from check_file_stage_local_cohort import verify_local_cohort
from run_guest_tree_install_transport import ROOT, load_io


SCHEMA = 'oneos-file-stage-current-ui/v1'
CAPTURES = ROOT / 'out/file-stage-current-ui-evidence'
COMPONENT = PACKAGES['tester'][0] + '/.PrepareActivity'
PREPARE = 'Prepare a private view?'
STOP = 'Stop preparation?'
PREPARE_ACK = 'Prepare request acknowledged.'
STOP_ACK = 'Stop request acknowledged.'
STOP_PENDING = 'Stop requested. Waiting for the same attempt.'
WAIT_HOST = 'Waiting for the host. Prepare has not been sent.'
WAIT_STATUS = 'Waiting for preparation status.'
PARTIAL = 'Partial filesystem view observed.'
CLOSING = 'Cleanup in progress.'
LOCAL_TERMINAL = 'Local terminal observed. Cleanup still pending.'
LOCAL_CLEANUP = 'Local cleanup observed.'
PRIMARIES = (WAIT_HOST, WAIT_STATUS, PARTIAL, CLOSING, LOCAL_TERMINAL, LOCAL_CLEANUP)
AMBIGUOUS = {
    'Latest status sample unavailable.', 'Service connection lost.', 'Service registration cleanup is unconfirmed.',
    'Cleanup unconfirmed.', 'Preparation unavailable before dispatch.', 'Stopped before dispatch.',
    'Preparation unavailable before the Prepare request was sent.', 'Stopped before the Prepare request was sent.',
    'Controller cleanup is unconfirmed.',
    'Tester stage preparation is required.', 'Preparation refused.', 'Prepare request unavailable.',
    'Prepare acknowledgment unconfirmed.', 'Stop request unavailable.', 'Stop acknowledgment unconfirmed.',
}
EVENT_FIELDS = {'event', 'elapsedMs', 'attempt', 'component'}


def expected_cohort(local_cohort):
    require(local_cohort.get('status') == 'MATCHED_LOCAL_COHORT_VERIFIED', 'LOCAL_COHORT_UNVERIFIED')
    return {key: local_cohort[key] for key in ('pairReceiptSha256', 'profileSha256', 'controllerSha256', 'packages')}


def _widget(lines):
    require(type(lines) is list and 1 <= len(lines) <= 8 and all(type(line) is str for line in lines),
            'INVALID_STATUS_WIDGET')
    require(AMBIGUOUS.isdisjoint(lines), 'AMBIGUOUS_OR_REFUSED_STATUS')
    primary, *footers = lines
    require(primary in PRIMARIES, 'UNKNOWN_PRIMARY_STATUS')
    rank = PRIMARIES.index(primary)
    history = bool(rank >= PRIMARIES.index(CLOSING) and footers[:1] == [PARTIAL])
    if history:
        footers.pop(0)
    prepare_ack = footers[:1] == [PREPARE_ACK]
    if prepare_ack:
        footers.pop(0)
    stop_ack = footers == [STOP_ACK]
    stop_pending = footers == [STOP_PENDING]
    require(not footers or stop_ack or stop_pending, 'INVALID_OR_DUPLICATE_FOOTER')
    return primary, rank, history, prepare_ack, stop_ack, stop_pending


def review(doc, local_cohort):
    result = {'status': 'HELD_UI_TRANSCRIPT', 'mayExecute': False, 'deviceAcceptance': False}
    try:
        require(type(doc) is dict and doc.keys() == {'schema', 'cohort', 'observations'} and doc['schema'] == SCHEMA,
                'UNEXPECTED_CAPTURE_SCHEMA')
        require(doc['cohort'] == expected_cohort(local_cohort), 'SIGNED_COHORT_MISMATCH')
        events = doc['observations']
        require(type(events) is list and 1 <= len(events) <= 64, 'MISSING_OR_OVERSIZE_TRANSCRIPT')
        attempt, last_ms, last_rank = None, -1, -1
        prepare_seen = partial_seen = stop_seen = terminal_seen = False
        prepare_ack_seen = stop_ack_seen = False
        for row in events:
            require(type(row) is dict and not terminal_seen, 'EVENT_AFTER_TERMINAL_OR_MALFORMED')
            event = row.get('event')
            require(event in ('prepare_confirmed', 'status', 'stop_confirmed'), 'UNKNOWN_OBSERVATION_EVENT')
            require(row.keys() == EVENT_FIELDS | {'lines' if event == 'status' else 'dialog'}, 'MALFORMED_OBSERVATION')
            stamp, occurrence = row['elapsedMs'], row['attempt']
            require(type(stamp) is int and last_ms < stamp <= 2**63 - 1, 'UNORDERED_OR_INVALID_ELAPSED_TIME')
            require(type(occurrence) is str and re.fullmatch('[0-9a-f]{64}', occurrence)
                    and (attempt is None or attempt == occurrence), 'ATTEMPT_CHANGED_OR_UNKNOWN')
            require(row['component'] == COMPONENT, 'UNEXPECTED_TESTER_COMPONENT')
            attempt, last_ms = occurrence, stamp

            if event == 'prepare_confirmed':
                require(not prepare_seen and row['dialog'] == PREPARE, 'DUPLICATE_OR_DIFFERENT_PREPARE_CONFIRMATION')
                prepare_seen = True
                continue
            require(prepare_seen, 'PREPARE_CONFIRMATION_MISSING')
            if event == 'stop_confirmed':
                require(partial_seen and not stop_seen and row['dialog'] == STOP, 'EARLY_DUPLICATE_OR_DIFFERENT_STOP')
                stop_seen = True
                continue

            primary, rank, history, prepare_ack, stop_ack, stop_pending = _widget(row['lines'])
            require(rank >= last_rank, 'PRIMARY_STATUS_REGRESSED')
            require(not prepare_ack_seen or prepare_ack, 'PREPARE_ACK_DISAPPEARED')
            require(not stop_ack_seen or stop_ack, 'STOP_ACK_DISAPPEARED')
            require(stop_seen or not (stop_ack or stop_pending), 'STOP_STATUS_WITHOUT_CONFIRMATION')
            require(primary != WAIT_HOST or not prepare_ack, 'PREPARE_ACK_BEFORE_DISPATCH')
            if primary == PARTIAL:
                require(prepare_ack, 'PARTIAL_WITHOUT_PREPARE_ACK')
                partial_seen = True
            if rank >= PRIMARIES.index(CLOSING):
                require(partial_seen and stop_seen and history, 'CLEANUP_WITHOUT_ORDERED_PARTIAL_AND_STOP')
            if primary == LOCAL_CLEANUP:
                require(stop_ack, 'LOCAL_CLEANUP_WITHOUT_STOP_ACK')
                terminal_seen = True
            prepare_ack_seen, stop_ack_seen, last_rank = prepare_ack, stop_ack, rank
        if terminal_seen:
            return result | {'status': 'ORDERED_UI_TRANSCRIPT_REQUIRES_DEVICE_READBACK',
                             'observationsReviewed': len(events)}
        return result | {'status': 'UI_TRANSCRIPT_PENDING', 'observationsReviewed': len(events)}
    except (KeyError, TypeError):
        return result | {'reason': 'MALFORMED_EVIDENCE'}
    except ValueError as error:
        return result | {'reason': str(error)}


def read_capture(path):
    require(path.is_relative_to(CAPTURES) and path.suffix == '.json', 'EXPECTED_LOCAL_CAPTURE_FILE')
    io = load_io()
    with io['checked_input'](path, max_size=64 * 1024) as stream:
        raw = stream.read(64 * 1024 + 1)
    require(len(raw) <= 64 * 1024, 'CAPTURE_EXCEEDS_LIMIT')
    return json.loads(raw, object_pairs_hook=io['unique_object'])


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('capture', type=Path)
    cli.add_argument('--integrated', action='store_true', help='Use the exact signed integrated tester and host cohort')
    args = cli.parse_args(argv)
    capture = read_capture(args.capture.absolute())
    if args.integrated:
        from file_stage_integrated_cohort import integrated_cohort

        local_cohort = integrated_cohort()
    else:
        local_cohort = verify_local_cohort()
    print(json.dumps(review(capture, local_cohort), indent=2))


if __name__ == '__main__':
    main()
