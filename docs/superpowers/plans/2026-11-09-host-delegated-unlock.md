# Host-delegated unlock implementation plan

## Goal

Run the native ColorOS 17 keyguard in the guest and unlock it with One UI's PIN,
fingerprint, or face. One UI remains the only owner of the credential, the
gatekeeper handle, the weaver slot, and the biometric templates. The guest gets
a read-only snapshot and verifies against the host services.

## Architecture

The switch snapshots One UI's lock state after One UI's `system_server` stops and
before the guest starts. The snapshot goes into the guest's staged data. The
host copy is hashed and backed up in a root-only guard directory. The guest's
`LockSettingsService` verifies the copied credential through the host
gatekeeper. Fingerprint and face use the host Samsung HALs with the host user 0
SID. The guest never enrolls, clears, or writes host lock state.

## Tech stack

- POSIX shell under dash and the phone's busybox
- Android 17 `services.jar` smali patches
- Kotlin guest app only for the fallback keyguard UI
- `adb`, `sha256sum`, `stat`, `nsenter`
- Existing OneOS switch, return, and stage scripts

## Spec

`docs/superpowers/specs/2026-11-09-host-delegated-unlock-design.md`

## Global constraints

- Never mount a host lock-state path writable in the guest.
- Never copy guest lock state back to the host.
- Keep the One UI screen-lock switch gate at its current default. The user
  already enabled the Advanced override.
- Keep the 42.0 C battery gate and the heat cap.
- One UI must be reachable after every test.
- No automatic reboot. A reboot loses soft root.
- The host has no Android SDK platforms or build-tools; use `apktool` on the
  existing stage `services.jar` for guard changes, not Gradle.
- Shell changes must pass `sh -n`, `git diff --check`, and `busybox sh -n` on
  the phone.

## Review focus

The host hash fence must fail closed. The weaver patch must allow only the
read path for the host slot and keep `write` and `destroy` as nops. The
biometric enrollment guard must cover every enrollment entry point in
`FingerprintService` and the face service. The guest database must always be a
fresh copy. The post-return check must run before One UI starts.

## Tasks

### 1. Baseline and environment check

Files: none.

Steps:

- [ ] Record the current branch, HEAD, stage hashes, and `files.sha256` state.
- [ ] Confirm `apktool`, `java`, and `zipalign` are available on the host, or
      record the fallback.
- [ ] Confirm the guest is not running and One UI is reachable.
- [ ] Save the current guest `locksettings.db`, `spblob`, and guards under
      `/tmp/opencode/oneos-perf/baseline-unlock/`.

Tests:

- `sha256sum -c files.sha256` on the phone returns 58 OK.
- `git status --short` is clean or only the design and plan files are new.

### 2. Lock-state guard helper

Files: `switcher/assets/oneos_lockstate.sh`

Interface:

- `snapshot`: hash the host files, copy them to `guard/backup`, and write
  `guard/host.sha256`.
- `stage`: copy the backup into the guest staged data.
- `verify`: run `sha256sum -c guard/host.sha256`; return non-zero on mismatch.
- `restore --confirm`: copy the backup back to the host paths; only the return
  script calls it after a failed verify.

Steps:

- [ ] Add the host paths for `locksettings.db`, its WAL and SHM, the gatekeeper
      handle, user 0 `spblob` files, the three biometric XMLs, and the keystore
      database.
- [ ] Add the guest staged destinations under `$STAGE/data`.
- [ ] Create `guard/` and `guard/backup/` with mode 0700.
- [ ] Copy with `cp -a`; keep the host files untouched.
- [ ] Set the guest copies to `system:system`; database 0600, spblob 0600,
      directories 0700.
- [ ] Print one timestamped line per action; no secrets.

Tests:

- `sh -n switcher/assets/oneos_lockstate.sh`
- `busybox sh -n` on the phone
- Run `snapshot` and `verify` on a scratch guard directory; the host hashes
  must match before and after.
- Corrupt a copy in `guard/backup` only, run `verify`, and confirm it fails.
  Restore the copy; do not touch the host files.

Commit: `Add a read-only lock-state guard for the guest keyguard`

### 3. Wire the snapshot into the switch

Files: `switcher/assets/oneos_switch.sh`

Steps:

- [ ] Call `oneos_lockstate.sh stage` after `guest_prepare` and after the guest
      data mounts, immediately before the takeover daemon starts.
- [ ] Call `oneos_lockstate.sh snapshot` after One UI's `system_server` stops
      and before any guest process starts.
- [ ] If `snapshot` fails, abort the switch and return to One UI.
- [ ] Keep the guest DB copy out of `guest_prepare`'s lock-state cleanup.

Tests:

- Start a guest with the new script; the guest `/data/system/locksettings.db`
  is the host snapshot, owned by system, and the guest boot completes.
- The host database hash is identical before and after the switch.
- Stop and restart the guest once; the second copy is fresh.

Commit: `Snapshot One UI's lock state for the guest keyguard`

