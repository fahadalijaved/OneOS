# Retaining the initialized Samsung authority: control feasibility

**Retaining the existing Samsung server could avoid constructing a second
security graph, but current OneOS 0.4.57 deliberately tears that server down.**
This comparison identifies the coordinated source cuts a retention experiment
would need. It does not select an architecture or change the METHOD_REVIEW
baseline. No retainer/hook, launcher, process exemption, mount operation,
watchdog change or guest producer replacement is implemented. `selected=false`.
No device state or OEM execution was inspected. Native/boot/quiescence cards
remain preserved, and the parent bridge remains paused.

Inputs are the same 14 immutable upstream files plus the previously pinned
return script, commit `1f2c2aa45ab8a7dc81384f6b67962d1e9cf7fefe`, and two
small captured Samsung init files. Their exact hashes, source ranges and slice
hashes are in `inventory/retained-authority-control.json`. The init files were
read from the existing local mounted tar only; no whole-OS extraction/re-pull.
Commands below describe source, not observed execution.

## Current control path conflicts

| Actual source cut | Effect relevant to retention |
| --- | --- |
| `oneos_switch.sh:971/979` | Requests stop of primary and conditional secondary zygote. |
| `:995..999` | SIGKILLs name-selected `app_process64`, `zygote_exec`, zygotes and `system_server`. |
| `:1011` | Keeper requests zygote stops every 0.2 seconds; deleting one kill is insufficient. |
| `:1017/1027/1047`; `guest_prepare.sh:186..237` | Magic-close writes, conditional softdog-off property, then recurring feeder assume the original server has gone. |
| `:1087`; `guest_prepare.sh:3240..3258` | Preparation runs before guest unshare and bind-mounts staged copies onto selected host `/data` paths. |
| `:1149/1418` | Calls guest property injection, then launches a new process with mount-only `unshare -m`. |
| `:1443..1464` | Bind-pins canonical `/dev/socket/zygote` and `usap_pool_primary` paths in the init view. |
| `:2602/2674/2742` | Helpers pick the first global `system_server` PID, then enter its mount view. Two servers make these selectors ambiguous. |
| `:3014..3021` | Any `system_server` OR `zygote64` resets guest-death detection. A retained host can mask genuine guest failure/auto-return. |
| `return_to_oneui.sh:215..229` | Broad-kills matching server and zygote names, not a distinguished guest generation. |
| `:256..285` | Repeatedly kills processes matching guest mount namespace or root device. Putting the authority there subjects it to this teardown. |
| `:709` | Explicitly rejects an existing `system_server` or running primary zygote before stock reconstruction. |
| `:876..907` | Aborts FUSE, may restart `zygote_next`, restarts netd and starts stock zygotes. This is reconstruction, not retained-server resume. |

The switch's cgroup/oom writes (`:281..286`) target its own shell PID and
inherited descendants. They neither move nor attest the pre-existing Samsung
server. These inspected control paths provide no retained-server exception or
original worker acknowledgment. Process renaming would not address init/parent/group,
socket, mount, cached-client, watchdog or service ownership.

## Captured Samsung zygote and watchdog declarations

`/system/etc/init/hw/init.zygote64.rc` (959 bytes,
SHA256 `55d71c63fcccb7b84664593f0bb1aebe7b54b07a04cea32b84427657b733debc`)
declares the original service command:
`app_process64 -Xzygote /system/bin --zygote --start-system-server --socket-name=zygote`.
It declares canonical zygote/usap sockets, task profiles
`ProcessCapacityHigh SystemServiceCapacityHigh MaxPerformance`, and a conditional
critical-service window. Its restart actions include `vdc volume abort_fuse`,
wake writes, and restart of audio, camera, media, netd, wificond and perfmond.
These are actual captured declarations; whether any specific action fires on a
particular stop/reap path is not inferred from its `onrestart` spelling.

`/system/etc/init/init.sysfw.rc` (3085 bytes,
SHA256 `db9688ba524c09d891f3498efacb0b1a8d303409df510164de0197f76e0475d9`)
initializes/enables Samsung softdog with timeout 100. Its stopped-zygote property
action sets reset information, restarts resetreason and disables softdog;
`persist.vendor.softdog=off` also disables it. Thus even a surviving server
needs a coherent watchdog/control contract. A changed property or a feeder log
does not establish that its real watchdog FD, heartbeat and failure response are
owned correctly.

**Unclosed native boundary:** these declarations do not establish this build's
init process-group kill/cgroup behavior, zygote/system-server parent-death or
SIGCHLD behavior, current task-profile membership, kernel watchdog ownership or
live PID tree. No stop/signal experiment or broad native audit was performed.
Skipping `kill system_server` must not be assumed to survive `ctl.stop zygote`.
Conversely, this report does not assert inevitable child death without that
missing implementation/runtime evidence. Keeping zygote instead requires real
host/guest socket and app-start routing; the current shared canonical socket
pins are incompatible with simply treating both as the original owner.

