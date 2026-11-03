#!/usr/bin/env python3
"""A built framework_patched.jar's Samsung IMS stand-ins brought to 0.4.40.

guest_secims_members.py up to 0.4.39 wrote four TelephonyManager stand-ins that
0.4.40 writes differently (the bodies are taken from guest_secims_members.py):
- isGbaSupported() and isGbaSupported(int): false; now from the ISIM service
  table (T-Mobile: no registration task without GBA, S26 Ultra 3255561a);
- semGetServiceState(int) and semGetDataState(int): the argument read as a
  subscription; Samsung passes the SIM slot (an IMS SMS refused by the network
  never fell back to CS, Partner IL 0390db1c).
This rewrites them in a jar built before, for scripts/patch-built-jar.sh. Only
the old body is replaced: a method with any other body refuses.

Usage: guest_secims_gba.py <apktool smali root of framework_patched.jar>
Prints the smali directories it changed.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_secims_members as m  # noqa: E402

CLASS = "android/telephony/TelephonyManager.smali"
SS = m.SS
# (method name and signature, old body, new body)
CHANGES = [
    ("isGbaSupported()Z", m.FALSE, m.GBA_SELF),
    ("isGbaSupported(I)Z", m.FALSE, m.GBA_SUB),
    (f"semGetServiceState(I){SS}", m.per_sub(f"getServiceState(){SS}", "obj"), m.per_slot(f"getServiceState(){SS}", "obj")),
    ("semGetDataState(I)I", m.per_sub("getDataState()I", "int"), m.per_slot("getDataState()I", "int")),
]


def norm(body):
    return "\n".join(l.strip() for l in body.split("\n") if l.strip())


def main(root):
    paths = [os.path.join(root, d, CLASS) for d in sorted(os.listdir(root))
             if d.startswith("smali") and os.path.isfile(os.path.join(root, d, CLASS))]
    if len(paths) != 1:
        sys.exit(f"TelephonyManager found {len(paths)} times")
    path = paths[0]
    text = open(path).read()
    for sig, old, new in CHANGES:
        # apktool writes the stand-ins back with a hidden-API flag (whitelist, ...) and blank lines.
        pat = re.compile(r"^(\.method public (?:[\w-]+ )?" + re.escape(sig) + r")\n(.*?)\n\.end method", re.S | re.M)
        found = pat.findall(text)
        if len(found) != 1:
            sys.exit(f"{sig}: found {len(found)} times")
        if norm(found[0][1]) != norm(old):
            sys.exit(f"{sig}: not the old stand-in:\n{found[0][1]}")
        text = pat.sub(lambda mt: f"{mt.group(1)}\n    {new}\n.end method", text, count=1)
        print(f"{sig}: 0.4.40 stand-in", file=sys.stderr)
    open(path, "w").write(text)
    print(os.path.relpath(path, root).split(os.sep)[0])


if __name__ == "__main__":
    main(sys.argv[1])
