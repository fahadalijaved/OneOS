# Guest-local PIN and ColorOS unlock

Status: draft, 2026-11-11. `feat/guest-local-pin` is the branch under review
(PR #152). `feat/host-delegated-unlock` is kept only as the closed PR #132
head; it does not carry the guest-local PIN, the biometric import, or the
battery gate.

## Branch

Base: `upstream/main` `913456d` (OneOS 0.4.93), with 0.4.92 and 0.4.93 merged.
The branch merges
`feat/host-delegated-unlock` (`0bfa556`..`751f2ff`) for its ColorOS fixes, adds
the guest-local PIN patcher (`d9f85f0`, `4cfbc6e`), and then removes the
host-delegated lock-state path. The guest-local PIN is the only screen lock.

## Removed host-delegated unlock

The old path snapshotted One UI's `locksettings.db`, gatekeeper handle,
biometric settings, and SP blob into the guest, then verified against the
phone's gatekeeper and weaver. It was ColorOS 17/S25 Ultra only and shared the
host's credentials and biometric templates.

The current tree does not use it:

- `switcher/assets/oneos_lockstate.sh` is gone.
- `oneos_switch.sh` no longer takes a host snapshot or stages one.
- `return_to_oneui.sh` no longer verifies a host lock-state hash.
- `oneos_root.sh`, `RootScript.kt`, and the app's script map no longer stage
  the script.
- The keyguard enable that depended on the staged marker now runs on every
  guest boot in `guest_runtime.sh`, against the guest's own database.

The host-fingerprint HAL fixes that the old branch introduced are kept: the
ColorOS AIDL v3 sensor forcing, the `fpdata` directory, the panel position
props, and the feature XMLs do not read One UI's credentials.

## What was kept from the merged branch

- `switcher/patches/guest_force_aidl_fingerprint.py`: ColorOS opens Samsung's
  AIDL v3 fingerprint HAL instead of the absent HIDL 2.1 adapter.
- `switcher/patches/guest_skip_negotiation.py`: skips the 3 s keystore
  property wait on PIN verification.
- `guest_prepare.sh`: fingerprint `fpdata`, sensor feature XMLs, and the
  Samsung camera overlay.
- `guest_props.sh`: optical icon position and size from the panel DPI.
- `guest_start.sh`: ColorOS audio policy overlay and audio HAL restart.
- `switcher/patches/systemui-fingerprint-wave/` and its build/install scripts:
  the ColorOS animation fix.

## Guest-local PIN

### Why

One UI's credential store belongs to the phone. The guest must not read or
write it, and a guest without One UI's PIN must still have a working screen
lock. A guest-owned verifier gives the ColorOS keyguard a PIN on any firmware,
at the cost of TEE-backed verification: the lock is only as strong as the
guest's `/data`.

### Storage

`/data/system/oneos_pin` holds `base64(salt):base64(SHA-256(salt || pin))`.
The salt is 16 bytes from `SecureRandom`; the file is fsynced after writing.
Verification uses `MessageDigest.isEqual`. No plaintext PIN is stored.

### LockSettingsService

`switcher/patches/guest_local_pin.py` patches
`smali_classes2/com/android/server/locksettings/LockSettingsService.smali`:

- `setLockCredentialInternal` for user 0: a PIN stores the verifier, `none`
  clears it, and any other credential falls through to the existing
  `guest_no_gatekeeper.py` guard.
- `doVerifyCredential` for user 0: a PIN is checked locally. On success it
  calls the progress callback, `setDeviceUnlockedForUser`,
  `reportSuccessfulStrongAuthUnlock`, and `notifyLockSettingsStateListeners`,
  then returns `VerifyCredentialResponse.OK`. A wrong PIN returns
  `OTHER_ERROR`.
- `getCredentialTypeInternal` reports a PIN while the file exists.
- `enforceFrpNotActive()` is skipped because the guest shares the phone's FRP
  partition.
- Adds `OneOsPin.smali` in the same package with `store`, `verify`, `exists`,
  `clear`, and the SHA-256 helper.

`scripts/make-overlays.sh` runs `guest_no_gatekeeper.py` first, then
`guest_local_pin.py`, so the PIN path sits in front of the fail-closed
`setLockCredentialInternal` guard. Without that order the guard returns false
before the PIN can be stored.

### Surviving a fixes update

The app's update installs upstream's `services_patched.jar`, which has no PIN
verifier. The guest's `/data/system/oneos_pin` stays, so ColorOS then reports
"Screenlock already set" and no PIN can be set or checked.

The PIN-patched jar is therefore kept in the guest's own data:

```
/data/local/tmp/oneos_pin/services_patched.jar
/data/local/tmp/oneos_pin/base.sha256
```

`base.sha256` is the hash of the stage `services_patched.jar` the copy was
built from. `guest_prepare.sh` binds the kept jar only while the hashes match,
relabels it `system_file`, and logs which jar it used. After a new fixes build
the stamp no longer matches, so the stock jar is used and a warning is printed;
re-running `scripts/install-pin-jar.sh` rebuilds the kept copy for the new
build. The update leaves the guest's `data/` alone, so the copy survives.

`scripts/install-pin-jar.sh` pulls the stage jar, runs
`scripts/patch-built-jar.sh` **twice** — `guest_force_aidl_fingerprint.py`, then
`guest_local_pin.py` — checks that `classes.dex` has no HIDL lockout call and
that `classes2.dex` contains `OneOsPin`, pushes the result and its stamp into
the guest's `data/local/tmp/oneos_pin`, and labels both. The release jar lacks
both patches; with only the PIN patch the keyguard lists a print, but
`FingerprintProvider` falls back to the absent HIDL adapter
(`Fingerprint HAL not available`).

### Tests

On the S25 Ultra ColorOS 17 guest:

- Setting a PIN makes the keyguard show PIN entry.
- A wrong PIN is rejected; the correct PIN unlocks.
- Clearing the PIN returns the keyguard to no credential.
- One UI's PIN, fingerprint, and face still work after returning to One UI.
- The guest does not call the phone's gatekeeper or weaver to verify the PIN.

## Standard fingerprint HAL

A test client (`FpUnlock.java`, host path `/tmp/opencode/hal/src/...`, not
committed) opened `android.hardware.biometrics.fingerprint.IFingerprint/default`
(AIDL v3), used the standard `ITestSession` to release the framework's HAL
session, opened its own session, and authenticated. On success it broadcast
`com.oneos.UNLOCK_KEYGUARD`; the keyguard hook dismissed the keyguard. A
correct finger unlocked and a wrong finger was rejected. No host
gatekeeper/weaver call was involved.

This is a probe, not a shipping path. The HAL is the phone's: any finger
enrolled in One UI can satisfy the guest, and there is no guest-specific
enrollment filter.

## Biometric enrollments

ColorOS keeps the enrollment metadata in `/data/system/users/0`; the templates
stay in the phone's TEE. The removed host lock-state snapshot was what copied
that metadata, so without it an image with a stale copy listed a print
("fingerprint is on, no glyph") and a fresh install listed nothing ("Add now
does nothing").

`guest_prepare.sh` copies, on every switch:

- `settings_fingerprint_0.xml` -> `settings_fingerprint.xml` (ColorOS reads the
  legacy AOSP name),
- `settings_face.xml` and `face_enrolled_position_0.xml` unchanged,
- owner `1000:1000`, mode 0644, label `system_data_file`.

The copy is a mirror, not a merge: a file One UI does not have is removed from
the guest, so a fingerprint or face deleted in One UI disappears from ColorOS
too. No credential, gatekeeper handle or SP blob is read.

Enrolling a new finger or face **inside** ColorOS is not possible with a
guest-local PIN. `FingerprintEnrollClient.doEnroll` sends a gatekeeper
`HardwareAuthToken` to `ISession.enroll`, and ColorOS gets that token from a
successful credential confirmation. The guest has a gatekeeper service but no
credential in it (`/data/system/gatekeeper.password.key` absent, since the PIN
is verified locally), so there is no token and enrollment stops. Minting one
would need the phone's gatekeeper, which is the host-delegated path this branch
removes. Enroll in One UI; the guest imports the result on the next switch.

Tested on the S25 Ultra: with the guest's `settings_fingerprint.xml` and
`settings_face.xml` deleted, the next switch logged `Guest biometrics: carried
One UI's 3 enrollment file(s) into the guest`; the three files landed at
223/160/44 bytes and ColorOS listed both face and fingerprint.

## ColorOS keyguard and fingerprint wave

The animation fix is the checked-in
`switcher/patches/systemui-fingerprint-wave/` patch, with its README and a
unified diff against stock ColorOS 17 SystemUI. It is the implementation that
stays.

It changes the UDFPS mech in `classes3.dex`:

- Records `oneosWakeAt` in `onStartedWakingUp`.
- If the touch arrives within 1200 ms of the wake, skips the pressed wave and
  shows the glyph immediately through
  `OnScreenFingerprintIcon.setVisibility(0, "startPressedAnimation")`.
- Posts `OneOsGlyphShow` 300 ms after screen-on; it calls
  `showFingerprintIconTemporarily` and forces the icon visible at alpha 1 for
  the window where `fpIconShow` is rejected because the screen was still off.
- At auth success (`hideUdfpsOverlay$1`), sets `pendingHide` and starts a fresh
  `OplusAnimationDrawable` through `oneosStartWave`. The full wave plays over
  the home screen, and the pending hide removes the ring at its end.
- Builds the auth wave with `getOptions(8)` and 16 ms frames, not the pressed
  animation. Changing the fingerprint animation setting therefore does not
  remove the wave.
- Disables `notifyHighlightVisibleUpdate`, keeping the black
  `OnScreenFingerprintDimLayer` window out of the unlock path.

`scripts/make-systemui-wave.sh` decodes the stock APK, applies the patch,
rebuilds `classes3.dex`, and replaces it in the original archive.
`scripts/install-systemui-wave.sh` stages the APK in the guest's
`/data/local/tmp`, writes the stock size and SHA-256 stamps, and binds it.
`switcher/assets/guest_start.sh` applies the bind before zygote starts on every
boot. Two fences keep it off other firmware: the guest must have ColorOS's
`oplus-services.jar`, and its stock SystemUI must match the size and hash the
APK was built from. The same hook restores `min_refresh_rate 120` after boot;
without the floor SurfaceFlinger thrashes 10-120 Hz and the wave looks like
30 fps.

Tested stock build:

```
SystemUI.apk  sha256 0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77
classes3.dex  sha256 793b3239aaaff2272bc912c67396ced50bd3077e30f8ab511e830389754e5071
```

The build script refuses another build unless `ONEOS_WAVE_ALLOW_OTHER=1` is
set.

The ad-hoc `glyphfix11` SystemUI and `OneOsUnlockReceiver` hook built earlier
in this session are not part of the branch and must not be deployed. They
reused the pressed animation, so changing the animation setting stopped the
wave. The branch patch replaces that path entirely.

## Merge

```
ff9b8c2 Bring guest-local PIN into host-delegated unlock
eb9415a Merge host-delegated unlock and the fingerprint wave
4cfbc6e Build the guest-local PIN patch into services.jar
d9f85f0 Verify a guest-local PIN inside LockSettingsService
751f2ff Record the host-delegated unlock portability limits
```

The commit on top of `ff9b8c2` removes the lock-state script and its wiring.
Both branches then build the guest-local PIN and keep the wave patch. Later
commits add the kept PIN jar, the AIDL patch inside that jar,
and the biometric import. The branch is merged with `upstream/main` 0.4.92
(`b9dd0ec`) and 0.4.93 (`64aa09a`).

## Portability

- **Guest-local PIN:** a patcher anchored to AOSP `LockSettingsService`
  signatures and register counts. Other firmware may need new anchors, but the
  verifier and the method hooks are not ColorOS-specific.
- **Wave patch:** tied to the tested ColorOS 17 SystemUI build. Another build
  must be re-patched from its own smali and gets new stamps.
- **Host-delegated unlock:** removed. Its history remains in the merge commits,
  but nothing in the tree snapshots or verifies against One UI's credentials.

## Safety

- One UI's credential store is never read or written. The guest-local PIN lives
  in the guest's `/data`; no lock-state snapshot is taken.
- `guest_no_gatekeeper.py` still blocks every non-PIN credential write, and the
  weaver and biometric cleanup guards are unchanged.
- The 42.0 C battery gate and the 45 C thermal cap are unchanged.
- The return path to One UI is unchanged. A successful return still ends with
  One UI's `system_server`, user 0 unlocked, and no panic.

## Verification

Host checks run on the merged tree:

```sh
python3 -m py_compile switcher/patches/guest_local_pin.py
sh -n scripts/make-overlays.sh scripts/make-systemui-wave.sh \
      scripts/install-systemui-wave.sh switcher/assets/guest_start.sh \
      switcher/assets/guest_prepare.sh switcher/assets/guest_props.sh \
      switcher/assets/guest_runtime.sh switcher/assets/oneos_switch.sh \
      switcher/assets/return_to_oneui.sh
git diff --check
```

`scripts/check-shell.py` needs `dash` and `busybox`, which are not installed on
this host, so it was not run. On-device `busybox sh -n` over the same scripts
and a full switch/return remain.

The PIN patcher was also run against the device's pre-pin `services.jar`. The
rebuilt `classes2.dex` is 10,063,824 bytes, the same size as the tested
`services_pin6.jar`, and the PIN block sits in front of the
`guest_no_gatekeeper.py` return. That confirms the anchors and the ordering on
the real 0.4.90 tree.

## Open

- Rebuild `services_patched.jar` through `make-overlays.sh` and confirm the PIN
  path on a fresh guest boot with the removed lock-state scripts.
- Deploy the branch's `SystemUI_wave.apk` over the current `glyphfix11` bind and
  test a native unlock after the animation setting change.
- Enrollment inside ColorOS: unsupported, because it needs a gatekeeper
  `HardwareAuthToken`; add fingers and faces in One UI.
- Biometric isolation: the templates are the phone's TEE entries, shared with
  One UI; the guest only mirrors the metadata. A finger enrolled in One UI can
  unlock the guest.
