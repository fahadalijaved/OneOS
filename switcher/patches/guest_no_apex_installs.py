"""Never let the guest's package manager change the phone's APEX state.

The container shares the host's apexd: the guest's "apexservice" is One UI's,
and apexd keeps its state in One UI's /data/apex and acts on One UI's /apex.
Whatever the guest's package manager asks of it lands in One UI:

- a staged session (a Play system update / Mainline train accepted in the
  Pixel or ColorOS guest) is submitted, marked ready and then activated by
  One UI's apexd at the phone's next boot, with the guest's modules in place
  of One UI's own (or a failed activation and a revert, at best);
- a rebootless install (installPackage) activates the guest's APEX in the
  host's /apex at once;
- revertActiveSessions and abortStagedSession revert or drop One UI's own
  pending module updates, and markStagedSessionSuccessful / markBootCompleted
  tell apexd that One UI booted fine with a session it never booted;
- the rollback helper snapshots, restores or deletes the apexdata snapshots
  of One UI's users (snapshotCeData, restoreCeData, destroy*Snapshots), and
  reserveSpaceForCompressedApex allocates files in One UI's /data/apex.

A broken APEX state can stop One UI from booting. It is the weaver problem
again (guest_no_weaver.py), for the system's modules.

ApexManager$ApexManagerImpl (services.jar) is the guest framework's only
client of apexd that changes its state (BinaryTransparencyService only reads
the package list), so in it:

1. isApexSupported() returns false: PackageInstallerService refuses APEX
   sessions when they are created ("This device doesn't support the
   installation of APEX files"), and StagingManager's failed-checkpoint path
   no longer asks for a revert.
2. Every state-changing method returns at entry, after a log line, and
   apexd is never called:
   - the void ones (markStagedSessionReady, markStagedSessionSuccessful,
     markBootCompleted, reserveSpaceForCompressedApex) return;
   - the boolean ones (abortStagedSession, revertActiveSessions,
     snapshotCeData, restoreCeData, destroyDeSnapshots, destroyCeSnapshots,
     destroyCeSnapshotsNotSpecified, uninstallApex) return false, which their
     callers already take as "apexd refused" (logged; no reboot);
   - submitStagedSession and installPackage throw the
     PackageManagerException(int, String) they already throw when apexd
     refuses, with the same error code, and the session fails with "OneOS:
     APEX changes are the phone's; not from the guest".
   The reads stay (active and all packages, sessions, staged session info,
   staged APEX infos, the size a compressed APEX would need): the guest's
   package manager scans the APEXes apexd reports, and none of them changes
   anything.

Fail closed: every IApexService call in ApexManagerImpl must be a known read
or sit in a method that now returns at entry; no other class may make a call
that is not a known read; ApexManager must declare these methods abstract
and have ApexManagerImpl as its only subclass, so no other code reaches apexd.

Pixel's services.jar (R8) has the same methods as public, with p registers and
.locals 0 in some of them (destroyCeSnapshots, uninstallApex, ...); ColorOS's
has package-private ones with .param/.local debug info and Throws
annotations. The early return goes after those directives and uses only v
registers, before any parameter is touched; where .locals is lower than the
registers it needs, .locals is raised to that (the parameters move up, which
smali takes care of; the total stays within 16 registers).

One UI 9.5 (S948BXXU6ZZKN, R8): ApexManager keeps only abortStagedSession,
markStagedSessionSuccessful, revertActiveSessions and submitStagedSession, and ApexManagerImpl
has no isApexSupported() (the check is gone), installPackage, markStagedSessionReady,
markBootCompleted, uninstallApex, the snapshot methods or reserveSpaceForCompressedApex: R8 inlined
them into their callers, which now call IApexService themselves. That shape (SAMSUNG_TARGETS,
none of the other methods declared) gets the early returns above for its four methods, and each
other state-changing IApexService call is found by name and must be exactly the known one
(SAMSUNG_SITES): ten calls in PackageSessionVerifier, StagingManager$Lifecycle,
PackageManagerInternalImpl, RecoverySystemService, RollbackManagerServiceImpl (and its lambda),
AppDataRollbackHelper and InstallingSession. Nine are void and become a nop (their callers
only log on failure). installAndActivatePackage in InstallingSession (the rebootless
install) throws an Exception instead, which the call's own handler turns into
PackageManagerException(-110, message), the error it gives when apexd refuses. APEX sessions
still fail at submitStagedSession (-22). Any other state-changing call, or a site that does
not look as expected, stops with nothing written.

Usage: guest_no_apex_installs.py <smali root dir>
Prints the smali_* directory (dex file) it changed.
"""
import os
import re
import sys

