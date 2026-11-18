# Prepared storage contract: bounded source-to-code cut

**Result:** the selected Samsung LSS coupling can be expressed as two synchronous
storage mutations plus a coherent status query. The proposed DEX edits need one
original LSS class and a new authored contract type; they do not require starting
Samsung StorageManagerService. This is a checked **retarget plan**, not an
implemented helper, generated DEX, native binding or runtime admission.

The [inventory](../inventory/storage-contract-adapter.json) pins reused evidence,
the exact field-reference scans and proposed instruction/register changes.
[The audit tool](../tools/audit_storage_contract_adapter.py) validates source hashes
and replacement boundaries. `--collect` issues only the bounded missing source
queries; otherwise it reuses their receipts. All raw methods remain ignored.
The existing [storage linkage](construction-storage-linkage.md),
[state](construction-state.md) and [user binding](security-user-binding.md)
obligations remain in force. No private state, phone, OEM class or native code ran.

## Minimum contract for root review

Proposed private helper descriptor:
`Lcom/appleexploit/oneos/security/storage/PreparedStorageContract;`

```java
interface PreparedStorageContract {
    void setCeStorageProtection(int userId, byte[] secret) throws RemoteException;
    void unlockCeStorage(int userId, byte[] hardwareAuthToken, byte[] secret);
    boolean isCeStorageUnlocked(int userId) throws RemoteException;
}
```

`RemoteException` is the real canonical Android exception. Protection preserves
the original checked native failure until LSS handles it; unlock preserves the
concrete implementation's conversion to RuntimeException. The interface is
internal to admitted original operations, not a public arbitrary-secret/HAT or
user-selecting IPC API. No shared interface or runtime code is created here;
root must approve the ABI/publication before implementation.

The backend owns genuine Samsung vold identity, current writer/user/generation,
HSUM/encryption policy and coherent status. There is no caller-supplied HSUM
argument, default getter or readiness boolean. Source Lifecycle.onStart captures
actual `UserManager.isHeadlessSystemUserMode` at191 into its implementation's
`isHSUMMode`195. A replacement must obtain and retain the corresponding admitted
policy; passing `false` merely to satisfy a signature is invalid.

## Original policy and borrowed buffers stay in LSS

Preserve these exact original decisions; the adapter does not rederive secrets:

| Path | Source behavior retained |
| --- | --- |
| Virtual users | Both LSS methods return before derivation/backend access. Preserve genuine user policy; do not invent a physical user from a numeric match. |
| Protection | Derive SP FBE secret at9 into register5. Genuine DualDAR, except device-owner mode, fetches the outer-layer key at73 into register0; call uses that key. Otherwise call uses register5. Protection directly calls vold for nonvirtual users; no new `isFileEncrypted` shortcut is introduced. |
| Unlock secret | Early return if coherent status already says unlocked. Derive SP FBE secret at48 into register2; genuine non-device-owner DualDAR can replace register2 at119. Preserve that exact value, including original null/error behavior; never substitute a default secret. |
| Unlock verification/HAT | Keep same-SP/user `verifyChallenge`131 even when the subsequent native HAT is null. HAT is selected only when firstAPI≤30, user0 or enterprise-and-not-SecureFolder, and response nonnull. That branch obtains HAT157, rejects a null object161/169, then calls165. Other cases pass explicit null179/180. A nonnull empty array is not rejected by that LSS test. |
| Buffer cleanup | Protection zeroizes derived register5 at124/128; in the outer-key branch that is not the transmitted register0. Unlock zeroizes its current register2 at213/233/237. Do not claim those paths wipe every discarded derived array, HAT or outer-key allocation. |

The mutation contract consumes the borrowed arrays synchronously before the
original call returns. It must not retain, mutate, log or queue them. Original
HAT formatting uses a newly allocated String; this plan does not claim that
immutable copy or every native buffer is zeroized. If a future design needs any
additional owned copy, it needs explicit consumption, completion, cleanup and
zeroization ownership, including exceptional/uncertain progress. An asynchronous
adapter returning while it still uses LSS's borrowed secret is invalid.

## Native operations and status

The source-backed native projection needs no Samsung-specific Parcelable object:
only the real Binder endpoint and canonical primitive/String/array operations.
It can therefore be prepared as a narrow authored Samsung-protocol marshaller
without importing the incompatible whole guest IVold proxy or storage service.
That marshaller remains unimplemented and must not run before actual endpoint,
caller, native-version and state admission.

| Actual Samsung operation | Code / flags | Request and response |
| --- | --- | --- |
| `setCeStorageProtection(I[BZ)V` | 46 /32 | interface token, user int, exact selected secret, genuine HSUM boolean; read reply exception |
| `unlockCeStorage(ILjava/lang/String;[BZ)V` | 60 /32 | token, user, original HAT text, exact secret, HSUM; read reply exception |
| `getUnlockedUsers()[I` | 59 /32 | token only; read reply exception and int array; candidate for a fresh encrypted-backend status view |

All three captured proxies call `Parcel.markSensitive` and recycle request/reply
on normal and exceptional paths. Preserve numeric flags32 and sensitive-buffer
treatment, not ordinary flags0. The descriptor is `android.os.IVold`. Captured
ColorOS protection54/unlock56 have different signatures and omit HAT/HSUM;
matching the descriptor cannot justify using them against Samsung vold.

