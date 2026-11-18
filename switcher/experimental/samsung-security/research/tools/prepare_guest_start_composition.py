"""Source-only eleven-edit guest_start composition; never execute scripts.

Default/--plan is report-only. --emit requires independent exact source review
and a separate root one-PC-emission decision. No runtime admission exists.
"""
import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import stat
import uuid

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'out/guest-start-composition'
PLAN = 'out/guest-start-composition-plan/composition-plan.json'
PLAN_SHA = 'e10e83f2c5beb51900f68c970d66e3f1902610a134cf015b908644d7832a3b7b'
SOURCE = 'firmware/installed-oneos-code-profile/static/assets/guest_start.sh'
SOURCE_SHA = '896b72cc5bafadf975e29c05da0280e92b56a8f508c378d2c24e25a2b7f30446'
PROPERTY_RECEIPT = 'out/retained-property-script-cut/20261106T072749384206Z-d3d76942c5ba4a9cb454863361008b6a/receipt.json'
NAMESPACE_RECEIPT = 'out/guest-start-namespace-cut/20261106T094045555832Z-06595f2bae184bfd9bb57d6330c8bb44/receipt.json'
RANGES = [(17, 17), (468, 852), (1891, 2425), (3750, 4494),
          (10193, 10200), (11796, 11803), (13208, 13215), (34403, 34410),
          (52539, 52546), (70641, 70648), (72011, 72018)]
FENCE_SHA = '25e206db59319cd25177e667471aedb7736fa684d85364a66612d11a42253a5a'
MAX_INPUT = 2*1024*1024


class Refused(ValueError): pass


def sha(data): return hashlib.sha256(data).hexdigest()
def encoded(value): return (json.dumps(value, indent=2)+'\n').encode()
def pin(data): return {'bytes': len(data), 'sha256': sha(data)}


class Inputs:
    """Retain the actual first admitted bytes; never overwrite a role/pin."""
    def __init__(self):
        self.rows = {}
        self.identities = set()

    def bounded_read(self, path, limit):
        path = Path(path)
        if path.is_symlink(): raise Refused('SYMLINK_INPUT')
        canonical = path.resolve(strict=True)
        if not canonical.is_relative_to(ROOT) or not stat.S_ISREG(canonical.stat().st_mode):
            raise Refused('INPUT_CONTAINMENT_OR_TYPE')
        if canonical.stat().st_size > limit: raise Refused('INPUT_SIZE')
        with canonical.open('rb') as stream:
            data = stream.read(limit+1)
        if len(data) > limit: raise Refused('INPUT_SIZE')
        return canonical, data

    def admit(self, name, role, expected=None, limit=MAX_INPUT):
        canonical, data = self.bounded_read(ROOT/name, limit)
        identity = str(canonical).casefold()
        if identity in self.identities: raise Refused('DUPLICATE_INPUT_OR_GATE_ROLE_PATH')
        actual = pin(data)
        if expected is not None and actual != expected: raise Refused('INPUT_PIN')
        self.identities.add(identity)
        key = canonical.relative_to(ROOT).as_posix()
        self.rows[key] = {'role': role, **actual, 'data': data}
        return data

    def snapshot(self):
        return {name: {k: value for k, value in row.items() if k != 'data'} for name, row in self.rows.items()}

    def recheck(self):
        for name, row in self.rows.items():
            canonical, data = self.bounded_read(ROOT/name, MAX_INPUT)
            if canonical.relative_to(ROOT).as_posix() != name or data != row['data']:
                raise Refused('ADMITTED_INPUT_MOVED')


