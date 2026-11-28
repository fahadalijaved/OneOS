# Guest metrics lifecycle cell: source/API proposal

**The born-Binder and phase100 seams support an authored lifecycle cell, but genuine publication acknowledgement/collision ownership is still open.** This card proposes the exact owner/API and default-OFF configuration. It emits no lifecycle runtime source, original method edit, publication or activation. The frozen Producer/Endpoint implementations, their builds and authored-fixture reviews remain separate unchanged components.

[The inventory](../inventory/guest-metrics-lifecycle.json) verifies the frozen endpoint factory's 36 source assertions and nine OneOS input files (seven patchers/helper plus producer/launch scripts), and pins two new ColorOS framework bodies with five exact edges. Recheck with `python -B tools/audit_guest_metrics_lifecycle.py --read --report`. No Android/OEM execution or phone operation occurs.

## Actual source ownership and proposed footprint

Reuse the actual donor source facts: DMS.onStart creates BinderService in v0 at15/17, calls the original vendor extension at1c, publishes real `display` at21 and the original local services through32, then returns35. The actual BinderService constructor stores the passed DMS in synthetic final `this$0` (flags0x1010). DMS currently declares no retained mBinderService field.

The proposed OneOS candidate adds **one private lifecycle-cell field to that actual DMS**, leaving it null when disabled/failed. After the original onStart body finishes all publication/extension work, the exact source hook creates the cell from original `this` and that still-live born v0. It must not look up another DMS, call an arbitrary provider or create a new original service. Genuine acquisition comes from this selected source factory/callsite, not a receiver type/name/UID assertion.

The second hook runs only at original onBootPhase normal completion before return114, with the actual phase argument100. The original default-display wait, timeout, vendor callback fb and tail111 run first. An original failure never reaches that hook. The same DMS object accesses its own captured cell; a different owner/phase cannot obtain a publication candidate. Exact source/body/branch/register preservation and inverse proof are required before selecting those edits. No retarget was authored here.

The helper, frozen Endpoint and complete Producer/Sample/Java8 marker closure must resolve from the actual DMS defining services loader. A same-name helper in an app loader, an arbitrary retained Object or another copy of the lifecycle class is not this owner. The candidate producer must validate exact selected services/framework/OPPO-patch inputs, helper definitions and edited outputs before packaging. Installed guest/ART/classloader/current-profile admission remains unassembled.

## Concrete configuration proposal

Use a **process-local, build-owned literal mode, default OFF**, in the future authored lifecycle class. The selected OneOS candidate build producer generates/pins that literal together with the original source profile, hook edits and complete helper closure. The lifecycle factory reads its own compiled mode once; no caller Boolean, UID, owner callback, property, SettingsProvider query or new file read decides it. This is configuration of a feature attempt, never source/authority attestation.

OFF returns no cell, prepares no Producer/Endpoint, retains no DMS/Binder and publishes nothing. Only an explicitly selected candidate build can carry ON. There is no runtime preference/setter, automatic retry or “enable on first call.” Current OneOS has no such metrics config/profile producer; modifying `make-overlays.sh` and its artifact selection is a **new required build-owner task**, not an existing implementation. Its ordinary DEX-rebuild behavior alone is not that producer.

No persistent user toggle is claimed. If later required, a separately reviewed OneOS-owned bounded asset/preference producer, permissions, pre-boot acquisition and update/disable contract must be added. Do not read SettingsProvider in this early DMS path by assumption, or treat a permissive persistent property as provenance. The compiled mode/source pins likewise do not prove the actual running code/profile. Root must separately select and admit the candidate.

## Proposed cell API and state

Names/signatures below are **proposed**, not implemented or approved runtime entry points:

| API | Required behavior |
| --- | --- |
| `captureAfterOnStart(Object actualDms, Binder actualBorn): GuestMetricsLifecycle?` | Called from the exact original source tail. OFF returns null. ON claims one bounded owner slot, retains the exact pair and prepares the frozen Producer/Endpoint once. No getter call, readiness or publication. |
| `candidateAfterPhase100(Object sameDms, int actualPhase): IBinder?` | Only matching owner and actual successful phase100; returns the one owned **INACTIVE** Endpoint Binder once, or null/refusal. Does not publish or activate. |
| `finishPublication(Object sameDms, IBinder attemptedCandidate): void` | Validates the exact owned candidate and internally acquires genuine registry readback/outcome. It cannot activate from void publication return, cached/null lookup or a caller's “success” argument. **Its registry/outcome dependency is not closed.** |
| `publicationFailed(Object sameDms, IBinder attemptedCandidate, Throwable ownPublicationFault): void` | Source hook's own publication failure, not an admission callback. Terminally fail/retire the optional projection; no retry/default or original DMS failure suppression. |
| `retire(Object sameDms): void` | Terminal/idempotent; prevents new publication/activation and retires the exact Endpoint. Retains active/uncertain owners; no native/global drain claim. |

