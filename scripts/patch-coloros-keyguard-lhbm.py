#!/usr/bin/env python3
"""ColorOS lock screen at full brightness on a Galaxy whose optical sensor lights its own spot (0.5.20, A36).

ColorOS SystemUI (KeyguardFeatureOption.isLocalHBM) asks OPPO's display-panel HAL (feature 0xd3, bit 0x10) whether
the panel lights the fingerprint spot by itself (local HBM). A Galaxy has no such HAL, so the answer is no, and for
an optical sensor without local HBM ColorOS darkens the whole lock screen (its dim layer) and raises the backlight
for the scan: on the A36 the lock screen was very dim and full brightness came back at unlock. The A36's panel has
local HBM (OneOSSehTouch lights it). With this change isLocalHBM() first reads ro.oneos.fp_lhbm, which
guest_props.sh sets to 1 on such a phone only; without it the stock check runs as before.

Applies to an already built ColorPanoramicSystemUI.apk (scripts/make-coloros-panoramic-aod.py's output): only the
dex holding KeyguardFeatureOption is rebuilt, every other entry and the signer block are kept, as that script does.

usage: patch-coloros-keyguard-lhbm.py INPUT_SystemUI.apk OUTPUT.apk
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

CLASS = b'Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;'
REL = 'com/oplusos/systemui/common/feature/KeyguardFeatureOption.smali'
MARK = 'ro.oneos.fp_lhbm'


def patch(text):
    if MARK in text:
        raise ValueError('KeyguardFeatureOption already patched')
    lines = text.split('\n')
    heads = [i for i, l in enumerate(lines) if l == '.method public static isLocalHBM()Z']
    if len(heads) != 1:
        raise ValueError(f'isLocalHBM()Z found {len(heads)} times')
    i = heads[0]
    m = re.fullmatch(r'    \.locals (\d+)', lines[i + 1])
    if not m:
        raise ValueError('unexpected isLocalHBM header')
    lines[i + 1] = f'    .locals {max(2, int(m.group(1)))}'
    lines[i + 2:i + 2] = [
        '',
        f'    # OneOS: the panel lights the fingerprint spot itself on this Galaxy ({MARK}, guest_props.sh).',
        f'    const-string v0, "{MARK}"',
        '    const/4 v1, 0x0',
        '    invoke-static {v0, v1}, Landroid/os/SystemProperties;->getBoolean(Ljava/lang/String;Z)Z',
        '    move-result v0',
        '    if-eqz v0, :oneos_stock_lhbm',
        '    return v0',
        '    :oneos_stock_lhbm',
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
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.lhbm-') as tmp:
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
    print(f'{output}: {names[0]} rebuilt (isLocalHBM reads {MARK})')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))
