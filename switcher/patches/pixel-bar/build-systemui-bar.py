#!/usr/bin/env python3
"""Double tap to sleep for the bar Pixel images (0.4.59): their own SystemUIGoogle with two hooks.

The Fold build (../fold8-pixel/build-systemui.py) swaps whole smali files that also carry the
hinge and quick settings work; a bar phone needs only double tap to sleep, so this one inserts
the two calls the Fold's NotificationShadeWindowView has, by pattern, into the image's own:
  - dispatchTouchEvent: OneOSDt2s.shadeTouch(view, event) first (the lock screen, and a wake on AOD);
  - onAttachedToWindow: OneOSDt2s.register(view) first (the receiver for the launcher's
    "double tap on the home screen" broadcast).
The helpers (../fold8-pixel/dt2s/smali, from dt2s/src by dt2s/build.sh) go into a new
classes4.dex: the Pixel 9 Pro XL's classes2.dex already has 65535 field ids. Only classes2.dex is
replaced and classes4.dex added; every other entry and the donor's signature block stay byte for
byte (its platform certificate, which android.uid.systemui needs: never use the Fold's APK, built
from yogi's donor, on these images).

Usage: build-systemui-bar.py <SystemUIGoogle.apk> --zipalign <zipalign> --output <apk>
"""
import argparse, copy, hashlib, pathlib, re, shutil, struct, subprocess, sys, tempfile, zipfile

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[2]
APKTOOL = ['apktool'] if shutil.which('apktool') else ['java', '-jar', str(sorted((REPO / 'mysticgsi/tools/apktool').glob('*.jar'))[0])]
DT2S = REPO / 'switcher/patches/fold8-pixel/dt2s/smali'
DONORS = {'db35d92ce22e7afcafde19877c4d5f60ec94cf7389bcb140b22902a4ca3e53ec': 'kodiak',
          'e2072d91e7fe553256de6b6bfdbce00691e67a0b99fb90db3afb3dff9285c91b': 'komodo'}
VIEW = 'smali_classes2/com/android/systemui/shade/NotificationShadeWindowView.smali'
HOOKS = [
    (re.compile(r'^(\.method public final dispatchTouchEvent\(Landroid/view/MotionEvent;\)Z\n    \.locals \d+\n)', re.M),
     '\n    invoke-static/range {p0 .. p1}, Loneos/sysui/OneOSDt2s;->shadeTouch(Landroid/view/View;Landroid/view/MotionEvent;)V\n'),
    (re.compile(r'^(\.method (?:public |protected )?(?:final )?onAttachedToWindow\(\)V\n    \.locals \d+\n)', re.M),
     '\n    invoke-static {p0}, Loneos/sysui/OneOSDt2s;->register(Landroid/view/View;)V\n'),
]
ADDED = {'oneos.sysui.OneOSDt2s', 'oneos.sysui.OneOSDt2s$1'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('donor', type=pathlib.Path)
    ap.add_argument('--zipalign', type=pathlib.Path, required=True)
    ap.add_argument('--output', type=pathlib.Path, required=True)
    a = ap.parse_args()
    a.donor = a.donor.resolve(); a.output = a.output.resolve()
    image = DONORS.get(hashlib.sha256(a.donor.read_bytes()).hexdigest())
    assert image, 'not a bar Pixel SystemUIGoogle this was written against'
    with tempfile.TemporaryDirectory(prefix='oneos-pixel-bar-') as tmp:
        w = pathlib.Path(tmp); decoded = w / 'decoded'
        subprocess.run(APKTOOL + ['d', '-f', '-r', '-o', str(decoded), str(a.donor)], check=True)
        view = decoded / VIEW
        text = view.read_text()
        assert 'OneOSDt2s' not in text, 'already hooked'
        for rx, call in HOOKS:
            ms = list(rx.finditer(text))
            assert len(ms) == 1, (rx.pattern, len(ms))
            text = text[:ms[0].end()] + call + text[ms[0].end():]
        view.write_text(text)
        own = decoded / 'smali_classes4'
        assert not own.exists()
        for helper in DT2S.rglob('*.smali'):
            dest = own / helper.relative_to(DT2S)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(helper, dest)
        subprocess.run(APKTOOL + ['b', '-o', str(w / 'rebuilt.apk'), str(decoded)], check=True)
        classes2 = (decoded / 'build/apk/classes2.dex').read_bytes()
        classes4 = (decoded / 'build/apk/classes4.dex').read_bytes()
        with a.donor.open('rb') as raw, zipfile.ZipFile(a.donor) as src, zipfile.ZipFile(w / 'raw.apk', 'w') as dst:
            assert 'classes4.dex' not in src.namelist()
            for info in src.infolist():
                if info.filename == 'classes2.dex':
                    dst.writestr(info.filename, classes2, compress_type=zipfile.ZIP_STORED)
                    continue
                raw.seek(info.header_offset); header = raw.read(30); assert header[:4] == b'PK\x03\x04'
                nl, el = struct.unpack_from('<HH', header, 26); body = raw.read(nl + el + info.compress_size); desc = b''
                if info.flag_bits & 8:
                    desc = raw.read(4); desc += raw.read(12 if desc == b'PK\x07\x08' else 8)
                entry = copy.copy(info); entry.header_offset = dst.fp.tell(); dst.fp.write(header + body + desc)
                dst.filelist.append(entry); dst.NameToInfo[entry.filename] = entry; dst.start_dir = dst.fp.tell(); dst._didModify = True
            dst.writestr('classes4.dex', classes4, compress_type=zipfile.ZIP_STORED)
        subprocess.run([str(a.zipalign), '-f', '-P', '16', '4', str(w / 'raw.apk'), str(w / 'aligned.apk')], check=True)
        # The donor's signature block, kept as the Fold build does (a trusted system-directory
        # replacement, not a content-valid signature).
        original = a.donor.read_bytes(); e = original.rfind(b'PK\x05\x06'); cd = struct.unpack_from('<I', original, e + 16)[0]
        assert original[cd - 16:cd] == b'APK Sig Block 42'
        size = struct.unpack_from('<Q', original, cd - 24)[0]; block = original[cd - size - 8:cd]
        assert struct.unpack_from('<Q', block)[0] == size
        result = (w / 'aligned.apk').read_bytes(); e = result.rfind(b'PK\x05\x06'); cd = struct.unpack_from('<I', result, e + 16)[0]
        result = bytearray(result[:cd] + block + result[cd:]); struct.pack_into('<I', result, e + len(block) + 16, cd + len(block))
        a.output.write_bytes(result)
    with zipfile.ZipFile(a.donor) as src, zipfile.ZipFile(a.output) as dst:
        assert set(dst.namelist()) - set(src.namelist()) == {'classes4.dex'}
        for name in src.namelist():
            if name != 'classes2.dex':
                assert src.read(name) == dst.read(name), name
    lister = REPO / 'switcher/patches/fold8-pixel/list_dex_classes.py'
    classes = lambda p: subprocess.check_output([sys.executable, str(lister), str(p), '.']).decode().splitlines()
    before, after = classes(a.donor), classes(a.output)
    assert len(after) == len(set(after)) and set(before).issubset(after)
    assert set(after) - set(before) == ADDED, set(after) - set(before)
    subprocess.run([sys.executable, str(REPO / 'scripts/check-dex.py'), str(a.output)], check=True)
    print(hashlib.sha256(a.output.read_bytes()).hexdigest(), image, a.output)


if __name__ == '__main__':
    main()
