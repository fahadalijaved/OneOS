# Required user and Context binding before credential cleanup

**Observed source:** a genuine framework `UserManager(Context,IUserManager)`
client is sufficient to issue the selected user queries; creating another
UserManagerService is unnecessary for that client and can create fresh user
state. The selected client still needs a real authoritative server, compatible
typed results and the additional genuine local policy owners. None is established
live by this audit. This narrows the construction cut; it does not provide a
runnable authority or require copying Samsung's entire UserManager implementation.

[The inventory](../inventory/security-user-binding.json) contains exact caller,
code-unit PC, target, body/receipt hashes and typed proxy cases. Raw implementations
remain ignored under `firmware/security-user-binding/`. Reproduce bounded reads
with `python -B tools/audit_security_user_binding.py --collect`; omit `--collect`
to validate retained receipts and regenerate metadata. All four original archive
hashes are checked before/after. No private user registry, credential/enrollment
state, device, OEM class, Binder or service was accessed or executed.

## The immediate destructive cut

The frozen [credential constructor audit](construction-credentials.md) establishes
that cold RecoverableKeyStoreManager construction calls
`CleanupManager.verifyKnownUsers` before LSS publication. This audit reuses and
checks the actual constructor/cleanup bodies:

* LSS obtains `Context.getApplicationContext()` at decimal PC277, calls
  `UserManager.get(applicationContext)`283 and passes that manager into
  CleanupManager287. Its later own `mUserManager` lookup/store617/623 and SPM's
  separate lookup700/assignment746 do not govern that earlier manager.
* Cleanup reads recoverable DB user serials, calls
  `getSerialNumberForUser(UserHandle.of(user))` at PC71, and conditionally removes
  state or stores serials at86/102/121/128. Original missing-user `-1` and serial
  mismatch have real consequences. A transport failure must not become `-1`,
  zero, an empty list or an invented serial. Genuine removed-user cleanup remains
  legitimate when both original state and policy establish removal.
* `UserManager.get(Context)` calls `getSystemService("user")`. Its serial wrapper
  extracts the UserHandle identifier and queries `getUserSerialNumber(int)`;
  the actual Samsung server reads `UserInfo.serialNumber` under `mUsersLock`,
  returning `-1` when no record exists. Android user number, serial, Linux UID,
  Gatekeeper fake user and hardware SID are different identities.

Admission must therefore establish the original recoverable DB generation and
the same authoritative user/serial registry **before** cold LSS construction.
The original cleanup's contained exception path is not a completed reconciliation
receipt. Constructor return alone cannot establish admission after that failure.

## Exact required surface

Whole-Samsung-services direct-reference scans select the locksettings package
and five actual target types. The inventory lists all198 selected references,
including field/type references. This is direct-reference completeness for those
targets, not full indirect/reflection/JNI closure.

| Actual target | Required declarations from locksettings callers |
| --- | --- |
| UserManager | `get(Context)`, `getUsers()`, `getAliveUsers()`, `getMainUser()`, `getUserInfo(int)`, `getProfiles(int)`, `getProfileParent(int)`, `getProfileIdsWithDisabled(int)`, `getSerialNumberForUser(UserHandle)`, `isQuietModeEnabled(UserHandle)`, `isUserRunning(int)`, `isUserUnlockingOrUnlocked(int/UserHandle)`, static `isHeadlessSystemUserMode()`, Samsung static `isVirtualUserId(int)` |
| UserManagerInternal | `getUserInfo(int)`, `getProfileParentId(int)`, `getMainUserId()`, `getUserProperties(int)`, `isMainUserPermanentAdmin()`, `addMaintenanceModeLifecycleListener(LockSettingsService$1)` |
| SupervisionManagerInternal | `isEscrowTokenRequired(int)`; the actual canonical type is `android.app.supervision.SupervisionManagerInternal` |
| UserInfo | Fields `id`, `serialNumber`, `profileGroupId`, `flags`; `getUserHandle`, `isForTesting`, `isFull`, `isMain`, `isPrimary`, `isManagedProfile`, `isSdpNotSupportedSecureFolder`, `isSecureFolder`, `isSuperLocked`, `isVirtualUser` |
| UserProperties | `isCredentialShareableWithParent()` |

