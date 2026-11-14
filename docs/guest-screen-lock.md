# The guest's own screen lock

A guest system shares the phone's gatekeeper, weaver and keystore daemon with One UI, so its
framework refuses to set a screen lock: a lock set there would be enrolled for user 0 on the
phone itself (`switcher/patches/guest_no_gatekeeper.py`, `guest_no_weaver.py`). Until now a guest
therefore had no lock screen credential at all.

`switcher/patches/guest_local_lock.py` gives the guest a lock of its own: a PIN, pattern or
password set in the guest's Settings as usual, kept and checked inside the guest. The idea came
from pull request #152 by @vdcoolok.

## What it is

- **A privacy lock for the guest's lock screen.** Somebody who picks up the phone while the guest
  is running cannot get past its lock screen without the PIN.
- The record is one line in the guest's `/data/system/oneos_guest_lock` (on the phone:
  `/data/local/tmp/oneos/data/system/`): a salted PBKDF2-HMAC-SHA256 hash (100,000 rounds), never
  the credential. It belongs to that guest system's data and goes away with it.
- Wrong tries are counted on disk before the credential is looked at: 30 s after the 5th and 10th
  wrong try, 30 s after every try from the 11th, from the 40th twice as long every ten tries
  (1 min, 2 min, ... about 8.5 hours), one day from the 140th. Count and wait survive a restart
  of the guest.
- Changing or removing the lock needs the current one.

## What it is not

- **Not protection for the data.** A restart of the phone always lands in One UI, which has no
  screen lock while OneOS is in use; with root there, the guest's files and the lock record are
  within reach. The guest's storage is not encrypted with this lock.
- **No fingerprint or face.** Enrolling them needs a token from the phone's gatekeeper, which the
  guest lock cannot and must not get. "Add fingerprint" in the guest refuses or shows an error.
- **Not a device credential for apps.** An app that asks for the device PIN in its own prompt, or
  ties keys or passkeys to the screen lock, behaves as on a phone without a secure lock.
- Nothing of it reaches the phone: no gatekeeper enrolment, no weaver slot, no auth token, no
  keystore call. One UI's lock state is exactly what it was before the session.

## Forgotten

From One UI, with root:

```
su -c 'rm -f /data/local/tmp/oneos/data/system/oneos_guest_lock /data/local/tmp/oneos/data/system/oneos_guest_lock.tries'
```

The guest starts without a lock the next time.

## Which systems have it

| System | Set | From |
| --- | --- | --- |
| ColorOS on the Z Folds (Find N6) | `n6-f8u`, n6g r16 | 0.4.94 |
| ColorOS IN (Find X9 Ultra) | `x9u-in-sultra`, x9u_in r71 | 0.4.95 |
| HyperOS | `hyper-f8u`, hyperos r26 | 0.4.95 |
| Nothing OS | `nothing-f8u`, nothing r33 | 0.4.95 |
| OriginOS | `originos`, originos_cn r18 | 0.4.95 |

The 0.4.95 sets were made with `scripts/patch-built-jar.sh` from the jars of the revision before
(only `services_patched.jar` and the hash list differ) and had not run on a phone when they were
uploaded. Not yet: the Pixel sets, Infinity-X and OxygenOS 16. Their `LockSettingsService` has
another shape (`getCredentialType`, the wrong-credential answer, no free register), so the patcher
leaves them unchanged and the guest refuses a screen lock there as before.

## How it is built

`guest_local_lock.py` runs in `scripts/make-overlays.sh` after the gatekeeper guard and makes six
changes to `services.jar`, all or none; a framework of another shape is left as it is (no guest
lock there):

| Where | Change |
| --- | --- |
| `LockSettingsService.setLockCredentialInternal` | the guest lock is asked first, in front of the gatekeeper guard; with no guest lock and nothing to set, the guard answers as before |
| `LockSettingsService.doVerifyCredential` | with a guest lock set, its record answers: match, wrong (with the wait), or "try again in" |
| `LockSettingsService.getCredentialType` | the guest lock's type for the lock screen and Settings; the service's own state stays "none", so storage and keys are handled as without a lock |
| `LockSettingsService.enforceFrpNotActive` | off: in a guest "FRP active" only says that One UI's FRP secret could not be read (`guest_pdb_init_survives.py`), and the only lock behind the check is the guest's own record |
| `TrustManagerService.notifyKeystoreOfDeviceLockState` | a locked guest is not reported to the phone's keystore daemon (it would drop user 0's unlocked-device keys until the phone itself is unlocked) |
| `biometrics.PreAuthInfo` | apps' prompts see no device credential: the prompt would need a gatekeeper token |

The checks themselves are in `OneOSGuestLock` (`switcher/patches/OneOSGuestLock.java`, one class,
only `java.*` and `javax.crypto`); `scripts/build-guest-lock-smali.sh` turns it into the smali the
patcher adds. Every call into it from the framework is inside a try range, so a class that cannot
be loaded leaves the framework as it was.

Tests: `python3 scripts/test-guest-local-lock.py` (the patcher on a small smali tree, the class on
the JVM, the wiring).
