# Closed Settings process snapshot

The [guest snapshot helper](../compat/guest-fingerprint-attach/com/android/server/am/PreparedGuestFingerprintAttach.java)
keeps the exact `ProcessRecord`, application-thread wrapper, start sequence,
PID, UID and source Java thread. The source thread can compare the snapshot
once after the original Binder identity restore. The comparison requires the
same record, wrapper and tuple, and reads the current Binder caller directly.
A foreign Java thread cannot consume the snapshot. The helper rejects the
SystemServer process's own PID. It supplies no package admission, Binder
publication or enrollment query.

The [SDK 37 build](../out/guest-fingerprint-attach-build/r-dc924137/receipt.json)
emitted three definitions in a 2,800-byte DEX `752af39b`. The hidden AMS,
`ProcessRecord` and `IApplicationThread` declarations were compiler-only.
The [JVM fixture](../out/guest-fingerprint-attach-model/r-bbc22046/receipt.json)
passed 43 checks, including replacement at the same PID, an unchanged record
with a different thread, identity mismatch and replay.

## Exact staged source cut

The planned typed copy of `finishAttachApplicationInner(JII)V` retains the
same arguments and is reserved for the public wait-for-finish caller. The
existing void method remains the path for the internal no-wait caller.
On the ordinary inner completion edge, the exact record is in `v2` and
the original global monitor is held through PC 792. Read the nonvolatile
`mThread:ApplicationThreadDeferred` while the original monitor is held.
The typed copy must retain the normal monitor exit, priority reset and
trace work and carry the result through the original outer identity restore.
The failure exits supply no snapshot. The future comparison also needs
a fresh, lock-bound check of the original PID map, record and thread.
[Original caller evidence](retained-fingerprint-caller-ingress.md) ·
[Exact cut audit](../out/guest-fingerprint-attach-cut-audit/r-773f18ae/receipt.json)

The [ID pool check](../out/guest-fingerprint-attach-pool/r-1568a62b/receipt.json)
used the exact held staged `classes.dex` `bcc9cb82`. It verified that
the two planned helper references match the emitted definitions and that
the existing `mThread` field reference can be reused. The typed copy and
two helper references would consume the last three method IDs.
Using the existing `snapshot` string and keeping the typed copy's
`(JII)` arguments leaves only old string IDs 65,533 through 65,535
crossing the short-string limit. The outer comparison takes seven argument
words and requires outgoing-register and instruction-layout verification.
An [independent scan](../out/guest-fingerprint-attach-independent-id-scan/r-76ab051f/receipt.json)
checked all 49,119 code bodies. The highest actual short-string operand is
65,532 and projects to 65,535. None of the planned references requires a
jumbo widening of an original instruction.
No modified AMS DEX has been emitted.

## Remaining admission

The donor Settings manifest uses a shared system UID. The selected APK,
named package signer and installed code generation still need proof. The
original process can retain its record and Binder while AMS replaces its
`ApplicationInfo`, so package updates must also retire the old association.
The real death recipient and PID-map or thread replacement edges must retire
only the corresponding process generation. The future endpoint must join
that live guest generation to the genuine incoming Samsung Binder caller
before invoking the query. No OEM code or device action ran.
