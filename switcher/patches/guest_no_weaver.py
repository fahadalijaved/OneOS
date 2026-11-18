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
# One UI 9.5 (S948BXXU6ZZKN): getWeaverService() returns the WeaverConnection wrapper (public final, one
# mWeaverInitializationLock monitor); its initialize() is the only thing that opens the AIDL or HIDL HAL.
HEADER_CONN = re.compile(r"^\.method (?:private |public |final |declared-synchronized )*getWeaverService\(\)Lcom/android/server/security/weaver/WeaverConnection;$")
HEADER_SUPPORT = re.compile(r"^\.method (?:private |public |final )*isSupportWeaver\(\)Z$")


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


def connection_lookup(path, lines, root):
    """One UI 9.5: getWeaverService() hands out the WeaverConnection. Accepted only when its callers
    treat null as "no weaver" (a null check on the result) and initialize() and the connection's own
    HAL lookups are reached from nowhere else, so returning null before them opens no slot."""
    heads = [k for k, l in enumerate(lines) if HEADER_CONN.match(l)]
    if len(heads) != 1:
        return []
    own = span_of(lines, heads[0])
    for k, l in enumerate(lines):
        if "WeaverConnection;->initialize()Z" in l and span_of(lines, k) != own:
            sys.exit(f"{path}: WeaverConnection.initialize() called outside getWeaverService() (line {k + 1})")
    for dp, _, fs in os.walk(root):
        for f in fs:
            if not f.endswith(".smali") or f.startswith("WeaverConnection"):
                continue
            fp = os.path.join(dp, f)
            if fp == path:
                continue
            txt = open(fp).read()
            if re.search(r"WeaverConnection;->(initialize\(\)Z|getWeaverAidlService|getWeaverHidlService)", txt) or \
               ("SyntheticPasswordManager;->getWeaverService()" in txt and not _null_checked(txt)):
                sys.exit(f"{fp}: reaches the weaver lookup without a null check")
    if not _null_checked("\n".join(lines)):
        sys.exit(f"{path}: a getWeaverService() caller does not null-check the result")
    return heads


def _null_checked(txt):
    """Every getWeaverService() call in txt is followed by move-result-object and an if-eqz/if-nez on it
    within a few lines (checkWeaverStatus() tests it after a try/catch)."""
    ls = txt.split("\n")
    for k, l in enumerate(ls):
        if "SyntheticPasswordManager;->getWeaverService()" in l and l.lstrip().startswith("invoke"):
            tail = [x.strip() for x in ls[k + 1:k + 40] if x.strip()]
            if not tail or not tail[0].startswith("move-result-object"):
                return False
            reg = tail[0].split()[-1]
            if not any(re.match(r"if-(eqz|nez) " + re.escape(reg) + ",", x) for x in tail[1:25]):
                return False
    return True


def samsung_no_securehw(root):
    """One UI 9.5: LockSettingsService.isSupportWeaver() is the system property security.securehw.available,
    and when it is set Samsung's rate-limit and policy paths ask HermesService, which reads weaver slot
    100000 + userId on the HAL (getFailureCount) with an empty key. Make it false: the guest is software only."""
    out = set()
    for dirpath, _, files in os.walk(root):
        if "LockSettingsService.smali" not in files:
            continue
        path = os.path.join(dirpath, "LockSettingsService.smali")
        text = open(path).read()
        if not re.match(r"\.class (?:public |final )*Lcom/android/server/locksettings/LockSettingsService;\n", text):
            continue
        if "HermesService/IHermesService;->" not in text:
            continue
        lines = text.split("\n")
        heads = [k for k, l in enumerate(lines) if HEADER_SUPPORT.match(l)]
        if len(heads) != 1:
            sys.exit(f"{path}: isSupportWeaver() found {len(heads)} times, expected once")
        i = heads[0]
        e = next(k for k in range(i, len(lines)) if lines[k].startswith(".end method"))
        body = [x.strip() for x in lines[i + 1:e] if x.strip()]
        if body != [".locals 1", 'const-string/jumbo p0, "security.securehw.available"', "const/4 v0, 0x0",
                    "invoke-static {p0, v0}, Landroid/os/SystemProperties;->getBoolean(Ljava/lang/String;Z)Z",
                    "move-result p0", "return p0"]:
            sys.exit(f"{path}: isSupportWeaver() is not the expected property read")
        lines[i + 1:e] = ["    .locals 1", "", "    # OneOS One UI 9.5: no securehw (Hermes weaver reads) in the guest; software protectors only.",
                          "    const/4 p0, 0x0", "", "    return p0"]
        open(path, "w").write("\n".join(lines))
        print(f"{os.path.relpath(path, root)}: isSupportWeaver() returns false", file=sys.stderr)
        out.add(os.path.relpath(path, root).split(os.sep)[0])
    return out


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
        is_conn = False
        if not heads:
            heads = connection_lookup(path, lines, root)
            is_conn = bool(heads)
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
        what = "getWeaverService() returns null" if is_conn else "getWeaverServiceLocked() returns null"
        print(f"{os.path.relpath(path, root)}: {what}", file=sys.stderr)
    if changed:
        changed |= samsung_no_securehw(root)
    if not changed:
        sys.exit("SyntheticPasswordManager not found")
    for d in sorted(changed):
        print(d)


if __name__ == "__main__":
    main(sys.argv[1])
