# Route B: guest-private native app-data view

**Disposition: no closed launcher prefix yet.** The static audit passes 78 checks over the exact installed OneOS 0.4.57 scripts and frozen native/Java proofs. It maps all fourteen global bridge pairs and twelve native root groups. No script, native binary, OEM class, mount or device command ran. No launcher or modified script was emitted. Route B remains a proposal; the frozen host-routing and 89-check user-lifecycle reports are unchanged.

The first missing producer is concrete: the current preparation path requires init's mount namespace and overbinds host paths there. No source-owned derivative currently prepares and admits a guest-private view while leaving host paths untouched. Calling the unchanged preparer in another namespace explicitly fails; calling it first in init's namespace already performs the global overbinds that route B must avoid. An alias-only native ELF change cannot repair that ordering.

## Exact inputs and present ordering

The [inventory](../inventory/guest-installd-data-view.json) pins every input. Script hashes are the **packaged installed** assets, including `guest_prepare.sh` `000d0a16…`, `guest_start.sh` `896b72cc…`, `oneos_switch.sh` `e0433f91…` and bridges `afe5e276…`. The actual staged guest services are `efb45f5f…`; their frozen method evidence establishes canonical Installer lookup → `OneOSInstalldProxy` → real Binder calls, including UUID/user/serial/flags for `createUserData`. This is acquired code, not loaded-guest acceptance. The Samsung native executable is `ed618c38…`; selected native bodies are reused without another disassembly.

PCs below prefixed `0x` are ELF virtual addresses. Other numbers are one-based packaged script lines; bounded exact script text is saved only under ignored `firmware/guest-installd-data-view/`.

Current source ordering is:

1. Switch reenters init's mount namespace (79) and invokes prepare (1087).
2. Prepare refuses a different namespace (7–10), mounted objects at/below staged data (21–24), selected staged symlinks (58–77), stale bridge mounts, or missing required bridge pairs. It attaches `system.raw` read-only, prepares staged directories and mutates their modes/labels/content.
3. Prepare globally binds the fourteen staged objects over `/data/<host-relative>` (3240–3246); existing host targets must then match staged `stat` device/inode or it exits3 (3249–3257). It also binds the **whole** staged data root into guest rootfs (3260), makes that bind private (3266), and explicitly imports host `/data/adb` and `/data/apex` children (3267–3268).
4. Only later does switch fork the guest mount namespace (1418). Guest start makes root recursively private (13), pivots (14), detaches old root with a remaining-mount refusal, removes selected inherited storage mounts, then creates user0 mirrors/storage views. Several individual mount commands ignore failure.

The existing identity/refusal checks protect the current global design. A new private design must replace their **meaning** with actual host-unchanged and guest-object equality checks, not delete the checks or treat an absent mount as success. No such producer or acknowledgment is currently implemented.

## All fourteen pairs and actual consumers

Let `S=/data/local/tmp/oneos`. Every row's candidate object is a source path, not an observed/admitted directory, serial, label or current filesystem identity. The global bind target would instead exist only in the guest-daemon/app-data view. `/data/data` deliberately selects `S/data/user/0`, not the separately created `S/data/data` directory.

