# Guarded private-view native and SDK build

Root completed one fresh PC build from producer `ae832d39…`; saved receipt
`out/retained-root-view-guard-build/r-d86f158c/receipt.json` is
`6c67ec7388f1d64e5a82eeb4f17aa7a23880a9d15c3f3a26bc74a8017d841f0a`.
The result covers native compilation/static inspection and SDK javac only.
No emitted native/Java program, Android implementation or model ran in this
workflow; no D8, APK, helper launch, kernel-view preparation or device acceptance
is claimed. Old receipts/models were not replayed against the new producer.

## Actual saved outputs

The AArch64 Android-31 static-PIE artifact is 663,592 bytes:
`oneos_retained_root_view_guard`, SHA-256
`4fb54644c1f97a64e76f057ba69e787aa28de5f9d5f9a9c696873f673f35afaa`.
Its recorded ELF inspection has 11 program headers and 23 sections, no interpreter
or NEEDED entries, non-executable stack, no writable/executable load and
RELRO+NOW. Minimum load alignment is 4096; 16 KiB loadability and target execution
are not established.

Fresh SDK37 javac emitted 57 authored class definitions: 43 host, 13 app and one
shared protocol. The two widget ABI definitions and libXposed API102 remain
compiler-only. A byte-preserving 56-class model-input subset excludes only the
real `RetainedRootOfferSpawn`; preparing it is not a model result. Major version
52 is preserved. The two real read-only availability methods are present in
fresh Module/Binding classes; neither supplies view readiness or admission.

| Recorded command | Exit | Seconds | Diagnostics |
| --- | ---: | ---: | --- |
| Native four-C compile | 0 | 2.516 | Empty stderr |
| readelf inspection | 0 | 0.062 | Empty stderr |
| Widget ABI javac | 0 | 0.578 | Three source/target-8 obsolete-option warnings |
| SDK javac | 0 | 1.188 | Same three warnings |

The command records report their own child reaped and log readers complete,
without reader/cleanup failures. This does not claim descendant or emitted
native-resource drain. Logs and exact argv/environment remain in the receipt.

## Selected source and composition scope

The build captures 33 source inputs, stages exactly 27 compile inputs
(eight native source/header files, 17 Java sources and two ABI sources), and
pins 15 selected NDK files including the actual flock declaration header.
It records 111 captured snapshots. Four native translation units compile the
retained controller, writer-guard GVI, original GVO and mountinfo parser.

Six patches compose in the declared order: native view, host view, post-host
read-only availability, image FD exports, installer FD exports, then writer
exclusion. The readiness patch consumes the exact host-stage bytes before its
own changes. Each individual/ordered step and the full reverse chain are
checked. Fifteen unique targets are composed; six are proof-only inputs,
including four Kotlin/shell overlap targets, the old v1 command and installer
fragment. Those four shell targets are not compiled, packaged or applied here.

The GVI source includes the actual cooperative flock/negative reservation code.
An existing root-protected `/dev/oneos-retained-view` directory and lease are
required. This workflow did not provision or test them. The selected shell
writers must actually participate; the currently unguarded app/old launcher
cohort is not made cooperative by building this ELF. Negative persistence is
limited to the current mounted `/dev` lifetime. HOLD/terminal 3 remain uncertain
and sticky; genuine zero-effect terminal 0 still requires actual drain and all
local closes before exact marker removal. Arbitrary root writers are not isolated.

The availability method observes whether the current captured host link can
accept a view request. It reserves no credit and establishes no native/GVI
readiness; the real action revalidates its guards. Actual
code/loader/root cohort, launch assembly, kernel behavior, legacy completed-return
issuer, terminal-3 kernel release, native authority, Android execution and all
reciprocal security/data/device outcomes remain unresolved.

## Independent evidence

Producer source review is immutable
`out/retained-root-guard-build-review/source/PROMOTION-READINESS-SOURCE-PASS.json`
(`21de95bb…`). Independent saved-output proof is immutable
`out/retained-root-view-guard-build-review/actual/ACTUAL-OUTPUT-CHECK.json`, SHA-256
`460ffb646d34847fd64575b5636941d15f68a3cdf1413cc96bf37de500fae928`.
It checks the actual captured source/snapshot/composition, emitted classes, raw
ELF and four command records without replay. This source/static artifact review
does not supply kernel, model, Android or full-app acceptance. This author only
read saved bytes and did not replay the producer or its commands.
