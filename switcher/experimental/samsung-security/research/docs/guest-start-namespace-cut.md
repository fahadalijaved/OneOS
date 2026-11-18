# Guest startup namespace cut: disabled source-only output

**One disabled candidate emitted; preservation checks pass. No script executed.** This derivative removes
three incompatible startup regions from the exact installed OneOS0.4.57
`guest_start.sh` (78054 bytes, SHA256
`896b72cc5bafadf975e29c05da0280e92b56a8f508c378d2c24e25a2b7f30446`).
Root confirmed these three ranges and authorized the narrow implementation.
Independent source review preceded root's separate one-PC-emission decision.
The result remains unselected, nonbootable and runtime-unwired.
No shell, mount, chroot, native/OEM code or phone action ran.

The assumed future entry is a real supervisor-owned guest child already rooted
and cwd-reset inside the admitted ColorOS root, with its native sibling and
actual data/mirror peers retained. This is an external ownership requirement,
not a caller assertion that this script can verify. No environment variable,
FD, PID, path, token or ready boolean can admit a launch through this leaf.

## Four exact edits

Offsets are half-open coordinates of the original bytes. The complete source
span and replacement hashes are in
`out/guest-start-namespace-cut/source-api-proposal.json`, SHA256
`80c15e7d40cc28c64669e3be81752172018b73fe37b5f6f93f6dca89b6423ac4`.

| Original range | Exact change and reason |
| --- | --- |
| `[17,17)` after shebang | Insert an unconditional source-only diagnostic and `exit 2` before any original body. No runtime bypass or success result. |
| lines11–21, `[468,852)` | Replace the entire old root-transition block with comments: staged-root `cd`, late recursive-private, both `pivot_root` attempts and fallback self-bind. These would replace or sever the common ancestor already owned by the future native supervisor. |
| lines40–49, `[1891,2425)` | Replace old-pivot `/postinstall` lazy detach and its pivot-specific failure/readback with comments. This leaf supplies no namespace-wide pivot or old-root mount; retaining that cleanup would operate on a topology this entry no longer creates. |
| lines76–85, `[3750,4494)` | Replace the duplicate `/data/data` bind, `/data_mirror` tmpfs, recursive mode change, null/user0/profile scaffolding and mirror rebinds with comments. The native owner supplies its actual data alias and fresh shared mirror peer before root separation; overwriting them here would invalidate that custody. |

The fence bytes are:

```sh
# SOURCE-ONLY: native custody and per-process root entry remain unassembled.
printf '%s\n' 'SOURCE_ONLY_GUEST_NAMESPACE_OWNER_UNBOUND' >&2
exit 2
```

This is intentionally nonbootable text, not a successful replacement for a
namespace operation. The three removed bodies become comments only behind the
fence. No `true`, fabricated validation or shell implementation substitutes for
native fork/chroot/exec custody.

All other bytes remain exact. In particular, preserve the BusyBox lookup and
missing-executable refusal1–9, `/proc/sysrq-trigger` protection/failure31–39,
`/mnt`/storage detach and guarded rebuilding53–74, later rescue/data/user and
native launch paths. Root explicitly limited “detach” to old-pivot postinstall;
the separate guarded storage work is not silently removed. These preserved
bodies remain unreachable in the disabled candidate. Their presence is not
acceptance of their transitive effects, background jobs or required consumers.

## Actual supporting source and remaining owners

The frozen common-ancestor proof (`7f5bfa1e…`) distinguishes per-process chroot
from namespace-wide pivot and identifies late recursive-private and mirror
replacement as incompatible. Reviewed native owner source `1026094b…` performs
private-before-bind setup, prepares fresh data/mirror peer groups, creates the
actual legacy data alias after both data peers exist and validates peer objects.
The fixed input adopter `5e645e05…` retains actual staged objects, and supervisor
contract `7d628609…` retains private ownership. Their exact pins are in the
proposal. They have no implemented root-separated guest exec/provider handoff;
PC compilation is not live mount propagation or native-service acceptance.

Actual C fork/root separation, chroot/cwd and outside-root descriptor closure,
exec/provider lifetime, selected code/native profile, peer propagation and
teardown remain required. Storage/UUID/CE/FBE, later native/background writers,
properties/global controls and rescue/hardware consumers remain separate
required owners. This cut does not add stock-equivalence, enforcing SELinux or
privapp-enforce gates; the accepted existing OneOS limits remain the baseline.

