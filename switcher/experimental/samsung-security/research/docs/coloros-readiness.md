# ColorOS authority-failure consumers and cold error-propagation leaf

The two original fail-soft returns reach real mode, dismissal and Settings
decisions. A cold, **unselected** framework leaf now preserves the caught
`RemoteException` instead. This closes those two error-to-value conversions;
it does **not** implement safe recovery, authority readiness, or cache-generation
ownership. Required readiness/FAIL-01 remains open. No OEM code was executed.

`inventory/coloros-readiness.json` pins 45 bounded method bodies, their raw
receipts, physical DEX, logical header, normalized body hashes and reference PCs.
Inputs are the immutable original ColorOS framework `d5c6b7fd…`, SystemUI
`0e253fad…` and Settings `33b0173b…`; these are not identified installed OneOS
bytes. Every selected logical header is zero. PCs below are 16-bit code units.
Existing protocol/frontend evidence is reused; new reads follow bounded cache,
mode, finish and native Settings caller edges. This is not an exhaustive audit of
every authentication consumer or exception boundary above Android dispatch.

## Observed cache and error boundary

In framework `classes6.dex`, `LockPatternUtils$1.apply(Integer):Integer` and
`$2.apply(Integer):Duration` have five registers. Both call the real service at
PC10, return its normal value at PC18, and catch `RemoteException` for `[0,18)`
at PC19 into **v0**. The original log at PC24 receives that same v0. At PC27,
the first body substitutes boxed −1; the second substitutes `Duration.ZERO`.
Each `apply(Object)` bridge invokes its typed method at PC2, without a catch.
Two exact whole-framework reference scans find those bridges as the only direct
typed-call references. Virtual dispatch is not claimed to be a whole-program
reachability proof.

`PropertyInvalidatedCache.recompute(Object)` invokes its actual QueryHandler at
PC2 without a catch. `query(Object)` calls recompute at PC54 (bypass) or PC109
(miss), both outside its catch ranges. Its catch-all monitor cleanup rethrows;
it supplies no unavailable fallback. On a cache hit it returns at PC108 without
recompute. A miss result can be inserted at PC139. Thus the stock synthetic NONE
or ZERO can become a cached ordinary value; the cold patch cannot cure an
already-cached value or detect a dead authority on a hit.

`LockPatternUtils.getCredentialTypeForUser` queries at PC31, with an existing
multi-app-user remap before that call. `getKeyguardStoredPasswordQuality` calls
this getter at PC0 then `credentialTypeToPasswordQuality` at PC4. The latter's
switch explicitly maps −1 to PC37, quality zero. `getActivePasswordQuality` calls
the stored-quality getter at PC0. Separately, `isSecure` returns false for −1
(comparison PC5, false PC9). These methods have no catch.

`getLockoutEndTime` queries at PC6; `isZero` at PC12 branches directly to return
PC45 for ZERO. Only an elapsed nonzero deadline takes the additional recompute
at PC38. It has no catch. The real invalidation methods exist:
`invalidateCredentialTypeCache` and `invalidateLockoutEndTimeCache`, both invoke
`PropertyInvalidatedCache.invalidateCache(String,String)` at PC4 using the
`system_server` module and respectively `getCredentialType` / `getLockoutEndTime`
API keys. Those property names are not an authority/user/generation attestation.

## Observed terminal consumers

| Consumer | Exact reached decision and effect |
| --- | --- |
| OPPO device mode (`OplusKeyguardSecurityModel`, SystemUI `classes3.dex`) | `getDeviceSecurityMode` reads current-user active quality at PC4. After its existing study-space branch, quality zero takes PC62 → PC121 and returns `SecurityMode.None`. Numeric quality still selects real four/six/general PIN metadata. `getSecurityMode` reaches this device path at PC60 after its SIM/other checks. Bouncer implementation delegates at PC4. None has an unavailable-error catch. |
| Base mode (`KeyguardSecurityModel`, SystemUI `classes.dex`) | Its credential Supplier calls the type getter at PC6; `getSecurityMode` invokes that Supplier through `DejankUtils.whitelistIpcs` at PC113. −1 branches PC124 → PC153, selecting None. Existing SIM and secure-lock-device early branches remain. The Supplier wrapper restores strict-mode state then rethrows the same caught object, or directly returns Supplier.get; it does not substitute a mode. |
| Primary screen | `showPrimarySecurityScreen` calls its Supplier at PC17. Lambda8 reads the selected-user ID at PC6 and mode at PC10. The returned mode is recorded at PC56 and shown at PC59. No catch in those selected controller/Supplier bodies converts an unavailable exception into a mode. |
| Finish | `showNextSecurityScreenOrFinish` queries mode at PC210/261/357. The current-None path can select the original NONE-security dismissal when the newly queried mode is None. Actual finish is PC602. Original secure-lock-device enabled PC391 / authenticated-pending PC413 can refuse completion at PC434. Trust, biometric, SIM, expected-mode and password paths remain unchanged; those paths do not all require fresh credential-cache recompute. The method has no catch. |
| Keypad lockout | `OplusKeyguardAbsKeyInputViewController.onResume` reads current-user deadline PC18. Existing fingerprint/face policy can supply another deadline; ZERO is not guaranteed to remain the chosen deadline. For the final deadline, `shouldLockout` returns false exactly for zero. The non-lockout branch at PC132 resets OlockState mode at PC134, resets input at PC140 and can enter STATE_NORMAL at PC163. `onPasswordChecked` also reads the deadline at PC234 before its lockout helper PC243. Selected bodies do not catch unavailable errors. |
| Native Settings lock choice | `OplusScreenLockSettings$ScreenLockSettingsFragment.currentKeyguardQuality` reads `isSecure` PC9; false returns quality zero at PC24/25. For confirmation, fragment `launchConfirmationActivity` calls Builder.show PC73 → helper.launch → helper.launchConfirmationActivity. Its ordinary selector reads credential-owner-profile stored quality at PC19. Quality zero produces `Optional.empty`; the helper can return false. Fragment `launchChooseOrConfirmLock` sees false at PC31 and launches ChooseLockGeneric at PC85. This is routing evidence, not proof the later chooser bypasses every independent check. No unavailable-error catch exists in these selected methods. |
| Native Settings lockout | `ConfirmLockPasswordFragment.onResume` reads effective-user deadline PC7, converts to milliseconds PC11, and zero branches PC79 → PC90. If `mLockInput` was set, it clears it at PC95 and calls `updateUi(InputPassword/ResetPassword)` at PC106. `onPasswordChecked` separately reads deadline PC170 before lockout PC178; its only selected catch is for IntentSender failure elsewhere. |

