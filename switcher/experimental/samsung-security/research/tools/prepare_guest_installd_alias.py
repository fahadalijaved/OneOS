"""Prepare one publisher-pointer retarget; no ELF emission is exposed by this CLI.

Only --plan runs here. apply_approved_profile is an unexecuted, fixed-profile
pure-byte producer for later review, not permission to emit or launch an ELF.
"""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import lzma
import runpy
import struct
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'firmware/guest-installd-alias'
OUT = ROOT / 'out/guest-installd-alias'
SOURCE = ROOT / 'firmware/retained-installd-native-owner/20261106T024945006359Z-7b005bf1d2054ec4821a3e3ebdfdf978/installd'
SOURCE_SHA = 'ed618c386528c0b9890c67cbdcb22e1c194f44b034d8e36be2d7f2217fef7dfc'
SOURCE_SIZE = 640912
PATCH = 0x26238
BEFORE = bytes.fromhex('219c0791')
AFTER = bytes.fromhex('21a00791')
ORIGINAL_LITERAL = 0x101e7
ALIAS_LITERAL = 0x101e8
ALIAS = b'nstalld\0'
DESCRIPTOR = 0x9351c
DESCRIPTOR_BYTES = 'android.os.IInstalld'.encode('utf-16le') + b'\0\0'
PARSER_SHA = '33c005e05b884ce03f4b57d3e288a62211abb78a2203ee8f3834bdce8a7d9831'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')


def replace_exact_word(blob, offset, before, after):
    """Pure bounded helper; actual OEM apply is deliberately not called by plan."""
    if len(before) != 4 or len(after) != 4 or offset % 4 or offset < 0 or offset + 4 > len(blob):
        raise ValueError('Exact aligned four-byte replacement required')
    if blob[offset:offset + 4] != before:
        raise ValueError('Before-word mismatch')
    return blob[:offset] + after + blob[offset + 4:]


def require_original(source):
    if len(source) != SOURCE_SIZE or sha(source) != SOURCE_SHA:
        raise ValueError('Exact original ed618 profile required')
    if source[PATCH:PATCH + 4] != BEFORE or source[ORIGINAL_LITERAL:ORIGINAL_LITERAL + 9] != b'installd\0':
        raise ValueError('Original publisher/literal mismatch')
    if source[ALIAS_LITERAL:ALIAS_LITERAL + len(ALIAS)] != ALIAS or source[DESCRIPTOR:DESCRIPTOR + len(DESCRIPTOR_BYTES)] != DESCRIPTOR_BYTES:
        raise ValueError('Alias suffix/UTF16 descriptor mismatch')


def apply_approved_profile(source):
    """UNEXECUTED on OEM input. Root must separately approve actual emission."""
    require_original(source)
    result = replace_exact_word(source, PATCH, BEFORE, AFTER)
    changed = [i for i, (a, b) in enumerate(zip(source, result)) if a != b]
    if changed != [PATCH + 1] or len(result) != len(source):
        raise ValueError('Exact one-byte output whitelist failed')
    inverse = replace_exact_word(result, PATCH, AFTER, BEFORE)
    if inverse != source:
        raise ValueError('Exact inverse failed')
    return result


def inverse_approved_profile(source, emitted, *, emitted_sha256):
    """UNEXECUTED on OEM output; fixed-source/full-output/byte-whitelist inverse."""
    require_original(source)
    if len(emitted) != len(source) or sha(emitted) != emitted_sha256:
        raise ValueError('Exact actual output hash/size required')
    if emitted[:PATCH] != source[:PATCH] or emitted[PATCH + 4:] != source[PATCH + 4:] or emitted[PATCH:PATCH + 4] != AFTER:
        raise ValueError('Only the fixed publisher ADD may differ')
    result = replace_exact_word(emitted, PATCH, AFTER, BEFORE)
    if result != source or sha(result) != SOURCE_SHA:
        raise ValueError('Full inverse/original identity failed')
    return result


