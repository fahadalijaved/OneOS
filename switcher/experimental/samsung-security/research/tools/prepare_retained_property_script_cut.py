"""Exact SOURCE-ONLY property-writer retirement; never execute a shell/script.

Default/--plan writes metadata only. --emit requires separate source review and
one root PC-emission decision. Every output script is unselected and exit2 fenced.
"""
import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import re
import uuid

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'firmware/installed-oneos-code-profile/static/assets'
OUT = ROOT/'out/retained-property-script-cut'
PINS = {
    'guest_props.sh': (63145, 'f8164fd19314936cabb11bfa73f3038e6a85f0a62f57c2feec9d4b37df27083a'),
    'oneos_switch.sh': (228581, 'e0433f913856b3fbe775ffc1768948a4581434111eab79a21df1f1c443809150'),
    'guest_prepare.sh': (278725, '000d0a168d6d32ad08f6905df0b7424a241bb7029a8dc43c2fe292189d7a2d70'),
    'guest_start.sh': (78054, '896b72cc5bafadf975e29c05da0280e92b56a8f508c378d2c24e25a2b7f30446'),
    'return_to_oneui.sh': (55872, '04eec2a0b855ddbb89035b6c2d7daeb086e7a094a31be274c3213f79a89b0a03'),
}
APPROVED_PROPOSAL_SHA = '9323fde352471573454f266248c1e14571971ef04ff3842796d7f1afa873f9df'
# Same approved structure serialized as explicit LF bytes, not Windows text CRLF.
PLAN_SHA = 'cc74c34c5b6ead3e4031faa33a2ff587bebc5267592a3776ca5c7a7da325d869'
COUNTS = {'guest_props.sh': 1, 'oneos_switch.sh': 47, 'guest_prepare.sh': 4,
          'guest_start.sh': 8, 'return_to_oneui.sh': 34}
SHEBANG = b'#!/system/bin/sh\n'
FENCE = (b'# SOURCE-ONLY: no runtime owner/consumer cohort is assembled.\n'
         b'retained_property_refuse() {\n'
         b'    printf \'%s\\n\' \'SOURCE_ONLY_RETAINED_PROPERTY_OWNER_UNBOUND\' >&2\n'
         b'    exit 2\n'
         b'}\n'
         b'retained_property_refuse\n')
HELPER = (SHEBANG + b'# SOURCE-ONLY retired property API; every operation refuses.\n'
          b'printf \'%s\\n\' \'SOURCE_ONLY_GUEST_PROPERTY_MUTATION_API_RETIRED\' >&2\n'
          b'exit 2\n')
WRAPPER = (b'set_prop() {\n'
           b'    retained_property_refuse "removed shared property setter" "$@"\n'
           b'}\n')
PATTERNS = ((rb'(?<![A-Za-z0-9_])setprop(?=[ \t])', 'refuse-direct-setprop-data-or-control'),
            (rb'"\$RP"(?=[ \t]+(?:-[np](?:[ \t]|$)|--delete(?:[ \t]|$)))',
             'refuse-direct-resetprop-write-or-delete'))


class Refused(ValueError): pass


def digest(data): return hashlib.sha256(data).hexdigest()
def file_sha(path): return digest(Path(path).read_bytes())
def encoded(value): return (json.dumps(value, indent=2)+'\n').encode()


def read_sources():
    result = {}
    for name, (length, expected) in PINS.items():
        data = (BASE/name).read_bytes()
        if len(data) != length or digest(data) != expected:
            raise Refused('SOURCE_PROFILE')
        if not data.startswith(SHEBANG) or b'retained_property_refuse' in data:
            raise Refused('SOURCE_STRUCTURE')
        result[name] = data
    return result


def wrapper_range(data):
    start_word = b'set_prop() {\n'
    if data.count(start_word) != 1:
        raise Refused('AMBIGUOUS_WRAPPER')
    start = data.index(start_word)
    end = data.find(b'\n}\n', start)
    if end < start:
        raise Refused('SOURCE_STRUCTURE')
    return start, end+3


def row(data, kind, start, end, first=None, last=None):
    if first is None:
        first = data[:start].count(b'\n')+1
    if last is None:
        last = first
    return {'kind': kind, 'start': start, 'end': end, 'lines': [first, last],
            'sourceSpanSha256': digest(data[start:end])}


