"""A Pixel guest's camera binder calls with One UI's transaction codes.

The guest's camera clients talk to One UI's cameraserver, and Samsung's
camera interfaces are not AOSP's (docs/pixel-guest.md, "What differs"):
ICameraService has notifyDeviceStateChangeSync at 23, so createDefaultRequest,
isSessionConfigurationWithParametersSupported, getSessionCharacteristics and
warmUp are 24-27 on Samsung (23-26 on the Pixels); ICameraDeviceUser has
setParameters at 13, so every Pixel method from getInputSurface (13) to
updateOutputConfigurations (28) is one higher. A Pixel session's
createDefaultRequest reached Samsung's getInputSurface. ICameraServiceListener's
9 is Samsung's onCameraDeviceStateChanged; the Pixel 9 Pro XL has
onStatusChangedBatched there and misparsed it ("Allocation of size 7209057").
Its CameraCompatibilityInfo also writes a sixth field, which Samsung read as the
next parcelable's null marker (NullPointerException in getCameraCharacteristics
and connect; "Failed to load metadata for CameraId-2").

Table-driven, like guest_installd_abi.py: the host table is
scripts/aidl-table.py's output for One UI's framework.jar (patches/host_camera.txt:
<interface> <method> <code> <signature>). For every interface in it:
  - the guest's Stub$Proxy: each method the host also has gets the host's code
    (the const feeding IBinder.transact), only when the signatures are equal;
    a host method the guest lacks is left to it (never called); a guest method
    the host lacks goes to UNUSED_CODE when it returns void (ColorOS's
    notifySmartWindowChange, notifyDisplayRotationChange), and when it has a
    result (HyperOS's ICameraService.addFaceListener, 23 on Xiaomi, where One
    UI has notifyDeviceStateChangeSync) the Proxy method throws
    RemoteException at entry: nothing reaches One UI's cameraserver, and the
    caller handles it like a dead service.
  - the guest's Stub.onTransact, for the interfaces the host calls into the
    guest (ICameraServiceListener, ICameraDeviceCallbacks): a guest case whose
    code is a different method on the host is dropped from the packed switch,
    so the host's call is ignored (returns false) instead of misparsed.
  - android.content.res.CameraCompatibilityInfo: a sixth field
    (mShouldOverrideLensFacingFrontToBack) is no longer written or read; the
    five Samsung reads stay as they are.
Every target must match exactly once, or the build stops (fail closed).

Usage: pixel_camera_abi.py <apktool decoded framework.jar dir> <host_camera.txt>
Prints the smali_* directories (dex files) it changed, one per line; prints
"unchanged" to stderr and nothing to stdout when the tables already agree.
"""
import os
import re
import sys

CALLBACK_IFACES = ("android.hardware.ICameraServiceListener", "android.hardware.camera2.ICameraDeviceCallbacks")
# A transaction code none of One UI's camera interfaces uses (the highest is 38).
UNUSED_CODE = 200
# Same name and signature as One UI's, but contents One UI's cameraserver cannot parse: One UI
# 9.5's notifyPkgListParamChange string lists crashed One UI 9.0's cameraserver in
# PackagePolicyList::applyPkgListParamChange (A36 run 9, 5 times). Void; sent to UNUSED_CODE.
NOT_TO_HOST = {"notifyPkgListParamChange"}
# A One UI 9.5 host (0.5.37, ONEOS_CAMERA_KEEP_COMPAT=1 builds) parses One UI 9.5's lists itself.
if os.environ.get("ONEOS_CAMERA_KEEP_COMPAT") == "1":
    NOT_TO_HOST = set()