### 4. Wire verify and restore into the return

Files: `switcher/assets/return_to_oneui.sh`

Steps:

- [ ] Call `oneos_lockstate.sh verify` after the guest processes stop and
      before `[4/4] Starting One UI in place`.
- [ ] On mismatch, print `@@FAIL lock state changed`, stop the return, and
      restore from the guard backup with `--confirm`.
- [ ] Re-run `verify`; only then continue to One UI.
- [ ] Never start One UI while a hash mismatch is unresolved.

Tests:

- A normal return passes `verify` and reaches One UI `system_server`.
- A deliberate mismatch in a scratch guard stops before One UI.
- Restore only from the backup; the host files match again.
- One UI unlocks after the restored return.

Commit: `Fence the return on One UI's lock-state hashes`

### 5. Allow read-only weaver access

Files: `switcher/patches/guest_no_weaver.py`, the stage `services.jar`

Steps:

- [ ] Change the patch so `getWeaverServiceLocked()` returns the host service.
- [ ] Keep `write` and `destroy` calls as nops.
- [ ] Keep the guest's lock-state cleanup from deleting host weaver slots.
- [ ] Rebuild only the `services.jar` smali and push it to the guest stage.
- [ ] Verify `verifyChallenge` works and `weaver.write` is never called.

Tests:

- Wrong PIN returns a failed verification.
- Correct PIN returns success only on the guest keyguard.
- Host weaver slot and `locksettings.db` hashes do not change.
- A forced `write` call in a test harness is nop.

Commit: `Allow the guest to read the host weaver slot without writing it`

### 6. Block biometric enrollment

Files: new `switcher/patches/guest_no_biometric_enroll.py`,
`scripts/make-overlays.sh`, the stage `services.jar`

Steps:

- [ ] Find every `FingerprintService` enrollment entry point.
- [ ] Find every face enrollment entry point.
- [ ] Return failure before the HAL call; keep authentication paths untouched.
- [ ] Keep `guest_no_biometric_cleanup.py` active.
- [ ] Add the patch to the overlay build in the same order as the cleanup
      guard.

Tests:

- The guest keyguard authenticates an enrolled finger and face.
- The guest Settings enrollment screen fails without a HAL enrollment call.
- Host `settings_fingerprint_0.xml`, `settings_face.xml`, and the HAL template
  count do not change.
- One UI still unlocks with its enrolled biometrics.

Commit: `Block guest biometric enrollment without touching authentication`

### 7. Validate the native ColorOS keyguard

Files: none.

Steps:

- [ ] Start the guest with the copied lock state.
- [ ] Confirm the native ColorOS PIN pad appears.
- [ ] Try five wrong PINs; confirm rejection and the retry timer.
- [ ] Enter the correct One UI PIN; confirm the guest unlocks.
- [ ] Confirm the fingerprint icon and face prompt appear.
- [ ] Test a wrong finger and a wrong face; confirm rejection.
- [ ] Test the enrolled finger and face; confirm unlock.
- [ ] Confirm the guest Settings cannot enroll a new biometric.

Tests:

- Every wrong credential fails.
- Every correct credential unlocks.
- No host hash changes.
- One UI unlocks after the guest returns.

### 8. Watchdogs and fail-safe matrix

Files: `switcher/assets/oneos_switch.sh`,
`switcher/assets/return_to_oneui.sh`,
`app-android/app/src/full/kotlin/com/fahadali/oneos/session/*`

Steps:

- [ ] Add the 120 s guest boot watchdog.
- [ ] Add the 30 s keyguard response watchdog.
- [ ] On timeout, run the normal return path, not a reboot.
- [ ] Add a post-return check for One UI `system_server` and user 0 unlock.
- [ ] Add a guard log to `guard/guard.log`.

Tests:

- Kill the guest `system_server`; the watchdog returns to One UI.
- Hold the keyguard unresponsive; the watchdog returns to One UI.
- Corrupt the guard copy; the return refuses to start One UI until restore.
- One UI unlocks after every failure case.
- No automatic reboot occurs.

Commit: `Add fail-closed watchdogs for the guest keyguard`

### 9. Usability test plan

Files: `docs/superpowers/specs/2026-11-09-host-delegated-unlock-usability.md`

Steps:

- [ ] Define the tasks: unlock with PIN, fingerprint, face, wrong PIN, wrong
      finger, wrong face, recovery from a failed guest boot.
- [ ] Define pass criteria: unlock under 2 s after a correct credential, clear
      error on a wrong credential, no One UI lock-state change.
- [ ] Run the plan on the phone with the user present.
- [ ] Record the results and any ColorOS animation differences.

### 10. Docs and cleanup

Files: `docs/`, `tasks/`, `AGENTS.md`

Steps:

- [ ] Update the design and plan with the measured results.
- [ ] Remove scratch scripts under `/data/local/tmp` and `/tmp/opencode`.
- [ ] Keep the guard backup until the user confirms One UI unlock.
- [ ] Do not commit or push the perf branch without permission.
