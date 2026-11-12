#!/usr/bin/env python3
"""ColorPanoramicSystemUI.apk: a ColorOS SystemUI that offers wallpaper AOD without OPPO's panel HAL.

ColorOS SystemUI (SmoothTransitionController.initSmoothTransitionState) asks OPPO's display-panel
HAL for feature 217; bit 4 means the panel can show the wallpaper on the always-on display
("panoramic AOD"). A Galaxy has no such HAL, so the call fails and the error path clears
isSupportPanoramicByPanelFeature. One UI shows the wallpaper on AOD on the same panels, so this
build keeps that one flag true on the error path, nothing else: smooth transition, all-day
panoramic and gotoDozeWithOff stay as the error path sets them. The other half of SystemUI's
check, the app feature com.oplus.systemui.panoramic_aod.enable, is added in the guest
(guest_prepare.sh, oneos_panoramic_aod.sh). The Find N6 build has the same change as a pinned
hunk (patches/fold8-coloros/systemui-global.patch).

Only the dex holding the class is rebuilt; every other entry and the signer block are kept as
they are (as make-fold8-coloros.py does: a root-only system overlay, not an installable APK).

usage: make-coloros-panoramic-aod.py ORIGINAL_SystemUI.apk OUTPUT.apk
"""
import copy
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
CLASS = b'Lcom/oplus/systemui/aod/display/SmoothTransitionController;'
FIELD = 'Lcom/oplus/systemui/aod/display/SmoothTransitionController;->isSupportPanoramicByPanelFeature:Z'
ERROR = '"initSmoothTransitionState get feature error"'


def defines(dex, name):
    """Whether this dex defines the class (not only refers to it)."""
    def string(i):
        off = struct.unpack_from('<I', dex, string_ids + 4 * i)[0]
        while dex[off] & 0x80:  # skip the ULEB128 length
            off += 1
        end = dex.index(b'\0', off + 1)
        return dex[off + 1:end]
    string_ids = struct.unpack_from('<I', dex, 0x3C)[0]
    type_ids = struct.unpack_from('<I', dex, 0x44)[0]
    n, off = struct.unpack_from('<II', dex, 0x60)
    for k in range(n):
        type_idx = struct.unpack_from('<I', dex, off + 32 * k)[0]
        if string(struct.unpack_from('<I', dex, type_ids + 4 * type_idx)[0]) == name:
            return True
    return False


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def patch_smali(text):
    """Set the panel flag true on initSmoothTransitionState's error path; refuse anything unexpected."""
    m = re.search(r'^\.method [^\n]*initSmoothTransitionState\(\)V\n(.*?)^\.end method', text, re.S | re.M)
    if not m:
        raise ValueError('initSmoothTransitionState not found')
    body = m.group(1)
    if 'OneOS wallpaper AOD' in body:
        return text
    e = body.find(ERROR)
    if e < 0:
        raise ValueError('error path not found')
    seg_end = body.find(':goto_', e)
    seg = body[e:seg_end if seg_end > 0 else len(body)]
    hits = list(re.finditer(r'^    iput-boolean (v(\d+)), (v\d+|p0), ' + re.escape(FIELD) + r'\n', seg, re.M))
    if len(hits) != 1:
        raise ValueError(f'expected one panel flag store on the error path, found {len(hits)}')
    h = hits[0]
    reg, num, obj = h.group(1), int(h.group(2)), h.group(3)
    if num > 15:
        raise ValueError(f'{reg} is out of const/4 range')
    new = (f'    # OneOS wallpaper AOD: a Galaxy has no display-panel HAL; One UI shows the wallpaper on AOD here\n'
           f'    const/4 {reg}, 0x1\n\n'
           f'    iput-boolean {reg}, {obj}, {FIELD}\n\n'
           f'    const/4 {reg}, 0x0\n')
    seg2 = seg[:h.start()] + new + seg[h.end():]
    body2 = body[:e] + seg2 + body[e + len(seg):]
    return text[:m.start(1)] + body2 + text[m.end(1):]


