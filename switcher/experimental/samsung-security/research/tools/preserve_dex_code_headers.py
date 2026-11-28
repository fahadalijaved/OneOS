"""Restore source outs_size only after complete ordinary039 header admission.

Pure static bytes, no writer/runtime. This is not instruction, metadata, source
provenance or authority acceptance; callers must separately pin/review emitters.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import uuid
import zipfile
import zlib

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'out/dex-code-header-preservation'
MAX_BYTES = 64 * 1024 * 1024
SOURCE_PROFILES = {
    'samsung-framework-classes3': ('256cc1744c36a88d3ee4c9218d2cf0156816ce89a63cd98787dd1633edbdf1a7', 8830032),
    'coloros-services-classes2': ('c9a84cebd3bc22a48c0737a7de34d96ba0b97a6294d4bdd97c935543e605659f', 10042704),
}
GL_METHOD = b'Landroid/opengl/GLLogWrapper;->glStencilMask(I)V'


def digest(data): return hashlib.sha256(data).hexdigest()


def need(condition, message):
    if not condition: raise ValueError(message)


def seal(data):
    result = bytearray(data)
    result[12:32] = hashlib.sha1(result[32:]).digest()
    struct.pack_into('<I', result, 8, zlib.adler32(result[12:]) & 0xffffffff)
    return bytes(result)


class Dex039:
    """Bounded consumed tables/class-data/code extents; not a full DEX verifier."""
    def __init__(self, data):
        need(isinstance(data, bytes) and 112 <= len(data) <= MAX_BYTES, 'DEX byte/type bound')
        self.data = data
        need(data[:8] == b'dex\n039\0', 'Only complete ordinary DEX039; no041/container fallback')
        need(self.u32(32) == len(data) and self.u32(36) == 112 and self.u32(40) == 0x12345678, 'Header extent/endian')
        need(hashlib.sha1(data[32:]).digest() == data[12:32] and zlib.adler32(data[12:]) & 0xffffffff == self.u32(8), 'DEX signature/checksum')
        self.data_start = self.u32(108)
        need(112 <= self.data_start <= len(data) and self.u32(104) == len(data) - self.data_start, 'Data extent')
        mp = self.u32(52); self.span(mp, 4)
        count = self.u32(mp); need(1 <= count <= 65536, 'Map count'); self.span(mp + 4, count * 12)
        self.maps = {}; ordered = []
        for index in range(count):
            pos = mp + 4 + index * 12
            kind, unused, size, offset = struct.unpack_from('<HHII', data, pos)
            need(unused == 0 and size > 0 and kind not in self.maps and offset < len(data), 'Map entry')
            self.maps[kind] = (size, offset); ordered.append((offset, kind))
        need(ordered == sorted(ordered) and len({p for p, _ in ordered}) == len(ordered), 'Ordered unique map offsets')
        self.sections = {kind: (offset, ordered[n + 1][0] if n + 1 < len(ordered) else len(data))
                         for n, (offset, kind) in enumerate(ordered)}
        need(self.maps.get(0) == (1, 0) and self.maps.get(0x1000) == (1, mp), 'Header/map entries')
        tables = []
        for header, kind, width in [(56, 1, 4), (64, 2, 4), (72, 3, 12), (80, 4, 8), (88, 5, 8), (96, 6, 32)]:
            size, offset = self.u32(header), self.u32(header + 4)
            need(size <= 2000000 and (size > 0 or offset == 0), 'Table count/empty offset')
            if size:
                need(offset >= 112 and offset % 4 == 0, 'Table offset alignment'); self.span(offset, size * width)
                need(offset + size * width <= self.data_start and self.maps.get(kind) == (size, offset), 'Table/map extent')
            else: need(kind not in self.maps, 'Empty table map')
            tables.append((size, offset))
        (ns, os_), (nt, ot), (np, op), (nf, of), (nm, om), (nc, oc) = tables
        need(nt <= 65536 and np <= 65536 and nf <= 65536 and nm <= 65536, '16-bit reference table bound')
        self.types_count = nt
        strings = []
        for index in range(ns):
            pos = self.u32(os_ + index * 4); self.in_section(pos, 0x2002)
            units, cursor = self.uleb(pos, self.sections[0x2002][1])
            end = data.find(b'\0', cursor, self.sections[0x2002][1])
            need(end >= cursor, 'Bounded string terminator')
            raw = data[cursor:end]
            # Count actual modified UTF8 units without lossy identity decoding.
            unit_count = 0; p = 0
            while p < len(raw):
                item = raw[p]
                if item < 0x80: need(item != 0, 'MUTF8 embedded zero'); step = 1
                elif 0xc0 <= item <= 0xdf:
                    need(p + 1 < len(raw) and raw[p + 1] & 0xc0 == 0x80, 'MUTF8 two-byte sequence')
                    value = (item & 31) << 6 | raw[p + 1] & 63
                    need(value == 0 or value >= 0x80, 'MUTF8 noncanonical sequence'); step = 2
                elif 0xe0 <= item <= 0xef:
                    need(p + 2 < len(raw) and all(x & 0xc0 == 0x80 for x in raw[p + 1:p + 3]), 'MUTF8 three-byte sequence')
                    need(((item & 15) << 12 | (raw[p + 1] & 63) << 6 | raw[p + 2] & 63) >= 0x800, 'MUTF8 overlong'); step = 3
                else: raise ValueError('MUTF8 leading byte')
                p += step; unit_count += 1
            need(unit_count == units, 'MUTF8 declared UTF16 length')
            strings.append(raw)
        def string(index): need(index < ns, 'String index'); return strings[index]
        types = [string(self.u32(ot + 4 * i)) for i in range(nt)]
        def typ(index): need(index < nt, 'Type index'); return types[index]
        protos = []
        for index in range(np):
            row = op + index * 12; shorty, result, params = struct.unpack_from('<III', data, row)
            string(shorty); args = []
            if params:
                self.in_section(params, 0x1001); count = self.u32(params); self.span(params + 4, count * 2)
                need(params + 4 + count * 2 <= self.sections[0x1001][1], 'Type-list extent')
                args = [typ(self.u16(params + 4 + 2 * n)) for n in range(count)]
            protos.append(b'(' + b''.join(args) + b')' + typ(result))
        method_ids = []
        for index in range(nm):
            owner, proto, name = struct.unpack_from('<HHI', data, om + 8 * index)
            need(proto < np, 'Method proto index')
            method_ids.append((typ(owner), typ(owner) + b'->' + string(name) + protos[proto]))
        field_owners = []
        for index in range(nf):
            owner, type_index, name = struct.unpack_from('<HHI', data, of + index * 8)
            typ(type_index); string(name); field_owners.append(typ(owner))
        self.methods = {}; self.codes = {}; self.classes = set(); self.class_data_extents = []
        for index in range(nc):
            row = oc + 32 * index; owner = typ(self.u32(row)); cursor = self.u32(row + 24)
            need(owner not in self.classes, 'Duplicate class identity'); self.classes.add(owner)
            if not cursor: continue
            self.in_section(cursor, 0x2000); start = cursor; limit = self.sections[0x2000][1]; counts = []
            for _ in range(4): value, cursor = self.uleb(cursor, limit); counts.append(value)
            need(sum(counts) <= nf + nm, 'Encoded member count')
            seen_members = set()
            for part, count in enumerate(counts):
                member_index = 0
                for number in range(count):
                    delta, cursor = self.uleb(cursor, limit); member_index += delta
                    need(number == 0 or delta > 0, 'Encoded member index order')
                    flags, cursor = self.uleb(cursor, limit)
                    code = 0
                    if part < 2:
                        need(member_index < nf and field_owners[member_index] == owner, 'Encoded field owner/index')
                        marker = ('field', member_index)
                    else:
                        code, cursor = self.uleb(cursor, limit)
                        need(member_index < nm and method_ids[member_index][0] == owner, 'Encoded method owner/index')
                        key = method_ids[member_index][1]; marker = ('method', member_index)
                        need(key not in self.methods, 'Duplicate declared method identity')
                        header = None
                        if code:
                            if code not in self.codes: self.codes[code] = self.code_item(code)
                            header = self.codes[code]['header']
                        self.methods[key] = {'flags': flags, 'partition': 'direct' if part == 2 else 'virtual',
                            'codeOffset': code, 'header': header, 'methodIndex': member_index}
                    need(marker not in seen_members, 'Duplicate encoded member'); seen_members.add(marker)
            self.class_data_extents.append((start, cursor))
        extents = sorted((code, item['end']) for code, item in self.codes.items())
        need(all(left[1] <= right[0] for left, right in zip(extents, extents[1:])), 'Partially overlapping code items')
        need(not self.codes or self.maps.get(0x2001, (0, 0))[0] == len(self.codes), 'Referenced code-item/map count')
        class_extents = sorted(set(self.class_data_extents))
        need(all(a[1] <= b[0] for a, b in zip(class_extents, class_extents[1:])), 'Overlapping class data')

    def span(self, offset, size):
        need(0 <= offset <= len(self.data) and 0 <= size <= len(self.data) - offset, 'Consumed byte range')

    def u16(self, offset): self.span(offset, 2); return struct.unpack_from('<H', self.data, offset)[0]
    def u32(self, offset): self.span(offset, 4); return struct.unpack_from('<I', self.data, offset)[0]

    def in_section(self, offset, kind):
        need(kind in self.sections and self.sections[kind][0] <= offset < self.sections[kind][1], 'Referenced section/range')

    def uleb(self, cursor, limit):
        value = 0
        for index in range(5):
            need(cursor < limit, 'ULEB extent'); byte = self.data[cursor]; cursor += 1
            need(index != 4 or byte <= 15, 'ULEB uint32 overflow')
            value |= (byte & 127) << (7 * index)
            if byte < 128: return value, cursor
        raise ValueError('ULEB termination')

    def sleb(self, cursor, limit):
        value = 0; shift = 0
        for _ in range(5):
            need(cursor < limit, 'SLEB extent'); byte = self.data[cursor]; cursor += 1
            value |= (byte & 127) << shift; shift += 7
            if byte < 128:
                if byte & 64: value -= 1 << shift
                need(-(1 << 31) <= value < 1 << 31, 'SLEB int32 overflow'); return value, cursor
        raise ValueError('SLEB termination')

    def code_item(self, offset):
        self.in_section(offset, 0x2001); limit = self.sections[0x2001][1]
        need(offset % 4 == 0 and offset + 16 <= limit, 'Code header alignment/range')
        regs, incoming, outgoing, tries, debug, units = struct.unpack_from('<4HII', self.data, offset)
        need(incoming <= regs and units <= (limit - offset - 16) // 2, 'Code incoming/instruction extent')
        if debug: self.in_section(debug, 0x2003)
        end = offset + 16 + units * 2
        if tries:
            if units & 1:
                need(end + 2 <= limit and self.u16(end) == 0, 'Code try padding'); end += 2
            need(tries <= (limit - end) // 8, 'Try table extent')
            try_offsets = []; previous_end = 0
            for number in range(tries):
                start, count, handler = struct.unpack_from('<IHH', self.data, end + number * 8)
                need(count > 0 and start >= previous_end and start < units and count <= units - start, 'Try instruction extent/order')
                previous_end = start + count; try_offsets.append(handler)
            end += tries * 8; handler_start = end
            count, end = self.uleb(end, limit); need(0 < count <= limit - end, 'Handler list count')
            entries = set()
            for _ in range(count):
                entries.add(end - handler_start); size, end = self.sleb(end, limit)
                need(abs(size) <= (limit - end) // 2, 'Typed handler count')
                for _ in range(abs(size)):
                    typ, end = self.uleb(end, limit); address, end = self.uleb(end, limit)
                    need(typ < self.types_count and address < units, 'Typed handler target/type')
                if size <= 0:
                    address, end = self.uleb(end, limit); need(address < units, 'Catch-all target')
            need(set(try_offsets) <= entries, 'Try handler reference')
        return {'header': (regs, incoming, outgoing, tries, units), 'end': end, 'debugOffset': debug}


def _plan(source, emitted, transformation):
    need(source.classes == emitted.classes and source.methods.keys() == emitted.methods.keys(), 'Class/declared method identity set changed')
    need(transformation in ('none', 'samsung-permission-gl-jumbo-v1'), 'Unknown transformation profile')
    changes = {}; groups = {}; gl_seen = False
    for identity, original in source.methods.items():
        actual = emitted.methods[identity]
        need((original['flags'], original['partition'], bool(original['codeOffset'])) ==
             (actual['flags'], actual['partition'], bool(actual['codeOffset'])), 'Method flags/partition/code presence changed')
        if original['header'] is None: continue
        expected = list(original['header'])
        if transformation == 'samsung-permission-gl-jumbo-v1' and identity == GL_METHOD:
            need(expected == [3, 2, 3, 0, 23], 'Exact approved source GL header'); expected[-1] = 24; gl_seen = True
        header = actual['header']
        need(tuple(header[n] for n in (0, 1, 3, 4)) == tuple(expected[n] for n in (0, 1, 3, 4)), 'Non-outs code header drift')
        word = actual['codeOffset'] + 4
        if word in groups:
            need(groups[word]['wanted'] == expected[2], 'Conflicting shared code outs mapping')
        else: groups[word] = {'wanted': expected[2], 'actual': header[2], 'methods': []}
        groups[word]['methods'].append(identity)
        if header[2] != expected[2]: changes[word] = groups[word]
    need(transformation == 'none' or gl_seen, 'Approved GL method absent')
    return changes, groups


def _assert_byte_whitelist(original, repaired, words):
    allowed = set(range(8, 32))
    for word in words: allowed.update((word, word + 1))
    need(len(repaired) == len(original) and all(n in allowed for n, (a, b) in enumerate(zip(original, repaired)) if a != b), 'Byte whitelist violation')


def _restore(source, emitted, transformation):
    changes, groups = _plan(source, emitted, transformation)  # complete admission before mutation
    original = emitted.data; result = bytearray(original)
    for word, row in changes.items(): struct.pack_into('<H', result, word, row['wanted'])
    repaired = seal(result)
    _assert_byte_whitelist(original, repaired, changes)
    reparsed = Dex039(repaired); remaining, _ = _plan(source, reparsed, transformation)
    need(not remaining, 'Post-repair outs mismatch')
    need(emitted.classes == reparsed.classes and emitted.methods.keys() == reparsed.methods.keys(), 'Repair changed identity set')
    receipts = [{'offset': word, 'oldOuts': row['actual'], 'sourceOuts': row['wanted'],
        'methodIdentities': [m.decode('utf-8', 'backslashreplace') for m in row['methods']]} for word, row in sorted(changes.items())]
    return repaired, {'declaredMethods': len(source.methods), 'methodsWithCode': sum(bool(m['codeOffset']) for m in source.methods.values()),
        'sourceUniqueCodeItems': len(source.codes), 'emittedUniqueCodeItems': len(emitted.codes),
        'sourceMethodRepairs': sum(len(row['methods']) for row in changes.values()), 'repairedOutsWords': len(changes),
        'sharedOutputCodeGroups': sum(len(row['methods']) > 1 for row in groups.values()), 'repairs': receipts,
        'inputSha256': digest(original), 'repairedSha256': digest(repaired), 'fileSizeUnchanged': True,
        'byteWhitelist': 'Only planned source outs_size uint16 words and DEX signature/checksum bytes8..31',
        'postRepairAllHeadersReparsed': True, 'declaredMethodSetUnchanged': True,
        'instructionMetadataOrAuthorityAcceptance': False}


def preserve_code_headers(source, emitted, *, source_profile, emitted_sha256, transformation='none'):
    """Return (new_bytes, receipt); never write/mutate input or relax other checks.

    Source hashes are fixed. emitted_sha256 is an explicit caller input pin, not
    provenance attestation. Apply after EVERY emit/reemit against ORIGINAL source.
    """
    need(source_profile in SOURCE_PROFILES, 'Unknown source profile')
    pin, size = SOURCE_PROFILES[source_profile]
    need(isinstance(source, bytes) and len(source) == size and digest(source) == pin, 'Literal original source pin')
    need(isinstance(emitted_sha256, str) and len(emitted_sha256) == 64 and all(c in '0123456789abcdef' for c in emitted_sha256), 'Explicit emitted input hash required')
    need(isinstance(emitted, bytes) and digest(emitted) == emitted_sha256, 'Emitted input pin')
    need(transformation == 'none' or source_profile == 'samsung-framework-classes3', 'Transformation/source profile mismatch')
    repaired, receipt = _restore(Dex039(source), Dex039(emitted), transformation)
    receipt.update({'schema': 'dex-code-header-preservation/v1', 'sourceProfile': source_profile,
        'sourceSha256': pin, 'transformation': transformation, 'callerEmittedPinVerified': True,
        'callerEmitterProvenanceAdmittedByThisModule': False, 'moduleSha256': digest(Path(__file__).read_bytes()),
        'applyAfterEveryEmitAndReemit': True, 'oemOrRuntimeExecuted': False})
    return repaired, receipt


def _fixture(outs=(2, 3), *, shared=False, regs=1, ins=1, units=1, flags=(1, 1), names=(b'm0', b'm1'),
             partition='virtual', code_presence=(True, True), tries=0):
    """Small authored valid039 fixture; not an OEM replacement or runtime test."""
    def enc(value):
        output = bytearray()
        while value > 127: output.append((value & 127) | 128); value >>= 7
        output.append(value); return bytes(output)
    strings = [b'Lfixture/C;', b'V', *names]; ns = len(strings)
    offset = 112; string_ids = offset; offset += ns * 4
    types = offset; offset += 8; proto = offset; offset += 12
    methods = offset; offset += 16; classes = offset; offset += 32
    data_start = offset; output = bytearray(offset); code_start = offset; code_offsets = []
    for index, value in enumerate(outs[:1] if shared else outs):
        if not code_presence[index]: code_offsets.append(0); continue
        while len(output) % 4: output.append(0)
        code_offsets.append(len(output)); output.extend(struct.pack('<4HII', regs, ins, value, tries, 0, units))
        output.extend(b'\x0e\x00' * units)
        if tries:
            need(tries == 1, 'Fixture single try only')
            if units & 1: output.extend(b'\0\0')
            output.extend(struct.pack('<IHH', 0, units, 1) + b'\1\0\0')
    if shared: code_offsets *= 2
    while len(output) % 4: output.append(0)
    class_data = len(output); output.extend(b'\0\0\0\2' if partition == 'virtual' else b'\0\0\2\0')
    for index in range(2): output.extend(enc(index) + enc(flags[index]) + enc(code_offsets[index]))
    string_start = len(output); string_offsets = []
    for value in strings: string_offsets.append(len(output)); output.extend(enc(len(value)) + value + b'\0')
    while len(output) % 4: output.append(0)
    map_start = len(output)
    rows = [(0, 1, 0), (1, ns, string_ids), (2, 2, types), (3, 1, proto), (5, 2, methods), (6, 1, classes),
        (0x2001, len(set(code_offsets) - {0}), code_start), (0x2000, 1, class_data), (0x2002, ns, string_start), (0x1000, 1, map_start)]
    rows = [row for row in rows if row[1]]
    output.extend(struct.pack('<I', len(rows)))
    for kind, count, pos in sorted(rows, key=lambda r: r[2]): output.extend(struct.pack('<HHII', kind, 0, count, pos))
    output[:8] = b'dex\n039\0'; struct.pack_into('<III', output, 32, len(output), 112, 0x12345678)
    struct.pack_into('<I', output, 52, map_start)
    for header, count, pos in [(56, ns, string_ids), (64, 2, types), (72, 1, proto), (88, 2, methods), (96, 1, classes)]:
        struct.pack_into('<II', output, header, count, pos)
    struct.pack_into('<II', output, 104, len(output) - data_start, data_start)
    for index, pos in enumerate(string_offsets): struct.pack_into('<I', output, string_ids + 4 * index, pos)
    struct.pack_into('<II', output, types, 0, 1); struct.pack_into('<III', output, proto, 1, 1, 0)
    for index in range(2): struct.pack_into('<HHI', output, methods + 8 * index, 0, 0, index + 2)
    struct.pack_into('<8I', output, classes, 0, 1, 0xffffffff, 0, 0xffffffff, 0, class_data, 0)
    return seal(output)


def self_test():
    source = _fixture(); emitted = _fixture((0, 0)); a, b = Dex039(source), Dex039(emitted)
    fixed, receipt = _restore(a, b, 'none'); need(fixed == source, 'Fixture exact repair')
    again, no_change = _restore(a, Dex039(fixed), 'none'); need(again == fixed and no_change['repairedOutsWords'] == 0, 'Idempotence')
    tests = ['exact-outs-repair', 'idempotence']
    negatives = {'registers': _fixture((0, 0), regs=2), 'incoming': _fixture((0, 0), ins=0),
        'instruction-count': _fixture((0, 0), units=2), 'method-flags': _fixture((0, 0), flags=(17, 1)),
        'partition': _fixture((0, 0), partition='direct'), 'code-presence': _fixture((0, 0), code_presence=(True, False)),
        'try-count': _fixture((0, 0), tries=1),
        'identity': _fixture((0, 0), names=(b'n0', b'm1')), 'alias-conflict': _fixture((0, 0), shared=True)}
    for name, bad in negatives.items():
        try: _restore(a, Dex039(bad), 'none')
        except ValueError: tests.append('reject-' + name)
        else: raise ValueError('Negative fixture accepted: ' + name)
    for name, bad in [('checksum', emitted[:-1] + bytes([emitted[-1] ^ 1])), ('short', b'dex\n039\0'), ('041', b'dex\n041\0' + emitted[8:])]:
        try: Dex039(bad)
        except ValueError: tests.append('reject-' + name)
        else: raise ValueError('Malformed fixture accepted: ' + name)
    need(receipt['repairedOutsWords'] == 2 and receipt['sourceMethodRepairs'] == 2, 'Fixture repair count')
    unexpected = bytearray(fixed); unexpected[next(iter(Dex039(fixed).codes)) + 16] ^= 1
    try: _assert_byte_whitelist(emitted, seal(unexpected), [p['offset'] for p in receipt['repairs']])
    except ValueError: tests.append('reject-nonword-byte-mutation')
    else: raise ValueError('Byte whitelist accepted unrelated instruction mutation')
    try: _restore(a, b, 'samsung-permission-gl-jumbo-v1')
    except ValueError: tests.append('reject-missing-exact-gl-method')
    else: raise ValueError('GL profile accepted unrelated fixture')
    return {'pass': True, 'cases': tests, 'count': len(tests), 'oemOrRuntimeExecuted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test: print(json.dumps(self_test())); return
    parser.error('Use the frozen import API; saved-output runner is separately pinned after source review')


if __name__ == '__main__': main()
