# Independent guest metrics producer review

Status: bounded source and prepared raw extractor review accepted, helper only. This
card does not admit a live DMS, execute OEM code or establish Android metrics.
The frozen UMS owner card remains unchanged.

## Independently checked original source

The existing exact source handles in
[context-display-contract.json](../inventory/context-display-contract.json)
identify ColorOS `DisplayManagerService$BinderService.getDisplayInfo(I)` body
`70326e8e9904bbdab0131911e881dc505956266c6fa4bbb4537b221afa38fe13`
and `DisplayManagerService.getDisplayInfoInternal(II)` body
`1f59a6b4d25a594743fa55a9614b59961e321b3269d4c5c8f356f026df3d9628`.
These actual bodies were read independently without a new broad scan.

Observed source: BinderService captures incoming `Binder.getCallingUid()`0,
clears identity4, passes the captured UID to the real internal getter10 and
restores identity on normal14 and exceptional19 paths. A producer must preserve
that real source subject; an outbound call under another process UID cannot
be declared equivalent to an arbitrary app caller.

The internal getter has different ownership paths. Its cached path takes one
CopyOnWriteSparseArray entry2, obtains info214, performs real access policy218,
applies frame-rate overrides306 and returns310. No enclosing mSyncRoot monitor
protects this path. If cache is absent for a nondefault display, source returns
null47. The default-display miss instead obtains actual mSyncRoot57, resolves
the logical display60/info66, applies overrides82/access88 and real backlight134,
zoom140 and benchmark146 extensions, releases the monitor150 and returns151.
Denial/absence and thrown errors are distinct source outcomes.

The selected entry methods alone did not prove an unconditional copy. Power's
subsequent exact source handle closes that question:
`getDisplayInfoForOverrides` always allocates DisplayInfo0, initializes2,
`copyFrom`5, applies frame-rate8/presentation11 overrides and returns the new
object14. The two selected override methods change modes/flags, do not retain
the argument, and do not change the five metrics. Original `copyFrom` transfers
the five primitives directly: appWidth36/38, appHeight40/42, density170/172,
XDpi174/176 and YDpi178/180. No arithmetic/boxing/wire conversion intervenes.

## Independent cache publication, writer and alias continuation

`CachedDisplayInfo` does not defensively copy: its constructor stores exact
DisplayInfo at5 and frame-rate array7; `info()` returns the field at0/2.
Those record fields are final. The actual producer is
`LogicalDisplay.computeCurrentDisplayInfoLocked`: allocate new DisplayInfo0,
copy genuine base/WM fields11, construct new CachedDisplayInfo23/29, publish
through the actual shared CopyOnWriteSparseArray32 when supportedModes is
nonempty, then return the same DisplayInfo35. The same computed object may be
retained by LogicalDisplay's DisplayInfoProxy. The source getter can return
that internal alias; its name does not establish immutability.

Actual `CopyOnWriteSparseArray.mContainer` is volatile. Its `put` synchronizes
on its own mLock, replaces an existing key using SparseArray.setValueAt52,
and clones/publishes a new container for a new key94/98. **Existing-key updates
do not clone the container.** The getter reads one entry from one container;
there is no extra DMS monitor or invented latest-generation acknowledgement.
A retained record can remain an older original result during replacement.

The independent exact five-field reference scans cover captured ColorOS services
and oplus-services. Their complete direct scalar-write receivers are:

| Writer | Actual destination |
| --- | --- |
| LogicalDisplay.updateLocked | distinct final mBaseDisplayInfo, created in its constructor; recomputation publishes a new DisplayInfo |
| DisplayContent.computeScreenConfiguration | new DisplayInfo copy45/49, then appWidth68/appHeight74 |
| DisplayContent.updateDisplayAndOrientation | its own mDisplayInfo, allocated once118–123 in its constructor; the field scan finds only that assignment |
| DisplayInfoOverrides.lambda$static$0 | destination argument of the original field copier; compute passes its newly allocated result |
| OplusZoomWindowManagerService.getZoomModeDisplayInfo | fresh slow-path return supplied by DMS; app dimensions46/58 |
| DisplayManagerServiceExtImpl.getBenchMarkDisplayInfo | the same fresh slow-path result; physical DPI47/55 |

The vendor archive has no logicalDensityDpi writer and no DisplayInfo.copyFrom
direct call. The ten services copyFrom calls target new return objects, original
base/override objects, owned WM/DeferredDisplayUpdater fields, or mapper
temporaries. The relevant constructors create those separate objects; mapper
and WM copy source data into their own targets. DisplayInfoProxy setters replace
its stored reference or clear it and invalidate the original local display cache;
they do not mutate a published DisplayInfo's five metrics.

The original WM copier copies base fields, then applies the actual
WM_OVERRIDE_FIELDS updater to its destination. Its source static initializer
selects the original updater lambda. Subsequent LogicalDisplay updates/rebinds
recompute and replace the record, rather than modify these published metrics.

The exact services scan contains35 calls to `getDisplayInfoLocked` in31 methods.
Their selected bodies were inspected for alias use, including these substantive
continuations:

- TopologyCoordinator consumes fields into topology/string metadata and its
  source predicate. Its vendor onDisplayUpdate delegates to actual
  FlexibleWindowManagerService/OplusConnectedDisplayManager: only primitive
  dimensions/density enter DisplayLayout under the latter's mDisplays lock.
- LogicalDisplay's actual LogicalDisplayExt reads displayId for Mirage policy;
  the actual Mirage rotation delegate only reads rotation. They do not retain
  or mutate DisplayInfo.
