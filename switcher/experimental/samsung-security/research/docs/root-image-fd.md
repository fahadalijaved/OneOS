# Explicit image/bootstrap descriptor exports

`compat/handoff-view/root-image-fd.patch` prepares a bounded fix without editing
the held v1/v2 sources or their builds. It targets both authored image commands
and both held base/derived RootScript private bootstrap child calls. It does not
change filenames, image pins, flags, permissions, Binder admission or native
verification behavior.

Root's approved read-only phone probe executed the actual `/system/bin/sh`:
standalone `exec 3</proc/version` followed by an external cat of
`/proc/self/fd/3` exited 1. Adding `3<&3` to that external invocation exited 0.
The raw commands/results remain under ignored
`firmware/read-only-resume-20261106/shell_fd_*`. This confirms the saved mksh
manual's distinction between permanent shell-private redirections and explicit
descriptor propagation. It is not native-helper execution or a root-session test.

Both commands keep the same opened image in descriptor 3. Their three external
`stat` calls, external SHA-256 call and final native `exec` now each explicitly
export `3<&3`. Fixing only the final exec would leave metadata/hash checks unable
to resolve their own process's `/proc/self/fd/3`. The native's same-image fd3
check remains mandatory; no reopened pathname or unverified image substitutes.

The private bootstrap resolves its child script through the retained bin anchor
in descriptor 4. Its child shell invocation now adds `4<&4`, while preserving the
existing close-only-owned-child-copies operations on descriptors 3, 5 and 6.
That does not occupy the installer's reserved 5–9 slots. The patch includes
separate exact hunks for held base RootScript (`49cf71f6…`) and generated v2
overlay (`8eeacd4b…`). Applying a hunk changes that source's identity; its old
generator receipt does not cover the corrected bytes. The explicit overlay hunk
closes that child edge without assuming regeneration.

Exact preimages and derived afterimages are recorded in
`out/root-image-fd/source-records.json`. Authored Java snapshots stay in out;
whole third-party Kotlin snapshots stay in ignored `firmware/root-image-fd/`.
The normal source files remain byte-identical to their preimages. Static inverse
checks remove only the explicit exports and reproduce those preimages.

This patch does not close the whole installation pipeline. Other external
metadata/hash/path operations through private bootstrap and installer descriptors
3–9 require the separately assigned installer patch. Composition, fresh emitted
command/SDK/Kotlin checks and actual native lifetime remain separate. The source
author ran no phone, shell/helper, compiler/model or native workflow. Cooperative
writer exclusion remains paused and incomplete; no readiness, security or guest
authority follows from exporting a descriptor.