def decode_relr(blob):
    """Bounded ELF64 RELR words, including Android SHT_ANDROID_RELR encoding."""
    if not blob or len(blob) % 8 or len(blob) > 65536:
        raise ValueError('Bounded whole ELF64 RELR words required')
    targets = []
    cursor = None
    for (entry,) in struct.iter_unpack('<Q', blob):
        if entry & 1:
            if cursor is None:
                raise ValueError('RELR bitmap before address')
            targets.extend(cursor + n * 8 for n in range(63) if entry & (1 << (n + 1)))
            cursor += 63 * 8
        else:
            if entry % 8:
                raise ValueError('Unaligned ELF64 RELR target')
            targets.append(entry)
            cursor = entry + 8
        if len(targets) > 65536 or cursor >= 1 << 64:
            raise ValueError('RELR expansion/target bound')
    if targets != sorted(set(targets)):
        raise ValueError('Nonmonotonic/duplicate RELR targets')
    return targets


def fixture_checks():
    fixture = b'\0' * 8 + BEFORE + b'\0' * 20
    changed = replace_exact_word(fixture, 8, BEFORE, AFTER)
    assert replace_exact_word(changed, 8, AFTER, BEFORE) == fixture
    assert [i for i, (a, b) in enumerate(zip(fixture, changed)) if a != b] == [9]
    refused = 0
    for args in [(fixture, -4, BEFORE, AFTER), (fixture, 9, BEFORE, AFTER),
                 (fixture, 32, BEFORE, AFTER), (fixture, 8, AFTER, BEFORE),
                 (fixture, 8, BEFORE[:3], AFTER), (fixture, 8, BEFORE, AFTER + b'\0')]:
        try:
            replace_exact_word(*args)
        except ValueError:
            refused += 1
        else:
            raise AssertionError('Malformed fixture accepted')
    try:
        apply_approved_profile(fixture)
    except ValueError:
        refused += 1
    else:
        raise AssertionError('Unpinned actual-profile producer accepted fixture')
    assert refused == 7
    assert decode_relr(struct.pack('<QQ', 0x100, 0b1011)) == [0x100, 0x108, 0x118]
    relr_refused = 0
    for malformed in [b'\0' * 7, struct.pack('<Q', 1), struct.pack('<Q', 0x102), struct.pack('<QQ', 0x100, 0x100)]:
        try:
            decode_relr(malformed)
        except ValueError:
            relr_refused += 1
        else:
            raise AssertionError('Malformed RELR fixture accepted')
    assert relr_refused == 4
    return {'positiveAuthoredFixture': 2, 'negativeAuthoredFixtures': 11,
            'breakdown': 'word replacement/inverse 1positive7negative; RELR decoding 1positive4negative',
            'scope': 'authored buffers only; no actual OEM output/inverse result exists'}


