# ColorOS 17 in the OneLineage container on the Galaxy Z Fold (SM-F976B)

> **Renamed after 0.3.6:** the stage is `/data/local/tmp/oneos` (was `/data/local/tmp/lineage_stage`), its set-aside copies `oneos.old-<epoch>` / `oneos.trash-<epoch>` (were `lineage_stage.old-*` / `.trash-*`), and the session scripts `oneos_switch.sh`, `guest_prepare.sh`, `guest_start.sh` (were `switch_to_lineage.sh`, `master_prepare.sh`, `master_inner.sh`). The run notes below keep the old names (they describe past runs); the app's root script and `scripts/deploy-phone.sh` rename an old stage and its copies when they are idle.

Guest: ColorOS V17.0.0 from the OPPO Find N6 (PLP120, `CP2A.260605.016`), built
into an ext4 GSI with MysticGSI. Host: One UI on Android 17, same AOSP build ID,
Snapdragon SM8850 on both. The guest runs as OneLineage runs LineageOS: its own
zygote, system_server and SurfaceFlinger in a mount namespace, on top of the
host's kernel, vendor HALs, init and property area.

## Fixed so far

| Symptom | Cause | Fix |
| --- | --- | --- |
| zygote aborts: `Unable to find class com/oplus/media/OplusBitmapChecker` | guest started with the host's `BOOTCLASSPATH` | `master_inner.sh` runs the guest's `derive_classpath` |
| same abort after that | OneLineage's prebuilt `zygote_exec` hardcodes LineageOS 23.2's class paths | `switcher/native/zygote_launcher.c` passes the environment through |
| system_server dies: `createProcessGroup(1000, 0) failed` | fresh sysfs in the container has no cgroup2 at `/sys/fs/cgroup` | `master_prepare.sh` binds the host's `/sys` |
| One UI apps lose their APKs during the switch | `/data/app` etc. were bridged while One UI still ran | stop the host framework first |
| DisplayManagerService constructor NPE in `DeviceStateToLayoutMapExtImpl` | oplus-services reads every `<display>`'s `<address>` without a null check and resolves every non-zero state's addresses through the state-0 layout (state 0's disabled display = big panel, enabled = small panel); Samsung's file breaks that | hide the host's `display_layout_configuration.xml`; since run 31 `master_inner.sh` writes our own (state 0 first, real ids from the guest SurfaceFlinger: cover port 148, inner port 147) |
| run 30: "Wallpapers and styles too zoomed in" | with `type.fold` and sw885 `com.oplus.wallpapers` picks its Find N6 inner-screen page (`PersonalFoldLargeScreenFragment`): a 4x4 grid of 2x2 cards, each half the panel wide. Not compat scaling, not the 408 density | static RRO `OneOSWallpapersFoldGrid.apk` in the guest's `/oem/overlay` makes the grid 8x2 (`make-overlays.sh`, `master_prepare.sh`, `ONEOS_GUEST_WALLPAPER_GRID=0` to keep ColorOS's). Run 31: the four cards sit in one row as intended, but the My theme header above them (`id/headerContainer`, 386dp = 984 px in the layout and in `PersonalLargeSizeFragment.Y0`) is drawn about 2400 px tall and fills the first screen. Cause (run 32 all.log): every activity of the app extends `BaseDefaultDensityActivity`, whose `getResources()` (`o.a`) lays the page out at a phone density, shortest side = 360dp = 6.27 px/dp (text stays at 3.0), unless `f0.w` says foldable. `f0.w` looks for `config_lidControlsDisplayFold` (not in this framework-res), then for `oplus.software.windowmode.compact`, which the Find N6 has in a `my_product` feature file the guest does not read. So the header was 386 x 6.27 = 2419 px and the card padding 100 px instead of 48 (`iconCardView 632,100-1089,557`). `master_prepare.sh` adds `windowmode.compact` with the fold form (`ONEOS_GUEST_COMPACT_WINDOW=0` leaves it out); it also turns on OPPO's full compact window mode in WMS. `switch_to_lineage.sh` saves `diag_pages/wallpapers_top_N.txt` (all the app's activities with frames) when the page is opened |
| run 31: no ringtones / notification sounds in the picker, silent defaults | the Find N6's sounds exist only as haptic sets in `my_product/res/audio/haptic_ringtone/output<Hz>HZ`; OplusAtlasService (`RingCopyHelper`) copies one to `/data/oplus/multimedia` only with `oplus.software.audio.haptic_channel_support` (a my_product feature the guest does not load); the dirs it left were unreadable for MediaProvider; and the shared props gave the guest One UI's `ro.config.ringtone` (`ACH_Galaxy_Bells.ogg`) | `master_prepare.sh` stages `output166HZ` into the guest's `/data/oplus/multimedia` (system 0775); `guest_props.sh` swaps in ColorOS's `ro.config.{ringtone,notification_sound,alarm_alert}` for the session and puts One UI's back on return (`ONEOS_GUEST_RINGTONES=0` for neither) |
| guest frames rejected `NO_RESOURCES`, panel frozen on One UI's last frame | composer still bound to the killed host SurfaceFlinger | restart `vendor.qti.hardware.display.composer` before the guest's |
| `Timeout waiting for default display` | OPPO's refresh rate selector (needs OPPO display HALs) gives no mode specs, so `LocalDisplayAdapter` drops both panels | `services_patched.jar` (`scripts/make-overlays.sh`) falls back to the active mode |
| One UI boots with ColorOS settings | guest saves `persist.*` props | snapshot before, restore on return |
| run 31: glass UI flat in places (black power menu, plain dim behind dialogs and QS detail panels, sharp wallpaper behind the app drawer) | guest SurfaceFlinger "Disabling blur effects, they are not supported.", RenderEngine blur algorithm None, WindowManager `mBlurEnabled=false`: `ro.surface_flinger.supports_background_blur` comes from the Find N6 vendor build.prop (not in the GSI) and One UI does not set it to 1. ColorOS's own capture blur (BlurService) kept the shade and Control Center blurred | `guest_props.sh add` sets it to 1 for the session; `remove` restores a host value; `ONEOS_GUEST_BLUR=0` skips it |
| run 31: com.coloros.assistantscreen (every ~10 s, kept alive by the launcher's card provider pull), phonemanager, wifibackuprestore, cosa, instant.local.service abort in zygote: `selinux_android_setcontext ... failed` | the guest's system_ext/product seapp_contexts name OPPO domains (`oplus_assistantscreen_app`, ...) that Samsung's loaded policy lacks; unknown types are EINVAL even in permissive mode | `master_prepare.sh` binds copies with every rule whose `domain=`/`type=` is missing from the host's CIL files commented out, so the apps get AOSP's generic domains (`ONEOS_GUEST_SEAPP=0` keeps ColorOS's files) |
| run 32: calls connect but are silent both ways (earpiece, speaker and mic), media fine | the call was on SIM 2 (`GsmCdmaCallTracker [1]`) but Samsung's audio HAL started the ADSP voice session on SIM 1's VSID (`switchAudioMode: new call state is ACTIVE for vsid VSID_1`): it takes the VSID from `g_call_sim_slot` (0x01 VSID_1, 0x02 VSID_2, 0x10 swap during a call), which One UI's audioserver (CallStateManager) sends before every setMode(IN_CALL) and ColorOS's never does | `master_inner.sh` watches the guest's per-SIM call state and sets `g_call_sim_slot` through the guest AudioFlinger (`service call media.audio_flinger 18`): the ringing SIM, else the last call's SIM while idle, and 0x10 when an outgoing call already runs on the wrong VSID; decisions in `/data/call_audio.log` (`ONEOS_GUEST_CALL_SIM=0` turns it off). Run 33: the loop never ran and every call stayed on VSID_1, because apostrophes in a comment inside the audioserver keeper's single-quoted `sh -c` script cut it short (`as` became the word `through`). The keeper handed over at 0 s in runs 31-33, dropped `guest_audio.flag` and started Samsung's audioserver next to the guest's, which kept serving. Comment fixed. Per hal.so, the HAL ignores 0x01/0x02 during a call, so a call already on the wrong VSID now gets 0x10 at once. Run 34 to confirm |
| run 32: Wi-Fi connects only while the Connecting dialog is open; Back disconnects and nothing is saved; Settings stuck behind the dialog | the image's WirelessSettings is the domestic build: it waits for the sticky `android.net.wifi.DISABLE_ALERT_NETWORKS` (COMPLETED) and removes the new network when the dialog is cancelled; only `OplusWifiConnectionAlert` sends it and `OplusWifiInjector` creates it only with `oplus.software.connectivity.region_CN`, a `/my_region` feature the guest never loads (no `CUST_LEVEL_LIST`) | `master_prepare.sh` adds `region_CN` to the system_ext feature switches (`ONEOS_GUEST_WIFI_CN=0` leaves it out); the stage also gets `/data/misc_ce/0/apexdata/com.android.wifi` for the wifi user store |
| run 32: power menu ~15 s late or missing after a long press, Power + Volume Down screenshot late, folds handled late | `lib_inputflingerEx.so` `saupwkProcessKey` (OPPO Theia power key statistics) runs on system_server's InputReader thread and looks up `vendor.oplus.hardware.stability.oplus_project.IOplusProject/default` with `AServiceManager_getService`, which polls 5 s for a missing service: each power key press froze all input for 5 s (EventHub "Slow read detected" up to 13.2 s) | `guest_props.sh` sets `persist.sys.saupwk_test=1` for the session, which makes the function return first (`ONEOS_GUEST_SAUPWK=0` leaves it out) |
| run 32: Weather crashes on open (`libprivate-constants-v3.so` not found), theme store cannot load `libmmkv.so` | `/data/preapps-lib` (native libraries of the `/my_stock/del-app` apps) was created 0700 by the guest's PackageManager; the guest's init.rc makes it 0771 | `master_prepare.sh` creates it 0771 system |
| run 32: shader cache never saved (`error creating cache file /data/misc/surfaceflinger/skia_shaders`) | init.rc makes the directory; the container has no init | `master_inner.sh` creates it before the guest SurfaceFlinger starts |

