# Closed root-host link: independent model review

The saved authored-model run passes within its stated JVM scope: **27 cases,
242 checks**. This review did not replay a compiler, model, native helper, root
command, Android/OEM implementation or phone operation.

The immutable saved-output proof is
`out/closed-root-host-model-review/ACTUAL-OUTPUT-CHECK.json`, SHA256
`d98be117e1fe5a3d80d78dd79f4fbf146ef38f60ba8bd08c48a76116412bd172`.
It checks the actual run
`out/closed-root-host-link-tests/r-a6eee388/receipt.json`, SHA256
`f2df32d9661f4c2a57b49659ebc2c1022823ac021a8f4f3921c907d10f43d11d`.

The review read the runner, new public-framework overlays and driver, and checked
all 100 selected authored source rows. The actual module, host binding, app
broker and retained session are compiled program bytes, rather than substitute
production facades. Only the actual package-private `RetainedRootSessionSpawn`
definition is excluded and replaced by an authored process fixture. No private
production field access, reset or class-file shaping is used.

The final actual SDK receipt `d10896ca…` contains 55 definitions. The selected
54 model definitions are unchanged, split into 39 host and 15 app/protocol
definitions. The two compiler-only ABI definitions are excluded from runtime.
The model output has 106 framework, 48 service and three driver classes.
All 179 retained input snapshots and 100 staged sources matched; four command
records exited zero and were reaped without reader or owned-cleanup errors.
The saved fixture-data directory was empty after cleanup.

Source corrections made the tests discriminate the intended behavior: exact
component/main-handler/bind flags; successful callback-body completion before
BEGIN returns; retirement before a late callback; and file-descriptor leak
assertions before forced harness cleanup. Unlock events are separate from the
authored current CE state.

Two earlier actual runs remain **FAILED**. Run `r-f10599c4` completed cases 0–21
before harness self-suppression of the exact modeled close error. Run
`r-6fc7adac` completed cases 0–20 before an unnecessary second uncertain close
created a new IOException. The corrected driver asserts the original error,
UNRESOLVED state and retained ownership, records the explicit close attempt
before it can fail, and never retries it in cleanup. Service cutoff and all
other cleanup remain. Exact failed receipts and source beforeimages were checked.

Typed direct Binder/Parcel calls, synthetic package/UID/proc/poll facts and
repository file descriptors are explicit model behavior. They do not establish
native transport or pidfd behavior, APK placement, live host authority, native
cleanup, PIN access, guest entry or Android acceptance. **Case 26 does not
discriminate stale Binding after unlock.** Thread-start refusal is not injected.
Production semantic review remains a separate scope.
