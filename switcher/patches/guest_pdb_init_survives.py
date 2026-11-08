"""The guest's PersistentDataBlockService finishes its start even when FRP cannot be cleared.

guest_pdb_readonly.py points every write of the guest's PDB service at /dev/null, so
the phone's real FRP partition stays One UI's. When the guest found FRP active or the
FRP magic missing on that partition, the service's start task (lambda$onStart$N:
enforceChecksumValidity, automaticallyDeactivateFrpIfPossible, publish, signalInitDone)
tried to write the FRP magic and default secret: the write failed (force() on /dev/null),
and computeAndWriteDigestLocked then threw SecurityException "FRP is active" out of
automaticallyDeactivateFrpIfPossible. The task died before signalInitDone, and at boot
phase 500 system_server threw "Service PersistentDataBlockService init timeout" and
died (0.4.59/0.4.60 A36 2bec9e85 "took a couple of tries", A54 cf0c2fdf, A56 3b80eb36:
sometimes, depending on the state One UI left in its partition).

The call to automaticallyDeactivateFrpIfPossible() in the start task now catches a
RuntimeException, logs it ("OneOS-PDB") and goes on, so the service is published and
init completes. Nothing is written to the real partition either way (guest_pdb_readonly).

Two registers are added to the method for the handler (no live value is touched); the
call is found by its exact method reference in the one start task that also signals
init done. Every pattern must match exactly once, or nothing is written.

Usage: guest_pdb_init_survives.py <apktool decoded services.jar dir>
Prints the smali_* directory it changed.
"""
import os
import re
import sys

REL = os.path.join("com", "android", "server", "pdb", "PersistentDataBlockService.smali")
CLS = "Lcom/android/server/pdb/PersistentDataBlockService;"
CALL = re.compile(r"^(\s*)invoke-(?:virtual|direct) \{(p\d+|v\d+)\}, " + re.escape(CLS)
                  + r"->automaticallyDeactivateFrpIfPossible\(\)Z\n(?:\s*\.line \d+\n|\s*\n)*(\s*move-result \w+\n)?", re.M)
MARK = "oneos_pdb_frp"


def fail(msg):
    sys.exit("guest_pdb_init_survives: " + msg)


def main():
    if len(sys.argv) != 2:
        fail(__doc__)
    root = sys.argv[1]
    hits = [d for d in sorted(os.listdir(root)) if d.startswith("smali") and os.path.isfile(os.path.join(root, d, REL))]
    if len(hits) != 1:
        fail("PersistentDataBlockService in %d dex dirs" % len(hits))
    d = hits[0]
    p = os.path.join(root, d, REL)
    t = open(p, encoding="utf-8").read()
    if MARK in t:
        fail("already patched")
    methods = [m for m in re.finditer(r"^\.method ([^\n]*)\n(.*?)^\.end method\n", t, re.M | re.S)
               if "->automaticallyDeactivateFrpIfPossible()Z" in m.group(2) and "->signalInitDone()V" in m.group(2)]
    if len(methods) != 1:
        fail("the start task (deactivate FRP, then signal init done) found %d times" % len(methods))
    m = methods[0]
    body = m.group(2)
    calls = list(CALL.finditer(body))
    if len(calls) != 1:
        fail("automaticallyDeactivateFrpIfPossible() called %d times in the start task" % len(calls))
    loc = re.search(r"^(\s*)\.locals (\d+)$", body, re.M)
    if not loc:
        fail("no .locals in the start task")
    n = int(loc.group(2))
    e, tag = "v%d" % n, "v%d" % (n + 1)
    c = calls[0]
    ind = c.group(1)
    call_text = body[c.start():c.end()]
    wrapped = (f"{ind}:{MARK}_try_start\n" + call_text.rstrip("\n") + "\n"
               f"{ind}:{MARK}_try_end\n"
               f"{ind}.catch Ljava/lang/RuntimeException; {{:{MARK}_try_start .. :{MARK}_try_end}} :{MARK}_catch\n\n"
               f"{ind}:{MARK}_after\n")
    body2 = body[:c.start()] + wrapped + body[c.end():]
    body2 = body2[:loc.start()] + f"{loc.group(1)}.locals {n + 2}" + body2[loc.end():]
    handler = (f"\n{ind}# OneOS (patches/guest_pdb_init_survives.py): FRP could not be cleared (the guest's PDB\n"
               f"{ind}# writes go to /dev/null); the service still publishes and signals init done.\n"
               f"{ind}:{MARK}_catch\n"
               f"{ind}move-exception {e}\n\n"
               f"{ind}const-string {tag}, \"OneOS-PDB\"\n\n"
               f"{ind}invoke-static/range {{{e} .. {tag}}}, Lcom/oneos/pdb/Dummy;->x()V\n")
    # Log.w(String tag, Throwable tr) takes the tag first: registers in that order.
    handler = handler.replace(f"move-exception {e}", f"move-exception {tag}").replace(
        f"const-string {tag}, \"OneOS-PDB\"", f"const-string {e}, \"OneOS-PDB\"").replace(
        "Lcom/oneos/pdb/Dummy;->x()V", "Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/Throwable;)I")
    handler += f"\n{ind}goto :{MARK}_after\n"
    body2 = body2.rstrip("\n") + "\n" + handler
    t = t[:m.start(2)] + body2 + t[m.end(2):]
    open(p, "w", encoding="utf-8").write(t)
    print("guest_pdb_init_survives: %s/%s: the start task survives a failed FRP deactivation" % (d, REL), file=sys.stderr)
    print(d)


if __name__ == "__main__":
    main()
