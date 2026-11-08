# Context metrics scalar diagnostic: emitted and unselected

**The approved one-method diagnostic was emitted and statically checked. It remains unselected and has no runtime caller.** The [approved contract](context-metrics-scalar-leaf.md), its inventory and the earlier consumer design are unchanged. This result implements that diagnostic contract; it does not add a boot-class member or provide Context metrics.

The [Java producer](../tools/Build-ContextMetricsScalar.java) reads the literal pinned Samsung `classes4.dex`, obtains the selected original method and retains its instructions directly. It changes the declaring owner/prototype/private-static flag/register count and precisely the four approved IGET operations into MOVE+NOP. It does not recreate Samsung arithmetic as Java source. Original Configuration, CompatibilityInfo and bounds behavior remains in the copied DEX instructions and original external calls.

The [runner and independent raw checks](../tools/build_context_metrics_scalar.py) verify the full Samsung framework archive SHA, selected DEX extent/SHA, source body and raw instruction-slice SHA, approved proposal and predecessor pins, and frozen parser/normalizer/runner dependencies before and after the run. Source framework bytes remain untouched. One early preflight refused a changing sibling tool dependency before compilation/output creation; the implementation now uses its own raw parser instead of that sibling tool. No shared file was changed.

## Actual artifacts and checks

The successful receipt is `out/context-metrics-scalar-leaf/20261105T232705560082Z-0986992e77f04b33acadee8c5cd9c0e9/receipt.json`. That directory contains four diagnostic/projection DEX files:

| File under its `dex/` directory | SHA-256 |
| --- | --- |
| context-metrics-scalar.dex | `0a310ff9f473537ef6e23cf82c91718d105944bc2a8e52439f07fa69b10980ae` |
| context-metrics-scalar-roundtrip.dex | `0a310ff9f473537ef6e23cf82c91718d105944bc2a8e52439f07fa69b10980ae` |
| source-method-projection.dex | `58d595b02dffa26b860b514b4830fa1d7b2a35e73e7bc0978ce6bf39a113b50f` |
| inverse-source-method-projection.dex | `58d595b02dffa26b860b514b4830fa1d7b2a35e73e7bc0978ce6bf39a113b50f` |

The scalar artifact defines exactly the approved public-final diagnostic class with Object superclass, no fields/interfaces/constructor/initializer/annotations, and one private-static method. Its raw code item has **11 registers, eight incoming words, three outgoing words, no tries and 91 code units**. It has 54 instructions. The derivative normalized body SHA is `75286f851d3181b85f962f32167cc20b2c663e46bb6b6a3f6d5b03465d31e163`.

The original five parameters and three added scalar parameters are unnamed and unannotated. All thirteen original line-number/PC entries and `DisplayInfo.java` source filename survive. Independent raw ULEB parsing reads numeric hidden-API **3** for the selected member in all four files. This is an explicit source-derived diagnostic policy value; it grants no runtime authority.

The raw checker compares all fifty original instruction sites. Each of the four replacements has the exact approved MOVE register pair followed by NOP. For the other 46 instructions, every non-reference instruction byte is exact. Reference instructions retain all non-ID bytes and resolve to the original member targets; 22 reference-ID operands relocate in the extracted scalar DEX. Therefore original literal encodings, branches, PCs, registers and call targets remain exact within the declared transformation. Pool indices are not claimed physically equal to the source framework.

Emission followed by actual decode/re-emission is byte-identical. Inverse reconstruction restores the original owner, five-parameter prototype, private-instance flag, eight-register layout and four IGETs. Its normalized selected method equals the original, including debug and metadata. Re-emitting/reparsing it produces the same bytes as the independently emitted **one-method source projection**. Both projections check every original instruction slice, with the same explicit reference-ID relocation rule. This is selected-method inverse proof; neither projection is a complete runnable DisplayInfo class, and no full framework inverse is claimed.

Five in-memory negative cases independently change the density argument, required NOP, register header, raw numeric policy or debug line. Each mutant has its SHA-1/Adler integrity recomputed before checking, and each is rejected by the relevant contract. No OEM method is invoked by these checks.

## Execution boundary and remaining selection gates

Only existing JDK tools and dexlib were used. The runner strips all five JVM/compiler injection variables, uses an exclusive task output working directory, confines TMP/TEMP and JVM home/temp flags there, bounds output and enforces subprocess timeout. Authored inspection/writer classes execute; Samsung/ColorOS code, Android/ART, native code and phone operations do not.

The [implementation inventory](../inventory/context-metrics-scalar-implementation.json) pins source/tool inputs, actual outputs, raw checks, logs and authored inspection classes. Raw selected method records and the 182-byte original instruction slice remain only under ignored `firmware/context-metrics-scalar-leaf/`; generated binaries remain under ignored `out/`.

This preparation establishes neither an ART verifier result nor usable metrics. The twenty remaining public member references still require the genuine original boot types/defining loaders and real configuration/CompatibilityInfo owners. Sandbox, DMG local/fallback branch and cache/callback effects, RAW endpoint subject/generation/lifetime, RM selection and private accesses, Context retarget, complete boot insertion and Resources publication remain open. A later source-class insertion must separately preserve all original members and raw per-member hidden-API metadata. No branch bypass, default policy or fabricated DisplayInfo is introduced here.
