"""Let the guest's overlay manager use the guest's own idmap2d.

IdmapDaemon starts and stops the "idmap2d" init service through
SystemService.start/stop. In the container that is the HOST init, which
starts One UI's idmap2d in One UI's mount namespace: it cannot see the
guest's /my_product, /my_stock or /system/system_ext overlays, so no overlay
ever applied (9241 "failed to read IDMAP" in run 25), and it wrote into One
UI's /data/resource-cache. guest_start.sh now runs the guest's
/system/bin/idmap2d for the whole session; drop the start/stop calls so the
overlay manager just uses that one. (Pixel's IdmapDaemon passes the name in p0.)

One UI 9.5 (S948BXXU6ZZKN, Android 17): the stop moved out of IdmapDaemon into the delayed-close
runnable IdmapDaemon$Connection$$ExternalSyntheticLambda0, so IdmapDaemon.smali has one start call;
the patch then takes that one and the one stop of the IdmapDaemon* classes, and nothing else in them
may start or stop a service.

Usage: guest_own_idmap.py <smali root dir>
Prints the smali_* directory it changed.
"""
import os
import re
import sys

SUFFIX = os.path.join("com", "android", "server", "om", "IdmapDaemon.smali")
CALL = re.compile(r"^\s*invoke-static \{[vp]\d+\}, Landroid/os/SystemService;->(start|stop)\(Ljava/lang/String;\)V\s*$")


ANY_CALL = re.compile(r"SystemService;->(?:start|stop|restart)\(")


def main(root):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
            if os.path.join(d, f).endswith(os.sep + SUFFIX)]
    if len(hits) != 1:
        sys.exit(f"expected one IdmapDaemon.smali, found {len(hits)}")
    path = hits[0]
    lines = open(path).read().split("\n")
    n = 0
    for i, line in enumerate(lines):
        m = CALL.match(line)
        if m:
            lines[i] = f"    # OneOS: SystemService.{m.group(1)}(idmap2d) dropped (host init; the guest runs its own)"
            n += 1
    dirs = {os.path.relpath(path, root).split(os.sep)[0]}
    extra = None
    if n == 1:
        # One UI 9.5: the one start is here; the one stop is in an IdmapDaemon* class of its own.
        if any(ANY_CALL.search(l) for l in lines):
            sys.exit("IdmapDaemon: another SystemService start/stop/restart call is left")
        here = os.path.dirname(path)
        for f in sorted(os.listdir(here)):
            if not f.startswith("IdmapDaemon") or f == "IdmapDaemon.smali":
                continue
            fp = os.path.join(here, f)
            ls = open(fp).read().split("\n")
            calls = [k for k, l in enumerate(ls) if ANY_CALL.search(l)]
            if not calls:
                continue
            m = CALL.match(ls[calls[0]])
            if len(calls) != 1 or not m or m.group(1) != "stop" or extra is not None:
                sys.exit(f"{f}: unexpected SystemService call")
            ls[calls[0]] = "    # OneOS: SystemService.stop(idmap2d) dropped (host init; the guest runs its own)"
            extra = (fp, ls)
        if extra is None:
            sys.exit("IdmapDaemon: expected 2 SystemService start/stop calls, found 1")
        n = 2
    if n != 2:
        sys.exit(f"IdmapDaemon: expected 2 SystemService start/stop calls, found {n}")
    if extra:
        open(extra[0], "w").write("\n".join(extra[1]))
        dirs.add(os.path.relpath(extra[0], root).split(os.sep)[0])
    open(path, "w").write("\n".join(lines))
    print("IdmapDaemon: idmap2d start/stop dropped", file=sys.stderr)
    for d in sorted(dirs):
        print(d)


if __name__ == "__main__":
    main(sys.argv[1])
