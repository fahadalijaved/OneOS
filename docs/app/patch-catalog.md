# OneOS app: patch catalog

> **Renamed after 0.3.6:** the stage is `/data/local/tmp/oneos` (was `/data/local/tmp/lineage_stage`), its set-aside copies `oneos.old-<epoch>` / `oneos.trash-<epoch>` (were `lineage_stage.old-*` / `.trash-*`), and the session scripts `oneos_switch.sh`, `guest_prepare.sh`, `guest_start.sh` (were `switch_to_lineage.sh`, `master_prepare.sh`, `master_inner.sh`). The app's root script and `scripts/deploy-phone.sh` rename an old stage and its copies when they are idle.

Status: design study (key `patch-catalog`). It lists every behaviour the
current pipeline applies, so the OneOS app can show them as patches with
toggles, choose defaults per phone and guest OS, and refuse a session when it
cannot verify the safety entries. Sources: `docs/coloros-on-fold.md`,
`switcher/README.md`, `scripts/make-overlays.sh`, `switcher/patches/*.py`,
`switcher/assets/*.sh`, and the run-33 commit `474b331`. Line numbers refer to
commit `474b331`.

Tested so far: one phone, the Galaxy Z Fold SM-F976B ("F8U"). A
read-only `getprop` on 2026-10-22 returned `ro.build.version.oneui=90000`,
`ro.soc.model=SM8850`, `ro.product.vendor.device=q8q`,
`ro.build.version.sdk=37`, `ro.build.characteristics=phone` and
`ro.surface_flinger.supports_background_blur=0`. Only one guest has been
tested: ColorOS 17 for the Find N6 (PLP120, `CP2A.260605.016`, MysticGSI ext4).
Nothing has run on an S26 Ultra or with any other guest.

Markers used below:
- **[CF]**: specific to ColorOS on the Fold. The default is OFF, or the entry is hidden, on an S26 Ultra or any non-ColorOS guest.
- **[F8U]**: carries numbers measured on this phone (panel ports, backlight levels, nits table). It may apply elsewhere only when a fix pack supplies that device's values.

## 1. Categories and toggle rules

| Category | Meaning | Toggle |
| --- | --- | --- |
| `safety` | Keeps the guest away from One UI's data, keys, power state and boot flow. Run 25 is why this exists. | `locked`: never shown as a switch. If it cannot be applied or verified, the session is refused. |
| `core` | Needed for any guest to boot in the container. | `locked` or `advanced`, depending on the entry |
| `samsung` | Specific to a Samsung host: the Qualcomm composer, Samsung's APEX set, imsd, audio HAL parameters, panel values. | `auto` from host facts |
| `form` | Fold, Flip or bar form factor: layouts, lid switch, touch ICs. | `auto`: hidden when the form does not match |
| `guest` | Specific to one guest OS (ColorOS/OPPO, LineageOS, AOSP, ...). | `auto` from guest facts and anchors |
| `optional` | Quality fixes that are not needed to boot. | `toggle` |
| `diagnostic` | Logs, probes, recordings and test modes. | `toggle` or `advanced` |

Toggle values: `locked` (no switch), `toggle` (normal switch), `advanced`
(under Settings > Advanced, with a warning), `dev` (debug builds only),
`hidden` (the predicate is false, so the entry is not listed).

## 2. Where each entry runs in the app

First release (`DESIGN.md` §5, decision 2026-10-22): the build server
runs the `import` and `patch` stages below and publishes one signed OneOS
package per OS image (image, patched files, RROs, scripts, catalog); its
link is shared privately. Entries built into a package's files have
no toggle on the phone; script-level entries keep their `ONEOS_*` toggles.
The on-phone `import`/`patch` stages described here are the later option
for user-supplied images (`patch-engine.md`). Fix packs carry our catalog,
scripts, RROs and per-device tables for a package.

| Stage | Runs | Replaces today |
| --- | --- | --- |
| `pack` | Content of a signed fix pack: rule JSON, helper smali, the RRO apk built from `switcher/overlays/`, binary-patch descriptors, device tables | build-server steps in `scripts/make-overlays.sh` |
| `import` | On the phone, once per image: unpack, ext4 check, SHA-256, guest fact probe, APEX payload extraction from the read-only mounted image | `scripts/deploy-phone.sh:271-291`, `make-overlays.sh:151-172` |
| `patch` | On the phone, once per image and host build: the `PatchEngine` rewrites dex with dexlib2, then `GuardVerifier`, then the guard manifest | `make-overlays.sh:21-99`, `switcher/patches/*.py`, `scripts/check-dex.py` |
| `probe` | On the phone, every session: host fingerprint, host installd table, host SELinux types, init services, sysfs nodes | `scripts/host-installd-table.sh`, `guest_prepare.sh:301-310` |
| `stage` | Root shell before the pivot | `guest_prepare.sh`, `oneos_switch.sh:1-434` |
| `props` | Root shell, host property area | `guest_props.sh` |
| `inner` | Inside the guest mount namespace, before zygote | `guest_start.sh` |
| `activator` | After the guest's WindowManager is up | `oneos_switch.sh:549-815` |
| `watcher` | Host-side session monitor and return triggers | `oneos_switch.sh:817-979` |
| `return` | Teardown, then reboot | `return_to_oneui.sh` |

The on-phone dex engine uses `com.android.tools.smali:smali-dexlib2:3.0.10` and
`com.android.tools.smali:smali:3.0.10` to assemble our helper classes. Both
are on Google Maven (checked 2026-10-22, group index 3.0.0 to 3.0.10). The
dexlib2 POM depends on `com.google.guava:guava:31.1-android` and
`com.google.code.findbugs:jsr305:3.0.2`. Proposed Kotlin classes, one per
current patcher:
`StorageGuardsPatch`, `InstalldAbiPatch`, `VoldKeysPatch`, `PowerGuardsPatch`,
`SysRqPatch`, `OwnIdmapPatch`, `SkipHostApexServicesPatch`,
`DisplayModeSpecsPatch`, `OplusWaitForServicePatch`, `OplusBootHangsPatch`,
`BacklightCurvePatch`, plus `EmptyTryRangeCheck` (port of `check-dex.py`) and
`GuardVerifier`. Shell stages keep reading `ONEOS_*` variables. The app
compiles the resolved catalog into `$STAGE/session.env`. **Locked entries get
no variable**: the scripts no longer accept a way to switch them off (see §6).

## 3. Safety model the catalog enforces

1. **Patch, then verify independently.** After `patch`, `GuardVerifier` scans every dex of every jar on the guest's `SYSTEMSERVERCLASSPATH`, not only `services.jar` and `oplus-services.jar`. Any remaining forbidden call site fails the check:
   - `IVold`/`IInstalld` destroy, wipe, move or prepare calls (lists in `guest_storage_guards.py:36-41`)
   - `AndroidKeyStoreMaintenance` clear and re-key calls
   - `IInstalld$Stub.asInterface` anywhere except inside `OneOSInstalldProxy`
   - `IStorageManager.commitChanges` in AMS
   - a `"sys.powerctl"` string in PowerManagerService
   - `doSysRq` without the `'c'` early return

   It also checks that `OneOSInstalldProxy` routes each method either to the host code from the probed table or to a throw.
