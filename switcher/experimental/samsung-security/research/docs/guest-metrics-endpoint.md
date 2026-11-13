# Guest metrics lifecycle and endpoint proposal

The original ColorOS DMS has an exact acquisition seam for the already reviewed RAW five-value extractor: **retain the BinderService born in the real `DisplayManagerService.onStart`, then enable a metadata projection only after that same DMS successfully completes phase100**. This is a source/API proposal. No lifecycle hook, endpoint implementation, DEX retarget, publication or service execution was produced. Default is off. This does not complete Samsung Context bootstrap or security integration.

The static ledger [guest-metrics-endpoint.json](../inventory/guest-metrics-endpoint.json) pins 14 new and two reused bodies, 36 checked instruction edges, the original archives and nine immutable OneOS sources. It records raw method lines, complete container/header identities and normalized body hashes. Recheck with `python tools/audit_guest_metrics_endpoint.py --read --summarize`; these are static reads only. The [RAW extractor](guest-metrics-producer.md), its separate SDK build and independent authored-fixture review remain frozen.

## Actual construction and publication

Observed original ColorOS `services.jar` SHA256 `66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3`:

| Actual method / hexadecimal PC | Source fact |
| --- | --- |
| `SystemServer.startBootstrapServices` `1fd,1ff,203,205` | Loads the actual DMS Class, starts it through SystemServiceManager, casts and retains that returned original service. |
| `SystemServiceManager.startService(Class)` `49,53,5a` | Resolves the real Context constructor, invokes it and starts the resulting service. The instance overload adds it to the actual service list at30 and calls `onStart` at37. |
| DMS public constructor `2,5` | Creates the original Injector and delegates to the actual two-input constructor. |
| DMS two-input constructor `2a,cd,d3,fe,100,10d,2ce` | Owns its actual SyncRoot; creates its vendor extension through ExtLoader; retains Injector, Context and original display-thread Handler; initializes the extension with that Context and lock. It also constructs the real mapper/directors/persistent-store dependencies. This is not permission to create a second DMS. |
| DMS `onStart` `5,8,f,12` | Loads persistent/stable values under the original lock, schedules original handler message1 and invalidates the display-info caches. |
| DMS `onStart` `15,17,1c,21` | Constructs one actual BinderService into v0, passes that same v0 to `mDmsExt.onStart(Binder)`, then publishes it as global `display`. |
| DMS `onStart` `28,32,35` | Publishes original extension and DisplayManagerInternal LocalServices, then returns normally. v0 still holds the actual born Binder; it is not overwritten after construction. |
| BinderService constructor `0,2,6,a` | Retains its actual outer DMS, obtains that owner's Context and PermissionEnforcer, then initializes the actual IDisplayManager Stub. |
| SystemServer bootstrap `211,213` | Immediately requests original SystemServiceManager phase100 after the DMS creation block. |

DMS has **no declared `mBinderService` field**. An imagined getter of that name is not an acquisition route. The existing OPPO extension callback is genuine but its implementation only constructs the real `OplusDisplayManagerServiceEnhance` and attaches it with `Binder.setExtension` at PCd; it does not retain the passed base Binder. Preserve that original extension behavior.

## Minimum lifecycle seam, still unimplemented

Propose two narrowly selected edits to original **base services.jar** bodies, rather than invent an existing retained owner or depend on unproved reverse visibility from the base services loader into an OPPO extension loader:

1. At DMS `onStart` normal tail, after original PC32 and before return35, pass original `this` and still-live v0 to a source-profile-selected lifecycle capture factory. Prepare the frozen extractor once over that exact BinderService; preparation reads metadata only. Hold the exact DMS, Binder, prepared extractor, future endpoint and defining code owner together. No getter call, endpoint publication or readiness follows from this capture.
2. At original DMS `onBootPhase` normal completion, before return114, take a branch only for the **actual phase argument100** and the same captured DMS identity. Permit the corresponding metadata endpoint to activate/publish once, only when the separately admitted feature/source profile is enabled. Failed capture/preparation disables this optional projection without replacing the original DMS. Preserve original Throwable behavior and original lifecycle work; do not transform a failed original start/phase into success.

The phase100 source checks logical display0 and the real VirtualDisplayAdapter under mSyncRoot at1a/20. Success exits the monitor at25 and jumps at26 to f9; it still executes original extension callback fb and original tail through111 before return114. Timeout creates and throws a real RuntimeException; it cannot reach the proposed success hook. `onBootComplete(100)` in the extension is not a fully booted-system receipt: most of that extension's boot-completed work is guarded by1000. Phase100 does not freeze subsequent display configuration, prove WMS/input/systemReady, or establish current cache generation. Subsequent original DMS initialization continues.

Observed classloading is concrete but not an installed hook: ColorOS `ZygoteInit.getOrCreateSystemServerClassLoader` reads actual `SYSTEMSERVERCLASSPATH` and caches a loader; `createPathClassLoader` uses ClassLoaderFactory with the real parent/native-library path. DMS is an actual class constant in that SystemServer path. The complete future lifecycle/endpoint/producer dependency closure must be selected and visible to **that actual DMS defining loader**, for example through a reviewed patched services classpath artifact. Merely putting a helper in an app DEX or supplying a same-name Class is insufficient. Actual guest classpath, source selection, duplicate definitions, compiled-code/DEX retarget and inverse preservation require their own admission. The hook proposal does not prove any of them.

## Proposed bounded metadata protocol

This is a feature-specific protocol under the **same original `getDisplayInfo` caller/access visibility policy**, as selected by root. It is not an authority-only channel. A possible distinct alias is `oneos.guest_display_metrics.v1`; its eventual availability/collision policy and ServiceManager publication owner remain unimplemented. Never replace global `display` or claim a discoverable alias is private isolation or Samsung authority attestation.

