# Separate display metadata bridge review

**Accept the exact authored component conditionally, unselected.** No blocking
source/API or packet-ownership defect was found. This is a separate review after
the seven-slice authority-bootstrap snapshot; it does not change that snapshot
or pass its bootstrap gate.

The reviewed source is PreparedSamsungDisplayBridge, SHA256
`b4f9023c2f82aad0833d10320e31c7edefc8157454e65778f427026df02c1484`.
The final Binder subclass strongly retains the supplied target and uses a null
local interface owner. Only source71→guest44 and source86→guest59 are forwarded.
Selected calls require flag0, a reply, the real descriptor and no arguments.
Rejecting trailing data is an explicit stricter contract for the original valid
no-argument requests. Unknown codes use Binder's base handling and are not sent
numerically to DMS.

For a selected request, the bridge allocates one canonical request Parcel,
writes the guest token, and lets the actual retained target fill the same
borrowed reply. It returns the actual transact Boolean and propagates errors.
It does not fabricate a value, add a success header, parse/recast a foreign
OverlayProperties, copy a native pointer or retry. Its finally block recycles
only its own request. The borrowed packets are not retained, cleared, rewound
or recycled by authored code.

The source performs no lookup, reflection, cache installation, publication,
identity clearing or target replacement. Its outbound metadata transaction uses
the authority process's native caller identity. This is not preservation of an
app credential caller across IPC and must not be repurposed as credential
forwarding. The source proof identifies these two cached getter paths, not all
display operations.

The frozen static proof covers the selected original request/dispatch/reply
shapes, named color-space ordering and compound native serialization comparison.
That proof precedes this component and its API-not-implemented wording describes
that source-only snapshot. The later component implements transport, not an
installed cache or operational Context. This reviewer read the bounded report
and metadata without repeating its native corpus/disassembly comparison.

The independent checks matched current source/proof/tool pins, class/DEX output
identities, DEX039 SHA1/Adler32/file size and its sole class/Binder superclass.
The build owner's structural declaration/try/reference checks are reported
evidence, not independently executed Android tests. No compiler, test suite,
Android/OEM/JNI code, Binder IPC, cache installation, phone/ADB, configuration or
Git operation ran in this review. The D8 API37/max36 warning remains explicit.

Real endpoint/code/profile/current-generation admission and retained lifetime
remain external. This object has no death/retirement protocol; a strong Binder
reference is not a live, initialized DMS authority. Root must compose the complete
admitted process-local cache map and own its one pre-Context installation, without
recursive lookup or replacing global display. Subsequent display-info/cache/
callback paths, live Context execution, policy/user/state/native ownership and
actual bootstrap remain unresolved. No authority readiness, architecture choice,
phone candidate or device acceptance follows from this component.
