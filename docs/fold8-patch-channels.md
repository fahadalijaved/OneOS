# Device patch channels and contributor guide

The ColorOS pre-boot page on Galaxy Z Fold8 has a patch channel choice. Stable
uses the APK-pinned upstream payload list. Experimental loads a small manifest
from `thatjoshguy67/OneOS-files`, release `fold8-experimental`, named
`f8-n6-global-f8.json`. (Pixel has no channel until a Pixel channel file is
allowed: its set has no file a channel may replace yet.)

**What a channel may replace** (merge of pull request #37, 2026-11-07): only
`Fold8SystemUI.apk` and `GlobalVerifiedAddons.tar` (`PatchManifest.REPLACEABLE`
in the app, `REPLACEABLE` in the publisher). Every other file of the set, above
all `guards.txt` and the guarded jars and binaries it pins, payload images, dex
files and archives root unpacks, must have exactly this app's hash, or the app
refuses the manifest. So a channel can never vouch for its own guards, and a
manifest made for an older OneOS is refused after an app update until its
contributor publishes it again for the new version. The addon archive may hold
only regular files and folders with plain relative names (no links of any kind):
`fold8_coloros.sh` checks its listing before root unpacks it.

Choose That Josh Guy's patches (Experimental) or tap **Check for patch updates**
to fetch the current experimental manifest. Stable also has an update-check
button: upstream has no separate stable channel manifest, so it checks the
official OneOS release and reports whether this app's own patch list is current. Apply changed payloads through the existing Update/Repair flow before
booting. Selecting a channel never modifies the running guest. Staging refreshes
an experimental manifest before touching the stage, downloads missing files,
and checks their size and SHA-256. A failed refresh keeps the previous selection
and cached manifest. An already prepared experimental stage can boot offline.

Stable ColorOS uses upstream's complete Find N6 payloads and a pinned empty addon
archive, which applies no custom overlays. Experimental currently replaces its
SystemUI and addon archive with Josh's Fold8 builds.

## Building a patch

Start from the exact system image named by the target's `Images` entry and the
matching upstream package set. Keep your source changes in a fork of OneOS;
keep firmware, decoded APKs and built binaries under ignored local `out/`
folders. Submit source patches and build instructions for review, rather than
committing OEM APKs or images. Do not copy a binary from another image version
and change its hash to make it pass.

Use the existing builders and patchers as starting points:

- `scripts/make-fold8-coloros.py` and `switcher/patches/fold8-coloros/` build the
  ColorOS SystemUI/hinge integration. The global-image `--into` mode adds the
  patched SystemUI and angle relay to an already populated, guarded base set.
- `switcher/patches/fold8-pixel/` and `scripts/make-overlays.sh` contain the Pixel
  and framework patch paths. Read the relevant builder before changing a jar;
  storage, installd and wipe guards must remain intact.
- `scripts/check-dex.py` checks rebuilt APKs/jars for malformed dex structures.
  Passing it does not prove a framework patch is safe or works on a device.

For a ColorOS SystemUI build, install Python 3, Java, apktool, Android SDK platform
37 and build-tools 36.1.0 (the builder allows environment overrides). Populate
`out/base-n6-global` with the verified upstream set and make a separate copy at
`out/my-built-set`, then run from the repository root:

```sh
export ANDROID_HOME=/path/to/android-sdk
export APKTOOL=/path/to/apktool.jar
python3 scripts/make-fold8-coloros.py \
  --base out/base-n6-global \
  --systemui /path/to/exact-global-SystemUI.apk \
  --into out/my-built-set
python3 scripts/check-dex.py out/my-built-set/Fold8SystemUI.apk
mkdir -p out/my-coloros-patches
cp out/my-built-set/Fold8SystemUI.apk out/my-coloros-patches/
cp out/my-built-set/Fold8AngleRelay.dex out/my-coloros-patches/
```

The stock class pins in `switcher/patches/fold8-coloros/classes-global.json` and
the matching patch file must describe the source changes you are proposing.
Keep the builder's refusal on an unknown class or donor image. For a new patch,
update its source hunks and reviewed before/after pins together; never bypass
the checks or directly replace strings in a compiled dex.

Only include changed payloads in the override folder. The registered set's file
names are the protocol: `Fold8SystemUI.apk` for the example above, not an arbitrary
new filename. Framework/native changes must include the corresponding source
patch and a repeatable build command. Hash verification proves file identity,
not that the guards still behave correctly; review and test those changes too.

### Prepare and publish

Put only changed payloads, under their normal names, in an override folder:

```sh
python3 scripts/release-patch-channel.py \
  --set n6-global-f8 --revision coloros-2 \
  --overrides out/my-coloros-patches --out out/coloros-2
```

Review the generated JSON, then repeat with a fresh output folder and `--publish`
to upload to the fork. The script uploads immutable
hash-named payloads, verifies their public downloads, then replaces the small
channel manifest. Other testers get it through Check for patch updates without
installing another APK. Unchanged payloads continue to use upstream's sources.
The publishing account needs write access to the fork; users need no credentials.
Fork OneOS-files or create a public GitHub repository, authenticate the GitHub
CLI with `gh auth login`, and register that repository as described below. The
publisher creates the configured prerelease if it does not exist. It never
uploads a contributor’s binaries to upstream unless that is their registered
repository.

### Test before sharing

Run the host checks from the repository root, and the Gradle checks from
`app-android` with the Android SDK configured:

```sh
python3 scripts/test-patch-channel.py
python3 scripts/test-fold8-coloros.py
python3 scripts/test-verified-overlays.py
cd app-android
./gradlew :core:model:test :core:root:testDebugUnitTest --tests '*StageAuditTest'
./gradlew :app:assembleFullDebug -Poneos.series=fold
```

Use the appropriate series for another device. A normal build downloads package
payloads at staging time; `-Poneos.packSets=true` is an explicit local test build
and requires all matching built files. Package sizes and sources for the normal
build are recorded in `packages/sizes.txt` and `packages/remote.txt`.

On your declared target device, select your source, check for updates, then use
Update/Repair while retaining the existing system image and data. Verify the
staged file hashes, the behaviour your patch changes, return to One UI, and a
subsequent boot. Switch back to Stable and verify the reverse path as well.
Record the device/model, firmware, image hash, manifest revision and results in
your contribution. Do not describe another device as tested from compilation
or a successful APK installation alone.

Keep old hash-named release assets available for users with cached manifests.
To roll back, publish a new manifest revision pointing to the earlier verified
hashes; do not replace an existing hash asset with different bytes. A malformed
manifest or a failed download must be fixed at the source, not by disabling the
app's checks.

## Adding contributors and devices

`app-android/packages/patch-sources.json` is the shared registry used by the app
and publisher. Add a contributor with a unique id, display label, GitHub
repository, release tag, and explicit targets. Each target names a supported
profile, image, package set and exact raw image hash. For example, a contributor
for the already supported Z Fold7 could declare:

```json
{
  "id": "another-contributor",
  "label": "Another contributor's patches (Experimental)",
  "repository": "another-contributor/OneOS-files",
  "tag": "experimental",
  "targets": [{
    "profile": "f7",
    "image": "coloros17-findn6",
    "set": "n6-f8u",
    "imageSha256": "eec6c10581657b17f3164d6f964c749b351c4a7ec07233840da5f6a0ce28a47c"
  }]
}
```

The picker automatically lists all contributors registered for the current
device and OS, below its checks grid, with the device name in the heading.
No UI, downloader or staging-engine edits are needed for an existing package
schema. Registering a new trusted source requires one APK release; that source's
subsequent compatible payload updates do not.

Publish with `--source another-contributor --profile f7 --set n6-f8u` and the
existing revision/override/output arguments. `--profile` is required when the
source supports several devices using the same set. Manifest assets are named
`<profile>-<set>.json`, so one contributor can publish different patches for
devices sharing an image. Downloads remain deduplicated by content hash, while
manifest caches and saved choices are scoped by contributor/device/system.

Packaging rejects unsupported device/image/set combinations and malformed
registry entries. Runtime validation also checks the image hash and only trusts
the selected contributor's repository plus upstream. Other contributors cannot
be substituted through a manifest. Keep sources narrowly scoped; registering
a contributor for one device does not enable it on any other device.

The manifest is trusted from the selected fork over HTTPS, then each payload is
verified against its manifest hash. The app enforces the exact system image,
supported file names, download repositories and receive-size limits. Root and
session scripts remain pinned in the APK. New file names, roles, system images,
script changes, and any change to a file outside the replaceable two (a guarded
jar, `guards.txt`) still need an APK update reviewed upstream; the publisher
refuses them.

## Adding a new payload name or system

The manifest format deliberately cannot invent new bind targets or scripts.
For an existing device/image, a new payload name needs a reviewed app change to
`PackageSets.kt`, the matching `packageSets` build entry, root `set_files` and
its runtime consumer. Add SHA/guard fixtures, update the relevant series list
if a new set is introduced, and run the staging audits. New device/image pairs
also need a model profile choice and matching root profile/image/set tables.
Ship that schema once before publishing manifests that use it. Scripts and the
root helper remain APK-pinned, so a script change always needs an app release.

Stable ColorOS adds one empty, immutable addon archive (one empty
`overlays.list`), mirrored in OneOS-files with the other set files. It applies
no overlays; all upstream payloads keep their upstream hashes. Experimental
payloads remain hosted by their registered contributor.
