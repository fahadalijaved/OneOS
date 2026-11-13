# Stage 1: native ColorOS authority bindings and optional OEM removal

This report applies the latest direction: adapt genuine ColorOS to Samsung;
remove unsupported optional OPPO integrations and their UI/background consumers.
Required reciprocal PIN and fingerprint lifecycles, genuine policy, app/key/CE
behavior and safe return remain mandatory. No source or firmware has been patched,
no runnable candidate exists, and no phone/OEM code ran in this audit.

`inventory/construction-frontend.json` pins the selected bodies, callsites,
manifest dump and source patch plan. `tools/audit_frontend_binding.py --stage
report` rechecks hashes and reviewed original callsites. Earlier lockscreen,
Binder and StrongAuth receipts are reused, not replaced. Raw methods/manifests
stay in ignored firmware. The actual Settings input is 280,336,937 bytes,
SHA256 `33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b`;
its declaration-only listing contains 78,960 classes. These are input facts,
not completion or Android-acceptance counts.

## Native entrypoint and service-binding table

**Observed actual manifest/body facts:** these are genuine donor presentation
entrypoints. They need coherent Samsung-backed typed services, current user,
policy and result ownership; replacing their successful UI response is invalid.

| Surface | Original entry/dispatch | Actual authority contract |
| --- | --- | --- |
| Lockscreen PIN/password | Existing audited Oplus keypad controllers -> OplusLockPatternChecker worker | `ILockSettings.checkCredential(LockscreenCredential,int,ICheckCredentialProgressCallback):VerifyCredentialResponse`, full final result and real policy effects. Existing transaction 10/54 difference requires translation. |
| Screen-lock Settings | Manifest activity `com.oplus.settings.feature.password.OplusScreenLockSettings`; `getIntent()` selects its `ScreenLockSettingsFragment` | `launchChooseOrConfirmLock`, current user/profile/policy and real confirmation. Activity is exported with `oplus.permission.OPLUS_COMPONENT_SAFE`; permission declaration alone does not establish effective enforcement. |
| Native create/change screen | Manifest `com.android.settings.password.ChooseLockPassword`; its `getIntent` passes through `ChooseLockPasswordAdaptor.getIntentChoosePasswordFragment` | Original `com.oplus.settings.feature.password.ChooseLockPasswordFragment.startSaveAndFinish` -> original `LockSaveAndFinishWorker.start`. Keep genuine UI and worker/result owner. Manifest declares `com.oplus.permission.safe.PASSWORD`. Adaptor enabled/installed-runtime selection remains separate evidence. |
| Native confirmation | Manifest `ConfirmLockPassword` and `$InternalActivity`, actual `getIntent` -> `ConfirmLockPasswordAdaptor.getIntentConfirmLockPasswordFragment` | Original OPPO confirm fragment uses `LockPatternChecker.verifyCredential` or `verifyTiedProfileChallenge`, retaining effective user/profile and flags. Its final callback reads match/Duration and conditionally returns actual `gk_pw_handle`/`hw_auth_token`. Preserve internal-return and caller authorization checks. |
| Credential removal | `OplusScreenLockSettings$ScreenLockSettingsFragment.updateUnlockMethodAndFinish(IZZStringZ)` | Calls `setSeparateProfileChallengeEnabled` where reached; `LockscreenCredential.createNone` -> `LockPatternUtils.setLockCredential(NONE,confirmedCurrent,user)` at PC262. Then real lockscreen policy, preference/result/broadcast work. Do not replace this entire method with success or strip Samsung-required biometric/key effects. |
| Fingerprint management | Manifest `OplusFingerprintSettings`; `getIntent` selects original `$FingerprintSettingsFragment` | Original confirmation, challenge, list/readiness, rename and removal. Selected callbacks call `FingerprintManager.remove(Fingerprint,user,RemovalCallback)` PC18 and `rename(id,user,name)` PC73. Lists and real callbacks must come from Samsung; no guest-only enrollment set. |
| Native enrollment | `getEnrollingIntent` -> `FingerprintUtils.getEnrollClass`: optical/ultrasonic/side selects `NewFingerEnrollActivity`, otherwise `FingerEnrollActivity`; both declared non-exported | Original `FingerprintEnrollProcessor` receives real HAT/user/options/cancellation and calls genuine `FingerprintManager.enroll(...)` PC97. `cancelEnrollment` cancels its exact CancellationSignal; local cancel return does not establish HAL/scheduler drain. |
| Enrollment authorization | Original challenge callbacks -> `BiometricUtils.requestGatekeeperHat(Context,handle,user,challenge)` | Actual `verifyGatekeeperPasswordHandle(handle,challenge,user)` response/HAT; preserve real handle origin, challenge and revocation. Do not fabricate HATs or use an old request's handle. |
| Delete all | Original `FingprintSwitchHelper.deleteAllFingerprints(Context,user,Handler)` | Enumerates actual enrollments and removes them using real callbacks. Credential-removal UI also calls its original delete helper. Preserve unrelated prints on remove-one and real authentication-bound key invalidation. |

