# Original Context metrics consumer: source-derived helper design

**Disposition: a bounded source-preserving design is mechanically plausible; acquisition/boot API review remains open.** RAW5 can supply the selected calculation without constructing a full Samsung DisplayInfo or guessing Samsung/OPPO-only policy fields. The calculation and preceding Samsung compatibility policy must remain original code. No helper, carrier, derivative DEX, boot selection or runtime conversion is implemented here.

The [inventory](../inventory/context-metrics-consumer.json) pins 23 exact bodies, nine source assertion groups, member access, complete direct read/write/reference sets and a declarative edit/register plan. [The auditor](../tools/audit_context_metrics_consumer.py) checks those source/input pins with `--report`; it emits metadata, not transformed code. Existing [Context display evidence](context-display-contract.md), RAW producer/build and all earlier frozen cards remain unchanged. PCs below are decimal unless explicitly hexadecimal. No OEM/Android/native code or phone operation ran.

## Exact selected order and owners

`ContextImpl.createSystemContextInner` obtains the original RM Configuration at 32, calls `ResourcesManager.getDisplayMetrics()` at **38 / 0x26**, then calls original `Resources.updateConfiguration(config, metrics)` at 42. The 38 call is one three-code-unit invoke with register `[2]`. Retargeting that call to an owned static member taking the same actual RM preserves its argument word, result register and surrounding code. It does not authorize constructing another RM or changing other Context/DMG callers.

The original no-argument RM method reads its actual private `mResDisplayId` and genuine `DEFAULT_DISPLAY_ADJUSTMENTS`. The overload does this, in order:

1. Obtain the original DisplayManagerGlobal owner; allocate/construct DisplayMetrics; acquire display information when that owner exists.
2. For nonnull information, read DisplayAdjustments Configuration, then CompatibilityInfo.
3. Select RM's `mResConfiguration` only when the requested display equals RM's current display and `Configuration.EMPTY.equals(adjustmentsConfig)` is true. Otherwise retain the actual adjustments configuration.
4. Invoke original getAppMetrics. The real null-info branch calls setToDefaults; it is not an error-to-null rule or readiness certificate.

RM `getConfiguration` returns its actual configuration alias. ActivityThread's getter follows its real ConfigurationController and returns that owner's configuration alias. WindowConfiguration bounds getters return actual Rect aliases. Do not hoist, copy/cache, merge or substitute those configurations, assume they equal EMPTY, or replace the earlier Context configuration with a later guessed snapshot. Their initialization, updates, lifetime and coherent use remain root-owned admission requirements.

## Preceding CompatSandbox is conditional, not optional

The selected fallback `DisplayManagerGlobal.getDisplayInfoInternal` applies Samsung CompatSandbox before its callback-registration continuation and before RM reads adjustments. Sandbox obtains genuine `ActivityThread.currentActivityThread`, its Configuration and the original private `hasCompatSandboxFlags(config, 2)`. Under that original predicate it obtains actual app/max bounds and writes:

| Source output | PC | Source value |
| --- | ---: | --- |
| appWidth | 32 | actual app-bounds width |
| appHeight | 38 | actual app-bounds height |
| logicalWidth | 50 | actual max-bounds width |
| logicalHeight | 56 | actual max-bounds height |

Sandbox reads **no DisplayInfo field**. A real per-call work frame can therefore receive those four stores without being a fabricated DisplayInfo. Its five input quantities come from RAW5. The two logical-dimension destinations can be write-only scratch fields: they must retain the original writes, require no invented incoming logical dimensions, must not escape, and must never be presented as genuine full DisplayInfo policy. Do not delete them merely because this metrics consumer does not later read them.

There is an important branch limit: public DMG `getDisplayInfo` reads private-final `mDmInternal`; nonnull calls genuine DMI directly at 34 and returns at 38. Only the null branch enters getDisplayInfoInternal at 39. Thus unconditional Sandbox application is not a source-equivalent global replacement. The admitted realm/branch must be established, or the genuine local and fallback owners must both be preserved/projected. Do not force that field absent. RM cannot inspect DMG's private field directly.

The new Sandbox derivative belongs **inside the original CompatSandbox class**. Change its parameter type to the owned boot-visible frame and only its four DisplayInfo output field references. Its register count stays four; branches, real ActivityThread/configuration/bounds calls, private flag helper and exceptions remain original. Copying this body into an unrelated helper would lose private access; a same-package child-loader name does not fix that.

## Calculation read set and exact scalar derivative

`getAppMetrics(metrics, compat, config)` reads appWidth/appHeight and invokes private `getMetricsWithSize`. That private method has **three distinct DisplayInfo fields but four read sites**:

| PC | Original receiver read | Planned scalar register |
| ---: | --- | ---: |
| 0 | logicalDensityDpi → v0 | v8 |
| 6 | logicalDensityDpi → v0 | v8 |
| 38 | physicalXDpi → v0 | v9 |
| 44 | physicalYDpi → v2 | v10 |

