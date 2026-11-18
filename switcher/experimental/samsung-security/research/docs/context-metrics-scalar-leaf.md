# Context metrics scalar derivative: diagnostic contract

**Proposed, unselected, not yet emitted.** This preparation isolates one original Samsung calculation. It neither inserts a member into a boot class nor supplies a runtime metrics path. The [frozen consumer design](context-metrics-consumer.md) remains unchanged.

The pinned Samsung framework archive is `8095a9ae…`; the selected original is `DisplayInfo.getMetricsWithSize(DisplayMetrics, CompatibilityInfo, Configuration, int, int):void` in **classes4.dex**, SHA `b3088ece8acfc76067eed2aefd2b93a0604da9b8645bd2f2f84012859fefb5c4`, 8,458,024 bytes. Its normalized body SHA is `4c9f073201d90b89486fd11b2f8330e717f3172c4da788f34214709a87b4e703`. Literal code begins at 3,412,524; its 182 instruction bytes hash to `f09114b4b9ef2b6515cdf8ecfcb4d78c3fb69a1eef5c5e42deeedf32e2564bdf`.

## Proposed member and mapping

Emit one separate diagnostic ClassDef, `Lcom/appleexploit/oneos/security/diagnostic/ContextMetricsScalar;`: public-final, Object superclass, no fields, interfaces, constructor or initializer. Its only member is private-static `getMetricsWithSize(Landroid/util/DisplayMetrics;Landroid/content/res/CompatibilityInfo;Landroid/content/res/Configuration;IIIFF)V`. It has no caller and is not a proposed runtime API. Retain `DisplayInfo.java` as the source filename for the original line mapping.

The original private instance member has flags 2, eight registers, six incoming words, three outgoing words, no try blocks and 91 code units. The derivative has flags 10, eleven registers, eight incoming words and three outgoing words. Three locals leave the five original explicit arguments in **v3–v7**. Raw density, X DPI and Y DPI occupy v8, v9 and v10. Old receiver v2 becomes scratch; after removing its four receiver reads it is not read before the original write at 44.

| Original PC | Two-unit source operation | Two-unit replacement |
| ---: | --- | --- |
| 0 | logicalDensityDpi into v0 | MOVE v0,v8; NOP |
| 6 | logicalDensityDpi into v0 | MOVE v0,v8; NOP |
| 38 | physicalXDpi into v0 | MOVE v0,v9; NOP |
| 44 | physicalYDpi into v2 | MOVE v2,v10; NOP |

Every other instruction is taken from literal original DEX data. The four replacements use one-unit MOVE and NOP, preserve 91 code units, and increase the instruction count from 50 to 54. Original PCs, branch targets, operands, literals, arithmetic, fontScale/configuration/appBounds rules, fourteen DisplayMetrics stores and final CompatibilityInfo invocation remain exact. No DisplayInfo argument, object or dummy receiver is introduced. Raw floats are typed input values; this leaf performs no transport decoding or sanitation.

All twenty remaining distinct member references have public declaring classes and public members in the immutable Samsung declaration index. This establishes a bounded language-access check, not cross-loader identity, hidden-API permission or successful ART verification.

## Metadata and hidden-API contract

The original method index is 37,947, code-item offset 3,412,508. Its debug table occupies 4,878,006–4,878,028: five null parameter names and thirteen line-only entries; there is no local-variable or `this` debug record. No selected method-annotation or parameter-annotation directory entry exists. Preserve the thirteen original PC/line records and original five parameter metadata records; append three unnamed, unannotated scalar parameters. A producer must check these premises and refuse drift.

The selected direct member's **raw numeric hidden-API value is 3**. The proposed diagnostic explicitly retains that value, with independent raw output readback; enum-only equality is insufficient. This is a declared derivation rule, not evidence that a new member inherits runtime authority. Original hidden-API streams remain untouched. The existing classes3 full-rewrite repair helper requires identical class/member order and a different pinned source profile, so it cannot certify this addition.

Full DisplayInfo insertion is deferred. It would require a reviewed new member/visibility, additive declaration and pool proof, preservation of every original method and raw per-member hidden-API value with changed ordering, and actual boot cohort/loading admission. This diagnostic proves none of those.

## Proposed validation and limits

Before emission, verify archive, DEX, selected raw body, metadata, instruction-site and member-access pins. Reparse the emitted selected member and compare every instruction/branch/try/debug/parameter record against the mechanical transformation. Check raw numeric policy, registers, incoming/outgoing words and class/member counts. A second emission must be byte-identical.

Inverse reconstruction restores the source owner, prototype, instance flags, register count, metadata and the four original IGETs. Compare the reconstructed selected method with the literal original, then emit/reparse a separately labeled one-method source projection. This is **selected-method inverse proof**, not full framework byte restoration or a runnable source class. Method/field pool indices may differ in extracted DEX files; reference-resolved equality is required in addition to literal source-site checks.

No OEM code, Android/native code or phone operation runs. The Sandbox derivative, original DMG local/fallback branch and cache/callback ownership, RM/configuration selection, RAW endpoint subject/generation, Context call retarget, boot placement and live Resources update remain open. No source branch may be bypassed to make this diagnostic a runtime path.
