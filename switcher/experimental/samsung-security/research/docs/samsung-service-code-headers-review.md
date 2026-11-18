# Samsung service extracts: raw code-header review

**HOLD: both previously saved DEX039 extracts change raw `outs_size` in two LockSettingsService methods.** Their body-normalization and byte-identical second emit did not establish complete source code-header preservation. This review changes no old artifact, producer, report or preservation profile; root decides the next action.

The [bounded reader](../tools/audit_samsung_service_code_headers.py) checks only the two definitions selected by the original [subset probe](samsung-dex041-rewrite.md): LockSettingsService (199 declared methods) and UserManagerService (277). All 476 have code in these literal inputs. It reads original declarations and code headers from the **intact** pinned physical DEX041 buffer, then reads both actual saved DEX039 files. It neither slices/rebases the source nor invokes a writer, compiler, OEM class or runtime. Source, compiled probe/reader classes, historical receipt, normalized evidence and saved output hashes are checked before and after inspection.

## Actual differences

Both `subset-039.dex` and `roundtrip-039.dex` are 266,472 bytes, SHA256 `80c379a3a0a9f6b94bfb45d78904fda8a1a827b46a9e7bc0f6495d8e13b2cef0`. Each has exactly the same two differences:

| Original exact member | Source `outs_size` | Each saved output | Original code offset | Output code offset |
| --- | ---: | ---: | ---: | ---: |
| `LockSettingsService.<clinit>()V` | 3 | 2 | 12,700,880 | 149,456 |
| `LockSettingsService.applyRemoteLock(int, RemoteLockInfo)boolean` | 11 | 5 | 12,680,368 | 153,080 |

The complete header tuples `(registers, ins, outs, tries, debug offset, insns_size)` are respectively `(3,0,3,0,0,51) → (3,0,2,0,0,51)` and `(38,3,11,3,0,601) → (38,3,5,3,0,601)`. Direct reads at these literal offsets independently confirm the declaration-resolved results. No UMS method drifts. No selected method identity, class/method flags, direct/virtual partition, code presence, register count, incoming words, try count or instruction-unit count differs. Thus each artifact has **2/476 changed method headers**, with only outgoing capacity changed; 474 match all requested fields.

This is preservation drift, not evidence that the outputs necessarily fail ART verification or that a credential result changed. Determining minimum required outgoing capacity, runtime validity or a repair is outside this check.

## Correct container boundary and missed dimension

Source services.jar SHA256 is `def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6`. Its single selected physical classes.dex is 28,157,552 bytes, SHA256 `6c9ac3f92a14050900b5fe9502a726cd186011a4342cb2a76c7ba5288e42c973`. Logical headers at 0 and 10,057,984 have 120-byte headers, matching physical container size/header-offset fields and 9,252/9,664 class declarations. Their logical file sizes close the original physical container. Both selected definitions belong to the second header. Table/data/map/code offsets are consumed as absolute positions in that full buffer; the DEX041 data-size/data-offset zeros are not reinterpreted using ordinary039 rules.

The bounded reader resolves exact class/method/prototype identities, encoded access/partition/code offsets, then reads `<4HII` directly from each selected code_item. Incoming-word counts also agree with static/instance flags and wide parameter words. Emitted039 SHA1/Adler32 checks pass. Pool indexes, code/debug offsets and physical header bytes are deliberately not equality requirements: pool/layout relocation is expected. This is not a full DEX verifier or an instruction/handler re-audit.

The original normalizer records `getRegisterCount()`, instructions, handlers and represented metadata; it never records raw incoming/outgoing header words. Equal normalized source/output bodies and a stable039 →039 roundtrip therefore missed these two source041 →039 changes. The prior PASS remains historical evidence for its stated represented normalization, and cannot support a complete raw-header preservation claim.

[The review inventory](../inventory/samsung-service-code-headers-review.json) pins every input and ignored per-method header/drift receipt. Root must keep these outputs unselected and withhold complete source-header-preservation acceptance until it explicitly chooses a reviewed next step. No preservation profile was expanded, no artifact was repaired, and no ART, Android, authentication, key, CE or phone acceptance follows.
