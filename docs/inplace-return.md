# Returning to One UI without a reboot

`return_to_oneui.sh` normally reboots. Its in-place mode restarts One UI's
framework on the same kernel boot, and it can only do that if every daemon One
UI cannot restart still owns its servicemanager names. This page covers the
return sequence, and how the guest's vold gets a name of its own (run 44) so
that One UI's vold keeps its names.

## The return sequence

First worked on the phone in run 48 (2026-10-25: tap to user 0 unlocked in about
50 s, same boot). Since app 0.4.7 every app session asks for it
(`ONEOS_RETURN_MODE=inplace` in session.env); without it the return reboots. Every step is logged to `return_inplace.log` in the stage,
and every check that fails ends in the failsafe: restore One UI's persist props,
`sync`, `sys.powerctl reboot,oneos-inplace-failsafe`, then `busybox reboot -f`.

**Baseline at the switch.** `oneos_switch.sh` runs `return_to_oneui.sh baseline`
after the persist snapshot and before `setenforce 0`. It writes to
`inplace_base/`: the boot id, `getprop`, the SELinux mode, a sysfs-only
description of every One UI APEX device (mounts, dm tables, loops and their
backing files), `ip rule`, the pids of `vold`, `android.system.vold.IVold/default`,
keystore2, installd and gatekeeper, f2fs `gc_urgent`, and a kernel-log marker.

**Chosen only when** busybox and resetprop are there, the baseline is complete,
the boot id is the same, vold is in the baseline, nothing of the stage is still
mounted and the guest asked for no shutdown. Otherwise the reboot return.

1. **Guest gone.** The guest is killed in up to 5 passes, with the session's
   helpers (the zygote stop loop, net_watch, app_storage_loop.sh). The stage is
   unmounted. A wakelock keeps the phone awake until One UI is up.
2. **Gate A, part 1 (busybox only).** Every `/proc/*/mountinfo` is free of the
   stage. The stage's own loops are detached through private device nodes
   made from sysfs maj:min (`/dev/oneos_nodes`), never through
   `/dev/block` names, which guest_prepare.sh re-made. One UI's APEX devices
   must match the baseline exactly; each loop must still answer
   `LOOP_GET_STATUS64`; each dm device must not be suspended and must read
   end to end with `dd iflag=direct` (below the page cache, through
   dm-verity); the kernel log since the marker must have no error, corrupt,
   verity or capacity-change line on those devices.
   Run 45: Android's bootstrap mount namespace (early vendor daemons, kernel
   threads) kept its own copy of the stage mounts (`$S/rootfs`, `rootfs/proc`,
   `rootfs/sys`), so this check rebooted. Before it, the return now unmounts
   stage mount points in every other namespace that still has them (deepest
   first, only below the stage) and logs the namespace and process.
3. **Gate A, part 2.** `vold` and the other names have the pids from the
   baseline, and `init.svc_debug_pid.vold` is unchanged.
4. **Before anything starts:** no process left in the guest's mount namespace
   or on its root device; One UI's zygote and system_server not started.
5. **Props and SELinux.** `guest_props.sh remove`; the props the switch
   set (privapp permissions, rescue counts, audio offload, bootanim, `log.tag.*`,
   changed `debug.*`) back to their baseline values in memory; One UI's
   persist props from the snapshot; RescueParty off in memory until the end.
   SELinux back to the baseline mode.
6. **Leftovers.** One UI's idmap2d and supplicant stopped (both start again on
   request), ip rule 14999 and table 4242 removed, `restorecon` on the loop
   nodes, f2fs `gc_urgent` back.
7. **Display.** The composer restarted (it still held the guest's
   surfaceflinger as its client); One UI's surfaceflinger and boot animation.
8. **Audio and the rest of zygote's onrestart list.** audioserver and the
   audio HAL restarted, waiting for `media.audio_policy`; cameraserver, media,
   wificond; gnss and update_engine if they ran at the switch.
9. **Gate B.** No guest process; `vold`, SurfaceFlinger, the audio services and
   installd registered; vold, keystore2, servicemanager, hwservicemanager,
   logd, lmkd and installd running if they were. Other `init.svc.*`
   differences are logged only.
