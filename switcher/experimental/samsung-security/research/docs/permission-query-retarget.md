# Narrow Samsung permission-query supplier proposal

Retarget only Samsung `PermissionManager.checkPermissionUncached(String,int,int,int)`
PC0 from `ActivityManager.getService()` to a new BOOT-visible
`PermissionQueryBinding.get()`. Both return the same admitted Samsung
`android.app.IActivityManager`, take no arguments and use `invoke-static` with
three code units. This is a source-supported proposal before implementation;
no helper, patched framework or live binding is produced.

## Exact original edge

Original framework SHA256 is
`8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe`.
The private static target has access flags0xa and body SHA256
`9337df69165b01e95e5f834e89cd4cc4ed9abc86008f20493d0aa5aab63877fe`.
Its original DEX039 location is classes3.dex, method51996, code4292828,
instructions4292844, with 49 code units, six registers and four incoming words.
PC0 occupies bytes[4292844,4292850), using method reference16 and zero argument
registers. The original DEX header, SHA1 signature and Adler32 verify.

PC3 moves the result to v0; null reaches the actual denial−1 at PCs33/34.
PC38 invokes `checkPermissionForDevice` with v0 and the untouched permission,
pid, uid and deviceId arguments. The existing RemoteException region covers
PC36 through exclusive42, with handler43; it does not cover PC0. A proposed
unready getter throws `IllegalStateException` at that original call position.
That is unavailable/error propagation, not a permission grant or proof that the
outer UI/bootstrap has implemented safe unknown-state handling.

The exact direct-reference query finds one caller in this captured framework:
the synthetic `PermissionManager.-$$Nest$smcheckPermissionUncached` accessor.
Its body forwards all four arguments. The retained original
PermissionManager$1.recompute reads permission/pid/uid/deviceId and invokes that
accessor at PC8. The xref does not cover reflection, other archives or an
installed OneOS image. Original ActivityManager.getService and Samsung
Stub.asInterface are public static; IActivityManager is a public abstract
interface with the public abstract selected query. The target remains private;
no visibility change to Samsung PermissionManager is proposed.

## Proposed helper API and binding

Public final class:
`com.appleexploit.oneos.security.boot.PermissionQueryBinding`

| Member | Contract |
| --- | --- |
| `public static void bindOnce(android.os.IBinder)` | Cold bootstrap supplies the exact sourceProtocolBinder from the separately admitted frozen PreparedSamsungPermissionBridge. Reject null; enter BINDING before conversion through the original Samsung Stub.asInterface; publish BOUND only after success. Any failed attempt is terminal. |
| `public static android.app.IActivityManager get()` | Return the retained exact typed view only when BOUND; otherwise throw. No lookup, external callback, identity change, policy substitution or fallback on this query path. |
| Private constructor/state | One retained process-lifetime view; UNBOUND/BINDING/BOUND/FAILED; no reset, hot rebind or general AM API installation. |

Both methods require public access: the original caller is in android.permission,
while the real bootstrap may have an app loader and different runtime package.
Public access is not an owner ACL. The bootstrap must admit the exact frozen
bridge code/class/object, actual retained guest AM/state generation and the
supplied Binder before binding. An arbitrary Binder, descriptor, UID, reflected
name or interface type cannot attest that owner. The helper has no static
reference to the app-only PreparedSamsungPermissionBridge class. It consumes
canonical IBinder and stores the original Samsung interface view. Root must
review this API and its ownership integration before code.

## Loader and cold preparation requirements

The helper must be genuinely visible to the original caller's BOOT loader before
first use. An app child loader cannot satisfy a boot parent's new reference.
Its IActivityManager/Stub/Proxy family must be the exact Samsung protocol family
also resolved by the original PermissionManager. A same-name guest interface is
not an interchangeable type or wire protocol. Canonical Binder/IBinder/IInterface,
Parcel, exceptions and Java primitives remain the admitted platform identities.
Compile-only hidden API declarations, if needed, must match those descriptors
and be excluded from the helper DEX. Actual BOOT insertion, loader delegation,
artifact admission and bootstrap invocation remain unassembled.

Before any admitted check, use the original same-realm process-local
PermissionManager.disablePermissionCache under the corrected
[permission binding contract](authority-permission-binding.md). This requires
cold/quiesced ownership with no earlier in-flight query or stale accepted result;
disable is not a drain. The original appId0/1000 shortcut remains before IPC.
Neither the helper nor the bridge installs a partial ActivityManager singleton,
changes global activity lookup, copies permission state or creates a grant.
Native caller and feature role/user/operation admission remain separate gates.

External call admission and real drain must retain helper, bridge and actual
endpoint through original queries and nested work. A reference already returned
by get cannot be revoked by clearing a field. This proposal permits no hot
endpoint replacement; retirement stops admission, drains and ends the owned
process lifetime. No constructor, cache or native operation ran for this report.

## Future producer admission

The helper owner/type and proposed method reference are absent from the original
classes3.dex. Its 65,412 method IDs leave 124 slots below 65,536. The getter's
instruction shape fits, but a new sorted reference-table entry and affected
index/offset remapping are still required. This is not an existing-reference
six-byte patch, and no output method ID or offset is invented here.

A future producer must independently decode output and preserve all original
definitions and every other method's symbolic instructions, operands, branches,
try/payload/debug contracts and non-DEX entries. Only target PC0 may change its
symbolic call; register shape, result, null/error/real-query and catch paths remain
original. Prove table/index consistency, unchanged bytes outside explicitly
admitted structural relocations, exact inverse/roundtrip and DEX integrity. Do
not reuse the earlier byte-only NOP-leaf preservation claim for this different
rewrite. A separately reviewed lowering is required if the producer cannot
establish those conditions.

`python -B tools/audit_permission_query_retarget.py` replays literal source pins,
actual original bytes, API visibility and the bounded caller proof. It writes
derived metadata only. The corrected65-body permission card, prepared bridge,
global ActivityManager state and public33 credential routes remain unchanged.
