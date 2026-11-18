# Guest zygote process scope and return

The held kernel profile supports a **candidate private cgroup2 subtree**.
Keep guest entry blocked. The saved evidence establishes a writable unified
mount, but does not establish permission to create and control a private
domain, the guest's real cgroup writer confinement, or descendant reap.
The current controller moves only itself to the unified root and the
current GVO close accounts only for its direct preparation child.
[Admission contract](../out/guest-zygote-cgroup-lifetime/ADMISSION.json)

## What the held sources establish

| Evidence | Consequence |
| --- | --- |
| Captured arm64 Linux 6.12.69 configuration enables `CGROUPS`, `MEMCG` and `CGROUP_FREEZER`. `PID_NS`, `USER_NS` and `CGROUP_PIDS` are unset. | No PID-namespace init-exit fence or pids-controller limit in this profile. The cgroup2 core kill and populated interfaces are a separate admission from the optional pids controller. |
| Two held mountinfo samples agree on a root-`/` cgroup2 mount at `/sys/fs/cgroup`, `rw` in both mount and superblock options, with shared propagation and `memory_recursiveprot`. Five v1 mounts coexist. | An existing unified hierarchy is plausible for scoped placement. `rw` does not prove DAC, SELinux, current domain, a non-root `cgroup.kill` file or controller enablement. No v1 mount needs to be altered for the proposed scope. |
| Captured Samsung init imports the zygote service and describes mounting cgroups from its configuration. The stock zygote service starts as root with its own task profiles. Captured platform policy labels cgroup2 `cgroup_v2` and has cgroup file-write grants to a broad domain attribute, including the captured zygote and SystemServer types. | Mount presence and the default type label cannot establish exclusive migration. The actual selected root-launch domain and access in the final guest/root views remain open. |
| Installed `guest_prepare.sh` lines 297–305 mount proc and recursively bind the **host** `/sys`. Its comment records the need for cgroup2 when zygote creates a SystemServer process group. `guest_start.sh` line 1284 execs the held launcher, which in turn execs app_process. | The legacy sys view is incompatible with the proposed migration fence. The comment identifies an actual integration obligation. It does not prove which paths the selected guest `libprocessgroup`, zygote specialization and task profiles will open. A flat leaf may also be insufficient for nested guest UID/PID groups. |
| Installed return script lines 215–229 includes name-based kills. Lines 256–284 scan mount namespaces and root devices and repeat bounded numeric PID kills. | The old script supplies no process occurrence binding, migration barrier or exact tree drain. Do not use it as the private scope's close path. |

See the held, rehashed source and mount records in the matching
[inventory](../inventory/guest-zygote-cgroup-lifetime.json).

## The exact owner seam

In the built guarded-view source cohort, `retained_root_handoff.c:308` opens
the cgroup2 root and ties it to visible PID1 and its own mountinfo. It writes
`0\n` through the held root `cgroup.procs` at line 333, reads its own
hybrid membership, and closes the descriptors. That self-only launch
profile is separate from guest containment. The shared root must never
become a kill target. These checks remain relative to the actual launch
view.

`guest_private_view_inputs.c:335` retains the real GVO owner before a
possible after-fork failure. GVO records the direct `fork()` at
`guest_private_view_owner.c:892`; its child sets parent-death SIGKILL and
unshares **only** the mount namespace at lines 597–599. The child sends
the seven PARTIAL rights at line 737 and accepts only CANCEL afterward.
The same owned child is the minimal place to add a private pre-exec
placement exchange. Neither a mount namespace, `setsid`, parent-death
signal, direct-child exit nor the BOOT SystemServer fork record establishes
this tree's lifetime.

Current `wait_owned` consumes exactly the direct child's terminal status
at lines 795–812. `finish_local_close` at lines 1057–1070 drops view/loop
handles after that direct reap. `gvi_close` at lines 346–369 then releases
its provider and guard after terminal 0 or 3. That is valid for the
preparation-only protocol. If entry can occur, the process-scope close
must precede those release branches, including the after-failure and
control-loss paths.

## Minimal unselected contract

