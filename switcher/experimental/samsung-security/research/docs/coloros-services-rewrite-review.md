# Independent strict ColorOS services no-edit review

**STRICT REJECT: 233 raw outgoing-register headers changed.** This review covers only the
complete original ordinary039 classes2 prerequisite. No new references, hooks,
members, helper definitions, retirement wiring or runtime selection are admitted.
The reviewer has not run a compiler, writer, model, OEM/Android code or phone.

The source-before-run pair is `Probe-ColorosServicesDex.java`, SHA256
`34de5f26da61d7c8b70bdbaa5c9d8a69dc87461c4aeed9d48f14218f44bec964`, and
`probe_coloros_services_dex.py`, SHA256
`c24df3a8c65c12ea70a79eb9399a2690586d62afa5c7cd745370b7420b3efef7`.
The accompanying contract is `docs/coloros-services-rewrite.md`, SHA256
`9aad5e5c134524c1a36bc9439bb6145988ad47cb6ce99a301d179ecec3d4d306`.

The initial wrapper omitted exact raw incoming/outgoing code-header comparisons.
This was a concrete source-review finding, corrected before any attempt. The
accepted source now compares every code-bearing method's registers_size,
ins_size, outs_size, tries_size and insns_size in its strict raw identity list.
Debug offsets may move; normalized debug events and their PCs must remain exact.
No header or normalizer waiver was accepted.

Source checks also confirm:

- One complete pinned 10,042,704-byte classes2, ordinary039/header112/logical
  offset0; all 6,554 classes; no subset, slicing or rebasing.
- Unchanged full normalizer for class/member partitions/access, parameters,
  annotations, typed explicit encoded initial values, instructions/registers/
  references/literals/PCs/payloads, try handlers and debug events.
- The existing authored initializer adapter preserves the exact nonnull explicit
  prefix, including encoded false/null values; holes refuse. No default-value
  repair or changed semantic comparator.
- Complete raw string/type/prototype/field/method-reference sequences, class and
  member order/presence/access, code headers and absent HAPI section must match.
- Source/output code-bearing method sets and entire code-offset partitions are
  saved. Physical offsets may move. Root permits splitting a source shared group,
  with exact per-method equality; merging distinct source groups refuses.
- Map type sets must match. Only code_item count changes are allowed, exactly
  explained by additional unique code offsets; any other map-count/topology
  change stops for concrete review.
- Both emitted DEXes must retain ordinary039 integrity and HAPI absence. First
  and second emission must be byte-identical. This is canonical roundtrip
  equality, not reproduction of original physical input bytes.
- Frozen tool/archive/JDK/dexlib inputs, sanitized JVM/compiler environment,
  repo-local outputs, bounded input, 4GiB heap and180-second writer limit.

## Actual single-attempt failure

Build's same session72047 terminated exit1. Actual receipt:
`out/coloros-services-rewrite/20261106T000303598099Z-e592ea319eb3485a9cdffef5144e4c89/receipt.json`,
SHA256 `35702f1f4d308d7001b40cb47ec78e4b2c2da7c4668f4517e16e17e70c9c9949`.
The overall status is `FAILED_STRICT_NO_EDIT_CLASSES2`. The nested Java pass
label describes its narrower normalized comparison and is not baseline admission.

Independent direct parsing of the original archive entry and both saved emitted
DEXes confirms:

- Both outputs are 10,061,988-byte ordinary039, valid SHA1/Adler32, byte-identical,
  SHA256 `7c1f21be5a088181d2b97df1e2a742930621afa91ece1d680f992886aab4bba3`.
- All raw string/type/prototype/field/method-reference sequences, class attributes,
  class/member order/partitions/access and code-bearing method identities match.
  All three retain absent HAPI sections.
- Exactly 233 of 45,059 code-bearing method headers differ in **outs_size only**.
  Registers, incoming words, try count and instruction-unit size remain equal.
  The first is
  `CallMetadataSyncConnectionService$CallMetadataSyncConnectionIdentifier.hashCode()I`:
  outs 2→1 while registers 3/ins 1/tries 0/units 17 remain unchanged. Another enum
  `$values` method changes outs 4→0. No claim that these smaller headers are safe
  or semantically equivalent is made; invoke/custom behavior is not waived.
- Source 44,520 code-offset groups become 45,059 output groups. Independent
  partition checks find no merge of distinct source groups. Code-item map count
  increases by exactly 539, matching the allowed splits; every other map type/
  count remains equal. Producer topology guards were not reached after the
  header failure; these are separate reviewer observations.
- All three 181,484,460-byte normalized streams have SHA256
  `1c2607a7116a0d0e003b2f78bddddff1f540f908f5ed37cb9ae99853e2761d0c`.
  The reviewer verified every actual row's own normalized hash, uniqueness,
  76,707 records and 6,554 class records. Typed initializers, bodies, annotations,
  try/debug records compare under the unchanged pinned normalizer; raw-header
  equality remains a distinct failed condition.

The pinned normalizer records 23,289 fields, 46,864 methods, 779,940 per-method
instruction records, 12,569 try blocks, 338,252 debug items, 13,820 annotations,
6,140 explicit initial values and zero hidden-API members. The preflight's
778,811 instruction count scans unique code items; the differing count here
includes per-method aliases and is not an instruction-preservation failure.

Read-only reproduction:
`python -B out/coloros-services-rewrite-review/verify_failed_output.py`.
It consumes only saved source/output evidence, without invoking the producer,
compiler, writer, model or OEM code. No source or failed artifact was repaired.
The new raw-header guard caught a defect that normalized equality and repeated
byte emission alone would miss. No canonical no-edit baseline or inverse target
is admitted from this attempt. A separate explicitly reviewed preservation
mechanism/workflow is required before another attempt; the old failed scope
remains immutable, with no normalizer or header waiver.

The parent preflight's seven-string footprint remains conditional: maximum short
index65,534 has one index of room. A successful no-edit prerequisite will not
authorize additional strings or the three source-hook edits. A future edited
inverse must compare against the actual admitted immutable canonical output.
