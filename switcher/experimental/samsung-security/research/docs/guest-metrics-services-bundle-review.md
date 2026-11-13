# Independent services bundle review

Accepted as **unselected PC packaging only**. No remaining material composition
defect was found in producer
`7b98178922b6bb9820687885f768581b220d391a3f6a3c2f4c1af4dfc55035b1`
and the saved44,630,115-byte JAR
`e016aa77a6defa38c08946f4d1917b3747ebf2dd8737fcfdf9384b5277886902`.
No compiler, D8, original patcher/publisher, helper/model, OneOS pipeline,
Android/OEM implementation or phone operation was run by this reviewer.

The corrected owner run exited0 in3.21seconds. Its immutable receipt is
`out/guest-metrics-services-bundle/20261106T012924622707Z-3ef008ff9b6c4ed6ab98f0345a44c2f9/receipt.json`,
SHA256 `070fead43eb55e606b165d6d8eee4a32ffcfbe0be4be5f158e6f052622bae101`.
Both saved JARs were independently read and are byte-identical. The separate
review checker reopened every entry of the first, validated CRC/uncompressed
bytes and parsed all five complete ordinary039 DEX class-definition tables.
The identical second file consequently has the same checked ZIP/DEX bytes;
this reviewer did not rerun the composer to establish that equality.

All83 original entries survive in their original physical and directory order,
followed by the sole classes5.dex append, giving84 entries. Every original
non-target local record is byte-identical: compressed payload, local metadata,
extras and data descriptor included. All original central records match except
relocated local offsets and target CRC/sizes. Original archive comments remain
exact. Only classes2.dex changes payload and integrity/size fields; its local
header otherwise matches exactly, including the original padding.

The target is exactly the previously accepted primary DEX `a93fe9b8...`, linked
to immutable primary receipt `12dd669e...`. It retains6,554 original class
definitions, with the previously reviewed two new members and three body edits;
this bundle does not regenerate or independently reapprove those edits. Other
original DEX uncompressed bytes remain exact. Independent class-set checks find
6,789/6,554/6,393/6,914 definitions across the four original DEXs, with26,650
unique classes and no cross-DEX duplication. The append equals the exact14,292-
byte helper DEX `11fd05dc...`, linked to immutable helper receipt `fdd4f619...`.
It adds exactly seven disjoint definitions, bringing the total to26,657, with no
ParentClient. The fixed-OFF public-cell body proof is reused from the frozen
independent helper review for these identical bytes; no helper code executes.

New classes5.dex is stored, flags0, with1980-01-01 timestamp, regular0644
attributes and no extra/comment. Its payload begins at44,607,228, a multiple
of4 in this literal layout. Alignment and DEX checksums are observations, not
proof of ART loading or the intended services-loader identity.

The complete source was reviewed before the first composition attempt. Its
extra-field parser incorrectly rejected original local alignment suffixes and
stopped before writing any JAR. Independent original-byte inspection confirms
14 such records: three1-byte, five2-byte and six3-byte all-zero tails, sometimes
after complete TLVs. The exact source amendment permits only those final1..3
zero bytes for local extras; central extras remain strict, and all raw bytes
are still copied unchanged. The original source/freeze/failure evidence and
this review's original/amended source-phase snapshots remain preserved. Root
separately authorized the corrected attempt; there was no automatic retry or
metadata-normalization waiver.

The admitted source uses literal original66d0d51d, approved primary/helper binary
and immutable-receipt pins plus the frozen static OFF reader. It consumes no
moving canonical inventory. Classic ZIP names, bounds, local/central agreement,
CRC, exact descriptors and contiguous layout are checked. Both independently
composed saved files reopen and compare; every admitted input/source is rehashed.
The45-second limit is an elapsed-budget check rather than a preemptive timeout.
No subprocess or environment-dependent compiler/tool command is invoked.

All META-INF bytes are preserved. No conventional SF/RSA/DSA/EC/SIG-* signature
entry exists in this literal source, and no signing or signature verification
was performed. Preserved META-INF, CRC and DEX checksums establish neither OEM
authenticity nor any signature's validity after code replacement.

The frozen helper definitions stay separate and fixed OFF. The resource APK,
actual OneOS patch pipeline, services loader/BOOT/hidden/native identities,
current genuine parent/source visibility, enabled control and retirement/drain
ownership remain unselected external requirements. This JAR is a bounded
packaging prerequisite, not a runnable integration, authority attestation,
security result or device candidate. Exact inputs, independent checks and saved
artifacts are pinned in the paired inventory.
