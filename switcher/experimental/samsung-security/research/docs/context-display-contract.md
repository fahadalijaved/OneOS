# Context display continuation and narrower metrics cut

The next required DMS interface read is **Samsung `getDisplayInfo(displayId)` transaction7 → original ColorOS transaction1**, synchronous flag0. Its reply **cannot be relayed unchanged**: Samsung serializes59 top-level fields, ColorOS58, with57 shared fields. Two Samsung-only policy slots occur in the middle, and a ColorOS-only backlight slot occurs near the end. No expanded Binder component, full DisplayInfo converter, guessed policy value, runtime retarget or cache installation was authored here.

The concrete next investigation is a **narrow genuine metrics projection** at the original system-Context callsite. It can avoid manufacturing a full Samsung DisplayInfo if its real producer, exact five-field data provenance and original configuration/compatibility calculation are closed. It is a proposal, not a prepared runnable API or an accepted Context.

All observations concern the pinned captured Samsung/ColorOS framework/services inputs. `inventory/context-display-contract.json` records50 new exact bodies, seven reused bodies,16 checked PC/reference edges, complete ordered top-level read/write fields, writer operations and wire/callback mappings. This is static evidence; no Android/OEM/JNI/service code, native binary or phone was executed. Prior bridge, probe and reports remain unchanged.

## Actual cold path, cache and callback condition

The original `ContextImpl.createSystemContextInner` calls `ResourcesManager.getConfiguration` at PC20, then `getDisplayMetrics` at PC26 and `Resources.updateConfiguration(config,metrics)` at PC2a. `ResourcesManager.getDisplayMetrics()` obtains its actual `mResDisplayId` and `DisplayAdjustments.DEFAULT_DISPLAY_ADJUSTMENTS`. The overloaded method obtains DisplayManagerGlobal, calls `getDisplayInfo(displayId)` at PCb, and invokes the actual `DisplayInfo.getAppMetrics` at PC29 when information exists. The actual null-info branch calls `DisplayMetrics.setToDefaults`; it is not permission to simulate missing display or turn an error into default metrics.

DisplayManagerGlobal uses real DisplayManagerInternal when present. Its fallback `getDisplayInfoInternal` queries `mDisplayCache` at PCd; the selected cache recompute calls real `mDm.getDisplayInfo` at PCa. The uncached path calls that same method at PC35. Nonnull information passes through Samsung CompatSandbox at PC42, then `registerCallbackIfNeeded` at PC45. CompatSandbox can change app/logical dimensions using genuine current original Configuration; it is not a no-op assumption.

**Fresh-state nuance:** the original DMG constructor sets registered mask0, all three implicit-registration booleans false, native-callback dispatch false and empty display/topology listener collections. In precisely this fresh state, `calculateEventsMaskLocked` returns0. A real local callback Binder is created and retained, but `updateCallbackIfNeededLocked` compares mask0 to registered0 and returns without remote registration. This is a source conditional, not observation of a running process or permission to suppress real listeners. Later listeners/native/snapshot/topology changes can require registration.

The actual PropertyInvalidatedCache query checks its nonce/reserved/bypass state, recomputes on misses and stores real results. `getCurrentNonce` delegates to the actual NonceHandler. Its selected factory can choose local, shared-memory system-namespace or system-property handlers. The effective handler/native invalidation region, writer/generation and host/guest coherency have not been established. Cache presence, invalidation notification and an applied callback are distinct facts; no shadow cache or forced disable was introduced.

## Complete top-level payload and genuine policy gap

Both exact DisplayInfo writers and readers were inspected. Their ordered field sets match within each source; the inventory lists **every field in wire order**, not declaration order, plus actual writer call PCs. Both use real collection counts, Parcelable/class framing and nested serializers. Source-compatible class names alone do not certify nested payloads or float-bit preservation.

| Wire difference | Samsung | ColorOS |
| --- | --- | --- |
| After `defaultModeId` | `refreshRateMode`, `appSensorAxisRemapRequired`, then `userPreferredModeId` | Directly `userPreferredModeId` |
| After `hdrSdrRatio` | Directly thermal data | `backlightType`, then thermal data |

Missing slots would shift subsequent reads and corrupt interpretation. A converter cannot just drop a suffix, relabel fields or use zeros. The nested DisplayAddress, DeviceProductInfo, DisplayCutout, FrameRateCategoryRate, frame-rate-velocity list, Display.Mode/HdrCapabilities, RoundedCorners, DisplayShape, RefreshRateRange and thermal SparseArray payloads still require their own complete conversion proof; their equivalence is not claimed. The previous two-read native OverlayProperties proof covers none of these.

The Samsung-specific fields have real producers:

