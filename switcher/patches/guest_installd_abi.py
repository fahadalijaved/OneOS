"""Make the guest's installd calls match the host installd's interface.

The guest framework talks to One UI's installd over the shared servicemanager,
and binder dispatches by transaction code. ColorOS's IInstalld differs from
Samsung's: it has clearAppDataWithPreservedCacheEntries at code 10 and two
OPPO methods at 51/52, so from code 10 on nearly every guest call reached a
different host method (the guest's destroyAppData arrived as destroyPccData,
rmPackageDir as freeCache). In run 25 most of them only failed because the
arguments did not parse.

In OneOS's copy of the guest's IInstalld$Stub$Proxy (services.jar):
- methods the host has with the same signature, and that only create, query,
  relabel or compile, are sent with the HOST's code;
- every other method throws RemoteException before transact(): all deleting,
  clearing, moving and snapshot calls, methods the host does not have, and
  anything new that is not listed below (fail closed). The callers already
  handle installd failures.

The copy is com.android.server.pm.OneOSInstalldProxy, and every
IInstalld.Stub.asInterface() call in services.jar (and, with --callers, in
oplus-services.jar) goes to its asInterface(). Patching
android.os.IInstalld$Stub$Proxy in place did nothing: ColorOS's framework.jar,
on the boot class path, has its own android.os.IInstalld, and system_server's
class loader asks the boot class path first. Runs 26-29 still sent ColorOS's
codes: invalidateMounts arrived as the host's isQuotaSupported ("error -61"),
isQuotaSupported as prepareAppProfile (NullPointerException), and Settings >
About crashed on the null storage size that followed.

(StorageStatsService.isQuotaSupported itself is made to return false by
guest_storage_guards.py, so free space comes from statfs.)

0.5.28: the codes are THIS phone's, read at runtime. One UI 9.5 renumbered IInstalld (67 methods,
85 on One UI 9.0, only 6 kept their code), so a code baked in at build time was right on one One UI
only. Each allowed method now loads its row number and calls OneOSInstalldCodes.code(row)
(patches/OneOSInstalldCodes.java), which answers this phone's code from
/data/system/oneos_installd_codes (guest_prepare.sh, from the stage's verified host_installd.table)
by name and signature, and throws RemoteException when the phone has no such method. The host table
argument is only reported against now.

Usage: guest_installd_abi.py <smali root dir> <host table>   (services.jar)
       guest_installd_abi.py --callers <smali root dir>      (oplus-services.jar)
       guest_installd_abi.py --retrofit <smali root dir>     (a services_patched.jar built before 0.5.28)
(the host table comes from scripts/host-installd-table.sh)
Prints the smali_* directories it changed, one per line.
"""
import os
import re
import sys

# Sent to the host when it has the same method with the same signature.
ALLOWED = {
    "createUserData", "setFirstBoot", "createAppData", "createAppDataBatched",
    "restoreconAppData", "fixupAppData", "getAppSize", "getUserSize",
    "getExternalSize", "getAppCrates", "getUserCrates",
    "controlDexOptBlocking", "mergeProfiles", "dumpProfiles", "copySystemProfile",
    "createProfileSnapshot", "linkNativeLibraryDirectory", "createOatDirs",
    "linkFile", "hashSecondaryDexFile", "invalidateMounts", "isQuotaSupported",
    "prepareAppProfile", "tryMountDataMirror", "getOdexVisibility",
    "createFsveritySetupAuthToken", "enableFsverity",
}
PROXY = os.path.join("android", "os", "IInstalld$Stub$Proxy.smali")
STUB = os.path.join("android", "os", "IInstalld$Stub.smali")
INSTALLER = os.path.join("com", "android", "server", "pm", "Installer.smali")
TRANSACT = re.compile(r"^\s*invoke-interface \{([vp]\d+), ([vp]\d+), ([vp]\d+), ([vp]\d+), ([vp]\d+)\}, "
                      r"Landroid/os/IBinder;->transact\(ILandroid/os/Parcel;Landroid/os/Parcel;I\)Z\s*$")