def validated_rows(source, rows):
    if len(source) != 78054 or sha(source) != SOURCE_SHA: raise Refused('SOURCE_PROFILE')
    if [(r['start'], r['end']) for r in rows] != RANGES: raise Refused('UNLISTED_OR_COLLIDING_ROWS')
    cursor = 0
    for row in rows:
        start, end = row['start'], row['end']
        replacement = row['replacementUtf8'].encode()
        if not cursor <= start <= end <= len(source): raise Refused('EDIT_OVERLAP')
        if sha(source[start:end]) != row['sourceSpanSha256']: raise Refused('SOURCE_SPAN')
        if pin(replacement) != {'bytes': row['replacementBytes'], 'sha256': row['replacementSha256']}:
            raise Refused('REPLACEMENT_PIN')
        cursor = end
    fence = rows[0]['replacementUtf8'].encode()
    if len(fence) != 197 or sha(fence) != FENCE_SHA: raise Refused('ONE_PROPERTY_FENCE')


def prepare_inputs(held):
    raw = held.admit(PLAN, 'approved-composition-plan', {'bytes': 23596, 'sha256': PLAN_SHA}, 65536)
    plan = json.loads(raw)
    if plan['composedEditCount'] != 11 or plan['currentNativeV2Covered'] is not False:
        raise Refused('PLAN_PROFILE')
    evidence = {}
    for name, expected in plan['evidencePins'].items():
        evidence[name] = held.admit(name, 'literal-component-evidence', expected)
    for original, row in plan['historicalNativeProfileMapping'].items():
        if row['snapshotPath'] != 'out/guest-private-image-preparation/history/pre-v2-source/'+original:
            raise Refused('HISTORICAL_PROFILE_PATH')
        held.admit(row['snapshotPath'], 'historical-v1-native-profile', {k: row[k] for k in ['bytes', 'sha256']})
    source = evidence[SOURCE]
    rows = plan['edits']
    validated_rows(source, rows)
    prop = json.loads(evidence[PROPERTY_RECEIPT])['candidateProofs']['guest_start.sh']
    ns = json.loads(evidence[NAMESPACE_RECEIPT])['candidate']
    components = {'property': (prop['edits'], evidence[prop['candidate'].replace('\\', '/')]),
                  'namespace': (ns['edits'], evidence[ns['path']])}
    matched = {'property': set(), 'namespace': set()}
    for row in rows:
        records, candidate = components[row['component']]
        matches = [r for r in records if (r.get('start', r.get('sourceStart')), r.get('end', r.get('sourceEnd')), r['kind'])
                   == (row['start'], row['end'], row['kind'])]
        if len(matches) != 1: raise Refused('COMPONENT_ROW_IDENTITY')
        item = matches[0]
        if candidate[item['candidateStart']:item['candidateEnd']] != row['replacementUtf8'].encode():
            raise Refused('COMPONENT_REPLACEMENT')
        matched[row['component']].add((row['start'], row['end']))
    if len(matched['property']) != 8 or matched['namespace'] != set(RANGES[1:4]):
        raise Refused('COMPONENT_COVERAGE')
    # The only omitted component row is the namespace's redundant entry fence.
    if len(prop['edits']) != 8 or len(ns['edits']) != 4: raise Refused('COMPONENT_COVERAGE')
    if not any(r['sourceStart'] == r['sourceEnd'] == 17 for r in ns['edits']):
        raise Refused('NAMESPACE_ENTRY_COLLISION')
    return source, plan


def review_gate(held, path, tool_sha):
    raw = held.admit(path, 'emission-gate', limit=65536)
    gate = json.loads(raw)
    if set(gate) != {'schema', 'sourceToolSha256', 'sourcePlanSha256', 'sourceReview', 'rootDecision'}:
        raise Refused('GATE_SCHEMA')
    if gate['schema'] != 'guest-start-composition-review/v1' or gate['sourceToolSha256'] != tool_sha or gate['sourcePlanSha256'] != PLAN_SHA:
        raise Refused('GATE_BINDING')
    for role, status in [('sourceReview', 'SOURCE_PASS'), ('rootDecision', 'ONE_PC_EMIT_GO')]:
        ref = gate[role]
        if set(ref) != {'path', 'sha256'}: raise Refused('GATE_REFERENCE')
        proof_raw = held.admit(ref['path'], role, limit=65536)
        if sha(proof_raw) != ref['sha256']: raise Refused('GATE_REFERENCE_PIN')
        proof = json.loads(proof_raw)
        if proof.get('status') != status or proof.get('sourceToolSha256') != tool_sha or proof.get('sourcePlanSha256') != PLAN_SHA:
            raise Refused('GATE_REFERENCE_BINDING')


