# Prepared Samsung permission-check bridge

The authored, unselected PreparedSamsungPermissionBridge implements exactly one
process-local explicit-subject query: Samsung IActivityManager transaction287
checkPermissionForDevice becomes genuine ColorOS transaction264. Root approved
this API, then reviewed exact Java source SHA256
8b601fa599b211df79f360d086014d47d49a307f663ff8abbb1a7ee33316534c
without requesting a correction. No installation or authority selection follows.

The final Binder subclass exposes prepare(IBinder retainedGenuineGuestAm) and
sourceProtocolBinder(). It strongly retains the target and uses
attachInterface(null,"android.app.IActivityManager"), so the original Samsung
Stub creates its protocol Proxy rather than returning a local interface owner.
The supplied Binder is not proof of its endpoint, installed code or generation.

## Exact wire and packet ownership

Both original Proxies writeString(permission), then writeInt(pid), writeInt(uid)
and writeInt(deviceId), using synchronous flags0. Both Stubs enforce the same
token and no trailing data, then writeNoException and the actual int result.
Samsung's root dispatch287 enters the dedicated helper; guest dispatch264 enters
the corresponding direct Stub branch. The builder pins five immutable original
raw proofs for both Proxies, both root Stubs and the Samsung helper. It does not
consume a moving whole-module output receipt. No OEM source is bundled.

The bridge accepts only flag0 with a nonnull reply for the selected route. It
enforces the token, reads exactly that String and those three ints, then enforces
no remaining data. Null permission and all subject integers remain unchanged.
It creates one fresh owned request, writes the genuine guest token and original
subjects, and invokes the retained target with the borrowed original reply.
Actual transact boolean and exceptions propagate. It neither parses the reply
nor adds a grant, denial, success, exception header or retry. Finally recycles
only its own request; borrowed packets are neither recycled nor reset. Other
codes use Binder's original fallback and never numerically forward to AM.

There is no service lookup, global replacement, publication, cache access,
reflection, identity clearing, permission mutation or new lifetime API. The
outbound remote call observes the authority process UID. The explicitly queried
permission/pid/uid/deviceId remain unchanged in the API payload. This transport
does not preserve an app caller across IPC and is unsuitable as a credential
forwarding mechanism or a public arbitrary-subject permission-query service.

## Original policy and admission remain real

Samsung PermissionManager's original app-ID0/1000 shortcut grants before IPC;
its PermissionQuery stores pid but equality/hash omit it. Guest AM denies null
permission. Its component checker can grant the supplied AMS pid, then invokes
vendor/window and per-process denied-permission checks before the framework
permission owner. None of those original paths is an authenticity certificate.
Never rewrite subjects to authority/self or substitute the transport caller.
A returned permission result does not establish cache validity or grant mutation.

Actual current guest AM/code, source process/realm, original cache and feature
caller/role/user/device/operation admission remain external and unassembled.
Bootstrap must own the complete process-local service/cache map, target and
source realm for their actual lifetime and replacement/death/retirement behavior.
This helper neither installs that map nor disables/implements the original cache.
The original local/shortcut/cache paths and other AM calls remain separate gates.
It does not close Context construction, security bootstrap or any device case.

## Actual bounded build

python tools/build_samsung_permission_bridge.py passed in
out/samsung-permission-bridge/20261105T202812401709Z-2a7a249c9a664c49ba87274c539b5197.
Only the authored source was compiled using the existing pinned SDK37/JDK/D8.
Source, five raw proof inputs and toolchain hashes were checked before and after;
TMP/TEMP/JVM temporary home were stream-local, with 30-second command bounds.
The builder's immutable execution receipt remains in that unique directory.

The sole class is1964 bytes, SHA256
bcf748b6133d1c8434429c6b0f1efe6ebefff2f68779ef8882ff71e8256a29cd.
The sole DEX039 is2288 bytes, SHA256
7bcde33c348eda06778e76cbf51f9f104910ef03678d7b04aee8a64326a47f61.
Static checks verify the final Binder subclass, exact four methods, nineteen
allowed method references, own-request cleanup try region, DEX signature/checksum
and absence of OEM/SDK/test definitions. These checks do not execute Binder or
exercise malformed packets; no negative runtime fixtures or behavior tests ran.

The actual compiler emitted three Java source/target8 obsolescence warnings.
D8 warned: API37 is unsupported; use API36 or earlier. SDK37 compilation and
DEX output do not establish ART, hidden-API, native Parcel/Binder, permission or
API37 runtime acceptance. No Android/OEM code, SDK stub test, IPC, cache install,
service publication or phone action occurred. All full-goal acceptance remains
pending. The inventory and frozen manifest contain exact source/tool/input and
artifact pins; earlier independent reviews remain unchanged.
