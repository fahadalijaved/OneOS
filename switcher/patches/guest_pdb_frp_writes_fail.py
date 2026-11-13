"""A guest PDB write while FRP looks active fails as an I/O error, not a SecurityException.

guest_pdb_readonly.py points every write of the guest's PersistentDataBlockService at
/dev/null, so the phone's real FRP partition stays One UI's. Reads still come from that
partition, so when One UI's FRP state reads as active, the guest's service is FRP-active
too, and getBlockOutputChannel() throws SecurityException "FRP is active" before it opens
the (/dev/null) channel. Its callers catch IOException only. On the first boot of a
fresh guest, LockSettingsService.onThirdPartyAppsStarted -> migrateUserToSpWithBoundKeys
-> SyntheticPasswordManager.synchronizeGatekeeperFrpPassword -> setFrpCredentialHandle
-> writeDataBuffer reached it on system_server's main thread, which died; the screen
stayed black until the user held Volume Up+Down (A34 ColorOS 17 Find X9 Ultra IN, app
0.4.99, report 0514e9ea).

getBlockOutputChannel() now goes straight to getBlockOutputChannelIgnoringFrp(): the
write lands on /dev/null, force() throws IOException, and every caller already handles
that as a failed write (writeDataBuffer returns false, computeAndWriteDigestLocked logs).
Nothing more reaches the real partition than before: fail closed unless
getBlockOutputChannelIgnoringFrp() already opens "/dev/null" (guest_pdb_readonly.py ran)
and only an enforce call directly followed by that delegation is dropped (in
getBlockOutputChannel(), or where R8 inlined it). No such pair: nothing is changed.

Usage: guest_pdb_frp_writes_fail.py <apktool decoded services.jar dir>
Prints the smali_* directory it changed.
"""
import os
import re
import sys

REL = os.path.join("com", "android", "server", "pdb", "PersistentDataBlockService.smali")
CLS = "Lcom/android/server/pdb/PersistentDataBlockService;"
MARK = "guest_pdb_frp_writes_fail"


def fail(msg):
    sys.exit("guest_pdb_frp_writes_fail: " + msg)


def method(t, sig):
    found = [m for m in re.finditer(r"^\.method ([^\n]*)\n(.*?)^\.end method\n", t, re.M | re.S)
             if m.group(1).endswith(" " + sig)]
    if len(found) != 1:
        fail("%s found %d times" % (sig, len(found)))
    return found[0]


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
    ign = method(t, "getBlockOutputChannelIgnoringFrp()Ljava/nio/channels/FileChannel;")
    if '"/dev/null"' not in ign.group(2):
        fail("getBlockOutputChannelIgnoringFrp() does not open /dev/null (run guest_pdb_readonly.py first)")
    # The enforce call directly followed by the delegation: getBlockOutputChannel() itself,
    # or wherever R8 inlined it. Any other enforce call (the Stub's own checks) stays.
    pair = re.compile(r"^(\s*)invoke-(?:direct|virtual) \{(p0|v\d+)\}, " + re.escape(CLS)
                      + r"->enforceFactoryResetProtectionInactive\(\)V\n((?:\s*\.line \d+\n|\s*\n)*"
                      r"\s*invoke-(?:direct|virtual) \{\2\}, " + re.escape(CLS)
                      + r"->getBlockOutputChannelIgnoringFrp\(\)Ljava/nio/channels/FileChannel;\n)", re.M)
    hits = list(pair.finditer(t))
    if not hits:
        # Nothing to relax (an image without this check): leave the class as it is.
        print("%s: no FRP check before a PDB write-open in %s; unchanged" % (MARK, REL), file=sys.stderr)
        return
    note = ("# OneOS (patches/%s.py): writes go to /dev/null (guest_pdb_readonly);\n"
            "%s# with One UI's FRP active they fail as IOException, which every caller handles.\n")
    for h in reversed(hits):
        ind = h.group(1)
        t = t[:h.start()] + ind + note % (MARK, ind) + h.group(3) + t[h.end():]
    open(p, "w", encoding="utf-8").write(t)
    print("%s: %s/%s: %d PDB write-open(s) with FRP active fail as an I/O error" % (MARK, d, REL, len(hits)), file=sys.stderr)
    print(d)


if __name__ == "__main__":
    main()
