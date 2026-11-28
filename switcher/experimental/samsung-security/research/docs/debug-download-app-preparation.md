# Local debug download-only package metadata

Status: actual source preparation PASS, not an APK/Gradle build. The optional
`-Poneos.debugDownloadMetadata=true` build flag selects an exact public release
metadata snapshot for local debug APK asset generation. It does not approve or
verify any downloaded package payload, change an app download/receive check, or
enable native view, guest or security behavior.

`compat/app-integration/debug-download-metadata.patch` modifies only the ac18
overlay's `app-android/app/build.gradle.kts`. Without the property (or with false),
the original real-payload directory, length and SHA-256 loop executes unchanged.
With `oneos.packSets=true`, the metadata option refuses. It also refuses custom
test-package directories, series filtering, and any Release task anywhere in the
actual task graph. All nine original package sets remain mandatory and nonempty;
the task is neither skipped nor supplied placeholder payload files.

The explicit mode uses only
`app-android/packages/debug-download-assets.tsv`. The prepared Gradle source pins
its SHA-256 to `ae4f9703e8756f2e20452fcfa13199e1e59526fecd0dcc5b74ac36db075c7f16`.
The 17,659-byte file has 242 sorted `<sha256><TAB><size><LF>` rows. The task opens a
regular, nonlink file with NOFOLLOW_LINKS, retains a single bounded read/EOF
snapshot (32 KiB maximum), checks path identity and the literal content hash,
then rejects invalid rows, zero/oversized lengths, duplicates, missing or extra
hashes. Sizes must be in 1..268,435,456, the existing root receive limit.

The task additionally pins and reads all nine actual raw package lists and the
actual `remote.txt`, rejecting changed sources. Their 329 filename occurrences
must resolve to exactly these 242 unique hashes. Remote mappings remain the
genuine existing source strings, including `gh:sets-1`; the task's configured
remote map must equal that retained mapping. It emits the same per-set list
rendering and the genuine declared sizes/source IDs into the existing index and
remote outputs. Existing script hashing, content-addressed script copies,
script-list generation and unknown-script refusal still execute normally.
No app runtime code, per-set BuildConfig hash calculation, SHA list or downloader
is changed. Official metadata is an input to a download-only APK, not a claim of
payload byte verification or remote availability at a later download.

The public data source is Root's exact official `sets-1` API capture:
`firmware/full-apk-release-metadata/oneos-files-sets-1.json`, SHA-256
`0f7c3e548678df8a598a6d2ef5d4e01bb37469e6a4220b876f82324e3ac5a730`.
Independent join `out/full-apk-remote-set-metadata-check.json`, SHA-256
`417f051d89dd24770612291fcab0d8a111a6398a2612278f4ccbf77b213e1db2`,
binds every current hash to one uploaded public asset with matching name and
`sha256:<hash>` digest, positive bounded size, exact release/tag/URL and source
filename memberships. It covers the 22 current hashes absent from the old APK as
well as the other 220. No package payload was fetched or hashed for this evidence.

`tools/prepare_debug_download_app.py` rechecks those exact sources and joins,
derives the fixed TSV, and applies the authored patch by strict count, position
and context with exact inverse/reapply. It keeps the original payload loop and
actual script block verbatim. It writes a fresh complete fourteen-file overlay
under ignored `firmware/debug-download-app/`, based on the exact ac18 receipt
`firmware/retained-view-app/receipt.json` SHA-256
`ac18addc37c2c9348fad157b216f27eba302b3c5e952af95624e5bbce259c49b`.
Thirteen base files are carried forward with only Gradle changed; the TSV is the
one new file. The twelve other base outputs remain exact. Input snapshots and the
original Gradle bytes are retained before final receipt publication. Existing
clone, ac18 output and prior receipts are never overwritten. A changed input,
unexpected source, or existing destination refuses without retry or repair.

Root ran `python -B tools/prepare_debug_download_app.py --prepare` once after
source review. Default invocation prints plan metadata. The resulting receipt
schema is `debug-download-app-source-preparation/v1`, with fourteen relative
`overlay/app-android/...` output paths. A fresh owned build tree copies the held
clone and applies only those fourteen files. To use this build adaptation it
must explicitly add `-Poneos.debugDownloadMetadata=true`; omitting it retains the
original requirement for real package-set payloads. Native asset opt-in remains
separate and default-off, with the unchanged ac18 native identity/profile and its
no-VIEW-route/no-writer-guard limitations. No Gradle, APK, helper, native, original
runtime, network, installation or phone workflow was run by this author.

Actual Root preparation `3bdecd` ended zero. Receipt
`firmware/debug-download-app/receipt.json`, SHA-256
`9038e670261cf106e540f8883eeb88c457859f107e5dc1cccaccd0b125390ea0`,
retains 27 inputs/snapshots, fourteen overlay files, the original Gradle inverse,
and 43 saved files plus the receipt. The actual new Gradle file is 58,065 bytes,
SHA-256 `8f8889e0ab8bfb726d25c9155fe35dbb85cbe5ee4d5839c9846af659d3933219`.
The TSV remains the exact 242-row / 17,659-byte `ae4f…` manifest. All twelve other
base overlay files, including native identity and service opt-ins, are unchanged.

Independent saved-output proof
`out/full-apk-remote-assets-review/actual/ACTUAL-OUTPUT-CHECK.json`, SHA-256
`a2e2b9858e3e39db26864676d44c24da049f770d232c14814b0dcdf30752a308`,
verifies the complete 44-file output closure, exact public/source metadata joins,
Gradle inverse and preserved default/script branches without replay. Source gate
is `out/full-apk-remote-assets-review/source/SOURCE-PASS.json`, SHA-256
`9c1f5537da7342e201d949e64633874bce5e7f64bcbcfd8ca32770b13fb86b6e`.
The earlier source-only cards are preserved under
`out/debug-download-app-preparation/history/source-phase-before-actual/`.
Neither this source preparation nor its review fetched or hashed any package
payload or executed Gradle, the app, scripts, native controller or a device.
