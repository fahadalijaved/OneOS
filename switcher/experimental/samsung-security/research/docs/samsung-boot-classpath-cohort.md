# Samsung original boot-classpath cohort provenance

This card pins an **original captured candidate**, not a selected boot cohort.
Thirty actual boot-classpath config fragments declare the same 61 jar paths as
the captured BOOTCLASSPATH metadata, with every fragment's internal order
preserved. The complete ordered paths, sizes, SHA256 hashes, config message
offsets/ordinals, raw SDK qualifiers and captured APEX alias records are in
`inventory/samsung-boot-classpath-cohort.json` and the compact generated
`out/samsung-boot-classpath-cohort/original-candidate-jars.json`.

No phone, network, OEM/ART execution or compiler ran. Only named config files,
the init producer edges and one producer binary were read from the existing
mounted tar; no jars or full tree were extracted. Existing topology, native,
retention and boot cards are preserved. This evidence supports future launch
owner preparation without claiming current environment, loaded classes, active
APEX resolution or Context readiness.

## Captured files and producer edge

All 33 extracted inputs are pinned against the prior strict mounted manifest
SHA256 `6654252d9f7bde941e367fe79eb9af541869f4a1ddb5d1b8a0f0d4d6dde57a7a`.
They comprise30 `/etc/classpaths/bootclasspath.pb` files, plus:

| Captured artifact | SHA256 |
| --- | --- |
| `/system/etc/init/hw/init.rc` | `94a786990f73b176d8d31a2cdeb8f7d6daab65e7ba766d5214df44d29e7a92bb` |
| `/apex/com.android.sdkext/etc/derive_classpath.rc` | `a9e65b0c114408e5cb8356bdb435a6b48d0a67cd7879915c52ffa094a267f607` |
| `/apex/com.android.sdkext/bin/derive_classpath` | `015e20a3dba724c2dae7ff8015bc50658f6f1a89e329e620200504568d7a0f2e` |

The actual init source imports `/init.environ.rc` at line 7. At 1354 it performs
`exec_start derive_classpath`; 1355 loads exports from
`/data/system/environ/classpath`; 1360 starts `art_boot` before odsign startup.
The service RC runs the original SDK-extension producer as system, group
system/reserved_disk, disabled/oneshot, with no command-line override in that
declaration. This connects the captured config producer to init export loading.

Neither root `/init.environ.rc` nor generated `/data/system/environ/classpath`
is in this ten-root mounted capture. Their absence from the index is not proof
they were absent on the phone. The metadata file
`../firmware/samsung/os-mirror-20261104/metadata/bootclasspath.txt`, SHA256
`524b012a77f96ab580ae9a7d25ad14ec1d8620fdc08b6c5cd6d8e2e7288858d1`,
is the ordered capture record. It is not an observation of a future process's
environment or this source's exact generated export-file bytes.

## Config declarations versus ordering

A bounded authored wire reader parses only the actual repeated jar messages:
path, classpath enum, optional min/max SDK strings. Duplicate/unrecognized fields,
unsupported wire kinds, truncated lengths and invalid paths refuse. The producer's
actual generated enum table at ELF VA `0x82c68`, linked by
`Classpath_Name` ADR `0x55e50` and count `0x55e5c`, establishes:
BOOTCLASSPATH=1, SYSTEMSERVERCLASSPATH=2, DEX2OATBOOTCLASSPATH=3,
STANDALONE_SYSTEMSERVER_JARS=4, UNKNOWN=0. This is Samsung binary evidence, not a
guessed protobuf schema or AOSP-revision assignment.

The 30 boot-fragment files contain 83 entries: 61 BOOTCLASSPATH and 22
DEX2OATBOOTCLASSPATH. The latter are a separate declared category, not extra
boot-loader jars. No jar definition/class inventory was repeated.

