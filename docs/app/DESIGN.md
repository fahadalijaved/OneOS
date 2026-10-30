# OneOS app: design and implementation plan

> **Renamed after 0.3.6:** the stage is `/data/local/tmp/oneos` (was `/data/local/tmp/lineage_stage`), its set-aside copies `oneos.old-<epoch>` / `oneos.trash-<epoch>` (were `lineage_stage.old-*` / `.trash-*`), and the session scripts `oneos_switch.sh`, `guest_prepare.sh`, `guest_start.sh` (were `switch_to_lineage.sh`, `master_prepare.sh`, `master_inner.sh`). The app's root script and `scripts/deploy-phone.sh` rename an old stage and its copies when they are idle.

Synthesis of the four design studies into one buildable plan, revised for the
**server-built package model** (project decisions of 2026-10-22). Our own Kotlin
code (nothing of `com.wewaffles.onelineage` is reused; `switcher/README.md`).
Sources: `docs/app/patch-catalog.md`, `docs/app/patch-engine.md`,
`docs/app/compat-safety-logs.md`, `docs/coloros-on-fold.md`, the scripts under
`switcher/assets/`, `switcher/patches/` and `scripts/`, the build outputs in
`out/` and the run-33 logs in `out/logs/run33/`. Commit `3e46795` (run 34).
Where the studies disagree with this doc, this doc is authoritative; the study
docs carry short notes pointing here (§14).

Project decisions this revision applies (they override the studies):

- **App first.** Nothing goes to friends before the app exists.
- **Heavy work on our server, light work on the phone.** The server builds the
  GSI from the OEM OTA (the image build (MysticGSI, not in this repository), MysticGSI), the patched
  framework files (`scripts/make-overlays.sh` + `switcher/patches/*.py`), the
  RROs and APEX payloads, and publishes one signed **OneOS package** per OS
  image (§5). The phone does device checks, the compatibility report, the
  per-phone installd table (§6), download + verify + unpack + stage, the
  toggles → `ONEOS_*` env, switch/return, the log bundle and fix packs.
- **No on-phone dex patching in the first release.** `patch-engine.md` stays
  as a later option (user-supplied images).
- Package links are shared privately with testers, never through this
  repository: the server-built images and patched framework files contain OEM
  code and are not redistributed publicly. The on-phone switch logic ships
  inside the app and the package. (2026-10-24: the source, the scripts
  included, is published on GitHub; images and package sets stay off it.)
- Samsung flagships only (Fold, Flip, S Ultra; Snapdragon first). This build
  says "tested only with ColorOS on Z Fold (F8U)".
- Application id and root package **`com.fahadali.oneos`** (decided
  2026-10-22).
- A first-launch **Before you start** screen: OneOS is experimental and
  switches the phone into another OS without flashing, so things can break;
  back up accounts and data first (Samsung Cloud, Google, Smart Switch);
  remove the screen lock (PIN, pattern, password, fingerprint/face) before
  switching, because a locked phone that boot-loops may not get into Download
  Mode to recover; tested only with ColorOS on Z Fold (F8U). Continue needs
  the checkbox "I have backed up and removed my screen lock"; the
  acknowledgement is kept in app-private SharedPreferences and the screen
  stays reachable from Home and About.
- **Screen lock**: `KeyguardManager.isDeviceSecure()` true is WARN "Screen
  lock is set - remove it before switching" in the M1 device report and
  becomes BLOCK at switch time (gate G16, §4.3) when switching arrives (M7).
- About credits OneLineage with its GitHub link only
  (`https://github.com/WeWaffles/OneLineage`); WeWaffles gave written
  permission on 2026-10-24 to publish OneOS on top of OneLineage with full
  credits in the app and on GitHub (§10, question 3, and `CREDITS.md`), and
  the app carries no handle and no permission wording. First packages: ColorOS
  Find N6 (tested, run 34) and ColorOS Find X9 Ultra (built 2026-10-22,
  untested) for S26 Ultra friends.

Status since the first draft: SIM 2 call audio works (run 34); the run-33
"screen-off hang" was the Power + Volume Down screenshot crash (OPPO
`getTpInfo` → `ctl.start gettpinfo`, fixed in `oplus_boot_hangs.py`); Nature
ringtones work; guest mobile data works and follows One UI's switch. Open: the
ColorOS status bar shows 4G where One UI shows 5G, and draws no signal bars
(§10, question 4).

Verified on the build server for this doc (2026-10-22, throwaway project, not
committed):

- The SESL coordinates resolve from **Maven Central with no token**:
  `io.github.oneuiproject.sesl:{appcompat 1.4.0, material 1.5.0, core 1.3.0,
  recyclerview 1.4.1, preference 1.1.0}` and `io.github.oneuiproject:{design
  1.2.6, icons 1.1.0, lib 1.2.1}` (release versions from each `maven-metadata`).
  This is unlike `tribalfs`' sesl9 fork, which comes from GitHub Packages and
  needs `gpr.user`/`gpr.token`.
- A minimal SESL app **builds and links**: AGP `9.3.3` (cached; `9.4.1`
  also cached), its bundled Kotlin `2.2.10`, Gradle `9.5.0` (`9.8.1` cached),
  `compileSdk = release(37)`, target 36, JDK 21 toolchain. Output
  `app-debug.apk`, `platformBuildVersionName='17'`.
- `design 1.2.6` ships `dev.oneuiproject.oneui.design` with `OneUITheme` and
  `dev.oneuiproject.oneui.layout.ToolbarLayout` (`setTitle`,
  `setExpandedSubtitle`, `setCustomTitleView`); `minSdk 23`. Its POM pulls sesl
  `appcompat 1.4.0`, `material 1.5.0`, `preference 1.1.0`, `indexscroll 1.0.3`,
  `picker-basic 1.2.0`, `picker-color 1.1.0`, `zxing 3.4.1`.
- Two build gotchas (both reproduced): SESL replaces the stock AndroidX
  artifacts, so the stock `androidx.{core,appcompat,fragment,recyclerview,
  preference,…}` and `com.google.android.material` must be `exclude`d; and `picker-color 1.1.0` shares the `androidx.picker`
  namespace with `picker-basic 1.2.0`, so `picker-color` must be excluded or
  the manifest merger fails.
- A pure-Kotlin/JVM `:core:model` with `kotlinx-serialization-json 1.11.0`
  builds and its JUnit test passes (`tests=1 failures=0`). `:app:lintDebug`
  ran clean (0 errors). First-release libraries: `com.android.tools.smali:
  smali-dexlib2:3.0.10` (Google Maven; read-only use for the installd table,
  §6.4) and `com.google.crypto.tink:tink-android:1.24.0` (Maven Central;
  Ed25519 verify). `smali:3.0.10`, `commons-compress:1.28.0` and `xz:1.12`
  are confirmed present too but only the later on-phone engine needs them.

---

## 1. Goals and non-goals

### Goals

1. One Kotlin app, One UI look (SESL), that installs a **server-built OneOS
   package** on a rooted Samsung flagship, starts the packaged OS as a guest
   session and returns to One UI by reboot. It replaces `scripts/deploy-phone.sh`
   + the switcher APK as the way files reach the phone and sessions start.
2. Make the run-25 safety guarantees **impossible to skip**: the app refuses a
   session it cannot verify, on this or any other phone/OS. Everything that
   depends on the phone (the host installd interface) is derived **on that
   phone** and read by the guest **at runtime**, fail closed (§6).
3. List every behaviour as a patch: safety patches locked; script-level
   behaviours as toggles that map to the scripts' `ONEOS_*` env vars, with
   smart per-device defaults; behaviours built into the package's files shown
   as "built in"; patches that do not apply hidden.
4. Heavy work on the server: one signed package per OS image (image +
   patched files + catalog + scripts + manifest), downloaded by a link
   shared privately (§5).
5. After a failed session grab the logs, redact them, let the user share a
   bundle; ship fixes as signed fix packs (catalog, scripts, RROs) without a
   new image; app updates by link/GitHub releases.
6. Works with a locked bootloader when root (KernelSU/Magisk/APatch) exists;
   nothing is flashed.

### Non-goals (this build)

- No on-phone dex patching and no user-supplied images: the app only stages
  packages our server built (`patch-engine.md` is the later option).
- No Exynos, no non-Samsung host, no erofs guest image, no cross-SDK
  host/guest pair: all BLOCK until a tested package exists (§4.5).
- No public distribution: the app never publishes or uploads a package or a
  log bundle; the package link is shared privately, the user shares bundles.
- No support claimed beyond **ColorOS 17 on the Z Fold (F8U)**; the S26 Ultra
  path (Find X9 Ultra package) is predicted and untested.
- Not a defence against a root user who hand-edits the scripts; it defends
  against accidents (stale files, partial downloads, an OTA under us, an old
  app, a bad package or fix pack). Stated on the About page.

---

## 2. Architecture overview

```
 build server (heavy work)
 ─────────────────────────
 OEM OTA ──► the image build (MysticGSI, not in this repository) (MysticGSI, MysticGSI's patch set) ──► system.img (ext4)
                  │
                  ▼
 scripts/make-overlays.sh + switcher/patches/*.py ──► services/oplus-services_patched.jar,
                  │                                    surfaceflinger_patched, *_payload.img,
                  │                                    OneOSWallpapersFoldGrid.apk, guards.txt
                  ▼
 scripts/make-package.sh (new, §5.6): check-dex + check-guards ─► gzip image ─► manifest.json
                  │                                                 + Ed25519 signature
                  ▼
 out/packages/<id>/<serial>/ ──upload──► HTTPS host ◄── one index link, shared privately
                                              │
 ┌──────────────────────────── phone (light work) ─┼──────────────────────────────────┐
 │  OneOS app (com.fahadali.oneos, SESL)           ▼                                  │
 │  Device report · Compat · Packages · Patches · Session · Logs · Fix packs          │
 │    │ fetch + verify index/manifest · download · sha256 · gunzip (sparse)           │
 │    │ derive the host installd table from One UI's own jars (dexlib2, read-only)    │
 │    ▼ su -c (APK assets)                                                            │
 │  oneos_stage.sh      move into $STAGE/packages/<id>/<serial>, root re-hash,        │
 │                      activate (hard links to the flat stage names),                │
 │                      write $STAGE/host_installd.table                              │
 │  oneos_preflight.sh  gates G1–G16 as root → $STAGE/session/preflight.json          │
 │    ▼                                                                               │
 │  package scripts (session.env): oneos_switch.sh → guest_prepare.sh →         │
 │    guest_start.sh · guest_props.sh · activator · watcher · return_to_oneui.sh     │
 │                                                                                    │
 │  guest system_server: OneOSInstalldProxy → OneOSInstalldTable reads                │
 │    /oem/oneos/host_installd.table (fail closed) → One UI's installd (shared)       │
 │                                                                                    │
 │  shared with One UI: kernel · binder/servicemanager · property area ·              │
 │  Samsung vendor HALs · installd/vold/keystore (guarded) · /apex                    │
 └────────────────────────────────────────────────────────────────────────────────────┘
```

The app is advisory. Everything that can delete data or boot a guest runs as
root from scripts and re-checks the gates itself (§4.2). The server is the only
place that patches dex; the phone verifies what the server signed and adds the
one thing the server cannot know, the host installd interface of this phone
and this One UI build.

---

## 3. Components and module layout

### 3.1 Modules (first release)

| Module | Kind | Contents | Replaces today |
| --- | --- | --- | --- |
| `:app` | Android app | SESL screens, `com.fahadali.oneos` | `switcher/src/.../MainActivity.java`, `res/` |
| `:core:model` | Kotlin/JVM | all JSON schemas (`kotlinx-serialization`): package, index, catalog, compat, logbundle, fixpack; predicate evaluator; `PlanResolver` (catalog + facts + toggles → `session.env`) | env logic scattered in scripts |
| `:core:device` | Android lib | `FactProbe`, `CompatEvaluator` (phone × package), form/SoC/root detection | fact reads in `MainActivity`, `guest_prepare.sh` |
| `:core:root` | Android lib | su/busybox/resetprop discovery; runs the APK-asset scripts `oneos_stage.sh`, `oneos_preflight.sh`; progress reattach | `MainActivity` `Runtime.exec` plumbing |
| `:core:package` | Android lib | `IndexClient`, `ManifestVerifier` (tink Ed25519), `Downloader` (resumable, streaming SHA-256), `ImageUnpacker` (gzip → sparse raw + SHA-256), `Stager` (drives `oneos_stage.sh`) | `scripts/deploy-phone.sh` |
| `:core:safety` | Android lib | `HostInstalldTable` (dexlib2, read-only), `InstalldTableWriter` (§6.2 format), `GateRunner`, safety floor | `scripts/host-installd-table.sh`, `guards.txt` checks |
| `:core:logs` | Android lib | `SessionLogCollector`, `Redactor`, `ReturnReasonParser`, bundle writer | `scripts/pull-run-logs.sh` |
| `:core:fixpack` | Android lib | verify, `match` (package id + phone), pin/rollback | new |

