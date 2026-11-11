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

## Seventh run's findings, fixed for the eighth (r2 sets, untested)

- **No cellular service.** `MtkRIL.isRildReady()` waited for six MediaTek
  radio extension services and retried every second forever.
  `patches/vivo_telephony.py` drops those six checks in
  `vivo-telephony-common-platform-ex.jar` (bound by guest_prepare.sh, listed in
  guards.txt); MediaTek's own proxies stay empty, so nothing of MediaTek's
  reaches Samsung's modem.
- **MediaTek's telephony helpers** (`MtkTelephonyAssist`, `MtkCapCtrl`,
  `DataChannelService`, `AtciService`, and MediaTek's `ImsService` unless
  Samsung's IMS is in the guest): hidden, 1 Hz retry loops for a vendor the
  phone does not have (`ONEOS_GUEST_MTK_TELEPHONY=1` keeps them).
- **Fold mode.** vivo's switch is `ro.vivo.device.type`, the image's "phone".
  guest_props.sh sets `foldable` for the session on a Fold, guest_prepare.sh
  writes vivo's device states (0 CLOSE, 1 OPEN on the lid switch; Samsung's 3
  reads as folded in vivo's launcher), and `vivo_guards.py services` skips the
  boot state from vivo's hall_status file (missing on Samsung: always OPEN) and
  vivo's sleep on leaving OPEN, so folding moves to the cover.
- **25 s cover to inner.** MediaTek's `libcomposer_ext.so` asked 21 times, 100
  ms apart, for its IComposerExt on every display power-mode change (2.2 s
  SurfaceFlinger stalls). The patched one (make-overlays.sh, pinned by sha256)
  gives up after the first try.
- **Themes and wallpapers empty.** vivo's init.vivo.rc makes `/data/bbkcore`
  (the theme tree) and `/data/vfonts`; guest_prepare.sh now makes the 39
  folders it lists in the guest's staged /data. If Themes still shows nothing,
  BBKTheme's `isVivoPhone` check is next.

- **Host safety (seventh run's health read).** vivo's `setVivoNavBar(false)`
  left `qemu.hw.mainkeys=1` for One UI after the return (no navigation bar until
  a restart): the return now puts it and `vold.has_adoptable` back, and fails
  safe if it cannot. One UI's CPU sets and core control are put back to the
  switch's (vivo's QoS writes them in split screen). A hard reset's recovery now
  deletes vivo's persist props too. vivo adds about 380 persist names at
  runtime: the switch wants 96 KB free in default_prop for it.
- **Processor null GHz.** `framework-adapter.jar` CpuInfoImpl reads the generic
  CPU nodes and shows the highest clock (`vivo_guards.py framework-adapter`).
- `Vivo3rdAlgoService` (ANR loop) and `vdfs` (init refuses its daemon) hidden.

## Eighth run (2026-11-07, r2 set)

