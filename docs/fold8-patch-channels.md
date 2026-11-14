# Contributor patch discovery

The pre-boot page checks That Josh Guy's OneOS-files fork in the background for
`<profile>-<set>.json` on the `fold8-experimental` release. A source appears only
after its manifest validates for the selected phone, package set and exact raw
image hash. Check for patch updates probes for newly published sources as well.
Validated snapshots remain usable offline. Discovery never selects a source or
changes the prepared guest; choose the source and apply Update/Repair as usual.

The app trusts the contributor repository and release tag in
`app-android/packages/patch-sources.json`. `discover: true` lets that contributor
publish for any already supported phone/OS without adding another embedded
target. Explicit targets remain available for contributors with narrower scope.
The publisher accepts `--profile` and derives the exact image pin from the app's
root compatibility table when publishing an OS not listed in the registry.
New payload roles, new OS images and session scripts still require an app update.
Guard jars, guards.txt, native binaries and system-UID DEX remain APK-pinned.

Lineage on the Galaxy Z Fold8 uses `f8-lineage.json`. Experimental replaces
`Fold8LineageSystemUI.apk`, `Fold8LineageUnfold.apk` and
`OneOSPixelStatusBar.apk`; unchanged payloads use their existing upstream pins.
The stable baseline includes the original Lineage SystemUI and a resource-only
AOD overlay. Only profile f8 activates the new Lineage SystemUI/unfold payloads.

See [Lineage port](fold8-lineage.md) for exact scope and validation limits.
