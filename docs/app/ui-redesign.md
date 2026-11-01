# OneOS SESL9 interface

The redesign lives on `codex/oneos-sesl9-redesign`, based on the latest Fold8 branch (`d285f56`). Existing local Fold8 work was restored after the pull; its recovery stash remains intact.

## Design and components

Figma file `pAZuve5FxNvCebYmd5dVJY`, OneOS page `341:10456`: phone catalogue `399:21700`, wide catalogue `397:12677`, onboarding `397:14509`, `397:14787`, `397:15006`.

The version catalog strictly pins the same SESL9 family and `io.github.tribalfs:oneui-design:0.9.13+oneui8` as Twidget. Settings use `PreferenceFragmentCompat` and the library's `startPopOverActivity` / `PopOverOptions.centerRightAnchored` API. Onboarding reuses Twidget's `AnimatedTitleView`, contained-button style, backdrop/card resources, and spring/fade timing, adapted to OneOS content. The unused barcode scanner is excluded to retain offline operation.

The five repeating catalogue slots are Infinity X, HyperOS, ColorOS, Nothing OS and Pixel. Only images actually offered by the resolved OneOS phone profile can enter the setup path. Unsupported slots remain visible with an Unsupported badge and explain their availability on tap. Setup, file identity checks, launch gates and return requests retain their existing implementations.

## Artwork

The ten supplied exports from `OneOS image cards` are bundled without edits. Default `drawable-nodpi` resources are the thin mobile versions; `drawable-w600dp-h480dp-nodpi` resources are the wide versions. The different source filenames do not change which OS image the backend installs. Artwork aspect ratio determines each card's width from its available safe height. The carousel does not inherit settings-page margins or rounded viewport masks.

## Build and verification limits

Normal full builds still require the server-built, hash-pinned OS package sets. Those are not all present in this checkout. Emulator UI builds use a temporary external Gradle init script that omits generated OS payloads; they are not release or device-switching artifacts. Do not distribute those APKs as complete OneOS builds.

Probe retains its asset/code/permission audit. AndroidX Core's app-private signature permission is permitted; platform and third-party permissions remain rejected. Its unshrunk SESL9 debug APK has a 60 MB cap; the 30 MB release cap remains.

The emulator verifies UI flows and unsupported-device behavior. It cannot establish that a real rooted Samsung device can stage and switch an OS. The native Samsung popover presentation also needs a One UI device; the app uses the same platform-aware API as Twidget.

Existing regression results: model 195/197 passed (the two failures concern pre-existing local Fold8Launcher package/fixture additions); safety 6/6 passed; root 75/112 passed (most script fixtures refuse macOS ownership checks, plus the local unregistered session assets). No switching safety check was bypassed to make those tests pass.
