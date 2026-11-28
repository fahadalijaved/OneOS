# Original DMS parent payload preflight

**Static preflight only: no writer, DEX emission, class loading or phone action.**
The captured original input admits the proposed pool footprint without a split or
additional const-string widening. This does not establish that an edited producer
can preserve the source, that the OneOS installed image matches it, or that the
parent lifecycle/loader is ready. Run `python -B tools/preflight_guest_metrics_parent_payload.py`.
The [inventory](../inventory/guest-metrics-parent-payload-preflight.json) records
the exact source pins, complete header pools/map and immutable per-run receipt.

## Actual selected source

Archive `66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3`
is the original ColorOS services.jar. Both actual DMS and BinderService definitions
are in **classes2.dex, ordinary DEX039, header112, logical offset0**. Input SHA1
and Adler32 are checked. No foreign-header slicing/rebasing occurs. Other physical
DEX pools are recorded only to identify boundaries; no cross-DEX class movement
or cohort reassembly is proposed.

| Pool | Original | Projected exact reference footprint |
| --- | ---: | ---: |
| Classes | 6,554 | 6,554 |
| Methods | 60,090 | 60,094 |
| Fields | 25,197 | 25,198 |
| Types | 9,999 | 10,001 |
| Prototypes | 16,751 | 16,755 |
| Strings | 93,865 | 93,872 |

The 65,536-entry method/field/type limits fit. This footprint excludes authored
helper **definitions**; the complete helper placement/profile is a separate
selection gate, not permission to append arbitrary classes to this DEX.

The four missing MethodRefs are DMS's package-private
`dispatchOneOsGuestMetricsFromParent(Binder,Parcel,Parcel,int):boolean` and the
cell's `captureAfterOnStart(Object,Binder):Cell`,
`onOriginalBootPhaseCompleted(Object,int):Cell.PhaseDisposition`, and
`dispatchFromParent(Object,Binder,Parcel,Parcel,int):boolean`. Two missing types
are the Cell and its PhaseDisposition. These four prototypes are absent; their
shorty strings already exist. The private default-null field name
`mOneOsGuestMetricsLifecycle` and new DMS method name are absent from actual DMS
declarations. No constructor change is needed or admitted.
The phase disposition return is discarded by the proposed original-source hook;
it remains a real MethodRef return type, not a substituted void signature.

The two owner strings insert at original string index28,856; capture/dispatch
names at45,272/49,299/49,325; field and phase names at70,560/77,336. The scanner
walks all44,520 unique code items (778,811 instructions), respecting payload
sizes and refusing reserved/unknown039 opcodes. All31,212 short CONST_STRING
references retain indices≤65,535 after these exact insertions: **zero width
changes**. This is literal pool-pressure evidence for this footprint, not an
allowlist for later helper strings. Sorting uses decoded MUTF8 UTF16 code units,
including encoded NUL/surrogates. Actual writer output must recheck every width,
PC, branch, try and debug record; even an unexpected jumbo is a refusal.

## Raw policy and exact edit/inverse obligations

The selected map contains **no hiddenapi_class_data_item (0xf000)**. There are
70,153 defined field/method entries. Thus no source numeric HAPI flags exist to
copy, default or recover here. Samsung's repaired no-edit framework HAPI section
is inapplicable. Preserve this source absence; adding original members must not
silently introduce a synthetic policy section. If the eventual patched input has
policy metadata, stop and build a descriptor/partition/order/presence mapping
with reviewed new-member policy; copying an old section after insertion is invalid.

Exact original hook shapes:

| Method | Registers / incoming / outgoing | Code units | Original try count |
| --- | --- | ---: | ---: |
| DMS.onStart()V | 4 / 1 / 4 | 57 | 2 |
| DMS.onBootPhase(I)V | 12 / 2 / 3 | 277 | 5 |
| BinderService.onTransact(int,Parcel,Parcel,int)Z | 7 / 5 / 5 | 27 | 0 |

The [frozen parent source](guest-metrics-parent-transport.md) and
[cell API](guest-metrics-parent-cell.md) select capture after originalPC0x32 and
before0x35, completed-phase100 after tail0x111/before0x114, and a private-code
prefix before original BinderService PC0. They do not permit catching original
failures, retrying borrowed packets or changing ordinary display dispatch.

Before an edited writer is accepted: establish a no-edit classes2 canonical
baseline with complete declarations, partitions, explicit initial values,
annotations, parameter/debug events, registers/literals/references, PCs,
branches/payloads/try handlers and unknown-map-item disposition. Preserve both
DMS constructors and BinderService constructor. Then admit only these three old
bodies, one private null field and one package-private dispatch method; new helper
definitions have their own exact closure. Each hook needs explicit old→new PC,
try and debug maps, new-own-catch boundaries and register/invoke-range proofs.
Inverse must remove the added members/hooks/references and restore every original
record plus canonical no-edit bytes. No canonical baseline, inverse, edited
artifact, helper insertion or Android acceptance is claimed by this preflight.
There is no selected retirement source hook or producer yet. Genuine retirement,
default-OFF/enablement, actual current parent/generation and lifetime admission
must be assembled and reviewed before enabling this transport. The cell's retire
API proposal does not establish an original lifecycle callsite.

## Frozen OneOS source overlap

The seven pinned patch inputs are six Python scripts plus authored
OneOSPanelBacklight.smali at commit
`1f2c2aa45ab8a7dc81384f6b67962d1e9cf7fefe`. They are inspected as data, never run.
The pinned make-overlays.sh routes them as follows:

| Input | Source-selected target and overlap |
| --- | --- |
| display_mode_specs.py | services LocalDisplayAdapter.tryConnectDisplayLocked; different class/method |
| qti_builtin_display_public.py | services LocalDisplayAdapter$LocalDisplayDevice.getDisplayDeviceInfoLocked; different class/method |
| oplus_wait_for_service.py | services scan is explicitly `--only DefragService` (make-overlays261); selected three hook bodies contain no waitForService invocation, independently scanned from actual code |
| oplus_boot_hangs.py | oplus-services GameGpuControlPanel, dumpenvironment pattern, AppErrorsExtImpl and policy/input getTpInfo; separate archive |
| samsung_backlight_curve.py | oplus-services LocalDisplayDeviceExtImpl.getBacklightFromBrightness plus helper copy; separate archive |
| OneOSPanelBacklight.smali | helper input to the preceding oplus patch; no DMS hook |
| oplus_resolution_tables.py | oplus-services OplusResolutionManagerFeature.init; separate archive |

There is no direct edit overlap of these three original methods in those selected
sources. **DEX-wide pool/layout overlap still exists** when OneOS reassembles the
same services DEX after its other patches; an edited producer must consume an
exactly pinned patched baseline or explicitly compose both edit sets. This source
inspection does not identify installed bytes or authorize overwriting OneOS work.
