# Offline linkerconfig admission for ColorOS guest entry

The held profile remains blocked before guest exec. The verifier rechecked 15 saved inputs for `x9u-in-sultra` and observed zero entries at the extracted `/linkerconfig` and `/apex` targets. It found none of the selected fallback filenames under the extracted `/system/etc`. The cached `ld.config.oplus.txt` belongs to the OPPO extension. There is no held effective generated `ld.config.txt` with provenance for this entry view. The saved Samsung mount table identifies a host mount stack without supplying its config bytes. [Source and result pins](../inventory/guest-linkerconfig-inputs.json) · [Entry ownership](guest-entry-linker-proc.md)

The known executable is the original donor `app_process64`. Its `/system/bin/linker64` interpreter symlink targets the verified runtime APEX. The runtime and ART payloads, generator ELF, runtime APEX manifest and protobuf, donor system and product protobufs, and system public-library list are pinned inputs. The ART payload is a held library source. Its active alias and the rest of the effective APEX view remain to be selected. An executable and its direct library candidates cannot establish the namespace links or permitted paths the loader will use. [Donor runtime APEX proof](guest-runtime-apex.md)

## Producer profile required

AOSP's linkerconfig implementation takes an active APEX view, partition linker protobufs and runtime variables. It generates the base config and can generate per-APEX configs and an APEX library listing. The exact donor Android ELF accepts a short `-r` argument that its help omits. It canonicalizes the path with `realpath` and passes the result to variable loading, APEX scanning and partition input lookup. `--target` independently controls output paths. The input prefix leaves Android interpreter and property dependencies in place. [AOSP generator source](https://android.googlesource.com/platform/system/linkerconfig/+/refs/heads/main/main.cc) · [Donor option and call sites](../out/guest-tree-linker-inputs/donor-short-root-static-proof.json)

The AOSP linker chooses a config using the executable's location and available files, including a per-APEX config for an APEX executable, an architecture-specific file and the generated base file. It also has fallback behavior when it cannot load a usable config. This is a reason to verify the effective file rather than infer that a chosen text file controls the process. The exact OEM loader and selected root still need their own resolution proof. [AOSP Android 16 linker selection](https://raw.githubusercontent.com/aosp-mirror/platform_bionic/android-16.0.0_r1/linker/linker.cpp)

The next input profile needs the exact private partition and active APEX aliases, module manifests and consumed library lists, relevant property values and generation phase. Then it needs either a genuine generated capture tied to that same view, or a reviewed exact producer and reproducible invocation over those inputs. Verify the effective configuration files against the admitted executable and interpreter in that view before an owned read-only snapshot can be staged. A filename, placeholder, copied Samsung config, or AOSP reference alone cannot satisfy this check. The verifier admits no configuration from the present profile and emits no launch manifest.

## Packaged carrier readback

The bounded raw EROFS reader followed the carrier's `/tree` directory and
verified its selected directory entries, inode metadata and exact file bytes.
`/product` and `/system_ext` are genuine aliases into `/system`. The product
protobuf is present and zero bytes. The system_ext protobuf is absent, and
the empty `/vendor` ends the vendor and ODM lookups. All four `/system`
protobuf and library-list files match their source hashes.

For the ordinary `/system/bin/app_process64` path, the donor linker considers
`/system/etc/ld.config.arm64.txt` before the generated
`/linkerconfig/ld.config.txt`. Both are absent in the raw carrier. The
per-APEX branch uses the executable's path. The carrier's linker symlink into
the Runtime APEX does not select a per-APEX config for `app_process64`.
The raw `/apex` and `/linkerconfig` directories are empty. The mounted view
must supply its own active APEX metadata and generated outputs.
[Donor loader instruction proof](../out/guest-tree-linker-loader-selection-39249b5e/receipt.json)

The readback used 68,044 bytes of EROFS metadata and rechecked the carrier's
identity around the selected reads. It reused the prior whole-image hash.
Three model mutations were refused, covering a retargeted alias, a changed
protobuf and an unexpected directory entry.
[Readback tool](../tools/review_guest_carrier_linker_inputs.py) · [Receipt](../out/guest-carrier-linker-inputs-d0793e59/receipt.json) · [Checks](../out/guest-carrier-linker-inputs-d0793e59/checks.json)

## Active APEX XML

The donor scanner reads `apex-info-list.xml` after collecting the stable
directories. Missing or malformed XML makes the scan return an error. The
generator can continue to partition configuration while skipping
`SetApexModules`. A recognized empty XML root reaches a different path and
adds no metadata. A generated file can therefore exist without a successful
APEX scan.
[Donor reader](../out/guest-tree-linker-inputs/donor-apex-xml-reader-static-proof.json) · [Generator caller](../out/guest-tree-linker-xml-caller-c7d331f7/receipt.json)

The donor merges qualifying active rows by module name and copies their
partition values. A repeated active name can replace the previous partition,
and a name absent from the mount scan can enter the map. The XML comparison
requires the exact observed active name set and matches versions, source paths,
partitions and activation flags. It allows inactive rows to share the active
row's name and version when their source paths differ.

Six offline cases passed. The held Samsung list parses as 58 active and 25
inactive rows, and is refused when compared with a different observed module
set. The donor candidate XML is also refused as a runtime list. The comparison
checks content. A separate post-mount observer still needs to bind the XML file
and stable directories to the same retained guest occurrence before generation.
[Comparison tool](../tools/review_guest_apex_info.py) · [Test receipt](../out/guest-apex-xml-review-e52d6f63/receipt.json)

### Donor publication

The packaged donor `apexd` and its init service file match the held source
hashes. Both the bootstrap and normal init services run as `root:system`.
The exact producer serializes the activation result, opens the canonical
`/apex/apex-info-list.xml` directly with create and truncate flags and mode
`0644`, writes the XML and closes the descriptor. Bootstrap and normal startup
pass different row-selection arguments to the same writer. Init runs bootstrap
before its first linkerconfig pass and later starts the default service.
[Carrier readback](../out/guest-carrier-apexd-producer-09add2c7/receipt.json) · [Donor publication proof](../out/guest-tree-linker-inputs/donor-apexd-xml-publication-static-proof.json)

The activation callers continue without a separate successful-publication
result. `apexd.status=activated` cannot attest the XML's contents. The guest
owner needs the actual activation records and a readback after publication in
its own mount and property view. The held producer still needs its bootstrap
interpreter and libraries as well as the selected package and state inputs.

The held carrier contains the bootstrap interpreter and 32 regular library
candidates across `/system/lib64/bootstrap` and `/system/lib64`. Raw EROFS
readback matched the sealed donor plan and the independent extracted-tree
walk for all 17 direct dependency names and 15 additional names. Four
top-level bionic aliases point into the Runtime APEX and were recorded
separately. The bootstrap interpreter and the separate system file both
advertise `ld-android.so` with different bytes.
[Readback tool](../tools/review_guest_apexd_bootstrap_inputs.py) · [Receipt](../out/guest-apexd-bootstrap-inputs-d948fb34/receipt.json)

The exact bootstrap linker prepends `/system/lib64/bootstrap` when its
non-sanitized no-config branch encounters the canonical `/system/lib64`
directory. The `fix_lib_paths` comparison and insert are at `0xe4e24` and
`0xe4e60` in the pinned interpreter. Startup inserts the `get_libdl_info`
record under the interpreter's SONAME into the default namespace at
`0x1a0a84`, before dependency loading. The loaded-name check at `0xdd288`
precedes file search. Keep the `ld-android.so` file candidate separate from
that preloaded record. The guest's actual config, environment, library
resolution and producer launch still require evidence from the retained view.

### First linkerconfig invocation

Donor init calls `/apex/com.android.runtime/bin/linkerconfig --target
/linkerconfig` after bootstrap. The generator uses `/system/bin/linker64`,
whose target is the Runtime APEX interpreter. The Runtime interpreter tries
the per-APEX config before the architecture-specific and generated base
paths. With the donor's early `#` placeholder and those higher-priority
paths absent, its parser finds no section. Its ordinary no-config search
list starts with `/system/lib64`, followed by `/odm/lib64` and
`/vendor/lib64`. The bionic aliases in `/system/lib64` lead into the active
Runtime module. The default namespace already contains the Runtime
interpreter's own `ld-android.so` record when it begins dependency lookup.
[Donor init and generator pins](../out/guest-tree-linker-inputs/receipt.json) · [Held library origins](../out/guest-entry-library-frontier/r-7288af31/receipt.json)

The original generator's 186 symbol relocation sites cover 177 strong
imports and three weak imports. All strong imports matched the pinned
direct library candidates by symbol and required version. Versioned imports
also matched the specific library named in the version requirement. The
three weak imports had no match. The remaining 439 relative relocations
refer to no dynamic symbol. A separate read of the product `libbase.so`
found the same 19 imported names as in the system copy, despite different
bytes. The actual library origin therefore still depends on the effective
guest namespace. Transitive relocations and runtime resolution remain open.
[Import verifier](../tools/review_guest_linkerconfig_imports.py) · [Receipt](../out/guest-linkerconfig-imports-5e9f5762/receipt.json)

The first pass also needs a stable Runtime alias and the effective guest
values of `ro.vndk.lite`, `ro.vndk.version`, `ro.product.vndk.version` and
`ro.debuggable`. The donor exits early when `ro.vndk.lite` is exactly
`true`. Its APEX scan reads the stable directories' manifests and the
canonical XML. A generated base file can still exist after a failed scan,
so admission must verify the same-view manifest and XML inputs separately.

### First-pass property readback

The compiled donor property map routes all three VNDK keys to `vndk_prop`
and `ro.debuggable` to `userdebug_or_eng_prop`. The current seed stores
`ro.vndk.lite=false`. Neither version is stored. The donor's declarations
include `ro.debuggable=1`, but the seed has no debug context area. A missing
area cannot establish that the consumer saw an absent key.
[Donor context map](../out/guest-tree-property-info-full/donor-v1/receipt.json) · [Held seed](../out/guest-tree-property-areas/donor-v1/receipt.json)

The native reader validates the fixed lookups in two disjoint immutable
areas. It preserves raw strings and distinguishes absent keys from stored
empty strings. It rejects malformed reached records, unsupported long
records and aliased input or output buffers before publishing a sample.
All 35 existing release-parser checks and 19 new model cases passed. The
new cases include the held donor VNDK area and a modeled debug area. The
reader compiled as an unselected ARM64 object.
[Reader source](../compat/native/guest_tree_property_view.c) · [ARM64 and release regression](../out/guest-linkerconfig-properties-build/r-91642e8f/receipt.json) · [Four-key model](../out/guest-linkerconfig-properties-model/r-bd225a00/receipt.json)

