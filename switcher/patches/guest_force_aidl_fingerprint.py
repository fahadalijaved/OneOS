"""Make a Samsung guest framework use the native AIDL fingerprint provider.

Samsung exposes android.hardware.biometrics.fingerprint.IFingerprint/default,
but no legacy HIDL 2.1 service. Some ColorOS/Infinity-X frameworks interpret
resetLockoutRequiresHardwareAuthToken=false as a request for the HIDL adapter.
Force the boolean passed to getFingerprintProvider() to true so the framework
opens the host's AIDL sensor instead.

Usage: guest_force_aidl_fingerprint.py <smali root dir>
Prints the smali directory (dex file) it changed, one per line.
"""

import os
import re
import sys


SUFFIX = os.path.join(
    "com", "android", "server", "biometrics", "sensors", "fingerprint",
    "FingerprintService.smali",
)
CALL = re.compile(
    r"(?P<line>    \.line \d+\n)"
    r"    invoke-virtual \{[vp]\d+\}, "
    r"Landroid/hardware/fingerprint/FingerprintSensorConfigurations;"
    r"->getResetLockoutRequiresHardwareAuthToken\(\)Z\n\n"
    r"    move-result (?P<result>[vp]\d+)\n"
)


def main(root):
    hits = [
        os.path.join(directory, name)
        for directory, _, names in os.walk(root)
        for name in names
        if os.path.join(directory, name).endswith(os.sep + SUFFIX)
    ]
    if len(hits) != 1:
        sys.exit(f"expected exactly one {SUFFIX}, found {len(hits)}")

    path = hits[0]
    source = open(path, encoding="utf-8").read()
    matches = list(CALL.finditer(source))
    if len(matches) != 1:
        sys.exit(
            "FingerprintService: expected one fingerprint transport choice, "
            f"found {len(matches)}"
        )

    def replacement(match):
        return (
            match.group("line")
            + "    # OneOS: Samsung exposes the native AIDL fingerprint HAL only.\n"
            + f"    const/4 {match.group('result')}, 0x1\n"
        )

    patched = CALL.sub(replacement, source, count=1)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        output.write(patched)
    print("FingerprintService: forced the native AIDL fingerprint provider", file=sys.stderr)
    print(os.path.relpath(path, root).split(os.sep)[0])


if __name__ == "__main__":
    main(sys.argv[1])
