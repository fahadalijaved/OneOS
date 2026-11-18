# One Samsung registry needs a real active-user lifecycle

**The proposed UMI state-map transport is necessary but insufficient.** The
captured guest calls a concrete guest UMS during start/unlock, and the original
Samsung operations require real user-data, package-data and storage-preparation
owners. Retention can preserve those initialized owners; cold reconstruction
has not supplied them. Neither architecture is selected here. No OEM class or
native service was executed; no private user registry or phone state was read.

The [inventory](../inventory/samsung-user-registry-lifecycle.json) contains 51
exact instruction/branch assertions over 34 reused/new method proofs, plus all
eight direct guest `UMI.setUserState` references in seven methods. Nine bounded
reader queries were used, including one exact-reference scan. Samsung services
`def967fb…` uses its full DEX041 container; source `onBefore*` methods are in
`classes.dex`, logical header offset 10057984. ColorOS services is immutable
`66d0d51d…`; this does not attest a running or patched guest. All PCs below are
decimal DEX code units. Raw bodies stay ignored under `firmware/`.

## The guest owner is a concrete local object

`UserController$Injector.getUserManager` resolves global `user`, runs the guest
`IUserManager.Stub.asInterface`, **casts to concrete guest UMS at15** and caches
it17. A remote Samsung Binder, private-loader UMS or projected UserInfo cannot
satisfy this cast. `getUserManagerInternal` separately uses the guest UMI Class
key in LocalServices6 and caches12. Changing a public Binder name or publishing
a host namesake therefore does not redirect these existing local owners.

Actual `continueStartUserInternal` calls concrete `UMS.onBeforeStartUser`281;
the asynchronous unlock worker calls concrete `UMS.onBeforeUnlockUser`49 before
UMI state2 at77. A complete selected source adaptation must account for these
calls, their failures and package-data realms, rather than forward only set/remove
or call both implementations blindly against shared physical state.

The direct guest state-writer sites are:

| Actual method | UMI set-state PC |
| --- | --- |
| `startUserInternal` | 657 |
| `continueStartUserInternal` | 204, 245 |
| `finishUserBoot(UserState,IIntentReceiver)` | 51 |
| `lambda$finishUserUnlocking$1` | 77 |
| `finishUserUnlocked` | 62 |
| `stopSingleUserLU` | 202 |
| `finishUserStopping` | 118 |

These are all direct references in this captured archive, not a proof against
reflection/vendor producer paths. Existing nested `LocalService.removeUserState`
only deletes the watched map; outer UMS `removeUserState` removes durable state.
They must never be confused because of the shared method name.

## Required normal start/unlock work exceeds a watched map

For an existing user, original Samsung `onBeforeStartUser` calls the actual
UserDataPreparer with flag1 at48 and PackageManagerInternal.reconcileAppsData64.
User0 skips the additional restrictions/write branch70; other subjects can
update restrictions82 and schedule a user write85. The operation is neither a
metadata read nor supplied by an arbitrary client PackageManager.

Original `onBeforeUnlockUser` returns for a genuinely missing UserInfo6. For an
existing user it prepares data with flag2 at43, then reaches this common path:

1. Non-managed profile branch53 and absent DualDAR flag branch60 both jump to132.
   Successful DualDAR policy work also joins132 at80. The failed DualDAR branch
   may instead mark/write/remove the invalid enterprise user122/125 and return129.
2. At132–144 it obtains/caches the actual Samsung
   `StorageManagerService$StorageManagerInternalImpl` under that Class key.
3. It dereferences the concrete parent SMS148, acquires its actual `mLock`150/152,
   reads `mCeStoragePreparedUsers`155 and adds the user163.
4. Actual PackageManagerInternal.reconcileAppsData189 follows.

Thus the concrete prepared-user storage owner is required on the **ordinary
existing-user path**, not only for DualDAR. A narrow genuine vold invoker can
perform its reviewed native operations but does not supply this Java cache,
lock, package-data reconciliation or userdata preparer. Unchanged code needs
the original concrete owners. A separately source-proved equivalent adaptation
could be narrower; full PMS/AM/SMS import has not been proved mandatory.

Original UMS LifeCycle callbacks are a separate channel. Starting/unlocked
maintenance branches reach PMS custom injector only under the actual maintenance
predicate. Switching reaches its real ASEC helper in the original path; this
cannot be converted to an unconditional requirement for all PMS functions or a
no-op. Unlocking updates real UserData time and, for system user with the actual
communal-profile feature, can ask real AM to start that profile. Stopping clears
real start/unlock times. Forwarding only watched-map state omits this behavior;
unsupported policy must be rejected under an explicitly selected profile.

## Coherent CE transitions and stop are asynchronous

