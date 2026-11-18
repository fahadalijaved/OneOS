# ColorOS SystemUI PIN task retarget

The captured OneOS 0.4.57 stage (code 74, `s-ultra-8850`, `x9u-in-sultra`) selects `coloros17-findx9u-in`. The raw image reread matched the installed `image_raw` table and captured `system.raw.id` at 14,669,168,640 bytes and SHA-256 `92c7cd8485dd6ef80d1f5c734ea13a8744510c15b77a18471eb11078df84ddb6`. The captured stage's 49 hash rows match the installed script and set manifests. The installed finish path moves unlisted staged files out of the flat stage before publishing the marker. The selected set contains neither `SystemUI_patched.apk` nor `Fold8SystemUI.apk`. The ColorOS Fold8 replacement requires a different profile and image, and the Pixel replacement addresses `SystemUIGoogle.apk`. These facts identify the image member under the captured selection, with live mounts and loaded code outside this check. [Selection inventory](../inventory/guest-pin-systemui-retarget-cut.json)

Reading `system/system_ext/priv-app/SystemUI/SystemUI.apk` directly from that image produced 116,521,421 bytes and SHA-256 `0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77`, exactly matching the cached APK used for the donor route. The checker, task constructor, worker, higher callback, `WrappedCallback` and component factory are therefore the same APK bodies. The staged `framework_patched.jar` separately matches the donor's decoded `AsyncTask.executeOnExecutor` and `cancel` instructions, code headers and exception ranges. Their raw instruction bytes differ. `executeOnExecutor` sets RUNNING before `onPreExecute`, then stores the arguments before calling the supplied executor. A throw can occur after these effects or after work was enqueued. [Image readback](../out/guest-pin-systemui-retarget-cut/IMAGE-MEMBER-READBACK.json) · [Code ownership](../out/guest-pin-systemui-retarget-cut/RAW-CODE-OWNERSHIP.json)

The proposed disabled edit replaces the three-unit invoke at `classes3.dex` code-unit PC 20 in `OplusLockPatternChecker.oplusCheckCredential`. A private static method on the checker would receive the same `v0, v8, v9` task, executor and arguments and call the original method once. The checker slot starts null, so the disabled branch forwards directly. If a later source owner binds that slot, the helper would adopt the actual task before the original invoke, using its captured checker, higher callback, controller, view, monitor and user. The outer checker stores `mCheckCredentialTask` only after this invoke returns. The new helper would own a narrow catch around the invoke, retire an adopted request on the exact throwing task and rethrow the original throwable. Any uncertain admitted work must remain owned across that failure. The original callsite has zero try items, and the worker's existing `RemoteException` try remains separate. [Edit map](../out/guest-pin-systemui-retarget-cut/EDIT-MAP.json)

The staged `LoadedApk` loader and factory methods match the donor. The actual manifest factory and its SystemUI base inherit the framework `instantiateClassLoader`, which returns the supplied loader. The proposed helpers belong in that same app loader. Both existing helpers are package-private, so the proposal uses reviewed copies relocated into `com.oplus.keyguard.security` and requires a fresh compile and DEX closure check. The existing helper compile applies to its original package. No new method index, reference-pool fit or APK build has been verified for this edit. [Loader readback](../out/guest-pin-systemui-retarget-cut/METHOD-SUPPLEMENT.json) · [Original helper](guest-pin-check-request.md)

The APK declares shared-user name `android.uid.systemui`. The staged package manager registers UID 1000 for `android.uid.system` and resolves shared users by name. This evidence leaves the actual guest SystemUI process UID and Binder caller admission open. The private client checks both its own process UID and the incoming Binder UID against 1000, and the endpoint separately checks its real caller. Actual source and physical-subject admission, worker dispatch, policy and guarded delivery still need their own binding. This cut is a static edit map with no DEX emission or execution. [UID readback](../out/guest-pin-systemui-retarget-cut/UID-SOURCE-READBACK.json) · [Private client](../compat/android/com/appleexploit/oneos/security/transport/PreparedRetainedPinEndpointClient.java)

## Checker-package lifecycle stage

