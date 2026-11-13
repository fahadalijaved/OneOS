"""Prepare a fresh, default-off app overlay with the reviewed fixed-FD corrections.

Data-only source composition. No patch subprocess, compiler, shell, network,
native execution, installation or mutation of the held clone/old overlay.
The new native build is packaged only through the existing v2 opt-in; this does
not integrate the separate writer guard or add an app VIEW_PREPARE operation.
"""
from pathlib import Path
import argparse
import base64
import difflib
import hashlib
import json
import re
import stat

ROOT = Path(__file__).absolute().parents[1]
DEST = ROOT / 'firmware/retained-view-app'
OLD = 'firmware/handoff-app-integration/'
CLONE = 'firmware/oneos-pr/OneOS/'
CORE = 'app-android/core/root/src/main/kotlin/com/fahadali/oneos/core/root/'
FULL = 'app-android/app/src/full/'
JAVA = FULL + 'java/com/fahadali/oneos/core/root/'
NORMAL = 'compat/android/com/fahadali/oneos/core/root/'
APP = 'compat/handoff-app/com/fahadali/oneos/core/root/'
PREP = OLD + 'receipt.json'
PREP_SHA = 'ecd44cdf79b4d735e6b17d7eff873afa23d3a685123a4db0795d797bae1696a5'
FD_REVIEW = 'out/root-fd-review/trust/SOURCE-PASS.json'
FD_REVIEW_SHA = '76ec673eefbb030a9a053f0a60a2a6779d1f48117cc4957f7b5a99a8485b3c9f'
NATIVE_RECEIPT = 'out/retained-root-view-build/r-8ecb3ffb/receipt.json'
NATIVE_RECEIPT_SHA = '2b1504c74123b9f8392025d2b790316f49e3710a4936106fc677d9ea7cc14571'
NATIVE_PATH = 'out/retained-root-view-build/r-8ecb3ffb/oneos_retained_root_view'
NATIVE_SHA = 'ba532858bfbe2aae07db41e88953bfe68519d0e12d40be916ba324bd4d342c89'
NATIVE_BYTES = 659336
OLD_NATIVE_SHA = '8dbc9f488daf8ab6422a788d5c67b16e35c4a6d7c4e73ee604f644c4a26c4831'
PATCHES = [
    ('compat/handoff-view/root-image-fd.patch',
     '3cbb489584cd95a5835ca8ee72bde909fffb98bb7c5262ea5bf336670e2e25d2'),
    ('compat/handoff-view/root-installer-fd.patch',
     '814747af7d1e346444cdd114e736769ef25f1cea7fe3417b8b3e98b73a7df8cc'),
]
PREIMAGES = {
    NORMAL + 'RetainedRootCommand.java': '4dafb8144d3205b539cb514cba8372d4de00a14febc9fcfa3492dc38ad041190',
    APP + 'RetainedRootOfferCommand.java': '337a9c877d510db8b8c9d44cbef5f9d322b42e9d2e4a4f84650243b976c39a4c',
    CLONE + CORE + 'RootScript.kt': '49cf71f666be2fee18323b9803ccaff9e300e984c444622eb673bbbedc5ad64f',
    OLD + 'overlay/' + CORE + 'RootScript.kt': '8eeacd4b88b97d394137f2fc9ce72c5f1a68ce2e8b38e71d7140e116fd447d6a',
    'compat/app-integration/retained-controller-install.sh': '903a4d9728a95d3eacaf47f8a36f77e9214628e5aaa6af7755c04f8d490f17a2',
    CLONE + FULL + 'assets/root/oneos_root.sh': '7d2bedaf07e0a4716e40620160a9aa4c9f20c4dbc4b2f36d6e070474334c3c66',
    OLD + 'overlay/' + FULL + 'assets/root/oneos_root.sh': '204c9a3829eba11dfac539c2e80fe3a0a15c2c10c3709a0dcb4775624b0483fc',
}
PATCH_TARGETS = [
    {NORMAL + 'RetainedRootCommand.java', APP + 'RetainedRootOfferCommand.java',
     CLONE + CORE + 'RootScript.kt', OLD + 'overlay/' + CORE + 'RootScript.kt'},
    {'compat/app-integration/retained-controller-install.sh',
     CLONE + FULL + 'assets/root/oneos_root.sh',
     OLD + 'overlay/' + FULL + 'assets/root/oneos_root.sh',
     CLONE + CORE + 'RootScript.kt', OLD + 'overlay/' + CORE + 'RootScript.kt'},
]


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

    def read(name, expected=None, size=None):
        name = safe_name(name)
        if name not in raw:
            path = checked(ROOT / name)
            require(path.is_file(), 'Regular input')
            require(path.stat().st_size <= 2 * 1024 * 1024, 'Bounded input')
            raw[name] = path.read_bytes()
        data = raw[name]
        require(expected is None or sha(data) == expected, 'Input pin: ' + name)
        require(size is None or len(data) == size, 'Input size: ' + name)
        return data

    prep = json.loads(read(PREP, PREP_SHA))
    review = json.loads(read(FD_REVIEW, FD_REVIEW_SHA))
    native_receipt = json.loads(read(NATIVE_RECEIPT, NATIVE_RECEIPT_SHA))
    require(prep['schema'] == 'retained-handoff-app-source-preparation/v1' and
            prep['status'] == 'SOURCE_ONLY_NOT_BUILT' and
            len(prep['inputs']) == 12 and len(prep['outputs']) == 12, 'Saved ECD44 profile')
    require(review['status'] == 'SOURCE_PASS_FIXED_FD_EXPORT_PATCHES_ONLY', 'FD source review')
    require(native_receipt['status'] == 'PASS_ROOT_VIEW_COMPOSED_NATIVE_STATIC_AND_SDK_ONLY',
            'Actual native/SDK build status')
    require(native_receipt['artifact'] == {'path': NATIVE_PATH, 'sha256': NATIVE_SHA,
                                         'bytes': NATIVE_BYTES}, 'Actual native artifact identity')
    read(NATIVE_PATH, NATIVE_SHA, NATIVE_BYTES)  # retain only in memory, never emit ELF under firmware
    for record in prep['inputs']:
        read(record['path'], record['sha256'], record['bytes'])
    outputs = {}
    for record in prep['outputs']:
        name = safe_name(record['path'])
        require(name.startswith('overlay/'), 'Saved virtual output prefix')
        virtual = name[len('overlay/'):]
        require(virtual not in outputs, 'Unique saved virtual output')
        outputs[virtual] = read(OLD + name, record['sha256'], record['bytes'])
    require(len({n.casefold() for n in outputs}) == 12, 'Canonical unique output paths')
    read(OLD + safe_name(prep['patch']['path']), prep['patch']['sha256'], prep['patch']['bytes'])
    for virtual, edits in prep['inverseEdits'].items():
        restored = outputs[virtual]
        for edit in reversed(edits):
            old = base64.b64decode(edit['old'], validate=True)
            new = base64.b64decode(edit['new'], validate=True)
            require(new and restored.count(new) == 1, 'Saved inverse occurrence')
            restored = restored.replace(new, old, 1)
        original = (APP + 'RetainedRootHostServiceV2.java' if
                    virtual == JAVA + 'RetainedRootHostServiceV2.java' else CLONE + virtual)
        require(restored == read(original), 'Saved overlay exact inverse')

    originals = {name: read(name, expected) for name, expected in PREIMAGES.items()}
    composed = dict(originals)
    phases = []
    for (name, expected), targets in zip(PATCHES, PATCH_TARGETS):
        patch = read(name, expected)
        before = {target: composed[target] for target in sorted(targets)}
        forward = apply_patch(patch, before)
        require(apply_patch(patch, forward, True) == before, 'Each phase exact inverse')
        composed.update(forward)
        phases.append({'patch': name, 'sha256': expected,
                       'before': {p: sha(b) for p, b in before.items()},
                       'after': {p: sha(b) for p, b in forward.items()}, 'inverseExact': True})
    # Independently invert the entire ordered composition, not only each local phase.
    restored = dict(composed)
    for (name, _), targets in reversed(list(zip(PATCHES, PATCH_TARGETS))):
        restored.update(apply_patch(raw[name], {p: restored[p] for p in targets}, True))
    require(restored == originals, 'Image-first/installer-second whole inverse')
    # The v2 Java command is exactly the source that entered the real SDK compile.
    compiled = native_receipt['compiledSourceInputs'][APP + 'RetainedRootOfferCommand.java']
    require(sha(composed[APP + 'RetainedRootOfferCommand.java']) == compiled['compiledSha256'],
            'Actual SDK v2 command correspondence')

    # Real app placement: v1 was already present in the held clone, v2 in ECD44.
    v1 = NORMAL + 'RetainedRootCommand.java'
    v2 = APP + 'RetainedRootOfferCommand.java'
    require(read(CLONE + JAVA + 'RetainedRootCommand.java') == originals[v1], 'Actual v1 app mirror')
    require(outputs[JAVA + 'RetainedRootOfferCommand.java'] == originals[v2], 'Actual v2 app mirror')
    before_outputs = dict(outputs)
    outputs[JAVA + 'RetainedRootCommand.java'] = composed[v1]
    outputs[JAVA + 'RetainedRootOfferCommand.java'] = composed[v2]
    outputs[CORE + 'RootScript.kt'] = composed[OLD + 'overlay/' + CORE + 'RootScript.kt']
    outputs[FULL + 'assets/root/oneos_root.sh'] = composed[OLD + 'overlay/' + FULL + 'assets/root/oneos_root.sh']
    # Existing opt-in only: fixed asset/installer/launch spelling, same v2 flag.
    gradle_name = 'app-android/app/build.gradle.kts'
    gradle = outputs[gradle_name]
    require(b'oneos.retainedHandoffFile' in gradle and b'oneos_retained_root_handoff' in gradle and
            b'if (retainedHandoffPath != null) retainedHandoffSha256 else ""' in gradle and
            b'if (retainedHandoffPath != null) retainedHandoffBytes else 0L' in gradle,
            'Actual default-off asset path required')
    require(b'--host-control-v2 3<&3' in composed[v2], 'Same fixed native entry only')
    old_sha = ('val retainedHandoffSha256 = "' + OLD_NATIVE_SHA + '"').encode()
    new_sha = ('val retainedHandoffSha256 = "' + NATIVE_SHA + '"').encode()
    old_size, new_size = b'val retainedHandoffBytes = 603416L', b'val retainedHandoffBytes = 659336L'
    require(gradle.count(old_sha) == 1 and gradle.count(old_size) == 1, 'Exact old native metadata')
    gradle = gradle.replace(old_sha, new_sha, 1).replace(old_size, new_size, 1)
    require(gradle.replace(new_size, old_size, 1).replace(new_sha, old_sha, 1) == outputs[gradle_name],
            'Native metadata exact inverse')
    outputs[gradle_name] = gradle
    require(len(outputs) == 13 and len({n.casefold() for n in outputs}) == 13,
            'Exact partial coexisting app overlay13')
    allowed_changed = {JAVA + 'RetainedRootOfferCommand.java', CORE + 'RootScript.kt',
                       FULL + 'assets/root/oneos_root.sh', gradle_name}
    require({n for n in before_outputs if before_outputs[n] != outputs[n]} == allowed_changed,
            'Only fixed FD and native metadata changes to ECD44')
    unchanged = [n for n in before_outputs if before_outputs[n] == outputs[n]]
    require(len(unchanged) == 8, 'Eight other saved overlay outputs unchanged')

    def stable():
        require(checked(__file__).read_bytes() == own, 'Producer moved')
        for name, data in raw.items():
            require(checked(ROOT / name).read_bytes() == data, 'Input moved: ' + name)

    stable()
    checked(DEST)
    require(not DEST.exists(), 'Fresh fixed destination only; no overwrite/retry')
    DEST.mkdir()
    print(json.dumps({'status': 'SOURCE_PREPARATION_STARTED', 'destination': str(DEST)}), flush=True)
    written = []

    def write(name, data):
        name = safe_name(name)
        path = checked(DEST / name)
        path.parent.mkdir(parents=True, exist_ok=True)
        checked(path)
        with path.open('xb') as file:
            require(file.write(data) == len(data), 'Complete owned write')
        require(checked(path).read_bytes() == data, 'Saved source readback')
        record = {'path': name, 'bytes': len(data), 'sha256': sha(data)}
        written.append(record)
        return record

    # Raw shell/Gradle source snapshots stay under ignored firmware. Native ELF
    # remains only at its existing out/ path; its exact receipt is retained here.
    snapshots = []
    for i, (name, data) in enumerate(sorted(raw.items())):
        if name == NATIVE_PATH:
            continue
        record = write('inputs/' + str(i) + '-' + Path(name).name, data)
        snapshots.append({'original': name, **record})
    write('executed-producer.py', own)
    output_records = [write('overlay/' + name, data) for name, data in sorted(outputs.items())]
    mirrors = [write('mirrors/' + name, composed[name]) for name in [v1, v2,
               'compat/app-integration/retained-controller-install.sh']]
    references = [write('v1-reference/' + name[len(CLONE):], composed[name]) for name in
                  [CLONE + CORE + 'RootScript.kt', CLONE + FULL + 'assets/root/oneos_root.sh']]
    # Save complete byte inverses for every changed output; no private method or
    # old producer execution is required to verify reversal later.
    inverses = []
    patch_text = []
    for name, value in sorted(outputs.items()):
        original = before_outputs.get(name, raw[CLONE + JAVA + 'RetainedRootCommand.java'])
        if original == value:
            continue
        inverse = write('inverse/' + name, original)
        inverses.append({'target': 'overlay/' + name, 'forwardSha256': sha(value),
                         'restored': inverse, 'fullOriginalByteInverse': True})
        patch_text.extend(difflib.unified_diff(original.decode().splitlines(True),
                                             value.decode().splitlines(True),
                                             fromfile='a/' + name, tofile='b/' + name))
    patch_record = write('integration.patch', ''.join(patch_text).encode())
    stable()
    # Reopen every saved path at final publication; an earlier write is not the
    # input to the final proof. Failed attempts remain intact, never repaired.
    for record in written:
        data = checked(DEST / record['path']).read_bytes()
        require(len(data) == record['bytes'] and sha(data) == record['sha256'], 'Final saved byte map')
    receipt = {
        'schema': 'retained-view-app-source-preparation/v1', 'status': 'SOURCE_ONLY_PARTIAL_APP_OVERLAY',
        'producerSha256': sha(own), 'oldPreparation': {'path': PREP, 'sha256': PREP_SHA},
        'sourceReview': {'path': FD_REVIEW, 'sha256': FD_REVIEW_SHA},
        'nativeBuildReceipt': {'path': NATIVE_RECEIPT, 'sha256': NATIVE_RECEIPT_SHA},
        'nativePins': {'path': NATIVE_PATH, 'sha256': NATIVE_SHA, 'bytes': NATIVE_BYTES,
                       'sourceProfile': 'API31/static PIE/4KiB; no runtime or 16KiB acceptance'},
        'inputs': [{'path': p, 'bytes': len(b), 'sha256': sha(b)} for p, b in sorted(raw.items())],
        'inputSnapshots': snapshots, 'outputs': output_records, 'mirrors': mirrors,
        'v1References': references, 'orderedPhases': phases, 'inverseOutputs': inverses,
        'wholeCompositionInverseExact': True, 'nativeMetadataInverseExact': True,
        'unchangedOldOverlayOutputs': unchanged, 'patch': patch_record, 'savedFiles': list(written),
        'defaultOff': True, 'existingPropertyOnly': 'oneos.retainedHandoffFile',
        'viewAppOperationAdded': False, 'writerGuardIntegrated': False,
        'hostViewSdkIntegratedIntoApp': False, 'cloneOrOldOverlayChanged': False,
        'executedTargets': [], 'limits': [
            'Source preparation only, not a full checkout/build/APK or runtime approval',
            'No actual writer guard, VIEW_PREPARE app route, prepared stage, guest exec or security admission',
            'New native build identity only; four-KiB source profile is not sixteen-KiB/runtime acceptance',
            'Fixed installer still refuses replacing a different existing image; no orphan reconciliation',
            'V1 command is source-composed, not newly SDK-compiled by this preparation',
        ],
    }
    stable()
    result = write('receipt.json', (json.dumps(receipt, indent=2) + '\n').encode())
    print(json.dumps({'status': receipt['status'], 'receipt': str(DEST / 'receipt.json'),
                      'sha256': result['sha256']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    if args.prepare:
        prepare()
    else:
        print(json.dumps({'status': 'PLAN_ONLY_NO_TOOLS', 'destination': str(DEST),
                          'defaultOff': True, 'viewOrWriterIntegration': False}))
