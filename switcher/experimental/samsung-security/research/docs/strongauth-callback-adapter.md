# StrongAuth callback and readiness prerequisite

The selected callback wire is compatible. Registration, applied initial state,
callback ordering and tracker policy are not yet a working adapter. This report
records static supplied-source facts and derived integration requirements; no
Android/OEM code ran and no callback or runtime adapter was implemented.

The [inventory](../inventory/strongauth-callback-adapter.json) pins every selected
body/raw receipt and source archive. It contains 50 newly selected bodies, ten
reused bodies, six exact-method reference scans and direct decoding of the two
trackers' encoded static integer constants. Replay with
`python -B tools/audit_strongauth_callback.py`: source hashes, selected 039 DEX
headers/checksums, named constants and 32 selected instruction assertions pass.
The supplied Samsung services reader retains full-container DEX041 offsets.
Assertion counts describe offline source checks, not runtime coverage.

## Exact wire and admission

Both framework Proxy/Stub implementations use descriptor
`android.app.trust.IStrongAuthTracker` and these two operations:

| Code | Signature | Parcel after interface token | Transport |
| --- | --- | --- | --- |
| 1 | `onStrongAuthRequiredChanged(II)V` | full flags int, user int | one-way flag 1; null reply |
| 2 | `onIsNonStrongBiometricAllowedChanged(ZI)V` | allowed boolean, user int | one-way flag 1; null reply |

Both Proxies write the arguments at PCs13/16; transact is PC23/24 respectively.
Both Stubs enforce the interface and absence of trailing data before dispatch:
ColorOS flags PCs36/40/44/47 and boolean21/25/29/32; Samsung flags38/42/46/49
and boolean23/27/31/34. Their selected callback Stubs perform no caller-UID,
user-owner or authority-generation check. A matching descriptor is not authority.
Callback one-way delivery provides no consumer application acknowledgement.

The enclosing credential protocol maps register21→65, unregister22→66 and
getStrongAuth28→72. Samsung's three service entries call `checkReadPermission`
at PC0. Preserve that real permission and validate the original caller, allowed
user/profile and exact registration Binder before an identity change or thread
hop. Bind callback admission to the retained real backend and immutable user/
authority generation; the wire has no generation field. OneOS shared UID and
permissive/relaxed permission limitations remain disclosed platform limits.
This prerequisite introduces no global Enforcing requirement.

## Initial state, application and removal

Samsung LSS register/unregister enqueue messages2/3 at PCs7–12 and return at15.
In `LockSettingsStrongAuth$1.handleMessage`, switchPC27 sends case2 to493 and
case3 to483. Register calls `RemoteCallbackList.register` at499 and ignores its
boolean result. It then enumerates only existing sparse-map entries: flags
size505/key513/value519/callback523, then boolean size538/key546/value552/
callback556. RemoteException at either callback is logged and iteration
continues. There is no per-user default callback or initial-complete marker in
this case. Empty maps can produce no initial callbacks. Unregister calls the
callback list at489, ignores its boolean and returns492. These paths neither
acknowledge client Handler application nor drain already delivered work.

Both original LPU trackers construct empty per-user maps. Their flags getter
uses `SparseIntArray.get(user, mDefaultStrongAuthFlags)` atPC4; the non-strong
getter uses a default **true** atPC2–3. Default flags come from the actual
Context's boolean resource: ColorOS17891997 and Samsung17892001. Numeric IDs
do not prove equal effective resource policy. Both apply handlers update their
map before calling the consumer; if the incoming value equals the cached/default
value they return without notifying the consumer. Thus even a genuine callback
with a default value need not produce a changed-state signal.

ColorOS flags callback queues at the **front** atPC17; Samsung flags callback
uses ordinary `Message.sendToTarget` atPC11. Both boolean callbacks queue
normally. A delayed ColorOS consumer can therefore observe scheduling that
differs from Samsung's producer order; transport arrival and latest applied
state must not be conflated. The exact ordering remedy remains unimplemented.

Samsung LSS `getStrongAuthForUser` calls its synchronized tracker atPC5, whose
getter invokes the superclass cache getter under a monitor atPC1. It does not
wait on registration/StrongAuth Handler work or read the producer maps in that
body. Register followed by this query is not a demonstrated snapshot/subscription
barrier, and it supplies no non-strong boolean snapshot.

