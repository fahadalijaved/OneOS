# Samsung security startup and import boundary

**Inference from observed source:** a guest-compatible facade backed by a controlled Samsung implementation remains a plausible design. The inspected sources do not prove that either the whole Samsung `system_server` or a tiny remote broker is required. **Missing evidence:** a runnable, isolated security stack. The immediate engineering boundary is the real service lifecycle, canonical Java/Binder types, and the actual local storage/user/security owners—not copying `services.jar` or constructing one Binder object.

All findings below are static. No OEM class, JNI, service, credential operation or phone action was executed. [The bounded inventory](../inventory/startup-import.json) pins actual bodies, physical/logical DEX locations, selected class/member differences and current OneOS source lines. Raw bodies remain ignored under `firmware/startup-import/`. Samsung services input is `def967fb…`; its DEX041 container has both logical headers at 0 and 10,057,984. The selected ColorOS services input is `66d0d51d…`. These supplied firmware inputs are not proof of the installed OneOS patched image.

## Actual creation and registration

Observed Samsung `SystemServer.startOtherServices(TimingsTraceAndSlog)` edges:

| Actual site | Source behavior | Import implication |
| --- | --- | --- |
| `0x0b11` | Starts `StorageManagerService$Lifecycle`. | Storage local ownership already precedes LockSettings in the original order. |
| `0x0c9c–0x0c9e` | Loads `LockSettingsService$Lifecycle.class`, calls `SystemServiceManager.startService(Class)`. | This pins the actual Samsung lifecycle/startup boundary. The exact guest replacement callsite and order remain unpinned by this table and require separate source evidence. |
| `0x0ca1–0x0ca8` | Looks up `lock_settings`, then calls `ILockSettings.Stub.asInterface`. | Publication is consumed immediately by the rest of startup. Canonical Binder/client compatibility is required at this point. |
| `0x1ae7–0x1aed`, `0x1b15–0x1b21` | Tests `android.hardware.fingerprint`; conditionally starts the real `FingerprintService`. | The feature declaration and actual provider startup are separate conditions. A class being present is insufficient. |
| `0x1b32–0x1b37`, `0x1b3c–0x1b3e` | Starts `BiometricService` through an actual outlined helper, then `AuthService`. | Fingerprint's constructor is part of a larger real registration graph. |
| `0x2332–0x2334` | Sends boot phase 520. | This reaches LockSettings' Weaver/DAR phase after service construction. |

The actual manager's `startService(Class)` checks assignability to its `SystemService` class, obtains a public `Context` constructor, creates the service, then calls `startService(SystemService)`. The latter records the service and calls its real `onStart` (`0x2c`). `startBootPhase` stores the phase and calls real `SystemService.onBootPhase` (`0xb1`). It is not sufficient to publish Binder names while omitting these owners and callbacks. The inspected late SystemServer runnable sends phases 550 and 600; the original LockSettings lifecycle separately contains a 1000 branch. This report does not claim to have inspected the complete caller chain that sends 1000.

Credential stream evidence, revalidated by the shared reader, supplies the next edges:

- `LockSettingsService$Lifecycle.onStart`: installs `AndroidKeyStoreProvider` (`0x0`), builds its real Injector and LockSettingsService, then publishes `lock_settings` (`0x18`).
- The actual LockSettings constructor starts `ServiceThread` (`0x192`), registers receivers (`0x20e`, `0x3ac`), constructs storage/database helpers, reads `LocalServices`, obtains biometric callback scheduling, creates Samsung DAR helpers and publishes `LockSettingsInternal` (`0x400`). Construction is already an active operation.
- Phase 520 obtains Weaver/configuration/used-slot information and Samsung DAR integration. Phase 550 calls `migrateOldDataAfterSystemReady`; phase 1000 posts further real work. Their mutations cannot be bypassed by declaring a service ready.

The `BiometricHandlerProvider` singleton is **not** an established missing-SystemServer blocker. Its actual `<clinit>` creates and stores the singleton itself (`0x0–0x5`). The callback and fingerprint getters lazily call `getNewHandler` when their cached handlers are absent. The scoped read does not inspect that helper's full implementation. The LockSettings constructor's own `ServiceThread.start` is independently observed. A null `LocalServices.getService` result also does not itself fail a `CHECK_CAST`; failure or incorrect authority may arise when the dependency is used. Neither point proves isolated construction impossible.

Fingerprint stream evidence identifies real publication of the global `fingerprint` Binder, Samsung extension/provider construction, and automatic cleanup/authenticator-ID work on initial/reconnected HAL acquisition. These startup paths must be included in the ownership gate. Calling a constructor or HAL getter is not a safe read-only device probe. See the fingerprint stream's report and body receipts for the sensor path.

## Canonical types and controlled loading

Observed loading paths:

