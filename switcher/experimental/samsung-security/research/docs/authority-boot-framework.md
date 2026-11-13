# Dedicated authority: selecting a retargeted Samsung boot framework

**Result:** the proposed ContextImpl cut requires a coherent **cold, process-local
boot-framework selection**. A helper on application `CLASSPATH`, a child-loader
ContextImpl, or `-Xint` alone does not establish it. No helper definition, retarget
leaf, boot-image build, selected VM option set or launcher is implemented by this
work. The captured Samsung runtime's effective image/options remain unobserved.

The [inventory](../inventory/authority-boot-framework.json) pins actual captured
paths/hashes, five defining classes, the original callsite and native startup
edges. Eight specifically named boot-image/classpath members were read and
rehash-verified from the existing local tar, approximately20MB; no whole-OS
re-extraction or device pull occurred. Raw files remain in ignored firmware.
Primary AOSP references are pinned to immutable commits and labeled mechanisms,
**not identified Samsung source revisions**. No OEM/native code, loader, VM or
phone action executed.

## Actual captured definition and artifact set

Captured `BOOTCLASSPATH` has61 entries. `/system/framework/framework.jar` is
zero-based index5, after the five ART core jars. The separate system-server classpath has23
entries and includes `/system/framework/services.jar`; placing a helper only
there is not boot visibility. The first core entries reside under the actual
`/apex/com.android.art/javalib/` view. APEX/mount and classpath capture metadata
are pinned independently; these are recorded snapshots, not live installed state.

| Actual captured member | Bytes | SHA256 prefix / disposition |
| --- | ---: | --- |
| `/system/framework/framework.jar` | 54,708,192 | `8095a9aeda27b790…`; original seven-DEX source |
| `/system/framework/arm64/boot-framework.art` | 4,693,440 | `4262c57ea1d0e7c9…` |
| `/system/framework/arm64/boot-framework.oat` | 9,199,744 | `ca8c11e6b94feeba…` |
| `/system/framework/arm64/boot-framework.vdex` | link | `../boot-framework.vdex` |
| `/system/framework/boot-framework.vdex` | 770,156 | `982fb51efdf5d119…` |
| `/system/framework/arm64/boot.art` | 971,840 | `7c76ecf8b1b860ff…` |
| `/system/framework/arm64/boot.oat` | 3,181,064 | `21e63d451881928c…` |
| `/system/framework/arm64/boot.vdex` | link | `../boot.vdex` |
| `/system/framework/boot.vdex` | 112,932 | `72898ec991a5a792…` |
| `/system/etc/classpaths/bootclasspath.pb` | 1,492 | `8827e1a78b744710…` |
| `/system/etc/classpaths/systemserverclasspath.pb` | 283 | `bc397dbefa445a2c…` |
| `/apex/com.android.art/lib64/libart.so` | 15,010,176 | `4166f04af3a71286…`; manifest identity, not executed/reversed |
| `/apex/com.android.art/bin/dex2oat64` | 232,008 | `2f13c3684fb90d86…`; active-path compiler identity only, not executed |

The inspected image prefixes are ART119, OAT275 and VDEX027. These are format
observations only. This pass does not decode image class tables, prove that
ContextImpl is preloaded/compiled in a particular image, identify live mappings
or establish compatible Samsung image-generation tools. Existing strict full-tar
framing/hash evidence is reused; selected members were individually verified.
The capture excludes `/data` ART caches and has no live image-map/VM-option
observation. System image files existing therefore does not prove which image
would be selected. Do not redirect all `ANDROID_DATA` to solve a cache problem:
original credential/storage paths still require their genuine Samsung view.

The exact defining archive index puts ContextImpl, ResourcesManager,
ActivityThread and Resources in `framework.jar/classes.dex`; DisplayMetrics is
in `classes4.dex`, all logical headers0. This is an ordinary DEX039 framework
source. The separate Samsung services DEX041 container is not this patch target.

`ContextImpl.createSystemContextInner(ActivityThread,LoadedApk):ContextImpl`
has original body SHA256
`79ade6efd4199672c182ecff08683769003b3b60413133817aeb6f28227b9fe5`.
At **PC0x26/decimal38**, its three-code-unit INVOKE_VIRTUAL calls
`ResourcesManager.getDisplayMetrics():DisplayMetrics`. Peer work proposes a
same-width static seam consuming the **actual original ResourcesManager** and
returning canonical DisplayMetrics. It has emitted no named helper, method ID,
source-preservation leaf or admitted artifact. The separate two-call display
bridge is not this complete metrics helper.

## Loader visibility and startup mechanism

