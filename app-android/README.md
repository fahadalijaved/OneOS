# OneOS app (Android)

> **Renamed after 0.3.6:** the stage is `/data/local/tmp/oneos` (was `/data/local/tmp/lineage_stage`), its set-aside copies `oneos.old-<epoch>` / `oneos.trash-<epoch>` (were `lineage_stage.old-*` / `.trash-*`), and the session scripts `oneos_switch.sh`, `guest_prepare.sh`, `guest_start.sh` (were `switch_to_lineage.sh`, `master_prepare.sh`, `master_inner.sh`). The app's root script and `scripts/deploy-phone.sh` rename an old stage and its copies when they are idle.

The OneOS phone app, application id and package `com.fahadali.oneos`: Kotlin,
One UI look (SESL + `io.github.oneuiproject:design`). Design and milestones: `docs/app/DESIGN.md`.
This is **Friend build 2, `0.3.7`** (versionCode 11). Friend build 2 (0.3.0)
is the first build that switches: it checks the ColorOS image the user
downloaded, prepares it in `/data/local/tmp/oneos` as root, runs every
safety gate and starts ColorOS; Volume Up+Down (3 s) returns to One UI. It
keeps everything of M1 and Friend build 1 (the device report, the read-only
tests and the findings). Phones and images (0.3.7): the Z Fold (F8U) takes
the Find N6 image or, from 0.3.7, the Pixel 11 Fold image (both have run on
it; the Pixel one so far staged over adb only); the Galaxy S26 Ultra
(SM-S948), S25 Ultra (SM-S938, on from 0.3.1) and, from 0.3.4, the Galaxy
S25 (SM-S931) take the Find X9 Ultra CN image (first sessions). No adb, no
server and no OneLineage switcher on the phone.

From 0.3.4 one codebase builds **two apps** (Gradle flavor dimension
`edition`):

| Flavor | App | Application id | Version | What it has |
| --- | --- | --- | --- | --- |
| `full` | **OneOS** | `com.fahadali.oneos` | `0.3.7` (11) | everything below: device report, Run tests, findings, OS image, Prepare, Switch, gap splash, Last session |
| `probe` | **OneOS Probe** | `com.fahadali.oneos.probe` | `0.3.7-probe` (11) | only the device report, Before you start (its own text: it only reads), Run tests (the read-only probe), Findings (redacted bundle, preview, Share, Save) and About |

OneOS Probe is for anyone who only wants to run the read-only tests and share
the findings (kept separate so people can use it on its own). It
installs next to OneOS (its own application id, so its own root grant and its
own data), has a green launcher icon with a magnifying glass, and carries no
root script, no session scripts, no stage, installd or log lists and no
package sets; its manifest has none of the switching screens. It still needs
root for the read-only tests (the same probe path as Run tests in OneOS).

## What 0.3.7 adds

