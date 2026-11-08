# Opaque retained host PIN binding

`PreparedRetainedPinBinding` implements the selected **host-only** object and
physical-subject selection contract. Its only public methods are
`captureExisting(actualRegistry,actualFamily)` and main-only `checkStillBound()`.
There is no caller-supplied Binder/user/serial, endpoint or subject getter,
authentication operation, generation token, lease or readiness grant. Source
implementation is prepared; no compiler/model or original runtime ran in this
scope. Existing capture/client sources and diagnostic APK remain unchanged.

The factory uses the exact existing RegistryV2/Family pair in the same authored
runtime package and defining loader. Four individually prepared first-party
private fields establish the family's retained registry and both original owner
records. The LSS is the actual retained local host Binder at Family[6]; UMS and
UserController are the actual Registry[1]/[15] objects. The initialized LSS
framework UserManager's actual `mService` must equal that same UMS. A different
manager backend or proxy is refused, without a descriptor or identity fallback.

All 24 original field descriptors/access flags come from the frozen source
proposal. Only four original read-access preparations supplement the four
first-party preparations: UserManager.mService, UserData.info (public field on a
package-private class), UserInfo.attributes and UserHandle.mHandle (package-private
final, flags16). Field/type metadata is cached once. No new registry, service,
provider, UserInfo or UserState is constructed; no original user/cache query or
Binder lookup is invoked. Exact class/loader checks constrain placement; they
do not authenticate code or the physical process.

Current and persistent-record snapshots use separate original monitors. Retained
lock/container identities are checked before entry, inside the retained monitor,
before each canonical container operation and afterward. Only exact canonical
ArrayDeque/SparseArray/SparseBooleanArray objects are called; subclasses and
namesakes are refused before their methods run. Existing capture controls stay
outside both OEM monitors. Neither monitor is held across the other, IPC, a
provider callback or metadata preparation.

The current snapshot requires a real nonnegative current user, source-empty
target(-10000), empty pending queue, no pending logout or switching, and an
original UserState whose retained handle agrees with that user. Both
RUNNING_LOCKED1 and RUNNING_UNLOCKED3 are supported; booting, unlocking-in-progress,
stopping, shutdown and unknown states are unavailable for this first binding.
Samsung `getCurrentUser()` can return the target during switching, so it is not
used to choose the subject. Neither supported state proves CE/key readiness.

Under actual UMS.mUsersLock, the binding retains the actual UserData/UserInfo
identities, id, nonnegative serial, flags, attributes, profile group and user type.
Partial, pre-created, removing, disabled, non-full and profile subjects are refused
using the pinned original markers. No Context-user0 shortcut or cached serial
default supplies the subject. The factory/check repeats both observations and
refuses identity or scalar drift; it never refreshes or retargets a binding.
Legitimate changes may require a separately admitted new binding after retirement.

Strong references keep Java objects reachable. These observations are not atomic
cross-process leases, do not detect every ABA event, do not fence every original
state writer and own no native/CE/policy lifetime. Original Samsung policy still
governs real verification. No guest state, forced-true CE result or UI keyguard
flag is treated as physical truth.

The endpoint remains a **local Samsung Binder**. This component cannot turn it
into guest5cb canonical objects or a remote BinderProxy. Authentic kernel-handle,
subject/currentness delivery into the guest, per-operation admission and original
producer retirement/drain remain the next distinct engineering boundary. It
does not call the private client factory, expose the raw original service or
publish a service. The historical client PC pass is not transferred to this
new component.

The new first-party fixture plan reuses only immutable authored world-source data
and the unchanged four actual SDK-compiled capture classes. New model boundaries
provide actual selected fields and loader/monitor mechanics, not authentication.
Cases cover both legitimate states and nonzero/user0 serials, exact retained
objects, all transition/record/flag refusals, proxy/cohort mismatch, replaced
monitors/containers, foreign subclass traps, wrong main thread/runtime package,
and observed drift around original anchor checks. Original constructors/getters
are poisoned outside authored setup. Compiler/D8/model execution requires a
separate reviewed builder and root gate; no such execution is claimed here.

## Final subject read after control checks

The [source-only successor](../tools/compose_retained_pin_binding_observation.py)
retains both control checks in the binding factory and recheck. It moves the
last control pass ahead of the final current-user and registry observations.
The previous order could return a stale observation if the retained control
pass reentered and changed the user record after the last subject read.
The transform preserves the exact historical source under its inverse.

The [paired JVM fixture](../tools/test_retained_pin_binding_observation.py)
changed the serial on the same retained model user record during the final
control callback. The baseline accepted the stale observation in both
factory and recheck. The successor refused both with the expected subject
drift result. Both versions accepted the stable-record controls.
[Model receipt](../out/retained-pin-binding-observation-tests/r-ee6279ac/receipt.json)

The targeted SDK37 and D8 build emitted the four binding definitions in a
15,704-byte DEX039 with SHA-256
`85a338b8a9fcf7fd0bcc14c197f14c83f08b276fd0e5593945a7e011e00ec8e2`.
The other retained host classes and compiler declarations served as build
inputs. The staged DEX remains unselected.
[Build receipt](../out/retained-pin-binding-observation-build/r-01558677/receipt.json)

The corrected reads still use the separate original monitors. Their ordering
improves the point observation and does not join the guest user, host boot
occurrence or endpoint lifetime. Those owners still require independent
source evidence before a worker can use the binding.
