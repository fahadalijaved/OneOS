#!/usr/bin/env python3
"""Filter hidden auxiliary cameras by camera ID, not ArrayMap position.

Some Samsung camera providers announce device status in an order unrelated to
the numeric camera ID. Android's CameraManager implementation in the
Infinity-X framework limits the device-status ArrayMap to its first two entries
when auxiliary cameras are hidden. On the Galaxy A15 one of those entries is
camera 23, while the real rear torch is camera 0. Infinity-X also allowlists
SystemUI for auxiliary cameras, so its flashlight controller sees 23 and saves
it instead of 0, then ignores torch callbacks for 0.

For every caller, force the existing auxiliary-camera policy off. Walk the
complete status map and, when that policy is off, keep the public IDs 0 and 1.
This is what One UI does to regular applications anyway: with the image's
original allowlist policy the whole status map leaks through in announcement
order, and a third-party app then takes the first entry — a wide or auxiliary
camera — as its default back camera (Telegram on the Galaxy A15 opened the
wide lens instead of camera 0). The existing status and device-policy checks
still run unchanged. Refuse unless the known method shape matches exactly.

Usage: camera_aux_id_filter.py <apktool decoded framework.jar dir>
Prints the one smali directory changed.
"""
import os
import re
import sys


REL = os.path.join(
    "android", "hardware", "camera2", "CameraManager$CameraManagerGlobal.smali"
)
MARKER = "# OneOS: filter hidden auxiliary cameras by numeric ID, not map position."


def die(message):
    raise SystemExit(f"camera_aux_id_filter: {message}")


def find_smali(root):
    hits = [
        os.path.join(root, directory, REL)
        for directory in sorted(os.listdir(root))
        if directory.startswith("smali") and os.path.isfile(os.path.join(root, directory, REL))
    ]
    if len(hits) != 1:
        die(f"{REL} found {len(hits)} times under {root} (one expected)")
    return hits[0]


def method(text):
    pattern = re.compile(
        r"^\.method private extractCameraIdListLocked\(II\)\[Ljava/lang/String;\n"
        r".*?^\.end method$",
        re.M | re.S,
    )
    hits = list(pattern.finditer(text))
    if len(hits) != 1:
        die(f"extractCameraIdListLocked found {len(hits)} times (one expected)")
    return hits[0]


def patch(root):
    path = find_smali(root)
    with open(path, encoding="utf-8") as source:
        text = source.read()
    hit = method(text)
    body = hit.group(0)
    if MARKER in body:
        return None

    locals_hits = re.findall(r"^    \.locals (\d+)$", body, re.M)
    if locals_hits != ["7"]:
        die(f"extractCameraIdListLocked locals are {locals_hits}, expected ['7']")

    limit = re.compile(
        r"(    invoke-static \{\}, Landroid/hardware/Camera;->shouldExposeAuxCamera\(\)Z\n\n"
        r"    move-result )v1"
        r"(\n.*?    const/4 v2, 0x2\n\n)"
        r"    if-eqz v1, :cond_0\n\n"
        r"(    iget-object v1, p0, Landroid/hardware/camera2/CameraManager\$CameraManagerGlobal;->mDeviceStatus:Landroid/util/ArrayMap;\n\n"
        r"    invoke-virtual \{v1\}, Landroid/util/ArrayMap;->size\(\)I\n\n"
        r"    move-result v1\n)"
        r"\n    goto :goto_0\n\n"
        r"    :cond_0\n"
        r"    move v1, v2\n"
        r"(\n.*?    :goto_0\n)",
        re.S,
    )
    policy = (
        r"\1v7"
        "\n\n"
        "    # OneOS: every caller gets the public camera IDs; aux cameras stay\n"
        "    # hidden from third-party apps exactly like One UI's own policy.\n"
        "    const/4 v7, 0x0\n\n"
        r"\2\3\4"
    )
    body, count = limit.subn(policy, body)
    if count != 1:
        die(f"auxiliary-camera loop limit matched {count} times (one expected)")

    key = (
        "    check-cast v6, "
        "Landroid/hardware/camera2/CameraManager$CameraManagerGlobal$DeviceCameraInfo;\n"
    )
    if body.count(key) != 1:
        die(f"device-info loop key matched {body.count(key)} times (one expected)")
    camera_id = (
        "\n"
        f"    {MARKER}\n"
        "    if-nez v7, :oneos_camera_aux_allowed\n\n"
        "    invoke-static {v6}, Landroid/hardware/camera2/CameraManager$CameraManagerGlobal$DeviceCameraInfo;->-$$Nest$fgetmCameraId(Landroid/hardware/camera2/CameraManager$CameraManagerGlobal$DeviceCameraInfo;)Ljava/lang/String;\n\n"
        "    move-result-object v8\n\n"
        "    const-string v9, \"0\"\n\n"
        "    invoke-virtual {v9, v8}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z\n\n"
        "    move-result v9\n\n"
        "    if-nez v9, :oneos_camera_aux_allowed\n\n"
        "    const-string v9, \"1\"\n\n"
        "    invoke-virtual {v9, v8}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z\n\n"
        "    move-result v9\n\n"
        "    if-eqz v9, :goto_2\n\n"
        "    :oneos_camera_aux_allowed\n"
    )
    body = body.replace(key, key + camera_id)
    body = body.replace("    .locals 7\n", "    .locals 10\n", 1)

    text = text[:hit.start()] + body + text[hit.end():]
    with open(path, "w", encoding="utf-8", newline="") as output:
        output.write(text)
    return os.path.relpath(path, root).split(os.sep, 1)[0]


def main():
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        die("usage: camera_aux_id_filter.py <apktool decoded framework.jar dir>")
    changed = patch(sys.argv[1])
    if changed:
        print(changed)
    else:
        print("unchanged", file=sys.stderr)


if __name__ == "__main__":
    main()