- **The Pixel 11 Fold image on the Z Fold (F8U)** (`pixel11fold-yogi`,
  `google/yogi/yogi:17/CD1A.261005.003.B1`, Android 17): upload
  `OneOS_Pixel11Fold_Full_ZFold8.img.gz` (3288346862 B, SHA-256 `8fbe950c…`),
  unpacked `system.raw` 6559223808 B (`8b303c37…`); the gunzip of the .gz is
  byte-identical to `out/oneos-pixel-yogi.img` (checked 2026-10-24). Its own
  file set `pixel-f8u`, offered on the Fold only, as a tested choice (runs
  41-44 booted it there, staged by `scripts/deploy-phone.sh`), after the Find
  N6 one. Name "Pixel 11 Fold", no variant; Google Play and the Play Store
  (`googleServices`), and its sessions present the image's own GmsCore
  (`presentsGms`), so **Hide Google services is not offered** for it:
  `oneos_switch.sh` refuses `ONEOS_GUEST_HIDE_GMS=1` next to a staged
  `gmssystem_payload.img` while `ONEOS_GUEST_GMS` is on, which `session.env`
  cannot change (`ImageRef.gmsHideable`; root's `IMAGES_GMS` is empty). CPU
  rule from the disassembly of the image's `linker64`: unguarded SVE in the
  loader itself and SVE2 (`MATCH`, `EOR3`, `XAR`), so SVE and SVE2 are
  required (a WARN without them); SME only behind the CPU feature bit, MOPS
  only in ifunc variants (the SM8850 has no MOPS and booted it).
- **The `pixel-f8u` set** from `out/overlays_pixel_yogi` (scripts/make-overlays.sh,
  2026-10-24), 31 files, 485687124 B, everything but `tethering_payload.img`
  (never mounted): `services_patched.jar` and the guest vold as "gvld"
  (`vold_patched`, `service.incremental_patched.so`), `guards.txt`, the
  signal poll (`oneos-telephony.jar`, `oneos-telephony.sha256`,
  `OneOSPhoneInjection.apk`), `OneOSPixelStatusBar.apk`, **`OneOSGuest.apk`**
  (Back to One UI from inside Pixel: `hasReturnApp`, so the Switch dialog
  offers it) and 22 APEX payloads (the 15 of every set, Google's
  cellbroadcast, bt and nfcservices, the image's telephonycore, conscrypt and
  profiling, and `gmssystem_payload.img`, GmsCore). New `FileRole`s:
  `GUARD_EXECUTABLE` (vold_patched, 0755 like surfaceflinger_patched),
  `GUARD_LIBRARY`, `GUEST_APP`, `INJECTION_JAR`, `INJECTION_SHA256`; the two
  Pixel RROs are `RRO`. `checkGuards` pins the jars and both gvld binaries
  (`#` comment lines are fine; one binary alone, a wrong hash or another
  name is refused) and, for a set with GmsCore, needs the comment lines to
  name the gatekeeper, pdb, apexd and appid15000 guards the session scripts
  require. The ColorOS sets' checks are unchanged.
- **The Find X9 Ultra IN image and its sets are gone** (`coloros17-findx9u-in`,
  `x9u-in-sultra`, `x9u-in-f8u`): the server build was deleted.
  The S Ultra profiles and the S25 take the Find X9 Ultra CN image only, so
  the texts call it plain "ColorOS 17" (no second ColorOS 17 build there), and
  on the Fold "ColorOS 17" and "Pixel 11 Fold" (ticks keyed by the old names
  are asked again once). A stage the IN build left is "prepared for another
  phone or image": prepare again.
- **Root** (`oneos_root.sh`): the Pixel rows in `profile_set`, `image_raw`,
  `set_files` (`SET_PIXEL`) and `set_image`; `file_mode` gives `vold_patched`
  0755; `check_files` also refuses a leftover `oneos-*` (the Pixel set's
  `oneos-telephony.sha256`). Switching the Fold's stage between the ColorOS
  and the Pixel set: `finish` moves every file the new set does not carry to
  the attic (as before), and guest data stays with its image (Keep is refused
  for the other one; *Move it aside*). The keep refusal says "guest data"
  (not "ColorOS data"); the hide refusals say "Google services a session may
  hide". The session scripts are unchanged; app sessions still refuse
  `ONEOS_RETURN_MODE` other than reboot.
- **Package lists**: `packages/pixel-f8u.sha256` and `.guards.txt` checked in,
  the IN ones deleted. The APK carries the Pixel set instead of the IN sets
  (see Build for the size).
- **Guest data stays with its own system** (review of the Pixel change): the
  stage check (`status.list`) also looks for Pixel's launcher
  (`com.google.android.apps.nexuslauncher`), so a Pixel guest's data reads as
  Pixel data (`GuestData.PIXEL`) instead of unknown. `ImageRef.family`
  (ColorOS or Pixel): a stage's ColorOS data is never offered Keep for the
  Pixel image, nor Pixel data for a ColorOS image, also on a stage OneOS did
  not prepare (`scripts/deploy-phone.sh`) and on one whose preparation
  stopped; Prepare checks the mode again for the identified image, and root's
  `begin keep` refuses another system's data (`image_family`, `data_family`:
  the same words, ColorOS first) wherever the stage came from. A Pixel stage
  whose update stopped after root verified its `system.raw` again is kept
  with its apps and data, as a ColorOS one is (it was set aside before). A
  stage `deploy-phone.sh` set up with Pixel may be kept for the Pixel image
  (Advanced › Set up again), as a ColorOS one may for ColorOS. OS image offers
  "Use the image already on this phone" only when Prepare can keep the stage.
- **Texts**: the Before you start, OS image, Prepare, Switch, Last session and
  Old stages screens no longer say ColorOS (StringsNeutralTest covers them):
  `%1$s` is the image's name, or "the other system". For an image whose
  sessions present Google services the Switch dialog says to skip signing in
  to Google and the screen lock, fingerprint and face in its setup. The
  legal line names Pixel. The retired Find X9 Ultra IN image is named, not
  shown as its id, and its remembered .gz is "no longer supported".
- **Restore One UI's settings after a Pixel session** says what it does:
  "restored the language only (other settings the session saved stay)"
  (`guest_props.sh recover` puts back only the language and OPPO's
  `persist.oplus.*`; docs/pixel-guest.md). ColorOS's reply is unchanged.

## What 0.3.4 adds

- **The weaver guard** (442568e; `docs/app/patch-catalog.md`
  `safety.weaver_guard`): `services.jar` of all three overlay sets makes
  `getWeaverServiceLocked()` return null, so the guest never enrolls, reads or
  writes a slot of the phone's weaver hardware (a 0.3.2 session on the S25
  Ultra wrote One UI's live lock protector and the phone had to be reset), and
  `guest_prepare.sh` removes a guest lock state that still holds weaver
  records from the stage only. The four set lists in `packages/` were
  regenerated for the rebuilt sets. **No build below 0.3.4 should switch.**