From 0.3.4 `:app` builds two editions from one codebase: OneOS (flavor
`full`) and OneOS Probe (flavor `probe`, `com.fahadali.oneos.probe`: only the
device report, the read-only tests and the findings; §11, 0.3.4).

Built so far (Friend build 1, `0.2.0-probe`, compat-safety-logs.md §7):
`:core:safety` exists as a **Kotlin/JVM** module (not an Android lib) with
`HostInstalldTable` (dexlib2 `3.0.10`), so the derivation is unit tested on
the server against the F8U `services.jar`; the format-1 writer/validator
(`InstalldTableFormat`), the `Redactor` and the findings bundle are pure
Kotlin in `:core:model`; `RootProbeRunner` in `:core:root` runs the read-only
probe list (`assets/probe/commands.list`). The JSON is written by a small
writer in `:core:model`; `kotlinx-serialization` comes with M4.

APK assets: `oneos_stage.sh`, `oneos_preflight.sh`, the safety floor
(`floor.json`: gates, minimum `BRIDGES`, safety patch ids, drop-tags), the
gap-splash PNG (`make-bootsplash.py --preview`). The session scripts are not
APK assets; they come with the package (§5.2).

### 3.2 Later option (not in the first release)

`:core:image`, `:core:dex`, `:core:patch` (11 patcher ports), `:engine`
(`com.fahadali.oneos.engine.EngineMain`, root `app_process`) and `:tools:patch-cli`
from `patch-engine.md`, for user-supplied images. The package format (§5)
keeps room for it: a package built on the phone would carry the same manifest,
signed by no one and therefore always WARN.

### 3.3 What runs where

| Build server (per OS image) | Phone, app (unprivileged) | Phone, root scripts |
| --- | --- | --- |
| GSI from the OEM OTA; patched `services`/`oplus-services` jars; `surfaceflinger_patched`; APEX payloads; RROs (aapt2); `check-dex.py`; guard check; `guards.txt`; gzip; catalog; manifest + Ed25519 signature; index | device facts; compat report; host installd table derivation; download + hash + unpack; toggles → `session.env`; log redaction + bundle; fix-pack verify | stage + activate (`oneos_stage.sh`); write the table; preflight gates; session scripts; return; log collection |
| never on the phone in this release: dex patching, aapt2, image building | never: anything under `/data` outside the app sandbox | never: anything that depends on the app's word alone (§4.2) |

---

## 4. Safety model

