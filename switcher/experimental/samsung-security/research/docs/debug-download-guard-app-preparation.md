# Fresh guard-controller identity in the prototype app overlay

Status: actual source preparation PASS, not an APK/Gradle or runtime result. The existing
`tools/prepare_debug_download_app.py` gains a distinct `--prepare-guard` mode.
Its original metadata preparation function and other existing functions remain
unchanged. This new mode writes only a fresh ignored
`firmware/debug-download-guard-app/` tree; it does not modify the existing 9038
overlay, held clone, APK build tree, original metadata patch, or native artifacts.

The fixed base is the already reviewed fourteen-file metadata overlay:
`firmware/debug-download-app/receipt.json`, SHA-256
`9038e670261cf106e540f8883eeb88c457859f107e5dc1cccaccd0b125390ea0`.
The actual fresh native/SDK receipt is
`out/retained-root-view-guard-build/r-d86f158c/receipt.json`, SHA-256
`6c67ec7388f1d64e5a82eeb4f17aa7a23880a9d15c3f3a26bc74a8017d841f0a`.
It records `out/retained-root-view-guard-build/r-d86f158c/oneos_retained_root_view_guard`,
663,592 bytes, SHA-256
`4fb54644c1f97a64e76f057ba69e787aa28de5f9d5f9a9c696873f673f35afaa`.
Those exact artifact bytes are verified as data; no ELF is copied into firmware.

Two existing Gradle identity literals change: `retainedHandoffSha256` and
`retainedHandoffBytes`, from the prior `ba532Ã¢â‚¬Â¦` / 659,336-byte image to the exact
fresh build above. The fixed asset, installer and `--host-control-v2` entry stay
the same. Both substitutions require one exact occurrence. The new overlay also
fixes the actual Kotlin DSL compile error observed in Root's closed R50 build:
Gradle's `java` accessor shadows qualified NIO references. Six import aliases
replace exactly fourteen references (Files 7, LinkOption 1, BasicFileAttributes 2,
FileChannel 1, StandardOpenOption 1, ByteBuffer 2). Only symbol resolution changes;
no operation, condition or argument changes. Removing those six imports,
reversing the fourteen names, and reversing the two native literals must reproduce
the entire original Gradle file. All thirteen other overlay files
remain byte-exact, including the 242-row TSV, original payload/script branches,
nine current set lists' source pins, explicit metadata flag and Release/packSets
refusals. No stock-writer patch or app/host Java source is inserted into the APK.

The mode checks the real SDK's compiled-source record and retained staged
`RetainedRootOfferCommand` bytes against the app's actual command. It also checks
that the existing app protocol constants are present in that same SDK's actual
staged protocol source. This establishes the bounded source correspondence used
for packaging; it is not execution, complete ABI/runtime compatibility or a new
authority grant. New protocol operations are not introduced into the app.

Root invoked
`python -B tools/prepare_debug_download_app.py --prepare-guard` once after peer review.
The original `--prepare` mode keeps its prior fixed destination and semantics;
the two modes are mutually exclusive. There is no arbitrary native path, hash or
output selector. All inputs are retained before transformation and rechecked
before the receipt; the fresh output, its fourteen source files, snapshots and
original Gradle inverse are reopened and hashed. Existing output or changed
input refuses without repair, overwrite or retry. Generated ELF bytes remain
only in their existing ignored `out/` path.

The actual new Gradle source is 58,269 bytes, SHA-256
`37a2465a4c071859abb3f5ddc8db7ac0f8a3fc1684f662dcd9a7a640d1a38fbb`.
Static byte-delta evidence is
`out/debug-download-app-preparation/GUARD-NIO-SOURCE-DELTA.json`, SHA-256
`00d1306f88ca6ce2314d527664081efd1c7b5db9dd9aa1ce7a40aa76b1c65cff`;
this is an authored source comparison, not an actual preparation/build result.
The failing build receipt is
`out/full-apk-build/r-50dc28be/home-fix-f4f63102/receipt.json`, SHA-256
`fc9ba550a1bd365d09f8bddbe0381c48561d1486affc9a2fdd04e6e57231f97a`.
The initial 8140 native-only source and cards were preserved before this fix in
`out/debug-download-app-preparation/history/pre-nio-alias-guard-8140/`.

The actual receipt has schema `debug-download-guard-app-source-preparation/v1`,
status `SOURCE_ONLY_GUARD_CONTROLLER_METADATA_RETARGET`, and fourteen relative
`overlay/app-android/...` file records. A future owned assembly copies the held
clone and applies only those fourteen outputs. Native packaging still requires
the separate explicit `oneos.retainedHandoffFile` opt-in, and the download-only
build still requires `oneos.debugDownloadMetadata=true`. Neither option enables
a view or security operation. Omission retains the existing default-off behavior.

The old stock writers cohort and actual guard preprovision remain external.
No app VIEW route, writer protection, prepared-input availability, guest launch,
security admission or successful return is claimed. The native build is an
API31/static PIE/4-KiB source profile, with runtime/16-KiB acceptance and model
transfer explicitly false. Packaging its identity transfers none of those
acceptance results.

Before this producer extension, the exact adce producer, 9038 receipt, 9c1f source
proof, a2e2 saved-output proof, patch and original normal cards were preserved at
`out/debug-download-app-preparation/history/pre-guard-native-retarget-adce/`;
the beforeimage manifest is SHA-256
`ea2e2785399baf9e54cad1ab7bb6fb811c80c2f381c4c2bb024b701f0f3d387d`.
They remain historical evidence rather than claims about the revised producer.
No producer, APK, compiler, model, native, original/runtime, network, installation
or device workflow was run by this author for the retarget.

Actual Root preparation `a0ff09` ended zero. Its receipt
`firmware/debug-download-guard-app/receipt.json`, SHA-256
`c06164ab0f8e3531f587d9eaa2415fe9f55a860e82939eed19cf761619fabd13`,
records nineteen inputs, eighteen snapshots (no ELF snapshot under firmware),
fourteen overlay files and 34 saved files plus the receipt. Exactly thirteen
base files are unchanged. The native identity/alias inverse reproduces the old
9038 Gradle bytes; the actual new file is the exact 37a2465a source above.

Independent saved-output proof:
`out/full-apk-remote-assets-review/guard-actual/ACTUAL-OUTPUT-CHECK.json`, SHA-256
`0e676b76da6ef205042c82c097c32d5f506bd78bebd1d9ee71e4459288f7ebb5`.
It checks the complete 35-file closure, source/native/SDK correspondence, six
aliases/fourteen references, both identity literals, inverse and unchanged
metadata/default flags without replay. Pre-use source gate:
`out/full-apk-remote-assets-review/source/GUARD-RETARGET-SOURCE-PASS.json`, SHA-256
`a13238c7f2c232f55782faeb07bee482f8677f852c758b7b1ba3cfd348fa1067`.
The source-only cards remain under
`out/debug-download-app-preparation/history/guard-source-phase-before-actual/`.
No app, Gradle, compiler, model, original script, native controller or device was
executed by this source preparation or saved-output review. Full APK compilation
and subsequent runtime work still need their own actual outcomes.