- `ZygoteInit.getOrCreateSystemServerClassLoader` reads `SYSTEMSERVERCLASSPATH`, creates a path loader and caches it. `createPathClassLoader` supplies the system loader's parent and `java.library.path` to `ClassLoaderFactory`.
- Samsung `SystemServiceManager.startServiceFromJar` uses the manager's own class loader as the parent, obtains a `SystemServerClassLoaderFactory` loader, loads the class and starts it. The inspected factory may refuse loader creation unless its actual standalone-system-server/APEX policy permits it. This API does not demonstrate arbitrary package isolation or masking.
- Samsung's full `SystemServer.main` loads `android_servers` (`0x1c0`). This is a fact about that entry point. Directly importing selected service lifecycles does not, by itself, prove that the entire main entry or that whole native library must be substituted.

The bounded class comparison gives a useful distinction:

| Actual collision | Observed declaration result | Consequence/inference |
| --- | --- | --- |
| `SystemService` | Same declared method surface in both selected services archives. | Using the guest's canonical base for an imported lifecycle is not ruled out by this surface. Bodies/resources/native contracts still need review. |
| `LocalServices` | Same declared method surface; present in both framework archives. | One canonical registry can be a designed boundary. A second private copy would have a different static registry/class-key realm. |
| `SystemServiceManager.startServiceFromJar` | Samsung returns `void`; ColorOS returns `SystemService`. | Samsung callers of that exact descriptor cannot simply bind to the guest namesake. This is not proof that LockSettings itself needs the Samsung manager: its lifecycle uses the common `Context` construction route. |
| `ILockSettings` | ColorOS additionally declares `sanitizePassword` and `setLockscreenPasswordType`; Samsung has other additional methods. | A canonical guest facade needs real, audited semantics for guest calls. No universal success/default implementation closes credential changes. |
| `IFingerprintService` | The selected guest declaration is a subset of Samsung's, but Samsung's Stub adds other methods. | Common signatures are promising; actual transaction/Parcelable/callback and Samsung-internal call compatibility still require proof. |
| `SemPersonaManager` | Present in Samsung framework, absent from the selected ColorOS framework. | A concrete Samsung dependency to supply or mediate. Absence from this single archive is not absence from every guest jar. |

**Inference:** an ordinary additional jar is not evidence that Samsung definitions supersede already canonical guest classes. Conversely, a deliberately controlled loader could keep selected implementation/SPM/nested classes together while delegating genuine canonical Android types to the guest. That is a design to prove, not a demonstrated loader. Preserve same-source SyntheticPassword implementation/nested types; public verification signature parity does not make Samsung and ColorOS subkey derivation or OEM extension contracts interchangeable.

Samsung `LocalServices.addService` explicitly rejects an existing key with `IllegalStateException` (“Overriding service registration”). The corresponding guest behavior was not body-verified here. Either design must avoid two live local/Binder authorities; a name replacement is not a state/lifetime handoff.

## Concrete dependency and state ownership

The actual LockSettings constructor looks up and casts `StorageManagerService$StorageManagerInternalImpl` and reads `SupervisionManagerInternal`. This is an exact dependency edge, not an assertion that a missing lookup instantly crashes. If a canonical ColorOS object satisfies a same-name cast, that still does not make it the Samsung storage authority.

Storage stream source evidence shows the relevant Samsung storage implementation calling its real `mVold.unlockCeStorage(user, HAT-as-hex, derived-secret, HSUM-mode)`, updating its CE-unlocked users and invalidating caches. Samsung LockSettings also calls `IVold.setCeStorageProtection` directly. Therefore user mapping, actual vold Binder owner, host mount/key trees, HSUM policy and unlock notifications must agree. Substituting guest user 0 or a guest-storage success callback is not an implementation.

Other required edges include real UserManager/ActivityManager/DevicePolicy context services, StrongAuth scheduling, Samsung Persona/Knox/DAR dependencies, resources and original KeyStore namespaces. The exact resource IDs in Samsung bytecode are not portable guest policy by number; the resource stream is comparing selected actual entries. Loading missing Samsung jars does not itself establish those service objects, state or permissions.

The bounded resource proof is now concrete: LockSettings constructor resource `17891991` is Samsung `config_softwareLskfRateLimiterEnforcing` with base default false, but the same ColorOS ID is `config_startDreamImmediatelyOnDock` with base default true. ColorOS's same-name rate-limiter resource is a different ID and has base default true. The migration resource `17891665`, `config_disableWeaverOnUnsecuredUsers`, is aligned at base default false. Effective overlays were not measured. This demonstrates why passing a generic guest Context can change security policy even when Java linkage succeeds; it does not justify selecting a weaker value. Preserve actual Samsung policy/resources. See [resource compatibility](resource-compat.md).

The captured Samsung boot path includes `knoxsdk.jar`; its system-server path includes `knoxanalyticssdk.jar`, `mcfsdk.jar`, `services.jar`, `ssrm.jar`, `semwifi-service.jar` and APEX service jars. This establishes where the source runtime supplies dependencies, not that every listed jar must be imported. The selected service native/HAL closure and access policy belong to the fingerprint/storage/trust evidence streams. No native compatibility or SELinux permission was demonstrated by the startup read.

