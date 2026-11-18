# Authority bootstrap gate F: policy and auxiliary Context owners

**Disposition: open, source proposal only.** A genuine system Context or a working guest Binder connection does not establish the policy owners consumed by original Samsung LockSettings. The finite source investigation identifies concrete producers and several narrow adaptation sites. It neither selects a runnable authority realm nor proves that the entire Samsung system_server is necessary.

The [inventory](../inventory/authority-bootstrap-policy.json) pins original archives, 96 selected methods (92 code bodies and four abstract declarations), four selected Binder request pairs, 20 asserted fact groups and raw/reader receipts. These are evidence counts, not runtime coverage. [The verifier](../tools/audit_authority_bootstrap_policy.py) checks immutable inputs and receipts with `--report`. PCs here are **decimal DEX code-unit offsets**. No private policy files were read; no OEM class, Android service, native operation or phone action executed. Installed OneOS bytes and effective runtime policy remain unknown.

## First operations and actual policy producers

| Reached original operation | Source-owned result or first effect | Required binding |
| --- | --- | --- |
| LSS constructor | Captures `ActivityManager.getService` at 440, NotificationManager at 610 and canonical SupervisionManagerInternal at 661. Injector obtains DevicePolicyManager from Context. | Genuine Context, canonical registry/client identities and retained owners; Context creation is not their readiness proof. |
| LSS `systemReady` | Reads the secure-lock-screen feature; DPM failed-attempt count at 40 precedes migration at 47. Later feature checks select fingerprint/face managers. | Real feature/resource policy and the same authoritative DPM/user state; never assume unmanaged or feature-off. |
| LSS post-credential change | DPM password-history length at 82 feeds the original history handling. | Actual admin/password policy and credential-owner mapping, not a zero/default history. |
| LSS escrow decision | DeviceStateCache organization-managed at 47/51, supervision at 110, provisioned at 147/151, followed by other Knox/user/feature guards. | Initialized local policy and updates before this decision can run. |
| LSS final verified-credential path | Concrete SecureLockDeviceService state at 16 selects the original additional-factor branch. `systemReady` also reads it at 522. | Same admitted persisted state, factor/StrongAuth owner and completion semantics as the credential authority. |
| LSS `unlockUser` | Calls `IActivityManager.unlockUser2(user, IProgressListener)` at 42. | Typed compatible guest AM operation, exact user and real progress owner; request return is not CE/user-unlock completion. |
| LSS encryption notification | DPM resource strings, genuine resource/PendingIntent construction, `notifyAsUser` at 655/733. | Correct package/user/resources, actual notification delivery and callback/work lifetime. |

The reused complete 199-method LSS receipt contains one direct IActivityManager operation (`unlockUser2`). DPM failed-attempt reads also appear in dump/debug methods; the selected factory must preserve their genuine behavior too. This is a bounded class frontier, not a claim about reflection, every server subclass or installed code.

## DPM Binder transport does not supply the local cache

Samsung DevicePolicyManager wraps `IDevicePolicyManager`, passing its actual Context package and parent-instance flag. The selected failed-attempt service body enforces caller/cross-user authorization, resolves the credential owner, then reads `DevicePolicyData.mFailedPasswordAttempts` (72). Password history invokes the real strictest-policy aggregation; this audit does not replace that aggregation.

`DeviceStateCache.getInstance` instead resolves **process-local** `DevicePolicyManagerInternal` and calls `getDeviceStateCache` (10). Its absent-owner path returns the original empty cache. Empty-cache defaults are source behavior, not evidence that an imported authority has loaded genuine policy. In particular, absent provisioning can postpone cleanup; an unrelated guest cache reporting provisioned but not organization-managed can take a different branch. After all remaining original guards, LSS can permanently destroy both escrow states at 238/241. No private-state inspection establishes which branch this phone would take.

The actual producer is DPMS's `DeviceStateCacheImpl`: organization-management uses profile-owner entries and device-owner type; `Owners.load` populates these from original owner data. Selected paths are `Environment.getDataSystemDirectory()/device_owner_2.xml` and `Environment.getUserSystemDirectory(user)/profile_owner.xml`; AtomicFile/XML dispatch and both concrete owner subparsers are pinned: the device-owner parser populates owner types and the original OwnerInfo; the profile-owner parser populates its per-user owner map. Original OwnerInfo deserialization is a retained callee, not reimplemented here. Per-user `device_policies.xml` supplies `setup-complete` and failed-attempt state. `initializePolicyDataFromXml` updates provisioning from that data, while live `Settings.Secure.user_setup_complete` updates also write the cache and save policy. A one-time boolean copy would omit these producers and updates.

Constructing full original DPMS is a concrete wider alternative, not a passive getter implementation. The selected constructor registers receivers (2041), publishes a lite local service (2304), conditionally upgrades policy data/owner files and version journal (2979/2994/3075), loads Owners (3338), publishes full DevicePolicyManagerInternal (3554), and loads DevicePolicyEngine (3607). The upgrade is conditional; existing version/state is unknown. PM/AM/ATM/UserManager local inputs, role listeners, resources and these possible writes must be owned before using that route. This investigation does not reconstruct their whole graph or infer that no smaller real policy owner can exist.

