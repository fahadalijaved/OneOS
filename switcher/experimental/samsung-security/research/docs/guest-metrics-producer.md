# Prepared raw guest metrics producer

`PreparedGuestMetricsProducer` prepares cached reflection metadata over one retained, externally admitted **real ColorOS DMS BinderService**. `capture(displayId)` invokes its genuine `getDisplayInfo(int)` once on the same thread and returns an immutable Sample containing only appWidth, appHeight, logicalDensityDpi and the two DPI quantities encoded as `Float.floatToRawIntBits` of actual Java field reads. It does not produce final Samsung metrics, a full DisplayInfo or an admitted authority.

The production source is `compat/android/com/appleexploit/oneos/security/authority/PreparedGuestMetricsProducer.java`, SHA256 `72b0f4cdbb984c4d3b59724fd4c671771f8bf7e81c48184351e9ce77aa27b8f7`. Root approved this exact RAW API after independent source ownership review. Shape checks are not source attestation: genuine receiver/code/subject/currentness/generation/lifetime admission remains external and unassembled.

## Actual getter, cache and copy ownership

The exact receiver is `com.android.server.display.DisplayManagerService$BinderService`, a non-public final class extending the original IDisplayManager.Stub. Its public `getDisplayInfo(int): android.view.DisplayInfo` captures real Binder caller UID at PC0, clears identity at4, passes the captured UID to the original internal getter at a, then restores identity at e/13 on success/failure. Calling this actual method directly on the same Binder thread preserves that incoming metadata subject; posting work to another thread or adopting another caller does not.

The original internal getter has two paths. Its cache path reads `LogicalDisplay.CachedDisplayInfo.info()`, checks real access, then applies per-caller overrides. Its cache-miss path obtains DMS's actual sync root, obtains current LogicalDisplay info, applies overrides/access/OPPO adjustments, then returns. The extractor adds no new lock.

The record itself is **not a defensive copy**: its constructor stores the passed reference and `info()` returns that alias. The bounded five-scalar publication/copy cut closes differently:

* `computeCurrentDisplayInfoLocked` allocates a fresh DisplayInfo, applies original base/WM override copying, builds a CachedDisplayInfo record and publishes it through CopyOnWriteSparseArray. DisplayInfoProxy stores/replaces/nulls the pointer rather than editing those previously published five scalar values. Existing-key COW.put can use setValueAt; no claim is made that every map update clones the container.
* Actual ColorOS `getDisplayInfoForOverrides` is six instructions and **unconditionally** creates a new DisplayInfo, copyFrom(source), applies frame-rate and presentation masking, then returns that new object. It does not conditionally return the cached input. These two override helpers do not escape the copied object; their mutations concern modes/flags.
* The admitted backlight, zoom and benchmark paths return the same private copied object. Backlight writes its separate backlight field; zoom can change dimensions/rotation; benchmark can change the two DPI fields. The selected implementations neither retain nor pass that DisplayInfo elsewhere after returning it.
* Additional published-info alias leaves were followed: LogicalDisplayExt/Mirage read only displayId/rotation, while FlexibleWindowManagerService→OplusConnectedDisplayManager copies scalar dimensions/density into its own layout under its own lock. They do not retain or mutate the supplied DisplayInfo. Independent Table review additionally checked the relevant five-scalar writers, copy receivers and cache/publication callsites.

This is a source proof for the **five values in these pinned implementations**, not a universal immutable DisplayInfo contract, an actual installed-image claim or a latest-generation certificate. Nested arrays/objects are not exported. Unknown extension implementations or changed source cannot inherit this proof from method names.

Inputs: original ColorOS services.jar SHA256 `66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3`; oplus-services.jar `cd2be8190990242cfcf01327ff4482404dbc308093fa3871a749f053f3849a39`. The new bounded audit records21 exact bodies plus two reused getter/internal bodies,17 checked edges and receipt/raw/normalized-body identities in `inventory/guest-metrics-producer.json`. Independent source review is recorded in [the review](guest-metrics-producer-review.md). No OEM implementation was executed or copied into normal sources.

## API and failure behavior

`prepare(Object retainedRealDmsBinderService) throws ReflectiveOperationException` caches the exact declared getter, its returned Class and six declared public primitive Fields: displayId for subject checking plus the five quantities. It verifies expected names/modifiers/types and requests reflection access to the public getter on the non-public service class. Real guest reflection/hidden-API access must succeed; there is no fallback or fake permission grant.

`capture(int displayId) throws Throwable`:

1. Captures native Binder UID/PID and invokes the cached genuine getter exactly once on that thread.
2. If invocation throws, rethrows its exact original cause. A new identity-check error cannot mask that original Throwable, and no Sample is published.
3. On successful return, checks UID/PID. Genuine null is returned as absence, never default metrics/readiness.
4. Requires exact returned Class and requested displayId, reads the five primitive values into locals, rechecks displayId and UID/PID, then creates Sample.

Sample is static/final, has five private final int storage fields and retains no DisplayInfo, service, producer or policy owner. DPI bits describe Java `Field.getFloat` values passed to `Float.floatToRawIntBits`; they are not a claim about untouched native memory or Parcelable byte representations. There is no sanitizer, guessed density/size, second getter, new monitor, identity clear, own cache, service lookup, endpoint publication, callback or boot retarget.

Root and Table source reads found no concrete defect in this approved cut. Exact production-only SDK37/D8 evidence belongs to [the build report](guest-metrics-producer-build.md); Table's separately authorized authored-fixture mechanics evidence belongs to [the independent review](guest-metrics-producer-review.md). Those reports are separate from this frozen source proof and cannot establish Android/native identity, genuine DMS or source admission. No Android, OEM, JNI or phone execution is part of this work.

## Remaining consumer and runtime gates

The retained target and Sample are not provenance. A genuine owner must retain the real initialized DMS, effective installed code/extension graph, chosen display and current generation through acquisition, external/reentrant work and retirement. Same UID/PID and matching class/field strings do not prove those facts. Failure, death, replacement and uncertain completion require the actual external owner; this extractor has no independent lifetime/readiness certificate.

These are **raw guest values**. The future Samsung consumer must preserve the actual CompatSandbox flag/ActivityThread Configuration transformation before the selected getAppMetrics calculation, then the actual ResourcesManager Configuration/appBounds/fontScale and CompatibilityInfo rules. Five fields are that calculation's read set, not proof the preceding sandbox is inert. Actual boot/framework callsite selection, helper visibility, source admission, inverse retarget, native/resource ownership and complete Context/security bootstrap remain open. The frozen Context card and prepared two-call display bridge are unchanged.

Recheck selected source/metadata with `python tools/audit_guest_metrics_producer.py --summarize`. `--read` acquires only the listed static bodies with the shared DEX041-safe reader. Raw OEM evidence remains in ignored firmware; authored build/fixture outputs remain ignored out. No Git, device changes or endpoint installation occurred.
