"""Prepare an explicit local-debug download-metadata app overlay; execute no tools.

All default/release/packSets payload checks remain. This opt-in renders genuine
current set lists, source IDs and official declared sizes without fake payloads.
Official metadata is not proof that payload bytes were downloaded or verified.
"""
from pathlib import Path
import argparse
import base64
import hashlib
import json
import re
import stat

ROOT = Path(__file__).absolute().parents[1]
DEST = ROOT / 'firmware/debug-download-app'
BASE = 'firmware/retained-view-app/'
BASE_RECEIPT = BASE + 'receipt.json'
BASE_SHA = 'ac18addc37c2c9348fad157b216f27eba302b3c5e952af95624e5bbce259c49b'
BASE_GRADLE_SHA = '9d0e85baf0b001b8160c0837e107cf48a59a8f612ac50c452e63e187d9d39b14'
PROOF = 'out/full-apk-remote-set-metadata-check.json'
PROOF_SHA = '417f051d89dd24770612291fcab0d8a111a6398a2612278f4ccbf77b213e1db2'
RAW_API = 'firmware/full-apk-release-metadata/oneos-files-sets-1.json'
RAW_SHA = '0f7c3e548678df8a598a6d2ef5d4e01bb37469e6a4220b876f82324e3ac5a730'
PATCH = 'compat/app-integration/debug-download-metadata.patch'
PATCH_SHA = '34b7f7f2126c275a98e1d6116e140aacafac22d6d9582b72efefd20ceef48eee'
MANIFEST = 'app-android/packages/debug-download-assets.tsv'
MANIFEST_SHA = 'ae4f9703e8756f2e20452fcfa13199e1e59526fecd0dcc5b74ac36db075c7f16'
GRADLE = 'app-android/app/build.gradle.kts'
SET_IDS = ['n6-f8u','x9u-in-sultra','pixel-f8u','pixel-sultra','pixel-f8','pixel9-sultra','infinityx','hyper-f8u','nothing-f8u']
LIMIT = 268435456
GUARD_SOURCE = 'firmware/debug-download-app/receipt.json'
GUARD_SOURCE_SHA = '9038e670261cf106e540f8883eeb88c457859f107e5dc1cccaccd0b125390ea0'
GUARD_BUILD = 'out/retained-root-view-guard-build/r-d86f158c/receipt.json'
GUARD_BUILD_SHA = '6c67ec7388f1d64e5a82eeb4f17aa7a23880a9d15c3f3a26bc74a8017d841f0a'
GUARD_IMAGE = {
    'path': 'out/retained-root-view-guard-build/r-d86f158c/oneos_retained_root_view_guard',
    'sha256': '4fb54644c1f97a64e76f057ba69e787aa28de5f9d5f9a9c696873f673f35afaa',
    'bytes': 663592,
}
RES_SOURCE = 'firmware/debug-download-guard-app/receipt.json'
RES_SOURCE_SHA = 'c06164ab0f8e3531f587d9eaa2415fe9f55a860e82939eed19cf761619fabd13'
RES_PATCH = 'compat/app-integration/enable-app-resvalues.patch'
RES_PATCH_SHA = '41713f836e9e149514c7cfe24c5c0e256c26e8144cef0f45e3c7f2c227e9b941'

def require(value, message):
    if not value:
        raise ValueError(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def checked(path):
    path = Path(path).absolute()
    path.relative_to(ROOT)
    current = ROOT
    for part in (None,) + path.relative_to(ROOT).parts:
        if part is not None:
            current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(info.st_mode) and
                not getattr(info, 'st_file_attributes', 0) & 0x400,
                'Reparse path refused: ' + str(current))
    require(path.resolve(strict=False) == path, 'Canonical path differs')
    return path

def safe_name(name):
    require(isinstance(name, str), 'String path required')
    name = name.replace('\\', '/')
    p = Path(name)
    require(name and not p.is_absolute() and ':' not in name and
            '..' not in p.parts and '.' not in p.parts, 'Relative path only')
    return p.as_posix()

