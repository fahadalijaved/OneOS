# Exynos phones as hosts (Galaxy S26+, Z Flip7, S23)

Findings from the S26+ bundle 4cad07e6 (SM-S947B, s5e9965, One UI 8.5, app 0.4.19,
ColorOS X9U IN; 2026-10-26). Two separate faults, one chained into the other.

## 1. Black screen: the guest's system_server dies on a Qualcomm native

`FATAL EXCEPTION IN SYSTEM PROCESS: O_dfd_16` at 10:19:38, 30 s into the guest:
`UnsatisfiedLinkError: No implementation found for int
com.qualcomm.qti.Performance.native_perf_get_feedback_extn(...)`, thrown from
`Performance$SendGameLaunchBroadcast.run` on an OPLUS dispatch thread
(`com.oplus.dispatch.OThread`), where nothing catches it. The same session logged
over 1,000 "No implementation found" lines for every `Performance` native
(`perf_get_prop`, `perf_hint`, `perf_lock_rel`, `perf_event`); those callers
survive, the OThread one does not.

Why: `QPerformance.jar` declares the natives, nothing in it loads the library.
`ZygoteInit.preloadSharedLibraries` (framework.jar) loads `qti_performance` only
when `Build.isQcomPlatform()` is true, and `Build.IS_QCOM_PLATFORM` is
`ro.boot.hardware` starting with "qcom". On an Exynos phone that is Samsung's
value, so the guest's zygote never loads `libqti_performance.so`, though the
image ships it with every dependency in `system_ext/lib64`. `QPerformance.jar`
is in the guest's boot image (`boot-QPerformance.vdex`), so it is not a jar to
patch. Only `perfGetFeedbackExtn` has an escape (`ro.soc.model` = `vsoc_arm64`);
the other 16 native callers have none.

Fix (`guest_props.sh`): when the guest ships that library and the phone's
`ro.boot.hardware` is not Qualcomm's, `ro.boot.hardware=qcom` for the session,
recorded in `guest_props.overridden` and restored on the return like the S23's
ABI lists. The guest is a Qualcomm build; "qcom" is the only configuration it was
ever run in. What else `IS_QCOM_PLATFORM` turns on in the guest on an Exynos
phone is for the next bundle to show.

## 2. Kernel panic: Samsung's software watchdog, 100 s after the guest died

`/proc/extra`: `PANIC: Software Watchdog Timer expired 100s`, at uptime 766 s,
10:21:26; the guest's system_server had died at 10:19:38 and nothing fed the
softdog after about 10:19:46. The 09:41 session had the same system_server death
and no panic: its auto-return restarted One UI's framework within 90 s.

0.4.19 assumed the softdog is `/dev/watchdog` (it wrote "V" there from the
switch and from `oneos_wdog_feeder.sh`). On the S26+ every such write was
refused: `/dev/watchdog` is the hardware watchdog, opened and fed by init's
`watchdogd` (pid 670) the whole time (`watchdog_feeder.log`: "held by:
670:watchdogd" at every session). Samsung's software watchdog is a second node,
`/dev/softdog`, which One UI's system_server feeds. The community module the
friend has installed ("Watchdog Feeder" v3.4, a fork of Pealeap/Watchdog-Feeder
for OneLineage) writes "1" to `/dev/softdog` every 5 s, but only after
`vendor.hotboot.rom=1`, which OneOS never sets, so it was idle.

Fix: `oneos_switch.sh` writes "1" to `/dev/softdog` right after One UI's
framework stops; `guest_prepare.sh`'s feeder writes "1" to it every 2 s for the
rest of the session (on top of its `/dev/watchdog` attempt) and logs both nodes'
holders. A phone without the node sees no change.

## Still to check on the next S26+ run

- The guest with `IS_QCOM_PLATFORM` true: anything else it tries against
  Qualcomm HALs that are not there.
- `watchdog_feeder.log` should show `/dev/softdog written` from the first
  seconds; a refusal there means the node is held exclusively and needs the
  holder named.
- The friend's module and ours both feeding is fine; the module can stay.

## 0.4.22: the softdog through Samsung's init

The S26+ (756047eb) and the Z Flip7 (aaeea148), both on 0.4.20 with ColorOS IN,
panicked again: "Software Watchdog Timer expired 100s", about 100 s after One
UI's system_server stopped (the S26+ log ends at 17:28:22, the stop was at
17:26:33). Neither phone has `/dev/softdog`: the switch never logged it and the
feeder never wrote it; `/dev/watchdog` stayed busy (init's `watchdogd`). The
guests themselves were fine: no system_server crash, and on the S26+ no missing
Qualcomm native (`ro.boot.hardware=qcom` works). The kernel's `[SOFTDOG]` line
names the current system_server's `watchdog` thread (the guest's: tid 3329 of
3107, 14817 of 14382); ColorOS's framework never opens a watchdog device, so that
is only the panic report.

Samsung's init owns the softdog (`/system/etc/init/init.sysfw.rc`, seen on the Z
Fold8 Ultra's One UI 9): `softdog init`, `softdog settimeout 100 # including
enable`, `softdog chmod 0660`, `softdog chown root system` on init;
`softdog disable` on `init.svc.zygote=stopped`, on `persist.vendor.softdog=off`,
in charger mode and on an orange verified-boot state (which also sets the
property). One UI's system_server (`WatchdogSoftdog`) kicks it unless the
property is off. Both phones restarted `resetreason` right after the switch
stopped zygote, so the zygote trigger ran, and the softdog still expired: most
likely One UI's system_server kicked it once more before it died.

0.4.22: `oneos_switch.sh` sets `persist.vendor.softdog=off` once One UI's
system_server is gone, on a phone where the switch's "V" could not reach
`/dev/watchdog` (the Z Fold8 Ultra's softdog is `/dev/watchdog`, closed with "V"
as before, so nothing changes there). The persist snapshot taken before the
switch deletes the property again on the return before One UI's zygote starts,
and `recover` does after a hard reset. The feeder no longer writes
`/dev/softdog`; it kicks only watchdogs `/sys/class/watchdog` lists as active
software ones, and logs every watchdog node, the property and each kernel
watchdog's state and time left.

## Still to check on the next Exynos run

- `watchdog_feeder.log`: the nodes, `persist.vendor.softdog=off`, and whether a
  software watchdog stays active after it.
- The switch log: "Softdog: persist.vendor.softdog off for the session".
- If it still panics, the time left per watchdog shows which one ran out.