Original concrete unlock first tests actual `StorageManager.isFileEncrypted`.
On its encrypted branch it maps null **or empty** HAT to `"!"`, otherwise uses
the original HexDump default uppercase encoding of the whole array, and calls
Samsung vold. Only after normal completion does it append the user under its lock
and invalidate user-unlocked/volume-list caches. Its genuine unencrypted branch
can update Java state without a vold call. Do not obtain this policy from an
unverified guest property/default or force either branch for convenience.

The existing Samsung `isCeStorageUnlocked` is Java cache membership under a lock,
not cryptographic proof. LSS uses it to skip unlock work. The proposed contract's
status must describe the same actual user/backend/generation as its mutations.
Native `getUnlockedUsers` is already used by original connection code and is a
source-supported encrypted-backend query candidate; it is not, by itself, exact
equivalence to the original cache's unencrypted branch or a complete cache/
listener/relock/reset design. Guest public storage and UserManager status views
also need alignment. A stale guest `true` must not skip required host work.
Do not solve that by starting another SMS that installs a vold listener or resets
the retained daemon; those active takeover effects are pinned separately.

## Exact original-class edit plan

The original field is public-final flags17. An exact whole-services scan now
confirms only five direct uses, all in LSS; the supplied Samsung framework has
zero direct references to that field. This closes the direct public-field concern
within these two archives, not reflection/JNI or arbitrary other loaders.

Change the field descriptor to PreparedStorageContract while preserving its name
and access flags. The constructor ABI stays unchanged. Proposed same-size edits:

| Original decimal PC(s) | Proposed change |
| --- | --- |
| Constructor643 /649 /651 | Contract `const-class`, contract `check-cast`, and same field name with new descriptor. Keep actual LocalServices lookup645. |
| Protection83 /105 | Read the retargeted LSS field into the same register3; retain existing `Object.getClass` null checks85/107. |
| Protection `[88,97)` | `invoke-interface {v3,v4,v0}, Contract.setCeStorageProtection(I[B)V`, followed by six one-unit NOPs. |
| Protection `[110,119)` | Same call with `{v3,v4,v5}`, followed by six NOPs. |
| Unlock163 /177 | Retarget the field reads into register5. |
| Unlock165 /180 | Replace concrete `invoke-virtual` with contract `invoke-interface`, same `{v5,v6,v7,v2}` and `(I[B[B)V`. |
| Status0 /2 | Read the retargeted contract field instead of `mStorageManager`; call contract `isCeStorageUnlocked(I)Z` with unchanged registers and result/RemoteException handler. This deliberately adds a sixth read of the new contract field. |

These13 instruction spans cover the original eight concrete-owner references,
five original field uses, both outer `mVold` accesses and the additional status
projection. The two protection spans remove outer/HSUM field peeks; the prepared
backend supplies their real semantics. All remaining branches, logging, SP/DAR/
verification calls, source exception handlers and zeroization PCs stay unchanged.
The audit verifies contiguous equal-size spans and no branch/try/handler boundary
strictly inside them. Original registers fit the proposed invocation encoding.
It does not emit or verify a rewritten DEX.

Before selection, the producer must also prove register types, method/type/field
index bounds, interface definitions, complete exact caller closure, unchanged
foreign definitions, inverse reconstruction and whole-container DEX041 correctness.
NOP padding only addresses instruction positions; it is not verifier or Android
acceptance. The old `mStorageManager` field/acquisition can remain untouched for
inverse preservation; the selected full LSS bodies call IStorageManager only from
the retargeted status method. No claim removes that Binder's other runtime owners.

## Publication, errors and remaining ownership

Publish the real prepared contract under the **same Class object** used by LSS's
const-class/cast, in the one canonical LocalServices registry, before any eager
LSS construction. Preserve duplicate-registration refusal. Do not use a private
copy of the registry, replace the guest storage service, fabricate a concrete SMS
instance or defer state admission until constructor PC643. A nullable lookup/cast
is not readiness. The root-owned factory must already retain the actual code,
resource, user/state/native and current-writer owners through partial construction.

Canonical `RemoteException.rethrowAsRuntimeException()` is now body-closed on both
frameworks: it constructs RuntimeException(cause) and throws. Consequently native
unlock failure does not fall through to the cache update. Protection's original
RemoteException handlers run inside the original cleanup contour. LSS unlock,
however, catches RuntimeException, logs, zeroizes and **returns void**. LSS status
logs a RemoteException and returns false. Neither normal return nor that false
value can be promoted into actual mutation/data readiness or safe retry.

The real owner needs an independent admitted operation disposition and recovery
gate. Native work can commit before response loss or retirement; a failed
post-check does not undo it. Unknown progress must retain state/backend owners
and block competing writes/replay until genuine reconciliation. No public
caller-provided readiness flag or default getter is proposed. The synchronous
[dispatch lifetime owner](dispatch-call-ownership.md) can retain a call/anchor;
its zero count is not storage, Binder, callback, thread or native drain.

This prepares a narrow genuine adapter cut without requiring whole SMS startup.
Actual interface/provider implementation, endpoint/policy identity, state paths,
guest status alignment, native completion/recovery, generated DEX proofs and
device acceptance remain open. Original OneOS key-preservation guards are not
disabled by this plan, and optional OPPO-only features do not become dependencies.
