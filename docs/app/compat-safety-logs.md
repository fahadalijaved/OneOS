# OneOS app: compatibility report, safety gates, failure logs, fix packs

> **Renamed after 0.3.6:** the stage is `/data/local/tmp/oneos` (was `/data/local/tmp/lineage_stage`), its set-aside copies `oneos.old-<epoch>` / `oneos.trash-<epoch>` (were `lineage_stage.old-*` / `.trash-*`), and the session scripts `oneos_switch.sh`, `guest_prepare.sh`, `guest_start.sh` (were `switch_to_lineage.sh`, `master_prepare.sh`, `master_inner.sh`). The app's root script and `scripts/deploy-phone.sh` rename an old stage and its copies when they are idle.

Study `compat-safety-logs`. Scope: what the new OneOS app (our own Kotlin
code, see `switcher/README.md` for why nothing of `com.wewaffles.onelineage`
is reused) detects about the phone and the user's OS image, which checks can
never be skipped, how it collects and redacts logs after a failed session,
and how signed fix packs reach users without an app update.

Facts below come from the repo (paths cited) and from read-only reads of the
reference phone (SM-F976B, "F8U") on 2026-10-22, marked *(phone)*.

Module names are proposals; align them with the architecture study.
Application id and root package: `com.fahadali.oneos` (decided 2026-10-22,
`DESIGN.md`). Proposed Gradle modules: `:core:root`, `:core:device`,
`:core:safety`, `:core:logs`, `:core:fixpack`, `:app`.

---

## 1. Device and OS detection

### 1.1 Where each fact comes from

All host facts are read when the app opens and again by the root-side
preflight right before a session (section 2). Reads only; nothing here writes.

| Fact | Source | F8U value *(phone)* |
| --- | --- | --- |
| Brand / maker | `ro.product.brand`, `ro.product.manufacturer` | `samsung` |
| Model | `ro.product.model` (`ro.boot.em.model` as a cross-check) | `SM-F976B` |
| Codename | `ro.product.device`, `ro.product.vendor.device` | `q8q` |
| SoC | `ro.soc.manufacturer`, `ro.soc.model`, `ro.board.platform`, `ro.hardware.egl` | `QTI`, `SM8850`, `canoe`, `adreno` |
| One UI | `ro.build.version.oneui` (major*10000 + minor*100 + patch) | `90000` (9.0) |
| Android | `ro.build.version.sdk`, `ro.build.version.sdk_full`, `ro.build.id` | `37`, `37.0`, `CP2A.260605.016` |
| Vendor level | `ro.vendor.api_level`, `ro.board.api_level`, `ro.vendor.build.version.sdk` | `202504`, `202504`, `36` |
| Fingerprint | `ro.build.fingerprint` | `samsung/q8qxxx/q8q:17/CP2A.260605.016/F976BXXS3AZIJ_...` |
| ABI | `ro.product.cpu.abilist64` | `arm64-v8a` (no 32-bit) |
| Displays | `dumpsys SurfaceFlinger --display-id`, `dumpsys display` (DisplayDeviceInfo) | port 147 2256x2504 (inner), port 148 1080x2520 (cover, `FLAG_EXTRA_BUILT_IN_DISPLAY`) |
| Device states | `cmd device_state print-states`, `/vendor/etc/devicestate/device_state_configuration.xml` | 0 CLOSED, 1 TENT, 2 HALF_OPENED, 3 OPENED, 4/5 CONCURRENT_* |
| Lid / hall | `getevent -pl` device names | `flip`, `certify_hall` |
| Touch ICs | `/sys/class/sec/tsp*`, `tspN/cmd_list` | `tsp1`, `tsp2`; tsp2 `cmd_list` has `set_fold_state` |
| Touch inputs | input device names | `sec_touchscreen`, `sec_touchscreen2` |
| Audio HAL | `service list` | AIDL `android.hardware.audio.core.IModule/default` |
| Root manager | section 1.4 | KernelSU (`me.weishu.kernelsu`) |
| Free space | `StatFs("/data")` | 407 GB free of 481 GB |
| Battery | `BatteryManager` (level, plugged, temperature) | – |
| Host SELinux types | host `*.cil` type lists (as `guest_prepare.sh` builds `host_sepolicy_types.txt`) | – |
| Host installd ABI | host `/system/framework/services.jar`, section 1.5 | `switcher/patches/host_installd.txt` |
| Bootloader | `ro.boot.flash.locked`, `ro.boot.verifiedbootstate` | `1`, `green` (works locked, nothing flashed) |
| Screen lock | `KeyguardManager.isDeviceSecure()` (public API, no permission): PIN, pattern or password, which fingerprint/face unlock needs | – |

`ro.build.characteristics` reads `phone` even on the Fold, so it is never used
for the form factor.

### 1.2 Form factor

Decided from hardware, then cross-checked with the model prefix:

1. Count built-in panels: `dumpsys display` DisplayDeviceInfo entries with
   `type INTERNAL`. One = **bar**.
2. Two panels plus device states named `CLOSED`/`OPENED` (or a `flip` lid input
   device) = foldable. The smaller panel's physical diagonal (from pixel size
   and dpi) under 4.5" = **flip** (cover screen), otherwise **fold**.
3. Model prefix cross-check: `SM-F9xx` fold, `SM-F7xx` flip, `SM-S9x8` S Ultra
   (S928, S938, S948), other `SM-S9xx` S series. A mismatch between steps 1-2
   and the prefix is WARN and the hardware answer wins.

Stored as `FormFactor { BAR, FOLD, FLIP }` with the panel list
`[{port, widthPx, heightPx, dpi, role: inner|cover|main}]`. The fold patches
(layout file with ports 147/148, cover touch IC monitor, `type.fold` feature
switches, Wallpapers fold grid RRO) are only offered when the form factor is
FOLD and the ports and `tsp2` match what the patch needs; on an S26 Ultra they
are hidden.

### 1.3 SoC

`ro.soc.manufacturer == QTI` (or `ro.board.platform` a Qualcomm name such as
`canoe`, `sun`) = Snapdragon. Samsung LSI (`ro.soc.manufacturer` `Samsung`,
platform `s5e*` / `erd*`) = Exynos. This build only knows the Qualcomm display
path: `surfaceflinger_patched` skips `IQtiComposer3Client` and
`guest_start.sh` restarts `vendor.qti.hardware.display.composer`. Exynos is
BLOCK until a fix pack ships an Exynos profile.

### 1.4 Root manager

Detected from files the root manager owns, then confirmed with one `su -c id`:

| Manager | Marker | busybox | resetprop |
| --- | --- | --- | --- |
| KernelSU (and forks) | `/data/adb/ksud`, `/data/adb/ksu` | `/data/adb/ksu/bin/busybox` | `/data/adb/ksu/bin/resetprop` |
| Magisk | `/data/adb/magisk`, `magisk -V` | `/data/adb/magisk/busybox` | `resetprop` applet |
| APatch | `/data/adb/apd`, `/data/adb/ap` | `/data/adb/ap/bin/busybox` | probed |

