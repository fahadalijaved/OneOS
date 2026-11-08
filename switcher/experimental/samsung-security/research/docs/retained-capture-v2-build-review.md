# Combined capture APK v2: independent source and packaging review

**PASS for the corrected source and saved PC APK packaging only.** Reviewed source is
`tools/build_retained_capture_v2.py`, SHA256
`74138ddfb050bdbda02ad24564fd6350119c442c7ac5021cf21016621a1577ac`.
No builder, compiler, SDK tool, fixture, model, OEM class or phone operation was
executed by this reviewer. The separately authorized builds below completed
after their respective source-PASS and root-GO gates. The newest artifact has
its own saved packaging readback, without transferring the older result.

## Containment-corrected artifact: current packaging result

**PASS_SAVED_PC_APK_PACKAGING_ONLY** for the new 25,207-byte APK, SHA256
`aa74e7b0229359196e63055ab9e717f27864c7cd859a8efa1307c294889ae470`.
The new run is
`out/retained-capture-v2/20261106T044056474939Z-a419ab36ffd940ac845b844844160d6c/`;
receipt is
`d71523f374bac6507976a5cc3b76e9cc0cf885477b33f9a4f86b53cd99d8b682`.
It used unchanged builder `74138ddf…`, Module `169316f2…`, unchanged Permit and
four capture classes. Its distinct frozen GO manifest has SHA256
`c4b11511ece275d8ed13efd37d9e5db42bc94fb82723a7f19ddb51f11cb18ce3`.
That manifest references H's new containment source-PASS `7ca9d049…`, reuse of
the unchanged builder source gate, and root's additional one-build authorization.

The same independent read-only checks were applied to these **new actual files**:
thirty input hashes, seven source snapshots, six compiled/staged classes and
eight command records/logs match. The new APK has exactly nine expected ZIP
members, no duplicates/comments, all nine local/central header and CRC checks,
six preserved unsigned payloads/compressed streams/central metadata and stored
resources aligned at the newly observed 676→684 offsets with the exact signer
TLV. Current MF/SF digest links and embedded certificate metadata pass; its own
saved SDK log reports v3 true, v1 false and the pinned certificate, with its own
read-only alignment exit 0. No SDK command or producer was replayed.

The new APK contains actual DEX SHA256
`f205b4317f69f3b782aec1b65f18a25d4b3526e69ec54eb447fc3a3524529fba`;
extent, SHA1/Adler32 and class count six pass. Actual Module class is
`064a95a3d9d11dc979af25a272b6c71db0794ebbab3447aeeaaa65455773c7bb`.
The four reused component class hashes remain exact. The API37 unsupported/max36
warning remains recorded. H owns the complementary new actual catch/stage/
proceed/return and dependency-semantic review; it is not implied by ZIP success.

The old `5c4b8ded…` report/inventory/output-freeze beforeimages are preserved at
`out/retained-capture-v2-build-review/history/5c4b-historical-packaging/`.
Its historical packaging freeze `6b6572fb…` remains unchanged and its phone
exclusion below still applies. This new PC result grants no installation,
activation, restart or phone/security acceptance; those require separate review
and permission.

**The `5c4b8ded…` APK is not a phone candidate.** H's complementary emitted-code
review found the post-proceed stage CONST_STRING at PC4 outside the owned try
region. Root requires a narrow Module containment correction, new source PASS
and a separately authorized build before any phone proposal. This report accepts
only the historical packaging of the saved artifact; it neither accepts that
semantic behavior nor transfers acceptance to the corrected successor.

## Historical first output: packaging only, excluded from phone use

The exact source-only report/inventory/freeze beforeimages are preserved under
`out/retained-capture-v2-build-review/history/source-pass/`. The original source
freeze `8dd25d3cc21065c823eba83b12c73c310ad6e7cd3fcf9f9a89ca0fd7304acdd7`
remains unchanged. This section records a successor output review, not a change
to the source review that preceded emission.

The actual run is
`out/retained-capture-v2/20261106T043054646451Z-ada868c20ed6419995a8fd257bac68cf/`.
Receipt SHA256 is
`1e7ea9782f916c86176d3ecd7983d12290f4ce247d369ecc27d2b627687bc196`.
`OneOS-Retained-Capture-0.0.2.apk` is **25,207 bytes**, SHA256
`5c4b8dedcc35af9812940059d283168b6cd969ddfd0cc635342e21467164bef4`.
It contains exactly the six original payload members plus the three expected
signer members, without duplicates or archive comments. All nine local headers
agree with their central CRC, sizes, flags, type and filename; actual payload
CRCs pass. The six payloads, compressed streams and original central metadata
match the fresh unsigned archive. Header-derived resource offsets are 676 and
684, with the precise recorded signer TLV append and four-byte stored alignment.

