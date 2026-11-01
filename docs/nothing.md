# Nothing OS guest: building it, and the three guards that refused

Nothing OS 5.0 as a OneOS guest (0.4.33). Built here from Nothing's own
firmware for the A024 (Metroid), `Metroid_C5.0-260924-2115`, build
`AQ3A.250924.001`, Android 17 / SDK 37. The firmware came from
`spike0en/nothing_archive`, which uploads it as a split 7z.

Image: `out/nothing-local/OneOS_NothingOS5_Metroid.img` (6,067,867,648 bytes),
shipped gzipped as `OneOS_NothingOS5_Metroid.img.gz` (3,276,156,748 bytes).
Package set `nothing-f8u`, `out/overlays_nothing_r2`, 27 files. Not yet run on
a phone.

## The GSI build

the image build (MysticGSI, not in this repository) with `MysticGSI's patch set/37/nothing/`, new here:

- `config.json`: `no_device_overlays`, `add_vendor_stuff: true`, and 23 debloat
  entries. The entries are the ones that exist in this firmware; 7 of upstream
  MysticGSI's `36/nothing` list name folders this build does not have, and were
  dropped rather than left to fail silently. `add_vendor_stuff` is set here
  although upstream's 36 config omits it, because upstream's own script binds
  `/system/mystic/group` and expects it.
- `rw-system-add.sh`: copied from `mysticgsi/patches/36/nothing/` unchanged.

The build worked first try.

## Image layout

`/product` and `/system_ext` are directories at the image root;
`system/product` and `system/system_ext` are **absolute** symlinks to them. This
is the HyperOS layout, not the ColorOS one, so anything that walks the guest
tree must use `GUEST_PRODUCT` / `GUEST_SYSTEM_EXT` / `GUEST_PRODUCT_RO` rather
than `$ROOTFS/system/product`: an absolute symlink read from the host resolves
to **One UI's** `/product`. See `docs/hyperos.md` and the same note there.

## Three guards refused, and why each refusal was right

Each of these stopped the overlay build rather than half-patching. All three
were fixed by teaching the patcher this build, not by loosening the guard.

### 1. `guest_app_id_offset.py`: a bare `nop`

The patcher matches the whole of
`AppIdSettingMap.acquireAndRegisterNewAppId()` as one regex, so a build that
allocates registers differently fails instead of being half-patched. Nothing's
build emits a bare `nop` after the loop's exit label, where the loop index goes
out of scope; ColorOS's and Pixel's do not. The match now accepts an optional
`nop` there.

This is safe because the match is only a *check* that this really is the stock
scan-then-append loop. The patch itself is inserted at the method's entry,
before the first instruction, so a `nop` in the body cannot affect what is
written.

### 2. `guest_no_wipe_secrets.py`: Secretkeeper in services.jar

The patcher refuses any class it does not expect to find the wipe stubs in.
Nothing's `services.jar` carries
`android.hardware.security.secretkeeper.ISecretkeeper$Stub`, which ColorOS's
and Pixel's builds do not. It is now in the allowed set, so the guard covers
it rather than refusing the jar.

### 3. `scripts/make-overlays.sh`: the SurfaceFlinger composer skip

The QTI composer skip is a three-instruction site patched by file offset, keyed
on the SHA-1 of the binary, so an unknown build is refused outright. Nothing's
`surfaceflinger` has the same three instructions at `0x452a50`
(`bl AIBinder_getExtension`, `ldr x8`, `cbz x8 -> +0x4c`,
`bl IQtiComposer3Client::fromBinder`), added as site `e5a8726a6687`.

A hypothesis worth recording as **wrong**: the binary has no
`qtiExecuteCommands` string, which looked like evidence the patch was not
needed. Checking ColorOS's binary killed it — ColorOS lacks the string too, and
needs the patch. It is a vtable call, not a symbol lookup. Shipping on that
hypothesis would have produced a black panel.

## The guest vold ("gvld")

