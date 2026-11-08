# Disabled guest_start composition for OneOS 0.4.58

One independently reviewed, disabled source-only artifact was emitted by root.
The actual static command exited 0; all eleven focused refusal cases passed.
Independent saved-byte review also passed. No source script, shell parser,
native helper, OEM code, Android process or phone action was executed. The
separate 0.4.57 candidate, producer, normal reports and receipts remain unchanged.
Root authorized this static operation after source review without another root gate.

The exact public input is `guest_start.sh` from upstream commit
`45abb3df03cbd4a8b006519baaebefdb2c68658a`, 78563 bytes, SHA256
`81460c5f089a21d9684ae9023af9938392621c8296a093ec8045fac5c81482c2`.
The new `tools/prepare_guest_start_composition_058.py` is independent of the old
producer at execution: it reads its pinned source as provenance but never
imports or runs it. `out/guest-start-composition-058/PLAN.json` pins the new
source, upstream index/freeze and static delta, old reviewed eleven-edit plan,
actual old candidate/receipt, component candidates and historical native inputs.

The whole new source must equal the old 78054-byte source with only the original
509-byte GNSS diagnostic inserted at byte 72411, hash
`e9b20fb12f9c187ece250554f51c70e019026d2698ada4af7d4c8bc088e09144`.
All eleven source ranges and exact replacement records must equal the frozen
old plan. Those cuts end before the insertion; their candidate coordinates also
remain unchanged. The saved disabled output is exactly 77679 bytes; inverse and deterministic
reapply byte files were also saved and checked.

| Source half-open range | Exact unchanged edit semantics |
| --- | --- |
| `[17,17)` | One 197-byte property refusal function and unconditional entry call |
| `[468,852)` | Omit staged cd/late-private/pivot block with authored comments |
| `[1891,2425)` | Omit old-pivot postinstall cleanup with authored comments |
| `[3750,4494)` | Omit duplicate data alias/mirror replacement with authored comments |
| `[10193,10200)`, `[11796,11803)`, `[13208,13215)`, `[34403,34410)`, `[52539,52546)`, `[70641,70648)`, `[72011,72018)` | Replace only original property/control token with exact refusal word |

The shared fence hash is
`25e206db59319cd25177e667471aedb7736fa684d85364a66612d11a42253a5a`.
Its unconditional `exit 2` path has no environment, path, FD, PID or ready bypass.
The redundant old namespace entry fence stays omitted. Seven token edits retain
original command arguments/operators. The deferred child-shell occurrence is
still not a live carrier; the entry fence prevents reaching it. Adjacent original
jobs, signals, mounts and native starts remain unassembled and unreachable.

The producer retains bounded, canonical-path-unique, regular-file inputs inside
this nested repository. It snapshots all actual admitted bytes before any
transformation and compares every admitted byte and the tool again before a
successful receipt. Default/`--plan` creates only unique ignored metadata and
snapshots. It does not publish the normal inventory.

`--emit <source-pass.json>` requires an independently supplied JSON record with
`status=SOURCE_PASS`, `sourceToolSha256`, `sourcePlanSha256` and `sourceSha256`
matching this exact producer, plan and new source. This is PC provenance, not
runtime authority. `--self-test <source-pass.json>` supports the same focused
static failures without saving a primary candidate. Emission includes those
failures, so a separate test run is not required.

A successful emission saves disabled candidate, inverse and deterministic
reapply byte files, a unified diff and receipt. Inverse must restore the complete
81460 input; saved reapply must equal the candidate. All twelve gaps must equal
the source, including the GNSS insertion projected to candidate `[71527,72036)`.
The new candidate must also equal the actual old saved composition with only
that original insertion added. No old receipt or inverse is silently repinned.

Focused failures exercise foreign gap bytes, changed fence exit status, duplicate
fence, candidate-side GNSS mutation before inverse restoration, wrong 0.4.57 base,
mutated source GNSS bytes, an unlisted overlapping row, substitution of real
admitted component bytes, input/output path escape and held-input movement.
The output escape calls the actual directory guard before mkdir/write. Mutated
script bytes remain ignored data, never shell commands.

