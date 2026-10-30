# Adding another guest system

What two ports (ColorOS 17 from the Find N6 and Find X9 Ultra, then Pixel 11
Fold) showed about bringing up a new system: what any image gets for free,
what has to be pinned per build, and what depends on the OS family.

## Any image, no new code

- **Session scripts** (`oneos_switch.sh`, `guest_prepare.sh`,
  `guest_start.sh`, `return_to_oneui.sh`). Image-specific steps detect their
  own files and skip when those are missing. The one split is ColorOS
  (`oplus-services.jar` present, `GUEST_OPLUS=1`) against an AOSP-style
  framework (`GUEST_OPLUS=0`, Pixel's path).
- **Image layout.** guest_prepare.sh runs in One UI's mount namespace, so
  an absolute link inside the image points at One UI's own files. It finds
  the guest's real `system_ext` and `product` folders in either layout
  (`system/product` as the folder with `/product` as a link, or the other
  way round). Before and after its setup it lists the mount points on One
  UI's partitions, and refuses to start the guest if one was added.
  return_to_oneui.sh checks the same before an in-place return. One image
  had `system/product` as the link, and the guest's display config, product
  seapp_contexts and a permissions file landed on One UI's `/product` until
  0.4.16.
- **Safety patches on services.jar** (`scripts/make-overlays.sh`): storage,
  installd ABI proxy, power and BCB, sysrq, vold keys, weaver, biometric,
  gatekeeper, FRP, apexd, app ids from 15000, no new users. Each patcher reads
  both smali flavours seen so far (Pixel's R8 output, ColorOS's non-R8 with
  debug info) and stops the build when a pattern does not match exactly. A
  third vendor's services.jar therefore either takes every guard or fails the
  build; it is never half patched. `scripts/check-dex.py` checks the result.
- **Stage-time guards and tools**: the data bridges, host-state record (FRP,
  gatekeeper, APEX), eSIM guard (any `Euicc*` app), the in-guest OneOS app,
  logs and diagnostics.

## Per build (pinned by SHA-256)

A new build ID of an image already supported counts as a new build here.

- **Guest vold as "gvld"** (needed for Back to One UI without a restart):
  three byte patches in `vold` and one in `service.incremental.so`, plus a
  pin of the crashrecovery APEX once its RescueParty has been read. The
  function addresses come from each binary's `.gnu_debugdata` symbols (xz,
  then `llvm-readelf -s`), the code from the NDK's `llvm-objdump`. Every
  other framework lookup of "vold" has to move too (ColorOS: OPPO's
  `OplusStorageManagerFeature`, `guest_own_vold.py --oplus`). Without this
  the image still runs, and the return reboots.
- **surfaceflinger**: only a SurfaceFlinger with Qualcomm's composer
  extension client needs the composer skip (ColorOS); Google's needs nothing.
- **App data**: `Images.kt` (size, SHA-256), the package set
  (`PackageSets.kt`, `packages/<set>.sha256`, root's `SET_*` lists) and the
  profile's tested flags.

## Per OS family

- **AOSP-style framework** (Pixel). The work was Samsung's vendor side seen
  from a plain framework: the Wi-Fi supplicant choice, services only the
  image's own VINTF declares, the Bluetooth audio HAL's vendor parameters
  (`l_a2dp_format`, SCO opened by the stack), signal-strength polling, the
  LTE attach APN, density and the fold line, Google Play services packaging.
  These now run for every `GUEST_OPLUS=0` image.
- **OEM framework** (ColorOS). Each OEM HAL the framework expects is a
  possible crash on Samsung's vendor: ColorOS's compatibility matrix lists
  101 optional OPPO HALs, and DisplayManager, DefragService, QSPM, gettpinfo,
  the power-key statistics, region features in `my_*` partitions and default
  grants each needed a fix (`docs/coloros-on-fold.md`). Budget weeks for a
  new OEM framework, not days.

## Candidates

MysticGSI has Android 17 patch sets for ColorOS, HyperOS, MagicOS, Flyme
and Pixel.

- **OPPO family** (ColorOS on other phones, OxygenOS, realme UI): the same
  oplus jars, so every ColorOS patch applies. A different build still needs
  its own gvld pins and image entry. Global builds bring Google Play services
  (the Find X9 Ultra IN build did).
- **Other Pixel models**: the same framework; the Pixel patches apply, with
  new pins.
- **HyperOS, MagicOS, Flyme**: new OEM frameworks, so expect ColorOS-sized
  work. MysticGSI's patch sets show what each needs as a GSI. HyperOS's
  framework (miui-services.jar) is guarded and audited (`docs/hyperos.md`);
  it has not had a phone run yet.

Whatever the system, the app shows a new image or build as untested until
it has run on a named phone. Its first sessions run over adb with the owner
watching.
