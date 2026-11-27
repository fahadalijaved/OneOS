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

New in 0.5.19: Nothing OS on the Galaxy S23s, Turn it off that lasts.
- **Nothing OS on the Galaxy S23, S23+ and S23 Ultra**, untested: it **might not boot**. If it does not, the phone
  comes back to One UI by itself; please send a report either way (with Record full logs from now on if it starts).
- **Turn it off keeps the timer app's kernel tool off**, also after a restart: its program file can no longer be
  started while the app is off (until now only uninstalling the app helped). Turning the app back on in OneOS gives
  it back as it was.

New in 0.5.18: fingerprint unlock in Nothing OS, smoother systems, a fresh setup without the account check.
- **Nothing OS: fingerprint unlock with One UI's fingerprints** on Galaxy phones with an in-display (optical) sensor:
  the sensor is in its place, its light comes on under the finger and the screen is bright enough to read it, as
  in One UI. On with Advanced > Switch with a screen lock set. Tested on the Galaxy A36.
- **Every system feels faster after its first start**: all its apps are compiled fully once (a notification shows
  the progress; until now most apps ran uncompiled), and the app watchers in a session cost less.
- **A fresh system no longer asks to verify your Google account** (factory reset protection): each system has its
  own, empty protection record instead of reading One UI's. One UI's own record is never touched.
- **Nothing OS uses the whole brightness range** (its slider stopped at about a third on a Galaxy), and its status
  bar and power key animation are right from the start.
- **Volume Up + Volume Down returns to One UI within seconds** (it could wait half a minute behind the session's
  checks), and the fingerprint sensor's light no longer stays lit on the screen when a system starts.

New in 0.5.17: Record full logs from inside a system, Nothing OS's Essential key on Volume Down.
- **Groundwork for fingerprint unlock with One UI's fingerprints** (off for now: the in-display sensor still needs
  its touch signals from Nothing's lock screen). Nothing OS can never delete a fingerprint from the phone, and Settings no
  longer crashes on Fingerprint. From vdcoolok's work (pull request #152).
- **Switch with a screen lock set** now asks first: a red warning (recent Samsung firmware blocks Download Mode while a
  lock is set; a failed switch can mean a factory reset) and a 5-second wait before it can be turned on.
- **Record full logs from now**, in the OneOS app inside any system (Logs card): full session logs stay off by default
  (they add heat); when something goes wrong, turn this on, make it happen again, go back to One UI and send a report.
- **Nothing OS: double tap to wake with the AOD off too** (it only worked with the AOD on: the panel never reads off).
- **Nothing OS: colour modes and warm/cool work** (Standard and Alive, and the temperature slider): Nothing sent them to
  display hardware a Galaxy does not have; OneOS applies them like Android's own Night Light does.
- **Nothing OS: the screen-off animation closes into the phone's own power button** (it went to
  where a Nothing phone has it).
- **Nothing OS: Volume Down twice opens Essential Space** (the power key's double press is the camera again); its
  first-run page, which waits for a double click of Nothing's own key, is marked done.
- **OxygenOS on the Galaxy A15, A16 and A17: SMS and VoLTE.** One UI's calling service died at every start there (it
  looked for a Samsung Knox provider OxygenOS does not have); OneOS now gives it a stand-in, in OxygenOS only.
- **Bluetooth audio recovery works in every system**: OneOS sent its "resume" request to the audio service by a call
  number that is a different call in some systems (OxygenOS 16: found by a tester's own module); it now asks the system
  itself. The same for the SIM a call uses.
- **OxygenOS: Bluetooth no longer drops out** on phones whose Bluetooth chip sends its own quality reports (Galaxy A17
  and others): the report handler that crashed on them is skipped. Thanks to the A17 tester who found it and built the fix.
- **Galaxy S26 (Exynos): the camera opens and records** in every system: each camera picture waited 5 s for a One UI
  service that is not there in another system (CPU boosts); OneOS answers it now.
- **Galaxy S24: Turn it off really stops the timer app's kernel tool** (it runs as root, so turning the app off left it
  running and the switch was refused again).
- **OriginOS on phones with less room for settings** (S25): it starts again after a restart; when even a fresh restart
  leaves too little room, OneOS says so instead of asking for another restart.
- **Phones list** in the group counts every report again (only the last 10 days hid systems that worked).
- The OneOS app inside a system: its bottom bar has its own background (text no longer runs under it).

New in 0.5.16: Telegram sign-in for reports, OneOS in Russian, a Turn it off button for the S24 kernel tool.
- **Reports come only from members of the OneOS Telegram group.** Send to the OneOS team now asks you to sign in with
  Telegram once (through @OneOSReportsBot: tap Start, then come back). Not in the group, or banned? You get the group's
  link instead. Installing and using OneOS stay open to everyone. Older versions can no longer send reports.
- **OneOS in Russian** (the app and the probe), when your phone's language is Russian.
- **Turn it off, right where the switch stops:** when an app's kernel tool (com.roottimer.app on the Galaxy S24) stops a
  switch, the progress screen now offers Turn it off instead of only OK; before, OK also took the button away from Home.
- **The OneOS website**, by fouadd: https://fahadalijaved.github.io/OneOS/

New in 0.5.15: Nothing OS for the Galaxy A series, Samsung Camera video and slow motion, steadier auto brightness.
- **New: Nothing OS for the Galaxy A series** (untested on most phones): Nothing's system from the Phone (3a), made for
  mid-range chips, on every Galaxy A and M phone with One UI 9 (A07, A15, A16, A17, A26, A27, A34, A35, A36, A54,
  A55, A56, A57, M35). Tried on the Galaxy A36: calls (also over Bluetooth), data, Wi-Fi, camera, Bluetooth music, the
  AOD and double tap all work.
- **Nothing OS on every phone:** the status bar clear of the screen's rounded corners and level with the camera hole;
  a double tap wakes the phone from the AOD; a click for double tap to wake and to sleep; stronger vibration; Nothing's
  own camera (which needs Nothing hardware) hidden, Samsung Camera is the camera; a brightness range for each panel.
- **120 Hz stays 120 Hz:** a system could start while the screen was still in One UI's idle 60 Hz and stay there
  (smooth only every other frame, and warm). OneOS now switches it back.
- **Samsung Camera on the A phones:** video, hyperlapse and slow motion no longer close the camera in LineageOS, and
  slow motion no longer freezes the preview.
- **Auto brightness in LineageOS** no longer jumps between very dim and the panel's full peak.
- **Galaxy S24+ with Snapdragon** (SM-S9260 and others) supported, with the Snapdragon S24's systems.
- **No 90-second wait at the start without a SIM:** the switch waited for a mobile network behind a screen that took
  no touches, and some of you restarted the phone during it.
- **Full session logs are off by default:** they added heat. Turn them on in Settings when something goes wrong.
- A clearer Switch dialog.

New in 0.5.14: smoother Galaxy A phones, Samsung Camera in LineageOS, real user numbers.
- **Smoother on the Galaxy A and M phones:** the systems no longer redraw the whole screen on the graphics chip
  every frame for the rounded corners, and window blur is off by default there (Settings > Developer options >
  "Allow window-level blurs" turns it back on). On the Galaxy A36 in LineageOS: from 238 dropped frames in 30 s to 1.
- **Samsung Camera in LineageOS:** the Galaxy A phones get the Galaxy A36's own camera, the S phones the S26 Ultra's.
  Untested.
- **No more "Update" after every session:** a helper left from the last session made OneOS ask to update the system
  instead of switching.
- **LineageOS shows its own artwork** in the OneOS app inside it (it showed ColorOS).
- **New: Settings > Anonymous usage count** (on by default): once a day a random ID, your phone model, OneOS version and
  the systems you set up, so we can count active phones. No account, number, location or files.

