"""Bounded static Samsung installd ELF source reader. Never loads or runs OEM code."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import lzma
import re
import runpy
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'firmware/retained-installd-native-owner/static'
OUT = ROOT / 'out/retained-installd-native-owner/static'
SOURCE = ROOT / 'firmware/retained-installd-native-owner/20261106T024945006359Z-7b005bf1d2054ec4821a3e3ebdfdf978/installd'
SOURCE_SHA = 'ed618c386528c0b9890c67cbdcb22e1c194f44b034d8e36be2d7f2217fef7dfc'
PARSER = ROOT / 'tools/audit_security_native_linkage.py'
WANTED = ['main', '_ZN7android8installd31init_globals_from_data_and_rootEv',
          '_ZN7android8installd21InstalldNativeService14createUserData',
          '_ZN7android8installd12_GLOBAL__N_115LocalLockHolderIjNSt3__112shared_mutexEEC2E',
          '_ZN7android8installd21InstalldNativeService5startEv',
          '_ZN7android8installd23ensure_config_user_dirsEj',
          '_ZN7android8installd16create_data_pathEPKc',
          '_ZN7android8installd24create_data_user_ce_pathEPKcj',
          '_ZN7android8installd28create_data_misc_legacy_pathEj',
          '_ZN7android8installd21InstalldNativeService18tryMountDataMirror',
          '_ZN7android8installd21InstalldNativeService12migrateSdpDb',
          '_ZN7android8installd21InstalldNativeService16invalidateMountsEv',
          '_ZN7android8installd21InvalidateQuotaMountsEv',
          '_ZN7android8installd12_GLOBAL__N_18checkUidEj']
CAPTURE_SHA = 'f2757c2e7ad01594e9e48e19371c27b38fd55e20883752b2b3ffe54ee8bd384c'
RAW_SHA = '073ce4abb6ed496693e57a529b7a6e7c9d24d8785df7f20135db5ea79a02f776'
PARSER_SHA = '33c005e05b884ce03f4b57d3e288a62211abb78a2203ee8f3834bdce8a7d9831'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def capture():
    assert SOURCE.stat().st_size == 640912 and sha(SOURCE) == SOURCE_SHA
    parser_sha = sha(PARSER)
    assert parser_sha == PARSER_SHA
    elf = runpy.run_path(str(PARSER))['elf']
    data = SOURCE.read_bytes()
    parsed = elf(data)
    assert parsed['machine'] == 183
    sections = parsed['sections']
    debug, = [s for s in sections if s['name'] == '.gnu_debugdata']
    mini = lzma.decompress(data[debug['offset']:debug['offset'] + debug['bytes']], memlimit=32 * 1024 * 1024)
    assert len(mini) < 8 * 1024 * 1024
    symbols = parsed['dynamicSymbols'] + elf(mini)['dynamicSymbols']
    sys.path.insert(0, str(ROOT / 'out/security-native/static-disassembler'))
    import capstone
    cs = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    cs.detail = True

    def offset(addr, count=1):
        s, = [s for s in sections if s['type'] != 8 and s['address'] <= addr and addr + count <= s['address'] + s['bytes']]
        return s['offset'] + addr - s['address']

    def string(addr):
        try:
            off = offset(addr)
            end = data.index(b'\0', off, min(len(data), off + 512))
            v = data[off:end]
            return v.decode('ascii') if v and all(32 <= c < 127 or c in (9, 10, 13) for c in v) else None
        except (ValueError, UnicodeError):
            return None

    plt, = [s for s in sections if s['name'] == '.plt']
    slots = [r for r in parsed['rela'] if r['type'] == 1026]

    def call_symbol(addr):
        if plt['address'] + 32 <= addr < plt['address'] + plt['bytes'] and (addr - plt['address'] - 32) % 24 == 0:
            relocation = slots[(addr - plt['address'] - 32) // 24]
            stub = list(cs.disasm(data[offset(addr, 24):offset(addr, 24) + 24], addr))
            adrp = next(i for i in stub if i.mnemonic == 'adrp' and i.op_str.startswith('x16,'))
            load = next(i for i in stub if i.mnemonic == 'ldr' and i.op_str.startswith('x17,'))
            disp = re.search(r'#(0x[0-9a-f]+|\d+)', load.op_str)
            assert int(adrp.op_str.split('#')[1], 16) + (int(disp.group(1), 0) if disp else 0) == relocation['target']
            return parsed['dynamicSymbols'][relocation['symbolIndex']]['name']
        names = [s['name'] for s in symbols if s['sectionIndex'] and s['value'] == addr]
        return names[0] if names else None

    functions = []
    seen = set()
    for sym in symbols:
        if not sym['sectionIndex'] or sym['type'] != 2 or not sym['size'] or sym['value'] in seen:
            continue
        if not any(sym['name'] == key or key != 'main' and sym['name'].startswith(key) for key in WANTED):
            continue
        assert sym['size'] <= 16384
        seen.add(sym['value'])
        off = offset(sym['value'], sym['size'])
        code = data[off:off + sym['size']]
        instructions = []
        pages = {}
        for ins in cs.disasm(code, sym['value']):
            row = {'pc': ins.address, 'bytes': ins.bytes.hex(), 'mnemonic': ins.mnemonic, 'operands': ins.op_str}
            if ins.mnemonic == 'adr' and len(ins.operands) == 2 and ins.operands[1].type == capstone.CS_OP_IMM:
                addr = ins.operands[1].imm
                row['localAddress'] = addr
                text = string(addr)
                if text:
                    row['literalAddress'] = addr
                    row['literal'] = text
            if ins.mnemonic == 'adrp':
                reg, value = ins.op_str.split(', ')
                pages[reg] = (int(value[1:], 0), ins.address)
            if ins.mnemonic == 'add' and len(ins.operands) == 3 and ins.operands[2].type == capstone.CS_OP_IMM:
                src = ins.reg_name(ins.operands[1].reg)
                if src in pages and ins.address - pages[src][1] <= 40:
                    addr = pages[src][0] + ins.operands[2].imm
                    text = string(addr)
                    row['localAddress'] = addr
                    if text:
                        row['literalAddress'] = addr
                        row['literal'] = text
                        row['adrpPc'] = pages[src][1]
            if ins.mnemonic in ('bl', 'b') and ins.op_str.startswith('#0x'):
                target = int(ins.op_str[1:], 16)
                row['targetPc'] = target
                name = call_symbol(target)
                if name:
                    row['targetSymbol'] = name
            instructions.append(row)
        assert len(instructions) * 4 == len(code)
        functions.append({'symbol': sym['name'], 'address': sym['value'], 'fileOffset': off, 'bytes': len(code),
                          'sha256': hashlib.sha256(code).hexdigest(), 'instructions': instructions})
    assert len(functions) == len(WANTED), [(f['symbol'], f['bytes']) for f in functions]
    assert sha(SOURCE) == SOURCE_SHA and sha(PARSER) == parser_sha
    save(RAW / 'selected-native.json', {'sourceSha256': SOURCE_SHA, 'pcKind': 'ELF virtual addresses, not live PCs',
                                      'functions': functions, 'annotationLimits': 'local ADRP/ADD and direct/PLT edges only; not execution or general dataflow'})
    save(OUT / 'capture.json', {'source': SOURCE.relative_to(ROOT).as_posix(), 'sourceSha256': SOURCE_SHA,
                              'parser': PARSER.relative_to(ROOT).as_posix(), 'parserSha256': parser_sha,
                              'raw': (RAW / 'selected-native.json').relative_to(ROOT).as_posix(), 'rawSha256': sha(RAW / 'selected-native.json'),
                              'capstoneVersion': capstone.__version__, 'needed': parsed['needed'],
                              'functions': [{k: v for k, v in f.items() if k != 'instructions'} for f in functions],
                              'oemExecuted': False})
    print(json.dumps({'status': 'static-capture-only', 'functions': len(functions), 'instructions': sum(len(f['instructions']) for f in functions)}))


def audit():
    assert sha(SOURCE) == SOURCE_SHA and sha(PARSER) == PARSER_SHA
    assert sha(OUT / 'capture.json') == CAPTURE_SHA
    assert sha(RAW / 'selected-native.json') == RAW_SHA
    captured = json.loads((OUT / 'capture.json').read_text(encoding='utf-8'))
    raw = json.loads((RAW / 'selected-native.json').read_text(encoding='utf-8'))
    binary = SOURCE.read_bytes()
    index = {}
    for f in raw['functions']:
        part = binary[f['fileOffset']:f['fileOffset'] + f['bytes']]
        assert hashlib.sha256(part).hexdigest() == f['sha256']
        assert b''.join(bytes.fromhex(i['bytes']) for i in f['instructions']) == part
        for i in f['instructions']:
            assert i['pc'] not in index
            index[i['pc']] = i
    assert len(raw['functions']) == 14 and len(index) == 3932
    checks = []

    def check(pc, field, expected):
        assert index[pc][field] == expected, (hex(pc), field, index[pc].get(field), expected)
        checks.append({'pc': pc, 'pcHex': hex(pc), 'field': field, 'expected': expected})

    def target(pc, fragment):
        assert 'targetSymbol' in index[pc], (hex(pc), index[pc])
        assert fragment in index[pc]['targetSymbol'], (hex(pc), index[pc])
        checks.append({'pc': pc, 'pcHex': hex(pc), 'targetContains': fragment})

    for pc, text in [
        (0x26238, 'installd'), (0x263cc, 'persist.zygote.app_data_isolation'),
        (0x743c0, 'ANDROID_DATA'), (0x743d4, 'ANDROID_ROOT'),
        (0x8ac84, '%smisc/installd/layout_version'), (0x8adc8, '/data/user'),
        (0x7a210, '%s/misc/user/%u'), (0x79034, '%s/user/%u'),
        (0x79324, '/mnt/expand/%s'), (0x3f98c, '/data_mirror/data_ce'),
        (0x3fab0, '/data_mirror/data_de'), (0x3fb2c, '/data_mirror/misc_ce'),
        (0x3fba8, '/data_mirror/misc_de'), (0x3ee18, '/proc/mounts'),
        (0x64440, '/proc/mounts'), (0x3ee80, 'persist.sys.fuse'),
        (0x4359c, 'pragma sdp_get_engine_id;'),
        (0x7e0a0, 'fs_prepare_dir'),
        (0x43768, 'pragma sdp_set_engine_id("engine_id=%d");'),
    ]:
        check(pc, 'literal', text)
    for pc, op in [
        (0x2633c, 'w3, wzr'), (0x26340, 'w4, #8'), (0x26344, 'x8, [x8, #0x30]'),
        (0x26348, 'x8'), (0x26390, 'w19, #0x26430'),
        (0x263d8, 'w1, #1'), (0x790e0, 'x20, #0x7913c'),
        (0x79140, 'w9, #0x642f'), (0x79144, 'w9, #0x7461, lsl #16'),
        (0x7914c, 'w8, #0x61'), (0x79150, 'w9, [x19, #1]'),
        (0x79154, 'w8, [x19, #5]'), (0x26c74, 'w0, #0x3e8'),
        (0x26c80, 'w0, #0x26c9c'), (0x43488, 'x23, x1'),
        (0x43564, 'x0, x23'), (0x4371c, 'x0, x23'),
    ]:
        check(pc, 'operands', op)
    for pc, fragment in [
        (0x2622c, 'defaultServiceManager'), (0x262a4, 'BnInstalldC2'),
        (0x263a4, 'startThreadPool'), (0x263ac, 'giveThreadPoolName'),
        (0x263e8, 'GetBoolProperty'), (0x8ac50, 'init_globals'),
        (0x8acac, 'fs_read_atomic_int'), (0x8acc8, 'ensure_config_user_dirs'),
        (0x8ad04, 'ensure_config_user_dirs'), (0x8af74, 'copy_dir_files'),
        (0x8b018, 'delete_dir_contents'), (0x8b070, 'fs_write_atomic_int'),
        (0x8b088, 'selinux_status_open'), (0x8b090, 'NativeService5start'),
        (0x8b0a0, 'joinThreadPool'), (0x7e098, 'create_data_misc_legacy_path'),
        (0x7e0c4, 'fs_prepare_dir'),
        (0x3463c, 'checkUid'), (0x346b4, 'LocalLockHolder'),
        (0x346c0, 'shared_mutex_base4lock'), (0x347ac, 'ensure_config_user_dirs'),
        (0x2894c, 'recursive_mutex4lock'), (0x28d4c, 'shared_mutex_baseC1'),
        (0x26c70, 'getCallingUid'), (0x3ed6c, 'recursive_mutex4lock'),
        (0x3ed74, 'clearEv'), (0x3ed78, 'InvalidateQuotaMounts'),
        (0x64334, 'recursive_mutex4lock'), (0x64340, 'clearEv'),
        (0x645fc, 'quotactl'), (0x40050, 'mount'), (0x400b4, 'mount'),
        (0x40104, 'mount'), (0x40154, 'mount'), (0x434d4, 'recursive_mutex4lock'),
        (0x43568, 'sqlite3_open'), (0x43720, 'sqlite3_open'), (0x43794, 'sqlite3_exec'),
    ]:
        target(pc, fragment)
    # The exact inspected branch constructs the short string /data, not an environment-derived path.
    assert (0x642f | (0x7461 << 16)).to_bytes(4, 'little') + b'a' == b'/data'
    inputs = {
        'out/retained-installd-native-owner/20261106T024945006359Z-7b005bf1d2054ec4821a3e3ebdfdf978/acquisition.json': '1e143424ec729ba2b47868b32057bca3504be179cea5b2a88e92bfb0c4857b45',
        'out/installed-oneos-code-profile/static/appdata-bridge-source.json': '07e8bcf175ece148ae86a7d81435fbe0c40bdb9b6fab4aeffa8d91702691c040',
        'firmware/retained-installd-native-owner/static/samsung-installd.rc': 'fcb59d1c3f8e49c5348d383805ca287b54c24d8f8fc3b70378078736676ed4a2',
        '../out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84/samsung-manifest.jsonl.gz': '6654252d9f7bde941e367fe79eb9af541869f4a1ddb5d1b8a0f0d4d6dde57a7a',
    }
    for path, value in inputs.items():
        assert sha(ROOT / path) == value
    bridge = json.loads((ROOT / 'out/installed-oneos-code-profile/static/appdata-bridge-source.json').read_text(encoding='utf-8'))
    assert len(bridge['bridgePairs']) == 14
    for value in bridge['assets'].values():
        assert sha(ROOT / value['path']) == value['sha256']
    rc = (RAW / 'samsung-installd.rc').read_text(encoding='utf-8')
    assert 'service installd /system/bin/installd' in rc and '    user root' in rc
    assert 'capabilities CHOWN DAC_OVERRIDE DAC_READ_SEARCH FOWNER FSETID KILL SETGID SETUID SYS_ADMIN' in rc
    acquisition = json.loads((ROOT / next(iter(inputs))).read_text(encoding='utf-8'))
    assert acquisition['code']['sha256'] == SOURCE_SHA and acquisition['observedPid'] == 2493
    manifest_path = next(p for p in inputs if p.endswith('samsung-manifest.jsonl.gz'))
    selected_manifest = {}
    with gzip.open(ROOT / manifest_path, 'rt', encoding='utf-8') as handle:
        for line in handle:
            record = json.loads(line)
            if record['path'] in ('system/bin/installd', 'system/etc/init/installd.rc'):
                assert record['path'] not in selected_manifest and record['kind'] == 'file'
                selected_manifest[record['path']] = record
    assert selected_manifest['system/bin/installd']['sha256'] == SOURCE_SHA
    assert selected_manifest['system/etc/init/installd.rc']['sha256'] == inputs['firmware/retained-installd-native-owner/static/samsung-installd.rc']
    result = {
        'schema': 'retained-installd-native-owner/1', 'status': 'BOUNDED_SOURCE_FEASIBILITY_ONLY',
        'selected': False, 'cloneLaunched': False, 'nativeExecuted': False, 'runtimeAcceptance': False,
        'source': {'path': SOURCE.relative_to(ROOT).as_posix(), 'sha256': SOURCE_SHA, 'bytes': len(binary)},
        'acquisitionScope': 'root-acquired /proc/2493/exe bytes; PID/start stable; not Binder recipient, loaded-library or future-view attestation',
        'reader': {'path': 'tools/audit_retained_installd_native_owner.py', 'sha256': sha(Path(__file__))},
        'parser': {'path': PARSER.relative_to(ROOT).as_posix(), 'sha256': PARSER_SHA},
        'capture': {'path': 'out/retained-installd-native-owner/static/capture.json', 'sha256': CAPTURE_SHA},
        'raw': {'path': 'firmware/retained-installd-native-owner/static/selected-native.json', 'sha256': RAW_SHA},
        'inputs': [{'path': p, 'sha256': v} for p, v in inputs.items()],
        'functions': captured['functions'], 'neededLibraries': captured['needed'], 'checks': checks,
        'capturedInitRc': {'origin': 'same immutable mounted Samsung cohort whose system/bin/installd hash equals the newly observed ELF',
                           'manifest': '../out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84/samsung-manifest.jsonl.gz',
                           'manifestSha256': '6654252d9f7bde941e367fe79eb9af541869f4a1ddb5d1b8a0f0d4d6dde57a7a',
                           'member': 'system/etc/init/installd.rc', 'archiveHeaderOffset': 2931451904, 'archiveDataOffset': 2931452416,
                           'size': 4783, 'sha256': inputs['firmware/retained-installd-native-owner/static/samsung-installd.rc'],
                           'loadedInitConfigProved': False},
        'publisher': {'name': 'installd', 'stringPc': '0x26238', 'managerVtableSlot': '0x30', 'indirectCallPc': '0x26348',
                      'w3': 0, 'w4': 8, 'directRuntimeCalleeAttested': False,
                      'scope': 'actual start function constructs String16 and BnInstalld then calls manager slot; no prepared alias patch or successful registration'},
        'oneOsBridgePairs': bridge['bridgePairs'],
        'firstUnboundOwner': 'Before either fresh clone main: real admitted filesystem/mount/property/library/SELinux-capability cohort for its layout_version and user-config writes, then literal /data,/mnt/expand,/data_mirror and caller-supplied native paths. Alias/environment alone does not establish this.',
        'alternatives': {
            'A_hostPrivateClone_keepLegacyGuestGlobalBinds': {
                'required': 'fresh host-owned clone in an original physical path view before init-view redirection; complete host route/death/reconnect/old-handle handoff; original canonical daemon remains guest-facing only if its own routing/drain is owned',
                'unclosed': 'existing init-view shared mounts can change live host daemon path resolution; retaining or renaming PID does not isolate it; clone pre-publication mutations and global consumers remain real'},
            'B_guestPrivateClone_keepHostCanonicalOriginal': {
                'required': 'fresh guest-owned Samsung native clone in deliberately private guest app-data/mirror/mount view; distinct endpoint plus complete guest routing; eliminate or segregate legacy global app-data binds before host work resumes',
                'unclosed': 'no guest publisher/launch/ABI binding or complete replacement of fourteen global binds is implemented; external callers, native mounts/properties/Knox and delayed work still require owners'},
        },
        'limits': [
            'Fourteen selected functions/3932 instructions only; no whole-binary or full native-library closure.',
            'LocalLockHolder and recursive/shared mutexes are process-memory locks; no cross-process admission/drain protocol proved.',
            'SQLite operation uses caller-supplied path; no app DB opened or copied by this audit; SQLite locking is not app-data lifecycle serialization.',
            'Mount/quota caches read /proc/mounts in current process view and properties; no live cache coherence or filesystem separation proved.',
            'Actual auxiliary libraries, linker namespace, SELinux context, capabilities, quotas, global properties and native child-work completion remain unadmitted.',
            'Only root acquired a file; this worker made no device call, native execution, runtime patch, launch or source-script execution.',
        ],
    }
    save(ROOT / 'inventory/retained-installd-native-owner.json', result)
    receipt = {'status': 'PASS-bounded-static-source-checks', 'checks': len(checks), 'functions': len(raw['functions']),
               'instructions': len(index), 'inventorySha256': sha(ROOT / 'inventory/retained-installd-native-owner.json'),
               'toolSha256': sha(Path(__file__)), 'oemExecuted': False, 'deviceAccessByWorker': False}
    save(OUT / 'audit-receipt.json', receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--capture', action='store_true')
    mode.add_argument('--audit', action='store_true')
    args = parser.parse_args()
    capture() if args.capture else audit()
