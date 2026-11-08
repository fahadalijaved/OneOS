# Retained Samsung runtime: property-view decision

**Current OneOS global property mutation/restore is not a coherent retained-host property contract.** Retaining initialized Samsung classes preserves some static values, not every later Java/native query or property writer. A retained runtime could keep its genuine Samsung policy inputs if its original property area/persistent writer remain owned and guest-specific values are supplied separately before the guest's first native/static initialization. That separate property owner is not assembled or source-closed here. A filesystem mount namespace alone does not supply it.

This finite source join covers five exact **installed** OneOS 0.4.57 scripts, eleven already captured Samsung methods, one actual-staged guest runtime writer, and the frozen native installd property facts. The audit passes60 checks; 112 syntactic mutation candidates are indexed with source lines and conditions left explicit. This is not complete transitive framework/HAL/property reachability, a list of actual values applied on the phone, or readiness measured by counts. No script, original runtime, native tool, property write or phone command ran. All previous cards remain unchanged.

## Exact global mutations and their order

The [inventory](../inventory/retained-property-view-plan.json) pins the literal script bytes, original method receipts/body hashes, every candidate line, and literal `setprop` targets. Script numbers below are one-based packaged source lines. Runtime branch outcomes are unobserved.

| Source | Writes / meaning |
| --- | --- |
| Switch311–313 | Writes/deletes `persist.oneos.probe` to test the global persistent writer, **before** snapshot320. This is a real shared write test, not an isolated guest property service. |
| Switch751,755–759 | `ro.control_privapp_permissions=log`, `persist.sys.disable_rescue=true`, `sys.rescue_boot_count=0`, `crashrecovery.rescue_boot_count=0`. These precede host zygote stop971 and guest preparation1087. A cut only at guest_props1149 is too late. |
| Switch773–776,810,814,830,1047 | Audio/offload tuning; `persist.sys.assert.panic=true`; `persist.sys.oplus.aotcrash_controller_enabled=false`; conditional saved guest locale; conditional `persist.vendor.softdog=off`. They are global setters, with original source predicates. |
| Prepare1529 /3340 | The preparer directly sets conditional `oneos.unfold_transition=0/1`; it also emits a helper containing `oneos.guest.powerctl=ksud:soft-reboot`. Emitted helper code is a later writer, not evidence it ran. No other direct literal setter in the preparer was identified by this bounded source pass. |
| Switch1149 → guest_props `add` | Dynamic image-property collection128–164, then `resetprop -n -f`702 or per-property708. Image files, host-defined-name set and branch inputs determine the actual manifest; that current manifest was not acquired by this task. |
| Guest_props explicit exceptions | Background blur181; Samsung-style USB config207; Bluetooth feature overrides236/320; ColorOS device-first-boot576; ringtone names727; audio vendor extension748; conditional ABI lists772; conditional boot hardware791; isolated compilation803. Their specific predicates matter; e.g. the Exynos/Qualcomm workaround is not assumed active on this observed Snapdragon profile. |
| Guest_props manifest-only edits | Panel scale, OPPO camera-hole geometry, `persist.sys.saupwk_test`, Night Light, HyperOS/Nothing feature/log/render fields are prepared in the new property list under source predicates before the shared setter. They are not per-process values merely because a guest consumes them. |
| Shared service/control setters | Switch/start/return have actual `ctl.start/stop/restart`, USB, boot-animation and guest-power-control writes. Root/host init and real hardware ownership must deliberately handle these; redirecting every command into a private guest area would break that control contract. |

The generic image filter **does protect important host identities**: it skips host-defined names147, excludes selected crypto/boot/hardware/zygote/vold/SELinux/APEX families154–155 and attestation names159. Explicit overrides bypass parts of the generic rule. This evidence does **not** prove a current change to Samsung first-API, FBE, attestation identity, HSUM or Weaver properties. A previously undefined property can still replace an original reader's default if a matching guest value is added; proving that requires the actual manifest and branch outcome. No guessed new value is treated as a security fact.

The preparer imports `/dev`316 and only later guest start makes its filesystem tree private. There is no independent property-area/client/service producer in those mount operations. Native cached references and shared property-service writes require their own owner.

Property writers also continue after shell preparation. The previously pinned **actual staged** `UserDataPreparer.prepareUserDataLI` constructs `sys.user.<id>.ce_available` (PCs115/126) and sets it to `true`167 under its original branch. Its staged storage guards do not make that signal physical Samsung CE proof. This source demonstrates a real guest runtime writer beyond the manifest; it does not establish that a particular retained host consumer reads that key, nor justify forcing/suppressing the signal with a fake result. The separate guest app-data/physical-user lifecycle contract remains mandatory.

## Cached code and future live policy are different

PCs in this table are code-unit addresses in the exact original Samsung bodies. The new raw slice contains only existing pinned methods; it performs no new OEM loading or source query.

