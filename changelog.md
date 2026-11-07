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
