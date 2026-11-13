# Bindings independent review

Status: final bounded source/component review accepted conditionally. The previous
transport review stays frozen.
This pass covers UserInfo conversion, StrongAuth prerequisites, storage-contract
planning, security-code-realm partitioning and the separate Android SID payload.
No runtime authority, policy readiness or phone behavior is accepted here.

## Concrete review gates

UserInfo conversion must consume all sixteen source fields and preserve the
full source record before emitting fifteen guest fields. Preserve null/list
framing, String8, signed values, flags and attributes. Guest projection is not
the Samsung policy record. Unknown authority/user/generation cannot become
user0, attributes0 or a successful partial list. Synthetic typed packets do not
prove actual Parcel framing, user-state ownership or Binder authorization.

StrongAuth wire compatibility does not supply registration acknowledgement,
initial completeness, consumer application or ordering. Preserve full source
flags and actual Samsung eligibility/higher-factor policy; neither copying a
mask nor accepting cached/default flags or the default true non-strong boolean
closes readiness. Resolve ColorOS front-of-queue delivery, stale generation,
same-authority snapshots and exact callback drain before publication.

Storage retarget planning must preserve original selected secret/HAT branches,
canonical exception behavior and cleanup. A proposed narrow interface must have
the exact same Class identity at publication and each consuming private callsite.
No name-based LocalServices alias or arbitrary HSUM/encryption/default status
may replace real native/state authority. Source rewrite spans are not an applied
DEX, inverse/type proof, coherent unlocked cache or native commit/readback proof.

The realm partition must distinguish private coherent OEM families from canonical
OS identities and explicit adaptation frontiers. Class declarations and matching
member names are insufficient. In particular, private Samsung LockPatternUtils
still resolves/caches `lock_settings`; its source-numbered requests cannot simply
reenter a guest-numbered frontend. The internal source-protocol endpoint or
injection remains a concrete owner/binding obligation. Do not infer DEX041 ART
support or complete isolation from SDK loader constructors.

The SID package may contain only the admitted authored helper definitions and
native bytes. Real Android class loading, private-target registration, global
anchor behavior and original-caller handle policy remain separate. Packaging,
headers, checksum and synthetic JNI evidence do not prove authentication.

## Reviewed source observations

The frozen UserInfoWire reads all sixteen fields before writing any projection;
SourceRecord preserves attributes as immutable metadata, and SourceList exposes
no mutable backing array. It creates no user default or policy decision. Its
strict presence0/1 and listâˆ’1 conventions reject malformed inputs beyond the
captured writers' domain. Any output write failure still needs an unpublished
output/discard contract; no actual Binder reply owner exists in this component.

The StrongAuth report identifies two one-way callbacks with matching wire,
different flags queue ordering, map-only registration replay without completeness,
separately cached queries and a real ALLOWING_BIOMETRIC mask difference. It
correctly keeps full policy delegation, higher-factor state, initial readiness
and drain unimplemented. These are supplied-source facts, not runtime evidence.

The paired inventory names final inputs and actual checks. No compiler/test,
OEM/JNI, phone, installation, configuration or Git action is part of this review.

## Final component dispositions

| Component | Accepted scope | Unresolved boundary |
| --- | --- | --- |
| UserInfo source schema and UserInfoWire | Exact sixteen-field read, immutable full data record and fifteen-field guest projection; 2,484 reported synthetic checks and six rejected unsafe variants. | Real String8 access is absent from public SDK37; no Android Packet wrapper, original object, current authority/user/generation or policy owner is supplied. |
| StrongAuth callback prerequisite | Matching two one-way callback wires, actual initial-map/query/queue behavior and source mask difference. | No runtime callback adapter, complete applied initial state, subscription barrier, real policy delegation or drain. No policy bits were patched. |
| Storage contract plan | Source-preserving three-operation interface proposal and exact instruction/field boundaries; original exception/secret/HAT/cleanup semantics retained. | No helper/provider, rewritten DEX, native/status authority or commit/readback/recovery owner. Equal-size NOP plans are not type/index/inverse or DEX041 runtime proofs. |
| Security code-realm plan | Bounded private/canonical/frontier classification, per-instance LPU route and genuine inherited LsConstants dependency. | No executable minimum, loader, subset producer, ART isolation proof or assembled constructor/state/resource/native graph. |
| SID Android payload | Exact authored helper-only DEX, frozen production ARM image and derived manifest. | No real target registration, admitted path/loader/process lifetime or Android/native authentication acceptance. |

The final UserInfo converter additionally refuses identical Packet objects
before I/O. Different wrappers can still alias one buffer; the actual owner must
prevent that, handle exception headers/cursors, supply a fresh unpublished output
and discard any partial write. Strict0/1 presence, count−1 and the maximum1024
are explicit authored bounds for the captured writers' domain. They do not prove
all native Parcel encodings or the real maximum user population. The full record
retains attributes but carries no authority/generation attestation by itself.

The StrongAuth mask check confirms 5892 versus5900 differs by bit8. The helper
therefore differs for flag8, blocks2048 on both sides and allows4096 on both
before independent policy. This is consistency with the supplied source proof,
not a replacement eligibility algorithm or additional-factor completion.
Map-only replay, silent equal/default callbacks, the default true non-strong
cache, front-of-queue delivery and separately cached queries cannot establish
an applied same-authority snapshot.

The realm report correctly records private instance field flags0x2 with
IGET/IPUT, not a static LPU cache. Each reached real instance needs its internal
source-protocol route and first-use/death/drain proof. REMOTELOCK_TYPE is actually
inherited from Samsung LsConstants; it is not a broken Samsung reference or a
reason to invent an empty rule. Canonical UserInfo projection likewise does not
make any Samsung-only getter/attributes consumer compatible automatically.

The SID ZIP's three regular stored, unencrypted entries, exact hashes/bounds,
manifest agreement, DEX039 integrity and sole helper descriptor, and frozen ARM
image/header were independently checked. Original OEM implementations, test
targets, host fault hooks and the portable oracle are absent from that payload.
The existing D8 API37/max36 warning remains; neither packaging nor the unsigned
manifest grants source authenticity, actual ART loading or real private-SPM
registration. Prior authored Windows JNI execution remains separate evidence.

## Architecture decision and review limits

**No architecture is selected or established as best by this review.** The
private-cohort plan is a conditional construction candidate, not a requirement
to host Samsung security inside guest system_server. The prior direct transport
requires facade and genuine backend co-residence in the incoming Binder process.
A separate Samsung-framework process containing both could receive ColorOS IPC
directly while preserving its native caller. Forwarding from a facade onward to
a remote backend adds a different caller/policy boundary. Comparing those options
remains the dedicated architecture review; component usability does not settle it.

Actual checks here were selected source/report reads, immutable input hashes,
UserInfo field/operation-order comparison with the pinned schema, mask-metadata
consistency, and bounded SID ZIP/DEX/header identities. Reported source-audit
assertions and JVM/compiler runs were not repeated. No broad dependency audit,
compiler/test run, OEM/JNI/Android execution, phone command, install, setting,
reboot or Git action occurred. The previous transport review remains unchanged.

This accepts only conditional source/components. A genuine current user/state/
policy authority, complete original credential/fingerprint/key/CE behavior,
readiness, one-writer commit recovery, drain and switch/return remain required.
All eighteen device cases, phone candidate, PR/beta readiness and the full goal
remain unaccepted. Implementation expansion is held for the architecture review.
