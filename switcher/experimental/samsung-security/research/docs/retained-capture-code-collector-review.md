# Retained-capture code collector: independent review

**The PROTO successor closes CC-01 in the reviewed PC component.** Exact tool
`c07f1e437c7a0d1bbe118b84ee3904d69fa0429fe7e2c23104c8dd7da7233bf6`
received pre-use source clearance, then the author completed one saved 54-check
authored fixture run. This review read that result; it did not replay it. No
material source/privacy defect remains in this bounded scope. This is not phone
approval, evidence of a real writer, or security/native/readiness acceptance.

## CC-01 and preserved history

The rejected `b94a3446…` collector matched LF-separated threadtime lines. AOSP's
formatter repeats a header for each segment of one multiline message. A single
unknown message containing `unknown\nFAMILY_BOUND` could therefore yield an
admitted code. The initial HOLD remains byte-for-byte under
`out/retained-capture-code-collector-review/history/text-HOLD-816fb994/`, including
freeze `816fb994…` and history manifest `3fa1ba49…`.

The successor compares the complete PROTO message bytes with the exact seven
bare or fixed-package-prefixed codes. It never splits or trims the message.
The author's discriminator demonstrates the old parser's false admission and
the new parser's refusal on authored inputs. Embedded LF, fake text headers,
trailing payload and terminal message NUL cannot become an admitted code.

## Source and parser readback

Pinned [logcat.cpp](https://android.googlesource.com/platform/system/logging/+/refs/heads/main/logcat/logcat.cpp)
blob `7e79c6d7…` sends PROTO through tag/priority filtering and serializes a
complete entry with an eight-byte size. BINARY bypasses that filter and is not
selected. The pinned proto3 schema defines fields 1–9. Primary
[logprint.cpp](https://android.googlesource.com/platform/system/logging/+/refs/heads/main/liblog/logprint.cpp)
blob `d5c8fd08…` supplies a normal tag including one terminal NUL and a message
excluding its terminal NUL; the collector matches those exact bytes. These are
upstream source facts, not identification of the installed Samsung implementation.

The collector validates the **entire** little-endian framed stream before
selecting records: at most 64 KiB/128 frames; complete nonzero bounded lengths;
canonical uint64 values; unique known fields and exact wire types; bounded
length-delimited fields; valid optional-string UTF-8; nanoseconds below one
billion. Omitted scalar zero semantics are preserved, including omitted nsec.
Unknown schema or a malformed suffix refuses the whole result, with no earlier
code prefix published. Optional process-name data is not retained.

Selection checks the supplied new PID, positive bounded TID, ERROR 6, UID 1000,
exact tag and integer-nanosecond interval. UID is a profile filter, not authority
attestation. Only `timestamp`, `pid`, `tid`, `code` survive; timestamps preserve
nanoseconds. Unknown valid messages/metadata retain fixed category counts only.

## Command, privacy and lifetime limits

Default/help/fixtures have no ADB call path. Explicit collection reads an
8192-byte-bounded admission file within nested `out/`, requires the exact known
serial/5038 profile and builds fixed `--proto -b main -d --pid=… -T <epoch.mmm>
-m 128 -s OneOSRetainedCaptureV2:E` arguments. Decimal `-T` avoids count semantics.
No install, restart, root, setting, log clear, phone write, arbitrary command,
transport discovery, polling or retry is present. Source and admission readback
pins are checked before publishing the output.

Raw bytes, messages, process names, stderr and exception text are neither printed
nor stored. Fixed error statuses retain no partial result. Output is bounded and
uses a unique fixed directory within nested `out/`; callers cannot choose an
output path. The reused helper's 20-second child wait, combined byte cap and
additional bounded reader joins are not a strict 20-second total deadline. Its
existing-server precheck retains the already disclosed ADB autostart race.

Root supplies trusted transport, fresh PID/starttime and actual device-time
interval. The validated starttime is not queried by this tool. The empty device
preflight proves selected flag acceptance only; no nonempty framing or real
diagnostic writer was observed. Differences fail inconclusively. Codes remain
observations, not capture/authentication/cleanup success.

The reviewer executed no collector, fixtures, suite/replay, ADB, Android or OEM
code. Saved author receipt records 54 PC checks and zero phone calls. Exact
source, history, source-evidence and saved-result pins are in the matching
inventory and `out/retained-capture-code-collector-review/FROZEN.json`.
