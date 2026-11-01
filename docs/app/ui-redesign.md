# OneOS SESL9 interface

The redesign lives on `codex/oneos-sesl9-redesign`, based on upstream OneOS 0.4.36 (`b5bcc47`, version code 53), matching the supplied `OneOS-0.4.36-fold.apk`. Older local Fold8 experiments remain in named recovery stashes rather than replacing the newer backend.

## Design and components

Figma file `pAZuve5FxNvCebYmd5dVJY`, OneOS page `341:10456`: phone catalogue `399:21700`, wide catalogue `397:12677`, onboarding `397:14509`, `397:14787`, `397:15006`.

The version catalog strictly pins the same SESL9 family and `io.github.tribalfs:oneui-design:0.9.13+oneui8` as Twidget. Settings use `PreferenceFragmentCompat` and the library's `startPopOverActivity` / `PopOverOptions.centerRightAnchored` API. Onboarding reuses Twidget's `AnimatedTitleView`, contained-button style, backdrop/card resources, and spring/fade timing, adapted to OneOS content. The unused barcode scanner is excluded to retain offline operation.

The five repeating catalogue slots are Infinity X, HyperOS, ColorOS, Nothing OS and Pixel. Only images actually offered by the resolved OneOS phone profile can enter the setup path. Saved-system cards also invoke the 0.4.36 quick-switch flow. Native Settings switches use the current thermal, IMS, camera and screen-lock preferences. Unsupported slots remain visible with an Unsupported badge and explain their availability on tap. Setup, file identity checks, launch gates and return requests retain their existing implementations.

## Artwork

The ten supplied exports from `OneOS image cards` are bundled without edits. Default `drawable-nodpi` resources are the thin mobile versions; `drawable-w600dp-h480dp-nodpi` resources are the wide versions. The different source filenames do not change which OS image the backend installs. Artwork aspect ratio determines each card's width from its available safe height. The carousel does not inherit settings-page margins or rounded viewport masks.

## Build and verification limits

The supplied Fold APK's seven package lists match the 0.4.36 source. All 169 unique payloads were extracted and SHA-256 verified into `/tmp/oneos0436-payloads`. A temporary external Gradle init script points the normal `oneosFiles` task to those files without bypassing hash or package checks. The build uses `-Poneos.series=fold`. The initial UI-only APKs have been superseded by this complete Fold build.

The bundled guest payload remains the official hash-pinned guest APK. The redesigned guest app source/debug APK is built separately; releasing it inside guest payloads requires the normal signed guest packaging/pin update.
Probe retains its asset/code/permission audit. AndroidX Core's app-private signature permission is permitted; the 0.4.36 INTERNET permission for reports is also retained, and other platform/third-party permissions remain rejected. Its unshrunk SESL9 debug APK has a 60 MB cap; the 30 MB release cap remains.

The emulator verifies UI flows and unsupported-device behavior. It cannot establish that a real rooted Samsung device can stage and switch an OS. The native Samsung popover presentation also needs a One UI device; the app uses the same platform-aware API as Twidget.

Current model and safety verification on the 0.4.36 base: 211 model tests and 6 safety tests passed. Root-script fixture execution on this macOS host was not established; earlier fixture runs hit host ownership checks. No switching safety check was bypassed to make tests pass.

## Debug setup preview

A debug card menu offers **Preview setup**, also available from an unsupported card's explanation. It binds the real setup progress layout to a pure local timeline, with no setup/launch/root-job subscription. Cancellation freezes that timeline; the preview boot confirmation only finishes the preview. It refuses entry while an actual OneOS operation is busy. Release builds do not expose this entry. Timeline tests cover completion boundaries, cancellation and restoration.

Catalogue actions use `OneUI.ContainedButton` / `OneUI.ContainedButtonTheme`. A 1dp translucent foreground stroke outlines each artwork card. The carousel requests the same native selection haptic used by Twidget after a user drag settles on a different snapped position; initial/programmatic positioning is silent.
