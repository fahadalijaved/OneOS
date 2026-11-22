# iOS 27 (OneiOS)

A system kind of its own in this fork (`akshaynexus/OneOS`, branch `oneios`): Apple's iOS 27 as a OneOS-style
session on the Galaxy S24 Ultra. One UI's framework stops, and instead of another Android framework the session
starts **xnuhost**, OneiOS's source-built XNU running as a process on One UI's kernel, with an iOS image set the
owner built. Volume Up + Volume Down for 3 s brings One UI back, in place when every check holds, else by a
restart. If that ever does nothing, **Power + Volume Down held until the phone restarts** always does: see
"Getting back to One UI".

OneiOS is https://github.com/akshaynexus/OneiOS. Its plan is `docs/plan.md` there; the contract between this fork
and its runtime is `oneos/interface.md` there ("session ABI 1"). This page is the fork's side.

**On the phone so far** (the S24 Ultra, 2026-11-11, 0.4.76 to 0.4.79, runtime 0.1.6): the preflight, the zygote
stop, the watchdog feeder and the in-place return ran, twice to One UI in 45 s. **xnuhost has never started
there**, and one return stood still with a black screen; both causes are found and fixed in 0.4.81 ("What the
first runs on the phone found", below). Everything after xnuhost's start is still unit tests only.

**0.4.86** (115) merges OneOS 0.4.83 to 0.4.85 and the guest wallpaper fix (#133); none of it runs in an iOS
session. It also clears the same two shell traps from OneOS's own Android scripts (a redirected `:`, `tr` reading
`/proc` itself), upstream's new ones included, and the reboot's last resorts no longer wait on each other. Not
yet run on the phone.

**0.5.14** (143) merges OneOS 0.4.88 to 0.5.13 (upstream's 0.5.13 is 142; the faster guest start and return of
#107 among them); none of it runs in an iOS session. The merge changes none of the iOS scripts or screens, and
of the boot screen's three files only `boot_status.sh`, by LineageOS 24's name in its Android path. The same two
shell traps are cleared from upstream's new lines (a redirected `:` is `true`, a `/proc/PID/cmdline` is read with
`cat` before `tr`). Not yet run on the phone.

**Upstream 0.5.14 to 0.5.31** came in by two merges (2d2f26b: 0.5.14 to 0.5.30; 728db89: 0.5.31, 2026-11-21).
None of it runs in an iOS session: `oneios_switch.sh` and `oneios_return.sh` use none of `guest_prepare.sh`,
`guest_start.sh` or `return_to_oneui.sh`, and no oneios root verb, screen or check changed. 0.5.31's changes
(fast charging shown in every system, the screen-on charging heat cap, Bring apps through the read-only view
`/mnt/oneos_oneui`, Android's logcat from under a covering mount, HyperOS's status bar) are all in the Android
guests' scripts and `oneos_root.sh`'s Bring code. The version stays the git count (`app/build.gradle.kts`): 173
at the 0.5.31 merge, one under upstream's 174; AppUpdater installs only an APK signed with this copy's
certificate, so upstream's builds never replace a fork build. Tested with `./gradlew test assembleFullDebug`;
not run on the phone.

**Upstream 0.5.32 to 0.5.35** came in by one merge (2026-11-22, branch `oneios-upstream-2026-11-22`; upstream is
https://github.com/fahadalijaved/OneOS `main`, 12 commits after 0.5.31). What they bring: Debloat (each Android
system's page, `assets/debloat/apps.tsv`, `DebloatActivity`), PixelOS 17 on the bar phones on One UI 9, the Z Fold8's
own One UI 9.5 files and its Feature flags (#328), search and system apps in Bring apps, Wireless debugging paired
inside a guest (#298), ColorOS raise to wake and its fingerprint circle, stereo through the earpiece speaker, USB-C
headphones, the One UI 9.5 r24 payloads and the Galaxy M36. None of it runs in an iOS session: the changed scripts
are the Android guests' (`guest_prepare.sh`, `guest_start.sh`, `guest_props.sh`, `oneos_switch.sh`,
`return_to_oneui.sh`) and `oneos_root.sh`'s Android verbs; `oneios_switch.sh`, `oneios_return.sh`, `oneios_root.sh`,
`boot_status.sh` and `OneOSBootStatus.dex` are as on `oneios`. Two conflicts: `app/build.gradle.kts` keeps the
fork's git count for the version (upstream set 0.5.35/178 by hand; the merge counts 193, 0.5.64), and `EditionsTest`
lists the fork's assets with upstream's new `debloat/apps.tsv`. Upstream's new lines had four redirected `:`
(`guest_prepare.sh`'s Fold8 home layout mark, `guest_start.sh`'s Fold8 input file and taskbar mark,
`oneos_switch.sh`'s adaptive mark): `true` now, as at the earlier merges. Tested on OneiOS's Mac (macOS, JDK 21,
dash, Homebrew's GNU tools on `PATH`): `scripts/build-guest-manager.sh --debug`, then `./gradlew --max-workers=3
test assembleFullDebug`: the APK 0.5.64 (193), "Staging integrity OK: 19 manifests, 529 payloads"; 700 tests, 1
failure, `StageScriptTest.debloatWritesTheListOrNothing`: BSD's `head` refuses `head -c 0` ("illegal byte count"),
so upstream's debloat read no empty list (Restore all) on a Mac only; toybox, busybox and GNU take it. The tests'
`host-tools.sh` now gives a `head` that does (Homebrew's `ghead`, else BSD's with `-c 0` as nothing); the root
script is unchanged. Then `:core:root:testDebugUnitTest --rerun`: 320 tests, 0 failures, 6 skipped (core:model 374,
1 skipped; core:safety 6, 1 skipped). Not run on the phone.

**Make iOS image with no PC** (2026-11-21): a phone with only this APK makes the whole iOS image set itself. The
flow stages the latest OneiOS runtime first when the staged one carries no kernel or its `oneios-tool` has no
`make-image`, puts the pairing files into `kb/` (root's `kbinput` ×9, as Update the kernel), then sends the tool's
one `make-image` (fetch from Apple, decrypt, the volumes, the root tweaks, the seed, the prelink, verify, the lists)
and root's `finish image` with its result. The `fetch` before it and the `tweaks` after it are gone. Set up iOS
27's image step is Make iOS image now, with the download, the room and this phone's free room said first, and
nothing on the fresh phone's path mentions a PC ("Make iOS image (no PC)"). Tested on the Linux PC, also against the
real tool on a stand-in IPSW; not run on the phone, and no OneiOS release has a tool with `make-image` yet.

**The iOS screens, redesigned** (2026-11-15, on 0.5.14): the iOS flow now has the Android systems' screens and
step order (pick, set up, the system's page, the Switch confirm with the ways back, switching, the last session),
every step saying what to do now, what is done (versions, sizes, checks), what is next, and a refusal in plain
words with its fix ("In the app"). Screens only: no root verb, argument, check or script changed. Not compiled
or opened on a device yet.

## Where its pieces come from

| Piece | Where from | In git or a release? |
|---|---|---|
| OneOS app, `oneios_root.sh`, `oneios_switch.sh`, `oneios_return.sh` | this fork | yes |
| **Runtime**: xnuhost and what it needs to run (OneiOS's own code only) | OneiOS's GitHub releases, asset `oneios-runtime-<version>-arm64.tar.zst` with `<name>.sha256` beside it; the latest release or a tag you name. Or the same file from the phone ("I have the file"), for a build of your own | OneiOS's releases |
| **Image set**: the iOS volumes, the kernel collection with Apple's kexts, the overlay | built by you from Apple's IPSW with OneiOS's scripts, imported from a `.tar.zst` file on the phone | **never**: it is made from Apple's firmware. The app has no download for it |

Both are a zstd-compressed tar with a manifest at the top: `runtime.json` or `manifest.json`, with `format` (1),
`version` and `files` (`path`, `size`, `sha256`; the runtime also `mode`). A runtime also names `session_abi`,
`xnuhost` (its path) and `image_formats` (the image formats it boots). The exact schema is in OneiOS's
`oneos/interface.md`; the image side follows OneiOS's `docs/image-format.md` once that exists.

## Scope: mainly the Galaxy S24 Ultra

`OneiosSystem.offeredOn` (`core/model/.../Oneios.kt`) is true for one profile, `s-ultra-8650` (SM-S928, e3q,
SM8650), and `oneios_switch.sh` checks the same three properties itself before anything else. That is every S24
Ultra model number, with the same card, gate and switch as the owner's SM-S928B: the US SM-S928U and U1, the
Canadian SM-S928W (its stock firmware carries the US bootloader `S928USQU...` and vendor model `SM-S928U`, which the
custom-ROM rule takes since 0.4.89), the Korean SM-S928N and the Chinese SM-S9280 (host-tested: `OneiosTest`,
`ProfilesTest`, `OneiosScriptTest.theSwitchTakesEveryS24UltraModelAsTheTestedPhone`; only the B has run a session).
The Japanese S24 Ultras (SC-52E, SCG26) are not `SM-S928`: they are warned as another phone. On the S24 Ultra
the card is last in Choose a system, marked Experimental, and the switch needs a tick every time ("I understand
that iOS 27 (OneiOS) is experimental..."), like an untested profile. The owner (2026-11-16): every other phone
is **warned, not refused** — the switch prints what to expect and goes on, the setup flows as usual, and the
switch's confirm has a third box ("mainly tested and working on the Galaxy S24 Ultra 5G (SM-S928B); on this
phone it may be unstable, miss pieces, or not come back to One UI"). A Samsung device is what the code is
written for; anything else may be unstable, half-working, or not come back.

It is not an `ImageRef`: it has no Android SDK, no `system.raw`, no package set and no guard jars, so none of the
Android guests' tables, pins or tests know it.

## In the app

The iOS flow has the Android systems' screens, in their order: **pick** (Choose a system), **download or
import** and **prepare** (Set up iOS 27, as Setting up), **switch** (the system's page, the Switch confirm, the
switching screen), **return** (Last session on the system's page, Session logs). They reuse the Android flow's
layouts and widgets, not copies of them: `activity_setup_progress`, `setup_progress_screen`, `setup_artwork` and
`setup_actions` (Setting up), `activity_environment`, `environment_artwork` and `environment_action` (a system's
page), `dialog_switch`, `home_way_tile` and `home_switch_ack` (the Switch confirm), `activity_boot_progress` (the
boot screen), and `PrebootCards`, `Cards.tileGrid`, `Cards.row`, `StepRingDrawable` and the step icons. The
redesign (2026-11-15, on 0.5.14) changed only screens: every root verb, its arguments and its order, the
preflight, the refusals and the session files read are the ones before it (`OneiosJob`; `oneios_root.sh`,
`oneios_switch.sh`, `oneios_return.sh` and the stage are unchanged). **Not opened on a phone or an emulator yet**:
the screens were written and read, not compiled on the box they were written on (it has no JDK 21 or Android SDK).

What each screen shows is read from root's `status` (`OneiosStatus`) by `OneiosFlow` (`core/root`): the steps and
their marks (pending, next, running, done, failed), each package's check, the one next action, and the line
under the steps. A refusal, `@@REFUSED` of `oneios_root.sh`, `PREFLIGHT REFUSED:` of `oneios_switch.sh` (which
root passes on as `ready 0 <why>` and as the switch's refusal) or a failure of the app's own download and
import, is put in plain words by `OneiosPlain` (`core/model`), as the Android systems' are by `Plain`: a title of
at most 40 characters, one line of at most 140, the step it is about, and the one fix (Get the runtime,
Download again, Choose the runtime file, Import the image set, Back to One UI, Remove the iOS files, Check
again, Session logs; none when the fix is outside the app: charge, cool down, restart, then Check again). The
script's own words stay under the steps ("What it said"). `OneiosFlowTest` reads both scripts and checks that
every refusal they can print has plain words of its own.

**How a check shows on the screens (2026-11-22).** iOS 27's page asks root again only when its last whole answer is
more than 30 s old (`OneiosJob.refreshIfStale`; Check again always asks, and every job reads the status when it
ends). While it asks, a full-size row says the step and counts its seconds: *Asking root for access…*, *Root
answered. Reading what is on this phone…*, *Checking the staged files and the phone…*, with **Stop**. The stage
shows as soon as root has printed it (`OneiosStatus.partial`: every line but the preflight's `ready`), before the
last check ends. When su prints nothing within 20 s (a root grant that does not come: after a reinstall with a new
signing key KernelSU sees a new app) the check stops with *Root didn't answer* and says to allow root for OneOS in
the root manager; a refusal says *Root isn't allowed for OneOS*. Before, the page said "Checking…" in a small line
for up to the whole 3 minutes of root's silence limit.
A check that finds another of the app's jobs running (an Android system's check or setup, the hardware checks, an
oneios-tool flow) shows *Waiting to check this phone*, which job and its seconds, looks again every 2 s and starts by
itself when that job has ended (at most 10 minutes, then it says so). The fixed button spins only while a job runs;
with no status and nothing running it says Check again. Before, such a check did nothing and the button spun with
no reason until another action (such as Download the latest runtime) read the status.

**What a package's check says.** Root's preflight checks, in this order, this phone and root, then the runtime,
then the image set, then the phone's state, and stops at the first refusal. For the screens (root's `status`) it is
quick (`ONEIOS_CHECK_QUICK=1`, since 2026-11-22): every file of both is there, root's, and the one root hashed at
staging by its device, inode, size and time, and nothing is hashed, so the answer comes in a moment. The switch's own
preflight is the full one ("Session flow": every runtime file and the image's files under 64 MiB hashed again)
before it changes anything. So a file rewritten in place within the second it was staged (same size, same time)
passes the screens' check and is refused by the switch (`OneiosScriptTest`). So the screens show a package as
**checked** when the preflight passed or refused something later, **check failed** when the refusal is the
package's own, and **not checked yet** when it stopped before (`OneiosFlow.check`; `OneiosFlowTest` checks the
preflight's order on the script's text).

**What `status` does not give, and how the screens do without it** (no script was changed for this):

- The runtime's size and file count: `status` reports its version, session ABI, xnuhost path, image formats and
  placeholder flag only. The app keeps its own record of what it checked when it staged each package (files,
  bytes, the time; `OneiosStaged`, in the app's preferences) and shows it only while root reports that version
  (and build). A stage made without the app (OneiOS's `oneios-tool phone stage`) shows no size for the runtime.
- iOS's data (`data/`): `status` does not name it. The switch makes it at the first switch together with
  `control/state`, so the screens say **New** while root reports the session state `never` (no state file) and
  **Kept** after that. Whether xnuhost wrote anything there is not known to the app.
- When the last check ran: `status` runs the preflight each time it is asked (each time an iOS screen opens), so
  "checked" is always the screen's own last answer.

### 1. Choose a system (pick)

The iOS card, last in the carousel, marked Experimental, on every phone (warned off the S24 Ultra: "Scope"
above). Its
button reads as an Android card's: **Set up** while root has reported no runtime or no image set, **Show
progress** while a download or an import runs (both open Set up iOS 27), else **Open** (iOS 27's page). Before
the app has asked root anything in this run it says Open.

### 2. Set up iOS 27 (download or import, and prepare)

`OneiosSetupActivity`, Setting up's layout. The title says what to do now; the footer's main button does it;
the steps say what is done; the line under them says what comes next ("Then: Make your iOS image").

| Step | Done (its line) | Next (its line; the button) |
|---|---|---|
| Check this phone | `Galaxy S24 Ultra · root allowed` | a refusal of root or of the phone (Allow root access; Check again) |
| Get the OneiOS runtime | `Version 0.1.6 · 12 files, 12 MB · every file as staged` (or `placeholder, can't start iOS`, `check failed`) | "Holds xnuhost, the program that runs iOS"; **Get the runtime**: "Where should the runtime come from?", a list with a line under each: *Download the latest release* (recommended), *Download an older release* (by its tag), *Use a runtime file I have* (the picker) |
| Make your iOS image | `iOS 27.0.1 (24A446) · 17.9 GB · every file as staged` | "This phone downloads iOS 27.0.1 from Apple and builds the image itself"; **Get the iOS image**: "Where should the iOS image come from?", *Make it on this phone* (recommended; then the download, the room it needs and this phone's free room, and Make it: the flow's own screen, "Make iOS image (no PC)") or *Use an image set I have* (the picker) |
| iOS's own data | `New: made at the first switch` or `Kept from earlier sessions` | |
| Last check before the switch | `Ready to switch` | the preflight's refusal in plain words, with its fix |

While a copy runs, the hero shows `Downloading` or `Importing · 42% · About 2 min left` over the step-wise bar, the
running step its ring, the file (`File 3 of 21: os.img (10.6 GB)`) and `3.2 GB of 17.9 GB (18%) · 412 MB/s · about
2 min left`; the footer has **Stop**, asked first as in Setting up (nothing staged before is lost). The screen
stays on, and `OneiosService`'s notification opens this screen. When every step is done the title is "iOS 27 is
ready" and **Continue** opens iOS 27's page. A download or an import started on the page shows its progress here.

### 3. iOS 27 (OneiOS): the system's page (switch)

`OneiosActivity`, a system page's layout (`activity_environment`), the artwork on top, then:

- **What runs now**, while a job runs: what it is, its step and the seconds on it (counted each second), **Stop** for a
  check, and *Show progress* for a download or an import.
- **Set up iOS 27: what is left**, while the runtime or the image set is not staged (2026-11-22): the five steps
  numbered with their marks (done, now, waiting, failed, running) and lines; the step to do now says what it needs
  and is the row to tap (the same action as the fixed button, which says it: Get the runtime, Get the iOS image). A
  failed step is tappable for its fix. Once both are staged, in its place:
- **On this phone**: four check tiles, tinted by their state: *OneiOS runtime* (`0.1.6 · checked`), *iOS image
  set* (`iOS 27.0.1 · checked`), *iOS data* (New or Kept), *Last check* (Passed, Refused, Not run yet).
- **What stops the switch**, one row: the plain refusal and its fix (tap it), or "Ready to switch".
- **OneiOS runtime**: what is staged (`xnuhost at bin/xnuhost · session ABI 1 (this OneOS: 1) · boots image format
  1`); *Download the latest runtime*; *Other ways to get it* (a list: an older release by its tag, a runtime file).
- **iOS image set**: what is staged (`Image format 1 · the runtime boots format 1`); *Make iOS image* (on this
  phone); *Use an image set I have*; *iOS data* and what keeps or deletes it.
- **Phone-built kernel** ("Kernel updates" below): the runtime's kernel and the image's `kernel.kc` with its
  build id, falling back to "unknown, staged before kernel tracking"; the prelink inputs staged of 13 and whether
  Apple's kernelcache is on the phone; *Check for a newer kernel*; **Update the kernel** (no PC: it fetches Apple's
  kernelcache from Apple once, then builds; while it runs the section shows its step, a pause or the wait for a
  network, *Pause*/*Resume*, *Stop* and its progress screen; after it, why it stopped in plain words, or
  *Activate the phone-built kernel*); *Restore the kept kernel set* while a fallback is kept; *I have the
  kernelcache file (optional)*, only for a phone without a network.
- **Last session** (the return): *Back to One UI* while a session is still open (root's `return`, as Volume Up +
  Volume Down); how the last session came back (`outcome` of `status`: in place, by a restart, by the failsafe
  with its reason); *Session logs*.
- **Tools**: *Hardware checks*. **Manage**: *Remove the iOS files* (asked first).
- The fixed button, one action: **Set up iOS 27** (nothing staged yet: opens Set up iOS 27), a fix's label, **Back
  to One UI**, **Check again**, or **Switch to iOS 27**; a spinner while root answers.

### 4. Switch to iOS 27? (the Switch confirm)

`OneiosSwitchConfirm`, the Android systems' Switch dialog: "One UI closes and iOS 27 starts on this phone's own
kernel. Nothing of One UI's is erased." The runtime and image set lines, then **Four ways back to One UI** as
tiles, before One UI closes (OneiOS's `oneos/interface.md` section 6, "Getting back to One UI" below):

1. **Hold Volume Up + Volume Down**: both together for 3 seconds; One UI comes back in about a minute, or the
   phone restarts into it.
2. **Pressed while iOS is starting?** That works too: the switch stops there, iOS doesn't start, and One UI
   comes back (a return asked during the switch wins, `control/stop.lock`).
3. **iOS never shows up?** After 10 minutes without iOS on screen (`ONEIOS_RETURN_MAX`), or when iOS stops, One
   UI comes back by itself (the watcher).
4. **Still stuck?** Hold Power + Volume Down for about 7 seconds: the phone restarts into One UI.

Two boxes, both every time: "I have read how to get back to One UI: Volume Up + Volume Down, both for 3 seconds"
and the experimental tick. **Switch to iOS 27** is on only with both. The experimental tick is what root's `switch`
gets (`switch <versionCode> 1`), as before; the other box only gates the button.

### 5. Switching to iOS 27

`OneiosSwitchActivity`, the boot screen's layout: what runs ("Checking before the switch…", then "Shutting down
One UI"), and once more how to come back. The button says "Can't cancel now" while the switch runs. A refusal
comes back as a dialog in plain words with its fix, and "Nothing changed. One UI keeps running."; its fix opens
iOS 27's page. Once root has started the switch, One UI's framework stops and the app with it.

### 6. Back in One UI (return)

After a return iOS 27's page shows under **Last session** how the session came back, and *Session logs* the logs
with their summary (below). While a session is still open (one that never stopped One UI, or is stuck) the page's
button is **Back to One UI**.

From 0.4.80 the switch first stages this build's two session scripts and the boot screen's three files again, so
an app update reaches the stage without a new import (before, only an import staged them). The redesign keeps
that: the same `script` verbs before `switch`.

### Importing either package

The import goes over the road an Android system's image takes (`PrepareJob`): the app unpacks, `RootShell` streams
each file into `su`'s stdin, the root script's `receive` writes it and checks its size and SHA-256, and a
foreground service keeps the app alive. `OneiosImport` (`:core:root`) runs it; the parts both systems use are
shared, not copied:

| Part | Android system (`PrepareJob`) | iOS package (`OneiosJob`, `OneiosImport`) |
|---|---|---|
| Unpacking | in the app, `GZIPInputStream` | in the app, zstd-jni's `ZstdInputStream` (window up to 2^27) |
| To root | `RootShell.Feed` into `oneos_root.sh receive` | the same `RootShell.Feed` into `oneios_root.sh receive` |
| Check | the app hashes while it sends; root hashes the file it wrote and refuses a mismatch | the same |
| Progress | `ByteMeter`: the screen hears of the bytes every 250 ms, with the time left | the same `ByteMeter`, also the speed |
| Kept alive by | `PrepareService` (`KeepAliveService`) | `OneiosService` (`KeepAliveService`), which also holds a CPU wakelock while the copy runs |

What the iOS import does on top, because a package is 21 files and about 18 GB behind one zstd stream:

- **One pass.** OneiOS packs `manifest.json` (and `runtime.json`) as the archive's first file. The app reads it
  from there (`OneiosPackage.manifestFirst`), checks it (`OneiosManifests.parse`: format version, plain relative
  paths, sizes, SHA-256s, no duplicates; a runtime must name an xnuhost that is one of its files with mode 0755)
  and goes on in the same stream. A package whose manifest is not first is read twice, as before 0.4.78: once to
  find the manifest, once to unpack.
- **Three threads for a file.** One reads ahead through the decompressor (`ReadAhead`, 4 MiB buffers), one
  writes to root's stdin in 4 MiB writes, one hashes the buffer being written (`HashedCopy`). Before 0.4.78 one
  thread did all three in turn, 1 MiB at a time.
- **Root's check of a large file runs while the next file is sent.** `receive` hashes the file it wrote by
  reading it again. For a file of 64 MiB or more the app starts the next `receive` meanwhile and takes root's
  answer before the file after that is done, and before `finish`. Smaller files are answered one at a time.
- **`receive` copies with `dd` in 1 MiB blocks** (`copy_bytes` in `oneios_root.sh`): toybox's `head -c` copies
  4 KiB at a time. It uses `iflag=count_bytes,fullblock` (GNU, busybox) or `iflag=count_bytes` (toybox, which
  counts the bytes it read and refuses `fullblock`), found by copying two bytes of three; a `dd` that does
  neither leaves `head -c`.
- **`finish` runs `sync` once** before it puts the new runtime or image in place.

What holds as before: a member the manifest does not list, a wrong size, a wrong SHA-256, a missing file, a
link or a device ends the import. Root refuses a file whose size or SHA-256 is not what `receive` was told and
removes its `.part`. Files land in `<kind>.new`, and only `finish`, which is asked for after root has answered
OK for every file, puts the new runtime or image in place of the old one. A failed import leaves what was staged
before untouched.

The screen during an import (Set up iOS 27 since the redesign; before, iOS 27's one screen): the file being sent (`File 3 of 21: os.img (10.6 GB)`), a bar, and
`3.2 GB of 17.9 GB (18%) · 412 MB/s · about 2 min left`. The rows are built again only when the step or the
file changes; the byte count moves the bar and that line. Before 0.4.78 the job sent a state for every MiB (a few
hundred a second) and the screen built all its rows again for each: that was the lag. The screen stays on while a
download or an import runs (`FLAG_KEEP_SCREEN_ON`), and with the screen off or the app in the background
`OneiosService` keeps it going; its notification shows the same line. *Stop* ends it.

#### Measuring the import

`OneiosImportBench` (`:core:root` tests) times the stages and the whole import on a PC against the root script
and a fake root folder. It needs a synthetic package (random and repeated bytes, `manifest.json` first; never
Apple's files) and runs only when asked:

```
ONEIOS_BENCH_PACKAGE=<synthetic .tar.zst> ONEIOS_BENCH_DIR=<folder on a disk> \
  [ONEIOS_BENCH_OLD_SCRIPT=<oneios_root.sh of 0.4.76>] \
  ./gradlew :core:root:testDebugUnitTest --rerun --tests '*OneiosImportBench*'
```

On the development PC (x86-64, NVMe, bash and GNU tools), a 4.0 GiB set of 21 files packed like the real one
(`zstd -10 --long=27`, 2.35 GiB):

| | 0.4.76 | 0.4.78 |
|---|---|---|
| The whole import | 242 MB/s (17.7 s) | 577 MB/s (7.4 s); 474 MB/s in another run |
| Screen updates sent | 4079 (about 230 a second) | 26 (about 4 a second) |
| Root's `receive` alone, 1 GiB: the write | 1.58 s (`head -c`); 1.25 s in another run | 1.05 s (`dd bs=1M`) |
| Root's `receive` alone, 1 GiB: the SHA-256 after it | 1.18 s | 1.15 s, now beside the next file |

The stages alone there: zstd 1400 to 1600 MB/s, SHA-256 in the JVM 990 MB/s, zstd with tar and SHA-256 on one
thread 660 MB/s. Without the app's own SHA-256 the whole import was 580 MB/s (507 in the other run), within the
spread between runs, so that hash stays as the second check. **None of
this has been measured on the phone**: its `dd`, `head` and `sha256sum` are toybox's, its storage and cores are
others, and the `iflag=count_bytes` branch of `copy_bytes` runs in the tests only behind a stand-in.

## Kernel updates

A new kernel used to mean rebuilding the whole image set on a PC. The app now rebuilds only `kernel.kc`, on the
phone, from the staged runtime's own XNU (`runtime.json`'s `kernel`: `kernel/xnu.macho` with its build record):
the phone's `oneios-tool prelink build` pairs it with Apple's kernelcache and the reviewed records, and the
audit and the stub check gate what lands in `make-kernel/out` (the tool refuses an `audit` failure itself, with
the log shown). Measured on the Linux PC (20 cores, cold): the whole build in 2.8 s wall with 678 MB peak RSS
(sum over the tool's processes); **not measured on the phone** (no phone is attached to this box): time and RAM
there are the open question, and the build flow is marked accordingly.

Every update keeps all hashes and configs in sync, atomically (stage-verify-activate; the previous working set
stays as the fallback; a half-updated set never activates):

- **Status**: `runtime.json`'s `kernel` object (build id, xnu, SHA-256, profile) is parsed at staging and recorded
  by root in `runtime.conf`; the iOS page shows it next to the runtime version.
- **Update check**: the latest release's runtime package is downloaded to the cache (its `.sha256` verified
  first, as for a runtime update), its `runtime.json` read without staging, and its kernel build id compared with
  the staged one.
- **On-device rebuild, with no PC** (*Update the kernel*, `OneiosToolJob` flow `KERNEL`, its order in
  `OneiosKernelUpdate`, `core/root`): what cannot be shipped is fetched and built on the phone itself. The pairing
  files ship with the app (`assets/kb/`: the kernel profile, reviewed, pairs, stubs, lead and user records,
  XnuPrelink's reviewed fixtures (`match/fixtures/`, the only matcher files the prelink reads; until 2026-11-22
  also XnuPrelink's three Python sources, for the old matcher signature); `kb/kb.json` pins their hashes, the Apple
  build they pair and Apple's decoded kernelcache's SHA-256, `kernelcache_sha256`). Apple's kernelcache is never
  committed, released or put in the APK: each phone downloads its own from Apple. One `tool work` session sends, in this order:

  1. root's `kbinput` for each of the 12 pairing files (each checked against `kb.json` by the app first, then by
     root as it writes it);
  2. unless `kb/kernelcache.macho` is already the pinned one (root's `status`, the line `kb <sha256> <n>`):
     `fetch` with `profile` `<stage>/runtime/lib/profiles/ios-27.0.1-iPhone18-2.toml`, `indir`
     `<stage>/make-kernel/inputs`, `only` `["kernelcache"]` and `resume` (the profile's member
     `kernelcache.release.v54`, 23,390,449 bytes, which the tool checks against the profile's size, CRC-32 and
     SHA-384); `im4p` with `in` `<stage>/make-kernel/inputs/kernelcache.release.v54` and `out`
     `<stage>/make-kernel/kernelcache.macho`; the `ok`'s `sha256` against `kb.json`'s `kernelcache_sha256`;
     then root's `kbcache <bytes> <sha256>`, which hashes the file itself, moves it into `kb/kernelcache.macho`
     (with `kb/kernelcache.sha256`) and removes `make-kernel/inputs` (the IM4P and the fetch's record);
  3. `prelink` (`OneiosTool.prelinkRequest`) into `make-kernel/out`.

  The decoded kernelcache stays in `kb/` (outside `runtime/` and `image/`, so `sums` and the switch's
  `check_list` see nothing new): a later runtime update builds again with no download. Every step of the tool
  says the room it needs before it writes (`space`) and refuses when it is short. Pause and Resume hold the
  download as for Make iOS image. What a stop leaves: a pause, a lost network (`failed` `network`), an ended app
  and a refusal for room, heat, the battery or a session keep the download's parts, and the next run goes on from
  them; *Stop*, a pin that does not match (the tool's `mismatch` of the member, the app's of the decode, root's
  of the file), a server file that changed (`changed`), and a decode or a build that failed run root's
  `kbclean`, which removes `make-kernel/` and never `kb/`. The stop is shown in plain words
  (`OneiosPlain.kernelUpdate`) on the iOS page and the flow's screen, with the tool's own words below.
  Measured on the Linux PC (2026-11-21, OneiOS's `oneios-tool serve` built that day, the exact requests above
  against a scratch stage): `fetch` from Apple's server in 12.4 s (`space` asked 46,760,649 bytes), `im4p` in
  0.1 s, 78,135,296 bytes, SHA-256 `349c4692…3e3`, the pin. Not run on a phone. *I have the kernelcache file*
  stays as an optional import for a phone without a network (`kbinput kernelcache.macho`, the same pin).
- **Activation** (root's `finish kernel <kc-sha256> <build-id>`): checks first — the collection is complete, its
  SHA-256 is the tool's, and its build record names this runtime's xnu and the staged kernelcache — then the old
  set aside to `kernel.prev/`, the new `kernel.kc` with freshly regenerated chunk hashes in, `image.sha256`,
  `image.ids`, `manifest.json` (the kernel entry) and `image.conf` rewritten, and a receipt in `logs/` (from/to
  SHAs and build ids, the xnu and kernelcache SHAs, the audit marker). Any check failure changes nothing; any
  state in between fails the switch's preflight (`check_list` hashes every small file and matches every file's
  identity against the lists), so a half-updated set refuses to boot instead of booting wrong. `restore kernel`
  swaps the kept set back, with its own receipt.
- **Runtime swap**: the existing `finish runtime` stages the whole package at once — runtime.json, xnuhost, the
  helpers and `lib/profiles/*.toml` all move together, every file hashed at `receive` and the set verified before
  it counts. Nothing outside the package is versioned per kernel: the switch's command line is fixed (no
  per-kernel boot-args or tunables exist in OneiOS's `oneos/interface.md`) and the bridges ship inside the
  runtime, so a kernel from the staged runtime's xnu needs no config change; a new runtime carries its own
  session ABI, image formats and `min_oneos_fork`, which staging already enforces — a newer one is refused with
  the mismatch named instead of booted against an incompatible config.

## oneios-tool in the app

From branch `app-oneios-tool` (2026-11-15). **Not run on the phone yet**: the app's side is tested on a PC against a
stand-in of the tool; the screens are compiled, not opened. OneiOS's Rust tools come in the runtime package as
`bin/oneios-tool` (OneiOS's `docs/releases.md`, "oneios-tool for the phone": why there and not in the APK). The app
runs that file as root, **one process per flow**, `oneios-tool serve`, and the tool does the work, the checks and the
step decisions on its own worker threads (all cores, nice 10, its own heat and battery stop); the app only starts it,
sends requests and shows what comes back. The protocol is the tool's (OneiOS's `tools/oneios-tool/README.md`,
"serve": one JSON object a line each way, protocol 1); `OneiosTool` (`core/model`) reads and writes those lines.

| Flow (screen, where) | Root | Requests | Shown |
|---|---|---|---|
| **Make iOS image** (Set up iOS 27's image step, its main button; the image section of iOS 27's page) | `status`, the latest runtime when the staged one has no kernel or its tool no `make-image` (`begin runtime` ... `finish runtime`, as Get the runtime), `kbinput` ×9, `begin image`, `tool work`, then `finish image <files> <format> <version> <build>` with `make-image`'s result | one `make-image` (`indir` `<stage>/make/inputs`, `out` `<stage>/image.new`, `sums_list`, `ids_list`, `work` `<stage>/make`, `resume`); no `fetch`, no `tweaks` | its phase in words, then the tool's 28 steps, progress and time left, the space it needs and has, a heat pause, Pause/Resume, Stop, and why it stopped in plain words with the tool's code ("Make iOS image (no PC)") |
| **Update the kernel** (iOS 27's page, Phone-built kernel) | `status`, `kbinput` ×9, `tool work`, `kbcache <bytes> <sha256>` after the decode, `kbclean` after a stop that cannot go on; then `finish kernel <kc-sha256> <build-id>` when the user taps Activate | `fetch` (`profile` the runtime's `lib/profiles/ios-27.0.1-iPhone18-2.toml`, `indir` `<stage>/make-kernel/inputs`, `only` `["kernelcache"]`, `resume`) and `im4p` (`in` `.../inputs/kernelcache.release.v54`, `out` `<stage>/make-kernel/kernelcache.macho`), both only when `kb/` has no pinned kernelcache; `prelink` | on the iOS page its step, a pause, Pause/Resume and Stop, and why it stopped in plain words; on its screen the tool's steps, progress, space and words |
| **Check every file** (Tools) | `tool read` | `sums` of `runtime/` and of `image/` against the lists root wrote at staging, `strict` | each file hashed again, all of them, on all cores; a difference is the tool's `refused` `mismatch` |
| **CPU, clocks and threads** (Hardware checks, "With oneios-tool") | `tool read` | `cpu` | the tool's report lines and its `cpu` rows |
| **Analyse the last session**, **iOS's own log: boots**, **last boot** (Session logs, "With oneios-tool") | `tool read` | `log-list` and `log` (`file` `xnuhost`); `ioslog-boots`; `ioslog-show` (`boot` `last`), on `<stage>/data/data.img` | the tool's lines and rows |

A flow stops at the first request that does not end with `ok` and shows that request's text. Make iOS image is a
flow of its own order (root's steps, the runtime when it needs one, then one `make-image`): "Make iOS image (no PC)",
below. What the app needs from the tool is in OneiOS's `oneos/interface.md` section 9.

**How a flow runs** (`OneiosToolJob`, app; `OneiosToolSession`, `core/root`):
- On the job's own thread (never the main thread), inside `OneiosService`, the foreground service of the import,
  which keeps the app and the CPU awake while it runs and whose notification shows the running step and its progress.
- `status` first (it puts this build's root script in the stage), then one `su -c "<launcher of tool work|read>"`.
  `oneios_root.sh tool` refuses without a staged runtime, when the runtime has no `bin/oneios-tool` ("get a newer
  runtime"), when that file is not the one root hashed at staging, and (`work`) during a session; else it `exec`s
  `nice -n 10 <stage>/runtime/bin/oneios-tool serve --stage <stage>` with `TMPDIR` `<stage>/tool`, on the app's pipe.
  Root's refusal before the tool starts is the flow's answer; so is a tool of another protocol (`hello`'s `proto`).
  A tool whose `hello` `kb` (the pairing files' format it reads; absent: 1, runtimes up to 0.1.13) is below
  `OneiosKb.FORMAT` (2, `kb.json`'s `kb`: `match/` with the fixtures alone, since 2026-11-22) cannot prelink with
  this app's `assets/kb/`: Update the kernel stops before its first request ("get the latest OneiOS runtime"), and
  Make iOS image counts it as a tool without `make-image`, so the newest runtime is staged once.
- The requests go one after the other on that one process. The screen hears of each step and end at once and of
  progress four times a second at most.
- **Stop** sends `{"cmd":"cancel","id":...}`: the tool stops at its next check, removes what it wrote and answers
  `cancelled`. Without an answer in 15 s the app ends the session as below.
- **Pause and Resume** (when the tool's `hello` lists `pause` and `resume`): Pause sends `{"cmd":"pause","id":...}`,
  Resume `{"cmd":"resume","id":...}`; the screen shows the tool's `paused`/`resumed` and its `net` `waiting` (its words
  and the seconds to its next try). How a request waits, retries and keeps its parts is the tool's.
- **The network**: while a flow runs the app watches Android's default network (`registerDefaultNetworkCallback`);
  lost, it sends `pause`, back, `resume`, unless the user paused (`OneiosToolPause`: the request is held while either
  holds it). The screen says "No network" meanwhile.
- **Started again after the app was ended**: the running flow is remembered (the app's preferences) until the tool has
  answered its last request. When OneOS was ended in the middle (Android, a crash, a swipe: the tool gets the end of
  its input and cancels, keeping the parts of a `resume` request), the tool's screen offers "Resume: <flow>", and the
  flow's requests carry `resume` where the tool takes it (`fetch`), so the tool goes on from what it kept.
- **Notifications**: the tool's screen and Set up iOS 27 ask for `POST_NOTIFICATIONS` once (Android 13+), as
  Setting up does; the flow runs without its notification when it is refused.
- **The end** (the flow's last request, a Stop that got no answer, or `OneiosService` stopping): the app closes the
  tool's standard input; the tool cancels what runs, says `bye` and exits. When it has not ended 10 s later the app
  runs `oneios_root.sh untool` as a root command of its own (with KernelSU the tool is root's, out of the app's
  signals): every process whose command line holds `<stage>/runtime/bin/oneios-tool serve`, and their children four
  levels down, get SIGTERM, then SIGKILL 2 s later. Only then does the app end its `su` (first ending it would leave
  the tool's children to init, where `untool` could no longer tell them by their parent). A request with no line from the tool for 120 s (outside a heat pause)
  ends the session the same way.

**On the phone (S24 Ultra, KernelSU; read through, not run).** `su -c` from the app becomes root in place (KernelSU),
so the tool, after the launcher's `exec`s, is the app's own child with the app's pipes: its standard input's end is the
app's close, and the app's signals cannot reach it (root's `untool` can). The stage's `runtime/bin` is run from as the
hardware checks run their tools (`check`: the same KernelSU domain, the same `shell_data_file` folder). The tool's
lines are flushed one by one (Rust's standard output is line-buffered). `untool` was made cheap for a phone with a
thousand processes: one `grep -l` over every `/proc/*/cmdline` instead of a `tr` per process, one pass of builtin `read`s
over `/proc/*/stat` per level for the children, and the wait after SIGTERM looks only at the processes found; it runs
under mksh in the tests. `OneiosService` is the import's `dataSync` foreground service, started from the screen the
user tapped (Android 14 allows that), with the 6 h a day limit of Android 15 ending the flow (`serviceStopped`).

**What the root scripts keep.** The switch, the return and every check of theirs are as before: the preflight still
hashes the runtime and the small image files itself, `receive` still checks each imported file's size and SHA-256
itself. The tool's `sums` is an extra, complete check (every file, the large ones too), not a replacement of the
preflight's. The import's receive check moves to the tool's `receive` only when the import does (see "Not done
yet").

**Tests** (`./gradlew :core:model:test :core:root:testDebugUnitTest`): `OneiosToolTest` (`core:model`, 8): the
request lines and the README's own event lines, the step marks of the tool's rule, a heat pause, pause/resume and the network's lines, the output limits.
`OneiosToolSessionTest` (`core:root`, 13) against `src/test/resources/oneios/serve-standin.sh`, a POSIX-sh stand-in
that speaks the protocol (start, space, step, progress, ok, refused, failed, cancelled, line, row, bye; a child
process per request, an idle end, a mode that ignores the end of its input): steps, progress and the result; two
requests on one process; a refusal and a failure with their codes; a cancel that ends the request and its child
while the session goes on; the end of input during a request (cancelled, by eof); a tool that does not end, ended
by the backstop; the idle end; a silent tool given up, but not during a heat pause, a pause or a wait for the network; Pause holding a request with no progress past the silence limit and Resume letting it finish; the user and the network holding one request together (`OneiosToolPause`); root's refusal before the tool; another protocol refused.
After each, no process the session started is left (the `su` stand-in, the tool, the tool's children: by
`ProcessHandle`). `OneiosToolScriptTest` (`core:root`, 4, each under every shell the machine has: sh, dash, mksh (the phone's), bash) runs the stand-in as the staged `bin/oneios-tool` through
the launcher and `oneios_root.sh tool` in a fake root: only the file hashed at staging runs; `work` is refused in a
session, `read` is not; and `untool` ends a tool that ignores the end of its input, and its child (Linux only:
it reads `/proc`). `OneiosToolRealTest` (`core:root`, 1; skipped unless `ONEIOS_TOOL_SERVE` names a host build of
OneiOS's `oneios-tool`) runs the same session against the real `serve`: `hello`, `ping`, `wait` with its steps and
progress, an unknown command refused `unknown`, `make-image` without its keys refused `usage` (`unknown` from a tool
older than `make-image`), a cancel (`by` `request`), the end of input (`bye`, `eof`). It passed on
the Linux PC against a host build of OneiOS `tool-app-progress` (PR #52, now in main) (`ONEIOS_TOOL_SERVE=... ./gradlew --no-daemon
:core:root:testDebugUnitTest --tests '*OneiosToolRealTest*'`).
`OneiosToolScreensTest` (`core:root`, 2) reads the full edition's manifest and sources: every iOS activity the code
starts is declared (`OneiosToolActivity` among them), `OneiosService` is a `dataSync` foreground service (Android 14
refuses one without a declared type), and `FOREGROUND_SERVICE_DATA_SYNC`, `POST_NOTIFICATIONS`, `ACCESS_NETWORK_STATE`
and `WAKE_LOCK` are asked for. No emulator or Robolectric runs the screens: the build box has neither; the phone test
plan (OneiOS's `docs/building.md` section 7) opens each one.

### Make iOS image (no PC)

**A phone with only this APK makes the whole image set itself** (2026-11-21, against OneiOS main at `e5fbf8d`, whose
`oneios-tool serve` has `make-image` and, since that day, the AEA decryption). Nothing of Apple's is in the APK or in
a release: the phone downloads Apple's IPSW members from Apple and builds the set there. `OneiosMakeImage`
(`core/root`) decides the order, `OneiosToolJob` (app) runs it; each step only after the one before it ended well:

1. root's `status`: no open session (else refused, "An iOS session is still open"), and a staged runtime that is no
   placeholder and carries a kernel (`status`'s `kernel runtime <build-id>`, recorded from `runtime.json`'s `kernel`
   at `finish runtime`: OneiOS v0.1.12 or newer). Without one, **the latest OneiOS release's runtime is downloaded
   and staged first**, as Get the runtime does (`OneiosJob.stageLatestForMakeImage`: the release JSON from GitHub;
   when its version is the staged one nothing is downloaded and the flow stops, "The runtime has no kernel yet"),
   then `status` again;
2. the pairing files into `kb/`: root's `kbinput <name> <bytes> <sha256>` ×9, each checked against the APK's
   `kb/kb.json` first (`OneiosKbInput`, the code Update the kernel uses too). Without them `make-image` refuses
   `not-found` ("the kernel's inputs are missing");
3. root's `begin image` (an empty `image.new`, empty `image.new.sha256` and `image.new.ids`);
4. root's `tool work`. When the tool's `hello` names no `make-image` (the v0.1.12 runtime's tool, which is older than
   `make-image`), the app closes it, stages the latest runtime once (unless that is the staged version: then it
   stops, "This runtime can't make the image yet") and opens the tool again;
5. the tool's **one** request:
   `{"cmd":"make-image","indir":"<stage>/make/inputs","out":"<stage>/image.new","sums_list":"<stage>/image.new.sha256","ids_list":"<stage>/image.new.ids","work":"<stage>/make","resume":true}`
   (`OneiosTool.makeImageRequest`; every key checked against OneiOS's `crates/oneios-serve/src/cmds.rs`
   `make_image`; the profile, the runtime's `kernel/xnu.macho`, `kb/` and the root tweaks are the tool's defaults
   from the stage). Its steps, as its `start` event lists them: `check`, `directory`, `download`, `decrypt`, `place`,
   `data`, `tweaks`, `seed`, `kernelcache`, `kernel-check` ... `kernel-place` (the prelink's sixteen, the audit and
   the stub check among them), `manifest`, `verify`, `lists`;
6. root's `finish image <files> <format> <version> <build>` with those four fields of `make-image`'s `ok` (checked
   with `OneiosRoot.problems` first; an `ok` without them is never sent to root).

**Gone from the flow:** the `fetch` before `make-image` (it fetches itself, resumably, and its `check` step asks the
whole room once and refuses `space`, and anything it cannot do, before a byte is downloaded; a `fetch` first would
have downloaded about 11 GB before that check), and the keyless `tweaks` after it (`make-image` runs the root
tweaks in its `tweaks` step; the tool now refuses that request `usage`).

**Before it starts** (`OneiosActions.makeImage`, from Set up iOS 27's image step, iOS 27's page and Run again) a
dialog says what it downloads from Apple (`OneiosTool.MAKE_IMAGE_DOWNLOAD_BYTES`, 11,382,548,957 bytes: the profile's
13 members), the room it needs at its peak (`MAKE_IMAGE_ROOM_BYTES`, 34 GiB: the profile's `need_gib` of 30 GiB for
the members and their decrypted images side by side, and about 4 GiB for the seed's tree and tar and the kernel's
work), that afterwards the image keeps about half of it (a guess: not run on a phone), and this phone's free room on
`/data` (`StatFs`), with a warning when it is less. The tool's own `space` event (`need`, `free`, its 256 MiB
reserve) is the exact check; a run that goes on from fetched members needs less, so the dialog does not refuse.

**While it runs** the flow's screen shows the phase in words (`OneiosMakeImage.Phase`: Checking what is on this
phone, Getting the newest OneiOS runtime with its file and bytes, Putting the pairing files on this phone, Making
room for the new image set, Starting oneios-tool, Making the iOS image on this phone, Putting the new image set in
place), then the tool's 28 steps with their marks, progress with the rate and time left, the `space` row, a heat
pause, the `net` wait, **Pause/Resume** (and Android's network lost and back), and **Stop** (the tool's `cancel`; during
the runtime download that download's Stop). The notification says the same. The app ended in the middle: "Resume:
Make iOS image" runs the same requests, and the tool goes on from the parts in `make/inputs`.

**When it stops** the screen says why in plain words (`OneiosPlain.makeImage`; the tool's or root's own words with
the code below them): `space` with the tool's numbers ("It needs 37.1 GB free, this phone has 12.0 GB"), `network`,
`changed`, `heat`, `battery`, `session`, `auth` (an AEA key or a byte that is not Apple's), `mismatch` (a member or
a decrypted image that is not the pinned one), `audit` (the kernel), `not-ported` (with `step decrypt`: "This runtime
can't decrypt iOS yet", for a tool with `make-image` but no AEA decryption), `unknown`, `not-found`, `usage`,
`outside`, `exists`, `io`, a cancel and a lost tool. What it leaves: the tool removes `make/build/`, the set's files
and the lists' lines; **the fetched members stay in `make/inputs`** for the next run (Remove the iOS files frees
them). **When it ends well** the set is staged (root's checks, as an import's), the iOS screens get root's new
status, and **Continue** opens iOS 27's page, where the last check and the switch are.

**The fresh phone's path**, with no step that mentions a PC: install the APK → Set up iOS 27: Check this phone →
Get the runtime (Download the latest release) → **Make your iOS image** (the step's button is Get the iOS image: Make it on
this phone, or Use an image set I have) → iOS's own data → Last check → Switch. The image step's words, the empty image row of
iOS 27's page and the image refusals ("Make your iOS image", "Make iOS image again for this runtime") say Make iOS
image now; the "How to build it" link to OneiOS's README is gone.

**Tested on the Linux PC:** `OneiosMakeImageTest` (`core/root`, 7) against stand-ins of root, the release download
and the tool: the exact order on a fresh phone (status, runtime, status, 12 `kbinput`, `begin image`, tool,
`make-image`, `finish image 21 1 27.0.1 24A446`) and with a runtime that has a kernel (no download), no `fetch` and
no `tweaks`, a runtime without a kernel replaced or refused, a tool without `make-image` getting the newest runtime
once, every refusal of the tool ending the flow with root's `finish` not asked, root's refusals before the tool, a
Stop after each step. `OneiosScriptTest.makeIOSImageRunsTheAppsRequestsAgainstTheRealTool` (skipped unless
`ONEIOS_TOOL_SERVE` names a tool with `make-image`): this root script on a fake root, a runtime staged by root's own
verbs with a kernel and one stand-in profile, the APK's real `assets/kb/`, a stand-in IPSW (nothing of Apple's;
OneiOS's `tests/serve.rs` `stand_in_ipsw`) served by `oneios-tool rangeserve` on 127.0.0.1, and the flow's exact
requests to the real `serve`: with the room short (`ONEIOS_SERVE_TEST_FREE`) refused `space` at `check` with one
`space` event and nothing fetched; with room, the request taken whole, every member fetched from the profile's URL,
then `failed` at `place` (the stand-in OS image is no APFS volume), `image.new` and both lists empty, no
`make/build`, the members kept, no `finish`. Passed against a host build of OneiOS `e5fbf8d`.
**Unproven:** a whole set made by the app (no stand-in IPSW has APFS volumes, a kernel and a kernelcache; OneiOS's
own `image build` comparison made one from Apple's members on the PC), the AEA decryption's key from Apple's key
service through the app, and everything on the phone: the 11 GB download over the phone's network, the decryption,
APFS copy, tweaks and prelink time, peak RAM and heat on the S24 Ultra, the room actually used. And no OneiOS
release has a tool with `make-image` yet (v0.1.12's has none): until one does, the flow ends at step 4 with "This
runtime can't make the image yet".

## Hardware checks

iOS 27 (OneiOS) → **Hardware checks**: OneiOS's own phone tools, run as root **while One UI keeps running**, one row
per check. They come in the runtime package (`bin/bridgectl`, `gpuctl`, `displayctl`, `brightctl`, `camctl`; OneiOS
release `v0.1.0` is the first that has them all), so the screen uses the staged runtime; with none staged it shows
*Download from OneiOS's releases* first (the latest release, the same download as on the iOS screen).
**None of the tools has run on the phone yet**: the first Run all is their first run.

| Row | Command (in `runtime/bin`) | Limit | Said before it runs |
|---|---|---|---|
| CPU layout | `bridgectl cpu` | 15 s | |
| GPU | `gpuctl` (Adreno through drm2kgsl and udmabuf; from runtime 0.1.5 all its steps: nodes, routes, probe, submit, large) | 120 s | |
| Display layer | `displayctl test` | 30 s | colour bars over the whole screen for 5 s |
| Haptics | `bridgectl haptic 200 1000` | 10 s | the phone buzzes once |
| Haptics pattern | `bridgectl haptic-pattern` | 15 s | three taps, then a ramp |
| Audio | `bridgectl audio <bin>/oneios-audio` | 20 s | a 440 Hz tone for 2 s |
| Bluetooth | `bridgectl bt` | 45 s | Bluetooth has to be off in One UI |
| Brightness | `brightctl info` | 10 s | |
| Brightness steps | `brightctl levels` | 30 s | adaptive brightness has to be off; the screen steps dim to full for 12 s |
| Light sensor | `brightctl als 10` | 25 s | cover the back, then point it at a light |
| Cameras | `camctl --backend ndk list` | 30 s | |
| Camera | `camctl --backend ndk --camera wide --frames 90 --out <checks>/camera.png capture` | 45 s | the camera is used briefly; close the Camera app |
| Cameras by the HAL (experimental) | `camctl --backend hal list` | 30 s | |
| Camera by the HAL (experimental) | `camctl -v --backend hal --camera wide --frames 90 --out <checks>/camera-hal.png capture` | 45 s | Samsung's HAL opened directly, never tried |

- **Run all** (the button at the bottom) runs the twelve ordinary rows in this order, after one dialog that lists
  what the owner will see, hear and has to do. The two HAL rows are not part of it. **Run** on a row runs that one;
  a row with something to say asks first.
- The app reads two settings itself: with Bluetooth on, the Bluetooth row is not run, and with adaptive brightness
  on, Brightness steps is not run. In Run all they are marked **Skipped** with the reason; a single Run says so and
  starts nothing.
- A row shows **Pass**, **Fail** or **Skipped** and one line: the tool's last line, or what the tool found (the CPU
  plan, the panel's node and range, frames and frame rate). Tapping the row opens the details: the command, the
  full output (the tool's stdout and stderr, selectable), and for the camera rows the PNG the tool wrote. **Copy**
  and **Share** there take that check's log; **Share all** and **Copy all** take every check's log as one text,
  headed by the app version, the runtime version, the phone and the time. A shared text is cut at 200,000 characters.
- **Skipped** also means: the tool is not in the staged runtime ("Not in this runtime: bin/camctl"), the owner
  pressed Stop, or root refused (an open session).
- **Stop** ends the running tool and leaves the rest of the queue as Skipped.

How a check runs. `oneios_root.sh check <id>` (the app's usual launcher; the id is one of the table's, nothing
else is taken): refuses during an iOS session, without a staged runtime, and when One UI is not fully up; runs only
the file whose SHA-256 root recorded when the runtime was staged; starts it with no stdin and `TMPDIR` in
`<stage>/checks`; prints its output as it comes (once a second, whole lines, each cut at 2000 characters, at most
20000; before 2026-11-22 all of it after the tool ended) and `exit <code>`, `timeout <seconds>` or `missing <tool>`. The
checks screen's running row shows the seconds of the limit (`12 s of at most 120 s`) and the tool's latest line. The app
(`OneiosChecks.classify`, `core/model`) reads the verdict from the exit code **and** the tool's lines:
`ok`/`failed` for bridgectl, `ok`/`FAILED at: ...` for gpuctl, `displayctl: ok`, `brightctl: ok` (plus a `panel:`
line that names a device, a `restored` line), `back end: ndk, N cameras` with N above 0, and for a capture frames
read, a written PNG and a picture that is not black. The failure lines of camctl's README
(`status -10013`, `hal: no service`, `exception -8, camera status 2`, `configureStreams ... status 1`,
`no frame arrived`, `(black`) each add a line that says what it means.

**Time limits.** Root's: at the row's limit the tool gets SIGTERM (bridgectl, brightctl and displayctl put back
what they changed on it), 2 s later SIGKILL, only if the pid is still that tool. The row then fails with
"Ended after N s". The app's: 20 s after root's limit it ends the root command itself and runs `uncheck <id>`.

**What is put back** after a tool was ended (by root's limit, by Stop, or by `uncheck <id>`): the tool and its
helpers are killed (only processes whose command line is a file of `<stage>/runtime/bin`, and the display test's
`OneiOSDisplay` layer process); the backlight is written back to the level read before `brightctl levels` ran; the
light sensor's `enable` file gets the value it had before `brightctl` ran; the display test's socket folder is
removed. A tool that ends by itself has done this itself (each README's "restore").

**What the checks never do** (`OneiosScriptTest.theChecksLeaveOneUiAlone`, on the script's text): set a property,
stop or start a service or zygote, run a session script, enter another namespace, mount, reboot, or write outside
`<stage>/checks`, except those two put-back writes under `/sys/class/backlight` and `/sys/class/input`. The camera
check's picture stays on the phone: in `<stage>/checks` and, for the details view, in the app's cache; Share sends
text only.

## Session logs

iOS 27 (OneiOS) → **Session logs** (`OneiosLogsActivity`, `OneiosLogActivity`, `OneiosLogsJob`): what the iOS
sessions left in the stage, read as root after the return. **Not run on the phone yet.**

- **Sessions**: *Last session* (or *This session (still open)*) is `session/xnuhost.log`; up to five *Earlier
  session* rows are `logs/xnuhost-<epoch>.log`, newest first. Each row has the time of the log's last line, its
  size, and how it ended, read from its last 40 lines (`exit 4 · kernel panic`, `exit 0 · stopped by SIGTERM`; with
  no end line, the log's last line).
- **The switch, the return and the helpers**: `switch.log`, `return.log` (the return's steps, the watcher's and the
  key readers' lines), `control/display.log`, `control/watchdog_feeder.log`, each when it exists.
- **A row opens the log.** Its last 256 KiB are read and shown first, scrolled to the end; earlier chunks of 1 MiB
  follow by themselves until 4 MiB are read or the log is whole, and *Load earlier lines* above the first line reads
  4 MiB more (the viewer holds 250,000 lines at most). The search field and the chips **E** (xnuhost's error
  lines), **!!** (lines from signal context), **panic** (the word by itself, not `-no_slto_panic` of the boot
  arguments) and **guest** (the kernel's console) narrow what is shown: chips add up, the search narrows further.
  A long press copies a line. **Copy** takes the lines shown, with the summary first (the last 200,000
  characters). **Share** reads the whole log again and hands it over as a file, the summary in the message's text.
- **Share all as a zip**: every listed log, whole (a log past 32 MiB keeps its last 32 MiB and says so), at its
  path in the stage, plus `summary.txt` with the app, the phone, and each session's summary. The files are made
  under `files/logs/oneios-session`, which the app's file provider serves to the app chosen in the share sheet.
- **What is shared here is the log as it is on the phone**, not redacted: an xnuhost log is the kernel's console
  and xnuhost's own lines. *Collect logs* (Last session) is the way that removes personal data; from 0.4.76 it
  takes these files too (below).

**The summary** above an xnuhost log (`OneiosLogs.summarize`, `core/model`):

| Line | From |
|---|---|
| Boot got to | the furthest of nine stages seen, in this order: `xnuhost I xnuhost: session ABI` (xnuhost started); `xnuhost I cpu0: entering the kernel at`; the console's `Darwin Kernel Version` (kernel start); `BSD root: ` (root mount); `load_init_program: attempting to load` (launchd loading); the first `com.apple.xpc.launchd\|` line (launchd running); the first console line with `backboardd[`; the first with `SpringBoard[` or `crashed: SpringBoard.`; `xnuhost I guest ready: first frame` (xnuhost writes `session/ready` with it). A stage before the furthest that was never seen is named |
| Kernel panic | the text after `panic(cpu N caller 0x...): ` of the console, the first of the last boot that panicked |
| Processes that died | the console's `sheng-exit: NAME[PID] status 0x.. reason ns .. code 0x..` (the signal is the status's low 7 bits), `Process[PID] crashed: NAME.` and `[NAME: killed] exiting with signal N`, counted once per process: by name, with the count and the signals |
| Ended | xnuhost's `stopping: WHY (reason R, code C)` (`signal 15` is the return's SIGTERM; `the guest halted on cpuN` with reason 2 a panic, 0 a shutdown, 3 a return asked by the guest; `PSCI SYSTEM_OFF`; `kernel fault`), its `exit N` with the meaning of OneiOS's exit code table, `xnuhost !! fault inside a host call` or `fault on a host thread` (a crash of xnuhost itself, with the signal), a log that ends before the kernel was entered (setup; the last error line), or no end line at all (killed, a restart of the phone, or still running). Then, from `return.log`, the return that started within two minutes of the log's last line: who started it (the watcher with its reason such as `return asked (keys: Volume Up + Volume Down down for 3 s ...)`, `xnuhost N ended`, `the guest did not report ready within 600s`; the app; the key readers; by hand) and how it came out (`One UI restored in place`, `FAILSAFE: ...`) |
| Counts | lines, xnuhost error lines, lines from signal context, in-place restarts of the guest; and a note while only the end of the log has been read |

The markers are the lines xnuhost's sources print (`runtime/xnuhost/src/main.c`, `log.c`, `cpu.c` in OneiOS, its
`docs/booter.md`) and the lines the kernel printed in OneiOS's boots on the PC (`logs/fb-boot.log`,
`logs/keystore-boot*.log`); OneiOS's `oneos/interface.md` section 8 lists them as what the fork reads. The
`backboardd` and `SpringBoard` stages go by the first console line that names the process with its pid, which is
what those logs have; a boot whose console never names them is shown as stopping at launchd.

How it is read. `oneios_root.sh logs` prints, for each log that exists, `@@RESULT log <id> <bytes> <mtime>` and its
last 40 lines (each cut at 400 characters) as `| <id> <line>`; ids are `session`, `xnuhost-<epoch>` (the five
newest), `switch`, `return`, `display`, `feeder`. `logfile <id> <end> <bytes>` prints `@@RESULT chunk <id> <size>
<start> <end>` and the bytes `[start, end)` as `| <line>`: at most 1 MiB a call, `end` 0 being the file's end, and
whole lines only (a chunk that does not start the file starts after its first line break, and the next call ends
there). Both verbs **only read**: no file is made, changed or moved, each read of a file runs under `timeout 20`,
and the app ends a root command that has not answered in 45 s. `session/` is the guest's to write, so a log is
read only when it is a plain file with one name in a folder that is no link. The launcher runs only this build's
root script: on a stage that holds an earlier build's, the screen's first read runs `status` once, which puts this
build's script there.

**Collect logs** (`assets/logs/collect.list`, entry `logs.oneios`, from 0.4.76): the same files (and
`return.outcome`) from `/data/local/tmp/oneios` go into the bundle's `oneios/` folder, through the same runner,
the same read-only audit (`ProbeAudit`) and the same redaction as every other entry (the Wi-Fi and Bluetooth
names learned first, the masks of `Redactor`). A file past 64 MiB is skipped with a note, as for every `files`
entry.

## Stage

`/data/local/tmp/oneios`, root:root, mode 0700. It is not the Android guests' stage (`/data/local/tmp/oneos`),
and neither kind of session starts while the other's stage has anything mounted.

| Path | What |
|---|---|
| `bin/oneios_root.sh` | the app's root script; the launcher runs it only with the SHA-256 pinned in BuildConfig |
| `oneios_switch.sh`, `oneios_return.sh` | the session scripts, pinned the same way, staged with every import and before every switch |
| `bin/boot_status.sh`, `bin/OneOSBootStatus.dex`, `bin/oneos_boot_icon.png` | OneOS's boot screen (below), the same three files an Android guest's stage holds, pinned and staged like the session scripts |
| `runtime/`, `runtime.conf`, `runtime.sha256`, `runtime.ids` | the unpacked runtime; its version, session ABI, xnuhost path and image formats; every file's SHA-256; every file's `dev:inode:size:mtime` |
| `image/`, `image.conf`, `image.sha256`, `image.ids` | the same for the image set |
| `data/` | iOS's own writable state. A new runtime or image keeps it; Remove deletes it |
| `session/` | what xnuhost and the switch share in the running or last session: `xnuhost.log`, `xnuhost.pid`, `ready`, `return.request`, `display.sock`, `tmp/` |
| `control/` | the way back's own: the session's state, the baseline, xnuhost's pid and namespace as the switch recorded them, the watcher's and key readers' pids, the return's lock and guard; `bootui/` (the boot screen's status files and pids) and `bootui.log` (the switch's lines about it). Read-only in xnuhost's namespace, like the two session scripts and `bin/` |
| `logs/` | the five sessions before the last: `xnuhost-<epoch>.log`, moved there by the next switch (the epoch is that switch's time; the file's own time is its session's last line) |
| `checks/` | the hardware checks' own: each check's last output (`<id>.log`), the camera pictures (`camera.png`, `camera-hal.png`), the values to put back (`saved.backlight`, `saved.als`), the tools' temporary files |
| `tool/`, `make/` | `TMPDIR` of `runtime/bin/oneios-tool serve` ("oneios-tool in the app"); Make iOS image's work folder: `make/inputs/` the fetched IPSW members and `inputs.json` (kept for the next run; the set's images are hard links to them), `make/build/` the build's own files, which the tool removes at the end, on a cancel and on a failure |
| `switch.log`, `return.log`, `return.outcome` | the switch's output; the return's, the watcher's and the key readers'; how the last return ended. `control/display.log`, `control/watchdog_feeder.log` and `control/usb.log` are the display helper's, the watchdog feeder's and the USB watcher's ("USB and adb during a session") |

## Session flow

`oneios_root.sh switch` runs the preflight (`oneios_switch.sh --check`) and returns its refusal to the app as one
line. Only when it passes does it start `oneios_switch.sh`, detached, in init's mount namespace.

**Preflight, before any change.** Root; the S24 Ultra; the stage and both session scripts root's own; a runtime
whose session ABI is this build's, with an xnuhost that is root's, executable and an arm64 ELF; every runtime
file's SHA-256 again; an image set of a format the runtime boots, every file the one root hashed at staging
(files under 64 MiB are hashed again; `ONEIOS_VERIFY_IMAGE=1` hashes all); nothing in either folder that its list
does not name; the root manager's busybox and resetprop; init's mount namespace; One UI fully up; no session of
either kind open; the volume keys readable; battery at 30 % or charging and not hot; 2 GiB free; the tick. Any
failure prints `PREFLIGHT REFUSED: <reason>` and exits: nothing was changed, One UI keeps running. **Until a
runtime with xnuhost is staged, this is where every switch ends.**

**Then:**

1. Session folder, control folder and baseline: boot id, SELinux mode, properties, the pids of vold, keystore2,
   surfaceflinger and servicemanager, init's mount points, the panel's brightness, and **One UI's clock caps**
   (`control/base/clocks`: each node, One UI's value, the session's): Samsung's `cpufreq_limit`
   (`/sys/devices/system/cpu/cpufreq_limit/cpufreq_max_limit` and `cpufreq_min_limit`, `drivers/cpufreq/cpufreq_limit.c`
   of the SM8650 kernel: SSRM's one value for every cluster, a freq QoS request of its own, so `scaling_max_freq`
   alone does not lift it; `-1` releases it), `scaling_min_freq` and `scaling_max_freq` of every cpufreq policy,
   `/sys/kernel/gpu/gpu_max_clock` and KGSL's `max_gpuclk`. The first phone run (0.4.87's scripts, 2026-11-12) lifted
   the GPU (500 -> 1000 MHz) but not the CPUs: their `scaling_max_freq` read 1689600/2035200 after the write, the
   `cpufreq_limit` cap. One UI (Samsung's SSRM in
   system_server) caps them when the phone is warm and its power HAL raises the floors in bursts; with
   system_server stopped, its last values stayed for the whole session (1.7-2.0 GHz CPUs and a 500 MHz GPU after a
   warm One UI, the S24 Ultra, 2026-11-12). `switch.log`: `Clocks of One UI: ...`. Also **One UI's USB gadget** (`control/base/usb`, "USB and adb during a session" below): `USB of One UI: ...`.
2. The way back is armed first, each part in a session of its own (`setsid`) in init's mount namespace: the
   watcher, a `getevent` reader per volume-key device, and a poll of the keys' state. A kernel wakelock
   (`oneios_session`) keeps the phone awake without One UI's power manager. **One UI is not stopped unless all
   of them run and the wakelock is held**; if not, the switch ends there.
3. The boot screen starts (below). Under the stop lock, after its last look for a return and just before the stop mark,
   the switch saves the shmem THP mode (`control/base/shmem_enabled`) and writes `advise` for xnuhost's 2 MiB host
   pages (OneiOS 8a9caf3). The file saves only the bare mode (`never`, `advise`, ...), parsed from the bracketed token
   of the node's annotated line; both sides compare bare modes, because writing the whole
   `always within_size advise [never] deny force` line back is `EINVAL` (the 2026-11-16 Gate A failure and reboot).
   The return writes it back and reads it back: before gate A's end on a normal return (a failure there is the
   failsafe), and on an early return too, when One UI was never stopped (a failure there is logged only: One UI
   runs). Until 2026-11-23 the switch wrote it at the baseline, before the way back was armed, and an early return
   left `advise` until the next boot (ported from `YMGPwcca/OneOS` 403d8b4; `shmemComesBackAtAnEarlyReturn`,
   `theSwitchWritesShmemOnlyUnderTheStopLock`). Then One UI's zygote and zygote_secondary are stopped, so
   system_server and every app end; a loop keeps them stopped. surfaceflinger, the vendor composer, audioserver, netd, vold, keystore2 and the radio keep running.
   Once system_server is gone the switch marks `control/clocks.set`, releases `cpufreq_limit` (`-1`, first), and
   writes the hardware's range into the other nodes (`cpuinfo_min_freq`, `cpuinfo_max_freq`, the top of `gpu_freq_table` and `gpu_available_frequencies`),
   one line each in `switch.log`: `clocks: NODE OLD -> NEW (reads N)`. The kernel's thermal zones, trips and
   cooling devices are never written, nor anything under `/sys/power` but the wakelock: the kernel's junction
   trips, LMh and xnuhost's own thermal step (OneiOS `runtime/bridges/thermal`) are what cap a session.
   Samsung's software watchdog gets its magic close and a feeder, as in an Android session. With USB debugging on, the USB watcher starts (below): adb stays on the USB gadget across unplug and replug.
4. xnuhost starts in a **new mount namespace** in which the stage is bound over `/data`; `runtime`, `image`,
   `control`, `bin` and the two session scripts are read-only there. It gets a cgroup of its own
   (`/sys/fs/cgroup/oneios_session`), the v1 cpuset's root (`/dev/cpuset`: every core; the shell the app started kept the
   app's cpuset, and `background` allows only the A520s, where xnuhost's cpu-pin cannot place a vCPU on the X4 or an A720;
   `oneios inner: cpuset ...` in `session/xnuhost.log`) and `oom_score_adj` 500, so that it, not One UI's daemons or the way back,
   is what the kernel ends when memory runs out:
   `/data/runtime/<xnuhost> --session-abi 1 --mode takeover --runtime /data/runtime --image /data/image --data /data/data --session /data/session`.
   If One UI's `/data` is still visible there, or `control` is writable there, it does not start.
   From 0.4.81 the shell that sets this namespace up writes a line to `session/xnuhost.log` before each step
   (`oneios inner: 08:12:21 making /data/runtime read-only`), and however it ends before xnuhost starts, its last
   line is `oneios inner: ... ended with status N in step: ...`. The switch waits for it by its progress: until
   it wrote xnuhost's pid, for as long as that shell runs (`control/inner.pid`), 30 s at most; a shell that ended
   is not waited for. A shell still setting up when a return begins is ended by its pid, and it starts nothing if
   the switch's state is no longer `starting`.
5. The watcher returns to One UI when xnuhost ends, when `session/return.request` appears (the volume keys write
   it; xnuhost does when the guest asks; `adb` can), or when xnuhost has not created `session/ready` within
   600 s of its start (`ONEIOS_RETURN_MAX`; iOS never came up).

**Return** (`oneios_return.sh`), five steps, each logged to `return.log`:

1. **The session ends.** SIGTERM to xnuhost, 20 s; then everything that is left is killed: the cgroup at once
   (`cgroup.kill`), every process in xnuhost's mount namespace, and every process outside init's namespace whose
   mount table still shows the stage. The key readers and the watcher end. The boot screen, where it is still
   up, says "Returning to One UI" during this step and is ended at its end, before the first gate. Then the
   panel's brightness and, when the switch marked `clocks.set`, **One UI's clock caps** go back from the baseline,
   in the reverse order of the switch's writes: `clocks: NODE NOW -> OLD (One UI's)` in `return.log`, also after
   a SIGKILL of xnuhost (the return runs on every way back but the reboot, which resets them anyway). Only those
   nodes and only numbers; a node that cannot be written is logged and does not stop the return. The USB watcher ends here too.
2. **Gate A.** No such process is left (a killed one that is still in the kernel gets up to 30 s of the gate's 45, killed again every second; each one is logged once with its `comm`, state and `wchan`, from its own `/proc/PID` files); the stage is mounted in no process's mount table (every namespace, not
   only init's: OneOS's run 45); nothing was mounted on One UI's partitions; the same boot; vold, keystore2 and
   servicemanager have their pids of the switch; the daemons One UI cannot restart are running; SELinux is as
   it was. Persist properties that differ from the switch are logged by name (the scripts set none).
3. **Gate B: display and services.** The stop loop is gone; One UI's boot-loop counters go back to the switch's
   (in memory). Then the display, as in OneOS's return: **the vendor composer is restarted, surfaceflinger with
   it** (restarted by name if it outlived the composer, started if it had died), and the boot animation starts.
   Then audioserver and the rest of zygote's restart list (cameraserver, media, wificond, and perfmond and
   media.tuner if they ran). Each must come back and register.
4. **One UI's framework.** `vdc volume abort_fuse`, a fresh zygote_next, `ctl.restart netd` (whose own restart
   list starts zygote; `ctl.start zygote` otherwise). First the USB gadget and adbd go back to One UI's where they differ (`usb:` lines; "USB and adb during a session").
5. **Gate C.** system_server keeps its pid until user 0 is unlocked and 20 s more, within 180 s.

**Every step has a time limit of its own** (0.4.81), kept by the return's guard, a process of its own: 90 s to
stop the session, 45 s for Gate A, **75 s for Gate B**, 45 s to start One UI's zygote, 290 s for Gate C (its
waits are 60 s, 180 s and 20 s). A step that stands still, on a command that never comes back, is rebooted out
of at its limit (`GUARD: '[3/5] Gate B: ...' did not finish within 75s`), not after the guard's 600 s for the
whole return. Gate B's waits for a service to register are by the clock (a `service check` that does not answer
takes 3 s each time).

A failed check anywhere is the failsafe: `sys.powerctl reboot,oneios-inplace-failsafe`, then Android's own
`reboot`, then busybox's `reboot -f`, then sysrq. None of them waits on the one before: Android's `reboot` (which
waits for init once it set the property) runs in the background, and each `sync` is given 5 s at most. Busybox needs no reboot applet: KernelSU's has none, and from
0.4.77 the switch no longer asks for one (`oneos_switch.sh` never did). In the session's mount namespace the stage is bound over `/data`, which hides the root manager's busybox
(`/data/adb`): from 0.4.79 the namespace's setup runs a copy in `control/busybox` (as `guest_prepare.sh` copies
busybox into an Android guest's `/data`). `oneios_return.sh reboot` goes straight there. A return with no open session does
nothing, and a switch that ended before it stopped One UI's zygote (the stop is marked in `control/stopped`)
only has its helpers ended: neither restarts anything.

**A return asked while the switch runs wins** (since 2026-11-12; before, a return during step 3 found no mark yet,
tidied up and ended, and the switch then stopped the framework anyway: xnuhost did not start and nothing returned).
The switch and the return meet at `control/stop.lock` (`mkdir`, atomic). The switch takes it for its stop: it looks
at the state and `session/return.request` once more inside it, writes `control/stopped`, stops zygote and
system_server, and gives it back; it also ends without stopping anything when a return was asked before step 3, or
when the lock does not come within 15 s, and it starts no xnuhost when a return was asked after the stop. The return
takes the lock right after it writes `returning` (waiting up to 15 s for a stop under way) and keeps it, so its look at
`control/stopped` is final and no switch stops One UI after it. "Nothing to restore" also needs One UI's zygote
running; a state `returned` with the mark and the framework down is returned again. A switch whose xnuhost does not
start runs `oneios_return.sh switch-failed` itself, and no longer only counts on a watcher that may have ended.

## USB and adb during a session

**The rule: adb over USB works for the whole iOS session, across unplug and replug, and the return leaves the USB
gadget as One UI had it** (2026-11-13; OneiOS's `oneos/interface.md` section 6a is the same rule from the other
side). **Not run on the phone yet.**

**The repairs are off by default** until a phone session has shown them to be right: the record, the watcher's
lines and the return's `usb:` lines always come, but the watcher and the return write nothing (each repair is
logged with `(repairs are off: logged only; ...)`, the return says `usb: repairs are off ... nothing put back`)
unless the stage has the file `usb-repair` at the switch (`su -c 'touch /data/local/tmp/oneios/usb-repair'`, or
`ONEIOS_USB_REPAIR=1` for a switch by hand); the switch records it as `repair=1` in `control/base/usb`, which the
watcher and the return go by. Remove the file to turn them off again. So with the default, a session is as
before for USB: nothing of it is changed.

Why: the USB gadget's functions are set by One UI's framework, UsbDeviceManager in system_server (through the USB
gadget HAL or init's `sys.usb.config` triggers), on every plug-in and unplug. The switch stops system_server, so
from then on nobody re-arms the gadget: whatever unbinds it or drops adb from it stays for the session. adbd and the
UDC binding themselves outlive the framework (OneiOS's session of 2026-11-13 morning kept USB adb through the switch,
the session and the return with the cable in from before the switch). On 2026-11-13 afternoon a cable plugged in
during a session showed no USB device on the Mac at all; but the Mac had not seen the phone on USB before that
switch either (it was staged over wireless adb), with One UI whole, so that session's missing USB came before the
switch: the cable, the Mac's port, or a gadget state One UI already had (a guess until the lines below come back).

What the scripts do:

1. **The switch's baseline** (`usb_save`, One UI whole) writes `control/base/usb`: `adb=` (1 when `sys.usb.config` or
   `persist.sys.usb.config` has adb, or `settings get global adb_enabled` is 1), `config=`, `state=`, `persist=`,
   `controller=` (`sys.usb.controller`, kept only when it is one path component), `udc=` (the gadget's UDC file,
   `/config/usb_gadget/g1/UDC`), `adbd=` (`init.svc.adbd`), `configfs=`, `repair=` (1 with `usb-repair` in the stage). `switch.log`: `USB of One UI: state ...,
   config ..., UDC NAME STATE; bound '...', adbd ..., ffs.ready ..., cable ...; USB debugging on|off`.
2. **After the framework's stop** (step 3), with USB debugging on, the **USB watcher** (`oneios_switch.sh
   --usb-watch`, `setsid`, init's mount namespace and the switch's root cgroup, never xnuhost's; a plain shell loop,
   no realtime thread; its pid in `control/usb-watch.pid`, its lines in `control/usb.log`) reads the gadget every 3 s
   (the properties `sys.usb.state`, `sys.usb.config`, `sys.usb.controller`, `sys.usb.ffs.ready`, `init.svc.adbd`
   and three named files: the UDC file, `/sys/class/udc/<controller>/state`, `/sys/class/power_supply/usb/online`)
   and logs a line when it changed. At most one repair every 21 s (with the repairs on; off, logged only), each only back to One UI's own value, in this
   order:
   - adbd not running: `setprop ctl.start adbd`;
   - adb gone from `sys.usb.config`: One UI's config again (`setprop sys.usb.config mtp,adb` on a phone that had
     that);
   - the UDC file empty (or `none`) while One UI had it bound: One UI's controller written into it;
   - a cable in for 15 s with the UDC still `not attached`, `attached` or `powered`: re-armed, `sys.usb.config none`
     then One UI's config (what OneOS's adb watchdog of the Android sessions does), and the UDC written again if it
     stayed empty. Twice per plug-in at most, so a charger that never enumerates is left alone.
   With USB debugging off at the switch it is not started. It ends on `control/usb-watch.off` or when the state is
   `returning`, `returned` or `failed`. It is not part of the way back: nothing of the return waits for it.
3. **The return** ends it in step 1 (`usb-watch.off`, then its pid, as the other helpers) and, in step 4 before One
   UI's zygote starts and with the repairs on, puts back what differs from `control/base/usb`: `sys.usb.config` (`setprop`, with its triggers,
   then up to 3 s for `sys.usb.state` to follow), adbd (`ctl.start` when it ran at the switch) and the UDC file (One
   UI's controller, when it was bound at the switch and is empty now). `return.log`: `usb: before the restore: ...`,
   what was put back, `usb: after the restore: ...`; with no record, `usb: no record of the switch`. Logged only,
   never a reason for the failsafe.

Only properties and named files: the UDC is found by the name in `sys.usb.controller`, and `/sys/class/udc`, the
gadget's folder and `/sys/class/power_supply` are never listed. Nothing persist is written, nothing under
`/sys/power`, no input device is opened, no reboot. xnuhost logs the gadget too (`usb: state S, config C, UDC NAME
STATE` at its start, on every change and at its stop: OneiOS `docs/booter.md` 2.9a). `control/usb.log` is not on
the app's Session logs screen yet (`oneios_root.sh logs` is unchanged); `oneios-tool phone log --file usb` reads it.

What the next sessions on the phone should bring back (one with the repairs off, the default, which shows what the
gadget does with nothing re-arming it; then one with `usb-repair`; each with the cable plugged in during the session, and unplugged
and plugged in again once): `oneios-tool phone log --file usb` (`control/usb.log`), `phone log --file switch`
(its `USB of One UI:` line), `phone log --file return` (the `usb:` lines), `phone log --grep 'xnuhost I usb: '`,
`control/base/usb`, and, with One UI back, `getprop sys.usb.config`, `sys.usb.state`, `persist.sys.usb.config`,
`sys.usb.controller`, `sys.usb.configfs`, `sys.usb.ffs.ready`, `init.svc.adbd`, `cat /config/usb_gadget/g1/UDC` and
`cat /sys/class/udc/$(getprop sys.usb.controller)/state`, and `logcat -d -b all | grep -iE 'UsbDeviceManager|usb_gadget|adbd'`.

## Boot screen

From the stop of One UI's framework until iOS draws, the screen shows **OneOS's own boot screen**, the one a
switch to an Android guest shows. Before 0.4.80 it went black there, and since iOS does not draw a frame yet, a
session looked like black and then One UI again, as if the phone had restarted. **Not run on the phone yet.**

What is reused, not written again (`docs/boot-status.md`):

| Piece | For an Android guest | For iOS |
|---|---|---|
| `boot_status.sh`: the status files (`title`, `status`, `verbose`, `generation`, `ready`, `stop`; iOS adds `progress` and `next`, the bar), the supervisor that restarts the renderer when surfaceflinger changes | `oneos_boot_begin enter` / `restart` / `return`, status directory `<Android stage>/data/oneos_bootui` | `oneos_boot_begin ios`, status directory `control/bootui`, the files from the stage's `bin/` (`ONEOS_BOOT_HOME`) |
| `OneOSBootStatus.dex` (`switcher/patches/OneOSBootStatus.java`): a root `app_process` that draws on a SurfaceControl BLAST layer at z 2,000,000,000 | icon, title, and the status line with Verbose boot on | the same, with the status line always on and a `hint` file drawn near the bottom edge (status and hint wrap) |
| `oneos_boot_icon.png` | the OneOS icon | the same icon. **No Apple logo, name or mark is drawn**: the title is the text "Starting iOS 27" |
| Where the status comes from | Android's boot events (`logcat -b events`) and the scripts' `ctl.start` / `ctl.stop` | the switch's feeder (`oneios_switch.sh --bootui`), from `session/xnuhost.log`; the supervisor's `ios` mode reads no Android event and does not wait for a boot animation |
| How it ends | the new framework's display-ready event or its boot animation's end; at most 600 s | the stop flag: at the hand-off, at the return, or after 1800 s |

**What it shows.** The OneOS icon; the title **Starting iOS 27**; one status line; under it **a bar and a
line "Step N of 12 · Next: ..."** (since 2026-11-22: what happens now and what comes next); and near the bottom
edge **Hold Volume Up + Volume Down for 3 s to go back to One UI**.

**The steps.** The boot is twelve steps. Each begins at the first line of `session/xnuhost.log` that names it (or
at the switch, for step 1); the status line is the step's name, the `next` file the next one's. The typical
lengths are from the phone's boots of 2026-11-22 (`out/session-logs/2026-11-22` in OneiOS: `xnuhost-s3` to
`xnuhost-s8`, five later boots and one first start, `xnuhost-s4`; the time from xnuhost's start, read with the
same markers), and step 1 from the switch's log (`gpu-debug/switch.log`, `[3/5]` to `[4/5]`).

| Step | Status (and the next step's name) | Begins at | Typical length |
|---|---|---|---|
| 1 | Stopping One UI's framework | the screen is up, One UI's zygote is being stopped (`bootui_begin`) | 18 s (2026-11-22), 17 s (2026-11-20); 44-49 s on 2026-11-16 |
| 2 | Starting xnuhost | the first `oneios inner: ` line, or `xnuhost I xnuhost: session ABI` | 0.6-0.9 s |
| 3 | Locking iOS's RAM | `xnuhost I memory: the guest's RAM is held for the session` | 3.0-3.6 s (the prefault) |
| 4 | Starting the kernel | `xnuhost I memory: the guest's RAM is held: `, `cpu0: entering the kernel at`, console `Darwin Kernel Version` or `BSD root: ` | 2.2-2.7 s |
| 5 | First start: making iOS's Data store (once) | console `OneiOS Data: first start` | 22.2 s (first start only) |
| 6 | First start: unpacking iOS's data (once) | console `OneiOS Data: unpacking the seed` | 9.7 s (first start only) |
| 7 | Starting launchd | console `load_init_program: attempting to load` | 20.2-21.8 s (0.5 s on the first start) |
| 8 | Starting iOS's system services | console `com.apple.xpc.launchd\|` (launchd's first line) | 11.0-12.7 s (19.0 s when backboardd came first, s3) |
| 9 | Starting SpringBoard | the first console line with `SpringBoard[` or `crashed: SpringBoard.` | 6.2-7.0 s |
| 10 | Starting the display (backboardd) | the first console line with `backboardd[` (its framebuffer open) | 3.6-4.1 s (steps 9 and 10: 22.1 s on the first start) |
| 11 | Waiting for iOS's first picture | `xnuhost I display: the guest's first frame of its own` (black: `session/ready` waits for a frame with content) | 23.0-38.9 s (s6 to s8); 120 s when iOS's frames stayed black (s3 to s5, `ready-content-wait`) |
| 12 | iOS is up: handing the screen to it | `xnuhost I guest ready: first frame` | until the display helper's first post (the hand-off, below) |

From xnuhost's start to `ready`, a later boot took 71.6-88.8 s (s6 to s8; 169-172 s with black frames), the first
start 192.0 s (s4); step 1 comes before that. The weights add up to 102 s for a later boot and 134 s for a first
start. SpringBoard and backboardd come in either order (backboardd first in s3 and on the boots of 2026-11-16 and
2026-11-20); a step is only ever raised, so when backboardd comes first, step 9 is passed over.

Besides the steps, the status line says:

| When | Status | Next |
|---|---|---|
| console `panic(cpu N caller 0x...): TEXT` | Kernel panic: TEXT | (none) |
| xnuhost ended | iOS stopped: kernel panic: TEXT; or iOS stopped: WHY (xnuhost exit N), from `stopping: WHY` and `exit N`; or xnuhost ended with exit N; or xnuhost ended: its last `xnuhost E` line | Going back to One UI |
| xnuhost never started | xnuhost did not start: the log's last line | |
| the watcher returns | the title becomes **Returning to One UI**; the status is the reason above, or "A return to One UI was asked for", "iOS did not start within 60 s", "iOS did not come up within 600 s"; the bar goes | |
| a return from the app, by hand or from the key readers | **Returning to One UI**, Stopping iOS; the bar goes | |

**The bar.** The feeder writes two files beside `status`, each whole (a temporary file, then `mv`) and only when
it changes: `progress`, `<step> <steps> <fraction>` (e.g. `7 12 0.243`), and `next`, the next step's name (empty
at step 12 and after a panic). The fraction is the share of the boot's typical time (the table's lengths, as
the weights 18 1 3 2 22 10 20 12 7 4 35 0 s) of the steps before this one, plus the time in this one up to 90% of
its own share; it is never less than the last value written, and it is 1.000 at step 12. Steps 5 and 6 count
only on a first start: the feeder expects one while the stage has no `data/data.img` (xnuhost makes it on the
first start), and the log decides (a `OneiOS Data: first start` or `unpacking the seed` line, or launchd's step
reached without either). A later boot goes from step 4 to step 7: the count goes on past the two. When xnuhost
starts the guest again in place (a new `session ABI` line), the steps and the bar start again at step 2. On a
panic or when xnuhost ends, the bar stays where the boot stopped. The return (the watcher's and
`oneios_return.sh`'s first step) removes `progress` and `next`, and the feeder writes neither once the state is
no longer `starting` or `running`. The renderer draws the bar (300 points wide at most, white on grey) 22 points
under the status's last line and the step line under it in the hint's grey; without a valid `progress` file it
draws nothing more, as before (an Android guest's screen never has one). The feeder looks once a second at what
the log gained (at most 1 MiB a look); one `awk` a second computes the fraction. The log is the guest's to
write, so what is drawn from it is cut to 200 characters of printable ASCII.

**The hand-off.** The display helper's layer is above the boot screen's (z 2,147,483,646 against 2,000,000,000)
and opaque. So when the helper posts the guest's first frame, that picture covers the boot screen, and the
feeder then stops the boot screen under it: it sees `oneios-display: first frame posted` in
`control/display.log` with the helper still running, or `session/ready` with the helper running and its
`oneios-display: layer up`. This is how OneOS hands its boot screen to a guest's compositor: the new picture
first, then the stop flag, and the renderer takes its own layer away. **While iOS shows nothing, the boot screen
stays**: `ready` without a running helper leaves it up ("iOS is up: handing the screen to it", the bar full), because
taking it away would leave a black screen with no way back written on it. It is not brought back if the helper
ends later. `control/display.log` is this session's only: the switch moves the last session's to
`display.log.1` before it starts the helper. A helper started again by hand during a session appends its pid to
`control/display.pid` (OneiOS's `runtime/display/README.md` has the command), or the hand-off never sees it and the
boot screen stays up under the helper's layer (phone, 2026-11-13: the renderer was still running when the owner
pressed the power key, after a helper that had started late).

**The size.** The renderer draws for the logical size One UI's display manager gave it (1080 x 2340 with One
UI's resolution set to FHD+). The display helper, when it connects in a takeover, sets the display's projection
to the panel's own mode and leaves it so. The feeder sees its `oneios-display: display projection set to the
active mode` and writes `native` to the status directory; the renderer then draws for the active mode's size.

**The return** ends it on every path. `oneios_return.sh` writes the title, and at the end of its first step
(before Gate A, and before the branch for a switch that never stopped One UI) sets the stop flag and a new
generation, which retire the supervisor, the renderer (it removes its layer) and the feeder; the feeder is
killed at once, the other two after a second if they are still there, each by its pid and only while that pid is
still the same program. The same happens before every reboot the return asks for (the failsafe, the guard, the
reboot return); the watcher's own reboot sets the stop flag. The three processes are One UI-side: init's mount
namespace, the root cgroup, never the session's, so the gates do not count them, and a renderer that could not
be ended is logged and nothing more: Gate B restarts the composer and surfaceflinger, which drops every layer.

**Optional, like OneOS's** ("every failure leaves the original boot/return path intact"). The screen starts only
after the way back is armed and checked. If one of the three files is not staged or not root's, if there is no
`app_process`, or if the renderer posts no frame, the switch goes on exactly as before 0.4.80 (the renderer gets
3 s before One UI is stopped, and is given up after 30 s without a frame). Nothing of the watcher, the key
readers, the poll or the gates reads anything of the boot screen's. It opens no input device (`getevent` stays
the only reader of the keys, and it does not grab), sets no property, holds no wakelock and stops no service.
`ONEIOS_BOOTUI=0` (over adb) turns it off.

## What the first runs on the phone found

Three switches on the S24 Ultra on 2026-11-11 (07:24 with 0.4.76, 07:38 and 08:12 with 0.4.79), each ending
`!!! xnuhost did not start`. The evidence: `switch.log`, `return.log`, the stage's listing, and the kernel log of
the boot that was force-restarted (`/proc/last_kmsg`).

**1. xnuhost never started, and from 0.4.79 the inner shell said nothing.** The shell that sets up xnuhost's
namespace checked that `control/` is read-only there with `if : 2>/dev/null > /data/control/.w; then`. `:` is a
*special builtin*, and Android's `sh` (mksh R59) ends the whole script when the redirection of a special builtin
fails; with `2>/dev/null` before it, without a word, with status 1. So the check ended the shell exactly when it
succeeded. On the phone: `sh -c 'if : 2>/dev/null > /proc/nonexistent/.w; then echo writable; fi; echo survived'`
prints nothing and returns 1 (bash prints `survived`, which is why the PC's tests under bash never saw it, and
the tests under mksh never ran this branch: it is behind the session). It fits the stage: `control/busybox` was
copied at 08:12 (the step before the binds), no `session/xnuhost.pid`, an empty log, and no process left for the
return to kill (the shell had exited, its namespace with it). In 0.4.76 the shell never got that far (busybox was
hidden by the bind, fixed in 0.4.79). The 10 s wait was not too short: the shell was gone within a second.
Reproduced on the PC with 0.4.79's script under mksh in a user and mount namespace: the same end. Fixed: no script redirects `:` any more (`true` is not a special builtin), in `oneios_switch.sh`,
`oneios_return.sh` and `oneios_root.sh`; the trace and the wait by progress above.

**2. The return of 08:12 stood still at Gate B** (`=== [3/5] Gate B ===` at 08:12:34, then nothing; a black
screen until the owner's forced restart at 08:21). The kernel log shows init received no `ctl.restart` for the
composer (its last control message is the switch's), and a process `tr` with pid 32734, 134 pids after the
return's own 32600, **on a CPU** at 428 s, 516 s, 581 s and 593 s of uptime (the return began at 330 s). Gate B
begins by waiting for the stop loop to end, asking each time whether its pid is still that script:
`tr '\0' ' ' < /proc/PID/cmdline`. The stop loop ended in that moment (it had just been told to). A read of
`/proc/PID/cmdline` whose process ended after the open fails with ESRCH, and **toybox 0.8.13's `tr` reads again
for ever when a read fails**. On the phone, with a 3 s limit: `tr a b < /system` (EISDIR) and `tr` on the open
cmdline of a `sleep` that ended both run into the limit (exit 124); `cat` ends with the error. It is a race, so
the returns of 07:25 and 07:39 passed. Fixed: `cat PID/cmdline | tr` everywhere a cmdline is read (the return,
the switch, and OneOS's `boot_status.sh`), so the read error ends `cat` and `tr` sees the end of a pipe; and the
step limits above, so that anything else that stands still in Gate B is a reboot after 75 s, not a black phone
for ten minutes.

Also in that log, not this fork's doing but worth knowing: the phone's reset history
(`/data/log/power_off_reset_reason.txt`) has two kernel panics between the sessions, at 07:49 and 08:02
(`_raw_spin_trylock`, `usercopy_abort`), with One UI running and no session open.

## Getting back to One UI

The way back is entirely on One UI's side. Nothing in it needs the guest to cooperate, to be responsive, or to
have started at all. From the fastest to the one that cannot fail:

| # | What | Works when |
|---|---|---|
| 1 | **Volume Up + Volume Down, 3 s.** One `getevent -lq` reader per key device (on this phone Volume Up is on `gpio-keys`, Volume Down on the PMIC's `pmic_resin`). When both are down, a timer looks at the two keys every 0.25 s for 3 s; a release of 0.5 s or more ends the hold, a shorter one does not (the S24 Ultra's two keys are one rocker, and pressing both ends chatters) | always, unless a program grabs the key device |
| 2 | The same chord from the keys' **state**: `getevent -pl` asks each device twice a second (EVIOCGKEY; a key that is down is marked `*`); seven samples with both down, one sample without them in between allowed | also when a program has grabbed the keys: a grab takes the events from other readers, not the state |
| 3 | **The watcher**: returns on `session/return.request`, when xnuhost ends, when the switch never started it (60 s), when the guest never reported `ready` (600 s) | iOS crashed, never started, or asked to leave |
| 4 | The key readers start the return themselves if the session is still not returning 5 s after their request | the watcher is gone or stuck |
| 5 | **The return's guard**: a process of its own that reboots the phone if a step of the return has not finished within its own limit (75 s for Gate B; above), or the whole return after 600 s; the watcher reboots at once if the return script cannot run or ends with an error | a step of the return hangs or the script is damaged |
| 6 | **The failsafe reboot** on any failed check of the return | anything about One UI's state is in doubt |
| 7 | **Power + Volume Down, held until the phone restarts (about 7 s)** | always |

**What the guest cannot do to 1 to 6.** The watcher, the readers and the poll are One UI-side processes: started
before xnuhost exists, in init's mount namespace, each its own session, in the root cgroup (which cannot be
frozen and is not xnuhost's), `oom_score_adj` -1000, at a higher priority than ordinary processes, and they run
on One UI's kernel, not on anything the guest schedules. A guest that hangs, spins on every core or runs out of
memory does not stop them. What they read is in `control/`, which xnuhost's namespace has read-only: a guest
that empties its `session/` folder is still returned from. The watcher keeps the wakelock up every 10 s.
What xnuhost must not do, by its contract on OneiOS's board (`docs/agents.md`, "booter -> oneos"): grab an input
device, run its threads in a realtime scheduling class (on every core that would leave the way back 5 % of
the CPU), leave its cgroup or mount namespace, or write to `/sys/power`. Path 2 covers a grab all the same.

**The display and the GPU.** xnuhost draws the guest with the Adreno (KGSL) and, in a session without One UI's
compositor, on the panel itself (DRM). The kernel takes all of that back when the process ends, however it
ends: its KGSL contexts and memory are freed and its DRM master and framebuffers are dropped on SIGKILL exactly
as on a clean exit, so nothing has to be released by xnuhost. What can be left is on One UI's side (a composer
that last saw another DRM master, a surfaceflinger whose GPU context a guest fault reset or that is stuck in a
call), which is why the return never trusts the old display state: it always restarts the composer and
surfaceflinger and requires both back. A GPU that does not recover fails those checks, or Gate C, and ends in
the reboot. A process the kernel cannot end (stuck in a driver) fails Gate A after its 30 s wait: reboot. (Phone, 2026-11-12 23:15: Gate A looked once, 1 s after the last SIGKILL, and a task that was still ending made it reboot; the wait is for that case.)

Not ported from OneOS's return: holding the composer (`oneos_boot_hold_display`). It keeps the return splash's
last frame on the panel while no surfaceflinger exists; an iOS session's boot screen is ended before the gates
("Boot screen", above), and the composer's client here is One UI's own surfaceflinger, which a stopped composer
would only block. So from the end of the return's first step to One UI's boot animation the screen is black.

**The hardware restart (7).** Holding the Side (Power) key and Volume Down together for about 7 seconds is the
phone's forced restart. It is done by the PMIC, below Android's kernel and everything in this session: the two
keys are the PMIC's own inputs on this phone (`pmic_pwrkey`, `pmic_resin`), the reset is set up once at boot,
and neither a grab of the keys, a hung kernel nor anything this session runs changes it (the scripts and
xnuhost never touch the PMIC's reset settings). **It always lands in One UI**, because a session
changes nothing that survives a restart: nothing is flashed, no partition of One UI's is written, no persist
property is set, SELinux's mode is not changed, and the reboot the scripts ask for names a reason
(`oneios-return`, `oneios-inplace-failsafe`) that the bootloader takes as an ordinary restart. The session
lives in processes, a mount namespace, a cgroup and two kernel wakelocks, and all of them end with the kernel.
The files it leaves are under the stage; the next switch clears `session/` and `control/`.

This is true by construction and is Samsung's documented forced restart for this phone; it has **not been
pressed during an iOS session**, because no session has run (below). On the first run over adb: start a
session, hold the two keys, and check that One UI boots and `oneios_root.sh status` reports no open session.

**From inside a working iOS.** xnuhost's host call `XH_HALT_RETURN` writes `session/return.request` and exits,
which is a return (3). What calls it from iOS (a Settings row, an AssistiveTouch action) is OneiOS's userland's
to add and is not needed for any of the above. The OneOS app's own *Back to One UI* does not go through
`return.request`: it runs `oneios_return.sh` directly (root's `return` verb), so it works without a watcher;
the two meet at the return's lock.

## One UI's data guards

- xnuhost and every iOS process run in a mount namespace where `/data` is the stage. One UI's app data,
  `/data/system`, `/data/misc` (keystore, gatekeeper, lock-screen files) do not exist there, and the session
  aborts if they do.
- The session scripts and the root script write only under the stage. They never call setenforce, never set a
  `persist.*` property, never talk to vold, keystore2, gatekeeper, weaver or locksettings, and mount nothing in
  init's namespace. `OneiosScriptTest` checks this on their text. The return unmounts nothing either: a
  namespace that still had the stage as its `/data` would see One UI's `/data` in its place, so its processes
  are ended instead, and what cannot be ended is a reboot.
- The Android guests' guard jars are not involved: an iOS guest has no binder client.

## Tests and build

- `core/model` `OneiosTest`: the S24 Ultra-only gating and the tick; manifest parsing (format version, paths,
  sizes, hashes, a runtime without xnuhost); verification against a manifest; unpacking a tar with the manifest
  first, last or under a top folder; damaged, padded and truncated packages; the release JSON and `.sha256` file;
  the runtime's `kernel` object (present, absent, malformed); `kb/kb.json`; the kernel activation checks and the
  staged-vs-release kernel comparison.
- `core/root` `OneiosScriptTest`: the launcher, `oneios_root.sh` and `oneios_switch.sh`'s stage checks run under
  the machine's shells against a fake root (`ONEIOS_TEST_ROOT`; the scripts refuse it as uid 0 and start nothing
  there): the refusal without a runtime, a runtime without xnuhost, changed files, mismatched pairs; and the
  guards on the scripts' text.
- **Kernel updates.** The same class, against fake stages: `kbinput` stages the 13 allowlisted inputs (and
  refuses any other name); `finish kernel` checks the phone-built collection (complete, its SHA-256, built from
  this runtime's xnu and the staged kernelcache) and refuses a wrong one or a wrongly paired one with nothing
  changed and no stray files; then the swap (files, hashes, lists, manifest, configs, receipt) and the fallback,
  and `restore kernel` puts the kept set back with its own receipt; every verb refuses during a session.
  `EditionsTest` pins the `kb/` assets (each the hash `kb.json` names, exactly the set the root script takes).
  `kbcache` keeps a fetched kernelcache only when root's own hash is the pin (another hash or size is deleted
  and refused, nothing lands in `kb/`), removes the IM4P, and `status` then reports it; `kbclean` removes
  `make-kernel/` and never `kb/`; both refuse during a session. `theKernelUpdateFetchesFromApple...` runs the
  whole update against the real `oneios-tool serve` and Apple's server when `ONEIOS_TOOL_SERVE` and
  `ONEIOS_PROFILE` are given (skipped otherwise; run on the Linux PC, see "Kernel updates").
- `core/root` `OneiosKernelUpdateTest`: Update the kernel's order against stand-ins of the tool and root (the 12
  `kbinput`s, `fetch`, `im4p`, `kbcache`, `prelink`), a kernelcache already on the phone skipping the download, a
  decoded file that is not the pinned one refused with `kbclean` and no build, a Stop at each request (or between
  two) cleaning up, a lost network or short room keeping the parts; `core/model` `OneiosTest` pins the two
  requests' keys and their JSON line, `OneiosPlainTest` every stop's plain words within the limits.
- `core/root` `OneiosMakeImageTest` (7): Make iOS image's order against stand-ins of root, the release download and
  the tool (a fresh phone: status, the runtime, status, 12 `kbinput`, `begin image`, the tool, `make-image`, `finish
  image`; a runtime with a kernel downloads nothing; no `fetch`, no `tweaks`; a tool without `make-image` gets the
  newest runtime once; the tool's refusals and root's end the flow where they come; a Stop after each step).
  `OneiosScriptTest.makeIOSImageRunsTheAppsRequestsAgainstTheRealTool` runs the flow against the real `serve` on a
  stand-in IPSW when `ONEIOS_TOOL_SERVE` names a tool with `make-image` ("Make iOS image (no PC)"). `core/model`
  `OneiosTest` pins `make-image`'s keys and JSON line, `OneiosPlainTest` every stop's plain words within the limits
  and none of them naming a PC.
- The same class runs **the way back** against a fake phone: the key readers, the poll, the watcher and
  `oneios_return.sh` themselves, with stand-ins for Android's tools
  (`core/root/src/test/resources/oneios/phone-tools.sh`), processes as folders, and a clock that runs faster.
  No real process is signalled. Covered: a return before, during and after the switch's stop (the stop lock), the chord on two devices, a chattering hold (a short lift about once a second
  through the hold: the rule before 2026-11-12, no release at all for 3 s, never returned there), a long release, a short hold, one key, auto-repeat, an old
  session's reader, the poll with no event at all, the keys starting the return without a watcher; the watcher
  on xnuhost's end, on a request, on a missing `ready`, with a wiped `session/` folder, and with a return
  script that cannot run; One UI's clock caps against a fake sysfs (`--clocks-save` and `--clocks-tops`, the
  switch's two steps run alone: the saved lines, the hardware's range written, then the return after a killed
  xnuhost writes One UI's values back before Gate A, leaves a thermal trip and any line that is not one of the nodes
  alone, and writes no clock without the switch's mark); USB and adb (`--usb-save`, then a return that puts
  `sys.usb.config`, adbd and the UDC file back before `ctl.restart netd`, one that sets nothing when nothing differs
  or there is no record, and `--usb-watch` writing the UDC back on an unbound gadget, adb back into `sys.usb.config`,
  and ending on `returning`: `oneUisUsbIsRecordedAndPutBackBeforeOneUisZygote`,
  `aReturnLeavesAnUnchangedUsbGadgetAlone`, `theUsbWatcherKeepsAdbOnTheGadgetUntilTheReturn`; **not run on this
  branch's box**, which has no JDK 21 or Android SDK: their steps were run by hand there against the same
  `phone-tools.sh`, and OneiOS's stand-in phone, `tools/oneios-tool/tests/phone/usb.sh`, runs these scripts' USB
  steps with unplug, replug, a re-arm and the return); the return in place after SIGTERM and after SIGKILL of tasks in other namespaces,
  with a surfaceflinger that died or outlived the composer; and a reboot for each failed check (a process that
  cannot be killed, a stage mount left anywhere, a mount on One UI's partitions, another vold, another SELinux
  mode, another boot, a zygote that started by itself, a composer, surfaceflinger or audioserver that does not
  come back, no system_server, a user that never unlocks), for a return that hangs (the guard) and for a
  return whose lock holder is gone. These are the scripts' logic, not the phone: `getevent`'s `*` mark, cgroup
  v2, the composer restart and the forced restart are still to be seen on the S24 Ultra.
- **What the phone found** (0.4.81). `OneiosScriptTest`, under each shell: no script redirects `:`, and the
  inner shell's read-only check goes on when the write fails; the trace's last line names the status and the
  step; the inner shell's step lines come before each command of the setup, and the switch waits by its pid;
  with a `tr` that never ends on an unreadable input (as toybox's), a stop loop and an inner shell whose cmdline
  cannot be read do not stall the return, and no script lets `tr` read a `/proc` file itself; an inner shell
  still setting up is ended by its pid; a composer restart that never comes back is a reboot at Gate B's limit
  with the step named, and the limits (90, 45, 75, 45, 290 s) stay under the guard's 600 s. Not in the unit tests, run by
  hand on the PC: the inner shell itself under mksh in a user and mount namespace (`unshare -Urm`, a stand-in
  root with the stage, `chroot`): 0.4.79's script ends there as on the phone (status 1, an empty log,
  `control/busybox` copied, no pid); 0.4.81's traces its fifteen steps and execs the runtime's xnuhost with the
  stage as `/data`.
- **The boot screen.** `OneiosScriptTest`, under each shell: root stages the three files in `bin/` and takes no
  other name; `boot_status.sh`'s `oneos_boot_begin ios` writes the title, the hint and the icon, and its
  supervisor in the `ios` mode starts the renderer with the bound, reads no Android boot event and ends on the
  stop flag; the feeder shows each of the twelve steps from real log lines of a first start (one after a
  megabyte of console) with `progress` (the step of 12, a fraction that never goes back, 1.000 at step 12) and
  `next`, keeps the furthest, passes over the two first-start steps on a later boot (the count goes from 4 to
  7), starts again, bar and all, at a restart in place, shows a panic as printable ASCII with no `next` and then
  why xnuhost ended with "Going back to One UI" and the bar where it stopped, signals nothing and asks nothing
  of init; the hand-off at the helper's first frame and at `ready` with its layer up, and no hand-off for
  `ready` alone, a helper without a frame, or a stale pid; a renderer that never drew is given up; the return
  ends the screen before Gate A in place (and removes the bar), on a failsafe, on the reboot return, for a
  switch that never stopped One UI and from the watcher (with the reason on the screen); a renderer that
  cannot be killed or a stale pid file is logged and One UI still comes back in place; and on the scripts' text:
  it starts after the way back is armed, has no key device, property, signal or reboot in it, and its end cannot
  fail the return. `scripts/test-boot-status.py` and `test-guest-restart-splash.py` (the Android guests' use of
  the same script) pass unchanged. Not covered by any test: the renderer itself (`app_process` and
  surfaceflinger exist only on the phone), so the layout with the hint, and the bar with its step line
  (2026-11-22), have not been seen; the dex is built from the source by `scripts/build-boot-status.sh` (the same
  bytes again from an unchanged source).
- **Hardware checks.** `core/model` `OneiosChecksTest`: the reading of each tool's output (bridgectl's five
  commands, gpuctl, displayctl, brightctl's three, camctl's list and capture with every failure line of its
  README), a missing tool, a tool ended at its limit, root's result lines, the shared text. `OneiosScriptTest`,
  with shell scripts standing in for the tools in a staged runtime: the script's table is the app's (tool,
  arguments, limit per id); a check passes the table's arguments and returns output and exit code; a missing
  tool; a changed tool is not run; no check during a session; the camera's picture comes back intact; **a hung
  tool is ended at the limit, also one that ignores SIGTERM, and the backlight and the sensor are put back**;
  `uncheck` alone puts back once and takes only plain names and numbers from its saved files; the guards on the
  script's text. Not covered by any test: the screen itself, and every tool on the phone.
- **Session logs.** `core/model` `OneiosLogsTest`: the summary of a boot that panics after SpringBoard, of an early
  panic, of a ready session ended by the return's SIGTERM with the watcher's reason from `return.log`; every way a
  session ends; a guest restart in place; the chips and the search; root's list and chunk lines; the returns in
  `return.log` and which one belongs to a log. `OneiosScriptTest`: `logs` lists this session's log, the five newest
  earlier ones and the others with sizes, times and last lines; a 6,000-line log read back in chunks of whole
  lines is the file; a last line with no line break; the 1 MiB limit and the ids, in the launcher and in the script
  itself; a symlink, a hard link or a linked folder in place of a log is never read; nothing in the stage changes;
  the two verbs' text has no write and a time limit on every read; the return's own log, written by the real
  scripts on the fake phone, gives the summary's "Return:" line. `ReadOnlyListsTest`: `logs.oneios` passes the
  read-only audit and names only the log files. Not covered by any test: the two screens.
- **The import.** `core/model` `TransferTest`: the screen hears of the bytes at most four times a second however
  often they are counted, the speed and the time left; reading ahead gives the same bytes in any read size, hands
  an error of its source over where it happened and lets only its own thread close the source; the copy that
  hashes beside the write. `OneiosTest`: a manifest that is the first file is read in the same pass as the files,
  one that is not is found by going on. `core/root` `OneiosImportTest` runs `OneiosImport` through `RootShell`
  (a shell in `su`'s place) against the root script and a fake root, from `.tar.zst` packages made in the test:
  one pass and one opening of the file when the manifest is first, two when it is not; root refusing a file
  whose SHA-256 is not the manifest's with the app's own hash off, and what was staged before left as it was;
  a link, an unlisted file, a cut-off archive, a file that is not a package, a missing file; a large file
  checked by root while the next is sent, and its refusal ending the import; Stop. `OneiosScriptTest`:
  `receive` with three kinds of `dd` (GNU's, a stand-in that refuses `fullblock` like toybox's, one that takes no
  `iflag`) takes a file of several pipe buffers whole, takes no more than it was told, and refuses a short file
  and a wrong SHA-256. Not covered by any test: toybox's own `dd`, the screen, the service and the wakelock.
- **The iOS screens' words and steps** (2026-11-15). `core/model` `OneiosPlainTest`: a refusal of the preflight,
  of root and of the app's download and import in plain words (the title, the line within 40 and 140
  characters, the step it is about, the fix), the preflight's prefix dropped and its words kept for Details, an
  earlier session's xnuhost as a restart and not the runtime, an import's failure naming its package, and the
  app's record of a staged package (encode, decode, shown only for the version root reports). `core/root`
  `OneiosFlowTest`, on the scripts' text and on status lines only (no shell, no tool: it runs as it is on Linux
  and macOS): every `refuse "..."` of `oneios_switch.sh` and of `oneios_root.sh` (but its hardware checks') and
  every `@@REFUSED` of the launcher has plain words of its own; the preflight refuses in the order
  `OneiosFlow.check` reads (this phone and root, the runtime, the image set, the phone's state); the steps,
  checks and next action of a phone with no stage, before root answered, with a runtime alone, ready, refused
  for the battery, with a changed image set, with a placeholder runtime, with a session open, during and after
  an import or a download, after a refused switch and after a check that failed itself; how the last session
  came back. **Not run on the box the redesign was written on** (no JDK 21, no Android SDK); not covered by any
  test: the screens themselves.
- `./gradlew :core:model:test :core:root:testDebugUnitTest`. The app itself needs the SESL9 libraries from
  GitHub Packages (a token in `~/.config/twidget/github.properties`), as before this change.
- **The root script tests on macOS.** The root scripts are written for the phone's tools (toybox, busybox), which
  take GNU's options: `stat -c`, `sha256sum`, `timeout`, `tac`, `sed -i`. macOS's own `stat` is BSD's, which
  refuses `-c`: on the Mac (macOS 27, `oneios-tool cycle --only build --force app` at 4ffd807) the owner check
  (`mine()`: `stat -c '%u %A'`) read nothing, so every stage folder "is not root's folder" (`@@REFUSED`, exit 2)
  and 140 of the 245 `:core:root` tests failed (GuestRuntimeScriptTest, OneiosImportTest, OneiosScriptTest,
  StageScriptTest). Not the owner: under `ONEOS_TEST_ROOT` "root" is the test's own uid, and only the stage
  path itself is checked for a link, so `/var/folders` (and `/var` being a link to `/private/var`) do not
  matter. The fix is in the tests only: `HostTools` (`FakeRoot.kt`) runs
  `core/root/src/test/resources/hosttools/host-tools.sh` once, which writes stand-ins into a folder that the
  harnesses (FakeRoot, OneiosFakeStage, OneiosScriptTest) put on the scripts' PATH after their own stubs, each
  chosen by what the machine's tool does, not by its name: Homebrew's GNU tool (`gstat`, `gsha256sum`,
  `gtimeout`, `gtac`, `gsed`) where there is one, else a translation (`gnu-stat.sh`: GNU's `-c`, `-L` and `-f`
  over BSD's `stat -f`; `shasum -a 256`; perl's alarm for `timeout`; awk for `tac`). With GNU coreutils
  (Linux) the folder stays empty and nothing changes. The harness's own snapshots (`find -printf`, which BSD's
  find has not) go through `listing.sh`. The root scripts are unchanged: on the phone the owner check is the
  same text with the same tools, as strict as before. Checked on Linux only (no JDK 21 here): `gnu-stat.sh`
  over a stand-in for macOS's stat prints what GNU's prints for every format the scripts use (300 checks, under
  bash as sh and zsh as sh); `mine()` of both root scripts refuses a group- or other-writable folder, a link,
  root's file and a missing one with the stand-in as with GNU's stat; `oneos_root.sh` under the BSD stand-in
  alone gives the Mac's refusal, with the stand-in it passes. On the Mac: `cd app-android && ./gradlew
  :core:root:testDebugUnitTest` (or `oneios-tool cycle --only build --force app`); expected 245 tests, 0 failed
  (the 2 skipped as before). If it still fails, the test report's standard error names the stand-ins in use
  (`core:root tests, this machine's stand-ins:`); `brew install coreutils gnu-sed` gives the GNU tools themselves.

- **The second round on the Mac (0.5.14, 143, 2026-11-15).** A few OneiosScriptTest tests still failed with
  `@@REFUSED .../data/local/tmp/oneios is missing or not root's` (the script's own `stage_ok`, not the
  launcher's check that #4 covered), among them `aCheckRunsTheStagedToolAndReportsItsOutputAndExitCode` and
  `theLogVerbsListTheSessionLogsAndReadThemInWholeLines`. All in the tests' environment. Proven from the code:
  `direct()` (#5's test helper that runs `oneios_root.sh` past the launcher) set no PATH, so it got BSD's stat
  without the stand-in. Likely (guesses: the failing lines, OneiosScriptTest.kt:2020 and
  :2175, are the picture's bytes and the return log's tail): the harnesses passed the Mac's UTF-8 locale on, under which BSD's `cut` and `sed` stop at
  the log test's bytes that are no UTF-8, where the phone's root shell (no LANG) reads bytes; and the camera
  check's `base64 FILE`, which an older BSD base64 takes only as `-i FILE`. The fix: `HostTools.env()`/`into()`
  (`FakeRoot.kt`) give every harness PATH and `LC_ALL=C`, `direct()` included, and `host-tools.sh` writes a
  `base64` stand-in where `base64 FILE` does not work. The scripts and their checks are unchanged. Checked on
  Linux only: the stand-ins folder stays empty here, and the `base64` stand-in was tried against a BSD-like
  `base64` that takes only `-i`. Not run on the Mac yet.
- **The third round, from OneiOS's macOS CI (2026-11-15).** OneiOS's workflow runs this fork's `./gradlew test` on
  `macos-15` with Homebrew off PATH (OneiOS's `docs/releases.md`, "macOS: the fork's unit tests"). With the
  second round (PR #7, `479d474`) every module passed up to `:core:root:testDebugUnitTest`, and there 431 tests
  passed (the two skipped as before), the two of the second round among them; then
  `aProcessThatEndsLateAfterSigkillIsWaitedForAtGateA` failed and `aHungToolIsEndedAtTheLimitAndWhatItChangedIsPutBack`
  hung until the job was stopped (OneiOS runs 43710921989; the head of `oneios` without PR #7, run 43710905603,
  failed the two of the second round as well). Both causes are in the tests' stand-ins, proven from the CI's
  log and process list:
  - The fake phone's `now` (`phone-tools.sh`) counted with `date +%s%N`. BSD's date has no `%N`: it printed
    the seconds and a literal `N`, the sum failed, `now` printed nothing, and Gate A's 30 s wait ended at once
    and took the failsafe. `now` now uses perl's clock when `date` prints anything but digits.
  - `oneios_root.sh`'s `check_is_tool` reads `/proc/PID/cmdline` so that a check's time limit ends only the tool
    it started. macOS has no `/proc`: the limit took the hung stand-in tool for gone and never ended it, and the
    test read its output for ever (the process list: `oneios_root.sh check levels` and the stand-in `brightctl
    levels` still running after 25 minutes). `host-tools.sh` now writes a `cat` stand-in where there is no
    `/proc`: `cat /proc/PID/cmdline` prints `ps -p PID -o command=`, everything else goes to the real `cat`.
  The scripts are unchanged; on Linux neither stand-in is used (`date` has `%N`, `/proc` is there). Checked on
  Linux: the `cat` stand-in, forced on, prints a live pid's arguments, fails for a dead one like `cat` of a
  missing file, and passes files and stdin through.
- **The fourth round (2026-11-15).** With the third round the Mac's `:core:root:testDebugUnitTest` ran to its end
  (OneiOS run 43714546247: 270 tests, 4 failed, 2 skipped; the hang was gone):
  - `aProcessThatEndsLateAfterSigkillIsWaitedForAtGateA` still took the failsafe. Its fake clock ran 100 times
    faster, so Gate A's 30 s were 0.3 s of real time, less than one round of kill, sleep and the session's
    listing with the Mac's stand-ins (each a new shell). The test runs its clock 10 times faster instead (3 s).
    `now` also takes perl's clock at once after its first call found no `%N` (a marker in the fake root).
  - `theReturnsLogSaysWhoReturnedAndHow`: every line of the return log was there twice. `oneios_return.sh` writes
    each line once when its stdout is the log itself, told by `[ /proc/$$/fd/1 -ef "$LOG" ]`; macOS has no
    `/proc`. A first try, asking `[ /dev/fd/1 -ef "$LOG" ]` as well, did not help on macOS (OneiOS run
    43717760387: the lines were still doubled) and is not kept. **A script line instead, for tests only:**
    with a test root (`ONEIOS_TEST_ROOT`, never set on the phone) `ONEIOS_TEST_OUT_IS_LOG=1` says it, as
    `ONEIOS_CHECK_LIMIT` is a test's; the test's `watcher()` sets it only where there is no `/proc/self/fd/1`,
    so on Linux the script's own check is still what is tested. On the phone nothing changes.
  - `aChatteringHoldOfTheRockerStillReturns` timed out: the hold of 8 s of the test's clock (1.6 s real) ended
    before the reader's twelve samples did on the Mac. The chatter goes on for 16 s (eight and seven lifts).
  - `StageScriptTest.removeSystemDeletesOnlyTheSystemSetUpNow` ran `find -printf`, which BSD's find has not; it
    uses `HostTools.listing` (`listing.sh`) as the other snapshots do.
  On the Mac (OneiOS run 43717760387, `406f008`): Gate A, the chatter and the `find` test pass; 270 tests, 1 failed
  (the return log, above, fixed after that run). Checked on Linux: `now` with a BSD-like `date` stand-in (perl's
  clock, the marker) and with GNU's.
- **macOS passes (2026-11-15).** OneiOS run 43720242712 (`433cb0c`): `./gradlew test` on `macos-15` (Homebrew off
  PATH) BUILD SUCCESSFUL, core:root's 270 tests with 2 skipped as before. The same run's Linux job had one failure,
  `aReadyGuestIsLeftRunningPastTheDeadline` at its wakelock line: a race of the test (the watcher rewrites the
  node with `echo >` each round, and the test read it once, between the truncation and the write). The test waits
  up to 5 s for the line instead.

## CI: the APK without a personal token

`.github/workflows/oneios-apk.yml`, on every push to `oneios` and by hand (`gh workflow run oneios-apk.yml -R
akshaynexus/OneOS --ref oneios`):

1. Reads tribalfs' SESL9 and oneui-design packages with the run's own `GITHUB_TOKEN` (`permissions: packages:
   read`), passed as `GH_PACKAGES_USER` / `GH_PACKAGES_TOKEN`, which `settings.gradle.kts` already takes. The first
   step tries it on one file and prints GitHub's answer; if that is a refusal, it uses the optional repository
   secret `GH_PACKAGES_TOKEN` (a token with `read:packages`) and says which one it used.
2. Builds the in-guest app (`scripts/build-guest-manager.sh --debug`), runs the unit tests, and builds the normal
   full edition: `:app:assembleFullDebug` with the default `oneos.packSets` (unset). That packs no package set:
   the build records each set file's size and download source from `packages/remote.txt` and `sizes.txt`, and the
   app downloads them by SHA-256. So upstream's `out/overlays*` folders are not needed, and the APK holds no OEM
   file and no image.
3. Uploads `OneOS-oneios-<version>-debug.apk` as an artifact and attaches it to the prerelease `oneios-<version>`
   on the fork, recreated at the built commit each time.

Every run signs with the OneiOS debug key: the secret `ONEIOS_DEBUG_KEYSTORE_B64` (a base64 debug keystore), set
here and on akshaynexus/OneiOS since 2026-11-22. It is the build machine's `secrets/oneios-debug.keystore` in OneiOS, which
OneiOS's `scripts/release/release.sh` signs with too (OneiOS's `docs/releases.md`, "The debug key"). So a build from
either workflow or from that machine installs over the last one. Any debug build in OneiOS's checkout (`./gradlew
assembleFullDebug`, `oneios-tool app build`) signs with it too: `app/build.gradle.kts` takes OneiOS's
`secrets/oneios-debug.keystore` as the debug key when the file is there (2026-11-22), else Android's own. APKs from before the key (OneiOS v0.1.13's 0.5.47
and earlier) were each signed with their run's own key, so the first build signed with it needs one uninstall.
Without the secret, a run signs with a key of its own. The run writes the secret to `~/.android/debug.keystore` and,
since 2026-11-23, also to `$GITHUB_WORKSPACE/../secrets/oneios-debug.keystore`, the path `app/build.gradle.kts` reads
first: Gradle did not take the first one on the runner, so 0.5.51 (`7920fa33…`) and 0.5.52 (`3b377b62…`) were each signed
with a key of their own and could not go over an installed build. "Name the APK" now prints the APK's signer and fails the
run when the secret is set and the signer is not the shared key (`8b3be966…`). The in-guest app is a
debug build too: Android guests that already hold upstream's release-signed one cannot take it as an update.

**OneiOS builds this branch too (2026-11-15).** This fork is the submodule `app/` of akshaynexus/OneiOS
(`branch = oneios`). OneiOS's one workflow, `.github/workflows/release.yml` there, takes the head of `oneios` on
every OneiOS pull request, push to its `main`, tag and dispatch (`git submodule update --init --remote app`), runs
the same steps as this workflow (the token probe, JDK 21, the guest app, mksh, `./gradlew test assembleFullDebug`),
checks the APK for package sets, images and firmware, runs `./gradlew test` on macOS as well, and puts the APK
beside the runtime on OneiOS's releases (the notes name this fork's commit, versionName and versionCode). OneiOS's
`docs/releases.md`, "CI and releases".

**This workflow stays, for this fork's own pushes.** OneiOS's workflow runs only on OneiOS's events: a push to
`oneios` here starts nothing there, so without `oneios-apk.yml` a fork change would be built and tested only at
the next OneiOS pull request or push. The prerelease `oneios-<version>` that this workflow publishes stays what a
push to `oneios` gives at once (`oneios-tool app install --release <version>` installs it). The two do not
interfere: different repositories, runs and releases.

## Not done yet

- **The kernel build has not run on the phone.** `serve prelink` and the KERNEL flow are tested on the PC
  (the tool's own 21 `serve` tests and the 24-of-24 prelink comparison) and the app's side is unit- and
  script-tested, but no phone has built a kernel yet: time and peak RAM on the S24 Ultra are unmeasured (PC:
  2.8 s wall, 678 MB peak RSS on 20 cores, cold). Until a phone run says otherwise the build row says so.
  Standing by for that run: `tests/phone/serve-on-phone.sh prelink` (OneiOS) with the inputs in
  `/data/local/tmp/oneios/work-prelink`.
- **Update the kernel has not run on the phone.** Its download and decode ran on the Linux PC with the real tool
  and Apple's server (12.4 s, 0.1 s, the pinned SHA-256); on the phone unproven are the `fetch` over the phone's own
  network (Wi-Fi or mobile data, KernelSU's `su` reaching Apple's CDN, a pause and resume there), the `im4p` and
  `prelink` time and peak RAM on the S24 Ultra, and root's `kbcache` hashing 78 MB with the phone's `sha256sum`.
- **oneios-tool in the app has not run on the phone** (branch `app-oneios-tool`). Unknown until it does: whether
  KernelSU's `su` from the app runs the staged `bin/oneios-tool` (it runs the checks' tools the same way, also never
  tried); the times of each flow on the phone (OneiOS's `docs/building.md` section 7 has the Mac's steps to measure
  them). **Make iOS image has not run on the phone, and no OneiOS release has a tool with `make-image` yet** (v0.1.12's
  has none: the flow ends with "This runtime can't make the image yet" until a release has one; "Make iOS image (no
  PC)" lists what is unproven). **The import still goes through
  root's `receive`**: the tool's `receive` (`from` a FIFO the app writes, the size and SHA-256 checked as it writes,
  the lines of `image.new.sha256` and `.ids` as root writes them) would replace that for the image set, with the
  app's own hash taken out; it needs a FIFO in the app's folder that root's tool reads (not tried under the phone's
  SELinux), and the app's open of the FIFO must not wait for a tool that refused before it opened it. The
  runtime's import stays root's: it may be what replaces the tool. **Pause, Resume and the `net` event** follow the
  tool's README (branch `tool-download-resume`, "Downloads on a mobile network": `{"cmd":"pause","id":...}`,
  `{"cmd":"resume","id":...}`; `paused`, `resumed`, `net` with `state`, `next`, `text`; an `error` with the id and a code such
  as `not-pausable` for a request that is no download, shown as "The tool says"). Tested against the stand-in only: the
  tool of that branch was not built here. A tool whose `hello` does not list `pause` and `resume` shows no Pause button.
- **The redesigned iOS screens have not been compiled, opened or seen** (2026-11-15): Set up iOS 27, iOS 27's
  page, the Switch confirm and the switching screen were written on a box without JDK 21 or the Android SDK. The
  first build (`./gradlew test assembleFullDebug`) and a click-through on the phone are their first run; real
  screenshots are still to be taken. `status` names no runtime size and no Data store, so the screens use the
  app's own record and the session state ("In the app"); a `status` line for either would be better.
- **The boot screen has not run on the phone** (0.4.80). Unknown until it does: whether `app_process` starts
  the renderer from the iOS stage's `bin/` (the Android guests run it from their own stage, which is tested on
  the Fold8); whether One UI's surfaceflinger keeps showing the layer once system_server is gone (OneOS's
  Verbose boot relies on the same); how the hint and a long reason look on the S24 Ultra's panel. OneiOS's
  `oneos/interface.md` section 8 should name the lines this reads beyond the nine stages: the console's
  `OneiOS Data: first start` and `OneiOS Data: unpacking the seed`, and the display helper's
  `oneios-display: first frame posted`, `oneios-display: layer up` and
  `oneios-display: display projection set to the active mode`.
- **Session logs have not run on the phone.** The two screens were compiled, never opened on a device; the root
  verbs and the parser ran under bash and mksh on the PC against fake stages and OneiOS's PC boot logs. A phone
  session's log may have lines the PC's never had: the summary names only what it finds.
- **Hardware checks have not run on the phone.** Unknown until they do: whether KernelSU's `su` from the app gives
  the tools what adb's root shell gives them (SELinux context, mount namespace); whether `displayctl`'s helper
  starts from the stage (`app_process` with a dex under `/data/local/tmp/oneios/runtime/lib`); whether `pkill -f`
  on this build matches as the put-back step expects; whether the app reads Bluetooth's and adaptive brightness's
  state on One UI 8 without a permission (if not, it reads "off" and the row runs). The screen's layout was
  compiled, not seen.

- **xnuhost has not started on the phone yet** (see "What the first runs on the phone found"). The switch
  starts whatever the runtime package names, by the contract above;
  the booter's own interface on OneiOS's board (`docs/agents.md`) replaces that command line if it differs.
- Nothing past the preflight has run on a phone: the zygote stop without a guest framework, the watchdog feeder,
  the wakelock, and the in-place return are written from OneOS's Android session and need their first run over
  adb with the owner watching. For the way back, that run should check, in this order: `getevent -pl
  /dev/input/event0` with Volume Up held shows `KEY_VOLUMEUP*`; `/sys/fs/cgroup/cgroup.controllers` exists; a
  session returns on the chord; it returns with `kill -9` of xnuhost and with `kill -STOP` of it (the keys
  still work); the composer restart brings One UI's display back; Power + Volume Down restarts into One UI.
- Left undone in the way back (2026-11-10): no return splash after the boot screen ends, so nothing like OneOS's composer hold; no
  "Back to One UI" inside iOS (xnuhost's `XH_HALT_RETURN` is there, nothing in the guest calls it); the watcher
  does not restart a key reader that died (the poll and the other readers cover it); the Bluetooth, camera and
  vibrator HALs are not restarted at the return (OneiOS's bridges are to name the ones that need it); the CI
  step that installs mksh for the script tests has not run yet.
- The display helper xnuhost asks for (a root SurfaceControl layer that shows the frames of
  `session/display.sock`) is not written. When it is, it belongs to the session: started after xnuhost, in its
  cgroup, so that the return ends it with the rest.
- No return splash for iOS (the boot screen ends before the return's gates), no Quick switch.
- Wi-Fi: One UI's supplicant leaves with its framework. Networking in the guest is xnuhost's to solve.
- The image format follows `oneos/interface.md` until OneiOS's `docs/image-format.md` is written.
- The app update, release scripts and the Probe edition know nothing of iOS.