The original native confirmation fragment deliberately distinguishes effective
and requested users, current credentials, tied-profile verification and returned
capabilities. This table pins callsites, not a complete authorization proof for
every exported intent/profile branch. App BiometricPrompt/CryptoObject and CE/key
contracts remain as required by GOAL and the existing protocol/fingerprint/key
reports; native Settings success alone does not accept them.
The delete-all helper's selected body uses a no-user enrollment getter before
passing its explicit user to removals. Its Context/current-user and requested-user
identities therefore must agree through the Samsung adapter, or be adapted to an
explicit genuine user-bound query; an integer removal argument alone is not proof
that the enumerated templates belong to that user.

## Native create/change commit boundary

**Observed raw body:** `LockSaveAndFinishWorker.saveAndVerifyInBackground` checks
its chosen credential, invokes `ScreenLockResetController.isCheckSuccess`, uses
NONE only when the supplied current credential is null, then calls real
`LockPatternUtils.setLockCredential(new,current,user)` at PC60. The initial
helper return is not consumed as setter authorization. The actual Samsung setter
must enforce current-credential and policy rules.

After setter success, this worker calls `verifyCredential(new,user,1)` at PC118.
It checks actual match plus `containsGatekeeperPasswordHandle`, adds a genuine
handle to the result only when available, and carries the original credential
result for its intended caller. It separately posts OEM RPMB work to a background
executor and returns `Pair(setterSuccess,result)` independently of that work.
A later failed verification, missing handle, optional callback failure or lost
reply does **not** prove the already committed credential was rolled back.
Native enrollment must not be enabled with a fabricated handle to hide this gap.
The same body constructs a diagnostic containing the handle at PC181 and passes
it to `LogUtils.d(String,String,boolean)` PC188. Whether that helper emits under
the installed logging guard is unproved. Remove the capability-bearing diagnostic
at the candidate callsite; preserving native enrollment's legitimate result
Intent does not require preserving this log or the extra optional RPMB Intent.

**Additional exact consumer found in independent review:** between setter and
verification, PC101 calls `com.oplus.settings.utils.LockSettingsHelper.savePassword`.
Its three actual instructions retain the **same chosen LockscreenCredential** in
a static per-user SparseArray. `isPasswordRepeated` reads this cache and compares
credentials for a native repeated-password UI hint after querying real password
enabled/quality state. The analogous pattern helper uses its own cache. These
are not verifier, hardware, CE or enrollment authority. The password-cache field
has three direct references in this selected Settings archive (initialization,
save and repeated-check), with no explicit removal/zeroization reference.
Ownership of the shared credential object and its later zeroization still matter;
the mere cache reference does not prove its bytes stay valid indefinitely.
Remove or adapt this optional UI hint/cache with real authoritative policy and
bounded credential lifetime. Do not retain it as a second credential source or
assume dropping it can bypass Samsung's actual password-history restrictions.

**Cross-stream observed facts:** the guest framework setter invokes the common
credential setter, then its guest-only
`ILockSettings.setLockscreenPasswordType(user,newType,package)` post-commit hook.
The protocol worker traced this hook to a package/type/user/time attribution
string under `lockscreen.password.type` (dots), with a log-only consumer.
It is different from credential quality's `lockscreen.password_type` (underscore).
Settings and SystemUI exact-literal scans find **zero** direct references to the
dotted key. Remove that optional post-commit edge and its log consumer, rather
than importing the OPPO extension or treating its failure as credential rollback.
Do not remove independent policy work in the same server hook.

The same worker independently writes `lockscreen_password_modify_record`
through `PasswordAndBiometricSettingsRecorder`; this is a separate timestamp/
type presentation record. It is not Samsung verifier state or evidence of a
successful commit. Likewise the Settings SDK's similarly named
`setLockScreenPasswordType(quality,user)` sends `CE_SET_LOCK_SCREEN_PWD_TYPE`
through its RPMB channel; it is **not** the dotted-key helper above or the required
native PIN-length metadata. Do not conflate these three operations.