COMPAT = "android/content/res/CameraCompatibilityInfo.smali"
# One UI 8 hosts (0.5.39, One UI 9.5 on the Galaxy S22: switcher/patches/host_camera_oneui8.txt):
# getCameraInfo, connect, connectDevice, getCameraCharacteristics and getSessionCharacteristics take
# Android 16's int rotationOverride where One UI 9.0/9.5 take a CameraCompatibilityInfo parcelable.
# ONEOS_CAMERA_COMPAT_AS_INT=1: such a method matches when its signature with that parcelable read as
# an int is the host's, and its Proxy writes oneosRotationOverride(info) (0 none, 1 override to
# portrait, 2 rotation only; a static method added to ICameraService$Stub$Proxy, in the same dex: the
# framework's first dex has no room for another method) in the parcelable's place. CameraCompatibilityInfo
# itself is then left as it is (it never reaches the host).
COMPAT_AS_INT = os.environ.get("ONEOS_CAMERA_COMPAT_AS_INT") == "1"
CCI = "Landroid/content/res/CameraCompatibilityInfo;"
OVERRIDE_HELPER = """
.method public static oneosRotationOverride(Landroid/content/res/CameraCompatibilityInfo;)I
    .registers 2

    # OneOS: Android 16's rotationOverride for a One UI 8 cameraserver (pixel_camera_abi.py).
    if-eqz p0, :oneos_none

    invoke-static {p0}, Landroid/content/res/CameraCompatibilityInfo;->isCameraCompatModeActive(Landroid/content/res/CameraCompatibilityInfo;)Z

    move-result v0

    if-eqz v0, :oneos_none

    invoke-virtual {p0}, Landroid/content/res/CameraCompatibilityInfo;->shouldOverrideSensorOrientation()Z

    move-result v0

    if-eqz v0, :oneos_rotation_only

    const/4 v0, 0x1

    return v0

    :oneos_rotation_only
    const/4 v0, 0x2

    return v0

    :oneos_none
    const/4 v0, 0x0

    return v0
.end method
"""


def param_regs(sig):
    """[(p register, type)] of an instance method's arguments (p0 is this; J and D take two)."""
    args = sig[1:sig.index(")")]
    out, i, reg = [], 0, 1
    while i < len(args):
        j = i
        while args[j] == "[":
            j += 1
        if args[j] == "L":
            j = args.index(";", j)
        t = args[i:j + 1]
        out.append((f"p{reg}", t))
        reg += 2 if t in ("J", "D") else 1
        i = j + 1
    return out


def compat_as_int(body, iface, name, gsig):
    """The Proxy body writing oneosRotationOverride(info) as an int where it wrote the parcelable."""
    regs = [r for r, t in param_regs(gsig) if t == CCI]
    if len(regs) != 1:
        die(f"{iface}.{name}: {len(regs)} CameraCompatibilityInfo arguments (one expected)")
    pr = regs[0]
    pat = re.compile(r"^(\s*)invoke-virtual \{([vp]\d+), " + pr + r", [vp]\d+\}, Landroid/os/Parcel;->writeTypedObject\(Landroid/os/Parcelable;I\)V$", re.M)
    hits = pat.findall(body)
    if len(hits) != 1:
        die(f"{iface}.{name}: {len(hits)} writeTypedObject of {pr} (one expected)")
    def rep(m):
        ind, parcel = m.group(1), m.group(2)
        return (f"{ind}# OneOS: One UI 8 takes an int rotationOverride here (pixel_camera_abi.py).\n"
                f"{ind}invoke-static {{{pr}}}, L{iface.replace('.', '/')}$Stub$Proxy;->oneosRotationOverride({CCI})I\n\n"
                f"{ind}move-result {pr}\n\n"
                f"{ind}invoke-virtual {{{parcel}, {pr}}}, Landroid/os/Parcel;->writeInt(I)V")
    return pat.sub(rep, body)


def add_override_helper(text, changed):
    """The Proxy class text with oneosRotationOverride appended (once)."""
    if "oneosRotationOverride(" in text.split(".method public static oneosRotationOverride")[0] and ".method public static oneosRotationOverride" in text:
        return text
    changed.append("ICameraService$Stub$Proxy: oneosRotationOverride added (One UI 8's int rotationOverride)")
    return text.rstrip("\n") + "\n" + OVERRIDE_HELPER
TRANSACT = "Landroid/os/IBinder;->transact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z"
# v registers in R8 builds (Pixel, ColorOS); p registers too in a build with
# debug info (Infinity-X's framework.jar: "const/16 p3, 0x17").
CONST = re.compile(r"^(\s*)const(/4|/16|)\s+([vp]\d+),\s*(-?0x[0-9a-f]+|-?\d+)\s*$")