Booted. SIM ready and in service (the MtkRIL fix), cover and inner switch at
once (14 IComposerExt lookups instead of 693), About phone's CPU from the
generic nodes. But nothing could be used:
- **vivo's launcher exited at every start** ("LauncherApplication
  unSupportCurrentPlatform", 85 starts): BBKLauncher2's install-compatibility
  deviceType list is "phone|flip|tablet", and fold mode makes the device type
  "foldable". `patches/vivo_launcher.py` answers that check yes
  (BBKLauncher2_patched.apk, the X500 Pro Max build's APK only).
- **SystemUI died 17 times**: "Writable dex file ... MagazinePlugin.apk is not
  allowed". guest_prepare.sh's `chmod -R 777` of SystemUI's data at every switch
  made the plugin APK vivo's SystemUI kept from run 7 writable, and Android 14+
  refuses to load a writable dex file. Code files (apk, dex, jar) there are
  read-only again after that sweep (every image).

## Ninth run (2026-11-07, r3 set)

The session property store worked (377 guest persist props blanked, One UI's
store untouched) and SystemUI stayed up. The launcher, let through its device
type check, crashed in its foldable paths: `ClassNotFoundException:
AllGroupsRecyclerView` inflating `all_groups` (75 crashes), classes R8 removed
from the X500 Pro Max's phone build. r4 keeps the launcher a phone's launcher
while the rest of the system is foldable: framework.jar `FtDeviceInfo.getDeviceType()`
answers "phone" in the launcher's process, and the launcher's three direct
`ro.vivo.device.type` reads point at a property no build sets.

## Tenth run (2026-11-07, r4 set, no restart needed)

The second session of the boot reused the first one's property slots. The launcher
stayed up (a phone's launcher on the inner panel), but the owner found it slow,
glitchy, "between a fold and an unfold UI", and without OriginOS's glass:
- **Slow:** the image says `ro.dalvik.vm.enable_uffd_gc=false`, so its boot image
  is built for the CC collector (read barriers); One UI's `true` made the guest's
  zygote run CMC and refuse it ("ValidateOatFile found read barrier state
  mismatch"), so the whole framework ran on the JIT. guest_props.sh now uses the
  image's value for the session when it differs.
- **No glass:** vivo's material SDK draws glass only when system setting
  `realtime_blur_state` is 1 and reads an unset one as 0; vivo's first boot sets it,
  the guest's never did. guest_start.sh sets it to 1 while unset.
- **Fold UI:** this is a bar phone's image; its launcher has no unfolded UI. Owner's
  decision: OriginOS becomes a slab (bar phone) system; fold mode stays in the tree.

## Runs 11 and 12 (2026-11-07, slab mode: ONEOS_GUEST_VIVO_FOLD=0)

Still no glass, apps took seconds to open, touch about 2 s late:
- **JIT Zygote:** with the collector right, ART still refused the image's
  boot-framework.oat ("dex file checksum": OneOS's framework_patched.jar) and the
  system_server odex (services_patched.jar). guest_start.sh now runs the image's
  own odrefresh before the zygote (artifacts in the stage's
  /data/misc/apexdata/com.android.art). Run 12's odrefresh aborted at once:
  "assertion hasLastUpdateMillis() failed", because guest_prepare.sh had stripped
  lastUpdateMillis from the ART entry of the guest's apex-info-list. Kept now,
  and every active entry gets one.
- **Heat:** the in-memory compiling ran the skin to 50 °C within a minute, so the
  heat cap held the CPU at 50-65 %.
- **No glass:** realtime_blur_state was 1 this time (vivo's TouchLight read it),
  but vivo's blur asks `FtFeature` and `QoSFeature` for vivo.software.realtimeblur,
  nativeblur and windowdeformblur, all off without vivo's config store.
  vivo_guards.py framework answers those three yes (r5); vblurnpu (MediaTek's
  APU) stays off.
- 48 touches dropped as "untrusted" under vivo's transition snapshot window
  (BLOCK_UNTRUSTED) while transitions crawled.

## Open

- vivo's vcode service waited for its HAL once a second: fixed for CN in r9
  (`vivo_no_wait.py`: vcode, vlight, sectee); the twelfth CN run had none.
- Bluetooth crashes once at its first start (a command complete with an empty
  callback in `HciLayer`). The twelfth CN run's tombstone registers name the
  command: `HDT_CMD(0xfc5b)`, MediaTek's vendor "HDT" (high data throughput)
  features read, which Samsung's Qualcomm controller answers differently. The
  restarted stack works. Next: keep MediaTek's HDT read from starting (its
  callers are in the stripped `libbluetooth_jni.so`; strings
  `read_local_hdt_features_handler`, `on_hdt_cmd_complete`).
- Property space: fixed for every system after the eighth run. A tmpfs copy over
  /data/property from the moment One UI's framework is down (guest_props.sh
  store-on) keeps the guest's persist settings out of One UI's store, so the
  return blanks them in memory and the next session reuses their slots. Only the
  first OriginOS session after a restart still costs about 95 KB of default_prop.

- `ro.vivo.comm.share=false` for the session (vivo's virtual modem service in
  the phone process); watch MediaTek's `RadioManager` on airplane mode.
- Log `/sys/devices/system/cpu/cpu*/core_ctl/enable` before and after (vivo's
  QoS `VCFAPolicy` can write it), and look for "Waited one second for" from
  system_server.
- vivo's features: answered from the vendor's vivo_config.ini since r9.
- App side: `Images.kt` (a VIVO family), the package set, the root tables and
  the mirror upload.

## OriginOS 6 CN (PD2609MA, k6993v1_64, 2026-11-07)

The CN full OTA (vos 17.0, Android 17, 2026-09-01), set `out/overlays_originos_cn_r2`.
Every per-build pin redone for its binaries; no guard skipped:
- gvld (`BUILDS`): vold "vold" at 0x10e40 (its only `\0vold\0`; the other 25
  references are log tags), try_start's tbz at 0x83384 as in the global build;
  service.incremental.so is the global build's. Its crashrecovery APEX
  (uncompressed, AOSP) has AOSP's RescueParty.isDisabled, checked by all four
  observer entry points.
- surfaceflinger: the global build's MtkSF_ext site 0x6060 later (0x65d2b0).
- libsensorservice: the same jump table at 0x18250 (LIGHT, HINGE_ANGLE -> scalar).
- libcomposer_ext: the global build's, byte for byte.
- Signal poll: vivo's what=7 re-queues its own poll after AOSP's
  getSignalStrength while the screen is on. `aosp_signal_poll_check.py` accepts
  that tail only when it calls nothing but reads, its log and
  queueNextSignalStrengthPoll, and that method removes pending what=7 before
  queueing one (OneOSSignalPoll's 20 s tick cannot start more chains).
- BBKLauncher2: `vivo_launcher.py` patches the CN APK as is. guest_prepare.sh binds
  a patched launcher only over the APK it was made from
  (`BBKLauncher2_patched.apk.src_sha256`), so a global set never lands on the CN
  image or the other way round.

### First CN run (2026-11-07, r2): system_server died making WifiService

The storage pins held (the guest's vold registered gvld, One UI's vold kept
"vold"), SurfaceFlinger and the zygote came up, and the session returned in place.
system_server died 7 s in: `VivoWifiInjector.<clinit>` added transport 11
(`TRANSPORT_EXTWIFI`, vivo's second Wi-Fi station) to a NetworkCapabilities
builder, and One UI's connectivity module, which the guest keeps (its BPF maps are
One UI's netd's), only knows transports up to 10. The CN wifi APEX is vivo's own
and loads `vivo-service-wifi.jar` (the global image's was Google's, without it).
r3: `patches/vivo_wifi_connectivity.py` gives the three classes that set
TRANSPORT_EXTWIFI vivo's overseas value (1, what vivo itself does on Google's
module), points the 8 literal transport-11 requests for the second Wi-Fi at
TRANSPORT_TEST (matches nothing), and replaces the five calls to methods only
vivo's CN connectivity module has (sendNetworkInfoInternal -> sendNetworkInfo;
explicitlyClear, flushDnsCache dropped; setExemptedFromVpnFiltering,
updateThirdAppAccLimit false). Comparing the image's copies of every module the
guest takes from One UI (tethering, ipsec, media, statsd, scheduling, uwb,
devicelock, uprobestats, npumanager) with One UI's: no other boot or
system_server class path code uses a member only the image's copies have.

Also seen: odrefresh's boot image was built without read barriers while the zygote
ran CC (`ro.dalvik.vm.enable_uffd_gc=false`), so the zygote refused it (slowness,
not boot); open. guest_start.sh printed odrefresh's exit codes swapped (80 is
compiled, 81 failed): fixed.

### Second CN run (r3): system_server reached enable_screen, then died

Wi-Fi came up; 8 s later vivo's app freezer (`vivo-services.jar`,
`am.frozen.state.SystemState.systemReady`) asked for transport 11 too. r4:
`vivo_wifi_connectivity.py services` on vivo-services.jar (a scan of the whole boot
and system_server class path found no other literal transport 11), and vivo's
"EXTWIFI" NetworkInfo / NetworkAgentConfig legacy type 38 (One UI's NetworkInfo
throws above 18) becomes TYPE_WIFI.

