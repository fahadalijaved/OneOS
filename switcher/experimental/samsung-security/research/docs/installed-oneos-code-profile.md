# Observed installed OneOS code profile

## Current 0.4.59 / code 85 baseline

The November 8 read-only snapshot matched the supported Samsung model, build,
API 37, SELinux Enforcing, and both held Samsung framework and services hashes.
The installed OneOS APK changed to 0.4.59, code 85. The captured 42,820,359-byte
base APK matches the phone's `af557d9b…` hash. SDK verification confirms the
same v2 signing certificate as the prior code 74 APK. The exact source commit
remains unassigned.
[Host snapshot](../out/live-stage1-host-code-snapshot/r-c48877e7/receipt.json)
· [APK acquisition](../out/installed-oneos-current/r-7b4bd2c2/receipt.json)
· [SDK verification](../out/installed-oneos-code85-sdk-readback/r-d48a2e7f/readback-receipt.json)

The current stock OneOS stage marker also reports code 85 and selects the same
`s-ultra-8850 / coloros17-findx9u-in / x9u-in-sultra` profile. All 49 rows in its
live `files.sha256` match the installed APK's 19 script rows and 30 selected
payload rows. The marker and manifest hashes match before and after the three
named JAR hashes. These are separate file observations, with loaded classes and
service ownership still open.
[Current marker](../out/live-stage1-stock-stage-selectors/r-59a18aee/receipt.json)
· [Current 49-row binding](../out/live-stage1-stock-stage-binding/r-ab3223b1/receipt.json)

The staged framework and services JAR hashes still match code 74. The staged
Oplus services JAR changed to `d02092bc…`, and its acquired bytes match that
hash. Only `classes3.dex` changed inside it. The raw DEX comparison found the
same member declarations and core reference tables. Of 47,160 coded methods,
only `ZenModeManagerExtImpl.handleZenModeChanged()` changed instruction words or
frame fields in this comparison. Try and debug preservation were outside this
check. The current guard, telephony and Samsung camera selectors also differ
from code 74.
[Oplus JAR acquisition](../out/installed-oneos-current-staged-code/r-231afab8/receipt.json)
· [DEX instruction and frame comparison](../out/installed-oneos-current-staged-code/r-231afab8/classes3-comparison.json)

The actual code 85 switch still stops the host zygotes at lines 1118 and 1126,
kills `system_server` at 1161 and suppresses host zygote restarts at 1173.
It prepares the guest at 1260 and starts it in a private mount namespace at
1592. Return still kills the guest system server, restarts stock zygote and
waits for a new Samsung `system_server` PID. Code 85 adds watchdog discovery,
composer stop/start and separate resource-cache work. Those changes preserve
the observed teardown and recreation boundary. The stock switch cannot serve
as a retained Samsung authority for this profile. A modified architecture
still needs the live owner, display, storage and return evidence.

## Historical 0.4.57 / code 74 baseline

The acquired app is **com.fahadali.oneos0.4.57, versionCode74, release/full,
DEBUG=false**. The root-owned staged preparation identifies
**s-ultra-8850 / coloros17-findx9u-in / x9u-in-sultra**, also code74. Its
49-row file manifest exactly equals this APK's19 script rows plus30 selected
package rows. The three acquired staged JARs match those selectors. This closes
the named app→preparation→code-file binding for the recorded observations;
it does not establish which code is loaded in a running guest or any security,
native service, credential, user-serial or mount-owner acceptance.

Root acquired one base APK with no splits in the package-path result:
42,790,067bytes, SHA256
`9b5595458766db1b0d08bff8037ae2de7351a321e808f777d494e653eb2b92d5`.
Remote before/after hashes and PC bytes matched. Static AAPT2 decoding gives
minSdk31, targetSdk36, compileSdk37. Compiled BuildConfig constants independently
agree on package/version/build type/flavor. AGP metadata says9.4.1; VCS metadata
says NO_SUPPORTED_VCS_FOUND. **An exact Git commit cannot be assigned from this
APK.** The captured0.4.55/2a5f cohort and current0.4.57/1f2c source remain separate
reference inputs, not names for this installed binary.

The APK has3,259 unique entries and five ordinary039 DEXs. A bounded cached
static reader inspected six selected bootstrap/asset classes without loading
APK classes, compiling anything, invoking native code or executing scripts.
RootScript.Layout's actual static constructor sets PHONE to stage
`/data/local/tmp/oneos`, legacy `/data/local/tmp/lineage_stage`, shell
`/system/bin/sh`, proc `/proc`, UID0 and owner0:0. The default launcher selects
that PHONE layout. AppAssets.rootScript reads root/oneos_root.sh and verifies
exactly82,529bytes/SHA04eace4b… before returning it. Its launcher builds a
hash/length-bound bootstrap for the stage's bin/oneos_root.sh. These are compiled
code facts, not an observation that the bootstrap ran during this audit.

Actual packaged root and session scripts agree on the stage. A nonempty
ONEOS_TEST_ROOT is expressly refused when UID0. The switcher requires staged
system.raw and guarded artifacts; preparation creates rootfs and attaches the
image read-only before mounting it there; guest-start uses that rootfs and
pivots in a private mount namespace. Thus absence of named files below rootfs
while observing ordinary One UI does **not** prove absence of a prepared image.
The persistent preparation is selected by .oneos_stage and its manifests.

Packaged script hashes distinguish this binary from source snapshots. Compared
with current1f2c files, guest_start, return_to_oneui and bridges are byte-exact.
Switcher and guest_prepare differ only at observed full-line comment text;
their non-comment lines compare equal. Older0.4.55 switch/prepare/return bytes
differ; guest_start remains equal. This limited comparison is not a whole-repo
reproducible-build or source-commit proof.

