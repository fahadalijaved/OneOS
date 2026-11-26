#!/usr/bin/env python3
"""vivo's camera keeps the phone's device type, for already-built OriginOS framework jars (0.5.50).

vivo_guards.py's launcher_phone_type makes FtDeviceInfo.getDeviceType() answer "phone" in the launcher's
process; its list now holds com.android.camera too (VivoCamera loaded its fold UI, which the PD2609MA build
lacks: ClassNotFoundException CameraUIController_Fold, Fold5 a36acd8a). This adds the camera's process to a
jar built before that change (scripts/patch-built-jar.sh). Prints the smali dir it changed.

Usage: vivo_camera_phone.py <decoded jar dir>
"""
import os
import re
import sys

NAME = "com.android.camera"


def main(root):
    for top in sorted(os.listdir(root)):
        p = os.path.join(root, top, "android", "util", "FtDeviceInfo.smali")
        if not top.startswith("smali") or not os.path.isfile(p):
            continue
        s = open(p, encoding="utf-8").read()
        if f'const-string v1, "{NAME}"' in s:
            return 0
        # A rebuilt jar's labels are apktool's (:cond_0), not vivo_guards.py's (:oneos_launcher): reuse the one there.
        anchor = re.search(r'    const-string v1, "com\.bbk\.launcher2"\n\n    invoke-virtual \{v1, v0\}, '
                           r'Ljava/lang/String;->equals\(Ljava/lang/Object;\)Z\n\n    move-result v1\n\n'
                           r'    if-nez v1, :(\w+)\n\n', s)
        if not anchor:
            sys.exit("vivo_camera_phone: the launcher check is not in FtDeviceInfo.getDeviceType()")
        add = (f'    const-string v1, "{NAME}"\n\n'
               "    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z\n\n"
               "    move-result v1\n\n"
               f"    if-nez v1, :{anchor.group(1)}\n\n")
        s = s[:anchor.end()] + add + s[anchor.end():]
        open(p, "w", encoding="utf-8").write(s)
        print(top)
        return 0
    sys.exit("vivo_camera_phone: no android/util/FtDeviceInfo.smali")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
