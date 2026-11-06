"""One UI's camera in a guest: videos with their rotation (written after the stop).

The camera sets a video's orientation when recording starts, after MediaRecorder.prepare().
AOSP's recorder refuses every parameter once prepared, and oneos.semcompat.OneOSRecorder (the
compat layer, fix_recorder_location.py) catches that so the recording goes on: guest videos had
no rotation tag and played sideways, photos were fine (owner, 0.4.59). Routed to
oneos.camera.OneOSRotation (helpers/src, helpers/build.sh):
  - setOrientationHint (OneOSRecorder's or MediaRecorder's): to the recorder, else remembered;
  - MediaRecorder.setOutputFile(String | FileDescriptor): passed on and remembered;
  - OneOSRecordProgress.stop (fix_recorder_progress.py, which must run first): that stop, then
    the remembered rotation into the finished file's video track header (OneOSMp4, in place).
The helpers go next to OneOSRecordProgress.smali, replaced on every run; a camera patched before
keeps its call sites.

Usage: fix_video_rotation.py <smali root of the decoded camera APK>
Prints the smali_* directories (dex files) it changed, one per line; the summary goes to stderr.
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
H = "Loneos/camera/OneOSRotation;"
MR = "Landroid/media/MediaRecorder;"
RULES = [
    (re.compile(r"invoke-static(/range)? \{([^}]*)\}, Loneos/semcompat/OneOSRecorder;->setOrientationHint\(Landroid/media/MediaRecorder;I\)V"),
     lambda m: f"invoke-static{m.group(1) or ''} {{{m.group(2)}}}, {H}->setOrientationHint({MR}I)V"),
    (re.compile(r"invoke-virtual(/range)? \{([^}]*)\}, Landroid/media/MediaRecorder;->setOrientationHint\(I\)V"),
     lambda m: f"invoke-static{m.group(1) or ''} {{{m.group(2)}}}, {H}->setOrientationHint({MR}I)V"),
    (re.compile(r"invoke-virtual(/range)? \{([^}]*)\}, Landroid/media/MediaRecorder;->setOutputFile\((Ljava/lang/String;|Ljava/io/FileDescriptor;)\)V"),
     lambda m: f"invoke-static{m.group(1) or ''} {{{m.group(2)}}}, {H}->setOutputFile({MR}{m.group(3)})V"),
    (re.compile(r"invoke-static(/range)? \{([^}]*)\}, Loneos/camera/OneOSRecordProgress;->stop\(Landroid/media/MediaRecorder;\)V"),
     lambda m: f"invoke-static{m.group(1) or ''} {{{m.group(2)}}}, {H}->stop({MR})V"),
]
HELPERS = ["OneOSRotation.smali", "OneOSRotation$1.smali", "OneOSRotation$2.smali", "OneOSMp4.smali", "OneOSMp4$Io.smali"]


def main(root):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs if f == "OneOSRecordProgress.smali"]
    if len(hits) != 1:
        sys.exit(f"expected one OneOSRecordProgress.smali (fix_recorder_progress.py first), found {len(hits)}")
    helper_dir = os.path.dirname(hits[0])
    dirs = {os.path.relpath(helper_dir, root).split(os.sep)[0]}
    for h in HELPERS:
        shutil.copyfile(os.path.join(HERE, "helpers", "smali", h), os.path.join(helper_dir, h))
    counts = [0] * len(RULES)
    seen = {"setOrientationHint": False, "setOutputFile": False, "stop": False}
    for d, _, fs in os.walk(root):
        if os.sep + os.path.join("oneos", "camera") in d:
            continue
        for f in fs:
            if not f.endswith(".smali"):
                continue
            p = os.path.join(d, f)
            s = open(p).read()
            if "setOrientationHint" not in s and "setOutputFile" not in s and "OneOSRecordProgress;->stop" not in s and H not in s:
                continue
            s2 = s
            for i, (rx, rep) in enumerate(RULES):
                s2, k = rx.subn(rep, s2)
                counts[i] += k
            for name in seen:
                seen[name] = seen[name] or f"{H}->{name}(" in s2
            if s2 != s:
                open(p, "w").write(s2)
                dirs.add(os.path.relpath(p, root).split(os.sep)[0])
    missing = [n for n, ok in seen.items() if not ok]
    if missing:
        sys.exit(f"no {', '.join(missing)} call routed to OneOSRotation")
    for x in sorted(dirs):
        print(x)
    print("video rotation: %d orientation hint(s), %d plain orientation hint(s), %d output file(s), %d stop(s) to OneOSRotation" % tuple(counts),
          file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