### Third CN run (r4): home screen for ~15 s, then system_server died

Booted to vivo's home. Then `libvivowifi-service.so` (vivo's wifi APEX) failed to
load: "libnativehelper.so not found ... in namespace com_android_wifi". The guest
runs on One UI's /linkerconfig, whose wifi namespace follows One UI's wifi manifest;
vivo's requires libnativehelper.so (and vivo's bt APEX libandroid.so). r5:
make-overlays.sh writes each payload's requireNativeLibs (oneos-apex-requires.txt),
and guest_prepare.sh binds a guest-only ld.config.txt that adds the missing links
of the payloads it mounted, through the namespace the others take each library from
(as linkerconfig would); One UI's /linkerconfig is untouched.

### Fourth CN run (r5): home again, then a native abort in system_server

The guest linker config worked (6 links; vivo's wifi JNI library loaded). Then
`VivoTrafficStats` (framework-wifi.jar of vivo's wifi APEX) read Wi-Fi traffic
counters through the APEX's own libnetworkstats.so from the kernel's stats BPF
maps, which One UI's bpfloader pinned with its own layout:
`BpfMapRO::abortOnMismatch`, SIGABRT in system_server. r6:
`patches/vivo_traffic_stats.py` sets the class's IS_OVERSEAS (vivo's overseas
builds return 0 or an empty StatsDetail in all 35 methods before any native read;
checked per method), and guest_prepare.sh binds framework-wifi_patched.jar with
vivo-service-wifi_patched.jar. framework-wifi.jar is on the boot class path, so the
guest's odrefresh recompiles its boot extension once.

### Fifth CN run (r6): boots and stays up

The fourth run's fixes held: no system_server death in four minutes; Wi-Fi joined,
the SIM was there, odrefresh compiled (102 files, 6 s). Two problems:
- **vivo's setup wizard** (`com.vivo.setupwizard`, the image's only one) stopped at
  its vivo account step. guest_prepare.sh now marks setup done before boot for vivo
  images (device_provisioned, user_setup_complete, setup_wizard_has_run, which
  vivo's wizard reads from Secure then System); ONEOS_GUEST_VIVO_SETUP=1 keeps it.
- **The cover stayed black** (slab mode, vendor device states 0/3). The framework
  moved display 0 to the cover (port 148) on folding and powered it, but vivo's
  SurfaceFlinger ("ResSwitch") kept the inner panel's projection. Open.

### Sixth CN run (r6, fold mode: ONEOS_GUEST_VIVO_FOLD=1)

The cover works in fold mode (vivo's device states 0/1). vivo's setup wizard came
back although setup was marked done: its LaunchActivity is a HOME activity that
only the wizard itself disables when it finishes. guest_prepare.sh now hides
/system/priv-app/SetupWizard (checked to be com.vivo.setupwizard) while setup is
marked done; ONEOS_GUEST_VIVO_SETUP=1 keeps both.

### Seventh CN run (r6, fold mode): setup skipped, launcher exits

vivo's wizard stayed hidden. BBKLauncher2 exited at every start (57 times) and asked
to uninstall itself: its install-compatibility deviceType is "phone|flip", and
vivo_guards.py's FtDeviceInfo "phone" answer matched only the global build's
launcher process (com.android.launcher3); the CN launcher is com.bbk.launcher2.
Both names now. guest_start.sh also sets the three provisioned keys after boot
when vivo's setup is skipped (a fresh /data has no settings files to seed).
The stage's guest /data was the global image's (shared since 11-06): to be moved
aside for a clean CN start.

### Eighth CN run (r7, fold mode, fresh guest /data)

system_server died 30 s in: NetworkStatsService "Cannot write into stats data
directory: /data/misc/apexdata/com.android.tethering/netstats". The guest has no
apexd/vold to make /data/misc/apexdata/<module>, and guest_start.sh's odrefresh step
(11-07) had created /data/misc/apexdata as root's 755 after guest_prepare.sh's
chmod pass; the old (global) /data had the dirs from before. guest_prepare.sh now
makes misc/apexdata, misc_ce/0/apexdata and misc_de/0/apexdata/<module> for every
module name (One UI's and the image's) before that pass.

### Ninth CN run (r7, fold mode, fresh /data): auto-brightness

Up two minutes, then system_server died in vivo-framework's
`BaseNitCurve.calcNitBrightnessUnFold` (NullPointerException on the light sensor
thread): with the device state above 0 (fold mode's OPEN; the vendor's 3 in slab
mode too) vivo's brightness code takes "unfolded" tables a phone build lacks;
automatic brightness is on by default on a fresh /data. r8:
`patches/vivo_brightness.py` keeps SensorInfo.getDeviceState(),
InfoManager.getDeviceState() (brightness and sensor callers only) and
BrightMapping's state at 0 in vivo-framework.jar (phone builds), bound by
guest_prepare.sh. A full sweep of the run (every crash, every caught exception in
system_server, native crashes, ANRs, fold-related traces in runs 6, 7 and 9) found
nothing else fatal: cell broadcast's background start refusal, vivo's pinyin SQL
bug and the IOemNetd guard refusals are handled.

### Tenth CN run (r8): stable 8.5 minutes; slow app open/close, missing features

Stable (returned with the keys). A full read of the log found:
- **~2 s on every launch from or return to home:** vivo's launcher plays those
  animations in vivo's animation server, `vivonrtservice` (`vivo_nrt_service`), which
  vivo's init starts and the guest never did ("AnimationServer: Service.INSTANCE is
  null"; the recents transition then waited 1.98 s each time). guest_start.sh starts
  it as system.
- **157 000 MediaTek frame-hook failures** (libgui's libged_kpi/libdisp_dejitter on a
  Qualcomm phone; logd dropped 1 219 times): both libraries hidden from the guest.
- **54 617 failed vivo config store lookups; every vivo feature off.** system_server's
  VivoConfigStoreHelper now reads the vendor's vivo_config.ini (as
  /data/system/oneos_vivo_features: 168 features on, 42 hardware ones off).
- **Fold mode broke vivo's apps** (Themes crashed twice: a phone build in foldable
  paths). Mode 2 (`ONEOS_GUEST_VIVO_FOLD=2`): ro.vivo.device.type stays "phone";
  SurfaceFlinger, libinputflinger, libinputservice and libandroid_servers read
  ro.oneos.vivo.dtype ("foldable") instead, so both panels work.
