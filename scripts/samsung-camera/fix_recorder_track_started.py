"""One UI's camera in a guest: videos kept when Stop is pressed.

One UI's MediaRecorder reports each track it starts writing with an info event of its own (905,
0x389). The camera's recording session (the class that is the recorder's OnInfoListener and maps
905 to "onTrackStarted") counts the tracks down from 2 (video and audio) in an AtomicInteger, and
the Stop button only stops a recording whose sessions all reached 0; otherwise it cancels it
("RecordingManager: changeRecordingState : RECORDING -> CANCELLING", CANCEL_VIDEO_RECORDING), which
deletes the file. A guest's MediaRecorder is AOSP's and never sends 905, so every video was
cancelled on Stop (Pixel on the Z Fold8 Ultra, session 9455098f: "camera fails to record video").

The session's MediaRecorder.start() call goes to Loneos/camera/OneOSTrackStart;->start, which
starts the recorder and, 300 ms later on the main thread (where the recorder's own info events
arrive), reports 905 to the session for each track still counted, as One UI's recorder does once
the first frames are written. A recorder that did send 905 has counted down already and gets
nothing more.

The helper goes into a dex of its own (a new smali_classesN), as with fix_notification_icon.py: the
camera's dex files are near their 65536 method ids.

Usage: fix_recorder_track_started.py <smali root of the decoded camera APK>
Prints the smali_* directories (dex files) it changed or added, one per line; the summary goes to
stderr.
"""
import os
import re
import sys

HELPER = "Loneos/camera/OneOSTrackStart;"
LISTENER = ".implements Landroid/media/MediaRecorder$OnInfoListener;"
TRACK_STARTED = 'const-string %s, "onTrackStarted: next output file started."'
START = re.compile(r"^(\s*)invoke-virtual \{([vp]\d+)\}, Landroid/media/MediaRecorder;->start\(\)V\s*$")
P0_WRITE = re.compile(r"^\s*(move(-object|-result(-object)?)?(/from16|/16)?|const[-/a-z0-9]*|iget[-a-z]*|sget[-a-z]*|"
                      r"new-instance|new-array|aget[-a-z]*|[a-z-]+/2addr|[a-z]+-int(/lit8|/lit16)?|instance-of|array-length) p0,")

HELPER_SMALI = """.class public final Loneos/camera/OneOSTrackStart;
.super Ljava/lang/Object;
.source "OneOSTrackStart.smali"

# interfaces
.implements Ljava/lang/Runnable;


# instance fields
.field private final pending:Ljava/util/concurrent/atomic/AtomicInteger;

.field private final recorder:Landroid/media/MediaRecorder;

.field private final session:Landroid/media/MediaRecorder$OnInfoListener;


# direct methods
.method private constructor <init>(Landroid/media/MediaRecorder$OnInfoListener;Landroid/media/MediaRecorder;Ljava/util/concurrent/atomic/AtomicInteger;)V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    iput-object p1, p0, Loneos/camera/OneOSTrackStart;->session:Landroid/media/MediaRecorder$OnInfoListener;
    iput-object p2, p0, Loneos/camera/OneOSTrackStart;->recorder:Landroid/media/MediaRecorder;
    iput-object p3, p0, Loneos/camera/OneOSTrackStart;->pending:Ljava/util/concurrent/atomic/AtomicInteger;
    return-void
.end method

.method public static start(Landroid/media/MediaRecorder;Landroid/media/MediaRecorder$OnInfoListener;)V
    .locals 5
    invoke-virtual {p0}, Landroid/media/MediaRecorder;->start()V
    move-object v0, p1
    check-cast v0, @SESSION@
    iget-object v0, v0, @SESSION@->@FIELD@:Ljava/util/concurrent/atomic/AtomicInteger;
    new-instance v1, Loneos/camera/OneOSTrackStart;
    invoke-direct {v1, p1, p0, v0}, Loneos/camera/OneOSTrackStart;-><init>(Landroid/media/MediaRecorder$OnInfoListener;Landroid/media/MediaRecorder;Ljava/util/concurrent/atomic/AtomicInteger;)V
    new-instance v2, Landroid/os/Handler;
    invoke-static {}, Landroid/os/Looper;->getMainLooper()Landroid/os/Looper;
    move-result-object v0
    invoke-direct {v2, v0}, Landroid/os/Handler;-><init>(Landroid/os/Looper;)V
    const-wide/16 v3, 0x12c
    invoke-virtual {v2, v1, v3, v4}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z
    return-void
.end method


# virtual methods
.method public run()V
    .locals 5
    const/4 v0, 0x0
    :loop
    const/16 v1, 0x8
    if-ge v0, v1, :done
    iget-object v1, p0, Loneos/camera/OneOSTrackStart;->pending:Ljava/util/concurrent/atomic/AtomicInteger;
    invoke-virtual {v1}, Ljava/util/concurrent/atomic/AtomicInteger;->get()I
    move-result v1
    if-gtz v1, :report
    if-lez v0, :done
    const-string v1, "OneOSCamera"
    const-string v2, "recording tracks reported started (the recorder sends no 905)"
    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    goto :done
    :report
    iget-object v1, p0, Loneos/camera/OneOSTrackStart;->session:Landroid/media/MediaRecorder$OnInfoListener;
    iget-object v2, p0, Loneos/camera/OneOSTrackStart;->recorder:Landroid/media/MediaRecorder;
    const/16 v3, 0x389
    :try_start
    invoke-interface {v1, v2, v3, v0}, Landroid/media/MediaRecorder$OnInfoListener;->onInfo(Landroid/media/MediaRecorder;II)V
    :try_end
    .catch Ljava/lang/RuntimeException; {:try_start .. :try_end} :failed
    add-int/lit8 v0, v0, 0x1
    goto :loop
    :failed
    move-exception v1
    const-string v2, "OneOSCamera"
    const-string v3, "reporting recording tracks started failed"
    invoke-static {v2, v3, v1}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I
    :done
    return-void
.end method
"""


