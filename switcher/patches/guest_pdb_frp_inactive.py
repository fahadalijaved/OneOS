"""Make the guest's PersistentDataBlockService report FRP as inactive.

guest_pdb_readonly.py points every write of the guest's PDB at /dev/null and leaves
reads alone, so the guest's FRP state is whichever state One UI's real FRP partition
holds. On a phone whose FRP partition reads active that makes the guest FRP-active
too, and MIUI-based images gate the screen-lock setup on it: Settings shows
"Factory reset protection is on" and refuses to set a password, which also keeps
fingerprint out of Settings (both live behind the same lock screen page).

The guest never uses the real partition, so its FRP state is meaningless. Two
methods are forced:

1. isFrpActive()Z returns false. It is the read behind enforceFactoryResetProtection
   Inactive (the write gate, already relaxed by guest_pdb_frp_writes_fail.py) and
   behind the Stub's own checks.
2. setOldSettingForBackworkCompatibility(Z)V writes 0 to Settings.Global
   "secure_frp_mode". MIUI keeps that global as a mirror of the FRP state for older
   Settings builds that read the setting instead of the service; the mirror is only
   written on a state change, so a guest that came up FRP-active keeps 1 forever.
   Forcing the written value to 0 makes every write of it agree with isFrpActive().

Usage: guest_pdb_frp_inactive.py <apktool decoded services.jar dir>
Prints the smali_* directory it changed.
"""
import os
import re
import sys

REL = os.path.join("com", "android", "server", "pdb", "PersistentDataBlockService.smali")
MARK = "guest_pdb_frp_inactive"

INACTIVE = """\
    .locals 2

    # OneOS (patches/%(m)s.py): the guest never uses One UI's FRP partition, so its
    # FRP state is meaningless. Report inactive; callers unchanged.
    const/4 v0, 0x0

    return v0
"""

MIRROR = [
    "# OneOS (patches/%(m)s.py): keep Settings.Global \"secure_frp_mode\" at 0 so MIUI",
    "# Settings never takes the FRP-active path when setting a screen lock.",
    "const/4 %(v)s, 0x0",
]


def fail(msg):
    sys.exit("guest_pdb_frp_inactive: " + msg)


def method(t, sig):
    found = [m for m in re.finditer(r"^\.method ([^\n]*)\n(.*?)^\.end method\n", t, re.M | re.S)
             if m.group(1).split() and m.group(1).split()[-1] == sig]
    if len(found) != 1:
        fail("%s found %d times" % (sig, len(found)))
    return found[0]


def main():
    if len(sys.argv) != 2:
        fail(__doc__)
    root = sys.argv[1]
    hits = [d for d in sorted(os.listdir(root)) if d.startswith("smali") and os.path.isfile(os.path.join(root, d, REL))]
    if len(hits) != 1:
        fail("PersistentDataBlockService in %d dex dirs" % len(hits))
    d = hits[0]
    p = os.path.join(root, d, REL)
    t = open(p, encoding="utf-8").read()
    if MARK in t:
        fail("already patched")

    active = method(t, "isFrpActive()Z")
    body = active.group(2)
    if "mFrpActive:Z" not in body:
        fail("isFrpActive() does not read mFrpActive")
    if ".locals 2" not in body:
        fail("isFrpActive() is not .locals 2")
    t = t[:active.start(2)] + INACTIVE % {"m": MARK} + t[active.end(2):]

    mirror = method(t, "setOldSettingForBackworkCompatibility(Z)V")
    body = mirror.group(2)
    m = re.search(r'^(\s*)if-eqz p1, :cond_\w+\n\s*\n?\s*const/4 (v\d+), 0x1\n\s*\n?\s*goto :\w+\n\s*\n?\s*:cond_\w+\n\s*const/4 \2, 0x0\n',
                  body, re.M)
    if not m:
        fail("setOldSettingForBackworkCompatibility() is not the p1 ? 1 : 0 mirror")
    ind = m.group(1)
    note = "\n".join(ind + s for s in MIRROR) % {"m": MARK, "v": m.group(2)}
    t = t[:mirror.start(2) + m.start()] + note + "\n" + t[mirror.start(2) + m.end():]

    open(p, "w", encoding="utf-8").write(t)
    print("%s: %s/%s: isFrpActive() is false, the secure_frp_mode mirror stays 0" % (MARK, d, REL), file=sys.stderr)
    print(d)


if __name__ == "__main__":
    main()