The [source producer](../tools/compose_guest_pin_systemui_lifecycle.py) places
the exact lifecycle request and completion classes in
`com.oplus.keyguard.security`, the donor checker's package. Its inverse restores
both original package declarations. The controller lives in
`com.oplus.keyguard.security.view`, so a later call needs a checker-owned entry
with a callable signature. The helper and Slot can keep their package-private
access. [Exact owner and access readback](../out/guest-pin-systemui-lifecycle-access/FINDINGS.md)

Pause uses the original entry before the superclass call at PC 0. Submit uses
the accepted branch at PC 5 and keeps the dismissing return at PC 4. The held
instruction frames fit one-reference static calls at those cuts. The actual
checker-owned entry still needs to be bound and verified in the original code.
When its optional Slot is absent, the original continuation runs directly.
When a Slot is present, the retirement result leaves that continuation intact.
[Raw control flow](../out/guest-pin-systemui-lifecycle-cfg/REVIEW.md) · [Disabled path contract](../out/guest-pin-systemui-disabled-cut/REPORT.md)

SDK 37 compiled both relocated sources. D8 emitted six nonpublic definitions
with the original member access, task name and wrapper name. The captured donor
APK has no collisions for those names across its nine DEX files and 73,080
class definitions. The donor DEX has 622 unused method IDs before any helper
or bridge references are added. The pool projection covers the held helpers.
The final checker-owned entry needs its own access and capacity check.
[SDK and DEX build](../out/guest-pin-systemui-lifecycle-relocated-build/r-c89ebd7b/receipt.json) · [Loader and collision readback](../out/guest-pin-systemui-lifecycle-loader/REPORT.md) · [Pool projection](../out/guest-pin-systemui-lifecycle-pools/REVIEW.md)

The 40 inert lifecycle and progress cases passed after exact package relocation.
The test uses authored fixtures. Actual SystemUI call sites, donor APK assembly
and the effective runtime loader remain separate from that result.
[Relocated fixture receipt](../out/guest-pin-systemui-lifecycle-relocated-tests/r-ee0909ef/receipt.json)

## Emitted disabled lifecycle cut

The [PC producer](../tools/prepare_guest_pin_lifecycle_retarget.py) emits a
standalone ordinary DEX039 from the pinned donor `classes3.dex` and six verified
helper definitions. It adds one call before the original pause superclass call
and one call on the active submit branch. The original dismissing return remains
at PC 4. The submit branch still targets PC 5, which now holds the added call.
An independent readback recovered both original instruction sequences after
removing the calls and reversing reference reindexing.

The added private controller method first calls the existing final checker
getter. An absent checker returns before invoking any checker method. Using the
already initialized controller for the static call preserves the original
checker initializer's placement. The checker forwarder returns on its null
Slot before reading the original held view and monitor. A present Slot would
receive the exact checker, controller, view and monitor. Its return value is
discarded. The private Slot has one direct read, zero direct writes and no
field method handles across all 46,076 emitted code items. This artifact leaves
the Slot unset.

The emitted leaf preserves 87,348 normalized original records under the inverse,
adds six definitions, two methods and one field, and retains 563 free method
IDs. Independent raw checks verified the declared members, table union, map,
and both new bodies. The initial writer recomputed 234 outgoing-register words.
The producer restored those words from the original and held helper before
running the raw checks on the final leaf. The final 10,193,996-byte DEX has SHA-256
`f0da78461c1dea56f40022bbdf29f6d80d67d9da4bcbbef346bc689a308021b0`.
[Static readback](../out/guest-pin-lifecycle-retarget/r-cbf2b3d2/receipt.json)

Editable PIN's OK and auto-confirm paths and the fixed-length submit path
reach the selected original submit method. The stock PIN fallback uses a
different controller. A Cancel action can defer or skip pause, and the
container can reselect the controller before pause dispatch. Any activated
request still needs exact current-source and queued-delivery checks through
those boundaries. Study and SIM controllers can reach the same pause method.
Admission must distinguish those sources from an ordinary PIN occurrence.

This standalone leaf is unselected. Effective SystemUI loader resolution,
request adoption, actual Samsung response delivery, and Android behavior
remain open. No APK was assembled or installed from this result.

## Final callback forwarding cut

