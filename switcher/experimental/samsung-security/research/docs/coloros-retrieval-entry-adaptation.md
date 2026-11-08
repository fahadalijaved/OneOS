# Unsupported OPPO old-mode entry: source proposal

**No patch approved or built.** Explicit UI cancellation should be `Activity.setResult(RESULT_CANCELED=0, null)` followed by the real finish request. That is a presentation outcome, not authentication success, credential rollback or acknowledgement that a job/native operation stopped. The exact native lifecycle makes a bare `finish(); return null` fragment stub insufficient.

This bounded continuation reuses the two complete fragment proofs from the frozen capability work and adds exact activity/adaptor/framework finish bodies. [The inventory](../inventory/coloros-retrieval-entry-adaptation.json) pins methods, body hashes, reader receipts, checked PCs, candidate cuts and remaining ownership requirements. [The audit tool](../tools/audit_coloros_retrieval_entry.py) regenerates derived metadata only. Frozen leaves, composer, shared APIs and phone are untouched; no OEM execution occurred.

## Exact ingress and two crucial distinctions

Both native fragments parse the actual Intent Boolean `is_verify_old_password`. Password `onCreateView` reads it at PC15 and stores `mIsVerifyOldPwd` at19; pattern reads it at53 and stores `mIsVerifyOldPassword` at57. The pattern fragment has already inflated its layout at10. A guard after the existing flag store is therefore too late to claim no view creation; a new reviewed entry guard is required for that claim.

Pattern restoration is earlier still: `onCreate(Bundle)` calls its superclass at0, reads `extra_chosen_pattern` at8, converts it at12 and stores `mChosenPattern` at16. **This key is not an old-recovery discriminator.** The sole explicit caller of its chosen-pattern writer is `$4.onPatternDetected` at89, after the old-mode-false branch and a true `mRemoteValidation` check. Its next accessor calls the genuine base `validateGuess`. Do not reject, erase or log this saved pattern by key presence; doing so breaks current remote credential validation. The separate `OLD_PWD_SCREEN_LOCK_PWD_INFO_LEFT_TRY_COUNT` is an OPPO presentation/TEE counter, not Samsung lockout state.

Both `onActivityResult(int requestCode,int resultCode,Intent data)` bodies have six registers: this=r2, request=r3, result=r4, data=r5. PC42 overwrites r3 with4; PC43 compares **result r4** with that constant. PC117/118 likewise tests result against `RESULT_OK=-1`. PC107 forwards the incoming result. Earlier shorthand describing a “request4” branch was incorrect. Never cancel every requestCode4 or every successful result. Rejection must identify the actual optional operation, caller/user and generation.

## Original result and finish behavior

The actual framework `Activity.setResult(int,Intent)` stores code at PC1 and data at3. `finish()` delegates to `finish(int)`; its ActivityClient submission is at54, with `mFinished` updated conditionally afterward. This provides the original typed result mechanism. It does not prove an activity has disappeared or pending work drained.

The concrete `ConfirmLockPassword.finish` and `ConfirmLockPattern.finish` first call their base finish, then their adaptor at7. Base finish reaches `SettingsActivity.finish` and its own adaptor, with optional fade/transition work. Enabled ScreenLockFeature finish methods reset the **process-wide AsyncTask default executor to SERIAL** at11 and invoke close animation at18. The inspected transition helpers read Intent animation information and request transitions. None of these selected finish bodies calls a credential setter or supplies an authentication result; none joins pending authentication jobs. Preserve their real lifecycle instead of assuming plain Activity semantics or bypassing cleanup.

The fragments' existing names are misleading cancellation candidates:

- `deleteOldPasswordOnVerifyFailed` sets custom result4 and queues background deletion. Never reuse it as unavailable/cancel.
- `goToResetPassword` starts a reset activity and sets `RESULT_OK=-1`.
- Successful-check/disappear paths also publish success and may carry credentials/handles.
- Back navigation can invoke vendor confirmation dialogs; it is not a minimal unconditional cancellation primitive.

## Exact candidate cut for root review

The best narrow **activity-side frontier** is the public `SettingsActivity.createUiFromIntent(Bundle,Intent)` invocation at `SettingsActivity.onCreate` PC48, restricted by actual activity type to these two confirmation activities. A typed wrapper could reject unsupported old mode before that factory creates its fragment, otherwise delegate the unchanged original call. This would avoid intentionally constructing a rejected fragment and then managing its null-view lifecycle.

However, original superclass initialization at PC36 precedes that factory. The actual restored-fragment ordering must be closed before this site can reject saved state safely. Parent/concrete onCreate continuations also remain: password runs adaptor hooks before and after its base, while pattern runs its creation hook afterward. The original common method contains an early `finish` at29, superclass call32 and return35, providing a lifecycle template, not blanket permission to skip those continuations or reuse the unrelated deep-link branch.

A **fragment-side alternative** would guard password `onCreateView` at entry, pattern `onCreate` after its required super call and before restoration, and pattern `onCreateView` before inflation. Rejected `View` results would be null; accepted current/remote flows stay original. This requires explicit lifecycle proof: later `onPause` calls timer/task cancellation and tracker/listener operations, and `onResume` expects initialized UI/tracker owners. A null-view return alone does not close that graph. Required superclass calls must remain.

For **late results**, both `onActivityResult` methods offer a point after original super PCs0–2 and before logging/legacy dispatch at3. Intercept only a purpose-bound unsupported old-operation completion, clear result data and request cancellation of that presentation. Do not manufacture stop acknowledgement, discard a genuine current/remote result or infer rollback of a credential change that already committed.

Cold admission must precede optional input, old-credential worker and callback creation. Existing `CountDownTimer.cancel`, ignored `AsyncTask.cancel` results and null listener writes do not prove producer/consumer drain. Non-cold requests require a separately owned disconnect/stop/join/reconciliation protocol.

Root must choose and review the exact boundary before a producer is written. Genuine Samsung prior-credential recovery remains separately mapped; ordinary previous PINs must fail. No current credential removal, fake authentication, deletion/reset helper or global UI/policy disablement is proposed.