BASE = "Lcom/android/server/pm/ApexManager;"
IMPL = "Lcom/android/server/pm/ApexManager$ApexManagerImpl;"
APEXD = "Landroid/apex/IApexService;"
PME = "Lcom/android/server/pm/PackageManagerException;"
PME_INIT = f"{PME}-><init>(ILjava/lang/String;)V"
WHY = "APEX changes are the phone's; not from the guest"
MSG = f"OneOS: {WHY}"

# State-changing ApexManager methods and what each does at entry now.
RETURN_VOID = (
    "markStagedSessionReady(I)V",
    "markStagedSessionSuccessful(I)V",
    "markBootCompleted()V",
    "reserveSpaceForCompressedApex(Landroid/apex/CompressedApexInfoList;)V",
)
RETURN_FALSE = (
    "abortStagedSession(I)Z",
    "revertActiveSessions()Z",
    "snapshotCeData(IILjava/lang/String;)Z",
    "restoreCeData(IILjava/lang/String;)Z",
    "destroyDeSnapshots(I)Z",
    "destroyCeSnapshots(II)Z",
    "destroyCeSnapshotsNotSpecified(I[I)Z",
    "uninstallApex(Ljava/lang/String;)Z",
)
# The error code each one already throws with when apexd refuses:
# INSTALL_FAILED_VERIFICATION_FAILURE (-22), INSTALL_FAILED_INTERNAL_ERROR (-110).
THROW = {
    "submitStagedSession(Landroid/apex/ApexSessionParams;)Landroid/apex/ApexInfoList;": "-0x16",
    "installPackage(Ljava/io/File;Z)Landroid/apex/ApexInfo;": "-0x6e",
}
UNSUPPORTED = "isApexSupported()Z"
TARGETS = (UNSUPPORTED,) + RETURN_VOID + RETURN_FALSE + tuple(THROW)
# One UI 9.5 (S948BXXU6ZZKN): what R8 left of ApexManager.
SAMSUNG_TARGETS = ("abortStagedSession(I)Z", "markStagedSessionSuccessful(I)V", "revertActiveSessions()Z",
                   "submitStagedSession(Landroid/apex/ApexSessionParams;)Landroid/apex/ApexInfoList;")
# The state-changing IApexService calls R8 inlined out of ApexManagerImpl, by (file, call);
# each must be found exactly once. "drop": a void call (nop); "throw": installAndActivatePackage.
SAMSUNG_SITES = {
    ("PackageSessionVerifier.smali", "markStagedSessionReady"): "drop",
    ("StagingManager$Lifecycle.smali", "markBootCompleted"): "drop",
    ("PackageManagerService$PackageManagerInternalImpl.smali", "unstagePackages"): "drop",
    ("RecoverySystemService.smali", "reserveSpaceForCompressedApex"): "drop",
    ("RollbackManagerServiceImpl.smali", "destroyDeSnapshots"): "drop",
    ("RollbackManagerServiceImpl.smali", "destroyCeSnapshots"): "drop",
    ("RollbackManagerServiceImpl$$ExternalSyntheticLambda", "destroyCeSnapshotsNotSpecified"): "drop",
    ("AppDataRollbackHelper.smali", "restoreCeData"): "drop",
    ("AppDataRollbackHelper.smali", "snapshotCeData"): "drop",
    ("InstallingSession.smali", "installAndActivatePackage"): "throw",
}

# IApexService calls that only read apexd's state. Any other call is taken as
# state-changing and must be in a method that returns at entry.
READS = {"getActivePackages", "getAllPackages", "getActivePackage", "getSessions",
         "getStagedSessionInfo", "getStagedApexInfos", "calculateSizeForCompressedApex"}

HEADER = re.compile(r"^\.method ((?:[a-z-]+ )*)([^\s(]+\([^)]*\)\S+)$")
CONCRETE = {"private", "public", "protected", "final", "synchronized", "declared-synchronized"}
CALL = re.compile(r"^\s*invoke-interface(?:/range)? \{[^}]*\}, " + re.escape(APEXD) + r"->(\w+)\(")
ANY_CALL = re.compile(re.escape(APEXD) + r"->(\w+)\(")


