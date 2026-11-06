#!/usr/bin/env python3
"""Pixel Launcher with double tap to sleep on the home screen (0.4.59), from the exact image donor.

The donor is the image's NexusLauncherRelease.apk: Pixel 11 Fold (yogi), Pixel 11 Pro (kodiak,
classes.dex identical to yogi's) or Pixel 9 Pro XL (komodo, whose classes.dex already has 65536
field ids: its helper goes into a new classes3.dex). One change in
classes.dex: WorkspaceTouchListener.onTouch, right after it sends the wallpaper its
"android.wallpaper.tap" (a tap on an empty spot of the home screen), passes the command, the
tap's screen x and y and the workspace to oneos.launcher.OneOSDt2s (smali-add/, from src/ by
../fold8-pixel/dt2s/build.sh), which asks SystemUI to sleep on a second tap within 400 ms.
Every other entry stays byte for byte; the donor's signature block is kept, as for
Fold8PixelSystemUI.apk (a trusted system-directory replacement, not a content-valid signature).

Usage: build-launcher.py <NexusLauncherRelease.apk> --zipalign <zipalign> --output <apk>
"""
import argparse, copy, hashlib, pathlib, re, shutil, struct, subprocess, sys, tempfile, zipfile

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[2]
DONORS = {'0c8c50434e0cf6f445be6bf6173702dcdbdd7a49baca274f15fcd86afa58500e': 'yogi',
          '3c0ea0aca798fa54395e619b26527da08037fe4bda145d2f4ab62db55547a62f': 'kodiak',
          '28866dd3953784fe154ffcc5c44d76461b12a304e20b9806a1a91338310b4bb0': 'komodo'}
# The donor whose classes.dex has no room for the helper: a new dex for it.
OWN_DEX = {'komodo': 'classes3.dex'}
APKTOOL = ['apktool'] if shutil.which('apktool') else ['java', '-jar', str(sorted((REPO / 'mysticgsi/tools/apktool').glob('*.jar'))[0])]
CLS = 'com/android/launcher3/touch/WorkspaceTouchListener.smali'
SEND = re.compile(r"^(\s*)invoke-virtual/range \{v13 \.\. v19\}, Landroid/app/WallpaperManager;->sendWallpaperCommand"
                  r"\(Landroid/os/IBinder;Ljava/lang/String;IIILandroid/os/Bundle;\)V\s*$", re.M)
HOOK = ("\n{0}# OneOS: double tap to sleep on the home screen (oneos.launcher.OneOSDt2s).\n"
        "{0}move-object/from16 v18, v9\n\n"
        "{0}invoke-static/range {{v15 .. v18}}, Loneos/launcher/OneOSDt2s;->wallpaperTap(Ljava/lang/String;IILandroid/view/View;)V\n")


