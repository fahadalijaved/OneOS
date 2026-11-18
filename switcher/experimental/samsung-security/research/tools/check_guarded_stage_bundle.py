"""Read back the selected saved APK/controller bundle. Never provisions a stage."""

import hashlib
import io
import json
from pathlib import Path, PureWindowsPath
import re
import struct
import zipfile
import zlib


ROOT = Path(__file__).resolve().parents[1]
BUILD = 'out/retained-root-view-guard-build/r-d86f158c'
MODULE = 'out/retained-guard-module-preparation/r-ea9310713eea'
WRITER = 'out/full-apk-build/guarded-writer/r-87e72aa0'
PROTOCOL = b'Lcom/fahadali/oneos/core/root/RetainedHostControlProtocol;'
CONFIG = b'Lcom/fahadali/oneos/BuildConfig;'
LEASE = '/dev/oneos-retained-view'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, expected, size=None):
    raw = (ROOT / path).read_bytes()
    require(sha(raw) == expected and (size is None or len(raw) == size), f'Pin changed: {path}')
    return raw


def artifact(record):
    return read(record['path'], record['sha256'], record['bytes'])


def receipt(path, expected):
    return json.loads(read(path, expected))


class Dex:
    """Selected ASCII descriptors and static constants in ordinary DEX039."""

    def __init__(self, raw):
        self.raw = raw
        require(raw[:8] == b'dex\n039\0' and self.u32(32) == len(raw)
                and self.u32(36) == 112 and self.u32(40) == 0x12345678, 'Wrong DEX framing')
        require(raw[12:32] == hashlib.sha1(raw[32:]).digest()
                and self.u32(8) == zlib.adler32(raw[12:]), 'Wrong DEX integrity')
        base, count = self.u32(100), self.u32(96)
        self.classes = {self.type_name(self.u32(pos)): pos for pos in range(base, base + 32 * count, 32)}
        require(len(self.classes) == count, 'Duplicate class in physical DEX')

    def u32(self, offset):
        return struct.unpack_from('<I', self.raw, offset)[0]

    def uleb(self, offset):
        value = 0
        for index in range(5):
            byte = self.raw[offset + index]
            value |= (byte & 0x7f) << (7 * index)
            if byte < 128 and (index < 4 or byte < 16):
                return value, offset + index + 1
        raise ValueError('Invalid ULEB128')

    def string(self, index):
        require(index < self.u32(56), 'String index outside DEX')
        _, start = self.uleb(self.u32(self.u32(60) + 4 * index))
        return self.raw[start:self.raw.index(0, start)]

    def type_name(self, index):
        require(index < self.u32(64), 'Type index outside DEX')
        return self.string(self.u32(self.u32(68) + 4 * index))

    def constants(self, class_name, selected):
        definition = self.classes[class_name]
        count, cursor = self.uleb(self.u32(definition + 24))
        for _ in range(3):
            _, cursor = self.uleb(cursor)
        fields, index = [], 0
        for _ in range(count):
            delta, cursor = self.uleb(cursor)
            flags, cursor = self.uleb(cursor)
            index += delta
            require(index < self.u32(80), 'Field index outside DEX')
            owner, _, name = struct.unpack_from('<HHI', self.raw, self.u32(84) + 8 * index)
            require(self.type_name(owner) == class_name and flags & 0x18 == 0x18,
                    'Expected static final field on selected class')
            fields.append(self.string(name).decode('ascii'))
        values = self.u32(definition + 28)
        count, cursor = self.uleb(values)
        require(values and count <= len(fields), 'Missing or excess static values')
        observed = {}
        for field in fields[:count]:
            tag = self.raw[cursor]
            kind, width = tag & 31, (tag >> 5) + 1
            cursor += 1
            if kind == 0x1f:
                require(width in (1, 2), 'Invalid boolean')
                value = width == 2
            elif kind == 0x1e:
                require(width == 1, 'Invalid null')
                value = None
            else:
                require(kind in (4, 6, 0x17) and width <= {4: 4, 6: 8, 0x17: 4}[kind],
                        'Unexpected selected-class value type')
                value = int.from_bytes(self.raw[cursor:cursor + width], 'little', signed=kind != 0x17)
                cursor += width
                if kind == 0x17 and field in selected:
                    value = self.string(value).decode('ascii')
            if field in selected:
                observed[field] = value
        require(observed == selected and all(type(observed[k]) is type(v) for k, v in selected.items()),
                f'Static constants differ: {class_name!r}')
        return observed


