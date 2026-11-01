# Pixel fold transitions on Galaxy Z Fold8

The `f8` + `pixel11fold-yogi` pair uses its own `pixel-f8` package set. The
Fold8 Ultra keeps `pixel-f8u`. The new set retains the Pixel base guard files
and adds the patched SystemUI, the existing system-UID angle reader and an
immutable resource overlay enabling native unfold and hinge-driven progress.
It also retains the existing tested stage’s 48dp bar, AOD configuration and
saved-wallpaper parser-spacing fix when upgrading its preparation scripts.

`fold8_pixel.sh prepare` checks the original SystemUI digest after the guest
system_ext overlay is ready, binds the replacement read-only and copies the
relay into guest data. The UI activator starts that relay inside the guest
namespace on every entry. Samsung sensor 65686 rejects registration by Pixel
SystemUI's app UID, while UID 1000 can register it. Timestamped frames bridge
that input into Pixel's existing hinge provider. Public sensor registration
remains available when the relay is absent or stale. The original Pixel
animation providers own progress smoothing and rendering.

For this profile/set, the default app-facing hinge feature follows native
posture instead of appending `-flat`. Its bounds still come from the measured
inner display. Explicit `ONEOS_GUEST_POSTURE=flat` remains an opt-out. Pixel's
native framework already reports HALF_OPENED; no framework device-state IDs or
screen-switch policy are replaced by this change.

The original SystemUI is pinned to
`9934d2dac326f56290f459b9e649185cd5531e1b6ae1f5a72b11e88f865f8b03`.
Only classes2.dex changes and one adapter class is appended in classes4.dex;
all original classes and non-DEX contents are checked. Certificate metadata is
retained for a trusted system-directory bind replacement; the changed APK does
not have an OEM-valid content signature and must not be installed normally.
OEM APKs are not committed. The small adapter DEX is generated from the included
Java source and its compilation-only stubs (`javac --release 8`, D8 `--min-api
31`); the stubs never enter the guest APK.

Build the set with `scripts/make-fold8-pixel.py --base out/overlays_pixel_yogi
--systemui /path/to/original-SystemUIGoogle.apk --relay
out/overlays_n6_fold8/Fold8AngleRelay.dex --out out/overlays_pixel_fold8`.
Supply `--sdk` and a debug keystore as needed. A different toolchain or ZIP
timestamp can change hashes; `--review-pins` explicitly updates the reviewed
package list and its test fixture. Gradle enforces the resulting pins when
packing the full APK.

On SM-F971B / F971BXXS3AZIJ, the owner confirmed working opening animation and
YouTube's half-fold layout with the live prototype. SystemUI logs showed
intermediate angle updates commonly 40 ms apart during motion. This is not a
fixed sample-rate guarantee. Cold-start integration is tested separately from
that live-prototype evidence. Physical screen-off, every orientation,
accessibility and deliberately failed-relay cases are not exhaustively tested.

Build 33 (`0.4.19-fold8-hinge`) is based on official OneOS 0.4.19. An in-place
host-app update must be signed with the same OneOS release key as the installed
APK. A local review build signed with a different key cannot update it.

## Z Fold8 Ultra (0.4.21)

The Fold8 Ultra (SM-F976B, profile `f8u`) runs the same Pixel 11 Fold image and
has the same Samsung sensor (`Folding Angle  Non-wakeup`, type 65686, read on
the phone 2026-10-26), so `pixel-f8u` now carries the same patched SystemUI and
relay. Its unfold RRO is `OneOSPixelUnfold.apk`
(`switcher/overlays/pixel_f8u_unfold`): only the two unfold gates, because the
Fold8's 48dp status bar and AOD values were measured on the Fold8; the Ultra's
bar stays with `OneOSPixelStatusBar.apk` and the host's measured height. Build:
`scripts/make-fold8-pixel.py --variant f8u --base out/overlays_pixel_yogi ...
--out out/overlays_pixel_f8u`. Both sets ship the same SystemUI build, so the
APK packs it once. Posture follows the hinge by default on both Fold profiles;
`ONEOS_GUEST_POSTURE=flat` keeps the old flat fold line (run 41 on the Ultra
saw HALF_OPENED 3 s after a flat unfold with the public hinge sensor; watch for
apps switching to tabletop after unfolding flat).

The saved-wallpaper spacing fix now runs for every Pixel guest: the parser is
Pixel 17's, not the Fold8's.
