# Retained view app-preparation review

Both the pre-use source review and the independent saved-output review pass. Root's actual data-only preparation `ecf3af` ended 0 and emitted `firmware/retained-view-app/receipt.json`, SHA256 `ac18addc37c2c9348fad157b216f27eba302b3c5e952af95624e5bbce259c49b`. The producer was not imported or invoked by this reviewer; no shell, compiler or target was replayed.

The exact producer is `tools/prepare_retained_view_app.py`, SHA256 `032ebf7c6252a5b061664f5d6fb2bc7f1a4c54ea2a969743ceb5037ba3dea018`. Its fixed fresh source destination, captured ECD44 predecessor, ordered fixed-FD patches, bounded path/write checks and explicit partial/default-off scope passed source review. The source-phase proof and normal cards remain preserved independently.

The actual review rehashed 95 file paths twice. All 34 original inputs, 33 source snapshots and the complete 59-file destination match the saved map: 13 overlay files, three mirrors, two v1 references, five full-byte inverses and other provenance files. The two ordered patches reproduce their recorded phase hashes and invert as a whole. The generated integration patch reproduces all five changed outputs and exactly restores them; eight other predecessor overlay files remain unchanged.

Relative to ECD44, the only Gradle delta is the native hash/size metadata. It matches the actual 659,336-byte `ba532858...` source-built artifact; the emitted V2 Command also matches the actual compiled SDK source hash. The native ELF remains under out and was not emitted into firmware. Existing opt-in remains default off, and source mirrors/v1 references are provenance rather than extra packaged runtime inputs.

The immutable actual proof is `out/retained-view-app-review/actual/ACTUAL-OUTPUT-CHECK.json`, SHA256 `938806032ba9bd891bfc894835b9ece6f6d11721c8186f6e65d10a3e102abda4`. An initial reviewer metadata reader refused Windows-separated predecessor paths and used an eager fallback lookup; only that reader was corrected. No subject source or output changed. Isolated pure byte-parser definitions were used for comparison, never a producer main/build/prepare path.

This remains source-only partial preparation: no full checkout/Gradle/APK or installation proof, no app VIEW operation, writer guard or host-view SDK integration. The v1 Command and Kotlin/shell composition are not new compiler results from this preparation. Android/native/security acceptance and all physical outcomes remain separate.
