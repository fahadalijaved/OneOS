# Retained Samsung cohort: installd routing and writer frontier

This is a static source contract, not a selected topology or running handoff. The saved reader audit passes **122 checks**, covers **89 selected method bodies in 46 queries**, and joins the actual staged OneOS services with Samsung's original Java/native owner evidence. No native, OEM or Android implementation ran. No phone action, patch, clone or endpoint was created.

The decisive result is that changing one `Installer.mInstalld` field cannot transfer the host writer cohort. The pinned Samsung services contain **75 direct IInstalld invoke sites in 65 methods across 29 classes**, excluding generated Stub dispatch. Samsung's R8 output loads the public volatile interface outside Installer. Independent HeimdAll code also caches the canonical Binder. Existing stack-local interfaces, queued tasks, callbacks and old death recipients survive a field replacement. Neither route below currently has a source-owned complete admission/drain and native-view handoff.

## Exact source identities and instance relationships

The audit pins original Samsung services `def967fb…` (two logical DEX041 headers in one physical container), Samsung framework `8095a9ae…`, and **actual staged** OneOS services `efb45f5f…`. The last is acquired code, not proof it is currently loaded. Every selected body/raw/receipt and all direct callsites are enumerated in [the inventory](../inventory/retained-installd-routing.json). PCs here are DEX code-unit addresses. The tool's `--report` verifies existing proofs without reading any live registry or rerunning OEM code.

The existing production factory proofs establish these source relationships:

- `PackageManagerService.main(Context,Installer,DomainVerificationService,boolean)` retains its real Installer argument in the UMS factory lambda at PC103 and `PackageManagerServiceInjector.mInstaller` at PC374.
- The real PMS constructor obtains that Installer at PC382 and stores `PMS.mInstaller` at PC386; the exact Injector getter directly reads `mInstaller` at PC0 and returns it at PC2. PMS passes it to `EnterprisePartitionManager.setInstaller` at PC956. The production UMS factory's `UserDataPreparer.mInstaller` is the captured same Installer (PC22); it also retains the actual install lock and Context before constructing UMS at PC40.
- Source Installer creation roots are SystemServer's reflective `startBootstrapServices` class operand PC370, SMS Lifecycle `onStart` PC360, FileService constructor PC72, RollbackManagerService `onStart` PC70 and StorageStats Lifecycle `onStart` PC102. These are five potential roots, not five observed live objects. Capture must use the original source-owned instances that actually exist; constructing them to discover their state changes the problem.

The Samsung services scan has 200 Installer-owner references and 162 IInstalld-owner references: 160 invokes plus two type checks. After generated Stub invokes are excluded, all 75 remaining invoke sites have exact body evidence. The captured framework has zero direct Installer-owner references; that does not exclude reflection, other classpath archives or loaded objects.

## Native call owners that a transfer must cover

| Source owner family | Direct native invoke sites |
| --- | ---: |
| Installer / Installer.Batch | 13 / 1 |
| PMS public Binder / PackageManagerInternal | 4 / 4 |
| AppDataHelper and its three selected lambdas | 6 |
| UserDataPreparer | 2 |
| InstallingSession / PackageInstallerSession / PackageManagerLocalImpl | 1 / 2 / 1 |
| StorageStatsService, Lifecycle and selected callback | 7 |
| SMS and selected callback | 3 |
| HeimdAllFsService and its two selected lambdas | 10 |
| RCPManagerService / EnterprisePartitionManager / DualDARDaemonProxy | 7 / 5 / 1 |
| InstalldProcessor | 2 |
| FileIntegrityService Binder / CacheQuotaStrategy / SpegService | 2 / 1 / 1 |
| Rollback selected lambda / PmLifecycleImpl | 1 / 1 |

The inventory lists all 65 exact method descriptors, PCs and native targets, including creation/destruction, migration, snapshots, Knox copy/cancel, quotas, fsverity tokens, compression, mirror mounts and policy operations. This is the complete **direct** cohort in the pinned services archive, not a whole-device reflection or asynchronous-native completeness claim. Read-only native operations also need the right view and subject; they cannot all be classified as harmless or suppressed with success.

## Cache, first effects, death and asynchronous work

`Installer` has 19 declared methods. Its `mInstalld`, `mInstalldLatch` and `mVold` fields are public volatile (0x41). The constructor initializes a null interface and one-count latch; `onStart` calls `connect` immediately. `connect` resolves canonical `installd` (PC3), links a death recipient (21), adapts the actual interface (28), publishes it (32), and counts down the latch (36). It then invokes `invalidateMounts` (44) and may apply deferred `setFirstBoot` (51). Binder presence, a cached interface and latch release therefore precede these effects and establish no complete native readiness or ownership.

`checkBeforeRemote` waits up to ten seconds (68), throws on timeout (83), but its interrupted path returns (84). It is not an active-call counter or quiescence gate. The installd death callback creates another latch (38) and calls `connect` (46), without first clearing `mInstalld`; a delayed reconnect Runnable also calls `connect` (4). There is no declared Installer close, death-unlink, reconnect-cancel or global drain API. Retargeting only the field allows an old recipient or delayed task to reconnect to the old canonical name, and cannot retract interface references already loaded by external callers.

