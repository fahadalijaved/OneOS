# Unselected native Settings RPMB ingress leaf

**Built PC artifact only; cold start only; unselected.** This leaf removes one optional Settings RPMB side-operation before its additional fingerprint challenge, HAT request or TEE operation can start through this ingress. It preserves the genuine Settings credential transaction and the rest of its mixed background job. It supplies no Samsung backend, installation candidate, live cleanup or device acceptance.

The authored producer is [build_coloros_settings_rpmb_leaf.py](../tools/build_coloros_settings_rpmb_leaf.py), with hash-only static helper [SettingsRpmbLeafProof.java](../tools/SettingsRpmbLeafProof.java). [The inventory](../inventory/coloros-settings-rpmb-leaf.json) records exact source, output, instruction boundary, immutable reader receipts, all-method proofs, negative fixtures and selection conditions. Generated APK/DEX and fixtures stay under ignored `out/settings-rpmb-leaf/`; raw OEM instruction evidence and hash inventories stay under ignored `firmware/`. No OEM class, JNI, Android service, credential operation or phone command executed.

## Exact source and cut

The sole admitted archive is the original ColorOS Settings APK, SHA256 `33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b`, with 14 ordinary DEX039 entries and 78,960 classes. This is not proof of installed OneOS patched bytes. Its archive is immutable; this producer does not depend on a moving frontend output receipt.

The modified method is `com.oplus.settings.feature.password.LockSaveAndFinishWorker.lambda$saveAndVerifyInBackground$0(Intent):void`, in `classes13.dex`, logical header 0. Its admitted normalized body SHA256 is `ea03a4aa622889842a00924044e9da47e30644f5b7e9ca16d71b49336250b281`.

| Code-unit PCs | Original source | Leaf |
| --- | --- | --- |
| 0–2 | Invoke private `saveScreenLockInRpmb(Intent)` | Three NOPs. |
| 3–10 | Load TAG, load `save_rpmb_success`, call its diagnostic logger | Eight NOPs; skipped RPMB is not logged as success. |
| 11 onward | Original retrieval-capability check, current/old credential selection, optional retrieval storage and modification record | Exact original decoded instructions and bytes. |

This is a 22-byte instruction slice replaced by eleven one-unit NOPs. No method size, register count, access flag, declaration, branch target, try/handler metadata, debug-data offset, reference pool or other payload byte changes outside the admitted slice and DEX integrity fields.

The original method has no try items or payloads. Every branch target remains an instruction boundary outside the removed prefix. Prefix-defined registers 0 and 7 are overwritten before any unchanged-tail read; a bounded control-flow/dataflow check visits 23 states. The tail still calls `isSupportPasswordRetrieve` at PC11, `storeOldPasswordOnModify` at PC43 where originally reached, and `recordScreenLockPassword` at PC48. No policy-false stub is introduced.

## Caller and ownership boundary

Immutable source receipts pin the mixed lambda, the exact private-helper invocation scan, `o0.run()` and the synthetic `LockSaveAndFinishWorker.d(...)` bridge. The full original Settings scan finds exactly one direct invocation of private `saveScreenLockInRpmb`: this lambda at PC0. Its original path is the successful save/verify worker posting `o0`, then `run → d → mixed lambda`. The helper would create the extra RPMB controller/challenge callback, acquire a challenge and HAT, and invoke optional TEE storage. The leaf removes that ingress, rather than replacing a TEE result or callback with success.

This invocation closure is bounded to explicit original Settings DEX references. Reflection, dynamically loaded code and other archives are not claimed absent. Other RPMB/RoR or old-password paths are not removed by this leaf.

**Preserved exact bytes:** real `setLockCredential` at save-worker PC60, post-commit `verifyCredential` PC118, credential removal PC262, native enrollment/handle/HAT paths, all other Settings methods and all other archive entry payloads. These preserved bytes do not establish successful Samsung API translation or runtime policy readiness.

The mixed post itself is deliberately retained. Its copied Intent and worker can still retain credential/handle owners until the actual job returns; the leaf claims no improved lifetime or live drain. The post-commit `LockSettingsHelper.savePassword` static credential cache, repeated-password/pattern UI hints, capability-bearing diagnostics elsewhere and optional old-retrieval UI/background work remain separate unresolved selection conditions. Removing their entire mixed job would also remove modification-record effects and is not this cut.

Cold-start admission means the modified code is selected before this job/challenge/callback chain exists. Previously queued original runnables, active HAL challenges or callbacks require a separate disconnect/drain/reconciliation design; loading this leaf cannot retire them.

## Actual artifact proof

The output audit wrapper is `out/settings-rpmb-leaf/Settings.settings-rpmb-leaf.apk`, SHA256 `18f996214d1b7ae0114edf3118c4cd974262c615cc6a1e0b2bc2ae95e4d5944f`. Its changed DEX is `classes13.settings-rpmb-leaf.dex`, SHA256 `4c566b491c1f7289386085e59d3d2fef8913e6444b2077706f13a019f99f3c2a`. The output normalized method SHA256 is `531add1c127e7b01db0dc7e592c7ee44bee5e4b3ace09c446eb36a727e1d1633`.

The static helper decodes and hashes every declared method in every DEX on both sides: 468,254 method declarations, including 452,426 code bodies and 15,828 declarations without code. All 78,960 class declarations remain equal. Exactly the target body changes; 452,425 other code bodies and every no-code declaration remain equal. All 10,548 non-target archive entry payloads remain equal. Every input/output DEX039 signature/checksum validates. Repeated builds reproduce the same APK, DEX and target-body hashes.

Every encoded code-bearing method in the target DEX is checked for overlap with the patch slice: 51,345 bodies, zero other-method aliases. Exact inverse replacement plus resealing reproduces the original DEX byte for byte; applying the cut again reproduces the output DEX byte for byte. A separate shared-reader decode verifies eleven NOPs followed by the exact original tail and identical register/try metadata.

Three generated actual-byte negative fixtures are refused by structural guards: an IF_EQZ operand targeting prefix interior, an unexpected target try count, and another encoded method redirected to the target code item. The branch operand is decoded from fixture bytes; try-count and code-alias fixtures exercise the producer's structural parser. These are static guard tests, not ART verification, complete malformed-DEX certification or runtime fault injection.

The APK wrapper is reserialized. Its other entry payloads are preserved, but physical ZIP layout/alignment and Android/JAR/APK signing acceptance are not established; existing signatures are not valid approval of modified code. The wrapper exists for offline proof and is not installable-release evidence.

## Selection still blocked

This leaf may only participate in a separately reviewed composition with exact profile admission, real Samsung credential/biometric/storage/key authority, typed caller/user/challenge dispatch, current applied policy, safe ownership and committed-state/recovery semantics. Optional old retrieval and retained static credentials need their own closed removal/adaptation decisions. Genuine StrongAuth, extra-factor gating, enrollment authorization, key effects and reciprocal PIN/fingerprint lifecycles remain mandatory.

No global feature binding, resource selection, backend replacement, existing OneOS guard removal or phone action follows. The artifact is an independently reviewable optional-ingress cut, not a claim that the broader frontend or Stage 1 is complete.
