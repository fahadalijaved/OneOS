# Independent authority permission-binding review

Status: accepted as a corrected bounded source-binding proposal. Actual
installation, caller/cache/endpoint admission and runtime acceptance remain open. No runtime code, converter or permission action is part of this review.
The implemented one-method permission bridge and previous reviews remain frozen.

The card correctly preserves the original permission check rather than replacing
it with a grant callback. Samsung Context captures the actual canonical Binder
PID/UID and passes the full original subject through its renounced-self and
permission-specific device resolution. ACCESS_KEYGUARD_SECURE_STORAGE resolves
device0 under the selected original set; arbitrary device IDs must not be forced
to zero. Native getter declarations and a same-thread dispatcher do not prove
kernel caller identity or current installed behavior. The LSS database-read
user/key denial text is not an independent user/profile authorization gate.

## Protocol and genuine policy owner

Samsung checkPermissionForDevice287 becomes guest264, String/readString plus
PID/UID/deviceId ints, synchronous0 and original exception/int reply. Original
root token checks are SamsungPC10 and guestPC18. The Samsung selected branch
calls its private helper; guest332 directly decodes the same subjects. Guest287
has no selected case, and the matching legacy code9 does not replace the reached
API. The frozen bridge preserves the exact query and actual handled/error result;
its compilation does not install or authenticate a target.

Remote transport sees the authority process, while explicit queried subjects
remain unchanged. Guest AMS's supplied-MY_PID grant, safe-window hook and real
per-process deniedPermissions precede the framework path. Directly querying
IPermissionManager31 or copying package grants would skip this policy. The
remaining guest path retains actual permissionmgr publication, hooks/delegate,
LocalServices PermissionService, AccessCheckingService state, users, packages
and permission policy. A service name, published interface or fresh empty
AccessState is not an initialized owner. Installed OneOS hooks/APEX/UID behavior
remain unverified; accepted platform limitations do not supply admission.

Samsung grants appId0/1000 before IPC; this is appId modulo100000, not just full
UID1000. Keep the real source behavior while independently admitting the feature
caller/role/user/operation. A result0 is neither backend identity nor hardware
authentication. PermissionQuery stores PID but equals/hash omit it, so a cache
hit cannot establish that current guest per-PID policy was evaluated.

## Exact local cache control

Original PermissionManager.disablePermissionCache delegates to the same-realm
cache's disableLocal, disableForCurrentProcess and named local registry. It
sets matching cache instances disabled, records the local name group, clears
entries and increments mClears. CacheMap.clear invokes SparseArray.clear. It
does not reset every statistic. The inspected selected chain changes no remote
permission or system property; that does not prove arbitrary class initialization
is inert. The named group can include more than one same-name local cache.

Disable is not an outstanding query/result drain. A query can have obtained a
result before disabling and return afterward. The author incorporated explicit
cold/quiesced same-realm ownership, no earlier in-flight query/stale accepted
result and no hot generation repair. This is an external preparation condition,
not an extra operation hidden in the wire helper or a global permission fix.
The original appId shortcut remains even with the cache disabled.

One tiny support edge was absent from the first frozen source scope: disabled
query selects nonce1 before calling private isReservedNonce(J), whose result
governs the recompute path at54. The actual helper must classify1 as reserved;
AOSP expectation or a method name is insufficient captured-source evidence.
The author added the exact ten-instruction helper and query-branch assertions.
I independently checked its raw hash, comparisons against0/3 and true/false
return branches: nonce1 is reserved. This closes the source deduction to
recompute54. The initial64-body snapshot is preserved and superseded by the
65-body card; no bridge change was needed.

## Implementation and acceptance boundary

A concrete source-local control exists; invocation and readiness are still
unimplemented. The narrow original checkPermissionUncached getService call at0
needs its own reviewed prepared permission view. A helper on the app classpath
does not retarget original boot-framework code. Do not replace global activity,
seed a partial general AM singleton or silently rebind stale clients. Real
source/code/endpoint/currentness, permission/cache/native user generation,
operation admission and work/death/retirement ownership remain required.

This reviewer read the authored card, inventory and verifier and inspected saved
discriminating protocol, subject, cache and policy-owner source edges. The source
audit and compiler were not rerun. No original class, Binder/native operation,
cache control, permission-state mutation, phone or Git action ran. No runtime
acceptance, stock isolation, bootstrap or device case is established here.

## Final checks and disposition

The review inventory pins the corrected report/inventory/verifier and actual
producer result. I read the new complete helper and branch assertions, and
checked 25 saved body windows plus that private leaf against their raw/body pins.
The ignored evidence records exact token, disabled-nonce and classification
edges. These are saved-source checks, not an independent full65-body audit;
the author's reported78 assertions were not rerun here. The previous three-file
snapshot's preserved copies and six previous bridge/review pins were verified
unchanged.

Two review qualifications were incorporated before the initial freeze: entry
clear plus clear-counter update, and disable != drain with cold/quiesced
same-realm ownership. The subsequent missing reserved-nonce source edge is now
resolved. No other material source contradiction remains in this reviewed cut.
Accept the concrete local-control/protocol proposal, not a live permission or
security authority. No new Enforcing requirement, global property change,
permission grant, copied cache or relaxed policy is approved. Full reciprocal
PIN/fingerprint, storage/app-key and all device acceptance remain pending.
