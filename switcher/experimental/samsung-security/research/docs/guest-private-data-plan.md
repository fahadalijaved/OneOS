# One guest-private data preparation sequence

**Result: a concrete operation plan, blocked at its first real producer.** The
PC-only [derivation tool](../tools/derive_guest_private_data_plan.py) emits a
non-executable twelve-operation plan and the exact fourteen-tree mapping. It
does **not** emit a shell, launcher or readiness stub: the installed sources
provide no owner that can perform the first private preparation transaction and
later mirror/native retirement safely. The
[inventory](../inventory/guest-private-data-plan.json) pins 42 checks and all
inputs; the ignored `out/guest-private-data-plan/operation-plan.json` is the
candidate sequence. No OneOS script, OEM/native code or device command ran.

This is one route-B proposal: retain the original canonical host daemon and its
views; prepare a fresh Samsung-root guest native process and a separate
ColorOS-root receiver over the same admitted guest objects. The emitted
`nstalld` ELF `511dac7e…` remains an unselected byte component. It supplies no
mount, protocol, state or namespace ownership. The frozen
[native-owner](retained-installd-native-owner.md),
[routing](retained-installd-routing.md) and
[data-view](guest-installd-data-view.md) cards remain unchanged.

## The exact source boundary to replace

The packaged switch reenters init's namespace at line79, stops zygote at971,
kills system_server at999, calls prepare at1087 and only forks the guest mount
namespace at1418. Prepare explicitly refuses a non-init namespace at7–10. Its
fourteen global binds occur at3240–3258, before the whole staged-data receiver
and explicit host adb/APEX imports at3260–3292.

The proposed owner must replace that entry/control composition; it cannot call
the unchanged switch first and repair mounts afterward, remove only the
namespace guard, or insert a hook after the host stop. Global property/control
changes are separately owned work, not made private by this plan. The first
missing implementation is a **source-owned private preparation and return
transaction**: it must retain real source/root/namespace handles, perform and
acknowledge actual child-only mount operations, preserve host invariants, and
keep their inverse ledger until real accepted work drains. No such object or
capability is supplied by the current scripts.

There is a matching new inverse constraint. Existing
`return_to_oneui.sh:349–352` unconditionally unmounts the fourteen **host** data
targets. Under B those targets must remain host-owned. Its later namespace/path
sweep at575–588 is also not a transaction over the proposed two child views.
Neither old cleanup region is a safe inverse to retain unchanged. This is not
a claim that an actual host mount was unmounted during this audit.

## Concrete forward sequence

| Operation | Exact proposed action and admission requirement |
| --- | --- |
| P0: source integration | Supply the reviewed preparation/return producer above instead of executing the unchanged switch/preparer. No runtime work proceeds while this owner is absent. |
| P1: acquire objects | Open/admit the actual staged-data directory, prepared ColorOS root and immutable Samsung code/library/APEX cohort before shadowing `/data`. Retain actual directory/executable/root identities and lifetimes. Handles are not immutable contents, labels or policy epochs. |
| N1: isolate the daemon view | Create the new child mount namespace, make its relevant hierarchy recursively private **before** a bind, and verify actual propagation plus host invariants. Merely calling unshare preserves inherited shared/slave relationships. No change belongs in init, canonical installd or retained SS. |
| M1/M2: bind data and alias | In that Samsung-root child only, bind the admitted whole staged-data object at `/data`; additionally bind its admitted `user/0` object at `/data/data`. The table below accounts for every old bridge pair. |
| M3: explicit host children | Import only genuinely required/admitted original adb/APEX children, if any, through retained objects with successful per-bind read-only checks. The source's warning-only writable fallback is not admission. Keep the original Samsung runtime/root distinct from guest metadata. |
| G1: ColorOS receiver | Supply the same admitted data backing/legacy alias under the separately admitted ColorOS root. Retain the root/cwd/executable objects needed across shadowing. Its root pivot must not substitute the native process's Samsung code/root view. This needs a real guest-start derivation, not the unchanged text-path entry. |
| V1: users/volumes/mirrors | Supply real user/UUID roots and data/misc/profile mirrors to **both** receivers, then own future update acknowledgements. Separate private mount namespaces share file changes through shared backing, not newly created mount events. No update channel is implemented. |
| Q1/W1: filesystem and other writers | Admit actual quota/project-ID, labels, serials, physical CE/FBE and caller-selected paths; replace other consumers' reliance on global binds and retain real background/native work owners. No fake result or forced-null UUID is permitted. |
| A1/R1: native admission and return | Only after those owners exist, admit the private native endpoint and guest routes. Stop guest admission and drain actual work before reversing exact child mounts. No daemon is launched by this plan. |

The recorded ordinary-OneUI observation `2d55a1ae…` is specific: init and
installd2493 main threads share mount namespace4026532781 with `/data` shared:48;
SS27202 main thread has namespace4026536359 with `/data` master:48. Sampling was
not atomic or all-thread. Thus the observed SS namespace difference does not
protect it from an init-view overbind. A future private-child transaction needs
real whole-thread propagation/object readback; this snapshot proves neither
that transaction nor future safety.

## Exact coverage of the fourteen pairs

