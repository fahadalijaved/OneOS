# Original ColorOS additional-factor and StrongAuth gating

**Observed source/body result:** this donor ColorOS SystemUI contains genuine
secure-lock-device second-factor presentation and an explicit finish guard.
It is incorrect to infer that its PIN success callback always finishes keyguard
or that an additional-factor frontend must be rewritten. It is equally incorrect
to treat a forwarded early credential callback as proof of complete Samsung
authentication under every represented host state. That universal forwarding
contract is **not established**.

No frontend files were changed. Their hashes are pinned in
`inventory/strong-auth-gating.json`. This separate bounded audit selected 37
actual methods in 20 class/side queries and reused six already-pinned credential
bodies, with full-container DEX041 semantics. All raw bodies remain ignored.
Reproduce/check with `python -B tools/audit_strong_auth_gating.py`; use
`--collect` only to refresh selected raw receipts. No OEM code or phone action ran.

## Original UI support is concrete

The supplied original ColorOS methods form the following source-backed path.

| Original contract | Actual behavior |
| --- | --- |
| `KeyguardSecurityModel` constructor | Collects `SecureLockDeviceInteractor.getRequiresStrongBiometricAuthForSecureLockDevice()` and `isAuthenticatedButPendingDismissal()` using the original JavaAdapter. Its consumer stores two model fields. |
| `KeyguardSecurityModel.getSecurityMode(user)` | Selects `SecureLockDeviceBiometricAuth` when either original factor-required or authenticated/pending field is true, before the ordinary OEM PIN/password mode path. |
| `KeyguardSecurityViewFlipperController.getSecurityView(...)` | Contains actual ordinal-11 selection for `keyguard_secure_lock_device_biometric_auth_view`; the OEM flipper has first opportunity, followed by original fallback inflation. |
| `KeyguardInputViewController.Factory.create(...)` | Recognizes the original `KeyguardSecureLockDeviceBiometricAuthView` and constructs its original controller with the original viewmodel factory and interactor. |
| `KeyguardSecureLockDeviceBiometricAuthViewController.onInit()` | Creates the original Compose content and attachment/lifecycle owners. This is original presentation code, not a substitute unlock overlay. |
| `KeyguardSecurityContainerController$3.dismiss(int,mode)` | Delegates to its four-argument dismiss method, which calls the original `showNextSecurityScreenOrFinish`. The original keypad's callback does not directly call final `finish`. |
| `showNextSecurityScreenOrFinish(...)` | Even after computing a candidate finish from password/biometric/trust/etc, reads secure-lock enabled and authenticated/pending state. If enabled and not pending, returns false before original `finish`. The administrator secondary-lockscreen requirement is still evaluated on the allowed path. |

**Actual raw positions:** in the pinned ColorOS finish method, enabled read is
PC391, pending read PC413, blocked return PC434, final callback `finish(user)`
PC602. The enabled-false branch skips the pending read. These are code-unit PCs,
not file offsets. The audit asserts the key edges and actual blocked return;
the full branch/register context was inspected in the raw body.

**Limit:** declaration/inflation support is not proof these actual owners are
started, subscribed, correctly selected or operating in the installed OneOS
image. This audit does not manufacture a view/controller or execute inflation.

## The two policy channels that must share one authority

**Observed source and raw-body facts:** the enabled state is a separate channel
from `ILockSettings.checkCredential` and from per-user StrongAuth flags.

1. `SecureLockDeviceRepositoryImpl$isSecureLockDeviceEnabled$1.invokeSuspend`
   emits false first, then, if `AuthenticationPolicyManager` is non-null,
   registers the original status listener using its background executor. It
   awaits close for unregister cleanup. A null manager supplies no true host
   state through this path.
2. `SecureLockDeviceInteractor` creates `isSecureLockDeviceEnabled` using
   `stateIn(..., WhileSubscribed, false)`. Its primary/factor-required flows are
   eagerly shared with initial false; `isAuthenticatedButPendingDismissal` is
   separately shared with initial false. These are ordinary original flow seeds,
   not an authenticated assertion that Samsung secure-lock-device is disabled.
3. `AuthenticationPolicyManager.registerSecureLockDeviceStatusListener` binds
   its listener registration to **Context.getUser()**. That must be reconciled
   with the actual selected Samsung user, not merely the same integer in a
   guest runtime. Both captured services register the listener and send actual
   initial enabled/availability notifications. The manager delivers enabled
   notifications through the supplied `Executor.execute`.