UserManagerInternal is obtained through the actual LocalServices Class key, not
Context/Binder. Required examples include FRP's main user, AuthSecret's user/main
admin policy, credential sharing and post-change user selection. Matching an
abstract declaration does not establish the owner behind it. Samsung's maintenance
listener signature carries its real private LSS callback type; it is absent from
the captured ColorOS interface and is not an ordinary IUserManager operation.
An unchanged reached registration needs its real callback/lifetime owner.

The27 Context callsites in reused selected bodies require nine signatures:
application Context, Resources, PackageManager, ContentResolver, string/class
service lookup, the selected receiver registrations and permission enforcement.
This is a scoped list, not a claim that all future reached Context use is closed.
Resource/policy and receiver ownership remain as recorded in the construction
reports. No optional OPPO-only context service is made mandatory by this list.

## Genuine narrow Binder projection

The actual Samsung registry factory resolves `ServiceManager.getServiceOrThrow
("user")`, decodes `IUserManager`, then constructs the client. The genuine client
constructor stores the supplied service, application Context and Context user ID,
and creates caches; its selected body does not create a user or user data.

All11 required remote projections have the **same selected transaction code and
Parcel operation signatures** in the captured Samsung/ColorOS frameworks. They
all use ordinary synchronous transact flags0. No code-number mismatch is invented
for this interface.

| Exact operation | Samsung / ColorOS code | Payload |
| --- | --- | --- |
| `getMainUserId()` | 19 /19 | int result |
| `getUsers(boolean)` | 23 /23 | UserInfo list |
| `getProfiles(int,boolean)` | 24 /24 | UserInfo list |
| `getProfileIds(int,boolean)` | 25 /25 | int array |
| `getProfileParent(int)` | 32 /32 | nullable UserInfo |
| `isHeadlessSystemUserMode()` | 34 /34 | boolean |
| `getUserInfo(int)` | 36 /36 | nullable UserInfo |
| `getUserSerialNumber(int)` | 46 /46 | int, widened by the client wrapper |
| `isQuietModeEnabled(int)` | 65 /65 | boolean |
| `isUserUnlockingOrUnlocked(int)` | 79 /79 | boolean |
| `isUserRunning(int)` | 91 /91 | boolean |

The selected cache callbacks and their actual R8 forwarding/lambda bodies close
the wrapper-to-proxy links, including the booleans supplied by profile wrappers.
The adapter must preserve those exact operations, boolean arguments, ordering,
nulls/errors and user subjects; it cannot let a guest choose a replacement parent
or serial. Scalar serial transport is a particularly small genuine projection.

**Typed payload difference:** Samsung UserInfo reads/writes16 fields; ColorOS15.
The common prefix ends in `profileBadge`; Samsung appends `attributes:int`.
Samsung `isSuperLocked()` consumes attributes and flags. Captured ColorOS also
lacks Samsung's secure-folder/virtual/super-locked methods. Consequently, matching
transaction codes do not license raw cross-framework UserInfo or typed-list
forwarding. Incompatible list-element decoding can misframe the next element;
a single-object decoder can discard required Samsung state. Decode with the
actual Samsung schema, then explicitly transport the consumed identity/profile/
policy fields. Preserve Samsung semantics in the adapted security callers, not
guest defaults or unsupported method substitutions. No real user values were
decoded here.

IUserManager additionally exposes `getUserPropertiesCopy(int)`, code37 on both
sides. This is a **candidate**, not automatic equivalence to local full properties:
the server checks cross-profile permission and constructs the copy according to
calling UID/manage/query permissions. The local method obtains the original user
properties, with Samsung virtual/DAR branches. A narrow privileged policy bridge
can return the genuinely evaluated credential-sharing boolean; a caller-filtered
copy must not silently become a false/default policy result. UserProperties
parcel declarations/bodies were retained, but no blanket schema-equivalence claim
is needed for that scalar projection.

