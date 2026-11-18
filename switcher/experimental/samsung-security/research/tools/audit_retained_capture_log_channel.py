"""Offline bounded Vector logger trace; no OEM loading, phone or log generation."""
from pathlib import Path
import hashlib, importlib.util, json, lzma, runpy, struct, sys, zipfile
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'out/retained-capture-log-channel'
RAW = ROOT / 'firmware/retained-capture-log-channel'
VECTOR = ROOT.parent / 'firmware/samsung/root-stack/vector/vector.dex'
DAEMON = VECTOR.with_name('daemon.apk')
FRAMEWORK = ROOT.parent / 'firmware/samsung/framework.jar'
RUNTIME = ROOT.parent / 'firmware/samsung/runtime-20261104/libandroid_runtime.so'
READER = ROOT / 'out/retained-capture-probe-review/vector_reader.py'
FRAMEWORK_RAW = RAW / '20261106T040917790307Z-aeafa96521f74bc0937b938b8d5172ec.jsonl'
OBSERVATION = ROOT / 'out/retained-capture-observation-preflight/20261106T041208629469Z-0101443169f34b8590f9bff99e9ecea5/observation.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
dump = lambda p, v: p.write_text(json.dumps(v, indent=2) + '\n')

def jsonable(v):
    if isinstance(v, bytes): return {'hex': v.hex()}
    if isinstance(v, (list, tuple)): return [jsonable(x) for x in v]
    if isinstance(v, dict): return {k: jsonable(x) for k, x in v.items()}
    return v

def log_constants(data):
    """Read only Log's encoded static scalars; do not discard its hidden-API map."""
    assert data[:8] == b'dex\n039\0'
    u = lambda p: struct.unpack_from('<I', data, p)[0]
    def leb(p):
        v = 0
        for shift in range(0, 35, 7):
            c = data[p]; p += 1; v |= (c & 127) << shift
            if c < 128: return v, p
        raise ValueError('LEB overflow')
    strings = []
    for i in range(u(56)):
        p = u(u(60) + 4*i); _, p = leb(p); strings.append(data[p:data.index(0, p)])
    types = [strings[u(u(68) + 4*i)] for i in range(u(64))]
    fields = []
    for i in range(u(80)):
        o, t, n = struct.unpack_from('<HHI', data, u(84) + 8*i)
        fields.append(types[o] + b'->' + strings[n] + b':' + types[t])
    for i in range(u(96)):
        p = u(100) + i*32
        if types[u(p)] != b'Landroid/util/Log;': continue
        q = u(p+24); counts = []
        for _ in range(4): n, q = leb(q); counts.append(n)
        names = []; index = 0
        for _ in range(counts[0]):
            delta, q = leb(q); index += delta; _, q = leb(q); names.append(fields[index].decode())
        p = u(p+28); count, p = leb(p); values = []
        assert count <= len(names) <= 32
        for _ in range(count):
            c = data[p]; p += 1; kind = c & 31; width = (c >> 5)+1
            assert kind == 4
            values.append(int.from_bytes(data[p:p+width], 'little', signed=True)); p += width
        return dict(zip(names, values))
    raise ValueError('Actual Log class absent')