def method_bounds(lines, i):
    """Index of the .method line before i and whether that method is static."""
    for j in range(i, -1, -1):
        if lines[j].startswith(".method "):
            return j, " static " in lines[j]
    return None, None


def main(root):
    if not os.path.isdir(root):
        sys.exit(f"{root} is not a folder")
    sessions = []
    for d, _, fs in os.walk(root):
        for f in fs:
            if not f.endswith(".smali"):
                continue
            p = os.path.join(d, f)
            s = open(p).read()
            if LISTENER in s and re.search(r"const/16 [vp]\d+, 0x389\b", s):
                sessions.append(p)
    if len(sessions) != 1:
        sys.exit(f"expected one recording session class (MediaRecorder OnInfoListener with 905), found {len(sessions)}: {sessions}")
    p = sessions[0]
    lines = open(p).read().split("\n")
    cls = next(l.split()[-1] for l in lines if l.startswith(".class "))
    # The counter: the session's AtomicInteger field that the 905 handler counts down
    # (decrementAndGet a few instructions after reading it). The handler is in the
    # session class itself (the Z Fold8 Ultra's camera) or in a lambda class the
    # info map holds (the S26 Ultra's).
    fields = re.findall(r"^\.field [^\n]*?\b(\w+):Ljava/util/concurrent/atomic/AtomicInteger;$", "\n".join(lines), re.M)
    counted = set()
    for d, _, fs in os.walk(root):
        for f in fs:
            if not f.endswith(".smali"):
                continue
            t = open(os.path.join(d, f)).read()
            if cls + "->" not in t or "decrementAndGet()I" not in t:
                continue
            code = [l for l in t.split("\n") if l.strip() and not l.strip().startswith((".line", "#"))]
            for i, l in enumerate(code):
                for fl in fields:
                    if f"{cls}->{fl}:Ljava/util/concurrent/atomic/AtomicInteger;" in l and \
                            any("AtomicInteger;->decrementAndGet()I" in x for x in code[i + 1:i + 25]):
                        counted.add(fl)
    if len(counted) != 1:
        sys.exit(f"{p}: expected one AtomicInteger of {cls} counted down after a read, found {sorted(counted)}")
    field = counted.pop()
    # The helper reads the field from another package: make it public.
    for n, l in enumerate(lines):
        m = re.match(r"^\.field (.*?)\b" + re.escape(field) + r":Ljava/util/concurrent/atomic/AtomicInteger;$", l)
        if m:
            flags = [w for w in m.group(1).split() if w not in ("private", "protected", "public")]
            lines[n] = ".field " + " ".join(["public"] + flags) + f" {field}:Ljava/util/concurrent/atomic/AtomicInteger;"
            break
    else:
        sys.exit(f"{p}: field {field} not declared")
    calls = 0
    for n, l in enumerate(lines):
        m = START.match(l)
        if not m:
            continue
        j, static = method_bounds(lines, n)
        if j is None or static:
            sys.exit(f"{p}:{n + 1}: MediaRecorder.start() outside an instance method")
        if any(P0_WRITE.match(x) for x in lines[j:n]):
            sys.exit(f"{p}:{n + 1}: p0 is reassigned before MediaRecorder.start(); not patched")
        loc = re.search(r"\.locals (\d+)", "\n".join(lines[j:n]))
        if not loc or int(loc.group(1)) > 15 or (m.group(2).startswith("v") and int(m.group(2)[1:]) > 15):
            sys.exit(f"{p}:{n + 1}: registers past v15, a two-register invoke cannot reach them")
        lines[n] = f"{m.group(1)}invoke-static {{{m.group(2)}, p0}}, {HELPER}->start(Landroid/media/MediaRecorder;Landroid/media/MediaRecorder$OnInfoListener;)V"
        calls += 1
    if not calls:
        sys.exit(f"{p}: no MediaRecorder.start() call")
    open(p, "w").write("\n".join(lines))
    smali = [d for d in os.listdir(root) if re.fullmatch(r"smali(_classes\d+)?", d)]
    for d in smali:
        if os.path.exists(os.path.join(root, d, "oneos", "camera", "OneOSTrackStart.smali")):
            sys.exit(f"OneOSTrackStart.smali is already there ({d})")
    own = "smali_classes%d" % (max(int(d[len("smali_classes"):]) if d != "smali" else 1 for d in smali) + 1)
    out = os.path.join(root, own, "oneos", "camera")
    os.makedirs(out)
    open(os.path.join(out, "OneOSTrackStart.smali"), "w").write(HELPER_SMALI.replace("@SESSION@", cls).replace("@FIELD@", field))
    print(os.path.relpath(p, root).split(os.sep)[0])
    print(own)
    print(f"recorder track start: {calls} start() call(s) in {cls} (counter {field}) to OneOSTrackStart ({own})", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
