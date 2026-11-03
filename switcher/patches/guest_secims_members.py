#!/usr/bin/env python3
"""Samsung IMS's framework additions as OneOS stand-ins in the guest's framework.jar.

Samsung's VoLTE app (com.sec.imsservice, staged from this phone's One UI when
ONEOS_GUEST_SEC_IMS=1; see guest_prepare.sh and guest_sec_ims_signature.py) calls
36 members One UI adds to standard Android classes. A guest's own framework.jar
defines those classes, and its boot classes win over One UI's framework classes
handed to the app as a library, so the members do not exist for it: the app died
at start with NoSuchMethodError TelephonyManager.getGroupIdLevel2,
ServiceState.isPsOnlyReg, NoSuchFieldError Build.VERSION.SEM_INT (F8U, Find N6
global, 0.4.38 test6). The list is scripts' scan of imsservice.apk, imsmanager,
rcsopenapi, vsimmanager and EpdgManager against the guest's boot class path.

Each stand-in is OneOS's own small code, no Samsung code: the standard Android
equivalent where there is one (service state, data state, cell info, subscriber
id, call extras, the five-argument SMS error report), a failure or a neutral
value where there is none (GBA bootstrapping; 0.4.40 GBA support from the ISIM service table, NR and VoNR modes, Samsung's OEM
RIL requests, video-call network statistics). A member the class already has is
left alone, so this is safe on any image; a class not found exactly once refuses.

Usage: guest_secims_members.py <apktool smali root of framework.jar>
Prints the smali directories it changed.
"""
import os
import sys

TM = "Landroid/telephony/TelephonyManager;"
SS = "Landroid/telephony/ServiceState;"
SMS = "Landroid/telephony/ims/stub/ImsSmsImplBase;"

NULL_OBJ = ".locals 1\n    const/4 v0, 0x0\n    return-object v0"
FALSE = ".locals 1\n    const/4 v0, 0x0\n    return v0"
ZERO_WIDE = ".locals 2\n    const-wide/16 v0, 0x0\n    return-wide v0"
VOID = ".locals 0\n    return-void"


def per_sub(call, ret):
    """this.createForSubscriptionId(p1).<call>, returned as <ret>."""
    return (".locals 1\n"
            f"    invoke-virtual {{p0, p1}}, {TM}->createForSubscriptionId(I){TM}\n"
            "    move-result-object v0\n"
            f"    invoke-virtual {{v0}}, {TM}->{call}\n"
            f"    move-result{'-object' if ret == 'obj' else ''} v0\n"
            f"    return{'-object' if ret == 'obj' else ''} v0")


def per_slot(call, ret):
    """Samsung's sem*State(int) take the SIM slot (ImsSmsImpl's mPhoneId, the ePDG
    listener's phone id), not a subscription: this.createForSubscriptionId(
    SubscriptionManager.getSubscriptionId(p1)).<call>. 0.4.40: per_sub read slot 0 as
    subscription 0, semGetServiceState returned null, ImsSmsImpl.canFallback said no,
    and an SMS the IMS network refused never went over CS (Partner IL 0390db1c: SIP 404,
    then status ERROR instead of FALLBACK)."""
    return (".locals 1\n"
            "    invoke-static {p1}, Landroid/telephony/SubscriptionManager;->getSubscriptionId(I)I\n"
            "    move-result v0\n"
            f"    invoke-virtual {{p0, v0}}, {TM}->createForSubscriptionId(I){TM}\n"
            "    move-result-object v0\n"
            f"    invoke-virtual {{v0}}, {TM}->{call}\n"
            f"    move-result{'-object' if ret == 'obj' else ''} v0\n"
            f"    return{'-object' if ret == 'obj' else ''} v0")


def gba(ist_of):
    """Service n°2 of the ISIM service table (EF_IST, 3GPP TS 31.103) is GBA:
    bit 0x02 of its first byte, as getIsimIst() hands it over (hex). 0.4.40: the
    stand-in answered false, and Samsung IMS builds no T-Mobile registration when
    the carrier has GBA on and the SIM does not support it (S26 Ultra 3255561a:
    "TMobile LTE/WiFi - Unsatisfying carrier requirement", no VoLTE, no calls)."""
    return (".locals 3\n"
            "    :try_start_gba\n"
            f"{ist_of}"
            "    move-result-object v0\n"
            "    if-eqz v0, :gba_no\n"
            "    invoke-virtual {v0}, Ljava/lang/String;->length()I\n"
            "    move-result v1\n"
            "    const/4 v2, 0x2\n"
            "    if-lt v1, v2, :gba_no\n"
            "    const/4 v1, 0x0\n"
            "    invoke-virtual {v0, v1, v2}, Ljava/lang/String;->substring(II)Ljava/lang/String;\n"
            "    move-result-object v0\n"
            "    const/16 v1, 0x10\n"
            "    invoke-static {v0, v1}, Ljava/lang/Integer;->parseInt(Ljava/lang/String;I)I\n"
            "    move-result v0\n"
            "    and-int/lit8 v0, v0, 0x2\n"
            "    if-eqz v0, :gba_no\n"
            "    const/4 v0, 0x1\n"
            "    return v0\n"
            "    :try_end_gba\n"
            "    .catch Ljava/lang/Throwable; {:try_start_gba .. :try_end_gba} :gba_no\n"
            "    :gba_no\n"
            "    const/4 v0, 0x0\n"
            "    return v0")