Five complete producer functions (4,321 statically decoded instructions) pin
`main`, `GenerateClasspathExports`, `ParseFragments`, the suffix initializer and
enum-name access. `GenerateClasspathExports` calls
`android_get_device_api_level` at `0x491d0`, checks the API threshold, then calls
`ParseFragments` with true at `0x491fc` and false at `0x49210`. The boolean selects
the boot versus system-server config suffixes initialized at `0x54b18/0x54b60`;
**it is not an ART-first versus other-APEX pass**. The fragment reader reaches
`glob` at `0x47ce0` and file reading at `0x48220`; the generator writes its output
at `0x49bdc`. SDK/codename and global fragment-enumeration/filtering behavior is
not completely reconstructed here. Filename sorting is not asserted as the
original producer algorithm.

Consequently the candidate's global order comes from the pinned captured list.
Its set equals all 61 declared BOOTCLASSPATH paths, and each fragment's entries
appear in their original relative order. This is a checked provenance relation,
not a proof that rerunning the producer under a different property/APEX view
would emit the same list. Four platform jar paths carry min-SDK `37`:
framework-graphics, framework-location, framework-ondeviceintelligence-platform
and framework-telecom. Qualifiers remain literal source facts; no fake global
SDK/codename or eligibility result is supplied.

| Captured candidate positions | Source/config cohort |
| --- | --- |
| 0–4 | ART core-oj, core-libart, okhttp, bouncycastle, apache-xml, in ART fragment order |
| 5–20 | Sixteen `/system/framework` jars in system fragment order |
| 21 | i18n core-icu4j, declared by the system fragment |
| 22–60 | Remaining APEX jars in captured metadata order; each mapped to its declaring fragment |

## APEX and edited-framework boundaries

Every ordered candidate record is a regular-file row with immutable captured
size/hash. APEX entries also retain matching versioned alias rows and active
records from captured `apex-info.txt`, SHA256
`6c8ebe0b93c4f9147d568678fd7909d748ff17e4211eb71255fa0fc6a801e8af`.
Those records describe the capture's mounted layout. They do not resolve a
future active mount, on-data update, linker namespace or existing process's
loaded code. No equality of unrelated APEX executables is inferred from jar
alias agreement.

Original framework.jar is at index 5, 54,708,192 bytes, SHA256
`8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe`.
The existing ContextImpl/ResourcesManager/DisplayMetrics ownership and private
boot-class visibility obligations stay in the frozen boot/source cards. The
unselected scalar diagnostic currently provides only a 1,624-byte method
projection, SHA256 `0a310ff9f473537ef6e23cf82c91718d105944bc2a8e52439f07fa69b10980ae`;
its inventory explicitly says no whole framework and no runtime cohort produced.
It cannot replace this framework slot or serve as a complete helper container.

A future edited whole-framework component needs its own exact output hash,
source-preservation/per-member hidden-API proof, original-definition boundaries
and slot selection. Authored helper containers need explicit definitions and
boot visibility for their full dependency closure. This card chooses neither
their insertion positions nor any helper artifact. App-classpath visibility is
not boot-class visibility, and a duplicate child framework jar is not a
replacement for the original boot definition.

## Launch-owner use and remaining gate

The compact candidate file gives Detail's future VM-vector owner a reproducible
61-entry order/hash baseline. It contains no command line or selected modified
cohort. Before any Context-only VM could be admitted, that owner still needs
the actual per-process source/root/APEX/linker view and all 61 intended bytes,
the complete reviewed edited component/helpers, coherent boot/image handling,
and UI's genuine property/final-vector boundary. Explicit BCP selection must
not silently inherit or regenerate guest paths. Resources, native registrations,
real display inputs and lifecycle ownership remain separate requirements.

Recheck: `python tools/audit_samsung_boot_classpath_cohort.py`. Bounded acquisition,
wire discovery and static producer decoding are explicit `--extract`,
`--discover`, `--native` modes. The ordinary recheck verifies source hashes,
config coverage/order relations, native anchors and malformed-wire refusal,
then regenerates only this stream's derived inventory and receipts. No boot
artifact or runtime identity is selected.