- **Galaxy S25 (base) profile** `s-8750` ("Galaxy S25"), from a tester's
  probe findings of 2026-10-23 (0.2.1-probe): SM-S931B, codename `pa1q`,
  SM8750 (`sun`, Snapdragon 8 Elite, no SVE/SVE2/SME), Android 17 (SDK 37),
  One UI 9.0, kernel 6.6.127-android15, vendor API 202404, one 1080 x 2340
  panel (6.16 in), no hinge, KernelSU Next 3.4.0; its installd table is
  identical to `switcher/patches/host_installd.txt` (85 methods). Matched on
  model prefix `SM-S931` AND codename AND SoC, form BAR, the S Ultra's images
  and sets (Find X9 Ultra → `x9u-sultra`, Find X9 Ultra IN →
  `x9u-in-sultra`), untested (the untested tick at Switch), enabled, with the
  S25 Ultra's note (older vendor software) and the same CPU rule per image
  (Find X9 Ultra: some OPPO features may crash; IN: the Find N6 rule).
- **Scope rule**: a phone is in scope when its model family is Z Fold, Z Flip
  or S Ultra, or when it matches an explicit profile
  (`CompatEvaluator.inScope`). Before, the S25's report was BLOCK
  `model-out-of-scope` (family Galaxy S); now it is an untested WARN. Any
  other S-series model (S22, S24, an S25 with another codename or chip)
  stays BLOCK `model-out-of-scope`, and the BLOCK names the profiled S-series
  phones' ids (0.4.10-0.4.11 added the S25+, S26, S24 Ultra, S23 and S23+).
- **Root**: `profile_info` has `s-8750 → SM-S931 pa1q SM8750 bar`,
  `profile_set` its two (image, set) pairs. `StageAuditTest` checks the tables
  against the model, `StageScriptTest` prepares and launch-checks an S25
  stage and refuses it on an S25 Ultra or with another codename.
- **Test fixtures** `core/model/src/test/resources/bundles/s25/` from the
  tester's bundle (redacted text only: `props/key.txt`, `cpu/cpuinfo.txt`,
  `installd/table.txt`, the input device names and five carrier props; no
  serials, IDs or names).
- **OneOS Probe**, the `probe` flavor (above). Shared code stays in
  `app/src/main`; OneOS's own code, assets and resources moved to
  `app/src/full` (the `session` package, the OS image, Prepare, Switch, Last
  session and gap splash screens, `Rows.kt`, `assets/root/*`,
  `assets/logs/collect.list`, their strings and manifest entries). Per
  edition: `res/xml/home.xml`, `before_you_start.xml`, `findings_paths.xml`
  (the probe shares `cache/findings/` only), the launcher icon colour and
  foreground, and a few strings (app name, Before you start, About).
  `EditionHome` adds OneOS's ColorOS group to Home (empty in the probe);
  `CarrierProps` (the carrier props for the device report) and
  `FindingsActivity.logsDir` moved to shared code. The `oneosFiles` import and
  the root-script and set pins in BuildConfig are the full flavor's only.

## What 0.3.3 adds

- **A second image, the Find X9 Ultra IN build** (`coloros17-findx9u-in`,
  `OneOS_ColorOS17_FindX9Ultra_IN.img.gz`, 5882128321 B, unpacked
  12069945344 B, Android 17), the global build with Google services
  (`ImageRef.googleServices`; the CN builds have none). Not scanned like the
  CN build yet, so its CPU rule is the Find N6 one (MysticGSI's linker64
  warning).
- **A profile takes a list of images** (`PhoneProfile.choices`: image, file
  set, tested). F8U: Find N6 → `n6-f8u` (tested), Find X9 Ultra IN →
  `x9u-in-f8u`. Both S Ultra profiles: Find X9 Ultra → `x9u-sultra`, Find X9
  Ultra IN → `x9u-in-sultra`. The image decides the set; an untested (phone,
  image) pair needs the untested tick at Switch (on the Fold it names the
  image), and free space and the CPU rule are the chosen image's.
- **Two new file sets** from `out/overlays_x9u_in` (built by
  `scripts/make-overlays.sh` at 005359e): `x9u-in-sultra` (everything but
  `tethering_payload.img` and the fold grid) and `x9u-in-f8u` (everything but
  `tethering_payload.img`). Both carry the IN build's own
  `cellbroadcast_payload.img`, which the CN sets do not have.
- **OS image** lists every image the phone takes and says which one a picked
  .gz is (size first, SHA-256 after Check file); *Use the image already on
  this phone* identifies the stage's `system.raw` the same way (size, and the
  hash root recorded in `system.raw.id` while the file is unchanged). An
  image the phone does not take is a BLOCK naming the ones it does.
- **Root**: `begin` and `finish` name the set (`begin <mode> <profile>
  <image> <set> <versionCode>`), and the script refuses a set that is not
  that image's on that phone (`profile_set` and `set_image` must agree), at
  begin, in the plan, at finish and at launch. The marker is
  `oneos.stage/2` with the set; a 0.3.0-0.3.2 marker (`oneos.stage/1`) is
  still read, so an older stage stays OneOS's for keep and Restore, but
  never switches. `session/current.json` records the image, the set and
  `hideGms`. Guest data stays with the image that made it: *Keep my ColorOS
  data* is offered only for that image (another image gets *Move it aside*,
  with the reason), and `begin keep` refuses another image's data, read from
  the marker or from the plan of a preparation that did not finish. `recover`
  installs this build's script first (see the root path), so an unfinished
  0.3.2 session can still be restored after the update.