def patch(decoded, helper_dir='smali'):
    p = decoded / 'smali' / CLS
    s = p.read_text()
    i = s.index('.method public final onTouch(Landroid/view/View;Landroid/view/MotionEvent;)Z')
    j = s.index('.end method', i)
    body = s[i:j]
    # The registers the hook reads: v9 the Workspace, v15 the command, v16/v17 the screen x/y.
    for need in ('iget-object v13, v9, Lcom/android/launcher3/Workspace;->mWallpaperManager:Landroid/app/WallpaperManager;',
                 'move-object v15, v1', 'aget v16, v10, v3', 'aget v17, v10, v4', '.locals 20'):
        assert need in body, need
    m = list(SEND.finditer(body))
    assert len(m) == 1, len(m)
    body = body[:m[0].end()] + HOOK.format(m[0].group(1)) + body[m[0].end():]
    p.write_text(s[:i] + body + s[j:])
    for helper in (ROOT / 'smali-add').rglob('*.smali'):
        dest = decoded / helper_dir / helper.relative_to(ROOT / 'smali-add')
        assert not dest.exists(), dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(helper, dest)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('donor', type=pathlib.Path)
    ap.add_argument('--zipalign', type=pathlib.Path, required=True)
    ap.add_argument('--output', type=pathlib.Path, required=True)
    a = ap.parse_args()
    a.donor = a.donor.resolve(); a.output = a.output.resolve()
    image = DONORS.get(hashlib.sha256(a.donor.read_bytes()).hexdigest())
    assert image, 'different donor'
    own = OWN_DEX.get(image)
    with tempfile.TemporaryDirectory(prefix='oneos-pixel-launcher-') as tmp:
        w = pathlib.Path(tmp); decoded = w / 'decoded'
        subprocess.run(APKTOOL + ['d', '-f', '-r', '-o', str(decoded), str(a.donor)], check=True)
        if own:
            with zipfile.ZipFile(a.donor) as src:
                assert own not in src.namelist(), own
        patch(decoded, 'smali_' + own[:-4] if own else 'smali')
        subprocess.run(APKTOOL + ['b', '-o', str(w / 'rebuilt.apk'), str(decoded)], check=True)
        replacement = (decoded / 'build/apk/classes.dex').read_bytes()
        extra = (decoded / 'build/apk' / own).read_bytes() if own else None
        with a.donor.open('rb') as raw, zipfile.ZipFile(a.donor) as src, zipfile.ZipFile(w / 'raw.apk', 'w') as dst:
            for info in src.infolist():
                if info.filename == 'classes.dex':
                    dst.writestr(info.filename, replacement, compress_type=zipfile.ZIP_STORED)
                    continue
                raw.seek(info.header_offset); header = raw.read(30); assert header[:4] == b'PK\x03\x04'
                nl, el = struct.unpack_from('<HH', header, 26); body = raw.read(nl + el + info.compress_size); desc = b''
                if info.flag_bits & 8:
                    desc = raw.read(4); desc += raw.read(12 if desc == b'PK\x07\x08' else 8)
                entry = copy.copy(info); entry.header_offset = dst.fp.tell(); dst.fp.write(header + body + desc)
                dst.filelist.append(entry); dst.NameToInfo[entry.filename] = entry; dst.start_dir = dst.fp.tell(); dst._didModify = True
            if extra is not None:
                dst.writestr(own, extra, compress_type=zipfile.ZIP_STORED)
        subprocess.run([str(a.zipalign), '-f', '-P', '16', '4', str(w / 'raw.apk'), str(w / 'aligned.apk')], check=True)
        original = a.donor.read_bytes(); e = original.rfind(b'PK\x05\x06'); cd = struct.unpack_from('<I', original, e + 16)[0]
        assert original[cd - 16:cd] == b'APK Sig Block 42'
        size = struct.unpack_from('<Q', original, cd - 24)[0]; block = original[cd - size - 8:cd]
        assert struct.unpack_from('<Q', block)[0] == size
        result = (w / 'aligned.apk').read_bytes(); e = result.rfind(b'PK\x05\x06'); cd = struct.unpack_from('<I', result, e + 16)[0]
        result = bytearray(result[:cd] + block + result[cd:]); struct.pack_into('<I', result, e + len(block) + 16, cd + len(block))
        a.output.write_bytes(result)
    with zipfile.ZipFile(a.donor) as src, zipfile.ZipFile(a.output) as dst:
        assert set(dst.namelist()) - set(src.namelist()) == ({own} if own else set()), set(dst.namelist()) - set(src.namelist())
        assert set(src.namelist()) <= set(dst.namelist())
        for name in src.namelist():
            if name != 'classes.dex':
                assert src.read(name) == dst.read(name), name
    lister = REPO / 'switcher/patches/fold8-pixel/list_dex_classes.py'
    classes = lambda p: subprocess.check_output([sys.executable, str(lister), str(p), '.']).decode().splitlines()
    before, after = classes(a.donor), classes(a.output)
    assert len(after) == len(set(after)) and set(before).issubset(after)
    assert set(after) - set(before) == {'oneos.launcher.OneOSDt2s'}, set(after) - set(before)
    subprocess.run([sys.executable, str(REPO / 'scripts/check-dex.py'), str(a.output)], check=True)
    print(hashlib.sha256(a.output.read_bytes()).hexdigest(), a.output)


if __name__ == '__main__':
    main()
