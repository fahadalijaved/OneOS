# Whole-entry retained-capture code snapshots

**PROTO successor: 54 authored PC checks pass after independent pre-use source
clearance.** Default, `--help` and `--fixtures` make no phone calls. No ADB,
Android, OEM or native operation was executed by this author. The APK, frozen
phone proposal and permission status remain unchanged. Actual device framing and
a diagnostic writer remain unproved.

The rejected threadtime tool `b94a3446…`, its docs/inventory/freeze, PC receipts
and Table's HOLD review were copied byte-for-byte to
`out/collect-retained-capture-codes/history/b94-threadtime-hold-20261106T055732682307Z-ced1d2c0b2a54104bf571bfb7530ebb3/`.
History receipt `25cdddd8…` pins 14 files. Old fixture PASS did not clear CC-01:
text formatting prefixes each LF-separated message segment, so one unknown
message containing a newline and fixed code can become a valid-looking line.

## Root-selected filtered whole-entry route

The future single read uses the pinned existing helper/ADB on port 5038:
`logcat --proto`, main buffer, dump-and-exit, exact new PID, `-T` followed by the
root start time as **epoch seconds with `.mmm`**, `-m 128`, and only
`OneOSRetainedCaptureV2:E`. The source constructs these fixed arguments from
validated root inputs. It does not use `-B`, text output, `-t` raw-tail selection,
regex message extraction, polling or retries. An integer-only `-T` token would
mean a count; the decimal token is mandatory.

Pinned AOSP [logcat.cpp](https://android.googlesource.com/platform/system/logging/+/refs/heads/main/logcat/logcat.cpp)
blob `7e79c6d75743f4a54f0359f6dccccb348e3a9918` shows that PROTO passes through
the tag/priority-filtered `ProcessBuffer`, whereas raw BINARY bypasses it.
`PrintToProto` writes one complete message, preceded by its eight-byte native
size; the selected little-endian device profile is decoded as eight-byte LE.
The exact [schema](https://android.googlesource.com/platform/system/logging/+/refs/heads/main/logcat/logcat.proto)
blob `ecbfeee479ba27f77480a91a47878bda29120b42` declares:

| Field | Wire type / meaning |
| --- | --- |
| 1–2 | uint64 seconds and nanoseconds |
| 3 | priority enum; selected ERROR value 6 |
| 4–6 | uint64 UID, PID and TID |
| 7–8 | opaque bytes tag and complete message |
| 9 | optional process-name string, validated but never retained |

Raw source snapshot `f513f1bc…` pins both source files under ignored firmware.
This is a finite upstream profile, not Samsung binary equivalence. Root's actual
read-only preflight `81d4892a…` confirms the selected options complete with empty
output. It establishes no actual diagnostic writer or nonempty framing sample.

The selected primary
[logprint.cpp](https://android.googlesource.com/platform/system/logging/+/refs/heads/main/liblog/logprint.cpp)
blob `d5c8fd081b9813cc64bd87eeebe97bbcc3e56d0a`, `android_log_processLogBuffer`
lines 537–545/568–572, supplies the precise lengths used by PrintToProto:
the tag contains one terminal NUL; the message excludes its terminal NUL.
Accordingly, only exact `OneOSRetainedCaptureV2` **plus one NUL** is admitted.
The decoder never strips NULs or trims/splits messages. A differing live profile
is inconclusive, not silently normalized.

## Admission and privacy boundaries

Default invocation prints a PC-only status. Future `--collect` requires a
nonsymlink JSON file inside this nested project's ignored `out/`, bounded to 8192
bytes. Its exact schema remains:

| Field | Root-supplied requirement |
| --- | --- |
| `schema` | `retained-capture-code-admission/v1` |
| `serverPort` | Integer 5038 |
| `serial` | Already trusted, explicitly known serial; bounded safe characters. No enumeration or fallback. |
| `newSystemServerPid`, `previousSystemServerPid` | Distinct positive bounded integer PIDs; ambiguous reuse refuses. |
| `systemServerStartTimeTicks` | Known positive start-time string; external root precondition, not queried/authenticated by this tool. |
| `startUtc`, `endUtc` | Exact `YYYY-MM-DDTHH:MM:SS.mmmZ`, positive epoch, increasing and at most 120s apart; root supplies actual device-time bounds, not a guessed PC offset. |

The helper preserves its existing-server socket precheck, 20s child wait and
64 KiB combined output cap. It makes no pair/connect/root/server reset,
manager/scope, install, restart, log clear, phone write or security query. Its
normal ADB-client autostart race after the precheck remains an explicit
limitation. The root input file conveys operator intent only, not permission or
source/device authority.

The decoder first validates **the entire stream**, at most 128 complete frames
and 64 KiB, before selecting any record. It rejects zero/oversized/truncated
frames, noncanonical or overflowing uint64 encodings, duplicate/unknown fields,
wrong wire types, invalid optional-string UTF-8 and out-of-range nanoseconds.
Unknown schema or a malformed suffix refuses the whole snapshot; an earlier
valid entry is not published. Proto3's omitted-zero semantics are honored,
notably omitted nanoseconds mean real zero. Empty/default PID, UID, priority, tag
or message cannot become successful admission.

Valid entries must match the exact new PID, UID 1000, positive bounded TID,
ERROR 6, source-profile tag bytes and root UTC interval. Comparisons use integer
nanoseconds; retained timestamps preserve nine fractional digits. The **complete
message bytes** must equal one of seven codes, optionally with exactly the fixed
package prefix `com.appleexploit.oneos.security.retainedcapture: `:
`HOOK_INSTALLED`, `INSTALL_REFUSED`, `PERMIT_REFUSED`, `REGISTRY_BOUND`,
`REGISTRY_REFUSED`, `FAMILY_BOUND`, `FAMILY_REFUSED`.

Only `timestamp`, `pid`, `tid`, `code` survive per record. Unknown valid messages
and stale metadata retain category counts only. Raw framed bytes, message/tag/
process-name values, prefixes, Throwables, unknown data and raw stdout/stderr
remain memory-only and are never printed or stored. Read/profile errors produce
fixed unresolved/inconclusive statuses. Silence remains inconclusive.

A unique `out/retained-capture-code-snapshots/<stamp>/snapshot.json` stores only
these records/counts and fixed scope/source metadata plus the admission hash.
The serial, input path and raw admission file are not copied. Serialized output
also has a 64 KiB limit; output containment is checked within nested `out/`.

## PC verification and limits

Exact successor tool `c07f1e43…` received independent pre-use source clearance
before any successor execution. Its one authored fixture run passed 54 checks,
receipt `out/retained-capture-code-fixtures/20261106T060532661557Z-fd67591ea77d44569e103f36d8b62292/receipt.json`.
Default and help also completed on the PC without helper/ADB invocation.

The fixtures include a real CC-01 discriminator: the pinned historical text
parser admits the second formatter-prefixed line, while the successor rejects
the same whole message as one opaque proto entry. They cover omitted-zero nsec,
exact NUL handling, all seven codes, stale PID/time, lookalikes, embedded fake
headers, private optional data, schema/varint/frame bounds and malformed-suffix
refusal without prefix publication. No protobuf package was installed.

The [inventory](../inventory/collect-retained-capture-codes.json) pins the exact
source, saved fixture result and source/profile evidence. These PC checks do not
establish actual device framing, source authority, callback/capture readiness,
cleanup, authentication or any full-goal case. No live collection or new phone
approval is implied.
