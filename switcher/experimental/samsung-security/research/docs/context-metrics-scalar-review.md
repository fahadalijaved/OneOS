# Independent review of the emitted Context metrics scalar

**No blocking defect found for the unselected one-method diagnostic.** This
review accepts the bounded artifact/projection evidence, not runtime placement,
ART verification, Context integration or authority admission. The approved
proposal and existing client-metadata preparation remain unchanged.

Reviewed inputs are the [implementation](context-metrics-scalar-implementation.md),
[producer inventory](../inventory/context-metrics-scalar-implementation.json) and
their frozen source/output manifest. The [review inventory](../inventory/context-metrics-scalar-review.json)
pins all evidence. No writer was rerun, no OEM code or Android/ART executed, and
no boot class, service, phone state or shared file was changed. The reviewer used
an independent, task-private Python byte reader and static javap of the authored
writer class; those are inspection tools, not execution of the emitted method.

| Actual artifact | Independent result |
| --- | --- |
| Scalar and decoded/re-emitted scalar | Both 1,624 bytes, SHA `0a310ff9f473537ef6e23cf82c91718d105944bc2a8e52439f07fa69b10980ae` |
| Source and inverse source projections | Both 1,660 bytes, SHA `58d595b02dffa26b860b514b4830fa1d7b2a35e73e7bc0978ce6bf39a113b50f` |
| Source instruction slice | Literal 182 bytes, SHA `f09114b4b9ef2b6515cdf8ecfcb4d78c3fb69a1eef5c5e42deeedf32e2564bdf` |

The sole ClassDef is the approved unique public-final diagnostic type, with
Object superclass, no interfaces/fields/annotations/constructor/initializer, and
one private-static method. Direct raw parsing verifies flags 10, eleven registers,
eight incoming words, three outgoing words, zero tries and 91 code units.
The original five explicit parameters still occupy v3–v7. Added int density,
float X DPI and float Y DPI occupy v8/v9/v10; no dummy DisplayInfo is supplied.

All four two-unit IGET sites have the exact planned one-unit primitive MOVE plus
NOP at PCs 0/6/38/44. The other 46 instructions preserve every non-index byte;
all 22 reference-bearing copied instructions independently resolve to the same
members. Original branch targets, constants, operands, configuration/fontScale,
appBounds behavior, fourteen DisplayMetrics stores and final CompatibilityInfo
call are preserved. The emitted method contains 54 instructions and no
DisplayInfo member/type reference. Raw floats are inputs, not decoded or
sanitized values in this diagnostic.

Bounded static dataflow over all 54 instruction PCs and 60 CFG edges finds no
uninitialized register read or incompatible primitive/reference use. Old v2 is
not read before its new assignment at PC44; later float, Rect/null and boolean
uses follow the original overwrites. Maximum invoke width is three words.
Three decoded-model mutations—wrong density type, an uninitialized scratch read,
and a float substituted for the density input—are rejected by that type-use
analysis. This is deliberately not an ART verifier claim.

Independent raw ULEB decoding reads numeric hidden-API value **3** from the source
and all four emitted selected members. Both projections retain original instance
flags, register/prototype layout and all fifty resolved source instructions.
All thirteen original line/PC records and `DisplayInfo.java` survive. Five null
parameter names remain in each source projection; eight null names appear in
each scalar. No selected method/parameter annotation entry or local/`this` debug
record appears. Each DEX's SHA-1/Adler header integrity also verifies.

The immutable source declaration index independently confirms the twenty
remaining distinct references across five declaring classes are public. That
language-access result supplies neither defining-loader identity nor hidden-API
or native runtime permission. Static compiled-writer inspection confirms four
emit and four decode callsites, including the decoded first scalar feeding its
actual second emission. The implementation's 29-file freeze and compile/emit
exit-zero receipts verify against current bytes. Its five integrity-recomputed
binary negative checks were source/receipt-reviewed, not rerun by this reviewer.

The inverse is explicitly **selected-method reconstruction and one-method
projection equality**. The projections omit original DisplayInfo fields and its
Parcelable interface; they are not complete runnable original classes. No full
framework restoration, original boot member insertion or runtime cohort follows.

Selection still requires genuine original boot types/configuration and
CompatibilityInfo owners, Sandbox handling, DMG local/fallback/cache/callback
behavior, RAW subject/generation/lifetime, RM selection/private access, Context
retarget and actual Resources publication. Raw numeric policy 3 is a derivation
rule, not authority. This diagnostic resolves none of those remaining owners or
the separate client-metadata/API/cancellation gates.
