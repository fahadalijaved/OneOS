#!/usr/bin/env python3
"""Build baseline and experimental Fold8 Lineage UI payloads from exact donors.

Does not change package pins or publish. Review hashes before updating metadata.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DONOR = 'aa22961855b1f8a9d3dbbbc643922f9b216f6d411313e12eb8b70086287b84c3'
RELAY = 'ccf2fbddc462eca6d7cb7f112ca1b36620fe0ccd044ff6ba28bebe13cfe6b89e'

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--systemui', type=Path, required=True)
    p.add_argument('--relay', type=Path, required=True)
    p.add_argument('--sdk', type=Path, required=True)
    p.add_argument('--keystore', type=Path, default=Path.home()/'.android/debug.keystore')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if digest(a.systemui) != DONOR or digest(a.relay) != RELAY:
        p.error('SystemUI or relay is not the pinned donor')
    if a.out.exists():
        p.error('Output already exists')
    bt = a.sdk/'build-tools/36.1.0'
    jar = a.sdk/'platforms/android-37.0/android.jar'
    def run(*args):
        subprocess.run(list(map(str,args)),check=True)
    a.out.mkdir(parents=True)
    baseline = a.out/'baseline'; baseline.mkdir()
    overrides = a.out/'overrides'; overrides.mkdir()
    shutil.copyfile(a.systemui,baseline/'Fold8LineageSystemUI.apk')
    shutil.copyfile(a.relay,baseline/'Fold8AngleRelay.dex')
    run('python3',ROOT/'switcher/patches/fold8-lineage/build-systemui.py',a.systemui,
        '--zipalign',bt/'zipalign','--output',overrides/'Fold8LineageSystemUI.apk')
    for variant,output in [('stable',baseline/'Fold8LineageUnfold.apk'),
                           ('experimental',overrides/'Fold8LineageUnfold.apk'),
                           ('statusbar',overrides/'OneOSPixelStatusBar.apk'),
                           ('settings_stable',baseline/'OneOSSettingsSplit.apk'),
                           ('settings_experimental',overrides/'OneOSSettingsSplit.apk')]:
        source = ROOT/'switcher/overlays'/(('lineage_'+variant) if variant.startswith('settings_') else ('lineage_fold8_'+variant))
        with tempfile.TemporaryDirectory(prefix='oneos-lineage-rro-') as temporary:
            w = Path(temporary)
            run(bt/'aapt2','compile','--dir',source/'res','-o',w/'res.zip')
            run(bt/'aapt2','link','-o',w/'unsigned.apk','--manifest',source/'AndroidManifest.xml',
                '-I',jar,'--min-sdk-version','31','--target-sdk-version','36','--auto-add-overlay',w/'res.zip')
            run(bt/'zipalign','-f','4',w/'unsigned.apk',w/'aligned.apk')
            run(bt/'apksigner','sign','--v4-signing-enabled','false','--ks',a.keystore,
                '--ks-key-alias','androiddebugkey','--ks-pass','pass:android','--key-pass','pass:android',
                '--out',output,w/'aligned.apk')
    for folder in (baseline,overrides):
        for item in sorted(folder.iterdir()):
            print(f'{digest(item)}  {item}')

if __name__ == '__main__':
    main()
