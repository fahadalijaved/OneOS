#!/usr/bin/env python3
"""Pixel Fold's device state policy without tent mode: patch an image's yogi-services.jar.

Pixel 11 Fold (yogi) decides which panel is on from the hinge angle with
BookStyleClosedStatePredicate (system_ext/framework/yogi-services.jar). Opened
from closed, the inner panel takes over as soon as the hinge leaves 0 degrees,
unless PostureEstimator.isLikelyTentOrWedgeMode() is true: then the cover is
kept until 90 degrees. It is true when the screen is rotated, when the right
half lies flat (an accelerometer in each half, which a Galaxy has not), when
the orientation sensor says seascape, or whenever the screen is kept on (a
window or "stay awake" while charging). On the Z Fold8 Ultra, whose hinge sensor
first reports at about 62 degrees and in coarse steps after, the inner panel
came on only fully open; One UI has no tent mode and uses it half open
(owner, 0.4.59 tests). The method returns false here.

Usage: patch-yogi-tent.py <yogi-services.jar> <out.jar>
The dex is stored uncompressed, as in the image; every other entry is copied.
"""
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLS = "com/android/server/policy/BookStyleClosedStatePredicate$PostureEstimator.smali"
BODY = """.method public isLikelyTentOrWedgeMode()Z
    .locals 1

    # OneOS (scripts/patch-yogi-tent.py): no tent mode on a Galaxy.
    const/4 v0, 0x0

    return v0
"""


def main(src, out):
    apktool = sorted(glob.glob(os.path.join(ROOT, "mysticgsi/tools/apktool/*.jar")))[0]
    w = tempfile.mkdtemp()
    try:
        dec = os.path.join(w, "dec")
        subprocess.run(["java", "-jar", apktool, "d", "-q", "-r", "-f", "-o", dec, src], check=True)
        p = os.path.join(dec, "smali", CLS)
        s = open(p).read()
        m = re.search(r"\.method public isLikelyTentOrWedgeMode\(\)Z\n.*?(?=\.end method)", s, re.S)
        if not m:
            sys.exit(f"{CLS}: no isLikelyTentOrWedgeMode()Z")
        open(p, "w").write(s[:m.start()] + BODY + s[m.end():])
        rebuilt = os.path.join(w, "rebuilt.apk")
        subprocess.run(["java", "-jar", apktool, "b", "-q", "-o", rebuilt, dec], check=True)
        with zipfile.ZipFile(rebuilt) as z:
            dex = z.read("classes.dex")
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, "w") as zout:
            for info in zin.infolist():
                data = dex if info.filename == "classes.dex" else zin.read(info.filename)
                zi = zipfile.ZipInfo(info.filename, info.date_time)
                zi.compress_type = zipfile.ZIP_STORED
                zi.external_attr = info.external_attr
                zout.writestr(zi, data)
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts/check-dex.py"), out], check=True)
        print(f"built {out} (isLikelyTentOrWedgeMode returns false)")
    finally:
        shutil.rmtree(w, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
