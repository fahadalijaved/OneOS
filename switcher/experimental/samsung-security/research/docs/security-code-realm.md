# Bounded Samsung security code-realm preparation plan

The source supports a private Samsung LockSettings family behind canonical
Android Binder/Parcel transport. It does **not** yet establish an executable
minimum extraction or a ready loader. The minimum type boundary is concrete;
the construction, internal LockPatternUtils route, local-service owners,
resources, native admission and lifetime remain required bindings.

The [inventory](../inventory/security-code-realm.json) enumerates 75 candidate
definitions across seven named service families and five protocol/value
families. Of these, 58 are roots or directly named by the already-selected
bodies; remaining lexical nested/compiler helpers are explicitly candidates,
not proven required or safely removable. It reuses 257 previously read method
bodies without recursively scanning their dependencies. Only one missing body,
Samsung `LockPatternUtils.getLockSettings`, was newly read. Four immutable
declaration indexes, exact source descriptors/members, physical/logical DEX
locations and inherited proof hashes are pinned. Counts describe this boundary,
not source closure, runnable construction or feature acceptance.

## Exact partition at the established boundary

| Definition / group | Required identity and reason |
| --- | --- |
| `android.os.Binder`, `IBinder`, `IInterface`, `Parcel`, `Parcelable` / `Creator`, `RemoteException` | Delegate to the genuine running platform. Private Stub ancestry and all reflected dispatch parameters must use these same actual Classes. Never define a second Binder/Parcel family. Ordinary Java/library primitives, Strings, arrays, collections and JCA/JCE interfaces likewise remain canonical. |
| `android.content.Context`, ContentResolver/Resources, Handler/Looper/HandlerThread, UserHandle/UserManager/UserInfo, DevicePolicyManager | Keep canonical object identity for objects supplied by the running framework and its Context. This does not prove correct users, policy, Resources content or hidden-method compatibility. A private same-name receiver cannot accept a canonical framework object by name alone. |
| `android.security.Scrypt` | **Canonical required.** Existing native-linkage proofs identify actual Java/native registration and matching selected implementations. A private same-name Scrypt is not automatically registered. No Samsung `libandroid_runtime` import follows from private SPM's call to canonical Scrypt. |
| `com.android.internal.widget.ILockSettings` + `$Stub` / `$Stub$Proxy` | **Samsung-private required** for the unmodified Samsung protocol. LSS extends this Stub; its wire transaction numbers differ from guest ILockSettings. `$Default` is inventoried separately as a candidate, not justified merely by being adjacent. |
| `com.android.internal.widget.LockscreenCredential`, `VerifyCredentialResponse`, their creators/builders/compiler support | The source-preserving candidate keeps these Samsung-private with its Stub and SPM. Use canonical Parcel transport and each side's own CREATOR, rather than casting guest objects to these types. Samsung `VerifyCredentialResponse.isSkip()Z` is actually reached at LSS credential setter PC194 and absent from the guest declaration; blindly sharing the guest value class is insufficient. Their bounded common wire format remains governed by the protocol proof. This does not prove that every payload class must be private under every possible future source adaptation. |
| `com.android.internal.widget.ICheckCredentialProgressCallback` + Stub/Proxy; `android.app.trust.IStrongAuthTracker` + Stub/Proxy | Keep the Samsung typed marshaller side in the same private protocol realm. Cross the boundary through genuine canonical IBinder callbacks and reviewed descriptors/transactions, not casts between guest/private callback interfaces. StrongAuth tracker methods are `onStrongAuthRequiredChanged(II)V` and `onIsNonStrongBiometricAllowedChanged(ZI)V`. Initial state, early progress, callback user/generation, death and drain remain real ownership obligations. |
| `com.android.server.locksettings.LockSettingsService`, SyntheticPasswordManager, LockSettingsStorage, LockSettingsStrongAuth, SyntheticPasswordCrypto, PasswordSlotManager, LockSettingsInternal | Same-source private service cohort, including reached nested/helper definitions. In particular keep SPM `$SyntheticPassword`, `$AuthenticationResult`, `$PasswordData` and other admitted nested types with their owner; the Samsung `deriveSubkey` API cannot be mixed with guest nested `deriveGkPassword` types. Exact same-package access also includes loader identity. No arbitrary guest namesake fallback is approved. |
| `com.android.server.LocalServices`, `SystemService` | Canonical shared registry/startup contracts. The private original `LockSettingsService$LocalService` extends its private Samsung `LockSettingsInternal`; publishing that Class key does not populate the distinct guest LockSettingsInternal key. A genuine typed adapter can project the same authority under the guest key only after the required methods/ownership are implemented. Never copy a registry to hide a missing service. |

The inventory gives every candidate descriptor, not just these short family
names. It also records exact framework members and the per-class source ancestry.
No duplicate class definition or shared-name type equality is inferred from
matching declarations.

## Binding frontiers that prevent blind parent delegation

Samsung LockPatternUtils is a concrete frontier. Saved LSS bodies reach
`isQualitySmartCard(I)Z` (credential-type path PC126),
`getBiometricStrongAuthTimeout(String,int):long` (selected dump sites), and
`invalidateSecurityStateCache()V` (`setLskfPolicyState` PC8); these Samsung
declarations are absent from guest LPU. The direct remote-lock field reference
at `applyRemoteLock` PC121 is valid through Samsung LPU's implemented
`com.samsung.android.lock.LsConstants` interface, which declares
`REMOTELOCK_TYPE:String[]`. Guest LPU has no such interface and the guest
framework lacks LsConstants. Retaining private LPU therefore also needs that
same-source policy interface, not an invented field or cleared remote-lock rule.
Inherited Binder identity methods on Stub are not missing guest APIs.