GBA_SELF = gba(f"    invoke-virtual {{p0}}, {TM}->getIsimIst()Ljava/lang/String;\n")
GBA_SUB = gba(f"    invoke-virtual {{p0, p1}}, {TM}->createForSubscriptionId(I){TM}\n"
              "    move-result-object v0\n"
              f"    invoke-virtual {{v0}}, {TM}->getIsimIst()Ljava/lang/String;\n")


# (class, member line (method header or field), body or None for a field)
MEMBERS = [
    ("Landroid/os/Build$VERSION;", ".field public static final SEM_INT:I = 0xe75", None),  # One UI 9 (ro.build.version.sem 3701)
    # TelephonyManager
    (TM, ".method public getGroupIdLevel2(I)Ljava/lang/String;", NULL_OBJ),
    (TM, ".method public checkCallControl(Ljava/lang/String;)Ljava/lang/String;", ".locals 0\n    return-object p1"),
    (TM, ".method public getAllCellInfoForPhone(I)Ljava/util/List;",
     f".locals 1\n    invoke-virtual {{p0}}, {TM}->getAllCellInfo()Ljava/util/List;\n    move-result-object v0\n    return-object v0"),
    (TM, ".method public getBtid()Ljava/lang/String;", NULL_OBJ),
    (TM, ".method public getKeyLifetime()Ljava/lang/String;", NULL_OBJ),
    (TM, ".method public getRand()[B", NULL_OBJ),
    (TM, ".method public getNextRetryTime()J", ZERO_WIDE),
    (TM, ".method public getSubscriberIdForUiccAppType(II)Ljava/lang/String;", per_sub("getSubscriberId()Ljava/lang/String;", "obj")),
    (TM, ".method public hasCall(Ljava/lang/String;)Z", FALSE),
    (TM, ".method public invokeOemRilRequestRawForPhone(I[B[B)I", ".locals 1\n    const/4 v0, -0x1\n    return v0"),
    (TM, ".method public isGbaSupported()Z", GBA_SELF),
    (TM, ".method public isGbaSupported(I)Z", GBA_SUB),
    (TM, ".method public semGetDataServiceState(I)I",
     ".locals 1\n"
     f"    invoke-virtual {{p0, p1}}, {TM}->createForSubscriptionId(I){TM}\n"
     "    move-result-object v0\n"
     f"    invoke-virtual {{v0}}, {TM}->getServiceState(){SS}\n"
     "    move-result-object v0\n"
     "    if-eqz v0, :oneos_no_state\n"
     f"    invoke-virtual {{v0}}, {SS}->getDataRegistrationState()I\n"
     "    move-result v0\n"
     "    return v0\n"
     "    :oneos_no_state\n"
     "    const/4 v0, 0x1\n"
     "    return v0"),
    (TM, ".method public semGetDataState(I)I", per_slot("getDataState()I", "int")),
    (TM, ".method public semGetNrMode(I)I", FALSE),
    (TM, ".method public semGetServiceState(I)Landroid/telephony/ServiceState;", per_slot(f"getServiceState(){SS}", "obj")),
    (TM, ".method public static semGetTelephonyProperty(ILjava/lang/String;Ljava/lang/String;)Ljava/lang/String;",
     ".locals 1\n    invoke-static {p1, p2}, Landroid/os/SystemProperties;->get(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;\n"
     "    move-result-object v0\n    return-object v0"),
    (TM, ".method public semIsVoNrEnabled()Z", FALSE),
    (TM, ".method public semSetNrMode(IIZ)Z", FALSE),
    (TM, ".method public semSetVoNrEnabled(Z)I", FALSE),
    (TM, ".method public setGbaBootstrappingParams([BLjava/lang/String;Ljava/lang/String;)V", VOID),
    # ServiceState
    (SS, ".method public getSnapshotStatus()I", FALSE),
    (SS, ".method public isPsOnlyReg()Z",
     ".locals 1\n"
     f"    invoke-virtual {{p0}}, {SS}->getState()I\n"
     "    move-result v0\n"
     "    if-eqz v0, :oneos_not_ps_only\n"
     f"    invoke-virtual {{p0}}, {SS}->getDataRegistrationState()I\n"
     "    move-result v0\n"
     "    if-nez v0, :oneos_not_ps_only\n"
     "    const/4 v0, 0x1\n"
     "    return v0\n"
     "    :oneos_not_ps_only\n"
     "    const/4 v0, 0x0\n"
     "    return v0"),
    # Interfaces: default methods, so every proxy and stub has them.
    ("Landroid/os/INetworkManagementService;", ".method public getNetworkStatsVideoCall(Ljava/lang/String;II)J", ZERO_WIDE),
    ("Landroid/os/INetworkManagementService;", ".method public startNetworkStatsOnPorts(Ljava/lang/String;II)V", VOID),
    ("Landroid/os/INetworkManagementService;", ".method public stopNetworkStatsOnPorts(Ljava/lang/String;II)V", VOID),
    ("Landroid/telephony/ims/aidl/IImsCallSessionListener;", ".method public callSessionCancelTransferFailed(Landroid/telephony/ims/ImsReasonInfo;)V", VOID),
    ("Landroid/telephony/ims/aidl/IImsCallSessionListener;", ".method public callSessionCancelTransferred()V", VOID),
    ("Landroid/telephony/ims/aidl/IImsCallSessionListener;", ".method public callSessionImsCallEvent(Ljava/lang/String;Landroid/os/Bundle;)V", VOID),
    # IMS SMS: Samsung's longer error reports carry Android's five values first.
    (SMS, ".method public onSendSmsResultError(IIIIIIII)V",
     f".locals 0\n    invoke-virtual/range {{p0 .. p5}}, {SMS}->onSendSmsResultError(IIIII)V\n    return-void"),
    (SMS, ".method public onSendSmsResultIncludeErrClass(IIIIIIIII)V",
     f".locals 0\n    invoke-virtual/range {{p0 .. p5}}, {SMS}->onSendSmsResultError(IIIII)V\n    return-void"),
    (SMS, ".method public onReceiveSmsDeliveryReportAck(II)V", VOID),
    ("Landroid/telephony/ims/ImsCallProfile;", ".method public setCallExtraStringArray(Ljava/lang/String;[Ljava/lang/String;)V",
     ".locals 1\n    invoke-virtual {p0}, Landroid/telephony/ims/ImsCallProfile;->getCallExtras()Landroid/os/Bundle;\n"
     "    move-result-object v0\n    invoke-virtual {v0, p1, p2}, Landroid/os/Bundle;->putStringArray(Ljava/lang/String;[Ljava/lang/String;)V\n"
     "    return-void"),
    ("Landroid/telephony/ims/ImsSsInfo$Builder;", ".method public setServiceClass(I)Landroid/telephony/ims/ImsSsInfo$Builder;", ".locals 0\n    return-object p0"),
    ("Lcom/android/internal/telephony/uicc/IccUtils;", ".method public static getIccType(I)I", FALSE),
]


