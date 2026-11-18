# Original LSS permission binding across the process boundary

The selected Samsung permission path needs **Samsung AM transaction 287→actual
ColorOS 264**, plus explicit source-local permission-cache preparation and genuine
caller/state ownership. Replacing LSS permission checks with an allow callback,
a package-table copy or a new self identity would lose the original contract.
The separately [prepared one-method bridge](samsung-permission-bridge.md) handles
that wire conversion; its unselected build is not installation or live authority.

This source card pins 65 bodies and 78 selected instruction assertions in the
[inventory](../inventory/authority-permission-binding.json). Replay:
`python -B tools/audit_authority_permission_binding.py`. Original framework/service
inputs remain Samsung `8095a9ae…71fe`/`def967fb…639f6`, ColorOS `d5c6b7fd…bcd2`/
`66d0d51d…edf3`. Raw bodies remain ignored. No OEM, Android, native Binder or
permission-state code ran; no phone or permission change occurred.

## Real original checks and subject provenance

Samsung LSS checkReadPermission/checkWritePermission both call the actual
Context's `enforceCallingOrSelfPermission(ACCESS_KEYGUARD_SECURE_STORAGE,...)`
at PC8. checkDatabaseReadPermission(user,key) calls hasPermission for that same
permission, then throws SecurityException on denial. Its user/key arguments
appear in denial text; this body is not an independent user/profile admission
gate. hasPermission accepts only the original Context result0.

The actual Samsung ContextImpl path is:

| Step | Exact observed source |
| --- | --- |
| Capture subject | checkCallingOrSelfPermission calls canonical Binder.getCallingPid at PC2 and getCallingUid 6, then checkPermission(permission,pid,uid) at10. |
| Preserve Context policy | checkPermission retains the ContextParams renounced-permission denial for its own PID/UID, resolves device ID and calls PermissionManager.checkPermission with the original permission/PID/UID. |
| Resolve selected device | The source device-aware set is CAMERA/RECORD_AUDIO or empty. ACCESS_KEYGUARD is outside it, so the original resolver returns device0. This is permission-specific, not authority to rewrite arbitrary device IDs. |
| Enforce result | Original ContextImpl.enforce returns only for result0; otherwise throws SecurityException at94. |

The reused [native caller proof](binder-direct-dispatch-source.md) identifies
getCallingUid/getCallingPid as public-static-final **native**, flags`0x119`,
with no Java body proving kernel identity. The existing33-route direct dispatch
does not clear identity or hop threads, but that alone is not native caller
acceptance. Keep actual canonical Binder/Parcel and the original caller before
the service's own legitimate identity changes. A local or cleared-self call can
observe a different subject. Never repair that by substituting an arbitrary UID,
authority PID, package name or WorkSource. Feature caller/user/profile/operation
admission remains independent of a permission result.

## Exact reached protocol

PermissionManager's uncached method calls
`IActivityManager.checkPermissionForDevice(permission,pid,uid,deviceId)`.
The original ActivityManager singleton factory looks up literal `activity`
(getService PC2/asInterface 6). It does not know that its captured Samsung Proxy's
transaction numbers differ from the actual ColorOS service.

| Wire item | Samsung | ColorOS |
| --- | --- | --- |
| Code | 287 | 264 |
| Token | `android.app.IActivityManager` | same |
| Payload | nullable String using **writeString/readString**, then PID int, UID int, deviceId int | same order and original argument provenance |
| Flags | synchronous 0 | synchronous 0 |
| Result | original exception envelope, actual int result | same |
| Root token enforcement | PC10 | PC18, after entry register moves |
| Root dispatch | case799→private helper | case332 |
| Argument reads | helper0/4/8/12 | 332/336/340/344 |
| Trailing-data check / method call | helper16/19 | 348/351 |
| writeNoException / writeInt | helper23/26 | 355/358 |

Both actual Stubs and both Proxies are pinned. String8 is not the selected API.
Preserve null and every subject integer. Guest 287 has no actual switch case and
falls to Binder; it is not the permission call. Legacy checkPermission is code 9
in both inputs, but **is not this reached uncached call**. No general AM numeric
pass-through follows from either observation. The bridge's transact boolean is
handled/refused, not the permission int or authentication success.

## Actual ColorOS decision and state owner

The query's payload PID/UID remain the original subjects even though a remote
outbound Binder hop observes the authority process as its transport caller.
ColorOS AMS denies null permission. Its component checker receives
(permission,pid,uid,deviceId,owningUid=−1,exported=true) and:

1. Grants when the **supplied PID** equals AMS.MY_PID.
2. Executes its actual vendor safe-window permission hook.
3. Reads actual per-process deniedPermissions and can deny.
4. Calls the genuine framework component/UID/isolated/exposure rules and
   permission-manager path.

Preserving PID is therefore necessary. A direct shortcut to a package/permission
table, or even directly to IPermissionManager, omits reached AM policy.

