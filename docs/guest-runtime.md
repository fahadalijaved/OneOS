# Guest root and modules

Enable guest root on the OS pre-boot page, choose a Zygisk framework if needed,
and import module ZIPs there or in the guest OneOS app. Module files, framework
state and package/UID grants live in that guest's `data/oneos_root/adb` tree.
One UI's persistent root app list is retained separately.

The existing guest OneOS app provides root status and permissions, the module
manager, framework status and a shortcut to reopen Vector or LSPosed. Permission
rows use native SESL9 components with real icons, direct switches, bottom search
and a toolbar filter menu. Search covers labels, package names and UIDs; filters
cover allowed/denied access and user/system apps. Apps sharing a UID appear as
one effective grant. Revoking that row removes all its package grants. The app
checks the current broker and package/UID association before each change.

Both module screens share native SESL9 cards with name, description, author,
version and an enable switch. Disabling keeps the module installed. Long press
opens available actions: update, uninstall or cancel removal, action.sh and WebUI.
Installs, updates and removals take effect at the next guest start. Actions and
WebUIs run inside the guest, never from the host pre-boot screen. The WebUI bridge
supports the common exec, spawn, toast, fullscreen and moduleInfo APIs; it does
not implement every KernelSU/APatch extension.

Restart guest closes guest processes, applies pending module changes, and starts
fresh guest services, root broker and the selected framework while One UI stays
stopped. It uses the existing splash renderer and launcher verbose setting.
Failure falls back to OneOS's existing return-to-One-UI recovery. Each startup
clears the shared boot-completion flags before module waiters start. Pixel 17's
saved-wallpaper spacing repair runs on both cold and soft startup paths.

## Building

Build the guest manager before the host app, so staging pins cover the new APK:

```sh
scripts/build-guest-manager.sh release
cd app-android
./gradlew :app:assembleFullRelease
```

Both release builds require the existing OneOS release signing configuration.
The host release build refuses a staged guest APK that differs from the normal
`:guest` release artifact.
`guest_manager.apk` is generated and ignored; a test APK or transplanted signing
block must not be committed or distributed as an official build. The original
OneOS signing key is needed to preserve ordinary update compatibility for an
existing guest app. For a fresh development guest, build with `--debug` followed
by `:app:assembleFullDebug`. Existing production-signed installations cannot be
updated with that debug certificate.

The native broker source, injection patch, framework normalizer, source pins and
binary checksums are documented in [third_party/guest-runtime](../third_party/guest-runtime/README.md).

## Validation

Run `:core:model:test`, `:core:root:testDebugUnitTest`, `:core:safety:test`,
`:guest:lintDebug`, and both host editions' debug assembly checks. Execute the
`scripts/test-guest-*.py` files directly (their hyphenated filenames are not
picked up by Python unittest discovery). SESL9's lint registries require a
Java 24 or newer Gradle runtime; the project compilation toolchain remains Java
21. Java 27 was used for the final lint run.


The owner reports guest root and module controls working in ColorOS and Pixel.
On the Fold8 with KernelSU, Pixel's guest-only restart produced a new guest
system server under the same kernel boot. PixelXpert's deferred APK install
completed after clearing the stale host boot flag. The native permissions page
and corrected toolbar action were exercised in the running guest. The grant
model, ZIP parser and installer/lifecycle helpers have focused automated checks.

A restart initially lost Pixel's live wallpaper because only cold preparation
normalized its metadata. The repair now runs at every guest startup; tests cover
preserving the selected component and content, idempotence, and symlink refusal.
Tidal Swirl was restored through Pixel's native picker and survived the updated
cold boot. A repeated soft restart with this wallpaper fix still needs a separate
live check; do not treat the cold-boot result as that verification.

See [provider compatibility](guest-root-provider-compatibility.md) for support
limits. This feature has not established universal cross-provider isolation.
