# Gate E: finite Samsung biometric authority bootstrap

**Conditional source-supported slice, not a startable authority.** The original
Fingerprint → Biometric → Auth service family has a finite dependency order that
can be described without requiring all Samsung SystemServer services. The
decisive missing owner is a real admitted Samsung Context/framework/service set
with correct users, resources, callbacks and local/remote endpoints, plus exclusive
native and metadata ownership **before** provider construction. This report does
not supply those owners or prove that an unmodified extraction can start.

The [inventory](../inventory/authority-bootstrap-biometrics.json) pins the source
edges and unresolved gates. The default
`python -B tools/audit_authority_bootstrap_biometrics.py` rechecks 65 saved bodies
and three new, narrowly selected SysUiManager bodies, with 15 source assertions.
`--collect` reproduces only those three methods. No OEM class, constructor,
initializer, service, HAL or phone operation was executed.

## Minimum direct owners actually reached

The table is a bounded direct frontier, not a complete transitive class or
resource closure. PCs are method-relative code units, hexadecimal where prefixed
`0x`; the inventory also records original signatures and hashes.

| Owner | Actual source boundary | Required genuine binding |
| --- | --- | --- |
| Context / framework / threads | Public Fingerprint constructor first calls `BiometricContext.getInstance`; injected constructor retains AppOps, LockPatternUtils, UserManager, registry and original fingerprint Looper. BiometricService has its real three-input Context/Injector/handler-provider constructor. Auth constructor creates its own Injector and wrapper. | Actual source-compatible Context, package/op attribution, Resources, ContentResolver, permission behavior and working main/fingerprint/biometric callback handlers. Gate A owns Context/manager factories; no mock Context or copied registry follows from this card. |
| Window / statusbar / display | First BiometricContext gets `window` through Context.getSystemService and `statusbar` through ServiceManager.getServiceOrThrow; provider registers biometric-context/session listeners and a dock receiver. BiometricService.onStart queries local `DisplayManagerInternal` at 173. | Real WindowManager and typed statusbar callbacks carrying actual display/awake/session state. Exact local Class identity and listener behavior; nullable source lookup is not proof that display requirements are satisfied. |
| ActivityManager | Provider constructor gets `IActivityManager`; SensorList registers user-switch observers, including an inline initial-user callback for sentinel `-10000`. BiometricService registers its user-switch observer at 546. | Genuine current user, observer delivery, callback generation and IPC permissions. No fabricated current user zero. |
| PackageManager / service binding | Auth fallback configuration and BiometricService settings branches query real hardware features. SysUiManager later binds an explicit Samsung component. | Actual source feature/resources/package state and real AM/PM service resolution; class or package-name presence is insufficient. |
| UserManager / UserInfo | Fingerprint state callback retains UserManager; BiometricService obtains it at 63/397. HAL acquisition iterates `getAliveUsers`, current-user cleanup and authenticator-ID loading. | Correct alive users, IDs, profiles, serials and lifecycle, consistently tied to credential/CE authority. Gate C's user/state admission must precede eager reads. |
| DevicePolicyManager / trust | BiometricService obtains DPM at 30 and `trust` in constructor/onStart. Policy/setting observer state is retained. | Real admin, lock, trust and user policy, with typed service interfaces; no independently relaxed biometric policy. |
| Camera / sensor privacy / optional modalities | BiometricService obtains CameraManager and SensorPrivacyManager at 409/417 and FaceManager at 79. A nonnull face manager registers a callback at 359. Auth also processes face/iris configurations. | Original feature and null guards remain. An FP-first slice needs genuinely absent optional modalities or separately reviewed unavailable-feature treatment; do not invent false features or null managers. |
| Local services | BiometricService gets `VirtualDeviceManagerInternal` at 495; onStart optionally obtains DisplayManagerInternal. | Real same-Class registry owners or explicit source-compatible typed projections. A source-private Class key does not match a guest namesake. |
| Crypto / credentials | BiometricService obtains KeyStoreAuthorization at 445 and GateKeeper at 451. FP retains its actual LockPatternUtils; operation paths consume genuine policy and tokens. | Same admitted credential authority and per-instance LPU route, authentic native Gatekeeper/KeyMint/Keystore operation and user/key namespace. Credential/storage/native owners remain prerequisites. |
| Power, deferred operation owner | Existing `SemFingerprintAuthenticationClient.isInteractive` obtains PowerManager at PC4 and calls `isInteractive` at `0x0a`; `enableEarlyWakeUp` calls `setEarlyWakeUp(boolean)` at `0x0d` after a null guard. | Real power/display behavior before admitting affected operations. This is not an observed acquisition in the cold constructors; importing a PowerManager name does not supply its service behavior. |

The source BiometricService constructor already obtains FingerprintManager at
PC71 and registers the authenticator callback at 349. Therefore manager factories
and same-family endpoint routing must exist before that constructor returns.
In the dedicated Samsung framework realm, the original global names can remain
Samsung-owned, with explicit guest-facing aliases owned by gate B. If a different
namespace is selected, exact internal suppliers/Injector routes need an admitted
adaptation; default guest-protocol endpoints are not substitutes.

## Finite candidate start order

This is an **inferred assembly order from actual dependencies**, not a new audit
of Samsung SystemServer's complete start method, and not permission to execute it.

1. Close Context/framework/resources, genuine user/state/credential/local owners,
   guest-producer suppression and exclusive native writer admission. Retain all
   callback/handler and rollback/recovery owners before first construction.
2. Prepare genuine BiometricContext, original handler provider and the FP service
   cohort. First singleton creation may register statusbar/session/dock callbacks;
   registration errors can be caught/logged, so a returned object is not readiness.
