# Samsung biometric authority with original ColorOS presentation

**Source-supported API proposal; no adapter or runnable integration.** The
captured ColorOS image has genuine app-prompt, credential-fallback and animated
readiness callbacks that can represent the Samsung authority's actions. The
narrow candidate is a replacement for Samsung's UI-session transport, retaining
its original authentication state machine. A show-method replacement alone is
insufficient. Prompt wire/schema admission, callback identity, native credential
fallback and the UDFPS hardware/display owners remain construction gates.

[The inventory](../inventory/biometric-ui-authority.json) pins 69 selected methods
in 24 bounded queries, 36 source assertions, inherited proofs and open contracts.
PCs below are decimal DEX code-unit positions. Recheck saved receipts with
`python -B tools/audit_biometric_ui_authority.py`; `--collect` requests only the
named methods. No OEM code, Android service, hardware operation or phone action
was executed. Supplied donor behavior is distinct from installed OneOS behavior.

## Source session boundaries

Samsung `AuthSession.<init>` stores the real token, request ID, operation ID and
user at 62/64/68/72. It expects the actual `BiometricService$2`, obtains that
object's `SemBiometricSysUiReceiver$1`, calls `SemBiometricSysUiManager.openSession`
at 241, then records the request/session/receiver pair in the wrapper map.
The inherited bootstrap proof follows `openSession` to `bind` at 120 and
`Context.bindService` at 57 for the Samsung `BiometricsUIService` companion.

Therefore a candidate must provide an owned UI-session branch **before that
openSession**, with corresponding map publication, notifications, hide,
timeout/error and release paths. No fabricated companion connection or blanket
manager no-op is justified. The constructor's concrete callback check and
`BiometricService$2.asBinder()` returning null also rule out passing that object
as a usable ColorOS remote receiver.

`SemBiometricSysUiWrapper.showAuthenticationDialog(PromptInfo,int[],boolean,
boolean,int,long,String,long)` uses the source request map, actual credential
owner and work/Knox/prompt policy, calls manager show at 309 and starts its
3000ms watchdog at 320. Hide and error have actual selected bodies. Hardware
success has a separate route: `BiometricService.handleAuthenticationSucceeded`
gets the current request at 8, checks source sensor strength, retains a genuine
strong token in `mTokenEscrow` at 81, notifies the UI-session map at 163/193,
and evaluates original confirmation policy at 217. Those map notifications need
adaptation too; the wrapper has no declared `onBiometricAuthenticated` method.

## Proposed original UI binding

This is an interface proposal for later source patches, with no new runtime API
or service publication in this batch:

| Direction | Actual boundary and required binding |
| --- | --- |
| Samsung to ColorOS show | Source wrapper's effective prompt/request becomes the existing guest `StatusBarManagerService.showAuthenticationDialog(PromptInfo,IBiometricSysuiReceiver,int[],boolean,boolean,int,long,String,long)` route, then original `CommandQueue` and initialized `AuthController` |
| Samsung to ColorOS update | Original source session's authenticated/help/error/hide notifications reach the matching original controller/dialog; authenticate remains a hardware-originated event |
| ColorOS to Samsung action | A real guest canonical `IBiometricSysuiReceiver` carrier delegates to the issued actual source `BiometricService$2` methods under that session's authority |
| Disposal or failure | Original cancellation, client death, timeout, sensor cleanup and UI dismissal remain owned; a cancel return or hidden window is not native drain |

Guest statusbar show and hide call `enforceBiometricDialog` and
`enforceValidCallingUser` first. Retain those checks and actual caller admission;
do not clear identity to get past them. `runWithStatusBarIfPresent` is not a
GUI-ready acknowledgement. `CommandQueue.showAuthenticationDialog` sends the
original asynchronous message `0x270000`; this audit does not close the entire
statusbar action/Handler/Binder transport merely from those two endpoints.

`AuthController.showDialog` asserts the main thread, builds the original
`AuthContainerView` with its 15 real constructor dependencies, and stores the
effective prompt, second positional boolean as `mRequireConfirmation` at 79,
user/package at 81/83, operation ID at 89, request ID at 91 and sensor IDs at 93.
Its original foreground-owner, visible-user and assigned-display checks remain.
Replaying an unfiltered guest app request would lose Samsung's effective policy.
The two positional booleans require schema/semantic admission; identical method
shapes do not establish all arguments' meanings.

Every issued UI session must retain the source authority epoch, actual source
session/callback/token, request ID, real user/caller/package, native operation ID,
sensor/display owners and the corresponding guest receiver/dialog lifetime.
Guest `getCurrentReceiver(requestId)` checks the current dialog's request.
Authenticated/help/error controller methods themselves have no request argument:
a future bridge must check the issued receiver and authority epoch on the real
main-thread delivery, after queued work, before touching the current dialog.
An earlier check followed by an unchecked post can target a replacement dialog.
No new public generic UI consumer can substitute for these original owners.

## Readiness, confirmation and cancellation

`AuthController.Callback.onBiometricPromptShown` runs at 179, before actual
`AuthContainerView.show(WindowManager)` at 316. It cannot cancel Samsung's show
watchdog, claim a displayed overlay or start prepared sensors.

The actual readiness event is `AuthContainerView.onDialogAnimatedIn`: a pending
dismissal animates away; states 4/5 are ignored; no biometric view means no
biometric-ready callback. Otherwise it computes
`startFingerprint = !(isCoex && !requireConfirmation && isFingerprintPending)`,
gets the current request's receiver at 65 and calls `onDialogAnimatedIn` with
that exact boolean at 79. Samsung's vendor receiver event 1004 hardcodes true;
that event is not a lossless translation of the ColorOS callback.

