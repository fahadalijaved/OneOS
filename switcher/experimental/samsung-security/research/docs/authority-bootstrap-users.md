# Authoritative users before security-service cleanup

**Gate C remains blocked by ownership, not by a demonstrated requirement to import all PMS/AM.** The unchanged Samsung Context-only UMS constructor cannot supply a usable standalone authority. A narrow, source-preserving handler retarget is plausible; it does not solve genuine registry/policy identity or live lifecycle. No original class was initialized, no private user registry was read, and no phone operation ran. All PCs below are decimal DEX code-unit offsets.

The [derived inventory](../inventory/authority-bootstrap-users.json) pins the reused [user-binding evidence](security-user-binding.md), new exact bodies and their full-container DEX041 locations. Samsung services is `def967fb…`, ColorOS services `66d0d51d…`; these are captured inputs, not proof of the running guest. [UserInfoWire](userinfo-wire.md) transports data only and does not establish an authority.

## Exact local frontier

These twelve methods define this bounded frontier, not the whole reachable service graph. UMI means the genuine Samsung `UserManagerInternal` implementation; its class identity/local registration cannot be replaced by an unrelated namesake.

| Original local method | Actual source owner / meaning | Required binding |
| --- | --- | --- |
| `getMainUserId()` | Scans UMS users, main flag and removing-user filter; no match is -10000. | Original admitted registry; never default0. |
| `getProfileParentId(int)` | Delegates to original profile-parent resolution. | Genuine profile graph, including legitimate absence. |
| `getUserInfo(int)` | Locks UMS users and returns actual UserData.info or null. | All Samsung fields/attributes, not guest15 plus invented attrs. |
| `getUserProperties(int)` | Original properties/defaults; conditional genuine DualDAR virtual-user mapping. | Original type defaults and per-user policy; unavailable is not false. |
| `isMainUserPermanentAdmin()` | Original Context resource policy. | Actual Samsung resource identity/value, not a main-user flag. |
| `isUserRunning(int)` | Watched state map, not registry existence. | Actual active lifecycle. |
| `isUserUnlockingOrUnlocked(int)` | States2/3; states4/5 also consult actual CE-unlocked state. | Lifecycle plus genuine CE authority. |
| `setUserState(int,int)` | Writes watched map and invalidates UserManager unlocked cache. | Sole admitted producer, ordered generation/currentness. |
| `removeUserState(int)` | Removes watched state and invalidates same cache. | Stop/drain acknowledgement; not deleting durable user identity. |
| `addMaintenanceModeLifecycleListener(...)` | PMS custom injector → MaintenanceModeManager's retained listener list. | Genuine maintenance owner if reachable, not a no-op. |
| `addUserLifecycleListener(...)` | Synchronizes and retains the actual listener in UMS. | Real event producer and listener lifetime. |
| Supervision `isEscrowTokenRequired(int)` | Locked original SupervisionSettings user data. | Loaded original policy owner, not a fresh empty settings object. |

Public serial/UserInfo/profile APIs are additional transport inputs to this local frontier. Serial's original -1 is genuine missing identity, never a substitute for a transport failure before recoverable-key cleanup. `UserProperties.isCredentialShareableWithParent()` returns an explicitly present value or original type default; without either, its selected outline helper **throws SecurityException** (PC5), rather than establishing false.

## What construction actually does

The Samsung `UserManagerService(Context)` constructor passes null PMS into its delegated constructor (PC18/22). The delegated constructor unconditionally reads PMS.mCustomInjector at254. This rejects unchanged Context-only construction; **it does not prove full PMS is intrinsically necessary**.

The selected factory is now closed: PmCustomInjector selects Lambda0 classId1 (constant1 PC106, install147–155). Its switch at6 targets349, constructs `HandlerThread("UserManagerHandler")` at349–354, starts357 and returns its thread Handler360–364. That branch consumes neither PMS nor PackageManagerServiceInjector. UMS MainHandler's constructor only retains UMS and calls Handler(Looper). An explicitly owned original HandlerThread/Looper supplier is therefore a concrete potential constructor retarget. No such patch, thread or runtime was created here; queue lifetime/drain and original message behavior remain obligations.

