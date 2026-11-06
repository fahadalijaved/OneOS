"""vivo OriginOS's framework against One UI's daemons and HALs (0.4.59, X500 Pro Max build).

Three things in vivo's system_server reach the shared phone's own services:

  - IOemNetd. vivo ships its own com.android.internal.net.IOemNetd (44 methods,
    in vivo-services.jar only) under AOSP's descriptor, which One UI's netd
    answers too. Only codes 1 and 2 are AOSP's; vivo's firewall, routing,
    socket-destroy and shell-command calls (3..0x2c) would land on other
    methods of Samsung's netd, which runs the phone's real network. Every
    Proxy method that transacts now throws RemoteException at entry, so no
    call reaches One UI's netd; the callers already catch RemoteException
    (mOemNetd also stays usable as an object, so no NullPointerException).
  - HAL extensions. vivo asks One UI's fingerprint, face and power HALs for
    their extension binder and casts it to vivo's interface without checking
    it (VivoFingerprintProvider, AnalysisService, UnisocPolicy in vivo-services;
    face/aidl/Sensor.initISessionExt in services.jar). Samsung's extension
    would get vivo's transactions: BAD_TYPE, an uncaught IllegalArgumentException
    in system_server (HyperOS, 2026-10-25), or one of Samsung's methods. Each
    getExtension() result now goes through a helper that keeps the binder only
    when its descriptor is vivo's ("vendor.vivo.") and is null otherwise, which
    vivo already handles ("extension get failed").
  - MediaTek's alarm manager (services.jar SystemServer.startOtherServices):
    on a MediaTek build MtkAlarmManagerService replaces AOSP's, and its power-off
    alarms program the RTC through /dev/rtc0, the phone's own. The
    startMtkAlarmManagerService() call is now read as false, so SystemServer
    starts AOSP's AlarmManagerService itself, as it does on that result.

  - vivo's camera JSON configs (framework.jar, every process): the first
    CameraManager call (getCameraIdList, connectCameraServiceLocked ->
    VivoCameraUtils.exposeAuxCamera) builds VivoJavaJsonOperate's cache with 31
    native parseJsonConfigToCache calls, each asking for vivo's own
    "media.vivocamera" service, which Samsung's vendor does not have: libbinder
    waits 5 s for each, about 2.5 minutes, holding CameraManagerGlobal's lock.
    The third OriginOS run's system_server main thread waited on that lock in
    VivoProxCaliService's constructor for 61 s and the watchdog killed it.
    parseAllJsonConfigToCache() now returns at entry: the cache stays empty and
    every getter takes its "no config" default, as on a vivo phone without the
    configs.

  - vivo's features (framework.jar): FtFeature asks vivo's vendor config store,
    which Samsung's vendor lacks, so every feature reads as off. On a real
    X500 Pro Max "vivo.software.multiwindow.newadvanced" is on, and services.jar
    relies on it: VivoActivityTaskManagerServiceImpl makes its
    VivoMultiWindowManagerService only when VivoMwUtils.IS_SUPPORT_ADVANCED_MULTIWINDOW
    is set, while ActivityStarter.executeRequest calls that manager without a
    null check (fifth OriginOS run: NullPointerException starting Home at
    systemReady). VivoMwUtils' static init now sets the flag to true, as the
    phone's config would.

Every pattern must match the expected number of times, or nothing is written
(fail closed).

Usage: vivo_guards.py vivo-services <apktool decoded vivo-services.jar dir>
       vivo_guards.py services <apktool decoded services.jar dir>
       vivo_guards.py framework <apktool decoded framework.jar dir>   (prints nothing without vivo's class)
Prints the smali_* directories (dex files) it changed.
"""
import os
import re
import sys

