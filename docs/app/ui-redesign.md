# OneOS SESL9 interface

The redesign lives on `codex/oneos-sesl9-redesign`, based on upstream OneOS 0.4.36 (`b5bcc47`, version code 53), matching the supplied `OneOS-0.4.36-fold.apk`. Older local Fold8 experiments remain in named recovery stashes rather than replacing the newer backend.

## Design and components

Figma file `pAZuve5FxNvCebYmd5dVJY`, OneOS page `341:10456`: phone catalogue `399:21700`, wide catalogue `397:12677`, onboarding `397:14509`, `397:14787`, `397:15006`.

The version catalog strictly pins the same SESL9 family and `io.github.tribalfs:oneui-design:0.9.13+oneui8` as Twidget. Settings use `PreferenceFragmentCompat` and the library's `startPopOverActivity` / `PopOverOptions.centerRightAnchored` API. Onboarding copies Twidget's permission-row XML, typography, spacing and selectable ripple, plus `AnimatedTitleView`, native contained buttons, backdrop and spring/fade timing. OneOS root/security checks remain real. The welcome icon is 112 dp and its block is vertically centred; the permission rows retain Twidget's own dimensions. The permission rows sit directly on the backdrop, without a nested preference page or second card surround. The unused barcode scanner is excluded to retain offline operation.

The five repeating catalogue slots are Infinity X, HyperOS, ColorOS, Nothing OS and Pixel. Only images actually offered by the resolved OneOS phone profile can enter the setup path. Saved-system cards also invoke the 0.4.36 quick-switch flow. Native Settings switches use the current thermal, IMS, camera and screen-lock preferences. Unsupported slots remain visible with an Unsupported badge and explain their availability on tap. Setup, file identity checks, launch gates and return requests retain their existing implementations.

## Artwork

The ten supplied exports from `OneOS image cards` are bundled without edits. Default `drawable-nodpi` resources are the thin mobile versions; `drawable-w600dp-h480dp-nodpi` resources are the wide versions. The different source filenames do not change which OS image the backend installs. Artwork aspect ratio determines each card's width from its available safe height. The carousel does not inherit settings-page margins or rounded viewport masks.

## Build and verification limits

The supplied Fold APK's seven package lists match the 0.4.36 source. All 169 unique payloads were extracted and SHA-256 verified into `/tmp/oneos0436-payloads`. A temporary external Gradle init script points the normal `oneosFiles` task to those files without bypassing hash or package checks. The build uses `-Poneos.series=fold`. The initial UI-only APKs have been superseded by this complete Fold build.

The bundled guest payload remains the official hash-pinned guest APK. The redesigned guest app source/debug APK is built separately; releasing it inside guest payloads requires the normal signed guest packaging/pin update.
Probe retains its asset/code/permission audit. AndroidX Core's app-private signature permission is permitted; the 0.4.36 INTERNET permission for reports is also retained, and other platform/third-party permissions remain rejected. Its unshrunk SESL9 debug APK has a 60 MB cap; the 30 MB release cap remains.

The emulator verifies UI flows and unsupported-device behavior. It cannot establish that a real rooted Samsung device can stage and switch an OS. The native Samsung popover presentation also needs a One UI device; the app uses the same platform-aware API as Twidget.

Current model and safety verification on the 0.4.36 base: 216 model tests and 6 safety tests passed. Root-script fixture execution on this macOS host was not established; earlier fixture runs hit host ownership checks. No switching safety check was bypassed to make tests pass.

## Debug setup preview

Preview mode is off by default, enabled only in **Settings → Debug → Preview mode** in debug builds. A card's **Set up** button always asks whether the file is downloaded: **No** opens the existing README download-information link, as requested, **Yes** opens the system file picker. With debug preview mode enabled, Yes instead displays the fake install screen. Card menus and unsupported-device dialogs have no preview shortcuts. Activity entry also verifies the debug flag and setting.

The preview binds the real setup layout to a pure local timeline with no setup/launch/root-job subscription. Cancellation freezes it; successful completion opens simulated environment checks; Boot previews the native loading page for eight seconds, without starting an OS. It refuses entry during a real OneOS operation. Timeline tests cover completion, cancellation and restoration.

Setup uses the eight mockup rows mapped to all nine original backend stages, blue completion marks, native `CardItemView` dividers and a stock SESL progress bar over the artwork. Wide actions sit below the right-hand checklist; phone actions stay pinned while content scrolls. The setup page uses a fixed native SESL toolbar and a weighted content viewport above navigation, so artwork shrinks with display height. On wide displays, checklist scrolling cannot move the toolbar or artwork; compact screens use one scrolling column under the fixed toolbar. SESL fading edges mark overflow at the checklist viewport, including on shorter displays; progress ticks do not rebuild the checklist. Other toolbar pages use the same SESL9 floating-toolbar compatibility bridge as Twidget.

Shared list cards throughout file/storage/session/diagnostic screens now use `CardItemView` inside `RoundedLinearLayout`, rather than the hand-built row/card shapes. Settings use SESL preference cards with Twidget's `InsetPreferenceCategory` ending and `SeslPreferenceCaption` descriptions below cards. Onboarding uses stock CardItemView rows instead of nesting a preference page inside a card, while retaining Twidget's title and button motion. Handoff and guest-return source use the matching artwork composition and native contained buttons. The bundled guest payload limitation above still applies.

