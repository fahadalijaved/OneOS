# Closed root link: concrete OneOS app placement

Read-only mapping of the actual `firmware/oneos-pr/OneOS` checkout. No clone,
manifest, Gradle, script, source-set or asset was modified; no build, native,
Android or device workflow ran. This is the next full-app integration plan, not
an already packaged feature or an instruction to run legacy takeover.

## Smallest full-flavor source placement

Use `app-android/app/src/full/java/com/fahadali/oneos/core/root/` for these six
actual Java sources from `compat/android/com/fahadali/oneos/core/root/`:

- `RetainedRootSession.java`, `RetainedRootSessionSpawn.java`;
- `RetainedRootCommand.java`, `RetainedRootProtocol.java`;
- `ClosedRootLinkProtocol.java`, `RetainedRootHostService.java`.

They keep their existing package and package-private boundaries; their package
does not require placing them in the `:core:root` module. The app already links
that library. Standard full source placement needs no new sourceSets or module
flavors. Putting these sources in `core/root/src/main` would also put the new
root producer into Probe: that library is shared by both editions. No AIDL,
hidden-API projection, JNI loader or `jniLibs` entry is needed for this code.

Merge the accepted service declaration into
`app-android/app/src/full/AndroidManifest.xml`, alongside `PrepareService`, with
the exact fully qualified class and `exported=false`. Leave main/Probe manifests,
current UI, lock gate, guards and existing launch behavior unchanged. This does
not activate the host profile or install a module.

## Native asset and the missing actual installer

Prefer a dedicated full-only asset
`app-android/app/src/full/assets/root/oneos_retained_root_session`. It is an
executable asset, not a shared library. Build its authored C/header with the
selected API31 ARM64 static-PIE recipe; pin the actual output size/hash in full
BuildConfig fields and validate the actual packaged bytes. Do not substitute an
older helper or treat source review as a native build. The existing
`switcher/native/build.sh` builds other helpers with Linux NDK commands; it does
not build this component and must not supply an assumed artifact.

The required installed location is fixed by actual `RetainedRootCommand`:
`/data/local/tmp/oneos/bin/oneos_retained_root_session`. Merely packaging it or
adding it to `sessionScripts` does not install it there. Actual root `do_receive`
writes `$STAGE/$name`; current name admission excludes this helper and file_mode
does not mark it executable. `AppAssets.files` also demands exact equality with
`RootScript.SCRIPTS`.

The minimal next installer is therefore a separate fixed controller-install
operation through the existing root setup path: add one bounded DATA verb and
argument validator to `RootScript.kt`, a fixed-target root-script handler, and
a full-only `AppAssets` reader/setup caller. It must stream only the pinned
asset, check actual byte count/hash and root/nonlink ownership, install atomically
at that fixed bin target with the selected executable mode, and reject unsafe
active/uncertain replacement. It accepts no arbitrary path or executable name.
Root-script BuildConfig pins and applicable script/setup tests must follow the
actual changed bytes. This installer is not implemented by the placement report.

This full-only asset choice avoids changing all session script/name sets and
per-image packages. The alternative `switcher/assets` route requires coordinated
`sessionScripts`, `RootScript.SCRIPTS`, root SCRIPTS/modes/destination handling,
content-addressed lists and stage checks; adding a file alone fails the explicit
unknown-asset check. Neither route can simply repoint the current launcher hash.

## Invocation stays separate from detached LAUNCH

Actual `LaunchJob` calls `RootVerbs.run(...RootScript.Verb.LAUNCH...)` after switch
gates/commit. `RootVerbs` selects no input for LAUNCH, and `oneos_root.sh` starts
the detached `nsenter/setsid` switch shell. Its line-oriented RootReply/RootShell
completion is not the new binary OFFER/control/pidfd channel.

Keep that call site intact. The closed path is already real in the accepted
sources: genuine host binding calls BEGIN on the explicit service, the service's
owned worker invokes `RetainedRootSession.begin`, and its private Spawn uses
`ProcessBuilder("su", "-c", RetainedRootCommand.build(...)).start()`. The command
verifies and execs the same opened image via fd3; native consumes that fd before
opening other descriptors. Do not route its binary stream through RootReply or
add a UI-ready Boolean. Native/Session ownership still cannot admit a guest or
host credential operation. The protected host profile and installed APK/native
identities must match the actual selected app build.

## Bootphase1000 is not app unlock readiness

The accepted manifest fragment leaves `directBootAware` at its false default.
The actual full application class is `.ui.OneOsApplication`. Its complete
`onCreate` calls only `super.onCreate` and AppCompatDelegate's system night-mode
setter; it does not directly open SessionPrefs. SessionPrefs separately uses
ordinary application-context `getSharedPreferences("oneos", MODE_PRIVATE)`.
This disproves a direct CE-pref read in that initializer, not CE safety of all
library initialization or the eventual merged manifest/providers.

Consequently a normal bootphase1000 capture cannot assume this service resolves
while user0 CE storage is locked. Do not silently set directBootAware=true and
call that closed. The smallest conservative startup change is an actual
user0-unlock admission owner after retained host capture: register the genuine
unlock callback before the final current `UserManager.isUserUnlocked` sample,
handle either ordering once on canonical main, recheck source/profile/package,
and issue the single bind/startup attempt only after unlock. No bind failure or
timer becomes a retryable no-process claim. If pre-unlock service startup is
instead required, its manifest and AppCompat/merged-provider initialization need
their own source-supported direct-boot contour first. Neither change is made here.

## Build/API boundary

Actual clone configuration is compileSdk37/minSdk31/targetSdk36, JDK21,
Gradle9.8.0, AGP9.4.1 and Kotlin2.4.21. The new code uses public Android Binder,
Service, LocalSocket, ancillary descriptors, ParcelFileDescriptor and Os APIs;
SDK37 component compilation is not proof of every minSdk31 runtime path (notably
the selected Parcel framing API). Keep the initial runtime profile explicit and
run full-app API/lint/manifest checks before claiming general minimum-API support.
Kernel pidfd, SELinux/root access and peer behavior remain runtime requirements.

Prior bounded local readiness found JDK21/SDK37 but not matching Gradle9.8/AGP9.4/
Kotlin2.4 caches at the locations checked; that cache observation was not refreshed
here. The actual clone still requests those versions. Do not downgrade them or
invoke the wrapper merely with --offline: missing wrapper bootstrap can download
before Gradle sees that flag. Full `oneosFiles` also requires actual selected
overlay directories and checked-in package-list hashes even when set bytes are
downloaded instead of embedded. No such full packaging closure is established.

Next code chunk: full-only six-source/manifest placement plus fixed native asset
pin/installer and unlock-gated source-owned invocation, followed by actual
matching-toolchain Full packaging/merged-manifest review. Probe or standalone
component/JDK checks cannot substitute for that evidence. No guest integration,
security acceptance or phone action follows from this mapping.
