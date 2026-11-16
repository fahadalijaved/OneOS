"""Bring an already built guest-lock services.jar up to the enrolment handle of guest_local_lock.py (0.5.17).

guest_local_lock.py (vdcoolok's pull request #152 version, commit 6dd81f2e) answers a matched guest credential
with its own gatekeeper-password handle and turns that handle into a placeholder token in
verifyGatekeeperPasswordHandle. Settings needs that token before any biometric page: without it, Fingerprint in
Nothing OS's Settings crashed with "Unable to request Gatekeeper HAT" (owner's A36). A set whose jar was built with
the earlier guest lock is left alone by guest_local_lock.py ("already has the guest screen lock"), and its image may
not be on the server any more; this adds the two missing pieces to such a jar, with the same code:

1. OneOSGuestLock (the helper class) replaced by the current one (OneOSGuestLock.smali: HANDLE, hat()).
2. In the verify hook, VerifyCredentialResponse.OK on a match becomes the response holding OneOSGuestLock.HANDLE.
3. guest_local_lock.GK_HOOK at the entry of LockSettingsService.verifyGatekeeperPasswordHandle.

Nothing of the phone's gatekeeper or keystore is reached: the handle is the guest lock's own, and the phone's
fingerprint HAL checks a token's MAC and refuses the placeholder. A jar that already has the handle is left as it is.

Usage: guest_local_lock_hat.py <smali root dir>
Prints the smali_* directories it changed, one per line.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import guest_local_lock as gl  # noqa: E402

LSS_REL = os.path.join("com", "android", "server", "locksettings", "LockSettingsService.smali")
HELPER_REL = os.path.join("com", "android", "server", "locksettings", "OneOSGuestLock.smali")
OLD_OK = f"    sget-object v7, {gl.VCR}->OK:{gl.VCR}"


def find(root, rel):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs if os.path.join(d, f).endswith(os.sep + rel)]
    if len(hits) != 1:
        sys.exit(f"expected one {rel}, found {len(hits)}")
    return hits[0]


def main(root):
    lss = find(root, LSS_REL)
    helper = find(root, HELPER_REL)
    lines = open(lss).read().split("\n")
    text = "\n".join(lines)
    if "0x4f4e454f53L" in text:
        print("guest_local_lock_hat: the jar already has the enrolment handle", file=sys.stderr)
        return
    # 2. The match answer: the one OK the guest lock's verify method returns (oneosGuestLockVerify; a decoded
    # jar has apktool's labels, not the patch's, so the method is found by name).
    heads = [i for i, l in enumerate(lines) if l.startswith(".method ") and " oneosGuestLockVerify(" in l]
    if len(heads) != 1:
        sys.exit("guest_local_lock_hat: no guest screen lock in this jar (build it with guest_local_lock.py)")
    start = heads[0]
    end = next(i for i in range(start, len(lines)) if lines[i] == ".end method")
    oks = [i for i in range(start, end) if lines[i] == OLD_OK]
    if len(oks) != 1 or lines[oks[0] + 2].strip() != "return-object v7":
        sys.exit(f"guest_local_lock_hat: {len(oks)} OK answers in the guest lock's match block, expected one")
    i = oks[0]
    lines[i:i + 1] = [
        "    # The guest lock's gatekeeper-password handle: Settings turns it into an enrollment token",
        "    # (guest_local_lock.py change 7). No handle or token of the phone's gatekeeper exists behind it.",
        f"    new-instance v7, {gl.BUILDER}",
        "",
        f"    invoke-direct {{v7}}, {gl.BUILDER}-><init>()V",
        "",
        "    const-wide v0, 0x4f4e454f53L",
        "",
        f"    invoke-virtual {{v7, v0, v1}}, {gl.BUILDER}->setGatekeeperPasswordHandle(J){gl.BUILDER}",
        "",
        "    move-result-object v7",
        "",
        f"    invoke-virtual {{v7}}, {gl.BUILDER}->build(){gl.VCR}",
        "",
        "    move-result-object v7",
    ]
    # 3. The token for that handle, at the entry of verifyGatekeeperPasswordHandle.
    try:
        g_i, _, g_locals = gl.method(lines, "verifyGatekeeperPasswordHandle", f"(JJI){gl.VCR}", LSS_REL)
    except gl.Skip as e:
        sys.exit(f"guest_local_lock_hat: {e}")
    g_at = gl.entry(lines, g_i)
    lines[g_at:g_at] = gl.GK_HOOK
    lines[g_i + 1] = f"    .locals {max(g_locals, 2)}"
    open(lss, "w").write("\n".join(lines))
    # 1. The helper with HANDLE and hat().
    new_helper = open(os.path.join(HERE, "OneOSGuestLock.smali")).read()
    if "hat(JI)[B" not in new_helper:
        sys.exit("guest_local_lock_hat: switcher/patches/OneOSGuestLock.smali has no hat(JI)[B")
    open(helper, "w").write(new_helper)
    print("guest_local_lock_hat: match answer with the guest handle, verifyGatekeeperPasswordHandle hook, helper with hat()",
          file=sys.stderr)
    for d in sorted({os.path.relpath(lss, root).split(os.sep)[0], os.path.relpath(helper, root).split(os.sep)[0]}):
        print(d)


if __name__ == "__main__":
    main(sys.argv[1])
