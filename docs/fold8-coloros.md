# Fold8 ColorOS port

Contributed by thatjoshguy67 (pull request #1) and ported into OneOS 0.4.14.
It brings the fixes he tested on SM-F971B / h8q / SM8850 with the Find N6
ColorOS 17 image (`coloros17-findn6`, PLP120_17.0.0.109(CN01)) to the `f8`
profile (OneOS's Galaxy Z Fold8 profile since 0.4.10) as its own package set,
`n6-f8`. The Z Fold8 Ultra and every other phone keep their sets. It does not
widen any hardware match, enable a new image, or change the screen-lock or
OneLineage startup requirements.

Follow-up work, exact tested app/source versions and remaining limitations:
[ColorOS session handover and Fold8 personalisation](patch-notes/2026-10-31-coloros-fold8.md).

## Included

- Cover camera bounds centered on its 1248 px panel, restoring status-bar width.
- Larger cover Quick Settings tiles with stock spacing for two swipeable rows.
  Crossing sw600 refreshes the QS view and text-density cache, including the
  existing font scale. The inner screen retains its original sizing.
- Samsung sensor 65686 read as degrees despite its maxRange metadata of 1.
  When SystemUI cannot register it, a guest system-UID helper relays timestamped
  angles. A single reader per provider rejects stale frames and stops with
  the provider; the producer exits when the guest zygote disappears. Android
  sensor 36 remains the fallback.
- The experimental Android unfold gates previously tested on this phone.
  These are not a complete implementation of OPPO's home/lock-screen and
  closing animations. The wallpaper callback reports merged window geometry
  only after Canvas posts a frame, fixing the observed multi-second blank
  display during panel changes.
- Original donor AOD, UMS and Instant APKs. UMS and Instant supply the home and
  lock-screen widget catalogues; their CN category names remain Chinese.
  CardService is already in this image and is not duplicated.
- Native lock-screen-linked Workshop AOD on either panel and a 0.12 doze
  brightness fallback. Native libraries are repaired only for the exact stock
  AOD APK. A later user-updated AOD is preserved.
- Stock Find N6 Pocket Studio and flexible-freeform feature declarations,
  scoped to Fold8 / Find N6. The container does not scan the stock
  `my_stock/etc/extension/com.oplus.oplus-feature.xml` that enables them.
  Restoring them selects the native multitasking path for the split-screen
  gesture and taskbar integration.
- Launcher taskbar feature-provider row and one-time taskbar/AOD defaults.
  Later user choices are retained. Live Alerts, fold animation, separate
  wallpapers and haptic-channel feature declarations are restored in the
  guest's feature configuration. A haptic flag does not provide OPPO hardware.
- Missing Play services and Play Store binaries copied from One UI before
  shutdown, with arm64 library directories derived from the same APK splits.
  These are guest-only mounts; host app/account data is not copied. Local
  network permission is left to the user rather than granted automatically.
  Since 0.4.16 this is `guest_google.sh`, for every ColorOS set on every
  phone ([coloros-google.md](coloros-google.md)).

The base is OneOS's own Find N6 set (`n6-f8u`, rebuilt 2026-10-25 as r50),
which already carries the storage, installd, power, sysrq, weaver, biometric,
gatekeeper, FRP, APEX-install, app-id and user-creation guards and the guest
vold as gvld; the builder checks guards.txt for all of them instead of patching
services.jar again (the pull request's 0.4.7 base needed that).
A stage containing old guest app ids 10000–14999 is refused before shutdown;
prepare fresh guest data rather than bypassing that refusal.

## Build

OEM APKs and generated package files stay outside Git, like the other OneOS
sets. Required inputs:

1. The base files matching `app-android/packages/n6-f8u.sha256` exactly.
2. Unmodified Find N6 `SystemUI.apk`, SHA-256
   `e6bf0e49649dc82117e7b9584c13dbcf737183d17c461cd6edcedcc127165f7e`.
3. A donor directory containing `Aod.apk`, `UMS.apk` and `Instant.apk` from
   the firmware above. The builder checks their full hashes before use.

```sh
ANDROID_HOME=/opt/android-sdk ONEOS_BUILD_TOOLS=37.0.0 ONEOS_ANDROID_PLATFORM=android-37.2 \
APKTOOL=mysticgsi/tools/apktool/apktool.jar \
python3 scripts/make-fold8-coloros.py \
    --base out/overlays_n6_r50 \
    --systemui out/fold8_donor/SystemUI.apk \
    --donor out/fold8_donor \
    --out out/overlays_n6_fold8
```

`--write-pins` writes `app-android/packages/n6-f8.sha256` from the build, for a
reviewed pin change (the first OneOS build did that once); without it the build
must match the checked-in pins. The original SystemUI comes from the Find N6
image itself (`/system/system_ext/priv-app/SystemUI/SystemUI.apk`); the donor
APKs from the firmware's `my_stock` partition (`app/Aod`, `priv-app/UMS`,
`app/Instant`).

Use Python 3.11+, apktool 3.0.3, Android build-tools 36.1.0 and a JDK capable
of `--release 8`. The builder creates `out/overlays_n6_fold8`, refuses an
existing output, and verifies every output against `n6-f8.sha256`. Changes in
compiler/tool output require an explicit reviewed pin update. It never
silently regenerates trusted hashes. Normal Gradle packaging then includes
this set, with the usual root/script/list pins and receive limits.

`fold8_coloros_systemui.py` applies `fold8-coloros/systemui.patch` only to
known class hashes. All classes are checked before any write; a complete
rerun is idempotent. New helper smali and their Java sources are beside the
patch. Only the affected dex entries are replaced; manifest, resources and
all other entries retain their original bytes. The original APK signer block
is retained as system-partition certificate metadata, **not as a valid OEM
signature for changed content**. This APK is a root-mounted system overlay,
not an APK for normal installation.

## Validation and remaining device check

```sh
python3 scripts/test-fold8-coloros.py /path/to/pristine/apktool/SystemUI
python3 scripts/test-google-snapshot.py
python3 scripts/test-permission-cleanup.py
python3 scripts/check-dex.py out/overlays_n6_fold8/Fold8SystemUI.apk \
    out/overlays_n6_fold8/services_patched.jar
cd app-android
./gradlew :core:model:test :core:root:testDebugUnitTest
```

The Python tests cover image/profile isolation, missing safety guards,
invalid Google snapshots, exact patch application, idempotence and atomic
refusal on class drift. The Kotlin tests cover the Fold8 model, set and root
staging agreement, and retain the screen-lock BLOCK test. Root script tests
expect GNU command semantics (not macOS's BSD `stat` and `find`).

The individual UI fixes were tested in the earlier modified ColorOS session;
this integrated source build still needs a fresh launch and fold/unfold/AOD/
widget/Play Store check on the device. No phone installation or OS switch is
part of this source change. Runtime installation failures are recorded in
`$STAGE/fold8_runtime.log`, and hinge producer errors in the guest's
`/data/local/tmp/oneos-angle.log`.

Local source-port verification: full app Kotlin compilation succeeded; 197
model tests, 106 root tests and four Python regressions passed (one additional
root test skipped for absent run logs). The 33 shell staging tests used local
GNU stat/find compatibility shims and simulated free space confined to the
fake test root; production checks were unchanged. A clean package rebuild
reproduced all 27 checked-in payload hashes exactly. SystemUI retained all
73,029 original classes plus the two intended helpers, and both patched
SystemUI and services.jar passed the DEX checks.

## First launch on the Z Fold8 (0.4.14) and the fixes after it

thatjoshguy67 ran 0.4.14 on his Z Fold8 and updated the pull request
(commits edb4c05 and 044fe00). Two problems showed up:

- **The Google snapshot stopped the switch** before One UI shut down.
  BusyBox awk rejected the escaped slashes in the native library pattern
  (`/^lib\/arm64-v8a\/...$/`). The library paths are now matched by
  component, and listing or extracting an APK that fails stops the snapshot.
  APKs with no native libraries get an empty native manifest, which
  verify_google accepts. The AOD library repair uses the same matcher.
  `scripts/test-google-snapshot.py` (renamed in 0.4.16) covers these cases.
- **No foldable layout.** The OneOS port called `fold8_coloros.sh prepare`
  before guest_prepare.sh mounted its overlay on the guest's system_ext,
  which hid the SystemUI bind. It now runs after that overlay. Also, the
  split-permission cleanup unmounted every bind on a permissions XML,
  including the ColorOS feature list guest_prepare.sh binds earlier. It now
  removes only its own `oneos_split_*.xml` binds. The feature list
  additions had been missing from every ColorOS session, not only on the
  Fold8: fold, multibits dimming, 5G and the CN Wi-Fi paths.
  `scripts/test-permission-cleanup.py` covers both points.

The pull request keeps an existing installation with old app ids
(10000-14999) running without the Google binary mounts. 0.4.15 refused such
a stage before shutdown. Since 0.4.16 it starts without One UI's copies, as
the pull request did ([coloros-google.md](coloros-google.md)).


## Continuous posture and animation update (local build 0.4.19-fold8-hinge3)

Fold8 / `n6-f8` now defaults to a guest device-state file that keeps Samsung's
lid-controlled state 0 (closed), state 1 (tent), and state 3 (open), and adds
state 2 (half-open) when the lid is open and vendor sensor 65686 reports
15–165 degrees. The exact sensor name and string type were read from the
connected SM-F971B. The shipped ColorOS posture mapping already maps 2 to
HALF_OPENED. The display-layout generator reads the same prepared state file,
so state 2 retains the inner panel. A missing sensor falls back to the
lid-only open state. Explicit `ONEOS_GUEST_DEVICE_STATES=vendor` retains the
previous behavior; `oneos` retains the earlier two-state property config.

The Z Fold8 Ultra's `n6-f8u` gets the same device-state file and live posture
since 0.4.21: its own vendor file has the same lid states (0 CLOSE, 3 OPEN) and
the phone has the same sensor. It keeps the Find N6's own SystemUI (the Fold8
SystemUI patches are measured for the Fold8's cover display), so it gets the
half-open posture, not the Fold8's reveal animation.

The guest fold-line setting now follows live posture for `n6-f8`, retaining
`ONEOS_GUEST_POSTURE=flat` as an explicit opt-out. Other profiles and package
sets keep their defaults. Runtime startup removes a previous guest's angle
frame before waiting for the new producer, and enables the two unfold
resource gates inside the guest before SystemUI is restarted.

Opening and HALF_OPENED state 2 were confirmed on-device after a normal
keep-data preparation and cold guest start. The first opening reveal used
only the left half of the inner display. The reveal controller now refreshes
its internal display information whenever it computes overlay layout bounds,
rather than retaining the geometry from SystemUI construction. Its original
display selector, rotation handling and panel choice are retained.
`Fold8RevealGeometry` falls back to the original cached list if a fresh lookup
fails. The owner confirmed the corrected reveal fills the entire inner
display; logs reported 2448 by 1848 in natural rotation.

The native progress provider already sent START_CLOSING and FINISH_CLOSED.
The reveal overlay created for FOLD held its reveal amount at 1, making it
fully transparent throughout closing. It now follows supplied progress for
both directions while retaining initial FOLD=1 and UNFOLD=0 values and native
finish/removal behavior. The owner confirmed closing animation works and
half-folded apps remain usable. These animation changes were verified as
session-only SystemUI mounts before packaging; the final packaged update
still requires a cold guest start check. These updates must travel
through the app's normal package preparation: editing staged scripts and
updating only files.sha256 failed the app’s stage-integrity check during the prototype attempt.