The scripts need busybox (`oneos_switch.sh` finds it with a fallback
search) and resetprop (`guest_props.sh` silently skips without it, and then
One UI's props are not restored on return). So: no working `su` = BLOCK, no
busybox = BLOCK, no resetprop = BLOCK. A resetprop "works" check reads a prop
(`resetprop ro.build.id`), never sets one.

Temp root is lost on every return (the return is a reboot,
`docs/coloros-on-fold.md` "Returning to One UI"). The app shows root as
"needed again after each session" and only collects logs once root is back
(section 3).

### 1.5 Host installd ABI

> First release (`DESIGN.md` §6): the table is no longer baked into the
> patched `services.jar`. The app derives it on each phone as below and
> writes it as the text file `$STAGE/host_installd.table` (format
> `oneos.installd-table 1`, which replaces the `host_installd.json` sketched
> here); `guest_prepare.sh` and the guest's `OneOSInstalldTable` re-check it
> and fail closed. The BLOCK rules below still apply.

The guest framework sends installd calls to One UI's installd over the shared
binder. `switcher/patches/guest_installd_abi.py` remaps the allowed calls to
the host's transaction codes and throws for everything else; the table comes
from `scripts/host-installd-table.sh`, which reads the `TRANSACTION_*` fields
of `android/os/IInstalld$Stub` and the signatures in `$Stub$Proxy` from the
host's `services.jar`.

In the app, `:core:safety` `HostInstalldTable` does the same on the phone
with `com.android.tools.smali:smali-dexlib2:3.0.10` (Google Maven, verified
2026-10-22): open every `classes*.dex` inside `/system/framework/services.jar`,
read the static values and proxy method signatures, and write
`host_installd.json`:

```json
{
  "fingerprint": "samsung/q8qxxx/q8q:17/CP2A.260605.016/F976BXXS3AZIJ_OXM3AZIJ:user/release-keys",
  "servicesJarSha256": "<sha256 of /system/framework/services.jar>",
  "methods": [
    {"name": "createUserData", "code": 1, "sig": "(Ljava/lang/String;III)V"},
    {"name": "destroyUserData", "code": 2, "sig": "(Ljava/lang/String;II)V"}
  ]
}
```

The ABI is **unknown** (BLOCK) when any of these hold:

- `IInstalld$Stub` is not found in the host jar (dex stripped or renamed);
- codes are not unique, or a method name appears twice;
- any method that `guest_installd_abi.py` `ALLOWED` lists is present with a
  different signature AND the patcher would keep it (the patcher already
  blocks those; the check confirms it);
- `destroyUserData` is missing from the table (the table is then not the
  interface we think it is);
- the table's `fingerprint` or `servicesJarSha256` no longer matches the
  running One UI (an OTA happened): the table and every jar built from it are
  stale and must be rebuilt before a session.

### 1.6 Guest OS (the image the user brings)

`GuestImageInspector` (`:core:image`) runs in the root engine's `inspect` job over a read-only loop mount in a private mount namespace (`patch-engine.md` §2.5; `DESIGN.md` resolves the earlier no-mount idea):

- container: raw ext4 (superblock magic `0xEF53` at byte 1080), Android sparse
  (`0xED26FF3A` at 0, unsparse first), erofs (`0xE0F5E1E2` at 1024), or a
  `.zip`/`.xz`/`.gz` holding one of those. Only ext4 is supported today
  (`guest_prepare.sh` loop-mounts ext4; `scripts/deploy-phone.sh` refuses
  others). erofs = BLOCK in this build.
- size: the raw image size (the ColorOS image is 10,276,003,840 bytes).
- props: read from the mounted image: `/system/build.prop`,
  `/system/system_ext/etc/build.prop`, `/system/product/etc/build.prop` and
  lists `/system/etc/vintf`.

Family rules (first match wins):

| Family | Markers | ColorOS image values |
| --- | --- | --- |
| ColorOS / OxygenOS | `ro.build.version.oplusrom*`, `ro.oplus.*`, `ro.oplus.image.system_ext.brand` | `V17.0.0`, brand `oppo` |
| LineageOS | `ro.lineage.version`, `ro.lineage.build.version` | – |
| HyperOS / MIUI | `ro.mi.os.version.*`, `ro.miui.ui.version.*` | – |
| One UI (as guest) | `ro.build.version.oneui` | refused: we never run One UI in One UI |
| AOSP / Pixel GSI | none of the above, `ro.product.system.brand` `google`/`Android` | – |
| Unknown | anything else | WARN, AOSP profile |

Also recorded: `ro.build.version.sdk`, `ro.build.id`,
`ro.system.build.version.sdk`, `ro.system.product.cpu.abilist64`
(`arm64-v8a` required), `ro.build.display.id`, the image's sha256 (shown and
put in the logs manifest; the image itself never leaves the phone).

### 1.7 How far host and guest may differ

The guest shares much more than vendor HALs with One UI: the property area,
servicemanager, and host system daemons whose interfaces are not stable across
Android releases (installd, which bit us in runs 25-29; also artd, netd,
keystore2, statsd, logd). The rules for this build:

| Check | OK | WARN | BLOCK |
| --- | --- | --- | --- |
| SDK | guest `ro.build.version.sdk` == host | – | different |
| Build ID | same `ro.build.id` (ColorOS case: both `CP2A.260605.016`) | same SDK, other build ID | – |
| Vendor matrix | guest has `/system/etc/vintf/compatibility_matrix.<host ro.vendor.api_level>.xml` (ColorOS has `202504`, host is `202504`) | – | missing |
| ABI | guest has `arm64-v8a` | – | no arm64 |
| installd | the patcher classifies every guest method (section 2) | – | any method left unclassified |

A different SDK is BLOCK and not WARN because the shared daemons are the risk
that already deleted data once. A fix pack can lift this for a specific
host/guest pair once it has been tested (profile `sdkPairs`, section 4).

### 1.8 SELinux types

`guest_prepare.sh` rewrites the guest's seapp_contexts against the host's
types. The report lists, as information, how many guest seapp rules name types
the host lacks (the ColorOS image: OPPO domains such as
`oplus_assistantscreen_app`). If the host type list misses any of the generic
types the rewrite relies on (`untrusted_app priv_app platform_app system_app
app_data_file privapp_data_file system_app_data_file`) the report is WARN and
the seapp patch is off, as the script does today.

### 1.9 Compatibility report

`CompatReport` is computed by `:core:device` `CompatEvaluator` from the facts
above and the active profiles. Each finding has a stable id, so fix packs and
logs can refer to it.

```json
{
  "schema": "oneos.compat/1",
  "generatedAt": "2026-10-22T15:10:31+03:00",
  "level": "OK | WARN | BLOCK",
  "host": {"model": "SM-F976B", "device": "q8q", "family": "z-fold", "form": "FOLD",
           "soc": "SM8850", "socVendor": "qualcomm", "oneui": 90000, "sdk": 37,
           "buildId": "CP2A.260605.016", "vendorApi": 202504, "root": "kernelsu"},
  "guest": {"family": "coloros", "version": "V17.0.0", "sdk": 37, "buildId": "CP2A.260605.016",
            "fs": "ext4", "sizeBytes": 10276003840, "sha256": "..."},
  "findings": [
    {"id": "tested-combo", "level": "OK", "text": "Tested: ColorOS on Z Fold (F8U)"},
    {"id": "build-id-differs", "level": "WARN", "text": "..."}
  ]
}
```

Level rules (the worst finding wins):

- **BLOCK**: not Samsung; not arm64; Exynos (until profiled); no working root,
  busybox or resetprop; installd ABI unknown; guest SDK != host SDK; vendor
  compatibility matrix missing; guest image not ext4; guest is One UI; free
  space short (section 2); any safety patch fails to build or verify.
- **WARN**: model or guest family not in the tested list (this build: tested
  only with ColorOS on Z Fold F8U); same SDK but different build ID; form
  factor and model prefix disagree; generic SELinux types missing; One UI
  version not seen in any profile. In the device report also a set screen
  lock ("Screen lock is set - remove it before switching"): a locked phone
  that boot-loops may not get into Download Mode to recover. That one is
  advisory only until switching exists; at switch time it is gate G16 (BLOCK).
  Also in the device report since Friend build 1 (section 7.7): "CPU lacks
  <features> used by the ColorOS images" (SVE2 or SME missing from
  `/proc/cpuinfo`; the tested Fold has no MOPS or SME2 and runs ColorOS) and
  "Android version differs from the OneOS images (17);
  switching may not work" (host SDK != 37; BLOCK at switch time, as the SDK
  rule above).
- **OK**: everything else.

WARN lets the user continue after reading the findings. BLOCK has no
continue button and no override setting.

---

## 2. Safety gates

### 2.1 The list

