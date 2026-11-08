# Required guest-local LockSettings control proposal

All **18 guest-local operations are required**, including platform resume on
reboot (RoR). The table below identifies their real implementation paths and the
remaining source-derived adaptations. It proposes a private bootstrap-owned
control transport and a real guest `LockSettingsInternal` proxy; it adds **no
runtime API, code, patch or public credential route**. The existing 33 credential
routes remain unchanged. Root review is required before implementation.

The [inventory](../inventory/local-locksettings-contract.json) pins 113 bodies,
including both complete LocalService implementations, 17 guest synthetic bridges, token/event
producers, actual consumer callbacks, RoR consumers and metric codecs/readers.
`python -B tools/audit_local_locksettings_contract.py` passes 25 selected site
assertions and the complete 18-operation proposal check. These are offline source
facts, not OEM/Android execution or acceptance. Original Samsung DEX041 container
offsets remain intact in the shared-reader proofs.

## Private control and publication

The guest proxy must be published under the actual guest-class LocalServices
key before the replacement lifecycle's onStart returns; Trust/APM constructors
and phase 480/500 consumers already need it. It must never construct the old
guest LSS. The authority side retains the **same actual Samsung LSS/LocalService,
Context, registries, storage/native and user generation** as both guarded Binder
endpoints. Local calls and callback carriers enter that same retirement/active
operation owner. A raw original Binder/local path must not bypass retirement.

The private transport is delivered by the reviewed bootstrap owner, with actual
admitted guest system_server/controller lifetime and operation ownership. Neither
UID1000, a class name, a caller-supplied role nor possession of an arbitrary
Binder proves that ownership. Preserve real upstream DPM/Trust/User/SLD policy
checks before delegation and before any identity hop. Validate actual users,
profiles and serial generations, including background users; global policy
listeners cannot simply be filtered to the selected UI user.

Results remain original values/exceptions. Distinguish refusal before entry,
an actual original return, and failure/transport loss after entry with uncertain
effects. Do not translate uncertainty into false, true, zero, NONE, retry or
rollback. An original void return can mean queued work. Neither it nor a
callback return establishes applied policy, ready storage or consumer drain.

## Exact per-method proposal

`H` below means the genuine Samsung LSS LocalService; `S` means its same LSS.
Full descriptors, argument provenance, original guest callers and proof hashes
are in the inventory. Every row remains unimplemented.

| Guest operation | Actual host path / adaptation | Result and required semantics |
| --- | --- | --- |
| addEscrowToken(token,user,callback) | S.addEscrowToken(token,**0**,user,hostCarrier) | Preserve actual long handle. Guest LocalService supplies literal0 at PC2; it is not a guessed token policy. Callback may be null. |
| armRebootEscrow() | H.armRebootEscrow() | Preserve original int/provider/key/storage result and exception; no invented success or reboot authorization. |
| clearRebootEscrow() | H.clearRebootEscrow() | Return guest true **only after genuine original normal completion**, as the original guest wrapper does; not ready/capture/drain proof. |
| createNewUser(user,serial) | H.createNewUser(user,serial) | Preserve actual KeyStore user-add, serial-reuse cleanup, early-user queue and later SP initialization. Void can mean deferred. |
| disableSecureLockDevice(user,authenticationComplete) | H, same arguments | Original message12 and real unlock/profile effects. True must come from genuine retained factor/policy completion; this is not a public arbitrary-boolean grant. |
| getUserPasswordMetrics(user) | H, same user | Preserve nullable authoritative metrics and original identity clear/restore. Secure-but-uncached null never becomes insecure/default. |
| isEscrowTokenActive(handle,user) | S.isEscrowTokenActive(**user,handle**) | Actual boolean; handle format/existence is not activation. |
| lockUser(user) | Reviewed source-derived Samsung user-lock operation | Execute the real ordered CE/Keystore/StrongAuth/metric sequence below before guest UserController resumes callbacks. |
| onThirdPartyAppsStarted() | H.onThirdPartyAppsStarted() | Real migrations, early-created/removed users and SP work precede original phase flag. One admitted occurrence; no fake boot completion or replay. |
| prepareRebootEscrow() | Reviewed source-derived operation from Samsung RecoverySystem.requestLskf's actual prepare core | Real clear/provider lookup/wanted/event5/StrongAuth 64 path. False for the original missing-provider path; true means preparation, not captured SP or ready. |
| refreshStrongAuthTimeout(user) | H, same user | Real message10 with actual DPM policy; queued return is not applied timeout. |
| registerLockSettingsStateListener(listener) | Genuine S listener list, owned host-interface carrier | Non-null; preserve duplicate registration semantics. No initial event or ready signal. |
| removeEscrowToken(handle,user) | H.removeEscrowToken(**user,handle**) | Original protector checks, actual boolean/exception and actual deletion. |
| removeUser(user) | H.removeUser(user) | Preserve early-user reconciliation and real state/key/security cleanup. No direct storage-only substitute. |
| setLockCredentialWithToken(credential,handle,token,user) | H, same values and genuine credential representation | Preserve actual secure-lock capability, pre-setter settings work, original setter result and post-change work only after true. |
| setRebootEscrowListener(listener) | Reviewed source-owned RoR event carrier tied to real manager and RecoverySystem owner | Host stores concrete RecoverySystemService, not the guest interface. No raw cast, no initial/prepared callback or no-op registration. |
| unlockUserWithToken(handle,token,user) | H.unlockUserWithToken(**user,token,handle**) | Actual escrow/protector verification and onCredentialVerified/metrics/storage/key effects; preserve actual boolean/exception. |
| unregisterLockSettingsStateListener(listener) | Remove the exact owned carrier entry; retire admission and drain | Original remove return does not drain a snapshot iterator, IPC or posted guest work. Preserve duplicate/first-match semantics. |

