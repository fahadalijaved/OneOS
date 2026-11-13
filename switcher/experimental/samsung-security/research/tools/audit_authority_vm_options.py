"""Bounded offline Samsung AndroidRuntime VM-option evidence. Never executes OEM code."""
import argparse, hashlib, json, lzma, re, runpy, sys
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'firmware/authority-vm-options'
OUT = ROOT / 'out/authority-vm-options'
SOURCE = ROOT.parent / 'firmware/samsung/runtime-20261104/libandroid_runtime.so'
PIN = 'f77d49dcfae7271ec3508cb06948218e65bdfbd1dc284797cb650b0db09af57d'
WANTED = ['AndroidRuntime7startVm', 'AndroidRuntime18parseRuntimeOption',
          'AndroidRuntime26parseCompilerRuntimeOption', 'AndroidRuntime14parseExtraOpts',
          'AndroidRuntime9addOption', 'AndroidRuntime5startE', 'JNI_CreateJavaVM']

def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf8')

def capture():
    assert sha(SOURCE) == PIN
    parser = ROOT / 'tools/audit_security_native_linkage.py'
    parser_pin = sha(parser)
    elf = runpy.run_path(str(parser))['elf']
    sys.path.insert(0, str(ROOT / 'out/security-native/static-disassembler'))
    import capstone
    decoder = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    decoder.detail = True
    data = SOURCE.read_bytes(); parsed = elf(data); sections = parsed['sections']
    debug, = [s for s in sections if s['name'] == '.gnu_debugdata']
    mini = lzma.decompress(data[debug['offset']:debug['offset'] + debug['bytes']])
    assert len(mini) < 16 * 1024 * 1024
    symbols = parsed['dynamicSymbols'] + elf(mini)['dynamicSymbols']
    def offset(addr, size=1):
        s, = [s for s in sections if s['type'] != 8 and s['address'] <= addr and addr + size <= s['address'] + s['bytes']]
        return s['offset'] + addr - s['address']
    def string(addr):
        try:
            off = offset(addr); end = data.index(b'\0', off, min(len(data), off + 512))
            value = data[off:end]
            return value.decode('ascii') if value and all(32 <= c < 127 or c in [9,10,13] for c in value) else None
        except (ValueError, UnicodeError): return None
    plt, = [s for s in sections if s['name'] == '.plt']
    slots = [r for r in parsed['rela'] if r['type'] == 1026]
    def call_symbol(addr):
        if plt['address'] + 32 <= addr < plt['address'] + plt['bytes'] and (addr - plt['address'] - 32) % 24 == 0:
            relocation = slots[(addr - plt['address'] - 32) // 24]
            stub = list(decoder.disasm(data[offset(addr,24):offset(addr,24)+24], addr))
            adrp = next(i for i in stub if i.mnemonic == 'adrp' and i.op_str.startswith('x16,'))
            load = next(i for i in stub if i.mnemonic == 'ldr' and i.op_str.startswith('x17,'))
            disp = re.search(r'#(0x[0-9a-f]+|\d+)', load.op_str)
            assert int(adrp.op_str.split('#')[1],16) + (int(disp.group(1),0) if disp else 0) == relocation['target']
            return parsed['dynamicSymbols'][relocation['symbolIndex']]['name']
        matches = [s['name'] for s in symbols if s['sectionIndex'] and s['value'] == addr]
        return matches[0] if matches else None
    funcs=[]; seen=set()
    for s in symbols:
        if not s['sectionIndex'] or s['type'] != 2 or not s['size'] or not any(k in s['name'] for k in WANTED) or s['value'] in seen: continue
        seen.add(s['value']); off=offset(s['value'],s['size']); body=data[off:off+s['size']]
        insns=[]; pages={}
        for ins in decoder.disasm(body,s['value']):
            row={'pc':ins.address,'bytes':ins.bytes.hex(),'mnemonic':ins.mnemonic,'operands':ins.op_str}
            # Bounded literal-address annotations only, not a general data-flow or execution model.
            if ins.mnemonic == 'adrp':
                reg, value=ins.op_str.split(', '); pages[reg]=(int(value[1:],0),ins.address)
            if ins.mnemonic == 'add' and len(ins.operands)==3 and ins.operands[2].type==capstone.CS_OP_IMM:
                src=ins.reg_name(ins.operands[1].reg)
                if src in pages and ins.address-pages[src][1] <= 40:
                    addr=pages[src][0]+ins.operands[2].imm; value=string(addr)
                    if value: row['literalAddress']=addr; row['literal']=value; row['adrpPc']=pages[src][1]
            if ins.mnemonic in ['bl','b'] and ins.op_str.startswith('#0x'):
                target=int(ins.op_str[1:],16); name=call_symbol(target)
                if name: row['targetSymbol']=name
            insns.append(row)
        assert len(insns)*4 == len(body)
        funcs.append({'symbol':s['name'],'address':s['value'],'fileOffset':off,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'instructions':insns})
    assert len(funcs)==7 and sha(SOURCE)==PIN and sha(parser)==parser_pin
    save(RAW/'selected-native.json',{'source':str(SOURCE),'sourceSha256':PIN,'elfMachine':183,'pcKind':'ELF virtual address, not live address','functions':funcs,'annotationLimits':'ADRP/ADD local literal pairs only; review instruction spans; not emulation','oemExecuted':False})
    save(OUT/'capture.json',{'sourceArchive':str(SOURCE),'sourceArchiveSha256':PIN,'raw':'firmware/authority-vm-options/selected-native.json','rawSha256':sha(RAW/'selected-native.json'),'parser':str(parser.relative_to(ROOT)),'parserSha256':parser_pin,'capstoneVersion':capstone.__version__,'functions':[{k:v for k,v in f.items() if k!='instructions'} for f in funcs],'oemExecuted':False})
    print(json.dumps({'pass':True,'functions':len(funcs),'instructions':sum(len(f['instructions']) for f in funcs),'oemExecuted':False}))

def audit():
    receipt=json.loads((OUT/'capture.json').read_text())
    assert sha(SOURCE)==PIN and sha(ROOT/receipt['raw'])==receipt['rawSha256']
    assert sha(ROOT/receipt['parser'])==receipt['parserSha256']
    raw=json.loads((ROOT/receipt['raw']).read_text()); binary=SOURCE.read_bytes()
    for f in raw['functions']:
        assert hashlib.sha256(binary[f['fileOffset']:f['fileOffset']+f['bytes']]).hexdigest()==f['sha256']
        assert b''.join(bytes.fromhex(i['bytes']) for i in f['instructions'])==binary[f['fileOffset']:f['fileOffset']+f['bytes']]
    index={i['pc']:i for f in raw['functions'] for i in f['instructions']}
    checks=[]
    def check(pc,key,value):
        assert index[pc][key]==value, (hex(pc),key,index[pc].get(key),value)
        checks.append({'pc':pc,'pcHex':hex(pc),'field':key,'expected':value})
    for pc,value in [(0x184868,'profilebootclasspath'),(0x184910,'dalvik.vm.profilebootclasspath'),
                     (0x184950,'runtime_native_boot'),(0x184968,'enable_apex_image'),
                     (0x1849fc,'dalvik.vm.boot-image'),(0x184a04,'-Ximage:'),
                     (0x185bcc,'-Xforcejitzygote'),(0x185558,'dalvik.vm.extra-opts'),
                     (0x185cf0,'-Xdeny-art-apex-data-files'),(0x1855c8,'dalvik.vm.image-dex2oat-filter'),
                     (0x18573c,'dalvik.vm.image-dex2oat-flags')]: check(pc,'literal',value)
    for pc,value in [(0x1849e0,'w19, #0, #0x185bc8'),(0x1849f4,'w0, #0, #0x185bc8'),
                     (0x185bfc,'#0x184a38'),(0x184a24,'w0, #0, #0x185e90'),
                     (0x185f30,'w21, #0x185f44'),(0x185570,'x2, xzr'),
                     (0x186038,'w8, #0x20'),(0x186058,'w8, #0x20'),
                     (0x186060,'wzr, [x19, #-1]'),(0x186070,'x8, #0x1860c0'),
                     (0x1e5fa8,'x1, x2, [sp]'),(0x1e5fac,'x0, x0, #8'),
                     (0x185b78,'x0, x21, #8'),(0x185b90,'x8, [x21, #0x18]'),
                     (0x185b98,'wzr, [x26, #0xe8]'),(0x186124,'x8')]: check(pc,'operands',value)
    for pc,word in [(0x184a18,'parseRuntimeOption'),(0x185564,'property_get'),
                    (0x185574,'parseExtraOpts'),(0x185f28,'property_get'),
                    (0x185f40,'VectorImpl3add'),(0x186084,'VectorImpl3add'),
                    (0x1860d4,'VectorImpl3add'),(0x1e5fb4,'VectorImpl3add'),
                    (0x1e61cc,'startVm'),(0x185ba0,'JNI_CreateJavaVM')]:
        assert word in index[pc]['targetSymbol']; checks.append({'pc':pc,'pcHex':hex(pc),'targetContains':word})
    app_path=ROOT/'firmware/authority-bootstrap-runtime/app_process64.native.json'
    assert sha(app_path)=='816b629cab4a4358504bc72ced43730084e30497789e3ab6cf871991da187993'
    app=json.loads(app_path.read_text()); ai={i['pc']:i for f in app['functions'] for i in f['instructions']}
    for pc,mn,op in [(0x41a4,'bl','#0x4cc0'),(0x41b4,'bl','#0x4ca8'),
                     (0x41f8,'cmp','w8, #0x2d'),(0x420c,'ldrb','w8, [x23, #2]'),
                     (0x4594,'mov','w3, wzr'),(0x4598,'bl','#0x4dc8')]:
        assert ai[pc]['mnemonic']==mn and ai[pc]['operands']==op
        checks.append({'source':'reused app_process64 raw','pc':pc,'pcHex':hex(pc),'mnemonic':mn,'operands':op})
    pri_path=ROOT/'out/authority-boot-framework/aosp-inputs.json'
    assert sha(pri_path)=='c5ab6dc831565446edf8d50e6cae1a086ae6b38c679abfca8eac059dcb41e873'
    primary=[r for r in json.loads(pri_path.read_text()) if r['sourceRelativePath'] in ['cmds/app_process/app_main.cpp','core/jni/AndroidRuntime.cpp','runtime/parsed_options.cc']]
    for r in primary: assert sha(ROOT/r['path'])==r['sha256']
    metadata=ROOT.parent/'out/os-comparison-resumed/samsung-inventory.json'
    queries=list(json.loads(metadata.read_text())['queries'])
    assert queries==['os-roots','mountinfo','bootclasspath','systemserverclasspath','os-sizes-kib','apex-info','current-base-hashes','osense-service','urcc-service']
    cards={'docs/authority-boot-framework.md':'498c2fc83901a8a34d6902b7135d771f8d5e46f8a72d8a8192ff8a6472b742fc',
           'inventory/authority-boot-framework.json':'8a7b144c1c9024ffbff548568439b2e81a9c072ecd05683469a7fbc33f31f96a',
           'docs/security-authority-quiescence.md':'946604e673df1c989e552b2e915e5ddeb3977ac834f64abc558e37e09a8f9da3',
           'inventory/security-authority-quiescence.json':'352d9b2ddd3f003f49b6027e2f9bb13dbad57f09a0e8208c562e220847ff43bd'}
    for path,pin in cards.items(): assert sha(ROOT/path)==pin
    vm=next(f for f in raw['functions'] if '7startVm' in f['symbol'])
    assert not any('-Xbootclasspath' in i.get('literal','') or '-Xallowinmemorycompilation' in i.get('literal','') for i in vm['instructions'])
    inv={'schema':'authority-vm-options-source/v1','status':'STATIC_OPTION_CONSTRUCTION_ONLY; no admitted launcher or matched ART parser proof',
         'selected':False,'oemExecuted':False,'deviceInspected':False,'nativeEvidence':receipt,
         'checks':checks,'primaryMechanismReferences':primary,
         'reusedAppProcessProof':{'path':app_path.relative_to(ROOT).as_posix(),'sha256':sha(app_path),'sourceSha256':app['sourceSha256']},
         'capturedPublicMetadata':{'inventory':str(metadata),'sha256':sha(metadata),'queries':queries,'effectiveVmPropertySnapshotPresent':False,'scope':'These listed metadata queries only; not a universal absence assertion'},
         'optionOrder':['app_process main argv -> existing mOptions before AndroidRuntime.start',
                        'profile option group and profile/enable_apex_image boot-image branch',
                        'dalvik.vm.boot-image option only on non-forced-image branch and nonempty property',
                        'ordinary runtime/compiler property options',
                        'dalvik.vm.extra-opts ASCII-space tokens (no prefix) at 0x185574',
                        'image compiler options, locale/trace/native bridge/ABI/fingerprint options',
                        'existing Vector options pointer/count -> JNI_CreateJavaVM at 0x185ba0'],
         'boundedInference':['Native option insertion order proved; duplicate/conflict effective precedence not proved for Samsung ART',
                             'No direct -Xbootclasspath or -Xallowinmemorycompilation literal construction in selected startVm annotations; caller/extra-opts/ART processing remain distinct',
                             'GetServerConfigurableFlag is imported; its backend and current values are not inferred',
                             'JNI_CreateJavaVM local wrapper calls pthread_once and indirect slot 0x300820; no selected libart/runtime PID attestation'],
         'requiredNextEvidence':['Exact future process argv/env/ordered JavaVMOption strings including property-derived values and relevant server flags',
                                 'Matching actual Samsung ART duplicate, image-conflict and in-memory compilation behavior',
                                 'Selected boot-image/oat/vdex and data cache paths plus full coherent modified BCP/helper closure before first boot-class resolution',
                                 'Retained original Samsung mount/APEX/library view with native linkage identity; no global property edits as workaround',
                                 'Real original-authority quiescence/native completion and guest display producer bootstrap ordering'],
         'preservedCards':[{'path':p,'sha256':pin} for p,pin in cards.items()]}
    path=ROOT/'inventory/authority-vm-options.json'; save(path,inv)
    save(OUT/'checks.json',{'pass':True,'instructionAssertions':len(checks),'functions':len(raw['functions']),'instructions':sum(len(f['instructions']) for f in raw['functions']),'sourceVerified':True,'oemExecuted':False})
    frozen=[ROOT/'docs/authority-vm-options.md',path,Path(__file__),OUT/'capture.json',OUT/'checks.json',ROOT/receipt['raw']]
    save(OUT/'FROZEN-MANIFEST.json',{'selected':False,'oemExecuted':False,'files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in frozen]})
    print(json.dumps({'pass':True,'functions':len(raw['functions']),'instructionAssertions':len(checks),'selected':False,'oemExecuted':False}))

if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--capture',action='store_true'); args=ap.parse_args()
    if args.capture: capture()
    else: audit()
