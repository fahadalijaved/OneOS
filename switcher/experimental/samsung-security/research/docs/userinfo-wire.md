# Authored UserInfo wire conversion

**Implemented and verified on synthetic operation tapes only.**
[UserInfoWire](../compat/src/com/appleexploit/oneos/security/userinfo/UserInfoWire.java)
reads the proven Samsung16-field typed object/list into immutable authored
metadata, and serializes the exact ColorOS15-field projection. It neither
constructs original UserInfo objects nor supplies a real user authority,
generation, permission or policy result. It is not selected in the earlier
transport build and is not an Android candidate.

The exact input map is pinned by
[userinfo-adapter-source.json](../inventory/userinfo-adapter-source.json),
SHA256 `399a2f12da177046f7dd8669d4f2a4abe64a28098ae9fd6d5846939c1bb4ac0a`.
The converter preserves `id`, nullable `name`/`iconPath`, all32 `flags` bits,
nullable `userType`, signed `serialNumber`, both64-bit timestamps, nullable
fingerprint, the three booleans, profile group/parent/badge and all32 Samsung
`attributes` bits. No normalization, masking, attributes0 reconstruction,
default user, policy helper or successful error fallback is supplied.

## Packet and ownership contract

`Packet` exposes only read/write Int, Long, String8 and Boolean operations.
Implementations must perform those exact genuine operations. This abstraction
does not prove a Packet's origin, backend, native encoding or buffer identity.
No original/SDK classes are referenced by the production helper.

- `readSourceObject(Packet)` consumes the typed presence marker and, for a
  nonnull object, all16 source fields. `SourceRecord` has16 final primitive or
  String fields and no retained Packet, mutable array or original object.
- `readSourceList(Packet,maximumCount)` consumes the list count and each typed
  object. `SourceList` privately owns its fixed array and exposes only size/get;
  entries can be null and records are immutable.
- `writeGuestObject`/`writeGuestList` emit only the exact15 common fields and
  the corresponding presence/count framing. The full source metadata is retained
  separately; guest output cannot become a Samsung policy record.
- `convertObject`/`convertList` decode completely, serialize the projection and
  return the full source record/list. They require distinct source and guest
  Packet instances **before any read or write**. The external owner must also
  prevent two different wrappers from aliasing the same underlying buffer.

The caller positions source and destination at the typed presence marker or list
count, after independently handling any Binder reply exception/header. No
exception/header parsing, cursor reset, full-message consumption, Binder dispatch
or original object reconstruction is inferred. Trailing source data is left for
the caller; it is not silently consumed.

The caller must supply a fresh, unpublished destination, own both buffers during
the synchronous call and retain the complete source metadata under its genuine
authority/user/generation policy. A source failure produces no successful record
or fallback projection. Underlying read/write exceptions propagate unchanged.
A destination write can leave a partial prefix; the caller must discard it and
must not publish it as a successful reply. There is no rollback or rewind.

## Strict framing and bounds

Presence accepts only0/null or1/non-null. Lists accept count−1/null or a count
from0 through the explicit caller maximum, with a hard maximum1024. Zero-length
and null lists remain distinct; null entries retain their position. A bound can
be0. Invalid bounds/counts are rejected before array allocation or output; an
oversized output list is rejected before writing its count. No truncation occurs.

These guards are deliberately stricter than the original Parcel readers, which
can interpret other nonzero presence or negative list markers. They admit the
canonical0/1 and−1 encodings produced by the selected original writers; broader
malformed encodings are not promoted to success. The hard ceiling is an authored
defensive limit, not proof of the actual number of users. A real composition must
choose a sufficient reviewed maximum and treat an exceeded bound as unresolved.

## Verification and Android boundary

```powershell
python -B tools/test_userinfo_wire.py
```

[The runner](../tools/test_userinfo_wire.py) compiles only the two authored Java
sources using the existing JBR, `-proc:none -source 8 -target 8`, with local
TMP/TEMP/JVM temporary directory/user home and bounded30-second/1MiB children.
Class files have version52. This avoids the known JBR `--release 8` resource-close
failure; it does not establish Java8 library/API availability. Javac's obsolete
source/target and missing bootstrap-classpath warnings remain in the logs.

The final run ended0 with2,484 checks. The independent test oracle uses literal
source-derived field kinds and synthetic typed-operation cells. It checks every
field over64 varied records, raw flags/attributes, nullable/unicode strings,
long values, exact cursor progression, object/list nulls, two-element and mixed
null-element lists, maximum count, malformed count/presence, truncation, operation
type mismatch, exception identity, immutability and partial-output failure.
Naive15-field reading of a synthetic two-element Samsung list fails at the extra
attributes word. Distinct attribute values retain distinct SourceRecords while
their guest projection is intentionally identical; reading that projection back
as a source record fails instead of defaulting attributes.

Six compiled unsafe source variants fail the same tests: dropped source
attributes, appended guest attributes, wrong guest ID, removed same-packet guard,
ignored count limit and missing null-object marker. These are authored JVM
checks, not execution of OEM implementations or Android Parcel emulation.
In particular, the String8/Boolean operation oracle does **not** prove Android's
native UTF8 representation, alignment, malformed-string handling or Binder/ART
behavior.

Actual pinned SDK37 `android.jar` was inspected with javap, without executing any
Android classes. Its public Parcel surface contains the six primitive operations
but omits `readString8` and `writeString8`. Therefore **no Android wrapper was
compiled or supplied**, and no String16 substitution, reflection fallback or
compiler-only stub was fabricated. Binding the exact genuine String8 operations
under a reviewed runtime/API policy remains open.

The final receipt is
`out/userinfo-wire/20261105T180908367039Z-d80c1f703743419a949b3faee294b746/receipt.json`,
mirrored in [userinfo-wire.json](../inventory/userinfo-wire.json). It records
input/toolchain hashes before/after, source field-map pin, compile/test logs,
class hashes, six negative variants and the exact SDK visibility result. The
earlier run's SDK visibility probe incorrectly required a `final` modifier;
the final runner ignores that irrelevant modifier and still identifies the two
missing String8 methods. Production source and tests were unchanged by that
probe correction; the final receipt comes from an actual successful run.

No live user data was obtained, logged or copied to PC. No Android/OEM class,
JNI, service, device, original registry or credential operation ran. Original
user/currentness/authority admission, authorization, caches, policy ownership,
real buffer access and complete security integration remain external and
unimplemented. All reciprocal PIN/fingerprint, policy, app-key and CE requirements
remain intact.
