"""The guest's own screen lock: a PIN, password or pattern kept in the guest's data.

The guest shares the phone's gatekeeper, weaver, keystore daemon and fingerprint HAL, so its
framework never sets a real screen lock (guest_no_gatekeeper.py: setLockCredentialInternal
returns false at its entry) and a guest could not be locked at all. This patch gives the guest's
LockSettingsService a lock of its own that touches none of those: one small record in the
guest's /data/system, kept and checked by OneOSGuestLock (OneOSGuestLock.java beside this file;
the checked-in smali is generated from it by scripts/build-guest-lock-smali.sh). The idea is
public pull request 152's; the code is new.

What it is: a lock for the guest's lock screen while the guest runs. What it is not: device
encryption, or a credential the keystore knows. A restart of the phone goes back to One UI,
which has no lock, and root there reaches the guest's data and can remove the record (that is
also the way out of a forgotten lock: delete oneos_guest_lock* in the guest's data/system).

Six changes, all or none:

1. LockSettingsService.setLockCredentialInternal: in front of the gatekeeper guard, the added
   method oneosGuestLockSet asks OneOSGuestLock.change() for user 0. Done -> true (the public
   setLockCredential then runs its usual steps), refused (wrong old credential, a wait is
   running) -> false, nothing to do -> the guard answers as before.
2. LockSettingsService.doVerifyCredential: at the entry, the added method oneosGuestLockVerify
   asks OneOSGuestLock.verify() for user 0. No guest lock -> the method goes its own way. A
   match -> the progress callback (AOSP's lock screen opens on it, not on the result), strong
   auth reported, listeners told, VerifyCredentialResponse.OK: never a gatekeeper handle or
   token, whatever the flags, and nothing of the framework's own unlock (keystore, CE storage,
   recoverable keystore). A wrong guess -> credIncorrect(wait), a guess during a wait ->
   fromTimeout(left), as the framework's own software rate limiter answers; with a wait, strong
   auth "after lockout" is required as there.
3. LockSettingsService.getCredentialType (the public binder method only): the guest lock's type
   when one is set. The lock screen, Settings, WindowManager and TrustManager read it through
   LockPatternUtils; getCredentialTypeInternal and with it the service's own state (synthetic
   password, CE storage, isUserSecure) stay "none", as in every guest so far.
4. LockSettingsService.enforceFrpNotActive returns at its entry. Its only caller is
   setLockCredential. "FRP active" in the guest only says that the guest could not read One
   UI's FRP secret (guest_pdb_readonly.py, guest_pdb_init_survives.py: A36, A54, A56), and the
   only lock that can be set behind the check is the guest's own record; with the check, those
   phones would get a SecurityException in Settings.
5. TrustManagerService.notifyKeystoreOfDeviceLockState: a "locked" report is dropped. With a
   guest lock the guest's device becomes "locked" for the first time, and that report would
   make the phone's keystore daemon drop user 0's unlocked-device-required keys, which only a
   real unlock of the phone gives back. The "unlocked" report is what a guest sends today.
6. biometrics/PreAuthInfo: "a device credential is available" is false. A credential prompt of
   an app (BiometricPrompt with DEVICE_CREDENTIAL) ends in SystemUI asking the gatekeeper for a
   token, which the guest lock cannot give (ColorOS SystemUI throws on the missing token). So
   such prompts answer what they answer today, without a lock: no credential enrolled. A
   constant on the register, because classes.dex has no room for a new method reference.

Apps therefore see a secure, lockable device (KeyguardManager), but nothing that needs the
keystore's idea of the user's credential: keys bound to user authentication cannot be made, as
in every guest so far.

The patch needs the framework shape it was written for (ColorOS 17 on Android 17: the method
names above, Duration-based VerifyCredentialResponse, the gatekeeper guard in place). Any other
shape is left alone: a note on stderr, nothing on stdout, exit 0, so make-overlays.sh (set -e)
still builds that image without the lock. A tree that already has the lock is left alone the
same way; one that has parts of it is an error. Calls into OneOSGuestLock sit in try/catch
Throwable: a helper class that cannot be loaded must not take system_server down.

Usage: guest_local_lock.py <smali root dir> [helper smali]
Prints the smali_* directories (dex files) it changed, one per line.
"""
import os
import re
import shutil
import sys

