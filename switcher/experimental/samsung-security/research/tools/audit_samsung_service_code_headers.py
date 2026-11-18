"""Read two pinned Samsung service definitions' raw 041/039 code headers.

No slicing/rebasing, writer, repair, class loading or OEM execution. The original
physical DEX remains one intact byte buffer; 041 data/table offsets are absolute.
"""
import hashlib
import json
from pathlib import Path
import struct
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
STREAM = 'samsung-service-code-headers-review'
OLD = 'out/samsung-dex041-rewrite/20261105T195435218414Z-5ee1bb346bb64533ade644907674ceca'
RAW_OLD = OLD.replace('out/', 'firmware/', 1)
WANTED = {'Lcom/android/server/pm/UserManagerService;', 'Lcom/android/server/locksettings/LockSettingsService;'}
PINS = {
    'inventory/samsung-dex041-rewrite.json': 'd4a22e6acc2dbe07e4c177b9156485c2ceeffbacfc27a404b8a2e045603041e3',
    '../firmware/samsung/runtime-20261104/services.jar': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
    'tools/Probe-SamsungDex041.java': '2dc5cdbbcdd508e8856ab1eb6b8addd3aca0a7bfdd4111437fb4b876a3ab4e6d',
    'tools/SecurityDexReader.java': '9ee6f28750779f289bbb85049472d5261b7bacad5655faf01c8395f2f6d244cc',
    OLD + '/classes/ProbeSamsungDex041.class': 'a40431d951aa23ce761f740162b9a7fd5be811ea5fa3c2dc57c672b57ed58cce',
    OLD + '/classes/SecurityDexReader.class': 'b940ce6a6d4c715f986b74079ed83dd00e2c68134efd0e70ab56b2ffbbc08681',
    OLD + '/classes/SecurityDexReader$LogicalDex.class': '2504a389fca3f1e02138fcc92e2c8d9cd6600b5f0544f8bad75c57ab3fcca5c1',
    OLD + '/receipt.json': 'd4a22e6acc2dbe07e4c177b9156485c2ceeffbacfc27a404b8a2e045603041e3',
    OLD + '/dex/subset-039.dex': '80c379a3a0a9f6b94bfb45d78904fda8a1a827b46a9e7bc0f6495d8e13b2cef0',
    OLD + '/dex/roundtrip-039.dex': '80c379a3a0a9f6b94bfb45d78904fda8a1a827b46a9e7bc0f6495d8e13b2cef0',
    RAW_OLD + '/original-normalized.jsonl': '9396e18b7d981a53abb90ec96f254fdcb24787e3bed2bbb097602be915274724',
    RAW_OLD + '/decoded-normalized.jsonl': '9396e18b7d981a53abb90ec96f254fdcb24787e3bed2bbb097602be915274724',
    RAW_OLD + '/roundtrip-normalized.jsonl': '9396e18b7d981a53abb90ec96f254fdcb24787e3bed2bbb097602be915274724',
}
WITNESSES = {
    'Lcom/android/server/locksettings/LockSettingsService;-><clinit>()V': {
        'sourceCodeOffset': 12700880, 'outputCodeOffset': 149456,
        'sourceHeader': [3, 0, 3, 0, 0, 51], 'outputHeader': [3, 0, 2, 0, 0, 51]},
    'Lcom/android/server/locksettings/LockSettingsService;->applyRemoteLock(ILcom/android/internal/widget/RemoteLockInfo;)Z': {
        'sourceCodeOffset': 12680368, 'outputCodeOffset': 153080,
        'sourceHeader': [38, 3, 11, 3, 0, 601], 'outputHeader': [38, 3, 5, 3, 0, 601]},
}

def need(ok, message):
    if not ok:
        raise ValueError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def verify_pins():
    for name, expected in PINS.items():
        need(digest((ROOT / name).read_bytes()) == expected, 'Pinned input changed: ' + name)

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')

