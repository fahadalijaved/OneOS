"""Read selected Samsung bootstrap bodies statically; never load OEM classes."""
import argparse, gzip, hashlib, json, lzma, re, runpy, struct, sys, tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARENT = ROOT.parent
ARCHIVE = PARENT / 'firmware/samsung/framework.jar'
SHA = '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'
MANIFEST = PARENT / 'out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84/samsung-manifest.jsonl.gz'
MANIFEST_SHA = '6654252d9f7bde941e367fe79eb9af541869f4a1ddb5d1b8a0f0d4d6dde57a7a'
APP_PROCESS_SHA = '08891284f79ebd9411d7ebd2e267bd2c083e8d5a02f2f192629fb126fabfeec8'
NSC_SHA = '57437a89c1231e6823777d560e7d723049a31f52a10180633bcb713f0039d125'
QUERIES = {
    'android.app.ActivityThread': ['<clinit>()V', '<init>()V', 'systemMain()Landroid/app/ActivityThread;', 'attach(ZJ)V', 'getSystemContext()Landroid/app/ContextImpl;', 'getPackageManager()Landroid/content/pm/IPackageManager;'],
    'android.app.ContextImpl': ['createSystemContext(Landroid/app/ActivityThread;)Landroid/app/ContextImpl;', 'getApplicationContext()Landroid/content/Context;', 'getPackageManager()Landroid/content/pm/PackageManager;', 'checkPermission(Ljava/lang/String;II)I'],
    'android.app.LoadedApk': ['<init>(Landroid/app/ActivityThread;)V', 'makeApplicationInner(ZLandroid/app/Instrumentation;)Landroid/app/Application;', 'makeApplicationInner(ZLandroid/app/Instrumentation;Z)Landroid/app/Application;'],
    'android.os.Looper': ['prepareMainLooper()V', 'loop()V'],
    'android.app.Application': ['<init>()V', 'onCreate()V', 'attach(Landroid/content/Context;)V'],
    'android.app.ActivityThread#system-init': ['initializeSystemThread(Landroid/app/ActivityThread;)V'],
    'android.app.ContextImpl#inner': ['createSystemContextInner(Landroid/app/ActivityThread;Landroid/app/LoadedApk;)Landroid/app/ContextImpl;', 'getPackageManagerInner()Landroid/content/pm/PackageManager;', '<init>(Landroid/app/ContextImpl;Landroid/app/ActivityThread;Landroid/app/LoadedApk;Landroid/content/ContextParams;Ljava/lang/String;Landroid/content/AttributionSource;Ljava/lang/String;Landroid/os/IBinder;Landroid/os/UserHandle;ILjava/lang/ClassLoader;Ljava/lang/String;IZ)V'],
    'android.view.ThreadedRenderer': ['<clinit>()V', 'initForSystemProcess()V'],
    'android.app.Instrumentation': ['basicInit(Landroid/app/ActivityThread;)V', 'newApplication(Ljava/lang/ClassLoader;Ljava/lang/String;Landroid/content/Context;)Landroid/app/Application;'],
    'android.app.ContextImpl#attribution': ['createAttributionSource(Ljava/lang/String;Landroid/content/AttributionSource;Ljava/util/Set;ZI)Landroid/content/AttributionSource;', 'createAppContext(Landroid/app/ActivityThread;Landroid/app/LoadedApk;)Landroid/app/ContextImpl;'],
    'android.app.SystemServiceRegistry': ['<clinit>()V', 'createServiceCache()[Ljava/lang/Object;'],
    'android.content.ContextParams': ['<clinit>()V'],
    'android.app.ResourcesManager': ['<init>()V', 'getInstance()Landroid/app/ResourcesManager;'],
    'android.content.res.Resources': ['getSystem()Landroid/content/res/Resources;'],
    'android.app.LoadedApk#application-init': ['<clinit>()V', 'createAppFactory(Landroid/content/pm/ApplicationInfo;Ljava/lang/ClassLoader;)Landroid/app/AppComponentFactory;', 'callNetworkSecurityConfigProviderHandleNewApplication(Landroid/content/Context;)V'],
    'android.graphics.Typeface': ['<clinit>()V', 'setFlipFonts()V'],
    'android.permission.PermissionManager': ['checkPermission(Ljava/lang/String;III)I', 'resolveDeviceIdForPermissionCheck(Landroid/content/Context;ILjava/lang/String;)I'],
    'com.android.internal.os.RuntimeInit': ['main([Ljava/lang/String;)V', 'commonInit()V', 'nativeFinishInit()V'],
    'android.app.SystemServiceRegistry#lookup': ['getSystemService(Landroid/app/ContextImpl;Ljava/lang/String;)Ljava/lang/Object;', 'getSystemServiceName(Ljava/lang/Class;)Ljava/lang/String;'],
    'android.graphics.HardwareRenderer': ['<clinit>()V', 'setIsSystemOrPersistent()V'],
    'android.graphics.Typeface#initializer': ['staticInitializer()V', 'getFontPathFlipFont()Ljava/lang/String;'],
    'android.app.ContextImpl#register-attribution': ['registerAttributionSourceIfNeeded(Landroid/content/AttributionSource;Z)Landroid/content/AttributionSource;'],
    'com.samsung.isrb.IsrbHooks': ['init()V'],
    'android.app.SystemServiceRegistry#registration': ['registerServices()V'],
    'android.graphics.Typeface#font-init': ['init()V', 'getFullFlipFont()Ljava/lang/String;'],
    'android.net.Uri$$ExternalSyntheticBUOutline0': ['m(Ljava/lang/String;Ljava/lang/Throwable;)V'],
    'android.content.ContextParams$Builder': ['<init>()V', 'build()Landroid/content/ContextParams;'],
    'android.app.ContextImpl$ApplicationContentResolver': ['<init>(Landroid/content/Context;Landroid/app/ActivityThread;)V'],
    'android.content.ContentResolver': ['<init>(Landroid/content/Context;)V', '<init>(Landroid/content/Context;Landroid/content/ContentInterface;)V'],
    'android.app.ResourcesManager#display': ['getDisplayMetrics()Landroid/util/DisplayMetrics;', 'getDisplayMetrics(ILandroid/view/DisplayAdjustments;)Landroid/util/DisplayMetrics;'],
    'android.content.res.Resources#constructor': ['<init>()V'],
    'android.hardware.display.DisplayManagerGlobal': ['getInstance()Landroid/hardware/display/DisplayManagerGlobal;', '<init>(Landroid/hardware/display/IDisplayManager;)V', 'getDisplayInfo(I)Landroid/view/DisplayInfo;'],
    'android.os.Looper#prepare': ['prepare(Z)V', '<init>(Z)V'],
    'android.os.MessageQueue': ['<init>(Z)V'],
    'android.app.ActivityThread$H': ['<init>(Landroid/app/ActivityThread;)V'],
    'android.app.ActivityThread#package-info': ['installSystemApplicationInfo(Landroid/content/pm/ApplicationInfo;Ljava/lang/ClassLoader;)V'],
    'android.app.ContextImpl#package-info': ['installSystemApplicationInfo(Landroid/content/pm/ApplicationInfo;Ljava/lang/ClassLoader;)V'],
}

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def native():
    """Bounded ELF reads/disassembly using existing authored parser/PC Capstone."""
    raw = ROOT / 'firmware/authority-bootstrap-runtime'
    raw.mkdir(parents=True, exist_ok=True)
    path = raw / 'app_process64'
    assert digest(MANIFEST) == MANIFEST_SHA
    rows = [json.loads(line) for line in gzip.open(MANIFEST, 'rt')]
    expected, = [row for row in rows if row['path'] == 'system/bin/app_process64' and row['kind'] == 'file']
    assert expected['sha256'] == APP_PROCESS_SHA and expected['size'] == 51856
    member_proof = None
    if not path.exists():
        capture = PARENT / 'firmware/samsung/os-mirror-20261104/mounted-os-20261104T235732022961Z.tar'
        assert capture.stat().st_size == 20434769920
        with tarfile.open(capture, 'r:') as archive:
            for member in archive:
                if member.name.removeprefix('./') != 'system/bin/app_process64':
                    continue
                assert member.isfile() and member.size == 51856
                data = archive.extractfile(member).read(51857)
                assert len(data) == 51856 and hashlib.sha256(data).hexdigest() == APP_PROCESS_SHA
                path.write_bytes(data)
                member_proof = {'headerOffset': member.offset, 'dataOffset': member.offset_data}
                break
            else:
                raise ValueError('Pinned regular app_process64 member missing')
    assert digest(path) == APP_PROCESS_SHA
    parser_path = ROOT / 'tools/audit_security_native_linkage.py'
    parser_sha = digest(parser_path)
    parse = runpy.run_path(str(parser_path))['elf']
    sys.path.insert(0, str(ROOT / 'out/security-native/static-disassembler'))
    import capstone
    decoder = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    result = {}
    for label, source, pin in [('app_process64', path, APP_PROCESS_SHA), ('libandroid_runtime.so', ROOT / 'firmware/security-native/samsung/system/lib64/libandroid_runtime.so', 'f77d49dcfae7271ec3508cb06948218e65bdfbd1dc284797cb650b0db09af57d')]:
        assert digest(source) == pin
        data = source.read_bytes()
        parsed = parse(data)
        symbols = list(parsed['dynamicSymbols'])
        debug = next((section for section in parsed['sections'] if section['name'] == '.gnu_debugdata'), None)
        if debug:
            mini = lzma.decompress(data[debug['offset']:debug['offset'] + debug['bytes']])
            assert len(mini) < 16 * 1024 * 1024
            symbols += parse(mini)['dynamicSymbols']
        wanted = ['main', 'onVmCreated', 'onStarted', 'nativeFinishInit', 'AndroidRuntime5start', 'AndroidRuntime8startReg', 'register_com_android_internal_os_RuntimeInit']
        functions = []
        seen = set()
        for symbol in symbols:
            name = symbol['name']
            if not symbol['sectionIndex'] or symbol['type'] != 2 or not symbol['size'] or not (name == 'main' or any(word in name for word in wanted[1:])):
                continue
            if symbol['value'] in seen:
                continue
            seen.add(symbol['value'])
            sections = [section for section in parsed['sections'] if section['type'] != 8 and section['address'] <= symbol['value'] and symbol['value'] + symbol['size'] <= section['address'] + section['bytes']]
            section, = sections
            offset = section['offset'] + symbol['value'] - section['address']
            body = data[offset:offset + symbol['size']]
            functions.append({'symbol': name, 'address': symbol['value'], 'fileOffset': offset, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(), 'instructions': [{'pc': ins.address, 'mnemonic': ins.mnemonic, 'operands': ins.op_str} for ins in decoder.disasm(body, symbol['value'])]})
        target = raw / (label + '.native.json')
        plt = next(section for section in parsed['sections'] if section['name'] == '.plt')
        slots = [relocation for relocation in parsed['rela'] if relocation['type'] == 1026]
        calls = []
        for function in functions:
            for instruction in function['instructions']:
                if instruction['mnemonic'] not in ['bl', 'b'] or not instruction['operands'].startswith('#0x'):
                    continue
                address = int(instruction['operands'][1:], 16)
                matches = [symbol for symbol in symbols if symbol['sectionIndex'] and symbol['value'] == address]
                symbol = matches[0]['name'] if matches else None
                if plt['address'] + 32 <= address < plt['address'] + plt['bytes'] and (address - plt['address'] - 32) % 24 == 0:
                    slot = (address - plt['address'] - 32) // 24
                    assert slot < len(slots)
                    relocation = slots[slot]
                    file_offset = plt['offset'] + address - plt['address']
                    stub = list(decoder.disasm(data[file_offset:file_offset + 24], address))
                    adrp = next(ins for ins in stub if ins.mnemonic == 'adrp' and ins.op_str.startswith('x16,'))
                    load = next(ins for ins in stub if ins.mnemonic == 'ldr' and ins.op_str.startswith('x17,'))
                    displacement = re.search(r'#(0x[0-9a-f]+|\d+)', load.op_str)
                    got = int(adrp.op_str.split('#')[1], 16) + (int(displacement.group(1), 0) if displacement else 0)
                    assert got == relocation['target']
                    symbol = parsed['dynamicSymbols'][relocation['symbolIndex']]['name']
                if symbol:
                    calls.append({'caller': function['symbol'], 'pc': instruction['pc'], 'target': address, 'symbol': symbol})
        relr_targets = []
        for section in parsed['sections']:
            if section['name'] != '.relr.dyn':
                continue
            assert section['bytes'] % 8 == 0
            cursor = 0
            for position in range(section['offset'], section['offset'] + section['bytes'], 8):
                entry = struct.unpack_from('<Q', data, position)[0]
                if entry & 1:
                    relr_targets += [cursor + index * 8 for index in range(63) if entry & (1 << (index + 1))]
                    cursor += 63 * 8
                else:
                    relr_targets.append(entry)
                    cursor = entry + 8
        vtable = None
        if label == 'app_process64':
            section, = [section for section in parsed['sections'] if section['name'] == '.data.rel.ro']
            assert section['address'] == section['offset'] == 0x8000 and section['bytes'] >= 0x30
            assert all(address in relr_targets for address in [0x8010, 0x8020, 0x8028])
            assert struct.unpack_from('<Q', data, 0x8020)[0] == 0x48a4
            assert struct.unpack_from('<Q', data, 0x8028)[0] == 0x4944
            vtable = {'installedAddressPoint': 0x8010, 'onVmCreatedSlot': 0x10, 'onVmCreatedTarget': 0x48a4, 'onStartedSlot': 0x18, 'onStartedTarget': 0x4944, 'selectedSlotsCoveredByRelr': True}
        registration = None
        if label == 'libandroid_runtime.so':
            def cstring(address):
                section, = [section for section in parsed['sections'] if section['type'] != 8 and section['address'] <= address < section['address'] + section['bytes']]
                offset = section['offset'] + address - section['address']
                end = data.index(b'\0', offset, min(offset + 1024, len(data)))
                return data[offset:end].decode('ascii')
            section, = [section for section in parsed['sections'] if section['address'] <= 0x2e27b0 and 0x2e27b0 + 48 <= section['address'] + section['bytes']]
            offset = section['offset'] + 0x2e27b0 - section['address']
            names = []
            for index in range(2):
                name, signature, function = struct.unpack_from('<QQQ', data, offset + index * 24)
                names.append({'name': cstring(name), 'signature': cstring(signature), 'function': function})
            assert names[0] == {'name': 'nativeFinishInit', 'signature': '()V', 'function': 0x1e5be4}
            entry, = [relocation for relocation in parsed['rela'] if 0x2e27f8 <= relocation['target'] <= 0x2e2d88 and parsed['dynamicSymbols'][relocation['symbolIndex']]['name'] == '_ZN7android44register_com_android_internal_os_RuntimeInitEP7_JNIEnv']
            assert cstring(0x87e41) == 'com/android/internal/os/RuntimeInit'
            registration = {'registrar': 'register_com_android_internal_os_RuntimeInit', 'registrarAddress': 0x1e5b94, 'class': cstring(0x87e41), 'tableAddress': 0x2e27b0, 'methodCount': 2, 'methods': names, 'startRegTableAddress': 0x2e27f8, 'startRegRegistrarEntry': entry['target'], 'startRegEntryRelocationType': entry['type']}
        assert digest(source) == pin
        target.write_text(json.dumps({'source': str(source), 'sourceSha256': pin, 'needed': parsed['needed'], 'functions': functions, 'resolvedDirectCalls': calls, 'symbols': symbols, 'relrTargets': relr_targets, 'selectedVtable': vtable, 'runtimeInitRegistration': registration, 'oemExecuted': False}, indent=2) + '\n')
        result[label] = {'raw': target.relative_to(ROOT).as_posix(), 'rawSha256': digest(target), 'sourceSha256': pin, 'functions': [{key: value for key, value in function.items() if key != 'instructions'} for function in functions], 'resolvedDirectCalls': calls, 'selectedVtable': vtable, 'runtimeInitRegistration': registration, 'sourceVerifiedBeforeAndAfter': True}
    if member_proof:
        (ROOT / 'out/authority-bootstrap-runtime/app-process-member.json').write_text(json.dumps(member_proof, indent=2) + '\n')
    assert digest(parser_path) == parser_sha
    (ROOT / 'out/authority-bootstrap-runtime/native.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'nativeFunctions': {key: len(value['functions']) for key, value in result.items()}, 'oemExecuted': False}))

def module_read():
    raw = ROOT / 'firmware/authority-bootstrap-runtime'
    raw.mkdir(parents=True, exist_ok=True)
    path = raw / 'framework-conscrypt-nsc.jar'
    assert digest(MANIFEST) == MANIFEST_SHA
    logical = 'apex/com.android.conscrypt/javalib/framework-conscrypt-nsc.jar'
    expected, = [row for line in gzip.open(MANIFEST, 'rt') if (row := json.loads(line))['path'] == logical]
    assert expected['sha256'] == NSC_SHA and expected['size'] == 79142
    if not path.exists():
        capture = PARENT / 'firmware/samsung/os-mirror-20261104/mounted-os-20261104T235732022961Z.tar'
        assert capture.stat().st_size == 20434769920
        with tarfile.open(capture, 'r:') as archive:
            for member in archive:
                if member.name.removeprefix('./') != logical:
                    continue
                assert member.isfile() and member.size == 79142
                data = archive.extractfile(member).read(79143)
                assert len(data) == 79142 and hashlib.sha256(data).hexdigest() == NSC_SHA
                path.write_bytes(data)
                (ROOT / 'out/authority-bootstrap-runtime/module-member.json').write_text(json.dumps({'path': logical, 'sha256': NSC_SHA, 'headerOffset': member.offset, 'dataOffset': member.offset_data}, indent=2) + '\n')
                break
            else:
                raise ValueError('Pinned module member absent')
    assert digest(path) == NSC_SHA
    reader = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
    receipt = reader(path, NSC_SHA, class_name='android.security.net.config.NetworkSecurityConfigProvider', methods=['handleNewApplication(Landroid/content/Context;)V'], stream='authority-bootstrap-runtime')
    (ROOT / 'out/authority-bootstrap-runtime/module.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['receipt'])

def display_wire():
    reader = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
    methods = ['getPreferredWideGamutColorSpaceId()I', 'getOverlaySupport()Landroid/hardware/OverlayProperties;']
    result = {}
    for side, archive, pin in [('samsung', ARCHIVE, SHA), ('coloros', PARENT / 'firmware/donor/extracted/system/framework/framework.jar', 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2')]:
        receipt = reader(archive, pin, class_name='android.hardware.display.IDisplayManager$Stub$Proxy', methods=methods, stream='authority-bootstrap-runtime')
        result[side] = receipt['receipt']
    (ROOT / 'out/authority-bootstrap-runtime/display-wire.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))

def summarize():
    work = ROOT / 'out/authority-bootstrap-runtime'
    reads = json.loads((work / 'reads.json').read_text())
    module = json.loads((work / 'module.json').read_text())
    reads['module:NetworkSecurityConfigProvider'] = module['receipt']
    wires = json.loads((work / 'display-wire.json').read_text())
    reads.update({'display-wire:' + side: path for side, path in wires.items()})
    methods = {}
    evidence = []
    for key, path in reads.items():
        receipt_path = ROOT / path
        receipt = json.loads(receipt_path.read_text())
        assert digest(ROOT / receipt['raw']) == receipt['rawSha256']
        assert not receipt['oemCodeExecuted'] and receipt['readerExitCode'] == 0
        lines = {}
        for line_number, line in enumerate((ROOT / receipt['raw']).read_text().splitlines(), 1):
            row = json.loads(line)
            if row['record'] == 'method':
                body = row['body']
                methods[(key, body['signature'])] = body
                lines[body['signature']] = line_number
        evidence.append({'key': key, 'receipt': path, 'receiptSha256': digest(receipt_path), 'raw': receipt['raw'], 'rawSha256': receipt['rawSha256'], 'archiveSha256': receipt['archiveSha256'], 'methods': [{**proof, 'rawMethodLine': lines[proof['signature']]} for proof in receipt['selectedMethodProofs']]})
    reused_path = 'out/tooling/20261105T123938572593Z-7fa57b74656d4701b1ebb25c779e8222/receipt.json'
    assert digest(ROOT / reused_path) == '738b76fd3896b91d745b6de18fb73f592935e8a011768382e7b876220a6db2c4'
    reused = json.loads((ROOT / reused_path).read_text())
    assert digest(ROOT / reused['raw']) == reused['rawSha256']
    signature = 'startBootstrapServices(Lcom/android/server/utils/TimingsTraceAndSlog;)V'
    for line_number, line in enumerate((ROOT / reused['raw']).read_text().splitlines(), 1):
        row = json.loads(line)
        if row['record'] == 'method' and row['body']['signature'] == signature:
            methods[('reused:SystemServer', signature)] = row['body']
            proof, = [proof for proof in reused['selectedMethodProofs'] if proof['signature'] == signature]
            evidence.append({'key': 'reused:SystemServer', 'receipt': reused_path, 'receiptSha256': digest(ROOT / reused_path), 'raw': reused['raw'], 'rawSha256': reused['rawSha256'], 'archiveSha256': reused['archiveSha256'], 'methods': [{**proof, 'rawMethodLine': line_number}]})
            break
    else:
        raise ValueError('Previously pinned bootstrap method absent')
    assertions = []
    def edge(key, method, pc, suffix):
        body = methods[(key, method)]
        instruction, = [ins for ins in body['instructions'] if ins['pc'] == pc]
        assert instruction.get('reference', '').endswith(suffix), (key, method, pc, instruction)
        assertions.append({'selection': key, 'method': method, 'pc': hex(pc), 'referenceSuffix': suffix})
    edge('android.app.ActivityThread', 'systemMain()Landroid/app/ActivityThread;', 0, '->initForSystemProcess()V')
    edge('android.app.ActivityThread', 'systemMain()Landroid/app/ActivityThread;', 11, '->attach(ZJ)V')
    edge('android.app.ActivityThread', 'attach(ZJ)V', 74, '->initializeSystemThread(Landroid/app/ActivityThread;)V')
    edge('android.app.ActivityThread', 'attach(ZJ)V', 46, '->attachApplication(Landroid/app/IApplicationThread;J)V')
    edge('android.app.ActivityThread', 'attach(ZJ)V', 82, '->addConfigCallback(Landroid/view/ViewRootImpl$ConfigChangedCallback;)V')
    edge('android.app.ActivityThread', 'getSystemContext()Landroid/app/ContextImpl;', 5, '->createSystemContext(Landroid/app/ActivityThread;)Landroid/app/ContextImpl;')
    edge('android.app.ActivityThread#system-init', 'initializeSystemThread(Landroid/app/ActivityThread;)V', 29, '->makeApplicationInner(ZLandroid/app/Instrumentation;)Landroid/app/Application;')
    edge('android.app.ActivityThread#system-init', 'initializeSystemThread(Landroid/app/ActivityThread;)V', 35, '->onCreate()V')
    edge('android.net.Uri$$ExternalSyntheticBUOutline0', 'm(Ljava/lang/String;Ljava/lang/Throwable;)V', 2, '-><init>(Ljava/lang/String;Ljava/lang/Throwable;)V')
    edge('android.app.Application', 'onCreate()V', 0, '->setFlipFonts()V')
    edge('android.graphics.HardwareRenderer', 'setIsSystemOrPersistent()V', 1, '->nSetIsSystemOrPersistent(Z)V')
    edge('android.app.ContextImpl', 'createSystemContext(Landroid/app/ActivityThread;)Landroid/app/ContextImpl;', 5, '->createSystemContextInner(Landroid/app/ActivityThread;Landroid/app/LoadedApk;)Landroid/app/ContextImpl;')
    constructor = next(signature for key, signature in methods if key == 'android.app.ContextImpl#inner' and signature.startswith('<init>'))
    edge('android.app.ContextImpl#inner', constructor, 93, '->createServiceCache()[Ljava/lang/Object;')
    edge('android.app.ContextImpl#inner', constructor, 285, '->createAttributionSource(Ljava/lang/String;Landroid/content/AttributionSource;Ljava/util/Set;ZI)Landroid/content/AttributionSource;')
    edge('android.app.SystemServiceRegistry', '<clinit>()V', 21, '->registerServices()V')
    edge('android.app.SystemServiceRegistry#registration', 'registerServices()V', 0xb24, '->registerServiceWrappers()V')
    edge('android.app.SystemServiceRegistry#lookup', 'getSystemServiceName(Ljava/lang/Class;)Ljava/lang/String;', 6, '->get(Ljava/lang/Object;)Ljava/lang/Object;')
    edge('android.app.ResourcesManager#display', 'getDisplayMetrics(ILandroid/view/DisplayAdjustments;)Landroid/util/DisplayMetrics;', 0, '->getInstance()Landroid/hardware/display/DisplayManagerGlobal;')
    edge('android.hardware.display.DisplayManagerGlobal', 'getInstance()Landroid/hardware/display/DisplayManagerGlobal;', 9, '->getService(Ljava/lang/String;)Landroid/os/IBinder;')
    edge('android.hardware.display.DisplayManagerGlobal', '<init>(Landroid/hardware/display/IDisplayManager;)V', 0xac, '->getPreferredWideGamutColorSpaceId()I')
    edge('android.hardware.display.DisplayManagerGlobal', '<init>(Landroid/hardware/display/IDisplayManager;)V', 0xb8, '->getOverlaySupport()Landroid/hardware/OverlayProperties;')
    edge('android.app.LoadedApk', '<init>(Landroid/app/ActivityThread;)V', 95, '->getSystem()Landroid/content/res/Resources;')
    edge('android.app.LoadedApk', '<init>(Landroid/app/ActivityThread;)V', 101, '->getSystemClassLoader()Ljava/lang/ClassLoader;')
    edge('android.app.LoadedApk', 'makeApplicationInner(ZLandroid/app/Instrumentation;Z)Landroid/app/Application;', 0xa8, '->callNetworkSecurityConfigProviderHandleNewApplication(Landroid/content/Context;)V')
    edge('module:NetworkSecurityConfigProvider', 'handleNewApplication(Landroid/content/Context;)V', 0x57, '->setDefaultInstance(Landroid/security/net/config/ApplicationConfig;)V')
    edge('android.app.ContextImpl', 'getApplicationContext()Landroid/content/Context;', 4, '->getApplication()Landroid/app/Application;')
    edge('android.app.ActivityThread#package-info', 'installSystemApplicationInfo(Landroid/content/pm/ApplicationInfo;Ljava/lang/ClassLoader;)V', 5, '->installSystemApplicationInfo(Landroid/content/pm/ApplicationInfo;Ljava/lang/ClassLoader;)V')
    edge('android.app.ActivityThread#package-info', 'installSystemApplicationInfo(Landroid/content/pm/ApplicationInfo;Ljava/lang/ClassLoader;)V', 8, '->getSystemUiContext()Landroid/content/Context;')
    edge('reused:SystemServer', signature, 0x5c9, '->getApplicationInfo(Ljava/lang/String;I)Landroid/content/pm/ApplicationInfo;')
    edge('reused:SystemServer', signature, 0x5d7, '->installSystemApplicationInfo(Landroid/content/pm/ApplicationInfo;Ljava/lang/ClassLoader;)V')
    edge('android.app.ContextImpl', 'getPackageManager()Landroid/content/pm/PackageManager;', 5, '->getPackageManagerInner()Landroid/content/pm/PackageManager;')
    edge('android.app.ActivityThread', 'getPackageManager()Landroid/content/pm/IPackageManager;', 10, '->getService(Ljava/lang/String;)Landroid/os/IBinder;')
    edge('android.app.ContextImpl', 'checkPermission(Ljava/lang/String;II)I', 56, '->checkPermission(Ljava/lang/String;III)I')
    edge('android.os.Looper', 'prepareMainLooper()V', 1, '->prepare(Z)V')
    edge('android.os.Looper#prepare', '<init>(Z)V', 8, '-><init>(Z)V')
    edge('android.os.MessageQueue', '<init>(Z)V', 0x42, '->nativeInit()J')
    edge('android.os.Looper', 'loop()V', 34, '->loopOnce(Landroid/os/Looper;JI)Z')
    edge('com.android.internal.os.RuntimeInit', 'main([Ljava/lang/String;)V', 21, '->commonInit()V')
    edge('com.android.internal.os.RuntimeInit', 'main([Ljava/lang/String;)V', 24, '->nativeFinishInit()V')
    wire = {}
    for side, expected in [('samsung', [71, 86]), ('coloros', [44, 59])]:
        wire[side] = {}
        for signature, transaction in zip(['getPreferredWideGamutColorSpaceId()I', 'getOverlaySupport()Landroid/hardware/OverlayProperties;'], expected):
            body = methods[('display-wire:' + side, signature)]
            values = {ins['pc']: ins for ins in body['instructions']}
            assert values[0x13]['literal'] == transaction
            assert values[0x15]['literal'] == 0 and values[0x16]['reference'].endswith('->transact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z')
            wire[side][signature] = {'transaction': transaction, 'flags': 0, 'transactPc': '0x16'}
    native_proof = json.loads((work / 'native.json').read_text())
    for value in native_proof.values():
        assert digest(ROOT / value['raw']) == value['rawSha256']
    peer_docs = ['docs/security-native-linkage.md', 'docs/authority-bootstrap-handoff.md']
    inventory = {'schema': 'authority-bootstrap-runtime/v1', 'status': 'source-path-pinned; unchanged-guest-display-protocol-blocked; no-entry-emitted', 'source': {'archive': '../firmware/samsung/framework.jar', 'sha256': SHA, 'networkModuleSha256': NSC_SHA, 'capturedManifestSha256': MANIFEST_SHA}, 'methodEvidence': evidence, 'assertions': assertions, 'assertionCount': len(assertions), 'selectedMethodBodies': sum(len(item['methods']) for item in evidence), 'displayWire': wire, 'nativeEvidence': native_proof, 'evidenceReferences': {name: digest(ROOT / name) for name in peer_docs}, 'proposedEntry': {'class': 'com.appleexploit.oneos.security.authority.SamsungAuthorityMain', 'method': 'public static void main(String[])', 'emitted': False, 'contextOnlyProbeEmitted': False, 'reason': 'Root requires renderer/native/module/Context first-effect closure before a separately approved context-only compile probe; exact display sender mismatch remains.'}, 'frontiers': ['Original Samsung bootclasspath/APEX/ART/linker/resource/native/property view before class initialization, not framework.jar alone', 'SystemServiceRegistry module initializer transitive bodies and native graphics/font first effects are not fully closed', 'Global display must supply proven original protocol, or an explicit source-supported narrow acquisition adaptation; do not supply fake absent service', 'Original package/permission/AM/user/policy endpoints and caches require their own proven ownership and protocol', 'Real Context acquisition is not LSS/SPM/FP startup, policy readiness, state ownership, cancellation/drain or hardware/key acceptance'], 'executed': {'staticReaders': True, 'oemClasses': False, 'oemNative': False, 'android': False, 'phone': False, 'compiledProbe': False}, 'toolSha256': digest(__file__)}
    target = ROOT / 'inventory/authority-bootstrap-runtime.json'
    target.write_text(json.dumps(inventory, indent=2) + '\n')
    print(json.dumps({'pass': True, 'assertions': len(assertions), 'selectedMethodBodies': inventory['selectedMethodBodies'], 'inventory': str(target), 'oemExecuted': False, 'entryEmitted': False}))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--read', action='store_true', help='Acquire missing exact static selections')
    parser.add_argument('--native', action='store_true', help='Selectively read/disassemble pinned native entry bodies')
    parser.add_argument('--module', action='store_true', help='Read exact NSC module dependency from indexed captured member')
    parser.add_argument('--display-wire', action='store_true', help='Compare two display Proxy calls eager Context creation reaches')
    parser.add_argument('--summarize', action='store_true', help='Verify captured exact assertions and emit bounded derived inventory')
    args = parser.parse_args()
    work = ROOT / 'out/authority-bootstrap-runtime'
    work.mkdir(parents=True, exist_ok=True)
    if args.summarize:
        summarize()
        return
    if args.native:
        native()
        return
    if args.module:
        module_read()
        return
    if args.display_wire:
        display_wire()
        return
    path = work / 'reads.json'
    reads = json.loads(path.read_text()) if path.exists() else {}
    reader = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
    for name, methods in QUERIES.items():
        if name not in reads:
            if not args.read:
                raise ValueError('Missing selection: ' + name)
            receipt = reader(ARCHIVE, SHA, class_name=name.split('#')[0], methods=methods, stream='authority-bootstrap-runtime')
            reads[name] = receipt['receipt']
            path.write_text(json.dumps(reads, indent=2) + '\n')
        receipt = json.loads((ROOT / reads[name]).read_text())
        assert receipt['archiveSha256'] == SHA
        assert digest(ROOT / receipt['raw']) == receipt['rawSha256']
        assert receipt['query']['exactMethods'] == methods
        assert not receipt['oemCodeExecuted']
        print(name, reads[name], len(receipt['selectedMethodProofs']), flush=True)
    assert digest(ARCHIVE) == SHA

if __name__ == '__main__':
    main()