## Comparison of viable-in-principle designs

| Candidate | Concrete startup/ownership plan | Hard unresolved requirements |
| --- | --- | --- |
| **Guest-compatible facade plus controlled Samsung implementation** | Before guest LockSettings/fingerprint startup, select one implementation. Keep canonical guest Binder/client types; load the genuine same-source Samsung security implementation closure; supply audited real dependency owners; drive its actual lifecycle/user/boot callbacks. The facade preserves real results, timeout/progress/cancellation and caller identity. | Actual closure behind storage/UserManager/Knox/DAR; canonical argument/result classes; unsupported guest method semantics; host protector/enrollment/data ownership; resource/native compatibility; startup cleanup and migrations. No such facade is implemented. |
| **Selected Samsung authority in a separate process/runtime realm** | Establish a Samsung classpath/context/data realm and one process-local registry containing the actual necessary Samsung dependency owners. After an owned handoff, expose the audited authority through compatible guest-facing contracts. Guest services for the same authority must not start. | Retained native daemons alone are insufficient. The actual local dependencies may require substantial Samsung services; a tiny broker is unproved. UID/SELinux/caller authorization, resources, Binder names, current-user/boot phase routing, native session/cleanup and death/recovery must be demonstrated. |
| **Retain the existing Samsung system_server** | Preserve its existing credential/provider/storage objects and identities; isolate competing framework/UI/service ownership before the guest starts. | Current OneOS deliberately kills that process and suppresses its zygote. Keeping it requires a concrete separation of competing Binder/services, callbacks and return behavior. Existing objects cannot simply move to another process. The inspected SystemService API supplies no general stop-and-extract operation. |
| **Import the entire Samsung system_server** | Use Samsung startup/classpath/resources and all its real dependencies, with ColorOS as clients/presentation. | Expands framework/service ownership drastically and conflicts with a simultaneously booting guest server. Nothing inspected proves this is the minimum necessary closure or makes it acceptable by default. |

The strongest next implementation hypothesis is the first or second row, chosen after the actual dependency frontier is closed. The evidence does not yet select between them.

A source-supported construction order for either candidate is: establish its deliberate class/resource/context realm; establish and authenticate the actual storage/user/policy/local-service owners; start the selected LockSettings lifecycle through the compatible `Context`/`SystemService` contract; provide compatible publication at its actual `onStart` site; start the selected fingerprint/biometric/auth registration graph; then drive the real, justified phase/user callbacks. Each stage retains its threads, receivers, providers, registry entries and pending Binder/native operations before the next can publish. This is a proposed order, not code to run: startup cleanup/migration admission and every missing actual owner must be closed first. For a separate authority, phase/user information and protected results require an owned authenticated transport; for an in-guest implementation, the canonical local registry and guest publication must have a single owner before guest constructors run.

## OneOS boundary and next meaningful proof

Observed **0.4.55 source intent**, not verified installed behavior:

- `oneos_switch.sh:622` requests permissive SELinux; `971` stops host zygote; `999` kills `system_server`; `1011` keeps host zygote suppressed.
- `guest_start.sh:106–143` derives and exports guest classpaths; the successful path replaces inherited Samsung lists. Its failure fallback is a warning, not a supported mixed framework.
- `return_to_oneui.sh:78` protects retained native names including vold, Keystore2, installd and GateKeeper. This does not keep Java LockSettings/fingerprint services alive after their owner process dies.
- Existing GateKeeper/Weaver/biometric cleanup preservation producers remain in place. Their source intent is not proof that a new imported Samsung service is covered by their exact match sites, nor that the selected guest image has those patches.

A runnable-in-principle candidate must name, before any device proposal:

1. The exact guest startup sites suppressed/replaced, canonical facade interfaces, Samsung implementation closure, class-loader routing and resource/native inputs. Do not hot-replace a constructed guest security service.
2. One owner for host user/protector/enrollment/lockout/strong-auth and storage/key namespaces. Show the actual objects behind each local lookup. Metadata copies or matching class names cannot certify this.
3. The real startup/user/phase order and an admission barrier before migration, cleanup, enrollment or credential-changing work. Preserve OneOS's existing guards until an equally strong owned replacement is proved. Unknown state refuses authentication and writes.
4. Binder and native/HAL session ownership, exact calling identity, cancellation/death handling, pending operations and genuine restoration acknowledgement. Returning a success boolean or posting asynchronous cleanup is not drain proof.
5. A bounded separately approved device proof that performs genuine Samsung verification and an authentication-bound protected operation, then demonstrates cancellation/failure/return and later cold-boot preservation. A visible lockscreen dismissal is insufficient. No device proof is authorized here.

**Open status:** static startup and loader boundaries are established; isolated service construction, cryptographic/data ownership, native acceptance, safe handoff, credential synchronization and recovery remain unproved. This is not a working security integration.
