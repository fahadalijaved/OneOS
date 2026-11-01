# Pixel as the guest

> **Renamed after 0.3.6:** the stage is `/data/local/tmp/oneos` (was `/data/local/tmp/lineage_stage`), its set-aside copies `oneos.old-<epoch>` / `oneos.trash-<epoch>` (were `lineage_stage.old-*` / `.trash-*`), and the session scripts `oneos_switch.sh`, `guest_prepare.sh`, `guest_start.sh` (were `switch_to_lineage.sh`, `master_prepare.sh`, `master_inner.sh`). The app's root script and `scripts/deploy-phone.sh` rename an old stage and its copies when they are idle.

The first system other than ColorOS: the Pixel 11 Fold image (yogi,
`google/yogi/yogi:17/CD1A.261005.003.B1`), built with MysticGSI
(the image build (MysticGSI, not in this repository)`), `out/oneos-pixel-yogi.img`.
Target for the first run: the main test phone, a Z Fold (F8U), over adb.

## Framework patches (services.jar)

Pixel's services.jar is R8 output: public final methods, p registers, no
`.line` before some returns, and the IVold / IInstalld AIDL classes inside the
jar. The patchers match both shapes; on ColorOS's services.jar the whole chain
gives the same smali as before.

| Patch | Pixel |
|---|---|
| display_mode_specs | applies (Google's SurfaceFlinger should return specs; fallback only) |
| guest_no_vold_keys | 5 calls dropped (AIDL classes skipped) |
| skip_host_apex_services | applies (registers read from the code) |
| guest_power_guards | applies |
| guest_storage_guards | 37 calls dropped, UserDataPreparer, CE unlock, quota |
| guest_installd_abi | 25 identical, 2 remapped (fsverity 0x34/0x35 -> 0x35/0x36), 28 blocked |
| guest_no_sysrq_crash | applies (Watchdog.doSysRq is public final) |
| guest_no_weaver | applies (public final there; every weaver lookup goes through it) |
| guest_own_idmap | applies (name in p0) |
| guest_own_vold | 3 lookups -> "gvld", with vold_patched (docs/inplace-return.md) |
| oplus_wait_for_service --only DefragService | nothing to do |

Pixel's other system_server jars (`/system_ext/framework/yogi-services.jar`,
`malibu-plugin-provider.jar`) have no IInstalld, IVold, keystore maintenance,
recovery, reboot, weaver, gatekeeper or sysrq calls (dexdump).

## Overlays (scripts/make-overlays.sh)

oplus-services, ims-ext-common and oplus-telephony-common are patched only when
the image has them; Google's surfaceflinger has no QTI composer client and is
not patched; guards.txt lists services_patched.jar with vold_patched and
service.incremental_patched.so (the guest vold as "gvld", run 44,
docs/inplace-return.md); the 19 APEX payloads
come from Google's `com.google.android.*` modules (i18n and runtime are
`com.android.*`). The session requires oplus-services_patched.jar only when the
image has oplus-services.jar (guest_prepare.sh refuses otherwise).

## Session scripts

Changed for Pixel: guest mediaserver (`/system/bin/mediaserver`), no
MMListService wait, Pixel's setup wizards disabled and the provisioned keys set
before HOME (not with Google services presented, see below),
`com.google.android.factoryota` disabled, fold key
`fold_lock_behavior_setting stay_awake_on_fold_key`, ColorOS's brightness floor
skipped, sound names from product build.prop, Google APEX names in the payload
checks, Pixel folders in `ONEOS_GUEST_HIDE_GMS`. Everything else ColorOS-only
skips by itself (missing files).

## First run

1. `scripts/make-overlays.sh out/oneos-pixel-yogi.img out/overlays_pixel_yogi`.
2. `scripts/deploy-phone.sh --fresh --overlays out/overlays_pixel_yogi out/oneos-pixel-yogi.img`
   (the ColorOS stage moves to `oneos.old-<epoch>`; the app's Old
   stages lists it). `ONEOS_GUEST_HIDE_GMS=1` for the first run.
3. Do not set a screen lock in the guest: gatekeeper is still the phone's.

## Run 38 (2026-10-23, Fold, first Pixel session)

Black after the OneOS splash, back in One UI after about 2 minutes (the
auto-return's reboot). Pixel's SurfaceFlinger and boot animation ran on the
inner panel (the phone was folded, the cover stayed black); then the guest
zygote died preloading `android.app.SystemServiceRegistry`:
`NoClassDefFoundError: Class not found using the boot class loader`.

Cause: Pixel 17 has no `/system/framework/framework-telecom.jar`; android.telecom
is in its telephonycore module (framework-telecom.jar on the boot class path,
service-telecom.jar on the system server's). The guest got One UI's
telephonycore, which carries only framework-telephony.jar (One UI keeps telecom
as a platform jar), so `TelecomFrameworkInitializer` was missing
(SystemServiceRegistry.registerServices -> TelecomDependencies ->
DependencyAdapter.registerServiceWrapper). Nothing touched One UI's data: the
system server never started.

Fixes for the next run:
- make-overlays.sh stages the image's telephonycore, conscrypt and profiling
  when the image has no platform framework-telecom.jar (conscrypt and profiling:
  One UI's newer builds call ART and framework APIs Pixel's lack); guest_prepare.sh
  mounts them only when staged. ColorOS's images have the platform jar.
- guest_props.sh: the guest's `ro.audio.ihaladaptervendorextension_enabled`
  (Pixel: false) wins for the session; with One UI's true the guest audioserver
  waited forever for IHalAdapterVendorExtension/default.
- Pixel has no wificond: the switch restarts One UI's (free of One UI's client
  interface) and guest_start.sh no longer starts a missing binary.
- `ro.config.isolated_compilation_enabled=false` for every guest session: the
  guest's IsolatedCompilationService would drive One UI's composd.

Seen, not fixed: the boot animation draws only on the inner panel (unfold the
phone for a run); the guest runs with One UI's identity props (fingerprint,
model).

## Run 39 (2026-10-24)

Boot animation, then black, then the auto-return. The run 38 fixes all took
(telephonycore, conscrypt and profiling mounted; no audio extension wait;
isolated compilation off; One UI's wificond restarted). Zygote preloaded and
system_server started, then died in PackageManagerService.<init>:
`IllegalStateException: Unknown source permission
com.google.android.gms.permission.ACTIVITY_RECOGNITION in split permissions`
from `product/etc/permissions/split-permissions-google.xml`: only GmsCore
declares that permission, and the guest has no GmsCore (Pixel's is in a
product APEX the phone never activates; HIDE_GMS hides the folders).
guest_prepare.sh now binds such files without their gms splits when the guest
has no GmsCore APK.

## Run 40 (2026-10-24)

The split-permission fix took; system_server got through PackageManagerService
and died in startOtherServices: VirtualDeviceManagerService.onStart ->
LockPatternUtils.registerStrongAuthTracker on a null ILockSettings.
LockSettingsService had been rejected by the verifier a second earlier
(`initKeystoreSuperKeys ... [0x7] copyRes1 v4<- result0 type=Undefined`): the
storage guard dropped AndroidKeyStoreMaintenance.initUserSuperKeys but only
rewrote a following `move-result vN`, and Pixel's code reads it into p3. Same in
SyntheticPasswordCrypto.migrateLockSettingsKey. Fixed in
guest_storage_guards.py (any register; anything else after the dropped call
stops the build), and check-dex.py now also rejects any move-result that does
not follow an invoke or filled-new-array (the shipped N6 set passes).

## Run 41 (2026-10-24): Pixel boots

First Pixel session to boot to a usable UI (Settings in the large-screen two-pane
layout on the inner panel, the taskbar, the cover screen). On the phone: sound, SIM 1,
calls and call audio work; the cover screen works. Not working: Wi-Fi (the guest
WifiService's ISupplicantStaIface.addIface fails), SIM 2, apps that need Google
Play services (Messages, Credential Manager), first boot came up in another language than One UI's;
com.google.pixel.camera.services crash-looped ~9000 times (not Play services:
see below). Returned with Volume Up + Down after 350 s.
Screenshots: out/logs/run41-pixel/screenshots/.

Causes and fixes (for run 42):
- Wi-Fi: Pixel's wifi module picks the mainline supplicant (its RRO enables it,
  SDK 37, and the guest's wifi payload has bin/wpa_supplicant_mainline). One UI's
  init starts that daemon from One UI's own wifi APEX, in One UI's namespace,
  without Samsung's overlay conf; P2P lands on wlan0 and addStaInterface fails.
  guest_prepare.sh hides the binary in the guest's wifi payload, so the guest
  uses Samsung's ISupplicant/default like ColorOS (ONEOS_GUEST_MAINLINE_SUPPLICANT=1
  keeps it).
- Camera services loop: PersistentBackgroundCameraServices registers binder
  services only Pixel's VINTF declares; the shared servicemanager checks One
  UI's and throws, and the app is persistent. Hidden for the session.
- AppSearch: Pixel's ro.appsearch.feature.enable_isolated_storage=true makes it
  start a protected VM through One UI's virtualization module; false for the
  session.
- Language: a fresh stage now starts in One UI's current language
  (settings system_locales); One UI's persist.sys.locale is only its boot
  default (on this phone another language than the en-GB it shows).
- SIM 2: both slots came up; on a fresh stage Pixel chose the carrier's first
  APN (web1) for the LTE attach and no data SIM. One-time fix inside the
  guest: SIM 2 > Access point names > the carrier's second APN (web2), and pick the data
  SIM; the stage keeps both.
- Messages and Credential Manager need Google Play services (separate work).

## Run 42 (2026-10-24)

Second Pixel boot, fresh stage (out/logs/run42-pixel). Healthier than run 41:
3 crashes instead of 9069, no crash loop. Every guard either took effect or had
nothing to act on (FRP write discarded, no gatekeeper calls, app ids from 15000,
apexd calls skipped, weaver the phone's). Host state was unchanged at return,
Samsung's supplicant served Wi-Fi, and Bluetooth came on. On the phone: SIM 2 still
had no data, the status bar was off-centre, the screen froze briefly on task
switches, and Night Light turned the screen black.

Causes and fixes (for run 43):
- SIM 2: Pixel again attached the carrier's LTE with `web1` (its first APN,
  no preferred one on a fresh stage). SIM 2 left LTE 1.3 s later and stayed on
  3G. One UI and ColorOS attach with `web2`. Run 41's manual fix cannot work:
  by the time Settings runs, the modem has given up on LTE (we tried
  `web2` and went back to `web1`). Now oneos_switch.sh records One UI's
  preferred APN per slot while One UI runs (`host_pref_apn`). Before boot,
  guest_prepare.sh writes it into the guest TelephonyProvider's
  `preferred-full-apn` prefs (`apn/mcc/mnc<slot+1>`) and drops its saved
  `apn_id`. The provider then looks the APN up by those fields; the carrier's `web2`
  matches exactly one row. The UI activator logs each SIM's slot, sub and
  preferred APN. `ONEOS_GUEST_APN=0` keeps the guest's own. The guest has no
  IMS, and after Samsung's RIL restart One UI's IMS does not reach SIM 2 either
  (the IMS gate comment in oneos_switch.sh predates this), so SIM 2 calls
  fall back to 3G.
- Status bar: SystemUIGoogle leaves 20dp for the privacy dot at the end and
  only the corner padding at the start. The corner padding is the framework's
  0dp on Samsung's vendor partition (Pixel's own vendor overlay sets it). New
  static RRO `OneOSPixelStatusBar.apk` (switcher/overlays/pixel_statusbar):
  corner and dot padding 8dp, end padding 4dp also at sw600dp. It goes in the
  guest's `/oem/overlay` when the guest has SystemUIGoogle.
  `ONEOS_GUEST_STATUSBAR_PADDING=0` leaves it out.
- Status bar height (0.4.18, a Galaxy S26 Ultra user: the bar far taller than
  the camera hole, higher than One UI's): the image's own device overlays in
  product, above OneOS's in /oem, give the guest the Pixel's cutout and status
  bar height. oneos_switch.sh saves One UI's cutout spec and status bar height
  (`host_statusbar`, phones with one internal display) before One UI stops,
  and the UI activator makes four fabricated overlays from them
  (`com.android.shell:OneOSCutout`, `OneOSCutoutRect`, `OneOSStatusBarHeight`,
  `OneOSStatusBarHeightPortrait`) and enables them. Fabricated overlays are
  mutable, so enabled they come above every static one. The S26 Ultra's: a
  21 x 37 dp cutout, status bar 30 dp. `ONEOS_GUEST_HOST_CUTOUT=0` leaves them
  out. Untested on a phone.
- Freezes: SurfaceFlinger dropped to 1 Hz at every window transition (9 times,
  1-2.4 s each). The app-request render range was [0, 120]; ColorOS kept
  [120, 120]. guest_start.sh now pins both ranges of each panel to [60, 120]
  with SurfaceFlinger's transaction 1035. Its layout (i32 mode, i64 display,
  f min, f max) was checked in the image's surfaceflinger. While pinned,
  SurfaceFlinger ignores DisplayManager's policies, its thermal cap included.
  `ONEOS_GUEST_SF_PIN=0` leaves the ranges to DisplayManager.
- Night Light: the colour matrix stayed all zeros because
  `config_setColorTransformAccelerated` is false without Pixel's vendor
  overlay. guest_props.sh sets `persist.sys.overlay.nightmode=true` for the
  session (memory only), which enables the image's treble NightMode overlay.
  `ONEOS_GUEST_NIGHT_LIGHT=0` leaves it out.
- Bluetooth works at the stack level, but none of One UI's pairings were in the
  guest. Pairing a One UI device again in the guest would replace its key, and
  One UI's pairing would stop working (same Bluetooth address). Now One UI's
  `bt_config.conf` is copied one way into the stage at each switch.
  `ONEOS_GUEST_BT_IMPORT=0` skips the copy. Not checked yet: whether One UI keeps
  the link keys in plain text. Until a run shows the devices working, don't pair
  One UI's devices in the guest. (Run 43: the import as it was broke Bluetooth
  audio; see Bluetooth below.)
- Wi-Fi: wlan0 came up and scanned, but no network was joined (the stage had
  none saved). Pixel's wifi module drives nl80211 itself and never uses
  wificond, so the comments were corrected. New: verbose Wi-Fi logging, and a
  `diag_wifi` capture 45 s after Wi-Fi comes on.
- Seen, not fixed: all 224 packages failed first-boot dexopt (NullPointerException
  through One UI's artd, as in run 40). Pixel Launcher crashed once opening Home
  settings. The guest doesn't know about the cover's camera hole.

Check in run 43: "Guest attach APN" and "SF render rate pinned" lines, and a
"Bound guest /oem" line with OneOSPixelStatusBar.apk, in the takeover logs. In
all.log, the first `SET_INITIAL_ATTACH_APN [PHONE1]` should be `web2`, with no
`fps=1.00 Hz` lines. `cmd overlay list android` should show nightmode `[x]`.

## Run 43 (2026-10-24)

Calls on SIM 2 (out/logs/run43-pixel): silent both ways on earpiece, speaker
and mic, as in runs 41 and 42 (SIM 1 calls worked in run 41).

Cause: the call ran on SIM 1's ADSP voice session. Samsung's audio HAL picks it
from the vendor key `g_call_sim_slot` (0x01 VSID_1, 0x02 VSID_2, 0x10 swap
during a call), and a restarted HAL starts on VSID_1. The call keeper sent
0x10 through the guest AudioFlinger and got `Result: Parcel(00000000)`, but the
HAL never logged `processSetVendorParameters: configured g_call_sim_slot`
(09:09:33; the same silent drop in run 41 at 04:17:46 and run 42 at 06:36:39
and 06:37:22). Pixel's libaudiohal@aidl passes unknown keys to
`IModule.setVendorParameters` only through an `IHalAdapterVendorExtension`.
With `ro.audio.ihaladaptervendorextension_enabled=false` (guest_props.sh, run
38, which the Pixel audioserver needs to start) it has none, and it drops the
key without a log line. One UI's and ColorOS's QTI audioservers load the
extension (`libaudiohalvendorextn.so`) in-process, which is why ColorOS's keys
arrived (run 34).

Fix (guest_start.sh call keeper):
- While the property is not true, the keeper sends the key straight to the
  shared HAL: `service call android.hardware.audio.core.IModule/default 34`,
  with the parcel the QTI extension builds (a `VendorParameter` whose ext is a
  `qti.audio.core.VString`; 136 bytes for one key, the layout ColorOS's
  audioserver sent in run 34). ColorOS keeps the AudioFlinger path.
  `ONEOS_GUEST_CALL_SIM_VIA=af|hal` forces the first path.
- Every send is checked against the HAL's own log: the last `configured
  g_call_sim_slot` line from the HAL's pid, before and after, looked at again
  1 s later before a send counts as lost (a late line must not move the keeper
  to a path that drops the key). The line also gives the HAL's VSID state
  afterwards (`HAL state I2`, `A2`, ...; `none` until the HAL logs one).
- Nothing is sent on a path that is not ready yet: the AudioFlinger path waits
  for the guest audioserver to register (before, an idle send on ColorOS could
  go out before that and be lost); the keeper tries again on its next turn.
- Path check as soon as the HAL is known, before any call: 0x01 (a restarted
  HAL is on VSID_1 anyway), or the last call's SIM. If it is not delivered,
  the keeper tries the other path once, and only with an idle 0x01/0x02. It
  never resends a 0x10, because a late first copy plus a second one would
  swap back.
- At start the keeper also logs where the HAL gets `VString`, whether the HAL
  library imports `AIBinder_getCallingUid`, and `bluetooth.sco.managed_by_audio`.
- Nothing persistent changes: the HAL's in-memory VSID, which One UI's
  audioserver sets again before every call, and the return restarts the HAL.

Run 43 had no in-call Bluetooth test: the only call (28 s) was
routed `call-handset` before any Bluetooth link existed, and the car kit never
connected (see Bluetooth, run 43). The Bluetooth media failure at 09:14:26
(`[bluetooth]` module, `openOutputStream` for bt-a2dp) is a separate issue.

Check in run 44: in call_audio.log, `g_call_sim_slot path hal first`, then
`g_call_sim_slot=0x01 via hal (path check, ...)` or `0x02 ...` with
`HAL got it` (for 0x02 also `HAL state I2`), before any call. For an outgoing
and an incoming call on SIM 2, `call on SIM slot 1: HAL A2` (or `I2`) and
audio both ways.
For a SIM 1 call after a SIM 2 call, a 0x10 and `HAL A1`. Also check the
speakerphone: One UI also sends `l_dual_speaker_amp_left_power_enable=true` at
call start, and Pixel never does.

If the `via hal` sends log `HAL NEVER got it` (on Pixel the AudioFlinger
path cannot help, so `on either path` may follow or not), the next steps, in
order:
- F1: if the `service call` Result is `00000000` and the HAL still logs no
  `configured` line, the HAL may check the caller uid (the keeper is root, an
  audioserver 1041; see the `AIBinder_getCallingUid` count). Retry the same
  call by hand as uid 1041 through the root manager's su, during the session
  and with no call running (0x01 is idle and harmless), before building
  anything: `su 1041 -c "service call android.hardware.audio.core.IModule/default
  34 i32 1 i32 1 i32 124 s16 g_call_sim_slot i32 1 i32 1 i32 72 s16
  qti.audio.core.VString i32 20 s16 0x01 i32 0"`, then look for the HAL's
  `configured g_call_sim_slot` line.
- F2 (not built): a small native helper in the guest that loads the QTI
  `libaudiohalvendorextn.so` and registers its `IHalAdapterVendorExtension`
  before the guest audioserver starts. The session would then keep One UI's
  `true`, and the guest audioserver would forward every vendor key itself.

## Google services

Pixel 17 has GmsCore only in `/system/product/apex/com.google.android.gmssystem.prodvic.apex`,
which the phone's apexd never activates ("Missing required system package:
com.google.android.gms"). make-overlays.sh stages that APEX's payload as
`gmssystem_payload.img` (EROFS, 155 MB, GmsCore 26.18.43 inside; deploy-phone.sh
pushes it like the other payloads). The image is not changed; for the session
guest_prepare.sh:

- loop-mounts the payload at the guest's `/apex/com.google.android.gmssystem`
  and its `@<version>` dirs (the guest no longer sees One UI's module there);
- binds a small read-only tmpfs package folder (`$STAGE/gmscore`, labelled
  `system_file`: the payload's `PrebuiltGmsCoreVic.apk` plus the image's own
  `app_chimera` and `m` Dynamite modules) over
  `/system/product/priv-app/PrebuiltGmsCore`, so GmsCore is a plain product
  priv-app as before Android 17 (the image's product XMLs already allowlist its
  privileged permissions and user types), and hides the payload's own
  `priv-app` so it is found once;
- writes `data/oneos_gms_present`. GSF, the Play Store and the setup/restore
  apps are the image's own folders.

Setup: with Google services presented nothing sets `device_provisioned` /
`user_setup_complete` or disables Pixel's setup wizards, so on a stage that was
never set up Pixel's setup wizard runs at first boot. Without an account, skip
sign-in, and skip screen lock, fingerprint and face (the gatekeeper guard
refuses a guest screen lock). When it finishes it sets both keys and turns
itself off; the stage keeps that and later sessions go straight home. A stage
the activator already marked set up (runs 41-42: keys forced, wizards
disabled) stays that way: the wizard needs a fresh stage. A session with
`ONEOS_GUEST_GMS=0` marks setup done as before.

Switches: `ONEOS_GUEST_GMS=1` (default; presents GmsCore when the payload is
staged) or `0`. Refused (switch preflight, or guest_prepare.sh) together with
`ONEOS_GUEST_HIDE_GMS=1`, when guards.txt lacks the gatekeeper, pdb, apexd and
appid15000 guards, and on a stage whose packages.list has app uids
10000-14999 (made before the app id guard: `deploy-phone.sh --fresh`).

Not covered yet: signing in (reviewed, not tried on a phone: see below);
Play's module updates (refused by the apexd guard); dexopt of GmsCore (artd
resolves paths in One UI's namespace, so it probably runs JIT-only). The
OneOS app (0.3.7) stages the payload with the rest of its `pixel-f8u` set and
never offers to hide Google services for this image.

### Signing in to Google (review, 2026-10-25)

What a Google account adds to a guest that already runs Google Play services,
and where each part lands. The Fold's stage (app 0.4.7) was checked read-only
first: guards.txt lists the gatekeeper, pdb, apexd, appid15000 and nousers
guards, packages.list has no app uid below 15000, and the stage holds no
Google account yet.

- **FRP.** Google Play services sets a factory-reset-protection secret
  (`setFactoryResetProtectionSecret`; run 43 already shows three calls
  without an account). The guest's PersistentDataBlockService writes its
  `frp_secret` files into the stage and the partition write is discarded
  (`guest_pdb_readonly.py`). One UI's partition holds the default secret, so
  the guest still boots with FRP deactivated ("FRP secret matched" with the
  default secret). The switch compares the partition's hash before and after
  every session (host_state.log: unchanged so far).
- **Screen lock.** Signing in sets no lock. Passkeys, Wallet and "verify it's
  you" prompts that want one fail (`setLockCredential` returns false, the
  gatekeeper guard): skip them.
- **Keystore.** Google Play services makes its keys under its own app id
  (15000 and up) in One UI's keystore2 database. One UI's apps are all below
  15000, so neither side can reach the other's keys. The guest's keys stay in
  One UI's database after the return, and deleting the stage does not remove
  them (`clearNamespace` is dropped): harmless, but they are not cleaned up.
- **Account storage.** `accounts_ce.db` is in the stage's
  `data/system_ce/0`, a plain stage folder rather than credential-encrypted
  storage, so root on One UI can read the account's tokens. Deleting the
  stage removes the account from the phone; remove the device in the Google
  account's device list too.
- **Find My Device** lists the guest as another device (Pixel 11 Fold). A
  remote erase reaches `wipeData` in the guest: the FRP wipe returns, the
  recovery command (BCB) cannot be written and the guest cannot reboot the
  phone, so One UI's data is not touched. The eSIM erase that comes with it
  is what the eSIM guard below is for. Turning Find My Device off in the
  guest is still the safer setting.
- **eSIM.** The guest's eSIM manager (EuiccGoogle) talks to the phone's eSIM
  chip directly. A guest factory reset with "Erase eSIMs", Erase downloaded
  SIMs, Erase SIM or a remote erase would delete One UI's eSIM profiles, and
  the test Fold's SIM 2 is an eSIM. guest_prepare.sh now hides the eSIM manager
  apps (`safety.esim_guard`: EuiccGoogle and EuiccSupportPixel-P23 here); the
  enabled eSIM keeps working, the guest just cannot change profiles.
  `ONEOS_GUEST_ESIM_MANAGER=1` keeps them (adb sessions only).
- **Play Store.** App updates install into the stage (`/data/app` is
  bridged). Google Play system updates (APEX trains) are refused by the apexd
  guard and Play will keep offering them.
- **RCS.** Google Messages in the guest takes RCS over for both numbers. Back
  in One UI its messaging app has to register again, and RCS messages sent in
  between can wait for the guest. Leave RCS chats off in the guest unless
  they are meant to live there.
- **Google's side.** A "new sign-in on a Pixel 11 Fold" security alert. Play
  Integrity's device check fails (unlocked bootloader, Samsung attestation),
  as it does on rooted One UI.

Verdict: safe to sign in with the current guards, if the guest gets no screen
lock and no factory reset. Until the eSIM guard is on the phone (the next
app build), also do not erase SIMs in the guest and turn Find My Device off
after signing in.

## Bluetooth (run 43)

Run 43 was the first session with One UI's pairings imported. A pair of
Bluetooth earbuds connected, showed as the output and played nothing, and calls
never reached them. The car kit never connected at all (no link to it in the whole session);
the test call happened before any Bluetooth link existed.

- One UI's LE keys are not in AOSP's layout. Each device's `LE_KEY_PID` (AOSP:
  16-byte IRK, address type 00 or 01, identity address) decoded to type 149, 181
  or 13 and a made-up identity address (the earbuds' `xx:xx` -> `yy:yy`). The Pixel
  stack used it anyway, in Java and in the native stack: A2DP's active device,
  HFP and even the earbuds' pairing record went to `yy:yy`. So no A2DP session
  started ("SetActivePeer: Error setting ..."; PAL `-19` on every write while
  audio was routed to "BT A2DP Out"), HFP never got its service-level
  connection ("CindResponse: Invalid index -1") and SCO was refused.
- The imported link key was rejected too: the earbuds' first connection dropped
  with `HCI_ERR_AUTH_FAILURE`, before any pairing in the guest. One UI may keep
  its keys in another form (not known yet).
- After that the earbuds asked to pair again, and the guest's stack accepted it
  by itself ("Auto-accept temporary pairing", no dialog). That gave the earbuds a
  new key for this phone: **the earbuds need pairing again in One UI after run
  43.**

Fix (guest_prepare.sh 5c2): the stage's `bt_config.conf` is now One UI's file
through a filter. If any device's `LE_KEY_PID` is not AOSP's layout with the
device's own address, every device loses its LE records (`LE_*`, `Le*`,
`AddrType`, `ServiceLe`, GATT, LE Audio, CSIP, hearing aid, VCP), LE-only
devices are dropped and dual-mode ones become BR/EDR (`DevType` 3 -> 1); the
BR/EDR link keys stay. An AOSP-layout file passes unchanged. If the filter
fails, or its output has no `[Adapter]`, the guest starts with no pairings
(never an unchecked copy, never run 43's stage file). One UI's file is only
read. `ONEOS_GUEST_BT_LE_SANITIZE=0` imports it unchanged;
`ONEOS_GUEST_BT_IMPORT=0` keeps the guest's own file, which goes through the
same filter (the stage's file from run 43 still holds One UI's bad LE data; a
file the Pixel stack wrote from its own pairings passes unchanged). The same
happens when One UI has no `bt_config.conf`. Since run 44 the import is off by
default, a link key check runs on every file, and `ONEOS_GUEST_BT_LE_SANITIZE=0`
only skips the LE part (see Run 44).

`$STAGE/diag_bt/` (pulled with the other `diag_*`): `shape_oneui.txt` and
`shape_guest_prev.txt` (the file the Pixel stack itself wrote last session)
list key names, value lengths, hex or not, the `DevType`, `AddrType`,
`LinkKeyType` and `*PairingAlgorithm` values and, for `LE_KEY_PID`, byte 16
and where the device's own address sits (`self_at`, `self_rev_at`; AOSP's
layout gives 17 and -). No key values; devices only by the last two bytes of
their address. `sanitize.txt` has the filter's summary, also in the takeover
log ("Guest Bluetooth pairings: ..."). Each diagnostics round
(`diag_20/40/90/final`) also has `bluetooth_manager.txt`, the guest's `dumpsys
bluetooth_manager` (active devices, bond states, identity addresses).

Rule: **never pair One UI's devices in the guest.** Both systems use the
phone's one Bluetooth address, so a new pairing replaces the device's key and
One UI's pairing with it stops working. Keep other paired devices (the car) off
or out of range until a run shows imported keys working.

Run 44 test:

1. In One UI, before switching: pair the earbuds again and play about 10 s on
   them (One UI's reference lines in all.log); switch the car kit off or keep
   it out of range for the whole session.
2. In the guest: take the earbuds out of the case. Don't pair; cancel any pairing
   dialog. If they connect: 30 s of media, then one SIM 2 call on the earbuds.
3. Pass: the earbuds' first connection (`xx:xx`) has no `HCI_ERR_AUTH_FAILURE`, "Bond
   loss" or "Auto-accept temporary pairing"; no "Unexpected identity address
   type"; `setActiveDeviceNative: xx:xx:xx:xx:xx:xx` (the earbuds) with no SetActivePeer
   error; no "has NO session" or "pal stream open failed"; HFP's
   ConnectionStateCallback reaches 3 with no "CindResponse: Invalid index".
4. After the return: the earbuds still play in One UI without pairing again.
5. If the first connection fails with `HCI_ERR_AUTH_FAILURE` again, imported
   link keys are unusable: make `ONEOS_GUEST_BT_IMPORT=0` the default, pair the
   earbuds again in One UI, and compare the two shape files. Try the car kit only
   after the earbuds pass.

Bluetooth lines in all.log:

```sh
grep -E 'HCI_ERR_AUTH_FAILURE|Bond loss|Auto-accept temporary|Unexpected (identity|pairing)|SetActivePeer|setActiveDeviceNative|CindResponse|ConnectionStateCallback|AG open failed|has NO session|startSession|bt_offload state|BT device .* not (connected|ready)|pal stream open failed' all.log
```

Not done: a smali patch of the Bluetooth APEX (the native pairing record had
the wrong address too, so a Java fix is not enough); A2DP offload off and a
full HCI snoop log (both props One UI probably defines too, so only through
guest_props.sh's override path; a snoop log holds One UI's link keys). Not
explained yet: "bt_offload state is disabled" (AHAL_Platform_QTI, 09:14:26),
and Settings not listing the connected earbuds as a media device (the imported
CSIP group is suspected; the filter removes it).

## Signal bars (run 43)

Both SIMs showed empty bars for the whole session, as ColorOS did in run 34.
Samsung's RIL accepted the guest's indication filter (127) and signal reporting
criteria and kept sending other network indications (network state, cell info,
PCC, LCE), but never currentSignalStrength. AOSP's SignalStrengthController asks
for the signal strength only at radio-on and, for opportunistic subscriptions
only, in getSignalStrength(). So the guest kept the all-invalid values read
right after RADIO_POWER on (09:07:37), level 0 on both SIMs. TelephonyRegistry
in diag_90 had level 0 while Phone 1's own cell info had LTE rsrp -99, level 2.
A GET_SIGNAL_STRENGTH does return real values (09:07:34, 09:07:35). The likely
gate is Samsung's screen state, which One UI sets with OEM_HOOK_RAW
(`1182000D...`) on every screen change; sending that would change the shared
modem's state, so it is not used.

The "!" on the bars was mostly not a badge. Pixel stacks both SIMs in one icon,
the primary as bars over the secondary as dots, and at level 0 that looks like a
row of "!". The real cutouts were SIM 1's "Emergency calls only" while the modem
answered REG_DENIED_EM after the RIL handover (09:07:40 to 09:08:50, REG_HOME
UMTS at 09:09:30), and every icon while setup ran with no default data
subscription. Both are radio and APN follow-ups, like SIM 2's
NO_SUITABLE_DATA_PROFILE.

Fix (run 44): AOSP's own TelephonyComponentFactory injection, not a patched
Google dex (telephony-common.jar is on the boot class path and in the boot
image). make-overlays.sh builds:
- `oneos-telephony.jar`: OneOSTelephonyComponentFactory makes the image's
  SignalStrengthController and starts OneOSSignalPoll on it, which sends the
  controller its own EVENT_POLL_SIGNAL_STRENGTH every 20 s while the screen and
  the radio are on (a read-only RIL query; the ColorOS helper made generic). An
  exception from the poll never reaches GsmCdmaPhone's constructor.
- `OneOSPhoneInjection.apk` (switcher/overlays/phone_injection): a static RRO
  for com.android.phone's `xml/telephony_injection` (empty in the image) that
  names the class and `/system_ext/framework/oneos-telephony.jar`.
- `oneos-telephony.sha256`: the telephony-common.jar and TeleService.apk it was
  checked against.

It builds only when the image has both files, is not ColorOS, has an empty
injection config, TeleService declares no overlayable resources, none of the
image's RROs for com.android.phone (9 here) overrides that config, and
`patches/aosp_signal_poll_check.py` finds every class, member and message
handler the jar relies on. guest_prepare.sh then checks the two hashes, puts the
jar in a read-only overlay layer on the guest's system_ext (the injection drops
a jar on a writable mount; the same tmpfs layer still carries the apex mount
point) and the RRO in the guest's `/oem/overlay`. `ONEOS_GUEST_SIGNAL_POLL=0`
leaves both out. The app's `pixel-f8u` set (0.3.7) carries these three
files.

Check in run 44: "Read-only overlay on .../system/system_ext" and "Signal poll:
TelephonyComponentFactory injection" in the takeover log, `OneOSPhoneInjection.apk`
in the "Bound guest /oem" line. In all.log: `TelephonyComponentFactory: validated
paths: /system_ext/framework/oneos-telephony.jar`, `Total components injected:
1` (the jar path passed; only the two `OneOSSignalPoll` lines show that the
class loaded), then `> SIGNAL_STRENGTH` for each SIM about every 20 s with the
screen on, no FATAL EXCEPTION in com.android.phone and no second "RIL Restart
for Phone Died". `validated paths: null` means the RRO was not applied; an
empty list means the jar was missing or on a writable mount;
"Injection jar is not protected , path: ..." means statvfs on it failed (no
jar, or SELinux kept the radio domain from the overlay mount); `failed:` or
`injection failed:` means the class did not load; "OneOSSignalPoll: stopped"
means the phone's controller was not the one the poll started on. diag_40 and
diag_90 have `overlays_phone.txt` (the RRO's state, the jar's label and the
guest's system_ext mounts, com.android.phone's pid, the injection lines) and
`signal_polls.txt` (every SIGNAL_STRENGTH request and answer still in the radio
log); `telephony_registry.txt` should then show mSignalStrength levels that
match mCellInfo.

## Run 44 (2026-10-24)

About 8 minutes on the Fold, on a stage that was already set up, started from
the app and ended with "Back to One UI" in the in-guest app (a reboot return).

Worked:
- SIM 2 calls both ways, through the call keeper's `hal` path. Before any call
  the path check sent `g_call_sim_slot=0x02 via hal` and logged `HAL got it;
  HAL state I2`; the HAL logged `configured g_call_sim_slot` and `updateSecVSID:
  mCurVSID to VSID_2`. One outgoing and one incoming call each went `INACTIVE ->
  ACTIVE vsid:VSID_2`, with audio both ways. No 0x10 swap was needed. Both
  calls ran on 3G (the guest has no IMS) and went back to LTE afterwards.
- Signal bars: the TelephonyComponentFactory injection loaded (`validated
  paths: /system_ext/framework/oneos-telephony.jar`, `Total components
  injected: 1`, both `OneOSSignalPoll` lines). There were 44 `SIGNAL_STRENGTH`
  polls, one per SIM every 20 s, all answered, and the registry's levels match
  the cell info.
- Mobile data and 5G NSA on SIM 2: the attach APN was One UI's, data
  validated, and `overrideNetwork=NR_NSA` showed except during the calls (on
  3G). One network-side drop lasted 2 s.
- Wi-Fi joined and validated. It dropped and reconnected twice on a weak
  5 GHz link (Android's normal linger while cellular is validated); nothing to fix.
- gvld: the guest vold registered as `gvld`, and One UI's vold kept `vold` and
  `IVold/default` (`vold_names.txt` was the same in all three diagnostics
  rounds). IncrementalService started.
- Also: the fold line, HW overlays (0 composer rejections), Google Play
  services, the in-guest OneOS app, and the return.

Failed, and the fixes:
- A2DP: every connect went to the offload path
  (`A2DP_HARDWARE_OFFLOAD_ENCODING_DATAPATH`). Samsung's QTI HAL logged
  `handleDeviceConnectionChangebt_offload state is disabled` (10 times), then
  PAL `BT device 8 not connected or not ready` on every write while A2DP was the
  route. Commit 5ba9ff7 sets
  `persist.bluetooth.a2dp_offload.disabled` and `leaudio_offload.disabled` to
  true for the session in non-ColorOS guests: memory only, One UI's values are
  recorded and restored. That moves the guest's stack to software encoding; it
  does not change the HAL's offload state.
  **Pending (static analysis of `libaudiocorehal.qti.so`, not seen on a phone
  yet).** The HAL's offload state is bit 21 of the number in the Samsung vendor
  parameter `l_a2dp_format`, which only One UI's framework sends; nothing in
  the Pixel stack does, and the guest audioserver (no vendor extension) would
  drop it anyway. The two persist props are only read where the audioserver
  asks whether offload can be reconfigured. The config file is chosen once per
  HAL process: One UI's `audio_module_config_primary.xml` only after One UI's
  audioserver has sent the vendor parameter `l_support_sec_audio_feature`,
  otherwise `audio_module_config_primary_sec_on_gsi.xml`, which is what the
  HAL restarted for the guest loads. Both files put the three BT A2DP ports on
  the primary module (One UI's without encodings, which counts as every format;
  the GSI one with `encodings="audio/mp4a.40 audio/x-sbc"`), so the guest
  audio policy attaches A2DP to primary with either file: `[default]
  setConnectedState` matched template port 24, the primary port, and each
  attempt to open the stream on the `bluetooth` module failed in
  `prepareToOpenStream`. With 5ba9ff7 alone the audio is expected to stay on
  the speaker. Fix (guest_start.sh, guest_props.sh): A2DP offload stays on as
  in One UI (the A2DP part of 5ba9ff7 is undone; LE Audio stays in software),
  and the session sends `l_a2dp_format=2097152` (bit 21) to IModule/default
  with the call keeper's parcel (sizes 124, 76, 24) when the guest audioserver
  starts and again after every HAL restart (log `/data/oneos_a2dp.log`, kept by
  the return). `l_support_sec_audio_feature` is never sent. Not proven yet:
  whether Samsung's Bluetooth controller accepts the Pixel stack's offload start.
- HFP: a call routed to the earbuds stayed silent. Telecom made the earbuds
  active and the HAL patched `[Telephony Rx -> BT SCO Headset]`, but the stack
  never left `BTA_AG_SCO_LISTEN_ST`. The guest audioserver only ever sent
  `BT_SCO=off`, and PAL logged `BT device 7 not connected or not ready`. Cause:
  the image's product build.prop sets `bluetooth.sco.managed_by_audio=true` and
  One UI does not define it, so guest_props.sh added it. With it, Pixel's
  Telecom, AudioService and Bluetooth stack leave opening SCO to the audio HAL,
  and Samsung's HAL never does that by itself. Fix (guest_props.sh `add`): for
  non-ColorOS guests the prop is left out, so it is undefined (false) as in One
  UI. AudioService then opens SCO through the stack and sends `BT_SCO=on`, which
  reaches the HAL as `setScoConfig` through the standard IBluetooth (no vendor
  extension needed). `ONEOS_GUEST_SCO_MANAGED=1` keeps it. The call keeper's
  start line now shows `bluetooth.sco.managed_by_audio=unset`.
  The image's other LE Audio offload props are left out the same way, under
  `ONEOS_GUEST_BT_OFFLOAD` (`=1` keeps them). One UI does not define them:
  - `ro.bluetooth.leaudio_offload.supported`: together with One UI's
    `leaudio_offload.disabled=false`, it put the Pixel stack's LE Audio codec on
    the DSP in run 44 (`codec_manager.cc ... configure_data_path for encode`,
    `LE_AUDIO_HARDWARE_OFFLOAD` capabilities read twice). That is the same HAL
    path that refused A2DP.
  - `persist.bluetooth.leaudio_sw_offload` and
    `persist.vendor.audio.leaudio_sw_offload`: they are for Pixel's own audio
    HAL. Nothing in the image's Bluetooth module, framework.jar, services.jar or
    audioserver libraries reads them, and neither does the QTI HAL library.
- Pairing import: off by default now (`ONEOS_GUEST_BT_IMPORT=1` turns it on).
  One UI stores link keys in a form that is not AOSP's: 64 hex characters (32
  bytes) for each BR/EDR device, and its LE keys are 64 hex too. The Pixel
  stack writes 32 hex (16 bytes). The imported keys only caused trouble:
  `HCI_ERR_AUTH_FAILURE`, `Bond loss detected ... KEY_MISSING`, the stack's
  autonomous re-pairing, and three pairing dialogs the owner accepted. Now any
  device whose `LinkKey` is not exactly 32 hex characters is dropped, from One
  UI's file and from the stage's own file. The stage's file still holds One
  UI's earlier imported records: run 43's file, saved by the guest's stack,
  kept one with its 64-hex key. The takeover log counts them ("N with a
  LinkKey not in AOSP form (32 hex) dropped"). Pairings the guest made itself
  are always 32 hex and stay as they are. One UI's file is only read; the
  switch refuses to start if the stage's Bluetooth folder or file is One UI's
  own (a hard link, for instance). **The earbuds now hold a key the guest
  made: pair them again in One UI.**
- Bluetooth process crash: one FATAL NPE in the guest's Bluetooth process
  (`CsipSetCoordinatorService.bondStateChanged`, `Map.forEach` on null). It
  came during the auto re-pair of an imported device whose CSIP and LE records
  the filter had removed; the process restarted 0.5 s later. No One UI record
  reaches the guest any more, so this path is gone.
- Diagnostics: the call keeper's per-call lines were in no capture. Both calls
  came after diag_90, and a reboot return writes no diag_final. Now
  return_to_oneui.sh first copies `call_audio.log` and `audio_keeper.log` from
  the stage into the session's log folder (`oneos_logs`, next to `boot.log`),
  before anything is stopped and on both return paths.
  Run 45 review, for the same reason (the earbuds connected minutes after
  diag_90): the return also saves the guest's Bluetooth and audio state before
  it stops anything, in `diag_return/` (`bluetooth_manager.txt` without
  base64-only lines, `dumpsys_media.audio_policy.txt`, `dumpsys_audio.txt`,
  `bt_props.txt`). It reads the guest's own dumpsys in its namespace, 8 s at
  most per dump, side by side. The A2DP sender checks each send in the HAL's
  log, as the call keeper does. `oneos_a2dp.log`, `audio_keeper.log` and
  `call_audio.log` grow across sessions, so each session now starts with a
  dated line in them. The switch clears `diag_20/40/90/final`, `diag_pages`
  and `diag_return`, so a file a round skips is not the last session's. The
  takeover log counts the guest's devices that One UI has paired too, and
  `diag_bt/shape_oneui.txt` is written with the import off as well.
- IMS / VoLTE: not supported in the guest (known), so calls fall back to 3G.

Not tested: SIM 1 calls, including a SIM 1 call after a SIM 2 call (the 0x10
swap and `HAL A1`); GPS (the HAL started, and GMS got 0 locations in 7.7 s of
tracking); NFC (the stack came up; no tag or HCE); SMS; whether both
loudspeakers play on speakerphone.

Thermal: the phone was warm at the switch and not charging. Skin temperature
reached 45.2 °C (SEVERE) about 20 s after the guest's system_server started,
and dropped back to MODERATE (41.9 °C) about 1.5 minutes later. One UI's last CPU cap stayed for the whole
session: both clusters at 2.112 GHz, about half their maximum. One UI's SIOP
set it just before One UI stopped, and nothing in the guest adjusts it. Android
17 turns window blur off at SEVERE, which is why blur was flat from 17:29:49 to
17:31:13; the blur setting was not the cause. Also adding load:
- the zygote runs `-Xforcejitzygote`, so the image's AOT boot image is never
  used;
- One UI's artd cannot dexopt guest apps;
- the guest's screen never times out.
These are follow-ups, not part of this change.

Check in run 45. Files: the switch's log is the stage's `takeover_app.log`.
The guest's start-up log is `data/takeover.log`, which pull-run-logs.sh
names `takeover_inner.log`. The keepers' logs are in the stage's `data/`, and
in `oneos_logs/` after the return. In each keeper log, only the lines after
the last `=== <date> session` line are run 45's.
- The new scripts ran: `takeover_inner.log` has `A2DP offload:
  l_a2dp_format=2097152 to the audio HAL, ... each send checked`. If that line
  is missing, the stage still has 0.4.1's scripts, and none of the fixes below
  applied.
- Props, in `takeover_app.log`: `guest_props: bluetooth.sco.managed_by_audio
  left out for the session`, `persist.bluetooth.leaudio_offload.disabled=false
  overridden to true`, and `left out for the session ...:
  ro.bluetooth.leaudio_offload.supported ...`. `persist.bluetooth.a2dp_offload`
  must not be named, because One UI's `false` stays.
  `diag_return/bt_props.txt` has the values at the end.
- Pairings, in `takeover_app.log`: `Guest Bluetooth pairings: the guest's own;
  ...`, then `... after the checks; N devices, M with a LinkKey not in AOSP form
  (32 hex) dropped ...`, then `K of the N devices paired in the guest
  (xx:xx:xx:xx:..:..): also paired in One UI`. If the earbuds are in that list
  and were paired again in One UI after run 44, expect a pairing request in
  the guest (see below).
- HFP, during a call on the earbuds:
  - `call_audio.log`: `bluetooth.sco.managed_by_audio=unset`.
  - all.log:
    - `DeviceHalAidl: [default] setParameters: parameters: "BT_SCO=on"`;
    - `AHAL_Bluetooth_QTI: setScoConfig: received ScoConfig{isEnabled:
      Boolean{value: true}`;
    - `bta_ag_sco_event: SCO_state_change: [BTA_AG_SCO_LISTEN_ST(0x01)]->[...OPENING...]`,
      then to `...OPEN...`;
    - no `PAL: StreamPCM: open: ... BT device 7 not connected or not ready`.
  - Probably no `startSession - SessionType=HFP_HARDWARE_OFFLOAD_DATAPATH` at
    the HFP connect. Run 44 had one at 17:32:16, because the stack left SCO to
    the HAL.
  - Failure looks like run 44: only `BT_SCO=off`, and the stack staying in
    `BTA_AG_SCO_LISTEN_ST`.
  - If SCO opens and the call is still silent, look at the SCO codec. Run 44
    matched the earbuds to the stack's `INTEROP_HFP_1_9_ALLOWLIST`, and One UI
    sets `bluetooth.hfp.swb.supported=true`, so a super-wideband codec is
    possible. Check the `bt_wbs`/`bt_swb` keys in the guest's `setParameters`
    lines and the `mode` in `setScoConfig`.
- A2DP:
  - `oneos_a2dp.log`: `l_a2dp_format=2097152 (sizes 124 76 24) to the audio HAL
    pid N: Result: Parcel(00000000 '....'); HAL: processSetVendorParameters:
    configured l_a2dp_format`. The `Parcel(00000000` part alone proves
    nothing. `HAL NEVER logged it` means the bit is not set. So does `not
    configured`.
  - all.log, at each connect:
    `BTAudioProviderStub: startSession - SessionType=A2DP_HARDWARE_OFFLOAD_ENCODING_DATAPATH`,
    then `AHAL_Platform_QTI: handleDeviceConnectionChangebt_offload state is
    enabled`.
  - Failure looks like run 44: `... is disabled`, then thousands of `PAL:
    StreamPCM: open: 224: BT device 8 not connected or not ready` and
    `pal_stream_open failed with status -19` while music plays.
  - Also look for `[default] setConnectedState` against `[bluetooth] ...` and
    for `Hal2AidlMapper: prepareToOpenStream ... Failed`, to see which module
    took the A2DP device.
- At the return, in `diag_return/`:
  - `bluetooth_manager.txt`: the bonded devices; `A2DP:` and `HFP:` with
    `Connected count` and `Active`; `Offload started handle` (not 0 while
    music plays); `SCO occupied`; the A2DP codec.
  - `dumpsys_media.audio_policy.txt`: the module and output that the BT
    A2DP device is attached to.
  - `dumpsys_audio.txt`: the communication device and SCO state.
- LE Audio: the earbuds should connect over A2DP and HFP, as in run 44.
  `LeAudioService` connection lines, or an LE Audio toggle that is on in the
  device's settings, mean this run tested neither of those two fixes.

The earbuds and the guest. The import is off, so the guest only has its own
pairings. The stage's file still has the earbuds from run 44, with a guest key
that passes the checks. A device keeps one key for the phone's one Bluetooth
address:
- If the earbuds were paired again in One UI after run 44, the guest's key is
  out of date. At the first connection in the guest you get
  `HCI_ERR_AUTH_FAILURE`, `Bond loss detected`, and a pairing request. Accept
  it, as in run 44, or for a cleaner start:
  1. In the guest, go to Settings > Connected devices, open the earbuds and
     tap Forget.
  2. Put the earbuds in pairing mode.
  3. Go to Settings > Connected devices > Pair new device and pair them.
- If One UI did not pair them again, they connect in the guest without a
  request.

Either way, after the session One UI's key is the stale one: pair the earbuds
again in One UI. In the device's settings in the guest, Phone calls and Media
audio must be on. Google Dialer has Nearby devices (granted by the UI
activator, `[UI Activator] dialer:` in `ui_activator.log`). To leave them out
of the session, keep the earbuds in the case and decline any pairing dialog.
Removing a device One UI also has paired from the stage's file is a separate
decision.

## Pixel 9 Pro XL image (0.4.22, untested)

The Pixel 11 images need SVE in every process (RefBase's constructor, the
loader), which the SM8750 and SM8650 phones lack. Google's Pixel 9 Pro XL
build (komodo, `CP3A.261005.005`, Android 17) has none in its system code:
llvm-objdump finds no SVE in libutils, libbinder, libhwui, libgui,
libandroid_runtime, init, surfaceflinger, servicemanager, app_process64 or
the boot image, and the loader's two `cntd` are in compiler-rt's SME state
routines behind the CPU feature bit. Built like the Pixel 11 Pro image
(`--type pixel --no-debloat`, then Pixel Camera, PixelCameraServices,
PixelDisplayService and grilservice removed); its set is `pixel9-sultra`.

Its `services.jar` needed three changes: the `guest_no_new_users.py` funnel
takes a trailing `String[]` (and a second in-process entry,
`createProfileForUserEvenWhenDisallowed`), `WebViewZygote.getProcess()`
returns `IZygoteProcess`, and `classes2.dex` went past 65536 method
references with the OneOS classes, which make-overlays.sh then moves to a dex
of their own. vold and service.incremental.so have the same code as the
Pixel 11 builds at other offsets (make-overlays.sh), and the crashrecovery
APEX the same `RescueParty.isDisabled()`.

### First session: Galaxy S25 Ultra (af6c2b17, 2026-10-27)

App 0.4.22, profile `s-ultra-8750`. It booted, went through Google's setup
wizard, and came back with Back to One UI after 9 min 50 s. The phone ran
very hot: thermal status SEVERE (3) 1 minute after boot, CRITICAL (4) from
6.5 minutes, skin 54.0 °C at most, AP 67 °C. It was charging the whole time,
and the battery still went from 92% to 88%. Both CPU clusters stayed at their
full clock (3.53 and 4.47 GHz) all session, because nothing caps the CPU in
the guest: One UI's thermal control (SSRM/SIOP) stops with One UI's
system_server, and it had set no cap before the switch.

The biggest load was one crash loop.
- Pixel's ConnectivityThermalPowerManager (persistent, system_ext priv-app)
  throttles the Pixel modem and Wi-Fi through GRIL. The first LIGHT status
  was at 09:22:36 (skin 40.7 °C). From then on, every throttling request it
  sent (`TelephonyManager.sendThermalMitigationRequest`) came back
  `IllegalArgumentException: modem does not support data throttling`, and
  the app crashed. That was 1394 crashes and restarts in 15 minutes, about
  95 a minute.
- Each restart is a zygote fork and an app start at full clock. Its broadcasts
  also add most of the 34,000 `Sending oneway calls to frozen process` lines.
- Since 0.4.23, guest_prepare.sh hides the app folder with a read-only tmpfs,
  as it does for PersistentBackgroundCameraServices.
- The modem is Samsung's and GRIL is not in the image, so the app can do
  nothing here anyway.

There was a second, smaller load. `installd.setAppQuota` is blocked in the
container, because quotas are set on One UI's /data. Even so,
StorageStatsService kept working out cache quotas after every Play Store
update and logged a stack trace for each app: 33,464 failures, mostly during
the updates at 09:29-09:32 and 09:36-09:37. Since 0.4.23 the UI activator sets
`enable_cache_quota_calculation=0` in the guest on every boot. With that
setting at 0, `StorageStatsService$H.handleMessage` returns before doing
anything.

The rest of the log is first-boot work: the Play Store updating apps
(Finsky, `notification_cancel_all` for com.android.vending), Android System
Intelligence, and Accessibility re-reading its shortcuts after each package
change. In 15 minutes the log captured 1.34 million lines.

Window blur was not the cause. The sampler shows `mBlurEnabled=true` for the
whole session; the GPU ran at 160 of 1200 MHz when diag_40 was taken; the
launcher's 90th-percentile GPU time was 6 ms. In Android 17 the switch is
**Settings > Accessibility > Color and motion > Reduce blur effects**
(`BlurSwitchPreference`, writing `disable_window_blurs`). Developer options
still lists "Allow window-level blurs" (key `enable_blurs_on_windows` in
development_settings.xml), but nothing in SettingsGoogle handles that key any
more, so switching it changes nothing. The UI activator sets
`disable_window_blurs=0` only once per stage, and BlurController still reads
that setting (guest_blur_no_thermal.py removes only the thermal check), so
"Reduce blur effects" keeps working across sessions.

Since 0.4.23 a heat cap runs during every session, on every guest
(oneos_switch.sh; owner: "cap only when hot").
- Every 10 s it reads the guest's SKIN temperature, the same way the sampler
  does.
- From 45 °C (Samsung's SEVERE) it caps each cpufreq policy's
  `scaling_max_freq` at 80% of `cpuinfo_max_freq`; from 47 °C at 65%; from
  50 °C at 50%. Each level ends once the skin is 2 °C below where that level
  began.
- The first reading under 45 °C also lifts a cap One UI left from before the
  switch (run 45 ran at half clock for that reason).
- Only the sysfs request is written, so the kernel's own thermal limits still
  apply. Each change is logged in `heat_cap.log`.
- At the return, the keeper and return_to_oneui.sh (`heat_cap.active`) put
  every policy back at full clock, and One UI's SSRM then sets its own caps.
- Advanced > Cool down when hot (on by default) turns it off: the launch
  writes `ONEOS_HEAT_CAP=0`, root's fifth `launch` word. Home's Switch dialog
  then says the phone can get very hot.

"Feels like 60 Hz" (testers): the panel was at 120 Hz the whole time, but
SurfaceFlinger rendered at 60 Hz for 47 s and at 120 Hz for 74 s by the 90 s
diag. guest_start.sh's backdoor pin (run 42, against the Fold's 1 Hz drops)
allowed a render range of [60, 120]. Inside that range, SurfaceFlinger's 250 ms
idle timer and content detection sent "normal" frame-rate-category content to
60 Hz: this display's categories are normal 60 and high 90. Since 0.4.23 the
floor is the active mode's vsync rate, at most 120. That gives [120, 120] on
the S25 Ultra and on the Fold's 240 Hz VRR panels, and it is never above what
a panel can show.

Pixel Camera (installed by the Play Store) stays on its icon: it crashes
without Pixel's camera HAL. Open Camera works. Weather took about 0.1 s to
start and loaded its data. The tester who saw most apps stuck on their icon
has no logs here yet.

Galaxy S25 (f7d5ec8c, profile `s-8750`, a stage already set up, 2 minutes,
ended with the volume keys):
- Every app the tester opened drew within 0.4 s: Photos, YouTube, Play Store,
  Settings, two Telegram clients, the guest's OneOS app. Open Camera took 8.3 s.
- Skin reached 43.4 °C at most; One UI's cap from before the switch (3.07 and
  3.51 GHz) stayed. ConnectivityThermalPowerManager started but did not crash
  in those 2 minutes.
- Render rate: 25 s at 60 Hz and 94 s at 120 Hz (fixed above).
- SIM 1 was in service. Bluetooth was off: it was switched off in that stage
  (`PersistentState=0`; the S25 Ultra's was 1 and came up).
- Samsung's composer logged "AI Scaler Config ... is not present" about 40
  times a second during the guest, and a few per minute under One UI. It is
  vendor log noise.

The camera, on both S25 phones: Samsung's cameraserver answers some
`ICameraService.getCameraCharacteristics` calls from the Android 17 framework
with a NullPointerException ("Failed to load metadata for CameraId-2"). The
Quick Settings flashlight tile does not initialise. One `ICameraServiceListener`
callback from the host arrives misparsed
(`BadParcelableException: Allocation of size 7209057`). The two sides'
interfaces differ, as installd's did (guest_installd_abi.py). Bridging
ICameraService is open; Open Camera works on the cameras it can read.

What differs (2026-10-27). One UI 9 on the Z Fold8 Ultra (CP2A.260605.016)
was read on the phone with the ART module's dexdump. It was compared with the
Pixel 9 Pro XL (CP3A.261005.005) and the Pixel 11 Fold (CD1A.261005.003.B1;
the Pixel 11 Pro has the same build) with `scripts/aidl-table.py`.
- `ICameraService`: Samsung adds `notifyDeviceStateChangeSync` at 23. The
  Pixels' `createDefaultRequest`, `isSessionConfigurationWithParametersSupported`,
  `getSessionCharacteristics` and `warmUp` (23-26) are 24-27 on Samsung, with
  the same signatures. Samsung's own methods are 28-38.
- `ICameraDeviceUser`: Samsung adds `setParameters(String)` at 13. Every Pixel
  method from `getInputSurface` (13) to `updateOutputConfigurations` (28) is one
  higher on Samsung, with the same signature. A Pixel camera session's
  `createDefaultRequest` (14) reaches Samsung's `getInputSurface`, and so on.
- `ICameraServiceListener`: Samsung's 9 is `onCameraDeviceStateChanged`. The
  Pixel 9 Pro XL's 9 is `onStatusChangedBatched` (the misparse above). The
  Pixel 11 Fold has no 9, so it ignores the call.
- `CameraCompatibilityInfo` (no size header): the Pixel 9 Pro XL writes a sixth
  field, `mShouldOverrideLensFacingFrontToBack`. Samsung reads it as the next
  parcelable's null marker, and gets a null `AttributionSourceState` in
  `getCameraInfo`, `connect`, `connectDevice`, `getCameraCharacteristics` and
  `getSessionCharacteristics` (the NullPointerException). The Pixel 11 Fold
  writes Samsung's five.
- `ICameraDeviceCallbacks`, the offline and injection interfaces, and the other
  parcels (CaptureRequest, OutputConfiguration, SessionConfiguration,
  CaptureResultExtras, CameraStatus, AttributionSourceState) are the same. The
  only differences are exception helpers the compiler outlines.
So the Pixel 11 images need the two renumberings. The Pixel 9 Pro XL also
needs the listener's 9 ignored and Samsung's five-field
`CameraCompatibilityInfo`. Only the Java side has been compared: NDK camera and
camera API1 clients go through the guest's native libraries, which were not
looked at.

The fix (0.4.24, untested on a phone): `switcher/patches/pixel_camera_abi.py`,
table-driven like the installd bridge. The host table is
`switcher/patches/host_camera.txt`, `scripts/aidl-table.py` on One UI 9's
`framework.jar` (the Z Fold8 Ultra's, CP2A.260605.016; the other One UI 9 phones
are expected to match, as installd's table did). For every interface in it the
guest's `Stub$Proxy` gets the host's code in the `const` that feeds
`IBinder.transact`, method by method, only with equal signatures; a guest-only
method on a service interface stops the build. For the interfaces the host
calls into the guest (`ICameraServiceListener`, `ICameraDeviceCallbacks`) a
guest `onTransact` case whose code is another method on the host is dropped
from the packed switch, so the call returns false instead of being misparsed.
`CameraCompatibilityInfo` stops writing and reading its sixth field. The result
is `framework_patched.jar` (`scripts/patch-framework-camera.sh`: the image's
jar with only the changed dex files replaced, as the other patched jars),
bound over the guest's `framework.jar` by `guest_prepare.sh` and pinned in
`guards.txt`; `make-overlays.sh` builds it for any image without
`oplus-services.jar`. A rebuild of the Pixel 11 sets needs their image or the
jar from a stage on the phone (`oneos.old-*/system.raw`, mounted read-only).

First run of the fix (S25 Ultra, Pixel 9 Pro XL, 0.4.24, bundle 6de3017c): the
jar was bound, the flashlight tile works and the listener callbacks parse (the
Java side is done); Open Camera in Camera2 mode works. In its default mode it
still fails: "Connect camera (legacy API)" answered `EX_NULL_POINTER` by
Samsung's camera service six times. That is the legacy camera API, marshalled
by the guest's own native client library, `/system/lib64/libcamera_client.so`
(`BpCameraService::connect`, with the native `CameraCompatibilityInfo`), which
the jar patch does not touch. The NDK camera2 path rides on the same library.

What is left, as a native overlay (`libcamera_client_patched.so`, bound and
pinned like `vold_patched`, per image build): the same two changes as the Java
side. In `BpCameraService` the four renumbered calls (createDefaultRequest,
isSessionConfigurationWithParametersSupported, getSessionCharacteristics,
warmUp) and in `BpCameraDeviceUser` the sixteen from getInputSurface to
updateOutputConfigurations pass their code to `IBinder::transact` as an
immediate; each becomes One UI's number from `host_camera.txt`. In the Pixel 9
Pro XL build the native `CameraCompatibilityInfo::writeToParcel` writes the
sixth field last; that write goes. `BnCameraServiceListener::onTransact` has
the same code-9 case as the Java listener (NDK clients only). Both libraries
(Pixel 11 build CD1A.261005.003.B1, Pixel 9 Pro XL CP3A.261005.005) are in the
images; the Pixel 11 one can be read from the Fold's old stage like the jar.
The "could not get camera service worker" lines in that bundle are One UI's
cameraserver restarting after the return, not part of the failure.
Until then: Camera2 apps work, legacy-API apps do not (Open Camera: Settings >
Camera API > Camera2).

The native overlay (unreleased, untested on a phone): `switcher/patches/pixel_camera_native.py`
reads the library's dynamic symbols and aarch64 encodings with no disassembler.
`BpCameraService` and `BpCameraDeviceUser` pass the code as `mov w1, #N` (the last
one in each method): the 9 Pro XL's build gets exactly the Java patcher's changes
(4 + 16 renumbered calls); `BnCameraServiceListener::onTransact`'s `cmp w1, #9;
b.ne` becomes `b` (code 9 ignored); `libcameracompatbilityinfo.so`'s sixth field
(`shouldOverrideLensFacingFrontToBack`, +0x1d) loses its last write and read call.
`scripts/patch-camera-native.sh` builds `libcamera_client_patched.so` and
`libcameracompatbilityinfo_patched.so`, `make-overlays.sh` runs it, `guest_prepare.sh`
binds and checks them (guards.txt). `pixel_camera_native.py --dump lib.so` prints a
library's Bp table.

ColorOS (X9U image, OP61A9L1) is not AOSP's numbering either: ICameraService
21-28 are Oplus's (`notifySmartWindowChange` 21, `notifyDisplayRotationChange` 22,
`notifyDeviceStateChange` 23, ...) and ICameraDeviceUser 13-28 are one lower than
One UI's, so the same renumbering applies; the two Oplus methods are void and go to
code 200 (One UI answers "unknown transaction"). Its native
CameraCompatibilityInfo already writes five fields, and its listener has no 9.
`make-overlays.sh` now builds the camera files for ColorOS images too. Not yet
done: the sets' file lists (`PackageSets.kt`, `SET_PIXEL`/`SET_COMMON`) and the
rebuilt sets, and the Pixel 11 libraries (their images are gone: pull
`/system/lib64/libcamera_client.so` and `libcameracompatbilityinfo.so` from the
Fold's old stage like the jar). Still to check on the phone: the legacy
`ICamera`/`ICameraClient` calls after connect (handwritten Bp classes in the same
library; compare `--dump` of One UI's own libcamera_client.so with the guest's).

Calls, Bluetooth and the speakers in the same session (nothing was paired and
no call was made):
- SIM 1 was in service on LTE with carrier aggregation, at 2-3 bars from
  the signal poll; the second slot was out of service.
- The call-audio keeper set `g_call_sim_slot=0x01` in the HAL at the start;
  there was no call.
- IMS is not there, as on the other phones, so calls go over 2G/3G.
- Bluetooth reached ON with A2DP offload. `l_a2dp_format` was sent to the HAL.
- LE Audio was off for the session (no `IBluetoothAudioProviderFactory/default`
  on SM8750), and SCO is opened by the guest's own stack.
- The only pairing attempt (09:25:56, failed) was the setup wizard's "copy
  from another phone" link, not earbuds.
- The speaker output is stereo and played 36 s of sound. The volume-curve
  error at 09:22:18 comes once, as audioserver starts and before AudioService
  sets the volumes.
- `PermissionController_patched.apk missing` is expected on Pixel sets: the
  patch is ColorOS's.

## Open (not seen on a phone yet)

- `/product/overlay/*__yogi__*` RROs carry the Pixel Fold's display config
  (cutout, corners, fold), the Pixel form of the camera-hole mismatch.
- The guest's brightness path on Samsung's panel (ColorOS needed
  samsung_backlight_curve.py in oplus-services).
- `guest_props.sh recover` puts back only the language and OPPO's
  `persist.oplus.*` after a hard reset: the other persist props a Pixel
  session saved (runs 38-43's returns deleted 22-28 added ones; which, the logs
  do not say, possibly Phenotype's `persist.device_config.*`) stay in One UI.
  The app's Restore says "restored the language only" for a Pixel stage (0.3.7);
  widening `guest_prop()` needs a Pixel session's persist diff from the phone.
- The app (0.3.7) offers the image on the Fold with its `pixel-f8u` set
  (app-android/README.md); no session has been started from the app yet.