- **Double tap to wake never armed:** vivo's AOD keeps the panel lit and is not
  doze_always_on; on vivo every guest sleep now counts as AOD for the keeper.
- The launcher restarts itself on each fold (density change): vivo's own behaviour.

### Twelfth CN run (r10, mode 2, after a phone restart)

Booted; app opening and closing seamless (vivo's animation server); the cover works
in mode 2; Bluetooth lists devices. Brightness stuck: vivo-services'
VivoLcmBrightnessController saw vivo.software.brightness.unified_mapping on (the new
feature list) and waited for SurfaceFlinger to load the panel's tables, while
SurfaceFlinger, asking vivo's (missing) config store HAL itself, read it off ("new
brightness path feature is not configured"): "lcm json not load", the LCM target
stayed 0.5. make-overlays.sh now leaves off every feature a system binary using
the config store names (six: brightness.unified_mapping, brightness.policy,
motionblur, immersive.v2, sleep.screen, nightwakeup.brightness).
Themes, wallpapers and home style (all com.bbk.theme, /system/custom/app/BBKTheme)
crashed four times, all from one cause: Themes decides "not a vivo phone" from
ro.product.system.manufacturer (isNoVivoPhone, in two copies), which is One UI's
samsung in the session ("judgePhoneManufacturer: manufacturer = samsung"), and then
runs as an overseas build: vivo's global servers, and overseas layouts the CN build
does not have (VTitleBarView inflated Resource ID #0x0, CuteResListFragment lost its
adapter, the overseas Settings entrance layout has no view 0x7f0a0af1). The
getRealid warnings were noise. guest_props.sh now gives vivo images their own
ro.product.system.manufacturer and ro.product.system.brand (vivo) for the session,
restored on return (ONEOS_GUEST_VIVO_MAKER=0 keeps One UI's); BBKMusic,
FingerprintSettings and VivoBrowser read the same key. ro.product.manufacturer and
ro.product.brand (Build.MANUFACTURER, Build.BRAND) stay the phone's.
The eleventh set's build stopped silently in the native feature scan: the config
store's own libraries name it but no feature, and grep's "no match" ended the
script under set -e (fixed).
Also in the log: Bluetooth crashed once at start (HciLayer, a command complete with
an empty callback, right after MediaTek's bredr_startup; the restarted stack ran
the same path without a crash), Google's CellBroadcastReceiver twice at boot
(background service start refused). The first odrefresh --compile fails as
expected; --force-compile then builds the boot image.
Still open: SMS (no IMS in the guest), the Bluetooth start race (needs the opcode).

### Before the thirteenth CN run: branch originos-0471, set r12 (2026-11-09)

OriginOS was parked while 0.4.60 to 0.4.71 shipped from `rel-0461`. Branch
`originos-0471` is `next` (the OriginOS work) with `rel-0461` merged in, so an
OriginOS session runs the current session scripts: the softdog feeder fix
(438e75c1: the feeder no longer exits after its first kick, the 0.4.66 panic a few
minutes into every session on Snapdragon Galaxies), the guest's own /mnt with its
storage folders, Dolby on the music output, the S23 libsec-ril SMS pattern,
installd tables per SDK, the system_ext bind farm for 5.10 kernels, Vulkan
RenderEngine on MediaTek/Exynos (OxygenOS only), Restore now, FRP's PDB start in
every set, and 0.4.71's (One UI's dumpstate stopped during a session, the Zygisk
Next warning). Conflicts: the app, set, test and docs files take the release branch's;
make-overlays.sh keeps both new gvld entries (OriginOS 6 CN, OxygenOS 16).
OriginOS stays out of `rel-0461` and every release.

Set `out/overlays_originos_cn_r12` (make-overlays.sh from this branch on the same CN
image, `VIVO_CONFIG_INI` = the CN vendor's vivo_config.ini; log
`out/originos/make-overlays.cn12.log`, exit 0). Same pins and the same 51 files as
r11; new from the merge: the FRP PDB start guard (`guest_pdb_init_survives`), the
sound-trigger no-reboot guard and the installd table picked by the image's SDK (37).
The log's only "not built" lines are the Wallpapers grid overlay (as in every vivo
build) and the guest app, which a worktree does not build: `OneOSGuest.apk` is the
released one (sha256 bd03c424..., the same in r11, infinityx r14, hyperos r25 and
oxygen16 r2; no guest app change since). Check: the 9 guarded files match
guards.txt (sha256 of guards.txt 7d4d64be206380f0...); against r11 only the rebuilt
jars and guards.txt differ.

Read again from the twelfth CN run (r10, F8U, 00:12 to 00:17, returned with the keys)
and fixed in the session scripts:
- **The guest's boot image was refused all along.** The zygote ran CC (the image's
  `ro.dalvik.vm.enable_uffd_gc=false`) and refused the guest's own boot image:
  "ValidateOatFile found read barrier state mismatch (oat file: false, runtime:
  true)", so the framework still started without a usable boot image. The artifacts
  in the stage's /data were made for CMC in an earlier session; `odrefresh --compile`
  checks the jars, not the collector, and `oneos_gc` was written whatever odrefresh
  did. guest_start.sh now reads the boot image's own `concurrent-copying` key (oat
  header) before and after odrefresh, removes artifacts made for the other
  collector, compiles once more if needed (bounded), and never leaves the zygote a
  boot image it would refuse. The log line names both values.
