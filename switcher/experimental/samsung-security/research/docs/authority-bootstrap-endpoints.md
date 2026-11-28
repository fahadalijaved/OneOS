# Authority bootstrap B: endpoints and guest lifecycle

The finite name/creation cut is **three guest lookup retargets plus replacement
of one original guest lifecycle producer before it constructs LockSettings**.
The current transport cannot execute the resulting bootstrap: its 33 routes
exclude `systemReady`, and no guest-local lifecycle/control bridge exists.
This is a source-supported proposal for review, not a patch, new runtime API,
published service or accepted bootstrap.

The [inventory](../inventory/authority-bootstrap-endpoints.json) pins 51 selected
and reused bodies, 16 exact instruction assertions, four literal-lookup scans,
and the 54-reference local-consumer scan. Replay:
`python -B tools/audit_authority_bootstrap_endpoints.py`. Static checks pass;
no OEM/Android code executed. Original supplied bytes do not identify the
currently installed OneOS guest.

## Two Binder endpoints, one authority owner

| Endpoint | Proposed owner and protocol | Required admission |
| --- | --- | --- |
| `lock_settings` | Dedicated authority process, actual Samsung ILockSettings protocol and original Samsung Stub/backend | Samsung-protocol guard entering the shared live/retirement owner, then genuine original checks |
| `oneos_coloros_lock_settings` | **PROPOSED**, same process, selected guest ILockSettings protocol mapped to that same backend | Guest caller/user/operation and authority-generation admission before original invocation |
| Guest `LockSettingsInternal` | Actual guest-class-keyed LocalServices object in guest system_server | Real local proxy and owned lifecycle/callback channel to the same authority; unimplemented |

Protocol separation does not establish exclusive writer ownership. Publishing
the raw Samsung backend Binder outside the guard lets Samsung-facing or stale
cached Binder callers bypass retirement. Both Binder endpoints, actual private
local calls and lifecycle entries must share admission/active-call/drain
ownership before return restarts stock LockSettings. Retain original Samsung
permission checks; a service name, descriptor or UID1000 is insufficient.

Keep Samsung's private framework/LPU lookups on their genuine Samsung binding;
do not globally rename the service string or seed guest process caches as a
substitute. `user`, `authentication_policy` and other Samsung Context lookups
still require actual corresponding owners. Neither endpoint name creates those
owners. Effective Binder driver/ServiceManager namespace, service labels,
publication permission, death/replacement and current installed-image behavior
remain separate admission requirements. Existing permissive/relaxed OneOS
platform limits are disclosed; this plan adds no global Enforcing gate.

## Complete literal cuts in the four selected guest archives

Inputs: ColorOS framework SHA`d5c6b7fd…bcd2`, services`66d0d51d…edf3`,
SystemUI`0e253fad…ef77` and Settings`33b0173b…4838b`. The exact
`string=lock_settings` scans find 2/2/0/0 instruction references respectively.
PCs are method-relative code units.

| Source method | Literal / lookup | Required change |
| --- | --- | --- |
| LPU.`getLockSettings()` returning `ILockSettings` | framework classes6.dex, PC5 / ServiceManager.getService7 | Lookup proposed guest alias before any admitted LPU caches a Binder |
| RecoveryController.`getInstance(Context)` | framework classes3.dex, PC1 / getService4 | Lookup guest alias; explicitly resolve its separately exposed recovery capabilities |
| SystemServer.`startOtherServices(TimingsTraceAndSlog)` | services classes.dex, PC1717 / getService1720 / guest asInterface1724 | Retain guest protocol using alias |
| LSS$Lifecycle.`onStart()` | services classes2.dex, PC14 / publish19 | **Suppress this producer**, not rename its original guest LSS publication |

LPU reads/writes its private **instance** cache at PC0/15, then returns it at17–19.
Changing a lookup does not retire already cached original Binders. Recovery's
getter also constructs a controller retaining the resolved guest interface.
Use fresh admitted guest processes/instances or prove old owners disconnected
and drained. No canonical fallback is permitted on alias loss.

RecoveryController is an additional direct lookup, outside LPU. Its recovery-key
operations are outside the current 33 guest routes. Leaving its getter canonical
would send guest transaction numbers to Samsung's different table; retargeting
it alone does not implement recovery. Support or explicit feature-unavailability
and consumer handling need review, without weakening required app-key policy.
These four archive scans close only their literal sites. Other admitted archives,
native consumers, reflection and dynamic-name construction need evidence or
exclusion; no whole-ROM lookup claim is made.

## Suppress the original producer before external effects