The run-25 incident (`docs/coloros-on-fold.md`, "Keeping the guest away from
One UI's data"): the guest's `UserDataPreparer.destroyUserData(0)` went through
One UI's shared `installd` and deleted One UI app data and the test phone's photos.
The whole safety design exists to make that un-repeatable and un-skippable.

### 4.1 Safety floor (compiled into the APK; a package or pack can only tighten it)

- the **gate list** G1–G16 (§4.3),
- the minimum **bridge list** (`switcher/assets/bridges.sh` `BRIDGES`: at least
  `app:app user:user user_de:user_de data:user/0 media:media`, as
  `guest_prepare.sh:15-17` requires); a package's `bridges.sh` must be a superset,
- the **safety patch ids** (`safety.*`, `patch-catalog.md` §6.1): locked, no
  toggle, no env var; a package whose manifest does not list every one of them
  as applied and verified is refused,
- the installd **ALLOWED** list as published by the patcher (§6.5): the app
  refuses a package whose `installd.mapped` names are not a subset of the
  floor's copy,
- the built-in **redaction drop-tag list** (`compat-safety-logs.md` §3.3).

A package or fix pack may add gates, bridges, drop-tags and forbidden
patterns, and tighten thresholds. One that would remove or loosen any of
these is rejected whole.

### 4.2 Layers, deepest wins

1. **App (advisory).** `GateRunner` runs the gates and shows results; safety
   patches render as locked toggles. No setting, debug menu or intent extra
   turns a gate off.
2. **Root preflight (binding).** `oneos_preflight.sh` (APK asset) re-runs every
   gate as root and writes `$STAGE/session/preflight.json` with the plan hash,
   the active package id/serial/manifest hash, the installd table hash and the
   current `boot_id` (`/proc/sys/kernel/random/boot_id`).
3. **Session scripts (binding, last moment).** `oneos_switch.sh` starts
   only if `preflight.json` exists, is < 5 min old, carries this boot's
   `boot_id`, and matches the plan hash; `guest_prepare.sh` keeps its own
   G1–G6 checks (`guest_prepare.sh:4-39`) and adds the installd table check
   (§6.3), so a stale or hand-edited preflight still cannot start a guest
   without the guarded jars and a valid table.
4. **Guest runtime (fail closed).** `OneOSInstalldTable` in the patched
   `services.jar` re-validates the table and throws on every installd call it
   cannot map (§6.3). This layer holds even if all three above were bypassed.

The app builds the session env from an **allow-list** of feature toggles
(`ONEOS_GUEST_*`, `ONEOS_GAP_*`, bounded return timers). Env that weakens a
gate is never emitted: `ONEOS_RETURN_MAX=0`, `ONEOS_RETURN_KEYS=0`,
`ONEOS_RETURN_MODE=inplace`, `ONEOS_LOGCAT=0`, `ONEOS_STOCK_SF=1`,
`ONEOS_KEEP_FOLD_LAYOUT=1` are debug-build-only or not shipped
(`patch-catalog.md` §6.8, §8).

### 4.3 Gates (refusals)

`G1`–`G8` exist in the scripts today; `G9`–`G16` are new in the app
(`compat-safety-logs.md` §2.1). Each is a refusal: unverifiable → no session.

| Id | Gate | First release |
| --- | --- | --- |
| G1 | Storage/power/sysrq/installd guards in the jars the guest loads | staged jars' SHA-256 = signed manifest, manifest guard checks all `ok` (server, §4.4); `guest_prepare.sh` `guards.txt` check unchanged |
| G2 | installd table valid for this phone and this One UI build | `$STAGE/host_installd.table` present, well-formed, fingerprint = `getprop ro.build.fingerprint`, source jar hash matches, every `installd.required` method maps (§6.3) |
| G3 | Every `bridges.sh` tree is the staged copy (device:inode) | unchanged |
| G4 | Nothing mounted at or under `$STAGE/data` | unchanged; also before stage/activate |
| G5 | No bridge left from an earlier session | unchanged; also before stage/activate |
| G6 | The guarded `services.jar` is the bound one | unchanged |
| G7 | One UI's `/apex` unchanged and readable | unchanged |
| G8 | Guest namespace has no host root/storage views/sysrq | unchanged |
| G9 | Free space | download + unpack sizes from the manifest + 8 GB staged data + 1 GB logs + 2 GB margin |
| G10 | Battery | ≥ 30 % or charging, temperature < 42 °C |
| G11 | Samsung + arm64 | unchanged |
| G12 | Auto-return watcher and return keys armed | always on |
| G13 | Compat report (phone × active package) not BLOCK | §4.5 |
| G14 | Every floor safety patch applied and verified | from the signed manifest (`files[].patches`, `guards.checks`) |
| G15 | Active package intact | signature valid, not revoked (last index check), flat stage names are the active package's files: SHA-256 for everything but `system.raw`, stat identity (dev:inode:size:mtime recorded at staging) for `system.raw` |
| G16 | No screen lock (PIN, pattern, password, fingerprint/face): a locked phone that boot-loops may not get into Download Mode to recover | `KeyguardManager.isDeviceSecure()` false, read by the app right before the session; the root preflight re-checks it (method settled in M7). Until switching exists (M1–M6) the device report shows it as WARN only |

### 4.4 Patch, then verify independently (on the server)

The patchers and the verifier share no code, so a selector miss cannot hide
a destructive call. In the first release both run on the server inside
`make-package.sh` (§5.6): `scripts/check-dex.py` (empty try ranges, run 26)
and a new `scripts/check-guards.py` that reads the **built** dex (dexdump, like
`host-installd-table.sh`) and checks, for every jar on the image's
`SYSTEMSERVERCLASSPATH` plus a boot-class-path shadowing check (runs 26–29:
ColorOS's own `framework.jar` shadowed the patched `IInstalld$Stub$Proxy`):
no destructive `IVold`/`IInstalld`/keystore-maintenance call sites;
`OneOSInstalldProxy` is the only `IInstalld$Stub.asInterface` target; its
blocked methods throw before `transact`; each mapped method gets its code
from `OneOSInstalldTable.code(name+sig)` and nothing else (§6.5); no
`"sys.powerctl"` left in PMS; `doSysRq('c')` returns. The result goes into
the manifest's `guards` object (schema `oneos.guards/1`) and `guards.txt` is
shipped unchanged for `guest_prepare.sh`. Any failed check fails the package
build: an unverified package is never signed.

### 4.5 Compat levels

`CompatReport` (`oneos.compat/1`) for this phone × a package, worst finding
wins.
**BLOCK** (no continue): manifest signature/key/schema invalid or revoked;
app older than `minApp`; not Samsung; not arm64; SoC vendor not in
`supports.socVendors` (Exynos until profiled); device family not in
`supports.families`; host SDK not in `supports.hostSdk` (cross-SDK); no working
su/busybox/resetprop; installd table cannot be derived or a required method
does not map (§6.4); free space short.
**WARN** (continue after reading): phone model not in the package's `tested`
list; package `status: untested`; One UI build differs from every tested
fingerprint; form factor vs model-prefix disagreement; generic SELinux types
missing.
Consequence for testers: an **S26 Ultra (Snapdragon) + the Find X9
Ultra package** is WARN and runs, pending a policy answer (§10,
question 2); Exynos, other families and cross-SDK are BLOCK.
The screen lock is a session precondition, not a phone × package property:
the device report shows a set lock as WARN ("Screen lock is set - remove it
before switching", `ScreenLockRule` in `:core:model`) and gate G16 makes it
BLOCK at switch time.

### 4.6 Signed content trust (packages, index, fix packs)

Ed25519 over the exact bytes of `manifest.json` (and `index.json`), verified
with `tink-android:1.24.0` `Ed25519Verify`. Two public keys compiled in:
active + offline backup for rotation. Verify order: signature → `keyId`
known → schema (unknown `critical` field → refuse) → `minApp` → anti-rollback
(`serial` ≥ last accepted for that id; the index `serial` ≥ last accepted) →
safety floor → every file hash as it is downloaded → `match`/`supports`
against the current report. The active set (package + packs) is recorded in
`preflight.json` and frozen for the session.

---

## 5. OneOS package

### 5.1 What a package is

One signed bundle per OS image build: the guest system image, every file the
session scripts bind over it, the session scripts themselves at the same
commit, the catalog for that image, and a manifest that ties them together
with hashes. A package is identified by `id` (stable per OS line, e.g.
`coloros17-findn6`) and `serial` (monotonic, bumped on every rebuild: new
image, new patched files, new scripts). The scripts ship inside the package
because script and jar changes land together in one commit per run (run 34
changed `guest_prepare.sh` and `oplus_boot_hangs.py` together); one version
of each avoids a skew matrix. Script-only fixes reach users as fix packs for
that package (§8.6) without re-downloading the image.

### 5.2 Layout (server output and download)

```
out/packages/<id>/<serial>/
  manifest.json               the manifest (§5.3), canonical JSON
  manifest.json.sig           base64 of the raw 64-byte Ed25519 signature
  system.img.gz               the MysticGSI ext4 image, gzip -n
  system.img.gz.part000 …     only when split for a host's file-size limit (§5.4)
  files/services_patched.jar
  files/oplus-services_patched.jar
  files/surfaceflinger_patched
  files/OneOSWallpapersFoldGrid.apk          fold packages only
  files/<name>_payload.img                   one per guest APEX module the scripts mount
  files/guards.txt
  scripts/oneos_switch.sh guest_prepare.sh guest_start.sh guest_props.sh
          bridges.sh check_host_apex.sh return_to_oneui.sh zygote_exec
  catalog.json                oneos/patch-catalog/1 for this image
out/packages/index.json, index.json.sig       the channel index (§5.5)
```

`tethering_payload.img` is built by `make-overlays.sh` but never mounted (the
host's tethering module stays, `guest_prepare.sh:1168`), so it is not
packaged. `oneos_tunnel.sh` and `7zz` are not packaged.

### 5.3 Manifest schema (`oneos.package/1`, final)

Example: the Find N6 package as it would be built from the run-34 tree (hash
values elided).

```json
{
  "schema": "oneos.package/1",
  "id": "coloros17-findn6",
  "serial": 1,
  "title": "ColorOS 17 (Find N6)",
  "status": "tested",
  "issued": "2026-10-22T16:00:00Z",
  "keyId": "oneos-2026a",
  "minApp": 100,
  "critical": [],
  "builtFrom": {
    "commit": "3e46795",
    "mysticgsi": "<submodule commit>",
    "gsiPatches": "MysticGSI's patch set",
    "ota": {"file": "<OEM OTA file name>", "sha256": "…"}
  },
  "os": {
    "family": "coloros",
    "version": "17.0.0.109",
    "displayId": "PLP120_17.0.0.109(CN01)",
    "product": "PLP120",
    "region": "CN",
    "release": "17",
    "sdk": 37,
    "fingerprint": "OPPO/PLP120/OP61A9L1:17/BP2A.250605.015/B.2a873cc-443f2b-48b08c:user/release-keys",
    "systemFingerprint": "qti/qssi/qssi:17/CP2A.260605.016/1791119910961:user/release-keys"
  },
  "image": {
    "file": "system.img.gz",
    "url": "system.img.gz",
    "compression": "gzip",
    "bytes": 0,
    "sha256": "…",
    "parts": [],
    "rawBytes": 10276003840,
    "rawSha256": "…",
    "fs": "ext4",
    "stageName": "system.raw"
  },
  "files": [
    {"name": "services_patched.jar", "url": "files/services_patched.jar",
     "bytes": 0, "sha256": "…", "mode": "0644", "kind": "framework-jar",
     "bind": {"how": "bind", "guestPath": "/system/framework/services.jar"},
     "imageSha256": "<sha256 of the image's own services.jar>",
     "patches": ["safety.storage_guards", "safety.installd_abi_proxy", "safety.vold_key_guard",
                 "safety.power_guards", "safety.no_sysrq_crash", "core.guest_idmap2d",
                 "samsung.skip_host_apex_services", "coloros.display_mode_fallback",
                 "coloros.wait_for_service"]},
    {"name": "oplus-services_patched.jar", "url": "files/oplus-services_patched.jar",
     "bytes": 0, "sha256": "…", "mode": "0644", "kind": "framework-jar",
     "bind": {"how": "bind", "guestPath": "/system/framework/oplus-services.jar"},
     "imageSha256": "…",
     "patches": ["safety.storage_guards", "safety.installd_abi_proxy", "safety.no_sysrq_crash",
                 "coloros.wait_for_service", "coloros.boot_hangs", "coloros.backlight_curve"],
     "deviceValues": {"coloros.backlight_curve": "F8U"}},
    {"name": "surfaceflinger_patched", "url": "files/surfaceflinger_patched",
     "bytes": 0, "sha256": "…", "mode": "0755", "kind": "binary",
     "bind": {"how": "bind", "guestPath": "/system/bin/surfaceflinger"},
     "imageSha256": "…", "patches": ["coloros.sf_skip_qti_composer"]},
    {"name": "OneOSWallpapersFoldGrid.apk", "url": "files/OneOSWallpapersFoldGrid.apk",
     "bytes": 0, "sha256": "…", "mode": "0644", "kind": "rro",
     "bind": {"how": "copy", "guestPath": "/oem/overlay/OneOSWallpapersFoldGrid.apk"},
     "when": {"forms": ["fold"]}, "patches": ["coloros.wallpapers_fold_grid"]},
    {"name": "art_payload.img", "url": "files/art_payload.img",
     "bytes": 0, "sha256": "…", "mode": "0644", "kind": "apex-payload", "fs": "erofs",
     "bind": {"how": "loop-ro", "guestPath": "/apex/com.android.art"}},
    {"name": "guards.txt", "url": "files/guards.txt",
     "bytes": 0, "sha256": "…", "mode": "0644", "kind": "guards", "bind": null}
  ],
  "scripts": [
    {"name": "guest_prepare.sh", "url": "scripts/guest_prepare.sh", "bytes": 0, "sha256": "…", "mode": "0755"}
  ],
  "catalog": {"url": "catalog.json", "schema": "oneos/patch-catalog/1", "version": 1, "sha256": "…"},
  "installd": {
    "tableFormat": 1,
    "guestTablePath": "/oem/oneos/host_installd.table",
    "mapped": [
      {"name": "createUserData", "sig": "(Ljava/lang/String;III)V"},
      {"name": "createAppData", "sig": "(Landroid/os/CreateAppDataArgs;)Landroid/os/CreateAppDataResult;"}
    ],
    "required": ["createUserData", "createAppData", "invalidateMounts"],
    "blocked": ["destroyUserData", "clearAppData", "destroyAppData"]
  },
  "guards": {
    "schema": "oneos.guards/1",
    "checks": [{"id": "no-destructive-installd", "ok": true}, {"id": "no-shadowing", "ok": true},
               {"id": "installd-runtime-table", "ok": true}, {"id": "no-empty-try", "ok": true}],
    "verifier": "scripts/check-guards.py@3e46795"
  },
  "supports": {
    "hostVendor": "samsung",
    "abi": "arm64-v8a",
    "families": ["z-fold"],
    "forms": ["fold"],
    "socVendors": ["qualcomm"],
    "hostSdk": [37],
    "oneuiMin": 90000
  },
  "tested": [
    {"model": "SM-F976B", "device": "q8q", "soc": "SM8850", "oneui": 90000,
     "fingerprint": "samsung/q8qxxx/q8q:17/CP2A.260605.016/F976BXXS3AZIJ_OXM3AZIJ:user/release-keys",
     "run": 34}
  ],
  "notes": "Run 34: SIM 2 call audio, screenshot crash fixed, mobile data follows One UI."
}
```

The Find X9 Ultra package differs in `id` `coloros17-findx9u`, `status`
`untested`, `os` (`PMA120_17.0.0.106(CN01)`, fingerprint
`OPPO/PMA120/OP61BDL1:17/CP2A.260605.016/B.30d6865-a9327b-aae421:user/release-keys`,
raw image 10385141760 bytes), `supports.families` `["s-ultra"]`,
`supports.forms` `["bar"]`, no fold RRO, and an empty `tested` list.

### 5.4 Field rules

- **Canonical bytes.** UTF-8, sorted keys, no insignificant whitespace except
  a final `\n`; the signature covers exactly these bytes. Unknown fields are
  ignored unless named in `critical`.
- **URLs** are relative to the manifest URL (or absolute `https://`; plain
  `http` is refused). `parts` (each `{url, bytes, sha256}`) is used when the
  host has a per-file limit: GitHub release assets must be under 2 GiB and the
  Find X9 Ultra image gzips to 5.29 GB (`out/oneos-coloros-x9u.img.gz`), so a
  GitHub-hosted package has three parts (§10, question 1). `sha256`/`bytes` of the whole `.gz` are still given.
- **image**: `sha256` covers the compressed stream, `rawSha256`/`rawBytes` the
  unpacked ext4 image the scripts loop-mount (the same check
  `deploy-phone.sh` does today). `fs` must be `ext4` in this release.
- **files[].bind.how**: `bind` (file bind-mounted over `guestPath`), `copy`
  (copied into a staged dir that is bound, e.g. `$STAGE/oem/overlay`),
  `loop-ro` (loop-mounted read-only at `guestPath` and its `@version` dirs),
  `null` (read on the host only). `guestPath` is informational for the app and
  the log bundle; the scripts own the actual mounts. `when` filters by
  `forms`/`families`; a file whose `when` cannot match the package's
  `supports` is not packaged.
- **files[].patches** lists catalog ids built into that file; together with
  `guards.checks` it is what G14 reads. `deviceValues` names entries that
  carry one phone's measured values (§5.8).
- **installd**: `tableFormat` is the runtime table format the package's
  `services_patched.jar` reads; `mapped` are the methods the proxy will look
  up at runtime (name + the **guest's** signature), `blocked` the ones that
  always throw; `required` (subset of `mapped`) are the methods without which
  the guest cannot boot, so the app BLOCKs when the phone's table cannot map
  them. All three come from the patcher's `--report` (§6.5).
- **supports** values: `families` ∈ `z-fold` (SM-F9xx), `z-flip` (SM-F7xx),
  `s-ultra` (S Ultra model numbers, to be listed per release), matched with
  the form check of `patch-catalog.md` §4; `socVendors` from
  `ro.soc.manufacturer`; `oneuiMin` against `ro.build.version.oneui`.

### 5.5 Channel index (`oneos.index/1`)

The maintainer shares **one link**: the index URL. It lists every package and fix
pack, so a friend's phone shows only the packages that match it.

```json
{
  "schema": "oneos.index/1",
  "serial": 7,
  "issued": "2026-10-22T16:00:00Z",
  "keyId": "oneos-2026a",
  "app": {"versionCode": 100, "url": "https://…/OneOS-1.0.0.apk", "sha256": "…"},
  "packages": [
    {"id": "coloros17-findn6", "serial": 1, "title": "ColorOS 17 (Find N6)", "status": "tested",
     "manifest": "coloros17-findn6/1/manifest.json", "manifestSha256": "…", "bytes": 0,
     "supports": {"families": ["z-fold"], "socVendors": ["qualcomm"], "hostSdk": [37]}},
    {"id": "coloros17-findx9u", "serial": 1, "title": "ColorOS 17 (Find X9 Ultra)", "status": "untested",
     "manifest": "coloros17-findx9u/1/manifest.json", "manifestSha256": "…", "bytes": 0,
     "supports": {"families": ["s-ultra"], "socVendors": ["qualcomm"], "hostSdk": [37]}}
  ],
  "fixpacks": [],
  "revoked": [{"id": "coloros17-findn6", "serial": 0, "reason": "example"}]
}
```

It supersedes the separate `oneos.fixpack-index/1` of `compat-safety-logs.md`
§4.4 (same fields, now under `fixpacks`). The app re-reads it only when the
user opens the app or taps Check (no background network); a revoked package
serial cannot start a session (G15).

### 5.6 Server: how a package is produced

Existing pieces, unchanged: the image build (MysticGSI, not in this repository)`
(MysticGSI, MysticGSI's patch set) builds the image;
`scripts/make-overlays.sh <img> <outdir>` builds the patched files, runs
`check-dex.py` and writes `guards.txt` (X9U: 5 min 16 s, `out/make-overlays-x9u.log`).
New: `scripts/make-package.sh` (outline; the scripts owners write it):

```
scripts/make-package.sh <profile.json> <system.img> [--serial N] [--split 1900M] [--dev]
  profile.json (checked in, e.g. packages/coloros17-findn6.json): id, title, status,
    supports, tested, notes, catalog source
  1. refuse a dirty tree under switcher/ scripts/ MysticGSI's patch set/ unless --dev
     (a --dev package gets status "dev" and the app shows it only in debug builds)
  2. facts: debugfs cat /system/build.prop (+ my_* props) → os.*; file -L must say ext4;
     sha256 + size of the raw image
  3. overlays: scripts/make-overlays.sh <img> $WORK/files   (existing; runs check-dex.py)
     with the patcher's --report written to $WORK/installd.json (§6.5)
  4. guards: scripts/check-guards.py <img> $WORK/files → $WORK/guards.json; non-zero exit stops
  5. drop files the scripts never use (tethering_payload.img) and files whose `when`
     cannot match `supports` (the fold RRO in a bar package)
  6. scripts: copy switcher/assets/{oneos_switch,guest_prepare,guest_start,guest_props,
     bridges,check_host_apex,return_to_oneui}.sh and zygote_exec into scripts/
  7. catalog: the app repo's catalog source filtered for os.family → catalog.json
  8. image: pigz -n -6 (or gzip -n -6) → system.img.gz; sha256; optional split into parts
  9. manifest: python3 -I writes canonical manifest.json from 2–8 (every sha256 recomputed
     from the files in the output dir, never copied from a log)
 10. sign: openssl pkeyutl -sign -rawin -inkey "$ONEOS_SIGN_KEY" -in manifest.json | base64
     > manifest.json.sig; verify at once with the public key; the key never enters the repo
 11. index: add/replace the package entry in out/packages/index.json, serial+1, sign the same way
 12. print what to upload (the host is §10, question 1)
```

Rebuilding the same tree and image yields the same files and hashes except
`issued` (gzip `-n`, sorted manifest keys), so a package is reproducible from
its `builtFrom` commit.

### 5.7 App: verify, download, unpack, stage, activate

1. **Add link.** The user pastes or shares the index URL to the app (also
   `oneos://add?index=<url>`). The app fetches `index.json` + `.sig`,
   verifies (§4.6), and lists the packages whose `supports` match this phone,
   each with its compat level (§4.5) and size.
2. **Manifest.** On Download the app fetches the manifest + `.sig`, checks it
   against the index entry (`manifestSha256`), verifies it and runs the compat
   evaluation (installd table included, §6.4) and G9 before any large byte
   moves.
3. **Download** into `filesDir/packages/<id>/<serial>/dl/` (app-private, on
   `/data`), as a user-initiated data transfer job (API 34+) with a
   notification; Wi-Fi only by default; HTTP `Range` resume; SHA-256 computed
   while writing; a file or part that ends with the wrong size or hash is
   deleted and fetched again (3 tries, then an error naming the file).
4. **Unpack** `system.img.gz` with `GZIPInputStream` into `system.raw`,
   writing 4 KiB zero blocks as holes (seek) and hashing the logical bytes in
   the same pass; `rawBytes`/`rawSha256` must match and the ext4 magic
   (`0xEF53` at offset 1080) must be present. The `.gz` is then deleted
   unless the user keeps it.
5. **Stage** (root, `oneos_stage.sh stage <id> <serial>`): refuses while a
   session is up (G4, G5, rootfs mounted); `mv` the verified files from the
   app dir into `$STAGE/packages/<id>/<serial>/` (a rename on the same `/data`
   filesystem; copy + re-hash on `EXDEV`), `chown root:root`, modes from the
   manifest, the label adb-pushed files have today (`shell_data_file`), so the
   guest sees what runs 30–34 saw; root re-hashes every file (the raw image
   once, as `deploy-phone.sh` does) against the manifest copy it stores next to
   them, and records `staged.json` (hashes + stat identity of `system.raw`).
6. **Activate** (root, `oneos_stage.sh activate <id> <serial>`, only when no
   session is up): hard-link the package's files and scripts to the flat stage
   names the scripts read today (`$STAGE/system.raw`,
   `$STAGE/services_patched.jar`, `$STAGE/guards.txt`, `$STAGE/*.sh`, …),
   remove every flat `*_patched*`/`*_payload.img`/RRO name the package does
   not carry (otherwise `guest_prepare.sh` would use another package's
   payload; it also binds OneLineage leftovers such as
   `PermissionController_patched.apk` when present, so the run-34 stage is
   listed once before M5 and every file it binds is either packaged or
   confirmed unused), and write `$STAGE/active_package.json` `{id, serial,
   manifestSha256}`. Hard links keep the inode, so G6's device:inode check
   sees the package file itself. The old switcher APK
   (`com.wewaffles.onelineage`) copies its own scripts into the stage when it
   opens (`deploy-phone.sh:41-46`) and `cp -f` would write through these
   links; G15 then refuses the session, and the app asks the user to remove
   the old switcher before the first activation.
7. **Guest data per package.** `$STAGE/data` belongs to the active package's
   `os.fingerprint`. Activating a package with another fingerprint renames
   `$STAGE/data` to `$STAGE/data.<old id>` and renames back a
   `$STAGE/data.<new id>` if one exists; both renames only after G4/G5 (no
   delete, no `rm -rf` near a possible bridge). Deleting old guest data is a
   separate, confirmed user action with the same checks.
8. **Installd table** for this phone is written or refreshed (§6.4); it does
   not depend on the package, but the package's `installd.required` must map.

### 5.8 Per-device values baked into server-built files

Patches that carry one phone's measured values become part of a file that
every phone of the package receives. Today that is `coloros.backlight_curve`
(`OneOSPanelBacklight.smali`, the F8U panel's nits → float table) inside
`oplus-services_patched.jar` of **both** packages; on an S26 Ultra it maps
brightness with the Fold's panel table. The manifest names such entries in
`deviceValues` and the Patches screen shows them as "built in (Z Fold F8U
values)". The follow-up is the same mechanism as §6: the helper reads a
per-panel table from `/oem/oneos/` at runtime and falls back to ColorOS's
stock mapping when there is none, so a package carries no device values.

---

## 6. Runtime host installd table

### 6.1 Today

`scripts/host-installd-table.sh <services.jar>` runs `dexdump -f` on One UI's
`services.jar` (pulled with adb), takes the `TRANSACTION_<name>` int values of
`android/os/IInstalld$Stub` and the first `(params)ret` per method name of
`android/os/IInstalld$Stub$Proxy`, and prints `name code signature` sorted by
code into `switcher/patches/host_installd.txt` (85 methods, F8U build
`F976BXXS3AZIJ`, fingerprint in a comment). `guest_installd_abi.py` reads that
file at **build time**: for each guest proxy method in `ALLOWED` (27 names)
whose host signature is identical it rewrites the `const` that feeds
`transact` to the host's code; every other method gets a `RemoteException`
before any binder code. The X9U build log reports "5 identical, 22 remapped,
31 blocked". The codes are therefore frozen into `services_patched.jar` for
one host build, which cannot work for a package that goes to many phones and
across One UI updates.

### 6.2 File format and path

Written by the app (through root) on each phone, read by the guest at runtime.

- Host path (canonical): `$STAGE/host_installd.table`, `root:root 0644`.
- Guest path: `/oem/oneos/host_installd.table`. `guest_prepare.sh` copies the
  validated file to `$STAGE/oem/oneos/` (root-owned, `0444`, dir `0755`,
  labelled `system_file` like the RRO today) and **always** binds `$STAGE/oem`
  on `$ROOTFS/oem`, then remounts it `ro`. `/oem` is empty in the image
  (`guest_prepare.sh:266`), and the guest's `system_server` (uid 1000) can
  read but not change the file. Not under the guest's `/data`: that is
  `system`-writable.

Format version 1, ASCII, `\n` line ends, no comments, no blank lines, at most
64 KiB:

```
oneos.installd-table 1
fingerprint samsung/q8qxxx/q8q:17/CP2A.260605.016/F976BXXS3AZIJ_OXM3AZIJ:user/release-keys
source /system/framework/services.jar <sha256 of that jar>
methods 85
createUserData 1 (Ljava/lang/String;III)V
destroyUserData 2 (Ljava/lang/String;II)V
…
getHighDataList 85 (Ljava/lang/String;II)Ljava/util/List;
sha256 <sha256 of every byte above this line>
```

Rules: line 1 exactly `oneos.installd-table 1`; `fingerprint` is One UI's
`ro.build.fingerprint` (no spaces); `source` is the jar the interface was read
from and its SHA-256; `methods N` with 1 ≤ N ≤ 512 followed by exactly N
entries; entry name `[A-Za-z_][A-Za-z0-9_]*`, code decimal in
1…16777215 (`FIRST_CALL_TRANSACTION`…`LAST_CALL_TRANSACTION`), signature
`(…)…` without spaces; names unique, codes unique and ascending; methods the
proxy class lacks (dexdump's `-`) are left out; last line `sha256 <hex>` over
all preceding bytes, followed by one `\n` and nothing else. The same phone and
build always give byte-identical files (no timestamps), so the F8U output can
be compared with `host_installd.txt` byte for byte (minus its comments).

### 6.3 Validation and fail-closed behaviour (three places)

| Where | Checks | On failure |
| --- | --- | --- |
| App (`InstalldTableWriter` + G2) | derivation rules of §6.4; all §6.2 rules; `destroyUserData` and `createAppData` present (it is the interface we think); every `installd.required` of the active package maps by name **and** guest signature | BLOCK with the reason; nothing written |
| `oneos_preflight.sh` (G2) and `guest_prepare.sh` before the pivot | §6.2 structure; `fingerprint` = `getprop ro.build.fingerprint`; `sha256sum <source>` = the `source` hash; trailer hash (`sed '$d' <file>` piped to `sha256sum`); the file hash equals the one in `preflight.json` | exit 3, "installd table missing or not for this One UI build; not starting the guest" (as for `guards.txt`) |
| Guest `system_server`: `OneOSInstalldTable` (in `services_patched.jar`) | loads once on the first installd call: structure, size cap, trailer SHA-256 (`MessageDigest`), `fingerprint` = `SystemProperties.get("ro.build.fingerprint")`, unique names/codes | state = invalid, one `Slog.e("OneOS", …)` with the reason, and **every** mapped method throws `RemoteException("OneOS: installd table unusable (<reason>): <name> not sent")` before `transact` |

Why the guest-side fingerprint check works: the property area is shared and
`guest_props.sh` never adds or overrides a key One UI defines (only blur,
`saupwk` and the ringtone names are overridden), so `ro.build.fingerprint`
inside the guest is One UI's. If a future change ever overrode it, the check
fails closed rather than open. A lookup for a name + signature the table does
not have (host lacks the method, or its signature differs) also throws, which
is exactly today's build-time "blocked" outcome. The `blocked` methods never
consult the table at all, so no table content can unblock
`destroyUserData` or any other destructive call. With an invalid table the
guest cannot create user or app data, so it does not reach a home screen and
the watcher's no-home / no-zygote triggers return the phone to One UI; One UI
data is never at risk.

### 6.4 What the app does on each phone (port of `host-installd-table.sh`)

`HostInstalldTable` (`:core:safety`, dexlib2 `3.0.10`, read-only, no root
needed: `/system/framework` is world-readable; root `cat` as fallback):

1. **Candidate jars**, in class-loader order for One UI's `system_server`: the
   `BOOTCLASSPATH` entries (from the app's environment), then
   `/system/framework/services.jar`. For each, open every `classes*.dex` in
   the zip and look for `Landroid/os/IInstalld$Stub;`.
2. **Codes**: each `static final int TRANSACTION_<name>` field's initial value
   (`IntEncodedValue`) in `IInstalld$Stub` (dexdump's `value :`).
3. **Signatures**: each method of `IInstalld$Stub$Proxy` as
   `(<param type descriptors>)<return descriptor>`; a name that appears twice
   is a BLOCK (AIDL has no overloads, so it is not the AIDL class). The
   script's "first signature wins" becomes "exactly one".
4. **Which class counts**: the first jar in step 1 that defines the class is
   what One UI loads (runs 26–29 were exactly this shadowing, on the guest
   side). If a later jar defines it too and its table differs → BLOCK
   (ambiguous); if the class is in no jar, or the jars hold no dex (stripped;
   a `services.vdex` read is a later option) → BLOCK "installd interface
   unknown".
5. **Checks** of §6.3 (app row), then write the §6.2 file: the text is passed
   to `oneos_stage.sh write-table` on stdin, which writes
   `$STAGE/host_installd.table.tmp`, runs the shell validation and renames it.
6. **When**: at app start and before every preflight, cached in the app by
   (fingerprint, jar size, jar mtime); a different `ro.build.fingerprint`
   (One UI OTA) always rewrites it. Cost: parse of a ~45 MB jar's dex index,
   expected under 2 s (`patch-engine.md` §4).

The compat screen shows the result per package: "installd: 27 of 27 allowed
calls map on this phone" or the names that do not.

### 6.5 Patcher change (`switcher/patches/guest_installd_abi.py`)

Described here, not edited (the patches belong to the scripts owners):

1. **Command line.** `guest_installd_abi.py <smali root> <host table>` becomes
   `guest_installd_abi.py <smali root> --table-helper
   switcher/patches/OneOSInstalldTable.smali [--report <json>]`. No host table
   is read at build time; `--callers <smali root>` (oplus-services.jar) is
   unchanged. `make-overlays.sh:41` changes accordingly.
2. **Classification no longer uses the host.** For each guest proxy method
   whose name has a guest `TRANSACTION_` field: if the name is in `ALLOWED`
   it is **mapped**, else **blocked**. The `host.get(name)` lookup, the
   `h[1] == sig` comparison and the `kept`/`remapped` split are removed;
   equal-code methods are mapped too, so one jar works on every host build.
3. **Mapped methods.** Locate the `transact` line and the code register `vN`
   exactly as today (`TRANSACT` regex, then the nearest preceding
   `const(/4|/16)? vN, …`). Replace that one `const` line with three lines:

   ```
   const-string vN, "<name><guest signature>"
   invoke-static {vN}, Lcom/android/server/pm/OneOSInstalldTable;->code(Ljava/lang/String;)I
   move-result vN
   ```

   `vN` is an operand of the non-range `invoke-interface … transact`, so it is
   v0–v15 and fits the 35c `invoke-static`; the register holds the String
   only between the first two instructions. Because a line becomes three, the
   method's `end` index grows by 2 before `i = end + 1` (the current code
   relies on unchanged length in this branch). Exit (fail the build) if the
   `const` is not found, if `vN` > v15, or if anything other than these three
   lines writes `vN` between the `move-result` and `transact`.
4. **Blocked methods**: unchanged (the `RemoteException` stub before any code).
5. **Helper class.** Copy `OneOSInstalldTable.smali` next to
   `OneOSInstalldProxy.smali` (the `Installer` dex, not the full
   `classes.dex`); exit if it already exists, if its class line is not
   `.class public final Lcom/android/server/pm/OneOSInstalldTable;`, or if it
   lacks `code(Ljava/lang/String;)I` or the exact path string
   `"/oem/oneos/host_installd.table"`. The helper is generated from a
   checked-in `OneOSInstalldTable.java` (javac against `android.jar` plus a
   compile-only `android.os.SystemProperties` stub, `d8`, `baksmali`) and the
   `.smali` is checked in, like `OneOSPanelBacklight.smali`, so
   `make-overlays.sh` needs no javac. Its logic is §6.3 (guest row): lazy
   synchronized load, `catch (Throwable)` → invalid, `HashMap<String,Integer>`
   keyed `name + sig`, `code()` throws `RemoteException` when invalid or when
   the key is missing.
6. **Fail-closed checks kept/added**: every guest method is mapped or blocked
   (the `missing` check); `destroyUserData` is blocked and `createAppData`
   mapped; the number of `OneOSInstalldTable;->code` call sites in
   `OneOSInstalldProxy` equals the number of mapped methods; no `asInterface`
   path left (unchanged `redirect_callers`).
7. **Report.** `--report` writes `{"tableFormat": 1, "guestTablePath": …,
   "mapped": [{name, sig, guestCode}], "blocked": [names]}`, which
   `make-package.sh` copies into the manifest's `installd` (§5.3). Stderr
   becomes `IInstalld: 27 mapped at runtime, 31 blocked (in …)`.
8. **Docstring** and `host-installd-table.sh` usage text: the host table is
   produced on the phone at runtime; `host_installd.txt` stays as the F8U test
   fixture.

`check-guards.py` gains the matching check (`installd-runtime-table`): each
mapped method's string constant is its own name + signature, it calls
`OneOSInstalldTable.code` exactly once before `transact`, and the helper
contains no file-write API.

### 6.6 Script changes this needs (dependencies, owned by the scripts owners)

- `guest_prepare.sh`: after the `guards.txt` block, validate
  `$STAGE/host_installd.table` (§6.3) or exit 3; in the `/oem` block
  (`:262-278`) always rebuild `$STAGE/oem`, copy the table to
  `$STAGE/oem/oneos/`, add the RRO only for fold + grid as today, bind and
  remount `ro`.
- Dev path until the app exists: `host-installd-table.sh` gains a mode that
  prints format 1 given the jar and the phone's `ro.build.fingerprint`;
  `deploy-phone.sh` pulls both from the phone, builds the table on the server
  and pushes it to `$STAGE/host_installd.table`.

### 6.7 Tests

- Server, Python: the patcher on both held images gives 27 mapped / 31
  blocked, exits on the negative fixtures (missing `const`, helper already
  present, wrong helper class line).
- Server, JVM: `OneOSInstalldTable.java` on fixtures: valid; wrong magic;
  wrong fingerprint; missing or wrong trailer; duplicate name or code;
  trailing bytes; over 64 KiB → invalid and every lookup throws; a valid table
  with a signature mismatch → that lookup throws, others map.
- Server, Kotlin: `HostInstalldTable` on the F8U `services.jar` held on the
  server (never committed) reproduces `host_installd.txt`'s 85 entries;
  `InstalldTableWriter` output passes the shell validator.
- Phone: one session via the dev path (§6.6): logcat shows the table loaded
  (85 methods), Settings > About storage works (the runs 26–29 regression),
  and a table with a wrong fingerprint is refused by `guest_prepare.sh`.

---

## 7. Data formats (final schemas)

All JSON is `kotlinx-serialization` in `:core:model`; each carries a `schema`.
Full field lists of the older schemas live in the study docs.

| Schema | Producer → reader | Definition | Notes |
| --- | --- | --- | --- |
| `oneos.package/1` | server → app, scripts | §5.3 | signed |
| `oneos.index/1` | server → app | §5.5 | signed; replaces `oneos.fixpack-index/1` |
| `oneos/patch-catalog/1` | package/pack → app | `patch-catalog.md` §5 | per package |
| `oneos.guards/1` | server → manifest | `compat-safety-logs.md` §2.3 | inside the manifest; `guards.txt` shipped for the scripts |
| `oneos.installd-table 1` (text) | app → scripts → guest | §6.2 | `$STAGE/host_installd.table`; replaces `host_installd.json` |
| `oneos.compat/1` | `CompatEvaluator` | `compat-safety-logs.md` §1.9 | phone × package |
| `oneos.logbundle/1` | `:core:logs` | `compat-safety-logs.md` §3.4 | records package id/serial |
| `oneos.fixpack/1` | server → app | `compat-safety-logs.md` §4.2 | `match.packages` added |
| `session.env` | app → scripts | key=value allow-list | §7.1 |
| `active_package.json`, `staged.json`, `preflight.json` | root scripts | §5.7, §4.2 | under `$STAGE` |

Not used in the first release: `oneos.image/1`, `oneos/patch-plan/1`,
`oneos.build/1` (`patch-engine.md`, later option).

Reconciled naming: application id and root package **`com.fahadali.oneos`**; the
guard record is **`guards.json`/`guards` object** (schema `oneos.guards/1`),
never `guard_manifest.json`; the stage path stays
`/data/local/tmp/oneos`; catalog ids (`safety.storage_guards`, …) in
manifests, plans and bundles.

### 7.1 `session.env` (app → scripts)

The app writes one env file per prepared session from the resolved catalog;
the launcher in `oneos_preflight.sh` runs `set -a; . $STAGE/session.env;
set +a` and then `oneos_switch.sh`, so the scripts keep reading
`${ONEOS_*:-default}` unchanged. Only allow-listed keys (`patch-catalog.md`
§8) appear; a locked entry emits no key. Example (F8U, Find N6 package,
defaults):

```
ONEOS_GUEST_FORM=fold
ONEOS_GUEST_FOLD=layout
ONEOS_GUEST_5G=1
ONEOS_GUEST_DUAL_5G=1
ONEOS_GUEST_MOBILE_DATA=1
ONEOS_GUEST_CALL_SIM=1
ONEOS_GUEST_RINGTONES=1
ONEOS_GAP_SPLASH=1
ONEOS_GAP_FAST=1
ONEOS_RETURN_BLACK=150
ONEOS_RETURN_MAX=600
```

Patches built into the package's files (`files[].patches`) have no env var
and no toggle in this release; the Patches screen lists them as "built in".

> **Friend build 2 (0.3.0)** writes a fixed allow-list instead of the catalog
> (`SessionEnv` in `:core:model`): the 13 keys `ONEOS_APP=1`, `ONEOS_PROFILE`,
> `ONEOS_SPLASH_COMPONENT`, `ONEOS_WALLPAPER_PROBE=0`, `ONEOS_RECORD=0`,
> `ONEOS_LOGCAT=1` and the seven form keys (`ONEOS_GUEST_FORM`,
> `ONEOS_GUEST_FOLD`, `ONEOS_COVER_TSP`, `ONEOS_GUEST_FOLD_CONTINUE`,
> `ONEOS_GUEST_UNFOLD_PORTRAIT`, `ONEOS_GUEST_COMPACT_WINDOW`,
> `ONEOS_GUEST_WALLPAPER_GRID`: today's defaults on the Fold, all off with
> `ONEOS_GUEST_FORM=phone` on an S Ultra), each exactly once. No return,
> tunnel, stock-SF or keep-fold-layout key is ever written, and the root
> script's `env` and `launch` refuse a file with any other key or value. The
> launcher is the root script's `launch` verb, not `oneos_preflight.sh`
> (section 11, Friend build 2). 0.3.3 adds a 14th key,
> `ONEOS_GUEST_HIDE_GMS` (Prepare writes 0; `launch` writes the Switch
> screen's choice for that launch, 1 only for an image with Google services;
> from 0.3.7 only for one whose sessions do not present them,
> `ImageRef.gmsHideable`, which no built-in image is).

---

## 8. Flows

### 8.1 Add a package link

Paste/share the index URL → verify → list matching packages with compat level,
status (tested/untested), size and "tested on" → the user picks one (§5.7
steps 1–2). Nothing is written outside the app sandbox.

### 8.2 Download, unpack, stage, activate

§5.7 steps 3–7. Download and unpack run unprivileged; root is used only to
move, re-hash, link and label. Activation never happens during a session.

### 8.3 Installd table

§6.4, at every app start and before every preflight; One UI OTA →
rewritten; failure → BLOCK with the reason on the compat screen.

### 8.4 Preflight + session

App → `oneos_preflight.sh` (G1–G16, `preflight.json`) → `oneos_switch.sh`
with `session.env`. The switch stops One UI's framework, binds the bridges,
guards and the table, pivots into the guest (`guest_prepare.sh`/
`guest_start.sh`), the activator finishes the boot, the watcher arms
auto-return (black 150 s, no-home 600 s, no-zygote 30 s, guest power request)
and the Vol-Up+Vol-Down 3 s keys.

### 8.5 Return + logs

`return_to_oneui.sh` kills guest processes by mount namespace, restores
`persist.*`, unmounts exactly `/proc/mounts` entries under the stage, checks
`/apex`, and **reboots**. Temp root is lost, so after the next boot the app
posts a notification and, once root is back, `SessionLogCollector` gathers the
session files, `Redactor` masks personal data on the phone
(`compat-safety-logs.md` §3.3), the preview screen lists files + masked
counts, and the user shares the zip via `FileProvider` (no network call by
the app). The bundle records the package id/serial and the installd table
hash. Run 33 is the worked case: `auto_return.log` → `guest requested 'reboot'
after 350s` and a later `… gone for 30s after 590s`; the app would show
"ColorOS stopped ~10 min in; OneOS returned to One UI by itself" with Share
logs.

### 8.6 Fix packs

Listed in the index; matched by `match.packages` (id + serial range) and the
phone; verified (§4.6); may replace package scripts, the catalog, RROs and
redaction additions, never `files/*` jars or the image (those need a new
package serial); pin/rollback keeps the last three verified versions; never
activates during a session.

---

## 9. What reuses existing scripts

- **Server, as they are**: `build-gsi.sh`, `make-overlays.sh` (one patcher
  call changes, §6.5), `switcher/patches/*.py`, `check-dex.py`,
  `make-bootsplash.py` (the gap-splash PNG goes into the APK).
- **Server, new**: `make-package.sh` (§5.6), `check-guards.py` (§4.4),
  `OneOSInstalldTable.{java,smali}` (§6.5), `packages/<id>.json` profiles.
- **Shipped in the package, driven by `session.env`** (our own code already,
  not OneLineage's — the import `3cff27f` has been fully rewritten; every line
  of `guest_prepare.sh` passed through later commits): `oneos_switch.sh`,
  `guest_prepare.sh`, `guest_start.sh`, `guest_props.sh`, `bridges.sh`,
  `check_host_apex.sh`, `return_to_oneui.sh`, `zygote_exec`.
- **Ported into the app**: `host-installd-table.sh` (→ `HostInstalldTable`,
  §6.4); the push/verify half of `deploy-phone.sh` (→ `:core:package`);
  `pull-run-logs.sh` (→ `:core:logs`). The scripts stay for the dev loop.
- **Dropped / not shipped**: `oneos_tunnel.sh`, the OneLineage prebuilt
  binaries (`framework_patched.jar`, `PermissionController_patched.apk`,
  `7zz`, `libaudio*_patched.so`), `ONEOS_RETURN_MODE=inplace`.
- **Script changes other work must land** (not edited here): the installd
  table validation + `/oem` bind (§6.6); read the jar list from the manifest
  instead of hard-coding `oplus-services_patched.jar` (`guest_prepare.sh:32`);
  mount `ro,noload` (`guest_prepare.sh:81-84`); pass the return reason to
  `return_to_oneui.sh` and write `session/last_return.json`; `lineage.*`
  entries must stop running for ColorOS (`patch-catalog.md` §6.6).

---

## 10. Open questions and risks

Open decisions:

1. **Signing key custody + where packages and releases live.** (The APK
   signing key exists since 0.2.1-probe: RSA 4096 `CN=OneOS`, kept in
   `~/.oneos-release/` of the build account, see `app-android/README.md`,
   "Build"; testers only ever get release builds.) One Ed25519
   key signs packages, the index and fix packs (offline backup key for
   rotation only). Who holds it, and does `make-package.sh` sign on the
   server or is it signed by hand? Which GitHub `owner/repo` hosts the
   app releases and the index? GitHub release assets must be under 2 GiB, so
   images go up as parts (§5.4), or the images are served from our own
   server over HTTPS with the index on GitHub.
2. **S26 Ultra: WARN, not BLOCK?** Nothing has run on an S26 Ultra and the
   Find X9 Ultra package is untested (and carries the F8U backlight table,
   §5.8). Confirm testers' S26 Ultras **run on WARN** (Snapdragon, same SDK,
   untested package) and we lean on log bundles → fix packs / new serials,
   rather than BLOCK until one is tested.
3. **OneLineage permission (granted 2026-10-24).** OneLineage has no license
   file. Its author, WeWaffles, gave written permission to publish OneOS on
   top of it with full credits in the app and on GitHub (`CREDITS.md`); the
   app's About credits OneLineage with its GitHub link. Still open: the
   license under which third parties may reuse the OneLineage-derived files
   (WeWaffles' agreement to the repository's license).
4. **Status bar: 4G instead of 5G, and no signal bars.** Run 34: mobile data
   works, but ColorOS's status bar shows 4G where One UI shows 5G and draws
   no signal bars. Evidence so far: Samsung's RIL never sets
   `isEndcAvailable`, so Android shows 5G only while an NR leg carries the
   internet data call (`docs/coloros-on-fold.md`, Radio); in run 33's guest
   `telephony_registry` dumps (`diag_40`, `diag_90`) `mSignalStrength` was
   invalid on both SIMs (every RAT `2147483647`, level 0) while the service
   state was IN_SERVICE on LTE, so the bars have no data to draw: the problem
   is upstream of SystemUI (signal indications from Samsung's radio HAL not
   reaching or not parsed by ColorOS telephony; OPPO's NR calls go to a
   vendor radio service that does not exist here). Ship the friends build
   with this as a known issue, or hold for a fix? Either way the next session
   should capture `dumpsys telephony.registry` with Wi-Fi off and mobile data
   on, plus the radio logcat buffer.

Resolved since the first draft: SIM 2 call audio (works, run 34); the run-33
screen-off hang (the Power + Volume Down screenshot crash, fixed in
`oplus_boot_hangs.py`); on-phone build time (no on-phone build in this
release).

Further risks (no decision needed now): guard coverage beyond two jars and
native guest daemons; the installd table is the Java proxy's view, not the
native daemon's; build-pinned anchors (`display_mode_specs.py` `.line 252`,
the surfaceflinger SHA-1) mean each new OS build may need patcher work on the
server before a package exists; device values baked into packages (§5.8);
root under Magisk/APatch and the KernelSU allowlist drop are untested; about
16 GB of transient space on the phone during download + unpack; redaction is
best-effort (the preview screen is the backstop).

---

## 11. Implementation plan

Each milestone is one focused work session. Server acceptance runs on the
build server (gradle tasks, unit tests, scripts, lint). Phone acceptance uses
the reference phone only where a milestone needs it. **M1–M2 and M4 never
touch One UI's data**; M3 runs one dev-path session; the app's first stage
writes are in M5, only under `$STAGE`; the app's first guest boot is M7.

### M1 — SESL app skeleton + device report (no phone data)

- **Deliverables.** Gradle project (`com.fahadali.oneos`, AGP 9.3.3, Gradle 9.5.0, JDK
  21, `compileSdk release(37)`, target 36, `minSdk 31`); modules `:app`,
  `:core:model`, `:core:device`, `:core:root` (read-only su facts). SESL deps
  with the verified stock-AndroidX and `picker-color` excludes. Device report
  screen (`ToolbarLayout` + `RecyclerView`/preferences) showing the facts of
  `compat-safety-logs.md` §1 (model, SoC, One UI/SDK, fingerprint,
  displays/ports, form, root manager, free space, battery, screen lock: WARN
  in M1, BLOCK at switch time from M7, G16). First-launch Before you start
  screen with the acknowledgement checkbox. No stage, no writes except that
  acknowledgement in app-private SharedPreferences.
- **Server acceptance.** `:app:assembleDebug`, `:app:lintDebug` (0 errors),
  `:core:model:test` green.
- **Phone acceptance.** Install, open, see correct facts for the F8U; confirm
  with `getprop`/`dumpsys`; no writes outside the app sandbox.
- **Dependencies.** None.

### Friend build 1 — probe build (0.2.0-probe, between M1 and M2)

- **Goal.** Friends install it, run read-only tests as root and send
  the findings; the team verifies them and only then ships a build that can
  switch. Nothing on the friend's phone may change.
- **Deliverables.** *Run tests* screen (dialog, `su -c id`, per-test
  progress), the one auditable root command list
  (`app/src/main/assets/probe/commands.list`) with its runner and
  `ProbeAudit`, the base64 stream (root writes no file), the CPU feature
  check (WARN "CPU lacks ... used by the ColorOS images", also in the device
  report), the Android-version WARN, on-phone `HostInstalldTable` with the
  raw dex as the primary output, `Redactor`, `findings-<model>-<date>.zip`
  with report.json (`oneos.findings/1`) + summary.txt, preview, share sheet
  (SESL core FileProvider) and Save to Downloads (SAF). Details:
  compat-safety-logs.md §7.
- **Server acceptance.** `assembleDebug test lintDebug` green; redaction,
  CPU parsing, verdict, list audit, stream and bundle tests; no permission in
  the APK; the runner checked under dash/ash/bash and the F8U dex derivation
  equal to `host_installd.txt`.
- **Phone acceptance.** On the F8U: all tests ok or not present, the zip's
  `installd/table.txt` equals the server derivation, `getprop` shows no
  serial/IMEI/MAC; nothing outside the app's own folders changed.

### Friend build 2 — the first build that switches (0.3.0, versionCode 4)

- **Goal.** An S Ultra friend downloads
  `OneOS_ColorOS17_FindX9Ultra_S26U.img.gz`, picks it in the app, which
  verifies it, stages it with the S Ultra profile, runs every gate and
  switches; Volume Up+Down (3 s) returns to One UI. The main test Fold does the
  same with the Find N6 image (or the image already on the phone, keeping its
  ColorOS data). No adb, no server, no OneLineage switcher on the phone. It
  takes the M5-M8 parts this needs, without the signed manifest, download or
  fix packs (those stay in M4/M5/M9).
- **Profiles and image table** (`:core:model`, workstream B1): `Profiles`
  (model prefix AND codename AND SoC: `f8u`, `s-ultra-8850`; `s-ultra-8750`
  disabled in 0.3.0), `Images` (both images' .gz and raw size and SHA-256),
  `PackageSets` (`n6-f8u`, `x9u-sultra`), `SessionEnv`, `CarrierRules`
  (VoLTE-only WARN to tick), `SwitchGates` (Prepare and Switch gates; BLOCK
  has no override, anything that cannot be read is BLOCK).
- **The root path** (`:core:root` and `assets/root`). Every change as root is
  a verb of `assets/root/oneos_root.sh`: `begin <new|keep|aside>`, `receive
  <name> <bytes> <sha256>` (stdin), `keep-raw`, `table`, `env`, `finish`,
  `launch <session|dry>`, `recover`. Root runs it only from
  `$STAGE/bin/oneos_root.sh`, root's and writable by root only, and only when
  its SHA-256 is the one pinned in BuildConfig; the launcher
  (`RootScript.TEMPLATE`, a fixed text with the arguments, the pin and the
  length filled in) may install it there only for `begin`, from stdin, after
  the same hash check. Arguments are fixed words, decimals and hex. Writes
  go under `$STAGE` only, with two documented exceptions (`begin aside`
  renames the stage to `oneos.old-<epoch>`; `launch` leaves the
  app's cgroup and starts the session); nothing is deleted except the
  script's own temp files and an old `system.raw` that a new one replaces;
  whatever is in the way goes to `$STAGE/attic/<epoch>/`. `RootShell` streams
  stdin (the .gz is unpacked by the app through `GZIPInputStream` into
  `receive system.raw`, root writes it with `head -c`, non-sparse, and
  checks its size and SHA-256 itself). The read-only stage check
  (`assets/root/status.list`), the installd read (`assets/root/installd.list`)
  and the log collection (`assets/logs/collect.list`) are probe-grammar lists
  run by `probe.sh` and audited by `ProbeAudit` like the probe.
- **Files written into the stage** (the contract with the session scripts):
  every staged file with its mode, `files.sha256` (all but `system.raw`),
  `system.raw.id` (`<size> <sha256> <dev:inode:size:mtime>`),
  `host_installd.table` (format 1; root checks this phone's fingerprint, the
  source jar's hash, the trailer, and that its methods equal the staged
  `host_installd.txt`, whose method lines hash to `InstalldExpected.SHA256`),
  `session.env`, and last the marker `.oneos_stage` (exactly
  `StageMarker.toJson()`). `launch` re-checks all of it plus the phone's ids,
  SDK 37, mounts and bridges, an unfinished session, busybox and resetprop at
  the root manager's paths, the old switcher (`pm path`), the volume keys
  (`getevent -pl`), the battery and 11 GiB free, then writes
  `$STAGE/session/current.json` and runs `nsenter -t 1 -m -- setsid sh -c
  'set -a; . session.env; set +a; exec sh oneos_switch.sh'` detached,
  output appended to `takeover_app.log`. The screen lock is re-read by the
  app right before (KeyguardManager); a root-side read is not built yet (see
  below).
- **Screens.** Home: OS image, Prepare, Switch to ColorOS, Last session.
  OS image: the profile's image, Pick the downloaded file
  (`ACTION_OPEN_DOCUMENT`, persisted read grant), Check file (SHA-256 with
  progress), "Use the image already on this phone" when the stage holds a
  `system.raw` of the right size. Prepare: the checks, the stage folder
  (new / Keep my ColorOS data (0.3.7: Keep its apps and data) / Move it aside), the steps with progress, Stop,
  screen kept on, then "Delete the downloaded file". Switch: how to get back,
  every Switch gate, the boxes to tick (untested phone, calls on this
  carrier), Dry run and Switch behind dialogs. `GapSplashActivity`
  (`com.fahadali.oneos/.ui.GapSplashActivity`, not exported, the old
  SplashActivity's frame and `Status: ok` handshake). Last session: reboot
  detection (boot time from wall clock minus uptime against the saved launch
  time), Collect logs (redacted as it streams, `oneos-logs-<session>.zip`,
  `oneos.logbundle/1`), the outcome from `auto_return.log` /
  `takeover_app.log`, Share/Save through the findings preview, and Restore
  One UI's settings (`recover`) after a session that never returned.
- **Packaging.** `app/build.gradle.kts` task `oneosFiles` imports
  `out/overlays` (set `n6-f8u`, without `tethering_payload.img`) and
  `out/overlays_x9u` (set `x9u-sultra`, also without
  `OneOSWallpapersFoldGrid.apk`) into `assets/oneos/files/<sha256>`
  (deduplicated) and fails when any file differs from the checked-in
  `app-android/packages/<set>.sha256`; the session scripts, `zygote_exec`,
  `bridges.sh` and `host_installd.txt` are copied from `switcher/` at build
  time with their list hash in BuildConfig (`oneos_tunnel.sh` and `7zz` are
  never shipped; any other new file in `switcher/assets` fails the build).
  APK about 255 MB (378 MB of files, deflated). Release-signed with the
  OneOS key as before.
- **Server acceptance.** `assembleDebug assembleRelease test lintDebug`
  green. `StageScriptTest` runs `oneos_root.sh` and its launcher under dash
  and busybox ash against a fake root folder (`ONEOS_TEST_ROOT`, refused as
  uid 0; `launch` refuses after its checks): the full preparation for both
  profiles, refusals that leave the stage unchanged (mounts, bridges, a loop
  device, `RETURN_MAX=0` and unknown keys, another fingerprint, a short or
  wrong file), a world-writable foreign stage moved aside, the Fold's stage
  kept with its leftovers in the attic, `keep-raw` of a wrong image, a changed
  or unpinned script never run. `StageAuditTest` audits the script and the
  launcher (allow-listed commands; every write under the stage; no user
  data paths, reboot, settings, wipes or mounts) and checks the script's
  tables against the model.
- **Phone acceptance (not run from here).** The Fold path from the
  app-architecture study: install over 0.2.1-probe, run the probe again,
  uninstall the old switcher, OS image → Use the image already on this phone,
  Prepare with Keep my ColorOS data, set a PIN and see Switch BLOCK, remove
  it, Dry run (survives the app's death, the return restarts the phone), a
  full session with Volume Up+Down, Collect logs and compare with
  `pull-run-logs.sh`, then `find -newer` outside the stage. The .gz path is
  tested separately; the X9U image is never run on the Fold.
- **Not in this build.** A root-side screen-lock read (`dumpsys
  lock_settings` only after its output was checked on the Fold); the
  previous session's capture (`oneos_logs.prev`), tombstones and reset nodes
  in the log bundle; a way to clear `oneos.old-*` and the attic
  from the app; resumable staging; a foreground service.

### Friend build 2, 0.3.3 (versionCode 7) — the Find X9 Ultra IN image

> 0.3.7 removed the IN image and its two sets (the server build was
> deleted); the Fold's second image is the Pixel 11 Fold one (below). The
> mechanisms here (choices, the image deciding the set, the root tables,
> guest data per image, the hide key) stay.

- **Goal.** A second image choice: the Find X9 Ultra IN build
  (`coloros17-findx9u-in`, `OneOS_ColorOS17_FindX9Ultra_IN.img.gz`, Android
  17, Google services), on the Fold and both S Ultra profiles, untested.
- **Model.** `PhoneProfile.choices` replaces the single image/set/tested:
  F8U takes Find N6 → `n6-f8u` (tested) and Find X9 Ultra IN → `x9u-in-f8u`;
  the S Ultra profiles take Find X9 Ultra → `x9u-sultra` and Find X9 Ultra IN
  → `x9u-in-sultra`. The gates are for the chosen image (PREPARE: the picked
  .gz or the stage's `system.raw`, identified by size and SHA-256 against
  what the phone takes; SWITCH: the marker's image with exactly its set):
  its set, CPU rule, free space and the untested tick come with it. An image
  the phone does not take is a BLOCK naming the ones it does.
- **Root.** `begin` and `finish` name the set; `profile_set` (profile, image
  → set) and `set_image` (set → image) must agree, or root refuses (begin,
  plan, finish, launch). Marker `oneos.stage/2` with the set (`/1` still read
  for keep and recover, never switched). `launch` takes `hideGms` and (0.4.20) `secIms` and writes
  `ONEOS_GUEST_HIDE_GMS` and `ONEOS_GUEST_SEC_IMS` into `session.env` after
  its checks; `current.json` records image, set, `hideGms` and `secIms`. Guest data stays with
  the image that made it: `begin keep` refuses another image's (marker, or
  the plan of an unfinished preparation) and Prepare offers only Move it
  aside then. The launcher also installs the pinned script for `recover` (a
  stage with a marker, root's folders only), because 0.3.2's script is not
  0.3.3's pin and its unfinished session must stay restorable.
  `StageAuditTest` checks the new tables against the model; `StageScriptTest`
  covers the IN sets, a mismatched set, Google services on a CN image, a
  0.3.2 stage, its recover, and keep across images.
- **Packaging.** `x9u-in-sultra` and `x9u-in-f8u` from `out/overlays_x9u_in`
  (both with the IN build's `cellbroadcast_payload.img`), checked against
  `app-android/packages/` like the others.
- **Switch.** "Hide Google services for this session", only for an image
  with them, off by default and never saved.
- **Not tested on a phone** (none of the IN pairs has run).

### Friend build 2, 0.3.4 (versionCode 8) — Galaxy S25, and OneOS Probe on its own

- **Goal.** Support a tester's Galaxy S25 (base) from its verified probe
  findings (0.2.1-probe, 2026-10-23: SM-S931B, `pa1q`, SM8750, Android 17,
  One UI 9.0, vendor API 202404, one panel, installd table equal to
  `host_installd.txt`), and keep the probe as an app of its own so anyone can
  run it and share the findings.
- **Weaver guard** (442568e, `safety.weaver_guard`): the rebuilt sets'
  `services.jar` gives the guest no weaver service, and `guest_prepare.sh`
  drops a pre-guard guest lock state from the stage; the package lists are
  regenerated. Nothing below 0.3.4 should switch.
- **Model.** Profile `s-8750` "Galaxy S25" (`SM-S931` + `pa1q` + `SM8750`,
  BAR), the S Ultra's choices (Find X9 Ultra → `x9u-sultra`, Find X9 Ultra
  IN → `x9u-in-sultra`, both untested) and the S25 Ultra's note. **Scope**:
  in scope is a Z Fold / Z Flip / S Ultra by model number *or* a phone that
  matches an explicit profile (`CompatEvaluator.inScope`); every other
  S-series model stays BLOCK `model-out-of-scope`. Root's `profile_info` and
  `profile_set` carry the new rows (`StageAuditTest`, `StageScriptTest`).
- **Two apps, one codebase.** Flavor dimension `edition`: `full` is OneOS
  (`com.fahadali.oneos`, `0.3.4`), `probe` is OneOS Probe
  (`com.fahadali.oneos.probe`, `0.3.4-probe`, versionCode 8 for both, the
  same release key, installs next to OneOS). Shared code and the probe runner
  stay in `app/src/main`; OneOS's session code, switching screens, root
  script, stage/installd/log lists, their strings and manifest entries are in
  `app/src/full`; `src/probe` has only its home, Before you start (it only
  reads), provider paths (findings only), icon and strings. The `oneosFiles`
  import and the root pins are the full flavor's. A build check
  (`ProbeApkCheckTask`) refuses a probe APK with any of OneOS's assets,
  code, screens or a permission, or over 30 MB; `EditionsTest` checks the
  source sets. Root has a grant per app, so every root prompt and finding
  names the app that asks (`app_name`; `CompatEvaluator.evaluate(app =)`,
  `AppInfo.name`) and OneOS Probe's texts say the results are its own; the
  check also refuses a probe APK whose strings say to allow "OneOS".
- **Not tested on a phone** (no session on a Galaxy S25; OneOS Probe not
  installed yet).

### Friend build 2, 0.3.7 (versionCode 11) — the Pixel 11 Fold image

- **Goal.** The primary guest is now the Pixel 11 Fold image (yogi,
  `google/yogi/yogi:17/CD1A.261005.003.B1`, runs 41-44 on the Fold over adb,
  `docs/pixel-guest.md`); the app offers it on the Fold so the showcase
  (OneOS app → Switch → Pixel setup wizard → Pixel → Back to One UI from the
  in-guest OneOS app) runs from the app. The Find X9 Ultra IN build was
  deleted from the server, so its image and sets go. The Find N6 and Find X9
  Ultra images and sets are unchanged.
- **Model.** `Images.PIXEL_YOGI` (`pixel11fold-yogi`, name "Pixel 11 Fold",
  no variant, `OneOS_Pixel11Fold_Full_ZFold8.img.gz` 3288346862 B, raw
  6559223808 B, tested on the Z Fold (F8U), Google services). CPU rule from
  the image's `linker64` (disassembled): SVE and SVE2 required (unguarded in
  the loader), SME and MOPS only behind runtime checks. F8U's choices: Find
  N6 → `n6-f8u`, Pixel → `pixel-f8u`, both tested; the S Ultra profiles and
  the S25: Find X9 Ultra → `x9u-sultra` only. `ImageRef.presentsGms`: the
  Pixel image's set stages GmsCore and the session presents it, so a launch
  cannot hide Google services there (`oneos_switch.sh` refuses
  `ONEOS_GUEST_HIDE_GMS=1` with the payload staged and `ONEOS_GUEST_GMS` on,
  which `session.env` cannot set); `gmsHideable` = Google services and not
  presented decides the Switch toggle, `SessionEnv.validate`, `LaunchJob` and
  root's `IMAGES_GMS` (empty).
- **The set.** `pixel-f8u` from `out/overlays_pixel_yogi` is exactly what a
  Pixel session uses (`guest_prepare.sh`): `services_patched.jar`,
  `vold_patched` and `service.incremental_patched.so` (the guest vold as
  "gvld", pinned by `guards.txt`, both or none), the signal poll
  (`oneos-telephony.jar`, `oneos-telephony.sha256`, `OneOSPhoneInjection.apk`),
  `OneOSPixelStatusBar.apk`, `OneOSGuest.apk` (`hasReturnApp`: the session
  copies it to the guest's `/oem/app`) and 22 APEX payloads (with an app
  session `guest_prepare.sh` refuses an image module that has no staged
  payload, so every mounted one is there; `tethering_payload.img` is never
  mounted and is left out). File roles `GUARD_EXECUTABLE` (0755),
  `GUARD_LIBRARY`, `GUEST_APP`, `INJECTION_JAR`, `INJECTION_SHA256`.
  `checkGuards` covers the gvld binaries and, for a set with GmsCore, the
  guard names Google services need in `guards.txt`'s comments.
- **Root.** The Pixel rows (`profile_set`, `image_raw`, `set_files` with
  `SET_PIXEL`, `set_image`), `vold_patched` 0755, and `oneos-*` among the
  leftovers `check_files` refuses (`StageStatus.LEFTOVER` too). `finish`
  still moves every other flat file to the attic, so a stage switched between
  the ColorOS and the Pixel set never keeps the other set's files where the
  scripts would use them; guest data stays with its image (keep refused,
  move aside). `StageAuditTest` checks `SET_PIXEL`, `set_image`, the modes
  and the leftover patterns against the model; `StageScriptTest` prepares
  and launch-checks a Pixel stage, switches the Fold's stage both ways and
  refuses the other set's files.
- **Packaging.** `pixel-f8u` replaces `x9u-in-sultra` and `x9u-in-f8u`
  (`app-android/packages/`); the release APK grows to about 500 MB (the
  Pixel files deflate worse than the IN ones). The packaging task refuses a
  set file over root's 256 MiB `receive` limit (`gmssystem_payload.img` is
  155 MB).
- **Guest data per system** (the review). `ImageRef.family` (COLOROS, PIXEL)
  and `GuestData.PIXEL` (Pixel's launcher in `packages.xml`, read by
  `status.list`): `beginModes` offers Keep only for data of the image's own
  system, on OneOS's stage, a stage whose preparation stopped and one
  `deploy-phone.sh` made; `SetupPlan` keeps a stopped Pixel update whose
  `system.raw` root verified again, as it keeps a ColorOS one; root's `begin
  keep` refuses another system's data (`image_family`, `data_family`) from
  any stage. The older screens' texts name `{system}` or "the other system"
  (StringsNeutralTest), the Switch dialog says what to skip in the setup
  wizard of an image that presents Google services, and Restore after a
  Pixel session says it restored the language only.
- **Not tested from the app on a phone** (the Pixel image has run only from
  `scripts/deploy-phone.sh`); the upload is not in the shared folder yet.

### M2 — Compat evaluator + advisory gates

- **Deliverables.** `FactProbe` (form via panel count + lid input + model
  prefix; SoC; root kind), `CompatEvaluator` → `oneos.compat/1` against a
  package's `supports`/`tested` (fixture manifests), `GateRunner` for G9–G13;
  compat screen with OK/WARN/BLOCK and finding ids.
- **Server acceptance.** Unit tests over synthetic facts × the two fixture
  manifests reproduce §4.5: F8U × N6 = OK; S26U × X9U = WARN; Exynos,
  cross-SDK, wrong family = BLOCK.
- **Phone acceptance.** On the F8U the report matches; no `$STAGE` created.
- **Dependencies.** M1.

### M3 — Runtime installd table (server patcher + app derivation)

- **Deliverables.** §6 complete: the `guest_installd_abi.py` change and
  `OneOSInstalldTable.{java,smali}` (§6.5), the `check-guards.py`
  `installd-runtime-table` check, the `guest_prepare.sh` validation + `/oem`
  bind and the dev-path table (§6.6) — landed by the scripts owners — and in
  the app `HostInstalldTable` + `InstalldTableWriter` + the compat line
  "installd: N of N allowed calls map".
- **Server acceptance.** §6.7 server tests; `make-overlays.sh` on both held
  images builds with no `host_installd.txt` input; the F8U derivation equals
  the fixture.
- **Phone acceptance.** One session (run 35) via `deploy-phone.sh` with the
  runtime table: guest boots as in run 34, the table loads (85 methods), About
  storage works; a wrong-fingerprint table is refused (exit 3). The app shows
  "27 of 27" on the F8U.
- **Dependencies.** M1 (app part); none for the server part, which can run in
  parallel with M1/M2.

### M4 — Package format + `make-package.sh` + index (server only)

- **Deliverables.** `oneos.package/1` and `oneos.index/1` in `:core:model`
  with canonical-bytes writer/reader; `scripts/make-package.sh` +
  `packages/coloros17-{findn6,findx9u}.json` profiles (§5.6); `check-guards.py`
  complete (§4.4); a test signing key (the release key is §10, question 1);
  `ManifestVerifier` (tink) as a JVM unit.
- **Server acceptance.** Both packages build from the run-34 tree; every
  manifest hash recomputes; signature verifies with the public key and fails
  after a one-byte change; a rebuild gives identical files and hashes except
  `issued`; `installd` block equals the patcher report; the N6 package has the
  fold RRO and no tethering payload, the X9U package neither.
- **Phone acceptance.** None.
- **Dependencies.** M3 (the runtime-table jars and the report).

### M5 — App: download, verify, unpack, stage, activate

- **Deliverables.** `:core:package` (index client, manifest verify,
  resumable downloader, sparse gunzip with hashing), `oneos_stage.sh` (stage,
  activate, write-table, per-package `$STAGE/data` rename), Packages screen.
- **Server acceptance.** Unit tests: tampered manifest / unknown key / older
  serial / revoked / wrong part hash / wrong raw hash all refused; unpack of
  a test ext4 image keeps holes and matches `rawSha256`; a shell harness runs
  `oneos_stage.sh` against a fake `$STAGE` and checks it refuses with a fake
  mount under `$STAGE/data`.
- **Phone acceptance.** On the F8U, add the index link, download the N6
  package over Wi-Fi (resume after a forced interruption), stage and activate
  it; flat names hash to the manifest; `system.raw` identical to the run-34
  image; the activated flat names equal the run-34 stage listing except the
  files §9 drops on purpose; One UI `/data` unchanged (before/after
  `find -newer` outside `$STAGE`); activation refused while a session is up.
- **Dependencies.** M1, M4.

### M6 — Catalog, toggles and `session.env`

- **Deliverables.** Catalog loading per package, predicate evaluator,
  `PlanResolver` → resolved toggles, safety locked, built-in entries shown,
  hidden-when-inapplicable; `session.env` compiler (allow-list); Patches
  screen with advanced/dev gating.
- **Server acceptance.** Golden env files for F8U × N6, S26U × X9U match the
  defaults (`patch-catalog.md` §7); no safety entry togglable; no
  gate-weakening key ever emitted.
- **Phone acceptance.** None (pure Kotlin).
- **Dependencies.** M2, M4 (catalog in the package).

### M7 — Preflight + session launch + return

- **Deliverables.** `oneos_preflight.sh` (G1–G16, `preflight.json` with
  boot_id/plan hash/package/table hash), launcher sourcing `session.env`,
  return button, return reason → `session/last_return.json`.
- **Server acceptance.** Dry-run harness: stale/mismatched preflight, a
  revoked or modified package, a table for another fingerprint are each
  refused.
- **Phone acceptance.** First with `ONEOS_PREPARE_ONLY=1` (prepare, check
  `/apex`, return, no guest), then a full session on the F8U from the
  app-staged N6 package reproducing run 34 (UI up, SIM 2 audio, mobile data,
  toggles effective); clean reboot return.
- **Dependencies.** M3, M5, M6; the script changes in §9.

### M8 — Log bundle + redaction

- **Deliverables.** `:core:logs` (`SessionLogCollector`, `Redactor`,
  `ReturnReasonParser`), bundle `oneos.logbundle/1` with package id/serial and
  table hash, preview + share sheet; outcome classification
  (`compat-safety-logs.md` §3.2).
- **Server acceptance.** Unit tests for every mask regex and the drop-tag
  list; a redacted zip built from `out/logs/run33/` contains no raw phone
  number/SSID.
- **Phone acceptance.** On the F8U after a session the bundle is produced
  once root is back; screenshots/recordings excluded by default.
- **Dependencies.** M7.

### M9 — Fix packs + channel updates

- **Deliverables.** `:core:fixpack` (verify, `match.packages`, pin/rollback,
  anti-downgrade), index re-check on open, revocation handling, app-update
  notice from `index.app`.
- **Server acceptance.** A signed test pack that replaces one script
  verifies and applies; tampered, unknown-key, wrong-hash and
  floor-loosening packs are rejected; rollback restores the previous version;
  a revoked package serial blocks G15.
- **Phone acceptance.** A pack that flips a non-safety default on the F8U is
  reflected in the next `session.env`; no activation mid-session.
- **Dependencies.** M5, M6, M8.

### M10 — Polish and the friends build

- **Deliverables.** About page (threat model, "tested only with ColorOS on Z
  Fold (F8U)", credits; OneLineage with its GitHub link only), known issues (status-bar
  4G/bars until fixed), signed release APK, both packages built and signed
  with the release key and published per §10 question 1, the index link.
- **Server acceptance.** Full `gradle build` + lint clean; both packages
  rebuild reproducibly.
- **Phone acceptance.** End to end on the F8U from a clean app install with
  only the index link; the S26U WARN path verified on fixture facts.
- **Dependencies.** M1–M9 and the answers to §10.

Dependency graph: M1→M2→M6; M3 (server part from day one) →M4→M5→M7→M8→M9→M10;
M1→M5; M6→M7. Later (not in the first release): on-phone engine for
user-supplied images (`patch-engine.md`), runtime panel tables (§5.8).

---

## 12. Build environment (confirmed on the server)

Gradle `9.5.0`/`9.8.1` (cached `~/.gradle/wrapper/dists`); AGP `9.3.3`/`9.4.1`
cached; JDK 25 default, 21 installed (toolchain 21 used); Android SDK
`/opt/android-sdk`, platforms `android-37.{0,1,2}`, build-tools `37.0.0`, NDK
`28.2`/`30.0` present (native `zygote_exec` already built with the repo's NDK
flow). Internet to Maven Central and Google Maven works. The SESL coordinates
need **no** GitHub token. Align on one Kotlin version before M2: the prototype
mixed AGP's bundled Kotlin `2.2.10` (Android modules) with KGP `2.4.21` (the
pure-JVM `:core:model` + serialization `1.11.0`) and both built, but a single
Kotlin should be pinned — `serialization-json 1.11.0` wants stdlib `2.3.20`, so
either take Kotlin `2.4.x` everywhere or drop serialization to `1.9.0` (stdlib
`2.2.0`) to match `2.2.10`. Server packaging needs `debugfs`, `openssl` (Ed25519
`pkeyutl -rawin`), `pigz` or `gzip`, and the existing apktool/aapt2 flow.

---

## 13. Repo file → component map (quick index)

| Today | Component | Milestone |
| --- | --- | --- |
| `switcher/src/.../MainActivity.java`, `res/` | `:app` (SESL) | M1 |
| fact reads in `MainActivity`, `guest_prepare.sh` | `:core:device` `FactProbe`/`CompatEvaluator` | M1–M2 |
| `scripts/host-installd-table.sh`, `switcher/patches/host_installd.txt` | `:core:safety` `HostInstalldTable` + runtime table; the `.txt` becomes a test fixture | M3 |
| `switcher/patches/guest_installd_abi.py` | runtime lookup via `OneOSInstalldTable` (server) | M3 |
| the image build (MysticGSI, not in this repository), `make-overlays.sh`, `switcher/patches/*.py`, `check-dex.py` | server package build, unchanged except §6.5 | M3–M4 |
| new `scripts/make-package.sh`, `scripts/check-guards.py` | package + guard check | M4 |
| `scripts/deploy-phone.sh` (push + verify) | `:core:package` + `oneos_stage.sh` | M5 |
| `switcher/assets/*.sh` | package `scripts/`, driven by `session.env`; fix packs | M5–M7 |
| `guest_prepare.sh:4-39` refusals | kept + `oneos_preflight.sh` | M7 |
| `scripts/pull-run-logs.sh` | `:core:logs` | M8 |
| new | `:core:fixpack` + channel index | M9 |

---

## 14. Changes to the study docs

Only `docs/app/*` were touched; no other repo file was edited.

First draft:

- `patch-catalog.md` §3: `guard_manifest.json` → `guards.json` (schema
  `oneos.guards/1`).
- `patch-engine.md` §1.1/§1.2: engine class `com.oneos.engine.EngineMain` →
  the app's package (now `com.fahadali.oneos.engine.EngineMain`).
- `compat-safety-logs.md` §1.6: the no-mount Kotlin ext4 reader replaced by
  the read-only loop-mount of `patch-engine.md` §2.5; the bundle example uses
  `safety.storage_guards`; packs carry feature scripts only.

This revision (server-built packages):

- `patch-engine.md`: status note at the top — not in the first release, kept
  as the later option for user-supplied images; its §4 (`host_installd.json`,
  re-patch on change) is superseded by §6 here.
- `patch-catalog.md` §2: the "built on the phone, never shipped" paragraph
  now describes server-built packages; `safety.host_installd_table` is a
  runtime table, not a re-patch; §3 points to §7 here; §8 gains
  `ONEOS_GUEST_MOBILE_DATA` and `ONEOS_GAP_FAST`; §9 items 2, 5 and 6 carry
  their current status.
- `compat-safety-logs.md`: §1.5 and the G2 row point to the runtime table
  (§6 here); a G15 row; §2.3 notes the verifier runs on the server in this
  release; §4.1 scripts ship in the package; §4.4 notes the merged index; §5
  rows updated.

Requests of 2026-10-22 (app id, Before you start, screen lock, credits):

- `compat-safety-logs.md`: application id `com.fahadali.oneos` (top); a
  screen-lock row in §1.1; §1.9 lists the screen lock under WARN for the
  device report; a G16 row in §2.1.
- `patch-engine.md` §1.1/§1.2: engine class
  `com.fahadali.oneos.engine.EngineMain`.
