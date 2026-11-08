# Independent parent-payload preflight review

**No scoped defect found in the conditional static preflight.** The original
ColorOS classes2 input fits exactly the proposed external-reference footprint,
with zero short-string widening. This does not admit a writer, complete helper
API, source hook, retirement hook or runtime payload. No patcher, compiler,
writer, OEM/Android code or phone operation ran in this review.

Reviewed frozen producer inputs:

- `tools/preflight_guest_metrics_parent_payload.py`, SHA256
  `d076c60a4c16774e1a8b75377661caf814a4eb4a72420f4082bc493dc4dce9ea`.
- `docs/guest-metrics-parent-payload-preflight.md`, SHA256
  `9fb395134ab3bc47b0dccf1e4dad59fa929a3df945e27960b6815b36f189427c`.
- `inventory/guest-metrics-parent-payload-preflight.json`, SHA256
  `006e31d5621b3009e0e7e9605a09dd91f88a3bfeb396fc5f51bd176e74851865`.
- Actual immutable receipt
  `out/guest-metrics-parent-payload-preflight/20261105T235452539307Z-7e95587536bd4f5484f6a458e1cc010b/receipt.json`,
  SHA256 `83aec0e3a6b699b77388f87b6e43286833de238a088a9d9226a0b1a1fce3cb93`.

## Independent original-byte checks

The independent Python reader reads only the selected ZIP entry in memory from
original services.jar SHA256
`66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3`.
It does not invoke/import the producer's parser or duplicate archive extraction.
Both actual DMS/BinderService definitions occur in ordinary039 classes2.dex,
logical header offset0, header112, 10,042,704 bytes, SHA256
`c9a84cebd3bc22a48c0737a7de34d96ba0b97a6294d4bdd97c935543e605659f`.
File extent, endian tag, SHA1 and Adler32 agree. The original map has17 items
and **no 0xf000 hidden-API section**. There are70,153 defined members. Section
absence is not an implicit numeric policy map and must remain explicit; a
Samsung HAPI copy/default-flag repair would be inapplicable.

| Pool | Original | Conditional projection |
| --- | ---: | ---: |
| Classes | 6,554 | 6,554 |
| Method IDs | 60,090 | 60,094 |
| Field IDs | 25,197 | 25,198 |
| Type IDs | 9,999 | 10,001 |
| Proto IDs | 16,751 | 16,755 |
| String IDs | 93,865 | 93,872 |

The projection includes one DMS field/dispatch definition and four total method
references: DMS dispatch, Cell capture, Cell completed-phase and Cell dispatch.
It includes Cell and PhaseDisposition types, four absent prototypes and seven
new strings; their shorties already exist. Actual DMS declarations contain
neither the new field name nor dispatch name. Exact full new references are
also absent. The phase method's actual proposed return remains
`Cell.PhaseDisposition`, even when the caller discards it. No void substitution
was counted.

These are **conditional counts**, not the complete eventual helper footprint.
They exclude helper definitions, added failure/lifetime paths, new lifecycle/
retirement references and unresolved API/type changes. There is no selected
retirement source callsite. Any expanded reference set requires a fresh proof.

## String ordering and remaining margin

An independent decoder checks every original string's declared UTF16 length,
encoded-NUL/surrogate handling, uniqueness and UTF16 sort order. It independently
reproduces the two type strings at insertion index28,856, capture/dispatch names
at45,272/49,299/49,325, and field/phase names at70,560/77,336. Raw MUTF8 byte
comparison alone would not establish DEX string ordering.

The independent instruction walk matches778,811 instructions in44,520 unique
code items, including payload extents, and31,212 short CONST_STRING uses.
**Maximum short index65,529 becomes65,534: only one index remains.** There are17
references with projected indices at least65,520. Two additional strings inserted
before the current maximum reference would force widening beyond65,535, so the
zero-overflow result cannot authorize arbitrary helper strings. There are232
shared code offsets; a later widening/preservation proof must account for every
defined method using a shared item. None widens under the current proposal.

Even with no opcode-width change, sorted pool insertion reindexes existing
references throughout the DEX. This is not literal byte preservation outside
three methods. A future no-edit canonical baseline and edited inverse must
establish symbolic full-record preservation and all affected operand/PC/debug/
try mappings; pool-capacity success does not establish that writer contract.

The three original code headers independently agree:

| Hook | Registers / incoming / outgoing | Units / tries |
| --- | --- | --- |
| DMS.onStart()V | 4 / 1 / 4 | 57 / 2 |
| DMS.onBootPhase(I)V | 12 / 2 / 3 | 277 / 5 |
| BinderService.onTransact(int,Parcel,Parcel,int)Z | 7 / 5 / 5 | 27 / 0 |

Instruction-byte hashes and actual debug offsets are recorded in the independent
result. No edited PC/debug mapping or inverse was produced here.

## Exact seven-source overlap scope

All seven selected OneOS inputs at commit
`1f2c2aa45ab8a7dc81384f6b67962d1e9cf7fefe` were read/hash-checked as data:

| Input | Bounded routing/target conclusion |
| --- | --- |
| display_mode_specs.py | LocalDisplayAdapter.tryConnectDisplayLocked; other class |
| qti_builtin_display_public.py | LocalDisplayAdapter$LocalDisplayDevice.getDisplayDeviceInfoLocked; other class |
| oplus_wait_for_service.py | services route is `--only DefragService` at make-overlays261; independently scanned selected hooks have zero waitForService invokes |
| oplus_boot_hangs.py | make-overlays320 routes to oplus-services tree; GameGpuControlPanel/dumpenvironment/AppErrorsExtImpl/getTpInfo patterns |
| samsung_backlight_curve.py | make-overlays340 routes to oplus-services LocalDisplayDeviceExtImpl |
| OneOSPanelBacklight.smali | helper copied by preceding patch, not a DMS hook |
| oplus_resolution_tables.py | make-overlays351 routes to oplus-services OplusResolutionManagerFeature.init |

No direct edit overlap with the three selected bodies was found in **these seven
selected sources**. This is not an audit of every make-overlays patcher or the
installed OneOS image. Other edits/reassembly still share services DEX pools,
and the original archive is not a substitute for a pinned complete patched
baseline or explicit composition proof. None of those patchers was executed.

Recheck independent evidence with
`python -B out/guest-metrics-parent-payload-preflight-review/independent_review.py`.
The review accepts only the stated preflight facts/conditional capacity result.
Complete ordinary039 no-edit serialization is a separate prerequisite; three-hook
emission, retirement and future reference changes remain unapproved.
