# Default-off retained SystemServer capture diagnostic

**Postexecution report amendment.** The signed APK is 21,104 bytes, SHA256
`bb0eba1047608b153d5a8f072ac334a496a42c32a19abf9fe3661a9dce766355`.
The final [validation inventory](../inventory/retained-capture-probe.json) records
`PASS_PC_APK_ONLY`, receipt `95d8eb9e…`. The APK has not been installed, activated
or selected. The [phone proposal](retained-capture-phone-review.md) is a separate
unapproved review document.

This is a separate API102 diagnostic APK for the exact captured Samsung SDK37
profile. PC compilation/signing cannot prove
Vector delivery, ART placement, an existing owner graph, or security readiness.
Root owns any later activation/device proposal; this build grants none.

The package is `com.appleexploit.oneos.security.retainedcapture`. Modern metadata
sets static scope `android`, API102 and no hot reload. There is no activity,
permission request, native library, boot receiver, service, polling worker, or
Looper creation. SDK/API/compiler/model/OEM definitions must not enter its DEX.

`onModuleLoaded` requires SystemServer placement reported by Vector, UID1000,
API102 and exact recorded MODEL `SM-S948U1`, SDK37, DISPLAY
`CP2A.260605.016.S948U1UES4BZIG` and recorded fingerprint. Property equality is
only a restriction: OneOS can preserve host properties, so it does not establish
ordinary OneUI/source namespace/authority. External approved launch/source-view
checks remain necessary. Android Build/reflection/file/hook/module operations
are not claimed inert.

`onSystemServerStarting` uses Vector's supplied ClassLoader to resolve without
initialization the **actual** public-final Samsung method
`SystemServiceManager.startBootPhase(TimingsTraceAndSlog,int):void`. Its pinned
original method body hash is `3224ace19b31677562481511725ac608298c83be43d43b1f7c5518901d70a567`,
full-container logical header0 in services `def967fb…`. There is no fabricated
`(Context,int)` overload. The timing object and arguments remain untouched.

One PASSTHROUGH hook calls `chain.proceed()` **outside** its own catch. Original
returns and Throwables propagate. After an original normal return, only phase1000
can consume the one-attempt latch. Actual main-thread/UID/property/permit checks
precede `captureExisting()`. The genuine returned capture is retained before
`checkStillBound()` or logging. The hook/capture remain process-lifetime owners;
there is no unhook, close, retry, timer, refresh or active-stack cleanup.
Acknowledged nonnull exact-target HookHandle admission is required: an installation
that partially takes effect then throws/returns null stays pass-through and cannot
capture. Unknown installed hooks are never interpreted as successful registration.

The module emits only these fixed codes through Vector's logger:
`HOOK_INSTALLED`, `INSTALL_REFUSED`, `CAPTURE_BOUND`, `CAPTURE_REFUSED`. It never
logs Throwable text/stack, users, objects, paths, tokens or captured state. Missing
or invalid request during registration is silent and creates zero hooks. A later
request does not cause polling/registration; a new approved lifecycle is required.

The installed Vector source has both early and late SystemServer callback paths:
`p.intercept` dispatches `t2.c` before its original proceed, while `u1.b(ZZ)` also
dispatches it after reporting live critical services. Therefore the callback name
does not guarantee arrival before phase1000. Late activation can yield
HOOK_INSTALLED with **no capture that boot**. There is no current-phase backfill,
phase replay, polling or restart in this APK. Required timely delivery is a
separate later proposal/admission condition.

## Dedicated operator permit

The fixed directory is `/data/local/tmp/oneos-samsung-security-capture`, owned
root:1000 with exact0750 permissions. The fixed `request-v1` must be a nonsymlink
regular root:1000 file, exact0440, link count1 and exactly the ASCII bytes
`CAPTURE_USER_REGISTRY_V1\n`. This is an operator diagnostic permit, not a secret,
realm identity or security/native authority. The APK never creates/changes it or
any OneOS-owned file.

Public SDK37 exposes `Os.open/fstat/lstat/read/close`, but not `openat`. The code
opens the fixed directory O_RDONLY|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK, immediately
requires the held fd's directory type, root ownership, exact mode and matching
device/inode identity **before** opening the request. It never reads directory
contents. It then opens only the fixed request with
O_RDONLY|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK. It bounds reads to marker+1 and a finite
call count, requires exact content and explicit EOF, rechecks held file identity,
named request identity and named/held directory identity. All owned descriptors
are closed; any denial, interruption, mismatch or close failure refuses admission.
No owner/group writable permit or symlink is accepted. Root-owned parent control
is trusted; these pathname rechecks **do not provide atomic openat resolution**,
or protect against a malicious root replacing/replacing-back objects. Removal
between registration and phase1000 refuses capture, but does not remove the
process-lifetime pass-through hook.

