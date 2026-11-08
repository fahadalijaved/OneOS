# Bootstrap gate D: original-vold storage owner

**Disposition: blocked on a genuine live provider.** The finite source cut is
closed for the selected Samsung protocol, native status disposition and policy
inputs. No current original-vold endpoint/user/policy owner is supplied by the
existing bootstrap. Root directed this gate to remain source/API-only: another
unselected marshaller would not resolve that missing owner. No helper, runtime
interface, native call, secret read or device action was added.

[The inventory](../inventory/authority-bootstrap-storage.json) separates source
facts, required provenance and explicit blockers. The authored
[audit tool](../tools/audit_authority_bootstrap_storage.py) reuses frozen Java
proofs and verifies selected bytes of captured Samsung vold. Its static ARM64
inspection uses the existing pinned PC Capstone tool; no OEM ELF/JNI executes.
The11 bounded native functions include the native dispatcher as context for
three selected cases, not a claim to audit every vold operation or its complete
cryptographic dependencies. No live native policy-map values were acquired.

## Actual endpoint protocol and native receiver

The captured Samsung `/system/bin/vold` is1,490,936 bytes, SHA256
`0b00f386f2056aebd3e0824f67cba35614fdc6e2d2b11414ae34d5a2c33bebb7`.
It is the individually verified OS-capture member, not an identified live process.
The exact original Java proxy and native Binder dispatch agree:

| Operation | Transaction | Native receiver |
| --- | --- | --- |
| Protection `(I[BZ)V` | 46 | VoldNativeService.setCeStorageProtection at `0x9d264` |
| Native status `()[I` | 59 | VoldNativeService.getUnlockedUsers at `0x9d3d0` |
| Unlock `(ILjava/lang/String;[BZ)V` | 60 | VoldNativeService.unlockCeStorage at `0x9d49c` |

The native dispatch table uses code-minus-one, a16-bit entry and scaled offset.
Cases46/59/60 resolve to their actual virtual slots `0x188/0x1f0/0x1f8`.
The service's installed vtable address point and those function pointers are
checked against the exact start instructions, file bytes and RELR relocations.
This corroborates the proxy codes against the real captured native receiver.
It does not establish what a currently named Binder refers to.

The original proxies mark request Parcels sensitive, use numeric transaction
flags32, read reply exceptions and recycle request/reply on all exits. Preserve
their argument order, native errors and lifetime behavior. The required endpoint
is framework service `vold` / descriptor `android.os.IVold`. Captured ColorOS's
protection54/unlock56 have incompatible arguments. The vendor/default service
name used in OneOS checks is process corroboration; it must not be assumed an
interchangeable framework-protocol endpoint.

**Do not send even status59 as a version-identification probe to an unidentified
Binder.** On another implementation, that transaction number can mean another
operation. Name, descriptor, ping, source strings or a constructed proxy do not
attest the receiving process/image/protocol generation.

## What native status actually says

The captured wrapper first calls `CheckUidOrRoot(1000)`, takes VolumeManager's
mutex, calls `fscrypt_get_unlocked_users`, returns its int vector with Binder
status, then unlocks. The check reads actual Binder calling UID; it accepts1000
or0 and otherwise builds an error. Both OSes can run system code as UID1000, so
this is not host/user/policy provenance and cannot authorize a public forwarding
service by itself.

The status helper iterates the daemon's native policy tree rooted at static
address `0x164a10`, copying node user IDs into a vector. The selected fscrypt
unlock installs a storage key before adding policy state; lock passes that same
tree to its eviction helper. The eviction helper's symbol identifies the map's
`UserPolicies` value type. This is the original daemon's tracked unlocked-policy
disposition, rather than Samsung or guest Java cache membership.

It is not fresh authentication, proof of CE file usability, newly committed
credential protection, app-key acceptance, persistence or native drain. Its
meaning is tied to that actual daemon generation. Restart/death/replacement is
not permission to reconnect by name and reuse the former generation's state.
An empty result is distinct from an unknown/failed response; no null/error-to-empty
conversion is proposed. The original Java unencrypted path can update Java state
without populating this native tree, so native status is not an exact replacement
for every unencrypted-cache case.

## Genuine policy inputs and original behavior