The [typed bridge source](../compat/guest-pin-final-callback/com/oplus/keyguard/security/GuestPinFinalCallbackBridge.java)
attempts the terminal receipt only when the original task supplies a request.
It forwards the exact original callback, nullable response, timeout and
duplicate bit once. Observer failures leave the original return or thrown
object in charge. The bridge owns neither credential object nor cleanup.
The SDK 37 and D8 build kept all 19 predecessor class inputs byte equal and
added one bridge definition. The donor callback and response compiler
declarations stayed external. The JVM model passed 409 checks, including
60 new checks for exact forwarding, throw identity and observer failures.
[SDK build](../out/guest-pin-final-callback-build/r-2fc9e372/receipt.json)
· [JVM model](../out/guest-pin-final-forward-model/r-76a034b0/receipt.json)

The call-site plan passes the actual task `v6` and the original four operands
to a private instance forwarder at PC 61 of `onPostExecute`. The instruction
keeps three code units and needs five outgoing words. The new method reads
one task-owned request field and uses the literal interface call when the
field is null. The original cleanup still begins at PC 64 after normal return.
The request field has no writer in this artifact. Task adoption, worker
observations, authority and policy remain separate cuts.
[Original call-site readback](../out/guest-pin-worker-runnable-readback/REVIEW.md)

The first one-DEX merge stopped before publishing an output. Its string pool
would move a `const-string` at PC 69 of an unrelated window-decoration method
from index 65416 to 65538. That requires a wider instruction and changes the
method during reserialization. The split keeps the helper in a separate
DEX and places only the new references in the edited donor DEX. The pinned
donor's nine DEXes must be free of helper class names before preparing the
split. Package assembly and actual same-loader resolution remain open.
[Rejected merge receipt](../out/guest-pin-final-callback-retarget/r-7777bbc5/receipt.json)

The [split producer](../tools/prepare_guest_pin_final_callback_retarget.py)
emitted the edited `classes3.dex` and recorded the separately built helper as
the proposed `classes10.dex`. The [independent reader](../tools/check_guest_pin_final_callback_retarget.py)
checked the exact invocation, field, fallback branch and return to PC 64.
It verified all 46,020 original coded methods under symbolic reindexing,
including original try and debug data, and scanned 46,021 code items for the
new field. The scan found one read, zero writes and zero field handles. The
writer recovered 87,348 original normalized records under the inverse. Its
232 regenerated outgoing words were restored, with five outgoing words
retained at the changed call. The edited DEX adds zero class definitions and
two method IDs, including the external bridge reference. Two in-memory
negative checks were refused after recomputing DEX integrity. One changed a
forwarding register and the other changed an unrelated worker instruction.
[Split build and readback](../out/guest-pin-final-callback-retarget/r-a9085108/receipt.json)

## Worker return cuts

The [worker-return producer](../tools/prepare_guest_pin_worker_return_retarget.py)
starts from that exact split DEX. In the original worker, the two normal
returns at PCs 67 and 70 now branch to PC 77. The caught return at PC 76
branches to PC 81 after the original logger. Both appended blocks return
the exact value in `v1`. The catch retains its original `RemoteException`
range `[27,67)` and handler PC 68. The handler and logger use `v5` for the
same exception so that `v6` still holds the task. The original timeout write,
exception log, and protected Binder call remain in their original order.

The two private wrappers read the same optional request field as the final
callback. The [worker bridge](../compat/guest-pin-final-callback/com/oplus/keyguard/security/GuestPinWorkerReturnBridge.java)
records normal and caught returns separately when that field is populated.
Only a normal return can post an already-owned progress ticket. Observer or
post errors stay separate from the original return. The 21-definition helper
DEX preserves the 20 predecessor class inputs. The authored JVM model passed
460 checks, including 51 worker-return checks.
[Helper build](../out/guest-pin-final-callback-build/r-32a284d7/receipt.json)
· [Worker model](../out/guest-pin-worker-helper-model/r-8185e9c1/receipt.json)