## Policy and current lifecycle are separate owners

Samsung local `isMainUserPermanentAdmin()` reads resource17891840 from its real
Context. It is not simply the result of `getMainUserId` or a guest admin flag.
Samsung supervision reads `escrowTokenRequired` from its loaded
SupervisionSettings under the service lock. Its constructor names
`Environment.getDataSystemDirectory()/supervision_settings.xml` and
`supervision_recovery_info.xml`, and the selected settings-loading path reads the
original policy file. The captured guest supervision method has an additional
feature-flag early-false branch. A guest namesake or empty settings object is
therefore not proof of original policy. These genuine local-policy semantics
need a small owned transport or a coherent original local owner; IUserManager
alone does not supply all of them.

Identity is also not current lifecycle state. Samsung local running/unlocking
queries use its real `mUserStates`; the unlocking path can consult
`StorageManager.isCeStorageUnlocked`. `setUserState`/`removeUserState` update that
state and invalidate the unlocked cache. A saved host serial/profile snapshot
cannot stand in for current guest phase/user state or genuine CE ownership.
UserManager's info/profile/serial/unlocked caches and static cached headless query
must belong to the admitted authority generation. The headless query resolves
the global `"user"` Binder directly, bypassing a substituted Context client.

## Smallest source-supported construction choice and remaining cut

**Inference/proposal:** use the genuine client with an explicitly selected typed
user backend, or adapt the exact security callsites to that same narrow backend.
Keep a minimal owned identity record with the actual consumed ID/serial/profile/
type/flags/attributes fields; evaluate genuine policy at its original owner.
Bind original and application Context, class/string lookups, local-service
projections, static/global queries and caches to that same generation. Do not
expose a public arbitrary-user or unchecked privileged-policy forwarding path.
The feature must preserve original caller/user/profile authorization across hops.

This avoids requiring another UserManagerService merely to make queries. It does
**not** establish a surviving server: OneOS stops the original system_server.
A retained authority or controlled import still needs a concrete real owner and
its state/lifecycle/permission dependencies. No such owner is instantiated here.

Actual production construction is now pinned: Samsung's PackageManager factory
obtains `Environment.getDataDirectory()` at PC34, passes that File at40 to the
full UserManagerService constructor, which appends relative `system/users`, names
`userlist.xml`, then reads it at1010. Per-user records have `.xml`, `.xml.backup`
and `.xml.reservecopy` paths. Under the ordinary `/data` environment this means
`/data/system/users`, subject to the process's real mount namespace. The separate
one-Context constructor uses `Context.getCacheDir()` instead; it is not a shortcut
to this production owner.

Missing/corrupt user-list paths can invoke original `fallbackToSingleUserLP`,
create a default system user and properties, set the next serial and persist user
and list files. Starting a server over guest staged data can therefore create a
new registry before credential cleanup notices the mismatch. The prior
[state/mount audit](construction-state.md) establishes why guest `/data` does not
automatically resolve host state. Do not instantiate the server, replay/copy a
user registry, create user data, bind all of `/data`, or treat numeric user0 as a
valid acquisition procedure.

Before the first eager cleanup, the candidate must establish one authoritative
user/serial/profile generation plus matching credential/native state, final
replace-safe path bindings, real application Context and policy owners, and the
exclusive writer. Any unknown transport/identity/admission result blocks that
construction and keeps the feature safely disabled. Original legitimate user
removal remains possible through its genuine lifecycle/policy; this is not a
promise to freeze all state indefinitely.

Still missing live: installed OneOS bytes/bridges, actual registry and directory
identities, user/profile/serial mapping, surviving/imported server ownership,
current user/CE state and callback/drain/reconciliation across handoff. The audit
establishes required code and typed transport edges, not current hardware identity,
cryptographic acceptance, PR readiness or beta fault-test completion. It preserves
GOAL's documented OneOS limitations without requiring global SELinux Enforcing.