These come from the run 25 incident (`docs/coloros-on-fold.md`, "Keeping the
guest away from One UI's data") and the refusals already in the scripts. Every
gate is a refusal: when it cannot be verified the session does not start.

| Id | Gate | Today | In the app |
| --- | --- | --- | --- |
| G1 | Storage, power, sysrq and installd guards present in the jars the guest will load | `guards.txt` sha256 check, `guest_prepare.sh` exit 3 | hashes plus a semantic check of the built jars (2.3) |
| G2 | installd table derived for this phone and this One UI build | table from the server | `HostInstalldTable` on the phone writes `$STAGE/host_installd.table`; fingerprint and jar hash must match, every required method must map; the guest re-checks it at runtime (1.5, `DESIGN.md` §6) |
| G3 | Every host /data tree in `bridges.sh` is the staged copy (device:inode) before the guest starts | `guest_prepare.sh` exit 3 | unchanged; the bridge list can only grow |
| G4 | Nothing mounted at or under `$STAGE/data` before the rebuild | `guest_prepare.sh` exit 4 | unchanged, also checked by the app first |
| G5 | No bridge left from an earlier session | `guest_prepare.sh` exit 4, `deploy-phone.sh` | unchanged |
| G6 | The guarded `services.jar` is the one bound in the rootfs | `guest_prepare.sh` exit 3 | unchanged |
| G7 | One UI's `/apex` mounts unchanged and its APEXes on /data readable | `oneos_switch.sh`, `check_host_apex.sh` | unchanged |
| G8 | Guest namespace has no host root, storage views or sysrq | `guest_start.sh` FATAL lines | unchanged |
| G9 | Free space | none | new: image + 8 GB staged data + 1 GB logs + 2 GB margin |
| G10 | Battery | none | new: 30% or charging, temperature under 42 C |
| G11 | Samsung and arm64 | none | new |
| G12 | Auto-return watcher and return keys armed | env can turn them off | new: always on |
| G13 | Compatibility report not BLOCK | none | new |
| G14 | Every safety patch applied | patchers `sys.exit` on surprises | new: any safety patch failure stops the whole build; first release: listed as applied and verified in the signed package manifest |
| G15 | Active package intact | none | new: signature valid, not revoked, staged files are the manifest's (`DESIGN.md` §4.3, §5.7) |
| G16 | No screen lock (PIN, pattern, password, fingerprint/face) | none | new: `KeyguardManager.isDeviceSecure()` false before the session, re-checked by the root preflight (`DESIGN.md` §4.3); WARN in the device report until switching exists (M7) |

### 2.2 Why the UI cannot skip them

The gates do not live in the UI. The design has three layers, and the deepest
one is the one that counts:

1. **App (advisory).** `:core:safety` `GateRunner` runs the gates and shows
   their results. Safety patches are shown as locked toggles. There is no
   setting, debug menu or intent extra that turns a gate off.
2. **Root-side preflight (binding).** A script shipped in the APK assets,
   `oneos_preflight.sh`, runs every gate again as root and writes
   `$STAGE/session/preflight.json` with the plan hash and the current
   `boot_id` (`/proc/sys/kernel/random/boot_id`).
3. **Session scripts (binding, last moment).** `oneos_switch.sh` refuses
   to start unless `preflight.json` exists, is under 5 minutes old, has this
   boot's `boot_id`, and matches the plan hash. `guest_prepare.sh` keeps its
   own G1-G6 checks, so a stale or hand-edited preflight still cannot start a
   guest without guards.

Env vars from the current scripts that would weaken a gate are not passed
through by the app: `ONEOS_RETURN_MAX=0` (disables the dead-man switch),
`ONEOS_RETURN_KEYS=0`, `ONEOS_LOGCAT=0`. The app only builds an env from an
allow list of feature toggles (`ONEOS_GUEST_*`, `ONEOS_GAP_SPLASH`, etc.).

Threat model: this protects against accidents (stale jars, partial builds, an
OTA under us, an older app version, a fix pack bug), not against a person with
root who edits the scripts. That is stated in the app's About page.

### 2.3 Checking the built jars, not only their hashes

> First release (`DESIGN.md` §4.4): the jars are built on the server, so
> these checks run there (`scripts/check-guards.py` inside
> `make-package.sh`) and their result is the `guards` object of the signed
> package manifest; a package with a failed check is never signed. The
> checks themselves are unchanged, plus one for the runtime installd lookup.

A hash only proves the jar is the one we built. Runs 26-29 show why that is
not enough: the installd patch was applied to `IInstalld$Stub$Proxy`, but
ColorOS's `framework.jar` on the boot class path had its own copy, so the
patched class was never used. `:core:safety` `GuardVerifier` reads the built
dex with dexlib2 and checks:

- no `invoke-interface` to the destructive `IVold` / `IInstalld` methods that
  `guest_storage_guards.py` lists (`VOLD`, `INSTALLD`), and no
  `AndroidKeyStoreMaintenance` calls from its `KEYSTORE` list;
- `com.android.server.pm.OneOSInstalldProxy` exists, every
  `IInstalld$Stub;->asInterface` call site in `services.jar` and
  `oplus-services.jar` goes to it, and its blocked methods throw before
  `transact`;
- `PowerManagerService` has no `"sys.powerctl"` string left (two writes go to
  `oneos.guest.powerctl`), and the `ShutdownThread` entry points return;
- the sysrq guard is in place (`guest_no_sysrq_crash.py`);
- **shadowing**: no jar on the guest's boot class path (from its
  `derive_classpath` output) defines any of the guarded classes. A shadowed
  class is BLOCK.
- `scripts/check-dex.py`'s empty try-range check (run 26: ART rejected a
  whole class).

The result goes to `guards.json` next to the jars:

```json
{
  "schema": "oneos.guards/1",
  "jars": [{"name": "services_patched.jar", "sha256": "..."},
           {"name": "oplus-services_patched.jar", "sha256": "..."}],
  "hostInstalld": {"fingerprint": "...", "servicesJarSha256": "..."},
  "checks": [{"id": "no-destructive-installd", "ok": true}, {"id": "no-shadowing", "ok": true}],
  "builtBy": {"app": "1.0.0", "rules": {"guest_storage_guards": 3}}
}
```

`guest_prepare.sh` keeps reading `guards.txt` (generated from `guards.json`)
so the scripts stay simple.

---

## 3. Logs after a failed session

### 3.1 What a session already writes

| File | Writer |
| --- | --- |
| `/data/local/tmp/oneos_logs/boot.log*` (logcat -b all, 25 x 32 MB; `head/`: the files of the boot, hard links made in the 90 s round) | `oneos_switch.sh` |
| `/data/local/tmp/oneos_logs.prev/` (the session before) | `oneos_switch.sh` |
| `$STAGE/takeover_app.log` | app launch |
| `$STAGE/data/takeover.log` (inside the guest) | `guest_start.sh` |
| `$STAGE/auto_return.log`, `manual_return.log` | watcher, return |
| `$STAGE/diag_20`, `diag_40`, `diag_90`, `diag_final`, `diag_fold`, `diag_host`, `diag_pages` | watcher, fold monitor |
| `$STAGE/apex_watch.log`, `net_watch.log`, `gap_splash.log` | switch |
| `$STAGE/data/call_audio.log`, `audio_keeper.log`, `backlight.log`, `vold.log`, `idmap.log` | `guest_start.sh` |
| `/data/local/tmp/ui_activator.log` | activator |

`scripts/pull-run-logs.sh` already packs exactly these; the app's
`:core:logs` `SessionLogCollector` takes the same list plus:

- `$STAGE/data/system/dropbox/` and `$STAGE/data/anr/` (guest),
- tombstones from the session window: guest processes share the host's
  `/dev` (`guest_prepare.sh` rbinds it), so their tombstones can land in the
  host's `/data/tombstones`; take entries whose mtime is inside the session,
- after a hard reset: the pstore console and Samsung's reset nodes
  (`/proc/reset_reason`, `reset_summary`, `reset_history`, `last_kmsg`,
  present on the F8U *(phone)*), raw, read as root,
- `persist.sys.boot.reason.history`, `sys.boot.reason`.

Screen recordings (`oneos_rec_*.mp4`) are never put in a bundle by default:
they show the user's screen. The user can add them by hand.

### 3.2 Was the last session a failure?

The app writes `$STAGE/session/current.json` at start (session id,
`boot_id`, start time, plan hash, app version, compat report). After the next
boot it decides:

| Evidence | Outcome |
| --- | --- |
| `sys.boot.reason` = `reboot,oneos-return` and the last `auto_return.log` line says keys | user return (clean) |
| `reboot,oneos-return`, line `guest zygote/system_server gone for Ns after Ms` | GUEST_DEAD |
| line `black screen after Ns (...)` | BLACK_SCREEN |
| line `guest requested 'reboot' after Ns` | GUEST_REBOOT (ColorOS restart in power menu, or a crash path) |
| line `session limit Ns reached` | SESSION_LIMIT (test runs) |
| line `guest still not booted after Ns` | BOOT_TIMEOUT |
| `takeover_app.log` has `guest_prepare.sh failed (code N)` (`master_prepare.sh failed` from 0.3.6 sessions) or the `/apex` abort | PREPARE_FAILED |
| `shutdown,oneos-guest-shutdown` | GUEST_SHUTDOWN |
| any other boot reason after a `current.json` from an earlier boot | HARD_RESET (raw reset nodes go in the bundle) |

Run 33 is a real example: the user saw "it hung and rebooted" after closing
the screen; `auto_return.log` says `guest zygote/system_server gone for 30s
after 590s, returning to One UI`, and the boot reason history shows
`reboot,oneos-return` *(phone)*. The app would show "ColorOS stopped 10 min
into the session; OneOS returned to One UI by itself" with a "Share logs"
button.

