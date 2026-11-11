"""Skip ColorOS's 3 s keystore-negotiation wait in the container.

SyntheticPasswordManagerExtImpl.checkNegotiationCompleted polls
keystore.shared_secret_negotiated and sleeps 100 ms up to 30 times while
LockSettingsService.doVerifyCredential holds the SyntheticPasswordManager
monitor. The container's keystore is the host's keystore2; the guest's
framework never sets the property, so every correct PIN paid the full 3 s
before gatekeeperd saw the verify (measured ~3.03 s, three samples). Wrong
PINs fail at the weaver read first, so only the correct-PIN path waited.

The loop only logs (OMA statistics) and does not gate the unlock; make the
method return at entry.

Usage: guest_skip_negotiation.py <smali root dir>
Prints the smali_* directories (dex files) it changed, one per line.
"""
import os
import re
import sys

HEADER = ".method public checkNegotiationCompleted(Landroid/content/Context;)V"
BODY = """    .locals 0
    .param p1, "context"    # Landroid/content/Context;

    # OneOS: the guest never sets keystore.shared_secret_negotiated (its
    # keystore is the host's), so the 30 x 100 ms wait cost every correct PIN
    # 3 s while holding the SyntheticPasswordManager monitor. It only logs.
    return-void
.end method"""


def find(root, rel_suffix):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
            if os.path.join(d, f).endswith(rel_suffix)]
    if len(hits) != 1:
        sys.exit(f"expected exactly one {rel_suffix}, found {len(hits)}")
    return hits[0]


def main(root):
    rel = os.path.join("com", "android", "server", "locksettings",
                       "SyntheticPasswordManagerExtImpl.smali")
    path = find(root, rel)
    src = open(path).read()
    out, n = re.subn(re.escape(HEADER) + r".*?\.end method",
                     HEADER + "\n" + BODY, src,
                     count=1, flags=re.S)
    if n != 1:
        sys.exit(f"{rel}: checkNegotiationCompleted not found as expected")
    open(path, "w").write(out)
    print("SyntheticPasswordManagerExtImpl.checkNegotiationCompleted: skipped",
          file=sys.stderr)
    print(os.path.relpath(path, root).split(os.sep)[0])


if __name__ == "__main__":
    main(sys.argv[1])
