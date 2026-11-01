# ColorOS session handover and Fold8 personalisation

## Version and validation baseline

These changes were developed and tested on a rooted Galaxy Z Fold8 running the
Find N6 ColorOS 17 guest. The OneOS app used for the accepted device tests is
**0.4.31-fold, versionCode 48**, with locally rebuilt session assets and DEX pins.
The final installed APK SHA-256 is
`dedb5fcc5f76eac4b2b3a89ecb3cfc30739c7fc8a2639a799b28616e96abd9a9`.
It is a customised build, not an unmodified upstream release.

The original development checkout was commit `2bce201`, whose Gradle source
still declares **0.4.13, versionCode 26**. This source port starts instead at
upstream **0.4.34, versionCode 51**, commit
`4bf9d5aec7c7072af0fa90dcf00e86831fd4bb7f`. It does not roll back upstream's
newer guest safety guards, package sets, Google handling, camera, Bluetooth or
reporting work. The earlier Fold8 hinge PR (#1) is already merged and is not
being proposed again.

The accepted phone behaviour and the current-upstream port are separate
validation results. The phone has not been replaced with a newly compiled
0.4.34-based full APK. The full release package must be rebuilt with the pinned
package sets, then tested through switch, fold/unfold and return before release.

## OneOS changes overall

- Capture host CPU/GPU userspace requests and per-policy CPU ceilings before
  stopping One UI. Start a guest-session helper and restore requests before
  One UI resumes. Initial activation is deliberately limited to the tested
  `f8` / Find N6 `n6-f8` combination; other phones and guests retain their
  existing path. This is a session-handover fix, not a ColorOS animation tweak.
- Release inherited idle limits only with valid cool readings: skin below
  38°C and GPU below 65°C. Preserve an explicit host power-saving selection;
  unknown restricted host policy fails closed.
- Keep the kernel/vendor thermal services. CPU/GPU caps step through
  80/65/50% at skin 45/47/50°C or GPU 70/75/80°C, with 2°C/5°C hysteresis.
  Missing telemetry prevents initial release; losing it after release selects
  conservative limits. Minimum clocks are never pinned.
- Compare read-back requests with the last value owned by this session.
  Relinquish ownership if another controller changes them, and preserve those
  external values on return. The old CPU-only worker is skipped for this
  combination so two helpers cannot compete.
- Declare the source-built geometry DEX in Gradle, root staging and Kotlin
  script tables together. Normal builds regenerate asset hashes and compiled
  pins; this port does not depend on manually modifying an installed APK.

The diagnosed bad state was CPU ceilings of roughly 1.2GHz and GPU 160MHz,
including cool periods. A live repair restored the normal 3.63/4.74GHz CPU
ceilings and GPU 1300MHz ceiling; the user reported much smoother app switching.
A fresh launcher sample measured 1,523 frames, 104 deadline misses (6.83%),
median 7ms and p90 15ms. Earlier cumulative counters covered a different window
and are not a controlled percentage-improvement comparison.

The helper's saved requests were restored during return to One UI. The matching
app/stage pair passed all 42 staged payload hashes and OneOS showed “Ready to
switch”, 4 of 4 checks. A subsequent ColorOS boot reached the launcher with the
helper alive; its initial skin 42.5°C correctly withheld release. The user then
reported that everything worked well. A separately instrumented cool-release
and full return using this *current-upstream source port* remain to be done.

## ColorOS fixes in general

- Apply `persist.sys.saupwk_test=1` for the session even when the host already
  has the property with a false value. The older presence check could leave
  OPPO's power-key statistics path waiting five seconds for an unavailable
  HAL and stall subsequent input. The existing host persist snapshot/restore
  flow remains in use; `ONEOS_GUEST_SAUPWK=0` still opts out.
- Supply four donor-pinned Flux patchers and a reproducible builder. Clock
  scaling uses the clock canvas, pager sizing uses the measured window,
  depth overlap uses window coordinates consistently, and clock hit testing
  converts rectangles to the raw-touch coordinate space. These are embedded
  window bugs, although the accepted runtime tests are on Fold8 only.
- Supply a guarded, explicit post-scan overlay tool. Original signed apps must
  finish package scanning first. Resolve APK paths dynamically, verify original
  and replacement hashes, restrict mount/signal operations to the guest data
  namespace, and preserve the saved launcher grid across its first unpatched
  startup. No fixed 4×5 setting is imposed on another user's grid.
- The tool also carries the accepted Chrome cached Javaless-renderer workaround,
  retaining a rollback and the preference file's inode/ownership. This remains
  an explicit maintenance tool, not a forced Chrome setting in every build.

The Flux builder and deferred overlay tool are **not automatically activated**
by the default package set. They allow maintainers to reproduce/review the
accepted fixes before adding pinned patched APKs to a release. No OEM APK,
account credentials, user preference dump or personal media is checked in.

## Fold8-specific fixes

- Use the accepted Pixel-equivalent 48dp status-bar dimensions. Centre the
  cover-camera metadata vertically in that bar while retaining its horizontal
  coordinates and size: the tested rectangle becomes `589,11:659,115`.
  This adjustment is restricted to Fold8/Find N6; Android's physical cutout is
  untouched. A donor-pinned SystemUI patcher supplies the separate cover-only
  vertical-padding correction; it requires a reviewed APK rebuild/overlay.
- Compact cover launcher cell spacing without changing grid count, icon size
  or density: spacing dimensions become -8dp/14dp, with original 8dp/30dp at
  `sw600dp`. Keep the inner-screen defaults.
- Retain space for two bottom Quick Settings tile rows on the cover by reducing
  the gesture-zone height from 16dp to 14dp; inner 16dp is retained.
- Personalisation cards use the OEM 4×4 grid in narrow Settings panes and 8×2
  only when the **window** is at least 800dp wide. At 550dp and above, the Flux
  carousel uses a 386dp header and 330×249dp landscape preview cards. Cover
  dimensions stay unchanged. This fixes the collapsed/tall carousel and
  postage-stamp cards without forcing the Settings editor into portrait.
- Resolve the guest SystemUI UID before provisioning only the two depth-mask
  files. Give SystemUI private 0600 files and directory traversal, rather than
  broad directory write access, so applying clock depth can save its masks.
- Reconcile HOME only when Settings holds the fallback role and HOME resolves
  to the OEM launcher. Preserve an intentionally selected third-party launcher;
  restoring this role recovered Quickstep app/Recents transitions on the phone.
- Select the export search path only when both global Search and Mind Pilot
  are installed. Otherwise retain the CN provider path. This does not install
  either app or promise global Search supports landscape.

## Build and test the additional sources

Rebuild the source-owned geometry DEX with Android build-tools 36.1.0 and a JDK:

```sh
ANDROID_HOME=/path/to/android-sdk sh switcher/patches/fold8-coloros/build_geometry.sh
```

Rebuild the exact supported Wallpapers APK (SHA-256
`2e8d489f7ea9c3a16c6258f72fc2d9dd59ad3f6f86d7db67a7f57f21cb384622`):

```sh
ANDROID_HOME=/path/to/android-sdk python3 scripts/make-coloros-wallpapers.py \
  --apk /path/to/original/Wallpapers.apk --out /path/to/Wallpapers-patched.apk
```

Requires apktool 3.0.3, Java and the SDK's dexdump. The output's classes5.dex/classes6.dex DEX
were reproduced byte-for-byte against the accepted phone artifact; other APK
entries are checked unchanged. Its content signature is no longer valid:
use only a reviewed root post-scan overlay, never `pm install` or an unguarded
pre-scan replacement. The cover-padding patcher likewise expects a decoded
supported SystemUI tree and refuses class drift without modifying it.

For the optional overlay tool, a root-owned `verified_addons/overlays.list`
contains `package original_sha256 patched_sha256 filename.apk` per line, with
all hashes reviewed in advance. Provide its SHA-256 explicitly as
`OVERLAY_MANIFEST_SHA256`, plus `STAGE` and `BB`, to
`scripts/apply-verified-overlays.sh verify` or `prepare`. `prepare` must run in
the host stage's preparation phase, before guest apps start; it captures grid
preferences and starts the bounded post-scan worker. Do not use it live against
already-modified preferences or substitute it for OneOS package verification.

The responsive RRO compiles/links successfully; its SHA is updated in both N6
package lists and their test fixtures. Rebuild the affected N6 artifacts with
the release's normal toolchain/key before compiling the full app.

## Source-port validation

| Check | Result |
| --- | --- |
| Kotlin model suite | 207 passed |
| Safety suite | 5 passed; 1 existing fixture skipped |
| Root audits and affected staging/integrity flows | 15 passed |
| Performance handover fixtures | 8 passed |
| Property, camera, responsive-resource and donor-refusal checks | 5 passed |
| Overlay integrity and guest-data path boundary checks | 4 passed |
| Existing Fold8 ColorOS / Pixel regression scripts | 4 / 4 passed; 1 optional pristine-SystemUI fixture skipped |
| Session scripts and nested shell strings | Parsed with dash and Android BusyBox |
| Geometry DEX and rebuilt Wallpapers | No empty try ranges or orphan move-results |
| Wallpapers APK contents | classes5.dex/classes6.dex exactly reproduce accepted artifact; other entries unchanged |
| Responsive RRO | Compiled, linked and pinned in both N6 lists/fixtures |

The broader root run completed 121 tests with one existing fixture skip and
one failure: an audit expectation treated the new DEX as executable. That
expectation was corrected to 0644; all 11 audits and four affected preparation,
pinned-launcher, tamper-refusal and Fold8 staging tests then passed. A full
0.4.34-based APK build and physical switch/return remain release gates. The
combined source-owned geometry helper has been compiled and DEX-checked;
the accepted phone trial used the equivalent separate helpers.

## Remaining limitations / deliberately excluded

- Global Photos launches and sees existing images in the device experiment;
  Google Photos sync was not verified. Its optional replacement, Mind Space
  WeChat-SDK workaround and account-centre compatibility edits remain personal
  donor-specific experiments, not silently bundled global app replacements.
- Photo Agent still rejects its cloud access token with HTTP 401. The temporary
  EU configuration-host trial fixed its independent malformed download URL,
  not authentication. No AI-generation success is claimed.
- Global Search still forces portrait. Per-app overrides did not resolve it.
- Ripple wallpapers are visible. 3D, weather and smart-layout flags alone did
  not establish functioning features; missing/empty downloads remain open.
- The inner-screen depth crop's empty alternate-matrix workaround was accepted
  as a saved configuration trial. A general code fallback is still pending.
- OEM depth saving can change file modes; provisioning is not a claim that
  the OEM save-time chmod has been redesigned.