def source_edits(name, data):
    if name == 'guest_props.sh':
        return [row(data, 'retire-complete-mutation-helper', 0, len(data), 1, len(data.splitlines()))]
    edits = [row(data, 'mandatory-source-only-entry-refusal', len(SHEBANG), len(SHEBANG), 2, 2)]
    block = None
    if name == 'oneos_switch.sh':
        block = wrapper_range(data)
        edits.append(row(data, 'retire-set_prop-wrapper-to-explicit-refusal', *block,
                         data[:block[0]].count(b'\n')+1, data[:block[1]].count(b'\n')))
    offset = 0
    for line_number, line in enumerate(data.splitlines(keepends=True), 1):
        if not line.lstrip().startswith(b'#'):
            for pattern, kind in PATTERNS:
                for match in re.finditer(pattern, line):
                    start, end = offset+match.start(), offset+match.end()
                    if block and block[0] <= start < block[1]:
                        continue
                    edits.append(row(data, kind, start, end, line_number, line_number))
        offset += len(line)
    return sorted(edits, key=lambda item: (item['start'], item['end']))


def source_plan(sources):
    if list(sources) != list(PINS):
        raise Refused('SOURCE_PROFILE')
    cohort = {}
    for name, data in sources.items():
        if (len(data), digest(data)) != PINS[name]:
            raise Refused('SOURCE_PROFILE')
        edits = source_edits(name, data)
        if len(edits) != COUNTS[name]:
            raise Refused('CUT_COUNT')
        last = 0
        for edit in edits:
            if not last <= edit['start'] <= edit['end'] <= len(data):
                raise Refused('OVERLAPPING_CUT')
            last = edit['end']
        cohort[name] = {'sourceBytes': len(data), 'sourceSha256': digest(data),
                        'editCount': len(edits), 'edits': edits}
    result = {'status': 'SOURCE_API_PROPOSAL_ONLY_NO_CANDIDATE_EMITTED', 'cohort': cohort,
              'phoneActions': False, 'scriptsExecuted': False}
    if digest(encoded(result)) != PLAN_SHA:
        raise Refused('APPROVED_CUT_PLAN')
    return result


def replacement(kind):
    return {'retire-complete-mutation-helper': HELPER,
            'mandatory-source-only-entry-refusal': FENCE,
            'retire-set_prop-wrapper-to-explicit-refusal': WRAPPER,
            'refuse-direct-setprop-data-or-control': b'retained_property_refuse',
            'refuse-direct-resetprop-write-or-delete': b'retained_property_refuse'}[kind]


def forward(source, edits):
    result = bytearray(); cursor = 0; mapping = []
    for edit in edits:
        start, end = edit['start'], edit['end']
        if not cursor <= start <= end <= len(source) or digest(source[start:end]) != edit['sourceSpanSha256']:
            raise Refused('CUT_RANGE')
        result.extend(source[cursor:start]); target_start = len(result)
        result.extend(replacement(edit['kind'])); target_end = len(result)
        mapping.append({**edit, 'candidateStart': target_start, 'candidateEnd': target_end})
        cursor = end
    result.extend(source[cursor:])
    return bytes(result), mapping


def inverse(source, edits, candidate):
    expected, mapping = forward(source, edits)
    if candidate != expected:
        raise Refused('FOREIGN_CANDIDATE_BYTES')
    restored = bytearray(candidate)
    for edit in reversed(mapping):
        restored[edit['candidateStart']:edit['candidateEnd']] = source[edit['start']:edit['end']]
    if bytes(restored) != source:
        raise Refused('INVERSE')
    return bytes(restored)


def preservation(source, candidate, mapping):
    source_cursor = target_cursor = 0
    for edit in mapping:
        if source[source_cursor:edit['start']] != candidate[target_cursor:edit['candidateStart']]:
            raise Refused('FOREIGN_UNEDITED_BYTES')
        source_cursor, target_cursor = edit['end'], edit['candidateEnd']
    if source[source_cursor:] != candidate[target_cursor:]:
        raise Refused('FOREIGN_UNEDITED_BYTES')
    return True


def work_dir():
    if not OUT.resolve().is_relative_to((ROOT/'out').resolve()) or not (ROOT/'out').resolve().is_relative_to(ROOT.resolve()):
        raise Refused('OUTPUT_CONTAINMENT')
    OUT.mkdir(parents=True, exist_ok=True)
    work = OUT/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex)
    work.mkdir(exist_ok=False)
    return work


