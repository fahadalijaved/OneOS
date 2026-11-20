#!/usr/bin/env python3
"""ColorOS lock screen fingerprint icon back after the first unlock on a Galaxy (0.5.20, A36).

At an unlock ColorOS SystemUI hides the on-screen fingerprint icon and its surface goes; the next lock screen shows
it again only once the phone dozes (AODDisplayUtil.isFpDelayUntilDozeAodProcessType: true for the AOD-off type 1001,
"do not show ... needDelayUntilDoze:true"). An OPPO phone dozes after every screen off; a ColorOS guest on a Galaxy
does not with Always-On Display off, so the icon stayed away after the first unlock (owner: "I gotta keep remembering
it"); with AOD on it came back. With this change isFpDelayUntilDozeAodProcessType() returns false: the icon shows at
the wake, as for ColorOS's own no-delay AOD types.

Applies to an already built ColorPanoramicSystemUI.apk: only the dex holding AODDisplayUtil is rebuilt, every other
entry and the signer block are kept, as scripts/patch-coloros-keyguard-lhbm.py does.

usage: patch-coloros-fp-icon-nodoze.py INPUT_SystemUI.apk OUTPUT.apk
"""
import importlib.util
import os
from pathlib import Path
import re
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('panoramic', HERE / 'make-coloros-panoramic-aod.py')
pano = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pano)

CLASS = b'Lcom/oplus/systemui/aod/display/AODDisplayUtil;'
REL = 'com/oplus/systemui/aod/display/AODDisplayUtil.smali'
MARK = 'OneOS: no doze on a Galaxy'


def patch(text):
    if MARK in text:
        raise ValueError('AODDisplayUtil already patched')
    lines = text.split('\n')
    heads = [i for i, l in enumerate(lines) if l == '.method public final isFpDelayUntilDozeAodProcessType()Z']
    if len(heads) != 1:
        raise ValueError(f'isFpDelayUntilDozeAodProcessType()Z found {len(heads)} times')
    i = heads[0]
    if not re.fullmatch(r'    \.locals \d+', lines[i + 1]):
        raise ValueError('unexpected isFpDelayUntilDozeAodProcessType header')
    lines[i + 2:i + 2] = [
        '',
        f'    # {MARK}: the icon shows at the wake, not after a doze that never comes.',
        '    const/4 v0, 0x0',
        '    return v0',
    ]
    return '\n'.join(lines)


def main():
    original, output = Path(sys.argv[1]), Path(sys.argv[2])
    sdk = Path(os.environ.get('ANDROID_HOME', '/opt/android-sdk'))
    bt = sdk / 'build-tools' / os.environ.get('ONEOS_BUILD_TOOLS', '37.0.0')
    apktool = os.environ['APKTOOL']
    with zipfile.ZipFile(original) as z:
        dexes = [n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex', n)]
        names = [n for n in dexes if CLASS in z.read(n) and pano.defines(z.read(n), CLASS)]
    if len(names) != 1:
        raise ValueError(f'{CLASS.decode()} defined in {len(names)} dex files')
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.nodoze-') as tmp:
        w = Path(tmp)
        one = w / 'one.apk'
        with zipfile.ZipFile(original) as src, zipfile.ZipFile(one, 'w') as dst:
            dst.writestr('classes.dex', src.read(names[0]))
            for n in ('AndroidManifest.xml', 'resources.arsc'):
                if n in src.namelist():
                    dst.writestr(src.getinfo(n), src.read(n))
        pano.run('java', '-jar', apktool, 'd', '-f', '-r', '-o', w / 'd', one)
        smali = w / 'd/smali' / REL
        smali.write_text(patch(smali.read_text()))
        pano.run('java', '-jar', apktool, 'b', '-q', '-o', w / 'rebuilt.apk', w / 'd')
        with zipfile.ZipFile(w / 'rebuilt.apk') as z:
            new = {names[0]: z.read('classes.dex')}
        pano.repack(original, new, output, bt / 'zipalign')
    print(f'{output}: {names[0]} rebuilt (isFpDelayUntilDozeAodProcessType returns false)')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))
