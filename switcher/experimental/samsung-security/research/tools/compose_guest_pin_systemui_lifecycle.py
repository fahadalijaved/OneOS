"""Stage the exact authored lifecycle pair in the donor checker package."""

import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from compose_guest_pin_progress_entry import COMPLETION, COMPLETION_SHA
from run_guest_tree_install_transport import ROOT, load_io, pinned


OUT = ROOT / 'out/guest-pin-systemui-lifecycle-relocated-source'
LIFECYCLE = ('out/guest-pin-progress-entry-source/r-1791273f/receipt.json',
             '6dcbf6f50247b86ee57a1694f1f55e70b0ffffade09c089633523d817a3d1196')
PLACEMENT = ('out/guest-pin-lifecycle-placement-review/READBACK.json',
             'e8449693a40dea0105d38212e4eec180cc12133baf14cf29e4057eed2f42c617')
PACKAGE = 'com.oplus.keyguard.security'
OLD_DECLARATION = b'package com.appleexploit.oneos.security.transport;'
NEW_DECLARATION = f'package {PACKAGE};'.encode('ascii')


def relocate(raw):
    if not raw.startswith(OLD_DECLARATION) or raw.count(b'com.appleexploit.oneos.security.transport') != 1:
        raise ValueError('Expected an isolated original package declaration')
    relocated = NEW_DECLARATION + raw[len(OLD_DECLARATION):]
    if OLD_DECLARATION + relocated[len(NEW_DECLARATION):] != raw:
        raise ValueError('Package relocation lacks the exact inverse')
    return relocated


def compose():
    io = load_io()
    lifecycle = json.loads(pinned(io, *LIFECYCLE, 16384), object_pairs_hook=io['unique_object'])
    placement = json.loads(pinned(io, *PLACEMENT, 16384), object_pairs_hook=io['unique_object'])
    request = lifecycle['source']
    source_join = placement['stagedReceipt']
    if (lifecycle['status'] != 'STAGED_PIN_REQUEST_LIFECYCLE_SOURCE_ONLY' or lifecycle['selected'] is not False
            or lifecycle['deviceEligible'] is not False or lifecycle['wholeSourceInversePassed'] is not True
            or placement['status'] != 'STAGED_LIFECYCLE_TUPLE_SOURCE_PLACEMENT_CONSISTENT_ONLY'
            or placement['selected'] is not False or placement['targetAccessed'] is not False
            or placement['executedOriginal'] is not False
            or (source_join['path'], source_join['sha256']) != LIFECYCLE or source_join['source'] != request):
        raise ValueError('Lifecycle source and donor placement evidence disagree')
    request_bytes = pinned(io, request['path'], request['sha256'], 16384)
    if len(request_bytes) != request['bytes'] or lifecycle['originalSources'][COMPLETION] != COMPLETION_SHA:
        raise ValueError('Lifecycle input size or completion source differs')
    sources = {
        'GuestPinCheckRequest.java': relocate(request_bytes),
        'PinCheckCompletion.java': relocate(pinned(io, COMPLETION, COMPLETION_SHA, 16384)),
    }
    if OUT.resolve() != OUT:
        raise ValueError('Expected a repository-local source output')
    OUT.mkdir(exist_ok=True)
    run = OUT / ('r-' + uuid4().hex[:8])
    run.mkdir()
    source = run / Path(*PACKAGE.split('.'))
    source.mkdir(parents=True)
    outputs = {}
    for name, data in sources.items():
        path = source / name
        with path.open('xb') as stream:
            stream.write(data)
        outputs[name] = {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(data),
                         'sha256': hashlib.sha256(data).hexdigest()}
    result = {
        'status': 'STAGED_DONOR_PIN_LIFECYCLE_RELOCATION_SOURCE_ONLY', 'selected': False, 'deviceEligible': False,
        'package': PACKAGE, 'outputs': outputs, 'onlyPackageDeclarationsChanged': True,
        'lifecycleReceipt': {'path': LIFECYCLE[0], 'sha256': LIFECYCLE[1]},
        'placementReceipt': {'path': PLACEMENT[0], 'sha256': PLACEMENT[1]},
        'donorArchiveSha256': placement['archive']['sha256'],
        'callerPlacementPending': True,
    }
    with (run / 'receipt.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(compose(), indent=2))