LOCALS_RE = re.compile(r"^(\s*)\.locals (\d+)$")


def die(msg):
    sys.exit(f"pixel_camera_abi: {msg}")


def read_table(path):
    """{interface: {method: (code, signature)}}"""
    out = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 3)
            if len(parts) != 4:
                die(f"{path}: malformed line '{line}'")
            iface, name, code, sig = parts
            out.setdefault(iface, {})[name] = (int(code), sig)
    return out


def find_smali(root, cls):
    hits = []
    for d in sorted(os.listdir(root)):
        if d.startswith("smali"):
            p = os.path.join(root, d, cls)
            if os.path.isfile(p):
                hits.append(p)
    if len(hits) != 1:
        die(f"{cls} found {len(hits)} times under {root} (one expected)")
    return hits[0]


def method_bodies(text):
    """[(start, end, header_line)] of every method, in file order."""
    out = []
    for m in re.finditer(r"^\.method .*$", text, re.M):
        end = text.find("\n.end method", m.end())
        if end < 0:
            die("method without .end method")
        out.append((m.start(), end, m.group(0)))
    return out


def sig_of(header):
    """The AIDL table's signature shape from a smali method header: name(args)ret."""
    m = re.search(r" ([A-Za-z_$][A-Za-z0-9_$]*)(\([^)]*\)\S+)$", header)
    return (m.group(1), m.group(2)) if m else (None, None)


def refuse_at_entry(body, iface, name):
    """The method body with a RemoteException thrown before anything else (an instance Proxy method)."""
    lines = body.split("\n")
    li = next((i for i, l in enumerate(lines) if LOCALS_RE.match(l)), None)
    if li is None:
        die(f"{iface}.{name}: no .locals line")
    if int(LOCALS_RE.match(lines[li]).group(2)) < 2:
        lines[li] = f"{LOCALS_RE.match(lines[li]).group(1)}.locals 2"
    j = li + 1
    while j < len(lines) and (lines[j].strip() == "" or lines[j].lstrip().startswith((".param", ".end param", ".annotation"))):
        if lines[j].lstrip().startswith(".annotation"):
            j = next(k for k in range(j, len(lines)) if lines[k].strip() == ".end annotation")
        j += 1
    lines[j:j] = [
        "    # OneOS: One UI's camera service has no such method (pixel_camera_abi.py).",
        "    new-instance v0, Landroid/os/RemoteException;",
        f'    const-string v1, "OneOS: {iface}.{name} is not on this phone"',
        "    invoke-direct {v0, v1}, Landroid/os/RemoteException;-><init>(Ljava/lang/String;)V",
        "    throw v0",
        "",
    ]
    return "\n".join(lines)


