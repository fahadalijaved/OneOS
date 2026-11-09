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

  - vivo's fold states (services.jar LogicalDisplayMapper), for the session's
    ro.vivo.device.type=foldable (guest_props.sh): the boot state is no longer read
    from vivo's hall_status file, which a Samsung kernel lacks (always OPEN), and
    leaving state 1 (OPEN) no longer puts the phone to sleep, so folding moves to
    the cover as in every OneOS guest (seventh OriginOS run: phone UI on the inner
    panel, as ro.vivo.device.type was the image's "phone").

  - vivo's main panel (vivo-services.jar): vivo's display code takes
    SurfaceControl.getPrimaryPhysicalDisplayId() as its main panel (panel 0 for
    the brightness animators, the LCM configs, touch and refresh rate). In fold
    mode 1 SurfaceFlinger named the cover primary at boot, so the inner panel
    was panel 1 and its brightness never followed the slider (F8U run 14: the
    inner panel stayed at 500 of 14063). Each call now goes through a helper that
    returns the physical id in oneos.vivo.inner_display (guest_start.sh sets it
    in mode 1 only) and SurfaceFlinger's answer otherwise.

  - vivo's brightness as a phone's (vivo-services.jar display brightness classes,
    services.jar DisplayPowerController): fold mode 1 (ro.vivo.device.type=foldable)
    turned on vivo's per-panel brightness, which a phone build carries only in part
    (F8U runs 14-15: on the inner panel the slider moved vivo's nits but the backlight
    stayed at the session's first level). Their device-type reads answer "phone", as
    in mode 2, where both panels followed the slider; the layout code keeps foldable.

Every pattern must match the expected number of times, or nothing is written
(fail closed).

  - vivo's launcher with the fold mode (framework.jar FtDeviceInfo): the bar
    phone's BBKLauncher2 has no working foldable paths (R8 removed their
    classes), so getDeviceType() answers "phone" in its process only.

  - About phone's processor (framework-adapter.jar CpuInfoImpl): with One UI's
    vendor version (16) vivo reads only its own /sys/cpu_info nodes, missing on
    a Samsung kernel ("Processor null GHz"); it now reads /sys/devices/system/cpu
    as on an older vendor and shows the highest clock ("4.74 GHz").

Usage: vivo_guards.py vivo-services <apktool decoded vivo-services.jar dir>
       vivo_guards.py framework-adapter <apktool decoded framework-adapter.jar dir>
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


LDM = os.path.join("com", "android", "server", "display", "LogicalDisplayMapper.smali")
SKIP = r"(?:\n|    \.line \d+\n|    nop\n)*"
HALL = re.compile(r"^    sget-boolean (v\d+), Lcom/android/server/policy/DeviceStateProviderImpl;->mIsFoldPhone:Z\n"
                  rf"(?={SKIP}    if-eqz \1, :(cond_\w+)\n{SKIP}    const/4 \1, 0x2\n{SKIP}    if-ne v\d+, \1, :\2\n)", re.M)
OPEN_SLEEP = re.compile(r"^(    invoke-virtual \{p2\}, Landroid/hardware/devicestate/DeviceState;->getIdentifier\(\)I\n"
                        rf"{SKIP}    move-result (v\d+)\n{SKIP})    if-eq \2, (v\d+), :cond_\w+\n"
                        rf"(?={SKIP}    sget-boolean \2, Lcom/android/server/policy/DeviceStateProviderImpl;->mIsFlipPhone:Z\n)", re.M)


def vivo_fold_states(root, changed):
    """vivo's fold handling against Samsung's hall and fold policy (OriginOS as a foldable).

    With ro.vivo.device.type=foldable (guest_props.sh), LogicalDisplayMapper takes
    its boot state from vivo's sys/module/hall_sensor/parameters/hall_status, which
    a Samsung kernel lacks: always OPEN, so the first real commit (CLOSE, the cover)
    came "from OPEN". And shouldDeviceBePutToSleep sleeps whenever the device leaves
    state 1 (OPEN) for CLOSE. The hall read is skipped (the first state comes from
    the device-state provider, as on a bar build), and the leave-OPEN clause is
    dropped, so folding moves to the cover as in every other OneOS guest.
    """
    hits = [p for p in smali_files(root) if p.endswith(os.sep + LDM)]
    if len(hits) != 1:
        die(f"expected one LogicalDisplayMapper.smali, found {len(hits)}")
    text = open(hits[0]).read()
    if text.count("Landroid/util/FtDeviceInfo;->getInitHallState()") != 1:
        die("LogicalDisplayMapper: getInitHallState() not called exactly once")
    text, k = HALL.subn(lambda m: "    # OneOS (patches/vivo_guards.py): no vivo hall_status file on this phone; the first state\n"
                        "    # comes from the device-state provider.\n"
                        f"    const/4 {m.group(1)}, 0x0\n", text)
    if k != 1:
        die(f"LogicalDisplayMapper: the hall boot state's mIsFoldPhone check found {k} times (one expected)")
    found = [(a, b, h) for a, b, h in methods(text) if "shouldDeviceBePutToSleep(Landroid/hardware/devicestate/DeviceState;" in h]
    if len(found) != 1:
        die(f"shouldDeviceBePutToSleep found {len(found)} times")
    a, b, _ = found[0]
    body = text[a:b]
    ms = list(OPEN_SLEEP.finditer(body))
    if len(ms) != 1:
        die(f"shouldDeviceBePutToSleep: the leave-OPEN clause found {len(ms)} times (one expected)")
    reg = ms[0].group(3)
    if not re.search(rf"^    const/4 {reg}, 0x1\n", body[:ms[0].start()], re.M):
        die(f"shouldDeviceBePutToSleep: {reg} is not OPEN (1) before the clause")
    body = OPEN_SLEEP.sub(lambda m: m.group(1) + "    # OneOS (patches/vivo_guards.py): leaving OPEN no longer puts the phone to sleep\n"
                          "    # (folding moves to the cover, as in every OneOS guest).\n", body)
    text = text[:a] + body + text[b:]
    open(hits[0], "w").write(text)
    changed.add(top(root, hits[0]))
    print("LogicalDisplayMapper: no hall_status boot state; folding from OPEN does not sleep", file=sys.stderr)


FT_FEATURE = os.path.join("android", "util", "FtFeature.smali")
QOS_FEATURE = os.path.join("android", "util", "QoSFeature.smali")
QOS_IS_FEATURE = re.compile(r"^(\.method public (?:[\w-]+ )*isFeatureSupport\(Ljava/lang/String;\)Z\n)    \.locals (\d+)\n", re.M)
IS_FEATURE = re.compile(r"^(\.method public static (?:[\w-]+ )*isFeatureSupport\(Ljava/lang/String;\)Z\n)    \.locals (\d+)\n", re.M)
# vivo features answered yes without vivo's vendor config store: software ones this
# phone's own GPU and the guest's vivo SurfaceFlinger can do. Not vivo.software.vblurnpu
# (MediaTek's APU), nor anything tied to vivo's sensors, hall or modem.
VIVO_FEATURES = ("vivo.software.realtimeblur", "vivo.software.nativeblur", "vivo.software.windowdeformblur")
FEATURE_HELPER = """.class public final Loneos/vivo/OneOSVivoFeatures;
.super Ljava/lang/Object;
.source "OneOSVivoFeatures.java"


# OneOS (patches/vivo_guards.py): vivo features answered yes on a phone without vivo's config store.
.method public static listed(Ljava/lang/String;)Z
    .locals 1

    if-nez p0, :named

    const/4 v0, 0x0

    return v0

    :named
{checks}
    const/4 v0, 0x0

    return v0
.end method
"""


def vivo_features(root, changed):
    """vivo's glass (real-time blur) without vivo's vendor config store (twelfth run).

    FtFeature.isFeatureSupport asks vivo's vendor config store, which a Samsung
    vendor lacks, so every feature reads as off. OriginOS's glass then takes its
    "no real-time blur" paths everywhere (vivo-framework VivoBlurRender,
    SystemUI's material SDK): no glass even with realtime_blur_state=1. The
    software blur features in VIVO_FEATURES now answer yes; every other name
    goes the way it went."""
    hits = [p for p in smali_files(root) if p.endswith(os.sep + FT_FEATURE)]
    if not hits:
        return
    if len(hits) != 1:
        die(f"expected one FtFeature.smali, found {len(hits)}")
    text = open(hits[0]).read()
    ms = list(IS_FEATURE.finditer(text))
    if len(ms) != 1:
        die(f"FtFeature.isFeatureSupport(String) found {len(ms)} times (one expected)")
    m = ms[0]
    head = (m.group(1) + f"    .locals {max(1, int(m.group(2)))}\n\n"
            "    # OneOS (patches/vivo_guards.py): vivo's software blur features without its config store.\n"
            "    invoke-static {p0}, Loneos/vivo/OneOSVivoFeatures;->listed(Ljava/lang/String;)Z\n\n"
            "    move-result v0\n\n"
            "    if-eqz v0, :oneos_not_listed\n\n"
            "    return v0\n\n"
            "    :oneos_not_listed\n")
    text = text[:m.start()] + head + text[m.end():]
    open(hits[0], "w").write(text)
    d = top(root, hits[0])
    # BlurRenderSettings asks android.util.QoSFeature (an instance method, answered
    # from a cache of vivo's QoS config, also absent: false) for the same names.
    qhits = [p for p in smali_files(root) if p.endswith(os.sep + QOS_FEATURE)]
    if len(qhits) != 1:
        die(f"expected one QoSFeature.smali, found {len(qhits)}")
    if top(root, qhits[0]) != d:
        die("QoSFeature and FtFeature are in different dex files; the helper would be in one only")
    qtext = open(qhits[0]).read()
    qms = list(QOS_IS_FEATURE.finditer(qtext))
    if len(qms) != 1:
        die(f"QoSFeature.isFeatureSupport(String) found {len(qms)} times (one expected)")
    qm = qms[0]
    qhead = (qm.group(1) + f"    .locals {max(1, int(qm.group(2)))}\n\n"
             "    # OneOS (patches/vivo_guards.py): vivo's software blur features without its QoS config.\n"
             "    invoke-static {p1}, Loneos/vivo/OneOSVivoFeatures;->listed(Ljava/lang/String;)Z\n\n"
             "    move-result v0\n\n"
             "    if-eqz v0, :oneos_not_listed\n\n"
             "    return v0\n\n"
             "    :oneos_not_listed\n")
    open(qhits[0], "w").write(qtext[:qm.start()] + qhead + qtext[qm.end():])
    checks = "".join(f'    const-string v0, "{n}"\n\n    invoke-virtual {{v0, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z\n\n'
                     f"    move-result v0\n\n    if-nez v0, :yes\n\n" for n in VIVO_FEATURES)
    helper = FEATURE_HELPER.replace("{checks}", checks).replace(
        "    const/4 v0, 0x0\n\n    return v0\n.end method", "    const/4 v0, 0x0\n\n    return v0\n\n    :yes\n    const/4 v0, 0x1\n\n    return v0\n.end method")
    hp = os.path.join(root, d, "oneos", "vivo", "OneOSVivoFeatures.smali")
    if any(os.path.exists(os.path.join(root, x, "oneos", "vivo", "OneOSVivoFeatures.smali"))
           for x in os.listdir(root) if x.startswith("smali")):
        die("oneos/vivo/OneOSVivoFeatures.smali exists already")
    if os.path.exists(hp):
        die(f"{hp} exists already")
    os.makedirs(os.path.dirname(hp), exist_ok=True)
    open(hp, "w").write(helper)
    changed.add(d)
    print(f"FtFeature and QoSFeature.isFeatureSupport: {', '.join(VIVO_FEATURES)} answered yes", file=sys.stderr)


FT_DEVICE = os.path.join("android", "util", "FtDeviceInfo.smali")
GET_TYPE = re.compile(r"^(\.method public static (?:[\w-]+ )*getDeviceType\(\)Ljava/lang/String;\n)    \.locals (\d+)\n", re.M)
# BBKLauncher2's process: com.android.launcher3 in the X500 Pro Max (global) build,
# com.bbk.launcher2 in the CN build (PD2609MA; seventh CN run: "foldable" is not in
# its install-compatibility deviceType "phone|flip", so it uninstalled itself and
# exited at every start).
LAUNCHER_PROCESSES = ("com.android.launcher3", "com.bbk.launcher2")


def launcher_phone_type(root, changed):
    """vivo's launcher keeps the bar phone's device type (ninth OriginOS run).

    With ro.vivo.device.type=foldable for the session, the X500 Pro Max's
    BBKLauncher2 takes its foldable paths, whose classes R8 removed from that
    phone build (ClassNotFoundException AllGroupsRecyclerView inflating
    all_groups, 75 crashes, no home). FtDeviceInfo.getDeviceType() now answers
    "phone" in the launcher's own process only (its code reads it directly, by
    reflection and through its helpers); everything else keeps "foldable"."""
    hits = [p for p in smali_files(root) if p.endswith(os.sep + FT_DEVICE)]
    if not hits:
        return
    if len(hits) != 1:
        die(f"expected one FtDeviceInfo.smali, found {len(hits)}")
    text = open(hits[0]).read()
    ms = list(GET_TYPE.finditer(text))
    if len(ms) != 1:
        die(f"FtDeviceInfo.getDeviceType() found {len(ms)} times (one expected)")
    m = ms[0]
    checks = "".join(
        f"    const-string v1, \"{name}\"\n\n"
        "    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z\n\n"
        "    move-result v1\n\n"
        "    if-nez v1, :oneos_launcher\n\n" for name in LAUNCHER_PROCESSES)
    head = (m.group(1) + f"    .locals {max(2, int(m.group(2)))}\n\n"
            "    # OneOS (patches/vivo_guards.py): the launcher (a bar phone's build) keeps \"phone\".\n"
            "    invoke-static {}, Landroid/app/ActivityThread;->currentProcessName()Ljava/lang/String;\n\n"
            "    move-result-object v0\n\n"
            + checks +
            "    goto :oneos_not_launcher\n\n"
            "    :oneos_launcher\n"
            "    const-string v0, \"phone\"\n\n"
            "    return-object v0\n\n"
            "    :oneos_not_launcher\n")
    text = text[:m.start()] + head + text[m.end():]
    open(hits[0], "w").write(text)
    changed.add(top(root, hits[0]))
    print("FtDeviceInfo.getDeviceType: \"phone\" in the launcher's process", file=sys.stderr)


CPU_INFO = os.path.join("com", "vivo", "adapter", "cpuinfo", "CpuInfoImpl.smali")
CPU_VENDOR = re.compile(r"(    const-string (v\d+), \"ro\.vendor\.build\.version\.release\"\n(?:\n|    \.line \d+\n)*"
                        r"    const/4 v\d+, 0x1\n(?:\n|    \.line \d+\n)*"
                        r"    invoke-static \{\2, v\d+\}, Landroid/os/SystemProperties;->getInt\(Ljava/lang/String;I\)I\n(?:\n|    \.line \d+\n)*)"
                        r"    move-result (v\d+)\n((?:\n|    \.line \d+\n)*    sput \3, Lcom/vivo/adapter/cpuinfo/CpuInfoImpl;->VENDOR_VERSION:I\n)")
CPU_DISP = re.compile(r"(    const-string (v\d+), \"init get userDispCpuRate fail\"\n(?:\n|    \.line \d+\n)*"
                      r"    invoke-static \{v\d+, \2\}, Lcom/vivo/common/utils/VLog;->w\(Ljava/lang/String;Ljava/lang/String;\)I\n)"
                      r"(?=(?:\n|    \.line \d+\n)*    :(cond_\w+)\n(?:\n|    \.line \d+\n)*"
                      r"    iput-object (v\d+), p0, Lcom/vivo/adapter/cpuinfo/CpuInfoImpl;->mDisplayMaxCpuRate:Ljava/lang/String;\n)")
CPU_HELPER = """.class public final Loneos/vivo/OneOSCpuRate;
.super Ljava/lang/Object;
.source "OneOSCpuRate.java"


# OneOS (patches/vivo_guards.py): the highest CPU clock (kHz) as vivo shows it, "4.74".
.method public static display(J)Ljava/lang/String;
    .locals 4

    const-wide/16 v0, 0x0

    cmp-long v0, p0, v0

    if-gtz v0, :rate

    const/4 v0, 0x0

    return-object v0

    :rate
    long-to-double v0, p0

    const-wide v2, 0x412e848000000000L    # 1000000.0

    div-double/2addr v0, v2

    invoke-static {v0, v1}, Ljava/lang/Double;->valueOf(D)Ljava/lang/Double;

    move-result-object v0

    const/4 v1, 0x1

    new-array v1, v1, [Ljava/lang/Object;

    const/4 v2, 0x0

    aput-object v0, v1, v2

    sget-object v0, Ljava/util/Locale;->US:Ljava/util/Locale;

    const-string v2, "%.2f"

    invoke-static {v0, v2, v1}, Ljava/lang/String;->format(Ljava/util/Locale;Ljava/lang/String;[Ljava/lang/Object;)Ljava/lang/String;

    move-result-object v0

    return-object v0
.end method
"""


def cpu_info(root, changed):
    """About phone's "Processor null GHz": vivo's CpuInfoImpl reads only vivo's
    /sys/cpu_info nodes when the vendor says Android 16 or later (One UI's does),
    and parses the missing clock as a number. As on an older vendor, it now reads
    the cores and the highest clock from /sys/devices/system/cpu, and the shown
    clock, which only vivo's kernel has, is made from that one ("4.74")."""
    hits = [p for p in smali_files(root) if p.endswith(os.sep + CPU_INFO)]
    if len(hits) != 1:
        die(f"expected one CpuInfoImpl.smali, found {len(hits)}")
    text = open(hits[0]).read()
    if "OneOS (patches/vivo_guards.py)" in text:
        die("CpuInfoImpl already patched")
    text, k = CPU_VENDOR.subn(lambda m: m.group(1) + "    # OneOS (patches/vivo_guards.py): the generic CPU nodes, as on a vendor up to Android 15.\n"
                              f"    const/16 {m.group(3)}, 0xf\n" + m.group(4), text)
    if k != 1:
        die(f"CpuInfoImpl: VENDOR_VERSION from ro.vendor.build.version.release found {k} times (one expected)")
    found = [(a, b) for a, b, h in methods(text) if h.endswith(" init()V")]
    if len(found) != 1:
        die(f"CpuInfoImpl.init() found {len(found)} times")
    a, b = found[0]
    body = text[a:b]
    ms = list(CPU_DISP.finditer(body))
    if len(ms) != 1:
        die(f"CpuInfoImpl.init: the shown clock's fallback point found {len(ms)} times (one expected)")
    reg = ms[0].group(4)
    if reg != "v0" or not re.search(r"^    \.locals ([4-9]|\d\d)$", body, re.M):
        die(f"CpuInfoImpl.init: unexpected registers ({reg})")
    body = (body[:ms[0].end()] + "\n    # OneOS (patches/vivo_guards.py): no vivo user_cpu_freq node; shown from the highest clock.\n"
            "    iget-wide v2, p0, Lcom/vivo/adapter/cpuinfo/CpuInfoImpl;->mMaxCpuRate:J\n\n"
            "    invoke-static {v2, v3}, Loneos/vivo/OneOSCpuRate;->display(J)Ljava/lang/String;\n\n"
            "    move-result-object v0\n" + body[ms[0].end():])
    text = text[:a] + body + text[b:]
    open(hits[0], "w").write(text)
    d = top(root, hits[0])
    hp = os.path.join(root, d, "oneos", "vivo", "OneOSCpuRate.smali")
    if os.path.exists(hp):
        die(f"{hp} exists already")
    os.makedirs(os.path.dirname(hp), exist_ok=True)
    open(hp, "w").write(CPU_HELPER)
    changed.add(d)
    print("CpuInfoImpl: generic CPU nodes, shown clock from the highest one (no \"null GHz\")", file=sys.stderr)



CONFIG_STORE = os.path.join("android", "util", "VivoConfigStoreHelper.smali")
FEATURES_HELPER = """.class public final Loneos/vivo/OneOSVivoConfigStore;
.super Ljava/lang/Object;
.source "OneOSVivoConfigStore.java"


# OneOS (patches/vivo_guards.py): vivo's feature list for system_server's
# VivoConfigStoreHelper, from the vendor's vivo_config.ini ("&"-joined "name$vivo-support"
# and "name:key$value"; make-overlays.sh, guest_prepare.sh), "" when there is none.
.method public static read()Ljava/lang/String;
    .locals 2

    :try_start_0
    const-string v0, "/data/system/oneos_vivo_features"

    const/4 v1, 0x0

    new-array v1, v1, [Ljava/lang/String;

    invoke-static {v0, v1}, Ljava/nio/file/Paths;->get(Ljava/lang/String;[Ljava/lang/String;)Ljava/nio/file/Path;

    move-result-object v0

    invoke-static {v0}, Ljava/nio/file/Files;->readAllBytes(Ljava/nio/file/Path;)[B

    move-result-object v0

    new-instance v1, Ljava/lang/String;

    invoke-direct {v1, v0}, Ljava/lang/String;-><init>([B)V

    invoke-virtual {v1}, Ljava/lang/String;->trim()Ljava/lang/String;

    move-result-object v0
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0

    return-object v0

    :catch_0
    const-string v0, ""

    return-object v0
.end method
"""


def config_store(root, changed):
    """vivo's feature list without vivo's config store HAL (tenth CN run: 54 617
    failed lookups in 12 minutes, every vivo feature off: launcher, Themes...).
    system_server's VivoConfigStoreHelper.getFeatureContent() (every app asks
    system_server for it) reads /data/system/oneos_vivo_features first; empty or
    missing, the HAL path runs as before."""
    hits = [p for p in smali_files(root) if p.endswith(os.sep + CONFIG_STORE)]
    if not hits:
        return
    if len(hits) != 1:
        die(f"expected one VivoConfigStoreHelper.smali, found {len(hits)}")
    text = open(hits[0]).read()
    ms = list(re.finditer(r"^\.method public static (?:[\w-]+ )*getFeatureContent\(\)Ljava/lang/String;\n(.*?)^\.end method\n", text, re.M | re.S))
    if len(ms) != 1:
        die(f"VivoConfigStoreHelper.getFeatureContent() found {len(ms)} times")
    body = ms[0].group(1)
    call = "    invoke-static {}, Landroid/util/VivoConfigStoreHelper;->getservice()V\n"
    if body.count(call) != 1 or not re.search(r"^    \.locals ([4-9]|\d\d)$", body, re.M) or len(re.findall(r"^    :goto_1$", body, re.M)) != 1:
        die("VivoConfigStoreHelper.getFeatureContent() is not the body this was written for")
    if "sCachedFeatureContent:Ljava/lang/String;" not in body or body.find(call) > body.find("    :goto_1\n"):
        die("VivoConfigStoreHelper.getFeatureContent(): the HAL call is not before :goto_1")
    ins = ("    # OneOS (patches/vivo_guards.py): vivo's feature list from the vendor's vivo_config.ini.\n"
           "    invoke-static {}, Loneos/vivo/OneOSVivoConfigStore;->read()Ljava/lang/String;\n\n"
           "    move-result-object v1\n\n"
           "    invoke-virtual {v1}, Ljava/lang/String;->isEmpty()Z\n\n"
           "    move-result v3\n\n"
           "    if-nez v3, :oneos_hal\n\n"
           "    move-object v0, v1\n\n"
           "    goto :goto_1\n\n"
           "    :oneos_hal\n")
    new_body = body.replace(call, ins + call, 1)
    text = text[:ms[0].start(1)] + new_body + text[ms[0].end(1):]
    open(hits[0], "w").write(text)
    d = top(root, hits[0])
    hp = os.path.join(root, d, "oneos", "vivo", "OneOSVivoConfigStore.smali")
    # Never over another helper (the eleventh CN run's zygote died: this one had
    # replaced vivo_features' oneos.vivo.OneOSVivoFeatures, listed() gone).
    if any(os.path.exists(os.path.join(root, x, "oneos", "vivo", "OneOSVivoConfigStore.smali"))
           for x in os.listdir(root) if x.startswith("smali")):
        die("oneos/vivo/OneOSVivoConfigStore.smali exists already")
    os.makedirs(os.path.dirname(hp), exist_ok=True)
    open(hp, "w").write(FEATURES_HELPER)
    changed.add(d)
    print("VivoConfigStoreHelper.getFeatureContent: vivo's feature list from /data/system/oneos_vivo_features first", file=sys.stderr)


PRIMARY_CALL = re.compile(r"(    invoke-static \{\}, Landroid/view/SurfaceControl;->getPrimaryPhysicalDisplayId\(\)J\n\n"
                          r"    move-result-wide ([vp])(\d+)\n)")
PRIMARY_HELPER = """.class public final Loneos/vivo/OneOSVivoPrimaryDisplay;
.super Ljava/lang/Object;
.source "OneOSVivoPrimaryDisplay.java"


# OneOS (patches/vivo_guards.py): the inner panel as vivo's main panel on a Fold in
# fold mode 1 (oneos.vivo.inner_display, set by guest_start.sh), else SurfaceFlinger's.
.method public static get(J)J
    .registers 6

    :try_start_0
    const-string v0, "oneos.vivo.inner_display"

    const-string v1, ""

    invoke-static {v0, v1}, Landroid/os/SystemProperties;->get(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v0

    invoke-virtual {v0}, Ljava/lang/String;->isEmpty()Z

    move-result v1

    if-nez v1, :cond_keep

    invoke-static {v0}, Ljava/lang/Long;->parseLong(Ljava/lang/String;)J

    move-result-wide v2
    :try_end_0
    .catch Ljava/lang/RuntimeException; {:try_start_0 .. :try_end_0} :catch_0

    return-wide v2

    :cond_keep
    return-wide p0

    :catch_0
    return-wide p0
.end method
"""


def vivo_primary_display(root, changed, expect):
    files, sites = [], 0
    for p in smali_files(root):
        text = open(p).read()
        total = text.count("Landroid/view/SurfaceControl;->getPrimaryPhysicalDisplayId()J")
        if not total:
            continue
        new, k = PRIMARY_CALL.subn(lambda m: m.group(1) +
                                   f"\n    # OneOS (patches/vivo_guards.py): the inner panel on a Fold in mode 1.\n"
                                   f"    invoke-static {{{m.group(2)}{m.group(3)}, {m.group(2)}{int(m.group(3)) + 1}}}, "
                                   f"Loneos/vivo/OneOSVivoPrimaryDisplay;->get(J)J\n\n"
                                   f"    move-result-wide {m.group(2)}{m.group(3)}\n", text)
        if k != total:
            die(f"{os.path.relpath(p, root)}: {total} getPrimaryPhysicalDisplayId() calls, {k} in the expected form")
        files.append((p, new))
        sites += k
    if sites != expect:
        die(f"{sites} getPrimaryPhysicalDisplayId() calls in vivo-services, {expect} expected; nothing written")
    for p, new in files:
        open(p, "w").write(new)
        changed.add(top(root, p))
    d = top(root, files[0][0])
    if any(os.path.exists(os.path.join(root, x, "oneos", "vivo", "OneOSVivoPrimaryDisplay.smali"))
           for x in os.listdir(root) if x.startswith("smali")):
        die("oneos/vivo/OneOSVivoPrimaryDisplay.smali exists already")
    hp = os.path.join(root, d, "oneos", "vivo", "OneOSVivoPrimaryDisplay.smali")
    os.makedirs(os.path.dirname(hp), exist_ok=True)
    open(hp, "w").write(PRIMARY_HELPER)
    print(f"vivo main panel: {sites} getPrimaryPhysicalDisplayId() calls through oneos.vivo.inner_display", file=sys.stderr)


DEVTYPE_CALL = re.compile(r"    invoke-static \{\}, Landroid/util/FtDeviceInfo;->getDeviceType\(\)Ljava/lang/String;\n\n"
                          r"    move-result-object ([vp]\d+)\n")
PHONE_NOTE = "    # OneOS (patches/vivo_guards.py): vivo's brightness takes the phone build's single-panel path.\n"


def brightness_phone(root, changed, dirs, expect, what):
    """Each FtDeviceInfo.getDeviceType() read in the files under dirs answers "phone"."""
    files, sites = [], 0
    for p in smali_files(root):
        rel = os.path.relpath(p, root).split(os.sep, 1)[1]
        if not any(rel.startswith(d) for d in dirs):
            continue
        text = open(p).read()
        total = text.count("Landroid/util/FtDeviceInfo;->getDeviceType()Ljava/lang/String;")
        if not total:
            continue
        new, k = DEVTYPE_CALL.subn(lambda m: PHONE_NOTE + f'    const-string {m.group(1)}, "phone"\n', text)
        if k != total:
            die(f"{os.path.relpath(p, root)}: {total} getDeviceType() reads, {k} in the expected form")
        files.append((p, new))
        sites += k
    if sites != expect:
        die(f"{what}: {sites} getDeviceType() reads, {expect} expected; nothing written")
    for p, new in files:
        open(p, "w").write(new)
        changed.add(top(root, p))
    print(f"{what}: {sites} device-type reads answer phone ({len(files)} classes)", file=sys.stderr)


LCM_PROPERTY = os.path.join("com", "android", "server", "display", "common", "config", "LcmProperty.smali")


def lcm_property_phone(root, changed):
    hits = [p for p in smali_files(root) if p.endswith(os.sep + LCM_PROPERTY)]
    if len(hits) != 1:
        die(f"expected one LcmProperty.smali, found {len(hits)}")
    text = open(hits[0]).read()
    pat = re.compile(r'(    const-string/jumbo (v\d+), "ro\.vivo\.device\.type"\n\n'
                     r'    invoke-static \{\2, v\d+\}, Lcom/android/server/display/common/config/LcmProperty;->getString\(Ljava/lang/String;Ljava/lang/String;\)Ljava/lang/String;\n\n'
                     r'    move-result-object (v\d+)\n)')
    new, k = pat.subn(lambda m: m.group(1) + PHONE_NOTE + f'    const-string {m.group(3)}, "phone"\n', text)
    if k != 1:
        die(f"LcmProperty: the ro.vivo.device.type read found {k} times (one expected)")
    open(hits[0], "w").write(new)
    changed.add(top(root, hits[0]))
    print("LcmProperty: ro.vivo.device.type answers phone", file=sys.stderr)


def main(kind, root):
    changed = set()
    if kind == "vivo-services":
        oemnetd(root, changed)
        # VivoFingerprintProvider, AnalysisService, UnisocPolicy.
        hal_ext(root, "OneOSVivoHalExt", 3, changed)
        vivo_primary_display(root, changed, 6)
        brightness_phone(root, changed, [os.path.join("com", "android", "server", "display", d) + os.sep
                                         for d in ("sensor", "brightness", "common")], 8, "vivo-services brightness")
        lcm_property_phone(root, changed)
    elif kind == "framework":
        camera_json(root, changed)
        advanced_multiwindow(root, changed)
        launcher_phone_type(root, changed)
        vivo_features(root, changed)
        config_store(root, changed)
    elif kind == "framework-adapter":
        cpu_info(root, changed)
    elif kind == "services":
        # face/aidl/Sensor.initISessionExt.
        hal_ext(root, "OneOSVivoHalExtServices", 1, changed)
        mtk_alarm(root, changed)
        vivo_fold_states(root, changed)
        brightness_phone(root, changed, [os.path.join("com", "android", "server", "display", "DisplayPowerController.smali")],
                         1, "DisplayPowerController")
    else:
        die(__doc__)
    for d in sorted(changed):
        print(d)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