PKG = os.path.join("com", "android", "server", "locksettings")
LSS_REL = os.path.join(PKG, "LockSettingsService.smali")
AUTH_REL = os.path.join(PKG, "LockSettingsStrongAuth.smali")
TMS_REL = os.path.join("com", "android", "server", "trust", "TrustManagerService.smali")
PRE_REL = os.path.join("com", "android", "server", "biometrics", "PreAuthInfo.smali")
HELPER_NAME = "OneOSGuestLock.smali"

LSS = "Lcom/android/server/locksettings/LockSettingsService;"
AUTH = "Lcom/android/server/locksettings/LockSettingsStrongAuth;"
HELPER = "Lcom/android/server/locksettings/OneOSGuestLock;"
CRED = "Lcom/android/internal/widget/LockscreenCredential;"
VCR = "Lcom/android/internal/widget/VerifyCredentialResponse;"
CALLBACK = "Lcom/android/internal/widget/ICheckCredentialProgressCallback;"
DURATION = "Ljava/time/Duration;"
SLOG = "Landroid/util/Slog;"

# What a patched tree still shows after the jar was built and decoded again.
MARK = "oneosGuestLockVerify"
KEYSTORE_TEXT = "OneOS: the guest lock state is not sent to the keystore of the phone"
GUARD_TEXT = '"OneOS: the screen lock is the phone'

# Framework members the added code calls: this image's lock service uses them itself.
FRAMEWORK_REFS = [
    CRED + "->isNone()Z",
    CRED + "->getType()I",
    CRED + "->getCredential()[B",
    CALLBACK + "->onCredentialVerified()V",
    VCR + "->OK:" + VCR,
    VCR + "->credIncorrect(" + DURATION + ")" + VCR,
    VCR + "->fromTimeout(" + DURATION + ")" + VCR,
]


class Skip(Exception):
    """An anchor is not there: this framework is left alone."""


def fail(msg):
    sys.exit("guest_local_lock: " + msg)


def one_dir(root, rel):
    """The smali_* directory that holds the class, or Skip."""
    hits = [d for d in sorted(os.listdir(root))
            if d.startswith("smali") and os.path.isfile(os.path.join(root, d, rel))]
    if len(hits) != 1:
        raise Skip(f"{len(hits)} files {rel}")
    return hits[0]


def method(lines, name, desc, rel):
    """(first, last) line index of the one instance method name+desc, and its .locals count."""
    head = re.compile(r"^\.method (?:[a-z-]+ )*" + re.escape(name + desc) + r"$")
    starts = [i for i, l in enumerate(lines) if head.match(l)]
    if len(starts) != 1:
        raise Skip(f"{rel}: {name}{desc} found {len(starts)} times")
    i = starts[0]
    if " static " in lines[i]:
        raise Skip(f"{rel}: {name} is static")
    end = next(k for k in range(i, len(lines)) if lines[k] == ".end method")
    m = re.fullmatch(r"\s*\.locals (\d+)", lines[i + 1])
    if not m:
        raise Skip(f"{rel}: {name} has no .locals line")
    return i, end, int(m.group(1))


def entry(lines, i):
    """First index inside the method body (after .locals, .param, .annotation blocks, blanks)."""
    j = i + 2
    while True:
        s = lines[j].strip()
        if s.startswith(".param"):
            j += 1
        elif s.startswith(".annotation"):
            while lines[j].strip() != ".end annotation":
                j += 1
            j += 1
        elif s in ("", ".end param"):
            j += 1
        else:
            return j


def code(lines, first, last):
    """(index, text) of the instructions of a method: no directives, labels, comments, blanks."""
    return [(k, lines[k].strip()) for k in range(first + 1, last)
            if lines[k].strip() and lines[k].strip()[0] not in ".:#"]


def invoke_kind(lines, i):
    return "invoke-direct" if " private " in lines[i] else "invoke-virtual"


def set_hook():
    return f"""\
    # OneOS: the guest's own screen lock is asked first (patches/guest_local_lock.py). Below
    # zero it has nothing to do here, and the guard that follows answers as before.
    invoke-direct/range {{p0 .. p3}}, {LSS}->oneosGuestLockSet({CRED}{CRED}I)I

    move-result v0

    if-ltz v0, :oneos_gl_guard

    if-eqz v0, :oneos_gl_refused

    const/4 v0, 0x1

    return v0

    :oneos_gl_refused
    const/4 v0, 0x0

    return v0

    :oneos_gl_guard""".split("\n")