1. **Create and retain the scope before entry.** The original controller
   stays outside it as sole waiter. Under the admitted cgroup2 parent,
   exclusively create a new non-threaded domain and a runtime leaf if
   needed. Refuse existing names and mismatched mount, inode or type.
   Retain opened parent, scope and exact control file identities. Require
   `cgroup.procs` in the placement leaf, `cgroup.kill` and
   `cgroup.events` at the retained non-root scope, and empty initial
   population. Require the actual root launch domain to own those
   operations. Use only controllers already delegated by the selected
   host profile. If nested guest process groups need a domain controller,
   keep the subtree root process-free and place zygote in its child leaf.
   Do not modify shared ancestor policy or controller enablement.
2. **Admit the actual writer topology.** Resolve the selected guest
   zygote/SystemServer's real `libprocessgroup`, config, task profiles and
   all v2 join destinations. Legitimate group creation and moves must stay
   below the held subtree. Exclude writable routes to the shared hierarchy
   outside that domain, including inherited descriptors, mounts and
   proc-root aliases. Prove stock host, init and other privileged owners
   cannot enroll foreign processes or move guest tasks out through their
   own paths for this admitted profile. A private mount name or successful
   initial membership read cannot enforce that condition. The current
   captured policy does not supply a new per-generation write boundary.
3. **Place only the already owned child.** While the exact GVO preparer
   is still blocked in its post-PARTIAL control loop, add a distinct
   source-owned placement step with the actual retained placement FD.
   On that same single-threaded child, write only self `0\n` once. Parent
   checks the still-owned live child's bounded unified membership against
   the exact held scope and rechecks the control/child generation before
   releasing a distinct one-shot ENTRY. Close the child placement
   capability before exec. No caller-selected PID, PID enumeration,
   parent-written PID migration, foreign task or launch-then-move window.
   A write or acknowledgement ambiguity retains ownership and forbids
   entry. The remaining exec, mount, runtime and source prerequisites
   still apply.
4. **Cut ingress, then stop and observe the held scope.** Latch retirement
   before any stop command. Revoke further entry, guest fork/control
   admission and any external placement. Target only the verified
   private scope's retained `cgroup.kill`; no pathname reopen or shared
   hierarchy fallback. Record the attempted write before issuing it.
   A successful write requests subtree termination. Require a fresh
   complete `populated 0` from the retained `cgroup.events` after the
   cutoff. A notification, empty PID snapshot or failed stop is not
   acknowledgement. Inaccessible, malformed, escaped, live or uncertain
   scope remains HOLD.
5. **Reap and release independently.** Kernel population and wait status
   are different. Consume the exact direct child status and account for
   orphaned descendants with a selected sole reaper. A dedicated
   controller subreaper armed before the fork is a candidate if it owns
   every child. It must coordinate its adopted-child wait with the
   original direct wait so a wildcard reaper cannot steal the direct
   status. Preserve other children and their owners if any exist. Keep the
   cgroup, view, loop and writer guard through confirmed process drain
   and separately owned outside-tree work. Remove only the exact empty
   scope and its owned descendants under the retained parent and check
   cleanup. Failed removal, lost custody or wait uncertainty remains
   HOLD. Existing GVO terminal 3 remains local release with kernel
   release unconfirmed.

The next selectable source change is the pre-exec self-placement and
combined drain owner. Selection needs the actual cgroup interface access
and guest migration/reaper closure above. This audit used saved evidence
only. It performed no process, cgroup, mount, device, native or OEM action.

For the file-backed controller, the drain gate belongs inside
`gtr_poll_close`, after its exact direct-child terminal reap and before
the first adopted view or witness close. The stage guard polls that owner
independently, and the provider releases its own backing after the guard
sees the expected terminal. Checking descendants after that terminal
would run after GTR had already released the references needed for
verification. An empty held scope and an exhausted dedicated child wait
also leave any namespace or file references exported to outside owners
to be accounted for separately.
[GTR close](../compat/native/guest_tree_release_owner.c#L208) · [Stage guard](../compat/native/guest_tree_stage_guard.c#L183) · [Provider close](../compat/native/guest_tree_stage_provider.c#L433)