A whole-archive exact mPm field-reference scan finds25 sites. None is a direct mPm read in the selected ordinary read-only/local state-map methods. Other real sites include creation/removal/quiet-mode/feature checks, original lifecycle boot `PMS.isDeviceUpgrading()`, maintenance work and switching's ASEC helper. This is a direct-reference bound, not proof that every transitive query is PMS-free. Original LSS `$2.run` registers its maintenance listener only for **actual user77** (compare49/51, non77 jump62→83, registration74). Refusing an unsupported maintenance realm can exclude that branch; it cannot silently turn the real listener into success. The original lifecycle and arbitrary UMS Binder surface must not be published as supported merely because the narrow queries work.

Before publication the full constructor initializes Samsung user-type builders/resources/default properties, creates directories/permissions, calls `readUserListLP`1010 and installs singleton1013. Local UMI publication follows at1076; an initial state-map entry/cache invalidation follows1094/1097. The durable read is not inert: `readUserListLP` can fall back, upgrade types/restrictions and write user files/list; ResilientAtomicFile.openRead deletes competing files at93/98, and failRead deletes the selected failed file at58. A missing/malformed registry can reach original single-user fallback and writes. These recovery/default behaviors cannot be used to manufacture authority for this project. The actual data mount, source registry generation, parser/default-policy resources and sole-writer/recovery ownership must be settled **before constructor/load**, not just before Binder publication.

## Lifecycle and supervision are separate owners

Samsung UserController.finishUserBoot calls UMI.setUserState at75; finishUserStopped removes it at194. ColorOS's corresponding methods call set at51 and remove at229. The reused complete reference scan also records start/handler/asynchronous updates. This supports a narrow live lifecycle transport as a design option; it does not authenticate guest IDs/serials against Samsung protectors, bind actual CE state or provide snapshot-plus-update ordering. A host snapshot becomes stale after hostSS dies. Importing all Samsung AM is not proved necessary; a real active guest lifecycle owner with authenticated user/serial/profile mapping, initial-complete barrier, ordered updates, cache invalidation and drain is still unimplemented. The separate policy bootstrap worker owns LSS's AM unlock protocol difference (Samsung transaction208 versus captured ColorOS205); this slice does not duplicate that AM protocol audit.

SupervisionService(Injector) loads/reuses the original settings singleton at31–51, owns a ServiceThread/Handler, registers a genuine UMI user-lifecycle listener113 and a RoleManager observer153. Its Lifecycle(Context) obtains RoleManager21; onStart publishes local6/Binder12 and registers profile-owner listener15. Original settings load `supervision_settings.xml` and `supervision_recovery_info.xml` under the actual data-system view. The parser reads `supervision_escrow_token_required` at55/59 and stores the genuine value63. A missing user's Java false default is a behavior of that admitted original owner, not proof that a fresh guest/empty policy is authoritative. Role/DPM mutation producers, ordering and listener drain remain the policy-owner boundary; publication is not completed loading/currentness evidence.

## Proposed cut and decision

Use three explicitly owned inputs: (1) original user registry/type-policy authority with complete16-field records, serials/profiles and genuine defaults; (2) current active lifecycle/CE authority authenticated to that same subject and generation; (3) original supervision/role policy. Retarget only the source-proven handler acquisition and exact required typed queries if those owners can be established. Refuse unsupported creation/removal/maintenance/ASEC operations before side effects; keep required PIN/profile/policy outcomes intact. Do not import a second global `user` endpoint or default an unavailable answer.

**No feasible complete selected construction is established yet.** The real providers after hostSS death are missing: a client `UserManager(Context,IUserManager)` does not create them, and guest global `user` cannot supply absent Samsung attributes/policy by projection. Conversely, the evidence does not force full PMS/AM: the handler edge is removable by a narrow owned retarget and lifecycle can potentially be supplied by the genuine active guest producer. Next admission gate: demonstrate the actual sole registry/policy provider and source-preserving load/recovery boundary, then coherent live user/serial/CE updates and listener lifetime before allowing LSS cleanup or service construction. Failure to close those providers blocks the dedicated realm; an interface sketch or cached user0 does not pass it.

Recheck existing evidence without new OEM reads: `python -B tools/audit_authority_bootstrap_users.py --report`. `--capture` requests only the explicit bounded selectors and reuses completed receipts. Neither mode executes OEM code or establishes Android acceptance.
