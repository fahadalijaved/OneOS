# Private view host source patch

`compat/handoff-view/root-view-host.patch` is an unapplied source extension over
Git `7b7c33e354a02343d511993f5b2cf4b76f8253c2`. Preparation left core Java files
unchanged. The patch contains the actual Binding/client changes and a proposed
shared-codec constants/range hunk for Root's integration. Full composed source and
exact preimages are retained under `out/retained-root-view-host/`.

The package-private main-only `requestPrivateView()` consumes a permanent local
credit before external checks. It requires the genuine existing captured source,
package and committed client, then queues one retained command on that client's
existing sole socket worker. There is no automatic post-COMMIT trigger, supplied
provider, PID, FD, path, input plan, readiness Boolean or public source factory.
The completed or uncertain preparation command remains a tombstone; no retry or
second preparation is possible.

`queryPrivateView()` requests retained native metadata on the same worker/sequence.
`privateViewObservation()` returns only the immutable last wire observation after
real main/source/package rechecks. Observed namespace/group values retain raw u64
bits, including their sign bit. They cannot attest current mounts, child liveness,
image authenticity or authority. Source/package failure invokes actual cutoff.

The worker adds PREPARE10 and QUERY12 with zero request payload. VIEW_STATE11
parses only states0..6, observed0/1, three raw u64s and exact reserved zeros.
Unobserved values must be zero, a successful observation cannot disappear/change,
and local closing/terminal tombstones cannot regress. The possibly-delivered
attempt is latched before the first send. Retirement during external work retains
the actual response but does not complete the caller's request.

A stage-missing/refused PREPARE result enters native QUERY-only drain without
another CLOSE. A view-bearing CLOSE accepts STATE4/HOLD, 5/kernel-unconfirmed or 6/refused-local-
closed, and rejects generic CLOSED. HOLD keeps the worker and actual native owner
in drain: it sends QUERY frames without resending CLOSE or preparing again. Lost
replies, EOF or pidfd exit never imply terminal5/6. Explicit5 and unknown effects
prevent `cleanupComplete()`; explicit6 permits local process/descriptor cleanup
only. Neither local cleanup nor the existing no-view CLOSED grants kernel return
or guest/security admission. Old PING and no-view CLOSE wire branches remain.

The earlier three-target patch passed independent source review (historical): `out/retained-root-view-review/trust/SOURCE-PASS.json`
(SHA-256 `7a9ffbd275158cefba7a3e3fd6daba26663225848cd2874d132a79c4052b0aec`). Static patch forward/inverse
checks reproduce the exact three composed Java files and all held preimages.

This is source only: no patch application, compilation, model workflow, Android,
OEM, native or phone execution has occurred for the extension. The prior 32/323
handoff model result covers its original sources, not this patch. Fresh source,
build and meaningful old/new lifecycle regressions remain required before use.

The current four-target successor also adds real main-only module forwarding for
request/query/close/cached metadata, with its actual private controller and
Binding checked before and after. Explicit view close retains the authentic
Binding for metadata; it does not retire the source first. Its module/close
delta passed independent source review: `out/retained-root-view-review/trust/MODULE-CLOSE-DELTA-PASS.json`
(SHA-256 `4c9e25b9c72edde5f9596b690deed5be2c22196630cd4625aa659b11ba54ad0f`).

The genuine module also forwards explicit private-view close without retiring the
authentic Binding. It checks the actual private controller/rootLink and source
before/after. Closure disables new preparation and PING; the same worker retains
QUERY-only drain. Cached final/HOLD data remains descriptive, not kernel return.