PROXY_DESC = "Landroid/os/IInstalld$Stub$Proxy;"
OWN = "Lcom/android/server/pm/OneOSInstalldProxy;"
CODES = "Lcom/android/server/pm/OneOSInstalldCodes;"
CODES_SMALI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OneOSInstalldCodes.smali")
PLACEHOLDER = '"@@ONEOS_INSTALLD_TABLE@@"'
BLOCK_MARK = "# OneOS: not sent to the host installd"
AS_INTERFACE = "->asInterface(Landroid/os/IBinder;)Landroid/os/IInstalld;"
STUB_CALL = re.compile(r"^(\s*invoke-static(?:/range)? \{[^}]*\}, )Landroid/os/IInstalld\$Stub;"
                       + re.escape(AS_INTERFACE) + r"\s*$")
OWN_AS_INTERFACE = f""".method public static asInterface(Landroid/os/IBinder;)Landroid/os/IInstalld;
    .locals 1

    # OneOS: the host installd is only reached through this class.
    if-nez p0, :oneos_binder

    const/4 v0, 0x0

    return-object v0

    :oneos_binder
    new-instance v0, {OWN}

    invoke-direct {{v0, p0}}, {OWN}-><init>(Landroid/os/IBinder;)V

    return-object v0
.end method
"""


def find(root, suffix):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
            if os.path.join(d, f).endswith(os.sep + suffix)]
    if len(hits) != 1:
        sys.exit(f"expected exactly one {suffix}, found {len(hits)}")
    return hits[0]


def top_dir(root, path):
    return os.path.relpath(path, root).split(os.sep)[0]


def own_class(lines):
    """The patched proxy as a public top-level class that the boot class path does not have."""
    text = "\n".join(lines)
    text = re.sub(r"^\.annotation system Ldalvik/annotation/(?:EnclosingClass|InnerClass);\n.*?^\.end annotation\n",
                  "", text, flags=re.S | re.M)
    first = text.split("\n", 1)[0]
    if not re.match(r"^\.class (?:public )?(?:final )?" + re.escape(PROXY_DESC) + "$", first):
        sys.exit(f"IInstalld$Stub$Proxy: unexpected class line {first!r}")
    text = text.replace(first, f".class public final {OWN}", 1)
    text = text.replace(PROXY_DESC, OWN)
    if "Ldalvik/annotation/InnerClass;" in text or "IInstalld$Stub$Proxy" in text:
        sys.exit("IInstalld$Stub$Proxy: references left in OneOSInstalldProxy")
    # One UI 9.5 (S948BXXU6ZZKN): R8 dropped the proxy's constructor; Stub.asInterface makes the
    # object with Object.<init> and sets mRemote itself. The copy gets the constructor back, the
    # one OWN_AS_INTERFACE calls (without it system_server died at Installer.connect, A36 run 3).
    if f".method public constructor <init>(Landroid/os/IBinder;)V" not in text and \
            f".method constructor <init>(Landroid/os/IBinder;)V" not in text:
        if text.count(".field public mRemote:Landroid/os/IBinder;") != 1 or \
                any(l.startswith(".method") and "<init>" in l for l in text.split("\n")):
            sys.exit("IInstalld$Stub$Proxy: no <init>(IBinder) and not the One UI shape (one mRemote field, no constructor)")
        text = text.rstrip("\n") + f"""

.method public constructor <init>(Landroid/os/IBinder;)V
    .locals 0

    invoke-direct {{p0}}, Ljava/lang/Object;-><init>()V

    iput-object p1, p0, {OWN}->mRemote:Landroid/os/IBinder;

    return-void
.end method
"""
        print("OneOSInstalldProxy: <init>(IBinder) added (the proxy has no constructor in this build)", file=sys.stderr)
    return text.rstrip("\n") + "\n\n" + OWN_AS_INTERFACE