There are19 content-addressed bundled session files, nine package-set manifests,
an index and remote mapping. No named Python/smali/patch source, JAR entry or
ZIP payload among those19 files is packaged. The selected JAR entries are absent
from the APK; only their selectors are supplied. Root therefore acquired actual
staged code instead of substituting original donor code:

| Stage file | Bytes | SHA256 |
| --- | ---: | --- |
| services_patched.jar | 44,699,364 | `efb45f5f061838431387f9c34e4d5c72504a963d0d5bd37f3c4d0ae043854671` |
| framework_patched.jar | 52,377,761 | `5cb16a378d41301c2d41d4653f7dc63c54b732516353f331f0316e2c237f6246` |
| oplus-services_patched.jar | 30,364,137 | `a854468fec404a8950f8f3c651f869f19ded098bb244fbef26880c2ece141fa8` |

All three came from explicit /proc/1/root stage paths as root-owned regular0644
files. Per-file size/device/inode/mtime and remote hashes stayed equal before
and after each read; PC bytes matched. The four profile-manifest hashes were
also rechecked in the init view around all three acquisitions. Earlier manifest
collection used a KSU /data view without per-file namespace/stat-after checks;
that earlier observation remains qualified rather than rewritten as atomic.
Before/after equality is still not an atomic snapshot or proof of loaded code.
The staged services/framework/oplus archives contain4/6/3 ordinary039 DEXs,
respectively; no041 slicing or container rebasing is needed for these inputs.

The installed prepare script verifies guards.txt code hashes at lines80–103,
then binds staged services at1216–1218 and oplus-services at1282–1285. Framework
selection is conditional at1329–1331/2015–2017. The same script explicitly binds
staged data trees over host-facing paths before guest startup; source path
spelling alone therefore cannot identify the physical data authority. Actual
mounts and applied branches were not observed by this static audit.

The app-data bridge has a concrete narrower contract. bridges.sh lists14 pairs,
including host /data/data→staged data/user/0, user/user_de, media, app/app-staging,
profiles, sandbox/rollback and resource-cache. Preparation checks init namespace,
imports the list and requires core pairs; each existing host target must match
the staged source's device/inode after binding or preparation refuses. It then
binds the staged data root into guest rootfs/data and makes that mount private.
Guest-start's data/data and data_mirror binds are best-effort. No ginstalld name,
new installd publisher or installd socket handoff appears in these packaged
session/root assets. Return baselines canonical installd's service-manager PID
and removes the bridges before host restart, refusing remaining mounts; that
is not Binder/session generation or pending-work drain evidence.

Preparation also generates ensure_app_storage.sh for the guest: numeric UIDs
from its packages.list determine CE/user_de and external app directory owners;
many per-directory failures are ignored and the helper exits0. The background
loop sleeps10seconds, waits for sys.boot_completed=1, runs that helper and may
refresh the guest launcher. The spawn log is not completion acknowledgement.
This shows the installed code already separates guest app-data paths when its
mounts apply. Actual host installd PID/mount namespace/root/native identity,
applied binds, user-storage/FBE authority and helper termination remain unproved;
no guest packages.list or application data was read here.

The subsequent narrow staged-byte investigation has already identified
com.android.server.pm.OneOSInstalldProxy.asInterface and createUserData in the
actual efb45f5f services JAR. The peer's immutable static receipt is linked in
the inventory. Thus absence of a new shell installd alias must not be read as
absence of a guest Binder adaptation. Its exact routing/ABI and the remaining
storage/user methods belong to the staged-code analyses, separate from the
packaged shell bridge and this profile binding.

For UserDataPreparer, UserController, UserManagerService, StorageManagerService,
Installer.prepareUserStorage, CE unlock and user.id serial checks, **the APK
contains selectors, not the patched guest method bodies**. Guard comments name
storage/installd/nousers/wipesecrets and gvld; those labels do not prove the
implementation of any particular method. Exact methods in the acquired staged
JARs must be queried before attributing original donor retry, wipe or serial
behavior to this preparation. Power/Trust own those narrow body checks. No
original guard producer or patched method was executed or regenerated here.

The four inspected manifests have code/profile-only producer contracts:

| File | Producer fields | Bounded read profile |
| --- | --- | --- |
| .oneos_stage | canonical schema/versionCode/profile/image/set/created; v1 omits set | valid v2 max243B;512B cap |
| files.sha256 | sorted SHA256+approved flat artifact basename; image bytes excluded | actual49rows/4,246B; APK maximum5,841B;8KiB cap |
| guards.txt | static guard comments and code SHA256/basename rows | selected1,683B, hashaf6decb3…;4KiB cap |
| system.raw.id | image size/SHA and device:inode:size:mtime | actual113B;1KiB cap; **not Android user.id/serial** |

None of these producer fields contains a license, account token or credential.
Unknown-hash guard comments should not be exported wholesale; the recorded
guard file matches the exact APK selector. No session.env, app private prefs,
user records, credential/enrollment material or raw system image was read.

Root's read-only acquisition receipts and this worker's PC-only manifest,
asset/DEX and file-binding evidence are pinned in the paired inventory. This
worker issued no ADB/phone command. No APK, script, JAR or native code was run,
and no app, staged file, setting, rootfs, private data or original source was
rewritten. Staged-file identity is now concrete; effective method semantics,
actual loaded guest/mount/native state and all runtime security outcomes remain
separate requirements.