class View:
    """Bounded consumed-header/table parser, deliberately not a full verifier."""
    def __init__(self, data, header):
        self.data, self.header = data, header
        self.string_cache, self.type_cache = {}, {}
        self.span(header, 112)
        version = data[header:header + 8]
        need(version in (b'dex\n041\0', b'dex\n039\0'), 'Exact admitted DEX version')
        self.version = version[4:7].decode('ascii')
        self.size = self.u32(header + 32)
        need(self.u32(header + 40) == 0x12345678, 'DEX endian')
        if self.version == '041':
            self.span(header, 120)
            need(self.u32(header + 36) == 120 and self.u32(header + 112) == len(data)
                 and self.u32(header + 116) == header and 120 <= self.size <= len(data) - header,
                 'Full intact041 container/header-offset semantics')
        else:
            need(header == 0 and self.size == len(data) and self.u32(36) == 112, 'Complete ordinary039 extent')
            need(hashlib.sha1(data[32:]).digest() == data[12:32]
                 and zlib.adler32(data[12:]) & 0xffffffff == self.u32(8), '039 signature/checksum')
        self.tables = {}
        for name, offset, width in [('strings', 56, 4), ('types', 64, 4), ('protos', 72, 12),
                                    ('fields', 80, 8), ('methods', 88, 8), ('classes', 96, 32)]:
            count, absolute = self.u32(header + offset), self.u32(header + offset + 4)
            need(count <= 2_000_000 and (count > 0 or absolute == 0), 'Table count')
            self.span(absolute, count * width)
            need(not count or absolute % 4 == 0, 'Table alignment')
            self.tables[name] = count, absolute, width
        mp = self.u32(header + 52)
        count = self.u32(mp)
        need(0 < count <= 65536, 'Map count'); self.span(mp + 4, count * 12)
        maps = []
        for n in range(count):
            kind, unused, size, absolute = struct.unpack_from('<HHII', data, mp + 4 + 12 * n)
            need(unused == 0 and size > 0 and absolute < len(data), 'Map entry')
            maps.append((absolute, kind, size))
        need(maps == sorted(maps) and len({x[1] for x in maps}) == len(maps)
             and len({x[0] for x in maps}) == len(maps), 'Ordered unique map entries')
        self.sections = {row[1]: (row[0], maps[n + 1][0] if n + 1 < len(maps) else len(data), row[2])
                         for n, row in enumerate(maps)}
        need(self.sections[0][0] == header and self.sections[0x1000][0] == mp, 'Actual logical header/map identity')

    def span(self, offset, size):
        need(0 <= offset <= len(self.data) and 0 <= size <= len(self.data) - offset, 'Consumed byte bound')

    def u16(self, offset):
        self.span(offset, 2); return struct.unpack_from('<H', self.data, offset)[0]

    def u32(self, offset):
        self.span(offset, 4); return struct.unpack_from('<I', self.data, offset)[0]

    def section(self, offset, size, kind):
        lo, hi, _ = self.sections[kind]
        need(lo <= offset <= hi and 0 <= size <= hi - offset, 'Consumed section bound')

    def uleb(self, cursor, limit):
        value = 0
        for n in range(5):
            need(cursor < limit, 'ULEB bound'); byte = self.data[cursor]; cursor += 1
            need(n != 4 or byte <= 15, 'ULEB uint32 overflow')
            value |= (byte & 127) << (7 * n)
            if byte < 128:
                return value, cursor
        raise ValueError('ULEB termination')

    def item(self, name, index):
        count, offset, width = self.tables[name]
        need(0 <= index < count, 'Table index'); return offset + index * width

    def string(self, index):
        if index not in self.string_cache:
            p = self.u32(self.item('strings', index)); self.section(p, 1, 0x2002)
            length, p = self.uleb(p, self.sections[0x2002][1])
            end = self.data.find(b'\0', p, self.sections[0x2002][1]); need(end >= p, 'String terminator')
            # Selected descriptors/names are ASCII, a lossless subset of MUTF8.
            value = self.data[p:end].decode('ascii'); need(len(value) == length, 'Selected ASCII UTF16 length')
            self.string_cache[index] = value
        return self.string_cache[index]

    def typ(self, index):
        if index not in self.type_cache:
            self.type_cache[index] = self.string(self.u32(self.item('types', index)))
        return self.type_cache[index]

    def method(self, index):
        p = self.item('methods', index)
        owner, proto, name = struct.unpack_from('<HHI', self.data, p)
        p = self.item('protos', proto)
        result, args = self.u32(p + 4), self.u32(p + 8)
        parameters = []
        if args:
            count = self.u32(args); need(count <= 65536, 'Selected parameter count')
            self.section(args, 4 + 2 * count, 0x1001)
            parameters = [self.typ(self.u16(args + 4 + 2 * n)) for n in range(count)]
        owner = self.typ(owner)
        return owner, owner + '->' + self.string(name) + '(' + ''.join(parameters) + ')' + self.typ(result), parameters

    def selected(self):
        classes, methods = {}, {}
        for n in range(self.tables['classes'][0]):
            p = self.item('classes', n); owner = self.typ(self.u32(p))
            if owner not in WANTED:
                continue
            need(owner not in classes, 'Duplicate selected class')
            class_flags = self.u32(p + 4); cursor = self.u32(p + 24)
            need(cursor != 0, 'Selected class data')
            self.section(cursor, 1, 0x2000); limit = self.sections[0x2000][1]; counts = []
            for _ in range(4):
                value, cursor = self.uleb(cursor, limit); counts.append(value)
            need(sum(counts) <= 200000, 'Selected encoded member count')
            for part, count in enumerate(counts):
                member = 0
                for number in range(count):
                    delta, cursor = self.uleb(cursor, limit); member += delta
                    need(number == 0 or delta > 0, 'Member index ordering')
                    flags, cursor = self.uleb(cursor, limit)
                    if part < 2:
                        self.item('fields', member); continue
                    code, cursor = self.uleb(cursor, limit)
                    actual_owner, identity, parameters = self.method(member)
                    need(actual_owner == owner and identity not in methods, 'Exact selected method owner/identity')
                    row = {'identity': identity, 'classFlags': class_flags, 'flags': flags,
                           'partition': 'direct' if part == 2 else 'virtual', 'codePresent': bool(code),
                           'methodIndex': member, 'logicalHeaderOffset': self.header, 'codeOffset': code,
                           'header': None}
                    if code:
                        self.section(code, 16, 0x2001); need(code % 4 == 0, 'Code header alignment')
                        regs, ins, outs, tries, debug, units = struct.unpack_from('<4HII', self.data, code)
                        self.section(code + 16, units * 2, 0x2001)
                        expected_ins = (0 if flags & 8 else 1) + sum(2 if t in ('J', 'D') else 1 for t in parameters)
                        need(ins <= regs and ins == expected_ins, 'Incoming words agree with exact signature/static flag')
                        row['header'] = {'registersSize': regs, 'insSize': ins, 'outsSize': outs,
                                         'triesSize': tries, 'insnsSize': units}
                        row['rawHeaderSha256'] = digest(self.data[code:code + 16])
                        row['debugInfoOffsetNotCompared'] = debug
                    methods[identity] = row
            classes[owner] = {'logicalHeaderOffset': self.header, 'classFlags': class_flags,
                              'classDefOffset': p, 'counts': dict(zip(['staticFields', 'instanceFields', 'directMethods', 'virtualMethods'], counts))}
        return classes, methods

