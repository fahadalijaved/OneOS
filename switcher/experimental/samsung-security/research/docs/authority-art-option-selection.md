# Captured Samsung ART option-selection constraints

The bounded Sol attempt establishes actual Samsung parser declarations and
image-selection branches. It does **not** establish repeated-option assignment
precedence, actual selected image paths, working in-memory compilation, or a
ready launch recipe. `selected=false`. No OEM/native code, VM, compiler or device
operation ran. Previous boot, VM-options and quiescence cards remain unchanged.

Only `/apex/com.android.art/lib64/libart.so` was extracted from the existing
mounted capture: 15,010,176 bytes, SHA256
`4166f04af3a71286ed0c8c760f0555a7edf213495f9b32ddc842783287aa91fa`.
Its active and versioned manifest entries have the same hash. The acquisition
receipt records the exact tar header/data offsets and reuses prior strict tar
verification; it does not rehash or extract the whole OS. Existing ELF parsing,
minidebug symbols and Capstone 5.0.6 decode nine complete bounded functions,
4,669 instructions. All PCs below are ELF virtual addresses, not live addresses.
Raw OEM evidence stays in `firmware/authority-art-option-selection/`.

## Actual entry edges

| Captured edge | Call PC | Actual target |
| --- | --- | --- |
| Exported `JNI_CreateJavaVM` | `0x8a5114` | `Runtime::Create(options,bool)` |
| `Runtime::Create(options,bool)` | `0x46c7d0` | `Runtime::ParseOptions` |
| `Runtime::ParseOptions` | `0x46c904` | `ParsedOptions::Parse` |
| `ParsedOptions::Parse` | `0x597a80` | `ParsedOptions::DoParse` |
| `DoParse` | `0x597bac` / `0x597be8` | `MakeParser` / `CmdlineParser::Parse` |
| Successful parsed-map creation path | `0x46c7dc`, then `0x46c86c` | `Runtime::Create(map)`, then `Runtime::Init(map)` |

The exported JNI body copies the passed VM options and forwards the
ignore-unrecognized byte. The exact initializer is
`_ZN3art7Runtime4InitEONS_18RuntimeArgumentMapE` at `0x591f7c`, size 17,128;
its body is outside this bounded decode. This proves edges in this captured
library. It does not prove that the prior AndroidRuntime wrapper's indirect
JNI slot resolves to this ELF in a future process.

## Registered options and keys

`MakeParser(bool)` starts at `0x51c8ec`, size 13,920. Its actual Define/typed
builder/IntoKey sequences reference these literal strings and GOT relocations:

| Option grammar | String PC | Key GOT load PC |
| --- | --- | --- |
| `-Xbootclasspath:_` | `0x51cbb0` | `0x51cbe4`: `BootClassPath` |
| `-Ximage:_` | `0x51d244` | `0x51d278`: `Image` |
| `-Xforcejitzygote` | `0x51d288` | `0x51d2ac`: `ForceJitZygote` |
| `-Xallowinmemorycompilation` | `0x51d2b8` | `0x51d2ec`: `AllowInMemoryCompilation` |
| `-Xbootclasspath-locations:_` | `0x51d328` | `0x51d35c`: `BootClassPathLocations` |

Image and bootclasspath use the actual colon-separated `ParseStringList<':'>`
typed builder. This establishes registered syntax and binding, rather than
treating a string occurrence as parser support. The additional BCP fd/image/
VDEX/OAT declarations are visible in the same selected function but are not an
admitted launcher strategy.

## Concrete Samsung branches

**Image and force-JIT conflict.** `DoParse` (`0x597b18`, size 2,612) tests the
`ForceJitZygote` key at `0x597dec..0x597df4`. If present, it obtains the `Image`
key at `0x5982d8` and branches at `0x5982e4` to the actual error string
`-Ximage and -Xforcejitzygote cannot be specified together` (`0x598540`), then
calls `Usage` at `0x598548`. Thus a caller image entry cannot simply override
AndroidRuntime's property-generated force-JIT entry through insertion order.
If Image is absent, it calls imported `GetJitZygoteBootImageLocation()` at
`0x5982ec`, splits its result and sets `Image` at `0x59830c`.

