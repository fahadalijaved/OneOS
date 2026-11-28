# Common private mount ancestor with two process roots

**Disposition: the common-ancestor mechanism is feasible with owned source
changes; the current launch script is incompatible unchanged.** One private
ancestor can preserve the Samsung-root native process and a ColorOS-root guest
receiver while fresh guest-only data/mirror peers carry mount events downward.
This need not keep every zygote/app in one permanent namespace. The captured
ColorOS native code itself creates descendants with slave propagation.

This is a source/preparation boundary, not a launcher or Android/kernel test.
No namespace, mount, chroot, OEM code or phone command ran. The
[inventory](../inventory/guest-common-namespace-proof.json) pins 35 checks, five
bounded original ColorOS functions/5,304 instructions, exact installed script
edges and reused native/alias/view evidence. Prior frozen 42-check data plan,
alias artifact and canonical selections are unchanged.

## What the actual launch code does

Installed `oneos_switch.sh:1418` creates the takeover mount namespace with
`unshare -m`. Installed `guest_start.sh` has **no chroot command**: it changes
directory to the staged root at12, makes `/` recursively private at13, and uses
`pivot_root . postinstall` at14 and fallback17. It later detaches `/postinstall`
at44. The mirror block mounts a new tmpfs at `/data_mirror` at78 and supplies
user0/profile binds at81–85, ignoring individual failures.

Those choices are not mandatory native behavior. A common ancestor must replace
the pivot/old-root cleanup under an owned fork and omit or reorder the late
recursive-private operation **before** new peer creation. Replacing the guest
mirror alias with another tmpfs would also destroy the intended receiver, so
that mirror block needs owner-controlled setup/readback rather than reuse.
The old stage-path `cd` cannot be retained after `/data` is shadowed.