One static bounded claim in the selected helper class prevents a second DMS/cell from taking over the feature. It is **one per admitted helper Class/loader**, not a universal singleton across arbitrary duplicate loaders. The defining-loader/source admission must exclude those duplicates. The DMS instance field roots its own cell; the cell retains its exact DMS, born Binder, Producer and Endpoint for the original process lifetime. Failure/retirement never clears the slot to permit a fresh writer. OFF need not claim an owner.

The conceptual transitions are OFF; or CLAIMED/PREPARING→CAPTURED→PUBLICATION_PENDING→ACTIVE, with terminal FAILED/RETIRED reachable from every attempted state. An original repeated onStart or phase100, mismatched DMS/Binder, second owner or reentrant call during preparation/publication is refused; it cannot create another Producer/Endpoint or republish. No lock may be held across reflection, registry calls, original publication, Endpoint operations or logging. Claim before external preparation; recheck the exact owner/state afterward. Failure retains bounded uncertainty and makes the projection unavailable. These rules are requirements for a future implementation/model review, not tested code.

## Original DMS publishes; normal return is not acknowledgement

The actual source DMS should call its original protected `publishBinderService` on the fixed proposed alias `oneos.guest_display_metrics.v1`, using the cell's optional Binder. The helper performs no app-only global publication shortcut. Proposed `allowIsolated=false` adds no grant; it restricts service discovery relative to original display's allowIsolated=true and needs explicit API approval. The original getter's visibility policy still applies to every actual call. Alias discovery is not Samsung authority attestation.

Two newly read actual ColorOS `android.os.ServiceManager` bodies expose the missing acknowledgement boundary:

| Exact method / hexadecimal PCs | Observed behavior |
| --- | --- |
| `addService(String,IBinder,boolean,int)` `0,4,8,d,10` | Acquires IServiceManager, calls addService, catches RemoteException from0…6 at8, logs atd and returns void at10. The existing SystemService wrapper simply delegates to it. |
| `checkService(String)` `0…a,b,f,17,1e,23,26/27` | Returns a process-local sCache hit first. On miss, calls genuine manager.checkService2, extracts Binder and allows blocking. It catches RemoteException and returns null. |

Consequently:

- A normal protected publication return does not prove the alias was registered.
- A null `checkService` is not proof the alias was absent; it may be a transport failure.
- A nonnull cached answer is not a fresh registry-generation receipt.
- Check-then-add is not an atomic no-overwrite/collision proof. The native addService replacement/exclusive-owner behavior was not audited here.

Keep the candidate INACTIVE through publication and uncertainty. Existing clients that acquire it during that window must receive inactive refusal, never fake metrics. Activation requires an actually owned, noncached registry/outcome path preserving errors and same-Binder identity, plus exclusive/collision semantics for this alias. No caller-supplied Boolean/Binder/hash or generic callback can establish it. Exact acquisition of the canonical registry client or a bounded framework source seam remains a **specific next gate**; no native registrar or app reflection shortcut is invented in this card. An uncertain/failed/colliding attempt terminally disables and retires the candidate even if a still-published inactive alias remains. Never overwrite or retry to hide uncertainty.

## Failure, retirement and bootstrap boundary

Source hook catch regions must cover only the **new optional projection work**, including helper class initialization/preparation/publication/readback failure. They must not encompass/swallow the original DMS/vendor calls or original default-display timeout. The required display service keeps its original behavior; optional projection failure leaves the Samsung bootstrap waiting/unready, not using default metrics. A helper failure record/log must be bounded and contain no metadata values or borrowed objects; actual logging/failure-owner implementation is not supplied.

Endpoint retirement retains the already reviewed reply-admission semantics: new calls and replies not past its ACTIVE fence are refused; replies admitted before retirement may arrive later. `activeTransactions()==0` counts only admitted endpoint Java frames and is not native delivery, original DMS, process or consumer drain. Real publication/death/client-instance/epoch ownership and return quiescence remain external. No force unpublish, service-name reuse or clear-to-retry API is proposed.

The actual Samsung consumer still needs admitted live guest metadata, original CompatSandbox/RM/configuration/CompatibilityInfo, boot-visible helper/callsite selection and the separate eager display reads/full process-local cache-map installation. This proposal is metadata-only and grants no credential capability. No lifecycle cell source, persistent config, hook, publication, runnable Context or security authority was emitted. The unresolved registry/config/source-admission owners are reported rather than replaced by an always-inactive “ready” bootstrap.