| run 33: Power + Volume Down screenshot, then about 10 s later the guest's system_server is gone and the switcher returns to One UI (reported as a hang after screen off) | `KeyGestureController.takeScreenshot` always calls `KeyGestureControllerExtlmpl.getTpInfo`, which runs `setprop ctl.start gettpinfo` (an OPPO init service for touch panel logs). The host's init has no such service, so `SystemProperties.set` threw on android.display (14:59:19.710). `KillApplicationHandler` waited 10 s in OPPO's `waitForDumpCondition` and then sent SIGKILL to its own process (14:59:29.749). `StrategyBlackscreenshot` makes the same call for Volume Up + Volume Down with the screen off | `oplus_boot_hangs.py` drops the setprop in both `getTpInfo` methods. Screen off was not the cause: five earlier power-key sleeps in run 33 went fine |

| run 34: com.android.phone binds a missing IMS service 6 times a second all session (5247 failed `bindService` calls on its main thread, plus 5247 ActivityManager "not found" lines) | Qualcomm's `ims.apk` (org.codeaurora.ims) needs `persist.oplus.qspa.modem=enabled` and is skipped, which is right: this phone's IMS is Samsung's. The three `QtiImsExtConnector`s that `oplus-telephony-common-ext.jar` creates in com.android.phone retry every 500 ms forever (`/system/product/framework/ims-ext-common.jar`) | `qti_ims_ext_backoff.py` makes the retry 60 s (`make-overlays.sh` builds `ims-ext-common_patched.jar`, `master_prepare.sh` binds it); `ONEOS_GUEST_IMS_EXT_BACKOFF=0` keeps ColorOS's jar |
| run 34: holding Volume Up + Volume Down to return to One UI turned TalkBack on in ColorOS (saved in the staged settings) | the chord is also Android's accessibility shortcut, and ColorOS's SettingsProvider aims it at TalkBack at first boot (`accessibility_shortcut_target_service` from its `config_preinstalled_screen_reader_service`). The first 3 s hold showed the shortcut's warning dialog (all.log 16:43:59.409) and set `accessibility_shortcut_dialog_shown=1`; the host watcher handled the request only at 16:44:06, so the keys were held again, and once the dialog has been shown the shortcut needs 1 s: TalkBack came on at 16:44:02.839 | `master_prepare.sh` empties the shortcut target while it is still the factory TalkBack one (an empty target makes `isAccessibilityShortcutAvailable` false, so `KeyGestureController` has no rule for the chord and the keys stay volume keys) and turns TalkBack off when it is the only enabled service (`ONEOS_GUEST_A11Y_SHORTCUT=1` keeps ColorOS's shortcut). The watcher in `switch_to_lineage.sh` checks the request every second and before its slow checks |

