# Genuine ColorOS frontend security contracts

This is offline source and ABI evidence from the supplied donor, not a working
OneOS image. No OEM code, service, credential operation or phone action ran.
`inventory/coloros-frontend.json` pins the actual archive/index hashes, exact
descriptors and fourteen decompiled input hashes with line anchors. Reproduce the
bounded declaration/source check with `python -B tools/audit_coloros_frontend.py`.
Original code remains in the parent's ignored `firmware/donor/`.

## Concrete candidate boundary

**Observed source fact:** genuine ColorOS PIN/password controllers already reach
standard framework credential and fingerprint service interfaces. Preserve their
views, keyboard widgets, input/falsing/haptic work, transition and dismissal
controllers; bind the verifier and its policy/state dependencies to one genuine
Samsung authority. The concrete credential call is:

`ILockSettings.checkCredential(LockscreenCredential, int userId,
ICheckCredentialProgressCallback) -> VerifyCredentialResponse`.

**Inference, not selected architecture:** an exact framework-service adaptation
can retain the original ColorOS keypad without reimplementing its frontend.
This may be supplied by transplanted genuine Samsung services or a retained
Samsung authority. Neither is proved to start or operate here. A raw service-name
replacement or callback returning success alone is insufficient. The frontend
also consumes authoritative credential type, lockout, strong-auth, enrollment,
trust and user state and triggers ColorOS-specific RPMB work.

## Actual credential caller graph

The following method edges are observed in pinned decompiled donor inputs;
selected raw-DEX confirmation is a separate evidence tier, described below.

| Edge | Required contract |
| --- | --- |
| `OplusKeyguardPinViewController.getEnteredCredential()` | `LockscreenCredential.createPinOrNone(EditInputWidget.getEntry())`; genuine entered PIN, not a credential hash or guessed type. |
| `OplusKeyguardPasswordViewController.getEnteredCredential()` | `LockscreenCredential.createPasswordOrNone(...)`; preserves password type. |
| `OplusKeyguardAbsKeyInputViewController.verifyPasswordAndUnlock()` | Blocks duplicate dismiss, disables entry and calls original checker with entered credential. |
| `OplusLockPatternChecker.checkPassword(...)` | Cancels only cancellable prior task, derives user from real update monitor; credentials shorter than four fail locally and zeroize. Study-space mode substitutes its OEM user. |
| `checkCredential(...) -> oplusCheckCredential(...)` | Original asynchronous worker calls `LockPatternUtils.getLockSettings().checkCredential(credential,user,wrappedProgressCallback)`. Remote exception produces no fabricated match. |
| `WrappedCallback -> OplusOnCheckCallback.onEarlyMatched()` | Genuine progress invokes `onPasswordChecked(true,true,false,user,0)` immediately. UI success is driven by this authenticated progress edge, before final asynchronous reply handling. |
| `onPostExecute -> onChecked(response,timeout,duplicate)` | Consumes `isMatched()`, `hasTimeout()`, `getTimeout():Duration`, `isCredAlreadyTried()`; final match schedules RPMB work, rather than synthesizing another success callback. |
| `OplusKeyguardAbsKeyInputViewController.onPasswordChecked(...)` | Reports original unlock attempt, checks current/OEM alternative user relationships, dismisses through `KeyguardSecurityCallback`; failure reads authoritative lockout end time and failed attempts. |
| `KeyguardSecurityContainerController.reportUnlockAttempt(...)` | Calls real `reportSuccessfulPasswordAttempt`, or failed-attempt/device-policy wipe/lockout reporting. These are additional policy effects, not a substitute for verifier cryptographic work. |
| `KeyguardViewMediator` | Later calls `LockPatternUtils.userPresent(selectedUser)`; hiding the view alone does not supply this service state. |

The original checker has `cannotCancel` and `canceled` state, credential copies
and explicit zeroization. A transport must retain exact request, callback, user
and owner identity through the final result and original task cancellation. A
late callback must not unlock a replacement user/session. Static source alone
does not prove an owner/drain implementation safe.