| Private target | Existing staged object | Exact additional producer/receiver evidence |
| --- | --- | --- |
| `/data/app` | `S/data/app` | Prepare2910–2912 makes/owns directories; whole guest data bind3260 |
| `/data/app-staging` | `S/data/app-staging` | Same actual directory loop; whole guest data receiver |
| `/data/user` | `S/data/user` | Prepare2503–2505 package scaffolding; helpers3451/3571; guest CE mirror82 |
| `/data/user_de` | `S/data/user_de` | Prepare2500–2502; same helpers; guest DE mirror81 |
| `/data/dalvik-cache` | `S/data/dalvik-cache` | Prepare2068 and2910 create/own it; exposed through whole guest data root |
| `/data/misc/profiles` | `S/data/misc/profiles` | Prepare2548 deletes profiles; helper3459–3464 creates them; guest mirror84–85 |
| `/data/data` | `S/data/user/0` | Guest start77 creates this actual legacy alias; native CE-path choice is separately pinned |
| `/data/media` | `S/data/media` | Prepare2485; helper3591/3612; start88–97 writes and supplies guest storage views |
| `/data/misc/user` | `S/data/misc/user` | Prepare2475 creates user0; native `ensure_config_user_dirs` performs real config-directory work |
| `/data/misc_ce/0/sdksandbox` | `S/data/misc_ce/0/sdksandbox` | Generic bridge-directory creation3242; whole guest data receiver3260 |
| `/data/misc_de/0/sdksandbox` | `S/data/misc_de/0/sdksandbox` | Same; no additional concrete reader pinned here |
| `/data/misc_ce/0/rollback` | `S/data/misc_ce/0/rollback` | Same; no additional concrete reader pinned here |
| `/data/misc_de/0/rollback` | `S/data/misc_de/0/rollback` | Same; no additional concrete reader pinned here |
| `/data/resource-cache` | `S/data/resource-cache` | Prepare2508–2510; actual guest `idmap2 create`1134–1137 writes the selected output path1129; guest `idmap2d` starts1197 |

**Zero rows are proved installd-exclusive.** Concrete shell/native-command receivers already disprove exclusivity for several rows; other rows have only generic preparation/whole-root exposure and remain unclosed. The bridges/preparer comments name artd and idmap2d and explain intended host-daemon use. Comments alone are not audited loaded endpoints or complete call graphs. This card does not invent another daemon dependency, but cannot justify removing all global binds after redirecting only installd. The actual guest `idmap2` invocation and daemon launch are source facts; their successful publication/ongoing routing are not.

The periodic scaffolder also remains an active writer: it reads guest `packages.list`, creates/reowns CE/DE/media directories, and runs repeatedly from a background script. Its exit0/logs do not acknowledge every write, native work or retirement. Running native installd beside it without owning both writers is not exclusive lifecycle management.

## Native roots beyond the fourteen binds

| Root/native use | Candidate guest object and required owner |
| --- | --- |
| `/data` and native data-root derivation | `S/data`; must resolve to this admitted object before globals initialize. Native reads ANDROID_DATA/ANDROID_ROOT at `0x743c0/0x743d4`, but hardcoded paths mean environment changes alone are insufficient. |
| `/data/misc/installd/layout_version` | `S/data/misc/installd/layout_version`. Native format is pinned at `0x8ac84`; main reads/writes layout before publication. No specific packaged preparation or validated state for this new native owner is proved. |
| `/data/misc/user/<id>` | `S/data/misc/user/<id>`. Native real directory creation precedes/participates in operations; scripts scaffold only user0. Actual registry subject/serial/profile/physical CE authority remains Samsung-owned. |
| Legacy CA roots and migration destinations | Native formats `%s/keychain/cacerts-added`, `…removed` (`0x8ad84/0x8adb4`), user enumeration `/data/user` (`0x8adc8`), and misc/user destinations must all resolve within the same guest data cohort **before main**. Do not import host CA trees or call main as a probe. No CA file was read. |
| `/mnt/expand/<uuid>` | **No admitted guest object supplied.** Prepare1209 rbinds host `/mnt`; start57's removal selector covers pass_through/installer/androidwritable/runtime/user/storage, not expand. Native non-null UUID paths can therefore still name inherited host volumes. A path-name substitution or forced null UUID would change actual semantics. |
| `/data_mirror/data_ce/null/0`, `data_de/null/0` | Private mirror mounts onto `S/data/user/0` and `user_de/0`. Original start creates these only for user0 and ignores individual mount failures. This is not native mirror completion or physical CE proof. |
| `/data_mirror/misc_ce`, `misc_de` | Native `tryMountDataMirror` has these additional fixed roots. The original start77–85 block does not supply them. Real subject/UUID/update/receiver ownership is unbound. |
| `/data_mirror/cur_profiles`, `ref_profiles` | Original guest source binds staged profile trees; native/profile writer and mirror lifetime still need one owner. |
| Explicit `/data/adb`, `/data/apex` imports | Existing host child objects intended read-only in the guest; these are not guest-owned replacement metadata. The clone's Samsung code/linker/APEX/runtime cohort must remain separately admitted. |
| Caller-selected absolute paths, including SDP databases | No finite fixed-root map covers arbitrary caller paths. Native aliases do not rewrite them. No generic path sanitizer, borrowed caller path override or fake result is proposed. |

