# Original DMS three-hook transformation contract

**Static contract only. No writer, emission, modified OEM artifact or codegen stage ran.** A root-reviewed corrected no-edit baseline and this contract are prerequisites to any future original-source producer. This card does not admit that baseline, enable the fixed-OFF helper or invent a retirement/control hook.

The exact input is original ColorOS services.jar SHA256 `66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3`, complete ordinary039 classes2.dex,10042704 bytes, SHA256 `c9a84cebd3bc22a48c0737a7de34d96ba0b97a6294d4bdd97c935543e605659f`. No041 split/rebase is involved. [The contract inventory](../inventory/guest-metrics-parent-hook-contract.json) contains every selected instruction boundary forward/inverse map, original branch map, raw/expanded try mapping and debug-event map. `python -B tools/audit_guest_metrics_parent_hook_contract.py` only reads pinned source and produces JSON metadata.

All PCs below are **decimal16-bit code-unit offsets**; raw code/debug offsets in the inventory are byte offsets in the original DEX. Source data was read through the existing frozen numeric preflight parser, not an emitter. The full original header ledger covers45059 coded methods (44520 unique source code items); selected original debug streams contain241 state/events across three hooks and three constructors. These are static scope counts, not runtime coverage.

## Declared source/member changes

Only these source changes are permitted:

- Edit DMS.onStart, DMS.onBootPhase and the **existing** BinderService.onTransact override as laid out below.
- Add instance field `DMS.mOneOsGuestMetricsLifecycle:PreparedGuestMetricsParentCell`, access**0x42/private|volatile**, implicit null, no encoded initializer and no constructor edit. Root approved volatile for the **new field only**: Binder threads read it before entering Cell.OWNER_LOCK, so a plain reference would lack publication visibility. No existing source field changes.
- Add virtual package-private/access0 DMS method `dispatchOneOsGuestMetricsFromParent(Binder,Parcel,Parcel,int)Z`, exactly the11-unit body below. New method annotations are empty; all four parameter names are null and parameter annotations empty. It has no debug_info or catch/throws annotation. Actual RemoteException/runtime/Error propagation is not caught; DEX checked-exception annotations are not an enforcement mechanism.

No original declaration/access/initializer/annotation/parameter/source-file change is otherwise allowed. No renamed constructor, alternate DMS, new subclass, wrapper/global display replacement, alias/publication method or arbitrary source callback belongs in this profile.

| Method | Original R/ins/outs/tries/units | Expected R/ins/outs/tries/units |
| --- | --- | --- |
| DMS.onStart | 4/1/4/2/57 | **4/1/4/3/65** |
| DMS.onBootPhase | 12/2/3/5/277 | **12/2/3/6/286** |
| BinderService.onTransact | 7/5/5/0/27 | **7/5/5/0/39** |
| New DMS dispatch | absent | **6/5/6/0/11**, debug offset0 |

Every other original registers/ins/outs/tries/units tuple must remain source-exact. Preserve original outs even when overprovisioned; do not recompute/shrink it. All three edited original outs also remain unchanged. Physical code/debug offsets relocate; preserve debug presence and the exact mapped semantic target, not literal source file offsets.

## onStart: actual born object, optional-only catch

Source has this=v3 and still-live born Binder=v0 after original invoke at50. Original NEW21/constructor23, vendor callback28, display publication33 and local publications40/50 remain original. Insert exactly eight units **before original return53**:

| New PC | Width | Authored action |
| --- | --- | --- |
| 53 | 3 | invoke-static `{v3,v0}` Cell.captureAfterOnStart(Object,Binder):Cell |
| 56 | 1 | move-result-object v1 |
| 57 | 2 | iput-object v1,v3,new private volatile field |
| 59 | 1 | goto original return61 |
| 60 | 1 | move-exception v1, then fall through return61 |

The sole new typed Throwable try is **[53,59)→60**. It covers only the added capture/result/store work. It excludes original calls, locks, publications, return and handlers. If the factory itself **throws/refuses before returning**, move-result/store are not reached and the existing field is not cleared. An internal preparation failure instead returns a claimed failed cell, which is deliberately stored. The catch itself neither disables/retires nor clears any cell; no raw Throwable is logged or retained by the hook. OFF returns/stores null and supplies no metrics/readiness. Optional availability remains governed by the controller, fixed build mode and genuine owner admission; catching an error is not cleanup/readiness evidence.