## Exact optional RPMB/RoR behavior and guards

**Observed original bodies; current installed activation is unknown:**

| Optional path | Reached guard and effect | Selected Samsung-profile treatment |
| --- | --- | --- |
| SystemUI HAT/input RPMB | Original successful checker schedules a real RpmbCheckTask; manager posts only user 0, caches the actual task/credential. No RoR feature check exists in this posting method. HAT verification can lead to a 64-byte challenge and `CE_CMD_PMS_MODIFY`. | Remove at allocation/admission, not by returning fake RPMB success or only no-oping the final post. Keep real verifier, credential cleanup and mandatory original guards. |
| Extra immutable input copy | PIN/password `getEnteredCredential` takes `EditInputWidget.getEntry().toString`, calls checker `setEntry`, then separately creates genuine LockscreenCredential. The task uses this **actual entered credential string**, not harmless metadata; the modify path UTF-8 copies it to its TEE info buffer. | Remove the extra checker entry copy and task retention together. Keep genuine credential creation. Fixed-PIN/pattern callers require the same paired removal audit before production. |
| RoR SP persistence | `OplusKeyguardVerifyManagerExImpl.init` unconditionally registers `OplusSyntheticPasswordManager.registerPasswordChangedCallback` PC60 after original monitor-registration work. Callback first clears local PIN-length cache, then requires `isSupportOplusRoR`; supported path encrypts supplied SP under AndroidKeyStore AES/GCM and sends save-SP to TEE, updating `persist.sys.oplus.save_sp` on success. | Remove the optional registration before SP can cross into UI. Merely forcing support=false still permits unnecessary secret delivery. Replace needed cache invalidation using authoritative commit notifications; no Samsung SP export is needed. |
| RoR capability | Real `isSupportOplusRoR` lazy is backed by `PackageManager.hasSystemFeature("oplus.hardware.resume_on_reboot")`; `isOplusRoR` also requires its cached saved-SP property equals `"1"`. | Mark unsupported on this profile and remove consumers. Presence of source code does not prove this feature is enabled. A literal search in extracted donor XML found no declaration; that absence is not an effective installed-feature proof. |
| Reboot recovery | `handleSystemRebooted` combines actual reboot properties/prefs, secure/provisioned/biometric state and zero lockout end time before choosing optional encrypted-SP or credential retrieval. Recovered SP decrypts then calls `OplusSyntheticPasswordManager.unlockCeStorageWithSyntheticPassword`; recovered entry is reverified through original LockPatternChecker. Failure retries are bounded by original counters. | Remove optional enqueue/registration/retry consumers together. Retain Samsung's genuine first-unlock, StrongAuth, current credential and recovery. Never turn warm CE storage or a removed recovery feature into `checkLockPatternSuccess`/userPresent. |
| Post-change Settings RPMB | `LockSaveAndFinishWorker.saveScreenLockInRpmb` is private void side work after real commit/verify. A real GK handle triggers an **additional fingerprint challenge**, HAT acquisition, `checkToken`, then `modifyPasswordInTeeByChallenge` with new credential bytes and TEE password-type update. This branch is separate from old-password-retrieval capability. | Skip before acquiring the extra challenge/HAT. Preserve required enrollment's independent genuine challenge and handle path; no fake TEE callback. |
| OPPO old-password retrieval | `SysFeatureUtils.isSupportPasswordRetrieve` caches feature `oplus.hardware.pwd_retrieve_settings`. Eleven direct callers include confirm UI onResume/updateUi/timer callbacks, old-password category controller, PIN/pattern save workers. Actual old-password storage sends old/new credential bytes to Settings ScreenLockResetController under this optional capability. | Set capability unavailable for the profile, remove paired exposed retrieval/reset UI and background writes. Samsung's genuine previous-credential recovery needs its own separately mapped route; old PINs still fail ordinary unlock. |

SystemUI `RpmbChannel.processCmdV2` calls actual
`CryptoEngManager.cryptoEngCommand`, retries once after an exception, then returns
null on repeated failure. The input task does not make a failed RPMB result into
keyguard verifier success: it schedules retry when its optional reboot callback
is present, or ends/continues its OEM work. A successful returned entry differing
from the entered string can trigger the modify path. None of this provides a
reason to import OPPO trustlets, expose Samsung SP or fabricate accepted tokens.

## Applied policy/readiness is mandatory