10. **Framework.** `vdc volume abort_fuse`, then `ctl.restart netd`, whose
    onrestart starts zygote (`ctl.start zygote` after 10 s otherwise).
11. **Gate C.** system_server must start within 60 s and keep its pid until
    user 0 is `RUNNING_UNLOCKED` (or One UI Home runs) plus 30 s, within 180 s.
    Any death reboots at once: Samsung's bootchecker reboots after a few anyway,
    and RescueParty would reset One UI's settings.
12. **Done.** RescueParty back to its stored value, `check_host_apex.sh
    after-inplace` reads the modules through their filesystems, ip rule
    differences are logged, the session's logcat stops 2 minutes later, and
    `return_inplace.done` is written.

### Return splash

The guest app first draws its return screen. The root renderer then posts its
own frame and holds it before the guest framework is stopped. Holding it only
after killing system_server/zygote can preserve a frame they already blanked.
The return wakelock also begins before teardown. While the guest compositor
is removed and Gates A and the property restoration run, `boot_status.sh`
holds that last frame in the vendor composer. It does not keep any guest
process or mount alive, and does not start One UI ahead of the safety checks.
This interval shows a static "Returning to One UI" / "Restoring One UI" frame;
live verbose events resume when One UI's SurfaceFlinger is available.

The hold requires a ready renderer, a validated composer pid/start time, and
an independently armed recovery process. The normal display restart and both
reboot paths release it. The recovery also releases it after 180 seconds if
the return shell stalls; a recycled pid is never signalled. Unsupported
composer names retain the original display teardown.

The outgoing guest's `service.bootanim.exit` cannot dismiss the root layer.
Completion is accepted only after the new framework starts, or from that
framework's display-ready event. `scripts/test-boot-status.py` covers this
distinction, the normal release and the independent recovery timeout. A real
guest-to-One-UI cycle is still required to validate panel behaviour.

**Known limits.**

- A kernel restart during Gate A (dm-verity in restart mode, a hung task) comes
  before step 5. One UI would boot with the guest's persist props until
  `guest_props.sh recover`, which fixes only props that are clearly the guest's.
- One UI's own `init.zygote64.rc` onrestart list is not on the server; steps
  7-10 follow AOSP's. Read `/system/etc/init/hw/init.zygote64.rc` once.
- The touch panel state and leftover `getevent` readers are not checked.
- Not checked on the phone yet: whether Samsung kernels prefix kernel-log lines
  with `[cpu: comm: pid]` (the device match needs a boundary on its left, so a
  `kworker/7:3` no longer counts as loop 7:3).

**Tested** on a fake phone (`~/oneos-notes/2026-10-24/inplace_harness.sh`):
16 scenarios. The normal case returns in place; changed APEX devices, a dead
loop, a failed read, a verity line, vold taken or gone, a stage mount (also
behind an unreadable mountinfo), a dying system_server and a missing composer
end in the failsafe; another boot id and the default mode reboot; a kworker
error line, a late unlock and a netd without onrestart still return in place.

## Run 44: what to look for (return)

`return_inplace.log`, in order: "In-place return (baseline: oneos-baseline …)",
"stage loop devices detached: N", the two "Gate A:" lines, "props: restored",
"display: …", "audio, camera, media, Wi-Fi and GNSS services restarted",
"init services not as at the switch: …", "Gate B: …", "One UI's zygote
started (running)", "One UI's system_server N", "user 0 unlocked after Ns",
"One UI restored in place (Enforcing)". Any "FAILSAFE:" line names the check.

## Why vold

- One UI's vold is `reboot_on_failure reboot,vold-failed` in its init.rc. It
  cannot be restarted, only rebooted.
- The guest shares One UI's servicemanager. Up to run 43 the guest vold
  registered `vold` and `android.system.vold.IVold/default` there over One UI's
  vold (run 43 `takeover_inner.log:42`; `all.log:286335`
  "VendorVoldNativeService::try_start() completed OK"). One UI's vold kept
  running without either name and could not take them back.
- A One UI framework restarted after that waits forever: StorageManagerService
  retries "vold not found".