Use v1 for the new result/store/catch temporary. Original `binderService` localv0 is debug-live from26 through54 and must retain the actual born Binder through the normal tail; v1 has no such live debug local. This choice changes no width/header/pool map.

Instruction map: `F(p)=p` for p<53, otherwise `p+8`; code end57→65. The inverse is its exact restriction to mapped original instruction boundaries; delete the declared new block, not an arbitrary suffix.

Original raw try items are [3,12)→catch-all54 and [55,56)→catch-all54. They become **[3,12)→62** and **[63,64)→62**. Handler instruction54→62, monitor-exit55→63 and throw56→64 retain original behavior. No original branch targets return53. Normal original work reaches the hook by fallthrough; an original exception reaches only its relocated original handler, never the new optional catch.

## onBootPhase: original success first

Keep this=v10, actual phase=v11, original registers and all existing work. Its19 original branches target PCs≤249; none jumps to return276. Original default-display timeout/monitor/InterruptedException and vendor/tail calls remain before the new work. Insert nine units before original return276:

| New PC | Width | Authored action |
| --- | --- | --- |
| 276 | 2 | const/16 v0,100 |
| 278 | 2 | if-ne v11,v0, original return285 |
| 280 | 3 | invoke-static `{v10,v11}` Cell.onOriginalBootPhaseCompleted(Object,int):PhaseDisposition; ignore result |
| 283 | 1 | goto original return285 |
| 284 | 1 | move-exception v0, then fall through return285 |

Only **[280,283)→284** is the new typed Throwable try. Non100 phases skip the helper; the original method already completed its actual phase work. Never wrap original DMS/vendor calls or default-display failure in the new catch. The catch continues original return flow without asserting optional readiness or disabling/retiring a cell. The actual controller, fixed-OFF mode and genuine owner admission govern availability. No original failure is converted to success and no default metrics are supplied.

Instruction map: p<276 unchanged; return276→285; code end277→286. All original branch PCs/targets and raw try boundaries/handler PCs remain unchanged. The five original raw try items are:

| Interval | Ordered original handlers |
| --- | --- |
| [9,81) | catch-all132 |
| [81,86) | InterruptedException87, then catch-all132 |
| [89,134) | catch-all132 |
| [193,219) | catch-all245 |
| [246,247) | catch-all245 |

These are **five raw try items but six flattened catch entries**. Add exactly one raw try item/new catch; do not confuse those counts, drop the typed-before-catch-all order or broaden a protected interval. Throwable already exists (source type9454→declared remapped9456); no extra type/string is introduced for this catch.

## BinderService: prefix before original token enforcement

Keep original parameters this=v2, code=v3, data=v4, reply=v5, flags=v6. Insert twelve units before original PC0:

| New PC | Width | Authored action |
| --- | --- | --- |
| 0 | 3 | const v0,0x00fe0001 |
| 3 | 2 | if-ne v3,v0, original body12 |
| 5 | 2 | iget-object v0,v2, original this$0 |
| 7 | 3 | invoke-virtual `{v0,v2,v4,v5,v6}` new actual DMS dispatch |
| 10 | 1 | move-result v0 |
| 11 | 1 | return v0 |

No new catch. Every other code enters the identical original body, including Stub descriptor checks/1…72 and vendor10111 fallback. The fixed private code does **not** fall back after false/error: its actual dispatch Boolean or failure returns directly. Putting the prefix after original Stub is unsound because Stub enforces its display token before the switch. Original attachInterface, descriptor and OPPO Binder extension remain unchanged.

All original PCs map `F(p)=p+12`; end27→39. Original conditional branches **5→8,12→25,22→25** become **17→20,24→37,34→37**, retaining their original relative offsets. The prefix only writes old localv0; original normal dispatch overwrites v0 before its own use. No input register is moved. Other-code original instructions are preserved, not replaced by an equivalent-looking wrapper.

## New dispatch and six-word call

R=6, ins=5 means v1=this, v2=actualBorn, v3=data, v4=reply, v5=flags; v0 is the sole local:

| PC | Width | Exact authored action |
| --- | --- | --- |
| 0 | 2 | iget-object v0,v1,new field |
| 2 | 2 | if-eqz v0, unhandled9 |
| 4 | 3 | invoke-virtual/range **v0…v5**, Cell.dispatchFromParent(Object,Binder,Parcel,Parcel,int)Z |
| 7 | 1 | move-result v0 |
| 8 | 1 | return v0 |
| 9 | 1 | const/4 v0,0 |
| 10 | 1 | return v0 |

