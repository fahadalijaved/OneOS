# Changelog

New in 0.4.33, untested: the Galaxy Z Fold6 (SM-F956, q6q, the S24 Ultra's
Snapdragon 8 Gen 3) with the Find N6 build and Infinity-X, and the Galaxy A07
(SM-A075, MediaTek MT6789, One UI 9), the first MediaTek phone, with Infinity-X
only. The Galaxy A16 and A17 on One UI 8.5 (Android 16) are not supported yet:
every system here is Android 17.

New in 0.4.49: **the Galaxy S25 Edge, S24 FE, A26, A17 and A16 5G (Exynos, SM-A166U)**, untested,
from their testers' probe reports: every one of them on One UI 9. The S22s, S23 FE, A06, A16 (MediaTek),
A34, M53, E55 and the Tab S10 FE and Tab S11 sent reports too, but are still on One UI 8 or 8.5
(Android 16): every OneOS system is Android 17, so they wait for One UI 9.

New in 0.4.52: **the Galaxy S26 with Exynos (SM-S942B, m1s)**, untested, with the S26+ (Exynos)'s
systems; and Back to One UI no longer restarts the phone when LSPosed is installed.

New in 0.4.55: **Samsung Camera on the S, A and Flip phones is the Galaxy S26 Ultra's own** (it was the
Z Fold8 Ultra's, laid out for a foldable) in ColorOS, the Pixel systems, Infinity-X and Nothing OS,
untested; Pixel, HyperOS and Nothing OS no longer run at 10-15 fps (the panel stayed at 24 Hz);
Infinity-X gets Samsung IMS and the SMS centre fix; and the **Galaxy A16 4G (SM-A165F)**, untested.

New in 0.4.59: **the Galaxy A27, A35 5G and A54 5G**, untested: the A27 (SM-A276, Snapdragon 6 Gen 3)
with the Galaxy A36's systems, the A35 5G and A54 5G (Exynos 1380, One UI 9) with the Galaxy A26's;
and the A16 5G sold as SM-S166V.

New in 0.4.60: **touch works again in the Pixel system on the Galaxy S23, S23+ and S23 Ultra** (the new
double tap to wake left their touch chip in its low-power mode), and the Pixel system no longer drops
back to One UI after a minute on the S23+ and S25 Ultra (an audio restart loop handed the sound over
to One UI's audio service). **VoLTE is on by default** (One UI's calling service, for calls and SMS on
4G-only networks; it can still be turned off in Settings). ColorOS's **lock screen depth effect**
works on every phone; slow first boots on the A07 and A17 are no longer taken for a black screen;
Samsung IMS gets both SIMs when the phone service starts late; a Z Flip's main screen stays lit at
boot. New, untested: **the Galaxy A17 5G (SM-A176) and Z Flip7 FE (SM-F761)**, and ColorOS (Find X9
Ultra IN build) on the Galaxy A07, A17, A16 4G and A16 5G next to Infinity-X.

