# Raw method-header preservation correction

The earlier Samsung framework baseline/permission leaf and failed ColorOS
services outputs remain rejected. Corrected successors now pass full raw-header
preservation and independent saved-byte review. A complete raw method-header
check found the gap missed by the earlier normalizer; the ColorOS no-edit attempt
independently exposed the same field drift. All artifacts remain unselected for
runtime use; no Android or phone test used them.

The frozen normalizer covers register count, instructions, debug, exceptions and
member metadata, but omits the raw incoming/outgoing argument-size fields. Its
successful comparisons therefore did not establish equality of those fields.
This is a gap in our earlier verification. Existing frozen reports and outputs
remain unchanged so their actual scope and execution history can be inspected.

Root compared all55,745 declared Samsung classes3 methods against the actual
permission edited, second-emission and canonical-inverse outputs. Each has274
unexpected differences, all in `outs_size`. Access/partition, code presence,
registers, incoming size, try count and instruction size match, accounting for
the separately approved GL instruction-size change in the edited pair. The
inverse's equality to the old canonical2254 bytes does not fix the canonical's
own header drift.

The new ColorOS classes2 attempt correctly failed its stronger guard:233 methods
change the same outgoing-size field. Its76,707 normalized records and byte-stable
second emission do not override that failure. Independent review also accounts
for539 extra code items from splitting shared source items; no distinct source
groups merge. That failed output is not the accepted ColorOS inverse baseline.

The subsequent writer inspection identifies the mechanism: outgoing-word
calculation handles method and call-site references but omits filled-array type
references. The complete source value is restored regardless of whether a
particular change would affect runtime allocation. No crash or ART-allocation
claim is inferred from the changed word alone.

The reviewed bounded correction restores only each source method's
outgoing-size word after validating every other raw header field and identity.
It reparses the result, proves an exact byte-change whitelist including DEX
integrity fields, and runs after every actual emission/re-emission. Existing
decoded-record, initializer, API-policy, shared-code and inverse checks remain.
The [Samsung successor](samsung-framework-preserved.md) and its
[independent review](samsung-framework-preserved-review.md) pass for the selected
full framework DEX. The [ColorOS successor](coloros-services-preserved.md) and its
[independent review](coloros-services-preserved-review.md) pass for the selected
services DEX. Their exact new hashes are in [the integrated checkpoint](../PREPARED_BOOTSTRAP.md).

A separate [two-service extract review](samsung-service-code-headers-review.md)
found two outgoing-size drifts in the earlier Samsung UMS/LSS039 subset. Those
old subset outputs also remain held. The new full039-source profiles do not
silently admit that041-to-subset workflow.

The component inventories and [current correction inventory](../inventory/framework-code-header-correction.json)
retain the actual failed evidence. Source byte hashes are not runtime identity,
and no code-generation result supplies the missing authority/BOOT/native graph.
All18 device cases, architecture selection and release gates remain open.
