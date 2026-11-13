# Installer descriptor inheritance patch

Root's read-only Android mksh probe found that an implicitly opened FD3 is absent
from an external utility's `/proc/self/fd/3`, while explicit `3<&3` preserves it.
The existing MSYS installer models did not establish Android FD inheritance.

`compat/handoff-view/root-installer-fd.patch` is source data only. It patches the
normal fixed installer handler, its embedded v1 and saved v2 copies, and both
base/derived RootScript bootstrap metadata blocks. Exact preimages/composed
sources are recorded in `out/root-installer-fd/SOURCE-PATCH.json`; static forward
and inverse checks reproduce all five targets. No core, clone, generated receipt,
installer or phone state was changed or executed by this preparation.

Each external utility that resolves a held proc-FD path explicitly exports the
known descriptor at that invocation. Stage/bin/target checks use fixed FD8/9/7;
private payload paths use FD5; payload metadata/hash uses writable FD6. Link
publication exports FD5 and FD9 together. The existing one-shot cleanup uses FD5
for payload removal and FD9 for removing the owned work directory, before closing
those anchors. Fixed installer-local hash helpers export FD6/7 at `sha256sum`
itself, preserving the existing SHA-256/cut algorithm without depending on a
shell-function redirection reaching its pipeline child. No global legacy hash
helper is changed.

Bootstrap fixed FD3/4/5 profile helpers replace proc-FD arguments to the generic
pathname helper. Stat/hash/head and mkdir/rm/rmdir export the exact bootstrap
anchor they use. The separate ColorOS patch owns the script-child `4<&4` export;
this patch excludes that hunk. The paired ColorOS `root-image-fd.patch` successor
adds it for both base and derived RootScript. Independent review explicitly
composed both patches across seven unique source targets.

No caller-selected FD number, environment token, repair path, overwrite fallback
or changed ownership policy is introduced. Length/hash/inode checks, regular
nonlink/no-clobber publication, occupied-slot refusal and cleanup disposition
remain. This patch has no new workflow or Android acceptance result. Historical
installer receipts remain unchanged and do not validate these new source bytes.

Independent combined source review passed: `out/root-fd-review/trust/SOURCE-PASS.json`
(SHA-256 `76ec673eefbb030a9a053f0a60a2a6779d1f48117cc4957f7b5a99a8485b3c9f`). This is source review, not
installer, shell, compiler or device execution.
