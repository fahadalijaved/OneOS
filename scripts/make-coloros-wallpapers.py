#!/usr/bin/env python3
"""Rebuild the four tested Flux fixes from the exact Find N6 Wallpapers donor.

The result is a root-only post-scan overlay, never an OEM-signed installable APK.
No account, region, orientation, theme data or unrelated APK entry is changed.
"""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DONOR = '2e8d489f7ea9c3a16c6258f72fc2d9dd59ad3f6f86d7db67a7f57f21cb384622'
PATCHES = ['editor', 'viewport', 'depth', 'touch']
DEX = ['classes5.dex', 'classes6.dex']


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apk', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    with a.apk.open('rb') as source:
        if hashlib.file_digest(source, 'sha256').hexdigest() != DONOR:
            p.error('Unsupported Wallpapers donor; output not written')
    if a.out.exists():
        p.error('Output already exists')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    tool = os.environ.get('APKTOOL', 'apktool')
    apktool = ['java', '-jar', tool] if tool.endswith('.jar') else [tool]
    with tempfile.TemporaryDirectory(dir=a.out.parent, prefix='.wallpapers-') as tmp:
        w = Path(tmp)
        with zipfile.ZipFile(a.apk) as source, zipfile.ZipFile(w/'input.apk', 'w') as filtered:
            for n in ['AndroidManifest.xml', 'resources.arsc', 'classes.dex'] + DEX:
                filtered.writestr(n, source.read(n))
        decoded = w/'decoded'
        run(*apktool, 'd', '-a', '-f', '-r', '-o', decoded, w/'input.apk')
        for name in PATCHES:
            run('python3', '-I', ROOT/f'switcher/patches/fold8_coloros_flux_{name}.py', decoded)
        run(*apktool, 'b', '-o', w/'rebuilt.apk', decoded)
        previous = a.apk
        with zipfile.ZipFile(w/'rebuilt.apk') as rebuilt:
            for i, name in enumerate(DEX):
                dex = w/name
                dex.write_bytes(rebuilt.read(name))
                result = w/f'patched-{i}.apk'
                run('python3', '-I', ROOT/'scripts/apk-replace-dex.py', previous, name, dex, result)
                previous = result
        run('python3', '-I', ROOT/'scripts/check-dex.py', previous)
        with zipfile.ZipFile(a.apk) as source, zipfile.ZipFile(previous) as result:
            assert source.namelist() == result.namelist()
            for name in source.namelist():
                if name not in DEX:
                    assert source.read(name) == result.read(name), name
        previous.rename(a.out)
    print(f'Root-only post-scan overlay: {a.out}')


if __name__ == '__main__':
    main()