4. The second channel is the real per-user StrongAuth tracker registered by
   `BiometricSettingsRepositoryImpl`. Its `AuthenticationFlags` represents
   primary-for-secure-device bit **2048**, strong-biometric-for-secure-device
   bit **4096**, and primary-after-lockout bit **8**, among all other original
   policy flags. The selected original map emits factor-required only when
   `!primaryRequired && strongBiometricRequired && !primaryAfterLockout`.

**Inference:** returning from listener registration is not proof that executor,
callbackFlow, `stateIn`, JavaAdapter and selected model consumers have all applied
the current authority state. Initial false, missing manager, stopped subscription,
service death or a callback for an obsolete selected user cannot grant finish.
No cross-Binder/coroutine ordering or atomic snapshot between these independent
channels has been demonstrated. This is an integration readiness obligation,
not a claim that the native OEM image has a demonstrated vulnerability.

## What the genuine factor path considers complete

**Observed raw-body facts:** original `SecureLockDeviceInteractor` resets local
factor state when biometric authentication is requested. Its
`onBiometricAuthenticatedStateUpdated(PromptAuthState)` marks strong biometric
complete only for `isAuthenticated && !needsUserConfirmation`; when confirmation
is needed it shows the original confirmation action. The original confirmation
coroutine first requires an actually authenticated PromptAuthState and uses
`asExplicitlyConfirmed()`. It does not convert unauthenticated input into success.

`isAuthenticatedButPendingDismissal` is the original combination of local strong
biometric completion OR local fully-unlocked/ready state. Thus its name is not
an independent Samsung service attestation. It is meaningful only when original
face/fingerprint request, selected-user, strength, confirmation and lifecycle
inputs remain bound to the same genuine authority.

If the biometric UI is hidden before ready, original
`onBiometricAuthUiHidden()` requests primary authentication again with bit 2048.
`onReadyToDismissBiometricAuth` sets the original ready state. After the owned
gone transition, `onGoneTransitionFinished()` calls real
`AuthenticationPolicyManager.disableSecureLockDevice(DisableSecureLockDeviceParams)`
and resets local state. That manager's no-user overload again uses its
Context user. The actual Samsung service checks its enabled-by-user identity,
computes authenticationComplete from its recorded strong-biometric user, and
can record a **pending disable request** when that authentication is incomplete
(PC104-108); it calls real LockSettingsInternal with the actual state. Calling
disable, or its return alone, therefore is not proof of completed two-factor
authentication. The service must remain the authority for effects; the UI's
flags are not permission to clear policy.

**Missing evidence:** end-to-end original second-factor activation, user/sensor
identity, confirmation/ready/gone callbacks, service permissions, full Samsung
disable/unlock effects and recovery are not assembled or executed. It is not
enough to feed a new Boolean into `isAuthenticatedButPendingDismissal`, invoke
`onGoneTransitionFinished` directly or treat an already displayed fingerprint
icon as evidence of a completed factor.

## Actual primary callback timing

The credential stream's actual source bodies distinguish three events that
must not be collapsed into one success.

| Event | Samsung actual source order | Meaning here |
| --- | --- | --- |
| Protector progress notification | `SyntheticPasswordManager.unlockLskfBasedProtector` invokes `ICheckCredentialProgressCallback.onCredentialVerified()` at PC834. | Original partial progress; notification has no factor-complete or selected-generation payload. |
| Remaining cryptographic work | Same method unwraps the SP blob at PC861; null produces OTHER_ERROR and returns at PC897. A non-null SP reaches SP `verifyChallenge` at PC898, whose response can fail. | Notification alone cannot certify all later cryptographic work. |
| Credential policy handling | `LockSettingsService.doVerifyCredential` checks final matched response and calls `onCredentialVerified(SP,metrics,user)` at PC668. | This is a distinct service method from the callback above. |
| Secure-device branch | The latter method checks real SecureLockDeviceService enabled state, performs genuine primary-auth keystore/CE/escrow/SP effects, queues StrongAuth message 11 and returns at PC95 awaiting additional-factor completion. | Primary success is not full StrongAuth unlock or permission for final presentation dismissal. |
| Ordinary branch | Performs ordinary original unlock effects and normal StrongAuth work. | Preserve real authority effects; no UI Boolean replacement. |