`HeimdAllFsService` independently resolves `installd`, caches its interface (constructor PC32), and creates a serial executor (44). Its singleton getter can construct the owner and must not be used as an initialized-only capture. `safeRun` posts to BackgroundThread; `onRunRequested` can enqueue serial work; the selected lambda can start another Thread. No declared service-wide close/shutdown/quiesce is established. It lies outside an Installer-only gate.

`Installer.Batch.execute` reads the external interface at PC65 and issues `createAppDataBatched` at 67; individual futures are completed at 93 or exceptionally at 104. Returning a future from batch admission does not drain native work. `InstalldProcessor.process` constructs a real `IAppDataOperationCallback`, then passes it to copy/move native operations at PCs281/322. The selected status callback forwards actual FileOperationResult values to the processor's real result callback. Native method return and terminal callback ownership must be accounted for separately; this audit does not invent a terminal status or cancellation acknowledgment.

Samsung Installer also separately caches canonical **vold**. `clearAppData`/`destroyAppData` reach Samsung Pass-related IVold policy calls. A new installd name/view does not reroute these calls or authorize changing physical Samsung CE/key ownership.

## Compare the two proposed routes

| Obligation | A: canonical installd serves existing OneOS global bridges; host uses separate original daemon | B: retain canonical host daemon; guest gets private daemon/name/view |
| --- | --- | --- |
| Initialized host Java/native handles | Must admit and drain every captured host caller, cached interface and pending native operation before migration; old deaths/reconnects must be retired or rebound coherently | Existing host canonical handles remain bound; guest first lookup/proxy must deliberately resolve its separate endpoint |
| Mount/data paths | Preserve original whole-thread host SS and new host-daemon view before global bridges; canonical daemon receives intended guest paths | Replace/segregate the 14 global binds so host SS **and other host native consumers** keep original paths; guest namespace gets its own paths |
| New native process | Requires private original host path/layout/user view before native main and an authored publication seam | Requires private guest path/layout/user view before native main and an authored publication seam |
| Existing OneOS work | Reuses canonical guest proxy lookup and more global bridge behavior | Changes native endpoint selection and namespace bridge/control composition; cannot obtain isolation from guest `unshare` alone |
| Additional native policy | Samsung IVold/CE/SDP and caller-selected paths remain explicit owners | Same; alias or numeric UID cannot grant physical user/key authority |

The [frozen native companion](retained-installd-native-owner.md) proves the captured binary publishes literal `installd`; no selected argv alias seam is present. Main initializes globals, reads/writes layout and user configuration, and may migrate/delete old CA directories **before publication**. Hardcoded `/data`, UUID `/mnt/expand`, `/data_mirror`, quota/mount caches and caller-selected SDP database paths defeat an alias-plus-environment-only plan. Independent processes have independent locks, not cross-process writer serialization. Publication also precedes one cached-property initialization. These facts block a naive launch; they do not prove two correctly owned processes are impossible.

The installed 14-tree bridge list does not cover `/data/misc/installd/layout_version`. A private host view under A and the canonical guest daemon could still share layout/configuration state outside the listed bridges unless explicitly owned. No inference of disjointness or safe shared writes is made. Under B the guest's private pre-main view must cover those paths too. Existing best-effort app-storage scaffolding and ten-second polling provide neither native completion nor exclusive writer ownership.

The qualified ordinary-OneUI observation has init/installd in one mount namespace and SS in another with `/data` propagation (`shared:48` versus `master:48`). It is not proof that future OneOS binds cannot propagate, that all SS threads share one view, or that a particular native Binder is admitted. PID equality alone is not drain or endpoint generation.

## Smallest next contract, with its exact missing owner

There is no safe current `swapInstaller` API. Route A first needs source-owned admission at all enumerated caller/scheduler roots, an actual inventory of initialized instances, and completion of their accepted Java frames, queued work, real futures/status callbacks and native operations. Old death/delayed reconnect ownership must remain retained until cancellation/removal and all active uses are acknowledged. Only then could an endpoint-generation transition publish a new interface with the correct private path view. A new counter around Installer or a strong-reference capture is insufficient. The original operations, errors, serial checks and guards must remain genuine; dropping work or fabricating return values is invalid.

**Inference for the next engineering choice:** B avoids migrating the already initialized host Java caches and is the smaller Java cut. It is not proven cheaper overall. The next discriminating offline design should specify one exact native publisher change and guest-private pre-main path/propagation plan while retaining the original host canonical endpoint, then demonstrate that removing/segregating the global 14 binds still supplies the actual guest proxy/app-data consumers. The native pre-main writers, metadata/layout/UUID/mirror paths, caller-selected paths, UID meaning and other host native consumers must have explicit owners before code or launch approval. Failure to supply that plan rejects this version of B; it does not justify a field swap under A.

Root selects that engineering direction. No native implementation, endpoint alias, queue drain, retained process, source hook, physical user/CE handoff, app-key acceptance or runtime architecture is selected by this report. The previous 89-check user-lifecycle contract remains frozen.
