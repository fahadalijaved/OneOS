"""Give an already patched services.jar the second staged path of the Samsung IMS carve-out.

guest_sec_ims_signature.py's carve-out keeps com.sec.imsservice in android.uid.system only
from the staged /system_ext/priv-app/OneOSSecIms. Since 2026-11-02 (Find N6 global) it also
takes /system/system_ext/priv-app/OneOSSecIms, where an image that keeps system_ext under
system has the package manager scan it. Sets patched before that and only re-patched on top
since (Infinity-X r3, Nothing OS r21, HyperOS r13) kept the one path: on Infinity-X, with
Calls on, "Signature mismatch on system package com.sec.imsservice for shared user
android.uid.system" stopped system_server at every boot (0.4.54 report 80dbbd7b, Galaxy A56).

This rewrites the old carve-out's single check
    const-string vA, "/system_ext/priv-app/OneOSSecIms"
    invoke-virtual {vB, vA}, String;->startsWith(String;)Z
    move-result vA
    if-eqz vA, <its label> (apktool renames the labels a built jar had)
into the current two-path one (the same registers, no new local), leaving the rest of the
carve-out as it is. It refuses a jar that already has the second path or not exactly one
old check.

Usage: guest_secims_path_upgrade.py <smali root dir>
"""
import os
import re
import sys

REL = os.path.join("com", "android", "server", "pm", "PackageManagerServiceUtils.smali")
STAGED = "/system_ext/priv-app/OneOSSecIms"
UNDER_SYSTEM = "/system" + STAGED


def main(root):
    hits = []
    for d, _, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f)
            if p.endswith(REL):
                hits.append(p)
    if len(hits) != 1:
        sys.exit(f"expected exactly one {REL}, found {len(hits)}")
    path = hits[0]
    s = open(path).read()
    if UNDER_SYSTEM in s:
        sys.exit(f"{path}: already takes {UNDER_SYSTEM}")
    pat = re.compile(
        r'(?P<ind>[ \t]*)const-string (?P<a>v\d+), "' + re.escape(STAGED) + r'"\n(?P<g1>\s*)'
        r'invoke-virtual \{(?P<b>v\d+), (?P=a)\}, Ljava/lang/String;->startsWith\(Ljava/lang/String;\)Z\n(?P<g2>\s*)'
        r'move-result (?P=a)\n(?P<g3>\s*)'
        r'if-eqz (?P=a), (?P<done>:\w+)\n')
    found = list(pat.finditer(s))
    if len(found) != 1:
        sys.exit(f"{path}: the one-path carve-out check found {len(found)} times, expected once")
    m = found[0]
    ind, a, b, done = m.group("ind"), m.group("a"), m.group("b"), m.group("done")
    new = (
        f'{ind}const-string {a}, "{STAGED}"\n\n'
        f"{ind}invoke-virtual {{{b}, {a}}}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z\n\n"
        f"{ind}move-result {a}\n\n"
        f"{ind}if-nez {a}, :cond_oneos_secims_staged\n\n"
        f'{ind}const-string {a}, "{UNDER_SYSTEM}"\n\n'
        f"{ind}invoke-virtual {{{b}, {a}}}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z\n\n"
        f"{ind}move-result {a}\n\n"
        f"{ind}if-eqz {a}, {done}\n\n"
        f"{ind}:cond_oneos_secims_staged\n"
    )
    s = s[:m.start()] + new + s[m.end():]
    open(path, "w").write(s)
    print(os.path.relpath(path, root).split(os.sep)[0])
    print(f"{os.path.relpath(path, root)}: the carve-out also takes {UNDER_SYSTEM}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
