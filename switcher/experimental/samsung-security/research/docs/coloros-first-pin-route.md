# First ordinary ColorOS PIN route

The ordinary PIN source route needs **`checkCredential` with genuine progress**.
The tested private `verifyPin`/original `verifyCredential(...,0)` operation is a
different entry and does not yet bind the native keypad. This is a bounded
source/API proposal; no implementation, activation or authentication ran.

The actual acquired staged framework is `5cb16a37...`, original classes6 DEX
`47f3b688...`. Its existing audited full normalization supplies the selected
framework method bodies. The accepted installed profile contains three acquired
JARs and **no acquired staged/current SystemUI APK**. The keypad and dismissal
evidence below remains supplied donor SystemUI `0e253fad...`; existing inventories
and Root's confirmation identify no newer acquisition. Some UI edges are exact
raw bodies, others explicitly pinned decompiler views. None proves loaded code
or the phone's active PIN widget, selected user, policy or current configuration.
The unselected Proxy33/RPMB-removal leaves are not installed-image evidence.

## Concrete source chain

| Edge | Observed behavior and tier |
| --- | --- |
| General/fixed PIN controllers → inherited `verifyPasswordAndUnlock()` | Donor decompiler: typed `createPinOrNone` input; refuse duplicate dismissal, disable entry, call `OplusLockPatternChecker.checkPassword`. General and fixed-length variants share this boundary; actual configured variant is unknown. |
| `checkPassword` → `checkCredential` → `oplusCheckCredential` | Donor decompiler: derive user from the real update monitor; below four input units fail locally/zeroize; study-space substitutes its own user. Capture credential/user/callback into an AsyncTask and duplicate credential for cleanup. `executeOnExecutor` occurs before the returned task is stored by its caller. |
| Task `doInBackground` → `utils.getLockSettings().checkCredential(...)` | Donor raw body `153e9dfb...`, PC43: genuine typed credential, captured user, wrapped progress callback (PC32 receives the interface obtained at29). It is not `verifyCredential`, and no verification-flags argument exists. Timeout response becomes `getTimeout().toMillis()` for original UI handling; RemoteException is logged, not changed into match. |
| Actual staged `LockPatternUtils.getLockSettings` → Proxy | Cache the `lock_settings` interface; cache miss calls ServiceManager at PC7/asInterface11. Staged Proxy writes credential21, user24, callback27; code10 at32, native flags32 at34, transact36, readException40, response CREATOR45. This is original acquired5cb, not candidate Proxy33's retargeted code54. |
| AIDL progress → main Handler → higher-level early match | Staged callback Proxy sends code1/oneway1, no payload, no reply. Donor `WrappedCallback.onCredentialVerified` posts its original Handler Runnable; that calls `LockPatternUtils.CheckCredentialProgressCallback.onEarlyMatched`, then clears its callback. Its higher callback calls the checker's `onEarlyMatched`. These are different method levels. |
| Checker early callback → UI/policy | Donor raw `ee509b91...`: set `cannotCancel`, mark password-match state, set target user and call `onPasswordChecked(true,true,false,user,0)` at PC95. It also reaches OPPO timing/lock-dead work. |
| Final task response → `onChecked` | Donor raw `6dbeb89e...`/`e93665b5...`: retain null, matched, duplicate and timeout semantics. A matched final response constructs/posts optional RPMB work and then returns without emitting a second ordinary successful UI callback. Failure can enter gated alternate-user fallback or `onPasswordChecked(false,...)`; credentials/task state are cleaned under original conditions. |

Thus replacing the checker with the tested synchronous verifier while discarding
progress can leave genuine native UI without its normal success event. Calling
`onEarlyMatched` yourself when a final verify response matches fabricates a
different protocol/timing and is not an equivalent adapter.

## Exact Samsung target and timing

