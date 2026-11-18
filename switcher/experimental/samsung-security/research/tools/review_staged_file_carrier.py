"""Review the existing file stage without deploying a profile or APK."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import uuid

import check_file_stage_device_preflight as preflight
import guest_tree_carrier_receiver as carrier
from guest_tree_shell_v2_transfer import verify_carrier_readback
from read_staged_file_carrier_receipt import read_completed_stage
from review_file_stage_sequence import require_stage_only_inventory
from run_guest_tree_install_transport import write_exclusive


OUT = preflight.ROOT / 'out/file-stage-staged-revalidation'


def verify_observation(code, stdout, stderr, publication, *, confirmation=False,
                       profile_present=False, tester_present=False):
    preflight.require(code == 0 and not stderr and stdout.isascii() and stdout.endswith(b'\n')
                      and b'\0' not in stdout and b'\r' not in stdout,
                      'Stage readback did not complete cleanly')
    lines = stdout.split(b'\n')
    preflight.require(len(lines) >= 5 and lines[0] == b'inventory_identity|begin'
                      and lines[-3] == b'inventory_identity|end', 'Stage inventory or carrier frame missing')
    inventory = preflight.inventory([line.decode('ascii') for line in lines[1:-3]],
                                    carrier_protocol='v2', confirmation=confirmation)
    require_stage_only_inventory(inventory, profile_present=profile_present, tester_present=tester_present)
    verify_carrier_readback(lines[-2] + b'\n', publication, carrier.CARRIER_BYTES)


def bind_completed_stage(witness, *, confirmation=False):
    transport = carrier.online_transport()
    parent, drop = carrier.observe_inventory(transport, True)
    target = carrier.CarrierTarget(parent, *drop, carrier_protocol='v2')
    with carrier._open_bound_observation(target, preflight.IDENTITY) as sock:
        code, stdout, stderr = preflight.shell_reply(sock, time.monotonic() + 20)
    preflight.require(code == 0 and not stderr and stdout.isascii() and b'\0' not in stdout,
                      'Current shell identity did not complete cleanly')
    command = carrier.readback_command(
        target, witness['stageStat'], witness['guardStat'],
        mounts=(witness['stageMount'], witness['guardMount']),
        inventory_identity=stdout.decode('ascii').splitlines(),
        confirmation=confirmation,
    )
    return target, command


def observe_stage(target, command, publication, *, confirmation=False, profile_present=False, tester_present=False):
    with carrier._open_bound_observation(target, command) as sock:
        reply = preflight.shell_reply(sock, time.monotonic() + 90)
    verify_observation(*reply, publication, confirmation=confirmation,
                       profile_present=profile_present, tester_present=tester_present)


def observe_completed_stage(witness, publication):
    target, command = bind_completed_stage(witness)
    observe_stage(target, command, publication)


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('job', type=Path)
    cli.add_argument('--live-readback', action='store_true')
    args = cli.parse_args(argv)
    result = {'status': 'STAGED_CARRIER_REVIEW_HELD', 'mayExecute': False, 'deviceEligible': False,
              'savedEvidenceVerified': False, 'currentReadbackVerified': False,
              'originalBootContinuity': 'not_recorded'}
    try:
        witness, publication = read_completed_stage(args.job.absolute())
        result['savedEvidenceVerified'] = True
        result['status'] = 'SAVED_STAGED_CARRIER_REVIEWED'
        result['sourceJob'] = args.job.name
        if args.live_readback:
            result['status'] = 'STAGED_CARRIER_REVIEW_HELD'
            observe_completed_stage(witness, publication)
            result['status'] = 'CURRENT_STAGED_CARRIER_REVIEWED'
            result['currentReadbackVerified'] = True
    except (EOFError, KeyError, OSError, TypeError, ValueError) as error:
        result['refusalType'] = type(error).__name__
    result['observedUtc'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    preflight.require(OUT.resolve() == OUT, 'Noncanonical review output directory')
    OUT.mkdir(exist_ok=True)
    job = OUT / ('r-' + uuid.uuid4().hex[:8])
    job.mkdir()
    receipt = job / 'receipt.json'
    write_exclusive(receipt, (json.dumps(result, indent=2) + '\n').encode('ascii'))
    print(result['status'], receipt)
    return 2 if result['status'] == 'STAGED_CARRIER_REVIEW_HELD' else 0


if __name__ == '__main__':
    raise SystemExit(main())