* `LogicalDisplay.updateLocked` copies `mRefreshRateMode` at PCb1→b3 under the actual feature condition. The mapper initially sets that mode0, but a real DMS consumer later updates it at PC58, marks the refresh/mode group changed and calls logical-display-change handling. An initial value does not establish the current mode.
* Samsung DMS captures real caller UID before clearing identity. Under its actual sensor-axis feature/WMI condition, PC1c calls `WindowManagerInternal.getAppSensorAxisRemapRequired(uid)` and PC20 writes the result. The real WMI implementation resolves the UID through PackageManagerInternal, then consults `MultiTaskingAppCompatController.mAppSensorAxisRemapRequiredOverrides`. Its genuine missing-name/missing-override branch returns the source disabled constant; the branch/state has not been proved for this authority, even for UID1000. No blanket system-UID shortcut was found in the selected method.

Guest `getDisplayInfoInternal` preserves its access/frame-rate policy and reaches actual OPPO backlight/zoom/benchmark extension calls. Those are genuine guest outputs to identify/admit, not values to replace with canonical defaults. Outbound metadata requests see the authority process's UID; they do not preserve a public app credential caller.

## Conditional callback wire and ownership

Registration is Samsung tx11 → ColorOS tx5: descriptor, callback Binder, long event mask, synchronous flag0 and actual exception reply. Both real services capture PID/UID, clear/restore identity and enter their callback registry. They can reuse the record for that PID, update its mask, link death/store a new record and send a snapshot during registration. ColorOS additionally reaches its actual proxy-Binder extension. Registration return alone is not callback application or a replacement-callback acknowledgement.

| Common callback | Both source/guest transaction | Payload / flags |
| --- | ---: | --- |
| `onDisplayEvent` | 1 | displayId:int, event:int; oneway1, null reply |
| `onTopologyChanged` | 2 | typed DisplayTopology; oneway1, null reply |
| `onDisplaySnapshot` | 3 | connected:int[], added:int[]; oneway1, null reply |

Proxy writes and Stub dispatches match for those common envelopes. Samsung declares four additional vendor callbacks; no guest sender support or automatic mapping is inferred. The complete nested DisplayTopology payload and all mask/event policy equivalence remain unproved. Source event handling can re-enter `getDisplayInfoInternal`, update display-ID caches, signal native refresh-rate callbacks and deliver listener work; snapshots update the real cache under its lock. Retain exact callback/receiver, source/code/generation and all active consumers before registration; real deregistration/death, queued delivery and applied-state/drain ownership remain external. No callback wrapper or registration was implemented.

## Precise projection proposal for the next gate

Investigate retargeting **only** original `ContextImpl.createSystemContextInner` PC26 from `ResourcesManager.getDisplayMetrics()` to a reviewed authored static target conceptually shaped as `DisplayMetrics snapshotForSystemContext(ResourcesManager exactOriginalOwner)`. This names a prospective seam, not an implemented or admitted API. It must not alter unrelated DisplayManagerGlobal users, replace global `display`, fabricate a full DisplayInfo or assert that the existing two-read bridge completes Context.

The selected Samsung `getAppMetrics`/`getMetricsWithSize` calculation reads only these five DisplayInfo inputs:

`appWidth:int`, `appHeight:int`, `logicalDensityDpi:int`, `physicalXDpi:float`, `physicalYDpi:float`.

It additionally uses actual original Configuration.fontScale/appBounds and actual CompatibilityInfo adjustment. ResourcesManager's chosen configuration depends on its genuine display ID and DisplayAdjustments configuration; its current resource configuration is selected when the default configuration matches that owner. Preserve those exact identities/values and apply compatibility/font scaling once. Already-scaled guest Resources DisplayMetrics would risk double application and is not the proposed input.

The preferred producer shape to investigate is a genuine guest-side projection of **one actual guest DisplayInfo result** into an owned raw five-field snapshot, with display/caller-subject/current-DMS generation and exact float bits. That avoids crossing an unproved full Parcelable and avoids inventing the two Samsung policy fields. A guest-side producer/endpoint is **not currently implemented or admitted**. Alternatively, a source-profile-complete parser would have to prove all framing it consumes; raw field offsets or a caller-supplied five-value object are not provenance.

The root bootstrap owner must retain the real endpoint/code/state view, selected display and generation, the exact original ResourcesManager/configuration/compatibility owners and the result's lifetime. It must handle coherent snapshots, changes/reentrancy, cache invalidation, endpoint death, false transact, exceptions, cancellation/uncertain completion and return retirement. Samsung `RemoteException.rethrowFromSystemServer` actually throws DeadSystemRuntimeException or RuntimeException; it does not authorize an error-to-null/default fallback. For the proposed physical-display bootstrap, absent/unauthenticated data must leave the gate unready. No error, default metrics or first constructor return establishes provenance/readiness.

A real source-derived single-call DEX retarget still needs exact admission/inverse preservation, Android loader/native ownership and independent review. Full process-local cache-map installation remains root-owned and unassembled. A new runtime retarget or converter was deliberately not authored at this source frontier.

Recheck captured evidence with `python tools/audit_context_display_contract.py --summarize`; `--read` acquires the exact selected static bodies. Neither command executes OEM code. The finite result is the genuine additional-call/schema/cache contract and a smaller next investigation, with full-info policy and nested-wire blockers explicit.