SystemServer loads `LockSettingsService$Lifecycle` at PC1712 and calls actual
`SystemServiceManager.startService(Class)` at 1714. Its result is not retained
through an implementation cast. Manager construction resolves the real public
Context constructor; starting records the service and invokes real `onStart`.
The original lifecycle constructor only calls SystemService super. Its onStart
installs AndroidKeyStoreProvider at 0, constructs guest LSS at 9 and publishes
canonical Binder at 19. The guest LSS constructor publishes its local service at
PC287 after earlier storage/observer/security initialization. Replacing Binder
publication after construction leaves that second security owner alive.

The proposed atomic producer cut replaces the class at 1712 with a reviewed
guest SystemService lifecycle. It must retain required provider setup without
constructing the original guest LSS; own Context, phase and TargetUser handling;
bind the admitted authority generation; and publish a **real guest-local proxy**
before onStart returns and subsequent consumers continue. Original
`LocalServices.addService` uses a synchronized static Class→object map and throws
on duplicate registration. Remote Samsung LocalServices publication cannot
populate that process-local guest map. Samsung's own constructor publishes its
private local service at 1024, then its lifecycle publishes canonical Binder at 24;
these remain actual authority-side operations, not guest-local publication.

## Required lifecycle and early consumers

| Point | Actual supplied contract |
| --- | --- |
| Before phase480 | SystemServer invokes guest `ILockSettings.systemReady()` at5625. Exact wire is guest26→Samsung70, no arguments, sync flags32, original exception/void reply. Samsung starts with `checkWritePermission` at 0, enforcing ACCESS_KEYGUARD_SECURE_STORAGE. It performs real migrations/native/policy work. |
| Before later service constructors continue | SystemServer starts TrustManager at3593; its constructor caches local owner at176–184. AuthenticationPolicy starts at4516; its constructor requires non-null local owner at66 and stores it at72. |
| Phase480 | SecureLockDevice lifecycle calls onLockSettingsReady; local cache32 and genuine StrongAuth registration68 follow. |
| Phase500 | AuthenticationPolicy.init registers local state listener at4; TrustManager conditionally registers at47. RecoverySystem registers reboot-escrow listener at16, or logs/skips on null—neither is recovery readiness. |
| After AMS.systemReady | SystemServer looks up local owner at6528, invokes onThirdPartyAppsStarted at6537, then starts SystemUI at6550. |

Lifecycle must preserve actual onBootPhase and onUserStarting/onUserUnlocking
events; both original user callbacks obtain `TargetUser.getUserIdentifier` at 2.
Samsung phase 520 discovers/refreshes Weaver slots,550 performs migration,1000
posts work; user unlocking also posts work. Event return is not child-work
completion. Do not replay phases, fabricate user success or use an ordinary
credential caller as a privileged boot controller.

The current 33-route adapter rejects bootstrap code26. A reviewed26→70 route
with genuine startup-role admission, or an exact controlled replacement of the
SystemServer call, is still required. This report adds neither. Java phase/user/
local calls additionally require an owned control channel, not raw parcel
forwarding. Caller ownership must cover the actual guest lifecycle/controller
generation and original request identity before any hop/identity change.

## The local proxy cannot be an empty compatibility stub

The exact guest internal class declares 18 abstract methods; Samsung's selected
internal class/LocalService declare 12. There are 8 exact guest signatures,
3 changed signatures and7 absent from the selected Samsung internal class:

- Changed: `clearRebootEscrow()Z` versus`()V`; `removeEscrowToken(JI)` versus`(IJ)`;
  `unlockUserWithToken(J[BI)` versus`(I[BJ)`.
- Absent: add/is-active escrow token, lockUser, prepareRebootEscrow, reboot-escrow
  listener and register/unregister LockSettings-state listener operations.

Samsung LSS separately declares addEscrowToken with an additional int and
isEscrowTokenActive with reordered arguments. No semantic mapping/default is
chosen. Exact declaration matches also require actual result/callback/type
ownership across process/realm; they are not eight implemented bridges.

The 54 exact local references include user lock/create/remove, DPM credential
metrics/token/StrongAuth policy, TrustManager token/listener paths, RecoverySystem,
AuthenticationPolicy, SecureLockDevice and AgentAuth. Required listeners and
policy cannot be discarded as optional OEM work. No void callback, default metric,
false/true result or fabricated completion can substitute their genuine duties.

The smallest executable bootstrap therefore still needs the shared guarded
endpoint owner, atomic lookup/producer cut, reviewed systemReady admission and
the real guest-local lifecycle/policy bridge before early use. Those are finite,
named missing implementations. Source/Context/registry construction, exclusive
native/state handoff and return supervision belong to the paired bootstrap
owners. Nothing here selects the proposal or establishes a runnable authority.