def apply_patch(patch, sources, inverse=False):
    """Strict count/position/context patch; preserve each input's LF/CRLF bytes."""
    require(len(patch) <= 128 * 1024 and patch.endswith(b'\n'), 'Patch bound')
    patch = patch.replace(b'\r\n', b'\n')
    require(b'\r' not in patch, 'Patch line terminators')
    lines = patch.splitlines(keepends=True)
    i = 0
    outputs = {}
    while i < len(lines):
        require(lines[i].startswith(b'--- a/'), 'Old patch header')
        target = safe_name(lines[i][6:-1].decode('ascii'))
        i += 1
        require(i < len(lines) and lines[i] == b'+++ b/' + target.encode() + b'\n',
                'New patch header')
        i += 1
        require(target in sources and target not in outputs, 'Unique admitted target')
        original = sources[target]
        crlf = b'\r\n' in original
        require(original.endswith(b'\n') and
                (not crlf or original.count(b'\r\n') == original.count(b'\n')),
                'Homogeneous source line endings')
        normalized = original.replace(b'\r\n', b'\n') if crlf else original
        require(b'\r' not in normalized, 'Source carriage return')
        before = normalized.splitlines(keepends=True)
        out = []
        cursor = hunks = 0
        while i < len(lines) and not lines[i].startswith(b'--- a/'):
            match = re.fullmatch(rb'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n', lines[i])
            require(match is not None, 'Exact hunk header')
            i += 1
            a, ac, b, bc = int(match[1]), int(match[2] or b'1'), int(match[3]), int(match[4] or b'1')
            if inverse:
                a, ac, b, bc = b, bc, a, ac
            position = a - 1 if ac else a
            new_position = b - 1 if bc else b
            require(cursor <= position <= len(before), 'Ordered bounded hunks')
            out.extend(before[cursor:position])
            cursor = position
            require(len(out) == new_position, 'Exact new hunk position')
            used = added = 0
            while i < len(lines) and not lines[i].startswith((b'@@ ', b'--- a/')):
                line = lines[i]
                i += 1
                kind, payload = line[:1], line[1:]
                require(kind in (b' ', b'-', b'+') and payload.endswith(b'\n'),
                        'Exact hunk data')
                if inverse:
                    kind = b'+' if kind == b'-' else b'-' if kind == b'+' else kind
                if kind != b'+':
                    require(cursor < len(before) and before[cursor] == payload,
                            'Exact hunk context/removal: ' + target)
                    cursor += 1
                    used += 1
                if kind != b'-':
                    out.append(payload)
                    added += 1
            require(used == ac and added == bc, 'Exact hunk counts')
            hunks += 1
        require(hunks, 'Nonempty patch target')
        out.extend(before[cursor:])
        data = b''.join(out)
        outputs[target] = data.replace(b'\n', b'\r\n') if crlf else data
    require(set(outputs) == set(sources), 'Complete selected patch coverage')
    return outputs