## Exact cold leaf and preservation

`tools/build_coloros_readiness_leaf.py` admits only the original framework SHA.
It changes PC27 in each typed apply to **THROW v0**, padding the remaining tail
with unreachable NOPs: `[27,33)` for type and `[27,30)` for lockout. PC19 still
captures the original exception; PC24 still logs it. No new exception, readiness
Boolean, credential type, policy value or security-mode sentinel is invented.
Normal Binder calls/results, bridges, catches, registers, descriptors, all other
method code and all other archive-entry payloads remain unchanged by byte proof.

The output is `out/coloros-readiness/framework.readiness-leaf.jar`, SHA256
`a099dcefc730d3d01d3512d7666807fd1d78d1156153c4c5fc2e99620644e3d7`.
Changed DEX SHA256 is
`1d3648ffa3516e3dfaf6abea7eca559105cb8842541ec9a60a3afc2a052b713c`.
The two source code offsets are 702080 and 702272 in `classes6.dex`.
`out/coloros-readiness/leaf-receipt.json` records exact code/header locations,
new normalized bodies, direct static readbacks and selection conditions.

Checks pass for exact inverse/roundtrip DEX, only the two tails plus DEX integrity
header changing, complete remaining ZIP payload equality, no overlapping method
code, valid input/output DEX039 integrity, unchanged bridge bodies and exact
decoded THROW/NOP/try/register shape. Three decoded-record refusal probes reject
wrong source hash, wrong caught register and an interior branch entry. These are
not malformed-byte tests or ART fault injection. All complete branch/try source
structures in the two changed bodies are checked; no branch enters either tail.
DEX SHA1/Adler32 establish format integrity, not authenticity. ZIP encoding is
reserialized; ART verification, signing and installation are untested.

The shared source-only Python wrapper correctly refuses a generated `out/`
archive. Output readback invokes its same pinned authored Java static reader
directly with two exact methods per class, writing raw output only to this
stream's ignored firmware directory; the wrapper policy is unchanged. This
executes the authored reader, never OEM classes.

## Required coherent ownership; still unassembled

The source-supported cut prevents these two **new failed recomputations** from
returning permissive values. It has no existing higher caller that demonstrably
owns a complete protected-unknown presentation and safe return. An uncaught
exception or SystemUI/Settings crash is not that recovery contract.

Before selecting any leaf, a real authority lifecycle must admit the actual
selected/effective user and current Samsung authority generation before mode,
confirmation, resume and input/auth requests; recheck after external callbacks
and immediately before accepting finish. It must apply actual StrongAuth and
additional-factor policy before UI activation. Preserve the original finish
guards, legitimate credential-free state, SIM/trust/remote/lock-dead semantics
and real policy deadlines. Never force PIN, force secure, clear policy, or treat
an initial false flag as proof.

That same owner must reconcile/invalidate both actual cache namespaces on
authority replacement/death, user changes and committed credential/policy
changes, then obtain authoritative same-generation results. Cache invalidation
alone cannot prove authority availability; a fresh valid NONE/ZERO is legitimate.
Lost authority must hold a protected unknown-state presentation, stop admitting
new attempts, own queued progress/cancel/death work and provide safe return with
real callback/resource drain. Settings must abort/retain the affected operation
and reconcile uncertain commits, preserving failure rather than starting a
credential-free flow or blindly retrying a possibly committed write. Existing
OPPO fallback fingerprint/face deadlines need genuine Samsung binding or explicit
optional removal without losing required policy.

This independent framework leaf contains neither the optional PIN-metadata nor
RPMB removals. Root owns coherent immutable-source composition and must retain
the union of all conditions. It is cold-start-only, never a live framework/cache
patch, and remains unselected. Installed-source identity, process/service owner,
protected recovery, cache-generation transport, ART/hardware/app-key/CE and all
cross-OS acceptance cases remain open. Parent ColorGlass work remains paused.

Recheck: `python tools/build_coloros_readiness_leaf.py`, then
`python tools/audit_coloros_readiness.py`. `--collect` on the audit is only for
regenerating its fixed named source queries; unchanged source audits need no
repeat collection.