New in 0.4.61: **SMS arrive in every system** (Samsung's radio held incoming texts until One UI's own
phone app said it was ready; from pull request #58 by vdcoolok), and **VoLTE registers on IPv4 IMS
networks** (the session's network rule sent Samsung IMS's traffic out of the wrong connection). The
**Samsung Camera opens on the Galaxy A phones** (it stopped at launch on settings the S26 Ultra's camera
does not know). **ColorOS starts on the Galaxy A16 5G and A17 5G** (it waited forever for a voice-wake
service these phones do not have). Infinity-X's status bar, quick settings and navigation work on the
Galaxy A36 again; the return to One UI is faster. New, untested: **the Galaxy S24 (Snapdragon, SM-S921)**.

New in 0.4.62: **calls and SMS in HyperOS** with VoLTE on (Xiaomi's own IMS add-on, which needs Xiaomi's
IMS service, is left out of the session, so HyperOS uses Samsung's IMS like the other systems).

New in 0.4.63: **the Galaxy A54 starts** (its sessions died at the first app process: One UI's /mnt was
read-only there, and the guest now has its own), **no more boot failures from factory reset protection**
(the guest's FRP service could stop its own system after a few tries on the A36, A54 and A56), the
**ColorOS lock screen depth effect** (0.4.60 gave its files to the wrong app; OPPO's AI engine from the
Find X9 Ultra's own firmware is in ColorOS too), and the **Samsung Camera on the A56** (its sensor crop).

New in 0.4.93: **root for the guest on the Galaxy S22 series, S23 FE, A25, A33 and A53**, and three more phones:
the **Galaxy S22 with Exynos**, the **Galaxy A16 5G with MediaTek** and the **au Galaxy S23 (SCG19)**.
- With root for the guest switched on, no system got past its logo on these phones: every switch ended in a black
  screen or a return to One UI (reports from a Galaxy A33 on 0.4.85 and 0.4.90 and a Galaxy S22 Ultra with Exynos
  on 0.4.92, all OxygenOS 16; with root for the guest off the same phones start). Their kernel has no overlayfs,
  so guest root puts a copy of the system's top folder in front of the image, with each of the image's folders
  attached inside it. One of them is the image's own folder of system modules (APEX files), and OneOS took it for
  One UI's, which has to be at that place: the list of modules comes from One UI. The guest then looked for One
  UI's modules among the image's, did not find them ("Unable to parse: /system/apex/com.android.bt.apex") and its
  system server stopped at once, again and again. OneOS now checks what the folder at that place is, not only
  that something is attached there, and puts One UI's folder over it. Not tried on the phones of the reports
  yet. **Tap Update on each system's page** to get it: the session scripts changed.
- The Galaxy S22 with Exynos (SM-S901B), now that findings show it on One UI 8.0: OxygenOS 16, as on the Galaxy
  S22+ and S22 Ultra with Exynos, untested on it.
- The Galaxy A16 5G with MediaTek (SM-A166P, One UI 8.5), from findings of 0.4.91: OxygenOS 16, as on the Galaxy
  A07 5G, untested on it. The A16 5G with Exynos and the A16 4G were there already.
- The au Galaxy S23 (SCG19), from findings of a phone on One UI 9.0: it takes the Galaxy S23's systems (ColorOS
  17, Pixel, Infinity X, HyperOS and OriginOS on One UI 9; OxygenOS 16 on One UI 8.0/8.5), untested on it.

New in 0.4.92: **a switch that stood on the "shutting down" splash for good with guest root on**, and the
**au Galaxy S23 Ultra (SCG20)**.
- With root for the guest switched on, the switch could stop behind the splash and never go on; only a forced
  reboot ended it (Galaxy S22 Ultra, OxygenOS 16, 0.4.91: three switches in a row, 15 and 27 minutes). Before each
  start the guest's module cleanup starts a helper and ends it again a moment later. The stop signal could be lost
  in the instant the helper was starting, and the cleanup then waited for it without end; nothing bounded the
  step. On a test phone's own shell the old lines lost 32 of 400 stops in one run, the new ones none of 1,600.
  The helper is now ended by a signal that cannot be lost, and the whole cleanup has 150 seconds: past that it
  is stopped and the switch ends with a message, as for any other failure while preparing. Not tried in a
  switch on the phone of the report yet. **Tap Update on each system's page** to get it: the session scripts
  changed.
- The au Galaxy S23 Ultra (SCG20), from findings of a phone on One UI 9.0 sent the same day: it takes the Galaxy
  S23 Ultra's systems (ColorOS 17, Pixel, Infinity X, HyperOS and OriginOS on One UI 9; OxygenOS 16 on One UI
  8.0/8.5), untested on it. Japanese carrier models have their own model number and device name, so each needs
  its own entry.

New in 0.4.91: **OxygenOS 16 on the Galaxy S23, S23+ and S23 Ultra that are still on One UI 8.0 or 8.5**
(Android 16), untested there. Until now the app told these phones to update One UI first, because all
five of their systems are Android 17. OxygenOS 16 is the one Android 16 system and already runs on the
S22 series and the S23 FE; on One UI 9 the S23s' list is unchanged (OxygenOS 16 is not offered there).
The session scripts and file sets are the ones of 0.4.90: nothing to update on a system's page.

New in 0.4.90: **Bluetooth and USB headphones on the Galaxy A35**, **OxygenOS 16's status bar**, and **ColorOS's
status bar on the Galaxy S24+**. None of the three has run on the phones concerned yet.
- Bluetooth and USB headphones connected and the sound stayed on the phone (Galaxy A35, OxygenOS 16; any phone whose
  vendor audio policy file names no Bluetooth or USB output). An A35 user found the fix and sent it as a script: the
  vendor's own Bluetooth and USB policy files, included in the guest's copy of the policy file. OneOS now does that
  before the guest starts, on phones that are not Qualcomm ones and have the files and their HAL libraries; the
  0.4.85 way (A2DP outputs in the primary module) stays for the rest. `ONEOS_GUEST_APM_BT_MODULE=0` (or `1` for a
  Qualcomm phone) and `ONEOS_GUEST_APM_USB=0` choose by hand.
- OxygenOS 16 laid its status bar out for a camera in the corner on every phone (clock pushed right of the camera
  on 1080 px phones, icons ending at the camera on 1440 px ones). 0.4.81's fix did not reach it: OPPO's SystemUI
  reads the image's own phone's width (1272 px) from a framework resource, not from DisplayManager. The resource now
  gets the guest's display size through an overlay. `ONEOS_GUEST_STABLE_SIZE=0` turns it off.
- ColorOS on a Galaxy S24+ (Exynos) had the clock and all icons in the left half of the status bar. The camera
  position was written for the whole 1440 px panel while the guest ran it at One UI's FHD+ size. The switch now asks
  the guest for its display size as soon as its window manager answers and places the camera for that size; the
  display density and, on Pixel and HyperOS guests, the status bar height follow the same size. Nothing changes where
  the guest runs the whole panel. Every bar-phone session now logs the guest's display size.

New in 0.4.89: **Canadian phones (SM-...W) are no longer refused as a custom ROM**. From the S24 series on, a
stock Canadian phone carries the US carrier model's bootloader and vendor partition under its own firmware (S24 Ultra
SM-S928W: bootloader S928U..., vendor SM-S928U), which OneOS took for One UI ported from another phone (public issue
#128). The Canadian model now counts as the same phone as the US carrier (U) and unlocked (U1) models, with either
bootloader, as U and U1 have counted as one since 0.4.84. One UI ported from another phone and other regions'
firmware are still refused.

New in 0.4.88: **Bluetooth headsets that drop and reconnect every few seconds in ColorOS on the Galaxy A16 4G
(and likely the A15 4G and A07)** (untested). ColorOS's Bluetooth is OPPO's build for Qualcomm chips. When a headset
connects it turns the Bluetooth chip's quality reports on, reads the MediaTek chip's shorter reports past their end,
and the Bluetooth process dies and starts over, again and again. On phones with the Helio G99 (MT6789), ColorOS's
Bluetooth now runs with its own switch for Android's original behaviour, where those reports are read with their
length checked. The switch changes more of ColorOS's Bluetooth than the reports (codecs, remote control), so it is
set on these phones only; ONEOS_GUEST_BT_ORIGIN=0 leaves it off, =1 sets it on any phone.

New in 0.4.87: **double tap to wake on more phones**. On the S24 and S24+ (Exynos), S23 FE, A25, A34 and A35 the
touchscreen answers two of the four writes with an error although it has done its part; OneOS took that for a refusal
and gave double tap up for the session. The S22 Ultra and S23 Ultra, whose touchscreen reports its state with other
numbers, were left out altogether. Both are handled now, and the first write waits until the touchscreen is held
open (without that it was lost on some phones). Double tap needs One UI's own "Double tap to turn on screen" on.
**Always-On Display in ColorOS and OxygenOS on phones other than the Z Fold8** (untested): the system was never told
that the phone has one, so its setting did nothing. It is told now wherever One UI has AOD and the system carries
its AOD app (ONEOS_GUEST_AOD=0 leaves it off). **HyperOS on Exynos phones with the older audio HAL (A16 5G, A35 and
the like): volume stuck at the maximum, no headset, no Bluetooth audio**. HyperOS was handed Samsung's own audio
policy file and rejected it for a Samsung-only microphone type; it gets Samsung's plain file now. **Bluetooth audio
on those phones, in every system** (untested): the plain file has no Bluetooth music output although the audio HAL
plays to one, so the outputs are added the way One UI's own file has them (ONEOS_GUEST_APM_A2DP=0 leaves the file
alone). On the A25, A33 and S23 FE the Bluetooth audio HAL is an older kind the bridge cannot serve: the log says so
now instead of waiting 15 s, and Bluetooth audio does not work there yet. **Mobile data in HyperOS**: HyperOS keeps
its mobile data switch per SIM slot, the other systems per SIM card; OneOS carried One UI's switch over the second
way, which on a phone with the SIM in the first slot switched the empty slot on and left the SIM's off (S25 Ultra:
signal, but no data all session). Both slots are set now, as HyperOS's own switch does. A first HyperOS start still
begins with mobile data off (there are no settings to change yet): turn it on once in its control centre.
**No SIM in Infinity-X on the Galaxy A07 and A15 (and likely the A16 4G and A17)** (untested): the fix of 0.4.74
looked for the phone's older radio service in the vendor's manifest files and did not find it there, so nothing
changed. OneOS now asks the running phone which radio services it has, and the log says what it saw either way.
**For reports:** when a system asks to shut the phone down or restart it, the log now keeps the request from the
system log buffer (a busy camera used to push it out) and what the system's thermal and battery services held;
HyperOS says when it unpacks its apps' libraries on a first start.

