"""HyperOS's VendorRIL on a phone whose radio HAL is HIDL (the MediaTek Galaxy A07, A16 4G, A17).

xiaomi-opt-telephony.jar's com.xiaomi.internal.telephony.VendorRIL.getRadioServiceProxy() returns an
empty proxy and re-queues itself every second until isRildReady() is true, and isRildReady() checks
only Xiaomi's AIDL radio instances (android.hardware.radio.data.IRadioData/slot1 and the other five
AIDL radio services). The MediaTek A phones run vendor API 31: Samsung's RIL there is HIDL
(android.hardware.radio@1.x), so the AIDL names never appear and the guest saw no SIM at all
("VendorRILJ: getRadioServiceProxy wait for rild ready", 0.4.67 A17 5357ba6a, A16 4G d946ff36,
A07 c3630d06). AOSP's RIL, which VendorRIL extends, takes a HIDL radio by itself.

The patch: right after isRildReady()'s MockModem check, if IRadioData/<slot> is not even declared
(ServiceManager.isDeclared), it returns true, so getRadioServiceProxy() goes to AOSP's. Where the AIDL
radio is declared (every Snapdragon Galaxy on One UI 9) nothing changes: isRildReady() checks the six
services as before. Fails closed if the method is not the one this was written against.

Usage: hyperos_hidl_radio.py <smali root of xiaomi-opt-telephony.jar>
Prints the smali_* directory it changed.
"""
import os
import sys

CLS = "com/xiaomi/internal/telephony/VendorRIL.smali"
HEAD = [
    ".method private isRildReady()Z",
    ".locals 5",
    "iget-object v0, p0, Lcom/xiaomi/internal/telephony/VendorRIL;->mMockModem:Lcom/android/internal/telephony/MockModem;",
    "const/4 v1, 0x1",
    "if-eqz v0, :cond_0",
    "return v1",
    ":cond_0",
]
MARK = "# OneOS: a HIDL radio"
INSERT = """    # OneOS: a HIDL radio (no AIDL IRadioData/<slot> declared) is AOSP RIL's; no wait for Xiaomi's AIDL rild
    sget-object v0, Landroid/hardware/radio/data/IRadioData;->DESCRIPTOR:Ljava/lang/String;
    new-instance v2, Ljava/lang/StringBuilder;
    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V
    invoke-virtual {v2, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v0, "/"
    invoke-virtual {v2, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    sget-object v0, Lcom/xiaomi/internal/telephony/VendorRIL;->AIDL_SERVICE_NAME_XIAOMI:[Ljava/lang/String;
    iget-object v3, p0, Lcom/xiaomi/internal/telephony/VendorRIL;->mPhoneId:Ljava/lang/Integer;
    invoke-virtual {v3}, Ljava/lang/Integer;->intValue()I
    move-result v3
    aget-object v0, v0, v3
    invoke-virtual {v2, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v0
    invoke-static {v0}, Landroid/os/ServiceManager;->isDeclared(Ljava/lang/String;)Z
    move-result v0
    if-nez v0, :oneos_aidl_radio
    return v1
    :oneos_aidl_radio
"""


def main(root):
    path = next((os.path.join(root, d, CLS) for d in sorted(os.listdir(root))
                 if d.startswith("smali") and os.path.isfile(os.path.join(root, d, CLS))), None)
    if not path:
        sys.exit(f"{CLS} not found, not patching")
    text = open(path).read()
    if MARK in text:
        sys.exit("already patched")
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if l.strip() == HEAD[0]), None)
    if start is None:
        sys.exit("isRildReady()Z not found, not patching")
    # The method's first instructions, .line and blank lines aside, must be the ones above.
    seen, i = [], start
    while len(seen) < len(HEAD) and i < len(lines):
        s = lines[i].strip()
        if s and not s.startswith(".line"):
            seen.append((s, i))
        i += 1
    if [s for s, _ in seen] != HEAD:
        sys.exit("isRildReady() does not start with the MockModem check this was written against: "
                 + " | ".join(s for s, _ in seen))
    for name in ("AIDL_SERVICE_NAME_XIAOMI:[Ljava/lang/String;", "mPhoneId:Ljava/lang/Integer;"):
        if f".field private static final {name}" not in text and f".field private {name}" not in text \
                and f".field private final {name}" not in text and name not in text:
            sys.exit(f"VendorRIL has no {name}, not patching")
    # .locals 5 gives v0-v4; the insert uses v0, v2 and v3 and keeps v1 (true).
    at = seen[-1][1] + 1
    lines[at:at] = INSERT.rstrip("\n").split("\n")
    open(path, "w").write("\n".join(lines))
    print("VendorRIL.isRildReady: true without a declared AIDL IRadioData/<slot> (HIDL radio)", file=sys.stderr)
    print(os.path.relpath(path, root).split(os.sep)[0])


if __name__ == "__main__":
    main(sys.argv[1])
