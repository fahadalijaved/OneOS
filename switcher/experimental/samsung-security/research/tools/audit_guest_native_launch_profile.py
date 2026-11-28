"""Static installd launch-profile evidence. Never execute OEM/native/phone code."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import tarfile
import struct

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
RAW = ROOT / 'firmware/guest-native-launch-profile/static'
OUT = ROOT / 'out/guest-native-launch-profile'
INDEX = PARENT / 'out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84/samsung-manifest.jsonl.gz'
INDEX_SHA = '6654252d9f7bde941e367fe79eb9af541869f4a1ddb5d1b8a0f0d4d6dde57a7a'
ARCHIVE = PARENT / 'firmware/samsung/os-mirror-20261104/mounted-os-20261104T235732022961Z.tar'
ARCHIVE_BYTES = 20434769920
INHERITED_ARCHIVE_SHA = '28eb27547fcc96348aa54f614a77aecd8bfcdbf875b61de2dd5279787985d96e'
MEMBERS = [
    'system/etc/selinux/plat_file_contexts',
    'system_ext/etc/selinux/system_ext_file_contexts',
    'vendor/etc/selinux/vendor_file_contexts',
    'product/etc/selinux/product_file_contexts',
    'odm/etc/selinux/odm_file_contexts',
    'system/etc/selinux/plat_service_contexts',
    'system_ext/etc/selinux/system_ext_service_contexts',
    'vendor/etc/selinux/vendor_service_contexts',
    'product/etc/selinux/product_service_contexts',
    'odm/etc/selinux/odm_service_contexts',
    'system/etc/selinux/plat_sepolicy.cil',
    'system/etc/passwd', 'system/etc/group',
    'system/etc/init/hw/init.rc',
]
ELF = ROOT / 'firmware/retained-installd-native-owner/20261106T024945006359Z-7b005bf1d2054ec4821a3e3ebdfdf978/installd'
ELF_SHA = 'ed618c386528c0b9890c67cbdcb22e1c194f44b034d8e36be2d7f2217fef7dfc'
RC = ROOT / 'firmware/retained-installd-native-owner/static/samsung-installd.rc'
RC_SHA = 'fcb59d1c3f8e49c5348d383805ca287b54c24d8f8fc3b70378078736676ed4a2'
NATIVE_RAW = ROOT / 'firmware/retained-installd-native-owner/static/selected-native.json'
NATIVE_RAW_SHA = '073ce4abb6ed496693e57a529b7a6e7c9d24d8785df7f20135db5ea79a02f776'
NATIVE_CAPTURE = ROOT / 'out/retained-installd-native-owner/static/capture.json'
NATIVE_CAPTURE_SHA = 'f2757c2e7ad01594e9e48e19371c27b38fd55e20883752b2b3ffe54ee8bd384c'
OWNER = ROOT / 'compat/native/guest_private_view_owner.c'
OWNER_SHA = '1026094b86171999544d957bcf120673cef5f4c66303e911f64c183cb3119f73'
OWNER_HEADER = ROOT / 'compat/native/guest_private_view_owner.h'
OWNER_HEADER_SHA = '463b79dbaa88ace7ea97f8775ac84faf436a535d4d79c165fc63ca20ee6d7daf'
INPUTS = ROOT / 'compat/native/guest_private_view_inputs.c'
INPUTS_SHA = '5e645e05e46fd8c5716572a26f9e90abf01b5871cbf60b95b71b883b093a7638'
INPUTS_HEADER = ROOT / 'compat/native/guest_private_view_inputs.h'
INPUTS_HEADER_SHA = '68a7b302c2f3b02479f8d89cc7dc4ecffc748243df395e67b6af55922ce3ef51'

def need(ok, label):
    if not ok:
        raise ValueError(label)

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

def index_rows():
    need(sha(INDEX) == INDEX_SHA, 'Immutable mounted index differs')
    result = {}
    with gzip.open(INDEX, 'rt', encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            need(row['path'] not in result, 'Duplicate indexed path')
            result[row['path']] = row
    return result

def raw_path(name):
    need(name in MEMBERS, 'Unselected member')
    return RAW / name.replace('/', '__')

def capture():
    rows = index_rows()
    need(ARCHIVE.stat().st_size == ARCHIVE_BYTES, 'Archive extent differs')
    before = ARCHIVE.stat()
    selected = {}
    with tarfile.open(ARCHIVE, 'r:') as archive:
        for count, member in enumerate(archive, 1):
            need(count <= 25000, 'Bounded tar header count')
            if member.name not in MEMBERS:
                continue
            need(member.name not in selected and member.isfile(), 'Unique regular selected member')
            row = rows[member.name]
            need(row['kind'] == 'file' and member.size == row['size'] and member.size <= 4 * 1024 * 1024, 'Selected member extent')
            need(member.offset_data + member.size <= ARCHIVE_BYTES, 'Selected archive extent')
            need((member.uid, member.gid, member.mode) == (row['metadata']['uid'], row['metadata']['gid'], row['metadata']['mode']), 'Member/index metadata')
            stream = archive.extractfile(member)
            need(stream is not None, 'Member payload')
            with stream:
                data = stream.read(member.size + 1)
            need(len(data) == member.size and hashlib.sha256(data).hexdigest() == row['sha256'], 'Member/index payload hash')
            target = raw_path(member.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                need(target.read_bytes() == data, 'Preserved selected raw differs')
            else:
                target.write_bytes(data)
            selected[member.name] = {'path': str(target.relative_to(ROOT)).replace('\\', '/'),
                'archiveHeaderOffset': member.offset, 'archiveDataOffset': member.offset_data,
                'bytes': len(data), 'sha256': row['sha256'], 'indexedMetadata': row['metadata']}
    need(set(selected) == set(MEMBERS), 'All fixed members present')
    after = ARCHIVE.stat()
    need((before.st_size, before.st_mtime_ns, before.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino), 'Archive moved during bounded reads')
    need(sha(INDEX) == INDEX_SHA, 'Index moved')
    save(OUT / 'capture.json', {'schema': 'guest-native-launch-profile-selected-source/v1',
        'status': 'STATIC_SELECTED_MEMBERS_COPIED_ONLY', 'members': selected,
        'indexSha256': INDEX_SHA, 'archiveBytes': ARCHIVE_BYTES,
        'archiveWholeSha256InheritedNotRecomputed': INHERITED_ARCHIVE_SHA,
        'headerRecordsVisited': count, 'selectedPayloadBytes': sum(r['bytes'] for r in selected.values()),
        'oemExecuted': False, 'phoneActions': []})
    print(json.dumps({'status': 'STATIC_CAPTURE_ONLY', 'members': len(selected), 'captureSha256': sha(OUT / 'capture.json')}))

def elf_profile(data):
    need(data[:7] == b'\x7fELF\x02\x01\x01', 'Original ELF64 LE')
    kind, machine = struct.unpack_from('<HH', data, 16)
    need(kind == 3 and machine == 183, 'Original AArch64 ET_DYN')
    phoff = struct.unpack_from('<Q', data, 32)[0]
    entsize, count = struct.unpack_from('<HH', data, 54)
    need(entsize == 56 and 0 < count <= 64 and phoff + count * entsize <= len(data), 'ELF program bounds')
    ph = [struct.unpack_from('<IIQQQQQQ', data, phoff + i * entsize) for i in range(count)]
    def at(va, size):
        matches = [p for p in ph if p[0] == 1 and p[3] <= va and va + size <= p[3] + p[5]]
        need(len(matches) == 1, 'Unique file-backed VA range')
        p = matches[0]
        start = p[2] + va - p[3]
        need(start + size <= len(data), 'ELF file range')
        return data[start:start + size]
    interpreters = [p for p in ph if p[0] == 3]
    need(len(interpreters) == 1 and interpreters[0][5] <= 256, 'Original interpreter')
    p = interpreters[0]
    interp = data[p[2]:p[2] + p[5]]
    need(interp.endswith(b'\0') and b'\0' not in interp[:-1], 'Interpreter framing')
    dynamic = [p for p in ph if p[0] == 2]
    need(len(dynamic) == 1 and dynamic[0][5] % 16 == 0, 'Dynamic table')
    p = dynamic[0]
    tags = []
    for off in range(p[2], p[2] + p[5], 16):
        tag, value = struct.unpack_from('<qQ', data, off)
        if tag == 0:
            break
        tags.append((tag, value))
    else:
        raise ValueError('Unterminated dynamic table')
    vals = dict(tags)
    strings = at(vals[5], vals[10])
    def string(index):
        need(index < len(strings), 'Dynamic string index')
        end = strings.find(b'\0', index)
        need(end >= 0, 'Dynamic string terminator')
        return strings[index:end].decode('utf-8')
    return {'ptInterp': interp[:-1].decode(), 'needed': [string(v) for k, v in tags if k == 1],
            'rpath': [string(v) for k, v in tags if k == 15],
            'runpath': [string(v) for k, v in tags if k == 29]}, at

def audit():
    reader_sha = sha(Path(__file__))
    rows = index_rows()
    source_pins = {str(p.relative_to(ROOT)): expected for p, expected in (
        (ELF, ELF_SHA), (RC, RC_SHA), (NATIVE_RAW, NATIVE_RAW_SHA),
        (NATIVE_CAPTURE, NATIVE_CAPTURE_SHA), (OWNER, OWNER_SHA), (OWNER_HEADER, OWNER_HEADER_SHA),
        (INPUTS, INPUTS_SHA), (INPUTS_HEADER, INPUTS_HEADER_SHA))}
    for n, expected in source_pins.items():
        need(sha(ROOT / n) == expected, 'Selected source identity: ' + n)
    captured = json.loads((OUT / 'capture.json').read_text())
    need(set(captured['members']) == set(MEMBERS), 'Fourteen selected source members')
    for n in MEMBERS:
        p = raw_path(n)
        need(p.stat().st_size == rows[n]['size'] and sha(p) == rows[n]['sha256'], 'Captured member/index identity')
    checks = []
    def check(ok, label):
        need(ok, label)
        checks.append(label)
    rc = RC.read_text().splitlines()
    init_rc = raw_path('system/etc/init/hw/init.rc').read_text().splitlines()
    check(init_rc.count('import /init.environ.rc') == 1, 'Captured primary init imports root environment source outside selected OS roots')
    start = rc.index('service installd /system/bin/installd')
    options = []
    for line in rc[start + 1:]:
        if line and not line[0].isspace():
            break
        if line.strip():
            options.append(line.strip().split())
    caps = 'CHOWN DAC_OVERRIDE DAC_READ_SEARCH FOWNER FSETID KILL SETGID SETUID SYS_ADMIN'.split()
    check(options == [['class', 'main'], ['user', 'root'], ['capabilities', *caps]], 'Exact installd service argv and only three options')
    check(rows['system/bin/installd']['sha256'] == ELF_SHA and rows['system/etc/init/installd.rc']['sha256'] == RC_SHA, 'Observed executable and rc match mounted index')
    check(rows['system/bin/installd']['normalizedMetadata'] == {'uid': 0, 'gid': 2000, 'modeBits': 493}, 'Executable uid0 gid2000 mode0755 is file metadata')
    context_hits = {}
    for n in MEMBERS:
        if n.endswith('_contexts'):
            context_hits[n] = [{'line': i, 'text': line} for i, line in enumerate(raw_path(n).read_text().splitlines(), 1)
                               if 'installd' in line or 'nstalld' in line]
    fc = raw_path('system/etc/selinux/plat_file_contexts').read_text().splitlines()
    sc = raw_path('system/etc/selinux/plat_service_contexts').read_text().splitlines()
    check(any(line.split() == ['/system/bin/installd', 'u:object_r:installd_exec:s0'] for line in fc), 'Captured expected exec file label')
    check(any(line.split() == ['installd', 'u:object_r:installd_service:s0'] for line in sc), 'Captured canonical service label')
    alias = []
    for n in MEMBERS:
        if n.endswith('service_contexts'):
            alias.extend(line for line in raw_path(n).read_text().splitlines() if line.split() and line.split()[0] == 'nstalld')
    check(not alias, 'No exact nstalld entry in five captured service-context tables; live policy unproved')
    cil = raw_path('system/etc/selinux/plat_sepolicy.cil').read_text().splitlines()
    required = ['(typetransition init installd_exec process installd)',
                '(allow init installd_exec (file (read getattr map execute open)))',
                '(allow init installd (process (transition)))',
                '(allow installd installd_service (service_manager (add find)))']
    policy = []
    for text in required:
        check(cil.count(text) == 1, 'Captured unique policy rule: ' + text)
        policy.append({'line': cil.index(text) + 1, 'text': text})
    binary = ELF.read_bytes()
    loader, at = elf_profile(binary)
    check(loader['ptInterp'] == '/system/bin/linker64', 'Original PT_INTERP')
    check(rows['system/bin/linker64']['kind'] == 'symlink' and rows['system/bin/linker64']['linkTarget'] == '/apex/com.android.runtime/bin/linker64', 'Captured runtime interpreter symlink')
    check(rows['apex/com.android.runtime/bin/linker64']['sha256'] == '8ec70ab6a3175a9cf5ac6ea5e7f18dfd3d9771f9a734f7ab7ebb71455bd225c1', 'Original runtime interpreter object')
    prior = json.loads(NATIVE_CAPTURE.read_text())
    check(sorted(loader['needed']) == sorted(prior['needed']) and len(loader['needed']) == 21, 'Original21 needed libraries independently read')
    raw = json.loads(NATIVE_RAW.read_text())
    funcs = {f['symbol']: f for f in raw['functions']}
    selected = ['main', '_ZN7android8installd31init_globals_from_data_and_rootEv', '_ZN7android8installd21InstalldNativeService5startEv']
    instructions = {}
    for symbol in selected:
        f = funcs[symbol]
        check(hashlib.sha256(binary[f['fileOffset']:f['fileOffset'] + f['bytes']]).hexdigest() == f['sha256'], 'Reused complete function identity: ' + symbol)
        instructions.update({i['pc']: i for i in f['instructions']})
    def ins(pc, field, expected):
        i = instructions[pc]
        check(i[field] == expected, 'Saved instruction ' + hex(pc) + ' ' + field)
        need(at(pc, 4) == bytes.fromhex(i['bytes']), 'Actual instruction bytes')
    env = []
    for name, literal_pc, getter_pc in [('ANDROID_DATA', 476096, 476100), ('ANDROID_ROOT', 476116, 476120), ('ASEC_MOUNTPOINT', 477536, 477548)]:
        ins(literal_pc, 'literal', name)
        ins(getter_pc, 'targetSymbol', 'getenv')
        i = instructions[literal_pc]
        check(at(i['literalAddress'], len(name) + 1) == name.encode() + b'\0', 'Original environment name bytes: ' + name)
        env.append({'name': name, 'literalPc': hex(literal_pc), 'getenvPc': hex(getter_pc)})
    ins(477552, 'mnemonic', 'mov')
    ins(477552, 'operands', 'x19, x0')
    ins(477556, 'targetSymbol', 'strlen')
    ins(569488, 'targetSymbol', '_ZN7android8installd21InstalldNativeService5startEv')
    ins(156580, 'targetSymbol', '_ZN7android12ProcessState15startThreadPoolEv')
    ins(156648, 'targetSymbol', '_ZN7android4base15GetBoolPropertyERKNSt3__112basic_stringIcNS1_11char_traitsIcEENS1_9allocatorIcEEEEb')
    ins(156216, 'literal', 'installd')
    ins(156484, 'operands', 'x8, [x8, #0x30]')
    ins(156488, 'mnemonic', 'blr')
    ins(156488, 'operands', 'x8')
    ins(569504, 'targetSymbol', '_ZN7android14IPCThreadState14joinThreadPoolEb')
    check('getuid()!=0 || geteuid()!=0' in INPUTS.read_text(), 'Current provider root guard is not exec-profile setup')
    library_candidates = {name: [{'path': n, 'sha256': row['sha256']} for n, row in rows.items()
                        if row['kind'] == 'file' and n.rsplit('/', 1)[-1] == name and '/lib64/' in n]
                        for name in loader['needed']}
    references = ['docs/retained-installd-native-owner.md', 'inventory/retained-installd-native-owner.json',
                  'docs/retained-installd-routing.md', 'docs/guest-common-namespace-proof.md',
                  'docs/guest-installd-alias.md', 'docs/guest-installd-alias-review.md']
    result = {'schema': 'guest-native-launch-profile/v1', 'status': 'SOURCE_CONTRACT_ONLY_NO_LAUNCH',
        'selected': False, 'sourcePins': source_pins, 'readerSha256': reader_sha,
        'referencePins': {n: sha(ROOT / n) for n in references},
        'mountedIndex': {'path': str(INDEX.relative_to(PARENT)), 'sha256': INDEX_SHA},
        'capture': {'path': str((OUT / 'capture.json').relative_to(ROOT)), 'sha256': sha(OUT / 'capture.json')},
        'archiveWholeHashInheritedNotRecomputed': INHERITED_ARCHIVE_SHA,
        'checks': checks, 'checkCount': len(checks),
        'initService': {'name': 'installd', 'argv': ['/system/bin/installd'], 'class': ['main'],
            'userToken': 'root', 'capabilities': caps, 'explicitGroup': None, 'explicitSeclabel': None,
            'explicitSetenv': [], 'explicitSocketOrFile': [], 'activeInitDefaultsOrProcessProfileProved': False},
        'execIndexedMetadata': rows['system/bin/installd']['normalizedMetadata'],
        'actualExecSelinuxXattrOrFileCapsProved': False,
        'capturedContextHits': context_hits, 'capturedPolicyRules': policy,
        'loader': loader, 'interpreterIndexRecords': {n: rows[n] for n in ('system/bin/linker64', 'apex/com.android.runtime/bin/linker64')},
        'libraryFilenameCandidatesNotResolvedOwners': library_candidates,
        'runtimeLinkerConfigurationCaptured': any(n.startswith('linkerconfig/') for n in rows),
        'requiredSelectedEnvironmentReads': env,
        'publisher': {'sourceName': 'installd', 'nameLiteralPc': '0x26238',
            'managerIndirectCallPc': '0x26348', 'managerSlot': '0x30',
            'sourceW3': 0, 'sourceW4': 8, 'actualRuntimeManagerOrPublicationAttested': False,
            'threadPoolStartPc': '0x263a4', 'cachedPropertyReadPc': '0x263e8',
            'cachedPropertyStorePc': '0x263f8', 'mainJoinPc': '0x8b0a0'},
        'asecGetenvImmediatelyFeedsStrlenNoInterveningGuard': True,
        'initEnvironRcPathPresentInIndex': any(n.endswith('init.environ.rc') for n in rows),
        'capturedPrimaryInitEnvironmentImport': {'path': 'system/etc/init/hw/init.rc', 'line': init_rc.index('import /init.environ.rc') + 1, 'target': '/init.environ.rc', 'targetContentsSelected': False},
        'currentAuthoredOwnerExportsExecOrLauncher': False,
        'originalEffectiveGidGroupsCapsDomainEnvironmentObserved': False,
        'mechanismReferenceNotSamsungRevision': 'https://raw.githubusercontent.com/aosp-mirror/platform_system_core/android-16.0.0_r1/init/README.md',
        'minimumFutureLaunchInputs': [
            'Actual retained private-view owner child and intended Samsung root/cwd/FD provenance, not a raw PID namespace selector',
            'Reviewed original exec object ed618 or separately selected alias511; real executable inode label/capability metadata and original interpreter/runtime cohort',
            'Real preexec credential/capability/SELinux setup from source-owned original or explicitly supported OneOS profile producer; rc root token alone is insufficient',
            'Genuine ANDROID_DATA, ANDROID_ROOT and ASEC_MOUNTPOINT producer values; no selected values/defaults supplied by this card',
            'Exact original native publisher and service policy route, with accepted operations/native startup/property acknowledgement and actual retirement/reap ownership',
        ],
        'originalAndStagedNativeProfilesEquivalentProved': False,
        'alias511PublisherPrototypeIsLauncher': False,
        'nativeOrDaemonExecuted': False, 'phoneActions': [],
        'limits': ['Captured source policy/config is not loaded live policy, process caps/groups/domain, inode labels or resolved libraries',
                   'Root user and copied ELF bytes do not establish original init exec transition or service label ownership',
                   'ASEC/ANDROID environment values require a genuine selected producer, not invented defaults',
                   'Profile must be owned before exec; selected main/start does not close interpreter/library constructors or transitive initialization',
                   'Current gvo/gvi custody APIs have no original-daemon exec/publication operation; no raw PID launch seam is admitted',
                   'No new enforcing/stock-equivalence/global-policy condition; required real functional owners remain unassembled']}
    for n, expected in source_pins.items():
        need(sha(ROOT / n) == expected, 'Source moved during audit')
    need(sha(INDEX) == INDEX_SHA, 'Index moved during audit')
    for n in MEMBERS:
        need(sha(raw_path(n)) == rows[n]['sha256'], 'Selected raw moved during audit')
    need(sha(Path(__file__)) == reader_sha, 'Reader moved during audit')
    result['sourceIndexRawAndReaderPinsVerifiedBeforeAfter'] = True
    save(OUT / 'report.json', result)
    save(ROOT / 'inventory/guest-native-launch-profile.json', result)
    print(json.dumps({'status': result['status'], 'checks': len(checks), 'needed': len(loader['needed']), 'inventorySha256': sha(ROOT / 'inventory/guest-native-launch-profile.json')}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--capture', action='store_true', help='Read only fourteen fixed regular members from existing PC tar')
    mode.add_argument('--audit', action='store_true', help='Check saved static inputs; no OEM or native execution')
    args = parser.parse_args()
    if args.capture:
        capture()
    else:
        audit()
