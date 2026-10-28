<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="images/banner-dark-2x.png">
    <source media="(prefers-color-scheme: light)" srcset="images/banner-light-2x.png">
    <img src="images/banner-light-2x.png" width="100%" alt="OneOS: another Android, next to One UI. Nothing flashed. Switch from an app, come back the same way. A One UI phone and a OneOS foldable, with arrows going both ways.">
  </picture>
</p>

<p align="center">
  <img alt="Status: experimental" src="https://img.shields.io/badge/status-experimental-5B3FCB?style=flat-square&labelColor=2B3445">
  <img alt="Android 17" src="https://img.shields.io/badge/Android-17-1C5FD6?style=flat-square&labelColor=2B3445">
  <img alt="One UI 9" src="https://img.shields.io/badge/One%20UI-9-1C5FD6?style=flat-square&labelColor=2B3445">
  <img alt="Root: KernelSU" src="https://img.shields.io/badge/root-KernelSU-1C5FD6?style=flat-square&labelColor=2B3445">
</p>

OneOS runs a second Android system next to One UI on a rooted Samsung Galaxy
and switches between the two without flashing anything. One UI stays
installed; the other system lives in a folder on the phone and starts on One
UI's kernel as a container with its own zygote and system_server. You switch
from the OneOS app and come back with **Back to One UI** (the OneOS app inside
the other system) or by holding **Volume Up + Volume Down** for 3 seconds.