def prepare():
    own = checked(__file__).read_bytes()
    raw = {}

    def read(name, expected, size=None):
        name = safe_name(name)
        if name not in raw:
            path = checked(ROOT / name)
            require(path.is_file() and 0 < path.stat().st_size <= 2 * 1024 * 1024, 'Bounded regular input')
            raw[name] = path.read_bytes()
        value = raw[name]
        require(sha(value) == expected and (size is None or len(value) == size), 'Exact input pin: ' + name)
        return value

    base = json.loads(read(BASE_RECEIPT, BASE_SHA))
    proof = json.loads(read(PROOF, PROOF_SHA))
    api = json.loads(read(RAW_API, RAW_SHA, 676256))
    patch = read(PATCH, PATCH_SHA)
    require(base['schema'] == 'retained-view-app-source-preparation/v1' and
            base['status'] == 'SOURCE_ONLY_PARTIAL_APP_OVERLAY' and len(base['outputs']) == 13,
            'Actual ac18 partial app source profile')
    require(base['defaultOff'] and not base['viewAppOperationAdded'] and not base['writerGuardIntegrated'],
            'Preserve existing native default-off and partial runtime scope')
    outputs = {}
    for row in base['outputs']:
        name = safe_name(row['path'])
        require(name.startswith('overlay/'), 'Exact saved overlay path')
        virtual = name[len('overlay/'):]
        require(virtual not in outputs, 'Unique overlay source')
        outputs[virtual] = read(BASE + name, row['sha256'], row['bytes'])
    require(len({n.casefold() for n in outputs}) == 13 and sha(outputs[GRADLE]) == BASE_GRADLE_SHA,
            'Complete exact base overlay')
    require(proof['status'] == 'COMPLETE_OFFICIAL_METADATA_AVAILABLE_FOR_CURRENT_NINE_SETS_NOT_PAYLOAD_VERIFIED',
            'Independent official metadata source profile')
    require(proof['source']['rawResponse'] == {'path': RAW_API, 'bytes': 676256, 'sha256': RAW_SHA},
            'Same official response provenance')
    require(api['id'] == 434754944 and api['tag_name'] == 'sets-1' and
            not api['draft'] and not api['prerelease'] and len(api['assets']) == 413,
            'Exact official release')
    require([row['set'] for row in proof['currentHeldManifests']] == SET_IDS,
            'All nine current source sets')
    required = set()
    references = {}
    set_maps = {}
    set_outputs = {}
    for row in proof['currentHeldManifests']:
        record = row['file']
        require(record['path'] == 'firmware/oneos-pr/OneOS/app-android/packages/' + row['set'] + '.sha256',
                'Fixed current package mapping')
        data = read(record['path'], record['sha256'], record['bytes'])
        want = {}
        for line in data.decode('utf-8').splitlines():
            if not line.strip() or line.startswith('#'):
                continue
            match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_][A-Za-z0-9._+\-]*)', line)
            require(match is not None and match[2] not in want, 'Unique strict package row')
            want[match[2]] = match[1]
            required.add(match[1])
            references.setdefault(match[1], []).append((row['set'], match[2]))
        require(want and len(want) == row['entryCount'], 'Actual nonempty package list')
        rendered = ''.join(want[name] + '  ' + name + '\n' for name in sorted(want)).encode()
        require(sha(rendered) == row['canonicalNameHashMapSha256'], 'Canonical runtime list hash')
        set_maps[row['set']] = want
        set_outputs[row['set']] = {'sha256': sha(rendered), 'bytes': len(rendered), 'entries': len(want)}
    require(len(required) == 242 and sum(map(len, set_maps.values())) == 329, 'Complete current source mapping')
    remote_record = proof['currentRemoteManifest']
    require(remote_record['path'] == 'firmware/oneos-pr/OneOS/app-android/packages/remote.txt', 'Fixed remote source')
    remote_bytes = read(remote_record['path'], remote_record['sha256'], remote_record['bytes'])
    remotes = {}
    source = r'(gh:[a-z0-9][a-z0-9.-]{0,39}|[A-Za-z0-9_-]{20,80})'
    for line in remote_bytes.decode('utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([0-9a-f]{64}) (' + source + '(,' + source + '){0,15})', line)
        require(match is not None and match[1] not in remotes, 'Unique genuine remote source row')
        require('gh:sets-1' in match[2].split(','), 'Official release source in current runtime mapping')
        remotes[match[1]] = match[2]
    require(set(remotes) == required, 'Exact current remote hash set')
    accepted = proof['acceptedAssetMetadata']
    require(len(accepted) == 242, 'Complete accepted release metadata')
    sizes = {}
    seen_ids = set()
    for row in accepted:
        digest = row['expectedSha256']
        require(digest in required and digest not in sizes and re.fullmatch('[0-9a-f]{64}', digest),
                'Unique required official asset digest')
        matches = [asset for asset in api['assets'] if asset['name'] == digest]
        require(len(matches) == 1, 'Unique official source asset name')
        asset = matches[0]
        size = asset['size']
        url = 'https://github.com/fahadalijaved/OneOS-files/releases/download/sets-1/' + digest
        require(type(size) is int and 1 <= size <= LIMIT and asset['state'] == 'uploaded' and
                asset['digest'] == 'sha256:' + digest and asset['browser_download_url'] == url and
                asset['id'] not in seen_ids, 'Genuine bounded uploaded asset metadata')
        require(row['name'] == digest and row['digest'] == asset['digest'] and row['state'] == 'uploaded' and
                row['size'] == size and row['assetId'] == asset['id'] and row['publicUrl'] == url and
                row['releaseId'] == api['id'] and row['tag'] == 'sets-1', 'Exact independently joined row')
        require(sorted((ref['set'], ref['name']) for ref in row['referencedBy']) == sorted(references[digest]),
                'Exact source filename/set membership')
        sizes[digest] = size
        seen_ids.add(asset['id'])
    require(set(sizes) == required, 'No missing or extraneous metadata')
    manifest = ''.join(digest + '\t' + str(sizes[digest]) + '\n' for digest in sorted(sizes)).encode()
    require(len(manifest) == 17659 and sha(manifest) == MANIFEST_SHA, 'Exact fixed 242-row manifest')
    original = outputs[GRADLE]
    forward = apply_patch(patch, {GRADLE: original})[GRADLE]
    require(apply_patch(patch, {GRADLE: forward}, True)[GRADLE] == original and
            apply_patch(patch, {GRADLE: original})[GRADLE] == forward, 'Exact source inverse/reapply')
    # The original payload loop and actual script generation remain verbatim.
    start = original.index(b'        for ((id, spec) in sets.get()) {')
    end = original.index(b'        val scriptSums =', start)
    require(original[start:end] in forward, 'Original default payload loop retained')
    tail_end = original.index(b'\nval oneosFiles =', end)
    require(original[end:tail_end] in forward, 'Original script hashing/copy/index checks retained')
    require(MANIFEST_SHA.encode() in forward and all(row['file']['sha256'].encode() in forward
            for row in proof['currentHeldManifests']) and remote_record['sha256'].encode() in forward,
            'Prepared task binds exact manifest/list/remote source hashes')
    outputs[GRADLE] = forward
    require(MANIFEST not in outputs, 'No manifest collision')
    outputs[MANIFEST] = manifest
    require(len(outputs) == 14 and len({n.casefold() for n in outputs}) == 14, 'Complete isolated overlay14')

    def stable():
        require(checked(__file__).read_bytes() == own, 'Producer moved')
        for name, value in raw.items():
            require(checked(ROOT / name).read_bytes() == value, 'Input changed: ' + name)

    stable()
    checked(DEST)
    require(not DEST.exists(), 'Fresh fixed output only; never overwrite')
    DEST.mkdir()
    saved = []

    def write(name, data):
        name = safe_name(name)
        path = checked(DEST / name)
        path.parent.mkdir(parents=True, exist_ok=True)
        checked(path)
        with path.open('xb') as file:
            require(file.write(data) == len(data), 'Complete exclusive write')
        require(checked(path).read_bytes() == data, 'Source readback')
        row = {'path': name, 'bytes': len(data), 'sha256': sha(data)}
        saved.append(row)
        return row

    snapshots = []
    for i, (name, data) in enumerate(sorted(raw.items())):
        row = write('inputs/' + str(i) + '-' + Path(name).name, data)
        snapshots.append({'original': name, **row})
    write('executed-producer.py', own)
    written_outputs = [write('overlay/' + name, value) for name, value in sorted(outputs.items())]
    inverse = write('inverse/app-android/app/build.gradle.kts', original)
    stable()
    for row in saved:
        value = checked(DEST / row['path']).read_bytes()
        require(len(value) == row['bytes'] and sha(value) == row['sha256'], 'Final output map')
    result = {
        'schema': 'debug-download-app-source-preparation/v1', 'status': 'SOURCE_ONLY_DEBUG_DOWNLOAD_METADATA_OPTION',
        'producerSha256': sha(own), 'baseReceipt': {'path': BASE_RECEIPT, 'sha256': BASE_SHA},
        'officialJoinProof': {'path': PROOF, 'sha256': PROOF_SHA},
        'officialRawResponse': {'path': RAW_API, 'sha256': RAW_SHA},
        'patch': {'path': PATCH, 'sha256': PATCH_SHA},
        'inputs': [{'path': name, 'bytes': len(data), 'sha256': sha(data)} for name, data in sorted(raw.items())],
        'inputSnapshots': snapshots, 'outputs': written_outputs,
        'manifest': {'path': 'overlay/' + MANIFEST, 'sha256': MANIFEST_SHA, 'bytes': len(manifest), 'rows': 242},
        'inverse': inverse, 'sourceInverseAndReapplyExact': True,
        'unchangedBaseOverlayFiles': [name for name in sorted(outputs) if name not in (GRADLE, MANIFEST)],
        'expectedPerSetOutputs': set_outputs, 'genuineRemoteSources': remotes,
        'officialDeclaredSizes': sizes, 'entryOccurrences': 329, 'uniqueHashes': 242,
        'explicitProperty': 'oneos.debugDownloadMetadata=true', 'fixedManifestRelativeToProject': 'packages/debug-download-assets.tsv',
        'releaseAllowedWithProperty': False, 'packSetsTrueAllowedWithProperty': False,
        'seriesOrPackageOverrideAllowedWithProperty': False,
        'defaultTaskPayloadChecksPreserved': True, 'actualScriptsStillHashedAndPackaged': True,
        'nativePins': base['nativePins'], 'nativeDefaultOff': True,
        'viewRouteOrWriterGuardAdded': False, 'savedFiles': list(saved), 'executedTargets': [],
        'limits': ['Official digest/name/size metadata is not downloaded payload digest verification',
                   'Local debug download-only packaging option; not Release/package-set payload admission',
                   'No APK, Gradle, helper, native, original/runtime, network, installation or phone execution'],
    }
    stable()
    record = write('receipt.json', (json.dumps(result, indent=2) + '\n').encode())
    print(json.dumps({'status': result['status'], 'receipt': str(DEST / 'receipt.json'), 'sha256': record['sha256']}), flush=True)


