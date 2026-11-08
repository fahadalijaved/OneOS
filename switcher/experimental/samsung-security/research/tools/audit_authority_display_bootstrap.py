"""Static proof for two eager display calls and process-local cache bootstrap."""
import argparse, gzip, hashlib, json, lzma, re, runpy, struct, sys, tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARENT = ROOT.parent
WORK = ROOT / 'out/authority-display-bootstrap'
SOURCES = {
    'samsung-framework': (PARENT / 'firmware/samsung/framework.jar', '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'),
    'coloros-framework': (PARENT / 'firmware/donor/extracted/system/framework/framework.jar', 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'),
    'samsung-services': (PARENT / 'firmware/samsung/runtime-20261104/services.jar', 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'),
    'coloros-services': (PARENT / 'firmware/donor/extracted/system/framework/services.jar', '66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'),
}
QUERY = [
    ('samsung-framework', 'android.os.ServiceManager', ['<clinit>()V', 'initServiceCache(Ljava/util/Map;)V', 'getService(Ljava/lang/String;)Landroid/os/IBinder;']),
    ('samsung-framework', 'android.hardware.OverlayProperties', ['<clinit>()V', '<init>(J)V', 'writeToParcel(Landroid/os/Parcel;I)V']),
    ('coloros-framework', 'android.hardware.OverlayProperties', ['<clinit>()V', '<init>(J)V', 'writeToParcel(Landroid/os/Parcel;I)V']),
    ('samsung-framework', 'android.hardware.OverlayProperties$1', ['createFromParcel(Landroid/os/Parcel;)Landroid/hardware/OverlayProperties;']),
    ('coloros-framework', 'android.hardware.OverlayProperties$1', ['createFromParcel(Landroid/os/Parcel;)Landroid/hardware/OverlayProperties;']),
    ('samsung-services', 'com.android.server.display.DisplayManagerService$BinderService', ['getPreferredWideGamutColorSpaceId()I', 'getOverlaySupport()Landroid/hardware/OverlayProperties;']),
    ('coloros-services', 'com.android.server.display.DisplayManagerService$BinderService', ['getPreferredWideGamutColorSpaceId()I', 'getOverlaySupport()Landroid/hardware/OverlayProperties;']),
    ('coloros-services', 'com.android.server.display.DisplayManagerService', ['getPreferredWideGamutColorSpaceIdInternal()I', 'getOverlaySupportInternal()Landroid/hardware/OverlayProperties;']),
    ('samsung-framework', 'android.hardware.display.IDisplayManager$Stub', ['onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z']),
    ('coloros-framework', 'android.hardware.display.IDisplayManager$Stub', ['onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z']),
    ('samsung-framework', 'android.graphics.ColorSpace$Named', ['<clinit>()V']),
    ('coloros-framework', 'android.graphics.ColorSpace$Named', ['<clinit>()V']),
    ('samsung-framework', 'android.net.Uri$$ExternalSyntheticBUOutline0', ['m$5(Ljava/lang/String;)V']),
]

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def read():
    WORK.mkdir(parents=True, exist_ok=True)
    ledger_path = WORK / 'reads.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    reader = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
    for source, name, methods in QUERY:
        key = source + ':' + name
        if key not in ledger:
            archive, pin = SOURCES[source]
            receipt = reader(archive, pin, class_name=name, methods=methods, stream='authority-display-bootstrap')
            ledger[key] = receipt['receipt']
            ledger_path.write_text(json.dumps(ledger, indent=2) + '\n')
        receipt = json.loads((ROOT / ledger[key]).read_text())
        assert receipt['archiveSha256'] == SOURCES[source][1]
        assert receipt['query']['exactMethods'] == methods
        assert digest(ROOT / receipt['raw']) == receipt['rawSha256']
        print(key, ledger[key], flush=True)

def native():
    WORK.mkdir(parents=True, exist_ok=True)
    raw = ROOT / 'firmware/authority-display-bootstrap'
    raw.mkdir(parents=True, exist_ok=True)
    helper = ROOT / 'tools/audit_security_native_linkage.py'
    helper_pin = digest(helper)
    parse = runpy.run_path(str(helper))['elf']
    sys.path.insert(0, str(ROOT / 'out/security-native/static-disassembler'))
    import capstone
    decoder = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    result = {}
    gui = raw / 'libgui.so'
    gui_pin = '3f241a05183cbced5d82a05b162d02ef6b90a0f81b970b22711ebf0293a43443'
    manifest = PARENT / 'out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84/samsung-manifest.jsonl.gz'
    assert digest(manifest) == '6654252d9f7bde941e367fe79eb9af541869f4a1ddb5d1b8a0f0d4d6dde57a7a'
    row, = [row for line in gzip.open(manifest, 'rt') if (row := json.loads(line))['path'] == 'system/lib64/libgui.so']
    assert row['sha256'] == gui_pin and row['size'] == 2135792
    if not gui.exists():
        capture = PARENT / 'firmware/samsung/os-mirror-20261104/mounted-os-20261104T235732022961Z.tar'
        assert capture.stat().st_size == 20434769920
        with tarfile.open(capture, 'r:') as archive:
            for member in archive:
                if member.name.removeprefix('./') != row['path']:
                    continue
                assert member.isfile() and member.size == row['size']
                data = archive.extractfile(member).read(row['size'] + 1)
                assert len(data) == row['size'] and hashlib.sha256(data).hexdigest() == gui_pin
                gui.write_bytes(data)
                (WORK / 'gui-member.json').write_text(json.dumps({'path': row['path'], 'sha256': gui_pin, 'headerOffset': member.offset, 'dataOffset': member.offset_data}, indent=2) + '\n')
                break
            else:
                raise ValueError('Pinned gui member absent')
    sources = [('samsung-runtime', ROOT / 'firmware/security-native/samsung/system/lib64/libandroid_runtime.so', 'f77d49dcfae7271ec3508cb06948218e65bdfbd1dc284797cb650b0db09af57d'), ('coloros-runtime', PARENT / 'firmware/donor/extracted/system/lib64/libandroid_runtime.so', 'edfd170ccbca035d6acd8da1b93a346a7cb438f35cf706ba03037bdc1feb1279'), ('samsung-gui', gui, gui_pin), ('coloros-gui', PARENT / 'firmware/donor/extracted/system/lib64/libgui.so', 'b99957d724a1364c7d52727c61c0d76372eb0e083ebbe243272c1a9e66e0e765')]
    for side, path, pin in sources:
        assert digest(path) == pin
        data = path.read_bytes()
        parsed = parse(data)
        debug = next(section for section in parsed['sections'] if section['name'] == '.gnu_debugdata')
        mini = lzma.decompress(data[debug['offset']:debug['offset'] + debug['bytes']])
        assert len(mini) < 16 * 1024 * 1024
        symbols = parsed['dynamicSymbols'] + parse(mini)['dynamicSymbols']
        functions = []
        seen = set()
        selected = ['OverlayProperties_write', 'OverlayProperties_read', 'register_android_hardware_OverlayProperties']
        for symbol in symbols:
            selected_name = (any(name in symbol['name'] for name in selected) or (any(name in symbol['name'] for name in ['jniRegisterMaybeRenamedNativeMethods', 'jniRegisterNativeMethods']) and '__uniq.224673656675951707818718193905588675883' in symbol['name'])) if side.endswith('runtime') else (any(name in symbol['name'] for name in ['OverlayProperties', 'LutProperties']) and any(name in symbol['name'] for name in ['writeToParcel', 'readFromParcel']))
            if not symbol['sectionIndex'] or not symbol['size'] or symbol['type'] != 2 or not selected_name or symbol['value'] in seen:
                continue
            seen.add(symbol['value'])
            section, = [section for section in parsed['sections'] if section['type'] != 8 and section['address'] <= symbol['value'] and symbol['value'] + symbol['size'] <= section['address'] + section['bytes']]
            offset = section['offset'] + symbol['value'] - section['address']
            code = data[offset:offset + symbol['size']]
            functions.append({'symbol': symbol['name'], 'address': symbol['value'], 'fileOffset': offset, 'bytes': len(code), 'sha256': hashlib.sha256(code).hexdigest(), 'instructions': [{'pc': ins.address, 'mnemonic': ins.mnemonic, 'operands': ins.op_str} for ins in decoder.disasm(code, symbol['value'])]})
        plt = next(section for section in parsed['sections'] if section['name'] == '.plt')
        slots = [relocation for relocation in parsed['rela'] if relocation['type'] == 1026]
        calls = []
        for function in functions:
            for instruction in function['instructions']:
                if instruction['mnemonic'] not in ['bl', 'b'] or not instruction['operands'].startswith('#0x'):
                    continue
                address = int(instruction['operands'][1:], 16)
                matches = [symbol for symbol in symbols if symbol['sectionIndex'] and symbol['value'] == address]
                name = matches[0]['name'] if matches else None
                if plt['address'] + 32 <= address < plt['address'] + plt['bytes'] and (address - plt['address'] - 32) % 24 == 0:
                    slot = (address - plt['address'] - 32) // 24
                    relocation = slots[slot]
                    offset = plt['offset'] + address - plt['address']
                    stub = list(decoder.disasm(data[offset:offset + 24], address))
                    page = next(ins for ins in stub if ins.mnemonic == 'adrp' and ins.op_str.startswith('x16,'))
                    load = next(ins for ins in stub if ins.mnemonic == 'ldr' and ins.op_str.startswith('x17,'))
                    displacement = re.search(r'#(0x[0-9a-f]+|\d+)', load.op_str)
                    got = int(page.op_str.split('#')[1], 16) + (int(displacement.group(1), 0) if displacement else 0)
                    assert got == relocation['target']
                    name = parsed['dynamicSymbols'][relocation['symbolIndex']]['name']
                calls.append({'caller': function['symbol'], 'pc': instruction['pc'], 'target': address, 'symbol': name})
        address_loads = []
        if side.endswith('gui'):
            for function in functions:
                instructions = function['instructions']
                for index, instruction in enumerate(instructions):
                    if instruction['mnemonic'] != 'adrp':
                        continue
                    register, immediate = instruction['operands'].split(', ')
                    page = int(immediate[1:], 16)
                    load = next(candidate for candidate in instructions[index + 1:index + 4] if candidate['mnemonic'] == 'ldr' and candidate['operands'].startswith(register + ', [' + register))
                    displacement = re.search(r'#(0x[0-9a-f]+|\d+)', load['operands'])
                    got = page + (int(displacement.group(1), 0) if displacement else 0)
                    relocation, = [relocation for relocation in parsed['rela'] if relocation['target'] == got]
                    symbol = parsed['dynamicSymbols'][relocation['symbolIndex']]['name']
                    assert symbol.startswith('_ZTVN7android3gui')
                    address_loads.append({'function': function['symbol'], 'pagePc': instruction['pc'], 'loadPc': load['pc'], 'symbol': symbol, 'got': got, 'relocationType': relocation['type']})
        virtuals = []
        if side.endswith('gui'):
            for name in ['_ZTVN7android3gui17OverlayProperties27SupportedBufferCombinationsE', '_ZTVN7android3gui13LutPropertiesE']:
                symbol = next(symbol for symbol in symbols if symbol['name'] == name and symbol['sectionIndex'])
                for displacement, suffix in [(32, '13writeToParcelEPNS_6ParcelE'), (40, '14readFromParcelEPKNS_6ParcelE')]:
                    relocation, = [relocation for relocation in parsed['rela'] if relocation['target'] == symbol['value'] + displacement]
                    target_symbol = parsed['dynamicSymbols'][relocation['symbolIndex']]['name']
                    assert target_symbol.endswith(suffix)
                    virtuals.append({'vtable': name, 'slot': displacement - 16, 'target': target_symbol, 'relocationType': relocation['type']})
        registration = None
        if side.endswith('runtime'):
            table, class_address = (0x2ef5e0, 0x9cba8) if side.startswith('samsung') else (0x2d1830, 0x9905c)
            def address_offset(address, size=1):
                section, = [section for section in parsed['sections'] if section['type'] != 8 and section['address'] <= address and address + size <= section['address'] + section['bytes']]
                return section['offset'] + address - section['address']
            def cstring(address):
                offset = address_offset(address)
                return data[offset:data.index(b'\0', offset, offset + 1024)].decode('ascii')
            assert cstring(class_address) == 'android/hardware/OverlayProperties'
            entries = []
            for index in range(7):
                name, signature, target = struct.unpack_from('<QQQ', data, address_offset(table + index * 24, 24))
                entries.append({'name': cstring(name), 'signature': cstring(signature), 'target': target})
            for name, suffix in [('nReadOverlayPropertiesFromParcel', 'OverlayProperties_read'), ('nWriteOverlayPropertiesToParcel', 'OverlayProperties_write')]:
                entry, = [entry for entry in entries if entry['name'] == name]
                function, = [function for function in functions if suffix in function['symbol']]
                assert entry['target'] == function['address']
            registration = {'class': cstring(class_address), 'tableAddress': table, 'entries': entries, 'renamingHelperSelected': True, 'registerNativesLeafSelected': True}
        assert digest(path) == pin
        target = raw / (side + '-native.json')
        target.write_text(json.dumps({'sourceSha256': pin, 'functions': functions, 'resolvedCalls': calls, 'addressLoads': address_loads, 'virtualSlots': virtuals, 'registration': registration, 'symbols': symbols, 'oemExecuted': False}, indent=2) + '\n')
        result[side] = {'raw': target.relative_to(ROOT).as_posix(), 'rawSha256': digest(target), 'sourceSha256': pin, 'functions': [{k: v for k, v in function.items() if k != 'instructions'} for function in functions], 'resolvedCalls': calls, 'addressLoads': address_loads, 'virtualSlots': virtuals, 'registration': registration}
    assert digest(helper) == helper_pin
    (WORK / 'native.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'selections': {key: len(value['functions']) for key, value in result.items()}, 'oemExecuted': False}))

def compare_native():
    ledger = json.loads((WORK / 'native.json').read_text())
    values = {}
    for side in ['samsung-gui', 'coloros-gui']:
        proof = ledger[side]
        assert digest(ROOT / proof['raw']) == proof['rawSha256']
        raw = json.loads((ROOT / proof['raw']).read_text())
        values[side] = {}
        for function in raw['functions']:
            normalized = []
            calls = {call['pc']: call for call in raw['resolvedCalls'] if call['caller'] == function['symbol']}
            page_loads = {load['pagePc']: load for load in raw['addressLoads'] if load['function'] == function['symbol']}
            got_loads = {load['loadPc']: load for load in raw['addressLoads'] if load['function'] == function['symbol']}
            for instruction in function['instructions']:
                pc, mnemonic, operands = instruction['pc'], instruction['mnemonic'], instruction['operands']
                if pc in page_loads:
                    operands = operands.split(', ')[0] + ', GOT_PAGE(' + page_loads[pc]['symbol'] + ')'
                elif pc in got_loads:
                    operands = re.sub(r'#(0x[0-9a-f]+|\d+)', 'GOT_SLOT(' + got_loads[pc]['symbol'] + ')', operands)
                elif mnemonic == 'bl' or mnemonic == 'b' or mnemonic.startswith('b.') or mnemonic in ['cbz', 'cbnz', 'tbz', 'tbnz']:
                    targets = list(re.finditer(r'#0x[0-9a-f]+', operands))
                    target = targets[-1] if targets else None
                    if target:
                        address = int(target.group()[1:], 16)
                        if function['address'] <= address < function['address'] + function['bytes']:
                            replacement = 'LOCAL(' + hex(address - function['address']) + ')'
                        else:
                            call = calls.get(pc)
                            assert call and call['symbol'], (side, function['symbol'], instruction)
                            replacement = 'CALL(' + call['symbol'] + ')'
                        operands = operands[:target.start()] + replacement + operands[target.end():]
                normalized.append([mnemonic, operands])
            values[side][function['symbol']] = normalized
    assert set(values['samsung-gui']) == set(values['coloros-gui'])
    results = []
    for name, source in values['samsung-gui'].items():
        guest = values['coloros-gui'][name]
        differences = [index for index in range(max(len(source), len(guest))) if source[index:index+1] != guest[index:index+1]]
        results.append({'symbol': name, 'instructionCount': len(source), 'guestInstructionCount': len(guest), 'equal': not differences, 'differenceInstructionIndexes': differences, 'normalizedSha256': hashlib.sha256(json.dumps(source, separators=(',', ':')).encode()).hexdigest()})
    (WORK / 'native-comparison.json').write_text(json.dumps({'normalization': 'All instruction order/registers/non-address immediates retained; internal branches function-relative; external branches resolved symbol; ADRP+LDR GOT pairs independently checked against exact named vtable relocation. No generic instruction deletion.', 'functions': results, 'allEqual': all(result['equal'] for result in results), 'oemExecuted': False}, indent=2) + '\n')
    print(json.dumps({'nativeWireFunctions': len(results), 'equal': all(result['equal'] for result in results), 'instructionsPerSide': sum(result['instructionCount'] for result in results)}))

def summarize():
    compare_native()
    assert digest(ROOT / 'inventory/authority-bootstrap-runtime.json') == 'b527fa96edc027866559e6fe8a54abaf15176af3767486c5d4e246b047f3fccc'
    reads = json.loads((WORK / 'reads.json').read_text())
    methods = {}
    evidence = []
    for key, receipt_path in reads.items():
        receipt = json.loads((ROOT / receipt_path).read_text())
        assert receipt['archiveSha256'] == SOURCES[key.split(':')[0]][1]
        assert digest(ROOT / receipt['raw']) == receipt['rawSha256']
        assert not receipt['oemCodeExecuted'] and receipt['readerExitCode'] == 0
        lines = {}
        for number, line in enumerate((ROOT / receipt['raw']).read_text().splitlines(), 1):
            row = json.loads(line)
            if row['record'] == 'method':
                body = row['body']
                methods[(key, body['signature'])] = body
                lines[body['signature']] = number
        evidence.append({'key': key, 'receipt': receipt_path, 'receiptSha256': digest(ROOT / receipt_path), 'raw': receipt['raw'], 'rawSha256': receipt['rawSha256'], 'archiveSha256': receipt['archiveSha256'], 'methods': [{**proof, 'rawMethodLine': lines[proof['signature']]} for proof in receipt['selectedMethodProofs']]})
    assertions = []
    def edge(key, method, pc, suffix):
        body = methods[(key, method)]
        instruction, = [instruction for instruction in body['instructions'] if instruction['pc'] == pc]
        assert instruction.get('reference', '').endswith(suffix), (key, method, pc, instruction)
        assertions.append({'selection': key, 'method': method, 'pc': hex(pc), 'referenceSuffix': suffix})
    manager = 'samsung-framework:android.os.ServiceManager'
    edge(manager, 'initServiceCache(Ljava/util/Map;)V', 2, '->size()I')
    edge(manager, 'initServiceCache(Ljava/util/Map;)V', 10, '->putAll(Ljava/util/Map;)V')
    edge(manager, 'getService(Ljava/lang/String;)Landroid/os/IBinder;', 2, '->get(Ljava/lang/Object;)Ljava/lang/Object;')
    edge(manager, 'getService(Ljava/lang/String;)Landroid/os/IBinder;', 11, '->rawGetService(Ljava/lang/String;)Landroid/os/IBinder;')
    edge('samsung-framework:android.net.Uri$$ExternalSyntheticBUOutline0', 'm$5(Ljava/lang/String;)V', 0, 'Ljava/lang/IllegalStateException;')
    dispatch = {}
    for side, numbers in [('samsung', [71, 86]), ('coloros', [44, 59])]:
        key = side + '-framework:android.hardware.display.IDisplayManager$Stub'
        body = methods[(key, 'onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z')]
        instructions = {instruction['pc']: instruction for instruction in body['instructions']}
        switch = instructions[13]
        payload = instructions[switch['targetPc']]
        edge(key, body['signature'], 10, '->enforceInterface(Ljava/lang/String;)V')
        assert instructions[8]['reference'] == 'string=android.hardware.display.IDisplayManager'
        dispatch[side] = {}
        for transaction, signature, reply_suffix in zip(numbers, ['getPreferredWideGamutColorSpaceId()I', 'getOverlaySupport()Landroid/hardware/OverlayProperties;'], ['->writeInt(I)V', '->writeTypedObject(Landroid/os/Parcelable;I)V']):
            element, = [element for element in payload['switchElements'] if element['key'] == transaction]
            pc = switch['pc'] + element['offsetFromReferringSwitchPc']
            edge(key, body['signature'], pc, '->' + signature)
            edge(key, body['signature'], pc + 4, '->writeNoException()V')
            edge(key, body['signature'], pc + 7, reply_suffix)
            dispatch[side][signature] = {'transaction': transaction, 'casePc': hex(pc), 'writeNoExceptionPc': hex(pc + 4), 'replyPc': hex(pc + 7)}
        overlay = side + '-framework:android.hardware.OverlayProperties'
        edge(overlay, 'writeToParcel(Landroid/os/Parcel;I)V', 0x13, '->nWriteOverlayPropertiesToParcel(JLandroid/os/Parcel;)V')
        edge(side + '-framework:android.hardware.OverlayProperties$1', 'createFromParcel(Landroid/os/Parcel;)Landroid/hardware/OverlayProperties;', 9, '->-$$Nest$smnReadOverlayPropertiesFromParcel(Landroid/os/Parcel;)J')
        service = side + '-services:com.android.server.display.DisplayManagerService$BinderService'
        for signature in ['getPreferredWideGamutColorSpaceId()I', 'getOverlaySupport()Landroid/hardware/OverlayProperties;']:
            edge(service, signature, 0, '->clearCallingIdentity()J')
            assert not any('enforce' in instruction.get('reference', '') for instruction in methods[(service, signature)]['instructions'])
    named = {}
    for side in ['samsung', 'coloros']:
        body = methods[(side + '-framework:android.graphics.ColorSpace$Named', '<clinit>()V')]
        registers = {}
        named[side] = []
        for instruction in body['instructions']:
            operands = instruction.get('registers', [])
            if operands and instruction.get('referenceKind') == 'string':
                registers[operands[0]] = instruction['reference'].removeprefix('string=')
            elif operands and 'literal' in instruction:
                registers[operands[0]] = instruction['literal']
            if instruction['opcode'].startswith('INVOKE_DIRECT') and instruction.get('reference', '').endswith('-><init>(Ljava/lang/String;I)V'):
                named[side].append([registers[operands[1]], registers[operands[2]]])
    assert named['samsung'] == named['coloros'] and len(named['samsung']) == 20
    native_proof = json.loads((WORK / 'native.json').read_text())
    for proof in native_proof.values():
        assert digest(ROOT / proof['raw']) == proof['rawSha256']
    comparison = json.loads((WORK / 'native-comparison.json').read_text())
    assert comparison['allEqual'] and len(comparison['functions']) == 6
    result = {'schema': 'authority-display-bootstrap/v1', 'status': 'two-call-static-contract-and-cache-route-closed; prepared-design-only', 'methodEvidence': evidence, 'assertions': assertions, 'assertionCount': len(assertions), 'selectedNewMethodBodies': sum(len(item['methods']) for item in evidence), 'reusedProxyEvidence': {'source': 'inventory/authority-bootstrap-runtime.json', 'sourceSha256': 'b527fa96edc027866559e6fe8a54abaf15176af3767486c5d4e246b047f3fccc', 'samsungTransactions': [71, 86], 'colorosTransactions': [44, 59], 'flags': 0}, 'dispatch': dispatch, 'colorSpaceNamedIds': named['samsung'], 'nativeEvidence': native_proof, 'nativeComparison': comparison, 'proposedApi': {'type': 'PreparedSamsungDisplayBridge', 'prepare': 'prepare(IBinder retainedGenuineGuestDms)', 'accessor': 'sourceProtocolBinder()', 'implemented': False, 'admission': 'Binder parameter is not provenance. Exact actual guest code/endpoint/bootstrap-generation owner remains external and unassembled.', 'installation': 'Root composes complete pre-Context Map and invokes genuine Samsung ServiceManager.initServiceCache once; no global addService/cache mutation/clearing'}, 'limits': ['Captured original code/static contract only, not currently installed patched guest identity or executable Android result', 'Selected compound native serializers/readers and vtables match; full native/linker/ART and libbinder primitive implementation/runtime acceptance are not claimed', 'No runtime adapter, cache installation, IPC, OEM/native execution or Context probe occurred', 'The two-case adapter must reject unprepared operations; subsequent display-info/cache/callback routes still prevent complete Context bootstrap', 'Real process-local first-install/exclusive ownership, retained remote lifetime/death/uncertain return and no early DisplayManagerGlobal singleton require genuine bootstrap assembly'], 'toolSha256': digest(__file__)}
    target = ROOT / 'inventory/authority-display-bootstrap.json'
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'pass': True, 'assertions': len(assertions), 'newBodies': result['selectedNewMethodBodies'], 'matchedNativeFunctions': 6, 'nativeInstructionsEach': 929, 'runtimeImplemented': False}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--read', action='store_true')
    parser.add_argument('--native', action='store_true')
    parser.add_argument('--compare-native', action='store_true')
    parser.add_argument('--summarize', action='store_true')
    args = parser.parse_args()
    if args.read:
        read()
    if args.native:
        native()
    if args.compare_native:
        compare_native()
    if args.summarize:
        summarize()
