"""Review the signed confirmation tester against the existing phone stage."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import time
import uuid

import check_file_stage_device_preflight as preflight
import guest_tree_carrier_receiver as carrier
from confirmation_publisher_delivery import confirmation_publisher_delivery_command, confirmation_publisher_readback_command
from confirmation_tester_cohort import load_confirmation_cohort
from confirmation_tester_data_slot import data_slot_command, require_empty_data_slots
from read_staged_file_carrier_receipt import read_completed_stage
from review_staged_file_carrier import bind_completed_stage, observe_stage
from review_staged_tester import check_syntax
from run_guest_tree_install_transport import write_exclusive
from staged_tester_apk import tester_install_command
from staged_tester_profile import profile_publication_command


OUT = preflight.ROOT / 'out/file-stage-confirmation-phone-review'


def observe_drop_for_review(target, witness):
    command = carrier._bound_installer_preamble(
        target, witness['stageStat'], witness['guardStat'], mounts=(witness['stageMount'], witness['guardMount']),
    ) + """entries=$(/system/bin/toybox ls -1A /proc/$$/fd/5 2>&1) || exit 2
[ "$entries" = 'installer
publisher' ] || exit 2
bound_current || exit 2
printf 'EXACT_ORIGINAL_DROP_ONLY\\n'
"""
    with carrier._open_bound_observation(target, command) as sock:
        reply = preflight.shell_reply(sock, time.monotonic() + 20)
    preflight.require(reply == (0, b'EXACT_ORIGINAL_DROP_ONLY\n', b''),
                      'Protected drop contains an unexpected object or is unobservable')


def review(witness, publication):
    cohort = load_confirmation_cohort()
    target, observe = bind_completed_stage(witness)
    observe_stage(target, observe, publication)
    observe_drop_for_review(target, witness)

    commands = (
        confirmation_publisher_delivery_command(target, witness, secrets.token_hex(16)),
        confirmation_publisher_readback_command(target, witness),
        profile_publication_command(target, witness, confirmation=True),
        tester_install_command(target, witness, confirmation=True),
    )
    for command in commands:
        check_syntax(target, command)

    observe_stage(target, observe, publication)
    with carrier._open_bound_observation(target, data_slot_command(target, witness)) as sock:
        reply = preflight.shell_reply(sock, time.monotonic() + 35)
    require_empty_data_slots(*reply, eof=True)
    observe_drop_for_review(target, witness)

    def pin(artifact):
        return {'bytes': artifact.size, 'sha256': artifact.sha256}

    return {
        'status': 'CONFIRMATION_TESTER_PROPOSAL_REVIEWED',
        'mayExecute': False,
        'sourceStageVerified': True,
        'newPublisherSlotAbsent': True,
        'currentTesterDataSlotsAbsent': True,
        'androidSyntaxChecks': len(commands),
        'tester': pin(cohort.tester_apk),
        'profile': pin(cohort.profile),
        'publisher': pin(cohort.publisher),
        'frameworkActivationInProposal': False,
    }


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('job', type=Path)
    args = cli.parse_args(argv)
    try:
        witness, publication = read_completed_stage(args.job.absolute())
        result = review(witness, publication)
    except (EOFError, KeyError, OSError, TypeError, ValueError) as error:
        result = {'status': 'CONFIRMATION_TESTER_PROPOSAL_HELD', 'mayExecute': False,
                  'refusalType': type(error).__name__}
        if type(error) is ValueError and error.args and type(error.args[0]) is str:
            result['reason'] = error.args[0]
    result['observedUtc'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    preflight.require(OUT.resolve() == OUT, 'Noncanonical confirmation review output directory')
    OUT.mkdir(exist_ok=True)
    job = OUT / ('r-' + uuid.uuid4().hex[:8])
    job.mkdir()
    receipt = job / 'receipt.json'
    write_exclusive(receipt, (json.dumps(result, indent=2) + '\n').encode('ascii'))
    print(result['status'], receipt)
    return 2 if result['status'] == 'CONFIRMATION_TESTER_PROPOSAL_HELD' else 0


if __name__ == '__main__':
    raise SystemExit(main())
