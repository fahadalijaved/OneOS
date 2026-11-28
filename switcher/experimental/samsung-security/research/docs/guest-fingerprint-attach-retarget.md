# Guest ActivityManager fingerprint caller retarget

The [static writer](../tools/GuestFingerprintAttachRetarget.java) takes only
the exact staged guest services `classes.dex` `bcc9cb82`. It adds one private,
observation-returning copy of `finishAttachApplicationInner(JII)V` and edits
one original method, public `finishAttachApplication(JJ)V`. The original
void inner method remains available to the original internal no-wait caller.

The [typed copy](../tools/GuestFingerprintAttachInner.java) reads the real
`ProcessRecord.mThread` under the original global monitor on the successful
edge. It preserves the monitor exit, priority reset and trace, then calls
the exact [companion snapshot helper](guest-fingerprint-attach-snapshot.md).
Both original refusal paths return null. The
[public retarget](../tools/GuestFingerprintAttachOuter.java) immediately
stores the typed result in an unnamed local and carries it through the
original Binder identity restore. The exception restore and rethrow retain
their original ordering. The result stays local and the original comparison
later overwrites it.

## Static write result

The [first writer run](../out/guest-fingerprint-attach-retarget/r-9ede9875/receipt.json)
compiled and then failed the normalized preservation check for the new typed
method. The output slot stayed empty. An
[isolated replay](../out/guest-fingerprint-attach-inner-check/r-f6c972db/receipt.json)
reproduced two differences. The mutable builder exposed 34 single-handler
entries and the serializer grouped them into 30 try ranges. It also
represented 109 end/restart debug events without the local metadata that
the decoded DEX restored. The instruction operands and flattened handler
list matched in that replay.

The follow-up source groups the original relocated try ranges and retains
the original debug local metadata. Automatic security review stopped the
worker during that correction, citing possible cybersecurity risk. The
revised source remains unverified through serialization, and there is no
verified patched DEX. The independent reader's source-only dry run covered
49,118 original coded methods. No device action occurred.

## Remaining integration

This cut uses two new method IDs. The later live comparison still needs
a rejoin to the original PID map, exact process and active thread under the
reviewed lock order. It also needs the actual named Settings package and
loaded generation, retirement and the native Binder sender. The emitted
services code would require exact companion class linkage before selection.
No new endpoint or device operation is part of this cut.
