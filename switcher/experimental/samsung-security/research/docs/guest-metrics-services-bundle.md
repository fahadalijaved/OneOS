# Prepared services archive composition

This PC-only composer prepares an unselected services JAR from three literal
binary inputs. It never invokes a compiler, D8, OneOS patcher, Android/OEM code
or a phone. Original sources, user-stored images and OneOS-owned files remain
read-only inputs.

The original ColorOS archive is SHA256
`66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3`.
Only `classes2.dex` is replaced with the actual primary DEX
`a93fe9b89a0d1f247f47072df8ce24de9060be9efcd9bfac1d69a75d8a678c9b`
from immutable primary receipt `12dd669e…`. The separate seven-helper DEX
`11fd05dcd1a69ce6b8fb0e585f5ae573c8cbadc929713a29afcf36d0831dc7c8`
comes from immutable helper receipt `fdd4f619…`. Receipt and binary paths/hashes
are literal constants; moving canonical inventories are not producer inputs.

Before composition, the tool requires the exact original contiguous sequence
`classes.dex` through `classes4.dex`, valid ordinary DEX039 checksums/headers,
unique class definitions within and across every original DEX, an unchanged
primary class-definition set, and no collision with the exact seven helper
definitions. The first missing contiguous slot is therefore `classes5.dex`.
The frozen helper reader independently verifies all five public cell OFF bodies
and retained private controllers. ParentClient is outside the helper allowlist.

The actual archive contains stored and deflated members, UTF-8 flags and data
descriptors. Rebuilding entries through `ZipFile.writestr` would normalize some
metadata. Instead, this composer copies every non-target local record byte for
byte, including its compressed payload, local metadata and descriptor. It copies
every original central record, changing only required local offsets. On the
target entry, only payload and CRC/size fields additionally change; names,
timestamps, attributes, extras, comments, methods and flags stay unchanged.
The deterministic new helper entry is stored, has a fixed timestamp and regular
0644 attributes. Every original entry keeps its order; the helper is appended.

The parser admits only bounded classic single-disk ZIP: no duplicates, traversal,
encryption, symlinks, ZIP64, overlapping/gapped local records, inconsistent local
and central names/metadata, malformed data descriptors, or trailing data. It
checks bounded decompression and CRC for every member. Limits are 64 MiB archive
and aggregate expanded bytes, 32 MiB per entry, 256 entries and bounded DEX tables.
There are no subprocesses or environment-dependent tool invocations. Own output
uses an exclusive timestamp/UUID directory; a finite elapsed-budget check rejects
a run exceeding 45 seconds, rather than claiming a preemptive process timeout.

Local extras permit the exact format seen in the pinned source: complete TLVs
followed by at most three zero alignment bytes. Central extras remain strict
TLVs. The first reviewed attempt rejected this source padding before any JAR
write; its failed handle, source and freeze are retained under
`out/guest-metrics-services-bundle/20261106T012432661462Z-5cab4a68d1db4c8e96469067acf9c183/`.
Table independently verified all fourteen suffixes and cleared the narrow
correction. Root separately authorized one corrected attempt using exact tool
`7b981789…`. The failed run remains distinct and is not assigned success.

The composer writes two independent JARs, reopens their saved bytes, validates
the same entry, metadata, DEX and class-set contracts, and requires byte-for-byte
equality. It rechecks source freeze and all literal binary/tool/receipt pins.
Generated archives and receipts belong only to ignored
`out/guest-metrics-services-bundle/`.

All original `META-INF` bytes remain unchanged. The receipt lists conventional
signature entries if present. There is no signing or signature verification;
any signature covering changed contents cannot be claimed valid. ZIP CRC and
DEX integrity checks establish neither OEM authenticity nor ART acceptance.

The separately authorized corrected PC composition passed. Both saved archives
reopened successfully and were byte-identical; all input/source pins remained
stable. The command was:

```text
python -B tools/build_guest_metrics_services_bundle.py --freeze out/guest-metrics-services-bundle/SOURCE-FREEZE.json
```

The immutable receipt is
`out/guest-metrics-services-bundle/20261106T012924622707Z-3ef008ff9b6c4ed6ab98f0345a44c2f9/receipt.json`,
SHA256 `070fead43eb55e606b165d6d8eee4a32ffcfbe0be4be5f158e6f052622bae101`;
the [inventory](../inventory/guest-metrics-services-bundle.json) is its identical
derived copy. Both 44,630,115-byte JARs have SHA256
`e016aa77a6defa38c08946f4d1917b3747ebf2dd8737fcfdf9384b5277886902`.
There are 84 entries, preserving the original 83 in order. All 26,650 original
class definitions remain, with seven helpers appended and no collisions.
The three original non-target DEXs are byte-identical. No conventional JAR
signature entries matched the bounded name scan; no broader authenticity or
signature-validity conclusion follows.

The seven helpers remain in a separate DEX and fixed OFF. Resource APK admission,
OneOS 0.4.57 patch composition, actual DMS services-loader/native/source/current
parent binding and real retirement control remain required, unselected gates.
This artifact is not a runnable integration, security result or device candidate.
