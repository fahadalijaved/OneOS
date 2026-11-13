# Authored private-view host lifecycle models

The Root-executed workflow passed 14 private-view scenarios / 197 recorded checks
and the unchanged 32 handoff regressions / 323 checks. The new view driver's
finish-error discriminator also passed; it is not an additional scenario.
All seven fixture compilers and both JVM commands exited zero and were reaped.

The actual result is `out/retained-root-view-tests/r-5e2224eb/receipt.json`
(`e716a939f8db291f0f0a932b2e9c9dbb5c151a289a399e3ecd3a9b986ab5e700`).
Independent saved-output review is
`out/retained-root-view-model-review/actual/ACTUAL-OUTPUT-CHECK.json`
(`9c2771634a2714b21c6858ced080c931154bbc34bdcfa1b4099a7e4760ba5763`).
The review did not replay the workflow.

The tested SDK receipt is
`out/retained-root-view-guard-build/r-d86f158c/receipt.json`
(`6c67ec7388f1d64e5a82eeb4f17aa7a23880a9d15c3f3a26bc74a8017d841f0a`).
Its 57 actual SDK definitions supply 56 byte-identical model definitions, excluding
only `RetainedRootOfferSpawn`. The model runner recompiles no production source.
The 33 original inputs and 27 staged compiler inputs are bound separately.
The saved model run retains 240 input snapshots and 119 staged authored sources.
Fixture output maps contain framework24, integration-framework106, service48,
regression-driver3, view-framework3, control1 and view-driver2 definitions.
Compiler-only projections and SDK jars remain outside the JVM runtime.

Run from the repository with an existing JDK and the selected actual receipt:

```text
python -B tools/test_retained_root_view.py --java-home <existing-JDK> --sdk-receipt out/retained-root-view-guard-build/r-d86f158c/receipt.json
```

The actual boot issuer and unchanged F/C capture graph create the retained
Binding/client. A same-package dispatcher invokes genuine module controls; it
never obtains a Binding or reads private production fields. Startup polls the
actual main-only no-argument availability observer: pending false does not
poison or issue a request, and true remains a non-reserving source observation.
The real one-shot operation performs its own final source/package/client guards.

The fourteen cases exercise one-shot PREPARE, cached QUERY/raw unsigned bits,
partial through HOLD to terminal QUERY5, stage/refusal QUERY-only drain to6,
lost replies, source retirement during blocked work, malformed observations,
changed/regressed metadata and absence of automatic preparation after COMMIT.
Only existing designed-negative PREPARE2/3/4/8–10, QUERY11 and CLOSE5/6/12 accept
an optional exact IllegalStateException from a genuine post-external guard.
They still require the selected consumed wire/fault, one-shot and custody facts.
Other exceptions and positive operations remain strict. Guarded metadata refusal
is distinct from null or a returned last observation; after refusal the actual
availability observer must be false. Cache retention beyond a guarded refusal is
source-reviewed, not inspected through private state. Owned copies of consumed
scripted frames and EOF counters never feed decisions into production.

Four failed workflows remain FAILED and preserved:

- `r-0fd43922` / `e6a78327...`: waited before main dispatch; new view cases0.
- `r-a92acf5d` / `fca265ff...`: main pumping added, invalid post witness remained; new view cases0.
- Diagnostic-only `r-2e98374a` / `1f47d409...`: actual COMMITTED input consumed without another post; new view cases0.
- `r-f5143292` / `29b4b20a...`: genuine startup/discriminator and view cases0–3 passed, then an immediate lost-reply guard throw exposed an incorrect negative-case normal-return assumption.

Each also earned its own unchanged 32/323 baseline result. None is promoted to a
view-suite PASS or transferred to another source version. The obsolete post
witness was removed. The earlier author claim that the original baseline loop
had an early return was wrong and is withdrawn; the copied baseline is exact.
Only the new view driver has the actual early-return cleanup discriminator.
Exact source-phase reports and failure beforeimages remain under
`out/retained-root-view-model/history/`.

These are authored JVM models with scripted peer input and repository-owned JDK
stream descriptors. They execute no native/GVI, Android/OEM implementation, JNI,
mount or device operation. State5 remains kernel-unconfirmed; state6 is local
refused cleanup only. Cached metadata, PING, process exit and model counts prove
no kernel return, guest/security admission, hardware performance or full scene.
The private `cleanupComplete` flag is source-reviewed and never runtime-inspected.
