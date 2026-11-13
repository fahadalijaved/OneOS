# Independent source-header-preserved ColorOS workflow review

**PASS: source-header-preserved no-edit prerequisite only.** The single corrected
workflow and its actual outputs passed independent review. The prior no-edit failure and
its independent rejection remain frozen. No reviewer compiler, writer, model,
OEM/Android code or phone execution occurs.

The prepared flow deliberately refuses while the shared preserver hash is unset.
Its intended sequence is original archive→first emission→source-header
preservation→decode/full original comparison→actual re-emission of that repaired
first DEX→preservation→decode/full original comparison→byte equality. This avoids
comparing two separately repaired products whose second writer consumed an
unrepaired input.

Static flow inspection finds explicit guards for:

- Original complete ordinary039 classes2 and literal archive/DEX/toolchain pins;
  no hooks, new references, members, helpers or instruction-size exceptions.
- Frozen pure header-preserver API with source profile and exact candidate hash;
  independently recomputed changed-byte whitelist for outs words and header
  integrity bytes8..31, fixed233-method writer-drift profile, exact full restored
  source identity/header list.
- Unchanged typed explicit initializer adapter and full code/parameter/debug/
  annotation/try normalizer; first restored output checked before re-emission.
- Full ID/reference/member/order/code-header equality, HAPI absence, split-only
  code partitions, no merged distinct source groups, and only exactly explained
  code-item map-count differences.
- Four bounded Java stages under an aggregate180-second writer-stage budget,
  fixed 4GiB heap, existing sanitized command boundary, local outputs and generated
  artifact bounds. Both repaired outputs must be byte-identical.

The reusable preserver source was independently read before use, SHA256
`943977880527f9cbc21f451c15b887fe5f513c88e9a20fbf3e61717f8068edc6`.
Its fixed original source profiles and exact caller candidate hash guard a pure
byte transformation. It checks all declared methods, flags, partitions,
code-presence, non-outs headers and conflicting shared-output word mappings
before mutation; it reseals and reparses after the actual byte whitelist check.
It does not authenticate the emitter or admit complete metadata/runtime behavior.
The ColorOS workflow uses transformation `none`; no Samsung GL size exception
is admitted for ColorOS. No normalizer change or smaller-header safety claim
was accepted.

Trust then applied that frozen module to the two saved failed ColorOS outputs,
without rerunning a writer. The reviewer independently parsed the actual original,
failed and saved repaired bytes. Both saved copies SHA256
`620bc981ce11b3367f4933ad96fb7326ccd5e2d9a1dec47a3a53bb88a0ccbba1`
restore exactly 233 independently derived outs-word locations; all 257 changed
bytes are those words or integrity bytes8..31. Candidate size, offsets, code
groups, full original raw IDs/members/class attributes and all original headers
match; ordinary039 integrity and HAPI absence hold. This establishes the bounded
saved-copy repair only. It does not prove actual re-emission of a repaired first
input. The reviewer did not invoke the helper, fixtures, compiler or writer.

The final wrapper source is SHA256
`837e68a804462d997d29d0e9988943f63b1deb4f9bc0c9cdc5e8183a8d52e0bd`,
with pre-run contract doc `1ea8dc778ed2fd3dfb5f7c5fbe9640e6ab49bca67e1dfabd4891796d618afe4b`.
Its final result doc is `34ee1541b91ff910aeb0ffe165578bef26c88faecaaad86d7ac5b38ea75c4646`.

## Actual corrected workflow

Same session96243 terminated exit0 without restart. The immutable receipt is
`out/coloros-services-preserved/20261106T002036982583Z-f6f5ab2395a34f279d39f26feea6f599/receipt.json`,
SHA256 `47ead2f7d09e9849aca46aa82414319a98fe454517c68eb584e0bd99a3d11591`.
The reviewer verified actual generated orchestration source against the frozen
wrapper literal, generated-source hashes and all four terminal stage records.
The second emission's actual input hash is the preserved first hash620bc981…,
not the unpreserved7c1f21be… file. This closes the saved-copy-only limitation.

Both actual final files are10,061,988 bytes and byte-identical, SHA256
`620bc981ce11b3367f4933ad96fb7326ccd5e2d9a1dec47a3a53bb88a0ccbba1`.
Independent binary parsing confirms original45059 method headers exactly,
all raw string/type/prototype/field/method-reference lists, class attributes,
class/member order/partitions/access, code presence and ordinary039 integrity.
HAPI remains absent. Every emission independently needs233 outs words restored;
only257 actual bytes differ from each immediate writer output, within those
words and integrity bytes8..31.

The complete source/output code partitions are split-only:44,520 original
groups→45,059 final groups, no merge of distinct original groups. The only map
type/count delta is code_item44520→45059, exactly539 additional items. Physical
layout/group splitting is not reproduction of original physical input bytes.

All eight actual raw-output pins were checked. The three181,484,460-byte
normalized streams are identical SHA256
`1c2607a7116a0d0e003b2f78bddddff1f540f908f5ed37cb9ae99853e2761d0c`.
The exact stream's76,707 individual row hashes/uniqueness and6,554 class records
were already independently verified in the immutable failed-output review;
matching complete actual stream hashes reuse that check. The unchanged
normalizer retains parameters, typed explicit values, code/try/debug records
and annotations; raw code headers are now separately exact rather than waived.

Readonly verification:
`python -B out/coloros-services-preserved-review/verify_corrected_output.py`.
It reads only saved inputs/outputs and the independent reader declaration. It
does not invoke the preserver, writer, compiler, model, OEM code or phone.

This620bc981… DEX is the reviewed immutable no-edit canonical candidate for a
later separately approved symbolic inverse. It is one complete DEX, not a whole
JAR/cohort or ART/runtime acceptance. The failed7c1f21be… attempt remains rejected.
No hook/member/helper insertion, retirement, policy/lifecycle/default-OFF
producer or future string footprint is approved. The earlier conditional
seven-string projection still leaves only one short-string index of margin.
