# Narrow UserInfo reply adapter: source boundary

**Source-supported conclusion:** the selected Samsung UserManager replies can
use a small, explicit field adapter without importing another UserManagerService
merely for conversion. The actual layouts share15 fields; Samsung appends one
`attributes:int`. This is not an implemented adapter or an admitted user/policy
authority. No real user object, registry, serial, Binder, Parcel or OEM method
was read or executed. The [inventory](../inventory/userinfo-adapter-source.json)
pins44 selected method bodies, reused evidence and10 new narrow static queries.

The source archives are Samsung framework SHA8095a9ae… and ColorOS framework
SHAd5c6b7fd…. This supplements [security-user-binding](security-user-binding.md);
its original user/serial/state and local-policy obligations remain mandatory.

## Exact object schema

Both actual `UserInfo.writeToParcel` and private Parcel constructor have the
following unconditionally ordered common prefix. These are Parcel operations,
not a fixed byte-offset structure: strings have platform framing and nulls.

| Position | Field | Exact read / write operation |
| --- | --- | --- |
| 1 | `id:int` | `readInt` / `writeInt` |
| 2 | `name:String?` | `readString8` / `writeString8` |
| 3 | `iconPath:String?` | String8 |
| 4 | `flags:int` | Int |
| 5 | `userType:String?` | String8 |
| 6 | `serialNumber:int` | Int |
| 7 | `creationTime:long` | Long |
| 8 | `lastLoggedInTime:long` | Long |
| 9 | `lastLoggedInFingerprint:String?` | String8 |
| 10 | `partial:boolean` | `readBoolean` / `writeBoolean` |
| 11 | `preCreated:boolean` | Boolean |
| 12 | `profileGroupId:int` | Int |
| 13 | `guestToRemove:boolean` | Boolean |
| 14 | `restrictedProfileParentId:int` | Int |
| 15 | `profileBadge:int` | Int |
| 16, Samsung only | `attributes:int` | Int |

Samsung writes attributes at code-unit PC77 and reads it at93; ColorOS returns
after field15. Preserve signed32-bit and64-bit patterns, nullable strings and
the original userType. Do not normalize names/types, clear unknown flags, widen
serials as unsigned, or infer a missing user from transport failure. No icon
path or other field value is opened by this investigation.

The static initializer installs `UserInfo$1` as CREATOR on each side. Its typed
`createFromParcel` constructs UserInfo through the synthetic Parcel constructor,
which directly delegates to the private Parcel-only constructor above. The
generic Creator bridge delegates to that typed method. There is no object-size,
schema-version or attributes-negotiation step in these bodies. Convenient
ID/name/flags constructors are not a replacement for the complete field set.

## Selected Binder replies and list framing

| Method | Both transaction codes | Request | Successful response |
| --- | --- | --- | --- |
| `getUsers(boolean)` | 23 | Boolean | typed UserInfo list |
| `getProfiles(int,boolean)` | 24 | Int, Boolean | typed UserInfo list |
| `getUserInfo(int)` | 36 | Int | nullable typed UserInfo |

The actual proxy and Stub cases agree on these numbers and synchronous flags0.
The proxy writes descriptor `android.os.IUserManager` and reads the exception
before using its own UserInfo CREATOR. The Stub reads the request, calls
`enforceNoDataAvail`, invokes the exact method, writes `writeNoException`, then
`writeTypedList(List,int)` or `writeTypedObject(Parcelable,int)`. Keep original
arguments, caller authorization, filtering, ordering, nulls and errors. Matching
wire numbers does not establish the actual server or its authority generation.

Actual Parcel bodies on both sides establish:

- A typed object writes presence0 for null; otherwise1, followed by its object's
  `writeToParcel`. The reader consumes the marker then invokes its Creator.
- A null typed list writes count−1; a nonnull list writes its count and then one
  typed-object marker/body per element. Empty lists and null lists are distinct.