def patch_proxy(text, iface, host, guest, changed):
    """Renumber the const that feeds transact in each Proxy method."""
    pieces, pos, n = [], 0, 0
    for s, e, header in method_bodies(text):
        name, sig = sig_of(header)
        body = text[s:e]
        if name is None or TRANSACT not in body or name not in guest:
            continue
        gcode, gsig = guest[name]
        if name not in host or name in NOT_TO_HOST:
            # ColorOS adds notifySmartWindowChange and notifyDisplayRotationChange. A void
            # call goes to a code One UI does not have: its Binder answers "unknown
            # transaction" (transact() returns false) and the Proxy goes on. A call with
            # a result would read garbage, so it throws before transact instead (fail closed).
            if not gsig.endswith(")V"):
                pieces.append(text[pos:s]); pieces.append(refuse_at_entry(body, iface, name)); pos = e
                n += 1
                changed.append(f"{iface}.{name}: {gcode} -> RemoteException at entry")
                continue
            hcode, hsig = UNUSED_CODE, gsig
        else:
            hcode, hsig = host[name]
        if hsig == "?":
            die(f"{iface}.{name}: the host table has no signature for it")
        as_int = False
        if hsig != gsig:
            if COMPAT_AS_INT and CCI in gsig and gsig.replace(CCI, "I") == hsig:
                as_int = True
            else:
                die(f"{iface}.{name}: signature differs (host {hsig}, guest {gsig})")
        if hcode == gcode and not as_int:
            continue
        if as_int:
            body = compat_as_int(body, iface, name, gsig)
            changed.append(f"{iface}.{name}: CameraCompatibilityInfo written as One UI 8's int rotationOverride")
        lines = body.split("\n")
        ti = [i for i, l in enumerate(lines) if TRANSACT in l]
        if len(ti) != 1:
            die(f"{iface}.{name}: {len(ti)} transact calls (one expected)")
        regs = re.search(r"invoke-interface \{([^}]*)\}", lines[ti[0]]).group(1).split(", ")
        code_reg = regs[1]
        ci = None
        for i in range(ti[0] - 1, -1, -1):
            m = CONST.match(lines[i])
            if m and m.group(3) == code_reg:
                ci = i
                break
        if ci is None:
            die(f"{iface}.{name}: no const for {code_reg} before transact")
        val = int(lines[ci].split(",")[-1].strip(), 0)
        if val != gcode:
            die(f"{iface}.{name}: const {val} before transact, table says {gcode}")
        if hcode != gcode:
            # const/4 only reaches v0-v15; a p register may sit higher, so it keeps const/16.
            width = "/4" if hcode < 8 and (code_reg.startswith("v") or CONST.match(lines[ci]).group(2) == "/4") else "/16"
            lines[ci] = f"{CONST.match(lines[ci]).group(1)}const{width} {code_reg}, {hex(hcode)}"
            changed.append(f"{iface}.{name}: {gcode} -> {hcode}")
        pieces.append(text[pos:s]); pieces.append("\n".join(lines)); pos = e
        n += 1
    pieces.append(text[pos:])
    return "".join(pieces), n


def patch_stub_switch(text, iface, host, guest, changed):
    """Remap or drop guest onTransact cases whose code differs on the host."""
    by_code_host = {c: (n, sig) for n, (c, sig) in host.items()}
    by_code_guest = {c: (n, sig) for n, (c, sig) in guest.items()}
    # Remap host code c -> guest handler when the host method at c also exists in the guest
    # with the exact same signature at another code (e.g. One UI 8.0's code 9
    # onCameraDeviceStateChanged vs One UI 9.5's code 10), and drop unmatched/stale codes.
    remap = {}
    drop = set()
    for c, (gn, _) in by_code_guest.items():
        if c in by_code_host:
            hn, hsig = by_code_host[c]
            if hn != gn:
                if hn in guest and guest[hn][1] == hsig:
                    remap[c] = (hn, guest[hn][0])
                else:
                    drop.add(c)
        elif gn in host and host[gn][0] != c and host[gn][1] == guest[gn][1]:
            # Moved to host[gn][0]; drop the old guest-only slot so it is not reachable by stale code.
            drop.add(c)
    if not drop and not remap:
        return text, 0
    bodies = [(s, e, h) for s, e, h in method_bodies(text) if " onTransact(" in h]
    if len(bodies) != 1:
        die(f"{iface}: {len(bodies)} onTransact methods (one expected)")
    s, e, _ = bodies[0]
    body = text[s:e]
    m = re.search(r"\.packed-switch (0x[0-9a-f]+|\d+)\n((?:\s*:pswitch_\d+\n)+)\s*\.end packed-switch", body)
    if not m:
        die(f"{iface}.onTransact: no packed switch")
    first = int(m.group(1), 0)
    labels = m.group(2).split()
    codes = {first + i: lab for i, lab in enumerate(labels)}
    for c in sorted(drop | set(remap)):
        if c not in codes:
            die(f"{iface}.onTransact: code {c} not in its switch")
    for c, (hn, gc) in sorted(remap.items()):
        if gc not in codes:
            die(f"{iface}.onTransact: target code {gc} ({hn}) not in its switch")
    resolved = {}
    for c, lab in codes.items():
        if c in remap:
            resolved[c] = codes[remap[c][1]]
        elif c in drop:
            resolved[c] = ":oneos_ignored"
        else:
            resolved[c] = lab
    keep = [(c, lab) for c, lab in sorted(resolved.items()) if lab != ":oneos_ignored"]
    # A packed switch must stay contiguous: dropped codes above the last kept one fall off the end;
    # a dropped code in the middle keeps its slot, pointed at the switch's own fall-through.
    last_kept = max(c for c, _ in keep)
    new = [resolved[c] for c in range(first, last_kept + 1)]
    table = f".packed-switch {m.group(1)}\n" + "".join(f"        {lab}\n" for lab in new) + "    .end packed-switch"
    body = body[:m.start()] + table + body[m.end():]
    if ":oneos_ignored" in table:
        # The fall-through label right after the switch instruction (the default path).
        sw = re.search(r"^(\s*)packed-switch p1, :pswitch_data_0\n", body, re.M)
        if not sw:
            die(f"{iface}.onTransact: switch instruction not found")
        body = body[:sw.end()] + f"{sw.group(1)}:oneos_ignored\n" + body[sw.end():]
    for c, (hn, gc) in sorted(remap.items()):
        changed.append(f"{iface}.onTransact: code {c} remapped to {hn} (was guest {gc}; replaced {by_code_guest[c][0]})")
    for c in sorted(drop):
        why = f"the host's {by_code_host[c][0]}" if c in by_code_host else f"moved to {host[by_code_guest[c][0]][0]}"
        changed.append(f"{iface}.onTransact: code {c} ({by_code_guest[c][0]}) ignored; {why}")
    return text[:s] + body + text[e:], len(drop) + len(remap)