- So Gate A of the in-place return compares `vold` and
  `android.system.vold.IVold/default` with their pids at the switch, and
  `init.svc_debug_pid.vold` with its value at the switch. Any difference ends in
  the reboot fallback.

## The guest vold as "gvld"

`scripts/make-overlays.sh` patches two builds: Pixel 17 (yogi), and since
2026-10-25 ColorOS 17 CP2A.260605.016, whose vold and service.incremental.so
the Find N6 and Find X9 Ultra images share. It checks three files of each by
sha256, and checks the old bytes before writing anything. Any other image is
not patched: the build logs "not a build this was written against" and the
guest vold keeps `vold`, which means no return without a reboot.

Pixel 17 (yogi):

| File (sha256 prefix) | Offset | Old | New | Effect |
|---|---|---|---|---|
| `/system/bin/vold` (`5ecfb2f6`) | 0xde12 | `vold` | `gvld` | `VoldNativeService::start()` registers `gvld` (adrp 0x65100 + add 0x65104). The other 9 references are log tags in forked children. |
| same | 0x64ac8 | `b3 06 00 36` (`tbz w19, #0, 0x64b9c`) | `35 00 00 14` (`b 0x64b9c`) | `VendorVoldNativeService::try_start` always takes its "not declared" path and returns OK: the guest never registers `android.system.vold.IVold/default` |
| `/system/lib64/service.incremental.so` (`3add0c25`) | 0x64129 | `vold` | `gvld` | Both IncrementalService lookups (adr 0xc09ec; adrp 0xc32ec + add 0xc32f0, `String16(s, 4)`) |
| `/system/apex/com.google.android.crashrecovery.apex` (`fc82e88e`) | | | pinned, not changed | Its RescueParty is the guest's one call left that reaches One UI's `vold` (see below) |

