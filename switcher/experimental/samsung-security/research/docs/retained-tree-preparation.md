# Tree-backed preparation components

A separate, materialized ColorOS tree could remove loop allocation from
the preparation and Stop path. The selected source would be the owned tree
under `/data/local/tmp/oneos-viewprep/backing/tree`. The dedicated EROFS
mount at `backing` leaves private data on the writable host mount. The
private child owns the fresh `/mnt/gvi/root` scaffold, its data and mirror
mounts, and the private device directory. The signed preparation cohort
uses the verified image controller. The tree components are a separate
offline build with no device selection.

## Native attachment and custody

The ARM64 attachment component clones the child-reopened source directory
by FD without recursion, sets read-only, nosuid and nodev on the detached
mount, then attaches it to the held scaffold directory by FD. It checks the
clone's inode and mount flags before moving it. A failed operation retains
the actual acquired clone FD and records whether the move was attempted.
The kernel can follow a covering mount during attachment, so the caller
must hold the private namespace and prove the exact unobstructed scaffold
through the operation. [Linux mount implementation](https://github.com/torvalds/linux/blob/v6.12/fs/namespace.c)

`guest_tree_prepare_root` joins these operations. It checks the exact
parent/child mount namespace witnesses, joins the fixed names to the held
directories, reads the complete private table from procfs, and verifies the
same clone by reopening `root` in the held scaffold. Its post-attach sample
must account for every original row and exactly one new private projection.
The source and reopened root share an inode and backing device. The clone
and reopened root share their mount ID, distinct from the source and the
covered scaffold. The pre-attach and post-attach parsers passed 64 and 55
inert fixtures respectively. The components link as an ARM64 relocatable.
[Linux FD mount ID](https://github.com/torvalds/linux/blob/v6.12/fs/stat.c#L231-L242)

The clone shares the source inodes and superblock. Read-only on the clone
requires independent exclusion of writers through other paths. The current
ext4 loop path checks a different filesystem identity and cannot admit this
tree by substituting a path. The separate release component owns its real
fork, sole waiter, control socket, source witnesses and adopted rights. It requires a
terminal reap and successful tracked closes. It passed 511 checks across 13
inert syscall-shim scenarios. The controller must also account for refused
rights, stage and guard custody before reporting local cleanup. Stock return
and the actual guest service lifecycle require separate evidence.

The tree-only control owner now selects the fixed child constructor and
complete seven-descriptor receiver. The child builds its root, data and
mirror peers, alias, device and socket tree before replying. The parent
reads the actual child proc mount table and verifies the received namespace
and root, inherited root, data and mirror peers, alias, and device and
socket objects inside one namespace check. A failed check closes the
received descriptors and retires that attempt. The complete preparation
components link as an ARM64 relocatable. The control, parent-root, data,
and device fixtures passed on the PC.

The separate tree stage provider now holds the fixed stage, tree, data and
parent namespace descriptors. It acquires the same lease and negative
reservation as the isolated image controller so the two cohorts exclude
each other. The tree guard holds its exact child owner and removes the
reservation after that child's local release and the provider's verified
source closure. An armed attempt with uncertain cleanup retains its marker.
The guard passed 19 inert host scenarios. The current stage provider
requires the donor backing's dedicated EROFS mount and a separate writable
data mount. Thirteen inert cases verified the split and late drift handling.

The original dispatcher and new stage provider link together as a distinct
ARM64 relocatable. The existing wire state 6 reports local cleanup after
the provider's actual terminal result. Seven host fixture checks covered
the transition and sticky terminal. The final executable link refuses on
the single required `guest_tree_admit_stage_contents` symbol. Its owner
must join the exact tree contents to a writer-exclusion guarantee on the
same retained descriptors. A PC receipt can locate a tree for independent
readback. Stage admission requires the live ownership guarantee as well.

The block-backed ARM64 build embeds the exact 2.43 MB manifest and its SHA-256
pin. The native decoder verified all 15,574 records and matched 14 digest
vectors. The compiled tree reader walks the held directory, verifies every
logical file hash, and checks raw names, mode, owners, links and xattrs.
It requires a writer fence before reading and latches uncertain closes.
The EROFS probe checks the same-device block descriptor, read-only state
and sampled single-device superblock. A retained mapping owner must still
prevent raw writes and mapping changes across the lease.
The table parser passed 49 inert cases for a read-only verity mapping with
exact device, digest, salt and range pins. It checks a returned table sample.
[SHA-256 specification](https://www.rfc-editor.org/rfc/rfc6234.html#section-6.2) · [Linux symlink xattrs](https://github.com/torvalds/linux/blob/v6.12/fs/xattr.c#L748-L758) · [Linux verity contract](https://docs.kernel.org/admin-guide/device-mapper/verity.html)

## Materialization and boot inputs

The bounded image audit verifies 15 selected inodes, the original ELF
interpreter link, and inline and external xattrs. `run-as` carries an
external `security.capability` attribute. A working materializer must
preserve file types, content, ownership, hardlink identity, symlink target
bytes, SELinux labels and capabilities. The old Windows extraction left
symlinks uncreated and renamed case collisions. Linux directory creation
also normalizes ordinary symlink mode bits to `0777`. The proposed profile
would need to verify that normalization only for enumerated links and
check the exact resolved executable and policy. [Linux exec lookup](https://github.com/torvalds/linux/blob/v6.12/fs/exec.c#L834-L859)

The full ext4 metadata census found 15,574 reachable paths and inodes. All
had a SELinux label, two had capability xattrs, and 329 were symlinks. The
saved 7-Zip listing independently matched all non-root paths and the
available metadata. A separate pass hashed 13,787,452,714 logical bytes
across all 11,864 regular files and joined the exact ext4 runs to the
census. Six independent sample files matched their earlier extraction,
including two sparse files and an empty file. The sealed-plan Linux writer
now streams and checks actual donor ranges, recreates raw directory entries
and metadata, and requires full destination readback. The PC verified the
plan and inert streaming fixtures. A separate readback checker verified
the plan and 21 inert checks. A real Linux round trip still needs a
repo-contained runtime and a filesystem that can preserve the required
xattrs. The PC has emulator binaries, but its held emulator guest is a
Google Play user image with no verified root writer.

The held Linux `mkfs.erofs` 1.7.1 can consume a tar stream with raw xattrs.
The stream producer now frames the exact donor under `tree/`, verifies
logical file digests, and preserves binary attributes. Its bounded dry run
and independent tar fixture passed. The Windows `mke2fs` test crashed on
a small inert tar input. The Linux builder still needs a compatible
runtime and an actual metadata round trip. The inspected Android QEMU
binary runs Android host setup before parsing its options, and its normal
`-qemu` boot path reaches AVD creation. The held EROFS tool also needs a
Linux dependency absent from the inspected caches.
[Held runner analysis](../out/contained-erofs-runtime/QEMU-ENTRY-STATIC.json)

The [Windows raw image builder](../tools/build_guest_tree_erofs_pc.py)
assembled the actual 13,890,850,816-byte carrier using the core EROFS format
with uncompressed data, extended inodes, inline security xattrs and zero
padding. The donor source and every logical file were checked during the
write. Full independent readback matched all 15,574 donor paths and 11,864
regular-file hashes, plus all three core APEX payloads. Its whole-image
SHA-256 is `094ff7e7ac1148fab732719d2e04a943fbbcc0d7d0ae67ad62d898b552eb365d`.
A separate bounded reader checked selected raw metadata and real payloads.
[EROFS core format](https://erofs.docs.kernel.org/en/latest/ondisk/core_ondisk.html) · [Full readback](../out/guest-tree-erofs-image-readback/r-c06d34d3/receipt.json) · [Independent sample](../out/guest-tree-erofs-pc-independent/receipt.json)

The [offline raw EROFS verifier](../tools/verify_guest_tree_erofs_image.py)
checks raw path closure, inode metadata, xattrs, symlinks, logical file
digests, image geometry and whole-image SHA-256. The tree-only fixtures
rejected 17 mutations. A separate carrier fixture embeds the three actual
APEX payloads and rejected six mutations. Full donor image readback remains
pending.

The [core APEX carrier stream](../tools/stream_guest_tree_core_apex_tar.py)
adds the pinned ART, I18N and Runtime images beside `tree/`. The PC checked
all 58,339,328 source bytes, the three exact archive names, root ownership,
mode `0444` and rejection of a changed digest. The original tree-only
stream remains a separate profile. The [ARM64 backing reader](../compat/native/guest_core_apex_backing.h)
requires the current stage guard, same read-only EROFS mount and exact
payload digests before offering the three descriptors together. Its offline
build and data checks leave the actual image, runtime attachment and APEX
activation pending.

The [offline dm-verity builder](../tools/build_guest_tree_verity.py)
and independent verifier passed five byte vectors and 28 CLI checks on
inert data. The captured platform policy permits multiple stock services to
issue control ioctls on the shared device-mapper node. An open block FD and
matching table sample therefore leave table replacement possible. The
separate file-backed EROFS option is under review for a way to bind an
fs-verity-protected inode to a mount created by the same owner. A read-only
query matched the pinned phone build, the current `/data` F2FS mount and the
same device's `verity` feature token. That records filesystem support.
[Mapping review](../out/guest-tree-mapping-owner/FILE-BACKED-EROFS.md) · [Read-only F2FS observation](../out/guest-tree-mapping-owner/LIVE-F2FS-FEATURE.json)

The [offline fs-verity tool](../tools/build_guest_tree_fsverity_pin.py)
produced the SHA-256 file digest
`9b2b664582360dec660e3e25c840104c16b1e1a9cb4aadbf8f467e200c525ba9`
for that exact image using an unsalted 4 KiB tree. The file-backed controller
build embeds the image length and digest once. An independent full-image
recalculation matched all four Merkle levels and the exact descriptor. The
controller joins the private controller
namespace, measured F2FS file, mount created from that same retained file, and
the attached `backing/tree` descriptors before starting the child. Teardown
requires the actual child release, the provider's descriptor closure, one
verified normal unmount and only then stage-guard release. The ARM64 static
PIE linked and the separate block-backed build continued to refuse its
missing owner. The provider passed 20 inert cases, including late missing
paths after mount acquisition and uncertainty during release. The real
controller can continue local mount acquisition after a peer cutoff until
the current syscall path returns. It must refuse publication on its next
control check and drain the same owner. Device provisioning, kernel mount
behavior and Prepare/Stop acceptance still require separate evidence.
[Digest algorithm](https://docs.kernel.org/filesystems/fsverity.html#file-digest-computation) · [Independent digest](../out/guest-tree-fsverity-pin/carrier-r-3d0dc2ef/INDEPENDENT-DESCRIPTOR.json) · [Controller build](../out/tree-retained-controller/r-9ca6ad43/receipt.json) · [Provider tests](../out/guest-tree-file-stage-provider-review/r-late-miss-3488eaa5/receipt.json)

The separate [provisioning component](../compat/native/guest_tree_fsverity_provision.h)
creates a fixed new leaf exclusively, verifies the written bytes, and has
one enable-and-measure path. Its ARM64 object intentionally depends on the
real installer writer guard. Publication to the controller's `guest.erofs`
name and actual device use remain open.

The held Samsung policy sources lack 48 donor SELinux types across 90
paths. None intersects the 67 direct donor startup paths or 10 Runtime
APEX inode labels checked. The comparison covers those specific paths.
Each unsupported path still needs verified compatibility or a documented
optional removal before a materialized stage can be admitted. The saved Samsung FUSE
policy uses filesystem-level label rules, so that alternative cannot be
admitted from preserved per-inode xattr bytes alone.
[Linux filesystem-label selection](https://github.com/torvalds/linux/blob/v6.12/security/selinux/ss/services.c#L2756-L2805)

The current read-only, `nosuid`, `nodev` attachment is a preparation view.
`nosuid` affects both file capabilities and SELinux transition checks even
when the original xattrs are present. Guest launch needs a separately
reviewed enforcing execution profile. [Linux capabilities](https://github.com/torvalds/linux/blob/v6.12/security/commoncap.c#L681-L703) · [Linux SELinux exec checks](https://github.com/torvalds/linux/blob/v6.12/security/selinux/hooks.c#L2117-L2159)

Five donor APEX trees and seven classpath fragments are pinned. Telephonycore
has a conditional versioned-to-stable alias with actual EROFS labels. An
active alias set, guest linker configuration and effective Java classpaths
remain open. The bionic property reader passed 35 byte fixtures for stored
SDK and codename. It also read SDK 37 and `REL` from the separate inert
build-property and serial files. A 388-byte property-info fixture verified
the donor layout for those two keys. The real private property area, complete
compiled contexts and guest access remain open. The unchanged donor tree
has all three original property-context source files in compiler order.
Its vendor and ODM lookups stop at verified missing paths. A different
partition mount view requires its own source check. The complete donor
`property_info` binary includes all 2,255 rules and passed 3,320 lookup
probes. The held runtime APEX's `linker64`
inode carries the original `system_linker_exec` label and all 14 direct
`app_process64` library inputs were rechecked. The active runtime alias
and executable mount remain unadmitted. The linkerconfig audit pins the
original producer order and named Runtime, ART, and I18N dependencies.
The three core payloads now have a joined source bundle with the scanner's
stable-directory rule. A separate ARM64 staging component can build those
aliases once it receives the three admitted backing owners. Active aliases,
effective partition and property
view, and generated configs remain open. [Evidence index](../inventory/retained-tree-preparation.json)

The two PIN path verifiers independently checked the held code. The selected
ColorOS keypad still sends transaction 10 to its guest LockSettings. The
original preparation host APK holds the check owner and omits the private
Binder endpoint. A separate host build now compiles the same-base closed
endpoint. Publication, delivery, physical-user binding and live policy
dispatch remain open. [Closed host build](retained-pin-host-cohort.md) · [ColorOS route](../out/guest-pin-retarget-admission/REPORT.md)

## Offline APEX provider link and entry inputs

The 18-object ARM64 relocatable link joins the existing v5 APEX components
with the saved source, mount, property and release providers. It resolves
all eight direct repository references from the v5 components. The linked
guard still requires `gtc_begin` and `gtc_poll_close` from a matching
controller owner. The relocatable has no program headers or `main`, and
the prepared controller still ends at Partial. The actual same-attempt
descriptor handoff, APEX attachment, and cleanup remain open.
[Provider link receipt](../out/guest-tree-apex-v5-provider-link/r-87dbbe8d/receipt.json)

The three-core preparation carrier contains Runtime, ART and I18N. Its
raw donor tree also contains SDK Extensions' compressed preinstall package,
but its prepared APEX inputs omit the active SDK Extensions payload. The
classpath generator, its boot fragment and `framework-sdkextensions.jar`
need the stable SDK Extensions directory. The held static classpath scenario
covers four modules. Five other donor modules have seven further classpath
declarations whose live membership and order still need proof.
[Carrier readback](../out/guest-tree-erofs-image-readback/r-c06d34d3/receipt.json)
· [Held classpath inputs](../out/guest-classpath-selection/receipt.json)

The static library audit rechecked the 14 direct `app_process64` names,
the five direct linkerconfig generator names and 109 additional names from
the next dependency step against the scoped held files. A name match can
identify several distinct ELF objects. For example, the interpreter and
`/system/lib64/ld-android.so` have the same SONAME and different digests.
Actual namespace resolution requires the effective linker configuration,
partition view and active APEX directories from the same guest generation.
[Library evidence](../out/guest-entry-library-frontier/r-7288af31/receipt.json)

## Cleanup after a failed preparation start

The stage guard now records the exact retained controller's terminal result
during explicit cleanup. A failed begin can proceed only if that controller
proves no child was created and its owned references closed. A successful
begin still requires tree-local release, including when the subsequent Partial
receive fails. A missing control owner, reaped child without accepted rights,
or uncertain close cannot satisfy either path. Checking the guard's identity
does not poll the child.

The stage provider still rechecks the stage, content and guard, closes its
descriptors and verifies file-backed teardown before the guard can remove its
marker. A settled no-child case uses the existing never-began local terminal.
The original Prepare refusal remains intact.

The exact predecessor failed the new no-child regression. The revised guard
passed 27 modeled cases, including physical marker drift and removal errors.
The stage provider passed 18 modeled cases, including final source drift and
descriptor-close failure after confirmed no-child closure.
Its file-backed branch passed 23 modeled cases. The new cases cover clean
no-child closure, a backing teardown failure that keeps the guard, and refusal
of a no-child report after a successful begin.
The control fixture passed all 13 cases, including one that preserves the
original setup error while retaining HOLD after a socket close error.
The guard and both provider variants compiled to unselected Android AArch64
objects. This work establishes a local preparation cleanup path. Same-session
return, guest launch and authentication remain unverified.
[Guard model](../out/guest-tree-stage-guard-no-child/r-6732302b/receipt.json)
· [Stage provider model](../out/guest-tree-stage-provider/never-began-fixture-41d4a43b/receipt.json)
· [File-backed provider model](../out/guest-tree-file-stage-provider-review/r-poll-control-658ab4d6/receipt.json)
· [Control fixture](../out/guest-tree-control-owner-setup-uncertain/r-da742255/fixture.stdout)
· [AArch64 build](../out/guest-tree-stage-amended-arm64/r-188b933b/receipt.json)