The pinned AOSP ClassLinker resolves a referenced type using its referrer's
loader; boot-loader resolution searches the loaded-class table and boot
classpath. A boot-defined ContextImpl consequently needs its direct helper
dependency visible in that boot realm. An app main class finding a helper in its
child classpath does not provide reverse visibility or replace a previously
selected ContextImpl. Package-private access also requires the correct defining
loader, not a copied `android.app` package string. These are mechanism findings;
captured Samsung ART internals were not assigned this upstream revision.
[AOSP ClassLinker](https://android.googlesource.com/platform/art/+/6484611fd45e69db9f33f98bfd6864014b030ecf/runtime/class_linker.cc#10184)

Native PCs here are captured ELF addresses, not live process addresses. Actual
captured `app_process64` calls AndroidRuntime.addOption at native PC16820
and AndroidRuntime.start at17816. Captured AndroidRuntime.start reaches startVm
at1991116 and startReg at1991256; AppRuntime.onStarted starts the Binder thread
pool at18792 before callMain18812. These existing static call proofs are reused;
they do not prove effective VM options. The AOSP app_process source provides the
argument-to-runtime-option path and chooses RuntimeInit for standalone entry.
[AOSP app_process](https://android.googlesource.com/platform/frameworks/base/+/1cdfff555f4a21f71ccc978290e2e212e2f8b168/cmds/app_process/app_main.cpp#215)

AOSP AndroidRuntime can add force-JIT/image choices from runtime configuration
or `dalvik.vm.boot-image`, and later adds `dalvik.vm.extra-opts`. The captured
Samsung runtime contains these corresponding strings, including
`-Xforcejitzygote`, but string presence is not branch/option-order proof. A shell
environment variable or Java `-D` property must not be assumed to override a
native Android property. No global property change is proposed.
[AOSP AndroidRuntime](https://android.googlesource.com/platform/frameworks/base/+/1cdfff555f4a21f71ccc978290e2e212e2f8b168/core/jni/AndroidRuntime.cpp#745)

The pinned AOSP parser recognizes explicit full bootclasspath/image/location and
image-compilation options. It treats BOOTCLASSPATH and CLASSPATH as different
defaults, validates file/location list lengths, rejects simultaneous image and
force-JIT-zygote selection, and enables in-memory compilation by default for
zygote. Standalone app_process is not automatically that zygote mode. These
options are candidates to validate against captured ART, not a ready command;
no `-Xbootclasspath/a` shortcut is assumed from a different ART version.
[AOSP option parser](https://android.googlesource.com/platform/art/+/6484611fd45e69db9f33f98bfd6864014b030ecf/runtime/parsed_options.cc#688)

AOSP image loading checks bootclasspath locations/dependencies/checksums. Its
invalid-primary-image path cannot simply generate a replacement without permitted
in-memory compilation and required profiles; an extension may be skipped or
compiled under separate conditions. Do not conclude that deleting/masking an
image necessarily yields a usable VM or that an old OAT/VDEX remains valid for
modified DEX. No captured-Samsung fallback or compiled/inlined-call invalidation
has been demonstrated.
[AOSP image loading](https://android.googlesource.com/platform/art/+/6484611fd45e69db9f33f98bfd6864014b030ecf/runtime/gc/space/image_space.cc#2112)

## Concrete candidate and alternatives

The smallest straightforward packaging candidate is a **complete preserved
Samsung framework.jar with the one reviewed callsite retarget and its uniquely
owned helper definition in the same boot-visible archive**. Keep every other
original definition and canonical framework/native identity. Before any VM
creation, select that archive in its original boot slot through an isolated
process mount/source view, or through an explicitly admitted complete boot
classpath. A separate boot helper JAR is possible only if genuinely included
in the selected boot cohort. App/system-server classpath placement alone fails
this requirement. The helper's complete dependency closure must also be
boot-visible; an app-only extractor referenced directly by that helper recreates
the same problem. A deliberate boot-visible handoff interface to a genuine app
producer would need its own identity, registration and lifetime proof and is not
implemented here.

Two image strategies deserve bounded validation:

1. Supply a coherent rebuilt boot/image/OAT/VDEX cohort for the changed framework
   and relevant dependencies, using the actual compatible tooling/profile. No
   such producer or admitted compiled artifacts exist here.
2. Preserve a verified compatible primary/core image while deliberately loading
   the changed framework/helper from DEX, or validate another explicit cold-DEX
   policy. Its actual Samsung option interactions and image fallback must first
   be proved. `-Xint` changes execution mode; it does not by itself replace loaded
   class definitions. A missing-image path is not an accepted configuration.

Neither strategy may trick checksum validation, reuse stale compiled/inlined
code, redefine the live stock process, edit PID1/global framework/APEX mounts,
or invalidate shared on-device ART caches as an unexplained side effect.
The required observation is the actual selected modified ContextImpl and helper
under one boot loader, not merely a staged JAR/hash or a successful main class.
Keeping original ContextImpl and completing its original DMS protocol is a
different candidate, still bounded by the known full DisplayInfo/policy gaps.

## Process/mount and first-use order

Retain the frozen quiescence requirement: the old authority must acknowledge
real retirement before switch971. The proposed dedicated process slot before
switch1087 remains conditional. Its **final boot-file/image/linker/native view
must exist before app_process starts the VM**, not after ActivityThread or
ContextImpl has loaded. Guest preparation then overmounts selected host data;
guest-start pivots root/derives guest classpaths and may create fresh metadata.
Do not launch this authority from that guest view or let those changes silently
alter its source/state bindings. Mount namespaces do not isolate shared Binder
names or property-service values.

Preserving/launching a VM before preparation also does not supply the genuine
guest display producer yet. If the metrics helper consumes guest DMS projection,
Context creation must wait for its actual admitted producer/order; the helper
cannot fabricate defaults to break a bootstrap cycle. Scope A/B still owe genuine
Context/application metadata, local/user/policy/native owners, endpoint/lifecycle
admission and complete first-effect ordering. The helper/retarget and its real
input owner must be reviewed before any source is selected.

**Current gate remains open:** actual Samsung runtime options/image selection,
new boot artifact production, helper visibility and first-use input ordering
are unmaterialized. No phone/ADB, actual launch, OEM execution, global classpath
edit or bootstrap/recovery acceptance follows. The frozen quiescence card and
parent ColorGlass pause are preserved.

Recheck with `python tools/audit_authority_boot_framework.py`. `--extract` only
reproduces/reuses the eight bounded regular-member reads from the existing tar;
it never runs an OEM executable or changes a runtime mount.
