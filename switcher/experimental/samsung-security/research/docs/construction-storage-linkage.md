# Stage 1: LockSettings storage linkage

**Observed source result:** unchanged Samsung LockSettings cannot use the captured
ColorOS storage local service merely by sharing its class name or registry.
The registry key, concrete Java members, method descriptors and vold wire format
all differ. This closes the immediate linkage question; it does **not** prove
controlled import impossible or establish a working retained authority.

The [derived inventory](../inventory/construction-storage-linkage.json) pins all
four actual archives, 19 successful reader receipts, body hashes, logical DEX
offsets and the selected edges. Raw bodies stay ignored under `firmware/`.
The Samsung services container is read without rebasing: logical headers 0 and
10057984, with 9252 and 9664 class definitions respectively. The original donor
archives are a source baseline, **not verified installed OneOS patched bytes**.

## Exact LockSettings requirements

The whole Samsung services reference scan finds 107 direct references to
`StorageManagerService$StorageManagerInternalImpl`, eight in the locksettings
package, all in `LockSettingsService`:

| Actual caller / code-unit PC | Required edge |
| --- | --- |
| Constructor 643, 645, 649, 651 | Load concrete implementation `Class`, `LocalServices.getService(Class)`, cast and store concrete `mStorageManagerInternal`. |
| `unlockCeStorage(int,SyntheticPassword)` 165 and 180 | Invoke concrete `unlockCeStorage(I[B[B)V`. |
| `setCeStorageProtection(int,SyntheticPassword)` 88/110, 90/112, 92/114, 94/116 | Read implementation `this$0`, outer service `mVold`, implementation `isHSUMMode`; call `IVold.setCeStorageProtection(I[BZ)V`. |

Those eight references are **not the complete typed field closure**. LSS itself
declares public-final `mStorageManagerInternal` with that concrete descriptor.
Five additional field references are owned by LSS: constructor `IPUT_OBJECT`651,
protection `IGET_OBJECT`83/105 and unlock `IGET_OBJECT`163/177. A typed retarget
must update/preserve this declaration and all five uses as well as the eight
concrete-owner edges; changing only an invocation or registry key is incomplete.

The scan counts references owned by the concrete implementation, so outer-service
field and registry-method references in that table are verified separately from
the full 199-body LockSettings receipt. Direct-edge completeness is limited to
explicit DEX references; it does not cover reflection, JNI or runtime dispatch.

Samsung's optimized implementation extends `Object`; the canonical
`com.android.server.StorageManagerInternal` declaration is absent from these
Samsung services/framework archives. ColorOS's implementation extends that
abstract class and exposes `unlockCeStorage(I[B)V`. Its implementation has no
`isHSUMMode`; `this$0` is package-private/final, and the outer `mVold` is private.
Samsung's corresponding outer field is public/volatile. Thus simply registering
a guest object under the Samsung key still leaves missing descriptors and
field-access differences. A null lookup alone does not fail `CHECK_CAST`;
later use, verifier/linkage behavior and the chosen loader must be tested.

LockSettings also obtains Binder service `mount` and calls canonical
`IStorageManager.isCeStorageUnlocked(I)Z`. Both actual storage service bodies
answer using their own `mCeUnlockedUsers` cache under `mLock`; this is not an
independent cryptographic check. Samsung's unlock path may skip work after that
query. The cache and unlock backend must describe the same authority/user.

## Registry ownership and initialization

Samsung `StorageManagerService$Lifecycle.onStart()` constructs the implementation,
sets `this$0`, initializes listener containers, captures
`UserManager.isHeadlessSystemUserMode()` at PC191 into `isHSUMMode` at195, then
registers the concrete implementation class at533–537. ColorOS's outer service
constructor registers **`StorageManagerInternal.class`**, at465–469. The captured
guest registration therefore does not satisfy Samsung's concrete-key lookup.

Both actual framework `LocalServices.addService` implementations synchronize on
their static `ArrayMap`, test `containsKey`, and throw `IllegalStateException` for
an existing key before insertion. They do not replace services. Keys are genuine
`Class` objects: a private loader copy would have another identity, and a private
`LocalServices` copy would have another registry. Adding another key is not a
safe authority handoff. Test-only removal is not a production replacement plan.

## Native endpoint and wire ABI

Both actual `connectVold` bodies perform
`ServiceManager.getService("vold") → IVold.Stub.asInterface → mVold`, register a
listener, and contain retry/death-related paths. This identifies a lookup route,
not the actual live host/guest service generation or caller authority.

| Proxy operation | Samsung | Original ColorOS |
| --- | --- | --- |
| Protection | Transaction **46**, `(I[BZ)V`: user, secret, HSUM boolean | **54**, `(I[B)V`: user, secret |
| Unlock | Transaction **60**, `(ILjava/lang/String;[BZ)V`: user, HAT text, secret, HSUM | **56**, `(I[B)V`: user, secret |

Actual proxy instruction registers prove these transaction codes and Parcel write
orders; both use descriptor `android.os.IVold`. Matching Binder names/descriptors
does not make these operations wire-compatible. Both each-side framework and
services IVold declarations agree on the selected signatures. Runtime classpath
selection and the receiving native implementation remain unverified.