The independent byte reader checked all 46,021 coded methods from the split
predecessor under symbolic reindexing. It found the intended worker edits and
the unchanged final callback cut, with three request-field reads, zero writes,
and zero field handles in 46,023 emitted code items. The inverse recovered
87,350 normalized predecessor records. The split helper remains separate and
the request field is unset. Three in-memory negative checks rejected a changed
try range, an incorrect logger register, and a misdirected normal return.
No APK assembly or Android execution occurred.
[Worker cut build and readback](../out/guest-pin-worker-return-retarget/r-80cbb577/receipt.json)

The next integration needs exact task adoption before the original executor
call and worker/receiver binding before the original credential dispatch.
Before enabling the worker post, the real progress edge must transfer sole
custody of the exact Runnable and refrain from stock posting it. The original
Handler samples the posting thread's WorkSource UID, which the Looper restores
for dispatch. A deferred post from the worker can change that attribution.
Resolve this on the actual selected path before enabling it. The standalone
lifecycle DEX and this split have overlapping helper names. A future package
must compose the lifecycle edits with a single helper cohort.

## Split archive preflight

Automated security review flagged the later credential-dispatch audit as a
possible cybersecurity risk. That audit and its planned edit stopped. The
archive preflight below uses the previously verified dormant worker-return
split as its only DEX input.

The [archive preflight](../tools/check_guest_pin_split_archive.py) rehashed
the 116,521,421-byte donor APK, inspected its nine stored and aligned root
DEX members, and checked definition ownership. Replacing `classes3.dex`
preserves its 6,737 definitions. The separate proposed `classes10.dex`
adds 21 without collisions, for 73,101 planned definitions. The receipt
also pins the expanded bytes of 8,440 donor pass-through members, including
the binary manifest and `resources.arsc`.
[Preflight receipt](../out/guest-pin-split-archive/r-3902f737/receipt.json)

The replacement is 6,716 bytes larger. All eight stored arm64 libraries
follow it and start on 16 KiB boundaries. An archive writer that shifts
all following entries together needs at least 9,668 additional bytes of
layout compensation. A future output must verify those boundaries, the
stored and aligned `resources.arsc`, the actual APK signature and loaded
DEX generation. The pass-through ledger covers expanded payloads, so
compression and other ZIP metadata need separate comparison. No archive
was assembled, signed or loaded.

The layout helper passed 32 in-memory checks for canonical DEX numbering,
duplicate and aliased names, local header equality, storage, alignment and
payload overlap. [Fixture receipt](../out/guest-pin-split-archive-model/r-7cbde04a/receipt.json)

## In-memory archive rehearsal

The SDK verifier cryptographically verified the exact donor APK under v2
for SDK 24–27 and v3 for SDK 28–37. Both reported the same one public
signer. The signature covers the original APK. The dormant split requires
its own valid signature and admission under the original package's
`android.uid.systemui` shared-user rules.
[Donor signature receipt](../out/guest-pin-donor-signature/r-946d4d85/receipt.json)

The [rehearsal runner](../tools/run_guest_pin_archive_rehearsal.py) uses the
preflight's exact donor and two DEX artifacts. It extends the replacement's
local alignment field by 9,668 zero bytes. Together with DEX growth, that
moves the original suffix exactly 16 KiB. It preserves the original central
extra, copies every other local record byte for byte, and appends the helper
as stored `classes10.dex`. The unsigned rehearsal excludes the original
APK Signing Block and its preceding padding.

The raw reader compares every original central record and only permits
the planned CRC, size and local offset updates. A separate expanded readback
checks all member CRCs, the exact DEX payloads, binary manifest and resource
table. It verifies stored DEX and resource table alignment at four bytes
and all eight stored arm64 libraries at 16 KiB. The runner saves only an
evidence receipt. Signing the changed content, package admission, loaded
DEX identity and device behavior remain unverified.

The final rehearsal produced 116,557,022 bytes in memory. It preserved all
8,448 untouched local records and checked all 8,449 original central records.
Both actual runs produced the same output hash. No archive or signing key
was written.
[Final rehearsal receipt](../out/guest-pin-archive-rehearsal/r-5ee4bd0e/receipt.json)

The synthetic ZIP suite passed 30 checks, including deterministic composition,
16 KiB native alignment, descriptor parsing, and refusal of malformed metadata
and payload drift. It used generated fixture bytes.
[Fixture receipt](../out/guest-pin-archive-rehearsal-model/r-4de9ec50/receipt.json)
