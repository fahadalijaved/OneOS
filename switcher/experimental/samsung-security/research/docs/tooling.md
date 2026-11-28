# Static security reader

`tools/static_security_reader.py` wraps the authored Java reader using the existing
parent JDK and JADX dexlib. It parses supplied archive bytes; it never loads or
executes an Android/OEM class, service, JNI library or credential operation.
The parent bridge project remains paused.

## CLI and Python API

Run from this nested project's root. A caller must supply the exact independently
selected archive SHA256. Omit method options to discover a class's actual declared
signatures, fields and flags:

```powershell
python -B tools/static_security_reader.py --archive ../firmware/samsung/runtime-20261104/services.jar --sha256 def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6 --class-name com.android.server.locksettings.LockSettingsService --stream tooling
```

Add repeated exact signature selectors, including the return descriptor:

```powershell
python -B tools/static_security_reader.py --archive ../firmware/samsung/runtime-20261104/services.jar --sha256 def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6 --class-name com.android.server.locksettings.LockSettingsService --method 'getStrongAuthForUser(I)I' --stream tooling
```

`--all-methods` selects all declared methods of that one class. `--list-classes`
instead emits bounded class summaries for the archive. Missing exact methods or
an absent/ambiguous selected class fail; no implicit constructor is invented.
Bare method names are refused because overloads are distinct source facts.

`--reference 'Lowner;->name(arguments)return'` scans exact direct method references
through the selected archive. `--reference 'Lowner;'` selects that type plus
method/field references whose declaring owner is that type. Reference mode takes
no class selector. A zero result means no matching explicit first-reference edge
in that archive; it does not exclude interface dispatch, reflection, JNI, inherited
targets or a runtime caller. All-method/list/reference sentinels are nonglob tokens;
the initial Windows launcher `*` expansion defect was fixed and failed queries
published no receipt.

For audit scripts:

```python
import runpy
reader = runpy.run_path('tools/static_security_reader.py')['read_archive']
receipt = reader(
    '../firmware/samsung/runtime-20261104/services.jar',
    'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
    class_name='com.android.server.locksettings.LockSettingsService',
    methods=['getStrongAuthForUser(I)I'],
    stream='tooling',
)
```

Archives must be under the supplied parent or nested `firmware/`. A stream name
is a bounded lowercase label, not a path. Each audit worker should choose its
authorized stream (`credentials`, `storage-keys`, `fingerprint`, etc.).

## Output contract

CLI stdout is a compact JSON locator. The receipt schema is
`static-security-reader/v1`. Every invocation uses unique names:

- Raw OEM instructions/strings/payloads: `firmware/<stream>/<stamp>.jsonl` only.
- Derived declaration/count/hash metadata: `out/tooling/<stamp>/receipt.json`.
- Authored tool classes/cache and generated logs: `out/tooling/` only.

Raw records are JSON Lines:

| `record` | Fields |
| --- | --- |
| `dex` | Physical entry, full physical DEX SHA256/length, logical header offset/length, version and class count |
| `class` | Exact descriptor/flags/super/interfaces and declared field/method signatures; physical entry and logical header offset |
| `method` | Exact owner/signature/access, code presence/register count, instructions, catches and normalized body SHA256 |
| `reference` | Exact caller signature, physical/logical identity and matching instruction |
| `summary` | Complete observed class count and selected/scanned counts |

Instructions retain code-unit PC/width, registers/ranges, literals, exact first
reference, optional second reference and target PC. Switch payload elements retain
keys and offsets **from the referring switch instruction PC**, not from payload
PC. Array payloads retain element widths/values. Catch records retain source
range/type/handler PC. A method's SHA256 covers the exact deterministic UTF8 JSON
`body` object emitted by Java, including owner/signature/flags, instructions and
catches. It is a normalized code/declaration hash, not a raw code-item byte hash.

Receipts keep method proof hashes/counts and raw-file SHA256; full raw bodies stay
in ignored firmware. Archive and reader source hashes are checked before/after.
Exact absence is local to the selected archive. Field initial encoded values,
debug line/local-variable tables and hidden-API restrictions are not decoded.
Second instruction references are retained in raw bodies, but the direct-reference
filter currently matches the first reference only.

## Full-container DEX041

The source reuses the established full-container constructor:
`super(null, container, 0, false, logicalHeaderOffset)`. Header count/file size,
container size/header offset, endianness and table extents are validated for every
logical header. Table/data offsets remain relative to the original full container;
no DEX bytes are patched or rebased. Physical DEX names and logical offsets are
retained through method output. The ordinary-only parent `Dump-SelectedDex.java`
must not be substituted for Samsung041.

Observed source anchors: Samsung services has18,916 classes, comprising9,252 at
header0 and9,664 at10,057,984 in one physical DEX. ColorOS services has26,650;
Samsung/ColorOS framework have43,498/38,870. The selected Samsung LockSettingsService
has199 declared methods in the second logical header; ColorOS has249. These are
declaration counts, not security capability or compatibility counts.

## Meaningful verification and bounds

An independent direct byte-table/code-item decoder under
`out/tooling/verify_actual.py` agrees on508 actual selected methods across Samsung
and ColorOS services and framework:17,250 instructions,9,139 references,1,813
branch targets,782 literals,711 catch handlers and three switch payloads. It does
not call dexlib. `out/tooling/actual-parity.json` pins all inputs and raw receipts.
There was no positive array-payload case in these selections; that coverage gap
is explicit. Register operands are retained by dexlib but not independently
bit-decoded by this parity validator.

Six focused refusal checks cover wrong input hash, ambiguous bare method names,
missing exact methods, output budget, stream escape and mixed selector modes.
Actual all-method and direct-reference launcher regressions now pass; the LSS
class-owner reference scan returned1,487 explicit edges. Proofs are in ignored
`out/tooling/`, with only bounded metadata pinned by `inventory/tooling.json`.

Bounds:64 physical DEX entries,128 logical headers per physical DEX,256MiB per
physical DEX/512MiB expanded aggregate,200,000 class definitions,128 exact method
selectors or2,048 all-method selections for one class,100,000 instructions per
selected method and20million instructions per reference scan. Output defaults
to32MiB, configurable by `--max-output-mib` up to128MiB. Failed/budget-stopped
`.partial.jsonl` files are not published receipts or usable completed evidence.
Current declaration/body/reference fixtures demonstrate source parsing only;
Android startup, caller policy correctness, hardware identity, cryptographic
acceptance and live phone behavior remain unverified.