2. **Guard manifest** (replaces `guards.txt`, `make-overlays.sh:94-99`). `$STAGE/guards.json` (schema `oneos.guards/1`, see `DESIGN.md` §7; in the first release it is the manifest's `guards` object; `guards.txt` is still written from it for the scripts) records:
   - image SHA-256 and host `ro.build.fingerprint`
   - host `services.jar` SHA-256 and installd table SHA-256
   - per jar: SHA-256 and the guard ids applied
   - verifier version

   The shell stage checks hashes and the bind inode, as `guest_prepare.sh:26-39` and `:159-163` do today. A host build change means re-patching.
3. **Fix packs may tighten safety, never loosen it.** A pack may add forbidden patterns, bridges or refusals. Removal of compiled-in safety rules is ignored.
4. **No guest is trusted by family.** A guest family the app does not know still gets every `safety`, `core` and `samsung` entry. `guest` entries stay off, and the user sees "untested".

## 4. Facts used by predicates (FactProbe)

Host facts:

| Fact | Source | Notes |
| --- | --- | --- |
| `device.model` | `ro.product.model` | |
| `device.vendor_device` | `ro.product.vendor.device` | |
| `device.soc` | `ro.soc.model` | |
| `device.form` | `fold` / `flip` / `bar` | From the model prefix (SM-F9xx Fold, SM-F7xx Flip), cross-checked with a `flip` SW_LID input device and a second `sec_touchscreen2`. `ro.build.characteristics` cannot tell: it says `phone` on the Fold. |
| `host.oneui` | integer `ro.build.version.oneui` | Use the integer, not the marketing name: the F8U reports 90000. |
| `host.sdk` | `ro.build.version.sdk` | |
| `host.init_service(name)` | `init.svc.<name>` exists | |
| `host.sysfs(path)` | path exists | |
| `host.input(name)` | input device with that name exists | |
| `host.sepolicy_types` | CIL scan, as in `guest_prepare.sh:302-306` | |
| `host.installd_table` | Derived on the phone from `/system/framework/services.jar` | |
| `host.dual_sim`, `host.nr` | telephony | |
| `root.kind` | `ksu`, `magisk` or `apatch` | |

Guest facts:

| Fact | Source |
| --- | --- |
| `guest.family` | `coloros` if `system/framework/oplus-services.jar` exists and the image sets `ro.oplus.*` props; `lineage` if `ro.lineage.version` is set (`MainActivity.java:232`); `aosp`; otherwise `unknown` |
| `guest.build_id`, `guest.sdk`, `guest.prop(key)` | the image's build props |
| `guest.file(path)`, `guest.sha1(path)` | the mounted image |
| `guest.class(jar, cls)`, `guest.string(jar, s)`, `guest.method(jar, cls, sig)` | dex anchors |
| `guest.feature(name, glob)` | a feature declared in the image's own `my_*` files |

Runtime facts, known only inside a running session:
- `rt.sf_ports`: display ports reported by the guest's SurfaceFlinger
- `rt.tsp(name)`: sysfs node of the touch IC with that name

## 5. Catalog schema (JSON)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "oneos/patch-catalog/1",
  "type": "object",
  "required": ["catalog_version", "entries"],
  "properties": {
    "catalog_version": {"type": "integer"},
    "pack": {"type": "object", "properties": {
      "id": {"type": "string"}, "version": {"type": "integer"},
      "min_app_version": {"type": "integer"}, "signature": {"type": "string"}}},
    "entries": {"type": "array", "items": {"$ref": "#/$defs/entry"}}
  },
  "$defs": {
    "entry": {
      "type": "object",
      "required": ["id", "title", "description", "category", "toggle", "default",
                   "applies_when", "stage", "impl", "risk_if_wrong", "status"],
      "properties": {
        "id": {"type": "string", "pattern": "^(safety|core|samsung|fold|flip|coloros|lineage|aosp|opt|diag)\\.[a-z0-9_]+$"},
        "title": {"type": "string", "maxLength": 60},
        "description": {"type": "string", "maxLength": 200},
        "category": {"enum": ["safety", "core", "samsung", "form", "guest", "optional", "diagnostic"]},
        "toggle": {"enum": ["locked", "toggle", "advanced", "dev"]},
        "default": {"enum": ["on", "off", "auto"]},
        "applies_when": {"$ref": "#/$defs/pred"},
        "requires": {"type": "array", "items": {"type": "string"}},
        "conflicts": {"type": "array", "items": {"type": "string"}},
        "stage": {"enum": ["pack", "import", "patch", "probe", "stage", "props", "inner", "activator", "watcher", "return"]},
        "impl": {"type": "object", "required": ["kind"], "properties": {
          "kind": {"enum": ["dex_patch", "binary_patch", "rro", "feature_switch", "prop", "settings",
                            "file_stage", "bind", "daemon", "shell_step", "sysfs_monitor", "check"]},
          "handler": {"type": "string"},
          "args": {"type": "object"},
          "legacy_env": {"type": "string"},
          "legacy_ref": {"type": "string"}}},
        "anchors": {"type": "array", "items": {"$ref": "#/$defs/pred"}},
        "postconditions": {"type": "array", "items": {"type": "string"}},
        "on_anchor_missing": {"enum": ["refuse_session", "block_image", "skip", "skip_warn"]},
        "device_values": {"type": "object", "description": "per ro.product.vendor.device values, e.g. ports, nits tables"},
        "evidence": {"type": "array", "items": {"type": "object", "properties": {
          "run": {"type": "integer"}, "summary": {"type": "string"}}}},
        "risk_if_wrong": {"type": "string"},
        "tested_on": {"type": "array", "items": {"type": "string"}},
        "status": {"enum": ["stable", "experimental", "deprecated"]}
      }
    },
    "pred": {"oneOf": [
      {"type": "object", "required": ["all"], "properties": {"all": {"type": "array", "items": {"$ref": "#/$defs/pred"}}}},
      {"type": "object", "required": ["any"], "properties": {"any": {"type": "array", "items": {"$ref": "#/$defs/pred"}}}},
      {"type": "object", "required": ["not"], "properties": {"not": {"$ref": "#/$defs/pred"}}},
      {"type": "object", "required": ["fact"], "properties": {
        "fact": {"type": "string"}, "arg": {},
        "eq": {}, "in": {"type": "array"}, "gte": {"type": "number"}, "lte": {"type": "number"},
        "exists": {"type": "boolean"}, "matches": {"type": "string"}}},
      {"const": true}
    ]}
  }
}
```

The example entries below are fully filled in. A device id is written as
`ro.product.vendor.device`, a run as `run N`.

```json
[
 {
  "id": "safety.storage_guards",
  "title": "Protect One UI's data",
  "description": "Removes every call that could make One UI's installd, vold or keystore delete, wipe or re-key the phone's real data.",
  "category": "safety", "toggle": "locked", "default": "on",
  "applies_when": true,
  "stage": "patch",
  "impl": {"kind": "dex_patch", "handler": "StorageGuardsPatch",
           "args": {"jars": ["system/framework/services.jar", "system/framework/oplus-services.jar?"],
                    "drop_void_calls": {"IVold": ["destroyUserStorage", "prepareUserStorage", "format", "partition", "forgetPartition", "moveStorage", "onUserRemoved", "abortChanges", "startCheckpoint", "shutdown", "sdlockErase"],
                                        "IInstalld": ["destroyUserData", "destroyAppData", "clearAppData", "clearAppDataWithPreservedCacheEntries", "destroyAppDataSnapshot", "destroyCeSnapshotsNotSpecified", "destroyPccData", "rmPackageDir", "cleanupInvalidPackageDirs", "moveCompleteApp", "moveAppDataPath", "copyAppDataPath", "migrateAppData", "restoreAppDataSnapshot", "onPrivateVolumeRemoved", "freeCache", "reconcileSdkData"]},
                    "keystore_maintenance_success": ["clearNamespace", "onUserRemoved", "onUserLskfRemoved", "onUserAdded", "migrateKeyNamespace", "initUserSuperKeys", "deleteAllKeys"],
                    "method_returns": {"UserDataPreparer.destroyUserDataLI": "void", "StorageManagerService.isCeStorageUnlocked": true, "StorageStatsService.isQuotaSupported": false},
                    "replace_call": {"RecoverySystem.rebootPromptAndWipeUserData": "Slog.w"}},
           "legacy_ref": "switcher/patches/guest_storage_guards.py; make-overlays.sh:38,68"},
  "anchors": [{"fact": "guest.class", "arg": ["system/framework/services.jar", "com.android.server.pm.UserDataPreparer"], "exists": true},
              {"fact": "guest.class", "arg": ["system/framework/services.jar", "com.android.server.usage.StorageStatsService"], "exists": true}],
  "postconditions": ["dropped IInstalld.destroyUserData", "dropped IVold.destroyUserStorage", "dropped IVold.prepareUserStorage",
                     "dropped AndroidKeyStoreMaintenance.clearNamespace", "GuardVerifier: no forbidden call site in SYSTEMSERVERCLASSPATH",
                     "EmptyTryRangeCheck: 0"],
  "on_anchor_missing": "refuse_session",
  "evidence": [{"run": 25, "summary": "UserDataPreparer.destroyUserData(0) through the host installd deleted One UI app data and photos"},
               {"run": 26, "summary": "a dropped call left an empty try range; ART VerifyError killed system_server (nop added)"},
               {"run": 27, "summary": "user 0 stuck RUNNING_LOCKED until isCeStorageUnlocked returned true"},
               {"run": 29, "summary": "Settings > About crash from quota query; isQuotaSupported false"}],
  "risk_if_wrong": "Missing: a guest can erase One UI's data again. Over-applied: guest storage features (quota stats, moving apps) do not work, which is harmless.",
  "tested_on": ["q8q / One UI 90000 / ColorOS 17 CP2A.260605.016"],
  "status": "stable"
 },
 {
  "id": "samsung.composer_restart",
  "title": "Hand the display to the guest",
  "description": "Restarts the Qualcomm display composer so the guest's SurfaceFlinger gets a fresh client, then keeps One UI's SurfaceFlinger down.",
  "category": "samsung", "toggle": "locked", "default": "auto",
  "applies_when": {"all": [{"fact": "host.init_service", "arg": "vendor.qti.hardware.display.composer", "exists": true}]},
  "stage": "inner",
  "impl": {"kind": "shell_step", "handler": "composer_restart",
           "args": {"service": "vendor.qti.hardware.display.composer", "settle_s": 2, "kill_host_sf_tries": 20},
           "legacy_ref": "guest_start.sh:172-189; host loop oneos_switch.sh:335"},
  "postconditions": ["no host surfaceflinger pid after restart"],
  "on_anchor_missing": "block_image",
  "evidence": [{"run": 13, "summary": "guest frames NO_RESOURCES, panel frozen on One UI's last frame (docs/coloros-on-fold.md fixed table)"},
               {"run": 20, "summary": "composer onrestart revived Samsung surfaceflinger, which answered guest calls (SecurityException in OPlusRefreshRateConfigs)"}],
  "risk_if_wrong": "Without it the panel stays on One UI's last frame and the watcher returns after 150 s. On a host with another composer service name (Exynos) the entry is hidden and the session refused until a pack adds that service.",
  "tested_on": ["q8q"],
  "status": "stable"
 },
 {
  "id": "coloros.saupwk_skip",
  "title": "Fast power key",
  "description": "Skips OPPO's power-key statistics, which wait 5 s for an OPPO service on every press.",
  "category": "guest", "toggle": "toggle", "default": "auto",
  "applies_when": {"all": [{"fact": "guest.family", "eq": "coloros"},
                           {"fact": "guest.string", "arg": ["system/lib64/lib_inputflingerEx.so", "persist.sys.saupwk_test"], "exists": true}]},
  "stage": "props",
  "impl": {"kind": "prop", "args": {"set": {"persist.sys.saupwk_test": "1"}, "memory_only": true, "only_if_host_lacks": true},
           "legacy_env": "ONEOS_GUEST_SAUPWK", "legacy_ref": "guest_props.sh:89-110"},
  "on_anchor_missing": "skip",
  "evidence": [{"run": 32, "summary": "power menu ~15 s late, EventHub slow reads up to 13.2 s, IOplusProject wait 25x"},
               {"run": 33, "summary": "on the phone: screenshot with buttons works"}],
  "risk_if_wrong": "Low. Only OPPO's Theia power statistics stop. The prop is removed on return.",
  "tested_on": ["q8q / ColorOS 17"],
  "status": "stable"
 },
 {
  "id": "fold.cover_touch_ic",
  "title": "Cover screen touch",
  "description": "Powers the cover screen's touch chip on fold and off on unfold, as One UI's input HAL would.",
  "category": "form", "toggle": "advanced", "default": "auto",
  "applies_when": {"all": [{"fact": "device.form", "eq": "fold"}, {"fact": "host.input", "arg": "flip", "exists": true},
                           {"fact": "host.input", "arg": "sec_touchscreen2", "exists": true},
                           {"fact": "host.sysfs", "arg": "/sys/class/sec/tsp2/enabled", "exists": true}]},
  "requires": ["fold.layout_file"],
  "stage": "activator",
  "impl": {"kind": "sysfs_monitor", "handler": "FoldMonitor",
           "args": {"tsp_by_input_name": {"cover": "sec_touchscreen2", "inner": "sec_touchscreen"},
                    "on_fold": ["cmd:set_fold_state,1", "enabled:2,0", "wait_backlight:panel1-backlight", "enabled:2,1"],
                    "on_unfold": ["cmd:set_fold_state,0", "enabled:1,0", "enabled:1,1", "inner_on_if_off"]},
           "legacy_env": "ONEOS_COVER_TSP", "legacy_ref": "oneos_switch.sh:636-735"},
  "device_values": {"q8q": {"cover_port": 148, "inner_port": 147}},
  "on_anchor_missing": "skip_warn",
  "evidence": [{"run": 31, "summary": "cover lit, sec_touchscreen2 mapped, no touches (getevent empty)"},
               {"run": 32, "summary": "tsp2 sequence written, inner IC never written; 7c35256 adds the inner-on recovery"}],
  "risk_if_wrong": "Writing Samsung touch sysfs on a device without the same IC protocol could leave a panel's touch off until reboot. Never applies to bar phones (S26 Ultra).",
  "tested_on": ["q8q"],
  "status": "experimental"
 }
]
```

## 6. Entries

Abbreviations in the tables: `mp` = `switcher/assets/guest_prepare.sh`,
`mi` = `guest_start.sh`, `sw` = `oneos_switch.sh`,
`gp` = `guest_props.sh`, `ret` = `return_to_oneui.sh`,
`mo` = `scripts/make-overlays.sh`, `p/` = `switcher/patches/`.
"Default" means the default on the F8U with ColorOS. §7 has the defaults for
other phones and guests.

### 6.1 SAFETY (all locked; the session is refused if any cannot be applied or verified)

| id | Title: description | Applies when | Today | App stage | Evidence | Risk if missing / wrong |
| --- | --- | --- | --- | --- | --- | --- |
| `safety.storage_guards` | Protect One UI's data: drop destroy/wipe/re-key calls (example above) | always | `p/guest_storage_guards.py`; `mo:38,68` | patch | run 25, 26, 27, 29 | data loss (run 25) |
| `safety.installd_abi_proxy` | Safe installd bridge: `OneOSInstalldProxy` sends only create/query/compile calls, with the host's codes; every other call throws | always (any guest has `IInstalld`) | `p/guest_installd_abi.py` (ALLOWED `:42-50`; `--callers` for oplus); `mo:41,74` | patch | runs 26-29 sent ColorOS codes (invalidateMounts arrived as isQuotaSupported, etc.) | guest calls reach different host methods |
| `safety.host_installd_table` | Read the phone's installd interface: name, code and signature per `IInstalld` method, from the HOST's `services.jar` | always; refuse if the host jar or `IInstalld$Stub` cannot be read | `scripts/host-installd-table.sh` -> `p/host_installd.txt` (static, F8U only) | probe (app start and every session): written to `$STAGE/host_installd.table` and read at runtime by `OneOSInstalldTable`, no re-patch (`DESIGN.md` §6) | needed by the ABI proxy | a stale table remaps to wrong host methods on another One UI build |
| `safety.vold_key_guard` | Keep One UI's encryption keys: drop `IVold` user-key calls | always | `p/guest_no_vold_keys.py`; `mo:31` | patch | LockSettings `setCeStorageProtection(0)` on the host vold | One UI's CE key protected with an unknown secret, so the phone would not unlock |
| `safety.weaver_guard` | Keep One UI's lock protectors: the guest never gets the weaver service | always (the HALs are shared) | `p/guest_no_weaver.py`; `mp` clears a pre-guard guest lock state | patch + stage | SyntheticPasswordManager enrolled user 0 in weaver slot 0, One UI's live slot on a never-reset phone (S25U, 0.3.2) | One UI cannot unlock user 0's CE storage after the return: Direct Boot lock screen with nothing to enter, phone reset |
| `safety.esim_guard` | Keep One UI's eSIM profiles: the guest gets no eSIM manager (LPA); the eSIM One UI left enabled still works | always (the eSIM chip is shared); `ONEOS_GUEST_ESIM_MANAGER=1` over adb keeps the LPA | `mp`: every `Euicc*` app folder but RROs and permission-only packages hidden (Pixel EuiccGoogle, EuiccSupportPixel-P23; Find X9 Ultra EuiccOplus) | stage | run 43: Pixel's EuiccGoogle opened the chip's ISD-R channel itself; the test Fold's SIM 2 is an eSIM | a guest factory reset with Erase eSIMs, Erase downloaded SIMs, Erase SIM, or a Find My Device remote erase deletes One UI's eSIM profiles |
| `safety.power_guards` | Guest cannot reboot the phone: AMS `commitChanges` dropped; ShutdownThread entry points only record `oneos.guest.powerctl`; PMS `sys.powerctl` renamed; RecoverySystem BCB/uncrypt fail | always | `p/guest_power_guards.py` (`:56-174`); host side `sw:929-938`, `ret:133-144` | patch + watcher | run 23: guest rebooted the phone; run 31: Restart in power menu | a guest reboot, recovery wipe command, or modem shutdown on the host |
| `safety.no_sysrq_crash` | No kernel crash from the guest: `doSysRq('c')` returns; `/proc/sysrq-trigger` bound to `/dev/null`, FATAL if that fails | always | `p/guest_no_sysrq_crash.py`; `mi:17-24` | patch + inner | ColorOS Theia panic path | kernel panic, reboot |
| `safety.guard_manifest` | Verified guarded build: hashes of the patched jars, checked before every session; the bind inode of `services.jar` checked | always | `mo:94-99` (`guards.txt`); `mp:26-39,159-163` | patch + stage | added after run 25 | unguarded jars could boot |
| `safety.dex_verify` | Patched code passes ART checks: no empty try ranges; plus `GuardVerifier` (§3) | always | `scripts/check-dex.py`; `mo:89-92` | patch | run 26 VerifyError killed system_server | boot loop, or a guard silently missing |
| `safety.data_bridges` | Host data redirected to the stage: every host `/data` tree a shared daemon can reach is bound to the staged copy and verified by inode | always | `switcher/assets/bridges.sh`; `mp:727-761`; `ret:63-83` | stage + return | run 25 | host daemons write into One UI's real `/data` |
| `safety.preflight_refusals` | Refuse unclean states: nothing mounted under stage `/data`; no leftover bridge; `bridges.sh` must list app, user, user_de, data, media | always | `mp:4-25`; `deploy-phone.sh:233-245` | stage | rm/chown through a stale mount would hit real data | data loss |
| `safety.guest_own_storage` | Guest gets its own storage: staged `/data/media`; host root (`/postinstall`) detached; host `/mnt` and `/storage` views removed (FATAL otherwise) | always | `mp:531-533`; `mi:25-59,72-82` | stage + inner | run 25 photos | guest reaches the owner's photos |
| `safety.guest_vold_owner` | Guest uses its own vold: servicemanager's `vold` must be the guest's pid before zygote | always | `mi:371-386` | inner | the guest framework must never get One UI's vold | key and storage operations on the host |
| `safety.host_prop_blocklist` | Never configure host daemons: guest props under `apexd`, `ro.boot`, `init`, `vold`, `sys.usb`, `selinux`, ... are not imported | always | `gp:52-59` | props | `apexd.config.compressed_apex` theory (kept as precaution) | host apexd or vold reconfigured |
| `safety.persist_snapshot` | One UI settings restored: snapshot `persist.*` before the session; delete or restore on return; clean up a session that never returned | always | `sw:67-70`; `gp:155-199`; `ret:130,202` | props + return | One UI booted with ColorOS settings | One UI behaviour changed after the session |
| `safety.host_apex_check` | One UI's APEXes intact: `/apex` mountinfo before and after must match; every `/data/apex` file must read back; refuse or reboot otherwise | always | `switcher/assets/check_host_apex.sh`; `sw:338-395`; `ret:156-190` | stage + return | SIGBUS boot loops after sessions | One UI boot loop |
| `safety.mount_propagation` | Container mounts stay private: rprivate rootfs, private `/data` bind, private before hiding APEX app dirs | always | `mp:108,763-769,1218-1228,1267-1273` | stage | host lost wifi APEX contents on return | host mounts changed |
| `safety.kill_by_namespace` | Stop only guest processes: kill by mount namespace or root device, never by name | always | `sw:528-540`; `ret:29-50` | watcher + return | `vold-failed` reboot when killed by name | host daemons killed |
| `safety.return_reboot` | Return by clean reboot: unmount exactly what `/proc/mounts` lists under the stage, then reboot; a guest shutdown request becomes a real power-off | always (in-place return = `dev`) | `ret:99-148` | return | in-place return damaged an APEX every time; ext4 panic once | host partitions unmounted through symlinks |
| `safety.auto_return` | Automatic way back: return after 150 s of black screen, 600 s without home, 30 s without zygote, or a guest power request | always; times `advanced` (not 0) | `sw:817-952` | watcher | a stuck guest means black screen and no network | phone stuck until a forced reboot |
| `safety.return_keys` | Hardware escape: hold Volume Up + Volume Down for 3 s to return | always | `sw:953-979`; `ret:13-14` | watcher | run 32: only Restart in ColorOS's menu ended a session | no escape when the UI hangs |
| `safety.no_clock_write` | Keep the phone's clock: seed `auto_time=0`, `auto_time_zone=0` | always | `mp:421-432` | stage | the guest set the clock to 1 Jan 2026 | host clock wrong |
| `safety.no_guest_ota` | Guest cannot update the phone: disable the guest's updater package | per family: `com.oplus.ota` (ColorOS); a list per OS in packs | `sw:594-595` | activator | the updater could reach the host `update_engine` | OTA applied to the real phone (see §9) |

### 6.2 CORE (needed for any guest)

| id | Title: description | Applies when | Default / toggle | Today | App stage | Evidence | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `core.image_import` | Import your OS image: .img/.zip/.7z/.gz to raw ext4, SHA-256, free-space check | always | on / locked | `deploy-phone.sh:271-291`; `MainActivity` 7zz | import | sparse/erofs not supported (`mp:84` mounts ext4) | an erofs GSI cannot mount: refuse with a message |
| `core.loop_mount` | Mount the image read-only on a loop device | always | on / locked | `mp:55-85` | stage | | |
| `core.namespace_pivot` | Run the guest in its own mount namespace (`unshare -m`, `pivot_root`) | always | on / locked | `sw:529`; `mi:5-15` | inner | | |
| `core.host_sys_dev_binds` | Share the kernel interfaces: rbind host `/sys`, `/dev`, binderfs | always | on / locked | `mp:91-113` | stage | system_server fork failed without cgroup2 | |
| `core.vendor_binds` | Use the phone's vendor HALs: bind `/vendor`, `/odm`, `/vendor_dlkm`, `/linkerconfig`, `/mnt` | always | on / locked | `mp:115-118,153` | stage | | |
| `core.apex_host_paths` | APEX paths the host reports: bind host `/system/apex` and `/system_ext/apex` (overlay mount point); apex tmpfs; bind non-payload APEXes except `*samsung*` | always | on / locked | `mp:119-152,1071-1088,1167-1191` | stage | PMS died on `com.android.compos.apex` | |
| `core.guest_apex_payloads` | Use the guest's own APEX modules: 19 payloads extracted from the image (erofs detected); versioned `@` dirs remounted | payload present in image | auto / locked | `mo:151-172`; `mp:1090-1165,1193-1208` | import + stage | host tethering signer mismatch | the wrong signer makes PMS abort |
| `core.hide_host_apex_apps` | Avoid duplicate system apps: hide host nfcservices/bt APEX `app` dirs when the guest has no payload for them | guest lacks that payload | auto / locked | `mp:1210-1228` | stage | Google vs OPPO signature clash | |
| `core.networkstack_group` | One signer for networking: keep host tethering; bind host `NetworkStackGoogle` and `CaptivePortalLoginGoogle`; hide guest CellBroadcastService | guest NetworkStack signer differs from host tethering | auto / locked | `mp:1147-1152,1230-1244` | stage | `map_netd_uid_permission_map` missing; shared-user mismatch | NetworkStatsService crash |
| `core.guest_classpath` | Guest's own class paths: `derive_classpath` plus `/data/oneos_genv.sh` for nsenter commands | always | on / locked | `mi:86-119` | inner | `OplusBitmapChecker` zygote abort | |
| `core.zygote_launcher` | Start the guest zygote: static launcher with sockets, passes the env; `-Xforcejitzygote` only with `ONEOS_GUEST_JIT_ZYGOTE=1` (default 1 for ColorOS, 0 otherwise: the image's own boot image, accepted by ART only when `/apex/apex-info-list.xml` lists the image's ART and i18n modules as factory) | always | on / locked | `switcher/native/zygote_launcher.c`; `mi:613-617` | inner | OneLineage hardcoded Lineage paths | |
| `core.stop_host_framework` | Pause One UI: stop zygote and surfaceflinger, kill system_server, keep them stopped in a loop | always | on / locked | `sw:290-336` | stage | One UI apps lost their APKs when stopped later | |
| `core.selinux_permissive` | Permissive SELinux for the session; enforcing again on return | always | on / locked | `sw:72-81`; `ret:232-234` | stage | MAC denials inside system_server | a phone left permissive if the return fails (a reboot resets it) |
| `core.rescue_party_off` | No RescueParty during the session: `persist.sys.disable_rescue`, `sys.rescue_boot_count=0` | always | on / locked | `sw:200-203` | stage | | removed again by restore-persist |
| `core.privapp_permissions_log` | Lenient privileged permissions: `ro.control_privapp_permissions=log` | always | on / locked | `sw:197-198` | stage | | |
| `core.guest_props_import` | Guest build properties: add guest `build.prop` keys the host lacks; remove them on return | always | on / locked | `sw:433-434`; `gp:25-121,139-154` | props | ColorOS gates on `ro.oplus.*` | |
| `core.data_stage_layout` | Guest data folder: staged `/data` tree, owners, modes, SELinux labels, realign to package uids | always | on / locked | `mp:372-374,521-597,675-725` | stage | `shell_data_file` denials; 353 packages refused by installd | |
| `core.package_cache_reset` | Fresh package cache each session: drop `package_cache`, `watchdog_timestamps` | always | on / locked | `mp:40-45` | stage | run 25 stale parse | |
| `core.settings_seed` | Usable first boot: `adb_enabled=1`, `device_provisioned=1`, `user_setup_complete=1` (edit existing XML only) | always | on / locked | `mp:385-433`; activator fallback `sw:590-593` | stage + activator | settings_global.xml non-numeric id; setup mode | settings file rejected (guarded by undo) |
| `core.seapp_rewrite` | App sandbox rules the phone knows: comment out seapp rules whose domain/type is missing from the host CIL types | guest seapp names types missing from host policy | auto / toggle (`ONEOS_GUEST_SEAPP`) | `mp:279-338` | probe + stage | run 31: 35 zygote aborts in 6 min | apps get generic domains (intended) |
| `core.runtime_dirs` | Missing system folders: bluedroid, wifi apexdata, SurfaceFlinger shader cache, audioserver | always | on / locked | `mp:524-529,599-605`; `mi:191-198,441` | stage + inner | bluetooth crash loop; wifi user store; run 32 shader cache | |
| `core.guest_surfaceflinger` | Guest display server: start guest SurfaceFlinger (stderr to `/dev/null`) | always | on / locked | `mi:199-207` | inner | `sf.log` hundreds of MB | |
| `core.aconfig_storage` | Feature flags: guest aconfig maps on a tmpfs `/metadata`, built after SF starts | always | on / locked | `mi:334-369` | inner | "Invalid feature flag" | before SF: composer rejects frames |
| `core.guest_wificond` | Wi-Fi scanner: stop host wificond, start the guest's | always | on / locked | `sw:506-515`; `mi:388-395` | stage + inner | "No scan results" | |
| `core.wifi_handover` | Keep Wi-Fi on: record host `wifi_on` and the supplicant service; the activator enables guest Wi-Fi | host Wi-Fi on | auto / toggle | `sw:280-288,791-810` | stage + activator | wifi drops when One UI stops | |
| `core.guest_media` | Guest media services: stop host mediaserver, extractor, metrics; start the guest's | always | on / advanced (`ONEOS_GUEST_MEDIA`) | `sw:439-477`; `mi:411-427` | stage + inner | overheating, codec spin | |
| `core.guest_audioserver` | Guest audio: stop host audioserver and restart the audio HAL; start the guest's; hand back to Samsung's after 60 s or 5 deaths | always | on / advanced (`ONEOS_GUEST_AUDIO`) | `sw:479-504`; `mi:429-473`; `ret:205-212` | stage + inner | run 29: host AudioFlinger refused app streams | no sound if it never registers (falls back) |
| `core.guest_idmap2d` | Overlays work: guest's own idmap2d; IdmapDaemon start/stop dropped | always | on / locked | `p/guest_own_idmap.py`; `mo:45`; `mi:599-608` | patch + inner | run 25: 9241 "failed to read IDMAP" | |
| `core.netd_restart` | DNS works: restart host netd for a fresh DnsResolver | always | on / locked | `mi:582-597` | inner | "Already called by AID_SYSTEM" | |
| `core.net_routes` | Internet works: private route table 4242 for the live interface | always | on / locked | `mp:975-1033`; host loop `sw:403-431` | stage + watcher | MOBILE VALIDATED but no traffic | |
| `core.bpf_net_permissions` | App network permission: host netd BPF maps (config map, uid permission map) | always | on / locked | `sw:222-225,775-783` | stage + activator | | writes host BPF maps (reset by reboot) |
| `core.app_storage_sweeper` | Newly installed apps start: create CE/DE and storage dirs per package every 10 s; code files read-only | always | on / locked | `mp:775-971,1035-1060`; `mi:570-579`; `sw:760-761` | stage + inner + activator | "Failed to mount /data_mirror" | Lineage-only parts split out in §6.6 |
| `core.guest_storage_views` | Guest storage views: `/data_mirror`, `/storage/emulated`, `/mnt/installer`, `/mnt/androidwritable` rebuilt over the guest data | always | on / locked | `mi:51-82`; `sw:789-790` | inner | | |
| `core.ui_activator` | Finish the boot: end bootanim, unlock user 0, go home, dismiss keyguard | always | on / locked | `sw:549-595` | activator | | |
| `core.stay_awake` | Screen stays on: stayon, `stay_on_while_plugged_in=7`, `screen_off_timeout` max | always | on / advanced | `sw:562-564` | activator | screen-off path untested; run 33 hung and rebooted after the screen was closed | OLED burn-in, battery; keep on until screen-off is fixed (§9) |
| `core.default_sound_props` | Guest's own default sounds: swap `ro.config.{ringtone,notification_sound,alarm_alert}` for the session | guest defines them and they differ from the host's | auto / toggle (`ONEOS_GUEST_RINGTONES`) | `gp:122-137` | props | host name `ACH_Galaxy_Bells.ogg` not in the guest | none (restored on return) |
| `core.watchdog_feeder` | Hardware watchdog feeder: writes `/dev/watchdog` every 2 s if nothing holds it | today always | on / advanced | `mp:49-53` (OneLineage heritage) | stage | none recorded | if the loop stalls, the hardware watchdog may reset the phone; needs review |

### 6.3 SAMSUNG host

| id | Title: description | Applies when | Default / toggle | Today | App stage | Evidence | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `samsung.composer_restart` | Hand the display to the guest (example above) | `vendor.qti.hardware.display.composer` init service | auto / locked | `mi:172-189` | inner | NO_RESOURCES frozen panel | |
| `samsung.force_gpu_composition` | GPU composition: SurfaceFlinger transaction 1008 (HW overlays off) | Samsung SDM composer | ColorOS: on; other guests (since run 44): off, and forced by `guest_start.sh` when the composer rejects more than 30 frames in the first 30 s / advanced (`ONEOS_GUEST_HWC=1` or `0` overrides) | `mi:209-231`; `mp:507-509` | inner | runs 31/32: about 45 GPU missed frames/s; run 43 (Pixel, no Qualcomm composer client): about 2/s | frame drops; off may bring rejected frames back (the fallback catches them) |
| `samsung.skip_host_apex_services` | Skip Samsung system services: no `com.samsung.*` APEX services in the guest SystemServer | the host has `com.samsung.*` APEXes | auto / locked | `p/skip_host_apex_services.py`; `mo:33`; `mp:1180-1184` | patch | lifeguard ClassLoader abort | system_server abort |
| `samsung.ims_in_guest` | VoLTE in the guest: this One UI's `com.sec.imsservice`, libraries and native libs as a system_ext layer, One UI's framework.jar as its `secimshttpclient` compat library, carrier config override to bind it | host has the set; `ONEOS_GUEST_SEC_IMS=1` | proposed off / advanced (not booted yet) | `gp` "Samsung's IMS stack in the guest"; `sw` activator | stage + activator | calls on 3G, none on VoLTE-only carriers | docs/samsung-ims-in-guest.md; needs the guest-side package-manager change |
| `pixel.camera_abi` | A Pixel guest's camera binder calls with One UI's transaction codes: `ICameraService` 23-26 to 24-27, `ICameraDeviceUser` 13-28 one higher, the listener's foreign 9 ignored, `CameraCompatibilityInfo` five fields | Pixel (AOSP) image, host table `p/host_camera.txt` | auto / locked (untested) | `p/pixel_camera_abi.py`, `scripts/patch-framework-camera.sh`; `mo` Pixel step; `gp` guard + bind | patch | S25/S25U Pixel sessions: getCameraCharacteristics NPE, flashlight tile dead, listener misparse | docs/pixel-guest.md "What differs" |
| `samsung.softdog_feed` | Samsung's software watchdog fed for the session: "1" to `/dev/softdog` after One UI's framework stops and every 2 s from the feeder (plus the `/dev/watchdog` "V" of 0.4.19) | host has `/dev/softdog` (Exynos) | auto / locked | `sw` after the stop; `gp` feeder | stage | S26+ 4cad07e6: panic "Software Watchdog Timer expired 100s" 100 s after the guest's system_server died; `/dev/watchdog` was watchdogd's | docs/exynos-hosts.md |
| `samsung.qcom_platform` | A Qualcomm-built guest on an Exynos phone: `ro.boot.hardware=qcom` for the session, restored on return | guest ships `libqti_performance.so`, host `ro.boot.hardware` not qcom | auto / locked | `gp` guest_props.sh | stage | S26+ 4cad07e6: zygote never loaded the perf library, system_server died on `Performance.native_perf_get_feedback_extn` | docs/exynos-hosts.md |
| `samsung.ims_keepalive` | Keep SMS working: start imsd, wait for voice registration, keepalive loop | host has `imsd` | auto / locked | `sw:83-107,171-195` | stage | SMS 20-40 min late | |
| `samsung.call_audio_sim` | Call audio on the right SIM: set `g_call_sim_slot` (0x01, 0x02, 0x10 swap) from the guest's per-SIM call state | dual SIM; Samsung QTI audio HAL; guest audioserver on | on / toggle (`ONEOS_GUEST_CALL_SIM`) | `mi:475-541` (AudioFlinger transaction 18) | inner | run 32: silent SIM-2 calls; run 33 owner: SIM 2 still silent, no ringback, SIM 1 heard | transaction 18 is this guest build's `setParameters`; on another build it may be a different method. Replace with in-guest `AudioSystem.setParameters` (§9). Experimental. |
| `samsung.boot_backlight` [F8U] | Light the panel during boot: `panel0-backlight` 928 (about 135 nits) while the boot animation runs | per-device value in pack | auto / toggle | `mi:312-332` | inner | dark boot animation | wrong scale gives the wrong brightness |
| `samsung.launcher_db_backup` | Protect One UI Home layout: snapshot `com.sec.android.app.launcher` databases; restore only when no bridge is left | host has that package | auto / locked | `sw:204-208`; `ret:85-97` | stage + return | OneLineage heritage | stale restore (bridges make it largely redundant) |

### 6.4 FORM (fold / flip / bar)

| id | Title: description | Applies when | Default / toggle | Today | App stage | Evidence | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `fold.hide_host_layout` [CF] | Hide Samsung's fold layout file from the guest (copy of displayconfig without it) | form fold/flip AND guest has `DeviceStateToLayoutMapExtImpl` | auto / dev (`ONEOS_KEEP_FOLD_LAYOUT=1`) | `mi:129-153` | inner | DisplayManagerService NPE at bootstrap | boot abort if not applied on the Fold |
| `fold.layout_file` [CF][F8U] | Cover and inner screen layout: state 0 = cover, state 3 = inner, from guest SF ports (147 inner, 148 cover). Guests without `oplus-services.jar` (run 44): AOSP states 0 and 3 (rear display) = cover, 1 and 2 = inner, as yogi's own file; 4 and 5 left out | form fold AND `rt.sf_ports` has both | auto / toggle (`ONEOS_GUEST_FOLD=off`) | `mi:233-282` | inner | run 30 inner only; run 31 cover works | wrong ports: no layout, inner only (the script falls back) |
| `fold.cover_off_without_layout` | Turn the cover off without a layout: disable non-zero internal displays | form fold AND no layout | auto / locked | `sw:616-621` | activator | cover mirrored, touches lost | |
| `fold.cover_touch_ic` [F8U] | Cover screen touch (example above) | fold + `tsp2` + `sec_touchscreen2` + `flip` | auto / advanced (`ONEOS_COVER_TSP`) | `sw:636-735` | activator | runs 31, 32 | wrong sysfs writes on other ICs |
| `fold.inner_touch_ic_recover` | Inner touch after a folded start: switch `tsp1` on only if One UI left it off | as above | auto / advanced | `sw:666-678,697-702` | activator | seen before run 32: tsp1 0 | |
| `fold.continue_on_fold` [CF] | Keep apps on the cover when folding: `continue_using_apps_when_folded=1` unless the user chose 2 | fold + layout + ColorOS | auto / toggle (`ONEOS_GUEST_FOLD_CONTINUE`) | `sw:603-615` | activator | run 31: fold ended on a locked cover | |
| `fold.guest_density` [F8U] | Inner panel density: a forced density (`wm density N -d 0`) so the short side is at least 840 dp: 420 on the 2256 px panel (859x954 dp), only at 90% of the real dpi or more, only while display 0 is the inner panel and `display_density_forced` is unset; the cover keeps the base 480 | form fold AND fold layout AND not ColorOS (no `oplus-services.jar`) | auto / toggle (`ONEOS_GUEST_DENSITY`: `off`, `auto` or a dpi) | `oneos_switch.sh` UI activator | activator | run 43: Samsung's 480 from the shared `ro.sf.lcd_density`, sw752dp, the setup wizard without its w840dp two-pane layouts | text smaller than before; a folded first start skips it until the next session; a later folded start gives the cover 420 too until the first lid event (WMS applies `display_density_forced` to display 0 at boot) |
| `fold.display_features` | Fold line for apps: Settings.Global `display_features` = the inner panel's middle line, `fold-[1128,0,1128,2504]-flat` | form fold AND fold layout AND not ColorOS | auto / advanced (`ONEOS_GUEST_POSTURE=live` drops `-flat`) | `oneos_switch.sh` UI activator | activator | run 43: WM Extensions rejected yogi's `fold-[1038,0,1038,2152]` ("must have full height"), no FoldingFeature | with `live`, false tabletop layouts while the hinge reads HALF_OPENED (run 41) |
| `fold.device_states_oneos` | AOSP fold properties: own `device_state_configuration.xml` (OUTER/INNER_PRIMARY, wake on unfold) | fold, opt-in | off / advanced (`ONEOS_GUEST_DEVICE_STATES=oneos`) | `mp:621-673` | stage | experiment; vendor file used since run 30 | fold handling changes |

There are no Flip-specific entries yet. The Flip's cover screen, ports and
touch ICs are unknown, so every `fold.*` entry is hidden for `device.form=flip`.

### 6.5 GUEST: ColorOS / OPPO (all [CF] unless noted; hidden when `guest.family != coloros`)

| id | Title: description | Applies when (plus family) | Default / toggle | Today | App stage | Evidence | Risk if wrongly applied |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `coloros.display_mode_fallback` | Show the display without OPPO HALs: LocalDisplayAdapter uses the active mode when the SF mode specs are null | anchor string `"Desired display mode specs from SurfaceFlinger are null"` + exact smali shape | auto / locked | `p/display_mode_specs.py`; `mo:21-28` | patch | "Timeout waiting for default display" | shape-pinned (`.line 252`, registers): block the image if the shape differs |
| `coloros.wait_for_service` | No endless waits for OPPO services: `waitForService` becomes `checkService` (keeps installd, cotaservice); services.jar DefragService only | `oplus-services.jar` | auto / locked | `p/oplus_wait_for_service.py`; `mo:47,62` | patch | OplusEngineerFwService watchdog | null binder callers (null-guarded) |
| `coloros.boot_hangs` | Fix OPPO boot stalls: GameGpuControlPanel QSPM wait, `ctl.start dumpenvironment`, zygote_ocomp fallback | anchors in `oplus-services.jar` | auto / locked | `p/oplus_boot_hangs.py`; `mo:65` | patch | runs 24, 28 | |
| `coloros.no_alt_zygote_prop` | Same as above, by prop: `persist.sys.oplus.aotcrash_controller_enabled=false` | | auto / locked | `sw:249-252` | stage | run 28: 62 s app-start stall | |
| `coloros.sf_skip_qti_composer` | Plain composer path: binary patch `cbz` to `b` at 0x470bc8 in guest SF | `guest.sha1(system/bin/surfaceflinger)` prefix `9896c0cba131` | auto / dev (`ONEOS_STOCK_SF=1`) | `mo:101-122`; `mp:164-171` | pack (descriptor) + patch | black panel, BAD_VALUE | only this exact binary; skipped otherwise, and the panel may stay black |
| `coloros.backlight_curve` [F8U] | Correct brightness on Samsung's panel: ColorOS level to nits to One UI float (`OneOSPanelBacklight` table) | `LocalDisplayDeviceExtImpl.getBacklightFromBrightness` AND a pack table for `device.vendor_device` | auto / toggle | `p/samsung_backlight_curve.py`, `p/OneOSPanelBacklight.smali`; `mo:77` | patch (table from pack) | run 28: 31 nits minimum, jumpy | F8U table on another panel: too bright or too dim. OFF on S26U until measured. |
| `coloros.brightness_defaults` [F8U] | Sensible start brightness: level 4570 if below 222; one-time reset (`.oneos_curve2`) | with `coloros.backlight_curve` | auto / toggle | `sw:622-628` | activator | run 28 | |
| `coloros.multibits_dimming` | Smooth brightness slider: feature `multibits_dimming_support` | | auto / toggle | `mp:238` | stage | run 28: jumpy slider | |
| `coloros.form_feature` | Device type for ColorOS: `type.fold` (fold), `type.tablet`, or none (phone) | from `device.form`: fold gives fold; bar gives phone; flip unknown (phone) | auto / advanced (`ONEOS_GUEST_FORM`) | `mp:235-248` | stage | runs 28 (phone), 29 (tablet), 30+ (fold) | `fold` on a bar phone: foldable layouts; `tablet`: off-screen grid |
| `coloros.unfold_portrait` [F8U] | Right-edge back gesture on a portrait inner panel: `feature_unfold_width_small_high` | form fold AND inner panel portrait at rotation 0 | auto / toggle (`ONEOS_GUEST_UNFOLD_PORTRAIT`) | `mp:241-243` | stage | run 31: back zone off screen | gesture zones off on a landscape panel |
| `coloros.compact_window` | Foldable layout in Wallpapers & styles: `windowmode.compact` (also OPPO compact window mode in WMS) | form fold | auto / toggle (`ONEOS_GUEST_COMPACT_WINDOW`) | `mp:244-246` | stage | run 32: header 2419 px | compat-window behaviour on a phone |
| `coloros.wallpapers_fold_grid` | Wallpapers card grid 8x2 (RRO in `/oem/overlay`) | form fold AND anchor `personal_card_fold_large_layout` `columnCount=4` | auto / toggle (`ONEOS_GUEST_WALLPAPER_GRID`) | `switcher/overlays/wallpapers_fold_grid`; `mo:124-149`; `mp:262-278` | pack (our RRO) + stage | run 30 | wrong layout if the anchor differs (the check prevents it) |
| `coloros.radio_5g` | 5G in ColorOS: `radio.support_5g` | `host.nr` | auto / toggle (`ONEOS_GUEST_5G`) | `mp:249-250` | stage | run 29: LTE only | |
| `coloros.radio_dual_nr` | 5G on both SIMs: `radio.support_dual_nr` | `host.nr` AND `host.dual_sim` | auto / toggle (`ONEOS_GUEST_DUAL_5G`) | `mp:251-253` | stage | run 32; run 33 on the phone: 5G offered on SIM 2, but SIM 2 never shows 5G in the status bar | experimental |
| `coloros.wifi_region_cn` | Wi-Fi connect dialog completes: `connectivity.region_CN` | the image's own `my_region` features declare `region_CN` (domestic build) | auto / toggle (`ONEOS_GUEST_WIFI_CN`) | `mp:255` | stage | run 32: network removed on Back | turns on other CN Wi-Fi paths in a global build |
| `coloros.vrr_oti_off` [F8U] | Stable 120 Hz: touch-idle off (`oplus_vrr_config.json`, `oti false`) | `my_product/etc/oplus_vrr_config.json` with `touch_idle` | auto / toggle (`ONEOS_GUEST_OTI=1` keeps OTI) | `mp:436-453`; `sw:568-570` | stage + activator | run 29: 240/60 Hz, heat | |
| `coloros.haptic_ringtones` | ColorOS ringtones: stage `haptic_ringtone/output<Hz>HZ` into guest `/data/oplus/multimedia` | dir present in `my_product` | auto / toggle (`ONEOS_GUEST_RINGTONES`) | `mp:455-502` | stage | runs 30, 31: no ringtones | |
| `coloros.blur` | Glass effects: `ro.surface_flinger.supports_background_blur=1` for the session (host value 0 on the F8U) | ColorOS (others: off by default, toggle) | auto / toggle (`ONEOS_GUEST_BLUR`) | `gp:65-88` | props | run 31: flat dialogs | GPU load |
| `coloros.saupwk_skip` | Fast power key (example above) | | auto / toggle (`ONEOS_GUEST_SAUPWK`) | `gp:89-110` | props | runs 32, 33 | |
| `coloros.preapps_lib_mode` | Weather and themes load: `/data/preapps-lib` 0771 system | `/my_stock/del-app` present | auto / locked | `mp:607-619` | stage | run 32: Weather crash | |
| `coloros.list_daemons` | Sound without delays: start `mmlistservice` and `atlasservice` | binaries present | auto / locked | `mi:397-409` | inner | run 29: 25 s call tone | |
| `coloros.cotad_defrag` | OPPO system daemons: start `cotad`, `oplus_defrag` | binaries present | auto / locked | `mi:543-550` | inner | cotaservice waits | |
| `coloros.mediaserver64` | 64-bit media server: prefer `mediaserver64` over the wrapper | file present | auto / locked | `mi:416-421` | inner | `media.player` missing | |
| `coloros.nav_mode_default` | Gesture navigation: `hide_navigationbar_enable=3` only if unset; never force AOSP overlays | | auto / toggle | `sw:571-581` | activator | run 28: 3-button mode with no buttons | |
| `coloros.launcher_card_seed` | Launcher start: seed `launcher_support_card_no_padding=1` | | auto / locked | `mp:429-432` | stage | runs 23-25 onCreate hang | |
| `coloros.log_silence` | Quieter logs: OPPO tags SILENT (PerformanceManager, ProjectManager, SchedAssist, ...) | | auto / toggle | `sw:268-278`; `ret:192-195` | stage | run 32: about 36k lines per 10 min | hides useful errors |
| `coloros.verbose_logs` | Full ColorOS logs: `persist.sys.assert.panic=true` | | on in test builds / toggle | `sw:245-248` | stage | launcher logs only with it | |

### 6.6 GUEST: LineageOS / AOSP heritage (from OneLineage)

These entries come from OneLineage (`switcher/README.md`). They still run for
every guest today; in the app they must be limited to the families listed.

| id | Title: description | Applies when | Default / toggle | Today | App stage | Risk if applied to ColorOS |
| --- | --- | --- | --- | --- | --- | --- |
| `lineage.gesture_nav_idmap` | Gesture navigation overlay: `idmap2 --ignore-overlayable` for `NavigationBarModeGestural` | `lineage`/`aosp` AND overlay present | auto / toggle | `mi:552-568` | inner | conflicts with ColorOS's own nav (run 28) |
| `lineage.default_sms_role` | Keep Messaging as SMS app: role and `sms_default_application=com.android.messaging` | `lineage`/`aosp` AND package present | auto / toggle | `mp:844-851` (in `fix_app_dirs.sh`) | activator | ColorOS's messages app may be a different package: check run logs for "[fix_app_dirs] restored default SMS app" |
| `lineage.launcher3_refresh` | Show new apps: force-stop `com.android.launcher3` on package changes | launcher package from the family profile (ColorOS: `com.android.launcher`) | auto / locked | `mp:1047-1053` | inner | no effect on ColorOS (wrong package) |
| `lineage.prepared_pkg_dirs` | Pre-create app folders for core packages (list includes `org.lineageos.lineagesettings`, `com.wewaffles.onelineage`) and chown latin IME to uid 10109 | package list per family | auto / locked | `mp:535-574,597` | stage | uid 10109 is hardcoded: on another image it may be a different app's uid |
| `lineage.legacy_binaries` | OneLineage patched files: `PermissionController_patched.apk`, `framework_patched.jar`, `framework-res_patched.apk`, `libaudio*_patched.so` (bound if present) | never (not built by `mo`) | hidden | `mp:339-368,1246-1265` | n/a | arbitrary unverified binaries over the guest |
| `lineage.microg` | Install microG (flag file) | `lineage`, user opt-in | off / toggle | `sw:763-773` | activator | |

### 6.7 OPTIONAL (quality)

| id | Title: description | Applies when | Default / toggle | Today | App stage | Evidence / risk |
| --- | --- | --- | --- | --- | --- | --- |
| `opt.gap_splash` | OneOS screen instead of black: switcher splash; One UI's SF frozen (SIGSTOP), released by inner or after 20 s | the app's `SplashActivity` | on / toggle (`ONEOS_GAP_SPLASH`) | `sw:45-65,293-310,542-547`; `mi:155-170` | stage + inner | run 32: 31.6 s black. Risk: a frozen SF if the inner script dies (20 s safety net) |
| `opt.refresh_rate_120` | 120 Hz: `peak_refresh_rate` and `min_refresh_rate` 120 | panel supports 120 | on / toggle | `sw:566-567` | activator | min 120 costs battery |
| `opt.audio_low_latency_props` | Audio stability props: offload off, deep buffer off | always (OneLineage) | on / advanced | `sw:210-220` | stage | deep buffer hang |
| `opt.log_silence` | Quieter logs (generic tags: CaptureStateTracker, Parcel, ResourcesManager, MediaCodecList, AString, BOOTPROF, GED) | always | on / toggle | `sw:275-278` | stage | run 23: about 30k lines/s |
| `opt.guest_locale` | Keep the guest's language between sessions | always | on / toggle | `sw:253-255`; `gp:175-181` | stage + return | |
| `opt.notification_assistant_off` | Disable the AOSP notification assistant (`android.ext.services`) | always (heritage, reason undocumented) | on / advanced | `sw:582` | activator | unknown, review |
| `opt.adb_keys` | Same adb authorization in the guest: copy host `adb_keys` | always | on / toggle | `mp:511-516` | stage | |
| `opt.su_bridge` | Root inside the guest: copy `ksud`/`su` to a tmpfs `/system/xbin` | `root.kind` | proposed off / advanced | `mp:1062-1069` | stage | the session flow uses nsenter from the host; gives guest apps root |
| `opt.bootanimation_clear` | Keep the guest's own boot animation | always | on / locked | `sw:517-520` | stage | |
| `opt.comfort_view_bridge` | Comfort View in a Pixel guest: Settings' `cv_enabled` and `cv_preferred_intensity` become a desaturation matrix (saturation 1 - 0.6 x intensity) at DisplayTransformManager level 175, the Night Light path | anchor `ColorDisplayService.setUp` ("setUp: currentUser="); skipped with a warning without it; not built for ColorOS images (`oplus-services.jar`) | on / locked (built into `services_patched.jar`) | `p/comfort_view_bridge.py`, `p/OneOSComfortView.smali`; `mo` | patch | run 43: the switch only wrote settings (no PixelDisplayService, no Pixel display HAL). Risk: a verifier failure would stop ColorDisplayService; the call is at method entry in its own try/catch (a helper class that fails to load is caught there) and every helper path catches Throwable |

### 6.8 DIAGNOSTIC

| id | Title: description | Default / toggle | Today | App stage | Notes |
| --- | --- | --- | --- | --- | --- |
| `diag.logcat_capture` | Session log: logcat -b all, 32 MB x 25, the boot kept in head/ (hard links), previous session kept | on / advanced (`ONEOS_LOGCAT`) | `sw:25-43` | stage | feeds the failure bundle; off means reports have no logs |
| `diag.log_bundle` | Share logs: after a failed session or reboot, pack the capture, `*.log`, `diag_*`, inner log, `call_audio.log`, activator log | on / locked (sharing is the user's choice) | `scripts/pull-run-logs.sh` | return + next app start | redact before sharing (§9) |
| `diag.host_snapshot` | Host device states, layouts, port associations, touch nodes | on / locked | `sw:345-370` | stage | |
| `diag.display_rounds` | Display and state dumps at 20, 40, 90 s and final; since run 44 also thermal and CPU/GPU clocks every round, and from 40 s, in the background: density and fold line, composition, dexopt, frame pacing, Comfort View, phone process and RIL props (identifiers left out), call audio route | on / advanced | `sw:845-911` | watcher | heavy (debuggerd, getevent 15 s) |
| `diag.wifi_verbose` | Verbose Wi-Fi logging in the guest; otherwise switched off on every boot (run 43: run 42's setting put debug text under every network) | off / dev (`ONEOS_WIFI_VERBOSE=1`) | `oneos_switch.sh` UI activator | activator | the debug text shows BSSIDs |
| `diag.fold_test` | Per lid event: state, layout, screenshot, 10 s cover touches | fold: on / advanced | `sw:631-735` | activator | screenshots are personal data |
| `diag.wallpaper_probe` [CF] | Wallpapers page view tree and screenshot | proposed off (one-off) / dev (`ONEOS_WALLPAPER_PROBE`) | `sw:736-759` | activator | investigation finished in run 33 |
| `diag.screen_record` | Record the session (90 s segments x 6) | off / toggle (`ONEOS_RECORD`) | `mp:504-506`; `mi:284-303`; `ret:5-15` | inner | consent needed |
| `diag.net_apex_watch` | Network and APEX watch logs every 10 s | on / locked | `sw:403-431` | watcher | |
| `diag.boot_failures` | List of failed system services | on / locked | `mp:890-900` | activator | |
| `diag.adb_watchdog` | Keep adb alive (restart adbd, re-add adb to the USB config) | on / advanced | `sw:109-169`; `ret:20-22` | watcher | |
| `diag.prepare_only` | Dry run: prepare, check and return without starting the guest | off / advanced (`ONEOS_PREPARE_ONLY`) | `sw:396-401` | stage | good first test on a new phone |
| `diag.session_max` | End a session after N s | off / dev (`ONEOS_SESSION_MAX`) | `sw:831-835,943-946` | watcher | |

Not shipped in the app:
- `oneos_tunnel.sh`: a developer reverse tunnel with a hardcoded server (`ONEOS_TUNNEL_*`).
- `ONEOS_RETURN_MODE=inplace`: it damaged One UI's APEXes in every session.
- `ONEOS_RETURN_MAX=0`, `ONEOS_RETURN_KEYS=0`, `ONEOS_KEEP_FOLD_LAYOUT=1`, `ONEOS_STOCK_SF=1`: debug builds only.

## 7. All entries: defaults per target

- **L** = on and locked
- **on**/**off** = default, user may toggle
- **A** = on when its predicate holds
- **-** = hidden (does not apply)
- **R** = refuse the session if it cannot be applied

The S26 Ultra columns are predictions from the predicates; nothing has been tested there.

| id | cat | F8U ColorOS | S26U ColorOS | S26U Lineage |
| --- | --- | --- | --- | --- |
| safety.storage_guards | safety | L/R | L/R | L/R |
| safety.installd_abi_proxy | safety | L/R | L/R | L/R |
| safety.host_installd_table | safety | L/R | L/R | L/R |
| safety.vold_key_guard | safety | L/R | L/R | L/R |
| safety.power_guards | safety | L/R | L/R | L/R |
| safety.no_sysrq_crash | safety | L/R | L/R | L/R |
| safety.guard_manifest | safety | L/R | L/R | L/R |
| safety.dex_verify | safety | L/R | L/R | L/R |
| safety.data_bridges | safety | L/R | L/R | L/R |
| safety.preflight_refusals | safety | L | L | L |
| safety.guest_own_storage | safety | L/R | L/R | L/R |
| safety.guest_vold_owner | safety | L/R | L/R | L/R |
| safety.host_prop_blocklist | safety | L | L | L |
| safety.persist_snapshot | safety | L | L | L |
| safety.host_apex_check | safety | L/R | L/R | L/R |
| safety.mount_propagation | safety | L | L | L |
| safety.kill_by_namespace | safety | L | L | L |
| safety.return_reboot | safety | L | L | L |
| safety.auto_return | safety | L | L | L |
| safety.return_keys | safety | L | L | L |
| safety.no_clock_write | safety | L | L | L |
| safety.no_guest_ota | safety | L | L | L (needs a Lineage package list) |
| core.* (all 37 in 6.2) | core | as 6.2 | as 6.2 | as 6.2 |
| samsung.composer_restart | samsung | L | A (verify service name) | A |
| samsung.force_gpu_composition | samsung | on | on | off (forced when the composer rejects frames) |
| samsung.skip_host_apex_services | samsung | L | L | L |
| samsung.ims_keepalive | samsung | L | L | L |
| samsung.call_audio_sim | samsung | on (experimental) | A (dual SIM) | off until reimplemented (§9) |
| samsung.boot_backlight | samsung | A | - until a pack value exists | - until a pack value exists |
| samsung.launcher_db_backup | samsung | L | L | L |
| fold.hide_host_layout [CF] | form | A | - | - |
| fold.layout_file [CF] | form | A | - | - |
| fold.cover_off_without_layout | form | A | - | - |
| fold.cover_touch_ic | form | A | - | - |
| fold.inner_touch_ic_recover | form | A | - | - |
| fold.continue_on_fold [CF] | form | A | - | - |
| fold.guest_density | form | A | - | - |
| fold.display_features | form | A | - | - |
| fold.device_states_oneos | form | off | - | - |
| coloros.display_mode_fallback | guest | L | A/block if the anchor differs | - |
| coloros.wait_for_service | guest | L | A | - |
| coloros.boot_hangs | guest | L | A | - |
| coloros.no_alt_zygote_prop | guest | L | A | - |
| coloros.sf_skip_qti_composer | guest | A (sha match) | - unless the sha matches | - |
| coloros.backlight_curve [F8U] | guest | A | **off** until an S26U table | - |
| coloros.brightness_defaults [F8U] | guest | A | **off** | - |
| coloros.multibits_dimming | guest | A | A | - |
| coloros.form_feature | guest | fold | **phone** | - |
| coloros.unfold_portrait [CF] | guest | A | **-** | - |
| coloros.compact_window [CF] | guest | A | **-** | - |
| coloros.wallpapers_fold_grid [CF] | guest | A | **-** | - |
| coloros.radio_5g | guest | A | A | - |
| coloros.radio_dual_nr | guest | A (experimental) | A (experimental) | - |
| coloros.wifi_region_cn | guest | A | A only for a CN image | - |
| coloros.vrr_oti_off | guest | A | A (verify panel modes) | - |
| coloros.haptic_ringtones | guest | A | A | - |
| coloros.blur | guest | A | A | off (toggle) |
| coloros.saupwk_skip | guest | A | A | - |
| coloros.preapps_lib_mode | guest | A | A | - |
| coloros.list_daemons | guest | A | A | - |
| coloros.cotad_defrag | guest | A | A | - |
| coloros.mediaserver64 | guest | A | A | - |
| coloros.nav_mode_default | guest | A | A | - |
| coloros.launcher_card_seed | guest | A | A | - |
| coloros.log_silence | guest | on | on | - |
| coloros.verbose_logs | guest | on | on | - |
| lineage.gesture_nav_idmap | guest | **-** (runs today) | - | A |
| lineage.default_sms_role | guest | **-** (runs today) | - | A |
| lineage.launcher3_refresh | guest | **-** | - | A |
| lineage.prepared_pkg_dirs | guest | family list | family list | A |
| lineage.legacy_binaries | guest | - | - | - |
| lineage.microg | guest | - | - | off |
| opt.* (10) | optional | as 6.7 | as 6.7 | as 6.7 |
| diag.* (13) | diagnostic | as 6.8 | as 6.8 (fold_test, wallpaper_probe hidden) | as 6.8 (fold_test, wallpaper_probe hidden) |

Must default OFF or hidden on an S26 Ultra or for non-ColorOS guests (ColorOS-on-Fold specific):
- `fold.hide_host_layout`, `fold.layout_file`, `fold.continue_on_fold`
- `fold.cover_touch_ic`, `fold.inner_touch_ic_recover`, `fold.cover_off_without_layout`
- `coloros.unfold_portrait`, `coloros.compact_window`, `coloros.wallpapers_fold_grid`
- `coloros.form_feature=fold`
- `coloros.backlight_curve`, `coloros.brightness_defaults`, `samsung.boot_backlight` (F8U panel values)
- `coloros.sf_skip_qti_composer` (exact binary)
- `diag.wallpaper_probe`
- every `coloros.*` entry for a non-ColorOS guest

Meanwhile the `lineage.*` entries, which run for ColorOS today, should stop doing so.

## 8. Environment variables mapped to catalog ids

| Variable (default) | Entry | App exposure |
| --- | --- | --- |
| `ONEOS_LOGCAT` (1) | diag.logcat_capture | advanced |
| `ONEOS_GAP_SPLASH` (1) | opt.gap_splash | toggle |
| `ONEOS_PREPARE_ONLY` (0) | diag.prepare_only | advanced |
| `ONEOS_GUEST_MEDIA` (1) | core.guest_media | advanced |
| `ONEOS_GUEST_AUDIO` (1) | core.guest_audioserver | advanced |
| `ONEOS_GUEST_CALL_SIM` (1) | samsung.call_audio_sim | toggle |
| `ONEOS_GUEST_FOLD_CONTINUE` (1) | fold.continue_on_fold | toggle |
| `ONEOS_COVER_TSP` (1) | fold.cover_touch_ic, fold.inner_touch_ic_recover | advanced |
| `ONEOS_WALLPAPER_PROBE` (1) | diag.wallpaper_probe | dev |
| `ONEOS_RETURN_BLACK` (150), `ONEOS_RETURN_MAX` (600) | safety.auto_return | advanced, bounded (no 0) |
| `ONEOS_SESSION_MAX` (0) | diag.session_max | dev |
| `ONEOS_RETURN_KEYS` (1) | safety.return_keys | dev |
| `ONEOS_RETURN_MODE` (reboot) | safety.return_reboot | dev |
| `ONEOS_STOCK_SF` (0) | coloros.sf_skip_qti_composer | dev |
| `ONEOS_GUEST_FORM` (fold) | coloros.form_feature | advanced, default from `device.form` |
| `ONEOS_GUEST_UNFOLD_PORTRAIT` (1) | coloros.unfold_portrait | toggle |
| `ONEOS_GUEST_COMPACT_WINDOW` (1) | coloros.compact_window | toggle |
| `ONEOS_GUEST_5G` (1), `ONEOS_GUEST_DUAL_5G` (1) | coloros.radio_5g, coloros.radio_dual_nr | toggle |
| `ONEOS_GUEST_MOBILE_DATA` (1) | coloros.mobile_data_follow (new since run 34: guest mobile data follows One UI's switch on the guest's data SIM, `mp:435-449`) | toggle |
| `ONEOS_GAP_FAST` (1) | opt.gap_fast (new since run 34: the gap splash waits for the composer instead of fixed sleeps, `mp:528-530`, `mi:187`) | advanced |
| `ONEOS_GUEST_WIFI_CN` (1) | coloros.wifi_region_cn | toggle |
| `ONEOS_GUEST_WALLPAPER_GRID` (1) | coloros.wallpapers_fold_grid | toggle |
| `ONEOS_GUEST_SEAPP` (1) | core.seapp_rewrite | advanced |
| `ONEOS_GUEST_OTI` (0) | coloros.vrr_oti_off (inverted) | toggle |
| `ONEOS_GUEST_A11Y_SHORTCUT` (0) | coloros.a11y_shortcut_off (inverted; new since run 34: empties the factory TalkBack target of ColorOS's volume-key accessibility shortcut, which shares the return chord, and turns TalkBack off when the shortcut left it on) | toggle |
| `ONEOS_GUEST_RINGTONES` (1) | coloros.haptic_ringtones, core.default_sound_props | toggle |
| `ONEOS_RECORD` (0) | diag.screen_record | toggle |
| `ONEOS_GUEST_HWC` (0 for ColorOS, 1 otherwise) | samsung.force_gpu_composition (inverted) | advanced |
| `ONEOS_GUEST_JIT_ZYGOTE` (1 for ColorOS, 0 otherwise) | core.zygote_launcher (`-Xforcejitzygote`; not in session.env) | dev |
| `ONEOS_GUEST_DENSITY` (auto) | fold.guest_density | toggle |
| `ONEOS_GUEST_POSTURE` (flat) | fold.display_features | advanced |
| `ONEOS_WIFI_VERBOSE` (0) | diag.wifi_verbose | dev |
| `ONEOS_GUEST_DEVICE_STATES` (vendor) | fold.device_states_oneos | advanced |
| `ONEOS_GUEST_BLUR` (1) | coloros.blur | toggle |
| `ONEOS_GUEST_SAUPWK` (1) | coloros.saupwk_skip | toggle |
| `ONEOS_KEEP_FOLD_LAYOUT` (0) | fold.hide_host_layout (inverted) | dev |
| `ONEOS_GUEST_FOLD` (layout) | fold.layout_file | toggle |
| `ONEOS_TUNNEL_SERVER`, `ONEOS_TUNNEL_PORT` | none (oneos_tunnel.sh) | not shipped |

## 9. Open risks and gaps

1. **Guard coverage beyond two jars.** Today only `services.jar` and `oplus-services.jar` are patched. Any other `SYSTEMSERVERCLASSPATH` jar (APEX service jars, another OEM's `*-services.jar`) could still call the host installd, vold or keystore. `GuardVerifier` must scan them all and refuse on an unexpected caller. Native guest daemons (`cotad`, `oplus_defrag`, mmlist/atlas, guest vold, wificond) are not covered by Java guards at all; only the bridges protect against them.
2. **Host installd table is per host build.** `p/host_installd.txt` was taken from the F8U. On every other phone, and after every One UI update, it must be derived on the phone before patching. If it cannot be derived, the session is refused. Status: `DESIGN.md` §6 replaces the build-time table with a runtime one (the app writes it on each phone, `OneOSInstalldTable` reads it in the guest, fail closed).
3. **Anchor drift.** Several patchers depend on exact smali shapes: `display_mode_specs.py` uses `.line 252` and fixed registers; `guest_power_guards.py` expects exactly 2 `sys.powerctl` writes; `oplus_boot_hangs.py` uses exact method headers. Safety anchors that are missing mean refuse. Boot anchors that are missing mean "image not supported yet, send a report". A fix pack may add alternative anchors.
4. **Python to Kotlin equivalence.** Golden test on the build server: run the Python patchers and the Kotlin `PatchEngine` on the run-33 image, then diff the baksmali output of every changed class. New classes go into a dex with method headroom, because `classes.dex` is at the 64K limit (`guest_installd_abi.py:215-216`).
5. **`samsung.call_audio_sim`.** Its transaction code 18 is guest-build-specific; a wrong code calls another AudioFlinger method. Replace it with a small in-guest `app_process` helper that calls `AudioSystem.setParameters`. Run 33: SIM 2 is still silent (no ringback), while SIM 1 audio works. Status: SIM 2 call audio works since run 34 (the keeper's quoting bug had kept the fix from running); the build-specific code 18 remains a porting risk for other guest builds.
6. **Screen-off hang (run 33).** After the screen was closed, the phone hung and rebooted; there are no logs yet. Keep `core.stay_awake` on. Collect the logs with `diag.log_bundle` on the next start; check the activator's stay-on settings, the fold monitor, and `core.watchdog_feeder` (which opens `/dev/watchdog`). Status: resolved; it was the Power + Volume Down screenshot crash (OPPO `getTpInfo` ran `ctl.start gettpinfo`), fixed in `oplus_boot_hangs.py` (run 34).
7. **OTA and clock are guarded by settings and package lists only.** A guest updater other than `com.oplus.ota` could reach the host `update_engine`, and a user can turn automatic time back on. Proposed new safety entries: `safety.no_update_engine`, which blocks UpdateEngine binder use in the guest framework, and `safety.no_set_time`.
8. **KernelSU allowlist.** OneHyper restores `/data/adb/ksu/.allowlist`, because the guest's PackageManager writing `packages.list` dropped Shell from it (`docs/coloros-on-fold.md`). OneOS has no such entry. Proposed `safety.root_allowlist_restore`, per `root.kind`.
9. **Fix-pack trust.** Packs can enable entries that write sysfs (`fold.cover_touch_ic`) or patch binaries. They need a signature check, a minimum app version, and the rule that safety entries can only be tightened (§3.3).
10. **Log bundle privacy.** Logcat, screenshots (`fold_N.png`, `diag_*/shot_*.png`), recordings and `telephony.registry` dumps hold personal data such as phone numbers and network names. The share screen must list what is included, and screenshots and recordings should be excluded by default.
11. **Exynos or other composers.** `samsung.composer_restart` and `samsung.force_gpu_composition` assume Qualcomm SDM. Every non-Qualcomm host is refused until a profile exists.
