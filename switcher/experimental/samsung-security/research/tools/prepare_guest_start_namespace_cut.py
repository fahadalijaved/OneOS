"""Prepare one disabled guest-start namespace derivative; never execute scripts.

Default/--plan is metadata-only. --emit needs exact source-review and root
one-PC-emission documents. Neither mode admits any runtime/phone operation.
"""
import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'out/guest-start-namespace-cut'
SOURCE = ROOT/'firmware/installed-oneos-code-profile/static/assets/guest_start.sh'
SOURCE_BYTES = 78054
SOURCE_SHA = '896b72cc5bafadf975e29c05da0280e92b56a8f508c378d2c24e25a2b7f30446'
PROPOSAL = OUT/'source-api-proposal.json'
PLAN_SHA = '80c15e7d40cc28c64669e3be81752172018b73fe37b5f6f93f6dca89b6423ac4'
SHEBANG = b'#!/system/bin/sh\n'
FENCE = (b'# SOURCE-ONLY: native custody and per-process root entry remain unassembled.\n'
         b"printf '%s\\n' 'SOURCE_ONLY_GUEST_NAMESPACE_OWNER_UNBOUND' >&2\n"
         b'exit 2\n')
EDITS = [
    (17, 17, 'mandatory-source-only-entry-refusal',
     'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', FENCE),
    (468, 852, 'omit-old-root-transition',
     'b7f0ca9767cf15cd2e6ee0fa2d0725031ea56d6b48a66029263b38e6a2429477',
     b'# SOURCE-ONLY OMITTED: staged cd, late recursive-private and pivot_root.\n'
     b'# Future native supervisor must own ColorOS root entry before script exec.\n'),
    (1891, 2425, 'omit-old-postinstall-detach',
     '94d1dd34bb21afd078cefa7060eb58f9e7ff6da86ab84531326156f5941ec749',
     b'# SOURCE-ONLY OMITTED: old-pivot postinstall detach and its obsolete-pivot guard.\n'
     b'# No namespace-wide pivot or old-root mount is supplied by this derivative.\n'),
    (3750, 4494, 'omit-old-data-alias-and-mirror-replacement',
     '833db4ad660b35feb18494bb30c5440fcd6b0126743bbb5cf973ed7a73f61108',
     b'# SOURCE-ONLY OMITTED: duplicate data alias and data_mirror replacement/rebinds.\n'
     b'# Future native owner must retain its actual alias and fresh mirror peers.\n'),
]


class Refused(ValueError): pass