- **Fold mode 2 is the default** (`ONEOS_GUEST_VIVO_FOLD` unset = 2: the apps stay
  a bar phone's, SurfaceFlinger and input see both panels). Mode 1 broke vivo's
  apps (Themes). On a bar phone (`ONEOS_GUEST_FORM=phone`) everything is "phone".
- **Density on a folded start (F8U).** WindowManagerService gave the cover the inner
  panel's forced density at boot (cover 420 after every fold), and a first session
  started folded left the inner panel at 480. For vivo the UI activator now resets
  the cover's density when it is the one OneOS set, and sets the inner panel's at
  the first unfold (a density chosen in the guest stays).
- **MediaTek's IMS stays hidden with Samsung's IMS on** (`ONEOS_GUEST_SEC_IMS=1`, the
  plan for SMS): `com.mediatek.ims` is a persistent app in the phone process with
  the MMTEL, emergency and RCS features, so the guest's ImsResolver would bind it
  before the UI activator moves both slots to Samsung's. Every session that worked
  ran without it. `ONEOS_GUEST_MTK_TELEPHONY=1` keeps it.
- vcode/vlight waits: none in the twelfth run (r9's `vivo_no_wait.py`). Untrusted
  touch drops: none (the transitions are fast since vivonrtservice). Glass:
  `realtime_blur_state` was set and the blur features answered yes; whether glass
  shows is for the owner to see.

#### Host check: Z Fold8 Ultra, S26 Ultra, S25 Ultra

From the reports inbox (probes of 11-08 and other systems' sessions, 0.4.62-0.4.70):

| | Z Fold8 Ultra (f8u) | S26 Ultra (s-ultra-8850) | S25 Ultra (s-ultra-8750) |
|---|---|---|---|
| SoC, CPU | SM8850, SVE/SVE2/SME | SM8850 (canoe), SVE/SVE2/SME | SM8750 (sun), no SVE/SME |
| Kernel, vendor API | 6.12, 202504 | 6.12.69, 202504 | 6.6.127, 202404 |
| Panels | 147 inner + 148 cover | 147, 1440x3120, One UI density 600 at WQHD | 147, 1440x3120 (1080 FHD+ in One UI) |
| Softdog | /dev/watchdog (watchdog0) | /dev/watchdog (watchdog0) | /dev/watchdog (watchdog0) |
| Inbound SMS patch | libsec-ril pattern | patched at 4208992 (0.4.70) | patched at 4123036 (0.4.66) |
| BT audio | Android factory | Android factory | Samsung's factory only: oneos_btaudio bridge |

- **CPU (S25 Ultra):** the CN build is `sys_mssi_64_64only_cn_armv82`. A scan of the
  image (llvm-objdump with SVE/SME on every library in /system/lib64 and
  system_ext/lib64, and libutils, libbinder, libhwui, libgui, libandroid_runtime,
  surfaceflinger, app_process64, servicemanager, the boot oat files) found no SVE
  in the core: only libjxl (Highway, runtime dispatch), MediaTek's TFLite and a few
  app libraries (Baidu maps, video SDKs), and scattered kCFI words elsewhere. Unlike
  the global X500 Pro Max build (SM8850 only), the CN image can run on SM8750; an
  app using those libraries may still stop with SIGILL there.
- **Bar form (S26 and S25 Ultra):** never run before. Everything vivo-specific for
  a Fold is gated on `ONEOS_GUEST_FORM=fold` (device type, vivo device states, fold
  cutout, fold density); with `phone` vivo keeps its image's "phone" everywhere,
  the density comes from One UI's dp scale, the status bar from One UI's cutout.
- **Property space:** the first OriginOS session after a phone restart wants 96 KB
  free in default_prop (preflight); it refuses with "restart the phone" otherwise.
- **Older vendor (S25 Ultra):** Android 15 vendor, no HIDL-only HALs in its sessions
  (no hwservicemanager stand-in needed), Samsung's Bluetooth audio factory only
  (the bridge serves the AIDL one; guest_props turns LE Audio off).

#### Host check: the Snapdragon S24 and S23 phones (0.4.82, no session yet)

Offered from 0.4.82 at the owner's request (2026-11-10), untested: the Galaxy S24 Ultra
and S24 (SM8650) and the S23, S23+ and S23 Ultra (SM8550). Not the FE phones; the Exynos
S24 and S24+ followed in 0.4.83 (the next section). The profiles' choices and the root script's
pair table (oneos_root.sh) name them; nothing in the set or the session scripts
changed for them: no OriginOS step depends on the vendor's generation, and the S25
series' download already carries the set.

| | S24 Ultra, S24 (s-ultra-8650, s-8650) | S23, S23+, S23 Ultra (s-8550, s-plus-8550, s-ultra-8550) |
|---|---|---|
| SoC, CPU | SM8650, no SVE/SME | SM8550, no SVE/SME |
| Kernel, vendor API | 6.1, 34 (Android 14) | 5.15, 33 (Android 13) |
| Display composer | composer3 (AIDL) | HIDL only (composer@2.4, IQtiComposer@3.1) |
| Audio HAL | HIDL | HIDL (audio@7.1::IDevicesFactory, S23 Ultra report 13ca27fb) |
| Other systems there (reports of 0.4.72-0.4.74) | S24 Ultra: Pixel 9 Pro XL started and returned (5e326061); its ColorOS 17 sessions ended in a stop after 50 s or a restart (7bb37deb, fd7d9016, 2d35388e, 753bfda9) | ColorOS 17, Pixel 9 Pro XL, HyperOS: started and returned |

- **What the image holds for an older vendor** (a scan of the .img.gz stream for file
  names and interface names, 2026-11-10; nothing was run): `libaudiohal@6.0.so`,
  `@7.0.so` and `@7.1.so` next to `libaudiohal@aidl.so`, with
  `android.hardware.audio@7.1.so`; `android.hardware.graphics.composer@2.1.so` to
  `@2.4.so`; `android.hardware.radio@1.0.so` to `@1.6.so`. The set's
  `surfaceflinger_patched` links composer@2.1 to @2.4 and has the HidlComposer client.
  The CN build has no SVE in its core (the S25 Ultra check above).
- **The session's own steps for these phones are the ones the other systems use:**
  the hwservicemanager marker for HIDL-only HALs, the per-SDK installd tables, the
  system_ext bind farm, the property store (every system from 0.4.81), the
  black-screen auto-return (the S23s keep their "will most likely not start" note).
- **Not known until a session report:** vivo's SurfaceFlinger on the HIDL composer
  (its vivo composer3 extension and MediaTek's `libcomposer_ext` have only met an
  AIDL composer); vivo's audio policy with Samsung's vendor policy file (which file
  it loads, whether the Bluetooth modules are in it: the policy overlay in
  guest_prepare.sh is HyperOS only); the radio and camera on the older HAL versions;
  how long the first start's odrefresh takes on these chips.
- **First report from one of them:** `sessionApp` 0.4.82 or later, then the outcome,
  `composer_before_sf.log`, the first SurfaceFlinger lines of the boot log, the
  audioserver's "DevicesFactoryHal" and "APM" lines, and the odrefresh line in
  takeover_inner.log.

#### What the first reports showed, and the 0.4.85 switch (not yet run on one of them)

Nine OriginOS reports of 0.4.83 from the S23 and S24 series (S23, S23+ x2, S23 Ultra x3,
S24 Ultra x3): every one ended "The other system stopped" about 60 s in, none reached
the home screen.

- **Cause (read in the set's vivo-services.jar and in the logs):** vivo's refresh-rate
  manager keeps flags of its own in the upper bits of a display mode's group and refuses
  every mode whose group is 256 or more (`PhysicalDisplayManager.rejectDisplayMode`:
  `group > 0 && group >> 8 != 0`). One UI's composer on these phones numbers the groups
  by the mode's width (`group=720`, `1080`, `1440` in `display_modes_host.log`), so every
  mode was refused: "Display device added ... modeId -1", then "Unable to locate mode
  id=-1,supportedModes=[]" ended system_server. The S25 series says `group=0`, the folds
  0 and 1, and they run.
- **The switch:** the manager's own off switch is `GlobalConfigs.IS_SUPPORTED` =
  `persist.sys.vivo.refresh_rate_adjuster` && `persist.sys.vivo.refresh_rate_manager`
  (read once in system_server and in the apps' framework). `guest_props.sh` sets
  `persist.sys.vivo.refresh_rate_manager=false` for the session when One UI's active
  mode is in a group of 256 or more; Android's own mode director then picks the rate.
  Line in the switch log: "guest_props: persist.sys.vivo.refresh_rate_manager=false for
  the session (One UI's active display mode group: 1080; ...)" or "vivo's refresh-rate
  manager kept (...)". `ONEOS_GUEST_VIVO_RRM=1` keeps the manager, `0` switches it off on
  any phone. Test: `scripts/test-vivo-rrm-props.py`.
- **If the first 0.4.85 report still stops:** the other route is a patch of
  `rejectDisplayMode` in `switcher/patches/vivo_guards.py` (a set revision after r17 and
  an upload). What the phone does with vivo's manager off (which rates it offers,
  whether 120 Hz holds) is not known until that report.

#### Host check: the Exynos S24 and S24+ (0.4.83, no session yet)

Offered from 0.4.83 at the owner's request (2026-11-10: "add the same supported roms as
s24 ultra to plus and base too"), untested: the Galaxy S24 (Exynos) (s-9945, SM-S921,
e1s) and the new Galaxy S24+ (Exynos) (s-plus-9945, SM-S926, e2s). They are the first
Exynos phones with OriginOS (and get Nothing OS in the same build); the S24 FE, Z Flip7
FE, S25 FE and the Exynos S26s do not offer it. Nothing in the set or the session
scripts changed for them.

| | S24 (Exynos), S24+ (Exynos) |
|---|---|
| SoC, CPU | s5e9945 (Exynos 2400), SVE and SVE2, no SME |
| Kernel, vendor API | 6.1, 34 (Android 14) |
| Display composer | composer3 (AIDL, `vendor.hwcomposer-3`) |
| Audio HAL | AIDL (`vendor.audio-hal`, `vendor.secaudiohal-aidl`; the S24+ probe of 2026-11-10) |
| Panel (S24+ probe) | 1080 x 2340 at density 450, brightnessMaximum 5.0, backlight `/sys/class/backlight/panel` |
| Other systems there (reports of 0.4.72-0.4.74) | S24 (Exynos): ColorOS 17 started and returned on an SM-S921N; on SM-S921B several sessions ended in a restart. No session from an S24+ yet |

- **No session step is there for OriginOS on Exynos:** the chip-specific steps in
  guest_props.sh are OPPO's and OxygenOS's (the RenderEngine retry wait and Vulkan
  choice, the Qualcomm perf library's hardware name); the image is MediaTek-built and
  has so far only met Samsung's Snapdragon vendor. What these phones have shown with
  other systems: ColorOS 17 and the Pixel 9 Pro XL image reach the home screen on the
  Exynos 2400's vendor (S24 (Exynos), S24 FE).
- **Not known until a session report:** vivo's SurfaceFlinger and its composer3
  extension on Exynos's composer; vivo's graphics stack on the Xclipse driver (every
  OriginOS session so far ran on Adreno); vivo's audio policy with Exynos's vendor
  policy file; the radio (Samsung's Exynos RIL) and the camera.
- **First report from one of them:** as for the Snapdragon S24s above, plus the
  `guest_props:` lines of takeover_app.log.

#### Staging recipe (for the run after r12; every switch needs a fresh, direct yes)

All commands from the server, in the branch's worktree (its session scripts are the
ones deployed): `W=<the originos-0471 worktree>; cd $W`
(it has `out -> /srv/projects/OneOS/out`). The CN image: raw
`/srv/projects/OneOS/mysticgsi/out/oneos-originos-cn/Originos-k6993v1_64-17-260919185055-AB-20261107-MysticGSI.img`
(15,998,222,336 bytes, sha256 9eab3c6de0938a8f31a96be0bfdc9d2c511198aa40704e0206bd633becfdd8ee)
with its `.img.gz` beside it (8,548,707,904 bytes, sha256 f55cf849b1c0510d633595bc7d74946c650da628d110a370684e390c8fdb61ad;
also on gofile as OneOS_OriginOS6_CN_PD2609MA.img.gz, md5 7ebb9f9b4af54765622402c193eb0e93).

**Z Fold8 Ultra (scripts and set only; the image is already on the old OriginOS stage):**

1. `adb connect 127.0.0.1:5565 && adb -s 127.0.0.1:5565 shell 'su -c id'` (root tunnel).
2. Nothing mounted from either stage, and the old OriginOS stage is there:
   `adb -s 127.0.0.1:5565 shell 'su -c "grep -c /data/local/tmp/oneos /proc/mounts; ls -d /data/local/tmp/oneos*; grep -c vivo-services_patched /data/local/tmp/oneos.old-1794151843-origin/guards.txt"'`
   (first number 0; the last 1).
3. Infinity-X's stage aside, OriginOS's back as the active stage:
   `adb -s 127.0.0.1:5565 shell 'su -c "cd /data/local/tmp && mv oneos oneos.old-$(date +%s)-infinityx && mv oneos.old-1794151843-origin oneos && ls -d oneos*"'`
   (going back to Infinity-X later: the same two moves the other way).
4. Scripts and set r12 (only the files that differ are pushed, no image):
   `ANDROID_SERIAL=127.0.0.1:5565 sh scripts/deploy-phone.sh --overlays /srv/projects/OneOS/out/overlays_originos_cn_r12 --scripts-only 2>&1 | tee /srv/projects/OneOS/out/originos/deploy-cn-r12.log`
   (ends with the stage listing; only the rebuilt jars and guards.txt travel, about 175 MB).
5. session.env for this run (mode 2, Samsung IMS on for SMS: the run 13 plan), the old one kept:
   `adb -s 127.0.0.1:5565 shell 'su -c "cat /data/local/tmp/oneos/session.env"'`, then
   `adb -s 127.0.0.1:5565 push scripts/originos/session-f8u.env /data/local/tmp/session-f8u.env`
   `adb -s 127.0.0.1:5565 shell 'su -c "cd /data/local/tmp/oneos && cp session.env session.env.r11-bak && cp /data/local/tmp/session-f8u.env session.env && chown 0:0 session.env && chmod 644 session.env && rm /data/local/tmp/session-f8u.env && cat session.env"'`
   (if the old file had other keys, carry them over by hand).
6. Launch script (the repo's copy; the phone's own /data/local/tmp/originos_launch.sh works too):
   `adb -s 127.0.0.1:5565 push scripts/originos/originos_launch.sh /data/local/tmp/originos_launch.sh`
7. If One UI ran sessions since its last restart and the preflight refuses on the
   property space: restart the phone (re-root, tunnel), then from 1.
8. The owner's direct yes, then: `adb -s 127.0.0.1:5565 shell 'su -c "sh /data/local/tmp/originos_launch.sh"'`.
9. After the return, once `/proc/loadavg` is under 4:
   `ANDROID_SERIAL=127.0.0.1:5565 sh scripts/pull-run-logs.sh originos_cn_run13`; check per
   memory/check-whole-session-health.md; then the odrefresh line in takeover_inner.log
   ("concurrent-copying true, the zygote's true"), no "read barrier state mismatch" in
   the logcat, Samsung IMS bound (ui_activator.log) and an SMS both ways.

**S26 Ultra and S25 Ultra (first OriginOS staging: the whole image):** the same, but
the image travels: deploy-phone.sh pushes the 8.55 GB .gz to
/data/local/tmp/oneos_incoming and unpacks it into the stage (about 24.5 GB free on
/data needed while unpacking, 16 GB stage afterwards; the S26 Ultra probe had 173 GB,
the S25 Ultra 81.8 GB). Over the ~1 MB/s tunnel that is hours: ask about Wi-Fi first,
or let the phone download the .gz itself (gofile, owner's testing folder) to
/sdcard/Download and pass `ON_PHONE_GZ`. `--fresh` moves the phone's current app stage
aside (oneos.old-<epoch>, listed in the app's Old copies): OriginOS needs its own /data.

1. `adb devices`; `export ANDROID_SERIAL=<that phone>`; `adb shell 'su -c id'`; no screen lock.
2. `sh scripts/deploy-phone.sh --fresh --overlays /srv/projects/OneOS/out/overlays_originos_cn_r12 /srv/projects/OneOS/mysticgsi/out/oneos-originos-cn/Originos-k6993v1_64-17-260919185055-AB-20261107-MysticGSI.img 2>&1 | tee /srv/projects/OneOS/out/originos/deploy-cn-r12-<s26u|s25u>.log`
   (with the phone's own download: `ON_PHONE_GZ=/sdcard/Download/OneOS_OriginOS6_CN_PD2609MA.img.gz` before `sh`);
   it ends with "image verified".
3. session.env: `adb push scripts/originos/session-s-ultra-8850.env /data/local/tmp/session.env`
   (S25 Ultra: `session-s-ultra-8750.env`), then
   `adb shell 'su -c "cp /data/local/tmp/session.env /data/local/tmp/oneos/session.env && chown 0:0 /data/local/tmp/oneos/session.env && chmod 644 /data/local/tmp/oneos/session.env && rm /data/local/tmp/session.env"'`.
4. `adb push scripts/originos/originos_launch.sh /data/local/tmp/originos_launch.sh`.
5. The owner's direct yes, then `adb shell 'su -c "sh /data/local/tmp/originos_launch.sh"'`.
   The first boot compiles the guest's boot image (odrefresh, up to a few minutes
   under the boot animation) and starts on a fresh guest /data (setup marked done).
6. Logs as for the Fold (`scripts/pull-run-logs.sh originos_cn_<phone>_run1`).

### Thirteenth CN run (r12, F8U, mode 2, Samsung IMS; 11-09 07:48-08:28)

Works: boot, Bluetooth (no first-start crash this time), themes, sound, calls and SMS
in and out (Samsung IMS), blur, double tap to sleep, double tap to wake from AOD on
the inner panel, odrefresh "concurrent-copying true, the zygote's true" (7 s). The
1 730 SystemUI DeadSystemException entries at 08:28 are the return.
Fixed after it (7f6ab8b6), for run 14:
- **vivo never scans /oem** (no package cache entry for anything there): the fold
  cutout overlay and the OneOS app were missing, so no camera hole (cutout 0, a
  63 px bar on the cover) and no in-guest app. Both now in system_ext (mount points
  in the overlay's upper layer, bound in the /oem step); with no partition-order
  config system_ext overlays rank above vendor (5) and product (11).
- **Play Store missing:** the payload presents Play services only; com.android.vending
  was the CN stub (GooglePlayServicesUpdater 22.7.54, no launcher entry).
  guest_google.sh STORE_ONLY puts One UI's Play Store over the stub.
- **No double tap on the cover's AOD:** the panel that is off reads backlight 1, not 0,
  so the keeper kept the inner panel lit, never saw the fold and never armed tsp2
  (raw touches reached the sleeping guest). On a Fold it now reads each panel's dpms.
- **AOD unseeable:** vivo's AOD asks for doze brightness 0.0 (backlight 1 of 13510);
  the keeper gives a lit AOD panel at 0 or 1 ONEOS_GUEST_VIVO_AOD percent (3).
- **Unfolded = the cover's UI stretched:** mode 2's phone layout on a 2256 x 2504 panel
  at 420. Run 14 tries mode 1 again: run 10's Themes crash in mode 1 was most likely
  the manufacturer check fixed in r11 (run 12 had the same crash in mode 2).

### Fourteenth CN run (r12 + run 13 fixes, F8U, mode 1; 11-09 08:34-08:45)

Mode 1 holds: unfolded layout right (density 450), Themes fine, cover cutout and status
bar right (overlay from system_ext), AOD floor and double tap on both panels, the Play
Store there (One UI's; "device isn't certified": a CN build with a new GSF id,
google.com/android/uncertified), return through the OneOS app.
**Inner panel brightness ignored the slider:** vivo's display code takes
SurfaceControl.getPrimaryPhysicalDisplayId() as panel 0 (VivoDisplayEvent,
VivoLocalDisplayAdapterImpl/DeviceImpl, color tracker, touch, refresh rate). In mode 1
SurfaceFlinger named the cover primary at boot, so the inner panel was panel 1: its
DisplayPowerController animated on "VRampAnimator displayId:1" (lcmInt 4197) while its
own LCM token only ever got 500 of 14063 (run 13, mode 2, had animators for both 0 and 1).
Set r13: vivo_guards.py routes the six calls in vivo-services through
OneOSVivoPrimaryDisplay.get(), which returns oneos.vivo.inner_display (guest_start.sh
sets it to the inner panel's physical id in mode 1, before system_server) and
SurfaceFlinger's answer otherwise; return_to_oneui.sh deletes the prop.
Run 15 (set r13) showed the panel id was not the whole cause: the inner panel's
DisplayPowerState kept the session's first brightness (0.1115 -> backlight 0.0356)
while vivo animated only the sdr value. Mode 1 turns on vivo's per-panel brightness,
which the phone build has only in part; mode 2 (phone) drove both panels. Set r14:
the device-type reads of vivo's brightness code answer "phone" (vivo_guards.py:
vivo-services' display sensor/brightness/common classes, 8 reads, LcmProperty's
ro.vivo.device.type, DisplayPowerController.mIsPhone in services.jar;
vivo_brightness.py: InfoImpl and RootConfig in vivo-framework, 4 reads). The layout
side (LogicalDisplayMapper, the display adapter, apps) keeps foldable.

### Runs 16-17 (set r14, mode 1)

Run 16: inner brightness follows the slider (setBacklight 0.185 -> 0.028). Wi-Fi drop
at 10:28:39 was vivo EasyShare's QR transfer screen starting its hotspot (swlan0).
Dynamic island (music, timer, clock) never showed: SuperX got the notifications, but
SuperXCapsuleDataController only ever deleted island items and IslandServiceProxy never
bound (no "bindIslandService" in SystemUI's VivoStatusBarCapsuleLog buffer, no :island
process). SystemUI had isHoleScreen=false: vivo.hardware.holescreen (vivo_config.ini:
hole_x=590 hole_y=45 hole_radius=40, the lens box's top left and radius) was left out
with the hardware features. guest_prepare.sh now appends it from One UI's lens
(host_holes: the cover's on a Fold, F8U 505,19 r35; ONEOS_GUEST_VIVO_HOLE=0 leaves it).
Play Store sign-in stuck on "Checking info": check-in succeeded (gms Checkin.xml
android_id), no Auth error in the guest; an uncertified CN build: register the GSF id
at google.com/android/uncertified.

### Runs 19-21: dynamic island, Google sign-in

- **Google sign-in white on white** (run 19): vivo's /system/etc/fonts.xml links to
  /data/vfonts/fonts.xml, which a vivo service writes on a vivo phone and nothing wrote
  in the guest; WebView (Chromium) reads fonts.xml and drew no text. guest_prepare.sh
  copies the image's fonts_default.xml there when it is missing (46a8b99f).
- **Dynamic island** needs three things: vivo.hardware.holescreen (294acc46),
  vivo.opt.notification.superx (26d1e738; VivoSuperXNotificationManager's scene support,
  missing from the CN vendor's vivo_config.ini) and Jovi's atomic notification switch
  (com.vivo.assistant/.settings.AtomicNotificationSettingsActivity; Jovi writes
  superx_notification_selector=0 at every boot until it is switched on there; its SuperX
  MMKV store was empty). With all three the island showed (run 21).
- **Island below the lens** (run 21: pill 28..123, lens 19..89): vivo centres it on the
  cutout's bounding box, bottom - width/2 (DynamicCapsuleContainer.updateCutoutValue);
  One UI's 0..108 box gave 73. Set r15 (= r14 + this overlay): a vivo image's fold cutout
  overlay has the cover's lens circle (M 540,19 a 35,35 ...), 54dp status bar kept.