OneOS started from [OneLineage](https://github.com/WeWaffles/OneLineage) by
WeWaffles, and builds its guest images with
[MysticGSI](https://github.com/MysticGSI/mysticgsi). See [Credits](#credits).

> [!WARNING]
> **Experimental. It can break your phone's data. Do not try this unless you
> know what you are doing.** OneOS replaces core parts of a running system as
> root. During development a guest system reached One UI's data and deleted
> app data and photos, and a guest once took over the phone's lock-screen
> hardware slot so that One UI could not unlock until a factory reset. Both
> are guarded against now, but untested phones and images can fail in new
> ways. **You must back up your accounts and data first, and remove the screen
> lock (PIN, pattern, password, fingerprint, face) before switching.** Only use
> a phone you can afford to reset. Nothing here is supported by Samsung,
> Google or OPPO.

## Status

App version 0.4.26. Samsung flagships with Snapdragon, plus the first two
Exynos phones; root is required (tested with KernelSU; Magisk and APatch are
detected but untested).

| Guest system | Tested on |
| --- | --- |
| Pixel 11 Fold (Android 17) | Galaxy Z Fold8 Ultra (SM-F976B), One UI 9 |
| ColorOS 17, Find N6 build | Galaxy Z Fold8 Ultra (SM-F976B), One UI 9 |
| ColorOS 17, Find X9 Ultra CN build | Galaxy S25 (SM-S931), Galaxy S25 Ultra (SM-S938), Galaxy S26 Ultra (SM-S948) |

Untested profiles, where the app asks you to tick that you know before
switching: Galaxy Z Fold8 (SM-F971) and Z Fold7 (SM-F966), Galaxy S26+ (SM-S947),
S26 (SM-S942, SC-51G), S25+ (SM-S936) and S24 Ultra (SM-S928) with ColorOS; the
Pixel 11 Fold image on the Z Fold8, the Pixel 11 Pro image on the Galaxy S26
Ultra, S26+ and S26, and the Pixel 9 Pro XL image on the Galaxy S25 Ultra, S25,
S25+ and S24 Ultra (the Pixel 11 images need a newer CPU); and on every Galaxy S phone above, the Find X9 Ultra IN (global) build
of ColorOS 17, with Google Play and the Play Store. Galaxy S23 (SM-S911) and
S23+ (SM-S916) are accepted for testing only:
their vendor software is too old and the system will most likely not start
(One UI comes back by itself; please share the session logs).

Exynos, first runs: the Galaxy S26+ with Exynos (SM-S947B, m2s) with both
Find X9 Ultra builds and the Pixel 11 Pro image, and the Galaxy Z Flip7
(SM-F766, Exynos 2500) with both Find X9 Ultra builds, used as a phone on the
main screen (no cover screen layout yet). Nothing has run on Exynos yet.

Pixel 11 Fold on the Galaxy Z Fold8 Ultra: calls and SMS on both SIMs, 5G and
Wi-Fi, Bluetooth audio, Google Play and Google's apps, the inner and cover
screens, blur, and Back to One UI (usually without a restart).

Pixel 9 Pro XL on the Galaxy S25 Ultra (first session, 0.4.22): it starts,
runs Google's setup wizard, has mobile data on SIM 1, Bluetooth and stereo
speakers, and Back to One UI works. The phone got very hot. 0.4.23 fixes the
crash loop behind that, renders at 120 Hz instead of dropping to 60, and adds
a heat cap (Advanced > Cool down when hot):
One UI's own heat control does not run in the other system, so from 45 °C
OneOS slows the processor until the phone cools.

Camera in the Pixel systems (0.4.24): the flashlight tile and apps that use
the Camera2 API work (Open Camera: Settings › Camera API › Camera2). Apps
that use the older camera API still fail; Pixel Camera itself needs Google's
camera hardware support and will not work on a Galaxy.

Known open issues for each system are in `docs/pixel-guest.md` and
`docs/coloros-on-fold.md`.

Everything else (other Exynos phones, other models, other images, other
Android versions) is refused by the app's compatibility checks.

## Your phone is not listed?

Run **OneOS Probe** on it. It is a separate read-only app: it changes nothing,
and it strips the IMEI, phone numbers and Wi-Fi names from its report (it
needs root to read the system). Tap **Run tests**, then **Share**, and post the
zip with your phone model in **Phone reports** in the
[OneOS Telegram group](https://t.me/TheoneOS). New releases are announced
there too. Probe is in the same download folder as the app (see the latest
release).

## Getting started

**Before anything else (do not skip these):**

1. **Use a tested phone.** The systems above have only been tested on the
   phones listed next to them. On any other phone the app warns you, and things
   may not work.
2. **Back up your accounts and data.** Samsung Cloud, Google and Smart Switch,
   plus photos and anything else you can't lose. OneOS guards One UI's data,
   but it is experimental.
3. **Remove your screen lock.** Settings › Lock screen › Screen lock type ›
   **None** or **Swipe**: no PIN, pattern, password, fingerprint or face. If
   something goes wrong and the phone boot-loops, a locked phone may need a
   factory reset to recover. OneOS will not switch while a lock is set.
4. **Root, battery and heat.** The phone must be rooted (tested with KernelSU),
   charged to at least 30 % and not hot (under 42 °C).

**Then:**

5. Install the OneOS app made for your phone's series and allow it in your
   root manager. From 0.4.25 there are three downloads, each about half the
   size of the old single app:
   `OneOS-<version>-fold.apk` (Galaxy Z Fold8 Ultra, Z Fold8, Z Fold7),
   `OneOS-<version>-s26.apk` (Galaxy S26 Ultra, S26+, S26) and
   `OneOS-<version>-s25.apk` (Galaxy S25 Ultra, S25+, S25, S24 Ultra, S23,
   S23+, Z Flip7). Installed the wrong one? OneOS tells you which file your
   phone needs.
6. In OneOS open **Systems**, tap **Download** on the system made for your
   phone and download it, on Wi-Fi (3.3 to 5.3 GB).
7. Back in OneOS tap **I have the file**, pick the download, then **Set up**.
   Setup takes about 15 minutes: keep OneOS open and the phone plugged in. One
   UI keeps working meanwhile.
8. Tap **Switch**. To come back, tap **Back to One UI** in the other system
   (usually no restart), or hold **Volume Up + Volume Down** for 3 seconds.
   Stuck on the logo? Hold
   **Power + Volume Down** to restart into One UI.

If your root does not survive a restart, activate it again after you come back.

**Removing OneOS:** in OneOS open **Advanced › Remove OneOS data**. It deletes
everything OneOS put on the phone: the system you set up (with the apps and
accounts in it), older copies and the session logs. It checks first that
nothing of a session is still connected to One UI, and refuses otherwise. One
UI and its data are not touched, and downloaded system files stay where you
saved them. Then uninstall the app as usual. Without the app, the same cleanup
runs from a root shell such as Termux: `sh remove-oneos-data.sh` (from
`scripts/`; it asks su for root, and `--dry-run` shows first what it would
delete).

## How it works

1. On a build machine, an OEM firmware image is turned into a system image
   (with MysticGSI, outside this repository), and `scripts/make-overlays.sh`
   patches its framework (`switcher/patches/`) so it can run as a guest next to
   One UI.
2. The app checks the phone and the image (size and SHA-256 against its own
   table), then, as root, stages the image and its patched files in
   `/data/local/tmp/oneos`.
3. `switcher/assets/oneos_switch.sh` stops One UI's zygote and system_server
   (the kernel, vendor services and radio keep running) and `guest_prepare.sh`
   / `guest_start.sh` start the guest's own framework in a mount namespace whose
   `/system` is the image and whose `/data` is the stage.
4. Guards keep the guest away from One UI's data and keys: its own vold,
   storage and installd guards, no weaver or gatekeeper writes, no new users,
   app ids of its own (`docs/app/patch-catalog.md`).
5. `return_to_oneui.sh` stops the guest and gives the phone back to One UI, in
   place when it can and by a reboot otherwise (`docs/inplace-return.md`).

## Repository

| Path | What it is |
| --- | --- |
| `app-android/` | The OneOS app and OneOS Probe (Kotlin, One UI look through SESL), the in-guest Back to One UI app, and their tests |
| `switcher/assets/` | The session scripts the app ships: switch, prepare, start, return, bridges |
| `switcher/patches/` | Framework patchers (Python and smali) applied by `make-overlays.sh`, and Samsung's installd interface table |
| `switcher/overlays/`, `switcher/native/` | Runtime resource overlays, and the source of the guest zygote launcher (`zygote_exec`) |
| `scripts/` | Build-machine tools: the overlay build, adb deploy for development, log collection |
| `docs/` | Design notes, the patch catalog, and what each test session showed |

## Building from source

```sh
git clone https://github.com/fahadalijaved23/OneOS.git
cd OneOS/app-android
./gradlew assembleProbeDebug     # OneOS Probe: needs nothing outside this repository
./gradlew test                   # unit tests (dash or busybox for the root script tests)
```

Requirements: JDK 21, the Android SDK with platform `android-37`
(`ANDROID_HOME` or `sdk.dir` in `local.properties`), and internet access to
Google Maven and Maven Central. Details: `app-android/README.md`.

The full OneOS app (`assembleFullDebug`, `assembleFullRelease`) also packs the
package sets: the files OneOS patches out of each built system image, from
`../out/overlays*`. They are not in this repository. Building the guest images
themselves is not part of this repository either (OneOS's images are built with
MysticGSI, see Credits). What is here is how OneOS patches a built image:

```sh
APKTOOL=/path/to/apktool.jar EXTRACT_EROFS=/path/to/extract.erofs \
    scripts/make-overlays.sh <system.img> out/overlays   # the set for that image
```

The build fails unless every file matches `app-android/packages/<set>.sha256`
exactly, so the sets must come from the same firmware builds. Release builds
are signed with a key from `~/.oneos-release/keystore.properties`
(`storeFile`, `storePassword`, `keyAlias`, `keyPassword`); without it the
release packaging stops. Debug builds use your machine's debug key.

## Where the images come from

This repository does not host system images, OEM firmware or the patched
framework files built from them, and GitHub releases never carry them. They
contain Samsung's, Google's or OPPO's code. The guest images are built from
the vendor's own firmware outside this repository, and the app accepts only
the builds whose size and SHA-256 it knows
(`app-android/core/model/src/main/kotlin/com/fahadali/oneos/core/model/Images.kt`).
The `firmware/` and `out/` folders are ignored by git for that reason.

## License

OneOS is licensed under the [Apache License 2.0](LICENSE). Parts of this
repository come from other projects and keep their own terms: the
OneLineage-derived session scripts (published with WeWaffles' permission). See
[NOTICE](NOTICE) and [CREDITS.md](CREDITS.md).

## Credits

- **[OneLineage](https://github.com/WeWaffles/OneLineage)** by **WeWaffles**:
  the container hot-switch OneOS is built on. OneOS's session scripts started
  from OneLineage's, and WeWaffles gave permission to publish this work on top
  of it, with credit here and in the app.
- **[MysticGSI](https://github.com/MysticGSI/mysticgsi)** (The MysticGSI
  Authors, Apache-2.0): builds the guest images OneOS runs (not part of this
  repository). MysticGSI includes TrebleDroid work by Pierre-Hugues Husson
  (phh) and contributors.
- **[OneUIProject](https://github.com/OneUIProject)**: SESL, oneui-design and
  oneui-icons (MIT) give the app its One UI look.
- **[Josh Skinner (@thatjoshguy67)](https://github.com/thatjoshguy67)**: Galaxy
  Z Fold8 support ([pull request #1](https://github.com/fahadalijaved23/OneOS/pull/1)):
  the Fold8's Find N6 ColorOS set, its cover display, Quick Settings, AOD, widgets,
  Pocket Studio and Google fixes, and Samsung's hinge sensor for half-folded
  postures and the open/close animations in ColorOS and Pixel, which the Z Fold8
  Ultra uses too.
- smali/dexlib2, AndroidX, Kotlin, Guava, ZXing and others: the full list with
  licenses is in [CREDITS.md](CREDITS.md).

Not affiliated with Samsung, Google, OPPO or OnePlus. Galaxy and One UI are
trademarks of Samsung Electronics; Android and Pixel of Google LLC; ColorOS of
OPPO.
