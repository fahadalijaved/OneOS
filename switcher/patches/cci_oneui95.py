#!/usr/bin/env python3
"""CameraCompatibilityInfo as One UI 9.5's cameraserver reads it (0.5.49).

One UI 9.5 (S26 Ultra S948BXXU6ZZKN) added mShouldOverrideLensFacingFrontToBack and writes it as a sixth
field, a boolean after mShouldAllowTransformInverseDisplay. AOSP/Android 17 guests (HyperOS, PixelOS, Pixel,
LineageOS, Infinity-X, Nothing OS, ColorOS, OriginOS) write five, so on a One UI 9.5 phone every camera call
carrying it (getCameraInfo, connect, connectDevice, getCameraCharacteristics) was read one field off and
answered with a NullPointerException: HyperOS's TorchModeHelper let it kill system_server 7 s after start
(S26 Ultra 4823ed41, 0.5.48). Only for the framework_patched_oneui95.jar variants: a false is written after
the fifth field. Frameworks that already write the sixth field, or not these five, are left alone.

0.5.51 (S26 Ultra PixelOS 356d83de, black screen): the guest's own framework also parcels the class in its app
transactions (IApplicationThread), so writing six and reading five left every app's bind with "Parcel data not
fully consumed" and no app ever started. The Parcel constructor now reads the sixth field too (marker READ_MARK),
also on a jar that already had the write.

Usage: cci_oneui95.py <decoded jar dir>; prints the smali dir it changed (nothing when none).
"""
import os
import re
import sys

WRITE = "Landroid/os/Parcel;->write"
FIELD6 = "mShouldOverrideLensFacingFrontToBack"
FIVE = ["writeInt", "writeBoolean", "writeBoolean", "writeInt", "writeBoolean"]
READ_MARK = "OneOS (cci_oneui95.py read)"
READ5 = [["readInt", "readByte", "readByte", "readInt", "readByte"], ["readInt", "readBoolean", "readBoolean", "readInt", "readBoolean"]]


def add_read(s, p):
    """The Parcel constructor reads One UI 9.5's sixth field (a boolean) after the five; returns the new text."""
    if READ_MARK in s:
        return s
    m = re.search(r"(\.method [^\n]*constructor [^\n]*<init>\(Landroid/os/Parcel;\)V\n)(.*?)(\.end method)", s, re.S)
    if not m:
        sys.exit(f"cci_oneui95: no Parcel constructor in {p}")
    body = m.group(2)
    reads = re.findall(r"Landroid/os/Parcel;->(read[A-Za-z]+)\(", body)
    if reads not in READ5:
        sys.exit(f"cci_oneui95: unexpected reads {reads} in {p}")
    preg = re.findall(r"invoke-virtual \{(p\d+)\}, Landroid/os/Parcel;->read", body)
    if len(set(preg)) != 1:
        sys.exit(f"cci_oneui95: the reads use {sorted(set(preg))} in {p}")
    rets = re.findall(r"^\s*return-void\s*$", body, re.M)
    if len(rets) != 1:
        sys.exit(f"cci_oneui95: {len(rets)} return-void in the Parcel constructor of {p}")
    add = (f"    # {READ_MARK}: One UI 9.5's sixth field, written by writeToParcel above\n"
           f"    invoke-virtual {{{preg[0]}}}, Landroid/os/Parcel;->readBoolean()Z\n\n")
    body2 = re.sub(r"^(\s*return-void\s*)$", lambda r: add + r.group(1), body, count=1, flags=re.M)
    return s[:m.start(2)] + body2 + s[m.end(2):]


def main(root):
    for top in sorted(os.listdir(root)):
        p = os.path.join(root, top, "android", "content", "res", "CameraCompatibilityInfo.smali")
        if not top.startswith("smali") or not os.path.isfile(p):
            continue
        s = open(p, encoding="utf-8").read()
        if FIELD6 in s:
            # The write is there (an earlier run, or the framework's own sixth field): the read may still be missing.
            s2 = add_read(s, p) if "OneOS (cci_oneui95.py)" in s else s
            if s2 != s:
                open(p, "w", encoding="utf-8").write(s2)
                print(top)
            return 0
        m = re.search(r"(\.method public [^\n]*writeToParcel\(Landroid/os/Parcel;I\)V\n)(.*?)(\.end method)", s, re.S)
        if not m:
            sys.exit(f"cci_oneui95: no writeToParcel in {p}")
        body = m.group(2)
        writes = re.findall(r"Landroid/os/Parcel;->(write[A-Za-z]+)\(", body)
        if writes == FIVE + ["writeBoolean"]:
            # A jar this patch built before 0.5.51 (apktool drops the comment): the write is there, add the read.
            s2 = add_read(s, p)
            if s2 != s:
                open(p, "w", encoding="utf-8").write(s2)
                print(top)
            return 0
        if writes != FIVE:
            sys.exit(f"cci_oneui95: unexpected fields {writes} in {p}")
        # R8 builds write from p2 with .locals 0: one local is added (apktool renumbers the p registers).
        if re.search(r"^\s*\.locals 0\s*$", body, re.M):
            body = re.sub(r"^(\s*)\.locals 0\s*$", r"\1.locals 1", body, count=1, flags=re.M)
        elif not re.search(r"\.locals [1-9]", body):
            sys.exit(f"cci_oneui95: no .locals in {p}")
        rets = re.findall(r"^\s*return-void\s*$", body, re.M)
        if len(rets) != 1:
            sys.exit(f"cci_oneui95: {len(rets)} return-void in {p}")
        add = ("    # OneOS (cci_oneui95.py): One UI 9.5's sixth field, mShouldOverrideLensFacingFrontToBack = false\n"
               "    const/4 v0, 0x0\n\n"
               "    invoke-virtual {p1, v0}, Landroid/os/Parcel;->writeBoolean(Z)V\n\n")
        body2 = re.sub(r"^(\s*return-void\s*)$", lambda r: add + r.group(1), body, count=1, flags=re.M)
        s = s[:m.start(2)] + body2 + s[m.end(2):]
        s = add_read(s, p)
        open(p, "w", encoding="utf-8").write(s)
        print(top)
        return 0
    sys.exit("cci_oneui95: no android/content/res/CameraCompatibilityInfo.smali")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