To make this robust, `return_to_oneui.sh` should get the reason as an
argument from the watcher and write `$STAGE/session/last_return.json` before
it reboots (a small script change for the scripts study). Until then the app
parses `auto_return.log` with the regexes above.

Two practical rules: root is gone after the reboot, so the app posts a
notification and collects when root is back; and the next session moves
`oneos_logs` to `.prev` and deletes the old `.prev`, so the app collects (or
the user discards) the last failed session's logs before it starts a new one.

### 3.3 Privacy redaction

Logs from run 32 show what needs care: SSIDs and BSSIDs (Wi-Fi tags), ICCID
and IMSI (`OplusUiccManagerImpl`, `SIMRecords`, `RILJ`), phone numbers
(`Ts43PhoneNumberController`, `PhoneNumberUtils`), emails (wakelock names),
cell ids, SMS provider lines, and file paths under `/storage/emulated/0`.

`:core:logs` `Redactor` runs on the phone before anything is zipped. Two
steps:

**Drop lines entirely** for tags that are mostly personal data: `SIPMSG*`,
`SmsProvider`, `TP/SmsProvider`, `TP/MmsSmsProvider`, `MmsSmsProvider`,
`GsmInboundSmsHandler`, `ContactsProvider`, `ContactInfoHelper`,
`Ts43PhoneNumberController`, `PhoneNumberOfflineGeocoder`,
`*GetUpcomingContactsUseCase`, `wpa_supplicant`, `WiFiPerception`,
`LocationManagerService`, `GnssLocationProvider`, `*Geofence*`. A fix pack can
add tags; it cannot remove the built-in ones.

**Mask values** in all remaining lines (ordered; each replaced by a typed
token plus a per-bundle salted hash prefix so the same value stays
recognizable inside one bundle):

| Data | Pattern (Kotlin regex) | Replacement |
| --- | --- | --- |
| Email | `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}` | `<email:h>` |
| ICCID | `\b89\d{17,18}[0-9Ff]?\b` | `<iccid:h>` |
| IMEI | `\b\d{15}\b` passing Luhn | `<imei:h>` |
| IMSI | `\b\d{15}\b` after `imsi`/`IMSI` within 20 chars | `<imsi:h>` |
| Phone | `(?<![\w.])\+?\d[\d\s().-]{7,16}\d(?![\w.])` | `<phone:h>` |
| MAC / BSSID | `\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b` | `<mac:h>` (keep the first 3 bytes only for `02:00:00...`) |
| SSID | `(?i)(ssid[=:\s"]+)("[^"]*"|\S+)` | `$1<ssid:h>` |
| GPS | `-?\d{1,3}\.\d{4,},\s*-?\d{1,3}\.\d{4,}` and `(?i)(lat|lon|latitude|longitude)[=:]\s*-?\d+\.\d+` | `<geo>` |
| Cell ids | `(?i)\b(mCi|mPci|mTac|mLac|mNci|ci|tac|lac)=\d+` | `$1=<cell>` |
| Accounts | `Account \{name=[^,}]+` | `Account {name=<acct:h>` |
| User files | `/(storage/emulated|sdcard|data/media)/\d+/[^\s"']+` | keep the dir, replace the file name with `<file:h>` |
| IPs | IPv4 not in private ranges, IPv6 global | `<ip:h>` |

Times are kept unchanged: they are what makes a log usable. Timestamps,
package names, class names and stack traces are not personal data and stay.

Dumpsys files in `diag_*` go through the same masks; `telephony_registry.txt`
and `windows.txt` keep only the lines a fix needs (a per-file keep list) and
screenshots (`shot_*.png`) are left out unless the user adds them.

Before sharing, the app shows the bundle's file list, sizes and a count of
masked values per type, and a "view" button for every text file.

### 3.4 Bundle format and sharing

`oneos-logs-<session-id>.zip`, written to the app's cache and shared with
`Intent.ACTION_SEND` through a `FileProvider` (no network call by the app):

```json
{
  "schema": "oneos.logbundle/1",
  "sessionId": "2026-10-22T14-40-12-q8q",
  "app": {"version": "1.0.0", "versionCode": 100},
  "outcome": {"kind": "GUEST_DEAD", "afterSeconds": 590,
              "line": "guest zygote/system_server gone for 30s after 590s"},
  "bootReason": "reboot,oneos-return",
  "compat": {"$ref": "compat.json"},
  "plan": {"patches": [{"id": "safety.storage_guards", "rule": 3, "on": true, "locked": true}],
           "env": {"ONEOS_GUEST_FORM": "fold"}},
  "fixPacks": [{"id": "core", "version": 7, "sha256": "..."}],
  "redaction": {"rules": 3, "droppedTags": 18, "masked": {"phone": 41, "mac": 220}},
  "files": [{"path": "logcat/boot.log", "bytes": 20971520, "sha256": "..."}]
}
```

Files are stored under `logcat/`, `stage/`, `diag/`, `guest/` (dropbox, anr),
`tombstones/`, `kernel/` (pstore, reset nodes). Logcat is compressed in the
zip (about 10x, as `pull-run-logs.sh` shows on the phone).

### 3.5 Friend build 2: Collect logs (what 0.3.0 does)

Last session → *Collect logs*, after the return to One UI (root is asked
again; nothing runs at boot). One read-only list,
`app/src/full/assets/logs/collect.list` (OneOS only, 0.3.4), in the probe grammar (7.2), run by
the same `probe.sh` and audited by the same `ProbeAudit` (in the unit tests
and in the app before every run); root writes no file. In order:

