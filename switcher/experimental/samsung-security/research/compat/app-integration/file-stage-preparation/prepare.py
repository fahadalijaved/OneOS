"""Derive the standalone OneOS file-backed Prepare/Stop app sources offline."""

import argparse
import hashlib
import json
from pathlib import Path
import stat


ROOT = Path(__file__).absolute().parents[3]
APP = 'out/isolated-retained-view-app-build/r-acfd6f87'
HOST = 'out/retained-pin-host-cohort/r-15a49021'
NATIVE = 'out/tree-retained-controller/r-b40000a8'
NATIVE_RECEIPT = '22865cbd53a654d217e93db31eff650e0bacc1a94f8681ceee817e1c3ee05e2d'
NATIVE_SHA = '803691c55ac876a42d57488a1c10d76328aa33c3a4ff6cf3606d16f8d201d125'
NATIVE_BYTES = 746760
NATIVE_LEAF = 'oneos_retained_tree_preparation'
STAGE = '/data/local/tmp/oneos-viewprep'
PACKAGE = 'com.fahadali.oneos.viewprep.filetree'
VERSION = '0.0.1-filetree'

APP_PINS = {
    'BuildConfig.java': 'fd183d227725ce9066e476285e12ae68cde8de3a8a04e03e6db996afca6fd9a0',
    'PrepareActivity.java': 'f2f7380b6dea92b6746360dd50d1c16aaf6dde77e676d8c3ef85c219ff09ca71',
    'RetainedHostControlProtocol.java': 'f7b587f52ba6aa7ec04985c4e8c6186b839d5e00d98bbd9d53ae748b7e331611',
    'RetainedRootHostServiceV2.java': '97b2afa1ed319d9e5362b470c2c44f02dfdc8ef36bd9186345a3da9318003c1f',
    'RetainedRootOfferCommand.java': '6d27d407c7fc958e75351a8ce521286d937853cd1a0559971dce563efd30c2e0',
    'RetainedRootOfferLaunch.java': '3b45a03d12cd77c4bc4b0cac35defad3f4d89f18b33be48d17b48a66b3afa386',
    'RetainedRootOfferSpawn.java': '3fc1c4cb6b3614419253ff536c77eed87d39cdb3dda036f4d29ebf8ad33362f0',
    'RetainedViewAppProtocol.java': '18f157d6e4642c7a5b094ca7cc9feabfa16af2e02ba66e013b5f0748f788597f',
}
MANIFEST_PIN = 'a1bd56ec474106ed69f8be68b1f8201e2fe7d029c4f52c6fc56216799ae91f99'
STOP_PATCH = 'compat/handoff-view/isolated-preparation-stop-observed.patch'
STOP_PIN = '54a491c4d8736ef30ac386df7d1ffff785ae8686dd300e999d761473500b1e8b'
HOST_PINS = {
    'receipt.json': '0260dffda000b95cfe2f4a9bf83afc939ae455f2724c6302a07de2d634abfab3',
    'source/RetainedHostNativeControlV2.java': '52482a9358f32ee51dd50d7a38d8a91f5b7cdb042bcb48ea6518723677e5671f',
    'source/PreparedRetainedHostNativeBindingV2.java': '35ae3a2e3ed50017ac0528dff7a170a0cd84814bb3e2fdb400be7dd8b2b10d8d',
    'source/HostRootLinkProfileV2.java': '020c0a2f91c8c62505851a2d091df1672b60cfd8d2ec012577077ca02fffdfec',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def read(path, expected, pins):
    data = (ROOT / path).read_bytes()
    require(sha(data) == expected, f'Exact input changed: {path}')
    pins[path] = expected
    return data


def patch_activity(source, patch):
    """Apply the small existing Stop fence with exact old/new lines and offsets."""
    before = source.splitlines(keepends=True)
    lines = patch.splitlines(keepends=True)
    out, cursor, cursor_out = [], 0, 0
    index = 2
    while index < len(lines):
        header = lines[index].split()
        require(len(header) >= 4 and header[0] == b'@@' and header[3] == b'@@', 'Stop hunk header differs')
        old_start, old_count = map(int, header[1][1:].split(b','))
        new_start, new_count = map(int, header[2][1:].split(b','))
        old_start -= 1
        new_start -= 1
        require(cursor <= old_start and cursor_out + old_start - cursor == new_start, 'Stop hunk offset differs')
        out.extend(before[cursor:old_start])
        cursor = old_start
        cursor_out = new_start
        index += 1
        while index < len(lines) and not lines[index].startswith(b'@@ '):
            tag, body = lines[index][:1], lines[index][1:]
            require(tag in (b' ', b'-', b'+'), 'Stop hunk operation differs')
            if tag != b'+':
                require(cursor < len(before) and before[cursor] == body, 'Stop hunk context differs')
                cursor += 1
            if tag != b'-':
                out.append(body)
                cursor_out += 1
            index += 1
        require(cursor == old_start + old_count and cursor_out == new_start + new_count, 'Stop hunk size differs')
    return b''.join(out + before[cursor:])


def changed(data, old, new):
    old, new = old.encode('ascii'), new.encode('ascii')
    require(data.count(old) == 1 and new not in data, 'Expected one exact source anchor')
    result = data.replace(old, new, 1)
    require(result.count(new) == 1 and result.replace(new, old, 1) == data, 'Source inverse differs')
    return result


def derive(enabled):
    pins = {}
    app = {name: read(f'{APP}/src/{name}', pin, pins) for name, pin in APP_PINS.items()}
    manifest = read(f'{APP}/manifest/AndroidManifest.xml', MANIFEST_PIN, pins)
    stop = read(STOP_PATCH, STOP_PIN, pins)
    for path, pin in HOST_PINS.items():
        read(f'{HOST}/{path}', pin, pins)
    receipt = json.loads(read(f'{NATIVE}/receipt.json', NATIVE_RECEIPT, pins))
    executable = receipt['executable']
    require(receipt['status'] == 'PASS_FILE_BACKED_PREPARE_STOP_STATIC_LINK_ONLY'
            and receipt['deviceEligible'] is False and receipt['localCleanupWireState'] == 6
            and executable['path'] == f'{NATIVE}/{NATIVE_LEAF}'
            and executable['sha256'] == NATIVE_SHA and executable['bytes'] == NATIVE_BYTES,
            'File-backed controller receipt differs')
    require(len(read(executable['path'], NATIVE_SHA, pins)) == NATIVE_BYTES <= 2097152,
            'File-backed controller exceeds the existing bound')

    app['BuildConfig.java'] = changed(app['BuildConfig.java'],
        'public static final boolean RETAINED_VIEW_PREPARATION = true;',
        f'public static final boolean RETAINED_VIEW_PREPARATION = {str(enabled).lower()};\n'
        f'    public static final String RETAINED_VIEW_CONTROLLER_SHA256 = "{NATIVE_SHA}";\n'
        f'    public static final long RETAINED_VIEW_CONTROLLER_BYTES = {NATIVE_BYTES}L;')

    launch = app['RetainedRootOfferCommand.java']
    app['RetainedRootOfferCommand.java'] = changed(launch,
        f'S={STAGE}\\nB=$S/bin\\nP=$B/oneos_retained_root_handoff\\n',
        f'S={STAGE}\\nB=$S/bin\\nP=$B/{NATIVE_LEAF}\\n')

    service = app['RetainedRootHostServiceV2.java']
    app['RetainedRootHostServiceV2.java'] = changed(service,
        '        if (callback == null || sha == null || !sha.matches("[0-9a-f]{64}") || bytes < 1 || bytes > 2097152) {',
        '        if (!com.fahadali.oneos.BuildConfig.RETAINED_VIEW_PREPARATION || callback == null\n'
        '                || !com.fahadali.oneos.BuildConfig.RETAINED_VIEW_CONTROLLER_SHA256.equals(sha)\n'
        '                || bytes != com.fahadali.oneos.BuildConfig.RETAINED_VIEW_CONTROLLER_BYTES) {')

    activity = patch_activity(app['PrepareActivity.java'], stop)
    activity = changed(activity, 'package com.fahadali.oneos.viewprep;', f'package {PACKAGE};')
    activity = changed(activity, '"OneOS View Prep"', '"OneOS File View Prep"')
    activity = changed(activity, 'boolean start = view == prepare && current == null;',
        'boolean start = view == prepare && current == null\n'
        '                && com.fahadali.oneos.BuildConfig.RETAINED_VIEW_PREPARATION;')
    activity = changed(activity, 'if (confirmingPrepare && current == null) {',
        'if (confirmingPrepare && current == null && com.fahadali.oneos.BuildConfig.RETAINED_VIEW_PREPARATION) {')
    activity = changed(activity, 'prepare.setVisibility(operation == null ? View.VISIBLE : View.GONE);',
        'prepare.setVisibility(operation == null ? View.VISIBLE : View.GONE);\n'
        '        prepare.setEnabled(com.fahadali.oneos.BuildConfig.RETAINED_VIEW_PREPARATION);')
    activity = changed(activity,
        'status.setText(operation == null ? "Prepare a private view of the tester stage." : operation.message());',
        'if (operation != null) status.setText(operation.message());\n'
        '        else if (com.fahadali.oneos.BuildConfig.RETAINED_VIEW_PREPARATION)\n'
        '            status.setText("Prepare a file-backed view of the tester stage. "\n'
        '                    + "The host has a two-minute window from native commit to send Prepare.");\n'
        '        else status.setText("File-backed preparation is disabled in this build.");')
    app['PrepareActivity.java'] = activity

    manifest = changed(manifest, 'package="com.fahadali.oneos.viewprep"', f'package="{PACKAGE}"')
    manifest = changed(manifest, 'android:label="OneOS View Prep"', 'android:label="OneOS File View Prep"')
    return {**{f'src/{name}': data for name, data in app.items()}, 'manifest/AndroidManifest.xml': manifest}, pins, executable


def save(enabled):
    files, pins, executable = derive(enabled)
    base = ROOT / 'out' / 'file-stage-preparation-app'
    target = base / ('enabled' if enabled else 'default-off')
    for directory in (ROOT, ROOT / 'out', base):
        if directory.exists() or directory.is_symlink():
            mode = directory.lstat()
            require(stat.S_ISDIR(mode.st_mode) and not stat.S_ISLNK(mode.st_mode)
                    and not (getattr(mode, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT),
                    f'Output directory must be a real directory: {directory}')
    base.mkdir(exist_ok=True)
    target.mkdir()  # Exclusive. A partial output is retained for inspection.
    (target / 'src').mkdir()
    (target / 'manifest').mkdir()
    output = {}
    for leaf, data in files.items():
        path = target / leaf
        with path.open('xb') as stream:
            stream.write(data)
        require(path.read_bytes() == data, f'Output readback differs: {leaf}')
        output[leaf] = {'sha256': sha(data), 'bytes': len(data)}
    result = {
        'status': 'PASS_PREPARE_STOP_APP_SOURCE_ONLY',
        'package': PACKAGE, 'versionCode': 1, 'versionName': VERSION,
        'enabled': enabled, 'inputs': pins, 'outputs': output,
        'controller': {**executable, 'fixedInstallPath': f'{STAGE}/bin/{NATIVE_LEAF}',
                       'execArg': '--host-control-v2'},
        'host': {'changed': False, 'nativeStateLocalTerminal': 6,
                 'firstPrepareReceiveWindowMs': 120000, 'frameObservationBudgetMs': 30000},
        'deviceEligible': False,
    }
    with (target / 'receipt.json').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print((target / 'receipt.json').relative_to(ROOT).as_posix())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--enable-preparation', action='store_true',
                        help='Emit an explicitly enabled offline source candidate')
    save(parser.parse_args().enable_preparation)
