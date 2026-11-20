#!/usr/bin/env python3
"""ColorOS AOD lift to show on a Galaxy (0.5.20, A36).

ColorOS SystemUI's AOD wake listener (OplusWakeUpController$amdSensorListener$1, the default branch) registers the
tilt detector and wakes the AOD only for an event whose value is 0, what OPPO's motion sensor sends for a lift. A
Galaxy's Tilt Detector sends 1.0 for every tilt, so picking the phone up never brought the hidden AOD back (A36,
11-17: tilt events at each lift, no wake). With this change any event of that listener counts as a lift.

Applies to an already built ColorPanoramicSystemUI.apk: only the dex holding the listener is rebuilt, every other
entry and the signer block are kept, as scripts/patch-coloros-keyguard-lhbm.py does.

usage: patch-coloros-aod-tilt-wake.py INPUT_SystemUI.apk OUTPUT.apk
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

CLASS = b'Lcom/oplus/systemui/aod/display/OplusWakeUpController$amdSensorListener$1;'
REL = 'com/oplus/systemui/aod/display/OplusWakeUpController$amdSensorListener$1.smali'
MARK = 'OneOS: a Galaxy tilt event is a lift'


def patch(text):
    if MARK in text:
        raise ValueError('listener already patched')
    old = (
        '    invoke-static {v3, v2}, Lkotlin/jvm/internal/Intrinsics;->areEqual(Ljava/lang/Float;F)Z\n'
        '\n'
        '    move-result p1\n'
        '\n'
        '    if-eqz p1, :cond_1\n'
    )
    if text.count(old) != 1:
        raise ValueError(f'lift check found {text.count(old)} times')
    new = (
        f'    # {MARK}: any value (Samsung sends 1.0), not only OPPO\'s 0.\n'
        '    if-eqz v3, :cond_1\n'
    )
    return text.replace(old, new)


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
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.tilt-') as tmp:
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
    print(f'{output}: {names[0]} rebuilt (any tilt event wakes the AOD)')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))
