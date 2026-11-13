# Findings that improve subsequent work

- Reuse the parent immutable OS archives/indexes. Re-extract only selected regular
  tar members into this project's ignored stream folder; pin each member's bytes.
  Do not copy or decompile the entire OS again.
- Samsung services uses one physical DEX041 container with two logical headers.
  The second contains key credential classes. Preserve full-container offsets;
  an ordinary first-header reader can produce false missing-class conclusions.
- Use the shared static reader's exact descriptors and unique stream outputs.
  PowerShell/MSYS expanded the first literal `*` sentinels; the current nonglob
  sentinels fix that actual defect. Retry failed queries only, not completed work.
- The reader's raw-byte parity covers selected instructions/references/branches/
  literals/handlers/switches. Register operands are not independently bit-decoded,
  and array payloads have no positive parity case in the current selection.
  Preserve these limits instead of converting a broad count into all-opcode proof.
- Check Stub dispatch and parcel semantics early. Equal AIDL descriptor strings
  hid a concrete ColorOS10/Samsung54 credential-check mismatch. Fingerprint's
  matching-width field also had different OEM meaning.
- Check resource name and policy value, not only integer IDs. Security services
  imported against guest resources can silently read an unrelated value.
- Inspect constructor/getter bodies before considering device probes. LockSettings
  construction and fingerprint/Weaver acquisition have active side effects.
- Treat real verification as stateful. Legitimate reenrollment/migration/slot-map
  changes require one owner and crash reconciliation; read-only inspection of the
  code does not make its future execution read-only.
- Verify an actual pending native crypto challenge and complete its key operation.
  The framework can return random operation IDs, and an OEM success callback can
  follow a token-installation error. Already-unlocked storage is a separate fact.
- Use current source plus the original supplied jars as separate evidence tiers.
  OneOS source patch intent, original firmware bodies and installed patched-image
  behavior are not interchangeable.
- Use `python -B` for audit helpers. Some Windows sandbox path-resolution calls
  deny canonical metadata access even when file reads succeed; normal Windows
  access verified the input record without changing source containment rules.
- Keep scoped workers and their proof files disjoint. Reuse frozen receipts after
  source/tool pin checks; rerun only for a relevant source change or an unresolved
  concern. Root owns architecture, cross-report consistency and commits.
- This nested repository disables Git text normalization to preserve exact
  authored source/evidence bytes across checkout. No global Git setting changes.