- There is no per-UserInfo length delimiter that lets a guest reader skip the
  Samsung-only field. A15-field decoder leaves attributes unread. In a list,
  the next presence-marker read then sees that integer, misframing subsequent
  elements. A single-object caller can instead silently lose the policy field.

Therefore conversion must consume **all16 fields for every nonnull Samsung
element**, then emit all15 guest fields with the correct object/list framing.
Removing four bytes once from a whole reply, forwarding a raw typed list, or
using the guest CREATOR directly on the Samsung reply is insufficient. Use exact
String8 operations, not unproved String16 substitutions. Actual Android API/access
and parcel execution still need their own reviewed implementation and tests.

## Preserve Samsung policy rather than a lossy guest authority

Retain an immutable authority-owned16-field record for the admitted user/serial/
profile generation. A15-field guest projection is presentation/API data; it is
not the policy record and must never replace it in a cache or round trip.
Guest data cannot reconstruct Samsung attributes. Unknown/missing provenance
blocks policy use instead of manufacturing attributes0 or an ordinary user0.

Selected actual getter semantics further constrain the conversion:

| Getter | Actual dependency / predicate |
| --- | --- |
| Primary, main, full, testing (both sides) | `(flags & mask) == mask`, masks1,0x4000,0x400,0x8000 respectively. Main/primary public wrappers also perform their existing deprecation logging. |
| Managed profile (both sides) | `userType` compared with exact string `android.os.usertype.profile.MANAGED`. |
| Samsung secure folder | flags0x20000 |
| Samsung SDP-not-supported secure folder | flags0x40000 |
| Samsung virtual user | flags0x80000000; preserve the sign bit. |
| Samsung super locked | If `(flags & 0x06000000) > 0`, test `(attributes & 0x1c) > 0`; otherwise test `(attributes & 0x0c) > 0`. |

The last predicate demonstrates why discarding attributes can erase real Samsung
policy. The captured guest class lacks these Samsung-specific getters/attribute
field. Unchanged imported Samsung callsites cannot simply invoke missing methods
on guest UserInfo. Either retain the coherent Samsung type in its reviewed realm,
or retarget the exact consumers to the owned record/original policy projection.
Keep all raw flag bits; this limited getter comparison is not an audit of every
guest/OEM flag consumer. Any conflicting additional guest interpretation needs
an explicit adaptation or safe optional-feature removal, not silent masking.

## Concrete future adapter contract and remaining owners

The source-supported contract is: issue the exact read operation to the admitted
original authority; preserve its exception and filtering result; decode the
complete Samsung schema under that same synchronous call/generation; retain the
full authority record; emit the exact guest projection for guest API consumers.
Preserve list count/order/null elements and reject malformed or over-bound data
without truncation/default users. Do not publish a successful partial result
while conversion or admission is unresolved. No such executable adapter or
retarget is delivered by this metadata audit.

This needs one real user/serial/profile owner, original caller/user/profile
authorization, current generation and cache invalidation/death handling. It does
not recreate those owners. The real local UserManagerInternal projections,
Samsung maintenance callback, credential-sharing properties and Supervision's
escrow policy remain separate obligations; IUserManager replies do not supply
them. Current running/unlocking/CE state also cannot be inferred from UserInfo
or a saved registry. Original user removal and cleanup require genuine current
state and policy, not a transport-created missing-user result.

OneOS stops Samsung's original system_server. A surviving or controlled-imported
authority and its state/lifecycle dependencies still must be established. This
wire conversion alone neither requires another full UserManagerService nor
proves a smaller service/state owner complete. It does not justify constructing
UMS over guest data, copying registry files, replacing authority with a snapshot,
or weakening reciprocal PIN/fingerprint/app-key/CE requirements.

Recheck retained evidence with:

```powershell
python -B tools/audit_userinfo_adapter.py --report
```

`--capture` only fills the ten exact additional static queries when missing;
it does not scan every framework method or execute Android/OEM code. Raw bodies
remain in ignored `firmware/userinfo-adapter/`, receipts in ignored `out/`.
Successful source checks do not imply actual Parcel/ART, user-state, native,
device-profile or security acceptance.