| Item | Proposed exact v1 envelope |
| --- | --- |
| Descriptor | `com.appleexploit.oneos.security.IGuestDisplayMetrics.v1` |
| Read | transaction1; synchronous flags0; nonnull reply |
| Request | interface token, int version1, int requestedDisplayId; reject trailing data |
| Successful reply | normal Binder no-exception envelope, int version1, int echoed displayId, int status0=ABSENT or1=SAMPLE |
| SAMPLE tail only | five fixed ints: appWidth, appHeight, logicalDensityDpi, physicalXDpiBits, physicalYDpiBits |
| ABSENT tail | none; it means the genuine getter returned null under the actual caller policy |

Only a bounded token and two scalar request ints are accepted; no arrays, arbitrary Parcelables, supplied dimensions, caller UID/PID, caller-selected source owner or attestation fields. The response has three or eight scalar ints after its exception envelope. Future clients must reject mismatched version/subject/status/trailing data. The DPI quantities mean `Float.floatToRawIntBits` of actual Java field reads, not untouched native/Parcelable bytes. Values are RAW guest metadata, not final Samsung metrics.

The endpoint must call frozen `capture(displayId)` once on the incoming native Binder thread. It must not clear identity, post to a Handler, use a second lookup, or substitute a system-UID transport hop. The actual DMS getter captures native callingUID before its own original clear/restore and applies its original access/override policy. The prepared extractor checks native UID/PID around successful/null capture and after its five reads. No invented UID allowlist or extra grant is needed for this metadata-specific policy; UID1000 alone never attests the Samsung security authority.

Malformed envelope/unsupported version is rejected before the getter. Genuine null remains ABSENT; an original getter Throwable is rethrown as its exact cause within the direct call. Binder's supported exception serialization can preserve supported exception meaning, not arbitrary Java Throwable object identity across processes; an unsupported transport failure must fail the transaction. Denial/exception/false transact/death/unavailable endpoint must never become ABSENT, default metrics or readiness. Do not retry an uncertain transaction implicitly. Unknown methods must follow ordinary Binder rejection/super behavior, not manufacture metadata.

## Lifetime and Samsung consumer

The source-owned lifecycle cell retains the exact objects and code loader. Publication is once per admitted DMS instance after successful original phase100; do not replace an occupied alias, rebind a new arbitrary DMS or infer a fresh generation from a service name. Future implementation needs explicit retirement: stop accepting calls, retain active stacks until they finish, prevent a retired result from publication and invalidate the Samsung bootstrap consumer before OneOS return/guest death. Native Binder endpoint identity/death can delimit this process instance; neither it nor an invented counter proves physical-display/cache freshness. No callback/cache/update/drain subsystem was added.

The Samsung process may preserve its real code/view before guest startup, but **Context construction waits for an admitted live metadata result** and actual consumer call ordering. The endpoint does not solve the separate eager two-read display adapter, complete process-local ServiceManager cache map, real guest endpoint/code/profile/generation admission, or original Samsung CompatSandbox/configuration/ResourcesManager/CompatibilityInfo calculation and boot-visible consumer retarget. Absent or unavailable required physical-display input leaves bootstrap unready.

## Current OneOS patch producer, not installed bytes

The immutable 0.4.57 commit is `1f2c2aa45ab8a7dc81384f6b67962d1e9cf7fefe`. Raw fetch receipts and download history are preserved under ignored firmware; no patch scripts were executed.

| Pinned producer source | Relevant actual transformation |
| --- | --- |
| `make-overlays.sh`189–195,277–280 | Applies active-mode fallback and conditional Qualcomm secondary-panel policy patch to services; it rebuilds selected DEX. |
| `display_mode_specs.py`40–90 | On a matched null-specs path, derives fallback desired mode from actual DynamicDisplayInfo.activeDisplayModeId/token and sets unrestricted refresh ranges; original default-display initialization semantics can therefore differ from the donor. |
| `qti_builtin_display_public.py`52–110 | If the Qualcomm branch exists, changes second built-in panel private/own-content flags. Source conditional intent is not evidence this branch exists in the selected ColorOS donor or installed image. |
| `make-overlays.sh`317–320,339–354 | Applies vendor wait/boot fixes, backlight helper and resolution-table guard to oplus-services. |
| `samsung_backlight_curve.py`20–94 and helper | Inserts real brightness-to-nits conversion followed by authored upstream panel curve in LocalDisplayDeviceExtImpl. The helper reads `ro.oneos.panel_scale_milli`; it is not a metrics provenance mechanism. |
| `oplus_resolution_tables.py`51–75 | In OplusResolutionManagerFeature.init, disables resolution-switch support only if both actual density table properties are empty. It can affect subsequent density choices; no fabricated640 or assumed unchanged values here. |
| `oplus_wait_for_service.py`55–91; `oplus_boot_hangs.py`55–160 | Replaces selected waits/null-handles absent OPPO service paths and removes specific GPU/zygote/diagnostic work. No metrics endpoint or born-Binder retention is implemented. |
| `guest_start.sh`106–139 | Derives guest classpaths and exports them, with an explicit failure path which can retain inherited host lists. Script intent does not identify the actual loader/code bytes. |

These seven selected patch files do not implement this acquisition or endpoint, and the hook addresses above are from original donor bodies. Other patch producers and exact rebuilt/installed bytes are outside this bounded comparison. A future source/DEX admission must check the actual selected patched bodies and configuration rather than assume original body offsets survived. No Android/ART, real DMS endpoint, native caller or Context runtime acceptance follows from this report.
