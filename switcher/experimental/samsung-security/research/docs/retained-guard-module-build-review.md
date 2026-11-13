# Retained guard host module: saved APK review

The independent saved-output review passed for the local debug APK from
packaging run `r-ea9310713eea`. The 131,497-byte APK has SHA-256
`2d05cb9b4f9817894dbdb37724ad9cde4af41fcf77300841169489dbae00bafe`.
The [review inventory](../inventory/retained-guard-module-build-review.json)
pins the actual receipt, binary and saved verification.

The APK has six stored entries. Its 123,968-byte DEX is version **039** and
contains exactly 44 definitions from the reviewed SDK build: 43 host classes
and one shared protocol. The 13 app classes, two compiler-only declarations,
Android/API102 library classes and OEM implementations are absent from the
definition table. DEX framing, checksums and class membership were read from
the binary. The APK carries no native libraries, assets, permissions or app
components. Its binary manifest sets min and target SDK 37; its modern Xposed
metadata sets min and target API 102, static scope `android` and no automatic
hot reload.

Every final stored entry starts at a four-byte-aligned offset. An independent
public-key check verified the v3 signature and recomputed the digest of the
actual APK content. The certificate matches the saved local debug certificate.
A v2 block is present; the saved verifier reports v2 false for its selected
verification, and this review did not independently verify v2.

The 44 D8 inputs match their saved SDK class bytes. The review checked 77
input snapshots against their originals, all 50 staged files and eight tool
identities. The nine saved commands report exit zero, reaped owned processes
and no reader or cleanup errors. D8 reported no diagnostics in this run.

The reviewed entry source refuses an absent or invalid bootstrap request before
hook lookup. A valid request can permit host capture even without an app
profile; the missing profile prevents starting the app link. Neither file is
in the APK or was written by the build. The package and its static scope
metadata establish no device state: this is a PC-only debug build, with no
installation, activation, device acceptance or release signing. The review
read saved bytes without replaying any packaging command or running the
packaged code.