The remaining path is wholly guest protocol: AppGlobals→ActivityThread's cached
`permissionmgr` interface→IPermissionManager.checkUidPermission(uid,permission,
deviceId), proxy code31/flags0. PermissionManagerService maps device0 to the
original persistent ID`default:0`, retains its actual vendor skip/hook and
optional CheckPermissionDelegate, then invokes its LocalServices-provided
PermissionManagerServiceInterface. Captured AccessCheckingService.onStart
creates/publishes the real PermissionService for that interface; PermissionService
uses actual users, packages/SystemConfig, AccessCheckingService.state and the
original permission policies. Publication alone does not prove initialized state.

Bind the already initialized actual guest owners. Do not construct a replacement
PermissionManagerService, copy requested/granted package entries or initialize
an empty AccessState in the Samsung process. Actual installed OneOS modifications,
active APEX/class definitions, hooks/delegates and namespace behavior remain
profile/runtime admission work. The observed source chain does not identify
today's effective loaded implementation or certify stock permission isolation.

## Original shortcuts and exact cache preparation

Samsung PermissionManager first computes appId as UID `%100000` and returns
GRANTED0 for appId 0 or 1000 **before cache/AM IPC**. This uses app ID, not only
literal UID1000. Preserve the real source check, but do not treat its shortcut as
proof of the dedicated process, authorized operation or actual guest per-PID
state. The feature's own caller/role/user/operation gate still applies.

For other subjects the original 2048-entry permission cache stores permission,
PID, UID and deviceId in PermissionQuery. **equals/hash omit PID** and use only
permission/UID/deviceId. A hit is not evidence that the actual guest's current
per-process restrictions were evaluated.

A source-supported preparation option is the original
`PermissionManager.disablePermissionCache()` in the admitted Samsung client
realm, before its first admitted check. The exact selected chain is:

- sPermissionCache.disableLocal→disableForCurrentProcess→disableLocal(cacheName).
- Under the local static registry lock, disable each matching named cache and
  record that name in local sDisabledKeys. This is the local **checkPermission
  name group**, not a promise to affect only one object if several share it.
- disableInstance sets mDisabled, clears local entries and increments the clear counter.
  CacheMap.clear clears its actual SparseArray. Disabled query takes the original
  recompute path, whose PermissionManager$1 callback forwards the original fields
  to the real AM query.

The exact `isReservedNonce(J)Z` helper closes that last branch: PCs0..10 test
the inclusive range 0..3, PCs12/13 return true, and PCs14/15 return false.
Query uses nonce1 at PCs4/13 when disabled, classifies it at PC14, branches
at PC18 to the second classification at PC28, then falls through PC32 to
mDisabled at PC34 and branches at PC36 to recompute PC54. This is a static
control-flow deduction. The earlier 64-body freeze is preserved under
`out/authority-permission-binding/history-initial-freeze/manifest.json`; this
revision adds the missing helper and assertions without changing the bridge.

These bodies do not change permission grants, remote state or system properties.
This is a proposed **process/source-local preparation**, not an executed action,
global permission change or hidden behavior inside the transport bridge. If
retaining cache instead, genuine invalidation/currentness and per-PID semantics
need their own proof. Local disable still preserves the original appId 0/1000
shortcut and does not replace independent feature admission.

Preparation requires actual cold or quiesced **same-realm** PermissionManager/
cache ownership, with no earlier in-flight bootstrap query or stale accepted
result. Disable is not an outstanding-query/result drain: an earlier query may
still return its result afterward. Disabling new calls does not repair decisions
already accepted or permit a hot endpoint/code-generation replacement.

## Prepared binding proposal and remaining gate

Prepare against the actual current guest AM publication and its permission-state
owner, retaining their exact source/profile, process/native and user generation.
A lookup name, Binder holder, descriptor or generic trusted callback returning 0
is insufficient. Use the same-realm original Samsung Stub.asInterface over the
one-method bridge, with canonical Binder/Parcel. Preserve its fresh owned request,
borrowed reply, actual transact result/errors and original String/three ints.
No grant, denial, fabricated reply, retry or identity clearing belongs there.

The narrow source integration candidate is the original
PermissionManager.checkPermissionUncached `ActivityManager.getService` call at PC0:
it needs a reviewed permission-specific prepared view. Do not globally replace
`activity` or seed a partial general AM singleton that silently defaults other
methods. That installation/source seam, original cache preparation and live
authority composition remain unimplemented by this card. Other reached AM or
Context dependencies require their own real bindings.

Retain the source client/view/target for actual work, child operations and
retirement/death drain. Do not rebind stale cached clients to another generation
or allow source-private calls around the feature retirement owner. Missing or
uncertain ownership stays unavailable. The existing accepted OneOS permissive
SELinux/relaxed privileged-permission limitations remain disclosed; this work
adds no global Enforcing prerequisite and establishes no live security outcome.