**Qualification:** original ColorOS SPM similarly emits its progress notification
at PC865 before blob unwrap PC899 and final SP challenge PC948. This is **not** a
proven cross-OEM callback-timing difference, newly established OEM vulnerability,
or evidence that the callback was unauthenticated. Both source implementations
use partial-progress semantics. The asynchronous transport may deliver a
notification later; neither delivery-before-final nor delivery-after-final is
guaranteed by inspecting emission order alone.

The already audited original ColorOS checker immediately turns that real
notification into `onPasswordChecked(true,...)`, target-user preparation and
unlock broadcast. It requests dismissal through the original callback, which
then encounters the finish guard above. Its final matched reply instead schedules
the original RPMB/HAT path. Consequently both original final-result semantics
and the separately owned policy/factor gates are necessary. Simply forwarding
Samsung progress and assuming the guest's initial false policy state is real
does not establish the requested security contract.

## Concrete admission seam and unsupported states

**Source-supported candidate seam, unimplemented:** retain original ColorOS
controllers/viewmodels and bind their real service inputs to the same genuine
Samsung credential, AuthenticationPolicy and StrongAuth authority. At request
admission and callback release, retain one selected-user/request generation and
actual live observation ownership. Require an initialized authoritative state
receipt and applied original consumers, not only a default flow value or
successful listener registration. Preserve the exact original finish guard,
admin/secondary/SIM/policy checks and real second-factor UI. This boundary lies
in service/input ownership and request admission; it is not a rewritten keypad.

| Represented state | Required behavior / remaining proof |
| --- | --- |
| Normal credential state, secure-device authoritatively disabled | Original callback may only carry the genuine request's primary success; original final response, authority effects and all other original finish checks still apply. Direct early forwarding has not been proved safe for later final failure/death. |
| Secure-device primary required | A genuine primary match may advance to original factor presentation. It must not finish keyguard while the additional factor remains required. Same-authority enabled state must be applied before releasing a success that can request dismissal. |
| Secure-device awaiting strong biometric | Use original factor-required mode and a genuine Samsung authorized strong biometric operation. Repeating a successful PIN does not authorize clearing factor policy. |
| Strong biometric result requires user confirmation | Preserve original confirmation requirement; authenticated-but-unconfirmed state does not open this guard. |
| Real factor completed and confirmed, original ready transition pending | Preserve original pending/ready/gone ordering and actual Samsung service completion. Local UI pending alone does not certify Samsung policy or key effects. |
| Lockout, lockdown, reboot, SIM, profile/enterprise/remote or administrator secondary lock | Preserve original host restrictions and original matching presentation. No clear of StrongAuth or implicit bypass; unmapped policy remains unsupported. |
| Missing/stale/wrong-authority enabled listener/tracker; foreign user or replaced operation; final error after progress; authority death/recovery | Explicitly refuse admission/success release or retain locked/recovery state. Do not classify unknown as disabled or replay a success into the new generation. |

A possible transport design can retain an **already received genuine** progress
notification until the exact request's real final primary result and policy
observation state are established; this is a timing/ownership design to review,
not implemented behavior or a license to fabricate progress from code 0. It must
allow the original secure-device factor stage to appear without incorrectly
waiting for full unlock first. If original callback ordering/owner semantics
cannot be preserved, that request/state must be explicitly unsupported until
another genuine source-supported integration exists.

**Explicit denial:** the present investigation cannot safely forward early
callbacks for every represented host state. The unsupported contract is
*cross-authority or uninitialized policy/factor state combined with success
delivery*, not absence of original ColorOS factor UI. No code was added to clear
StrongAuth, synthesize success, rewrite presentation or bypass the original
guard. `userPresent` must remain a consequence of a legitimately permitted
original finish; using its real StrongAuth-clear effect to make finish seem
permitted would reverse the security dependency.

## Next bounded proof

Prove actual same-authority initial/status/StrongAuth callback application and
selected-user generation before any original success delivery; then exercise
the original secure-device primary -> strong-factor -> optional-confirmation ->
ready -> gone -> genuine Samsung policy completion path, including final
failure after progress, callback delay, cancellation, death and stale user.
This requires a concrete separately approved runtime proposal. Static bodies,
an authored model, a successful build or a dismissed view are not that proof.