def verify_hook():
    return f"""\
    # OneOS: with a guest screen lock set, the guest's own record answers
    # (patches/guest_local_lock.py); null means there is none.
    invoke-direct/range {{p0 .. p3}}, {LSS}->oneosGuestLockVerify({CRED}I{CALLBACK}){VCR}

    move-result-object v0

    if-eqz v0, :oneos_gl_native

    return-object v0

    :oneos_gl_native""".split("\n")


def type_hook(result, spare):
    """Lines for after the move-result, and lines for after the return."""
    front = f"""\

    # OneOS: with a guest screen lock set (patches/guest_local_lock.py), its type is the
    # answer for the lock screen and Settings; the service's own state stays as it is. A
    # helper class that cannot be loaded leaves the answer above.
    :oneos_gl_type_start
    invoke-static {{p1, {result}}}, {HELPER}->credentialType(II)I

    move-result {result}
    :oneos_gl_type_end
    .catch Ljava/lang/Throwable; {{:oneos_gl_type_start .. :oneos_gl_type_end}} :oneos_gl_type_catch

    :oneos_gl_type_done""".split("\n")
    back = f"""\

    :oneos_gl_type_catch
    move-exception {spare}

    goto :oneos_gl_type_done""".split("\n")
    return front, back


FRP_HOOK = """\
    # OneOS: "FRP active" in the guest only says that the guest could not read One UI's FRP
    # secret; the only lock set behind this check is the guest's own record
    # (patches/guest_local_lock.py).
    return-void
""".split("\n")

KEYSTORE_HOOK = f"""\
    # OneOS: the guest's lock state is the guest's (patches/guest_local_lock.py). A "locked"
    # report would make the phone's keystore daemon drop user 0's unlocked-device-required
    # keys; only a real unlock of the phone gives them back.
    if-eqz p2, :oneos_gl_unlocked

    const-string v0, "TrustManagerService"

    const-string v1, "{KEYSTORE_TEXT}"

    invoke-static {{v0, v1}}, {SLOG}->i(Ljava/lang/String;Ljava/lang/String;)I

    return-void

    :oneos_gl_unlocked""".split("\n")