| Entry | Reads | Kept |
| --- | --- | --- |
| `logs.ssids` | the `name="...SSID"` elements only of One UI's and the guest's Wi-Fi stores (`WifiConfigStore.xml`, `WifiConfigStoreSoftAp.xml`); no password is read | memory only, never written: the names are removed from everything after it (the home network is often the owner's name) |
| `logs.input` | `/proc/bus/input/devices` | memory only: Bluetooth device names are removed |
| `logs.reason` | `sys.boot.reason`, `persist.sys.boot.reason.history` | `boot/reason.txt` |
| `logs.current` | `$STAGE/session/current.json` (written by the root script's `launch`) | `stage/current.json` |
| `logs.stage` | `$STAGE/*.log` (takeover_app, auto_return, manual_return, apex_watch, net_watch, gap_splash, ...) | `stage/` |
| `logs.guest` | `$STAGE/data/*.log` (takeover, call_audio, audio_keeper, backlight, vold, idmap, ...) | `guest/` |
| `logs.host` | `ui_activator.log`, `adb_watchdog.log`, `ims_watchdog.log`, `restore_app.log` in `/data/local/tmp` | `host/` |
| `logs.diag` | `$STAGE/diag_series.txt` (the 30 s session sampler) and `$STAGE/diag_*/*` with the endings `.txt`, `.log`, `.xml`, `.err` only | `diag/` |
| `logs.capture` | `/data/local/tmp/oneos_logs/head/boot.log*` no longer in the capture (the boot), then `/data/local/tmp/oneos_logs/boot.log*` (the session's full capture) | `capture/` |

Redaction happens as the stream arrives, line by line
(`:core:root` `RedactingOutputStream`), so no raw line ever reaches the app's
storage and no 20 MB file is held in memory: a logcat line whose tag is on the
drop list of 3.3 is dropped whole (`SmsProvider`, `TP/SmsProvider`,
`TP/MmsSmsProvider`, `MmsSmsProvider`, `GsmInboundSmsHandler`,
`ContactsProvider`, `ContactInfoHelper`, `Ts43PhoneNumberController`,
`PhoneNumberOfflineGeocoder`, `wpa_supplicant`, `WiFiPerception`,
`LocationManagerService`, `GnssLocationProvider`, `SIPMSG*`,
`*GetUpcomingContactsUseCase`, `*Geofence*`); every other line goes through
`Redactor` (7.5, the same rules as the findings, with the learned Wi-Fi and
Bluetooth names), and file names under `/storage/emulated/<n>`, `/sdcard`
and `/data/media/<n>` become `<file:hash>` (folders stay). Lines over 64 kB
are cut. A path ending in `.mp4`, `.png`, `.jpg` or another media ending is
never written, whatever a list prints: screen recordings (`oneos_rec_*.mp4`)
and screenshots (`shot_*.png`, `fold_*.png`) never get into a bundle.

The outcome (3.2) is read from the newest block of `auto_return.log` (after
its last `=== OneOS session` header) and of `takeover_app.log` (after the
root script's `=== OneOS app launch <session>` header), with the boot reason:
`USER_RETURN`, `GUEST_REBOOT`, `GUEST_SHUTDOWN`, `GUEST_DEAD`, `BLACK_SCREEN`,
`SESSION_LIMIT`, `BOOT_TIMEOUT`, `PREPARE_FAILED`, `REFUSED`, `DRY_RUN`,
`HARD_RESET`, `UNKNOWN` (`:core:root` `ReturnOutcomes`).

The bundle is `cache/logs/oneos-logs-<session>.zip` with `report.json`
(`oneos.logbundle/1`: session id, app, profile, image, the installd table's
hash from `current.json`, dry run or not, outcome, boot reason, the list's
and runner's SHA-256, entries that did not finish, redaction counts, every
file with size and SHA-256), `summary.txt` and `redaction.txt`. The findings
preview shows it (every file can be opened) with Share and Save to Downloads;
the FileProvider serves `cache/logs/` besides `cache/findings/`.

Not in 0.3.0: the session before (`oneos_logs.prev`), the guest's dropbox
and ANR folders, host tombstones of the session window, pstore and Samsung's
reset nodes, and a log of the watcher's own `logcat` excerpts beyond what
`auto_return.log` holds.

---

## 4. Fix packs

### 4.1 What they carry

A fix pack changes data and scripts, never the app's code:

- patch catalog updates (new patches, new defaults, new applicability rules),
- device profiles (model family, ports, touch IC layout, quirks),
- OS profiles (family, version ranges, feature switches, prop lists),
- feature scripts only (`guest_prepare.sh`, `guest_start.sh`, `guest_props.sh`, activator and fold monitor); first release: the session scripts ship in the signed package and the APK carries `oneos_preflight.sh`, `oneos_stage.sh` and the safety floor (`DESIGN.md` §3.1, §4.1),
- prebuilt RROs (such as `OneOSWallpapersFoldGrid.apk`),
- patch rule versions for the patch engine,
- redaction additions and Samsung reset reason names.

Safety floor: the APK carries the minimum gate list (2.1), the minimum
`BRIDGES` list from `switcher/assets/bridges.sh`, the safety patch ids and the
built-in drop-tag list. A pack may add to each and tighten thresholds; it can
never remove or loosen them. A pack that would is rejected as a whole.

### 4.2 Signing

Ed25519. Verification with `com.google.crypto.tink:tink-android:1.24.0`
(Maven Central, verified 2026-10-22) `Ed25519Verify`, so it does not depend on
the platform's provider. The public keys are compiled into the APK (two keys:
one in use, one offline backup for rotation). Signing on the build server:
`openssl pkeyutl -sign -rawin -inkey fixpack.key`.

Pack layout (a zip):

```
manifest.json
manifest.json.sig      # raw 64-byte Ed25519 signature over manifest.json, base64
files/...              # every file listed in the manifest with its sha256
```

```json
{
  "schema": "oneos.fixpack/1",
  "id": "core",
  "version": 7,
  "channel": "stable",
  "minApp": 100,
  "maxApp": null,
  "keyId": "oneos-2026a",
  "match": {
    "hostFamilies": ["z-fold", "z-flip", "s-ultra"],
    "socVendors": ["qualcomm"],
    "oneui": {"min": 80500, "max": 99999},
    "sdk": {"min": 37, "max": 37},
    "guestFamilies": ["coloros", "lineage", "aosp"],
    "sdkPairs": [{"host": 37, "guest": 37}]
  },
  "safety": {"addGates": [], "addBridges": [], "addDropTags": []},
  "files": [
    {"path": "files/catalog/patches.json", "sha256": "...", "kind": "catalog"},
    {"path": "files/scripts/guest_prepare.sh", "sha256": "...", "kind": "script"},
    {"path": "files/rro/OneOSWallpapersFoldGrid.apk", "sha256": "...", "kind": "rro"}
  ],
  "notes": "Run 33: SIM 2 call audio slot fix"
}
```

Verification order: signature, then `keyId` known, then schema, then every
file hash, then the safety floor, then `match` against the current report.

### 4.3 Matching, pinning, rollback

- Several packs can be active (`core` plus a device or OS pack). Each match
  field is an AND; a missing field matches anything.
- The user can pin a pack version. Pinned packs are not updated.
- Rollback: the app keeps the last three verified versions of each pack under
  `files/fixpacks/<id>/<version>/`. "Use previous" switches the active pointer
  (`active.json`). A rolled-back pack is still verified again before use.
- Anti-downgrade: the channel index (4.4) has a `serial`; the app refuses an
  index with a lower serial than the last one it accepted. A rollback picks an
  older pack the user already has, which is not a downgrade attack.
- Never during a session: the active set is copied into
  `$STAGE/session/<session-id>/` when a session is prepared, and the scripts
  read only that copy. The app does not activate a new pack while
  `$STAGE/session/current.json` belongs to the current boot.

### 4.4 Update channel

> First release (`DESIGN.md` §5.5): one signed channel index,
> `oneos.index/1`, lists packages and fix packs together (`fixpacks` carries
> the entries below) and is the link the maintainer shares; the hosting choice is
> an open question (`DESIGN.md` §10).

GitHub releases: one release per pack version, and a signed index uploaded to
a fixed release, read from
`https://github.com/<owner>/<repo>/releases/download/fixpacks/index.json` and
`index.json.sig`. App updates use the same repo's normal releases.

```json
{
  "schema": "oneos.fixpack-index/1",
  "channel": "stable",
  "serial": 42,
  "issued": "2026-10-22T12:00:00Z",
  "packs": [
    {"id": "core", "version": 7, "url": "https://github.com/<owner>/<repo>/releases/download/core-7/core-7.zip",
     "sha256": "...", "bytes": 182000, "minApp": 100, "match": {"hostFamilies": ["z-fold"]}}
  ],
  "revoked": [{"id": "core", "version": 5, "reason": "broke Wi-Fi on Flip"}]
}
```

The app checks for updates only when the user opens it (no background
network), downloads into the cache, verifies, then installs. A revoked
version is deactivated at once and the previous version used.

---

## 5. Mapping from today's files to the app

| Today | App component | Runs where |
| --- | --- | --- |
| `scripts/host-installd-table.sh` | `:core:safety` `HostInstalldTable` (dexlib2) | phone, in the app |
| `guards.txt` in `scripts/make-overlays.sh` | `GuardVerifier` + `guards.json` | first release: server (`check-guards.py` in `make-package.sh`, result in the signed manifest); phone later |
| `scripts/check-dex.py` | part of `GuardVerifier` | first release: server; phone later |
| preflight refusals in `guest_prepare.sh`, `oneos_switch.sh` | kept, plus `oneos_preflight.sh` | phone, root |
| `scripts/deploy-phone.sh` refusals | `GateRunner` G4/G5 | phone |
| `scripts/pull-run-logs.sh` | `SessionLogCollector` + `Redactor` | phone |
| `auto_return.log` text | `ReturnReasonParser` (later `last_return.json`) | phone |
| `switcher/assets/*.sh` | first release: inside the signed package (`DESIGN.md` §5.2), replaceable by signed fix packs | phone |
| patch rules, profiles, RROs | fix packs | built on the server, verified on the phone |

---

## 6. Open risks

1. **installd from the jar, not the daemon.** The table comes from the Java
   stub in `services.jar`. Samsung ships the daemon and the stub in the same
   system image, so they match by construction, but nothing checks the native
   side. A safe probe of the daemon is not known.
2. **Other shared daemons.** artd (ART module), netd, keystore2 and statsd are
   the host's. Same-SDK keeps the risk small; the guard list only covers
   installd, vold, keystore maintenance and power today.
3. **Root loss on return.** Every session ends in a reboot that drops temp
   root, so log collection waits for the user to re-root.
4. **Log rotation.** A new session deletes the logs from two sessions ago;
   the app must collect first (3.2).
5. **Redaction is best effort.** Regexes miss things. The preview screen and
   the drop-tag list are the main protection; we tell users to look before
   sharing.
6. **Exynos, erofs images, other SDKs** are BLOCK in this build and need real
   testing before any fix pack lifts them.
7. **Fix pack scripts run as root.** The signing key is the most sensitive
   secret of the project: keep it offline, use the backup key only for
   rotation.
8. **KernelSU allowlist.** `docs/coloros-on-fold.md` notes KernelSU dropping
   Shell from its allowlist when the guest writes `packages.list`; the app's
   own root grant may be affected the same way. Needs a test.

---

## 7. Friend build 1: the probe build and its findings (`oneos.findings/1`)

App version `0.2.0-probe` (versionCode 2). Friends install it, run the tests
as root and send the findings zip to the OneOS team; the team verifies the
findings (above all the installd table) and only then ships a build that can
switch. **Nothing on the tester's phone may change**: every root command only
reads, and outputs go only into the app's own cache.

### 7.1 Flow

1. Home → *Run tests* (`RunTestsActivity`). The screen explains what is read,
   that nothing changes and what is removed before sharing, and lists every
   test (tap one to see its exact command).
2. *Run tests* → a dialog → `su -c id` (`SuProbe`). Anything but uid 0 stops
   here with the reason (allow OneOS in the root manager).
3. Before root is asked, the app parses and audits the bundled list and
   runner (section 7.2); a violation stops the run ("failed its read-only
   check, so nothing ran").
4. The app copies `assets/probe/probe.sh` and `assets/probe/commands.list` to
   `files/probe/` (verified by SHA-256) and runs
   `su -c "sh <files>/probe/probe.sh <files>/probe/commands.list"`
   (`RootProbeRunner`). The runner prints everything base64 framed (section
   7.3); the app decodes it into `cache/probe-capture/` and shows per-test
   progress (waiting / running / ok / not present / timed out / failed).
5. Without root, the app reads the device facts (`FactProbe`, as the device
   report), derives the installd table from the captured dex
   (`:core:safety` `HostInstalldTable`, dexlib2 3.0.10) and builds the bundle:
   every text file is redacted (section 7.5) into
   `cache/findings/findings-<model>-<date>/`, which is zipped to
   `cache/findings/findings-<model>-<date>.zip`. The raw capture is deleted.
6. *View and share findings* (`FindingsActivity`): summary.txt, the file list
   (tap any text file to read it as it will be shared), what was removed;
   **Share** (share sheet; SESL core's `androidx.core.content.FileProvider`,
   authority `com.fahadali.oneos.findings`, serving only `cache/findings/`)
   or **Save to Downloads** (`ACTION_CREATE_DOCUMENT`, no storage
   permission). The APK declares no permission at all
   (`aapt2 dump permissions` lists none).

A new run deletes the previous capture and findings first; *Delete findings
from this phone* removes them by hand.

### 7.2 The root command list (`app/src/main/assets/probe/commands.list`)

The one auditable file: every command OneOS runs as root besides
`su -c id` and the runner call itself. `probe.sh` sources it; the grammar is
enforced by `ProbeCommandList` (anything else is a parse error, so no other
shell line can run):

```
#== <group title>
#: <description of the next entry>
run   <id> <timeout s> <output file>   '<command>'   stdout + stderr of `sh -c '<command>'`
files <id> <timeout s> <output folder> '<command>'   the command prints paths or jar!entry;
                                                     each is read (cat / unzip -p) into a file
```

Exit codes: 0 ok; 3 (said by the entry) or 127 (command not found) not
present; 124/137/143 timed out; anything else failed. Commands use double
quotes only.

`ProbeAudit` (`:core:model`) checks the list in the unit tests and again in
the app before every run:

- **allow-list** of commands in command position (also inside `$(...)`, after
  `|`, `&&`, `||`, `then`, `do`): `getprop cat ls sha256sum stat grep sed awk
  sort uniq wc head tail cut tr printf echo dumpsys getevent service uname df
  id unzip basename dirname readlink pidof getenforce test [ true false exit
  command break continue magisk /data/adb/ksud /data/adb/apd`;
- **argument rules**: `dumpsys` only `SurfaceFlinger` (arguments only
  `--display-id`, `--list`; others such as `--latency-clear` or
  `--timestats -enable` change SurfaceFlinger state) or `display` (no
  arguments); `service` only `list`; `getevent` only with `-p` and flags
  `-p`/`-l`/`-i`, no device and no `-c` (prints capabilities and exits; no
  events are read); `unzip` only `-l`/`-p`; `sed` only options `-n -E -r`
  and one printing command (`[address]s/re/repl/[gpI0-9]`, `p`, `d`, `q`,
  `=`; so no `-i`, `-f`, `w`, `W` or `e` in any position); `awk` without
  `-f`, `system`, `|`, `>`, `getline`; `sort` without `-o`/`--output`;
  `uniq` without an output file; `magisk`/`ksud`/`apd` only `-v`/`-V`;
  `command` only `-v`;
- **refused**: output redirection other than `2>&1`, `>&2`, `>/dev/null`,
  `2>/dev/null` as whole tokens (`>/dev/null_x` and `2>&10` are refused);
  assignments to `PATH`, `IFS`, `ENV`, `LD_*`; background `&`; backticks;
  here-documents; `$(( ))`; single quotes inside a command; `case`, `eval`,
  `exec`, `source`; dynamic command names (`$x ...`); the strings `logcat`,
  `telephony.registry`, `setprop`, `resetprop`, `settings `, `service call`,
  `/proc/sysrq`.

The runner (`probe.sh`) gets its own audit: it may only run `printf`,
`timeout` (starting only `sh -c "$4"`, `cat` or `unzip -p`), `base64`,
`stat`, `command -v`, `set -f` and source `$LIST`; its redirections go only
to stdout, `/dev/null` and file descriptors 3 and 4 (pipes inside the
process). It writes no file. A `files` entry's paths (and the jar of a
`jar!entry`) are read only when they are regular files (`[ -f ]`): never a
block or character device, FIFO or folder (`@@NOTE <path> skipped (not a
regular file)`, the entry counts as failed). `timeout` (toybox) puts the
command in its own process group and signals the whole group, so a stuck
pipeline (`service list | sed ...`) ends with it.

### 7.3 Stream format (`oneos.probe-stream/1`)

```
@@ONEOS-PROBE 1
@@PROBE <id> <timeout s>
@@FILE <target> <source>       source "-" for a run entry, a path, or jar!entry
<base64, 76 columns>
@@END <exit code of the read>
@@NOTE <text>                  e.g. a file over 64 MB skipped
@@STATUS <id> <exit code>
@@ERROR <text>                 runner stopped: no timeout/base64, list unreadable
@@DONE
```

Local paths (`ProbePaths`): a run entry writes its target; a files entry
writes `<folder>/<source with / as _>`, and `jar!entry` becomes
`<folder>/<jar path with / as _>/<entry>`
(`installd/system_framework_services.jar/classes.dex`). Names outside
`[A-Za-z0-9._+=,@-]` become `_`; `.`/`..` segments are refused. The app kills
the run if it prints nothing for the current entry's timeout + 30 s, or after
20 minutes in all.

Checked on the build server: the shipped runner and list under dash,
busybox ash and bash produce the frames above, the exit codes 0/1/2/3/127
come through, and `services.jar!classes.dex` of the F8U decodes byte for byte
equal to `unzip -p`, from which `HostInstalldTable` gives exactly
`switcher/patches/host_installd.txt` (85 methods).

### 7.4 What is read

| Group | Entries (output) |
| --- | --- |
| Build and system properties | `build.getprop` full `getprop` (redacted) (`props/getprop.txt`); `build.key` fingerprint, build id, release/SDK, `ro.build.version.oneui`, model/device, `ro.soc.*`, `ro.board.platform`, ABI, vendor API, flash lock, verified boot, verity, warranty bit, secure/debuggable (`props/key.txt`) |
| CPU | `cpu.cpuinfo` `/proc/cpuinfo`; `cpu.uname` `uname -a`; `cpu.midr` MIDR_EL1/REVIDR_EL1 per core |
| installd interface | `installd.classpath` BOOTCLASSPATH / SYSTEMSERVERCLASSPATH / DEX2OATBOOTCLASSPATH lines of system_server's environment (nothing else of it); `installd.jars` size + SHA-256 of each candidate jar and `ls -l /system/framework` (+ `oat/arm64`); `installd.dex` the dex entries defining `android.os.IInstalld$Stub` (checked for the `IInstalld$Stub$Proxy` descriptor), the whole jar if under 15 MB, in class-loader order |
| Displays | `dumpsys SurfaceFlinger --display-id`; `dumpsys display` DisplayDeviceInfo / uniqueId / port lines without Wi-Fi or virtual displays (their names and addresses are the user's TV or PC: Smart View, DeX); listing and copies of `/vendor/etc/{displayconfig,devicestate}/*.xml` and the `/odm/etc` variants |
| Input and touch | `getevent -pl`; `/proc/bus/input/devices`; `input-port-associations.xml` (vendor, odm); per `/sys/class/sec/tsp*`: `ls`, `input/name`, `input/enabled`, `enabled`, `cmd_list` |
| Backlight | `/sys/class/backlight/*/{max_brightness,brightness,type}` |
| HALs and services | `service list` names only; `init.svc.*` props; `ls /vendor/bin/hw`; `ls /vendor/etc/init` |
| SELinux policy | `ls -l` of the five policy folders; SHA-256 of each `.cil`; `(type` / `(typealias` names from the CIL files as `guest_prepare.sh` reads them (debug files skipped) |
| Storage and root | `df /data`; `ls -ld` of `/data/local/tmp/oneos` and `/data/local/tmp/lineage_stage`, its path up to 0.3.6 (not present = fine); `id; getenforce`; `ksud -V` / `magisk -v` + `-V` / `apd -V`, whichever exists |

Not read: logcat, `dumpsys telephony.registry` or any telephony, SMS,
contacts, accounts, Wi-Fi state, location, photos or user files.

### 7.5 Redaction (`oneos.redact/1`, `:core:model` `Redactor`)

Runs on the phone on every text file before the bundle exists; only dex and
jar files (system binaries) are copied unchanged. Each value becomes
`<kind:hash>`, the hash being 6 hex digits of SHA-256(salt, kind, value) with
a random salt per bundle (never stored): the same value has the same token
inside one bundle and cannot be matched across bundles.

- **By property name** (getprop `[key]: [value]`, also values that span
  several lines, and `prop.name=value` lines): `*imei*`; `*meid*`; `*iccid*`;
  eSIM EID (`eid`, `euicc_id` as a name part); `*imsi*`; `*serial*`
  (`ro.serialno`, `ro.boot.serialno`, `ril.serialnumber`,
  `ro.boot.ap_serial`, ...); Samsung and other device IDs (as a name part:
  `did`, so `ro.boot.em.did`; `un`, so `ro.boot.un`; `cid`, `uniqueno`,
  `unique_id`, `unique_number`, `device_id`, `android_id`, `ufsid`, `chipid`,
  `cpuid`, `emmcid`, `kg.ap` (Knox Guard), `distname`
  (`ro.vendor.skeymast.distname`), `vaultkeeper.id`, `rfcal_date`); MAC (`macaddr`, `bdaddr`, `btaddr`, `wifi.mac`,
  `bluetooth.address`, ...); phone (`msisdn`, `mdn`, `line1_number`,
  `phone.number`, `voicemail_number`, `subscriber_number`, ...); accounts
  (`account`, `email`, `username`, `user.name`); device names
  (`device_name`, `device.name`, `hostname`, `friendly_name`, `nick_name`,
  `*bluetooth*name`); `lat`/`lon`/`cell_id` names; IP values (IPv4, or IPv6
  with 2+ colons; not `default:6 0:400`) of `dns`/`ipaddr`/`gateway`/`ip`
  names; Wi-Fi (`wifi.`/`wifi_` anywhere in
  the name, so also `persist.sys.wifi.*` and `ro.vendor.wifi.*`; `*ssid*`,
  `*hotspot*`, `*softap*`): the value is removed (BSSID if MAC-shaped, else
  SSID) unless it is plainly technical (`wlan0`, `wlan0,wlan1`,
  `p2p-dev-wlan0`, `wifi-aware0`, a number up to 6 digits, a duration, a
  path). Empty, 0/1, true/false, service states (`running`, `stopped`, ...)
  and `Android` are kept; so are, under any name, a plain path
  (`ro.bt.bdaddr_path`), a library file (`ro.bluetooth.library_name` =
  `libbluetooth_qti.so`) and a Samsung model (`ro.quick_start.device_id` =
  `SM-F976`; spread through the bundle it removed the model from every
  build property). Never removed by name, being the same on every phone of a
  model or carrier: Samsung carrier codes (`*.sec_cid`, `*.sec_pcid`,
  `sec_cid_ver`), the Bluetooth DI profile (`bluetooth.device_id.*`),
  `cache_key.*` nonces and `remote_provisioning.hostname`. **Safety net**:
  a value with a run of 16+ letters and digits (4+ digits, 8+ different
  characters) under a name no rule knows is removed as a device ID, unless
  the name says digest, uuid, fingerprint, vbmeta, build, sha256 or checksum
  (on the tested Fold it catches exactly `ro.vendor.security.vaultkeeper.id`,
  `persist.bluetooth.registerapptoscpm`, `ro.boot.kg.ap`,
  `ro.vendor.skeymast.distname` and the serials). Service-state properties (`init.svc.*`,
  `init.svc_debug_pid.*`, `ro.boottime.*`) are named after services and never
  removed by name (`init.svc.vendor.serial_logger` is not a serial number).
  Every value removed by name (5+ characters, 4+ different characters) is
  then removed wherever else it appears in the bundle (a serial inside the
  boot config, a later file); identifiers (IMEI, serial, device ID, MAC,
  ICCID, EID, IMSI) in any letter case, MAC addresses also with `-` or no
  separator, hex IDs also without `0x`, all spellings with one token. A
  low-variety value such as `00000001` is removed only where its name is, so
  it cannot cut into the input bitmaps of `/proc/bus/input/devices`.
- **By value pattern** in every line: emails (not a link of an `a@b@c`
  chain such as `system@framework@services.jar@classes.odex`, and not a
  file name such as `samsung.software.media.c2@1.0-service.rc`: `rc`, `so`,
  `jar`, `xml`, ... are not domains); `Account {name=...}` and
  `accountName=`; MAC addresses, also right after a prefix such as `wifi:`
  (Wi-Fi display ids) or `mac:` but not inside a longer colon-separated run
  (not `00:00:...`, `02:00:00:00:00:00`, `ff:ff:...`), BSSID next to its
  label; EID `89` + 30 digits; ICCID `89` + 17-18 digits; IMSI, IMEI (14-16
  digits) and MEID next to their label; any 15-digit number that passes the
  IMEI Luhn check; serials next to `serial`/`serialno` (also the `Serial`
  line of `/proc/cpuinfo`) and input device `Uniq=` values (a USB
  accessory's serial number; Bluetooth ones are MACs); E.164 numbers
  (`+966 50 123 4567`, `+44 ...`); Saudi numbers `05xxxxxxxx` and
  `(00)9665xxxxxxxx`; SSIDs next to `ssid`; GPS pairs (`52.5163, 13.3777`,
  |lat| <= 90, |lon| <= 180) on a line or under a property name that says
  location, gps, gnss, fused, fix, lat/lon, coord or geo (refresh rates
  `60.00001, 48.000008` and cutout paths are pairs too) and `lat=`/`lon=`
  values; cell ids
  (`mCi=`, `mPci=`, `mTac=`, `mLac=`, `mNci=`); the names of virtual and
  Wi-Fi displays (`DisplayDeviceInfo{"<name>": uniqueId="virtual:<pkg>,<uid>,<name>,<n>"`,
  a TV's name under Smart View), which `display.dm` also leaves out at the
  source. Text already replaced is never matched again.
- **Bluetooth input device names**: the `N: Name="..."` of every
  `I: Bus=0005` block of `/proc/bus/input/devices` (a paired keyboard or
  controller often carries its owner's name) is learned before any file is
  redacted and removed wherever it appears (also from `input/getevent.txt`,
  which lists devices without their bus). Built-in devices keep their names.
- **Log**: `redaction.txt` and report.json `redaction`: counts per kind and
  per file, distinct values per kind and the property names removed by key,
  never a value.

Tests: `RedactorTest` (33 tests on realistic samples, including no false
positives on fingerprints, display ids, SHA-256 lines, dates and versions),
`RedactorSampleTest` (a full synthetic Samsung capture, `RedactorSample`:
getprop with 30+ planted personal values in real and plausible property
names, cpuinfo, uname, display manager and SurfaceFlinger lines, framework
cutout resources, display and device-state XML, getevent, input devices,
init states; no planted value survives and the technical lines come through
unchanged), `RedactorFindingsTest` (the first real bundle, Z Fold F8U
0.2.0-probe: the model, carrier codes, refresh rates, oat and HAL file names
and the copyright line stay; the per-phone IDs it kept go) and
`FindingsBundleTest` (no planted secret survives anywhere in the zip). The
first real bundle had 306 removals, about 280 of them not personal; the same
phone now gives 12, all per-phone IDs.

### 7.6 Bundle layout and `report.json`

`findings-<model>-<yyyy-MM-dd>.zip`, every entry under the folder of the
same name, `report.json` and `summary.txt` first:

```
report.json  summary.txt  redaction.txt
props/getprop.txt  props/key.txt
cpu/cpuinfo.txt  cpu/uname.txt  cpu/midr.txt
installd/classpath.txt  installd/jars.txt  installd/<jar path>/classesN.dex (or installd/<jar path>)
installd/table.txt  installd/host_installd.txt          (when the app derived the table)
display/...  input/...  backlight/...  hal/...  selinux/...  storage/...  root/...
```

`installd/table.txt` is format `oneos.installd-table 1` (DESIGN.md §6.2)
with the phone's fingerprint and the source jar's SHA-256 from
`installd/jars.txt`; `installd/host_installd.txt` is the older
`name code signature` layout that `guest_installd_abi.py` reads today.

```json
{
  "schema": "oneos.findings/1",
  "generatedAt": "2026-10-22T15:10:31+03:00",
  "app": {"id": "com.fahadali.oneos", "version": "0.2.0-probe", "versionCode": 2},
  "probe": {"stream": "oneos.probe-stream/1", "completed": true, "error": null,
            "runnerSha256": "...", "commandsSha256": "...", "commands": 28},
  "device": {"brand": "samsung", "manufacturer": "samsung", "model": "SM-F976B", "device": "q8q",
             "family": "Z_FOLD", "form": "FOLD", "formEvidence": ["..."], "soc": "SM8850",
             "socVendor": "QUALCOMM", "socPlatform": "canoe", "socName": "Snapdragon 8 Elite Gen 5",
             "oneui": "9.0", "oneuiRaw": "90000", "androidRelease": "17", "sdk": 37,
             "buildId": "CP2A.260605.016", "fingerprint": "...", "vendorApiLevel": "202504",
             "abis64": ["arm64-v8a"], "kernel": "...", "flashLocked": "1", "verifiedBootState": "green",
             "screenLockSet": false, "panels": [{"id": 0, "name": "...", "widthPx": 2256, "heightPx": 2504,
             "xdpi": 420.0, "ydpi": 420.0, "inches": 7.6}],
             "root": {"kind": "KERNELSU", "managerPackages": ["me.weishu.kernelsu"],
                      "manager": "kernelsu ksud ...", "suIdState": "GRANTED", "suContext": "u:r:su:s0"}},
  "cpu": {"hardware": "...", "summary": "8 cores: ...", "features": ["..."], "heterogeneous": false,
          "reported": {"sve": true, "sve2": true, "sme": true, "sme2": false, "mops": false, "bf16": true, "i8mm": true},
          "colorOsRequired": ["sve2", "sme"], "missingForColorOs": [],
          "cores": [{"cpu": 0, "implementer": "0x51", "part": "0x002", "variant": "0x3", "revision": "2", "label": "..."}]},
  "verdict": "OK | WARN | BLOCK",
  "verdictLabel": "Compatible | Warning | Not supported",
  "findings": [{"id": "cpu-features", "level": "OK", "title": "...", "detail": "..."}],
  "probes": [{"id": "build.getprop", "group": "...", "kind": "run", "target": "props/getprop.txt",
              "status": "ok | not present | timed out | failed | not run", "exitCode": 0, "millis": 180,
              "files": [{"path": "props/getprop.txt", "source": "-", "bytes": 61234, "exitCode": 0}],
              "notes": []}],
  "installd": {"derived": true, "error": null, "methods": 85, "sourceJar": "/system/framework/services.jar",
               "sourceEntry": "classes.dex", "sourceSha256": "...", "fingerprint": "...",
               "table": "installd/table.txt", "tableNote": null, "inputs": ["..."], "notes": []},
  "selinux": {"typeDeclarations": 0, "typealiasDeclarations": 0, "names": 0,
              "genericAppTypes": {"untrusted_app": true, "...": true}},
  "redaction": {"rules": "oneos.redact/1", "saltedPerBundle": true, "total": 12,
                "counts": {"serial": 4}, "distinct": {"serial": 1}, "files": {"props/getprop.txt": {"serial": 3}},
                "propertiesByKey": ["ro.serialno"]},
  "files": [{"path": "props/getprop.txt", "bytes": 61234, "sha256": "...", "redacted": true}]
}
```

`files` lists every file of the bundle except report.json with its SHA-256
as shipped (after redaction); `redacted` is false for the dex/jar copies and
the files the app generated. `device` is null when the app could not read the
facts (then a `facts-unread` WARN), `cpu` falls back to the root-read
`cpu/cpuinfo.txt`. `summary.txt` is the same in text: phone, chip, One UI,
Android, fingerprint, root, CPU features, verdict and findings, installd,
SELinux, one line per test, redaction counts.

### 7.7 Findings added in this build

Device report and bundle (`CompatEvaluator`):

| id | Level | When |
| --- | --- | --- |
| `cpu-features-missing` | WARN | `/proc/cpuinfo` lacks any of `sve2`, `sme`: "CPU lacks <features> used by the ColorOS images" (the images' `bootstrap/linker64` uses SME, MOPS, SVE/SVE2; the SM8850 Fold runs it without MOPS or SME2, so those are not required) |
| `cpu-features` / `cpu-unknown` | OK / INFO | all present / not readable |
| `android-version-differs` | WARN | host SDK matches none of the profile's systems (0.4.85: the profile's own, not every image of the build): "Android version differs from the OneOS images (17); switching may not work", or, when One UI is older than all of them, "The systems for this phone need Android 17: update One UI first"; BLOCK at switch time ("Update One UI first" on the home screen) |
| `free-space-short` | WARN | 0.4.85 (was BLOCK, which read "Not supported" on phones with a system already set up): "Low on free space"; the set-up and switch gates check the real numbers |

S25 Ultra (SM-S938*, SM8750) and S26 Ultra stay WARN (`untested-model`,
S Ultra family), never BLOCK; One UI 9.0 (`90000`) is the tested version.

Bundle only (`ProbeFindings`, from root reads; none of them is BLOCK, since
nothing switches and the team verifies):

| id | Level | When |
| --- | --- | --- |
| `installd-table` | OK | derived; `destroyUserData` and `createAppData` present |
| `installd-unknown` / `installd-unexpected` | WARN | not derived (no dex, no class, ambiguous copies, overloads, parse error) / required methods missing |
| `selinux-types` / `selinux-types-missing` / `selinux-types-unread` | OK / WARN / INFO | section 1.8 |
| `stage-present` | INFO | a OneOS stage exists, `/data/local/tmp/oneos` or `/data/local/tmp/lineage_stage` (only listed) |
| `root-manager-version` | INFO | `ksud -V` / `magisk -v` / `apd -V` |
| `probes-incomplete`, `probe-run-incomplete`, `facts-unread` | INFO / INFO / WARN | tests failed or timed out; the stream ended early; FactProbe failed |

### 7.8 On the server: checking a tester's findings

1. `sha256sum` every file against `report.json` `files`.
2. installd: in `installd/<jar>/`, `zip /tmp/host.jar classes*.dex` and run
   `scripts/host-installd-table.sh /tmp/host.jar` (or point it at the whole
   jar if it was captured); compare with `installd/host_installd.txt` and the
   method lines of `installd/table.txt`. Check the class-loader order in
   `installd/classpath.txt` (the first jar that defines `IInstalld$Stub`
   wins) and the jar's SHA-256 in `installd/jars.txt`.
3. Compare displays, touch ICs (`tsp*/cmd_list`), backlight range, HAL
   names and SELinux types with the F8U profile before enabling any patch for
   that model.

### 7.9 Known limits

- Redaction is pattern based. A property that holds a personal value under
  a name none of the rules knows (and in a shape no value pattern knows,
  such as a 9-digit local number or a Wi-Fi name under a `wlan.*` name) stays.
  Bluetooth input device names are only learned from
  `/proc/bus/input/devices`: if that entry fails, a paired device's name can
  stay in `input/getevent.txt`, and the name of a virtual input device an
  app creates (a uinput device on another bus) always stays. Phone numbers
  are matched in E.164 and Saudi forms only. The safety net only knows long
  values; a short ID under an unknown name (like the 8-digit
  `ro.boot.em.cid`, which a rule does know) would stay. `report.json` and
  `summary.txt` are written from the phone facts after redaction and are not
  redacted themselves; they hold no personal values today (model, build,
  kernel release, built-in panels, root manager). The preview shows every
  file before sharing (up to 512 kB each; the largest text file on the
  tested Fold, `selinux/types.txt`, is 182 kB).
- A file over 64 MB is skipped with a note; a jar that defines
  `IInstalld$Stub` is captured whole only under 15 MB, otherwise only the
  defining `classesN.dex`.
- Busybox ash with standalone applets may run its own `pidof`; the runner
  sets `PATH=/system/bin:$PATH`, and Android's `sh` (mksh) uses toybox.
