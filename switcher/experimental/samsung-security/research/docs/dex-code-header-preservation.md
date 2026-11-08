# Preserve actual source DEX code headers after every emission

The new pure-Python module restores only original `outs_size` words after strict
ordinary039 header admission. Frozen module SHA256:
`943977880527f9cbc21f451c15b887fe5f513c88e9a20fbf3e61717f8068edc6`.
Sixteen authored static fixtures and five actual saved-output cases pass.
No original source, failed output/report, writer, OEM runtime or phone was changed.
Independent full writer workflows and their reviews remain separate evidence.

## Fixed API and source profiles

```python
repaired, receipt = preserve_code_headers(
    original_source_bytes, emitted_bytes,
    source_profile="coloros-services-classes2",
    emitted_sha256=literal_reviewed_input_hash,
    transformation="none",
)
```

The two admitted original profiles are Samsung framework classes3
SHA256`256cc1744c36a88d3ee4c9218d2cf0156816ce89a63cd98787dd1633edbdf1a7`
(8,830,032 bytes) and ColorOS services classes2
`c9a84cebd3bc22a48c0737a7de34d96ba0b97a6294d4bdd97c935543e605659f`
(10,042,704 bytes). Names are `samsung-framework-classes3` and
`coloros-services-classes2`. No041/container fallback or arbitrary source profile
is accepted. The emitted hash identifies caller input; it is not emitter/source
provenance or authority attestation.

Default transformation `none` requires all non-outs code header values to match
the original. The sole alternate literal is
`samsung-permission-gl-jumbo-v1`, only on the Samsung profile: the actual
GLLogWrapper.glStencilMask(I)V source tuple[regs3,ins2,outs3,tries0,units23]
must become units24, preserving its other fields. This exception does not approve
the instruction/debug/PM-reference rewrite; the surrounding producer must prove
that separately. Added/removed declarations or other header changes are refused.
Future legitimate profiles require explicit review, not generic caller exceptions.

## Admission, patch and independent byte proof

Before making a mutable buffer, the module parses and checks complete original
and emitted class/declared-method identity sets, original access flags,
direct/virtual partition, code presence and every code header. It requires exact
registers_size, ins_size, tries_size and insns_size except that single approved
GL length change. Source and emitted code/debug offsets may relocate; the tool
checks their consumed extents rather than equating physical addresses.

Consumed fixed tables, modified-UTF8 identities, class data, code/try/handler
extents and referenced sections are bounded. Distinct code items cannot partially
overlap. Shared emitted code offsets are grouped before repair: differing desired
source outs words for the same destination cause refusal. Source aliases may
split; this module does not independently approve instruction equivalence or a
new merge. Surrounding normalized-record, full ID/order, alias, HAPI, map and
policy proofs remain mandatory.

Only a conflict-free plan permits replacing each affected uint16 at emitted
code_item+4. Then the DEX SHA1 signature and Adler32 checksum are resealed.
Every changed byte must belong to those planned two-byte words or integrity
bytes8..31; file size is unchanged. The result is reparsed in full and all
source-based headers/identities checked again, with no remaining outs drift.
The function returns new bytes and metadata without writing either input.

Apply this function against the **original source after every emit/reemit**,
including corrected canonical, edited, reemitted and inverse outputs. Reemission
can recompute outs again. Pin this exact module in each new producer; do not use
a moving module output receipt as an input. Do not relax the old normalizer or
claim its omitted ins/outs fields establish preservation.

## Static fixtures and saved outputs

The16 fixtures cover exact repair/idempotence and refusal of register, incoming,
try-count, instruction-count, flag, partition, code-presence and identity changes,
conflicting aliases, checksum/short/041 inputs, unrelated byte mutation and a
missing exact GL method. They use authored039 byte fixtures and execute no OEM.

Shade reviewed frozen source943 before actual saved repair. Corrected copies are
only under
`out/dex-code-header-preservation/20261106T001804331100Z-638079cc70cf45baba9f80b8d5406d76/`.

| Saved case | Declared methods | Restored outs words | Corrected SHA256 |
| --- | ---: | ---: | --- |
| Samsung edited + saved roundtrip |55,745 each|274 each|14ddb4effc54dd6e7ed2ccfa4659c1b93d2da898bd44e8339ac7cff9f2267cb3|
| Samsung saved inverse/canonical |55,745|274|1c6d093f864e1a30ba78126469df3afc3ae4cfe1e1653f905c31d32bbe6b36ad|
| ColorOS saved no-edit + roundtrip |46,864 each|233 each|620bc981ce11b3367f4933ad96fb7326ccd5e2d9a1dec47a3a53bb88a0ccbba1|

All five reparsed header/identity/byte-whitelist/integrity checks pass; the actual
old outputs remain byte-identical. Their complete per-word receipts and the
summary026ce283… are in that owned run. These saved-copy results do not themselves
prove a new writer roundtrip; the new producer must reemit the **repaired first**
and preserve again. Independent review of actual ColorOS copies confirmed233
derived words/257 changed bytes including integrity, exact raw headers/IDs/member
attributes and unchanged candidate alias groups. Its separate receipt owns that
review; this tool does not manufacture review or runtime acceptance.

## Concrete cause, without a harmlessness claim

The actual pinned dexlib JAR is SHA256fe3e12c4… . Static javap of its
DexWriter.writeCodeItem shows outgoing count initialized0 at117, recomputed over
instructions169..293 and written at296..299. ReferenceType3 METHOD uses
MethodUtil's parameter-word count plus receiver, or actual register count for
polymorphic invokes. ReferenceType5 CALL_SITE uses actual variable-register count.
Other reference types contribute0. It reconstructs this header value instead of
preserving the original source word. ReferenceType1 TYPE includes filled arrays.

Two exact supplied Samsung source bodies distinguish this mechanism:

- AppId.hashCode(): FILLED_NEW_ARRAY with two words at PC4; Objects.hash(array)
  with one word at PC8. Actual source outs2 becomes emitted1.
- SystemService$State.$values(): FILLED_NEW_ARRAY with four words at PC8 and no
  method invocation. Actual source outs4 becomes emitted0.

Both selected original DEX map lists have no call-site-ID or method-handle-ID
sections. Do not assign these drifts to invoke-custom: the inspected writer
explicitly handles CALL_SITE, and the two examples are filled-array cases.
All274 Samsung and233 ColorOS observed changed words decrease on emission.
The original compiler's reason for its source allocations is not established.
This static evidence proves neither harmless oversizing nor ART-safe smaller
frames/runtime underallocation. Exact source preservation still requires every
word restored, regardless of that unresolved runtime interpretation. Raw writer
disassembly and two original method-body proofs stay ignored under firmware.

The module is a bounded code-header preservation component, not a full DEX
verifier, instruction/policy approval, Android build or runtime acceptance. The
previous failures remain historical failures; no phone candidate follows.