def forward(source, rows):
    validated_rows(source, rows)
    result = bytearray(); cursor = 0; mapping = []
    for row in rows:
        result.extend(source[cursor:row['start']]); start = len(result)
        result.extend(row['replacementUtf8'].encode())
        if (start, len(result)) != (row['plannedCandidateStart'], row['plannedCandidateEnd']):
            raise Refused('PLANNED_SOURCE_COORDINATE_MAPPING')
        mapping.append({**row, 'candidateStart': start, 'candidateEnd': len(result)})
        cursor = row['end']
    result.extend(source[cursor:])
    return bytes(result), mapping


def inverse(source, rows, candidate):
    expected, mapping = forward(source, rows)
    if candidate != expected: raise Refused('FOREIGN_CANDIDATE_BYTES')
    restored = bytearray(candidate)
    for row in reversed(mapping):
        restored[row['candidateStart']:row['candidateEnd']] = source[row['start']:row['end']]
    if bytes(restored) != source: raise Refused('INVERSE')
    return bytes(restored)


def preservation(source, candidate, mapping):
    original = target = 0
    for row in mapping:
        if source[original:row['start']] != candidate[target:row['candidateStart']]:
            raise Refused('FOREIGN_GAP_BYTES')
        original, target = row['end'], row['candidateEnd']
    if source[original:] != candidate[target:]: raise Refused('FOREIGN_GAP_BYTES')


def negatives(source, rows, candidate):
    fence = rows[0]['replacementUtf8'].encode()
    foreign = bytearray(candidate); foreign[2] ^= 1
    changed = bytearray(candidate); changed[candidate.index(b'exit 2\n')+5] = ord('0')
    duplicate = candidate[:17]+fence+candidate[17:]
    cases = [('foreign-original-gap-byte', bytes(foreign)),
             ('changed-exit-zero-with-truthful-untrusted-seal', bytes(changed)),
             ('duplicate-entry-fence', duplicate)]
    rejected = []
    for name, data in cases:
        if sha(data) == sha(candidate): raise Refused('NEGATIVE_SETUP')
        try: inverse(source, rows, data)
        except Refused: rejected.append(name)
        else: raise Refused('NEGATIVE_FAILED')
    try: forward(source, [*rows[:2], rows[1], *rows[2:]])
    except Refused: rejected.append('unlisted-colliding-source-row')
    else: raise Refused('NEGATIVE_FAILED')
    return rejected


def work_dir():
    if not (ROOT/'out').resolve(strict=True).is_relative_to(ROOT): raise Refused('OUTPUT_CONTAINMENT')
    OUT.mkdir(exist_ok=True)
    if OUT.is_symlink() or not OUT.resolve(strict=True).is_relative_to((ROOT/'out').resolve(strict=True)):
        raise Refused('OUTPUT_CONTAINMENT')
    work = OUT/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex)
    work.mkdir(exist_ok=False)
    return work