The primary Linux mechanism distinction matters: chroot changes the calling
process's path root and leaves cwd/open descriptors separately owned; it is not
a security sandbox. Pivot_root changes the namespace's root mount and can
update other processes rooted at the former root. A shared bind peer receives
submount events; a slave receives them one way; recursive-private breaks that
relationship. These are upstream mechanisms, not an audit of the captured
Samsung kernel. See the upstream [chroot](https://man7.org/linux/man-pages/man2/chroot.2.html),
[pivot_root](https://man7.org/linux/man-pages/man2/pivot_root.2.html) and
[shared-subtree](https://docs.kernel.org/filesystems/sharedsubtree.html)
documentation, checked November6 UTC.

## Actual original ColorOS native flags

The captured source is original ColorOS `libandroid_runtime.so`, 3,138,824 bytes,
SHA256 `edfd170ccbca035d6acd8da1b93a346a7cb438f35cf706ba03037bdc1feb1279`.
It is **not** an assertion that the staged or running guest loads this exact
native file. That profile/loader admission remains required. PCs below are ELF
virtual addresses.

| Exact captured edge | Consequence |
| --- | --- |
| `nativeInitNativeState` calls `UnmountStorageOnInit` at `0x27fe50` | The native initialization edge is real in this source, rather than inferred from an AOSP release. |
| Normal path: load `CLONE_NEWNS=0x20000` at `0x28249c`, call unshare at `0x2824a0` | A zygote namespace split can happen even if the launcher did not create another one. |
| Load flags `0x4000`, add `8<<16`, call mount of `rootfs` on `/` at `0x2824cc` | Actual flags are `0x84000 = MS_REC|MS_SLAVE`, **not MS_PRIVATE**. A preexisting master/receiver relationship can continue downward. |
| `service_name == "zygote_c"` branch at `0x282498` | It skips only unshare, unsets that environment name at `0x282578`, then branches back to the **same slave-mount path**. No environment spoofing is proposed; actual branch inputs are unobserved. |
| `ensureInAppMountNamespace`, 308 bytes: flag check `0x12d6e8`; unshare at `0x12d708` | The helper conditionally creates an app mount namespace; it contains no mount call or recursive-private operation. |
| `SpecializeCommon` calls that helper at `0x12e2d0`, `0x12e480`, `0x12ec70` | Real app privacy work can create additional namespaces; its source behavior and failure paths must remain genuine. |
| `MountInitOverride` mounts tmpfs over `/system/etc/init` at `0x134788` | Per-root guest filesystem effects remain real. A ColorOS chroot must resolve its own admitted code/root tree, not host aliases. |

The selected SpecializeCommon body is included to pin the actual helper calls;
this is not complete transitive app/runtime/native behavior. It must not become
a claim that every descendant, vendor branch or later mount remains admitted.

Captured Samsung installd `ed618c…` has no explicit unshare/setns/chroot/pivot
imports, and selected complete main/start bodies have no direct such call,
generic syscall call or SVC instruction. This is a bounded negative fact only.
The ELF imports generic `syscall` elsewhere; loader/library constructors and all
later methods are not closed here. **No universal no-self-unshare guarantee or
live same-namespace attestation is claimed.**

## Minimum source-owned sequence

1. **Own one fresh child mount namespace and make its inherited hierarchy
   recursively private once, before any bind.** Verify actual mount/root
   invariants. The observed host init/installd main namespace4026532781 and
   shared:48 group, and SS main namespace4026536359/master:48, remain outside
   this new guest propagation topology. Those observations are not all-thread
   or future-propagation proof.
2. **Acquire child-local source/root handles after that privatization and before
   `/data` shadowing.** Parent-observed object identity can be an admission
   input, but an inherited parent-opened FD may pin a different mount object.
   Do not assume that inode equality supplies an appropriate child mount-source
   capability. The real owner must reopen/validate the intended child-local
   objects and retain their namespace, mount and lifetime relationships.
3. **Create fresh guest data and mirror mounts, then fresh shared peer groups.**
   The ColorOS root must itself be an admitted private mountpoint, using its
   original image mount or an owned self-bind; an arbitrary directory chroot
   does not establish the mount-root requirement of the native slave operation.
   The daemon-side `/data` receives the admitted whole staged-data object plus
   the `/data/data → user/0` alias. Bind the same shared data mount into the held
   ColorOS root's `/data`. Create a new mirror-base mount at daemon-side
   `/data_mirror`, make it shared, then bind its peer into the ColorOS root's
   `/data_mirror`. They must be **new groups from child-private sources**, not
   aliases retaining host shared:48 membership or an upstream host master.
4. **Validate both peer members before forking.** Same backing directories alone
   are insufficient. Native submounts at daemon mirror paths must have the
   corresponding guest receiver peer; actual source/target, group, flags and
   host-isolation readback are obligations of the future preparation owner.
5. **Fork with separate filesystem-root state.** The native child keeps the
   genuine Samsung root/runtime. In the guest child, use the admitted ColorOS
   root handle, per-process chroot and cwd reset; close outside-root handles
   except explicitly owned protocol/exec requirements. Do not share CLONE_FS or
   run namespace-wide pivot_root. This does not confer a root-compromise or
   shared-UID security boundary.
6. **Enter an owned startup derivative.** Remove the old pivot/postinstall
   operations and avoid any later recursive-private or mirror-tmpfs reset
   covering the peers. Preserve original failures, data/user policy, app privacy
   and required mount consumers. Do not execute the old global preparer or
   global return cleanup from the frozen data plan.
7. **Keep genuine native descendant behavior.** The normal ColorOS zygote can
   unshare and turn its inherited mirror/data peers into slaves of the common
   parent's native-side masters. The native sibling remains present as a master
   peer; this avoids a singleton peer becoming private with no master. Future
   native mount events can then flow to the ColorOS peer/slave descendants.
   Preserve actual branch values and validate the selected runtime/profile.
8. **Retire actual work before topology teardown.** Own every native/script/app
   receiver use, generated submount, accepted operation and persistent commit.
   The old fourteen-host-target unmount loop, lazy detach or PID equality is
   not an inverse or drain acknowledgement.

This closes the earlier **independent-rprivate mirror objection as a mechanism
requirement**, not every preparation requirement. It does not require two
independent private roots with an invented cross-namespace event broker; the
kernel peer/master relationships can carry the events if constructed and
retained by the real owner.

## Concrete stops that remain

The exact installed source needs the startup derivative above; leaving its
pivot/late-private/mirror replacement unchanged disqualifies this common-view
version. These are patchable source choices, not a demonstrated impossibility
of the topology. No such patch or launcher was emitted here.

The actual FD/private-preparation owner is still missing. Build has the precise
source boundary for a root-reviewed authored owner around steps1–6, including
child-local acquisition, fork/root separation and peer ledger. No new shared API
or controller readiness flag is introduced by this card.

Real non-null UUID `/mnt/expand` objects remain unassigned. Common propagation
cannot supply a legitimate volume, physical CE/FBE state or user identity. The
same applies to project/UID quotas, mutable inode metadata, caller-selected
paths, unowned artd/profile/scaffolding consumers, native completion and safe
return. Property-area/client/persistence, Binder routing, device controls and
permissions remain separate owners. The `511dac…` alias prototype does not
close any of them.

Recheck saved source evidence only:
`python tools/audit_guest_common_namespace.py --audit`. No phone candidate,
architecture selection or runtime acceptance follows.
