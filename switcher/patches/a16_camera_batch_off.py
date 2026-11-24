"""One UI 9.5's camera2 on a One UI 8 cameraserver: stream configuration without configureStreams.

The image's CameraDeviceImpl.configureStreamsChecked sends one ICameraDeviceUser.configureStreams
(Android 17's batch call) when the camera flag configureStreamsBatch is on, and beginConfigure,
createStream/deleteStream and endConfigure otherwise. One UI 8's ICameraDeviceUser has no
configureStreams (switcher/patches/host_camera_oneui8.txt; pixel_camera_abi.py makes the Proxy throw
RemoteException for it), so the flag reads false in that method: the old calls, which One UI 8 has.

Usage: a16_camera_batch_off.py <apktool decoded framework.jar dir>
Prints the smali directory it changed (fails closed when the call is not found exactly once).
"""
import os
import re
import sys

CLS = "android/hardware/camera2/impl/CameraDeviceImpl.smali"
CALL = re.compile(
    r"^(\s*)invoke-static \{\}, Lcom/android/internal/hidden_from_bootclasspath/com/android/internal/camera/flags/Flags;->configureStreamsBatch\(\)Z\n"
    r"(\s*\n)*\s*move-result ([vp]\d+)\n", re.M)


def main(root):
    hits = [os.path.join(root, d, CLS) for d in sorted(os.listdir(root)) if d.startswith("smali") and os.path.isfile(os.path.join(root, d, CLS))]
    if len(hits) != 1:
        sys.exit(f"a16_camera_batch_off: {CLS} found {len(hits)} times")
    text = open(hits[0]).read()
    m = list(CALL.finditer(text))
    if len(m) != 1:
        sys.exit(f"a16_camera_batch_off: configureStreamsBatch() read {len(m)} times (one expected)")
    m = m[0]
    text = text[:m.start()] + f"{m.group(1)}# OneOS: One UI 8 has no ICameraDeviceUser.configureStreams (a16_camera_batch_off.py).\n{m.group(1)}const/4 {m.group(3)}, 0x0\n" + text[m.end():]
    open(hits[0], "w").write(text)
    print("a16_camera_batch_off: configureStreamsBatch read as false in CameraDeviceImpl", file=sys.stderr)
    print(os.path.relpath(hits[0], root).split(os.sep)[0])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
