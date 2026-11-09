"""Keep the guest's lock settings away from the phone's weaver hardware.

The container shares the host's HALs, so the guest framework's weaver (the
secure element / TEE slots that protect every user's synthetic password) is
the one One UI's own protectors live in. ColorOS's SyntheticPasswordManager
knows no protectors (its /data is the stage's), picks the first weaver slot it
considers free and enrolls user 0's synthetic password there: slot 0, which
on a phone that was never reset is One UI's live slot. The friend's S25 Ultra
(session f075d93a, 2026-10-23) then came back from ColorOS unable to unlock
user 0's credential-encrypted storage ("Phone restarted - unlock your phone",
Direct Boot state, nothing to enter: no lock was set), and had to be reset.
The owner's Fold was spared only because its live protector sits in slot 2.

Make getWeaverServiceLocked() return null: the framework then takes the
"device has no weaver" paths (gatekeeper or software-only protectors, as on
phones without weaver) and never enrolls, reads or writes a slot.
guest_prepare.sh clears a guest lock state that still has weaver records.

Pixel's services.jar (R8) has the same method as public final. Every weaver
lookup there goes through it as well: getWeaverService() calls it, and
getWeaverServiceInternal() (AIDL, then HIDL) is called only from it.

Usage: guest_no_weaver.py <smali root dir>
Prints the smali_* directories (dex files) it changed, one per line.
"""
import os
import re
import sys

HEADER = re.compile(r"^\.method (?:private |public |final )*getWeaverServiceLocked\(\)Landroid/hardware/weaver/IWeaver;$")
# Android 16 (OnePlus's OxygenOS 16) has no getWeaverServiceLocked(): the lookup is the synchronized
# getWeaverService() itself (it caches mWeaver and calls getWeaverServiceInternal(), AIDL then HIDL).
# Taken only when nothing else calls getWeaverServiceInternal() and mWeaver is written nowhere else
# (its death recipient clears it through the -$$Nest$fputmWeaver accessor).
HEADER16 = re.compile(r"^\.method (?:private |public |final |declared-synchronized )*getWeaverService\(\)Landroid/hardware/weaver/IWeaver;$")


def span_of(lines, k):
    """The method containing line k: (its .method line, its .end method line)."""
    s = max(i for i in range(k + 1) if lines[i].startswith(".method "))
    e = next(i for i in range(k, len(lines)) if lines[i].startswith(".end method"))
    return s, e


def android16_lookup(path, lines):
    heads = [k for k, l in enumerate(lines) if HEADER16.match(l)]
    if len(heads) != 1:
        sys.exit(f"{path}: neither getWeaverServiceLocked() nor one getWeaverService() ({len(heads)})")
    own = span_of(lines, heads[0])
    for k, l in enumerate(lines):
        if "SyntheticPasswordManager;->getWeaverServiceInternal()" in l and span_of(lines, k) != own:
            sys.exit(f"{path}: getWeaverServiceInternal() called outside getWeaverService() (line {k + 1})")
        if re.match(r"^\s*iput-object \S+, \S+, Lcom/android/server/locksettings/SyntheticPasswordManager;->mWeaver:", l):
            s, _ = span_of(lines, k)
            if s != own[0] and "-$$Nest$fputmWeaver(" not in lines[s]:
                sys.exit(f"{path}: mWeaver written outside getWeaverService() (line {k + 1})")
    return heads


def main(root):
    changed = set()
    for dirpath, _, files in os.walk(root):
        if "SyntheticPasswordManager.smali" not in files:
            continue
        path = os.path.join(dirpath, "SyntheticPasswordManager.smali")
        lines = open(path).read().split("\n")
        if not any(l.startswith(".class ") and l.endswith("Lcom/android/server/locksettings/SyntheticPasswordManager;") for l in lines):
            continue
        heads = [k for k, l in enumerate(lines) if HEADER.match(l)]
        if not heads:
            heads = android16_lookup(path, lines)
        if len(heads) != 1:
            sys.exit(f"{path}: getWeaverServiceLocked() found {len(heads)} times, expected once")
        i = heads[0]
        m = re.match(r"\s*\.locals (\d+)$", lines[i + 1])
        if not m or int(m.group(1)) < 2:
            sys.exit(f"{path}: unexpected getWeaverServiceLocked header")
        j = i + 2
        while lines[j].strip() == "" or lines[j].lstrip().startswith((".param", ".end param")):
            j += 1
        lines[j:j] = [
            "    # OneOS: the weaver slots belong to One UI's protectors; the guest never gets the service.",
            '    const-string v0, "SyntheticPasswordManager"',
            "",
            '    const-string v1, "OneOS: weaver is the host\'s; the guest keeps software protectors"',
            "",
            "    invoke-static {v0, v1}, Landroid/util/Slog;->i(Ljava/lang/String;Ljava/lang/String;)I",
            "",
            "    const/4 v0, 0x0",
            "",
            "    return-object v0",
            "",
        ]
        open(path, "w").write("\n".join(lines))
        changed.add(os.path.relpath(path, root).split(os.sep)[0])
        print(f"{os.path.relpath(path, root)}: getWeaverServiceLocked() returns null", file=sys.stderr)
    if not changed:
        sys.exit("SyntheticPasswordManager not found")
    for d in sorted(changed):
        print(d)


if __name__ == "__main__":
    main(sys.argv[1])
