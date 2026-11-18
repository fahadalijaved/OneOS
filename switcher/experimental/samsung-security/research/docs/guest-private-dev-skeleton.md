# Private dev/socket skeleton v3

**Compiled and statically reviewed only; unselected and never executed.** This
explicit v3 successor changes only the authored owner C/header and adds this
report and its inventory. One separately authorized PC cross-build and read-only
ELF inspection passed. No model/test, native helper, mount, Android/OEM, network
or device operation ran. The diagnostic APK/phone proposal is unchanged.

The original cached donor image supports the target: a bounded9,760-byte ext4
read found root `dev`→inode24, directory0755/UID0/GID0 with only dot entries.
`dev/socket` is absent. The whole92c7 image hash was inherited, not recomputed;
this is not actual staged/mounted image equivalence. That evidence and the
root-selected v3 API/independent API review are separately pinned in the
[inventory](../inventory/guest-private-dev-skeleton.json).

## Source behavior

The existing child owns its unshare/rprivate, actual RO loop configuration and
CONFIG result/ACK, RO image mount, guest data/alias and mirror peers. V3 then
no-follow-opens actual image-root `dev`, requires the same image mount, exact
root-owned0755 directory, a bounded empty-directory read and no foreign target
submount. It refuses unsupported/missing/nonempty targets; no image mkdir,
writable remount, host-dev rbind or fallback occurs.

Only the owned child mounts a new1MiB/64inode tmpfs on that exact dev target:
mode0755/UID0/GID0,NOSUID|NODEV|NOEXEC, private without shared/master propagation.
It reopens and reads back the actual post-mount object before using a writable
FD to create `socket`. Metadata adjustment is limited to this newly created
directory, accounting for inherited umask/group. It does not make device nodes,
listeners, property areas or Binder objects. The inherited-root dev object/mount
is compared before/after; parent performs no namespace/root/mount operation.

The final packet has new magic0x47564f33/version3 and exactly seven private
SCM_RIGHTS roles: namespace, inherited root, guest root, data, mirror, dev root,
socket directory. Earlier f5..15 temporaries retain their meanings; named new
cells and explicit rights packing avoid sending those temporaries as new roles.
The parent accepts no v2 packet/fallback. CONFIG/ACK remains an independent
zero-right stage; DEV/SOCKET failures remain errors after confirmed loop work.

Dev and socket are distinct directory objects on **one fresh mount**. Shared
child/parent validation checks actual mount IDs, filesystem/type/options/modes,
guest-root/dev relation and a no-follow socket lookup from the received dev FD.
The parent reads the actual owned child's mountinfo/namespace relation, not a
packet-supplied ready flag. Unexpected entries, read/closedir errors, incorrect
objects or close uncertainty refuse publication.

The opaque public plan, observations, functions and numeric terminal values are
unchanged. Gvi, supervisor and parser source bytes are unchanged. The header's
comments describe the stronger private custody; its non-comment C declarations
remain identical. This is a source comparison; the cross-build establishes its
limited compilation result, not a kernel or Android ABI acceptance test.

## Lifetime and remaining owners

Every new child cell is initialized and closed on both exit paths; the packing
array owns no aliases. Parent adoption, resource-zero checks and final local
close cover all seven retained roles. Existing unknown commit/close/reap paths
retain HOLD. Only known local child reap and capability closure can yield the
permanent3 LOCAL_RELEASED_KERNEL_UNCONFIRMED; this never means kernel unbound,
native work drained, successful boot or safe return. Lost control delivery does
not erase the parent's actual child/wait/resource custody, and EOF cannot attest
final exec. No high-FD or process-name workaround is added.

The helper still only prepares filesystem resources. Its default no-op, exact
preparation flag and30-second decision budget remain in the unchanged supervisor;
it has no continuing runtime lease, guest exec, extra peer or permanent process.
NODEV is preparation-only: genuine device/Binder/property/logging/native socket
providers, code/APEX/classpath identity, real process/current-subject ownership,
accepted descendant/native work and return remain unassembled. Later dev overlays
must not silently cover this tree. Missing providers do not become fabricated
device numbers, endpoints, policy results or readiness values.

## Historical source and evidence

Exact v2 owner4894ca19/header01e95768 and17 related source/report/receipt files
were copied before editing under
`out/guest-private-dev-skeleton/history/v2-before-v3-20261106T125827302468Z/`.
The BEFORE-IMAGES manifest3327bc0d explicitly maps old source-path/hash references
to those copies. Original reports, source/API manifests and actual unexecuted
638,664-byte28365340 build output are unchanged; their earlier compile proof is
historical and is not reused as v3 compilation. The new source freeze records
actual successor hashes, source diff, unchanged dependencies and that resolution.

Root selected source preparation after APIef615543/Power962f06ea. Actual-source
review429e2a36 passed before the separate root-authorized build. Source-phase
reportf0a26562/inventorya801c4f3/freezed5066a17 are preserved byte-exact under
`out/guest-private-dev-skeleton/history/source-phase-before-actual-20261106T133442609899Z/`
and in the builder's immutable inputs. Manifesta4040f1a records exact historical
path/hash resolutions; none of those source/API receipts was refreshed.

## Actual PC artifact and saved-output review

The one actual driver attempt ended0, authoritative terminal chunk9ad6fd.
`out/gdv-build/r-afb1c08e/receipt.json`, SHA256
`d9abd9dcee1125f500b4e7435bde7386f950202eeddeb7067082ef6271a8d10d`,
records compiler/readelf exits0/0 with empty diagnostic streams,1.375s/0.094s.
It compiled the actual four C units/seven source/header inputs for
`aarch64-linux-android31`, static PIE, without GVO_STANDALONE or extra source
substitution. Owner9e17a235/header0961f308 and the five unchanged gvi/supervisor/
parser inputs still match the frozen source and actual executed copies.

The 645,368-byte artifact is
`out/gdv-build/r-afb1c08e/guest_private_dev_skeleton`, SHA256
`3135cf1f0c2317d1422ad141a77f8aed508de8103076cc799e5e0cd9bbef7bd7`.
It was not executed, including its default/help paths. The old28365340 executable
is unchanged and was not used as the v3 output or rebuilt by this metadata step.

Independent saved-output proof
`out/guest-private-dev-skeleton-review/actual/actual-output-check.json`, SHA256
`2c1c86b6dd069a68a0635fff36dfb43a1dcc1596057943fb649a9a6a23ab1bb3`,
rehashed the saved artifact, 52 frozen entries, 27 input/copy pairs, 14 selected
NDK pins,seven source files and five source-phase copies. It independently read
ELF structure without invoking the producer/compiler/readelf/helper/model again.
The saved ELF is AArch64 static PIE with 4096-byte load alignment, NX/no WX,
RELRO/NOW, no PT_INTERP or DT_NEEDED. These are limited API31/static4KiB results;
they do not establish API37,16KiB or actual loading/kernel behavior.

The peer also found bounded source-corresponding symbols/literals and selected
opcode constants: magic0x47564f33,version3,count7 and200-byte frame comparisons.
That is bounded output correspondence, not a full control-flow/compiler-correctness
or runtime FD/protocol proof. Namespace/mount/loop/SCM_RIGHTS, actual close/HOLD/
terminal3, native/Android/full-security acceptance remain unobserved. This
metadata update replays none of those tools and grants no helper or phone action.
