#!/usr/bin/env python3
"""vdcoolok's ColorOS fingerprint wave (pull request #152, switcher/patches/systemui-fingerprint-wave there), for
ultrasonic sensors (owner 11-27: "we should have used Vd's PR for S25U and ColorOS"; S25 Ultra 115496: no unlock
animation, a laggy lock screen to home).

What it does, as he made it on the Galaxy S25 Ultra: the glyph shows first when the thumb is already on the sensor
at the wake (no pressed wave before it), a full wave plays over the home screen after the unlock and the ring hides
at its end, the wave runs at 16 ms frames (120 Hz), and the full-screen black dim layer
(notifyHighlightVisibleUpdate) stays out of the unlock path. His diff, rebased onto this image's SystemUI after
scripts/patch-coloros-fp-icon-screenon.py (oneosWakeGlyph goes before that patch's stale-dream block).

Ours on top: every entry point first asks OneOsGlyphShow.on(), ro.oneos.fp_wave, which guest_props.sh sets only for
an ultrasonic sensor. The set also serves Galaxies with optical sensors (A36, A5x, FE), which need ColorOS's own
highlight flow and were never tried with the wave.

Applies to an already built ColorPanoramicSystemUI.apk: only the dex holding OnScreenFingerprintUiMech is rebuilt,
every other entry and the signer block are kept.

usage: APKTOOL=apktool.jar patch-coloros-fp-wave.py INPUT_SystemUI.apk OUTPUT.apk
"""
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PATCH = HERE.parent / 'switcher/patches/coloros-fp-wave/coloros-fp-wave.patch'
spec = importlib.util.spec_from_file_location('panoramic', HERE / 'make-coloros-panoramic-aod.py')
pano = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pano)

CLS = 'Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;'
CLASS = CLS.encode()
UDFPS = 'smali/com/oplus/systemui/biometrics/finger/udfps'


def main():
    original, output = Path(sys.argv[1]), Path(sys.argv[2])
    sdk = Path(os.environ.get('ANDROID_HOME', '/opt/android-sdk'))
    bt = sdk / 'build-tools' / os.environ.get('ONEOS_BUILD_TOOLS', '37.0.0')
    apktool = os.environ['APKTOOL']
    with zipfile.ZipFile(original) as z:
        dexes = [n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex', n)]
        names = [n for n in dexes if CLASS in z.read(n) and pano.defines(z.read(n), CLASS)]
    if len(names) != 1:
        raise ValueError(f'{CLS} defined in {len(names)} dex files')
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.fpwave-') as tmp:
        w = Path(tmp)
        one = w / 'one.apk'
        with zipfile.ZipFile(original) as src, zipfile.ZipFile(one, 'w') as dst:
            dst.writestr('classes.dex', src.read(names[0]))
            for n in ('AndroidManifest.xml', 'resources.arsc'):
                if n in src.namelist():
                    dst.writestr(src.getinfo(n), src.read(n))
        pano.run('java', '-jar', apktool, 'd', '-f', '-r', '-o', w / 'd', one)
        if (w / 'd' / UDFPS / 'OneOsGlyphShow.smali').exists():
            raise ValueError('OnScreenFingerprintUiMech already has the wave')
        subprocess.run(['patch', '-p1', '--no-backup-if-mismatch', '-F0', '-d', str(w / 'd'), '-i', str(PATCH)], check=True)
        pano.run('java', '-jar', apktool, 'b', '-q', '-o', w / 'rebuilt.apk', w / 'd')
        with zipfile.ZipFile(w / 'rebuilt.apk') as z:
            new = {names[0]: z.read('classes.dex')}
        pano.repack(original, new, output, bt / 'zipalign')
    print(f'{output}: {names[0]} rebuilt (vdcoolok fingerprint wave, gated on ro.oneos.fp_wave)')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        sys.exit(str(exc))