def run(emit_path=None):
    tool_bytes = Path(__file__).read_bytes(); tool_sha = sha(tool_bytes)
    held = Inputs(); source, plan = prepare_inputs(held)
    if emit_path is not None: review_gate(held, emit_path, tool_sha)
    work = work_dir()
    value = {'schema': 'guest-start-disabled-composition/v1', 'status': 'SOURCE_PLAN_ONLY_NO_COMBINED_CANDIDATE',
             'toolSha256': tool_sha, 'sourcePlanSha256': PLAN_SHA, 'sourceSha256': SOURCE_SHA,
             'admittedInputs': held.snapshot(), 'selected': False, 'bootable': False,
             'runtimeOwnerImplemented': False, 'currentNativeV2Covered': False,
             'scriptsExecuted': False, 'phoneActions': False, 'oldComponentFilesModified': False,
             'sharedEntryFence': {'sha256': FENCE_SHA, 'bytes': 197, 'count': 1},
             'deferredChildShellLine888Wired': False, 'adjacentKillsJobsAndControlsAssembled': False,
             'remainingRealOwners': plan['remainingRealOwners'],
             'existingOneOsPermissiveAndPrivappLimitationsAllowed': True, 'stockEquivalenceRequired': False,
             'baselineCheckpoint': {'historicalOnly': True, **plan['baseline']}}
    try:
        (work/'source-plan.json').write_bytes(encoded(plan))
        if emit_path is not None:
            value['status'] = 'FAILED_SOURCE_EMISSION'
            candidate, mapping = forward(source, plan['edits'])
            fence = plan['edits'][0]['replacementUtf8'].encode()
            if len(candidate) != 77170 or not candidate.startswith(b'#!/system/bin/sh\n'+fence) or candidate.count(fence) != 1 or candidate.count(b'retained_property_refuse() {\n') != 1:
                raise Refused('ONE_UNCONDITIONAL_ENTRY_FENCE')
            preservation(source, candidate, mapping)
            path = work/'guest_start.sh.candidate.sh.disabled'; path.write_bytes(candidate)
            saved = path.read_bytes(); restored = inverse(source, plan['edits'], saved)
            reapplied, _ = forward(restored, plan['edits'])
            if reapplied != saved: raise Refused('SAVED_REAPPLY')
            diff = ''.join(difflib.unified_diff(source.decode('utf-8').splitlines(True), saved.decode('utf-8').splitlines(True), fromfile='a/guest_start.sh', tofile='b/guest_start.sh'))
            (work/'guest_start.sh.diff').write_bytes(diff.encode())
            value['candidate'] = {'path': path.relative_to(ROOT).as_posix(), **pin(saved), 'edits': mapping,
                                  'restoredOriginalSha256': sha(restored), 'inverseExact': restored == source,
                                  'savedReapplyExact': reapplied == saved, 'outsideEditsPreserved': True}
            value['negativeCasesRejected'] = negatives(source, plan['edits'], saved)
            value['status'] = 'PASS_SOURCE_ONLY_DISABLED_COMPOSITION'
    except Exception as error:
        value['status'] = 'FAILED_SOURCE_EMISSION' if emit_path is not None else 'FAILED_SOURCE_PLAN'
        value['failure'] = type(error).__name__
        raise
    finally:
        try:
            held.recheck()
            if Path(__file__).read_bytes() != tool_bytes: raise Refused('TOOL_MOVED')
            value['allAdmittedInputsAndToolUnchanged'] = True
        except Exception as error:
            value['allAdmittedInputsAndToolUnchanged'] = False
            value['recheckFailure'] = type(error).__name__
            value['status'] = 'FAILED_INPUT_MOVED'
        (work/'receipt.json').write_bytes(encoded(value))
    if value['status'].startswith('FAILED'): raise Refused('NO_COHERENT_EMISSION')
    if emit_path is not None and value['status'] == 'PASS_SOURCE_ONLY_DISABLED_COMPOSITION':
        (ROOT/'inventory/guest-start-composition.json').write_bytes(encoded({**value,
            'receipt': (work/'receipt.json').relative_to(ROOT).as_posix(), 'receiptSha256': sha((work/'receipt.json').read_bytes())}))
    print(json.dumps({'status': value['status'], 'receipt': (work/'receipt.json').relative_to(ROOT).as_posix(),
                      'receiptSha256': sha((work/'receipt.json').read_bytes()), 'candidateScripts': int(emit_path is not None)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--plan', action='store_true')
    group.add_argument('--emit', type=Path, help='Independent source review plus root one-PC-emission gate; never runtime admission')
    args = parser.parse_args()
    run(args.emit)


if __name__ == '__main__': main()