| Input | Exact selected source | Required provenance |
| --- | --- | --- |
| Encryption | Java `isFileEncrypted` first checks `isEncrypted`, then cached RoSystemProperties.CRYPTO_FILE_ENCRYPTED. CryptoProperties reads `ro.crypto.state/type`; defaults include UNSUPPORTED/NONE. Native `IsFbeEnabled` uses `property_get("ro.crypto.type", …, "none")` and compares `file`. | Same original property view and admitted profile/generation, not a guest cached/default false value or caller-provided boolean. |
| HSUM | SMS's original initialization captures UserManager.isHeadlessSystemUserMode. The framework caches a global `user` Binder query; the actual service computes `!UserInfo(0).isFull()` under its users lock. | Genuine registry/lifecycle owner C and applicable policy owner F; endpoint/alias evidence B does not mint these. A guest user0 record or absent-state fallback is insufficient. |
| Selected user | Native calls take only the numeric user ID; native status returns only IDs. | Same authoritative user/profile/serial, protector and physical CE/key namespace used by LSS/SPM. Neither numeric user0 nor map membership supplies that mapping. |
| First API | LSS constructor reads `ro.product.first_api_level`; its original unlock body uses that captured value when selecting a HAT. | Actual admitted original policy value, not donor properties, missing-property defaults or a force-null rewrite. |

The [frozen adapter cut](storage-contract-adapter.md) preserves original SP-derived
and genuine non-device-owner DualDAR secret selection, HAT/null routing and exact
existing cleanup contours. Those borrowed arrays must be consumed synchronously.
Original cleanup does not establish a wipe of every outer-key, discarded derived
array or immutable HAT String; this gate adds no such claim.

One additional native constraint is now explicit. Native unlock examines the token
String: empty or single `!` proceeds to fscrypt; other text produces service-specific
error−22 before that unlock call. The Java concrete path maps null/empty HAT arrays
to `!` and nonempty arrays to uppercase hex. Therefore the original legacy HAT
branch's compatibility depends on the actual first-API/profile. Preserve that
branch; dropping HAT or forcing null to hide an incompatible policy is invalid.
No real HAT was inspected or sent.

Native key-operation failure produces real Binder status. Java proxy `readException`
preserves it; native RemoteException conversion and LSS's original RuntimeException
catch/log/void-return remain as pinned. A normal LSS unlock return is not a storage
commit receipt. A lost response or failed post-check can follow a committed native
change. User membership alone cannot reconcile uncertain protection of a credential
secret; no universal readonly proof or hardware rollback is established here.

## Required prepared owner and why D remains blocked

The proposed internal contract remains:

* `setCeStorageProtection(I[B)V` with original checked RemoteException boundary;
* `unlockCeStorage(I[B[B)V`, HAT then secret, with original runtime conversion;
* `isCeStorageUnlocked(I)Z` from a coherent original-user/backend view.

It must be backed by a genuinely acquired original endpoint/proxy and retained
code, actual user binding, policy and operation-disposition owner. The original
proxy already preserves the wire protocol. A prepared exact invoker can use it
without constructing/borrowing a Samsung SMS, installing its listener or resetting
vold. A new raw-Binder wrapper, arbitrary admission callback, UID check, opaque
anchor or `ready` flag cannot establish those inputs.

Current OneOS source has a conditional `gvld` branch. It records/checks the host
init vold PID, compares service-manager PIDs, checks guarded native/framework
markers and rechecks host names before guest framework startup. Its fallback
starts guest vold under `vold`. These are concrete producer/guard paths; the
installed branch, bytes, PID/namespace and returned Binder handle are unverified.
No existing trusted process owner currently joins those checks to a retained
original endpoint and the admitted registry/lifecycle C and policy F owners.

The missing bootstrap must perform that acquisition before guest name replacement
and before any eager LSS work, using internally verified profile/process/image/
namespace/generation provenance rather than caller-provided hashes or receipts.
It must preserve the original daemon and OneOS key guards, hold one credential
writer, reject death/replacement without fresh admission, and align guest public
status/user caches with actual key/data ownership. Unlocking a host key does not
prove that staged guest app data has the intended CE policy or becomes accessible.
No whole-`/data` bind or fresh user/key creation is proposed.

Finally, native/Java callbacks, caches, in-flight operations and uncertain commits
need owned quiescence and reconciliation across return/reboot. The existing
[call-lifetime owner](dispatch-call-ownership.md) supplies none of those backend
acknowledgements. Repeating a mutation, resetting vold, replaying a stale database
or making raw-secret backups is not a recovery design.

D is therefore **source/API prepared, live-provider blocked**. Once the selected
bootstrap provides those real dependencies, root can approve the exact contract
implementation and its tests. No current hardware, Android, security or device
acceptance follows from this card.
