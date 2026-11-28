# Corrected partial app overlay for the private-view controller

Status: actual source preparation PASS, partial app overlay only. `tools/prepare_retained_view_app.py` prepares
a fresh ignored `firmware/retained-view-app/` tree. It never modifies the held
OneOS clone, ECD44 overlay, canonical Java/C, prior receipts or compiled artifacts.
No worker ran the producer, compiler, root script, native controller or device.

The real app path already exists: the optional `oneos.retainedHandoffFile` property
selects a byte-checked generated full-only `root/oneos_retained_root_handoff` asset;
the existing BuildConfig pins feed the typed setup and fixed
`install-handoff-controller` verb; the actual command verifies the same opened
image before `--host-control-v2`. The native view build preserves that entry.
Thus the new build identity can use this path without inventing a new installer,
filename selector, launcher or application control API. Absence of the property
still disables the v2 service and emits empty/zero v2 pins.

The exact accepted source inputs are:

- Saved ECD44 preparation receipt and its twelve inputs/twelve outputs:
  `firmware/handoff-app-integration/receipt.json`, SHA-256
  `ecd44cdf79b4d735e6b17d7eff873afa23d3a685123a4db0795d797bae1696a5`.
- Image FD patch `compat/handoff-view/root-image-fd.patch`, SHA-256
  `3cbb489584cd95a5835ca8ee72bde909fffb98bb7c5262ea5bf336670e2e25d2`,
  followed by installer FD patch `compat/handoff-view/root-installer-fd.patch`,
  SHA-256 `814747af7d1e346444cdd114e736769ef25f1cea7fe3417b8b3e98b73a7df8cc`.
  Independent source review: `out/root-fd-review/trust/SOURCE-PASS.json`, SHA-256
  `76ec673eefbb030a9a053f0a60a2a6779d1f48117cc4957f7b5a99a8485b3c9f`.
- Actual new native/SDK receipt
  `out/retained-root-view-build/r-8ecb3ffb/receipt.json`, SHA-256
  `2b1504c74123b9f8392025d2b790316f49e3710a4936106fc677d9ea7cc14571`.
  Its existing `oneos_retained_root_view` artifact is 659,336 bytes, SHA-256
  `ba532858bfbe2aae07db41e88953bfe68519d0e12d40be916ba324bd4d342c89`.

The producer retains and checks the exact preimages before transforming. Its
bounded patch reader checks every target, hunk count, position and context while
preserving each file's LF/CRLF bytes. It applies image-first/installer-second,
checks each inverse, then reverses the entire composition in the opposite order.
It rechecks the old ECD44 inverses, the actual v1/v2 app command mirrors, and the
v2 command's compiled-source identity from the real SDK receipt. The v1 corrected
command is source-only here; this preparation does not compile it.

The combined app overlay has thirteen files: all twelve saved ECD44 files, plus
the corrected existing v1 command. Four old outputs change: v2 command,
RootScript, the root shell asset, and the two literal v2 native metadata values
inside the existing Gradle file. The other eight old outputs stay byte-exact.
No task, dependency, service, callback, profile, opt-in or runtime operation is
added by this successor. The root script corrections cover both fixed installers.
Different existing installed images are still refused; this does not implement
replacement, orphan reconciliation or migration.

`receipt.json` has schema `retained-view-app-source-preparation/v1`, status
`SOURCE_ONLY_PARTIAL_APP_OVERLAY`, and an `outputs` list of relative
`overlay/app-android/...` paths, sizes and hashes. A future owned build tree can
copy the held full clone and then apply this complete thirteen-file overlay; do
not apply ECD44 again afterward. `mirrors/` contains the two corrected canonical
command counterparts and the standalone installer fragment. `v1-reference/`
contains corrected original v1 RootScript/root-shell source for provenance only;
neither directory is an additional worktree overlay.

Source snapshots, full original-byte inverses and a deterministic source patch
are saved under that new ignored firmware directory. The producer opens the
actual native artifact for identity verification but never copies an ELF into
firmware; generated binaries remain in their existing ignored `out/` location.
Every input and saved output is reopened before receipt publication. A preexisting
destination, changed input or failed transform refuses without overwrite, repair,
fallback or automatic retry. Default invocation prints plan metadata only; Root
ran `python -B tools/prepare_retained_view_app.py --prepare` once after source review.

This is deliberately partial packaging. The app has no selected VIEW_PREPARE
operation. The separate `root-view-writer.patch` is not applied by this producer;
the real writer lease/negative marker, actual prepared inputs, host request route
and runtime admission remain unassembled. Packaging a controller which contains
the native view implementation does not close those requirements or authorize a
view attempt. Native build evidence is API31/static PIE with a 4-KiB profile,
not 16-KiB compatibility or execution, mount, Android, guest or security acceptance.

The actual Root-authored preparation attempt ended zero. Receipt
`firmware/retained-view-app/receipt.json`, SHA-256
`ac18addc37c2c9348fad157b216f27eba302b3c5e952af95624e5bbce259c49b`,
records 34 inputs, 33 source/data snapshots (the ELF stays in `out/`), thirteen
combined overlay files, three mirrors, two v1 references, five original-byte
inverses and 58 saved files plus the receipt. Both ordered patch phases and the
whole reverse are exact; the saved Gradle file differs only in its two selected
native identity literals. The producer remains SHA-256
`032ebf7c6252a5b061664f5d6fb2bc7f1a4c54ea2a969743ceb5037ba3dea018`.

Independent saved-output proof:
`out/retained-view-app-review/actual/ACTUAL-OUTPUT-CHECK.json`, SHA-256
`938806032ba9bd891bfc894835b9ece6f6d11721c8186f6e65d10a3e102abda4`.
It independently verifies the complete 59-file output closure, ordered patch and
whole-source inverses, unchanged ECD44 outputs, actual SDK correspondence and
partial/default-off limits without replaying the producer. Earlier source-only
cards are preserved in
`out/retained-view-app-preparation/history/source-phase-before-actual/`.
No app, compiler, shell script, native controller, original runtime or device was
executed by this preparation or its saved-output review. The new overlay still
needs its own actual full APK build and later explicitly selected runtime work.
