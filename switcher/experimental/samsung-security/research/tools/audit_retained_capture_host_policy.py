"""Bounded indexed Samsung policy extraction/static facts, never policy execution."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import runpy
import tarfile

ROOT = Path(__file__).resolve().parent.parent
PARENT = ROOT.parent
BASE = PARENT / 'out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84'
MANIFEST = BASE / 'samsung-manifest.jsonl.gz'
MANIFEST_SHA = '6654252d9f7bde941e367fe79eb9af541869f4a1ddb5d1b8a0f0d4d6dde57a7a'
REPORT_SHA = 'c1785505f9f01ac922c48dc31e3fd8e2489630a9730489fc5bd27dcfaf9a8733'
ARCHIVE = PARENT / 'firmware/samsung/os-mirror-20261104/mounted-os-20261104T235732022961Z.tar'
ARCHIVE_SHA = '28eb27547fcc96348aa54f614a77aecd8bfcdbf875b61de2dd5279787985d96e'
RAW = ROOT / 'firmware/retained-capture-host-policy'
WORK = ROOT / 'out/retained-capture-host-policy'
WANTED = tuple(part + '/etc/selinux/' + name for part, names in [
    ('system', ('plat_file_contexts', 'plat_sepolicy.cil')),
    ('system_ext', ('system_ext_file_contexts', 'system_ext_sepolicy.cil')),
    ('product', ('product_file_contexts', 'product_sepolicy.cil')),
    ('vendor', ('vendor_file_contexts', 'vendor_sepolicy.cil')),
    ('odm', ('odm_file_contexts', 'odm_sepolicy.cil'))] for name in names)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def snapshot(path):
    s = path.stat()
    return dict(zip(['dev', 'ino', 'bytes', 'mtimeNs', 'ctimeNs'], [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]))


def indexed():
    assert sha(MANIFEST) == MANIFEST_SHA and sha(BASE / 'report.json') == REPORT_SHA
    report = json.loads((BASE / 'report.json').read_text())
    assert report['samsungArchiveSha256'] == ARCHIVE_SHA
    found = {}
    with gzip.open(MANIFEST, 'rt') as stream:
        for text in stream:
            row = json.loads(text)
            if row['path'] in WANTED:
                assert row['kind'] == 'file' and row['path'] not in found and 0 <= row['size'] <= 4 * 1024 * 1024
                found[row['path']] = row
    assert set(found) == set(WANTED) and sum(x['size'] for x in found.values()) <= 8 * 1024 * 1024
    return found


class BudgetFile:
    """Unbuffered archive reads, separate header/extension and selected-body caps."""
    def __init__(self, file, size):
        self.file, self.size = file, size
        self.mode = 'header'
        self.count = {'header': 0, 'selected': 0}
        self.cap = {'header': 32 * 1024 * 1024, 'selected': 8 * 1024 * 1024}

    def read(self, length=-1):
        assert 0 <= length <= self.cap[self.mode] - self.count[self.mode], 'bounded TAR read refused'
        data = self.file.read(length)
        self.count[self.mode] += len(data)
        return data

    def tell(self):
        return self.file.tell()

    def seek(self, offset, whence=0):
        target = offset if whence == 0 else self.tell() + offset if whence == 1 else self.size + offset
        assert 0 <= target <= self.size
        return self.file.seek(target)


def extract():
    expected = indexed()
    before = snapshot(ARCHIVE)
    assert before['bytes'] == 20434769920
    strict_path = PARENT / 'tools/Strict-MountedTar.py'
    assert sha(strict_path) == '3515037292dc3d748e0c57a23bb19f183c26ea91d66332fae893bd461ae47c5b'
    strict = runpy.run_path(str(strict_path))['MountedTar'](list(json.loads((BASE / 'report.json').read_text())['capturedRoots']))
    records, walked = {}, 0
    with ARCHIVE.open('rb', buffering=0) as file:
        bounded = BudgetFile(file, before['bytes'])
        with tarfile.open(fileobj=bounded, mode='r:') as archive:
            for member in archive:
                walked += 1
                assert walked <= 20000 and len(member.name.encode('utf-8')) <= 4096
                strict.member(member)
                name = member.name.removeprefix('./')
                if name not in expected:
                    continue
                index = expected[name]
                assert name not in records and member.isfile() and member.size == index['size']
                bounded.seek(member.offset_data)
                bounded.mode = 'selected'
                data = bounded.read(member.size)
                bounded.mode = 'header'
                assert len(data) == index['size'] and hashlib.sha256(data).hexdigest() == index['sha256']
                target = RAW / name
                assert RAW.resolve() in target.resolve().parents
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                records[name] = {'path': str(target.relative_to(ROOT)), 'bytes': len(data), 'sha256': index['sha256'],
                                 'archiveHeaderOffset': member.offset, 'archiveDataOffset': member.offset_data}
                if set(records) == set(WANTED):
                    break
        counts = dict(bounded.count)
    assert set(records) == set(WANTED) and snapshot(ARCHIVE) == before
    assert sha(MANIFEST) == MANIFEST_SHA and sha(BASE / 'report.json') == REPORT_SHA
    WORK.mkdir(parents=True, exist_ok=True)
    producer_dir = WORK / 'producers'
    producer_dir.mkdir(exist_ok=True)
    producer_sha = sha(Path(__file__))
    (producer_dir / (producer_sha + '.py')).write_bytes(Path(__file__).read_bytes())
    result = {'schema': 'retained-capture-host-policy-selected-extraction/v1',
              'archive': str(ARCHIVE), 'priorCaptureSha256': ARCHIVE_SHA, 'freshWholeArchiveHashPerformed': False,
              'archiveStatBeforeAfter': before, 'manifestSha256': MANIFEST_SHA, 'comparisonReceiptSha256': REPORT_SHA,
              'headerRecordsVisited': walked, 'readBytes': counts, 'caps': {'headerAndExtensionBytes': 33554432, 'selectedBodyBytes': 8388608},
              'selected': records, 'toolSha256': producer_sha, 'policyExecuted': False, 'phoneActions': [],
              'limits': 'Selected data/hash/header binding only; prior full-stream framing/hash reused, no new complete archive validation.'}
    (WORK / 'extraction.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'selected': len(records), 'headers': walked, 'readBytes': counts}))


def audit():
    expected = indexed()
    receipt_path = WORK / 'extraction.json'
    receipt = json.loads(receipt_path.read_text())
    producer = WORK / 'producers' / (receipt['toolSha256'] + '.py')
    assert sha(producer) == receipt['toolSha256']
    checks = []
    def check(name, value):
        assert value, name
        checks.append(name)
    check('bounded saved header/extension reads', receipt['readBytes']['header'] <= 32 * 1024 * 1024)
    check('bounded saved selected member reads', receipt['readBytes']['selected'] <= 8 * 1024 * 1024)
    check('no fresh20GB rehash or policy execution', not receipt['freshWholeArchiveHashPerformed'] and not receipt['policyExecuted'])
    check('ten exact index-selected policy/context members', set(receipt['selected']) == set(WANTED))
    for name, row in receipt['selected'].items():
        check('selected member ' + name, sha(ROOT / row['path']) == expected[name]['sha256'] == row['sha256'] and
              (ROOT / row['path']).stat().st_size == expected[name]['size'] == row['bytes'])
    platform = RAW / 'system/etc/selinux/plat_sepolicy.cil'
    lines = platform.read_text().splitlines()
    direct = []
    raw_facts = []
    for number, text in enumerate(lines, 1):
        match = re.fullmatch(r'\(allow system_server system_data_file \((dir|file) \(([^()]*)\)\)\)', text)
        if match:
            permissions = match[2].split()
            direct.append({'member': 'system/etc/selinux/plat_sepolicy.cil', 'line': number,
                           'source': 'system_server', 'target': 'system_data_file', 'class': match[1], 'permissions': permissions})
            raw_facts.append({'member': 'system/etc/selinux/plat_sepolicy.cil', 'line': number, 'text': text})
    for kind, permissions in [('dir', {'getattr', 'open', 'read', 'search'}), ('file', {'getattr', 'open', 'read'})]:
        check('explicit source allow system_server system_data_file ' + kind,
              any(row['class'] == kind and permissions <= set(row['permissions']) for row in direct))
    domain = next((n, text) for n, text in enumerate(lines, 1) if text.startswith('(typeattributeset domain ('))
    check('system_server member of domain source attribute', 'system_server' in re.findall(r'[\w]+', domain[1]))
    root_rule = next((n, text) for n, text in enumerate(lines, 1) if text.startswith('(allow domain system_data_root_file (dir '))
    check('parent data-root source allow getattr/search', 'getattr' in root_rule[1] and 'search' in root_rule[1])
    constraints = [{'member': 'system/etc/selinux/plat_sepolicy.cil', 'line': n, 'text': text}
                   for n, text in enumerate(lines, 1) if text.startswith('(mlsconstrain (') and
                   any(text.startswith('(mlsconstrain (' + k + ' ') for k in ('dir', 'file')) and
                   any(' ' + p in text for p in ('read', 'open', 'search', 'getattr'))]
    check('relevant MLS constraints retained as unevaluated source evidence', len(constraints) >= 4)
    raw_facts += [{'member': 'system/etc/selinux/plat_sepolicy.cil', 'line': root_rule[0], 'text': root_rule[1]}] + constraints
    target = '/data/system/oneos-samsung-security-capture'
    matches, errors, pattern_count = [], [], 0
    for name in WANTED:
        if not name.endswith('file_contexts'):
            continue
        for number, text in enumerate((RAW / name).read_text().splitlines(), 1):
            stripped = text.strip()
            if not stripped or stripped.startswith('#'):
                continue
            tokens = stripped.split()
            if len(tokens) not in (2, 3):
                errors.append({'member': name, 'line': number, 'reason': 'fields'})
                continue
            try:
                pattern = re.compile(tokens[0])
            except re.error:
                errors.append({'member': name, 'line': number, 'reason': 'Python regex unsupported'})
                continue
            pattern_count += 1
            for path in [target, target + '/request-v1']:
                if pattern.fullmatch(path):
                    matches.append({'member': name, 'line': number, 'pattern': tokens[0],
                                    'kindSelector': tokens[1] if len(tokens) == 3 else None,
                                    'context': tokens[-1], 'candidatePath': path})
    check('all captured context patterns accepted by bounded textual Python-re filter', not errors)
    check('only one textual context candidate per v2 path, both system_data_file',
          len(matches) == 2 and all(x['context'] == 'u:object_r:system_data_file:s0' and
                                    x['member'] == 'system/etc/selinux/plat_file_contexts' and x['line'] == 490 for x in matches))
    old = ROOT / 'out/retained-capture-permit-access/FROZEN-MANIFEST.json'
    check('old access snapshot untouched', sha(old) == '76b9e51d1eafffcfcb648d0cdc22046b58930380f67ca337b512671061ce746b')
    for name, pin in json.loads(old.read_text())['entries'].items():
        check('old snapshot entry unchanged ' + name, sha(ROOT / name) == pin)
    fact_path = RAW / 'selected-policy-source-facts.json'
    fact_path.write_text(json.dumps({'schema': 'retained-capture-host-policy-raw-facts/v1', 'facts': raw_facts}, indent=2) + '\n')
    result = {'schema': 'retained-capture-host-policy/v1', 'status': 'CAPTURED_SAMSUNG_SOURCE_SUPPORTS_V2_SYSTEM_DATA_FILE_READ',
              'selected': False, 'extractionReceipt': {'path': str(receipt_path.relative_to(ROOT)), 'sha256': sha(receipt_path)},
              'extractionProducer': {'path': str(producer.relative_to(ROOT)), 'sha256': sha(producer)},
              'manifest': {'path': str(MANIFEST), 'sha256': MANIFEST_SHA}, 'comparisonReceiptSha256': REPORT_SHA,
              'priorArchiveSha256': ARCHIVE_SHA, 'freshWholeArchiveHashPerformed': False,
              'selectedMembers': receipt['selected'], 'checks': checks, 'checkCount': len(checks),
              'directSourceAllows': direct, 'domainAttributeLine': domain[0], 'dataRootSourceRuleLine': root_rule[0],
              'fileContextTextCandidates': matches, 'contextPatternsChecked': pattern_count, 'textRegexErrors': errors,
              'rawSourceFacts': {'path': str(fact_path.relative_to(ROOT)), 'sha256': sha(fact_path)},
              'oldAccessFreezeSha256': sha(old),
              'sourceConclusion': 'Exact Samsung CIL directly grants required dir/file operations on system_data_file; captured context patterns support proposed /data/system dedicated path.',
              'runtimeConclusion': 'UNKNOWN: actual future inode labels and target-process open/read; effective loaded policy/root overlays/current code and creation transitions not certified by captured source.',
              'nextSmallStep': 'After separately authorized v2 creation, retain exact source/code/owner modes and observe both real labels; evaluate those types/domain against captured source and any effective-policy differences. This task authorizes no creation/relabel/read probe.',
              'limits': ['Textual Python-re filter is not libselabel matching/ranking or actual label application.',
                         'MLS source constraints recorded, not an executed complete policy decision.',
                         'No policy compiler/native tool/OEM code, phone action or target-process access executed.',
                         'Selected archive contents are hash-bound; full archive hash/framing is prior capture evidence, not freshly rechecked.'],
              'toolSha256': sha(Path(__file__)), 'phoneActions': [], 'policyExecuted': False}
    (ROOT / 'inventory/retained-capture-host-policy.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'checks': len(checks), 'patterns': pattern_count, 'contextCandidates': len(matches), 'status': result['status']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--extract', action='store_true')
    group.add_argument('--audit', action='store_true')
    args = parser.parse_args()
    if args.extract:
        extract()
    else:
        audit()
