# Isolated full-edition v2 source integration

`tools/prepare_retained_handoff_app.py` prepares a source overlay and patch under
ignored `firmware/handoff-app-integration/`. It accepts only the exact held v1
candidate and v2 component source hashes. It does not edit that checkout, build,
execute a shell/helper, install, publish or change a device. The existing PR,
v1 sources and current clone patch remain separate.

Root completed the data-only preparation once with native v2 build identity
`8dbc9f488daf8ab6422a788d5c67b16e35c4a6d7c4e73ee604f644c4a26c4831`,
603,416 bytes. Receipt `firmware/handoff-app-integration/receipt.json`
(`ecd44cdf…`) records 12 held inputs, 12 source outputs, unchanged input bytes
and no executed targets. The 53,966-byte patch (`22565000…`) passed Root's
`git apply --check` against the held v1 clone without applying it. This is source
preparation and patch applicability, not SDK/Kotlin/Gradle compilation or APK,
installer, Android, native-session or device acceptance. The normal preparer
and setup source remain unchanged from their independent source review.

The full-only authored `RetainedHandoffControllerSetup` checks the actual
BuildConfig pins against BEGIN's expected build, reads only the fixed
`root/oneos_retained_root_handoff` asset, snapshots bounded bytes and verifies
size/hash before feeding root. Its one-shot Attempt retains the actual asset,
feed and result. The generated ServiceV2 calls this typed setup before the real
launch factory, then checks its own delivery-retirement state again. This is an
observed check, not atomic exclusion of birth after retirement: the admitted
startup frame remains retained if retirement races with later creation. A recorded
inverse removes only those two inserted statements to reproduce the held
ServiceV2 bytes. It does not add a caller-ready predicate or supplied Process.

The overlay adds `INSTALL_HANDOFF_CONTROLLER` / `install-handoff-controller`
beside v1. Both use the already retained, serialized SCRIPT_DATA installer path:
verified root-script prefix, then exact native payload and EOF. The same actual
RootShell source is copied unchanged, including process/helper retention and
the no-unknown-retry contour. A permanently claimed install owner still prevents
another installer in that process; v2 cannot bypass an uncertain v1 invocation.

The new shell dispatch calls a separate literal-target copy of the reviewed
installer. Its sole destination is `bin/oneos_retained_root_handoff`, private
work directory is distinct, and its sole success record is
`@@OK closed-handoff-controller-installed`. No caller supplies a filename or
path. It requires existing safe root-owned stage/bin, skips legacy migration,
does not repair/chown existing OneOS paths and never runs the native image.
Matching-image publication is idempotent; a different existing image refuses.
The existing single-digit-descriptor bootstrap is reused unchanged. The new
RootVerbs success comparison requires the exact v2 ACK, full feed, exact byte
count and terminal error/cancel/kill checks. This is a file receipt only.

Full Gradle adds distinct RETAINED_HANDOFF_SHA256/BYTES fields and an asset task
for `-Poneos.retainedHandoffFile`. The generator may pin a separately admitted
native build with `--native-sha256` and `--native-bytes`; those are build identity,
not authority. Without those literal pins an attempted opt-in fails. Without the
Gradle property the asset is absent, BuildConfig is empty/zero and ServiceV2 is
disabled through a full-only boolean resource. Probe has no new asset, service,
source or required native input. The service is non-exported and not direct-boot
aware; actual host user-unlock and source/package checks remain necessary.

The preparer records exact inputs/outputs and inverse byte edits. It refuses
linked/reparse output ancestors and an existing output directory, writes new
files exclusively, and verifies reopened source bytes before its final receipt.
These are bounded local observations, not an atomic namespace lease. It does
not reuse classfiles. The overlay is not a
complete checkout or an accepted APK. Native v2 output, SDK/Kotlin/Gradle build,
manifest/asset readback, installer models, actual image custody, direct-host
peer/pidfd/commit and real switch lifetime remain separate. No guest/security
admission, root readiness, native drain or app-death survival follows from setup.

## Local controller options are Full Debug only

The earlier template enables controller pins, assets and the V2 relay for
every Full variant when a local controller property is present. The existing
debug-download-metadata guard does not cover a build without that unrelated
property. The unmodified build reproduced enabled V2 and populated v1 and v2
pins in the generated Full Release configuration.
[Unmodified Gradle observations](../out/retained-controller-variant-verification/r-55fa6669/receipt.json)

Apply the [Full Debug packaging patch](../compat/handoff-app-integration/retained-controller-full-debug-only.patch)
after preparing the generic v2 source overlay. AGP 9.4.1 also requires the
[resValues prerequisite](../compat/app-integration/enable-app-resvalues.patch).
Apply the packaging patch to an LF source copy. The four Full BuildConfig
fields default to empty hashes and zero lengths, and the V2 relay's resource
defaults to false. An explicit controller option can override only its own
Full Debug fields, alongside the same variant's generated asset source.
Release variants and Probe do not consume either controller option. The
already-pinned guarded writer build remains a separate profile.

The patch and inverse were checked against the generic overlay. The same
three edits were transplanted into a separate copy of the held Full Debug
source tree for actual Gradle 9.8.0 / AGP 9.4.1 checks. Generated BuildConfig
and resources passed with both options, neither option, and each option
alone. Release stayed off and Probe had no controller fields or enable
resource even with both options present. The opted-in V2 Full Debug merge
contained the exact 663,592-byte controller and omitted v1. With both options
present, the generated-asset tasks appeared only in the Full Debug merge
graph. This run verified generated configuration, one actual merged asset
set, and task graphs. Signed release packaging and live behavior remain
unverified. [Gradle verification receipt](../out/retained-controller-variant-verification/r-16a2f1d7/receipt.json)
