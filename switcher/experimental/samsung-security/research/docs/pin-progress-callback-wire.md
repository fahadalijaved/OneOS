# PIN progress callback: exact wire compatibility

The actual AIDL method is **ICheckCredentialProgressCallback.onCredentialVerified():void**, not onEarlyMatched. Captured Samsung8095 and current staged5cb interfaces both have public-interface-abstract flags1537, extend IInterface and declare only public-abstract1025 `onCredentialVerified()V`. Their public-abstract1025 Stubs extend Binder; their constructors attach the same exact descriptor to themselves. Current guest Stub.asBinder returns that original Stub.

The common operation envelope is established from bodies, not descriptor equality:

| Item | Host and current staged guest |
| --- | --- |
| Descriptor | com.android.internal.widget.ICheckCredentialProgressCallback |
| Method / transaction | onCredentialVerified()V / code1 |
| Sender flags / reply | flags1 (one-way), null reply |
| Payload | interface token only; no user, credential, result, PID, generation or other argument |
| Reply decoding | none: no readException or acknowledgement |
| Cleanup | original request Parcel recycle on normal/failure paths |
| Receiver | enforceInterface for ordinary transaction range, dispatch code1 to original onCredentialVerified(), return true |

Host Proxyac3c6fce and current guest sender have the same transact tuple, although registers/NOP layout differ. Neither sender checks the transact boolean or provides a retry/default-implementation branch. The host Stub uses an IF branch; staged Stub uses a packed-switch whose key1 targets PC21. Neither selected callback case calls enforceNoDataAvail or validates the flags argument: genuine sender shape supplies flags1/no arguments, not a claim that receiver code rejects every other frame. Unknown transactions delegate to original Binder behavior. No synchronous exception/status/result payload is invented.

## Reuse the genuine Binder, not a forwarding Stub

Host canonical Stub.asInterface7dafa829 has the required actual behavior: null Binder returns null; queryLocalInterface(descriptor) returns its exact object only if it implements the canonical HOST interface; otherwise the existing host Proxy is constructed with the same supplied Binder. Proxy constructor69ecd48f stores that exact object in mRemote, and asBinder2fcc78c0 returns it. No replacement server-side Binder node is created by this Java Proxy.

Consequently passing the **genuine source-owned guest callback Binder** to the canonical host asInterface is source-compatible for operation1 without a new forwarding Stub, provided the actual Binder context, selected source/receiver and callback lifetime are independently admitted. Across different Java realms, identical class names do not make interface instances assignable; the factory's canonical instanceof check and Binder-proxy fallback are essential. Never cast a guest interface object to a host interface merely because the descriptor matches.

The local shortcut is genuinely direct Java invocation. A same-process foreign-loader local Binder may also fall through to Proxy/local transact; flags1 alone does not establish remote asynchronous behavior or a remote identity hop in that case. Remote one-way behavior, kernel permissions/driver context and meaningful caller PID values are runtime obligations. There is no argument carrying a PID to forward, and no equality assumption between request caller, host verifier and callback receiver. Do not add identity clearing, a relay thread or an extra outgoing callback transaction. A new forwarding Stub would introduce a different endpoint/custody/identity/timing boundary without solving source admission.

Null remains null; no dummy success callback is created. Descriptor compatibility does not authenticate an arbitrary supplied Binder as the genuine guest callback, bind a physical user, or authorize invocation. Keep the actual callback object/node with its original operation occurrence. The event has no user/generation payload, so a shared or stale callback cannot be assigned to a later operation from this wire shape. Death, cutoff, cancelled work and late delivery remain real caller/receiver ownership obligations; neither a strong Java reference nor normal Proxy return proves delivery/drain.

## Early progress is not final completion

The already acquired donor WrappedCallback source shows the separate bridge: AIDL onCredentialVerified posts its original Handler Runnable, then that Runnable invokes the higher-level LockPatternUtils.CheckCredentialProgressCallback.onEarlyMatched and clears its reference. That is not a second AIDL method. This acquired donor-source observation is not runtime or current installed-SystemUI placement evidence. It adds a Handler queue after the one-way Binder queue; normal send/post and nulled local fields are not a delivery acknowledgement. Preserve this genuine ordering rather than synthesize progress at final return or buffer it until a fabricated success.

Actual Samsung SPM caf41fd9 tests callback-null@832, invokes onCredentialVerified@834, catches/logs RemoteException@848 and continues. Only later does it unwrap the synthetic-password blob@861; failure can set OTHER_ERROR@875. The final original VerifyCredentialResponse and original policy/authority/UI continuation remain separate. Progress is neither a completed synthetic-password/native/CE/key result nor an independent UI/authentication grant. The required source path is original checkCredential(credential,user,callback), not verifyCredential(flags0) plus a synthetic callback.

This is a disabled source/ABI prerequisite: no helper, forwarding Stub, endpoint change, callback invocation, SDK/OEM/native execution, model, phone or Git operation is implemented or run. Full eighteen-outcome acceptance remains unchanged. Existing exact sender/staged-receiver bodies were reused; new bounded reads cover only missing host Stub/factory, current guest factory and callback/interface/identity declarations.
