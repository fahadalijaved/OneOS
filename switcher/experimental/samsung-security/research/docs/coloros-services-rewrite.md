# Strict no-edit ColorOS services DEX baseline

**FAILED strict no-edit attempt; output rejected.** The single source-reviewed
attempt ended exit1 on the raw code-header comparison. This is the complete captured original `classes2.dex`,
not hooks, helper insertion, retirement wiring, a JAR or a runnable cohort.

Input services.jar SHA256 is
`66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3`.
Selected DEX SHA256 is
`c9a84cebd3bc22a48c0737a7de34d96ba0b97a6294d4bdd97c935543e605659f`,
10,042,704 bytes, ordinary039/header112/logical offset0. No slicing/rebasing is
permitted. Input pool facts come from the
[original parent preflight](guest-metrics-parent-payload-preflight.md).

`python -B tools/probe_coloros_services_dex.py` will compile only authored static
tools against the existing pinned dexlib. It imports the literal-pinned
`c189f70c…` initializer adapter source, verified against the `f9ef37dd…` writer
profile, and unchanged `2dc5cdbb…` normalizer / `9ee6f287…` reader. The adapter
retains every explicitly encoded initializer prefix, including false/null tails,
and rejects gaps. It does not rewrite normalizer semantics or modify a global
library. Nothing is added to the OEM DEX. Writer API29 enables correct metadata
capability; it does not grant runtime compatibility.

All original classes, field/method partitions/access, parameter/debug/try/code
records, annotations and typed explicit initial values must compare exactly
through emit→decode and second emit→decode. Original/decoded/roundtrip normalized
bodies remain ignored firmware; generated classes/DEX/logs remain ignored out.
The second emitted DEX must be byte-identical to the first. Input/output integrity
and map structure are checked. No raw HAPI map item exists in this selected
source, and all three representations must retain that absence: no raw repair,
flag normalization, synthetic defaults or Samsung-section transplant.

A separate Python raw parser checks full class/member order/access and complete
string/type/prototype/field-reference/method-reference lists, not only used code
references or dexlib enum labels. Per-method source/output code-offset partitions
are saved. Raw per-method registers_size, ins_size, outs_size, tries_size and
insns_size must also match exactly; debug offset locations may move while the
normalized debug events remain exact. Root permits only splitting existing shared code-item groups into
independently identical items; merging distinct source groups is refused. The
code-item map count delta must exactly equal the additional unique offsets. All
other map type/count differences stop for concrete review. Physical offsets and
permitted alias splitting are representation changes, not physical source-byte
reproduction. Unknown metadata or unexpected deltas are not silently waived.

The command boundary is the pinned sanitized helper: all five JVM/compiler
environment variables stripped case-insensitively, unique own cwd, local
TMP/TEMP/JVM home/temp, empty application native path, streaming 2MiB command
output cap. The writer has a 180-second wall limit and 4GiB heap; selected ZIP
entry reading is bounded and normalized files have a 512MiB publication bound.
Failure publishes a distinct actual failed receipt and stops without auto-fix.
Source/tool/input pins are checked before/after.

No OEM class, Android/ART, JNI, service or phone runs. A successful baseline would
be an immutable target for a later separately approved symbolic inverse; it does
not approve the three source hooks, added members, helper placement, lifecycle,
native ownership, Context construction or full security goal.

## Actual failed evidence

Authoritative receipt:
`out/coloros-services-rewrite/20261106T000303598099Z-e592ea319eb3485a9cdffef5144e4c89/receipt.json`,
SHA256 `35702f1f4d308d7001b40cb47ec78e4b2c2da7c4668f4517e16e17e70c9c9949`.
Actual exec session72047 ended1. Source and tool pins remained unchanged; executed
Java/wrapper snapshots are in that run's `executed-source/` directory. No second
attempt, repair, preservation waiver or automatic fix was made.

All76,707 normalized records matched across three 181,484,460-byte raw files,
SHA256 `1c2607a7116a0d0e003b2f78bddddff1f540f908f5ed37cb9ae99853e2761d0c`.
Both emitted files are 10,061,988 bytes, SHA256
`7c1f21be5a088181d2b97df1e2a742930621afa91ece1d680f992886aab4bba3`.
Those Java subchecks passing do **not** override the wrapper's strict failure.

Independent raw identity comparison found **233 changed per-method headers**,
all solely `outs_size`; all other compared identity lists and header fields were
equal. First: `CallMetadataSyncConnectionService$CallMetadataSyncConnectionIdentifier.hashCode()I`
changes outs2→1 with registers3/in1/tries0/17code units unchanged. Full source and
decoded raw headers remain under ignored firmware. The bounded derived
`strict-header-differences.json` in the run directory has SHA256
`9638404b22f839b43630484f92eab26d7c686edc988bcba35daf0da68da7e533`.
This is a representation mismatch, not permission to normalize outgoing capacity.

Source has45,059 code-bearing methods/44,520 unique offsets; first output has45,059
unique offsets. The later split-only/map-count acceptance guards were **not
reached** because raw header equality failed first; no claim is made that all
remaining topology gates passed. No immutable inverse baseline is accepted.