def methods(lines, path):
    """{signature: [(header index, .end method index, modifiers)]}"""
    found = {}
    for i, line in enumerate(lines):
        m = HEADER.match(line)
        if not m:
            continue
        end = next((k for k in range(i + 1, len(lines)) if lines[k] == ".end method"), None)
        if end is None:
            sys.exit(f"{path}: {m.group(2)} has no .end method")
        found.setdefault(m.group(2), []).append((i, end, set(m.group(1).split())))
    return found


def param_registers(sig):
    """Registers the parameters take, `this` included."""
    params = sig[sig.index("(") + 1:sig.index(")")]
    n, i = 1, 0
    while i < len(params):
        if params[i] in "JD":
            n += 2
            i += 1
            continue
        while params[i] == "[":
            i += 1
        i = params.index(";", i) + 1 if params[i] == "L" else i + 1
        n += 1
    return n


def entry(lines, head, end, path, sig):
    """(index of .locals, its value, index of the first code line) of a method."""
    j = head + 1
    loc = None
    while j < end:
        s = lines[j].strip()
        if s.startswith(".locals "):
            loc = j
        elif s.startswith(".registers "):
            sys.exit(f"{path}: {sig} uses .registers, expected .locals")
        elif s.startswith(".annotation"):
            while lines[j].strip() != ".end annotation":
                j += 1
        elif s and not s.startswith((".param", ".end param")):
            break
        j += 1
    m = re.match(r"^\s*\.locals (\d+)$", lines[loc]) if loc is not None else None
    if not m or j >= end:
        sys.exit(f"{path}: unexpected {sig} header")
    return loc, int(m.group(1)), j


def early_return(sig):
    """(registers needed, smali lines using v0..vN) for a target method."""
    name = sig[:sig.index("(")]
    log = [
        '    const-string v0, "ApexManager"',
        "",
        f'    const-string v1, "OneOS: {name}() {"refused" if sig in THROW else "skipped"}: {WHY}"',
        "",
        "    invoke-static {v0, v1}, Landroid/util/Slog;->w(Ljava/lang/String;Ljava/lang/String;)I",
        "",
    ]
    head = [f"    # OneOS: apexd is the phone's (One UI's); {name}() never reaches it from the guest."]
    if sig == UNSUPPORTED:
        return 1, ["    # OneOS: no APEX sessions in the guest; apexd is the phone's (One UI's).",
                   "    const/4 v0, 0x0", "", "    return v0", ""]
    if sig in RETURN_VOID:
        return 2, head + log + ["    return-void", ""]
    if sig in RETURN_FALSE:
        return 2, head + log + ["    const/4 v0, 0x0", "", "    return v0", ""]
    return 3, head + log + [
        f"    new-instance v0, {PME}",
        "",
        f"    const/16 v1, {THROW[sig]}",
        "",
        f'    const-string v2, "{MSG}"',
        "",
        f"    invoke-direct {{v0, v1, v2}}, {PME_INIT}",
        "",
        "    throw v0",
        "",
    ]


