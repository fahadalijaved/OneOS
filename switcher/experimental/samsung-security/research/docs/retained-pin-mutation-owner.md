# Retained PIN mutation worker admission

The retained operation model reproduced the missing worker admission check. On
the current saved SDK classes, the original-main Binding check refused the
incoming worker. After an authored current-user change, the same check refused
on main while an already-open verify owner still called the authored verify
backend once with its earlier bound user0 and flags0. The source-owned
admission required for a mutation entry remains unresolved.

Samsung supplies the exact public-final instance method
`LockSettingsService.setLockCredential(LockscreenCredential, LockscreenCredential, int):boolean`
with access flags17 and descriptor
`(Lcom/android/internal/widget/LockscreenCredential;Lcom/android/internal/widget/LockscreenCredential;I)Z`.
The saved public body `a3ad1816…` delegates with ignore-notify false. The
underlying body `296f05de…` checks actual caller permissions before its own
identity clear, including the saved credential's `isNone()Z` check for the
initial-lock permission. The adapter would have to invoke it synchronously on
the same incoming worker and Binder identity, with the genuine retained
physical user and the original borrowed NEW and SAVED objects. See the
[original call audit](retained-pin-mutation-call.md).

The current SDK `PreparedRetainedPinBinding.checkStillBound()` begins with
`Metadata.checkControl()`. In the actual emitted Metadata class, the
`Thread.currentThread()` comparison at PC7 branches a foreign worker to the
false value at PC38 and the refusal at PC42. Registry and Family checks begin at
PC49 and PC56. Their comparison paths also require the original main thread.
Moving the call to main would leave the incoming Binder stack. Sampling main
before opening and comparing the saved integer on the worker still leaves a
window for physical user changes.

The probe reuses the exact SDK program subset from `6c67ec73…` and the authored
framework34, service49 and control1 classes from the retained operation model
`34c817b4…`. It captures and checks the Binding on the fixture main, tries the
same check on a foreign worker, and checks that no backend call occurred. It
then opens only the existing verify adapter through the authored control and
uses the existing fixture's `change("current")` to invalidate the bound user.
The actual main Binding rejects that graph. The existing verify adapter,
whose contract requires the caller to supply a separate worker admission and
custody decision, retains its local OPEN state and still dispatches one verify
call for the earlier bound user. This models an invalidated graph rather than a
completed Android user switch. The credential-shaped fixture object holds
synthetic type flags only. The outcome records zero mutation invocations.

The isolated JDK source-launch exited zero and was reaped. Its input class maps
matched before and after, including all 56 SDK definitions. The initial
preflight failed before Java because Windows denied strict realpath resolution
for the saved fixture directory. That attempt is preserved. The successful
launch used receipt-pinned copies under the owned run directory after checking
path components for symlinks and reparse points. See
`out/retained-pin-mutation-owner/r-f4ca3114/receipt.json` (`8695ac06…`) and
`out/retained-pin-mutation-owner/preflight-winerror5/failure.json`.

The saved Samsung credential ABI has public `isPin()Z` and `isNone()Z`, both
flags1. The current compiler-only projection class `1bc7248b…` exposes
`isPin()Z` and omits `isNone()Z`. A direct Java call to the omitted method
cannot bind against that projection. A separately reviewed compiler-only ABI
addition or an exact cached method lookup could cover that narrow declaration
gap. Either approach still needs the source-owned worker admission.

The missing contract is an actual source owner that couples the incoming worker
to current physical user identity and credential custody through the call,
with a cutoff that prevents new calls on source drift. The closed verify
owner's ingress counter provides local frame accounting. It cannot supply that
mutation admission. The future call must preserve the original boolean or
Throwable, retain any after-entry uncertainty, and leave reconciliation with
the real authority owner. The guest post-set metadata operation stays a
separate prerequisite. This evidence covers an authored JVM admission gap.