def main():
    verify_pins()
    with zipfile.ZipFile(ROOT / '../firmware/samsung/runtime-20261104/services.jar') as archive:
        entries = [e for e in archive.infolist() if e.filename == 'classes.dex']
        need(len(entries) == 1 and entries[0].file_size == 28157552, 'Pinned source physical member')
        original = archive.read(entries[0])
    need(digest(original) == '6c9ac3f92a14050900b5fe9502a726cd186011a4342cb2a76c7ba5288e42c973', 'Pinned full physical041')
    cursor = 0; headers = []; classes = {}; methods = {}
    while cursor < len(original):
        view = View(original, cursor); need(view.version == '041', 'Original041 only')
        headers.append({'offset': cursor, 'logicalFileSize': view.size, 'containerSize': len(original),
                        'classCount': view.tables['classes'][0], 'mapOffset': view.u32(cursor + 52)})
        selected_classes, selected_methods = view.selected()
        need(not classes.keys() & selected_classes.keys() and not methods.keys() & selected_methods.keys(), 'No selected cross-header alias')
        classes.update(selected_classes); methods.update(selected_methods); cursor += view.size
    need(cursor == len(original) and [h['offset'] for h in headers] == [0, 10057984]
         and [h['classCount'] for h in headers] == [9252, 9664], 'Exact full041 header chain closes')
    need(set(classes) == WANTED and len(methods) == 476
         and all(c['logicalHeaderOffset'] == 10057984 for c in classes.values()), 'Exact two selected definitions')
    raw = ROOT / 'firmware' / STREAM
    save(raw / 'original-headers.json', {'headers': headers, 'classes': classes, 'methods': methods})
    outputs = []
    for label in ('subset', 'roundtrip'):
        path = OLD + '/dex/' + label + '-039.dex'; data = (ROOT / path).read_bytes(); view = View(data, 0)
        outclasses, outmethods = view.selected(); need(set(outclasses) == WANTED, 'Only selected output classes')
        need(view.tables['classes'][0] == 2, 'Actual output has exactly2definitions')
        save(raw / (label + '-headers.json'), {'classes': outclasses, 'methods': outmethods})
        need(methods.keys() == outmethods.keys(), 'Declared selected method identity set')
        field_counts = {}; drift = []
        for identity, source in methods.items():
            after = outmethods[identity]; changes = {}
            for key in ('classFlags', 'flags', 'partition', 'codePresent'):
                if source[key] != after[key]: changes[key] = [source[key], after[key]]
            if source['header'] is not None and after['header'] is not None:
                for key, value in source['header'].items():
                    if value != after['header'][key]: changes[key] = [value, after['header'][key]]
            if changes:
                drift.append({'identity': identity, 'changes': changes})
                for key in changes: field_counts[key] = field_counts.get(key, 0) + 1
        # Independent literal-offset witnesses, read directly from intact buffers.
        for identity, witness in WITNESSES.items():
            need(methods[identity]['codeOffset'] == witness['sourceCodeOffset']
                 and outmethods[identity]['codeOffset'] == witness['outputCodeOffset'], 'Exact witnessed code offsets')
            need(list(struct.unpack_from('<4HII', original, witness['sourceCodeOffset'])) == witness['sourceHeader']
                 and list(struct.unpack_from('<4HII', data, witness['outputCodeOffset'])) == witness['outputHeader'],
                 'Literal original and saved-output code header witness')
        need({d['identity'] for d in drift} == set(WITNESSES) and field_counts == {'outsSize': 2}, 'Pinned bounded drift result')
        byclass = {owner: {'methods': sum(k.startswith(owner + '->') for k in methods),
                           'codedMethods': sum(k.startswith(owner + '->') and r['codePresent'] for k, r in methods.items()),
                           'driftMethods': sum(r['identity'].startswith(owner + '->') for r in drift)} for owner in sorted(WANTED)}
        save(raw / (label + '-drift.json'), drift)
        outputs.append({'label': label, 'path': path, 'sha256': digest(data), 'bytes': len(data),
                        'declaredMethods': len(outmethods), 'driftMethods': len(drift), 'driftFieldCounts': field_counts,
                        'perClass': byclass, 'rawHeaderComparison': 'PASS' if not drift else 'HOLD_DRIFT',
                        'driftExamples': drift[:6]})
    verify_pins()
    evidence = []
    for path in sorted(raw.glob('*.json')):
        evidence.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(path.read_bytes()), 'bytes': path.stat().st_size})
    result = {'schema': 'samsung-service-code-headers-review/v1', 'status': 'HOLD_RAW_CODE_HEADER_DRIFT' if any(o['driftMethods'] for o in outputs) else 'PASS_BOUNDED_RAW_CODE_HEADERS',
              'selected': False, 'scope': 'Only the two original selected UMS/LSS definitions and both previously saved039 outputs',
              'inputPins': PINS, 'sourcePhysicalDexSha256': digest(original), 'originalHeaders': headers,
              'sourceClasses': classes, 'sourceDeclaredMethods': len(methods),
              'sourceCodedMethods': sum(r['codePresent'] for r in methods.values()),
              'outputs': outputs, 'rawEvidence': evidence,
              'comparisonFields': ['declaredMethodIdentity', 'classFlags', 'flags', 'directOrVirtualPartition', 'codePresence', 'registersSize', 'insSize', 'outsSize', 'triesSize', 'insnsSize'],
              'directHeaderWitnesses': WITNESSES,
              'debugOffsetsCompared': False, 'codeOffsetsCompared': False,
              'normalizerGap': 'Original Probe normalization compares getRegisterCount and normalized bodies/handlers but never raw ins_size or outs_size;039 second-emit equality does not prove041 source header equality.',
              'input041SlicedOrRebased': False, 'rewriterRun': False, 'repairApplied': False, 'oemExecuted': False,
              'limits': ['No full DEX verifier, instruction/header minimum-outs verifier, wider dependency cohort or unrelated artifact review.', 'No old files modified, no repair or preservation-profile expansion.', 'Exact source/header evidence only; no ART/runtime/security/phone acceptance.']}
    save(ROOT / 'inventory' / (STREAM + '.json'), result)
    save(ROOT / 'out' / STREAM / 'checks.json', result)
    print(json.dumps({'status': result['status'], 'declaredMethods': len(methods), 'codedMethods': result['sourceCodedMethods'], 'outputs': [{k: o[k] for k in ('label', 'driftMethods', 'driftFieldCounts')} for o in outputs], 'rewriterRun': False, 'oemExecuted': False}))

if __name__ == '__main__':
    main()