| run 34: Weather never finds a location; OPPO system apps lack the runtime permissions ColorOS grants them | OplusRuntimePermGrantPolicyManager grants OPPO apps their default runtime permissions on every boot, but reads the lists (`<default-grant-permissions>` in my_product and my_stock `etc/permissions`) only through `OplusCfgFilePolicy.getCfgLevelList`, which is empty without `CUST_LEVEL_LIST` ("default xmls not found", 16:29:11.463). The network location provider com.oplus.location had no location or phone permission and WifiService refused all 27 of its scans ("UID 10163 has no location permission"); Weather asks the network provider first, then GPS, and timed out after 60 s (16:34:16-16:35:16); com.coloros.weather.service had no background location (`-410005`). 108 grants of 35 installed OPPO apps were missing | `oplus_default_grants.py`: with no CUST_LEVEL_LIST, `getDefaultPermissionFiles` reads `/my_product/etc/permissions` and `/my_stock/etc/permissions` while the guest's `/data/oneos_oplus_grants` exists (`master_prepare.sh`; `ONEOS_GUEST_OPLUS_GRANTS=0` leaves it out). OPPO's own checks stay: system apps or a matching certificate, requested permissions only, never over a user's choice. Run 35 to confirm |
| run 34: GPS in the guest without A-GPS (no fix in four 57 s Weather sessions) | One UI's com.qualcomm.location holds the HAL's A-GPS callback (`vendor.qti.gnss` ILocAidlAGnss.setCallbackExt), which outranks Android's IAGnss callback in libgnss (`GnssAdapter::initAgpsCommand` callback priority). It died with One UI (16:28:34.332 "IAGnssCallback died") and the guest image has no com.qualcomm.location, so the HAL kept sending SUPL connection requests to the dead callback (16:34:19.116 `requestATL`, "locAidlAgnssStatusIpV4Cb: Peer has gone", 15 s later "LocSvc_Agps: Entered timeout event"). `OplusGnssPowerCorrector: isEngineOffByStrategy: true` is only logged when a request stops; the engine did start | `master_inner.sh` restarts the vendor `gnss_service` before the guest zygote, so the guest's own IAGnss callback is the only one (`ONEOS_GUEST_GNSS_RESTART=0` leaves the HAL alone). A fix still needs sky view; `diag_*/location.txt` (dumpsys location) shows providers, satellites and fixes. Run 35 to confirm |
| 0.4.10 (Fold, USB to a PC): a charging "voltage error" warning whenever plugged in | OplusBatteryService takes the battery notify code from OPPO's ICharger HAL (`getPsyBatteryNotify`), which Samsung's vendor lacks: -1, broadcast as `notifycode`, and ColorOS's SystemUI (OplusPowerNotificationWarnings.updateBattery) tests it bit by bit, every bit set ("updateBattery : event code is -1 mPlugged is 2") | `oplus_battery_notify.py` stores a negative notify code as 0; a real code from a HAL that answers still gets through |
| 0.4.10 (Fold): the cover screen "looks 720p", blurry even at High resolution | not resolution: SurfaceFlinger drew the cover 1:1 at 1080 x 2520 with full-size buffers. ColorOS took Samsung's shared `ro.sf.lcd_density` 480 for it, a 360 dp phone layout about 14% larger than One UI's 420 on the same 422 dpi panel | `oneos_switch.sh` records the cover (uniqueId, port, size, dpi) from One UI's display dump; `guest_prepare.sh` gives it `forcedDensity` in the guest's `display_settings.xml`: its real dpi down to a multiple of 20 (420, also one of ColorOS's own display sizes), only under the base density and never over a size chosen in ColorOS. The inner panel and `display_density_forced` stay as they were (`ONEOS_GUEST_COVER_DENSITY=off\|auto\|<dpi>`) |
| S25 Ultra (X9U CN, 0.4.7, session e98f44ff): the status bar clock next to the camera, in the middle | One UI runs the 1440 px panel at FHD+ (1080), so the camera hole read from its display dump was 521..560; ColorOS runs the whole panel, where that is left of the middle (HOLE_LEFT_TYPE) and the clock starts right of it | `oneos_switch.sh` scales the hole by the cutout's `physicalDisplayWidth / displayWidth` (695..747 on 1440 px: a centre hole) |
| S25 Ultra (same session): Bluetooth never turns on, com.android.bluetooth aborts 2.5 s after each start (19 times) | `[broadcaster.cc:1532] Initialize: HAL requirements not met`, after "HalVersionManager: No supported HAL version": the SM8750 and older phones register only Samsung's `vendor.samsung.hardware.bluetooth.audio.ISehBluetoothAudioProviderFactory`, not Android's `IBluetoothAudioProviderFactory/default` (probe reports: only the SM8850 phones have it), and the stack's HIDL fallback is off; One UI turns every LE Audio profile on, and the LE Audio broadcaster then aborts the process | `guest_props.sh` turns the LE Audio profiles off for the session (`bluetooth.profile.bap.*`, csip, hap, vcp, ccp, mcp; memory only, restored on return) when the phone has no `IBluetoothAudioProviderFactory/default`, so classic Bluetooth starts (`ONEOS_GUEST_LE_AUDIO=1` keeps them). Bluetooth audio there still needs a bridge to Samsung's provider. 0.4.11 asked with `service list`, which waits on every service's interface: One UI's surfaceflinger is frozen behind the gap splash then, so every 0.4.11 switch hung there (S24 Ultra session 0210fa8a: logo, black, reboot); 0.4.12 uses `service check` (servicemanager only) |

## Returning to One UI

| Symptom after return | Cause | Fix |
| --- | --- | --- |
| One UI's surfaceflinger: `CANNOT LINK ... libdisplayconfig.system.qti.so` | `umount -l rootfs/*` followed the image's absolute symlinks (`system_ext`, `product`) to the host's partitions | unmount only `/proc/mounts` entries under the rootfs |
| reboot `vold-failed` | guest vold killed by its launch flags, which the host vold shares | kill guest processes by mount namespace |
| One UI system_server SIGBUS in package parsing, WifiService NPE, RescueParty | One UI's decompressed APEXes (`/data/apex/decompressed`, e.g. NFC on loop31) read back with dm-verity I/O errors after a session | **cause not confirmed yet**; the switch now logs the APEX backing files (`apex_watch.log`) and the return checks them |

Since then `return_to_oneui.sh` returns by **rebooting** (it still kills the
container, unbinds /data, restores the host's `persist.*` props, and unmounts
everything under the stage dir first; OneLineage's One UI Home database
restore is gone, see "Starting from the OneOS app"). The in-place
restart (`ONEOS_RETURN_MODE=inplace`) left a decompressed APEX unreadable after
every session, even one where the guest never started (`ONEOS_PREPARE_ONLY=1`
with clean APEX reads after the setup), and once ended in an ext4
`errors=panic` kernel panic on the wifi APEX. Temp root is lost either way.

`commit 27673bb` blames `apexd.config.compressed_apex=false` for the last row.
That is wrong: the host defines that property itself, so the guest's value is
never loaded. The prop blocklist it added is kept as a precaution only.

## Pixel-era fixes and ColorOS (2026-10-25)

The ColorOS sets the app ships (`n6-f8u`, `x9u-sultra`) were built on
2026-10-23 with the storage, installd, power, sysrq and weaver guards only.
What the Pixel work since then means for them:

- **Comes with a rebuild of the sets, no new code**: the biometric,
  gatekeeper, FRP (pdb), apexd, app-id-15000 and no-new-users guards. Each
  patcher reads ColorOS's non-R8 smali as well as Pixel's, and make-overlays
  applies them to any image. The in-guest OneOS app (Back to One UI, its
  Quick Settings tile) also comes with the rebuild: guest_prepare.sh copies
  it into every guest's /oem.
- **Guest vold as "gvld"**, so Back to One UI can return without a restart
  (`docs/inplace-return.md`). The Find N6 and Find X9 Ultra images carry the
  same `vold` and `service.incremental.so` (CP2A.260605.016), and both have
  the layout of Pixel's: `VoldNativeService::start` at 0x79140 passes the
  only "\0vold\0" (0x104e7) to addService, and `VendorVoldNativeService::
  try_start` at 0x78afc has the same `tbz w19, #0, +0xd4` after isDeclared
  (0x78b64). `service.incremental.so` has its one "vold" at 0x6536c, with
  the same two lookups. services.jar has the same three lookups as Pixel's.
  OPPO adds a fourth in oplus-services.jar
  (`OplusStorageManagerFeature.connectVold`, OPPO's own IVold calls), which
  `guest_own_vold.py --oplus` moves to "gvld" too, and guest_start.sh checks
  for it. The crashrecovery APEX (`com.android.crashrecovery`, the same in
  both images) has AOSP's RescueParty: the factory reset that calls
  `rebootPromptAndWipeUserData` runs only while RescueParty is on. No other
  native library in system_server names "vold"; the binaries that do
  (gsid, incident_helper, apexd, vdc, vold) are the same as Pixel's, and the
  guest runs none but its vold. make-overlays.sh pins all three files.
- **eSIM guard**: the Find X9 Ultra image's EuiccOplus is hidden like
  Pixel's EuiccGoogle; the Find N6 image has no eSIM manager.
- **Already shared** (same session scripts for every image): host-state
  record, stage-mount cleanup and Permissive return, hardened reboots, the
  in-place sequence (gated on gvld, so ColorOS returns by reboot until its
  sets carry it), session sampler and logcat capture.
- **Pixel-only today, worth a ColorOS test**: Bluetooth music. Samsung's
  audio HAL turns its A2DP offload path on only from `l_a2dp_format`
  (run 44), whatever the guest is, and guest_start.sh sends it only to
  non-ColorOS guests. No ColorOS Bluetooth audio test is on record; if
  music plays on the speaker, sending it there is the first thing to try.
  HFP's `bluetooth.sco.managed_by_audio` does not apply: the Find N6 image
  does not set it.
- **Not needed for ColorOS**: the attach APN (ColorOS attaches with the
  right APN itself), signal poll injection and call audio (ColorOS has its
  own), the Wi-Fi supplicant switch, density and fold line, Comfort View,
  the status bar padding RRO and Google Play services packaging.

A rebuilt set changes what runs in a ColorOS session (new guards, gvld, the
in-place return), so it needs a ColorOS session on the Fold, and on an S
Ultra for the X9U set, before friends get it.

## The Find X9 Ultra IN build (0.4.11)

The global (India) build of the Find X9 Ultra's ColorOS 17
(`OneOS_ColorOS17_FindX9Ultra_IN.img.gz`, the 0.3.3 upload byte for byte),
offered on every Galaxy S profile next to the CN build and listed first. It
brings Google's mainline modules, Play services and the Play Store in
my_product. Differences from the CN build that the session and the set handle:

- **Its own gvld pins** (`make-overlays.sh`): its vold is the CN one laid out
  0x2000 later (same instructions; the try_start branch at 0x7ab64), its
  service.incremental.so has the string and both lookups where the CN one
  does, and its crashrecovery module is a compressed APEX
  (`com.google.android.crashrecovery_compressed.apex`) whose
  service-crashrecovery.jar is Pixel yogi's, byte for byte. So it returns in
  place like the CN build.
- **Its set** (`x9u-in-sultra`): the CN set's files built from this image,
  plus `cellbroadcast_payload.img` (Google's module, compressed in the image).
  Only the in-guest app is byte-identical to the CN set's.
- **Region overlays** (run 37): its 24 `my_product/cust/<region>/overlay`
  folders are hidden for the session, or the zygote's fd allowlist aborts
  system_server.
- **No `region_CN`**: guest_prepare.sh adds the CN Wi-Fi feature only when
  `my_region` says `ro.oplus.pipeline.region=CN`; this build keeps its
  export Wi-Fi settings.
- **Google services**: in the image and running by default; a launch may hide
  them (`IMAGES_GMS`, `ONEOS_GUEST_HIDE_GMS=1`). The guards that keep the
  guest out of One UI's lock and keys (weaver, gatekeeper, FRP) apply as with
  Pixel.
- **CPU**: its core binaries (linker, libc, app_process, boot image,
  SurfaceFlinger, input) use no more SVE/SME than the CN build's, which runs
  on the SM8750 phones.

## Where the boot stands (end of day 1, attempts 13-23)

ColorOS's system_server now gets through bootstrap, core and other services,
`systemReady`, and starts **SystemUI and the launcher** (`com.android.launcher`).
The panel stays black. Fixed on the way:

| Blocker | Fix |
| --- | --- |
| Cached APEX payloads were the host's modules (ext4, Google-signed) | `make-overlays.sh` extracts the guest's 16 erofs payloads; `mount_payload` detects erofs |
| Google cellbroadcast/nfc/bt APEX apps vs ColorOS system apps | hide the host APEX app dirs (bind made private first) |
| BPF maps of ColorOS's connectivity module not pinned by the host | use the host's whole `android.uid.networkstack` group (tethering, NetworkStackGoogle, CaptivePortalLoginGoogle, cellbroadcast) |
| `IDnsResolver.getUnstableInterface` "Already called by AID_SYSTEM" | restart the host netd before the guest zygote |
| aconfig: "Invalid feature flag" | guest flag storage on a tmpfs `/metadata` |
| `settings_global.xml` rejected (non-numeric id) | numeric ids; seed `adb_enabled=1`, `auto_time=0`, `auto_time_zone=0` |
| `OplusEngineerFwService` waits forever for an OPPO HAL (watchdog) | `oplus-services.jar`: `waitForService` -> `checkService` for OPPO HALs |
| `cotaservice` / `DefragService` | start ColorOS's `cotad` / `oplus_defrag` in the container |
| LockSettingsService `setCeStorageProtection` via the host vold | `services.jar`: drop all IVold user-key calls (protects One UI's keys) |
| Samsung `lifeguard` APEX system service | `services.jar`: skip `com.samsung.*` APEX services |
| composer BAD_VALUE / NO_RESOURCES on every frame | **not fixed.** Transaction 1008 (HW overlays off) changed nothing: run 23 still had 3890 rejected frames; the "0 rejected" reading came from a 300-line tail flooded by log storms. Next: patched surfaceflinger without the Qualcomm composer extension client |

Open:

- **Black panel: the composer rejects every frame.** Every content-bearing
  executeCommands batch fails with EX_TRANSACTION_FAILED / BAD_VALUE before
  SDM runs, so the panels never power on (SDM defers power-on until a first
  commit) and no brightness reaches them. ColorOS's surfaceflinger routes
  frames through IQtiComposer3Client::qtiExecuteCommands; the next run skips
  that client (surfaceflinger_patched). Composer version skew was ruled out.
- **The guest rebooted the real phone.** No system_server crash: after
  finishBooting's checkpoint commit failed on the container's vold it called
  PowerManager.reboot, ShutdownThread shut down the modem, and
  PowerManagerService wrote the shared sys.powerctl. Now guarded
  (patches/guest_power_guards.py).
- **KernelSU drops Shell from its allowlist** when the guest PMS writes
  packages.list. OneHyper (`WeWaffles/OneLineage@onehyper`) snapshots and
  restores `/data/adb/ksu/.allowlist` during the session.
- **The guest set the shared clock** (now prevented with `auto_time=0`).
- OneHyper reached HyperOS's first frame with largely the same fixes; its
  README lists the stubs it needed.

## Keeping the guest away from One UI's data (after run 25)

Run 25 got as far as ColorOS's UI, then its UserDataPreparer could not prepare
user 0 and called destroyUserData(0) through One UI's own installd (shared
binder). That deleted most of One UI's /data/data and the photos in
/data/media, which were not bridged. Since then:

- `switcher/assets/bridges.sh`: every host /data tree a shared daemon can reach
  for the guest (app data incl. /data/data, /data/media, misc/user,
  sdksandbox/rollback, resource-cache, ...) is bound to the staged copy for the
  session. master_prepare.sh checks each by inode and refuses to start
  otherwise; deploy-phone.sh and master_prepare.sh refuse while a bridge is
  left over; return_to_oneui.sh reboots if one will not come off.
- The guest has its own empty /data/media. In its mount namespace the old host
  root (/postinstall), the host's /mnt storage views and /proc/sysrq-trigger
  are removed; the guest must get its own vold from servicemanager.
- `guest_storage_guards.py`: destructive IVold/IInstalld calls and the keystore
  maintenance calls that clear users or uid namespaces are dropped;
  UserDataPreparer never destroys data or asks for a wipe.
- `guest_installd_abi.py`: ColorOS's IInstalld numbering differs from Samsung's
  from code 10 on (an extra method), so guest calls reached other host methods.
  The proxy now uses One UI's codes (switcher/patches/host_installd.txt, from
  scripts/host-installd-table.sh) for create/query/compile calls and throws for
  everything else.
- `guest_no_sysrq_crash.py`: the guest watchdog cannot crash the kernel.
- make-overlays.sh writes guards.txt; master_prepare.sh only starts the guest
  with the jars listed there, and checks that both guarded jars (services and,
  since build 2, oplus-services) are the ones bound into the guest.
- Since build 2: the switch runs only in init's mount namespace (the one One
  UI's installd and artd use, so the bridges reach them), and host /data/adb
  and /data/apex are read-only inside the guest.
- master_prepare.sh refuses to start if any path it writes through, binds or
  relabels under the staged `/data` (a bridge source, or a parent of one) is a
  symlink: a guest with root could otherwise point e.g. `$STAGE/data/misc` at
  `/data/misc` and have the host-root rm/cp/chown/chcon land in One UI's data.
  Every recursive `chcon`/`chown` over the staged tree is `-h` (no-dereference),
  so an absolute symlink a guest app left in its own data dir never gets its
  host target relabelled; copies into the guest `/data` rm the destination first.

### Known limit: guest apps on the shared kernel (uid-collision root)

The guest shares the host kernel, and `su` works inside it. KernelSU/APatch/Magisk
decide root grants by uid, but the guest's own PackageManager hands out app uids
independently. An app inside ColorOS that is assigned the same uid as a
root-granted One UI app (the OneOS app, or the root manager itself) is granted
root when it runs `su`, and from there can reach host `/data`. There is no fix in
0.3.0; the mitigation is trust: the "Before you start" screen and the Switch
confirmation warn that apps installed inside ColorOS run on the same kernel and
root, so testers should install only apps they trust and not grant root to
unknown ones. Pinning the guest PackageManager away from the root-granted uids,
or refusing on a collision with the root manager's allowlist, is left for later.

## Starting from the OneOS app (build 2)

From build 2 the OneOS app stages the image and the overlays itself and starts
the switch as root: `nsenter -t 1 -m` into init's mount namespace, then
`set -a; . $STAGE/session.env; set +a; exec sh $STAGE/switch_to_lineage.sh`
(output in `$STAGE/takeover_app.log`). `ONEOS_APP=1` in `session.env` turns on
the strict checks below; without it (the developer's adb loop through
`scripts/deploy-phone.sh`) they are skipped or only warn, and the rest works
as before. Nothing here has run on a phone yet.

| Symptom | Cause | Fix |
| --- | --- | --- |
| a refused switch left the phone half switched (up to run 35: no `system.raw` stopped the switch at [4/6], after `setenforce 0`, the persist snapshot, the adb/imsd watchdogs, `disable_rescue` and the BPF map update, none of them undone) | every check sat somewhere in the middle of `switch_to_lineage.sh` or in `master_prepare.sh`, which only runs after One UI's framework is stopped | a preflight at the top of `switch_to_lineage.sh` runs every refusal before the first change: root, the tools, the namespace, the stage, the staged files, `guards.txt`, the `bridges.sh` floor, nothing mounted under the stage or bridged, and (app) `files.sha256`, `system.raw.id` and `session.env`. A refusal prints `PREFLIGHT REFUSED: <reason>` and `Nothing on the phone was changed`, exit 2. The persist snapshot is then the first change; if it fails the switch stops there (exit 1). `master_prepare.sh` keeps its own checks |
| bridges that One UI's installd never sees | a root shell can run in a mount namespace of its own (KernelSU's per-app namespace option); binds made there do not reach installd and artd in init's namespace, so they would write into One UI's real /data for the guest (run 25) | `switch_to_lineage.sh` and `master_prepare.sh` require `readlink /proc/self/ns/mnt` = `readlink /proc/1/ns/mnt`. The app's launch enters init's namespace; the adb loop is run once more there with `busybox nsenter -t 1 -m` and refused if that does not help. No opt-out |
| a stage another tool wrote to (OneLineage's switcher copies its own scripts in on every start; the S26U's old stage is mode 777) | only `services_patched.jar` and `oplus-services_patched.jar` were checked (`guards.txt`); scripts, `zygote_exec`, `bridges.sh`, `surfaceflinger_patched`, the other jars, payloads and RROs were bound or run as root unchecked, and any leftover `framework_patched.jar`, `libaudio*_patched.so`, `PermissionController_patched.apk` or `clean_apex_info_list.xml` is bound too | app only: the stage must be root's and not group/other writable; every line of `files.sha256` (`<sha256>  <flat name>`, written by the app, everything but `system.raw`) must match a root-owned regular file, and it must list the 7 scripts, `zygote_exec`, `guards.txt` and both guarded jars; a flat `*_patched*`, `*_payload.img`, `*.apk` or `clean_apex_info_list.xml` it does not list is refused; `system.raw` (hashed once at staging) must still have the `stat` dev:inode:size:mtime in `system.raw.id` (`<size> <sha256> <dev:inode:size:mtime>`, one line or two). `master_prepare.sh` does not extract a missing payload from the image then (it would be unlisted and unchecked) and refuses one the image has but the stage lacks |
| busybox or resetprop from wherever a search found them; no resetprop silently skipped One UI's persist snapshot and restore | OneLineage's `find /data -name busybox` fallbacks; `guest_props.sh` exited 0 without resetprop | only the root manager's own copies (`/data/adb/ksu/bin`, `/data/adb/ap/bin`, `/data/adb/magisk` for busybox); the adb loop may still fall back to `command -v`. busybox must have `sh mount umount losetup unshare nsenter pivot_root setsid awk grep sed` and show a `losetup -r` (the adb loop only warns about the latter); resetprop must read `ro.build.fingerprint` like getprop; a missing resetprop is fatal everywhere (`guest_props.sh` exits 1). Without `getevent` the app is refused (no return keys) |
| `session.env` that turns the way back off | `ONEOS_RETURN_MAX=0` also disarms the keys; `ONEOS_RETURN_KEYS=0`, `ONEOS_RETURN_MODE=inplace`, `ONEOS_LOGCAT=0`, `ONEOS_STOCK_SF=1`, `ONEOS_KEEP_FOLD_LAYOUT=1` | the app's root script never writes them; the preflight checks again (app): `ONEOS_RETURN_MAX` 300..900, `ONEOS_RETURN_BLACK` 60..max, keys 1, mode reboot, logcat 1, stock SF 0, fold layout 0, `ONEOS_GUEST_A11Y_SHORTCUT` 0 (ColorOS would take the return chord for TalkBack, run 34), `ONEOS_PREPARE_ONLY` 0 or 1, no `ONEOS_TUNNEL_*`; `session.env` must be root's and say `ONEOS_APP=1` |
| the gap splash belonged to the OneLineage switcher (`com.wewaffles.onelineage/.SplashActivity`) | hardcoded in `switch_to_lineage.sh` | `ONEOS_SPLASH_COMPONENT`, default `com.fahadali.oneos/.ui.GapSplashActivity` (not exported; root starts it, same `Status: ok` / `settled` handshake); only `package/.Activity` characters are accepted. A component that is not installed means no freeze, the black gap of run 32. The pre-created guest package dirs in `master_prepare.sh` name `com.fahadali.oneos` instead of the switcher |
| writes into One UI's app data and LineageOS leftovers | OneLineage copied One UI Home's databases to `/data/local/tmp/lineage_backups` on every switch and back over the live ones on return (never emptied); `fix_app_dirs.sh` made LineageOS's `com.android.messaging` the default SMS app on every boot (ColorOS has `com.android.mms`); the activator installed microG from flag files; dirs for Launcher3, LatinIME (chowned to 10109) and LineageSettings | all removed. An old `lineage_backups` on a phone is neither read nor written any more |
| a hard reset during a session leaves One UI with ColorOS's `persist.*` props, its language among them, until the next switch, which only deletes added ones | `return_to_oneui.sh` never ran; `switch_to_lineage.sh` sets `persist.sys.locale` to the guest's | `guest_props.sh recover` (for the app, after a reboot): restores the snapshot like the return (deletes added, restores changed, `persist.sys.boot.reason*` kept), drops the memory-only prop lists of that boot. Exit 0 done or nothing to do, 3 the session may still run (same boot or the stage mounted; nothing touched), 4 snapshot not trusted (moved to `$STAGE/attic/<epoch>/`, not used) |
| an old stage's persist snapshot would delete One UI props missing from it (S26U: a stage from before the app) | `snapshot-persist` cleaned up after any `persist_session.active` with whatever `persist_props.snapshot` was there | `persist_session.active` is now a record (`format=2`, `boot_id`, `epoch`, `app`, `profile`, `stage_marker` = sha256 of `.oneos_stage` or `none`, `snapshot` = sha256 of the snapshot). Only a matching record is used (`recover` also needs `app=1` and the same `.oneos_stage`); anything else is moved to the attic unused. `guest_props.overridden`/`.added` from an earlier boot are dropped, not replayed (`guest_props.boot`). `guest_locale` must be a language tag |
| which session an `auto_return.log` line belongs to | every session appends to it | each switch writes `=== OneOS session <date time> epoch <s> boot <boot_id> app <0/1> profile <id> return max <s>s black <s>s keys <0/1> ===` first |
| a session started from the app could lose its way back when the app dies | ActivityManager kills an app's whole cgroup; processes started by its su inherit the app's cgroup and OOM score | `switch_to_lineage.sh`, the auto-return watcher and the Volume Up + Volume Down readers move themselves to the root cgroup (`/sys/fs/cgroup/cgroup.procs`) and set `oom_score_adj` -1000; `return_to_oneui.sh` inherits it from the watcher. To confirm on a phone: the session survives the app being killed |
| a tester's phone got adb in the guest though One UI had USB debugging off | the adb watchdog, the host `adb_keys` copy and the guest's `adb_enabled=1` were unconditional | only when One UI's `adb_enabled` is 1 (or `persist.sys.usb.config` has adb), read before the framework stops (`$STAGE/host_adb_on`, `data/oneos_host_adb` for `fix_app_dirs.sh`). Off: no watchdog, no keys (an earlier stage copy is removed), the guest's setting is left alone |
| the guest could write the root manager's data and One UI's APEX store | host `/data/adb` (for the guest's busybox path) and `/data/apex` were bound read-write into the guest's /data | `master_prepare.sh` copies busybox to `data/oneos_bin/busybox` (like `zygote_exec`; the file must be named busybox: run 36a named it `oneos_busybox` and every call answered "applet not found", so the guest refused to start), `master_inner.sh` uses it after the pivot, and both binds are remounted `remount,bind,ro` (that bind only; host /data is checked to still be read-write, both its bind and its filesystem). `takeover.log` logs both binds' options next to `su -c id`. App: a writable `/data/adb` stops the start; a writable `/data/apex` is a warning. `ONEOS_GUEST_DATA_ADB_RW=1` / `ONEOS_GUEST_DATA_APEX_RW=1` keep one writable (adb loop only) |
| `system.raw` could change under the app's check | a plain loop device lets a read-only ext4 mount replay its journal into the file | `losetup -r` for `system.raw` and every payload; with the app, a `system.raw` loop device that sysfs (`/sys/dev/block/<major:minor>/ro`) does not show read-only stops the start (the adb loop warns) |
| a failed `oplus-services.jar` bind started the guest with ColorOS's own (no storage, installd-caller and sysrq guards in it) | only `services.jar` was checked by dev:inode after its bind | the same dev:inode check for `oplus-services.jar`; missing or not the staged jar stops the start |
| on a bar phone the cover touch-IC writer could find the only touch IC | the S Ultra has a single `/sys/class/sec/tsp`, which the `sec_touchscreen` match takes as TSP1 | the activator writes touch ICs only with the fold form (`ONEOS_GUEST_FORM` fold), a `flip` lid switch and a `sec_touchscreen2` (and, as before, the fold layout); `ONEOS_COVER_TSP=0` still turns it off |
| fold ports 147/148 were the Fold's only | hardcoded in `master_inner.sh` | read from the host's `input-port-associations.xml` (`sec_touchscreen` inner, `sec_touchscreen2` cover), 147/148 when it does not say; logged as `Fold ports` |
| the call SIM loop sends `g_call_sim_slot` to any audio HAL | its keys and the 0x10 swap were read from the F8U's HAL only | the loop first looks for both `g_call_sim_slot` and `updateSecVSID` in the vendor audio libraries (`/vendor/lib64/*audio*.so`, `/vendor/lib64/hw/*audio*.so`, `/vendor/bin/hw/*audio*`) and stops with a line in `call_audio.log` when no file has both. `ONEOS_GUEST_CALL_SIM=2` skips the look, `0` turns the loop off |
| the call SIM loop never knew whether the HAL got `g_call_sim_slot` (Pixel runs 41-43: AudioFlinger returned OK, the HAL never saw the key, SIM 2 calls silent) | a guest audioserver without the QTI vendor extension drops vendor keys without a log line (docs/pixel-guest.md, run 43) | every send is checked against the HAL's own `configured g_call_sim_slot` line (looked at again 1 s later before it counts as lost); ColorOS (property true) keeps the AudioFlinger path, whose sends now wait for the guest audioserver to register (an idle send before that was lost), and when a send is not delivered the keeper tries the direct `IModule/default` path once, only with an idle 0x01/0x02 (never a 0x10); `ONEOS_GUEST_CALL_SIM_VIA=af\|hal` forces the first path |
| ColorOS's system_server died at boot phase 550 on the S25U (session f075d93a, app 0.3.1, fresh stage): `NullPointerException` in `AdbService$Lifecycle.onBootPhase`, "ADB data directory does not exist" and "Failure starting AdbService" 6 s earlier; the F8U booted the same image | the guest's `/data/misc/adb` was only ever created by the host `adb_keys` copy, so a phone with USB debugging on but no `adb_keys` (nothing allowed over USB yet) had none, and ColorOS's Android 17 `AdbDebuggingManager` turns the missing directory into null key files that the `AdbService` constructor throws on; the Lifecycle then calls `systemReady()` on a service it never made | `master_prepare.sh` always makes `data/misc/adb` (system:shell 02750, labelled with the rest of `data/misc`). What goes in is unchanged: the host's `adb_keys` only with One UI's USB debugging on, never its `adb_temp_keys.xml` |
| started from the app, `master_prepare.sh` printed "can't create temporary file : No such file or directory" four times (run 36a and the S25U session) and `fix_app_dirs.sh`, `ensure_app_storage.sh`, `net_fix.sh` and `app_storage_loop.sh` were never written; the adb loop never saw it | mksh writes a long here-document to a temp file in `$TMPDIR`, a directory it checks once at start-up; the app-started shells had one that was gone by [5d] (the bridges hide an app's cache folder under `/data/user/0`), while adb shell's is `/data/local/tmp` | `switch_to_lineage.sh` exports `TMPDIR=$STAGE/tmp` (root's, 0700, refused as a link) after the preflight; `master_inner.sh` uses the guest's `/data/local/tmp` after the pivot |
| the first session on a fresh stage kept ColorOS's touch-idle refresh rate (the dry run warned "guest VRR config not staged") | `oplus_vrr_config.json` was written into `data/system` before anything created that directory | `master_prepare.sh` makes `data/system` first |
| the S25U came back from its first ColorOS session (0.3.2) unable to unlock user 0: "Phone restarted - unlock your phone", Home screen greyed out, no screenshots (Direct Boot state), no lock set in either OS, nothing to enter; the phone had to be reset | the guest's SyntheticPasswordManager enrolled user 0's synthetic password in the phone's weaver hardware, in the first slot it saw as free: slot 0, which on a never-reset phone is One UI's live protector. The Fold was spared by chance: its live protector is in slot 2 and only a stale record sits in slot 0, which the guest did overwrite (`spblob/*.weaver` on both sides) | `patches/guest_no_weaver.py`: `getWeaverServiceLocked()` returns null, so the guest takes the no-weaver paths (software or gatekeeper protectors) and never enrolls, reads or writes a slot; OPPO's `ISyntheticPasswordManagerWrapper.getWeaver()` goes through the same method. `master_prepare.sh` removes a guest lock state that still has weaver records (stage only), so the guest makes a fresh protector on its next boot |
| a test of the Find X9 Ultra image staged the Find N6 overlays | `deploy-phone.sh` always pushed `out/overlays`, and a set's `guards.txt` vouches for its own jars | `deploy-phone.sh --overlays <dir>` (or `OVERLAYS=<dir>`), default `out/overlays`; it checks the set's jars against its `guards.txt` before touching the phone, and keeps the stage root's 0755. On a stage the app set up it notes that the app's `files.sha256` no longer matches |
| the Find X9 Ultra IN image never started: plain Android boot animation on the cover, black, the auto-return after 40 s (run 37, Fold, 0.3.3) | OPPO's global images keep their region overlays in `my_product/cust/<region>/overlay` (24 regions in the IN build). OPPO's own first stage maps the phone's region onto an allowed path; the container does not run it, so ColorOS's package manager registers them at the raw path, the zygote opens one while preloading, and its file-descriptor allowlist (`fd_utils`: `/my_product/overlay` allowed, `/my_product/cust` not) aborts the fork of system_server: `JNI FatalError called: (system_server) Not allowlisted (72): /my_product/cust/IN/overlay/GmsConfigOverlaySearchSelector` | `master_prepare.sh` hides every `my_product/cust/*/overlay` folder for the session (read-only tmpfs; the region's dialer, contacts and Google config tweaks do not apply). The N6 and X9U CN images have no overlay folder under `cust`, so nothing changes for them. `ONEOS_GUEST_REGION_OVERLAYS=1` keeps them (adb loop only) |
| the Galaxy S25 (SM-S931B) went black and came back on every session after its first (0.3.4, X9U CN) | the first session's system_server died before ColorOS had written all of user 0's settings: `settings_secure.xml` was there, `settings_global.xml` was not. Every later boot then took SettingsProvider's upgrade path ("No settings state .../settings_global.xml", "Upgrading settings for user: 0 ... from version: 201") and crashed on the missing file (NullPointerException in `SettingsRegistry$UpgradeController.onUpgradeLocked`, "Unable to get provider SettingsProvider") | `master_prepare.sh` moves a partial set (some but not all of `settings_global/secure/system.xml`) to `data/system/users/0/oneos-partial-settings-<epoch>/`, never deleted, so ColorOS writes all three fresh. A stage that ran has all three, one that never booted has none: both unchanged. What stopped the first session is still open (its guest log was not in the bundle) |
| the Galaxy S25's status icons ended next to the camera, with the right half of the bar empty (0.3.5, X9U image) | the image's `ro.oplus.display.screenhole.positon` is the Find X9 Ultra's hole, `679,40:762,123` on its 1440 px panel. `OplusStatusBarUtils.isHoleType` compares it raw with this panel's width: on the S25's 1080 px the hole lies right of the middle (540), `HOLE_RIGHT_TYPE`, so the system icons end at the hole's left edge (as on the Fold's inner screen in run 36a). The S25 Ultra at One UI's FHD+ (1080 px, hole 521..560) is the same; the S26 Ultra (1440 px, 680..760) matches the image | `switch_to_lineage.sh` reads the phone's own hole from One UI's display service before it stops it (top bounding rect of the one default-capable internal display, `$STAGE/host_screenhole`; S25 `511,0:569,103`), and on bar phones `guest_props.sh` gives ColorOS that instead of the image's (`HOLE_CENTER_TYPE`: clock left, icons at the right edge). Unread = `0,0:0,0`, no hole. The fold layout keeps its no-hole value. `ONEOS_GUEST_INNER_HOLE=image` keeps the image's |
| the Galaxy S24+ (Exynos, SM-S926B) had ColorOS's clock and all its status icons in the left half of the bar, nothing right of the camera (0.4.89, a user's screenshot; no log of that phone yet) | the picture is `HOLE_RIGHT_TYPE`'s. `guest_props.sh` places the hole for the panel's whole width (1440 px: about `686..756`), and ColorOS compares it raw with the width of its own display (`isHoleType stableDisplayWidth: N`, the display's width in every ColorOS report; on a Fold the panel in use). On a display 1080 px wide that hole lies right of the middle: the guest ran the panel in One UI's FHD+ mode. The Snapdragon phones in the reports run the whole panel whatever One UI was set to | 0.4.90: `oneos_switch.sh` writes `$STAGE/guest_panel_fit.sh`, asks the guest's window manager for its display size as soon as it answers (`fit_guest_panel`, through the takeover process's mount namespace, before SystemUI starts) and places `ro.oplus.display.screenhole.positon` for that size (S24+ at FHD+: about `515..567` of 1080, `HOLE_CENTER_TYPE`). Only for the main panel's own shape, only over a value OneOS placed, nothing where the guest has the whole panel. The UI activator checks once more and logs `guest display 0: WxH (the whole panel: WxH); camera hole property: ...` in every bar-phone session. The density (One UI's dp width) and, on Pixel and HyperOS guests, the status bar height and corner padding go by the guest's width the same way. Until a phone has it: One UI's screen resolution on WQHD+ before starting |
| OxygenOS 16's status bar was laid out for a corner camera on every phone: clock pushed right of a centred camera on 1080 px phones (Galaxy A35: 607 px in), icons ending at the camera on 1440 px ones. 0.4.81's fix changed nothing on the screen | the image's `config_stableDeviceDisplayWidth` is its own phone's 1272. 0.4.81 wrote the panel's size into `display-manager-state.xml`, which DisplayManager prefers (`mStableDisplaySize` was the panel's in the seven OxygenOS sessions after it), but OPPO's SystemUI reads the resource itself: `ScreenSizeHelper--> StableDisplayWidthSize = config_stableDeviceDisplayWidth: 1272`, then `isHoleType stableDisplayWidth: 1272, holeLeftPosition 507,holeRightPosition 573 ,holeType HOLE_LEFT_TYPE` (A35 b06d044f). ColorOS sets no such resource and goes by its display | 0.4.90: the UI activator overlays `android:integer/config_stableDeviceDisplayWidth` and `...Height` with the size the guest runs its display at (fabricated overlays `OneOSStableWidth` and `OneOSStableHeight`, bar phones, only where the image sets one), log line `[UI Activator] stable display size: ...`. SystemUI may keep the old value until it starts again; the overlays stay for the next session. `ONEOS_GUEST_STABLE_SIZE=0` turns both parts off. Not seen on a phone yet |

## Operational pitfalls

- **Wifi drops the moment One UI stops** (`wlan0 linkdown`): One UI's WifiService
  owns the connection. Anything over wifi (an ssh app's tunnel, a root tunnel) is gone
  until the guest's WifiService runs. Use USB adb; the laptop's adb server can
  be forwarded to the build server (`ssh -N -R 127.0.0.1:<port>:127.0.0.1:5037`).
- **Returning to One UI often ends in a reboot** (`rescueparty_by_bootchecker`
  or a plain reboot shortly after). Temp root does not survive it.
- **A frozen panel is not a hang**: when the guest's SurfaceFlinger cannot
  present, the panel keeps showing One UI's last frame (black, or the charging
  icon).
- **The OneOS screen at the start of a switch is One UI's frozen
  surfaceflinger** (gap splash, run 33 on): switch_to_lineage.sh starts a
  splash activity (since build 2 the OneOS app's
  `com.fahadali.oneos/.ui.GapSplashActivity`; `ONEOS_SPLASH_COMPONENT` names
  another, e.g. `com.wewaffles.onelineage/.SplashActivity` while the old
  switcher is still installed), then in [4b/6] stops One UI's surfaceflinger with
  SIGSTOP instead of killing it, so its composer client keeps that frame on the
  panel through master_prepare.sh (run 32: 31.6 s of black from 13:09:24.55 to
  ColorOS's first frame at 13:09:56.18). master_inner.sh kills it right before
  the composer restart; a splash still up long after that means master_inner.sh
  never got there (switch_to_lineage.sh kills it after 20 s anyway, see
  `gap_splash.log`). `ONEOS_GAP_SPLASH=0` brings the black gap back.

## Likely next blockers

ColorOS's device compatibility matrix lists 101 optional OPPO HAL entries; none
exist on the Samsung vendor. "Optional" only means VINTF will not refuse them;
ColorOS code that assumes them can still crash, as the display one did. The
areas, roughly in the order system_server meets them:

- **Display/graphics**: displaypanelfeature, displaycolorfeature, mmdisplayfeature,
  cwb, MixLut3D, Qualcomm display.config (`Unable to create IDC client`). Mode
  switching and color modes will not work even once the panels are up.
- **Power/thermal/performance**: power, powermodel, performance, thermalmntcfg,
  charger, urcc, rpmh. PowerManagerService and battery UI.
- **Input**: touch, pogo_keyboard, lmvibrator (haptics).
- **Fold handling** (run 31, stage 1): ColorOS folds like the Find N6 (same
  panel ports 147/148, same state ids 0 CLOSE / 3 OPEN, AOSP remap model; never
  add `oplus.software.fold_remap_display_disabled`, it switches ColorOS to OPPO's
  fixed two-display model). The lid switch (input device `flip`, SW_LID) drives
  Samsung's states 0 and 3; with our layout file folding makes the cover
  display 0, unfolding brings the inner panel back. Touch follows the panels
  through the static port associations (`sec_touchscreen` port 147,
  `sec_touchscreen2` port 148). Samsung powers each panel's touch IC from One
  UI's sysinput HAL, which nothing runs in the guest: run 31's cover lit up but
  never took a touch. The HAL writes `/sys/class/sec/tspN/enabled` with
  `<display state>,<event>` (2 ON / 1 OFF, 0 early / 1 late around the panel
  power change) and `set_fold_state,<1 folded / 0 open>` to `tspN/cmd`; tsp2 is
  the cover (`sec_touchscreen2`). Since run 32 the activator's fold monitor does
  that for tsp2 only (fold: set_fold_state,1, 2,0, cover backlight on, 2,1;
  unfold: set_fold_state,0, 1,0, 1,1) and logs it in `diag_fold/fold_test.log`;
  the inner IC is never written. `ONEOS_COVER_TSP=0` turns it off.
  `ONEOS_GUEST_FOLD=off` = run 30 (inner only, cover switched
  off); `ONEOS_GUEST_DEVICE_STATES=oneos` adds the AOSP fold properties
  (OUTER_PRIMARY/INNER_PRIMARY, wake on unfold, no sleep on fold). Later: the
  OPPO display overlay's cutout uniqueIds are the Find N6's, so both panels get
  the inner cutout; half-open from the folding-angle sensor; cover brightness
  config; screenrecord follows display 0 at a fixed size. Run 32:
  `oplus.software.feature_unfold_width_small_high` (fold form) tells SystemUI's
  side gesture that the open panel is portrait; without it the right back zone
  was computed for a 2504 px wide panel and sat off screen
  (`ONEOS_GUEST_UNFOLD_PORTRAIT=0` leaves it out).
- **Biometrics/security**: biometrics, fido, keymint/weaver (OPPO's), mkey,
  olck_ca. Fingerprint and face unlock will not work; lock screen PIN should.
- **Radio**: radio, ims, esim, appradio. ColorOS's telephony stack against
  Samsung's RIL; calls/SMS may need One UI's imsd like OneLineage. 5G (run 30):
  Samsung's RIL never sets `isEndcAvailable` (false even while One UI is on 5G
  NSA), so Android and ColorOS show 5G only while an NR leg is attached, which
  needs active mobile data; One UI behaves the same. ColorOS shows the mobile
  type even on Wi-Fi, so on Wi-Fi it reads 4G: test 5G with Wi-Fi off. ColorOS's
  NR-mode/SA calls go to OPPO's vendor radio service, which does not exist here
  (`RILExtJ ... Radio is null`); the modem keeps One UI's NR setting. Run 32:
  5G entries in SIM > Preferred network type need `support_dual_nr` (bound
  since run 33) on the SIM without mobile data; without it they show only on
  the data SIM. Android marks NR connected only for an NR channel that carries
  the internet data call, so the 5G icon also needs guest mobile data on (it
  was off all of run 32). Calls fall back to 3G (no IMS voice in the guest).

  Run 34: no signal bars on either SIM. Samsung's RIL sent the guest no
  currentSignalStrength indication after boot, although the indication filter
  (127) and reporting criteria were accepted and other network indications kept
  coming. AOSP polls only for opportunistic subscriptions, so the guest kept the
  all-invalid value read right after RADIO_POWER on. One UI gets its bars from
  Samsung's own SehSignalBar indication and sends Samsung OEM_HOOK_RAW screen
  messages (`1182000D...`, `11980007...`) on every screen change; the guest sends
  neither. `guest_signal_poll.py` makes OplusSignalSmooth poll every 20 s while
  the screen is on (`ONEOS_GUEST_SIGNAL_POLL=0` turns it off). Run 35 to confirm.
  Images without OplusSignalSmooth (Pixel, run 43) get the same poll through
  AOSP's TelephonyComponentFactory injection instead (docs/pixel-guest.md,
  "Signal bars").
  5G in run 34: one NR leg appeared at 16:29:40, before mobile data was up
  (empty contextIds, `Endc: false`). After the data call, every physical channel
  config was LTE or LTE_CA, and One UI was on LTE_CA at the same spot afterwards,
  so there was no NR to show.
- **Camera**: camera, cameraextension, engcamera, camera_audio. The OPPO camera
  app will not work with Samsung's camera HAL.
