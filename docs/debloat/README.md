# OneOS Debloater: app lists per system

Research for the Debloater (handoff 2026-11-19). One TSV per family, columns `package, label, rating, reason, images, folder, notes`.
Every image was streamed from SourceForge, checked against `rawSha256` in Images.kt (rel-0518b), inventoried with debugfs + aapt2 (no mount), then deleted.

- 🟢 **Safe**: removing loses nothing the user needs (reason given per app).
- 🟡 **Caution**: the system works, a feature goes (named in the reason).
- 🔴 **Keep**: boot, setup, calls/SMS, data, keyboard, launcher, SystemUI, Settings, GMS or OneOS can break. Automatic rules from the handoff applied first (persistent, system/phone/bluetooth/nfc uid, IME/HOME/SETUP_WIZARD/DIALER/SMS, telephony/IMS, Google core and mainline, what OneOS relies on).
- Resource overlays (RROs) are counted apart: tiny, and hiding one only changes its target's config, so they are 🔴 unless their target is 🟢.
- Sizes are the app folder on the image (APK + its libs/oat). `notes` also lists OneOS script references, config XMLs naming the package, framework-res mentions, components (boot receivers, bound services) and per-image differences.
- Hiding is reversible (Restore all), and an app's data stays, so 🟢 includes standalone apps with a Play Store equivalent.

## Findings for the admin session (nothing changed)

- **Pixel 11 thermal manager not hidden.** guest_prepare.sh hides `system_ext/priv-app/ConnectivityThermalPowerManager` (crash loop on a Samsung modem). Pixel 11 Fold and Pixel 11 Pro ship it as `ConnectivityThermalPowerManagerNextgen`; only the Pixel 9 Pro XL matches.
- **HyperOS Lhasa Find Device not hidden.** The 0.5.31 wakelock fix hides `product/priv-app/MiuiFindDevice`; Lhasa ships `MIUIFindDeviceCN`.
- **GMS core is in no image except OxygenOS 16**; every other image has only the Play Store package and Google apps, OneOS provides Play services itself (guest_google.sh). GMS rows are still rated 🔴 wherever they appear.

## Not covered