def added_methods(invalidate, listeners, strong):
    """oneosGuestLockSet and oneosGuestLockVerify, with this image's kinds of invoke."""
    return f"""\

# OneOS: sets, changes or removes the guest's own screen lock (OneOSGuestLock) for user 0.
# 1: done. 0: refused (wrong saved credential, a wait is running, unusable new credential).
# Below zero: nothing to do here (another user, no guest lock and none to set, or the helper
# cannot be used); setLockCredentialInternal then answers with its guard, as before.
.method private oneosGuestLockSet({CRED}{CRED}I)I
    .locals 8

    const/4 v7, -0x1

    if-nez p3, :oneos_gl_done

    if-eqz p1, :oneos_gl_done

    :oneos_gl_try_start
    const/4 v1, 0x0

    const/4 v2, 0x0

    invoke-virtual {{p1}}, {CRED}->isNone()Z

    move-result v0

    if-eqz v0, :oneos_gl_new

    const/4 v0, -0x1

    goto :oneos_gl_saved

    :oneos_gl_new
    invoke-virtual {{p1}}, {CRED}->getCredential()[B

    move-result-object v1

    invoke-virtual {{p1}}, {CRED}->getType()I

    move-result v0

    :oneos_gl_saved
    if-eqz p2, :oneos_gl_call

    invoke-virtual {{p2}}, {CRED}->isNone()Z

    move-result v3

    if-nez v3, :oneos_gl_call

    invoke-virtual {{p2}}, {CRED}->getCredential()[B

    move-result-object v2

    :oneos_gl_call
    invoke-static {{}}, Landroid/os/SystemClock;->elapsedRealtime()J

    move-result-wide v3

    invoke-static {{}}, Ljava/lang/System;->currentTimeMillis()J

    move-result-wide v5

    invoke-static/range {{v0 .. v6}}, {HELPER}->change(I[B[BJJ)I

    move-result v7
    :oneos_gl_try_end
    .catch Ljava/lang/Throwable; {{:oneos_gl_try_start .. :oneos_gl_try_end}} :oneos_gl_catch

    const/4 v0, 0x1

    if-ne v7, v0, :oneos_gl_done

    {invalidate} {{p0, p3}}, {LSS}->invalidateCredentialTypeCaches(I)V

    const-string v0, "LockSettingsService"

    const-string v1, "OneOS: guest screen lock set, changed or removed"

    invoke-static {{v0, v1}}, {SLOG}->i(Ljava/lang/String;Ljava/lang/String;)I

    :oneos_gl_done
    return v7

    :oneos_gl_catch
    move-exception v0

    const-string v1, "LockSettingsService"

    const-string v2, "OneOS: the guest screen lock cannot be used"

    invoke-static {{v1, v2, v0}}, {SLOG}->w(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    const/4 v7, -0x1

    goto :oneos_gl_done
.end method

# OneOS: one guess at the guest's own screen lock (OneOSGuestLock) for user 0. Null: there is
# none (or another user, no credential, or the helper cannot be used) and doVerifyCredential
# goes its own way. Else the answer: OK without a gatekeeper handle, or the two answers of the
# framework's software rate limiter (see OneOSGuestLock.verify for the numbers).
.method private oneosGuestLockVerify({CRED}I{CALLBACK}){VCR}
    .locals 8

    const/4 v7, 0x0

    if-nez p2, :oneos_gl_native

    if-eqz p1, :oneos_gl_native

    :oneos_gl_try_start
    invoke-virtual {{p1}}, {CRED}->isNone()Z

    move-result v0

    if-nez v0, :oneos_gl_native

    invoke-virtual {{p1}}, {CRED}->getCredential()[B

    move-result-object v0

    invoke-static {{}}, Landroid/os/SystemClock;->elapsedRealtime()J

    move-result-wide v1

    invoke-static {{}}, Ljava/lang/System;->currentTimeMillis()J

    move-result-wide v3

    invoke-static/range {{v0 .. v4}}, {HELPER}->verify([BJJ)J

    move-result-wide v0
    :oneos_gl_try_end
    .catch Ljava/lang/Throwable; {{:oneos_gl_try_start .. :oneos_gl_try_end}} :oneos_gl_catch

    const-wide/16 v2, -0x1

    cmp-long v4, v0, v2

    if-eqz v4, :oneos_gl_native

    const-wide/16 v2, 0x0

    cmp-long v4, v0, v2

    if-nez v4, :oneos_gl_failed

    # A match. AOSP's lock screen opens on this callback, not on the result.
    if-eqz p3, :oneos_gl_matched

    :oneos_gl_cb_start
    invoke-interface {{p3}}, {CALLBACK}->onCredentialVerified()V
    :oneos_gl_cb_end
    .catch Ljava/lang/Throwable; {{:oneos_gl_cb_start .. :oneos_gl_cb_end}} :oneos_gl_cb_catch

    :oneos_gl_matched
    iget-object v0, p0, {LSS}->mStrongAuth:{AUTH}

    {strong} {{v0, p2}}, {AUTH}->reportSuccessfulStrongAuthUnlock(I)V

    const/4 v0, 0x1

    {listeners} {{p0, v0, p2}}, {LSS}->notifyLockSettingsStateListeners(ZI)V

    sget-object v7, {VCR}->OK:{VCR}

    return-object v7

    :oneos_gl_failed
    if-lez v4, :oneos_gl_waiting

    # A wrong guess: result - 1 ms to wait before the next one (may be none).
    const-wide/16 v2, 0x1

    sub-long/2addr v0, v2

    invoke-static {{v0, v1}}, {DURATION}->ofMillis(J){DURATION}

    move-result-object v5

    invoke-static {{v5}}, {VCR}->credIncorrect({DURATION}){VCR}

    move-result-object v7

    goto :oneos_gl_reported

    :oneos_gl_waiting
    # Not looked at, a wait is running: -result - 2 ms are left.
    neg-long v0, v0

    const-wide/16 v2, 0x2

    sub-long/2addr v0, v2

    invoke-static {{v0, v1}}, {DURATION}->ofMillis(J){DURATION}

    move-result-object v5

    invoke-static {{v5}}, {VCR}->fromTimeout({DURATION}){VCR}

    move-result-object v7

    :oneos_gl_reported
    const-wide/16 v2, 0x0

    cmp-long v4, v0, v2

    if-lez v4, :oneos_gl_listeners

    # STRONG_AUTH_REQUIRED_AFTER_LOCKOUT, as doVerifyCredential does on a timeout.
    const/16 v4, 0x8

    invoke-virtual {{p0, v4, p2}}, {LSS}->requireStrongAuth(II)V

    :oneos_gl_listeners
    const/4 v4, 0x0

    {listeners} {{p0, v4, p2}}, {LSS}->notifyLockSettingsStateListeners(ZI)V

    return-object v7

    :oneos_gl_native
    return-object v7

    :oneos_gl_catch
    move-exception v0

    const-string v1, "LockSettingsService"

    const-string v2, "OneOS: the guest screen lock cannot be used"

    invoke-static {{v1, v2, v0}}, {SLOG}->w(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    goto :oneos_gl_native

    :oneos_gl_cb_catch
    move-exception v0

    goto :oneos_gl_matched
.end method""".split("\n")


