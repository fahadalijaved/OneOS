# vivo OriginOS 17 as a guest

The global vivo X500 Pro Max build (V2610_EEA, MediaTek Dimensity k6995,
CP2A.260605.016, Android 17), built with MysticGSI
(the image build (MysticGSI, not in this repository) ... --type originos`, `MysticGSI's patch set/37/originos`: no
device overlays, stock init, nothing debloated). Status: boots on the Z Fold8
Ultra since 2026-11-07 (seventh run, over adb): setup, home, Wi-Fi, sound and
brightness work; no cellular, no fold mode (see Open).

It is the first guest built for a MediaTek phone running on Samsung's
Qualcomm vendor, and vivo's framework is an OEM framework in the ColorOS and
HyperOS sense (`docs/new-guest-systems.md`). The CPU side is like Pixel 11's:
SVE, SVE2 and SME in core libraries, so SM8850 hosts only (the F8U, S26
series); MOPS uses in the linker are runtime-checked.

## How vivo's system_server is put together

`SYSTEMSERVERCLASSPATH` holds `services.jar`, `vivo-services.jar`,
`soc-services.jar`, `services-adapter.jar` and `vivo-service-wifi-ex.jar`.
SystemServer reaches vivo's code through reflection factories
(`ServiceAdapterFactoryImpl`, `VivoSystemServiceFactoryImpl`), and MediaTek's
through `MtkSystemServer`, which loads `/system_ext/framework/mediatek-services.jar`
with its own class loader. Most vivo HAL lookups are `checkService`,
`isDeclared` or `waitForDeclaredService` with a null check, so Samsung's
vendor mostly reads as "feature absent". There is no brand or model gate.

## What reaches the phone's own services, and the guard for each

- **netd.** vivo's `com.android.internal.net.IOemNetd` (44 methods, only in
  `vivo-services.jar`) uses AOSP's descriptor; only codes 1 and 2 are AOSP's.
  Its firewall, routing, socket-destroy and shell-command calls would run
  other methods of One UI's netd. `patches/vivo_guards.py` makes every Proxy
  method throw `RemoteException` at entry; the callers catch it.
- **HAL extensions.** vivo casts the extension binder of One UI's fingerprint
  (`VivoFingerprintProvider`, `AnalysisService`), face (`services.jar`
  `face/aidl/Sensor.initISessionExt`) and power HALs (`UnisocPolicy`) to vivo
  interfaces without checking them: an uncaught `IllegalArgumentException`
  (BAD_TYPE) in system_server, or a Samsung method run with vivo's parcel.
  Each `getExtension()` result now goes through `oneos.vivo.OneOSVivoHalExt`,
  which keeps the binder only when its descriptor starts with `vendor.vivo.`.
- **keystore2.** `VivoLockSettingsServiceImpl` calls
  `AndroidKeyStoreMaintenance.onUserLskfRemoved` twice; the storage guards
  (`guest_storage_guards.py`, also run on `vivo-services.jar`) drop both.
- **vold.** vivo's `IVold` interleaves vendor methods (26 `getDuInfo`, 27
  `rmFile`, ...), so any guest call reaching One UI's "vold" would run another
  method on the phone's storage daemon. The gvld pins (`make-overlays.sh`
  BUILDS) are therefore required here, not optional: `vold` 0x10e24 (the
  string `start()` passes), `try_start`'s `tbz` at 0x83384, and
  `service.incremental.so` 0x6578e. vivo's own IVold calls use the IVold
  StorageManagerService hands them (the guest's gvld). Never run the image's
  `vdc` from the session scripts. vold's `libvdecrypt` recovery path
  (gatekeeper, keystore) is gated on `/system/bin/recovery`, which the image
  lacks.
- **installd.** vivo's `IInstalld` numbers differ too (`rmDataFile` 0x45, a
  vivo method); `guest_installd_abi.py` matched the services.jar `Installer`
  and blocks 48 methods, `rmDataFile` among them.
- **RTC.** On a MediaTek build `MtkAlarmManagerService` replaces AOSP's; its
  power-off alarms program `/dev/rtc0`. `vivo_guards.py` reads
  `startMtkAlarmManagerService()` as false in SystemServer, which then starts
  AOSP's `AlarmManagerService` itself.
- **app ids.** vivo's `AppIdSettingMap.acquireAndRegisterNewAppId` gives
  MediaProvider app id 10000 on first boot (`firstBoot()` reserves index 0),
  rescans from index 0 when full and returns ids restored from `mAppIdsMap`.
  `guest_app_id_offset.py`'s vivo form turns all three to 15000 and up.
- **Properties.** The image's `system/build.prop` sets
  `vendor.rild.libpath=mtk-ril.so`; `guest_props.sh` never adds `rild` keys.
  `ro.vivo.os.version` and `ro.vivo.product.solution` must come from it
  (two vivo classes `Float.parseFloat` the first at boot, uncaught).

