#!/usr/bin/env python3
"""Prepare an isolated, default-off full-flavor v2 source overlay; execute no code.

This uses exact held source bytes, writes only firmware/handoff-app-integration,
and emits inverse-checked edits plus a patch. It never builds, installs, launches,
downloads or modifies the input checkout. Native pins are build identity only.
"""
import argparse
import base64
import difflib
import hashlib
import json
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLONE = 'firmware/oneos-pr/OneOS/'
DEST = ROOT / 'firmware/handoff-app-integration'
CORE = 'app-android/core/root/src/main/kotlin/com/fahadali/oneos/core/root/'
FULL = 'app-android/app/src/full/'
SESSION = FULL + 'kotlin/com/fahadali/oneos/session/'
JAVA = FULL + 'java/com/fahadali/oneos/core/root/'
APP = 'compat/handoff-app/com/fahadali/oneos/core/root/'
SHARED = 'compat/handoff-shared/com/fahadali/oneos/core/root/'
PINS = {
    CLONE + CORE + 'RootScript.kt': '49cf71f666be2fee18323b9803ccaff9e300e984c444622eb673bbbedc5ad64f',
    CLONE + CORE + 'RootShell.kt': '2b1ca549f99eefe756711da8e657081fb381148c4ccf77920457c001a89c1ea0',
    CLONE + SESSION + 'RootVerbs.kt': 'a070ac5b29e948ce043e6389f6f7b97f5d11f985f421ea16efa71ffd8836070d',
    CLONE + 'app-android/app/build.gradle.kts': '68421d566f9e2541ed1b33bb5f792dc938520621eed3cf6538e86a18669ed08c',
    CLONE + FULL + 'AndroidManifest.xml': 'b5ea3d36f1680ff0fb0ad900d6a9972a6b3e25c1afaa7fef7cadffc92d783cb3',
    CLONE + FULL + 'assets/root/oneos_root.sh': '7d2bedaf07e0a4716e40620160a9aa4c9f20c4dbc4b2f36d6e070474334c3c66',
    APP + 'RetainedRootHostServiceV2.java': '6e7f527c57781805b63eacb7f849637c14caed8f13caba02d3f7fa29e0f05380',
    APP + 'RetainedRootOfferLaunch.java': '3b45a03d12cd77c4bc4b0cac35defad3f4d89f18b33be48d17b48a66b3afa386',
    APP + 'RetainedRootOfferSpawn.java': '3fc1c4cb6b3614419253ff536c77eed87d39cdb3dda036f4d29ebf8ad33362f0',
    APP + 'RetainedRootOfferCommand.java': '337a9c877d510db8b8c9d44cbef5f9d322b42e9d2e4a4f84650243b976c39a4c',
    SHARED + 'RetainedHostControlProtocol.java': 'f7b587f52ba6aa7ec04985c4e8c6186b839d5e00d98bbd9d53ae748b7e331611',
    'compat/handoff-app-integration/RetainedHandoffControllerSetup.kt': '067c31ddf490e33e891bff5290c990381cfd0d1acb0810b14486cfaed69e15d2',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_path(path):
    """Fixed repository output only; refuse existing symlink/reparse ancestors."""
    path.relative_to(ROOT)
    current = ROOT
    for piece in (None,) + path.relative_to(ROOT).parts:
        if piece is not None:
            current = current / piece
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Linked output ancestor refused: ' + str(current))
    if path.resolve(strict=False) != path:
        raise ValueError('Output canonical path differs')


def write_owned(path, value):
    checked_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    checked_path(path)
    with path.open('xb') as output:
        if output.write(value) != len(value):
            raise IOError('Short source output write')
    checked_path(path)
    actual = path.read_bytes()
    if actual != value:
        raise IOError('Reopened source output differs: ' + str(path))
    return {'path': str(path.relative_to(DEST)), 'bytes': len(actual), 'sha256': sha(actual)}


def prepare(native_sha='', native_bytes=0):
    if (native_sha or native_bytes) and (len(native_sha) != 64 or
            any(c not in '0123456789abcdef' for c in native_sha) or not 1 <= native_bytes <= 2097152):
        raise ValueError('Supply both a lowercase native SHA256 and size 1..2097152')
    sources = {}
    for path, expected in PINS.items():
        actual = (ROOT / path).read_bytes()
        if sha(actual) != expected:
            raise ValueError('Held input differs: ' + path)
        sources[path] = actual
    checked_path(DEST)
    if DEST.exists():
        raise FileExistsError('Use a fresh isolated output; existing candidate is never overwritten')
    # Fail before creating the output if any byte transform/anchor is unexpected.
    outputs, edits = {}, {}

    def change(path, transforms):
        original = sources[CLONE + path]
        value = original
        records = []
        for old, new in transforms:
            old, new = old.encode(), new.encode()
            if value.count(old) != 1:
                raise ValueError('Expected one source anchor in ' + path)
            value = value.replace(old, new, 1)
            records.append((old, new))
        inverse = value
        for old, new in reversed(records):
            if inverse.count(new) != 1:
                raise ValueError('Ambiguous inverse in ' + path)
            inverse = inverse.replace(new, old, 1)
        if inverse != original:
            raise ValueError('Inverse failed in ' + path)
        outputs[path] = value
        edits[path] = [{'old': base64.b64encode(a).decode(), 'new': base64.b64encode(b).decode()}
                       for a, b in records]

    script = sources[CLONE + CORE + 'RootScript.kt'].decode()
    nl = '\r\n' if '\r\n' in script else '\n'
    enum = '        INSTALL_CLOSED_CONTROLLER("install-closed-controller", Stdin.SCRIPT_DATA),'
    change(CORE + 'RootScript.kt', [
        (enum, enum + nl + '        INSTALL_HANDOFF_CONTROLLER("install-handoff-controller", Stdin.SCRIPT_DATA),'),
        ('Verb.INSTALL_CLOSED_CONTROLLER -> {', 'Verb.INSTALL_CLOSED_CONTROLLER, Verb.INSTALL_HANDOFF_CONTROLLER -> {'),
        ('if (verb == Verb.INSTALL_CLOSED_CONTROLLER) INSTALL_TEMPLATE',
         'if (verb == Verb.INSTALL_CLOSED_CONTROLLER || verb == Verb.INSTALL_HANDOFF_CONTROLLER) INSTALL_TEMPLATE'),
    ])
    change(SESSION + 'RootVerbs.kt', [
        ('val install = verb == RootScript.Verb.INSTALL_CLOSED_CONTROLLER',
         'val install = verb == RootScript.Verb.INSTALL_CLOSED_CONTROLLER ||' + nl +
         '            verb == RootScript.Verb.INSTALL_HANDOFF_CONTROLLER'),
        ('reply.ok == "closed-controller-installed" && reply.okCount == 1',
         'reply.ok == (if (verb == RootScript.Verb.INSTALL_HANDOFF_CONTROLLER)' + nl +
         '                            "closed-handoff-controller-installed" else "closed-controller-installed") && reply.okCount == 1'),
    ])
    # Identical RootShell retention policy; both installers use its retained path.
    outputs[CORE + 'RootShell.kt'] = sources[CLONE + CORE + 'RootShell.kt']
    shell = sources[CLONE + FULL + 'assets/root/oneos_root.sh'].decode()
    start = shell.index('do_install_closed_controller() (')
    end = shell.index('\n# --- Main ', start)
    original_handler = shell[start:end]
    handoff_handler = original_handler.replace('do_install_closed_controller', 'do_install_handoff_controller')
    handoff_handler = handoff_handler.replace('install-closed-controller', 'install-handoff-controller')
    handoff_handler = handoff_handler.replace('oneos_retained_root_session', 'oneos_retained_root_handoff')
    handoff_handler = handoff_handler.replace('.oneos-retained-controller-install', '.oneos-retained-handoff-install')
    handoff_handler = handoff_handler.replace('closed-controller-installed', 'closed-handoff-controller-installed')
    dispatch = '    install-closed-controller) do_install_closed_controller "$@" ;;'
    change(FULL + 'assets/root/oneos_root.sh', [
        (original_handler, original_handler + '\n' + handoff_handler),
        (dispatch, dispatch + '\n    install-handoff-controller) do_install_handoff_controller "$@" ;;'),
    ])
    # Reuse the bounded task as a distinct v2 task, preserving all v1 inputs.
    gradle = sources[CLONE + 'app-android/app/build.gradle.kts'].decode()
    gn = '\r\n' if '\r\n' in gradle else '\n'
    a = gradle.index('// Explicit local opt-in only.')
    b = gradle.index('// Release signing key:', a)
    original_pack = gradle[a:b]
    handoff_pack = original_pack.replace('RetainedController', 'RetainedHandoff').replace('retainedController', 'retainedHandoff')
    handoff_pack = handoff_pack.replace('retained-controller', 'retained-handoff').replace('oneos_retained_root_session', 'oneos_retained_root_handoff')
    handoff_pack = handoff_pack.replace('1cacc47717468c6e91b791126ce011af25dab9bdbde50765ec0a013cea2b116b', native_sha)
    handoff_pack = handoff_pack.replace('596312L', str(native_bytes) + 'L')
    # A property without generator-selected literal pins must refuse, not ship
    # an arbitrary locally named image. Absence keeps ordinary full/Probe builds.
    handoff_pack = handoff_pack.replace('val retainedHandoffAssets = retainedHandoffPath?.let { path ->',
        'val retainedHandoffAssets = retainedHandoffPath?.let { path ->' + gn +
        '    if (retainedHandoffSha256.length != 64 || retainedHandoffBytes !in 1L..2_097_152L)' + gn +
        '        throw GradleException("No selected v2 native build pins")')
    config = '            buildConfigField("String", "SCRIPTS_SHA256",'
    generated_config = gn.join([
        '            buildConfigField("String", "RETAINED_HANDOFF_SHA256",',
        r'                "\"${if (retainedHandoffPath != null) retainedHandoffSha256 else ""}\"")',
        '            buildConfigField("long", "RETAINED_HANDOFF_BYTES",',
        '                "${if (retainedHandoffPath != null) retainedHandoffBytes else 0L}L")',
        '            resValue("bool", "retained_handoff_enabled", (retainedHandoffPath != null).toString())',
    ]) + gn
    asset_anchor = '                retainedControllerAssets?.let { task ->'
    asset_v2 = gn.join([
        '                retainedHandoffAssets?.let { task ->',
        '                    variant.sources.assets?.addGeneratedSourceDirectory(task, RetainedHandoffAssetTask::outputDir)',
        '                }',
    ]) + gn
    change('app-android/app/build.gradle.kts', [
        (original_pack, original_pack + handoff_pack),
        (config, generated_config + config),
        (asset_anchor, asset_v2 + asset_anchor),
    ])
    manifest = '    <application android:name=".ui.OneOsApplication">'
    service = gn.join([
        '        <!-- Default-off v2 direct-host offer relay; no native control in app. -->',
        '        <service android:name="com.fahadali.oneos.core.root.RetainedRootHostServiceV2"',
        '            android:enabled="@bool/retained_handoff_enabled"',
        '            android:directBootAware="false" android:exported="false" />',
    ])
    change(FULL + 'AndroidManifest.xml', [(manifest, manifest + gn + service)])
    outputs[SESSION + 'RetainedHandoffControllerSetup.kt'] = sources['compat/handoff-app-integration/RetainedHandoffControllerSetup.kt']
    for name in ('RetainedRootOfferLaunch.java', 'RetainedRootOfferSpawn.java', 'RetainedRootOfferCommand.java'):
        outputs[JAVA + name] = sources[APP + name]
    outputs[JAVA + 'RetainedHostControlProtocol.java'] = sources[SHARED + 'RetainedHostControlProtocol.java']
    original_service = sources[APP + 'RetainedRootHostServiceV2.java']
    anchor = b'                RetainedRootOfferLaunch actual = RetainedRootOfferLaunch.prepare(caller, sha, bytes);'
    insertion = (b'                com.fahadali.oneos.session.RetainedHandoffControllerSetup.ensureInstalled(service, sha, bytes);\n'
                 b'                if (!mayDeliver()) { notifyHost(null); return; }\n')
    if original_service.count(anchor) != 1:
        raise ValueError('Unexpected v2 service entry')
    derived_service = original_service.replace(anchor, insertion + anchor)
    if derived_service.replace(insertion + anchor, anchor, 1) != original_service:
        raise ValueError('Service inverse failed')
    outputs[JAVA + 'RetainedRootHostServiceV2.java'] = derived_service
    edits[JAVA + 'RetainedRootHostServiceV2.java'] = [{'old': base64.b64encode(anchor).decode(),
                                                    'new': base64.b64encode(insertion + anchor).decode()}]
    # All derivation is data-only; no source/tool/native implementation is run.
    checked_path(DEST)
    DEST.mkdir()
    checked_path(DEST)
    patch = []
    actual_outputs = []
    for path, value in outputs.items():
        target = DEST / 'overlay' / path
        actual_outputs.append(write_owned(target, value))
        old = sources.get(CLONE + path, b'')
        patch.extend(difflib.unified_diff(old.decode().splitlines(True), value.decode().splitlines(True),
                                        fromfile='a/' + path, tofile='b/' + path))
    patch_record = write_owned(DEST / 'integration.patch', ''.join(patch).encode())
    receipt = {'schema': 'retained-handoff-app-source-preparation/v1', 'status': 'SOURCE_ONLY_NOT_BUILT',
               'nativePins': {'sha256': native_sha, 'bytes': native_bytes},
               'inputs': [{'path': p, 'bytes': len(v), 'sha256': sha(v)} for p, v in sources.items()],
               'outputs': actual_outputs,
               'inverseEdits': edits, 'patch': patch_record,
               'unchangedInputs': all((ROOT / p).read_bytes() == v for p, v in sources.items()),
               'executedTargets': [], 'limits': ['overlay only, not a complete checkout',
               'no build/install/helper/Android execution', 'file ACK is not process or security readiness']}
    if not receipt['unchangedInputs']:
        raise ValueError('Source changed during preparation; candidate is unaccepted')
    # Reopen every source again at final publication, rather than relying on
    # the generated in-memory values or an earlier successful write alone.
    for record in actual_outputs + [patch_record]:
        path = DEST / record['path']
        checked_path(path)
        actual = path.read_bytes()
        if len(actual) != record['bytes'] or sha(actual) != record['sha256']:
            raise ValueError('Source output changed before receipt')
    write_owned(DEST / 'receipt.json', (json.dumps(receipt, indent=2) + '\n').encode())
    print(json.dumps({'status': receipt['status'], 'receipt': str(DEST / 'receipt.json'),
                      'sha256': sha((DEST / 'receipt.json').read_bytes())}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true', help='Write the isolated source overlay once')
    parser.add_argument('--native-sha256', default='')
    parser.add_argument('--native-bytes', type=int, default=0)
    args = parser.parse_args()
    if not args.prepare:
        parser.error('Specify --prepare for this source-only operation')
    prepare(args.native_sha256, args.native_bytes)