## Supervision and Secure Lock Device remain required policy

[Gate C](authority-bootstrap-users.md) pins original SupervisionSettings loading, the service's thread/user/role listeners, canonical local publication and parser. Its frozen inventory is pinned by this verifier. The earlier [user-policy comparison](security-user-binding.md) establishes that guest supervision can have an additional early-false feature branch; a guest namesake is not policy equivalence.

F additionally closes profile-owner ingress: lifecycle registers `PROFILE_OWNER_CHANGED` for all users (26), with null permission/Handler arguments in the selected original call. The receiver uses `getSendingUserId` (4). Its Injector caches a canonical LocalServices DPMInternal lookup. The actual sync wrapper queries that genuine DPMInternal `getProfileOwnerAsUser` (8), compares original resource strings 17039420 and 17040325, then calls `setSupervisionEnabledForUserInternal` (54/89). That method saves settings at 19 before subsequent clean-identity work. Preserve producer/event/user/resource provenance and persistence; do not replace this observer with an unowned guest default. Those later clean-identity callees are a remaining effect frontier, not independently proven harmless work.

SecureLockDeviceService's getter directly follows private `mStore -> mFileStore -> mIsEnabled` under the file lock. Its lifecycle constructor creates the original owner and synchronously loads `Environment.getDataSystemDirectory()/secure_lock_device_state.xml`, parsing `enabled`, `client-id` and original setting values. Missing-file and error branches retain/reset disabled/default client state. Those fallbacks cannot authenticate an absent authoritative binding.

The same constructor obtains genuine biometric/face/fingerprint/power and UserManagerInternal owners, constructs restriction/USB/NFC/status-bar/settings controllers, and registers USER_UNLOCKED plus biometric-enabled callbacks (717/727). `onStart` publishes the concrete local service. Phase 480 acquires LockSettingsInternal and registers StrongAuth; phase 1000 registers biometric listeners and can reapply real restrictions and persist enabled state. Required additional-factor policy cannot be classified as an optional OPPO feature. [The existing StrongAuth analysis](strong-auth-gating.md) remains authoritative about primary success versus final unlock. Complete controller/backend initialization, callback drain and state handoff remain unimplemented.

## Narrow transport results and source adaptation proposal

| Selected request | Samsung / ColorOS transaction | Bounded conclusion |
| --- | --- | --- |
| DPM failed attempts | 31 / 31 | Selected write signatures match; real server/caller/state policy still required. |
| DPM password history | 19 / 19 | Same limitation; not general DPM ABI compatibility. |
| AM `unlockUser2` | **208 / 205** | Opaque original Samsung proxy to guest AM is invalid. |
| Notification enqueue | 7 / 7 | Matching request writes do not prove Notification Parcelable or server equivalence. |

The Samsung notification wrapper additionally invokes edge/overflow-specific operations and schedules delayed work before enqueue. Therefore matching enqueue alone does not validate importing that wrapper. A reviewed adaptation may use the genuine guest notification manager while preserving intended user/package/channel/resource and notification behavior. This audit selects no removal of the encryption alert and supplies no notification no-op.

PM also has an important supported bootstrap path: ApplicationPackageManager's constructor records `isSystemFeaturesCacheAvailable`. With a genuine system ActivityThread and absent global cache, that helper returns false, and feature queries use the original property-invalidated fallback. The bounded framework cache xref pins app `bindApplication` as its external initializer. Cache absence alone does not disqualify system Context. Read-only compiled feature decisions, actual PM feature-map provenance and invalidation still require admission; Samsung PMS's selected non-maintenance path reads `mAvailableFeatures`. The producer/contents of that map and guest equivalence are not closed here.

The concrete next adaptation surface is **source proposal only**:

1. Select either the genuine initialized Samsung DPM/Supervision/SecureLockDevice policy family with its state/update owners, or reviewed typed operations against those same authoritative producers. For the latter, explicitly retarget LSS's two DeviceStateCache queries, supervision query and two concrete SecureLockDevice getter sites; preserve every original user/Knox/feature and additional-factor branch. Merely changing Context cannot redirect the static LocalServices lookups or concrete store dereferences.
2. Supply real DPM client operations through Injector, preserving caller/package/parent/user/credential-owner semantics. Unknown policy is unavailable, never unmanaged/false/zero readiness.
3. Adapt the exact AM operation to the genuine guest client contract and retain its real IProgressListener through user/storage completion. Admit notification and PM/resource clients separately, without importing unsupported Samsung wrapper work by accident.
4. Establish all admitted state and policy producers before eager credential cleanup; drive the real phase/user/update order, then verify additional-factor and handoff ownership. No live policy object, adapter API, mutation lease, teardown/drain or uncertain-progress recovery is implemented by this report.

These are specific unresolved gate-F bindings. They prevent declaring the proposed realm ready; they do not prove that a whole Samsung system_server is the only possible solution. No new policy patch, optional-feature removal, firmware selection or device candidate follows.
