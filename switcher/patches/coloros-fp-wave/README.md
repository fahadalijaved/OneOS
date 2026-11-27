# ColorOS fingerprint wave (vdcoolok)

vdcoolok made this on a Galaxy S25 Ultra running ColorOS 17 as the guest (pull request #152,
`switcher/patches/systemui-fingerprint-wave` on his branch). It changes ColorOS SystemUI's
`OnScreenFingerprintUiMech`:

- **Glyph first.** If the thumb is already on the sensor when the screen wakes, the glyph shows
  at once. The pressed wave no longer plays first.
- **Wave after unlock.** A full wave plays over the home screen after the unlock. The ring
  hides when the wave ends.
- **120 Hz frames.** The wave runs at 16 ms frames.
- **No dim layer.** The black full-screen dim layer (`notifyHighlightVisibleUpdate`) stays
  out of the unlock path.

`coloros-fp-wave.patch` is his diff rebased onto the Find X9 Ultra IN (1105) SystemUI. It is
applied after `scripts/patch-coloros-fp-icon-screenon.py`, and his `oneosWakeGlyph` call runs
before that script's stale-dream block.

On top of his diff, every entry point first checks `OneOsGlyphShow.on()`, which reads
`ro.oneos.fp_wave`. `guest_props.sh` sets that property only for ultrasonic sensors, as on the
S25 Ultra the wave was made on. The same set serves optical-sensor Galaxies, which keep
ColorOS's own flow. `ONEOS_GUEST_FP_WAVE=0` turns the wave off.

Build: `APKTOOL=apktool.jar scripts/patch-coloros-fp-wave.py ColorPanoramicSystemUI.apk out.apk`