The original generator treats missing and empty version strings as
undefined and still uses the unversioned LLNDK list. It tests the lite flag
against exact `true`; the debug flag uses libbase's boolean parser. The
readback leaves those decisions to the original consumer. The guest owner
must establish the actual mapped contexts and read access, exclude inherited
Samsung property areas and prove `BIONIC_APPCOMPAT_OVERRIDE` is absent for
this profile before relying on canonical key lookups.

The descriptor readback joins the visible `/dev/__properties__` directory
to the held guest root and verifies the four named files on that private
tmpfs. It requires the exact `property_info` digest and each leaf label,
then parses the same VNDK and debug bytes it hashes. The serial file must
have the donor's empty-area layout. The reader checks its digest again
after the context reads and rechecks every held and named identity before
publishing the sample. An unavailable debug area refuses the readback.
All 13 host cases passed with held map, VNDK and serial bytes and a modeled
debug area. They include a changed global serial with identical metadata,
stable malformed serial bytes and a late same-content inode replacement.
[Descriptor reader](../compat/native/guest_linkerconfig_property_readback.c) · [Combined ARM64 link](../out/guest-linkerconfig-property-fd-build/r-f15ccd02/receipt.json) · [Host model](../out/guest-linkerconfig-property-fd-model/r-4440d12d/receipt.json)

Serial equality checks drift. Bionic publishes property data before
incrementing the global serial, so equal samples alone cannot establish
writer exclusion. The owner still has to hold the directory label, final
reader credentials, and writer exclusion through use. The current staged
directory is `0500` and has five seed files. The readback expects the
consumer `0711` directory and an actual debug area. Its ARM64 link joins
the readback code without selecting or launching a guest.
[Staged property owner](../compat/native/guest_tree_property_child.c) · [Consumer label and mapping checks](../compat/native/guest_tree_property_labels.c)

The offline fixture builder rereads both pinned donor `ro.debuggable=1`
declarations, uses the existing bionic-area writer for the mapped debug
context, and advances the modeled global serial from nine to ten. An
independent decoder checked that the resulting area contains exactly that
one clean short record. The seven-source startup smoke passed all six
cases with the generated debug and serial files. The original five-file
seed also passed verification. The fixture does not establish an effective
guest value or make the staged property directory a consumer view.
[Builder](../tools/build_guest_linkerconfig_property_fixture.py) · [Fixture receipt](../out/guest-linkerconfig-property-fixture/r-0f7cbfa2/receipt.json) · [Native model rerun](../out/guest-linkerconfig-property-fixture/check-58272915/receipt.json)

### Readback from retained descriptors

The native reader borrows a held APEX directory and a read-only XML file. It
checks the fixed `apex-info-list.xml` name against the held file on the same
tmpfs before and after reading. It verifies the exact extent and EOF and
returns a digest only after both the file and directory pass the final checks.
Positional reads preserve the file offset. The reader opens and closes no
descriptors. Thirteen inert native cases passed, including refusal of a
same-size replacement, mount drift, early EOF and extra bytes. The updated
XML grammar fixture passed seven cases and rejects namespace declarations and
non-XML whitespace in the document layout.

This object check still needs the owner to prove that the directory is the
same guest's visible `/apex`, and that the file came from its activation
producer. The mount-only phase admits the alias directories and has no XML
descriptor to lend. The reader compiled as a separate Android AArch64 object.
[Native source](../compat/native/guest_apex_info_readback.c) · [ARM64 build](../out/guest-apex-info-readback-arm64/r-01465fbd/receipt.json) · [Native fixture](../out/guest-apex-info-readback-model-cce4bd1d/receipt.json) · [XML fixture](../out/guest-apex-xml-grammar-e83967ba/receipt.json)

The donor entry uses the same borrowed-object checks with a strict
`root:system` mode `0644` file profile. The original `root:root` entry keeps
its existing profile. The successor passed 18 inert cases, including
cross-profile refusal and a same-content inode replacement after EOF. Both
entries compiled to an unselected ARM64 object.
[Donor fixture](../out/guest-apex-info-readback-donor-model-3673faeb/receipt.json) · [Successor ARM64 build](../out/guest-apex-info-readback-arm64/r-3e306062/receipt.json)

The Runtime input reader borrows the same XML plus the stable
`com.android.runtime` directory, its manifest, its `etc` directory, and its
inner `linker.config.pb`. It verifies the fixed names and their held mount
and inode identities together before and after the reads. It requires the
exact 143-byte donor manifest digest and the two-byte inner config. The
inputs are pinned to the same Runtime EROFS payload. The result is published
only after all six identities and both Runtime file contents pass. The XML
bytes remain available in the caller's scratch buffer for the cohort check.
[Runtime payload pins](../out/guest-tree-core-apex-cohort/source-cohort.json) · [Reader source](../compat/native/guest_apex_info_readback.c)

The owner must still hold the actual guest mount and donor backing, settle
the publisher, and compare the XML to the complete active module set. The
inner config is a module input. The generated `/linkerconfig` output has a
separate producer and needs its own readback. The reader compiled as an
unselected ARM64 object. All 18 existing XML model cases and 12 Runtime
cases passed. A transient XML identity change between the outer and inner
samples failed the regression against the previous implementation and is
now refused before reading any file.
[Build and model receipt](../out/guest-apex-runtime-readback-build/r-dbc8d16a/receipt.json)

### Generated base and library list

The donor opens the final output paths separately and truncates in place.
The ordinary pass writes `ld.config.txt` before any per-APEX config, then
writes `apex.libraries.config.txt` last. It requests mode `0644`. Per-APEX
generation requires a visible module `bin` path. Runtime and ART have one
in the held source, and I18N does not. In the classic factory bootstrap
branch ART is outside the selected early set. The normal pass can include
it. The actual activation phase and mounts determine which files to expect.
The ordinary invocation can return successfully after a per-APEX or
companion write failure. An empty companion is also a legitimate result
when the complete selected input set contributes no rows.
[Donor generator and phase evidence](../out/guest-tree-linker-inputs/FINDINGS.md)

The native output reader borrows the guest root, the active
`/linkerconfig` directory, and its two fixed output files. It verifies
both held names and the mount from the guest root, reads both bounded
extents through EOF, and rechecks the whole group before returning either
digest. The base must have content beyond comments and whitespace. A
present empty library list has its own successful digest and extent.
The ARM64 build also reproduced the prior APEX readback object byte for
byte after sharing the identity checks. All 30 APEX regression cases passed.
All 16 output model cases passed, including same-content replacement after
both reads and an overmount hiding the held directory.
[Output reader](../compat/native/guest_linkerconfig_output.c) · [ARM64 and APEX regression](../out/guest-linkerconfig-output-build/r-0840bf59/receipt.json) · [Output model](../out/guest-linkerconfig-output-model/r-cc892c23/receipt.json)

The first-write check records the visible target and its exact single-byte
`#` placeholder while the companion name returns `ENOENT`. It rechecks the
absence and all held identities after reading the placeholder. After the
writer, the generated-pair reader checks those original root, target and
base identities before either output read. The base inode stays the same
because the donor uses `O_TRUNC`. Extents, timestamps and target directory
link counts can change between the two observations. A preexisting empty
companion and a later target overmount both fail this check. All 14 new
generation model cases and 16 existing output cases passed.
[First-write API](../compat/native/guest_linkerconfig_output.h) · [ARM64 and output regression](../out/guest-linkerconfig-generation-build/r-b9e098b1/receipt.json) · [Generation model](../out/guest-linkerconfig-generation-model/r-720b776e/receipt.json)

The held donor has no captured generated output. The owner must prove a
fresh target, one completed producer occurrence and exclusion of other
writers through use. It still has to verify the complete per-APEX output
set and the selected loader configuration. For `app_process64`, the
architecture-specific file takes precedence. A generated base that fails
parsing can also leave the loader on its default namespace path.
[Original loader selection](../out/guest-tree-linker-loader-selection-39249b5e/receipt.json)

### Ordinary app_process64 entry paths

The entry reader verifies the fixed `system`, `bin` and `etc` names under
the same retained carrier root as the generated pair. It requires exact
`ENOENT` for `ld.config.arm64.txt` before and after the reads. A symlink or
an inaccessible entry fails the check. The original loader tests the
architecture path first. It can follow a symlink during selection and then
fail the parser's nofollow open.

The reader matches the 51,880-byte donor `app_process64` and the 2,640,432-byte
Runtime `linker64` by digest. The carrier's `/system/bin/linker64` link must
contain the exact 38-byte target. The reader resolves the target's fixed
components separately under the held guest root and checks the stable
Runtime mount against the earlier APEX sample. It checks the generated
pair using the first-write sample and rechecks the complete executable path
afterward. The three native sources link into an unselected ARM64 library.
All 11 host cases passed with the pinned donor executables read as data,
including an override appearing late and same-content inode replacements.
[Entry reader](../compat/native/guest_linkerconfig_app_process.c) · [ARM64 link](../out/guest-linkerconfig-app-process-build/r-0d4cc835/receipt.json) · [Host model](../out/guest-linkerconfig-app-process-model/r-ddf33932/receipt.json)

The staged controller's mount code explicitly requires `noexec` on the
carrier and preserves it when cloning the root. The saved phone run verified
the regular carrier file on host F2FS and recorded zero nested isolated
mounts. The private EROFS root flags are therefore a source and model result.
[Carrier mount](../compat/native/guest_tree_file_erofs_mount.c) · [Root clone](../compat/native/guest_tree_root_attach.c) · [Phone staging result](../out/file-stage-live-staging/r-d3a9b960/result.json)

The entry reader now samples the mount flags on the two held executable FDs
before and after the joined readback. It requires read-only, nosuid and
nodev on both and reports separate bits when either leaf has `noexec` clear.
Stable `noexec` is a blocked execution observation. Changing a sampled flag
refuses the sample. This keeps the carrier app and the separate Runtime
interpreter distinct, even though the parent `/apex` mount can be noexec.
The ARM64 library relinked against the pinned API 31 `fstatvfs` interface.
All 32 host cases passed, including the original path checks, each leaf
permission combination, late flag drift and syscall errors.
[ARM64 link](../out/guest-linkerconfig-exec-mount-build/r-8ab1955d/receipt.json) · [Host model](../out/guest-linkerconfig-exec-mount-model/r-8bd594a1/receipt.json)

Guest entry still needs executable placement for the app and its mapped
libraries, actual access and SELinux behavior, the real `/proc/self/exe`
resolution and environment, and successful config parsing and namespace
selection.

### Generated system section check