def redirect_callers(root):
    """Every IInstalld.Stub.asInterface() call goes to OneOSInstalldProxy.asInterface()."""
    dirs, total, files = set(), 0, []
    for dirpath, _, names in os.walk(root):
        for name in names:
            if not name.endswith(".smali"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            if rel.split(os.sep, 1)[-1].startswith(os.path.join("android", "os", "IInstalld")):
                continue  # the AIDL classes themselves (shadowed by the boot class path)
            with open(path) as f:
                lines = f.read().split("\n")
            hits = 0
            for i, line in enumerate(lines):
                m = STUB_CALL.match(line)
                if m:
                    lines[i] = m.group(1) + OWN + AS_INTERFACE
                    hits += 1
            text = "\n".join(lines)
            # Fail closed: nothing may reach installd through the boot class path's proxy.
            if "Landroid/os/IInstalld$Stub;->asInterface" in text or PROXY_DESC + "-><init>" in text:
                sys.exit(f"{rel}: IInstalld proxy reference not redirected")
            if hits:
                with open(path, "w") as f:
                    f.write(text)
                dirs.add(top_dir(root, path))
                files.append(rel)
                total += hits
                print(f"{rel}: IInstalld.Stub.asInterface -> OneOSInstalldProxy ({hits})", file=sys.stderr)
    print(f"IInstalld: {total} asInterface calls redirected", file=sys.stderr)
    return dirs, files


def runtime_code(lines, i, end, row):
    """The const feeding transact's code in lines[i:end] becomes OneOSInstalldCodes.code(row). Returns the line count added."""
    t = [j for j in range(i, end) if TRANSACT.match(lines[j])]
    if len(t) != 1:
        sys.exit(f"{lines[i]}: {len(t)} transact calls")
    reg = TRANSACT.match(lines[t[0]]).group(2)
    rx = re.compile(rf"^\s*const(?:/4|/16)? {reg}, ")
    cs = [j for j in range(t[0] - 1, i, -1) if rx.match(lines[j])]
    if not cs or any(re.search(rf"\b{reg}\b", lines[j]) for j in range(cs[0] + 1, t[0])):
        sys.exit(f"{lines[i]}: no single constant feeds transact's code")
    lines[cs[0]:cs[0] + 1] = [
        f"    const/16 {reg}, 0x{row:x}",
        "",
        "    # OneOS: this phone's installd code (OneOSInstalldCodes).",
        f"    invoke-static/range {{{reg} .. {reg}}}, {CODES}->code(I)I",
        "",
        f"    move-result {reg}",
    ]
    return 5


def write_codes(dirname, rows):
    """OneOSInstalldCodes next to OneOSInstalldProxy, its table the proxy's rows ("name signature")."""
    dst = os.path.join(dirname, "OneOSInstalldCodes.smali")
    if os.path.exists(dst):
        sys.exit(f"{dst} exists already")
    text = open(CODES_SMALI).read()
    if text.count(PLACEHOLDER) != 1:
        sys.exit("OneOSInstalldCodes.smali: the table placeholder is not there once")
    for r in rows:
        if not re.match(r"^\w+ \([^\s()]*\)\S+$", r) or '"' in r or "\\" in r:
            sys.exit(f"bad table row {r!r}")
    with open(dst, "w") as f:
        f.write(text.replace(PLACEHOLDER, '"' + "\\n".join(rows) + '"'))
    return dst


def retrofit(root):
    """A services_patched.jar of an older build: its OneOSInstalldProxy's baked codes become runtime ones."""
    path = find(root, os.path.join("com", "android", "server", "pm", "OneOSInstalldProxy.smali"))
    lines = open(path).read().split("\n")
    if any(CODES in l for l in lines):
        sys.exit("OneOSInstalldProxy already reads its codes at runtime")
    rows, blocked = [], []
    i = 0
    while i < len(lines):
        m = re.match(r"^\.method public (?:final )?(\w+)(\([^)]*\)\S+)$", lines[i])
        if not m:
            i += 1
            continue
        name, sig = m.groups()
        end = next(j for j in range(i, len(lines)) if lines[j] == ".end method")
        body = lines[i:end]
        if not any(TRANSACT.match(l) for l in body):
            i = end + 1
            continue
        if any(f'"OneOS: installd.{name} blocked in the container"' in l for l in body):
            blocked.append(name)
        else:
            if name not in ALLOWED:
                sys.exit(f"{name}: sent by the old proxy but not allowed")
            end += runtime_code(lines, i, end, len(rows))
            rows.append(f"{name} {sig}")
        i = end + 1
    if not rows or "createAppData" not in [r.split()[0] for r in rows]:
        sys.exit("OneOSInstalldProxy: unexpected methods")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    write_codes(os.path.dirname(path), rows)
    print(f"IInstalld (retrofit): {len(rows)} methods with this phone's codes, {len(blocked)} blocked", file=sys.stderr)
    print("  runtime: " + ", ".join(r.split()[0] for r in rows), file=sys.stderr)
    print(top_dir(root, path))


def main(root, table):
    host = {}
    for line in open(table):
        if line.startswith("#") or not line.strip():
            continue
        name, code, sig = line.split()
        host[name] = (int(code), sig)
    guest_codes = {m.group(1): int(m.group(2), 16) for m in re.finditer(
        r"^\.field static final TRANSACTION_(\w+):I = 0x([0-9a-f]+)", open(find(root, STUB)).read(), re.M)}

    path = find(root, PROXY)
    lines = open(path).read().split("\n")
    remapped, blocked, kept, rows = [], [], [], []
    i = 0
    while i < len(lines):
        m = re.match(r"^\.method public (?:final )?(\w+)(\([^)]*\)\S+)$", lines[i])
        if not m or m.group(1) not in guest_codes:
            i += 1
            continue
        name, sig = m.groups()
        end = next(j for j in range(i, len(lines)) if lines[j] == ".end method")
        h = host.get(name)
        if name in ALLOWED:
            # The code register loaded just before transact() gets this phone's code at runtime.
            end += runtime_code(lines, i, end, len(rows))
            rows.append(f"{name} {sig}")
            if h and h[1] == sig:
                (kept if h[0] == guest_codes[name] else remapped).append(
                    name if h[0] == guest_codes[name] else f"{name} 0x{guest_codes[name]:x}->0x{h[0]:x}")
            else:
                kept.append(name)
                print(f"  {name}{sig}: not in {os.path.basename(table)} with this signature (sent only where the phone has it)",
                      file=sys.stderr)
        else:
            # Throw before any code that could reach the host.
            k = i + 1
            in_annotation = False
            while True:
                s = lines[k].strip()
                if s.startswith(".annotation"):
                    in_annotation = True
                elif s.startswith(".end annotation"):
                    in_annotation = False
                elif s and not in_annotation and not s.startswith((".locals", ".param", ".end param", "#")):
                    break
                k += 1
            locals_ = int(next(re.match(r"\s*\.locals (\d+)", l).group(1) for l in lines[i:end] if l.strip().startswith(".locals")))
            if locals_ < 2:
                sys.exit(f"{name}: needs 2 locals, has {locals_}")
            lines[k:k] = [
                BLOCK_MARK.join(["    ", " (different interface or not allowed)."]),
                "    new-instance v0, Landroid/os/RemoteException;",
                "",
                f'    const-string v1, "OneOS: installd.{name} blocked in the container"',
                "",
                "    invoke-direct {v0, v1}, Landroid/os/RemoteException;-><init>(Ljava/lang/String;)V",
                "",
                "    throw v0",
                "",
            ]
            blocked.append(name)
            end += 9
        i = end + 1

    missing = set(guest_codes) - set(remapped_names := [r.split()[0] for r in remapped]) - set(blocked) - set(kept)
    if missing:
        sys.exit(f"IInstalld methods without a proxy method: {sorted(missing)}")
    if "destroyUserData" not in blocked or "createAppData" not in kept + remapped_names:
        sys.exit("unexpected IInstalld classification")

    # The patched proxy goes next to Installer (classes.dex, where the original
    # lives, is at the 64K method limit), under a name the boot class path lacks.
    installer = find(root, INSTALLER)
    dst = os.path.join(os.path.dirname(installer), "OneOSInstalldProxy.smali")
    if os.path.exists(dst):
        sys.exit(f"{dst} exists already")
    with open(dst, "w") as f:
        f.write(own_class(lines))
    write_codes(os.path.dirname(dst), rows)
    dirs, files = redirect_callers(root)
    if os.path.relpath(installer, root) not in files:
        sys.exit("Installer: IInstalld.Stub.asInterface call not found")
    dirs.add(top_dir(root, installer))
    print(f"IInstalld: {len(kept)} identical, {len(remapped)} remapped, {len(blocked)} blocked"
          f" (in {os.path.relpath(dst, root)})", file=sys.stderr)
    print("  remapped: " + ", ".join(remapped), file=sys.stderr)
    print("  blocked: " + ", ".join(blocked), file=sys.stderr)
    for d in sorted(dirs):
        print(d)


def callers_only(root):
    dirs, _ = redirect_callers(root)
    for d in sorted(dirs):
        print(d)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--callers":
        callers_only(sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "--retrofit":
        retrofit(sys.argv[2])
    elif len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        sys.exit(__doc__)