## Producer and composition API

`tools/prepare_guest_start_namespace_cut.py` uses Python byte operations
only. Default/`--plan` validates literal inputs/proposal/dependency hashes and
writes report-only metadata to a unique ignored output directory, without
publishing the normal inventory. It does not apply transformations.
`--emit <PC-review-gate.json>` requires exact tool/proposal hashes and pinned
independent `SOURCE_PASS` plus root `ONE_PC_EMIT_GO` documents. All input,
dependency and gate bytes are rechecked before successful publication.
The PC gate is not a runtime permission, readiness or provenance API.
The exact gate schema is `guest-start-namespace-cut-review/v1`, with fields
`sourceToolSha256`, `sourcePlanSha256`, `sourceReview` and `rootDecision`.
Each reference has only `path` and `sha256`; both JSON documents must carry
their required status and the same exact tool/plan hashes. Plan means the
literal approved proposal80c15e7d, not a new serialization-dependent hash.

A gated emission creates only one `guest_start.sh.candidate.sh.disabled`,
one unified diff and a receipt. It verifies original span hashes, four disjoint
edits, exact expected candidate bytes, every unedited gap, and the entry fence.
Inverse must consume the actual saved candidate, restore only its mapped edited
spans and reproduce the original896b72 bytes; reapplying must equal the saved
candidate. Off-target-byte mutation and a changed fence `exit 0` with a truthful
but untrusted recomputed candidate hash must reject. No scripts or shell parser
will execute. Successful emission alone may publish the output inventory.

The prior property cohort `41019f1c…` is immutable. Both leaves derive from the
same original896b72 source. Its seven setter edits lie outside the three removed
intervals. The sole overlap is their distinct zero-width entry insertions at17.
A future separately reviewed composer must apply a source-coordinate union,
placing this namespace fence first and the existing property fence second,
retaining each exact byte sequence once. No offset-based patch of the already
edited candidate, fence deletion or whole-output compatibility is authorized.
No composer or combined candidate is produced here. Namespace-only output still
contains original property operations behind its fence and cannot be selected
alone; property/clock composition and all real owners remain prerequisites.

## Actual preparation result

The source/API proposal and original report/inventory are preserved before
amendment under `out/guest-start-namespace-cut/history/source-api-before-implementation/`
(history manifest `dd076161…`). The initial prepared producer was exact tool
`58ba8c74c20df8f024d81bafb41efa6fc661044fbee28cd4348717bc0202e917`.
Its first authorized metadata-only plan stopped during strict proposal-path
resolution with `PermissionError [WinError 5]`, before work-directory creation,
forward transformation, candidate writing, inverse or negatives. The surrounding
PowerShell command continued to its post-hash checks and returned0; the Python
exit code was not separately saved. Those before/after hashes prove the tool
and normal inventory remained unchanged. The exception is not a transform result.

`out/guest-start-namespace-cut/plan-path-resolution-failure.json` (`8cdfebee…`)
records that exact boundary; executed source/proposal snapshots are preserved.
No retry or containment-check waiver occurred. The filesystem failure's cause
is unassigned. This source can be reviewed without claiming a successful plan,
emission or runtime. Root owns any later read-only diagnosis and renewed gate.

Independent static review withheld initial58ba source clearance for two concrete
provenance gaps (findings `489fea70…`): the proposal's second pin could differ
from the already validated80c bytes, and duplicate normalized gate-role paths
could replace an earlier retained hash. Root authorized only these corrections.
Beforeimages are preserved under
`history/source-58ba-before-provenance-correction/` (manifest `9c7f6c4d…`).

Corrected tool `31783aaf28653bcdcb2d7ab6e91ab1c39195924c8b182ee0ced18697d5a9d955`
requires the proposal reread hash to equal its already admitted hash before
retaining that pin. Gate, source-review and root-decision paths are resolved
canonically; case-insensitive duplicate role paths refuse before map insertion.
Final checks reuse those canonical paths and exact retained hashes. Literal
cuts, fence, source inputs and composition contract are unchanged. This
successor had not run a plan, producer, negative or script at source freeze34427c80.
Source delta review and a separate root emission decision followed. The initial
filesystem failure is not attributed to or resolved by these provenance fixes.

## Actual offline emission and saved result