Let `S=/data/local/tmp/oneos`. Each path below names the **candidate existing
source object**, not an observed/admitted inode or credential/user generation.
The proposed target is inside each owned child view, never host init's view.

| Child target | Candidate staged source | Required topology after private whole-data bind |
| --- | --- | --- |
| `/data/app` | `S/data/app` | inherited same-relative subtree |
| `/data/app-staging` | `S/data/app-staging` | inherited same-relative subtree |
| `/data/user` | `S/data/user` | inherited same-relative subtree |
| `/data/user_de` | `S/data/user_de` | inherited same-relative subtree |
| `/data/dalvik-cache` | `S/data/dalvik-cache` | inherited same-relative subtree |
| `/data/misc/profiles` | `S/data/misc/profiles` | inherited same-relative subtree |
| `/data/data` | `S/data/user/0` | **explicit legacy alias**, not `S/data/data` |
| `/data/media` | `S/data/media` | inherited same-relative subtree |
| `/data/misc/user` | `S/data/misc/user` | inherited same-relative subtree |
| `/data/misc_ce/0/sdksandbox` | `S/data/misc_ce/0/sdksandbox` | inherited same-relative subtree |
| `/data/misc_de/0/sdksandbox` | `S/data/misc_de/0/sdksandbox` | inherited same-relative subtree |
| `/data/misc_ce/0/rollback` | `S/data/misc_ce/0/rollback` | inherited same-relative subtree |
| `/data/misc_de/0/rollback` | `S/data/misc_de/0/rollback` | inherited same-relative subtree |
| `/data/resource-cache` | `S/data/resource-cache` | inherited same-relative subtree |

This derives **thirteen covered subtrees plus one alias**, not fourteen
installd-exclusive trees. A whole child `/data` bind also selects more than
those fourteen paths: notably guest-local layout/configuration and migration
state. Its scope must be admitted explicitly. The already captured preparer
itself warns that recursive rebuild/chown/chcon could cross mounts beneath
staged data (lines18–24); the new producer must retain the real refusal semantics.

## Remaining state and receiver stops

`/data/misc/installd/layout_version`, `/data/misc/user/<id>` and the legacy CA
migration source/destinations must all resolve into the intended guest cohort
before native main. The original main can create/migrate/delete/write before
publication. No host metadata/CA database is copied here, and no default layout
or user serial is fabricated.

The installed start block creates only user0 data_ce/de and profile mirrors,
with ignored mount failures. It does not supply native misc_ce/de mirrors.
Its root-private operation at13 and later ColorOS pivot require an explicit
two-view receiver/update design; file-object equality alone does not deliver a
native `tryMountDataMirror` event to guest zygote/apps. No shared-peer propagation
bridge or acknowledged update channel is selected.

Non-null UUID operations still select `/mnt/expand/<uuid>`. The actual preparer
imports host `/mnt`; the guest cleanup selector omits expand. No admitted guest
volume object is supplied. Treating UUID as null, silently falling back to host
paths or returning successful preparation would change genuine semantics.

Quota is a real writer frontier. The frozen Samsung
`CacheQuotaStrategy.pushProcessedQuotas(List)` body invokes
`IInstalld.setAppQuota(String,int,int,long)` at PC52. The existing native quota
cache reads real mounts and calls `quotactl`. The qualified host `/data` mount
is F2FS with usrquota/grpquota; that is not an independent guest quota or a proof
of any particular project-ID policy. A bind mount does not partition kernel
filesystem accounting or numeric UID/project identifiers. Actual backing-object,
quota assignment and inode metadata ownership remain unbound; no setter was
executed or new native setter decoded here.

Zero bridge rows have been proved exclusive to installd. The periodic package
scaffolder remains a real CE/DE/media writer; original idmap2/idmap2d paths and
profile/code consumers also need the right objects. Source comments name host
artd, but its complete endpoint/caller/view closure is not supplied by an alias.
Caller-selected absolute paths, including native SDP databases, remain outside
a finite fixed-root map. Property-area/cache ownership is separate Power work;
mount isolation alone makes no property or Binder-driver isolation claim.

## Supported inverse scope and next work

The operation plan gives a reverse dependency order for **future-owned mount
topology only**: stop admission and acknowledge real native/script/mirror work;
remove native-created volume/mirror submounts and the guest receiver; then
explicit host imports, legacy alias and private `/data`; finally release actual
child namespace/object owners. Ordinary unmount refusal retains the owner.
Lazy detach, a PID/log or empty router counter is not drain. The inverse does
not roll back layout migrations, app-data writes, quota changes or legitimate
security commits. It never unmounts the preserved host's fourteen targets.

The next concrete implementation is the P0 producer/control cut spanning the
identified switch entry, prepare receiver and return cleanup regions, with real
source/root/namespace handles and a mount-operation ledger. It must be reviewed
before any phone execution. Even after P0, the UUID/mirror receiver, quota and
other-native-consumer owners above still block a complete recipe. Emitting a
shell that merely exits on placeholder readiness would add no missing owner,
so this scope emits only the bounded source plan.

Recheck PC derivation: `python tools/derive_guest_private_data_plan.py`. No
canonical selection, architecture acceptance, phone candidate or runtime action
follows.
