"""vivo OriginOS's MediaTek RIL on One UI's radio (0.4.60, X500 Pro Max build).

telephony-common.jar hands the phone process's RIL to vivo's
vivo-telephony-common-platform-ex.jar (VivoTelephonyComponentFactory, MediaTek
build), which makes com.mediatek.internal.telephony.MtkRIL. MtkRIL connects to
the AOSP IRadio* services only once isRildReady() is true, and on an AIDL radio
that needs the six AOSP services (IRadioData, Messaging, Modem, Network, Sim,
Voice: One UI's RIL serves them) and MediaTek's six
vendor.mediatek.hardware.mtkradioex.* services, which a Samsung vendor does not
have. So it never connects: no SIM, no signal, and a retry every second (seventh
OriginOS run: "RIL missing").

The six mtkradioex checks are dropped: isRildReady() now goes from the AOSP
IRadioVoice check straight to the IRadioIms one. MediaTek's own requests keep
going through MtkRadioEx*Proxy, which stays empty (RADIO_NOT_AVAILABLE), so none
of them reaches Samsung's modem.

Every pattern must match exactly once, or nothing is written (fail closed).

Usage: vivo_telephony.py <apktool decoded vivo-telephony-common-platform-ex.jar dir>
Prints the smali_* directory (dex file) it changed.
"""
import os
import re
import sys

MTKRIL = os.path.join("com", "mediatek", "internal", "telephony", "MtkRIL.smali")
METHOD = re.compile(r"^\.method private isRildReady\(\)Z\n.*?^\.end method\n", re.M | re.S)
CHECK = "Landroid/os/ServiceManager;->checkService(Ljava/lang/String;)Landroid/os/IBinder;"
MTK_DESC = re.compile(r"Lvendor/mediatek/hardware/mtkradioex/\w+/IMtkRadioEx(\w+);->DESCRIPTOR")
STATEMENT = "    new-instance v0, Ljava/lang/StringBuilder;\n"
# The last MediaTek check: "if-nez v0, :cond_N" past a "goto :goto_M" to the failing return.
LAST = re.compile(r"^    if-nez v0, :(cond_\d+)\n\n    goto :goto_\d+\n\n", re.M)
EXPECTED = {"Data", "Messaging", "Modem", "Network", "Sim", "Voice"}


def fail(msg):
    sys.exit(f"vivo_telephony: {msg}")


def main():
    if len(sys.argv) != 2:
        fail(__doc__)
    found = [os.path.join(sys.argv[1], d, MTKRIL) for d in sorted(os.listdir(sys.argv[1]))
             if d.startswith("smali") and os.path.isfile(os.path.join(sys.argv[1], d, MTKRIL))]
    if len(found) != 1:
        fail(f"MtkRIL.smali {len(found)} times")
    path = found[0]
    text = open(path).read()
    ms = list(METHOD.finditer(text))
    if len(ms) != 1:
        fail(f"isRildReady() {len(ms)} times")
    body = ms[0].group(0)
    if body.count(CHECK) != 13 or body.count("isDeclared(") != 1:
        fail(f"isRildReady() has {body.count(CHECK)} checkService calls, expected 13 (6 AOSP, 6 MediaTek, IRadioIms)")
    descs = list(MTK_DESC.finditer(body))
    if {d.group(1) for d in descs} != EXPECTED or len(descs) != 6:
        fail(f"MediaTek services {[d.group(1) for d in descs]}")
    # From the statement that builds the first MediaTek name to the last check's goto.
    start = body.rfind(STATEMENT, 0, descs[0].start())
    if start < 0 or body.count(CHECK, 0, start) != 6:
        fail("the first MediaTek check does not follow the six AOSP ones")
    lasts = list(LAST.finditer(body, descs[-1].end()))
    if len(lasts) != 1:
        fail(f"the last MediaTek check's branch {len(lasts)} times")
    end = lasts[0].end()
    cut = body[start:end]
    if cut.count(CHECK) != 6 or len(MTK_DESC.findall(cut)) != 6:
        fail("the cut is not exactly the six MediaTek checks")
    if re.search(r"^    :\w+$", cut, re.M):
        fail("a label inside the MediaTek checks")
    if not re.match(rf"    \.line \d+\n    :{lasts[0].group(1)}\n|    :{lasts[0].group(1)}\n", body[end:]):
        fail("the IRadioIms check does not follow the MediaTek ones")
    new = (body[:start] + "    # OneOS (patches/vivo_telephony.py): a Samsung vendor has no MediaTek radio\n"
           "    # extension services; One UI's AOSP IRadio services are enough.\n\n" + body[end:])
    if new.count(CHECK) != 7 or "mtkradioex" in new:
        fail("after the cut")
    text = text[:ms[0].start()] + new + text[ms[0].end():]
    open(path, "w").write(text)
    print(os.path.relpath(path, sys.argv[1]).split(os.sep)[0])


if __name__ == "__main__":
    main()
