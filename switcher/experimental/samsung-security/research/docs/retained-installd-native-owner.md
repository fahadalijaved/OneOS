# Samsung installd: native owner boundary for two instances

**Source-only disposition:** a second Samsung installd is not closed by changing
the service name or `ANDROID_DATA`. Both proposed placements need a real path,
mount, state and caller owner **before its `main` runs**. No demonstrated
singleton makes two processes universally impossible; the selected source also
does not provide their cross-process admission/drain contract.

Root acquired `/proc/2493/exe`: 640,912 bytes, SHA256
`ed618c386528c0b9890c67cbdcb22e1c194f44b034d8e36be2d7f2217fef7dfc`.
Remote hashes before/after, stable PID start time and PC bytes matched. This pins
the observed executable, not future Binder recipients, loaded libraries or all
threads' views. This worker made no phone request. The
[inventory](../inventory/retained-installd-native-owner.json) and
[reader](../tools/audit_retained_installd_native_owner.py) preserve fourteen
selected functions/3,932 decoded instructions and 74 exact instruction/literal/
edge checks. PCs below are ELF virtual addresses, not live process addresses.

The same executable hash appears in the earlier immutable mounted Samsung
index. One bounded 4,783-byte `system/etc/init/installd.rc` member was copied from
that capture and hash-checked; no OS tree was re-extracted. Its service stanza
starts `/system/bin/installd`, class `main`, user `root`, with CHOWN,
DAC_OVERRIDE, DAC_READ_SEARCH, FOWNER, FSETID, KILL, SETGID, SETUID and SYS_ADMIN
capabilities. These are captured init declarations, not proof of the current
process's effective capabilities/SELinux context or a permissible clone launch.
No network/AOSP source substitution was needed for these ELF facts.

## Publisher and work before publication

`InstalldNativeService::start()` at `0x261fc` obtains
`defaultServiceManager` at `0x2622c`, constructs `String16("installd")` at
`0x26238/0x26240` and a `BnInstalld` instance at `0x262a4`. It invokes the
manager's virtual slot `0x30` at `0x26348`, with `w3=0`, `w4=8`, then tests the
returned status at `0x26390`. This is the actual name/publisher construction
edge. The indirect runtime manager target and successful registration were not
attested. No selected main/start instruction supplies an argv-configured name.
A same-length alias would still require a reviewed code change and complete
route ownership; none was made here.

On the zero-status path it starts Binder threads at `0x263a4`, names the pool at
`0x263ac`, then reads `persist.zygote.app_data_isolation` with default true at
`0x263e8` and stores the result at `0x263f8`. `main` later joins the pool at
`0x8b0a0`. Endpoint publication/thread startup therefore precede this cached
property initialization. Name presence is not a complete startup acknowledgement.

Earlier, `main` at `0x8aaf8` already performs real state work:

| Exact edge | Ownership consequence |
| --- | --- |
| `init_globals_from_data_and_root` at `0x8ac50`; its getenv calls read ANDROID_DATA/ANDROID_ROOT. | Selected environment and original dependency/root view must exist before startup. |
| Format `%smisc/installd/layout_version`; `fs_read_atomic_int` at `0x8acac`. | The layout file belongs to the selected data cohort; it is not a process-private marker by name alone. |
| `ensure_config_user_dirs` at `0x8acc8`/`0x8ad04`. | Startup may create/adjust user-config directories before serving a client. |
| Conditional literal `/data/user` enumeration, CA-directory copy calls at `0x8af74`/`0x8afc0`, old-directory deletion at `0x8b018`/`0x8b050`. | A fresh clone is not an inert probe. Conditional migration must target the intended cohort. |
| `fs_write_atomic_int` at `0x8b070`; SELinux status open at `0x8b088`; only then service start at `0x8b090`. | A later publication refusal cannot undo earlier startup mutations. |

`ensure_config_user_dirs` builds `%s/misc/user/%u` through the original helper,
computes user-dependent ownership and calls `fs_prepare_dir` at `0x7e0c4`.
`createUserData` also reaches that helper at `0x347ac` after native caller checks
and a per-user lock. The selected source is not an empty user-creation ACK.

## Path, cache and shared-state constraints

**Environment alone is insufficient.** `create_data_path(nullptr)` branches at
`0x790e0` to `0x7913c`, then builds `/data` with immediate stores at
`0x79140–0x79154`. Non-null ordinary UUIDs lead to `/mnt/expand/%s`. Debug TEST
branches have separate property checks; they are not a proposed routing API.
The CE helper can choose the data alias or `%s/user/%u`. A renamed process or
different ANDROID_DATA does not rewrite these literal paths or caller-provided
absolute filenames.