def prepare_guard():
    """Retarget controller identity and NIO symbol names only; no writer patches."""
    destination = ROOT / 'firmware/debug-download-guard-app'
    own = checked(__file__).read_bytes()
    raw = {}

    def read(name, expected, size=None):
        name = safe_name(name)
        if name not in raw:
            path = checked(ROOT / name)
            require(path.is_file() and 0 < path.stat().st_size <= 2 * 1024 * 1024,
                    'Bounded regular guard packaging input')
            raw[name] = path.read_bytes()
        value = raw[name]
        require(sha(value) == expected and (size is None or len(value) == size),
                'Exact guard packaging input: ' + name)
        return value

    base = json.loads(read(GUARD_SOURCE, GUARD_SOURCE_SHA))
    build = json.loads(read(GUARD_BUILD, GUARD_BUILD_SHA))
    require(base['schema'] == 'debug-download-app-source-preparation/v1' and
            base['status'] == 'SOURCE_ONLY_DEBUG_DOWNLOAD_METADATA_OPTION' and len(base['outputs']) == 14,
            'Actual reviewed fourteen-file source overlay')
    require(base['manifest']['sha256'] == MANIFEST_SHA and base['manifest']['rows'] == 242 and
            base['explicitProperty'] == 'oneos.debugDownloadMetadata=true' and base['nativeDefaultOff'] and
            not base['viewRouteOrWriterGuardAdded'], 'Keep metadata and default-off runtime profile')
    require(build['schema'] == 'retained-root-guard-view-source-build/v2' and
            build['status'] == 'PASS_ROOT_GUARD_VIEW_COMPOSED_NATIVE_STATIC_AND_SDK_ONLY' and
            build['artifact'] == GUARD_IMAGE and build['nativeTarget'] == 'aarch64-linux-android31',
            'Actual fresh guard-controller native/SDK build')
    require(not build['runtimeReadinessAccepted'] and not build['runtimeOrSixteenKiBAccepted'] and
            not build['literalReceiptModelTransfer'], 'Do not transfer runtime or model acceptance')
    read(GUARD_IMAGE['path'], GUARD_IMAGE['sha256'], GUARD_IMAGE['bytes'])
    outputs = {}
    for row in base['outputs']:
        name = safe_name(row['path'])
        require(name.startswith('overlay/'), 'Saved guard overlay path')
        virtual = name[len('overlay/'):]
        require(virtual not in outputs, 'Unique guard overlay source')
        outputs[virtual] = read('firmware/debug-download-app/' + name, row['sha256'], row['bytes'])
    require(len({n.casefold() for n in outputs}) == 14 and sha(outputs[MANIFEST]) == MANIFEST_SHA,
            'Exact fourteen-file base and TSV bytes')
    app = 'app-android/app/src/full/java/com/fahadali/oneos/core/root/'
    command_key = 'compat/handoff-app/com/fahadali/oneos/core/root/RetainedRootOfferCommand.java'
    protocol_key = 'compat/handoff-shared/com/fahadali/oneos/core/root/RetainedHostControlProtocol.java'
    command = build['compiledSourceInputs'][command_key]
    command_bytes = read(command['stagedPath'], command['compiledSha256'])
    require(command_bytes == outputs[app + 'RetainedRootOfferCommand.java'] and
            b'--host-control-v2 3<&3' in command_bytes, 'Same actual compiled app command and entry')
    protocol = build['compiledSourceInputs'][protocol_key]
    protocol_bytes = read(protocol['stagedPath'], protocol['compiledSha256'])
    existing = outputs[app + 'RetainedHostControlProtocol.java'].decode().splitlines()
    actual = {line.strip() for line in protocol_bytes.decode().splitlines()}
    require(all(line.strip() in actual for line in existing if line.strip().startswith('public static final ')),
            'Existing app protocol constants remain the compiled SDK schema')
    original = outputs[GRADLE]
    previous = base['nativePins']
    require(previous['sha256'] == 'ba532858bfbe2aae07db41e88953bfe68519d0e12d40be916ba324bd4d342c89' and
            previous['bytes'] == 659336, 'Fixed prior controller identity')
    edits = [
        (('val retainedHandoffSha256 = "' + previous['sha256'] + '"').encode(),
         ('val retainedHandoffSha256 = "' + GUARD_IMAGE['sha256'] + '"').encode()),
        (b'val retainedHandoffBytes = 659336L', b'val retainedHandoffBytes = 663592L'),
    ]
    forward = original
    for old, new in edits:
        require(forward.count(old) == 1, 'Unique native identity literal')
        forward = forward.replace(old, new, 1)
    # Gradle's `java` accessor shadows qualified java.nio references in Kotlin
    # DSL. Fix symbol resolution only, after the exact native identity retarget.
    aliases = [
        ('java.nio.file.Files', 'OneOsNioFiles', 7),
        ('java.nio.file.LinkOption', 'OneOsNioLinkOption', 1),
        ('java.nio.file.attribute.BasicFileAttributes', 'OneOsNioAttributes', 2),
        ('java.nio.channels.FileChannel', 'OneOsNioChannel', 1),
        ('java.nio.file.StandardOpenOption', 'OneOsNioOpenOption', 1),
        ('java.nio.ByteBuffer', 'OneOsNioBuffer', 2),
    ]
    for qualified, alias, count in aliases:
        require(forward.count(qualified.encode()) == count and alias.encode() not in original,
                'Exact NIO reference count and fresh import alias')
        forward = forward.replace(qualified.encode(), alias.encode())
    newline = b'\r\n' if b'\r\n' in original else b'\n'
    imports = newline.join(('import ' + qualified + ' as ' + alias).encode()
                           for qualified, alias, _ in aliases) + newline
    require(original.startswith(b'import java.security.MessageDigest'), 'Original import preimage')
    forward = imports + forward
    inverse = forward
    require(inverse.startswith(imports) and inverse.count(imports) == 1, 'Exact NIO alias import block')
    inverse = inverse[len(imports):]
    for qualified, alias, count in reversed(aliases):
        require(inverse.count(alias.encode()) == count, 'Exact inverse NIO symbol count')
        inverse = inverse.replace(alias.encode(), qualified.encode())
    for old, new in reversed(edits):
        require(inverse.count(new) == 1, 'Unique inverse native identity literal')
        inverse = inverse.replace(new, old, 1)
    require(inverse == original, 'Only two native literals and compile-safe NIO aliases')
    outputs[GRADLE] = forward

    def stable():
        require(checked(__file__).read_bytes() == own, 'Guard producer moved')
        for name, value in raw.items():
            require(checked(ROOT / name).read_bytes() == value, 'Guard input changed: ' + name)

    stable()
    checked(destination)
    require(not destination.exists(), 'Fresh guard packaging output; no overwrite')
    destination.mkdir()
    saved = []

    def write(name, data):
        name = safe_name(name)
        path = checked(destination / name)
        path.parent.mkdir(parents=True, exist_ok=True)
        checked(path)
        with path.open('xb') as file:
            require(file.write(data) == len(data), 'Complete exclusive guard source write')
        require(checked(path).read_bytes() == data, 'Saved guard source readback')
        row = {'path': name, 'bytes': len(data), 'sha256': sha(data)}
        saved.append(row)
        return row

    snapshots = []
    for i, (name, value) in enumerate(sorted(raw.items())):
        if name == GUARD_IMAGE['path']:
            continue  # Generated ELF remains only at its original ignored out/ path.
        row = write('inputs/' + str(i) + '-' + Path(name).name, value)
        snapshots.append({'original': name, **row})
    write('executed-producer.py', own)
    written = [write('overlay/' + name, value) for name, value in sorted(outputs.items())]
    original_record = write('inverse/app-android/app/build.gradle.kts', original)
    stable()
    for row in saved:
        value = checked(destination / row['path']).read_bytes()
        require(len(value) == row['bytes'] and sha(value) == row['sha256'], 'Final guard packaging output')
    result = {
        'schema': 'debug-download-guard-app-source-preparation/v1',
        'status': 'SOURCE_ONLY_GUARD_CONTROLLER_METADATA_RETARGET', 'producerSha256': sha(own),
        'baseReceipt': {'path': GUARD_SOURCE, 'sha256': GUARD_SOURCE_SHA},
        'nativeBuildReceipt': {'path': GUARD_BUILD, 'sha256': GUARD_BUILD_SHA},
        'nativePins': dict(GUARD_IMAGE), 'nativeDefaultOff': True,
        'inputs': [{'path': p, 'bytes': len(v), 'sha256': sha(v)} for p, v in sorted(raw.items())],
        'inputSnapshots': snapshots, 'outputs': written, 'inverse': original_record,
        'edits': [{'old': base64.b64encode(a).decode(), 'new': base64.b64encode(b).decode()} for a, b in edits],
        'nioAliasFix': [{'qualified': q, 'alias': a, 'referenceCount': n} for q, a, n in aliases],
        'nioAliasImportBytes': base64.b64encode(imports).decode(),
        'fullNativeAndAliasInverseExact': True,
        'nativeLiteralInverseExact': True, 'changedBaseFiles': [GRADLE],
        'unchangedBaseFiles': [name for name in sorted(outputs) if name != GRADLE],
        'manifest': base['manifest'], 'explicitProperty': base['explicitProperty'],
        'appCommandsAndExistingProtocolConstantsMatchActualSdk': True,
        'writerPatchOrViewRouteAdded': False, 'runtimeReadinessOrModelAcceptanceTransferred': False,
        'savedFiles': list(saved), 'executedTargets': [],
        'limits': ['Compiled control prototype packaging only; no full APK/runtime/security acceptance',
                   'Old stock writers cohort and actual guard preprovision remain external',
                   'No app VIEW route or writer patch, no native ELF copied under firmware',
                   'API31/4KiB build profile does not establish 16KiB or runtime support',
                   'Original 242-row metadata/default task/explicit debug flag preserved unchanged'],
    }
    stable()
    record = write('receipt.json', (json.dumps(result, indent=2) + '\n').encode())
    print(json.dumps({'status': result['status'], 'receipt': str(destination / 'receipt.json'),
                      'sha256': record['sha256']}), flush=True)


