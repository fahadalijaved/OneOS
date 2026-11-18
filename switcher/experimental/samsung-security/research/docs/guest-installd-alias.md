# Publisher-only installd alias proposal

**One PC-only prototype emitted; unselected.** Root accepted the spelling
`nstalld` as a bounded route-B discriminator, then authorized one static emission
after independent source review. Actual saved output, inverse and deterministic
reapplication pass the byte contract below. This is not final runtime naming,
an endpoint identity, a launcher or a security integration.

The input is the observed Samsung installd, 640,912 bytes, SHA256
`ed618c386528c0b9890c67cbdcb22e1c194f44b034d8e36be2d7f2217fef7dfc`.
Its [frozen native-owner card](retained-installd-native-owner.md) remains
unchanged. The [plan inventory](../inventory/guest-installd-alias.json) records
the exact byte/section/relocation/reference evidence. All addresses below are
ELF virtual addresses; the selected load segments give equal file offsets at
these particular addresses. They are not live process addresses.

## Exact proposed change

`InstalldNativeService::start` obtains the default service manager, creates its
String16 name, constructs the original BnInstalld object, and invokes the
manager's virtual publisher slot. The name's ADRP at `0x26234` supplies
`0x10000`; its ADD at `0x26238` supplies offset `0x1e7` before the original
String16 constructor call at `0x26240`.

| Item | Original | Proposed |
| --- | --- | --- |
| Instruction VA/file offset | `0x26238` | unchanged |
| Four-byte instruction | `21 9c 07 91` | `21 a0 07 91` |
| Decoded operation | `add x1,x1,#0x1e7` | `add x1,x1,#0x1e8` |
| String address | `0x101e7`, `installd\0` | `0x101e8`, existing `nstalld\0` suffix |
| Actual changed bytes | — | **one byte**, file `0x26239`: `9c` → `a0` |

Both operations are fixed-width, nonbranch 64-bit ADD-immediate instructions
with the same destination/source registers. No string is added or overwritten.
No code, data, segment, section or file size changes. This avoids rewriting the
pooled `installd` literal, which is also used by other original code/logging.

The bounded one-address query scans all 110,470 instructions in `.text` for
direct ADR and local ADRP/ADD patterns (up to 40 bytes). It records 244 encoded
reference candidates across 43 containing function symbols, including exactly
one selected publisher ADD; main alone has thirteen candidates. There are no
relocation addends or aligned pointer words into that literal range, and no
direct B/BL target equal to the patched instruction. The full metadata list is
retained under ignored firmware. This is not complete arbitrary computed-pointer
dataflow. That limitation does not require altering another user of the literal:
the proposal leaves the literal and all other instructions byte-identical.

## ELF and protocol preservation contract

The source is AArch64 little-endian PIE/ET_DYN. The patch is four-byte aligned
inside the existing read/execute, nonwritable PT_LOAD segment, with 16-KiB
alignment. No dynamic relocation overlaps the instruction. Ordinary and
Android-packed RELA records are parsed. The source also has an Android
`.relr.dyn` section (type `0x6fffff00`): 33 encoded words at `0x7d40`, expanding
to 756 relative relocation targets. Its three Android dynamic tags agree on
address/264-byte size/eight-byte entries. The bounded decoder checks every
target's alignment/order/file backing and original addend; none overlaps the
patch or points into the selected literal. All relocation bytes remain untouched.

The GNU property note advertises AArch64 feature bits 3 (BTI and PAC). Its bytes,
all entry/return instructions, indirect-call targets and branch displacements
remain unchanged. The ADD creates no branch landing pad or new stack behavior.
The original `.eh_frame`, `.eh_frame_hdr`, symbol/minidebug ranges and offsets
also remain unchanged. These are byte/layout preservation arguments, not a
successful loader/unwinder or execution test.