ColorOS 17 CP2A.260605.016 (same changes, found from each binary's
`.gnu_debugdata` symbols with the NDK's llvm-objdump):

| File (sha256 prefix) | Offset | Old | New | Effect |
|---|---|---|---|---|
| `/system/bin/vold` (`3df4d13b`) | 0x104e7 | `vold` | `gvld` | `VoldNativeService::start()` (0x79140) registers `gvld` (adrp 0x79174 + add 0x79178); 9 log tags besides |
| same | 0x78b64 | `b3 06 00 36` (`tbz w19, #0, 0x78c38`) | `35 00 00 14` (`b 0x78c38`) | `VendorVoldNativeService::try_start` (0x78afc), as on Pixel |
| `/system/lib64/service.incremental.so` (`43ae8309`) | 0x6536c | `vold` | `gvld` | Both IncrementalService lookups (adr 0xc005c; adrp 0xc2710 + add 0xc2714, `String16(s, 4)`) |
| `/system/apex/com.android.crashrecovery.apex` (`a8396ec6`) | | | pinned, not changed | AOSP's RescueParty, as on Pixel |

On ColorOS, oplus-services.jar has a fourth lookup,
`OplusStorageManagerFeature.connectVold` (OPPO's own IVold calls), which
`guest_own_vold.py --oplus` moves to `gvld` too.

- In all four binaries the file offset equals the vaddr in every LOAD segment.
- No relocation and no data pointer refers to either string.
- The vendor name is skipped, not renamed: it is a VINTF name, and
  servicemanager refuses any such name the manifest does not declare.
- The name must stay 4 characters (service.incremental.so passes the length).
- `gvld` has no `/` and no `.`, so it needs no VINTF declaration.
- The logcat tag stays `vold` (it comes from argv[0]).

The full analysis is in the notes for 2026-10-24 (inplace2_voldName).

**services.jar.** `switcher/patches/guest_own_vold.py` changes its three
`vold` lookups to `gvld`:

- `StorageManagerService.connectVold`
- `StorageManagerService$StorageManagerInternalImpl.prepareStorageDirs`
- `StatsPullAtomService.getIVoldService`

The build fails unless exactly these three change and no other `vold` string is
left. make-overlays.sh runs this patch only when it built `vold_patched`.

**Built together, bound together.** `guards.txt` lists `vold_patched` and
`service.incremental_patched.so` beside `services_patched.jar`, under the line
`# guest vold name: gvld`. Every script that reads the set checks all three:

- `scripts/deploy-phone.sh` refuses a set whose files do not match its
  guards.txt, or whose guards.txt lists only one of the two binaries.
- `oneos_switch.sh` refuses both at the preflight, before One UI's framework
  stops. With the app, all three must also be listed in files.sha256.
- `guest_prepare.sh` checks the hashes again. It binds `vold_patched` over the
  guest's `/system/bin/vold` and the library over
  `/system/lib64/service.incremental.so`, checks that both binds are in place,
  and writes `gvld` to the guest's `/data/oneos_vold_name`.

A set without the two files (the ColorOS sets built before 2026-10-25) binds
neither, and leaves no `oneos_vold_name`.

## Guest code that reached "vold"

The scan covered:

- **Dex strings:** the image's `/system`, `system_ext` and `product` framework
  folders; every APK in their app and priv-app folders; the APEX payloads
  make-overlays.sh stages; GmsCore in the gmssystem payload.
- **Native code:** `/system/bin`, `/system/lib64`, `system_ext/bin`,
  `system_ext/lib64` and `product/lib64`.

| Where | What | Now |
|---|---|---|
| services.jar | the three lookups above | `gvld` |
| service.incremental.so (guest system_server, incfs v2 in run 43) | two lookups | `gvld` |
| framework.jar `RecoverySystem.rebootPromptAndWipeUserData` | `checkService("vold")`, then `needsCheckpoint()`, and `abortChanges()` (which reboots the phone) while One UI is in an update checkpoint | Not patched (boot class path). The two callers are guarded, see below. |
| services.jar `UserDataPreparer` | calls it after a failed first boot | A log line since `guest_storage_guards.py`. `guest_own_vold.py` fails the build if any call is left in services.jar. |
| crashrecovery APEX `RescueParty` (factory reset level, `RescueParty$1`) | calls it | Every path to it passes `RescueParty.isDisabled()`, which is false with `persist.sys.enable_rescue` and true with `persist.sys.disable_rescue` (set by `oneos_switch.sh` [1/6]). `guest_start.sh` refuses a gvld guest otherwise. The APEX is pinned. |
| `/system/bin/apexd`, `gsid`, `vdc`, `incident_helper` | contain `vold` | The container runs none of them. |
| `libdumputils.so` | `/system/bin/vold` | A process path for stack dumps, not a service name. |
| services.jar `DynamicSystemService` | `waitForService("gsiservice")` | servicemanager would start One UI's lazy gsid, which uses One UI's vold. This happens only on a DSU install request, and it is One UI's own program acting on One UI's vold, as before run 44. |

No app, priv-app or GmsCore dex has `vold` or `rebootPromptAndWipeUserData`.

The scan did not cover:

- One UI's own APEX modules that the guest keeps (everything without a staged
  payload: statsd, media, uwb, virt, scheduling and the others). Their jars
  run in the guest system_server.
- the vendor partition, whose libraries some guest processes load.

Up to run 43, a "vold" lookup from such code in a guest process reached the
guest vold. Now it would reach One UI's. Two things limit this:

- Module jars are built against their module SDK, which has no `IVold`. Their
  one way to vold is the system API `RecoverySystem.rebootPromptAndWipeUserData`
  above.
- Vendor code uses `android.system.vold.IVold/default`. Its only method is
  `registerCheckpointListener` (the vold binary has no other).

To check the first on the phone (read-only, as root):
`for j in /apex/*/javalib/*.jar; do unzip -p "$j" | grep -qa rebootPromptAndWipeUserData && echo "$j"; done`.
Only the crashrecovery module should be listed. The guest runs the Pixel's
copy of that module, not One UI's.

## What guest_start.sh checks

When `/data/oneos_vold_name` says `gvld`, `guest_start.sh` checks the
following before it starts the guest vold. Each check that fails is FATAL, and
the guest is not started.

- One UI's vold owns `vold`. Its pid is `init.svc_debug_pid.vold`.
- One UI's vold also owns `android.system.vold.IVold/default`, when that name
  is registered.
- `/system/bin/vold`, `/system/lib64/service.incremental.so` and
  `/system/framework/services.jar` contain `gvld`. A services.jar that still
  looked up `vold` would give the guest StorageManagerService One UI's vold,
  and its `IVold.reset()`.
- SELinux is not enforcing.
- RescueParty is off: `persist.sys.disable_rescue` is true and
  `persist.sys.enable_rescue` is not.

After starting it:

- It waits up to 10 s until servicemanager's `gvld` is the guest vold's pid.
- It checks that One UI's names are unchanged.

It checks both again right before zygote. The vendor name would come a moment
after `gvld`, so a guest vold that registered it would be caught there.
Without `oneos_vold_name` the guest vold waits for `vold`, as up to run 43.

The session watcher writes `diag_20`, `diag_40` and `diag_90/vold_names.txt`.
Each file has the pid of `vold`, `android.system.vold.IVold/default` and `gvld`
at that point, and `init.svc_debug_pid.vold`.

## Depends on the permissive session

`gvld` has no entry in `service_contexts`, so servicemanager's
`Access::canAdd` and `canFind` label it with the catch-all line,
`* u:object_r:default_android_service:s0`. That line is in the image's
`plat_service_contexts`, next to `vold` (`vold_service`) and
`android.system.vold.IVold/default` (`fwk_vold_service`).

AOSP policy forbids adding a `default_android_service`. system_server has no
find permission on it either. Both are therefore allowed only because the
session is permissive:

- `oneos_switch.sh` runs `setenforce 0` before the guest starts, and the guest
  processes run in the root manager's domain (`u:r:ksu:s0`).
- The in-place return sets enforcing again only after the guest vold is gone
  ([4/4]); the reboot return reboots.
- `guest_start.sh` refuses to start a gvld guest while SELinux is enforcing.

Two things need the same care:

- **An enforcing session** would need a real policy entry for `gvld` (a
  `service_contexts` line and allow rules), which One UI's policy cannot get
  without patching it.
- **The catch-all line** must exist in One UI's `plat_service_contexts`. Without
  it the label lookup fails and servicemanager refuses `gvld` even in permissive
  mode. It is AOSP standard. Check it once on the phone, read-only:
  `grep '^\*' /system/etc/selinux/plat_service_contexts`.

## Run 44: what to look for

- **make-overlays.sh:** "built .../vold_patched (registers gvld, not
  android.system.vold.IVold/default)", the three `-> "gvld"` lines, "services.jar: no
  RecoverySystem.rebootPromptAndWipeUserData call left", and guards.txt with
  the `# guest vold name: gvld` line.