Guest `finishUserUnlocking` checks real CE24, verifies the same current UserState
object41 and expected state, posts a vendor-selected foreground Handler87, then
returns true90 **without checking post's Boolean**. That is not completion.
The actual worker rechecks CE2, invokes beforeUnlock49, commits state/UMI77 and
posts another continuation114. `finishUserUnlocked` rechecks CE17/current object,
changes state2→3, updates UMI62 and finishes the real progress reporter67. The
original gates and callback occurrence must survive; do not synthesize state3
from a credential Binder return or elapsed timeout.

Samsung UMI's states2/3 return true directly. Its stopping/shutdown states4/5
instead consult `StorageManager.isCeStorageUnlocked`32. That helper caches the
actual global `mount` interface, clears/restores Binder identity30/40 around its
real remote query36, and can return the original early-boot false when absent.
That bootstrap fallback is not admission of an unidentified/missing CE owner.
The guest Injector also calls its own actual StorageManager helper. Both must
refer to the admitted same physical user/serial/CE generation; a numerically
equal user or a copied cache is insufficient.

Guest `finishUserStopped` removes UMI state229 **before** later dispatchUserLocking484.
The latter posts work15 through a vendor-selected Handler. Its worker checks
whether that user restarted0 and can skip eviction13; otherwise it invokes the
genuine guest-local LockSettingsInternal.lockUser20, then KeyEvicted callbacks39.
The frozen local-security contract maps the real Samsung ordered operation:
lockCeStorage373 → Keystore onUserStorageLocked378 → genuine StrongAuth387 →
metrics cleanup, followed by callbacks. None can be replaced with user-state
deletion or an empty queue. Original local-method returns also do not prove
native durability or settle a lost reply.

UMS itself schedules writes with a 2000ms delay25/27 and invalidates caches30;
its actual MainHandler performs list19/user55 writes under original locks.
Restriction callbacks can post further work. A stopped map entry, constructor
return, Handler marker or router counter does not drain those descendants.
Return needs source ingress fencing, admitted worker/native/persistence outcome
and real progress/key-lock callback reconciliation before old graph retirement
or stock reconstruction. Existing OneOS kills are not those acknowledgements.

## Earliest ordering, and the minimum-owner challenge

Before cold UMS loading, the admitted physical registry/sole writer, real source
type defaults/resources and recovery disposition must exist. The frozen owner
card proves readUserList1010 precedes singleton1013, local publication1076 and
the constructor's initial watched entry1094. That initial entry is not an active
UserController snapshot. Upgrades can queue mutations before publication. Before
LSS/recoverable cleanup, registry/user serials and actual users must already agree.

Trust's production factory/constructor work supplies necessary additional owner
edges; the original handler extraction avoids PMS only for that handler branch.
It does not supply the real lifecycle's userdata/PMI/SMS work. Conversely, the
guest's current active UserController may avoid importing all Samsung AM **only
after** its concrete-call, state, CE, source/currentness and child ownership are
actually adapted. No such route is implemented. The prior
[owner assembly suggestion](authority-owner-assembly.md) remains historical:
its set/remove seam understates this required lifecycle closure; no frozen card
was edited here. The [old registry card](user-registry-owner.md) already warned
that beforeStart/beforeUnlock exceed the query cut; this report pins the concrete
guest cast and the normal-path Samsung prepared-user dependency.

**One next retention discriminator for root selection:** close a source-pinned
active-user lifecycle routing cut at the real guest unlock worker's concrete
beforeUnlock49 → UMI77 → continuation114 sequence, paired with original stop
dispatch/lock acknowledgements. Its retained endpoint must bind the existing
Samsung UMS + its real UserDataPreparer/PMI/SMS cohort, without constructing a
second Samsung registry. The offline artifact should first be the exact source
transformation/API/ownership contract and inverse/profile checks for that cut;
it must resolve which package-data work belongs to the guest versus retained
host and exclude competing host lifecycle producers. Merely adding a second
call, replacing the Injector cast with a remote interface, or accepting UID1000
would not pass. Runtime hook/transport emission requires root selection and
source closure, not another generic cold helper.

Reject this retention cut if it cannot preserve both package-data realms and
one physical CE/credential owner, if host LSS→AM can race a second active user
controller, or if any required owner loses its real mount/native/endpoint view.
Passing its offline source contract would still leave zygote/watchdog survival,
whole-thread mounts/properties, Binder/local namespaces, package/UID admission,
biometric physical ownership and return/drain to demonstrate. This is a finite
next decision, not a claim two complete SystemServers can coexist freely.

Recheck saved evidence without new reads:
`python -B tools/audit_samsung_user_registry_lifecycle.py --report`.
`--capture` uses only the explicit bounded selectors and saved receipts. No new
cold leaf, retainer, lifecycle transport, public service or runtime code was built.