Historical native v1 snapshots explain the old namespace cut's provenance.
Neither current v2 nor current v3 helper inputs are admitted by this script leaf.
The newer v3 filesystem-only resource owner does not supply `/dev/null`, Binder,
property or native sibling endpoints and never executes a guest. The real
preparer still requires init's namespace and its own old rootfs target; host-dev
imports, mirrors, property/global control, endpoint/lifecycle, display/audio,
rescue and accepted native/descendant drain remain separate. The 0.4.58 watchdog,
cache reset/bridge split, property and background/network changes outside this
single script also need their own coherent ownership cuts.

The artifact remains disabled, unselected, nonbootable and runtime-unwired. It
does not modify canonical module/script inputs or select a retained-versus-cold
architecture. The complete required PIN/fingerprint/policy/key/data and return
outcomes remain unchanged.

## Actual saved output and preserved source phase

The sole command was run by root in the nested project:

```text
python -B tools/prepare_guest_start_composition_058.py --emit out/guest-start-composition-058-review/SOURCE-PASS.json
```

Terminal `ecf49d` exited 0 in 0.642 seconds; no retry, worker duplicate or
separate self-test was run. The receipt is
`out/guest-start-composition-058/20261106T144657693926Z-02d9dc76951043e3969f9fc17bb5c386/receipt.json`,
SHA256 `1814450cffefcc109e54735ef105a56d13943587225f8ed862664662f6e93297`.
It records producer
`f68c60b98b5f40fb2ee11c26631d1b752bc09a16bd8e6b7b5db8db50d9373b0b`
and new plan
`ba7d9f752f5b87fafc75047208e3fa13e05b1b952cfe443f655ec77b57919490`.

| Saved byte artifact | Bytes | SHA256 |
| --- | ---: | --- |
| guest_start.058.candidate.sh.disabled | 77679 | 4ae2bc47ecb4198e7cae2379b7844bbd1503b09882db090afecd4c7374bd8abb |
| guest_start.058.inverse.sh.disabled | 78563 | 81460c5f089a21d9684ae9023af9938392621c8296a093ec8045fac5c81482c2 |
| guest_start.058.reapply.sh.disabled | 77679 | 4ae2bc47ecb4198e7cae2379b7844bbd1503b09882db090afecd4c7374bd8abb |

All 31 actual admitted inputs and their pre-transform snapshots matched at final
recheck and author readback. Saved output retains exactly the eleven selected
replacements, twelve original gaps, one unconditional fence and original GNSS
509-byte insertion. Eleven recorded refusal cases passed; the five saved mutated
script/component artifacts and held-input movement fixture are preserved.

The author read saved bytes without invoking the producer, inverse or test
functions again. The separate immutable independent proof is
`out/guest-start-composition-058-review/actual-output-check.json`, SHA256
`1edd46f0c1f622e8023a688eebec62bfd73c78ae10c25339ecdae68929ba5c01`.
It corroborates these complete source/output relations without rerunning the
producer or refusal probes. No moving peer normal report is an input to this card.

The source-phase document/inventory and producer/plan/API/freeze beforeimages
remain exact under `out/guest-start-composition-058/history/source-phase/`,
recorded by HISTORY SHA256
`9403b399f90388e31486ef7816309cfdc4740c476938860aaaa8b2f70bff2a86`.
Old source freeze `d3661c89` still refers to that original phase; its old document
`99c80291` and inventory `e7b0748a` hashes resolve to the saved beforeimages,
not this post-result metadata. Producer/plan bytes are unchanged. A worker's
read-only strict-resolve preflight failed with WinError5 while byte reads worked;
root's minimal same-interpreter preflight and this actual emission succeeded.
That execution-context cause remains unassigned, and no guard was weakened.
