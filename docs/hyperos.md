# HyperOS guest: guards and audit

The HyperOS image is built from the Xiaomi 18 Fold (lhasa) CN OTA,
OS4.0.26.0.XPNCNXM (build CP2A.260605.016, MysticGSI's HyperOS patch set).
It is not in the app yet. This page covers what keeps it away from One UI's
data before it is offered (audit of 2026-10-25).

## What runs in system_server

The system server class path has two Xiaomi jars next to `services.jar`
(`/system/etc/classpaths/systemserverclasspath.pb`):

- `system_ext/framework/miui-services.jar`: Xiaomi's framework. It runs in the
  same system_server, and has its own copies of AOSP code that reach the phone
  without going through the guarded services.jar paths.
- `system_ext/framework/apprecovery.proinstaller.jar`: an auto-install service.

## services.jar

Every guard OneOS applies to services.jar applies to HyperOS's, with no
HyperOS-specific code apart from one fix. `guest_no_new_users.py` used to
stop on HyperOS. Its check that only `addUserDataLU` writes `mUsers` also
flagged `repairProfileGroupIdIfNecessaryLP`, which reads `mUsers` but writes
only to a SparseArray it creates itself. The check now skips such methods.
`addUserDataLU` writes the field itself, so the ColorOS and Pixel images give
the same result as before. `scripts/check-dex.py` passes.

## miui-services.jar (`switcher/patches/miui_guards.py`)

Each of these methods becomes a bare return (false for the boolean one):

| Path | Methods |
| --- | --- |
| Recovery: a recovery command in the boot control block, then reboot | `SystemServerImpl.rebootIntoRecovery`, `BcbUtil.setupOrClearBcb` (a copy of RecoverySystemService's `ctl.start setup-bcb` and uncrypt socket code) |
| Factory resets | `RescuePartyXM.executeFactoryReset` and its Runnable (`RecoverySystem.rebootPromptAndWipeUserData`), `MiuiInitServer.doFactoryReset`, `LiteFactoryResetImpl.startLiteFactoryReset` |
| Packages in /data/app (One UI's in a session) | `MiuiInitServer.deletePackagesByRegion`, `PreinstallApp.copyPreinstallApps`, `installCustApps`, `installVanwardCustApps`, `MiuiPreinstallHelper.performLegacyCopyPreinstall`, `installCustApps`, `installVanwardApps`, `batchInstallApps`, `copyLegacyPreisntallApp`, `copyMiuiPreinstallApp`, `deleteArtifactsForPreinstall`, `onStartJob` (the background job that removes native libraries) |
| Memory extension on vold | `ExtendMImpl.startExtM` |
| Xiaomi's OEM netd methods, sent to One UI's netd | every `MiuiNetworkManagementService` method that uses `IOemNetd` (28: firewall rules, QoS, Wi-Fi limits, `setPidForPackage`, `setOemNetd`; the build stops on another count) |

Three more changes:

- `RescuePartyImpl` sets `sys.powerctl` itself ("Config Reset"). It now sets
  `oneos.guest.powerctl`, the same change `guest_power_guards.py` makes in
  PowerManagerService.
- `MiuiGcImproveImpl` calls `IVold.setDiscardIoAwareGran`, a Xiaomi vold
  method. The call is removed.
- `ShutdownThreadImpl.showShutdownAnimOrDialog` set `service.bootanim.exit`
  and `ctl.start bootanim`. The guest shares One UI's init, so this would have
  started One UI's boot animation, which would then cover One UI after the
  return. Both setprops are removed, and the guest's own shutdown animation
  still runs.

The jar also gets the guards oplus-services.jar gets:

- `guest_storage_guards.py`: it finds nothing here today and runs so that a
  later build cannot add a call unnoticed.
- `guest_installd_abi.py --callers`: `AppCacheOptimizer`'s own
  `IInstalld.Stub.asInterface` goes through OneOSInstalldProxy.
- With "gvld", `guest_own_vold.py --miui` moves the jar's two "vold" lookups
  (`ExtendMImpl.connect` and `AppCacheOptimizer.connectVold`) to "gvld".
  ExtendMImpl calls Xiaomi's IVold methods (`runExtMFlush` and others) by
  reflection, with Xiaomi's transaction codes. After `miui_guards.py`, the
  jar calls `rebootPromptAndWipeUserData` nowhere. The guarded methods keep no
  dead code, so that check applies to the whole jar.

Every target has to match exactly once, or the build stops (fail closed).

## apprecovery.proinstaller.jar

`InstallService.onStart` (`com.miui.me.server.auto_install`) returns at
entry (`miui_guards.py --proinstaller`).

## Session scripts

- `make-overlays.sh` builds `miui-services_patched.jar` and
  `apprecovery.proinstaller_patched.jar`, checks both with check-dex, and
  lists both in guards.txt.
- `guest_prepare.sh` checks their hashes and binds them over the guest's
  system_ext, after its overlay. An image with miui-services.jar does not
  start unless both guarded jars are in place.
- `oneos_switch.sh` checks both against files.sha256, like the other guard
  jars.
- With "gvld", `guest_start.sh` also checks that miui-services.jar is the
  gvld build.

## Checked and left as they are

- **Weaver and gatekeeper**: Xiaomi's Sec* lock classes reach weaver only
  through the guarded `getWeaverService` (null in the guest). They make no
  direct calls.
- **Runtime.exec**: every call in miui-services.jar only reads.
- **CloudControlPreinstallService**: it uninstalls through
  `PackageManager.deletePackage`, which reaches only packages the guest's own
  PackageManagerService knows.
- **MemoryFreezeStubImpl**: it calls `IStorageManager.runExtmFlushPages`,
  which goes to the guest's StorageManagerService and from there to the
  guest's vold.
- **Shared properties**: like ColorOS, Xiaomi's code sets its own `sys.*`,
  `persist.sys.*` and `persist.vendor.*` properties in the property area it
  shares with One UI. One of these is `CrashRecoveryModuleXM`'s
  `persist.device_config.configuration.major_user_impact_level_threshold=101`.
  It makes RescueParty less aggressive, and it stays on One UI after the
  return.
- **CPU**: FEAT_MOPS instructions appear only in the linker and libc, as in
  the Find N6 image.

## Twelfth run (2026-10-28): the image's own zygote_next, reverted

0.4.25-hyperos-f8u, 3 minutes: no mobile data in apps and a black wallpaper;
system_server died at 04:55:19 (`DeadSystemException` in com.android.phone and
Google Play services). The image's own zygote_next (run 11's change) started,
but every child it forked exited at once: `Resetting FileDescriptorRegistry
for subspecies`, then `Failed to poll client socket: EBADF`, `Exiting server`
(04:53:37, 04:54:39). An app zygote
(`com.android.internal.os.AppZygoteInit/<uuid>`) therefore never listened:
system_server's process start thread retried its socket every 5 ms ("Got error
connecting to zygote, retrying. msg= Connection refused", 20,000 lines) until
`Failed to connect to Zygote through socket` after 20 s, and again. No process
could start meanwhile: MiWallpaper, which the UI activator had restarted, never
came back ("pid 12968 -> none after 15 s"), Chrome's pages never loaded, and the
watchdog ended system_server. The data network itself was up: DN-102 connected
at 04:53:38 and NetworkMonitor's HTTP and HTTPS probes passed at 04:53:41.

The handover is reverted (switch, guest_start.sh, return; socket_exec keeps
--seqpacket, set r9 stays): One UI's zygote_next forks the native-only
processes again, as up to 0.4.24, and Chrome's renderers crash as in run 11
while everything else works. The likely difference from init's start is the
file descriptors zygote_next inherits through guest_start.sh and socket_exec
(stdout and stderr on a log file, the shell's own); to be tried with only the
socket and /dev/null, on a test run watched live, before it ships again.

The CPU sampler's first lines: 53% composer at the switch, then system_server,
SystemUI, zygote64 and installd at boot, logd at 44% (the log volume), and
crash_dump64 at 103% while the stack dumps ran.

## Eleventh run (2026-10-28): Chrome, heat

0.4.24-hyperos-f8u, 13 minutes. Wallpapers (home and lock) and the cover
screen's size were right; mobile data came up; Chrome, installed in the
session, opened no page, and the phone got hot.

- **Data.** SIM 1's data network (Jazz, cid 2, then cid 3 after a reconnect
  at 04:07:25) passed NetworkMonitor's DNS, HTTP and HTTPS probes and stayed
  VALIDATED; the routes (net_fix.sh table 4242) followed it.
- **Chrome.** Its renderers (`com.android.chrome:sandboxed_process0`,
  NativeOnlySandboxedProcessService) died with SIGSEGV in
  `minikin::FontCollection::readVector` / `MinikinFontSkiaFactory::skip`
  within a second of starting, 13 times in 12 s. They are forked by Android
  17's `zygote_next` (`NativeZygoteProcess`), and the one answering was One
  UI's: started at boot from One UI's zygote_next.rc (`socket zygote_next
  seqpacket 660 root system`, `persist.zygote.zygote_next.start_on_boot`) in
  init's mount namespace, with One UI's libraries, reading HyperOS's font map.
  0.4.25-hyperos started the image's own instead (socket_exec --seqpacket,
  set r9) with One UI's stopped; that broke every app zygote and was reverted
  after run 12 (above). The ColorOS image has a zygote_next too.
- **Heat.** Skin 42-44 C for the whole session, thermal status 2, under the
  heat cap's 45 C; battery 78 to 75% in 12 minutes. The log was 230 MB in 13
  minutes again, now led by the keyboard (`InputMethodService`:
  ClassNotFoundException for `com.miui.inputmethod.InputMethodBottomManager`
  from `MiInputMethodService.onCreateInputView`, about 1,000 a file), the
  freezer (`Unexpected non-cached process may get frozen soon`, wtf with a
  stack, about 860 a file, for HyperOS's `previous-improve` processes),
  `AdrenoVK-0` ("Unknown struct ... provided to vkCmdBeginRenderPass", 16,600
  a file), RadioProxyEx (9,500) and com.xiaomi.type (8,000). The last three
  join the session's log.tag list (AdrenoVK-0 at W). The sampler now writes
  the six busiest processes every 30 s to cpu_top.log, collected with the
  stage's logs, to find what keeps the CPU busy.

## Tenth run (2026-10-27): data, wallpaper, cover size, log volume

0.4.23-hyperos-f8u on the Z Fold8 Ultra, 12 minutes. The cover screen worked;
the owner saw no mobile data, a lock-screen-only wallpaper, a cover that
looked zoomed in (the Dynamic Island past the right edge), no double tap to
wake and a warm phone.

- **Mobile data.** Turned on at 23:47:27 (Quick Settings), it failed in the
  same millisecond: `VendorRILJ: setupDataCallEx`, `RadioInterfaceManager`,
  `onSetupDataCallComplete. resultCode = 4`, cause `RADIO_NOT_AVAILABLE`.
  `VendorRIL.setupDataCall` (xiaomi-opt-telephony.jar) calls RIL's own only
  when `XmTelephonyUtils.ModemProvider.IS_XRING` is false; that reads
  `ro.vendor.radio.modem.provider`, else `ro.mi.os.soc.vendor`, which the
  image's build.prop sets to `xring`. Xiaomi's radio extension is not on a
  Samsung phone (`RadioProxyEx: getRadioProxy: ready = false`, 33,000 lines).
  The APNs loaded (Jazz for SIM 1 once the carrier config came), RIL bound
  IRadioData 2.3 for both SIMs, and SIM 1 was the data SIM. guest_props.sh
  sets `ro.vendor.radio.modem.provider=qcom` on Qualcomm phones (One UI does
  not define it); `IS_QCOM` only moves the temporary data SIM switch in calls
  to AOSP's code.
- **Wallpaper.** Until the first fold state commits (pending at 23:39:30,
  committed at 23:39:34, about 4 s after MiWallpaper bound), the display
  mapper's default layout shows the cover as a display of its own (#7). When
  #7 closed, MiWallpaper's `clearEngineServiceBySystemWhich` removed the home
  engines (1 and the cover's 4) while the inner home engine kept running;
  every later apply then got `requireEngineService returns null` (about 800
  times) and only the lock screen (2, 8) changed. A layout for state -1
  cannot be given: DeviceStateToLayoutMap makes it before reading the file and
  refuses a second one. The UI activator restarts MiWallpaper's process once,
  after display 0 is the only active built-in display; WallpaperManagerService
  rebinds a wallpaper that died once (it reverts to the built-in one after a
  second death within 10 s or a low-memory kill).
- **Cover screen size.** The UI activator forces 420 on the inner panel only;
  the cover ran at the base 480 (360 dp; One UI uses 422 on the same panel),
  and the Dynamic Island's window was laid out at 452 dpi past the edge.
  guest_prepare.sh's cover density (display_settings.xml, the panel's dpi
  down to a multiple of 20), ColorOS's since 0.4.10, now covers HyperOS: 420.
- **Log volume and warmth.** 1.37 million lines in 12 minutes. libxqos
  (`XQos: Failed to open /dev/xr_fbt`, `Failed to initialize`: 300,000; it
  opens the node again on every call, and `ro.vendor.qos.v1.enable` only picks
  another missing node), the Dolby renderer (`Failed to get Metadata`,
  51,000) and SurfaceFlinger's PerfFlinger client (17,000). guest_props.sh
  sets `log.tag.<tag>=S` for those three tags (liblog checks it before it
  formats a line); AOSP tags (BufferQueueProducer's `sendPerfSignal open perf
  fbt fail`, 18,000) stay. The heat cap went to 80% once (45.9 C, a minute).
- **Double tap to wake.** HyperOS sends the setting to Xiaomi's ITouchFeature
  HAL (not found, 222 exceptions). Samsung's panels (`/sys/class/sec/tsp1`,
  `tsp2`) have `aot_enable` and report KEY_WAKEUP, but no wake key reached the
  guest, whose InputReader also logged "Ignoring disabled device
  sec_touchscreen" with the screens off. No guest system has it yet; to be
  looked at with the phone attached.

## Ninth run (2026-10-27): the cover screen and every JPEG

The Settings rows had their text again and the inner screen turned off on
folding, but two things were left:

- **Cover screen on for a second, then dark**: the fold made the cover panel
  (port 148) display 0 with `FLAG_PRIVATE | FLAG_OWN_CONTENT_ONLY`, so every
  app was refused it ("Calling uid ... does not have access to display 0").
  SystemUI's context display was null and it crashed 444 times in the two
  folds (SplitLayout, ScreenDecorationsUtils, the keyguard shortcuts). HyperOS's
  LocalDisplayAdapter has Qualcomm's branch for a second built-in panel:
  presentation with `vendor.display.builtin_presentation`, else private, and
  own-content-only without `vendor.display.builtin_mirroring`. Samsung's vendor
  sets neither, and setting them would reach One UI's display HAL.
  `switcher/patches/qti_builtin_display_public.py` gives the panel AOSP's
  flags instead (ColorOS has no such branch: private only for
  `config_localPrivateDisplayPorts`).
- **Wallpapers, lock styles and themes never applied**: the lock screen
  editor's apply stopped after writing its first screenshot and never went
  on; the theme app's screenshots timed out. HyperOS's libhwui encodes JPEG
  through Xiaomi's XRING VPU (`JpegXEncoder`) and waits for
  `vendor.xring.hardware.graphics.vpu.jpeg.IJpegXCodecStore/default`, which
  Samsung's vendor never registers: 537 "Waited one second" from the first
  encode on, system_server's wallpaper thread included. guest_props.sh sets
  `debug.video.jpegopt.enable=0` and `debug.video.heifopt.enable=0` for the
  session (libhwui reads them with default 1; bit 0 clear uses libjpeg). Not
  the `vendor.video.*` pair, which One UI's vendor might read.

`xring.hardware.audio.event.IHalEventService` is waited for the same way, by
one system_server thread from boot on; left alone.

## Eighth run (2026-10-27): the image's own product and system_ext

HyperOS keeps `/product`, `/system_ext` and `/mi_ext` at the image root;
`system/product` and `system/system_ext` are absolute links, which read One
UI's folders from the host. The theme folders, the lid-switch device states
and the product/system_ext/mi_ext props all checked the links and did
nothing. They now use the image's own folders (guest_prepare.sh
`GUEST_PRODUCT`/`GUEST_SYSTEM_EXT`, guest_props.sh `GSE`/`GPR`).

## Seventh run (2026-10-26): fold, theme folders, device states, vold

The launcher, Recents and sound came up (hyos_spawner; the guest audioserver
registered after 10 s; a SIM 1 call reached the HAL on VSID_1). Four things
were left, and the return rebooted:

- **"Zoomed in", no wallpaper**: HyperOS logged `isFoldDevice: false` 3566
  times. The sixth run's `persist.sys.muiltdisplay_type=2` was never added:
  its check looked for `ro.config.fold_disp` among the props One UI lacks,
  and One UI defines that name too (Samsung's `2256,2504,1080,2520`). The
  check now reads the image's own build.prop. HyperOS's Java framework does
  not read `ro.config.fold_disp`, so Samsung's value stays. MiWallpaper still
  crashed in WallpaperTypeUtils.f for the same reason.
- **Icons, fonts, lock styles, wallpapers could not be applied**: Theme Store's
  `mkdirs` failed (chmod ENOENT). HyperOS's init rc files create
  `/data/system/theme`, `theme_magic` and `fonts` (owner `system_theme`, 6101)
  and about 45 more folders at boot; One UI's init never reads them.
  guest_prepare.sh now makes the missing ones under `/data/system` and
  `/data/miuilog` in the guest's own /data, with the rc's mode and owners, never
  through a link.
- **Cover screen never on**: Xiaomi's DeviceStateProviderImpl reads
  `product/etc/devicestate/device_state_configuration.xml`, whose states all
  wait on `xiaomi.sensor.fold_status`: "No declared device states match", no
  state was committed, and DisplayManager stayed on the inner panel's default
  layout. guest_prepare.sh binds a copy with Xiaomi's ids and properties: 0
  CLOSED on the lid switch closed, 3 OPENED on it open, TENT and HALF_OPENED
  request-only. guest_start.sh's layout gives HyperOS its own order (0 and 1 on
  the cover, 2 and 3 on the inner panel, 4 on the cover); the Pixel order had
  put 3 on the cover.
- **Return rebooted** ("vold is not registered"): the guest vold had taken
  "vold". make-overlays.sh now pins HyperOS's vold (string 0xf3fd, try_start's
  tbz at 0x6e2d4), service.incremental.so (0x64746) and its crashrecovery APEX
  (AOSP RescueParty.isDisabled), so set r7 has vold_patched and
  service.incremental_patched.so and the guest vold registers "gvld".

Also from the public track (0.4.17 friend logs): the return blanks the guest's
props instead of deleting them (One UI's property areas filled up over
sessions without a reboot), and the switch refuses below 16 KB free.

Bluetooth was not turned on in this run either. DisplayModeDirectorImpl logs
"only 0 and 1 are supported" for the cover's logical id (6); left for now.

## Sixth run (2026-10-26): launcher, wallpaper, sound

HyperOS ran for four minutes until the manual return: SystemUI, Quick
Settings and the signal worked, with no home screen, Recents or wallpaper and
no sound.

- **Launcher and Recents.** `com.miui.home` (Recents is part of it) is a rust
  package: MiuiHome.apk has no dex, its code is a Flutter library. With the
  fourth run's rust guards zygote started it with no code ("Didn't find class
  com.miui.maml.MamlProvider ... DexPathList[[]]"), 1008 times in four
  minutes; each start also asked for a CPU boost that failed on Xiaomi's
  `/dev/xr_fbt` (XQos, 258,000 log lines). The guards are gone again (they
  are left out of miui_guards.py). guest_start.sh now starts
  `/system_ext/bin/hyos_spawner` the way the image's `init.hyos_spawner.rc`
  does: as root, with its control socket `/dev/socket/hyos_spawner` (stream,
  0660 root:system) made by `socket_exec` (switcher/native, in the HyperOS set
  only). guest_props.sh adds `rust.runtime_version=3.1.0` and
  `rust.runtime_active=1` for the session, and the return deletes both and the
  socket.
- **Wallpaper.** MiWallpaper is a fold build (the image is Xiaomi's fold
  lhasa). It loads the cover screen's wallpaper records (which 4 and 8) only
  when `persist.sys.muiltdisplay_type` is 2 and then reads them anyway: an NPE
  in `WallpaperTypeUtils.f` at every start. The value lives in the phone's
  vendor props, which the GSI does not carry. guest_props.sh sets it to 2 for
  the session on fold profiles (memory only, never over a value One UI has).
- **Sound.** AOSP's libaudiohal@aidl.so reads
  `ro.audio.ihaladaptervendorextension_enabled` and, when it is true, waits
  with no time limit for `android.media.audio.IHalAdapterVendorExtension/default`.
  The image sets it (Xiaomi's vendor serves the extension) and so does One UI,
  whose value the guest reads. On One UI the service lives in Samsung's own
  audioserver, which the session stops, so HyperOS's audioserver never
  registered (servicemanager asked init to start the interface every second).
  After 60 s the audio keeper handed over to One UI's audioserver, whose
  permission controller HyperOS cannot fill ("NPC::checkPermission:
  controller never populated by system_server"). `switcher/patches/hyperos_audio_ext.py`
  changes the first letter of the property name in libaudiohal@aidl.so (bound
  over the image's as `libaudiohal_aidl_patched.so`), so the guest's libaudiohal
  reads an unset property and goes on without a vendor extension, which AOSP
  allows. One UI's property stays as it is. Calls use the same audio path.
- **Setup wizard.** The image's Provision is AOSP's 20 KB stub (it sets
  `device_provisioned` and `user_setup_complete` and turns itself off). There is
  no Xiaomi setup wizard to run, so guest_prepare.sh keeps setting both keys.
- **Calls.** None was made. SIM 2 was in service; SIM 1 had voice on 3G
  (`REG_HOME`, UMTS) while the network refused it data (`REG_DENIED`, causes
  7, 14 and 15). That is the modem and the network, not the guest.
- **Bluetooth.** Off by the fresh data's setting; it was not turned on.
- **Left as they are.** SurfaceFlinger "presentOrValidateDisplay 3
  presentFence:-1" (the cover screen), DisplayModeDirectorImpl "Invalid
  displayId: 6, only 0 and 1 are supported" (a virtual display), 2,249 times.

## Fifth run (2026-10-26): the brightness curve's range

With the Fold's port files next to the image's own (fourth run), HyperOS's
DisplayDeviceConfig loaded them and threw at once: "Min or max values are
invalid; raw min=0.0026; raw max=0.196299; backlight min=3.66255E-4; backlight
max=1.0". HyperOS's brightness range is wider than the curve, which covers One
UI's manual range only (the Pixel guest's range fits in it). For an image with
its own displayconfig folder, guest_prepare.sh now writes the curve with two
more points: 3.66255E-4 at 0.3 nits and 1.0 at 2600 nits. The second comes
from the curve's own slope (Samsung's composer maps the float linearly onto
the backlight; a quarter of it is about 660 nits), so it is the panel's peak.
The Pixel guest keeps the plain curve.

## Fourth run (2026-10-25): SystemUI up, then four more fixes

HyperOS booted to SystemUI (Quick Settings opened), with no home screen,
signal bars dropping in and out and a 3 % screen the slider did not change.
system_server then died.

- **IOemNetd, at the client.** `MiuiOnelinkNetManagerService`
  (miui-wifi-service.jar) called `IOemNetd.enableOnelinkNetSyncDrop`, and One
  UI's netd answered with a NullPointerException: it had run a Samsung method.
  Xiaomi numbers IOemNetd's transactions its own way (`enableWmmer` is 2,
  AOSP's `registerOemUnsolicitedEventListener`; Xiaomi's register is 45), and
  only `isAlive` (1) matches. miui_guards.py now makes the 54 other methods of
  `IOemNetd$Stub$Proxy` (miui-services.jar, the only copy; every caller uses
  it) throw `RemoteException` before anything is sent. AIDL callers have to
  handle that.
- **Home screen.** HyperOS starts "rust" packages (`com.miui.home`,
  `com.miui.weather2`) through a spawner service its own init starts when
  `rust.runtime_active=1`. One UI's init has none: "IOException while
  communicating with spawner", `Start proc 0:com.miui.home` 31 times.
  `RustProcessManagerImpl.activeRustRuntime`, `allowRustRuntime` and
  `isActiveRustTime` returned at entry, so those packages started through zygote
  and the property was not set (undone in the sixth run, above).
- **Signal.** `MiuiImsControllerImpl` (miui-telephony-common.jar) gets its
  phone when the IMS phone is made, and the guest has none. Its `log()`
  dereferenced the missing phone from `ServiceStateTracker.pollStateDone`, and
  com.android.phone died on every poll. `switcher/patches/hyperos_telephony.py`
  makes `log()` print -1 without a phone, and `isPseudoDsdaCall` answers
  false; `miui-telephony-common_patched.jar` is bound like the other
  system_ext jars.
- **Brightness.** The image has its own `product/etc/displayconfig`
  (`display_id_<Xiaomi panel>.xml`), so guest_prepare.sh left out the Fold's
  `display_port_147/148.xml`, and the Fold's panels had no nits mapping ("requesting
  nits when no mapping exists" 543 times; Xiaomi's brightness code works in
  nits). The two port files are now added next to the image's own (the
  overlay merges the folder), unless the image has port files of its own.

## HAL extensions (third run, 2026-10-25)

With netd guarded, system_server ran for 58 s and died in MiuiWifiService:
`IllegalArgumentException` from `ISupplicantXm.registerCallback`. Xiaomi asks
AOSP HAL binders for their extension (`IBinder.getExtension()`) and casts it
to a Xiaomi interface with `Stub.asInterface`, which does not check the
remote descriptor. One UI's HALs have Samsung's extensions. Six such casts:
- miui-wifi-service.jar: `IHardwareXm`, `IHostapdXm` (two classes each with
  their Aml variants) and `ISupplicantXm`;
- miui-services.jar: the vibrator's `IVibratorExt`.

`switcher/patches/hyperos_hal_ext.py` routes each cast through a helper
class added to the jar. It passes the extension on only when its descriptor
is the target interface's `DESCRIPTOR`, read at run time, and logs the one
it found otherwise (`OneOSHalExt`); Xiaomi's code then gets null, which it
handles. Any other `getExtension()` call, or another count, stops the build.
make-overlays.sh builds `miui-wifi-service_patched.jar`; guest_prepare.sh
binds it with the other two system_ext jars and refuses to start without it.

## netd (second run, 2026-10-25)

With the camera fixed, system_server ran for 58 s and then died in
`MiuiNetworkPolicyManagerService.systemReady`:
`IllegalArgumentException` from `IOemNetd.enableWmmer`. The guest's netd is
One UI's, whose `IOemNetd` has AOSP's two methods only (the listener
registration went through). Xiaomi's other methods were rejected, and
`setPidForPackage`, called for every new process, had already stopped apps
from starting ("Failure starting process"). A Xiaomi transaction code could
also match one of Samsung's own methods. miui_guards.py therefore makes every
method of the class that uses `IOemNetd` return at entry, and nothing
Xiaomi-specific reaches One UI's netd.

## framework.jar: camera status (`switcher/patches/hyperos_framework.py`)

Xiaomi added two fields to `android.hardware.CameraStatus` (`isAuxExported`,
`roleIdList`), read and written after AOSP's five. The guest's camera calls go
to One UI's cameraserver, which writes AOSP's five only. From the second
entry on, `ICameraService.addListener`'s array was read at the wrong offset
and came out null. At boot, BiometricService's camera manager registers an
availability callback; CameraManager read `cameraId` from a null entry and
system_server died. This was the first run on the Z Fold8 Ultra (2026-10-25),
stuck on the boot animation:

    NullPointerException: Attempt to read from field 'java.lang.String
    android.hardware.CameraStatus.cameraId' on a null object reference
      at CameraManager$CameraManagerGlobal.connectCameraServiceLocked
      at BiometricCameraManagerImpl.<init>

- **The patch:** `readFromParcel` and `writeToParcel` keep AOSP's five fields.
  The two extra fields stay false and null. Their only reader,
  `CameraInjector.updateMiCameraSDKCloud` (miui-framework.jar), returns at
  once for those values.
- **Build:** make-overlays.sh builds `framework_patched.jar` (only
  classes2.dex replaced) and lists it in guards.txt.
- **Setup:** guest_prepare.sh binds it over the guest's
  `system/framework/framework.jar` and refuses to start without it.
- **Effects:**
  - The image's boot image no longer matches, so ART compiles the boot class
    path in memory. It already did, because the image's ART module version
    differs from One UI's.
  - The smali round trip drops the test-API bit from the hidden-API flags
    (SDK,TEST-API becomes SDK); what apps may call is unchanged.

## Product layout (fixed in 0.4.16)

HyperOS's image has `/product` as a folder and `system/product` as an absolute
link to it; ColorOS and Pixel images have it the other way round.
guest_prepare.sh runs in One UI's mount namespace, where `system/product`
points at One UI's own `/product`. The first run put three mounts there: the
display config overlay on `/product/etc`, product_seapp_contexts and
split-permissions-google.xml. The in-place return found the stage's binds
and rebooted the phone (`reboot,oneos-inplace-failsafe`). guest_prepare.sh now
uses the guest's real product folder (`GUEST_PRODUCT`). Before and after its
setup it lists the mount points on One UI's partitions and refuses to start
if any was added. return_to_oneui.sh checks the same before an in-place
return.

## Google apps (0.4.16)

The image has the same Google layout as the ColorOS CN builds:
- `product/priv-app/GmsCore` holds only `m`, and Play services itself is in
  `product/apex/com.google.android.gmssystem.prodvic.apex`, which the phone
  never activates.
- `product/priv-app/GooglePlayServicesUpdater` is the same 2022 Play Store
  stub.
- Google Services Framework is in `system_ext/priv-app`.
- `product/etc/permissions/privapp-permissions-gms-cn-product.xml` grants
  `com.google.android.gms` its privileged permissions, MANAGE_USERS among
  them.

guest_google.sh therefore runs for HyperOS sets too (guards.txt lists
miui-services_patched.jar). It binds One UI's Play services and Play Store
copies over those two product folders, and hides One UI's GmsCore in the
gmssystem APEX bind (docs/coloros-google.md). HyperOS CN may still keep
Google services off until "Google basic services" is turned on in its
settings.

## Not done yet

- **Bluetooth**: not tried on the phone yet.

## In the app

HyperOS was local builds only up to 0.4.30 (owner, 2026-10-25). From 0.4.31
it is published like the other systems (owner, 2026-10-29: "publish HyperOS
... Allow all users to try ... Mention that it's for Fold8U and Fold8 but
others can test too"):

- `Images.HYPEROS_LHASA` (`hyperos-lhasa`): the .gz is on the OneOS download
  folder with the other images.
- The `hyper-f8u` set from `out/overlays_hyperos_r10` (r1 until the camera status fix, r2 until the netd guard, r3 until the HAL extension casts, r4 until the fourth run fixes, r5 until the sixth run fixes, r6 until the seventh run's vold pins, r7 until the ninth run's cover panel patch, r8 until socket_exec --seqpacket for zygote_next, r9 until 0.4.31's rebuild with the guards added since: the wipe guard and the native-only services guard), in every series download.
- An untested choice on every phone, after Infinity-X. Made for the Z Fold8
  Ultra and Z Fold8, whose cover the HyperOS fold layout drives; on the other
  phones it runs as a phone on the main screen.
- A system family of its own. HyperOS guest data (`com.miui.` packages) is
  never kept for a ColorOS or Pixel image, and theirs is never kept for
  HyperOS.
