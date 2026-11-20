#!/usr/bin/env python3
"""ColorOS panoramic AOD hides at once on a Galaxy (0.5.20, A36).

When the panoramic (full-screen wallpaper) AOD hides, ColorOS SystemUI fades a black mask in over 700 ms
(OplusAODMaskAnimController.getPanoramicMaskInAnim) with the display in doze. A Galaxy panel in doze takes few frames,
so the fade showed as a few hard steps and a flicker before black (A36, 11-17: "flickering and going black"). With
this change the mask is in at once: the wallpaper goes to black in one frame.

Applies to an already built ColorPanoramicSystemUI.apk: only the dex holding the controller is rebuilt, every other
entry and the signer block are kept, as scripts/patch-coloros-keyguard-lhbm.py does.

usage: patch-coloros-aod-mask-instant.py INPUT_SystemUI.apk OUTPUT.apk
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

CLASS = b'Lcom/oplus/systemui/aod/anim/OplusAODMaskAnimController;'
REL = 'com/oplus/systemui/aod/anim/OplusAODMaskAnimController.smali'
MARK = 'OneOS: panoramic mask in at once on a Galaxy'


def patch(text):
    if MARK in text:
        raise ValueError('controller already patched')
    lines = text.split('\n')
    heads = [i for i, l in enumerate(lines) if l.startswith('.method public final getPanoramicMaskInAnim()')]
    if len(heads) != 1:
        raise ValueError(f'getPanoramicMaskInAnim found {len(heads)} times')
    end = lines.index('.end method', heads[0])
    hits = [i for i in range(heads[0], end) if lines[i] == '    const-wide/16 v2, 0x2bc']
    if len(hits) != 1:
        raise ValueError(f'700 ms duration found {len(hits)} times')
    lines[hits[0]] = f'    const-wide/16 v2, 0x0  # {MARK} (was 0x2bc, 700 ms)'
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
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.mask-') as tmp:
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
    print(f'{output}: {names[0]} rebuilt (panoramic mask in at once)')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))