The initial PC attempt `031615…586001ef` failed at javac because SDK37 omits the
public `OsConstants.O_DIRECTORY` symbol (receipt `7925cb71…`). Its source,
commands, manifest and snapshots remain immutable; it produced no APK. Root and
independent review approved only omission of that unavailable flag: directory
enforcement uses the existing immediate fstat type/identity validation instead.
There is no guessed native ABI constant or compiler-only projection. A separate
successor input manifest records the correction; the failed attempt is not
relabeled as successful.

## Build/review boundary

The source-build entry
`tools/build_retained_capture_probe.py --manifest <frozen-own-out-manifest>`
requires independently source-reviewed inputs and the reviewed/built capture
component. It snapshots direct sources/evidence and stages the exact two reviewed
SDK-compiled Capture class files from the immutable `030902` component run
(`2b3f547c…` and `d1849091…`), verifying byte identity before/after. It compiles only
Module and PermitFile with source8/target8 against pinned SDK37/API102 plus those
staged classes, then admits exactly four DEX definitions (Module, PermitFile,
Capture, Capture$Metadata). Capture source `26fcbb30…` remains a literal input;
no Capture source recompile or model classes are included. No moving component
build receipt is a producer input. Literal installed Vector
declarations are checked statically; actual callback/exception dispatcher review
is separate. Existing local preview signing key is read only.

Each bounded command uses its unique repository output cwd, local TMP/TEMP/JVM
home and removes CLASSPATH/JAVA_TOOL_OPTIONS/_JAVA_OPTIONS/JDK_JAVA_OPTIONS/
JDK_JAVAC_OPTIONS case-insensitively. Output is capped while draining at2MiB;
each command has45s maximum. The build checks source/tool hashes before/after,
actual class/DEX isolation/integrity, resource manifest, APK signature, alignment,
CRC and descriptor bytes. D8's requested API37/max-supported36 warning is retained.
There is no SDK/API/OEM code execution, ADB, installation or phone permission.

### Actual continuation and preservation evidence

The Windows native archive-output crash cause remains unassigned. No security
settings, exclusions, tool installation or compiler/profile workaround was used.
Each failed receipt, executed tool snapshot and source/input manifest remains
unchanged:

| Stage / receipt prefix | Actual terminal result |
| --- | --- |
| `031615` / `7925cb71` | Javac refused the SDK-unavailable O_DIRECTORY field; no DEX/APK. |
| `031917` / `c8e95950` | Corrected javac and D8 passed, exact four definitions; AAPT2 resource-ZIP output crashed. |
| `032456` / `e94b2e5d` | Single-resource compilation to a flat directory passed; AAPT2 APK output crashed. |
| `032821` / `d4abe0b8` | Directory linking and Python ZIP passed; native zipalign output crashed. |
| `033711` / `d7231021` | Narrow ZIP padding, signing, signature verification, read-only zipalign and badging passed; wrapper refused the newer minSdkVersion label. |
| `034616` / `95d8eb9e` | Separate validation-only finalizer passed; zero new build/verifier subprocesses and no re-signing. |

The single compiled DEX remains
`7d8a25d1435a156c3e5a1179b7c47123108ada8436ebb793ee8f8cfe96cba43b`.
No javac/D8 work repeated after `031917`. Later stages reused exact immutable
products. Alignment changed only the local resource-table padding plus necessary
ZIP offset relocations, with an exact inverse to the original unsigned ZIP.
Signing preserved all six original entry payloads, compressed streams and central
metadata. The only three additional entries are exact pinned signer metadata;
the signed resource table remains stored and four-byte aligned. Actual SDK
verification reports **v3=true, v1=false**; there is no v1 acceptance claim.
The certificate SHA256 is
`ad40f7c185abb46a5ba4798625e3245333987594379e5014aa0c977e69febfc9`.

The finalizer `--verify-signed` has fixed saved-artifact/log prerequisites; it is
not a clean-checkout APK build or a request to repeat historical failed stages.
The actually executed signing wrapper `f2c07ef9…` and strict failed receipt are
preserved. The succeeding validator `52567706…` checks the exact SDK37
`minSdkVersion:'37'` label, exact nine-entry signer closure, actual alignment and
all remaining payload guards without changing the signed APK.

The former producer-input report, SHA `fcd427a2…`, and exact capture source
`26fcbb30…` were copied byte-for-byte to the private history directory
`out/retained-capture-probe/history/postexecution-report-20261106T040027092233Z-9ab3ad4463554afe8c73e1417f34e3af/`.
This amended report is **not** substituted into any historical producer receipt.
Later capture successors are excluded from this v1 APK.

CAPTURE_BOUND would mean only that the source-checked component returned and its
immediate same-binding check completed in that callback. It would not mean real
user/native generation, lifecycle leases, CE/key/auth/security admission, switch
survival or a retained initialized authority. Captured private owners remain
unexposed. The component's package-private future control getters are unused.

Independent review: [retained capture probe](retained-capture-probe-review.md).