Independent parsing validates current MF/SF payload, section and whole-manifest
digest links and the embedded PKCS7 certificate metadata. Saved official SDK
verification reports v3 true, v1 false and certificate SHA256
`ad40f7c185abb46a5ba4798625e3245333987594379e5014aa0c977e69febfc9`.
The saved read-only alignment command exits 0. These are inspected actual SDK
results, **not reviewer verification replays**; metadata parsing alone does not
claim v1 or independently recomputed v3 cryptographic acceptance.

At this saved-output readback, all thirty input hashes matched before/after records, including the builder,
frozen true-GO manifest and four immutable component classes. Seven source
snapshots match their selected source pins; all six compiled/staged class files
match the receipt. Eight command records/logs have exit 0, no timeout/output-cap
failure, owned cwd/home/temp and the recorded five-variable option sanitation.
The APK contains the exact saved DEX, SHA256
`0eb34fe9b92329392983af3373382cc1520c3c592304dbe4789c1bcc8b1345b1`;
its header extent, SHA1/Adler32 and six-class count pass readback. The actual
API37 unsupported/max36 warning is retained. H's emitted method/dependency
semantics, permit and manifest/resource review is a complementary scope and is
not duplicated or claimed by this packaging report.

## Source review retained from the pre-use phase

The module/API source gate is separate: reviewed Module `e9181ffd…` and Permit
`fe7c6d70…`, with H's source-manifest `46aa3aca…`. At source review the seven-file
proposal remained NO-GO. Actual emission required a new frozen own-output input
manifest with independent source PASS, root build go and explicit references.
Those fields express operator review; they are not runtime authority tokens.

One concrete guard correction preceded clearance. Initial source `1156d286…`
called `local_entry` for the six payloads but omitted that explicit local versus
central CRC/size/flags/type check for the three signer members. It also omitted
the signed archive comment check. Corrected `74138ddf…` adds the signer loop and
rejects source/target archive comments. The exact initial hash is preserved in
review history by reversing those two source-line edits and verifying SHA256;
no old source is falsely credited with the new guards. No build or test ran
during the correction.

Static readback, without importing the builder, rehashed its 21 literal inputs,
the four immutable Java8 component files and all seven selected module inputs.
The Registry and Family classes are staged from fixed timestamped paths with
literal hashes; neither component is recompiled. Only Module and Permit compile
with annotation processing and implicit compilation disabled, an empty source
search path and explicit SDK/API/component classpath. The compiler output must
have exactly those two definitions. D8 receives only those two plus the four
staged classes. Its checked DEX declaration set must contain exactly six, with
header extent, SHA1 and Adler32 validation through the pinned parser. SDK/API,
OEM, model and other definitions cannot enter that accepted program closure.

The only subprocesses are explicitly pinned Java/javac, AAPT2 and zipalign.
Commands use unique owned cwd, TMP/TEMP/JVM home, strip five inherited option
variables case-insensitively, cap drained output at 2 MiB and time out at 45
seconds. This is a time/output/environment bound, not a claimed heap-memory
bound. No compiled capture/module or SDK implementation class is invoked as an
application. The reused Vector/target helpers only inspect pinned saved source
and DEX declarations; they do not execute Vector or Samsung code.

AAPT2 compiles one strings file to a flat directory, then links to an output
directory requiring exactly binary manifest and resources.arsc. It does not use
the prior native ZIP/APK output paths. Python creates a fresh classic six-member
ZIP, with explicit timestamp/regular attributes and computed resource alignment.
Payload bytes, CRC, local/central fields, compression and extras are checked.
The resource table is stored; no v1 APK offsets, member sizes or payload hashes
substitute for newly generated values.

The existing pinned Java apksigner produces the signed APK; zipalign is read-only.
Acceptance requires official actual v3/certificate verification, exact manifest
badging, nine unique expected members, empty comments, all local/central header
checks and unchanged original payload/compressed streams/central metadata.
The fixed SDK signer alignment-TLV profile is checked relative to the newly
computed resource offset; its eight-byte transform is not an old absolute
offset. Manifest/SF digests are computed from current payloads/sections, and
bounded PKCS7 metadata must carry the pinned certificate. Metadata parsing alone
does not claim v1 cryptographic acceptance; official v3 verification is required.

Inputs, frozen manifest and builder are checked before/after; failures retain
their receipt and do not trigger an automatic workaround. Source XML rejects
unexpected permissions, components and attributes; Xposed metadata fixes Android
scope/API102/no reload and exact entrypoint. Source hashes remain necessary:
the builder does not independently attest arbitrary code chosen by an operator.

Root subsequently authorized **one bounded PC build** of those reviewed fixed
inputs. Its saved packaging and source-byte reuse are now inspected as described
above. This admits no future emission. D8's requested API37/max36 warning, Android/ART
placement, Vector callback delivery, genuine live owner capture, recovery and
all shared-security device cases remain separate. This clears no install,
activation, restart, OneOS switch or credential action. Prior alias and capture
reviews were not modified.
