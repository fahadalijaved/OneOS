# Independent closed parent-hook header-preserver review

**PASS for source-only preparation of the fixed header-preservation API.**
The reviewer read `tools/preserve_guest_metrics_parent_headers.py`, SHA256
`ac9537fc8485a49b50da159577085537fe4cacb92ecb258496314be17cd22bbf`,
before any new OEM output repair by this component. No concrete defect was
found within its declared header-only scope. The reviewer did not invoke the
helper, its fixtures, a writer/compiler or Android/OEM/device code.

The API accepts only original bytes, emitted bytes and their exact explicit
SHA256; the source hash/size are literal c9a84/10,042,704. It provides no caller
profile or waiver seam. The reused parser/seal dependency is pinned to94397788…
and stays unchanged. Exact original declared/coded counts and identities,
flags, partitions, code/debug presence and class identities are guarded.

Only the three literal edited hook headers and one new virtual dispatch are
admitted. All other original non-outs header fields remain exact. The new
dispatch must be flags0, virtual, coded and debug0, with the literal6/5/6/0/11
tuple after repair. The total frontier is46,865 declared /45,060 coded methods.

A complete shared-output-word plan precedes buffer mutation. Conflicting
desired outs values refuse admission. Actual mutation is only uint16 outs
words, followed by integrity resealing; the complete changed-byte whitelist,
same-size check, reparse and repeated fixed-profile check follow. Caller
hashes identify supplied bytes and do not attest producer authority.

This verdict accepts neither the three-hook instructions nor complete DEX
metadata. The helper's explicit exclusions are material: it checks debug
**presence**, not raw headers/events/END cursor; it does not validate field
insertion, class/member order, references, instruction mappings, catch behavior
or source code-group preservation. Parent producers and independent output
reviewers must check those separately after every emission/re-emission.

The new raw-debug baseline review independently measures c9a84→620bc and finds
all raw facts equal. Its original terminal cursors for onStart, phase and
parent onTransact are54,276,25, respectively, before code ends57,277,27.
That baseline result is not future edited-output debug relocation acceptance.
An edited output must preserve each exact mapped terminal cursor as well as
headers, parameters, locals and line/source/prologue/epilogue events.

The producer's17 reported focused checks were read as authored record/byte
fixtures, not independently rerun or represented as an actual emitted artifact.
Any literal hook/body/profile change requires a new source review. No runtime
readiness, source/epoch lifetime, retirement, native security authority, phone
launch or emission beyond the root-authorized finite attempt follows.