Catalogue actions use `OneUI.ContainedButton` / `OneUI.ContainedButtonTheme`. A 1dp translucent foreground stroke outlines each artwork card. The carousel requests the same native selection haptic used by Twidget after a user drag settles on a different snapped position; initial/programmatic positioning is silent.


## Environment and boot sequence

Successful setup automatically opens the phone/wide environment-check page. App launch always opens the card picker, with the last used OS centred. Opening a prepared OS card goes to environment checks; successful setup still opens those checks directly. Remembered image IDs only guide navigation: Boot stays disabled until the real stage and environment checks pass. The original Switch confirmation, warnings, fresh screen-lock read and root checks remain in place. Saved copies retain the existing restore operation, then stop on the environment page for checks rather than automatically launching.

Guest root is a current-status row, as requested; no unsupported toggle is shown. Boot opens a native SESL progress page. Cancellation is accepted before the irreversible root launch is committed, and unavailable afterwards. A synchronized guard ensures a cancellation and a commit cannot both succeed; tests cover the race. The root script's frozen handoff frame remains separate. Debug setup completes into the simulated environment page, whose Boot action previews the loading screen without starting or observing a real launch.


Short hero cards use the supplied wider compositions with ordinary bitmap crop matrices and per-OS focus points. These give the complete heading more breathing room without scaling down into side bands or extending edge pixels. Thin exports remain on the mobile catalogue. Setup reserves space below the heading for its progress overlay. Geometry tests cover all five OSes and assert both complete-heading visibility and continuous bitmap coverage.


## Window and navigation behavior

The host uses Twidget's `applyEdgeToEdge` integration and its native SESL9 `FloatingToolbarLayout` bridge. Toolbar XML sets `handleInsets=false`, and the activity applies insets to the toolbar root itself, so the wrapper cannot add a second copy of the status/navigation spacing. Only the top of the main container is rounded; it has no bottom viewport mask. Both system-bar surfaces are transparent. Preference lists own navigation padding and native fading, allowing the scrolling surface to reach the navigation edge while the last row can scroll clear of it. Fixed setup/environment/boot controls retain safe system-bar and cutout insets. The manifests opt into predictive Back; ordinary pages use AndroidX's default activity Back handling. Internal onboarding steps and a real in-progress boot retain only their necessary custom Back behavior.

The carousel waits until the saved OS is laid out and snapped before its first visible frame, then fades in over 220 ms with a 6 dp rise. Settled user swipes and OS actions remember the chosen family. Debug contains the original team checks, phone report, read-only tests, technical setup and OS-file entries directly, alongside the debug-only preview setting.

The redundant “Before you start” Settings entry is removed; that content remains in first-run onboarding. Native phone (1080 × 2400), foldable (2208 × 1840), and tablet (1920 × 1200) display presets have been exercised. AVD size/density metadata has no override; the presets do not change OneOS guest-display configuration.

The centred carousel card remains at full safe size; adjacent cards scale continuously to 92% using a smoothstep of their distance from the snap centre. The transform does not affect layout or snap bounds. Environment tiles keep the same native `RoundedLinearLayout`/`CardItemView` stack as Twidget. An outline from `SeslRoundedCorner.getSmoothCornerRectPath` uses the stock outer SESL radius minus the 8 dp inset, keeping nested corners concentric without requiring a Material Components theme.

On compact displays the centre card is capped at 78% of the carousel width, with an 8 dp inter-card gap. Its height follows the original artwork aspect ratio and available safe height; the remaining vertical space centres it. Neighbour peeks remain visible after the 92% scale transform. Wide displays retain height-driven sizing.

Artwork navigation uses the platform `MaterialContainerTransform` bundled in SESL9 Material: a 420 ms bounds/shape transition with an overlapping fade between the existing artwork crops (320 ms on return), plus a 160 ms surrounding-content fade. Picker → setup/checks, successful setup → checks, and checks → boot use it when the source artwork is visible. Back remaps the element to the selected OS card. Missing/offscreen sources fall back to normal navigation; transition completion never authorizes an OS operation.

Prepared OS cards have no primary button: tapping their surface opens the pre-boot checks with the artwork transition. Saved copies retain the original restore confirmation. Unprepared cards retain Set up. The launcher icon uses Figma foreground `395:11658` and gradient background `395:11655` as separate native adaptive layers; the Android layer framing reproduces the composite `395:11863` proportions after masking. The same icon is used by the guest source; Probe keeps its diagnostic branding.

The environment-screen crash was reproduced as a Material theme-enforcement exception. Inner cards now retain the native One UI component and SESL smooth-corner path. A complete debug setup reached the pre-boot page on Emulator 2 with the OneOS process still alive and no AndroidRuntime exception for that process.