Retain the original extra-factor/confirmation/native finish flow from
`docs/strong-auth-gating.md`. Actual ColorOS finish reads secure-enabled PC391,
authenticated-pending PC413 and can return false PC434 before finish PC602.
Removing optional RoR does not authorize changing this gate or real Samsung
StrongAuth. AuthenticationPolicy enabled-listener and selected-user StrongAuth
must be applied from the same authority before original success can authorize
completion; initial false is not readiness.

**Cross-stream actual source fact:** guest LockPatternUtils credential-type query
can catch RemoteException and return NONE, and its lockout query can return
Duration.ZERO. These stock fail-soft values require **external admission and
recovery gating** before mode selection/requests. Do not let removal of an OPPO
provider silently present a secure Samsung user as swipe-only. Real credential
type/quality/PIN length and cache invalidation stay bound to Samsung.

## Concrete ColorOS-side patch plan and limits

The tool emits a hash-pinned method/callsite plan; no binary patch is claimed.

1. Keep original native keypad, Settings create/change/remove, confirmation,
   standard fingerprint and app/key service calls. Route the complete typed
   protocol and policy/resource/user inputs to the one selected authority.
2. In VerifyManager.init, remove only optional SP-callback registration PC60;
   retain original mandatory KeyguardUpdateMonitor registration. Replace its
   incidental cache invalidation with genuine committed-change notification.
   This is a cold-construction ingress cut. A previously registered callback,
   queued Binder/handler work or active job needs real disconnect/drain before
   replacement; a flag flip or source edit does not tear it down.
3. Elide optional reboot-recovery enqueue edges PC333/337 and their callback/
   retry ingress. Preserve original mandatory reboot/StrongAuth state and safe
   return; do not manufacture a verified-reboot preference or success call.
4. In original checker matched handling, skip RpmbCheckTask construction/posting
   before credential duplication. Preserve real result handling, input zeroize,
   task-state cleanup, selected-user checks and original finish gate. Remove
   PIN/password/fixed-PIN/pattern `setEntry` copies and corresponding owners.
   Exact selected-SystemUI xref finds 12 setter calls, including presentation and
   subdisplay variants; all are listed in raw evidence. No caller may retain an
   immutable copy just because the normal primary-screen pair was changed.
   Exact getter xref finds both `checkCredential$1.onChecked` PC84 and
   `checkMultiUserCredential$1.onChecked` PC54. Their matched task allocation and
   cleanup paths both belong in this removal; field references alone would not
   have closed the getter's consumer frontier.
5. Remove Settings' private `saveScreenLockInRpmb` ingress and optional retrieval
   capability/UI/background storage; preserve actual setter PC60, verification
   PC118, removal PC262, real GK-handle/HAT enrollment and mandatory metadata.
   Native screens must describe unavailable optional OPPO recovery honestly.
   Do not remove the whole background post blindly: its mixed lambda also runs
   old-password optional work and the separate modification record. Split those
   effects deliberately and release captured copied Intent/worker/credential
   owners. A no-op private leaf alone still leaves the original capture alive
   until its executor work actually returns.
   The actual `o0.run` (four instructions) and `LockSaveAndFinishWorker.d` bridge
   (two instructions) are pinned: the Runnable forwards its captured worker and
   Intent to the mixed lambda. This closes static forwarding; it does not prove
   runtime executor drain or zeroization of every captured credential owner.
6. Remove guest-only dotted-key attribution edge and log-only consumer through
   the coordinated protocol patch, preserving independent quality/PIN metadata.

**Required unresolved bindings:** enrollment currently invokes
`OplusFingerprintManager.getEnrollmentTotalTimes` PC10 before standard enroll
PC97. No genuine Samsung equivalent is proved. Adapt native progress to genuine
Samsung enrollment remaining/terminal callbacks or an honest indeterminate
display; never fabricate a total or terminal success. Fingerprint stream owns
real sensor type/property adaptation and live sensor/session admission.

Full late callback/retry removal, pattern/fixed-PIN entry copies, all alternate
exposed password/profile/recovery branches, native metadata refresh and lifecycle
drain still need coordinated closure before an executable producer. The exact
source decisions above are reviewable, but a bounded binary producer is **not
implemented** because these coupled obligations are not yet fully proved.
No harmless-looking no-op leaf is promoted as a complete security integration.

Read-only independent removal review identified the intermediate static
credential cache and mixed-lambda/cold-versus-live ownership qualifications above.
Those corrections are incorporated; review does not establish runtime drain or
authorize a payload/device action.

Stage 1 remains open on those bindings. Optional OPPO removal is authorized;
required bidirectional credential/fingerprint/app-key behavior is not optional.