## Ordered replacement plan, with admission stops

This is a source/control proposal, **not executable instructions**:

1. **Before the global-bind region, select the real preparation producer.** It must preserve retained host canonical installd/SS views and all current guards while supplying guest-only mounts. The unchanged preparer cannot provide that contract. Exact derivative source, hash-selected OneOS integration and its failure/return behavior need approval first. No arbitrary boolean asserts that this work occurred.
2. **Retain original source objects before shadowing `/data`.** In a Samsung-root native process, binding `S/data` over `/data` makes the old text path `S/data` resolve inside the newly substituted tree. Acquire/retain directory handles to admitted staged data and any selected source roots before that operation. A future implementation must validate opened object identities and reject symlink/reentry/race drift. A held FD is not a contents/label snapshot or policy epoch; source paths alone are not admission. Executable and dynamic-library lookup also cannot be preserved by merely opening the data directory.
3. **Construct a child-only view before the first native thread or main effect.** Require successful recursive-private propagation isolation/readback before any bind; retain the genuine Samsung runtime/code root while mapping admitted guest app-data roots. Do not mutate init, retained SS or canonical host daemon mounts. Original rslave mounts still receive upstream changes; unchecked `--make-rprivate` attempts are not proof. Legitimate CE/volume changes need an owned propagation/update policy rather than a blanket frozen view.
4. **Bind the actual guest data and resolve every root above.** Require guest target/source identity checks and host target identity/propagation invariants. Resolve the source-FD lifetime issue before any shadow. The UUID/expand, native misc/layout/migration and caller-path gaps currently stop this step. Missing directories cannot become default metadata or forged readiness; new native first effects need an admitted target cohort.
5. **Supply guest receivers from the same objects and generations.** Ordinary file changes in shared backing directories do not automatically share later mount events. A Samsung-root clone and ColorOS-pivoted guest with independently private namespaces need a real mirror/user/volume update path; native `tryMountDataMirror` in one view does not prove guest zygote sees it. Existing user0 scripts are insufficient for all native roots or future users. Do not copy user registries, force CE getters true or replay Samsung user boot.
6. **Only then admit the native process and exact private route.** Alias selection/prototype is Shade/root's separate task. Original canonical host handles stay bound. The genuine guest proxy must resolve the approved private endpoint, preserving real arguments/errors/caller policy. Name presence and UID0/1000 do not attest source, state, code or readiness; native publication precedes cached-property completion. Native first effects and actual startup acknowledgment remain real operations.
7. **Own all accepted work until return.** Stop guest admission and the real script/native/profile/mirror writers, obtain their actual completion, then retire guest-only mounts/endpoint without changing retained host state. Background PID/log, namespace name or a counter around one wrapper is not drain. No retirement hook is invented here.

Even a correct namespace plan does not create a separate filesystem quota or UID namespace. Selected native quota code reads real mounts and invokes `quotactl`; stage binds alone do not prove distinct backing storage/project IDs/accounting. Labels, ownership, user serials, inode flags and physical CE/key semantics remain properties of actual objects. Two process-local locks do not serialize two daemons touching one object. These are limits of the proposed isolation mechanism, not claims that a particular unobserved guest filesystem is already shared or corrupt.

**Next action:** root must choose and review a source-owned preparation/mount composition that replaces the global region, then assign actual UUID/expand and mirror-receiver ownership before authorizing a launcher. The present result is the explicit first missing producer plus concrete later counterexamples to `/data`-only isolation. No route-B launch prefix is closed by this card.