Samsung's actual implementation converts the optional HAT to hex (or `!`),
passes HSUM to vold, then updates its unlocked-user cache; the guest method
passes only user/secret and updates its own cache. Unencrypted branches can
update Java state without vold. These are source paths, not successful CE unlock.

The LSS input contract is narrower than accepting a caller-selected secret/HAT.
Protection derives the SP FBE subkey at PC9; the genuine non-device-owner DualDAR
branch instead fetches the outer-layer key at73 and passes that to vold at94.
The other branch passes the derived subkey at116. Unlock derives at48, can
substitute the genuine DualDAR key fetched at109 into its secret register, and
calls same-SP `verifyChallenge` at131. Its actual first-API-level/user/enterprise/
SecureFolder/response conditions determine whether it obtains the HAT at157 and
passes it at165, or passes explicit null at179/180. The HAT-bearing branch throws
if that HAT is null. Do not always require a HAT, always discard it, accept an
arbitrary caller HAT, or replace the DualDAR branch with an unconditional FBE
subkey. These exact bodies are pinned in the inventory.

Buffer lifetime is part of that contract: protection zeroizes its derived SP
array at124 on normal return and128 on its catch-all path. Unlock zeroizes its
current secret register at213 on normal return,233 after a caught RuntimeException
(which logs and returns), and237 before rethrow. In the substituted protection
branch this is the derived SP array, not a demonstrated wipe of every outer-key
or HAT allocation. Preserve the exact source behavior and do not overclaim its
hygiene. An asynchronous adapter cannot retain borrowed arrays after the original
synchronous call returns; any necessary owned copy requires explicit consumption,
drain, cleanup and zeroization, including exceptions and uncertain progress.

OneOS's pinned `guest_no_vold_keys.py` producer removes create/destroy/protect/
unlock/lock IVold invocations outside the AIDL classes and expects five removed
calls. Its stated purpose is preserving host keys. That source does not establish
which patches are installed. Leaving this protection intact cannot supply a real
new credential-to-CE-key transition; removing it without an owned replacement can
expose host keys to the wrong writer. No protection is changed here.

## Concrete architecture consequences

**Controlled Samsung import remains a design option.** Before construction it
needs a single explicit registry/type policy: either retain the same-source
concrete storage dependency closure, or prove narrow source-derived rewrites for
all eight concrete-owner references plus their outer-field/IVold accesses.
An abstract adapter alone does not close the unchanged code. Keep the real
Samsung HAT/HSUM/user policy, error propagation, caches and notifications; never
drop arguments or return success to bridge the descriptor gap. Prove the exact
receiving native wire contract and original user/mount/key authority before a
mutating operation. No such rewrite or runnable adapter is delivered here.

**Guest-side typed adapter/retarget is an explicit alternative to importing the
full Samsung storage service.** Adapt ColorOS-facing APIs to a genuine Samsung
backend. A narrow owned internal contract must distinguish protection, unlock
and authoritative status, preserving the original user, actual conditional
same-SP HAT/null, SP-derived or genuine DualDAR secret and HSUM policy. Retarget
the concrete-key acquisition, the public-final LSS field declaration and its five
uses, both concrete unlock calls and the direct outer-service/IVold protection access
to that contract, with exact per-method preservation proofs. Bind it to the
actual Samsung native storage authority through its verified wire ABI, not the
incompatible guest IVold proxy. If a canonical guest `StorageManagerInternal`
adapter is retained for other consumers, its two-argument unlock operation does
not magically supply the missing HAT/HSUM; the real policy/ownership contract
must determine whether that caller is permitted and sufficient, or refuse it.

Guest SMS can continue owning guest-specific volumes/status only after the
host-key operations and same-user status/cache/listener view are explicitly
separated and coherent. An owned status facade must not let a guest cached
"unlocked" result skip required host work. This design does not require keeping
incompatible OPPO implementation details. Optional unsupported OPPO features,
their UI entry points and background work may be removed with audited callers
and lifecycle cleanup. No missing signature becomes a no-op or fabricated
success. Full shared PIN/fingerprint, policy, app-key and CE behavior stays in
scope. This alternative is source-supported preparation, not an implemented
adapter or proof that its native authority and notifications are ready.

**Retained/reconstructed Samsung authority remains a design option.** Its storage
objects, vold route and current-writer ownership must actually survive or be
established by a reviewed lifecycle. A surviving native daemon alone does not
preserve Java objects. Guest presentation needs authenticated operations/results,
and a coherent read-only storage status view, without a second credential writer.
Neither option proves the whole Samsung server is necessary or a tiny broker
sufficient.

Remaining Stage-1 gates are concrete: loader/registry ownership and duplicate
startup prevention; exact native endpoint/version and caller identity; original
user/HSUM/data/metadata namespace; cache/listener coherence; failure and mutation
recovery. All cross-OS PIN creation/change/removal, fingerprints, encrypted data
and auth-bound key requirements in [GOAL](../GOAL.md) remain mandatory.

Recheck frozen evidence with `python -B tools/audit_storage_linkage.py --report`.
`--capture` and `--close-edges` issue only their bounded missing static reads.
The failed initial query for `android.os.storage.StorageManagerInternal` published
no receipt; the correct guest declaration is `com.android.server.StorageManagerInternal`.
No Android, OEM class, native code, phone action, storage mutation or runtime
security acceptance occurred.