def prepare_res_values():
    """Enable the existing module's resource generation; preserve all values."""
    destination = ROOT / 'firmware/debug-download-resvalues-app'
    own = checked(__file__).read_bytes()
    raw = {}

    def read(name, expected, size=None):
        name = safe_name(name)
        if name not in raw:
            path = checked(ROOT / name)
            require(path.is_file() and 0 < path.stat().st_size <= 2 * 1024 * 1024, 'Bounded module input')
            raw[name] = path.read_bytes()
        value = raw[name]
        require(sha(value) == expected and (size is None or len(value) == size), 'Exact module source pin')
        return value

    base = json.loads(read(RES_SOURCE, RES_SOURCE_SHA))
    patch = read(RES_PATCH, RES_PATCH_SHA)
    require(base['schema'] == 'debug-download-guard-app-source-preparation/v1' and
            base['status'] == 'SOURCE_ONLY_GUARD_CONTROLLER_METADATA_RETARGET' and
            len(base['outputs']) == 14 and base['fullNativeAndAliasInverseExact'] and
            base['nativeDefaultOff'] and not base['writerPatchOrViewRouteAdded'], 'Exact c061 source cohort')
    outputs = {}
    for row in base['outputs']:
        name = safe_name(row['path'])
        require(name.startswith('overlay/'), 'Saved module overlay prefix')
        virtual = name[len('overlay/'):]
        require(virtual not in outputs, 'Unique module output')
        outputs[virtual] = read('firmware/debug-download-guard-app/' + name, row['sha256'], row['bytes'])
    require(len({p.casefold() for p in outputs}) == 14 and sha(outputs[MANIFEST]) == MANIFEST_SHA,
            'Preserve complete metadata overlay')
    original = outputs[GRADLE]
    require(sha(original) == '37a2465a4c071859abb3f5ddc8db7ac0f8a3fc1684f662dcd9a7a640d1a38fbb',
            'Exact compiled-stage2 Gradle preimage')
    forward = apply_patch(patch, {GRADLE: original})[GRADLE]
    require(apply_patch(patch, {GRADLE: forward}, True)[GRADLE] == original, 'Full module inverse')
    newline = b'\r\n' if b'\r\n' in original else b'\n'
    insertion = b'        resValues = true' + newline
    require(insertion not in original and forward.count(insertion) == 1 and
            forward.replace(insertion, b'', 1) == original, 'Only resValues=true line added')
    declarations = lambda value: [line for line in value.splitlines() if b'resValue(' in line]
    require(declarations(original) and declarations(original) == declarations(forward), 'Preserve all custom values')
    require(b'        buildConfig = true' in forward, 'Keep BuildConfig generation')
    outputs[GRADLE] = forward

    def stable():
        require(checked(__file__).read_bytes() == own, 'Module producer moved')
        for name, value in raw.items():
            require(checked(ROOT / name).read_bytes() == value, 'Module input changed')

    stable()
    checked(destination)
    require(not destination.exists(), 'Fresh module-fix destination only')
    destination.mkdir()
    saved = []

    def write(name, value):
        name = safe_name(name)
        path = checked(destination / name)
        path.parent.mkdir(parents=True, exist_ok=True)
        checked(path)
        with path.open('xb') as file:
            require(file.write(value) == len(value), 'Complete exclusive module write')
        require(checked(path).read_bytes() == value, 'Saved module source readback')
        row = {'path': name, 'bytes': len(value), 'sha256': sha(value)}
        saved.append(row)
        return row

    snapshots = []
    for i, (name, value) in enumerate(sorted(raw.items())):
        row = write('inputs/' + str(i) + '-' + Path(name).name, value)
        snapshots.append({'original': name, **row})
    write('executed-producer.py', own)
    written = [write('overlay/' + name, value) for name, value in sorted(outputs.items())]
    inverse = write('inverse/app-android/app/build.gradle.kts', original)
    stable()
    for row in saved:
        value = checked(destination / row['path']).read_bytes()
        require(len(value) == row['bytes'] and sha(value) == row['sha256'], 'Final module source map')
    result = {
        'schema': 'debug-download-resvalues-app-source-preparation/v1',
        'status': 'SOURCE_ONLY_MODULE_RESVALUES_ENABLED', 'producerSha256': sha(own),
        'baseReceipt': {'path': RES_SOURCE, 'sha256': RES_SOURCE_SHA},
        'patch': {'path': RES_PATCH, 'sha256': RES_PATCH_SHA},
        'inputs': [{'path': p, 'bytes': len(v), 'sha256': sha(v)} for p, v in sorted(raw.items())],
        'inputSnapshots': snapshots, 'outputs': written, 'inverse': inverse,
        'singleResValuesLineOnly': True, 'fullOriginalInverseExact': True,
        'existingCustomResourceValuesPreserved': True, 'buildConfigTruePreserved': True,
        'changedBaseFiles': [GRADLE], 'unchangedBaseFiles': [p for p in sorted(outputs) if p != GRADLE],
        'nativePins': base['nativePins'], 'nativeBuildReceipt': base['nativeBuildReceipt'],
        'manifest': base['manifest'], 'explicitProperty': base['explicitProperty'],
        'nativeDefaultOff': True, 'writerPatchOrViewRouteAdded': False,
        'savedFiles': list(saved), 'executedTargets': [],
        'limits': ['Module resource generation fix only, not APK/build/runtime acceptance',
                   'All metadata, native, Release/packSets and no-view constraints preserved'],
    }
    stable()
    row = write('receipt.json', (json.dumps(result, indent=2) + '\n').encode())
    print(json.dumps({'status': result['status'], 'receipt': str(destination / 'receipt.json'),
                      'sha256': row['sha256']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--prepare-guard', action='store_true')
    mode.add_argument('--prepare-res-values', action='store_true')
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.prepare_guard:
        prepare_guard()
    elif args.prepare_res_values:
        prepare_res_values()
    else:
        print(json.dumps({'status': 'PLAN_ONLY_NO_TOOLS', 'destination': str(DEST),
                          'debugOptionDefaultsOff': True, 'payloadsFetchedOrVerified': False}))
