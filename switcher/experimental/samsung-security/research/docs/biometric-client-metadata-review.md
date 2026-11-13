# Independent biometric client-metadata proposal review

The reviewed card's actual Context/argument lineage and fresh-prompt lost-cancel
counterexample are supported by the selected source. Accept this as a bounded
source proposal, with the implementation conditions below. Root has not approved
its private protocol/API; no helper, codec, retarget, runtime caller identity or
biometric/crypto acceptance is established by this review.

Reviewed inputs are the exact frozen report c399dc2c…, inventory d43dfd78… and
auditor0fc021f4…. Eighteen existing method proofs were checked against their raw
hashes. Three additional tiny dependency bodies close the showing getter,
cancel accessor and CancellationSignal wait path, with raw proofs confined to
firmware/biometric-client-metadata-review/. The review does not rerun the original
suite, inspect unrelated services or execute OEM/Android/phone code.

## Actual client and server ownership

Builder stores its exact Context at PC18. build loads that same field at PC50
and passes it at PC63 through the synthetic constructor into the real constructor,
which stores it at PC17. That constructor creates the original token Binder
(PC3/5/8) and original app receiver (PC10/12/15), stores the supplied service at
PC27, and explicitly initializes mIsPromptShowing=false at PCs29/30. A supplied
service bypasses Builder's default auth lookup, so it needs explicit private-route
admission too.

The ordinary crypto public entry reads actual Context.getUserId at PC62, preserves
its strong-crypto checks, and forwards to the private CryptoObject overload.
That overload retains the same CryptoObject, reads its operation ID at PC4 and
passes it at PC17. The long overload retains source checks, effective-prompt
cloning/normalization and exact requested user. At PC129, v8 is service, v9 the
token, v10/v11 the operation long, v12 user, v13 app receiver, v14 the actual
Context.getPackageName result and v15 effective PromptInfo. The actual Context
also remains in v0. The source uses getPackageName, not an inferred package,
server Context or replacement application Context.

The real returned long is captured at PC132 and enters the cancellation listener
at PC135; that constructor stores it at PC5. Cancellation ultimately reaches
the same prompt's cancelAuthentication, loading service/token/Context and its
package at PCs4/6/8/10, then passing the original long at PC14. The newly read
synthetic accessor body forwards that long unchanged. This is a lineage proof,
not a license to guess a request ID or assert that every returned long denotes
an admitted request.

Samsung AuthServiceImpl reads native calling user/UID/PID at PCs62/66/70 and
reaches original permission, AppOps113, foreground135, internal/advanced/Sem
checks before identity clear236 and BiometricService259. Cancel reaches original
permission37 before clear45 and backend53. The proposed app must enter that
original policy directly on the real Binder entry thread. A privileged guest
SystemServer forwarding hop, early post/clear or payload UID cannot reproduce
that native caller. Actual endpoint, Context, permission/AppOps/user/foreground
and source/loader owners remain unassembled; this review does not certify their
live policy merely from these call sites.

## Exact Sem producer outcomes are client data

Samsung semSetExtraInfo reads the actual prompt Context.getDisplayId at PC6;
its actual Exception branch selects display0 at PC31 before the write at PC32.
The same Context must be an Activity at PC37 to query getTaskId43 and write47.
Non-Activity branches39→71 without a task write; the task Exception handler also
performs no task write. Its catch regions are display[4,10) and task[35,50).
Do not unwrap ContextWrapper, infer task from PID, query a server Context, or
turn no-write into an invented successful task0. The earlier common Builder
display and authentication-time Sem display remain separate values.

These source-produced values remain untrusted client metadata, including with a
custom Context. Ordinary fresh non-Sem defaults depend on the separately reviewed
absence profile; they do not authorize dropping existing Sem/security fields.
Actual task/display/user/caller admissibility needs real server owners. A client
metadata codec, operation number or typed receiver is not attestation.

## Concrete lost-cancel schedule and required repair

For a fresh prompt and CancellationSignal, choose no unrelated callback or field
write during this schedule:

1. Initial isCanceled check30 passes; authenticate RPC129 is in flight.
2. Another thread completes CancellationSignal.cancel: canceled=true8, no new
   listener at12, cancelInProgress=false45 and notifyAll47.
3. RPC returns the genuine long132; new listener135 is installed140.
4. setOnCancelListener waits at1. The newly pinned wait helper reads
   cancelInProgress1 and returns11 when false. The setter stores the listener10,
   sees canceled12/14, exits its monitor19 and synchronously invokes onCancel20.
5. The listener's showing accessor2 reads the actual field at its own PC0.
   Showing is still false, so branch8 falls through to return15 without cancel.
   Only after that does authenticate write showing=true144.

This is a conditional static interleaving, not an observed device failure. Both
synthetic bodies and the completed-cancel wait edge were read explicitly.
An authenticate-only invoke replacement leaves it intact. Setting showing early
would not prove visible UI or fix request ownership.

The private route therefore needs a usable pending cell **before** installing
its pre-call listener, with listener installation and remote operations outside
the cell lock. Actual setOnCancelListener can call back synchronously and can
wait for in-progress cancellation; holding that lock across it can deadlock with
the listener. Cancellation must latch without an ID while admission is in flight;
the reply/cancel race must claim cancellation once for the exact same retained
endpoint epoch, token, package and real request. Do not reinstall the source's
late showing-gated listener over this handoff. Preserve source UI state and
app callback/executor semantics separately.

Keep disposition explicit: original AuthService sets −1 at PC117 and returns it
on foreground150, null-input279 and AppOps297 fast-fail paths. The backend result
instead flows from PC259 through262/266. Preserve real failure/return behavior;
do not cancel a fabricated ID or treat a failure sentinel as an admitted request.
This review does not infer a general positive-ID rule from those branches.
Early terminal callbacks, reply loss after possible admission, cancel RPC failure
and stale callbacks require retained ownership and explicit uncertain outcomes.
The guest cancel wrapper itself logs RemoteException18..23 and returns26; normal
void return is not proof of native or callback drain. No retry, fabricated error
or success callback may replace genuine server disposition.

Full common/nested prompt and app receiver schemas, supplied-service admission,
actual pending-cell implementation, same protected native crypto operation,
StrongAuth/additional factors, original ColorOS presentation and real callback
completion remain selection/acceptance gates. No concrete contradiction was
found in the bounded proposal; these conditions do not approve runtime code.
