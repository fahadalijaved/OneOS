# Unselected ColorOS PIN audit-metadata leaf

**Built and statically checked on PC; unselected. No Android/OEM execution or
phone action.** This removes one proven optional ColorOS audit notification after
the real credential setter succeeds. It is not a credential verifier, Samsung
runtime, complete adapter, installed candidate or authentication acceptance.

The source-supported boundary is [CP-01](construction-protocol.md): ColorOS
`LockPatternUtils.setLockCredential(new,previous,user)` first calls the real
`ILockSettings.setLockCredential` and returns false if that operation fails. Its
later guest-only `setLockscreenPasswordType` writes package/type/user/wall-clock
audit text to `lockscreen.password.type`. Its only bounded native consumer reads
and logs that text. This dots-key is distinct from mandatory credential quality
and policy metadata. The user authorized removal of optional unsupported OEM
features while retaining genuine authentication and storage/key behavior.

## Exact edit and output

[Producer](../tools/build_coloros_pin_metadata_leaf.py):
`python -B tools/build_coloros_pin_metadata_leaf.py`.
The [inventory](../inventory/coloros-pin-metadata-leaf.json) and ignored
`out/coloros-pin-metadata-leaf/receipt.json` record the actual successful run.

- Immutable original framework archive:
  `d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2`.
- Exact method:
  `Lcom/android/internal/widget/LockPatternUtils;->setLockCredential(Lcom/android/internal/widget/LockscreenCredential;Lcom/android/internal/widget/LockscreenCredential;I)Z`.
- Original body:
  `c6f0ba72dc78f9c351632cbd4a470d29d681ba50c7eade5c6952f3159923f069`.
- Patched body:
  `868fd9b553fcabd2be6bd36c85b1247e47b07e7374a696a77ef8bcce4e2df4af`.
- Primary generated DEX:
  `out/coloros-pin-metadata-leaf/classes6.pin-metadata-leaf.dex`, SHA256
  `28eb3a7af9c6988edbfac8a0d258733259bb9c198176274143fd1886e115795a`.
- Offline reader ZIP wrapper:
  `out/coloros-pin-metadata-leaf/framework.pin-metadata-leaf.jar`, SHA256
  `fb2aef0fc1b8435a3cff8f9cbfdec8fb1472b7352e654d49765742d814e7f56d`.

All six source DEX files are ordinary **039**, not 041. The producer deliberately
admits this exact format/profile only. The selected method is in `classes6.dex`,
method ID4418, code-item offset706956, instruction offset706972. It has 63 code
units, seven registers and one try item.

PCs38 through51 become fourteen one-unit NOPs. The real setter at PC30, false
return at PC37, true return at PC52/53 and original RemoteException/error path
PC54 through62 remain byte-identical. A branch enters PC38, the patch start;
there is no interior branch/handler entry or payload. The original try range
PC22 through50 still ends at PC51, which remains a legal NOP instruction boundary.
The patch removes the optional notification call and its package/service lookup;
it does not replace the real setter or manufacture its Boolean result.

## Actual checks

The producer validates all six input/output DEX039 extents, table/data/map bounds,
SHA1 format signatures and Adler32 checksums. Only the admitted instruction slice
and required DEX integrity header bytes8 through31 differ in the primary DEX.
It enumerates all 17,065 encoded methods/14,893 code bodies in that DEX and rejects
another method aliasing or overlapping the changed instruction range.

Restoring the exact saved slice and recomputing integrity fields reproduces the
original DEX byte for byte. Applying the patch again reproduces the patched DEX
byte for byte. Actual independent dexlib-backed reads of original and patched
wrappers exit0: the complete archive retains 38,870 class definitions; all141
LockPatternUtils methods remain declared; exactly this method changes and the
other140 normalized bodies match. Registers, catches, branches and every
instruction outside the slice match. Wrong-body and interior-entry **decoded JSON
record** negative probes are rejected. These are admission-invariant checks, not
malformed-byte DEX fixtures. Actual-byte altered-branch, try/handler and method
code-offset-alias negative fixtures remain unexecuted; no runtime fault campaign
ran. All103 non-target ZIP entry payloads remain byte-identical.

The wrapper is reserialized ZIP: unchanged **entry payloads** are proved, not
identical physical ZIP encoding. DEX SHA1 is a format integrity field, not an
authenticity signature. No Android/JAR signing, ART verification, runtime
linkage, UI behavior or hardware acceptance is claimed.

## Required before any selection

The selected stack must exclude the optional OPPO audit producer/log consumer,
or remove only that consumer's exact optional read/log slice if its service is
otherwise retained. The same `hookOnSystemReady` has independent timeout work;
this leaf does not authorize deleting that work. Do not import an OPPO backend
solely for this optional notification.

An actual Samsung authority, correct typed protocol, admission/readiness owners,
current user/generation, commit readback and safe recovery remain mandatory.
The separate NONE/zero cache fallbacks and credential-change uncertainty still
require their own reviewed adaptations. Mandatory PIN/fingerprint, StrongAuth,
lockout, application keys and CE storage are untouched requirements. This leaf
does not remove existing OneOS preservation guards or select any phone payload.
