"""Read-only raw debug_info audit; no writer, compiler, DEX loading or OEM execution."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, collections, hashlib, json, runpy, struct, uuid, zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT.parent / 'firmware/donor/extracted/system/framework/services.jar'
ARCHIVE_SHA = '66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'
SOURCE_SHA = 'c9a84cebd3bc22a48c0737a7de34d96ba0b97a6294d4bdd97c935543e605659f'
BASELINE = ROOT / 'out/coloros-services-preserved/20261106T002036982583Z-f6f5ab2395a34f279d39f26feea6f599/dex/classes2-preserved-039.dex'
BASELINE_SHA = '620bc981ce11b3367f4933ad96fb7326ccd5e2d9a1dec47a3a53bb88a0ccbba1'
PARSER = ROOT / 'tools/preflight_guest_metrics_parent_payload.py'
PARSER_SHA = 'd076c60a4c16774e1a8b75377661caf814a4eb4a72420f4082bc493dc4dce9ea'
DMS = 'Lcom/android/server/display/DisplayManagerService;'
BINDER = 'Lcom/android/server/display/DisplayManagerService$BinderService;'
TARGETS = {DMS + '->onStart()V', DMS + '->onBootPhase(I)V', BINDER + '->onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z'}


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


class RawDebug:
    def __init__(self, data, strings, types):
        self.data, self.strings, self.types = data, strings, types

    def leb(self, cursor, signed=False):
        value = 0
        for index in range(5):
            need(cursor < len(self.data), 'LEB outside DEX')
            byte = self.data[cursor]
            cursor += 1
            value |= (byte & 127) << (index * 7)
            if byte < 128:
                if signed and byte & 64:
                    value -= 1 << ((index + 1) * 7)
                need(-(1 << 31) <= value < (1 << 31) if signed else 0 <= value <= 0xffffffff, 'LEB32 overflow')
                return value, cursor
        raise ValueError('Unterminated LEB32')

    def ref(self, cursor, pool):
        value, cursor = self.leb(cursor)
        index = value - 1
        need(index == -1 or index < len(pool), 'Debug reference outside pool')
        # Hex preserves MUTF8 exactly, including encoded NUL/surrogate data.
        return (None if index == -1 else [index, pool[index].hex()]), cursor

    def read(self, start):
        need(0 < start < len(self.data), 'Invalid debug_info offset')
        line_start, cursor = self.leb(start)
        count, cursor = self.leb(cursor)
        need(count <= 65535, 'Debug parameter bound')
        params = []
        for _ in range(count):
            ref, cursor = self.ref(cursor, self.strings)
            params.append(ref)
        address, line, events = 0, line_start, []
        histogram = collections.Counter()
        for _ in range(len(self.data)):
            need(cursor < len(self.data), 'Debug stream missing END_SEQUENCE')
            opcode = self.data[cursor]
            cursor += 1
            histogram[opcode] += 1
            if opcode == 0:
                return {'offset': start, 'lineStart': line_start, 'parameterNames': params,
                        'events': events, 'terminalCursor': [address, line],
                        'endSequenceByteOffset': cursor - 1, 'bytes': cursor - start,
                        'rawSha256': hashlib.sha256(self.data[start:cursor]).hexdigest(),
                        'opcodeHistogram': {str(k): v for k, v in sorted(histogram.items())}}
            if opcode == 1:
                value, cursor = self.leb(cursor)
                address += value
            elif opcode == 2:
                value, cursor = self.leb(cursor, True)
                line += value
            elif opcode in (3, 4):
                register, cursor = self.leb(cursor)
                name, cursor = self.ref(cursor, self.strings)
                typ, cursor = self.ref(cursor, self.types)
                signature = None
                if opcode == 4:
                    signature, cursor = self.ref(cursor, self.strings)
                events.append(['startLocal', address, register, name, typ, signature])
            elif opcode in (5, 6):
                register, cursor = self.leb(cursor)
                events.append(['endLocal' if opcode == 5 else 'restartLocal', address, register])
            elif opcode in (7, 8):
                events.append(['prologueEnd' if opcode == 7 else 'epilogueBegin', address])
            elif opcode == 9:
                name, cursor = self.ref(cursor, self.strings)
                events.append(['setSourceFile', address, name])
            else:
                adjusted = opcode - 10
                address += adjusted // 15
                line += -4 + adjusted % 15
                events.append(['line', address, line])
            need(address <= 0xffffffff and -(1 << 31) <= line <= 0x7fffffff, 'Debug cursor overflow')
        raise ValueError('Debug opcode count bound')


def self_test():
    # Authored byte fixtures only, independent of any OEM/writer runtime.
    strings, types = [b'name', b'file', b'sig'], [b'I']
    fixtures = [
        (b'\x09\x01\x01\x00', [], [0, 9]),
        (b'\x09\x00\x01\x07\x02\x7f\x00', [], [7, 8]),
        (b'\x09\x00\x0e\x00', [['line', 0, 9]], [0, 9]),
        (b'\x09\x00\x03\x02\x01\x01\x05\x02\x06\x02\x07\x08\x09\x02\x00',
         [['startLocal', 0, 2, [0, '6e616d65'], [0, '49'], None], ['endLocal', 0, 2], ['restartLocal', 0, 2], ['prologueEnd', 0], ['epilogueBegin', 0], ['setSourceFile', 0, [1, '66696c65']]], [0, 9]),
        (b'\x09\x00\x04\x00\x00\x00\x03\x00', [['startLocal', 0, 0, None, None, [2, '736967']]], [0, 9]),
    ]
    for data, events, terminal in fixtures:
        parsed = RawDebug(b'\xff' + data, strings, types).read(1)
        need(parsed['events'] == events and parsed['terminalCursor'] == terminal, 'Authored debug fixture differs')
        need(parsed['endSequenceByteOffset'] == len(data), 'END_SEQUENCE extent fixture')
    for data in (b'\xff\x01\x00', b'\xff\x01\x01\x08\x00', b'\xff\x01\x00\x01\x80'):
        try:
            RawDebug(data, strings, types).read(1)
        except ValueError:
            pass
        else:
            raise ValueError('Malformed authored fixture accepted')
    return {'positive': len(fixtures), 'negative': 3}


def scan(dex):
    raw = RawDebug(dex.d, dex.strings, [x.encode('ascii') for x in dex.types])
    methods, streams = {}, {}
    for method in dex.codes:
        code = method['codeOffset']
        debug = dex.u32(code + 8)
        if debug and debug not in streams:
            streams[debug] = raw.read(debug)
        methods[method['descriptor']] = {'codeOffset': code, 'codeUnits': dex.u32(code + 12), 'debugOffset': debug}
    need(len(methods) == len(dex.codes), 'Duplicate code-bearing descriptor')
    mapped = [r for r in dex.map if r['type'] == 0x2003]
    need(len(mapped) == 1 and mapped[0]['size'] == len(streams), 'Unreferenced/missing raw debug map item')
    extents = sorted((s['offset'], s['endSequenceByteOffset'] + 1) for s in streams.values())
    need(extents and extents[0][0] == mapped[0]['offset'] and all(a[1] <= b[0] for a, b in zip(extents, extents[1:])), 'Overlapping debug extents or map start')
    return methods, streams


def compare(a, b):
    if a is None or b is None:
        return ['presence'] if a != b else []
    return [key for key in ('lineStart', 'parameterNames', 'events', 'terminalCursor') if a[key] != b[key]]


def dump(path, rows):
    with path.open('w', encoding='utf8', newline='\n') as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(',', ':'), ensure_ascii=True) + '\n')
    need(path.stat().st_size <= 256 * 1024 * 1024, 'Raw audit output bound')
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test-only', action='store_true')
    args = parser.parse_args()
    tests = self_test()
    if args.self_test_only:
        print(json.dumps({'status': 'PASS_AUTHORED_DEBUG_PARSER_FIXTURES', **tests}))
        return
    tool_sha = sha(__file__)
    need(sha(PARSER) == PARSER_SHA and sha(ARCHIVE) == ARCHIVE_SHA and sha(BASELINE) == BASELINE_SHA, 'Frozen input differs')
    # The frozen module defines an authored passive static parser; its guarded main is not called.
    Dex = runpy.run_path(str(PARSER), run_name='raw_debug_static_import')['Dex']
    with zipfile.ZipFile(ARCHIVE) as archive:
        need(archive.namelist().count('classes2.dex') == 1 and archive.getinfo('classes2.dex').file_size == 10042704, 'Archive entry bound')
        source = archive.read('classes2.dex')
    need(hashlib.sha256(source).hexdigest() == SOURCE_SHA, 'Original DEX differs')
    a, b = Dex(source), Dex(BASELINE.read_bytes())
    need(a.strings == b.strings and a.types == b.types and a.methods == b.methods, 'Raw reference pools differ')
    am, ast = scan(a)
    bm, bst = scan(b)
    need(am.keys() == bm.keys() and len(am) == 45059 and TARGETS <= am.keys(), 'Method closure differs')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex
    work, raw = ROOT / 'out/coloros-raw-debug-baseline-review' / stamp, ROOT / 'firmware/coloros-raw-debug-baseline-review' / stamp
    work.mkdir(parents=True)
    raw.mkdir(parents=True)
    differences, selected, mapping = [], [], []
    hist = collections.Counter()
    encoding_diff = 0
    present = [0, 0]
    event_counts = [collections.Counter(), collections.Counter()]
    for method in sorted(am):
        aa = ast.get(am[method]['debugOffset'])
        bb = bst.get(bm[method]['debugOffset'])
        for index, stream in enumerate((aa, bb)):
            present[index] += stream is not None
            if stream:
                event_counts[index].update(x[0] for x in stream['events'])
        changes = compare(aa, bb)
        hist.update(changes)
        encoding_diff += bool(aa and bb and aa['rawSha256'] != bb['rawSha256'])
        row = {'method': method, 'source': am[method], 'baseline': bm[method], 'changedFacts': changes}
        mapping.append(row)
        if changes:
            differences.append({**row, 'sourceDebug': aa, 'baselineDebug': bb})
        if method in TARGETS or (method.startswith(DMS + '-><init>(') or method.startswith(BINDER + '-><init>(')):
            selected.append({**row, 'sourceDebug': aa, 'baselineDebug': bb})
    pins = [dump(raw / 'source-debug-streams.jsonl', ast.values()), dump(raw / 'baseline-debug-streams.jsonl', bst.values()),
            dump(raw / 'all-method-mapping.jsonl', mapping), dump(raw / 'differences.jsonl', differences), dump(raw / 'selected-methods.jsonl', selected)]
    result = {'schema': 'coloros-raw-debug-baseline-review/v1', 'status': 'RAW_DEBUG_DIFFERENCES_FOUND' if differences else 'RAW_DEBUG_FACTS_EQUAL',
              'tool': {'path': Path(__file__).relative_to(ROOT).as_posix(), 'sha256': tool_sha},
              'inputs': {'archive': {'path': str(ARCHIVE), 'sha256': ARCHIVE_SHA}, 'sourceDexSha256': SOURCE_SHA,
                         'baseline': {'path': BASELINE.relative_to(ROOT).as_posix(), 'sha256': BASELINE_SHA},
                         'passiveParser': {'path': PARSER.relative_to(ROOT).as_posix(), 'sha256': PARSER_SHA}},
              'methodsCompared': len(am), 'debugPresentMethods': present, 'uniqueStreams': [len(ast), len(bst)],
              'changedMethods': len(differences), 'changedFactCounts': dict(hist), 'rawEncodingDifferentMethods': encoding_diff,
              'eventCountsPerMethod': [dict(x) for x in event_counts], 'selectedMethodCount': len(selected),
              'selectedSummary': [{'method': s['method'], 'changedFacts': s['changedFacts'],
                                   'sourceHeader': None if s['sourceDebug'] is None else {k: s['sourceDebug'][k] for k in ('lineStart', 'parameterNames', 'terminalCursor', 'bytes')},
                                   'baselineHeader': None if s['baselineDebug'] is None else {k: s['baselineDebug'][k] for k in ('lineStart', 'parameterNames', 'terminalCursor', 'bytes')}} for s in selected],
              'rawProofs': pins, 'authoredFixtures': tests, 'writerExecuted': False, 'compilerExecuted': False,
              'oemExecuted': False, 'phoneActions': False, 'existingFrozenClaimsNotExpanded': True}
    need(sha(__file__) == tool_sha and sha(PARSER) == PARSER_SHA and sha(ARCHIVE) == ARCHIVE_SHA and sha(BASELINE) == BASELINE_SHA, 'Input changed during audit')
    receipt = work / 'receipt.json'
    receipt.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'status': result['status'], 'receipt': receipt.relative_to(ROOT).as_posix(), 'methodsCompared': len(am), 'changedMethods': len(differences), 'changedFactCounts': dict(hist), 'selectedMethodCount': len(selected)}))


if __name__ == '__main__':
    main()
