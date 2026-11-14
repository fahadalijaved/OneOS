"""Make the guest framework reach the phone's fingerprint HAL whatever transport it uses.

The guest's FingerprintService picks its sensor adapter from
FingerprintSensorConfigurations.resetLockoutRequiresHardwareAuthToken: false
adds HidlToAidlSensorAdapter wrappers and asks hwservicemanager for the HIDL
2.1 IBiometricsFingerprint HAL, true adds the native AIDL sensor. ColorOS 17
reports false, and on a phone whose HAL is AIDL only (Samsung, Pixel, most
2023+ devices) the guest then logs "Fingerprint HAL not available" and
FingerprintUpdateActiveUserClient retries forever with a NullPointerException,
so the keyguard never offers fingerprint.

The flag is replaced with a question the phone answers: is
android.hardware.biometrics.fingerprint.IFingerprint/default registered? It is
on every AIDL HAL; on a HIDL-only phone the lookup returns null and the image's
own value is used, which is what that image shipped for its own HAL.

Usage: guest_force_aidl_fingerprint.py <smali root dir>
Prints the smali_* directories (dex files) it changed, one per line.
"""
import os
import re
import sys

METHOD = """.method private getProviders(Landroid/hardware/fingerprint/FingerprintSensorConfigurations;)Ljava/util/List;
    .locals 4
"""
METHOD_NEW = """.method private getProviders(Landroid/hardware/fingerprint/FingerprintSensorConfigurations;)Ljava/util/List;
    .locals 5
"""

# The read sits in a different .line block per image (ColorOS 1201, HyperOS
# 1182); match the instruction, not its line number.
INVOKE = re.compile(
    r"(?m)^(?P<indent>[ \t]*)"
    r"invoke-virtual \{p1\}, Landroid/hardware/fingerprint/FingerprintSensorConfigurations;->"
    r"getResetLockoutRequiresHardwareAuthToken\(\)Z[ \t]*\n"
    r"(?:[ \t]*\n)?"
    r"(?P<move>[ \t]*)move-result v3[ \t]*\n"
)
NEW = """{indent}# OneOS: the image's flag names its own HAL's transport (false = HIDL 2.1).
{indent}# Ask the phone instead: the AIDL instance is there on every AIDL HAL, and
{indent}# its absence leaves a HIDL image with the value it shipped.
{indent}const-string v4, "android.hardware.biometrics.fingerprint.IFingerprint/default"

{indent}invoke-static {{v4}}, Landroid/os/ServiceManager;->getService(Ljava/lang/String;)Landroid/os/IBinder;

{indent}move-result-object v4

{indent}if-eqz v4, :oneos_fingerprint_hidl

{indent}const/4 v3, 0x1

{indent}goto :oneos_fingerprint_transport

{indent}:oneos_fingerprint_hidl
{indent}invoke-virtual {{p1}}, Landroid/hardware/fingerprint/FingerprintSensorConfigurations;->getResetLockoutRequiresHardwareAuthToken()Z

{indent}move-result v3

{indent}:oneos_fingerprint_transport
"""


def find(root, rel_suffix):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
            if os.path.join(d, f).endswith(rel_suffix)]
    if len(hits) != 1:
        sys.exit(f"expected exactly one {rel_suffix}, found {len(hits)}")
    return hits[0]


def main(root):
    rel = os.path.join("com", "android", "server", "biometrics", "sensors",
                       "fingerprint", "FingerprintService.smali")
    path = find(root, rel)
    src = open(path).read()
    if src.count(METHOD) != 1:
        sys.exit(f"{rel}: getProviders is not there once with .locals 4")
    hits = list(INVOKE.finditer(src))
    if len(hits) != 1:
        sys.exit(f"{rel}: the getResetLockoutRequiresHardwareAuthToken read is not there once (found {len(hits)})")
    m = hits[0]
    src = src[:m.start()] + NEW.format(indent=m.group("indent")) + src[m.end():]
    src = src.replace(METHOD, METHOD_NEW, 1)
    open(path, "w").write(src)
    print("FingerprintService.getProviders: AIDL sensor when the AIDL HAL is registered, "
          "the image's flag otherwise", file=sys.stderr)
    print(os.path.relpath(path, root).split(os.sep)[0])


if __name__ == "__main__":
    main(sys.argv[1])
