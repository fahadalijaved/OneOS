# OneOS 0.4.58 source and integration boundary

The intended delivery is an updated **full OneOS app** that verifies/provisions selected files and orchestrates the root session. The credential, biometric, policy and native adapters must operate in their genuine system/runtime owners. Final runtime architecture, companion route and packaging remain unselected. The inspected update does not establish reciprocal Samsung PIN/fingerprint authentication. No rebase, payload selection, build, installation or device-baseline update follows from this report.

The fixed public source is [commit45abb3df03cbd4a8b006519baaebefdb2c68658a](https://github.com/fahadalijaved/OneOS/commit/45abb3df03cbd4a8b006519baaebefdb2c68658a), committed2026-11-05T22:19:19Z, against parent1f2c2aa45ab8a7dc81384f6b67962d1e9cf7fefe. The received API enumerates54 changed paths. The bounded pin contains19 selected old/new text pairs:10 changed and9 identical. Exact HTTP entity bytes, URLs, UTC, hashes and the acquisition history are preserved by [source-pin report](../out/upstream-oneos-0.4.58-pin/PIN-REPORT.md) and immutable816458d2 manifest. Remaining paths are metadata/available-patch classifications, not a full repository or unseen-binary semantic audit.

Public0.4.58 source and advertised payload hashes are separate from the previously observed installed **full0.4.57/versionCode74** APK and captured guest JARs. The new source declares versionCode75/versionName0.4.58 and selected X9U overlay r62 instead of r61. Of30 selected manifest entries, only guards.txt, oplus-services, telephony-common and samcam hashes change. No new APK or payload binary was acquired.

| Guest JAR | Captured0.4.57 / parent advertised | 0.4.58 advertised |
|---|---|---|
| services | efb45f5f…854671 | Same hash |
| framework | 5cb16a37…7f6246 | Same hash |
| oplus-services | a854468f…141fa8 | d02092bc…3665e; unacquired/unaudited |

Full hashes and actual captured-file evidence are in the inventory and [security delta](../out/upstream-oneos-0.4.58-security-delta/REPORT.md). Equal advertised services/framework hashes identify the already captured contents; they do not prove a newly installed/loaded0.4.58 cohort. The changed OPPO/telephony/camera payloads need their own selected proof if reached. Existing source, DEX leaves, helpers and compatibility receipts keep their original pins.

`ScreenLockRule` is in the unchanged ScreenLock.kt. Actual switchGate code defaults a set lock to BLOCK, explicit Advanced allowed=true to WARN, no lock to OK, and unknown state to BLOCK. Its older header prose does not override that branch. This is a switch-risk decision, not credential verification, enrollment reconciliation, StrongAuth or key authority. The risk override cannot supply a real authentication result. [Pinned gate source](https://github.com/fahadalijaved/OneOS/blob/45abb3df03cbd4a8b006519baaebefdb2c68658a/app-android/core/model/src/main/kotlin/com/fahadali/oneos/core/model/ScreenLock.kt#L39).

The four selected guard producers are also unchanged: credential setters refuse changes and selected enroll/SID/setup calls are omitted; the selected Weaver getter yields null; five Vold-key operations are omitted; unknown-template cleanup is skipped with its reported-success behavior. Their existing make-overlays callsites remain. These preservation guards do not implement genuine shared verification/change, enrollment, CE or app-key policy. The added notification-light and SMS source producers address different faults. No whole-release absence claim is made, and the new oplus JAR remains unseen. [Pinned build source](https://github.com/fahadalijaved/OneOS/blob/45abb3df03cbd4a8b006519baaebefdb2c68658a/scripts/make-overlays.sh#L196).

The finite app review identifies these concrete contribution owners:

| Owner | Source-supported integration boundary |
|---|---|
| OneOsFilesTask / sessionScripts / packageSets | Add explicitly selected reproducible artifacts and synchronize content hashes, sizes, lists, remote selectors and mirrored package tests. |
| AppAssets | Verify root/list pins and supply bundled or hash-cached files through expectedStageHashes/open. Delivery alone is not runtime admission. |
| RootScript | Extend finite verbs, arguments, SCRIPTS/RECEIVE_NAMES and verified launch protocol for a selected contribution. |
| oneos_root.sh | Preserve profile/image/set/environment and received-byte checks, then coordinate the actual privileged lifecycle. Its detached launch acknowledgement is not guest/native readiness. |
| make-overlays and narrow patch/native producers | Produce reviewed guest bindings with preservation/inverse evidence; retain existing protections until their genuine replacement is assembled. |
| switch/prepare/start/return | Install the selected owner/lifetime/control branch before existing destructive takeover, with genuine errors, drain and return acknowledgement. |

These assets belong to the **full** flavor. Probe is separate, and generated OneOS package/session assets are attached only to full. Package-set files may be bundled when oneos.packSets=true or obtained by hash; they are not universally inside the APK. AppAssets, RootScript and oneos_root are byte-identical across the two commits. The [build flavor/asset gates](https://github.com/fahadalijaved/OneOS/blob/45abb3df03cbd4a8b006519baaebefdb2c68658a/app-android/app/build.gradle.kts#L409), [app map](../out/upstream-oneos-0.4.58-app-integration/FINDINGS.md) and [independent claim check](../out/upstream-oneos-0.4.58-app-claim-review/VERDICT.md) retain exact owners/line spans. A Vector companion is a prototype vehicle, not a mandatory final dependency.

The [startup delta](../out/upstream-oneos-0.4.58-startup-delta/REPORT.md) makes old lifecycle proofs unsafe to relabel. Five of six session scripts change; boot_status is identical. New watchdog FD-name discovery1089 follows stop requests1060/1068. Name-based system_server kill1103 and the recurring stop loop1115 remain. A retained-host design therefore needs a real admitted branch before those actions; the scan does not witness a surviving initialized authority.

One of fourteen data bridge destinations changes to a dedicated host resource-cache; thirteen remain. Preparation now deletes/recreates that cache each session, so mapping equality is not lifetime/drain proof. Theme-directory writes, animation/cutout/property producers, route changes and new sound-watch/app_process owners add work that must be accounted for. Return adds diagnostics while retaining global kill/restore/restart behavior. None is a security drain or accepted-return acknowledgement.

guest_start changes only by a509-byte GNSS diagnostic insertion after the old selected spans. The eleven old disabled-composition spans match the new bytes/offsets, but the whole source hash changes. This is a finite reuse opportunity, not a rebased derivative: fresh exact-base/gap/forward/roundtrip/inverse proof and review are required. Existing namespace/pivot, classpath, socket and native entry contours remain; no v3 helper/input ownership is admitted by the release name.

The next reviewable integration must bind an explicitly selected upstream/profile and actual runtime topology, add its verified delivery/protocol entries through the named full-app owners, and re-derive the changed lifecycle/property/bridge/return contracts. Genuine Samsung authority must retain physical user/policy/native ownership while original ColorOS lockscreen, native Settings and app-auth consumers receive real typed results. Preserve bidirectional PIN creation/change/removal, fingerprint authentication/enrollment management, StrongAuth/additional-factor/lockout, CE/app keys and correct return/reboot. Unknown transport or readiness cannot become NONE/swipe, a fabricated empty enrollment, cosmetic unlock or success.

This report joins final acquisition, startup, security and app-source evidence only. Runtime authority/display/native ownership, final artifact packaging, upstream PR admission and the full security acceptance remain distinct unfinished work. No scripts, downloaded source, compiler/tests, phone/ADB or network operations were run for this two-card synthesis; the prior acquisition remains immutable and the installed0.4.57 baseline is unchanged.