| Actual original source | Classification and consequence |
| --- | --- |
| `RoSystemProperties.<clinit>` reads `ro.control_privapp_permissions`28, stores the string32 and LOG/ENFORCE flags151/159; calls CryptoProperties99/113 and stores crypto fields111/125 | **Class-initialization cache.** If this actual class was already initialized, later global changes do not reexecute these stores. A late class/other reader can still see the changed area. Actual initialization generations are not observed here. |
| PMS constructor reads `Build.VERSION.DEVICE_INITIAL_SDK_INT`689 and other Build static fields | **Static field consumption**, not a fresh property read at that callsite. The genuine producer/runtime/class identity must be preserved. This does not certify every Build accessor or prove its whole class-init path in this pass. |
| `CryptoProperties.state/type` each call `SystemProperties.get`3 for `ro.crypto.state/type` | **Per-call query** where these methods are invoked directly; the RoSystemProperties wrapper instead snapshots their earlier results. Generic OneOS filtering protects these families, so changed values are not asserted. |
| LSS `isSupportWeaver` gets `security.securehw.available`4; `isEnablePrevCredential` gets `ro.organization_owned`4 | **Per-call query**, subject to original control flow. A retained LSS is not a frozen copy of these future reads. Actual conflicting guest values are unproved. |
| UMS headless-mode/creation-override methods | Existing bodies combine Build debug guards with direct property queries. Preserve the guard and actual source; do not replace them with a cached default or assert a release build always takes a particular path without runtime evidence. |
| UMS `setContainerInfo` writes `persist.sys.knox.userinfo`103, literal100 | **Real retained-host writer**, not a value owned by the guest merely because it differs from an earlier snapshot. |
| Native installd `start` reads `persist.zygote.app_data_isolation` at0x263e8, stores0x263f8 after publication/thread start | **Startup cache** in that daemon. A fresh clone and retained original can have different initialization times; a new namespace or publication does not certify the value. |
| Native `invalidateMounts` reads `persist.sys.fuse` at0x3ef60 | **Read during rebuild**, alongside actual mount inspection. Filesystem view and property view are separate inputs; preserving one does not preserve the other. |

## A concrete lost-update counterexample

Normal `guest_props restore-persist` is broader than guest-name ownership. It deletes a currently present `persist.*` name absent from the saved snapshot975 and restores a changed saved value984. The guest-name filter applies only to `--recover`974/983. A trusted snapshot proves what was saved and its stage association; it does not identify the producer of a later change.

For example, if the legitimate retained Samsung UMS updates `persist.sys.knox.userinfo` after snapshot320, normal return can overwrite it with the older snapshot or delete it if previously absent. This is a source-supported conditional lost update even when the guest never needed that key. No such event was induced or observed. Restoring an old snapshot also cannot undo callbacks, native cache changes or actions already taken while a different value was visible.

Therefore the existing normal snapshot/restore algorithm cannot simply stay active over a concurrently operating host. Removing it alone is also insufficient: guest writes need an owned replacement rather than leaving their effects in the host area/store.

## Smallest next owner and exact rejection test

The proposed direction is **host-global values remain genuine; guest-only values move to a new guest property runtime before its caches initialize**. It does not move an already initialized multithreaded Samsung property client or replace its Build fields.

1. Prepare the guest property manifest from the exact selected image and original source filters **without applying it to the host area**. Classify every direct setter as guest-local data, deliberately shared host/hardware control, or refused/unresolved. Preserve errors and original safety guards. The generic manifest, explicit exceptions and direct/background writers must all use the selected route; changing only `set_prop()`292 is insufficient because direct setters bypass it.
2. Close the **actual guest-native property client/area/service bootstrap** before guest app_process/zygote and native/static caches initialize. It must own native/generated sysprop reads, writes, callbacks/invalidation and the guest persistent store. A Java-only SystemProperties hook, mount of `/dev/__properties__` after client initialization, copied Build, map of defaults or UID test is not that closure. Whether the original client/service can be hosted in this placement is the precise next source/native question; no whole second init is assumed mandatory.
3. Keep host canonical property memory, persistent writer and legitimate updates untouched. Route only reviewed genuine init/hardware commands outward under their actual owner. Retire guest admission/writers and acknowledge completion before disposing its private view; do not replay the broad shared persistent snapshot over the retained host.

**Disqualifier:** if a required same live host/native process must consume a guest value and a different Samsung policy value for the same key at the same time, one shared area cannot represent both. Either the actual source must support a narrower owner/protocol adaptation or this topology fails. This pass proves the restore lost-update problem, but does **not** manufacture an unavoidable conflicting required hardware key from unacquired property values. Optional unsupported OPPO behavior should remain unavailable under the project's policy instead of driving host policy changes for parity.

The first unbound owner is thus the guest native property-area/service initialization and complete write/persistence route, **not** another filesystem namespace flag. Root chooses the next proof; no runtime property overlay, source hook, launcher, architecture pivot or original operation is selected by this card.