def samsung_sites(root, foreign_at):
    """Check the inlined state-changing IApexService calls (One UI 9.5 shape); return a function
    that patches them, to run after everything else has been checked."""
    CALLRE = re.compile(r"^(\s*)invoke-interface \{([vp]\d+)(?:, ([vp]\d+))?(?:, [vp]\d+)*\}, "
                        + re.escape(APEXD) + r"->(\w+)\(([^)]*)\)(\S+)\s*$")
    seen = {}
    for path, name in foreign_at:
        b = os.path.basename(path)
        if b.startswith("RollbackManagerServiceImpl$$ExternalSyntheticLambda"):
            b = "RollbackManagerServiceImpl$$ExternalSyntheticLambda"
        key = (b, name)
        if key not in SAMSUNG_SITES:
            sys.exit(f"{os.path.relpath(path, root)}: IApexService.{name} is not a known inlined call")
        seen.setdefault(key, []).append(path)
    for key in SAMSUNG_SITES:
        if len(seen.get(key, [])) != 1:
            sys.exit(f"expected IApexService.{key[1]} once in {key[0]}, found {len(seen.get(key, []))}")
    plan = []
    texts = {}
    for (base, name), path in ((k, v[0]) for k, v in seen.items()):
        if path not in texts:
            with open(path) as f:
                texts[path] = f.read().split("\n")
        lines = texts[path]
        idx = [i for i, l in enumerate(lines) if CALLRE.match(l) and CALLRE.match(l).group(4) == name]
        if len(idx) != 1:
            sys.exit(f"{os.path.relpath(path, root)}: IApexService.{name} call not found as expected")
        plan.append((path, lines, idx[0], name, SAMSUNG_SITES[(base, name)]))
        m = CALLRE.match(lines[idx[0]])
        if SAMSUNG_SITES[(base, name)] == "drop":
            if m.group(6) != "V":
                sys.exit(f"{os.path.relpath(path, root)}: IApexService.{name} is not void")
        else:
            # installAndActivatePackage(String, Z) -> ApexInfo, then move-result-object
            nxt = next(l.strip() for l in lines[idx[0] + 1:] if l.strip() and not l.strip().startswith(".line"))
            if m.group(6) != "Landroid/apex/ApexInfo;" or not re.match(r"move-result-object [vp]\d+$", nxt) \
                    or not m.group(3) or not m.group(2).startswith("v") or not m.group(3).startswith("v"):
                sys.exit(f"{os.path.relpath(path, root)}: IApexService.{name} call not as expected")
            if not any(re.match(r"^\s*\.catch Ljava/lang/Exception; \{:try_start_\d+ \.\. :try_end_\d+\} :catch_\d+$", l)
                       for l in lines[idx[0]:idx[0] + 20]):
                sys.exit(f"{os.path.relpath(path, root)}: IApexService.{name} is not covered by a catch of Exception")

    def apply():
        for path, lines, i, name, kind in plan:
            m = CALLRE.match(lines[i])
            ind = m.group(1)
            if kind == "drop":
                lines[i] = (f"{ind}# OneOS: IApexService.{name} dropped (apexd is the phone's, One UI's)\n"
                            f"{ind}nop")
            else:
                svc, arg = m.group(2), m.group(3)
                j = next(k for k in range(i + 1, len(lines)) if lines[k].strip() and not lines[k].strip().startswith(".line"))
                lines[j] = f"{ind}nop"
                lines[i] = (f"{ind}# OneOS: no rebootless APEX install from the guest (apexd is the phone's, One UI's);\n"
                            f"{ind}# the call's own handler turns this into PackageManagerException(-110, message).\n"
                            f"{ind}new-instance {svc}, Ljava/lang/Exception;\n\n"
                            f'{ind}const-string {arg}, "{MSG}"\n\n'
                            f"{ind}invoke-direct {{{svc}, {arg}}}, Ljava/lang/Exception;-><init>(Ljava/lang/String;)V\n\n"
                            f"{ind}throw {svc}")
            print(f"{os.path.relpath(path, root)}: IApexService.{name}: {kind}", file=sys.stderr)
        for path, lines in texts.items():
            with open(path, "w") as f:
                f.write("\n".join(lines))
        return {os.path.relpath(path, root).split(os.sep)[0] for path in texts}
    return apply


