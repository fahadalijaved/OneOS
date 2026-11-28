# Prepared guest metrics endpoint

`PreparedGuestMetricsEndpoint` implements the approved **uninstalled, initially inactive** v1 RAW metadata endpoint over the frozen `PreparedGuestMetricsProducer`. It captures no DMS instance itself, performs no service lookup/publication, and installs no lifecycle or DEX hook. The [original lifecycle proposal](guest-metrics-endpoint.md) remains a separate frozen source card. Calling `activate()` does not establish that genuine DMS/phase100/code/generation admission happened.

The new production class is `com.appleexploit.oneos.security.authority.PreparedGuestMetricsEndpoint`, SHA256 `a3e01dc99c4a879640e55ac0416859abba12dea47cd447824e6e4f329d6466ed`. It directly depends on the existing Producer source SHA256 `72b0f4cdbb984c4d3b59724fd4c671771f8bf7e81c48184351e9ce77aa27b8f7`; no earlier class directory, fixture or moving build receipt is a production input. [The implementation inventory](../inventory/guest-metrics-endpoint-implementation.json) freezes the direct source and proof pins. This card is source evidence; the separate build and review cards record any later SDK/D8 or authored-fixture results without changing these producer inputs.

## API and state

`prepare(PreparedGuestMetricsProducer)` retains the exact nonnull prepared producer. `protocolBinder()` returns this endpoint's Binder; `attachInterface(null, descriptor)` exposes no local IInterface implementation. `activate()` permits one PREPARED→ACTIVE transition. A second activation throws; `retire()` is terminal and idempotent from either state. No path reactivates a retired endpoint. The exact source service, producer and defining loader remain retained through the endpoint; retirement does not null them or pretend their external work is drained.

`activeTransactions()` is only the count of **admitted code1 Java frames**. Under the endpoint's own lock, an ACTIVE call increments before validation and decrements in `finally` after capture/reply/error handling. Inactive refusals and unknown-code `super.onTransact` work are not included. This count does not cover native Binder transport, original DMS work after a call, external callbacks, other endpoints or the rest of the process. Zero is not a cancellation, native delivery, owner-release or global drain acknowledgement.

## Exact request and result

Code1 requires synchronous flags0 and a nonnull borrowed reply. Before parsing the interface token it refuses `dataSize()` outside0…512 bytes. It then enforces descriptor `com.appleexploit.oneos.security.IGuestDisplayMetrics.v1`, reads int version1 and int displayId, and refuses trailing data. Unknown codes delegate to Binder superclass behavior. There are no caller UID/PID arguments, arbitrary Parcelable/list/array inputs or caller-supplied metric values.

The producer is invoked exactly once, on the incoming thread, outside the endpoint lock. The endpoint adds no identity clear, handler hop, DMS lookup, policy override or allowlist. The original DMS getter remains responsible for native-caller display visibility. Producer preparation/member shapes and a shared UID are not source or Samsung authority attestation.

After a normal capture result, a second ACTIVE check under the own lock is the **reply-admission fence**. If retirement won before this fence, no success/ABSENT fields are written. The lock is released before writing the borrowed reply. Retirement after the fence may precede construction or native delivery of that admitted reply. A client must retain/check its own admitted endpoint instance and epoch; this component supplies no physical-display/cache-generation proof.

Successful replies write the normal no-exception envelope, version1, echoed displayId, then status0 for the original getter's genuine null or status1 followed by five ints: appWidth, appHeight, logicalDensityDpi, physicalXDpiBits and physicalYDpiBits. The two DPI quantities are `Float.floatToRawIntBits` of the producer's Java field reads; no native/Parcelable byte-preservation claim is made. Only one genuine result supplies a Sample; no DisplayInfo or synthetic full Parcelable crosses this protocol. RAW values still require the actual Samsung CompatSandbox and ResourcesManager/configuration/CompatibilityInfo calculation in a future consumer.

The endpoint leaves borrowed Parcel ownership with Binder/caller: no recycle, position reset, size reset or request mutation. A native write fault can occur after partial reply construction; it is a failed/uncertain transaction, not ABSENT or a retry instruction.

## Failure and retirement

Capture's original `RemoteException`, `RuntimeException` and `Error` are rethrown directly, even when retirement occurs during that failing capture. Other checked helper faults become `RemoteException("Guest metadata capture failed")` with the original cause. That fixed message contains no input values. No exception is converted to null/default/readiness. Supported Binder serialization is distinct from preserving arbitrary Java Throwable object identity across processes. The count decrements through every admitted exit.

The state lock is never held across capture or Parcel parsing/writing. Concurrent and reentrant calls each have a local result and balanced count. Retirement refuses newly admitted work and unadmitted replies; it neither waits for active stacks nor revokes already admitted native replies. The real lifecycle owner still must stop consumers, establish its own endpoint/source-generation lifetime, deal with death/uncertain completion, and acknowledge actual retirement/drain before release or return to One UI.

## Prepared build/review boundary

Root approved this source/API scope; no endpoint publication, original lifecycle edit, Android/OEM class execution, phone work or service mutation is authorized or performed here. SDK37/D8 emission and isolated authored fixtures are owned by separate workers. The intended source8 output closure is the one Endpoint definition plus the frozen Producer, Sample and its already reviewed Java8 empty synthetic `$1` constructor-access marker—four definitions total, subject to actual emitted-class verification. No test or SDK declaration definition belongs in the output.

Actual hidden-API reflection, incoming native identity, admitted DMS/phase100/source/loader/currentness/lifetime, alias collision/publication, native reply/death/drain, Samsung boot/helper selection and Context startup remain unassembled. This source-only component proves no PIN/fingerprint/key/CE operation and no functioning Android endpoint.
