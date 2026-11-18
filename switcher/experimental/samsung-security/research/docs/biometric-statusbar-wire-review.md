# Independent review: selected biometric statusbar wire

**Disposition: no new blocking source defect found.** The [statusbar card](biometric-statusbar-wire.md) correctly describes the selected original transport and its missing ownership guarantees. It remains a source/API proposal, not an implemented safe renderer path. This review uses the dependency-refreshed inventory `f584556câ€¦507d49`, freeze `04c6641câ€¦bdbd29`, and corrected prompt inventory `834670bcâ€¦9a4bf`.

[The review inventory](../inventory/biometric-statusbar-wire-review.json) records ten independent check groups over 30 selected raw method bodies. The out-only checker reads and hash-verifies saved evidence and original archives; it does not invoke the peer producer or re-query firmware. The peer's five mutation cases are accurately labeled static checker sensitivity, not OEM behavior. No OEM/Android/Binder/native code or phone operation ran. PCs below are decimal DEX code units.

## Source facts independently confirmed

- The five IStatusBarService transactions are 50â€“54, synchronous with a reply/readException. The corresponding IStatusBar transactions are 47â€“51, one-way with no reply reader. All ten selected proxy payloads preserve the original argument words, including both words of operation/request longs. Both selected Stubs read the exact corresponding sequence, enforce trailing-data framing and have the documented reply behavior.
- Show's two positional booleans remain B1 then B2 through both Binder frames and CommandQueue's SomeArgs `arg4`/`arg5`. B2's original controller use as confirmation does not establish B1's effective producer. This review does not equate B1 with raw `PromptInfo.deviceCredentialAllowed`.
- `runWithStatusBarIfPresent(action, tag)` reads `mBar` at 0. An absent bar reaches false at 17/18; RemoteException from execute at 4 reaches the same false return. All five public void wrappers discard the helper result and return. Thus even a normal synchronous service reply cannot acknowledge UI delivery or readiness.
- The documented calling-user predicate matches its actual conditional branches. It is not a comparison with showâ€™s payload user, source-session authentication or epoch validation. Original permission/user checks remain required.
- CommandQueue binds its H to the actual main Looper. Show explicitly sets its Message asynchronous; the four other selected senders do not. None of those sender facts establishes complete queue ordering or drain.
- H removes pending error/help/authenticated messages by global message code at 1600/1609/1618, before show fan-out at 1688 and before reading its request field. No request predicate precedes that cleanup span. A guard only inside AuthController would be too late to prevent those removals.
- The three update arms read only modality/message/error/vendor payloads and iterate callbacks. They carry no request/epoch and contain no such predicate before callback dispatch at 1514/1552/1586. The only selected branch in each span controls iteration completion. A check before enqueue cannot reject work that becomes stale while queued.

The resulting counterexample is a **source scheduling inference**, not an executed test: A's event can queue, A can retire and B can become current before delivery, and the unchanged update payload cannot identify A. Stale show can additionally remove queued work by global code before reaching the controller. The original card states this limitation correctly.

## Conditions retained for any later implementation

1. Keep genuine initialized endpoint/controller, canonical receiver, caller/user, resources, native and policy ownership. A normal return, matching descriptor or numeric UID is not their attestation.
2. Retain an authenticated issued source request/epoch envelope through the real delivery queue. Validate on the actual main thread before showâ€™s global cleanup and before each unscoped update can affect the current dialog. Hideâ€™s request check also needs source-owner/epoch admission.
3. Keep the admitted source/use valid through external callback fan-out, or recheck before further owned effects. The selected source loop supplies no owner lifetime fence or callback-drain acknowledgement. This review does not assert that an actual callback reentrancy failure executed.
4. Use the corrected PromptInfo contract. IdentityCheckInfoâ€™s last two values are guarded independently by actual `clearFallbackOption` and `doubleAuth` calls; effective flag-profile admission remains **open**. Matching conditional source shape is not an accepted nested wire layout. Other nested payload and vendor enum semantics remain separately required.
5. Preserve actual animated-in readiness, hardware/factor/credential results, issued reverse receiver actions and terminal-versus-resume semantics. One-way action submission, successful show enqueue and a UI callback cannot supply authentication or complete native recovery.
6. Establish real callback/consumer/queue teardown and uncertain-progress ownership. SomeArgs recycling on the selected normal path, message removal, cancellation return or an empty registration list is not full drain.

No runtime API, patch, converter, guard, firmware selection or device candidate is implemented or approved by this review. The source card is suitable for the next root-owned API/ownership decision with these conditions retained.