# Fields One UI's subclasses read that the guest declares private: made protected,
# as One UI declares them (still invisible outside the class's subclasses).
# MmTelFeature.mContext: com.sec.internal.imsphone.MmTelFeatureImpl read it and the
# app died at every start with IllegalAccessError (F8U test9; 100% of a core for
# the whole session in the restart loop, so the phone ran hot and throttled).
WIDEN = [("Landroid/telephony/ims/feature/MmTelFeature;", "mContext")]


def find(root, cls):
    rel = cls[1:-1] + ".smali"
    hits = [os.path.join(root, d, rel) for d in sorted(os.listdir(root))
            if d.startswith("smali") and os.path.isfile(os.path.join(root, d, rel))]
    if len(hits) != 1:
        sys.exit(f"{cls}: found {len(hits)} times, expected once")
    return hits[0]


def key(header):
    """'name(sig)ret' of a method header or 'name:' of a field line."""
    last = header.split()[-1]
    return last.split("=")[0].strip() if header.startswith(".field") else last


def main(root):
    changed = {}
    for cls, header, body in MEMBERS:
        path = find(root, cls)
        text = changed.get(path) or open(path, encoding="utf-8").read()
        k = key(header)
        lines = text.split("\n")
        existing = [l.split()[-1] for l in lines if l.startswith(".method ")]
        if body is None:
            name = header.split(":")[0].split()[-1]
            if any(l.startswith(".field ") and f" {name}:" in l for l in lines):
                continue
            # Fields go before the first method.
            i = text.index("\n.method ") if "\n.method " in text else len(text)
            text = text[:i] + f"\n\n# OneOS: Samsung IMS (patches/guest_secims_members.py)\n{header}\n" + text[i:]
        else:
            if k in existing:
                continue
            text = text.rstrip("\n") + f"\n\n# OneOS: Samsung IMS (patches/guest_secims_members.py)\n{header}\n    {body}\n.end method\n"
        changed[path] = text
    for cls, name in WIDEN:
        path = find(root, cls)
        text = changed.get(path) or open(path, encoding="utf-8").read()
        lines = text.split("\n")
        hit = [i for i, l in enumerate(lines) if l.startswith(".field ") and f" {name}:" in l]
        if len(hit) != 1:
            sys.exit(f"{cls}.{name}: declared {len(hit)} times, expected once")
        line = lines[hit[0]]
        if " private " in line:
            lines[hit[0]] = line.replace(" private ", " protected ", 1)
            changed[path] = "\n".join(lines)
    for path, text in changed.items():
        open(path, "w", encoding="utf-8").write(text)
    dirs = sorted({os.path.relpath(p, root).split(os.sep)[0] for p in changed})
    print(f"guest_secims_members: {sum(1 for _ in changed)} classes changed", file=sys.stderr)
    print(" ".join(dirs))


if __name__ == "__main__":
    main(sys.argv[1])
