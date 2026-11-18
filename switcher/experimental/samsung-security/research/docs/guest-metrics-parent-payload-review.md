# Independent DMS parent payload review

**PASS for the unselected, fixed-OFF three-hook static artifact.** No concrete
source or saved-byte defect was found. This review does not select a runtime
cohort, enable transport or establish Android/native acceptance.

The Java producer `3ed1fc6a…` and Python coordinator `96316759…` were read and
hash-checked before root authorized the single attempt. The final hook contract
was doc `c0a2bec6…`, inventory `38f234ec…`, auditor `8ce619e2…`. The separate
closed-header and source-flow reviews were cleared before emission. Their raw
baseline also established that each selected debug stream is unique to its hook;
no source alias forced an extra debug stream split.

The actual attempt terminated successfully with receipt `12dd669e…bbe8a`.
This reviewer invoked no writer, compiler, header preserver, model, OEM class,
ART/JNI/native code or phone action. A separate ordinary039 reader inspected
the immutable original and all six saved writer/preserved DEX files, hash-checked
every saved raw proof, and compared the actual normalized metadata streams.

| Actual output | SHA-256 | Bytes |
| --- | --- | ---: |
| Forward and actual reemit | `a93fe9b89a0d1f247f47072df8ce24de9060be9efcd9bfac1d69a75d8a678c9b` | 10062584 |
| Symbolic inverse | `620bc981ce11b3367f4933ad96fb7326ccd5e2d9a1dec47a3a53bb88a0ccbba1` | 10061988 |

Forward input is original services.jar `66d0d51d…edf3`, whole classes2.dex
`c9a84ceb…659f`. The actual second emitter consumed repaired forward bytes.
The inverse target is corrected no-edit620, rather than physical original DEX
equality. The reviewed sources remained unchanged during the attempt.

## Actual preservation checks

- All 6554 class definitions, original member order/access/partitions,
  superclass/interfaces/source metadata, class/field/method/parameter annotation
  graphs and explicit static initializer prefixes match the original. All original
  constructors remain exact. The only added declarations are the implicit-null
  private volatile field, access `0x42`, and the package-private virtual dispatch.
- All 45059 original coded methods have their complete raw headers checked.
  Their decoded instruction scalar bytes, opcodes, widths and resolved references
  match the original under the three approved PC maps. The exact 8/9/12-unit
  blocks and R6/ins5/outs6/tries0/11-unit dispatch match independently specified
  instruction bytes. No other original body changes. All 22 original branch
  edges retain their displacements and mapped destinations.
- Ordered raw try groups, exception types and handler destinations match those
  maps, with only the two specified Throwable regions added. Complete raw debug
  presence, line_start, nullable parameter names, ordered local/line/source and
  prologue/epilogue events, registers, resolved MUTF8/type payloads and terminal
  END_SEQUENCE address **and line** match independently. State-only advance
  encoding may vary. END cursors onStart54/phase276/Binder25 become62/285/37;
  they are not replaced with method-end addresses.
- Full original pool/reference sets and relative order remain, with exactly
  seven strings, two types, four prototypes, one field and four method references
  added. The maximum actual short const-string index is65534; no existing opcode
  widens. All map type/count entries match the finite projection: code_items45060,
  type_lists10762 and debug_info30669. HAPI remains absent. Original code aliases
  may split; no output group merges distinct original source groups.
- All76707 original normalized records were compared. Exactly the three hook
  records change; the field and dispatch make76709 edited records. Inverse records
  match the original. Forward/reemit are byte-identical and inverse matches the
  literal corrected620 baseline.
- For each of forward, reemit and inverse, the reviewer independently located
  233 required outs words by original method identity and checked the writer
  versus preserved byte pair. Exactly257 bytes change; every change belongs to
  those planned words or integrity bytes8..31. No repair escapes that whitelist.

## Separate helpers and limits

The separately emitted helper JAR `6cdfca85…e10` contains only its classes.dex
`11fd05dc…dc7c8`: exactly seven authored definitions and no ParentClient.
The reviewer independently parsed its three reached Cell methods: capture returns
literal null, phase returns the actual OFF enum and dispatch returns literal false,
without argument reads or calls in those wrappers. No helper definition is merged
into the6554-class primary payload. Existing SDK37/D8 diagnostics remain separate
from Android acceptance.

These bytes prove an offline source-preserving fixed-OFF prototype. OFF does not
grant readiness, authenticate a current parent/epoch, retire an old owner or drain
native operations. Actual DMS services-loader visibility and canonical identity,
helper/client placement, BOOT/Context/VM admission, live lifecycle/acquisition and
retirement/drain ownership, packaging and device execution remain unselected.
The field/capture failure semantics and original descriptor parsing boundaries are
the frozen finite contract; no ON build or extra control/retirement hook is added.

Bounded derived results and the independent reader are pinned by
`inventory/guest-metrics-parent-payload-review.json`. Raw OEM evidence remains in
the producer's ignored firmware directory. The review generated no OEM binary.