New in 0.4.86: **a faster switch and a faster return**, from a contributor's work (public pull request #107):
One UI's display details are read once and in the background, the Samsung Camera's files are bound in parallel
(one by one where the root manager's busybox cannot), app data ownership is checked in one pass, and One UI's
persist properties go back in one pass at the return (the author measured about 21 s down to 10 s for that step).
The log now carries a time at every step. **App folders keep the labels the guest gave them** between sessions:
the rule from 0.4.44 never took effect, because the folders were reset just before it looked. **A live or video
wallpaper survives a restart in ColorOS 17 too**, not only in Pixel guests (public pull request #133).

New in 0.4.85: **Galaxy A phones on One UI 8 or 8.5 are no longer called "not supported"**. Whenever the
app had no set-up system to go by, it measured them against Android 17 and refused them (A15, A16, A25, A33 and the
others with OxygenOS 16). Phones whose systems are all Android 17 (A56, A57, A36, A27, S24 FE,
Z Flip7 FE, S25 FE) now say what to do on One UI 8.5: update One UI first. The device report no longer says "Not
supported" for low free space when a system is already set up. **OxygenOS 16 on the Galaxy A25 and A33** no longer
stays on a black screen (the earlier fixes did not take effect there). **OriginOS 7 on the Galaxy S23 and S24 series**
stopped after a minute on every try: vivo's refresh-rate manager refused all of Samsung's display modes; it is now
switched off on those phones (untested on a real one). OxygenOS and ColorOS get the folder their system font link
lives in, and the logs say more about fonts in web pages (text missing in Google sign-in and some apps on OxygenOS 16
is still open) and about the Galaxy A57's radio library (incoming SMS). Tap Update on the system's page after
installing.

New in 0.4.84: US phones on the other US firmware are no longer refused. A carrier model (SM-...U) and the
unlocked model (SM-...U1) are the same phone and take each other's stock firmware, but 0.4.83 and 0.4.74 called
that "Custom ROM: One UI from another phone" and would not prepare or switch (seen on a Galaxy S26+, SM-S947U1 on
the U firmware). Nothing else changed: coming from 0.4.83 there is nothing to update on a system's page; from an
older version, tap Update there as 0.4.83 asks.

New in 0.4.83: **Bring apps** (experimental): take apps you installed on One UI along into a system, with their data
and logins, so you do not sign in again there. Tick them under Bring apps on the system's page; they are copied when
you start the system, or right away with Bring now, and the system installs them shortly after its home screen shows.
One way: One UI's copy is only read, and nothing comes back to it. An app the system already has is brought again
only when you ask (Only new / All), the boot screen says how many apps come along, and there is Select all and a
reminder when an app is newer on One UI. Tested on the Z Fold8 Ultra with ColorOS 17.
**Cooler systems:** every system now runs its own system code compiled instead of interpreted, the main cause of warm
and slow sessions, and ColorOS uses the display's hardware overlays instead of drawing every frame on the GPU
(confirmed on the Z Fold8 Ultra with ColorOS 17; first runs on the other systems and phones).
**ColorOS:** apps and overlays follow this phone's own corner radius (they were cut for the Find N6's rounder
screen); double tap to wake works from sleep and with the always-on clock; on the Z Fold phones the screen switch at
fold and unfold is quick again on a warm phone. **Uninstalled apps stay gone in ColorOS:** apps you uninstalled or
removed as bloat came back at the next start or after an update, because ColorOS installs every app folder it finds
when it starts. Those folders are now cleared before each start, with the folders of older versions and old install
leftovers, which also gives their space back.
**From the reports of 0.4.72 to 0.4.74** (not yet confirmed on the phones they are for): the OxygenOS 16 black screen
on the Galaxy A25 and A33 (the 0.4.74 fix did not recognise these phones); ColorOS 17 ending with "The other system
stopped" on slower Galaxy A phones; the brightness slider on Galaxy A phones in ColorOS and OxygenOS; the OxygenOS
status bar laid out for a corner camera; "One UI's property space is nearly full" on any system; apps compiled by the
system's own compiler (first starts that stalled on the A36 and Z Fold8); guest root: a module whose installer fails
is turned off instead of ending the switch; the S23 Ultra's Samsung Camera closing at the shutter; two sessions that
Last session wrongly called a restart. **Skip saving logs** now answers at the first tap.
**New phone:** Galaxy S24+ with Exynos (SM-S926B). **OriginOS 7** is now offered on the Snapdragon Galaxy S24 Ultra,
S24, S23, S23+ and S23 Ultra, and, next to ColorOS 17, Pixel 9 Pro XL, Infinity-X, HyperOS and Nothing OS, on the
Exynos Galaxy S24 and S24+ (untested on all of these; OriginOS has not run on an Exynos phone yet). After updating,
tap Update on your system's page. The phone list is in [docs/devices.md](docs/devices.md).

New in 0.4.74: Galaxy A34 5G and A15 on One UI 9 (ColorOS 17, Infinity-X, HyperOS, untested) and the au Galaxy S22
Ultra (SCG14, OxygenOS 16, untested). OxygenOS 16: its NFC app's crash loop (slow, warm phones) is left out; Google
account, Chrome and Gboard on One UI 8.5 phones. Heat after a session (a log search kept a CPU core busy); guest root:
Xposed frameworks can be removed again and a module step that hangs returns to One UI; switching is refused while a
root module has stopped One UI's thermal service; OriginOS on the Z Fold7: a slow first boot is no longer taken for a
failed one. OneOS runs next to stock One UI only: on a ported One UI, a ROM without One UI or a phone that is not a
Samsung it says so and does not switch.

New in 0.4.73: **OriginOS 7** (vivo, Android 17), experimental: a new system for the Snapdragon Galaxy S26, S26+, S26
Ultra, S25, S25+, S25 Ultra, S25 Edge and the Z Fold7, Fold8 and Fold8 Ultra. Tested on the Z Fold8 Ultra (both
screens with their own layouts, brightness, AOD and double tap to wake, calls and SMS, Bluetooth, themes, blur, the
dynamic island once Jovi's atomic notifications are on, Google Play after registering the device at
google.com/android/uncertified); first runs on the other phones.

New in 0.4.72: **Root and modules per system (experimental, by Josh)**: each system can have its own root
permissions, Magisk/KernelSU-style modules and an Xposed framework (Vector bundled, or an imported Zygisk LSPosed),
set up on the system's pre-boot page and managed from the OneOS app inside the system; Restart guest applies module
changes without going back to One UI. Play Integrity does not pass inside the guest yet.

New in 0.4.71: **Stuck at "Check the system already on this phone" / system not found after an update** fixed (setup
steps run one at a time and never under a starting session; Update/Retry no longer re-checks a copy that is gone, it
asks for the download instead). **Phones restarting with "vold-failed"** during a session: One UI's dumpstate and
bugreport stay stopped while the guest runs. **S24 Ultra stuck at the boot screen on every system**: Switch now warns
when Zygisk Next 1.5.2 or older is enabled (update it or turn it off). New phone: Galaxy M55s (OxygenOS 16).

New in 0.4.70: **OxygenOS 16 on the S22 series, S23 FE and other phones with the older kernel** (5.10: both forms of
the system_ext mount were refused, and the guest crashed at startup; it is now built without overlayfs). **Vulkan
drawing on Exynos phones too** (A54, A26, S23 FE stopped where the A34 did). **HyperOS on the MediaTek A07, A16 4G and
A17: SIM** (HyperOS waited for a radio service type these phones do not have; set hyperos r25). Reports now name the
app build that ran the session.

New in 0.4.69: **OxygenOS 16 fixes** (from the first reports): the return to One UI no longer forces a phone restart
(OxygenOS's storage service is now the guest's own, set oxygen16 r2); on the A34 and other MediaTek Galaxies the guest
draws with Vulkan (the GL driver load hung its screen); the S22 Ultra / S23 FE mount fix from 0.4.68 now logs why the
kernel refused. **Skip saving logs**: the log save after a return can be stopped, so switching does not wait for it.

New in 0.4.68: **Fix for phones restarting during a session since 0.4.66** (all systems: the watchdog keeper stopped
right after the switch, and Samsung's software watchdog restarted the phone a few minutes later). After a force
restart the app now offers **Restore now** instead of a "Retry update" that could not go through. New phones: Galaxy
A55 5G, S25 FE, S22 (Snapdragon). OxygenOS 16 shows its own name on the boot screen; S23 FE system_ext mount fix.

New in 0.4.67: **OxygenOS 16 for the phones still on One UI 8.0/8.5** (Android 16; experimental, never run on a
phone yet): the S22+, S22 Ultra, S23 FE, A06, A07 5G, A15, A24, A25, A33, A34, A53 and F55/E55, and the A07, A16,
A17, A26, A35 and A54 while on One UI 8.5. Not on One UI 9. No camera yet. The app now carries an Android version per
image and One UI 8's installd tables.

New in 0.4.66: **HyperOS on the Galaxy A07, A16 4G and 5G, A17 4G and 5G, A26, A35 and A54** (untested), **no restart
on the Galaxy A17 5G** (Samsung's software watchdog on its second watchdog device was never fed, and the phone
restarted about 100 s into every session), and **Samsung Camera on the Galaxy A16 4G** (it closed at launch on a
resolution the camera does not know).

New in 0.4.65: **downloads from SourceForge** (GitHub's downloads were down for hours and Google Drive's
copies ran out: the app now tries SourceForge right after GitHub), **internal storage in every system again**
(since 0.4.63 the systems showed full or no storage: their storage never mounted), **Samsung's Dolby on music
through the speaker**, **the Galaxy A07's screen** in ColorOS (black after boot: its brightness goes through the
panel's LED), and **incoming SMS on the Galaxy S23, S23+ and S23 Ultra** (their radio library is built
differently: the SMS patch did not find its spot).

New in 0.4.64: **video recording and steady sound in the Pixel system** (Pixel's Now Playing made it restart
Samsung's audio service over and over), **volume in HyperOS** on Snapdragon Galaxies (every volume had a
maximum of 0, and apps and the volume slider crashed), and **no false "black screen" on slow first boots**
(the session went back to One UI a second before the home screen appeared).

New in 0.4.40: **the Galaxy S23 Ultra, Z Flip6 and S24 (Exynos)**, untested.
Calls on T-Mobile in ColorOS (Samsung's IMS never registered: it found no GBA
support on the SIM), SMS that the IMS network refuses go out the classic way as
on One UI, and HyperOS's display service no longer crashes in its Dolby renderer
on the S24 Ultra, S23 and A57 (untested on those phones).

New in 0.4.39: **calls and SMS in ColorOS on more carriers.** Samsung's IMS
waited for an "ISIM loaded" signal that only One UI sends (AT&T and other
ISIM carriers never registered), and SMS named the message centre without its
international "+" (the network answered "user unknown"). Also: One UI's camera
lays out right on bar phones, HyperOS skips the start-up step that left the
S23, S24 Ultra and A57 on a black screen (untested on those phones),
ColorOS no longer resets the clock to 1 January (Google said "offline"), and a
Pixel guest keeps its own audio service.

New in 0.4.38: **HyperOS starts on the Galaxy S23, S24 Ultra and Z Flip5**
(Xiaomi's SurfaceFlinger read those screens' display mode groups as a single
byte, found no mode and stopped at the first frame), and **Magisk** works as
the root app (OneOS looked for its prop tool only where KernelSU and APatch
keep theirs). Samsung Camera saves photos on a phone's first session with it.

New in 0.4.37: **the camera in ColorOS and HyperOS.** Every camera app was
refused on the S25, S26 and A phones: ColorOS sent One UI's camera service the
app's screen name instead of its package, and its camera calls were numbered
one off from One UI's. Both fixed in ColorOS (Find X9 Ultra IN and Find N6
builds) and the first in HyperOS. **Samsung Camera in ColorOS** too (the Find X9
Ultra IN build and the Find N6 build on the folds), as in Nothing OS. Bluetooth
audio in ColorOS and Infinity-X on the S25 and A phones (the earbuds connected
and played nothing). ColorOS turns on the features its own build declares and
our container skipped: Live Alerts, smoother app and window animations,
floating windows and Pocket Studio, and on the folds separate wallpapers per
screen. Samsung Camera on bar phones uses the phone's layout (it took the Fold's
cover-screen layout), and runs on the S24 Ultra and Z Fold6 too. Nothing OS
draws the camera cutout as a round hole, not a bar from the top edge. The Z
Fold6 no longer restarts on the way back to One UI.

