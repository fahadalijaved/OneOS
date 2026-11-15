#!/usr/bin/env python3
"""The guest's own screen lock: the services.jar patcher and the helper class.

The guest shares the phone's gatekeeper, weaver and keystore daemon, so its framework refuses to
set a screen lock (patches/guest_no_gatekeeper.py). patches/guest_local_lock.py puts a lock of the
guest's own in front of that guard: a PIN, pattern or password whose record lives in the guest's
/data/system and is checked by OneOSGuestLock, a class added to services.jar. Nothing of it reaches
the phone's gatekeeper, weaver or keystore.

Here:
- the patcher on a small smali tree with the shapes of the ColorOS 17 framework: the six changes,
  the guard in both of its forms (as guest_no_gatekeeper.py writes it and as a decoded built jar
  shows it), a framework of another shape left untouched, a second run, a half-patched tree;
- the helper class on the JVM through a small driver: set, check, change, remove, the waits after
  wrong tries and what survives a restart, damaged files, the record format;
- the checked-in smali belongs to the checked-in Java source, and make-overlays.sh runs the
  patcher after the gatekeeper loop.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCHES = ROOT / 'switcher/patches'
PATCHER = PATCHES / 'guest_local_lock.py'
JAVA = PATCHES / 'OneOSGuestLock.java'
SMALI = PATCHES / 'OneOSGuestLock.smali'

W = 'Lcom/android/internal/widget/'
CRED = W + 'LockscreenCredential;'
VCR = W + 'VerifyCredentialResponse;'
CB = W + 'ICheckCredentialProgressCallback;'
LSS = 'Lcom/android/server/locksettings/LockSettingsService;'
HELPER = 'Lcom/android/server/locksettings/OneOSGuestLock;'
PKG = 'com/android/server/locksettings'
LSS_FILE = 'smali_classes2/' + PKG + '/LockSettingsService.smali'
AUTH_FILE = 'smali_classes2/' + PKG + '/LockSettingsStrongAuth.smali'
HELPER_FILE = 'smali_classes2/' + PKG + '/OneOSGuestLock.smali'
TMS_FILE = 'smali_classes3/com/android/server/trust/TrustManagerService.smali'
PRE_FILE = 'smali/com/android/server/biometrics/PreAuthInfo.smali'

GUARD_STRING = "OneOS: the screen lock is the phone's gatekeeper; not set in the guest"
GUARD_TAIL = [
    '',
    '    invoke-static {v0, v1}, Landroid/util/Slog;->w(Ljava/lang/String;Ljava/lang/String;)I',
    '',
    '    const/4 v0, 0x0',
    '',
    '    return v0',
    '',
]
GUARDS = {
    # As guest_no_gatekeeper.py writes it into a freshly decoded framework.
    'fresh': ["    # OneOS: the guest never sets or resets the phone's shared screen lock.",
              '    const-string v0, "LockSettingsService"',
              '',
              f'    const-string v1, "{GUARD_STRING}"'] + GUARD_TAIL,
    # As a built jar shows it when decoded again: no comment, the apostrophe escaped.
    'decoded': ['    const-string v0, "LockSettingsService"',
                '',
                '    const-string v1, "' + GUARD_STRING.replace("'", "\\'") + '"'] + GUARD_TAIL,
    'none': [],
}

TYPE_BODIES = {
    'plain': f'''    .locals 1
    .param p1, "userId"    # I

    .line 1717
    invoke-direct {{p0}}, {LSS}->checkHavePermission()V

    .line 1718
    invoke-direct {{p0, p1}}, {LSS}->getCredentialTypeInternal(I)I

    move-result v0

    return v0''',
    # Another shape: the result is looked at before it is returned.
    'branch': f'''    .locals 1
    .param p1, "userId"    # I

    invoke-direct {{p0, p1}}, {LSS}->getCredentialTypeInternal(I)I

    move-result v0

    if-gez v0, :cond_0

    const/4 v0, -0x1

    :cond_0
    return v0''',
}


def lss_text(guard='decoded', type_body='plain', helpers='private'):
    return f'''.class public {LSS}
.super {W}ILockSettings$Stub;
.source "LockSettingsService.java"


# instance fields
.field private final mStrongAuth:Lcom/android/server/locksettings/LockSettingsStrongAuth;


# direct methods
.method private doVerifyCredential({CRED}I{CB}I){VCR}
    .locals 14
    .param p1, "credential"    # {CRED}
    .param p2, "userId"    # I
    .param p3, "progressCallback"    # {CB}
    .param p4, "flags"    # I

    .line 2100
    invoke-virtual {{p1}}, {CRED}->isNone()Z

    move-result v0

    if-eqz v0, :cond_0

    invoke-virtual {{p1}}, {CRED}->getType()I

    invoke-virtual {{p1}}, {CRED}->getCredential()[B

    invoke-interface {{p3}}, {CB}->onCredentialVerified()V

    const-wide/16 v1, 0x0

    invoke-static {{v1, v2}}, Ljava/time/Duration;->ofMillis(J)Ljava/time/Duration;

    move-result-object v1

    invoke-static {{v1}}, {VCR}->credIncorrect(Ljava/time/Duration;){VCR}

    invoke-static {{v1}}, {VCR}->fromTimeout(Ljava/time/Duration;){VCR}

    :cond_0
    sget-object v0, {VCR}->OK:{VCR}

    return-object v0
.end method

.method private enforceFrpNotActive()V
    .locals 3

    .line 1452
    new-instance v0, Ljava/lang/SecurityException;

    const-string v1, "Cannot change credential while factory reset protection is active"

    invoke-direct {{v0, v1}}, Ljava/lang/SecurityException;-><init>(Ljava/lang/String;)V

    throw v0
.end method

.method {helpers} invalidateCredentialTypeCaches(I)V
    .locals 0
    .param p1, "userId"    # I

    return-void
.end method

.method {helpers} notifyLockSettingsStateListeners(ZI)V
    .locals 0

    return-void
.end method

.method private setLockCredentialInternal({CRED}{CRED}IZ)Z
    .locals 10
    .param p1, "credential"    # {CRED}
    .param p2, "savedCredential"    # {CRED}
    .param p3, "userId"    # I
    .param p4, "isLockTiedToParent"    # Z

''' + '\n'.join(GUARDS[guard] + ['    .line 1900', '    const/4 v0, 0x1', '', '    return v0']) + f'''
.end method


# virtual methods
.method public getCredentialType(I)I
{TYPE_BODIES[type_body]}
.end method

.method public requireStrongAuth(II)V
    .locals 0

    return-void
.end method
'''


def auth_text(access='public'):
    return f'''.class public Lcom/android/server/locksettings/LockSettingsStrongAuth;
.super Ljava/lang/Object;


# virtual methods
.method {access} reportSuccessfulStrongAuthUnlock(I)V
    .locals 0

    return-void
.end method
'''


def tms_text(reports=True):
    locked = ('''    iget-object v0, p0, Lcom/android/server/trust/TrustManagerService;->mKeyStoreAuthorization:Landroid/security/KeyStoreAuthorization;

    const/4 v1, 0x0

    invoke-virtual {v0, p1, v1, v1}, Landroid/security/KeyStoreAuthorization;->onDeviceLocked(I[JZ)V
''' if reports else '    nop\n')
    return f'''.class public Lcom/android/server/trust/TrustManagerService;
.super Lcom/android/server/SystemService;


# direct methods
.method private notifyKeystoreOfDeviceLockState(IZ)V
    .locals 4
    .param p1, "userId"    # I
    .param p2, "isLocked"    # Z

    .line 1192
    if-eqz p2, :cond_0

{locked}
    :cond_0
    return-void
.end method
'''


def pre_text(calls=1):
    call = '''    invoke-interface {v0, v3, v4}, Landroid/app/trust/ITrustManager;->isDeviceSecure(II)Z

    move-result v21

'''
    return f'''.class Lcom/android/server/biometrics/PreAuthInfo;
.super Ljava/lang/Object;


# direct methods
.method static create(Landroid/app/trust/ITrustManager;II)Z
    .locals 22

    move-object/from16 v0, p0

    move/from16 v3, p1

    move/from16 v4, p2

    .line 120
{call * calls}    return v21
.end method
'''


def make_tree(root, lss=None, auth=None, tms=None, pre=None):
    files = {
        LSS_FILE: lss if lss is not None else lss_text(),
        AUTH_FILE: auth if auth is not None else auth_text(),
        TMS_FILE: tms if tms is not None else tms_text(),
        PRE_FILE: pre if pre is not None else pre_text(),
        # A dex the patcher has nothing to do in.
        'smali_classes4/com/android/server/Other.smali': '.class Lcom/android/server/Other;\n',
    }
    for rel, text in files.items():
        path = Path(root) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def snapshot(root):
    return {str(p.relative_to(root)): p.read_text()
            for p in sorted(Path(root).rglob('*')) if p.is_file()}


def patch(root, *more):
    return subprocess.run([sys.executable, '-I', str(PATCHER), str(root), *more],
                          capture_output=True, text=True)


def body(text, name):
    """Instructions and labels of the one method whose header holds `name`."""
    heads = [m for m in re.finditer(r'^\.method [^\n]*$', text, re.M) if name in m.group(0)]
    assert len(heads) == 1, (name, len(heads))
    rest = text[heads[0].end():].split('\n.end method', 1)[0]
    return [l.strip() for l in rest.split('\n')
            if l.strip() and l.strip()[0] not in '.#']


class PatcherTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def read(self, rel):
        return (self.root / rel).read_text()

    def patched(self, **tree):
        make_tree(self.root, **tree)
        done = patch(self.root)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done

    def assert_untouched(self, done, before):
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, '', 'a framework left as it is reports no changed dex')
        self.assertEqual(snapshot(self.root), before)

    def test_the_changed_dex_folders_are_reported(self):
        done = self.patched()
        self.assertEqual(done.stdout.split(), ['smali', 'smali_classes2', 'smali_classes3'])
        self.assertEqual(self.read(HELPER_FILE), SMALI.read_text())

    def test_the_guest_lock_is_asked_before_the_gatekeeper_guard(self):
        for form in ('decoded', 'fresh'):
            with self.subTest(guard=form), tempfile.TemporaryDirectory() as tmp:
                make_tree(tmp, lss=lss_text(guard=form))
                self.assertEqual(patch(tmp).returncode, 0)
                got = body((Path(tmp) / LSS_FILE).read_text(), ' setLockCredentialInternal(')
                self.assertEqual(got[:11], [
                    f'invoke-direct/range {{p0 .. p3}}, {LSS}->oneosGuestLockSet({CRED}{CRED}I)I',
                    'move-result v0',
                    'if-ltz v0, :oneos_gl_guard',
                    'if-eqz v0, :oneos_gl_refused',
                    # Never the int itself: the method returns a boolean.
                    'const/4 v0, 0x1',
                    'return v0',
                    ':oneos_gl_refused',
                    'const/4 v0, 0x0',
                    'return v0',
                    ':oneos_gl_guard',
                    'const-string v0, "LockSettingsService"',
                ])
                self.assertTrue(got[11].startswith('const-string v1, "OneOS: the screen lock is'))

    def test_a_check_is_answered_by_the_guest_lock_first(self):
        self.patched()
        got = body(self.read(LSS_FILE), ' doVerifyCredential(')
        self.assertEqual(got[:6], [
            f'invoke-direct/range {{p0 .. p3}}, {LSS}->oneosGuestLockVerify({CRED}I{CB}){VCR}',
            'move-result-object v0',
            'if-eqz v0, :oneos_gl_native',
            'return-object v0',
            ':oneos_gl_native',
            f'invoke-virtual {{p1}}, {CRED}->isNone()Z',
        ])

    def test_the_credential_type_comes_from_the_guest_lock_and_survives_a_missing_helper(self):
        self.patched()
        text = self.read(LSS_FILE)
        method = text.split('.method public getCredentialType(I)I\n', 1)[1].split('.end method')[0]
        self.assertTrue(method.startswith('    .locals 2\n'), 'one more register for the exception')
        self.assertIn('    .catch Ljava/lang/Throwable; {:oneos_gl_type_start .. :oneos_gl_type_end}'
                      ' :oneos_gl_type_catch\n', method)
        self.assertEqual(body(text, ' getCredentialType(I)I'), [
            f'invoke-direct {{p0}}, {LSS}->checkHavePermission()V',
            f'invoke-direct {{p0, p1}}, {LSS}->getCredentialTypeInternal(I)I',
            'move-result v0',
            ':oneos_gl_type_start',
            f'invoke-static {{p1, v0}}, {HELPER}->credentialType(II)I',
            'move-result v0',
            ':oneos_gl_type_end',
            ':oneos_gl_type_done',
            'return v0',
            ':oneos_gl_type_catch',
            'move-exception v1',
            'goto :oneos_gl_type_done',
        ])

    def test_the_frp_check_of_the_set_path_is_off(self):
        self.patched()
        self.assertEqual(body(self.read(LSS_FILE), ' enforceFrpNotActive()V')[0], 'return-void')

    def test_a_locked_guest_is_not_reported_to_the_phones_keystore(self):
        self.patched()
        got = body(self.read(TMS_FILE), ' notifyKeystoreOfDeviceLockState(IZ)V')
        self.assertEqual(got[:6], [
            'if-eqz p2, :oneos_gl_unlocked',
            'const-string v0, "TrustManagerService"',
            'const-string v1, "OneOS: the guest lock state is not sent to the keystore of the phone"',
            'invoke-static {v0, v1}, Landroid/util/Slog;->i(Ljava/lang/String;Ljava/lang/String;)I',
            'return-void',
            ':oneos_gl_unlocked',
        ])
        # The unlocked report and the rest of the method are as before.
        self.assertEqual(got[6:], body(tms_text(), ' notifyKeystoreOfDeviceLockState(IZ)V'))

    def test_app_prompts_get_no_device_credential(self):
        self.patched()
        got = body(self.read(PRE_FILE), ' create(')
        at = got.index('move-result v21')
        self.assertIn('ITrustManager;->isDeviceSecure(II)Z', got[at - 1])
        self.assertEqual(got[at + 1], 'const/16 v21, 0x0')
        self.assertEqual(self.read(PRE_FILE).count('->'), pre_text().count('->'),
                         'a constant only: the first dex has no room for new references')

    def test_the_added_methods_call_what_the_class_and_the_helper_have(self):
        self.patched()
        text = self.read(LSS_FILE)
        self.assertEqual(len(re.findall(r'^\.method private oneosGuestLock(Set|Verify)\(', text, re.M)), 2)
        self.assertTrue(text.rstrip('\n').endswith('.end method'))
        self.assertEqual(text.count('\n.method '), text.count('\n.end method'))
        helper = SMALI.read_text()
        calls = set(re.findall(re.escape(HELPER) + r'->([A-Za-z]+\([^)]*\)\S+)', text))
        self.assertEqual({c.split('(')[0] for c in calls}, {'change', 'verify', 'credentialType'})
        for call in calls:
            self.assertRegex(helper, r'(?m)^\.method public static (declared-synchronized )?'
                             + re.escape(call) + '$')
        added = text.split('.method private oneosGuestLockSet(', 1)[1]
        # Private methods of the class are called directly, the helper inside try ranges.
        self.assertIn(f'invoke-direct {{p0, p3}}, {LSS}->invalidateCredentialTypeCaches(I)V', added)
        self.assertEqual(added.count(f'invoke-direct {{p0, v0, p2}}, {LSS}->notifyLockSettingsStateListeners(ZI)V')
                         + added.count(f'invoke-direct {{p0, v4, p2}}, {LSS}->notifyLockSettingsStateListeners(ZI)V'), 2)
        self.assertGreaterEqual(added.count('.catch Ljava/lang/Throwable;'), 3)
        for needs in ('->OK:', '->credIncorrect(', '->fromTimeout(', '->requireStrongAuth(II)V',
                      '->reportSuccessfulStrongAuthUnlock(I)V', '->onCredentialVerified()V'):
            self.assertIn(needs, added)

    def test_public_helpers_of_the_class_are_called_virtually(self):
        self.patched(lss=lss_text(helpers='public'))
        added = self.read(LSS_FILE).split('.method private oneosGuestLockSet(', 1)[1]
        self.assertIn(f'invoke-virtual {{p0, p3}}, {LSS}->invalidateCredentialTypeCaches(I)V', added)
        self.assertNotIn('invoke-direct {p0, p3}', added)
        self.assertIn('invoke-virtual {p0, v0, p2}, ' + LSS + '->notifyLockSettingsStateListeners(ZI)V', added)

    def test_a_framework_of_another_shape_is_left_as_it_is(self):
        cases = {
            'no gatekeeper guard': dict(lss=lss_text(guard='none')),
            'credential type looked at before the return': dict(lss=lss_text(type_body='branch')),
            'no strong-auth field': dict(lss=lss_text().replace('.field private final mStrongAuth:',
                                                                '.field private final mAuth:')),
            'no FRP check': dict(lss=lss_text().replace(' enforceFrpNotActive()V', ' frpCheck()V')),
            'static verify': dict(lss=lss_text().replace('.method private doVerifyCredential(',
                                                         '.method private static doVerifyCredential(')),
            'no timeout response': dict(lss=lss_text().replace('->fromTimeout(', '->fromError(')),
            'strong-auth report not callable': dict(auth=auth_text('private')),
            'no keystore report': dict(tms=tms_text(reports=False)),
            'two device-secure calls': dict(pre=pre_text(calls=2)),
            'no device-secure call': dict(pre=pre_text(calls=0)),
        }
        for name, tree in cases.items():
            with self.subTest(name):
                shutil.rmtree(self.root)
                self.root.mkdir()
                make_tree(self.root, **tree)
                before = snapshot(self.root)
                done = patch(self.root)
                self.assert_untouched(done, before)
                self.assertIn('this framework gets no guest screen lock', done.stderr)

    def test_a_class_missing_from_the_jar_is_no_error(self):
        make_tree(self.root)
        (self.root / PRE_FILE).unlink()
        before = snapshot(self.root)
        self.assert_untouched(patch(self.root), before)

    def test_a_second_run_changes_nothing(self):
        self.patched()
        before = snapshot(self.root)
        done = patch(self.root)
        self.assert_untouched(done, before)
        self.assertIn('already has the guest screen lock', done.stderr)

    def test_a_patched_jar_is_recognised_after_the_helper_moved_to_its_own_dex(self):
        # make-overlays.sh moves OneOS*.smali to a new last dex when one overflows.
        self.patched()
        moved = self.root / 'smali_classes5' / PKG
        moved.mkdir(parents=True)
        shutil.move(self.root / HELPER_FILE, moved / 'OneOSGuestLock.smali')
        before = snapshot(self.root)
        self.assert_untouched(patch(self.root), before)

    def test_a_half_patched_tree_is_an_error(self):
        make_tree(self.root)
        shutil.copy(SMALI, self.root / HELPER_FILE)
        before = snapshot(self.root)
        done = patch(self.root)
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual(done.stdout, '')
        self.assertEqual(snapshot(self.root), before)

    def test_a_missing_helper_file_is_an_error(self):
        make_tree(self.root)
        before = snapshot(self.root)
        done = patch(self.root, str(self.root / 'nowhere.smali'))
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual(snapshot(self.root), before)


DRIVER = r'''
package com.android.server.locksettings;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.attribute.PosixFilePermissions;
import java.security.MessageDigest;
import java.util.Arrays;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;

public final class GuestLockDriver {
    static final String RECORD = "oneos_guest_lock";
    static final String TRIES = "oneos_guest_lock.tries";
    static final byte[] PIN = b("2580");
    static final byte[] OTHER = b("1111");
    static final byte[] PASS = b("correct horse");
    static final long E = 100000L;            // elapsed time since the system started
    static final long W = 1700000000000L;     // wall clock
    static File dir;

    static byte[] b(String s) { return s.getBytes(StandardCharsets.US_ASCII); }
    static void eq(long want, long got, String what) {
        if (want != got) throw new AssertionError(what + ": want " + want + ", got " + got);
    }
    static void yes(boolean ok, String what) { if (!ok) throw new AssertionError(what); }
    static void restart() { OneOSGuestLock.useDir(dir); }
    static boolean has(String name) { return new File(dir, name).exists(); }
    static String text(String name) throws Exception {
        return new String(Files.readAllBytes(new File(dir, name).toPath()), StandardCharsets.US_ASCII);
    }
    static void put(String name, String s) throws Exception {
        Files.write(new File(dir, name).toPath(), s.getBytes(StandardCharsets.US_ASCII));
    }
    static String hex(byte[] in) {
        StringBuilder out = new StringBuilder();
        for (byte x : in) out.append(String.format("%02x", x & 255));
        return out.toString();
    }
    static byte[] unhex(String s) {
        byte[] out = new byte[s.length() / 2];
        for (int i = 0; i < out.length; i++) out[i] = (byte) Integer.parseInt(s.substring(2 * i, 2 * i + 2), 16);
        return out;
    }
    static int type() { return OneOSGuestLock.credentialType(0, -1); }
    static long check(byte[] c) { return OneOSGuestLock.verify(c, E, W); }
    static int set(int type, byte[] c, byte[] saved) { return OneOSGuestLock.change(type, c, saved, E, W); }

    public static void main(String[] a) throws Exception {
        dir = new File(a[1]);
        restart();
        switch (a[0]) {
            case "basics": basics(); break;
            case "record": record(); break;
            case "schedule": schedule(); break;
            case "waits": waits(); break;
            case "restarts": restarts(); break;
            case "damaged": damaged(); break;
            default: throw new AssertionError("no scenario " + a[0]);
        }
        System.out.println("PASS " + a[0]);
    }

    static void basics() throws Exception {
        eq(-1, type(), "no lock: the native type");
        eq(7, OneOSGuestLock.credentialType(0, 7), "no lock: whatever the native type is");
        eq(-1, check(PIN), "no lock: a check is not handled");
        eq(-1, set(-1, null, null), "no lock: a removal is not handled");
        yes(!has(RECORD) && !has(TRIES), "nothing written without a lock");
        eq(0, set(3, b("123"), null), "three digits are refused");
        eq(0, set(2, PIN, null), "an unknown type is refused");
        eq(0, set(0, PIN, null), "type 0 is refused");
        eq(-1, type(), "refused: still no lock");
        yes(!has(RECORD), "refused: no record");

        eq(1, set(3, PIN, null), "set a PIN");
        eq(3, type(), "the type is PIN");
        eq(-1, OneOSGuestLock.credentialType(10, -1), "other users keep the native type");
        eq(0, check(PIN), "the PIN matches");
        eq(1, check(OTHER), "a wrong PIN, no wait yet");
        eq(1, check(null), "null is wrong");
        eq(1, check(new byte[0]), "empty is wrong");
        yes(text(TRIES).equals("1 0\n"), "null and empty are not counted");
        eq(0, check(PIN), "the PIN matches again");
        yes(!has(TRIES), "a match removes the tries file");

        eq(0, set(4, PASS, null), "a change without the old PIN is refused");
        eq(0, set(4, PASS, OTHER), "a change with a wrong old PIN is refused");
        eq(0, set(-1, null, OTHER), "a removal with a wrong old PIN is refused");
        eq(0, set(-1, null, null), "a removal without the old PIN is refused");
        yes(text(TRIES).equals("2 0\n"), "wrong old PINs are counted like wrong tries");
        eq(0, set(3, b("12"), PIN), "too short a new PIN is refused");
        eq(3, type(), "still the PIN");
        eq(0, check(PIN), "and it still matches");

        eq(1, set(4, PASS, PIN), "changed to a password");
        eq(4, type(), "the type is password");
        eq(1, check(PIN), "the old PIN no longer matches");
        eq(0, check(PASS), "the password matches");
        restart();
        eq(4, type(), "the lock survives a restart");
        eq(0, check(PASS), "and matches after it");
        eq(1, set(1, b("0124"), PASS), "changed to a pattern");
        eq(1, type(), "the type is pattern");

        eq(1, set(-1, null, b("0124")), "removed with the pattern");
        eq(-1, type(), "no lock again");
        eq(-1, check(PASS), "a check is not handled again");
        yes(!has(RECORD) && !has(TRIES) && !has(RECORD + ".tmp"), "no files left");
        restart();
        eq(-1, type(), "and none after a restart");
    }

    static void record() throws Exception {
        eq(1, set(3, PIN, null), "set a PIN");
        String line = text(RECORD);
        yes(line.matches("1 3 100000 [0-9a-f]{32} [0-9a-f]{64}\n"), "record format");
        String[] f = line.trim().split(" ");
        byte[] salt = unhex(f[3]);
        String key = hex(MessageDigest.getInstance("SHA-256").digest(PIN));
        byte[] want = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
                .generateSecret(new PBEKeySpec(key.toCharArray(), salt, 100000, 256)).getEncoded();
        yes(hex(want).equals(f[4]), "the record is PBKDF2-HMAC-SHA256 over the hex SHA-256 of the credential");
        yes(Arrays.equals(want, OneOSGuestLock.derive(PIN, salt, 100000)), "derive gives the same");
        yes(!Arrays.equals(want, OneOSGuestLock.derive(OTHER, salt, 100000)), "another PIN, another hash");
        yes(Files.getPosixFilePermissions(new File(dir, RECORD).toPath())
                .equals(PosixFilePermissions.fromString("rw-------")), "the record is the owner's only");
        eq(1, set(3, PIN, PIN), "the same PIN set again");
        yes(!text(RECORD).split(" ")[3].equals(f[3]), "a new salt each time");
        yes(!has(RECORD + ".tmp"), "no temporary file left");
    }

    static void schedule() {
        long[][] want = {
            {-1, 0}, {0, 0}, {1, 0}, {4, 0}, {5, 30000}, {6, 0}, {9, 0}, {10, 30000},
            {11, 30000}, {29, 30000}, {30, 30000}, {39, 30000}, {40, 60000}, {50, 120000},
            {100, 3840000}, {139, 30720000}, {140, 86400000}, {1000000, 86400000},
            {Integer.MAX_VALUE, 86400000},
        };
        for (long[] row : want) {
            eq(row[1], OneOSGuestLock.timeoutMs((int) row[0]), "wait after " + row[0] + " wrong tries");
        }
        long last = 30000;
        for (int n = 11; n <= 200; n++) {
            long t = OneOSGuestLock.timeoutMs(n);
            yes(t >= last, "from the eleventh wrong try the wait never gets shorter (" + n + ")");
            last = t;
        }
    }

    static void waits() throws Exception {
        eq(1, set(3, PIN, null), "set a PIN");
        for (int i = 1; i <= 4; i++) eq(1, check(OTHER), "wrong try " + i);
        yes(text(TRIES).equals("4 0\n"), "four tries on disk");
        eq(1 + 30000, check(OTHER), "the fifth wrong try starts a 30 s wait");
        yes(text(TRIES).equals("5 " + (W + 30000) + "\n"), "the wait is on disk");
        eq(-2 - 30000, check(PIN), "during the wait the right PIN is not looked at");
        eq(-2 - 20000, OneOSGuestLock.verify(OTHER, E + 10000, W + 10000), "10 s later: 20 s left");
        eq(-2 - 20000, OneOSGuestLock.verify(null, E + 10000, W + 10000), "also for an empty try");
        yes(text(TRIES).equals("5 " + (W + 30000) + "\n"), "tries during the wait are not counted");
        eq(0, OneOSGuestLock.change(-1, null, PIN, E + 10000, W + 10000), "no removal during the wait");
        eq(0, OneOSGuestLock.change(4, PASS, PIN, E + 10000, W + 10000), "no change during the wait");
        eq(3, type(), "still the PIN");
        eq(1, OneOSGuestLock.verify(OTHER, E + 30000, W + 30000), "after the wait: wrong try 6, no new wait");
        yes(text(TRIES).equals("6 0\n"), "six tries on disk");
        eq(0, OneOSGuestLock.verify(PIN, E + 30000, W + 30000), "then the right PIN");
        yes(!has(TRIES), "a match forgets the tries");
        eq(1, check(OTHER), "the count starts again");
        yes(text(TRIES).equals("1 0\n"), "one try on disk");
        for (int i = 2; i <= 4; i++) eq(1, check(OTHER), "wrong try " + i);
        // The try is counted before the credential is looked at: the fifth try starts its
        // wait on disk even when it is the right one.
        eq(0, check(PIN), "a right fifth try matches");
        yes(!has(TRIES), "and forgets the tries");
    }

    static void restarts() throws Exception {
        eq(1, set(3, PIN, null), "set a PIN");
        for (int i = 1; i <= 4; i++) eq(1, check(OTHER), "wrong try " + i);
        restart();
        eq(1 + 30000, OneOSGuestLock.verify(OTHER, 5000, W + 60000), "the count survives a restart");
        restart();
        eq(-2 - 20000, OneOSGuestLock.verify(PIN, 1000, W + 70000), "the wait survives a restart: 20 s left");
        restart();
        eq(-2 - 30000, OneOSGuestLock.verify(PIN, 1000, W - 86400000L),
                "clock set back: never longer than the wait of that count");
        restart();
        eq(0, OneOSGuestLock.verify(PIN, 1000, W + 90000), "after the wait the PIN matches");

        put(TRIES, "7 99999999999999\n");
        restart();
        eq(1, OneOSGuestLock.verify(OTHER, 1000, W), "a count without a wait gets none from an edited time");
        yes(text(TRIES).equals("8 0\n"), "and goes on counting");
        put(TRIES, "what is this\n");
        restart();
        eq(1, OneOSGuestLock.verify(OTHER, 1000, W), "an unreadable tries file counts as none");
        yes(text(TRIES).equals("1 0\n"), "counting from one");
        put(TRIES, "-5 0\n");
        restart();
        eq(1, OneOSGuestLock.verify(OTHER, 1000, W), "a negative count is none");
        put(TRIES, "2000000 0\n");
        restart();
        eq(1 + 86400000L, OneOSGuestLock.verify(OTHER, 1000, W), "the count is capped, the wait is a day");
        yes(text(TRIES).equals("1000000 " + (W + 86400000L) + "\n"), "capped on disk");
        eq(3, type(), "the lock is still the PIN");
    }

    static void damaged() throws Exception {
        eq(1, set(3, PIN, null), "set a PIN");
        String good = text(RECORD);
        StringBuilder big = new StringBuilder(good.trim());
        while (big.length() <= 512) big.append(' ');
        String[] bad = {
            "", "\n", "garbage\n",
            good.replaceFirst("^1 ", "2 "),                 // another record version
            good.replaceFirst("^1 3 ", "1 2 "),             // an unknown type
            good.replaceFirst("^1 3 ", "1 -1 "),
            good.replaceFirst(" 100000 ", " 10 "),          // too few rounds
            good.replaceFirst(" 100000 ", " 99999999999 "),
            good.replaceFirst(" 100000 ", " x "),
            good.trim().substring(0, good.length() - 3) + "\n",   // a short hash
            good.trim() + "00\n",
            good.trim().substring(0, good.length() - 2) + "g\n",  // not hex
            good.trim() + " more\n",
            good.replace(' ', '\t'),
            big.toString(),
        };
        for (int i = 0; i < bad.length; i++) {
            put(RECORD, bad[i]);
            restart();
            eq(-1, type(), "damaged record " + i + ": no lock");
            eq(-1, check(PIN), "damaged record " + i + ": a check is not handled");
        }
        put(RECORD, good);
        restart();
        eq(3, type(), "the good record again");
        eq(0, check(PIN), "and its PIN");
        put(RECORD, "garbage\n");
        restart();
        eq(1, set(4, PASS, null), "a new lock over a damaged record");
        eq(4, type(), "the type is password");
        eq(0, check(PASS), "the password matches");
        // The folder is gone: nothing can be stored, nothing is claimed.
        OneOSGuestLock.useDir(new File(dir, "missing"));
        eq(0, set(3, PIN, null), "a lock that cannot be stored is refused");
        eq(-1, type(), "and there is none");
    }
}
'''

JAVAC = shutil.which('javac')
JAVA_BIN = shutil.which('java')


@unittest.skipUnless(JAVAC and JAVA_BIN, 'needs a JDK')
class HelperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.classes = Path(cls.tmp.name) / 'classes'
        src = Path(cls.tmp.name) / 'src' / PKG
        src.mkdir(parents=True)
        (src / 'GuestLockDriver.java').write_text(DRIVER)
        done = subprocess.run([JAVAC, '--release', '17', '-Xlint:all', '-Werror', '-d', str(cls.classes),
                               str(JAVA), str(src / 'GuestLockDriver.java')],
                              capture_output=True, text=True)
        assert done.returncode == 0, done.stderr[-2000:]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def scenario(self, name):
        with tempfile.TemporaryDirectory() as data:
            done = subprocess.run([JAVA_BIN, '-cp', str(self.classes),
                                   'com.android.server.locksettings.GuestLockDriver', name, data],
                                  capture_output=True, text=True, timeout=300)
        self.assertEqual(done.returncode, 0, done.stderr[-1500:])
        self.assertEqual(done.stdout.strip(), 'PASS ' + name)

    def test_one_class_without_lambdas_or_inner_classes(self):
        names = sorted(p.name for p in (self.classes / PKG).glob('OneOSGuestLock*.class'))
        self.assertEqual(names, ['OneOSGuestLock.class'])

    def test_set_check_change_remove(self):
        self.scenario('basics')

    def test_the_record_is_a_salted_pbkdf2_hash_only_the_owner_reads(self):
        self.scenario('record')

    def test_the_wait_schedule(self):
        self.scenario('schedule')

    def test_waits_after_wrong_tries(self):
        self.scenario('waits')

    def test_count_and_wait_survive_a_restart_and_edits(self):
        self.scenario('restarts')

    def test_a_damaged_record_is_no_lock(self):
        self.scenario('damaged')


class SourceTest(unittest.TestCase):
    def test_the_smali_belongs_to_the_java_source(self):
        want = hashlib.sha256(JAVA.read_bytes()).hexdigest()
        head = SMALI.read_text().split('\n# static fields', 1)[0]
        self.assertIn(f'# from OneOSGuestLock.java (sha256 {want});', head,
                      'run scripts/build-guest-lock-smali.sh after changing the Java source')

    def test_the_smali_is_one_plain_class(self):
        text = SMALI.read_text()
        self.assertEqual(text.count('\n.class ') + text.startswith('.class '), 1)
        self.assertTrue(text.startswith('.class public final ' + HELPER + '\n'))
        for word in ('invoke-custom', 'invoke-polymorphic', 'const-method-handle', 'Landroid/'):
            self.assertNotIn(word, text)
        # Nothing of the phone's lock, keys or the service manager.
        for word in ('gatekeeper', 'keystore', 'KeyStore', 'weaver', 'ServiceManager', 'Binder'):
            self.assertNotIn(word, re.sub(r'(?m)^\s*#.*$', '', text))

    def test_the_helper_touches_only_its_own_files(self):
        code = re.sub(r'(?s)/\*.*?\*/', '', JAVA.read_text())
        code = re.sub(r'(?m)//.*$', '', code)
        self.assertEqual(re.findall(r'"(/[^"]*)"', code), ['/data/system'])
        self.assertEqual(sorted(set(re.findall(r'"(oneos[^"]*)"', code))),
                         ['oneos_guest_lock', 'oneos_guest_lock.tries'])
        self.assertEqual(sorted(set(re.findall(r'^import ([a-z]+(?:\.[a-z]+)*)\.', code, re.M))),
                         ['java.io', 'java.security', 'java.util', 'javax.crypto', 'javax.crypto.spec'])
        for word in ('Runtime', 'ProcessBuilder', 'java.net', 'Class.forName', 'System.load'):
            self.assertNotIn(word, code)

    def test_the_overlay_build_runs_the_patcher_after_the_gatekeeper_loop(self):
        text = (ROOT / 'scripts/make-overlays.sh').read_text()
        loop = text.index('for g in guest_no_gatekeeper ')
        line = 'KEY_DIRS="$KEY_DIRS $(python3 -I "$ROOT/switcher/patches/guest_local_lock.py" "$WORK/services")"\n'
        self.assertEqual(text.count(line), 1)
        self.assertGreater(text.index(line), text.index('\ndone\n', loop))
        self.assertLess(text.index(line), text.index('java -jar "$APKTOOL" b -q -o "$WORK/rebuilt.jar"'))

    def test_the_smali_build_script_checks_what_it_makes(self):
        text = (ROOT / 'scripts/build-guest-lock-smali.sh').read_text()
        for needs in ('set -eu', '-Werror', 'invoke-custom', 'sha256'):
            self.assertIn(needs, text)


if __name__ == '__main__':
    unittest.main()
