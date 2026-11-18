# Publisher alias: independent source and saved-output review

**PASS for the unselected PC publisher-alias component only.** No material scoped defect
was found in `prepare_guest_installd_alias.py`, SHA256
`1293e0a484115ec007901deb2c30b0b8effdbf504af73cf0bedf2c3f73186f86`.
The pre-emission source review preceded root's separate authorization of one
actual static workflow. Independent saved-output readback now also passes.
This is not runtime selection, a private data view or daemon-launch approval.

## Actual saved-output successor

The immutable pre-use report/inventory/freeze beforeimages are under
`out/guest-installd-alias-review/history/pre-emission/`; original pre-use freeze
`b589e72f2115216393446231b479e6709aca9452674fc4349748b8045aad42f6`
remains unchanged. The author retained the executed pre-use inputs separately.
The following is a successor review, not a retroactive change to that clearance.

Readback checked the source and three actual saved byte files at
`out/guest-installd-alias/20261106T040812300982Z-271fd9053e2c4d8983463e6e76a43a76/`.
All are 640,912 bytes. Primary `installd-guest-nstalld` and saved
`installd-reapplied-nstalld` both have SHA256
`511dac7eae780ad476c84953805a380e4943175672503d9c53b264b6cad54a1e`.
The saved inverse is byte-for-byte the original `ed618c38…` file, and the saved
reapplication is byte-for-byte the primary output. The actual primary differs
from the entire original file **only at `0x26239`, `9c→a0`**.

Independent parsing confirms equal ELF headers, program tables, section tables,
all 26 file-backed non-text sections and every other byte. The resulting ADD,
unaltered ADRP, pooled string/suffix and 42-byte UTF16 descriptor match the
source contract. Therefore relocation tables, BTI/PAC/build-id notes, unwind,
protocol code, vtables and all other instructions retain their exact bytes.
This is static preservation, not loader, linker or native execution evidence.

The author receipt is
`e81fd1dc1e04d6ac78a13b3303e229f360210c0c87550dbcd5e0d199881f34a5`.
The actual one-primary/one-inverse/one-reapplication runner source and executed
input snapshots were inspected and hashed; all sixteen pre-use pins have a
matching immutable input/source image. The reviewer **did not invoke** the
patcher, plan, fixtures, runner, inverse or reapplication. Saved files were only
read and compared; no modified OEM buffer was constructed by the reviewer.

The author's final report/inventory are `ba59e56f…` / `5bbe42e8…`; final author
freeze is `0295be62f9daecb554fc8a7eb991607643a8a9059f385ad08173bc906523f713`.
That freeze leaves this independent review separate, avoiding a reciprocal pin
cycle. No additional emission or runtime action follows from this result.

## Source review retained from the pre-use phase

The reviewed [proposal](guest-installd-alias.md) and inventory are pinned at
`4fdf1d33cf95e41315886c8b84145ff08cd2b36861254c5b93f585fadbbd0bff`
and `578951a4bb3519b612533b969dcb9130a0eaac65b53ee4951032d3b6919d23af`.
All six inputs in its corrected pre-emission freeze were rehashed. The earlier
standard-RELR-only draft is superseded history; no emitted artifact is credited
to either proposal.

Independent Python readback inspected the actual 640,912-byte ELF with SHA256
`ed618c386528c0b9890c67cbdcb22e1c194f44b034d8e36be2d7f2217fef7dfc`.
It did not import or call the author's patcher, plan, fixtures, apply or inverse
functions. No full modified OEM byte buffer or executable was constructed.

| Boundary | Independent source/readback result |
| --- | --- |
| Publisher site | Mini-debug symbol places the ADD in the original 596-byte `InstalldNativeService::start` window. All saved instructions in that window match actual source bytes. The original name is constructed before the manager's indirect publisher call. |
| Address and instruction | Original ADRP at `0x26234` gives page `0x10000`. ADD at `0x26238`, `219c0791`, decodes as 64-bit x1→x1, unshifted immediate `0x1e7`; candidate `21a00791` preserves operation/registers and changes the immediate to `0x1e8`. |
| Literal | Actual source contains `installd\0` at `0x101e7` and its existing `nstalld\0` suffix at `0x101e8`. No pooled string rewrite is needed. |
| Mapping | Both selected addresses equal file offsets in this ELF. The ADD is aligned in the existing executable, nonwritable PT_LOAD with 16-KiB alignment. |
| Relocations | Independently decoded 1,039 normal/Android APS2 RELA records and Android RELR section type `0x6fffff00`: 33 words → 756 ordered, file-backed targets. Dynamic address/size/entry tags match. None overlaps the ADD or has a selected literal-range addend. |
| Encoded references | Independent bit decoding reproduced all 244 bounded ADR/local ADRP+ADD candidates over 110,470 instructions and their saved containing symbols. One is the publisher ADD; no direct B/BL targets the ADD. No aligned pointer word points into the literal range. |
| Preserved data | Actual source matches all seven recorded section hashes, GNU BTI/PAC property note, historical build-id note and the full **42-byte** UTF16LE IInstalld descriptor. |

The encoded reference query permits a preceding ADRP within forty bytes; it does
not establish complete register/dataflow provenance across clobbers or branches.
It is a candidate inventory, not a claim that every computed reference is known.
The fixed patch leaves every other use of the unchanged literal untouched.

Source inspection confirms `apply_approved_profile(source)` admits only the
literal original full size/SHA and exact original instruction/string/descriptor,
changes only the fixed instruction, requires the one-byte difference at
`0x26239` and checks an exact inverse. The separate inverse additionally checks
the supplied actual output hash/size and equality of all other bytes, then
requires original bytes/SHA. That output hash is input identity, not authority.
The CLI exposes only `--plan`; a generic four-byte replacement helper is used by
fixtures and does not relax the fixed-profile apply API.

The author's saved two positive / eleven negative authored-fixture results were
reviewed against their source. They cover aligned replacement/inverse and short,
misaligned, out-of-range, wrong-word/width/profile inputs, plus malformed RELR
word length, initial bitmap, alignment and duplicate targets. These fixtures were
not rerun by this reviewer. At that pre-use checkpoint, actual apply/inverse/
roundtrip and output byte-whitelist evidence remained pending. The saved static
artifacts above now close that bounded byte-production gate; no OEM code ran.

The successor satisfies the required entire-file comparison, exact
`0x26239: 9c→a0` whitelist, full saved inverse and deterministic reapplication.
Source identity was rechecked. The new full SHA identifies this artifact; the
unchanged build-id remains historical metadata. No generic descendant or later
emission is admitted by these checks.

Alias collision/policy, genuine endpoint/caller/epoch ownership, complete guest
lookup/death/reconnect, original protocol/loaded library binding, pre-main native
filesystem/mount/propagation/SELinux-capability ownership and all fourteen global
bind replacements remain unbound. An alias neither isolates shared state nor
acknowledges real native work. No OEM/native/phone execution, launch or capture
component change occurred in this review.