ColorOS LPU registration propagates RemoteException via
`rethrowFromSystemServer` atPC13. The selected RemoteException implementation
always throws (DeadSystemRuntimeException at19, RuntimeException at25).
Unregistration instead logs RemoteException atPC17 and returns20. Neither
normal wrapper return proves removal/drain. Retain uncertain registration and
removal ownership; no blind retry or replacement registration is justified.

## Genuine policy and native consumers

Direct encoded values agree for all 14 common named flags, including boot1,
lockout8, primary secure-device2048 and strong-biometric secure-device4096.
`ALLOWING_BIOMETRIC` is ColorOS5892 (`0x1704`) versus Samsung5900 (`0x170c`).
Samsung additionally defines five Knox reasons: biometric lockout65536,
lock131072, fingerprint change262144, face change524288 and non-strong idle
timeout1048576. Preserve full flags, including unfamiliar high bits.

Both complete helper paths compute
`((flags & ~ALLOWING_BIOMETRIC) == 0) && (isStrong || nonStrongAllowed)`.
The AND literal atPC4 is ColorOS−5893 versus Samsung−5901. Consequently flag8
alone blocks the ColorOS helper but permits the Samsung helper for strong
biometrics; non-strong still requires its actual boolean. Flag2048 blocks both;
flag4096 alone is permitted by both helpers. A true helper result therefore
does not establish additional-factor completion or permission to finish.
Trust eligibility independently requires flags==0 in both selected helpers.

Exact direct-call scope, with complete selected caller bodies:

| Archive | Call sites | Actual consumers |
| --- | --- | --- |
| ColorOS SystemUI | 4 / 3 methods | KUM unlockPC22; repository constructor strong409/non-strong440; StrongAuth flow map70 |
| Samsung SystemUI | 6 / 5 methods | KUM10; security override16; fingerprint margin17; repository constructor427/452; flow map63 |
| Samsung services | 1 | TrustManagerService Keystore lock-state policyPC41 |
| Both frameworks, ColorOS services | 0 exact references | Limited to this exact declared method target; not reflection/other apps |

Both repository constructors seed eager StateFlows from current cached helper
values before a demonstrated initial-state receipt. Flow maps use the emitted
AuthenticationFlags' user, then query their tracker's cache; they do not derive
the boolean from the emitted flags value. Pinned declarations confirm the two
SystemUI tracker classes on each side and Samsung's TrustManager tracker extend
this base directly and declare no `isBiometricAllowedForUser` override. This is
supplied class evidence, not an admission of arbitrary runtime subclasses.
ColorOS KUM also checks flags1/2048,
face/fingerprint lockout and prevent mode. Samsung base KUM adds fingerprint
class/lockout conditions; its security override includes two-step, security
dialog, biometric deadline and ultra-power-saving policy. Samsung TrustManager
uses non-strong eligibility alongside real enrollment, sensor strength, device
policy and trust state before `KeyStoreAuthorization.onDeviceLocked` at190.
None of these higher policy paths is replaced by a matching callback parcel.

The required compatibility direction is delegation of tracker-level eligibility
to the genuine Samsung original under the same current user/authority, with
genuine higher policy, additional-factor and finish gates preserved. Keeping
the guest's stricter flag8 outcome is a full-UX gap; copying the Samsung mask
alone is insufficient and no policy byte patch is selected.

## Minimum remaining adapter contract

Retain actual code/state owners before opening the exact registration. Obtain
a same-authority selected-user initial snapshot, including genuine default
policy and non-strong boolean, coupled to a source-owned subscription ordering
barrier. Acknowledge actual consumer application without assuming changed-value
notifications. Resolve front-of-queue ordering, user changes and stale cache
seeds before publishing readiness. The existing three routes provide no such
complete contract; a source-owned extension or another reviewed original owner
is required. Zero flags/true boolean can be legitimate attested values, but
local defaults, silence, a completed call or an independently cached query are
not that attestation.

Retirement must close callback admission first, remove the exact registered
Binder, and acknowledge real source broadcast/Binder/local queue and active
consumer drain before releasing owners. Late callbacks must retain their old
generation and be rejected. Uncertain progress remains owned and unavailable.
Version, authority or selected-user mismatch retires readiness. Independent
AuthenticationPolicy enabled/additional-factor state and actual finish gates
remain required, as documented in [strong-auth-gating](strong-auth-gating.md).
These mechanisms are unimplemented: protected presentation remains unknown/
locked until genuine current state and policy are applied. No fake callbacks,
replayed tokens, permissive defaults or cached UI success close this gap.