New in 0.5.13: fixes from your reports.
- **Bluetooth audio on the Galaxy S26** (and other Exynos phones) in ColorOS: Samsung's audio driver now hears that
  Bluetooth audio is ready before the earbuds connect, as One UI tells it (0.5.12 told it too late), untested.
- **Screen lock on the Galaxy Z Fold8 in ColorOS:** a PIN, pattern or password set in ColorOS now works there.
- **Touch no longer dies after a second on bar phones** (Galaxy S24+ in LineageOS): OneOS switches the touchscreen
  back on when it finds it off with the screen on.

New in 0.5.12: fixes from your reports.
- **Bluetooth audio on the Galaxy S26** (and other Exynos phones) in ColorOS: Samsung's audio driver kept the sound on
  the speaker because ColorOS never told it Bluetooth audio was ready; OneOS now does, untested.
- **Pixel on the Galaxy S23 Ultra no longer stops after a minute** when the audio driver restarts during its start.

New in 0.5.11: fixes from your reports.
- **Brighter screen on the Galaxy S23, S24 and S25 phones** (base, Plus and Ultra), in every system: they ran at a
  dimmer brightness scale than One UI's.
- **Calls and SMS on OxygenOS** on One UI 8 phones (S22, S23 FE and others): Samsung's VoLTE (IMS) now runs there.
- **Bluetooth audio on the Galaxy A16 4G** (and other MediaTek Galaxy A) in ColorOS: earbuds that connected and
  played nothing should now play, untested.
- **ColorOS no longer restarts its status bar under you** a couple of minutes after starting (it looked like a
  SystemUI crash); the wallpaper AOD setup now waits until the screen is off.
- **Speaker sound on LineageOS** and the other systems: Samsung's Dolby tuning now follows the output music plays on.
- **New: Settings > Full session logs.** Turn it off to stop recording everything a session does (saves storage
  and some heat); reports then carry only the short logs.

New in 0.5.10: fixes from your reports.
- **LineageOS gets its own screen lock**: a PIN, pattern or password set in LineageOS now works there, as in the
  other systems.
- **Bluetooth audio on Exynos phones** (Galaxy S26 and others): earbuds that connected and played nothing now play,
  untested.
- **Kernel tool apps** (S24 phones): when one stops a switch, **Turn it off** disables it for you instead of making
  you uninstall it; the system's page has a row to turn it back on.
- **Reports need a Telegram username** so we can get back to you; the last one you gave is filled in.
- The first ColorOS build for the Find X9 Ultra (IN) is retired: every phone takes the newer 1105 build, and a
  system set up with the old build keeps its apps and data when you move to 1105.

New in 0.5.09: **remove one system or start it fresh**, and a smoother app.
- Long-press a system's card, or tap its ⋮ button: the system you set up now offers **Start fresh** (erases its apps,
  accounts and settings; it stays set up and starts like new) and **Remove** (deletes it and frees its space). A saved
  copy offers **Delete saved**. The system's own page has the same two under **Manage**. One UI, other systems' saved
  copies and your downloaded files are never touched.
- Every delete and remove now shows what it is doing and for how long, then how much space it freed; Hide lets you
  keep using the app meanwhile. Buttons say what is running instead of just going grey.
- Cleaner screens: one card style and spacing per page, arrows on everything you can tap, the menu no longer
  touches the screen edge, long names and release notes fit.
- When a kernel tool app (S24 phones) stops a switch, OneOS now names the app to uninstall instead of "Couldn't
  switch".

