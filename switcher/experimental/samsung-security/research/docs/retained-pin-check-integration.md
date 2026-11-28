# Retained Samsung PIN check integration

The new, default-closed check adapter and private transport compile together from
eleven production sources. The actual SDK37/D8 build produced 24 authored classes
and a 73,048-byte DEX (`ccea8f286c8ade6c04bd3a2c9388cf2d0d0c3c13d122c72df030b50fa0a17a9a`).
This is PC component verification. No endpoint is published, no real keypad is
retargeted, and no device acceptance case is complete.

`PreparedRetainedPinCheckOwner` derives its original service, physical user and
serial only through the existing retained operation owner's fenced preparation
bridge. It caches Samsung's original public-final `checkCredential` method and
the canonical progress interface. An admitted worker calls that method once,
on the same worker and Binder caller, with the internally bound user and nullable
original callback. The adapter adds no identity clearing, worker hop, verification
substitution, retry or synthetic result. The original response, null and cause
remain observable. It does not invoke the callback itself.

The private v1 endpoint adds synchronous sensitive code2. Its request contains
the original typed PIN and original callback Binder, with no supplied user,
serial or operation flags. Samsung's canonical `Stub.asInterface` creates the
host callback interface; no forwarding Stub is introduced. The host owns and
closes its decoded credential. The client borrows its input and recycles only
its two acquired Parcels. Existing code1 bodies remain preserved apart from the
new dispatch. UID1000 is an operation restriction, not proof of guest provenance.

Preparation review corrected a reentrancy gap before compilation: the check
owner now claims its control fence before observing the main Looper or external
captures. Nested or wrong-thread rejection cannot clear the winning operation.
The base bridge has an exact inverse to its previous source. Ingress defaults
closed; close is terminal local cutoff, and synchronous-frame idle does not
acknowledge pending progress callbacks, outer Binder replies or native work.

The actual public source-build receipt is
`out/retained-pin-source-build/r-c0b68b59be5c/receipt.json` (`952d4e49...`).
Two compiler commands and D8 returned zero, with owned processes reaped and
unchanged inputs. All three compiler-only declarations stay outside program
DEX. The model cohort is a byte-identical subset of 19 of those 24 classes;
the capture module and permit are excluded. No production recompilation or
classfile shaping is used to prepare that cohort. Independent saved-output
review `d3517f16...` checked the actual build and export. The bounded source,
tool, build and review identities are recorded in
[`inventory/retained-pin-check-build.json`](../inventory/retained-pin-check-build.json).
Java8 and API37/max36 warnings remain recorded in the actual logs.

The actual model run passed **30 scenarios and 258 checks** against the unchanged
19-class SDK subset. Its receipt is
`out/retained-pin-check-tests/r-33c30e7c/receipt.json` (`6baf10b6...`). Four authored
fixture compilers and one JDK model process returned zero with owned processes
reaped; no production source was recompiled. Cases cover callbacks preceding
error/null, protocol and caller rejection, cleanup faults, cutoff/reentrancy,
and code1 regression. Independent saved-output review `eefaf9d9...` verified
the actual inputs, 77 staged sources, class maps, logs and results without
replaying the workflow. This is separate from the fixture source review.
The earlier ten-source/22-class public-build report describes its historical
checkpoint and does not cover this extension.

Real guest delivery and process ownership remain unassembled. Genuine progress
can precede a later failed result, so this transport alone cannot authorize
ColorOS's early-success handler. The separate completion cell still needs the
actual request/task, current-user, SIM/admin/strong-auth and policy owners before
any UI success path is selected. Reciprocal PIN changes, fingerprints, app keys,
encrypted storage, switch/return/cold boot and all 18 device cases remain open.
The phone remains offline-only and unchanged.