The exact UTF16LE `android.os.IInstalld` string at file `0x9351c` is preserved,
as are all original Stub/dispatch/marshalling instructions, vtables, `.rodata`
and `.data.rel.ro`. Changing the service-manager name does not translate the
guest protocol or prove ABI compatibility. The original GNU build-id note is
deliberately unchanged historical metadata; any later modified file must be
identified by its **actual full SHA256**, never that preserved build-id alone.
No signature, verity, policy or runtime-integrity admission is inferred.

## Producer and inverse review boundary

The [frozen pure patcher](../tools/prepare_guest_installd_alias.py), SHA256
`1293e0a484115ec007901deb2c30b0b8effdbf504af73cf0bedf2c3f73186f86`, has only a
`--plan` CLI and exposes no emission/launch option. Its fixed-profile
apply function requires the complete original size/SHA, old instruction, pooled
string, suffix and UTF16 descriptor. It permits exactly the single changed byte
above and internally requires a byte-exact inverse. There is no arbitrary alias,
offset, before-word, input path or general ELF writer in that apply API.

The inverse API separately requires the original source profile, actual
output size/SHA, exact replacement word and equality of every other byte; it
must reproduce the entire original bytes/SHA. The authorized ignored-out runner
called these exact authored byte functions, saving actual source/output/inverse
hashes, byte-diff evidence and deterministic reapplication. Frozen function
comments saying unexecuted describe their pre-emission history; the saved run
below supersedes that state without modifying the reviewed tool. Two authored
positive fixtures and eleven negative fixtures remain separate helper evidence.

## Actual one-emission result

The run is
`out/guest-installd-alias/20261106T040812300982Z-271fd9053e2c4d8983463e6e76a43a76/`.
Its `receipt.json` SHA256 is
`e81fd1dc1e04d6ac78a13b3303e229f360210c0c87550dbcd5e0d199881f34a5`.
The primary `installd-guest-nstalld` is 640,912 bytes, SHA256
`511dac7eae780ad476c84953805a380e4943175672503d9c53b264b6cad54a1e`.
Only file byte `0x26239` differs (`9c` → `a0`). The saved inverse equals every
original input byte and its `ed618c…` hash; saved deterministic reapplication
equals every primary output byte and its `511dac…` hash.

Parsed ELF metadata matches the source; every non-text section, the canonical
UTF16 descriptor and all other file bytes match. The input and reviewed tool
were unchanged before/after. All sixteen independent pre-use review pins
(`b589e72f…`) were checked before/after this workflow. Exact pre-emission
tool/doc/inventory/review/freeze/plan beforeimages and the runner source are
retained in the run's `executed-inputs/`. This is one primary emission plus the
explicit inverse/reapplication checks, not an OEM execution or runtime test.
Independent saved-output review is separate from these producer assertions.

ELF metadata preservation does not create Linux ownership, file capabilities,
SELinux context, verity admission or a valid process/mount namespace. No such
filesystem/runtime metadata was installed or changed.

The initial pre-emission draft incorrectly checked only standardized SHT_RELR
and missed this Android-specific section type. It emitted no ELF. Its exact
source/doc/inventory/receipt/freeze history is retained under ignored
`out/guest-installd-alias/history/before-android-relr-correction/`; this corrected
source supersedes that proposal before independent review or emission.

The frozen pre-emission plan/fixture command is historical proposal regeneration;
the actual output is established by the saved receipt and byte files above:

```text
python tools/prepare_guest_installd_alias.py --plan
```

Before runtime selection, actual name collision/service-manager policy,
endpoint/caller-generation identity, guest lookups/proxy/death/reconnect routes,
canonical protocol and loaded library cohort still need admission. The private
pre-main filesystem/root/mount/propagation/SELinux-capability/property owner and
replacement or segregation of all fourteen global OneOS binds remain unbound.
So do mirror updates, UUID mappings, quotas, native/deferred completion and safe
return. An alias cannot isolate shared state, authenticate a UID or become a
ready acknowledgement. Only PC-side bytes were patched; no phone/OEM/native
execution, live-process patch or daemon launch occurred.
