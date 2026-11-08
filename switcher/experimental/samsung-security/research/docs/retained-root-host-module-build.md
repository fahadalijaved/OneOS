# Retained host module APK

The [producer](../tools/prepare_retained_guard_module.py) packaged the exact
43 host classes and one shared protocol class from the actual SDK build
`6c67ec7388f1d64e5a82eeb4f17aa7a23880a9d15c3f3a26bc74a8017d841f0a`.
Root's PC packaging run completed with exit 0 (`434c76`). The saved receipt is
`out/retained-guard-module-preparation/r-ea9310713eea/receipt.json`, SHA256
`b05b38e8e57006d348c8430e694b7215b346b035783c768da38c4d83f12a37e6`.
It did not recompile production sources or reuse an old module APK.

Independent recipe source review passed at
`out/retained-guard-module-recipe-review/trust/SOURCE-PASS.json`, SHA256
`52f382ffe7a4999b28a16ec437c5485a5a8501fdbdeb0009565ae537344f5604`.
That gate covers source and the captured inputs, not a produced APK.

The local debug APK is
`out/retained-guard-module-preparation/r-ea9310713eea/OneOS-Retained-Guard-Host-debug.apk`,
131,497 bytes, SHA256
`2d05cb9b4f9817894dbdb37724ad9cde4af41fcf77300841169489dbae00bafe`.
Its one ordinary DEX039 has 44 definitions, is 123,968 bytes and hashes to
`f60220d97d1139c507cfc2482cbf577ce544e12548c7813a390496758f0b68d0`.
All nine packaging and verification commands returned 0. The receipt records
77 captured inputs, 50 staged files, eight tools and empty D8 diagnostics.
The six APK payloads are the compiled manifest, `resources.arsc`, that DEX and
the three Xposed metadata files.

The recorded signature verification passed for v3 only, with one RSA-3072
debug signer and certificate SHA256
`81e516ed4312eeb0e0e57bacc55618acff32aabf5f2ee4a14eac256e2ce927dd`.
V2 verification reported false. This certificate identifies the module APK;
the separately pinned OneOS app/profile identities are not supplied by this
artifact. Independent saved-output review passed, including verification of
the public v3 signature and APK content digest. Its proof is
`out/retained-guard-module-build-review/actual/ACTUAL-OUTPUT-CHECK.json`, SHA256
`ab67f57676c439e5841c4bb12f574d84b439cc7eeb62c1743fd0f0f3682fdb58`.

The distinct local package is `com.appleexploit.oneos.security.retainedguard`.
Its SDK37 manifest has no permissions, services, activities, receivers or providers.
It reuses the actual host-bootstrap template's API102 metadata, static `android`
scope, disabled hot reload and single `RetainedPinHostModule` entry. Those files
describe a module; this recipe does not enable it or activate its scope.

Default-off has a precise source meaning: an absent protected bootstrap request
returns before installing the hook or capturing owners. A valid request can
install the hook and capture closed owners even when the separate app profile is
absent. Neither protected file is created or changed by this producer. No UI,
credential operation or guest/security admission is selected by packaging.

The 13 app classes, including the real Spawn, stay outside program DEX. The two
compiler-only widget declarations and libxposed API102 are D8 classpath inputs,
never packaged definitions. The independent class-reference inventory found no
hard references to those excluded app classes; the app service's component name
is an IPC string. Canonical platform/widget/API linkage on Android remains an
external obligation. The APK contains only the linked manifest, optional resource
table, one exact-44-definition DEX and three `META-INF/xposed` descriptors.
No OEM JAR, native controller, request, profile or app assets are included.

Run from the repository root with existing tools, after the source review:

```text
python -B tools/prepare_retained_guard_module.py --package --java-home "<existing-JBR-home>" --android-sdk "../out/toolchain/android-sdk" --api102 "../out/toolchain/libxposed-api-102.0.0/classes.jar" --r8 "out/full-apk-build/r-50dc28be/gradle-home/caches/modules-2/files-2.1/com.android.tools.build/builder/9.4.1/af1135b3a2fd9c7606e2f0e301348147953e49ef/builder-9.4.1.jar"
```

Without `--package` it prints the recipe. There is no additional approval-file
mechanism. Root owns actual tool invocation. Python 3.11+ is required.

The admitted embedded D8/R8 is version **9.4.24**, read as ZIP/property/class data
from the existing AGP `builder-9.4.1.jar`, SHA256
`3ac6cce8e9aaa42683d66cf3b0d10b0bb44e40f9dea4a4db512481e858197b75`.
The old SDK D8 is not substituted. Existing SDK37 aapt2, zipalign and apksigner
and the pinned JBR are used. No dependency download or software installation runs.

The recipe snapshots the actual 44 class bytes, ABI2, compiled Java source inputs,
source/SDK evidence and exact captured helper bytes before executing selected
helper definitions. The command helper is the reviewed `7c55e2c3` revision with
explicit attempted/returned reader-start tracking and bounded retained-process
cleanup. JBR homes, temporary files and a fresh local debug keystore all stay in
an exclusive directory under `out/retained-guard-module-preparation/`; no operator
or release key is accepted. The key is freshly generated, so signatures and APK
bytes are not expected to reproduce between runs.

