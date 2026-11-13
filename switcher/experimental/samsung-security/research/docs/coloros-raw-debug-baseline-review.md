# ColorOS classes2 raw-debug baseline review

**PASS for the newly measured raw-debug scope only.** The actual original
`c9a84ceb…` and preserved no-edit baseline `620bc981…` contain equal raw
debug facts for all **45,059 code-bearing methods**. This conclusion comes
from a new static byte parser, not the earlier `getDebugItems()` normalizer.

The original classes2 is read from the immutable donor services archive
`66d0d51d…`; the baseline is the actual corrected single-workflow first
product. Their full paths/hashes and the passive ordinary039 parser pin are in
the inventory and receipt. The audit never invokes a DEX writer, compiler,
Android/OEM class, service, phone command or the header-preservation helper.

## Compared facts and actual results

- Debug-info presence: **39,544 present / 5,515 absent** in each input.
- All **30,669 unique debug_info streams** in each file are referenced by the
  audited methods; their count/start agrees with the raw 0x2003 map entry.
  Referenced stream extents do not overlap.
- `line_start`, parameter-name count/order/presence and exact MUTF8 names match
  by method. Raw string/type reference pools match before decoding.
- Every meaningful event matches in original order, including address and
  payload: line, local start (including extended signature), end/restart,
  prologue/epilogue and source-file events. Per-method totals are **246,501 line,
  42,331 local-start, 37,026 local-end, 12,394 local-restart**. Prologue, epilogue
  and source-file events are each zero in both actual inputs.
- The parser executes the raw debug state machine through opcode **0
  END_SEQUENCE**, including preceding ADVANCE_PC/ADVANCE_LINE. Its terminal
  **address and line** match for every method. It records the END opcode byte
  location and stream extent separately from code/debug physical offsets.
- **Zero changed methods; zero changed raw stream bytes by per-stream SHA256.**
  Physical debug offsets relocate and therefore the stream-record JSONL files
  have different hashes. This is location change, not omitted header/end data.

The parser retains raw MUTF8 hex and reference indices, nullable ULEB128p1
references, signed line deltas, and the complete meaningful event sequence.
Five positive authored fixtures cover parameter headers, trailing advances,
special line opcodes, local/source/prologue/epilogue events and extended-local
signatures; three malformed fixtures must fail. These fixtures execute only
authored Python inspection code.

## Explicit original hook and constructor records

| Original method | line_start / parameter names | Terminal END cursor: code-unit address, line | Code units |
| --- | --- | --- | --- |
| DMS.onStart()V | 873 / none | **54, 876** | 57 |
| DMS.onBootPhase(I)V | 903 / phase | **276, 963** | 277 |
| DMS$BinderService.onTransact(int,Parcel,Parcel,int)Z | 7075 / code,data,reply,flags | **25, 7081** | 27 |
| DMS(Context) | 734 / context | 8, 735 | 9 |
| DMS(Context,Injector) | 739 / context,injector | 750, 833 | 751 |
| DMS$BinderService(DMS) | 6035 / this$0 | 13, 6037 | 14 |

DMS means the original
`Lcom/android/server/display/DisplayManagerService;`. All six records include
their actual source/baseline code/debug offsets and complete events in the
selected-method raw proof. **END_SEQUENCE is not implicitly at code end.**
A later edited-method relocation must independently preserve the mapped
original header, parameter names, meaningful events and terminal cursor; using
the new instruction count as END cursor changes these facts.

## Scope of the result

The frozen earlier no-edit review remains unchanged and retains its original
record-based scope. This new card supplies the previously missing header/end
measurement; it does not retroactively turn `getDebugItems()` into a raw
debug decoder. No runtime-semantic harmlessness waiver was used. There are
no observed raw-debug differences to waive in this specific baseline.

This does **not** establish debug relocation for a future three-hook output,
new dispatch method, other DEX, inverse, roundtrip or installed image. Those
outputs still need their own exact source-to-output PC/register mapping and
raw header/event/end checks. New references, source edits, lifecycle/retirement,
authority ownership, launch and Android acceptance remain outside this result.

Recheck (static inspection only):

```
python -B tools/audit_coloros_raw_debug_baseline.py --self-test-only
python -B tools/audit_coloros_raw_debug_baseline.py
```

The actual run was session77802, terminal exit0. Immutable receipt:
`out/coloros-raw-debug-baseline-review/20261106T005326093299Z-1f04451bce1b41a38c0cd928cf38e048/receipt.json`.
All OEM-derived debug records stay under ignored
`firmware/coloros-raw-debug-baseline-review/`.