WRITE6 = """    iget-boolean v0, p0, Landroid/content/res/CameraCompatibilityInfo;->mShouldOverrideLensFacingFrontToBack:Z

    invoke-virtual {p1, v0}, Landroid/os/Parcel;->writeBoolean(Z)V
"""
READ6 = re.compile(
    r"    invoke-virtual \{p1\}, Landroid/os/Parcel;->readByte\(\)B\n\n    move-result v0\n\n    if-eqz v0, :cond_(\d+)\n\n    goto :goto_(\d+)\n\n"
    r"    :cond_\1\n    move v1, v2\n\n    :goto_\2\n    iput-boolean v1, p0, Landroid/content/res/CameraCompatibilityInfo;->mShouldOverrideLensFacingFrontToBack:Z\n")


# One UI 9.5 (S948BXXU6ZZKN, Samsung's R8 output): the same sixth field with other registers and
# .line markers; One UI 9.0's cameraserver reads five (A36 run 4: getCameraVendorTagDescriptor
# reached it as another call and CameraServiceWorker took system_server down).
WRITE6_SEC = re.compile(
    r"(?:    \.line \d+\n)?    iget-boolean p0, p0, Landroid/content/res/CameraCompatibilityInfo;->mShouldOverrideLensFacingFrontToBack:Z\n\n"
    r"    invoke-virtual \{p1, p0\}, Landroid/os/Parcel;->writeBoolean\(Z\)V\n")
READ6_SEC = re.compile(
    r"(?:    \.line \d+\n)?    invoke-virtual \{p1\}, Landroid/os/Parcel;->readByte\(\)B\n\n    move-result p1\n\n    if-eqz p1, :cond_(\d+)\n\n    goto :goto_(\d+)\n\n"
    r"    :cond_\1\n    move v1, v2\n\n    :goto_\2\n    iput-boolean v1, p0, Landroid/content/res/CameraCompatibilityInfo;->mShouldOverrideLensFacingFrontToBack:Z\n")


def patch_compat(root, changed):
    path = find_smali(root, COMPAT)
    text = open(path).read()
    if "mShouldOverrideLensFacingFrontToBack" not in text:
        return None
    if text.count(WRITE6) == 0 and len(WRITE6_SEC.findall(text)) == 1 and len(READ6_SEC.findall(text)) == 1:
        text = WRITE6_SEC.sub("", text)
        text = READ6_SEC.sub("", text)
        open(path, "w").write(text)
        changed.append("CameraCompatibilityInfo: sixth field (mShouldOverrideLensFacingFrontToBack) not written or read (Samsung shape)")
        return path
    if text.count(WRITE6) != 1:
        die(f"CameraCompatibilityInfo: the sixth field's write found {text.count(WRITE6)} times (one expected)")
    text = text.replace(WRITE6, "")
    text, n = READ6.subn("", text)
    if n != 1:
        die(f"CameraCompatibilityInfo: the sixth field's read found {n} times (one expected)")
    open(path, "w").write(text)
    changed.append("CameraCompatibilityInfo: sixth field (mShouldOverrideLensFacingFrontToBack) not written or read")
    return path