The recipe requires one DEX with exactly the 44 selected definitions, complete
ordinary DEX or a whole single-header DEX041 container without rebasing, payload
bytes/ZIP CRC closure, aapt2 package/SDK checks, zip alignment and genuine apksigner
v3 verification matching the freshly exported debug certificate. All actual scheme
verification text is retained; enabling v2 in the sign command is not a claim that
v2 verification succeeded. Source/tool/staged bytes are checked before and after.
Every command and failure disposition is recorded; no automatic retries occur.

Evidence inputs are the private saved SDK check
`out/retained-root-view-guard-build-review/actual/ACTUAL-OUTPUT-CHECK.json`
(`460ffb646d34847fd64575b5636941d15f68a3cdf1413cc96bf37de500fae928`),
the class/template inventory `out/retained-guard-module-closure.json`
(`7dcb5f54cfeba23a63f74ecd397dded93b64f3bfe55b903198fee4d0c3fbb494`),
and the precise default-off review
`out/retained-guard-module-defaultoff-review.json`
(`99c8d602d26204c41a2d362342f1184cd55e92604acdb796c8c057e09a58c29e`).

This recipe grants no Android, ART, Vector, native, kernel, authentication or model
acceptance. Cooperative writer provisioning, unguarded older writers, real launch
and namespace admission, lifetime/release and the complete security integration
remain open. A momentary availability query is not GVI readiness or a reservation.

## Guarded host cache-check DEX successor

The current Registry source was compiled in the exact guarded 17-source
cohort. The two compiler-only classes and the other 56 program classes match
the held guarded build byte for byte. Only Registry Metadata changed. The
held native artifact also matches its existing hash.
[Guarded SDK successor](../out/guarded-direct-host-registry-sdk-build/r-f72c2073/receipt.json)

The exact 43 host classes and one shared protocol class emitted a
124,192-byte DEX039 with the same 44 definitions. The 13 app classes and
the compiler-only widget, SDK and API102 definitions stay outside the DEX.
Independent comparison covered all 433 coded methods and found instruction,
frame or try changes only in Registry Metadata's constructor and
`readOwners`. Type, field, method, prototype and class structure match the
predecessor. The three added strings support the two sampled cache checks.
Debug metadata was outside the executable comparison.
[Host DEX successor](../out/retained-guard-cache-identity-d8/r-d4c9cabe3efa/receipt.json)
· [Executable comparison](../out/retained-guard-cache-identity-d8/r-d4c9cabe3efa/executable-delta-readback.json)

The prior signed APK and its DEX retain their exact hashes. The successor is
a standalone, unselected DEX. It still needs a separately verified APK,
matched app and profile, authorized host delivery, and live owner and native
custody evidence.

## Guarded cache-check local APK

The successor is now a 135,593-byte locally signed APK with SHA-256
`18679959bd1615e08bb121a54ea200ee629bfa9975b2e8f57f4c17faa7b53306`.
Its six ZIP members pass CRC and four-byte alignment checks. It carries the
exact reviewed 44-definition DEX. The other five payloads match the held
predecessor byte for byte, including the manifest, resource table and three
Xposed descriptors. The package remains `com.appleexploit.oneos.security.retainedguard`,
SDK 37, static `android` scope, API 102 and hot reload disabled.

SDK verification passed v3 for the manifest's API 37 range and separately
verified v2 for API 24–27. Both checks observed the same fresh debug signer
`f1419f6f…`. The package keeps the prior name and version code with a different
signer, so a differently signed installation has no in-place update path.
The disposable test key was removed. The APK remains unselected for device use.
[Signed build receipt](../out/retained-guard-cache-identity-package/r-7304734f/receipt.json)

The exact stock OneOS 0.4.59 APK has neither `RetainedRootHostServiceV2` nor
`RetainedHostControlProtocol` across its five DEX members.
[Stock app pairing check](../out/guarded-host-stock-code85-pairing-review/r-65e4a405/receipt.json)

## Guarded cache-check PC pairing

The signed host pairs offline for the base V2 association with the held Full
Debug 0.4.58 app (code 75, APK `f47bfe85…`) and its embedded 663,592-byte
controller (`4fb54644…`). The actual app manifest enables the private V2
service after user unlock. The APKs share all 26 base V2 protocol constants
and all eight coded protocol method signatures. The host retains its three
extra view commands and the predecessor's profile parser. The 271-byte
local profile binds the exact app
package, signer, APK digest, version code and controller digest and length.
The parser accepted that tuple and rejected all six malformed variants.
[Profile syntax receipt](../out/guarded-full-debug-host-profile-syntax/r-c2e68d0b/receipt.json)

This Full Debug app lacks the retained Prepare and Stop entry point. It shares
the stock app's package name and root stage, and its signer differs from the
installed release. A package suffix alone would still share the root stage
and lease. The pair remains PC-only and unselected. The host also needs a
real boot phase 1000 transition, so the current no-restart boundary leaves
delivery into the running Samsung framework open. Protected profile loading,
live owner admission, and native controller custody remain unverified.