def main():
    sdk_hash = '6c67ec7388f1d64e5a82eeb4f17aa7a23880a9d15c3f3a26bc74a8017d841f0a'
    sdk = receipt(f'{BUILD}/receipt.json', sdk_hash)
    module = receipt(f'{MODULE}/receipt.json', 'b05b38e8e57006d348c8430e694b7215b346b035783c768da38c4d83f12a37e6')
    writer = receipt(f'{WRITER}/receipt.json', '5540b5b2de9b2389b76b33712adbddd2be38ae02a4eb6324b67d1c59be655fed')
    review = receipt('out/retained-guard-module-build-review/actual/ACTUAL-OUTPUT-CHECK.json',
                     'ab67f57676c439e5841c4bb12f574d84b439cc7eeb62c1743fd0f0f3682fdb58')
    require(review['apk']['sha256'] == module['apk']['sha256']
            and module['sdkReceipt'] == {'path': f'{BUILD}/receipt.json', 'sha256': sdk_hash}, 'Different SDK/module join')
    controller = artifact(sdk['artifact'])
    require(controller[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<HH', controller, 16) == (3, 183),
            'Controller is not the expected AArch64 ET_DYN')
    for literal in ('--host-control-v2', 'oneos.orh.', LEASE, 'writer-blocked', 'legacy-blocked',
                    'view-blocked', 'system.raw.id'):
        require(literal.encode() in controller, f'Controller literal absent: {literal}')

    kinds = ('INIT', 'NATIVE_OFFER', 'IDENTITY', 'PING', 'PONG', 'CLOSE', 'CLOSED', 'COMMIT', 'COMMITTED')
    base_protocol = dict(zip(kinds, range(1, 10)))
    base_protocol.update(VERSION=2, FRAME_BYTES=64, PAYLOAD_OFFSET=16, NAME_BYTES=42, REQUEST=0,
                         ADMISSION_CLOSED=1, LOCAL_CLOSED=2, REFUSED=3, BEGIN=1, OFFER=1, FAILED=2,
                         QUEUED=1, UNAVAILABLE=1, NATIVE_NAME_PREFIX='oneos.orh.',
                         BROKER='com.fahadali.oneos.IRetainedRootBroker.v2',
                         CALLBACK='com.fahadali.oneos.IRetainedRootHost.v2',
                         SERVICE_CLASS='com.fahadali.oneos.core.root.RetainedRootHostServiceV2')
    host_protocol = {**base_protocol, 'VIEW_PREPARE': 10, 'VIEW_STATE': 11, 'VIEW_QUERY': 12}
    source_pins = {PureWindowsPath(path).name: h for path, h in sdk['stagedSourcePins'].items()}
    header_name = 'retained_root_handoff.h'
    header = read(f'{BUILD}/native-src/{header_name}', source_pins[header_name]).decode('ascii')
    native_kinds = {key: int(value) for key, value in re.findall(r'\bORH_([A-Z_]+)=(\d+)\b', header)}
    for name in (*kinds, 'VIEW_PREPARE', 'VIEW_STATE', 'VIEW_QUERY', 'REQUEST', 'ADMISSION_CLOSED',
                 'LOCAL_CLOSED', 'REFUSED'):
        require(native_kinds['OFFER' if name == 'NATIVE_OFFER' else name] == host_protocol[name],
                f'Controller wire constant differs: {name}')
    for name in ('FRAME_BYTES', 'PAYLOAD_OFFSET', 'VERSION'):
        require(f'#define ORH_{name} {host_protocol[name]}U' in header, f'Controller wire macro differs: {name}')
    require(re.findall(r"#define ORH_MAGIC_\d '([A-Z])'", header) == list('ORSH'), 'Controller magic differs')
    gvo_name = 'guest_private_view_owner.c'
    gvo = read(f'{BUILD}/native-src/{gvo_name}', source_pins[gvo_name]).decode('ascii')
    role_match = re.search(r'enum \{ R_NAMESPACE=0,([^}]+)\};', gvo)
    roles = ['R_NAMESPACE', *role_match.group(1).strip().split(',')] if role_match else []
    require('#define GVO_RIGHTS 7' in gvo and '#define GVO_MAGIC UINT32_C(0x47564f33)' in gvo
            and roles == ['R_NAMESPACE', 'R_INHERITED_ROOT', 'R_GUEST_ROOT', 'R_DATA', 'R_MIRROR', 'R_DEV', 'R_SOCKET'],
            'Private GVO role layout differs')
    with zipfile.ZipFile(io.BytesIO(artifact(module['apk']))) as archive:
        require(archive.read('META-INF/xposed/scope.list') == b'android\n', 'Unexpected module scope')
        require(archive.read('META-INF/xposed/java_init.list') ==
                b'com.appleexploit.oneos.security.authority.RetainedPinHostModule\n', 'Unexpected module entry')
        dex = archive.read('classes.dex')
        require(sha(dex) == module['dex']['sha256'], 'Module DEX differs')
        parsed = Dex(dex)
        program = {('L' + name.removesuffix('.class') + ';').encode() for name in module['programClasses']}
        groups = sdk['logicalClassGroups']
        require(module['programClasses'] == groups['host'] | groups['sharedProtocol'], 'Module program origin differs')
        require(len(program) == 44 and parsed.classes.keys() == program, 'Module classes differ')
        parsed.constants(PROTOCOL, host_protocol)

    with zipfile.ZipFile(io.BytesIO(artifact(writer['apk']))) as archive:
        entry = 'assets/root/oneos_retained_root_handoff'
        require(archive.read(entry) == controller and 'assets/root/oneos_retained_root_session' not in archive.namelist(),
                'Writer APK did not select only the guarded controller')
        root_script = archive.read('assets/root/oneos_root.sh')
        script_list = archive.read('assets/oneos/sets/scripts.sha256')
        for literal in (LEASE, 'writer-blocked', 'legacy-blocked', 'view-blocked', '/proc/self/fd/3', '3<&-'):
            require(literal.encode() in root_script, f'Packaged root script literal absent: {literal}')
        expected = {'APPLICATION_ID': 'com.fahadali.oneos', 'VERSION_CODE': 75, 'RETAINED_WRITER_GUARD': True,
                    'ROOT_SCRIPT_BYTES': len(root_script), 'ROOT_SCRIPT_SHA256': sha(root_script),
                    'SCRIPTS_SHA256': sha(script_list), 'RETAINED_HANDOFF_BYTES': len(controller),
                    'RETAINED_HANDOFF_SHA256': sha(controller)}
        seen = {}
        for member in ('classes3.dex', 'classes7.dex', 'classes8.dex'):
            data = archive.read(member)
            expected_dex = writer['apk']['dex'][member]
            require(sha(data) == expected_dex['sha256'] and len(data) == expected_dex['bytes'], f'DEX changed: {member}')
            parsed = Dex(data)
            if member == 'classes3.dex':
                require(b'Lcom/fahadali/oneos/core/root/RootScript;' in parsed.classes, 'RootScript class absent')
                for literal in (LEASE, '8<&8', '3<&8 4<&4', 'writer-blocked', 'legacy-blocked'):
                    require(literal.encode() in data, f'Compiled RootScript DEX literal absent: {literal}')
            elif member == 'classes7.dex':
                seen['buildConfig'] = parsed.constants(CONFIG, expected)
            else:
                seen['appProtocol'] = parsed.constants(PROTOCOL, base_protocol)
                require(b'VIEW_PREPARE' not in data and b'--host-control-v2' in data,
                        'Unexpected app entry dialect')

    require(writer['certificate'] == '977baa3ee40b91fc658f9f16fab07dead12ec6ea0f909ff360ea2e2090c58639'
            and writer['inPlaceUpdateSupported'] is False and not writer['livePreparationVerified'],
            'Unexpected app provenance/runtime status')
    signature = writer['commands']['verify-signature']
    require(signature['exitCode'] == 0 and signature['ownedProcessReaped']
            and writer['certificate'].encode() in artifact(signature['stdout']), 'Saved writer signer result differs')
    print(json.dumps({'status': 'PASS_STATIC_BUNDLE_PINS_PROVISIONING_OPEN', 'writerApk': writer['apk']['sha256'],
                      'hostModuleApk': module['apk']['sha256'], 'controller': sdk['artifact'], **seen,
                      'hostProtocol': host_protocol, 'scope': 'Saved bytes only', 'nativeProtocolMagic': 'ORSH',
                      'privateGvoScmRightsRoles': roles, 'writerSigner': writer['certificate'],
                      'guardPath': LEASE, 'sharedLeaseObjectProvisioningProved': False,
                      'liveHostLinkProfileProved': False, 'liveAppPreparationProved': False}, indent=2))


if __name__ == '__main__':
    main()