The held ordinary generator emits `dir.system = /system/bin/` first,
then the rest of its directory mappings, then `[system]`. Its first default
search path is `/system/${LIB}`. The loader scans mappings in order before
the first section. It checks directory access, attempts `realpath` and uses
a slash boundary when matching the executable. It looks for the selected
section by exact name. A missing section can leave it on its built-in
configuration. Repeated `dir.system` rules for different directories are
valid, as are the writer's `+=` continuation lines.
[Held generator](../../firmware/donor/apex/005-com.android.runtime/files/bin/linkerconfig) · [Held Runtime linker](../../firmware/donor/apex/005-com.android.runtime/files/bin/linker64) · [AOSP format reference](https://android.googlesource.com/platform/bionic/+show/main/linker/ld.config.format.md)

The strict readback checks that first rule, one first `[system]` section,
the initial default search path, and any continuations that follow it.
It parses the same bounded bytes used for the base SHA-256. The combined
entry variant publishes the section and output only after the final file,
mount and architecture-override checks. The digest-only variants remain
available for inspection. The strict profile establishes the expected
text structure. The owner still has to verify directory resolution and
the original parser's effective namespace and library selection.
[Output reader](../compat/native/guest_linkerconfig_output.c) · [Joined entry reader](../compat/native/guest_linkerconfig_app_process.c)

The ARM64 link and 32 joined entry cases passed. The 35-case output model
also passed, including refusal of the held OPPO extension config, scratch
capacity failures before reading, and a late replacement with identical
bytes. The positive generated base was modeled. The held capture has no
actual generated base file.
[ARM64 and joined model](../out/guest-linkerconfig-system-section-build/r-6d021074/receipt.json) · [Output model](../out/guest-linkerconfig-system-section-model/r-a944b852/receipt.json)

### Same-guest startup observations

The coordinator borrows the property, APEX and first-write descriptors
under one guest root. Before generation it reads the properties and
Runtime/XML, then checks the untouched output target. It records the
retained slot identities and a digest of the fixed input metadata fields.
XML has separate scratch so the owner can compare the complete active set.

After the owner settles the exact generator, the coordinator checks the
generated system section and app entry, then rereads Runtime/XML and
properties. It compares the same input metadata and content digests across
generation. The final checks resample both executable-mount flags before
checking the held and named identities of all 22 roles and the absence of
an architecture override. This ordering catches a companion replacement
during the flag check. The base and target retain their first-write
identities while their generated metadata can change. Distinct roles
sharing the same device and inode fail even across distinct mount IDs.
The seven-source ARM64 link passed. A rerun of the host model with modeled
leaf readers passed 21 cases on the current coordinator.
[Coordinator](../compat/native/guest_linkerconfig_startup.c) · [ARM64 builder](../tools/build_guest_linkerconfig_startup.py) · [ARM64 receipt](../out/guest-linkerconfig-startup-build/r-509d9671/receipt.json) · [Model rerun](../out/guest-linkerconfig-startup-model/r-cc847c60/run.stdout)

The host smoke test linked all seven production sources and passed six
cases. It read the pinned donor ELF, Runtime configuration and property
seed bytes as data through modeled system calls. The generated configuration,
empty companion, XML and debug property were fixture inputs. The successful
case retained the interpreter-only execution observation. All five failure
cases preserved the caller's output, including the companion swap during the
last flag check and the duplicate inode through distinct mount IDs.
[Full host receipt](../out/guest-linkerconfig-startup-full-model/r-246e2ccc/receipt.json)

The owner still needs the correct generator occurrence, full active
APEX and partition inputs, effective consumer mappings, and exclusion of
other writers and path or mount changes through use. The coordinator
preserves both executable-mount bits as observations. The selected staged
property view and `noexec` carrier do not supply a runnable guest.

The retained controller currently stops at `Partial` and its child then
waits for cancellation. A later phase in the retained child would take the
baseline before the exact generator and read back after the producer and
its writers settle. The existing release owner can account for the
preparation child's exit. It has no generator occurrence or terminal
status to supply to this phase.
[Preparation child](../compat/native/guest_tree_control_owner.c) · [Release owner](../compat/native/guest_tree_release_owner.c)

### Executable mappings and root candidates

The executable-segment audit reread 45 exact donor ELFs. Each has a
nonempty, file-backed executable `PT_LOAD`. The counts below include the
entry and interpreter for each phase, plus the libraries in its held graph.
The ordinary donor loader maps executable DSO segments from their file
descriptors. The phase counts describe the pinned candidate origins.
Effective namespace selection and the app's transitive graph remain open.

| Startup phase | Carrier system | Runtime APEX | ART APEX |
| --- | ---: | ---: | ---: |
| Bootstrap `apexd`, held graph | 33 | 0 | 0 |
| First `linkerconfig`, provisional transitive graph | 3 | 5 | 0 |
| `app_process64`, provisional direct graph | 10 | 4 | 2 |

The physical system `ld-android.so` also has an executable segment. The
phase counts exclude it because the inspected loader branches reuse the
already-loaded interpreter under that SONAME. Independent LLVM checks
matched the segment coordinates for the five entry/interpreter objects
and the separate system stub.
[Executable-segment tool](../tools/review_guest_exec_mount_demand.py) · [Demand receipt](../out/guest-exec-mount-demand-ce69fa4f/receipt.json) · [Independent checks](../out/guest-exec-mount-demand-ce69fa4f/checks.json)

The file-backed EROFS controller verifies the exact donor-derived carrier
and holds it under a `noexec` preparation policy. Even the Runtime-hosted
generator has three carrier library mappings in its held graph. The legacy
loop-backed ext4 controller requests a read-only ext4 mount without
`noexec`. Its held input manifest identifies the same donor, while its
native admission checks a cached ID and current file identity. It also
stops at Partial and has no verified executable mount or entry handoff.
[File-backed controller](../out/file-stage-controller-successor-build/r-122795bb/receipt.json) · [Legacy ext4 build](../out/isolated-retained-view-controller/r-c88346bc/receipt.json) · [Legacy input check](../compat/native/guest_private_view_inputs.c)

The block-backed EROFS prototype verifies a supplied read-only block and
table sample. Its final link refused because the lifetime content and
mapping owner was unresolved. None of these prepared roots supplies an
admitted execution placement for the held startup graph.
[Block-backed link refusal](../out/tree-retained-controller/r-812c92f1/verify-final-link-refusal.stderr)

## Held classpath order

The nine-module classpath scenario adds seven pinned fragments and their JARs
to the earlier five-fragment scenario. It reproduces the earlier result first.
The exact donor bionic instruction anchors show that successful wildcard
matches are sorted by pathname bytes. The scenario then follows the donor's
separate boot and system-server scan patterns. ART's boot fragment appears
once even though it matches both the fixed and wildcard paths.
[Scenario tool](../tools/review_guest_classpath_frontier.py) · [Saved results](../out/guest-classpath-frontier-c7f081a6/receipt.json)

| Held release scenario | Boot | Dex2oat boot | System server | Standalone |
| --- | ---: | ---: | ---: | ---: |
| SDK 37, `REL` | 28 | 23 | 8 | 0 |
| SDK 36, `REL` | 23 | 19 | 8 | 0 |

The SDK 37 case includes `framework-virtualization.jar`. Its minimum SDK
excludes it at 36. These counts apply to the exact held candidates. Actual
guest classpaths still require the complete mounted APEX set and the effective
properties and libc seen by `derive_classpath`. The same stable directories
also need to pass the separate linkerconfig scanner's directory checks.

### Full factory donor scenario

The supplied image catalog and extraction inventory agree on 43 factory
APEX containers. The review matches each held payload to its ZIP member
and matches each payload's raw manifest to the packaged manifest. It
walks the fixed classpath directories directly in 34 Ext and nine EROFS
payloads. Manifest names supply the candidate aliases even where the
archive stem differs. The full scenario includes 46 APEX and two system
fragments with 86 distinct JARs. The review reads the Ext JAR bytes from
their original inodes and checks EROFS and system JARs against the held
extraction pins. [Factory reader](../tools/review_guest_classpath_factory.py) · [Factory receipt](../out/guest-classpath-factory/r-5bb77c65/receipt.json)

| Factory donor scenario | Boot | Dex2oat boot | System server | Standalone |
| --- | ---: | ---: | ---: | ---: |
| SDK 37, `REL` | 58 | 23 | 19 | 9 |
| SDK 36, `REL` | 51 | 19 | 18 | 9 |

`python -B tools/review_guest_classpath_factory.py --emit-exports 37`
emits the SDK 37 scenario as exact bytes. Its 5,674-byte fixture passed all
20 native environment model cases, including refusal when the nonempty
standalone value is cleared. The nine-module scenario remains the
separate held subset with an empty standalone value. The factory result
does not determine the active OneOS aliases. The held legacy path can
mix staged payloads with host APEX mounts. [Factory environment model](../out/guest-classpath-factory/r-5bb77c65/native-model.json)

### Conditional OneOS code 85 mix

The captured APK's 19 script rows and 30 selected package rows reproduce
the saved 49-row stage manifest digest. All 16 declared APEX payloads
match factory donor payload hashes and the stable names in the packaged
prepare script. Under a successful declared-mount scenario using the
held Samsung capture, 28 other stable aliases come from Samsung and 14
Samsung-named host aliases are excluded by the script. The review reads
the selected fallback fragments from the retained tar and rehashes all
36 referenced host JARs. [Selection and source evidence](../out/stock-oneos-classpath-mix/r-a268854f/receipt.json)

At SDK 37 `REL`, this projection yields 51 fragments and 89 distinct
JAR paths, with 60 boot, 23 dex2oat boot, 19 system-server, and 10
standalone entries. The prepare script also binds staged framework,
telephony-common, services, and Oplus services JARs over four existing
classpath paths. All four declared hashes differ from the donor bytes.
The saved stage observation verifies three hashes. The telephony JAR
still has selector evidence only. This makes file identity a separate
check even when all four exported strings match.

The scenario assumes the declared mounts and JAR binds succeed, the
held donor system fragments are visible, and the producer sees SDK 37
`REL`. It uses the historical Samsung capture for fallbacks. The live
stage snapshot establishes the selected manifest and three JAR hashes.
The active aliases, resolved JAR bytes, and effective consumer environment
still need observation in the same retained guest. [Scenario reader](../tools/review_stock_oneos_classpath_mix.py) · [Saved stage observation](../out/live-stage1-stock-stage-binding/r-ab3223b1/receipt.json)

### Classpath JAR identity

The native JAR observer covers the held `/system/framework` and stable
`/apex/<module>/javalib` path shapes. It borrows the root, exact parent
directories and read-only JAR descriptor. Each held node must match its
visible name under the previous held directory. Each mount ID must match
the caller's admitted view. The file must also match the independently
held backing device and inode, size and digest. The reader hashes through
EOF with positional reads and checks the full name and identity chain
again before returning a sample.

A host model passed 23 cases with the actual reader and simulated
filesystem calls. It accepts an explicitly selected file-bind mount and
a stable APEX JAR path. It refuses the wrong mount or backing inode even
with the expected bytes, and catches late replacements of the file and
its ancestors. [Host model](../out/guest-classpath-jar-readback-model/r-98e2b034/receipt.json)

A separately admitted file bind can have its own mount ID while keeping
its backing device and inode. The caller still proves that the source
name belongs to the correct stage or APEX and holds the view and writers
through use. A full launch check must retain the deduplicated cohort and
rejoin it after classpath generation, before validating the final
environment. The linked ARM64 reader remains unselected.
[Native reader](../compat/native/guest_classpath_jar_readback.c) · [ARM64 receipt](../out/guest-classpath-jar-readback-build/r-2473bdb4/receipt.json)

A separate host model streamed the actual 52,377,761-byte staged
framework JAR as inert data. It verified its exact digest and EOF through
the simulated file-bind view. [Held large-file receipt](../out/guest-classpath-jar-readback-held-large-model/r-033756f7/receipt.json)

### Joined classpath launch readback

The coordinator matches the four ordered exports to the exact unique JAR
path set. It allows one path to serve multiple categories and rejects
duplicates within a category. It hashes each named and held JAR once,
retains a fingerprint of its full metadata chain, and brackets the fresh
output baseline. After generation it compares the published bytes against
the original export digest, rejoins all JAR and final file identities, and
checks the proposed final environment. The rechecks read metadata only.
[Coordinator](../compat/native/guest_classpath_launch_readback.c) · [Combined ARM64 build](../out/guest-classpath-launch-readback-build/r-7b9ad9d3/receipt.json)

The roster checker accepted the two factory scenarios and the conditional
89-path code85 mix. It refused omitted, extra, duplicated and malformed
paths. The combined model linked the actual five C units and passed 12
cases with simulated filesystem calls. It caught later same-byte name
replacement, an unchanged inode with a later ctime, and temporary-name
creation during the last export stat. It also checked one content read
per distinct JAR and zero JAR rehashes at finish.
[Held roster model](../out/guest-classpath-launch-roster-model/r-85062bd6/receipt.json) · [Combined model](../out/guest-classpath-launch-readback-model/r-460730eb/receipt.json) · [Late-race checks](../out/guest-classpath-launch-readback-model/late-4db85220/receipt.json)

The retained launch owner still has to acquire the active inputs, settle
the exact producer and keep descriptors, names and bytes stable through
exec. Sequential metadata checks supply drift evidence under that
ownership. The combined build remains unselected.

### Held subset export comparison

The offline scenario now matches only visible direct `/apex` children,
skips numeric version aliases and preserves the fixed ART path's single
visit. The held profile checks contiguous protobuf ordinals across both
categories in each fragment, and rejects a JAR outside its declaring APEX
before SDK filtering. The saved two-SDK receipt still reproduces byte for
byte. [Focused tests](../tools/test_review_guest_classpath_frontier.py)

Use `python -B tools/review_guest_classpath_frontier.py --check-exports <file> --sdk 37`
to compare a file as bytes against the held SDK 37 `REL` scenario. The
comparison follows the donor's four fixed `export` lines and preserves
colon-delimited JAR order. A present-empty standalone list includes its
export line and the space before LF. The donor init parser preserves that
empty value, whereas an omitted key leaves an inherited value in place.
Both held scenarios passed. Six altered exports refused, including a
same-length reorder and a missing empty export.
[CLI evidence](../out/guest-classpath-export-check/r-1ed0aa33/receipt.json)

The donor generator writes a temporary file and renames it into the final
`/data/system/environ/classpath` path. The native observer checks that
`classpath` and `classpath.tmp` are absent before generation. It rejoins
the same retained guest root and data, system, and environ directories
after generation, with the output file on that same private data mount.
It compares the final named and held file before and after bounded
positional reads, matches the supplied expected bytes through EOF, and
requires the temporary name to remain absent. The strict fresh profile
uses the donor's system-owned `0775` and `0700` directories, and a `0600`
output from the writer's `0666` request under stock init's `0077` umask.
The native reader linked for ARM64. All 13 host-model cases passed with
simulated filesystem calls, including stale or replaced final files with
identical bytes, temporary residue, and late extent drift.
[Native reader](../compat/native/guest_classpath_readback.c) · [ARM64 receipt](../out/guest-classpath-readback-build/r-91e92cbe/receipt.json) · [Host-model receipt](../out/guest-classpath-readback-model/r-e2780985/receipt.json)

The retained owner must still provision the private data directories,
hold the labels and exclude other writers, and settle the exact SDKext
producer before opening the final name. That producer runs after normal
APEX/linker configuration and `derive_sdk`, before init loads the four
exports and starts `art_boot`. A matching file provides no proof of the
effective environment. The legacy OneOS fallback can preserve Samsung's
inherited values when the guest generator fails.
[Producer instructions](../firmware/samsung-boot-classpath-cohort/producer-native.json) · [Legacy launcher](../firmware/installed-oneos-code-profile/static/assets/guest_start.sh)

### Child classpath environment

The native environment projection ties its input length and SHA-256 to
the file readback sample, checks the four fixed LF-terminated export rows,
and copies four literal `KEY=value` strings into caller-owned storage.
The launch-side check compares those values with the proposed bounded
`envp`, including exact JAR order, a readable terminating null pointer,
and exactly one entry for each of the four keys. A present-empty value is
an explicit `KEY=` entry. The checker never loads the file into the process
environment. [Projection and check](../compat/native/guest_classpath_environment.c)

The held SDK 37 export passed 20 host cases. They cover omitted, stale,
reordered, duplicate and malformed values and a projection round trip.
The combined file-to-environment model passed 13 cases using the actual
reader and projection with simulated filesystem calls. Its successful file
readback sample accepts the projected explicit empty value and refuses
the same vector with that key omitted or replaced by an inherited value.
[Environment tests](../out/guest-classpath-environment-model/r-8c88b555/receipt.json) · [Joined model](../out/guest-classpath-environment-model/join-c9385d69/receipt.json)

The held OneOS `zygote_exec` rebuilds `envp` and omits empty classpath
values. A match on the wrapper's input therefore cannot attest to the
`app_process64` environment. The future retained launch owner must carry
the admitted file occurrence and the immutable strings through final exec
and independently check all remaining environment values and controls.
[Held launcher profile](../out/guest-entry-exec-profile/PROFILE.md#exact-replacement-environment) · [Combined ARM64 build](../out/guest-classpath-environment-build/r-b0d901e0/receipt.json)

### Direct entry vectors

The joined finish path now builds a fixed `app_process64` argument and
environment vector from its own local file readback sample. It preserves
the held launcher's argument order and takes an explicit JIT choice.
The 16 environment entries use the ten held path defaults, two socket
slot names and all four verified classpath values, including `KEY=`.
This intentionally excludes ambient overrides that the stock wrapper can
inherit. The caller keeps the returned vectors and their backing buffer
stable through exec and uses separate scratch for another attempt.
[Vector builder](../compat/native/guest_zygote_vectors.c) · [Joined finish](../compat/native/guest_classpath_launch_readback.c)

The six-source ARM64 link passed. The combined model passed 17 cases
with simulated filesystem calls, including both JIT modes, an ignored
ambient classpath, and a late same-byte export replacement that left the
result unpublished. The held subset and mixed export fixtures also passed
exact vector checks with modeled file samples, including empty and
nonempty standalone values. The fixed directory values, private socket
descriptors, executable placement and final process lifetime remain
launch-owner obligations. This build is unselected.
[ARM64 receipt](../out/guest-classpath-launch-zygote-build/r-522ba512/receipt.json) · [Combined model](../out/guest-classpath-zygote-vectors-model/r-c3c6cc88/receipt.json) · [Held vector checks](../out/guest-zygote-held-vector-model/r-e5bb0e7d/receipt.json)

### Listener descriptor readback

The native observer rejoins the held guest root, `dev` and `socket`
directories by name and mount. It checks that slots 3 and 4 are
inheritable, blocking, listening Unix stream sockets, each with the
expected pathname address and kernel cookie. It separately verifies both
filesystem socket nodes as `0660` root:system on the selected private
mount with their expected inodes. It resamples both parts before success.
The address check uses the exact length including the terminating NUL.
[Socket observer](../compat/native/guest_zygote_socket_readback.c) · [Linux pathname address handling](https://github.com/torvalds/linux/blob/v6.12/net/unix/af_unix.c)

The actual observer passed 23 host cases with simulated filesystem and
socket queries. The cases cover swapped slots, non-inheritable or
non-listening descriptors, bad addresses, wrong mounts and inodes, and
late pathname or endpoint-cookie substitution.
[Socket model](../out/guest-zygote-socket-readback-model/r-ce218044/receipt.json)

The owner must record the endpoint cookie and pathname inode from the
same exclusive creation and keep both stable through exec. A bound
address can outlive its current pathname, and the endpoint identity is
separate from the filesystem node. The preparation child still supplies
the empty directory only. The ARM64 build includes the socket and stdio
observers alongside the direct-entry vector code. The linked library
imports no socket creation, connection or mutation function.
[Private directory source](guest-private-dev-skeleton.md) · [Stdio observer](guest-zygote-stdio.md) · [ARM64 receipt](../out/guest-zygote-descriptor-readback-build/r-1232efa8/receipt.json)

### Private listener owner

The unselected creation code requires the final child already rooted at
the retained guest, with its private writable `nosuid,nodev,noexec` tmpfs
and distinct host `/dev` device and mount witnesses. It checks stdio,
vacant listener slots and absent names before reserving one attempt. It
acquires both listeners with close-on-exec set, restores the prior umask
after each bind, and changes the group on the held socket node. It
verifies the pair before publishing its cookie and inode pins.
[Owner source](../compat/native/guest_zygote_socket_owner.c)

A partial attempt retains the acquired descriptors and retires the view
for the caller. Local close consumes each owned descriptor once and
retains any close error. The owner never removes a pathname or replaces
an occupied descriptor. Whole-view disposal still needs the exact child,
all inherited references and the private mount accounted for.

The ARM64 link includes the actual stdio and socket observers. The host
model passed 20 cases with simulated syscalls and stdio, including
refusal of a host-device clone, failure on the second bind, and sticky
close errors. The current preparation child still has no rooted launch
callsite for the owner. Private socket creation, effective labels and
final inheritance remain unobserved on Android.
[ARM64 receipt](../out/guest-zygote-socket-owner-build/r-5b01b6ab/receipt.json) · [Host model](../out/guest-zygote-socket-owner-model/r-e43243d6/receipt.json)

### Child process root entry

The unselected entry step joins the child's current mount namespace to its
held NSFS descriptor and requires a distinct held parent mount namespace.
It joins the actual `/` to the inherited root opened after the namespace
clone and checks the separate prepared root by mount and backing device.
After changing cwd to the held guest root, it rechecks the namespace,
inherited root and new cwd before making the guest the process root.
Success requires both `/` and `.` to resolve to that exact held guest root.
Any failure after the first cwd change is attempted retires the attempt,
preserves the error and leaves disposal to the child owner.
[Root-entry source](../compat/native/guest_zygote_root_entry.c)

The selected child reports Partial from its inherited root, which the
parent checks through the exact child. A future entry callsite belongs
after that acknowledgment and before creation of the private listeners.
The callsite must own the child's exclusive filesystem and descriptor
state, reobserve the entered child from the parent, and dispose of all
outside-root handles before exec. The current child still accepts only
cancellation. The ARM64 build links the entry step with the listener
owner and verifiers. Android policy, executable placement and the launch
handoff remain unverified.
[Child control](../compat/native/guest_tree_control_owner.c) · [ARM64 receipt](../out/guest-zygote-root-entry-build/r-39870004/receipt.json)

The host model passed 21 cases with simulated syscalls, including a
same-device clone, namespace drift before root entry, partial cwd and
root changes, and separate final root and cwd mismatches.
[Host model](../out/guest-zygote-root-entry-model/r-b0ef9f37/receipt.json)

### Combined child preparation

The unselected child coordinator derives the root and socket inputs from
the same seven-role GTC view. Before any change, it checks the parent,
vacant FDs 0–4 and the held null FD against the actual inherited
`dev/null` name and mount. This supplies the inherited `/dev` mount and
device witness for excluding it during private listener setup. The private
`nodev` tmpfs supplies the socket names. Stdio uses the already opened
inherited null description.

The coordinator enters the exact guest root, installs the shared null
description into vacant stdio slots, then creates the two private
listeners. It rechecks stdio and the parent before publishing child
preparation. Failures after the attempt starts retain the component
states and owned listener descriptors for retirement of the same child.
[Coordinator](../compat/native/guest_zygote_child_prepare.c) · [Stdio installer](../compat/native/guest_zygote_stdio_owner.c) · [ARM64 receipt](../out/guest-zygote-child-prepare-build/r-744a836a/receipt.json)

The combined host model links all six production C units and passed
13 cases with simulated syscalls. A root refusal prevents stdio and
listener setup. A failed second stdio duplication retains the first
installed slot. A failed second bind retains both listener FDs for
retirement. The model also checked parent loss after root entry and
after listener creation.
[Combined host model](../out/guest-zygote-child-prepare-model/r-4cb9980e/receipt.json)

The selected control path can allocate witnesses into slots 0–4 and
accepts only cancellation after Partial. An entry callsite needs owned
FD placement and a bounded continuation after parent adoption. It must
prove exact child retirement and close the remaining outside-root
references. Executable placement, generated linker configuration,
classpath and actual startup require their own admission.
[Current control path](../compat/native/guest_tree_control_owner.c)

### Startup slot reservation

The slot owner checks the four child-owned control and witness FDs, and
refuses any other occupant of slots 0–4. It duplicates low owned cells
above 4 before consuming their original slots. A fresh CLOEXEC pipe and
copies of its read end fill the five low slots without replacing an
occupant. Release checks all five identities and directions before
closing any reservation. A failed close retires the child and preserves
the error without retrying the consumed FD number.
[Slot owner](../compat/native/guest_zygote_slot_owner.c)

The host model passed 11 cases with simulated descriptor operations,
including a foreign low occupant, partial relocation, a later pipe
identity mismatch, and uncertain close. A separate ARM64 relocatable
build calls the owner after the real controller's initial sweep and
before filesystem preparation, then uses the relocated child cells.
The overlay inverts to the pinned source and retains the CANCEL-only
protocol. It has no release or root-entry call and remains unselected.
[Host model](../out/guest-zygote-slot-owner-model/r-85356f43/receipt.json) · [Controller build](../out/guest-zygote-slot-control-build/r-34951002/receipt.json)

### Slot-release acknowledgment

The unselected controller and provider use a distinct private v6 wire
with the existing fixed packet size and kernel credential checks. The
controller adopts the seven original Partial FDs and retains the exact
observation. The provider then re-admits the source before asking the
controller to send one zero-rights release request. A successful child
reply follows verified closure of all five reservations and echoes
that original view. The provider re-admits the source again before
publishing its observation.

Both sides use the original deadline. An observed endpoint cutoff,
unexpected rights, a failed close, a missing reply or a mismatched
observation prevents provider publication. Stop and reap retain the
original GTR custody. The child accepts cancellation after reporting
release. This phase does not run root entry, stdio setup or a listener.
[Source composer](../tools/compose_guest_zygote_slot_release.py) · [ARM64 controller and provider object](../out/guest-zygote-slot-phase-build/r-13a290d7/receipt.json)

The parent host model passed 25 cases through the actual staged wire
helpers with simulated transport and child state. The child model
passed 17 cases against the exact release helper with simulated slot,
clock and send operations. These are separate endpoint models.
[Parent model](../out/guest-zygote-slot-phase-model/r-8054c880/receipt.json) · [Child model](../out/guest-zygote-slot-child-phase-model/r-891f01ad/receipt.json)

### Child startup preparation handoff

The unselected v7 successor retains the original pre-entry Partial
verification, GTR adoption and provider source re-admission. Its single
preparation request opens and verifies an inherited null description
while slots 0–4 are still reserved. The null owner pins the fixed
`dev/null` node and verifies the child's procfs view before reopening
the same object read-write. The child releases the slot reservations,
enters the guest root, installs stdio and prepares the private listeners.
It closes the extra null FD before reporting preparation.
[Null owner](../compat/native/guest_zygote_null_owner.c) · [Controller composer](../tools/compose_guest_zygote_child_phase.py)

The child echoes the admitted pre-entry observation and returns to
waiting for cancellation. This echo identifies the occurrence. Failed
preparation or missing acknowledgment goes through the existing
exact-child retirement path.
The ARM64 relocatable links the actual preparation units and has no
entrypoint. The null-owner model passed 18 cases with simulated syscalls.
[ARM64 receipt](../out/guest-zygote-child-phase-build/r-3794aebf/receipt.json) · [Null model](../out/guest-zygote-null-owner-model/r-387f3f6a/receipt.json)

Separate host models passed 25 parent cases through the actual wire
helpers and 20 child cases against the exact preparation-phase helper.
They exercise refusal of a stale v6 reply, timeout and peer loss, partial
ownership retention, and the acquisition, release, preparation, close
and acknowledgment order. Transport and leaf effects are simulated.
[Parent model](../out/guest-zygote-child-phase-parent-model/r-11923e85/receipt.json) · [Child model](../out/guest-zygote-child-entry-phase-model/r-99d12b38/receipt.json)

Before selecting a launch path, account for the remaining retained
outside-root roles and validate executable placement. The outer
controller's synchronous provider call has host cutoff checks at its
boundaries. The private child phase checks its own peer and absolute
deadline across preparation.
[Outer controller](../compat/native/retained_root_handoff.c)

### Independent parent readback after preparation

The research controller accepts the exact v7 reply, then asks the sole
waiter to verify its still-owned child. GTR keeps the adopted root and
namespace FDs private. It checks liveness before sampling and again
after the temporary descriptors have closed. GTC checks the original
deadline before returning to the provider's final admission check.

The reader checks procfs and its parent PID projection, then opens the
exact child task's fixed `root`, `cwd` and `ns/mnt` links. Root and cwd
must match the adopted guest directory's mount, device and inode. The
namespace must match the adopted typed mount namespace. A refused read
or uncertain temporary close withholds the result and invokes the
existing stop path. This sample covers root, cwd and namespace. Listener
endpoint checks remain in the child.
[Parent reader](../compat/native/guest_zygote_parent_readback.c) · [Source composer](../tools/compose_guest_zygote_post_entry.py) · [ARM64 receipt](../out/guest-zygote-post-entry-build/r-5b272267/receipt.json)

The reader passed 20 host model cases, the sole waiter passed 22 cases
with the reader simulated, and the controller passed 29 cases with the
waiter boundary simulated. The cases cover proc PID mismatch, stale
root, cwd or namespace, child loss, deadline and uncertain close. The
object is relocatable. Android proc access and post-entry behavior
remain unverified.
[Reader model](../out/guest-zygote-parent-readback-model/r-ee5953ae/receipt.json) · [Waiter model](../out/guest-zygote-gtr-post-entry-model/r-ff0bdd41/receipt.json) · [Controller model](../out/guest-zygote-post-entry-integration-model/r-024a3d90/receipt.json)

### Construction scratch retirement

The unselected typed child-view builder records the 24 retained
construction handles at their acquisition sites. This includes the
attached clone handle and preserves the separately reopened guest root.
After the final local view observation, the close helper validates the
complete roster against the exact control FD, three witnesses and seven
report rights. It closes the construction handles in reverse order
while slots 0–4 remain reserved. The child checks its parent again
before returning the seven rights for independent parent verification.

A close error consumes that cell once and leaves the remaining child
handles for retirement. The original error survives builder cleanup.
The controller sends its existing error frame instead of Partial. If
the parent reaps the child before adopting the seven rights, the stage
guard still holds the backing. This phase retires construction handles
and keeps the explicit report roles for later preparation.
[Close helper](../compat/native/guest_zygote_view_scratch.c) · [Source composer](../tools/compose_guest_zygote_view_scratch.py)

The ARM64 relocatable resolves both the typed builder and the close
helper. The close model passed 13 cases with simulated FD operations,
including a bad roster entry and a failure after earlier close calls.
The staged builder finalization model passed six cases and checked all
24 acquisition registrations. It verifies that observation, close and
the final parent check precede publication, and that cleanup preserves
the original errno on refusal.
[ARM64 receipt](../out/guest-zygote-view-scratch-build/r-533194f2/receipt.json) · [Close model](../out/guest-zygote-view-scratch-close-model/r-8468f95b/receipt.json) · [Finalization model](../out/guest-zygote-view-scratch-finalization-model/r-fb51c3ef/receipt.json)

### Retire the child-side preparation witnesses

The v7 research successor closes the extra null FD after preparation.
It then checks the rooted child, stdio and listener owner states, and
validates the 11 distinct high CLOEXEC FDs and the exact guest view
behind the socket owner. It consumes the child's inherited root,
namespace, native data and mirror FDs and the three relocated
witnesses. The child keeps control, its guest root, dev and socket
directory FDs, and startup slots 0–4.

A failed close consumes that cell once and prevents a preparation
reply. The same child retires through the existing stop and reap
path. The parent owns separate SCM_RIGHTS copies for its independent
readback and later closure. The successful reply still carries the
original scalar observation after a final peer and deadline check.
[Retirement helper](../compat/native/guest_zygote_child_retained.c) · [Source composer](../tools/compose_guest_zygote_child_retained.py)

The ARM64 relocatable resolves the retirement call. The retirement
model passed 20 cases with simulated FD operations. The modeled cases
include wrong readiness, overlap with a retained role, incomplete
closure and retry after a close error. The staged child phase passed
24 cases with simulated operations, including partial retirement and
peer or deadline loss after all seven closes. The entry executable
and its mapped libraries still require admitted executable placement.
[ARM64 receipt](../out/guest-zygote-child-retained-build/r-ac1b0146/receipt.json) · [Retirement model](../out/guest-zygote-child-retained-model/r-24475098/receipt.json) · [Child phase model](../out/guest-zygote-child-retained-phase-model/r-ab35736f/receipt.json)

### Early native executable placement

The pinned early placement profile covers 33 bootstrap files on the
carrier and eight first-linkerconfig files. Five of the latter belong
to Runtime. The other three are the carrier's `libbase.so`, `libc++.so`
and `liblog.so`, shared with the bootstrap set. A fresh PC parse of the
donor ELF bytes reproduced the complete demand receipt and the generated
pin header. The phases contain 38 distinct regular files.
[Demand receipt](../out/guest-exec-mount-demand-ce69fa4f/receipt.json) · [Profile generator](../tools/build_guest_native_exec_placement_profile.py) · [Profile receipt](../out/guest-native-exec-placement-profile/r-078191c7/receipt.json)

The readback borrows the exact phase directories and already-open files.
It checks held and named identities, exact bytes and stable mount
flags on the EROFS carrier and Runtime mounts. Bootstrap uses its
regular carrier interpreter. The generator uses the carrier's exact
interpreter and three Bionic symlinks to join the corresponding
Runtime paths below the admitted `/apex` tmpfs. The noexec bitset
records each blocked file in profile order. The selected carrier's
noexec policy covers the bootstrap set and the three carrier objects
in the generator set.
[Placement reader](../compat/native/guest_native_exec_placement.c) · [Carrier mount policy](../compat/native/guest_tree_file_erofs_mount.c)

The Android 31 ARM64 relocatable links the reader and real SHA-256
implementation with the pinned profile. The PC model passed 22 cases
using the actual donor files read in place, with simulated path and
mount observations. It reported `0x1ffffffff` for the noexec bootstrap
carrier, `0xe0` for the three first-linkerconfig carrier files with an
executable Runtime mount, and zero for a hypothetical fully executable
placement. Bad bytes, alias substitution and late identity or mount
flag changes refused publication.
[ARM64 receipt](../out/guest-native-exec-placement-build/r-483ec817/receipt.json) · [PC model](../out/guest-native-exec-placement-model/r-14d1279d/receipt.json)

This readback needs the independently retained phase view. Genuine
bootstrap, complete APEX and property inputs, loader search selection
and execution policy still require their own evidence. The
`app_process64` demand receipt covers direct candidates only.

### Early loader configuration and search inputs

For the held ordinary bootstrap linker, the architecture config
precedes the visible base config. The first Runtime generator also
checks its own per-APEX config before those two candidates. Both
phases need the visible `/linkerconfig/ld.config.txt` placeholder.
The raw carrier has an empty output directory. Donor init writes
`#` to its bootstrap placeholder and bind-mounts that directory
before bootstrap and the first generation call.

The authored target seeder consumes the already-admitted private tmpfs
at that visible name. It checks the complete empty directory, exclusively
creates the fixed file, corrects a restrictive umask on the created FD,
and writes one byte. It verifies a read-only reopen of the same inode,
closes the writer, and calls the existing generation reader before
transferring the read-only FD. The final directory contains only the
placeholder. The caller retains the root and target, including on
failure, when the target may require retirement. The seeder supplies the
first-generation baseline only. Placement of the private tmpfs and the
later default config view remain separate.
The same authored code linked for ARM64 API 31 and passed 14 host cases
against the actual baseline reader with modeled filesystem calls.
The cases cover stale identities, unexpected names, an exclusive
create collision, a short write, restrictive umask and failed mode
correction, failed close, and a late companion file.
[Target seeder](../compat/native/guest_linkerconfig_seed.c#L83) · [Baseline reader](../compat/native/guest_linkerconfig_output.c#L259) · [ARM64 link](../out/guest-linkerconfig-seed-build/r-f267eb06/receipt.json) · [Host model](../out/guest-linkerconfig-seed-model/r-1c5d74e8/receipt.json)

#### Private bootstrap target in the research child

The unselected v7 derivative leaves initial Partial verification ahead
of any new mount. After authenticated child preparation enters the
private root and closes the extra null FD, the target owner borrows the
admitted guest root. It joins the covered `linkerconfig` directory
to that exact EROFS mount and attaches a writable tmpfs using only
held descriptors. It reopens the fixed name, checks the detached and
visible identities and the `nosuid,nodev,noexec` flags, then calls the
existing seeder. The configured limit is 8 MiB and 64 inodes. This is
a prototype capacity, with the donor's full output requirements open.
[Fixed target owner](../compat/native/guest_linkerconfig_target.c) · [Exact controller composition](../out/guest-zygote-linkerconfig-target-source/r-cbd8a258/receipt.json) · [ARM64 link](../out/guest-zygote-linkerconfig-target-build/r-19959000/receipt.json)

The child keeps the two new FDs private for the bootstrap baseline
and closes them on normal cancellation. A refusal enters the existing
error and exact-child retirement path. The caller owns the exclusive
private namespace and its immutable carrier. The existing preparation
reply carries no target FDs. The donor's later default view has its
own placeholder, bind and generator occurrence.
The 28-case host phase fixture checks the exact controller source with
a modeled target hook. It covers target refusal and loss of the parent
or deadline before acknowledgement.
A separate 14-case host fixture checks the actual target owner with
modeled filesystem calls and seed handoff. It verifies FD-only
attachment order and refusal on stale cover, flags, identity, seed
or close failures.
[Child phase model](../out/guest-zygote-linkerconfig-target-phase-model/r-a02f2c96/receipt.json) · [Target model](../out/guest-linkerconfig-target-model/r-509ac4f7/receipt.json)

#### Parent verification of the parked target

The unselected v7 observer reuses the existing bounded proc mountinfo
reader with the authenticated child task FD. The parent opens the
target and base from the already verified live child root. It matches
the projected EROFS root and direct private tmpfs rows by mount ID
and device, and refuses stacked or nested target mounts. It checks
target flags through the held FD and the mount row. It samples the
rows again after verifying the exact `#` and absent companion with
the existing generation reader, then rechecks the held and named
nodes.

The parent closes its temporary target and proc handles and freshly
follows the same child's root, cwd and namespace links. The GTR
sole-waiter liveness bracket and GTC deadline still enclose the
observation. Mount table allocations are freed even on a parse or
profile refusal. A close error remains in the owner's sticky cell.
This checks the visible baseline. The existing reply does not carry
the child's retained target identities, and actual generation,
device mount verification and shutdown remain separate.
The ARM64 link resolves the observer and shared reader inside the
controller object. Thirteen host cases use the actual mountinfo parser
and generation reader with modeled filesystem calls. They cover late
row drift, stale names, invalid topology and close uncertainty.
Twenty-seven wrapper cases cover the original checks plus observer
refusal, close uncertainty and drift in each freshly followed link.
[v7 parent observation](../out/guest-zygote-linkerconfig-parent-build/r-c7dcc550/src/guest_linkerconfig_parent_readback.c) · [Exact source composition](../out/guest-zygote-linkerconfig-observation-source/r-bc50b2c4/receipt.json) · [ARM64 link](../out/guest-zygote-linkerconfig-parent-build/r-c7dcc550/receipt.json) · [Observer model](../out/guest-linkerconfig-parent-readback-model/r-93f741be/receipt.json) · [Wrapper model](../out/guest-zygote-linkerconfig-parent-wrapper-model/r-858ff6cd/receipt.json)

#### Prepared target descriptor transfer

The unselected GTZ v8 controller uses the same 200-byte private frame
and a new magic and version. Partial carries its original seven rights.
The prepared reply carries exactly two SCM copies in directory, base
order. Commands and errors carry zero rights. The child checks the
original descriptor slots and CLOEXEC before sending. The parent
receives with `MSG_CMSG_CLOEXEC` and authenticates the exact child
and the original observation.

The parent verifier borrows that actual pair through the sole waiter.
It matches each descriptor to the fixed name under the independently
verified live root, checks directory and base status flags, and reads
the one-byte seed through the received base. The child retains the
original descriptions. The parent closes every installed copy on
success or refusal before its final liveness and deadline checks.
Uncertain closes remain sticky and preserve an earlier primary error.
This establishes the intended preparation custody in the research
source. The real generator and the device runtime remain separate.
The 26 descriptor cases include same-byte substitutions and wrong
status flags. The 41 parent transport cases exercise wrong counts,
malformed ancillary messages, stale versions and peer credentials,
as well as close failures and child exit after close.
The 36 child cases check actual send framing with a modeled socket,
including original descriptor flags, ancillary length and order, and
short sends.
[Exact GTZ v8 source](../out/guest-zygote-linkerconfig-rights-source/r-cb936e85/receipt.json) · [Borrowed descriptor reader](../compat/native/guest_linkerconfig_parent_readback.c) · [ARM64 link](../out/guest-zygote-linkerconfig-v8-build/r-8efb68bc/receipt.json) · [Borrowed descriptor model](../out/guest-linkerconfig-parent-readback-model/r-4c8ae713/receipt.json) · [Parent transport model](../out/guest-zygote-linkerconfig-rights-transport-model/r-7d29e83f/receipt.json) · [Child sender model](../out/guest-zygote-linkerconfig-rights-child-model/r-6c90d57d/receipt.json)

An offline traversal of the sealed carrier reproduced the ordered
bootstrap and first-generator library candidates from the pinned
demand. It found all 27 earlier bootstrap names absent for libraries
whose selected copy is under `/system/lib64`. It also matched the
generator's Bionic symlinks and the donor init directive order.
The lookup assumes the held ordinary search branch and interpreter's
preloaded `ld-android.so`.
[Raw carrier search](../out/guest-native-early-loader-carrier-search/r-b04e67fb/receipt.json) · [Runtime loader selection](../out/guest-tree-linker-loader-selection-39249b5e/receipt.json)

The joined reader borrows the same root and explicit environment as
the placement view. It rejects `LD_*` environment names, verifies the
visible one-byte placeholder and applicable shadow absence, samples
placement once, then rechecks the small config inputs and their
identities. The visible output directory and base file must retain their
full metadata across the placement read. It checks bootstrap library
shadows or the first generator's per-APEX override as appropriate. The
caller owns the immutable proposed environment and stable mounted view
through use.

The ARM64 relocatable links the actual placement and generation
readers. The joined PC model passed 23 cases with the actual donor
bytes and simulated guest metadata. These cases include a same-byte
placeholder replacement, changed output directory times with both
absence checks still passing, a late shadow and a loader environment
override. Effective loader selection and native startup remain open.
[Joined reader](../compat/native/guest_native_early_loader.c) · [ARM64 receipt](../out/guest-native-early-loader-build/r-25bdf330/receipt.json) · [PC model](../out/guest-native-early-loader-model/r-b8dae4e7/receipt.json)

#### Opening the exact early-loader inputs

The opener starts from the child's retained root, output directory and
base FD. It opens each fixed directory relative to that root, then
reads the 33 bootstrap or eight first-generator files in the pinned
profile order through the existing placement and loader readers. The
generator branch borrows the admitted stable Runtime APEX sample and
checks the optional override directory on the output tmpfs. The carrier
symlinks are checked by the existing reader, separate from the regular
Runtime files they name.

The caller supplies an explicit proposed environment. Donor init's
early exports and the tester's inherited environment are different
inputs. The loader override check covers `LD_*`; the effective
property profile and `BIONIC_APPCOMPAT_OVERRIDE` are separate
prerequisites.

All opened placement FDs are temporary. The opener closes them before
rechecking the retained baseline and publishing the observed mount
flags. The returned baseline still uses the caller's three live FDs.
Any `noexec_objects` bit blocks that phase's future executable
placement. The opener is a separate prelaunch research API. Its ARM64
build and 30 host cases use the existing readers. The host cases
read pinned donor ELF bytes with simulated filesystem calls. With the
staged carrier's modeled `noexec` policy and an executable Runtime
mount, the reader reports all 33 bootstrap files and the first
generator's three carrier files as blocked. The cases also cover
open refusal, same-byte replacement, close uncertainty and late
placeholder drift.
[FD opener](../compat/native/guest_native_early_loader_open.c) · [Pinned roster](../out/guest-native-exec-placement-profile/r-078191c7/receipt.json) · [ARM64 link](../out/guest-native-early-loader-open-build/r-ce873811/receipt.json) · [Host model](../out/guest-native-early-loader-open-model/r-e5a41f20/receipt.json)

### Transitive app process library candidates

The offline graph starts with the pinned `app_process64` and Runtime
interpreter and traverses each `DT_NEEDED` from every matching physical
origin in the bounded donor census. It verifies the prior 14 direct
objects and 109 next-hop names. Carrier members are read from the sealed
EROFS image and compared to its materialization pins. ART and statsd
are read directly from their pinned ext4 payloads. The other APEX
members are explicitly labeled as saved extraction bytes. Reparse
aliases with unavailable target metadata are recorded separately.

Without statsd, `/system/lib64/libostatslog.so` leaves
`libstatspull.so` and `libstatssocket.so` unresolved in this census.
Both are present in raw statsd version 371020260 and named in that
manifest's `provideNativeLibs`. Adding that payload gives 287 parsed
objects and 4,818 candidate edge references with no unmatched names
in the bounded scan. Fourteen names have more than one candidate,
including different system and ART bytes for `libunwindstack.so`.
The physical system `ld-android.so` and the interpreter's preloaded
SONAME remain distinct records.

The graph retains ordered dependencies and distinct RPATH and RUNPATH
records. Effective generated config, selected namespace links, symbol
versions, relocations and dynamic loading still govern which objects
the guest actually maps. The graph supplies candidates for that
decision and leaves their executable placement open.
[Graph reader](../tools/review_guest_app_process_dependency_graph.py) · [Donor graph receipt](../out/guest-app-process-dependency-graph/r-edbed514/receipt.json) · [ELF parser checks](../out/guest-elf-candidate-model/r-3593f1a0/receipt.json) · [Graph model](../out/guest-elf-dependency-graph-tests/r-ac819fdf/receipt.json)

### Declared symbol-version compatibility

The offline readback replayed all 287 graph objects from their pinned
source extents and digests. It checked the ELF dynamic and GNU version
tables and preserved each versioned undefined symbol's declared
dependency name. The audit found 13,186 versioned undefined symbols
in 762 consumer-and-dependency groups. All 1,226 candidate comparisons
matched the local declarations tested, including ten matches that
depend on candidate-local unversioned fallback. Weak and unversioned
imports remain separately counted. Twelve of the 14 ambiguous names
have identical export sets for this comparison.
[Version audit](../out/guest-app-process-version-contract/r-8eaa1786/receipt.json) · [Parser checks](../out/guest-elf-version-contract-tests/r-3469c2ae/receipt.json)

The disk `ld-android.so` and preloaded Runtime interpreter share 24
loader function names. Every one of those disk-stub functions points
to the same `BRK #1` trap. The interpreter has distinct function
addresses and real implementations for the checked operations.
That difference makes the preloaded interpreter's identity a
requirement even when symbol names match.
[Held interpreter and stub readback](../out/guest-runtime-linker-stub-readback/r-f348fda2/receipt.json)

Android's upstream linker tracks the declared dependency's SONAME,
then checks symbol versions within the objects available to its
lookup. The candidate audit reports what each pinned object can
supply locally. The donor's selected namespaces, actual relocations
and dynamic loads still require runtime evidence.
[Bionic version tracking](https://android.googlesource.com/platform/bionic/+/refs/tags/android-16.0.0_r1/linker/linker.cpp) · [Bionic lookup](https://android.googlesource.com/platform/bionic/+/refs/tags/android-16.0.0_r1/linker/linker_soinfo.cpp)

### Carrier layout for startup

The sealed image's `/tree` directory is the guest root. The outer EROFS
root also contains the three raw core APEX payloads. A bounded raw
readback joined the early executable profile and the app-process
candidate graph to 280 carrier files across six directories. It
rehashes 33 distinct early carrier files. The first generator's three
carrier files are already in that set. The other carrier rows join
saved digest and inode evidence to the raw directory and inode metadata.
The readback verifies the app reader's carrier modes and owners, the
exact interpreter symlink, nine raw aliases and absent arch config.
Raw security xattrs describe the image. Effective mounted labels
remain unobserved.
[Readback tool](../tools/review_guest_carrier_startup_topology.py) · [Topology receipt](../out/guest-carrier-startup-topology/r-877e0bf0/receipt.json)

| Layout | Current reader behavior |
| --- | --- |
| Separate candidate preserving the complete sealed `/tree` projection | Fits the modeled root-to-system mount relationship under one coherent new mount identity. The existing stage provider requires `noexec`. |
| Directory overmount under the carrier | Refuses the directory's different mount ID even when device, inode and bytes match. A held directory hidden by a different named mount also fails. |
| File overmount under the carrier | Refuses the file's different mount ID from its pinned parent. |

The 26-case fixture uses the exact early placement reader and donor
bytes with modeled metadata. It confirms `EXDEV` for directory-only and
directory-plus-leaf overmounts, `ESTALE` for a stale held directory, and
an executable observation for a coherent new carrier mount under
hypothetical flags. The app-process reader separately requires the
system directories and entry to share the root mount, and the Runtime
interpreter to share the distinct, admitted Runtime mount. These are
source and host-model results.
[Placement model](../out/guest-native-exec-topology-model/r-6a108ad8/receipt.json) · [Early placement checks](../compat/native/guest_native_exec_placement.c#L89) · [App process checks](../compat/native/guest_linkerconfig_app_process.c#L79)

Preserving the full projection is the layout to carry forward for
design review. Candidate admission needs a separate backing and
mount identity, verified immutable input and effective mount policy,
and a release owner that can prove all descendants and namespace
holders drained before releasing the backing. After that, the first
runtime gate is the owned bootstrap occurrence and same-view APEX
evidence needed by the first genuine linkerconfig generation. The
staged cohort supplies raw ART, I18N and Runtime payloads. Statsd is
present as a compressed donor package, with no staged raw payload role.
The live provider and namespace decisions remain open.
[Stage provider](../compat/native/guest_tree_stage_provider.c#L322) · [Release boundary](../compat/native/guest_tree_release_owner.c#L208) · [Sealed payloads](../out/guest-tree-erofs-image-readback/r-c06d34d3/receipt.json)

#### Complete native link for the v8 research controller

The earlier v8 link left the file stage, guard and child birth checks
as unresolved project references. The 44-unit ARM64 link adds the
nine pinned provider sources from the verified file-stage cohort.
It resolves those references to the actual fs-verity, namespace,
EROFS create/attach/release, guard and process-identity owners. All
94 remaining imports are present in the pinned Android API 31 libc
stub. The artifact is a relocatable object with no entry point.
[44-unit link](../out/guest-zygote-v8-closure-build/r-a2a77cb6/receipt.json) · [File-stage predecessor](../out/file-stage-controller-successor-build/r-122795bb/receipt.json)

This link uses the existing `noexec` profile. Twenty host model
cases verify the existing owner's exact mount flags, rechecks of
the image and proc references, and retirement on flag drift. The
model simulates all mount calls.
[Carrier model](../out/guest-tree-file-erofs-noexec-model/r-943cf4ae/receipt.json)

#### Separate executable carrier research profile

The offline composition derives eight source changes from that
44-unit link. It selects `/data/local/tmp/oneos-exec-research` and
retains the same protected lease so the two controller profiles
cannot own the stage concurrently. The image file still needs the
exact fs-verity digest, extent, protected inode and proc FD identity.
The stage remeasures the same held FD pair after detached mount
creation and before attachment.

The research profile requests a fresh read-only, `nosuid,nodev` EROFS
mount. It requires `noexec` clear in creator, attachment, clone,
parked-parent and release readback. It makes no remount or flag
change on the selected carrier. The child keeps the existing
`noexec` tmpfs policy for data scaffolds, dev and linkerconfig.
The mock creator tests exercise both mount profiles and check that
either rejects the other profile's flag, as well as missing
protections and image or reference drift.

The 44-unit ARM64 relink resolves all project-local symbols and
checks the remaining imports against the pinned API 31 libc. The
new path is present and the old stage name is absent in the linked
cohort. The artifact is a relocatable research object with no
entry point. Kernel placement, actual generator execution and
whole-guest shutdown still require their own evidence.
[Source composer](../tools/compose_guest_exec_carrier_research.py) · [Exact overlay](../out/guest-exec-carrier-research-source/r-5c2391d2/receipt.json) · [ARM64 link](../out/guest-exec-carrier-research-build/r-1328c8a4/receipt.json) · [Two-profile creator model](../out/guest-tree-file-erofs-exec-model/r-97c25f1d/receipt.json)

The host fixtures cover the exact attachment, clone, parent observer
and release changes. They refuse a wrong mount or flag drift,
including a late `noexec` change before release. The stage fixture
also refuses a substituted image or proc FD after remeasurement.
[Attachment](../out/guest-exec-carrier-attach-model/r-6ae8d7a5/receipt.json) · [Clone](../out/guest-exec-root-clone-model/r-5e9c16d1/receipt.json) · [Parent observer](../out/guest-exec-carrier-parent-readback-model/r-c70eefa4/receipt.json) · [Release](../out/guest-exec-carrier-release-model/r-e12c64aa/receipt.json) · [Stage reborrow](../out/guest-exec-carrier-stage-reborrow-model/r-618dfaa2/receipt.json)

With simulated executable carrier flags, the existing bootstrap
opener reports zero blocked files across the same 33 pinned donor
ELFs. The original modeled carrier blocks all 33. Both samples
retain read-only, `nosuid,nodev` protection.
[Bootstrap comparison](../out/guest-native-early-loader-open-model/r-d329c60e/receipt.json)

#### Bootstrap check in child preparation

The separate carrier controller now calls the real early-loader opener
after preparing the seed and retiring the inherited descriptor roles.
The check first samples the retained carrier root and refuses
`NOEXEC` before opening the roster. It then requires a fresh result
with 33 verified files, zero blocked executable mappings and clean
temporary close. Parent and original deadline checks bracket the
operation and run again before sending the retained target pair.
The private v8 frame and the parent's independent checks stay in use.

The source composer renders the pinned donor's two `early-init`
export blocks as 26 ordered literal strings. They supply the explicit
research readback environment. The declarations establish their
values, while trigger order across imports and the complete effective
invocation environment remain open. The 47-unit ARM64 link resolves
the actual opener and placement reader. Nine helper cases use the
exact generated array and modeled mount and opener results.
The 45 child-phase cases run the exact helper and sender with modeled
acquisition. They check retained baseline identity, the two flag
refusals, and expiry after preflight and immediately before send.
[Source composer](../tools/compose_guest_exec_carrier_bootstrap.py) · [Exact source overlay](../out/guest-exec-carrier-bootstrap-source/r-aaf10787/receipt.json) · [ARM64 link](../out/guest-exec-carrier-bootstrap-loader-build/r-18273101/receipt.json) · [Helper model](../out/guest-gtc-bootstrap-helper-model/r-d41689ce/receipt.json) · [Child phase model](../out/guest-exec-carrier-bootstrap-child-phase-model/r-4cacb571/receipt.json)

Success is a preparation check in the offline research controller.
Actual bootstrap execution, settled APEX publication and verified
generator output still need separate phase ownership and device
evidence.

#### Standalone research preparation entry

The source composer reuses the original, pinned host-mediated main
with a single argument change to `--exec-carrier-research-v1`.
It preserves the root identity, executing-image FD, peer credentials,
pidfd and commit checks. The original launcher uses a different
argument and pinned controller bytes. The research entry stays
separate from that installed cohort.
[Entry composer](../tools/compose_guest_exec_carrier_entry.py) · [Exact entry source](../out/guest-exec-carrier-entry-source/r-454ce3b3/receipt.json)

The standalone link produces an 810,232-byte static ARM64
preparation executable. The final readback checks a file-backed RX
entry, bounded load segments, NX stack and RELRO, with zero dynamic
loader or relocation entries. The sole undefined weak Bionic
symbol also appears in the predecessor. Both binaries retain
libc stubs for `execve`, `setuid` and `setgid`; the independent
instruction scan finds no direct branch to those stubs in the
research executable. Source review finds no OEM dispatch path.
The 34 host entry cases cover both argument profiles and the
unchanged image and credential gates with modeled calls.
[Static build readback](../out/guest-exec-carrier-static-build/r-9c7627f7/readback-receipt.json) · [Independent ELF readback](../out/guest-exec-carrier-static-independent/r-bc889b32/receipt.json) · [Entry model](../out/guest-gtc-research-entry-gate-model/r-850f2c19/receipt.json)

Explicit entry would set up the controller's own session and cgroup
before host admission. A committed Prepare request can attach the
research backing and park the child after bootstrap readback. A
recovery gap in this original executable is a child exit after Begin
but before Partial descriptor adoption. GTR can confirm local child
reap while the stage guard still expects the full tree-release
terminal, leaving the shared lease held.
[Main entry](../out/guest-exec-carrier-entry-source/r-454ce3b3/retained_root_handoff.c#L860) · [Stage guard](../out/guest-exec-carrier-bootstrap-loader-build/r-18273101/src/guest_tree_stage_guard.c#L168)

#### Early preparation recovery

The research successor carries a distinct early local cleanup result.
The exact child must be reaped by its sole waiter, with its control
endpoint and tracked references closed. The controller also requires
positive evidence from the handoff. That can be a clean socket EOF,
an authenticated zero-rights child error, or a fully verified Partial
whose adoption failed and whose received FDs closed successfully.
After a reap, the controller still reads the private endpoint to
distinguish EOF from a queued frame. A queued unverified Partial,
malformed ancillary data, missing evidence or uncertain close keeps
the raw reap insufficient for stage release.

The guard retains the exact typed terminal. The provider then
re-admits its source, closes owned references, verifies normal
backing unmount and finishes the guard before publishing its own
early cleanup result. The host uses the existing local-closed state,
without a successful Prepare or an adopted-view claim. The recovery
is scoped to this preparation-only controller and its exact child.

The final 810,408-byte static ARM64 build passed ELF readback. The
52 controller, 35 guard and 11 provider host cases cover the typed
handoff, pre-adoption uncertainty and the ordering of source, backing
and guard cleanup. The provider rejects missing or invalid terminal
output before releasing any references. The model uses simulated
system calls. Actual mounted-view cleanup remains open.
[Recovery composer](../tools/compose_guest_exec_carrier_recovery.py) · [Exact source overlay](../out/guest-exec-carrier-recovery-source/r-5217344a/receipt.json) · [Static build](../out/guest-exec-carrier-recovery-build/r-370116f9/receipt.json) · [Controller model](../out/guest-exec-carrier-gtc-recovery-model/r-14624625/receipt.json) · [Guard model](../out/guest-tree-stage-guard-typed-model/r-fa2c70b4/receipt.json) · [Provider model](../out/guest-tree-early-prepare-provider-model/r-68cd4a53/receipt.json)

#### Matched research preparation pair

The isolated tester now pins the research controller's exact path, entry
argument, digest and extent. The launcher still checks ownership, mode,
size and digest on the held executable FD before the same-FD exec. The
old host would reject a successful research Prepare role trailer because
its constructor authorized that trailer only for the prior controller.
The rebuilt host replaces that exact digest and extent and preserves the
role parser, wire protocol, peer checks and module registration metadata.
[Tester source](../tools/compose_exec_carrier_prepare_tester.py) · [Host source](../tools/compose_exec_carrier_prepare_host.py) · [Launcher model](../out/exec-carrier-prepare-tester-launcher-model/r-ead94f62/receipt.json) · [Tester DEX comparison](../out/exec-carrier-prepare-tester-dex-independent/r-2e612aef/receipt.json) · [Host DEX comparison](../out/exec-carrier-prepare-host-dex-independent/r-5ae71a2a/receipt.json)

Both APKs preserve their lab package names and non-DEX payloads. Each
has a fresh lab certificate verified by apksigner v2 and v3, so an
installed predecessor under either package name cannot be updated in
place. The exact V2 profile payload binds the tester package, version,
APK and signer to the research controller. The held Java profile parser
accepted the canonical fields and rejected 20 malformed cases. The pair
checker joined the actual APK payloads, compiled DEX and signer evidence
to that profile and controller. Substituting the legacy host receipt or
the legacy profile receipt failed the pair check.
[Tester APK receipt](../out/exec-carrier-prepare-tester-apk/r-86432e64/receipt.json) · [Host APK receipt](../out/exec-carrier-prepare-host-apk/r-89406ca2/receipt.json) · [Profile parser receipt](../out/exec-carrier-prepare-tester-profile/r-5fb105e7/receipt.json) · [Pair checker](../tools/check_exec_carrier_prepare_pair.py) · [Pair receipt](../out/exec-carrier-prepare-pair/r-84e064fd/receipt.json)

The pair is an offline preparation artifact with no publisher, protected
profile load, host activation or target execution. A live run still needs
the exact host registered in SystemServer at startup and an isolated stage
that can demonstrate real backing unmount and guard release. The new
stage path shares the prior stage's lease. Device acceptance remains 0 of
18. This pair pins the controller before the source correction below and
is held for research comparison.

#### Real Linux transport check and early error classification

The exact pre-Partial child has one error sender and uses `S_PRIVATE`.
The first recovery build accepted any well-formed error in the inherited
diagnostic range as verified cleanup. A Linux fixture reproduced that
behavior with a credential-authenticated stage-11 frame after child exit.
The controller preserved `ENOENT` and incorrectly promoted the reap to
`GTR_EARLY_PREPARE_LOCAL_CLOSED`. The source correction keeps the old
diagnostic errno and restricts this proof to `S_PRIVATE`. An impossible
stage now leaves the raw reap, which the guard holds before backing release.
[Corrected source](../out/guest-exec-carrier-recovery-source/r-813c77cc/receipt.json) · [Prior failing run](../out/exec-carrier-kernel-transport-fixture/r-JABgooSw/baseline-impossible-error-stage.txt) · [Corrected run](../out/exec-carrier-kernel-transport-fixture/r-JABgooSw/corrected-impossible-error-stage.txt)

The WSL2 fixture linked the exact controller, release and slot sources
against Linux x86-64 with the mounted child operation replaced by a
controlled fixture. The original build passed seven cases and failed the
new stage-11 assertion. The corrected source passed all eight cases with
actual kernel sockets, credentials, descriptor transfers and reap. The
zero-byte credentialed frame differed from EOF. The truncated rights
case delivered 32 descriptors and the pipe and FD inventory confirmed
release. The original 52 mocked cases also passed with the correction.
Focused mock cases preserve `ENOENT` and withhold promotion at stages 3,
11 and 12.
[Linux result and input pins](../out/exec-carrier-kernel-transport-fixture/r-JABgooSw/receipt.json) · [Mock regression results](../out/exec-carrier-error-stage-model/r-1f7ed53b/receipt.json)

The WSL2 kernel lacks fs-verity. The actual F2FS and file-backed EROFS
unmount and guard release still require a compatible lab. The source
correction has no rebuilt Android ARM64 executable or matching APK pair.

## Reproduce the refusal

```powershell
python -B tools/check_guest_linkerconfig_inputs.py
```

Exit `2` means the exact known bytes were verified and the profile remains blocked. Exit `1` means a check or receipt write failed. Add `--record` to save the refusal in a fresh `out/guest-linkerconfig-inputs/` run directory. The verifier has fixed input paths, uses bounded reads and rejects symlinks and reparse points in the inspected paths. It makes no generator call or network request. A separate check modeled an unbound file appearing at the correct path and verified that no launch manifest was issued. The real donor init source also failed admission when checked against a deliberately wrong hash. No OEM code, guest process, mount or device operation ran.
