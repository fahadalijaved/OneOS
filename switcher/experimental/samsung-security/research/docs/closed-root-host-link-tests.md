# Closed host/app link authored models

The corrected Root-executed workflow passed **27 cases / 242 checks**. The saved receipt is `out/closed-root-host-link-tests/r-a6eee388/receipt.json` (SHA256 `f2df32d9661f4c2a57b49659ebc2c1022823ac021a8f4f3921c907d10f43d11d`). Independent saved-output review is `out/closed-root-host-model-review/ACTUAL-OUTPUT-CHECK.json` (`d98be117e1fe5a3d80d78dd79f4fbf146ef38f60ba8bd08c48a76116412bd172`); the reviewer did not replay the workflow.

```text
python -B tools/test_closed_root_host_link.py --java-home <canonical existing JDK home> --sdk-receipt out/closed-root-host-link-build/r-eb2019cc/receipt.json
```

The runner compiles only authored fixtures. It copies the actual SDK model cohort: 54 unchanged program classes from the 55-class SDK build, excluding only the real package-private `RetainedRootSessionSpawn` definition. The actual bootstrap module, host binding/profile, app broker and session controller remain intact. The selected SDK receipt is `d10896caec8081a647e0df37ea26db5b576b63c9f308e1b0ce650d579aea5dc9`; compiler-only interfaces, SDK and API102 jars are absent from runtime. There is no production compilation, D8, shaping or private production-state inspection in the model runner.

The actual 100 staged fixture sources produced framework106/service48/driver3 classes. All four compiler/model commands exited0 and were reaped with no reader or owned cleanup errors. The receipt retains179 input snapshots, exact source/class maps and the actual command records. The source phase reports were copied unchanged before this metadata update under `out/closed-root-host-link-model/history/pre-actual-report-f2df32d9/`.

The cases exercise the actual module boot-hook → host binding → app broker → retained Session → host callback path, including the host's real validation PING to that same Session. They cover default disabled/new protected profile, package/signer/version/APK mismatch, bind refusal, worker work failure, refused main delivery, broker caller/framing refusal, callback body completion before BEGIN returns, callback arrival after host retirement, package drift, broker/control death, uncertain unbind, failed one-shot startup, ACK versus pidfd exit and uncertain descriptor close. The unlock cases keep binding disabled while CE is locked, reject an event whose fresh UserManager result is still false, and bind once after modeled unlock.

Two earlier workflows remain FAILED, not passing evidence: `r-f10599c4`/`1ce346d453e7382a8d411b64248a1d26c6cb5e56aa4819daca49d12326287105` failed in case22's exception/cleanup expectations; `r-6fc7adac`/`a47fffe8c7ba3487679b6cbc10f41bbef1812a4a7e4e5bdafafac3eb7bce96ba` failed when cleanup repeated case21's unresolved close. Exact sources and receipts are preserved in the corresponding `history/failed-*` directories. The correction asserts expected failure/state/live ownership and records the test-owned close attempt before calling; cleanup keeps service cutoff but never repeats that uncertain close. It does not swallow errors by class/message or change production behavior.

These are authored direct Binder token calls, synthetic UID/package/CE/proc facts, a controlled main queue and repository-only stream-backed descriptors. Public APIs are invoked across isolated model loaders; no private production fields are read/reset. Ordinary file-FD cleanup is asserted before forced fixture cleanup; selected unresolved pidfd owners remain a separate observation. No su, socket/syscall/native helper, Android/OEM implementation, PIN operation, guest start or device action ran. CAPTURED/QUEUED, unbind, Binder ACK and fixture cleanup are not native drain, source authority or execution permission.

Case26 does not change the retained PIN Binding's state after unlock, so it does **not** discriminate an incorrect stale-Binding check after CE transition. The actual Registry/Family-only source check is separate source evidence. Thread-start refusal, exhaustive schedules, Android packaging/loading/security and real native lifecycle remain outside these models.

## Cached storage owner successor model

The successor used the exact current SDK 37 build and kept the 54-class model
closure. It excludes only the real Spawn class and supplies the same authored
substitute. The historical manifest and fixture files remain held. Four
fixture copies were updated for this run. The two service stubs declare the
real nullable cache shape, the authored World controls cache identity, and
the driver adds six cases. All other 96 fixture sources are byte-identical.

All 33 scenarios and 313 checks passed, including the exact prior 27 scenarios
and 242 checks. An observed foreign UMS or preparer cache blocks startup before
binding or Spawn. A mismatch observed after the unlock receiver registers
cuts admission and removes that receiver once. When the modeled host and app
are already linked, disconnect still unbinds the retained connection, removes
both receivers, and closes the modeled Session once while the cache mismatch
persists. Duplicate disconnect does not repeat that cleanup.

These outcomes come from the authored JVM environment and exact compiled
production Java classes. Live Samsung owner admission, Android loader behavior,
native drain and device acceptance remain open.
[Successor fixture manifest](../out/closed-root-host-link-cache-identity-tests/fixture-manifest-with-extents.json)
· [Successor model receipt](../out/closed-root-host-link-cache-identity-tests/r-a5307b7c/receipt.json)