TRANSACT = "Landroid/os/IBinder;->transact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z"
OEMNETD = os.path.join("com", "android", "internal", "net", "IOemNetd$Stub$Proxy.smali")
EXT = re.compile(r"^(    invoke-interface \{(v\d+)\}, Landroid/os/IBinder;->getExtension\(\)Landroid/os/IBinder;\n"
                 r"(?:\n|    \.line \d+\n)*    move-result-object \2\n)", re.M)
ALARM = re.compile(r"^(    invoke-virtual \{(v\d+)\}, Lcom/vivo/server/adapter/AbsSystemServerAdapter;->"
                   r"startMtkAlarmManagerService\(\)Z\n(?:\n|    \.line \d+\n)*    move-result \2\n)", re.M)
LOCALS = re.compile(r"^(\s*)\.locals (\d+)$")
HELPER = """.class public final Loneos/vivo/{name};
.super Ljava/lang/Object;
.source "{name}.java"


# OneOS (patches/vivo_guards.py): a HAL extension binder only when it is vivo's.
.method public static onlyVivo(Landroid/os/IBinder;)Landroid/os/IBinder;
    .locals 3

    const/4 v0, 0x0

    if-nez p0, :check

    return-object v0

    :check
    :try_start_0
    invoke-interface {{p0}}, Landroid/os/IBinder;->getInterfaceDescriptor()Ljava/lang/String;

    move-result-object v1
    :try_end_0
    .catch Ljava/lang/Throwable; {{:try_start_0 .. :try_end_0}} :failed

    if-eqz v1, :refuse

    const-string v2, "vendor.vivo."

    invoke-virtual {{v1, v2}}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z

    move-result v2

    if-eqz v2, :refuse

    return-object p0

    :refuse
    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {{v2}}, Ljava/lang/StringBuilder;-><init>()V

    const-string p0, "HAL extension is not vivo's, not used: "

    invoke-virtual {{v2, p0}}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {{v2, v1}}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {{v2}}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v2

    const-string v1, "OneOS"

    invoke-static {{v1, v2}}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    return-object v0

    :failed
    return-object v0
.end method
"""


def die(msg):
    sys.exit(f"vivo_guards: {msg}")


def smali_files(root):
    for d, _, fs in os.walk(root):
        for f in fs:
            if f.endswith(".smali"):
                yield os.path.join(d, f)


def top(root, path):
    return os.path.relpath(path, root).split(os.sep)[0]


def methods(text):
    """(start, end, header) of each method, end at the start of '.end method'."""
    for m in re.finditer(r"^\.method [^\n]*$", text, re.M):
        e = text.index("\n.end method", m.end())
        yield m.start(), e, m.group(0)


def refuse_at_entry(body, name):
    lines = body.split("\n")
    li = next((i for i, l in enumerate(lines) if LOCALS.match(l)), None)
    if li is None:
        die(f"IOemNetd.{name}: no .locals line")
    if int(LOCALS.match(lines[li]).group(2)) < 2:
        lines[li] = f"{LOCALS.match(lines[li]).group(1)}.locals 2"
    j = li + 1
    while j < len(lines) and (lines[j].strip() == "" or lines[j].lstrip().startswith((".param", ".end param", ".annotation"))):
        if lines[j].lstrip().startswith(".annotation"):
            j = next(k for k in range(j, len(lines)) if lines[k].strip() == ".end annotation")
        j += 1
    lines[j:j] = [
        "    # OneOS (patches/vivo_guards.py): vivo's IOemNetd codes are other methods of One UI's netd.",
        "    new-instance v0, Landroid/os/RemoteException;",
        f'    const-string v1, "OneOS: IOemNetd.{name} is not sent to the phone\'s netd"',
        "    invoke-direct {v0, v1}, Landroid/os/RemoteException;-><init>(Ljava/lang/String;)V",
        "    throw v0",
        "",
    ]
    return "\n".join(lines)