`tryMountDataMirror` prepares fixed `/data_mirror/data_ce`, `data_de`, `misc_ce`
and `misc_de` roots, derives data source paths, checks access/stat and reaches
four `mount` calls (`0x40050`, `0x400b4`, `0x40104`, `0x40154`). A distinct
endpoint does not isolate these kernel mount operations. UUID, mirrors, app-data
trees, propagation and real FBE/user policy must describe the same intended
cohort; copying directory names is insufficient.

`invalidateMounts` locks an instance mutex at `0x3ed6c`, clears its map, invokes
quota invalidation and reads `/proc/mounts` plus `persist.sys.fuse`.
`InvalidateQuotaMounts` similarly locks/clears a map, reads `/proc/mounts`, filters
mirror/device paths and calls `quotactl`. These caches describe the process's
actual view and the real backing filesystem; separate instances do not
automatically maintain each other's coherence or divide filesystem-wide quota.

The selected `LocalLockHolder` uses heap weak/shared-pointer maps and
recursive/shared mutexes. `createUserData` takes its user lock at `0x346b4` and
`0x346c0`. These process-memory locks do not serialize another installd process.
This does not claim that no file/kernel locks exist elsewhere; it means no
cross-instance app-data lifecycle drain is proved by these locks.

The Samsung `migrateSdpDb` method retains the caller's path, locks its own
instance, uses `sqlite3_open` at `0x43568`/`0x43720`, and can execute
`pragma sdp_set_engine_id(...)` at `0x43794`. It is a caller-selected database,
not a newly discovered universal installd database. SQLite locking does not
establish exclusive ownership of broader package/data/DAR operations. No database
or app-private content was opened by this audit.

`checkUid` obtains real Binder calling UID and accepts UID1000 or root; other
values take the error path. That check is not host/guest package or generation
attestation, particularly for two frameworks using system UID. Actual imports
also require the captured Samsung dependency cohort, including libbinder,
libselinux, libsqlite, libpersona, libdualdar, libknox_filemanager and libepm.
Their full global/native/child-work state is not closed by this bounded ELF read.

## Placement comparison against current OneOS

The frozen [installed profile](installed-oneos-code-profile.md) pins fourteen
**init-view** app-data binds: app/app-staging, user/user_de, data→user/0,
dalvik-cache, misc/profiles, media, misc/user, CE/DE sandbox and rollback trees,
and resource-cache. They are not a blanket redirect of `/data/system` or
`/data/misc/installd`. Root's qualified observation has init and installd sharing
mount namespace4026532781 and `/data` shared:48; system_server's distinct view
has `/data` master:48. Neither distinct PIDs nor that namespace difference proves
protection from future app-data overmounts. No such transition was tested.

| Proposed placement | Concrete required cut / first unresolved owner |
| --- | --- |
| **A: fresh host-owned private clone; keep legacy global guest binds** | Establish its original physical `/data`, `/mnt/expand`, mirror/config/layout view before main; prevent later init-view bind propagation from changing it. Retarget every host native route, cached handle, death/reconnect and already-issued operation. The original canonical daemon becomes guest-facing only under a real owned handoff. Both fresh startup effects and existing canonical native consumers remain live obligations. |
| **B: retain original host canonical daemon; fresh guest-owned private clone** | Put the guest clone's actual paths/mirrors and startup writes in an admitted guest view; provide a distinct endpoint and complete guest ABI/routes. Remove or segregate the fourteen global guest binds so they cannot redirect the retained host daemon. Guest-only binds are a proposal, not a completed substitute for current OneOS scaffolding or other native consumers. |

Both clones are **fresh processes**, unlike retaining the initialized original.
B avoids moving host routes if the canonical daemon truly remains host-owned;
A can preserve more current guest routing but needs complete host endpoint and
original-view separation. This is a bounded tradeoff, not architecture selection.
The paired Power scope owns actual Installer/direct-IInstalld callers, reconnects,
cached references and asynchronous drain; a counter around one Java wrapper
cannot own those existing native frames.

The minimal remaining contract is: admit the full intended pre-main cohort;
establish whole-thread view/propagation and real capabilities/context/library
binding; prepare one explicit endpoint identity and caller-generation routing;
quiesce old callers plus native/deferred work before handoff; publish only after
real startup/property/cache acknowledgement; and drain the guest/clone before
unmount/return while preserving the original daemon's valid state. The first
item is already unbound in both alternatives. No fake readiness flag, PID/name
comparison or SIGSTOP substitutes for it.

Recheck saved static evidence only:

```text
python tools/audit_retained_installd_native_owner.py --audit
```

No OEM code, OneOS script, daemon, VM, runtime patch or launch ran. No alias was
emitted, phone state changed or clone/readiness/security case accepted.