Conversely, blindly privatizing LPU leaves a concrete routing error. Its real
getter reads **private instance** `mLockSettingsService` at PC0, looks up literal
`lock_settings` through canonical ServiceManager at PC7, calls private
`ILockSettings.Stub.asInterface` at PC11 and writes that instance field at PC15.
The field flags are **0x2**, with **IGET_OBJECT/IPUT_OBJECT**, not static. A
Samsung-protocol Proxy obtained from a guest-protocol frontend would use the
wrong transaction meanings.

A bounded proposed binding is to populate each actual private LPU instance with
the same genuine private LSS implementing its private ILockSettings before any
getter. This is **not implemented or ordering-proven**. Identifying every real
LPU owner, first access, constructor/eager callback ordering, safe publication,
cache/death/replacement and final drain remains open. It is not a single static
realm seed and does not authorize a global ServiceManager substitution.

Other exact frontiers remain:

- Samsung LSS's concrete `StorageManagerService$StorageManagerInternalImpl`
  field/key/outer `mVold` accesses cannot consume the guest namesake. The frozen
  storage linkage/adapter plans describe preserving a genuine owner or a
  coherent typed source retarget, not importing all StorageManager startup.
- Samsung `android.os.IVold` protection/unlock descriptors and codes differ
  from guest; a same-name canonical guest Proxy is not its native projection.
  The selected indexes contain IVold/Stub/Proxy definitions in both Samsung
  framework and services roles: choose one admitted exact definition, never
  define both or assume body equality from the name.
- Concrete `com.android.server.security.authenticationpolicy.SecureLockDeviceService`,
  canonical/private UserManagerInternal and BiometricHandlerProvider ownership,
  `android.security.KeyStoreAuthorization`, AndroidKeyStore load parameters and
  Gatekeeper API/payloads need their actual supplied instances and member
  contracts. No unrestricted parent fallback or blanket private copy is proved.
- Canonical Context/Resources identity does not fix Samsung numeric resource
  values. The existing resource audit's LSKF-enforcement boolean collision
  remains a separate construction binding; code loading cannot turn a guest
  value into the Samsung policy value.

## Loader and DEX admission plan

Existing SDK37 `javap -protected -s` confirms **final**
`dalvik.system.InMemoryDexClassLoader`, with constructors:

```
(ByteBuffer, ClassLoader)
(ByteBuffer[], ClassLoader)
(ByteBuffer[], String librarySearchPath, ClassLoader)
```

It cannot be subclassed to override load policy. BaseDexClassLoader's exposed
`findClass`, `findLibrary` and resource methods and DelegateLastClassLoader's
different API shape are pinned in the SDK receipt; SDK stubs do not prove the
captured ART implementation or DEX parser behavior.

The simplest reviewable preparation is a physically bounded, hash-inventoried
DEX cohort plus an explicit parent rule: canonical definitions delegate to the
actual running platform; admitted private names cannot silently resolve to
guest collisions; unavailable/unadmitted names fail. CNFE-only parent masking
with whole Samsung archives does not itself prevent an unadmitted child
definition from resolving after a parent miss. Root's alternative non-CNFE
parent-miss barrier is a plausible ordinary-Java design, **not equivalent ART
isolation proof**; optimized/in-memory resolution behavior remains unverified.
No such loader, barrier or source-subset producer is prepared here.

Samsung services is one DEX041 physical container with logical headers 0 and
10057984. Table/data references remain full-container-relative. Do not split at
the second header and treat slices as independent DEX. Nor does a public
ByteBuffer[] constructor establish that the actual ART in-memory loader accepts
this whole container, enumerates both logical members, or preserves dependencies.
A future bounded producer needs exact source/member/header admission and
preservation proofs; any reconstruction needs its own method/descriptor/branch/
try/native provenance checks. Preserve duplicate detection across all buffers
and keep code buffers/loader ownership through their real lifetime.

## Native ownership and preparation order

Canonical startup registration binds the resolved platform Scrypt/SPM Class,
not every private same-name Class. The prepared authored
`SidNativeBinding.loadAndBindOnce(String,Class)` route takes an **actual target
Class** declaring private instance native `nativeSidFromPasswordHandle([B)J`.
Its inventory requires genuine helper/image/target provenance, one admitted
attempt and process-lifetime native GlobalRefs/owners. It is not yet bound to
an admitted original private SPM. A class name, library search directory or
exported JNI symbol alone cannot establish the right registration or namespace.
Do not load another copy of Samsung server/runtime libraries to make linkage
appear complete.

The dependency order is therefore: pin complete candidate source/profile and
type policy; close the named route/local-service/resource/native frontiers;
produce and statically admit a bounded coherent code cohort; prepare its real
canonical parent/native/helper ownership; establish every real LPU and service
first-use boundary; only then consider original construction/startup under the
separate policy/state/user/generation and recovery owners. Future loading,
linking, initialization or registration is not authorized by this report.
Original eager effects, one-writer state, callback drain and safe return remain
mandatory. All runtime/cross-OS acceptance remains open; parent ColorGlass stays
paused.

Recheck metadata and pinned inherited evidence with
`python tools/audit_security_code_realm.py`. `--sdk` refreshes SDK declarations;
`--collect-route` reproduces only the named LPU getter query. No OEM class was
loaded, initialized or executed, and no global classpath, service, phone or Git
action was taken.
