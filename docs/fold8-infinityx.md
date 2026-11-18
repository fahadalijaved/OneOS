# Pixel fixes on Infinity-X 4.1 / Galaxy Z Fold8

This port uses the exact OneOS Infinity-X image, not a Lineage donor:

- Compressed image: `608bb8602dcc0c85fc80127a2f9713a695508438b8c2d31eef3df25d23109bb5`
- Raw image: `899ce57a069959b6463263074f35e5aadadeb7bb46f0c0a756d2ba64168545e2`
- SystemUI donor: `6a99684e831f9635738189d39667debe0f8b798012fa4eb622a7cb87ad9b1ddf`
- Settings donor: `bfe921965d18fd1c16ac335073dee4ccbf2be83adcd24e840fdd477f80d9d87b`

Experimental supplies continuous Samsung hinge input with native public-sensor
fallback, native unfold progress, live half-fold posture, 48dp framework status
bar heights, zero SystemUI top padding, symmetric side spacing, Quick Settings
header refresh on panel changes, lock-screen double tap to sleep/AOD double tap
to wake, and a 50:50 Settings activity-embedding ratio. Infinity-X's Settings
uses the same named float resource as Lineage, with original value 0.3636.

Only the Fold8 (`f8`) activates these new UI payloads. Stable receives the
original Infinity-X SystemUI, the original Settings ratio and the existing AOD
availability value. The experimental framework overlay exposes SystemUI's
existing DozeService. The native text/icon sizes, Infinity-X classes/resources,
launcher and guarded framework payloads are retained. The existing wallpaper
metadata normalization and shared guest artwork/root-manager fixes also apply.
The Pixel-only home-screen gesture broadcast is not enabled for Infinity-X's
launcher.

The SystemUI patch modifies Infinity-X's own methods. Its header callback uses
five local registers, so a sixth register preserves the listener before the
existing code runs; Lineage's different register layout is not transplanted.
Only classes2.dex changes, and the pinned hinge adapter is appended as a new
classes4.dex. Original classes, non-DEX entries and signing metadata are
preserved. These modified system APKs are for guest-directory binds, not
installation with Package Installer.

Build with `scripts/make-fold8-infinityx.py --systemui <donor> --relay <relay>
--sdk <Android SDK> --out <new output directory>`. The baseline and overrides
are separate outputs. Package metadata pins the baseline; the channel publisher
pins the experimental replacement payloads. The source manifest is
`f8-infinityx.json` on the contributor release. Discovery finds it without an
embedded Infinity-X source target. The new UI roles and boot hooks require the
updated app; subsequent compatible channel revisions do not.

Validation is static/build-time: exact image/donor hashes, retained classes and
non-DEX contents, DEX checks, resource values, preparation failure boundaries,
package/source model tests and full debug APK staging integrity. The phone was
disconnected during this port. Physical hinge/gesture behavior, visual layout,
AOD and persistence across guest re-entry are not yet verified on Infinity-X.