def main(root):
    classes = {BASE: [], IMPL: []}
    foreign = []
    foreign_at = []
    for dirpath, _, files in os.walk(root):
        for name in files:
            if not name.endswith(".smali"):
                continue
            path = os.path.join(dirpath, name)
            with open(path) as f:
                text = f.read()
            cls = re.match(r"^\.class (?:[a-z-]+ )*(L\S+;)$", text.split("\n", 1)[0])
            cls = cls.group(1) if cls else None
            if cls in classes:
                classes[cls].append(path)
                if cls == IMPL:
                    continue  # its own calls are classified below
            if "ApexManager" in text and cls not in classes:
                sup = re.search(r"^\.super (\S+)$", text, re.M)
                if sup and sup.group(1) in (BASE, IMPL):
                    sys.exit(f"{os.path.relpath(path, root)}: {cls} extends {sup.group(1)}, "
                             "expected ApexManagerImpl to be ApexManager's only subclass")
            if APEXD + "->" in text and not (cls or "").startswith("Landroid/apex/"):
                for m in ANY_CALL.finditer(text):
                    if m.group(1) not in READS:
                        foreign.append(f"{os.path.relpath(path, root)}: IApexService.{m.group(1)}")
                        foreign_at.append((path, m.group(1)))
    for cls, paths in classes.items():
        if len(paths) != 1:
            sys.exit(f"{cls} found {len(paths)} times, expected once")

    # ApexManager declares, ApexManagerImpl implements: no other body to guard.
    base_path = classes[BASE][0]
    with open(base_path) as f:
        base = methods(f.read().split("\n"), base_path)
    targets = TARGETS
    samsung = False
    path = classes[IMPL][0]
    if not all(len(base.get(sig, [])) == 1 and "abstract" in base[sig][0][2] for sig in TARGETS):
        with open(path) as f:
            impl_sigs = methods(f.read().split("\n"), path)
        extra = [sig for sig in TARGETS if sig not in SAMSUNG_TARGETS]
        if all(len(base.get(sig, [])) == 1 and "abstract" in base[sig][0][2] for sig in SAMSUNG_TARGETS) and \
                not any(sig in base or sig in impl_sigs for sig in extra):
            samsung = True
            targets = SAMSUNG_TARGETS
    apply_sites = None
    if samsung:
        apply_sites = samsung_sites(root, foreign_at)
    elif foreign:
        sys.exit("state-changing apexd calls outside ApexManagerImpl:\n  " + "\n  ".join(foreign))
    for sig in targets:
        found = base.get(sig, [])
        if len(found) != 1 or "abstract" not in found[0][2]:
            sys.exit(f"{os.path.relpath(base_path, root)}: {sig} not declared abstract exactly once")

    path = classes[IMPL][0]
    rel = os.path.relpath(path, root)
    with open(path) as f:
        lines = f.read().split("\n")
    if any(l.strip().startswith(("# OneOS: apexd is the phone's", "# OneOS: no APEX sessions in the guest")) for l in lines):
        sys.exit(f"{rel}: already patched")
    if f".super {BASE}" not in lines:
        sys.exit(f"{rel}: does not extend ApexManager")
    impl = methods(lines, rel)

    # Every apexd call is a read, or in a method that returns at entry now.
    sig = None
    for line in lines:
        if line.startswith(".method "):
            m = HEADER.match(line)
            sig = m.group(2) if m else line
            continue
        if APEXD + "->" not in line:
            continue
        m = CALL.match(line)
        if not m:
            sys.exit(f"{rel}: {sig}: unexpected apexd call {line.strip()!r}")
        if m.group(1) in READS:
            kind = "read, kept"
        elif sig in targets:
            kind = "state-changing, method returns at entry"
        else:
            sys.exit(f"{rel}: {sig} calls IApexService.{m.group(1)}, which is not a known read")
        print(f"{rel}: {sig.split('(')[0]} -> IApexService.{m.group(1)}: {kind}", file=sys.stderr)

    # Insert from the bottom up, so the indices found above stay valid.
    sites = []
    for sig in targets:
        found = impl.get(sig, [])
        if len(found) != 1:
            sys.exit(f"{rel}: {sig} found {len(found)} times, expected once")
        head, end, mods = found[0]
        if not mods <= CONCRETE:
            sys.exit(f"{rel}: {sig} has unexpected modifiers {sorted(mods)}")
        if sig in THROW:
            body = lines[head:end]
            if not any(l.strip().startswith("invoke-direct {") and l.rstrip().endswith(PME_INIT) for l in body):
                sys.exit(f"{rel}: {sig} does not throw PackageManagerException(int, String)")
            if not any(re.match(rf"^\s*const/16 [vp]\d+, {THROW[sig]}$", l) for l in body):
                sys.exit(f"{rel}: {sig} does not use error code {THROW[sig]}")
        sites.append((head, end, sig))
    for head, end, sig in sorted(sites, reverse=True):
        loc, count, j = entry(lines, head, end, rel, sig)
        need, code = early_return(sig)
        if count < need:
            if need + param_registers(sig) > 16:
                sys.exit(f"{rel}: {sig}: no room for {need} registers")
            lines[loc] = re.sub(r"\d+$", str(need), lines[loc])
        lines[j:j] = code
    with open(path, "w") as f:
        f.write("\n".join(lines))
    extra_dirs = set()
    if apply_sites:
        extra_dirs = apply_sites()
        print(f"{rel}: {len(targets)} state-changing methods return at entry (no isApexSupported here)",
              file=sys.stderr)
    else:
        print(f"{rel}: isApexSupported() false, {len(TARGETS) - 1} state-changing methods return at entry",
              file=sys.stderr)
    for d in sorted({rel.split(os.sep)[0]} | extra_dirs):
        print(d)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: guest_no_apex_installs.py <smali root dir>")
    main(sys.argv[1])
