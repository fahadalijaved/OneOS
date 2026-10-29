# Exynos phones (first runs, 0.4.17)

Two probe reports of 2026-10-25 brought the first Exynos profiles (a third, the
Galaxy A57, came in 0.4.29; see the end):

| | Galaxy S26+ (Exynos) | Galaxy Z Flip7 |
| --- | --- | --- |
| Model, codename, chip | SM-S947B, m2s, s5e9965 (Exynos 2600) | SM-F766U, b7s, s5e9955 (Exynos 2500) |
| One UI / Android | 9.0, 17, CP2A.260605.016 | 9.0, 17, CP2A.260605.016 |
| Panels | 1440 x 3120 on port 129, density 600 | 1080 x 2520 on port 129 (density 480), cover 948 x 1048 on 130 |
| Touch | sec_touchscreen | sec_touchscreen, sec_touchscreen2, a "flip" lid switch |
| Backlight | /sys/class/backlight/panel (max 12750) | panel and panel1 (max 12750) |
| Display composer | vendor.hwcomposer-3 | vendor.hwcomposer-3 |
| CPU | SVE, SVE2, SME, SME2 | SVE, SVE2, no SME |
| installd | identical to switcher/patches/host_installd.txt | identical |
| Images | both Find X9 Ultra builds, Pixel 11 Pro | both Find X9 Ultra builds |

The guest system takes One UI's vendor through Android's standard
interfaces (the AIDL composer, allocator, audio, radio and sensors), the same
as on Snapdragon. What the session scripts had learned on Snapdragon:

- **Display composer.** guest_start.sh restarts the vendor composer so that
  the guest's SurfaceFlinger becomes its client, and return_to_oneui.sh
  restarts it again for One UI. Snapdragon's service is
  `vendor.qti.hardware.display.composer`, Samsung's Exynos one
  `vendor.hwcomposer-3`. Both scripts now take whichever init knows. The
  return falls back to a reboot when neither is there.
- **Backlight.** `panel0-backlight` / `panel1-backlight` on Snapdragon, `panel`
  / `panel1` on Exynos. guest_start.sh's boot-animation wake and the
  diagnostics take whichever exists. The wake value 928 is in the range the
  probes showed in normal use (838 and 1295 of 12750).
- **Ports** are 129/130 instead of 147/148. Only the fold layout and the Z Fold8
  Ultra's Pixel display configs use ports, and neither applies here.

The Flip7 runs the guest as a phone on the main screen (the bar settings; root
gives every non-fold profile the phone values). With the lid closed, the guest
does nothing for the cover screen yet.

The compatibility check keeps every other Exynos phone blocked. With a
profile, Exynos is a warning ("Exynos: first runs"), and both profiles carry
a first-runs note at Switch. If the screen stays black, the black-screen
auto-return brings One UI back; the session logs are what the next step needs.

## Galaxy A57 (0.4.29)

A probe report of 2026-10-29: SM-A576B, a57x, s5e8865 (Exynos, 3 x Cortex-A520
and 5 x Cortex-A720), One UI 9.0, Android 17 build CP2A.260605.016, vendor API
202504, kernel 6.12. One 1080 x 2340 panel on port 129 at density 450,
sec_touchscreen, backlight /sys/class/backlight/panel (max 9180),
vendor.hwcomposer-3 with the AIDL composer, allocator and audio HAL, Samsung's
init.vendor.sysfw.rc (the softdog of docs/exynos-hosts.md), SVE and SVE2 but no
SME, and an installd table identical to switcher/patches/host_installd.txt.
Profile `a57`, in the s25 series, with the Z Flip7's images: both Find X9 Ultra
builds and Infinity-X, whose system code needs neither SVE nor SME. It is the
first A-series phone and the first mid-range chip; nothing about it differs
from the S26+ (Exynos) in what the session scripts read.
