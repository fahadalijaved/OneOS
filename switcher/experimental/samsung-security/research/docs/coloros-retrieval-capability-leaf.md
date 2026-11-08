# Cold-only OPPO retrieval capability leaf

**Unselected PC artifact.** This leaf makes the unsupported OPPO old-password-retrieval capability unavailable. The returned false is a capability result, never an authentication result. It does not disable Samsung's genuine previous-credential recovery, change current-credential verification or clear policy. No Android/OEM execution, phone action, installation or live teardown occurred.

[The inventory](../inventory/coloros-retrieval-capability-leaf.json) is the composition interface. [The producer](../tools/build_coloros_retrieval_capability_leaf.py) and [private locator](../tools/retrieval_capability_dex.py) modify only this leaf's new outputs. The frozen first Settings producer supplies pure DEX integrity utilities, and its frozen hash-only Java helper supplies whole-archive method comparison. Neither older producer/helper nor its proof/output files is changed.

## Exact cut

The admitted original Settings APK is SHA256 `33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b`: fourteen ordinary DEX039 files, 78,960 classes. The exact public static getter is `com.oplus.settings.utils.SysFeatureUtils.isSupportPasswordRetrieve():boolean`, original normalized body SHA256 `9356ef0eecaf5e606577c12e928be89f8ea5fabd62c73a8db6bd1d7e589fa556`.

In `classes2.dex`, code-unit PCs `[0,2)` originally load the cached Boolean. The four replacement bytes encode `CONST_4 v0,0; RETURN v0`. The remaining original method bytes, register count, references, branch offsets, debug offset and empty try metadata remain unchanged. Its original body queries `oplus.hardware.pwd_retrieve_settings` and caches the result; this leaf returns unavailable before either cached value or PackageManager can enable the optional capability. The cache field has exactly three direct references in this archive, all inside this getter, so no other observed direct cache consumer depends on initializing it.

This is explicit supported-profile capability selection, not an inference from absent feature declarations and not a fake hardware response. Only one method changes.

## Eleven callers and paired original behavior

The immutable full-Settings reference proof finds eleven direct getter calls. Every call's exact body, invocation PC, consuming result register and false-branch successor are pinned. Newly inspected complete password/pattern fragments, timer callbacks and preference controller close their immediate UI/lifecycle frontier.

| Original caller group | Behavior with unavailable capability; unchanged source otherwise |
| --- | --- |
| Password and pattern confirmation `onResume` | Skip the optional old-password-entry decision. Actual lockout queries, current credential UI, result trackers and required listeners continue through their original paths. |
| Password and pattern countdown `onFinish` | Skip the feature-gated old-password-info refresh. Existing enable/stage/timer work remains. Independent old-mode stages are not silently reinterpreted as Samsung recovery. |
| Password and pattern `updateUi(Stage)` | Skip a feature-gated reset-view hide/listener-clear block. This is **not** an unconditional hide operation. Cold-view resource evidence and the exclusion of existing optional jobs/state are necessary. |
| Native PIN/password and pattern save-worker mixed lambdas | Skip only the old-password-storage block. Genuine setter/verification and modification-record effects are unchanged. Their independent RPMB ingress is a different operation: compose the separate reviewed PIN/password RPMB leaf; pattern-specific RPMB work remains separately tracked. |
| OldPasswordCategoryController constructor | Still constructs its SDK wrapper, whose actual constructor only initializes Object and stores Context/system type; unavailable capability skips its asynchronous old-password-info fetch. |
| Controller `isAvailable` | Returns unavailable before old-password-info/try-count checks. |
| Controller `updateState` | Uses the original preference update without launching its feature-gated async refresh. Actual false-state preference handling hides the delete category and old-password time summary, **shows** `lock_pwd_footer`, and skips starting the countdown. It does not hide all three preferences. |

Actual donor resource mapping ties reset view ID `0x7f0b0c60` to both fragment fields. Password layout `0x7f0e0108` resolves to `choose_lock_password_oplus.xml`; pattern layout `0x7f0e03ea` resolves to `navigation_choose_lock_pattern.xml`. Both selected XML nodes declare visibility enum 2 (`gone`). The raw complete resource dump and selected XML trees are pinned under ignored firmware; they are source resources, not proof of installed overlays or actual inflation.

The only observed methods that explicitly show the two reset TextViews are their `displayOldPasswordResetGuide` paths after asynchronous info retrieval. Other selected field users initialize or hide them. False capability prevents the ordinary cold onResume/countdown fetch ingress. It does **not** drain an already queued supplier/consumer or prove every independent way into old-mode UI is disabled.

## Precise retained limits

The original fragments also parse explicit old-mode Intent flags and can restore old-mode state. Their `onActivityResult` methods can handle an old reset result, show a dialog or finish. These are independent of the eleven capability queries. This leaf preserves those methods and **does not claim the entire retrieval/reset UI is unreachable**. Runtime selection must first reject/cancel unsupported old-mode requests and restored/results state through a separately reviewed admission design. A cold new process alone is not proof that an incoming Intent is ordinary current-credential confirmation.

No already registered callback, old click listener, pending supplier/consumer, countdown or returned result may survive into selection. The unchanged footer and other independent UI state need accurate profile presentation. There is no hot cleanup or manufactured cancellation acknowledgement here.

Samsung's legitimate previous-credential recovery remains a dedicated mapped policy route. Previous PINs must still fail ordinary unlock in both systems. Preserve real current-credential checks, setters/removal, password-history policy, StrongAuth, additional factors, fingerprint/enrollment authorization and intended app-key/CE behavior. No new true/authenticated result, HAT, token, credential or backend is supplied by this leaf.

## Actual artifact and byte proof

Run `python -B tools/build_coloros_retrieval_capability_leaf.py` using the pinned local source receipts/resources. It refuses source-lock, archive, dependency or normalized-method drift. Output:

- APK audit wrapper: `out/retrieval-capability-leaf/Settings.retrieval-capability.unselected.apk`, SHA256 `90f81c83f3012e1b9c329c559f02c490536fb74584043470b45c4177747049dd`.
- Changed DEX SHA256: `626b87c6e4f6fa5023df630cb3bcdf92ed1079730f2811bce9ab372a90d5cdb2`.
- Patched normalized getter SHA256: `e6b969c6067218515e292829e8e4609e4c45eff606d25ad2e8e8229949c05aa4`.

All 78,960 class declarations and 468,254 method declarations remain equal. Exactly the capability body changes; the other 452,425 code bodies and 15,828 declarations without code remain equal. All 10,548 non-target archive entry payloads, including thirteen complete DEX files, remain equal. The target parser rejects code aliases overlapping the cut. All input/output DEX039 integrity fields validate; exact inverse restores the original DEX, and forward roundtrip restores the patched DEX. A fresh shared-reader decode confirms the exact false return plus original tail, registers, branches and empty tries.

These are positive static byte/decoded-method proofs; no malformed-byte negative fixture or runtime fault campaign ran. The ZIP wrapper is reserialized, with stale/unsupported signing and alignment status; it is not release/install evidence. The untouched original archive remains the source for root's disjoint-method composition with the earlier Settings RPMB leaf. Root must retain the union of **all** selection conditions, including credential-cache and remaining optional-path obligations.

The claim is limited to the exact supplied Settings APK's explicit references and selected resource layouts. Reflection, other APKs, dynamically loaded code, installed bytes, Android scheduling, cryptographic acceptance and the full reciprocal security outcome remain outside this artifact's acceptance.