def main():
    OUT.mkdir(parents=True, exist_ok=True); RAW.mkdir(parents=True, exist_ok=True)
    pins = {VECTOR: 'b75c889406507bae5f5f580efea778df6e2f556944a4bddc9d8f628ea0f3b4fd',
            DAEMON: 'c48a8fb270b7685bc06686b4ac0521a79a076adcd50bc336e0be99be2b69d2ff',
            FRAMEWORK: '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
            RUNTIME: 'f77d49dcfae7271ec3508cb06948218e65bdfbd1dc284797cb650b0db09af57d',
            OBSERVATION: '2648148b7b9c87b52733de5a8831523b25307196db892388aebb76edb5d5c1f5'}
    for p, h in pins.items(): assert sha(p) == h, str(p)
    spec = importlib.util.spec_from_file_location('saved_vector_reader', READER)
    reader = importlib.util.module_from_spec(spec); spec.loader.exec_module(reader)
    vector = reader.D(VECTOR.read_bytes())
    with zipfile.ZipFile(DAEMON) as z: daemon = reader.D(z.read('classes.dex'))
    selected = {
        'vector': ['Lio/github/libxposed/api/XposedInterfaceWrapper;->log(ILjava/lang/String;Ljava/lang/String;)V',
                   'Lio/github/libxposed/api/XposedInterfaceWrapper;->ensureAttached()V',
                   'Lio/github/libxposed/api/XposedInterfaceWrapper;->attachFramework(Lio/github/libxposed/api/XposedInterface;Ljava/lang/Runnable;)V',
                   'Lg2;-><init>(Ljava/lang/String;Landroid/content/pm/ApplicationInfo;Lf0;Lio/github/libxposed/api/XposedInterface$ExceptionMode;)V',
                   'Lg2;->log(ILjava/lang/String;Ljava/lang/String;)V',
                   'Lg2;->log(ILjava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)V',
                   'Lb3;->a(Lt0;ZLjava/lang/String;)Le1;',
                   'Lw;->e()Z',
                   'Lorg/matrix/vector/core/Main;->forkCommon(ZZLjava/lang/String;Ljava/lang/String;Landroid/os/IBinder;)V'],
        'daemon': ['Lvc;->onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z', 'Lyf;->b()Z',
                   'Lx7;->f(Lx7;Ljava/lang/String;ILjava/lang/String;)Ljava/util/LinkedHashMap;',
                   'Lmg;-><clinit>()V', 'Loa;-><clinit>()V',
                   'Loa;->j(Z)Ljava/util/List;',
                   'Lorg/matrix/vector/daemon/env/LogcatMonitor;->refreshFd(Z)I']}
    proofs = []
    for side, methods in selected.items():
        d = {'vector': vector, 'daemon': daemon}[side]
        for key in methods:
            row = d.members[key.encode()]; body = d.body(row)
            raw = {'member': key, 'header': row['header'], 'flags': row['flags'], 'body': jsonable(body)}
            path = RAW / (side + '-' + hashlib.sha256(key.encode()).hexdigest()[:16] + '.json')
            dump(path, raw)
            proofs.append({'member': key, 'header': row['header'], 'raw': str(path.relative_to(ROOT)),
                           'sha256': sha(path), 'instructionSha256': hashlib.sha256(d.b[row['code']+16:row['code']+16+row['header'][-1]*2]).hexdigest()})
    writes = []
    for key, row in vector.members.items():
        if not row['code']: continue
        for pc, op, _, _, refs in vector.body(row)[0]:
            if 0x67 <= op <= 0x6d and ('field', b'Lu1;->b:Z') in refs:
                writes.append({'member': key.decode(), 'pc': pc, 'opcode': op})
    assert writes == [{'member': selected['vector'][-1], 'pc': 238, 'opcode': 0x6a}]
    with zipfile.ZipFile(FRAMEWORK) as z: constants = log_constants(z.read('classes4.dex'))
    assert constants['Landroid/util/Log;->LOG_ID_MAIN:I'] == 0 and constants['Landroid/util/Log;->INFO:I'] == 4
    records = [json.loads(l) for l in FRAMEWORK_RAW.read_text().splitlines()]
    log = next(v for v in records if v.get('record') == 'method')
    assert log['body']['instructions'][0]['literal'] == 0
    assert log['body']['instructions'][1]['reference'] == 'Landroid/util/Log;->println_native(IILjava/lang/String;Ljava/lang/String;)I'

    # One actual native function and its relocation-verified PLT call only.
    native_parser = ROOT / 'tools/audit_security_native_linkage.py'
    elf = runpy.run_path(str(native_parser))['elf']; data = RUNTIME.read_bytes(); parsed = elf(data)
    def off(a):
        matches = [s for s in parsed['sections'] if s['type'] != 8 and s['address'] <= a < s['address'] + s['bytes']]
        assert len(matches) == 1
        return matches[0]['offset'] + a - matches[0]['address']
    debug = next(s for s in parsed['sections'] if s['name'] == '.gnu_debugdata')
    mini = lzma.decompress(data[debug['offset']:debug['offset']+debug['bytes']])
    symbols = elf(mini)['dynamicSymbols']
    sym = next(s for s in symbols if 'android_util_Log_println_nativeEP' in s['name'])
    assert sym['value'] == 0x1df41c and sym['size'] == 360
    sys.path.insert(0, str(ROOT / 'out/security-native/static-disassembler')); import capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    ins = [{'pc': i.address, 'bytes': i.bytes.hex(), 'mnemonic': i.mnemonic, 'operands': i.op_str}
           for i in md.disasm(data[off(sym['value']):off(sym['value'])+sym['size']], sym['value'])]
    assert next(i for i in ins if i['pc'] == 0x1df4a4)['operands'] == '#0x2bfef0'
    plt = [{'pc': i.address, 'bytes': i.bytes.hex(), 'mnemonic': i.mnemonic, 'operands': i.op_str}
           for i in md.disasm(data[off(0x2bfef0):off(0x2bfef0)+16], 0x2bfef0)]
    assert [(i['mnemonic'], i['operands']) for i in plt] == [
        ('adrp', 'x16, #0x2f4000'), ('ldr', 'x17, [x16, #0x188]'),
        ('add', 'x16, x16, #0x188'), ('br', 'x17')]
    reloc = next(r for r in parsed['rela'] if r['target'] == 0x2f4188)
    assert parsed['dynamicSymbols'][reloc['symbolIndex']]['name'] == '__android_log_buf_write'
    # Its exact JNI triplet uses in-place RELR addends, not only RELA entries.
    relr = next(s for s in parsed['sections'] if s['name'] == '.relr.dyn')
    slots = set(); cursor = 0
    for p in range(relr['offset'], relr['offset']+relr['bytes'], 8):
        value = struct.unpack_from('<Q', data, p)[0]
        if not value & 1: slots.add(value); cursor = value + 8
        else:
            for bit in range(1, 64):
                if value & (1 << bit): slots.add(cursor + 8*(bit-1))
            cursor += 63*8
    triplet = 0x2e1868
    assert all(triplet + n*8 in slots for n in range(3))
    ptrs = struct.unpack_from('<3Q', data, off(triplet))
    def string(a):
        p = off(a); return data[p:data.index(0, p)].decode()
    assert [string(ptrs[0]), string(ptrs[1]), ptrs[2]] == ['println_native', '(IILjava/lang/String;Ljava/lang/String;)I', sym['value']]
    native = {'symbol': sym, 'instructions': ins, 'jniTriplet': {'address': triplet, 'relrSlotsVerified': True,
              'name': string(ptrs[0]), 'signature': string(ptrs[1]), 'target': ptrs[2]},
              'pltCall': {'pc': 0x1df4a4, 'target': 0x2bfef0, 'got': 0x2f4188, 'symbol': '__android_log_buf_write',
                          'instructions': plt, 'relocation': reloc}}
    dump(RAW / 'native-println.json', native)
    result = {'schema': 'retained-capture-log-channel/v1', 'status': 'SOURCE_ROUTE_CLOSED_CURRENT_WRITER_UNPROVED',
              'inputPins': {str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p): h for p, h in pins.items()},
              'readerSha256': sha(READER), 'nativeParserSha256': sha(native_parser), 'methodProofs': proofs,
              'wholeVectorClassCount': len(vector.classes), 'quietFlagDirectWriters': writes,
              'frameworkRaw': {'path': str(FRAMEWORK_RAW.relative_to(ROOT)), 'sha256': sha(FRAMEWORK_RAW)},
              'logConstants': constants, 'nativeProof': {'path': str((RAW/'native-println.json').relative_to(ROOT)), 'sha256': sha(RAW/'native-println.json')},
              'channel': {'bufferId': 0, 'bufferName': 'main', 'priority': 4, 'tag': 'OneOSRetainedCapture',
                          'messageShape': 'loaded module record prefix plus colon-space plus fixed code; no Throwable in three-argument path'},
              'quietPolicy': 'INFO suppressed iff cached u1.b true; bootstrap reads NOT enable_verbose_log; absent/non-Boolean setting defaults verbose true',
              'quietPolicySourceSelector': {'database': '/data/adb/lspd/config/modules_config.db', 'table': 'configs',
                  'module_pkg_name': 'config', 'user_id': 0, 'group': 'lspd', 'key': 'enable_verbose_log',
                  'currentPrivateContentsRead': False, 'processCacheLiveValueObserved': False},
              'runtimeReadAvailability': {'path': str(OBSERVATION.relative_to(ROOT)), 'sha256': sha(OBSERVATION), 'scope': 'root observed main ring reader availability only; no diagnostic writer observed'},
              'unclosed': ['Current per-process quiet flag and live INFO delivery', 'Native liblog/logd retention/filter/access and real fresh process ownership',
                           'Daemon native LogcatMonitor file filter; module log files are not admitted as equivalent fallback'],
              'phoneActionsByThisAudit': False, 'oemOrNativeExecution': False, 'sourceOrSecurityAuthority': False}
    for p, h in pins.items(): assert sha(p) == h
    dump(OUT/'receipt.json', result)
    print(json.dumps({'status': result['status'], 'methods': len(proofs), 'receipt': str((OUT/'receipt.json').relative_to(ROOT)), 'sha256': sha(OUT/'receipt.json')}))

if __name__ == '__main__': main()