Samsung's public-final `LockSettingsService.checkCredential(LockscreenCredential,
int,ICheckCredentialProgressCallback)` is the matching operation. Raw body
`a17ca685...` checks read permission at0, clears Binder identity3 and passes the
original callback plus flags0 into `doVerifyCredential` at18/42. It retains the
enterprise stream branch, identity restoration and parcel-credential zeroization.
The tested `verifyCredential` has a different permission/envelope; invoking that
entry or bypassing it for `doVerifyCredential` does not preserve `checkCredential`.
Samsung framework's check transaction is54, rather than staged guest10.

Genuine progress is also **not final/native completion**. Samsung SPM body
`caf41fd9...` calls the supplied progress callback at834; unwrap follows861 and
an unwrap-failure path assigns `OTHER_ERROR` at875. Original donor ColorOS SPM
body `a172e322...` likewise invokes progress865 before unwrap899. Preserve the
source callback rather than inventing a stronger final-success interpretation.
Samsung's later LSS `onCredentialVerified` at668 still owns real key/storage/user,
StrongAuth and deferred work. A callback or Java return does not drain that work.
The continuously retained same Samsung family remains its owner; presentation
change alone does not require a global LSS drain.

## Policy and final dismissal are still real consumers

Donor `onPasswordChecked` reports the attempt, handles failure/lockout and only
admits matching-current/explicit OEM alternative users for dismissal. Its safe-mode
branch is different. `KeyguardSecurityContainerController` then checks current
security mode, trust/biometric state, remaining SIM mode, secure-lock-device
additional factor and admin secondary lockscreen before `finish`. The mediator
checks selected/OEM user correspondence again before keyguard-done; UI/animation
completion and later user-present work are separate. These final edges are pinned
decompiler evidence here, not a new complete raw/UI or live policy proof.

Actual staged framework policy methods show why the new PIN call alone is not a
drop-in replacement:

* Successful/failed attempt reporting reaches DevicePolicyManager and, under the
  original feature flag, TrustManager. Failed-count reads are DPM-backed. Preserve
  genuine policy/wipe/accounting authority and original conditions; do not return
  guessed counts or drop guest reporting merely because host verification ran.
* Lockout end time uses PropertyInvalidatedCache and the elapsed-time supplier.
  Its actual query `LockPatternUtils$2.apply` calls
  `ILockSettings.getLockoutEndTime():ParcelDuration` then extracts Duration.
  Preserve authoritative values, invalidation and clock semantics. The original
  response `getTimeout` can clamp under its feature flag; do not substitute an
  invented milliseconds/zero response.
* `requireStrongAuth` and later `userPresent` still reach LockSettings. The donor
  mediator's user-present task includes original profile/broadcast conditions.
  Secure-lock-device/secondary-admin state cannot be defaulted to dismissed.

Original final-match handling additionally retains plaintext entry strings,
credential duplicates and response HAT through `RpmbCheckTask`. Its support on
Samsung is not established. Root permits removing unsupported optional OPPO
dependencies; existing **unselected** RPMB-input leaf1120a5e4 removes exact entry
and task producers while preserving early match and mandatory failure/policy
logic. It is not an installed cut or host-HAT acceptance. Select a complete
supported removal/capability cut before retaining this optional consumer; a
no-op post alone still leaves the extra credential retention. The donor verifier
also updates its OPPO preference timeout state; that is not Samsung StrongAuth.

## Smallest proposed endpoint extension

Keep tested private code1 unchanged. Add one separate check operation, for example
private code2 with the existing v1 sensitive/synchronous profile:

1. Owner: cache/invoke the exact original **public checkCredential** once on the
   same worker/caller, using its internally bound physical subject and the genuine
   canonical host progress interface. Preserve original result/errors/envelope;
   do not run main-only binding checks on the worker or require old UserState.state
   to remain unchanged through legitimate unlock.
2. Endpoint/client: request version1, original typed PIN and strong progress Binder,
   no wire user/serial/verification flags; original nullable response and native
   exception handling. Use original canonical callback marshalling. Forward only
   progress actually emitted by Samsung; never derive it from final response.
   Original endpoint/PIN/Parcel cleanup and closed-by-default restrictions remain.
3. Consumer: replace the exact worker check invocation with the source-owned
   prepared check client while preserving the original task, wrapped callback,
   final-result/timeout path and required reporting/dismissal gates. The captured
   guest user must agree with the real issued physical-subject mapping **before**
   dispatch; no universal user0, PID/UID/name/descriptor or supplied Boolean grant.
   Unmapped study/multi-user fallback must refuse, not try another host subject.

This operation needs a real per-request callback/consumer owner, adopted before
original invocation, tying the actual guest task/handler/current subject to the
same retained authority. Cancellation/replacement/source loss must stop stale
UI delivery while preserving admitted original effects and uncertain results.
One-way return, AsyncTask cancellation and Handler.post are not consumer-drain
acknowledgments; already queued guest work needs its real owner. The private
transport's Java-stack counts do not cover those callbacks or native delivery.
Ordinary stock calls sharing the same live authority remain legitimate.

There is an additional **consumer activation gate**, not solved by compatible
callback bytes: forwarding genuine progress straight into the unchanged donor
WrappedCallback can run the UI-success body before the later unwrap/final result
fails. The smallest proposed completion cut must retain both facts for the same
real request: (a) genuine host-emitted progress was observed and (b) its final
original response actually matched, with the original subject/remaining-factor
and dismissal-policy gates still valid. Only then may the higher UI-success body
run once. Buffer the genuine event or gate its existing higher-level consumer
and final-response branch; a final-only synthetic callback is not allowed.
Final error/null, cancellation, stale subject/task or lost source cannot release
buffered success. No coherent native-completion or global-drain claim follows
even when both facts exist. This changes the current donor's early UI behavior
and therefore needs Root's explicit source/consumer selection before activation.

The selected worker/final consumer also conflates unavailable with wrong PIN:
RemoteException becomes null, then final `onChecked` sends
`onPasswordChecked(false,true,...)`, reaching failed-attempt policy reporting.
A new private-transport failure can follow real host effects. Its per-request
consumer must preserve exceptional/null uncertainty separately from a genuine
negative response; it must not fabricate success, authoritative bad-PIN accounting,
timeout or retry from that uncertainty. The exact original catch/final/report
branch therefore needs a selected consumer adaptation as well. The private
client's preserved error/null alone does not fix that downstream conflation.
Even a genuine final `OTHER_ERROR` can follow unwrap failure; `!isMatched()` alone
does not prove a wrong PIN. Preserve exact result meaning and real host policy
accounting rather than inventing a response status or reason from that predicate.

The matching canonical host `ICheckCredentialProgressCallback.Stub.asInterface`
can consume the original genuine guest callback Binder through its source-owned
Proxy path; no additional host forwarding Stub is needed merely for ABI
translation. That source-compatible placement does not supply the guest task's
completion gate, source identity or lifetime owner. A same-name Java interface
from another loader is not assignable as the host interface; transport the actual
Binder and use the original host factory, rather than casting that Java object.

This is a bounded API/source proposal only. Real guest issuer/routing, current
SystemUI code identity, selected-user/serial ownership, callback delivery lifetime,
genuine DPM/Trust/StrongAuth/SLD policy and native key/CE acceptance remain open.
Only authored Python selection/hash checks over saved data ran. No shared
Java/ABI/source selection, patch, compiler, new raw-DEX reader/toolchain process,
test, OEM, Android/native, network or device action was performed by this audit.
