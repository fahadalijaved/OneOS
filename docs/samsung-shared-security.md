# RFC: shared Samsung security during a OneOS session

This draft proposes retaining genuine Samsung security authority while ColorOS
provides the guest experience. The full eighteen acceptance requirements remain
the intended scope; this initial contribution completes none of them as an
Android feature. It adds an isolated scheduling primitive and first-party JVM
tests, without wiring them into the app, switch scripts or guest framework.
There is no Android, Binder, native credential, biometric or device acceptance.

## Intended behavior

All eighteen cases below remain pending device evidence. Correct original UI,
input, policy and recovery behavior remain required; model success is insufficient.

| Case | Required behavior |
| --- | --- |
| PIN-01 | From a verified credential-free baseline, set a PIN in One UI; it unlocks both OSes. |
| PIN-02 | From a separate credential-free baseline, set it in ColorOS; it unlocks both without a second setup. |
| PIN-03 | Change it in One UI; the new PIN works in both and the old PIN fails ordinary unlock. |
| PIN-04 | Change it in ColorOS; the new PIN works in both and earlier PINs fail ordinary unlock. |
| PIN-05 | Repeat changes and switches in both directions without stale caches or delayed reconciliation. |
| PIN-06 | Preserve genuine wrong-PIN, lockout, cancellation, lockdown and additional-factor policy. |
| PIN-07 | Preserve supported removal/password/pattern/recovery behavior; prior-PIN recovery is not ordinary unlock. |
| FP-01 | Existing fingerprints work in both, including app authentication, after required primary authentication. |
| FP-02 | Enrollment in One UI appears and authenticates in both. |
| FP-03 | Enrollment in ColorOS appears and authenticates in both. |
| FP-04 | Removal from either OS removes the selected prints in both, preserves others and matches authenticator generations. |
| FP-05 | PIN changes preserve supported enrollment continuity and required reauthentication, without unsolicited reset. |
| APP-01 | Credential confirmation, BiometricPrompt/CryptoObject and fallback preserve user/confirmation policy and authorize the exact fresh native operation and caller/key/challenge. |
| DATA-01 | CE data and applicable app keys remain usable; intended policy invalidation is distinguished from corruption. |
| FAIL-01 | Interrupted mutation/cleanup/callback/handoff yields a resolved outcome or explicit uncertainty, without blind retry or stale restore. |
| RETURN-01 | Repeated returns, screen locking, runtime/service death and HAL reconnect preserve coherent state and recovery. |
| BOOT-01 | Separately agreed cold boot/manual root restoration preserves current-PIN data access and real first-unlock biometric policy. |
| RELEASE-01 | Required surfaces, ownership, version admission, isolation limits, measured normal use and controlled-fault evidence pass user/maintainer acceptance. |

Samsung remains the authority for genuine security decisions and physical
credential/key operations. Guest UI must consume the real result for the real
current subject. A copied registry, default user zero, cached success, fabricated
CE-unlocked status or independently initialized security backend cannot provide
that authority. Ordinary screen locking is distinct from stopping a user and
evicting credential-encrypted keys.

## What the experimental code does

[`PinCheckCompletion`](../switcher/experimental/samsung-security/src/com/appleexploit/oneos/security/transport/PinCheckCompletion.java)
is a package-private, per-request scheduling cell. It joins an actual progress
event and its original delivery Runnable with that same request's original
canonical `VerifyCredentialResponse`. It returns the original Runnable at most
once after both observations and a matching final response. It never runs or
posts the Runnable, dismisses keyguard, opens an endpoint or grants unlock.

`checkCredential` progress and a final result are separate observations. An early
callback is not final success or proof of completed native work. Conversely,
`verifyCredential` has no equivalent progress callback to manufacture from its
final response. This cell does not turn that path into a two-callback protocol.

A match without progress creates no ticket. Error, timed nonmatch, null response,
exception and uncertain transport release no success ticket. Cancellation,
staleness and closure prevent later release. The first progress occurrence wins;
conflicting final objects prevent release. Response errors must not be treated
as proof of a wrong PIN: framework results can lose the distinction between a
credential mismatch and backend failure.

A returned ticket can become stale before execution. The future caller must own
the genuine source, request, receiver, subject and queued work, recheck them at
delivery, and preserve required original policy and cleanup. The cell cannot
recall a ticket it already returned. Its constructor arguments bind identity
inside the cell; they do not authenticate their producer.

The [experimental README](../switcher/experimental/samsung-security/README.md)
describes the runnable JVM checks. Their response and environment are explicitly
authored models. They do not execute Android/OEM classes, establish runtime
placement or test a real callback, credential, fingerprint or unlock operation.
No model may be packaged as a framework replacement.

## Where integration belongs

This spans the app, privileged launch control, framework and native owners.
An app-only PIN check or UI switch cannot supply the missing backend lifetime.