def patch_lss(lines, rel, pkg_text):
    """All edits of LockSettingsService, or Skip; returns the new lines."""
    for ref in FRAMEWORK_REFS:
        if ref not in pkg_text:
            raise Skip(f"the lock service does not use {ref}")
    if not any(re.fullmatch(r"\.field (?:[a-z]+ )*mStrongAuth:" + re.escape(AUTH), l) for l in lines):
        raise Skip(f"{rel}: no field mStrongAuth")

    s_i, s_end, s_locals = method(lines, "setLockCredentialInternal", f"({CRED}{CRED}IZ)Z", rel)
    v_i, v_end, v_locals = method(lines, "doVerifyCredential", f"({CRED}I{CALLBACK}I){VCR}", rel)
    t_i, t_end, t_locals = method(lines, "getCredentialType", "(I)I", rel)
    f_i, f_end, _ = method(lines, "enforceFrpNotActive", "()V", rel)
    inv_i, _, _ = method(lines, "invalidateCredentialTypeCaches", "(I)V", rel)
    lis_i, _, _ = method(lines, "notifyLockSettingsStateListeners", "(ZI)V", rel)
    req_i, _, _ = method(lines, "requireStrongAuth", "(II)V", rel)
    if " private " in lines[req_i]:
        raise Skip(f"{rel}: requireStrongAuth is private")
    if s_locals < 1 or v_locals < 1:
        raise Skip(f"{rel}: no free register at the entry of the set or verify method")
    tail = added_methods(invoke_kind(lines, inv_i), invoke_kind(lines, lis_i), "invoke-virtual")

    # 1. The set hook goes in front of the gatekeeper guard (v0 is free at the entry).
    s_at = entry(lines, s_i)
    guard = [t for _, t in code(lines, s_i, s_end)[:2]]
    if (len(guard) < 2 or guard[0] != 'const-string v0, "LockSettingsService"'
            or not guard[1].startswith("const-string v1, " + GUARD_TEXT)):
        raise Skip(f"{rel}: setLockCredentialInternal does not start with the gatekeeper guard")

    # 2. The verify hook, at the entry.
    v_at = entry(lines, v_i)

    # 3. getCredentialType: [permission check,] p0.getCredentialTypeInternal(p1), return it.
    t_code = code(lines, t_i, t_end)
    call = re.compile(r"invoke-(?:direct|virtual) \{p0, p1\}, " + re.escape(LSS)
                      + r"->getCredentialTypeInternal\(I\)I")
    if len(t_code) not in (3, 4) or not call.fullmatch(t_code[-3][1]):
        raise Skip(f"{rel}: getCredentialType has another shape")
    m = re.fullmatch(r"move-result (v\d+)", t_code[-2][1])
    if not m or t_code[-1][1] != "return " + m.group(1) or t_locals > 8:
        raise Skip(f"{rel}: getCredentialType has another shape")
    if any(".catch" in l or l.strip().startswith(":") for l in lines[t_i:t_end]):
        raise Skip(f"{rel}: getCredentialType has labels of its own")
    front, back = type_hook(m.group(1), f"v{t_locals}")

    # 4. The FRP check.
    f_at = entry(lines, f_i)

    edits = [
        (s_at, s_at, set_hook()),
        (v_at, v_at, verify_hook()),
        (t_i + 1, t_i + 2, [f"    .locals {t_locals + 1}"]),
        (t_code[-2][0] + 1, t_code[-2][0] + 1, front),
        (t_code[-1][0] + 1, t_code[-1][0] + 1, back),
        (f_at, f_at, FRP_HOOK),
    ]
    for first, last, new in sorted(edits, reverse=True):
        lines[first:last] = new
    while lines and lines[-1] == "":
        lines.pop()
    lines += tail + [""]
    return lines


