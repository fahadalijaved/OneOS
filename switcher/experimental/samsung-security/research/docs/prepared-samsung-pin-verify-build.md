# Private PIN verify component build preparation

The frozen production source is `76c6b2b5…`. Independent source review accepted
the narrow client and corrected runner `adfae398…`. Root authorized exactly one
PC run, which completed with all six commands exiting zero: one SDK-compiled
production class, one DEX039 definition, and 59 authored synthetic scenarios /
189 checks. Independent saved-output review is separate and pending at this
report checkpoint. This is an unselected PC component, not authentication or
integration acceptance. The existing 34-pin source freeze `16956f0d…` stays
immutable; its earlier compilation-pending status is historical.

The actual work directory is
`out/prepared-samsung-pin-verify/20261106T071613736750Z-638f1cfd6dd94664b5a499aed87a6e8d`.
Receipt SHA256 is `24dbb91e52c5273f4d985695e570e1973457393046bf776331ad4ded11a7b740`.
The client class is `fba32c629427ffecd34b7359bc1a7625b7aa13e59d094935dc9687aa65850d25`;
the 4268-byte one-definition DEX is
`284d63965be5435ea4fb050aa1eb3dc35e0d21c2a254464f48b3bc348a92e2c8`.
Actual source and all three projection, one production and 25 authored runtime
class maps stayed unchanged across execution. D8's API37/max36 warning remains
in the saved log. No OEM/SDK implementation, native service or phone ran.

The first prebuild runner `7f2360b6…` had two concrete provenance gaps: staged
source hashes were not compared to intended template bytes, and after-run class
checks reused earlier path lists. The reviewed successor compares complete
intended source paths/bytes before compilation and after testing and freshly
enumerates every class-output path/hash afterward. No compiler/model run used
the earlier runner. Its exact source, reports and initial preparation freeze,
plus corrected pre-run reports, remain in private history.

Precision for the earlier source card's cleanup wording: **recycle is attempted
once for each obtained Parcel**. A throwing recycle does not establish native
release. The code attempts the second cleanup even if the first throws, preserves
the exact primary including self-suppression/suppression failure, and propagates
a cleanup failure when there was no primary. Neither the source card nor this
build claims native drain.

`tools/build_prepared_samsung_pin_verify.py` uses only the pinned existing JDK,
SDK37 and D8. It imports the unchanged parent-client bounded command function
and changes only that function instance's output root. Its commands have their
own cwd/temp/home, empty native-library directory, 512MiB heap, 45-second timeout
and 2MiB combined output cap; five JVM/compiler/classpath option variables are
removed from child environments. Global environment and old builders remain
unchanged. No command invokes an OEM/SDK runtime, Android, native service or phone.

Three compiler-only projections are generated under the new private work folder:
canonical Parcel, LockscreenCredential and VerifyCredentialResponse. Only the
used/minimum implementation declarations are projected; exact original class,
interface, field and method descriptors/access (including private constructors)
are checked against captured staged class records. Stub bodies throw and are
never packaged or executed. The projection compile uses the unchanged SDK37;
the client compile puts projection classes before SDK37 on its explicit compiler
bootclasspath. This is SDK37 plus an excluded hidden-ABI projection, not public
SDK37 API acceptance or proof of ART/hidden-API access.

The only production javac input is the frozen client. The runner requires exactly
one classfile with its exact binary name, audits its canonical method references,
and passes only that file to D8. The actual DEX must have ordinary039 integrity
and exactly one declared class. No original widget, Parcel, projection, fixture,
old transport or SDK definition is allowed in production output. D8's known
API37/max36 warning remains explicit. Unexpected class closure or compile failure
stops this attempt; it does not broaden the accepted set or retry automatically.

First-party runtime models contain no credential bytes, verifier, real exception
decoder or authentication decision. They supply canonical method mechanics to
the **unchanged SDK-compiled client class**. Runtime classpaths contain only own
model classes and that client directory; SDK, projection and OEM inputs are
excluded. A separate loader case deliberately separates the canonical framework
classes and must refuse preparation.

The cases check exact borrowed object/CREATOR/result identity, sensitive55/32 and
user/flags wire order; real entry UID and local process UID refusals; bound-user,
flags, null/subclass/non-PIN/zeroized refusals before packet emission; unchanged
arbitrary response fields; false/RPC/decode/null/malformed errors; every acquisition
and writer failure; both cleanup attempts with exact/distinct/same/disabled
suppression; no retry after uncertainty; reentry and independent concurrent
packets on their actual calling threads. They do not model successful PIN
authentication. Suppression-allocation failure is not injected through memory
exhaustion; the compiled guarded Throwable catch must be independently read.

All generated source and class bytes are pinned before/after the model run.
Source/proof/tool pins are checked before/after the entire attempt. The new
timestamped receipt records commands/logs, projection shapes, actual one-class
and DEX closure, model result and limitations. It does not rewrite the historical
source card or move a canonical selector.

Actual guest boot/ART, the active BinderProxy extension/native remote55 path,
authentic retained endpoint, physical-user mapping, source/epoch lifetime,
borrowed-credential custody, real decoder effects, complete guest local18 and
producer readiness remain outside this PC component result. It publishes no
service and grants no keyguard dismissal or security readiness.
