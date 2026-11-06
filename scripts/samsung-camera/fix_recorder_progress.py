"""One UI's camera in a guest: the recording timer runs.

One UI's MediaRecorder reports the recording's duration while it records (info 0x385,
DURATION_IN_PROGRESS, in ms). AOSP's does not, so the camera's timer stayed at 00:00 and the
recording looked stopped (Pixel on the Z Fold8 Ultra, 0.4.59 test). helpers/smali/
OneOSRecordProgress.smali (helpers/src, helpers/build.sh) reports the time since the start every
500 ms (a 0 first, which starts the camera's own timer) until the camera stops that recorder;
OneOSTrackStart.start (fix_recorder_track_started.py, which must run first) starts it next to its
track-started reports, on the same main-thread handler, and the recording session's
MediaRecorder.stop() goes through OneOSRecordProgress.stop. Runs again on a camera that already
has an earlier OneOSRecordProgress: the helper is replaced, nothing is added twice.

Usage: fix_recorder_progress.py <smali root of the decoded camera APK>
Prints the smali_* directory it changed; the summary goes to stderr.
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
POST = "invoke-virtual {v2, v1, v3, v4}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z"
STOP = re.compile(r"invoke-virtual \{([vp]\d+)\}, Landroid/media/MediaRecorder;->stop\(\)V")
STOP_NEW = "Loneos/camera/OneOSRecordProgress;->stop(Landroid/media/MediaRecorder;)V"
CALL = ("    invoke-static {p1, p0, v2}, Loneos/camera/OneOSRecordProgress;->start(Landroid/media/MediaRecorder$OnInfoListener;"
        "Landroid/media/MediaRecorder;Landroid/os/Handler;)V")


def main(root):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs if f == "OneOSTrackStart.smali"]
    if len(hits) != 1:
        sys.exit(f"expected one OneOSTrackStart.smali (fix_recorder_track_started.py first), found {len(hits)}")
    p = hits[0]
    s = open(p).read()
    dirs = {os.path.relpath(p, root).split(os.sep)[0]}
    if "OneOSRecordProgress" not in s:
        i = s.index(".method public static start(")
        j = s.index(".end method", i)
        body = s[i:j]
        if body.count(POST) != 1:
            sys.exit(f"{p}: start() has no single postDelayed to put the progress next to")
        s = s[:i] + body.replace(POST, POST + "\n" + CALL) + s[j:]
        open(p, "w").write(s)
    shutil.copyfile(os.path.join(HERE, "helpers", "smali", "OneOSRecordProgress.smali"),
                    os.path.join(os.path.dirname(p), "OneOSRecordProgress.smali"))
    # Every MediaRecorder.stop() (the fold camera stops it from a session state class, e9/c) first
    # ends that recorder's reports; a recorder without them just stops.
    n = 0
    for d, _, fs in os.walk(root):
        if os.sep + os.path.join("oneos", "camera") in d:
            continue
        for f in fs:
            if f.endswith(".smali"):
                q = os.path.join(d, f)
                t = open(q).read()
                t, k = STOP.subn(lambda m: f"invoke-static {{{m.group(1)}}}, {STOP_NEW}", t)
                if k:
                    open(q, "w").write(t)
                    n += k
                    dirs.add(os.path.relpath(q, root).split(os.sep)[0])
    if not n and STOP_NEW not in "".join(open(os.path.join(d, f)).read() for d, _, fs in os.walk(root)
                                         if os.sep + os.path.join("oneos", "camera") not in d
                                         for f in fs if f.endswith(".smali")):
        sys.exit("no MediaRecorder.stop() in the camera")
    for x in sorted(dirs):
        print(x)
    print(f"recording progress: OneOSRecordProgress (0 first, then the time) from OneOSTrackStart; {n} stop() call(s) through it", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