def plan():
    source = SOURCE.read_bytes()
    require_original(source)
    parser_path = ROOT / 'tools/audit_security_native_linkage.py'
    assert sha(parser_path.read_bytes()) == PARSER_SHA
    elf = runpy.run_path(str(parser_path))['elf']
    parsed = elf(source)
    assert parsed['machine'] == 183
    assert struct.unpack_from('<H', source, 16)[0] == 3, 'Exact PIE ET_DYN profile required'
    sections = parsed['sections']
    debug, = [s for s in sections if s['name'] == '.gnu_debugdata']
    mini = lzma.decompress(source[debug['offset']:debug['offset'] + debug['bytes']], memlimit=32 * 1024 * 1024)
    assert len(mini) < 8 * 1024 * 1024
    symbols = parsed['dynamicSymbols'] + elf(mini)['dynamicSymbols']
    sys.path.insert(0, str(ROOT / 'out/security-native/static-disassembler'))
    import capstone
    cs = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    cs.detail = True
    original_decoded = list(cs.disasm(BEFORE, PATCH))
    assert len(original_decoded) == 1 and original_decoded[0].mnemonic == 'add' and original_decoded[0].op_str == 'x1, x1, #0x1e7'
    decoded = list(cs.disasm(AFTER, PATCH))
    assert len(decoded) == 1 and decoded[0].mnemonic == 'add' and decoded[0].op_str == 'x1, x1, #0x1e8'
    text, = [s for s in sections if s['name'] == '.text']
    rodata, = [s for s in sections if s['name'] == '.rodata']
    assert text['offset'] == text['address'] and rodata['offset'] == rodata['address']
    assert text['address'] <= PATCH < text['address'] + text['bytes']
    assert rodata['address'] <= ORIGINAL_LITERAL < rodata['address'] + rodata['bytes']
    references = []
    pages = {}
    branch_targets = []
    count = 0
    for ins in cs.disasm(source[text['offset']:text['offset'] + text['bytes']], text['address']):
        count += 1
        if ins.mnemonic == 'adrp':
            register, address = ins.op_str.split(', ')
            pages[register] = (int(address[1:], 0), ins.address)
        candidate = None
        if ins.mnemonic == 'adr' and len(ins.operands) == 2 and ins.operands[1].type == capstone.CS_OP_IMM:
            candidate = ins.operands[1].imm
        if ins.mnemonic == 'add' and len(ins.operands) == 3 and ins.operands[2].type == capstone.CS_OP_IMM:
            register = ins.reg_name(ins.operands[1].reg)
            if register in pages and ins.address - pages[register][1] <= 40:
                candidate = pages[register][0] + ins.operands[2].imm
        if candidate is not None and ORIGINAL_LITERAL <= candidate < ORIGINAL_LITERAL + 9:
            containing = [s for s in symbols if s['sectionIndex'] and s['type'] == 2 and s['value'] <= ins.address < s['value'] + s['size']]
            names = sorted(set(s['name'] for s in containing))
            references.append({'pc': ins.address, 'pcHex': hex(ins.address), 'instructionBytes': ins.bytes.hex(),
                               'mnemonic': ins.mnemonic, 'operands': ins.op_str, 'literalAddress': candidate,
                               'containingSymbols': names, 'isPublisherPatch': ins.address == PATCH})
        if ins.mnemonic in ('b', 'bl') and ins.op_str.startswith('#0x') and int(ins.op_str[1:], 16) == PATCH:
            branch_targets.append(ins.address)
    assert count * 4 == text['bytes']
    assert len([r for r in references if r['isPublisherPatch']]) == 1
    exact_literal_sites = [r for r in references if r['literalAddress'] == ORIGINAL_LITERAL]
    owners = Counter(n for r in exact_literal_sites for n in r['containingSymbols'])
    assert len(references) == len(exact_literal_sites) == 244 and len(owners) == 43
    assert all(r['containingSymbols'] for r in references)
    # RELA includes normal + Android APS2; this exact source also uses Android RELR.
    relr_section, = [s for s in sections if s['type'] in (19, 0x6fffff00)]
    assert (relr_section['name'], relr_section['type'], relr_section['address'], relr_section['offset'], relr_section['bytes']) == ('.relr.dyn', 0x6fffff00, 0x7d40, 0x7d40, 264)
    relr_targets = decode_relr(source[relr_section['offset']:relr_section['offset'] + relr_section['bytes']])
    dynamic, = [s for s in sections if s['type'] == 6]
    tags = dict(struct.unpack_from('<qQ', source, o) for o in range(dynamic['offset'], dynamic['offset'] + dynamic['bytes'], 16))
    assert (tags[0x6fffe000], tags[0x6fffe001], tags[0x6fffe003]) == (0x7d40, 264, 8)
    relr_records = []
    for address in relr_targets:
        backing, = [s for s in sections if s['type'] != 8 and s['address'] <= address and address + 8 <= s['address'] + s['bytes']]
        file_offset = backing['offset'] + address - backing['address']
        addend = struct.unpack_from('<Q', source, file_offset)[0]
        relr_records.append({'target': address, 'fileOffset': file_offset, 'addend': addend})
    overlapping_relocations = [r for r in parsed['rela'] if r['target'] < PATCH + 4 and r['target'] + 8 > PATCH]
    overlapping_relocations += [r for r in relr_records if r['target'] < PATCH + 4 and r['target'] + 8 > PATCH]
    assert not overlapping_relocations
    pointer_aliases = [r for r in parsed['rela'] if ORIGINAL_LITERAL <= r['addend'] < ORIGINAL_LITERAL + 9]
    relr_aliases = [r for r in relr_records if ORIGINAL_LITERAL <= r['addend'] < ORIGINAL_LITERAL + 9]
    word_aliases = [offset for offset in range(0, len(source) - 7, 8)
                    if ORIGINAL_LITERAL <= struct.unpack_from('<Q', source, offset)[0] < ORIGINAL_LITERAL + 9]
    assert not branch_targets
    phoff = struct.unpack_from('<Q', source, 32)[0]
    phentsize, phnum = struct.unpack_from('<HH', source, 54)
    assert phentsize == 56 and phnum <= 128
    programs = []
    for n in range(phnum):
        ptype, flags, offset, va, pa, filesz, memsz, align = struct.unpack_from('<IIQQQQQQ', source, phoff + n * 56)
        programs.append({'type': ptype, 'flags': flags, 'offset': offset, 'virtualAddress': va,
                         'fileBytes': filesz, 'memoryBytes': memsz, 'alignment': align})
    load, = [p for p in programs if p['type'] == 1 and p['offset'] <= PATCH and PATCH + 4 <= p['offset'] + p['fileBytes']]
    assert load['flags'] & 1 and not load['flags'] & 2
    note = next(s for s in sections if s['name'] == '.note.gnu.property')
    note_bytes = source[note['offset']:note['offset'] + note['bytes']]
    assert note_bytes.hex() == '040000001000000005000000474e5500000000c0040000000300000000000000'
    build_note = next(s for s in sections if s['name'] == '.note.gnu.build-id')
    build_bytes = source[build_note['offset']:build_note['offset'] + build_note['bytes']]
    preserved_sections = [s for s in sections if s['name'] in ('.rodata', '.note.gnu.property', '.note.gnu.build-id', '.eh_frame', '.eh_frame_hdr', '.gnu_debugdata', '.data.rel.ro')]
    save(RAW / 'literal-xrefs.json', {'sourceSha256': SOURCE_SHA, 'textInstructionsScanned': count,
                                   'query': 'one literal range 0x101e7..0x101ef only', 'references': references,
                                   'relocationAddendAliases': pointer_aliases, 'alignedPointerWords': word_aliases,
                                   'androidRelr': {'section': relr_section, 'encodedWords': 33, 'records': relr_records, 'literalAliases': relr_aliases},
                                   'scope': 'ADR and local ADRP/ADD<=40-byte patterns plus relocation addends/pointer words; not complete computed-pointer dataflow'})
    fixtures = fixture_checks()
    history_path = ROOT / 'out/guest-installd-alias/history/before-android-relr-correction/history.json'
    history_sha = 'ff1aa52a5ea1ab83c4436ca0630559ec2b74fb46664f453542e9dd9c30a6e04c'
    assert sha(history_path.read_bytes()) == history_sha
    for prior in json.loads(history_path.read_text(encoding='utf-8'))['files']:
        assert sha((ROOT / prior['retainedAt']).read_bytes()) == prior['beforeSha256']
    inventory = {
        'schema': 'guest-installd-alias-plan/1', 'status': 'PRE_EMISSION_SOURCE_PROPOSAL', 'selected': False,
        'artifactEmitted': False, 'oemExecuted': False, 'deviceAccess': False, 'cloneLaunched': False,
        'source': {'path': SOURCE.relative_to(ROOT).as_posix(), 'sha256': SOURCE_SHA, 'size': SOURCE_SIZE},
        'tool': {'path': 'tools/prepare_guest_installd_alias.py', 'sha256': sha(Path(__file__).read_bytes())},
        'patch': {'fileOffset': PATCH, 'virtualAddress': PATCH, 'length': 4, 'beforeHex': BEFORE.hex(), 'afterHex': AFTER.hex(),
                  'changedByteOffsets': [PATCH + 1], 'before': 'add x1,x1,#0x1e7', 'after': 'add x1,x1,#0x1e8',
                  'originalStringAddress': ORIGINAL_LITERAL, 'proposedAliasAddress': ALIAS_LITERAL,
                  'originalName': 'installd', 'proposedName': 'nstalld', 'nameIsNotRuntimeAdmission': True},
        'xrefEvidence': {'raw': 'firmware/guest-installd-alias/literal-xrefs.json', 'rawSha256': sha((RAW / 'literal-xrefs.json').read_bytes()),
                         'textInstructionsScanned': count, 'literalRangeCandidates': len(references),
                         'originalLiteralCandidates': len(exact_literal_sites), 'relocationAddendAliases': len(pointer_aliases),
                         'androidRelrLiteralAliases': len(relr_aliases),
                         'containingSymbolCounts': dict(sorted(owners.items())),
                         'alignedPointerWords': len(word_aliases), 'directBranchesToPatchedInstruction': branch_targets,
                         'limits': 'static encoded reference patterns; unresolved computed aliases remain harmless to unchanged literal bytes, not a global xref-completeness claim'},
        'descriptor': {'fileOffset': DESCRIPTOR, 'encoding': 'UTF16LE', 'text': 'android.os.IInstalld',
                       'sha256': sha(DESCRIPTOR_BYTES), 'bytesRemainUntouchedByContract': True},
        'elf': {'programHeaders': programs, 'patchLoadSegment': load, 'overlappingRelocationCount': len(overlapping_relocations),
                'androidRelr': {'type': '0x6fffff00', 'encodedWords': 33, 'decodedTargets': len(relr_targets),
                                'dynamicAddress': '0x7d40', 'dynamicSize': 264, 'entryBytes': 8, 'overlapWithPatch': False},
                'gnuPropertyNoteHex': note_bytes.hex(),
                'gnuAarch64Feature1And': 3, 'btiBit': True, 'pacBit': True,
                'buildIdNoteHex': build_bytes.hex(),
                'buildIdScope': 'preserved historical source build-id; future modified artifact must be identified by its actual full SHA, never this unchanged note alone',
                'preservedSections': [{'name': s['name'], 'offset': s['offset'], 'size': s['bytes'],
                                       'sha256': sha(source[s['offset']:s['offset'] + s['bytes']])} for s in preserved_sections],
                'contract': 'fixed-width nonbranch ADD only; unchanged file size/all headers/sections/relocations/entry instructions/BTI-PAC/unwind and all other bytes'},
        'inverseContract': 'same source profile plus exact output full SHA from a future authorized actual run; only AFTER→BEFORE at0x26238; require full original SHA and byte equality. No current actual output/inverse exists.',
        'fixtures': fixtures,
        'supersededHistory': {'path': 'out/guest-installd-alias/history/before-android-relr-correction/history.json',
                              'sha256': history_sha,
                              'reason': 'prior standard-SHT_RELR-only guard missed Android .relr.dyn; retained old source/docs/inventory/receipt/freeze, no ELF emitted'},
        'requiredBeforeEmission': ['Root accepted suffixalias spelling as unselected discriminator; independent source review and root one-emission gate still required; no emit CLI exists.'],
        'requiredBeforeRuntimeSelection': [
            'Actual endpoint name collision/identity, service-manager policy and complete guest lookup/proxy/death/reconnect routing.',
            'Real private pre-main data/root/mount/propagation/property/library/SELinux-capability owner; replace/segregate all14globalbinds.',
            'Preserve host canonical endpoint/old handles and genuine native/data/user/callback/drain ownership.',
            'Verify actual loaded cohort and original IInstalld protocol/caller/UID/generation/ABI contracts; no readiness from alias/PID.',
        ],
    }
    save(ROOT / 'inventory/guest-installd-alias.json', inventory)
    save(OUT / 'plan-receipt.json', {'status': inventory['status'], 'artifactEmitted': False, 'fixtures': fixtures,
                                   'inventorySha256': sha((ROOT / 'inventory/guest-installd-alias.json').read_bytes()),
                                   'toolSha256': inventory['tool']['sha256']})
    assert sha(SOURCE.read_bytes()) == SOURCE_SHA
    print(json.dumps({'status': inventory['status'], 'patch': inventory['patch'],
                      'xrefCounts': {k: v for k, v in inventory['xrefEvidence'].items() if isinstance(v, int)},
                      'androidRelr': inventory['elf']['androidRelr'],
                      'fixtures': fixtures, 'artifactEmitted': False}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', action='store_true', required=True)
    parser.parse_args()
    plan()