3. Construct/start original FingerprintService under the single chosen authority.
   Its onStart publishes `fingerprint` at PC5. Publication is earlier than provider
   registration; guest consumers must remain gated. The registry's biometric
   supplier must later resolve the same genuine source service family.
4. Construct/start original BiometricService with real managers. It publishes
   `biometric` at PC113 (`0x71`), before subsequent listener/post/display work.
   Complete those owned effects rather than equating the publication with health.
5. Construct/start original AuthService. Its Injector resolves global `biometric`
   at onStart PC4 and `fingerprint` at 99, posts fingerprint registration at 200,
   then publishes `auth` at 437. These must be original source-family interfaces,
   not guest aliases. Its public constructor creates its Injector; the source has
   no supplied-injector constructor in the selected declarations.
6. Let the original configuration/provider registry complete under the same
   admitted native/state owner. Supplier execution precedes registry lookup of
   biometric service. On a cache miss, `getSensorPropForInstance` calls genuine
   HAL `getSensorProps` **before** provider construction.
7. Preserve real phase and callback order. Admit operations only after actual
   registry/property/user/lockout/policy readiness and required phase work; do not
   force boot phases or synthesize callbacks to finish this sequence.

No complete class-cohort producer or lifecycle owner is delivered. Reached
original nested helpers, schedulers, lockout/authenticator adapters, state stores
and callback implementations stay with their source owners. Constructors,
property lists and registration callbacks do not prove native authentication.

## First effects and original guards

**Observed:** provider construction creates Samsung provider/callback owners and
statistics/dangling receivers before its null-properties check. It registers
per-sensor user observers, posts AIDL HAL acquisition and reads user0 fingerprint
metadata before returning. The literal zero read is original behavior, not a user
mapping fix. `getHalInstance` links death and schedules alive-user cleanup and
authenticator-ID loading. Thus exclusive correct state must precede the factory,
including any HAL property-cache miss, rather than only `authenticate`.

The existing state proof establishes why the read frontier matters:
BiometricUserState construction can rename legacy metadata, and parse failure can
delete/rewrite it. Cleanup can remove hardware templates unknown to the selected
metadata. Neither an empty guest XML nor a read-only-looking factory is safe
admission for existing prints. New enrollment/removal must later use that same
writer and authentic authorization chain.

Specifically, `construction-state.json`'s `fingerprint-parse-recovery` proof is
`BiometricUserState.readStateSyncLocked()`: decimal PC58 calls File.delete and
84 calls AsyncTask.execute. Its separate `fingerprint-asynchronous-file-write`
proof follows the actual write Runnable to AtomicFile start18/finish58/fail74.
Those are separate selected body proofs, beyond the original constructor's
legacy-rename evidence.

Actual feature/phase distinctions include:

- `FP_FEATURE_LOCAL_HBM` guards the constructor's local-HBM controller; in-house
  HBM has its own source flag. Do not disable required illumination or touch
  behavior as a presentation extra.
- Auth's `isHidlDisabled` returns false; real declared AIDL instances and genuine
  configuration select the provider path. The captured AIDL-v3/default manifest
  is a declaration, not a live sensor assertion. No virtual/test provider fallback.
- BiometricService display registration is guarded by a nonnull local service
  at PC183; brightness additionally uses the genuine DRM-brightness feature at
  190. Existing selected guest declarations lack these exact Samsung listener
  members. Null-skipping them is not an implemented display adaptation.
- Phase550's source `mHasUdfps` guard at `0x57` skips to `0x1ec` when false.
  Reached UDFPS work reads geometry, programs TSP behavior and conditionally
  writes `key_fingerprint_lockstar_custom_effect=1` for current-user sentinel
  `-2` at `0x1da` when its actual stored value is zero. This is a real settings
  write, **not** an unconditional all-profile effect.
- Phase600 registers the all-user removal receiver and, with a provider, performs
  feature-dependent TSP/S-pen, one-hand, film and optical support. Phase1000 sets
  per-sensor boot-complete state, executes pending fingerprint metadata Runnables
  at `0x593`, and re-establishes statusbar/display context. A posted callback or
  phase method return does not acknowledge its children or metadata durability.

## Deferred UI endpoint and scope boundaries

The three new bodies distinguish a local manager from an operational endpoint.
The outer `SemBiometricSysUiManager(Context,Looper)` body allocates local
collections, callbacks, executors and handlers; it contains no direct endpoint
bind. This is not a proof that every reached initializer is effect-free.
`openSession` calls `bind` at PC120; `bind` invokes actual Context.bindService at
57 for `com.samsung.android.biometrics.app.setting/.BiometricsUIService`, then
posts a 3000ms connection timeout. An app/package/connection object or constructor
return does not prove that service exists, responds or owns the right hardware
session. Full typed Samsung UI/native display support or a separately proved
projection is a required deferred owner for reached operations, not evidence
that all Samsung SystemServer must run.

Gate E identifies the **original service family and its effects**. Gate B owns
suppression of competing guest starts/producers and alias/publication cuts;
gate A owns real Context/manager/registry construction. Matching a remote manager
descriptor does not certify its transaction numbers, nested payloads, callbacks,
caller/user policy or native endpoint. The prior limited ABI comparison is not a
blanket permission to use guest AM, WM, statusbar, trust or policy proxies.

The finite slice remains blocked on concrete external owner admission, same-family
manager/endpoints, exact display/local/UI support, complete callback and native
drain, and installed-image identity. These are explicit finite gates, not proof
of impossibility or a demand to import every Samsung service. Existing/new prints,
real protected app crypto and intended CE/key policy remain required. No fake
flags, current-user values, default endpoints, enrollment lists or success states
are supplied.
