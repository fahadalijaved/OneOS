# Samsung DEX041: source-preserving subset re-emission

**Passed for the two explicitly selected top-level definitions only.** The static tool reads the intact Samsung services.jar DEX041 container and re-emits original `UserManagerService` and `LockSettingsService` definitions to standalone ordinary DEX039 without a source edit. Decoding preserves every compared class/field/method record; a second emit produces byte-identical DEX039. This is a concrete code-generation prerequisite for later reviewed retargets, **not** a dependency-complete cohort, ART compatibility proof or a security artifact selection. No OEM class, service, JNI or Android runtime was loaded/initialized/executed.

Run `python -B tools/probe_samsung_dex041.py`. Exact results, source/tool pins, member-level normalization hashes and ignored output paths are in [the inventory](../inventory/samsung-dex041-rewrite.json). Raw normalized original/decoded bodies stay under ignored `firmware/samsung-dex041-rewrite/<run>/`; generated DEX binaries, authored helper classes/API inspection/compiler logs and the receipt stay under ignored `out/samsung-dex041-rewrite/<run>/`. Earlier runs remain historical; the final producer separates raw-body and generated-binary output locations. No phone, package installation or system modifications are performed.

## Actual container and writer boundary

Input services.jar is pinned to `def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6`; its single physical classes.dex is28,157,552 bytes. The unchanged [static reader](tooling.md) supplies `LogicalDex(container, headerOffset)` using dexlib's full-container constructor `super(null, container, 0, false, headerOffset)`. No bytes are sliced into an alleged independent subDEX, no table/data offsets are rebased and no header is patched for input admission.

Both logical headers are validated at0 and10,057,984, with9,252 and9,664 class declarations. **Both selected definitions live at10,057,984.** The first header's class-count/extent validation is not a claim that any first-header class was re-emitted. Nested classes and referenced definitions are deliberately excluded; their references are preserved as references, not replaced by stubs.

The installed JADX1.5.6 all-jar is pinned to `fe3e12c45acf75f92369685fd02d1d7a7323385dc725680a9b98a0dac0ea554b`. Before any writer call the runner records actual `javap` API signatures and DexWriter bytecode. This installed relocated dexlib exposes `DexPool(Opcodes)`, `internClass(ClassDef)`, `writeTo(DexDataStore)` and MemoryDataStore.getData/close. MemoryDataStore does **not** implement AutoCloseable: the first authored compilation failed on try-with-resources, before any rewrite; the final implementation closes it explicitly in finally. That failed compile/log remains separate from the passing actual writer run.

DexWriter's hidden-API writer requires both nonempty restrictions and `opcodes.api >= 29`. The tool therefore uses `Opcodes.forApi(29)` and verifies the installed VersionMap maps that to DEX039; it does not assume `forDexVersion(39)` preserves that writer gate. Output magic/header, table bounds, SHA1 and Adler32 are checked before decode. These checks are format/checksum evidence, not an Android version/loader admission.

## What was preserved

The passing actual input covers2 classes,134 fields,476 methods,24,604 instructions,799 try blocks,51 debug items,8 annotation instances and6 explicit field initial values. These are evidence dimensions, not readiness or security-coverage counts. All612 normalized records match after first decode and second decode.

| Normalized category | Included details |
| --- | --- |
| Class | Descriptor, access flags, superclass, ordered interfaces, source filename, annotation visibility/type/elements. |
| Field | Static/instance partition, owner/name/type, access flags, typed encoded initial value, annotations and hidden-API restriction set. Null/absent and explicit values are distinguished; float/double raw bits are retained. |
| Method | Direct/virtual partition, exact signature/access flags, ordered parameter types/names/signatures/annotations, method annotations and hidden-API set; no-code versus code distinction. |
| Instructions | Register count and instruction registers/ranges, opcode/width, literal values, exact method/field/type/string/proto/handle/callsite references, branch targets, switch offsets/payload values and array data. Address-bearing instructions are not erased to obtain equality. |
| Exception/debug data | Try start/length, ordered catch types/handler PCs; debug item kind/address, local register/name/type/signature, lines, source changes and prologue/epilogue markers. |

Original041 → emitted039 → decoded039 normalization preserves the represented metadata. Decoded039 → emitted039 is additionally byte-identical: SHA256 `80c379a3a0a9f6b94bfb45d78904fda8a1a827b46a9e7bc0f6495d8e13b2cef0`. This is **not** a byte inverse to the original041 container: pool layout/header/offsets/encoding legitimately differ. Source-provenance locations stay in the receipt, not reconstructed output header offsets.

Selected hidden-API member restrictions are empty. Independent source map inspection finds no0xf000 hidden-API section in either original logical map (offsets10,057,776 and28,157,344;17 map entries each). Thus empty restrictions are source absence evidence, **not a nonempty hidden-API preservation test**. The API29 writer gate is verified from the installed writer implementation, but nonempty restrictions remain unexercised here. Unknown/unrepresented map sections, original string/pool ordering and physical debug encoding are outside the normalized preservation claim.

## Deliberate stop boundary

No PMS/handler/storage/reference/authentication transformation was applied, no opcode was intentionally changed and no source guard was weakened. Successful no-edit normalization establishes this writer path for these actual definitions; a later edit needs exact per-method/reference/metadata delta admission, inverse/roundtrip where applicable, retained unaffected records, source-frozen inputs and independent review. Whole logical-DEX emission was not needed to establish this bounded prerequisite and was not attempted. Its pool limits, instruction widening/layout, complete metadata coverage and runtime cohort admission remain unproved.

The ordinary039 subset is unselected OEM evidence. No ART parsing, class-loader isolation/linking, native registration, resources, service construction, Binder identity, user/policy/state owner, live credential/fingerprint/CE/key operation or phone acceptance follows from it.