- **takeover_app.log (guest_prepare.sh):** "Guarded overlays verified:
  services_patched.jar vold_patched service.incremental_patched.so", "Bound
  vold_patched -> .../rootfs/system/bin/vold", "Bound
  service.incremental_patched.so -> ...", and "Guest vold: registers gvld; One
  UI's vold keeps vold and android.system.vold.IVold/default".
- **takeover_inner.log (guest_start.sh):**
  - "One UI's vold: pid N, android.system.vold.IVold/default: N; SELinux
    Permissive; the guest's will register gvld"
  - "servicemanager's gvld is the guest's (M)"
  - "One UI's vold (N) still has vold and android.system.vold.IVold/default (N)"
  - "Before zygote: gvld is the guest vold's (M); vold One UI's (N),
    android.system.vold.IVold/default N"

  Any "FATAL" there names the check that failed.
- **all.log:** from the guest vold M, `D vold : Service for
  VendorVoldNativeService (android.system.vold.IVold/default) not declared.`
  then "VendorVoldNativeService::try_start() completed OK". The guest
  StorageManagerService should log no "vold" connection errors, and the guest
  IncrementalService should come up as in run 43 (incfs v2). One UI's vold N
  keeps running all session.
- **diag_*/vold_names.txt:** `vold: N`, `android.system.vold.IVold/default: N`
  (or "Can't find service" if One UI never registered it), `gvld: M` and
  `init.svc_debug_pid.vold: N`.
