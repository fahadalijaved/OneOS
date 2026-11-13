# Unselected StrongAuth queue leaf

The approved offline leaf changes one queue invocation in the original ColorOS
framework. It remains **unselected and cold-start-only**. It adds no readiness,
registration, authentication or biometric-policy implementation. The earlier
[callback report](strongauth-callback-adapter.md) continues to describe the
unaltered supplied inputs and remaining adapter obligations.

Input `framework.jar` SHA256:
`d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2`.
Output `out/strongauth-queue-leaf/framework.strongauth-queue.unselected.jar`:
`df7fe651d4d593d985edee2903c7c80eb40eb79413592478b92b7f95fb487a38`.
The [inventory](../inventory/strongauth-queue-leaf.json) records exact source,
output, tool, raw-reader, code-ownership and inverse proofs.

## Exact approved cut

Owner `LockPatternUtils$StrongAuthTracker$1`, method
`onStrongAuthRequiredChanged(II)V`, `classes6.dex`, encoded method4279:

| Item | Original | Output |
| --- | --- | --- |
| PC | 17–19, three code units | same |
| Invocation | `INVOKE_VIRTUAL {v1,v0}` | `INVOKE_VIRTUAL {v0}` |
| Existing method ID | 4283: `StrongAuthTracker$H.sendMessageAtFrontOfQueue(Message)Z` | 832: `Message.sendToTarget()V` |
| Instruction bytes | `6e20bb100100` | `6e1040030000` |
| Callback signature/result | `(int flags,int user) → void` | same |

The byte interval is `[702862,702868)` inside the unchanged21-unit code item.
Source body hash is
`83d55f01ac64a4c30023a9db3777fdb423d23033bf8473b32f3472912f86813c`;
output body hash is
`5966eaea01163e441b5c62fe42aa910b5a37e208b1651bb9f92f9673c445f637`.

The canonical `Handler.sendMessage(Message)Z` reference is absent from this
DEX's21,699 method IDs. A pure method-index swap to that method was therefore
unavailable. The approved alternative changes the internal invocation receiver,
argument count and prototype to an existing wrapper. The old boolean result
was discarded; PC20 remains `RETURN_VOID`. No callback parameter/result changed.
The original redundant second handler lookup remains intact.

## Same-target source proof

Original public-final `Handler.obtainMessage(III)` delegates to
`Message.obtain(Handler,III)`. That implementation writes the same handler into
`Message.target` atPC4, then what/arg1/arg2 at6/8/10. The callback passes what1,
the full original flags and original user atPC7. Its message remainsv0 through
PC17. The tracker field is private-final; its synthetic accessor only returns
that field. No argument rewriting or new message allocation is introduced.

Both actual ColorOS and Samsung `Message.sendToTarget()` invoke canonical
`Handler.sendMessage` atPC2 and discard its boolean. ColorOS sendMessage uses
zero delay; its selected delayed implementation schedules using uptime, whereas
the original front-of-queue path enqueues with time0. Samsung's original flags
callback already uses sendToTarget. This establishes the selected ordinary-send
path through the same genuine Message target. It does not establish global
FIFO, concurrent-producer order, delivery or consumer application.

One exact-reference scan of the supplied ColorOS framework finds only this
callback'sPC17 using the selected H.front reference. Callback entry remains the
original code1 Stub dispatch; all callers, wrappers and other methods are
unchanged. The exact-reference result makes no claim about reflection or other
archives.

## Verification and selection boundary

`python -B tools/build_strongauth_queue_leaf.py` passed. All six ordinary039
DEX inputs retain38,870 class definitions. Actual output decoding confirms the
single approved invocation change and identical class/method declarations and
other owner bodies. The target has no branches, payloads or try items. All
17,065 encoded methods in the target DEX were considered for ownership;
its code range overlaps exactly its own method. Every byte outside the approved
instruction and DEX integrity fields is identical. Actual inverse and reapply
roundtrip reproduce source/output exactly. All104 archive entry payloads are
checked;103 are unchanged. The ZIP wrapper is reserialized and no JAR signing,
ART verification or Android acceptance is claimed. No malformed-byte negatives
or runtime fault campaign was run.

Selection still requires a fresh process or genuine old callback/queue/consumer
drain, actual Samsung authority and caller/user/generation admission, genuine
initial snapshot plus subscription/application ordering, Samsung original
tracker-policy delegation, real non-strong/lockout/additional-factor/finish and
Keystore policy, and acknowledged registration/removal/drain. Unknown remains
locked. This leaf changes no mask, defaults, permission, flags or success path.
The accepted OneOS permissive/relaxed platform limitations remain disclosed.
No OEM/Android code executed and no phone action occurred.