def oemnetd(root, changed):
    hits = [p for p in smali_files(root) if p.endswith(os.sep + OEMNETD)]
    if len(hits) != 1:
        die(f"expected one IOemNetd$Stub$Proxy.smali, found {len(hits)}")
    text = open(hits[0]).read()
    if '"com.android.internal.net.IOemNetd"' not in open(hits[0].replace("$Proxy", "")).read():
        die("IOemNetd$Stub has another descriptor")
    if "OneOS (patches/vivo_guards.py)" in text:
        die("IOemNetd$Stub$Proxy already patched")
    pieces, pos, n = [], 0, 0
    for s, e, header in methods(text):
        body = text[s:e]
        if TRANSACT not in body:
            continue
        if body.count(TRANSACT) != 1 or " static " in header:
            die(f"IOemNetd: unexpected method {header.strip()}")
        name = re.search(r" (\w+)\(", header).group(1)
        pieces.append(text[pos:s]); pieces.append(refuse_at_entry(body, name)); pos = e
        n += 1
    pieces.append(text[pos:])
    if n < 3:
        die(f"IOemNetd$Stub$Proxy: {n} transacting methods (vivo's has 44)")
    open(hits[0], "w").write("".join(pieces))
    changed.add(top(root, hits[0]))
    print(f"IOemNetd$Stub$Proxy: {n} methods throw RemoteException at entry (nothing to One UI's netd)", file=sys.stderr)


def hal_ext(root, helper, expect, changed):
    sites, files = 0, []
    for p in smali_files(root):
        text = open(p).read()
        if "getExtension()Landroid/os/IBinder;" not in text:
            continue
        total = text.count("Landroid/os/IBinder;->getExtension()Landroid/os/IBinder;")
        new, k = EXT.subn(lambda m: m.group(1) + f"\n    invoke-static/range {{{m.group(2)} .. {m.group(2)}}}, "
                          f"Loneos/vivo/{helper};->onlyVivo(Landroid/os/IBinder;)Landroid/os/IBinder;\n\n"
                          f"    move-result-object {m.group(2)}\n", text)
        if k != total:
            die(f"{os.path.relpath(p, root)}: {total} getExtension() calls, {k} in the expected form")
        files.append((p, new))
        sites += k
        print(f"{os.path.relpath(p, root)}: {k} HAL extension(s) kept only when vivo's", file=sys.stderr)
    if sites != expect:
        die(f"{sites} getExtension() calls, {expect} expected; nothing written")
    for p, new in files:
        open(p, "w").write(new)
        changed.add(top(root, p))
    d = files[0][0]
    hp = os.path.join(root, top(root, d), "oneos", "vivo", f"{helper}.smali")
    if os.path.exists(hp):
        die(f"{helper} already in the jar")
    os.makedirs(os.path.dirname(hp), exist_ok=True)
    open(hp, "w").write(HELPER.format(name=helper))


def mtk_alarm(root, changed):
    hits = []
    for p in smali_files(root):
        if not p.endswith(os.sep + os.path.join("com", "android", "server", "SystemServer.smali")):
            continue
        text = open(p).read()
        new, k = ALARM.subn(lambda m: f"    # OneOS (patches/vivo_guards.py): AOSP's AlarmManagerService, not MediaTek's (RTC power-off alarms).\n"
                            f"    const/4 {m.group(2)}, 0x0\n", text)
        hits.append((p, new, k, text.count("->startMtkAlarmManagerService()Z")))
    if len(hits) != 1 or hits[0][2] != 1 or hits[0][3] != 1:
        die(f"SystemServer.startMtkAlarmManagerService: {[(h[2], h[3]) for h in hits]} (one call expected)")
    p, new, _, _ = hits[0]
    open(p, "w").write(new)
    changed.add(top(root, p))
    print("SystemServer: startMtkAlarmManagerService() read as false (AOSP AlarmManagerService)", file=sys.stderr)


JSON_OP = os.path.join("android", "hardware", "camera2", "vivo_ext", "VivoJavaJsonOperate.smali")
PARSE_ALL = re.compile(r"^\.method public static (?:[\w-]+ )*parseAllJsonConfigToCache\(\)I\n(    \.locals (\d+)\n)", re.M)