**Observed source fact:** failed checks can try ColorOS multi-system user 0 or
its alternate user when configured and when strong-auth/fingerprint lockout,
secure-lock-device and other OEM gates allow it. The original controller also
accepts certain study-space/family transitions. **Inference:** numeric user 0
and a shared system UID do not authenticate a Samsung user, user serial,
credential SID/protector, selected-user generation or profile. These OEM fallback
branches require genuine mapped identities; an initial proof must explicitly
reject unmapped users rather than allowing fallback to a different authority.

## Reply and policy data beyond a Boolean

**Observed declaration facts:** both captured framework archives declare the
same `checkCredential` method descriptor and the same response constructor
`(int, java.time.Duration, byte[], long)`. Both expose match/timeout/duplicate,
Gatekeeper HAT and password-handle accessors. This revision has no public
`getResponseCode()` accessor. Samsung additionally declares `mSecret`, secret
access/destroy methods and `SKIP` state. Same declared constructors do not prove
parcel or response-code semantic compatibility.

**Observed raw-DEX facts, now checked separately:** the seven selected framework
class queries on each side verify the credential service transport, credential
parcel, response parcel/predicates and progress callback. Four additional donor
SystemUI queries confirm six actual bodies at the worker/checker/early-success/
final-response/RPMB/mode-selection edges. Every proof records physical DEX,
logical header, body hash and before/after input hashes; raw methods stay ignored.

| Contract | Samsung | ColorOS | Consequence |
| --- | --- | --- | --- |
| `ILockSettings` descriptor | `com.android.internal.widget.ILockSettings` | Same | Descriptor equality does not permit forwarding. |
| `checkCredential` transaction | **54**, flags 32 | **10**, flags 32 | Exact transaction translation or correct typed proxy is required. |
| Samsung transaction 10 | `setCarrierLockEnabled(int)` | Guest means `checkCredential` | A direct guest-to-host Binder endpoint is concretely incompatible. The Samsung stub's trailing-data check should reject the mismatched credential parcel before the carrier method; this is not a safe forwarding design. |
| Credential parcel | type int, credential byte array, invalid-chars Boolean, unified-profile Boolean | Same sequence, confirmed readers/writers | Selected wire fields align; constructor/type semantics and real user identity remain separate obligations. |
| Response parcel | code int, timeout seconds long, timeout nanos int, HAT byte array, password handle long | Same sequence, confirmed readers/writers | Samsung secret is not serialized by this method. Preserve exact fields; never mint HAT or handles. |
| Match / duplicate | code 0 / code 3 | Same | Actual predicate branches agree for these two values; no blanket claim about every Samsung-specific status. |
| Progress callback | descriptor `com.android.internal.widget.ICheckCredentialProgressCallback`, transaction 1, no args, one-way | Same | Only this callback ABI aligns. Its authority, generation, authenticated timing and lifetime still need proof. |

Proxy at PC36 dispatches the credential transaction on each side. Samsung stub
switch PC13 resolves case54 to PC1066 and calls checkCredential at PC1090; case10
resolves to PC2058 and calls setCarrierLockEnabled at PC2066. ColorOS case10
resolves to PC1062 and calls checkCredential at PC1085. These PCs are code units
in the specific pinned bodies, not file offsets. The authored audit asserts the
transaction numbers, selected parcel reference sequences and Samsung case10
target. Register/control flow was also inspected directly; static equality is
not hardware acceptance.

Required data/authority includes:

- Original credential type/bytes and exact chosen user; genuine authenticated
  progress callback and final matched/error/retry/too-short/duplicate meaning.
- Genuine timeout duration and lockout end time in the correct elapsed-time
  domain; current failure count and device-policy reporting/wipe authority.
- Samsung's real HAT/protector/SID and associated encrypted-storage/key-unlock
  effects. A UI has no ability to mint a hardware-accepted HAT from a Boolean.
