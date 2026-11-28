# Cold-start ColorOS RPMB input-removal leaf

This **unselected, offline component** removes the original SystemUI plaintext
entry copies and the two optional RPMB task producers. It preserves native
credential construction, genuine verification results and original policy/UI
completion gates. It implements no Samsung authentication binding and makes no
runtime or device acceptance claim.

Source: original `SystemUI.apk`, SHA-256
`0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77`.
The archive contains nine ordinary DEX039 files and 73,080 class definitions.
The producer admits this literal profile and fourteen exact normalized source
body hashes. It reuses the frozen first-leaf DEX039 integrity helpers with a
literal SHA-256 dependency pin; no old tool or source archive is modified.

## Observed source contracts and exact edits

Ranges below are half-open instruction PCs in 16-bit DEX code units. Every
range becomes same-size NOP instructions; no register count, offset, class,
signature or handler is rewritten. Full owner descriptors, source/patched body
hashes and absolute per-DEX byte ranges are in the inventory.

| Original owner/member | NOP ranges | Retained native work |
| --- | --- | --- |
| `OplusKeyguardFixedPinViewController.getEnteredCredential` | `[0,11)` | Original input getter and `createPinOrNone` at 11/15 |
| `OplusKeyguardPasswordViewController.getEnteredCredential` | `[0,27)` | Original widget input and password factory |
| `OplusKeyguardPinViewController.getEnteredCredential` | `[0,27)` | Original widget input and PIN factory |
| `OplusKeyguardLockDeadPasswordViewController.getEnteredCredential` | `[0,27)` | Original mode, input and typed credential factory |
| `OplusKeyguardPatternViewController.access$onKeyUp` | `[127,140)` | Keyboard handling, genuine pattern string at 123, verification at 153, input-list cleanup at 158 |
| `OplusKeyguardPatternViewController$UnlockPatternListener.onPatternDetected` | `[18,33)` | Input timing/disable and genuine pattern conversion/verification at 41/49 |
| `PresentationFixedPinViewController.getEnteredCredential` | `[0,11)` | Original input getter and PIN factory |
| `PresentationPasswordViewController.getEnteredCredential` | `[0,25)` | Original widget input and password factory |
| `PresentationPatternViewController.getEnteredCredential` | `[0,9)` | Actual stored pattern input and typed factory |
| `PresentationPinViewController.getEnteredCredential` | `[0,25)` | Original widget input and PIN factory |
| `OplusSubDisplayKeyguardFixedPinViewController.getEnteredCredential` | `[0,11)` | Original subdisplay input and PIN factory |
| `OplusSubDisplayKeyguardPinViewController.getEnteredCredential` | `[0,27)` | Original subdisplay widget input and PIN factory |
| `OplusLockPatternChecker$checkCredential$1.onChecked` | `[59,111)`, `[114,117)` | Full response/matched logic, null task assignment at 111, credential zeroize at 119, cancellation/task cleanup at 122/124, failure/current-user/StrongAuth/fallback logic |
| `OplusLockPatternChecker$checkMultiUserCredential$1.onChecked` | `[29,82)`, `[85,88)` | Full response/matched/family/minors guards, null task assignment at 82, original conditional zeroize at 90, cleanup at 93/95, failure/cross-user policy |

**Source fact:** the original direct graph has twelve `setEntry` callers and
two `getEntry` consumers. Both consumers feed `RpmbCheckTask` construction,
including a duplicated `LockscreenCredential`, the real response, user and
optional retry callback. The patched direct graph has zero setter calls, getter
calls and task-constructor calls. It retains the two original null task writes.
The task field has four direct references, with only its accessor writing it;
the original four accessor calls become those two null writes. The entry field
has only constructor initialization, setter and getter references.

**Inference limited to fresh owners:** the original task field starts null and
has no remaining direct non-null producer in this archive. No current plaintext
is retained through this optional entry/task chain. Other original
`postRpmbCheckTask` callers remain. They can realize the manager; its unchanged
downstream method rejects null at PC0, returning at 79 before its cache write
at 28 or executor submission at 76. This is not complete manager/RoR removal.

Neither callback is replaced wholesale. Original credential failure handling,
zeroize sites and their branch conditions remain, including existing
family/minors conditions; this leaf does not claim to repair every original
credential lifetime. Early-progress handling, authoritative full verification,
user selection, lockout, StrongAuth/additional-factor and finish controllers
remain separate integration obligations. No success result or policy clear is
introduced.

## Verification and admission limits

Run `python -B tools/build_coloros_rpmb_input_leaf.py`. Output is ignored
`out/rpmb-input-leaf/SystemUI.rpmb-input-leaf.apk`, SHA-256
`1120a5e47b750cac44f215a29a549df230920fae549a6a1869eac33950d2aa16`.
The tracked inventory is the composition interface; raw original/patched bodies
remain under ignored `firmware/rpmb-input-leaf/`.

The checks prove fourteen changed methods/sixteen ranges in `classes3.dex`,
`classes8.dex` and `classes9.dex`; 169 other selected-class bodies are unchanged.
Every byte outside the ranges and DEX integrity fields is equal. Other archive
payloads, including six complete DEX files, are equal. All nine input/output DEX
headers, extents, SHA-1 and Adler32 fields validate. Exact inverse and forward
roundtrip reproduce every changed DEX. Other-method code overlap is rejected.
Retained branch targets and both keyboard switch payloads are checked, including
switch-relative case offsets; all fourteen original methods have no try blocks.
Decoded-record wrong-body and interior-branch negatives reject. These negatives
are not malformed-byte fixtures or runtime fault injection.

Admission requires a **cold fresh process with newly constructed owners** and
no existing cached task, credential duplicate, queued job or callback. There is
no live drain/teardown claim. Separate RoR/SP registration/reboot and Settings
RPMB/cache removal must be composed and reviewed before declaring the broader
optional feature removed. Exact Samsung authority/transport, required native
PIN/fingerprint Settings flows, app keys, CE access, policy readiness and the
full cross-OS matrix remain pending.

DEX checksums establish format integrity. The reserialized APK preserves entry
payloads, not physical ZIP encoding or its original signing block. No Android
signing, ART verifier, OEM execution, phone action or installed-image acceptance
was performed. `selected=false`, `coldStartOnly=true` remain mandatory.
