#!/usr/bin/env python3
"""ColorOS lock screen fingerprint icon at every wake on a Galaxy (0.5.33, S24 FE report 97db2ff1 + screenshot).

OnScreenFingerprintUiMech keeps onDreamingStart from the last screen off and clears it only in onDreamingStopped,
which an OPPO phone gets when its doze dream ends at the wake. A ColorOS guest on a Galaxy with Always-On Display off
does not doze, so the flag stayed true: at every wake updateFpIconAlpha took the AOD branch (needShowAODFp:true) and
logged "do not show when screen off or before dream start ... screenTurnedOff:true onDreamingStart:true" (the screen
turns on ~240 ms after the wake starts), and onScreenTurnedOn's own second try ("fp icon not visible, check again")
is skipped while onDreamingStart is set. The lock screen had no fingerprint circle, though the sensor worked.
ColorOS already has the cure for a wake with the screen on ("onStartedWakingUp with screen on, just call
onDreamingStopped"); with this change onScreenTurnedOn does the same when the flag is still set and the phone is
awake (PowerManager.isInteractive: never on an AOD screen, which is not interactive).

Applies to an already built ColorPanoramicSystemUI.apk: only the dex holding OnScreenFingerprintUiMech is rebuilt,
every other entry and the signer block are kept, as scripts/patch-coloros-fp-icon-nodoze.py does.

usage: patch-coloros-fp-icon-screenon.py INPUT_SystemUI.apk OUTPUT.apk
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

CLS = 'Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;'
CLASS = CLS.encode()
REL = 'com/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech.smali'
MARK = 'OneOS: stale dream flag at screen on'
HEAD = f'.method public static final access$onScreenTurnedOn({CLS})V'


def patch(text):
    if MARK in text:
        raise ValueError('OnScreenFingerprintUiMech already patched')
    for need in (r'^\.field [\w ]*\bonDreamingStart:Z$', r'^\.field [\w ]*\bcontext:Landroid/content/Context;$',
                 '^' + re.escape(f'.method public static final access$onDreamingStopped({CLS})V') + '$'):
        if not re.search(need, text, re.M):
            raise ValueError(f'not the expected OnScreenFingerprintUiMech: no {need}')
    lines = text.split('\n')
    heads = [i for i, l in enumerate(lines) if l == HEAD]
    if len(heads) != 1:
        raise ValueError(f'access$onScreenTurnedOn found {len(heads)} times')
    i = heads[0]
    m = re.fullmatch(r'    \.locals (\d+)', lines[i + 1])
    if not m:
        raise ValueError('unexpected access$onScreenTurnedOn header')
    end = lines.index('.end method', i)
    if '"onScreenTurnedOn()"' not in '\n'.join(lines[i:end]):
        raise ValueError('access$onScreenTurnedOn without its log line')
    if int(m.group(1)) < 2:
        lines[i + 1] = '    .locals 2'
    lines[i + 2:i + 2] = [
        '',
        f'    # {MARK}: no doze dream ends on a Galaxy, so do what ColorOS does at a wake with the screen on.',
        f'    iget-boolean v0, p0, {CLS}->onDreamingStart:Z',
        '    if-eqz v0, :oneos_screenon_keep',
        f'    iget-object v0, p0, {CLS}->context:Landroid/content/Context;',
        '    const-class v1, Landroid/os/PowerManager;',
        '    invoke-virtual {v0, v1}, Landroid/content/Context;->getSystemService(Ljava/lang/Class;)Ljava/lang/Object;',
        '    move-result-object v0',
        '    check-cast v0, Landroid/os/PowerManager;',
        '    if-eqz v0, :oneos_screenon_keep',
        '    invoke-virtual {v0}, Landroid/os/PowerManager;->isInteractive()Z',
        '    move-result v0',
        '    if-eqz v0, :oneos_screenon_keep',
        '    const-string v0, "OnScreenFingerprintUiMech"',
        '    const-string v1, "OneOS: screen on while awake, dream flag still set: onDreamingStopped"',
        '    invoke-static {v0, v1}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V',
        f'    invoke-static {{p0}}, {CLS}->access$onDreamingStopped({CLS})V',
        '    return-void',
        '',
        '    :oneos_screenon_keep',
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
        raise ValueError(f'{CLS} defined in {len(names)} dex files')
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.fpscreenon-') as tmp:
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
    print(f'{output}: {names[0]} rebuilt (onScreenTurnedOn clears a stale dream flag)')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))