- **Hide Google services for this session** (Switch, only when the staged
  image has them; off by default; they stay on once a run with them
  works). `session.env` has a 14th key, `ONEOS_GUEST_HIDE_GMS` (Prepare
  writes 0); `launch <session|dry> <versionCode> <sessionId> <0|1>` writes
  the launch's value into `session.env` after every check, and root and the
  app accept 1 only for an image with Google services. `guest_prepare.sh`
  (005359e) then hides Play services, the Play Store and their helpers for
  the session; `oneos_switch.sh` needed no change (its preflight does
  not look at this key).

## What Friend build 2 adds (0.3.0)

- **Home**: a ColorOS group with *OS image*, *Prepare*, *Switch to ColorOS*
  and, after a session, *Last session*.
- **OS image** (`ImageActivity`): which image this phone's profile needs
  (`:core:model` `Profiles`, `Images`); *Pick the downloaded file* (the system
  file picker, `ACTION_OPEN_DOCUMENT`, a persisted read grant for that file;
  no storage permission); *Check file* (SHA-256 and size of the whole .gz,
  with progress; `ImageIdentifier` says verified, not checked, damaged, the
  wrong image for this phone or not a OneOS image); *Use the image already on
  this phone* when the read-only stage check finds a `system.raw` of the
  image's size (root then hashes it in Prepare and moves it to the attic if
  it differs).
- **Prepare** (`PrepareActivity`, `PrepareJob`): the checks (`su -c id`, the
  read-only stage check, One UI's installd interface, then
  `SwitchGates` PREPARE: profile, Android 17, form, image, installd equality,
  old switcher, nothing mounted, free space, screen lock WARN, carrier, CPU);
  what happens to the stage folder (*Start a new stage*, *Keep my ColorOS
  data*, *Move it aside and start fresh*; a LineageOS stage can only be moved
  aside); then, behind a dialog, the root script's verbs with per-step
  progress, Stop, and the screen kept on: `begin`, the image (the .gz
  unpacked on the fly by the app into `receive system.raw`, or `keep-raw`),
  every session script and file of the profile's set, the installd table,
  `session.env`, `finish`, and a last read of the stage. Afterwards it offers
  to delete the 5 GB download.
- **Switch to ColorOS** (`SwitchActivity`, `LaunchJob`): how to get back (the
  keys, the automatic return, a force restart, re-rooting afterwards), every
  Switch gate (BLOCK has no override: no screen lock, battery, 11 GiB free,
  the prepared files unchanged, the marker of this app build), the boxes to
  tick (an untested phone; no calls on a VoLTE-only carrier, with a fixed
  text), *Dry run* (`ONEOS_PREPARE_ONLY=1`) and *Switch*, each behind a
  dialog. The screen lock is read again right before root is asked.
- **GapSplashActivity** (`com.fahadali.oneos/.ui.GapSplashActivity`, not
  exported): the still OneOS frame `oneos_switch.sh` freezes One UI's
  surfaceflinger on during the black gap (its `Status: ok` handshake).
- **Last session** (`LastSessionActivity`, `LogJob`): when it ran and whether
  the phone restarted since (boot time from wall clock minus uptime against
  the saved launch time); *Collect logs* (read-only as root, redacted line by
  line as it arrives, never recordings or screenshots,
  `docs/app/compat-safety-logs.md` section 3.5); how it ended; the bundle in
  the findings preview with Share and Save; *Restore One UI's settings*
  (`recover`) after a session that never returned.

### The root path

- **One root script** (OneOS only): `app/src/full/assets/root/oneos_root.sh`, with fixed
  verbs `begin <new|keep|aside> <profile> <image> <set> <versionCode>`,
  `receive <name> <bytes> <sha256>` (stdin), `keep-raw <bytes> <sha256>`,
  `table <bytes>`, `env <bytes>` (stdin), `finish <profile> <image> <set>
  <versionCode>`, `launch <session|dry> <versionCode> <sessionId> <hideGms>`
  and `recover`. Every change OneOS makes as root
  is one of them. Arguments are fixed words, decimals and lowercase hex only
  (`RootScript.problems`).
- **Run only from a root-owned, pinned copy**: the app's command is always
  `su -c "<launcher>"` (`RootScript.TEMPLATE`, a fixed text). The launcher
  runs `$STAGE/bin/oneos_root.sh` only when the stage, `bin` and the script
  are root's and writable by root only and the script's SHA-256 is
  `BuildConfig.ROOT_SCRIPT_SHA256`. Only `begin` may install it, and
  `recover` into a stage with OneOS's marker whose folders are root's already
  (0.3.3: an older build's script is not this pin, and its unfinished session
  must still be restorable), from stdin, after the same hash check; never from
  the app's own storage.
