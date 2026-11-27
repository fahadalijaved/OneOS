"""One UI 9.5's camera2 on a One UI 8.0/8.5 cameraserver: CaptureResultExtras without multiResConcurrentReadersStartInfo.

Android 17 (API 37, One UI 9.0/9.5) appended a non-size-prefixed typed array
multiResConcurrentReadersStartInfo (MultiResConcurrentReadersStartInfo[]) to
CaptureResultExtras.readFromParcel(). One UI 8.0 (Android 16 BP2A) and One UI 8.5
(Android 16 QPR2 BP4A) cameraservers do not write this field. Reading it from a
One UI 8.0/8.5 parcel consumes the following long timestamp in
ICameraDeviceCallbacks.onCaptureStarted (causing OutOfMemoryError/BadParcelableException
or a null array that NPEs in sendOnMultiResolutionOutputStarted) and consumes
PhysicalCaptureResultInfo[] in onResultReceived (breaking multi-camera fusion/portrait).

Replaces that read with an empty non-null MultiResConcurrentReadersStartInfo[0] array.

Usage: a16_camera_result_extras.py <apktool decoded framework.jar dir>
Prints the smali directory it changed (fails closed when the field exists but the read
pattern is not found exactly once).
"""
import os
import re
import sys

CLS = "android/hardware/camera2/impl/CaptureResultExtras.smali"
READ = re.compile(
    r"^([ \t]*)sget-object ([vp]\d+), Landroid/hardware/camera2/impl/MultiResConcurrentReadersStartInfo;->CREATOR:Landroid/os/Parcelable\$Creator;\n"
    r"(?:\s*(?:\.line \d+\s*)?\n)*"
    r"[ \t]*invoke-virtual \{[vp]\d+, \2\}, Landroid/os/Parcel;->createTypedArray\(Landroid/os/Parcelable\$Creator;\)\[Ljava/lang/Object;\n"
    r"(?:\s*(?:\.line \d+\s*)?\n)*"
    r"[ \t]*move-result-object ([vp]\d+)\n"
    r"(?:\s*(?:\.line \d+\s*)?\n)*"
    r"[ \t]*check-cast \3, \[Landroid/hardware/camera2/impl/MultiResConcurrentReadersStartInfo;\n",
    re.M,
)


def main(root):
    hits = [os.path.join(root, d, CLS) for d in sorted(os.listdir(root))
            if d.startswith("smali") and os.path.isfile(os.path.join(root, d, CLS))]
    if len(hits) != 1:
        sys.exit(f"a16_camera_result_extras: {CLS} found {len(hits)} times")
    with open(hits[0]) as f:
        text = f.read()
    if "multiResConcurrentReadersStartInfo" not in text:
        print("a16_camera_result_extras: unchanged (no multiResConcurrentReadersStartInfo)", file=sys.stderr)
        return
    if "a16_camera_result_extras.py" in text:
        print("a16_camera_result_extras: unchanged (already patched)", file=sys.stderr)
        return
    ms = list(READ.finditer(text))
    if len(ms) != 1:
        sys.exit(f"a16_camera_result_extras: multiResConcurrentReadersStartInfo read matched {len(ms)} times (one expected)")
    m = ms[0]
    ind, r_tmp, r_arr = m.group(1), m.group(2), m.group(3)
    rep = (
        f"{ind}# OneOS: One UI 8.0/8.5 (Android 16) cameraserver does not write multiResConcurrentReadersStartInfo (a16_camera_result_extras.py).\n"
        f"{ind}const/4 {r_tmp}, 0x0\n\n"
        f"{ind}new-array {r_arr}, {r_tmp}, [Landroid/hardware/camera2/impl/MultiResConcurrentReadersStartInfo;\n"
    )
    with open(hits[0], "w") as f:
        f.write(text[:m.start()] + rep + text[m.end():])
    print("a16_camera_result_extras: CaptureResultExtras.readFromParcel returns empty MultiResConcurrentReadersStartInfo[]", file=sys.stderr)
    print(os.path.relpath(hits[0], root).split(os.sep)[0])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