The outgoing call is **six** words: cell receiver, DMS owner, born Binder, data, reply, flags. The new method's incoming size is **five**, including DMS receiver. A five-word invoke encoding is insufficient for the Cell call; use the declared contiguous range. No catch, borrowed-packet reset/recycle, flag rewriting, target lookup, identity clear or private-code fallback is permitted.

## Debug and constructors

The inventory provides exact maps for17 onStart,71 phase and6 parent raw debug state/events, plus147 constructor events. Excluding ADVANCE_PC/ADVANCE_LINE states but including END_SEQUENCE gives16/61/6 semantic events for the three hooks. Keep original line_start, parameter count/names, event order/kind, line values and register numbers; map addresses with the same F used for original instructions. Parent source origin0 maps12, requiring the debug address state to advance before the corresponding original event. Do not invent source lines/locals for the inserted work or add debug strings.

Preserve actual END_SEQUENCE positions: onStart54→62, phase276→285, parent25→37. Do not force sequence end to method extent. Address-state opcode encoding may relocate; the original semantic records and declared pool-index mappings are exact. Existing debug string indices add the number of declared insertion positions≤old index; absent−1 stays absent. Type indices use the two declared type insertions at9309. The raw selected debug streams and source hashes remain ignored; the contract records their mapped semantics. Absolute output debug offsets are not guessed.

Raw code-item try padding is also explicit: onStart keeps2 zero bytes (57→65 odd units); phase changes2→0 bytes (277 odd→286 even); parent has no try padding because try_count stays0. These are layout consequences, not additional instruction changes or permission to normalize headers.

All original constructors remain semantically exact, with identity PC/try/debug maps and only declared pool-reference/physical-offset relocation:

| Constructor | Access | R/ins/outs/tries/units |
| --- | --- | --- |
| DMS(Context) | 0x10001 | 3/2/3/0/9 |
| DMS(Context,Injector) | 0x10000 | 28/3/12/0/751 |
| BinderService(DMS) | 0x10000 | 3/2/2/0/14 |

Keep original Context/Injector path, synthetic final this$0, PermissionEnforcer/Stub initialization, declarations/annotations and debug names. No constructor field assignment is needed for implicit null. Raw source instruction/debug hashes in the inventory are provenance; output pool IDs/offsets relocate, so those hashes are not an unrelocated output-byte assertion.

## Global preservation and producer gate

The source numeric ledger fixes every original five-word header tuple by descriptor; only the three listed units/try changes are allowed. The new dispatch has its own explicit tuple. Preserve code presence, access/partitions, original relative member order, values, annotations, parameters, instructions/references/widths/branches/debug and actual source code-group relationships. Selected edited methods have no shared source code-item alias. Do not permit a generic “edited methods may differ” escape hatch.

The reviewed preflight adds exactly seven strings, two types, four method references and one field; primary projected method count60094 fits16-bit references. **The narrow-string margin is only one index:** maximum projected short const-string index65534. No extra logger/debug/name/sentinel strings or instruction widening is admitted. Any deviation needs a new literal projection and explicit contract; never hide jumbo changes through normalization. Primary class definitions remain6554.

Original classes2 has **no raw HAPI section**. Preserve absence for the whole DEX, including new members; do not synthesize policy, copy a Samsung section or ignore member/section changes. The full guest helper closure—Cell/two enums, Producer/Sample/marker and Endpoint, seven definitions—stays in a **separate authored DEX** under the same actually admitted services loader, not merged into primary. Packaging/loader admission and exact helper manifest remain separate tasks.

The symbolic inverse deletes only declared authored blocks/catches/field/method/references, applies exact inverse PC/try/debug maps and restores declared pool forms. It must compare the complete source profile and root-admitted corrected no-edit canonical baseline, including header/group/map/initializer/HAPI preservation. This metadata plan emits no inverse or modified DEX and approves no existing failed writer output.

Before any source producer: root/H must approve the corrected no-edit baseline and this finite contract. Before runtime enablement: actual parent/currentness, phase/code/profile/source/loader/configuration admission, real retirement/control and consumer ownership remain open. No retirement hook is invented; successful static mapping, helper models or a fixed OFF artifact is not a ready Android/Samsung Context or security authority.
