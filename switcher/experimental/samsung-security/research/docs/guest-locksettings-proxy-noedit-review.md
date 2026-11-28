# Guest LockSettings Proxy: independent no-edit output review

**PASS for the complete saved no-edit output.** The preserved first DEX and its
actual re-emission are byte-identical `7470bc67`; the two full JARs are identical
`e1f3ef4b`. This establishes an offline no-edit preservation prerequisite. It
neither emits the proposed 33-method leaf nor selects any runtime/security path.
The separate source review `a399b900` remains unchanged.

The reviewed input is the actual staged framework archive `5cb16a37`, whose
original `classes6.dex` is `47f3b688`. The saved source DEX equals that exact ZIP
entry. Root's one-workflow gate `6dc63a92` named producer `cafd12f8`, its source
freeze `680f9cad` and independent source pass `d63e50e5`. Saved terminal session
80775 reports one run, exit zero; receipt `94606ba6` and output freeze `2fd65405`
are independently pinned. No compiler, producer, writer, negative probe, OEM code
or phone operation was run by this reviewer.

## Independent actual-byte checks

A separate authored Python metadata parser reads the original and both final
DEX files. It compares every raw instruction byte and code header, resolved
instruction references and typed catch ranges/handlers across all 14,893 coded
methods. All 14,523 present debug programs retain lineStart, parameter names,
events and the END address/line cursor. Debug absence remains absence. It also
compares all original classes, member flags/partitions/order, annotations,
parameter annotations and typed encoded static values with explicit prefixes.

Ordered raw string declarations/MUTF8, type indices, proto shorty/result/parameter
indices and list presence, field/method IDs and structural class indices are
exact. All 4,253 shorty indices are included. The complete 34,109 numeric HAPI
entries, their class order/absence and the raw 42,949-byte policy section match
the source. Map cardinalities match with the disclosed code-item split: 14,352
original code groups become 14,893, with 541 splits and no merge of distinct
source groups. This is semantic/raw-content preservation, not equality to the
original physical DEX layout.

For each saved writer-to-preserved pair, the checker independently derives the
62 `outs_size` words from original method-to-output-code mappings, substitutes
only those words and the original HAPI section, then computes the DEX integrity
fields. That exact byte array equals the saved final output; there are 4,698
changed bytes and no other changes. The actual corrected first DEX is named in
the re-emission argv and its input hash. Both final DEX files agree byte for byte.

All 36,318 normalized class/member records have valid content hashes and match
across the source and both outputs. Both JARs preserve every original entry
name/order/comment and each non-target entry's expanded bytes. Original
compressed ZIP bytes/layout and OEM signing authenticity are not claimed.

The saved shorty-negative DEX `443eae8d` has valid DEX integrity and changes only
shorty index 1,819 to 1,820 plus integrity fields. Its semantic proto descriptors
remain equal while the independent raw-ID comparison detects the difference.
The author's recorded rejection was not rerun. All 63 frozen files were hashed
before and after reading. The 14 executed-source snapshots match their pinned
inputs. Five retained command results report terminal exit zero, no reader,
overflow or cleanup failure, and the bounded sanitized command profile. These
records are not process or Android attestation.

## Admission boundary

No material defect was found in the saved no-edit outputs. Root owns the
separate literal baseline-admission edit; this card does not perform it. Leaf
emission, its actual forward/roundtrip/inverse proof and activation remain open.
All 29 untouched incompatible Proxy transactions remain runtime blockers, along
with genuine endpoint/caller/user binding, constructor suppression, local18
lifecycle, cache/currentness/policy, native completion and key/CE/commit ownership.
No runtime, authentication or device acceptance follows.

Evidence: [independent saved-output proof](../out/guest-locksettings-proxy-retarget-review/actual-noedit-output-check.json),
[checker source](../out/guest-locksettings-proxy-retarget-review/check_actual_noedit.py),
[author output freeze](../out/guest-locksettings-proxy-retarget/ACTUAL-NOEDIT-OUTPUT-FROZEN.json)
and [unchanged source review](../out/guest-locksettings-proxy-retarget-review/FROZEN-SOURCE-REVIEW.json).
