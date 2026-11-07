# Experimental PIN check completion

This directory contains an unwired, per-request scheduling primitive and
first-party JVM models. It is not included in the OneOS app, session scripts,
package sets or guest framework. It introduces no enabled security feature.

`PinCheckCompletion` joins two separate observations for the same actual request
and callback receiver:

- a genuine progress event and its original delivery Runnable;
- that request's original canonical response reporting a match.

It returns the original Runnable at most once after both observations. A final
match alone never creates progress. An early event followed by an error, timed
nonmatch, null response, exception or transport uncertainty releases no success
ticket. Cancellation, stale-request marking and closure are terminal. The first
genuine progress occurrence wins; conflicting final objects prevent release.

A returned ticket is only a scheduling decision. The cell never invokes it,
posts to a Handler, dismisses keyguard, reports a policy attempt or grants unlock.
It cannot recall a ticket already returned. A real consumer must own the source,
request, current subject and queued execution, recheck them at delivery, and keep
required policy and cleanup behavior. Response errors are not classified as
wrong PIN; a framework response can lose the distinction between a credential
mismatch and a backend failure.

The source uses hidden framework `VerifyCredentialResponse` predicates. The JVM
tests supply an explicitly authored response model; they do not execute an
Android/OEM implementation or demonstrate an Android callback, Binder, native
credential operation, policy decision or device unlock. The model must never be
packaged as a framework replacement. No production build or runtime placement is
selected here.

## Run the source-only models

Use Python 3.9+ and an existing JDK 17+; no Android SDK or downloads are needed.
From the OneOS repository root, with `JAVA_HOME` pointing to that JDK:

```sh
python3 switcher/experimental/samsung-security/tools/test_pin_check_completion.py \
  --java-home "$JAVA_HOME" \
  --out /absolute/path/outside/OneOS/pin-cell-tests
```

Choose an absolute output directory outside the entire OneOS checkout. The runner
compiles three declaration-only projections for compiler use, the cell, separate
authored runtime models and the test driver. The projections are excluded from
the runtime classpath; only fresh cell classes, authored models and the JDK test
driver run. A fresh run of this recipe passed 16 cases and 132 checks with JDK 21,
with zero delivery-Runnable invocations. These are authored scheduling-model
results, not Android or device acceptance.

The proposed retained-host integration and its remaining source, subject, policy
and lifetime requirements are described in [the RFC](../../../docs/samsung-shared-security.md).
Shared PIN/fingerprint authority, credential changes, CE/app-key continuity and
normal return to One UI remain separate unimplemented integration work.