New in 0.5.08: fixes from your reports.
- LineageOS now starts on the Galaxy A16 (it went back to One UI after 40 s: the brightness range the system asked
  for began below OneOS's brightness curve).
- No more lost sound for the rest of a session after the other system's audio restarted (S25 Ultra, A34).
- Bluetooth turns on again in ColorOS on the A15, A16 and A07.
- The "Returning to One UI" screen no longer stays on top of a One UI that is already up (S24, S24 FE).

New in 0.5.07: **bring apps from inside the other system**, **remove a brought app**, and LineageOS fixes.
- The OneOS app inside the other system has a new **Bring apps from One UI** screen: it lists your One UI apps
  (as they were when you switched) and brings the one you tap over with its data, while the system runs: no
  restart, you stay signed in. One way, as always: One UI's data is only read.
- In OneOS on One UI, **Bring apps** now has a Remove button for each brought app: it is uninstalled from the other
  system at its next start; One UI keeps it.
- LineageOS: it no longer stops on its first start on some phones (Galaxy S26 Ultra: the screen lock setup now
  carries on without a key One UI's keystore refuses); the boot animation now shows on the Z Fold's cover screen too;
  always-on display and the OneOS version name (Settings, About phone).
- Every system starts lighter: a search of the phone's audio libraries that took a whole CPU core for about three
  minutes at every start now runs once per One UI update.

New in 0.5.06: **LineageOS 24**, a new system, on every phone that offers Infinity-X (the S, Z Fold, Z Flip
and A phones). Experimental, not tried on a phone yet.
- The official LineageOS 24 (Android 17, November 2026 security patch) from the OnePlus 15, with LineageOS's own
  apps. Its own system: its guest data is kept apart from every other system's.
- LineageOS has no Google apps of its own. A session adds One UI's own Play services, Play Store and Google Services
  Framework (the files on your phone, never their data), so you can sign in and use the Play Store. Some banking and
  payment apps may still refuse: OneOS does not fake the device's certification. The launch screen can start it
  without Google, as for ColorOS.
- The switch to OneOS that refused because of an app's kernel tool (0.5.04) now says what to do: uninstall that app.
  Restarting the phone does not help, because the app starts its tool again.

New in 0.5.05: **outgoing calls in ColorOS on US carriers** (Spectrum and others), on the Z Folds and slab phones.
- ColorOS let incoming calls and texts through but dialled every outgoing call the old way (GSM), which LTE-only
  carriers such as Spectrum do not have: the carrier's settings asked for VoLTE "provisioning", and Samsung's IMS
  service, which the systems use, answers that it is not provisioned. ColorOS now calls over IMS as the Pixel system
  does. For the Find N6 system (Z Folds) and the Find X9 Ultra November build. Not tried on a phone yet.
  **Tap Update on the system's page**.

New in 0.5.04: **Bluetooth sound in ColorOS and OxygenOS on the Galaxy S23 series** and **an end to the Galaxy S24 restarts**.
- On the S23, S23+ and S23 Ultra, ColorOS and OxygenOS read the phone's own audio settings from a second place and
  never saw OneOS's Bluetooth changes, so headphones connected without sound (0.4.97 to 0.5.03). They now get the
  same settings the Pixel system plays with on the S23. Not tried on a phone yet. **Tap Update on the system's page**.
- The Galaxy S24 restarts during sessions came from a third-party app's tool that works on the kernel (it runs as
  "libtimer.so"), not from OneOS or the systems: 0.5.03's note caught it. OneOS now stops before switching while
  that tool runs and says which app it is: close it, or restart the phone without starting it, and switch again.

New in 0.5.03: **a clue for the Galaxy S24 restarts**.
- Some Galaxy S24, S24+, S24 FE and S24 Ultra phones restart by themselves during a session (10 reports, in
  ColorOS, OriginOS and the Pixel 9 Pro XL system): the phone's kernel stops while a program closes. Sessions now
  note which program that is, so the next report can show us. If your S24 restarts on its own, send a report
  from the app after it comes back.

New in 0.5.02: **a newer ColorOS build for the slab phones (Find X9 Ultra IN, November update)**, to try.
- OPPO's newer global build of ColorOS 17 for the Find X9 Ultra, with OPPO's latest bug fixes (security patch
  November 2026). It shows as a second choice, "global build, November update", next to the current one on every
  phone that has the Find X9 Ultra build; the current build stays the default and keeps working.
- Your ColorOS stays as it is when you move to it: apps, accounts and settings come along.
- **Untested**: nobody has started it on a phone yet. Please try it and send a report, whether it works or not.

New in 0.5.01: **calls end again when you decline or hang up**, in every system that uses Samsung's
calling service (not OxygenOS).
- Samsung's calling service ended the call on the network, but kept the news from the system until the
  system said it was ready for it, which only One UI does. The call went on showing in the Phone app and
  no other call could be made (Z Fold8 with the Pixel 11 Fold build). Now the system says so as soon as it
  takes the call. Not tried on a phone yet. **Tap Update on the system's page**.

New in 0.5.00: **Bluetooth sound on the Galaxy S23 series, third try**, in every system.
- 0.4.99's bridge now reaches Samsung's Bluetooth audio service, but the systems asked for the DSP ("offload")
  path, which the S23's audio driver never connects for them: S23 and S23+ reports on 0.4.99 still had no sound,
  in ColorOS and in the Pixel system. One UI plays Bluetooth headphones the other way, encoding the sound itself,
  and every system now does the same on the S23s. The S24s, where Bluetooth sound works, stay as they are.
  Not tried on a phone yet. **Tap Update on the system's page**.
- **No more black screen on a system's first start when One UI has a screen lock and a Google account**
  (A34 ColorOS report): the new system could not clear factory-reset protection, which stays One UI's, and its
  lock-screen setup stopped the system at the first start. Every system now carries on. Not tried on a phone yet.

New in 0.4.99: **Bluetooth sound on the Snapdragon Galaxies, second try**.
- 0.4.97's fix did not work: Galaxy S23 reports on 0.4.97 still had no sound in Bluetooth headphones. The bridge
  was meant to notice when Samsung's audio service took its place and take it back, but it never noticed. Now
  it simply takes its place again every second. Not tried on a phone yet. **Tap Update on the system's page**.

New in 0.4.98: **always-on display in ColorOS on the Z Fold7, Fold6 and Fold5**, and **AOD brightness in
ColorOS on the other phones**.
- ColorOS on the older Folds (the Find N6 system) had no always-on display at all: only the Z Fold8s had it.
  Now the Fold7, Fold6 and Fold5 get it too, with the wallpaper AOD style from 0.4.97 (report on a Z Fold7).
- ColorOS sets the always-on display's brightness through OPPO's own display hardware, which a Galaxy
  lacks. The Z Fold8s had a fix for that; the other phones on ColorOS (the Find X9 Ultra system) get it now.
- Not tried on those phones yet: if the AOD stays black or missing, please send a report. **Tap Update on the
  system's page** to get it.

New in 0.4.97: **Bluetooth sound in the guest on the Snapdragon Galaxies** and **wallpaper AOD in ColorOS**.
- On the Galaxy S23, S24, S25 and the Z Folds, Bluetooth headphones connected in the guest but every sound stayed
  on the phone's speaker (a Galaxy S23 on ColorOS). Samsung's audio service put Qualcomm's own Bluetooth audio
  entry over OneOS's bridge a minute into the session, and Samsung's audio path never plays through that one.
  The bridge now takes its place back.
- ColorOS (the Find N6 system on the Z Folds, the Find X9 Ultra system on the other phones) can now show the
  wallpaper on the always-on display. ColorOS only offered it when OPPO's own display hardware said so; One UI
  already shows the wallpaper on AOD on these screens. Choose it in ColorOS's always-on display settings.
- Wallpaper AOD was tried on the Z Fold8 Ultra and works; on the other phones it was not tried yet. The
  Bluetooth fix was not tried on a phone yet. If either does not work, please send a report. **Tap Update on
  the system's page** to get both.

New in 0.4.96: **a switch that could not start no longer stays on "Shutting down One UI"**, and **Restart
guest that ended in One UI on slower phones** (root for the guest).
- Right before it changes anything, the switch checks the phone once more and can still refuse to start. The
  app did not hear about that: its screen stayed on "Shutting down One UI" while One UI kept running, and the
  reason was only in the log (a Galaxy S23 on 0.4.95, twice: after several switches without a restart One UI
  had run out of room for settings). Now the app waits for that check and shows the reason. For this one it
  says "Restart your phone first".
- With root for the guest on, Restart guest (the step that applies a module change) stops the guest's processes
  and starts the system again. Finding the guest's processes took about 50 seconds a round on a Galaxy A34, the
  restart ran into its two-minute limit, and the phone went back to One UI instead, twice in a row (a report on
  0.4.93). Now each round reads all processes in one go and looks closely only at those that can be the guest's;
  what gets stopped is decided exactly as before.
- Neither fix was tried on a phone yet: if a switch still stays on "Shutting down One UI", or Restart guest
  still ends in One UI, send a report.
- **Tap Update on each system's page** to get both.

New in 0.4.95: **a screen lock of the guest's own** (a PIN, a pattern or a password) in ColorOS, HyperOS, Nothing OS
and OriginOS, and two more phones: the **Galaxy M35 5G** and the **Galaxy A15 5G with MediaTek**.
- Until now a guest system refused every screen lock: it shares the phone's lock hardware with One UI, and a lock
  set from a guest once left One UI unable to unlock. Now these systems take a PIN, pattern or password in their
  own Settings, as on any phone. OneOS keeps it inside the guest (a salted hash in the guest's own data) and
  checks it there; nothing of it reaches the phone's lock hardware or keystore, and One UI's lock state stays
  exactly what it was. The idea comes from pull request #152 by @vdcoolok.
- What it is not: it keeps other people out of the guest's lock screen, it does not protect the data. A restart
  of the phone always lands in One UI, which has no lock while OneOS is in use, and with root there the guest's
  files are within reach. No fingerprint or face: "Add fingerprint" in the guest refuses. An app that asks for
  the device PIN in its own prompt behaves as on a phone without a lock. One UI's own lock still has to be off
  before a switch.
- Forgotten: from One UI, with root, `su -c 'rm -f /data/local/tmp/oneos/data/system/oneos_guest_lock /data/local/tmp/oneos/data/system/oneos_guest_lock.tries'`;
  the guest starts without a lock the next time (docs/guest-screen-lock.md).
- Where: ColorOS on the Galaxy Z Fold8 Ultra, Z Fold7, Z Fold6 and Z Fold5 (tried on the Z Fold8 Ultra: set,
  unlock, back to One UI, all good), ColorOS on the bar phones (the Find X9 Ultra build), HyperOS, Nothing OS
  and OriginOS. The last four have the same change but have not run on a phone yet: if such a system does not
  start after its update, send a report. Not yet: the Pixel systems, Infinity-X, OxygenOS 16 and ColorOS on the
  Galaxy Z Fold8; they refuse a lock as before. **Tap Update on the system's page** to get it.
- The Galaxy M35 5G (SM-M356B, Exynos 1380, One UI 9.0), from findings of 2026-11-11: the Galaxy A35 5G's
  systems (ColorOS 17, Infinity-X, HyperOS, OxygenOS 16), untested on it.
- The Galaxy A15 5G with MediaTek (SM-A156M, One UI 8.5), from findings of the same day: OxygenOS 16, as on the
  Galaxy A07 5G, untested on it. The Galaxy A15 with the Helio G99 was there already.

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

New in 0.5.20: Share my files, fingerprint and Samsung Camera in ColorOS on the Galaxy A36.
- **Share my files** (Settings, off by default): One UI's photos, downloads, documents, videos and music inside the
  other system; its apps can change and delete them, as in One UI.
- **ColorOS (Find X9 Ultra IN, November)**: fingerprint unlock with One UI's fingerprints, and Samsung Camera on the
  Galaxy A and M phones (the A36's own camera, built for ColorOS), untested.
- **ColorOS on the Galaxy A36**: the lock screen fingerprint icon comes back after every unlock; Always-On Display
  shows again when you pick the phone up; the Updater stays for its About phone banner but cannot download; no lag
  from a warm phone (ColorOS no longer sees "severe" heat at 45 °C). Full-screen wallpaper AOD is work in progress
  (it flickers); the normal AOD works.
- **A session ended by powering off** inside the other system counts as a clean return (a boot-safety module sent
  the phone to Download Mode at every start afterwards).
- **The "optimizing apps" notification** shows again.
- **Smoother in every system:** Samsung's touch booster is on during a session, as in One UI.
- **Record full logs** keeps recording for the whole session (some full reports were cut to 1 MB).
- Switching to a system you already set up needs 2 GB free instead of 11 GB, and the message says how much is
  missing (issue #265).
- An update whose notes are long no longer stops the in-app update (issue #210).
- You can start a session below 30 % battery while the phone is on its charger.
- Smoother sessions: old log readers from earlier sessions no longer pile up.
- Back to One UI from the OneOS app inside the other system goes only after you confirm it.
- Galaxy S23 Ultra: touch works again after a double tap wakes the other system (thanks corexo).
- Other systems on MediaTek phones (Galaxy A15): Bluetooth audio recovery, sound after a soft reboot, screen refresh rate, brightness, camera list and lock screen fixes (thanks helixoff).
- Root inside the other system can be given to uid 0, 1000 and 2000 (thanks thatjoshguy67).
- Website badge in the README (thanks to the website contributors).
- Galaxy Z Fold8: patch channels from a contributor are found automatically (never selected for you); Pixel fold fixes and equal Settings panes for LineageOS and Infinity-X follow with the next system sets (thanks thatjoshguy67).
- Galaxy S24+ (and other phones whose firmware has One UI's Bluetooth-offload audio file): volume steps work in Nothing OS, LineageOS and HyperOS; sound played at full volume at any setting, untested.

New in 0.5.21: sound, videos and updates.
- **Louder, clearer speaker** in the other systems on Galaxy phones: Samsung's Dolby and the speaker amplifier's
  temperature are set as One UI sets them.
- **Videos from Samsung Camera play upright** on the Galaxy A phones in ColorOS, Nothing OS and LineageOS (they had
  no rotation and showed sideways).
- **Updating a system you already use** needs room for the update only, not for a new setup (ColorOS asked for
  27.4 GB).

New in 0.5.22: **One UI 9.5 on One UI 9 Galaxies.**
- **One UI 9.5 (the Galaxy S26 Ultra's, S948BXXU6ZZKN) as a OneOS system** for every Galaxy on One UI 9,
  months before Samsung sends it to most of them. Tested on the Galaxy A36: it boots, runs fast, Wi-Fi
  with internet, apps brought with their data (Add apps). It comes with One UI 9.5's software features
  (Color Lens, the AI erasers and document scan, desktop windowing) on top of the phone's own hardware
  features, and the phone shows as a Galaxy S26 Ultra in it (Galaxy Store then offers Live Effect).
  Your One UI stays as it is.
  **Untested yet:** every other Galaxy (it should work on the S25, S24 and S23 series, the Folds and Flips
  and the A series on One UI 9), the camera (fixed for the A36, not confirmed), calls with the S26 Ultra
  model name, Live Effect and the AI features on phones without the S26 Ultra's NPU. Please send a report
  from the app if something does not work.
- **App optimizing after the first start is gone** for every system: it made phones warm and slow for a
  long time and gave no visible gain.
- **ColorOS on the Galaxy S24 Ultra and other QHD phones:** the fingerprint icon sits on the sensor again (it was
  drawn near the top of the screen).
- **Add apps from inside the other system** works again ("not an installed user app" for every app).

New in 0.5.23: **One UI 9.5 test fix for heat and calls.**
- **One UI 9.5 no longer overheats from a calling crash loop.** Started from the app, it got One UI 9's Samsung
  calling files on top of its own; its calling service then crashed hundreds of times (A56: 260 in 10 minutes),
  kept three cores busy and the phone throttled (choppy sound, "IMS services keeps stopping", no calls or SMS).
  One UI 9.5 now keeps its own. Untested with a SIM: please report calls, SMS and heat.
- **Privacy Display is off in One UI 9.5** (set r2): it is the Galaxy S26 Ultra's own panel feature, and One UI 9.5
  had it switched on for every phone.
- Phones stuck in the setup wizard or with "keeps stopping" messages: the calling crash loop above kept the system
  too busy; please report if setup still does not finish.
- **The One UI 9.5 card** shows "One UI 9.5" above the Set up button.

New in 0.5.24: **reports go to Telegram.**
- **Send report posts to the private OneOSReports Telegram group:** tap Post to OneOSReports, pick the group in Telegram,
  send. Join it once from the Send screen; members of the OneOS group are let in automatically. The bot checks
  membership, files the report and shows it as one card with its summary. Nothing in the app can be abused any more:
  no keys, no upload service (the old one was flooded and is switched off; older OneOS versions can no longer send).
- **Fingerprint: set it up in One UI, not in the other system.** OneOS uses the fingerprints saved in One UI.

New in 0.5.25: **One UI 9.5 fixes from your reports, and fixes for every system.**
- **One UI 9.5: SystemUI no longer crashes every few seconds** (set r4). The Privacy Display switch-off in 0.5.23
  left SystemUI asking for a Privacy Display list the system no longer had; it now gets an empty one (A16, A17, S23,
  S23 Ultra reports).
- **One UI 9.5 on the Galaxy S23, S23+ and S23 Ultra: setup and "System isn't responding"** no longer wait forever
  for a Samsung service those phones do not have. Untested on an S23: please report setup and Bluetooth (Bluetooth may
  still not turn on there).
- **One UI 9.5 black screen on some Galaxy A36 phones** (the screen stayed black and OneOS returned after 30 s) fixed.
- **One UI 9.5 on slow first boots** (A17): OneOS no longer returns to One UI while the setup screen is still coming up.
- **Galaxy S23 family, every system:** after Back to One UI the phone could restart by itself a minute later
  ("rollback"): One UI's 32-bit system process was crash-looping during the session. Fixed.
- **Every system:** a forced restart could block every later start ("Performance limit snapshot failed"); fixed.
  Back to One UI no longer restarts the phone when a Samsung Camera library was left in use.
- **Exynos phones:** video recording in the other system uses the phone's hardware encoder (the rear camera froze
  after 2 s and could not save on the A56 with Nothing OS). Untested: please report video recording.
- **Galaxy Z Fold7:** One UI 9.5 no longer runs at a tablet-sized tiny layout (both screens at 213 dpi).
- Session logs now show the real session time.
- Returning from One UI 9.5 still restarts the phone (being worked on).

New in 0.5.26: **One UI 9.5 no longer stops after a few minutes.**
- **One UI 9.5's system stopped by itself 1 to 6 minutes in** on many phones (S23, S23 Ultra, A26 reports), and OneOS
  returned to One UI: one more place in the system still expected the Privacy Display part that 0.5.23 switched off
  (set r5). Please report how long One UI 9.5 now runs.

New in 0.5.27: **HyperOS 4 Global**, and One UI 9.5 no longer stuck in setup on the S23s.
- **HyperOS 4 Global** (Xiaomi's global build OS4.0.5.0.XFRMIXM, with Google apps and Xiaomi's region apps), on every
  phone that has the older HyperOS. Tested on the Galaxy A36: setup with Wi-Fi, HyperOS blur and visual effects,
  Themes / Personalization, Xiaomi Dialer and Messages, the status bar and Dynamic Island around the camera hole,
  rounded corners, the in-display fingerprint (lock screen at normal brightness), Samsung Camera (opens in about a
  second), Gallery, the screen recorder, and Back to One UI without a restart. The first minutes after the first
  boot are slow while Google updates Play services.
- **One UI 9.5 on the Galaxy S23, S23+ and S23 Ultra stayed on the setup screen** (and could stop after about two
  minutes): a Samsung security service these phones do not have was waited for forever at the end of boot. It now
  goes on without it (set r6).
- **One UI 9.5 could not start on some phones** ("Unable to load SELinux MMAC policy": A07, S23, Z Fold8): a part of
  the phone's own app permissions file One UI 9.5 ignores stopped the whole system. It is now skipped (set r6).

New in 0.5.28: **Galaxy S26 phones updated to One UI 9.5 can switch**, the **Galaxy S26 FE**, and the One UI 9.5 camera.
- **S26 phones on One UI 9.5 firmware** (S948BXXU6ZZKN and its regional builds): One UI 9.5 renumbered the phone's
  app installer service (installd) and Samsung's network service (IOemNetd), so the app refused to switch ("installd
  interface differs"). Every system's files now read the phone's own numbers when the system starts, on One UI 9.0
  and 9.5 alike (all sets have a new revision; only the guard jar changed). Untested on a One UI 9.5 phone.
- **Galaxy S26 FE** (SM-S741, Exynos 2500): the Galaxy Z Flip7's systems, untested.
- **One UI 9.5's camera**: it crashed on the Galaxy S23 ("There is no capability for : 54", the S26 Ultra's second
  telephoto) and did not open on the Galaxy A17 (a picture size the S26 Ultra's camera app does not know). The camera
  now gets only the phone's own lenses and sizes.
- **"Not enough room for this system"** (Galaxy S25+): the app lost track of the sessions run since the phone last
  started and told it to pick another system "even after a restart". It now asks for the restart that frees the room.
- **Probe**: Exynos and MediaTek phones OneOS has already run on no longer read "Chip not recognised" or "first runs",
  and the systems testers ran on their phones (HyperOS 4 Global, One UI 9.5, ColorOS, Nothing OS) are marked tested.
- **Full session logs on the Galaxy S24 FE and S24+**: the log recording stopped the moment it started, so their reports
  had no log; it now starts again on the standard logs.
- Reports: the Probe's findings zip is accepted in the reports group again, and session logs carry the phone's video
  encoders (for the Exynos video recording crash).

New in 0.5.29: **Galaxy S24 phones can switch again.**
- **OneOS now stops the timer app's kernel tool itself** before every switch, and again if it starts during a session.
  Since 0.5.24 the S24, S24+ and S24 Ultra refused every system while the tool ran, also after the app was
  uninstalled (the tool kept running from its deleted file until a restart, where Turn it off did not see it). The
  switch is refused only if the tool survives being stopped; then a restart helps.
- **Full session logs on phones with another "logcat" program** (Galaxy S24 FE: a tool on the phone answered in
  logcat's place, so the log stayed empty and some of OneOS's own checks saw nothing): OneOS now uses Android's own
  logcat for the session.

New in 0.5.30: **the OneOS app and Back to One UI inside One UI 9.5.**
- One UI 9.5 never installed the OneOS app (its package manager does not look where OneOS puts it), so the only way
  back was Volume Up + Volume Down. The app now goes where One UI 9.5 finds it, as on vivo's OriginOS.

New in 0.5.31: **fast charging shown in every system, HyperOS's super charging, Bring apps during a session, and a
battery drain fixed.**
- **Fast charging** on a Galaxy's Super Fast (PPS) and Fast (AFC, QC 2.0, PD) chargers now shows as fast charging in
  every system ("Charging rapidly" and the systems' own fast-charging screens): the Galaxy reports no charger power,
  so every system took them for slow chargers. **HyperOS** shows its super charging (Super Fast) and quick charging.
  Every system's files have a new revision.
- **Faster charging while you use the phone:** with the charger in and the screen on, OneOS now holds the CPU back a
  little when Samsung's fast charger gets hot (from 44 C), as One UI does. Without it the A36 charged at a fraction
  of its speed in use (the charger at 47-52 C).
- **HyperOS battery drain** with the screen off (20 % in 2 hours, almost no deep sleep): Xiaomi Find Device, which
  works only with Xiaomi's own phones and servers, held the phone awake for hours. It is left out now.
- **Bring apps during a session** said "not an installed user app" for every One UI app: OneOS now reads One UI's
  apps through a read-only view the other system cannot see.
- **Full session logs on phones where a root tool covers Android's logcat** (Galaxy S24 FE): OneOS now runs
  Android's own logcat from underneath it.
- **HyperOS status bar in light apps** (white icons on white, as in Settings): HyperOS sent an app's bar colours to
  a per-app status bar only it draws; they now go to the screen's status bar, as on any Android. The Dynamic Island
  stays.
- **HyperOS status bar icon spacing and the rounded app open/close animations** were lost with this version's new
  HyperOS files: HyperOS started its status bar and home screen before OneOS's sizes were on. Both now restart once
  when that happens.

New in 0.5.51: **smoother sessions with full logs, S26 black screen, ColorOS fingerprint wave.**
- **Less heat and lag with full logs on**: full session logs record the first 10 minutes of a session, then stop;
  **Record full logs from now** in the other system's OneOS app records until the return. With Full session logs off,
  the background CPU sampler and sound log are skipped too.
- **Galaxy S26 series: black screen fixed** on PixelOS and the other systems that got the 0.5.49 camera change (testing).
- **ColorOS 17 fingerprint wave on ultrasonic sensors** (S25 Ultra and others), vdcoolok's work from pull request #152:
  the icon at once at the wake, the wave over home after the unlock, no dark dim layer in the unlock (testing).
- **Samsung Camera on the Galaxy S22 series, S23 FE, A25, A33 and A53** in the other systems: their kernel refused the
  layer that adds it, so it never installed (testing).
- Snapdragon phones (S24 Ultra): no sound for the rest of a session after Hey Google crashed the audio DSP; OneOS now
  turns Hey Google listening off when it happens (testing).
- Galaxy S22 Ultra (Exynos), One UI 9.5: the voice wake-up guard runs at every start (testing).
- New phone: the au Galaxy S25 (SCG31), with the Galaxy S25's systems (untested).
- OriginOS camera on the Z Fold5, HeyTap store stopped in the background on ColorOS and OxygenOS, a power-off request
  with the screen off returns to One UI, and apps reinstalled after Bring apps no longer crash (testing).

New in 0.5.50: **S22 Ultra (Exynos) One UI 9.5 setup, OriginOS camera on the Z Fold5.**
- **Galaxy S22 Ultra (Exynos) with One UI 9.5 now starts** (the 0.5.49 fix worked), and no longer restarts the
  phone during setup: Google's "Hey Google" crashed the Exynos 2200 voice wake-up chip until the whole phone reset.
  On that chip OneOS now turns voice wake-up off (Hey Google and Bixby) before it can load (testing).
- **OriginOS camera on the Z Fold5** and other folds: vivo's camera opened a fold screen its build doesn't have and
  closed at once. It now opens with its normal layout (testing).
- Galaxy S23 FE on One UI 8.5: the session logs record what the One UI 9.5 camera fix still needs.

New in 0.5.49: **S26 series camera with every non-Samsung system, ColorOS and OriginOS notification sounds, S22 Ultra (Exynos) One UI 9.5.**
- **Camera on One UI 9.5 phones (S26 series) with HyperOS, PixelOS, Pixel, LineageOS, Infinity-X, Nothing OS,
  ColorOS and OriginOS**: One UI 9.5 added a field to every camera request and OneOS sent the old one, so the camera
  failed and HyperOS on the S26 Ultra stopped 7 seconds after starting (testing).
- **ColorOS notification, ringtone and alarm sounds** (Z Fold5, S23 and others): every sound waited 10 seconds for an
  OPPO service a Samsung phone does not have, and notifications gave up before they played. OneOS now stands in
  for it (testing).
- **OriginOS notification sound**: OriginOS looked for One UI's sound files, which it does not have, so no default
  sound was set. It now uses its own (testing).
- **Galaxy S22 Ultra (Exynos) with One UI 9.5** should now start: its kernel refused the network program because
  of root's small locked-memory limit, which OneOS now raises like Android's own loader (testing).
- Session logs no longer show an earlier restart as the way the session ended.

New in 0.5.48: **One UI 9.5 on every Galaxy Tab, the Galaxy Tab S11 Ultra, Z Fold8 (US) first setup, S25 Ultra restarts.**
- **One UI 9.5 on every Galaxy Tab** we support (Tab S9, S9 Ultra, S9 FE+, S10 FE 5G and Wi-Fi, S11, S12 Ultra), next
  to the tablet ColorOS/OxygenOS 17, each keeping its own tablet model (testing; the LCD and camera fixes are the
  Tab S9 FE's only so far).
- **Galaxy Tab S11 Ultra (SM-X930)** with the tablet ColorOS/OxygenOS 17 and One UI 9.5 (testing).
- **One UI 9.5 first setup on US carrier phones** (Z Fold8 SM-F971U and others): Samsung's setup went on to a US
  carrier activation step the image does not have and stopped there ("Settings has stopped"). OneOS now finishes the
  setup at the home screen when that happens; add your accounts afterwards in Settings › Accounts (testing).
- **Galaxy S25 Ultra with One UI 9.5: Bixby is turned off** for now. Setting up Bixby voice wake-up froze the whole
  phone and the chip's watchdog restarted it (testing).

New in 0.5.47: **S22 Ultra (Exynos) restart loop, Galaxy A17 freezes, Galaxy Tab S9 FE 5G, OriginOS on the Z Fold5.**
- **Galaxy S22 Ultra (Exynos) with One UI 9.5 no longer restarts the phone again and again** (testing). Its kernel
  refused a small network program One UI 9.5 needs, so the system never finished starting and Samsung's boot checker
  restarted the phone. OneOS now tries two more ways to make it; if the phone still refuses, OneOS stops before
  starting and returns to One UI once, with a message, instead of the restart loop.
- **Galaxy A17 (MediaTek) with One UI 9.5: apps such as Telegram no longer freeze** (testing). Loading the "Hey Google"
  voice model crashed the phone's audio chip about once a minute, and apps waiting for sound stopped responding.
  OneOS now turns off Hey Google's always-listening mode when that happens, as it already did on Exynos phones.
- **Galaxy Tab S9 FE 5G (SM-X516B/N)** with OxygenOS 17 Pad and One UI 9.5, like the Wi-Fi model (testing).
- **Galaxy Z Fold5: OriginOS 7** too, as on the Z Flip5 (testing).

New in 0.5.46: **Send to the OneOS team is back, Galaxy Tab fixes, Galaxy Tab S9 FE, OriginOS on the Z Flip5.**
- **Send to the OneOS team** shows again in Last session and Session logs. It was hidden in every build since 0.5.24,
  so only Share and Save were there. On Session logs, the "Send the logs to the OneOS team" line now opens it too.
- **Galaxy Tabs: ColorOS no longer powers the tablet off** after 13-30 minutes. ColorOS's setup app has an alarm
  that powers the device off while its pages wait; OneOS turns that alarm off (testing).
- **Galaxy Tabs: "The data in the stage is another system's"** after the first session is fixed. ColorOS 17 on
  tablets skips one OnePlus app, so OneOS took its own data for another system's and refused every update.
- **Galaxy Tab S9 FE (SM-X510)** with OxygenOS 17 Pad and One UI 9.5, from pull request #371 by asarr22 (testing).
- **Galaxy Z Flip5: OriginOS 7** too, as on the S23s with the same chip (testing).

New in 0.5.45: **Camera for One UI 9.5 on One UI 8.5 phones, the Z Fold8 starts One UI 9.5 again, S22 fixes, clearer broken downloads.**
- **Camera in One UI 9.5 on One UI 8.5 phones** (S23 FE, A35, S22s updated to One UI 8.5; testing): One UI 8.5 asks for
  the camera in a newer way than One UI 8, so every camera call failed and Samsung's video call service crashed again
  and again. These phones now get their own camera file.
- **Z Fold8: One UI 9.5 starts again** (since 0.5.42 it stopped at startup).
- **One UI 9.5 on the S22 and other One UI 8 phones** (testing): it stopped about 50 seconds in on a second network
  log One UI 8 never set up. OneOS now sets that up for the session too.
- **No sound on some Exynos phones** (S23 FE; testing): the "Hey Google" voice model was too big for the phone's voice
  wake-up chip, which crashed the sound service every minute. OneOS now turns off Hey Google's always-on listening
  in the other system when that happens.
- **S Pen on Galaxy Tabs** (ColorOS; testing): the pen worked as a mouse pointer. It now writes and taps like a pen.
- **"The download is damaged"** now says what to do: delete the file, download it again (use ADM from the Play Store
  if Chrome keeps breaking it), then choose the new file. The button is Download again instead of Retry update,
  which only checked the same broken file again.
- Reports now say which root setting changed when the return to One UI fell back to a restart, and which app asked
  the other system to power off.

New in 0.5.44: **One UI 9.5 on the Galaxy S22 (Snapdragon) gets past its first minute, ColorOS on Galaxy Tabs as a tablet.**
- 0.5.43 got One UI 9.5 starting on these phones, but on the S22 it stopped after about a minute: One UI 8's network
  module asked for a newer network setting (L4S) that One UI 8 never set up. OneOS now sets it up, switched off,
  for the session, and removes it when you return. Untested on a phone.
- **ColorOS 17 on Galaxy Tabs is a tablet now:** it showed the phone lock screen, home screen and dock. OneOS now tells
  ColorOS it runs on a tablet.

New in 0.5.43: **One UI 9.5 starts again on One UI 8 phones (S22 series and others), Tab S9 Ultra and Tab S11.**
- **One UI 9.5 stuck on the OneOS logo** (0.5.39 to 0.5.42, the S22 series, S23 FE and other phones whose sound driver
  is the older kind): a sound check OneOS made before starting One UI 9.5 waited forever. It now asks only what
  answers at once, so the system starts.
- **Galaxy Tab S9 Ultra (SM-X910) and Galaxy Tab S11 (SM-X730):** ColorOS 17 for tablets, testing.

New in 0.5.42: **One UI 9.5 boots again on the Galaxy S22 series, its own screen lock, and more Galaxies.**
- **One UI 9.5 on the Galaxy S22 series and other One UI 8 phones** stopped at the One UI logo since 0.5.39's camera
  change: the camera's native part still spoke One UI 8's numbering and stopped the system as it started. It now
  speaks One UI 9's, so the system starts with the camera on. Untested on a phone.
- **Screen lock in One UI 9.5** (testing): One UI 9.5 now has its own lock screen with your PIN, pattern or password,
  as the other systems do.
- **The OneOS app inside One UI 9.5** shows One UI's artwork and the root page again (it showed ColorOS's header and
  no root items).
- **Galaxy Tabs: the tablet system is ColorOS 17** (it was called OxygenOS 17), now with ColorOS artwork. Also for the
  Galaxy Tab S9 FE+ (SM-X610) and Tab S9 FE (SM-X510), testing.
- **Galaxy S22+ with Snapdragon** (SM-S906E): OxygenOS 16 and One UI 9.5, as on the other Snapdragon S22s. Untested.

New in 0.5.41: **Galaxy Tabs (testing), choose your download mirror, proximity in S24 Ultra calls.**
- **Galaxy Tabs on One UI 9** (testing): OxygenOS 17 built from the OnePlus Pad 4, the one system offered on the Galaxy
  Tab S9 (SM-X710), Tab S10 FE and Tab S10 FE 5G (SM-X520, SM-X526) and Tab S12 Ultra (SM-X940). Not tried on a
  tablet yet: the screen, sound, S Pen or keyboard cover may not work; share the session logs.
- **Pick where to download a system:** every Download button now asks SourceForge, Google Drive or gofile, and
  offers your last choice first (SourceForge is slow for many users).
- **Proximity during calls on the Galaxy S24 Ultra** (ColorOS, PixelOS and the others): the screen turns off at your
  ear. The S24 Ultra has no proximity sensor of its own; the touchscreen's ear detection now stands in, as on the
  S24 FE. Untested on an S24 Ultra.

New in 0.5.40: **Calls on SIM 2 with sound on the Galaxy S24 Ultra, and Screen resolution in One UI 9.5 no longer
sticks.**
- **Calls on the second SIM** (Galaxy S24 Ultra and other Snapdragon Galaxies with Qualcomm's newer audio driver, in
  ColorOS, PixelOS and the other systems): a call on SIM 2 started on SIM 1's voice channel and had no sound either
  way. OneOS now moves the call to SIM 2's channel as soon as it starts. Untested on a phone.
- **Screen resolution in One UI 9.5:** switching from QHD to FHD or HD made everything too small and switching back
  did not help. A bad switch no longer sticks: every new session starts at the panel's own resolution (Screen zoom
  is kept). Switching inside a session can still look wrong; leave it until the next start.

New in 0.5.39: **Camera in One UI 9.5 on the Galaxy S22 series and other One UI 8 phones, and the crackling fix on
more phones.**
- **Camera on One UI 8 phones** (experimental, untested on a phone): One UI 9.5 now talks to One UI 8's camera service
  in its own numbering (read from the S22 Ultra), sends the rotation setting the way One UI 8 expects, and configures
  camera streams with the calls One UI 8 has. Samsung Camera and the torch are back there.
- **No more crackling sound in One UI 9.5**, now on every phone it affects: 0.5.38's fix looked for the newer audio
  driver in one place only and missed it on the Galaxy A56 (still 0.5 ms buffers and hundreds of breaks).

New in 0.5.38: **One UI 9.5 on the Galaxy S22 series and other phones still on One UI 8, the OneOS app and clean
sound in One UI 9.5, the Galaxy Z Fold4, and S24 Ultra Bluetooth audio.**
- **One UI 9.5 on phones still on One UI 8.0/8.5** (experimental): the Galaxy S22, S22+ and S22 Ultra (Snapdragon
  and Exynos), S23 FE, Z Fold4 and the Galaxy A, M and F phones held on One UI 8 can now start One UI 9.5.
  Thirteen test rounds with S22 testers fixed what Android 16 cannot give an Android 17 system: its own system
  modules, networking (no stop at boot or on calls), Bluetooth, the screen's size and sharpness, SELinux for new
  apps, NFC, the quick panel and the setup screens. The camera stays off on these phones for now, and you confirm a
  short warning before the switch.
- **OneOS app in One UI 9.5:** One UI 9.5 only installs system apps on its own allow list, so the OneOS app (and
  with it Back to One UI) was missing on phones on One UI 9. It is now on that list for the session.
- **No more crackling sound in One UI 9.5** on the Galaxy A56, A57, S26 FE and other phones whose audio driver is
  older than One UI 9.5: One UI 9.5 cut the speaker's audio buffer to an eighth there (0.5 ms), and the sound broke
  up thousands of times a session. It now keeps the full buffer.
- **Galaxy Z Fold4 (SM-F936)** with OxygenOS 16 (pull request #361 by jinkun1998): tested by the contributor; the
  cover screen's brightness now follows the slider. Known: the camera does not work, and the phone runs warm.
- **Galaxy S24 Ultra Bluetooth audio** in Pixel, PixelOS, LineageOS and Infinity-X (pull request #358 by
  ankaserdev): music plays through Samsung's software Bluetooth route instead of staying on the speaker.
- **Keyboard covers** (pull request #362 by crisazas): detaching a keyboard cover no longer leaves a key reader
  using a full CPU core until the next restart.
- **Also fixed:** a black screen on OxygenOS and ColorOS on some Exynos phones with a 120 Hz screen (Galaxy A25,
  since 0.5.37); Bluetooth stuck at "turning on" in One UI 9.5 on the S22 Ultra; One UI 9.5 stopping at boot on the
  S22 Ultra (Exynos).
- Known: changing Screen resolution in One UI 9.5's settings makes the screen too small and does not switch back;
  leave it as it is for now. Untested on a phone: the One UI 9.5 app and sound fixes, the Fold4 brightness changes,
  and One UI 9.5 on One UI 8 beyond the S22 series.

New in 0.5.37: **Camera on One UI 9.5 phones, the Galaxy S24 FE on ColorOS, ColorOS's equalizer, and the screen
compositor on the fast CPU cores.**
- **Camera on phones with One UI 9.5** (the Galaxy S26 series): One UI 9.5 numbers its camera service calls
  differently. PixelOS, Pixel, Infinity-X, Nothing OS, HyperOS, ColorOS, LineageOS, OriginOS and One UI 9.5 now
  pick the matching camera files on those phones. LineageOS on the S26 Ultra stopped 40 s after the start for this
  reason (its system crashed at the camera); it should start now.
- **Galaxy S24 FE and Exynos phones on ColorOS** (pull request #355 by Energobro, brought in with safety changes):
  screen recording, hardware screen corners and an anti-aliased camera cutout, proximity during calls, the camera
  sensors, reverse wireless and bypass charging from ColorOS's own switches (One UI's charging settings are put
  back on the return), Dolby levels, and no loud burst or click when audio is paused.
- **ColorOS's Equalizer** (Settings, Sound) opens OneOS's sound effects page instead of an empty screen.
- **Screen compositor on the fast cores:** the other system's compositor stayed on the phone's slow CPU cores for the whole
  session (seen on the A36: up to 24 ms a frame, slow first touches). It now runs where One UI's own runs.
- **Lighter animations** (OneOS app in ColorOS): switching it on or off now restarts ColorOS for a moment, so
  turning it off really brings the app open and close animations back.
- **PixelOS screen corners** on phones that run PixelOS at FHD+ on a QHD screen (Galaxy S24+): the corners were
  rounder than the screen.
- Untested on a phone: the One UI 9.5 camera (needs an S26 on One UI 9.5), the S24 FE fixes beyond the
  contributor's own phone. Known: changing HyperOS's region restarts the other system; a fix is in the works.

New in 0.5.36: **HyperOS fits the screen on QHD Ultras, SMS on more phones, PixelOS corners, safer returns.**
- **HyperOS on the S24 Ultra, S25 Ultra and other QHD phones left at FHD+:** the system ran the whole QHD screen
  with the density meant for FHD+, and HyperOS's own scaling then made everything about a quarter too big
  (Control Center cut off on both sides). HyperOS now gets the density for the width it really runs at; the
  Exynos S24+ (which runs it at FHD+) keeps One UI's.
- **Incoming SMS** on the Galaxy A56, A57 and S26 Ultra: their Samsung radio library has the same message check in
  another form, which OneOS did not recognise, so no SMS arrived in the guest. It is found by its instructions now.
- **PixelOS screen corners** follow the phone's own rounding: apps rounded to the display's corners no longer show
  grey edges (confirmed on the A36).
- **Return to One UI** no longer reboots when a guest app compile is still hanging in the background (A57 on
  ColorOS): OneOS stops it and finishes the return in place.
- Untested on a phone: the HyperOS density on the Ultras, SMS on the A56/A57/S26 Ultra.

New in 0.5.35: **PixelOS 17 on every Galaxy on One UI 9, One UI 9.5 on the Z Fold8 with its own files, Dolby on
Bluetooth, and contributors' fixes.**
- **PixelOS 17** (new system, the Pixel experience built for the A series' CPUs; Google's Pixel builds cannot run on
  them): on **every bar phone on One UI 9** (S and A series, S22 and newer), with its own card; Folds and Flips keep
  their own Pixel builds. Tested on the A36, untested on the others: in-display fingerprint and face
  unlock, Always-On Display in the panel's low-power mode, the large lock screen clock, a brightness range and a
  slider that follows One UI's (the middle of the bar is no longer near the bottom), the status bar centred on
  the camera hole, calls (also over Bluetooth) and SMS. Face unlock stays set up after a return to One UI.
- **Dolby Atmos follows the music:** in the AOSP-based systems Samsung's Dolby stayed on the speaker's output when
  music moved to Bluetooth earbuds; it now moves with it (A36 with Galaxy Buds: confirmed).
- **Fingerprint and lock screen in the Pixel-style systems:** the in-display sensor's icon has the right size, and
  the lock screen's message line sits above the sensor circle instead of on it.
- **One UI 9.5:** the OneOS app inside it is installed again (One UI 9.5 only installs system apps on its own
  list); MediaTek A and M phones (A17) use their own Samsung Camera instead of the A36's, whose HDR mode their
  camera driver refused (the preview froze). The **Galaxy Z Fold8** gets its own One UI 9.5 files from Josh
  (thatjoshguy67, pull request #328): its two screens, cover and inner Home layouts, taskbar, Settings and
  rotation; other phones don't download them. Also from #328: **Feature flags** on the One UI 9.5 card (the
  Dynamic Island media player, on by default) and **search and system apps in Bring apps**.
- **ColorOS on QHD phones left at FHD+** (S+ and Ultra): ColorOS ran the full QHD screen while keeping One UI's
  FHD+ size for its layout; both now match (Sa12008s, who found, fixed and tested it).
- **Wireless debugging inside a system** accepts devices paired there (syedarhamraza, pull request #298).
- **New phone:** the Galaxy M36 5G (pull request #327), untested.
- Untested on a phone: PixelOS beyond the A36, the One UI 9.5 OneOS app and MediaTek camera, the Z Fold8's One UI
  9.5 files, the M36.

New in 0.5.34: **S24 FE zoomed photos and steady stereo, A16 brightness, USB-C headphones on the A35, and a safer
Debloat.**
- **Samsung Camera:** zoomed photos no longer close the camera on phones whose One UI lacks the S26 Ultra camera's
  AI Clear Zoom library (S24 FE): the camera then does without that step.
- **Stereo speakers** stay on: the earpiece speaker is powered at every start of playback, as One UI does (0.5.33
  powered it once, so stereo came and went).
- **Brightness on HyperOS (Galaxy A16 4G):** Samsung's lights service refused every brightness HyperOS sent, so the
  slider did nothing; OneOS now drives the panel itself when that happens.
- **USB-C headphones (Galaxy A35 and others):** the systems found only the USB accessory output and played nothing
  on wired USB headphones; they now get USB headphone outputs as One UI has them. Thanks to the tester who sent a
  working policy file.
- **Debloat** no longer offers apps that other apps need as a library (HyperOS's Xiaomi Cloud SDK and two more):
  removing it broke the phone app, so calls and mobile data stopped. Anyone who removed one gets it back at the
  next start.
- Untested on a phone: all of the above.

New in 0.5.33: **stereo speakers, the S24 FE camera, the ColorOS fingerprint circle, and One UI 9.5 without
freezes or reboots.**
- **Stereo speakers** in every system on Galaxies whose second speaker is the earpiece (S24 FE and others): One
  UI's own audio service powers the earpiece speaker for media; the other systems never did, so only the bottom
  speaker played. OneOS now does it, outside calls.
- **Samsung Camera on the S24 FE** (ColorOS): photo and video stayed black. The camera looked up the FE's 10 MP
  selfie sensor in a crop table the S26 Ultra's camera has no entry for. ColorOS's files have a new revision.
- **ColorOS lock screen fingerprint circle** at every wake on every phone: ColorOS waited for an Always-On Display
  doze that never ends on a Galaxy, so the circle never showed though the sensor worked.
- **One UI 9.5 no longer freezes** on the S25, S25 Ultra and S24 Ultra: OneOS's own session diagnostics (stack
  dumps of the launcher and SystemUI, a scan of every open file) stopped the whole phone; users held the keys and
  got the blue upload-mode screen. They now run only when the system is stuck before unlocking.
- **One UI 9.5 returns to One UI without a reboot:** its storage service took One UI's own name, so every return
  restarted the phone. One UI 9.5's files have a new revision.
- Untested on a phone: the S24 FE camera and stereo (the A36 has neither), the One UI 9.5 return (A36 can test).

New in 0.5.32: **Debloat, ColorOS raise to wake, the A-series camera in One UI 9.5, and the fingerprint circle on
the S24+, S25+ and Ultras.**
- **Debloat** (each system's page, under Apps): choose the system's apps to leave out at its next start. Safe to
  remove (nothing you use goes) and Remove with care (each app says what stops working, and asks once more) are
  separate pages, the apps grouped by who made them. **Same as MysticGSI's debloat** ticks what MysticGSI's own
  builds remove (ColorOS: Metis, UMS, AIUnit, Global Search and the rest), which made ColorOS clearly smoother on
  the A36. Apps you updated from the Play Store go with their updates, and their code and data are deleted. Restore
  all brings every app back at the next start, HyperOS's preinstalled apps included. The system image is never
  changed. Always-On Display stays: the lock screen's fingerprint circle needs it.
- **ColorOS raise to wake** works: ColorOS took every Galaxy lift for "put down" (OPPO's sensor reports a lift
  differently). It now uses the Galaxy's own pick-up sensor (A36: confirmed). ColorOS's files have a new revision.
- **ColorOS Lighter animations** in the OneOS app inside ColorOS (Performance): OPPO's mid-range effects instead of
  its flagship ones. Smoother on most Galaxies, but apps open and close without their animation; off by default.
- **One UI 9.5 camera on Galaxy A and M phones:** the S26 Ultra's camera of the image died at launch on their
  sensors (A17). A and M phones now get the A series' own Samsung Camera. One UI 9.5's files have a new revision.
  On the **S26 Ultra** itself the camera no longer closes at launch, and Samsung's Message Guard no longer crashes.
- **Fingerprint circle on the S24+, S25+ and the Ultras** (QHD screens at their default FHD+): it sat a quarter too
  low in the Pixel systems, Nothing OS, LineageOS, Infinity-X and ColorOS, and far from the sensor in HyperOS.
- **HyperOS on the S25 Ultra and other QHD phones at QHD** no longer looks zoomed in, like a foldable.
- **120 Hz on the S24 FE** and other Galaxies whose One UI lists its fast mode as 120.00001 Hz: the systems ran at
  60 Hz, so swipes lagged.
- **Galaxy A17 5G on One UI 9.5:** no more kernel panics from a second double-tap-to-wake writer.
- **Back to One UI with Volume Up + Volume Down** now buzzes once when the 3 s hold is taken, so a frozen black
  screen still shows it worked.
- Pixel 11 phones' modem thermal manager and HyperOS (Lhasa) Find Device are left out like their siblings'.
- Untested on a phone: the One UI 9.5 A-series camera, the QHD fingerprint and HyperOS fixes (A36: 1080 px).