Independent corrected-source clearance is the immutable source-pass `b0b5c471…`;
the separate root decision `e9697b03…` and gate `50be9e41…` bind tool31783aaf and
approved plan80c15e7d. Root directly executed exactly one emission and reported
terminal exit0. Actual receipt
`out/guest-start-namespace-cut/20261106T094045555832Z-06595f2bae184bfd9bb57d6330c8bb44/receipt.json`,
SHA256 `83935c2560720abace97d5183f7b203a4d84fe20133ec236c72fac82b22912db`,
records `PASS_SOURCE_ONLY_DISABLED_NAMESPACE_CUT`.

The saved disabled candidate is77000 bytes, SHA256
`cdca47a04a59dbb49e586bf49dda463e3dba881b37d6fcf05b4c09046fa6a9d2`.
The receipt records all four mappings, unchanged gaps, saved-candidate inverse
to original896b72 and reapply equality, the two rejected candidate mutations,
and unchanged source/tool/proposal/dependency/review inputs. The3447-byte diff
has SHA256 `9a6c6fbbed8ff0083e121eb8987aebedc2c129f2ee9e9543a341031f1a766ff1`.
The author read only those saved bytes/hash/entry shape and receipt results
(`saved-output-readback.json`, `d1154f38…`), without replaying producer, inverse,
negatives or scripts. Independent saved-output review is peer-owned separately.

The post-emission source-phase history2677cda4 preserves unchanged source3178,
reportb59c, sourcefreeze3442 and source-pass bytes before this report amendment.
The producer had already replaced the normal source-only inventory7a45 with
published output inventory8b69. The latter is copied intact. The former was
reconstructed after emission from the actual prior2724 snapshot plus recorded
correction metadata and verified against its frozen7a45 hash. It is explicitly
identified as reconstructed, not a claimed pre-emission copy. Earlier58ba,
withheld review, path failure and proposal histories remain intact.

This is text preparation only: no shell parse/run, namespace/mount/chroot,
native/OEM execution, phone action or real startup took place. Neither this
cut nor existing compiled helpers establishes future launch custody, storage,
property composition, full propagation/teardown or a bootable cohort. The
unconditional fence remains in the emitted artifact; property28f/4101 remains
unchanged and no combined candidate is emitted.

## Historical native dependency profile

The actual8393 emission binds the original v1 native dependency hashes below.
Concurrent v2 work later changed normal `compat/native` paths. The first final
author manifest7bff incorrectly captured intermediate v2 owner source/header
rows while retaining the actual v1 receipt. That manifest/report/inventory are
preserved in `history/output-7bff-before-native-profile-correction/` (manifest
`dde5382c…`). This is a metadata pinning error; it does not change the saved
candidate, diff, tool, source cuts, gate or receipt.

The corrected delivery manifest references these exact immutable pre-v2
snapshots, verified against the original receipt's complete length/hash pins:

| Original receipt dependency | Immutable snapshot under `out/guest-private-image-preparation/history/pre-v2-source/compat/native/` | SHA256 prefix |
| --- | --- | --- |
| `compat/native/guest_private_view_owner.c` | `guest_private_view_owner.c` | `1026094b` |
| `compat/native/guest_private_view_owner.h` | `guest_private_view_owner.h` | `463b79db` |
| `compat/native/guest_private_view_inputs.c` | `guest_private_view_inputs.c` | `5e645e05` |
| `compat/native/guest_private_view_inputs.h` | `guest_private_view_inputs.h` | `68a7b302` |

The same pre-v2 snapshot also supplies the three associated historical
inventory files under its `inventory/` directory: `guest-private-view-owner.json`
(`1899a44e…`), `guest-private-view-inputs.json` (`7df6a3d1…`) and
`guest-private-view-supervisor.json` (`7d628609…`). Their complete pins also match
actual8393. The metadata correction refused to absorb a changed normal input
inventory during its final rehash, then selected these exact historical report
bytes. All seven original receipt paths are mapped explicitly; no moving v2
source or report is silently adopted.

These files were preserved by the separate pre-v2 stream; this report does not
claim they were copied before namespace emission. Original source/proposal/gate
records are historical and unchanged. The mapping is explicit in the author
inventory and delivery manifest; current normal native/profile paths are excluded from
delivery pins. **Current native v2 source, ABI, launch assembly and compatibility
are not covered by this v1-only namespace leaf.** Neither historical byte
equivalence nor the text cut admits a new runtime cohort. The successor performs
metadata correction only, with no producer, tests, inverse or script replay.
