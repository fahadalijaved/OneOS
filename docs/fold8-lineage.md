# Pixel fixes on LineageOS 24 / Galaxy Z Fold8

This port is pinned to Lineage image
`f1ce7c1add2dae73c681b29ccb86068864d5f42886bc1c22d249891f3bdf6261`
and SystemUI donor
`aa22961855b1f8a9d3dbbbc643922f9b216f6d411313e12eb8b70086287b84c3`.
Other devices and images do not activate it.

Experimental brings over the Pixel continuous Samsung hinge-angle adapter with
native public-sensor fallback, enables native unfold/hinge progress flags,
sets all three framework status bar heights to 48dp, and removes SystemUI top
padding while retaining its normal font/icon sizes and symmetric side spacing.
Quick Settings header heights are recomputed when switching panels even if the
density stays the same. Lock-screen double tap to sleep and AOD double tap wake
use the existing Pixel touch helper. The original Lineage classes, resources,
other DEX entries and signing metadata are retained. This is a system-directory
bind replacement, not an APK to install using Package Installer.

The existing guest startup already normalizes saved wallpaper XML spacing and
exposes SystemUI's AOD service. Those fixes are retained. Pixel Launcher is not
transplanted onto Trebuchet; its Pixel-only broadcast sender check is retained,
so this port does not add the Pixel home-screen double-tap gesture to Trebuchet.
The contributor SystemUI opts into native hinge posture for half-fold app layouts; Stable retains its previous policy. Explicit ONEOS_GUEST_POSTURE still overrides the default.

The guest manager update adds the tested side-chat's LineageOS/OxygenOS/OriginOS
artwork mappings, headers and wide assets. System UIDs (including shell 2000)
can now be shown, granted and revoked in the guest root manager, using current
package identity and shared-UID grouping as before.

Build the SystemUI payload with:

```sh
python3 switcher/patches/fold8-lineage/build-systemui.py /path/to/SystemUI.apk \
  --zipalign "$ANDROID_HOME/build-tools/36.1.0/zipalign" \
  --output /path/to/Fold8LineageSystemUI.apk
```

The resource overlay sources are `switcher/overlays/lineage_fold8_*`.
Compile/link them with aapt2 against android-37, zipalign, and sign with a local
resource-overlay key. Use the stable source for the app baseline and the
experimental/statusbar sources for the contributor overrides. Overlay hashes
must match the published channel and the app's baseline package metadata.

Static validation: exact donor/image hashes, retained original classes and
non-DEX entries, DEX instruction checks, model/package/source tests, native
security regressions and packaged staging integrity. Physical hinge motion,
lock-screen gestures, artwork framing and persistence through a guest restart
still require an on-device run of the signed app update.