- Shared current strong-auth flags and live tracker registration, including
  reboot/lockdown/lockout/secure-lock-device requirements; no clearing those
  flags merely to make fingerprints available.
- Real trust/device-locked state, enrollment/sensor identity and biometric
  strength, plus SIM, enterprise/remote-lock and selected-user restrictions.

**Observed source and selected raw-body fact:** original
`OplusKeyguardBouncerExImpl.getSecurityMode` delegates to
`OplusKeyguardSecurityModel`. Its device mode reads
`LockPatternUtils.getActivePasswordQuality(currentUser)`; numeric quality
131072/196608 chooses PINFour/PINSix/general PIN from the OEM numeric-length
helper; quality 0 yields None. Thus guest-empty policy metadata can bypass the
very presentation route being preserved even if the verification method is
adapted correctly. SIM/lock-dead/study/children/secure-lock-device paths remain
additional policy authorities.

**Observed source fact:** PIN auto-confirm metadata has OEM dependencies beyond
`ILockSettings.getPinLength`: `KeyguardPasswordUtils.getNumericPwdLength()` uses
`OplusLockPatternUtils.getLockPasswordMinLength(...)` in one property-selected
path, otherwise `Settings.System.PASSWORD_LENGTH`; another helper reads
`lockscreen.pin_password_length` through `getLong`. Its successful result is
cached for 30 seconds. These values must remain presentation metadata from the
same authority; a mismatched guest setting must not select the wrong keypad or
be accepted as credential evidence. `triggerChannelOpen()` also reaches
`OplusSyntheticPasswordManager`, an additional original OEM dependency.

## ColorOS RPMB is a concrete extra consumer

**Observed source fact:** final successful response creates `RpmbCheckTask` with
credential duplicate, requested quality, user and full response. Its `run()`
extracts `getGatekeeperHAT()` and calls `RpmbChecker.checkPassword(HAT,false,...)`.
That constructs `CE_CMD_PMS_VERIFY` with verify type 8 and calls
`RpmbChannel.processCmdV2`. `postRpmbCheckTask` runs only for user 0, caches the
credential/task and submits to the OEM offload executor. Reboot retry and old
password/retrieval/save-SP operations also exist in this component family.

**Missing evidence:** a Samsung-produced HAT accepted by this ColorOS/OEM channel,
matching RPMB trustlet state, and the consequences of its failure/retry are not
established. Passing a Samsung HAT to an unrelated ColorOS trustlet or returning
fake RPMB success is not a supported integration. This seam needs an explicit
owner/capability policy backed by the security-stack design. Leaving original
credential changes/preservation guards in place is mandatory until a reviewed
replacement owns all effects; this report does not authorize disabling RPMB or
credential guards.

## Genuine fingerprint presentation caller graph

**Observed source facts:** `KeyguardUpdateMonitor.startListeningForFingerprint`
derives selected user and creates `FingerprintAuthenticateOptions(userId)`. It
chooses `detectFingerprint` or genuine `FingerprintManager.authenticate(null,
CancellationSignal,SafeFingerprintAuthCallback,null,options)`. A fresh monitor
session ID binds the callback; stale-session authentication/acquired/help/error
callbacks are rejected. Detect is distinct from authenticate and must not
become unlock.

Authentication success uses `AuthenticationResult.getUserId()` and
`isStrongBiometric()`. `handleFingerprintAuthenticated` checks selected user
against returned user, with an OEM user-switch exception, and rejects disabled
fingerprints. `onFingerprintAuthenticated` updates original per-user state,
calls `TrustManager.unlockedByBiometricForUser` only when bouncer-skip policy
allows, emits original authenticated callbacks and asynchronously calls
`LockPatternUtils.reportSuccessfulBiometricUnlock(strong,user)`. Secure-lock-device
flag 4096 delegates unlock to its dedicated service. Original strong-auth and
lockout policy still governs bouncer skip.

