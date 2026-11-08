"""Bounded static common-ancestor namespace proof. No namespaces or OEM code run."""
from pathlib import Path
import argparse
import hashlib
import json
import lzma
import re
import runpy
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'firmware/guest-common-namespace-proof'
OUT = ROOT / 'out/guest-common-namespace-proof'
COLOROS = ROOT.parent / 'firmware/donor/extracted/system/lib64/libandroid_runtime.so'
COLOROS_SHA = 'edfd170ccbca035d6acd8da1b93a346a7cb438f35cf706ba03037bdc1feb1279'
INSTALLD = ROOT / 'firmware/retained-installd-native-owner/20261106T024945006359Z-7b005bf1d2054ec4821a3e3ebdfdf978/installd'
INSTALLD_SHA = 'ed618c386528c0b9890c67cbdcb22e1c194f44b034d8e36be2d7f2217fef7dfc'
PARSER = ROOT / 'tools/audit_security_native_linkage.py'
PARSER_SHA = '33c005e05b884ce03f4b57d3e288a62211abb78a2203ee8f3834bdce8a7d9831'
WANTED = ['UnmountStorageOnInit', 'Zygote_nativeInitNativeState', 'SpecializeCommon',
          'ensureInAppMountNamespace', 'MountInitOverride']
CAPTURE_SHA = '42da71e4af04ad556b689f1968c15b40cb2b1d3c15fe4306fe6ee781bee223d2'
RAW_SHA = '5568c1a4c5ad983b3d3ab0828fec95b44397c22b388f8479c80a72445d5bb631'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def capture():
    assert sha(COLOROS) == COLOROS_SHA and sha(INSTALLD) == INSTALLD_SHA and sha(PARSER) == PARSER_SHA
    elf = runpy.run_path(str(PARSER))['elf']
    sys.path.insert(0, str(ROOT / 'out/security-native/static-disassembler'))
    import capstone
    cs = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    cs.detail = True
    data = COLOROS.read_bytes()
    parsed = elf(data)
    sections = parsed['sections']
    debug, = [s for s in sections if s['name'] == '.gnu_debugdata']
    mini = lzma.decompress(data[debug['offset']:debug['offset'] + debug['bytes']], memlimit=32 * 1024 * 1024)
    assert len(mini) < 8 * 1024 * 1024
    symbols = parsed['dynamicSymbols'] + elf(mini)['dynamicSymbols']
    def offset(addr, size=1):
        s, = [s for s in sections if s['type'] != 8 and s['address'] <= addr and addr + size <= s['address'] + s['bytes']]
        return s['offset'] + addr - s['address']
    def string(addr):
        try:
            off = offset(addr)
            end = data.index(b'\0', off, min(len(data), off + 512))
            value = data[off:end]
            return value.decode('ascii') if value and all(32 <= c < 127 or c in (9,10,13) for c in value) else None
        except (ValueError, UnicodeError):
            return None
    plt, = [s for s in sections if s['name'] == '.plt']
    slots = [r for r in parsed['rela'] if r['type'] == 1026]
    def resolve(addr):
        names = [s['name'] for s in symbols if s['sectionIndex'] and s['value'] == addr]
        if names:
            return names[0]
        if plt['address'] + 32 <= addr < plt['address'] + plt['bytes'] and (addr - plt['address'] - 32) % 24 == 0:
            relocation = slots[(addr - plt['address'] - 32) // 24]
            stub = list(cs.disasm(data[offset(addr,24):offset(addr,24)+24],addr))
            adrp = next(i for i in stub if i.mnemonic == 'adrp' and i.op_str.startswith('x16,'))
            load = next(i for i in stub if i.mnemonic == 'ldr' and i.op_str.startswith('x17,'))
            disp = re.search(r'#(0x[0-9a-f]+|\d+)',load.op_str)
            assert int(adrp.op_str.split('#')[1],16) + (int(disp.group(1),0) if disp else 0) == relocation['target']
            return parsed['dynamicSymbols'][relocation['symbolIndex']]['name']
        return None
    functions = []
    seen = set()
    for sym in symbols:
        if not sym['sectionIndex'] or sym['type'] != 2 or not sym['size'] or sym['value'] in seen or not any(w in sym['name'] for w in WANTED):
            continue
        assert sym['size'] <= 32768
        seen.add(sym['value'])
        off = offset(sym['value'],sym['size'])
        code = data[off:off+sym['size']]
        instructions = []
        pages = {}
        for ins in cs.disasm(code,sym['value']):
            row = {'pc':ins.address,'bytes':ins.bytes.hex(),'mnemonic':ins.mnemonic,'operands':ins.op_str}
            if ins.mnemonic == 'adrp':
                reg, address = ins.op_str.split(', ');pages[reg] = (int(address[1:],0),ins.address)
            address = None
            if ins.mnemonic == 'adr' and len(ins.operands) == 2 and ins.operands[1].type == capstone.CS_OP_IMM:
                address = ins.operands[1].imm
            if ins.mnemonic == 'add' and len(ins.operands) == 3 and ins.operands[2].type == capstone.CS_OP_IMM:
                reg = ins.reg_name(ins.operands[1].reg)
                if reg in pages and ins.address - pages[reg][1] <= 40:
                    address = pages[reg][0] + ins.operands[2].imm
            if address is not None:
                value = string(address)
                if value:row.update({'literalAddress':address,'literal':value})
            if ins.mnemonic in ('b','bl') and ins.op_str.startswith('#0x'):
                target = int(ins.op_str[1:],16);name = resolve(target)
                row['targetPc'] = target
                if name:row['targetSymbol'] = name
            instructions.append(row)
        assert len(instructions)*4 == len(code)
        functions.append({'symbol':sym['name'],'address':sym['value'],'fileOffset':off,'bytes':len(code),
                          'sha256':hashlib.sha256(code).hexdigest(),'instructions':instructions})
    assert len(functions) == 5
    # Query the exact installd dynamic imports, not every transitive library initializer.
    native = elf(INSTALLD.read_bytes())
    imports = [s['name'] for s in native['dynamicSymbols'] if not s['sectionIndex']]
    explicit_isolation = [s for s in imports if s in ('unshare','setns','chroot','pivot_root')]
    assert not explicit_isolation
    assert 'syscall' in imports
    assert sha(COLOROS) == COLOROS_SHA and sha(INSTALLD) == INSTALLD_SHA
    save(RAW/'coloros-zygote-selected.json',{'source':str(COLOROS),'sourceSha256':COLOROS_SHA,'functions':functions,
                                          'pcKind':'ELF virtual addresses, not live PCs','scope':'original captured ColorOS source; actual staged/loaded native runtime identity not established'})
    save(OUT/'capture.json',{'coloros':{'path':'../firmware/donor/extracted/system/lib64/libandroid_runtime.so','sha256':COLOROS_SHA},
                            'installd':{'path':INSTALLD.relative_to(ROOT).as_posix(),'sha256':INSTALLD_SHA},
                            'parserSha256':PARSER_SHA,'raw':'firmware/guest-common-namespace-proof/coloros-zygote-selected.json',
                            'rawSha256':sha(RAW/'coloros-zygote-selected.json'),'functions':[{k:v for k,v in f.items() if k!='instructions'} for f in functions],
                            'installdExplicitIsolationImports':explicit_isolation,'installdGenericSyscallImport':True,
                            'oemExecuted':False,'capstoneVersion':capstone.__version__})
    print(json.dumps({'functions':len(functions),'instructions':sum(len(f['instructions']) for f in functions),'oemExecuted':False}))


def audit():
    assert sha(COLOROS) == COLOROS_SHA and sha(INSTALLD) == INSTALLD_SHA and sha(PARSER) == PARSER_SHA
    assert sha(OUT/'capture.json') == CAPTURE_SHA and sha(RAW/'coloros-zygote-selected.json') == RAW_SHA
    raw = json.loads((RAW/'coloros-zygote-selected.json').read_text(encoding='utf-8'))
    capture_proof = json.loads((OUT/'capture.json').read_text(encoding='utf-8'))
    data = COLOROS.read_bytes()
    index = {}
    for f in raw['functions']:
        code = data[f['fileOffset']:f['fileOffset']+f['bytes']]
        assert hashlib.sha256(code).hexdigest() == f['sha256']
        assert b''.join(bytes.fromhex(i['bytes']) for i in f['instructions']) == code
        for i in f['instructions']:
            assert i['pc'] not in index
            index[i['pc']] = i
    assert len(index) == 5304
    checks = []
    def check(pc, field, expected):
        assert index[pc][field] == expected, (hex(pc), field, index[pc].get(field))
        checks.append({'pc':hex(pc),'field':field,'expected':expected})
    def target(pc, fragment):
        assert fragment in index[pc]['targetSymbol'], (hex(pc),index[pc])
        checks.append({'pc':hex(pc),'targetContains':fragment})
    for pc, op in [(0x28249c,'w0, #0x20000'), (0x2824ac,'w3, #0x4000'),
                   (0x2824c4,'w3, #8, lsl #16'), (0x282498,'w0, #0x282558'),
                   (0x28257c,'#0x2824ac'), (0x12d704,'w0, #0x20000'),
                   (0x12d6e8,'w8, #0, #0x12d700')]:
        check(pc,'operands',op)
    for pc, text in [(0x282480,'service_name'), (0x282490,'zygote_c'),
                     (0x2824b4,'rootfs'), (0x2824bc,'/'),
                     (0x282564,'UnmountStorageOnInit: zygote_c process, skip unshare'),
                     (0x134760,'/system/etc/init')]:
        check(pc,'literal',text)
    for pc, name in [(0x27fe50,'UnmountStorageOnInit'), (0x282484,'getenv'),
                     (0x2824a0,'unshare'), (0x2824cc,'mount'), (0x282578,'unsetenv'),
                     (0x12d708,'unshare'), (0x12e2d0,'ensureInAppMountNamespace'),
                     (0x12e480,'ensureInAppMountNamespace'), (0x12ec70,'ensureInAppMountNamespace'),
                     (0x131018,'MountInitOverride'), (0x134788,'mount')]:
        target(pc,name)
    ensure = next(f for f in raw['functions'] if 'ensureInAppMountNamespace' in f['symbol'])
    assert not any(i.get('targetSymbol') == 'mount' for i in ensure['instructions'])
    native_raw_path = ROOT/'firmware/retained-installd-native-owner/static/selected-native.json'
    assert sha(native_raw_path) == '073ce4abb6ed496693e57a529b7a6e7c9d24d8785df7f20135db5ea79a02f776'
    native_raw = json.loads(native_raw_path.read_text(encoding='utf-8'))
    native_entries = [f for f in native_raw['functions'] if f['symbol'] == 'main' or f['symbol'].endswith('NativeService5startEv')]
    assert len(native_entries) == 2
    for f in native_entries:
        assert not any(i.get('targetSymbol') in ('unshare','setns','chroot','pivot_root','syscall') or i['mnemonic']=='svc' for i in f['instructions'])
    assert capture_proof['installdExplicitIsolationImports'] == [] and capture_proof['installdGenericSyscallImport']
    checks.append({'installdScope':'main/start no direct namespace/root/syscall/svc edges; no explicit isolation imports; generic syscall elsewhere and transitive constructors/libraries remain unclosed'})
    inputs = {
        'out/installed-oneos-code-profile/static/appdata-bridge-source.json':'07e8bcf175ece148ae86a7d81435fbe0c40bdb9b6fab4aeffa8d91702691c040',
        'inventory/guest-private-data-plan.json':'2c6034331f33d06a029adf8127e136e3ae1fe53ad02a3ae61a91c2c08a197dca',
        'inventory/guest-installd-data-view.json':'b1381a57c778366a5e3c6586dfffd58c63b89ef237a2bd10c0b39448dbf64801',
        'out/retention-native-view-observation/20261106T022427951464Z-d70f0ad08106435bb3bcac4bf737f458/observation.json':'2d55a1ae77a5886787926b307aaad1d2e76c33c2d167a7a1e72e6738bdec0f04',
        'out/guest-installd-alias/20261106T040812300982Z-271fd9053e2c4d8983463e6e76a43a76/receipt.json':'e81fd1dc1e04d6ac78a13b3303e229f360210c0c87550dbcd5e0d199881f34a5',
    }
    for p, pin in inputs.items():
        assert sha(ROOT/p) == pin
    bridge = json.loads((ROOT/'out/installed-oneos-code-profile/static/appdata-bridge-source.json').read_text(encoding='utf-8'))
    lines = {}
    for name, p in bridge['assets'].items():
        assert sha(ROOT/p['path']) == p['sha256']
        lines[name] = (ROOT/p['path']).read_text(encoding='utf-8').splitlines()
    script_edges = [('oneos_switch.sh',1418,'unshare -m'), ('guest_start.sh',12,'cd /data/local/tmp/oneos/rootfs'),
                    ('guest_start.sh',13,'mount --make-rprivate /'), ('guest_start.sh',14,'pivot_root . postinstall'),
                    ('guest_start.sh',17,'pivot_root . postinstall'), ('guest_start.sh',44,'umount -l /postinstall'),
                    ('guest_start.sh',71,'mount --make-shared /mnt'), ('guest_start.sh',78,'mount -t tmpfs tmpfs /data_mirror'),
                    ('guest_start.sh',81,'data_mirror/data_de/null/0'), ('guest_start.sh',82,'data_mirror/data_ce/null/0')]
    for name, line, token in script_edges:
        assert token in lines[name][line-1]
        checks.append({'script':name,'line':line,'contains':token})
    assert not any(re.search(r'(^|[\s;])chroot([\s;]|$)', line) for line in lines['guest_start.sh'] if not line.lstrip().startswith('#'))
    save(RAW/'script-edges.json',[{'script':name,'line':line,'text':lines[name][line-1]} for name,line,_ in script_edges])
    sequence = [
        {'order':1,'action':'Own one fresh child mount namespace; recursively privatize inherited mounts once before any new bind/group. Keep original host init/installd/SS namespaces and shared48 unrelated.', 'status':'requires real preparation owner'},
        {'order':2,'action':'Inside that already-private child, reopen/admit child-local staged-data, ColorOS-root and original Samsung runtime source handles before /data shadow. Parent-opened handles may pin different mount objects; do not infer usable child source capability from inode equality.', 'status':'requires actual namespace/mount/object identity'},
        {'order':3,'action':'Require an owned private ColorOS root mountpoint (existing admitted image mount or owned self-bind) so native mount(/,MS_SLAVE|MS_REC) addresses a mount root. Prepare private whole-data mount and explicit /data/data alias; create NEW guest-only shared data and mirror-base mounts from child-private sources. Bind peer aliases into held ColorOS root data/data_mirror targets.', 'status':'mechanism-supported; no mounts performed'},
        {'order':4,'action':'Verify two data/mirror peer members and absence of a host master/peer link BEFORE fork. Do not place the guest root itself in a host peer group.', 'status':'future actual mount-ID/propagation readback required'},
        {'order':5,'action':'Fork without CLONE_FS sharing. Native child keeps Samsung root/runtime; guest child fchdir to admitted ColorOS root, chroot(.), chdir(/), close outside-root handles except explicitly retained protocol/exec requirements, then enter owned startup tail.', 'status':'per-process-root mechanism; no chroot or launch performed'},
        {'order':6,'action':'Replace guest_start12-20 and40-49: no namespace-wide pivot/postinstall detach. Omit/reorder line13 before peer creation. Replace mirror tmpfs/reset78-85 with owned existing-peer verification/setup; never overwrite the installed peer after creation.', 'status':'source changes proposed only; frozen script unchanged'},
        {'order':7,'action':'Allow genuine ColorOS native namespace branches: default zygote unshares then recursiveSLAVE; zygote_c skips only unshare then follows sameSLAVE; app helper can unshare. Validate actual selected native/profile and downstream master relationships, preserving privacy mounts and errors.', 'status':'five captured original functions only; staged/loaded identity unproved'},
        {'order':8,'action':'Native mirror/user-volume submounts under its common-parent master can reach ColorOS peer and slave descendants. Keep real UUID/expand mappings, mount flags, FBE, permission/property/Binder/caller/native-drain owners explicit.', 'status':'kernel mechanism, not execution or full guest compatibility'},
        {'order':9,'action':'Stop accepted work and drain real native/guest/script/mirror consumers before topology teardown; use owned namespace/mount handles, not old global14 unmount or path/PID sweep.', 'status':'retirement owner still missing'},
    ]
    mechanism_refs = [
        {'url':'https://docs.kernel.org/filesystems/sharedsubtree.html','source':'Linux kernel documentation','checkedUtcDate':'2026-11-06','use':'new shared bind peers propagate submount events; slaves receive one way; private mounts do not'},
        {'url':'https://man7.org/linux/man-pages/man2/chroot.2.html','source':'upstream Linux man-pages project','checkedUtcDate':'2026-11-06','use':'calling-process root/cwd/FD semantics; no sandbox or automatic capability claim'},
        {'url':'https://man7.org/linux/man-pages/man2/pivot_root.2.html','source':'upstream Linux man-pages project','checkedUtcDate':'2026-11-06','use':'mount-namespace root transition can update other processes rooted at old root'},
    ]
    result = {'schema':'guest-common-namespace-proof/v1','status':'COMMON_PRIVATE_ANCESTOR_MECHANISM_FEASIBLE_WITH_OWNED_SOURCE_CHANGES',
              'selected':False,'kernelOrMountOperationExecuted':False,'oemExecuted':False,'deviceAccess':False,'launcherEmitted':False,
              'toolSha256':sha(Path(__file__)),'inputs':inputs,'nativeCapture':capture_proof,'captureSha256':CAPTURE_SHA,
              'rawSha256':RAW_SHA,'scriptEdges':{'path':'firmware/guest-common-namespace-proof/script-edges.json','sha256':sha(RAW/'script-edges.json')},
              'checks':checks,'checkCount':len(checks),'sequence':sequence,'primaryMechanismReferences':mechanism_refs,
              'sourceDisposition':'Current script cannot be reused unchanged in common namespace; pivot and late-private/mirror replacement are mutable source choices, not inherent native prohibitions.',
              'propagationContract':{'host':'original namespaces/peer groups untouched; actual isolation unobserved',
                                     'commonParent':'fresh private-from-host namespace; new shared data/mirror twin aliases',
                                     'native':'Samsung-root child retains master peers',
                                     'guest':'independent fs_struct via fork and process chroot; original native zygote may create slave descendants',
                                     'mustNotDo':['run pivot_root in common namespace','make-rprivate over guest mirror peers after creation','replace guest alias with fresh unrelated tmpfs','assume same backing directories propagate mount events','force service_name to bypass source branch']},
              'installdScope':'No direct isolation/root/syscall/svc edges in selected main/start and no explicit isolation imports. Generic syscall elsewhere, library/loader constructors and every later method remain outside this negative proof.',
              'remaining':['actual original-vs-staged libandroid_runtime and full native cohort admission','authored FD/private-preparation owner with real child-local mount/source/root handles','actual kernel/SELinux/capability and same-object propagation readback','real UUID/expand/user/FBE/projectquota objects and unowned consumers','separate property/Binder/device/native policy and asynchronous retirement'],
              'handoffToBuild':'Prepare source-only FD transaction owner around sequence1-6 only after root gate; no device launch, ready booleans or shared API modifications implied.'}
    save(ROOT/'inventory/guest-common-namespace-proof.json',result)
    save(OUT/'audit-receipt.json',{'status':result['status'],'checkCount':len(checks),'functions':5,'instructions':5304,
                                  'inventorySha256':sha(ROOT/'inventory/guest-common-namespace-proof.json'),'toolSha256':result['toolSha256'],
                                  'oemOrKernelExecuted':False,'launcherEmitted':False})
    print(json.dumps({'status':result['status'],'checks':len(checks),'functions':5,'instructions':5304,'oemOrKernelExecuted':False},indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--capture',action='store_true')
    mode.add_argument('--audit',action='store_true')
    args = parser.parse_args()
    capture() if args.capture else audit()
