# Credential transport PC build boundary

The [runner](../tools/test_credential_transport.py) builds one explicit, frozen
authored source snapshot. Production/test/Android-wrapper owners supply final
pins before the final run. A source file appearing on disk is not automatically
selected. Shared APIs remain root-owned. This report does not accept the real
Samsung backend, Binder callers, Android runtime or any phone behavior.

The final manifest lives beneath ignored `out/credential-transport/` and uses
schema `credential-transport-sources/v1`, `frozen:true`, and explicit `pure`,
`android`, `tests` lists. Every row supplies repository-relative `path` and exact
`sha256`; test rows also supply their authored fully qualified `main` class,
explicit `success` fields and `args` (empty or the fixed `PROJECT_ROOT` token).
Only the transport namespace beneath the three corresponding `compat/` source
roots is admitted. All lists are bounded, and duplicate/outside paths, missing
pins, changed bytes and unexpected manifest fields are refused.
The `dependencies` list also pins the exact `inventory/construction-protocol.json`
read by the route test, before and after the build.

```powershell
python -B tools/test_credential_transport.py --manifest out/credential-transport/FROZEN.json --check-manifest
python -B tools/test_credential_transport.py --manifest out/credential-transport/FROZEN.json
```

The first command only validates the frozen source map. The second creates an
exclusive timestamp/UUID run directory, prints its exact handle/path before
compilation, and performs the bounded checks below. It does not acquire a device
or install software. Failure leaves logs for that run and publishes no new
successful inventory. A prior receipt stays historical and cannot be relabeled.

Pure production and tests are compiled into separate directories using the
existing Android Studio JBR, `-proc:none -source 8 -target 8`, with an empty
source-search path. Only the explicit test mains execute, on a classpath with
pure production and authored tests. The real SDK is absent from that runtime
classpath. Outputs must match their explicit success fields and a positive
integer `checks` count. A truthy value, zero checks or nonzero child exit fails.
This is JVM/model evidence; synthetic packet/authority tests do not prove real
credential state, kernel caller identity or lifecycle assembly.

Android wrappers compile separately against the actual SDK37 `android.jar`,
SHA256 `bf1b4387cc7ca94fc6ef684f040d9d16fbf16248e181819f020736ea2053f177`,
and the frozen pure production classes. No Android/OEM classes execute. The
runner supplies no implementation stubs and does not use an invented Android
class graph. Source8/target8 emits class version52; Java8 library/API availability
is not checked. The existing JBR `--release 8` resource-close failure is avoided,
not presented as a successful release-API check.

D8 receives only production class files, with the real SDK supplied as `--lib`.
Tests and SDK definitions are excluded from the emission inputs. Class-file and
DEX declaration inventories reject foreign namespaces/duplicate definitions and
require every authored production class to survive emission. The own-output DEX
reader verifies format extents, SHA1 and Adler32, and has no DEX041 rebasing
fallback. Unexpected formats fail rather than silently borrowing an OEM parser.

The requested minimum API remains37. This installed D8 has previously emitted
an unsupported API37 diagnostic declaring maximum36. The final receipt retains
the actual full diagnostic; successful DEX output is not API37/ART acceptance.
No desugared library, SDK implementation class or test class is intentionally
bundled. Any D8-generated transport synthetic definitions are inventoried.

JDK/JVM temporary files and user home, child TMP/TEMP, classes, DEX and logs stay
inside the run directory. Each child is capped at45 seconds and2MiB combined
stdout/stderr. Source manifest, authored runner and actual JDK/SDK/D8 inputs are
hashed before and after. Movement prevents publication of a success receipt.
The completed out-only receipt is mirrored to the owned
`inventory/credential-transport-build.json`; it is build evidence, not canonical
runtime selection or a deployable security candidate.

## Completed frozen batch

The first coherent run completed with exit0 at
`out/credential-transport/20261105T174349327541Z-fc071d2fd69f46c18753570c7d53870b/`.
Its exact `receipt.json` is also recorded in
[credential-transport-build.json](../inventory/credential-transport-build.json).
Frozen manifest `out/credential-transport/FROZEN-INITIAL.json` has SHA256
`a0f2470ce1606f108974256f0493f2b8a127588579bebb3f2e34295123ab4258`.

The selected pure sources are root's three dispatch interfaces plus
`CredentialRoutes`, `DirectCredentialDispatch` and `ManagedDispatchAuthority`.
The two Android sources are `LockSettingsBinderFrontend` and
`OriginalStubInvoker`. Both authored test sources and the exact protocol inventory
are pinned in the same manifest. Existing SID helpers and unrelated WIP are not
included. Source, manifest, runner, protocol and toolchain pins matched before
and after execution.

- `CredentialDispatchTest`: 1,161 checks,52 scenarios,33 routes against protocol
  inventory SHAaa2baaa0…. Its root argument points only at the nested project.
- `ManagedDispatchAuthorityTest`:87 checks over authored admission/lifetime models.
- Pure compilation, test compilation, actual SDK37 wrapper compilation and D8
  each ended0. Eleven production class files emitted11 DEX definitions, all in
  the authored transport namespace; no SDK/stub/test definitions were emitted.
- Output `dex/classes.dex` SHA256:
  `f33a516b9e8db9623401c06b9ef7e7ff6d80ff8a6c9959fb035da115cae73996`.

Actual D8 diagnostic: “An API level of 37 is not supported by this compiler.
Please use an API level of 36 or earlier”. The full log is retained. Javac also
warned that source/target8 are obsolete and that the bootstrap class path was not
set. These warnings are not suppressed or relabeled as release-API acceptance.

The runner's separate local child-process checks rejected nonzero exit,
oversized output, timeout and an unfrozen manifest, and accepted bounded success.
Evidence is under
`out/credential-transport/runner-validation-618253402438424ab46a6b7b25e79cc8/`.
Those checks invoked no Java compilation, ADB or OEM code.

This successful snapshot remains unselected transport preparation. No original
Stub invocation, Android Binder transaction, ART class loading, kernel caller
authentication, real Samsung authority or live security state was exercised.
Later source/API changes require a separately pinned reviewed batch; they do not
inherit this receipt merely because their names match.
