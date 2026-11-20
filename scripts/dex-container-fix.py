#!/usr/bin/env python3
"""After a patched jar was made by swapping single rebuilt dex files into a copy of the original:
fix it when the original is a dex container, then check that no class went missing.

One UI 9.5 (S948BXXU6ZZKN) ships framework.jar and telephony-common.jar as one classes.dex in the
dex container format (version 041, several dex sections in one file). apktool decodes the sections
as smali, smali_classes2, ... and rebuilds them as separate classes*.dex, so replacing only the
"changed" ones left classes.dex holding section 1 alone: framework_patched.jar had 22,198 of
46,463 classes and the A36's zygote aborted ("Native registration unable to find class
com/android/internal/os/ApplicationSharedMemory", run 5).

When the rebuilt jar has more dex files than the original, every classes*.dex of <patched.jar> is
replaced by the rebuilt jar's (all of them, stored). Either way, every class of <original.jar> must
be in <patched.jar> afterwards, or this exits 1.

Usage: dex-container-fix.py <original.jar> <rebuilt.jar> <patched.jar>
Needs dexdump from the SDK build-tools.
"""
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

DEX = re.compile(r"classes\d*\.dex$")
dexdump = sorted(glob.glob(os.path.join(os.environ.get("ANDROID_HOME", "/opt/android-sdk"),
                                        "build-tools", "*", "dexdump")))[-1]


def dex_names(jar):
    with zipfile.ZipFile(jar) as z:
        return sorted(n for n in z.namelist() if DEX.match(n))


def classes(jar):
    out = set()
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(jar) as z:
        for n in z.namelist():
            if not DEX.match(n):
                continue
            p = z.extract(n, tmp)
            text = subprocess.run([dexdump, p], capture_output=True).stdout.decode("utf-8", "replace")
            out.update(re.findall(r"^  Class descriptor  : '([^']+)'", text, re.M))
    return out


def main(orig, rebuilt, patched):
    if len(dex_names(rebuilt)) > len(dex_names(orig)):
        tmp = patched + ".tmp"
        with zipfile.ZipFile(patched) as src, zipfile.ZipFile(tmp, "w") as dst, zipfile.ZipFile(rebuilt) as rb:
            for info in src.infolist():
                if not DEX.match(info.filename):
                    dst.writestr(info, src.read(info.filename))
            for n in dex_names(rebuilt):
                dst.writestr(zipfile.ZipInfo(n, date_time=(2008, 1, 1, 0, 0, 0)), rb.read(n),
                             compress_type=zipfile.ZIP_STORED)
        shutil.move(tmp, patched)
        print(f"{os.path.basename(patched)}: the original is a dex container "
              f"({len(dex_names(orig))} dex, {len(dex_names(rebuilt))} rebuilt): all rebuilt dex files used")
    missing = classes(orig) - classes(patched)
    if missing:
        sys.exit(f"{os.path.basename(patched)}: {len(missing)} classes of the original are missing "
                 f"(e.g. {sorted(missing)[:3]})")
    print(f"{os.path.basename(patched)}: every class of the original is there")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