- `/system/mystic/*.apk`: MysticGSI's auto-generated vendor resource overlays (framework-res, SystemUI, Settings, Wi-Fi, telephony RROs; 9–22 per image). Port plumbing, not apps: keep. Not listed per package.
- One UI `system/hidden/SmartTutor.apk` (Samsung remote support) and OriginOS `system/res/VCodeImpl.apk` (purpose not checked): found after those images were deleted, so not inventoried. Probably 🟢 and 🟡; confirm before shipping.
- The retired `coloros17-findx9u-in` image (handoff).
- Vendor partitions: not in the images (the phone's own).

## Status

- ColorOS 17: done
- HyperOS: done
- One UI 9.5: done
- OxygenOS 16: done
- OriginOS 7: done
- Pixel: done
- Nothing OS 5: done
- Infinity-X / LineageOS: done

## ColorOS 17  (`coloros.tsv`)

Images: `coloros17-findn6`, `coloros17-findx9u-in-1105`

| | 🟢 Safe | 🟡 Caution | 🔴 Keep |
|---|---|---|---|
| Apps | 72 | 141 | 157 |
| Overlays | 0 | 0 | 104 |

**Biggest wins:** the 🟢 apps take **3.2 GB** on the image (🟡 apps: 3.7 GB). Largest 🟢:

- Internet (`com.heytap.browser`), 299 MB
- Notes (`com.coloros.note`), 294 MB
- Maps (`com.google.android.apps.maps`), 163 MB
- Gmail (`com.google.android.gm`), 158 MB
- Photos (`com.google.android.apps.photos`), 153 MB
- Documents (`andes.oplus.documentsreader`), 139 MB
- YouTube (`com.google.android.youtube`), 128 MB
- App Market (`com.heytap.market`), 120 MB
- Home (`com.google.android.apps.chromecast.app`), 117 MB
- OSee (`com.coloros.ocrscanner`), 114 MB

**For the owner to decide:**

- **The Fluid Cloud set** (UMS `com.oplus.pantanal.ums`, Metis, AIUnit, Aod, Instant/Card, LockAssistant, FloatAssistant, OShare, SystemClone): all 🟡. MysticGSI's own ColorOS debloat removed exactly these on the old CN build, and that build had no Fluid Cloud (Dynamic Island); you then asked for no-debloat images. They should be offered as one "Fluid Cloud & smart cards" group, not one by one.
- **Apps made 🔴 only because they declare HOME/SETUP** (handoff rule): Lock Screen Magazine `com.heytap.pictorial` (also the lock-screen ad feed), Update highlights `com.oplus.upgradeguide`, Kids mode, Zen Space, and on the X9U IN a second keyboard, Yandex Keyboard. By function the first two and Yandex would be 🟢; your call whether the rule stays absolute.
- **System-uid apps hand-debloaters remove** but the rule keeps 🔴: System Messages `com.heytap.mcs` (OPPO push, including promos), Feedback `com.oplus.logkit`, Diagnostics `com.oplus.postmanservice`, Engineering mode. Not tested here, so they stay 🔴.
- **Judgement 🔴, not rule 🔴:** Phone Manager (has an InCallService, backs call blocking and permission pages), DeepThinker, the network plugins (`com.oplus.nas.*`, NetworkSense, NHS, NR mode, DRS), Blur, Screenshot, Multi-window UI. Worth a test before moving any of them down.
- **OneOS patches them, but they are optional:** Theme Store (patched brand check), OPPO Photos (Fold8 patch), AOD, Weather service, Shelf, Global Search: 🟡. Hiding one only skips our patch; the scripts check that the file exists first. Software update `com.oplus.ota` is 🟢: OneOS references it only to cut its network.
- **Telemetry kept 🟡:** DCS `com.oplus.statistics.rom`. Many OPPO apps report through it; it is not shown safe on this port.
- **Browsers:** OPPO Internet is 🟢 and Chrome 🟡; the app should stop the user from hiding both.
- **Per image:** only the X9U IN 1105 has Yandex Keyboard and OPPO Bubble (`com.oplus.ebadge`); only the Find N6 has AI Painter, Smart accessories, PayJoy and GlobalCollect. The retired `coloros17-findx9u-in` was not inventoried.


<details><summary>Every flagged row (auto 🔴 overriding the function, or 🟢/🟡 that OneOS scripts mention)</summary>

- `com.android.chrome` Chrome: 🟡 but OneOS references it (fold8_coloros.sh): Chrome: the default browser on GMS builds; WebView does not need it, but keep one browser
- `com.google.android.as` Android System Intelligence: 🟡 but OneOS references it (guest_soundtrigger_no_reboot.py): Android System Intelligence: Live Caption, smart text selection, Now Playing, app suggestions
- `com.oplus.aod` Always-On Display: 🟡 but OneOS references it (fold8_coloros.sh, guest_prepare.sh): Always-On Display: OneOS's AOD/panoramic-AOD work targets it (guest_prepare.sh, fold8_coloros.sh)
- `com.coloros.assistantscreen` Shelf: 🟡 but OneOS references it (guest_prepare.sh): Shelf (the launcher's left page with cards); OneOS reported its card provider restarting before 0.4.x seapp fix
- `com.nearme.instant.platform` InstantWeb Service Framework: 🟡 but OneOS references it (fold8_coloros.sh): Quick apps / instant cards (Fluid Cloud cards, Shelf cards); OneOS's Fold8 set replaces Instant
- `com.coloros.weather.service` Weather Services: 🟡 but OneOS references it (oplus_default_grants.py): Weather service: lock-screen/clock weather and widgets; OneOS grants it location (oplus_default_grants.py)
- `com.oppo.quicksearchbox` Global Search: 🟡 but OneOS references it (fold8_coloros.sh): Global Search (launcher swipe-down search)
- `com.oplus.themestore` Theme Store: 🟡 but OneOS references it (guest_prepare.sh): Theme Store: OneOS patches its brand check (KeKeThemeSpace_patched.apk); themes, icon packs and AOD styles go
- `com.coloros.sceneservice` Data-Driven Enhancement Service: 🟡 but OneOS references it (guest_prepare.sh): Scene service: context cards (travel, commute) for Shelf and lock screen
- `com.oplus.pantanal.ums` Smart Suggestion Service: 🟡 but OneOS references it (fold8_coloros.sh): Smart Suggestion Service (UMS): Fluid Cloud (Dynamic Island) and suggestion cards; OneOS's Fold8 set replaces it
- `com.oplus.ota` Software update: 🟢 but OneOS references it (oneos_switch.sh): Software update: ColorOS OTAs cannot install on a OneOS image, and OneOS already cuts its network (oneos_switch.sh)
- `ru.yandex.androidkeyboard` Yandex Keyboard: auto 🔴 by IME, but by function it would be 🟢: Yandex Keyboard: a second keyboard preloaded for Russia (Gboard stays)

</details>

## HyperOS  (`hyperos.tsv`)

Images: `hyperos-lhasa`, `hyperos-hongkong`

| | 🟢 Safe | 🟡 Caution | 🔴 Keep |
|---|---|---|---|
| Apps | 72 | 99 | 169 |
| Overlays | 0 | 0 | 114 |

**Biggest wins:** the 🟢 apps take **2.9 GB** on the image (🟡 apps: 1.9 GB). Largest 🟢:

- WPS for Pad (`cn.wps.moffice_hd`), 555 MB
- Gmail (`com.google.android.gm`), 225 MB
- Mi Browser (`com.mi.globalbrowser`), 209 MB
- Maps (`com.google.android.apps.maps`), 160 MB
- Photos (`com.google.android.apps.photos`), 153 MB
- YouTube (`com.google.android.youtube`), 124 MB
- Xiaomi Home (`com.xiaomi.smarthome`), 115 MB
- Meet (`com.google.android.apps.tachyon`), 109 MB
- Music (`com.miui.player`), 102 MB
- Notes (`com.miui.notes`), 82 MB

**For the owner to decide:**

- **Two different builds:** `hyperos-lhasa` (Xiaomi 18 Fold, China: Sogou/XiaoAi keyboards, UnionPay, Mi Pay, no Google apps) and `hyperos-hongkong` (HyperOS 4 Global: Google apps, Mi Browser, GetApps, MSA). The handoff's table left out `hyperos-hongkong`; it is in `Images.ALL`, so I included it. The `images` column shows which build has each app.
- **Finding, not a rating: the Find Device wakelock fix misses Lhasa.** guest_prepare.sh (0.5.31) hides `product/priv-app/MiuiFindDevice` because it held wakelocks for hours (A36, 11-20). Lhasa ships it as `MIUIFindDeviceCN` (same package `com.xiaomi.finddevice`), so on Lhasa it is **not** hidden. The global build's folder is hidden. For the admin session; I changed nothing.
- **Already hidden / managed by OneOS:** Find Device (global), Provision (when Google's wizard is there), and MiWallpaper (patched APK bound). Screen Recorder gets its signature permissions from OneOS, so it is 🔴 by the system-uid rule; by function it would be 🟡.
- **Biggest 🟢:** Mi Browser (208 MB), WPS, GetApps, Game Center, Mi Store/Community, Wallpaper Carousel (lock-screen ads), MSA/Analytics (ads and telemetry), Cleaner, and the standalone apps in `product/data-app`. About 2.9 GB in total.
- **🔴 only by rule:** IFAA and SOTER payment services (persistent), the Xiaomi Service Framework keeper, AOD and Voice Call Recorder (system uid), and the DT Ignite carrier installer `com.dti.aone` (declares HOME). By function they are 🟢 or 🟡.


<details><summary>Every flagged row (auto 🔴 overriding the function, or 🟢/🟡 that OneOS scripts mention)</summary>

- `org.ifaa.aidl.manager` IfaaService: auto 🔴 by persistent, but by function it would be 🟡: UnionPay / IFAA: secure payment and fingerprint payment in Chinese banking apps
- `com.tencent.soter.soterserver` SoterService: auto 🔴 by persistent, but by function it would be 🟡: Tencent SOTER: fingerprint payments in WeChat Pay
- `com.xiaomi.xmsfkeeper` Xiaomi Service Framework Keeper: auto 🔴 by persistent, but by function it would be 🟡: Xiaomi Service Framework: Mi push, account and Find Device plumbing for Xiaomi apps
- `com.miui.screenrecorder` Screen Recorder: auto 🔴 by android.uid.system, but by function it would be 🟡: Screen recorder; OneOS adds its signature permissions so it works (guest_prepare.sh)
- `com.miui.aod` Always-on display and Lock screen editor: auto 🔴 by android.uid.system, but by function it would be 🟡: Always-on display and lock-screen editor
- `com.mediatek.autodialer` Auto Dialer: auto 🔴 by android.uid.phone, but by function it would be 🟢: MediaTek engineering/test tool
- `com.miui.audiomonitor` Voice Call Recorder: auto 🔴 by android.uid.system, but by function it would be 🟡: Call recording
- `com.android.chrome` Chrome: 🟡 but OneOS references it (fold8_coloros.sh): Chrome: the default browser on GMS builds; WebView does not need it, but keep one browser
- `com.google.android.as` Android System Intelligence: 🟡 but OneOS references it (guest_soundtrigger_no_reboot.py): Android System Intelligence: Live Caption, smart text selection, Now Playing, app suggestions
- `com.dti.aone` Mobile Services Manager: auto 🔴 by HOME, but by function it would be 🟢: Mobile Services Manager (DT Ignite: carrier app installer during setup); declares HOME
- `com.qualcomm.qti.xrvd.service` XRVD: auto 🔴 by android.uid.system, but by function it would be 🟢: Qualcomm XR (AR/VR glasses) services

</details>

## One UI 9.5  (`oneui95.tsv`)

Images: `oneui95-s948b`

| | 🟢 Safe | 🟡 Caution | 🔴 Keep |
|---|---|---|---|
| Apps | 62 | 162 | 193 |
| Overlays | 0 | 0 | 61 |

**Biggest wins:** the 🟢 apps take **1.8 GB** on the image (🟡 apps: 3.8 GB). Largest 🟢:

- Gmail (`com.google.android.gm`), 230 MB
- YouTube (`com.google.android.youtube`), 177 MB
- Maps (`com.google.android.apps.maps`), 163 MB
- Meet (`com.google.android.apps.tachyon`), 140 MB
- OneDrive (`com.microsoft.skydrive`), 138 MB
- SamsungTTS MSA Arabic Voice 1 (`com.samsung.SMT.lang_ar_ae_m00`), 75 MB
- SamsungTTS US English Voice 1 (`com.samsung.SMT.lang_en_us_l03`), 75 MB
- Creative Studio (`com.samsung.android.app.sketchbook`), 70 MB
- Galaxy Store (`com.sec.android.app.samsungapps`), 59 MB
- Studio (`com.sec.android.app.vepreload`), 53 MB

**For the owner to decide:**

- **Already hidden by OneOS on One UI images** (handoff): KnoxGuard `com.samsung.android.kgclient`, Samsung Device Health Manager `com.sec.android.sdhms`, and Samsung Smart Suggestions `com.samsung.android.smartsuggestions` (341 MB). Listed 🔴 as OneOS-managed with an "ALREADY HIDDEN" note. Don't offer them as user ticks.
- **OneOS relies on:** Samsung IMS `com.sec.imsservice`, Samsung Camera, the Filter Provider (the camera stops without it), and the Samsung setup wizard. All 🔴.
- **Built-in wallpapers** `com.samsung.android.wallpaper.res` are 814 MB and 🟡: the largest single item, but the wallpaper picker loses its stock wallpapers.
- **Galaxy AI** (Samsung AI Core, AIOS kernel, Intelligence Service, Vision, Photo Remaster) is 🟡 as a group, about 0.5 GB. Photo Remaster runs as system, so it is 🔴 by rule.
- **🔴 only by the system-uid rule:** Bixby voice wake-up (100 MB), Sticker Center, Video call effects, the factory/test apps (FACM, DeviceKeystring, HwModuleTest, WlanTest, UwbTest, FactoryCamera…), Software update (`com.sec.android.soagent`, `com.wssyncmldm` FOTA) and Recommended apps (`com.samsung.android.app.omcagent`). Hand debloaters remove the FOTA, OMC and factory apps; your call.
- **Biggest 🟢:** Gmail, YouTube, Maps, Meet, OneDrive, 16 Samsung TTS voices (Google speech stays), Creative Studio, Studio, Galaxy Store. About 1.8 GB in total.
- **Setup:** Smart Switch, Studio and the Gallery widget hook into Samsung's setup wizard (a deferred step, not the wizard itself), so they keep their functional rating. Setup should just skip that step when the app is missing; not tested.


<details><summary>Every flagged row (auto 🔴 overriding the function, or 🟢/🟡 that OneOS scripts mention)</summary>

- `com.samsung.android.bixby.wakeup` \"Bixby\" voice wake-up: auto 🔴 by android.uid.system, but by function it would be 🟡: Bixby assistant, voice wake-up and interpreter
- `com.samsung.android.stickercenter` Sticker Center: auto 🔴 by android.uid.system, but by function it would be 🟢: Galaxy Avatar stub / sticker center
- `com.samsung.android.vtcamerasettings` Video effects: auto 🔴 by android.uid.system, but by function it would be 🟡: Video call effects
- `com.samsung.android.photoremasterservice` PhotoRemasterService: auto 🔴 by android.uid.system, but by function it would be 🟡: Galaxy AI (live translate, writing/photo assist, AI vision, photo remaster)
- `com.android.chrome` Chrome: 🟡 but OneOS references it (fold8_coloros.sh): Chrome: the default browser on GMS builds; WebView does not need it, but keep one browser
- `com.google.android.as` Android System Intelligence: 🟡 but OneOS references it (guest_soundtrigger_no_reboot.py): Android System Intelligence: Live Caption, smart text selection, Now Playing, app suggestions

</details>

## OxygenOS 16  (`oxygenos.tsv`)

Images: `oxygenos16-cph2745`

| | 🟢 Safe | 🟡 Caution | 🔴 Keep |
|---|---|---|---|
| Apps | 64 | 103 | 141 |
| Overlays | 1 | 0 | 94 |

**Biggest wins:** the 🟢 apps take **2.3 GB** on the image (🟡 apps: 2.4 GB). Largest 🟢:

- Maps (`com.google.android.apps.maps`), 158 MB
- Photos (`com.google.android.apps.photos`), 153 MB
- Gmail (`com.google.android.gm`), 153 MB
- Amazon Shopping (`com.amazon.mShop.android.shopping`), 151 MB
- iHeartRadio (`com.clearchannel.iheartradio.controller`), 134 MB
- Home (`com.google.android.apps.chromecast.app`), 117 MB
- YouTube (`com.google.android.youtube`), 112 MB
- Meet (`com.google.android.apps.tachyon`), 111 MB
- App Market (`com.heytap.market`), 108 MB
- My Account (`com.fidosolutions.myaccount`), 94 MB

**For the owner to decide:**

- **This image is already debloated.** UMS, Metis, AOD, Instant, LockAssistant, FloatAssistant, OShare, SystemClone and the OPPO camera are not in it: that is MysticGSI's ColorOS debloat list. AIUnit is still there. So there is no Fluid Cloud set to decide here, and the 🟢 total is smaller than ColorOS's.
- **Canadian carrier preloads** (Bell, Virgin, Rogers, Fido: MyBell, Crave, iHeartRadio, Citytv+, Sportsnet, Seekr and others) are in `my_product/apps_extension/*/SimSwitchFirstTime`. They are installed only when that carrier's SIM is seen, and all are 🟢.
- **NFC** `com.android.nfc` is 🔴 by rule. OneOS already hides it when the phone's vendor has no OPPO NFC HAL (otherwise it crash-loops).
- OxygenOS shares ColorOS's OPPO base, so the reasons for the `com.oplus.*`, `com.coloros.*` and `com.heytap.*` apps read "ColorOS". The same decisions apply: Lock Screen Magazine, Update highlights, System Messages (`com.heytap.mcs`), Phone Manager, DeepThinker, the network plugins, and DCS telemetry.


<details><summary>Every flagged row (auto 🔴 overriding the function, or 🟢/🟡 that OneOS scripts mention)</summary>

- `com.android.chrome` Chrome: 🟡 but OneOS references it (fold8_coloros.sh): Chrome: the default browser on GMS builds; WebView does not need it, but keep one browser
- `com.google.android.as` Android System Intelligence: 🟡 but OneOS references it (guest_soundtrigger_no_reboot.py): Android System Intelligence: Live Caption, smart text selection, Now Playing, app suggestions
- `com.coloros.assistantscreen` Shelf: 🟡 but OneOS references it (guest_prepare.sh): Shelf (the launcher's left page with cards); OneOS reported its card provider restarting before 0.4.x seapp fix
- `com.coloros.weather.service` Weather Services: 🟡 but OneOS references it (oplus_default_grants.py): Weather service: lock-screen/clock weather and widgets; OneOS grants it location (oplus_default_grants.py)
- `com.oplus.themestore` Theme Store: 🟡 but OneOS references it (guest_prepare.sh): Theme Store (themes, icon packs, AOD styles); OneOS's brand-check patch is for the ColorOS images
- `com.coloros.sceneservice` Data-Driven Enhancement Service: 🟡 but OneOS references it (guest_prepare.sh): Scene service: context cards (travel, commute) for Shelf and lock screen
- `com.oplus.ota` Software update: 🟢 but OneOS references it (oneos_switch.sh): Software update: ColorOS OTAs cannot install on a OneOS image, and OneOS already cuts its network (oneos_switch.sh)

</details>

## OriginOS 7  (`originos.tsv`)

Images: `originos7-pd2609ma`

| | 🟢 Safe | 🟡 Caution | 🔴 Keep |
|---|---|---|---|
| Apps | 53 | 131 | 145 |
| Overlays | 0 | 0 | 15 |

**Biggest wins:** the 🟢 apps take **2.3 GB** on the image (🟡 apps: 4.4 GB). Largest 🟢:

- Browser (`com.vivo.browser`), 350 MB
- vivo Docs (`com.vivo.smartoffice`), 245 MB
- vivo Health (`com.vivo.health`), 236 MB
- Quick App Frame Service (`com.vivo.hybrid`), 205 MB
- Music (`com.android.bbkmusic`), 136 MB
- Origin Notes (`com.android.notes`), 121 MB
- vivo Photography (`com.vivo.symmetry`), 107 MB
- Game Center (`com.vivo.game`), 104 MB
- vivo.com (`com.vivo.space`), 98 MB
- V-Appstore (`com.bbk.appstore`), 92 MB

**For the owner to decide:**

- **This is a China build** (PD2609MA): Baidu IME, Jovi/BlueLM AI and Chinese payment services are in it. It has no Google apps besides the Play Store package.
- **About 25 vivo apps are 🔴 only because they run as system or are persistent.** By function they would be 🟢 or 🟡: User Experience Improvement Program and log collection (`com.bbk.iqoo.logsystem`, `com.android.bbklog`, FuelSummary: telemetry), demo videos, Mobile KTV, AfterSale service, Easy Touch, Super screenshot, AOD (`com.vivo.nightpearl`), Ultra game mode, voice wake-up, AI Adviser. They are listed under "Every flagged row". Your call whether the system-uid rule stays absolute for vivo.
- **Already hidden by OneOS:** MediaTek telephony and IMS (MtkTelephonyAssist, MtkCapCtrl, DataChannelService, AtciService, ImsService), Vivo3rdAlgoService, vdfs, and vivo's setup wizard once setup is done.
- **vivo Camera** (539 MB) is 🟡, not 🔴. OneOS doesn't patch the app itself, only framework camera lookups (vivo_guards.py). Hiding it removes the camera unless the session binds Samsung Camera.
- **Launchers that declare HOME** stay 🔴: Desktop-mode launcher, Privacy launcher, VTrust Guard, Super Battery Saver. EasyShare declares an SMS role and Scan (Jovi Vision) declares an IME, so both are 🔴 by rule.


<details><summary>Every flagged row (auto 🔴 overriding the function, or 🟢/🟡 that OneOS scripts mention)</summary>

- `com.vivo.accessibilityenhance` Accessibility Enhance: auto 🔴 by android.uid.system, but by function it would be 🟡: Accessibility
- `com.vivo.audiofx` Audio effect: auto 🔴 by android.uid.system, but by function it would be 🟡: Audio effects / 4D haptics (system uid)
- `com.android.BBKCrontab` Task timer: auto 🔴 by android.uid.system, but by function it would be 🟡: Task timer (scheduled power on/off)
- `com.android.bbklog` Log Collection: auto 🔴 by android.uid.system, but by function it would be 🟢: User experience program / log collection (telemetry)
- `com.vivo.doubleinstance` App clone: auto 🔴 by android.uid.system, but by function it would be 🟡: App clone / privacy system / password safe
- `com.bbk.facewake` Smart Screen On: auto 🔴 by android.uid.system, but by function it would be 🟡: Smart motion, quick action key, smart screen-on
- `com.vivo.floatingball` Easy Touch: auto 🔴 by android.uid.system, but by function it would be 🟡: Multi-window, mini screen, Easy Touch, drag & go
- `com.vivo.fuelsummary` FuelSummary: auto 🔴 by android.uid.system, but by function it would be 🟢: User experience program / log collection (telemetry)
- `com.vivo.gamecube` Ultra Game Mode: auto 🔴 by android.uid.system, but by function it would be 🟡: Ultra game mode and game services
- `com.vivo.hover` Voice isolation floating button: auto 🔴 by android.uid.system, but by function it would be 🟡: Accessibility
- `com.bbk.iqoo.logsystem` User Experience Improvement Program: auto 🔴 by persistent, but by function it would be 🟢: User experience program / log collection (telemetry)
- `com.vivo.minscreen` Mini screen: auto 🔴 by android.uid.system, but by function it would be 🟡: Multi-window, mini screen, Easy Touch, drag & go
- `com.vivo.nightpearl` Always On Display: auto 🔴 by android.uid.system, but by function it would be 🟡: Always On Display
- `com.vivo.smartshot` Super screenshot: auto 🔴 by android.uid.system, but by function it would be 🟡: Super screenshot (scrolling and long screenshots)
- `com.vivo.assistant` AI Adviser: auto 🔴 by persistent, android.uid.system, but by function it would be 🟡: Jovi / BlueLM AI features (assistant, AI memory, AI notes, call assistant, voice wake-up)
- `com.vivo.ai.gptagent` 智能体服务: auto 🔴 by android.uid.system, but by function it would be 🟡: Jovi / BlueLM AI features (assistant, AI memory, AI notes, call assistant, voice wake-up)
- `com.vivo.smartmultiwindow` Multitasking: auto 🔴 by android.uid.system, but by function it would be 🟡: Multi-window, mini screen, Easy Touch, drag & go
- `com.vivo.voicerecognition` Sound recognition: auto 🔴 by android.uid.system, but by function it would be 🟡: Jovi / BlueLM AI features (assistant, AI memory, AI notes, call assistant, voice wake-up)
- `com.vivo.voicewakeup` Voice wakeup: auto 🔴 by android.uid.system, but by function it would be 🟡: Jovi / BlueLM AI features (assistant, AI memory, AI notes, call assistant, voice wake-up)
- `com.vos.as.vit` AfterSale Service: auto 🔴 by android.uid.system, but by function it would be 🟢: Factory/engineering test tool
- `com.vivo.vibrator4d` vibrator4d: auto 🔴 by android.uid.system, but by function it would be 🟡: Audio effects / 4D haptics (system uid)
- `com.vivo.demovideo` 演示视频: auto 🔴 by android.uid.system, but by function it would be 🟢: Tips, feedback, survey and demo videos
- `com.vivo.pushservice` Push Engine: auto 🔴 by persistent, but by function it would be 🟡: vivo push engine: notifications for vivo apps
- `com.vivo.car.networking` Jovi InCar: auto 🔴 by android.uid.system, but by function it would be 🟡: Jovi InCar (car mode)
- `com.vivo.vivokaraoke` Mobile KTV: auto 🔴 by android.uid.system, but by function it would be 🟢: Mobile KTV (karaoke monitoring)
- `com.mobile.cos.iroaming` iRoamingService: auto 🔴 by android.uid.system, but by function it would be 🟡: iRoaming service (roaming data packages)
- `com.vivo.connbase` Multi-Device Connectivity: auto 🔴 by persistent, android.uid.system, but by function it would be 🟡: Multi-device connectivity, vivoShare, screen mirroring, office kit
- `com.vivo.healthservice` Health Service: auto 🔴 by android.uid.system, but by function it would be 🟡: Health service (step counting for widgets and Health)
- `com.mediatek.location.lppe.main` LPPe Service: auto 🔴 by android.uid.system, but by function it would be 🟢: Factory/engineering test tool

</details>

## Pixel  (`pixel.tsv`)

Images: `pixel11fold-yogi`, `pixel11pro-kodiak`, `pixel9proxl-komodo`

| | 🟢 Safe | 🟡 Caution | 🔴 Keep |
|---|---|---|---|
| Apps | 35 | 98 | 119 |
| Overlays | 4 | 0 | 530 |

**Biggest wins:** the 🟢 apps take **1.4 GB** on the image (🟡 apps: 955 MB). Largest 🟢:

- Gmail (`com.google.android.gm`), 180 MB
- Photos (`com.google.android.apps.photos`), 180 MB
- YouTube (`com.google.android.youtube`), 155 MB
- Maps (`com.google.android.apps.maps`), 114 MB
- Recorder (`com.google.android.apps.recorder`), 89 MB
- YouTube Music (`com.google.android.apps.youtube.music`), 88 MB
- Drive (`com.google.android.apps.docs`), 83 MB
- Meet (`com.google.android.apps.tachyon`), 73 MB
- Pixel troubleshooting (`com.google.android.apps.pixel.support`), 67 MB
- Google Fi (`com.google.android.apps.tycho`), 48 MB

**For the owner to decide:**

- **Finding, not a rating: OneOS's thermal-manager hide misses Pixel 11.** guest_prepare.sh hides `system_ext/priv-app/ConnectivityThermalPowerManager`: Pixel modem throttling that crash-loops on a Samsung modem (1394 crashes in 15 min, S25U session af6c2b17). That matches only the Pixel 9 Pro XL. Pixel 11 Fold and Pixel 11 Pro ship it as `ConnectivityThermalPowerManagerNextgen` (same package `com.google.android.connectivitythermalpowermanager`), so on those two it is **not** hidden today. This is for the admin session; I changed nothing.
- **Pixel's telephony stack is 🔴**: ImsStack, QNS, Iwlan, carrier settings/setup, modem services, satellite. It is Google's modem stack running against a Samsung modem, so some of it may be idle, but it carries Wi-Fi calling, IMS and carrier config, so it stays 🔴 until tested.
- **Few 🟢 by design.** Pixel ships mostly Google apps, and most of those are 🟡 because they are system features (Now Playing, Pixel Screenshots, live wallpapers, Pixel Stand, theme packs). The 🟢 are Play apps (YouTube, Maps, Photos, Gmail, Drive, Fi, Weather, Calculator), My Pixel tips, troubleshooting/diagnostics, and retail demo.
- **Verizon services** (`com.verizon.*`, `com.vzw.apnlib`) are 🟡 rather than 🟢: they matter only with a Verizon SIM.
- **Hidden by OneOS already:** PersistentBackgroundCameraServices (all three), ConnectivityThermalPowerManager (Pixel 9 Pro XL only, see above), and the eSIM managers EuiccGoogle and EuiccSupportPixel.


<details><summary>Every flagged row (auto 🔴 overriding the function, or 🟢/🟡 that OneOS scripts mention)</summary>

- `com.android.chrome` APK Stub: 🟡 but OneOS references it (fold8_coloros.sh): Chrome: the default browser on GMS builds; WebView does not need it, but keep one browser
- `com.google.android.apps.cbrsnetworkmonitor` : auto 🔴 by persistent, but by function it would be 🟡: CBRS network monitor / satellite gateway (US carrier features)
- `com.google.android.as` Android System Intelligence: 🟡 but OneOS references it (guest_soundtrigger_no_reboot.py): Android System Intelligence: Live Caption, smart text selection, Now Playing, app suggestions
- `com.google.android.repairmode` Repair Mode: auto 🔴 by android.uid.system, but by function it would be 🟡: Repair mode (system uid)
- `com.google.android.settings.future.biometrics.faceenroll` Face Enroll: auto 🔴 by android.uid.system, but by function it would be 🟡: Face unlock enrollment

</details>

## Nothing OS 5  (`nothingos.tsv`)

Images: `nothingos5-metroid`, `nothingos5-asteroids`

| | 🟢 Safe | 🟡 Caution | 🔴 Keep |
|---|---|---|---|
| Apps | 24 | 67 | 98 |
| Overlays | 6 | 0 | 108 |

**Biggest wins:** the 🟢 apps take **359 MB** on the image (🟡 apps: 1.4 GB). Largest 🟢:

- Tips & feedback (`com.nothing.userguide`), 107 MB
- Calendar (`com.google.android.calendar`), 54 MB
- Contacts (`com.google.android.contacts`), 40 MB
- Google Play Games (`com.google.android.play.games`), 34 MB
- Files by Google (`com.google.android.apps.nbu.files`), 27 MB
- Glyph (`com.nothing.glyph`), 23 MB
- FT Terminal Test (`com.focaltech.ft_terminal_test`), 14 MB
- Glyph Toys (`com.nothinglondon.toys`), 12 MB
- Glyph Progress (`com.nothing.glyphnotification`), 11 MB
- Weather (`com.nothing.weather`), 11 MB

**For the owner to decide:**

- **Glyph apps are 🟢.** They drive Nothing's LED back panel, which no Galaxy host has. Nothing X (351 MB, Nothing earbuds) and Essential Space/Recorder are 🟡.
- **🔴 only by rule:** Essential Recorder, the Generative Ringtone Engine (OneOS binds a patched APK for haptics), Game dashboard, the factory/diagnostics apps (`com.tools.cit`, Nothing Diagnostics), aptX services, and Rakuten's setup installer (declares HOME). By function they are 🟢 or 🟡.
- **Nothing Camera** is 🔴 (OneOS-managed). OneOS hides it itself whenever Samsung Camera or Aperture is the camera.
- **Per image:** the A-series build (asteroids) and Metroid differ only in Magic 8 Ball, Leveller, Glyph Toys, AICore, Goodix fingerprint settings and FactoryTest. Japan's FeliCa (Osaifu-Keitai) apps are in the image and 🟡.
- **Smallest win of all families** (about 0.35 GB of 🟢): Nothing OS ships close to stock.


<details><summary>Every flagged row (auto 🔴 overriding the function, or 🟢/🟡 that OneOS scripts mention)</summary>

- `com.android.chrome` Chrome: 🟡 but OneOS references it (fold8_coloros.sh): Chrome: the default browser on GMS builds; WebView does not need it, but keep one browser
- `com.nothing.ntessentialrecorder` Essential Recorder: auto 🔴 by android.uid.system, but by function it would be 🟡: Essential Space / Essential Recorder (Essential key features; OneOS maps the key: oneos_essential_key)
- `com.nothing.ntessentialspace` Essential Space: 🟡 but OneOS references it (oneos_switch.sh): Essential Space / Essential Recorder (Essential key features; OneOS maps the key: oneos_essential_key)
- `com.nothing.generateringtoneservice` Generative Ringtone Engine: auto 🔴 by android.uid.system, but by function it would be 🟡: Generative ringtone engine; OneOS binds a patched APK for haptics (NothingGenerateRingtoneService_patched.apk)
- `com.aura.oobe.rakuten` Mobile Services: auto 🔴 by HOME, but by function it would be 🟢: Rakuten (Japan carrier) app installer during setup; declares HOME
- `com.google.android.as` Android System Intelligence: 🟡 but OneOS references it (guest_soundtrigger_no_reboot.py): Android System Intelligence: Live Caption, smart text selection, Now Playing, app suggestions
- `com.tools.cit` FactoryTest: auto 🔴 by android.uid.system, but by function it would be 🟢: Factory test / diagnostics tool
- `com.nothing.ntgamedashboard` NtGameDashboard: auto 🔴 by android.uid.system, but by function it would be 🟡: Game dashboard
- `com.nothing.ntfactorytest` Nothing Diagnostics: auto 🔴 by android.uid.system, but by function it would be 🟢: Factory test / diagnostics tool
- `com.nothing.gallery` Nothing Gallery: 🟡 but OneOS references it (oneos_switch.sh): Nothing Gallery (the camera's photo viewer)
- `com.qualcomm.qtil.aptxals` als: auto 🔴 by persistent, but by function it would be 🟡: aptX Bluetooth audio codec services
- `com.qualcomm.qtil.aptxui` aptxui: auto 🔴 by persistent, but by function it would be 🟡: aptX Bluetooth audio codec services
- `com.qualcomm.qti.xrvd.service` XRVD: auto 🔴 by android.uid.system, but by function it would be 🟢: Qualcomm XR (AR/VR glasses) services

</details>

## Infinity-X / LineageOS  (`infinityx-lineage.tsv`)

Images: `infinityx41-findx9u`, `lineage24-infiniti`

| | 🟢 Safe | 🟡 Caution | 🔴 Keep |
|---|---|---|---|
| Apps | 24 | 81 | 122 |
| Overlays | 4 | 0 | 246 |

**Biggest wins:** the 🟢 apps take **328 MB** on the image (🟡 apps: 1.7 GB). Largest 🟢:

- Photos (`com.google.android.apps.photos`), 180 MB
- IR Remote (`com.oplus.consumerIRApp`), 35 MB
- Contacts (`com.google.android.contacts`), 32 MB
- Updater (`com.infinity.updater`), 12 MB
- Battery Stats Viewer (`com.android.frameworks.core.batterystatsviewer`), 12 MB
- Music (`org.lineageos.twelve`), 8 MB
- Calendar (`org.lineageos.etar`), 7 MB
- DeviceDiagnostics (`com.android.devicediagnostics`), 6 MB
- System updates (`org.lineageos.updater`), 6 MB
- Calculator (`com.google.android.calculator`), 5 MB

**For the owner to decide:**

- **Two very different images**, rated in one list because the handoff groups them. Infinity-X 4.1 (Find X9 Ultra base) has Google apps, OPPO pieces (OplusCamera, Plus Key, OplusDoze) and Infinity-X extras. LineageOS 24 (OnePlus 15) is plain, with no Google apps: 24 packages are only in Lineage, 103 only in Infinity-X (see the `images` column).
- **Camera:** on Infinity-X, OneOS hides OplusCamera and Aperture becomes the camera, so Aperture is 🔴 and OplusCamera is 🔴 (OneOS-managed).
- **Infinity-X extras that run as system/persistent** (Freeform, Sidebar, QuickLook, GameSpace, Quick Tap, App locker, Sandbox, Theme store, Plus Key) are 🔴 by rule. Some of them would be 🟡 by function.
- **Small win:** about 0.33 GB 🟢 (Lineage's standalone apps, updaters, ViPER4Android, Play apps on Infinity-X). These ROMs are already lean.


<details><summary>Every flagged row (auto 🔴 overriding the function, or 🟢/🟡 that OneOS scripts mention)</summary>

- `com.android.chrome` APK Stub: 🟡 but OneOS references it (fold8_coloros.sh): Chrome: the default browser on GMS builds; WebView does not need it, but keep one browser
- `com.google.android.as` Android System Intelligence: 🟡 but OneOS references it (guest_soundtrigger_no_reboot.py): Android System Intelligence: Live Caption, smart text selection, Now Playing, app suggestions
- `com.oplus.pantanal.ums` Smart Suggestion Service: 🟡 but OneOS references it (fold8_coloros.sh): Smart Suggestion Service (UMS): Fluid Cloud (Dynamic Island) and suggestion cards; OneOS's Fold8 set replaces it
- `com.infinity.updater` Updater: 🟢 but OneOS references it (oneos_switch.sh): OTA updater: ROM OTAs cannot install on a OneOS image

</details>