def checked_json(path):
    path = Path(path)
    if path.is_symlink() or not path.resolve(strict=True).is_relative_to(ROOT.resolve()) or path.stat().st_size > 65536:
        raise Refused('REVIEW_PATH')
    with path.open('rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise Refused('REVIEW_SIZE')
    return json.loads(raw), digest(raw)


def emission_gate(path, tool_sha):
    gate, gate_sha = checked_json(path)
    if set(gate) != {'schema', 'sourceToolSha256', 'sourcePlanSha256', 'sourceReview', 'rootDecision'}:
        raise Refused('REVIEW_SCHEMA')
    if gate['schema'] != 'retained-property-script-cut-review/v1' or gate['sourceToolSha256'] != tool_sha or gate['sourcePlanSha256'] != PLAN_SHA:
        raise Refused('REVIEW_BINDING')
    references = {}
    for key, required in [('sourceReview', 'SOURCE_PASS'), ('rootDecision', 'ONE_PC_EMIT_GO')]:
        ref = gate[key]
        if set(ref) != {'path', 'sha256'}:
            raise Refused('REVIEW_REFERENCE')
        value, actual = checked_json(ROOT/ref['path'])
        if actual != ref['sha256'] or value.get('status') != required or value.get('sourceToolSha256') != tool_sha or value.get('sourcePlanSha256') != PLAN_SHA:
            raise Refused('REVIEW_REFERENCE')
        references[key] = {'path': str((ROOT/ref['path']).resolve().relative_to(ROOT)), 'sha256': actual}
    return {'path': str(Path(path).resolve().relative_to(ROOT)), 'sha256': gate_sha, 'references': references,
            'meaning': 'PC source-emission workflow only; no runtime authority/phone approval'}


def negatives(sources, plan, candidates):
    name = 'oneos_switch.sh'; source = sources[name]; edits = plan['cohort'][name]['edits']
    candidate = candidates[name]
    _, mapping = forward(source, edits)
    gaps = [(0, mapping[0]['candidateStart'])]
    for left, right in zip(mapping, mapping[1:]):
        gaps.append((left['candidateEnd'], right['candidateStart']))
    gaps.append((mapping[-1]['candidateEnd'], len(candidate)))
    index = next(i for start, end in gaps for i in range(start, end) if 65 <= candidate[i] <= 90 or 97 <= candidate[i] <= 122)
    altered = bytearray(candidate); altered[index] ^= 1; altered = bytes(altered)
    rejected = []
    try:
        inverse(source, edits, altered)
    except Refused:
        rejected.append('off-target-byte-in-supplied-candidate')
    else:
        raise Refused('NEGATIVE_FAILED')
    # Alter an EDITED span as a distinct case: change the explicit exit status,
    # then truthfully recompute its untrusted output seal. The inverse must
    # validate derived replacement bytes as well as unmodified source spans.
    resealed_bytes = bytearray(candidate)
    exit_word = candidate.index(b'exit 2\n', mapping[0]['candidateStart'], mapping[0]['candidateEnd'])
    resealed_bytes[exit_word+5] = ord('0')
    resealed_bytes = bytes(resealed_bytes)
    resealed = {'candidateSha256': digest(resealed_bytes)}
    if resealed['candidateSha256'] != digest(resealed_bytes):
        raise Refused('NEGATIVE_SETUP')
    try:
        inverse(source, edits, resealed_bytes)
    except Refused:
        rejected.append('foreign-candidate-with-recomputed-untrusted-seal')
    else:
        raise Refused('NEGATIVE_FAILED')
    start, end = wrapper_range(source)
    ambiguous = source+source[start:end]
    try:
        wrapper_range(ambiguous)
    except Refused:
        rejected.append('ambiguous-wrapper-refuses-instead-of-first-match')
    else:
        raise Refused('NEGATIVE_FAILED')
    return rejected


def run(emit_path=None):
    tool_sha = file_sha(Path(__file__))
    sources = read_sources(); plan = source_plan(sources)
    gate = emission_gate(emit_path, tool_sha) if emit_path is not None else None
    work = work_dir()
    value = {'schema': 'retained-property-script-cut/v1', 'status': 'SOURCE_PLAN_ONLY_NO_CANDIDATE',
             'selected': False, 'bootable': False, 'runtimeProducerWired': False,
             'scriptOrShellExecuted': False, 'phoneActions': False, 'propertiesWritten': False,
             'toolSha256': tool_sha, 'sourcePlanSha256': PLAN_SHA, 'plan': plan,
             'approvedRawProposalSha256': APPROVED_PROPOSAL_SHA,
             'existingOneOsPermissiveAndPrivappLimitationsAllowed': True, 'stockEquivalenceRequired': False,
             'sourceOnlyEntryFenceHasRuntimeOverride': False, 'approvedAdditiveKeys': [],
             'limits': ['Five exact source scripts only, not every native/background/transitive writer',
                        'Rescue/CE/hardware/init/global-control/native owner assembly remains unresolved',
                        'Original reads/guards outside edited spans preserved but candidates cannot run',
                        'Clock leaf composition, staged hashes/callers/producer wiring and legacy-session refusal remain selection prerequisites',
                        'No phone/OneOS file or property changed; source-only artifacts are not a launcher']}
    try:
        (work/'source-plan.json').write_bytes(encoded(plan))
        if gate is not None:
            value['status'] = 'FAILED_SOURCE_EMISSION'
            value['emissionWorkflow'] = gate
            candidates = {}; proof = {}
            for name, source in sources.items():
                edits = plan['cohort'][name]['edits']; candidate, mapping = forward(source, edits)
                if name == 'guest_props.sh':
                    if candidate != HELPER: raise Refused('HELPER_REFUSAL')
                elif not candidate.startswith(SHEBANG+FENCE):
                    raise Refused('ENTRY_REFUSAL')
                preservation(source, candidate, mapping)
                path = work/(name+'.candidate.sh.disabled'); path.write_bytes(candidate)
                saved = path.read_bytes()
                restored = inverse(source, edits, saved)
                reapplied, _ = forward(restored, edits)
                if reapplied != saved: raise Refused('SAVED_REAPPLY')
                diff = ''.join(difflib.unified_diff(source.decode('utf-8').splitlines(True),
                           saved.decode('utf-8').splitlines(True), fromfile='a/'+name, tofile='b/'+name))
                (work/(name+'.diff')).write_bytes(diff.encode())
                candidates[name] = saved
                proof[name] = {'candidate': str(path.relative_to(ROOT)), 'candidateBytes': len(saved),
                               'candidateSha256': digest(saved), 'sourceSha256': digest(source),
                               'originalRestoredSha256': digest(restored), 'inverseExact': restored == source,
                               'actualSavedReapplyExact': reapplied == saved, 'outsideEditsPreserved': True,
                               'edits': mapping, 'shellOrScriptExecuted': False}
            value['negativeCasesRejected'] = negatives(sources, plan, candidates)
            value['candidateProofs'] = proof
            value['status'] = 'PASS_SOURCE_ONLY_DISABLED_COHORT'
    except Exception as error:
        value['failure'] = type(error).__name__
        raise
    finally:
        try:
            value['sourceInputsAfter'] = {name: {'bytes': (BASE/name).stat().st_size,
                'sha256': file_sha(BASE/name)} for name in PINS}
            value['sourceInputsUnchanged'] = all(
                (item['bytes'], item['sha256']) == PINS[name]
                for name, item in value['sourceInputsAfter'].items())
        except Exception as error:
            value['sourceInputsUnchanged'] = False
            value['inputRecheckFailure'] = type(error).__name__
        try:
            value['toolUnchanged'] = file_sha(Path(__file__)) == tool_sha
        except Exception:
            value['toolUnchanged'] = False
        value['reviewInputsUnchanged'] = True
        if gate is not None:
            review_refs = [{'path': gate['path'], 'sha256': gate['sha256']},
                           *gate['references'].values()]
            try:
                value['reviewInputsAfter'] = {ref['path']: checked_json(ROOT/ref['path'])[1]
                                             for ref in review_refs}
                value['reviewInputsUnchanged'] = all(
                    value['reviewInputsAfter'][ref['path']] == ref['sha256'] for ref in review_refs)
            except Exception as error:
                value['reviewInputsUnchanged'] = False
                value['reviewRecheckFailure'] = type(error).__name__
        if not value['sourceInputsUnchanged'] or not value['toolUnchanged'] or not value['reviewInputsUnchanged']:
            value['status'] = 'FAILED_INPUT_MOVED'
        receipt = work/'receipt.json'; receipt.write_bytes(encoded(value))
    if value['status'].startswith('FAILED'):
        raise Refused('NO_COHERENT_EMISSION')
    # Planning remains report-only; it cannot replace a successfully published
    # emitted-cohort inventory. Only one coherently gated successful emit publishes.
    if gate is not None and value['status'] == 'PASS_SOURCE_ONLY_DISABLED_COHORT':
        (ROOT/'inventory/retained-property-script-cut.json').write_bytes(encoded({**value,
            'receipt': str(receipt.relative_to(ROOT)), 'receiptSha256': file_sha(receipt)}))
    print(json.dumps({'status': value['status'], 'receipt': str(receipt.relative_to(ROOT)),
                      'receiptSha256': file_sha(receipt), 'candidateScripts': 5 if gate else 0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--plan', action='store_true')
    selection.add_argument('--emit', type=Path, help='Root-reviewed PC source-emission gate; never runtime permission')
    args = parser.parse_args()
    run(args.emit)


if __name__ == '__main__': main()
