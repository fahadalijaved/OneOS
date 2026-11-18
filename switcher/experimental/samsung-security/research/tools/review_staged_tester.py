"""Review the profile and tester-only install against the published stage."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import time
import uuid

import check_file_stage_device_preflight as preflight
import guest_tree_carrier_receiver as carrier
from read_staged_file_carrier_receipt import read_completed_stage
from review_staged_file_carrier import bind_completed_stage, observe_stage
from run_guest_tree_install_transport import write_exclusive
from staged_tester_apk import load_tester_apk, tester_install_command
from staged_tester_profile import profile_publication_command


OUT = preflight.ROOT / 'out/file-stage-staged-tester-review'


def check_syntax(target, command):
    # The command is data on stdin to the device's parser, never a shell script to execute.
    parse = f"printf '%s' {shlex.quote(command)} | /system/bin/sh -n"
    with carrier._open_bound_observation(target, parse) as sock:
        reply = preflight.shell_reply(sock, time.monotonic() + 25)
    preflight.require(reply == (0, b'', b''), 'Android shell parser refused the exact candidate command')


def review(witness, publication):
    apk = load_tester_apk()
    target, observe = bind_completed_stage(witness)
    observe_stage(target, observe, publication)
    profile_command = profile_publication_command(target, witness)
    tester_command = tester_install_command(target, witness)
    for command in (profile_command, tester_command):
        check_syntax(target, command)
    observe_stage(target, observe, publication)
    _, readiness = preflight.readiness_artifacts('v2')
    return {
        'status': 'TESTER_PREFIX_REVIEWED_HOST_INACTIVITY_UNVERIFIED',
        'mayExecute': False,
        'currentStageVerified': True,
        'androidShellSyntaxVerified': True,
        'profileSha256': readiness['profile'],
        'publisherSha256': preflight.drop_artifacts('v2')['deploy_publisher'][2],
        'testerSha256': hashlib.sha256(apk).hexdigest(),
        'testerBytes': len(apk),
        'hostInstallInPlan': False,
        'activationInPlan': False,
    }


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('job', type=Path)
    args = cli.parse_args(argv)
    try:
        witness, publication = read_completed_stage(args.job.absolute())
        result = review(witness, publication)
    except (EOFError, KeyError, OSError, TypeError, ValueError) as error:
        result = {'status': 'STAGED_TESTER_REVIEW_HELD', 'mayExecute': False,
                  'refusalType': type(error).__name__}
    result['observedUtc'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    preflight.require(OUT.resolve() == OUT, 'Noncanonical tester review output directory')
    OUT.mkdir(exist_ok=True)
    job = OUT / ('r-' + uuid.uuid4().hex[:8])
    job.mkdir()
    receipt = job / 'receipt.json'
    write_exclusive(receipt, (json.dumps(result, indent=2) + '\n').encode('ascii'))
    print(result['status'], receipt)
    return 2 if result['status'] == 'STAGED_TESTER_REVIEW_HELD' else 0


if __name__ == '__main__':
    raise SystemExit(main())