## Mounts, global names and native survival

The switch enters init's mount namespace (`:68..81`) and runs preparation there.
`bridges.sh` includes app/user/user_de, dalvik-cache/profiles, media and
resource-cache paths. Its bridge list is not a blanket bind of locksettings or
all `/data/system`; the concrete issue is ongoing original AM/PM/user/native
fresh path resolution through those overmounts. Open descriptors do not prove
future pathname accesses see the original state.

The new guest's private pivot (`guest_start.sh:12..48`) does not move an existing
multithreaded server into a preserved Samsung view. A promising investigation is
to separate guest-only mount preparation deliberately, rather than assume one
new namespace operation relocates every initialized security worker. That is a
proposal, not a prepared mount topology. Real CE/mount propagation and native
authorities must still agree with the original server's state.

Mount separation also does not provide separate global Binder service names or
property authority. OneOS calls guest property injection; return later restores
properties and SELinux (`:710..753`). A retained server could have continued
reacting to session changes. Cached original AM/PM/display/native handles alone
do not protect death/reconnect/new-lookup paths when guest services publish into
the same shared service environment. Canonical Samsung security endpoints,
separately routed guest framework services, and every real local lifecycle/user
adapter remain a required ownership plan. Alias names alone do not provide it.
A separate Binder driver context is not established here. Aliases in the shared
environment need complete real lookup/reconnect ownership; a different driver
would separately need proven handle, callback and native-caller transport.
The proposed separation must not silently assume either topology is assembled.

Native preservation is conditional. The guarded matched `gvld` branch
(`guest_prepare.sh:1257..1281`, `guest_start.sh:679..709`) preserves the host vold
names; the fallback gives guest vold the global `vold` name. This source branch
is not evidence of the currently installed profile. Return's five-name baseline
covers vold's two names, keystore2, installd and gatekeeper, with PID checks
`:689..700`. It omits original Java authority generation and fingerprint,
Weaver/KeyMint sessions/completion. Neither those PIDs nor a registered endpoint
prove a retained native operation/session remains valid. Media/audio/composer
and network control during the session can also affect genuine host callbacks.

## Retention versus cold reconstruction

| Dimension | Retained initialized server | Cold Samsung process |
| --- | --- | --- |
| Existing graph | Can preserve actual LSS/SPM, concrete SMS, LocalServices, user/policy objects and JNI bindings. | Must construct/admit the real graph, including Context/display, users/policy/native owners and boot-helper loading. |
| Mutation during startup | Avoids replaying cold constructors/migrations/cleanup merely to recreate already initialized owners. | Cold construction can perform real state reconciliation, migration and biometric cleanup; constructor success is not readiness. |
| Runtime burden | Keeps a broad live framework graph and callbacks; it is not a small inert credential library. | Can seek a narrower process, but its executable closure and exclusive handoff remain unassembled. |
| Switch/return burden | Requires coherent replacement of the exact controls above, preserving original dependencies and a resume contract. | Current teardown shape is closer, but real old-authority drain, native handoff and later retirement are still mandatory. |

The companion dependency worker corroborates that original AM unlock callbacks,
UMS/UserController, DPM/Supervision and StrongAuth handler/alarm work must remain
operational. Freezing/SIGSTOP of the server prevents it serving those obligations.
Fingerprint also retains real HAL/session and display/input/power callbacks;
indiscriminately disabling host presentation or display work is not a proven
security-only topology. Guest users/packages/UID policy and exclusive physical
display/input ownership remain required. See the independent companion
`docs/retained-authority-dependencies.md`; this card does not claim that its
objects were observed live.

## Four proposed coordinated gates

1. **Before stop line 971:** establish real original-server/zygote/init parent,
   process-group and watchdog ownership; replace the stop/kill/keeper/socket and
   process-identity assumptions coherently. Keep required workers running.
2. **Before prepare line 1087 and bridge line 3244:** preserve the genuine
   original source/state view for every real worker and native dependency;
   separate guest-only preparation with proven propagation and CE behavior.
3. **Before guest framework security construction/publication:** suppress the
   competing guest security producers; assemble guest-local lifecycle/user/
   policy adapters and explicit endpoint routing around the same live Samsung
   writer, with genuine physical fingerprint/display/input ownership.
4. **Before return teardown:** drain guest work and choose an owned retained
   resume OR safely retire then reconstruct. Adapt broad kills, absence gate
   and zygote starts together; never start a second stock LSS alongside the
   retained original. Default/failsafe reboot behavior remains unchanged here.

Current return's PID/user0/launcher postcheck (`:910..943`) proves neither
reciprocal PIN/FP acceptance nor exclusive writers. A retained resume branch
would need a different demonstrated contract, not deletion of gate 709. No
no-reboot or beta claim follows from this source comparison.

Recheck: `python tools/audit_retained_authority_control.py`. It verifies 15 pinned
upstream inputs, two captured init files, 30 source cards and preserved native
report pins. Only own report/inventory/tool/raw/generated files were written.
