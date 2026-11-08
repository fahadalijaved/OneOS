# V2 app integration: independent source and saved-byte review

The exact preparer `e7564584…` and setup `067c31dd…` pass the bounded source
review. The root-executed data-only preparation receipt `ecd44cdf…` also passes
independent saved-byte review. This is a source overlay, not an applied checkout,
integrated compilation, APK or runtime result.

All twelve held input identities and twelve written output identities match.
Six recorded inverse edit sets recover the exact original source; the other six
outputs are exact copies. The saved patch equals the diffs between those inputs
and actual saved outputs. The output directory contains exactly twelve overlay
files, that patch and its receipt. The original v1 checkout input hashes remain
unchanged. Root separately reported successful `git apply --check`; this reviewer
did not run a patch command or preparation again.

The generated Gradle hash expression now uses the exact existing valid quoting
shape. Literal v2 pins are SHA256
`8dbc9f488daf8ab6422a788d5c67b16e35c4a6d7c4e73ee604f644c4a26c4831`,
603416 bytes, matching the actual saved native build artifact. The new asset task
is attached only to Full. Absent the opt-in property, the new BuildConfig values
are empty/zero and the non-exported ServiceV2 is disabled; Probe gets no added
source, service or asset source. These are source facts, not APK observations.

The fixed installer retains the existing serialized SCRIPT_DATA shell ownership
and uncertainty handling, with a separate v2 target/work directory and exact
`closed-handoff-controller-installed` file ACK. Typed setup checks the BEGIN
build against Full's pins and the bounded asset before the launch factory.
Its following delivery-retirement check is an observation, not an atomic promise
that later retirement cannot race an already admitted frame. It confers no
source, native-control or guest-authority grant.

The source review closed two defects before preparation: HAI-01 malformed
generated Kotlin quoting, and HAI-02 missing fixed-output containment/readback
guards. The successor rejects existing linked/reparse output ancestry, creates
outputs exclusively and verifies reopened bytes before its receipt. These local
checks do not establish an atomic filesystem lease. The review's first attempt
to snapshot HAI-01 crossed the author's correction; its inaccurate captured-byte
label is preserved and explicitly corrected in the private evidence. The exact
old producer was later reconstructed by the author through an inverse edit and
hash match; no pre-edit capture is claimed.

The saved compile-input map identifies four Kotlin and five Java overlay files
under `firmware/handoff-app-integration/overlay/`. The complete existing app/module
dependency closure is still required. No producer replay, Kotlin/Gradle build,
installer, native/helper, Android/OEM or device execution occurred in this review.
No packaging, real Binder/wire, source custody, cgroup survival, guest operation,
readiness or device acceptance follows from this result.