Permanent fingerprint error 9 calls `requireStrongAuth(8,user)`; errors 7/9
update original lockout state. The monitor checks authenticators-registered,
sensor/enrollment, policy, SIM and StrongAuth. `stopListeningForFingerprint`
cancels its exact cancellation signal, starts a cancel watchdog and transitions
to stopping; a subsequent start request records restart-pending rather than
starting a second operation. A cancellation return is not evidence of remote
scheduler/HAL drain. Preserve operation request ID/token/callback and complete
drain across runtime switches.

**Observed declaration facts:** both frameworks declare standard
`IFingerprintService.authenticate`/`detectFingerprint`/`cancelAuthentication`
and result-receiver methods with the selected descriptors in the JSON. Sensor
properties, templates and real authenticator IDs are part of the service state.
**Cross-stream observed raw-DEX result:** the fingerprint stream reports matching
selected top-level sender transactions: authenticate 5, detect 6, cancel-auth 9,
cancel-detect 10 (synchronous flags 0); receiver acquired 2, success 3, detect 4,
failure 5, error 6 (one-way flags 1). This is narrower than complete wire parity;
the fingerprint worker also traced the nested parcel: common name/string,
biometricId/int, deviceId/long and groupId/int are followed by a Samsung duplicated
image count/int versus ColorOS extension finger-flags/int. Equal width/order
therefore conceals a different meaning. Do not blindly relay this nested type.
Option flag meanings remain its explicit review obligation. Consult
`docs/fingerprint.md` for its exact receipts.

**Missing evidence:** full nested parcel compatibility, host Samsung
sensor/session import, UDFPS/side-FPS geometry/touch/display/vendor extensions and
ColorOS overlay behavior on this actual Samsung sensor. The parent donor's
`OplusFingerprintManager` additionally obtains the `fingerprint` Binder's
`getExtension()` as `IOplusFingerprintManager`; a standard Binder descriptor is
not evidence that this OEM extension exists or works on Samsung.

## Supplied source versus OneOS/current installation

The framework pins are Samsung `8095a9ae...ce71fe` and ColorOS
`d5c6b7fd...55bcd2` (full values in JSON), obtained from the existing immutable
archive declaration indexes and rehashed actual input archives this run.
The original SystemUI Java is an existing decompiler view of donor code;
decompiler control flow is not treated as raw-byte proof.

OneOS 0.4.55 commit `2a5f41043b4a69399cae058bad213cdef7408e88` includes
`guest_no_gatekeeper.py`, `guest_no_weaver.py` and
`guest_no_biometric_cleanup.py`. Their contents are patch-producer evidence;
comments about previous experiments are not independently verified runtime
evidence. Effective installed-image code, data, SELinux, Binder namespace and
service startup remain unverified. The current investigation preserves guards
and makes no phone changes.

## Next meaningful proof

1. Extend the established credential raw-body proof to the full selected policy
   interface (strong-auth/tracker, lockout, user-present, reporting, metadata),
   plus the callback receiver and exact endpoint/caller permission boundary.
   Fingerprint's request/result/cancel/option parcel comparison belongs to
   the fingerprint stream. Same descriptor is only an input to these proofs.
2. Complete the remaining actual ColorOS UI call closure at
   RPMB/channel consumers and OEM fingerprint overlay/touch callbacks;
   map each operation to its genuine Samsung authority or an explicit unresolved
   capability. Do not silently substitute guest policy.
3. Select one startup/authority design only after credential, fingerprint,
   encryption, trust and SELinux workers demonstrate its real owners/dependencies.
   Define one request-bound selected-user generation and authenticated service
   endpoint; handle death/recovery/unknown replies by retaining lock state.
4. The smallest later separately authorized runtime proof must run the genuine
   ColorOS keypad/controller and original callback path against Samsung's real
   verifier, prove host policy/CE/key effects and correct failure/timeout/stale
   handling, then show return and reboot preserve host authentication. Fingerprint
   adds real template/sensor/HAT/strength and cancellation/drain evidence. A
   screenshot, model, compilation or dismissed view satisfies none of these.

No exact working integration or device acceptance is claimed.