- **The stage's old name**: up to 0.3.6 the stage was
  `/data/local/tmp/lineage_stage` (OneLineage's name) and its copies
  `lineage_stage.old-*`. While nothing is at `/data/local/tmp/oneos` and the
  old path is a folder, the launcher works on the old stage; before its verb
  the script renames it to `/data/local/tmp/oneos`, and every
  `lineage_stage.old-*` / `.trash-*` copy to `oneos.old-*` / `.trash-*` (same
  suffix), each only when idle: nothing mounted at or under it in any mount
  namespace (`/proc/*/mountinfo`), no loop device on a file in it, no bridge
  up, no session of this boot, the new name free (`migrate_legacy`, audited by
  `StageAudit`). An old stage that is busy stays where it is: `old-list` and
  `purge` read it there and work on both names, the other verbs refuse
  ("restart the phone first"); both stages at once are refused.
  `status.list` and `collect.list` read the old path while it is the only
  stage. Nothing has to be set up again: Prepare with *Keep my ColorOS data*
  keeps the image and the guest data.
- **Writes**: only under the stage. Documented exceptions: `begin aside`
  renames the stage to `oneos.old-<epoch>`; the renames from the old names
  above; `launch` moves itself out
  of the app's cgroup and starts the session in init's mount namespace;
  `recover` runs the prepared `guest_props.sh recover`. Nothing is deleted
  except the script's own `incoming/` files and an old `system.raw` a new one
  replaces; what is in the way goes to `$STAGE/attic/<epoch>/`. Every
  refusal comes before its verb's first change.
- **What it writes** for the session scripts (`oneos_switch.sh` checks
  all of it under `ONEOS_APP=1`): each file root:root with its mode,
  `files.sha256`, `system.raw.id`, `host_installd.table`, `session.env` and
  the marker `.oneos_stage` (`StageMarker`, `oneos.stage/2` from 0.3.3). `launch` re-checks all of it,
  the phone's ids and SDK, mounts and bridges, busybox and resetprop, the old
  switcher, the volume keys, battery and free space, then starts
  `oneos_switch.sh` detached through `nsenter -t 1 -m -- setsid`.
- **Read-only lists** (probe grammar, `probe.sh`, `ProbeAudit`):
  `assets/root/status.list` (the stage: folder, entries, marker, hashes,
  mounts in init's namespace, bridges, loop devices, an unfinished session,
  whose guest data, tools, carrier props), `assets/root/installd.list` (the
  probe's three installd entries) and `assets/logs/collect.list`.
- `RootShell` (`:core:root`) is `su -c` with a streamed stdin; when the
  source fails (not root closing the pipe) it kills su, so root never takes a
  short file for a whole one (its own size and hash checks refuse it too).

## What M1 does

- **Before you start** (first launch): OneOS is experimental and switches the
  phone into another OS without flashing, so things can break; back up
  accounts and data first (Samsung Cloud, Google, Smart Switch); remove the
  screen lock (PIN, pattern, password, fingerprint/face) before switching,
  because a locked phone that boot-loops may not get into Download Mode to
  recover; tested only with ColorOS on Z Fold (F8U). *Continue* is enabled only
  after ticking "I have backed up and removed my screen lock". Until then every
  launch opens this screen (Back closes the app). The acknowledgement is one
  int in app-private SharedPreferences (`oneos.xml`,
  `before_you_start_ack_version`; excluded from backup and device transfer);
  raising `BeforeYouStart.VERSION` asks again. Home and About open it again,
  read-only.
- **Home**: the OS package list (an empty placeholder in M1; packages are built
  on the OneOS server and shared by link in later milestones), *Check this
  phone*, *Before you start*, *About*, and "Tested only with ColorOS on Z Fold
  (F8U)".
- **Device report** (*Check this phone*): a summary of **Compatible**,
  **Warning** or **Not supported**, the findings behind it (worst first), and
  the facts:
  - model, codename, maker, model family (SM-F9xx Z Fold, SM-F7xx Z Flip,
    SM-S9x8 S Ultra);
  - form factor from the hardware: the `flip` lid input device, the hinge
    angle sensor and the built-in display count (Android 16 QPR2+ lists the
    panel that is off as well). With two measurable panels the smaller one
    decides: under 4.5" is a Flip cover screen, otherwise a Fold. The result is
    cross-checked against the model prefix; a mismatch is a warning and the
    hardware answer is used;
  - displays (id, name, pixels, size from dpi);
  - SoC from `ro.soc.manufacturer` / `ro.soc.model` / `ro.board.platform`
    (Snapdragon, Exynos, MediaTek), with the marketing name when known;
  - One UI from `ro.build.version.oneui` (`90000` = One UI 9.0), Android
    release and SDK, build ID, fingerprint, vendor API level, kernel, 64-bit
    ABIs;
  - root: installed manager apps (KernelSU and forks, Magisk, APatch) and
    `su` binaries visible to the app. **Check root** runs `su -c id` once,
    only after the user confirms a dialog. It is the only root command in M1;
  - free space on `/data`, battery level, charging and temperature,
    bootloader lock and verified-boot state;
  - screen lock from `KeyguardManager.isDeviceSecure()` (public API,
    read-only, no permission). The report re-reads it when you come back from
    Settings.
- **About**: what OneOS is and what this version does, the tested scope,
  safety, *Before you start*, credits (OneOS; OneLineage with its GitHub link
  only, `https://github.com/WeWaffles/OneLineage`, which opens in the browser;
  OneUIProject's One UI Design and SESL, MIT License).

All reads are read-only: system properties (reflection on
`SystemProperties.get`, with one `getprop` dump as the fallback), Android APIs
(`DisplayManager`, `InputManager`, `SensorManager`, `StatFs`,
`BatteryManager`, `PackageManager` with a `<queries>` list of the root
managers), `KeyguardManager` and `/proc/bus/input/devices` when SELinux allows
it. The app has no storage permission, and INTERNET only for **Send to the
OneOS team** (0.4.29: the report service in `reports/`, used only on that tap;
the OneLineage link is handed to the browser). It writes only inside its own storage: the Before
you start acknowledgement in its SharedPreferences and, after *Run tests*,
`files/probe/` (the runner and list it runs) and `cache/probe-capture/` +
`cache/findings/` (the raw capture is deleted once the redacted findings
exist).

## What Friend build 1 adds (0.2.0-probe)

- **Home**: *Run tests* and the line "Send the findings to the OneOS team".
- **Run tests** (`RunTestsActivity`): what is read, that nothing changes and
  what is removed before sharing; one row per test (tap one to see its exact
  command); *Run tests* asks in a dialog, then `su -c id`, then runs the
  probe with per-test progress (waiting / running / ok / not present / timed
  out / failed) and a *Stop*.
- **The root command list**: `app/src/main/assets/probe/commands.list` holds
  every command OneOS runs as root besides `su -c id` and
  `su -c "sh <files>/probe/probe.sh <files>/probe/commands.list"`.
  `probe.sh` runs each entry with a timeout and prints its output base64
  framed to stdout, so **root writes no file**; the app decodes it into its
  cache. `ProbeAudit` (`:core:model`) checks the list and the runner against
  a read-only allow-list in the unit tests and again before every run.
- **What is read**: all properties, CPU (`/proc/cpuinfo`, `uname`, MIDR),
  the dex that defines One UI's `IInstalld$Stub` (plus class path, jar sizes
  and SHA-256), displays (SurfaceFlinger, DisplayDeviceInfo lines, display
  and device-state XML), input (`getevent -pl`, port associations, `tsp*`
  name/enabled/cmd_list), backlight, service and HAL names, SELinux policy
  listings/hashes/type names, `df /data`, the old stage folder entry, `id`,
  root manager version. No logcat, no telephony.
- **Findings** (`FindingsActivity`): personal data is removed on the phone
  first (`Redactor`: IMEI/MEID, serials, device IDs, MACs, ICCID/IMSI, phone
  numbers incl. +966 and 05..., emails, Wi-Fi names, accounts, device names,
  locations; by property name and by value pattern, salted tokens, a
  redaction log), then `findings-<model>-<date>.zip` is built in the cache
  with `report.json` (`oneos.findings/1`), `summary.txt`, `redaction.txt`,
  the files, and `installd/table.txt` (format 1) + `host_installd.txt` when
  the app could derive the table (`:core:safety` `HostInstalldTable`,
  dexlib2). The preview shows the summary and every file; **Share** uses the
  share sheet (SESL core's FileProvider, `cache/findings/` only) and **Save
  to Downloads** the system file picker. The APK still declares no
  permission.
- **Device report**: a CPU row (cores; SVE, SVE2, SME, SME2, MOPS, BF16,
  I8MM) and two new WARNs (below).

### Summary rules (M1 + Friend build 1)

The worst finding wins (`docs/app/DESIGN.md` section 4.5,
`docs/app/compat-safety-logs.md` section 1.9). M1 only knows what an app can
read without root and without an image:

| Level | Findings |
| --- | --- |
| Not supported (BLOCK) | not Samsung; no arm64; Samsung model outside Z Fold / Z Flip / S Ultra that matches no profile (0.3.4: the Galaxy S25 has one); Exynos; `su -c id` ran and failed; free space on `/data` below the need for a typical image (10.3 GB image + 8 GB staged data + 1 GB logs + 2 GB margin) |
| Warning (WARN) | model not tested (only Z Fold F8U is; S25 Ultra SM-S938 and S26 Ultra are S Ultra family, the Galaxy S25 SM-S931 has a profile, so WARN); chip not recognised; form factor and model prefix disagree; One UI version not in a profile (seen: 9.0); "Android version differs from the OneOS images (17); switching may not work" (SDK != 37; BLOCK at switch time later); "CPU lacks <SVE2, SME> used by the ColorOS images"; no root manager found; `su -c id` timed out; "Screen lock is set - remove it before switching" (or the lock could not be read); free space unknown |
| Compatible (OK) | everything else; notes such as "root manager found, not checked yet" or "battery would stop a session now" are shown but never change the result |

So an S26 Ultra (Snapdragon) on One UI 9.0 is **Warning** (untested model)
and a Z Fold F8U with KernelSU and no screen lock is **Compatible** (with a
screen lock: **Warning**). The screen lock is advisory in M1 only: when
switching arrives (M7) a set lock is BLOCK at switch time (gate G16,
`docs/app/DESIGN.md` section 4.3; `ScreenLockRule` in `:core:model`). busybox, resetprop, the
installd ABI and the guest image checks need root or a package and come in
M2 and later.

## Modules

| Module | Kind | Contents |
| --- | --- | --- |
| `:app` | Android app, flavors `full` and `probe` | `src/main` (both): Before you start, Home, Device report, Run tests, Findings, About (`com.fahadali.oneos.ui`); `ProbeSession`, `CarrierProps` (`com.fahadali.oneos.probe`); assets `probe/{probe.sh,commands.list}`. `src/full` (OneOS only): OS image, Prepare, Switch, Gap splash, Last session, `EditionHome`, `Rows`; `StageCheck`, `PrepareJob`, `LaunchJob`, `LogJob`, `ImageCheckJob`, `RootVerbs`, `AppAssets`, `SessionPrefs` (`com.fahadali.oneos.session`); assets `root/{oneos_root.sh,status.list,installd.list}`, `logs/collect.list` and the generated `oneos/{files,sets}`. `src/probe`: its `EditionHome` (empty), home, Before you start, provider paths, icon and strings |
| `:core:model` | Kotlin/JVM | pure rules and parsers (`com.fahadali.oneos.core.model`): `OneUiVersion`, `ModelFamily`, `FormFactorRules`, `SocRules`, `RootRules`, `ScreenLockRule`, `Getprop`, `CompatEvaluator`, `Profiles`, `Images`/`ImageIdentifier`, `PackageSets`/`ShaList`, `SessionEnv`, `CarrierRules`, `SwitchGates`/`StageMarker`, `SpaceRule`, `CpuInfoParser`/`CpuRules`, `ProbeCommandList`/`ProbeAudit`, `ProbeStreamParser`, `ProbeFindings`, `Redactor`, `InstalldTableFormat`/`InstalldExpected`, `FindingsBuilder`, `Json`; JUnit tests |
| `:core:safety` | Kotlin/JVM | `HostInstalldTable` (One UI's installd table from its dex, dexlib2 3.0.10, read-only); JUnit tests |
| `:core:device` | Android library | `FactProbe`, `PropReader` (read-only fact collection; `com.fahadali.oneos.core.device`) |
| `:core:root` | Android library | `RootProbe` (manager apps, `su` paths, the old switcher through `<queries>`), `SuProbe` (`su -c id`), `RootProbeRunner` (the read-only lists), `RootScript` (the launcher, verbs and argument rules), `RootShell` (su with a streamed stdin), `StageStatus` (the stage check's output), `LogRules`/`RedactingOutputStream`/`ReturnOutcomes`/`LogBundle` (session logs), `ShellScan`/`StageAudit` (the root script's audit) (`com.fahadali.oneos.core.root`); JVM unit tests, including the root script under dash and busybox ash |

`CompatEvaluator` lives in `:core:model` rather than `:core:device` (DESIGN.md
section 3) so the rules run as plain JVM tests and, later, on the server.

## Build

Requirements: JDK 21 installed (the build uses a JDK 21 toolchain and never
downloads one; Gradle itself may run on JDK 21 or 25), Android SDK with
platform `android-37` (`ANDROID_HOME`, or `sdk.dir` in `local.properties`),
internet to Google Maven and Maven Central. No GitHub token is needed. Build
2 also needs the server's overlay sets in `../out/overlays`,
`../out/overlays_x9u` and (0.3.7) `../out/overlays_pixel_yogi` (out/ is not in
git; 0.3.3-0.3.6 also needed `../out/overlays_x9u_in`) and `dash` or
`busybox` for the root script's tests.

```sh
cd app-android
# Both apps, release (what testers get) and debug, all tests, lint of both:
./gradlew --max-workers=3 assembleFullRelease assembleProbeRelease assembleFullDebug assembleProbeDebug test lintFullDebug lintProbeDebug
# Only OneOS Probe (needs no ../out overlay sets):
./gradlew --max-workers=3 assembleProbeRelease
```

- OneOS: `app/build/outputs/apk/full/{debug,release}/app-full-{debug,release}.apk`:
  the three file sets, 864 MB of files deduplicated (0.3.6 with the four
  ColorOS sets: 703 MB, a 379 MB release APK). The Pixel set's files deflate
  to about 255 MB against the IN sets' 136 MB, so 0.3.7's release APK is
  about 500 MB (estimated from 0.3.6's APK; 0.3.0 with two sets was about
  255 MB).
- OneOS Probe: `app/build/outputs/apk/probe/{debug,release}/app-probe-{debug,release}.apk`,
  about 15 MB release and 19 MB debug (SESL, the One UI icons, dexlib2 and Guava for the on-phone
  installd table). Task `check<Variant>Apk` (`ProbeApkCheckTask`, run by
  every `assembleProbe*`) fails the build when the probe APK carries anything
  of OneOS: assets other than `probe/probe.sh`, `probe/commands.list` and
  library assets, `assets/root`, `assets/logs` or `assets/oneos`, a session
  script, list or set file by name, the `session` package or a switching
  screen in its dex, one of those screens or any permission in its merged
  manifest, or more than 30 MB. Its report:
  `app/build/reports/probe-apk/<variant>.txt`. `EditionsTest` (`:core:root`)
  checks the same split on the source sets.
- Debug builds are signed with the debug key of the machine that builds them.
- **What the OneOS APK carries** (task `oneosFiles` in `app/build.gradle.kts`, only for the `full` variants,
  generated into `app/build/generated/oneos/assets`): the files of
  `out/overlays` (set `n6-f8u`, without `tethering_payload.img` and
  `OneOSGuest.apk`), `out/overlays_x9u` (set `x9u-sultra`, also without
  `OneOSWallpapersFoldGrid.apk`) and (0.3.7) `out/overlays_pixel_yogi` (set
  `pixel-f8u`, without `tethering_payload.img`) as
  `assets/oneos/files/<sha256>`, once per hash, with `oneos/sets/<set>.sha256` and `oneos/files/index.txt` (sizes).
  **The build fails** when a file in those folders differs from the
  checked-in `packages/<set>.sha256`, is missing, or is not on the list:
  after rebuilding the overlays, regenerate the list (and
  `packages/<set>.guards.txt`) on purpose and commit them. The session
  scripts (`oneos_switch.sh`, `guest_prepare.sh`, `guest_start.sh`,
  `guest_props.sh`, `return_to_oneui.sh`, `check_host_apex.sh`,
  `bridges.sh`, `zygote_exec`) and `switcher/patches/host_installd.txt` are
  copied from `switcher/` at build time into the same store, with
  `oneos/sets/scripts.sha256`; `oneos_tunnel.sh` and `7zz` are never shipped,
  and any other new file in `switcher/assets` fails the build until it is
  added or excluded there. BuildConfig pins `ROOT_SCRIPT_SHA256`/`_BYTES`
  (the root script), `SCRIPTS_SHA256` and `SET_<SET>_SHA256` (the lists),
  which the app checks before it uses any of them.
- Unit tests: `./gradlew test` (`:core:model`, `:core:safety` and
  `:core:root`; reports in `core/*/build/reports/tests/`). The tests audit
  the shipped `assets/probe` (`app/src/main`), `assets/root` and
  `assets/logs` (`app/src/full`) files, use
  `switcher/patches/host_installd.txt` and the four findings bundles (F8U,
  S26 Ultra, S25 Ultra, S25) as fixtures, and check `packages/` against the
  sets. `StageScriptTest` runs
  `oneos_root.sh` and its launcher under dash and busybox ash (each when
  installed) against a fake root folder: `ONEOS_TEST_ROOT` prefixes every
  path, the script refuses it as uid 0, and `launch` refuses after its
  checks, so nothing can start. With `ONEOS_HOST_SERVICES_JAR=<the F8U
  services.jar>` (never committed) one more test checks that
  `HostInstalldTable` reproduces that fixture from the real jar; without it
  the test is skipped.
- Permissions: `aapt2 dump permissions app/build/outputs/apk/full/debug/app-full-debug.apk`
  (and the probe APK) prints only the package line.
- Lint reports: `app/build/reports/lint-results-fullDebug.html`,
  `lint-results-probeDebug.html`, and the libraries' `*/build/reports/lint-results-debug.html`.

**What testers get is the release build, never the debug one.**
`./gradlew assembleFullRelease assembleProbeRelease` gives
`app/build/outputs/apk/full/release/app-full-release.apk` (OneOS) and
`app/build/outputs/apk/probe/release/app-probe-release.apk` (OneOS Probe),
not debuggable (no `run-as` into the app's files) and both signed with the
OneOS release key (`CN=OneOS`, certificate SHA-256 `37560f7b…2295f83a`). The key
lives outside the repo, because the build machine's projects folder is shared:
`~/.oneos-release/{oneos-release.jks,keystore.properties}` (mode 600) in the
account that builds releases. Without it `packageFullRelease` and
`packageProbeRelease` stop instead of writing an unsigned APK. Every update must be signed with this same key: a
new key means every tester uninstalls first (and loses the app's root
grant), and a debug-signed build could be replaced by anyone holding the
shared debug key, keeping the root grant. Keep an offline copy of the key.
R8 is off (`isMinifyEnabled = false`), so the release has the same code as
the debug build; SESL and dexlib2 use reflection that shrinking could break.

Versions (`gradle/libs.versions.toml`): Gradle 9.5.0 (wrapper), AGP 9.3.3,
Kotlin 2.4.21 for every module (AGP's built-in Kotlin picks up the same KGP),
`compileSdk release(37)`, `targetSdk 36`, `minSdk 31`, JVM target 21. SESL:
`io.github.oneuiproject.sesl:{core 1.3.0, appcompat 1.4.0, material 1.5.0,
recyclerview 1.4.1, preference 1.1.0}`, `io.github.oneuiproject:{design 1.2.6,
icons 1.1.0}`, `com.android.tools.smali:smali-dexlib2 3.0.10` (Google Maven;
brings Guava 31.1-android).

`app/build.gradle.kts` excludes the stock `androidx.{core,appcompat,fragment,
recyclerview,preference,…}` and `com.google.android.material` artifacts (SESL
replaces them) and `sesl:picker-color` (it shares `picker-basic`'s namespace
and breaks the manifest merger).

`gradle.properties` is sized for the shared build server: Gradle daemon heap
2 GB, at most 3 workers, Kotlin compiled inside the Gradle daemon.

Target SDK 36 always draws edge to edge; the 2022 `ToolbarLayout` does not
handle insets, so `ToolbarActivity` pads the content view by the system bars.