Already covered by existing guards: vivo's shutdown animation and
`/sys/power/state` write (`guest_power_guards.py`), sysrq, and `vivo_daemon`
(a root shell service the session never starts; keep it that way, as for
`vivoperfservice` and `vivosymphonyservice`).

## Native

- **surfaceflinger** registers MediaTek's `IMtkSF_ext/default`, a VINTF-stable
  binder only the guest's manifest declares; One UI's servicemanager refuses
  it and the failed `addService` is a `LOG(FATAL)`. `make-overlays.sh` turns
  the descriptor check at 0x657250 into a branch to the binary's own "can't
  start MtkSF_ext" path, which rejoins the main loop. MediaTek's ComposerExt
  client then retries a HIDL service Samsung's vendor lacks (about 2 s at
  init; measure on the phone).
- **Camera.** vivo's `ICameraService` has `setVersionName` (called on every
  open by `CameraManager.openCameraDeviceUserAsync`) and the oneway
  `onFrozenPackage`; both go to the unused code 200. The Java proxy ignores
  `transact`'s result and reads an empty reply, so the open goes on; the
  native `BpCameraService` returns on the error status before reading.

## Google services

GmsCore exists only in `product/apex/com.google.android.gmssystem.prodvic.apex`
(`priv-app/PrebuiltGmsCoreVic@.../PrebuiltGmsCoreVic.apk`), with
`product/priv-app/GmsCore` holding only `m`. That is Pixel's arrangement with
another folder name: `make-overlays.sh` stages the payload and
`guest_prepare.sh` presents the APK in `GmsCore`. Google's setup wizard is the
home activity; vivo's `com.vivo.setupwizard` is its partner customisation and
may show an area picker (vivo's region data lives on a `/vgc` partition the
image lacks).

## First runs on the Z Fold8 Ultra (2026-11-06/07, over adb)

Each failed run returned to One UI in place (no reboot); each fix is in the tree.

1. zygote aborted forking system_server: "Not allowlisted (29):
   /system/system_ext/framework/mediatek-common.jar". vivo's boot classpath has
   four MediaTek jars in /system_ext/framework and its zygote allowlists them by
   that path; MysticGSI's merged image links /system_ext. guest_prepare.sh now
   gives /system_ext its own mount for such images (root overlay + rbind).
2. system_server: DisplayDeviceConfig "Min or max values are invalid" (vivo's
   minimum brightness 7.0E-5 is below the wide curve's first point): the curve
   now starts at 1.0E-5.
3. Watchdog: 31 native camera JSON parses each waited 5 s for vivo's
   media.vivocamera under CameraManager's lock (vivo_guards.py framework).
4. SensorService abort: vivo reads HINGE_ANGLE and LIGHT as "data", One UI's
   HAL sends scalars (libsensorservice_patched.so, two jump table entries).
5. NullPointerException starting Home: VivoMultiWindowManagerService is made
   only with the advanced multi-window feature, which reads as off
   (VivoMwUtils flag set in vivo_guards.py framework).
6. "failed to set system property persist.vivo.qos...": One UI's default_prop
   area was full (196476 of 196608 bytes) after a day of guest sessions without
   a phone restart. The preflight now refuses while it is nearly full.
7. Booted.

## Open

- **No cellular service.** `MtkRIL.isRildReady()` waits for six MediaTek
  radio extension services and retries every second forever. Fix:
  `vivo-telephony-common-platform-ex.jar`, `isRildReady` true once the AOSP
  radio services are registered, without redirecting MediaTek's proxies.
- **IMS.** The default MmTel service is MediaTek's `com.mediatek.ims`, which
  never initialises on Samsung's vendor (about 15 s per slot, then null): use
  the Samsung IMS override, or hide it when that is off. Hide MediaTek's
  telephony helpers too (`com.mediatek.telephony`, `.capctrl.service`,
  `.datachannel.service`, `.atci.service`: 1 Hz retry loops).
- `ro.vivo.comm.share=false` for the session (vivo's virtual modem service in
  the phone process); watch MediaTek's `RadioManager` on airplane mode.
- vivo's vcode telemetry waits forever for its HAL on a background thread
  (`oplus_wait_for_service.py` on `vivo-services.jar`).
- First run: log `/sys/devices/system/cpu/cpu*/core_ctl/enable` before and
  after (vivo's QoS `VCFAPolicy` can write it), and look for "Waited one
  second for" from system_server.
- Fold mode: vivo's features all read as off without its vendor config store,
  so OriginOS runs as the X500 bar phone (phone UI on the inner panel, a slow
  and broken cover/inner switch). Themes and wallpapers list nothing.
- "Processor null GHz %s GHz" in About phone.
- App side: `Images.kt` (a VIVO family), the package set, the root tables and
  the mirror upload.