TRANS_FIELD = re.compile(r"^\.field static final (?:[a-z-]+ )*TRANSACTION_(\w+):I = (0x[0-9a-f]+|\d+)\s*$", re.M)


def guest_table(stub_text, proxy_text):
    """{method: (code, signature)} from the guest's Stub constants and Proxy headers."""
    codes = {n: int(v, 0) for n, v in TRANS_FIELD.findall(stub_text)}
    sigs = {}
    for _, _, header in method_bodies(proxy_text):
        name, sig = sig_of(header)
        if name in codes:
            sigs[name] = sig
    missing = sorted(set(codes) - set(sigs))
    if missing:
        die(f"Proxy lacks methods the Stub names: {missing}")
    return {n: (codes[n], sigs[n]) for n in codes}


def main(root, table_path):
    host = read_table(table_path)
    changed, dirs = [], set()
    for iface, hmethods in host.items():
        cls = iface.replace(".", "/")
        proxy = find_smali(root, cls + "$Stub$Proxy.smali")
        stub = find_smali(root, cls + "$Stub.smali")
        stub_text, proxy_text = open(stub).read(), open(proxy).read()
        guest = guest_table(stub_text, proxy_text)
        if iface in CALLBACK_IFACES:
            # The host calls these into the guest; the guest's own Proxy for
            # them is never used against One UI, so only the Stub's switch matters.
            pass
        else:
            text, n = patch_proxy(proxy_text, iface, hmethods, guest, changed)
            if n and "->oneosRotationOverride(" in text:
                text = add_override_helper(text, changed)
            if n:
                open(proxy, "w").write(text)
                dirs.add(os.path.relpath(proxy, root).split(os.sep)[0])
        if iface in CALLBACK_IFACES:
            text, n = patch_stub_switch(stub_text, iface, hmethods, guest, changed)
            if n:
                open(stub, "w").write(text)
                dirs.add(os.path.relpath(stub, root).split(os.sep)[0])
    # One UI 9.5 hosts (0.5.37) read and write the sixth field themselves (libcameracompatbilityinfo.so has
    # shouldOverrideLensFacingFrontToBack): ONEOS_CAMERA_KEEP_COMPAT=1 leaves the guest's class as it is.
    # ONEOS_CAMERA_COMPAT_FROM_JAR=1 (a16_camera.py for One UI 8.5 hosts, 0.5.45): the jar patched is a set's
    # framework_patched.jar whose class make-overlays.sh already wrote without the sixth field; checked, kept.
    if COMPAT_AS_INT:
        p = None
    elif os.environ.get("ONEOS_CAMERA_COMPAT_FROM_JAR") == "1":
        text = open(find_smali(root, COMPAT)).read()
        bodies = [text[a:b] for a, b, h in method_bodies(text) if " writeToParcel(" in h]
        if len(bodies) != 1 or "->writeInt(" not in bodies[0] or "mShouldOverrideLensFacingFrontToBack" in bodies[0]:
            die("CameraCompatibilityInfo: ONEOS_CAMERA_COMPAT_FROM_JAR but writeToParcel still writes the sixth field (or was not found)")
        changed.append("CameraCompatibilityInfo: the jar's own (sixth field already not written)")
        p = None
    else:
        p = None if os.environ.get("ONEOS_CAMERA_KEEP_COMPAT") == "1" else patch_compat(root, changed)
    if p:
        dirs.add(os.path.relpath(p, root).split(os.sep)[0])
    for c in changed:
        print(f"pixel_camera_abi: {c}", file=sys.stderr)
    if not dirs:
        print("pixel_camera_abi: unchanged (the guest's camera tables are the host's)", file=sys.stderr)
    for d in sorted(dirs):
        print(d)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
