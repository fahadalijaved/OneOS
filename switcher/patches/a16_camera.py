"""One UI 9.5's framework.jar against a One UI 8 cameraserver (framework_patched_oneui8.jar, 0.5.39).

Run by scripts/patch-built-jar.sh on the oneui95-a16 set's framework_patched.jar (every other patch of
that set kept): the camera interface classes are first put back as the image
has them (from ONEOS_CAMERA_ORIG_DECODED, the image's framework.jar decoded by apktool; the set's copies
carry One UI 9.0's numbering), then pixel_camera_abi.py renumbers them to switcher/patches/
host_camera_oneui8.txt with ONEOS_CAMERA_COMPAT_AS_INT=1, and a16_camera_batch_off.py keeps stream
configuration on the calls One UI 8 has.

ONEOS_A16_CAMERA_HOST=oneui85 (framework_patched_oneui85.jar, 0.5.45): a One UI 8.5 cameraserver instead
(switcher/patches/host_camera_oneui85.txt, read on the S23 FE): One UI 8's numbering but One UI 9.0's
CameraCompatibilityInfo parcelable, so the parcelable is written as it is (no ONEOS_CAMERA_COMPAT_AS_INT;
ONEOS_CAMERA_COMPAT_FROM_JAR: the set's jar already writes it without the sixth field, as for One UI 9.0). The One UI 8 jar on such a phone sent an int there and
cameraserver answered every getCameraCharacteristics with a NullPointerException (S23 FE 8a093c12, A35
5434447d: no camera; Samsung's video call engine com.sec.sve restarted about 2,000 times a session).

Usage: [ONEOS_A16_CAMERA_HOST=oneui85] ONEOS_CAMERA_ORIG_DECODED=<dir> a16_camera.py <decoded jar dir>
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CLASSES = [
    "android/hardware/ICameraService$Stub$Proxy.smali", "android/hardware/ICameraService$Stub.smali",
    "android/hardware/ICameraServiceListener$Stub$Proxy.smali", "android/hardware/ICameraServiceListener$Stub.smali",
    "android/hardware/camera2/ICameraDeviceUser$Stub$Proxy.smali", "android/hardware/camera2/ICameraDeviceUser$Stub.smali",
    "android/hardware/camera2/ICameraDeviceCallbacks$Stub$Proxy.smali", "android/hardware/camera2/ICameraDeviceCallbacks$Stub.smali",
]


def where(root, cls):
    hits = [d for d in sorted(os.listdir(root)) if d.startswith("smali") and os.path.isfile(os.path.join(root, d, cls))]
    if len(hits) != 1:
        sys.exit(f"a16_camera: {cls} found {len(hits)} times under {root}")
    return hits[0]


def main(root):
    orig = os.environ.get("ONEOS_CAMERA_ORIG_DECODED")
    if not orig or not os.path.isdir(orig):
        sys.exit("a16_camera: ONEOS_CAMERA_ORIG_DECODED (the image's decoded framework.jar) is required")
    dirs = set()
    for cls in CLASSES:
        d, o = where(root, cls), where(orig, cls)
        if d != o:
            sys.exit(f"a16_camera: {cls} in {d} here, {o} in the image")
        shutil.copyfile(os.path.join(orig, o, cls), os.path.join(root, d, cls))
        dirs.add(d)
    host = os.environ.get("ONEOS_A16_CAMERA_HOST", "oneui8")
    if host not in ("oneui8", "oneui85"):
        sys.exit(f"a16_camera: ONEOS_A16_CAMERA_HOST={host} (oneui8 or oneui85)")
    env = dict(os.environ)
    env.pop("ONEOS_CAMERA_KEEP_COMPAT", None)
    env.pop("ONEOS_CAMERA_COMPAT_AS_INT", None)
    if host == "oneui8":
        env["ONEOS_CAMERA_COMPAT_AS_INT"] = "1"
    else:
        env["ONEOS_CAMERA_COMPAT_FROM_JAR"] = "1"
    for cmd in (["python3", "-I", os.path.join(HERE, "pixel_camera_abi.py"), root, os.path.join(HERE, f"host_camera_{host}.txt")],
                ["python3", "-I", os.path.join(HERE, "a16_camera_batch_off.py"), root],
                ["python3", "-I", os.path.join(HERE, "a16_camera_result_extras.py"), root]):
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        sys.stderr.write(r.stderr)
        if r.returncode != 0:
            sys.exit(f"a16_camera: {os.path.basename(cmd[2])} failed")
        dirs.update(l for l in r.stdout.split() if l)
    for d in sorted(dirs):
        print(d)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
