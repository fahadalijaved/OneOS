# Enable declared module resource values

Status: actual source preparation PASS, not an APK/Gradle or runtime result. The selected app Gradle source
declares the full flavor's `resValue("bool", "retained_handoff_enabled", ...)`,
while `android.buildFeatures` enables only BuildConfig generation. Root's actual
assemble reached Kotlin DSL stage 2, then AGP refused the disabled resource-values
feature. The failure receipt is
`out/full-apk-build/r-50dc28be/assemble-24f86a37/receipt.json`, SHA-256
`5603a198eeeda69a0c9c119cd4a6058c9e532f56142856b677533c5d1bcff305`.

The [AGP 9.4 BuildFeatures API](https://developer.android.com/reference/tools/gradle-api/9.4/com/android/build/api/dsl/BuildFeatures#resValues)
declares `resValues` as a nullable Boolean controlling resource-values generation,
with default false. Actual resolved API artifact `gradle-api-9.4.1.jar` is
419,090 bytes, SHA-256
`f2996c141c2b36dd8a02075395f7abc3d2a7a648d6b08f867700ba88d29b18e8`,
under R50's private Gradle cache. The implementation error names
`BaseVariantFactory.validateResValues`; no compiler flag or global property
override is needed.

The authored `compat/app-integration/enable-app-resvalues.patch` adds one line:

```kotlin
    buildFeatures {
        buildConfig = true
        resValues = true
    }
```

It keeps the real custom resource declaration and its native-asset opt-in
expression. It does not force `retained_handoff_enabled` true, remove validation,
change a flavor, downgrade AGP, or enable any guest/security operation. BuildConfig
generation, all 242 metadata rows, runtime source hashes, native image identity,
NIO aliases, Release/packSets restrictions and default-off behavior remain intact.

The existing producer gains only `--prepare-res-values`, mutually exclusive with
its existing modes. Its old preparation functions remain unchanged. It admits the
exact c061 receipt `firmware/debug-download-guard-app/receipt.json`, SHA-256
`c06164ab0f8e3531f587d9eaa2415fe9f55a860e82939eed19cf761619fabd13`,
and all fourteen saved output pins, applies the fixed patch, and checks both the
full patch inverse and removal of exactly the one new line. Every existing
`resValue(...)` declaration is retained. Only the Gradle output changes; the
thirteen other files remain byte-exact.

The new ignored output is `firmware/debug-download-resvalues-app/`. Its actual
receipt schema is `debug-download-resvalues-app-source-preparation/v1`, status
`SOURCE_ONLY_MODULE_RESVALUES_ENABLED`, with fourteen relative
`overlay/app-android/...` records. The actual Gradle file is 58,295 bytes,
SHA-256 `e78df3840664abf026d3f2e3aeb779d03cc855d526aa86bd85f17e435ffb5653`.
Root ran
`python -B tools/prepare_debug_download_app.py --prepare-res-values` once after source
review. A fresh owned build tree applies only these fourteen files. Existing
c061/9038 outputs, clone, native files and R50 build tree are not modified.

The d3f0 producer, c061 receipt, source/saved review proofs and original guard
cards were preserved before the extension under
`out/debug-download-app-preparation/history/pre-resvalues-d3f0/`; manifest SHA-256
`13c32e04acd9d5ba3f0eda2381ac61d89b01600bdbad933bcb83dcf4a465141d`.
Inputs and source snapshots are checked again before publication; existing
destination or changed bytes refuse without repair/overwrite/retry.

This is a module build correction, not a successful APK build. The same actual
4fb54644 controller / 663,592-byte asset, API31/4-KiB qualifications, absent
app VIEW route and unassembled writer/preprovision/security requirements remain.
Official API documentation was read. No producer, Gradle, compiler, model, app,
script, native, dependency-fetch, installation or phone workflow was run by this author.

Actual Root preparation `e1560b` ended zero. Receipt
`firmware/debug-download-resvalues-app/receipt.json`, SHA-256
`c6c5374388d14d4872ea2300850304edbce7bf5f4735cceac7d245fcd5f31993`,
records sixteen input snapshots, fourteen overlay files and 32 saved files plus
the receipt. The new e78df384 Gradle source differs only by the one resource
generation line, and its inverse reproduces the exact c061 Gradle source.

Independent saved-output proof:
`out/full-apk-remote-assets-review/resvalues-actual/ACTUAL-OUTPUT-CHECK.json`,
SHA-256 `0fb88f7d3560aeef62f4baa1a9e16b05cd74911426c6c44da84a5a41e57dbe06`.
It verifies the complete 33-file closure, source/API correspondence, full inverse,
thirteen unchanged files and retained resource/native/metadata/default flags
without replay. Source gate is
`out/full-apk-remote-assets-review/source/RES-VALUES-SOURCE-PASS.json`, SHA-256
`836458632542ea10ba01115ef0cbdb1a736dcdfecfafe408e231e4b45abc4917`.
Earlier source-only cards remain under
`out/debug-download-app-preparation/history/resvalues-source-phase-before-actual/`.
No compiler, Gradle, app, script, native, model or device ran in this source
preparation or its review. The next real assembly must establish its own outcome.