- ModeRequestManager.getDisplayInfo can return the original/current reference
  or its stored snapshot; this is an alias, not another defensive-copy proof.
  The checked downstream scalar/copy writers still target their distinct owned
  objects. No published-five-scalar mutation was found in this bounded cut.
- Nonoverride copies, read-only access/group tests, stats, and mapper comparisons
  consume original fields/copies. Source code inspection did not invoke screenshot
  or any other operation encountered while following these aliases.

**Review conclusion:** for the pinned original implementations and genuine
selected feature implementations, cached values support one coherent original
five-scalar return copy. Mutable source base/WM objects are separated from the
published record. The slow default-display path starts from that same unconditional
return copy before its checked vendor modifications. The authored extractor need
not add an enclosing lock around arbitrary external calls. A lock would not replace
the required source/code/receiver/feature-implementation admission.

This conclusion is limited to the five scalar fields and selected source profile;
it does not certify every nested DisplayInfo object/array, reflection/native or
unreviewed implementation mutation, the effective installed code, live cache
freshness, display generation, or hardware correctness. Property/cache retirement
and current real subject checks still belong to the concrete integration owner.

## Prepared extractor and independent authored tests

The reviewed source is
`compat/android/com/appleexploit/oneos/security/authority/PreparedGuestMetricsProducer.java`,
SHA256 `72b0f4cdbb984c4d3b59724fd4c671771f8bf7e81c48184351e9ce77aa27b8f7`.
Root approved its raw prepare/capture/Sample API after the source cut. No concrete
production defect was found. This is acceptance of this bounded extractor,
not its still-missing runtime/source admission.

Independent code observations:

- Preparation retains the provided receiver strongly and caches the exact
  declared public/nonstatic/nonabstract getter, returned Class, and six declared
  public/nonstatic primitive fields. Unexpected receiver/return names or member
  shapes fail. Genuine reflection access must succeed; name/shape checks do not
  authenticate the actual receiver/code/epoch.
- Capture calls that getter once on the current thread. A getter failure is
  unwrapped from InvocationTargetException and its exact original Throwable is
  thrown before any identity postcheck can mask it. Reflection failure does not
  become null or a default.
- On normal success, including null, actual Binder UID/PID reads are checked.
  Nonnull results must have the exact prepared Class and requested displayId.
  Five scalar loads are local; displayId and actual UID/PID are checked again
  before Sample construction. Sample contains only five private final ints;
  floating values use Float.floatToRawIntBits on Field.getFloat values.
- There is no retained DisplayInfo, default/sanitizer, extra getter, new cache,
  monitor, identity adoption, service lookup, publication, or source-ready flag.
  Concurrency/reentry use independent local variables. External lifetime/epoch
  admission remains required through all work and delivery.

The independent probe ran the **unchanged actual SDK37-compiled production class
bytes** from build receipt
`out/guest-metrics-producer-build/20261105T203639957947Z-2343ce1549274da5b453fe4fac510259/receipt.json`,
SHA256 `cc4a619a9835ab409274887121ccacd19f2ab91516866234df8a3e3ab1af9d21`.
The artifact has three authored class definitions, including javac's synthetic
private-constructor marker. No production hooks, source changes, patched class
bytes, OEM implementation or SDK runtime stub was used.

Root explicitly allowed isolated authored Binder/DMS/DisplayInfo models with
matching binary API names solely to link and exercise that authored production
class under JDK. The test runtime classpath contains only the authored fixture
classes and exact production classes: **no android.jar or OEM archives/classes**.
These models perform no real Binder/native identity/DMS operation. Their source,
commands, output and class/source hashes are in ignored
`out/guest-metrics-producer-review/`; `AUTHORED-PROBE.json` is the receipt.

Twenty-seven focused checks passed, covering one getter call, exact checked/
runtime/Error identity even when the fixture changes caller identity before
throwing, genuine null, wrong display, subclass refusal, UID/PID drift before
publication and after scalar loads, signed integer values, quiet-NaN payloads,
negative zero, infinity/subnormal bits, scalar-only immutable retention, cached
metadata identity, nested calls and two deliberately overlapping threads.
Three separately compiled malformed authored shapes were refused: static
getter, correct-field return class with the wrong binary name, and wrong scalar
field type. These are malformed fixture variants, not altered production code.
The probe does not claim signaling-NaN payload behavior on an untested Android
implementation or native-memory/Parcelable bit equivalence.

The source-phase snapshot predating this code/test successor is retained with
original hashes in `out/guest-metrics-producer-review/source-phase-snapshot/`
and `HISTORICAL-SOURCE.json`. The source/D8 build remains separate from the JDK
fixture receipt; neither is Android acceptance.

## Remaining admission and consumer obligations

Integration still requires the exact real initialized guest DMS object/getter and
selected display/current process subject, source/code/generation retention, one
coherent genuine original DisplayInfo result, exact owned scalar/float-bit
extraction, and reentry/retirement handling after external calls. Source absence,
access denial, failed lookup, thrown getter, death or uncertain progress cannot
become invented default metrics. A generic trusted interface is not the missing
actual source owner. This card does not require a full DisplayInfo wire converter
or stand-in Samsung policy fields.

The exact runtime source/epoch/feature-implementation owner remains missing.
Same caller IDs, expected class strings and a prepared Sample do not supply it.
Samsung CompatSandbox, actual ResourcesManager/configuration/compatibility
calculation, source-preserving boot retarget, resource/native ownership and full
security bootstrap are external. No Android/OEM/native/phone execution or
authentication/metrics/hardware acceptance follows from this review.