The current [root command producer](../app-android/core/root/src/main/kotlin/com/fahadali/oneos/core/root/RootScript.kt)
selects `LAUNCH` with no stdin control channel. The
[root script](../app-android/app/src/full/assets/root/oneos_root.sh)
detaches the switch shell and reports a text launch marker. The
[switch script](../switcher/assets/oneos_switch.sh) and
[guest startup](../switcher/assets/guest_start.sh) then create further process
and namespace transitions. Waiting for the app's shell or reading its marker
does not retain the guest SystemServer, its descendants or a security callback.

The smallest proposed integration boundary is a separate, retained privileged
root-session operation. Its actual native controller must retain its real
preparation child, control channel and private filesystem handles before
acknowledging acquisition. The existing launch path stays unchanged in this PR.
Host SystemServer's UID does not grant root or mount capabilities to a Java
`ProcessBuilder` child. A spawning call that throws also cannot be assumed to
have created no child. An unavailable root provider cannot be replaced by a
wrapper returning a supplied ready flag.

That native occurrence must connect to the initialized host's private controller
and the actual guest SystemServer fork/Runnable occurrence. A self pidfd, PID,
UID, service name, descriptor or executable hash alone is not authority. Real
Binder references require Binder delivery; passing a file descriptor does not
transfer a Binder object. Control-channel EOF is neither readiness nor proof
that accepted work or descendants have drained.

## Current validation and first device test

Offline component testing is underway. The retained host PIN endpoint has
compiled in a separate preparation build and stays closed. Its lifecycle tests
cover retirement during construction. The guest caller frame has compiled
and passed modeled checks for preserving the original call and observing its
Binder identity before the identity clear. Connecting both to the live ColorOS
keypad remains open.

The tree preparation controller cross-compiles with the exact donor manifest
embedded. Host fixtures exercise mount and descriptor checks, teardown, and the
cleanup status reported over the control channel. The full executable link is
still held at the stage admission boundary. Admission must establish the exact
mounted contents and keep the backing generation stable throughout the lease.
The donor image still needs a real filesystem build and metadata readback.

The first on-device work has three separate gates.

1. Verify preparation and Stop against the real stage. Confirm the retained
   child, mounts and descriptors, exercise a refused preparation, and confirm
   the controller preserves uncertainty when cleanup cannot be proven.
2. Verify the enforcing guest startup and connect its actual SystemServer
   occurrence to the retained Samsung service. This needs a positive guest
   Binder context claim, authenticated delivery, and a lease that keeps the
   physical Samsung user stable through verification and cleanup. A stock
   user-switch observer alone cannot establish that lease because the current
   user has already changed before the callback.
3. Exercise an existing PIN from the genuine ColorOS keypad. Check a correct
   PIN, wrong PIN, cancellation and applicable lockout behavior, then verify
   One UI can still unlock and use its encrypted data after return.

All 18 device acceptance cases remain pending. Reciprocal PIN changes,
fingerprint enrollment and authentication, authentication-bound app keys, and
cold-boot recovery still require their own evidence even after the first PIN
test passes.

## Remaining implementation boundaries

- Retain genuine initialized Samsung registry, LockSettings, policy and related
  owners, with current subject, loader, thread and lifetime checks. Capture is
  distinct from permission to invoke or export them.
- Implement the real privileged root-session and guest bootstrap handoff,
  including failure after partial creation, cancellation and uncertain cleanup.
  Retain owners while completion is unknown; do not report a false successful
  close or retry a potentially completed destructive action.
- Separate guest app-data/native writers and private device/socket views while
  preserving genuine host data, CE/key ownership, shared metadata and native
  consumers. A private mount namespace alone does not isolate property areas,
  Binder service contexts or physical hardware.
- Deliver a scoped real backend reference to the guest before its security
  consumers initialize. Preserve callback identity, per-call retirement,
  policy accounting and original failures through that delivery.
- Define full guest stop and return acknowledgements before releasing retained
  host resources. Direct-child exit and a local preparation close are not proof
  that zygote descendants, native work or queued callbacks are drained.

Optional OPPO-only consumers may be removed or adapted where a source review
shows that preserves the required behavior. This is not permission to remove
required policy, encryption, strong-authentication or recovery checks, force
successful status, or disable physical Samsung security owners. Keeping genuine
host property values and narrowly owned guest additions is a candidate, not
proof that the complete guest boots.

Retained-host and other hosting/compositor arrangements remain alternatives;
this draft selects no complete runtime architecture. Source-compatible byte
artifacts and JVM tests are useful preparation, but do not establish loaded
code identity, platform bootability or end-to-end security.

## Existing protections remain

The current [screen-lock switch rule](../app-android/core/model/src/main/kotlin/com/fahadali/oneos/core/model/ScreenLock.kt),
its existing Advanced behavior, and the
[patch/guard requirements](app/patch-catalog.md) remain unchanged. In particular,
this proposal does not remove Gatekeeper/Weaver protections or biometric cleanup
guards and does not make switching with a lock safe. No new launch mode, enabled
feature, modified framework bundle or native executable is included here.