The guest clear manager body is exactly real `clearRebootEscrowIfNeeded()`
followed by true. Guest LocalService then removes StrongAuth 64 for user−1.
Samsung H.clear performs real clear and posts the same reason/user removal.
This supports the stated normal-completion translation; a missing backend or
failed call never supplies that true.

## Source-owned user lock and mutation disposition

Samsung optimized `lockUser` into
`UserController$$ExternalSyntheticLambda3.run`: actual `IStorageManager.lockCeStorage`
at PC373, `KeyStoreAuthorization.onUserStorageLocked`378, genuine Context default
StrongAuth flags383/requireStrongAuth387, then synchronized metrics removal393.
Its user-locking callbacks follow. Guest LSS has the corresponding CE/default
StrongAuth/cache sequence and a conditional Keystore-cleanup branch. The
proposal follows the genuine Samsung sequence using its actual owners; it must
not construct a fake AMS/Runnable. Samsung `clearStorageForUser` is **not** an
equivalent: it deletes SecureFolder/enterprise LockSettingsStorage and returns
for ordinary users. The reviewed control entry/helper is still missing.

Original Samsung token credential change resets `n_digits_pin_enabled` under
clear/restoreIdentity **before** invoking its real setter. It returns false only
when that setter returns false; on true it invokes onPostLockCredentialChanged
before returning true. Even false can follow the settings effect, and a
post-change exception can follow a committed credential mutation. Preserve that
disposition; never announce cache/credential completion from transport success
or repeat the setter after uncertainty. Real source commit/readback and owned
post-change/cache notification remain required. User create/remove may instead
commit to real early-user queues, reconciled by the actual third-party phase.

## Listener and token event ownership

Both LockSettings-state interfaces contain succeeded(user)/failed(user).
Samsung's actual verify tail calls `isMatched` at 760, then iterates its genuine
CopyOnWrite list and calls succeeded 784 or failed 788, before final result/SP
cleanup. Guest uses its actual helper from doVerifyCredential 488. There is no
per-listener catch in those loops: a callback failure can fail verification
return after authentication effects. It must not become an ordinary wrong-PIN
result, a healthy dropped event or an automatic retry. These events carry a
user, not a challenge/HAT/authenticator proof; they never replace verification
results or app authentication.

Guest registration requires non-null then `CopyOnWriteArrayList.add`; removal
uses remove. Samsung's public-final list is initialized by its real LSS; actual
APM.init and AgentAuth.start register into it. A carrier must implement the
actual host interface in its admitted realm and own each published entry before
add can expose it. Preserve duplicate adds and first matching removals. Closing
an entry rejects stale-generation ingress and retains ownership through actual
snapshot-iterator, transport, guest Handler and active-consumer drain. A missing
or null removal is not proof an uncertain registration disappeared.

Actual guest APM, StrongAuthListener and TrustManager callbacks post required
Handler work; callback return is not applied policy. Their full original
behavior and one selected policy/reporting owner must remain. The bridge emits
no extra LPU/DPM/Trust attempt report. Guest APM's separate nullable RedLogger/
Oplus-background branch can be absent while its core policy message still
posts; this does not make the listener or any of the 18 operations optional.
No telemetry removal is selected here.

Escrow activation is host **(user,handle)** versus guest **(handle,user)**.
Both actual producers sync state and remove the pending-token entry before
callback. Samsung can activate during addEscrowToken before add returns. Retain
the request/callback owner before invoking add; accept the real handle under
that pending occurrence and actual requested user, then reconcile the returned
handle. A lost/thrown callback can follow durable activation. Do not replay it,
invent a handle, roll back by guess or export the SP/key material.

## Metrics and RoR required closure

Both original metrics writers/readers/constructors preserve ten ints in order:
credType, length, letters, upperCase, lowerCase, numeric, symbols, nonLetter,
nonNumeric, seqLength. Both LSS getters create metrics(−1) only for a genuinely
insecure user; otherwise they return the nullable synchronized cache result.
The five actual guest DPM consumers and followed complexity/validation helpers
read those actual metrics. Validation changes a new copy of required-minimum
metrics, not the actual-user argument; merge changes its new aggregate. A
nullable source-value snapshot is supported for these selected consumers, not
Java object identity or arbitrary future users. Source/authority consistency
during capture still requires the real owner; no staged/default cache is added.

RoR remains required. Only guest RecoverySystem calls the four grouped RoR local
operations in the selected services scan. They are platform functions, not
proven OPPO-only extras. Samsung's requestLskf contains the real prepare core
at 223–300. Its manager's ready change posts Runnable0; that Runnable consumes
the real concrete RecoverySystemService's pending/prepared clients, sends real
IntentSenders and persists capture metrics. A generic guest Binder cannot be
stored in that concrete field. Complete support needs the real host RoR owner
and a reviewed source-owned event seam preserving that original work and the
guest listener's real state-change boolean/order. No such carrier/hook or
source-derived prepare entry is implemented here.

A future separately reviewed **complete** RecoverySystem/public/OTA/client/
listener unavailable-path cut could justify optional removal. None exists in
this proposal. Until these required owners, control operations, codecs and
drains are implemented and validated, the guest-local proxy and bootstrap remain
unselected. No phone, OEM execution, runtime API or public26 route extension
follows from this source audit.
