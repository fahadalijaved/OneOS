"""One UI's camera in a guest: its media entries without Samsung's media provider.

The camera records pictures and videos in Samsung's own provider (content://secmedia/media), which a
guest does not have: the video's insert came back null, the camera queried that null uri and
crashed after every recording ("Failed to find provider info for secmedia", "insertToDbForVideo
ContentResolver insert failed", NullPointerException: uri; Pixel on the Z Fold8 Ultra, 0.4.59 test).

Every ContentResolver.insert and query in the camera goes to helpers/smali/OneOSMedia.smali
(helpers/src, helpers/build.sh): any other uri, or a phone with secmedia, as before; otherwise an
insert goes to MediaStore (video, images or files by its mime type) with the standard columns only,
and a query on secmedia/media[/id] to MediaStore's files table (the camera's "camera bucket" check:
"isCameraBucketEmpty", so its thumbnail opened nothing). The helper goes into a dex of its own (a new
smali_classesN), as with fix_notification_icon.py; a camera that has an earlier OneOSMedia gets the
new one in its place.

Usage: fix_secmedia_insert.py <smali root of the decoded camera APK>
Prints the smali_* directories (dex files) it changed or added, one per line; the summary goes to
stderr.
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CR = "Landroid/content/ContentResolver;"
H = "Loneos/camera/OneOSMedia;"
_SIGS = {
    "insert(Landroid/net/Uri;Landroid/content/ContentValues;)Landroid/net/Uri;":
        f"insert({CR}Landroid/net/Uri;Landroid/content/ContentValues;)Landroid/net/Uri;",
    "query(Landroid/net/Uri;[Ljava/lang/String;Ljava/lang/String;[Ljava/lang/String;Ljava/lang/String;)Landroid/database/Cursor;":
        f"query({CR}Landroid/net/Uri;[Ljava/lang/String;Ljava/lang/String;[Ljava/lang/String;Ljava/lang/String;)Landroid/database/Cursor;",
    "query(Landroid/net/Uri;[Ljava/lang/String;Ljava/lang/String;[Ljava/lang/String;Ljava/lang/String;Landroid/os/CancellationSignal;)Landroid/database/Cursor;":
        f"query({CR}Landroid/net/Uri;[Ljava/lang/String;Ljava/lang/String;[Ljava/lang/String;Ljava/lang/String;Landroid/os/CancellationSignal;)Landroid/database/Cursor;",
    "query(Landroid/net/Uri;[Ljava/lang/String;Landroid/os/Bundle;Landroid/os/CancellationSignal;)Landroid/database/Cursor;":
        f"query({CR}Landroid/net/Uri;[Ljava/lang/String;Landroid/os/Bundle;Landroid/os/CancellationSignal;)Landroid/database/Cursor;",
}
CALLS = {f"{CR}->{k}": f"{H}->{v}" for k, v in _SIGS.items()}
CALL = re.compile(r"invoke-virtual(/range)? \{([^}]*)\}, (" + "|".join(re.escape(k) for k in CALLS) + r")")


def main(root):
    changed, files, dirs = 0, 0, set()
    for d, _, fs in os.walk(root):
        if os.sep + os.path.join("oneos", "camera") in d:
            continue
        for f in fs:
            if not f.endswith(".smali"):
                continue
            p = os.path.join(d, f)
            s = open(p).read()
            if "ContentResolver;->insert(" not in s and "ContentResolver;->query(" not in s:
                continue
            n = 0

            def sub(m):
                nonlocal n
                n += 1
                return f"invoke-static{m.group(1) or ''} {{{m.group(2)}}}, {CALLS[m.group(3)]}"
            s2 = CALL.sub(sub, s)
            if n:
                open(p, "w").write(s2)
                changed += n
                files += 1
                dirs.add(os.path.relpath(p, root).split(os.sep)[0])
    smali = [x for x in os.listdir(root) if re.fullmatch(r"smali(_classes\d+)?", x)]
    have = [x for x in smali if os.path.exists(os.path.join(root, x, "oneos", "camera", "OneOSMedia.smali"))]
    if not changed and not have:
        sys.exit("no ContentResolver.insert or query call found")
    if have:
        own = have[0]
    else:
        own = "smali_classes%d" % (max(int(x[len("smali_classes"):]) if x != "smali" else 1 for x in smali) + 1)
        os.makedirs(os.path.join(root, own, "oneos", "camera"))
    shutil.copyfile(os.path.join(HERE, "helpers", "smali", "OneOSMedia.smali"), os.path.join(root, own, "oneos", "camera", "OneOSMedia.smali"))
    for x in sorted(dirs | {own}):
        print(x)
    print(f"secmedia: {changed} ContentResolver insert/query call(s) in {files} file(s) to OneOSMedia ({own})", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