The actual Samsung `$2.onDialogAnimatedIn` removes the watchdog at 14 and posts
its original Lambda3. Reject a stale issued callback **before invoking this
original method**: its watchdog removal precedes the posted current-request
check and could otherwise cancel a newer session's timeout. Lambda3 checks
`getAuthSessionIfCurrent(request)` at 16,
accepts states 2/8/4/6/5, preserves 4/6 or writes state 3, and invokes
`startAllPreparedSensors` at 78 only if the received boolean is true (71).
False explicitly delays fingerprint start. A candidate can therefore retain
ColorOS's real boolean by calling this actual typed source callback; it must not
forge the source UI event or advance the session itself.

| Original ColorOS owner | Real action, retained without synthetic success |
| --- | --- |
| `BiometricCallback.onButtonTryAgain` | Current receiver's `onTryAgainPressed` |
| `onStartDelayedFingerprintSensor` | Current receiver's `onStartFingerprintNow` |
| `onUseDeviceCredential` | `onDeviceCredentialPressed`, then original credential-view transition |
| `onUserCanceled` | Early user-cancel system event plus animated dismissal reason 3 |
| `onButtonNegative` | Animated dismissal reason 2 |
| `onAuthenticated` / `onAuthenticatedAndConfirmed` | Animated dismissal reason 4 / 1, following genuine authentication and actual confirmation policy |
| `onCredentialMatched(HAT,terminal)` | Stores real HAT; true dismisses with reason 7; false switches back to authentication and sends `onResumeAuthentication` |

`removeWindowIfAttached` sends the pending real reason/HAT to
`AuthController.onDismissed(request,reason,HAT)` at 39. Source `$2` routes
dismissal and each retry/start/pause/resume/credential action to its original
request-bound handler/state machine. UI success reasons are admissible only for
the actual issued session and genuine preceding match/confirmation; receipt of
a callback alone supplies no authentication authority.

Source `handleOnDismissed` checks the current request at 8. Reason 7 submits the
actual credential attestation to `KeyStoreAuthorization.addAuthToken` at 248;
reasons 1/4 use genuine escrow at 293/299. Original app callbacks occur separately
at 362/372. The token result is not an app-key acceptance proof. Preserve the
same pending native crypto operation and authentic token/challenge/user policy;
never replace a requested operation with zero, create a fresh CryptoObject or
produce success from UI dismissal. The native ColorOS credential view exists
(`addCredentialView` initializes it at 204), but upstream challenge/HAT binding
and the policy origin of its terminal boolean remain unclosed here. Extra-factor
and StrongAuth finish gates from the existing reports still apply.

## Keyguard, enrollment and native display owners

The inherited fingerprint reports retain real ColorOS keyguard and Settings
callback paths. These are separate from the app dialog above. Actual Samsung
authentication factory Lambda8 obtains the real helper at 361. BiometricPrompt
at 374 skips its per-sensor session setup to 442; `SemFpSysUiImpl.start` likewise
skips its own show for BiometricPrompt. Neither removes outer `AuthSession`'s
companion open. A genuine non-UDFPS legacy/keyguard branch can return no helper
under the original sensor/keyguard/privileged-flag conditions; forcing those
conditions is unsupported.

Enrollment selects UDFPS or side-sensor UI type 64, otherwise no helper.
Factory Lambda15 opens a session at 264 whenever that helper is nonnull; its
optical test changes `canIgnoreSysUiError`, not whether the session opens.
`startHalOperation` starts the helper at 4, enables real UDFPS TSP at 21, shows
`SensorOverlays` at 76 and invokes genuine enrollment at 121. `SensorOverlays`
sends `showUdfpsOverlay(requestId,sensorId,reason,callback)` to its actual
controller, and hides by sensor ID. Stop invokes the genuine cancellation signal.

Thus a presentation-only patch cannot erase the whole helper: UDFPS stop/error
also contain conditional native sysfs effects. Real sensor properties, geometry,
display, pointer events, TSP, illumination/HBM and actual source overlay/controller
registration must remain owned. Their cross-runtime ABI and native completion
are open. Optional vendor guide/styling extras may be removed only with their
callers, state and error behavior accounted for; no fake shown/error-ignored or
terminal enrollment-zero callback is permitted.

## Finite remaining gates

The exact `IAuthService`/AuthService ingress, effective `PromptInfo` fields and
parcel order/nested payloads, `IBiometricSysuiReceiver` wire, Samsung vendor
Bundles and complete statusbar transport are not closed by this card. A separate
prompt-wire audit is coordinated; no same-name cast or raw parcel relay is
approved. The source map's outbound notification lambda payloads also need exact
conversion admission before implementing authenticate/help/error delivery.
Guest original class/loader, initialized controller/dependencies,
callback caller authorization, source session publication/retirement, native
overlay admission and credential-fallback policy also remain required.

The next meaningful proof is a bounded source patch design closing those schemas
and session edges, followed by an unselected adapter with real-interface tests.
Later device acceptance must cover shown/failed-to-show, delayed fingerprint,
try-again, negative/back/caller cancellation, replacement/late callbacks,
confirmation and extra-factor fallback, enrollment cancellation/progress, and
successful plus rejected use of the same protected native app operation. This
source proposal establishes none of those runtime outcomes.
