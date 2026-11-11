# Host-delegated unlock design

## Goal

The guest runs the native ColorOS 17 keyguard and unlocks with One UI's PIN, fingerprint, or face. The guest reads One UI's lock state, verifies it, and never writes it. The ColorOS UI stays in control of the lock screen look and animation.

## Scope

This is an opt-in ColorOS 17 path on a Galaxy S25 Ultra (One UI 9). It
borrows the host's gatekeeper, weaver and installd ABI, so it does not port to
another phone or guest as-is. Other images keep their own lock screen; the
guards in `oneos_switch.sh`, `guest_start.sh` and `return_to_oneui.sh` skip the
snapshot and the SystemUI wave when the guest is not ColorOS.

A portable follow-up is a guest-local "temporary overlay": OneOS stores a
salted PIN verifier in the stage, the guest keyguard checks that verifier, and
the host gatekeeper and weaver are never called. It gives every guest a PIN
without requiring One UI to have one, at the cost of TEE-backed verification.
Fingerprint and face still need per-device HAL and template work.

## Non-goals

- Separate guest PIN, fingerprint, or face in this host-delegated path.
- Independent guest file-based encryption.
- Guest enrollment of new biometrics.
- A custom lock screen app.

## Architecture

### Host snapshot

After One UI's system_server stops, the switch copies these files to the guest's staged data:

- `/data/system/locksettings.db`
- `/data/system_de/0/spblob/<sp-handle>.spblob`
- `/data/system/users/0/settings_fingerprint_0.xml`
- `/data/system/users/0/settings_face.xml`
- `/data/system/users/0/face_enrolled_position_0.xml`

The copy is one way. The guest never mounts the host paths read-write, and the switch never copies a guest file back.

### Guest verification

The guest's `LockSettingsService` reads the copied database and SP blob. PIN verification calls the host `IGateKeeperService.verifyChallenge` with the host `user0_handle`. Fingerprint and face verification call the host HALs with the host SID. The host keeps the only credential and template store.

The guest's native ColorOS keyguard supplies the PIN pad, fingerprint icon, face animation, blur, and unlock transition. The guest's Settings app must not enroll new biometrics.

### Host watchdog

The switch records SHA-256 hashes of the host database, gatekeeper handle, SP blob, and keystore database before the guest starts. It checks them again after the guest returns. A mismatch stops the session and restores the host files from a root-only backup.

## Fail-safes

1. **Read-only host access.** The switch copies the host files after One UI stops. The guest gets copies. No host path is writable from the guest.
2. **Hash fence.** The switch stores host SHA-256 values in `/data/local/tmp/oneos/guard/host.sha256` and keeps a root-only backup in `/data/local/tmp/oneos/guard/backup/`.
3. **Gatekeeper writes blocked.** `LockSettingsService.setLockCredentialInternal` and `setLockCredentialWithTokenInternalLocked` return false. Every `enroll`, `clearSecureUserId`, and `reportDeviceSetupComplete` call is a nop. These guards already exist.
4. **Weaver writes blocked, reads allowed only for the host slot.** `guest_no_weaver.py` keeps `write` and `destroy` as nops. It allows `getWeaverServiceLocked()` so the host SP blob can be read. If the SP blob does not use weaver, the read path is unused.
5. **Vold keys untouched.** `guest_no_vold_keys.py` keeps every create, destroy, protect, unlock, and lock call as a nop.
6. **Biometric cleanup blocked.** `guest_no_biometric_cleanup.py` keeps the host templates from being deleted.
7. **Biometric enrollment blocked.** A new `guest_no_biometric_enroll.py` makes the guest `FingerprintService` and face service enrollment methods return failure. The guest can authenticate but cannot add a template.
8. **Guest database is a copy.** The guest may update its own `locksettings.db`, failed-attempt counters, or keyguard state. Those writes stay in guest data.
9. **Boot watchdog.** If the guest does not reach `sys.boot_completed` in 120 seconds, or the keyguard does not answer in 30 seconds, the host triggers the normal return to One UI.
10. **Post-return gate.** The host waits for One UI `system_server`, user 0 unlock, and matching hashes. If One UI does not unlock, the switch stops and reports the failure. It does not erase data.
11. **No automatic host reboot.** A reboot loses soft root. The watchdog returns to One UI first and asks the user before any reboot.
12. **Test order.** Wrong PIN, wrong fingerprint, and wrong face must all fail before a correct credential is tried. Every guest session ends with a One UI unlock check.

## Risks

- The SP blob may be weaver-protected. If the read-only weaver path fails, the guest keyguard cannot verify the PIN and we fall back to the gatekeeper-only path or stop.
- The guest keyguard may write to its copied database. The copy can diverge from the host. A fresh copy is made on every start.
- Guest data is One UI's user-0 data. The lock screen gates the guest UI, not storage. Root or adb can bypass it.
- The host's biometric HAL is shared. A guest bug could still call an unexpected method. The enrollment and cleanup guards are the barrier.

## Acceptance

- Correct One UI PIN unlocks the ColorOS keyguard.
- Wrong PIN is rejected.
- Enrolled fingerprint unlocks. Wrong finger is rejected.
- Enrolled face unlocks. Wrong face is rejected.
- One UI still unlocks after every guest session.
- Host hashes match before and after every session.
- Guest boot timeout returns to One UI.
- No new biometric template appears in One UI's settings XML.