`Usage` itself is captured (`0x946c0c`, 564 bytes). After printing, it loads the
configured exit callback from `this+0x10` (`0x946db4`), supplies nonzero status
for this nonnull error (`0x946db8`), and invokes it (`0x946dbc`). `Parse` initially
loads libc `exit` at `0x597a6c`; however, `ProcessSpecialOptions` can process
hook-bearing VM entries before ordinary parsing. The prior AndroidRuntime card
already contains a native `exit` option. This card leaves that override's exact
callback target unresolved; the error path is not recovery or successful
precedence, and no UI readiness follows.

**In-memory permission.** The actual `Zygote` key test at `0x597e00..0x597e08`
branches to `0x598334`; `0x59833c/0x598340` set the
`AllowInMemoryCompilation` key, then rejoin. The explicit flag above is also
registered. A proposed standalone process has no inferred zygote key or
permission. This key says nothing by itself about usable DEX, profiles,
compiler/native dependencies, memory or coherent image reconstruction.

**Bootclasspath environment fallback.** The explicit `BootClassPath` iterator
is captured at `0x597c84/0x597c88`, before `getenv("BOOTCLASSPATH")` at
`0x597cb0`. The split environment value reaches `SetIfMissing` at `0x597cd8`.
Its actual 104-byte body (`0x598598`) tests that key: a populated existing value
returns unchanged; missing/null storage takes the Set tail. This is a concrete
explicit-key/environment relationship. It does not establish how multiple
explicit bootclasspath occurrences combine.

**Conditional default image.** After the compiler-callback lookup at
`0x597e18..0x597e28`, `0x598348..0x598364` excludes a previously captured
explicit bootclasspath key and an existing Image key. Only the remaining path
reads `DenyArtApexDataFiles`, calls `GetAndroidRoot`, and calls imported
`GetDefaultBootImageLocation(root,deny)` at `0x598398`. It splits/sets the
returned image list. The saved explicit-BCP iterator precedes environment
fallback, so this is not a rule that any BOOTCLASSPATH environment value disables
default images. Both image-location helpers are undefined imports in this ELF;
their returned paths are not recovered here. `libartbase.so` is DT_NEEDED, but
that alone is not a verified defining-library or live-linker binding.

## Exact remaining frontier

Repeated explicit `Image`/`BootClassPath` occurrence behavior remains delegated
to the concrete `CmdlineParser::Parse(vector)` at `0x5d3d38` (128 bytes), its
`Parse(TokenRange&&)` at `0x5d3db8` (1,328 bytes), and typed `IntoKey` at
`0x608c58`. Those bodies/callbacks are not expanded in this attempt; no blanket
“last wins,” list replacement or append claim is made. Hook overriding remains
at actual `ParsedOptions::ProcessSpecialOptions`, `0x3cd8cc`, size 860. The
inventory records exact mangled symbols for these finite frontiers.

The prior AOSP references remain useful mechanism comparisons, but none of the
assertions above assigns Samsung an AOSP source revision. Still required before
selection: exact future argv/environment/ordered VM options and relevant
property/server-flag values; the actual library binding and imported image
helpers; selected image/OAT/VDEX/data-cache validation; real in-memory compile
prerequisites; and the entire modified boot/helper closure before first class
resolution. Original-authority drain and guest display startup remain separate
open gates. No global property changes or ready command line are emitted.

Recheck: `python tools/audit_authority_art_options.py`. It verifies exact source,
function/instruction bytes, branch/key assertions and all six old-card pins,
then emits this stream's inventory/check/freeze metadata. Bounded acquisition
and static decoding are explicit `--extract`, `--symbols`, `--capture` modes.