Its original density literal, float operations, fontScale branch/fallback, Configuration/appBounds rules, fourteen DisplayMetrics stores and final CompatibilityInfo call remain untouched. Preserve original CompatibilityInfo code too: it can use **both** override inverse scale and override inverse density scale, compare with actual DEFAULT_COMPATIBILITY_INFO and apply original per-app compatibility. Do not hand-port a simplified density/font formula, sanitize source values, use already-scaled guest Resources metrics or apply scaling twice.

A new **private-static derivative inside DisplayInfo** can take the original five explicit parameters followed by raw density:int and X/Y:float. No DisplayInfo or dummy receiver is necessary:

| Value | Original register | Derivative register |
| --- | ---: | ---: |
| metrics | v3 | v3 |
| CompatibilityInfo | v4 | v4 |
| Configuration | v5 | v5 |
| width / height | v6 / v7 | v6 / v7 |
| raw density / X / Y | — | v8 / v9 / v10 |
| old receiver slot | v2 | local scratch v2 |

The original method has eight registers and six incoming words including `this`. The static derivative has **eleven registers, eight incoming words and three locals**. Old explicit parameter registers remain exactly v3–v7. Once all four receiver reads are replaced, old v2 is not read before its first write at 44. Replace each two-code-unit IGET with a one-code-unit MOVE from its scalar argument plus NOP. All remaining instruction PCs, branches, literal bits and output operations can stay exact. This is a verified layout calculation, not an emitted/verifier-tested method.

A new public-static getAppMetrics derivative can accept the actual frame plus original metrics/compat/config and keep the original ten-register layout. Retarget only its width/height reads to the frame. Retain its moves at 4–7; after they save the inputs, stage density/X/Y from frame v0 into v6/v7/v8. Invoke the scalar derivative with contiguous **v1–v8**, eight words. The original wrapper has no branches or try regions; nevertheless the six inserted code units and new call need actual emission/inverse proof. Keep the original public/private DisplayInfo methods intact for every existing caller.

## RM placement, loader and acquisition decision

Place the owned entry and overload derivatives inside original ResourcesManager. Static entry `(actualRM)` and static overload `(actualRM, displayId, actualAdjustments)` preserve their old receiver/argument register positions and private RM accesses. ContextImpl can call a package-visible entry only in the **same actual runtime package/defining loader**; an external helper cannot read private mResDisplayId or private-final mResConfiguration. Cross-package Sandbox and DisplayInfo code needs a genuinely boot-visible public frame type and accessible typed primitive fields. Root must review the exact new names, constructor/factory ownership and placement before code.

Target boot classes must resolve that new type through their real defining loader. They cannot import the guest producer's Sample, resolve a child-only class by name, or equate same-named framework classes across realms. Original Configuration, WindowConfiguration, DisplayAdjustments, CompatibilityInfo, Rect and DisplayMetrics owners stay in that same admitted original type universe. Source names/member shape are not provenance.

Adding a static DisplayInfo helper still initializes the original class. The selected initializer constructs the genuine Parcelable Creator; its constructor is Object-only. It does not require constructing a full DisplayInfo, but class resolution/allocation/init timing remains real. The original full-info acquisition could initialize it before Sandbox; a later static call must not silently claim unchanged cold initialization/error order.

The acquisition API is the remaining concrete choice:

- Retain genuine DMG construction and actual local/fallback branch, using source-owned projection at the real owner. Retaining a derived private-field branch may require a DMG-owned helper; current RM scope alone cannot reach its private-final member. A substituted getter cannot claim the old cache, callback or native-owner effects happened.
- Explicitly replace acquisition for this one Context cut with the admitted scoped RAW source. Preserve calculation/configuration order and real absence/error distinctions, but review and record the removed/changed DMG/cache/callback obligations and selected Sandbox branch. Do not make global getInstance/getDisplayInfo a no-op or pretend a missing endpoint is an absent display.

RAW5's floats are Java field-value `floatToRawIntBits` encodings, not untouched native/Parcelable bytes. Decode mechanically at the typed boundary; no scaling or policy inference belongs there. Retain the genuine endpoint, display/caller subject, generation and use through external acquisition, policy calculation and Resources update. Exceptions propagate; Sandbox null-bounds errors, compatibility errors or transport failures are not defaults. For the required physical-display bootstrap, outer publication admission must distinguish genuine absence from unavailable/unauthenticated input.

If branch/owner/loader closure fails, keep the gate open: retain a genuine original owner/full path, add the narrowly needed source-owned projection, or pursue the previously unclosed full DisplayInfo conversion with actual policy/nested producers. Guessed policy fields and fabricated full objects are not alternatives. If same-width generation fails, use a reviewed deterministic source reassembler with explicit register/CFG/try/inverse proofs rather than reimplementing the algorithm.

Before selection, require exact DEX/header/member-pool placement, additive-member/class guards, original-method preservation except Context's bounded invoke, parameter/type verification, actual inverse/roundtrip/direct-caller proof and independent owner/config/error review. None of those artifact/runtime gates is passed by this plan. The result is a concrete next API decision, not a boot artifact or completed Context/security bootstrap.
