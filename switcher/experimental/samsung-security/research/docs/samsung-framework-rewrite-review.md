# Independent full selected-framework rewrite review: rejected output

**Disposition: strict no-edit preservation FAILED.** The initial emitted DEX
remains rejected evidence. Correct headers, class counts and a shared decoder
comparison cannot justify selecting it. No full writer, compiler or OEM code was
executed by this reviewer; all checks read the existing failed attempt.

## Independent complete comparisons

The pinned original classes3.dex is ordinary039, 8,830,032 bytes, 7,881 classes
and65,412 method IDs. The first emitted039 is8,984,376 bytes. Both file-size,
header, SHA1 and Adler32 checks pass. That establishes valid framing, not unchanged
metadata. There is no second emission or roundtrip artifact in this failed run.

I independently streamed all107,060 existing normalized record pairs, checked
both content hashes and verified the same member/order. Seventeen represented
records differ: fifteen explicit false/null initializer entries disappear, and
two decoded restriction sets become WHITELIST. Every other represented record
matches. That representation misses substantial raw policy changes.

A separate standard-DEX parser compared **all99,179 member descriptors**:
43,434 declared fields and55,745 methods. It decoded full numeric ULEBs, without
dexlib enums, masks or policy-version labels. **28,559 flags changed**:

| Original raw flag | Emitted raw flag | Members |
| --- | --- | ---: |
| 7 | 0 | 2 |
| 32 | 0 | 25,909 |
| 33 | 1 | 25 |
| 34 | 2 | 512 |
| 35 | 3 | 59 |
| 37 | 5 | 1 |
| 38 | 6 | 22 |
| 48 | 16 | 2,029 |

The latter28,557 lose bit0x20. Changed members comprise10,734 fields and17,825
methods. All class/member descriptors, partitions/access and within-class flag
ordering match. Both files have6,882 explicit and999 absent class flag records;
99,178 members have numeric records and one belongs to an absent record. Absence
is preserved as an explicit absence marker/raw=null, never assigned7 or0 and
never given guessed runtime semantics.

A second, direct raw-section comparison corroborates those results: both sections
are130,706 bytes, their size/class-offset prefix is byte-identical, all99,178
stored flags are single-byte ULEBs and exactly28,559 data bytes differ with the
same transitions. The complete descriptor change list remains ignored; only
bounded counts/examples and evidence pins belong in the authored inventory.

## Concrete causes and exact field evidence

AsyncPlayer.mDebug is static access26, partition index2. Original encoded-array
count3 contains the third entry byte0x1f: typed boolean31/false. Output count2
omits that entry. Its raw hidden flag3, access and type remain unchanged. This
is actual explicit-versus-absent metadata loss. An effective type-default
explanation is not the requested exact metadata/inverse contract.

Installed ClassPool delegates to StaticInitializerUtil, which finds the last
initializer that is nonnull and not an EncodedValueUtils default. Its explicit
default tail trimming explains the fifteen losses. The normalizer deliberately
retains typed values versus absence; weakening that comparison is not a fix.

Hidden-API loss begins at the installed reader's enum projection. Its getAllFlags
masks base values with7 and enumerates only domain8/16, discarding0x20. Its method
accessor special-cases raw7 into an empty set. The writer subsequently combines
only the represented enum values and writes blank entries as WHITELIST. The
raw7->0 changes affect PowerManager.isLightDeviceIdleMode and Process.setArgV0;
code/parameter/annotation portions of their normalized records match. The other
28,557 numeric losses are invisible to that normalized enum comparison.

API29 is the correct existing emission gate: actual writer bytecode requires
hasHiddenApiRestrictions and api>=29. It does not upgrade this older enum model.
The pinned immutable AOSP header has four value bits, SDK0, MaxTargetS7 and
higher domain bits. It is a mechanism reference, not an assigned Samsung ART
revision. Exact numeric preservation is required regardless of human labels;
none of these policy changes is accepted as equivalent.

## Boundary and next proof

The failed receipt/logs and compiled source/tool pins are retained. Reviewed
current report/tool snapshots are separately preserved under this review's own
ignored failure-input-snapshot. Raw javap metadata stays in ignored firmware;
independent scripts and derived checks stay in ignored out. Shared source reader
and normalizer are unchanged. No success or edited inverse is claimed.

A separately authorized successor must preserve explicit initial-value presence,
all107,060 normalized records and **every raw numeric flag plus class-record
absence/order**, then prove its repaired second emission byte-identical. Merely
fixing the seventeen visible rows still misses domain-bit loss. Whole-section
raw preservation is admissible only with exact no-edit class/member/order,
presence, header and extent checks. It does not authorize future helper insertion
or changed member mappings; those need a separately reviewed rebuild design.

This review freezes only the rejected initial attempt and its diagnosis. No
successor writer/normalizer change is reviewed or approved here. No selected boot
framework, complete cohort/ART linkage, native/resources/caller/user/policy/state
owner, PIN/fingerprint/key/CE operation or device case is established.
