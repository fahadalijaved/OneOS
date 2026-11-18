# Independent parent-transport source/API review

Status: source-supported proposal accepted at the selected boundary; no cell,
parent-client variant, original method retarget, publication or runtime owner is
implemented by this card. No material source contradiction was found. Review
reused the frozen five-body raw evidence in
[guest-metrics-parent-transport.json](../inventory/guest-metrics-parent-transport.json)
without rerunning the collector/writer or executing OEM/Android code.

## Interception and selected collision proof

Observed ColorOS DMS BinderService.onTransact is an existing public override with
seven registers and16 instructions. Its first instruction invokes the original
IDisplayManager.Stub; only an unhandled result reaches the real extension.
The Stub enforces `android.hardware.display.IDisplayManager` for codes1 through
0xffffff at PC10, **before** the packed switch at13. That switch contains exactly
keys1…72. Thus a v1 metadata token at0x00fe0001 would fail original descriptor
enforcement before ordinary unknown-code fallback. A private-code prefix must
precede the existing override's PC0, not follow the Stub or vendor fallback.

The complete selected Java chain has no0x00fe0001 case: the concrete OPPO
extension switches only10111 and otherwise returns false; Binder superclass
recognizes only the distinct interface/dump/shell controls before default false.
The candidate is within the Stub's enforced application-code range and outside
all these selected cases. This proves a candidate allocation for this source
profile, not a universal vendor reservation or safe discovery probe on an
unadmitted live Binder. Other/native/rebuilt/installed implementations still need
source admission.

Only the exact private code may take the new prefix. Its missing/inactive cell
must return unhandled false directly; it must not fall through to the original
display parser or manufacture ABSENT. Every other code must enter the unchanged
original body, preserving existing display calls, exceptions, Binder controls
and vendor fallback. Descriptor, attachInterface, queryLocalInterface, extension
Binder and global `display` identity remain original.

The proposed prefix's five-word call fits the observed registers: outer DMS,
actual BinderService this, data, reply and flags. The added DMS method can use one
local plus its five incoming words to call cell/owner/born/data/reply/flags as a
six-register range. These are source/register feasibility observations only.
New fields/types/method references, DEX tables, branch/catch layout, caller and
inverse preservation still require a real selected artifact proof.

## Direct local delegation really changes borrowed positions

Observed `android.os.Binder.transact` is public/final, eight instructions, no
catch region. If data is nonnull it sets position0 at3, directly calls the same
object's virtual onTransact at6, and **only after normal return** resets nonnull
reply position0 at12 before returning the actual Boolean. False is also a normal
return. A thrown original error bypasses that reply reset; data/reply stay where
execution reached them.

Calling the internally owned actual final PreparedGuestMetricsEndpoint's
protocolBinder().transact(1, borrowedData, borrowedReply, originalFlags) therefore
has a concrete Java-local route, not a BinderProxy hop. It performs no explicit
identity clear or thread hop. The frozen Endpoint itself does not reset/recycle
borrowed packets, but the canonical local Binder layer does reset positions.
End-to-end position immutability would be a false claim. No manual rewind,
clear, recycle, retry or fabricated reply is justified on failure.

The source path supports the same incoming native-caller frame; it does not
execute native Binder/Parcel or prove actual UID/PID behavior. The existing
Producer still reads real calling identity and uses the original getter/access
policy. Direct RemoteException/RuntimeException/Error behavior and the Endpoint's
checked-fault conversion remain intact; cross-process exception identity/native
serialization are separate.

## Real acquisition and the still-proposed cell

Frozen original evidence supplies a genuine future acquisition: DMS.onStart's
born Binder v0 survives through its normal tail after both original LocalService
publications. Matching phase100 must finish the default-display/virtual-adapter
wait, extension and remaining tail before activation. Those previously reviewed
source facts are reused; no original lifecycle event was observed here.

The proposed private DMS field/new dispatch method/typed cell are **future code**.
Passing this/actual born Binder and comparing their retained identities can bind
the route to that pair, but cannot itself prove source/loader/phase admission.
The full helper closure must be visible to the actual DMS defining loader, even
where verification/member resolution occurs before the feature becomes ACTIVE.
A default-OFF flag, arbitrary Object anchor, same-name Class or app DEX is not a
replacement for actual source/member/loader admission.

The selected cell must own exactly its captured DMS/born pair and internally
created final Endpoint, admit only matching ACTIVE work, and retain active or
uncertain stacks. It must not accept a caller-provided substitute Binder or
generic Boolean authority callback. Completed retirement must include actual
Endpoint.retire, not merely a cell flag: already-admitted calls can otherwise
enter the still-active Endpoint in that interval. Replies admitted before the
Endpoint fence may still arrive later; cell/Endpoint Java counts are not native
Binder/DMS/callback/consumer/global drain. No borrowed service/loader disposal
follows from zero counts.

Removing a new alias avoids that additional publication/readback race. It does
not prove that the existing global parent was published, discoverable, current,
or associated with this source generation. Actual parent acquisition and
post-return/epoch/death/consumer checks remain required.

## Client consequence and remaining gates

| Current/proposed binding | Required interpretation |
| --- | --- |
| Frozen client afd99…, transaction1 | Standalone private Endpoint only; direct binding to original DMS is invalid. |
| Proposed prepareParent(real DMS), internally fixed0x00fe0001 | Separate source-approved class/mode/variant, preserving v1 framing, target-specific Parcel.obtain, cleanup and absence rules. Not emitted by this source proposal. |

No public caller-supplied transaction number is justified. An extra wrapper to
translate1→high would introduce another Binder/Parcel target question; the
proposal correctly avoids it. The factory name is conceptual, not permission to
rewrite the frozen client: root can choose a separately reviewed parent-client
class. That fixed binding still does not attest the actual parent/source/epoch.
An expanded native-header profile requires its own source/code review and cannot
be inferred from this transport proposal. Full AppOps/StrictMode header
compatibility remains required before integration/full-goal completion.

OneOS selected patched bytes, unused-code admission in that actual chain,
classloader/helper closure, default-OFF configuration producer, lifecycle cell,
three body retargets plus new members, inverse proof and native dispatch remain
unimplemented/unverified. Samsung CompatSandbox/ResourcesManager/configuration/
CompatibilityInfo, boot-helper visibility/callsite selection and complete
process-local display mapping remain external. This is a bounded source/API
review, not a working transport, Context, hardware or security acceptance.
