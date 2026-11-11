"""Make the guest framework open Samsung's AIDL v3 fingerprint HAL.

Samsung's fingerprint service on the host declares only
android.hardware.biometrics.fingerprint.IFingerprint/default (AIDL v3); there
is no HIDL 2.1 IBiometricsFingerprint service. ColorOS's
FingerprintSensorConfigurations reports
resetLockoutRequiresHardwareAuthToken=false, and FingerprintProvider.initSensors
treats that flag as the transport choice: false adds
HidlToAidlSensorAdapter wrappers and asks hwservicemanager for the missing
HIDL 2.1 HAL (null -> "Fingerprint HAL not available" and a NullPointerException
in FingerprintUpdateActiveUserClient), true adds the native AIDL sensor.

The guest's enrolled prints are already read from One UI's snapshot
(settings_fingerprint.xml), so this only changes which adapter the guest
framework uses to reach the same host HAL.

Usage: guest_force_aidl_fingerprint.py <smali root dir>
Prints the smali_* directories (dex files) it changed, one per line.
"""
import os
import re
import sys

OLD = """    .line 1201
    invoke-virtual {p1}, Landroid/hardware/fingerprint/FingerprintSensorConfigurations;->getResetLockoutRequiresHardwareAuthToken()Z

    move-result v3
"""
NEW = """    .line 1201
    # OneOS: Samsung's HAL is AIDL v3 only; the false value picked the absent
    # HIDL 2.1 adapter. initSensors treats true as "add AIDL sensors".
    const/4 v3, 0x1
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
    if src.count(OLD) != 1:
        sys.exit(f"{rel}: getProviders lockout-auth-token read not found once")
    open(path, "w").write(src.replace(OLD, NEW, 1))
    print("FingerprintService.getProviders: forced resetLockoutRequiresHardwareAuthToken=true",
          file=sys.stderr)
    print(os.path.relpath(path, root).split(os.sep)[0])


if __name__ == "__main__":
    main(sys.argv[1])
