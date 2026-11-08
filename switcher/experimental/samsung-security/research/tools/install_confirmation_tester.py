"""Run one explicitly approved confirmation tester file and install sequence."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import uuid

import check_file_stage_device_preflight as preflight
from confirmation_payload_transfer import call
from confirmation_publisher_delivery import (
    PUBLISHER_LEAF, READBACK_FRAME, confirmation_publisher_delivery_command, confirmation_publisher_readback_command,
    published_frame, ready_frame,
)
from confirmation_tester_cohort import CONFIRMATION_TESTER_SHA256, load_confirmation_cohort
from confirmation_tester_data_slot import data_slot_command, require_empty_data_slots
from read_staged_file_carrier_receipt import read_completed_stage
from review_confirmation_tester import observe_drop_for_review
from review_file_stage_sequence import PROFILE, native_terminal
from review_staged_file_carrier import bind_completed_stage, observe_stage
from review_staged_tester import check_syntax
from run_guest_tree_install_transport import write_exclusive
from staged_tester_apk import tester_install_command
from staged_tester_profile import profile_publication_command


OUT = preflight.ROOT / 'out/file-stage-confirmation-install'
APK_READY = b'ONEOS_APK_READY\n'


def require_approval(approval):
    preflight.require(type(approval) is str and approval == CONFIRMATION_TESTER_SHA256,
                      'The exact confirmation tester approval is required')


def install(witness, publication, approval, save):
    """Finish each remote action and its readback before granting the next action."""
    require_approval(approval)
    cohort = load_confirmation_cohort()
    preflight.require(cohort.tester_apk.sha256 == approval, 'Approved tester bytes differ')
    target, observation = bind_completed_stage(witness, confirmation=True)
    observe_stage(target, observation, publication, confirmation=True)
    observe_drop_for_review(target, witness)
    require_empty_data_slots(*call(target, data_slot_command(target, witness)), eof=True)

    nonce = secrets.token_hex(16)
    delivery = confirmation_publisher_delivery_command(target, witness, nonce)
    publisher_readback = confirmation_publisher_readback_command(target, witness)
    profile = profile_publication_command(target, witness, confirmation=True)
    tester = tester_install_command(target, witness, confirmation=True)
    for command in (delivery, publisher_readback, profile, tester):
        check_syntax(target, command)

    def run(phase, command, *, payload=None, ready=None):
        attempt = {'status': 'ATTEMPT_STARTED', 'automaticRetry': False}
        if phase == 'publisher':
            attempt['temporaryNamePrefix'] = f'.{PUBLISHER_LEAF}-{nonce}.'
        save(phase + '-started', attempt)
        code, stdout, stderr = call(target, command, payload=payload, ready=ready)
        save(phase + '-terminal', {'exitCode': code, 'stdoutSha256': hashlib.sha256(stdout).hexdigest(),
                                   'stderrBytes': len(stderr), 'remoteEof': True})
        return code, stdout, stderr

    def verify_publisher():
        preflight.require(call(target, publisher_readback) == (0, READBACK_FRAME, b''),
                          'Independent confirmation publisher readback failed')

    terminal = run('publisher', delivery, payload=cohort.publisher.data, ready=ready_frame(nonce))
    preflight.require(terminal == (0, published_frame(nonce), b''), 'Publisher delivery terminal is unconfirmed')
    verify_publisher()
    observe_stage(target, observation, publication, confirmation=True)

    terminal = run('profile', profile)
    preflight.require(native_terminal(PROFILE, *terminal, eof=True) == 'PUBLISHED_REQUIRES_READBACK',
                      'Fresh profile publication terminal is unconfirmed')
    observe_stage(target, observation, publication, confirmation=True, profile_present=True)

    terminal = run('tester', tester, payload=cohort.tester_apk.data, ready=APK_READY)
    preflight.require(terminal == (0, b'Success\n', b''), 'Fresh tester installation terminal is unconfirmed')
    observe_stage(target, observation, publication, confirmation=True, profile_present=True, tester_present=True)
    verify_publisher()
    return {'status': 'CONFIRMATION_TESTER_INSTALLED_AND_VERIFIED', 'testerSha256': approval,
            'profileSha256': cohort.profile.sha256, 'publisherSha256': cohort.publisher.sha256,
            'launcherInvoked': False, 'activationCommandIssued': False, 'automaticRetry': False}


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('job', type=Path)
    cli.add_argument('--approved-tester-sha256', required=True)
    args = cli.parse_args(argv)
    require_approval(args.approved_tester_sha256)
    witness, publication = read_completed_stage(args.job.absolute())
    preflight.require(OUT.resolve() == OUT, 'Noncanonical tester install output directory')
    OUT.mkdir(exist_ok=True)
    job = OUT / ('r-' + uuid.uuid4().hex[:8])
    job.mkdir()

    def save(name, record):
        write_exclusive(job / (name + '.json'), (json.dumps(record, indent=2) + '\n').encode('ascii'))

    try:
        result = install(witness, publication, args.approved_tester_sha256, save)
    except (EOFError, KeyError, OSError, TypeError, ValueError) as error:
        result = {'status': 'CONFIRMATION_TESTER_INSTALL_HELD', 'refusalType': type(error).__name__,
                  'automaticRetry': False}
    result['observedUtc'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    save('result', result)
    print(result['status'], job / 'result.json')
    return 2 if result['status'] == 'CONFIRMATION_TESTER_INSTALL_HELD' else 0


if __name__ == '__main__':
    raise SystemExit(main())
