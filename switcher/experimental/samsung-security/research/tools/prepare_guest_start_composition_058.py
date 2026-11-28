"""Pinned OneOS0.4.58 eleven-edit disabled source leaf; never execute shell/OEM code.

Default/--plan produces metadata only. --emit SOURCE_PASS.json emits a disabled
byte artifact after independent source review. Root already authorized these
reversible PC operations; source review is provenance, never runtime authority.
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
OUT = ROOT / 'out/guest-start-composition-058'
PLAN = 'out/guest-start-composition-058/PLAN.json'
PLAN_SHA = 'ba7d9f752f5b87fafc75047208e3fa13e05b1b952cfe443f655ec77b57919490'
OLD_PLAN = 'out/guest-start-composition-plan/composition-plan.json'
OLD_PLAN_SHA = 'e10e83f2c5beb51900f68c970d66e3f1902610a134cf015b908644d7832a3b7b'
SOURCE = ('firmware/upstream-oneos-0.4.58/45abb3df03cbd4a8b006519baaebefdb2c68658a/'
          'raw/45abb3df03cbd4a8b006519baaebefdb2c68658a/switcher/assets/guest_start.sh')
SOURCE_SHA = '81460c5f089a21d9684ae9023af9938392621c8296a093ec8045fac5c81482c2'
OLD_SOURCE_SHA = '896b72cc5bafadf975e29c05da0280e92b56a8f508c378d2c24e25a2b7f30446'
FENCE_SHA = '25e206db59319cd25177e667471aedb7736fa684d85364a66612d11a42253a5a'
GNSS_SHA = 'e9b20fb12f9c187ece250554f51c70e019026d2698ada4af7d4c8bc088e09144'
RANGES = [(17, 17), (468, 852), (1891, 2425), (3750, 4494),
          (10193, 10200), (11796, 11803), (13208, 13215), (34403, 34410),
          (52539, 52546), (70641, 70648), (72011, 72018)]
PROPERTY_RECEIPT = ('out/retained-property-script-cut/'
                  '20261106T072749384206Z-d3d76942c5ba4a9cb454863361008b6a/receipt.json')
NAMESPACE_RECEIPT = ('out/guest-start-namespace-cut/'
                   '20261106T094045555832Z-06595f2bae184bfd9bb57d6330c8bb44/receipt.json')
MAX_INPUT = 2 * 1024 * 1024


class Refused(ValueError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2) + '\n').encode('utf-8')


def pin(data):
    return {'bytes': len(data), 'sha256': sha(data)}


class Inputs:
    """Retain first admitted bytes; paths and duplicate roles never redefine pins."""
    def __init__(self):
        self.rows = {}
        self.identities = set()

    def bounded_read(self, path, limit=MAX_INPUT):
        path = Path(path)
        if path.is_symlink():
            raise Refused('SYMLINK_INPUT')
        canonical = path.resolve(strict=True)
        if not canonical.is_relative_to(ROOT) or not stat.S_ISREG(canonical.stat().st_mode):
            raise Refused('INPUT_CONTAINMENT_OR_TYPE')
        if canonical.stat().st_size > limit:
            raise Refused('INPUT_SIZE')
        with canonical.open('rb') as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise Refused('INPUT_SIZE')
        return canonical, data

    def admit(self, name, role, expected=None, limit=MAX_INPUT):
        canonical, data = self.bounded_read(ROOT / name, limit)
        identity = str(canonical).casefold()
        if identity in self.identities:
            raise Refused('DUPLICATE_INPUT_OR_ROLE_PATH')
        if expected is not None and pin(data) != expected:
            raise Refused('INPUT_PIN')
        self.identities.add(identity)
        key = canonical.relative_to(ROOT).as_posix()
        self.rows[key] = {'role': role, **pin(data), 'data': data}
        return data

    def metadata(self):
        return {n: {k: v for k, v in row.items() if k != 'data'}
                for n, row in self.rows.items()}

    def snapshot(self, work):
        for name, row in self.rows.items():
            target = work / 'executed-inputs' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(row['data'])
            if target.read_bytes() != row['data']:
                raise Refused('SNAPSHOT_BYTES')

    def recheck(self):
        for name, row in self.rows.items():
            canonical, data = self.bounded_read(ROOT / name)
            if canonical.relative_to(ROOT).as_posix() != name or data != row['data']:
                raise Refused('ADMITTED_INPUT_MOVED')


def validated_rows(source, rows):
    if pin(source) != {'bytes': 78563, 'sha256': SOURCE_SHA}:
        raise Refused('SOURCE_058_PROFILE')
    if [(r['start'], r['end']) for r in rows] != RANGES:
        raise Refused('UNLISTED_OR_COLLIDING_ROWS')
    cursor = 0
    for row in rows:
        start, end = row['start'], row['end']
        replacement = row['replacementUtf8'].encode('utf-8')
        if not cursor <= start <= end <= len(source):
            raise Refused('EDIT_OVERLAP')
        if sha(source[start:end]) != row['sourceSpanSha256']:
            raise Refused('SOURCE_SPAN')
        if pin(replacement) != {'bytes': row['replacementBytes'], 'sha256': row['replacementSha256']}:
            raise Refused('REPLACEMENT_PIN')
        cursor = end
    if pin(rows[0]['replacementUtf8'].encode('utf-8')) != {'bytes': 197, 'sha256': FENCE_SHA}:
        raise Refused('ONE_PROPERTY_FENCE')


def prepare_inputs(held):
    plan = json.loads(held.admit(PLAN, 'version-specific-plan',
                                {'bytes': 11571, 'sha256': PLAN_SHA}, 65536))
    old = json.loads(held.admit(OLD_PLAN, 'historical-approved-eleven-edit-plan',
                               {'bytes': 23596, 'sha256': OLD_PLAN_SHA}, 65536))
    if (plan['schema'] != 'guest-start-disabled-composition-058-plan/v1'
            or plan['edits'] != old['edits'] or old['composedEditCount'] != 11
            or plan['expectedCandidateBytes'] != 77679
            or plan['currentNativeV2Covered'] is not False
            or plan['currentNativeV3Covered'] is not False):
        raise Refused('PLAN_PROFILE_OR_CHANGED_OLD_SEMANTICS')
    evidence = {}
    for name, expected in old['evidencePins'].items():
        evidence[name] = held.admit(name, 'literal-historical-component-evidence', expected)
    for original, row in old['historicalNativeProfileMapping'].items():
        if row['snapshotPath'] != 'out/guest-private-image-preparation/history/pre-v2-source/' + original:
            raise Refused('HISTORICAL_V1_PATH')
        held.admit(row['snapshotPath'], 'historical-v1-only-not-current-native-admission',
                   {k: row[k] for k in ('bytes', 'sha256')})
    extra = {name: held.admit(name, 'literal-058-or-historical-provenance', expected)
             for name, expected in plan['extraEvidencePins'].items()}
    source = extra[SOURCE]
    parent = extra[plan['parentSource']['path']]
    if pin(parent) != {'bytes': 78054, 'sha256': OLD_SOURCE_SHA}:
        raise Refused('PARENT_PROFILE')
    inserted = source[72411:72920]
    if (pin(inserted) != {'bytes': 509, 'sha256': GNSS_SHA}
            or source != parent[:72411] + inserted + parent[72411:]):
        raise Refused('WHOLE_UPSTREAM_DELTA')
    index = json.loads(extra['out/upstream-oneos-0.4.58-pin/SOURCE-INDEX.json'])
    hits = [r for r in index['files'] if r['revision'] == plan['revision']
            and r['repositoryPath'] == 'switcher/assets/guest_start.sh']
    if (len(hits) != 1 or hits[0]['localPath'] != SOURCE
            or hits[0]['sha256'] != SOURCE_SHA or hits[0]['bytes'] != len(source)):
        raise Refused('UPSTREAM_INDEX_BINDING')
    validated_rows(source, plan['edits'])
    prop = json.loads(evidence[PROPERTY_RECEIPT])['candidateProofs']['guest_start.sh']
    ns = json.loads(evidence[NAMESPACE_RECEIPT])['candidate']
    components = {'property': (prop['edits'], evidence[prop['candidate'].replace('\\', '/')]),
                  'namespace': (ns['edits'], evidence[ns['path']])}
    matched = {'property': set(), 'namespace': set()}
    for row in plan['edits']:
        records, candidate = components[row['component']]
        matches = [r for r in records if
                   (r.get('start', r.get('sourceStart')), r.get('end', r.get('sourceEnd')), r['kind'])
                   == (row['start'], row['end'], row['kind'])]
        if len(matches) != 1:
            raise Refused('COMPONENT_ROW_IDENTITY')
        item = matches[0]
        if candidate[item['candidateStart']:item['candidateEnd']] != row['replacementUtf8'].encode('utf-8'):
            raise Refused('COMPONENT_REPLACEMENT')
        matched[row['component']].add((row['start'], row['end']))
    if (len(matched['property']) != 8 or matched['namespace'] != set(RANGES[1:4])
            or len(prop['edits']) != 8 or len(ns['edits']) != 4
            or not any(r['sourceStart'] == r['sourceEnd'] == 17 for r in ns['edits'])):
        raise Refused('COMPONENT_COVERAGE')
    old_actual = json.loads(extra[plan['oldActualReceipt']])
    old_candidate = extra[plan['oldActualCandidate']]
    if (old_actual['status'] != 'PASS_SOURCE_ONLY_DISABLED_COMPOSITION'
            or old_actual['sourcePlanSha256'] != OLD_PLAN_SHA
            or old_actual['toolSha256'] != '7d58f922f8a25a0f6661d4747fd2da43296c076422d64567b4712144116d9d48'
            or old_actual['candidate']['path'] != plan['oldActualCandidate']
            or pin(old_candidate) != {k: old_actual['candidate'][k] for k in ('bytes', 'sha256')}):
        raise Refused('OLD_ACTUAL_BINDING')
    return source, parent, plan, old_candidate


def source_review(held, path, tool_sha):
    raw = held.admit(path, 'independent-pre-use-source-review', limit=65536)
    proof = json.loads(raw)
    if (proof.get('status') != 'SOURCE_PASS'
            or proof.get('sourceToolSha256') != tool_sha
            or proof.get('sourcePlanSha256') != PLAN_SHA
            or proof.get('sourceSha256') != SOURCE_SHA):
        raise Refused('SOURCE_REVIEW_BINDING')
    return {'path': str(Path(path).as_posix()), **pin(raw)}


def forward(source, rows):
    validated_rows(source, rows)
    result = bytearray()
    cursor = 0
    mapping = []
    for row in rows:
        result.extend(source[cursor:row['start']])
        start = len(result)
        result.extend(row['replacementUtf8'].encode('utf-8'))
        if (start, len(result)) != (row['plannedCandidateStart'], row['plannedCandidateEnd']):
            raise Refused('PLANNED_SOURCE_COORDINATE_MAPPING')
        mapping.append({**row, 'candidateStart': start, 'candidateEnd': len(result)})
        cursor = row['end']
    result.extend(source[cursor:])
    return bytes(result), mapping


def inverse(source, rows, candidate):
    expected, mapping = forward(source, rows)
    if candidate != expected:
        raise Refused('FOREIGN_CANDIDATE_BYTES')
    restored = bytearray(candidate)
    for row in reversed(mapping):
        restored[row['candidateStart']:row['candidateEnd']] = source[row['start']:row['end']]
    if bytes(restored) != source:
        raise Refused('INVERSE')
    return bytes(restored)


def preservation(source, candidate, mapping, old_candidate):
    gaps = []
    original = target = 0
    for row in mapping:
        a, b = source[original:row['start']], candidate[target:row['candidateStart']]
        if a != b:
            raise Refused('FOREIGN_GAP_BYTES')
        gaps.append({'source': [original, row['start']], 'candidate': [target, row['candidateStart']], **pin(a)})
        original, target = row['end'], row['candidateEnd']
    if source[original:] != candidate[target:]:
        raise Refused('FOREIGN_GAP_BYTES')
    gaps.append({'source': [original, len(source)], 'candidate': [target, len(candidate)], **pin(source[original:])})
    projected = 72411 + sum(r['replacementBytes'] - (r['end'] - r['start']) for r in mapping)
    if (projected != 71527 or pin(candidate[projected:projected+509]) != {'bytes': 509, 'sha256': GNSS_SHA}
            or candidate != old_candidate[:projected] + source[72411:72920] + old_candidate[projected:]):
        raise Refused('GNSS_OR_OLD_COMPOSITION_RELATION')
    return {'gaps': gaps, 'gnss': {'source': [72411, 72920], 'candidate': [projected, projected+509],
                                 'bytes': 509, 'sha256': GNSS_SHA, 'exact': True},
            'equalsOldSavedCompositionPlusOnlyGnssInsertion': True}


def work_dir(base=OUT):
    """Validate output containment before any mkdir; no public output selector."""
    base = Path(base)
    out_root = (ROOT / 'out').resolve(strict=True)
    if (base.is_symlink() or not out_root.is_relative_to(ROOT)
            or not base.resolve(strict=False).is_relative_to(out_root)):
        raise Refused('OUTPUT_CONTAINMENT')
    base.mkdir(parents=True, exist_ok=True)
    if not base.resolve(strict=True).is_relative_to(out_root):
        raise Refused('OUTPUT_CONTAINMENT')
    work = base / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex)
    work.mkdir(exist_ok=False)
    return work


def negative_cases(source, parent, rows, candidate, work, held):
    results = []
    def refuses(name, expected, action):
        try:
            action()
        except Refused as error:
            if str(error) != expected:
                raise Refused('NEGATIVE_WRONG_REASON_' + name) from error
            results.append({'name': name, 'rejected': True, 'reason': str(error)})
        else:
            raise Refused('NEGATIVE_FAILED_' + name)
    bad_gap = bytearray(candidate)
    bad_gap[2] ^= 1
    bad_fence = bytearray(candidate)
    bad_fence[candidate.index(b'exit 2\n')+5] = ord('0')
    bad_gnss = bytearray(candidate)
    bad_gnss[71527+20] ^= 1
    fence = rows[0]['replacementUtf8'].encode('utf-8')
    candidates = [('foreign-original-gap-byte', bytes(bad_gap)),
                  ('changed-fence-exit-zero', bytes(bad_fence)),
                  ('duplicate-entry-fence', candidate[:17] + fence + candidate[17:]),
                  ('changed-gnss-candidate-gap', bytes(bad_gnss))]
    negatives = work / 'negatives'
    negatives.mkdir()
    for name, data in candidates:
        p = negatives / (name + '.sh.disabled')
        p.write_bytes(data)
        refuses(name, 'FOREIGN_CANDIDATE_BYTES', lambda: inverse(source, rows, p.read_bytes()))
        results[-1]['artifact'] = {'path': p.relative_to(ROOT).as_posix(), **pin(data)}
    refuses('wrong-057-base', 'SOURCE_058_PROFILE', lambda: validated_rows(parent, rows))
    mutated_source = bytearray(source)
    mutated_source[72411+20] ^= 1
    refuses('changed-gnss-source', 'SOURCE_058_PROFILE', lambda: validated_rows(bytes(mutated_source), rows))
    refuses('unlisted-colliding-source-row', 'UNLISTED_OR_COLLIDING_ROWS',
            lambda: forward(source, [*rows[:2], rows[1], *rows[2:]]))
    # Change actual admitted dependency bytes, not a synthetic ready marker.
    dependency_name = next(n for n, r in held.rows.items() if r['role'] == 'literal-historical-component-evidence'
                           and n.endswith('.candidate.sh.disabled'))
    dependency = held.rows[dependency_name]['data']
    bad_dependency = bytearray(dependency)
    bad_dependency[2] ^= 1
    fixture = negatives / 'substituted-real-component.sh.disabled'
    fixture.write_bytes(bad_dependency)
    refuses('substituted-real-component', 'INPUT_PIN', lambda: Inputs().admit(
        fixture.relative_to(ROOT).as_posix(), 'negative-substitution', pin(dependency)))
    results[-1]['artifact'] = {'path': fixture.relative_to(ROOT).as_posix(), **pin(bytes(bad_dependency))}
    refuses('input-path-escape', 'INPUT_CONTAINMENT_OR_TYPE',
            lambda: Inputs().admit('../AGENTS.md', 'negative-escape'))
    # This invokes the real output guard; the invalid target is checked before mkdir/write.
    refuses('output-path-escape-before-mkdir', 'OUTPUT_CONTAINMENT', lambda: work_dir(ROOT.parent))
    moving = negatives / 'held-input-movement.txt'
    moving.write_bytes(b'first admitted bytes\n')
    moved = Inputs()
    moved.admit(moving.relative_to(ROOT).as_posix(), 'negative-retained-input', pin(moving.read_bytes()))
    moving.write_bytes(b'changed after admission\n')
    refuses('held-input-movement', 'ADMITTED_INPUT_MOVED', moved.recheck)
    return results


def run(review_path=None, self_test=False):
    tool_bytes = Path(__file__).read_bytes()
    work = work_dir()
    held = Inputs()
    value = {'schema': 'guest-start-disabled-composition-058/v1', 'status': 'FAILED_INPUT_ADMISSION',
             'toolSha256': sha(tool_bytes), 'sourcePlanSha256': PLAN_SHA, 'sourceSha256': SOURCE_SHA,
             'selected': False, 'bootable': False, 'runtimeOwnerImplemented': False,
             'currentNativeV2Covered': False, 'currentNativeV3Covered': False,
             'scriptsExecuted': False, 'phoneActions': False, 'oldFilesModified': False,
             'sourceReviewIsProvenanceNotRuntimeAuthority': True,
             'rootPcAuthorization': 'Root approved new058 static producer/focused failures after independent source review; no extra root gate required.'}
    try:
        held.admit(Path(__file__).resolve().relative_to(ROOT).as_posix(), 'executed-producer-source', pin(tool_bytes))
        source, parent, plan, old_candidate = prepare_inputs(held)
        if review_path is not None:
            value['sourceReview'] = source_review(held, review_path, sha(tool_bytes))
        elif self_test:
            raise Refused('SOURCE_REVIEW_REQUIRED_FOR_TESTS')
        held.snapshot(work)
        value['snapshotsWrittenBeforeTransform'] = True
        value['remainingRealOwners'] = plan['remainingRealOwners']
        value['status'] = 'SOURCE_PLAN_ONLY_NO_CANDIDATE'
        if review_path is not None:
            value['status'] = 'FAILED_STATIC_TRANSFORM'
            candidate, mapping = forward(source, plan['edits'])
            fence = plan['edits'][0]['replacementUtf8'].encode('utf-8')
            if (len(candidate) != 77679 or not candidate.startswith(b'#!/system/bin/sh\n' + fence)
                    or candidate.count(fence) != 1 or candidate.count(b'retained_property_refuse() {\n') != 1):
                raise Refused('ONE_UNCONDITIONAL_ENTRY_FENCE')
            value['preservation'] = preservation(source, candidate, mapping, old_candidate)
            value['negativeCases'] = negative_cases(source, parent, plan['edits'], candidate, work, held)
            if not self_test:
                path = work / 'guest_start.058.candidate.sh.disabled'
                path.write_bytes(candidate)
                saved = path.read_bytes()
                restored = inverse(source, plan['edits'], saved)
                inverse_path = work / 'guest_start.058.inverse.sh.disabled'
                inverse_path.write_bytes(restored)
                reapplied, _ = forward(inverse_path.read_bytes(), plan['edits'])
                reapply_path = work / 'guest_start.058.reapply.sh.disabled'
                reapply_path.write_bytes(reapplied)
                if reapply_path.read_bytes() != saved or inverse_path.read_bytes() != source:
                    raise Refused('SAVED_INVERSE_REAPPLY')
                difference = ''.join(difflib.unified_diff(source.decode('utf-8').splitlines(True),
                    saved.decode('utf-8').splitlines(True), fromfile='a/guest_start.058.sh', tofile='b/guest_start.058.sh.disabled'))
                (work / 'guest_start.058.diff').write_bytes(difference.encode('utf-8'))
                value['candidate'] = {'path': path.relative_to(ROOT).as_posix(), **pin(saved), 'edits': mapping}
                value['inverse'] = {'path': inverse_path.relative_to(ROOT).as_posix(), **pin(restored), 'exactSource': True}
                value['reapply'] = {'path': reapply_path.relative_to(ROOT).as_posix(), **pin(reapplied), 'exactCandidate': True}
                value['status'] = 'PASS_SOURCE_ONLY_DISABLED_058_COMPOSITION'
            else:
                value['status'] = 'PASS_STATIC_NEGATIVES_ONLY_NO_PRIMARY_CANDIDATE'
    except Exception as error:
        value['status'] = 'FAILED_STATIC_SOURCE_OPERATION'
        value['failure'] = {'type': type(error).__name__, 'reason': str(error)}
    finally:
        value['admittedInputs'] = held.metadata()
        try:
            held.recheck()
            if Path(__file__).read_bytes() != tool_bytes:
                raise Refused('TOOL_MOVED')
            value['allAdmittedInputsAndToolUnchanged'] = True
        except Exception as error:
            value['allAdmittedInputsAndToolUnchanged'] = False
            value['recheckFailure'] = {'type': type(error).__name__, 'reason': str(error)}
            value['status'] = 'FAILED_INPUT_MOVED'
        (work / 'receipt.json').write_bytes(encoded(value))
    result = {'status': value['status'], 'receipt': (work / 'receipt.json').relative_to(ROOT).as_posix(),
              'receiptSha256': sha((work / 'receipt.json').read_bytes())}
    print(json.dumps(result))
    if value['status'].startswith('FAILED'):
        raise Refused('NO_COHERENT_SOURCE_ARTIFACT')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--plan', action='store_true')
    group.add_argument('--emit', type=Path, help='Exact independent SOURCE_PASS JSON; disabled artifact only')
    group.add_argument('--self-test', type=Path, help='Exact source review; only focused static failures')
    args = parser.parse_args()
    run(args.emit or args.self_test, args.self_test is not None)


if __name__ == '__main__':
    main()