New in 0.4.36: brightness by your phone's own panel in every system. Each
system's brightness steps came from the Galaxy Z Fold8 Ultra's panel, which is
right on the S26, S25 and S24 phones and the Z Fold6, Fold8 and Flip8, but
gave an A56 or A36 about two thirds, a Z Fold5 or Flip5 a little over half and an S23 under
half of the brightness each step asks for. OneOS now reads your panel's scale
from One UI before the switch. **Nothing OS on more phones**, untested: the
Galaxy S25 Ultra, S25, S25+, S24 Ultra, Z Fold7 and Z Fold6 (it turned out
not to need the newest CPUs). New, untested: the Galaxy Z Fold5 (SM-F946,
Snapdragon 8 Gen 2) with the Find N6 build and Infinity-X.

New in 0.4.35: **Nothing OS 5.0** (Nothing's system from the Phone (3), with
Google apps) on the Galaxy Z Fold8 Ultra, where it was made, and, untested, on
the Z Fold8, S26 Ultra, S26+, S26 and the new Z Flip8: its Glyph ringtones and
sounds, the boot animation on both screens of a Fold, One UI's brightness
range, Essential Space on a double press of the power key, and an About phone
page with your phone's picture, processor, RAM, storage, screens and battery.
**One UI's own camera runs inside Nothing OS** (One UI's camera app, adapted
on our side for a system that is not One UI): photos, both selfie cameras on
a Fold, lens switching, and no 5 s wait at the start. New phones, untested:
the Galaxy Z Flip8 (SM-F776, Exynos 2600) and the Galaxy A36 (SM-A366,
Snapdragon). Fixes: the Pixel 9 Pro XL starts again on every phone but the
Fold8 Ultra (0.4.34's brightness curve stopped it at the boot animation);
the processor is no longer held at a low clock during and after a session
when One UI had capped it before the switch (it stayed slow until power
saving was turned on and off); the screen turns off while charging.
Thanks to Josh for the ColorOS work on the Z Fold8 in this release (smoother
switching and returning, the power key without a 5 s wait, cover screen
spacing, wallpaper and lock screen editor layouts).

New in 0.4.34: sound and the microphone in Infinity-X on the S25 series (its
audio service waited for a One UI extension that is not there during a
session); the Bluetooth audio bridge starts on the phones that need it (0.4.33
checked too early and skipped it); the camera opens without a 5 s wait and a
refusal on the S25 Ultra's firmware; One UI's brightness curve for every
phone's own screen in Pixel and HyperOS; HyperOS's preinstalled apps
(Downloads, Weather, Game Center, WPS) find their libraries.

Also in 0.4.33: Bluetooth audio on the phones whose One UI has only Samsung's
Bluetooth audio HAL (S25, S24, S23, Z Fold7, Z Flip7 and Flip5, A57, A56;
untested there), through a small bridge to Samsung's HAL; Chrome loads pages
again in every system (it is told to use its Java renderers); the camera opens
without Knox's 5 s wait by default; on bar phones the Pixel and Infinity-X
status bar takes One UI's height and corner size.

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