def patch_tms(lines, rel):
    i, end, n_locals = method(lines, "notifyKeystoreOfDeviceLockState", "(IZ)V", rel)
    if n_locals < 2:
        raise Skip(f"{rel}: notifyKeystoreOfDeviceLockState has fewer than two registers")
    if not any("Landroid/security/KeyStoreAuthorization;->onDeviceLocked(" in l for l in lines[i:end]):
        raise Skip(f"{rel}: notifyKeystoreOfDeviceLockState does not report to the keystore")
    at = entry(lines, i)
    lines[at:at] = KEYSTORE_HOOK
    return lines


def patch_pre(lines, rel):
    call = re.compile(r"\s*invoke-interface(?:/range)? \{[^}]*\}, "
                      r"Landroid/app/trust/ITrustManager;->isDeviceSecure\(II\)Z")
    sites = [i for i, l in enumerate(lines) if call.fullmatch(l)]
    if len(sites) != 1:
        raise Skip(f"{rel}: {len(sites)} calls of ITrustManager.isDeviceSecure")
    j = sites[0] + 1
    while lines[j].strip() == "" or lines[j].strip().startswith(".line"):
        j += 1
    m = re.fullmatch(r"\s*move-result (v\d+)", lines[j])
    if not m:
        raise Skip(f"{rel}: the result of isDeviceSecure is not kept in a register")
    lines[j + 1:j + 1] = [
        "",
        "    # OneOS: a credential prompt of an app would ask the gatekeeper for a token, which the",
        "    # guest's own screen lock cannot give (patches/guest_local_lock.py): no device",
        "    # credential is available, as in a guest without a lock. A constant: no new reference.",
        f"    const/16 {m.group(1)}, 0x0",
    ]
    return lines


def read(path):
    with open(path) as f:
        return f.read()


def main(root, helper):
    if not os.path.isfile(helper):
        fail(f"no helper smali at {helper}")
    try:
        dirs = {rel: one_dir(root, rel) for rel in (LSS_REL, AUTH_REL, TMS_REL, PRE_REL)}
        if dirs[AUTH_REL] != dirs[LSS_REL]:
            raise Skip("LockSettingsStrongAuth is in another dex than LockSettingsService")
        paths = {rel: os.path.join(root, dirs[rel], rel) for rel in dirs}
        text = {rel: read(paths[rel]) for rel in dirs}
        helper_out = os.path.join(root, dirs[LSS_REL], PKG, HELPER_NAME)

        have = [MARK in text[LSS_REL], KEYSTORE_TEXT in text[TMS_REL],
                any(os.path.isfile(os.path.join(root, d, PKG, HELPER_NAME))
                    for d in os.listdir(root) if d.startswith("smali"))]
        if all(have):
            print("guest_local_lock: this services.jar already has the guest screen lock",
                  file=sys.stderr)
            return
        if any(have):
            fail("parts of the guest screen lock are already in this tree")

        auth_head = re.search(r"^\.method (?:[a-z-]+ )*reportSuccessfulStrongAuthUnlock\(I\)V$",
                              text[AUTH_REL], re.M)
        if not auth_head or " private " in auth_head.group(0) or " static " in auth_head.group(0):
            raise Skip("LockSettingsStrongAuth.reportSuccessfulStrongAuthUnlock(I)V is not callable")
        pkg_dir = os.path.dirname(paths[LSS_REL])
        pkg_text = "".join(read(os.path.join(pkg_dir, f)) for f in sorted(os.listdir(pkg_dir))
                           if f.endswith(".smali"))

        new = {
            LSS_REL: patch_lss(text[LSS_REL].split("\n"), LSS_REL, pkg_text),
            TMS_REL: patch_tms(text[TMS_REL].split("\n"), TMS_REL),
            PRE_REL: patch_pre(text[PRE_REL].split("\n"), PRE_REL),
        }
    except Skip as why:
        print(f"guest_local_lock: {why}; this framework gets no guest screen lock",
              file=sys.stderr)
        return

    for rel, lines in new.items():
        with open(paths[rel], "w") as f:
            f.write("\n".join(lines))
    shutil.copy(helper, helper_out)
    print("guest_local_lock: LockSettingsService set, verify, credential type and FRP check; "
          "TrustManagerService keystore report; PreAuthInfo device credential; OneOSGuestLock",
          file=sys.stderr)
    for d in sorted({dirs[LSS_REL], dirs[TMS_REL], dirs[PRE_REL]}):
        print(d)


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__.strip().split("\n")[-2])
    main(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else
         os.path.join(os.path.dirname(os.path.abspath(__file__)), HELPER_NAME))