Nothing's `vold` was not in `make-overlays.sh`'s table at first, so the first
overlay set (`r1`) had no `vold_patched` and the guest vold would have taken the
name `vold` — which means no return to One UI without a reboot. `r2` adds it.
The three sites, each confirmed by disassembly:

- The binary's only `"\0vold\0"` is at `0xe1e8`. It has 10 references: one real
  use at `0x64d38` (`adrp 0xe000` + `add 0x1e8`, then `String16` and a new
  `VoldNativeService`), and 9 `__android_log_print` tags clustered around
  `0xa56c0`. Same 1 + 9 shape as the Pixel builds, so renaming it to `gvld`
  changes the service name and some log tags in forked children, nothing else.
- `try_start`'s `tbz w19, #0, +0xd4` is at `0x64728`, immediately after the
  `isDeclared("android.system.vold.IVold/default")` call — that string is at
  `0x14316` — made through the service manager's vtable at `+0x48`. Patched to
  an unconditional branch, the code always takes the not-declared path at
  `0x647fc`, which logs and returns 0 without registering the AIDL instance.
- `service.incremental.so` has the string at `0x64411` with exactly two lookups
  (`adr` at `0xc005c`, `adrp` + `add` at `0xc2714`).

The crashrecovery APEX is pinned with the build because `RescueParty` is the
guest's one remaining call that reaches One UI's `vold`
(`RecoverySystem.rebootPromptAndWipeUserData`), and only while RescueParty is
on. Nothing's `com.google.android.crashrecovery_compressed.apex` holds AOSP's
`RescueParty.isDisabled()` — the same four tests in the same order
(`persist.sys.enable_rescue`,
`persist.device_config.configuration.disable_rescue_party`, `eng`/`userdebug`
build types, `persist.sys.disable_rescue`) — so `guest_start.sh`'s property
check does what it is meant to do on this image.

## Google services

Nothing's GApps are ordinary `priv-app` folders in the image, not an APEX to
present, so the set stages no `gmssystem_payload.img` and `presentsGms` is
false. That makes the image `gmsHideable`: `ONEOS_GUEST_HIDE_GMS=1` covers each
folder with an empty read-only tmpfs, leaving the image untouched.

The six folders are all ones `guest_prepare.sh`'s patterns already match,
verified against the mounted image:

```
product/priv-app/GmsCore          product/priv-app/ConfigUpdater
product/priv-app/Phonesky         product/priv-app/GoogleRestore
product/priv-app/GooglePartnerSetup
system_ext/priv-app/GoogleServicesFramework
```

As with the Find X9 Ultra IN build, the toggle is off by default and is there
for the first runs of an image.

## The smallest set so far

27 files. Nothing's system is close enough to AOSP that `services.jar` and
`framework.jar` carry every guard between them, which is what the ColorOS and
HyperOS sets spend most of their extra guard files on.

There **is** a vendor framework jar — `nt-services.jar`, in system_server's
class path (seen in the first run's `nativeloader` line, 2026-10-30; an earlier
draft of this page wrongly said there was none). It is left unpatched because
nothing in it reaches storage the way `oplus-services.jar` and
`miui-services.jar` do: its only `vold` string is the property prefix
`persist.vold.` in `NtOnlineConfigHelper`, and its one `StorageManager` use is
the framework API (`checkPermissionReadImages`, lock-screen wallpaper), which
goes through the guarded `StorageManagerService`. Worth re-checking on any new
Nothing build before trusting it again.

It is also the first non-ColorOS set to carry `surfaceflinger_patched`.

## Known gap: mobile signal

The signal poll injection (`oneos-telephony.jar`, `OneOSPhoneInjection.apk`) was
**not** built. `/system/product/overlay/TelephonyResCommon_Sys.apk` overrides
`xml/telephony_injection`, so there is no resource to inject into. The guest may
show no mobile signal until that is solved — probably by building an RRO that
outranks Nothing's overlay, rather than by patching the APK.

## Not checked yet

Everything that needs a phone: boot, display (the SF site is reasoned, not
observed), camera, audio, the in-place return, and whether the guest's own
setup wizard behaves. Nothing OS has never run here.