def sha(data): return hashlib.sha256(data).hexdigest()
def encoded(value): return (json.dumps(value, indent=2)+'\n').encode()
def pin(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': sha(data)}


def checked_json(path):
    path = Path(path)
    if path.is_symlink() or not path.resolve(strict=True).is_relative_to(ROOT) or path.stat().st_size > 65536:
        raise Refused('REVIEW_PATH')
    with path.open('rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise Refused('REVIEW_SIZE')
    return json.loads(raw), sha(raw)


def inputs():
    source = SOURCE.read_bytes()
    if (len(source), sha(source)) != (SOURCE_BYTES, SOURCE_SHA) or not source.startswith(SHEBANG):
        raise Refused('SOURCE_PROFILE')
    plan, actual = checked_json(PROPOSAL)
    if actual != PLAN_SHA or plan['source'] != {'path': str(SOURCE.relative_to(ROOT)).replace('\\', '/'),
                                               'bytes': SOURCE_BYTES, 'sha256': SOURCE_SHA}:
        raise Refused('APPROVED_PLAN')
    if plan['editCount'] != 4 or len(plan['edits']) != 4:
        raise Refused('EDIT_COUNT')
    cursor = 0
    for row, (start, end, kind, old_sha, replacement) in zip(plan['edits'], EDITS):
        if not cursor <= start <= end <= len(source) or row['start'] != start or row['end'] != end or row['kind'] != kind:
            raise Refused('EDIT_RANGE')
        if sha(source[start:end]) != old_sha or row['sourceSpanSha256'] != old_sha:
            raise Refused('SOURCE_SPAN')
        if row['replacementUtf8'].encode() != replacement or row['replacementSha256'] != sha(replacement):
            raise Refused('REPLACEMENT')
        cursor = end
    proposal_pin = pin(PROPOSAL)
    if proposal_pin['sha256'] != actual:
        raise Refused('PROPOSAL_MOVED')
    dependencies = {str(PROPOSAL.relative_to(ROOT)).replace('\\', '/'): proposal_pin}
    for name, expected in plan['evidencePins'].items():
        path = ROOT/name
        if path.is_symlink() or not path.resolve(strict=True).is_relative_to(ROOT) or pin(path) != expected:
            raise Refused('DEPENDENCY_PIN')
        dependencies[name] = expected
    return source, plan, dependencies


def gate(path, tool_sha):
    value, actual = checked_json(path)
    if set(value) != {'schema', 'sourceToolSha256', 'sourcePlanSha256', 'sourceReview', 'rootDecision'}:
        raise Refused('GATE_SCHEMA')
    if value['schema'] != 'guest-start-namespace-cut-review/v1' or value['sourceToolSha256'] != tool_sha or value['sourcePlanSha256'] != PLAN_SHA:
        raise Refused('GATE_BINDING')
    canonical_gate = Path(path).resolve(strict=True)
    refs = {str(canonical_gate.relative_to(ROOT)).replace('\\', '/'): actual}
    role_paths = {str(canonical_gate).casefold()}
    for key, status in [('sourceReview', 'SOURCE_PASS'), ('rootDecision', 'ONE_PC_EMIT_GO')]:
        ref = value[key]
        if set(ref) != {'path', 'sha256'}:
            raise Refused('GATE_REFERENCE')
        proof, proof_sha = checked_json(ROOT/ref['path'])
        if proof_sha != ref['sha256'] or proof.get('status') != status or proof.get('sourceToolSha256') != tool_sha or proof.get('sourcePlanSha256') != PLAN_SHA:
            raise Refused('GATE_REFERENCE')
        canonical_ref = (ROOT/ref['path']).resolve(strict=True)
        identity = str(canonical_ref).casefold()
        if identity in role_paths:
            raise Refused('DUPLICATE_GATE_ROLE_PATH')
        role_paths.add(identity)
        refs[str(canonical_ref.relative_to(ROOT)).replace('\\', '/')] = proof_sha
    return refs


def forward(source):
    result = bytearray(); mapping = []; cursor = 0
    for start, end, kind, old_sha, replacement in EDITS:
        if not cursor <= start <= end <= len(source) or sha(source[start:end]) != old_sha:
            raise Refused('SOURCE_SPAN')
        result.extend(source[cursor:start]); target = len(result)
        result.extend(replacement)
        mapping.append({'kind': kind, 'sourceStart': start, 'sourceEnd': end,
                        'candidateStart': target, 'candidateEnd': len(result),
                        'sourceSpanSha256': old_sha, 'replacementSha256': sha(replacement)})
        cursor = end
    result.extend(source[cursor:])
    return bytes(result), mapping


def inverse(source, candidate):
    expected, mapping = forward(source)
    if candidate != expected:
        raise Refused('FOREIGN_CANDIDATE_BYTES')
    restored = bytearray(candidate)
    for row in reversed(mapping):
        restored[row['candidateStart']:row['candidateEnd']] = source[row['sourceStart']:row['sourceEnd']]
    if bytes(restored) != source:
        raise Refused('INVERSE')
    return bytes(restored)


def preservation(source, candidate, mapping):
    original = target = 0
    for row in mapping:
        if source[original:row['sourceStart']] != candidate[target:row['candidateStart']]:
            raise Refused('FOREIGN_UNEDITED_BYTES')
        original, target = row['sourceEnd'], row['candidateEnd']
    if source[original:] != candidate[target:]:
        raise Refused('FOREIGN_UNEDITED_BYTES')


def negatives(source, candidate):
    foreign = bytearray(candidate); foreign[2] ^= 1
    changed = bytearray(candidate); changed[candidate.index(b'exit 2\n')+5] = ord('0')
    results = []
    for name, data in [('foreign-original-shebang-byte', bytes(foreign)),
                       ('changed-exit-zero-with-truthful-untrusted-seal', bytes(changed))]:
        truthful_untrusted_seal = sha(data)
        if truthful_untrusted_seal == sha(candidate): raise Refused('NEGATIVE_SETUP')
        try:
            inverse(source, data)
        except Refused:
            results.append(name)
        else:
            raise Refused('NEGATIVE_FAILED')
    return results


def work_dir():
    if not OUT.resolve(strict=True).is_relative_to((ROOT/'out').resolve(strict=True)) or not (ROOT/'out').resolve(strict=True).is_relative_to(ROOT):
        raise Refused('OUTPUT_CONTAINMENT')
    work = OUT/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex)
    work.mkdir(exist_ok=False)
    return work


def run(emit_path=None):
    tool_sha = sha(Path(__file__).read_bytes())
    source, plan, dependencies = inputs()
    review = gate(emit_path, tool_sha) if emit_path is not None else {}
    work = work_dir()
    receipt = {'schema': 'guest-start-namespace-cut/v1', 'status': 'SOURCE_PLAN_ONLY_NO_CANDIDATE',
               'toolSha256': tool_sha, 'sourcePlanSha256': PLAN_SHA, 'sourceSha256': SOURCE_SHA,
               'sourceBytes': SOURCE_BYTES, 'dependencies': dependencies, 'reviewInputs': review,
               'selected': False, 'bootable': False, 'runtimeOwnerImplemented': False,
               'scriptsExecuted': False, 'phoneActions': False, 'originalOneOsFilesModified': False,
               'propertyCompositionImplemented': False, 'propertyComposition': plan['propertyComposition'],
               'missingOwners': plan['missingOwners'], 'existingOneOsPermissiveAndPrivappLimitationsAllowed': True,
               'stockEquivalenceRequired': False}
    try:
        (work/'source-plan.json').write_bytes(encoded(plan))
        if emit_path is not None:
            receipt['status'] = 'FAILED_SOURCE_EMISSION'
            candidate, mapping = forward(source)
            if not candidate.startswith(SHEBANG+FENCE): raise Refused('ENTRY_FENCE')
            preservation(source, candidate, mapping)
            path = work/'guest_start.sh.candidate.sh.disabled'; path.write_bytes(candidate)
            saved = path.read_bytes(); restored = inverse(source, saved)
            reapplied, _ = forward(restored)
            if reapplied != saved: raise Refused('SAVED_REAPPLY')
            diff = ''.join(difflib.unified_diff(source.decode('utf-8').splitlines(True), saved.decode('utf-8').splitlines(True),
                                              fromfile='a/guest_start.sh', tofile='b/guest_start.sh'))
            (work/'guest_start.sh.diff').write_bytes(diff.encode())
            receipt['candidate'] = {'path': str(path.relative_to(ROOT)).replace('\\', '/'),
                                    'bytes': len(saved), 'sha256': sha(saved), 'edits': mapping,
                                    'originalRestoredSha256': sha(restored), 'inverseExact': restored == source,
                                    'savedReapplyExact': reapplied == saved, 'outsideEditsPreserved': True}
            receipt['negativeCasesRejected'] = negatives(source, saved)
            receipt['status'] = 'PASS_SOURCE_ONLY_DISABLED_NAMESPACE_CUT'
    except Exception as error:
        receipt['failure'] = type(error).__name__
        raise
    finally:
        try:
            receipt['sourceUnchanged'] = pin(SOURCE) == {'bytes': SOURCE_BYTES, 'sha256': SOURCE_SHA}
            receipt['toolUnchanged'] = sha(Path(__file__).read_bytes()) == tool_sha
            receipt['dependenciesUnchanged'] = all(pin(ROOT/name) == expected for name, expected in dependencies.items())
            receipt['reviewInputsUnchanged'] = all(checked_json(ROOT/name)[1] == expected for name, expected in review.items())
        except Exception as error:
            receipt['sourceUnchanged'] = receipt['toolUnchanged'] = receipt['dependenciesUnchanged'] = receipt['reviewInputsUnchanged'] = False
            receipt['recheckFailure'] = type(error).__name__
        if not all(receipt[k] for k in ['sourceUnchanged', 'toolUnchanged', 'dependenciesUnchanged', 'reviewInputsUnchanged']):
            receipt['status'] = 'FAILED_INPUT_MOVED'
        (work/'receipt.json').write_bytes(encoded(receipt))
    if receipt['status'].startswith('FAILED'): raise Refused('NO_COHERENT_EMISSION')
    if emit_path is not None and receipt['status'] == 'PASS_SOURCE_ONLY_DISABLED_NAMESPACE_CUT':
        (ROOT/'inventory/guest-start-namespace-cut.json').write_bytes(encoded({**receipt,
            'receipt': str((work/'receipt.json').relative_to(ROOT)).replace('\\', '/'),
            'receiptSha256': sha((work/'receipt.json').read_bytes())}))
    print(json.dumps({'status': receipt['status'], 'receipt': str((work/'receipt.json').relative_to(ROOT)),
                      'receiptSha256': sha((work/'receipt.json').read_bytes()), 'candidateScripts': int(emit_path is not None)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--plan', action='store_true')
    selection.add_argument('--emit', type=Path, help='Independent review plus root one-PC-emission gate; never runtime admission')
    args = parser.parse_args()
    run(args.emit)


if __name__ == '__main__': main()