def camera_json(root, changed):
    hits = [p for p in smali_files(root) if p.endswith(os.sep + JSON_OP)]
    if not hits:
        return  # not vivo's framework
    if len(hits) != 1:
        die(f"expected one VivoJavaJsonOperate.smali, found {len(hits)}")
    text = open(hits[0]).read()
    if "OneOS (patches/vivo_guards.py)" in text:
        die("VivoJavaJsonOperate already patched")
    ms = list(PARSE_ALL.finditer(text))
    if len(ms) != 1:
        die(f"VivoJavaJsonOperate.parseAllJsonConfigToCache()I found {len(ms)} times (one expected)")
    m = ms[0]
    locals_line = m.group(1) if int(m.group(2)) >= 1 else "    .locals 1\n"
    new = (text[:m.start(1)] + locals_line
           + "\n    # OneOS (patches/vivo_guards.py): no vivo camera service on this phone; each native parse would\n"
           + "    # wait 5 s for media.vivocamera under CameraManager's lock. The cache stays empty.\n"
           + "    const/4 v0, 0x0\n\n    return v0\n"
           + text[m.end(1):])
    open(hits[0], "w").write(new)
    changed.add(top(root, hits[0]))
    print("VivoJavaJsonOperate.parseAllJsonConfigToCache: returns at entry (no media.vivocamera waits)", file=sys.stderr)


MW_UTILS = os.path.join("android", "util", "VivoMwUtils.smali")
MW_FLAG = re.compile(r"(    const-string(?:/jumbo)? (v\d+), \"vivo\.software\.multiwindow\.newadvanced\"\n(?:\n|    \.line \d+\n)*"
                     r"    invoke-static \{\2\}, Landroid/util/FtFeature;->isFeatureSupport\(Ljava/lang/String;\)Z\n(?:\n|    \.line \d+\n)*)"
                     r"    move-result (v\d+)\n((?:\n|    \.line \d+\n)*    sput-boolean \3, Landroid/util/VivoMwUtils;->IS_SUPPORT_ADVANCED_MULTIWINDOW:Z\n)")


def advanced_multiwindow(root, changed):
    hits = [p for p in smali_files(root) if p.endswith(os.sep + MW_UTILS)]
    if not hits:
        return
    if len(hits) != 1:
        die(f"expected one VivoMwUtils.smali, found {len(hits)}")
    text = open(hits[0]).read()
    new, k = MW_FLAG.subn(lambda m: m.group(1) + "    # OneOS (patches/vivo_guards.py): on, as this phone's vivo_config.ini has it "
                          "(services.jar needs its multi-window manager).\n" + f"    const/4 {m.group(3)}, 0x1\n" + m.group(4), text)
    if k != 1:
        die(f"VivoMwUtils: IS_SUPPORT_ADVANCED_MULTIWINDOW from FtFeature found {k} times (one expected)")
    open(hits[0], "w").write(new)
    changed.add(top(root, hits[0]))
    print("VivoMwUtils.IS_SUPPORT_ADVANCED_MULTIWINDOW: true (vivo's multi-window manager is made)", file=sys.stderr)


def main(kind, root):
    changed = set()
    if kind == "vivo-services":
        oemnetd(root, changed)
        # VivoFingerprintProvider, AnalysisService, UnisocPolicy.
        hal_ext(root, "OneOSVivoHalExt", 3, changed)
    elif kind == "framework":
        camera_json(root, changed)
        advanced_multiwindow(root, changed)
    elif kind == "services":
        # face/aidl/Sensor.initISessionExt.
        hal_ext(root, "OneOSVivoHalExtServices", 1, changed)
        mtk_alarm(root, changed)
    else:
        die(__doc__)
    for d in sorted(changed):
        print(d)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