Card navigation stays available during read-only stage checks. A cached prepared-image identity can open pre-boot checks while a fresh check runs; it never authorizes Boot. The real Boot control requires a completed, fresh check matching its rendered report and selected image, with all original gates passing and jobs idle. Unprepared-card surfaces and buttons share the same setup action. Carousel selection ticks use SESL's Samsung index 41 on One UI (the native seek-bar step effect), with the standard clock tick as fallback; the request result is logged in debug builds.

Picker actions now distinguish never-prepared (Set up), the current image needing OneOS update/repair/re-staging (Update), a prepared saved copy (Switch), and a current ready image (tap to inspect, no primary button). The same backend image finding supplies update status on the pre-boot page and replaces its Boot action with Update. Switching saved copies retains restore confirmation; updating retains the existing repair/setup gates and data-preservation plan.

The pre-boot action floats above the scrolling content. SESL's bottom fade is measured from the action area's height and drawn by the scroll view behind the button; trailing padding lets the final row scroll clear. Fact tiles blend 16% of the existing functional green/orange/red into the native neutral surface according to their individual SWITCH gate. Pending checks stay neutral, and the screen-lock override retains its warning severity.

Update/repair operations use the setup artwork, checklist, progress and native Cancel layout with an Update title and Updating state. When root can reuse the installed image, the image row says Verify existing system image; the original KEEP_RAW verification, OneOS patches, installd table, session settings, cleanup and final verification still run. A root-verified interrupted stage can be identified without a marker, but the original fresh prepare gates and data-preservation plan still decide whether it can be reused.

Final validation: Full debug, Probe isolation audit and guest source build pass. Model/safety tests pass (222), plus targeted SetupPlan/StageStatus tests (23). On the physical Fold8, saved Nothing OS exposes Switch and its card tap opens the existing restore confirmation. The swipe log records the native Samsung tick accepted. Non-preview ColorOS checks show green root/storage/battery and orange screen lock under the existing override; the overflow is behind the fixed Update control. A replacement install retains the original app install time. Real OS update/restore/boot was not performed as part of UI verification.

Pre-boot → update/setup now enters through the same shared-artwork transform, including when a downloaded-file confirmation is required first. A successful update returns through the reverse transform to the existing checks page, whose observers refresh its gates, instead of pushing a duplicate checks activity. Other setup entry points retain their normal destination.

While environment checks run, the disabled native action button shows a centred SESL spinner instead of its label. It retains the native label measurement and exposes the checking state to accessibility. The spinner uses Twidget's lifecycle cleanup for the SESL animation callback. The scroll view forces its native bottom fade to the measured action clearance even when temporary checking content does not overflow; no checking row sits under the button.

Setup/update artwork has a local transparent-to-dark status scrim behind the white state label and stock SESL horizontal progress bar. A lighter blue native progress tint and translucent track keep both determinate and indeterminate states visible on bright exports. The original progress values and timing are unchanged.

During the user's real ColorOS update, the update-specific checklist was observed through cleanup, then the existing pre-boot page returned with Boot into ColorOS 17 restored. No boot was triggered by the agent. Contrast installation waited until this update completed.

Ordinary list sections add no outer row padding: CardItemView owns its native minimum height, typography, icon spacing, summary spacing and dividers. Toggle rows now use the same SwitchItemView as Twidget, and onboarding uses CardItemView rather than hand-sized text/icon rows. Setup check icons use the component default. Compact two-column environment facts retain their adaptive grid layout.

The carousel holds its selected view and defers stage-driven adapter replacement during shared-element capture and return. Artwork now owns the visible outline, while its parent has only a transparent rounded clipping shape, so an empty outlined shell cannot remain behind. Mobile pre-boot uses the same fixed-height ToolbarLayout and SESL9 FloatingToolbarLayout bridge as Twidget; nested scrolling drives its native floating back-button transition. Wide pre-boot retains independent fixed artwork and checklist scrolling.

Card height is derived from the measured carousel viewport, including while Android temporarily hides the shared element. The old global-visible-rect fallback could produce a 500 dp card on return and clip its bottom. Visible holders now resize when the viewport height changes and preserve the snapped position. The native image fade keeps the source opaque beneath the destination over most of the motion, avoiding a fade through black between different exports.

On mobile, the Boot/Update footer is a direct sibling of the ToolbarLayout in the window root, anchored above the actual navigation/cutout inset. It is outside the app-bar-scrolling content, so the floating-toolbar transition cannot move the action offscreen. The scrolling page retains clearance for the fixed footer.

Edge-to-edge is enforced in the common host activity on creation and resume: decor fitting is disabled, both bars stay transparent, and navigation contrast enforcement is off. Ordinary toolbar pages reserve navigation space in scroll padding instead of root padding. The old wrapper's bottom-corner mask is hidden globally, including About, reports and technical pages. Native footer slots retain control clearance without adding a navigation strip to pages with no footer. Mobile pre-boot's fade is window-aligned and includes the button plus navigation clearance.

The user confirmed that all behavior was working as intended after the all-pages edge-to-edge build was installed on the Fold8 and Emulator 2. Device interaction stopped at that point to retain the working state. The final full/Probe/guest build and model/safety checks passed; targeted stage/data-preservation tests passed earlier in this change.