def repack(original, dex_name, dex_bytes, output, zipalign):
    rawzip, aligned = output.with_suffix('.zip'), output.with_suffix('.aligned')
    with original.open('rb') as raw, zipfile.ZipFile(original) as src, zipfile.ZipFile(rawzip, 'w') as dst:
        for info in src.infolist():
            if info.filename == dex_name:
                dst.writestr(zipfile.ZipInfo(info.filename, info.date_time), dex_bytes, compress_type=zipfile.ZIP_STORED)
                continue
            raw.seek(info.header_offset)
            header = raw.read(30)
            assert header[:4] == b'PK\x03\x04'
            nl, el = struct.unpack_from('<HH', header, 26)
            body = raw.read(nl + el + info.compress_size)
            desc = b''
            if info.flag_bits & 8:
                desc = raw.read(4)
                desc += raw.read(12 if desc == b'PK\x07\x08' else 8)
            entry = copy.copy(info)
            entry.header_offset = dst.fp.tell()
            dst.fp.write(header + body + desc)
            dst.filelist.append(entry); dst.NameToInfo[entry.filename] = entry
            dst.start_dir = dst.fp.tell(); dst._didModify = True
    run(zipalign, '-f', '-P', '16', '4', rawzip, aligned)
    rawzip.unlink()
    a = original.read_bytes()
    e = a.rfind(b'PK\x05\x06'); cd = struct.unpack_from('<I', a, e + 16)[0]
    if a[cd - 16:cd] != b'APK Sig Block 42':
        raise ValueError('original SystemUI has no APK signer block')
    size = struct.unpack_from('<Q', a, cd - 24)[0]
    block = a[cd - size - 8:cd]
    b = aligned.read_bytes()
    aligned.unlink()
    e = b.rfind(b'PK\x05\x06'); cd = struct.unpack_from('<I', b, e + 16)[0]
    result = bytearray(b[:cd] + block + b[cd:])
    struct.pack_into('<I', result, e + len(block) + 16, cd + len(block))
    output.write_bytes(result)
    with zipfile.ZipFile(original) as src, zipfile.ZipFile(output) as dst:
        assert src.namelist() == dst.namelist()
        assert dst.testzip() is None
        for n in src.namelist():
            if n != dex_name:
                assert src.read(n) == dst.read(n), n


def main():
    original, output = Path(sys.argv[1]), Path(sys.argv[2])
    sdk = Path(os.environ.get('ANDROID_HOME', '/opt/android-sdk'))
    bt = sdk / 'build-tools' / os.environ.get('ONEOS_BUILD_TOOLS', '37.0.0')
    apktool = os.environ.get('APKTOOL', str(ROOT / 'mysticgsi/tools/apktool/apktool.jar'))
    with zipfile.ZipFile(original) as z:
        names = [n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex', n) and CLASS in z.read(n) and defines(z.read(n), CLASS)]
    if len(names) != 1:
        raise ValueError(f'SmoothTransitionController in {len(names)} dex files')
    dex_name = names[0]
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.panoramic-') as tmp:
        w = Path(tmp)
        one = w / 'one.apk'
        with zipfile.ZipFile(original) as src, zipfile.ZipFile(one, 'w') as dst:
            dst.writestr('classes.dex', src.read(dex_name))
            for n in ('AndroidManifest.xml', 'resources.arsc'):
                if n in src.namelist():
                    dst.writestr(src.getinfo(n), src.read(n))
        run('java', '-jar', apktool, 'd', '-f', '-r', '-o', w / 'd', one)
        smali = w / 'd/smali/com/oplus/systemui/aod/display/SmoothTransitionController.smali'
        smali.write_text(patch_smali(smali.read_text()))
        run('java', '-jar', apktool, 'b', '-q', '-o', w / 'rebuilt.apk', w / 'd')
        with zipfile.ZipFile(w / 'rebuilt.apk') as z:
            dex_bytes = z.read('classes.dex')
        repack(original, dex_name, dex_bytes, output, bt / 'zipalign')
    print(f'{output}: {dex_name} rebuilt')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        sys.exit(str(exc))
